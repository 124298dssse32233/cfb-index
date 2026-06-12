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
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from .ledgers import fetch_ledger_lead
from .season_labels import _last_completed_season, _upcoming_season
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
    "SELECT_MODES",
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

# Per-achievement "surprise" weight for the BAN candidate pool (doc 41 §6).
# Encodes how NATIONAL / exceptional the distinction is so a real leaderboard
# rank outranks a mid perception gap (de-monopolizes the aura-delta BAN), while a
# team-relative leader stays weak enough to win only when nothing better exists.
# Honors badges are intentionally ABSENT — they're categorical (no honest single
# number) and belong in the selector grid, not the BAN. Source detectors live in
# ``cfb_rankings.bets.achievements``; ``rarity_pct`` there is a PERCENTAGE of the
# eligible pool (0..100), not a [0,1] fraction.
# BAN priority tiers (doc 41 §6). The four candidate families historically used
# non-comparable ad-hoc score formulas, so PEDIGREE could outscore proprietary
# PRODUCTION and a vanilla counting total could outscore the WEPA moat metric.
# We enforce the brand hierarchy STRUCTURALLY: pick the highest-priority tier that
# has any candidate, then the top score WITHIN that tier. Lower number = higher
# priority. This is what keeps the BAN from monopolizing on any single register.
_BAN_T_NATIONAL   = 1   # rarest, most legible national distinctions (leaderboard rank, extreme hype/tape gap)
_BAN_T_PRODUCTION = 2   # proprietary production (WEPA moat) + notable perception gaps + statistical twins
_BAN_T_VOLUME     = 3   # national counting-stat distinction (legible but vanilla; dups a chip)
_BAN_T_PEDIGREE   = 4   # recruiting rank — the honest hero ONLY for unproven players
_BAN_T_TEAM       = 5   # team-relative leader — last resort

# Aura gap >= this is a signature national story (hype vs tape), not just noise.
_BAN_AURA_NATIONAL_GAP = 25.0

# Per-achievement "surprise" weight (within-tier score). See _ACH_TIER for the
# priority class. Honors badges are intentionally absent (categorical -> no honest
# single number; they live in the selector grid, not the BAN).
_ACH_SURPRISE = {
    "achievement_money_efficiency":  1.00,  # national top-5 efficiency leaderboard
    "achievement_dual_threat":       0.85,  # top-50 in BOTH WEPA dims (proprietary, elite)
    "achievement_mirror_elite":      0.55,  # statistical twin of an honored player (comparative)
    "achievement_volume_king":       0.70,  # cleared a national volume bar
    "achievement_program_benchmark": 0.55,  # team-relative leader
}
_ACH_TIER = {
    "achievement_money_efficiency":  _BAN_T_NATIONAL,
    "achievement_dual_threat":       _BAN_T_NATIONAL,
    "achievement_mirror_elite":      _BAN_T_PRODUCTION,
    "achievement_volume_king":       _BAN_T_VOLUME,
    "achievement_program_benchmark": _BAN_T_TEAM,
}


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


def _as_of_date(as_of: str | None) -> _dt.date:
    """Parse the card's as_of ISO string to a date; fall back to today.

    The forward frame (the season we're previewing TOWARD) is derived from THIS
    date, never from the data `season` (= last completed). In June 2026 this is
    2026 while the stats are from 2025."""
    if as_of:
        try:
            return _dt.date.fromisoformat(str(as_of)[:10])
        except (TypeError, ValueError):
            pass
    return _dt.date.today()


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
def _paren_number(text: str | None) -> str | None:
    """Pull the comma/digit run inside the last (...) of a context string.

    "Team leader in rushing yards (775)." -> "775". Regex-free to avoid a new
    import; returns None when there's no parenthesised number."""
    if not text:
        return None
    s = str(text)
    close = s.rfind(")")
    open_ = s.rfind("(", 0, close) if close != -1 else -1
    if open_ == -1 or close == -1:
        return None
    inner = "".join(ch for ch in s[open_ + 1 : close] if ch.isdigit() or ch == ",")
    return inner or None


def _volume_bar(text: str | None) -> str | None:
    """Pull the threshold out of a volume-king context — reads the detector's
    OWN words so it can't drift from ``bets/achievements.py``.

    "... clears the 2,500-QB volume bar." -> "2,500". None if unparseable."""
    if not text:
        return None
    s = str(text)
    marker = "clears the "
    i = s.find(marker)
    if i == -1:
        return None
    tail = s[i + len(marker):]
    bar = "".join(ch for ch in tail.split("-", 1)[0] if ch.isdigit() or ch == ",")
    return bar or None


def _achievement_ban(row: dict[str, Any], card_season: int) -> tuple[int, float, Ban] | None:
    """Map one ``player_achievements`` row to a scored BAN candidate (doc 41 §6).

    Returns ``(tier, score, Ban)`` where ``tier`` is the priority class
    (``_ACH_TIER``) and ``score = surprise x rarity x recency`` is the WITHIN-tier
    rank. ``surprise`` is the per-type weight (``_ACH_SURPRISE``); ``rarity =
    1 - rarity_pct/100`` (rarity_pct is a pool PERCENTAGE, not a fraction);
    ``recency`` decays gently per prior season. Returns None for non-numeric /
    unknown achievements (honors badges, etc.) so the BAN stays number-welded."""
    aid = str(row.get("achievement_id") or "")
    base = _ACH_SURPRISE.get(aid)
    if base is None:
        return None  # unknown / non-numeric (e.g. honors badge) -> not a BAN
    rarity_pct = _to_float(row.get("rarity_pct"))
    if rarity_pct is None:
        return None  # rarity not yet computed -> can't honesty-gate; skip
    try:
        meta = json.loads(row.get("meta_json") or "{}")
    except (TypeError, ValueError):
        meta = {}
    rarity = max(0.0, min(1.0, 1.0 - rarity_pct / 100.0))
    ssn = _to_int(row.get("season_year")) or card_season
    recency = max(0.60, 1.0 - 0.15 * max(0, int(card_season) - int(ssn)))
    surprise = base
    number = label = kind = None

    if aid == "achievement_money_efficiency":
        rank = _to_int(meta.get("rank")) or 1
        ypa = _to_float(meta.get("ypa"))
        surprise = max(0.45, base - 0.12 * (rank - 1))   # #1=1.0 -> #5~=0.52
        rate = f"{ypa:.1f} Y/A · " if ypa is not None else ""
        number, label, kind = f"No.{rank}", f"{rate}QUALIFIED QBs", "rank"
    elif aid == "achievement_volume_king":
        val = _to_float(meta.get("value"))
        if val is None:
            return None
        # "PASS"/"RUSH"/"REC" from "passing_yds"/"rushing_yds"/"receiving_yds".
        stem = str(meta.get("metric") or "").split("_", 1)[0].lower()
        head = {"passing": "PASS", "rushing": "RUSH", "receiving": "REC"}.get(stem, "VOL")
        bar = _volume_bar(row.get("unlock_context"))           # drift-proof: detector's own words
        tag = f"{bar}-YD CLUB" if bar else "VOLUME TIER"
        number, label, kind = f"{int(round(val)):,}", f"{head} YDS · {tag}", "magnitude"
    elif aid == "achievement_program_benchmark":
        num = _paren_number(row.get("unlock_context"))
        if num is None:
            return None
        metric = str(meta.get("metric") or "team metric").upper()
        number, label, kind = num, f"TEAM {metric} LEADER", "magnitude"
    elif aid == "achievement_dual_threat":
        ranks = [r for r in (_to_int(meta.get("pass_rank")), _to_int(meta.get("rush_rank"))) if r]
        if not ranks:
            return None
        number, label, kind = f"No.{min(ranks)}", "DUAL-THREAT · WEPA PASS+RUSH", "rank"
    elif aid == "achievement_mirror_elite":
        sim = _to_int(meta.get("similarity_pct"))
        if not sim:
            return None
        number, label, kind = f"{sim}%", "MIRROR OF AN HONORED PLAYER", "magnitude"
    else:
        return None

    score = surprise * rarity * recency
    return (
        _ACH_TIER.get(aid, _BAN_T_TEAM),
        score,
        Ban(
            number=number,
            label=label,
            receipt=Receipt(
                table="player_achievements",
                detail=str(row.get("unlock_context") or "").strip() or f"{aid} · {ssn}",
            ),
            kind=kind,
        ),
    )


def _select_ban(db, player_id: int, season_year: int, position: str | None) -> Ban | None:
    """Pick the single most surprising-yet-honest true number (doc 41 §6).

    Candidates carry ``(tier, score, Ban)``: we take the HIGHEST-priority tier
    that has any candidate, then the top score within it. This enforces the brand
    hierarchy structurally — national distinction > proprietary production > vanilla
    volume > pedigree > team-relative — so the BAN never monopolizes on one register
    (see ``_BAN_T_*``)."""
    candidates: list[tuple[int, float, Ban]] = []

    # --- Candidate A: aura perception↔production gap (the hype-vs-tape number) ---
    #   An EXTREME gap (>= _BAN_AURA_NATIONAL_GAP) is a signature national story;
    #   a moderate gap (>= 12) is proprietary-production tier. Below 12 = noise.
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
                tier = (
                    _BAN_T_NATIONAL if abs(gap) >= _BAN_AURA_NATIONAL_GAP
                    else _BAN_T_PRODUCTION
                )
                candidates.append((
                    tier,
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

    # --- Candidate B: WEPA value (the proprietary moat metric) ----------------
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
            _BAN_T_PRODUCTION,
            0.6 * surprise + 0.2,
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

    # --- Candidate C: recruiting national rank (pedigree — unproven-only) ------
    #   Pedigree is tier 4: it is the honest hero number ONLY when the player has
    #   no production signal (no aura gap, no WEPA, no achievement). For anyone
    #   who has played, live production leads. (A stale 4-year-old star rating
    #   must never headline over a junior's actual tape.)
    rec = _fetch_recruiting(db, player_id)
    if rec:
        nat = _to_int(rec.get("national_rank"))
        stars = _to_int(rec.get("stars"))
        if nat is not None and 0 < nat <= 500:
            surprise = max(0.0, 1.0 - (nat / 500.0))  # rarer (lower rank) = higher
            star_tag = f"{stars}★ · " if stars else ""
            candidates.append((
                _BAN_T_PEDIGREE,
                surprise,
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

    # --- Candidate D: rare achievements (leaderboard ranks / volume / team) ----
    #   Real detectors in bets/achievements.py. Each carries its own priority tier
    #   (_ACH_TIER): a national #1 (e.g. YPA leader) is NATIONAL-tier and beats a
    #   moderate aura gap; volume-king is VOLUME-tier (below WEPA); a team leader
    #   is last-resort. Honors badges are non-numeric and excluded by
    #   _achievement_ban (they live in the selector grid).
    for ar in _safe_all(
        db,
        """
        select achievement_id, season_year, unlock_context, rarity_pct, meta_json
          from player_achievements
         where player_id = :pid and season_year <= :s
        """,
        {"pid": int(player_id), "s": int(season_year)},
    ):
        cand = _achievement_ban(ar, int(season_year))
        if cand is not None:
            candidates.append(cand)

    if not candidates:
        return None
    # Highest-priority tier first (lowest tier number), then top score within it.
    candidates.sort(key=lambda c: (c[0], -c[1]))
    return candidates[0][2]


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
def _build_tension(
    db, player_id: int, season_year: int, ledger: str | None = None
) -> str | None:
    """The curiosity-gap tension (doc 41 §4 / doc 43 §1.4).

    Grounded in the aura perception↔production gap, but the *phrasing* is keyed
    to the player's dominant ledger — so the tension voices WHY the perception
    runs hot (rival fixation / fan love / pure hope / an open verdict), not the
    same percentile sentence for everyone. A stable per-player rotation keeps
    two same-ledger players from reading identically (doc 42 §4b, anti-formula).
    Deterministic: same player + same data → same line.
    """
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
    p, q, mag = int(round(perc)), int(round(prod)), abs(int(round(gap)))
    led = (ledger or "").lower()

    if gap < 0:
        # Perception above tape ("aura tax") — phrased by the lead ledger.
        pools = {
            "grudge": [
                f"Rival boards can't stop bringing him up — a {p}th-percentile name against {q}th-percentile tape. Fear dressed up as mockery?",
                f"Opposing fans talk about him more than their own guy. The production sits at the {q}th. What are they actually bracing for?",
            ],
            "belonging": [
                f"The fanbase would run through a wall for him; the tape grades at the {q}th. Does the love still need the numbers?",
                f"{p}th-percentile beloved, {q}th-percentile productive — and around here only one of those is negotiable.",
            ],
            "hope": [
                f"The believers price him at the {p}th percentile on what's coming; today's tape says {q}th. Which season settles it?",
                f"All ceiling, for now — a {p}th-percentile bet riding on a {q}th-percentile résumé. The hope is the whole position.",
            ],
            "judgment": [
                f"The eye test files him at the {p}th; the résumé argues {q}th. The room hasn't returned a verdict.",
                f"Stat-padder or the real thing? {p}th-percentile buzz, {q}th-percentile production — the argument is the story.",
            ],
        }
        default = [
            f"The room sees a {p}th-percentile name; the tape grades at the {q}th — is the buzz ahead of the production?",
            f"The name carries {p}th-percentile weight; the snaps grade out {q}th. The gap is the open question.",
            f"{p}th-percentile reputation, {q}th-percentile tape — somewhere in that {mag}-point gap is who he really is.",
        ]
    else:
        # Produces above perception — underrated.
        pools = {
            "grievance": [
                f"The tape produces at the {q}th; the coverage treats him like the {p}th. The disrespect writes itself.",
                f"Quietly {q}th-percentile, publicly {p}th — and the fanbase has clocked exactly who's leaving him off the lists.",
            ],
        }
        default = [
            f"Fans price his perception around the {p}th percentile; the tape produces at the {q}th — why isn't he getting the credit?",
            f"The production ({q}th) is outrunning the reputation ({p}th). The recognition is the thing lagging behind.",
        ]

    pool = pools.get(led) or default
    return pool[int(player_id) % len(pool)]


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
    upcoming: int,
    lead: dict[str, Any] | None,
    succ: SuccessionRead | None,
    transferred: bool,
) -> str | None:
    """The heartbeat (doc 43 §6). calendar_pressure is EMPTY (doc 46 gotcha), so
    this degrades to a generic projective why-now — never blocks on the calendar.

    `upcoming` is the season we're previewing TOWARD (e.g. 2026 in June 2026),
    NOT the data season (= last completed, e.g. 2025). Every forward-looking
    statement here frames around `upcoming` so the offseason reads forward."""
    if transferred:
        return f"He changed programs heading into {upcoming} — a fresh fit to prove out."
    if succ is not None and getattr(succ, "clock_line", None):
        return f"The {succ.role} job is the open question heading into {upcoming}."
    if lead:
        ledger = str(lead.get("ledger") or "")
        if ledger == "hope":
            return f"He is squarely in the {upcoming} hype cycle — projection season."
        if ledger == "grievance":
            return f"The {upcoming} preseason slights are already feeding the chip."
        if ledger == "judgment":
            return f"His {upcoming} case is being argued before a snap is played."
    return f"The {upcoming} outlook is the live story — the offseason looks forward."


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
# Packet evidence fingerprint (doc 59 §11) — the SECOND regen trigger.
#
# The Packet Builder (player_pages/packet.py build_packet) emits a stable sha1 of
# hash(selected discourse doc_ids + structured fact keys). It is RICHER than the
# narrator spine hash's evidence_doc_ids set: it folds in the full §4 packet's
# selected discourse AND structured fact keys, so new discourse forces a rewrite
# even when the BAN / chips / ledger-lead spine is unchanged. The cadence regen
# trigger fires when the spine hash OR this fingerprint moved since the last cache
# write (doc 59 §11 keystone). Best-effort: returns "" on any failure (the gate
# then degrades to content_hash only — never blocks, never raises).
# ===========================================================================
def _packet_fingerprint(db, external_id: str, season: int) -> str:
    """Stable packet evidence fingerprint for (external_id, season) — doc 59 §11.

    Builds the §4 evidence packet (itself never-raises) and returns its
    ``evidence_fingerprint``. Returns "" on any failure so the caller can treat a
    missing/unstable fingerprint as 'no second signal' and fall back to the spine
    hash alone. NEVER raises.
    """
    try:
        if db is None or not external_id or season is None:
            return ""
        from . import packet as _packet

        upcoming = _upcoming_season(_as_of_date(_today()))
        pk = _packet.build_packet(
            db, str(external_id), int(season), upcoming_season=int(upcoming)
        )
        return str(getattr(pk, "evidence_fingerprint", "") or "")
    except Exception:
        return ""


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
# Additive column from migration 20260612_02 (doc 59 §11 cadence trigger). Probed
# INDEPENDENTLY of the 03 set — a DB may carry the 03 columns but not this one, so
# folding it into _CACHE_EXTRA_COLUMNS would wrongly downgrade those DBs to the
# legacy write path. The fingerprint write/read is gated on this single column.
_CACHE_FINGERPRINT_COLUMN = "evidence_fingerprint"

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
    evidence_fingerprint: str | None = None,
) -> bool:
    """Upsert ``card`` into player_story_card_cache. Returns True on a write.

    Additive-only: never alters existing data beyond this player-season row, and
    degrades to the legacy column set when the 20260611_03 columns are absent.
    The packet ``evidence_fingerprint`` (doc 59 §11) is persisted in a separate
    guarded UPDATE when the 20260612_02 column exists, so it rides alongside the
    content_hash WITHOUT forking the four INSERT variants. NEVER raises
    (per-player non-critical).
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
        else:
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

        # Persist the packet evidence fingerprint (doc 59 §11) in a separate
        # guarded UPDATE so it rides alongside the content_hash WITHOUT forking the
        # INSERT variants above. Only when the 20260612_02 column is present;
        # absent column -> no-op (the gate then falls back to content_hash only).
        if _CACHE_FINGERPRINT_COLUMN in cols:
            try:
                db.execute(
                    "UPDATE player_story_card_cache "
                    "SET evidence_fingerprint = :fp "
                    "WHERE player_external_id = :ext AND season_year = :s",
                    {
                        "fp": evidence_fingerprint,
                        "ext": str(card.player_external_id),
                        "s": int(card.season),
                    },
                )
            except Exception:
                pass  # fingerprint is a non-critical optimization hint.
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
        # The packet fingerprint (doc 59 §11) is probed independently of the 03 set.
        fp_col = (
            ", evidence_fingerprint" if _CACHE_FINGERPRINT_COLUMN in cols else ""
        )
        if have_extras:
            row = _safe_one(
                db,
                f"""
                select card_json, content_hash, card_tier, fallback_rung,
                       model_id, coalesce(is_lkg, 0) as is_lkg, prose_source,
                       fallback_reason, eval_factscore{fp_col}
                  from player_story_card_cache
                 where player_external_id = :ext and season_year = :s
                """,
                {"ext": str(external_id), "s": int(season_year)},
            )
        else:
            row = _safe_one(
                db,
                f"""
                select card_json, content_hash, card_tier, fallback_rung,
                       model_id{fp_col}
                  from player_story_card_cache
                 where player_external_id = :ext and season_year = :s
                """,
                {"ext": str(external_id), "s": int(season_year)},
            )
            if row is not None:
                # Synthesize the additive fields the caller expects.
                row.setdefault("is_lkg", 0)
                # Infer prose source from the model id when the column is absent.
                # An LLM card is either ollama: (local mistral) or anthropic:
                # (the Sonnet API writer, doc 59 §2); everything else = deterministic.
                mid = str(row.get("model_id") or "")
                if mid.startswith("anthropic:"):
                    _inferred = "sonnet"
                elif mid.startswith("ollama:"):
                    _inferred = "mistral"
                else:
                    _inferred = "deterministic"
                row.setdefault("prose_source", _inferred)
        if not row:
            return None
        # Uniform key for the caller whether or not the column exists yet (the
        # cadence gate reads existing.get('evidence_fingerprint')). NULL/absent ->
        # None, which the gate treats as "never fingerprinted -> regen".
        row.setdefault("evidence_fingerprint", None)
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
        # Forward frame: the season we're previewing TOWARD, derived from the
        # card's as_of date (NOT the data `season`, which is the last completed
        # season the stats come from). In June 2026: upcoming=2026, stats=2025.
        upcoming = _upcoming_season(_as_of_date(as_of))

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
        tension = _build_tension(
            db, player_id, season_year,
            (str(lead.get("ledger")) if lead else None),
        )
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
            why_now = _build_why_now(upcoming, lead, succ, transferred)
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
    # LLM-written prose is 'sonnet' (Anthropic API) | 'mistral' (Ollama) | legacy
    # 'llm'; plus 'lkg' (last-known-good). A deterministic row carries nothing the
    # live build lacks, so skip the overlay for it.
    if str(head.get("prose_source") or "") not in ("sonnet", "mistral", "llm", "lkg"):
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
    _hsrc = str(head.get("prose_source") or "")
    if _hsrc in ("sonnet", "mistral", "llm"):
        card.fallback_reason = f"{_hsrc} prose (cached)"
    else:
        card.fallback_reason = "lkg prose (stale-ok)"


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
def _attach_lenses(nar, db, card: StoryCard, tier: str, evidence, writer: str = "mistral") -> dict | None:
    """Build the tribal-lens payload via the narrator's narrate_lenses.

    The narrator owns everything: the rival representativeness floor, the rival
    second pass + eval gate, and the lens-dict shape. It re-runs national from
    `evidence` (the SAME pool the primary pass already used), so the national lens
    equals the prose already overlaid onto the card — no divergence, no second
    national cost beyond one re-narrate. ``writer`` routes the lens passes to the
    same backend the primary pass used (doc 59 §2 — 'sonnet' for the top-50).
    Returns {"national":{...}, "rival":{...}?} or None (then the card renders
    single-voice, no toggle). NEVER raises."""
    try:
        return nar.narrate_lenses(db, card, tier, evidence=evidence, writer=writer)
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
def _most_talked_about_ids(db, season: int) -> list[int]:
    """The 'most talked about' cohort (doc 59 §2 / §4.1.1) — ordered by the latest
    week's ``player_aura_weekly.mention_count`` DESC, non-low-signal only.

    This is the FORWARD-COHORT half of the selector: the players fans are actually
    arguing about right now (Joey Aguilar's 199 mentions with zero watch-list
    pedigree get the writer here, where the importance pool would miss them). Unioned
    with ``_llm_candidate_ids`` (the pedigree pool) in ``compute_story_cards`` and the
    union is then run through ``eligibility.filter_active`` so DEPARTED players (Beck
    et al.) drop from the forward cohort. Returns [] on any failure (the caller falls
    back to the importance pool alone). NEVER raises."""
    rows = _safe_all(
        db,
        """
        SELECT paw.player_id, paw.mention_count
          FROM player_aura_weekly paw
         INNER JOIN (
               SELECT player_id, MAX(week) AS max_week
                 FROM player_aura_weekly
                WHERE season_year = :s
                  AND COALESCE(is_low_signal, 0) = 0
                GROUP BY player_id
         ) latest
            ON latest.player_id = paw.player_id
           AND latest.max_week  = paw.week
         WHERE paw.season_year = :s
           AND COALESCE(paw.is_low_signal, 0) = 0
         ORDER BY paw.mention_count DESC
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


# Cap for the Sonnet-routed cohort (doc 59 §2 — the "live top-50").
_SONNET_TOP50_CAP = int(os.environ.get("CFB_INDEX_SONNET_TOP50_CAP", "50"))


def _sonnet_top50_ids(db, season: int) -> set[int]:
    """The live top-50 active player_ids routed to the Sonnet API (doc 59 §2/§14.6).

    Mirrors the compute-step cohort selector: the mention-first UNION of
    ``_most_talked_about_ids`` (player_aura_weekly.mention_count DESC) and the
    importance pool ``_llm_candidate_ids``, run through ``eligibility.filter_active``
    to drop DEPARTED players, then capped at ``_SONNET_TOP50_CAP`` (50). Returned as
    a SET for O(1) per-card writer routing. Returns an empty set on any failure ->
    the whole batch then routes to local mistral (the existing behavior; never a
    crash, never blocks the deploy). NEVER raises."""
    try:
        try:
            talked = _most_talked_about_ids(db, season)
        except Exception:
            talked = []
        try:
            importance = _llm_candidate_ids(db, season)
        except Exception:
            importance = []
        ordered: list[int] = []
        seen: set[int] = set()
        for pid in (*talked, *importance):
            try:
                ipid = int(pid)
            except (TypeError, ValueError):
                continue
            if ipid not in seen:
                seen.add(ipid)
                ordered.append(ipid)
        # Drop DEPARTED players so a player who blew up last year but has since
        # left never gets the frontier writer for a 2026 preview (doc 59 §4.1.1).
        try:
            from . import eligibility as _elig

            upcoming = _upcoming_season(_as_of_date(_today()))
            filtered = _elig.filter_active(db, ordered, upcoming_season=upcoming)
            if filtered:  # never let the gate empty the cohort
                ordered = filtered
        except Exception:
            pass
        return set(ordered[:_SONNET_TOP50_CAP])
    except Exception:
        return set()


# ===========================================================================
# --select cohort modes (doc 59 §11). The compute step resolves a candidate
# player_id list; --select narrows/reorders WHICH of them this run touches:
#   'sweep'    — the full cohort (the union selector / passed allow-list). The
#                explicit name for "do the whole list this beat" (the Sunday recap
#                / nightly full pass). Identical to today's default ordering.
#   'hot-list' — only the players who MOVED most since the last run: a jumped
#                mention_count (latest aura week vs the prior week) OR a changed
#                packet evidence fingerprint vs the cached one. The cheap mid-week
#                beat (Mon / Thu-Fri) that rewrites just the handful that shifted,
#                keeping the API bill tiny (doc 59 §11/§15 D-1).
#   None       — default; today's behavior (the full cohort, no extra filtering).
# Both modes return a SUBSET of `base_pids` in priority order; on any failure they
# fall back to `base_pids` unchanged (never empty a run, never raise).
# ===========================================================================
def _mention_movers(db, season: int) -> dict[int, float]:
    """player_id -> |latest-week mention_count - prior-week mention_count|.

    The two most recent non-low-signal aura weeks per player drive a movement
    score; a player present in only one week scores its lone mention_count (a
    first-sighting IS movement). Returns {} on any failure. NEVER raises."""
    rows = _safe_all(
        db,
        """
        WITH ranked AS (
            SELECT player_id, week, mention_count,
                   ROW_NUMBER() OVER (
                       PARTITION BY player_id ORDER BY week DESC
                   ) AS rn
              FROM player_aura_weekly
             WHERE season_year = :s
               AND COALESCE(is_low_signal, 0) = 0
        )
        SELECT player_id,
               MAX(CASE WHEN rn = 1 THEN mention_count END) AS cur,
               MAX(CASE WHEN rn = 2 THEN mention_count END) AS prev
          FROM ranked
         WHERE rn <= 2
         GROUP BY player_id
        """,
        {"s": int(season)},
    )
    out: dict[int, float] = {}
    for r in rows:
        pid = _to_int(r.get("player_id"))
        if pid is None:
            continue
        cur = _to_float(r.get("cur")) or 0.0
        prev = _to_float(r.get("prev"))
        # No prior week -> the player's whole current volume is "new" movement.
        out[pid] = abs(cur - prev) if prev is not None else cur
    return out


def _hot_list_ids(db, season: int, base_pids: list[int]) -> list[int]:
    """The 'moved most since last run' subset of ``base_pids`` (doc 59 §11).

    A candidate is HOT when EITHER its mention_count jumped (latest aura week vs
    prior) OR its packet evidence fingerprint changed vs the cached one. Ranked by
    the mention-movement magnitude (fingerprint-only movers sort after, by a small
    positive floor so they still qualify). Returns a SUBSET of ``base_pids`` in
    priority order; falls back to ``base_pids`` unchanged on any failure or when
    nothing moved (an empty hot-list would silently skip the whole beat — better to
    run the cohort than ship nothing). NEVER raises."""
    try:
        if not base_pids:
            return base_pids
        movers = _mention_movers(db, season)
        scored: list[tuple[float, int]] = []
        for pid in base_pids:
            try:
                ipid = int(pid)
            except (TypeError, ValueError):
                continue
            score = float(movers.get(ipid, 0.0))
            moved = score > 0.0
            if not moved:
                # Second signal: did the packet fingerprint move vs the cache?
                ext = resolve_external_id(db, ipid)
                if ext:
                    cached = read_fresh_card_cache(db, ext, season, content_hash=None)
                    live_fp = _packet_fingerprint(db, ext, season)
                    cached_fp = str((cached or {}).get("evidence_fingerprint") or "")
                    if live_fp and live_fp != cached_fp:
                        moved = True
                        score = 0.5  # small positive floor: fingerprint-only mover.
            if moved:
                scored.append((score, ipid))
        if not scored:
            return base_pids  # nothing moved -> run the cohort (never ship nothing).
        scored.sort(key=lambda t: t[0], reverse=True)
        return [pid for _, pid in scored]
    except Exception:
        return base_pids


def _apply_select_mode(db, season: int, base_pids: list[int], select: str | None) -> list[int]:
    """Resolve a candidate list per the --select mode (doc 59 §11). NEVER raises."""
    mode = (select or "").strip().lower()
    if mode in ("", "default"):
        return base_pids
    if mode == "sweep":
        return base_pids  # the full cohort, explicitly.
    if mode == "hot-list":
        return _hot_list_ids(db, season, base_pids)
    # Unknown mode -> degrade to the full cohort (never empty a run).
    return base_pids


# Recognized --select modes (the CLI choices + the public contract).
SELECT_MODES = ("sweep", "hot-list")


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
    select: str | None = None,
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
        select:   cohort mode (doc 59 §11) — None (default; full cohort) |
                  'sweep' (the full cohort, explicit) | 'hot-list' (only the
                  players whose mention_count or packet fingerprint moved most
                  since the last run). Applied AFTER the cohort is assembled and
                  BEFORE the --limit slice.

    Returns a dict of counts:
        {candidates, considered, generated, skipped, fell_back, deterministic,
         errors, tiers, season, dry_run, select}.
    NEVER raises (the enrich step is non-critical).
    """
    counts: dict[str, Any] = {
        "candidates": 0, "considered": 0, "generated": 0, "skipped": 0,
        "fell_back": 0, "deterministic": 0, "errors": 0,
        "season": None, "tiers": None, "dry_run": bool(dry_run),
        "select": (select or "default"),
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

        # The Sonnet-routed cohort (doc 59 §2/§14.6): the live top-50 active
        # players (most-talked-about ∪ importance, post eligibility.filter_active,
        # capped 50) are written by the Anthropic API; everyone else in S/T1 stays
        # on local mistral. Computed alongside the candidate list so the per-pid
        # writer decision below is O(1) set membership. Empty on any failure ->
        # the whole batch routes to mistral (the existing behavior).
        sonnet_top50: set[int] = _sonnet_top50_ids(db, season)

        if players:
            pids = [int(p) for p in players]
        else:
            # Forward cohort (doc 59 §2 / §4.1.1) = the UNION of 'most talked about'
            # (player_aura_weekly.mention_count DESC) and the importance/pedigree
            # pool, mention-first so a bounded --limit batch hits the players fans
            # argue about now (Aguilar) AND the marquee pedigree (Manning). The union
            # is then filtered through eligibility.filter_active so DEPARTED players
            # (drafted/transferred-out/graduated — Beck et al.) drop from the forward
            # top-50; they recast as ghosts in successors' cards, never as a 2026
            # preview. Each step degrades gracefully to the prior behavior.
            try:
                talked = _most_talked_about_ids(db, season)
            except Exception:
                talked = []
            try:
                importance = _llm_candidate_ids(db, season)
            except Exception:
                importance = []
            # Mention-first union, de-duped, order preserved.
            pids = []
            _seen: set[int] = set()
            for pid in (*talked, *importance):
                try:
                    ipid = int(pid)
                except (TypeError, ValueError):
                    continue
                if ipid not in _seen:
                    _seen.add(ipid)
                    pids.append(ipid)
            # Eligibility gate: drop DEPARTED, keep ACTIVE + UNCERTAIN (never-raise;
            # on any failure keep the unfiltered union — better an extra card than a
            # silently-dropped cohort).
            try:
                from . import eligibility as _elig

                upcoming = _upcoming_season(_as_of_date(_today()))
                filtered = _elig.filter_active(db, pids, upcoming_season=upcoming)
                if filtered:  # never let the gate empty the cohort
                    pids = filtered
            except Exception:
                pass
            if not pids:  # signal tables empty -> fall back to the raw roster.
                try:
                    pids = nar._roster_player_ids(db, season)
                except Exception:
                    pids = []
        # --select cohort mode (doc 59 §11). Applied to the assembled list (the
        # union cohort OR an explicit --players allow-list) BEFORE the --limit
        # slice, so 'hot-list' narrows to the movers FIRST and --limit then caps
        # that already-prioritized subset. None/'sweep' keep the full cohort.
        pids = _apply_select_mode(db, season, pids, select)
        if limit is not None:
            pids = pids[: int(limit)]
        counts["candidates"] = len(pids)
        # Per-card prose_source tally for the loud-on-fallback summary (doc 59 §12).
        prose_sources: list[str] = []

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
                # The packet evidence fingerprint (doc 59 §11) — the SECOND regen
                # signal. Built once per card; persisted on every write so the next
                # run can compare. "" when the packet is unavailable (the gate then
                # degrades to the spine hash alone).
                fingerprint = _packet_fingerprint(db, card.player_external_id, season)

                existing = read_fresh_card_cache(
                    db, card.player_external_id, season, content_hash=None
                )
                # CADENCE REGEN TRIGGER (doc 59 §11): skip ONLY when the player is
                # unchanged on BOTH signals — the deterministic SPINE hash AND the
                # packet evidence fingerprint. Richer discourse moves the
                # fingerprint even when the BAN/chips/ledger spine is steady, so it
                # now forces a rewrite. Unchanged player + unchanged fingerprint
                # still skips (cost stays low). A previously-cached row with NO
                # fingerprint (NULL, pre-migration / first sight) fails the
                # fingerprint match and regenerates exactly once, then carries it.
                if not force and existing and existing.get("prose_source") in (
                    "sonnet", "mistral", "llm"
                ):
                    spine_same = str(existing.get("content_hash") or "") == str(chash)
                    fp_same = str(existing.get("evidence_fingerprint") or "") == str(fingerprint)
                    if spine_same and fp_same:
                        counts["skipped"] += 1
                        continue  # regen short-circuit: nothing moved, keep LLM prose.

                if dry_run:
                    if verbose:
                        ndocs = sum(1 for e in evidence if e.get("kind") == "discourse")
                        print(
                            f"  [dry-run] {tier} pid={pid} ext={card.player_external_id} "
                            f"docs={ndocs} hash={chash} fp={fingerprint[:12]}",
                            flush=True,
                        )
                    continue

                # Route the live top-50 to Sonnet (doc 59 §2); everyone else to
                # the local mistral path. The narrator runs the §12 fallback
                # ladder internally (Sonnet → mistral) and reports which backend
                # actually wrote the card via prose_source.
                writer = "sonnet" if int(pid) in sonnet_top50 else "mistral"
                prose = nar.narrate(db, card, tier, evidence=evidence, writer=writer)

                # prose_source is now the BACKEND ('sonnet'|'mistral'), not 'llm'.
                _ps = (prose or {}).get("prose_source")
                _is_llm = bool(prose) and _ps in ("sonnet", "mistral", "llm")
                if prose and _is_llm:
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
                    # Record the actual backend so prose_source is 'sonnet' or
                    # 'mistral', not a flat 'llm' (doc 59 §3/§12). Legacy rows that
                    # only said 'llm' still read fine downstream.
                    _src = _ps if _ps in ("sonnet", "mistral") else "mistral"
                    card.fallback_reason = f"{_src} prose"
                    # Tribal lenses (national + rival?). Reuse the SAME primary pass
                    # for national (pass `prose` so we don't re-narrate national);
                    # rival is a second audience-filtered pass added only when it
                    # clears the floor + eval. Route to the SAME backend the primary
                    # pass used. Purely additive, never-raise: any failure leaves
                    # card.lenses = None (single-voice, no toggle).
                    try:
                        card.lenses = _attach_lenses(nar, db, card, tier, evidence, writer=writer)
                    except Exception:
                        card.lenses = None
                    write_story_card_cache(
                        db, card, chash,
                        model_id=prose.get("model_id") or f"ollama:{nar.WRITER_MODEL}",
                        prose_source=_src,
                        is_lkg=1,
                        fallback_reason=None,
                        eval_factscore=prose.get("eval_factscore"),
                        evidence_fingerprint=fingerprint,
                    )
                    prose_sources.append(_src)
                    # Bible + changelog: deterministic state, written AFTER the cache
                    # write succeeds (the bible only reflects a card that persisted).
                    # Own try/except inside the helper — one bad bible never aborts
                    # the batch and never blocks the LLM card that already shipped.
                    _upsert_bible(db, card, evidence=evidence, tier=tier, content_hash=chash)
                    counts["generated"] += 1
                    if verbose:
                        print(
                            f"  [{_src}] {tier} pid={pid} ext={card.player_external_id} "
                            f"factscore={prose.get('eval_factscore')}",
                            flush=True,
                        )
                else:
                    # FAIL — keep an existing usable LKG row (serve last-good).
                    if (
                        existing
                        and existing.get("is_lkg")
                        and existing.get("prose_source") in ("sonnet", "mistral", "llm", "lkg")
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
                        evidence_fingerprint=fingerprint,
                    )
                    # The bible is deterministic STATE, not LLM state — write it for
                    # the fall-back card too (the deterministic logline IS what
                    # shipped here). content_hash is the SAME narrator hash the cache
                    # used, so bible/snapshot/cache all agree on "the story moved".
                    _upsert_bible(db, card, evidence=evidence, tier=tier, content_hash=chash)
                    counts["deterministic"] += 1
                    counts["fell_back"] += 1
                    # Only a TOP-50 card that should have been Sonnet counts toward
                    # the loud-on-fallback share — a non-top-50 mistral deterministic
                    # fall is normal and must not drag the Sonnet floor.
                    if int(pid) in sonnet_top50:
                        prose_sources.append("deterministic")
            except Exception:
                # One bad player never aborts the batch (mirror write_ledger_scores).
                counts["errors"] += 1
                continue

        # LOUD-ON-FALLBACK summary (doc 59 §12). Tally the per-card prose_source
        # over the SONNET-routed top-50 and surface the Sonnet share so the beat
        # job can fail loudly when the API-written share drops below the floor for
        # a non-thin reason. We only compute/return it here (alert wiring is the
        # caller's job); never-raise so it can't break the enrich step.
        try:
            top50_sources = [s for s in prose_sources]
            from . import anthropic_backend as _ab

            summary = _ab.summarize_prose_sources(top50_sources)
            counts["prose_source_counts"] = summary.get("counts")
            counts["sonnet_share"] = summary.get("sonnet_share")
            counts["sonnet_alert"] = summary.get("alert")
            if verbose and summary.get("total"):
                print(
                    f"  [prose-source] sonnet={summary.get('sonnet')}/{summary.get('total')} "
                    f"share={summary.get('sonnet_share')} alert={summary.get('alert')} "
                    f"counts={summary.get('counts')}",
                    flush=True,
                )
        except Exception:
            pass

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
