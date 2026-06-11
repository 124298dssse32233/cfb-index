"""Tests for cfb_rankings.discourse.keyness (Language Layer wave 1).

These tests run entirely against a synthetic in-memory sqlite corpus — NO
network, NO real cfb_rankings.db. They assert the five keyness contract
properties:

  1. a word used heavily by team A and rarely elsewhere ranks #1 with z >= 1.96
  2. structural terms (the team name) are excluded
  3. a banlisted term is excluded
  4. docs in an excluded city-sub subchannel are excluded from the team corpus
  5. an idempotent re-run does not duplicate rows

The corpus is deterministic (no randomness) so the ranking is stable. Every
synthetic doc carries 2-3 football anchors ("quarterback", "touchdown",
"recruiting", "depth chart", ...) so it clears the Stage-1 relevance gate in
``cfb_rankings.ingest.relevance.score_text`` (is_football requires >= 1 anchor).

Following the established test conventions (tests/test_chronicle_*.py): plain
pytest, a tmp/in-memory sqlite fixture, schema built from the migration .sql
when present, else hand-built CREATE TABLEs matching the live column names the
prototype + scout report (see scripts/discourse_keyness_prototype.py).
"""
from __future__ import annotations

import sqlite3

import pytest

# Implementation is being written in parallel against the contract; importing it
# is the first thing these tests exercise. Until it lands, every test in this
# module errors on ImportError (a missing-implementation signal, not a logic bug).
from cfb_rankings.discourse.keyness import compute_team_keyness


# ---------------------------------------------------------------------------
# Constants tied to the contract / synthetic corpus
# ---------------------------------------------------------------------------

# Season the whole corpus is dated into. resolve_week uses the Jul-Jun
# convention: a date in (year, month>=7) belongs to that calendar year's season.
# We date docs 2025-09-15, which resolves to season_year=2025.
CORPUS_DATE = "2025-09-15T12:00:00Z"
SEASON_YEAR = 2025

# The distinctive word team A's fans pour on and nobody else uses. Made-up so it
# can never collide with anything in the stopword/structural/banlist sets.
DISTINCTIVE = "zorblat"
# A junk word that only appears in the excluded city-sub docs.
CITY_JUNK = "cityjunk"
# A banlisted term seeded into chronicle_banlist that must be filtered out even
# though team A's fans use it heavily.
BANNED = "slurword"

# Team A is the program under test. Its slug feeds the structural-term builder.
TEAM_A_ID = 293
TEAM_A_SLUG = "michigan"
TEAM_A_SCHOOL = "Michigan"
# A second team to make the "rest of corpus" non-trivial.
TEAM_B_ID = 195
TEAM_B_SLUG = "ohio-state"
TEAM_B_SCHOOL = "Ohio State"

# Two or three football anchors per doc to clear the relevance gate. Drawn
# straight from cfb_rankings.ingest.relevance._CATEGORIES.
FOOTBALL_ANCHORS = "quarterback touchdown recruiting depth chart"

# An excluded city subreddit (per the contract: 'Columbus','Eugene','AnnArbor',
# plus any in seeds/discourse_city_subs.yaml). AnnArbor is the city sub for the
# team-A slug, so its docs must NOT contribute to Michigan's corpus.
CITY_SUB = "AnnArbor"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def _create_schema(conn: sqlite3.Connection) -> None:
    """Hand-build the minimal tables the engine reads + the output table.

    Column names mirror the live schema as used by
    scripts/discourse_keyness_prototype.py and the scout-reported
    chronicle_banlist PRAGMA. The team_discourse_terms DDL is copied from the
    wave-1 contract verbatim (so the idempotency assertion exercises the real
    UNIQUE constraint).
    """
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

        CREATE INDEX idx_team_discourse_terms_lookup
            ON team_discourse_terms (team_id, season_year, week, term_rank);
        """
    )


# ---------------------------------------------------------------------------
# Database wrapper shim
#
# The engine takes the project's `Database` wrapper (named-param API:
# query_all / query_one / execute, plus session()/connection() contexts). We
# wrap a single in-memory sqlite3 connection so the same connection is reused
# across the engine's read pass AND its write pass (a fresh connection per call
# would lose the :memory: schema). Named-param SQL (:name) works directly with
# sqlite3 when passed a dict, so this shim is intentionally thin.
# ---------------------------------------------------------------------------


class _MemoryDB:
    """Minimal stand-in for cfb_rankings.db.Database over one sqlite conn."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # -- read surface --------------------------------------------------------
    def query_all(self, sql: str, params=None):
        cur = self._conn.execute(sql, params or {})
        return cur.fetchall()

    def query_one(self, sql: str, params=None):
        cur = self._conn.execute(sql, params or {})
        return cur.fetchone()

    # -- write surface -------------------------------------------------------
    def execute(self, sql: str, params=None):
        cur = self._conn.execute(sql, params or {})
        self._conn.commit()
        return cur

    def executemany(self, sql: str, seq_of_params):
        cur = self._conn.executemany(sql, seq_of_params)
        self._conn.commit()
        return cur

    # -- lifecycle contexts the engine may open ------------------------------
    def connection(self):
        return _PassthroughCtx(self._conn)

    def session(self):
        return _NoopCtx()

    # raw escape hatch some wrappers expose
    @property
    def conn(self):
        return self._conn

    def cursor(self):
        return self._conn.cursor()


class _PassthroughCtx:
    """Context manager that yields the shared connection without closing it."""

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
    """Deterministic corpus:

    - 60 team-A reddit docs heavy with DISTINCTIVE ('zorblat'), each carrying
      football anchors so they clear the relevance gate; some also carry the
      team name (structural) + the banned word, to prove those get filtered.
    - 200 background team-B docs that never mention 'zorblat'.
    - 6 city-sub (AnnArbor) docs containing CITY_JUNK ('cityjunk'); these are
      tagged to team A but live in an excluded subchannel, so they must NOT
      feed team A's corpus.
    """
    # Teams rows: the engine resolves --teams slugs AND builds the programmatic
    # structural-term sets from these rows (school_name / slug words / etc).
    conn.executemany(
        """
        INSERT INTO teams (team_id, slug, school_name, short_name, canonical_name)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (TEAM_A_ID, TEAM_A_SLUG, TEAM_A_SCHOOL, TEAM_A_SCHOOL, TEAM_A_SCHOOL),
            (TEAM_B_ID, TEAM_B_SLUG, TEAM_B_SCHOOL, TEAM_B_SCHOOL, TEAM_B_SCHOOL),
        ],
    )

    doc_id = 1

    # -- 60 team-A fan docs: 'zorblat' on every one, plus structural team name
    #    and the banned word on every one. The DISTINCTIVE word should win #1;
    #    the team name + banned word must be filtered despite identical volume.
    for i in range(60):
        body = (
            f"The {DISTINCTIVE} was incredible today. {TEAM_A_SCHOOL} fans love "
            f"the {DISTINCTIVE}. What a {BANNED} performance. "
            f"{FOOTBALL_ANCHORS}. Our {DISTINCTIVE} energy is unmatched."
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

    # -- 200 background team-B docs: ordinary football chatter, no 'zorblat'.
    #    Distinct filler nouns so the global vocab is realistic but the
    #    distinctive word stays unique to team A.
    fillers = ["scheme", "tempo", "rotation", "secondary", "tackling"]
    for i in range(200):
        filler = fillers[i % len(fillers)]
        body = (
            f"Talking about the {filler} this week. {TEAM_B_SCHOOL} looked sharp. "
            f"{FOOTBALL_ANCHORS}. The {filler} adjustments paid off."
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

    # -- 6 city-sub docs (excluded subchannel) tagged to team A, full of
    #    CITY_JUNK. If the city-sub exclusion fails, 'cityjunk' would surface
    #    as a distinctive team-A term.
    for i in range(6):
        body = (
            f"The {CITY_JUNK} downtown is open. {CITY_JUNK} parking is rough. "
            f"{FOOTBALL_ANCHORS}. More {CITY_JUNK} news from {CITY_JUNK} hall."
        )
        _insert_doc(
            conn,
            doc_id,
            body,
            source_name="reddit",
            source_subchannel=CITY_SUB,
        )
        _tag(conn, doc_id, TEAM_A_ID, toxicity=0.05)
        doc_id += 1

    conn.commit()


def _seed_banlist(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO chronicle_banlist (phrase, kind, severity, is_active, added_by)
        VALUES (?, 'cfb_specific', 2.0, 1, 'test_seed')
        """,
        (BANNED,),
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
    _seed_banlist(c)
    return c


@pytest.fixture()
def db(conn: sqlite3.Connection) -> _MemoryDB:
    return _MemoryDB(conn)


# ---------------------------------------------------------------------------
# Helpers for reading results back out
# ---------------------------------------------------------------------------


def _team_terms(conn: sqlite3.Connection, team_id: int = TEAM_A_ID) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM team_discourse_terms
        WHERE team_id = ? AND season_year = ? AND week = 0
        ORDER BY term_rank ASC
        """,
        (team_id, SEASON_YEAR),
    ).fetchall()


def _term_set(conn: sqlite3.Connection, team_id: int = TEAM_A_ID) -> set[str]:
    return {r["term"] for r in _team_terms(conn, team_id)}


# ---------------------------------------------------------------------------
# Test 1: distinctive word ranks #1 with z >= 1.96
# ---------------------------------------------------------------------------


def test_distinctive_word_ranks_first_with_significant_z(db, conn):
    result = compute_team_keyness(
        db, seasons=[SEASON_YEAR], teams=[TEAM_A_SLUG], commit=True
    )

    assert result["teams_written"] >= 1
    assert result["terms_written"] >= 1
    assert SEASON_YEAR in result["seasons"]

    rows = _team_terms(conn, TEAM_A_ID)
    assert rows, "expected team-A discourse rows after a committed run"

    top = rows[0]
    assert top["term"] == DISTINCTIVE, (
        f"expected {DISTINCTIVE!r} ranked #1, got {top['term']!r}"
    )
    assert top["term_rank"] == 1
    assert top["z_score"] >= 1.96, f"top term z below floor: {top['z_score']}"
    # Heavy on team A, absent elsewhere -> a large 'x the field' ratio.
    assert top["mention_count"] >= 60
    assert top["rest_count"] == 0
    assert top["rate_ratio"] > 1.0
    # The signature magnitude band kicks in at >= 10x; with 0 rest mentions this
    # is overwhelmingly above that floor.
    assert top["magnitude_band"] == "signature"
    # Corpus-size receipts populated.
    assert top["team_doc_count"] >= 60
    assert top["team_token_count"] > 0
    assert top["model_version"] == "discourse-keyness-v1"


# ---------------------------------------------------------------------------
# Test 2: structural terms (the team name) are excluded
# ---------------------------------------------------------------------------


def test_structural_team_name_excluded(db, conn):
    compute_team_keyness(db, seasons=[SEASON_YEAR], teams=[TEAM_A_SLUG], commit=True)
    terms = _term_set(conn, TEAM_A_ID)

    assert terms, "expected some surviving terms"
    # School name + slug words must be filtered programmatically.
    for structural in ("michigan", "wolverines", "wolverine"):
        assert structural not in terms, (
            f"structural term {structural!r} should be excluded, got {sorted(terms)}"
        )
    # The genuinely distinctive cultural word survives the structural filter.
    assert DISTINCTIVE in terms


# ---------------------------------------------------------------------------
# Test 3: banlisted term is excluded
# ---------------------------------------------------------------------------


def test_banlisted_term_excluded(db, conn):
    compute_team_keyness(db, seasons=[SEASON_YEAR], teams=[TEAM_A_SLUG], commit=True)
    terms = _term_set(conn, TEAM_A_ID)
    assert BANNED not in terms, (
        f"banlisted term {BANNED!r} should be filtered, got {sorted(terms)}"
    )
    assert DISTINCTIVE in terms  # sanity: filtering banned didn't nuke everything


# ---------------------------------------------------------------------------
# Test 4: city-sub docs excluded from the team corpus
# ---------------------------------------------------------------------------


def test_city_sub_docs_excluded(db, conn):
    compute_team_keyness(db, seasons=[SEASON_YEAR], teams=[TEAM_A_SLUG], commit=True)
    terms = _term_set(conn, TEAM_A_ID)
    assert CITY_JUNK not in terms, (
        f"city-sub junk {CITY_JUNK!r} leaked into team corpus, got {sorted(terms)}"
    )
    # The 6 city-sub docs must not be counted toward team A's doc receipts: the
    # 60 fan docs are the only contributors.
    rows = _team_terms(conn, TEAM_A_ID)
    assert rows
    assert rows[0]["team_doc_count"] == 60, (
        f"team_doc_count should count only the 60 fan-voice docs (city subs "
        f"excluded), got {rows[0]['team_doc_count']}"
    )


# ---------------------------------------------------------------------------
# Test 5: idempotent re-run does not duplicate rows
# ---------------------------------------------------------------------------


def test_idempotent_rerun_no_duplicates(db, conn):
    compute_team_keyness(db, seasons=[SEASON_YEAR], teams=[TEAM_A_SLUG], commit=True)
    first = conn.execute(
        "SELECT COUNT(*) FROM team_discourse_terms WHERE team_id = ?",
        (TEAM_A_ID,),
    ).fetchone()[0]
    assert first > 0

    compute_team_keyness(db, seasons=[SEASON_YEAR], teams=[TEAM_A_SLUG], commit=True)
    second = conn.execute(
        "SELECT COUNT(*) FROM team_discourse_terms WHERE team_id = ?",
        (TEAM_A_ID,),
    ).fetchone()[0]

    assert second == first, (
        f"re-run should DELETE+reinsert, not accumulate: {first} -> {second}"
    )
    # And the UNIQUE(team_id, season_year, week, term) constraint must hold: no
    # (term) appears twice for the same (team, season, week).
    dupes = conn.execute(
        """
        SELECT term, COUNT(*) c FROM team_discourse_terms
        WHERE team_id = ? AND season_year = ? AND week = 0
        GROUP BY term HAVING c > 1
        """,
        (TEAM_A_ID, SEASON_YEAR),
    ).fetchall()
    assert dupes == [], f"duplicate terms after re-run: {[tuple(d) for d in dupes]}"


# ---------------------------------------------------------------------------
# Test 6: dry run (commit=False) writes nothing
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(db, conn):
    result = compute_team_keyness(
        db, seasons=[SEASON_YEAR], teams=[TEAM_A_SLUG], commit=False
    )
    # Dry run still computes + reports counts...
    assert "docs_scanned" in result
    assert "docs_gated" in result
    # ...but persists no rows.
    n = conn.execute("SELECT COUNT(*) FROM team_discourse_terms").fetchone()[0]
    assert n == 0, f"commit=False must not write rows, found {n}"


# ---------------------------------------------------------------------------
# Test 7: return-dict shape matches the contract
# ---------------------------------------------------------------------------


def test_return_dict_shape(db):
    result = compute_team_keyness(
        db, seasons=[SEASON_YEAR], teams=[TEAM_A_SLUG], commit=True
    )
    for key in ("teams_written", "terms_written", "docs_scanned", "docs_gated", "seasons"):
        assert key in result, f"missing key {key!r} in result dict: {sorted(result)}"
    assert isinstance(result["seasons"], (list, tuple))
