"""Fault-injection tests for the Wave 0 Data Health Spine.

These run against TINY synthetic in-memory / temp sqlite DBs (never the 1.3 GB
production file). The contract is simple and adversarial: for every pillar we
build a known-good miniature DB, assert it reads clean, then inject ONE fault
and assert the pillar flips to the right ``fail`` / ``unknown`` status. A check
that cannot catch its own injected fault does not ship (spec W0.4 / W0.8 §3).

Faults exercised (one per the brief):
  * a dropped season            -> completeness FAIL (critical, regime=normal)
  * a null key column           -> validity null-density FAIL (warning)
  * an orphan FK                -> integrity orphan-FK FAIL (critical)
  * a duplicate grain row       -> integrity dup-grain FAIL (critical)
  * a renamed/dropped column    -> validity schema-drift FAIL (critical) AND a
                                   completeness UNKNOWN when the season column
                                   itself vanishes (never a silent pass).

Plus regime sanity: a COVID-reduced 2020 spine reads GREEN, never "incomplete".
"""
from __future__ import annotations

import sqlite3

import pytest

from cfb_rankings.data_health.checks import (
    completeness,
    integrity,
    validity,
)
from cfb_rankings.data_health import calendar as dh_calendar
from cfb_rankings.data_health import gate as dh_gate
from cfb_rankings.data_health.checks import run_all


# ---------------------------------------------------------------------------
# Synthetic DB builders — minimal real-schema spine (verified column names).
# ---------------------------------------------------------------------------

# The 5 game-spine seasons the contracts expect: 2020(covid)..2025(in_progress).
# We populate a "healthy" subset so the known-good DB reads clean, then mutate.
_SPINE_SEASONS = (2020, 2021, 2022, 2023, 2024, 2025)


def _mem_db() -> sqlite3.Connection:
    """A fresh in-memory connection with the spine + universe tables created."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE conferences (conference_id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE team_seasons (
            team_id INTEGER, season_year INTEGER, level_code TEXT,
            conference_id INTEGER
        );
        CREATE TABLE teams (team_id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE players (player_id INTEGER PRIMARY KEY, full_name TEXT,
            position TEXT);
        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY, season_year INTEGER,
            home_team_id INTEGER, away_team_id INTEGER,
            home_points INTEGER, away_points INTEGER,
            start_time_utc TEXT, status TEXT
        );
        CREATE TABLE player_game_stats (
            player_game_stat_id INTEGER PRIMARY KEY, game_id INTEGER,
            player_id INTEGER, team_id INTEGER, category TEXT, stat_type TEXT,
            season_year INTEGER
        );
        CREATE TABLE roster_entries (
            roster_entry_id INTEGER PRIMARY KEY, player_id INTEGER,
            team_id INTEGER, season_year INTEGER, position TEXT
        );
        CREATE TABLE power_ratings_weekly (
            power_rating_weekly_id INTEGER PRIMARY KEY, team_id INTEGER,
            season_year INTEGER, week INTEGER
        );
        CREATE TABLE official_rankings (
            official_ranking_id INTEGER PRIMARY KEY, team_id INTEGER,
            season_year INTEGER, week INTEGER
        );
        """
    )
    return conn


def _seed_universe(conn: sqlite3.Connection, n_teams: int = 12) -> None:
    """One real FBS conference + ``n_teams`` teams enrolled in every season."""
    conn.execute("INSERT INTO conferences VALUES (1, 'SEC')")  # a real FBS conf
    for tid in range(1, n_teams + 1):
        conn.execute("INSERT INTO teams VALUES (?, ?)", (tid, f"Team{tid}"))
        conn.execute("INSERT INTO players VALUES (?, ?, ?)", (tid, f"Player{tid}", "QB"))
        for season in _SPINE_SEASONS:
            conn.execute(
                "INSERT INTO team_seasons VALUES (?,?,?,?)",
                (tid, season, "FBS", 1),
            )


def _seed_games(
    conn: sqlite3.Connection,
    season: int,
    home_games_per_team: int,
    n_teams: int = 12,
    status: str = "Final",
) -> None:
    """Give every team ``home_games_per_team`` home games in ``season``."""
    gid = conn.execute("SELECT COALESCE(MAX(game_id),0) FROM games").fetchone()[0]
    for home in range(1, n_teams + 1):
        for k in range(home_games_per_team):
            gid += 1
            away = (home % n_teams) + 1
            conn.execute(
                "INSERT INTO games VALUES (?,?,?,?,?,?,?,?)",
                (gid, season, home, away, 21, 14, f"{season}-09-0{(k % 9) + 1} 18:00:00", status),
            )


def _seed_spine_dependents(conn: sqlite3.Connection, season: int) -> None:
    """A couple of rows in each non-games spine table for ``season``."""
    pgs = conn.execute(
        "SELECT COALESCE(MAX(player_game_stat_id),0) FROM player_game_stats"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO player_game_stats VALUES (?,?,?,?,?,?,?)",
        (pgs + 1, 1, 1, 1, "rushing", "yards", season),
    )
    conn.execute(
        "INSERT INTO roster_entries VALUES (?,?,?,?,?)",
        (season * 10 + 1, 1, 1, season, "QB"),
    )
    conn.execute(
        "INSERT INTO power_ratings_weekly VALUES (?,?,?,?)",
        (season * 10 + 1, 1, season, 1),
    )
    conn.execute(
        "INSERT INTO official_rankings VALUES (?,?,?,?)",
        (season * 10 + 1, 1, season, 1),
    )


def _healthy_spine_db() -> sqlite3.Connection:
    """A miniature spine that should read GREEN-ish for the spine pillars.

    Every normal season is fully present + dense; 2020 is COVID-reduced (above
    the covid floor, below the normal one) so it tests the regime exemption.
    """
    conn = _mem_db()
    _seed_universe(conn)
    # 2020 COVID: 4 home games/team -> above covid floor (3.0), below normal (5.5).
    _seed_games(conn, 2020, home_games_per_team=4)
    # 2021,2022,2023,2024: dense normal seasons (6 >= 5.5).
    for season in (2021, 2022, 2023, 2024):
        _seed_games(conn, season, home_games_per_team=6)
    # 2025 in-progress: a few games present.
    _seed_games(conn, 2025, home_games_per_team=2)
    for season in _SPINE_SEASONS:
        _seed_spine_dependents(conn, season)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Isolate the validity schema baseline so tests never touch the checked-in file.
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_signature(tmp_path, monkeypatch):
    """Point validity's schema-signature baseline at a throwaway temp file."""
    sig = tmp_path / "schema_signatures.json"
    monkeypatch.setattr(validity, "_SIGNATURE_PATH", str(sig))
    return sig


def _spine_completeness(conn) -> dict:
    """Map check_id -> CheckResult for the game-spine completeness rows."""
    return {r.check_id: r for r in completeness.run(conn)}


# ===========================================================================
# Baseline: the healthy synthetic DB reads clean for the spine pillars.
# ===========================================================================

def test_healthy_spine_completeness_is_clean():
    conn = _healthy_spine_db()
    rows = {r.check_id: r for r in completeness.run(conn)}
    # All 5 game-spine datasets, all 6 seasons, should PASS (2020 via covid floor).
    for ds in ("games", "player_game_stats", "roster_entries",
               "power_ratings_weekly", "official_rankings"):
        for season in _SPINE_SEASONS:
            r = rows[f"completeness.{ds}.{season}"]
            assert r.status == "pass", (
                f"{ds} {season} should pass on the healthy DB, got {r.status}: {r.detail}"
            )


def test_2020_covid_not_flagged_incomplete():
    """Regime sanity: a COVID-reduced 2020 spine is GREEN, never 'incomplete'."""
    conn = _healthy_spine_db()
    rows = _spine_completeness(conn)
    g20 = rows["completeness.games.2020"]
    assert g20.status == "pass"
    assert "covid" in g20.detail.lower()


def test_healthy_integrity_is_clean():
    conn = _healthy_spine_db()
    rows = {r.check_id: r for r in integrity.run(conn)}
    # All dup-grain + orphan-FK + impossible-score assertions pass on a clean DB.
    for cid, r in rows.items():
        if "completed_scoreless" in cid:
            continue  # not present in the synthetic DB (no 0-0 finals)
        assert r.status == "pass", f"{cid} should be clean, got {r.status}: {r.detail}"


# ===========================================================================
# FAULT 1 — a dropped season -> completeness FAIL (critical, regime=normal).
# ===========================================================================

def test_dropped_season_fails_completeness_critical():
    conn = _healthy_spine_db()
    # Wipe an entire normal season from the games table (the 2023 black-hole class).
    conn.execute("DELETE FROM games WHERE season_year = 2024")
    conn.commit()
    rows = _spine_completeness(conn)
    r = rows["completeness.games.2024"]
    assert r.status == "fail"
    assert r.severity == "critical"
    assert "MISSING" in r.detail


def test_real_2023_blackhole_is_critical_fail():
    """The verified live finding: game-spine 2023 absent => RED/critical (NOT a
    silently-acknowledged 'known_missing' pass)."""
    conn = _healthy_spine_db()
    # Drop 2023 across the whole spine, mirroring the production black hole.
    for tbl in ("games", "player_game_stats", "roster_entries",
                "power_ratings_weekly", "official_rankings"):
        conn.execute(f"DELETE FROM {tbl} WHERE season_year = 2023")
    conn.commit()
    rows = _spine_completeness(conn)
    for ds in ("games", "player_game_stats", "roster_entries",
               "power_ratings_weekly", "official_rankings"):
        r = rows[f"completeness.{ds}.2023"]
        assert r.status == "fail" and r.severity == "critical", (
            f"{ds} 2023 must be critical-fail, got {r.status}/{r.severity}: {r.detail}"
        )
    # And the regime itself must resolve to 'normal', not 'known_missing'.
    assert dh_calendar.regime_for("game_spine", 2023) == "normal"


def test_sparse_season_fails_density():
    """Present-but-sparse (the 2022 half-season class) fails the density gate."""
    conn = _healthy_spine_db()
    # 2024 normally has 6 home games/team; cut it to ~2 (well under the 5.5 floor)
    # while keeping all teams present, so a presence check would still pass.
    conn.execute(
        "DELETE FROM games WHERE season_year = 2024 AND (game_id % 3) <> 0"
    )
    conn.commit()
    rows = _spine_completeness(conn)
    r = rows["completeness.games.2024"]
    assert r.status == "fail" and r.severity == "critical"
    assert "SPARSE" in r.detail


# ===========================================================================
# FAULT 2 — a null key column -> validity null-density FAIL (warning).
# ===========================================================================

def test_null_key_column_fails_validity(isolated_signature):
    conn = _healthy_spine_db()
    # Give player_game_stats enough rows that the null share is meaningful, then
    # null out a contract-declared required-non-null key column. ``category`` is
    # in player_game_stats.required_non_null and is text-empty-as-null aware.
    for i in range(2, 12):
        conn.execute(
            "INSERT INTO player_game_stats VALUES (?,?,?,?,?,?,?)",
            (1000 + i, 1, 1, 1, "rushing", "yards", 2024),
        )
    # Establish the schema baseline first (first run mints + passes it).
    validity.run(conn)
    # Now null out 100% of player_game_stats.category -> should warn-fail.
    conn.execute("UPDATE player_game_stats SET category = NULL")
    conn.commit()
    rows = {r.check_id: r for r in validity.run(conn)}
    r = rows["validity.null.player_game_stats.category"]
    assert r.status == "fail"
    assert r.severity == "warning"
    assert "null" in r.detail.lower()


def test_players_position_null_density_warns(isolated_signature):
    """The verified players.position finding: high null density => warning fail."""
    conn = _healthy_spine_db()
    validity.run(conn)  # baseline
    # Make 50% of players.position null (well over the 12% threshold).
    conn.execute("UPDATE players SET position = NULL WHERE player_id % 2 = 0")
    conn.commit()
    rows = {r.check_id: r for r in validity.run(conn)}
    r = rows["validity.null.players.position"]
    assert r.status == "fail" and r.severity == "warning"


# ===========================================================================
# FAULT 3 — an orphan FK -> integrity orphan-FK FAIL (critical).
# ===========================================================================

def test_orphan_fk_fails_integrity_critical():
    conn = _healthy_spine_db()
    # Point a player_game_stats row at a game_id that does not exist.
    conn.execute(
        "INSERT INTO player_game_stats VALUES (999999, 888888, 1, 1, 'rushing', 'yards', 2024)"
    )
    conn.commit()
    rows = {r.check_id: r for r in integrity.run(conn)}
    r = rows["integrity.orphan_fk.player_game_stats.game_id"]
    assert r.status == "fail"
    assert r.severity == "critical"
    assert "orphan" in r.detail.lower()


def test_orphan_team_fk_in_games_fails():
    conn = _healthy_spine_db()
    conn.execute(
        "INSERT INTO games VALUES (777777, 2024, 4242, 1, 10, 7, '2024-09-01 18:00:00', 'Final')"
    )
    conn.commit()
    rows = {r.check_id: r for r in integrity.run(conn)}
    r = rows["integrity.orphan_fk.games.home_team_id"]
    assert r.status == "fail" and r.severity == "critical"


# ===========================================================================
# FAULT 4 — a duplicate grain row -> integrity dup-grain FAIL (critical).
# ===========================================================================

def test_duplicate_grain_fails_integrity_critical():
    conn = _healthy_spine_db()
    # SQLite lets us bypass the PK uniqueness via a second table with the same
    # grain column; simplest path is to drop the PK constraint by rebuilding the
    # table without it, then insert a dup game_id.
    conn.executescript(
        """
        CREATE TABLE games_nodup (
            game_id INTEGER, season_year INTEGER,
            home_team_id INTEGER, away_team_id INTEGER,
            home_points INTEGER, away_points INTEGER,
            start_time_utc TEXT, status TEXT
        );
        INSERT INTO games_nodup SELECT * FROM games;
        DROP TABLE games;
        ALTER TABLE games_nodup RENAME TO games;
        """
    )
    # Duplicate an existing game_id.
    first_gid = conn.execute("SELECT game_id FROM games LIMIT 1").fetchone()[0]
    conn.execute(
        "INSERT INTO games VALUES (?, 2024, 1, 2, 0, 0, '2024-09-01 18:00:00', 'Final')",
        (first_gid,),
    )
    conn.commit()
    rows = {r.check_id: r for r in integrity.run(conn)}
    r = rows["integrity.dup_grain.games"]
    assert r.status == "fail"
    assert r.severity == "critical"


# ===========================================================================
# FAULT 5 — a renamed / dropped column -> validity schema-drift FAIL (critical)
#           + completeness UNKNOWN when the season column itself vanishes.
# ===========================================================================

def test_renamed_column_fails_schema_drift(isolated_signature):
    conn = _healthy_spine_db()
    # First run mints the baseline from the healthy schema and passes.
    first = {r.check_id: r for r in validity.run(conn)}
    assert first["validity.schema.baseline"].status == "pass"

    # Rename a column on a contract table (the Savant display_name bug class).
    conn.execute("ALTER TABLE games RENAME COLUMN status TO game_status")
    conn.commit()
    rows = {r.check_id: r for r in validity.run(conn)}
    r = rows["validity.schema.games"]
    assert r.status == "fail"
    assert r.severity == "critical"
    assert "DRIFT" in r.detail


def test_dropped_season_column_is_unknown_not_silent_pass():
    """If the season column itself disappears, completeness must return UNKNOWN
    for that dataset (never a silent pass that the gate could read as GREEN)."""
    conn = _healthy_spine_db()
    # Rebuild official_rankings without ANY recognised season column.
    conn.executescript(
        """
        CREATE TABLE official_rankings_x (
            official_ranking_id INTEGER PRIMARY KEY, team_id INTEGER, week INTEGER
        );
        DROP TABLE official_rankings;
        ALTER TABLE official_rankings_x RENAME TO official_rankings;
        """
    )
    conn.commit()
    rows = {r.check_id: r for r in completeness.run(conn)}
    r = rows["completeness.official_rankings.season_column"]
    assert r.status == "unknown"
    assert r.severity == "critical"  # spine contract severity


def test_missing_table_is_unknown_not_pass():
    """A contract table missing entirely => completeness UNKNOWN, never pass."""
    conn = _healthy_spine_db()
    conn.execute("DROP TABLE power_ratings_weekly")
    conn.commit()
    rows = {r.check_id: r for r in completeness.run(conn)}
    r = rows["completeness.power_ratings_weekly.season_column"]
    assert r.status == "unknown"


# ===========================================================================
# Gate-level behaviour over the synthetic faults.
# ===========================================================================

def test_gate_unknown_on_empty_results_never_green():
    gate = dh_gate.compute_gate([])
    assert gate["overall"] == "UNKNOWN"


def test_gate_red_on_any_critical_fail():
    conn = _healthy_spine_db()
    conn.execute("DELETE FROM games WHERE season_year = 2024")  # drop a normal season
    conn.commit()
    results = completeness.run(conn)
    gate = dh_gate.compute_gate(results)
    assert gate["overall"] == "RED"
    assert gate["counts"]["critical_fail"] >= 1


def test_gate_unknown_never_collapses_to_green():
    """A critical UNKNOWN (un-evaluable required assertion) must not read GREEN."""
    conn = _healthy_spine_db()
    conn.execute("DROP TABLE games")  # forces a critical-severity unknown
    conn.commit()
    results = completeness.run(conn)
    gate = dh_gate.compute_gate(results)
    assert gate["overall"] in ("UNKNOWN", "RED")
    assert gate["overall"] != "GREEN"


def test_run_all_isolates_a_broken_pillar(isolated_signature, monkeypatch):
    """A pillar that raises is converted to one UNKNOWN/critical row, never
    crashing the run or silently dropping the others."""
    conn = _healthy_spine_db()

    def boom(_conn):
        raise RuntimeError("injected pillar explosion")

    monkeypatch.setattr(integrity, "run", boom)
    results = run_all(conn)
    err = [r for r in results if r.check_id.endswith(".pillar_error")]
    assert err, "a raising pillar must surface as a pillar_error row"
    assert err[0].status == "unknown" and err[0].severity == "critical"
    # The other pillars still produced rows.
    assert any(r.pillar == "completeness" for r in results)
