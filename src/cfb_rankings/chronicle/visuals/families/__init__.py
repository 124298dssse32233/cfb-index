"""Chronicle visual chart families — one module per family.

Each renderer takes (query_result: dict, spec: VisualSpec) and returns:
    {
        "svg_html": str,
        "headline_finding": str,
        "annotations": list[Annotation],
        "alt_text": str,
    }
"""
from __future__ import annotations
