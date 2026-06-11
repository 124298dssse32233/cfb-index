"""Tests for the Savant Card renderer's peer-set qualification (WP-1.3).

The all-time ("Program history") peer set is only meaningful with a multi-season
history. With a single season of advanced stats it degenerates to a flat 50th
percentile (a season ranked against itself), so the renderer must suppress that
toggle chip until ``_ALLTIME_MIN_SEASONS`` seasons exist. These tests pin that
behaviour so it can't silently regress when the stats table grows.
"""
from __future__ import annotations

from types import SimpleNamespace

from cfb_rankings.team_pages.savant_card import (
    _ALLTIME_MIN_SEASONS,
    _render_toggle,
    render_savant_card,
)


def _row(alltime_peers: int) -> dict:
    return {
        "metric_group": "offense", "metric_label": "EPA / play", "metric_key": "epa_play",
        "is_inverted": 0, "raw_value": 0.12,
        "pct_vs_fbs": 70.0, "pct_vs_p4": 60.0, "pct_vs_conf": 55.0, "pct_vs_alltime": 50.0,
        "sample_size": 12,
        "peer_set_size_fbs": 130, "peer_set_size_p4": 40, "peer_set_size_conf": 16,
        "peer_set_size_alltime": alltime_peers,
    }


def test_toggle_includes_alltime_by_default() -> None:
    assert 'data-peer="alltime"' in _render_toggle(include_alltime=True)


def test_toggle_suppresses_alltime_when_excluded() -> None:
    html = _render_toggle(include_alltime=False)
    assert 'data-peer="alltime"' not in html
    # The three real peer sets remain.
    for peer in ("fbs", "p4", "conf"):
        assert f'data-peer="{peer}"' in html


def test_card_hides_alltime_with_thin_history() -> None:
    """1 season of history → all-time chip suppressed (no misleading flat-50)."""
    prof = SimpleNamespace(program_name="Test U")
    html = render_savant_card(prof, [_row(alltime_peers=1)], season_year=2025)
    assert 'data-peer="alltime"' not in html
    assert 'data-peer="fbs"' in html  # card still renders the real peer sets


def test_card_shows_alltime_with_enough_history() -> None:
    """≥ _ALLTIME_MIN_SEASONS of history → all-time chip appears."""
    prof = SimpleNamespace(program_name="Test U")
    html = render_savant_card(prof, [_row(alltime_peers=_ALLTIME_MIN_SEASONS)], season_year=2025)
    assert 'data-peer="alltime"' in html


def test_empty_rows_render_nothing() -> None:
    prof = SimpleNamespace(program_name="Test U")
    assert render_savant_card(prof, [], season_year=2025) == ""
