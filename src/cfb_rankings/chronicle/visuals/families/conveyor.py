"""Draft Pipeline Conveyor — draft capital lost by position + portal answers.

Migrated onto the Editorial Grammar (doc 77). Horizontal capital bars per
bar/lollipop best practice (web research 2026-06-14 — Domo "Lollipop Charts";
3iap): zero baseline, descending by capital (query-ordered), direct tip labels,
first-rounder highlighted, portal-replacement read on the right rail,
interactive bars. Keeps the "who's exposed?" finding-headline.
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from .grammar import editorial_card, cls_text, VIOLET, BLUE, SANS, MONO, MUTED, INK, NEG

EXPOSED = NEG  # colour-blind-safe vermillion


def render_draft_pipeline_conveyor(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    if not rows:
        return _empty_render("No NFL draft picks for this program.")

    draft_year = summary.get("draft_year", "")
    headline = _headline(rows, summary)
    height = 152 + 30 * len(rows)
    max_cap = max((float(r["capital"]) for r in rows), default=1.0) or 1.0

    def draw(px, py, pw, ph):
        n = len(rows)
        row_h = ph / n
        bar_x0 = px + 52
        bar_x1 = px + pw - 132
        bw = bar_x1 - bar_x0
        out: list[str] = []
        for i, r in enumerate(rows):
            yc = py + row_h * i + row_h / 2
            cap = float(r["capital"])
            w = (cap / max_cap) * bw
            is_first = bool(r.get("first_rounder"))
            col = VIOLET if is_first else BLUE
            out.append(cls_text(px, yc + 4, r["position"], "ed-ax", family=SANS, color=INK, weight="700"))
            picks = r["picks"]
            t = f"{r['position']}: {picks} pick{'s' if picks != 1 else ''}" + (" · first-rounder" if is_first else "")
            out.append(f'<rect class="ed-dot" x="{bar_x0:.1f}" y="{yc - 9:.1f}" width="{w:.1f}" '
                       f'height="18" rx="2" fill="{col}" opacity="0.9" tabindex="0" data-tip="{html.escape(t)}">'
                       f'<title>{html.escape(t)}</title></rect>')
            out.append(cls_text(bar_x0 + w + 6, yc + 4, f"{picks} pick{'s' if picks != 1 else ''}",
                                "ed-ptlabel", family=MONO, color=INK))
            repl = r.get("incoming_replacements", 0)
            if repl > 0:
                out.append(cls_text(px + pw, yc + 4, f"+{repl} portal", "ed-ptlabel",
                                    family=SANS, color=INK, anchor="end"))
            else:
                out.append(cls_text(px + pw, yc + 4, "no portal answer", "ed-ptlabel",
                                    family=SANS, color=EXPOSED, anchor="end", italic=True))
        return out

    exposed = summary.get("exposed_position")
    bits = [f"{summary.get('total_picks', 0)} drafted · {summary.get('total_capital', 0)} capital units"]
    if exposed:
        bits.append(f"exposed at {exposed}")
    conf = (query_result.get("confidence") or "unset")
    receipt = (f"Source: CFB Index — round-weighted draft capital lost by position + portal answers · "
               f"{draft_year} · {conf} confidence")
    svg = editorial_card(
        eyebrow=f"NFL DRAFT  ·  {draft_year}", headline=headline,
        annotation="▸ " + " · ".join(bits) + ".", receipt=receipt,
        title=f"Draft Pipeline Conveyor — {draft_year} draft capital lost by position",
        draw_plot=draw, height=height,
    )
    annotations: list[Annotation] = []
    if exposed:
        annotations.append(Annotation(target=exposed, text=f"{exposed}: draft loss, no portal answer",
                                      reason="position lost draft capital with zero incoming transfers"))
    return {
        "svg_html": svg, "headline_finding": headline, "annotations": annotations,
        "alt_text": (f"Draft Pipeline Conveyor: {summary.get('total_picks', 0)} {draft_year} NFL picks "
                     f"lost across {len(rows)} position groups; most at {summary.get('top_position', '?')}."),
    }


def _headline(rows: list[dict], summary: dict) -> str:
    n = summary.get("total_picks", 0)
    if n == 0:
        return "No NFL draft departures this cycle."
    top = summary.get("top_position")
    top_n = summary.get("top_position_picks", 0)
    exposed = summary.get("exposed_position")
    dy = summary.get("draft_year", "")
    if exposed:
        return f"The {dy} draft hit {exposed} hardest — and the portal hasn't replaced it yet."
    if summary.get("top_position_first_rounder") and top:
        return f"A first-rounder gone at {top} headlines {n} {dy} draft departures to replace."
    if top and top_n >= 2:
        return f"{top} took the biggest {dy} draft hit ({top_n} picks) — the reload watch is on."
    player_word = "player" if n == 1 else "players"
    return f"{n} {player_word} drafted in {dy}; the reload runs through the portal and recruiting."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" '
                    f'font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
