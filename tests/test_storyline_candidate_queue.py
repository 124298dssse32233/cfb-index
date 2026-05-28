"""Tests for the WS-12 storyline candidate queue.

Coverage:
  - Ranking: priority = tension x frame_weight, sorted descending.
  - Dedupe: an arc whose team an active thread already covers is penalised
    (covered_by_thread set) but still surfaced.
  - Only live arcs (open / closure_eligible) become candidates.
  - Dry-run writes nothing; --commit writes one row per arc.
  - Idempotent re-run preserves an editor's review_status verdict.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.storylines.candidate_queue import (
    FRAME_WEIGHTS,
    populate_storyline_candidates,
    render_candidate_digest,
)

SEASON = 2025


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    db_path = tmp_path / "candidates.db"
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
            slug TEXT
        );
        CREATE TABLE season_narrative_arc (
            arc_id TEXT PRIMARY KEY,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            frame TEXT NOT NULL,
            status TEXT NOT NULL,
            opened_at_week INTEGER NOT NULL DEFAULT 0,
            closed_at_week INTEGER,
            tension_score REAL NOT NULL DEFAULT 0.0,
            confirming_evidence_count INTEGER NOT NULL DEFAULT 0,
            disconfirming_evidence_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE storyline_threads (
            thread_slug TEXT PRIMARY KEY,
            status TEXT,
            primary_program_slugs TEXT
        );
        CREATE TABLE storyline_candidate (
            candidate_id TEXT PRIMARY KEY,
            arc_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            team_slug TEXT,
            season_year INTEGER NOT NULL,
            frame TEXT NOT NULL,
            arc_status TEXT NOT NULL,
            tension_score REAL NOT NULL DEFAULT 0.0,
            frame_weight REAL NOT NULL DEFAULT 0.0,
            priority_score REAL NOT NULL DEFAULT 0.0,
            confirming_evidence_count INTEGER NOT NULL DEFAULT 0,
            covered_by_thread TEXT,
            review_status TEXT NOT NULL DEFAULT 'proposed',
            headline_hint TEXT,
            created_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at_utc TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )


def _seed(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO teams VALUES (?,?)",
        [
            (1, "alabama"),
            (2, "auburn"),
            (3, "vanderbilt"),
            (4, "oregon"),
        ],
    )

    def _arc(arc_id, team_id, frame, status, tension):
        conn.execute(
            """INSERT INTO season_narrative_arc
               (arc_id, team_id, season_year, frame, status, tension_score)
               VALUES (?,?,?,?,?,?)""",
            (arc_id, team_id, SEASON, frame, status, tension),
        )

    # Alabama: high tension coaching_transition (weight 1.0) — but covered by an
    # active thread, so it should be penalised below an uncovered peer.
    _arc("alabama-2025-coach", 1, "coaching_transition", "open", 0.90)
    # Auburn: portal_class_arrival (weight 0.75), uncovered.
    _arc("auburn-2025-portal", 2, "portal_class_arrival", "open", 0.80)
    # Oregon: archetype_transition (weight 0.85), uncovered, top expected.
    _arc("oregon-2025-arche", 4, "archetype_transition", "open", 0.95)
    # Vanderbilt: resolved arc — must NOT become a candidate.
    _arc("vandy-2025-done", 3, "archetype_transition", "resolved", 0.99)

    # alabama is covered by an active thread.
    conn.execute(
        "INSERT INTO storyline_threads VALUES (?,?,?)",
        ("saban-to-deboer", "active", '["alabama"]'),
    )
    # An archived thread must NOT count as coverage.
    conn.execute(
        "INSERT INTO storyline_threads VALUES (?,?,?)",
        ("old-thread", "archived", '["oregon"]'),
    )


def test_only_live_arcs_become_candidates(db: Database) -> None:
    result = populate_storyline_candidates(db, SEASON, commit=False)
    # 3 live (alabama/auburn/oregon); resolved vandy excluded.
    assert result["arcs_scanned"] == 3
    assert result["candidates_ranked"] == 3


def test_ranking_orders_by_priority(db: Database) -> None:
    result = populate_storyline_candidates(db, SEASON, commit=True)
    rows = db.query_all(
        "select candidate_id, priority_score, frame_weight from storyline_candidate "
        "order by priority_score desc",
        {},
    )
    # Oregon (0.95 * 0.85 = 0.8075) tops; Auburn (0.80 * 0.75 = 0.60) next;
    # Alabama (0.90 * 1.0 * 0.25 covered-penalty = 0.225) last.
    assert rows[0]["candidate_id"] == "oregon-2025-arche"
    assert rows[1]["candidate_id"] == "auburn-2025-portal"
    assert rows[2]["candidate_id"] == "alabama-2025-coach"
    assert rows[0]["frame_weight"] == FRAME_WEIGHTS["archetype_transition"]


def test_active_thread_coverage_penalises_but_keeps(db: Database) -> None:
    populate_storyline_candidates(db, SEASON, commit=True)
    bama = db.query_one(
        "select covered_by_thread, priority_score from storyline_candidate "
        "where candidate_id = 'alabama-2025-coach'",
        {},
    )
    assert bama["covered_by_thread"] == "saban-to-deboer"
    # 0.90 * 1.0 * 0.25 = 0.225
    assert bama["priority_score"] == pytest.approx(0.225)
    # Oregon's archived-thread coverage must NOT register.
    oregon = db.query_one(
        "select covered_by_thread from storyline_candidate "
        "where candidate_id = 'oregon-2025-arche'",
        {},
    )
    assert oregon["covered_by_thread"] is None


def test_dry_run_writes_nothing(db: Database) -> None:
    result = populate_storyline_candidates(db, SEASON, commit=False)
    assert result["candidates_ranked"] == 3
    assert result["rows_written"] == 0
    n = db.query_one("select count(*) as n from storyline_candidate", {})
    assert n["n"] == 0


def test_offseason_falls_back_to_latest_arc_season(db: Database) -> None:
    """Arcs are stamped for the upcoming season (2026), but the offseason CI
    computes SEASON as the last completed season (2025). A bare 2026-empty call
    must fall back to where the arcs actually live rather than no-op."""
    # The fixture arcs are all season 2025; request 2026 (empty) and expect fallback.
    result = populate_storyline_candidates(db, 2026, commit=True)
    assert result["arc_season"] == SEASON  # fell back to 2025
    assert result["candidates_ranked"] == 3
    rows = db.query_all("select season_year from storyline_candidate", {})
    # Candidates are stamped with the arc's real season, not the requested one.
    assert all(r["season_year"] == SEASON for r in rows)


def test_digest_renders_md_and_json(db: Database, tmp_path: Path) -> None:
    populate_storyline_candidates(db, SEASON, commit=True)
    # Editor dismisses Alabama; promotes Oregon.
    db.execute(
        "update storyline_candidate set review_status='dismissed' "
        "where candidate_id='alabama-2025-coach'", {})
    db.execute(
        "update storyline_candidate set review_status='promoted' "
        "where candidate_id='oregon-2025-arche'", {})

    out = tmp_path / "candidates.md"
    result = render_candidate_digest(db, SEASON, output_path=out)

    assert out.exists()
    assert (tmp_path / "candidates.json").exists()
    # 1 proposed (auburn), 1 promoted (oregon), 1 dismissed (alabama).
    assert result["proposed"] == 1
    assert result["promoted"] == 1
    assert result["dismissed"] == 1
    text = out.read_text(encoding="utf-8")
    assert "Storyline candidate queue" in text
    assert "auburn" in text          # the lone proposed net-new candidate
    assert "## Promoted" in text     # promoted section appears
    # Dismissed Alabama must NOT appear in the proposed tables.
    assert "alabama" not in text


def test_digest_falls_back_to_latest_arc_season(db: Database, tmp_path: Path) -> None:
    # Candidates were committed for 2025; ask the digest for empty 2099.
    populate_storyline_candidates(db, SEASON, commit=True)
    out = tmp_path / "candidates.md"
    result = render_candidate_digest(db, 2099, output_path=out)
    assert result["season_year"] == SEASON  # fell back to where candidates live
    assert result["proposed"] == 3


def test_recommit_preserves_editor_review_status(db: Database) -> None:
    populate_storyline_candidates(db, SEASON, commit=True)
    # Editor dismisses the Alabama candidate.
    db.execute(
        "update storyline_candidate set review_status = 'dismissed' "
        "where candidate_id = 'alabama-2025-coach'",
        {},
    )
    # Daily cron re-runs the populator.
    populate_storyline_candidates(db, SEASON, commit=True)
    bama = db.query_one(
        "select review_status from storyline_candidate "
        "where candidate_id = 'alabama-2025-coach'",
        {},
    )
    assert bama["review_status"] == "dismissed"  # verdict survived the re-run
