"""Tests for cfb_rankings.discourse.eras (Language Layer Wave 3).

compute_team_eras(db, *, seasons, top_n=8, min_team_docs=150, min_seasons=2,
                 teams=None, commit=False) -> dict

All tests run against an in-memory sqlite corpus — no network, no real DB.
"""
from __future__ import annotations

import sqlite3

import pytest

from cfb_rankings.discourse.eras import compute_team_eras


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEAM_A_ID = 293
TEAM_A_SLUG = "michigan"
TEAM_A_SCHOOL = "Michigan"
TEAM_B_ID = 195
TEAM_B_SLUG = "ohio-state"
TEAM_B_SCHOOL = "Ohio State"

FOOTBALL_ANCHORS = "quarterback touchdown recruiting depth chart"

# Synthetic distinctive terms — one set per season so cross-season contrast is clear.
TERM_2023 = "haarbugh"   # heavy in 2023, absent in 2024
TERM_2024 = "moorhead"   # heavy in 2024, absent in 2023

SEASONS = [2023, 2024]


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

        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY,
            title_text               TEXT,
            body_text                TEXT,
            source_name              TEXT,
            source_subchannel        TEXT,
            external_created_at_utc  TEXT,
            is_deleted               INTEGER DEFAULT 0,
            is_removed               INTEGER DEFAULT 0,
            relevance_ml_score       REAL
        );

        CREATE TABLE conversation_document_targets (
            target_id                INTEGER PRIMARY KEY,
            conversation_document_id INTEGER NOT NULL,
            team_id                  INTEGER,
            player_id                INTEGER,
            target_type              TEXT NOT NULL,
            toxicity_score           REAL
        );

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


def _build_corpus(conn: sqlite3.Connection, n_docs_per_season: int = 80) -> None:
    """Insert synthetic fan-voice docs with distinct 2023/2024 vocabulary.

    2023 docs: heavy use of TERM_2023 ("haarbugh"), zero TERM_2024.
    2024 docs: heavy use of TERM_2024 ("moorhead"), zero TERM_2023.
    Each doc carries football anchors to pass any relevance gate.
    """
    conn.execute(
        "INSERT INTO teams VALUES (?,?,?,?,?,?)",
        (TEAM_A_ID, TEAM_A_SLUG, TEAM_A_SCHOOL, "Michigan", "Michigan", "Ann Arbor"),
    )
    conn.execute(
        "INSERT INTO teams VALUES (?,?,?,?,?,?)",
        (TEAM_B_ID, TEAM_B_SLUG, TEAM_B_SCHOOL, "Ohio State", "Ohio State", "Columbus"),
    )

    doc_id = 1
    for season, distinctive in [(2023, TERM_2023), (2024, TERM_2024)]:
        date_str = f"{season}-10-01T12:00:00Z"
        for i in range(n_docs_per_season):
            body = (
                f"{FOOTBALL_ANCHORS} {distinctive} {distinctive} {distinctive} "
                f"great game this week index {i}"
            )
            conn.execute(
                "INSERT INTO conversation_documents VALUES (?,?,?,?,?,?,0,0,NULL)",
                (doc_id, f"Thread {doc_id}", body, "reddit", f"r/{TEAM_A_SLUG}", date_str),
            )
            conn.execute(
                "INSERT INTO conversation_document_targets VALUES (?,?,?,?,?,?)",
                (doc_id, doc_id, TEAM_A_ID, None, "team", 0.0),
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


@pytest.fixture()
def db_one_season():
    """DB with only 1 season of docs — should produce no era terms."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_schema(conn)
    conn.execute(
        "INSERT INTO teams VALUES (?,?,?,?,?,?)",
        (TEAM_A_ID, TEAM_A_SLUG, TEAM_A_SCHOOL, "Michigan", "Michigan", "Ann Arbor"),
    )
    date_str = "2023-10-01T12:00:00Z"
    for i in range(80):
        body = f"{FOOTBALL_ANCHORS} {TERM_2023} {TERM_2023} doc {i}"
        conn.execute(
            "INSERT INTO conversation_documents VALUES (?,?,?,?,?,?,0,0,NULL)",
            (i + 1, f"Thread {i+1}", body, "reddit", f"r/{TEAM_A_SLUG}", date_str),
        )
        conn.execute(
            "INSERT INTO conversation_document_targets VALUES (?,?,?,?,?,?)",
            (i + 1, i + 1, TEAM_A_ID, None, "team", 0.0),
        )
    conn.commit()
    return _MemoryDB(conn)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dry_run_returns_zero_writes(db):
    result = compute_team_eras(db, seasons=SEASONS, commit=False)
    assert result["terms_written"] == 0
    assert result["teams_written"] == 0
    # No rows in DB either
    rows = db.query_all("SELECT * FROM team_discourse_era_terms")
    assert len(rows) == 0


def test_commit_writes_era_terms(db):
    result = compute_team_eras(db, seasons=SEASONS, top_n=8, commit=True)
    assert result["terms_written"] > 0
    assert result["teams_written"] >= 1
    assert result["docs_scanned"] > 0
    rows = db.query_all("SELECT * FROM team_discourse_era_terms")
    assert len(rows) > 0


def test_distinctive_term_appears_in_correct_season(db):
    """TERM_2023 should be top-ranked for 2023 but not dominant in 2024."""
    compute_team_eras(db, seasons=SEASONS, top_n=8, commit=True)

    rows_2023 = db.query_all(
        "SELECT term, term_rank FROM team_discourse_era_terms "
        "WHERE team_id=? AND season_year=2023 ORDER BY term_rank",
        (TEAM_A_ID,),
    )
    rows_2024 = db.query_all(
        "SELECT term FROM team_discourse_era_terms "
        "WHERE team_id=? AND season_year=2024",
        (TEAM_A_ID,),
    )

    terms_2023 = [r["term"] for r in rows_2023]
    terms_2024 = [r["term"] for r in rows_2024]

    # TERM_2023 must appear prominently in 2023 results
    assert TERM_2023 in terms_2023
    # TERM_2024 must appear in 2024 results but not necessarily dominate 2023
    assert TERM_2024 in terms_2024
    # The two distinctive terms should not both appear in the same season
    assert not (TERM_2023 in terms_2024 and TERM_2024 in terms_2023)


def test_team_with_only_one_season_gets_no_era_terms(db_one_season):
    """A team with docs in only 1 season cannot form cross-season contrast."""
    result = compute_team_eras(db_one_season, seasons=SEASONS, min_seasons=2, commit=True)
    rows = db_one_season.query_all("SELECT * FROM team_discourse_era_terms")
    assert len(rows) == 0
    assert result["teams_written"] == 0


def test_structural_terms_excluded(db):
    """The team name ('michigan') must not appear as an era term."""
    compute_team_eras(db, seasons=SEASONS, top_n=8, commit=True)
    rows = db.query_all(
        "SELECT term FROM team_discourse_era_terms WHERE team_id=?",
        (TEAM_A_ID,),
    )
    terms = {r["term"].lower() for r in rows}
    assert "michigan" not in terms
    assert "wolverines" not in terms


def test_idempotency_no_duplicates(db):
    """Running commit=True twice must not duplicate rows (UNIQUE constraint enforced)."""
    compute_team_eras(db, seasons=SEASONS, top_n=8, commit=True)
    first_count = db.query_one("SELECT COUNT(*) AS n FROM team_discourse_era_terms")["n"]

    # Second run — should upsert/replace, not append duplicates
    compute_team_eras(db, seasons=SEASONS, top_n=8, commit=True)
    second_count = db.query_one("SELECT COUNT(*) AS n FROM team_discourse_era_terms")["n"]

    assert second_count == first_count


def test_result_dict_has_required_keys(db):
    result = compute_team_eras(db, seasons=SEASONS, commit=False)
    for key in ("teams_written", "terms_written", "docs_scanned", "seasons"):
        assert key in result, f"missing key: {key}"
