"""Tests for cfb_rankings.discourse.voice_profile (Language Layer wave 2, A4).

compute_fanbase_voice aggregates per-team fan-voice emotion/sentiment/sarcasm
into one fanbase_voice_profile row per (team, season), but ONLY for teams whose
mention count clears the cohort floor (min_mentions). Percentile ranks +
optimism_rank are computed WITHIN that season's cohort at write time, and the
season is fully cleared before insert (no stale below-floor rows).

Per the wave-2 contract these tests assert:

  1. cohort_size = number of teams above the floor (below-floor team absent)
  2. percentile ordering is correct (more-optimistic team ranks higher)
  3. a season clear removes stale rows from a prior run
  4. a dry run (commit=False) writes nothing

Deterministic, in-memory sqlite — NO network, NO real cfb_rankings.db. Docs carry
football anchors so the fan-voice corpus + relevance gate accept them. Fixture
style reused from tests/test_discourse_keyness.py.
"""
from __future__ import annotations

import sqlite3

import pytest

# Implementation lands in parallel; the import is the first contract assertion.
# Until then every test errors on ImportError (missing-impl signal, not a bug).
from cfb_rankings.discourse.voice_profile import compute_fanbase_voice


CORPUS_DATE = "2025-09-15T12:00:00Z"
SEASON_YEAR = 2025
FOOTBALL_ANCHORS = "quarterback touchdown recruiting depth chart"

# Three teams: HIGH + LOW above the cohort floor (min_mentions), TINY below it.
# HIGH is the most-optimistic, joyful fanbase; LOW is angry/doom; TINY is small.
HIGH_ID, HIGH_SLUG, HIGH_NAME = 293, "michigan", "Michigan"
LOW_ID, LOW_SLUG, LOW_NAME = 195, "ohio-state", "Ohio State"
TINY_ID, TINY_SLUG, TINY_NAME = 291, "oregon", "Oregon"

MIN_MENTIONS = 300


# ---------------------------------------------------------------------------
# Schema (engine reads + the wave-2 output table, DDL from contract A4)
# ---------------------------------------------------------------------------


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE teams (
            team_id        INTEGER PRIMARY KEY,
            slug           TEXT,
            school_name    TEXT,
            short_name     TEXT,
            canonical_name TEXT
        );

        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY,
            source_name              TEXT,
            source_subchannel        TEXT,
            title_text               TEXT,
            body_text                TEXT,
            external_created_at_utc  TEXT,
            is_deleted               INTEGER DEFAULT 0,
            is_removed               INTEGER DEFAULT 0
        );

        CREATE TABLE conversation_document_targets (
            conversation_document_id INTEGER NOT NULL,
            target_type              TEXT NOT NULL,
            team_id                  INTEGER,
            player_id                INTEGER,
            target_label             TEXT,
            toxicity_score           REAL,
            sentiment_score          REAL,
            sarcasm_score            REAL,
            emotion_primary          TEXT
        );

        -- Wave-2 output table — DDL copied verbatim from contract A4.
        CREATE TABLE fanbase_voice_profile (
            fanbase_voice_profile_id INTEGER PRIMARY KEY,
            team_id        INTEGER NOT NULL,
            season_year    INTEGER NOT NULL,
            n_mentions     INTEGER NOT NULL,
            optimism_mean  REAL NOT NULL,
            joy_share      REAL NOT NULL,
            anger_share    REAL NOT NULL,
            doom_share     REAL NOT NULL,
            sarcasm_mean   REAL NOT NULL,
            optimism_pct   INTEGER NOT NULL,
            joy_pct        INTEGER NOT NULL,
            anger_pct      INTEGER NOT NULL,
            doom_pct       INTEGER NOT NULL,
            sarcasm_pct    INTEGER NOT NULL,
            optimism_rank  INTEGER NOT NULL,
            cohort_size    INTEGER NOT NULL,
            model_version  TEXT NOT NULL,
            computed_at_utc TEXT NOT NULL,
            UNIQUE(team_id, season_year)
        );
        """
    )


# ---------------------------------------------------------------------------
# Database wrapper shim
# ---------------------------------------------------------------------------


class _MemoryDB:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def query_all(self, sql: str, params=None):
        return self._conn.execute(sql, params or {}).fetchall()

    def query_one(self, sql: str, params=None):
        return self._conn.execute(sql, params or {}).fetchone()

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

    @property
    def conn(self):
        return self._conn

    def cursor(self):
        return self._conn.cursor()


class _PassthroughCtx:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *exc):
        return False


class _NoopCtx:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


# ---------------------------------------------------------------------------
# Corpus builders
# ---------------------------------------------------------------------------


def _build_team_mentions(
    conn: sqlite3.Connection,
    start_doc_id: int,
    team_id: int,
    n: int,
    *,
    sentiment: float,
    sarcasm: float,
    emotion: str,
    subchannel: str,
) -> int:
    """Insert n fan-voice docs all tagged to team_id with identical, controlled
    emotion/sentiment/sarcasm so the per-team aggregates are exact. Returns the
    next free doc_id.
    """
    doc_id = start_doc_id
    body = (
        f"Big game thoughts on the team. {FOOTBALL_ANCHORS}. "
        "The depth chart looks strong heading into the matchup."
    )
    for _ in range(n):
        conn.execute(
            """
            INSERT INTO conversation_documents (
                conversation_document_id, source_name, source_subchannel,
                title_text, body_text, external_created_at_utc, is_deleted, is_removed
            ) VALUES (?, 'reddit', ?, '', ?, ?, 0, 0)
            """,
            (doc_id, subchannel, body, CORPUS_DATE),
        )
        conn.execute(
            """
            INSERT INTO conversation_document_targets (
                conversation_document_id, target_type, team_id, player_id,
                target_label, toxicity_score, sentiment_score, sarcasm_score,
                emotion_primary
            ) VALUES (?, 'team', ?, NULL, NULL, 0.05, ?, ?, ?)
            """,
            (doc_id, team_id, sentiment, sarcasm, emotion),
        )
        doc_id += 1
    return doc_id


def _build_corpus(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT INTO teams (team_id, slug, school_name, short_name, canonical_name)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (HIGH_ID, HIGH_SLUG, HIGH_NAME, HIGH_NAME, HIGH_NAME),
            (LOW_ID, LOW_SLUG, LOW_NAME, LOW_NAME, LOW_NAME),
            (TINY_ID, TINY_SLUG, TINY_NAME, TINY_NAME, TINY_NAME),
        ],
    )

    doc_id = 1
    # HIGH: 400 mentions, very optimistic + joyful, low sarcasm. Above floor.
    doc_id = _build_team_mentions(
        conn, doc_id, HIGH_ID, 400,
        sentiment=0.8, sarcasm=0.1, emotion="optimism",
        subchannel="MichiganWolverines",
    )
    # LOW: 400 mentions, negative sentiment, anger emotion. Above floor.
    doc_id = _build_team_mentions(
        conn, doc_id, LOW_ID, 400,
        sentiment=-0.6, sarcasm=0.2, emotion="anger",
        subchannel="OhioStateFootball",
    )
    # TINY: 100 mentions (< MIN_MENTIONS=300). Must be excluded from the cohort.
    doc_id = _build_team_mentions(
        conn, doc_id, TINY_ID, 100,
        sentiment=0.3, sarcasm=0.1, emotion="joy",
        subchannel="ducks",
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    _create_schema(c)
    _build_corpus(c)
    return c


@pytest.fixture()
def db(conn: sqlite3.Connection) -> _MemoryDB:
    return _MemoryDB(conn)


# ---------------------------------------------------------------------------
# Result readers
# ---------------------------------------------------------------------------


def _profile_row(conn: sqlite3.Connection, team_id: int):
    return conn.execute(
        "SELECT * FROM fanbase_voice_profile WHERE team_id = ? AND season_year = ?",
        (team_id, SEASON_YEAR),
    ).fetchone()


# ---------------------------------------------------------------------------
# Test 1: cohort excludes the below-floor team; cohort_size = 2
# ---------------------------------------------------------------------------


def test_cohort_excludes_below_floor_team(db, conn):
    compute_fanbase_voice(
        db, seasons=[SEASON_YEAR], min_mentions=MIN_MENTIONS, commit=True
    )

    high = _profile_row(conn, HIGH_ID)
    low = _profile_row(conn, LOW_ID)
    tiny = _profile_row(conn, TINY_ID)

    assert high is not None, "HIGH team (400 mentions) should be in the cohort"
    assert low is not None, "LOW team (400 mentions) should be in the cohort"
    assert tiny is None, "TINY team (100 < 300) must be excluded from the cohort"

    # cohort_size is stamped on every written row and equals the # above floor.
    assert high["cohort_size"] == 2
    assert low["cohort_size"] == 2
    assert high["n_mentions"] == 400
    assert low["n_mentions"] == 400


# ---------------------------------------------------------------------------
# Test 2: percentile ordering — the more-optimistic fanbase ranks higher
# ---------------------------------------------------------------------------


def test_percentile_ordering(db, conn):
    compute_fanbase_voice(
        db, seasons=[SEASON_YEAR], min_mentions=MIN_MENTIONS, commit=True
    )
    high = _profile_row(conn, HIGH_ID)
    low = _profile_row(conn, LOW_ID)

    # HIGH has the larger optimism_mean -> higher optimism percentile + rank 1.
    assert high["optimism_mean"] > low["optimism_mean"]
    assert high["optimism_pct"] >= low["optimism_pct"]
    assert high["optimism_rank"] == 1, "most-optimistic fanbase ranks #1"
    assert low["optimism_rank"] == 2

    # LOW is the angry fanbase -> higher anger share + anger percentile.
    assert low["anger_share"] > high["anger_share"]
    assert low["anger_pct"] >= high["anger_pct"]

    # Percentiles are integers in [0, 100].
    for r in (high, low):
        for key in ("optimism_pct", "joy_pct", "anger_pct", "doom_pct", "sarcasm_pct"):
            val = r[key]
            assert isinstance(val, int)
            assert 0 <= val <= 100, f"{key}={val} out of [0,100]"


# ---------------------------------------------------------------------------
# Test 3: season clear removes stale rows from a prior run
# ---------------------------------------------------------------------------


def test_season_clear_removes_stale_rows(db, conn):
    # Pre-seed a stale row for a team that will NOT be in the recomputed cohort
    # (a phantom team_id 999). The season-clear must wipe it before insert.
    conn.execute(
        """
        INSERT INTO fanbase_voice_profile (
            team_id, season_year, n_mentions, optimism_mean, joy_share,
            anger_share, doom_share, sarcasm_mean, optimism_pct, joy_pct,
            anger_pct, doom_pct, sarcasm_pct, optimism_rank, cohort_size,
            model_version, computed_at_utc
        ) VALUES (
            999, ?, 500, 0.5, 0.5, 0.1, 0.1, 0.1, 50, 50, 50, 50, 50, 1, 1,
            'stale', '2026-01-01T00:00:00Z'
        )
        """,
        (SEASON_YEAR,),
    )
    conn.commit()

    compute_fanbase_voice(
        db, seasons=[SEASON_YEAR], min_mentions=MIN_MENTIONS, commit=True
    )

    stale = conn.execute(
        "SELECT COUNT(*) FROM fanbase_voice_profile "
        "WHERE team_id = 999 AND season_year = ?",
        (SEASON_YEAR,),
    ).fetchone()[0]
    assert stale == 0, "stale prior-run row must be cleared before insert"

    total = conn.execute(
        "SELECT COUNT(*) FROM fanbase_voice_profile WHERE season_year = ?",
        (SEASON_YEAR,),
    ).fetchone()[0]
    assert total == 2, f"expected exactly the 2 cohort rows, found {total}"


# ---------------------------------------------------------------------------
# Test 4: dry run (commit=False) writes nothing
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(db, conn):
    compute_fanbase_voice(
        db, seasons=[SEASON_YEAR], min_mentions=MIN_MENTIONS, commit=False
    )
    n = conn.execute("SELECT COUNT(*) FROM fanbase_voice_profile").fetchone()[0]
    assert n == 0, f"commit=False must not write rows, found {n}"
