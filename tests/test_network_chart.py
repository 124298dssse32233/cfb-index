"""Tests for the WS-08 circular-chord network renderer (chart type #9).

The renderer is pure geometry — no live data, no DB — so these assert the
invariants that make a static, no-JS network trustworthy: deterministic
overlap-free layout, edges that actually connect their declared endpoints,
graceful handling of degenerate / dirty input, and HTML escaping.
"""
from __future__ import annotations

import re
from math import hypot

from cfb_rankings.charts.network import (
    _CX,
    _CY,
    _H,
    _R,
    _W,
    NetworkEdge,
    NetworkNode,
    _layout,
    render_network,
)

_CIRCLE = re.compile(
    r'<circle class="network__node" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"'
)
_EDGE = re.compile(r'd="M([\d.]+),([\d.]+) Q[\d.]+,[\d.]+ ([\d.]+),([\d.]+)"')


def _nodes(*ids: str) -> list[NetworkNode]:
    return [NetworkNode(id=i, label=i.upper()) for i in ids]


def test_empty_renders_nothing() -> None:
    assert render_network([], []) == ""


def test_single_node_or_no_edges_renders_nothing() -> None:
    # < 2 nodes is not a network.
    assert render_network(_nodes("a"), [NetworkEdge("a", "a")]) == ""
    # 2 nodes but no live edge.
    assert render_network(_nodes("a", "b"), []) == ""


def test_layout_is_on_the_ring_and_equidistant() -> None:
    pos = _layout(["a", "b", "c", "d", "e"])
    assert len(pos) == 5
    for (x, y) in pos.values():
        assert hypot(x - _CX, y - _CY) == round(_R, 6) or abs(hypot(x - _CX, y - _CY) - _R) < 1e-6
    # First node sits at 12 o'clock (straight up from centre).
    fx, fy = pos["a"]
    assert abs(fx - _CX) < 1e-6
    assert fy < _CY


def test_nodes_stay_in_bounds() -> None:
    svg = render_network(_nodes("a", "b", "c", "d"),
                         [NetworkEdge("a", "b"), NetworkEdge("c", "d")])
    circles = _CIRCLE.findall(svg)
    assert len(circles) == 4
    for cx, cy, r in circles:
        cx, cy, r = float(cx), float(cy), float(r)
        assert 0 <= cx <= _W
        assert 0 <= cy <= _H


def test_edge_starts_at_source_center() -> None:
    # The bezier must originate exactly at the source node centre, so the line
    # visibly leaves the right dot (the arrowhead end is intentionally backed
    # off the target, so only the start is pinned to a centre).
    nodes = _nodes("a", "b", "c")
    svg = render_network(nodes, [NetworkEdge("a", "b")])
    centers = {}
    for cx, cy, _r in _CIRCLE.findall(svg):
        centers[(round(float(cx), 1), round(float(cy), 1))] = True
    edges = _EDGE.findall(svg)
    assert len(edges) == 1
    sx, sy, _ex, _ey = (round(float(v), 1) for v in edges[0])
    assert (sx, sy) in centers


def test_unknown_edge_endpoints_are_dropped() -> None:
    # An edge to a node that isn't in the allowlist must be silently ignored,
    # not crash — so callers can pass a node subset without pre-filtering edges.
    svg = render_network(
        _nodes("a", "b"),
        [NetworkEdge("a", "b"), NetworkEdge("a", "ghost"), NetworkEdge("z", "b")],
    )
    assert len(_EDGE.findall(svg)) == 1


def test_higher_degree_node_is_larger() -> None:
    # hub <- spokes: the hub has degree 3, each spoke degree 1.
    nodes = _nodes("hub", "s1", "s2", "s3")
    edges = [NetworkEdge("s1", "hub"), NetworkEdge("s2", "hub"), NetworkEdge("s3", "hub")]
    svg = render_network(nodes, edges)
    radii = {}
    # Map circle centre -> radius, then identify the hub by its layout position.
    pos = _layout(["hub", "s1", "s2", "s3"])
    hub_xy = (round(pos["hub"][0], 1), round(pos["hub"][1], 1))
    for cx, cy, r in _CIRCLE.findall(svg):
        radii[(round(float(cx), 1), round(float(cy), 1))] = float(r)
    hub_r = radii[hub_xy]
    others = [r for xy, r in radii.items() if xy != hub_xy]
    assert all(hub_r > o for o in others)


def test_labels_are_escaped() -> None:
    nodes = [NetworkNode("a", "A & <B>"), NetworkNode("b", "plain")]
    svg = render_network(nodes, [NetworkEdge("a", "b")])
    assert "A &amp; &lt;B&gt;" in svg
    assert "<B>" not in svg


def test_arrowhead_marker_present_for_direction() -> None:
    svg = render_network(_nodes("a", "b"), [NetworkEdge("a", "b")])
    assert 'id="net-arrow"' in svg
    assert 'marker-end="url(#net-arrow)"' in svg


def test_deterministic_output() -> None:
    nodes = _nodes("a", "b", "c")
    edges = [NetworkEdge("a", "b"), NetworkEdge("b", "c")]
    assert render_network(nodes, edges) == render_network(nodes, edges)


def test_as_figure_false_returns_bare_svg() -> None:
    nodes = _nodes("a", "b", "c")
    edges = [NetworkEdge("a", "b"), NetworkEdge("b", "c")]
    bare = render_network(nodes, edges, accent="#1f2c4d",
                          label_color="#1a1a1a", as_figure=False)
    # No surrounding <figure>/<figcaption> chrome — just the svg.
    assert bare.startswith("<svg")
    assert bare.rstrip().endswith("</svg>")
    assert "<figure" not in bare and "figcaption" not in bare
    # CSS vars land on the svg so edges/labels still resolve their colors.
    assert "--net-accent:#1f2c4d" in bare
    assert "--net-label:#1a1a1a" in bare
    # Still a real chart: arrowhead marker + at least one edge present.
    assert 'id="net-arrow"' in bare and "network__edge" in bare
