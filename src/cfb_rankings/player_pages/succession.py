"""Deterministic succession detector — "The Ghost, the Clock, the Musical Chairs".

Spec: docs/design-system/44-succession-engine.md. ZERO LLM / ZERO network.

Detects positional succession from structured data only:

  * ROLE-HOLDER (the throne-line, vertical) — the player with the most
    position-defining usage in a (team, position, season): QB = MAX pass ATT,
    RB = MAX rush CAR, WR/TE = MAX receiving REC. Season totals live in
    ``player_season_stats`` with ``week`` as a season marker (16 or 21) and
    ``season_type='both'`` — aggregate ``MAX(stat_value_num)`` GROUP BY
    player/team/season, then take the max-usage player. That table carries
    ``source_player_id`` (the cfbd external id) directly, so the role-holder's
    ``player_external_id`` resolves without a second join.
  * DIFF consecutive seasons -> a succession event (the ghost handed off).
  * PEDIGREE (Filling-the-Shoes) — ``player_recruiting_profiles`` stars/rating
    for incumbent, predecessor, heir.
  * PREDECESSOR FATE + PORTAL FLOW (horizontal / musical chairs) —
    ``transfer_entries`` traces transferred-out + destination;
    ``player_nfl_draft`` = drafted; still-rostered-but-lost-role = benched;
    else graduated.
  * HEIR-APPARENT (the Clock) — ``player_depth_chart_2026`` (partial, 513 rows;
    confidence-gated) plus a roster + recruiting fallback (the highest-pedigree
    young non-holder). clock_score = pedigree x youth x latent_opportunity.

Every path degrades to ``None`` / ``[]`` / ``0`` on missing data and NEVER
raises into the page. All new state keys on ``player_external_id`` (the stable
cfbd id = ``player_source_ids.source_player_id`` WHERE ``source_name='cfbd'``);
the unstable numeric ``player_id`` is carried only as a convenience denorm.

Public API:
    detect_succession(db, team_id, position_group, season_year) -> dict | None
    compute_throne_line(db, team_id, position_group, season_years) -> list[dict]
    fetch_succession_for_player(db, player_external_id, season_year) -> SuccessionRead | None
    write_succession(db, season_year, position_groups=('QB','RB','WR','TE')) -> int
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Typed result contract (mirrors docs/design-system/49 §5 SuccessionRead verbatim).
# Defined locally so this module is self-contained — story_card.py imports it
# from here. ZERO external deps to keep the render path crash-proof.
# ---------------------------------------------------------------------------
@dataclass
class SuccessionRead:
    """Filling-the-Shoes + the Clock, deterministic (doc 44)."""

    role: str                        # position_group, e.g. "QB"
    predecessor_name: Optional[str]
    predecessor_stars: Optional[int]
    heir_name: Optional[str]
    heir_stars: Optional[int]
    shoes_read: Optional[str]        # downgrade|upgrade|continuity|leap_of_faith|low_bar
    tone: Optional[str]              # mourning|dread|hope|reverence|relief|suspense
    clock_line: Optional[str]        # "how many games until <heir> (4*) takes the job?"
    confidence: float = 0.0          # gated low when depth data is partial


# ---------------------------------------------------------------------------
# Role definitions — position_group -> (stats category, defining stat_type).
# v1 scope: QB (existential), then RB/WR/TE. OL/DEF are confidence-gated /
# skipped (weak without snap data — doc 44 §2/§9).
# ---------------------------------------------------------------------------
_ROLE_STAT: dict[str, tuple[str, str]] = {
    "QB": ("passing", "ATT"),
    "RB": ("rushing", "CAR"),
    "WR": ("receiving", "REC"),
    "TE": ("receiving", "REC"),
}

# Positions whose succession read we trust at full confidence. Everything else
# (OL/DL/LB/DB/K/P...) is detectable but confidence-gated low per doc 44 §7/§9.
_FULL_CONFIDENCE_POS = frozenset({"QB", "RB", "WR", "TE"})

# Young = class_year codes that read as "the kid / the clock". roster_entries
# stores class_year as a string code ('1'..'6'); 1=FR, 2=SO are the loud-clock
# years, 3=JR still young-ish. Treat blanks/garbage as unknown (mid weight).
_YOUTH_WEIGHT = {"1": 1.0, "2": 0.85, "3": 0.6, "4": 0.3, "5": 0.2, "6": 0.1}

# Minimum defining-usage to count as a real role-holder (filters fringe arms).
_MIN_ROLE_USAGE = {"QB": 40.0, "RB": 30.0, "WR": 15.0, "TE": 12.0}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_all(db, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """query_all that never raises (missing table / bad column -> [])."""
    try:
        return db.query_all(sql, params) or []
    except Exception:
        return []


def _safe_one(db, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return db.query_one(sql, params)
    except Exception:
        return None


def _to_int(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def _to_float(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _resolve_external_id(db, player_id: int | None) -> str | None:
    """cfbd stable id for a numeric player_id (the linkrot anchor)."""
    if db is None or player_id is None:
        return None
    row = _safe_one(
        db,
        "select source_player_id from player_source_ids "
        "where player_id = :pid and source_name = 'cfbd' limit 1",
        {"pid": int(player_id)},
    )
    if row and row.get("source_player_id"):
        return str(row["source_player_id"])
    return None


def _team_name(db, team_id: int | None) -> str | None:
    if team_id is None:
        return None
    row = _safe_one(
        db,
        "select canonical_name from teams where team_id = :tid",
        {"tid": int(team_id)},
    )
    return str(row["canonical_name"]) if row and row.get("canonical_name") else None


def _recruiting(db, player_id: int | None) -> dict[str, Any] | None:
    """Most recent recruiting profile (stars/rating/national_rank) for a player."""
    if player_id is None:
        return None
    row = _safe_one(
        db,
        """
        select stars, rating, national_rank, committed_team, season_year
          from player_recruiting_profiles
         where player_id = :pid
         order by season_year desc, stars desc
         limit 1
        """,
        {"pid": int(player_id)},
    )
    return row


def _class_year(db, player_id: int | None) -> str | None:
    """Latest roster class_year code ('1'..'6') for the player, if any."""
    if player_id is None:
        return None
    row = _safe_one(
        db,
        """
        select class_year from roster_entries
         where player_id = :pid and class_year is not null and class_year <> ''
         order by season_year desc limit 1
        """,
        {"pid": int(player_id)},
    )
    return str(row["class_year"]) if row and row.get("class_year") else None


# ---------------------------------------------------------------------------
# Role-holder detection (the throne-line vertical)
# ---------------------------------------------------------------------------
def _role_holder(db, team_id: int, position_group: str, season_year: int) -> dict[str, Any] | None:
    """The max-usage player at (team, position, season). None if below floor.

    Season totals are stored with week as a season marker (16/21) and
    season_type='both'; aggregate MAX(stat_value_num) GROUP BY player/team/season
    (do NOT filter week IS NULL and do NOT SUM — that double-counts cumulative
    rows). player_season_stats carries source_player_id directly.
    """
    spec = _ROLE_STAT.get((position_group or "").upper())
    if spec is None:
        return None
    category, stat_type = spec
    rows = _safe_all(
        db,
        """
        select player_id,
               max(source_player_id) as source_player_id,
               max(player_name)      as player_name,
               max(stat_value_num)   as usage
          from player_season_stats
         where team_id = :tid
           and season_year = :s
           and category = :cat
           and stat_type = :stype
           and stat_value_num is not null
         group by player_id
         order by usage desc
         limit 1
        """,
        {"tid": int(team_id), "s": int(season_year), "cat": category, "stype": stat_type},
    )
    if not rows:
        return None
    top = rows[0]
    usage = _to_float(top.get("usage")) or 0.0
    floor = _MIN_ROLE_USAGE.get((position_group or "").upper(), 0.0)
    if usage < floor:
        return None
    pid = _to_int(top.get("player_id"))
    ext = top.get("source_player_id")
    ext = str(ext) if ext else _resolve_external_id(db, pid)
    return {
        "player_id": pid,
        "player_external_id": ext,
        "player_name": top.get("player_name"),
        "usage": usage,
    }


def compute_throne_line(
    db, team_id: int, position_group: str, season_years: list[int],
) -> list[dict]:
    """Ordered role-holders for (team, position) across the given seasons.

    Each node carries the holder + recruiting stars + class year + fate. Seasons
    with no detectable holder are skipped. Never raises; returns [] on no data.
    """
    if db is None or team_id is None or not season_years:
        return []
    pos = (position_group or "").upper()
    if pos not in _ROLE_STAT:
        return []

    years = sorted({int(y) for y in season_years})
    nodes: list[dict] = []
    for yr in years:
        holder = _role_holder(db, int(team_id), pos, yr)
        if holder is None:
            continue
        rec = _recruiting(db, holder.get("player_id")) or {}
        nodes.append(
            {
                "season_year": yr,
                "team_id": int(team_id),
                "position_group": pos,
                "player_id": holder.get("player_id"),
                "player_external_id": holder.get("player_external_id"),
                "player_name": holder.get("player_name"),
                "usage": holder.get("usage"),
                "stars": _to_int(rec.get("stars")),
                "rating": _to_float(rec.get("rating")),
                "national_rank": _to_int(rec.get("national_rank")),
                "class_year": _class_year(db, holder.get("player_id")),
                "fate": None,  # filled in by the caller when a successor is known
            }
        )
    return nodes


# ---------------------------------------------------------------------------
# Predecessor fate + portal flow (the horizontal / musical-chairs axis)
# ---------------------------------------------------------------------------
def _predecessor_fate(
    db, predecessor_id: int | None, from_team_id: int, season_year: int,
) -> tuple[str | None, str | None]:
    """(fate, dest_team) for a departed role-holder.

    Order of checks: drafted (NFL) -> transferred_out (portal, w/ destination)
    -> benched (still on the from-team roster this season) -> graduated.
    """
    if predecessor_id is None:
        return (None, None)

    # Drafted? NFL draft in the season after he last held the role (or any).
    draft = _safe_one(
        db,
        "select draft_year, college_team_name from player_nfl_draft "
        "where player_id = :pid order by draft_year desc limit 1",
        {"pid": int(predecessor_id)},
    )
    if draft:
        return ("drafted", None)

    # Transferred out? transfer_entries from this team. The portal-flow row is
    # keyed on the destination season (season_year+1 relative to the role year).
    tr = _safe_one(
        db,
        """
        select to_team_name, transfer_date
          from transfer_entries
         where player_id = :pid and from_team_id = :tid
         order by transfer_date desc limit 1
        """,
        {"pid": int(predecessor_id), "tid": int(from_team_id)},
    )
    if tr and tr.get("to_team_name"):
        return ("transferred_out", str(tr["to_team_name"]))

    # Still on the from-team roster the following season but lost the role = benched.
    still = _safe_one(
        db,
        "select 1 as ok from roster_entries "
        "where player_id = :pid and team_id = :tid and season_year = :s limit 1",
        {"pid": int(predecessor_id), "tid": int(from_team_id), "s": int(season_year)},
    )
    if still:
        return ("benched", None)

    return ("graduated", None)


def _heir_origin(
    db, heir_id: int | None, team_id: int, prior_season: int,
) -> tuple[str, str | None]:
    """(origin, origin_team) for the heir: portal / internal / true_freshman."""
    if heir_id is None:
        return ("internal", None)

    # Portal arrival INTO this team?
    tr = _safe_one(
        db,
        """
        select from_team_name, transfer_date
          from transfer_entries
         where player_id = :pid and to_team_id = :tid
         order by transfer_date desc limit 1
        """,
        {"pid": int(heir_id), "tid": int(team_id)},
    )
    if tr and tr.get("from_team_name"):
        return ("portal", str(tr["from_team_name"]))

    # On last year's roster behind the legend = internal ("the kid who waited").
    prev = _safe_one(
        db,
        "select 1 as ok from roster_entries "
        "where player_id = :pid and team_id = :tid and season_year = :s limit 1",
        {"pid": int(heir_id), "tid": int(team_id), "s": int(prior_season)},
    )
    if prev:
        return ("internal", None)

    # First-year on the roster with no prior presence = true freshman.
    cy = _class_year(db, heir_id)
    if cy == "1":
        return ("true_freshman", None)
    return ("internal", None)


# ---------------------------------------------------------------------------
# Heir-apparent / the Clock
# ---------------------------------------------------------------------------
def _departed_player_ids(db, team_id: int) -> set[int]:
    """player_ids who transferred OUT of this team — never eligible as heirs.

    A departed starter still carries a stale roster row for the team (e.g. Nico
    Iamaleava's 2024 Tennessee roster + UCLA depth-chart row), which would
    otherwise pollute the team-scoped depth-chart join. Filtering on
    transfer_entries.from_team_id removes the ghost from the clock.
    """
    rows = _safe_all(
        db,
        "select distinct player_id from transfer_entries where from_team_id = :tid",
        {"tid": int(team_id)},
    )
    out: set[int] = set()
    for r in rows:
        pid = _to_int(r.get("player_id"))
        if pid is not None:
            out.add(pid)
    return out


def _clock_candidate(
    db,
    team_id: int,
    position_group: str,
    incumbent_id: int | None,
    season_year: int,
    *,
    exclude_ids: frozenset[int] = frozenset(),
) -> dict[str, Any] | None:
    """The most threatening young talent BELOW the incumbent (the clock).

    Two paths, best-available wins:
      1. Depth chart (player_depth_chart_2026, partial 513 rows): a same-position
         non-incumbent on the team, gated by its TEXT confidence ('confirmed' >
         'projected'). Team-scoped via roster_entries (no 2026 roster exists, so
         we scope across any season the player was rostered for this team).
      2. Roster + recruiting fallback: the highest-pedigree young (class 1-3)
         same-position player on the team's roster who is NOT the incumbent.

    The incumbent, the predecessor, and anyone who transferred OUT of this team
    are excluded (a departed player is a ghost, not an heir). Returns the
    candidate dict, or None when no credible clock exists. The candidate carries
    a `depth_confidence` token used to gate the Clock display.
    """
    pos = (position_group or "").upper()
    blocked: set[int] = set(exclude_ids) | _departed_player_ids(db, int(team_id))
    if incumbent_id is not None:
        blocked.add(int(incumbent_id))

    def _eligible(pid: int | None) -> bool:
        return pid is not None and pid not in blocked

    # --- Path 1: depth chart, team-scoped via roster_entries ------------------
    depth_rows = _safe_all(
        db,
        """
        select distinct d.player_id, d.slot_rank, d.starter_status, d.confidence
          from player_depth_chart_2026 d
          join roster_entries r on r.player_id = d.player_id and r.team_id = :tid
         where d.position_group = :pos
        """,
        {"tid": int(team_id), "pos": pos},
    )
    best: dict[str, Any] | None = None
    best_score = -1.0
    for row in depth_rows:
        pid = _to_int(row.get("player_id"))
        if not _eligible(pid):
            continue
        cand = _score_clock(db, pid, depth_conf=str(row.get("confidence") or "projected"),
                            slot_rank=_to_int(row.get("slot_rank")))
        if cand and cand["clock_score"] > best_score:
            best, best_score = cand, cand["clock_score"]
    if best is not None:
        return best

    # --- Path 2: roster + recruiting fallback ---------------------------------
    # Same-position players on the most recent roster for this team, NOT the
    # incumbent, who are young and carry recruiting pedigree.
    roster_rows = _safe_all(
        db,
        """
        select distinct r.player_id, r.class_year
          from roster_entries r
         where r.team_id = :tid
           and upper(coalesce(r.position,'')) = :pos
           and r.season_year >= :s0
        """,
        {"tid": int(team_id), "pos": pos, "s0": int(season_year) - 1},
    )
    for row in roster_rows:
        pid = _to_int(row.get("player_id"))
        if not _eligible(pid):
            continue
        cand = _score_clock(db, pid, depth_conf=None, slot_rank=None)
        if cand and cand["clock_score"] > best_score:
            best, best_score = cand, cand["clock_score"]
    return best


def _score_clock(
    db, player_id: int, *, depth_conf: str | None, slot_rank: int | None,
) -> dict[str, Any] | None:
    """clock_score = pedigree x youth x latent_opportunity for one candidate."""
    rec = _recruiting(db, player_id) or {}
    stars = _to_int(rec.get("stars"))
    cy = _class_year(db, player_id)

    # Pedigree: 5* dominates; unknown -> mild (0.4) so an unranked kid still ticks.
    pedigree = {5: 1.0, 4: 0.75, 3: 0.45, 2: 0.25, 1: 0.15}.get(stars or 0, 0.35)
    youth = _YOUTH_WEIGHT.get(cy or "", 0.5)
    # Latent opportunity: a higher (worse) depth slot or unknown depth => more
    # upside to climb; confirmed depth-chart presence is a stronger signal.
    if depth_conf == "confirmed":
        latent = 0.9
    elif depth_conf == "projected":
        latent = 0.7
    else:
        latent = 0.5
    score = pedigree * youth * latent
    if score <= 0.0:
        return None

    name_row = _safe_one(
        db, "select full_name from players where player_id = :pid", {"pid": int(player_id)},
    )
    return {
        "player_id": int(player_id),
        "player_external_id": _resolve_external_id(db, player_id),
        "player_name": str(name_row["full_name"]) if name_row and name_row.get("full_name") else None,
        "stars": stars,
        "class_year": cy,
        "depth_confidence": depth_conf,
        "slot_rank": slot_rank,
        "clock_score": round(score, 4),
    }


# ---------------------------------------------------------------------------
# Filling-the-Shoes read + tone (doc 44 §5 / §10)
# ---------------------------------------------------------------------------
def _shoes_read(
    incumbent: dict[str, Any],
    predecessor: dict[str, Any] | None,
    heir_origin: str | None,
) -> tuple[str, str]:
    """(read, tone) from the pedigree/production deltas.

    read  in {downgrade, upgrade, continuity, leap_of_faith, low_bar}
    tone  in {mourning, dread, hope, reverence, relief, suspense}
    """
    inc_stars = _to_int(incumbent.get("stars")) or 0
    inc_usage = _to_float(incumbent.get("usage")) or 0.0

    # Leap of faith: the incumbent is an unproven freshman / true-freshman arrival.
    if heir_origin == "true_freshman" or (incumbent.get("class_year") == "1"):
        return ("leap_of_faith", "hope")

    if predecessor is None:
        # No ghost to measure against — read as continuity if he's productive,
        # else a leap.
        return ("continuity", "reverence") if inc_usage > 0 else ("leap_of_faith", "suspense")

    pred_stars = _to_int(predecessor.get("stars")) or 0
    pred_usage = _to_float(predecessor.get("usage")) or 0.0
    pred_fate = predecessor.get("fate")

    # Low bar: the ghost was benched (a disappointment the room is glad to escape).
    if pred_fate == "benched":
        return ("low_bar", "relief")

    star_delta = inc_stars - pred_stars

    if star_delta >= 2:
        return ("upgrade", "hope")
    if star_delta <= -2:
        # A real downgrade — mourning if the ghost was a high-pedigree departure
        # (drafted / 5*), otherwise dread.
        if pred_fate == "drafted" or pred_stars >= 5:
            return ("downgrade", "mourning")
        return ("downgrade", "dread")
    # Comparable pedigree — continuity. If the ghost was drafted/elite, the
    # register is reverence (honor the ghost); else neutral reverence.
    if pred_fate == "drafted" or pred_stars >= 5:
        return ("continuity", "reverence")
    return ("continuity", "reverence")


_STARS_GLYPH = "★"  # ★


def _clock_line(heir: dict[str, Any] | None, incumbent: dict[str, Any]) -> str | None:
    """The suspense open-loop line, attributed/honest. None when no heir."""
    if not heir or not heir.get("player_name"):
        return None
    heir_name = heir["player_name"]
    stars = _to_int(heir.get("stars"))
    star_tag = f" ({stars}{_STARS_GLYPH})" if stars else ""
    inc_name = incumbent.get("player_name") or "the starter"
    return f"How many games until {heir_name}{star_tag} takes the job from {inc_name}?"


# ---------------------------------------------------------------------------
# Top-level detector — one throne-line node for (team, position, season)
# ---------------------------------------------------------------------------
def detect_succession(
    db, team_id: int, position_group: str, season_year: int,
) -> dict | None:
    """One succession node: incumbent + predecessor (ghost) + heir (clock) + read.

    Returns a fully-resolved dict ready to upsert into player_succession, or
    None when there is no detectable role-holder for this (team, position,
    season). Never raises.
    """
    if db is None or team_id is None or season_year is None:
        return None
    pos = (position_group or "").upper()
    if pos not in _ROLE_STAT:
        return None

    incumbent_raw = _role_holder(db, int(team_id), pos, int(season_year))
    if incumbent_raw is None:
        return None

    inc_rec = _recruiting(db, incumbent_raw.get("player_id")) or {}
    incumbent = {
        **incumbent_raw,
        "stars": _to_int(inc_rec.get("stars")),
        "rating": _to_float(inc_rec.get("rating")),
        "national_rank": _to_int(inc_rec.get("national_rank")),
        "class_year": _class_year(db, incumbent_raw.get("player_id")),
    }

    # Predecessor = prior-season role-holder if it's a DIFFERENT player (a real
    # handoff). Same player two years running = no succession event this year.
    prev_raw = _role_holder(db, int(team_id), pos, int(season_year) - 1)
    predecessor: dict[str, Any] | None = None
    if prev_raw and prev_raw.get("player_id") != incumbent.get("player_id"):
        pred_rec = _recruiting(db, prev_raw.get("player_id")) or {}
        fate, dest = _predecessor_fate(
            db, prev_raw.get("player_id"), int(team_id), int(season_year),
        )
        predecessor = {
            **prev_raw,
            "stars": _to_int(pred_rec.get("stars")),
            "rating": _to_float(pred_rec.get("rating")),
            "fate": fate,
            "dest_team": dest,
        }

    # Heir origin (how the incumbent got here) — drives leap_of_faith.
    heir_origin, heir_origin_team = _heir_origin(
        db, incumbent.get("player_id"), int(team_id), int(season_year) - 1,
    )

    # The Clock — the threat below the incumbent. Exclude the predecessor (the
    # ghost) so a departed starter never resurfaces as his own replacement.
    exclude: set[int] = set()
    if predecessor and predecessor.get("player_id") is not None:
        exclude.add(int(predecessor["player_id"]))
    clock = _clock_candidate(
        db, int(team_id), pos, incumbent.get("player_id"), int(season_year),
        exclude_ids=frozenset(exclude),
    )

    read, tone = _shoes_read(incumbent, predecessor, heir_origin)

    # Confidence: full for QB/RB/WR/TE; dampened for everything else; further
    # dampened when the clock leans only on the roster fallback (no depth data).
    base_conf = 0.85 if pos in _FULL_CONFIDENCE_POS else 0.4
    if clock is not None and clock.get("depth_confidence") is None:
        # roster-only clock — keep the node confident but flag the clock soft.
        clock_conf = 0.45
    elif clock is not None and clock.get("depth_confidence") == "confirmed":
        clock_conf = 0.8
    elif clock is not None:
        clock_conf = 0.6
    else:
        clock_conf = 0.0
    confidence = round(base_conf, 4)

    team_name = _team_name(db, int(team_id))

    detail = {
        "incumbent": incumbent,
        "predecessor": predecessor,
        "heir_apparent": clock,
        "heir_origin": heir_origin,
        "heir_origin_team": heir_origin_team,
        "shoes_read": read,
        "shoes_tone": tone,
        "clock_confidence": clock_conf,
        "portal_chain": _portal_chain(predecessor, incumbent, heir_origin, heir_origin_team),
    }

    return {
        "player_external_id": incumbent.get("player_external_id"),
        "player_id": incumbent.get("player_id"),
        "team_id": int(team_id),
        "team_name": team_name,
        "season_year": int(season_year),
        "position_group": pos,
        "role_holder_usage": incumbent.get("usage"),
        "role_holder_stars": incumbent.get("stars"),
        "predecessor_external_id": (predecessor or {}).get("player_external_id"),
        "predecessor_name": (predecessor or {}).get("player_name"),
        "predecessor_stars": (predecessor or {}).get("stars"),
        "predecessor_usage": (predecessor or {}).get("usage"),
        "predecessor_fate": (predecessor or {}).get("fate"),
        "predecessor_dest_team": (predecessor or {}).get("dest_team"),
        "heir_external_id": (clock or {}).get("player_external_id"),
        "heir_name": (clock or {}).get("player_name"),
        "heir_stars": (clock or {}).get("stars"),
        "heir_origin": heir_origin,
        "heir_origin_team": heir_origin_team,
        "clock_score": (clock or {}).get("clock_score"),
        "shoes_read": read,
        "shoes_tone": tone,
        "confidence": confidence,
        "detail_json": json.dumps(detail, default=str),
    }


def _portal_chain(
    predecessor: dict[str, Any] | None,
    incumbent: dict[str, Any],
    heir_origin: str | None,
    heir_origin_team: str | None,
) -> dict[str, Any]:
    """The musical-chairs view: where the ghost went, where the incumbent came from."""
    return {
        "predecessor_left_to": (predecessor or {}).get("dest_team"),
        "predecessor_fate": (predecessor or {}).get("fate"),
        "incumbent_origin": heir_origin,
        "incumbent_came_from": heir_origin_team,
    }


# ---------------------------------------------------------------------------
# Enrich step — upsert player_succession for the season
# ---------------------------------------------------------------------------
def write_succession(
    db, season_year: int, position_groups: tuple[str, ...] = ("QB", "RB", "WR", "TE"),
) -> int:
    """Detect + upsert succession nodes for every team at each position.

    NON-critical enrich step (collect / non-critical build) — a failure here
    must never block the deploy, so the whole body is defensive. Returns the
    number of rows written. UNIQUE key is (team_id, position_group, season_year).
    """
    if db is None or season_year is None:
        return 0

    written = 0
    for pos in position_groups:
        pos_u = (pos or "").upper()
        if pos_u not in _ROLE_STAT:
            continue
        category, stat_type = _ROLE_STAT[pos_u]
        # Teams that fielded this role in the season (have any defining-stat row).
        team_rows = _safe_all(
            db,
            """
            select distinct team_id from player_season_stats
             where season_year = :s and category = :cat and stat_type = :stype
               and team_id is not null and stat_value_num is not null
            """,
            {"s": int(season_year), "cat": category, "stype": stat_type},
        )
        for tr in team_rows:
            team_id = _to_int(tr.get("team_id"))
            if team_id is None:
                continue
            try:
                node = detect_succession(db, team_id, pos_u, int(season_year))
            except Exception:
                node = None
            if node is None:
                continue
            try:
                _upsert_succession(db, node)
                written += 1
            except Exception:
                # Never let one bad row abort the batch.
                continue
    return written


def _upsert_succession(db, node: dict[str, Any]) -> None:
    """INSERT ... ON CONFLICT upsert into player_succession (UNIQUE team/pos/season)."""
    payload = {
        "player_external_id": node.get("player_external_id"),
        "player_id": node.get("player_id"),
        "team_id": node.get("team_id"),
        "team_name": node.get("team_name"),
        "season_year": node.get("season_year"),
        "position_group": node.get("position_group"),
        "role_holder_usage": node.get("role_holder_usage"),
        "role_holder_stars": node.get("role_holder_stars"),
        "predecessor_external_id": node.get("predecessor_external_id"),
        "predecessor_name": node.get("predecessor_name"),
        "predecessor_stars": node.get("predecessor_stars"),
        "predecessor_usage": node.get("predecessor_usage"),
        "predecessor_fate": node.get("predecessor_fate"),
        "predecessor_dest_team": node.get("predecessor_dest_team"),
        "heir_external_id": node.get("heir_external_id"),
        "heir_name": node.get("heir_name"),
        "heir_stars": node.get("heir_stars"),
        "heir_origin": node.get("heir_origin"),
        "heir_origin_team": node.get("heir_origin_team"),
        "clock_score": node.get("clock_score"),
        "shoes_read": node.get("shoes_read"),
        "shoes_tone": node.get("shoes_tone"),
        "confidence": node.get("confidence") if node.get("confidence") is not None else 0.0,
        "detail_json": node.get("detail_json"),
        "computed_at_utc": _now(),
    }
    db.execute(
        """
        insert into player_succession
            (player_external_id, player_id, team_id, team_name, season_year,
             position_group, role_holder_usage, role_holder_stars,
             predecessor_external_id, predecessor_name, predecessor_stars,
             predecessor_usage, predecessor_fate, predecessor_dest_team,
             heir_external_id, heir_name, heir_stars, heir_origin,
             heir_origin_team, clock_score, shoes_read, shoes_tone, confidence,
             detail_json, computed_at_utc)
        values
            (:player_external_id, :player_id, :team_id, :team_name, :season_year,
             :position_group, :role_holder_usage, :role_holder_stars,
             :predecessor_external_id, :predecessor_name, :predecessor_stars,
             :predecessor_usage, :predecessor_fate, :predecessor_dest_team,
             :heir_external_id, :heir_name, :heir_stars, :heir_origin,
             :heir_origin_team, :clock_score, :shoes_read, :shoes_tone, :confidence,
             :detail_json, :computed_at_utc)
        on conflict(team_id, position_group, season_year) do update set
            player_external_id      = excluded.player_external_id,
            player_id               = excluded.player_id,
            team_name               = excluded.team_name,
            role_holder_usage       = excluded.role_holder_usage,
            role_holder_stars       = excluded.role_holder_stars,
            predecessor_external_id = excluded.predecessor_external_id,
            predecessor_name        = excluded.predecessor_name,
            predecessor_stars       = excluded.predecessor_stars,
            predecessor_usage       = excluded.predecessor_usage,
            predecessor_fate        = excluded.predecessor_fate,
            predecessor_dest_team   = excluded.predecessor_dest_team,
            heir_external_id        = excluded.heir_external_id,
            heir_name               = excluded.heir_name,
            heir_stars              = excluded.heir_stars,
            heir_origin             = excluded.heir_origin,
            heir_origin_team        = excluded.heir_origin_team,
            clock_score             = excluded.clock_score,
            shoes_read              = excluded.shoes_read,
            shoes_tone              = excluded.shoes_tone,
            confidence              = excluded.confidence,
            detail_json             = excluded.detail_json,
            computed_at_utc         = excluded.computed_at_utc
        """,
        payload,
    )


# ---------------------------------------------------------------------------
# Render-path read — the cached SuccessionRead for a player
# ---------------------------------------------------------------------------
def fetch_succession_for_player(
    db, player_external_id: str, season_year: int,
) -> SuccessionRead | None:
    """Read player_succession for an INCUMBENT and return a typed SuccessionRead.

    Keyed on player_external_id (the stable cfbd id). Returns None when the
    player holds no detectable throne this season or the table is empty/absent.
    Never raises — this is on the (-Critical) render path.
    """
    if db is None or not player_external_id or season_year is None:
        return None
    row = _safe_one(
        db,
        """
        select position_group, predecessor_name, predecessor_stars,
               heir_name, heir_stars, shoes_read, shoes_tone, confidence,
               detail_json, role_holder_usage
          from player_succession
         where player_external_id = :ext and season_year = :s
         order by confidence desc
         limit 1
        """,
        {"ext": str(player_external_id), "s": int(season_year)},
    )
    if not row:
        return None

    # Reconstruct the clock line + clock confidence from detail_json.
    clock_line: str | None = None
    clock_conf = 0.0
    detail: dict[str, Any] = {}
    try:
        detail = json.loads(row.get("detail_json") or "{}")
    except Exception:
        detail = {}
    heir = detail.get("heir_apparent") or {}
    incumbent = detail.get("incumbent") or {}
    if heir.get("player_name"):
        clock_line = _clock_line(heir, incumbent)
        clock_conf = _to_float(detail.get("clock_confidence")) or 0.0

    # Drop the clock when its confidence is too thin to assert (doc 44 §9).
    if clock_conf < 0.4:
        clock_line = None

    return SuccessionRead(
        role=str(row.get("position_group") or ""),
        predecessor_name=row.get("predecessor_name"),
        predecessor_stars=_to_int(row.get("predecessor_stars")),
        heir_name=row.get("heir_name") if clock_line else None,
        heir_stars=_to_int(row.get("heir_stars")) if clock_line else None,
        shoes_read=row.get("shoes_read"),
        tone=row.get("shoes_tone"),
        clock_line=clock_line,
        confidence=_to_float(row.get("confidence")) or 0.0,
    )


__all__ = [
    "SuccessionRead",
    "detect_succession",
    "compute_throne_line",
    "fetch_succession_for_player",
    "write_succession",
]
