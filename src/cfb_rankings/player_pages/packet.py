"""Player Evidence Packet Builder — the data-completeness contract (LOCKED).

Spec: ``docs/design-system/59-player-evidence-packet-contract.md`` (LOCKED design,
2026-06-12). Build step 14.4. ZERO LLM / ZERO network — pure structured reads +
the already-built discourse pool.

WHY THIS EXISTS (doc 59 §0)
---------------------------
We proved (Nico Iamaleava, 2026-06-12) that a frontier writer handed the COMPLETE
data pile writes at the ceiling, and the same writer handed a thin/truncated pile
writes a thin card. The quality of a Story Card is BOUNDED by the completeness and
honesty of the evidence packet, not by the cleverness of the model. This module is
NOT a writer — it is the Packet Builder: for ONE player it gathers every available
fact and every relevant fan voice (doc 59 §4), wraps each atomic fact in the
universal Fact envelope (doc 59 §3) with a VALENCE and a SUPPRESSION rule, and
hands the result to whichever writer is on duty (Sonnet API / local mistral /
deterministic template). The packet is writer-agnostic (doc 59 §2).

THE FACT ENVELOPE (doc 59 §3)
-----------------------------
Every atomic fact is a :class:`Fact` carrying ``key`` / ``value`` / ``display`` /
``source_id`` (the citation anchor) / ``source_kind`` / ``valence`` (the direction
of the fact) / ``evidence_bar`` (what must be true to assert it) / ``suppress_when``
(the machine-evaluable silence predicate) / ``confidence``. Two rules fall straight
out: no fact is asserted as narrative unless it clears ``evidence_bar``; and if
``suppress_when`` is true the fact is dropped from the writer's "use these" set
(doc 59 §3 / §6 suppression catalog).

NIL RULE (doc 59 §7 — LOCKED)
-----------------------------
``player_nil_valuations`` (the MODELED number) is NEVER queried by this module —
grep this file for it and you will find only this comment. The NIL STORY is derived
from DISCOURSE docs whose text matches nil/collective/holdout/rev-share/buyout/
"more money" (the holdout, the portal-for-money snark, "the Joey Aguilar situation")
plus the structured portal event (``transfer_entries``). Reported dollar figures are
quotable WITH attribution because they are facts ABOUT the discourse, anchored to a
``doc:`` source_id; modeled figures are never emitted.

EVIDENCE FINGERPRINT (doc 59 §11)
---------------------------------
``Packet.evidence_fingerprint`` is a stable sha1 of ``sorted(selected discourse
doc_ids) + sorted(structured fact keys)``. Deterministic across runs/processes. The
regen trigger fires when either the deterministic spine OR this fingerprint moves —
so new discourse forces a rewrite even when the chips are unchanged, while unchanged
players still skip.

CONTRACT (doc 59 §12)
---------------------
:func:`build_packet` NEVER raises into the render path. Every section is wrapped in
its own try/except that degrades to an EMPTY list on any failure (missing table,
bad column, locked DB), never an exception. A missing source is reflected as an
absent/empty section so coverage (doc 59 §8) does not punish a player for data we do
not have.

Stable key: the packet is keyed on ``player_external_id`` = the cfbd athlete id
(``player_source_ids.source_player_id`` WHERE source_name='cfbd'), the linkrot
anchor. The numeric ``player_id`` is resolved internally for the per-table reads.

Public API:
    Fact (dataclass)            — the universal envelope (doc 59 §3)
    Packet (dataclass)          — one (player_external_id, season) packet (doc 59 §4)
    build_packet(db, player_external_id, season, *, upcoming_season=2026) -> Packet
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .season_labels import _last_completed_season, _upcoming_season


# ===========================================================================
# §3 — The universal Fact envelope. Every atomic fact in every section is one of
# these. ``valence`` is the DIRECTION of the fact (improved/declined/positive/
# aura_tax/...). ``evidence_bar`` states what must be true to ASSERT it as
# narrative. ``suppress_when`` is the machine-evaluable SILENCE predicate (a short
# human-readable string per the §6 catalog; the builder also pre-evaluates it and
# drops/keeps via the ``suppressed`` convenience flag so a writer/consumer needn't
# re-parse the predicate).
# ===========================================================================
@dataclass
class Fact:
    key: str
    value: Any
    display: str
    source_id: str
    source_kind: str  # 'structured' | 'discourse'
    valence: Optional[str] = None
    evidence_bar: str = ""
    suppress_when: Optional[str] = None
    confidence: float = 1.0
    # Convenience: the builder's pre-evaluation of suppress_when (doc 59 §3/§6).
    # True => this fact is dropped from the writer's "use these" set (it may still
    # be carried for context). Defaults False (no suppression).
    suppressed: bool = False


# ===========================================================================
# §4 — The packet schema. One packet per (player_external_id, season). Sections is
# keyed by the §4 section name; each value is a list[Fact].
# ===========================================================================
@dataclass
class Packet:
    player_external_id: str
    season: int
    identity: dict
    season_clock: dict  # {"upcoming": int, "last_completed": int}
    eligibility: dict   # {"status": ..., "reason": ..., "on_upcoming_roster": ...}
    sections: dict  # str -> list[Fact], keyed by §4 section name
    evidence_fingerprint: str = ""


# The canonical §4 section keys (the packet always carries every key, possibly to
# an empty list — coverage reads availability vs capture per section).
SECTION_KEYS: tuple[str, ...] = (
    "discourse",
    "before_after",
    "recruiting",
    "honors",
    "award_watch",
    "depth_chart",
    "transfer",
    "aura",
    "succession",
    "nil_narrative",
    "ledger_take",
)


# ===========================================================================
# Crash-proof DB helpers (mirror eligibility/succession/ledgers — never raise).
# ===========================================================================
def _safe_one(db, sql: str, params: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        return db.query_one(sql, params)
    except Exception:
        return None


def _safe_all(db, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return db.query_all(sql, params) or []
    except Exception:
        return []


def _to_int(v: Any) -> Optional[int]:
    try:
        if v is None or v == "":
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt_num(v: Any) -> str:
    """Compact human number: drop a trailing .0, keep meaningful decimals."""
    f = _to_float(v)
    if f is None:
        return str(v) if v is not None else ""
    if abs(f - round(f)) < 1e-9:
        return f"{int(round(f)):,}"
    return f"{f:g}"


def _resolve_player_id(db, player_external_id: str) -> Optional[int]:
    """cfbd external id -> numeric player_id (the linkrot anchor resolution)."""
    if db is None or not player_external_id:
        return None
    row = _safe_one(
        db,
        "select player_id from player_source_ids "
        "where source_player_id = :ext and source_name = 'cfbd' limit 1",
        {"ext": str(player_external_id)},
    )
    return _to_int((row or {}).get("player_id"))


# ===========================================================================
# §4.6 award slug -> display-name map (doc 59 §4.6, verbatim).
# ===========================================================================
_AWARD_NAMES: dict[str, str] = {
    "heisman": "Heisman",
    "davey_obrien": "Davey O'Brien (QB)",
    "maxwell": "Maxwell",
    "manning": "Manning",
    "biletnikoff": "Biletnikoff (WR)",
    "butkus": "Butkus (LB)",
    "bednarik": "Bednarik",
    "doak_walker": "Doak Walker (RB)",
    "lombardi": "Lombardi",
    "lou_groza": "Lou Groza (K)",
    "mackey": "Mackey (TE)",
    "hornung": "Paul Hornung",
}


def _award_display(slug: Any) -> str:
    s = str(slug or "").strip().lower()
    return _AWARD_NAMES.get(s, s.replace("_", " ").title() if s else "watch list")


# ===========================================================================
# §4.11 / §7 NIL narrative detector — discourse-only. NEVER queries
# player_nil_valuations (the modeled number). Matches the NIL STORY keywords.
# ===========================================================================
_NIL_PATTERN = re.compile(
    r"\b("
    r"nil|collective|holdout|held out|rev[\s-]?share|revenue[\s-]?shar|buyout|"
    r"more money|pay raise|raise his pay|portal for money|bag\b|the bag|"
    r"reportedly sought|guarantee[d]?\s+money"
    r")\b",
    re.IGNORECASE,
)

# Reported-figure detector (a $ amount in a discourse doc — quotable WITH
# attribution per §7; the figure itself is a fact ABOUT the discourse).
_DOLLAR_PATTERN = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|million|thousand)?", re.IGNORECASE)


# ===========================================================================
# Re-export the relevance + toxicity gates from ledgers (single source of truth).
# Degrade to the documented defaults if ledgers can't import.
# ===========================================================================
try:  # pragma: no cover - cheap sibling import
    from .ledgers import RELEVANCE_GATE as _RELEVANCE_GATE
    from .ledgers import TOXICITY_CEILING as _TOXICITY_CEILING
except Exception:  # pragma: no cover - defensive
    _RELEVANCE_GATE = 0.30
    _TOXICITY_CEILING = 0.85


# ===========================================================================
# §4.2 DISCOURSE — the firehose. Reuse the narrator's _discourse_rows pool (same
# join + relevance/toxicity gates) but DO NOT truncate the bodies for the packet
# (doc 59 §4.2 / §9: the API writer gets full discourse bodies). De-dup by
# independent origin so N reposts of one thread count once (representativeness).
# ===========================================================================
def _section_discourse(db, player_id: Optional[int], season: int) -> list[Fact]:
    if player_id is None:
        return []
    # Reuse the narrator's discourse SQL pool. _discourse_rows applies the same
    # relevance + toxicity gates and returns FULL body_text (it truncates only in
    # assemble_evidence, which we deliberately do NOT call — the packet keeps full
    # bodies per §4.2/§9). Fall back to a local query if the import fails.
    rows: list[dict[str, Any]] = []
    try:
        from .story_card_narrator import _discourse_rows  # noqa: WPS433

        rows = _discourse_rows(db, int(player_id), int(season))
    except Exception:
        rows = _fallback_discourse_rows(db, int(player_id), int(season))

    facts: list[Fact] = []
    seen_origin: set[str] = set()
    for r in rows:
        doc_id = r.get("doc_id")
        if doc_id is None:
            continue
        title = str(r.get("title_text") or "").strip()
        body = str(r.get("body_text") or "").strip()
        text = (title + " " + body).strip()
        if not text:
            continue
        # Independent-origin de-dup (author first, then source) — one troll/bot or
        # N reposts of one thread count once toward representativeness.
        origin = (
            str(r.get("author_id") or r.get("author_name") or "")
            or str(r.get("source_name") or "")
            or str(doc_id)
        )
        if origin and origin in seen_origin:
            continue
        if origin:
            seen_origin.add(origin)

        bucket = str(r.get("audience_bucket") or "").strip().lower()
        sentiment = str(r.get("sentiment_label") or "").strip().lower()
        # Valence = sentiment_label + audience_bucket (doc 59 §4.2).
        valence = "/".join(p for p in (sentiment, bucket) if p) or None
        rel = _to_float(r.get("relevance_ml_score"))
        # Confidence carries the relevance score (None -> a neutral 0.6 prior).
        conf = rel if rel is not None else 0.6
        # High-salience NIL/money/holdout docs are flagged never-truncate (§7).
        nil_flag = bool(_NIL_PATTERN.search(text))
        facts.append(
            Fact(
                key=f"discourse.doc_{doc_id}",
                value={
                    "doc_id": doc_id,
                    "title": title or None,
                    "body": body or None,
                    "audience_bucket": bucket or None,
                    "sentiment_label": sentiment or None,
                    "source_name": r.get("source_name"),
                    "source_author_name": r.get("author_name"),
                    "source_url": r.get("source_url"),
                    "like_count": _to_int(r.get("like_count")),
                    "relevance_ml_score": rel,
                    "high_salience_nil": nil_flag,
                },
                # FULL text in display — NOT truncated (doc 59 §4.2 / §9).
                display=text,
                source_id=f"doc:{doc_id}",
                source_kind="discourse",
                valence=valence,
                evidence_bar=(
                    "a take becomes the DOMINANT take only with >= N independent "
                    "origins; a single loud doc is a minority take"
                ),
                # NIL/money docs are never truncated/suppressed; ordinary docs are
                # context the writer selects from (no per-doc suppression).
                suppress_when=None,
                confidence=max(0.0, min(1.0, conf)),
            )
        )
    return facts


def _fallback_discourse_rows(db, player_id: int, season: int) -> list[dict[str, Any]]:
    """Local discourse pull if story_card_narrator can't import (defensive). Same
    gates as the narrator's _discourse_rows, full bodies, no truncation."""
    return _safe_all(
        db,
        """
        SELECT cdt.conversation_document_id   AS doc_id,
               cdt.audience_bucket            AS audience_bucket,
               cdt.sentiment_label            AS sentiment_label,
               cdt.toxicity_score            AS toxicity_score,
               cd.title_text                 AS title_text,
               cd.body_text                  AS body_text,
               cd.relevance_ml_score         AS relevance_ml_score,
               cd.source_name                AS source_name,
               cd.source_author_id           AS author_id,
               cd.source_author_name         AS author_name,
               cd.source_url                 AS source_url,
               cd.like_count                 AS like_count
          FROM conversation_document_targets cdt
          JOIN conversation_documents cd
            ON cd.conversation_document_id = cdt.conversation_document_id
         WHERE cdt.player_id = :pid
           AND cdt.season_year = :s
           AND COALESCE(cd.is_deleted, 0) = 0
           AND COALESCE(cd.is_removed, 0) = 0
           AND (cd.relevance_ml_score IS NULL OR cd.relevance_ml_score >= :relgate)
           AND (cdt.toxicity_score    IS NULL OR cdt.toxicity_score    <= :toxceil)
         ORDER BY cd.relevance_ml_score DESC, cd.like_count DESC
        """,
        {
            "pid": int(player_id),
            "s": int(season),
            "relgate": _RELEVANCE_GATE,
            "toxceil": _TOXICITY_CEILING,
        },
    )


# ===========================================================================
# §4.3 PRODUCTION & BEFORE/AFTER — current + prior season stat lines from
# player_season_stats (MAX(stat_value_num) per category/stat_type — NEVER SUM the
# cumulative rows) + the WEPA durable signal from player_value_metrics. Valence =
# improved | declined | steady from the headline-stat delta.
# ===========================================================================
# The headline stat per category that drives the before/after VALENCE direction.
_HEADLINE_STAT = {"passing": "YDS", "rushing": "YDS", "receiving": "YDS"}


def _season_stat_lines(db, player_id: int, season: int) -> dict[str, dict[str, Any]]:
    """{category: {stat_type: value}, plus '_team': team_name} for one season.

    MAX(stat_value_num) per (category, stat_type) — season totals live with week as
    a 16/21 marker and season_type='both'; MAX de-dups the cumulative rows without
    double-counting (doc 59 §4.3 / §13).
    """
    rows = _safe_all(
        db,
        """
        select category, stat_type, max(stat_value_num) as v, max(team_name) as tn
          from player_season_stats
         where player_id = :pid and season_year = :s and stat_value_num is not null
         group by category, stat_type
        """,
        {"pid": int(player_id), "s": int(season)},
    )
    out: dict[str, dict[str, Any]] = {}
    team: Optional[str] = None
    for r in rows:
        cat = str(r.get("category") or "").lower()
        st = str(r.get("stat_type") or "").upper()
        if not cat or not st:
            continue
        out.setdefault(cat, {})[st] = _to_float(r.get("v"))
        if team is None and r.get("tn"):
            team = str(r.get("tn"))
    if team is not None:
        out["_team"] = team  # type: ignore[assignment]
    return out


def _headline_line(cat: str, stats: dict[str, Any]) -> Optional[str]:
    """Compact "2,616 YDS / 19 TD / 5 INT" style line for a category."""
    if cat == "passing":
        order = ["YDS", "TD", "INT"]
        labels = {"YDS": "yds", "TD": "TD", "INT": "INT"}
    elif cat == "rushing":
        order = ["YDS", "TD", "CAR"]
        labels = {"YDS": "yds", "TD": "TD", "CAR": "car"}
    elif cat == "receiving":
        order = ["YDS", "TD", "REC"]
        labels = {"YDS": "yds", "TD": "TD", "REC": "rec"}
    else:
        order = list(stats.keys())[:3]
        labels = {k: k for k in order}
    parts = []
    for st in order:
        if stats.get(st) is not None:
            parts.append(f"{_fmt_num(stats[st])} {labels.get(st, st)}")
    return " / ".join(parts) if parts else None


def _section_before_after(db, player_id: Optional[int], season: int) -> list[Fact]:
    if player_id is None:
        return []
    facts: list[Fact] = []
    prior = int(season) - 1
    cur_lines = _season_stat_lines(db, int(player_id), int(season))
    prior_lines = _season_stat_lines(db, int(player_id), prior)
    cur_team = cur_lines.get("_team")
    prior_team = prior_lines.get("_team")

    # Per-category before/after facts (the transfer/role delta lives here).
    categories = sorted(
        (set(cur_lines) | set(prior_lines)) - {"_team"}
    )
    for cat in categories:
        cur = cur_lines.get(cat) or {}
        pri = prior_lines.get(cat) or {}
        if not cur and not pri:
            continue
        headline = _HEADLINE_STAT.get(cat)
        cv = _to_float(cur.get(headline)) if headline else None
        pv = _to_float(pri.get(headline)) if headline else None
        # Valence from the headline-stat delta.
        if cv is not None and pv is not None:
            if cv > pv * 1.05:
                valence = "improved"
            elif cv < pv * 0.95:
                valence = "declined"
            else:
                valence = "steady"
        else:
            valence = None
        cur_str = _headline_line(cat, cur)
        pri_str = _headline_line(cat, pri)
        # Build a before/after display only when we have a prior to compare.
        if pri_str and cur_str:
            display = (
                f"{cat}: {prior} {prior_team or ''} {pri_str} -> "
                f"{season} {cur_team or ''} {cur_str}".replace("  ", " ").strip()
            )
        elif cur_str:
            display = f"{cat}: {season} {cur_team or ''} {cur_str}".replace("  ", " ").strip()
        else:
            display = f"{cat}: {prior} {prior_team or ''} {pri_str}".replace("  ", " ").strip()
        facts.append(
            Fact(
                key=f"before_after.{cat}_{season}",
                value={
                    "category": cat,
                    "current": {"season": season, "team": cur_team, "stats": cur},
                    "prior": {"season": prior, "team": prior_team, "stats": pri} if pri else None,
                },
                display=display,
                source_id=f"row:player_season_stats:{player_id}:{cat}",
                source_kind="structured",
                valence=valence,
                evidence_bar=(
                    "a before/after is only a STORY with context (injury / scheme / "
                    "level-of-comp); a bare decline ships as a fact, the writer gates "
                    "the knock framing on the discourse"
                ),
                suppress_when=None,
                confidence=1.0,
            )
        )

    # WEPA durable signal (player_value_metrics) — production envelope.
    vm = _safe_all(
        db,
        """
        select metric_name, metric_value, plays from player_value_metrics
         where player_id = :pid and season_year = :s and metric_value is not null
        """,
        {"pid": int(player_id), "s": int(season)},
    )
    for m in vm:
        name = str(m.get("metric_name") or "").strip()
        if not name:
            continue
        val = _to_float(m.get("metric_value"))
        plays = _to_int(m.get("plays"))
        facts.append(
            Fact(
                key=f"before_after.{name}_{season}",
                value={"metric_name": name, "metric_value": val, "plays": plays},
                display=f"{name} {val:g} over {plays} plays ({season})" if val is not None and plays
                else f"{name} {val:g} ({season})" if val is not None else name,
                source_id=f"row:player_value_metrics:{player_id}:{name}",
                source_kind="structured",
                valence=None,
                evidence_bar="WEPA is a production envelope; assert with the stat line, not alone",
                suppress_when=None,
                confidence=1.0,
            )
        )
    return facts


# ===========================================================================
# §4.4 RECRUITING — stars / national rank / hometown / original commit.
# ===========================================================================
def _section_recruiting(db, player_id: Optional[int], season: int) -> list[Fact]:
    if player_id is None:
        return []
    row = _safe_one(
        db,
        """
        select stars, rating, national_rank, committed_team, city, state_province,
               position, season_year
          from player_recruiting_profiles
         where player_id = :pid
         order by season_year desc, stars desc
         limit 1
        """,
        {"pid": int(player_id)},
    )
    if not row:
        return []
    stars = _to_int(row.get("stars"))
    nat = _to_int(row.get("national_rank"))
    city = (row.get("city") or "").strip()
    state = (row.get("state_province") or "").strip()
    hometown = ", ".join(p for p in (city, state) if p)
    commit = (row.get("committed_team") or "").strip()
    bits = []
    if stars:
        bits.append(f"{stars}-star")
    if nat:
        bits.append(f"#{nat} national")
    if hometown:
        bits.append(f"from {hometown}")
    if commit:
        bits.append(f"committed to {commit}")
    display = "; ".join(bits) or "recruiting profile"
    return [
        Fact(
            key="recruiting.profile",
            value={
                "stars": stars,
                "rating": _to_float(row.get("rating")),
                "national_rank": nat,
                "hometown": hometown or None,
                "city": city or None,
                "state_province": state or None,
                "committed_team": commit or None,
            },
            display=display,
            source_id=f"row:player_recruiting_profiles:{player_id}",
            source_kind="structured",
            valence="neutral",
            evidence_bar="always available; the 'comes home' / 'left X for Y' angle is neutral",
            suppress_when=None,
            confidence=1.0,
        )
    ]


# ===========================================================================
# §4.5 HONORS — current + prior; valence positive SCALED BY SCOPE (consensus/
# unanimous All-American >> a third-team all-conference nod).
# ===========================================================================
def _section_honors(db, player_id: Optional[int], season: int) -> list[Fact]:
    if player_id is None:
        return []
    rows = _safe_all(
        db,
        """
        select honor_name, honor_scope, selector, honor_team, placement,
               consensus_flag, unanimous_flag, season_year, conference_name
          from player_honors
         where player_id = :pid
         order by season_year desc
        """,
        {"pid": int(player_id)},
    )
    facts: list[Fact] = []
    for r in rows:
        name = (r.get("honor_name") or "").strip()
        if not name:
            continue
        scope = (r.get("honor_scope") or "").strip()
        selector = (r.get("selector") or "").strip()
        # placement is sometimes an INT in the DB (e.g. 1) — coerce to str before
        # stripping so a numeric placement doesn't raise AttributeError and silently
        # drop the whole honors section via the build_packet guard.
        placement = str(r.get("placement")).strip() if r.get("placement") not in (None, "") else None
        consensus = bool(_to_int(r.get("consensus_flag")))
        unanimous = bool(_to_int(r.get("unanimous_flag")))
        yr = _to_int(r.get("season_year"))
        # Weight by scope: the packet carries the scope so the writer doesn't
        # overweight a thin honor. Valence encodes the weight band.
        if unanimous or consensus or "all-ameri" in scope.lower():
            valence = "positive_major"
        elif "all_conference" in scope.lower() or "all-conf" in scope.lower():
            valence = "positive_minor"
        else:
            valence = "positive"
        disp_bits = [name]
        if yr:
            disp_bits.append(str(yr))
        if placement:
            disp_bits.append(placement)
        if consensus:
            disp_bits.append("consensus")
        if unanimous:
            disp_bits.append("unanimous")
        facts.append(
            Fact(
                key=f"honors.{name.lower().replace(' ', '_')}_{yr or 'x'}",
                value={
                    "honor_name": name,
                    "honor_scope": scope or None,
                    "selector": selector or None,
                    "honor_team": r.get("honor_team"),
                    "placement": placement,
                    "consensus_flag": consensus,
                    "unanimous_flag": unanimous,
                    "season_year": yr,
                    "conference_name": r.get("conference_name"),
                },
                display=" · ".join(disp_bits),
                source_id=f"row:player_honors:{player_id}:{name}:{yr}",
                source_kind="structured",
                valence=valence,
                evidence_bar="an honor is assertable; its WEIGHT is governed by scope/selector",
                suppress_when=None,  # never silenced; weight scaled by scope (§6)
                confidence=1.0,
            )
        )
    return facts


# ===========================================================================
# §4.6 AWARD WATCH (upcoming season) — forward-looking credibility. slug->name map.
# ===========================================================================
def _section_award_watch(db, player_id: Optional[int], upcoming_season: int) -> list[Fact]:
    if player_id is None:
        return []
    rows = _safe_all(
        db,
        """
        select award_slug, list_type, position_rank, priority, as_of
          from player_award_watch_2026
         where player_id = :pid
         order by priority
        """,
        {"pid": int(player_id)},
    )
    facts: list[Fact] = []
    for r in rows:
        slug = r.get("award_slug")
        name = _award_display(slug)
        rank = _to_int(r.get("position_rank"))
        list_type = (r.get("list_type") or "").strip()
        display = f"{name} watch" + (f" #{rank}" if rank else "")
        facts.append(
            Fact(
                key=f"award_watch.{str(slug or '').lower()}",
                value={
                    "award_slug": slug,
                    "award_name": name,
                    "list_type": list_type or None,
                    "position_rank": rank,
                    "as_of": r.get("as_of"),
                },
                display=display,
                source_id=f"row:player_award_watch_2026:{player_id}:{slug}",
                source_kind="structured",
                # Forward-looking credibility — complicates an "all hype" take.
                valence="positive_forward",
                evidence_bar="always assertable when present; it IS a forward signal, season-clock safe",
                suppress_when=None,
                confidence=1.0,
            )
        )
    return facts


# ===========================================================================
# §4.7 DEPTH CHART / STARTER STATUS (upcoming) — confidence text gates assertion.
# ===========================================================================
def _section_depth_chart(db, player_id: Optional[int], upcoming_season: int) -> list[Fact]:
    if player_id is None:
        return []
    rows = _safe_all(
        db,
        """
        select position_group, slot_rank, starter_status, confidence
          from player_depth_chart_2026
         where player_id = :pid
         order by slot_rank
        """,
        {"pid": int(player_id)},
    )
    facts: list[Fact] = []
    for r in rows:
        status = (r.get("starter_status") or "").strip()
        conf_txt = (r.get("confidence") or "").strip().lower()
        pos_group = (r.get("position_group") or "").strip()
        slot = _to_int(r.get("slot_rank"))
        # 'confirmed' > 'projected' gates assertion (doc 59 §4.7 / §5 entrenchment).
        if conf_txt == "confirmed":
            valence = "starter_confirmed"
            conf = 0.9
        elif conf_txt == "projected":
            valence = "starter_projected"
            conf = 0.6
        else:
            valence = status or None
            conf = 0.5
        display = " ".join(p for p in (pos_group, status.replace("_", " ")) if p) or "depth chart"
        if conf_txt:
            display += f" ({conf_txt})"
        facts.append(
            Fact(
                key=f"depth_chart.{pos_group.lower()}_{slot or 0}",
                value={
                    "position_group": pos_group or None,
                    "slot_rank": slot,
                    "starter_status": status or None,
                    "confidence": conf_txt or None,
                },
                display=display,
                source_id=f"row:player_depth_chart_2026:{player_id}",
                source_kind="structured",
                valence=valence,
                evidence_bar="'confirmed' > 'projected' gates the strength of the starter assertion",
                # A 'projected' (not confirmed) starter status should not be asserted
                # as a settled fact — flag it so the writer hedges.
                suppress_when=(
                    None if conf_txt == "confirmed"
                    else "confidence != 'confirmed' (assert as projected, not settled)"
                ),
                confidence=conf,
            )
        )
    return facts


# ===========================================================================
# §4.8 TRANSFER / PORTAL HISTORY — the portal arc + the drafted fate.
# ===========================================================================
def _section_transfer(db, player_id: Optional[int], season: int) -> list[Fact]:
    if player_id is None:
        return []
    facts: list[Fact] = []
    rows = _safe_all(
        db,
        """
        select from_team_name, to_team_name, transfer_date, season_year,
               from_team_id, to_team_id
          from transfer_entries
         where player_id = :pid
         order by season_year desc, transfer_date desc
        """,
        {"pid": int(player_id)},
    )
    for r in rows:
        frm = (r.get("from_team_name") or "").strip()
        to = (r.get("to_team_name") or "").strip()
        yr = _to_int(r.get("season_year"))
        date = (r.get("transfer_date") or "")
        date_short = str(date)[:10] if date else None
        display = f"transfer {frm or '?'} -> {to or '?'}" + (f" ({yr})" if yr else "")
        facts.append(
            Fact(
                key=f"transfer.{frm.lower().replace(' ', '_')}_{to.lower().replace(' ', '_')}_{yr or 'x'}",
                value={
                    "from_team_name": frm or None,
                    "to_team_name": to or None,
                    "transfer_date": date_short,
                    "season_year": yr,
                },
                display=display,
                source_id=f"row:transfer_entries:{player_id}:{yr}",
                source_kind="structured",
                valence="portal_move",
                evidence_bar="the portal move is factual; the WHY (NIL) comes from discourse, never our valuation (§7)",
                suppress_when=None,
                confidence=1.0,
            )
        )
    # The drafted fate (player_nfl_draft) — the departure / where-he-ended-up signal.
    draft = _safe_one(
        db,
        "select draft_year, round, overall, nfl_team from player_nfl_draft "
        "where player_id = :pid order by draft_year desc limit 1",
        {"pid": int(player_id)},
    )
    if draft:
        yr = _to_int(draft.get("draft_year"))
        rnd = _to_int(draft.get("round"))
        overall = _to_int(draft.get("overall"))
        team = (draft.get("nfl_team") or "").strip()
        bits = ["NFL draft"]
        if yr:
            bits.append(str(yr))
        if rnd:
            bits.append(f"r{rnd}")
        if overall:
            bits.append(f"#{overall}")
        if team:
            bits.append(team)
        facts.append(
            Fact(
                key=f"transfer.nfl_draft_{yr or 'x'}",
                value={"draft_year": yr, "round": rnd, "overall": overall, "nfl_team": team or None},
                display=" ".join(bits),
                source_id=f"row:player_nfl_draft:{player_id}",
                source_kind="structured",
                valence="drafted",
                evidence_bar="the drafted fate is the departure signal; a departed player gets no forward preview",
                suppress_when=None,
                confidence=1.0,
            )
        )
    return facts


# ===========================================================================
# §4.9 AURA / BAN — the hype-vs-tape signal. Valence = the verdict (aura_tax /
# matched). The BAN is asserted only when the gap is real AND the buzz exists
# (mention_count above floor) — a big gap with tiny buzz is NOT a story (§6).
# ===========================================================================
_BAN_MENTION_FLOOR = 5     # below this, the BAN gap is "big gap, tiny buzz" — suppress
_BAN_GAP_FLOOR = 15.0      # perception - production pctl gap that reads as a real BAN


def _section_aura(db, player_id: Optional[int], season: int) -> list[Fact]:
    if player_id is None:
        return []
    row = _safe_one(
        db,
        """
        select mention_count, perception_pctl, production_pctl, aura_score,
               aura_tax, verdict, is_low_signal, week
          from player_aura_weekly
         where player_id = :pid and season_year = :s
         order by week desc limit 1
        """,
        {"pid": int(player_id), "s": int(season)},
    )
    if not row:
        return []
    mentions = _to_int(row.get("mention_count")) or 0
    perception = _to_float(row.get("perception_pctl"))
    production = _to_float(row.get("production_pctl"))
    verdict = (row.get("verdict") or "").strip()
    gap = None
    if perception is not None and production is not None:
        gap = round(perception - production, 1)
    # The BAN gap is suppressed when the gap is real but the buzz is below floor
    # (doc 59 §4.9 / §6: "big gap, tiny buzz" is not a story).
    big_gap = gap is not None and abs(gap) >= _BAN_GAP_FLOOR
    buzz_ok = mentions >= _BAN_MENTION_FLOOR
    suppress = bool(big_gap and not buzz_ok)
    bits = []
    if verdict:
        bits.append(verdict)
    if gap is not None:
        bits.append(f"perception-production gap {gap:+.0f} pctl")
    bits.append(f"{mentions} mentions")
    display = "; ".join(bits)
    return [
        Fact(
            key="aura.ban",
            value={
                "mention_count": mentions,
                "perception_pctl": perception,
                "production_pctl": production,
                "aura_score": _to_float(row.get("aura_score")),
                "aura_tax": _to_float(row.get("aura_tax")),
                "verdict": verdict or None,
                "is_low_signal": bool(_to_int(row.get("is_low_signal"))),
                "perception_production_gap": gap,
            },
            display=display,
            # Valence = the verdict (aura_tax / matched) IS the valence (doc 59 §4.9).
            valence=verdict or None,
            source_id=f"row:player_aura_weekly:{player_id}:{season}",
            source_kind="structured",
            evidence_bar=(
                "the BAN is asserted only when the gap is real AND the buzz exists "
                f"(mention_count >= {_BAN_MENTION_FLOOR})"
            ),
            suppress_when=(
                f"abs(perception-production gap) >= {_BAN_GAP_FLOOR:.0f} AND "
                f"mention_count < {_BAN_MENTION_FLOOR}"
            ),
            confidence=0.85 if not suppress else 0.3,
            suppressed=suppress,
        )
    ]


# ===========================================================================
# §4.10 SUCCESSION — via succession.fetch_succession_for_player. Carries
# suggested_frame / predecessor_band / threat_label / entrenchment / suppress_clock.
# The heir/clock fact is SUPPRESSED when succession.suppress_clock is True (§6).
# ===========================================================================
def _section_succession(db, player_external_id: str, season: int) -> list[Fact]:
    try:
        from . import succession  # local import keeps the module import-time deps lean

        sr = succession.fetch_succession_for_player(db, str(player_external_id), int(season))
    except Exception:
        return []
    if sr is None:
        return []

    facts: list[Fact] = []
    role = getattr(sr, "role", "") or ""
    pred = getattr(sr, "predecessor_name", None)
    pred_band = getattr(sr, "predecessor_band", None)
    pred_stars = getattr(sr, "predecessor_stars", None)
    heir = getattr(sr, "heir_name", None)
    heir_stars = getattr(sr, "heir_stars", None)
    frame = getattr(sr, "suggested_frame", None)
    threat = getattr(sr, "threat_label", None)
    entrenchment = getattr(sr, "incumbent_entrenchment", None)
    suppress_clock = bool(getattr(sr, "suppress_clock", False))
    competition = bool(getattr(sr, "discourse_competition", False))
    clock_line = getattr(sr, "clock_line", None)
    tone = getattr(sr, "tone", None)
    shoes = getattr(sr, "shoes_read", None)
    conf = _to_float(getattr(sr, "confidence", None)) or 0.0

    # The succession FRAME fact — always carried (it tells the writer how to read the
    # handoff: live-up-to-a-legend / escape-a-bust / entrenched-no-clock / ...).
    frame_bits = []
    if frame:
        frame_bits.append(f"frame: {frame}")
    if pred:
        pb = f" ({pred_band})" if pred_band else ""
        frame_bits.append(f"succeeds {pred}{pb}")
    if entrenchment:
        frame_bits.append(f"entrenchment {entrenchment}")
    facts.append(
        Fact(
            key="succession.frame",
            value={
                "role": role,
                "predecessor_name": pred,
                "predecessor_band": pred_band,
                "predecessor_stars": pred_stars,
                "suggested_frame": frame,
                "threat_label": threat,
                "incumbent_entrenchment": entrenchment,
                "discourse_competition": competition,
                "shoes_read": shoes,
                "tone": tone,
            },
            display="; ".join(frame_bits) or f"{role} succession",
            source_id=f"row:player_succession:{player_external_id}:{season}",
            source_kind="structured",
            # Valence carries the predecessor band + frame (the direction of the read).
            valence=pred_band or frame,
            evidence_bar=(
                "the predecessor read is production-banded (elite=reverence / "
                "poor=relief); the writer reaches for the suggested_frame"
            ),
            suppress_when=None,
            confidence=conf,
        )
    )

    # The HEIR / CLOCK fact — SUPPRESSED when succession.suppress_clock is True (the
    # entrenched-star-with-quiet-backup case: Beck, Chambliss). Carried for context
    # but flagged suppressed so the writer drops the whole clock block (doc 59 §6).
    if heir or clock_line:
        facts.append(
            Fact(
                key="succession.heir_clock",
                value={
                    "heir_name": heir,
                    "heir_stars": heir_stars,
                    "threat_label": threat,
                    "clock_line": clock_line,
                    "discourse_competition": competition,
                },
                display=(clock_line or (f"heir-apparent {heir}" if heir else "the clock")),
                source_id=f"row:player_succession:{player_external_id}:{season}:heir",
                source_kind="structured",
                valence=threat,
                evidence_bar="assert a clock only if threat >= floor OR discourse competition exists",
                suppress_when="succession.suppress_clock is True (entrenched starter + quiet backup)",
                confidence=conf if not suppress_clock else 0.0,
                suppressed=suppress_clock,
            )
        )
    return facts


# ===========================================================================
# §4.11 / §7 NIL NARRATIVE — discourse-only. NEVER queries player_nil_valuations.
# Derives the NIL STORY from discourse docs matching the NIL keyword set + the
# structured portal event. Reported $ figures are quotable WITH attribution.
# ===========================================================================
def _section_nil_narrative(
    discourse_facts: list[Fact], transfer_facts: list[Fact]
) -> list[Fact]:
    """Build the NIL-narrative section from the ALREADY-GATHERED discourse pool +
    the portal event. Takes the discourse facts (not the DB) so it never issues a
    second query and is guaranteed to never touch player_nil_valuations."""
    facts: list[Fact] = []
    # NIL-flagged discourse docs (high salience, never truncate — §7).
    for d in discourse_facts:
        val = d.value if isinstance(d.value, dict) else {}
        if not val.get("high_salience_nil"):
            continue
        text = d.display or ""
        dollar = None
        m = _DOLLAR_PATTERN.search(text)
        if m:
            dollar = m.group(0).strip()
        facts.append(
            Fact(
                key=f"nil_narrative.{d.key}",
                value={
                    "doc_id": val.get("doc_id"),
                    "reported_figure": dollar,
                    "source_name": val.get("source_name"),
                    "source_url": val.get("source_url"),
                },
                display=text,
                source_id=d.source_id,  # the doc: anchor — quotable WITH attribution
                source_kind="discourse",
                valence=d.valence,
                evidence_bar=(
                    "the NIL figure is quotable only when REPORTED by a source doc "
                    "(attributed); modeled valuations are never emitted (§7)"
                ),
                suppress_when="the figure is our MODELED valuation (never reached — we never query it)",
                confidence=d.confidence,
            )
        )
    # The portal event grounds the "portal for money" arc (the structured half).
    for t in transfer_facts:
        if t.valence == "portal_move":
            facts.append(
                Fact(
                    key=f"nil_narrative.portal_{t.key}",
                    value=t.value,
                    display=f"portal event grounding the NIL arc: {t.display}",
                    source_id=t.source_id,
                    source_kind="structured",
                    valence="portal_move",
                    evidence_bar="the portal move is the structured anchor for the NIL discourse",
                    suppress_when=None,
                    confidence=t.confidence,
                )
            )
    return facts


# ===========================================================================
# §4.12 FIRED LEDGER LEADS / TAKES — via ledgers.fetch_ledger_lead. The
# dominant-take candidate + its pinned evidence docs.
# ===========================================================================
def _section_ledger_take(db, player_external_id: str, season: int) -> list[Fact]:
    try:
        from . import ledgers  # local import

        lead = ledgers.fetch_ledger_lead(db, str(player_external_id), int(season), None)
    except Exception:
        return []
    if not lead:
        return []
    ledger = (lead.get("ledger") or "").strip()
    score = _to_float(lead.get("score"))
    direction = (lead.get("direction") or "").strip()
    conf = _to_float(lead.get("confidence")) or 0.0
    doc_count = _to_int(lead.get("doc_count")) or 0
    source_count = _to_int(lead.get("source_count")) or 0
    fired = bool(_to_int(lead.get("fired")))
    pinned: list[Any] = []
    try:
        raw = lead.get("evidence_doc_ids_json")
        if raw:
            ids = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(ids, list):
                pinned = ids
    except Exception:
        pinned = []
    # Representativeness gate (doc 59 §4.2/§4.12): a take only leads with >= N
    # independent origins; a thin/single-source take is demoted (suppressed).
    representative = doc_count >= 5 and source_count >= 2
    return [
        Fact(
            key=f"ledger_take.{ledger or 'lead'}",
            value={
                "ledger": ledger or None,
                "score": score,
                "direction": direction or None,
                "doc_count": doc_count,
                "source_count": source_count,
                "fired": fired,
                "evidence_doc_ids": pinned,
            },
            display=(
                f"dominant fan ledger: {ledger or '?'} ({direction or 'n/a'}), "
                f"{doc_count} docs / {source_count} sources"
            ),
            source_id=f"row:player_ledger_scores:{player_external_id}:{ledger}",
            source_kind="discourse",
            valence=direction or ledger or None,
            evidence_bar="the dominant take must clear representativeness (>= N independent origins)",
            suppress_when="doc_count < 5 OR source_count < 2 (single loud doc -> minority take)",
            confidence=conf,
            suppressed=not representative,
        )
    ]


# ===========================================================================
# §4.1 IDENTITY + SEASON CLOCK. players + roster_entries for identity; the season
# clock is the forward-frame (upcoming = the season previewed; last_completed = the
# stats season). season_labels is the spec source but is empty in the live DB, so
# we derive the clock from the date helpers (the same _upcoming_season /
# _last_completed_season the narrator uses) — the canonical clock in this codebase.
# ===========================================================================
def _identity(db, player_id: Optional[int], player_external_id: str, last_completed: int) -> dict:
    ident: dict[str, Any] = {
        "player_external_id": str(player_external_id),
        "player_id": player_id,
        "name": None,
        "position": None,
        "team": None,
        "class_year": None,
        "jersey": None,
        "hometown": None,
    }
    if player_id is None:
        return ident
    p = _safe_one(
        db,
        "select full_name, position, hometown, home_state from players where player_id = :pid",
        {"pid": int(player_id)},
    )
    if p:
        ident["name"] = p.get("full_name")
        ident["position"] = p.get("position")
        ht = ", ".join(
            x for x in ((p.get("hometown") or "").strip(), (p.get("home_state") or "").strip()) if x
        )
        ident["hometown"] = ht or None
    # Latest roster entry for team / class / jersey (prefer the last completed season).
    r = _safe_one(
        db,
        """
        select team_id, class_year, jersey, position from roster_entries
         where player_id = :pid
         order by case when season_year = :s then 0 else 1 end, season_year desc
         limit 1
        """,
        {"pid": int(player_id), "s": int(last_completed)},
    )
    if r:
        ident["class_year"] = r.get("class_year")
        ident["jersey"] = r.get("jersey")
        if not ident["position"] and r.get("position"):
            ident["position"] = r.get("position")
        tid = _to_int(r.get("team_id"))
        if tid is not None:
            t = _safe_one(
                db, "select canonical_name from teams where team_id = :tid", {"tid": tid}
            )
            if t and t.get("canonical_name"):
                ident["team"] = t.get("canonical_name")
    return ident


def _season_clock(season: int, upcoming_season: int) -> dict:
    """The hard framing instruction (doc 59 §4.1 / §8 season clock). ``upcoming`` =
    the season being previewed; ``last_completed`` = the stats season (= ``season``,
    the data season passed in). Date-derived helpers reconcile the calendar."""
    today = _dt.date.today()
    try:
        upcoming = int(upcoming_season) if upcoming_season else _upcoming_season(today)
    except Exception:
        upcoming = _upcoming_season(today)
    return {"upcoming": upcoming, "last_completed": int(season)}


# ===========================================================================
# EVIDENCE FINGERPRINT (doc 59 §11). Stable sha1 of sorted(selected discourse
# doc_ids) + sorted(structured fact keys). Deterministic across runs/processes.
# ===========================================================================
def _evidence_fingerprint(sections: dict[str, list[Fact]]) -> str:
    doc_ids: list[str] = []
    struct_keys: list[str] = []
    for facts in sections.values():
        for f in facts:
            if f.source_kind == "discourse" and str(f.source_id).startswith("doc:"):
                doc_ids.append(str(f.source_id))
            elif f.source_kind == "structured":
                struct_keys.append(str(f.key))
    payload = {
        "discourse_doc_ids": sorted(set(doc_ids)),
        "structured_fact_keys": sorted(set(struct_keys)),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


# ===========================================================================
# THE PUBLIC ENTRY — build_packet. NEVER raises (every section guarded); a failed
# section degrades to []. Returns a fully-populated Packet with the fingerprint.
# ===========================================================================
def build_packet(
    db,
    player_external_id: str,
    season: int,
    *,
    upcoming_season: int = 2026,
) -> Packet:
    """Assemble the complete evidence packet for one (player_external_id, season).

    Gathers every doc 59 §4 source via the exact tables/columns in §13, wraps each
    atomic fact in the Fact envelope (§3) with valence + evidence_bar + suppress_when
    (§6 catalog), and emits the deterministic evidence fingerprint (§11). NIL is
    discourse-derived only — player_nil_valuations is NEVER queried (§7).

    NEVER raises into the render path (doc 59 §12): each section has its own
    try/except that degrades to an empty list on any failure.
    """
    season = int(season)
    ext = str(player_external_id) if player_external_id else ""

    # Resolve the numeric player_id once (guarded).
    try:
        player_id = _resolve_player_id(db, ext)
    except Exception:
        player_id = None

    # Identity + season clock (§4.1).
    try:
        identity = _identity(db, player_id, ext, season)
    except Exception:
        identity = {"player_external_id": ext, "player_id": player_id}
    try:
        season_clock = _season_clock(season, upcoming_season)
    except Exception:
        season_clock = {"upcoming": upcoming_season, "last_completed": season}
    up = _to_int(season_clock.get("upcoming")) or int(upcoming_season)

    # Eligibility (§4.1.1) — classify_2026_status on the numeric player_id.
    eligibility_d: dict[str, Any] = {"status": "uncertain", "reason": "not evaluated", "on_upcoming_roster": None}
    try:
        from . import eligibility as _elig

        if player_id is not None:
            eligibility_d = _elig.classify_2026_status(
                db, player_id, upcoming_season=up, last_completed=season
            )
    except Exception:
        pass

    # Each section in its own guard — a failure degrades to [] (doc 59 §12).
    def _guard(fn, *args) -> list[Fact]:
        try:
            return fn(*args) or []
        except Exception:
            return []

    discourse = _guard(_section_discourse, db, player_id, season)
    before_after = _guard(_section_before_after, db, player_id, season)
    recruiting = _guard(_section_recruiting, db, player_id, season)
    honors = _guard(_section_honors, db, player_id, season)
    award_watch = _guard(_section_award_watch, db, player_id, up)
    depth_chart = _guard(_section_depth_chart, db, player_id, up)
    transfer = _guard(_section_transfer, db, player_id, season)
    aura = _guard(_section_aura, db, player_id, season)
    succession = _guard(_section_succession, db, ext, season)
    # NIL is derived from the already-gathered discourse + transfer facts (no second
    # query, guaranteeing player_nil_valuations is never touched — §7).
    nil_narrative = _guard(_section_nil_narrative, discourse, transfer)
    ledger_take = _guard(_section_ledger_take, db, ext, season)

    sections: dict[str, list[Fact]] = {
        "discourse": discourse,
        "before_after": before_after,
        "recruiting": recruiting,
        "honors": honors,
        "award_watch": award_watch,
        "depth_chart": depth_chart,
        "transfer": transfer,
        "aura": aura,
        "succession": succession,
        "nil_narrative": nil_narrative,
        "ledger_take": ledger_take,
    }

    try:
        fingerprint = _evidence_fingerprint(sections)
    except Exception:
        fingerprint = ""

    return Packet(
        player_external_id=ext,
        season=season,
        identity=identity,
        season_clock=season_clock,
        eligibility=eligibility_d,
        sections=sections,
        evidence_fingerprint=fingerprint,
    )


__all__ = [
    "Fact",
    "Packet",
    "SECTION_KEYS",
    "build_packet",
]
