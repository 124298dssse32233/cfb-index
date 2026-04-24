"""Scenario Explorer — interactive "what if" projection (S3.3 / §4 Bet #12).

Builds the server-side payload the Alpine widget consumes. Given a
player's current signature-metric value + the metric's cohort
distribution, the client slider lets a reader project remaining-game
totals and see where the resulting season value lands in the cohort.

Data reality today: player_game_stats has only 2025 Week 1, so
"remaining games" can't be computed from snaps played. Fallback: use
the metric's season total and a generic `remaining_games` default of
4. Reader adjusts via slider.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cfb_rankings.db import Database


@dataclass(frozen=True)
class ScenarioPayload:
    applicable: bool
    metric_id: str
    metric_label: str
    current_value: float
    current_rank: int
    cohort_size: int
    cohort_label: str
    cohort_values_sorted: list[float]  # descending
    default_remaining_games: int
    default_per_game_projection: float
    unit: str


def build_scenario_payload(
    db: Database, player_id: int, season: int
) -> ScenarioPayload | None:
    try:
        from cfb_rankings.signature_story import build_candidate_scoreboard
        scoreboard = build_candidate_scoreboard(db, player_id, season, None)
    except Exception:
        return None
    if not scoreboard:
        return None
    w = scoreboard[0]
    # Cohort values already live inside w.cohort_rows — sorted by value.
    cohort_values = sorted(
        (float(r.get("value")) for r in w.cohort_rows if r.get("value") is not None),
        reverse=w.metric.higher_is_better,
    )
    # Per-game projection default: current value / 4 as rough pace.
    default_per_game = (
        float(w.value) / 4.0 if w.value not in (None, 0) else 0.0
    )
    return ScenarioPayload(
        applicable=True,
        metric_id=str(w.metric.id),
        metric_label=str(w.metric.label),
        current_value=float(w.value),
        current_rank=int(w.rank),
        cohort_size=int(w.cohort_size),
        cohort_label=str(w.metric.cohort),
        cohort_values_sorted=cohort_values,
        default_remaining_games=4,
        default_per_game_projection=round(default_per_game, 2),
        unit=str(w.metric.unit),
    )


def payload_to_dict(payload: ScenarioPayload | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return {
        "applicable":                  payload.applicable,
        "metric_id":                   payload.metric_id,
        "metric_label":                payload.metric_label,
        "current_value":               payload.current_value,
        "current_rank":                payload.current_rank,
        "cohort_size":                 payload.cohort_size,
        "cohort_label":                payload.cohort_label,
        "cohort_values_sorted":        payload.cohort_values_sorted,
        "default_remaining_games":     payload.default_remaining_games,
        "default_per_game_projection": payload.default_per_game_projection,
        "unit":                        payload.unit,
    }
