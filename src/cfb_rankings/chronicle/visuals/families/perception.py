"""Player belief family — Perception vs the Tape (quadrant scatter).

Hype percentile (x) vs production percentile (y) within the player's position
cohort, with median crosshairs forming four named quadrants. The subject is
the one saturated dot; the cohort recedes to gray; only the subject + two
notable peers are labelled (overplot discipline). Built on the shared
Editorial Grammar (doc 77) — proving the grammar copies to a 2-D geometry,
not just dumbbells. Every value comes from the query.
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import text, line, circle, rect
from .grammar import editorial_card, dot, ordinal, VIOLET, GRID, SANS, MUTED, CREAM, INK

COHORT = "#bfb9ab"   # field dots recede
PEER = "#8a8475"     # notable peers, a touch darker


def _last(name: str) -> str:
    return name.split()[-1] if name else name


def render_perception_vs_tape(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    s = query_result.get("summary_stats", {}) or {}
    pts = query_result.get("rows", []) or []
    if not s or not pts:
        return _empty("Not enough cohort data for a perception-vs-tape read.")

    name = s.get("player_name", "")
    pos = s.get("position", "")
    metric = s.get("metric", "")
    n = int(s.get("n_cohort", 0))
    hx, py_ = int(s.get("hype_pctile", 0)), int(s.get("prod_pctile", 0))
    quad = s.get("quadrant", "")
    season, prod_season = s.get("season_year", ""), s.get("prod_season", "")
    conf = (query_result.get("confidence") or "unset").upper()

    if quad == "PROVEN":
        headline = f"{name} is producing like a star — and the buzz agrees."
    elif quad == "UNDERRATED":
        headline = f"{name} is producing like a star the hype hasn't caught."
    elif quad == "OVERHYPED":
        headline = f"{name} draws star buzz the tape doesn't back yet."
    else:
        headline = f"{name} is quiet on both the buzz and the tape."

    def draw(px, py, pw, ph):
        # inner field with gutters for axis labels
        fx0, fy0 = px + 30, py + 6
        fw, fh = pw - 30 - 12, ph - 6 - 26

        def X(p):
            return fx0 + fw * (max(0, min(100, p)) / 100.0)

        def Y(p):
            return fy0 + fh * (1 - max(0, min(100, p)) / 100.0)

        out: list[str] = []
        # subject-quadrant faint shade (draws the eye to the story)
        qx0 = fx0 if hx < 50 else X(50)
        qw = (X(50) - fx0) if hx < 50 else (fx0 + fw - X(50))
        qy0 = fy0 if py_ >= 50 else Y(50)
        qh = (Y(50) - fy0) if py_ >= 50 else (fy0 + fh - Y(50))
        out.append(rect(qx0, qy0, qw, qh, fill=VIOLET, opacity=0.06))
        # median crosshairs
        out.append(line(X(50), fy0, X(50), fy0 + fh, color=MUTED, width=1.0, dasharray="2,3"))
        out.append(line(fx0, Y(50), fx0 + fw, Y(50), color=MUTED, width=1.0, dasharray="2,3"))
        # quadrant corner labels
        out.append(text(fx0 + 6, fy0 + 13, "UNDERRATED", font_size=9, family=SANS, color=MUTED))
        out.append(text(fx0 + fw - 6, fy0 + 13, "PROVEN", font_size=9, family=SANS, color=MUTED, anchor="end"))
        out.append(text(fx0 + 6, fy0 + fh - 5, "OFF RADAR", font_size=9, family=SANS, color=MUTED))
        out.append(text(fx0 + fw - 6, fy0 + fh - 5, "OVERHYPED", font_size=9, family=SANS, color=MUTED, anchor="end"))
        # axis direction labels
        out.append(text(fx0 + fw / 2, fy0 + fh + 20, "MORE HYPE →", font_size=10, family=SANS,
                        color=MUTED, anchor="middle"))
        ylx, yly = px + 9, fy0 + fh / 2
        out.append(f'<text x="{ylx:.1f}" y="{yly:.1f}" font-family="{SANS}" font-size="10" '
                   f'fill="{MUTED}" text-anchor="middle" transform="rotate(-90 {ylx:.1f} {yly:.1f})">'
                   f'MORE PRODUCTION →</text>')
        # cohort dots (gray), then peers, then subject on top
        subject = None
        for p in pts:
            if p.get("subject"):
                subject = p
                continue
            if p.get("peer"):
                continue
            out.append(f'<circle cx="{X(p["x"]):.1f}" cy="{Y(p["y"]):.1f}" r="3.0" '
                       f'fill="{COHORT}" opacity="0.5" style="mix-blend-mode:multiply"/>')
        for p in pts:
            if p.get("peer") and not p.get("subject"):
                cx, cy = X(p["x"]), Y(p["y"])
                out.append(dot(cx, cy, 4.2, fill=PEER,
                               tip=f"{p['name']} — hype {ordinal(p['x'])}, production {ordinal(p['y'])}"))
                anc = "end" if p["x"] >= 72 else "start"
                dx = -7 if anc == "end" else 7
                out.append(text(cx + dx, cy + 3, _last(p["name"]), font_size=9, family=SANS, color=PEER, anchor=anc))
        if subject:
            cx, cy = X(subject["x"]), Y(subject["y"])
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="{VIOLET}" opacity="0.14"/>')  # outlier halo
            out.append(dot(cx, cy, 6.5, fill=VIOLET, stroke=CREAM, stroke_width=2.0,
                           tip=f"{name} — hype {ordinal(subject['x'])}, production {ordinal(subject['y'])} ({quad.title()})"))
            anc = "end" if hx >= 72 else "start"
            dx = -10 if anc == "end" else 10
            ly = cy + 18 if py_ >= 86 else cy - 11
            out.append(text(cx + dx, ly, name, font_size=12, family=SANS, weight="700", color=VIOLET, anchor=anc))
        return out

    metric_human = {
        "wepa_passing": "passing value (wEPA)",
        "wepa_rushing": "rushing value (wEPA)",
    }.get(metric, metric)
    annotation = f"▸ Hype {ordinal(hx)} percentile, production {ordinal(py_)} percentile among {n} {pos}s."
    receipt = (f"Source: CFB Index — buzz ({season} mentions) vs production "
               f"({prod_season} {metric_human}) · {n} {pos}s · {conf.lower()} confidence")
    svg = editorial_card(
        eyebrow=f"{name.upper()}  ·  PERCEPTION vs THE TAPE", headline=headline,
        annotation=annotation, receipt=receipt,
        title=f"{name}: hype percentile vs production percentile among {pos}s", draw_plot=draw,
        height=420,
    )
    alt = (f"{name}: hype in the {ordinal(hx)} percentile and production in the {ordinal(py_)} "
           f"percentile among {n} {pos}s — quadrant: {quad.lower()}.")
    return {
        "svg_html": svg, "headline_finding": headline,
        "annotations": [Annotation(target=name, text=quad, reason="hype percentile vs production percentile")],
        "alt_text": alt,
    }


def _empty(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" '
                    f'font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
