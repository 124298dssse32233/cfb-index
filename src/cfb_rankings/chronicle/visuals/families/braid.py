"""Heisman Race Braid — a bump chart of weekly rank trajectory.

Migrated onto the Editorial Grammar (doc 77). Bump-chart best practice (web
research 2026-06-14 — Domo "Bump Charts"; Power BI/Lumiplot "What Bump Charts
Tell You That Line Charts Hide"; NumberAnalytics): invert Y so #1 is at top,
strip clutter, highlight ONE line, and **label lines at their endpoints** —
so every contender is labelled at its end-rank (leader bold violet, the rest
gray), not just the leader; the crossings (overtakes) are the story. The
finalist-probability leader is folded into the marginalia.
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import line
from .grammar import editorial_card, cls_text, dot, VIOLET, GRID, SANS, MUTED, CREAM

FIELD = "#9a948a"


def render_heisman_race_braid(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    if not rows:
        return _empty_render("No Heisman rankings for this snapshot.")

    week = summary.get("snapshot_week", "?")
    season = summary.get("season_year", "")
    weeks = sorted({h["week"] for r in rows for h in r["history"] if h["week"] is not None})
    if not weeks:
        return _empty_render("No week history available.")
    w_min, w_max = weeks[0], weeks[-1]
    n_ranks = len(rows)
    headline = _headline_for_braid(rows, summary)

    def draw(px, py, pw, ph):
        fx0, fx1 = px + 26, px + pw - 92
        fy0, fy1 = py + 4, py + ph - 18

        def X(w):
            return fx0 + (fx1 - fx0) * ((w - w_min) / (w_max - w_min) if w_max > w_min else 0.5)

        def Y(rank):
            return fy0 + (fy1 - fy0) * ((rank - 1) / max(1, n_ranks - 1)) if n_ranks > 1 else (fy0 + fy1) / 2

        out: list[str] = []
        for i in range(1, n_ranks + 1):
            y = Y(i)
            out.append(line(fx0, y, fx1, y, color=GRID, width=0.5))
            out.append(cls_text(fx0 - 5, y + 3, f"#{i}", "ed-ax", family=SANS, color=MUTED, anchor="end"))
        for idx, r in enumerate(rows):
            is_anchor = idx == 0
            hist = sorted([h for h in r["history"] if h["rank"] is not None], key=lambda h: h["week"])
            if not hist:
                continue
            d = " ".join((("M" if j == 0 else "L") + f"{X(h['week']):.1f},{Y(h['rank']):.1f}")
                         for j, h in enumerate(hist))
            color = VIOLET if is_anchor else FIELD
            op = "" if is_anchor else ' stroke-opacity="0.4"'
            out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{2.4 if is_anchor else 1.2}" '
                       f'stroke-linejoin="round"{op}/>')
            last = hist[-1]
            if is_anchor:
                out.append(dot(X(last["week"]), Y(last["rank"]), 5.0, fill=VIOLET, stroke=CREAM, stroke_width=1.5,
                               tip=f"{r['player_name']} — #{last['rank']} at Week {last['week']}"))
                out.append(cls_text(X(last["week"]) + 9, Y(last["rank"]) + 4, str(r["player_name"]),
                                    "ed-ptlabel", family=SANS, weight="700", color=VIOLET))
            else:
                out.append(f'<circle cx="{X(last["week"]):.1f}" cy="{Y(last["rank"]):.1f}" r="2.6" fill="{FIELD}"/>')
                out.append(cls_text(X(last["week"]) + 8, Y(last["rank"]) + 3, str(r["player_name"]).split()[-1],
                                    "ed-ax", family=SANS, color=FIELD))
        for w in weeks:
            if w == w_min or w == w_max or w % 4 == 0:
                out.append(cls_text(X(w), fy1 + 16, f"W{w}", "ed-ax", family=SANS, color=MUTED, anchor="middle"))
        return out

    lead_hist = sorted(rows[0]["history"], key=lambda h: h["week"]) if rows[0].get("history") else []
    lp = (lead_hist[-1].get("finalist_probability", 0) or 0) if lead_hist else 0
    annotation = (f"▸ {rows[0]['player_name']} — {lp * 100:.0f}% finalist probability through Week {week}."
                  if lp else f"▸ {rows[0]['player_name']} leads the race through Week {week}.")
    conf = (query_result.get("confidence") or "unset")
    receipt = (f"Source: CFB Index — weekly Heisman rank trajectory · {season} Wk {week} · "
               f"top {n_ranks} · {conf} confidence")
    svg = editorial_card(
        eyebrow=f"HEISMAN RACE  ·  {season} WK {week}", headline=headline,
        annotation=annotation, receipt=receipt,
        title=f"Heisman Race Braid — {season} through week {week}; top {n_ranks} contenders",
        draw_plot=draw, height=380,
    )
    annotations = [Annotation(target=rows[0].get("team_slug") or rows[0]["player_name"],
                              text=f"#{rows[0].get('current_rank', '?')} at week {week}",
                              reason="anchor of the current Heisman race")]
    return {
        "svg_html": svg, "headline_finding": headline, "annotations": annotations,
        "alt_text": (f"Heisman Race Braid {season} through week {week}: top {n_ranks} traced week by week, "
                     f"leader {rows[0]['player_name']} at #{rows[0].get('current_rank', '?')}."),
    }


def _headline_for_braid(rows: list[dict], summary: dict) -> str:
    if not rows:
        return "A snapshot of the Heisman race."
    leader = rows[0]
    h = sorted(leader["history"], key=lambda x: x["week"]) if leader.get("history") else []
    if len(h) >= 2:
        sr, er = h[0]["rank"], h[-1]["rank"]
        if sr and er and sr > er + 3:
            return f"{leader['player_name']} climbed from #{sr} to #{er} in the Heisman race."
        if sr and er and er > sr + 3:
            return f"{leader['player_name']} held the lead despite a {er - sr}-spot slide."
    return f"{leader['player_name']} leads the Heisman race through week {summary.get('snapshot_week', '?')}."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" '
                    f'font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
