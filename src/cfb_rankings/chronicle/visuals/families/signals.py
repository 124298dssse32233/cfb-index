"""Signal-family renderers: Delta DNA (EKG swing line) + Continuity Stress Test.

Both exploit proprietary CFB Index model outputs (per-game rating deltas,
structured returning production) that competitors don't expose.
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

_ARCHETYPE_COPY = {
    "boom-built": "boom-built — high week-to-week swing, but trending up",
    "boom-bust": "boom-bust — volatile week to week, no clear direction",
    "steadily-built": "steadily-built — low volatility, quietly improving",
    "fake-stable": "fake-stable — calm on the surface, trending the wrong way",
    "flat-line": "flat-line — little real movement either direction",
}


def render_delta_dna(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    s = query_result.get("summary_stats", {})
    if not rows:
        return _empty("Not enough game data for a swing signature.")

    season = s.get("season_year", "")
    width, height = 640, 240
    pad_l, pad_r, pad_t, pad_b = 24, 24, 64, 36
    cw = width - pad_l - pad_r
    ch = height - pad_t - pad_b

    sr_title = f"Delta DNA — {season} per-game power swing signature ({s.get('archetype','')})"
    parts = [svg_open(width, height, title=sr_title), rect(0, 0, width, height, fill=PALETTE_CREAM)]
    parts.append(text(20, 28, "Delta DNA", font_size=16, weight="700"))
    parts.append(text(20, 48, f"{season} per-game power swing · {s.get('archetype','')}", font_size=12, color=PALETTE_MUTED, italic=True))

    deltas = [r["power_delta"] for r in rows]
    n = len(deltas)
    amax = max(1.0, max(abs(d) for d in deltas))
    zero_y = pad_t + ch / 2

    # zero baseline
    parts.append(line(pad_l, zero_y, pad_l + cw, zero_y, color=PALETTE_INK, width=1.0, dasharray="2,3"))

    def x_of(i): return pad_l + (cw * i / (n - 1)) if n > 1 else pad_l + cw / 2
    def y_of(d): return zero_y - (d / amax) * (ch / 2)

    # EKG line + per-game bars
    d_path = "M" + " L".join(f"{x_of(i):.1f},{y_of(d):.1f}" for i, d in enumerate(deltas))
    parts.append(f'<path d="{d_path}" fill="none" stroke="{PALETTE_NAVY}" stroke-width="1.8" stroke-linejoin="round"/>')
    for i, d in enumerate(deltas):
        col = PALETTE_GOLD if d >= 0 else "#b3402f"
        parts.append(circle(x_of(i), y_of(d), 3, fill=col))

    # volatility + mean readout
    parts.append(text(width - 20, pad_t - 8, f"volatility {s.get('volatility',0):.2f} · mean {s.get('mean_delta',0):+.2f}",
                      font_size=10, color=PALETTE_MUTED, anchor="end"))
    parts.append(text(20, height - 12, _ARCHETYPE_COPY.get(s.get("archetype",""), ""), font_size=11, color=PALETTE_MUTED, italic=True))
    parts.append(svg_close())

    headline = _delta_headline(s)
    return {
        "svg_html": join(parts),
        "headline_finding": headline,
        "annotations": [Annotation(target=str(s.get("archetype","")), text=_ARCHETYPE_COPY.get(s.get("archetype",""),""), reason="power-delta volatility + mean")],
        "alt_text": f"Delta DNA swing line for {season}: {n} games, volatility {s.get('volatility',0):.2f}, archetype {s.get('archetype','')}.",
    }


def _delta_headline(s: dict) -> str:
    a = s.get("archetype", "")
    season = s.get("season_year", "")
    vol = s.get("volatility", 0)
    if a == "boom-built":
        return f"A boom-built {season} swing signature — volatile, but the trend points up into 2026."
    if a == "boom-bust":
        return f"A boom-bust {season}: big week-to-week swings ({vol:.1f} volatility) with no settled direction."
    if a == "steadily-built":
        return f"A steadily-built program — low {season} volatility and a quietly positive trend."
    if a == "fake-stable":
        return f"Fake-stable in {season}: calm week to week, but the model trend runs the wrong way."
    return f"A flat-line {season} signature — little real week-to-week movement either way."


def render_continuity_stress_test(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    bars = query_result.get("rows", [])
    s = query_result.get("summary_stats", {})
    if not bars:
        return _empty("No returning-production snapshot for this season.")

    season = s.get("season_year", "")
    width = 600
    row_h = 34
    pad_t, pad_b = 64, 34
    height = pad_t + pad_b + row_h * len(bars)
    bar_x0, bar_x1 = 96, width - 90
    bw = bar_x1 - bar_x0

    sr_title = f"Continuity Stress Test — {season} returning production by unit"
    parts = [svg_open(width, height, title=sr_title), rect(0, 0, width, height, fill=PALETTE_CREAM)]
    parts.append(text(20, 28, "Continuity Stress Test", font_size=16, weight="700"))
    parts.append(text(20, 48, f"{season} returning production by unit · vs FBS average", font_size=12, color=PALETTE_MUTED, italic=True))

    stressed_key = s.get("stressed_key")
    for i, b in enumerate(bars):
        y = pad_t + row_h * i
        v = max(0.0, min(1.0, b["value"]))
        is_stress = b["key"] == stressed_key
        col = "#b3402f" if is_stress else (PALETTE_GOLD if b["key"] == "TOT" else PALETTE_NAVY)
        parts.append(text(20, y + 18, b["label"], font_size=12, weight="700" if b["key"] == "TOT" else "400"))
        parts.append(rect(bar_x0, y + 6, bw, 18, fill="#fff", opacity=0.6))
        parts.append(rect(bar_x0, y + 6, bw * v, 18, fill=col, opacity=0.9))
        # league avg tick
        la = max(0.0, min(1.0, b.get("league_avg", 0)))
        tx = bar_x0 + bw * la
        parts.append(line(tx, y + 2, tx, y + 28, color=PALETTE_INK, width=1.0, dasharray="2,2"))
        parts.append(text(width - 16, y + 18, f"{v*100:.0f}%", font_size=12, anchor="end",
                          family="ui-monospace,Menlo,monospace", weight="700" if is_stress else "400",
                          color="#b3402f" if is_stress else PALETTE_INK))

    parts.append(text(20, height - 12, "dashed tick = FBS average", font_size=10, color=PALETTE_MUTED, italic=True))
    parts.append(svg_close())

    headline = _continuity_headline(s)
    return {
        "svg_html": join(parts),
        "headline_finding": headline,
        "annotations": [Annotation(target=str(s.get("stressed_key","")), text=f"{s.get('stressed_label','')} is the stress point", reason="lowest returning production vs league average")],
        "alt_text": f"Continuity Stress Test {season}: overall {s.get('overall_value',0)*100:.0f}% returning; stress point {s.get('stressed_label','')}.",
    }


def _continuity_headline(s: dict) -> str:
    season = s.get("season_year", "")
    overall = s.get("overall_value", 0)
    avg = s.get("overall_avg", 0)
    stressed = s.get("stressed_label", "")
    anchored = s.get("anchored_label", "")
    diff = overall - avg
    if diff >= 0.08:
        return f"Among the most continuous rosters into {season} — {overall*100:.0f}% back, anchored by the {anchored.lower()}, only {stressed.lower()} to settle."
    if diff <= -0.08:
        return f"A heavy-turnover {season}: {overall*100:.0f}% returning (below average), with the {stressed.lower()} the biggest question."
    return f"Average {season} continuity ({overall*100:.0f}% back) — {anchored.lower()} anchors it, {stressed.lower()} is the stress point."


def _empty(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
