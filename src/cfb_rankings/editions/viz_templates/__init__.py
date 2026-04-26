"""Cover-viz template renderers.

Each template takes a ``data`` dict (sourced from
``editions.cover_viz_data_json``) and returns an SVG string. Pre-rendered
at build time — no client-side charting. Each template ships with an
``annotate(point, label, color)`` API for editorial annotations.

Templates:
    gap         — dumbbell chart (two endpoints + connecting bar per row)
    drift       — slope chart (≤6 lines, named endpoints, hand-annotated swings)
    field       — beeswarm of 134 programs by mood × velocity
    heatmap     — calendar heatmap of conversation volume by program-week
    distribution — joyplot/ridgeplot of mood by program over time
    flow        — sankey of attention/topic movement week-over-week
    rank_shift  — bump chart of top-10 programs by ranking change
"""
from __future__ import annotations

from typing import Any, Callable

from . import distribution, drift, field, flow, gap, heatmap, rank_shift


_RENDERERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "gap": gap.render,
    "drift": drift.render,
    "field": field.render,
    "heatmap": heatmap.render,
    "distribution": distribution.render,
    "flow": flow.render,
    "rank_shift": rank_shift.render,
}


def render(viz_kind: str, data: dict[str, Any]) -> str:
    """Render the requested viz_kind. Raises ``KeyError`` for unknown kinds."""
    return _RENDERERS[viz_kind](data)


def available_kinds() -> list[str]:
    return sorted(_RENDERERS)
