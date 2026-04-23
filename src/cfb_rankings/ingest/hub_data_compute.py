"""Computed Hub v5 replacement paths for retro offseason rows."""

from __future__ import annotations

import json
from statistics import median
from typing import Any
from uuid import uuid4

from cfb_rankings.db import Database
from cfb_rankings.fan_intelligence import MIN_AUTHORS_FOR_SIGNAL, MIN_MENTIONS_FOR_SIGNAL
from cfb_rankings.ingest.hub_data_retro import RETRO_ISSUES, seed_retro_lexicon_week, seed_retro_mood_week, seed_retro_rivalry_week


def _issue_for_week_start(week_start: str) -> str | None:
    for issue_key, issue in RETRO_ISSUES.items():
        if issue["week_start_date"] == week_start:
            return issue_key
    return None


def _week_for_week_start(db: Database, week_start: str) -> tuple[int, int] | None:
    row = db.query_one(
        """
        select season_year, offseason_week
        from offseason_week_map
        where week_start_date = %(week_start)s
        limit 1
        """,
        {"week_start": week_start},
    )
    if row:
        return int(row["season_year"]), int(row["offseason_week"])
    issue_key = _issue_for_week_start(week_start)
    if issue_key is None:
        return None
    return 2025, int(RETRO_ISSUES[issue_key]["model_week"])


def _previous_week_start(db: Database, week_start: str) -> str | None:
    row = db.query_one(
        """
        select prev.week_start_date
        from offseason_week_map cur
        join offseason_week_map prev
          on prev.season_year = cur.season_year
         and prev.offseason_week = cur.offseason_week - 1
        where cur.week_start_date = %(week_start)s
        limit 1
        """,
        {"week_start": week_start},
    )
    if row and row.get("week_start_date"):
        return str(row["week_start_date"])
    sorted_issues = sorted(RETRO_ISSUES.values(), key=lambda issue: issue["week_start_date"])
    starts = [issue["week_start_date"] for issue in sorted_issues]
    if week_start not in starts:
        return None
    idx = starts.index(week_start)
    return starts[idx - 1] if idx > 0 else None


def _team_id_by_slug(db: Database, slug: str) -> int | None:
    row = db.query_one("select team_id from teams where slug = %(slug)s limit 1", {"slug": slug})
    return int(row["team_id"]) if row and row.get("team_id") is not None else None


def _source_priority(row: dict[str, Any]) -> tuple[int, int]:
    audience = str(row.get("audience_bucket") or "")
    source = str(row.get("source_name") or "")
    audience_rank = {"fan": 0, "national": 1, "all": 2}.get(audience, 3)
    source_rank = {"reddit": 0, "all": 1}.get(source, 2)
    return audience_rank, source_rank


def _confidence(mentions: int, authors: int) -> float:
    return round(min(1.0, mentions / 50.0, authors / 12.0), 3)


def _write_computed_rows(
    db: Database,
    table: str,
    rows: list[dict[str, Any]],
    *,
    key_columns: list[str],
    update_columns: list[str],
    run_id: str,
) -> None:
    insert_rows: list[dict[str, Any]] = []
    for row in rows:
        row_key = {column: row[column] for column in key_columns}
        where_sql, params = _where_clause(row_key)
        existing = db.query_one(f"select source from {table} where {where_sql} limit 1", params)
        if existing and str(existing.get("source") or "") != "computed":
            computed_value = {column: row[column] for column in update_columns if column in row}
            confidence = float(computed_value.pop("confidence", row.get("confidence") or 1.0))
            promote_row_to_computed(
                db,
                table,
                row_key,
                computed_value,
                confidence,
                run_id=run_id,
                reason="retro computed replacement",
            )
        else:
            insert_rows.append(row)
    db.upsert_many(
        table,
        insert_rows,
        conflict_columns=key_columns,
        update_columns=update_columns,
    )


def _seed_fallback_for_week(db: Database, week_start: str, kind: str) -> None:
    issue_key = _issue_for_week_start(week_start)
    if not issue_key:
        return
    if kind == "mood":
        seed_retro_mood_week(db, issue_key)
    elif kind == "rivalry":
        seed_retro_rivalry_week(db, issue_key)
    elif kind == "lexicon":
        seed_retro_lexicon_week(db, issue_key)


def compute_mood_week_from_features(db: Database, week_start: str) -> int:
    """Compute publishable Mood Index rows from team_week_conversation_features.

    Rows that fail sample gates are intentionally left on the seeded editorial
    fallback so Phase A pages never null-publish a stat.
    """

    week_key = _week_for_week_start(db, week_start)
    if week_key is None:
        raise ValueError(f"No offseason week mapping for {week_start}")
    season_year, week = week_key
    _seed_fallback_for_week(db, week_start, "mood")

    rows = db.query_all(
        """
        select
          twcf.*,
          t.slug,
          t.canonical_name
        from team_week_conversation_features twcf
        join teams t on t.team_id = twcf.team_id
        where twcf.season_year = %(season_year)s
          and twcf.week = %(week)s
          and (t.level_code = 'FBS' or lower(coalesce(t.cfbd_classification, '')) = 'fbs')
        order by twcf.team_id
        """,
        {"season_year": season_year, "week": week},
    )
    best_by_team: dict[int, dict[str, Any]] = {}
    for row in sorted(rows, key=_source_priority):
        best_by_team.setdefault(int(row["team_id"]), row)

    previous_start = _previous_week_start(db, week_start)
    computed_rows: list[dict[str, Any]] = []
    for row in best_by_team.values():
        mentions = int(row.get("mention_count") or 0)
        authors = int(row.get("unique_author_count") or 0)
        sentiment = float(row.get("mean_sentiment_score") or 0.0)
        if mentions < MIN_MENTIONS_FOR_SIGNAL or authors < MIN_AUTHORS_FOR_SIGNAL:
            continue
        mood_score = int(round(50 + 50 * sentiment * min(1.0, mentions / 50.0)))
        mood_score = max(0, min(100, mood_score))
        previous_score = None
        if previous_start:
            previous = db.query_one(
                """
                select mood_score
                from fanbase_mood_weekly
                where team_id = %(team_id)s and week_start_date = %(week_start)s
                limit 1
                """,
                {"team_id": row["team_id"], "week_start": previous_start},
            )
            previous_score = int(previous["mood_score"]) if previous and previous.get("mood_score") is not None else None
        delta = mood_score - previous_score if previous_score is not None else 0
        computed_rows.append(
            {
                "team_id": int(row["team_id"]),
                "week_start_date": week_start,
                "mood_score": mood_score,
                "delta_from_prev_week": int(delta),
                "top_cause_token": "conversation_signal",
                "top_cause_label": "conversation signal",
                "sample_size": mentions,
                "source": "computed",
                "sample_authors": authors,
                "confidence": _confidence(mentions, authors),
            }
        )

    _write_computed_rows(
        db,
        "fanbase_mood_weekly",
        computed_rows,
        key_columns=["team_id", "week_start_date"],
        update_columns=[
            "mood_score",
            "delta_from_prev_week",
            "top_cause_token",
            "top_cause_label",
            "sample_size",
            "source",
            "sample_authors",
            "confidence",
            "ingested_at",
        ],
        run_id=f"mood:{season_year}:{week}",
    )
    return len(computed_rows)


def compute_rivalry_ratios_from_features(db: Database, week_start: str) -> int:
    week_key = _week_for_week_start(db, week_start)
    if week_key is None:
        raise ValueError(f"No offseason week mapping for {week_start}")
    season_year, week = week_key
    _seed_fallback_for_week(db, week_start, "rivalry")

    pairs = db.query_all(
        """
        select
          a.team_id as team_a_id,
          a.rival_team_id as team_b_id,
          ta.slug as team_a_slug,
          tb.slug as team_b_slug,
          ta.canonical_name as team_a_name,
          tb.canonical_name as team_b_name,
          a.mention_count as a_mentions_b_count,
          b.mention_count as b_mentions_a_count,
          a.sample_authors + b.sample_authors as sample_authors
        from team_week_rival_mentions a
        join team_week_rival_mentions b
          on a.team_id = b.rival_team_id
         and a.rival_team_id = b.team_id
         and a.season_year = b.season_year
         and a.week = b.week
         and a.source_name = b.source_name
         and a.audience_bucket = b.audience_bucket
        join teams ta on ta.team_id = a.team_id
        join teams tb on tb.team_id = a.rival_team_id
        where a.season_year = %(season_year)s
          and a.week = %(week)s
          and a.team_id < a.rival_team_id
          and a.mention_count >= 8
          and b.mention_count >= 8
        """,
        {"season_year": season_year, "week": week},
    )
    rows: list[dict[str, Any]] = []
    for pair in pairs:
        a_count = int(pair["a_mentions_b_count"])
        b_count = int(pair["b_mentions_a_count"])
        if a_count >= b_count:
            ratio = a_count / max(b_count, 1)
            leaning = 1
        else:
            ratio = b_count / max(a_count, 1)
            leaning = 2
        slug = f"{pair['team_a_slug']}-{pair['team_b_slug']}"
        name = f"{pair['team_a_name']} / {pair['team_b_name']}"
        rows.append(
            {
                "rivalry_slug": slug,
                "rivalry_name": name,
                "team_a_id": int(pair["team_a_id"]),
                "team_b_id": int(pair["team_b_id"]),
                "week_start_date": week_start,
                "a_mentions_b_count": a_count,
                "b_mentions_a_count": b_count,
                "ratio_dominant": round(ratio, 2),
                "leaning_team": leaning,
                "take": "Computed from pair-level team-week rival mentions.",
                "source": "computed",
                "sample_authors": int(pair.get("sample_authors") or 0),
                "confidence": _confidence(a_count + b_count, int(pair.get("sample_authors") or 0)),
            }
        )

    _write_computed_rows(
        db,
        "rivalry_obsession_weekly",
        rows,
        key_columns=["rivalry_slug", "week_start_date"],
        update_columns=[
            "rivalry_name",
            "team_a_id",
            "team_b_id",
            "a_mentions_b_count",
            "b_mentions_a_count",
            "ratio_dominant",
            "leaning_team",
            "take",
            "source",
            "sample_authors",
            "confidence",
            "ingested_at",
        ],
        run_id=f"rivalry:{season_year}:{week}",
    )
    return len(rows)


def _median_total_volume(db: Database, season_year: int, weeks: list[int]) -> float | None:
    totals = []
    for week in weeks:
        row = db.query_one(
            """
            select sum(mention_count) as volume
            from team_week_conversation_features
            where season_year = %(season_year)s and week = %(week)s
            """,
            {"season_year": season_year, "week": week},
        )
        volume = int(row["volume"] or 0) if row else 0
        if volume:
            totals.append(volume)
    return float(median(totals)) if totals else None


def compute_lexicon_spikes_from_features(db: Database, week_start: str) -> int:
    week_key = _week_for_week_start(db, week_start)
    if week_key is None:
        raise ValueError(f"No offseason week mapping for {week_start}")
    season_year, week = week_key
    _seed_fallback_for_week(db, week_start, "lexicon")

    current_volume = _median_total_volume(db, season_year, [week])
    prior_volume = _median_total_volume(db, season_year, [week - 3, week - 2, week - 1])
    outage_guard = current_volume is not None and prior_volume is not None and current_volume < prior_volume * 0.6

    phrases = db.query_all(
        """
        select *
        from phrase_mentions_weekly
        where season_year = %(season_year)s
          and week = %(week)s
        """,
        {"season_year": season_year, "week": week},
    )
    candidates: list[dict[str, Any]] = []
    if not outage_guard:
        for phrase in phrases:
            history = db.query_all(
                """
                select week, document_count, mention_count
                from phrase_mentions_weekly
                where phrase = %(phrase)s
                  and season_year = %(season_year)s
                  and week between %(start_week)s and %(end_week)s
                order by week
                """,
                {
                    "phrase": phrase["phrase"],
                    "season_year": season_year,
                    "start_week": week - 3,
                    "end_week": week - 1,
                },
            )
            prior_counts = [int(row.get("document_count") or row.get("mention_count") or 0) for row in history]
            if len(prior_counts) < 3 or any(count < 5 for count in prior_counts):
                continue
            baseline = median(prior_counts)
            current = int(phrase.get("document_count") or phrase.get("mention_count") or 0)
            if baseline <= 0 or current <= baseline:
                continue
            spike = ((current - baseline) / baseline) * 100.0
            if spike < 100.0:
                continue
            candidates.append(
                {
                    "phrase": phrase["phrase"],
                    "week_start_date": week_start,
                    "mention_count": int(phrase.get("mention_count") or current),
                    "spike_pct_wow": round(spike, 1),
                    "origin_community": phrase.get("audience_bucket") or "fan",
                    "related_team_id": None,
                    "sample_quotes_json": phrase.get("sample_quotes_json") or "[]",
                    "trend_json": json.dumps(
                        [
                            {"week": f"W-{3 - idx}", "frequency": count}
                            for idx, count in enumerate(prior_counts)
                        ]
                        + [{"week": "Now", "frequency": current}]
                    ),
                    "narrative": "Computed phrase spike from distinct conversation-document counts.",
                    "featured": 0,
                    "source": "computed",
                    "sample_authors": 0,
                    "confidence": round(min(1.0, current / 50.0), 3),
                }
            )

    candidates.sort(key=lambda row: float(row["spike_pct_wow"]), reverse=True)
    for idx, row in enumerate(candidates):
        row["featured"] = 1 if idx == 0 else 0
    _write_computed_rows(
        db,
        "lexicon_weekly",
        candidates,
        key_columns=["phrase", "week_start_date"],
        update_columns=[
            "mention_count",
            "spike_pct_wow",
            "origin_community",
            "related_team_id",
            "sample_quotes_json",
            "trend_json",
            "narrative",
            "featured",
            "source",
            "sample_authors",
            "confidence",
            "ingested_at",
        ],
        run_id=f"lexicon:{season_year}:{week}",
    )
    return len(candidates)


def _where_clause(row_key: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    params = {f"k_{idx}": value for idx, value in enumerate(row_key.values())}
    parts = [f"{column} = :k_{idx}" for idx, column in enumerate(row_key.keys())]
    return " and ".join(parts), params


def promote_row_to_computed(
    db: Database,
    table: str,
    row_key: dict[str, Any],
    computed_value: dict[str, Any],
    confidence: float,
    *,
    run_id: str | None = None,
    reason: str = "retro computed promotion",
) -> bool:
    where_sql, params = _where_clause(row_key)
    old = db.query_one(f"select * from {table} where {where_sql} limit 1", params)
    if not old:
        return False
    new_values = {**computed_value, "source": "computed", "confidence": confidence}
    old_values = {column: old.get(column) for column in new_values}
    update_sql = ", ".join(f"{column} = :u_{column}" for column in new_values)
    update_params = {**params, **{f"u_{column}": value for column, value in new_values.items()}}
    db.execute(f"update {table} set {update_sql} where {where_sql}", update_params)
    db.upsert_many(
        "hub_provenance_audit",
        [
            {
                "table_name": table,
                "row_key_json": json.dumps(row_key, sort_keys=True),
                "old_value_json": json.dumps(old_values, sort_keys=True),
                "new_value_json": json.dumps(new_values, sort_keys=True),
                "old_source": str(old.get("source") or "computed"),
                "new_source": "computed",
                "run_id": run_id or str(uuid4()),
                "reason": reason,
            }
        ],
        conflict_columns=["audit_id"],
        update_columns=[],
    )
    return True


def revert_row_to_editorial(
    db: Database,
    table: str,
    row_key: dict[str, Any],
    *,
    reason: str = "retro editorial revert",
) -> bool:
    row_key_json = json.dumps(row_key, sort_keys=True)
    audit = db.query_one(
        """
        select *
        from hub_provenance_audit
        where table_name = %(table)s and row_key_json = %(row_key)s
        order by audit_id desc
        limit 1
        """,
        {"table": table, "row_key": row_key_json},
    )
    if not audit:
        return False
    old_values = json.loads(audit["old_value_json"])
    old_source = str(audit.get("old_source") or "editorial")
    old_values["source"] = old_source
    where_sql, params = _where_clause(row_key)
    update_sql = ", ".join(f"{column} = :u_{column}" for column in old_values)
    update_params = {**params, **{f"u_{column}": value for column, value in old_values.items()}}
    db.execute(f"update {table} set {update_sql} where {where_sql}", update_params)
    db.upsert_many(
        "hub_provenance_audit",
        [
            {
                "table_name": table,
                "row_key_json": row_key_json,
                "old_value_json": audit["new_value_json"],
                "new_value_json": json.dumps(old_values, sort_keys=True),
                "old_source": "computed",
                "new_source": old_source,
                "run_id": str(uuid4()),
                "reason": reason,
            }
        ],
        conflict_columns=["audit_id"],
        update_columns=[],
    )
    return True


def revert_week_to_editorial(db: Database, week_start: str) -> int:
    """Best-effort audited revert for computed rows on a retro issue week."""

    reverted = 0
    mood_rows = db.query_all(
        """
        select team_id, week_start_date
        from fanbase_mood_weekly
        where week_start_date = %(week_start)s and source = 'computed'
        """,
        {"week_start": week_start},
    )
    for row in mood_rows:
        if revert_row_to_editorial(
            db,
            "fanbase_mood_weekly",
            {"team_id": row["team_id"], "week_start_date": row["week_start_date"]},
            reason="seed-retro-issue revert",
        ):
            reverted += 1

    rivalry_rows = db.query_all(
        """
        select rivalry_slug, week_start_date
        from rivalry_obsession_weekly
        where week_start_date = %(week_start)s and source = 'computed'
        """,
        {"week_start": week_start},
    )
    for row in rivalry_rows:
        if revert_row_to_editorial(
            db,
            "rivalry_obsession_weekly",
            {"rivalry_slug": row["rivalry_slug"], "week_start_date": row["week_start_date"]},
            reason="seed-retro-issue revert",
        ):
            reverted += 1

    lexicon_rows = db.query_all(
        """
        select phrase, week_start_date
        from lexicon_weekly
        where week_start_date = %(week_start)s and source = 'computed'
        """,
        {"week_start": week_start},
    )
    for row in lexicon_rows:
        if revert_row_to_editorial(
            db,
            "lexicon_weekly",
            {"phrase": row["phrase"], "week_start_date": row["week_start_date"]},
            reason="seed-retro-issue revert",
        ):
            reverted += 1
    return reverted


def _mood_score_for(db: Database, slug: str, week_start: str) -> int | None:
    team_id = _team_id_by_slug(db, slug)
    if team_id is None:
        return None
    row = db.query_one(
        """
        select mood_score
        from fanbase_mood_weekly
        where team_id = %(team_id)s
          and week_start_date = %(week_start)s
          and source = 'computed'
        limit 1
        """,
        {"team_id": team_id, "week_start": week_start},
    )
    return int(row["mood_score"]) if row and row.get("mood_score") is not None else None


def _direction_check(
    db: Database,
    *,
    name: str,
    slug: str,
    current_week: str,
    baseline_week: str,
    minimum_delta: int,
    direction: str,
) -> dict[str, Any]:
    current = _mood_score_for(db, slug, current_week)
    baseline = _mood_score_for(db, slug, baseline_week)
    expected = f"{direction} {abs(minimum_delta)}"
    if current is None or baseline is None:
        return {"check": name, "status": "INSUFFICIENT DATA", "observed": "missing", "expected": expected}
    delta = current - baseline
    passes = delta >= minimum_delta if direction == "up" else delta <= -abs(minimum_delta)
    return {"check": name, "status": "PASS" if passes else "FAIL", "observed": f"{delta:+d}", "expected": expected}


def retro_calibrate(db: Database, window: str = "21..30") -> list[dict[str, Any]]:
    """Run the retro directional checks.

    Checks with missing baselines are explicitly insufficient instead of failing,
    which keeps Phase B honest when the Jan. 12 Week 21 baseline has not been
    backfilled yet.
    """

    checks = [
        {"name": "Indiana title jump", "slug": "indiana", "current_week": "2026-01-19", "baseline_week": "2026-01-12", "minimum_delta": 8, "direction": "up"},
        {"name": "Miami title drop", "slug": "miami", "current_week": "2026-01-19", "baseline_week": "2026-01-12", "minimum_delta": 8, "direction": "down"},
        {"name": "Oregon portal gain", "slug": "oregon", "current_week": "2026-01-26", "baseline_week": "2026-01-19", "minimum_delta": 5, "direction": "up"},
        {"name": "Nebraska portal loss", "slug": "nebraska", "current_week": "2026-01-26", "baseline_week": "2026-01-19", "minimum_delta": 5, "direction": "down"},
        {"name": "USC signing gain", "slug": "usc", "current_week": "2026-02-09", "baseline_week": "2026-02-02", "minimum_delta": 5, "direction": "up"},
        {"name": "Texas spring drop", "slug": "texas", "current_week": "2026-02-23", "baseline_week": "2026-02-09", "minimum_delta": 4, "direction": "down"},
        {"name": "Oregon hype gain", "slug": "oregon", "current_week": "2026-03-02", "baseline_week": "2026-02-23", "minimum_delta": 5, "direction": "up"},
        {"name": "Michigan presser drop", "slug": "michigan", "current_week": "2026-03-09", "baseline_week": "2026-03-02", "minimum_delta": 8, "direction": "down"},
        {"name": "Michigan hire rebound", "slug": "michigan", "current_week": "2026-03-23", "baseline_week": "2026-03-09", "minimum_delta": 5, "direction": "up"},
        {"name": "Michigan spring-game drop", "slug": "michigan", "current_week": "2026-04-06", "baseline_week": "2026-03-23", "minimum_delta": 5, "direction": "down"},
    ]
    return [_direction_check(db, **check) for check in checks]
