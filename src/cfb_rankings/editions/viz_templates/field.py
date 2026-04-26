"""Beeswarm-style scatter of all 134 programs by mood × velocity.

Data shape:
    {
        "title": "...",
        "x_label": "MOOD →",
        "y_label": "VELOCITY →",
        "points": [
            {"slug": "alabama", "x": 0.71, "y": 0.42,
             "highlight": false, "label": null},
            ...
        ],
        "caption": "...", "source": "..."
    }
"""
from __future__ import annotations

from typing import Any

from . import _common as c

WIDTH = 880
HEIGHT = 520
TOP_PAD = 80
BOTTOM_PAD = 88
LEFT_PAD = 80
RIGHT_PAD = 60


def render(data: dict[str, Any]) -> str:
    points = data.get("points") or []
    plot_top = TOP_PAD
    plot_bot = HEIGHT - BOTTOM_PAD
    plot_left = LEFT_PAD
    plot_right = WIDTH - RIGHT_PAD
    plot_w = plot_right - plot_left
    plot_h = plot_bot - plot_top

    parts: list[str] = [c.svg_open(WIDTH, HEIGHT)]

    if data.get("title"):
        parts.append(c.text(plot_left, 28, data["title"], font_size=22, weight="600"))

    # Axis frame.
    parts.append(c.line(plot_left, plot_bot, plot_right, plot_bot,
                        color=c.PALETTE_RULE, width=0.75))
    parts.append(c.line(plot_left, plot_top, plot_left, plot_bot,
                        color=c.PALETTE_RULE, width=0.75))
    # Axis labels.
    parts.append(c.text(plot_right, plot_bot + 28, data.get("x_label", ""),
                        font_size=11, color=c.PALETTE_MUTED, weight="600",
                        anchor="end"))
    parts.append(c.text(plot_left - 16, plot_top - 8, data.get("y_label", ""),
                        font_size=11, color=c.PALETTE_MUTED, weight="600"))

    # Points.
    for p in points:
        x = plot_left + plot_w * float(p.get("x", 0.5))
        y = plot_bot - plot_h * float(p.get("y", 0.5))
        if p.get("highlight"):
            parts.append(c.circle(x, y, 6, fill=c.PALETTE_GOLD,
                                  stroke=c.PALETTE_INK, stroke_width=1.0))
            label = p.get("label") or p.get("slug", "").replace("-", " ").title()
            parts.append(c.text(x + 9, y + 4, label,
                                font_size=11, weight="600"))
        else:
            parts.append(c.circle(x, y, 3.5, fill=c.PALETTE_INK,
                                  stroke=None, stroke_width=0))

    # Caption + source.
    cap_y = HEIGHT - BOTTOM_PAD + 56
    if data.get("caption"):
        parts.append(c.text(plot_left, cap_y, data["caption"],
                            font_size=13, italic=True))
    if data.get("source"):
        parts.append(c.text(plot_right, cap_y + 22, data["source"],
                            font_size=10, color=c.PALETTE_MUTED,
                            anchor="end", weight="600"))

    parts.append(c.svg_close())
    return c.join(parts)
