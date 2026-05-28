"""Tests for team_name_tagger — the source-agnostic team-mention extractor that
populates `conversation_document_targets` (target_type='team') for curated feeds
(bluesky_curated, substack_*) that arrive without per-team context.

Coverage:
  - Collision drop: an alias normalizing to >1 team is skipped, not guessed.
  - Precision gate: stoplist words + sub-floor single tokens dropped; whitelisted
    acronyms and multi-word aliases kept.
  - Span-containment: a short alias inside a longer one ("Florida" in "Florida
    State") is suppressed unless it also stands alone.
  - NFL-city suppression: "Houston" inside "Houston Texans" does not tag college
    Houston.
  - Untagged-only scan: docs that already carry a team target are left alone.
  - Dry-run vs commit; idempotent re-run.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.ingest.team_name_tagger import (
    build_team_alias_index,
    tag_team_mentions,
)

SEASON = 2025


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    db_path = tmp_path / "team_tagger.db"
    conn = sqlite3.connect(db_path)
    _schema(conn)
    _seed(conn)
    conn.commit()
    conn.close()
    return Database(str(db_path))


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY,
            canonical_name TEXT,
            slug TEXT
        );
        CREATE TABLE team_aliases (
            team_alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            alias_text TEXT,
            alias_normalized TEXT,
            alias_type TEXT,
            season_year INTEGER,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT, source_author_id TEXT,
            body_text TEXT, title_text TEXT
        );
        CREATE TABLE conversation_document_targets (
            conversation_document_target_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_document_id INTEGER NOT NULL,
            season_year INTEGER, week INTEGER,
            team_id INTEGER, player_id INTEGER,
            target_type TEXT, target_key TEXT, target_label TEXT,
            affiliation_team_id INTEGER, audience_bucket TEXT,
            mention_role TEXT,
            sentiment_label TEXT, sentiment_score REAL,
            emotion_primary TEXT, emotion_secondary TEXT,
            sarcasm_score REAL, toxicity_score REAL, confidence_score REAL,
            is_primary_target INTEGER DEFAULT 0
        );
        """
    )


# Team ids used across tests.
T_FLORIDA = 203
T_FLORIDA_ST = 4
T_HOUSTON = 248
T_LSU = 337
T_MIAMI_FL = 410
T_MIAMI_OH = 411
T_RICE = 500


def _alias(conn, team_id, text, atype="source"):
    import re

    norm = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()
    conn.execute(
        """INSERT INTO team_aliases
           (team_id, alias_text, alias_normalized, alias_type, season_year, is_active)
           VALUES (?,?,?,?,?,1)""",
        (team_id, text, norm, atype, SEASON),
    )


def _seed(conn: sqlite3.Connection) -> None:
    teams = [
        (T_FLORIDA, "Florida", "florida"),
        (T_FLORIDA_ST, "Florida State", "florida-state"),
        (T_HOUSTON, "Houston", "houston"),
        (T_LSU, "LSU", "lsu"),
        (T_MIAMI_FL, "Miami", "miami-fl"),
        (T_MIAMI_OH, "Miami (OH)", "miami-oh"),
        (T_RICE, "Rice", "rice"),
    ]
    for tid, name, slug in teams:
        conn.execute(
            "INSERT INTO teams (team_id, canonical_name, slug) VALUES (?,?,?)",
            (tid, name, slug),
        )

    _alias(conn, T_FLORIDA, "Florida")
    _alias(conn, T_FLORIDA_ST, "Florida State")
    _alias(conn, T_HOUSTON, "Houston")
    _alias(conn, T_LSU, "LSU")
    # Miami collision — both teams claim the bare "Miami" alias.
    _alias(conn, T_MIAMI_FL, "Miami")
    _alias(conn, T_MIAMI_OH, "Miami")
    # "Rice" is a stoplisted common word — must be dropped from the index.
    _alias(conn, T_RICE, "Rice")


def _doc(db: Database, body: str, source: str = "bluesky_curated") -> None:
    db.execute(
        "INSERT INTO conversation_documents (source_name, body_text) VALUES (:s, :b)",
        {"s": source, "b": body},
    )


# ---------------------------------------------------------------------------
# Index-building precision gates
# ---------------------------------------------------------------------------


def test_collision_alias_is_dropped(db: Database) -> None:
    index, _ = build_team_alias_index(db, SEASON)
    # "miami" maps to two teams → dropped rather than guessed.
    assert "miami" not in index


def test_stoplisted_common_word_is_dropped(db: Database) -> None:
    index, _ = build_team_alias_index(db, SEASON)
    assert "rice" not in index


def test_whitelisted_acronym_survives_length_floor(db: Database) -> None:
    index, _ = build_team_alias_index(db, SEASON)
    # "lsu" is 3 chars (under MIN_SINGLE_TOKEN_LEN) but acronym-whitelisted.
    assert index.get("lsu") == T_LSU


def test_multiword_and_long_single_aliases_kept(db: Database) -> None:
    index, _ = build_team_alias_index(db, SEASON)
    assert index.get("florida") == T_FLORIDA
    assert index.get("florida state") == T_FLORIDA_ST
    assert index.get("houston") == T_HOUSTON


# ---------------------------------------------------------------------------
# Span-containment + NFL suppression
# ---------------------------------------------------------------------------


def test_short_alias_inside_longer_is_suppressed(db: Database) -> None:
    """'Florida State goes...' must tag Florida State, NOT bare Florida."""
    _doc(db, "Florida State goes on the road this week.")

    tag_team_mentions(db, season_year=SEASON, commit=True)
    rows = db.query_all(
        "select team_id from conversation_document_targets where target_type='team'",
        {},
    )
    hit = {r["team_id"] for r in rows}
    assert T_FLORIDA_ST in hit
    assert T_FLORIDA not in hit


def test_short_alias_standing_alone_still_tags(db: Database) -> None:
    """'Florida beat Florida State' must tag BOTH — Florida stands alone too."""
    _doc(db, "Florida beat Florida State in a rivalry classic.")

    tag_team_mentions(db, season_year=SEASON, commit=True)
    rows = db.query_all(
        "select team_id from conversation_document_targets where target_type='team'",
        {},
    )
    hit = {r["team_id"] for r in rows}
    assert T_FLORIDA in hit
    assert T_FLORIDA_ST in hit


def test_nfl_city_name_does_not_tag_college(db: Database) -> None:
    """'Houston Texans' is an NFL mention — college Houston must not be tagged."""
    _doc(db, "NFL scouts: Houston Texans and Pittsburgh Steelers attended.")

    tag_team_mentions(db, season_year=SEASON, commit=True)
    rows = db.query_all(
        "select team_id from conversation_document_targets where target_type='team'",
        {},
    )
    assert T_HOUSTON not in {r["team_id"] for r in rows}


def test_college_city_standing_alone_still_tags(db: Database) -> None:
    """A bare 'Houston' that is not inside an NFL name still tags the college."""
    _doc(db, "Houston opens conference play at home.")

    tag_team_mentions(db, season_year=SEASON, commit=True)
    rows = db.query_all(
        "select team_id from conversation_document_targets where target_type='team'",
        {},
    )
    assert T_HOUSTON in {r["team_id"] for r in rows}


# ---------------------------------------------------------------------------
# Scan scope + write discipline
# ---------------------------------------------------------------------------


def test_already_tagged_docs_are_skipped(db: Database) -> None:
    _doc(db, "LSU rolls again this weekend.")
    doc_id = db.query_one(
        "select max(conversation_document_id) as d from conversation_documents", {}
    )["d"]
    # Pre-existing team target → tagger must not re-scan this doc.
    db.execute(
        """INSERT INTO conversation_document_targets
           (conversation_document_id, season_year, week, team_id, target_type)
           VALUES (:d, :s, 0, :t, 'team')""",
        {"d": doc_id, "s": SEASON, "t": T_LSU},
    )

    result = tag_team_mentions(db, season_year=SEASON, commit=True)
    assert result["docs_scanned"] == 0
    assert result["rows_written"] == 0


def test_dry_run_inserts_nothing(db: Database) -> None:
    _doc(db, "LSU and Florida State both won.")

    result = tag_team_mentions(db, season_year=SEASON, commit=False)
    assert result["matches"] > 0
    assert result["rows_written"] == 0
    n = db.query_one(
        "select count(*) as n from conversation_document_targets where target_type='team'",
        {},
    )
    assert n["n"] == 0


def test_commit_is_idempotent(db: Database) -> None:
    _doc(db, "LSU and Florida State both won.")

    first = tag_team_mentions(db, season_year=SEASON, commit=True)
    second = tag_team_mentions(db, season_year=SEASON, commit=True)
    assert first["rows_written"] > 0
    assert second["rows_written"] == 0
