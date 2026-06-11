"""Tests for cfb_rankings.discourse.leaderboard_page — Language Layer Wave 4."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from cfb_rankings.discourse.leaderboard_page import (
    _ordinal,
    build_leaderboard_page,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    """In-memory SQLite DB with fanbase_voice_profile pre-populated."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE fanbase_voice_profile (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year    INTEGER NOT NULL,
            team_id        INTEGER,
            slug           TEXT,
            display_name   TEXT,
            optimism_score REAL,
            anger_score    REAL,
            joy_score      REAL,
            sarcasm_score  REAL,
            anxiety_score  REAL,
            cohort_size    INTEGER
        )
        """
    )
    # Seed five teams for season 2025
    rows = [
        (2025, 1, "alabama",    "Alabama",    0.412,  0.150,  0.370, 0.080, 0.200, 5000),
        (2025, 2, "ohio-state", "Ohio State",  0.310,  0.280,  0.290, 0.120, 0.310, 4800),
        (2025, 3, "georgia",    "Georgia",    0.250, -0.050,  0.310, 0.200, 0.180, 4200),
        (2025, 4, "michigan",   "Michigan",   0.190,  0.330,  0.210, 0.310, 0.270, 3900),
        (2025, 5, "texas",      "Texas",     -0.050,  0.410,  0.180, 0.360, 0.450, 3500),
    ]
    conn.executemany(
        "INSERT INTO fanbase_voice_profile "
        "(season_year,team_id,slug,display_name,optimism_score,anger_score,"
        "joy_score,sarcasm_score,anxiety_score,cohort_size) VALUES (?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def tmp_out(tmp_path):
    """Temporary output directory."""
    return tmp_path


# ---------------------------------------------------------------------------
# _ordinal tests
# ---------------------------------------------------------------------------

class TestOrdinal:
    def test_1st(self):
        assert _ordinal(1) == "1st"

    def test_2nd(self):
        assert _ordinal(2) == "2nd"

    def test_3rd(self):
        assert _ordinal(3) == "3rd"

    def test_4th(self):
        assert _ordinal(4) == "4th"

    def test_5th(self):
        assert _ordinal(5) == "5th"

    def test_11th(self):
        assert _ordinal(11) == "11th"

    def test_12th(self):
        assert _ordinal(12) == "12th"

    def test_13th(self):
        assert _ordinal(13) == "13th"

    def test_21st(self):
        assert _ordinal(21) == "21st"

    def test_22nd(self):
        assert _ordinal(22) == "22nd"

    def test_23rd(self):
        assert _ordinal(23) == "23rd"

    def test_111th(self):
        # 111 ends in 11 → "th"
        assert _ordinal(111) == "111th"

    def test_112th(self):
        assert _ordinal(112) == "112th"

    def test_113th(self):
        assert _ordinal(113) == "113th"

    def test_101st(self):
        assert _ordinal(101) == "101st"

    def test_102nd(self):
        assert _ordinal(102) == "102nd"


# ---------------------------------------------------------------------------
# build_leaderboard_page — happy-path tests
# ---------------------------------------------------------------------------

class TestBuildLeaderboardPage:
    def test_returns_string_path(self, db, tmp_out):
        """build_leaderboard_page must return a string."""
        result = build_leaderboard_page(db, tmp_out, season=2025)
        assert isinstance(result, str)

    def test_output_file_exists(self, db, tmp_out):
        """Output file must land at <output_dir>/fan-voice/leaderboard.html."""
        result = build_leaderboard_page(db, tmp_out, season=2025)
        expected = tmp_out / "fan-voice" / "leaderboard.html"
        assert expected.exists(), "leaderboard.html was not created"
        assert Path(result) == expected

    def test_page_contains_team_names(self, db, tmp_out):
        """Page HTML must mention each seeded team name."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        for name in ("Alabama", "Ohio State", "Georgia", "Michigan", "Texas"):
            assert name in html, f"Team '{name}' not found in leaderboard HTML"

    def test_page_contains_word_leaderboard(self, db, tmp_out):
        """Page must contain 'leaderboard' or 'Leaderboard' (case-insensitive)."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        assert "leaderboard" in html.lower()

    def test_page_contains_season_year(self, db, tmp_out):
        """Season year must appear in the page."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        assert "2025" in html

    def test_fanbases_count_in_hero(self, db, tmp_out):
        """Hero bar must show the fanbase count (5 in seed data)."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        assert "5" in html

    def test_nba_framing_present(self, db, tmp_out):
        """Rows must include ordinal NBA-framing text."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        # e.g. "1st of 5 fanbases in optimism"
        assert "fanbases in optimism" in html

    def test_back_link_to_fan_voice_index(self, db, tmp_out):
        """Page must contain a link back to /fan-voice/index.html."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        assert "/fan-voice/index.html" in html

    def test_fan_voice_subdir_created(self, db, tmp_out):
        """fan-voice/ subdirectory must be created automatically."""
        fan_voice_dir = tmp_out / "fan-voice"
        assert not fan_voice_dir.exists(), "pre-condition: dir should not exist yet"
        build_leaderboard_page(db, tmp_out, season=2025)
        assert fan_voice_dir.is_dir()

    def test_scores_formatted_with_sign(self, db, tmp_out):
        """Scores must appear with leading '+' or '-' sign."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        # Alabama has optimism_score=0.412 → should appear as "+0.412"
        assert "+0.412" in html

    def test_negative_score_formatted(self, db, tmp_out):
        """Negative scores must use '-' sign (Texas optimism = -0.050)."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        assert "-0.050" in html

    def test_metric_extremes_section_present(self, db, tmp_out):
        """Page must include a per-metric extremes section."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        # Should contain at least one of the metric labels in the extremes grid
        assert any(label in html for label in ("Optimism", "Anger", "Joy", "Sarcasm"))

    def test_is_valid_html(self, db, tmp_out):
        """Output must start with <!DOCTYPE html> and contain closing </html>."""
        build_leaderboard_page(db, tmp_out, season=2025)
        html = (tmp_out / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        assert html.strip().startswith("<!DOCTYPE html")
        assert "</html>" in html


# ---------------------------------------------------------------------------
# Zero-rows / stub page tests
# ---------------------------------------------------------------------------

class TestStubPage:
    @pytest.fixture()
    def empty_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE fanbase_voice_profile (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                season_year    INTEGER NOT NULL,
                team_id        INTEGER,
                slug           TEXT,
                display_name   TEXT,
                optimism_score REAL,
                anger_score    REAL,
                joy_score      REAL,
                sarcasm_score  REAL,
                anxiety_score  REAL,
                cohort_size    INTEGER
            )
            """
        )
        conn.commit()
        yield conn
        conn.close()

    def test_stub_file_exists(self, empty_db, tmp_path):
        """Even with zero rows the output file must be created."""
        result = build_leaderboard_page(empty_db, tmp_path, season=2025)
        assert Path(result).exists()

    def test_stub_contains_no_data(self, empty_db, tmp_path):
        """Stub page must contain 'No data' text."""
        build_leaderboard_page(empty_db, tmp_path, season=2025)
        html = (tmp_path / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        assert "No data" in html

    def test_stub_returns_string(self, empty_db, tmp_path):
        """Return value must be a string even for the stub."""
        result = build_leaderboard_page(empty_db, tmp_path, season=2025)
        assert isinstance(result, str)

    def test_stub_for_wrong_season(self, db, tmp_path):
        """Querying a season with no rows must produce a stub (No data) page."""
        build_leaderboard_page(db, tmp_path, season=1999)
        html = (tmp_path / "fan-voice" / "leaderboard.html").read_text(encoding="utf-8")
        assert "No data" in html
