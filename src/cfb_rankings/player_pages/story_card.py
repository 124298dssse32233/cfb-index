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

Phase 2 (additive, never breaks the deterministic path):
  - ``compute_story_cards`` is the nightly-enrich entry the ``compute-story-cards``
    CLI subcommand calls. It builds every S/T1 card, optionally upgrades the prose
    via the confident-compiler LLM narrator (graceful: any failure keeps the
    deterministic prose), and PERSISTS the result to ``player_story_card_cache``
    (regen-gated by ``content_hash``; the single PK row per player-season IS the
    LKG). It also warms the ledger + succession writers so the coverage guard sees
    populated tables. It NEVER triggers an Ollama call from ``build_card`` /
    ``build-site`` — only this compute step generates.
  - ``build_card`` / ``build_card_payload`` READ the FRESH cache first (matched by
    ``content_hash``) and overlay ONLY the prose fields (``logline`` / ``body`` /
    ``kicker``); on any miss/staleness/error they ship the live deterministic card
    unchanged. The read is one indexed PK lookup — build-site stays fast.

Public API:
    @dataclass Receipt / Ban / DominantTake / SuccessionRead / StoryCard
    build_card(db, player_id, season_year, position=None, *, as_of_date=None) -> str
    build_card_payload(db, player_id, season_year, position=None, *, as_of_date=None) -> StoryCard | None
    resolve_external_id(db, player_id) -> str | None
    compute_story_cards(db, season, players=None, tiers=None) -> dict   # counts
    write_story_card_cache(db, card, content_hash, ...) -> bool
    read_fresh_card_cache(db, external_id, season_year, content_hash) -> dict | None
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
    # --- additive Phase-3 fields (tribal lenses + changelog). Both default-safe so
    #     every existing construction site + the cache round-trip keep working.
    #   `lenses`: the tribal-lens POV payload, populated ONLY on the LLM path by
    #     compute_story_cards from the national+rival narrate() passes. Shape:
    #       {"national": {logline,dominant_take,minority_take,body,kicker},
    #        "rival":    {...}?}   — None on the deterministic / single-voice path
    #     (today's behavior; the renderer then emits no toggle). LLM prose, so it
    #     rides the cache (round-trips through card_json) and is overlaid by
    #     _overlay_cached_prose under the same content_hash freshness gate.
    lenses: Optional[dict] = None
    #   `changelog`: the recent player_bible_snapshots deltas (newest-first, <=4),
    #     `[{"as_of","week","delta"}, ...]`. DERIVED state — always recomputed LIVE
    #     from the snapshots table by _attach_changelog (NEVER trusted from cache,
    #     NEVER folded into the content_hash). Empty when the player has no recorded
    #     shifts (the renderer then shows nothing — silence is correct).
    changelog: list[dict] = field(default_factory=list)


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
    "compute_story_cards",
    "write_story_card_cache",
    "read_fresh_card_cache",
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
# Content-hash (regen short-circuit; mirrors signature_story_generator). Generic
# 16-hex canonical-json hash helper. NOTE: the CANONICAL Story-Card content hash
# (the one that gates the cache READ in build_card_payload and the cache WRITE in
# compute_story_cards) is story_card_narrator.story_content_hash — it folds in the
# tier + the fan-take confidence band + the evidence doc-id SET so the card
# re-narrates only when the story actually moves. This helper is kept as a small
# stable utility; both READ and WRITE must use the narrator's hash so they agree.
# ===========================================================================
def _content_hash(inputs: dict[str, Any]) -> str:
    canonical = json.dumps(inputs, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ===========================================================================
# Cache I/O (Phase 2) — persistence of the assembled StoryCard, regen-gated by
# content_hash. The PK is (player_external_id, season_year), so there is exactly
# ONE row per player-season and that single row IS the Last-Known-Good (LKG): a
# successful LLM narration promotes it (is_lkg=1); a failed narration LEAVES the
# prior good row untouched (serve LKG) or, absent one, writes the deterministic
# card. All writes are additive-only and NEVER raise — the enrich step is
# non-critical and a render-path read can never blank the page.
#
# The additive 20260611_03 columns (is_lkg / lkg_promoted_at_utc / prose_source /
# fallback_reason / eval_factscore / eval_slop) may not exist yet on every DB, so
# every read selects only the base columns and probes the extras best-effort, and
# every write degrades to the legacy column set when the extras are absent.
# ===========================================================================

# Columns guaranteed by migration 20260611_02 (the base contract). Anything
# beyond this set is probed defensively so build-site works pre-migration-03.
_CACHE_BASE_COLUMNS = (
    "player_external_id", "player_id", "season_year", "as_of_date",
    "card_tier", "fallback_rung", "card_json", "card_html",
    "content_hash", "model_id", "generated_at_utc",
)
# Additive columns from migration 20260611_03 (probed; absent on older DBs).
_CACHE_EXTRA_COLUMNS = (
    "is_lkg", "lkg_promoted_at_utc", "prose_source",
    "fallback_reason", "eval_factscore", "eval_slop",
)

_CACHE_COLS_ATTR = "_story_card_cache_columns"


def _cache_columns(db) -> set[str]:
    """Live column set of player_story_card_cache, cached on the db object.

    Used to decide whether the additive 20260611_03 columns are present so the
    reader/writer can degrade gracefully on a pre-migration-03 database.
    """
    cols = getattr(db, _CACHE_COLS_ATTR, None)
    if cols is not None:
        return cols
    found: set[str] = set()
    try:
        rows = db.query_all("PRAGMA table_info(player_story_card_cache)", {}) or []
        for r in rows:
            name = r.get("name")
            if name:
                found.add(str(name))
    except Exception:
        found = set(_CACHE_BASE_COLUMNS)
    try:
        setattr(db, _CACHE_COLS_ATTR, found)
    except Exception:
        pass
    return found


def write_story_card_cache(
    db,
    card: StoryCard,
    content_hash: str,
    *,
    model_id: str = "deterministic-v1",
    prose_source: str = "deterministic",
    is_lkg: int = 0,
    fallback_reason: str | None = None,
    eval_factscore: float | None = None,
    eval_slop: float | None = None,
    card_html: str | None = None,
) -> bool:
    """Upsert ``card`` into player_story_card_cache. Returns True on a write.

    Additive-only: never alters existing data beyond this player-season row, and
    degrades to the legacy column set when the 20260611_03 columns are absent.
    NEVER raises (per-player non-critical).
    """
    try:
        if db is None or card is None or not getattr(card, "player_external_id", None):
            return False
        cols = _cache_columns(db)
        have_extras = all(c in cols for c in _CACHE_EXTRA_COLUMNS)

        player_id = None
        try:
            player_id = _resolve_player_id_for_cache(db, card.player_external_id)
        except Exception:
            player_id = None

        base_params = {
            "ext": str(card.player_external_id),
            "pid": player_id,
            "s": int(card.season),
            "as_of": card.as_of_date,
            "card_tier": card.tier,
            "fallback_rung": card.fallback_rung,
            "card_json": json.dumps(asdict(card), default=str),
            "card_html": card_html,
            "content_hash": content_hash,
            "model_id": model_id,
            "gen_at": _now_utc(),
        }

        if have_extras:
            params = dict(base_params)
            params.update({
                "is_lkg": int(is_lkg),
                "lkg_at": _now_utc() if is_lkg else None,
                "prose_source": prose_source,
                "fallback_reason": fallback_reason,
                "eval_factscore": eval_factscore,
                "eval_slop": eval_slop,
            })
            db.execute(
                """
                INSERT INTO player_story_card_cache (
                    player_external_id, player_id, season_year, as_of_date,
                    card_tier, fallback_rung, card_json, card_html,
                    content_hash, model_id, generated_at_utc,
                    is_lkg, lkg_promoted_at_utc, prose_source,
                    fallback_reason, eval_factscore, eval_slop
                ) VALUES (
                    :ext, :pid, :s, :as_of,
                    :card_tier, :fallback_rung, :card_json, :card_html,
                    :content_hash, :model_id, :gen_at,
                    :is_lkg, :lkg_at, :prose_source,
                    :fallback_reason, :eval_factscore, :eval_slop
                )
                ON CONFLICT(player_external_id, season_year) DO UPDATE SET
                    player_id            = excluded.player_id,
                    as_of_date           = excluded.as_of_date,
                    card_tier            = excluded.card_tier,
                    fallback_rung        = excluded.fallback_rung,
                    card_json            = excluded.card_json,
                    card_html            = excluded.card_html,
                    content_hash         = excluded.content_hash,
                    model_id             = excluded.model_id,
                    generated_at_utc     = excluded.generated_at_utc,
                    is_lkg               = excluded.is_lkg,
                    lkg_promoted_at_utc  = excluded.lkg_promoted_at_utc,
                    prose_source         = excluded.prose_source,
                    fallback_reason      = excluded.fallback_reason,
                    eval_factscore       = excluded.eval_factscore,
                    eval_slop            = excluded.eval_slop
                """,
                params,
            )
            return True

        # Legacy column set only (pre-migration-03): still records the card.
        db.execute(
            """
            INSERT INTO player_story_card_cache (
                player_external_id, player_id, season_year, as_of_date,
                card_tier, fallback_rung, card_json, card_html,
                content_hash, model_id, generated_at_utc
            ) VALUES (
                :ext, :pid, :s, :as_of,
                :card_tier, :fallback_rung, :card_json, :card_html,
                :content_hash, :model_id, :gen_at
            )
            ON CONFLICT(player_external_id, season_year) DO UPDATE SET
                player_id        = excluded.player_id,
                as_of_date       = excluded.as_of_date,
                card_tier        = excluded.card_tier,
                fallback_rung    = excluded.fallback_rung,
                card_json        = excluded.card_json,
                card_html        = excluded.card_html,
                content_hash     = excluded.content_hash,
                model_id         = excluded.model_id,
                generated_at_utc = excluded.generated_at_utc
            """,
            base_params,
        )
        return True
    except Exception:
        return False


def _resolve_player_id_for_cache(db, external_id: str) -> int | None:
    """numeric player_id for a cfbd external id (cache denorm convenience)."""
    row = _safe_one(
        db,
        "select player_id from player_source_ids "
        "where source_player_id = :ext and source_name = 'cfbd' limit 1",
        {"ext": str(external_id)},
    )
    return _to_int((row or {}).get("player_id"))


def read_fresh_card_cache(
    db, external_id: str, season_year: int, content_hash: str | None = None
) -> dict[str, Any] | None:
    """Read the cached card row IFF it is fresh for ``content_hash``.

    Returns a dict {card_json, content_hash, prose_source, is_lkg, ...} when a row
    exists AND (content_hash is None OR matches). Returns None on miss, on a stale
    hash, or on any error — the caller then ships the live deterministic card.
    NEVER raises.
    """
    try:
        if db is None or not external_id or season_year is None:
            return None
        cols = _cache_columns(db)
        have_extras = all(c in cols for c in _CACHE_EXTRA_COLUMNS)
        if have_extras:
            row = _safe_one(
                db,
                """
                select card_json, content_hash, card_tier, fallback_rung,
                       model_id, coalesce(is_lkg, 0) as is_lkg, prose_source,
                       fallback_reason, eval_factscore
                  from player_story_card_cache
                 where player_external_id = :ext and season_year = :s
                """,
                {"ext": str(external_id), "s": int(season_year)},
            )
        else:
            row = _safe_one(
                db,
                """
                select card_json, content_hash, card_tier, fallback_rung, model_id
                  from player_story_card_cache
                 where player_external_id = :ext and season_year = :s
                """,
                {"ext": str(external_id), "s": int(season_year)},
            )
            if row is not None:
                # Synthesize the additive fields the caller expects.
                row.setdefault("is_lkg", 0)
                # Infer prose source from the model id when the column is absent.
                mid = str(row.get("model_id") or "")
                row.setdefault(
                    "prose_source", "llm" if mid.startswith("ollama:") else "deterministic"
                )
        if not row:
            return None
        if content_hash is not None and str(row.get("content_hash") or "") != str(content_hash):
            return None  # stale — the deterministic inputs moved since this was cached.
        return row
    except Exception:
        return None


def _now_utc() -> str:
    return _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


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

        # --- additive LLM-prose overlay (Phase 2). CACHE-READ ONLY; never blocks,
        #     never calls Ollama, never raises. If a fresh cached row carries
        #     LLM/LKG prose that still matches the live deterministic inputs (by
        #     content_hash), overlay ONLY the prose fields (logline/body/kicker)
        #     and keep every other structural field (ban/dominant_take/succession/
        #     citations) LIVE. On any miss/staleness/error the deterministic card
        #     already built ships unchanged — today's behavior exactly. -----------
        try:
            _overlay_cached_prose(db, card)
        except Exception:
            pass  # any failure -> the deterministic card is already complete.

        # --- additive changelog ("how this story shifted"). READ-ONLY from the
        #     player_bible_snapshots table compute_story_cards last wrote — zero
        #     Ollama, zero compute dependency, recomputed live every render so it
        #     is never stale even when the prose is a cached LKG. Graceful-empty on
        #     any miss/error (a brand-new or never-shifted player shows nothing). --
        try:
            _attach_changelog(db, card)
        except Exception:
            card.changelog = []  # never raise into the page.

        return card
    except Exception:
        # Never raise into the page; a failed payload becomes "" upstream.
        return None


def _attach_changelog(db, card: StoryCard, limit: int = 4) -> None:
    """Attach the recent player_bible_snapshots deltas to ``card.changelog``.

    READ-ONLY: reads whatever ``compute_story_cards`` last wrote (deterministic
    state, no Ollama, no compute), maps each snapshot to a compact
    ``{"as_of","week","delta"}`` dict, newest-first, capped at ``limit``. Filters
    empty diffs. Graceful-empty (``[]``) on any miss/error — silence is correct
    for a never-shifted player. NEVER raises.
    """
    card.changelog = []
    if db is None or card is None or not getattr(card, "player_external_id", None):
        return
    rows = _safe_all(
        db,
        """
        select as_of_date, week, diff_summary, logline
          from player_bible_snapshots
         where player_external_id = :ext and season_year = :s
         order by created_at_utc desc
         limit 5
        """,
        {"ext": str(card.player_external_id), "s": int(card.season)},
    )
    out: list[dict] = []
    for r in rows:
        delta = (r.get("diff_summary") or "").strip()
        if not delta:
            continue  # an empty diff is not a transition worth showing.
        out.append({
            "as_of": r.get("as_of_date"),
            "week": _to_int(r.get("week")),
            "delta": delta,
        })
        if len(out) >= int(limit):
            break
    card.changelog = out


def _overlay_cached_prose(db, card: StoryCard) -> None:
    """If a FRESH cached row carries upgraded prose, overlay it onto ``card``.

    Freshness = the cached ``content_hash`` equals the hash of the CURRENT live
    deterministic inputs (computed via the narrator's canonical hash so READ and
    WRITE agree). Only the prose fields are overlaid; all structured truth stays
    live. READ-ONLY: no generation, no Ollama. NEVER raises.
    """
    if db is None or card is None or not getattr(card, "player_external_id", None):
        return
    # A cheap existence probe first — skip all hashing when there is no row.
    head = read_fresh_card_cache(db, card.player_external_id, card.season, content_hash=None)
    if not head:
        return
    if str(head.get("prose_source") or "") not in ("llm", "lkg"):
        return  # deterministic cache row carries nothing the live build lacks.

    # Compute the canonical hash for the CURRENT live inputs and require a match.
    try:
        from . import story_card_narrator as _nar

        tier = _nar.classify_player_tier(
            db, _resolve_player_id_for_cache(db, card.player_external_id), card.season
        )
        evidence = _nar.assemble_evidence(db, card)
        live_hash = _nar.story_content_hash(card, tier, evidence)
    except Exception:
        return  # cannot prove freshness -> ship the deterministic card.

    if str(head.get("content_hash") or "") != str(live_hash):
        return  # stale -> the story moved; deterministic prose is the honest state.

    try:
        cj = json.loads(head.get("card_json") or "{}")
    except Exception:
        return
    for f in ("logline", "body", "kicker"):
        val = cj.get(f)
        if val:
            setattr(card, f, val)
    # The dominant_take .text / .minority_take are LLM-upgraded too (the bespoke
    # fanbase take that pairs with the confidence meter). Overlay them onto the
    # LIVE DominantTake so the meter band (.confidence / .source_count) stays
    # live while the cached prose leads. Only when both sides carry the take.
    cj_take = cj.get("dominant_take") or {}
    if isinstance(cj_take, dict) and card.dominant_take is not None:
        if cj_take.get("text"):
            card.dominant_take.text = cj_take["text"]
        if cj_take.get("minority_take"):
            card.dominant_take.minority_take = cj_take["minority_take"]
    # The tribal-lens payload is LLM prose too (the per-lens national/rival voice),
    # so it belongs with the cached prose under the SAME freshness gate. Overlay it
    # here; the deterministic path never carries lenses (stays None -> no toggle).
    # NOT overlaid: `changelog` — that is derived from snapshots and recomputed live
    # by _attach_changelog AFTER this overlay, so a cached value must not leak in.
    cj_lenses = cj.get("lenses")
    if cj_lenses:
        card.lenses = cj_lenses
    card.fallback_rung = "full"
    card.fallback_reason = (
        "llm prose (cached)" if head.get("prose_source") == "llm" else "lkg prose (stale-ok)"
    )


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


# ===========================================================================
# THE BIBLE + CHANGELOG (Phase 3) — the long-lived narrative state + the EKG.
#
# The bible (`player_bible`, one PK row per player) is the deterministic register
# of the player's current arc; the snapshot log (`player_bible_snapshots`) is the
# append-only EKG of the moments the story MOVED. Both are written ONLY by the
# nightly compute (inside compute_story_cards, AFTER the cache write), NEVER by
# build_card / build-site (which is read-only, zero-Ollama). All writes are
# additive and NEVER raise — one bad bible never aborts the batch.
#
# Change detection keys on the SAME narrator content_hash the cache uses (it
# excludes the clock + raw body text, folding only tier + take-band + evidence
# doc-id SET), so a snapshot fires on a shifted take / flipped confidence band /
# new discourse docs / new BAN / tier change — the real "story moved" events,
# never on a daily tick. Unchanged players write nothing (idempotent re-runs).
# ===========================================================================
def _attach_lenses(nar, db, card: StoryCard, tier: str, evidence) -> dict | None:
    """Build the tribal-lens payload via the narrator's narrate_lenses.

    The narrator owns everything: the rival representativeness floor, the rival
    second pass + eval gate, and the lens-dict shape. It re-runs national from
    `evidence` (the SAME pool the primary pass already used), so the national lens
    equals the prose already overlaid onto the card — no divergence, no second
    national cost beyond one re-narrate. Returns {"national":{...}, "rival":{...}?}
    or None (then the card renders single-voice, no toggle). NEVER raises."""
    try:
        return nar.narrate_lenses(db, card, tier, evidence=evidence)
    except Exception:
        return None


def _bible_identity_json(card: StoryCard) -> str:
    """{name,team,pos,class,jersey,team_color} from the in-hand card.

    The card carries identity as the `·`-joined `identity_meta` string
    ("QB · Tennessee · Sr · #15") plus player_name + team_color. Parse the meta
    defensively (best-effort positional read) so the bible identity is structured.
    NEVER raises (returns at minimum {name, team_color})."""
    pos = team = klass = jersey = None
    try:
        meta = str(card.identity_meta or "")
        parts = [p.strip() for p in meta.split("·") if p.strip()]
        # _identity_meta order is [position, team_name, class_year, #jersey], each
        # present only when known — so read by shape, not fixed index.
        for p in parts:
            if p.startswith("#") and jersey is None:
                jersey = p.lstrip("#") or None
            elif p in ("Fr", "So", "Jr", "Sr") and klass is None:
                klass = p
            elif pos is None and len(p) <= 4 and p.isupper():
                pos = p           # short all-caps token is the position code
            elif team is None:
                team = p          # the remaining long token is the team name
    except Exception:
        pass
    return json.dumps(
        {
            "name": card.player_name,
            "team": team,
            "pos": pos,
            "class": klass,
            "jersey": jersey,
            "team_color": card.team_color,
        },
        default=str,
    )


def _bible_current_beats_json(card: StoryCard) -> str:
    """The decaying current-arc register: the live ledger + take + BAN."""
    beats: list[dict] = []
    take = None
    conf = None
    if card.dominant_take is not None:
        take = getattr(card.dominant_take, "text", None)
        conf = getattr(card.dominant_take, "confidence", None)
    if card.ledger_lead or take:
        beats.append({"ledger": card.ledger_lead, "take": take, "confidence": conf})
    if card.tension_text:
        beats.append({"tension": card.tension_text})
    if card.ban is not None:
        try:
            beats.append({"ban": asdict(card.ban)})
        except Exception:
            pass
    return json.dumps(beats, default=str)


def _bible_permanent_beats_json(card: StoryCard) -> str:
    """The never-decayed career-frame register: succession line + recruiting BAN."""
    beats: list[dict] = []
    succ = card.succession
    if succ is not None:
        pred = getattr(succ, "predecessor_name", None)
        heir = getattr(succ, "heir_name", None)
        if pred or heir:
            beats.append({"predecessor": pred, "heir": heir})
    if card.ban is not None and getattr(card.ban, "kind", None) == "rank":
        try:
            beats.append({"ban": asdict(card.ban)})
        except Exception:
            pass
    return json.dumps(beats, default=str)


def _bible_arc_state_json(card: StoryCard) -> str:
    return json.dumps(
        {
            "chapter": card.chapter_number,
            "chapter_label": card.chapter_label,
            "tensions": [card.tension_text] if card.tension_text else [],
            "trajectory": card.archetype_slug,
        },
        default=str,
    )


def _bible_coverage_flag(card: StoryCard) -> str:
    """CHECK-constrained to {'narrative','no_story','no_data'}. Derive from the card:
    a narrative-tier card -> 'narrative'; a stats-strip WITH chips (we have stats,
    just no fired discourse) -> 'no_story'; nothing at all -> 'no_data'."""
    if card.tier == "narrative":
        return "narrative"
    if card.key_stat_chips:
        return "no_story"
    return "no_data"


def _resolve_current_week(db, season: int) -> int | None:
    """Best-effort current CFB week for the snapshot UNIQUE key. None when the
    season's week is not resolvable (NULL-week + dated rows coexist by design).
    NEVER raises."""
    try:
        from cfb_rankings.common.week import resolve_week  # type: ignore

        wk = resolve_week(db, season)
        # resolve_week may return an int or a small mapping; accept either.
        if isinstance(wk, int):
            return wk
        if isinstance(wk, dict):
            return _to_int(wk.get("week") or wk.get("week_number"))
        return _to_int(getattr(wk, "week", None))
    except Exception:
        return None


def _take_band(conf: float | None, minority: Any) -> str:
    """'split' | 'settled' band label for a take's confidence (the meter band)."""
    c = conf or 0.0
    return "split" if (minority or c < 0.66) else "settled"


def _prior_band_and_ban(prior: dict | None) -> tuple[str, str]:
    """Recover the prior take-band + prior BAN string from the prior bible row's
    current_beats_json (the bible stores these in the current register, not as
    columns). Returns ('','') when absent/unparseable. NEVER raises."""
    if not prior:
        return "", ""
    band = ban = ""
    try:
        beats = json.loads(prior.get("current_beats_json") or "[]")
        for b in beats if isinstance(beats, list) else []:
            if not isinstance(b, dict):
                continue
            if "confidence" in b or "take" in b:
                band = _take_band(_to_float(b.get("confidence")), None)
            if isinstance(b.get("ban"), dict):
                num = b["ban"].get("number") or ""
                lab = b["ban"].get("label") or ""
                ban = f"{num} {lab}".strip()
    except Exception:
        return "", ""
    return band, ban


def _bible_diff_summary(prior: dict | None, card: StoryCard) -> str:
    """A deterministic human delta from the prior bible row to the new card.

    First sighting -> 'first card'. Otherwise a compact transition string keyed to
    whatever moved (logline / why_now / take confidence band / new BAN). NEVER
    raises (returns 'story shifted' as the honest floor)."""
    try:
        if prior is None:
            return "first card"
        bits: list[str] = []
        old_logline = (prior.get("logline") or "").strip()
        new_logline = (card.logline or "").strip()
        if new_logline and new_logline != old_logline:
            bits.append(f"logline: '{old_logline}' -> '{new_logline}'")
        old_why = (prior.get("why_now") or "").strip()
        new_why = (card.why_now or "").strip()
        if new_why and new_why != old_why:
            bits.append(f"why now: {new_why}")
        old_band, old_ban = _prior_band_and_ban(prior)
        # Confidence band flip (split <-> settled) vs the prior current register.
        if card.dominant_take is not None:
            band = _take_band(
                getattr(card.dominant_take, "confidence", None),
                getattr(card.dominant_take, "minority_take", None),
            )
            if old_band and band != old_band:
                bits.append(f"the room {band}")
        if card.ban is not None:
            num = getattr(card.ban, "number", "") or ""
            lab = getattr(card.ban, "label", "") or ""
            new_ban = f"{num} {lab}".strip()
            if new_ban and new_ban != old_ban:
                bits.append(new_ban)
        return "; ".join(bits) if bits else "story shifted"
    except Exception:
        return "story shifted"


def _write_bible_snapshot(
    db, card: StoryCard, *, week: int | None, diff_summary: str
) -> None:
    """Append ONE player_bible_snapshots row (the EKG transition). ON CONFLICT DO
    NOTHING on (ext,season,week,as_of_date) so a same-day re-run after the same
    change is idempotent. NEVER raises."""
    try:
        db.execute(
            """
            INSERT INTO player_bible_snapshots (
                player_external_id, season_year, week, as_of_date,
                logline, why_now, arc_state_json, tension_text,
                diff_summary, snapshot_json, created_at_utc
            ) VALUES (
                :ext, :s, :week, :as_of,
                :logline, :why_now, :arc_state, :tension,
                :diff, :snapshot, :created
            )
            ON CONFLICT(player_external_id, season_year, week, as_of_date)
            DO NOTHING
            """,
            {
                "ext": str(card.player_external_id),
                "s": int(card.season),
                "week": week,
                "as_of": card.as_of_date,
                "logline": card.logline,
                "why_now": card.why_now,
                "arc_state": _bible_arc_state_json(card),
                "tension": card.tension_text,
                "diff": diff_summary,
                "snapshot": json.dumps(asdict(card), default=str),
                "created": _now_utc(),
            },
        )
    except Exception:
        pass


def _upsert_bible(
    db, card: StoryCard, *, evidence: list[dict] | None, tier: str, content_hash: str
) -> None:
    """Upsert player_bible + append a snapshot ONLY on a MATERIAL change.

    Called from compute_story_cards AFTER the cache write succeeds. The change
    gate compares the SAME narrator content_hash the cache uses: identical hash ->
    no material change -> write NOTHING (idempotent nightly re-run). New row or a
    changed hash -> UPSERT the bible AND append one snapshot. Wrapped never-raise:
    one bad bible never aborts the batch. content_hash is passed in (the SAME the
    cache row stored) so bible / snapshot / cache always agree on "the story
    moved" — do NOT recompute it here with the local _content_hash helper."""
    try:
        if db is None or card is None or not getattr(card, "player_external_id", None):
            return
        ext = str(card.player_external_id)

        prior = _safe_one(
            db,
            """
            select content_hash, logline, why_now, arc_state_json,
                   current_beats_json
              from player_bible
             where player_external_id = :ext
            """,
            {"ext": ext},
        )
        # No material change: same hash as the last bible -> skip BOTH writes. This
        # is what keeps the changelog a real EKG and not a daily-noise log.
        if prior is not None and str(prior.get("content_hash") or "") == str(content_hash):
            return

        diff = _bible_diff_summary(prior, card)
        player_id = None
        try:
            player_id = _resolve_player_id_for_cache(db, ext)
        except Exception:
            player_id = None

        db.execute(
            """
            INSERT INTO player_bible (
                player_external_id, player_id, season_year,
                identity_json, permanent_beats_json, current_beats_json,
                canon_events_json, arc_state_json, archetype_slug,
                logline, logline_locked_event_id, why_now,
                data_coverage_flag, content_hash, updated_at_utc
            ) VALUES (
                :ext, :pid, :s,
                :identity, :permanent, :current,
                :canon, :arc, :archetype,
                :logline, NULL, :why_now,
                :coverage, :chash, :updated
            )
            ON CONFLICT(player_external_id) DO UPDATE SET
                player_id            = excluded.player_id,
                season_year          = excluded.season_year,
                identity_json        = excluded.identity_json,
                permanent_beats_json = excluded.permanent_beats_json,
                current_beats_json   = excluded.current_beats_json,
                canon_events_json    = excluded.canon_events_json,
                arc_state_json       = excluded.arc_state_json,
                archetype_slug       = excluded.archetype_slug,
                logline              = excluded.logline,
                why_now              = excluded.why_now,
                data_coverage_flag   = excluded.data_coverage_flag,
                content_hash         = excluded.content_hash,
                updated_at_utc       = excluded.updated_at_utc
            """,
            {
                "ext": ext,
                "pid": player_id,
                "s": int(card.season),
                "identity": _bible_identity_json(card),
                "permanent": _bible_permanent_beats_json(card),
                "current": _bible_current_beats_json(card),
                "canon": json.dumps([]),  # NEL canon is a later phase; honest empty.
                "arc": _bible_arc_state_json(card),
                "archetype": card.archetype_slug,
                "logline": card.logline,
                "why_now": card.why_now,
                "coverage": _bible_coverage_flag(card),
                "chash": str(content_hash),
                "updated": _now_utc(),
            },
        )

        week = _resolve_current_week(db, int(card.season))
        _write_bible_snapshot(db, card, week=week, diff_summary=diff)
    except Exception:
        # One bad bible never aborts the batch.
        pass


# ===========================================================================
# THE COMPUTE STEP (Phase 2) — compute_story_cards(...). The entry the new
# ``compute-story-cards`` CLI subcommand calls in the NIGHTLY ENRICH (non-critical;
# NOT build-site, NOT inline render). It:
#   1. warms player_ledger_scores + player_succession (the coverage guard wants
#      these populated; warming also gives fetch_ledger_lead stable evidence ids),
#   2. classifies every candidate's tier and, for S/T1 only, runs the confident-
#      compiler narrator (graceful: a None return keeps the deterministic prose),
#   3. PERSISTS each card to player_story_card_cache, content-hash-gated so
#      unchanged players are skipped and a failed generation keeps the prior LKG.
# build_card READS that cache; this step is the ONLY place generation runs.
# Returns a dict of counts. NEVER raises into the caller.
# ===========================================================================
def _llm_candidate_ids(db, season: int) -> list[int]:
    """Importance-ordered S/T1 candidate pool for the bounded LLM batch.

    The nightly compute is GPU-budgeted (``--limit``), so a bounded batch must
    hit the marquee players fans actually visit (and who carry real discourse to
    compile) — NOT an arbitrary slice of the ~23k-player roster (the old
    ``_roster_player_ids`` order, which put low-discourse long-tail players first
    and starved the batch). Ranks by the same signals ``classify_player_tier``
    reads: award/Heisman watch first, then 5-star, top-decile WEPA, 4-star, and a
    live (non-low-signal) aura row. The classifier stays the authority — this only
    orders a superset so ``[:limit]`` lands on the right players. Returns [] on any
    failure so the caller falls back to the raw roster.
    """
    rows = _safe_all(
        db,
        """
        WITH sig AS (
            SELECT player_id, 0 AS pri, -COALESCE(priority, 999) AS w
              FROM player_award_watch_2026
            UNION ALL
            SELECT player_id, 1, COALESCE(rating, 0)
              FROM player_recruiting_profiles WHERE stars = 5
            UNION ALL
            SELECT player_id, 2, ABS(metric_value)
              FROM player_value_metrics
             WHERE season_year = :s AND plays >= 50
               AND metric_name IN ('wepa_passing', 'wepa_rushing')
            UNION ALL
            SELECT player_id, 3, COALESCE(rating, 0)
              FROM player_recruiting_profiles WHERE stars = 4
            UNION ALL
            SELECT player_id, 4, COALESCE(aura_score, 0)
              FROM player_aura_weekly
             WHERE season_year = :s AND COALESCE(is_low_signal, 0) = 0
        )
        SELECT player_id
          FROM sig
         GROUP BY player_id
         ORDER BY MIN(pri) ASC, MAX(w) DESC
        """,
        {"s": int(season)},
    )
    out: list[int] = []
    seen: set[int] = set()
    for r in rows:
        pid = r.get("player_id")
        if pid is None:
            continue
        pid = int(pid)
        if pid not in seen:
            seen.add(pid)
            out.append(pid)
    return out


def compute_story_cards(
    db,
    season: int,
    players: list[int] | None = None,
    tiers: tuple[str, ...] | list[str] | None = None,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    warm: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Generate + cache LLM Story-Card prose for the S+T1 cohort.

    Args:
        db:       open Database handle.
        season:   season year (required).
        players:  optional numeric player_id allow-list (default = on-roster cohort).
        tiers:    LLM tiers to generate (default = ('S','T1')); T2/T3 stay deterministic.
        limit:    cap the number of candidates processed.
        force:    bypass the content-hash skip and regenerate every candidate.
        dry_run:  classify + content-hash only; no narration, no writes.
        warm:     warm the ledger + succession writers first (default True).

    Returns a dict of counts:
        {candidates, considered, generated, skipped, fell_back, deterministic,
         errors, tiers, season, dry_run}.
    NEVER raises (the enrich step is non-critical).
    """
    counts: dict[str, Any] = {
        "candidates": 0, "considered": 0, "generated": 0, "skipped": 0,
        "fell_back": 0, "deterministic": 0, "errors": 0,
        "season": None, "tiers": None, "dry_run": bool(dry_run),
    }
    try:
        if db is None or season is None:
            return counts
        season = int(season)
        counts["season"] = season

        # Lazy import (the narrator imports THIS module at top -> avoid a cycle).
        from . import story_card_narrator as nar

        tier_set = tuple(
            t.strip().upper()
            for t in (tiers if tiers else nar.LLM_TIERS)
            if t and str(t).strip()
        )
        counts["tiers"] = list(tier_set)

        if warm and not dry_run:
            try:
                nar._warm_detectors(db, season)
            except Exception:
                pass

        if players:
            pids = [int(p) for p in players]
        else:
            # Importance-ordered S/T1 cohort so a bounded --limit batch hits the
            # marquee players (real discourse) first, not the long-tail roster.
            try:
                pids = _llm_candidate_ids(db, season)
            except Exception:
                pids = []
            if not pids:  # signal tables empty -> fall back to the raw roster.
                try:
                    pids = nar._roster_player_ids(db, season)
                except Exception:
                    pids = []
        if limit is not None:
            pids = pids[: int(limit)]
        counts["candidates"] = len(pids)

        for pid in pids:
            try:
                tier = nar.classify_player_tier(db, pid, season)
                if tier not in tier_set or tier not in nar.LLM_TIERS:
                    continue
                counts["considered"] += 1

                card = build_card_payload(db, pid, season)
                if card is None:
                    continue

                evidence = nar.assemble_evidence(db, card)
                chash = nar.story_content_hash(card, tier, evidence)

                existing = read_fresh_card_cache(
                    db, card.player_external_id, season, content_hash=None
                )
                if (
                    not force
                    and existing
                    and str(existing.get("content_hash") or "") == str(chash)
                    and existing.get("prose_source") == "llm"
                ):
                    counts["skipped"] += 1
                    continue  # regen short-circuit: unchanged player, keep LLM prose.

                if dry_run:
                    if verbose:
                        ndocs = sum(1 for e in evidence if e.get("kind") == "discourse")
                        print(
                            f"  [dry-run] {tier} pid={pid} ext={card.player_external_id} "
                            f"docs={ndocs} hash={chash}",
                            flush=True,
                        )
                    continue

                prose = nar.narrate(db, card, tier, evidence=evidence)

                if prose and prose.get("prose_source") == "llm":
                    # PASS — overlay the FIVE structured prose fields onto the card,
                    # promote this row to LKG, persist. Graceful partial upgrade:
                    # a missing/empty structured field keeps the deterministic value
                    # for that slot (the narrator never blanks the card).
                    if prose.get("logline"):
                        card.logline = prose["logline"]            # short serif hook
                    # The dominant_take is the confident-compiler FANBASE take that
                    # pairs with the confidence meter — overlay only .text +
                    # .minority_take, keeping the deterministic .confidence /
                    # .source_count that drive the meter band.
                    if card.dominant_take is not None:
                        if prose.get("dominant_take_text"):
                            card.dominant_take.text = prose["dominant_take_text"]
                        if prose.get("minority_take"):
                            card.dominant_take.minority_take = prose["minority_take"]
                    if prose.get("body"):
                        card.body = prose["body"]                  # fuller expand prose
                    if prose.get("kicker"):
                        card.kicker = prose["kicker"]              # else keep deterministic
                    card.fallback_rung = "full"
                    card.fallback_reason = "llm prose"
                    # Tribal lenses (national + rival?). Reuse the SAME primary pass
                    # for national (pass `prose` so we don't re-narrate national);
                    # rival is a second audience-filtered pass added only when it
                    # clears the floor + eval. Purely additive, never-raise: any
                    # failure leaves card.lenses = None (single-voice, no toggle).
                    try:
                        card.lenses = _attach_lenses(nar, db, card, tier, evidence)
                    except Exception:
                        card.lenses = None
                    write_story_card_cache(
                        db, card, chash,
                        model_id=prose.get("model_id") or f"ollama:{nar.WRITER_MODEL}",
                        prose_source="llm",
                        is_lkg=1,
                        fallback_reason=None,
                        eval_factscore=prose.get("eval_factscore"),
                    )
                    # Bible + changelog: deterministic state, written AFTER the cache
                    # write succeeds (the bible only reflects a card that persisted).
                    # Own try/except inside the helper — one bad bible never aborts
                    # the batch and never blocks the LLM card that already shipped.
                    _upsert_bible(db, card, evidence=evidence, tier=tier, content_hash=chash)
                    counts["generated"] += 1
                    if verbose:
                        print(
                            f"  [llm] {tier} pid={pid} ext={card.player_external_id} "
                            f"factscore={prose.get('eval_factscore')}",
                            flush=True,
                        )
                else:
                    # FAIL — keep an existing usable LKG row (serve last-good).
                    if (
                        existing
                        and existing.get("is_lkg")
                        and existing.get("prose_source") in ("llm", "lkg")
                    ):
                        counts["fell_back"] += 1
                        if verbose:
                            print(
                                f"  [lkg-kept] {tier} pid={pid} ext={card.player_external_id}",
                                flush=True,
                            )
                        continue
                    # Else persist the deterministic card (no LLM, is_lkg=0).
                    card.fallback_reason = "deterministic (llm reject/unavailable)"
                    write_story_card_cache(
                        db, card, chash,
                        model_id="deterministic-v1",
                        prose_source="deterministic",
                        is_lkg=0,
                        fallback_reason=card.fallback_reason,
                    )
                    # The bible is deterministic STATE, not LLM state — write it for
                    # the fall-back card too (the deterministic logline IS what
                    # shipped here). content_hash is the SAME narrator hash the cache
                    # used, so bible/snapshot/cache all agree on "the story moved".
                    _upsert_bible(db, card, evidence=evidence, tier=tier, content_hash=chash)
                    counts["deterministic"] += 1
                    counts["fell_back"] += 1
            except Exception:
                # One bad player never aborts the batch (mirror write_ledger_scores).
                counts["errors"] += 1
                continue

        if verbose:
            print(
                f"compute_story_cards: season={season} tiers={','.join(tier_set)} "
                f"candidates={counts['candidates']} considered={counts['considered']} "
                f"generated={counts['generated']} skipped={counts['skipped']} "
                f"fell_back={counts['fell_back']} errors={counts['errors']}",
                flush=True,
            )
        return counts
    except Exception:
        return counts
