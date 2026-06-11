"""Tests for cfb_rankings.discourse.mirror (Language Layer wave 2, package A3).

The rivalry mirror contrasts what team A's fans say *about rival B* against what
team B's fans say *about rival A*, using +/-12-token windows around rival
mentions (the validated prototype approach in scripts/discourse_keyness_prototype
rival_windows). Output lands in team_discourse_mirror.

Per the wave-2 contract these tests assert:

  1. a word that dominates team B's rival-windows ranks for side B with z>=1.96
  2. school-name words are excluded from the windows
  3. a generic-seed boilerplate word is excluded
  4. an idempotent re-run does not accumulate / duplicate rows
  5. a dry run (commit=False) writes nothing

The corpus is deterministic (no randomness), entirely in-memory sqlite — NO
network, NO real cfb_rankings.db. Every synthetic doc carries football anchors
("quarterback touchdown recruiting depth chart") so it clears the Stage-1
relevance gate in cfb_rankings.ingest.relevance.score_text.

Fixture style is reused verbatim from tests/test_discourse_keyness.py (the
_MemoryDB wrapper, hand-built schema incl. the contract DDL for the new table).
"""
from __future__ import annotations

import sqlite3

import pytest

# Implementation is being written in parallel against the contract; importing it
# is the first thing these tests exercise. Until it lands, every test in this
# module errors on ImportError (a missing-implementation signal, not a logic bug).
from cfb_rankings.discourse.mirror import compute_discourse_mirror


# ---------------------------------------------------------------------------
# Constants tied to the contract / synthetic corpus
# ---------------------------------------------------------------------------

# A date in (year, month>=7) belongs to that calendar year's CFB season; dating
# docs 2025-09-15 resolves to season_year=2025 via resolve_week.
CORPUS_DATE = "2025-09-15T12:00:00Z"
SEASON_YEAR = 2025

# Two rival teams (a real seeded blood rivalry: The Game).
TEAM_A_ID = 293
TEAM_A_SLUG = "michigan"
TEAM_A_SCHOOL = "Michigan"
TEAM_A_NICK = "wolverines"

TEAM_B_ID = 195
TEAM_B_SLUG = "ohio-state"
TEAM_B_SCHOOL = "Ohio State"
TEAM_B_NICK = "buckeyes"

# The word team B's fans pour onto team A inside their rival-windows. Made-up so
# it can never collide with any stopword/structural/junk/generic set. It must win
# side B (= the team_id=B / rival_team_id=A side).
TROPHY = "trophyword"

# A generic-seed boilerplate word (must be in seeds/discourse_generic_terms.yaml,
# contract A1). It appears heavily in B's rival-windows but must be excluded.
GENERIC = "highlights"

# Football anchors to clear the Stage-1 relevance gate (from relevance._CATEGORIES).
FOOTBALL_ANCHORS = "quarterback touchdown recruiting depth chart"


# ---------------------------------------------------------------------------
# Schema (engine reads + the wave-2 output table, DDL copied from the contract)
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
            is_removed               INTEGER DEFAULT 0,
            relevance_ml_score       REAL
        );

        CREATE TABLE conversation_document_targets (
            conversation_document_id INTEGER NOT NULL,
            target_type              TEXT NOT NULL,
            team_id                  INTEGER,
            player_id                INTEGER,
            target_label             TEXT,
            toxicity_score           REAL
        );

        CREATE TABLE chronicle_banlist (
            phrase_id      INTEGER PRIMARY KEY,
            phrase         TEXT NOT NULL,
            kind           TEXT NOT NULL,
            severity       REAL NOT NULL DEFAULT 1.0,
            is_active      INTEGER NOT NULL DEFAULT 1,
            added_by       TEXT,
            created_at_utc TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- One row per pair (scout: team_a_id / team_b_id, NOT team_id_a/b).
        CREATE TABLE rivalry_pairs (
            rivalry_pair_id INTEGER PRIMARY KEY,
            rivalry_slug    TEXT NOT NULL,
            rivalry_name    TEXT NOT NULL,
            team_a_id       INTEGER NOT NULL,
            team_b_id       INTEGER NOT NULL,
            tier            TEXT NOT NULL DEFAULT 'classic',
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Wave-2 output table — DDL copied verbatim from contract A3 so the
        -- idempotency assertion exercises the real UNIQUE constraint.
        CREATE TABLE team_discourse_mirror (
            team_discourse_mirror_id INTEGER PRIMARY KEY,
            team_id                  INTEGER NOT NULL,
            rival_team_id            INTEGER NOT NULL,
            season_year              INTEGER NOT NULL,
            term                     TEXT NOT NULL,
            term_rank                INTEGER NOT NULL,
            window_count             INTEGER NOT NULL,
            z_score                  REAL NOT NULL,
            side_token_count         INTEGER NOT NULL,
            rival_mention_doc_count  INTEGER NOT NULL,
            sample_quote             TEXT,
            sample_quote_source      TEXT,
            model_version            TEXT NOT NULL,
            computed_at_utc          TEXT NOT NULL,
            UNIQUE(team_id, rival_team_id, season_year, term)
        );

        CREATE INDEX idx_team_discourse_mirror_lookup
            ON team_discourse_mirror (team_id, rival_team_id, season_year, term_rank);
        """
    )


# ---------------------------------------------------------------------------
# Database wrapper shim (identical surface to the wave-1 test)
# ---------------------------------------------------------------------------


class _MemoryDB:
    """Minimal stand-in for cfb_rankings.db.Database over one sqlite conn."""

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
# Synthetic corpus builders
# ---------------------------------------------------------------------------


def _insert_doc(
    conn: sqlite3.Connection,
    doc_id: int,
    body: str,
    *,
    source_name: str = "reddit",
    source_subchannel: str = "MichiganWolverines",
    title: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO conversation_documents (
            conversation_document_id, source_name, source_subchannel,
            title_text, body_text, external_created_at_utc, is_deleted, is_removed
        ) VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (doc_id, source_name, source_subchannel, title, body, CORPUS_DATE),
    )


def _tag(
    conn: sqlite3.Connection,
    doc_id: int,
    team_id: int,
    *,
    toxicity: float = 0.05,
) -> None:
    conn.execute(
        """
        INSERT INTO conversation_document_targets (
            conversation_document_id, target_type, team_id, player_id,
            target_label, toxicity_score
        ) VALUES (?, 'team', ?, NULL, NULL, ?)
        """,
        (doc_id, team_id, toxicity),
    )


def _build_corpus(conn: sqlite3.Connection) -> None:
    """Deterministic two-team rivalry corpus.

    Side B (team B fans talking about rival A): every doc mentions team A by its
    nickname, embeds the distinctive TROPHY word and the GENERIC boilerplate word
    AND a co-mentioned third school name (oklahoma) that must be stripped as a
    school-name token. The TROPHY word should win side B; GENERIC + the
    school-name word must NOT survive.

    Side A (team A fans talking about rival B): plain rival chatter, no TROPHY —
    so the asymmetry is real and side B's distinctive word can't bleed in.
    """
    conn.executemany(
        """
        INSERT INTO teams (team_id, slug, school_name, short_name, canonical_name)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (TEAM_A_ID, TEAM_A_SLUG, TEAM_A_SCHOOL, TEAM_A_SCHOOL, TEAM_A_SCHOOL),
            (TEAM_B_ID, TEAM_B_SLUG, TEAM_B_SCHOOL, TEAM_B_SCHOOL, TEAM_B_SCHOOL),
            # A co-mentioned third school so its name shows up inside windows and
            # must be stripped (the "Texas, Oklahoma, Michigan..." list-post case).
            (129, "oklahoma", "Oklahoma", "Oklahoma", "Oklahoma"),
        ],
    )

    # One seeded rivalry pair (a<->b). pairs=None path reads this table.
    conn.execute(
        """
        INSERT INTO rivalry_pairs (
            rivalry_slug, rivalry_name, team_a_id, team_b_id, tier, is_active
        ) VALUES (?, ?, ?, ?, 'blood', 1)
        """,
        ("michigan-vs-ohio-state", "The Game", TEAM_A_ID, TEAM_B_ID),
    )

    doc_id = 1

    # -- 60 side-B docs: team B fans, mention rival A (nickname), TROPHY + GENERIC
    #    + a co-mentioned school name. TROPHY should dominate B's windows.
    for i in range(60):
        body = (
            f"The {TEAM_A_NICK} got the {TROPHY} again this year. "
            f"Watch the {GENERIC} of {TEAM_A_NICK} losing the {TROPHY}. "
            f"Even oklahoma fans laughed at the {TEAM_A_NICK}. "
            f"{FOOTBALL_ANCHORS}. {TROPHY} stays home."
        )
        _insert_doc(
            conn,
            doc_id,
            body,
            source_name="reddit",
            source_subchannel="OhioStateFootball",
        )
        _tag(conn, doc_id, TEAM_B_ID, toxicity=0.05)
        doc_id += 1

    # -- 60 side-A docs: team A fans, mention rival B (nickname). Ordinary rival
    #    chatter — never the TROPHY word.
    fillers = ["scheme", "tempo", "rotation", "secondary", "tackling"]
    for i in range(60):
        filler = fillers[i % len(fillers)]
        body = (
            f"The {TEAM_B_NICK} {filler} looked beatable this week. "
            f"Our defense will give the {TEAM_B_NICK} trouble. "
            f"{FOOTBALL_ANCHORS}. {filler} matchup vs the {TEAM_B_NICK}."
        )
        _insert_doc(
            conn,
            doc_id,
            body,
            source_name="reddit",
            source_subchannel="MichiganWolverines",
        )
        _tag(conn, doc_id, TEAM_A_ID, toxicity=0.05)
        doc_id += 1

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


def _side_rows(
    conn: sqlite3.Connection, team_id: int, rival_id: int
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM team_discourse_mirror
        WHERE team_id = ? AND rival_team_id = ? AND season_year = ?
        ORDER BY term_rank ASC
        """,
        (team_id, rival_id, SEASON_YEAR),
    ).fetchall()


def _side_terms(conn: sqlite3.Connection, team_id: int, rival_id: int) -> set[str]:
    return {r["term"] for r in _side_rows(conn, team_id, rival_id)}


# ---------------------------------------------------------------------------
# Test 1: a dominant rival-window word ranks for side B with z >= 1.96
# ---------------------------------------------------------------------------


def test_trophyword_ranks_for_side_b_with_significant_z(db, conn):
    result = compute_discourse_mirror(db, seasons=[SEASON_YEAR], commit=True)
    assert result, "expected a non-empty result summary"

    # Side B = team B talking about rival A.
    rows = _side_rows(conn, TEAM_B_ID, TEAM_A_ID)
    assert rows, "expected side-B (team B about rival A) mirror rows"

    terms = {r["term"]: r for r in rows}
    assert TROPHY in terms, (
        f"expected {TROPHY!r} to surface on side B, got {sorted(terms)}"
    )
    row = terms[TROPHY]
    assert row["z_score"] >= 1.96, f"trophy z below floor: {row['z_score']}"
    assert row["window_count"] >= 5, "trophy should clear the min_count=5 floor"
    assert row["side_token_count"] > 0, "side_token_count must be populated"
    assert row["rival_mention_doc_count"] >= 60, (
        "every side-B doc mentions rival A — doc count should be >= 60"
    )
    assert row["model_version"], "model_version must be stamped"


# ---------------------------------------------------------------------------
# Test 2: school-name words are excluded from windows
# ---------------------------------------------------------------------------


def test_school_name_words_excluded_from_windows(db, conn):
    compute_discourse_mirror(db, seasons=[SEASON_YEAR], commit=True)
    terms = _side_terms(conn, TEAM_B_ID, TEAM_A_ID)

    assert terms, "expected surviving side-B terms"
    # Co-mentioned third school + both teams' own school/nickname words must be
    # stripped from the windows (the list-post contamination guard).
    for school in ("oklahoma", "michigan", "wolverines", "ohio", "buckeyes"):
        assert school not in terms, (
            f"school-name token {school!r} must be excluded, got {sorted(terms)}"
        )
    # The genuine rival-talk word survives.
    assert TROPHY in terms


# ---------------------------------------------------------------------------
# Test 3: a generic-seed boilerplate word is excluded
# ---------------------------------------------------------------------------


def test_generic_seed_word_excluded(db, conn):
    compute_discourse_mirror(db, seasons=[SEASON_YEAR], commit=True)
    terms = _side_terms(conn, TEAM_B_ID, TEAM_A_ID)
    assert GENERIC not in terms, (
        f"generic-seed term {GENERIC!r} must be filtered, got {sorted(terms)}"
    )
    assert TROPHY in terms  # filtering generics didn't nuke the real signal


# ---------------------------------------------------------------------------
# Test 4: idempotent re-run does not duplicate / accumulate rows
# ---------------------------------------------------------------------------


def test_idempotent_rerun_no_duplicates(db, conn):
    compute_discourse_mirror(db, seasons=[SEASON_YEAR], commit=True)
    first = conn.execute(
        "SELECT COUNT(*) FROM team_discourse_mirror WHERE season_year = ?",
        (SEASON_YEAR,),
    ).fetchone()[0]
    assert first > 0

    compute_discourse_mirror(db, seasons=[SEASON_YEAR], commit=True)
    second = conn.execute(
        "SELECT COUNT(*) FROM team_discourse_mirror WHERE season_year = ?",
        (SEASON_YEAR,),
    ).fetchone()[0]

    assert second == first, (
        f"re-run should clear+reinsert, not accumulate: {first} -> {second}"
    )
    dupes = conn.execute(
        """
        SELECT team_id, rival_team_id, term, COUNT(*) c
        FROM team_discourse_mirror
        WHERE season_year = ?
        GROUP BY team_id, rival_team_id, term HAVING c > 1
        """,
        (SEASON_YEAR,),
    ).fetchall()
    assert dupes == [], f"duplicate (side, term) rows after re-run: {[tuple(d) for d in dupes]}"


# ---------------------------------------------------------------------------
# Test 5: dry run (commit=False) writes nothing
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(db, conn):
    compute_discourse_mirror(db, seasons=[SEASON_YEAR], commit=False)
    n = conn.execute("SELECT COUNT(*) FROM team_discourse_mirror").fetchone()[0]
    assert n == 0, f"commit=False must not write rows, found {n}"


# ---------------------------------------------------------------------------
# Test 6: explicit pairs override targets the requested pair
# ---------------------------------------------------------------------------


def test_explicit_pairs_override(db, conn):
    # pairs param overrides the rivalry_pairs table read (list of (slugA, slugB)).
    compute_discourse_mirror(
        db,
        seasons=[SEASON_YEAR],
        pairs=[(TEAM_A_SLUG, TEAM_B_SLUG)],
        commit=True,
    )
    rows = _side_rows(conn, TEAM_B_ID, TEAM_A_ID)
    assert rows, "explicit pair should still produce mirror rows"
    assert TROPHY in {r["term"] for r in rows}
