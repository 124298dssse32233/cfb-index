"""Tests for player dedup — merging duplicate-human players rows.

Safety gates under test:
  - merge happens ONLY into a unique cfbd-canonical row with year overlap
  - groups with >=2 cfbd rows (distinct humans) are never touched
  - year-range mismatch -> skipped (likely different humans)
  - dead rows (no years, no child data) are deleted, their source ids NOT
    repointed (no evidence they belong to the canonical)
  - unique-constraint collisions during repoint resolve to the canonical's
    copy (dup's redundant row deleted, not duplicated)
  - dry-run changes nothing
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from cfb_rankings.db import Database
from cfb_rankings.player_dedup import audit_duplicates, merge_duplicates


_SCHEMA = """
CREATE TABLE players (
    player_id  integer primary key autoincrement,
    full_name  text not null,
    position   text
);
CREATE TABLE player_source_ids (
    player_source_id integer primary key autoincrement,
    player_id        integer not null references players(player_id),
    source_name      text not null,
    source_player_id text not null,
    unique(source_name, source_player_id)
);
CREATE TABLE player_honors (
    honor_id    integer primary key autoincrement,
    player_id   integer,
    season_year integer,
    award       text
);
CREATE TABLE heisman_rankings_weekly (
    heisman_ranking_id integer primary key autoincrement,
    player_id   integer,
    season_year integer,
    rank_overall integer,
    unique(player_id, season_year)
);
CREATE TABLE player_current_status_cache (
    player_id integer primary key,
    status    text
);
"""


def _make_db(tmp_path: Path, name: str = "dedup.db") -> Database:
    p = tmp_path / name
    conn = sqlite3.connect(p)
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
    return Database(str(p))


def _add_player(db: Database, pid: int, name: str, *, cfbd: str | None = None,
                recruit: str | None = None, honors_years: list[int] = ()) -> None:
    with db.connection() as conn:
        conn.execute("insert into players (player_id, full_name) values (?,?)", (pid, name))
        if cfbd:
            conn.execute(
                "insert into player_source_ids (player_id, source_name, source_player_id) values (?,'cfbd',?)",
                (pid, cfbd))
        if recruit:
            conn.execute(
                "insert into player_source_ids (player_id, source_name, source_player_id) values (?,'cfbd-recruit',?)",
                (pid, recruit))
        for y in honors_years:
            conn.execute(
                "insert into player_honors (player_id, season_year, award) values (?,?,'x')",
                (pid, y))
        conn.execute(
            "insert or ignore into player_current_status_cache (player_id, status) values (?,'active')",
            (pid,))
        conn.commit()


def test_merge_repoints_children_into_cfbd_canonical(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    _add_player(db, 100, "Dillon Gabriel", cfbd="ath-1", honors_years=[2024])
    _add_player(db, 200, "Dillon Gabriel", honors_years=[2024, 2025])  # honors ghost

    audit = audit_duplicates(db)
    assert audit.summary()["merge"] == 1
    stats = merge_duplicates(db, commit=True)
    assert stats["players_deleted"] == 1

    # Ghost gone; its honors now belong to the canonical.
    assert db.query_one("select count(*) as n from players")["n"] == 1
    rows = db.query_all("select distinct player_id from player_honors")
    assert [int(r["player_id"]) for r in rows] == [100]


def test_two_cfbd_rows_are_distinct_humans_untouched(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    _add_player(db, 1, "Jalen Johnson", cfbd="ath-1", honors_years=[2024])
    _add_player(db, 2, "Jalen Johnson", cfbd="ath-2", honors_years=[2024])

    audit = audit_duplicates(db)
    assert not audit.plans
    assert audit.skipped_multi_cfbd == 1
    merge_duplicates(db, commit=True)
    assert db.query_one("select count(*) as n from players")["n"] == 2


def test_year_mismatch_skipped(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    _add_player(db, 1, "John Smith", cfbd="ath-1", honors_years=[2024])
    _add_player(db, 2, "John Smith", honors_years=[1995])  # historical award winner

    audit = audit_duplicates(db)
    assert not audit.plans
    assert audit.skipped_year_mismatch == 1


def test_dead_row_deleted_without_repointing_source_ids(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    _add_player(db, 1, "Dillon Gabriel", cfbd="ath-1", honors_years=[2024])
    _add_player(db, 2, "Dillon Gabriel", recruit="rec-9")  # no years, no child data

    audit = audit_duplicates(db)
    assert audit.summary()["delete_dead"] == 1
    merge_duplicates(db, commit=True)
    assert db.query_one("select count(*) as n from players")["n"] == 1
    # No evidence the recruit id belongs to the canonical -> NOT repointed.
    assert db.query_one(
        "select count(*) as n from player_source_ids where source_player_id='rec-9'")["n"] == 0


def test_unique_collision_resolves_to_canonical_copy(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    _add_player(db, 1, "QB One", cfbd="ath-1", honors_years=[2024])
    _add_player(db, 2, "QB One", honors_years=[2024])
    with db.connection() as conn:
        # BOTH rows have a heisman entry for 2024 -> unique(player_id, season_year)
        # collides on repoint; the dup's copy must be dropped, canonical's kept.
        conn.execute("insert into heisman_rankings_weekly (player_id, season_year, rank_overall) values (1,2024,1)")
        conn.execute("insert into heisman_rankings_weekly (player_id, season_year, rank_overall) values (2,2024,5)")
        conn.commit()

    merge_duplicates(db, commit=True)
    rows = db.query_all("select player_id, rank_overall from heisman_rankings_weekly")
    assert len(rows) == 1
    assert int(rows[0]["player_id"]) == 1
    assert int(rows[0]["rank_overall"]) == 1  # canonical's row won


def test_dry_run_changes_nothing(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    _add_player(db, 1, "Dillon Gabriel", cfbd="ath-1", honors_years=[2024])
    _add_player(db, 2, "Dillon Gabriel", honors_years=[2024])

    stats = merge_duplicates(db, commit=False)
    assert stats["merge"] == 1
    assert "players_deleted" not in stats
    assert db.query_one("select count(*) as n from players")["n"] == 2
