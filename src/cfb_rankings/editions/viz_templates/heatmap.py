"""Calendar heatmap of conversation volume by program-week.

Data shape:
    {
        "title": "...",
        "rows": [
            {"label": "Alabama", "values": [0.1, 0.3, 0.8, ...]},
            ...
        ],
        "col_labels": ["W1","W2",...],
        "scale_max": 1.0,
        "caption": "...", "source": "..."
    }
"""
from __future__ import annotations

from typing import Any

from . import _common as c

CELL = 26
ROW_LABEL_W = 140
TOP_PAD = 72
BOTTOM_PAD = 88
LEFT_PAD = 24
RIGHT_PAD = 24


def render(data: dict[str, Any]) -> str:
    rows = data.get("rows") or []
    col_labels = data.get("col_labels") or []
    scale_max = float(data.get("scale_max", 1.0)) or 1.0
    n_cols = max((len(r.get("values") or []) for r in rows), default=0)
    if not col_labels:
        col_labels = [f"W{i+1}" for i in range(n_cols)]
    grid_left = LEFT_PAD + ROW_LABEL_W
    grid_top = TOP_PAD + 24
    width = grid_left + CELL * n_cols + RIGHT_PAD
    height = grid_top + CELL * len(rows) + BOTTOM_PAD

    parts: list[str] = [c.svg_open(width, height)]
    if data.get("title"):
        parts.append(c.text(LEFT_PAD, 28, data["title"], font_size=22, weight="600"))

    # Column labels.
    for i, lbl in enumerate(col_labels[:n_cols]):
        cx = grid_left + i * CELL + CELL / 2
        parts.append(c.text(cx, TOP_PAD + 12, lbl, font_size=10,
                            color=c.PALETTE_MUTED, anchor="middle", weight="600"))

    # Cells.
    for ri, row in enumerate(rows):
        ry = grid_top + ri * CELL
        parts.append(c.text(grid_left - 10, ry + CELL * 0.7,
                            row.get("label", ""), font_size=13,
                            anchor="end", weight="500"))
        for ci, v in enumerate(row.get("values") or []):
            t = max(0.0, min(1.0, float(v) / scale_max))
            # Two-stop ramp: cream → gold → navy.
            if t < 0.5:
                fill = _blend(c.PALETTE_CREAM, c.PALETTE_GOLD, t * 2)
            else:
                fill = _blend(c.PALETTE_GOLD, c.PALETTE_NAVY, (t - 0.5) * 2)
            parts.append(c.rect(grid_left + ci * CELL + 1, ry + 1,
                                CELL - 2, CELL - 2, fill=fill))

    # Caption + source.
    cap_y = grid_top + CELL * len(rows) + 36
    if data.get("caption"):
        parts.append(c.text(LEFT_PAD, cap_y, data["caption"],
                            font_size=13, italic=True))
    if data.get("source"):
        parts.append(c.text(width - RIGHT_PAD, cap_y + 22,
                            data["source"], font_size=10,
                            color=c.PALETTE_MUTED, anchor="end", weight="600"))

    parts.append(c.svg_close())
    return c.join(parts)


def _blend(hex_a: str, hex_b: str, t: float) -> str:
    a = _hex_to_rgb(hex_a)
    b = _hex_to_rgb(hex_b)
    rgb = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
