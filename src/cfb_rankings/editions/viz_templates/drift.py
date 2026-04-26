"""Slope chart — ≤6 lines connecting two endpoints with named labels.

Data shape:
    {
        "title": "...",
        "left_label": "WEEK 1",
        "right_label": "WEEK 16",
        "y_min": 0.0, "y_max": 100.0,
        "lines": [
            {"name": "Texas", "left": 78, "right": 92, "color": "#bf5700",
             "annotation": "the December turn"},
            ...
        ],
        "caption": "...", "source": "..."
    }
"""
from __future__ import annotations

from typing import Any

from . import _common as c

WIDTH = 880
HEIGHT = 480
TOP_PAD = 72
BOTTOM_PAD = 96
LEFT_PAD = 140
RIGHT_PAD = 200


def render(data: dict[str, Any]) -> str:
    lines = (data.get("lines") or [])[:6]
    y_min = float(data.get("y_min", 0.0))
    y_max = float(data.get("y_max", 100.0))
    span = (y_max - y_min) or 1.0

    plot_top = TOP_PAD
    plot_bot = HEIGHT - BOTTOM_PAD
    plot_left = LEFT_PAD
    plot_right = WIDTH - RIGHT_PAD

    def y_for(v: float) -> float:
        return plot_bot - (plot_bot - plot_top) * (v - y_min) / span

    parts: list[str] = [c.svg_open(WIDTH, HEIGHT)]

    if data.get("title"):
        parts.append(c.text(plot_left, 28, data["title"], font_size=22, weight="600"))

    # Left/right axis labels.
    parts.append(c.text(plot_left, plot_top - 16, data.get("left_label", ""),
                        font_size=11, color=c.PALETTE_MUTED, weight="600"))
    parts.append(c.text(plot_right, plot_top - 16, data.get("right_label", ""),
                        font_size=11, color=c.PALETTE_MUTED, weight="600",
                        anchor="end"))
    # Vertical rules at endpoints.
    parts.append(c.line(plot_left, plot_top, plot_left, plot_bot,
                        color=c.PALETTE_RULE, width=0.75))
    parts.append(c.line(plot_right, plot_top, plot_right, plot_bot,
                        color=c.PALETTE_RULE, width=0.75))

    for line in lines:
        color = line.get("color") or c.PALETTE_INK
        x1, y1 = plot_left, y_for(float(line.get("left", y_min)))
        x2, y2 = plot_right, y_for(float(line.get("right", y_max)))
        parts.append(c.line(x1, y1, x2, y2, color=color, width=2.0))
        parts.append(c.circle(x1, y1, 5, fill=color))
        parts.append(c.circle(x2, y2, 5, fill=color))
        # Right-side label.
        name = line.get("name", "")
        parts.append(c.text(x2 + 12, y2 + 4, name, font_size=13, weight="600",
                            color=color))
        # Annotation: italic, centered between endpoints.
        ann = line.get("annotation")
        if ann:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2 - 8
            parts.append(c.text(mid_x, mid_y, ann, font_size=11, italic=True,
                                color=c.PALETTE_MUTED, anchor="middle"))

    # Caption + source.
    cap_y = HEIGHT - BOTTOM_PAD + 40
    if data.get("caption"):
        parts.append(c.text(plot_left, cap_y, data["caption"],
                            font_size=13, italic=True))
    if data.get("source"):
        parts.append(c.text(plot_right, cap_y + 22, data["source"],
                            font_size=10, color=c.PALETTE_MUTED,
                            anchor="end", weight="600"))

    parts.append(c.svg_close())
    return c.join(parts)
