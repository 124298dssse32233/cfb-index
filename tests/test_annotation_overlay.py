"""Tests for the WS-08 in-chart annotation overlay DSL
(``src/cfb_rankings/charts/annotation.py``).

Pins the contract the chart vocabulary depends on: (1) empty / blank input
renders nothing, (2) every label box stays inside the host plot rect, (3) boxes
never overlap each other (collision avoidance has teeth), (4) the marker dot
sits exactly on the supplied data point, (5) text is HTML-escaped, and (6) an
explicit placement is honored when it fits.
"""
from __future__ import annotations

import re

from cfb_rankings.charts.annotation import (
    Annotation,
    render_annotation_overlay,
)

_W = 880.0
_H = 200.0


def _rects(svg: str) -> list[tuple[float, float, float, float]]:
    out = []
    for m in re.finditer(
        r'<rect class="chart-ann__box" x="([\d.]+)" y="([\d.]+)" '
        r'width="([\d.]+)" height="([\d.]+)"',
        svg,
    ):
        out.append(tuple(float(g) for g in m.groups()))
    return out


def _dots(svg: str) -> list[tuple[float, float]]:
    return [
        (float(a), float(b))
        for a, b in re.findall(
            r'<circle class="chart-ann__dot" cx="([\d.]+)" cy="([\d.]+)"', svg
        )
    ]


def _overlap(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def test_empty_and_blank_render_nothing() -> None:
    assert render_annotation_overlay([], width=_W, height=_H) == ""
    blank = [Annotation(10, 10, ["", "   "])]
    assert render_annotation_overlay(blank, width=_W, height=_H) == ""


def test_boxes_stay_in_bounds() -> None:
    # Points jammed into every corner — boxes must still clamp inside the rect.
    anns = [
        Annotation(2, 2, ["top-left corner"]),
        Annotation(_W - 2, 2, ["top-right corner"]),
        Annotation(2, _H - 2, ["bottom-left corner"]),
        Annotation(_W - 2, _H - 2, ["bottom-right corner"]),
    ]
    svg = render_annotation_overlay(anns, width=_W, height=_H)
    for x, y, w, h in _rects(svg):
        assert x >= 0 and y >= 0
        assert x + w <= _W
        assert y + h <= _H


def test_boxes_do_not_overlap() -> None:
    # Three points clustered together: layout must spread the boxes apart.
    anns = [
        Annotation(400, 100, ["peak rating 95.4"]),
        Annotation(410, 105, ["title-run inflection"]),
        Annotation(420, 110, ["post-Saban transition"]),
    ]
    svg = render_annotation_overlay(anns, width=_W, height=_H)
    rects = _rects(svg)
    assert len(rects) == 3
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            assert not _overlap(rects[i], rects[j]), (rects[i], rects[j])


def test_dot_sits_on_data_point() -> None:
    svg = render_annotation_overlay(
        [Annotation(123.0, 77.0, ["x"])], width=_W, height=_H
    )
    assert _dots(svg) == [(123.0, 77.0)]


def test_text_is_escaped() -> None:
    svg = render_annotation_overlay(
        [Annotation(100, 100, ["<b>2017</b> & 'peak'"])], width=_W, height=_H
    )
    assert "<b>2017</b>" not in svg
    assert "&lt;b&gt;2017&lt;/b&gt; &amp; &#x27;peak&#x27;" in svg


def test_explicit_placement_below_right_when_it_fits() -> None:
    # Point near top-left with room below-right: box should land below and right.
    svg = render_annotation_overlay(
        [Annotation(100, 40, ["below me"], placement="below-right")],
        width=_W,
        height=_H,
    )
    (x, y, _w, _h) = _rects(svg)[0]
    assert x >= 100          # to the right of the point
    assert y >= 40           # below the point


def test_max_three_lines() -> None:
    svg = render_annotation_overlay(
        [Annotation(400, 100, ["l1", "l2", "l3", "l4", "l5"])],
        width=_W,
        height=_H,
    )
    assert svg.count('class="chart-ann__text"') == 3
