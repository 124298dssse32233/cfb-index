"""Shared SVG helpers for the viz_templates package.

Editorial conventions:
    * Hairline rules at 1px, color #1a1a1a.
    * Series colors come from a fixed editorial palette (gold, navy, ink).
    * Annotation captions use serif italic, 13px.
    * Each viz has a 24px top padding for the eyebrow + 24px bottom for the
      caption row.
"""
from __future__ import annotations

import html
from typing import Iterable


PALETTE_GOLD = "#c9a24a"
PALETTE_NAVY = "#1f2c4d"
PALETTE_INK = "#1a1a1a"
PALETTE_RULE = "#1a1a1a"
PALETTE_MUTED = "#7a7a7a"
PALETTE_CREAM = "#f6f1e6"


def svg_open(width: int, height: int, viewbox: tuple[int, int, int, int] | None = None) -> str:
    vb = viewbox or (0, 0, width, height)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" '
        f'style="background:transparent;font-family:Georgia,serif;">'
    )


def svg_close() -> str:
    return "</svg>"


def text(x: float, y: float, content: str, *, font_size: int = 13,
         color: str = PALETTE_INK, family: str = "Georgia,serif",
         weight: str = "normal", italic: bool = False,
         anchor: str = "start") -> str:
    style_italic = "italic" if italic else "normal"
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" '
        f'font-size="{font_size}" font-weight="{weight}" '
        f'font-style="{style_italic}" fill="{color}" '
        f'text-anchor="{anchor}">{html.escape(content)}</text>'
    )


def line(x1: float, y1: float, x2: float, y2: float, *,
         color: str = PALETTE_RULE, width: float = 1.0,
         dasharray: str | None = None) -> str:
    dash = f' stroke-dasharray="{dasharray}"' if dasharray else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{width}"{dash}/>'
    )


def circle(cx: float, cy: float, r: float, *,
           fill: str = PALETTE_INK, stroke: str | None = None,
           stroke_width: float = 1.0) -> str:
    s = f' stroke="{stroke}" stroke-width="{stroke_width}"' if stroke else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{s}/>'


def rect(x: float, y: float, w: float, h: float, *,
         fill: str = PALETTE_INK, opacity: float = 1.0) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" opacity="{opacity:.2f}"/>'
    )


def path(d: str, *, stroke: str = PALETTE_INK, stroke_width: float = 1.5,
         fill: str = "none") -> str:
    return (
        f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{stroke_width}" stroke-linejoin="round"/>'
    )


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def join(parts: Iterable[str]) -> str:
    return "".join(parts)
