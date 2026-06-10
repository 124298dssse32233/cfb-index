"""Tests for the player-ID anchor — the mechanism that keeps player-page URLs
stable across a full DB rebuild (the linkrot fix).

Guarantees under test:
  - export_anchor writes one row per cfbd source id with its canonical player_id.
  - seed_anchor on a FRESH db recreates players + player_source_ids with the
    exact canonical ids (so /players/<name>-<id>.html stays the same url).
  - the cfbd source-id -> player_id lookup (what ingestion's _get_or_create_player
    does first) returns the canonical id after seeding → ingestion REUSES it.
  - sqlite_sequence is advanced so a brand-new autoincrement player gets an id
    ABOVE the anchored range (no collision).
  - seed_anchor is idempotent / a no-op on an already-populated db.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.player_id_anchor import export_anchor, seed_anchor


_SCHEMA = """
CREATE TABLE players (
    player_id  integer primary key autoincrement,
    full_name  text not null,
    first_name text,
    last_name  text,
    position   text,
    hometown   text,
    home_state text,
    created_at text not null default current_timestamp
);
CREATE TABLE player_source_ids (
    player_source_id integer primary key autoincrement,
    player_id        integer not null references players(player_id),
    source_name      text not null,
    source_player_id text not null,
    unique(source_name, source_player_id)
);
CREATE INDEX idx_player_source_ids_lookup on player_source_ids (source_name, source_player_id);
"""


def _make_db(tmp_path: Path, name: str) -> Database:
    p = tmp_path / name
    conn = sqlite3.connect(p)
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
    return Database(str(p))


def _seed_canonical(db: Database) -> None:
    """A populated 'old' DB with non-contiguous canonical ids (mimics the real
    world: ids assigned over many ingests, not 1..N)."""
    with db.connection() as conn:
        conn.executemany(
            "insert into players (player_id, full_name, position) values (?,?,?)",
            [(12763, "Fernando Mendoza", "QB"),
             (12194, "Jeremiyah Love", "RB"),
             (38981, "Byrum Brown", "QB")],
        )
        conn.executemany(
            "insert into player_source_ids (player_id, source_name, source_player_id) values (?, 'cfbd', ?)",
            [(12763, "athlete-501"), (12194, "athlete-777"), (38981, "athlete-902")],
        )
        conn.commit()


def _lookup(db: Database, source_player_id: str) -> int | None:
    """Exactly what _get_or_create_player does first: cfbd source id -> player_id."""
    row = db.query_one(
        "select player_id from player_source_ids where source_name='cfbd' and source_player_id=%(s)s",
        {"s": source_player_id},
    )
    return int(row["player_id"]) if row else None


def test_export_then_seed_preserves_ids_on_fresh_db(tmp_path: Path) -> None:
    old = _make_db(tmp_path, "old.db")
    _seed_canonical(old)
    anchor = tmp_path / "anchor.csv"
    n = export_anchor(old, anchor)
    assert n == 3

    fresh = _make_db(tmp_path, "fresh.db")
    result = seed_anchor(fresh, anchor)
    assert result["players_inserted"] == 3
    assert result["source_ids_inserted"] == 3

    # Canonical ids materialised exactly → URLs unchanged.
    rows = {r["full_name"]: r["player_id"] for r in fresh.query_all("select player_id, full_name from players")}
    assert rows == {"Fernando Mendoza": 12763, "Jeremiyah Love": 12194, "Byrum Brown": 38981}

    # The ingestion lookup now reuses the canonical id (the whole point).
    assert _lookup(fresh, "athlete-501") == 12763
    assert _lookup(fresh, "athlete-777") == 12194


def test_new_autoincrement_player_lands_above_anchored_range(tmp_path: Path) -> None:
    old = _make_db(tmp_path, "old.db")
    _seed_canonical(old)
    anchor = tmp_path / "anchor.csv"
    export_anchor(old, anchor)

    fresh = _make_db(tmp_path, "fresh.db")
    seed_anchor(fresh, anchor)

    # A brand-new player created by normal autoincrement must NOT reuse an
    # anchored id (38981 is the max anchored) — it must land above it.
    with fresh.connection() as conn:
        conn.execute("insert into players (full_name, position) values ('New Recruit','WR')")
        conn.commit()
        new_id = conn.execute("select player_id from players where full_name='New Recruit'").fetchone()[0]
    assert new_id > 38981


def test_seed_is_noop_on_populated_db(tmp_path: Path) -> None:
    old = _make_db(tmp_path, "old.db")
    _seed_canonical(old)
    anchor = tmp_path / "anchor.csv"
    export_anchor(old, anchor)

    # Seeding the SAME populated DB again must change nothing.
    result = seed_anchor(old, anchor)
    assert result["players_inserted"] == 0
    assert result["source_ids_inserted"] == 0
    assert old.query_one("select count(*) as n from players")["n"] == 3


def test_seed_missing_anchor_is_safe(tmp_path: Path) -> None:
    fresh = _make_db(tmp_path, "fresh.db")
    result = seed_anchor(fresh, tmp_path / "does-not-exist.csv")
    assert result == {"anchor_rows": 0, "players_inserted": 0, "source_ids_inserted": 0}
    assert fresh.query_one("select count(*) as n from players")["n"] == 0


def test_seed_preserves_existing_players_and_adds_missing(tmp_path: Path) -> None:
    """Partial-overlap rebuild: some canonical players already exist (e.g. created
    by a non-cfbd path); seeding must ADD the missing ones without disturbing
    the present ones."""
    old = _make_db(tmp_path, "old.db")
    _seed_canonical(old)
    anchor = tmp_path / "anchor.csv"
    export_anchor(old, anchor)

    partial = _make_db(tmp_path, "partial.db")
    with partial.connection() as conn:
        # Mendoza already present at his canonical id; the other two are missing.
        conn.execute("insert into players (player_id, full_name, position) values (12763,'Fernando Mendoza','QB')")
        conn.execute("insert into player_source_ids (player_id, source_name, source_player_id) values (12763,'cfbd','athlete-501')")
        conn.commit()

    result = seed_anchor(partial, anchor)
    assert result["players_inserted"] == 2          # Love + Brown
    assert result["source_ids_inserted"] == 2
    assert _lookup(partial, "athlete-501") == 12763  # untouched
    assert _lookup(partial, "athlete-902") == 38981  # added
