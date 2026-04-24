"""Player advanced metric computation (Autopilot v1 TASK 1.4)."""

from cfb_rankings.metrics.player_advanced import (
    METRICS,
    MetricResult,
    MetricSpec,
    compute_player_advanced_metrics,
    compute_player_advanced_metrics_season,
)

__all__ = [
    "METRICS",
    "MetricResult",
    "MetricSpec",
    "compute_player_advanced_metrics",
    "compute_player_advanced_metrics_season",
]
