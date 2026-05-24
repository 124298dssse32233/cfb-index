"""Returning Production X-Ray — waterfall + peer-comparison bars.

Layout:
    - Title row + caption row
    - 2 stacked horizontal bars: Offense returning %, Defense returning %
    - Faint peer-average tick under each bar
    - QB + OL returning shown as annotation chips beneath
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


def render_returning_production_xray(
    query_result: dict[str, Any],
    spec_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})

    if not rows:
        return _empty_render("No returning-production snapshot for this season.")

    width = 600
    height = 280
    season = summary.get("season_year", "")
    sr_title = f"Returning Production X-Ray — {season} season"

    parts: list[str] = []
    parts.append(svg_open(width, height, title=sr_title))
    parts.append(rect(0, 0, width, height, fill=PALETTE_CREAM))

    parts.append(text(20, 28, "Returning Production X-Ray", font_size=16, weight="700"))
    parts.append(text(
        20, 48,
        f"{season} returning value vs FBS average",
        font_size=12, color=PALETTE_MUTED, italic=True,
    ))

    bar_x0 = 140
    bar_x1 = width - 80
    bar_w = bar_x1 - bar_x0

    league_avgs = {
        "Offense": summary.get("league_avg_offense", 0.0),
        "Defense": summary.get("league_avg_defense", 0.0),
    }

    # Determine max for scaling — give padding above league-best
    max_v = max([abs(r["value"]) for r in rows] + list(league_avgs.values()) + [1.0])
    max_v = max(max_v, 1.0)

    y = 90
    for r in rows:
        v = r["value"]
        # Frame
        parts.append(rect(bar_x0, y - 14, bar_w, 28, fill="#fff", opacity=0.7))
        # Filled portion
        fill_w = (v / max_v) * bar_w
        color = PALETTE_NAVY if r["label"] == "Defense" else PALETTE_GOLD
        parts.append(rect(bar_x0, y - 14, fill_w, 28, fill=color, opacity=0.92))
        # Label
        parts.append(text(20, y + 4, r["label"], font_size=13, weight="700"))
        # Value
        parts.append(text(
            bar_x1 + 8, y + 4,
            f"{v*100:.0f}%" if 0 <= v <= 1 else f"{v:.0f}",
            font_size=13, color=PALETTE_INK, family="ui-monospace,Menlo,monospace",
        ))
        # League average tick
        avg = league_avgs.get(r["label"], 0)
        if avg > 0:
            tick_x = bar_x0 + (avg / max_v) * bar_w
            parts.append(line(tick_x, y - 18, tick_x, y + 18, color=PALETTE_INK, width=1.0, dasharray="2,3"))
            parts.append(text(
                tick_x, y - 22,
                "FBS avg",
                font_size=10, color=PALETTE_MUTED, anchor="middle",
            ))
        y += 50

    # QB + OL chips
    chip_y = y + 16
    chips = []
    qb = summary.get("returning_qb", 0)
    ol = summary.get("returning_ol", 0)
    if qb is not None:
        chips.append(("QB return", f"{qb*100:.0f}%" if 0 <= qb <= 1 else f"{qb:.0f}"))
    if ol is not None:
        chips.append(("OL return", f"{ol*100:.0f}%" if 0 <= ol <= 1 else f"{ol:.0f}"))

    chip_x = 20
    for label, value in chips:
        chip_w = 110
        parts.append(rect(chip_x, chip_y, chip_w, 26, fill="#fff", opacity=0.8))
        parts.append(text(chip_x + 8, chip_y + 17, f"{label}: ", font_size=11, color=PALETTE_MUTED))
        parts.append(text(
            chip_x + chip_w - 8, chip_y + 17, value,
            font_size=12, weight="700", anchor="end",
            family="ui-monospace,Menlo,monospace",
        ))
        chip_x += chip_w + 10

    parts.append(svg_close())
    svg = join(parts)

    headline = _headline_for_returning(rows, summary)
    annotations: list[Annotation] = []
    if summary.get("returning_qb"):
        annotations.append(Annotation(
            target="qb_room",
            text=f"QB room returns {summary['returning_qb']*100:.0f}%",
            reason="passing-room continuity from prior season",
        ))

    alt_text = (
        f"Returning Production X-Ray for {season}: offense "
        f"{rows[0]['value']*100:.0f}% returning, defense "
        f"{rows[1]['value']*100:.0f}% returning, vs FBS averages."
        if len(rows) >= 2 else "Returning production snapshot."
    )

    return {
        "svg_html": svg,
        "headline_finding": headline,
        "annotations": annotations,
        "alt_text": alt_text,
    }


def _headline_for_returning(rows: list[dict], summary: dict) -> str:
    if len(rows) < 2:
        return "Returning production snapshot."
    off = rows[0]["value"]
    deff = rows[1]["value"]
    avg_off = summary.get("league_avg_offense", 0) or 0
    avg_def = summary.get("league_avg_defense", 0) or 0
    side = None
    diff = 0.0
    if avg_off and abs(off - avg_off) > abs(deff - avg_def):
        side = ("Offense", off, avg_off)
        diff = off - avg_off
    elif avg_def:
        side = ("Defense", deff, avg_def)
        diff = deff - avg_def
    if side and abs(diff) >= 0.08:
        direction = "above" if diff > 0 else "below"
        return f"{side[0]} returns {abs(diff)*100:.0f} points {direction} the FBS average."
    return "Returning production lands near the FBS average on both sides."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
