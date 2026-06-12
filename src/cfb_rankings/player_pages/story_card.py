"""Player Story Card ("Dossier Noir") — the ORCHESTRATOR.

Top-of-page narrative crown for the player page. This module is the public
entry point ``reporting.py`` calls; it owns the contract dataclasses, resolves
the stable ``player_external_id`` internally, calls the deterministic detectors
(succession + fan-ledgers), pulls the structured facts, selects the BAN (the one
big honest number), picks the lead ledger + the dominant fan take, composes ONE
coherent frame with variable CONTENT slots, applies the four-rung degradation
ladder, and hands a fully-built ``StoryCard`` to the pure renderer.

Specs:
  - doc 49 §5  — the card data contract (the dataclasses below).
  - doc 48     — the degradation ladder (full -> reduced -> low-data -> omit).
  - doc 42     — the engine (composition by content, two registers, salience,
                 editorial stance: COMPILE, do not adjudicate; do-not-amplify).
  - doc 43     — the content model (ledgers, ghosts/clock, BAN as narrative).
  - doc 41 §5/§6 — the stats-strip fallback + the BAN honesty gate.

THIS PHASE IS DETERMINISTIC ONLY. ZERO LLM / Ollama / network. The
confident-narrator prose is a later phase (doc 49 §7 step 3); where the card
would otherwise need prose we compose deterministic templated copy from
structured facts + the already-computed discourse signals (the same publishable
template mode the existing narrative/signature-story generators use).

Editorial stance honored everywhere: fan takes are attributed to the fanbase
("fans frame it as..."), never the site's own opinion; the gate is
representativeness, not truth; the C7 do-not-amplify floor (unverified
criminal/legal/medical allegations, identity pile-ons, doxxing) is enforced
upstream in the ledger detector (toxicity gate) and never re-surfaced here.

Stable key: ALL new narrative state keys on ``player_external_id`` = the cfbd
athlete id (``player_source_ids.source_player_id`` WHERE ``source_name='cfbd'``),
the linkrot anchor per ``src/cfb_rankings/player_id_anchor.py``. ``roster_entries``
has NO ``external_id`` column — resolve via ``player_source_ids``. The numeric
``player_id`` is carried only as a convenience denorm.

NEVER raises into the page. ``build_card`` (the render entry) returns "" on any
failure, mirroring the new_aura_html / new_in_their_words_html "" pattern.

Public API:
    @dataclass Receipt / Ban / DominantTake / SuccessionRead / StoryCard
    build_card(db, player_id, season_year, position=None, *, as_of_date=None) -> str
    build_card_payload(db, player_id, season_year, position=None, *, as_of_date=None) -> StoryCard | None
    resolve_external_id(db, player_id) -> str | None
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from .ledgers import fetch_ledger_lead
from .story_card_renderer import render_story_card
from .succession import SuccessionRead, fetch_succession_for_player


# ===========================================================================
# The card data contract (doc 49 §5) — verbatim from the pinned manifest.
# ===========================================================================
@dataclass
class Receipt:
    """A hoverable/tappable source marker pointing at the DB origin (doc 41 §1.3)."""
    table: str                       # e.g. "player_value_metrics"
    detail: str                      # human label, e.g. "via your WEPA model · 2025"
    url: Optional[str] = None        # source_url for discourse/canon claims; None for structured


@dataclass
class Ban:
    """The single big honest number — number welded to label (doc 41 §6)."""
    number: str                      # rendered string, e.g. "No.1" or "+0.51"
    label: str                       # ALWAYS present; never a bare number, e.g. "RUSHING VALUE · P4 QBs"
    receipt: Receipt
    kind: str = "rank"               # "rank" (spring-settle) | "magnitude" (count-up) — drives motion


@dataclass
class DominantTake:
    """Confident-compiler fan take, attributed to the fanbase (doc 42 §1, doc 49 C1).
    State plainly with conviction; dissent shown as a labeled minority."""
    text: str                        # "Tennessee fans overwhelmingly call it a betrayal"
    confidence: float                # 0..1 -> drives the confidence meter band
    source_count: int                # independent origins behind the meta-claim
    minority_take: Optional[str] = None   # the labeled dissent, or None if the room is one-sided


@dataclass
class StoryCard:
    """The card data contract (doc 49 §5). Every render/compute path degrades to
    an all-defaults card with tier='stats-strip' and fallback_reason set — never raises."""
    player_external_id: str
    season: int
    as_of_date: str
    tier: str = "stats-strip"        # "narrative" | "stats-strip" (low-data §5)
    # narrative-only fields (None on the stats-strip path):
    logline: Optional[str] = None
    why_now: Optional[str] = None
    body: Optional[str] = None       # 6-beat recap (deterministic templated copy in v1)
    kicker: Optional[str] = None
    chapter_label: Optional[str] = None
    chapter_number: Optional[int] = None
    ban: Optional[Ban] = None
    dominant_take: Optional[DominantTake] = None
    ledger_lead: Optional[str] = None     # hope|grievance|belonging|judgment|grudge
    succession: Optional[SuccessionRead] = None
    tension_text: Optional[str] = None
    archetype_slug: Optional[str] = None  # 'narr:transfer-saga'
    tier_rail: str = "t3"            # 's'|'t1'|'t2'|'t3' -> left-rail color (doc 41 §1 tier-is-texture)
    key_stat_chips: list[dict] = field(default_factory=list)  # [{"value":"1,928","label":"PASS YDS"}]
    citations: list[Receipt] = field(default_factory=list)
    composition: list[str] = field(default_factory=list)      # ordered module slugs the engine chose
    fallback_reason: Optional[str] = None                     # set when tier dropped (doc 48 ladder)
    # --- presentation-only fields the pure renderer reads via duck-typed getattr
    #     (NOT part of the doc-49 contract; populated by the orchestrator so the
    #     renderer needs no DB access). All optional / degrade to "".
    player_name: Optional[str] = None
    identity_meta: Optional[str] = None   # "QB · Tennessee · Sr · #15"
    team_color: Optional[str] = None      # strict #hex; renderer drops anything unsafe
    fallback_rung: Optional[str] = None   # 'full'|'reduced'|'low-data'|'omit' (doc 48 §3)


# Re-export SuccessionRead so callers/tests can import the whole contract from
# this one module (it is defined in succession.py to keep that module
# self-contained; the contract lives here per doc 49 §5).
__all__ = [
    "Receipt",
    "Ban",
    "DominantTake",
    "SuccessionRead",
    "StoryCard",
    "build_card",
    "build_card_payload",
    "resolve_external_id",
]


# ===========================================================================
# Tunables (doc 48 ladder + doc 42 representativeness floor).
# ===========================================================================
LEDGERS = ("hope", "grievance", "belonging", "judgment", "grudge")

# BAN honesty gate (doc 41 §6). A candidate below these is disqualified, not
# down-weighted; if nothing clears, the card simply has no BAN.
_BAN_MIN_COHORT = 30          # aura cohort_size floor
_BAN_MIN_PLAYS = 50           # WEPA / usage sample floor

# Star -> rail tier mapping (doc 41 tier-is-texture). Pedigree is the cheapest
# deterministic proxy for "how loud is this player's lane" in the offseason.
_STAR_RAIL = {5: "s", 4: "t1", 3: "t2"}


# ===========================================================================
# Small safe helpers — every query is wrapped so a missing table/column can
# never raise into the page.
# ===========================================================================
def _safe_one(db, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return db.query_one(sql, params)
    except Exception:
        return None


def _safe_all(db, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return db.query_all(sql, params) or []
    except Exception:
        return []


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


def _today() -> str:
    return _dt.date.today().isoformat()


# class_year codes ('1'..'6') -> readable label for the identity meta.
_CLASS_LABEL = {"1": "Fr", "2": "So", "3": "Jr", "4": "Sr", "5": "Sr", "6": "Sr"}


# ===========================================================================
# Stable-key resolution (the linkrot anchor).
# ===========================================================================
def resolve_external_id(db, player_id: int) -> str | None:
    """cfbd stable athlete id for a numeric player_id (doc 46 linkrot anchor).

    SELECT source_player_id FROM player_source_ids
     WHERE player_id=:pid AND source_name='cfbd'.
    roster_entries has NO external_id; this is the only anchor. Returns None when
    the player has no cfbd mapping (the card then degrades to omit/strip).
    """
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


# ===========================================================================
# Identity + structured facts (doc 48 identity-anchor + key-stat rows).
# ===========================================================================
def _fetch_identity(db, player_id: int, season_year: int, position: str | None) -> dict[str, Any]:
    """Name, position, team, class, jersey — best-effort; never raises.

    position from player_season_stats is the per-season truth (players.position
    is sparse/wrong); the caller's `position` is trusted first.
    """
    out: dict[str, Any] = {
        "full_name": None,
        "position": (position or "").strip().upper() or None,
        "team_name": None,
        "team_id": None,
        "class_year": None,
        "jersey": None,
        "team_color": None,
    }
    nm = _safe_one(db, "select full_name from players where player_id = :pid", {"pid": int(player_id)})
    if nm and nm.get("full_name"):
        out["full_name"] = str(nm["full_name"])

    # Per-season team + position from the stat rows (authoritative for the season).
    pss = _safe_one(
        db,
        """
        select team_name, team_id, position
          from player_season_stats
         where player_id = :pid and season_year = :s
         order by week desc limit 1
        """,
        {"pid": int(player_id), "s": int(season_year)},
    )
    if pss:
        if pss.get("team_name"):
            out["team_name"] = str(pss["team_name"])
        out["team_id"] = _to_int(pss.get("team_id"))
        if not out["position"] and pss.get("position"):
            out["position"] = str(pss["position"]).strip().upper() or None

    # Roster row for class/jersey/team fallback.
    re_row = _safe_one(
        db,
        """
        select team_id, class_year, jersey, position
          from roster_entries
         where player_id = :pid
         order by season_year desc limit 1
        """,
        {"pid": int(player_id)},
    )
    if re_row:
        if out["team_id"] is None:
            out["team_id"] = _to_int(re_row.get("team_id"))
        if re_row.get("class_year"):
            out["class_year"] = _CLASS_LABEL.get(str(re_row["class_year"]).strip(), None)
        if re_row.get("jersey") not in (None, ""):
            out["jersey"] = str(re_row["jersey"]).strip()
        if not out["position"] and re_row.get("position"):
            out["position"] = str(re_row["position"]).strip().upper() or None

    if out["team_id"] is not None and out["team_name"] is None:
        t = _safe_one(
            db, "select canonical_name from teams where team_id = :tid", {"tid": out["team_id"]}
        )
        if t and t.get("canonical_name"):
            out["team_name"] = str(t["canonical_name"])

    return out


def _identity_meta(ident: dict[str, Any]) -> str:
    """'QB · Tennessee · Sr · #15' — only the parts we actually have."""
    bits: list[str] = []
    if ident.get("position"):
        bits.append(str(ident["position"]))
    if ident.get("team_name"):
        bits.append(str(ident["team_name"]))
    if ident.get("class_year"):
        bits.append(str(ident["class_year"]))
    jersey = ident.get("jersey")
    if jersey:
        j = str(jersey).lstrip("#")
        if j:
            bits.append(f"#{j}")
    return " · ".join(bits)


def _fetch_recruiting(db, player_id: int) -> dict[str, Any] | None:
    return _safe_one(
        db,
        """
        select stars, rating, national_rank, season_year
          from player_recruiting_profiles
         where player_id = :pid and stars is not null
         order by season_year desc, stars desc limit 1
        """,
        {"pid": int(player_id)},
    )


def _fetch_key_stats(db, player_id: int, season_year: int, position: str | None) -> list[dict[str, str]]:
    """Up to three real season-total stat chips for the player's position.

    Season totals live with week=16/21 + season_type='both'; aggregate with
    MAX(stat_value_num) (do NOT SUM the cumulative rows, do NOT filter week IS NULL).
    Returns [] when no stats exist (the strip then shows the no-signal note).
    """
    pos = (position or "").strip().upper()
    # (category, stat_type, label) chip recipe per position family.
    recipes: list[tuple[str, str, str]] = []
    if pos == "QB":
        recipes = [
            ("passing", "YDS", "PASS YDS"),
            ("passing", "TD", "PASS TD"),
            ("rushing", "YDS", "RUSH YDS"),
        ]
    elif pos in ("RB", "FB"):
        recipes = [
            ("rushing", "YDS", "RUSH YDS"),
            ("rushing", "TD", "RUSH TD"),
            ("rushing", "CAR", "CARRIES"),
        ]
    elif pos in ("WR", "TE"):
        recipes = [
            ("receiving", "YDS", "REC YDS"),
            ("receiving", "REC", "REC"),
            ("receiving", "TD", "REC TD"),
        ]
    else:
        # Defense / specialists / unknown — surface tackles then a generic line.
        recipes = [
            ("defensive", "TOT", "TACKLES"),
            ("defensive", "SACKS", "SACKS"),
            ("defensive", "INT", "INT"),
        ]

    chips: list[dict[str, str]] = []
    for category, stat_type, label in recipes:
        row = _safe_one(
            db,
            """
            select max(stat_value_num) as v
              from player_season_stats
             where player_id = :pid and season_year = :s
               and category = :cat and stat_type = :stype
               and stat_value_num is not null
            """,
            {"pid": int(player_id), "s": int(season_year), "cat": category, "stype": stat_type},
        )
        v = _to_float((row or {}).get("v"))
        if v is None:
            continue
        chips.append({"value": _fmt_stat(v), "label": label})
        if len(chips) >= 3:
            break
    return chips


def _fmt_stat(v: float) -> str:
    """Thousands-separated int when whole; one decimal otherwise."""
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    return f"{v:,.1f}"


# ===========================================================================
# BAN selection (doc 41 §6) — the single most surprising-yet-honest true number.
# Candidate pool (deterministic v1): aura perception/production gap, WEPA value,
# recruiting rank. Each is honesty-gated; if none clears, there is no BAN.
# ===========================================================================
def _select_ban(db, player_id: int, season_year: int, position: str | None) -> Ban | None:
    candidates: list[tuple[float, Ban]] = []

    # --- Candidate A: aura perception↔production gap (the tension-as-number) ---
    aura = _safe_one(
        db,
        """
        select perception_pctl, production_pctl, cohort_size, production_plays, week
          from player_aura_weekly
         where player_id = :pid and season_year = :s
         order by week desc limit 1
        """,
        {"pid": int(player_id), "s": int(season_year)},
    )
    if aura:
        perc = _to_float(aura.get("perception_pctl"))
        prod = _to_float(aura.get("production_pctl"))
        cohort = _to_int(aura.get("cohort_size")) or 0
        plays = _to_int(aura.get("production_plays")) or 0
        # honesty gate: real cohort + real sample.
        if perc is not None and prod is not None and cohort >= _BAN_MIN_COHORT:
            gap = prod - perc
            if abs(gap) >= 12.0 and plays >= _BAN_MIN_PLAYS:
                sign = "+" if gap >= 0 else "-"
                label = (
                    "PRODUCES ABOVE PERCEPTION" if gap >= 0 else "PERCEPTION ABOVE TAPE"
                )
                surprise = min(1.0, abs(gap) / 50.0)
                candidates.append((
                    surprise,
                    Ban(
                        number=f"{sign}{abs(int(round(gap)))}",
                        label=f"{label} · PCTL GAP",
                        receipt=Receipt(
                            table="player_aura_weekly",
                            detail=f"perception vs production percentile · {season_year}",
                        ),
                        kind="magnitude",
                    ),
                ))

    # --- Candidate B: WEPA value (the respect-gap / production magnitude) ---
    wepa = _safe_all(
        db,
        """
        select metric_name, metric_value, plays
          from player_value_metrics
         where player_id = :pid and season_year = :s
           and metric_name in ('wepa_passing','wepa_rushing')
        """,
        {"pid": int(player_id), "s": int(season_year)},
    )
    best_wepa: tuple[float, str, int] | None = None
    for m in wepa:
        val = _to_float(m.get("metric_value"))
        plays = _to_int(m.get("plays")) or 0
        if val is None or plays < _BAN_MIN_PLAYS:
            continue
        if best_wepa is None or abs(val) > abs(best_wepa[0]):
            best_wepa = (val, str(m.get("metric_name") or ""), plays)
    if best_wepa is not None:
        val, mname, plays = best_wepa
        kind_word = "PASSING" if "pass" in mname else "RUSHING"
        sign = "+" if val >= 0 else ""
        surprise = min(1.0, abs(val) / 1.0)  # WEPA is roughly -1..1 scale
        candidates.append((
            0.6 * surprise + 0.2,  # slightly behind a strong aura gap when both exist
            Ban(
                number=f"{sign}{val:.2f}",
                label=f"{kind_word} VALUE · WEPA",
                receipt=Receipt(
                    table="player_value_metrics",
                    detail=f"via your WEPA model · {season_year} · {plays} plays",
                ),
                kind="magnitude",
            ),
        ))

    # --- Candidate C: recruiting national rank (Hope register, offseason-honest) ---
    rec = _fetch_recruiting(db, player_id)
    if rec:
        nat = _to_int(rec.get("national_rank"))
        stars = _to_int(rec.get("stars"))
        if nat is not None and 0 < nat <= 500:
            # rarer (lower rank) = higher surprise.
            surprise = max(0.0, 1.0 - (nat / 500.0))
            star_tag = f"{stars}★ · " if stars else ""
            candidates.append((
                0.45 * surprise,  # pedigree is the weakest BAN; loses to live production
                Ban(
                    number=f"No.{nat}",
                    label=f"{star_tag}NATIONAL RECRUIT",
                    receipt=Receipt(
                        table="player_recruiting_profiles",
                        detail="recruiting national rank",
                    ),
                    kind="rank",
                ),
            ))

    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    return candidates[0][1]


# ===========================================================================
# Lead ledger + the dominant fan take (doc 42 §1 — COMPILE, attribute, meter).
# ===========================================================================
# Templated, attributed phrasings per ledger + direction. Deterministic copy
# (the LLM confident narrator is a later phase). Always attributed to the
# fanbase ("fans frame it as..."), never the site's opinion.
def _dominant_take_text(ledger: str, direction: str | None, fanbase: str | None) -> str:
    who = f"{fanbase} fans" if fanbase else "Fans"
    rival_who = "Rival fans"
    d = (direction or "").lower()
    if ledger == "hope":
        return f"{who} frame him as a player to bet on — the case is potential, not production."
    if ledger == "grievance":
        return f"{who} read the coverage as disrespect and treat it as fuel."
    if ledger == "belonging":
        return f"{who} talk about him as one of their own — loyalty over stat line."
    if ledger == "judgment":
        return f"{who} are litigating his worthiness — the eye test against the résumé."
    if ledger == "grudge":
        return f"{rival_who} root against him as much as their own team roots for theirs."
    return f"{who} keep circling back to him."


def _ledger_chapter_label(ledger: str) -> str:
    return {
        "hope": "The Hope Economy",
        "grievance": "Disrespect as Fuel",
        "belonging": "One of Us",
        "judgment": "On Trial",
        "grudge": "The Long Memory",
    }.get(ledger, "The Story So Far")


def _build_dominant_take(lead: dict[str, Any], fanbase: str | None) -> DominantTake | None:
    """Build the attributed fan take from the top fired ledger row.

    The ledger detector already enforced representativeness (MIN_DOCS/MIN_SOURCES)
    and the C7 toxicity floor, so a fired lead is safe to surface. Dissent is
    shown as a labeled minority when the room is split (low confidence).
    """
    if not lead:
        return None
    ledger = str(lead.get("ledger") or "")
    if ledger not in LEDGERS:
        return None
    confidence = _to_float(lead.get("confidence")) or 0.0
    source_count = _to_int(lead.get("source_count")) or 0
    direction = lead.get("direction")
    text = _dominant_take_text(ledger, direction, fanbase)
    minority: str | None = None
    # A split room (contested direction OR low confidence) gets a labeled minority.
    if direction == "contested" or (0.0 < confidence < 0.33):
        minority = "A vocal minority sees it the other way."
    return DominantTake(
        text=text,
        confidence=max(0.0, min(1.0, confidence)),
        source_count=source_count,
        minority_take=minority,
    )


# ===========================================================================
# Tension line (doc 41 §4 / doc 43 §1.4) — perception vs production, as a
# curiosity gap. Deterministic from aura; "" when no aura signal.
# ===========================================================================
def _build_tension(db, player_id: int, season_year: int) -> str | None:
    aura = _safe_one(
        db,
        """
        select perception_pctl, production_pctl, verdict, is_low_signal
          from player_aura_weekly
         where player_id = :pid and season_year = :s
         order by week desc limit 1
        """,
        {"pid": int(player_id), "s": int(season_year)},
    )
    if not aura or _to_int(aura.get("is_low_signal")):
        return None
    perc = _to_float(aura.get("perception_pctl"))
    prod = _to_float(aura.get("production_pctl"))
    if perc is None or prod is None:
        return None
    gap = prod - perc
    if abs(gap) < 12.0:
        return None
    if gap >= 0:
        return (
            f"Fans rank his perception around the {int(round(perc))}th percentile; "
            f"the tape produces at the {int(round(prod))}th — why the gap?"
        )
    return (
        f"The room sees a {int(round(perc))}th-percentile name; "
        f"the tape grades at the {int(round(prod))}th — is the buzz ahead of the production?"
    )


# ===========================================================================
# Archetype classification (deterministic v1) — drives the chapter framing.
# Namespaced 'narr:*' to reuse player_archetype_tags without colliding with
# future positional archetypes (doc 46). Classified from the lead ledger +
# succession shape + recruiting register — NOT from per-archetype geometry.
# ===========================================================================
def _classify_archetype(card_inputs: dict[str, Any]) -> str:
    """Return a 'narr:*' slug from the assembled inputs (deterministic).

    One coherent frame; the archetype only flavors the chapter label + lead,
    never the card geometry (doc 49 §3 / doc 42 §4b — bespoke by COMPOSITION,
    not by template).
    """
    lead = (card_inputs.get("ledger_lead") or "").lower()
    succ = card_inputs.get("succession")
    stars = _to_int(card_inputs.get("stars"))
    transferred = bool(card_inputs.get("transferred"))

    # Succession-driven reads come first (the ghost/clock is the loudest frame).
    if succ is not None:
        read = (getattr(succ, "shoes_read", "") or "").lower()
        if read in ("downgrade", "leap_of_faith"):
            return "narr:filling-the-shoes"
    if transferred:
        return "narr:transfer-saga"
    if lead == "hope" and (stars or 0) >= 4:
        return "narr:phenom"
    if lead == "grievance":
        return "narr:disrespected"
    if lead == "belonging":
        return "narr:quiet-workhorse"
    if lead == "judgment":
        return "narr:on-trial"
    if lead == "grudge":
        return "narr:rival-villain"
    if lead == "hope":
        return "narr:hope-economy"
    return "narr:cornerstone"


# ===========================================================================
# Deterministic body (the 6-beat recap) + why-now + kicker. Templated
# publishable copy (the LLM narrator is a later phase). Composed from facts +
# the already-computed ledger/succession signals; attributed where it's
# discourse, plain where it's fact.
# ===========================================================================
def _build_body(
    ident: dict[str, Any],
    rec: dict[str, Any] | None,
    chips: list[dict[str, str]],
    succ: SuccessionRead | None,
    lead: dict[str, Any] | None,
) -> str | None:
    name = ident.get("full_name") or "He"
    team = ident.get("team_name")
    paras: list[str] = []

    # Beat 1 — who he is, grounded in pedigree + role.
    pieces: list[str] = []
    if rec and _to_int(rec.get("stars")):
        stars = _to_int(rec.get("stars"))
        nat = _to_int(rec.get("national_rank"))
        nat_txt = f", the No.{nat} recruit nationally" if nat and nat <= 500 else ""
        pieces.append(f"{name} arrived as a {stars}-star prospect{nat_txt}.")
    if team and ident.get("position"):
        pieces.append(f"He lines up at {ident['position']} for {team}.")
    if pieces:
        paras.append(" ".join(pieces))

    # Beat 2 — the production, as narrative context (never a bare number).
    if chips:
        top = chips[0]
        line = f"On the field, the headline is {top['value']} {top['label'].lower()}"
        if len(chips) > 1:
            line += f", with {chips[1]['value']} {chips[1]['label'].lower()}"
        line += "."
        paras.append(line)

    # Beat 3 — succession (the ghost / the clock), if any.
    if succ is not None:
        s_pieces: list[str] = []
        if getattr(succ, "predecessor_name", None):
            ps = getattr(succ, "predecessor_stars", None)
            star_tag = f" ({ps}-star)" if ps else ""
            s_pieces.append(f"He inherited the {succ.role} job from {succ.predecessor_name}{star_tag}.")
        if getattr(succ, "clock_line", None):
            s_pieces.append(str(succ.clock_line))
        if s_pieces:
            paras.append(" ".join(s_pieces))

    # Beat 4 — the fan ledger, attributed (compile, don't adjudicate).
    if lead:
        ledger = str(lead.get("ledger") or "")
        if ledger in LEDGERS:
            paras.append(_dominant_take_text(ledger, lead.get("direction"), team))

    if not paras:
        return None
    # Blank-line separated; the renderer splits paragraphs on blank lines.
    return "\n\n".join(paras)


def _build_why_now(
    season_year: int,
    lead: dict[str, Any] | None,
    succ: SuccessionRead | None,
    transferred: bool,
) -> str | None:
    """The heartbeat (doc 43 §6). calendar_pressure is EMPTY (doc 46 gotcha), so
    this degrades to a generic projective why-now — never blocks on the calendar."""
    if transferred:
        return f"He changed programs heading into {season_year} — a fresh fit to prove out."
    if succ is not None and getattr(succ, "clock_line", None):
        return f"The {succ.role} job is the open question heading into {season_year}."
    if lead:
        ledger = str(lead.get("ledger") or "")
        if ledger == "hope":
            return f"He is squarely in the {season_year} hype cycle — projection season."
        if ledger == "grievance":
            return f"The {season_year} preseason slights are already feeding the chip."
        if ledger == "judgment":
            return f"His {season_year} case is being argued before a snap is played."
    return f"The {season_year} outlook is the live story — the offseason looks forward."


def _build_kicker(
    succ: SuccessionRead | None,
    lead: dict[str, Any] | None,
    ban: Ban | None,
) -> str | None:
    # Vary the kicker TYPE per available signal (anti-formula lever, doc 42 §4c).
    if succ is not None and getattr(succ, "clock_line", None):
        return "The clock is the open loop — and it is already ticking."  # forward question
    if ban is not None:
        return f"The number to watch: {ban.number} — {ban.label.lower()}."  # factual gut-punch
    if lead:
        return "Whatever the tape says, the room has already made up its mind."  # quote-style
    return None


# ===========================================================================
# Transfer signal (cheap structured flag feeding archetype + why-now).
# ===========================================================================
def _is_transfer(db, player_id: int, season_year: int) -> bool:
    row = _safe_one(
        db,
        "select 1 as ok from transfer_entries "
        "where player_id = :pid and season_year >= :s0 limit 1",
        {"pid": int(player_id), "s0": int(season_year) - 1},
    )
    return bool(row)


# ===========================================================================
# Content-hash (regen short-circuit; mirrors signature_story_generator). Stored
# on the StoryCard inputs so the cache write can short-circuit unchanged players.
# ===========================================================================
def _content_hash(inputs: dict[str, Any]) -> str:
    canonical = json.dumps(inputs, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ===========================================================================
# Cache write — TODO-stubbed (the orchestrator returns the object this phase;
# persistence is a follow-up). Kept here so the call site is explicit and a
# later phase only fills the body. NEVER raises.
# ===========================================================================
def _write_card_cache(db, card: StoryCard, content_hash: str, model_id: str = "deterministic-v1") -> None:
    """TODO (later phase): upsert player_story_card_cache.

    Intentionally a no-op in v1 — doc 49 §7 builds the deterministic engine
    first and returns the object; the cache write (regen short-circuit by
    content_hash) lands with the nightly enrich step. Stubbed, never raises.
    """
    return None


# ===========================================================================
# Tier rail (doc 41 tier-is-texture). Deterministic from pedigree + whether the
# player holds a throne — the loudest cheap proxy for "S/T1/T2/T3 lane."
# ===========================================================================
def _tier_rail(stars: int | None, succ: SuccessionRead | None, ledger_lead: dict[str, Any] | None) -> str:
    rail = _STAR_RAIL.get(stars or 0, "t3")
    # A confident throne-holder or a strongly-fired ledger nudges the rail up one
    # notch (the player is clearly in a louder lane than pedigree alone implies).
    loud = bool(succ is not None and getattr(succ, "confidence", 0.0) >= 0.8) or bool(
        ledger_lead and (_to_float(ledger_lead.get("confidence")) or 0.0) >= 0.66
    )
    if loud:
        bump = {"t3": "t2", "t2": "t1", "t1": "s", "s": "s"}
        rail = bump.get(rail, rail)
    return rail


# ===========================================================================
# THE ORCHESTRATOR — build the structured StoryCard.
# ===========================================================================
def build_card_payload(
    db,
    player_id: int,
    season_year: int,
    position: str | None = None,
    *,
    as_of_date: str | None = None,
) -> StoryCard | None:
    """Assemble the full StoryCard for a player (the structured contract).

    Resolves player_external_id internally, runs the deterministic detectors,
    selects the BAN, picks the lead ledger + dominant take, composes ONE frame,
    and applies the four-rung degradation ladder (doc 48 §3). Returns None only
    when there is no stable anchor (cannot key state) — otherwise always returns
    a card (the lowest rung is the honest stats-strip). NEVER raises.
    """
    try:
        if db is None or player_id is None or season_year is None:
            return None
        season_year = int(season_year)
        as_of = as_of_date or _today()

        external_id = resolve_external_id(db, player_id)
        if not external_id:
            # No stable anchor -> we cannot key narrative state. Omit honestly.
            return None

        ident = _fetch_identity(db, player_id, season_year, position)
        pos = ident.get("position")
        chips = _fetch_key_stats(db, player_id, season_year, pos)
        rec = _fetch_recruiting(db, player_id)
        stars = _to_int((rec or {}).get("stars"))

        # --- deterministic detectors (the engine for everyone) ---------------
        succ = fetch_succession_for_player(db, external_id, season_year)
        lead = fetch_ledger_lead(db, external_id, season_year, None)

        ban = _select_ban(db, player_id, season_year, pos)
        tension = _build_tension(db, player_id, season_year)
        transferred = _is_transfer(db, player_id, season_year)

        # --- composition inputs (one coherent frame, content-variable) -------
        ledger_lead_name = str(lead.get("ledger")) if lead else None
        archetype_inputs = {
            "ledger_lead": ledger_lead_name,
            "succession": succ,
            "stars": stars,
            "transferred": transferred,
        }
        archetype = _classify_archetype(archetype_inputs)
        rail = _tier_rail(stars, succ, lead)

        identity_meta = _identity_meta(ident)
        team_color = ident.get("team_color")  # None in v1 (no team-theme join wired); renderer drops it

        # --- the degradation ladder (doc 48 §3) ------------------------------
        # The representativeness floor (doc 42, doc 49 §4): a NARRATIVE tier needs
        # a genuinely-fired fan ledger (cross-source, sustained, above noise) OR a
        # confident structural story (a throne-line read). Below that, the honest
        # stats-strip — never a padded story over thin/sarcastic data.
        has_fired_ledger = bool(lead and lead.get("fired"))
        has_structural_story = bool(
            succ is not None and (getattr(succ, "confidence", 0.0) or 0.0) >= 0.6
            and (getattr(succ, "predecessor_name", None) or getattr(succ, "clock_line", None))
        )
        narrative_ok = has_fired_ledger or has_structural_story

        dominant_take = _build_dominant_take(lead, ident.get("team_name")) if has_fired_ledger else None

        if narrative_ok:
            body = _build_body(ident, rec, chips, succ, lead)
            why_now = _build_why_now(season_year, lead, succ, transferred)
            kicker = _build_kicker(succ, lead, ban)
            logline = _build_logline(ident, archetype, succ, lead, ban)
            chapter_label = _ledger_chapter_label(ledger_lead_name) if ledger_lead_name else (
                "Filling the Shoes" if has_structural_story else "The Story So Far"
            )
            composition = _composition_order(has_fired_ledger, has_structural_story, ban is not None, bool(tension))

            # Rung 1 (FULL) vs Rung 2 (REDUCED): identical geometry here in the
            # deterministic phase; FULL is reserved for the later LLM-voice layer.
            # We ship REDUCED (deterministic, bespoke-by-composition) and label it.
            fallback_rung = "reduced"
            fallback_reason = "deterministic narrative (LLM voice tier deferred to a later phase)"

            citations = _collect_citations(ban, succ, lead, chips)

            card = StoryCard(
                player_external_id=external_id,
                season=season_year,
                as_of_date=as_of,
                tier="narrative",
                logline=logline,
                why_now=why_now,
                body=body,
                kicker=kicker,
                chapter_label=chapter_label,
                chapter_number=None,
                ban=ban,
                dominant_take=dominant_take,
                ledger_lead=ledger_lead_name,
                succession=succ,
                tension_text=tension,
                archetype_slug=archetype,
                tier_rail=rail,
                key_stat_chips=chips,
                citations=citations,
                composition=composition,
                fallback_reason=fallback_reason,
                player_name=ident.get("full_name"),
                identity_meta=identity_meta,
                team_color=team_color,
                fallback_rung=fallback_rung,
            )
        else:
            # Rung 3 (LOW-DATA): the honest stats-strip — below the discourse
            # floor there is genuinely no story to compile (doc 49 §4).
            reason = (
                "Limited signal — not enough coverage for a story yet."
                if not chips else
                "Below the discourse floor — the honest stats-only state."
            )
            card = StoryCard(
                player_external_id=external_id,
                season=season_year,
                as_of_date=as_of,
                tier="stats-strip",
                ban=None,
                tier_rail="t3",
                key_stat_chips=chips,
                composition=["identity", "stat"],
                fallback_reason=reason,
                player_name=ident.get("full_name"),
                identity_meta=identity_meta,
                team_color=team_color,
                fallback_rung="low-data",
            )

        # Cache write is TODO-stubbed this phase (returns the object).
        try:
            content_hash = _content_hash({
                "ext": external_id, "season": season_year, "tier": card.tier,
                "ledger": ledger_lead_name, "archetype": archetype, "rail": rail,
                "ban": (asdict(ban) if ban else None),
                "chips": chips,
                "succ": (asdict(succ) if succ else None),
            })
            _write_card_cache(db, card, content_hash)
        except Exception:
            pass

        return card
    except Exception:
        # Never raise into the page; a failed payload becomes "" upstream.
        return None


def _build_logline(
    ident: dict[str, Any],
    archetype: str,
    succ: SuccessionRead | None,
    lead: dict[str, Any] | None,
    ban: Ban | None,
) -> str:
    """The stable mixed-case serif logline (doc 41 §7 logline-stability rule).

    Deterministic v1: a single grounded sentence keyed to the archetype, locked
    to the inflection it reflects. The LLM rewrite is a later phase; this is the
    publishable deterministic spine.
    """
    name = ident.get("full_name") or "The player"
    team = ident.get("team_name") or "his program"
    if archetype == "narr:filling-the-shoes" and succ is not None and getattr(succ, "predecessor_name", None):
        return f"{name} steps into {succ.predecessor_name}'s shoes — the gap is the story."
    if archetype == "narr:transfer-saga":
        return f"{name} arrives at {team} with a new fit to prove and an old chapter behind him."
    if archetype == "narr:phenom":
        return f"{name} carries five-star expectation into {team}'s season — promise, not yet proof."
    if archetype == "narr:disrespected":
        return f"{name} is the player {team} fans say the polls keep overlooking."
    if archetype == "narr:quiet-workhorse":
        return f"{name} is {team}'s steady hand — loved less for the stat line than for staying."
    if archetype == "narr:on-trial":
        return f"{name} is on trial in {team}'s fan jury — the eye test against the résumé."
    if archetype == "narr:rival-villain":
        return f"{name} is the {team} name rival fanbases love to root against."
    if archetype == "narr:hope-economy":
        return f"{name} is {team}'s offseason bet — the case is potential over production."
    return f"{name} is a cornerstone for {team} — measured against the line he joined."


def _composition_order(
    has_ledger: bool, has_succession: bool, has_ban: bool, has_tension: bool,
) -> list[str]:
    """Ordered module slugs the engine chose — bespoke by CONTENT, one geometry.

    The lead differs per player (succession-led vs ledger-led vs stat-led), but
    the frame is the same coherent card (doc 49 §3, doc 42 §4b). This list is the
    auditable record of what the engine surfaced, in order.
    """
    order: list[str] = ["identity", "logline"]
    if has_ban:
        order.append("ban")
    order.append("chips")
    if has_ledger:
        order.append("dominant_take")
    if has_tension:
        order.append("tension")
    order.append("recap")
    if has_succession:
        order.append("succession")
    order.append("why_now")
    return order


def _collect_citations(
    ban: Ban | None,
    succ: SuccessionRead | None,
    lead: dict[str, Any] | None,
    chips: list[dict[str, str]],
) -> list[Receipt]:
    """Provenance receipts for the footer — the DB origins behind the card."""
    cites: list[Receipt] = []
    seen: set[tuple[str, str]] = set()

    def _add(table: str, detail: str) -> None:
        key = (table, detail)
        if key in seen:
            return
        seen.add(key)
        cites.append(Receipt(table=table, detail=detail))

    if chips:
        _add("player_season_stats", "season totals")
    if ban is not None and ban.receipt is not None:
        _add(ban.receipt.table, ban.receipt.detail)
    if succ is not None:
        _add("player_succession", "throne-line + Filling-the-Shoes")
    if lead and lead.get("fired"):
        _add("player_ledger_scores", "compiled from tagged fan discourse")
    return cites


# ===========================================================================
# THE RENDER ENTRY — what the reporting.py injection calls.
# ===========================================================================
def build_card(
    db,
    player_id: int,
    season_year: int,
    position: str | None = None,
    *,
    as_of_date: str | None = None,
) -> str:
    """Build + render the player Story Card. Returns rendered HTML, or "".

    This is the top-level entry the reporting.py player-page injection calls
    (mirrors the _v2 (db, player_id, season_year, position) signature; resolves
    the stable external id internally). NEVER raises — any failure degrades to
    "" so a card error can never blank the page (matches new_aura_html /
    new_in_their_words_html).
    """
    try:
        card = build_card_payload(
            db, player_id, season_year, position, as_of_date=as_of_date
        )
        if card is None:
            return ""
        return render_story_card(card) or ""
    except Exception:
        return ""
