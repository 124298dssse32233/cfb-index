"""Tests for cfb_rankings.discourse.player_descriptors (Language Layer Wave 3).

compute_player_descriptors(db, *, seasons, top_n=10, min_windows=30,
                           players=None, commit=False) -> dict

All tests use an in-memory sqlite corpus. No network, no real DB.
"""
from __future__ import annotations

import sqlite3

import pytest

from cfb_rankings.discourse.player_descriptors import compute_player_descriptors


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEAM_A_ID = 293
TEAM_A_SLUG = "michigan"
TEAM_A_SCHOOL = "Michigan"

# Player under test — last name is what the windowing algorithm will anchor on.
PLAYER_A_ID = 1001
PLAYER_A_FIRST = "Blake"
PLAYER_A_LAST = "Corum"

# A player with very few mentions — should fall below min_windows floor.
PLAYER_B_ID = 1002
PLAYER_B_FIRST = "Zach"
PLAYER_B_LAST = "Charbonnet"

# Synthetic distinctive descriptor for player A
DESCRIPTOR = "blazing"

# A known blocklist term that should be filtered even if frequent near player name
BLOCKED_TERM = "weight"

SEASONS = [2024]
CORPUS_DATE = "2024-09-15T12:00:00Z"
FOOTBALL_ANCHORS = "quarterback touchdown recruiting depth chart"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def _create_schema(conn: sqlite3.Connection) -> None:
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

        CREATE TABLE players (
            player_id  INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name  TEXT
        );

        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY,
            title_text               TEXT,
            body_text                TEXT,
            source_name              TEXT,
            source_subchannel        TEXT,
            external_created_at_utc  TEXT,
            is_deleted               INTEGER DEFAULT 0,
            is_removed               INTEGER DEFAULT 0
        );

        CREATE TABLE conversation_document_targets (
            target_id                INTEGER PRIMARY KEY,
            conversation_document_id INTEGER NOT NULL,
            team_id                  INTEGER,
            player_id                INTEGER,
            target_type              TEXT NOT NULL,
            toxicity_score           REAL
        );

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
# Corpus builder
# ---------------------------------------------------------------------------


def _build_corpus(conn: sqlite3.Connection, n_player_docs: int = 40) -> None:
    """Insert docs with player-name windows containing the DESCRIPTOR term.

    n_player_docs docs mention PLAYER_A_LAST with DESCRIPTOR nearby.
    PLAYER_B_LAST appears in only 2 docs (below min_windows floor).
    BLOCKED_TERM appears near PLAYER_A_LAST in every doc.
    """
    conn.execute(
        "INSERT INTO teams VALUES (?,?,?,?,?,?)",
        (TEAM_A_ID, TEAM_A_SLUG, TEAM_A_SCHOOL, "Michigan", "Michigan", "Ann Arbor"),
    )
    conn.execute(
        "INSERT INTO players VALUES (?,?,?)",
        (PLAYER_A_ID, PLAYER_A_FIRST, PLAYER_A_LAST),
    )
    conn.execute(
        "INSERT INTO players VALUES (?,?,?)",
        (PLAYER_B_ID, PLAYER_B_FIRST, PLAYER_B_LAST),
    )

    doc_id = 1
    for i in range(n_player_docs):
        body = (
            f"{FOOTBALL_ANCHORS} {DESCRIPTOR} {PLAYER_A_LAST.lower()} {BLOCKED_TERM} "
            f"incredible run great player {i}"
        )
        conn.execute(
            "INSERT INTO conversation_documents VALUES (?,?,?,?,?,?,0,0)",
            (doc_id, f"Thread {doc_id}", body, "reddit", f"r/{TEAM_A_SLUG}", CORPUS_DATE),
        )
        conn.execute(
            "INSERT INTO conversation_document_targets VALUES (?,?,?,?,?,?)",
            (doc_id, doc_id, TEAM_A_ID, PLAYER_A_ID, "player", 0.0),
        )
        doc_id += 1

    # PLAYER_B: only 2 docs — below min_windows=30
    for i in range(2):
        body = f"{FOOTBALL_ANCHORS} {PLAYER_B_LAST.lower()} solid carry {i}"
        conn.execute(
            "INSERT INTO conversation_documents VALUES (?,?,?,?,?,?,0,0)",
            (doc_id, f"Thread {doc_id}", body, "reddit", f"r/{TEAM_A_SLUG}", CORPUS_DATE),
        )
        conn.execute(
            "INSERT INTO conversation_document_targets VALUES (?,?,?,?,?,?)",
            (doc_id, doc_id, TEAM_A_ID, PLAYER_B_ID, "player", 0.0),
        )
        doc_id += 1

    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_schema(conn)
    _build_corpus(conn)
    return _MemoryDB(conn)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dry_run_returns_zero_writes(db):
    result = compute_player_descriptors(db, seasons=SEASONS, commit=False)
    assert result["players_written"] == 0
    assert result["terms_written"] == 0
    rows = db.query_all("SELECT * FROM player_discourse_terms")
    assert len(rows) == 0


def test_commit_writes_descriptor_terms(db):
    result = compute_player_descriptors(db, seasons=SEASONS, min_windows=30, commit=True)
    assert result["terms_written"] > 0
    assert result["players_written"] >= 1
    assert result["windows_scanned"] > 0
    rows = db.query_all("SELECT * FROM player_discourse_terms WHERE player_id=?", (PLAYER_A_ID,))
    assert len(rows) > 0


def test_blocklist_term_excluded(db):
    """BLOCKED_TERM ('weight') must not appear in player_discourse_terms output."""
    compute_player_descriptors(db, seasons=SEASONS, min_windows=1, commit=True)
    rows = db.query_all(
        "SELECT term FROM player_discourse_terms WHERE player_id=?", (PLAYER_A_ID,)
    )
    terms = {r["term"].lower() for r in rows}
    assert BLOCKED_TERM not in terms


def test_player_below_min_windows_gets_no_terms(db):
    """PLAYER_B has only 2 doc appearances — must produce zero terms at min_windows=30."""
    compute_player_descriptors(db, seasons=SEASONS, min_windows=30, commit=True)
    rows = db.query_all(
        "SELECT * FROM player_discourse_terms WHERE player_id=?", (PLAYER_B_ID,)
    )
    assert len(rows) == 0


def test_idempotency_no_duplicates(db):
    """Running commit=True twice must not create duplicate rows."""
    compute_player_descriptors(db, seasons=SEASONS, min_windows=30, commit=True)
    first_count = db.query_one("SELECT COUNT(*) AS n FROM player_discourse_terms")["n"]

    compute_player_descriptors(db, seasons=SEASONS, min_windows=30, commit=True)
    second_count = db.query_one("SELECT COUNT(*) AS n FROM player_discourse_terms")["n"]

    assert second_count == first_count


def test_result_dict_has_required_keys(db):
    result = compute_player_descriptors(db, seasons=SEASONS, commit=False)
    for key in ("players_written", "terms_written", "windows_scanned", "seasons"):
        assert key in result, f"missing key: {key}"
