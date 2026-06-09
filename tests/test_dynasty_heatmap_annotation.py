"""Annotation overlay on the Dynasty Heatmap (WS-08 annotation discipline).

DB-free: synthetic enriched rows drive the renderer. Asserts the heatmap
self-narrates — a single callout marks the top program's peak season — and that
the bare share-card form opts out (it carries no stylesheet for the classes).
"""
from __future__ import annotations

from cfb_rankings.dynasty_heatmap import (
    _peak_dynasty_annotation,
    _team_index,
    render_dynasty_heatmap_svg,
)


def _rows() -> list[dict]:
    """Two teams across 2014-2021. Team A dominates, peaking in 2018 at 99."""
    years = list(range(2014, 2022))
    rows: list[dict] = []
    a_pcts = {2014: 80, 2015: 85, 2016: 88, 2017: 90,
              2018: 99, 2019: 92, 2020: 91, 2021: 93}
    b_pcts = {y: 40 for y in years}
    for y in years:
        rows.append({
            "team_id": 1, "season_year": y, "team_name": "Alpha St",
            "team_slug": "alpha-st", "conference_name": "Test", "level_code": "FBS",
            "percentile": float(a_pcts[y]), "power_rating": 10.0,
        })
        rows.append({
            "team_id": 2, "season_year": y, "team_name": "Beta U",
            "team_slug": "beta-u", "conference_name": "Test", "level_code": "FBS",
            "percentile": float(b_pcts[y]), "power_rating": 1.0,
        })
    return rows


def test_peak_annotation_marks_the_dynasty_at_its_best_season() -> None:
    rows = _rows()
    teams = _team_index(rows)
    assert teams[0]["team_name"] == "Alpha St"  # highest avg percentile
    cell_lookup = {(r["team_id"], r["season_year"]): r for r in rows}
    years = list(range(2014, 2022))
    anns = _peak_dynasty_annotation(
        teams, cell_lookup, years,
        label_w=220, cell_w=52, cell_h=16, header_h=64,
    )
    assert len(anns) == 1
    lines = list(anns[0].lines)
    assert lines[0] == "Alpha St, 2018"          # the peak year, not 2021
    assert "99th percentile" in lines[1]


def test_render_embeds_the_overlay_by_default() -> None:
    svg = render_dynasty_heatmap_svg(_rows(), year_start=2014, year_end=2021)
    assert 'class="chart-annotations"' in svg
    assert "Alpha St, 2018" in svg
    # The overlay is a self-contained <g> inside the chart's own viewBox.
    assert svg.count("<svg") == 1
    assert "chart-ann__dot" in svg and "chart-ann__leader" in svg


def test_share_card_form_opts_out_of_the_overlay() -> None:
    # The downloadable bare .svg has no stylesheet, so the class-styled callout
    # would render unstyled — the build entry point passes annotate=False.
    svg = render_dynasty_heatmap_svg(
        _rows(), year_start=2014, year_end=2021, annotate=False,
    )
    assert "chart-annotations" not in svg


def test_no_annotation_when_no_data() -> None:
    assert _peak_dynasty_annotation([], {}, [], label_w=220, cell_w=52,
                                    cell_h=16, header_h=64) == []
