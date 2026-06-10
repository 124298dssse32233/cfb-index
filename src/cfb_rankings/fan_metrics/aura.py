"""Aura — player perception vs production (the "Him Watch" engine).

Two axes, percentile-ranked within a position cohort:
- PERCEPTION: how much fans talk about the player (mention volume from
  conversation_document_targets). The hype signal.
- PRODUCTION: on-field value (player_value_metrics weighted-EPA — wepa_passing
  for QBs, wepa_rushing for RBs). The tape.

``aura_tax = perception_pctl - production_pctl``. Positive = more hype than
tape (paying aura tax); negative = quietly producing (underrated). The gap IS
the story. WRs are excluded in v1 — we have no receiving production metric, and
a one-axis "Aura" would be dishonest.

Cohort = position players with production data and >= PLAY_FLOOR snaps, so both
percentiles are computed over the same, sample-meaningful universe. Persisted
to player_aura_weekly (cheap per-player-page lookups + future wk/wk movement).

CLI:
    python manage.py compute-aura --season YYYY
"""

from __future__ import annotations

import logging
from typing import Any

from cfb_rankings.common.week import resolve_week
from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

# Production metric per position (player_value_metrics.metric_name). Positions
# absent here are not eligible for Aura (no honest production axis yet).
POSITION_METRIC = {
    "QB": "wepa_passing",
    "RB": "wepa_rushing",
}
PLAY_FLOOR = 100          # cohort inclusion: meaningful on-field sample
MENTION_FLOOR = 8         # below this, perception is noise -> low-signal verdict
TAX_BAND = 18.0           # |aura_tax| past this earns an overhype/underrated verdict


def _percentiles(values: dict[int, float]) -> dict[int, float]:
    """Map {player_id: value} -> {player_id: percentile 0-100}.

    Percentile = share of the cohort with a value <= this one (ties share the
    upper rank), so the cohort max is 100 and a unique min is ~0.
    """
    n = len(values)
    if n == 0:
        return {}
    if n == 1:
        return {next(iter(values)): 100.0}
    import bisect
    ordered = sorted(values.values())
    out: dict[int, float] = {}
    for pid, v in values.items():
        # count of cohort values <= v (bisect_right handles ties as upper rank)
        cnt = bisect.bisect_right(ordered, v)
        out[pid] = round(100.0 * cnt / n, 1)
    return out


def _verdict(aura_tax: float, low_signal: bool) -> str:
    if low_signal:
        return "low_signal"
    if aura_tax >= TAX_BAND:
        return "aura_tax"        # more hype than tape
    if aura_tax <= -TAX_BAND:
        return "underrated"      # quietly producing
    return "matched"             # hype matches tape


def compute_aura(db: Database, *, season: int) -> dict[str, int]:
    """Compute player_aura_weekly for a season across eligible cohorts."""
    week_meta = None
    rows_written = 0
    cohorts_done = 0

    # Resolve a representative week stamp for the season snapshot.
    season_week = db.query_one(
        "select max(week) as w from conversation_document_targets where season_year = :s",
        {"s": season},
    )
    week_no = int(season_week["w"]) if season_week and season_week.get("w") is not None else 0

    out_rows: list[dict[str, Any]] = []
    for position, metric in POSITION_METRIC.items():
        # Cohort: production-qualified players in this position/season.
        cohort = db.query_all(
            """
            select v.player_id, p.full_name, v.metric_value as production, v.plays
            from player_value_metrics v
            join players p on p.player_id = v.player_id
            where v.season_year = :season
              and v.position = :pos
              and v.metric_name = :metric
              and v.plays >= :floor
            """,
            {"season": season, "pos": position, "metric": metric, "floor": PLAY_FLOOR},
        )
        if len(cohort) < 5:
            continue
        cohort_ids = [int(r["player_id"]) for r in cohort]

        # Perception: mention volume per cohort player (0 if unmentioned).
        mentions = {pid: 0 for pid in cohort_ids}
        ph = ",".join(f":p{i}" for i in range(len(cohort_ids)))
        prm = {f"p{i}": pid for i, pid in enumerate(cohort_ids)}
        prm["season"] = season
        mrows = db.query_all(
            f"""
            select player_id, count(*) as n
            from conversation_document_targets
            where target_type = 'player'
              and season_year = :season
              and player_id in ({ph})
            group by player_id
            """,
            prm,
        )
        for r in mrows:
            mentions[int(r["player_id"])] = int(r["n"])

        production = {int(r["player_id"]): float(r["production"]) for r in cohort}
        plays = {int(r["player_id"]): int(r["plays"]) for r in cohort}
        names = {int(r["player_id"]): r["full_name"] for r in cohort}

        perc_pctl = _percentiles({pid: float(m) for pid, m in mentions.items()})
        prod_pctl = _percentiles(production)
        cohort_label = f"{position}s · {len(cohort_ids)} qualified"

        for pid in cohort_ids:
            m = mentions[pid]
            low = m < MENTION_FLOOR
            p_pctl = perc_pctl[pid]
            d_pctl = prod_pctl[pid]
            tax = round(p_pctl - d_pctl, 1)
            out_rows.append(
                {
                    "player_id": pid,
                    "season_year": season,
                    "week": week_no,
                    "week_start_date": None,
                    "position": position,
                    "cohort_label": cohort_label,
                    "cohort_size": len(cohort_ids),
                    "mention_count": m,
                    "perception_pctl": p_pctl,
                    "production_metric": metric,
                    "production_value": round(production[pid], 4),
                    "production_plays": plays[pid],
                    "production_pctl": d_pctl,
                    "aura_score": p_pctl,            # aura = perception percentile
                    "aura_tax": tax,
                    "verdict": _verdict(tax, low),
                    "is_low_signal": 1 if low else 0,
                }
            )
        cohorts_done += 1

    if out_rows:
        db.upsert_many(
            "player_aura_weekly",
            out_rows,
            conflict_columns=["player_id", "season_year", "week"],
            update_columns=[
                "week_start_date", "position", "cohort_label", "cohort_size",
                "mention_count", "perception_pctl", "production_metric",
                "production_value", "production_plays", "production_pctl",
                "aura_score", "aura_tax", "verdict", "is_low_signal",
            ],
        )
        rows_written = len(out_rows)

    logger.info(
        "compute-aura: season=%d cohorts=%d rows=%d", season, cohorts_done, rows_written
    )
    return {"cohorts": cohorts_done, "rows": rows_written}


__all__ = ["compute_aura", "POSITION_METRIC", "PLAY_FLOOR", "MENTION_FLOOR", "TAX_BAND"]
