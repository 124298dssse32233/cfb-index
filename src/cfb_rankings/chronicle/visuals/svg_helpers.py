"""SVG primitives for Chronicle visuals.

Thin re-export over `cfb_rankings.editions.viz_templates._common` so the
visuals package has its own import surface without duplicating SVG helpers.
The editorial palette (gold/navy/ink/muted/cream) and primitive functions
(svg_open, text, line, circle, rect, path, lerp, join) all come from there.
"""
from __future__ import annotations

from cfb_rankings.editions.viz_templates._common import (  # noqa: F401
    svg_open,
    svg_close,
    text,
    line,
    circle,
    rect,
    path,
    lerp,
    join,
    PALETTE_GOLD,
    PALETTE_NAVY,
    PALETTE_INK,
    PALETTE_MUTED,
    PALETTE_CREAM,
    PALETTE_RULE,
)
