"""Joyplot / ridgeplot of mood distributions by program over time.

Data shape:
    {
        "title": "...",
        "ridges": [
            {"label": "Texas", "samples": [0.2, 0.3, 0.4, 0.5, 0.6, ...]},
            ...
        ],
        "caption": "...", "source": "..."
    }

Each ridge is rendered as a stacked area whose y-axis is a kernel density
estimate of ``samples``. We use a simple Gaussian KDE evaluated on a fixed
grid.
"""
from __future__ import annotations

import math
from typing import Any

from . import _common as c

WIDTH = 880
TOP_PAD = 80
BOTTOM_PAD = 88
LEFT_PAD = 160
RIGHT_PAD = 60
RIDGE_HEIGHT = 72
RIDGE_OVERLAP = 28
GRID_POINTS = 80


def render(data: dict[str, Any]) -> str:
    ridges = data.get("ridges") or []
    n = len(ridges)
    height = TOP_PAD + n * (RIDGE_HEIGHT - RIDGE_OVERLAP) + RIDGE_HEIGHT + BOTTOM_PAD
    plot_left = LEFT_PAD
    plot_right = WIDTH - RIGHT_PAD

    parts: list[str] = [c.svg_open(WIDTH, height)]
    if data.get("title"):
        parts.append(c.text(plot_left, 28, data["title"],
                            font_size=22, weight="600"))

    parts.append(c.line(plot_left, TOP_PAD, plot_right, TOP_PAD,
                        color=c.PALETTE_RULE, width=0.75))

    for i, ridge in enumerate(ridges):
        cy_top = TOP_PAD + i * (RIDGE_HEIGHT - RIDGE_OVERLAP)
        cy_bot = cy_top + RIDGE_HEIGHT
        samples = [float(s) for s in (ridge.get("samples") or [])]
        density = _kde(samples, GRID_POINTS) if samples else [0.0] * GRID_POINTS
        # Build path.
        points: list[tuple[float, float]] = []
        for j, d in enumerate(density):
            x = plot_left + (plot_right - plot_left) * j / (GRID_POINTS - 1)
            y = cy_bot - (cy_bot - cy_top) * d
            points.append((x, y))
        d_attr = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        d_attr += f" L {points[-1][0]:.1f},{cy_bot:.1f} L {points[0][0]:.1f},{cy_bot:.1f} Z"
        parts.append(c.path(d_attr, stroke=c.PALETTE_INK,
                            stroke_width=1.2, fill=c.PALETTE_CREAM))
        parts.append(c.text(plot_left - 12, cy_bot - 6, ridge.get("label", ""),
                            font_size=12, anchor="end", weight="500"))

    cap_y = height - BOTTOM_PAD + 36
    if data.get("caption"):
        parts.append(c.text(plot_left, cap_y, data["caption"],
                            font_size=13, italic=True))
    if data.get("source"):
        parts.append(c.text(plot_right, cap_y + 22, data["source"],
                            font_size=10, color=c.PALETTE_MUTED,
                            anchor="end", weight="600"))

    parts.append(c.svg_close())
    return c.join(parts)


def _kde(samples: list[float], n_grid: int) -> list[float]:
    if not samples:
        return [0.0] * n_grid
    s_min, s_max = min(samples), max(samples)
    span = (s_max - s_min) or 1.0
    bandwidth = span * 0.15
    grid = [s_min + span * i / (n_grid - 1) for i in range(n_grid)]
    raw = []
    for x in grid:
        v = sum(math.exp(-0.5 * ((x - s) / bandwidth) ** 2) for s in samples)
        raw.append(v / (len(samples) * bandwidth * math.sqrt(2 * math.pi)))
    peak = max(raw) or 1.0
    return [v / peak for v in raw]
