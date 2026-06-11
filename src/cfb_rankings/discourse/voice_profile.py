"""Fanbase voice personality aggregates — Language Layer Wave 2 (A4).

Per (team, season): one aggregation over ``conversation_document_targets``
joined to ``conversation_documents``, restricted to the fan-voice corpus
(reddit/bluesky/youtube/board + city-sub exclusion — the SAME source filter as
keyness, via ``_common.fan_voice_filter_sql``):

* ``optimism_mean`` = avg(sentiment_score)
* ``joy_share``     = share of emotion_primary in (joy, optimism)
* ``anger_share``   = share of emotion_primary in (anger, disgust)
* ``doom_share``    = share of emotion_primary in (fear, sadness, pessimism)
* ``sarcasm_mean``  = avg(coalesce(sarcasm_score, 0))

Cohort = teams with ``n_mentions >= min_mentions`` THAT SEASON. Percentile
ranks (0-100) + ``optimism_rank`` (1-based dense rank, 1 = most optimistic)
are computed WITHIN the cohort at write time, rows are written ONLY for cohort
members, and each requested season is fully cleared before insert — so no
stale below-floor rows linger (the Wave-1 stale-row contract).

Season bucketing: the SQL aggregates per (team, day) and the days are bucketed
into seasons in Python via ``resolve_week(day).season_year`` (A5) — exact
weighted recombination from per-day sums, no approximation.

PYTHONUTF8 note: never prints raw post text — counts and slugs only.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from cfb_rankings.common.week import resolve_week

from ._common import fan_voice_filter_sql
from .keyness import _row_get

MODEL_VERSION = "discourse-voice-v1"

_METRICS = ("optimism", "joy", "anger", "doom", "sarcasm")


def _pct_rank(values: list[float], v: float) -> int:
    """0-100 percentile rank within the cohort (prototype-validated formula)."""
    return round(100 * sum(1 for x in values if x < v) / max(len(values) - 1, 1))


def compute_fanbase_voice(
    db: Any,
    *,
    seasons: list[int],
    min_mentions: int = 300,
    commit: bool = False,
) -> dict:
    """Compute + (optionally) store per-(team, season) voice profiles.

    ``commit=False`` is a dry run: computes, prints the cohort summary, writes
    nothing. Returns ``{"seasons", "rows_written", "cohorts"}`` where
    ``cohorts`` maps season -> cohort size.
    """
    season_list = sorted({int(s) for s in seasons})
    season_set = set(season_list)
    if not season_set:
        raise ValueError("compute_fanbase_voice: at least one season required")

    # Slug map for readable progress lines.
    slug_by_id: dict[int, str] = {}
    try:
        for row in db.query_all("SELECT team_id, slug FROM teams"):
            tid = _row_get(row, "team_id")
            slug = _row_get(row, "slug")
            if tid is not None and slug:
                slug_by_id[int(tid)] = str(slug)
    except Exception:
        pass

    # -- one SQL aggregation per (team, day); seasons recombined in Python ---
    where, city_params = fan_voice_filter_sql("d")
    agg_sql = (
        "SELECT t.team_id AS team_id, "
        "SUBSTR(COALESCE(d.external_created_at_utc,''),1,10) AS day, "
        "COUNT(*) AS n, "
        "SUM(COALESCE(t.sentiment_score, 0)) AS sent_sum, "
        "SUM(CASE WHEN t.emotion_primary IN ('joy','optimism') "
        "THEN 1 ELSE 0 END) AS joy_n, "
        "SUM(CASE WHEN t.emotion_primary IN ('anger','disgust') "
        "THEN 1 ELSE 0 END) AS anger_n, "
        "SUM(CASE WHEN t.emotion_primary IN ('fear','sadness','pessimism') "
        "THEN 1 ELSE 0 END) AS doom_n, "
        "SUM(COALESCE(t.sarcasm_score, 0)) AS sarcasm_sum "
        "FROM conversation_document_targets t "
        "JOIN conversation_documents d "
        "ON d.conversation_document_id = t.conversation_document_id "
        f"WHERE t.target_type = 'team' AND t.team_id IS NOT NULL AND {where} "
        "GROUP BY t.team_id, day"
    )
    day_rows = db.query_all(agg_sql, city_params)

    # (team_id, season) -> [n, sent_sum, joy_n, anger_n, doom_n, sarcasm_sum]
    acc: dict[tuple[int, int], list[float]] = defaultdict(
        lambda: [0, 0.0, 0, 0, 0, 0.0]
    )
    for row in day_rows:
        day = _row_get(row, "day") or ""
        if len(day) != 10:
            continue
        try:
            season = resolve_week(day).season_year
        except (ValueError, TypeError):
            continue
        if season not in season_set:
            continue
        tid = int(_row_get(row, "team_id") or 0)
        bucket = acc[(tid, season)]
        bucket[0] += int(_row_get(row, "n") or 0)
        bucket[1] += float(_row_get(row, "sent_sum") or 0.0)
        bucket[2] += int(_row_get(row, "joy_n") or 0)
        bucket[3] += int(_row_get(row, "anger_n") or 0)
        bucket[4] += int(_row_get(row, "doom_n") or 0)
        bucket[5] += float(_row_get(row, "sarcasm_sum") or 0.0)

    # -- per-season cohort, percentiles + ranks at write time ----------------
    computed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_rows: list[dict[str, Any]] = []
    cohorts: dict[int, int] = {}
    for season in season_list:
        members: list[tuple[int, dict[str, float], int]] = []
        for (tid, s), bucket in acc.items():
            if s != season:
                continue
            n = int(bucket[0])
            if n < min_mentions:
                continue
            measures = {
                "optimism": bucket[1] / n,
                "joy": bucket[2] / n,
                "anger": bucket[3] / n,
                "doom": bucket[4] / n,
                "sarcasm": bucket[5] / n,
            }
            members.append((tid, measures, n))
        if not members:
            continue
        cohort_size = len(members)
        cohorts[season] = cohort_size
        series = {
            m: [measures[m] for _tid, measures, _n in members] for m in _METRICS
        }
        # Dense rank on optimism_mean, descending (1 = most optimistic).
        distinct_desc = sorted(
            {measures["optimism"] for _tid, measures, _n in members}, reverse=True
        )
        rank_of = {v: i + 1 for i, v in enumerate(distinct_desc)}

        for tid, measures, n in sorted(members):
            out_rows.append(
                {
                    "team_id": tid,
                    "season_year": season,
                    "n_mentions": n,
                    "optimism_mean": round(measures["optimism"], 6),
                    "joy_share": round(measures["joy"], 6),
                    "anger_share": round(measures["anger"], 6),
                    "doom_share": round(measures["doom"], 6),
                    "sarcasm_mean": round(measures["sarcasm"], 6),
                    "optimism_pct": _pct_rank(series["optimism"], measures["optimism"]),
                    "joy_pct": _pct_rank(series["joy"], measures["joy"]),
                    "anger_pct": _pct_rank(series["anger"], measures["anger"]),
                    "doom_pct": _pct_rank(series["doom"], measures["doom"]),
                    "sarcasm_pct": _pct_rank(series["sarcasm"], measures["sarcasm"]),
                    "optimism_rank": rank_of[measures["optimism"]],
                    "cohort_size": cohort_size,
                    "model_version": MODEL_VERSION,
                    "computed_at_utc": computed_at,
                }
            )
        top = max(members, key=lambda m: m[1]["optimism"])
        bottom = min(members, key=lambda m: m[1]["optimism"])
        print(
            f"  season {season}: cohort={cohort_size} (floor {min_mentions}) — "
            f"most optimistic {slug_by_id.get(top[0], top[0])} "
            f"({top[1]['optimism']:+.3f}), least "
            f"{slug_by_id.get(bottom[0], bottom[0])} "
            f"({bottom[1]['optimism']:+.3f})",
            flush=True,
        )

    # -- write (full season clear + insert cohort rows only) -----------------
    # Every requested season is cleared even when its cohort is empty — the
    # Wave-1 stale-row contract (no below-floor leftovers from prior runs).
    rows_written = 0
    if commit:
        insert_sql = (
            "INSERT INTO fanbase_voice_profile ("
            "team_id, season_year, n_mentions, optimism_mean, joy_share, "
            "anger_share, doom_share, sarcasm_mean, optimism_pct, joy_pct, "
            "anger_pct, doom_pct, sarcasm_pct, optimism_rank, cohort_size, "
            "model_version, computed_at_utc"
            ") VALUES ("
            ":team_id, :season_year, :n_mentions, :optimism_mean, :joy_share, "
            ":anger_share, :doom_share, :sarcasm_mean, :optimism_pct, :joy_pct, "
            ":anger_pct, :doom_pct, :sarcasm_pct, :optimism_rank, :cohort_size, "
            ":model_version, :computed_at_utc)"
        )
        with db.connection() as conn:
            for season in season_list:
                conn.execute(
                    "DELETE FROM fanbase_voice_profile "
                    "WHERE season_year = :season",
                    {"season": season},
                )
            conn.executemany(insert_sql, out_rows)
            rows_written = len(out_rows)
            conn.commit()
    else:
        print(
            "compute_fanbase_voice: dry run — "
            f"{len(out_rows)} profile rows across {len(cohorts)} season cohorts "
            "NOT written (use --commit)",
            flush=True,
        )

    return {
        "seasons": season_list,
        "rows_written": rows_written,
        "cohorts": cohorts,
    }


__all__ = ["compute_fanbase_voice", "MODEL_VERSION"]
