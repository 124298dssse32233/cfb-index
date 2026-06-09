"""Annotated scatter / quadrant family.

Two visuals share this geometry:
    - CFP Bubble Wall: x=resume percentile, y=power percentile
    - Talent Yield Curve: x=talent rank percentile, y=draft yield rate

Common renderer takes a typed query result with rows of {label, x, y, slug,
highlight, color_band} and produces:
    - 2D scatter
    - median crosshair (P50 x P50)
    - highlighted entity callout
    - peer labels (max 6)
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


def _render_scatter_core(
    rows: list[dict[str, Any]],
    *,
    title: str,
    subtitle: str,
    x_label: str,
    y_label: str,
    highlight_slug: str | None,
    sr_title: str,
    headline_finding: str,
    annotations: list[Annotation],
) -> dict[str, Any]:
    if not rows:
        return _empty_render("No data available.")

    width = 720
    height = 500
    pad_l = 60
    pad_r = 24
    pad_t = 80
    pad_b = 56
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b

    parts: list[str] = []
    parts.append(svg_open(width, height, title=sr_title))
    parts.append(rect(0, 0, width, height, fill=PALETTE_CREAM))

    parts.append(text(pad_l, 30, title, font_size=16, weight="700"))
    parts.append(text(pad_l, 50, subtitle, font_size=12, color=PALETTE_MUTED, italic=True))

    # Axis lines
    parts.append(line(pad_l, pad_t + chart_h, pad_l + chart_w, pad_t + chart_h, color=PALETTE_INK, width=1.0))
    parts.append(line(pad_l, pad_t, pad_l, pad_t + chart_h, color=PALETTE_INK, width=1.0))

    # Median crosshair at 0.5 x 0.5 (proportional space)
    mx = pad_l + chart_w * 0.5
    my = pad_t + chart_h * 0.5
    parts.append(line(mx, pad_t, mx, pad_t + chart_h, color=PALETTE_MUTED, width=0.5, dasharray="3,3"))
    parts.append(line(pad_l, my, pad_l + chart_w, my, color=PALETTE_MUTED, width=0.5, dasharray="3,3"))

    # Axis labels
    parts.append(text(pad_l + chart_w / 2, height - 18, x_label, font_size=11, color=PALETTE_INK, anchor="middle"))
    # Y label rotated
    parts.append(
        f'<text x="{18}" y="{pad_t + chart_h / 2}" font-family="Georgia,serif" font-size="11" '
        f'fill="{PALETTE_INK}" text-anchor="middle" '
        f'transform="rotate(-90 18 {pad_t + chart_h / 2})">{html.escape(y_label)}</text>'
    )

    # Axis tick text
    for f, t in [(0.0, "0"), (0.25, "25"), (0.5, "50"), (0.75, "75"), (1.0, "100")]:
        # X ticks
        x = pad_l + chart_w * f
        parts.append(line(x, pad_t + chart_h, x, pad_t + chart_h + 4, color=PALETTE_INK, width=0.5))
        parts.append(text(x, pad_t + chart_h + 18, t, font_size=10, color=PALETTE_MUTED, anchor="middle"))
        # Y ticks (inverted: 1.0 at top)
        y = pad_t + chart_h * (1.0 - f)
        parts.append(line(pad_l - 4, y, pad_l, y, color=PALETTE_INK, width=0.5))
        parts.append(text(pad_l - 8, y + 4, t, font_size=10, color=PALETTE_MUTED, anchor="end"))

    # Points
    for r in rows:
        x_v = max(0.0, min(1.0, float(r.get("x", 0.5))))
        y_v = max(0.0, min(1.0, float(r.get("y", 0.5))))
        cx = pad_l + chart_w * x_v
        cy = pad_t + chart_h * (1.0 - y_v)

        is_highlight = (highlight_slug is not None) and (r.get("slug") == highlight_slug)
        is_peer = bool(r.get("peer_label"))
        radius = 8 if is_highlight else (5 if is_peer else 3)
        color = PALETTE_GOLD if is_highlight else (PALETTE_NAVY if is_peer else PALETTE_MUTED)
        opacity = 1.0 if is_highlight else (0.85 if is_peer else 0.55)
        stroke = PALETTE_INK if is_highlight else None
        # Render dot
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius}" fill="{color}" opacity="{opacity:.2f}"'
            + (f' stroke="{stroke}" stroke-width="1.2"' if stroke else "")
            + '/>'
        )
        # Label
        label = r.get("label") or ""
        if is_highlight:
            parts.append(text(cx + radius + 4, cy + 4, label, font_size=13, weight="700"))
        elif is_peer and label:
            parts.append(text(cx + radius + 3, cy + 3, label[:14], font_size=10, color=PALETTE_NAVY))

    # Quadrant legend (corner labels)
    parts.append(text(pad_l + chart_w - 6, pad_t + 14, "elite", font_size=10, color=PALETTE_MUTED, anchor="end"))
    parts.append(text(pad_l + 6, pad_t + chart_h - 6, "below avg", font_size=10, color=PALETTE_MUTED))

    parts.append(svg_close())
    svg = join(parts)

    alt_text = sr_title + " — " + headline_finding
    return {
        "svg_html": svg,
        "headline_finding": headline_finding,
        "annotations": annotations,
        "alt_text": alt_text,
    }


# ---------------------------------------------------------------------------
# CFP Bubble Wall
# ---------------------------------------------------------------------------


def render_cfp_bubble_wall(
    query_result: dict[str, Any],
    spec_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    highlight_slug = summary.get("anchor_slug")
    season = summary.get("season_year", "")
    week = summary.get("snapshot_week", "?")

    if not rows:
        return _empty_render("No CFP-window rankings for this snapshot.")

    sr_title = (
        f"CFP Bubble Wall — {season} week {week}: resume rating vs power rating "
        f"percentiles for the at-large field"
    )
    headline = _headline_for_cfp_wall(rows, summary, highlight_slug)

    annotations: list[Annotation] = []
    if highlight_slug:
        annotations.append(Annotation(
            target=highlight_slug,
            text=_anchor_position_label(rows, highlight_slug),
            reason="anchor team CFP position",
        ))

    return _render_scatter_core(
        rows,
        title="CFP Bubble Wall",
        subtitle=f"{season} week {week}: at-large field by resume + power percentile",
        x_label="Resume percentile (committee case)",
        y_label="Power percentile (model)",
        highlight_slug=highlight_slug,
        sr_title=sr_title,
        headline_finding=headline,
        annotations=annotations,
    )


def _headline_for_cfp_wall(rows: list[dict], summary: dict, anchor: str | None) -> str:
    if not anchor:
        return "The at-large CFP field plotted by resume against model strength."
    anchor_row = next((r for r in rows if r.get("slug") == anchor), None)
    if not anchor_row:
        return "Anchor team not in the CFP at-large field this snapshot."
    x = anchor_row.get("x", 0.5)
    y = anchor_row.get("y", 0.5)
    name = anchor_row.get("label") or anchor
    if x > 0.65 and y > 0.65:
        return f"{name} clears both the committee case and the model — in the bracket on every read."
    if x < 0.4 and y > 0.65:
        return f"{name} models like a contender but the resume is sitting near the cut line."
    if x > 0.65 and y < 0.4:
        return f"{name} has the resume the committee wants — the model says it might be borrowed."
    return f"{name} sits in the bubble zone where one bad result tips the bracket either way."


def _anchor_position_label(rows: list[dict], anchor: str) -> str:
    r = next((r for r in rows if r.get("slug") == anchor), None)
    if not r:
        return ""
    return f"{r.get('label', anchor)}: resume {int(r.get('x', 0) * 100)}P, power {int(r.get('y', 0) * 100)}P"


# ---------------------------------------------------------------------------
# Talent Yield Curve
# ---------------------------------------------------------------------------


def render_talent_yield_curve(
    query_result: dict[str, Any],
    spec_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    highlight_slug = summary.get("anchor_slug")
    season = summary.get("season_year", "")

    if not rows:
        return _empty_render("No talent / draft data for this snapshot.")

    sr_title = (
        f"Talent Yield Curve — {season}: recruiting talent rank vs draft-pick yield "
        f"across FBS programs"
    )
    headline = _headline_for_talent_yield(rows, summary, highlight_slug)

    annotations: list[Annotation] = []
    if highlight_slug:
        anchor_row = next((r for r in rows if r.get("slug") == highlight_slug), None)
        if anchor_row:
            annotations.append(Annotation(
                target=highlight_slug,
                text=f"{anchor_row.get('label', highlight_slug)} yield position",
                reason="anchor team talent-to-draft yield",
            ))

    return _render_scatter_core(
        rows,
        title="Talent Yield Curve",
        subtitle=f"{season}: recruit talent percentile vs draft-pick yield",
        x_label="Recruit talent percentile",
        y_label="Draft yield percentile",
        highlight_slug=highlight_slug,
        sr_title=sr_title,
        headline_finding=headline,
        annotations=annotations,
    )


def _headline_for_talent_yield(rows: list[dict], summary: dict, anchor: str | None) -> str:
    if not anchor:
        return "Recruit-talent rank vs draft-yield rate across FBS programs."
    anchor_row = next((r for r in rows if r.get("slug") == anchor), None)
    if not anchor_row:
        return "Anchor program has no draft-yield snapshot for this window."
    x = anchor_row.get("x", 0.5)
    y = anchor_row.get("y", 0.5)
    name = anchor_row.get("label") or anchor
    if y > x + 0.15:
        return f"{name} converts recruit talent into draft picks better than its class rank suggests."
    if x > y + 0.15:
        return f"{name} signs higher-rated classes than its draft yield delivers."
    return f"{name} sits where recruit talent and draft yield largely match."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
