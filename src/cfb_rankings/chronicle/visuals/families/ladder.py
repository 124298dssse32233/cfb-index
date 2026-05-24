"""Statement Win Ladder — dot/range plot showing which wins moved the resume most.

CFB Index visual design:
    - X axis: total_delta (power + resume delta)
    - Y axis: ordered list of games (top = biggest impact)
    - Each row: result label (W 27-10), opponent name, value bar, delta value
    - Highlighted dot = the one win that moved the season the most
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


def render_statement_win_ladder(
    query_result: dict[str, Any],
    spec_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})

    if not rows:
        return _empty_render("No completed games yet.")

    # Layout — mobile-first 360px native, scales up.
    width = 600
    row_h = 44
    top_pad = 64
    bottom_pad = 36
    height = top_pad + bottom_pad + (row_h * len(rows))

    parts: list[str] = []
    parts.append(svg_open(width, height))
    parts.append(rect(0, 0, width, height, fill=PALETTE_CREAM))

    # Title + caption row
    parts.append(text(20, 28, "Statement Win Ladder", font_size=16, weight="700"))
    parts.append(text(
        20, 48,
        f"Top {len(rows)} results by combined power + resume delta",
        font_size=12, color=PALETTE_MUTED, italic=True,
    ))

    # Axis range
    deltas = [r["total_delta"] for r in rows]
    max_abs = max(abs(d) for d in deltas) if deltas else 1.0
    if max_abs == 0:
        max_abs = 1.0

    chart_x0 = 200
    chart_x1 = width - 80
    chart_w = chart_x1 - chart_x0
    zero_x = chart_x0 + chart_w * (0 - (-max_abs)) / (2 * max_abs)

    # Zero line
    parts.append(line(
        zero_x, top_pad - 8, zero_x, height - bottom_pad + 4,
        color=PALETTE_INK, width=1.0, dasharray="2,3",
    ))

    # Each row
    for i, r in enumerate(rows):
        y = top_pad + row_h * i + row_h / 2
        d = r["total_delta"]
        bar_w = (d / max_abs) * (chart_w / 2)
        bar_x = zero_x if d >= 0 else zero_x + bar_w
        bar_w_abs = abs(bar_w)

        bar_color = PALETTE_GOLD if r.get("is_top_result") or r["is_win"] else PALETTE_MUTED
        # Bar
        parts.append(rect(bar_x, y - 8, bar_w_abs, 16, fill=bar_color, opacity=0.85))
        # Dot at tip
        parts.append(circle(
            bar_x + bar_w_abs if d >= 0 else bar_x,
            y,
            5 if r.get("is_top_result") else 3.5,
            fill=PALETTE_INK if r.get("is_top_result") else bar_color,
        ))

        # Result + opponent label (left rail)
        label_text = f"{r['result_text']}  vs {html.escape(r['opponent_name'])[:18]}"
        if r.get("is_top_result"):
            parts.append(text(20, y + 5, label_text, font_size=13, weight="700"))
        else:
            parts.append(text(20, y + 5, label_text, font_size=12, color=PALETTE_INK))

        # Delta value (right rail)
        sign = "+" if d >= 0 else ""
        parts.append(text(
            width - 12, y + 5,
            f"{sign}{d:.2f}",
            font_size=12, color=PALETTE_INK, family="ui-monospace,Menlo,monospace",
            anchor="end",
        ))

    # Caption
    delta_spread = summary.get("delta_spread", 0)
    if delta_spread > 0 and len(rows) > 1:
        top_d = rows[0]["total_delta"]
        rest_avg = sum(r["total_delta"] for r in rows[1:]) / max(1, len(rows) - 1)
        ratio = top_d / max(0.001, rest_avg) if rest_avg > 0 else 0
        if ratio >= 1.4:
            parts.append(text(
                20, height - 10,
                f"Top result moved the resume {ratio:.1f}× the rest combined.",
                font_size=11, color=PALETTE_MUTED, italic=True,
            ))

    parts.append(svg_close())
    svg = join(parts)

    # Headline finding generation (deterministic — no LLM)
    headline = _headline_for_ladder(rows, summary)

    # Annotations
    annotations: list[Annotation] = []
    if rows and rows[0].get("is_top_result"):
        annotations.append(Annotation(
            target=rows[0]["opponent_slug"] or rows[0]["opponent_name"],
            text=f"biggest mover ({rows[0]['result_text']})",
            reason="top combined power+resume delta on the schedule",
        ))

    alt_text = (
        f"Statement Win Ladder showing the top {len(rows)} games "
        f"by power+resume delta. Largest mover: "
        f"{rows[0]['result_text']} vs {rows[0]['opponent_name']} ({rows[0]['total_delta']:+.2f})."
    )

    return {
        "svg_html": svg,
        "headline_finding": headline,
        "annotations": annotations,
        "alt_text": alt_text,
    }


def _headline_for_ladder(rows: list[dict], summary: dict) -> str:
    if not rows:
        return "No completed games on the schedule yet."
    top = rows[0]
    if len(rows) == 1:
        return f"{top['result_text']} vs {top['opponent_name']} is the season so far."
    top_d = top["total_delta"]
    rest_avg = sum(r["total_delta"] for r in rows[1:]) / (len(rows) - 1)
    if rest_avg > 0 and top_d / max(0.001, rest_avg) >= 1.6:
        return (
            f"{top['result_text']} vs {top['opponent_name']} moved the resume "
            f"more than the next {len(rows)-1} wins combined."
        )
    return (
        f"{top['result_text']} vs {top['opponent_name']} leads the season's "
        f"top {len(rows)} results by combined power and resume delta."
    )


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
