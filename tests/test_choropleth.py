"""Tests for the WS-08 statebins choropleth chart + Recruiting Footprint wiring.

The chart tests are DB-free (pure render). One integration test seeds a tiny
``player_recruiting_profiles`` table and asserts the footprint module embeds
the map above its text-chip fallback.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from cfb_rankings.charts import render_state_choropleth
from cfb_rankings.charts.choropleth import _GRID
from cfb_rankings.db import Database
from cfb_rankings.team_pages.recruiting_footprint import render_recruiting_footprint


def test_empty_counts_render_nothing() -> None:
    assert render_state_choropleth({}) == ""
    assert render_state_choropleth({"AL": 0, "GA": 0}) == ""
    assert render_state_choropleth({"AL": -3}) == ""


def test_invalid_values_are_skipped_not_fatal() -> None:
    html = render_state_choropleth({"AL": 5, "GA": "bad", "": 9, "TX": None})
    assert html  # AL alone keeps it non-empty
    assert "peak 5" in html


def test_grid_covers_50_states_plus_dc() -> None:
    assert len(_GRID) == 51
    assert "DC" in _GRID
    # No two states share a cell.
    assert len(set(_GRID.values())) == 51


def test_render_emits_svg_tiles_and_peak_legend() -> None:
    html = render_state_choropleth(
        {"AL": 24, "GA": 12, "CA": 11}, title="Where they recruit",
        caption="footprint",
    )
    assert 'data-chart="choropleth"' in html
    assert "<svg" in html and "viewBox" in html
    assert 'preserveAspectRatio' in html  # scales on mobile, no overflow
    assert ">AL<" in html and ">CA<" in html
    # Every state has a tile (zero-count states render faint, still present).
    assert ">WY<" in html
    assert "Where they recruit" in html
    assert "peak 24" in html
    # Accessibility: each tile is a labelled img with its value.
    assert 'aria-label="AL: 24"' in html
    assert 'aria-label="WY: 0"' in html


def test_as_figure_false_returns_bare_svg_and_legend() -> None:
    # The card-friendly form drops the figure/title/caption chrome so it can
    # render through render_chart_card without nesting figures.
    bare = render_state_choropleth(
        {"AL": 24, "GA": 12}, title="ignored", caption="ignored",
        as_figure=False,
    )
    assert bare.startswith("<svg")
    assert "<figure" not in bare and "figcaption" not in bare
    # Still a real chart: tiles + legend (the ramp scale) remain.
    assert 'data-chart="choropleth"' in bare
    assert "choropleth__legend" in bare and "peak 24" in bare
    # Title/caption are the card's job now, not the bare svg's.
    assert "ignored" not in bare


def test_peak_state_is_brightest() -> None:
    # The peak state should carry the accent (bright) fill; a low state should
    # be visibly dimmer. We just assert distinct fills are emitted.
    html = render_state_choropleth({"AL": 100, "WA": 1})
    assert html.count("<rect") == 51  # all tiles drawn
    # accent gold appears for the peak
    assert "#c9a24a" in html


def _make_db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{tmp_path / 'choro.db'}")
    db.execute(
        """
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY, slug TEXT, state TEXT, country TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE player_recruiting_profiles (
            player_recruiting_profile_id INTEGER PRIMARY KEY,
            player_id INTEGER, season_year INTEGER, team_id INTEGER,
            state_province TEXT
        )
        """
    )
    db.execute("INSERT INTO teams (team_id, slug, state) VALUES (1, 'alabama', NULL)")
    return db


def test_footprint_module_embeds_choropleth(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    # Two cycles of recruits across several states.
    rows = (
        [("AL", 2026)] * 10 + [("GA", 2026)] * 5 + [("FL", 2025)] * 3
        + [("CA", 2025)] * 2 + [("TX", 2024)] * 1
    )
    for i, (st, yr) in enumerate(rows, start=1):
        db.execute(
            "INSERT INTO player_recruiting_profiles "
            "(player_recruiting_profile_id, player_id, season_year, team_id, state_province) "
            "VALUES (:i, :p, :y, 1, :s)",
            {"i": i, "p": 1000 + i, "y": yr, "s": st},
        )

    profile = SimpleNamespace(program_name="Alabama")
    snapshot = SimpleNamespace(team_id=1, season_year=2026)
    html = render_recruiting_footprint(db, profile, snapshot)

    assert 'data-module="recruiting-footprint"' in html
    # The map is embedded (geography is the point).
    assert 'data-chart="choropleth"' in html
    assert "recruit-footprint__map" in html
    # The map now renders through the shared chart-card shell: it carries the
    # card chrome (a single card figure, no nested choropleth figure) and a
    # source-receipt footer.
    assert "chart-card" in html
    assert html.count('<figure class="chart-card"') == 1
    assert "<figure class=\"choropleth\"" not in html
    assert "chart-card__source" in html
    assert "player_recruiting_profiles" in html
    # The text chips remain as the accessible fallback.
    assert "recruit-footprint__states" in html
    # Map aggregates across cycles, so AL=10 is the peak of the window.
    assert "peak 10" in html
    assert 'aria-label="AL: 10"' in html


def test_footprint_empty_when_no_recruits(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    profile = SimpleNamespace(program_name="Alabama")
    snapshot = SimpleNamespace(team_id=1, season_year=2026)
    assert render_recruiting_footprint(db, profile, snapshot) == ""
