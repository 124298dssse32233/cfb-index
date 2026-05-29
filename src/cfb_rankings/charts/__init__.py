"""Centralised chart vocabulary (WS-08, D-007).

All chart renderers live here so the locked vocabulary stays governable and a
CI lint can forbid ``def render_*_chart`` outside this package. Each renderer
returns a self-contained, server-side SVG string (no JS required) so charts
satisfy the WS-11 static-SVG-fallback bar.

Locked types (9): Percentile Bar, Trajectory Spark, Bump Chart, Annotated
Line, Small Multiples, Heatmap (the original 6, rendered inline across
modules today) + Sankey, Choropleth, Network (the 3 expansion types). This
package currently houses Choropleth; the others migrate here as they are
refactored to the shared component.
"""
from __future__ import annotations

from .annotation import ANNOTATION_CSS, Annotation, render_annotation_overlay
from .choropleth import CHOROPLETH_CSS, render_state_choropleth

__all__ = [
    "render_state_choropleth",
    "CHOROPLETH_CSS",
    "Annotation",
    "render_annotation_overlay",
    "ANNOTATION_CSS",
]
