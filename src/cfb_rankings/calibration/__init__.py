"""WS-09 calibration — the product's prediction trust spine.

Public surface:
  - record_prediction        : log/refresh one standing prediction (idempotent).
  - resolve_due_predictions  : weekly outcome resolver (per D-015 cadence A/C).
  - calibration_summary      : per-model/per-kind accuracy aggregate for the
                               methodology page + Sunday public summary (D-015 B).
  - record_archetype_predictions : the first instrumented live surface.
"""
from __future__ import annotations

from cfb_rankings.calibration.ledger import (
    OUTCOME_RESOLVERS,
    calibration_summary,
    prediction_id_for,
    record_archetype_predictions,
    record_prediction,
    record_season_win_predictions,
    resolve_due_predictions,
)

__all__ = [
    "OUTCOME_RESOLVERS",
    "calibration_summary",
    "prediction_id_for",
    "record_archetype_predictions",
    "record_prediction",
    "record_season_win_predictions",
    "resolve_due_predictions",
]
