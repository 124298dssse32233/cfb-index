"""Smoke tests for cfb_rankings.season_phase_status."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.season_phase_status import (
    OffseasonStatusKind,
    resolve_offseason_status,
)


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    path = tmp_path / "phase.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            full_name TEXT
        );
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY,
            canonical_name TEXT,
            school_name TEXT,
            short_name TEXT
        );
        CREATE TABLE roster_entries (
            roster_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER, team_id INTEGER, season_year INTEGER,
            class_year TEXT
        );
        CREATE TABLE transfer_entries (
            transfer_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER, season_year INTEGER,
            from_team_name TEXT, to_team_name TEXT, transfer_date TEXT,
            eligibility TEXT
        );
        CREATE TABLE recruiting_entries (
            recruiting_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER, team_id INTEGER, season_year INTEGER
        );
        CREATE TABLE player_nfl_draft (
            player_nfl_draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER, draft_year INTEGER, round INTEGER,
            pick INTEGER, nfl_team TEXT, nfl_team_abbr TEXT
        );
        INSERT INTO teams VALUES
            (1, 'Notre Dame', 'Notre Dame', 'ND'),
            (2, 'Indiana', 'Indiana', 'IU'),
            (3, 'USC', 'USC', 'USC');
        INSERT INTO players VALUES
            (100, 'Returning Player'),
            (200, 'Drafted Player'),
            (300, 'Portal Player'),
            (400, 'Unknown Player');
        """
    )
    # Returning: roster entry for 2026
    conn.execute("INSERT INTO roster_entries(player_id, team_id, season_year, class_year) VALUES(100, 1, 2026, 'JR')")
    # Drafted: player_nfl_draft entry
    conn.execute("INSERT INTO player_nfl_draft(player_id, draft_year, round, pick, nfl_team, nfl_team_abbr) VALUES(200, 2026, 1, 10, 'Dallas Cowboys', 'DAL')")
    # Portal: transfer_entries committed-out row
    conn.execute("INSERT INTO transfer_entries(player_id, season_year, from_team_name, to_team_name, transfer_date) VALUES(300, 2026, 'USC', 'Indiana', '2026-03-15')")
    conn.commit()
    conn.close()
    return Database(str(path))


def test_returning_resolves(db: Database) -> None:
    s = resolve_offseason_status(db, 100, forward_season_year=2026)
    assert s.kind == OffseasonStatusKind.RETURNING
    assert "JR 2026" in s.display_copy
    assert s.chip_color == "accolade-gold"


def test_drafted_resolves(db: Database) -> None:
    from datetime import date
    s = resolve_offseason_status(db, 200, today=date(2026, 4, 28), forward_season_year=2026)
    assert s.kind == OffseasonStatusKind.DRAFTED
    assert "R1" in s.display_copy
    assert "DAL" in s.display_copy


def test_portal_commit_resolves(db: Database) -> None:
    s = resolve_offseason_status(db, 300, forward_season_year=2026)
    assert s.kind == OffseasonStatusKind.COMMITTED_OUT_OF_PORTAL
    assert "INDIANA" in s.display_copy


def test_unknown_is_unresolved(db: Database) -> None:
    s = resolve_offseason_status(db, 400, forward_season_year=2026)
    assert s.kind == OffseasonStatusKind.UNRESOLVED
    assert s.chip_color == "muted"
