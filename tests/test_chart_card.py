"""Tests for the shared chart-card shell (WS-08, D-007).

The card is pure, deterministic string composition, so every slot can be
verified with zero live data.
"""
from __future__ import annotations

import re

from cfb_rankings.charts import render_chart_card

_CHART = '<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'


def test_empty_chart_returns_empty() -> None:
    assert render_chart_card("") == ""
    assert render_chart_card("   ") == ""


def test_bare_chart_still_renders_figure() -> None:
    out = render_chart_card(_CHART)
    assert out.startswith("<figure class=\"chart-card\"")
    assert _CHART in out
    # No optional slots → no header, no footer.
    assert "chart-card__head" not in out
    assert "chart-card__source" not in out


def test_all_slots_present() -> None:
    out = render_chart_card(
        _CHART,
        eyebrow="Network",
        headline="Portal Pipelines",
        lede="Who feeds whom this cycle.",
        x_label="Destination",
        y_label="Players",
        source="CFB Index · transfer_entries",
        anchor="network",
    )
    assert 'id="network"' in out
    assert "Portal Pipelines" in out
    assert "Who feeds whom this cycle." in out
    assert ">Network<" in out  # eyebrow text
    assert "chart-card__xlabel" in out and "Destination" in out
    assert "chart-card__ylabel" in out and "Players" in out
    assert "chart-card__source" in out and "CFB Index · transfer_entries" in out


def test_source_receipt_prefixed_with_label() -> None:
    out = render_chart_card(_CHART, source="CFB Index · games")
    assert "chart-card__source-label" in out
    assert ">Source<" in out
    assert "CFB Index · games" in out


def test_heading_level_clamped() -> None:
    assert "<h2 " in render_chart_card(_CHART, headline="X", heading_level=1)
    assert "<h3 " in render_chart_card(_CHART, headline="X", heading_level=3)
    assert "<h6 " in render_chart_card(_CHART, headline="X", heading_level=9)


def test_text_is_escaped() -> None:
    out = render_chart_card(
        _CHART,
        headline="A & B <script>",
        eyebrow="<x>",
        source="t & t",
    )
    assert "<script>" not in out
    assert "A &amp; B &lt;script&gt;" in out
    assert "&lt;x&gt;" in out
    assert "t &amp; t" in out
    # The chart SVG itself must pass through untouched.
    assert _CHART in out


def test_annotation_overlay_layer() -> None:
    overlay = '<svg><g class="chart-annotations"></g></svg>'
    out = render_chart_card(_CHART, annotation_svg=overlay)
    assert "chart-card__overlay" in out
    assert overlay in out
    # Overlay sits inside the plot container, after the chart.
    plot = re.search(r'chart-card__plot">(.*?)</div></div>', out, re.S)
    assert plot is not None
    assert plot.group(1).index(_CHART) < plot.group(1).index("chart-card__overlay")


def test_no_overlay_div_without_annotation() -> None:
    assert "chart-card__overlay" not in render_chart_card(_CHART)


def test_deterministic() -> None:
    kw = dict(headline="H", eyebrow="E", lede="L", source="S", x_label="x", y_label="y")
    assert render_chart_card(_CHART, **kw) == render_chart_card(_CHART, **kw)
