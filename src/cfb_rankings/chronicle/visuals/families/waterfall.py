"""Returning Production X-Ray — returning value by side vs the FBS average.

Migrated onto the Editorial Grammar (doc 77). Horizontal bars per bar/lollipop
best practice (web research 2026-06-14 — Domo "Lollipop Charts"; 3iap bars-vs-
lollipops): zero baseline, a reference tick (the FBS average), direct tip value
labels, interactive bars; QB/OL continuity folded into the marginalia. Keeps the
deterministic finding-headline.
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import line, rect
from .grammar import editorial_card, cls_text, BLUE, SANS, MONO, MUTED, INK


def render_returning_production_xray(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    if not rows:
        return _empty_render("No returning-production snapshot for this season.")

    season = summary.get("season_year", "")
    headline = _headline_for_returning(rows, summary)
    league_avgs = {"Offense": float(summary.get("league_avg_offense", 0.0) or 0.0),
                   "Defense": float(summary.get("league_avg_defense", 0.0) or 0.0)}
    max_v = max([abs(float(r["value"])) for r in rows] + list(league_avgs.values()) + [1.0])

    def draw(px, py, pw, ph):
        n = len(rows)
        row_h = ph / n
        bar_x0 = px + 116
        bar_x1 = px + pw - 48
        bw = bar_x1 - bar_x0
        out: list[str] = []
        for i, r in enumerate(rows):
            yc = py + row_h * i + row_h / 2
            v = float(r["value"])
            out.append(cls_text(px, yc + 4, r["label"], "ed-ax", family=SANS, color=INK, weight="700"))
            out.append(rect(bar_x0, yc - 11, bw, 22, fill="#ffffff", opacity=0.5))
            disp = f"{v * 100:.0f}%" if 0 <= v <= 1 else f"{v:.0f}"
            t = f"{r['label']}: {disp} returning"
            out.append(f'<rect class="ed-dot" x="{bar_x0:.1f}" y="{yc - 11:.1f}" '
                       f'width="{(v / max_v) * bw:.1f}" height="22" rx="2" fill="{BLUE}" opacity="0.9" '
                       f'tabindex="0" data-tip="{html.escape(t)}"><title>{html.escape(t)}</title></rect>')
            avg = league_avgs.get(r["label"], 0)
            if avg > 0:
                tx = bar_x0 + (avg / max_v) * bw
                out.append(line(tx, yc - 14, tx, yc + 14, color=INK, width=1.0, dasharray="2,3"))
            out.append(cls_text(px + pw, yc + 4, disp, "ed-ptlabel", family=MONO, color=INK, anchor="end"))
        return out

    qb = summary.get("returning_qb")
    ol = summary.get("returning_ol")
    chips = []
    if qb is not None:
        chips.append(f"QB room {float(qb) * 100:.0f}%" if 0 <= float(qb) <= 1 else f"QB {qb}")
    if ol is not None:
        chips.append(f"O-line {float(ol) * 100:.0f}%" if 0 <= float(ol) <= 1 else f"OL {ol}")
    annotation = "▸ " + " · ".join(chips) + " returning." if chips else "▸ Returning value vs the FBS average."

    conf = (query_result.get("confidence") or "unset")
    receipt = (f"Source: CFB Index — returning value vs the FBS average (dashed = league avg) · "
               f"{season} · {conf} confidence")
    svg = editorial_card(
        eyebrow=f"RETURNING PRODUCTION  ·  {season}", headline=headline,
        annotation=annotation, receipt=receipt,
        title=f"Returning Production X-Ray — {season} season", draw_plot=draw, height=300,
    )
    annotations: list[Annotation] = []
    if qb:
        annotations.append(Annotation(target="qb_room", text=f"QB room returns {float(qb) * 100:.0f}%",
                                      reason="passing-room continuity from prior season"))
    alt = (f"Returning Production X-Ray {season}: " +
           ", ".join(f"{r['label']} {float(r['value']) * 100:.0f}%" for r in rows) + " vs FBS averages.")
    return {"svg_html": svg, "headline_finding": headline, "annotations": annotations, "alt_text": alt}


def _headline_for_returning(rows: list[dict], summary: dict) -> str:
    if len(rows) < 2:
        return "A returning-production snapshot for the season ahead."
    off = float(rows[0]["value"])
    deff = float(rows[1]["value"])
    avg_off = float(summary.get("league_avg_offense", 0) or 0)
    avg_def = float(summary.get("league_avg_defense", 0) or 0)
    side = None
    diff = 0.0
    if avg_off and abs(off - avg_off) > abs(deff - avg_def):
        side, diff = ("Offense", off, avg_off), off - avg_off
    elif avg_def:
        side, diff = ("Defense", deff, avg_def), deff - avg_def
    if side and abs(diff) >= 0.08:
        direction = "above" if diff > 0 else "below"
        return f"{side[0]} returns {abs(diff) * 100:.0f} points {direction} the FBS average."
    return "Returning production lands near the FBS average on both sides."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" '
                    f'font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
