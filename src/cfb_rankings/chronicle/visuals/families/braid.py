"""Heisman Race Braid — bump chart layered with finalist-probability sparks.

Each line traces a player's rank from week 1 -> snapshot week. The top player
gets the gold accent; the rest are navy. A small probability strip on the right
shows current finalist probability.
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
    path,
    join,
    PALETTE_GOLD,
    PALETTE_NAVY,
    PALETTE_INK,
    PALETTE_MUTED,
    PALETTE_CREAM,
)


def render_heisman_race_braid(
    query_result: dict[str, Any],
    spec_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})

    if not rows:
        return _empty_render("No Heisman rankings for this snapshot.")

    width = 720
    height = 380
    snapshot_week = summary.get("snapshot_week", "?")
    season = summary.get("season_year", "")
    sr_title = (
        f"Heisman Race Braid — {season} season through week {snapshot_week}; "
        f"top {len(rows)} contenders"
    )

    parts: list[str] = []
    parts.append(svg_open(width, height, title=sr_title))
    parts.append(rect(0, 0, width, height, fill=PALETTE_CREAM))
    parts.append(text(20, 28, "Heisman Race Braid", font_size=16, weight="700"))
    parts.append(text(
        20, 48,
        f"{season} weekly rank trajectory · top {len(rows)} thru week {snapshot_week}",
        font_size=12, color=PALETTE_MUTED, italic=True,
    ))

    # Compute week range
    weeks_seen = {h["week"] for r in rows for h in r["history"] if h["week"] is not None}
    if not weeks_seen:
        return _empty_render("No week history available.")
    w_min = min(weeks_seen)
    w_max = max(weeks_seen)

    chart_x0 = 24
    chart_x1 = width - 200
    chart_y0 = 90
    chart_y1 = height - 60
    chart_w = chart_x1 - chart_x0
    chart_h = chart_y1 - chart_y0

    n_ranks = len(rows)  # we show top-N ranks on the y-axis

    def x_of(week: int) -> float:
        if w_max == w_min:
            return chart_x0 + chart_w / 2
        return chart_x0 + chart_w * (week - w_min) / (w_max - w_min)

    def y_of(rank: int) -> float:
        # rank 1 at top, rank n_ranks at bottom
        if n_ranks <= 1:
            return chart_y0 + chart_h / 2
        return chart_y0 + chart_h * (rank - 1) / max(1, n_ranks - 1)

    # Grid: horizontal rank guides
    for i in range(1, n_ranks + 1):
        y = y_of(i)
        parts.append(line(chart_x0, y, chart_x1, y, color="#dcd6c6", width=0.5))
        parts.append(text(chart_x0 - 4, y + 4, f"#{i}", font_size=10, color=PALETTE_MUTED, anchor="end"))

    # Each player line
    for idx, r in enumerate(rows):
        is_anchor = idx == 0
        color = PALETTE_GOLD if is_anchor else PALETTE_NAVY
        weight = 2.2 if is_anchor else 1.2
        opacity_str = "" if is_anchor else "stroke-opacity=\"0.55\""

        hist = sorted([h for h in r["history"] if h["rank"] is not None], key=lambda h: h["week"])
        if not hist:
            continue
        d_parts = []
        for j, h in enumerate(hist):
            cmd = "M" if j == 0 else "L"
            d_parts.append(f"{cmd}{x_of(h['week']):.1f},{y_of(h['rank']):.1f}")
        d = " ".join(d_parts)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{weight}" '
            f'stroke-linejoin="round" {opacity_str}/>'
        )

        # Final dot
        last = hist[-1]
        parts.append(circle(x_of(last["week"]), y_of(last["rank"]), 4 if is_anchor else 3, fill=color))

        # Anchor name label
        if is_anchor:
            parts.append(text(
                x_of(last["week"]) + 8, y_of(last["rank"]) + 4,
                r["player_name"], font_size=12, weight="700", color=PALETTE_INK,
            ))

    # Right-side probability strip
    strip_x = chart_x1 + 16
    strip_y = chart_y0
    parts.append(text(strip_x, strip_y - 8, "finalist %", font_size=10, color=PALETTE_MUTED))
    for idx, r in enumerate(rows[:8]):
        hist = sorted(r["history"], key=lambda h: h["week"]) if r["history"] else []
        if not hist:
            continue
        latest_p = hist[-1].get("finalist_probability", 0) or 0
        y = strip_y + idx * 30
        parts.append(rect(strip_x, y, 80, 22, fill="#fff", opacity=0.7))
        # `text()` already escapes — pass raw, truncated.
        parts.append(text(
            strip_x + 6, y + 14,
            (r["player_name"] or "")[:14],
            font_size=10, color=PALETTE_INK,
        ))
        parts.append(text(
            strip_x + 76, y + 14,
            f"{latest_p*100:.0f}%" if latest_p else "—",
            font_size=11, weight="700", anchor="end",
            family="ui-monospace,Menlo,monospace",
        ))

    # Bottom axis — week numbers
    for w in sorted(weeks_seen):
        x = x_of(w)
        if w == w_min or w == w_max or w % 4 == 0:
            parts.append(text(x, chart_y1 + 16, f"W{w}", font_size=10, color=PALETTE_MUTED, anchor="middle"))

    parts.append(svg_close())
    svg = join(parts)

    headline = _headline_for_braid(rows, summary)
    annotations: list[Annotation] = []
    if rows:
        annotations.append(Annotation(
            target=rows[0].get("team_slug") or rows[0]["player_name"],
            text=f"#{rows[0].get('current_rank', '?')} at week {snapshot_week}",
            reason="anchor of the current Heisman race",
        ))

    alt_text = (
        f"Heisman Race Braid for {season} season through week {snapshot_week}: "
        f"top {len(rows)} contenders traced week by week, "
        f"anchor {rows[0]['player_name']} at rank #{rows[0].get('current_rank','?')}."
    )

    return {
        "svg_html": svg,
        "headline_finding": headline,
        "annotations": annotations,
        "alt_text": alt_text,
    }


def _headline_for_braid(rows: list[dict], summary: dict) -> str:
    if not rows:
        return "Heisman race snapshot."
    leader = rows[0]
    leader_hist = sorted(leader["history"], key=lambda h: h["week"]) if leader["history"] else []
    if len(leader_hist) >= 2:
        start_rank = leader_hist[0]["rank"]
        end_rank = leader_hist[-1]["rank"]
        if start_rank and end_rank and start_rank > end_rank + 3:
            return f"{leader['player_name']} climbed from #{start_rank} to #{end_rank} in the Heisman race."
        if start_rank and end_rank and end_rank > start_rank + 3:
            return f"{leader['player_name']} held the lead despite a {end_rank - start_rank}-spot slide."
    snap = summary.get("snapshot_week", "?")
    return f"{leader['player_name']} leads the Heisman race through week {snap}."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
