"""Sankey diagram of attention/topic movement week-over-week.

Data shape:
    {
        "title": "...",
        "left_label": "WEEK N", "right_label": "WEEK N+1",
        "left_nodes":  [{"label": "Portal", "value": 32, "color": "#c9a24a"}, ...],
        "right_nodes": [{"label": "Spring",  "value": 41, "color": "#1f2c4d"}, ...],
        "links": [{"from": 0, "to": 0, "value": 18}, ...],
        "caption": "...", "source": "..."
    }
"""
from __future__ import annotations

from typing import Any

from . import _common as c

WIDTH = 880
HEIGHT = 520
TOP_PAD = 80
BOTTOM_PAD = 80
NODE_W = 12
GUTTER = 60


def render(data: dict[str, Any]) -> str:
    left_nodes = data.get("left_nodes") or []
    right_nodes = data.get("right_nodes") or []
    links = data.get("links") or []
    plot_top = TOP_PAD
    plot_bot = HEIGHT - BOTTOM_PAD
    plot_h = plot_bot - plot_top
    left_x = GUTTER
    right_x = WIDTH - GUTTER - NODE_W

    parts: list[str] = [c.svg_open(WIDTH, HEIGHT)]
    if data.get("title"):
        parts.append(c.text(left_x, 28, data["title"], font_size=22, weight="600"))

    # Compute node positions (stacked, proportional to value, with 4px gaps).
    def stack(nodes: list[dict[str, Any]]) -> list[tuple[float, float]]:
        total = sum(float(n.get("value", 0)) for n in nodes) or 1.0
        gap_total = max(0, len(nodes) - 1) * 4
        usable = plot_h - gap_total
        out: list[tuple[float, float]] = []
        y = plot_top
        for n in nodes:
            h = usable * float(n.get("value", 0)) / total
            out.append((y, h))
            y += h + 4
        return out

    left_pos = stack(left_nodes)
    right_pos = stack(right_nodes)

    # Labels.
    parts.append(c.text(left_x, plot_top - 16, data.get("left_label", ""),
                        font_size=11, color=c.PALETTE_MUTED, weight="600"))
    parts.append(c.text(right_x + NODE_W, plot_top - 16,
                        data.get("right_label", ""),
                        font_size=11, color=c.PALETTE_MUTED, weight="600",
                        anchor="end"))

    # Links — drawn first so nodes sit on top.
    # For each link, allocate a band on each node proportional to value.
    left_consumed = [0.0] * len(left_nodes)
    right_consumed = [0.0] * len(right_nodes)
    for link in links:
        i = int(link.get("from", 0))
        j = int(link.get("to", 0))
        v = float(link.get("value", 0))
        if not (0 <= i < len(left_pos) and 0 <= j < len(right_pos)):
            continue
        ly, lh = left_pos[i]
        ry, rh = right_pos[j]
        l_total = float(left_nodes[i].get("value", 1)) or 1
        r_total = float(right_nodes[j].get("value", 1)) or 1
        l_h = lh * v / l_total
        r_h = rh * v / r_total
        ly0 = ly + left_consumed[i]
        ly1 = ly0 + l_h
        ry0 = ry + right_consumed[j]
        ry1 = ry0 + r_h
        left_consumed[i] += l_h
        right_consumed[j] += r_h
        # Cubic bezier band.
        cx1 = left_x + NODE_W + (right_x - left_x - NODE_W) * 0.45
        cx2 = left_x + NODE_W + (right_x - left_x - NODE_W) * 0.55
        d = (
            f"M {left_x + NODE_W:.1f},{ly0:.1f} "
            f"C {cx1:.1f},{ly0:.1f} {cx2:.1f},{ry0:.1f} {right_x:.1f},{ry0:.1f} "
            f"L {right_x:.1f},{ry1:.1f} "
            f"C {cx2:.1f},{ry1:.1f} {cx1:.1f},{ly1:.1f} {left_x + NODE_W:.1f},{ly1:.1f} Z"
        )
        parts.append(c.path(d, stroke=c.PALETTE_RULE, stroke_width=0.5,
                            fill=c.PALETTE_GOLD))
        parts[-1] = parts[-1].replace('fill="#c9a24a"',
                                       'fill="#c9a24a" fill-opacity="0.35"')

    # Nodes.
    for n, (y, h) in zip(left_nodes, left_pos):
        parts.append(c.rect(left_x, y, NODE_W, h,
                            fill=n.get("color") or c.PALETTE_NAVY))
        parts.append(c.text(left_x - 8, y + h / 2 + 4,
                            n.get("label", ""), font_size=12,
                            anchor="end", weight="500"))
    for n, (y, h) in zip(right_nodes, right_pos):
        parts.append(c.rect(right_x, y, NODE_W, h,
                            fill=n.get("color") or c.PALETTE_GOLD))
        parts.append(c.text(right_x + NODE_W + 8, y + h / 2 + 4,
                            n.get("label", ""), font_size=12, weight="500"))

    cap_y = HEIGHT - BOTTOM_PAD + 36
    if data.get("caption"):
        parts.append(c.text(left_x, cap_y, data["caption"],
                            font_size=13, italic=True))
    if data.get("source"):
        parts.append(c.text(right_x + NODE_W, cap_y + 22, data["source"],
                            font_size=10, color=c.PALETTE_MUTED,
                            anchor="end", weight="600"))

    parts.append(c.svg_close())
    return c.join(parts)
