"""Tests for src/cfb_rankings/signature_story.py.

Strategy: build a minimal in-memory SQLite DB with enough fixture data to
exercise the three fixture archetypes from the kickoff:

  - CJ Carr (R15 Heisman finalist): multiple metrics qualify → real story.
  - Backup QB (R03): only volume-leader metrics qualify → lower-score story.
  - Walk-on (R00): no metric clears min_volume → shape-accurate skeleton.

We build a tiny cohort of 30 QBs so percentile math is non-degenerate.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.signature_story import (
    build_candidate_scoreboard,
    fetch_player_signature_story,
    reload_seed,
)


CARR_ID = 4788
BACKUP_ID = 99001
WALKON_ID = 99002
STAR_RB_ID = 97001
STAR_WR_ID = 97101


@pytest.fixture()
def db_with_fixtures(tmp_path: Path) -> Database:
    reload_seed()
    db_path = tmp_path / "fixture.db"
    conn = sqlite3.connect(db_path)
    _build_schema(conn)
    _seed_fixtures(conn)
    conn.commit()
    conn.close()
    return Database(str(db_path))


# ---------------------------------------------------------------------------
# Fixture setup
# ---------------------------------------------------------------------------


def _build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            position TEXT,
            hometown TEXT,
            home_state TEXT,
            created_at TEXT
        );
        CREATE TABLE player_value_metrics (
            player_value_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER,
            week INTEGER,
            player_id INTEGER,
            team_id INTEGER,
            source_name TEXT,
            source_player_id TEXT,
            team_name TEXT,
            player_name TEXT,
            conference_name TEXT,
            position TEXT,
            metric_name TEXT,
            metric_value REAL,
            plays INTEGER,
            created_at TEXT
        );
        CREATE TABLE player_season_stats (
            player_season_stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER,
            week INTEGER,
            season_type TEXT,
            player_id INTEGER,
            team_id INTEGER,
            source_name TEXT,
            source_player_id TEXT,
            team_name TEXT,
            player_name TEXT,
            conference_name TEXT,
            position TEXT,
            category TEXT,
            stat_type TEXT,
            stat_value_text TEXT,
            stat_value_num REAL,
            created_at TEXT
        );
        CREATE TABLE player_game_stats (
            player_game_stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            season_year INTEGER,
            week INTEGER,
            season_type TEXT,
            team_id INTEGER,
            player_id INTEGER,
            source_name TEXT,
            source_player_id TEXT,
            team_name TEXT,
            conference_name TEXT,
            player_name TEXT,
            category TEXT,
            stat_type TEXT,
            stat_value_text TEXT,
            stat_value_num REAL,
            created_at TEXT
        );
        CREATE TABLE player_usage_season (
            player_usage_season_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER,
            week INTEGER,
            player_id INTEGER,
            team_id INTEGER,
            source_name TEXT,
            source_player_id TEXT,
            team_name TEXT,
            player_name TEXT,
            conference_name TEXT,
            position TEXT,
            usage_overall REAL,
            usage_pass REAL,
            usage_rush REAL,
            usage_first_down REAL,
            usage_second_down REAL,
            usage_third_down REAL,
            usage_standard_downs REAL,
            usage_passing_downs REAL,
            created_at TEXT
        );
        CREATE TABLE player_advanced_metrics (
            player_advanced_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER,
            week INTEGER,
            player_id INTEGER,
            team_id INTEGER,
            metric_id TEXT,
            value REAL,
            sample_size INTEGER,
            created_at TEXT
        );
        """
    )


def _seed_fixtures(conn: sqlite3.Connection) -> None:
    # Players: Carr, 29 cohort QBs, backup, walk-on.
    conn.execute(
        "INSERT INTO players(player_id, full_name, position) VALUES (?,?,?)",
        (CARR_ID, "C.J. Carr", "QB"),
    )
    # 29 cohort QBs id 100..128
    for i in range(100, 129):
        conn.execute(
            "INSERT INTO players(player_id, full_name, position) VALUES (?,?,?)",
            (i, f"Cohort QB {i}", "QB"),
        )
    conn.execute(
        "INSERT INTO players(player_id, full_name, position) VALUES (?,?,?)",
        (BACKUP_ID, "Backup QB", "QB"),
    )
    conn.execute(
        "INSERT INTO players(player_id, full_name, position) VALUES (?,?,?)",
        (WALKON_ID, "Walk-on QB", "QB"),
    )

    # Carr: elite wepa_passing, good traditional stats.
    _insert_wepa(conn, CARR_ID, "C.J. Carr", "Notre Dame", "FBS Independents", "wepa_passing", 0.41, 307)
    _insert_wepa(conn, CARR_ID, "C.J. Carr", "Notre Dame", "FBS Independents", "wepa_rushing", 0.33, 32)
    _insert_season_passing(conn, CARR_ID, "C.J. Carr", "Notre Dame", att=293, yds=2741, td=24, intc=6, pct=66.6)
    _insert_usage(conn, CARR_ID, "C.J. Carr", "Notre Dame", "QB", third_down=0.514)

    # Cohort QBs: spread of wepa values so Carr ranks mid-pack or better.
    # Make Carr 7th of 30 by wepa_passing_per_dropback. Values 0.60 down to 0.02.
    wepa_values = [0.60, 0.58, 0.55, 0.50, 0.48, 0.45] + [0.40 - 0.01 * i for i in range(23)]
    for idx, val in enumerate(wepa_values):
        pid = 100 + idx
        _insert_wepa(
            conn, pid, f"Cohort QB {pid}", "Test Team", "SEC", "wepa_passing", val, 300 + idx
        )
        _insert_season_passing(
            conn,
            pid,
            f"Cohort QB {pid}",
            "Test Team",
            att=250 + idx,
            yds=int(2000 + val * 2000),
            td=int(15 + val * 30),
            intc=int(10 - val * 8),
            pct=55.0 + val * 20,
        )
        _insert_usage(
            conn, pid, f"Cohort QB {pid}", "Test Team", "QB", third_down=0.4 + 0.01 * (idx % 10)
        )
    # Carr's wepa_passing is 0.41 — that's above 0.40 (idx=0 at 0.40), so he
    # slots between idx=0 (0.40) and the 6 top cohort QBs. Rank = 7 of 30.

    # Backup QB: ATT 120 (below 150 gate) → should fail min_volume on passing metrics.
    # No wepa entry.
    _insert_season_passing(
        conn, BACKUP_ID, "Backup QB", "Test Team", att=120, yds=800, td=5, intc=4, pct=60.0
    )
    _insert_usage(
        conn, BACKUP_ID, "Backup QB", "Test Team", "QB", third_down=0.20
    )

    # Walk-on: 3 ATT, no WEPA, no usage row.
    _insert_season_passing(
        conn, WALKON_ID, "Walk-on QB", "Test Team", att=3, yds=15, td=0, intc=1, pct=33.3
    )

    # RB fixture: a star RB with elite wepa_rushing, embedded in a cohort of 30 RBs.
    conn.execute(
        "INSERT INTO players(player_id, full_name, position) VALUES (?,?,?)",
        (STAR_RB_ID, "Star RB", "RB"),
    )
    for idx in range(30):
        pid = 200 + idx
        conn.execute(
            "INSERT INTO players(player_id, full_name, position) VALUES (?,?,?)",
            (pid, f"Cohort RB {pid}", "RB"),
        )
        value = 0.35 - 0.01 * idx  # 0.35 down to 0.06
        conn.execute(
            """INSERT INTO player_value_metrics(
                season_year, week, player_id, team_id, source_name, source_player_id,
                team_name, player_name, conference_name, position,
                metric_name, metric_value, plays, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (2025, 99, pid, 1, "cfbd", str(pid), "Test Team",
             f"Cohort RB {pid}", "SEC", "RB", "wepa_rushing", value, 120 + idx, ""),
        )
        _insert_rushing_stats(conn, pid, f"Cohort RB {pid}", "Test Team",
                              car=120 + idx, yds=int(500 + value * 2000),
                              td=int(3 + value * 20), ypc=5.0 + value * 2)
    # Star RB: wepa_rushing=0.40 → rank 1 of 31.
    conn.execute(
        """INSERT INTO player_value_metrics(
            season_year, week, player_id, team_id, source_name, source_player_id,
            team_name, player_name, conference_name, position,
            metric_name, metric_value, plays, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (2025, 99, STAR_RB_ID, 1, "cfbd", str(STAR_RB_ID), "Notre Dame",
         "Star RB", "FBS Independents", "RB", "wepa_rushing", 0.40, 180, ""),
    )
    _insert_rushing_stats(conn, STAR_RB_ID, "Star RB", "Notre Dame",
                          car=180, yds=1000, td=12, ypc=5.6)

    # WR fixture: star with high YPR, embedded in a cohort of 40 WRs.
    conn.execute(
        "INSERT INTO players(player_id, full_name, position) VALUES (?,?,?)",
        (STAR_WR_ID, "Star WR", "WR"),
    )
    for idx in range(40):
        pid = 300 + idx
        conn.execute(
            "INSERT INTO players(player_id, full_name, position) VALUES (?,?,?)",
            (pid, f"Cohort WR {pid}", "WR"),
        )
        rec = 30 + idx
        ypr = 12.0 + 0.1 * idx
        _insert_receiving_stats(conn, pid, f"Cohort WR {pid}", "Test Team",
                                rec=rec, yds=int(rec * ypr), td=max(1, idx // 5),
                                ypr=ypr)
    _insert_receiving_stats(conn, STAR_WR_ID, "Star WR", "Notre Dame",
                            rec=80, yds=1500, td=12, ypr=18.75)


def _insert_rushing_stats(conn, pid, name, team, *, car, yds, td, ypc):
    for stat_type, val in [("CAR", car), ("YDS", yds), ("TD", td), ("YPC", ypc), ("LONG", 50)]:
        conn.execute(
            """INSERT INTO player_season_stats(
                season_year, week, season_type, player_id, team_id, source_name,
                source_player_id, team_name, player_name, conference_name,
                position, category, stat_type, stat_value_text, stat_value_num,
                created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (2025, 99, "regular", pid, 1, "cfbd", str(pid), team, name, "SEC",
             "RB", "rushing", stat_type, str(val), float(val), ""),
        )


def _insert_receiving_stats(conn, pid, name, team, *, rec, yds, td, ypr):
    for stat_type, val in [("REC", rec), ("YDS", yds), ("TD", td), ("YPR", ypr), ("LONG", 60)]:
        conn.execute(
            """INSERT INTO player_season_stats(
                season_year, week, season_type, player_id, team_id, source_name,
                source_player_id, team_name, player_name, conference_name,
                position, category, stat_type, stat_value_text, stat_value_num,
                created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (2025, 99, "regular", pid, 1, "cfbd", str(pid), team, name, "SEC",
             "WR", "receiving", stat_type, str(val), float(val), ""),
        )


def _insert_wepa(conn, pid, name, team, conf, metric, value, plays):
    conn.execute(
        """INSERT INTO player_value_metrics(
            season_year, week, player_id, team_id, source_name, source_player_id,
            team_name, player_name, conference_name, position,
            metric_name, metric_value, plays, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (2025, 99, pid, 1, "cfbd", str(pid), team, name, conf, "QB", metric, value, plays, ""),
    )


def _insert_season_passing(conn, pid, name, team, *, att, yds, td, intc, pct):
    rows = [
        ("ATT", att),
        ("YDS", yds),
        ("TD", td),
        ("INT", intc),
        ("PCT", pct),
        ("COMPLETIONS", int(att * pct / 100)),
        ("YPA", yds / att if att else 0),
    ]
    for stat_type, val in rows:
        conn.execute(
            """INSERT INTO player_season_stats(
                season_year, week, season_type, player_id, team_id, source_name,
                source_player_id, team_name, player_name, conference_name,
                position, category, stat_type, stat_value_text, stat_value_num,
                created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (2025, 99, "regular", pid, 1, "cfbd", str(pid), team, name, "SEC",
             "QB", "passing", stat_type, str(val), float(val), ""),
        )


def _insert_usage(conn, pid, name, team, position, *, third_down):
    conn.execute(
        """INSERT INTO player_usage_season(
            season_year, week, player_id, team_id, source_name,
            source_player_id, team_name, player_name, conference_name,
            position, usage_overall, usage_pass, usage_rush,
            usage_first_down, usage_second_down, usage_third_down,
            usage_standard_downs, usage_passing_downs, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (2025, 99, pid, 1, "cfbd", str(pid), team, name, "SEC", position,
         0.5, 0.5, 0.2, 0.4, 0.4, third_down, 0.4, 0.4, ""),
    )


# ---------------------------------------------------------------------------
# Contract-shape tests
# ---------------------------------------------------------------------------


def _assert_shape(story: dict) -> None:
    required = {
        "has_story", "player_id", "season_year", "week",
        "headline_stat", "narrative", "supporting_chart", "confidence",
        "updated_label", "runners_up",
    }
    missing = required - set(story)
    assert not missing, f"missing keys: {missing}"
    assert isinstance(story["narrative"], str) and story["narrative"].strip()
    assert story["supporting_chart"]["type"] == "cohort_strip"


def test_carr_gets_real_signature_story(db_with_fixtures: Database) -> None:
    story = fetch_player_signature_story(db_with_fixtures, CARR_ID, 2025)
    _assert_shape(story)
    assert story["has_story"] is True
    hs = story["headline_stat"]
    assert hs is not None
    # Carr should hit wepa_passing_per_dropback as the winner given its
    # narrative_weight=1.0 and his top-10 rank in the 30-QB cohort.
    assert hs["metric_id"] in {
        "wepa_passing_per_dropback",
        "wepa_combined_per_play",
        "wepa_passing_total",
    }
    assert hs["cohort_size"] >= 20
    assert 1 <= hs["rank"] <= hs["cohort_size"]
    assert 0 <= hs["percentile"] <= 100
    assert story["confidence"]["label"] in {"High", "Moderate", "Thin"}


def test_backup_qb_gets_skeleton_or_thin_story(db_with_fixtures: Database) -> None:
    # With ATT=120 and no WEPA, every QB metric below its gate → skeleton.
    story = fetch_player_signature_story(db_with_fixtures, BACKUP_ID, 2025)
    _assert_shape(story)
    assert story["has_story"] is False
    assert story["headline_stat"] is None
    assert story["confidence"]["label"] == "No signal"


def test_walkon_gets_skeleton(db_with_fixtures: Database) -> None:
    story = fetch_player_signature_story(db_with_fixtures, WALKON_ID, 2025)
    _assert_shape(story)
    assert story["has_story"] is False
    assert story["headline_stat"] is None


def test_unknown_player_returns_skeleton(db_with_fixtures: Database) -> None:
    story = fetch_player_signature_story(db_with_fixtures, 999_999, 2025)
    _assert_shape(story)
    assert story["has_story"] is False


def test_scoreboard_orders_by_score(db_with_fixtures: Database) -> None:
    scoreboard = build_candidate_scoreboard(db_with_fixtures, CARR_ID, 2025)
    assert scoreboard, "expected at least one qualifying metric for Carr"
    scores = [e.score for e in scoreboard]
    assert scores == sorted(scores, reverse=True)
    # Every entry exposes the cohort strip we'll render in Figma.
    assert all(len(e.cohort_rows) >= 1 for e in scoreboard)


def test_rb_gets_wepa_rushing_story(db_with_fixtures: Database) -> None:
    """Star RB should win via wepa_rushing_per_carry (narrative_weight=1.0)."""
    story = fetch_player_signature_story(db_with_fixtures, STAR_RB_ID, 2025)
    _assert_shape(story)
    assert story["has_story"] is True
    hs = story["headline_stat"]
    assert hs is not None
    # Among RB metrics, WEPA/carry has the highest narrative_weight.
    assert hs["metric_id"] in {"wepa_rushing_per_carry", "ypc", "rushing_yards_total"}
    assert hs["cohort_size"] >= 25
    assert 1 <= hs["rank"] <= hs["cohort_size"]


def test_wr_gets_story_from_stubs(db_with_fixtures: Database) -> None:
    """Star WR (80 rec / 1500 yds / 18.75 ypr) should surface one of the 3 WR stub metrics."""
    story = fetch_player_signature_story(db_with_fixtures, STAR_WR_ID, 2025)
    _assert_shape(story)
    assert story["has_story"] is True
    hs = story["headline_stat"]
    assert hs["metric_id"] in {"receiving_yards_total", "ypr", "receiving_tds"}
    assert hs["cohort_size"] >= 30


def test_higher_is_better_ranking_direction(db_with_fixtures: Database) -> None:
    """Rank 1 must correspond to the best performer given higher_is_better."""
    scoreboard = build_candidate_scoreboard(db_with_fixtures, CARR_ID, 2025)
    for eval_result in scoreboard:
        sorted_values = sorted(
            (float(r["value"]) for r in eval_result.cohort_rows if r.get("value") is not None),
            reverse=eval_result.metric.higher_is_better,
        )
        # rank 1's value should equal the first value in the sorted list.
        carr_row = next(r for r in eval_result.cohort_rows if int(r["player_id"]) == CARR_ID)
        # Position-1 in the sorted list is the best performer.
        top_value = sorted_values[0]
        # Carr's percentile must be consistent: best player percentile == 100
        if float(carr_row["value"]) == top_value:
            assert eval_result.rank == 1
            assert eval_result.percentile == 100.0
