"""Smoke tests for S1 countdown + S4 recruit board surfaces.

Both renderers should:
  - Produce valid HTML even with empty/missing DB tables
  - Pull date/phase from cfb_calendar
  - Write expected files to the output dir
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from cfb_rankings.countdown import render_countdown
from cfb_rankings.recruit_board import render_recruit_board


@pytest.fixture
def empty_db():
    """In-memory SQLite with minimal schema for the recruit board query."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE player_recruiting_profiles (
            player_recruiting_profile_id INTEGER PRIMARY KEY,
            player_id INTEGER,
            season_year INTEGER,
            recruit_type TEXT,
            source_name TEXT,
            source_recruit_id TEXT,
            source_athlete_id TEXT,
            team_id INTEGER,
            school_name TEXT,
            committed_team TEXT,
            position TEXT,
            stars INTEGER,
            rating REAL,
            national_rank INTEGER,
            height_inches REAL,
            weight_lbs REAL,
            city TEXT,
            state_province TEXT,
            country TEXT,
            latitude REAL,
            longitude REAL,
            county_fips TEXT,
            notes TEXT,
            created_at TEXT
        );
    """)
    return conn


# ────────────────────────────────────────────────────────────────────────
# render_countdown (S1)
# ────────────────────────────────────────────────────────────────────────

def test_countdown_late_spring_writes_two_files(tmp_path):
    """May 15 2026 → offseason; should write index.html + countdown.json."""
    result = render_countdown(
        db=None,
        today=date(2026, 5, 15),
        output_dir=str(tmp_path),
    )
    assert result["files_written"] == 2
    html_path = Path(result["html_path"])
    json_path = Path(result["json_path"])
    assert html_path.exists()
    assert json_path.exists()
    # HTML should mention the days count
    html = html_path.read_text(encoding="utf-8")
    assert str(result["days_to_kickoff"]) in html
    # JSON should be parseable + carry the canonical fields
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["today_iso"] == "2026-05-15"
    assert payload["in_season"] is False
    assert payload["days_to_kickoff"] == result["days_to_kickoff"]
    assert "phase_label" in payload
    assert "week_label" in payload


def test_countdown_offseason_has_positive_days(tmp_path):
    """Late spring should report >0 days to kickoff."""
    result = render_countdown(
        db=None,
        today=date(2026, 5, 15),
        output_dir=str(tmp_path),
    )
    assert isinstance(result["days_to_kickoff"], int)
    assert result["days_to_kickoff"] > 0
    assert result["days_to_kickoff"] < 365


def test_countdown_in_season_zeros_out(tmp_path):
    """Mid-season → in_season=True, days=0, unit reflects games in progress."""
    result = render_countdown(
        db=None,
        today=date(2026, 10, 15),  # in-season
        output_dir=str(tmp_path),
    )
    assert result["days_to_kickoff"] == 0
    json_payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    assert json_payload["in_season"] is True


def test_countdown_phase_label_present(tmp_path):
    """The phase_label should be a non-empty human string."""
    result = render_countdown(
        db=None,
        today=date(2026, 5, 15),
        output_dir=str(tmp_path),
    )
    assert isinstance(result["phase_label"], str)
    assert len(result["phase_label"]) > 0
    # Late spring → "Late Spring" phase label
    assert "Spring" in result["phase_label"] or "spring" in result["phase_label"].lower()


# ────────────────────────────────────────────────────────────────────────
# render_recruit_board (S4)
# ────────────────────────────────────────────────────────────────────────

def test_recruit_board_empty_db_renders_empty_state(empty_db, tmp_path):
    """No rows in player_recruiting_profiles → empty-state page renders."""
    result = render_recruit_board(
        empty_db,
        class_year=2027,
        today=date(2026, 5, 15),
        output_dir=str(tmp_path),
    )
    assert result["class_year"] == 2027
    assert result["program_count"] == 0
    out_path = Path(result["output_path"])
    assert out_path.exists()
    html = out_path.read_text(encoding="utf-8")
    assert "No recruiting commitments yet" in html


def test_recruit_board_default_class_year(empty_db, tmp_path):
    """Default class_year picks next class for the anchor date."""
    # May 15 2026 → class_year defaults to 2027
    result = render_recruit_board(
        empty_db,
        class_year=None,
        today=date(2026, 5, 15),
        output_dir=str(tmp_path),
    )
    assert result["class_year"] == 2027


def test_recruit_board_with_committed_players(empty_db, tmp_path):
    """Seed a handful of commits → top program by weighted score wins."""
    empty_db.executescript("""
        INSERT INTO player_recruiting_profiles
          (season_year, committed_team, school_name, stars, rating, position, notes)
        VALUES
          (2027, 'Alabama', 'Big HS', 5, 0.95, 'QB', '{"first_name":"Alex"}'),
          (2027, 'Alabama', 'Other HS', 5, 0.94, 'WR', '{}'),
          (2027, 'Alabama', 'Local HS', 4, 0.91, 'OT', '{}'),
          (2027, 'Georgia', 'GA HS', 5, 0.95, 'DT', '{}'),
          (2027, 'Georgia', 'GA HS2', 4, 0.90, 'LB', '{}'),
          (2027, 'Texas', 'TX HS', 3, 0.85, 'S', '{}');
    """)
    empty_db.commit()
    result = render_recruit_board(
        empty_db,
        class_year=2027,
        today=date(2026, 5, 15),
        output_dir=str(tmp_path),
    )
    # 3 distinct committed_team values seeded
    assert result["program_count"] == 3
    html = Path(result["output_path"]).read_text(encoding="utf-8")
    # Alabama has weighted score 10+10+4 = 24 (top)
    # Georgia has 10+4 = 14
    # Texas has 1
    # Alabama should appear before Georgia in the markup
    assert html.index("Alabama") < html.index("Georgia") < html.index("Texas")
