"""Tests for cfb_rankings.team_pages.story_words (Language Layer Wave 3).

render_story_words(db, profile, snapshot) -> str

Returns "" on missing table or <2 seasons; non-empty HTML string otherwise.
"""
from __future__ import annotations

import sqlite3

import pytest

from cfb_rankings.team_pages.story_words import render_story_words


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEAM_ID = 293
TEAM_SLUG = "michigan"


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _create_full_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE team_discourse_era_terms (
            era_term_id             INTEGER PRIMARY KEY,
            team_id                 INTEGER NOT NULL,
            season_year             INTEGER NOT NULL,
            term                    TEXT NOT NULL,
            term_rank               INTEGER NOT NULL,
            mention_count           INTEGER NOT NULL,
            rest_count              INTEGER NOT NULL,
            z_score                 REAL NOT NULL,
            rate_ratio              REAL NOT NULL,
            log2_ratio              REAL NOT NULL,
            magnitude_band          TEXT NOT NULL,
            team_season_doc_count   INTEGER NOT NULL,
            team_season_token_count INTEGER NOT NULL,
            sample_quote            TEXT,
            sample_quote_source     TEXT,
            model_version           TEXT NOT NULL,
            computed_at_utc         TEXT NOT NULL,
            UNIQUE(team_id, season_year, term)
        );
        """
    )


def _insert_era_terms(conn: sqlite3.Connection, team_id: int, seasons_terms: dict) -> None:
    """Insert era terms. seasons_terms = {season_year: [term, ...]}"""
    row_id = 1
    for season, terms in seasons_terms.items():
        for rank, term in enumerate(terms, start=1):
            conn.execute(
                """INSERT INTO team_discourse_era_terms VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row_id, team_id, season, term, rank,
                    50, 10, 3.5, 2.1, 1.07, "high",
                    200, 8000,
                    f"Sample quote about {term}", "reddit",
                    "test-v1", "2024-10-01T00:00:00Z",
                ),
            )
            row_id += 1
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
# Fake profile / snapshot stubs
# ---------------------------------------------------------------------------


class _FakeProfile:
    team_id = TEAM_ID
    slug = TEAM_SLUG
    school_name = "Michigan"


class _FakeSnapshot:
    season_year = 2024


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_no_table():
    """DB with NO team_discourse_era_terms table at all."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Intentionally no schema created
    return _MemoryDB(conn)


@pytest.fixture()
def db_one_season():
    """DB with era terms for only 1 season."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_full_schema(conn)
    _insert_era_terms(conn, TEAM_ID, {2024: ["haarbugh", "tunnel", "maize"]})
    return _MemoryDB(conn)


@pytest.fixture()
def db_two_seasons():
    """DB with era terms for 2023 and 2024 — should render non-empty."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_full_schema(conn)
    _insert_era_terms(conn, TEAM_ID, {
        2023: ["haarbugh", "tunnel", "wolverine"],
        2024: ["moorhead", "maize", "harbaugh"],
    })
    return _MemoryDB(conn)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_empty_when_table_missing(db_no_table):
    """Missing table must be caught gracefully and return ''."""
    result = render_story_words(db_no_table, _FakeProfile(), _FakeSnapshot())
    assert result == ""


def test_returns_empty_when_fewer_than_two_seasons(db_one_season):
    """Only 1 season of era terms — no cross-season contrast possible."""
    result = render_story_words(db_one_season, _FakeProfile(), _FakeSnapshot())
    assert result == ""


def test_returns_nonempty_html_for_two_seasons(db_two_seasons):
    """Two seasons with 3+ terms each — should return rendered HTML."""
    result = render_story_words(db_two_seasons, _FakeProfile(), _FakeSnapshot())
    assert isinstance(result, str)
    assert len(result) > 0


def test_story_words_css_class_present(db_two_seasons):
    """Rendered output must contain the 'story-words' CSS class."""
    result = render_story_words(db_two_seasons, _FakeProfile(), _FakeSnapshot())
    assert "story-words" in result


def test_most_recent_season_appears_first(db_two_seasons):
    """2024 should appear before 2023 in the HTML output."""
    result = render_story_words(db_two_seasons, _FakeProfile(), _FakeSnapshot())
    pos_2024 = result.find("2024")
    pos_2023 = result.find("2023")
    assert pos_2024 != -1, "2024 not found in output"
    assert pos_2023 != -1, "2023 not found in output"
    assert pos_2024 < pos_2023, "Most recent season (2024) should appear before 2023"
