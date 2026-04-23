"""Cohort divergence metric — STRATEGY §4 / TASK 8.1.

    divergence_score = stdev(cohort_sentiment for each cohort where effective_n ≥ FLOOR_MIN)

High divergence = fragmented fanbase = story. Low divergence = real consensus.
Written to ``team_cohort_divergence_week`` per (team_id, week).

Only cohorts that passed the floor (sentiment_score IS NOT NULL) participate.
If fewer than 2 cohorts qualify, divergence_score is NULL.
"""
from __future__ import annotations

import math
from typing import Iterable

from cfb_rankings.db import Database


def _utcnow_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sample_stdev(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(var)


def compute_divergence_week(db: Database, week_key: str,
                            teams: Iterable[int] | None = None) -> dict[str, int]:
    params: dict[str, object] = {"week": week_key}
    filter_sql = ""
    if teams:
        team_list = list(teams)
        placeholders = ",".join(f":team_{i}" for i in range(len(team_list)))
        for i, t in enumerate(team_list):
            params[f"team_{i}"] = t
        filter_sql = f" and team_id in ({placeholders}) "

    rows = db.query_all(
        f"""
        select team_id, cohort, sentiment_score
        from team_cohort_week
        where week = :week
          and sentiment_score is not null
          {filter_sql}
        """,
        params,
    )

    by_team: dict[int, list[float]] = {}
    for r in rows:
        by_team.setdefault(r["team_id"], []).append(float(r["sentiment_score"]))

    written = 0
    for team_id, sentiments in by_team.items():
        n = len(sentiments)
        score = _sample_stdev(sentiments) if n >= 2 else None
        db.execute(
            """
            insert into team_cohort_divergence_week (
                team_id, week, divergence_score, num_cohorts_qualifying,
                created_at_utc, updated_at_utc
            ) values (
                :team_id, :week, :score, :n, :now, :now
            )
            on conflict (team_id, week) do update set
                divergence_score = excluded.divergence_score,
                num_cohorts_qualifying = excluded.num_cohorts_qualifying,
                updated_at_utc = excluded.updated_at_utc
            """,
            {
                "team_id": team_id,
                "week": week_key,
                "score": score,
                "n": n,
                "now": _utcnow_iso(),
            },
        )
        written += 1

    # Also write zero-row entries for teams that exist in team_cohort_week
    # for this week but had zero qualifying cohorts (so /methodology can show
    # "Awaiting Signal" instead of omitting the team silently).
    empty_rows = db.query_all(
        """
        select distinct team_id from team_cohort_week
        where week = :week and team_id not in (
            select team_id from team_cohort_week
            where week = :week and sentiment_score is not null
        )
        """,
        {"week": week_key},
    )
    for r in empty_rows:
        db.execute(
            """
            insert into team_cohort_divergence_week (
                team_id, week, divergence_score, num_cohorts_qualifying,
                created_at_utc, updated_at_utc
            ) values (
                :team_id, :week, NULL, 0, :now, :now
            )
            on conflict (team_id, week) do update set
                divergence_score = NULL,
                num_cohorts_qualifying = 0,
                updated_at_utc = excluded.updated_at_utc
            """,
            {"team_id": r["team_id"], "week": week_key, "now": _utcnow_iso()},
        )
        written += 1

    return {"teams_written": written}


__all__ = ["compute_divergence_week"]
