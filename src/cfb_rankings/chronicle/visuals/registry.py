"""Visual registry — maps VisualId -> (query function, renderer function).

Adding a new visual = add the mapping here. The pipeline never reaches into
queries.py or families/ directly — it goes through this registry.
"""
from __future__ import annotations

from typing import Callable

from .models import VisualId, ChartFamily
from . import queries
from .families import ladder, waterfall, braid, tilemosaic, scatter


# Each entry: (chart_family, query_fn, renderer_fn)
_REGISTRY: dict[VisualId, tuple[ChartFamily, Callable, Callable]] = {
    VisualId.STATEMENT_WIN_LADDER: (
        ChartFamily.WATERFALL,  # waterfall-style ladder showing delta magnitudes
        queries.query_statement_win_ladder,
        ladder.render_statement_win_ladder,
    ),
    VisualId.RETURNING_PRODUCTION_XRAY: (
        ChartFamily.WATERFALL,
        queries.query_returning_production_xray,
        waterfall.render_returning_production_xray,
    ),
    VisualId.HEISMAN_RACE_BRAID: (
        ChartFamily.BRAID,
        queries.query_heisman_race_braid,
        braid.render_heisman_race_braid,
    ),
    VisualId.ROSTER_REPLACEMENT_GRID: (
        ChartFamily.TILE_MOSAIC,
        queries.query_roster_replacement_grid,
        tilemosaic.render_roster_replacement_grid,
    ),
    VisualId.CFP_BUBBLE_WALL: (
        ChartFamily.ANNOTATED_SCATTER,
        queries.query_cfp_bubble_wall,
        scatter.render_cfp_bubble_wall,
    ),
    VisualId.TALENT_YIELD_CURVE: (
        ChartFamily.ANNOTATED_SCATTER,
        queries.query_talent_yield_curve,
        scatter.render_talent_yield_curve,
    ),
}


def list_registered_visuals() -> list[VisualId]:
    return list(_REGISTRY.keys())


def get_query_function(visual_id: VisualId) -> Callable:
    return _REGISTRY[visual_id][1]


def get_renderer_function(visual_id: VisualId) -> Callable:
    return _REGISTRY[visual_id][2]


def get_chart_family(visual_id: VisualId) -> ChartFamily:
    return _REGISTRY[visual_id][0]
