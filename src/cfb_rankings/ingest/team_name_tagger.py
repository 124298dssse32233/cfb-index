"""Team name-extraction tagger for source-agnostic conversation documents.

Reddit documents are team-tagged at *collection* time (each search is keyed to
a team alias), so their ``conversation_document_targets`` rows are written by
the collector. Curated feeds — ``bluesky_curated`` and the ``substack_*``
sources — arrive as a single CFB stream with no per-team context, so they land
with **zero** targets and contribute nothing to the mood / cohort features
downstream. The player tagger can't rescue them either: it only scans documents
that already carry a team target.

This module closes that gap. It scans untagged documents for team-alias
mentions and emits ``target_type='team'`` rows, after which the existing
``tag_player_mentions`` → ``compute_player_week_mood`` → cohort pipeline can pick
them up with no further change.

Precision-first design (recall is deliberately the secondary concern, mirroring
``player_name_tagger``):

- **Collision drop.** An alias that normalizes to more than one team (e.g.
  "Miami" → Miami FL + Miami OH) is dropped — we skip rather than guess. The
  reddit collector doesn't face this because it already knows the team.
- **Word-boundary match.** Plain substring would match "rice" inside "price".
  Matching is anchored on non-alphanumeric boundaries.
- **Common-word stoplist + length floor.** Single-token aliases that are common
  English words carry a high false-positive rate even in a CFB feed; they are
  dropped. Multi-word aliases ("ohio state", "notre dame") are always kept —
  their FP rate is negligible.
- **Dry-run by default.** Like the player tagger, rows are only written with
  ``--commit``. ``--preview`` prints match snippets so an operator can judge
  precision before turning it on.

CLI:
    python manage.py tag-team-mentions --season=YYYY [--week=N] [--limit=N]
        [--sources bluesky_curated,substack_gameday] [--commit] [--preview]
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from cfb_rankings.conversation_utils import score_sentiment
from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

# Sources that arrive without per-team context and therefore need post-ingest
# tagging. Reddit is intentionally excluded — it is tagged at collection time.
DEFAULT_UNTAGGED_SOURCES: tuple[str, ...] = (
    "bluesky_curated",
    "substack_gameday",
    "substack_recruits",
    "substack_long",
    "substack_tradition",
)

# Single-token aliases that are common English words / generic nouns with a high
# non-team usage rate. Multi-word aliases are never stoplisted. Tunable — widen
# this after eyeballing --preview output if false positives surface.
COMMON_WORD_STOPLIST: frozenset[str] = frozenset(
    {"rice", "army", "navy", "state", "tech", "southern", "memphis", "buffalo"}
)

# Normalized single-token aliases shorter than this are dropped (kills stray
# initialisms that collide with ordinary words). Distinctive 3-letter program
# acronyms (lsu, tcu, byu, usc, ucla) are whitelisted past this floor below.
MIN_SINGLE_TOKEN_LEN = 4
ACRONYM_WHITELIST: frozenset[str] = frozenset(
    {"lsu", "tcu", "byu", "usc", "ucla", "smu", "utep", "uab", "ucf", "fiu", "fau"}
)

# NFL team full names share a city with several college programs ("Houston"
# Texans / Cougars, "Pittsburgh" Steelers / Panthers, "Cincinnati" Bengals /
# Bearcats). A bare city alias whose only occurrences sit *inside* an NFL team
# name is an NFL mention, not a college one. These phrases are fed into the same
# span-containment suppression that handles college substring collisions
# ("Florida" inside "Florida State"), so a city tagged here is dropped unless it
# also stands alone elsewhere in the document.
NFL_TEAM_PHRASES: frozenset[str] = frozenset(
    {
        "arizona cardinals", "atlanta falcons", "baltimore ravens",
        "buffalo bills", "carolina panthers", "chicago bears",
        "cincinnati bengals", "cleveland browns", "dallas cowboys",
        "denver broncos", "detroit lions", "green bay packers",
        "houston texans", "indianapolis colts", "jacksonville jaguars",
        "kansas city chiefs", "las vegas raiders", "los angeles chargers",
        "los angeles rams", "miami dolphins", "minnesota vikings",
        "new england patriots", "new orleans saints", "new york giants",
        "new york jets", "philadelphia eagles", "pittsburgh steelers",
        "san francisco 49ers", "seattle seahawks", "tampa bay buccaneers",
        "tampa bay bucs", "tennessee titans", "washington commanders",
    }
)


def _normalize(text: str) -> str:
    """Lowercase, strip non-alphanumerics to spaces, collapse whitespace.

    Matches the normalization ``Repository._raw_name_key`` applied when the
    ``team_aliases.alias_normalized`` column was written, so an alias key
    compares apples-to-apples against the normalized document body.
    """
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (text or "").lower())).strip()


@dataclass(frozen=True)
class TeamAlias:
    team_id: int
    alias_text: str
    alias_normalized: str


_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _word_boundary_pattern(normalized_alias: str) -> re.Pattern[str]:
    cached = _PATTERN_CACHE.get(normalized_alias)
    if cached is not None:
        return cached
    pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(normalized_alias)}(?![A-Za-z0-9])"
    )
    _PATTERN_CACHE[normalized_alias] = pattern
    return pattern


def _alias_is_precise(normalized: str) -> bool:
    """Precision gate for a single normalized alias key."""
    if not normalized:
        return False
    if " " in normalized:
        # Multi-word aliases are high-precision — always keep.
        return True
    if normalized in ACRONYM_WHITELIST:
        return True
    if normalized in COMMON_WORD_STOPLIST:
        return False
    return len(normalized) >= MIN_SINGLE_TOKEN_LEN


def build_team_alias_index(
    db: Database,
    season_year: int,
) -> tuple[dict[str, int], dict[int, str]]:
    """Return ``({alias_normalized: team_id}, {team_id: label})``.

    Only precision-safe aliases survive: collision-free (one team per key),
    past the precision gate. Falls back to the most recent season that has
    aliases when the requested season has none (offseason — aliases are seeded
    per completed season).
    """
    rows = db.query_all(
        """
        select team_id, alias_text, alias_normalized
        from team_aliases
        where season_year = %(season)s and is_active = 1
        """,
        {"season": season_year},
    )
    if not rows:
        fallback = db.query_one(
            "select max(season_year) as y from team_aliases where is_active = 1"
        )
        fb_year = fallback["y"] if fallback else None
        if fb_year is not None and fb_year != season_year:
            rows = db.query_all(
                """
                select team_id, alias_text, alias_normalized
                from team_aliases
                where season_year = %(season)s and is_active = 1
                """,
                {"season": fb_year},
            )

    by_alias: dict[str, set[int]] = defaultdict(set)
    label: dict[int, str] = {}
    text_for_alias: dict[str, str] = {}
    for r in rows:
        norm = (r.get("alias_normalized") or "").strip()
        if not norm or not _alias_is_precise(norm):
            continue
        team_id = int(r["team_id"])
        by_alias[norm].add(team_id)
        text_for_alias.setdefault(norm, str(r.get("alias_text") or norm))
        # Prefer the longest alias_text as the human label (canonical-ish).
        cand = str(r.get("alias_text") or "")
        if len(cand) > len(label.get(team_id, "")):
            label[team_id] = cand

    index: dict[str, int] = {}
    for norm, team_ids in by_alias.items():
        if len(team_ids) != 1:
            continue  # collision — skip rather than guess
        index[norm] = next(iter(team_ids))
    return index, label


@dataclass
class TeamTagMatch:
    conversation_document_id: int
    team_id: int
    team_label: str


def tag_team_mentions(
    db: Database,
    *,
    season_year: int,
    week: int = 0,
    sources: Iterable[str] = DEFAULT_UNTAGGED_SOURCES,
    doc_limit: int | None = None,
    commit: bool = False,
    preview: bool = False,
) -> dict[str, int]:
    """Scan untagged documents for team-alias mentions.

    Returns counts: ``{'docs_scanned', 'matches', 'rows_written'}``.
    Only documents that currently carry **no** team target are scanned, so a
    re-run never double-tags and reddit's collection-time targets are left
    untouched.
    """
    index, label = build_team_alias_index(db, season_year)
    if not index:
        return {"docs_scanned": 0, "matches": 0, "rows_written": 0}

    source_list = [s.strip() for s in sources if s.strip()]
    if not source_list:
        return {"docs_scanned": 0, "matches": 0, "rows_written": 0}
    placeholders = ",".join(f":src_{i}" for i in range(len(source_list)))
    params: dict[str, Any] = {s_key: s for s_key, s in
                              ((f"src_{i}", s) for i, s in enumerate(source_list))}
    limit_clause = ""
    if doc_limit is not None:
        params["limit"] = int(doc_limit)
        limit_clause = "limit :limit"

    docs = db.query_all(
        f"""
        select cd.conversation_document_id as doc_id,
               cd.body_text                as body_text,
               cd.title_text               as title_text
        from conversation_documents cd
        where cd.source_name in ({placeholders})
          and cd.body_text is not null
          and length(cd.body_text) > 0
          and not exists (
              select 1 from conversation_document_targets t
              where t.conversation_document_id = cd.conversation_document_id
                and t.target_type = 'team'
          )
        {limit_clause}
        """,
        params,
    )

    docs_scanned = 0
    matches: list[TeamTagMatch] = []
    for doc_row in docs:
        docs_scanned += 1
        doc_id = int(doc_row["doc_id"])
        body = (doc_row.get("body_text") or "") + " " + (doc_row.get("title_text") or "")
        body_norm = _normalize(body)
        if not body_norm:
            continue
        # Collect match spans per alias so we can suppress a short alias that
        # only ever appears *inside* a longer one ("Florida" inside "Florida
        # State", "Virginia" inside "West Virginia"). A short alias survives if
        # at least one of its spans stands alone somewhere in the text.
        matched_spans: dict[str, list[tuple[int, int]]] = {}
        for alias_norm in index:
            spans = [
                (m.start(), m.end())
                for m in _word_boundary_pattern(alias_norm).finditer(body_norm)
            ]
            if spans:
                matched_spans[alias_norm] = spans

        # Spans of any NFL team name present in the doc. These never tag a team
        # themselves; they only act as covering spans that suppress a bare city
        # alias sitting inside them ("houston" inside "houston texans").
        nfl_spans: list[tuple[int, int]] = []
        for phrase in NFL_TEAM_PHRASES:
            nfl_spans.extend(
                (m.start(), m.end())
                for m in _word_boundary_pattern(phrase).finditer(body_norm)
            )

        items = list(matched_spans.items())
        hit_team_ids: set[int] = set()
        for alias_norm, spans_a in items:
            stands_alone = False
            for (s, e) in spans_a:
                covered = any(
                    s2 <= s and e2 >= e and (e2 - s2) > (e - s)
                    for other, spans_b in items if other != alias_norm
                    for (s2, e2) in spans_b
                ) or any(
                    s2 <= s and e2 >= e and (e2 - s2) > (e - s)
                    for (s2, e2) in nfl_spans
                )
                if not covered:
                    stands_alone = True
                    break
            if stands_alone:
                hit_team_ids.add(index[alias_norm])
        for team_id in hit_team_ids:
            matches.append(
                TeamTagMatch(
                    conversation_document_id=doc_id,
                    team_id=team_id,
                    team_label=label.get(team_id, str(team_id)),
                )
            )
            if preview:
                print(f"  doc={doc_id:<10} team={team_id:<6} {label.get(team_id, '')[:30]}")

    rows_written = 0
    if commit and matches:
        # Score sentiment once per document (not per match) — all team targets
        # in a doc share the document-level sentiment, matching how the player
        # tagger inherits a single document-level score.
        sentiment_cache: dict[int, dict[str, Any]] = {}
        body_by_doc: dict[int, str] = {}
        for doc_row in docs:
            body_by_doc[int(doc_row["doc_id"])] = (
                (doc_row.get("body_text") or "") + " " + (doc_row.get("title_text") or "")
            )
        for m in matches:
            existing = db.query_one(
                """
                select 1 as x from conversation_document_targets
                 where conversation_document_id = :doc
                   and target_type = 'team'
                   and team_id = :tid
                """,
                {"doc": m.conversation_document_id, "tid": m.team_id},
            )
            if existing:
                continue
            sent = sentiment_cache.get(m.conversation_document_id)
            if sent is None:
                sent = score_sentiment(body_by_doc.get(m.conversation_document_id, ""))
                sentiment_cache[m.conversation_document_id] = sent
            db.execute(
                """
                insert into conversation_document_targets (
                    conversation_document_id, season_year, week, team_id,
                    target_type, target_key, target_label, affiliation_team_id,
                    audience_bucket, mention_role, sentiment_label, sentiment_score,
                    emotion_primary, emotion_secondary, sarcasm_score,
                    toxicity_score, confidence_score, is_primary_target
                ) values (
                    :doc, :season, :week, :tid,
                    'team', :target_key, :target_label, :tid,
                    'national', 'curated-feed', :sentiment_label, :sentiment_score,
                    :emotion_primary, :emotion_secondary, :sarcasm_score,
                    :toxicity_score, :confidence_score, 0
                )
                """,
                {
                    "doc": m.conversation_document_id,
                    "season": season_year,
                    "week": week,
                    "tid": m.team_id,
                    "target_key": f"team:{m.team_id}",
                    "target_label": m.team_label,
                    "sentiment_label": sent.get("sentiment_label"),
                    "sentiment_score": sent.get("sentiment_score"),
                    "emotion_primary": sent.get("emotion_primary"),
                    "emotion_secondary": sent.get("emotion_secondary"),
                    "sarcasm_score": sent.get("sarcasm_score"),
                    "toxicity_score": sent.get("toxicity_score"),
                    "confidence_score": sent.get("confidence_score"),
                },
            )
            rows_written += 1

    return {
        "docs_scanned": docs_scanned,
        "matches": len(matches),
        "rows_written": rows_written,
    }


__all__ = [
    "tag_team_mentions",
    "build_team_alias_index",
    "TeamAlias",
    "TeamTagMatch",
    "DEFAULT_UNTAGGED_SOURCES",
]
