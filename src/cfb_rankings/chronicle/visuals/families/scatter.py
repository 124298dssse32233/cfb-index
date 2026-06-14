"""Annotated scatter / quadrant family — migrated onto the Editorial Grammar.

Two visuals share this geometry:
    - CFP Bubble Wall: x=resume percentile, y=power percentile
    - Talent Yield Curve: x=talent rank percentile, y=draft yield rate

Both render through `grammar.editorial_card` (doc 77): finding-headline, human
receipt, design fonts, mobile type scale, scroll-driven entrance, and
interactive points. Quadrant-scatter best practice (web research 2026-06-13/14
— europa.eu data-viz guide on labelling scatters; Visier 2x2 scatter): selective
labelling (subject + a few peers), quadrant reference + corner labels, highlight
the one point — all preserved, now on the shared chrome.
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import line, join  # noqa: F401
from .grammar import editorial_card, cls_text, dot, VIOLET, GRID, SANS, MUTED, CREAM

FIELD = "#bfb9ab"   # the recede-into-background field
PEER = "#8a8475"    # labelled peers, a touch darker


def _render_scatter_core(
    rows: list[dict[str, Any]],
    *,
    eyebrow: str,
    headline: str,
    x_label: str,
    y_label: str,
    highlight_slug: str | None,
    sr_title: str,
    annotation: str,
    receipt: str,
    annotations: list[Annotation],
) -> dict[str, Any]:
    if not rows:
        return _empty_render("No data available.")

    def draw(px, py, pw, ph):
        gl = 32
        side = min(pw - gl - 8, ph - 26)
        fx0, fy0 = px + gl, py + 2

        def X(v):
            return fx0 + side * max(0.0, min(1.0, float(v)))

        def Y(v):
            return fy0 + side * (1.0 - max(0.0, min(1.0, float(v))))

        out: list[str] = [
            line(fx0, fy0, fx0, fy0 + side, color=GRID, width=1.0),
            line(fx0, fy0 + side, fx0 + side, fy0 + side, color=GRID, width=1.0),
            line(X(0.5), fy0, X(0.5), fy0 + side, color=MUTED, width=1.0, dasharray="2,3"),
            line(fx0, Y(0.5), fx0 + side, Y(0.5), color=MUTED, width=1.0, dasharray="2,3"),
        ]
        out.append(cls_text(fx0 + side / 2, fy0 + side + 16, x_label + " →", "ed-ax",
                            family=SANS, color=MUTED, anchor="middle"))
        ylx, yly = px + 8, fy0 + side / 2
        out.append(f'<text x="{ylx:.1f}" y="{yly:.1f}" class="ed-ax" font-family="{SANS}" '
                   f'fill="{MUTED}" text-anchor="middle" transform="rotate(-90 {ylx:.1f} {yly:.1f})">'
                   f'{html.escape(y_label)} →</text>')

        subject = None
        for r in rows:
            if highlight_slug and r.get("slug") == highlight_slug:
                subject = r
                continue
            if r.get("peer_label"):
                continue
            out.append(f'<circle cx="{X(r.get("x", 0.5)):.1f}" cy="{Y(r.get("y", 0.5)):.1f}" '
                       f'r="2.4" fill="{FIELD}" opacity="0.22" style="mix-blend-mode:multiply"/>')
        for r in rows:
            if r.get("peer_label") and not (highlight_slug and r.get("slug") == highlight_slug):
                cx, cy = X(r.get("x", 0.5)), Y(r.get("y", 0.5))
                lab = str(r.get("label", ""))
                out.append(dot(cx, cy, 4.0, fill=PEER,
                               tip=f"{lab} — {int(float(r.get('x', 0)) * 100)} / {int(float(r.get('y', 0)) * 100)} pctile"))
                anc = "end" if float(r.get("x", 0.5)) >= 0.72 else "start"
                out.append(cls_text(cx + (-6 if anc == "end" else 6), cy + 3, lab[:16],
                                    "ed-ptlabel", family=SANS, color=PEER, anchor=anc))
        if subject:
            cx, cy = X(subject.get("x", 0.5)), Y(subject.get("y", 0.5))
            lab = str(subject.get("label", ""))
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="{VIOLET}" opacity="0.14"/>')
            out.append(dot(cx, cy, 6.5, fill=VIOLET, stroke=CREAM, stroke_width=2.0,
                           tip=f"{lab} — {int(float(subject.get('x', 0)) * 100)} / {int(float(subject.get('y', 0)) * 100)} pctile"))
            anc = "end" if float(subject.get("x", 0.5)) >= 0.72 else "start"
            ly = cy + 18 if float(subject.get("y", 0.5)) >= 0.86 else cy - 11
            out.append(cls_text(cx + (-10 if anc == "end" else 10), ly, lab,
                                "ed-ptlabel", family=SANS, weight="700", color=VIOLET, anchor=anc))
        return out

    svg = editorial_card(eyebrow=eyebrow, headline=headline, annotation=annotation,
                         receipt=receipt, title=sr_title, draw_plot=draw, height=460)
    return {
        "svg_html": svg,
        "headline_finding": headline,
        "annotations": annotations,
        "alt_text": sr_title + " — " + headline,
    }


# ---------------------------------------------------------------------------
# CFP Bubble Wall
# ---------------------------------------------------------------------------


def render_cfp_bubble_wall(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    highlight_slug = summary.get("anchor_slug")
    season = summary.get("season_year", "")
    week = summary.get("snapshot_week", "?")
    conf = (query_result.get("confidence") or "unset")
    if not rows:
        return _empty_render("No CFP-window rankings for this snapshot.")

    sr_title = (f"CFP Bubble Wall — {season} week {week}: résumé rating vs power rating "
                f"percentiles for the at-large field")
    headline = _headline_for_cfp_wall(rows, summary, highlight_slug)
    anchor_row = next((r for r in rows if r.get("slug") == highlight_slug), None) if highlight_slug else None
    name = (anchor_row or {}).get("label") or "The at-large field"

    annotations: list[Annotation] = []
    if highlight_slug:
        annotations.append(Annotation(target=highlight_slug,
                                      text=_anchor_position_label(rows, highlight_slug),
                                      reason="anchor team CFP position"))
    if anchor_row:
        annotation = (f"▸ Résumé {int(float(anchor_row.get('x', 0)) * 100)}th vs model "
                      f"{int(float(anchor_row.get('y', 0)) * 100)}th among {len(rows)} at-large teams.")
    else:
        annotation = f"▸ The {len(rows)}-team at-large field by résumé and model strength."

    receipt = (f"Source: CFB Index — committee résumé vs model power · {season} Wk {week} · "
               f"{len(rows)} teams · {conf} confidence")
    return _render_scatter_core(
        rows, eyebrow=f"{name.upper()}  ·  CFP BUBBLE WALL", headline=headline,
        x_label="Résumé (committee case)", y_label="Power (model)",
        highlight_slug=highlight_slug, sr_title=sr_title, annotation=annotation,
        receipt=receipt, annotations=annotations,
    )


def _headline_for_cfp_wall(rows: list[dict], summary: dict, anchor: str | None) -> str:
    if not anchor:
        return "The at-large CFP field plotted by résumé against model strength."
    anchor_row = next((r for r in rows if r.get("slug") == anchor), None)
    if not anchor_row:
        return "Anchor team not in the CFP at-large field this snapshot."
    x = float(anchor_row.get("x", 0.5))
    y = float(anchor_row.get("y", 0.5))
    name = anchor_row.get("label") or anchor
    if x > 0.65 and y > 0.65:
        return f"{name} clears both the committee case and the model — in the bracket on every read."
    if x < 0.4 and y > 0.65:
        return f"{name} models like a contender but the résumé is sitting near the cut line."
    if x > 0.65 and y < 0.4:
        return f"{name} has the résumé the committee wants — the model says it might be borrowed."
    return f"{name} sits in the bubble zone where one bad result tips the bracket either way."


def _anchor_position_label(rows: list[dict], anchor: str) -> str:
    r = next((r for r in rows if r.get("slug") == anchor), None)
    if not r:
        return ""
    return f"{r.get('label', anchor)}: résumé {int(float(r.get('x', 0)) * 100)}P, power {int(float(r.get('y', 0)) * 100)}P"


# ---------------------------------------------------------------------------
# Talent Yield Curve
# ---------------------------------------------------------------------------


def render_talent_yield_curve(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    highlight_slug = summary.get("anchor_slug")
    season = summary.get("season_year", "")
    conf = (query_result.get("confidence") or "unset")
    if not rows:
        return _empty_render("No talent / draft data for this snapshot.")

    sr_title = (f"Talent Yield Curve — {season}: recruiting talent rank vs draft-pick yield "
                f"across FBS programs")
    headline = _headline_for_talent_yield(rows, summary, highlight_slug)
    anchor_row = next((r for r in rows if r.get("slug") == highlight_slug), None) if highlight_slug else None
    name = (anchor_row or {}).get("label") or "FBS programs"

    annotations: list[Annotation] = []
    if anchor_row:
        annotations.append(Annotation(target=highlight_slug,
                                      text=f"{name} yield position",
                                      reason="anchor team talent-to-draft yield"))
        annotation = (f"▸ Talent {int(float(anchor_row.get('x', 0)) * 100)}th, draft yield "
                      f"{int(float(anchor_row.get('y', 0)) * 100)}th among {len(rows)} programs.")
    else:
        annotation = f"▸ Recruit talent vs draft yield across {len(rows)} FBS programs."

    receipt = (f"Source: CFB Index — recruit talent vs draft-pick yield · {season} · "
               f"{len(rows)} programs · {conf} confidence")
    return _render_scatter_core(
        rows, eyebrow=f"{name.upper()}  ·  TALENT YIELD", headline=headline,
        x_label="Recruit talent (percentile)", y_label="Draft yield (percentile)",
        highlight_slug=highlight_slug, sr_title=sr_title, annotation=annotation,
        receipt=receipt, annotations=annotations,
    )


def _headline_for_talent_yield(rows: list[dict], summary: dict, anchor: str | None) -> str:
    if not anchor:
        return "Recruit-talent rank vs draft-yield rate across FBS programs."
    anchor_row = next((r for r in rows if r.get("slug") == anchor), None)
    if not anchor_row:
        return "Anchor program has no draft-yield snapshot for this window."
    x = float(anchor_row.get("x", 0.5))
    y = float(anchor_row.get("y", 0.5))
    name = anchor_row.get("label") or anchor
    if y > x + 0.15:
        return f"{name} converts recruit talent into draft picks better than its class rank suggests."
    if x > y + 0.15:
        return f"{name} signs higher-rated classes than its draft yield delivers."
    return f"{name} sits where recruit talent and draft yield largely match."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" '
                    f'font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
