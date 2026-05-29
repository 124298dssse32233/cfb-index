"""In-chart annotation overlay DSL (WS-08, D-007).

The locked chart vocabulary (``docs/design-system/31-chart-vocabulary.md`` —
"Annotation discipline" and the Annotated Line type) requires that the story of
a chart lives *on* the chart, not in a caption: a marker on the notable point, a
short leader to a label box of 2-3 lines, readable from the chart alone.

Every chart that wants annotations was rolling its own ad-hoc dot+label markup
(see ``team_pages/game_recap_hero.py``). This module is the one shared overlay
so the NYT-Upshot callout looks identical everywhere and stays governable.

It is coordinate-space agnostic: callers convert data points to pixel positions
in their own ``viewBox`` and hand us those pixels. We return a self-contained
``<g>`` fragment (NOT a whole ``<svg>``) so it drops straight into an existing
chart's SVG. Placement is deterministic and collision-aware — label boxes are
clamped inside the plot rect and nudged off each other — so the output is
stable and unit-testable with no live data.

Static SVG only (no JS, no hover): satisfies the WS-11 static-fallback bar and
stays legible at 320px.

Public API:
    Annotation(x, y, lines, *, placement="auto")
    render_annotation_overlay(annotations, *, width, height, accent) -> str
    ANNOTATION_CSS -> str
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable, Sequence

# Geometry constants (user units == pixels in the host viewBox).
_CHAR_W = 6.0          # avg glyph advance at 11px sans-serif
_LINE_H = 14.0         # label line height
_BOX_PAD_X = 7.0
_BOX_PAD_Y = 6.0
_LEADER = 12.0         # gap between the marked point and its label box
_MARGIN = 4.0          # min gap enforced between boxes / box and edge
_DOT_R = 3.5
_MAX_LINES = 3         # spec: 2-3 lines max per annotation

_Placement = ("above-right", "above-left", "below-right", "below-left")


@dataclass
class Annotation:
    """One callout: marker at ``(x, y)`` (pixels) with up to 3 lines of label.

    ``placement`` forces a corner ("above-right" etc.); "auto" lets the layout
    pick the first non-overlapping, in-bounds corner.
    """

    x: float
    y: float
    lines: Sequence[str]
    placement: str = "auto"


@dataclass
class _Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h


def _measure(lines: Sequence[str]) -> tuple[float, float]:
    longest = max((len(s) for s in lines), default=0)
    w = longest * _CHAR_W + 2 * _BOX_PAD_X
    h = len(lines) * _LINE_H + 2 * _BOX_PAD_Y
    return w, h


def _corner_box(px: float, py: float, w: float, h: float, placement: str) -> _Box:
    """Box top-left for a given corner placement, before clamping."""
    if placement == "above-right":
        return _Box(px + _LEADER, py - _LEADER - h, w, h)
    if placement == "above-left":
        return _Box(px - _LEADER - w, py - _LEADER - h, w, h)
    if placement == "below-right":
        return _Box(px + _LEADER, py + _LEADER, w, h)
    # below-left
    return _Box(px - _LEADER - w, py + _LEADER, w, h)


def _clamp(box: _Box, width: float, height: float) -> _Box:
    x = min(max(box.x, _MARGIN), max(_MARGIN, width - _MARGIN - box.w))
    y = min(max(box.y, _MARGIN), max(_MARGIN, height - _MARGIN - box.h))
    return _Box(x, y, box.w, box.h)


def _overlaps(a: _Box, b: _Box, margin: float = _MARGIN) -> bool:
    return not (
        a.right + margin <= b.x
        or b.right + margin <= a.x
        or a.bottom + margin <= b.y
        or b.bottom + margin <= a.y
    )


def _nearest_corner(px: float, py: float, box: _Box) -> tuple[float, float]:
    """Leader anchor: the box corner/edge closest to the marked point."""
    cx = min(max(px, box.x), box.right)
    cy = min(max(py, box.y), box.bottom)
    return cx, cy


def _place(
    px: float, py: float, w: float, h: float, placement: str,
    width: float, height: float, placed: list[_Box],
) -> _Box:
    """Choose a clamped, ideally non-overlapping box for one annotation."""
    order = (placement,) if placement in _Placement else _Placement
    fallback: _Box | None = None
    for corner in order:
        box = _clamp(_corner_box(px, py, w, h, corner), width, height)
        if fallback is None:
            fallback = box
        if not any(_overlaps(box, p) for p in placed):
            return box
    # Every corner collided — nudge the fallback vertically until it clears or
    # we run out of room. Deterministic: try down first, then up.
    assert fallback is not None
    for direction in (1, -1):
        box = _Box(fallback.x, fallback.y, w, h)
        for _ in range(40):
            if not any(_overlaps(box, p) for p in placed):
                return _clamp(box, width, height)
            box = _Box(box.x, box.y + direction * (_LINE_H / 2), w, h)
            if box.y < _MARGIN or box.bottom > height - _MARGIN:
                break
    return fallback


def render_annotation_overlay(
    annotations: Iterable[Annotation],
    *,
    width: float,
    height: float,
    accent: str = "#c9a24a",
) -> str:
    """Return a ``<g class="chart-annotations">`` overlay fragment.

    ``width``/``height`` are the host chart's viewBox dimensions; annotation
    ``(x, y)`` must already be in that pixel space. Returns ``""`` when there is
    nothing to draw, so callers treat it like any other optional layer.
    """
    anns = [a for a in annotations if a.lines and any(s.strip() for s in a.lines)]
    if not anns or width <= 0 or height <= 0:
        return ""

    placed: list[_Box] = []
    parts: list[str] = []
    for ann in anns:
        lines = [s for s in list(ann.lines)[:_MAX_LINES] if s.strip()]
        bw, bh = _measure(lines)
        box = _place(ann.x, ann.y, bw, bh, ann.placement, width, height, placed)
        placed.append(box)

        lx, ly = _nearest_corner(ann.x, ann.y, box)
        text_spans = []
        for i, line in enumerate(lines):
            ty = box.y + _BOX_PAD_Y + _LINE_H * (i + 1) - 3
            text_spans.append(
                f'<text x="{box.x + _BOX_PAD_X:.1f}" y="{ty:.1f}" '
                f'class="chart-ann__text">{escape(line)}</text>'
            )
        parts.append(
            f'<g class="chart-ann">'
            f'<line class="chart-ann__leader" x1="{ann.x:.1f}" y1="{ann.y:.1f}" '
            f'x2="{lx:.1f}" y2="{ly:.1f}"/>'
            f'<circle class="chart-ann__dot" cx="{ann.x:.1f}" cy="{ann.y:.1f}" r="{_DOT_R}"/>'
            f'<rect class="chart-ann__box" x="{box.x:.1f}" y="{box.y:.1f}" '
            f'width="{box.w:.1f}" height="{box.h:.1f}" rx="3"/>'
            f'{"".join(text_spans)}'
            f'</g>'
        )

    return (
        f'<g class="chart-annotations" style="--ann-accent:{escape(accent)}">'
        f'{"".join(parts)}</g>'
    )


ANNOTATION_CSS = """
/* In-chart annotation overlay — WS-08 (NYT-Upshot callout) */
.chart-ann__leader {
  stroke: var(--ann-accent, #c9a24a);
  stroke-width: 1;
  stroke-opacity: 0.7;
}
.chart-ann__dot {
  fill: var(--ann-accent, #c9a24a);
  stroke: #fff;
  stroke-width: 1.5;
}
.chart-ann__box {
  fill: rgba(20, 20, 24, 0.92);
  stroke: var(--ann-accent, #c9a24a);
  stroke-opacity: 0.45;
  stroke-width: 1;
}
.chart-ann__text {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 11px;
  fill: #e9e6dc;
}
"""


__all__ = ["Annotation", "render_annotation_overlay", "ANNOTATION_CSS"]
