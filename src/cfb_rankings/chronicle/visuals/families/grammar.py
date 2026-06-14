"""The Editorial Chart Grammar — shared render chrome (design-system 77).

`editorial_card` owns the constant anatomy every chart inherits: eyebrow,
serif finding-headline, marginalia annotation, and the mono credit line — plus
the token palette and the MOBILE type scale. A family supplies ONLY a
`draw_plot(x, y, w, h) -> list[str]` closure that renders its geometry into the
plot field. Implement the grammar once here; every family inherits it (doc 77
§6). All displayed values come from the query, never from prose.

Mobile (doc 77 §5): one responsive SVG, no dual-render. An embedded `<style>`
sizes text by class and bumps the small text under `@media (max-width:640px)`
so the chart stays legible at ~330px. Families label text with the shared
classes (`ed-ax`, `ed-zone`, `ed-ptlabel`) via `cls_text()` to opt in.
"""
from __future__ import annotations

import html
from typing import Callable

from ..svg_helpers import (
    svg_open,
    svg_close,
    text,
    rect,
    join,
    PALETTE_INK,
    PALETTE_MUTED,
    PALETTE_CREAM,
)

# Semantic tokens (doc 77 §3): belief = violet, model/national = blue, grays recede.
VIOLET = "#6d4ac9"
BLUE = "#2f6fdb"
GRID = "#dcd6c7"
INK = PALETTE_INK
# Darker than the design-system muted (#7a7a7a, only ~3.8:1 on cream) so small
# axis/credit text clears WCAG AA 4.5:1 (research/audit 2026-06-14).
MUTED = "#5b5b5b"
CREAM = PALETTE_CREAM
# Colour-blind-safe diverging pair (Okabe-Ito) for +/- · up/down · in/out.
# RESEARCH 2026-06-14: avoid red/green (RdGn) for diverging data — Datawrapper
# colourblindness guide + Okabe-Ito (Nature Methods). Blue vs vermillion stays
# distinguishable across all common CVD types.
POS = "#0072B2"   # positive / gain / in / up
NEG = "#D55E00"   # negative / loss / out / down
# Design-system fonts FIRST, web-safe fallback last (the page loads the webfonts
# per the design tokens; Georgia is only a graceful fallback, never the intent).
SERIF = "'Source Serif Pro',Georgia,serif"
SANS = "Inter,'Helvetica Neue',Arial,sans-serif"
MONO = "'IBM Plex Mono',ui-monospace,Menlo,monospace"


# Mobile type scale — base sizes + a single breakpoint that bumps the small
# text (and hides the faintest clutter) so the chart survives ~330px phones.
_STYLE = (
    "<style>"
    # --- type scale ---
    ".ed-eyebrow{font-size:11px}.ed-headline{font-size:19px}"
    ".ed-annot{font-size:12px}.ed-receipt{font-size:11px}"
    ".ed-ax{font-size:9px}.ed-zone{font-size:15px}.ed-ptlabel{font-size:11px}"
    # --- entrance motion: scroll-driven reveal (2026 universal, zero-JS), with
    # an on-load fallback where view() is unsupported (research 2026-06-14) ---
    "@keyframes ed-rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
    ".ed-anim{animation:ed-rise .6s ease-out both}"
    "@supports (animation-timeline:view()){.ed-anim{animation-timeline:view();animation-range:entry 0% cover 35%}}"
    # --- interactivity: data points highlight on hover/focus (zero-JS) ---
    ".ed-dot{transition:stroke-width .12s ease;cursor:pointer}"
    ".ed-dot:hover,.ed-dot:focus{stroke:#1a1a1a;stroke-width:2px;outline:none}"
    # --- mobile type scale ---
    "@media (max-width:640px){"
    ".ed-eyebrow{font-size:15px}.ed-headline{font-size:24px}"
    ".ed-annot{font-size:16px}.ed-receipt{font-size:14px}"
    ".ed-ax{font-size:14px}.ed-zone{font-size:21px}.ed-ptlabel{font-size:15px}"
    "}"
    # --- accessibility: honor reduced-motion ---
    "@media (prefers-reduced-motion:reduce){.ed-anim{animation:none}}"
    "</style>"
)


def dot(cx: float, cy: float, r: float, *, fill: str, tip: str, stroke: str | None = None,
        stroke_width: float = 1.5, opacity: float | None = None) -> str:
    """An interactive data point: highlights on hover/focus (CSS), keyboard-
    focusable, with a native `<title>` tooltip (the zero-JS floor) AND a
    `data-tip` the page tooltip script enhances for touch/styling. Use for the
    meaningful points (subject + labelled peers), not the faint field."""
    s = f' stroke="{stroke}" stroke-width="{stroke_width}"' if stroke else ''
    op = f' opacity="{opacity}"' if opacity is not None else ''
    t = html.escape(tip)
    return (f'<circle class="ed-dot" cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{s}{op} '
            f'tabindex="0" role="img" data-tip="{t}"><title>{t}</title></circle>')


def cls_text(x: float, y: float, content: str, cls: str, *, family: str, color: str,
             weight: str = "normal", anchor: str = "start", italic: bool = False,
             opacity: float | None = None) -> str:
    """A <text> whose size comes from its CSS class (so the `<style>` media query
    can restyle it on mobile). Use for any text that must reflow on phones."""
    st = ' font-style="italic"' if italic else ''
    op = f' fill-opacity="{opacity}"' if opacity is not None else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-family="{family}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{st}{op}>'
            f'{html.escape(content)}</text>')


def ordinal(n: int) -> str:
    n = int(round(n))
    suf = "th" if 10 <= (n % 100) <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def editorial_card(
    *,
    eyebrow: str,
    headline: str,
    annotation: str,
    receipt: str,
    title: str,
    draw_plot: Callable[[float, float, float, float], list[str]],
    width: int = 640,
    height: int = 340,
    animate: bool = True,
) -> str:
    """Assemble one editorial card. `draw_plot(px, py, pw, ph)` renders the
    family geometry into the plot field; everything else is shared chrome.

    `animate` adds a scroll-driven entrance reveal. **Default ON** (owner
    decision 2026-06-14). It is `prefers-reduced-motion`-safe and a family may
    set `animate=False` for a data type where motion would not help; the gate
    enforces correctness only when motion is present."""
    ML, MR, MT, MB = 56, 56, 92, 60
    px, py = ML, MT
    pw, ph = width - ML - MR, height - MT - MB

    # Accessibility: role="img" collapses the SVG to one node, so screen readers
    # hear ONLY <title>+<desc>, never the visible text. Make the title the FINDING
    # and the desc carry the context + provenance (audit 2026-06-14).
    _desc = f"{annotation.lstrip('▸').strip()} {receipt}".strip()
    parts: list[str] = [
        svg_open(width, height, title=headline, desc=_desc),
        _STYLE,  # mobile type scale (doc 77 §5)
        # clean paper — no grain, no stamp (Upshot restraint: authority comes
        # from the rigor of the sourcing, not decoration).
        rect(0, 0, width, height, fill=CREAM),
        # eyebrow (mono caps) — the only top-line metadata
        cls_text(ML, 38, eyebrow, "ed-eyebrow", family=MONO, color=MUTED, weight="700"),
        # headline = the finding (serif)
        cls_text(ML, 66, headline, "ed-headline", family=SERIF, weight="700", color=INK),
    ]
    # the plot/data reveals on scroll-into-view (.ed-anim); chrome stays immediate
    plot = "".join(draw_plot(px, py, pw, ph))
    parts.append(f'<g class="ed-anim">{plot}</g>' if animate else plot)
    # marginalia annotation (the storyteller) + human credit line
    parts.append(cls_text(ML, height - 40, annotation, "ed-annot", family=SERIF, italic=True, color=INK))
    parts.append(cls_text(ML, height - 18, receipt, "ed-receipt", family=MONO, color=MUTED))
    parts.append(svg_close())
    return join(parts)
