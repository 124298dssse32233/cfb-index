"""Tests for the KWIC quote extraction module (Language Layer Wave 4).

Uses an in-memory SQLite database so no real DB or network access is required.
All tests are self-contained and can run with ``pytest tests/test_discourse_kwic.py``.
"""
from __future__ import annotations

import sqlite3

import pytest

from cfb_rankings.discourse.kwic import compute_kwic_quotes, _extract_passage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    """Return a fresh in-memory SQLite DB with the required schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE teams (
            team_id   INTEGER PRIMARY KEY,
            name      TEXT,
            slug      TEXT
        );

        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY,
            body_text    TEXT,
            title_text   TEXT,
            source_name  TEXT,
            source_subchannel TEXT,
            is_deleted   INTEGER DEFAULT 0,
            is_removed   INTEGER DEFAULT 0,
            relevance_ml_score REAL
        );

        CREATE TABLE conversation_document_targets (
            conversation_document_id INTEGER,
            team_id                  INTEGER,
            target_type              TEXT
        );

        CREATE TABLE team_discourse_terms (
            team_id      INTEGER,
            season_year  INTEGER,
            week         INTEGER,
            term         TEXT,
            term_rank    INTEGER
        );

        CREATE TABLE team_discourse_term_quotes (
            team_id         INTEGER,
            season_year     INTEGER,
            week            INTEGER,
            term            TEXT,
            position_index  INTEGER,
            passage         TEXT,
            computed_at_utc TEXT
        );
        """
    )
    return conn


def _seed_team(conn: sqlite3.Connection, team_id: int = 1) -> None:
    conn.execute(
        "INSERT INTO teams (team_id, name, slug) VALUES (?, ?, ?)",
        (team_id, "Test Bulldogs", "test-bulldogs"),
    )


def _seed_term(
    conn: sqlite3.Connection,
    team_id: int,
    season: int,
    term: str,
    rank: int = 1,
) -> None:
    conn.execute(
        "INSERT INTO team_discourse_terms (team_id, season_year, week, term, term_rank) "
        "VALUES (?, ?, 0, ?, ?)",
        (team_id, season, term, rank),
    )


def _seed_doc(
    conn: sqlite3.Connection,
    doc_id: int,
    team_id: int,
    body: str,
    source: str = "reddit_cfb",
) -> None:
    conn.execute(
        "INSERT INTO conversation_documents "
        "(conversation_document_id, body_text, source_name) VALUES (?, ?, ?)",
        (doc_id, body, source),
    )
    conn.execute(
        "INSERT INTO conversation_document_targets "
        "(conversation_document_id, team_id, target_type) VALUES (?, ?, 'team')",
        (doc_id, team_id),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReturnShape:
    """compute_kwic_quotes always returns the correct dict shape."""

    def test_keys_present_empty_corpus(self):
        conn = _make_db()
        result = compute_kwic_quotes(conn, seasons=2025)
        assert set(result.keys()) == {"teams_processed", "quotes_written", "seasons"}

    def test_seasons_normalised_from_int(self):
        conn = _make_db()
        result = compute_kwic_quotes(conn, seasons=2025)
        assert result["seasons"] == [2025]

    def test_seasons_normalised_from_list(self):
        conn = _make_db()
        result = compute_kwic_quotes(conn, seasons=[2024, 2025])
        assert result["seasons"] == [2024, 2025]


class TestEmptyCorpus:
    """Zero quotes when there are no matching documents."""

    def test_zero_quotes_no_docs(self):
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "rivalry")
        result = compute_kwic_quotes(conn, seasons=2025, commit=False)
        assert result["quotes_written"] == 0
        assert result["teams_processed"] == 0

    def test_zero_quotes_no_terms(self):
        conn = _make_db()
        _seed_team(conn, 1)
        # No rows in team_discourse_terms.
        result = compute_kwic_quotes(conn, seasons=2025, commit=False)
        assert result["quotes_written"] == 0
        assert result["teams_processed"] == 0


class TestPassageExtraction:
    """Passages are extracted and contain the target term."""

    def test_extracts_passage_containing_term(self):
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "rivalry", rank=1)
        body = (
            "The annual rivalry game between the two programs draws more fans "
            "than any other match-up in the state."
        )
        _seed_doc(conn, 1, 1, body)
        result = compute_kwic_quotes(conn, seasons=2025, commit=False)
        assert result["quotes_written"] == 1

    def test_passage_is_case_insensitive(self):
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "rivalry", rank=1)
        # Term appears in uppercase in the document.
        body = (
            "Fans call this the greatest RIVALRY in college football history "
            "because both fanbases show up in equal force every single year."
        )
        _seed_doc(conn, 1, 1, body)
        result = compute_kwic_quotes(conn, seasons=2025, commit=False)
        assert result["quotes_written"] == 1

    def test_no_match_yields_zero(self):
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "rivalry", rank=1)
        # The word "rivalry" does not appear in the body.
        body = "The offensive line played exceptionally well against a tough defensive unit."
        _seed_doc(conn, 1, 1, body)
        result = compute_kwic_quotes(conn, seasons=2025, commit=False)
        assert result["quotes_written"] == 0

    def test_multiple_docs_deduplication(self):
        """Identical leading prefix is counted only once."""
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "rivalry", rank=1)
        body = (
            "The annual rivalry game between the two programs draws more fans "
            "than any other match-up in the state."
        )
        # Insert same text twice — should deduplicate to 1 passage.
        _seed_doc(conn, 1, 1, body)
        _seed_doc(conn, 2, 1, body)
        result = compute_kwic_quotes(conn, seasons=2025, commit=False)
        assert result["quotes_written"] == 1


class TestCommitBehaviour:
    """commit flag controls whether rows are written to the DB."""

    def test_commit_false_does_not_write(self):
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "rivalry", rank=1)
        body = (
            "The annual rivalry game is the most-watched contest every season "
            "and drives enormous engagement across all fan channels."
        )
        _seed_doc(conn, 1, 1, body)
        compute_kwic_quotes(conn, seasons=2025, commit=False)
        count = conn.execute(
            "SELECT COUNT(*) FROM team_discourse_term_quotes"
        ).fetchone()[0]
        assert count == 0

    def test_commit_true_writes_rows(self):
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "rivalry", rank=1)
        body = (
            "The annual rivalry game is the most-watched contest every season "
            "and drives enormous engagement across all fan channels."
        )
        _seed_doc(conn, 1, 1, body)
        result = compute_kwic_quotes(conn, seasons=2025, commit=True)
        count = conn.execute(
            "SELECT COUNT(*) FROM team_discourse_term_quotes"
        ).fetchone()[0]
        assert count == result["quotes_written"]
        assert count >= 1

    def test_commit_true_sets_position_index(self):
        """position_index is 0-based and increments for each passage."""
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "offense", rank=1)
        # Three distinct docs, each containing the term.
        bodies = [
            (
                "Their offense was absolutely electric in the third quarter "
                "and the crowd went wild as the points piled up quickly."
            ),
            (
                "Running the offense through the interior of the line proved "
                "to be the right strategic choice throughout the whole game."
            ),
            (
                "Coaches praised the offense for its discipline in the red zone "
                "and its ability to convert on third downs consistently."
            ),
        ]
        for i, b in enumerate(bodies, start=10):
            _seed_doc(conn, i, 1, b)

        compute_kwic_quotes(conn, seasons=2025, commit=True)
        rows = conn.execute(
            "SELECT position_index FROM team_discourse_term_quotes ORDER BY position_index"
        ).fetchall()
        indices = [r[0] for r in rows]
        assert indices == list(range(len(indices)))

    def test_commit_idempotent_replaces_existing(self):
        """Running twice with commit=True replaces, not duplicates, rows."""
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_term(conn, 1, 2025, "rivalry", rank=1)
        body = (
            "The annual rivalry game is the most-watched contest every season "
            "and drives enormous engagement across all fan channels."
        )
        _seed_doc(conn, 1, 1, body)
        compute_kwic_quotes(conn, seasons=2025, commit=True)
        first_count = conn.execute(
            "SELECT COUNT(*) FROM team_discourse_term_quotes"
        ).fetchone()[0]
        compute_kwic_quotes(conn, seasons=2025, commit=True)
        second_count = conn.execute(
            "SELECT COUNT(*) FROM team_discourse_term_quotes"
        ).fetchone()[0]
        assert first_count == second_count


class TestTeamFilter:
    """The optional teams parameter restricts processing to specific team_ids."""

    def test_team_filter_excludes_other_teams(self):
        conn = _make_db()
        _seed_team(conn, 1)
        _seed_team(conn, 2)
        _seed_term(conn, 1, 2025, "rivalry", rank=1)
        _seed_term(conn, 2, 2025, "offense", rank=1)
        body_1 = (
            "The annual rivalry game is the most-watched event in the region "
            "and fans from both sides travel hundreds of miles to attend."
        )
        body_2 = (
            "Their offense is the best unit they have fielded in many years "
            "and scouts are watching the skill positions very closely now."
        )
        _seed_doc(conn, 1, 1, body_1)
        _seed_doc(conn, 2, 2, body_2)
        result = compute_kwic_quotes(conn, seasons=2025, teams=[1], commit=False)
        assert result["teams_processed"] == 1


class TestExtractPassageHelper:
    """Unit tests for the _extract_passage helper directly."""

    def test_returns_none_for_short_result(self):
        # Even if the term is found, a very short surrounding context is rejected.
        assert _extract_passage("hi rivalry ok", "rivalry") is None

    def test_returns_none_when_term_absent(self):
        assert _extract_passage("no match here at all", "rivalry") is None

    def test_returns_passage_for_valid_context(self):
        text = (
            "Fans have always regarded this as the greatest rivalry in the sport "
            "because both sides bring passion, history, and tradition every year."
        )
        result = _extract_passage(text, "rivalry")
        assert result is not None
        assert "rivalry" in result.lower()

    def test_passage_within_length_bounds(self):
        text = (
            "The rivalry between these two storied programs has defined an entire "
            "generation of college football fans across the entire southern region."
        )
        result = _extract_passage(text, "rivalry")
        if result is not None:
            assert 30 <= len(result) <= 250

    def test_normalises_whitespace(self):
        text = "Some   context   about  the    rivalry    game   and   the   fans."
        result = _extract_passage(text, "rivalry")
        if result is not None:
            assert "  " not in result
