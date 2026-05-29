"""Centralised chart vocabulary (WS-08, D-007).

All chart renderers live here so the locked vocabulary stays governable. That
invariant is enforced by ``tests/test_chart_governance.py``: a chart-type
renderer defined outside this package fails the build unless it is registered
as inline-and-pending-migration. Each renderer returns a self-contained,
server-side SVG string (no JS required) so charts satisfy the WS-11
static-SVG-fallback bar.

Locked types (9): Percentile Bar, Trajectory Spark, Bump Chart, Annotated
Line, Small Multiples, Heatmap (the original 6, rendered inline across
modules today) + Sankey, Choropleth, Network (the 3 expansion types). This
package houses the centralised renderers — Choropleth, the Annotation overlay
(which delivers the Annotated Line type), and the Network chord diagram. The
original-6 inline renderers migrate here as they are refactored to the shared
component (their migration debt is tracked in
``tests/test_chart_governance.py::PENDING_CENTRALIZATION``).
"""
from __future__ import annotations

from .annotation import ANNOTATION_CSS, Annotation, render_annotation_overlay
from .choropleth import CHOROPLETH_CSS, render_state_choropleth
from .network import NETWORK_CSS, NetworkEdge, NetworkNode, render_network

__all__ = [
    "render_state_choropleth",
    "CHOROPLETH_CSS",
    "Annotation",
    "render_annotation_overlay",
    "ANNOTATION_CSS",
    "render_network",
    "NetworkNode",
    "NetworkEdge",
    "NETWORK_CSS",
]
