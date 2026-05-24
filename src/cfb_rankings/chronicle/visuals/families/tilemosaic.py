"""Roster Replacement Grid — tile mosaic showing portal flow per position group.

Each row = position; columns = (out, in). Tile width = count.
Color encodes net direction (gold = net gain, navy = net loss).
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import (
    svg_open,
    svg_close,
    text,
    line,
    rect,
    circle,
    join,
    PALETTE_GOLD,
    PALETTE_NAVY,
    PALETTE_INK,
    PALETTE_MUTED,
    PALETTE_CREAM,
)


def render_roster_replacement_grid(
    query_result: dict[str, Any],
    spec_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})

    if not rows:
        return _empty_render("No portal activity recorded for this season.")

    width = 600
    row_h = 30
    top_pad = 70
    bottom_pad = 36
    height = top_pad + bottom_pad + row_h * len(rows)

    parts: list[str] = []
    parts.append(svg_open(width, height))
    parts.append(rect(0, 0, width, height, fill=PALETTE_CREAM))

    parts.append(text(20, 28, "Roster Replacement Grid", font_size=16, weight="700"))
    season = summary.get("season_year", "")
    n_in = summary.get("total_incoming", 0)
    n_out = summary.get("total_outgoing", 0)
    parts.append(text(
        20, 48,
        f"{season} portal: {n_out} out · {n_in} in by position",
        font_size=12, color=PALETTE_MUTED, italic=True,
    ))

    # Column layout
    pos_x = 20
    mid_x = width / 2
    out_x_end = mid_x - 8
    in_x_start = mid_x + 8
    chart_right = width - 24

    # Determine tile-width unit
    max_count = max(
        [r["incoming_n"] for r in rows] + [r["outgoing_n"] for r in rows] + [1]
    )
    out_width = mid_x - 80  # space from pos label to mid line
    in_width = chart_right - in_x_start
    unit_w = min(out_width, in_width) / max(1, max_count)

    # Header row
    parts.append(text(mid_x - 12, top_pad - 12, "OUT", font_size=10, color=PALETTE_MUTED, anchor="end"))
    parts.append(text(mid_x + 12, top_pad - 12, "IN", font_size=10, color=PALETTE_MUTED, anchor="start"))
    parts.append(line(mid_x, top_pad - 8, mid_x, top_pad + len(rows) * row_h + 4, color=PALETTE_INK, width=1.0))

    for i, r in enumerate(rows):
        y = top_pad + i * row_h
        # Position label
        parts.append(text(pos_x, y + 18, r["position"], font_size=12, weight="700"))
        # OUT tile
        out_w = r["outgoing_n"] * unit_w
        if out_w > 0:
            parts.append(rect(mid_x - out_w, y + 6, out_w, row_h - 12, fill=PALETTE_NAVY, opacity=0.82))
            parts.append(text(
                mid_x - 6, y + 18, str(r["outgoing_n"]),
                font_size=11, color=PALETTE_INK, anchor="end", weight="700",
                family="ui-monospace,Menlo,monospace",
            ))
        # IN tile
        in_w = r["incoming_n"] * unit_w
        if in_w > 0:
            parts.append(rect(mid_x, y + 6, in_w, row_h - 12, fill=PALETTE_GOLD, opacity=0.82))
            parts.append(text(
                mid_x + 6, y + 18, str(r["incoming_n"]),
                font_size=11, color=PALETTE_INK, weight="700",
                family="ui-monospace,Menlo,monospace",
            ))
        # Net delta on right
        net = r["net_n"]
        sign = "+" if net > 0 else ""
        net_color = PALETTE_GOLD if net > 0 else (PALETTE_NAVY if net < 0 else PALETTE_MUTED)
        parts.append(text(
            chart_right, y + 18, f"net {sign}{net}",
            font_size=11, color=net_color, anchor="end",
            family="ui-monospace,Menlo,monospace",
        ))

    # Footer
    parts.append(text(
        20, height - 12,
        f"Net movement: {summary.get('net_movement', 0):+d}",
        font_size=11, color=PALETTE_MUTED, italic=True,
    ))

    parts.append(svg_close())
    svg = join(parts)

    headline = _headline_for_grid(rows, summary)
    annotations: list[Annotation] = []
    # Highlight largest net swing position
    if rows:
        biggest = max(rows, key=lambda r: abs(r["net_n"]))
        if abs(biggest["net_n"]) >= 2:
            direction = "net gain" if biggest["net_n"] > 0 else "net loss"
            annotations.append(Annotation(
                target=biggest["position"],
                text=f"{biggest['position']}: {direction} of {abs(biggest['net_n'])}",
                reason="largest net positional swing in portal flow",
            ))

    alt_text = (
        f"Roster Replacement Grid for {season}: "
        f"{n_out} players out and {n_in} in across {len(rows)} positions."
    )

    return {
        "svg_html": svg,
        "headline_finding": headline,
        "annotations": annotations,
        "alt_text": alt_text,
    }


def _headline_for_grid(rows: list[dict], summary: dict) -> str:
    net = summary.get("net_movement", 0)
    n_in = summary.get("total_incoming", 0)
    n_out = summary.get("total_outgoing", 0)
    if n_in == 0 and n_out == 0:
        return "No portal activity recorded for this season."
    biggest = max(rows, key=lambda r: abs(r["net_n"])) if rows else None
    if biggest and abs(biggest["net_n"]) >= 3:
        direction = "added" if biggest["net_n"] > 0 else "lost"
        return (
            f"The portal {direction} {abs(biggest['net_n'])} net "
            f"{biggest['position']}s — the season's biggest positional swing."
        )
    if net > 0:
        return f"Portal nets {net:+d} bodies across {len(rows)} positions."
    if net < 0:
        return f"Portal sheds {abs(net)} net bodies across {len(rows)} positions."
    return f"Portal in/out balance flat at {n_in}/{n_out}."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
