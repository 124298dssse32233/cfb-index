"""Dumbbell chart for the cover viz.

Data shape:
    {
        "title": "...",            # serif headline placed above
        "x_label_left": "BLOWN OUT",
        "x_label_right": "DOMINANT",
        "rows": [
            {"label": "Big Ten", "left": 0.32, "right": 0.71, "annotation": "..."},
            ...
        ],
        "x_min": 0.0,              # optional, default 0
        "x_max": 1.0,              # optional, default 1
        "caption": "italic editorial caption",
        "source": "source attribution"
    }
"""
from __future__ import annotations

from typing import Any

from . import _common as c

WIDTH = 880
ROW_HEIGHT = 56
LEFT_GUTTER = 180
RIGHT_GUTTER = 60
TOP_PAD = 72
BOTTOM_PAD = 88


def render(data: dict[str, Any]) -> str:
    rows = data.get("rows") or []
    x_min = float(data.get("x_min", 0.0))
    x_max = float(data.get("x_max", 1.0))
    span = x_max - x_min if x_max > x_min else 1.0
    chart_height = max(ROW_HEIGHT * len(rows), ROW_HEIGHT)
    height = TOP_PAD + chart_height + BOTTOM_PAD
    plot_left = LEFT_GUTTER
    plot_right = WIDTH - RIGHT_GUTTER
    plot_w = plot_right - plot_left

    parts: list[str] = [c.svg_open(WIDTH, height)]

    # Title
    title = data.get("title")
    if title:
        parts.append(c.text(plot_left, 28, title, font_size=22, weight="600"))

    # Axis labels (top of plot area).
    label_y = TOP_PAD - 16
    parts.append(
        c.text(plot_left, label_y, data.get("x_label_left", ""),
               font_size=11, color=c.PALETTE_MUTED, weight="600")
    )
    parts.append(
        c.text(plot_right, label_y, data.get("x_label_right", ""),
               font_size=11, color=c.PALETTE_MUTED, weight="600", anchor="end")
    )

    # Hairline at top of plot area.
    parts.append(c.line(plot_left, TOP_PAD, plot_right, TOP_PAD,
                        color=c.PALETTE_RULE, width=0.75))

    # Rows.
    for i, row in enumerate(rows):
        cy = TOP_PAD + i * ROW_HEIGHT + ROW_HEIGHT / 2
        label = row.get("label", "")
        left_v = float(row.get("left", x_min))
        right_v = float(row.get("right", x_max))
        x_left = plot_left + plot_w * (left_v - x_min) / span
        x_right = plot_left + plot_w * (right_v - x_min) / span
        # Row label.
        parts.append(c.text(plot_left - 12, cy + 4, label,
                            font_size=14, anchor="end", weight="500"))
        # Connecting bar.
        parts.append(c.line(x_left, cy, x_right, cy,
                            color=c.PALETTE_INK, width=2.0))
        # Endpoints — left = navy, right = gold.
        parts.append(c.circle(x_left, cy, 7, fill=c.PALETTE_NAVY))
        parts.append(c.circle(x_right, cy, 7, fill=c.PALETTE_GOLD))
        # Annotation if provided.
        ann = row.get("annotation")
        if ann:
            ann_x = (x_left + x_right) / 2
            parts.append(c.text(ann_x, cy - 14, ann,
                                font_size=12, italic=True,
                                color=c.PALETTE_MUTED, anchor="middle"))
        # Hairline below row.
        parts.append(c.line(plot_left, cy + ROW_HEIGHT / 2,
                            plot_right, cy + ROW_HEIGHT / 2,
                            color=c.PALETTE_RULE, width=0.5,
                            dasharray="2,3"))

    # Caption + source row.
    caption = data.get("caption", "")
    source = data.get("source", "")
    cap_y = TOP_PAD + chart_height + 36
    if caption:
        parts.append(c.text(plot_left, cap_y, caption,
                            font_size=13, italic=True,
                            color=c.PALETTE_INK))
    if source:
        parts.append(c.text(plot_right, cap_y + 22, source,
                            font_size=10, color=c.PALETTE_MUTED,
                            anchor="end", weight="600"))

    parts.append(c.svg_close())
    return c.join(parts)
