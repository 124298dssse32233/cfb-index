"""Bump chart of top-N programs by ranking change across two timepoints.

Data shape:
    {
        "title": "...",
        "left_label": "PRE-DRAFT", "right_label": "POST-DRAFT",
        "rows": [
            {"name": "Texas", "left_rank": 1, "right_rank": 3, "color": "#bf5700"},
            ...
        ],
        "caption": "...", "source": "..."
    }
"""
from __future__ import annotations

from typing import Any

from . import _common as c

WIDTH = 880
ROW_H = 36
TOP_PAD = 80
BOTTOM_PAD = 96
LEFT_PAD = 80
RIGHT_PAD = 80
COL_W = 540


def render(data: dict[str, Any]) -> str:
    rows = data.get("rows") or []
    n = max(
        max((int(r.get("left_rank", 1)) for r in rows), default=1),
        max((int(r.get("right_rank", 1)) for r in rows), default=1),
    )
    height = TOP_PAD + n * ROW_H + BOTTOM_PAD
    left_col = LEFT_PAD
    right_col = LEFT_PAD + COL_W

    parts: list[str] = [c.svg_open(WIDTH, height)]
    if data.get("title"):
        parts.append(c.text(left_col, 28, data["title"],
                            font_size=22, weight="600"))

    parts.append(c.text(left_col, TOP_PAD - 16, data.get("left_label", ""),
                        font_size=11, color=c.PALETTE_MUTED, weight="600"))
    parts.append(c.text(right_col, TOP_PAD - 16, data.get("right_label", ""),
                        font_size=11, color=c.PALETTE_MUTED, weight="600"))

    # Rank columns.
    for r in range(1, n + 1):
        y = TOP_PAD + (r - 1) * ROW_H + ROW_H / 2 + 4
        parts.append(c.text(left_col - 10, y, f"#{r}", font_size=11,
                            color=c.PALETTE_MUTED, anchor="end", weight="600"))

    for row in rows:
        color = row.get("color") or c.PALETTE_INK
        l_rank = int(row.get("left_rank", 1))
        r_rank = int(row.get("right_rank", 1))
        ly = TOP_PAD + (l_rank - 1) * ROW_H + ROW_H / 2
        ry = TOP_PAD + (r_rank - 1) * ROW_H + ROW_H / 2
        # Bezier curve between endpoints.
        cx1 = left_col + COL_W * 0.4
        cx2 = left_col + COL_W * 0.6
        d = (
            f"M {left_col:.1f},{ly:.1f} "
            f"C {cx1:.1f},{ly:.1f} {cx2:.1f},{ry:.1f} {right_col:.1f},{ry:.1f}"
        )
        parts.append(c.path(d, stroke=color, stroke_width=2.0))
        parts.append(c.circle(left_col, ly, 5, fill=color))
        parts.append(c.circle(right_col, ry, 5, fill=color))
        parts.append(c.text(right_col + 12, ry + 4, row.get("name", ""),
                            font_size=13, weight="600", color=color))

    cap_y = TOP_PAD + n * ROW_H + 36
    if data.get("caption"):
        parts.append(c.text(left_col, cap_y, data["caption"],
                            font_size=13, italic=True))
    if data.get("source"):
        parts.append(c.text(WIDTH - RIGHT_PAD, cap_y + 22, data["source"],
                            font_size=10, color=c.PALETTE_MUTED,
                            anchor="end", weight="600"))

    parts.append(c.svg_close())
    return c.join(parts)
