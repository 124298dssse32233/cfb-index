"""Tests for cfb_rankings.discourse.board_page (Language Layer Wave 3).

build_fan_voice_board(db, output_dir, season) -> str

Creates output_dir/fan-voice/index.html and returns that path.
Handles empty DB gracefully — still writes valid HTML.
"""
from __future__ import annotations

import os
import sqlite3

import pytest

from cfb_rankings.discourse.board_page import build_fan_voice_board


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEAM_ID = 293
TEAM_SLUG = "michigan"
TEAM_SCHOOL = "Michigan"
SEASON = 2024


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _create_full_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE teams (
            team_id        INTEGER PRIMARY KEY,
            slug           TEXT,
            school_name    TEXT,
            short_name     TEXT,
            canonical_name TEXT,
            city           TEXT
        );

        CREATE TABLE fanbase_voice_profile (
            profile_id        INTEGER PRIMARY KEY,
            team_id           INTEGER NOT NULL,
            season_year       INTEGER NOT NULL,
            optimism_mean     REAL,
            optimism_rank     INTEGER,
            cohort_size       INTEGER,
            joy_share         REAL,
            anger_share       REAL,
            doom_share        REAL,
            sarcasm_share     REAL,
            opt_percentile    REAL,
            joy_percentile    REAL,
            anger_percentile  REAL,
            doom_percentile   REAL,
            sarcasm_percentile REAL
        );

        CREATE TABLE team_discourse_terms (
            team_discourse_term_id INTEGER PRIMARY KEY,
            team_id          INTEGER NOT NULL,
            season_year      INTEGER NOT NULL,
            week             INTEGER NOT NULL DEFAULT 0,
            term             TEXT NOT NULL,
            term_rank        INTEGER NOT NULL,
            mention_count    INTEGER NOT NULL,
            rest_count       INTEGER NOT NULL,
            z_score          REAL NOT NULL,
            rate_ratio       REAL NOT NULL,
            log2_ratio       REAL NOT NULL,
            magnitude_band   TEXT NOT NULL,
            team_doc_count   INTEGER NOT NULL,
            team_token_count INTEGER NOT NULL,
            sample_quote        TEXT,
            sample_quote_source TEXT,
            model_version    TEXT NOT NULL,
            computed_at_utc  TEXT NOT NULL,
            UNIQUE(team_id, season_year, week, term)
        );
        """
    )


def _seed_data(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO teams VALUES (?,?,?,?,?,?)",
        (TEAM_ID, TEAM_SLUG, TEAM_SCHOOL, "Michigan", "Michigan", "Ann Arbor"),
    )
    conn.execute(
        "INSERT INTO fanbase_voice_profile VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (1, TEAM_ID, SEASON, 0.72, 3, 120, 0.35, 0.15, 0.10, 0.08,
         78.0, 62.0, 40.0, 35.0, 30.0),
    )
    for rank, term in enumerate(["haarbugh", "tunnel", "maize"], start=1):
        conn.execute(
            "INSERT INTO team_discourse_terms VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rank, TEAM_ID, SEASON, 0, term, rank, 50, 10, 3.5, 2.1, 1.07,
             "high", 200, 8000, f"quote {term}", "reddit", "test-v1", "2024-10-01T00:00:00Z"),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# _MemoryDB (verbatim from test_discourse_keyness.py)
# ---------------------------------------------------------------------------


class _PassthroughCtx:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *_):
        pass


class _NoopCtx:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class _MemoryDB:
    """Minimal stand-in for cfb_rankings.db.Database over one sqlite conn."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def query_all(self, sql: str, params=None):
        cur = self._conn.execute(sql, params or {})
        return cur.fetchall()

    def query_one(self, sql: str, params=None):
        cur = self._conn.execute(sql, params or {})
        return cur.fetchone()

    def execute(self, sql: str, params=None):
        cur = self._conn.execute(sql, params or {})
        self._conn.commit()
        return cur

    def executemany(self, sql: str, seq_of_params):
        cur = self._conn.executemany(sql, seq_of_params)
        self._conn.commit()
        return cur

    def connection(self):
        return _PassthroughCtx(self._conn)

    def session(self):
        return _NoopCtx()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_empty():
    """DB with no data tables at all — graceful-degradation path."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # No schema — the board builder must handle this without raising
    return _MemoryDB(conn)


@pytest.fixture()
def db_full():
    """DB with teams + fanbase_voice_profile + team_discourse_terms."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_full_schema(conn)
    _seed_data(conn)
    return _MemoryDB(conn)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_creates_index_html(db_full, tmp_path):
    """build_fan_voice_board must write output_dir/fan-voice/index.html."""
    output_dir = str(tmp_path)
    result_path = build_fan_voice_board(db_full, output_dir, SEASON)

    expected = os.path.join(output_dir, "fan-voice", "index.html")
    assert os.path.exists(expected), f"Expected file not found: {expected}"
    assert os.path.normpath(result_path) == os.path.normpath(expected)


def test_html_contains_required_sections(db_full, tmp_path):
    """Board HTML must include 'Optimism Leaderboard' and 'Signature Terms'."""
    build_fan_voice_board(db_full, str(tmp_path), SEASON)
    html_path = os.path.join(str(tmp_path), "fan-voice", "index.html")
    content = open(html_path, encoding="utf-8").read()
    assert "Optimism Leaderboard" in content
    assert "Signature Terms" in content


def test_handles_empty_db_gracefully(db_empty, tmp_path):
    """No data tables — must still write a valid HTML file without raising."""
    output_dir = str(tmp_path)
    result_path = build_fan_voice_board(db_empty, output_dir, SEASON)

    expected = os.path.join(output_dir, "fan-voice", "index.html")
    assert os.path.exists(expected), "HTML file must be created even on empty DB"
    content = open(expected, encoding="utf-8").read()
    # Must at minimum be valid-ish HTML with a body tag
    assert "<html" in content or "<!DOCTYPE" in content or "<body" in content
