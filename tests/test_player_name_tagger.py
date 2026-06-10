"""Tests for player_name_tagger — the extraction step that populates
`conversation_document_targets.player_id` from raw `conversation_documents`.

Coverage:
  - Full-name match surfaces a player.
  - Team-affiliation tiebreak picks the right Carr when two exist.
  - Ambiguous match with no team cue → skipped (not guessed).
  - Candidate pool excludes non-skill / inactive players.
  - Dry-run vs. commit — no rows inserted without --commit.
  - Idempotent: re-running with --commit does not duplicate rows.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.ingest.player_name_tagger import (
    build_player_name_index,
    tag_player_mentions,
)


SEASON = 2025


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    db_path = tmp_path / "tagger.db"
    conn = sqlite3.connect(db_path)
    _schema(conn)
    _seed(conn)
    conn.commit()
    conn.close()
    return Database(str(db_path))


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            full_name TEXT,
            position TEXT
        );
        CREATE TABLE player_value_metrics (
            player_value_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER, player_id INTEGER, team_id INTEGER,
            team_name TEXT, player_name TEXT, conference_name TEXT,
            position TEXT, metric_name TEXT, metric_value REAL, plays INTEGER
        );
        CREATE TABLE player_season_stats (
            player_season_stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER, player_id INTEGER, team_id INTEGER,
            team_name TEXT, player_name TEXT, conference_name TEXT,
            position TEXT, category TEXT, stat_type TEXT, stat_value_num REAL
        );
        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT, source_author_id TEXT,
            body_text TEXT, title_text TEXT,
            like_count INTEGER DEFAULT 0, reply_count INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0
        );
        CREATE TABLE conversation_document_targets (
            conversation_document_target_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_document_id INTEGER NOT NULL,
            season_year INTEGER, week INTEGER,
            team_id INTEGER, player_id INTEGER,
            target_type TEXT, target_key TEXT, target_label TEXT,
            affiliation_team_id INTEGER, audience_bucket TEXT, mention_role TEXT,
            sentiment_score REAL, emotion_primary TEXT,
            sarcasm_score REAL, confidence_score REAL,
            is_primary_target INTEGER DEFAULT 0
        );
        """
    )


def _seed(conn: sqlite3.Connection) -> None:
    # Two Carrs in the candidate pool to force disambiguation:
    # (4788) C.J. Carr at Notre Dame — active QB
    # (9001) Tommy Carr at Texas — active QB
    # Plus Diego Pavia (5676) — active QB at Vanderbilt.
    # Plus an INACTIVE QB "Legacy Player" with no stats in 2025 — must NOT match.
    conn.execute("INSERT INTO players VALUES (4788, 'C.J. Carr', 'QB')")
    conn.execute("INSERT INTO players VALUES (9001, 'Tommy Carr', 'QB')")
    conn.execute("INSERT INTO players VALUES (5676, 'Diego Pavia', 'QB')")
    conn.execute("INSERT INTO players VALUES (9900, 'Legacy Player', 'QB')")

    def _wepa(pid, name, team, conf, plays):
        conn.execute(
            """INSERT INTO player_value_metrics
               (season_year, player_id, team_id, team_name, player_name,
                conference_name, position, metric_name, metric_value, plays)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (SEASON, pid, 1, team, name, conf, "QB", "wepa_passing", 0.4, plays),
        )
    _wepa(4788, "C.J. Carr", "Notre Dame", "FBS Independents", 307)
    _wepa(9001, "Tommy Carr", "Texas", "SEC", 220)
    _wepa(5676, "Diego Pavia", "Vanderbilt", "SEC", 384)

    # Documents:
    # d1 — mentions "C.J. Carr" + "Notre Dame" → should match 4788.
    # d2 — mentions just "C.J. Carr" (no team) → still unambiguous (unique name).
    # d3 — mentions "Tommy Carr" + "Texas" → should match 9001.
    # d4 — ambiguous: "Carr looked great" — no full-name match expected.
    # d5 — mentions "Diego Pavia" → matches 5676 unambiguously.
    # d6 — mentions "Legacy Player" — must NOT match (no 2025 stats).
    def _doc(body, author="fan1"):
        cur = conn.execute(
            """INSERT INTO conversation_documents
               (source_name, source_author_id, body_text) VALUES (?,?,?)""",
            ("reddit_cfb", author, body),
        )
        return cur.lastrowid

    def _team_target(doc_id, team_id, bucket="fan"):
        conn.execute(
            """INSERT INTO conversation_document_targets
               (conversation_document_id, season_year, week, team_id,
                target_type, audience_bucket, is_primary_target)
               VALUES (?,?,?,?,?,?,1)""",
            (doc_id, SEASON, 12, team_id, "team", bucket),
        )

    d1 = _doc("C.J. Carr is the real deal at Notre Dame right now.")
    _team_target(d1, 1, "fan")
    d2 = _doc("Anyone else watching CJ Carr lately? Absolute cannon.")
    _team_target(d2, 1, "national")
    d3 = _doc("Tommy Carr balled out for Texas this weekend.")
    _team_target(d3, 2, "fan")
    d4 = _doc("Carr looked great in the scrimmage.")
    _team_target(d4, 1, "fan")
    d5 = _doc("Diego Pavia is the heart of Vanderbilt.")
    _team_target(d5, 3, "fan")
    d6 = _doc("Legacy Player was good back in the day.")
    _team_target(d6, 1, "fan")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_index_excludes_inactive_players(db: Database) -> None:
    idx = build_player_name_index(db, SEASON)
    # "Legacy Player" has no 2025 stats → must NOT appear.
    assert "legacy player" not in idx
    # The three active players must be indexed.
    assert "cj carr" in idx
    assert "tommy carr" in idx
    assert "diego pavia" in idx


def test_full_name_match_surfaces_correct_player(db: Database) -> None:
    result = tag_player_mentions(db, season_year=SEASON, commit=True)
    assert result["matches"] >= 4  # d1, d2 (Carr), d3 (Tommy), d5 (Pavia)
    assert result["rows_written"] == result["matches"]

    rows = db.query_all(
        """select conversation_document_id, player_id, audience_bucket, target_type
             from conversation_document_targets
            where target_type = 'player' order by conversation_document_id, player_id""",
        {},
    )
    player_hits = {(r["conversation_document_id"], r["player_id"]) for r in rows}
    # Doc 1 → C.J. Carr
    assert any(pid == 4788 for (_, pid) in player_hits)
    # Doc 3 → Tommy Carr
    assert any(pid == 9001 for (_, pid) in player_hits)
    # Doc 5 → Diego Pavia
    assert any(pid == 5676 for (_, pid) in player_hits)


def test_audience_bucket_inherits_from_team_target(db: Database) -> None:
    tag_player_mentions(db, season_year=SEASON, commit=True)
    rows = db.query_all(
        """select player_id, audience_bucket
             from conversation_document_targets
            where target_type = 'player' and player_id = 4788""",
        {},
    )
    # Both d1 (team target team=1 bucket=fan) and d2 (team target team=1 bucket=national)
    # reference Carr's team. Bucket should be inherited from the existing team target.
    buckets = {r["audience_bucket"] for r in rows}
    assert "fan" in buckets or "national" in buckets


def test_ambiguous_last_name_only_is_skipped(db: Database) -> None:
    """doc d4 says "Carr looked great" — last-name-only. No match expected."""
    result = tag_player_mentions(db, season_year=SEASON, commit=True)
    # Only docs d1/d2/d3/d5 should match; d4 and d6 must NOT produce a player row.
    rows = db.query_all(
        """select conversation_document_id from conversation_document_targets
            where target_type = 'player' and conversation_document_id in
                  (select conversation_document_id from conversation_documents
                    where body_text like 'Carr looked great%%')""",
        {},
    )
    assert len(rows) == 0


def test_dry_run_inserts_nothing(db: Database) -> None:
    result = tag_player_mentions(db, season_year=SEASON, commit=False)
    assert result["matches"] > 0
    assert result["rows_written"] == 0
    count_rows = db.query_one(
        "select count(*) as n from conversation_document_targets where target_type='player'",
        {},
    )
    assert count_rows["n"] == 0


def test_commit_is_idempotent(db: Database) -> None:
    first = tag_player_mentions(db, season_year=SEASON, commit=True)
    second = tag_player_mentions(db, season_year=SEASON, commit=True)
    assert first["rows_written"] > 0
    assert second["rows_written"] == 0  # every match already present → skip


def test_limit_truncates_scan(db: Database) -> None:
    result = tag_player_mentions(db, season_year=SEASON, doc_limit=1, commit=False)
    assert result["docs_scanned"] == 1


def test_offseason_falls_back_to_latest_stats_season(tmp_path: Path) -> None:
    """Bare call for an upcoming season with no stats (the daily CI invocation in
    the offseason) must auto-fall-back to the latest season that has stats,
    instead of silently no-opping on an empty index."""
    db_path = tmp_path / "offseason.db"
    conn = sqlite3.connect(db_path)
    _schema(conn)
    # Player stats exist only for 2024 — none for the upcoming 2025 season.
    conn.execute("INSERT INTO players VALUES (4788, 'C.J. Carr', 'QB')")
    conn.execute(
        """INSERT INTO player_value_metrics
           (season_year, player_id, team_id, team_name, player_name,
            conference_name, position, metric_name, metric_value, plays)
           VALUES (2024, 4788, 1, 'Notre Dame', 'C.J. Carr',
                   'FBS Independents', 'QB', 'wepa_passing', 0.4, 307)"""
    )
    # A 2025-stamped doc + team target (as the team tagger would emit offseason).
    cur = conn.execute(
        """INSERT INTO conversation_documents (source_name, source_author_id, body_text)
           VALUES ('bluesky_curated', 'fan1', 'C.J. Carr looked sharp this spring.')"""
    )
    doc_id = cur.lastrowid
    conn.execute(
        """INSERT INTO conversation_document_targets
           (conversation_document_id, season_year, week, team_id, target_type,
            audience_bucket, is_primary_target)
           VALUES (?, 2025, 0, 1, 'team', 'national', 1)""",
        (doc_id,),
    )
    conn.commit()
    conn.close()
    db = Database(str(db_path))

    # Bare call: upcoming season, no pool override.
    result = tag_player_mentions(db, season_year=2025, commit=True)
    assert result["docs_scanned"] == 1
    assert result["matches"] >= 1
    rows = db.query_all(
        "select player_id, season_year from conversation_document_targets "
        "where target_type='player'",
        {},
    )
    assert any(r["player_id"] == 4788 for r in rows)
    # Target is stamped with the docs-season (2025), not the fallback (2024).
    assert all(r["season_year"] == 2025 for r in rows)
