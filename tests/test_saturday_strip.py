"""Tests for cfb_rankings.mobile.saturday_strip (Sprint v5-7.6).

Locked spec: docs/mockups/mockup_06_saturday_strip.html + Spec H.1 in
IMPLEMENTATION_PLAN_v3_iteration.md.
"""

from __future__ import annotations

import datetime as dt
import pytest

from cfb_rankings.mobile.saturday_strip import (
    StripChip,
    StripGame,
    StripState,
    render_strip_html,
)


# ---------------------------------------------------------------------------
# Pure renderer tests
# ---------------------------------------------------------------------------

def test_state_is_frozen_dataclass() -> None:
    s = StripState(mode="in_season", generated_at_utc="2026-05-17T00:00:00Z",
                   refresh_seconds=30)
    with pytest.raises(Exception):  # FrozenInstanceError variant
        s.mode = "off_season"


def test_in_season_empty_state_renders_message() -> None:
    s = StripState(mode="in_season", generated_at_utc="2026-05-17T00:00:00Z",
                   refresh_seconds=300, games=[])
    html = render_strip_html(s)
    assert 'data-strip-mode="in_season"' in html
    assert "No games today" in html
    assert 'data-refresh-seconds="300"' in html


def test_in_season_renders_live_row_with_pulsing_dot() -> None:
    g = StripGame(
        away_abbr="IND", home_abbr="PSU", status="live",
        away_points=17, home_points=14,
        period_clock="2Q · 4:32",
    )
    s = StripState(mode="in_season", generated_at_utc="X", refresh_seconds=30,
                   games=[g])
    html = render_strip_html(s)
    assert 'class="live-dot"' in html
    assert 'class="live-tag">LIVE' in html
    assert ">IND<" in html and ">PSU<" in html
    assert ">17<" in html and ">14<" in html
    assert "2Q · 4:32" in html


def test_in_season_renders_final_with_upset_tag() -> None:
    g = StripGame(
        away_abbr="TEX", home_abbr="OU", status="final",
        away_points=24, home_points=21, upset_flag=True,
    )
    s = StripState(mode="in_season", generated_at_utc="X", refresh_seconds=600,
                   games=[g])
    html = render_strip_html(s)
    assert 'class="strip__final">FINAL' in html
    assert 'class="strip__upset">UPSET' in html


def test_in_season_renders_upcoming_with_channel() -> None:
    g = StripGame(
        away_abbr="ALA", home_abbr="LSU", status="upcoming",
        kickoff_local="7:30 ET", channel="CBS",
    )
    s = StripState(mode="in_season", generated_at_utc="X", refresh_seconds=300,
                   games=[g])
    html = render_strip_html(s)
    assert '7:30 ET' in html
    assert 'class="strip__channel">CBS' in html
    # Should NOT include LIVE / FINAL / UPSET for an upcoming game
    assert 'class="live-tag">LIVE' not in html
    assert 'class="strip__final">FINAL' not in html
    assert 'class="strip__upset">UPSET' not in html


def test_off_season_renders_days_to_kickoff_first() -> None:
    s = StripState(
        mode="off_season",
        generated_at_utc="X", refresh_seconds=3600,
        days_to_kickoff=79,
        phase_label="Off-season",
        chips=[StripChip(label="CAMP", body="Opens Aug 3", kind="camp")],
    )
    html = render_strip_html(s)
    assert 'data-strip-mode="off_season"' in html
    assert "79" in html
    assert "DAYS TO KICKOFF" in html
    assert "CAMP" in html
    assert "Opens Aug 3" in html


def test_off_season_escapes_chip_content() -> None:
    """Defense against XSS via injected chip body."""
    s = StripState(
        mode="off_season",
        generated_at_utc="X", refresh_seconds=3600,
        days_to_kickoff=10,
        chips=[StripChip(label="<bad>", body="<script>x</script>", kind="other")],
    )
    html = render_strip_html(s)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;bad&gt;" in html


def test_render_emits_aria_label() -> None:
    """A11y: strip carries an aria-label per spec."""
    s = StripState(mode="in_season", generated_at_utc="X", refresh_seconds=30,
                   games=[StripGame(away_abbr="A", home_abbr="B", status="live")])
    html = render_strip_html(s)
    assert "aria-label=" in html


def test_refresh_seconds_serialized() -> None:
    """Client-side ticker reads data-refresh-seconds to set its interval."""
    s = StripState(mode="off_season", generated_at_utc="X",
                   refresh_seconds=3600, days_to_kickoff=120)
    html = render_strip_html(s)
    assert 'data-refresh-seconds="3600"' in html
