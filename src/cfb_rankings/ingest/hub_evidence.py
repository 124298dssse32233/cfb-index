"""Evidence reports for computed Hub v5 rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cfb_rankings.conversation_utils import normalize_lookup_text
from cfb_rankings.db import Database


def write_hub_computed_evidence_report(
    db: Database,
    output_path: str | Path,
    *,
    week_start_from: str = "2026-01-19",
    week_start_to: str = "2026-04-22",
    max_posts: int = 0,
) -> dict[str, int | str]:
    """Write a no-hidden-truncation JSON evidence report for computed Hub rows.

    ``max_posts=0`` means include every contributing source thread. If callers
    pass a positive limit the JSON marks that entry as truncated explicitly.
    """

    mood = _mood_evidence(db, week_start_from=week_start_from, week_start_to=week_start_to, max_posts=max_posts)
    rivalry = _rivalry_evidence(db, week_start_from=week_start_from, week_start_to=week_start_to)
    lexicon = _lexicon_evidence(db, week_start_from=week_start_from, week_start_to=week_start_to)
    payload = {
        "report_version": "hub-computed-evidence-v1",
        "week_start_from": week_start_from,
        "week_start_to": week_start_to,
        "max_posts": max_posts,
        "no_hidden_truncation": max_posts == 0,
        "mood": mood,
        "rivalry": rivalry,
        "lexicon": lexicon,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "output": str(output),
        "mood_rows": len(mood),
        "rivalry_rows": len(rivalry),
        "lexicon_rows": len(lexicon),
    }


def _mood_evidence(
    db: Database,
    *,
    week_start_from: str,
    week_start_to: str,
    max_posts: int,
) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select
          fmw.*,
          t.slug,
          t.canonical_name,
          owm.season_year,
          owm.offseason_week
        from fanbase_mood_weekly fmw
        join teams t on t.team_id = fmw.team_id
        left join offseason_week_map owm on owm.week_start_date = fmw.week_start_date
        where fmw.source = 'computed'
          and fmw.week_start_date between %(week_start_from)s and %(week_start_to)s
        order by fmw.week_start_date, t.canonical_name
        """,
        {"week_start_from": week_start_from, "week_start_to": week_start_to},
    )
    evidence: list[dict[str, Any]] = []
    for row in rows:
        season = int(row.get("season_year") or 2025)
        week = int(row.get("offseason_week") or 0)
        team_id = int(row["team_id"])
        source_threads = _source_threads_for_team(db, season=season, week=week, team_id=team_id)
        total_threads = len(source_threads)
        if max_posts > 0:
            source_threads = source_threads[:max_posts]
        evidence.append(
            {
                "stat_type": "mood",
                "week_start_date": row["week_start_date"],
                "season_year": season,
                "week": week,
                "team_id": team_id,
                "team_slug": row["slug"],
                "team_name": row["canonical_name"],
                "published_row": {
                    "mood_score": row.get("mood_score"),
                    "delta_from_prev_week": row.get("delta_from_prev_week"),
                    "sample_size": row.get("sample_size"),
                    "sample_authors": row.get("sample_authors"),
                    "confidence": row.get("confidence"),
                    "source": row.get("source"),
                },
                "feature_rows": _feature_rows_for_team(db, season=season, week=week, team_id=team_id),
                "content_type_mix": _group_counts(
                    db,
                    season=season,
                    week=week,
                    team_id=team_id,
                    expression="cd.content_type",
                    label="content_type",
                ),
                "source_subreddits": _group_counts(
                    db,
                    season=season,
                    week=week,
                    team_id=team_id,
                    expression="coalesce(cd.source_subchannel, '')",
                    label="source_subchannel",
                ),
                "mention_roles": _group_counts(
                    db,
                    season=season,
                    week=week,
                    team_id=team_id,
                    expression="cdt.mention_role",
                    label="mention_role",
                ),
                "comment_attribution": _comment_attribution_counts(db, season=season, week=week, team_id=team_id),
                "source_threads": source_threads,
                "source_threads_total": total_threads,
                "source_threads_included": len(source_threads),
                "truncated": max_posts > 0 and total_threads > len(source_threads),
            }
        )
    return evidence


def _rivalry_evidence(db: Database, *, week_start_from: str, week_start_to: str) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select
          row.*,
          ta.slug as team_a_slug,
          tb.slug as team_b_slug,
          ta.canonical_name as team_a_name,
          tb.canonical_name as team_b_name,
          owm.season_year,
          owm.offseason_week
        from rivalry_obsession_weekly row
        join teams ta on ta.team_id = row.team_a_id
        join teams tb on tb.team_id = row.team_b_id
        left join offseason_week_map owm on owm.week_start_date = row.week_start_date
        where row.source = 'computed'
          and row.week_start_date between %(week_start_from)s and %(week_start_to)s
        order by row.week_start_date, row.rivalry_slug
        """,
        {"week_start_from": week_start_from, "week_start_to": week_start_to},
    )
    evidence: list[dict[str, Any]] = []
    for row in rows:
        season = int(row.get("season_year") or 2025)
        week = int(row.get("offseason_week") or 0)
        evidence.append(
            {
                "stat_type": "rivalry",
                "week_start_date": row["week_start_date"],
                "season_year": season,
                "week": week,
                "rivalry_slug": row["rivalry_slug"],
                "team_a": {"team_id": row["team_a_id"], "slug": row["team_a_slug"], "name": row["team_a_name"]},
                "team_b": {"team_id": row["team_b_id"], "slug": row["team_b_slug"], "name": row["team_b_name"]},
                "published_row": {
                    "a_mentions_b_count": row.get("a_mentions_b_count"),
                    "b_mentions_a_count": row.get("b_mentions_a_count"),
                    "ratio_dominant": row.get("ratio_dominant"),
                    "leaning_team": row.get("leaning_team"),
                    "sample_authors": row.get("sample_authors"),
                    "confidence": row.get("confidence"),
                    "source": row.get("source"),
                },
                "pair_aggregate_rows": _rival_mention_rows(
                    db,
                    season=season,
                    week=week,
                    team_a_id=int(row["team_a_id"]),
                    team_b_id=int(row["team_b_id"]),
                ),
                "limitation": "Pair evidence is aggregate-level because team_week_rival_mentions does not store per-document pair links.",
            }
        )
    return evidence


def _lexicon_evidence(db: Database, *, week_start_from: str, week_start_to: str) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select row.*, owm.season_year, owm.offseason_week
        from lexicon_weekly row
        left join offseason_week_map owm on owm.week_start_date = row.week_start_date
        where row.source = 'computed'
          and row.week_start_date between %(week_start_from)s and %(week_start_to)s
        order by row.week_start_date, row.phrase
        """,
        {"week_start_from": week_start_from, "week_start_to": week_start_to},
    )
    evidence: list[dict[str, Any]] = []
    for row in rows:
        season = int(row.get("season_year") or 2025)
        week = int(row.get("offseason_week") or 0)
        evidence.append(
            {
                "stat_type": "lexicon",
                "week_start_date": row["week_start_date"],
                "season_year": season,
                "week": week,
                "phrase": row["phrase"],
                "published_row": {
                    "mention_count": row.get("mention_count"),
                    "growth_pct": row.get("growth_pct"),
                    "sample_authors": row.get("sample_authors"),
                    "confidence": row.get("confidence"),
                    "source": row.get("source"),
                },
                "phrase_rows": _phrase_rows(db, season=season, week=week, phrase=str(row["phrase"])),
            }
        )
    return evidence


def _feature_rows_for_team(db: Database, *, season: int, week: int, team_id: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select
          source_name,
          audience_bucket,
          mention_count,
          unique_author_count,
          mean_sentiment_score,
          net_sentiment_score,
          sample_quality_score,
          top_storyline_json
        from team_week_conversation_features
        where season_year = %(season)s
          and week = %(week)s
          and team_id = %(team_id)s
        order by source_name, audience_bucket
        """,
        {"season": season, "week": week, "team_id": team_id},
    )


def _group_counts(
    db: Database,
    *,
    season: int,
    week: int,
    team_id: int,
    expression: str,
    label: str,
) -> list[dict[str, Any]]:
    return db.query_all(
        f"""
        select {expression} as {label},
               count(*) as target_count,
               count(distinct cd.conversation_document_id) as document_count,
               count(distinct coalesce(cd.source_author_id, cd.source_author_name, cd.source_document_id)) as author_count
        from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id = cdt.conversation_document_id
        where cdt.season_year = %(season)s
          and cdt.week = %(week)s
          and cdt.team_id = %(team_id)s
          and cdt.target_type = 'team'
          and cd.source_name = 'reddit'
        group by {expression}
        order by target_count desc, {label}
        """,
        {"season": season, "week": week, "team_id": team_id},
    )


def _comment_attribution_counts(db: Database, *, season: int, week: int, team_id: int) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select cdt.notes, count(*) as target_count, count(distinct cd.conversation_document_id) as document_count
        from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id = cdt.conversation_document_id
        where cdt.season_year = %(season)s
          and cdt.week = %(week)s
          and cdt.team_id = %(team_id)s
          and cdt.mention_role = 'comment-thread'
          and cd.source_name = 'reddit'
        group by cdt.notes
        """,
        {"season": season, "week": week, "team_id": team_id},
    )
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        attribution = _notes_value(str(row.get("notes") or ""), "attribution") or "unknown"
        entry = counts.setdefault(attribution, {"target_count": 0, "document_count": 0})
        entry["target_count"] += int(row.get("target_count") or 0)
        entry["document_count"] += int(row.get("document_count") or 0)
    return [
        {"attribution": key, **value}
        for key, value in sorted(counts.items(), key=lambda item: (-item[1]["target_count"], item[0]))
    ]


def _source_threads_for_team(db: Database, *, season: int, week: int, team_id: int) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select
          coalesce(parent.source_document_id, cd.source_document_id) as source_document_id,
          coalesce(parent.source_url, cd.source_url) as source_url,
          coalesce(parent.source_subchannel, cd.source_subchannel) as source_subchannel,
          coalesce(parent.title_text, cd.title_text) as title_text,
          count(*) as target_count,
          count(distinct cd.conversation_document_id) as document_count,
          count(distinct case when cd.content_type = 'comment' then cd.conversation_document_id end) as comment_count,
          count(distinct case when cd.content_type = 'post' then cd.conversation_document_id end) as post_count,
          count(distinct coalesce(cd.source_author_id, cd.source_author_name, cd.source_document_id)) as author_count
        from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id = cdt.conversation_document_id
        left join conversation_documents parent
          on cd.content_type = 'comment'
         and parent.source_name = cd.source_name
         and parent.source_document_id = cd.source_parent_document_id
        where cdt.season_year = %(season)s
          and cdt.week = %(week)s
          and cdt.team_id = %(team_id)s
          and cdt.target_type = 'team'
          and cd.source_name = 'reddit'
        group by
          coalesce(parent.source_document_id, cd.source_document_id),
          coalesce(parent.source_url, cd.source_url),
          coalesce(parent.source_subchannel, cd.source_subchannel),
          coalesce(parent.title_text, cd.title_text)
        order by target_count desc, document_count desc, source_document_id
        """,
        {"season": season, "week": week, "team_id": team_id},
    )
    return rows


def _rival_mention_rows(db: Database, *, season: int, week: int, team_a_id: int, team_b_id: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select *
        from team_week_rival_mentions
        where season_year = %(season)s
          and week = %(week)s
          and (
            (team_id = %(team_a_id)s and rival_team_id = %(team_b_id)s)
            or
            (team_id = %(team_b_id)s and rival_team_id = %(team_a_id)s)
          )
        order by team_id, rival_team_id, source_name, audience_bucket
        """,
        {"season": season, "week": week, "team_a_id": team_a_id, "team_b_id": team_b_id},
    )


def _phrase_rows(db: Database, *, season: int, week: int, phrase: str) -> list[dict[str, Any]]:
    normalized_phrase = normalize_lookup_text(phrase)
    return db.query_all(
        """
        select *
        from phrase_mentions_weekly
        where season_year = %(season)s
          and week = %(week)s
          and phrase = %(phrase)s
        order by source_name, audience_bucket
        """,
        {"season": season, "week": week, "phrase": phrase if normalized_phrase else phrase},
    )


def _notes_value(notes: str, key: str) -> str | None:
    prefix = f"{key}="
    for part in notes.split(";"):
        if part.startswith(prefix):
            return part[len(prefix) :]
    return None
