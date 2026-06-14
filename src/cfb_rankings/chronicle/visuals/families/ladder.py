"""Statement Win Ladder — diverging bars: which results moved the résumé most.

Migrated onto the Editorial Grammar (doc 77). Diverging-bar best practice (web
research 2026-06-14 — Domo "Divergent Bar Charts"; ChartGen diverging-bar
guide): a centre zero spine, colour by sign, sort by value (the query orders by
impact), direct value labels. Ours conformed on migration; the single biggest
mover is additionally highlighted with a halo, now on the shared chrome.
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import line, rect
from .grammar import editorial_card, cls_text, dot, VIOLET, SANS, MONO, MUTED, INK, CREAM, POS, NEG

UP = POS    # colour-blind-safe (Okabe-Ito blue)
DOWN = NEG  # vermillion


def render_statement_win_ladder(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    if not rows:
        return _empty_render("No completed games yet.")

    headline = _headline_for_ladder(rows, summary)
    sr_title = f"Statement Win Ladder — top result: {rows[0]['result_text']} vs {rows[0]['opponent_name']}"
    height = 152 + 32 * len(rows)
    deltas = [float(r["total_delta"]) for r in rows]
    max_abs = max((abs(d) for d in deltas), default=1.0) or 1.0

    def draw(px, py, pw, ph):
        n = len(rows)
        row_h = ph / n
        rail_l = px + 172
        chart_x1 = px + pw - 52
        chart_w = chart_x1 - rail_l
        zero_x = rail_l + chart_w * 0.5
        out = [line(zero_x, py, zero_x, py + ph, color=MUTED, width=1.0, dasharray="2,3")]
        for i, r in enumerate(rows):
            yc = py + row_h * i + row_h / 2
            d = float(r["total_delta"])
            bw = (d / max_abs) * (chart_w / 2)
            bx = zero_x if d >= 0 else zero_x + bw
            bwa = abs(bw)
            is_top = bool(r.get("is_top_result"))
            col = VIOLET if is_top else (UP if d >= 0 else DOWN)
            opp = (r.get("opponent_name") or "")[:18]
            lab = f"{r['result_text']}  vs {opp}"
            out.append(cls_text(px, yc + 4, lab, "ed-ax" if not is_top else "ed-ptlabel",
                                family=SANS, color=INK, weight="700" if is_top else "400"))
            tip = f"{r['result_text']} vs {r.get('opponent_name', '')} — {d:+.2f} résumé impact"
            out.append(f'<rect class="ed-dot" x="{bx:.1f}" y="{yc - 8:.1f}" width="{bwa:.1f}" '
                       f'height="16" rx="2" fill="{col}" opacity="0.85" tabindex="0" '
                       f'data-tip="{html.escape(tip)}"><title>{html.escape(tip)}</title></rect>')
            if is_top:
                tipx = bx + bwa if d >= 0 else bx
                out.append(f'<circle cx="{tipx:.1f}" cy="{yc:.1f}" r="10" fill="{VIOLET}" opacity="0.14"/>')
                out.append(dot(tipx, yc, 5.0, fill=VIOLET, stroke=CREAM, stroke_width=1.5, tip=tip))
            out.append(cls_text(px + pw, yc + 4, f"{'+' if d >= 0 else ''}{d:.2f}", "ed-ptlabel",
                                family=MONO, color=INK, anchor="end"))
        return out

    conf = (query_result.get("confidence") or "unset")
    receipt = (f"Source: CFB Index — results ranked by combined power + résumé impact · "
               f"top {len(rows)} games · {conf} confidence")
    svg = editorial_card(
        eyebrow=f"STATEMENT WINS  ·  TOP {len(rows)} RESULTS", headline=headline,
        annotation=f"▸ {rows[0]['result_text']} vs {rows[0]['opponent_name']} is the biggest mover.",
        receipt=receipt, title=sr_title, draw_plot=draw, height=height,
    )
    annotations: list[Annotation] = []
    if rows[0].get("is_top_result"):
        annotations.append(Annotation(target=rows[0].get("opponent_slug") or rows[0]["opponent_name"],
                                      text=f"biggest mover ({rows[0]['result_text']})",
                                      reason="top combined power+resume delta on the schedule"))
    return {
        "svg_html": svg, "headline_finding": headline, "annotations": annotations,
        "alt_text": (f"Statement Win Ladder: top {len(rows)} games by power+résumé delta. "
                     f"Largest mover {rows[0]['result_text']} vs {rows[0]['opponent_name']} "
                     f"({float(rows[0]['total_delta']):+.2f})."),
    }


def _headline_for_ladder(rows: list[dict], summary: dict) -> str:
    if not rows:
        return "No completed games on the schedule yet."
    top = rows[0]
    if len(rows) == 1:
        return f"{top['result_text']} vs {top['opponent_name']} is the season so far."
    top_d = float(top["total_delta"])
    rest_avg = sum(float(r["total_delta"]) for r in rows[1:]) / (len(rows) - 1)
    if rest_avg > 0 and top_d / max(0.001, rest_avg) >= 1.6:
        return (f"{top['result_text']} vs {top['opponent_name']} moved the résumé more than the "
                f"next {len(rows) - 1} wins combined.")
    return (f"{top['result_text']} vs {top['opponent_name']} leads the season's top {len(rows)} "
            f"results by combined power and résumé delta.")


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" '
                    f'font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
