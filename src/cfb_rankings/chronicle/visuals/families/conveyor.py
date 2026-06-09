"""Draft Pipeline Conveyor — draft capital lost by position + replacements.

Horizontal bars of round-weighted draft capital lost per position group, with
a first-rounder marker (gold) and the count of incoming portal replacements
annotated on the right. Answers "who did the draft take, and who's left to
replace them?" (research 2026-05-25, fan interest #10).
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


def render_draft_pipeline_conveyor(
    query_result: dict[str, Any],
    spec_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})

    if not rows:
        return _empty_render("No NFL draft picks for this program.")

    draft_year = summary.get("draft_year", "")
    width = 600
    row_h = 38
    top_pad = 64
    bottom_pad = 34
    height = top_pad + bottom_pad + row_h * len(rows)

    parts: list[str] = []
    sr_title = (
        f"Draft Pipeline Conveyor — {draft_year} NFL draft capital lost by "
        f"position, with portal replacements"
    )
    parts.append(svg_open(width, height, title=sr_title))
    parts.append(rect(0, 0, width, height, fill=PALETTE_CREAM))

    parts.append(text(20, 28, "Draft Pipeline Conveyor", font_size=16, weight="700"))
    parts.append(text(
        20, 48,
        f"{draft_year} draft capital lost by position · portal replacements",
        font_size=12, color=PALETTE_MUTED, italic=True,
    ))

    max_cap = max((r["capital"] for r in rows), default=1) or 1
    bar_x0 = 70
    bar_x1 = width - 150
    bar_w = bar_x1 - bar_x0

    for i, r in enumerate(rows):
        y = top_pad + row_h * i + row_h / 2
        cap = r["capital"]
        w = (cap / max_cap) * bar_w
        is_first = r.get("first_rounder")
        color = PALETTE_GOLD if is_first else PALETTE_NAVY
        # Position label
        parts.append(text(20, y + 5, r["position"], font_size=13, weight="700"))
        # Capital bar
        parts.append(rect(bar_x0, y - 9, w, 18, fill=color, opacity=0.9))
        # Picks count inside/after bar
        parts.append(text(
            bar_x0 + w + 6, y + 5,
            f"{r['picks']} pick{'s' if r['picks'] != 1 else ''}",
            font_size=11, color=PALETTE_INK, family="ui-monospace,Menlo,monospace",
        ))
        # Replacement annotation on the right rail
        repl = r.get("incoming_replacements", 0)
        if repl > 0:
            repl_txt = f"+{repl} portal"
            repl_color = PALETTE_INK
        else:
            repl_txt = "no portal repl"
            repl_color = "#b3402f"  # exposed
        parts.append(text(
            width - 12, y + 5, repl_txt,
            font_size=11, color=repl_color, anchor="end", italic=(repl == 0),
        ))

    # Footer
    exposed = summary.get("exposed_position")
    footer = f"{summary.get('total_picks', 0)} drafted · {summary.get('total_capital', 0)} capital units"
    if exposed:
        footer += f" · exposed at {exposed}"
    parts.append(text(20, height - 10, footer, font_size=11, color=PALETTE_MUTED, italic=True))

    parts.append(svg_close())
    svg = join(parts)

    headline = _headline(rows, summary)
    annotations: list[Annotation] = []
    if summary.get("exposed_position"):
        annotations.append(Annotation(
            target=summary["exposed_position"],
            text=f"{summary['exposed_position']}: draft loss, no portal answer",
            reason="position lost draft capital with zero incoming transfers",
        ))

    alt_text = (
        f"Draft Pipeline Conveyor: {summary.get('total_picks', 0)} {draft_year} NFL "
        f"draft picks lost across {len(rows)} position groups; "
        f"most at {summary.get('top_position', '?')}."
    )
    return {
        "svg_html": svg,
        "headline_finding": headline,
        "annotations": annotations,
        "alt_text": alt_text,
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
        return f"{top} took the biggest {dy} draft hit ({top_n} picks) — reload watch is on."
    player_word = "player" if n == 1 else "players"
    return f"{n} {player_word} drafted in {dy}; the roster reload runs through the portal and recruiting."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
