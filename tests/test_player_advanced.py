"""Tests for cfb_rankings.metrics.player_advanced.

Builds a minimal in-memory schema containing players, games, plays, drives,
player_game_stats, player_value_metrics, and the player_advanced_metrics
landing tables, seeds synthetic rows, runs the compute path, and asserts
the math of each metric.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.metrics.player_advanced import (
    METRICS,
    METRIC_VERSION,
    MetricResult,
    _aggregate_player_game_stats,
    compute_player_advanced_metrics,
    compute_player_advanced_metrics_season,
)


CARR = 4788           # QB — full pass profile
BACKUP = 5001         # QB — below min_sample pass gate
STAR_RB = 6001        # RB
STAR_WR = 7001        # WR
NOTRE_DAME = 374
OTHER_TEAM = 375

SEASON = 2025


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    path = tmp_path / "padv.db"
    conn = sqlite3.connect(path)
    _schema(conn)
    _seed(conn)
    conn.commit()
    conn.close()
    return Database(str(path))


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            full_name TEXT,
            position TEXT
        );
        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY,
            season_year INTEGER,
            week INTEGER,
            season_type TEXT
        );
        CREATE TABLE plays (
            play_id INTEGER PRIMARY KEY,
            game_id INTEGER,
            drive_id INTEGER,
            offense_team_id INTEGER,
            defense_team_id INTEGER,
            success_flag INTEGER,
            yards_gained INTEGER,
            is_garbage_time INTEGER DEFAULT 0,
            play_type TEXT,
            down INTEGER,
            distance INTEGER,
            yard_line INTEGER,
            period INTEGER,
            epa REAL,
            ppa REAL,
            home_win_prob REAL
        );
        CREATE TABLE drives (
            drive_id INTEGER PRIMARY KEY,
            game_id INTEGER,
            offense_team_id INTEGER,
            end_yardline INTEGER,
            result TEXT,
            period INTEGER,
            drive_number INTEGER,
            start_yardline INTEGER,
            play_count INTEGER,
            yards INTEGER
        );
        CREATE TABLE player_game_stats (
            player_game_stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            season_year INTEGER,
            week INTEGER,
            team_id INTEGER,
            player_id INTEGER,
            category TEXT,
            stat_type TEXT,
            stat_value_text TEXT,
            stat_value_num REAL
        );
        CREATE TABLE player_value_metrics (
            player_value_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER,
            week INTEGER,
            player_id INTEGER,
            team_id INTEGER,
            position TEXT,
            metric_name TEXT,
            metric_value REAL,
            plays INTEGER
        );
        CREATE TABLE player_advanced_metrics (
            player_advanced_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            metric_id TEXT NOT NULL,
            value REAL,
            sample_size INTEGER NOT NULL DEFAULT 0,
            cohort_id TEXT,
            metric_version TEXT,
            computed_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX ux_pam ON player_advanced_metrics(player_id, season_year, week, metric_id);

        CREATE TABLE player_advanced_metrics_season (
            player_advanced_metrics_season_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            metric_id TEXT NOT NULL,
            value REAL,
            sample_size INTEGER NOT NULL DEFAULT 0,
            cohort_id TEXT,
            percentile REAL,
            rank_in_cohort INTEGER,
            cohort_size INTEGER,
            metric_version TEXT,
            computed_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX ux_pams ON player_advanced_metrics_season(player_id, season_year, metric_id);
        """
    )


def _seed(conn: sqlite3.Connection) -> None:
    # Players
    conn.executemany(
        "INSERT INTO players(player_id, full_name, position) VALUES(?, ?, ?)",
        [
            (CARR, "C.J. Carr", "QB"),
            (BACKUP, "Backup QB", "QB"),
            (STAR_RB, "Star RB", "RB"),
            (STAR_WR, "Star WR", "WR"),
        ],
    )

    # Games (3 games for season 2025)
    conn.executemany(
        "INSERT INTO games(game_id, season_year, week, season_type) VALUES(?, ?, ?, ?)",
        [(i, SEASON, i, "regular") for i in range(1, 4)],
    )

    # Plays — Notre Dame as offense, 100 plays per game × 3 = 300 plays.
    # 54% success, 12% explosive-20plus. Other team same, for baseline.
    plays_rows = []
    play_id = 1
    drive_id = 1
    for team_id in (NOTRE_DAME, OTHER_TEAM):
        for game_id in range(1, 4):
            for idx in range(100):
                success = 1 if idx < 54 else 0
                yards = 22 if idx < 12 else 3
                plays_rows.append(
                    (play_id, game_id, drive_id, team_id, None, success, yards, 0, "Rush", 1, 10, 50, 1, 0.2, 0.2, 0.5)
                )
                play_id += 1
            drive_id += 1
    conn.executemany(
        "INSERT INTO plays(play_id, game_id, drive_id, offense_team_id, defense_team_id, success_flag, yards_gained, is_garbage_time, play_type, down, distance, yard_line, period, epa, ppa, home_win_prob) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        plays_rows,
    )

    # Drives — 20 drives for Notre Dame × 3 games = 60 drives; 15 red-zone;
    # 10 end in TD inside 20.
    drive_rows = []
    drive_id_counter = 1000
    for game_id in range(1, 4):
        for i in range(20):
            end_yl = 15 if i < 5 else (40 if i < 10 else 80)
            result = "TD" if i < 3 else "Punt"
            drive_rows.append((drive_id_counter, game_id, NOTRE_DAME, end_yl, result, 1, i, 50, 6, 30))
            drive_id_counter += 1
    conn.executemany(
        "INSERT INTO drives(drive_id, game_id, offense_team_id, end_yardline, result, period, drive_number, start_yardline, play_count, yards) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        drive_rows,
    )

    # player_value_metrics — Carr has 300 pass plays (wepa 0.41), 32 rush plays.
    # Backup has 20 pass plays (below min_sample=50).
    conn.executemany(
        "INSERT INTO player_value_metrics(season_year, week, player_id, team_id, position, metric_name, metric_value, plays) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (SEASON, 3, CARR, NOTRE_DAME, "QB", "wepa_passing", 0.41, 300),
            (SEASON, 3, CARR, NOTRE_DAME, "QB", "wepa_rushing", 0.10, 32),
            (SEASON, 3, BACKUP, NOTRE_DAME, "QB", "wepa_passing", 0.05, 20),
            (SEASON, 3, STAR_RB, OTHER_TEAM, "RB", "wepa_rushing", 0.30, 200),
        ],
    )

    # player_game_stats — Carr: 195/300 for 2700 yards, 24 TDs, 6 INTs.
    # Backup: 10/20 for 100 yards, 1 TD, 0 INTs.
    # Star RB: 200 carries for 1200 yards, 14 TDs
    # Star WR: 80 receptions for 1250 yards, 10 TDs
    for game_id in range(1, 4):
        conn.executemany(
            "INSERT INTO player_game_stats(game_id, season_year, week, team_id, player_id, category, stat_type, stat_value_text, stat_value_num) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (game_id, SEASON, game_id, NOTRE_DAME, CARR, "passing", "C/ATT", "65/100", 65.0),
                (game_id, SEASON, game_id, NOTRE_DAME, CARR, "passing", "YDS", "900", 900.0),
                (game_id, SEASON, game_id, NOTRE_DAME, CARR, "passing", "TD", "8", 8.0),
                (game_id, SEASON, game_id, NOTRE_DAME, CARR, "passing", "INT", "2", 2.0),
                (game_id, SEASON, game_id, NOTRE_DAME, CARR, "passing", "QBR", "85.0", 85.0),
                (game_id, SEASON, game_id, NOTRE_DAME, CARR, "rushing", "CAR", "11", 11.0),
                (game_id, SEASON, game_id, NOTRE_DAME, CARR, "rushing", "YDS", "66", 66.0),
                (game_id, SEASON, game_id, NOTRE_DAME, CARR, "rushing", "TD", "1", 1.0),
                (game_id, SEASON, game_id, NOTRE_DAME, BACKUP, "passing", "C/ATT", "3/7", 3.0),
                (game_id, SEASON, game_id, NOTRE_DAME, BACKUP, "passing", "YDS", "33", 33.0),
                (game_id, SEASON, game_id, OTHER_TEAM, STAR_RB, "rushing", "CAR", "67", 67.0),
                (game_id, SEASON, game_id, OTHER_TEAM, STAR_RB, "rushing", "YDS", "400", 400.0),
                (game_id, SEASON, game_id, OTHER_TEAM, STAR_RB, "rushing", "TD", "5", 5.0),
                (game_id, SEASON, game_id, OTHER_TEAM, STAR_WR, "receiving", "REC", "27", 27.0),
                (game_id, SEASON, game_id, OTHER_TEAM, STAR_WR, "receiving", "YDS", "415", 415.0),
                (game_id, SEASON, game_id, OTHER_TEAM, STAR_WR, "receiving", "TD", "4", 4.0),
            ],
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_registry_has_13_metrics() -> None:
    # v1 kickoff scope: at least 13 metric_ids registered.
    assert len(METRICS) >= 13
    # Required metric_ids per design.
    required = {
        "wepa_passing_per_play",
        "wepa_rushing_per_play",
        "pass_completion_pct",
        "pass_ypa",
        "pass_td_rate",
        "pass_int_rate",
        "pass_yards_per_game",
        "qbr_season_avg",
        "rush_ypc",
        "rush_yards_per_game",
        "receiving_ypr",
        "receiving_yards_per_game",
        "team_success_rate_on_offense",
        "team_explosive_rate_20plus_on_offense",
        "team_red_zone_td_rate",
    }
    assert required <= set(METRICS.keys())


def test_aggregate_player_game_stats_parses_c_att() -> None:
    rows = [
        {"category": "passing", "stat_type": "C/ATT", "stat_value_text": "195/300", "stat_value_num": 195.0, "game_id": 1},
        {"category": "passing", "stat_type": "YDS", "stat_value_text": "2700", "stat_value_num": 2700.0, "game_id": 1},
    ]
    totals = _aggregate_player_game_stats(rows)
    assert totals["pass_completions"] == 195
    assert totals["pass_attempts"] == 300
    assert totals["pass_yards"] == 2700
    assert totals["games_counted"] == 1


def test_compute_writes_carr_13_qb_metric_rows(db: Database) -> None:
    written = compute_player_advanced_metrics(db, SEASON, week=None)
    assert written > 0
    rows = db.query_all(
        "select metric_id, value, sample_size from player_advanced_metrics "
        "where player_id = :pid and season_year = :s and week = 0",
        {"pid": CARR, "s": SEASON},
    )
    metric_ids = {r["metric_id"] for r in rows}
    # QB gets all 13 of its applicable metrics populated (the v1 spec).
    expected = {
        "wepa_passing_per_play",
        "wepa_rushing_per_play",
        "pass_completion_pct",
        "pass_ypa",
        "pass_td_rate",
        "pass_int_rate",
        "pass_yards_per_game",
        "qbr_season_avg",
        "rush_ypc",
        "rush_yards_per_game",
        "team_success_rate_on_offense",
        "team_explosive_rate_20plus_on_offense",
        "team_red_zone_td_rate",
    }
    assert expected <= metric_ids, f"missing: {expected - metric_ids}"
    assert len(expected) == 13  # sanity


def test_carr_wepa_per_play_math(db: Database) -> None:
    compute_player_advanced_metrics(db, SEASON, week=None)
    row = db.query_one(
        "select value, sample_size from player_advanced_metrics "
        "where player_id = :pid and season_year = :s and week = 0 and metric_id = 'wepa_passing_per_play'",
        {"pid": CARR, "s": SEASON},
    )
    assert row is not None
    # 0.41 / 300 = 0.001366...
    assert abs(row["value"] - (0.41 / 300)) < 1e-6
    assert row["sample_size"] == 300


def test_carr_completion_pct_math(db: Database) -> None:
    compute_player_advanced_metrics(db, SEASON, week=None)
    row = db.query_one(
        "select value, sample_size from player_advanced_metrics "
        "where player_id = :pid and season_year = :s and week = 0 and metric_id = 'pass_completion_pct'",
        {"pid": CARR, "s": SEASON},
    )
    assert row is not None
    # 195/300 * 100 = 65.0
    assert abs(row["value"] - 65.0) < 1e-6
    assert row["sample_size"] == 300


def test_carr_team_success_rate_matches_seed(db: Database) -> None:
    compute_player_advanced_metrics(db, SEASON, week=None)
    row = db.query_one(
        "select value, sample_size from player_advanced_metrics "
        "where player_id = :pid and season_year = :s and week = 0 and metric_id = 'team_success_rate_on_offense'",
        {"pid": CARR, "s": SEASON},
    )
    # Notre Dame has 300 offense plays with 54% success.
    assert row is not None
    assert abs(row["value"] - 54.0) < 1e-6
    assert row["sample_size"] == 300


def test_carr_red_zone_td_rate_matches_seed(db: Database) -> None:
    compute_player_advanced_metrics(db, SEASON, week=None)
    row = db.query_one(
        "select value, sample_size from player_advanced_metrics "
        "where player_id = :pid and season_year = :s and week = 0 and metric_id = 'team_red_zone_td_rate'",
        {"pid": CARR, "s": SEASON},
    )
    # Notre Dame has 3 games × 5 drives ending <=20 yd line = 15; of those 3/game end
    # in 'TD' (i<3 AND i<5 is always True) = 9 TDs.
    assert row is not None
    assert abs(row["value"] - (9.0 / 15.0 * 100.0)) < 1e-6
    assert row["sample_size"] == 15


def test_below_min_sample_nulls_value(db: Database) -> None:
    compute_player_advanced_metrics(db, SEASON, week=None)
    row = db.query_one(
        "select value, sample_size from player_advanced_metrics "
        "where player_id = :pid and season_year = :s and week = 0 and metric_id = 'pass_ypa'",
        {"pid": BACKUP, "s": SEASON},
    )
    # Backup has 21 pass attempts (3/7 × 3 games), below min_sample=40.
    assert row is not None
    assert row["value"] is None
    assert row["sample_size"] == 21


def test_idempotent_upsert(db: Database) -> None:
    first = compute_player_advanced_metrics(db, SEASON, week=None)
    second = compute_player_advanced_metrics(db, SEASON, week=None)
    # Same row count both times (upsert preserved uniqueness).
    assert first == second
    total = db.query_one(
        "select count(*) as c from player_advanced_metrics where season_year=:s",
        {"s": SEASON},
    )
    assert total["c"] == first


def test_season_rollup_writes_percentiles(db: Database) -> None:
    compute_player_advanced_metrics_season(db, SEASON)
    # Carr's wepa_passing_per_play should have a percentile in the QB cohort.
    row = db.query_one(
        "select percentile, rank_in_cohort, cohort_size, cohort_id "
        "from player_advanced_metrics_season "
        "where player_id = :pid and season_year = :s and metric_id = 'wepa_passing_per_play'",
        {"pid": CARR, "s": SEASON},
    )
    # With only Carr qualifying (Backup is below min_sample=50 on 20 plays),
    # cohort_size = 1 and percentile = 100.
    assert row is not None
    assert row["cohort_size"] == 1
    assert row["percentile"] == pytest.approx(100.0)
    assert row["rank_in_cohort"] == 1
    assert row["cohort_id"] == "qb_season_2025"


def test_position_filtering_rb_no_pass_metrics(db: Database) -> None:
    compute_player_advanced_metrics(db, SEASON, week=None)
    metric_ids = {
        r["metric_id"]
        for r in db.query_all(
            "select metric_id from player_advanced_metrics "
            "where player_id = :pid and season_year = :s",
            {"pid": STAR_RB, "s": SEASON},
        )
    }
    # RB must NOT produce pass_* metrics.
    assert not any(m.startswith("pass_") or m.startswith("qbr_") for m in metric_ids)
    # RB MUST produce rush_* metrics.
    assert "rush_ypc" in metric_ids
    assert "rush_yards_per_game" in metric_ids


def test_position_filtering_wr_rec_only(db: Database) -> None:
    compute_player_advanced_metrics(db, SEASON, week=None)
    metric_ids = {
        r["metric_id"]
        for r in db.query_all(
            "select metric_id from player_advanced_metrics "
            "where player_id = :pid and season_year = :s",
            {"pid": STAR_WR, "s": SEASON},
        )
    }
    # WR must NOT produce pass/rush/qbr metrics.
    forbidden = {"pass_ypa", "pass_completion_pct", "rush_ypc", "qbr_season_avg", "wepa_passing_per_play"}
    assert not (forbidden & metric_ids)
    # WR MUST produce receiving metrics.
    assert "receiving_ypr" in metric_ids
    assert "receiving_yards_per_game" in metric_ids


def test_metric_version_stamped(db: Database) -> None:
    compute_player_advanced_metrics(db, SEASON, week=None)
    row = db.query_one(
        "select metric_version from player_advanced_metrics limit 1",
    )
    assert row is not None
    assert row["metric_version"] == METRIC_VERSION
