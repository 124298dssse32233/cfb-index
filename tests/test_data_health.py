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

from pathlib import Path

from cfb_rankings.data_health.checks import (
    completeness,
    integrity,
    validity,
)
from cfb_rankings.data_health import calendar as dh_calendar
from cfb_rankings.data_health import gate as dh_gate
from cfb_rankings.data_health.checks import run_all
from cfb_rankings.data_health.checks.base import CheckResult
from cfb_rankings.data_health import snapshots as dh_snapshots
from cfb_rankings.data_health import alerting as dh_alerting


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


# ===========================================================================
# Active-guard layer — snapshot persistence + source-change diff + alerting.
# ===========================================================================

# Schema for the two additive tables (mirrors migration
# 20260612_01_data_health_snapshots.sql) so the round-trip test runs on a tiny
# temp DB without invoking the full migration runner.
_SNAPSHOT_SCHEMA = """
CREATE TABLE IF NOT EXISTS data_health_snapshot (
    snapshot_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    run_utc        TEXT,
    overall        TEXT,
    db_fingerprint TEXT,
    passrates_json TEXT,
    counts_json    TEXT,
    summary        TEXT
);
CREATE TABLE IF NOT EXISTS data_health_result (
    snapshot_id INTEGER,
    check_id    TEXT,
    pillar      TEXT,
    dataset     TEXT,
    season      INTEGER,
    status      TEXT,
    severity    TEXT,
    detail      TEXT
);
"""


def _r(check_id, pillar, status, *, dataset="ds", season=None, severity="warning",
       detail="d"):
    """Compact CheckResult builder for the guard-layer tests."""
    return CheckResult(
        check_id=check_id, pillar=pillar, dataset=dataset, season=season,
        status=status, severity=severity, detail=detail, evidence_sql="",
    )


def _snapshot_db(tmp_path) -> str:
    """A temp file DB carrying ONLY the two additive data_health_* tables."""
    db_path = tmp_path / "guard.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SNAPSHOT_SCHEMA)
    conn.commit()
    conn.close()
    return str(db_path)


def test_snapshot_persist_round_trips(tmp_path):
    """persist() writes one header + the result rows; latest() reads them back."""
    db_path = _snapshot_db(tmp_path)
    results = [
        _r("completeness.games.2023", "completeness", "fail",
           dataset="games", season=2023, severity="critical"),
        _r("freshness.source_class.cfbd", "freshness", "pass", dataset="cfbd"),
    ]
    gate = dh_gate.compute_gate(results)

    sid = dh_snapshots.persist(db_path, gate, results, now_utc="2026-06-12T00:00:00+00:00")
    assert isinstance(sid, int) and sid >= 1

    conn = sqlite3.connect(str(db_path))
    try:
        # Header round-trips with the gate's overall + a stable fingerprint.
        hdr = conn.execute(
            "SELECT run_utc, overall, db_fingerprint, summary "
            "FROM data_health_snapshot WHERE snapshot_id=?", (sid,)
        ).fetchone()
        assert hdr[0] == "2026-06-12T00:00:00+00:00"
        assert hdr[1] == gate["overall"]
        assert "schema=" in hdr[2]  # fingerprint has the spine schema-hash component

        rows = dh_snapshots.latest(conn)
        assert len(rows) == 2
        by_id = {r["check_id"]: r for r in rows}
        assert by_id["completeness.games.2023"]["season"] == 2023
        assert by_id["completeness.games.2023"]["status"] == "fail"
        assert by_id["freshness.source_class.cfbd"]["pillar"] == "freshness"
    finally:
        conn.close()


def test_persist_stamps_now_utc_when_omitted(tmp_path):
    """Omitting now_utc still stamps a value (no crash, non-null run_utc)."""
    db_path = _snapshot_db(tmp_path)
    sid = dh_snapshots.persist(db_path, dh_gate.compute_gate([]), [])
    conn = sqlite3.connect(str(db_path))
    try:
        run_utc = conn.execute(
            "SELECT run_utc FROM data_health_snapshot WHERE snapshot_id=?", (sid,)
        ).fetchone()[0]
        assert run_utc  # an ISO timestamp was stamped
    finally:
        conn.close()


def test_fingerprint_stable_and_db_sensitive(tmp_path):
    """Same file -> identical fingerprint; a different file -> a different one."""
    a = _snapshot_db(tmp_path)
    fp1 = dh_snapshots.compute_fingerprint(a)
    fp2 = dh_snapshots.compute_fingerprint(a)
    assert fp1 == fp2

    b = tmp_path / "other.db"
    conn = sqlite3.connect(str(b))
    conn.executescript(_SNAPSHOT_SCHEMA + "CREATE TABLE games (game_id INTEGER);")
    conn.commit()
    conn.close()
    assert dh_snapshots.compute_fingerprint(str(b)) != fp1


def test_previous_vs_latest_two_snapshots(tmp_path):
    """latest()/previous() resolve the newest and second-newest snapshots."""
    db_path = _snapshot_db(tmp_path)
    first = [_r("freshness.source_class.cfbd", "freshness", "pass", dataset="cfbd")]
    second = [_r("freshness.source_class.reddit", "freshness", "pass", dataset="reddit")]
    dh_snapshots.persist(db_path, dh_gate.compute_gate(first), first,
                         now_utc="2026-06-11T00:00:00+00:00")
    dh_snapshots.persist(db_path, dh_gate.compute_gate(second), second,
                         now_utc="2026-06-12T00:00:00+00:00")
    conn = sqlite3.connect(str(db_path))
    try:
        latest_ids = {r["check_id"] for r in dh_snapshots.latest(conn)}
        prev_ids = {r["check_id"] for r in dh_snapshots.previous(conn)}
        assert latest_ids == {"freshness.source_class.reddit"}
        assert prev_ids == {"freshness.source_class.cfbd"}
    finally:
        conn.close()


def test_diff_source_states_added_retired_newly_failing():
    """The whole add/retire/newly-failing story is derived from freshness rows."""
    prev = [
        _r("freshness.source_class.cfbd", "freshness", "pass", dataset="cfbd"),
        _r("freshness.source_class.reddit", "freshness", "pass", dataset="reddit"),
        _r("freshness.source_class.gdelt", "freshness", "fail", dataset="gdelt"),
        # A non-freshness row must be ignored entirely by the diff.
        _r("completeness.games.2023", "completeness", "fail", season=2023),
    ]
    curr = [
        _r("freshness.source_class.cfbd", "freshness", "pass", dataset="cfbd"),
        # reddit retired (gone), youtube added, gdelt still failing (NOT "newly"),
        # cfbd unchanged, and now reddit replaced by a newly-failing 'beat'.
        _r("freshness.source_class.youtube", "freshness", "pass", dataset="youtube"),
        _r("freshness.source_class.gdelt", "freshness", "fail", dataset="gdelt"),
        _r("freshness.source_class.beat", "freshness", "fail", dataset="beat"),
    ]
    diff = dh_snapshots.diff_source_states(prev, curr)
    assert diff["added"] == ["beat", "youtube"]
    assert diff["retired"] == ["reddit"]
    # gdelt was already failing -> not "newly"; beat is new + failing -> newly.
    assert diff["newly_failing"] == ["beat"]


def test_diff_works_against_persisted_dicts(tmp_path):
    """diff_source_states accepts the plain dict rows read back from a snapshot."""
    db_path = _snapshot_db(tmp_path)
    prev = [_r("freshness.source_class.cfbd", "freshness", "pass", dataset="cfbd")]
    curr = [_r("freshness.source_class.cfbd", "freshness", "fail", dataset="cfbd")]
    dh_snapshots.persist(db_path, dh_gate.compute_gate(prev), prev,
                         now_utc="2026-06-11T00:00:00+00:00")
    dh_snapshots.persist(db_path, dh_gate.compute_gate(curr), curr,
                         now_utc="2026-06-12T00:00:00+00:00")
    conn = sqlite3.connect(str(db_path))
    try:
        diff = dh_snapshots.diff_source_states(
            dh_snapshots.previous(conn), dh_snapshots.latest(conn)
        )
    finally:
        conn.close()
    assert diff["newly_failing"] == ["cfbd"]
    assert diff["added"] == [] and diff["retired"] == []


# --- alerting: per-class dedup + dry-run opens nothing ---------------------


def test_build_issue_payloads_dedupes_to_per_class_titles():
    """Many flagged rows collapse to ONE issue per regression class, stable title."""
    results = [
        # Two completeness fails for the SAME dataset -> ONE games issue.
        _r("completeness.games.2022", "completeness", "fail",
           dataset="games", season=2022, severity="critical"),
        _r("completeness.games.2023", "completeness", "fail",
           dataset="games", season=2023, severity="critical"),
        # A different dataset -> its own issue.
        _r("completeness.roster_entries.2023", "completeness", "fail",
           dataset="roster_entries", season=2023, severity="critical"),
        # Many freshness source-class fails -> ONE "source feeds unhealthy" issue.
        _r("freshness.source_class.athletics_template", "freshness", "fail",
           dataset="athletics_template"),
        _r("freshness.source_class.campus_template", "freshness", "fail",
           dataset="campus_template"),
        _r("freshness.inventory.overall", "freshness", "fail", dataset="scrape_health"),
        # A provenance ratchet drop -> ONE provenance issue.
        _r("provenance.conversation_documents.canonical_pct", "provenance", "fail",
           dataset="conversation_documents"),
    ]
    gate = dh_gate.compute_gate(results)
    payloads = dh_alerting.build_issue_payloads(gate, results)
    titles = sorted(p["title"] for p in payloads)

    assert titles == [
        "[data-health] games missing/sparse seasons",
        "[data-health] provenance coverage dropped",
        "[data-health] roster_entries missing/sparse seasons",
        "[data-health] source feeds unhealthy",
    ]
    # Stable + unique: no duplicate titles, so re-runs dedupe against open issues.
    assert len(titles) == len(set(titles))
    # The games issue body names BOTH failing seasons (not two separate issues).
    games_body = next(p["body"] for p in payloads
                      if p["title"].startswith("[data-health] games"))
    assert "2022" in games_body and "2023" in games_body


def test_build_issue_payloads_empty_on_clean_gate():
    """A clean (no-fail) run opens nothing."""
    results = [_r("freshness.source_class.cfbd", "freshness", "pass", dataset="cfbd")]
    assert dh_alerting.build_issue_payloads(dh_gate.compute_gate(results), results) == []


def test_open_issues_dry_run_opens_nothing(monkeypatch, capsys):
    """--dry-run prints the plan and NEVER shells out to gh."""
    called = {"which": 0, "run": 0}

    def _no_which(_name):
        called["which"] += 1
        return "/usr/bin/gh"

    def _no_run(*_a, **_k):
        called["run"] += 1
        raise AssertionError("gh must not be invoked in dry-run")

    monkeypatch.setattr(dh_alerting.shutil, "which", _no_which)
    monkeypatch.setattr(dh_alerting.subprocess, "run", _no_run)

    payloads = [{"title": "[data-health] games missing/sparse seasons", "body": "x\ny"}]
    n = dh_alerting.open_issues(payloads, dry_run=True)
    out = capsys.readouterr().out
    assert n == 1
    assert "dry-run" in out and "games missing/sparse seasons" in out
    # Neither gh discovery nor gh invocation happened.
    assert called["which"] == 0 and called["run"] == 0


def test_open_issues_missing_gh_never_crashes(monkeypatch, capsys):
    """gh absent -> a printed warning, return 0, never an exception."""
    monkeypatch.setattr(dh_alerting.shutil, "which", lambda _n: None)
    payloads = [{"title": "[data-health] source feeds unhealthy", "body": "b"}]
    assert dh_alerting.open_issues(payloads, dry_run=False) == 0
    assert "gh not on PATH" in capsys.readouterr().out
