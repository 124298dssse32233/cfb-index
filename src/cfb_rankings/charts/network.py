"""Directed network as a circular chord diagram (WS-08, D-007).

Locked usage (per ``docs/design-system/31-chart-vocabulary.md``): use when the
relationships *between* entities are the point — coaching carousel, transfer
flows between a cluster of programs, rivalry graphs. Do NOT use it as a
decorative "everything connects to everything" hairball.

Why a circular layout and not force-directed: a force-directed layout is
non-deterministic (seed-dependent) and needs client-side JS to settle — both
disqualifying here (the WS-11 static-SVG bar forbids JS; the build needs stable,
diffable output). Placing nodes evenly on a ring is fully deterministic, never
overlaps by construction, and stays legible at 320px for the small node counts
this chart is meant for (≤ ~20). Edges bow toward the centre as quadratic
beziers so direction and density read at a glance; an arrowhead marker encodes
source → target.

Public API:
    render_network(nodes, edges, *, title, caption, accent) -> str
    NetworkNode(id, label, weight=0.0)
    NetworkEdge(source, target, weight=1.0)
    NETWORK_CSS -> str
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from math import cos, pi, sin, sqrt
from typing import Sequence

from .annotation import Annotation, render_annotation_overlay


@dataclass(frozen=True)
class NetworkNode:
    """A node on the ring. ``weight`` is an optional sizing hint; when it is
    ``0`` the node is sized by its edge degree instead."""
    id: str
    label: str
    weight: float = 0.0


@dataclass(frozen=True)
class NetworkEdge:
    """A directed edge ``source -> target``. ``weight`` scales stroke width."""
    source: str
    target: str
    weight: float = 1.0


# viewBox geometry. Wider than tall so left/right labels have room to breathe.
_W = 420.0
_H = 360.0
_CX = 210.0
_CY = 168.0
_R = 108.0            # node ring radius
_LABEL_GAP = 12.0     # label baseline sits this far outside the ring
_NODE_MIN_R = 3.5
_NODE_MAX_R = 11.0
_EDGE_MIN_W = 1.0
_EDGE_MAX_W = 5.0
_BOW = 0.55           # 0 = straight chord, 1 = passes through centre
_ARROW_BACKOFF = 4.0  # stop the curve this far short of the target dot edge


def _layout(node_ids: list[str]) -> dict[str, tuple[float, float]]:
    """Evenly space nodes on the ring, starting at 12 o'clock, going clockwise.

    Deterministic and overlap-free by construction — the core reason this chart
    uses a ring rather than a force simulation.
    """
    pos: dict[str, tuple[float, float]] = {}
    n = len(node_ids)
    if n == 0:
        return pos
    for i, nid in enumerate(node_ids):
        theta = -pi / 2 + (2 * pi * i) / n
        pos[nid] = (_CX + _R * cos(theta), _CY + _R * sin(theta))
    return pos


def _node_radius(value: float, peak: float) -> float:
    if peak <= 0:
        return _NODE_MIN_R
    t = sqrt(max(value, 0.0) / peak)
    return _NODE_MIN_R + (_NODE_MAX_R - _NODE_MIN_R) * t


def _edge_width(weight: float, peak: float) -> float:
    if peak <= 0:
        return _EDGE_MIN_W
    t = sqrt(max(weight, 0.0) / peak)
    return _EDGE_MIN_W + (_EDGE_MAX_W - _EDGE_MIN_W) * t


def render_network(
    nodes: list[NetworkNode],
    edges: list[NetworkEdge],
    *,
    title: str | None = None,
    caption: str | None = None,
    accent: str = "#c9a24a",
    label_color: str | None = None,
    as_figure: bool = True,
    annotations: list[tuple[str, Sequence[str]]] | None = None,
) -> str:
    """Render a directed circular-chord network.

    Edges that reference an unknown node id are silently dropped (so a caller
    can pass a node allowlist without pre-filtering its edges). Returns an empty
    string when there is nothing meaningful to draw (< 2 nodes or no live
    edges), so callers can treat it like any other optional chip.

    ``label_color`` overrides the node-label fill (emitted as ``--net-label``)
    so the same renderer reads correctly on a light host page as well as the
    dark design-system surfaces it defaults to.

    ``as_figure`` (default True) returns the self-contained ``<figure>`` with
    its own title/caption. Pass ``as_figure=False`` to get just the bare
    ``<svg>`` (CSS vars applied to the svg element) so the chart can render
    through the shared ``render_chart_card`` shell without nesting figures —
    the card then owns the headline/lede/source-receipt.

    ``annotations`` attaches in-chart callouts keyed by node id: each
    ``(node_id, lines)`` pair places a shared annotation-overlay callout on that
    node's ring position so the chart self-narrates (the locked "annotation
    discipline" — the story lives on the chart). Pairs whose node id is not on
    the ring are silently dropped. The host page must ship ``ANNOTATION_CSS`` for
    the callout to render styled.
    """
    seen: set[str] = set()
    order: list[str] = []
    label_by_id: dict[str, str] = {}
    weight_by_id: dict[str, float] = {}
    for nd in nodes:
        if not nd.id or nd.id in seen:
            continue
        seen.add(nd.id)
        order.append(nd.id)
        label_by_id[nd.id] = nd.label
        weight_by_id[nd.id] = max(nd.weight, 0.0)

    live_edges = [
        e for e in edges
        if e.source in seen and e.target in seen and e.source != e.target
    ]
    if len(order) < 2 or not live_edges:
        return ""

    pos = _layout(order)

    degree: dict[str, float] = {nid: 0.0 for nid in order}
    for e in live_edges:
        w = max(e.weight, 0.0)
        degree[e.source] += w
        degree[e.target] += w

    # Node size: explicit weight if any node carries one, else edge degree.
    use_weight = any(weight_by_id[nid] > 0 for nid in order)
    size_val = weight_by_id if use_weight else degree
    size_peak = max(size_val.values()) if size_val else 0.0
    radius_by_id = {nid: _node_radius(size_val[nid], size_peak) for nid in order}

    edge_peak = max((max(e.weight, 0.0) for e in live_edges), default=0.0)

    defs = (
        '<defs>'
        f'<marker id="net-arrow" viewBox="0 0 8 8" refX="7" refY="4" '
        f'markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" '
        f'orient="auto-start-reverse">'
        f'<path d="M0,0 L8,4 L0,8 z" fill="{escape(accent)}" fill-opacity="0.8"/>'
        '</marker>'
        '</defs>'
    )

    edge_svg: list[str] = []
    for e in live_edges:
        sx, sy = pos[e.source]
        tx, ty = pos[e.target]
        # Control point bows the chord toward the ring centre.
        mx, my = (sx + tx) / 2, (sy + ty) / 2
        cx = mx + (_CX - mx) * _BOW
        cy = my + (_CY - my) * _BOW
        # Back the endpoint off so the arrowhead lands just outside the dot.
        tr = radius_by_id[e.target] + _ARROW_BACKOFF
        dx, dy = tx - cx, ty - cy
        dist = sqrt(dx * dx + dy * dy) or 1.0
        ex = tx - dx / dist * tr
        ey = ty - dy / dist * tr
        w = _edge_width(e.weight, edge_peak)
        edge_svg.append(
            f'<path class="network__edge" '
            f'd="M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}" '
            f'stroke-width="{w:.2f}" marker-end="url(#net-arrow)"/>'
        )

    node_svg: list[str] = []
    for nid in order:
        x, y = pos[nid]
        r = radius_by_id[nid]
        label = label_by_id[nid]
        # Quadrant-aware label placement so text fans outward from the ring.
        if x >= _CX + 1:
            anchor, lx = "start", x + r + _LABEL_GAP
        elif x <= _CX - 1:
            anchor, lx = "end", x - r - _LABEL_GAP
        else:
            anchor, lx = "middle", x
        ly = y + 3 if abs(x - _CX) >= 1 else (y - r - 6 if y < _CY else y + r + 12)
        aria = f"{label} ({int(round(degree[nid]))} connections)"
        node_svg.append(
            f'<g role="img" aria-label="{escape(aria)}">'
            f'<circle class="network__node" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>'
            f'<text class="network__label" x="{lx:.1f}" y="{ly:.1f}" '
            f'text-anchor="{anchor}">{escape(label)}</text>'
            f'</g>'
        )

    overlay_svg = ""
    if annotations:
        anns = [
            Annotation(pos[nid][0], pos[nid][1], lines)
            for nid, lines in annotations
            if nid in pos
        ]
        overlay_svg = render_annotation_overlay(
            anns, width=_W, height=_H, accent=accent
        )

    title_html = (
        f'<figcaption class="network__title">{escape(title)}</figcaption>'
        if title else ""
    )
    caption_html = (
        f'<p class="network__caption">{escape(caption)}</p>' if caption else ""
    )

    style = f"--net-accent:{escape(accent)}"
    if label_color:
        style += f";--net-label:{escape(label_color)}"

    aria = escape(title or "Entity relationship network")
    if not as_figure:
        # Bare SVG (CSS vars on the svg so they cascade to edges/labels) for the
        # shared chart-card shell — no figure/title/caption of its own.
        return (
            f'<svg class="network__svg" data-chart="network" style="{style}" '
            f'viewBox="0 0 {_W:.0f} {_H:.0f}" role="group" aria-label="{aria}" '
            f'preserveAspectRatio="xMidYMid meet">'
            f'{defs}{"".join(edge_svg)}{"".join(node_svg)}{overlay_svg}'
            f'</svg>'
        )

    return (
        f'<figure class="network" data-chart="network" '
        f'style="{style}">'
        f'{title_html}'
        f'<svg class="network__svg" viewBox="0 0 {_W:.0f} {_H:.0f}" '
        f'role="group" aria-label="{aria}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'{defs}'
        f'{"".join(edge_svg)}'
        f'{"".join(node_svg)}'
        f'{overlay_svg}'
        f'</svg>'
        f'{caption_html}'
        f'</figure>'
    )


NETWORK_CSS = """
/* Network (circular chord diagram) — WS-08 */
.network { margin: 0; }
.network__title {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 8px;
}
.network__svg {
  width: 100%;
  height: auto;
  max-width: 460px;
  display: block;
  overflow: visible;
}
.network__edge {
  fill: none;
  stroke: var(--net-accent, #c9a24a);
  stroke-opacity: 0.32;
}
.network__node {
  fill: var(--net-accent, #c9a24a);
  stroke: rgba(20, 20, 24, 0.85);
  stroke-width: 1;
}
.network__label {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 9px;
  font-weight: 700;
  fill: var(--net-label, var(--fg-secondary, #e9e6dc));
}
.network__caption {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 12px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 8px 0 0 0;
  max-width: 56ch;
}
"""


__all__ = [
    "render_network",
    "NetworkNode",
    "NetworkEdge",
    "NETWORK_CSS",
]
