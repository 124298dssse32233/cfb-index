"""Signal-family renderers (migrated onto the Editorial Grammar):
    - Delta DNA: an EKG annotated line of per-game power-rating swings
    - Continuity Stress Test: returning production by unit vs the FBS average

Both exploit proprietary CFB Index model outputs and now render through
`grammar.editorial_card` (doc 77): finding-headline, human receipt, design
fonts, mobile type scale, scroll-driven entrance, interactive points.
Web research 2026-06-14 — annotated line (Venngage "Line Charts"; index.app
"Line Graph Guide"): zero baseline, direct labels, and **annotate the
inflection point** (the biggest swing is now marked + labelled). Ranked bars
(Domo "Lollipop Charts"; 3iap bars-vs-lollipops): zero baseline + a reference
tick (the FBS average) + highlight the stress unit + tip value labels.
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import line, rect
from .grammar import editorial_card, cls_text, dot, BLUE, GRID, SANS, MONO, MUTED, INK, POS, NEG

UP = POS     # positive swing (colour-blind-safe blue)
DOWN = NEG   # negative swing / stress (vermillion)

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
    archetype = s.get("archetype", "")
    deltas = [float(r["power_delta"]) for r in rows]
    n = len(deltas)
    amax = max(1.0, max(abs(d) for d in deltas))
    headline = _delta_headline(s)

    def draw(px, py, pw, ph):
        zero_y = py + ph * 0.5

        def X(i):
            return px + (pw * i / (n - 1) if n > 1 else pw / 2)

        def Y(d):
            return zero_y - (d / amax) * (ph * 0.42)

        out = [line(px, zero_y, px + pw, zero_y, color=MUTED, width=1.0, dasharray="2,3")]
        path = "M" + " L".join(f"{X(i):.1f},{Y(d):.1f}" for i, d in enumerate(deltas))
        out.append(f'<path d="{path}" fill="none" stroke="{INK}" stroke-width="1.8" stroke-linejoin="round"/>')
        for i, d in enumerate(deltas):
            out.append(dot(X(i), Y(d), 3.2, fill=(UP if d >= 0 else DOWN),
                           tip=f"Game {i + 1}: {d:+.2f} power swing"))
        # annotate the inflection point — the single biggest swing (research 2026-06-14)
        bi = max(range(n), key=lambda i: abs(deltas[i]))
        bx, by = X(bi), Y(deltas[bi])
        out.append(line(bx, by, bx, zero_y, color=MUTED, width=0.8, dasharray="1,3"))
        out.append(cls_text(bx, by - 9 if deltas[bi] >= 0 else by + 15, f"{deltas[bi]:+.1f}", "ed-ptlabel",
                            family=SANS, color=(UP if deltas[bi] >= 0 else DOWN), anchor="middle", weight="700"))
        out.append(cls_text(px + pw, py + 8, f"volatility {float(s.get('volatility', 0)):.2f} · "
                            f"mean {float(s.get('mean_delta', 0)):+.2f}", "ed-ax", family=SANS,
                            color=MUTED, anchor="end"))
        return out

    conf = (query_result.get("confidence") or "unset")
    receipt = (f"Source: CFB Index — per-game power-rating swings · {season} · "
               f"{n} games · {conf} confidence")
    svg = editorial_card(
        eyebrow=f"PER-GAME POWER SWING  ·  {season}",
        headline=headline,
        annotation="▸ " + _ARCHETYPE_COPY.get(archetype, "the season's swing signature") + ".",
        receipt=receipt, title=f"Delta DNA — {season} per-game power swing ({archetype})",
        draw_plot=draw, height=300,
    )
    return {
        "svg_html": svg, "headline_finding": headline,
        "annotations": [Annotation(target=str(archetype), text=_ARCHETYPE_COPY.get(archetype, ""),
                                   reason="power-delta volatility + mean")],
        "alt_text": f"Delta DNA for {season}: {n} games, volatility {float(s.get('volatility', 0)):.2f}, archetype {archetype}.",
    }


def _delta_headline(s: dict) -> str:
    a = s.get("archetype", "")
    season = s.get("season_year", "")
    vol = float(s.get("volatility", 0))
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
    stressed_key = s.get("stressed_key")
    headline = _continuity_headline(s)
    height = 152 + 30 * len(bars)

    def draw(px, py, pw, ph):
        n = len(bars)
        row_h = ph / n
        bar_x0 = px + 88
        bw = (px + pw) - bar_x0 - 44
        out: list[str] = []
        for i, b in enumerate(bars):
            yc = py + row_h * i + row_h / 2
            is_tot = b["key"] == "TOT"
            out.append(cls_text(px, yc + 4, b["label"], "ed-ax", family=SANS, color=INK,
                                weight="700" if is_tot else "400"))
            out.append(rect(bar_x0, yc - 9, bw, 18, fill="#ffffff", opacity=0.5))
            if b.get("value") is None:
                out.append(cls_text(px + pw, yc + 4, "n/a", "ed-ptlabel", family=MONO,
                                    color=MUTED, anchor="end"))
                continue
            v = max(0.0, min(1.0, float(b["value"])))
            is_stress = b["key"] == stressed_key
            col = DOWN if is_stress else (INK if is_tot else BLUE)
            t = f"{b['label']}: {v * 100:.0f}% returning"
            out.append(f'<rect class="ed-dot" x="{bar_x0:.1f}" y="{yc - 9:.1f}" width="{bw * v:.1f}" '
                       f'height="18" rx="2" fill="{col}" opacity="0.9" tabindex="0" data-tip="{html.escape(t)}">'
                       f'<title>{html.escape(t)}</title></rect>')
            la = max(0.0, min(1.0, float(b.get("league_avg") or 0)))
            tx = bar_x0 + bw * la
            out.append(line(tx, yc - 11, tx, yc + 11, color=INK, width=1.0, dasharray="2,2"))
            out.append(cls_text(px + pw, yc + 4, f"{v * 100:.0f}%", "ed-ptlabel", family=MONO,
                                color=DOWN if is_stress else INK, anchor="end",
                                weight="700" if is_stress else "400"))
        return out

    conf = (query_result.get("confidence") or "unset")
    receipt = (f"Source: CFB Index — returning production vs the FBS average (dashed = league avg) · "
               f"{season} · {conf} confidence")
    svg = editorial_card(
        eyebrow=f"RETURNING PRODUCTION  ·  {season}",
        headline=headline,
        annotation=f"▸ {s.get('stressed_label', 'one unit')} is the stress point for {season}.",
        receipt=receipt, title=f"Continuity Stress Test — {season} returning production by unit",
        draw_plot=draw, height=height,
    )
    return {
        "svg_html": svg, "headline_finding": headline,
        "annotations": [Annotation(target=str(stressed_key or ""),
                                   text=f"{s.get('stressed_label', '')} is the stress point",
                                   reason="lowest returning production vs league average")],
        "alt_text": f"Continuity Stress Test {season}: overall {float(s.get('overall_value', 0)) * 100:.0f}% returning; stress point {s.get('stressed_label', '')}.",
    }


def _continuity_headline(s: dict) -> str:
    season = s.get("season_year", "")
    overall = float(s.get("overall_value", 0))
    avg = float(s.get("overall_avg", 0))
    stressed = s.get("stressed_label", "")
    anchored = s.get("anchored_label", "")
    diff = overall - avg
    if diff >= 0.08:
        return (f"Among the most continuous rosters into {season} — {overall * 100:.0f}% back, "
                f"anchored by the {anchored.lower()}, only {stressed.lower()} to settle.")
    if diff <= -0.08:
        return (f"A heavy-turnover {season}: {overall * 100:.0f}% returning (below average), with "
                f"the {stressed.lower()} the biggest question.")
    return (f"Average {season} continuity ({overall * 100:.0f}% back) — {anchored.lower()} anchors it, "
            f"{stressed.lower()} is the stress point.")


def _empty(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" '
                    f'font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
