"""Belief-family renderers — both built on the shared Editorial Grammar.

`render_fan_mood_braid`  — the Phantom Delta: belief percentile vs model percentile.
`render_home_away_mind`  — the Belonging Gap: a fanbase's mood vs the national read.

Each supplies only a dumbbell plot-field; `grammar.editorial_card` owns the
chrome (eyebrow, finding-headline, marginalia, receipt, grain, tokens). This
file proves the grammar is reusable: two different charts, one publication look.
Every displayed value comes from the query (doc 74 honesty rule).
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import text, line, circle, rect, PALETTE_CREAM, PALETTE_MUTED
from .grammar import editorial_card, cls_text, dot, ordinal, VIOLET, BLUE, GRID, SANS


def _dumbbell(px, py, pw, ph, *, xa, xb, color_a, color_b, label_a, label_b,
              gap_label, gap_color, tip_a="", tip_b="", special_x=None, special_label=None,
              ticks=()) -> list[str]:
    """Shared dumbbell geometry: a track, an optional reference tick, a shaded
    gap + connector, and two direct-labelled dots. Used by both belief charts."""
    axis_y = py + ph * 0.40
    parts: list[str] = [line(px, axis_y, px + pw, axis_y, color=GRID, width=1.0)]
    for tx in ticks:
        parts.append(line(tx, axis_y - 3, tx, axis_y + 3, color=GRID, width=1.0))
    if special_x is not None:
        parts.append(line(special_x, axis_y - 40, special_x, axis_y + 40, color=PALETTE_MUTED,
                          width=1.0, dasharray="2,3"))
        if special_label:
            parts.append(text(special_x, axis_y + 54, special_label, font_size=10, family=SANS,
                              color=PALETTE_MUTED, anchor="middle"))
    lo, hi = (min(xa, xb), max(xa, xb))
    if hi - lo > 1:
        parts.append(rect(lo, axis_y - 13, hi - lo, 26, fill=gap_color, opacity=0.12))
    parts.append(
        f'<line x1="{lo:.1f}" y1="{axis_y}" x2="{hi:.1f}" y2="{axis_y}" '
        f'stroke="{gap_color}" stroke-width="9" stroke-linecap="butt" opacity="0.85"/>'
    )
    if gap_label and hi - lo > 1:
        parts.append(text((lo + hi) / 2, axis_y + 28, gap_label, font_size=11, family=SANS,
                          weight="700", color=gap_color, anchor="middle"))
    close = abs(xa - xb) < 150
    parts.append(dot(xa, axis_y, 8, fill=color_a, stroke=PALETTE_CREAM, stroke_width=2.0, tip=tip_a)
                 if tip_a else circle(xa, axis_y, 8, fill=color_a, stroke=PALETTE_CREAM, stroke_width=2.0))
    parts.append(dot(xb, axis_y, 8, fill=color_b, stroke=PALETTE_CREAM, stroke_width=2.0, tip=tip_b)
                 if tip_b else circle(xb, axis_y, 8, fill=color_b, stroke=PALETTE_CREAM, stroke_width=2.0))
    parts.append(text(xa, axis_y - 22, label_a, font_size=11, family=SANS, weight="700",
                      color=color_a, anchor="middle"))
    parts.append(text(xb, axis_y + 44 if close else axis_y - 22, label_b, font_size=11,
                      family=SANS, weight="700", color=color_b, anchor="middle"))
    return parts


# ---------------------------------------------------------------------------
# FAN_MOOD_BRAID — belief percentile vs model percentile (the Phantom Delta)
# ---------------------------------------------------------------------------


def render_fan_mood_braid(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    s = query_result.get("summary_stats", {}) or {}
    if not s:
        return _empty("Not enough belief signal for a Phantom Delta.")

    name = s.get("team_name", "")
    bp, mp = int(s.get("belief_pctile", 0)), int(s.get("model_pctile", 0))
    spots = int(s.get("spots", 0))
    n = int(s.get("n_cohort", 0))
    zone = s.get("zone", "")
    dwow = s.get("delta_wow")
    sample = s.get("sample_size")
    conf = (query_result.get("confidence") or "unset").upper()
    bweek, pweek, season = s.get("belief_week"), s.get("power_week"), s.get("season_year", "")
    offseason = bool(s.get("is_offseason"))

    delusion = bp >= mp
    gap_color = VIOLET if delusion else BLUE
    if offseason:
        gap_label = "OFFSEASON GAP · EARLY"
    else:
        gap_label = "THE DELUSION GAP" if bp > mp else ("THE PARANOIA GAP" if mp > bp else "IN LINE")

    if offseason:
        if delusion and bp != mp:
            headline = f"Even now, {name}'s fans are higher than the model — an early read."
        elif bp != mp:
            headline = f"In the quiet months, the model is higher on {name} than its own fans."
        else:
            headline = f"{name}'s fans and the model open the offseason in step."
    else:
        # Unit-consistent with the chart's percentile axis (no rank/percentile mismatch).
        gap = bp - mp
        if gap > 0:
            headline = f"{name}'s fans rank it {gap} percentile points above the model."
        elif gap < 0:
            headline = f"The model rates {name} {abs(gap)} percentile points above its fans."
        else:
            headline = f"{name}'s fans and the model agree on where it stands."

    rows = query_result.get("rows", []) or []

    def draw(px, py, pw, ph):
        # Diagonal scatter: belief (x) vs model (y), the 45° line = "they agree".
        # The whole field is faint; the subject + the two extremes carry labels.
        gl = 16
        side = min(pw - gl - 8, ph - 26)
        fx0, fy0 = px + gl, py + 2

        def X(p):
            return fx0 + side * (max(0.0, min(100.0, p)) / 100.0)

        def Y(p):
            return fy0 + side * (1 - max(0.0, min(100.0, p)) / 100.0)

        out: list[str] = [
            # line-of-identity best practice (research 2026-06-14): shade the two
            # regions the diagonal splits — below = delusion (fans>model),
            # above = paranoia (model>fans) — so the gap's *meaning* is ambient.
            f'<polygon points="{fx0:.1f},{fy0 + side:.1f} {fx0 + side:.1f},{fy0 + side:.1f} '
            f'{fx0 + side:.1f},{fy0:.1f}" fill="{VIOLET}" opacity="0.05"/>',
            f'<polygon points="{fx0:.1f},{fy0 + side:.1f} {fx0:.1f},{fy0:.1f} '
            f'{fx0 + side:.1f},{fy0:.1f}" fill="{BLUE}" opacity="0.05"/>',
            line(fx0, fy0, fx0, fy0 + side, color=GRID, width=1.0),
            line(fx0, fy0 + side, fx0 + side, fy0 + side, color=GRID, width=1.0),
            line(fx0, fy0 + side, fx0 + side, fy0, color="#b4ad9d", width=1.2),  # agree line
        ]
        amx, amy = fx0 + side * 0.5, fy0 + side * 0.5
        out.append(f'<text x="{amx:.1f}" y="{amy - 5:.1f}" class="ed-ax" font-family="{SANS}" '
                   f'fill="#b4ad9d" text-anchor="middle" transform="rotate(-45 {amx:.1f} {amy:.1f})">'
                   f'FANS &amp; MODEL AGREE</text>')
        # territory labels (faint) — removes "is above the line good?" cognitive load
        out.append(f'<text x="{X(96):.1f}" y="{Y(8):.1f}" class="ed-zone" font-family="{SANS}" '
                   f'font-weight="700" fill="{VIOLET}" fill-opacity="0.15" text-anchor="end">DELUSION</text>')
        out.append(f'<text x="{X(4):.1f}" y="{Y(92):.1f}" class="ed-zone" font-family="{SANS}" '
                   f'font-weight="700" fill="{BLUE}" fill-opacity="0.15" text-anchor="start">PARANOIA</text>')
        out.append(cls_text(fx0 + side / 2, fy0 + side + 16, "FAN BELIEF  (percentile) →",
                            "ed-ax", family=SANS, color=PALETTE_MUTED, anchor="middle"))
        ylx, yly = px + 8, fy0 + side / 2
        out.append(f'<text x="{ylx:.1f}" y="{yly:.1f}" class="ed-ax" font-family="{SANS}" '
                   f'fill="{PALETTE_MUTED}" text-anchor="middle" transform="rotate(-90 {ylx:.1f} {yly:.1f})">'
                   f'MODEL  (percentile) →</text>')
        # the field — every other team, faint (the "landscape of hype")
        subject = None
        for r in rows:
            if r.get("subject"):
                subject = r
                continue
            if r.get("label"):  # labelled extremes are drawn darker below
                continue
            out.append(f'<circle cx="{X(r["belief"]):.1f}" cy="{Y(r["model"]):.1f}" r="2.2" '
                       f'fill="#8a8475" opacity="0.20" style="mix-blend-mode:multiply"/>')
        # the two labelled extremes — sense of scale without overplot
        for r in rows:
            if r.get("label") and not r.get("subject"):
                cx, cy = X(r["belief"]), Y(r["model"])
                out.append(dot(cx, cy, 3.2, fill="#6f6a5e",
                               tip=f"{r['label']} — fan belief {ordinal(r['belief'])}, model {ordinal(r['model'])}"))
                anc = "end" if r["belief"] >= 70 else "start"
                out.append(cls_text(cx + (-6 if anc == "end" else 6), cy + 3, str(r["label"]).split()[-1],
                                    "ed-ptlabel", family=SANS, color="#6f6a5e", anchor=anc))
        # the subject — gap connector to the agree-line, then the hero dot + label
        if subject:
            m = (subject["belief"] + subject["model"]) / 2.0
            sx, sy = X(subject["belief"]), Y(subject["model"])
            out.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{X(m):.1f}" y2="{Y(m):.1f}" '
                       f'stroke="{gap_color}" stroke-width="1.4" stroke-dasharray="3,2"/>')
            out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="11" fill="{gap_color}" opacity="0.14"/>')  # outlier halo
            out.append(dot(sx, sy, 6.0, fill=gap_color, stroke=PALETTE_CREAM, stroke_width=2.0,
                           tip=f"{name} — fan belief {ordinal(bp)}, model {ordinal(mp)} ({bp - mp:+d})"))
            anc = "end" if subject["belief"] >= 70 else "start"
            ly = sy + 18 if subject["model"] >= 86 else sy - 10
            out.append(cls_text(sx + (-10 if anc == "end" else 10), ly, f"{name}  {bp - mp:+d}",
                                "ed-ptlabel", family=SANS, weight="700", color=gap_color, anchor=anc))
        return out

    dwow_txt = ""
    if isinstance(dwow, (int, float)):
        arrow = "▲" if dwow > 0 else ("▼" if dwow < 0 else "■")
        dwow_txt = f" · {arrow}{abs(dwow):.1f} WoW"
    rank = s.get("gap_rank")
    if rank and not offseason and n:
        # Cohort scale: "is 22 points a lot?" -> where this gap ranks nationally.
        if bp - mp >= 0:
            annotation = f"▸ The {ordinal(rank)}-widest fans-over-model gap among {n} fanbases."
        else:
            annotation = f"▸ The {ordinal(n - rank + 1)}-widest model-over-fans gap among {n} fanbases."
    else:
        annotation = f"▸ Among {n} tracked fanbases — belief {zone}{dwow_txt}."
    receipt = (f"Source: CFB Index — fan belief vs the model's power rating · "
               f"{season} Wk {pweek} · n={sample} · {conf.lower()} confidence")
    svg = editorial_card(
        eyebrow=f"{name.upper()}  ·  BELIEF vs THE MODEL", headline=headline,
        annotation=annotation, receipt=receipt,
        title=f"{name}: fan belief vs model percentile across the field — the Phantom Delta",
        draw_plot=draw, height=470,
    )
    alt = (f"{name}: fan belief in the {ordinal(bp)} percentile versus the model's {ordinal(mp)} "
           f"percentile among {n} tracked teams — {gap_label.lower()} of {abs(bp - mp)} points.")
    return {
        "svg_html": svg, "headline_finding": headline,
        "annotations": [Annotation(target=name, text=gap_label, reason="belief percentile minus model percentile")],
        "alt_text": alt,
    }


# ---------------------------------------------------------------------------
# HOME_AWAY_MIND — a fanbase's mood vs the national read (the Belonging Gap)
# ---------------------------------------------------------------------------


def render_home_away_mind(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    s = query_result.get("summary_stats", {}) or {}
    if not s:
        return _empty("Not enough fan-vs-national signal yet.")

    name = s.get("team_name", "")
    fan_net = float(s.get("fan_net", 0.0))
    nat_net = float(s.get("national_net", 0.0))
    gap = float(s.get("belonging_gap", fan_net - nat_net))
    nf, nn = s.get("n_fan"), s.get("n_national")
    conf = (query_result.get("confidence") or "unset").upper()
    week, season = s.get("week"), s.get("season_year", "")

    fans_higher = fan_net >= nat_net
    gap_color = VIOLET if fans_higher else BLUE
    gap_label = "BELONGING GAP" if fan_net > nat_net else ("EVEN WE'VE COOLED" if nat_net > fan_net else "IN STEP")

    if fan_net > nat_net:
        headline = f"{name}'s own fans are warmer on the team than the nation is."
    elif nat_net > fan_net:
        headline = f"Even {name}'s fans have cooled below the national read."
    else:
        headline = f"{name}'s fanbase and the nation see it the same way."

    dom = max(0.25, max(abs(fan_net), abs(nat_net)) * 1.15)

    def draw(px, py, pw, ph):
        def x_of(v):
            return px + pw * ((max(-dom, min(dom, v)) + dom) / (2 * dom))
        return _dumbbell(
            px, py, pw, ph,
            xa=x_of(fan_net), xb=x_of(nat_net), color_a=VIOLET, color_b=BLUE,
            label_a=f"YOUR FANBASE · {fan_net:+.2f}", label_b=f"THE NATION · {nat_net:+.2f}",
            tip_a=f"Your fanbase — {fan_net:+.2f} net sentiment (n={nf})",
            tip_b=f"The nation — {nat_net:+.2f} net sentiment (n={nn})",
            gap_label=f"{gap_label} · {abs(gap):.2f}", gap_color=gap_color,
            special_x=x_of(0.0), special_label="neutral",
        )

    annotation = f"▸ A {abs(gap):.2f}-point net-sentiment gap between the fanbase and the national conversation."
    receipt = (f"Source: CFB Index — fanbase vs national discourse · "
               f"{season} Wk {week} · n={nf}/{nn} · {conf.lower()} confidence")
    svg = editorial_card(
        eyebrow=f"{name.upper()}  ·  YOUR FANBASE vs THE NATION", headline=headline,
        annotation=annotation, receipt=receipt,
        title=f"{name}: fan vs national net sentiment — the Belonging Gap", draw_plot=draw,
    )
    alt = (f"{name}: fanbase net sentiment {fan_net:+.2f} versus national {nat_net:+.2f} "
           f"in week {week} — {gap_label.lower()} of {abs(gap):.2f}.")
    return {
        "svg_html": svg, "headline_finding": headline,
        "annotations": [Annotation(target=name, text=gap_label, reason="fan minus national net sentiment")],
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
