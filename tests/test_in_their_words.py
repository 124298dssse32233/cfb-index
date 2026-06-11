"""Tests for cfb_rankings.player_pages.in_their_words (Language Layer Wave 3).

render_in_their_words(db, player_id) -> str

Returns "" on missing table, or fewer than _MIN_TERMS=3 terms.
Returns non-empty HTML with <mark class="itw__hl"> chips otherwise.
"""
from __future__ import annotations

import sqlite3

import pytest

from cfb_rankings.player_pages.in_their_words import render_in_their_words


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLAYER_ID = 1001
SEASON = 2024
_MIN_TERMS = 3


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _create_full_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE player_discourse_terms (
            pdesc_id            INTEGER PRIMARY KEY,
            player_id           INTEGER NOT NULL,
            season_year         INTEGER NOT NULL,
            term                TEXT NOT NULL,
            term_rank           INTEGER NOT NULL,
            window_count        INTEGER NOT NULL,
            global_count        INTEGER NOT NULL,
            z_score             REAL NOT NULL,
            rate_ratio          REAL NOT NULL,
            log2_ratio          REAL NOT NULL,
            total_windows       INTEGER NOT NULL,
            sample_quote        TEXT,
            sample_quote_source TEXT,
            model_version       TEXT NOT NULL,
            computed_at_utc     TEXT NOT NULL,
            UNIQUE(player_id, season_year, term)
        );
        """
    )


def _insert_player_terms(
    conn: sqlite3.Connection, player_id: int, terms: list[str], window_count: int = 45
) -> None:
    for rank, term in enumerate(terms, start=1):
        conn.execute(
            """INSERT INTO player_discourse_terms VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rank, player_id, SEASON, term, rank,
                window_count, 200, 2.8, 1.9, 0.92, 500,
                f"He is truly {term} out there", "reddit",
                "test-v1", "2024-10-01T00:00:00Z",
            ),
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
def db_no_table():
    """DB with no player_discourse_terms table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return _MemoryDB(conn)


@pytest.fixture()
def db_two_terms():
    """Player has only 2 terms — below _MIN_TERMS=3 floor."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_full_schema(conn)
    _insert_player_terms(conn, PLAYER_ID, ["explosive", "shifty"])
    return _MemoryDB(conn)


@pytest.fixture()
def db_three_terms():
    """Player has 3 terms — meets the floor."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_full_schema(conn)
    _insert_player_terms(conn, PLAYER_ID, ["explosive", "shifty", "blazing"])
    return _MemoryDB(conn)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_empty_when_table_missing(db_no_table):
    """Missing table must be caught gracefully and return ''."""
    result = render_in_their_words(db_no_table, PLAYER_ID)
    assert result == ""


def test_returns_empty_when_fewer_than_min_terms(db_two_terms):
    """Only 2 terms — below _MIN_TERMS=3, must return ''."""
    result = render_in_their_words(db_two_terms, PLAYER_ID)
    assert result == ""


def test_returns_nonempty_html_for_player_with_enough_terms(db_three_terms):
    """3 terms above floor — should return rendered HTML."""
    result = render_in_their_words(db_three_terms, PLAYER_ID)
    assert isinstance(result, str)
    assert len(result) > 0


def test_highlight_mark_tag_present(db_three_terms):
    """Term chips must be wrapped in <mark class=\"itw__hl\">."""
    result = render_in_their_words(db_three_terms, PLAYER_ID)
    assert 'class="itw__hl"' in result or "class='itw__hl'" in result


def test_hepta_slab_font_in_css(db_three_terms):
    """Hepta Slab font reference must appear somewhere in the rendered string."""
    result = render_in_their_words(db_three_terms, PLAYER_ID)
    assert "Hepta Slab" in result
