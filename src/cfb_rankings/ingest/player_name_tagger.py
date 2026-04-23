"""Player name-extraction tagger.

Scans `conversation_documents.body_text` for mentions of active QB/RB/WR
players in a given season and emits new `conversation_document_targets`
rows with `target_type='player'` and `player_id` populated. This is the
last piece Feature B needs to start producing non-empty mood profiles:

    conversation_documents (raw)
      └─ [player_name_tagger]
          └─ conversation_document_targets (target_type='player', player_id=…)
              └─ [compute_player_week_mood]
                  └─ player_week_conversation_features
                      └─ [fetch_player_mood_profile]
                          └─ The Room on [Player] renders live.

Design rules enforced in code:

- **Roster-bounded candidate pool.** We only match players with real
  season stats (``player_value_metrics`` preferred, ``player_season_stats``
  as fallback) for the target season. Scanning against all 46k historical
  players would explode false-positive rate.
- **Full-name match only (first + last).** No first-name-only and no
  last-name-only matching — the false-positive rate is prohibitive
  (thousands of "Smith", "Williams" mentions that belong to other people).
  Kickoff calls this out as the hard part of disambiguation; v1 punts
  by requiring the full name.
- **Team-affiliation tiebreak.** When two players share a full name and
  both are active, prefer the one whose team is also named in the same
  document. If neither wins the tiebreak, skip.
- **One player-target row per (document, player) pair.** Idempotent via
  a pre-query check.
- **Dry-run by default.** The CLI only inserts rows with ``--commit``.
  This is a safety gate because the real cfb_rankings.db mixes live
  data and runs one-way; every tagger run is effectively an ingestion
  step and needs explicit sign-off.

CLI:
    python manage.py tag-player-mentions --season=YYYY [--week=N] [--limit=N] [--commit]
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlayerIndexEntry:
    player_id: int
    full_name: str
    position: str
    team_id: int | None
    team_name: str | None
    conference_name: str | None


# Precompile: find spans that might be player names (sequences of
# capitalized tokens, 2-4 words long). Used only for logging; matching
# itself is substring-based so it catches informal capitalizations too.
_NAME_SPAN_RE = re.compile(r"(?:[A-Z][A-Za-z'\.\-]+\s+){1,3}[A-Z][A-Za-z'\.\-]+")


def _normalize(text: str) -> str:
    """Case-fold + collapse whitespace + drop periods for matching."""
    out = re.sub(r"\s+", " ", (text or "").lower())
    return out.replace(".", "").strip()


def build_last_name_index(
    full_name_index: dict[str, list[PlayerIndexEntry]],
) -> dict[str, list[PlayerIndexEntry]]:
    """Derive a {normalized_last_name: [entries]} index from the full-name index.

    Only entries whose last token is ≥ 3 characters are included — this
    filters initials and suffixes like "II" / "Jr" that would match
    everything. The caller is expected to disambiguate via team-name
    cooccurrence; a last name that doesn't cooccur with its team in the
    document must NOT be tagged.
    """
    out: dict[str, list[PlayerIndexEntry]] = defaultdict(list)
    for entries in full_name_index.values():
        for entry in entries:
            last = entry.full_name.split()[-1]
            # Strip common suffixes.
            if last.lower() in {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}:
                parts = entry.full_name.split()
                if len(parts) < 2:
                    continue
                last = parts[-2]
            key = _normalize(last)
            if len(key) < 3:
                continue
            out[key].append(entry)
    return dict(out)


def build_player_name_index(
    db: Database,
    season_year: int,
    positions: Iterable[str] = ("QB", "RB", "WR"),
) -> dict[str, list[PlayerIndexEntry]]:
    """Return {normalized_full_name: [entries]} for in-season skill players.

    The candidate pool is intentionally narrow: only players with
    `player_value_metrics` OR non-zero `player_season_stats` for the
    given season and position. Scanning against all 46k players
    produces too many false positives.
    """
    position_list = [p.upper() for p in positions]
    placeholders = ",".join(f":pos_{i}" for i in range(len(position_list)))
    params: dict[str, Any] = {"season": season_year}
    for i, p in enumerate(position_list):
        params[f"pos_{i}"] = p

    rows = db.query_all(
        f"""
        with active as (
            select distinct player_id
              from player_value_metrics
             where season_year = :season
            union
            select distinct player_id
              from player_season_stats
             where season_year = :season
               and stat_value_num is not null
               and stat_value_num != 0
        ),
        affiliation as (
            select pvm.player_id,
                   pvm.team_id,
                   pvm.team_name,
                   pvm.conference_name,
                   row_number() over (
                     partition by pvm.player_id
                     order by pvm.plays desc
                   ) as rn
              from player_value_metrics pvm
             where pvm.season_year = :season
        ),
        fallback_aff as (
            select pss.player_id,
                   pss.team_id,
                   pss.team_name,
                   pss.conference_name,
                   row_number() over (
                     partition by pss.player_id
                     order by pss.stat_value_num desc
                   ) as rn
              from player_season_stats pss
             where pss.season_year = :season
        )
        select p.player_id,
               p.full_name,
               p.position,
               coalesce(a.team_id, f.team_id) as team_id,
               coalesce(a.team_name, f.team_name) as team_name,
               coalesce(a.conference_name, f.conference_name) as conference_name
          from active
          join players p on p.player_id = active.player_id
          left join affiliation a
            on a.player_id = p.player_id and a.rn = 1
          left join fallback_aff f
            on f.player_id = p.player_id and f.rn = 1
         where p.position in ({placeholders})
        """,
        params,
    )

    index: dict[str, list[PlayerIndexEntry]] = defaultdict(list)
    for r in rows:
        full = (r.get("full_name") or "").strip()
        if not full or len(full.split()) < 2:
            continue
        key = _normalize(full)
        index[key].append(
            PlayerIndexEntry(
                player_id=int(r["player_id"]),
                full_name=full,
                position=str(r.get("position") or ""),
                team_id=int(r["team_id"]) if r.get("team_id") is not None else None,
                team_name=str(r.get("team_name") or "") or None,
                conference_name=str(r.get("conference_name") or "") or None,
            )
        )
    return index


def _disambiguate(
    entries: list[PlayerIndexEntry],
    doc_body_norm: str,
) -> PlayerIndexEntry | None:
    """Pick one entry given ambiguous full-name matches.

    Team-affiliation tiebreak: if the document body also mentions the
    player's team_name (normalized), prefer that entry. If multiple
    entries win the tiebreak, or none do, return None (skip rather than
    guess).
    """
    if len(entries) == 1:
        return entries[0]
    matches = [
        e for e in entries
        if e.team_name and _normalize(e.team_name) in doc_body_norm
    ]
    if len(matches) == 1:
        return matches[0]
    return None


@dataclass
class TagMatch:
    conversation_document_id: int
    player: PlayerIndexEntry
    affiliation_team_id: int | None
    inherited_audience_bucket: str | None
    inherited_week: int | None
    inherited_sentiment: float | None = None
    inherited_emotion: str | None = None
    inherited_sarcasm: float | None = None
    inherited_confidence: float | None = None


def _audience_bucket_for(
    player_entry: PlayerIndexEntry,
    team_targets_for_doc: list[dict[str, Any]],
) -> str | None:
    """Infer audience bucket for the new player-target row.

    Rule of thumb:
    - If the document has an existing team-scope target that matches the
      player's own team, inherit that team target's audience_bucket
      (typically 'fan' when the audience matches the player's team).
    - If the doc's team target is a DIFFERENT team, emit 'rival' or
      'national' based on the team target's bucket.
    - If the doc has no team target, return None — the downstream
      aggregator treats missing bucket as 'fan'.

    This is intentionally coarse. A smarter version uses doc source
    (e.g., reddit_team_sub vs. reddit_cfb) to refine. Out of scope for v1.
    """
    if not team_targets_for_doc:
        return None
    # Team-match wins.
    for tt in team_targets_for_doc:
        if player_entry.team_id is not None and tt.get("team_id") == player_entry.team_id:
            return tt.get("audience_bucket") or "fan"
    # Otherwise the first team target's bucket gives audience context.
    primary = team_targets_for_doc[0]
    tb = primary.get("audience_bucket") or ""
    if tb == "fan":
        return "rival"
    if tb == "rival":
        return "national"
    return tb or "national"


_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _word_boundary_pattern(normalized_name: str) -> re.Pattern[str]:
    """Compile (once) a word-boundary regex for the normalized name.

    Match boundaries treat any non-alphanumeric+apostrophe character as a
    break. This catches "C.J. Carr" → normalized "cj carr" → matches in
    bodies containing "CJ Carr", "C.J. Carr", "... about cj carr." but
    NOT in "cjcarrington" or "carrson".
    """
    cached = _PATTERN_CACHE.get(normalized_name)
    if cached is not None:
        return cached
    escaped = re.escape(normalized_name)
    pattern = re.compile(rf"(?<![A-Za-z0-9']){escaped}(?![A-Za-z0-9'])", re.IGNORECASE)
    _PATTERN_CACHE[normalized_name] = pattern
    return pattern


def _match_context(body: str, needle_norm: str) -> str:
    """Return ~80 chars of raw body around the first match of the normalized needle.

    Used by --preview to let an operator eyeball match quality. Falls back to
    the first 80 chars of body if precise location can't be pinpointed
    (e.g., when the normalization dropped periods between doc and index).
    """
    if not body:
        return ""
    lower = body.lower()
    # Try the needle verbatim first, then a cheap variant with periods.
    for probe in (needle_norm, needle_norm.replace(" ", ".")):
        idx = lower.find(probe)
        if idx >= 0:
            start = max(0, idx - 30)
            end = min(len(body), idx + len(probe) + 50)
            return body[start:end].replace("\n", " ").strip()
    return body[:80].replace("\n", " ").strip()


def tag_player_mentions(
    db: Database,
    *,
    season_year: int,
    week: int | None = None,
    doc_limit: int | None = None,
    commit: bool = False,
    preview: bool = False,
    include_last_name_matches: bool = True,
) -> dict[str, int]:
    """Scan conversation_documents for player-name mentions and either
    report (dry-run) or insert conversation_document_targets rows.

    Returns counts: {'docs_scanned': N, 'matches': M,
                     'skipped_ambiguous': S, 'rows_written': W}.
    """
    index = build_player_name_index(db, season_year)
    if not index:
        return {"docs_scanned": 0, "matches": 0, "skipped_ambiguous": 0, "rows_written": 0}
    last_name_index = build_last_name_index(index) if include_last_name_matches else {}

    # Load candidate docs. We filter to the season via existing team-scope
    # target rows to keep scan volume bounded — a doc without any team
    # target is almost never worth tagging for player scope.
    params: dict[str, Any] = {"season": season_year}
    week_filter = ""
    if week is not None:
        params["week"] = week
        week_filter = "and t.week = :week"
    limit_clause = ""
    if doc_limit is not None:
        params["limit"] = int(doc_limit)
        limit_clause = "limit :limit"

    docs = db.query_all(
        f"""
        select distinct
          cd.conversation_document_id as doc_id,
          cd.body_text                as body_text,
          cd.title_text               as title_text,
          t.season_year               as season_year,
          t.week                      as week
        from conversation_documents cd
        join conversation_document_targets t
          on t.conversation_document_id = cd.conversation_document_id
        where t.season_year = :season
          {week_filter}
          and cd.body_text is not null
          and length(cd.body_text) > 0
        {limit_clause}
        """,
        params,
    )

    docs_scanned = 0
    matches: list[TagMatch] = []
    skipped_ambiguous = 0

    for doc_row in docs:
        docs_scanned += 1
        doc_id = int(doc_row["doc_id"])
        body = (doc_row.get("body_text") or "") + " " + (doc_row.get("title_text") or "")
        body_norm = _normalize(body)
        if not body_norm:
            continue

        # Pull this doc's existing team-scope targets once for bucket +
        # week + sentiment inheritance. The player-target row MUST carry
        # document-level sentiment/emotion/sarcasm/confidence so the
        # aggregator can do its math — those scores are produced by the
        # upstream classifier on the full document, not re-derived by the
        # tagger. Week must match too, or the aggregator (which filters
        # by :week) never finds it.
        team_targets = db.query_all(
            """
            select team_id, audience_bucket, affiliation_team_id, week,
                   sentiment_score, emotion_primary, sarcasm_score, confidence_score
              from conversation_document_targets
             where conversation_document_id = :doc
               and target_type = 'team'
            """,
            {"doc": doc_id},
        )
        inherited_week = team_targets[0]["week"] if team_targets else week
        primary_tt = team_targets[0] if team_targets else None

        # Scan the index. For perf, we iterate the (small) index of
        # in-season skill players, not the (large) doc tokens. Each key
        # is a normalized full name; `in` substring test is fast.
        doc_matches: list[PlayerIndexEntry] = []
        for key, entries in index.items():
            # Word-boundary check — plain substring produces false positives
            # like "Peyton Higgins" matching "Peyton Higginson". The regex
            # is compiled once per key by `_word_boundary_pattern`.
            pattern = _word_boundary_pattern(key)
            if pattern.search(body_norm) is None:
                continue
            resolved = _disambiguate(entries, body_norm)
            if resolved is None:
                skipped_ambiguous += 1
                continue
            doc_matches.append(resolved)

        # Last-name pass — requires team cooccurrence AND single-candidate
        # resolution. Skip if the full-name pass already surfaced a player;
        # last names are the backfill for casual references.
        if last_name_index:
            full_name_hits: set[int] = {p.player_id for p in doc_matches}
            for last_key, entries in last_name_index.items():
                # Shared-last-name candidates may cover many players; team
                # cooccurrence is the only disambiguator we have.
                if _word_boundary_pattern(last_key).search(body_norm) is None:
                    continue
                # Filter to candidates whose team_name appears in the doc.
                team_matches = [
                    e for e in entries
                    if e.team_name and _normalize(e.team_name) in body_norm
                    and e.player_id not in full_name_hits
                ]
                # One unique player per (last_name, team) — if we got
                # multiple (e.g., Mendoza brothers at Indiana), we cannot
                # disambiguate from text alone; skip.
                if len(team_matches) == 1:
                    doc_matches.append(team_matches[0])
                elif len(team_matches) > 1:
                    skipped_ambiguous += 1

        # Deduplicate within a single doc (same player mentioned twice → one row).
        seen: set[int] = set()
        for p in doc_matches:
            if p.player_id in seen:
                continue
            seen.add(p.player_id)
            matches.append(
                TagMatch(
                    conversation_document_id=doc_id,
                    player=p,
                    affiliation_team_id=p.team_id,
                    inherited_audience_bucket=_audience_bucket_for(p, team_targets),
                    inherited_week=inherited_week,
                    inherited_sentiment=(primary_tt or {}).get("sentiment_score") if primary_tt else None,
                    inherited_emotion=(primary_tt or {}).get("emotion_primary") if primary_tt else None,
                    inherited_sarcasm=(primary_tt or {}).get("sarcasm_score") if primary_tt else None,
                    inherited_confidence=(primary_tt or {}).get("confidence_score") if primary_tt else None,
                )
            )
            if preview:
                # Look up the first matching normalized key for this player
                # to produce an informative context snippet.
                needle = next(
                    (k for k, entries in index.items()
                     if any(e.player_id == p.player_id for e in entries)
                     and k in body_norm),
                    p.full_name.lower(),
                )
                ctx = _match_context(
                    (doc_row.get("body_text") or "")
                    + " "
                    + (doc_row.get("title_text") or ""),
                    needle,
                )
                print(
                    f"  doc={doc_id:<8} pid={p.player_id:<6} "
                    f"{p.full_name[:22]:<22} "
                    f"team={(p.team_name or '?')[:18]:<18} "
                    f"bucket={ (m_bucket := _audience_bucket_for(p, team_targets)) or 'fan':<8} "
                    f"…{ctx[:120]}…"
                )

    rows_written = 0
    if commit and matches:
        for m in matches:
            # Idempotent insert: skip if a player target already exists.
            existing = db.query_one(
                """
                select 1 as x from conversation_document_targets
                 where conversation_document_id = :doc
                   and target_type = 'player'
                   and player_id = :pid
                """,
                {"doc": m.conversation_document_id, "pid": m.player.player_id},
            )
            if existing:
                continue
            db.execute(
                """
                insert into conversation_document_targets (
                    conversation_document_id, season_year, week, player_id,
                    target_type, target_key, target_label, affiliation_team_id,
                    audience_bucket, sentiment_score, emotion_primary,
                    sarcasm_score, confidence_score, is_primary_target
                ) values (
                    :doc, :season, :week, :pid,
                    'player', :target_key, :target_label, :aff_team,
                    :bucket, :sentiment, :emotion,
                    :sarcasm, :confidence, 0
                )
                """,
                {
                    "doc": m.conversation_document_id,
                    "season": season_year,
                    "week": m.inherited_week if m.inherited_week is not None else week,
                    "pid": m.player.player_id,
                    "target_key": f"player:{m.player.player_id}",
                    "target_label": m.player.full_name,
                    "aff_team": m.affiliation_team_id,
                    "bucket": m.inherited_audience_bucket or "fan",
                    "sentiment": m.inherited_sentiment,
                    "emotion": m.inherited_emotion,
                    "sarcasm": m.inherited_sarcasm,
                    "confidence": m.inherited_confidence,
                },
            )
            rows_written += 1

    return {
        "docs_scanned": docs_scanned,
        "matches": len(matches),
        "skipped_ambiguous": skipped_ambiguous,
        "rows_written": rows_written,
    }


__all__ = [
    "tag_player_mentions",
    "build_player_name_index",
    "PlayerIndexEntry",
    "TagMatch",
]
