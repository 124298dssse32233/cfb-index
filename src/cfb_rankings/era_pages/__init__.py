"""WS-07 — CFP-era pages (three-act program history).

A program's CFP-era story (2014-present) told in three acts:
Founding (2014-2020) / Transition (2021-2023) / Expansion (2024-present).

Public API:
    build_era_summary(db, slug, *, end_season=...) -> EraSummary | None
    render_era_page(summary) -> str   (self-contained HTML, inline CSS)
"""
from __future__ import annotations

from .data import (
    ACTS,
    EraAct,
    EraSeason,
    EraSummary,
    build_era_summary,
)
from .renderer import render_era_page

__all__ = [
    "ACTS",
    "EraAct",
    "EraSeason",
    "EraSummary",
    "build_era_summary",
    "render_era_page",
]
