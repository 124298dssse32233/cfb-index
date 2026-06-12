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
    young non-holder) yields a heir CANDIDATE; whether a clock actually FIRES is
    a RELATIVE-THREAT decision (doc 59 §5, redesigned 2026-06-12), not the heir's
    absolute pedigree.

doc 59 §5 redesign (2026-06-12) — three cracks fixed:
  * (A/P0) RELATIVE-THREAT CLOCK. A clock fires only when the heir is a real talent
    (stars>=4 or a notable transfer) AND (the incumbent is not entrenched OR a real
    discourse competition exists). An entrenched, productive starter with a quiet
    backup => the clock is SUPPRESSED (heir dropped, frame ``entrenched-no-clock``).
    ``incumbent_entrenchment`` = f(production_pctl, confirmed-starter): HIGH if
    production_pctl>=70 or confirmed starter; LOW if <30/none; MEDIUM between.
  * (P1) DISCOURSE-COMPETITION GATE — heir BUZZ + incumbent<->heir CO-MENTION, never
    a keyword scan (a keyword scan gave 41 false hits for Carson Beck, doc 59 §5.1).
  * (B/P1) PREDECESSOR_BAND — the ghost's grade comes from their FINAL-SEASON
    production (player_season_stats + wepa + fate), NOT recruiting stars. A departed
    ghost has no current aura row, so aura is the wrong source (doc 59 §5.1).
  * (C/P1) VALENCE-TO-WRITER — ``suggested_frame`` / ``predecessor_band`` /
    ``threat_label`` / ``incumbent_entrenchment`` / ``suppress_clock`` /
    ``discourse_competition`` are computed, persisted in ``detail_json``, and surfaced
    on ``SuccessionRead`` (new fields, safe defaults — backward-compatible).
  * (P2) SEASON ROLL-FORWARD — if the role-season incumbent is DEPARTED for the
    upcoming season (``eligibility.is_departed``), the node is flagged so the 2026
    preview never frames the ghost as a returning starter; best-effort heir-> or
    depth-chart-> incumbent promotion is annotated in ``detail_json['rollforward']``.

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
    """Filling-the-Shoes + the Clock, deterministic (doc 44 + doc 59 §5).

    The doc-59 redesign (2026-06-12) adds *valence-to-writer* fields with safe
    defaults so the contract stays backward-compatible: existing callers
    (story_card.py, story_card_narrator.py, story_card_renderer.py) read only the
    original fields via getattr/_attr and never break when the new ones are absent.
    """

    role: str                        # position_group, e.g. "QB"
    predecessor_name: Optional[str]
    predecessor_stars: Optional[int]
    heir_name: Optional[str]
    heir_stars: Optional[int]
    shoes_read: Optional[str]        # downgrade|upgrade|continuity|leap_of_faith|low_bar
    tone: Optional[str]              # mourning|dread|hope|reverence|relief|suspense
    clock_line: Optional[str]        # "how many games until <heir> (4*) takes the job?"
    confidence: float = 0.0          # gated low when depth data is partial

    # --- doc 59 §5 valence-to-writer (NEW, safe defaults) --------------------
    suggested_frame: Optional[str] = None     # frame taxonomy (see _FRAME_*) — what the writer should reach for
    predecessor_band: Optional[str] = None    # elite|solid|poor — the ghost's FINAL-SEASON production grade
    threat_label: Optional[str] = None        # real|nominal|none — the relative heir threat
    incumbent_entrenchment: Optional[str] = None  # high|medium|low — why the clock fires or stays silent
    suppress_clock: bool = False              # True => the writer should drop the whole clock block
    discourse_competition: bool = False       # True => real heir-buzz / co-mention competition exists


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
# doc 59 §5 D-2 seeded constants — "what CFB fans actually want" (discourse-first,
# data-as-qualifier). Named + tunable; the discourse-first ORDERING is locked, the
# numbers are seeded from the live percentile distribution and may be retuned.
# ---------------------------------------------------------------------------
# Incumbent entrenchment bands from production_pctl (player_aura_weekly, last season).
_ENTRENCH_HIGH_PCTL = 70.0   # >= 70 (top third) => HIGH (entrenched, productive starter)
_ENTRENCH_LOW_PCTL = 30.0    # < 30 (or none) => LOW (unproven / open job)
ENTRENCH_HIGH = "high"
ENTRENCH_MEDIUM = "medium"
ENTRENCH_LOW = "low"

# A heir is a *real* talent (the precondition for ANY clock) at >= this star floor,
# OR as a notable transfer / top-class recruit. An unranked walk-on never starts a clock.
_HEIR_REAL_STARS = 4

# Discourse-competition floors (doc 59 §5.1): NOT a keyword count. Real competition =
# the heir generates meaningful OWN buzz AND/OR fans co-mention incumbent+heir together.
# Seeded so Keelon Russell (46 heir docs, 4 co-mentions) clears but Luke Nickel
# (16 docs, 2 co-mentions) and Shawqi Itraish (0 docs, 0 co-mentions) do not.
_COMP_HEIR_BUZZ_FLOOR = 25       # heir's own discourse-doc / mention count floor
_COMP_COMENTION_FLOOR = 3        # incumbent<->heir co-mention doc count floor
_COMP_HEIR_BUZZ_STRONG = 60      # heir buzz this high alone signals a real QB-room story

# Threat labels (the relative heir threat that reaches the writer).
THREAT_REAL = "real"
THREAT_NOMINAL = "nominal"
THREAT_NONE = "none"

# Predecessor-band production thresholds (the GHOST's FINAL-SEASON grade, NOT aura).
# production_pctl from player_aura_weekly is null for departed ghosts, so we grade
# from their last player_season_stats line + wepa + fate (doc 59 §5.1).
_PRED_BAND_ELITE_PCTL = 75.0     # final-season production_pctl >= 75 => elite (if an aura row survives)
_PRED_BAND_POOR_PCTL = 33.0      # bottom third => poor
PRED_BAND_ELITE = "elite"
PRED_BAND_SOLID = "solid"
PRED_BAND_POOR = "poor"

# suggested_frame taxonomy (doc 59 §5).
_FRAME_LEGEND = "live-up-to-a-legend"
_FRAME_ESCAPE_BUST = "escape-a-bust"
_FRAME_UPGRADE = "upgrade"
_FRAME_OPEN_COMP = "open-competition"
_FRAME_ENTRENCHED = "entrenched-no-clock"
_FRAME_FIRST_TIME = "first-time-starter"
_FRAME_CONTINUITY = "continuity"


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
# doc 59 §5 — relative threat, entrenchment, discourse-competition, predecessor band
# ---------------------------------------------------------------------------
def _production_pctl(db, player_id: int | None, season_year: int) -> float | None:
    """The player's production_pctl from player_aura_weekly for the given season.

    Latest week wins. Returns None when no (non-low-signal) aura row exists — note a
    DEPARTED ghost has NO current aura row, so this is null for most predecessors
    (use _predecessor_final_production for them, NOT this — doc 59 §5.1).
    """
    if player_id is None:
        return None
    row = _safe_one(
        db,
        """
        select production_pctl from player_aura_weekly
         where player_id = :pid and season_year = :s
           and production_pctl is not null
         order by week desc limit 1
        """,
        {"pid": int(player_id), "s": int(season_year)},
    )
    return _to_float(row.get("production_pctl")) if row else None


def _is_confirmed_2026_starter(db, player_id: int | None) -> bool:
    """True iff the player carries a 'confirmed' starter row in player_depth_chart_2026."""
    if player_id is None:
        return False
    row = _safe_one(
        db,
        """
        select 1 as ok from player_depth_chart_2026
         where player_id = :pid
           and (lower(coalesce(starter_status,'')) like '%start%'
                or lower(coalesce(confidence,'')) = 'confirmed')
         limit 1
        """,
        {"pid": int(player_id)},
    )
    return bool(row)


def _incumbent_entrenchment(
    db, incumbent_id: int | None, season_year: int, *, has_real_usage: bool,
) -> tuple[str, str]:
    """(entrenchment band, why) for the incumbent (doc 59 §5 D-2).

    HIGH   — returning starter with production_pctl >= 70 (top third) OR a confirmed
             2026 starter with real prior usage.
    MEDIUM — a starter, but new/unproven or mid production (30 <= pctl < 70).
    LOW    — unproven / open job (pctl < 30 or none).

    Discourse is the primary gate downstream; entrenchment is the data qualifier.
    """
    pctl = _production_pctl(db, incumbent_id, season_year)
    confirmed = _is_confirmed_2026_starter(db, incumbent_id)

    if pctl is not None and pctl >= _ENTRENCH_HIGH_PCTL:
        return (ENTRENCH_HIGH, f"returning starter, production_pctl {pctl:.0f} (top third)")
    if confirmed and has_real_usage:
        return (ENTRENCH_HIGH, "confirmed 2026 starter with prior usage")
    if pctl is not None and pctl >= _ENTRENCH_LOW_PCTL:
        return (ENTRENCH_MEDIUM, f"starter, mid production_pctl {pctl:.0f}")
    if pctl is not None:
        return (ENTRENCH_LOW, f"unproven, low production_pctl {pctl:.0f}")
    # No aura production signal at all: lean on usage as a weak qualifier.
    if has_real_usage:
        return (ENTRENCH_MEDIUM, "starter with usage but no production percentile")
    return (ENTRENCH_LOW, "no production signal / open job")


def _heir_buzz(db, heir_id: int | None) -> int:
    """The heir's OWN discourse buzz — the larger of (distinct tagged docs, aura
    mention_count). A real threat generates real conversation (doc 59 §5.1).

    NOT a keyword scan: a real heir has people *talking about him*.
    """
    if heir_id is None:
        return 0
    docs = _safe_one(
        db,
        "select count(distinct conversation_document_id) as c "
        "from conversation_document_targets where player_id = :pid",
        {"pid": int(heir_id)},
    )
    doc_n = _to_int((docs or {}).get("c")) or 0
    aura = _safe_one(
        db,
        "select mention_count from player_aura_weekly "
        "where player_id = :pid and mention_count is not null "
        "order by season_year desc, week desc limit 1",
        {"pid": int(heir_id)},
    )
    mc = _to_int((aura or {}).get("mention_count")) or 0
    return max(doc_n, mc)


def _comention_count(db, incumbent_id: int | None, heir_id: int | None) -> int:
    """Docs tagged to BOTH the incumbent and the heir (the QB-room co-mention).

    Fans writing the two names together = a genuine QB-room story (doc 59 §5.1).
    This is the co-mention half of the discourse-competition gate.
    """
    if incumbent_id is None or heir_id is None:
        return 0
    row = _safe_one(
        db,
        """
        select count(distinct a.conversation_document_id) as c
          from conversation_document_targets a
          join conversation_document_targets b
            on a.conversation_document_id = b.conversation_document_id
         where a.player_id = :inc and b.player_id = :heir
        """,
        {"inc": int(incumbent_id), "heir": int(heir_id)},
    )
    return _to_int((row or {}).get("c")) or 0


def _discourse_competition(
    db, incumbent_id: int | None, heir_id: int | None, season_year: int,
) -> tuple[bool, dict[str, int]]:
    """Does a REAL discourse competition exist between (incumbent, heir)?

    doc 59 §5.1 — NOT a keyword count (a naive 'battle/QB1/depth chart' scan gave 41
    false hits for Carson Beck). Real competition requires the heir to generate
    meaningful OWN buzz AND/OR fans to co-mention the two together:

      * heir buzz >= floor AND co-mention >= floor      (a genuine QB-room story), OR
      * heir buzz >= a STRONG floor alone               (a hyped heir who's all anyone
                                                          discusses, even if the tagger
                                                          under-links the co-mention).

    Returns (bool, {"heir_buzz", "comention"}) so the caller can persist the why.
    """
    buzz = _heir_buzz(db, heir_id)
    co = _comention_count(db, incumbent_id, heir_id)
    metrics = {"heir_buzz": buzz, "comention": co}
    if buzz >= _COMP_HEIR_BUZZ_STRONG:
        return (True, metrics)
    if buzz >= _COMP_HEIR_BUZZ_FLOOR and co >= _COMP_COMENTION_FLOOR:
        return (True, metrics)
    return (False, metrics)


def _heir_is_real_talent(heir: dict[str, Any] | None) -> bool:
    """A clock precondition: the heir is a real talent (doc 59 §5 D-2).

    True when stars >= 4 OR the heir arrived via the portal (a notable transfer).
    An unranked walk-on with no portal pedigree never starts a clock.
    """
    if not heir:
        return False
    stars = _to_int(heir.get("stars")) or 0
    if stars >= _HEIR_REAL_STARS:
        return True
    if (heir.get("origin") or heir.get("heir_origin")) == "portal":
        return True
    return False


def _predecessor_final_production(
    db, predecessor_id: int | None, role_season: int,
) -> dict[str, Any]:
    """The GHOST's final-season production grade (doc 59 §5.1).

    A departed predecessor has NO current player_aura_weekly row, so we CANNOT grade
    them from aura. Grade from their last player_season_stats line + wepa
    (player_value_metrics) instead. ``role_season`` is the season they last held the
    role (the prior season); we read their stats AT or BEFORE that season.

    Returns {"prod_pctl": float|None, "wepa": float|None, "usage": float|None}.
    prod_pctl is best-effort: if an aura row happens to survive for that season we use
    it, but the band logic falls back to fate+wepa when it's null.
    """
    out: dict[str, Any] = {"prod_pctl": None, "wepa": None, "usage": None}
    if predecessor_id is None:
        return out
    # If an aura row survives for the role season, take its production_pctl (rare for
    # ghosts but cheap to check). NOT the current aura row — scoped to the role season.
    out["prod_pctl"] = _production_pctl(db, predecessor_id, role_season)
    # wepa (passing/rushing/receiving) from player_value_metrics — the durable signal.
    wepa = _safe_one(
        db,
        """
        select max(metric_value) as wepa from player_value_metrics
         where player_id = :pid and season_year <= :s
           and lower(coalesce(metric_name,'')) like 'wepa%'
           and metric_value is not null
        """,
        {"pid": int(predecessor_id), "s": int(role_season)},
    )
    out["wepa"] = _to_float((wepa or {}).get("wepa"))
    return out


def _predecessor_band(
    db,
    predecessor: dict[str, Any] | None,
    role_season: int,
) -> str | None:
    """elite | solid | poor — the ghost's FINAL-SEASON production grade (doc 59 §5.1).

    Production-based, NOT recruiting-star-based. Fate dominates (drafted => elite,
    benched/bottom-third => poor); production_pctl / wepa / honors refine the middle.
    Returns None when there's no predecessor at all.
    """
    if not predecessor:
        return None
    fate = predecessor.get("fate")
    pid = _to_int(predecessor.get("player_id"))

    # Fate is the strongest production signal we have for a departed ghost.
    if fate == "drafted":
        return PRED_BAND_ELITE
    if fate == "benched":
        return PRED_BAND_POOR

    prod = _predecessor_final_production(db, pid, role_season)
    pctl = prod.get("prod_pctl")
    if pctl is not None:
        if pctl >= _PRED_BAND_ELITE_PCTL:
            return PRED_BAND_ELITE
        if pctl < _PRED_BAND_POOR_PCTL:
            return PRED_BAND_POOR
        return PRED_BAND_SOLID

    # No surviving aura percentile (the common ghost case). Lean on honors + wepa.
    if pid is not None:
        honor = _safe_one(
            db,
            """
            select 1 as ok from player_honors
             where player_id = :pid
               and (consensus_flag = 1 or unanimous_flag = 1
                    or lower(coalesce(honor_scope,'')) like '%national%'
                    or lower(coalesce(honor_scope,'')) like '%all-ameri%')
             limit 1
            """,
            {"pid": int(pid)},
        )
        if honor:
            return PRED_BAND_ELITE
    wepa = prod.get("wepa")
    if wepa is not None and wepa <= 0.0:
        return PRED_BAND_POOR
    # Default: a competent starter who graduated/transferred without elite markers.
    return PRED_BAND_SOLID


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
    predecessor_band: str | None = None,
) -> tuple[str, str, str]:
    """(read, tone, suggested_frame) — PRODUCTION-banded (doc 59 §5 crack B).

    The read is keyed off the predecessor's FINAL-SEASON production band
    (elite/solid/poor), NOT recruiting stars, so a weak ghost reads 'escape-a-bust'
    / relief and an elite ghost reads 'live-up-to-a-legend' / reverence.

    read  in {downgrade, upgrade, continuity, leap_of_faith, low_bar}
    tone  in {mourning, dread, hope, reverence, relief, suspense}
    frame in the _FRAME_* taxonomy (doc 59 §5).
    """
    inc_usage = _to_float(incumbent.get("usage")) or 0.0

    # First-time starter / leap of faith: the incumbent is an unproven freshman or a
    # true-freshman arrival stepping in.
    if heir_origin == "true_freshman" or (incumbent.get("class_year") == "1"):
        return ("leap_of_faith", "hope", _FRAME_FIRST_TIME)

    if predecessor is None:
        # No ghost to measure against — continuity if productive, else a first start.
        if inc_usage > 0:
            return ("continuity", "reverence", _FRAME_CONTINUITY)
        return ("leap_of_faith", "suspense", _FRAME_FIRST_TIME)

    pred_fate = predecessor.get("fate")
    band = predecessor_band  # elite | solid | poor (production-based, doc 59 §5.1)

    # POOR ghost — the room is glad to escape him. Relief, not reverence.
    if band == PRED_BAND_POOR or pred_fate == "benched":
        return ("low_bar", "relief", _FRAME_ESCAPE_BUST)

    # ELITE ghost — a legend to live up to. Reverence; mourning if he was drafted away.
    if band == PRED_BAND_ELITE or pred_fate == "drafted":
        tone = "mourning" if pred_fate == "drafted" else "reverence"
        return ("continuity", tone, _FRAME_LEGEND)

    # SOLID ghost (or unknown band) — a same-caliber, bland handoff. Continuity.
    return ("continuity", "reverence", _FRAME_CONTINUITY)


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

    # --- Predecessor band (doc 59 §5 crack B) — production-based, NOT stars. The
    # ghost's grade comes from their FINAL-SEASON (= prior) production line. ------
    predecessor_band = _predecessor_band(db, predecessor, int(season_year) - 1)
    if predecessor is not None:
        predecessor["band"] = predecessor_band

    # --- The Clock CANDIDATE — the most threatening young talent below the
    # incumbent. Exclude the predecessor (the ghost) so a departed starter never
    # resurfaces as his own replacement. This is only a CANDIDATE; whether a clock
    # actually FIRES is decided by the relative-threat gate below. -----------------
    exclude: set[int] = set()
    if predecessor and predecessor.get("player_id") is not None:
        exclude.add(int(predecessor["player_id"]))
    clock = _clock_candidate(
        db, int(team_id), pos, incumbent.get("player_id"), int(season_year),
        exclude_ids=frozenset(exclude),
    )

    # --- Relative-threat clock gate (doc 59 §5 crack A — THE P0 FIX) --------------
    # OLD behaviour scored the heir ALONE and fired a clock against entrenched stars.
    # NEW: threat is RELATIVE to incumbent entrenchment, and discourse is the truth
    # test. Suppress the clock for an entrenched, productive starter with a quiet
    # backup; fire it only for a real heir against a beatable starter OR when fans
    # are genuinely talking about a QB-room competition.
    has_real_usage = (_to_float(incumbent.get("usage")) or 0.0) > 0.0
    entrenchment, entrench_why = _incumbent_entrenchment(
        db, incumbent.get("player_id"), int(season_year), has_real_usage=has_real_usage,
    )

    heir_real = _heir_is_real_talent(clock)
    competition, comp_metrics = _discourse_competition(
        db, incumbent.get("player_id"), (clock or {}).get("player_id"), int(season_year),
    )

    # Threat label (reaches the writer): real only when the heir is a real talent AND
    # (the incumbent is beatable OR fans are competing over the room).
    if not clock or not clock.get("player_name"):
        threat_label = THREAT_NONE
    elif heir_real and (entrenchment != ENTRENCH_HIGH or competition):
        threat_label = THREAT_REAL
    elif heir_real:
        threat_label = THREAT_NOMINAL  # real talent, but entrenched + no chatter
    else:
        threat_label = THREAT_NONE

    # Suppress decision: a clock fires ONLY when the heir is real AND
    # (entrenchment != HIGH OR a real discourse competition exists). Otherwise the
    # clock is suppressed — heir_name/clock dropped, frame => entrenched-no-clock.
    fire_clock = bool(
        clock and clock.get("player_name") and heir_real
        and (entrenchment != ENTRENCH_HIGH or competition)
    )
    suppress_clock = not fire_clock

    # --- Filling-the-Shoes read (production-banded) + base frame ------------------
    read, tone, base_frame = _shoes_read(incumbent, predecessor, heir_origin, predecessor_band)

    # --- suggested_frame: the clock decision overrides the base read frame --------
    if fire_clock:
        suggested_frame = _FRAME_OPEN_COMP if competition else _FRAME_UPGRADE
    elif suppress_clock and (clock and clock.get("player_name")):
        # We HAD a candidate heir but the gate suppressed the clock — the entrenched
        # star with a quiet backup. This is the Beck/Chambliss case.
        suggested_frame = _FRAME_ENTRENCHED
    else:
        suggested_frame = base_frame

    # When the clock is suppressed, drop the heir from the persisted node so the
    # render path can't surface "pushed by <backup>" against an entrenched star.
    fired = clock if fire_clock else None

    # Confidence: full for QB/RB/WR/TE; dampened for everything else; further
    # dampened when a FIRED clock leans only on the roster fallback (no depth data).
    base_conf = 0.85 if pos in _FULL_CONFIDENCE_POS else 0.4
    if fired is None:
        clock_conf = 0.0
    elif fired.get("depth_confidence") is None:
        clock_conf = 0.45  # roster-only clock — keep node confident, flag clock soft
    elif fired.get("depth_confidence") == "confirmed":
        clock_conf = 0.8
    else:
        clock_conf = 0.6
    confidence = round(base_conf, 4)

    team_name = _team_name(db, int(team_id))

    detail = {
        "incumbent": incumbent,
        "predecessor": predecessor,
        "predecessor_band": predecessor_band,
        "heir_apparent": fired,                 # only the FIRED heir survives here
        "heir_candidate": clock,                # the raw candidate (context, not asserted)
        "heir_origin": heir_origin,
        "heir_origin_team": heir_origin_team,
        "shoes_read": read,
        "shoes_tone": tone,
        "suggested_frame": suggested_frame,
        "threat_label": threat_label,
        "incumbent_entrenchment": entrenchment,
        "entrenchment_why": entrench_why,
        "discourse_competition": competition,
        "competition_metrics": comp_metrics,
        "suppress_clock": suppress_clock,
        "incumbent_departed": False,            # set true by the roll-forward step below
        "clock_confidence": clock_conf,
        "portal_chain": _portal_chain(predecessor, incumbent, heir_origin, heir_origin_team),
    }

    node = {
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
        # Only the FIRED heir is persisted to the heir_* columns — a suppressed
        # backup is not the player's heir-apparent.
        "heir_external_id": (fired or {}).get("player_external_id"),
        "heir_name": (fired or {}).get("player_name"),
        "heir_stars": (fired or {}).get("stars"),
        "heir_origin": heir_origin,
        "heir_origin_team": heir_origin_team,
        "clock_score": (fired or {}).get("clock_score"),
        "shoes_read": read,
        "shoes_tone": tone,
        "confidence": confidence,
        "detail_json": None,  # filled after the roll-forward step
    }

    # --- Season roll-forward (doc 59 §5 crack / P2 — the 2026 preview) ------------
    # If the 2025 incumbent is DEPARTED for the upcoming season, they must NOT be
    # framed as a returning 2026 starter — they are the GHOST/predecessor. Flag the
    # node so the card never previews a departed player as returning. Best-effort
    # heir->incumbent promotion is annotated in detail for the downstream packet.
    _apply_season_rollforward(db, node, detail, int(season_year))

    node["detail_json"] = json.dumps(detail, default=str)
    return node


def _depth_chart_2026_starter(db, team_id: int, position_group: str) -> dict[str, Any] | None:
    """The projected/confirmed 2026 starter for (team, position) from the depth chart.

    Used by the season roll-forward to promote a heir into the 2026 incumbent slot
    when last year's starter has departed. Team-scoped via roster_entries because no
    2026 roster exists yet. Returns the best (lowest slot_rank, confirmed > projected)
    same-position player, or None. Never raises.
    """
    pos = (position_group or "").upper()
    rows = _safe_all(
        db,
        """
        select distinct d.player_id, d.slot_rank, d.starter_status, d.confidence
          from player_depth_chart_2026 d
          join roster_entries r on r.player_id = d.player_id and r.team_id = :tid
         where d.position_group = :pos
        """,
        {"tid": int(team_id), "pos": pos},
    )
    if not rows:
        return None

    def _rank(row: dict[str, Any]) -> tuple[int, int]:
        conf = str(row.get("confidence") or "").lower()
        conf_rank = 0 if conf == "confirmed" else 1
        slot = _to_int(row.get("slot_rank"))
        slot = slot if slot is not None else 99
        return (conf_rank, slot)

    rows.sort(key=_rank)
    top = rows[0]
    pid = _to_int(top.get("player_id"))
    if pid is None:
        return None
    name_row = _safe_one(
        db, "select full_name from players where player_id = :pid", {"pid": int(pid)},
    )
    return {
        "player_id": pid,
        "player_external_id": _resolve_external_id(db, pid),
        "player_name": str(name_row["full_name"]) if name_row and name_row.get("full_name") else None,
        "starter_status": top.get("starter_status"),
        "confidence": top.get("confidence"),
    }


def _apply_season_rollforward(
    db, node: dict[str, Any], detail: dict[str, Any], role_season: int,
) -> None:
    """Mark a departed-incumbent node so the 2026 preview never frames the ghost as
    a returning starter (doc 59 §5 / P2). Best-effort heir->incumbent promotion.

    Uses ``eligibility.is_departed`` (the prior-phase classifier) on the incumbent's
    numeric player_id. If DEPARTED for the upcoming season, the node is flagged and
    the would-be 2026 starter (the fired heir, or the player_depth_chart_2026 starter
    for this team/position) is annotated as the new incumbent. NEVER raises — the
    whole body is defensive so a missing eligibility module / table can't break the
    enrich step or the render path.
    """
    try:
        from . import eligibility  # local import: keep module import-time deps minimal
    except Exception:
        return

    inc_pid = _to_int(node.get("player_id"))
    if inc_pid is None:
        return

    upcoming = int(role_season) + 1
    try:
        status = eligibility.classify_2026_status(
            db, inc_pid, upcoming_season=upcoming, last_completed=int(role_season),
        )
    except Exception:
        status = None
    departed = bool(status and status.get("status") == eligibility.DEPARTED)

    detail["incumbent_departed"] = departed
    detail["incumbent_eligibility"] = status or {}
    node["incumbent_departed"] = departed  # convenience denorm for the packet/selector

    if not departed:
        return

    # The departed incumbent becomes the GHOST for the upcoming season. Best-effort:
    # promote the fired heir (if any), else the 2026 depth-chart starter, into the
    # new-incumbent slot. We do NOT mutate the persisted incumbent columns (those
    # remain the role-season role-holder, the table's contract); we annotate detail so
    # the forward packet / narrator can recast the ghost without a schema change.
    new_inc = detail.get("heir_apparent") or detail.get("heir_candidate")
    if not (new_inc and new_inc.get("player_name")):
        new_inc = _depth_chart_2026_starter(
            db, int(node.get("team_id")), str(node.get("position_group") or ""),
        )
    detail["rollforward"] = {
        "ghost_player_id": inc_pid,
        "ghost_name": (detail.get("incumbent") or {}).get("player_name"),
        "ghost_reason": (status or {}).get("reason"),
        "new_incumbent": new_inc or None,
        "upcoming_season": upcoming,
    }
    # The ghost is no longer a returning starter — reframe accordingly so the card
    # never previews a departed player as QB1.
    node["suggested_frame_note"] = "incumbent-departed-recast-as-ghost"

    # The "How many games until <heir> takes the job from <incumbent>?" clock is a
    # RELATIVE-THREAT framing: it asserts the heir is pushing a SITTING starter. Once
    # that starter is DEPARTED (NFL/transfer/graduated), the premise is false — there
    # is no job to take from him and the heir has, if anything, already inherited it
    # (annotated as ``rollforward.new_incumbent``). Firing the clock here previews a
    # departed player as the contested incumbent (e.g. "until Keelon Russell takes the
    # job from Ty Simpson" after Simpson was a R1 pick). Suppress it and strip the
    # heir_* columns so the render path (fetch_succession_for_player) cannot rebuild
    # the contradictory clock line. The forward narrator uses rollforward.new_incumbent
    # to frame "the job is now <heir>'s", not a countdown against a ghost.
    detail["suppress_clock"] = True
    detail["heir_apparent"] = None
    detail["clock_confidence"] = 0.0
    detail["suppress_reason"] = "incumbent-departed"
    if detail.get("suggested_frame") in (_FRAME_OPEN_COMP, _FRAME_UPGRADE):
        detail["suggested_frame"] = _FRAME_FIRST_TIME
    node["heir_external_id"] = None
    node["heir_name"] = None
    node["heir_stars"] = None
    node["clock_score"] = None


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

    # Reconstruct the clock line + clock confidence + valence from detail_json.
    clock_line: str | None = None
    clock_conf = 0.0
    detail: dict[str, Any] = {}
    try:
        detail = json.loads(row.get("detail_json") or "{}")
    except Exception:
        detail = {}
    heir = detail.get("heir_apparent") or {}
    incumbent = detail.get("incumbent") or {}

    # doc 59 §5 valence — read from detail with safe defaults (old rows lack these).
    suppress_clock = bool(detail.get("suppress_clock"))
    suggested_frame = detail.get("suggested_frame")
    predecessor_band = detail.get("predecessor_band")
    threat_label = detail.get("threat_label")
    entrenchment = detail.get("incumbent_entrenchment")
    competition = bool(detail.get("discourse_competition"))
    incumbent_departed = bool(detail.get("incumbent_departed"))

    # The clock line is only built for a FIRED, surviving heir. suppress_clock makes
    # the suppression explicit even for legacy rows where heir_apparent lingered.
    if heir.get("player_name") and not suppress_clock:
        clock_line = _clock_line(heir, incumbent)
        clock_conf = _to_float(detail.get("clock_confidence")) or 0.0

    # Drop the clock when its confidence is too thin to assert (doc 44 §9).
    if clock_conf < 0.4:
        clock_line = None

    show_heir = bool(clock_line and not suppress_clock)

    return SuccessionRead(
        role=str(row.get("position_group") or ""),
        predecessor_name=row.get("predecessor_name"),
        predecessor_stars=_to_int(row.get("predecessor_stars")),
        heir_name=row.get("heir_name") if show_heir else None,
        heir_stars=_to_int(row.get("heir_stars")) if show_heir else None,
        shoes_read=row.get("shoes_read"),
        tone=row.get("shoes_tone"),
        clock_line=clock_line if show_heir else None,
        confidence=_to_float(row.get("confidence")) or 0.0,
        # doc 59 §5 valence-to-writer (safe defaults preserve backward compat)
        suggested_frame=suggested_frame,
        predecessor_band=predecessor_band,
        threat_label=threat_label,
        incumbent_entrenchment=entrenchment,
        suppress_clock=suppress_clock,
        discourse_competition=competition,
    )


__all__ = [
    "SuccessionRead",
    "detect_succession",
    "compute_throne_line",
    "fetch_succession_for_player",
    "write_succession",
]
