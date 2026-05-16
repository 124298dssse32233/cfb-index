"""Tests for Sprint v5-3 owner Interrupt 2 — per-surface CostMeter ceilings
+ 24-hour rolling aggregate auto-disable.

Surfaces under test (PER_RUN_CEILINGS_USD + DAILY_AGGREGATE_CEILINGS_USD):

  tier1.edition_cover      $5.00 per run / $10.00 per 24h
  tier1.daily_lead         $3.00          / $15.00
  tier1.daily_supporting   $3.00          / $15.00
  tier1.heisman_weekly     $2.00          / $5.00
  tier1.mailbag            $1.00          / $20.00
  tier1.reaction_story     $0.50          / $15.00
  tier1.storyline_chapter  $2.00          / $10.00
  tier1.chronicle_profiled $0.50          / $25.00

Coverage matrix (in this order):

  1. PER_RUN_CEILINGS_USD trips CostMeter at configured threshold (parametric)
  2. 24h aggregate ceiling trips when spend events sum past threshold
  3. should_auto_disable returns True only when over threshold
  4. get_active_pattern returns configured flag normally, degrade pattern when breached
  5. CLI status command output shape
  6. Re-enable clears the degrade marker
  7. Old events (>24h) don't count toward aggregate
  8. record_surface_spend zero-cost no-op (saves a write)
  9. Degrade row persists across get_active_pattern calls (no double-write)
 10. Pattern C surfaces all have both per-run + 24h ceilings configured
 11. Surface NOT in QUALITY_LOOP_FLAGS returns None from get_active_pattern
 12. loop_for_surface honors auto-disable when db is passed
 13. loop_for_surface ignores auto-disable when db is None (legacy contract)
 14. make_cost_meter_for_surface wires PER_RUN_CEILINGS_USD correctly
 15. prune_old_events housekeeping
 16. status_report shape for human + JSON output paths
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from cfb_rankings import circuit_state, config, quality_loop
from cfb_rankings.db import Database
from cfb_rankings.llm_runtime import CostCeilingExceeded, CostMeter
from cfb_rankings.migrations import apply_runtime_migrations
from cfb_rankings.quality_loop import LoopPattern

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA_PATH = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Fresh on-disk SQLite with all migrations applied. Per-test scope so
    spend events don't leak between tests."""
    db_path = tmp_path / "ceilings.db"
    database = Database(f"sqlite:///{db_path}")
    database.apply_sql_file(BASE_SCHEMA_PATH)
    apply_runtime_migrations(database)
    return database


@pytest.fixture(autouse=True)
def _reset_quality_loop_state():
    """Quality-loop in-memory state reset between tests (the weekly counters
    are orthogonal but resetting keeps the assertions deterministic)."""
    quality_loop.reset_circuit_state()
    yield
    quality_loop.reset_circuit_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_usage(*, in_toks: int, out_toks: int) -> dict[str, int]:
    """Build a usage dict shape CostMeter.record accepts."""
    return {
        "input_tokens": in_toks,
        "output_tokens": out_toks,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }


PER_RUN_SURFACES = [
    ("tier1.edition_cover",      5.00),
    ("tier1.daily_lead",         3.00),
    ("tier1.daily_supporting",   3.00),
    ("tier1.heisman_weekly",     2.00),
    ("tier1.mailbag",            1.00),
    ("tier1.reaction_story",     0.50),
    ("tier1.storyline_chapter",  2.00),
    ("tier1.chronicle_profiled", 0.50),
]


# ===========================================================================
# 1. PER_RUN_CEILINGS_USD trips CostMeter at configured threshold
# ===========================================================================

@pytest.mark.parametrize("surface,expected_ceiling", PER_RUN_SURFACES)
def test_per_run_ceiling_configured(surface: str, expected_ceiling: float):
    """Config maps every Pattern C surface to the spec'd USD ceiling."""
    assert config.PER_RUN_CEILINGS_USD[surface] == expected_ceiling


@pytest.mark.parametrize("surface,ceiling", PER_RUN_SURFACES)
def test_per_run_ceiling_trips_costmeter(surface: str, ceiling: float):
    """A CostMeter constructed for each surface raises CostCeilingExceeded
    when a single call burns past the configured per-run ceiling.

    We tune the call so usage*rate just clears the ceiling — this checks
    that the ceiling propagates from config through the helper into
    CostMeter.record().
    """
    meter = circuit_state.make_cost_meter_for_surface(surface)
    assert meter.ceiling_usd == ceiling

    # Pick an output-token count that produces (ceiling + 1c) of Opus output
    # cost: Opus output rate is $75/M. So `(ceiling + 0.01) / 75e-6` tokens.
    over_tokens = int((ceiling + 0.01) / (75.00 / 1_000_000)) + 1
    with pytest.raises(CostCeilingExceeded):
        meter.record(
            "claude-opus-4-7",
            _make_usage(in_toks=0, out_toks=over_tokens),
        )


def test_per_run_ceiling_does_not_trip_below_threshold():
    """CostMeter stays open until cumulative > ceiling. Exactly at the
    ceiling is allowed (spec: 'exceeds', strict greater-than)."""
    meter = circuit_state.make_cost_meter_for_surface("tier1.edition_cover")
    # $1 of output via Opus: 1.0 / (75e-6) tokens.
    tokens = int(1.0 / (75.00 / 1_000_000))
    cost = meter.record(
        "claude-opus-4-7",
        _make_usage(in_toks=0, out_toks=tokens),
    )
    assert cost == pytest.approx(1.0, rel=1e-4)
    assert meter.spent_usd < meter.ceiling_usd


# ===========================================================================
# 2. 24h aggregate ceiling trips when spend events sum past threshold
# ===========================================================================

def test_24h_aggregate_ceiling_trips_at_threshold(db: Database):
    """Three records of $4 each = $12 > $10 (edition_cover ceiling)."""
    surface = "tier1.edition_cover"
    for _ in range(3):
        circuit_state.record_surface_spend(db, surface, 4.00)
    assert circuit_state.get_24h_spend(db, surface) == pytest.approx(12.00)
    assert circuit_state.should_auto_disable(db, surface) is True


def test_24h_aggregate_below_ceiling_not_disabled(db: Database):
    """One $5 record on edition_cover ($10 ceiling) — under threshold."""
    surface = "tier1.edition_cover"
    circuit_state.record_surface_spend(db, surface, 5.00)
    assert circuit_state.get_24h_spend(db, surface) == pytest.approx(5.00)
    assert circuit_state.should_auto_disable(db, surface) is False


def test_24h_aggregate_exactly_at_ceiling_not_disabled(db: Database):
    """At exactly the ceiling, NOT over. Disable only on strict greater-than."""
    surface = "tier1.heisman_weekly"  # $5.00 ceiling
    circuit_state.record_surface_spend(db, surface, 5.00)
    assert circuit_state.should_auto_disable(db, surface) is False


# ===========================================================================
# 3. should_auto_disable bounds
# ===========================================================================

def test_should_auto_disable_unknown_surface(db: Database):
    """Surface not in DAILY_AGGREGATE_CEILINGS_USD → no auto-disable."""
    assert circuit_state.should_auto_disable(db, "tier99.unknown") is False


# ===========================================================================
# 4. get_active_pattern decision tree
# ===========================================================================

def test_get_active_pattern_returns_configured_when_clean(db: Database):
    """No spend, no degrade — get_active_pattern returns the configured
    Pattern C from QUALITY_LOOP_FLAGS."""
    surface = "tier1.edition_cover"
    pattern = circuit_state.get_active_pattern(db, surface)
    assert pattern is LoopPattern.C_CRITIC_REVISE


def test_get_active_pattern_returns_none_for_unconfigured(db: Database):
    """Surface not in QUALITY_LOOP_FLAGS → None (caller falls through to
    legacy path)."""
    pattern = circuit_state.get_active_pattern(db, "tier99.unknown")
    assert pattern is None


def test_get_active_pattern_returns_degrade_after_breach(db: Database):
    """24h aggregate over ceiling → degrade pattern is returned AND the
    degrade row is written so subsequent calls short-circuit."""
    surface = "tier1.edition_cover"
    # Breach 24h ceiling.
    circuit_state.record_surface_spend(db, surface, 11.00)
    pattern = circuit_state.get_active_pattern(db, surface)
    assert pattern is LoopPattern.A_SINGLE_SHOT  # configured degrade target

    # Marker row should be present now.
    row = db.query_one(
        "SELECT surface, degrade_pattern, reason FROM surface_degrade_state "
        "WHERE surface = :s", {"s": surface},
    )
    assert row is not None
    assert row["degrade_pattern"] == LoopPattern.A_SINGLE_SHOT.value
    assert row["reason"] == "daily_aggregate_ceiling"


def test_get_active_pattern_storyline_degrades_to_pattern_b(db: Database):
    """Storyline + Chronicle profiled degrade to Pattern B (single critic),
    not Pattern A — continuity is core to their value."""
    # storyline_chapter isn't in QUALITY_LOOP_FLAGS by default in v5-3,
    # so to exercise this path we monkeypatch the flag map.
    surface = "tier1.storyline_chapter"
    saved = dict(config.QUALITY_LOOP_FLAGS)
    config.QUALITY_LOOP_FLAGS[surface] = LoopPattern.C_CRITIC_REVISE
    try:
        circuit_state.record_surface_spend(db, surface, 11.00)
        pattern = circuit_state.get_active_pattern(db, surface)
        assert pattern is LoopPattern.B_SINGLE_CRITIC
    finally:
        config.QUALITY_LOOP_FLAGS.clear()
        config.QUALITY_LOOP_FLAGS.update(saved)


# ===========================================================================
# 5. Old events (>24h) don't count
# ===========================================================================

def test_old_events_excluded_from_24h_rollup(db: Database):
    """An event timestamped 25 hours ago is below the rolling window."""
    surface = "tier1.mailbag"
    long_ago = datetime.now(timezone.utc) - timedelta(hours=25)
    circuit_state.record_surface_spend(db, surface, 100.00, timestamp=long_ago)
    # Even though we just inserted $100, the 24h rollup should be $0.
    assert circuit_state.get_24h_spend(db, surface) == pytest.approx(0.0)
    assert circuit_state.should_auto_disable(db, surface) is False


def test_recent_event_inside_24h_window(db: Database):
    """An event 23 hours ago is inside the rolling window."""
    surface = "tier1.mailbag"
    recent = datetime.now(timezone.utc) - timedelta(hours=23)
    circuit_state.record_surface_spend(db, surface, 21.00, timestamp=recent)
    # Mailbag ceiling is $20.00.
    assert circuit_state.get_24h_spend(db, surface) == pytest.approx(21.00)
    assert circuit_state.should_auto_disable(db, surface) is True


# ===========================================================================
# 6. record_surface_spend zero-cost no-op
# ===========================================================================

def test_record_zero_cost_is_no_op(db: Database):
    """cost_usd <= 0 doesn't write a row (saves the write + matches
    CostMeter semantics for zero-token calls)."""
    surface = "tier1.daily_lead"
    circuit_state.record_surface_spend(db, surface, 0.0)
    circuit_state.record_surface_spend(db, surface, -1.0)
    rows = db.query_all(
        "SELECT id FROM surface_spend_events WHERE surface = :s",
        {"s": surface},
    )
    assert rows == []


# ===========================================================================
# 7. reset_surface_degrade clears the marker
# ===========================================================================

def test_reset_surface_degrade_clears_marker(db: Database):
    """Re-enable deletes the degrade row, and a clean get_active_pattern
    returns the configured Pattern C again."""
    surface = "tier1.edition_cover"
    circuit_state.record_surface_spend(db, surface, 11.00)
    # Trigger auto-disable so a marker is written.
    assert circuit_state.get_active_pattern(db, surface) is LoopPattern.A_SINGLE_SHOT

    cleared = circuit_state.reset_surface_degrade(db, surface)
    assert cleared is True

    # Marker is gone, but 24h spend is unchanged — so get_active_pattern
    # will RE-trip and rewrite the marker. That's intentional: human must
    # do the re-enable AND wait for 24h to pass / events to age out.
    # To test the "clean re-enable" path we also prune the events.
    db.execute("DELETE FROM surface_spend_events WHERE surface = :s",
               {"s": surface})
    pattern = circuit_state.get_active_pattern(db, surface)
    assert pattern is LoopPattern.C_CRITIC_REVISE


def test_reset_when_no_marker_returns_false(db: Database):
    """Idempotent: clearing a non-existent marker returns False, no error."""
    assert circuit_state.reset_surface_degrade(db, "tier1.edition_cover") is False


# ===========================================================================
# 8. loop_for_surface honors auto-disable when db is passed
# ===========================================================================

def test_loop_for_surface_with_db_uses_degraded_pattern(db: Database):
    """When db is passed and surface is auto-disabled, loop_for_surface
    returns the degraded pattern's function."""
    surface = "tier1.edition_cover"
    circuit_state.record_surface_spend(db, surface, 11.00)
    fn = quality_loop.loop_for_surface(surface, db=db)
    # Degrade target is Pattern A → loop_a_single_shot.
    assert fn is quality_loop.loop_a_single_shot


def test_loop_for_surface_without_db_ignores_auto_disable(db: Database):
    """db=None preserves legacy contract — no circuit_state lookup, no
    auto-disable, configured flag wins."""
    surface = "tier1.edition_cover"
    circuit_state.record_surface_spend(db, surface, 100.00)  # way over
    fn = quality_loop.loop_for_surface(surface)  # db not passed
    assert fn is quality_loop.loop_c_critic_revise


# ===========================================================================
# 9. make_cost_meter_for_surface wires PER_RUN_CEILINGS_USD correctly
# ===========================================================================

def test_make_cost_meter_default_ceiling_for_unknown_surface():
    """Unknown surface gets the default fallback ceiling, not a KeyError."""
    meter = circuit_state.make_cost_meter_for_surface(
        "tier99.unknown", default_usd=2.50,
    )
    assert meter.ceiling_usd == 2.50
    assert meter.label == "tier99.unknown"


# ===========================================================================
# 10. prune_old_events housekeeping
# ===========================================================================

def test_prune_old_events_deletes_aged_rows(db: Database):
    """Events older than max_age_hours are deleted; fresh ones are kept."""
    surface = "tier1.daily_lead"
    fresh = datetime.now(timezone.utc) - timedelta(hours=1)
    stale = datetime.now(timezone.utc) - timedelta(hours=200)
    circuit_state.record_surface_spend(db, surface, 0.50, timestamp=fresh)
    circuit_state.record_surface_spend(db, surface, 0.50, timestamp=stale)

    n_pruned = circuit_state.prune_old_events(db, max_age_hours=168)
    assert n_pruned == 1
    remaining = db.query_all(
        "SELECT id FROM surface_spend_events WHERE surface = :s",
        {"s": surface},
    )
    assert len(remaining) == 1


def test_prune_no_old_events_returns_zero(db: Database):
    """prune is a no-op on a clean table."""
    assert circuit_state.prune_old_events(db, max_age_hours=24) == 0


# ===========================================================================
# 11. Pattern C surfaces have both per-run + 24h ceilings configured
# ===========================================================================

def test_pattern_c_surfaces_have_complete_ceiling_config():
    """Every surface flipped to Pattern C in v5-2/v5-3 must have BOTH a
    per-run ceiling AND a 24h aggregate ceiling configured.

    Catches the foot-gun where a future flag flip forgets to add the
    matching ceiling rows.
    """
    pattern_c_surfaces = [
        k for k, v in config.QUALITY_LOOP_FLAGS.items()
        if v is LoopPattern.C_CRITIC_REVISE
        or v == "C_critic_revise"
    ]
    for surface in pattern_c_surfaces:
        assert surface in config.PER_RUN_CEILINGS_USD, (
            f"{surface} on Pattern C but no PER_RUN_CEILINGS_USD entry"
        )
        assert surface in config.DAILY_AGGREGATE_CEILINGS_USD, (
            f"{surface} on Pattern C but no DAILY_AGGREGATE_CEILINGS_USD entry"
        )
        assert surface in config.SURFACE_DEGRADE_PATTERN, (
            f"{surface} on Pattern C but no SURFACE_DEGRADE_PATTERN entry"
        )


# ===========================================================================
# 12. status_report output shape
# ===========================================================================

def test_status_report_includes_every_configured_surface(db: Database):
    """status_report rolls up every surface in
    QUALITY_LOOP_FLAGS ∪ DAILY_AGGREGATE_CEILINGS_USD."""
    rows = circuit_state.status_report(db)
    surfaces = {r["surface"] for r in rows}
    # Spot-check the v5-3 Pattern C surfaces.
    for expected in ("tier1.edition_cover", "tier1.daily_lead",
                     "tier1.daily_supporting", "tier1.heisman_weekly",
                     "tier1.mailbag", "tier1.reaction_story"):
        assert expected in surfaces, expected


def test_status_report_marks_degraded_surfaces(db: Database):
    """A surface with a degrade marker shows up as degraded=True in the
    status report, with the active_pattern showing the degraded value."""
    surface = "tier1.edition_cover"
    circuit_state.record_surface_spend(db, surface, 11.00)
    # Trigger marker.
    circuit_state.get_active_pattern(db, surface)

    rows = circuit_state.status_report(db)
    edition_row = next(r for r in rows if r["surface"] == surface)
    assert edition_row["degraded"] is True
    assert edition_row["active_pattern"] == LoopPattern.A_SINGLE_SHOT.value
    assert edition_row["configured_pattern"] == LoopPattern.C_CRITIC_REVISE.value
    assert edition_row["degrade_reason"] == "daily_aggregate_ceiling"
    assert edition_row["spend_24h_usd"] == pytest.approx(11.00)
    assert edition_row["ceiling_24h_usd"] == 10.00


def test_status_report_clean_surface_shows_configured_pattern(db: Database):
    """Clean surface: degraded=False, active_pattern == configured."""
    rows = circuit_state.status_report(db)
    surface = "tier1.mailbag"
    row = next(r for r in rows if r["surface"] == surface)
    assert row["degraded"] is False
    assert row["active_pattern"] == LoopPattern.C_CRITIC_REVISE.value
    assert row["spend_24h_usd"] == 0.0
    assert row["fraction"] == 0.0


# ===========================================================================
# 13. Persistence — degrade row survives across get_active_pattern calls
# ===========================================================================

def test_degrade_row_persists_across_calls(db: Database):
    """Once the marker is written, subsequent get_active_pattern calls
    read it directly without re-querying the 24h rollup."""
    surface = "tier1.heisman_weekly"
    circuit_state.record_surface_spend(db, surface, 6.00)  # > $5 ceiling

    pattern_first = circuit_state.get_active_pattern(db, surface)
    pattern_second = circuit_state.get_active_pattern(db, surface)

    assert pattern_first is LoopPattern.A_SINGLE_SHOT
    assert pattern_second is LoopPattern.A_SINGLE_SHOT

    # Only one row in surface_degrade_state — the upsert is idempotent.
    rows = db.query_all(
        "SELECT surface FROM surface_degrade_state WHERE surface = :s",
        {"s": surface},
    )
    assert len(rows) == 1


# ===========================================================================
# 14. Migration creates the tables
# ===========================================================================

def test_migration_creates_surface_spend_events_table(db: Database):
    row = db.query_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='surface_spend_events'"
    )
    assert row is not None
    cols = {r["name"] for r in db.query_all("PRAGMA table_info(surface_spend_events)")}
    for c in ("surface", "ts_utc", "cost_usd", "note"):
        assert c in cols


def test_migration_creates_surface_degrade_state_table(db: Database):
    row = db.query_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='surface_degrade_state'"
    )
    assert row is not None
    cols = {r["name"] for r in db.query_all("PRAGMA table_info(surface_degrade_state)")}
    for c in ("surface", "degrade_pattern", "breached_at_utc",
              "breached_spend_usd", "ceiling_usd", "reason"):
        assert c in cols


# ===========================================================================
# 15. CLI command output (smoke test — uses subprocess-free direct call)
# ===========================================================================

def test_cli_quality_loop_status_human_output(db: Database, capsys):
    """quality-loop-status human output prints a table with the surface
    column header. We invoke through main() with monkeypatched argv and
    a stub Database loader."""
    from unittest import mock
    from cfb_rankings import cli as cli_module

    with mock.patch("cfb_rankings.db.Database", return_value=db), \
         mock.patch.object(cli_module, "apply_runtime_migrations"),\
         mock.patch("sys.argv", ["cfb-rankings", "quality-loop-status"]):
        cli_module.main()

    out = capsys.readouterr().out
    assert "surface" in out and "active" in out
    # Spot-check a v5-3 Pattern C surface shows up.
    assert "tier1.edition_cover" in out


def test_cli_quality_loop_status_json_output(db: Database, capsys):
    """--json emits a parseable JSON array."""
    import json as _json
    from unittest import mock
    from cfb_rankings import cli as cli_module

    with mock.patch("cfb_rankings.db.Database", return_value=db), \
         mock.patch.object(cli_module, "apply_runtime_migrations"),\
         mock.patch("sys.argv", ["cfb-rankings", "quality-loop-status", "--json"]):
        cli_module.main()

    out = capsys.readouterr().out
    payload = _json.loads(out)
    assert isinstance(payload, list)
    assert any(r["surface"] == "tier1.edition_cover" for r in payload)


def test_cli_quality_loop_reenable_clears_marker(db: Database, capsys):
    """quality-loop-reenable deletes the marker; second invocation is a no-op."""
    from unittest import mock
    from cfb_rankings import cli as cli_module

    surface = "tier1.edition_cover"
    circuit_state.record_surface_spend(db, surface, 11.00)
    circuit_state.get_active_pattern(db, surface)  # writes marker

    with mock.patch("cfb_rankings.db.Database", return_value=db), \
         mock.patch.object(cli_module, "apply_runtime_migrations"),\
         mock.patch("sys.argv", ["cfb-rankings", "quality-loop-reenable", surface]):
        cli_module.main()
    out_first = capsys.readouterr().out
    assert "cleared" in out_first.lower()

    # Re-run — marker already gone.
    with mock.patch("cfb_rankings.db.Database", return_value=db), \
         mock.patch.object(cli_module, "apply_runtime_migrations"),\
         mock.patch("sys.argv", ["cfb-rankings", "quality-loop-reenable", surface]):
        cli_module.main()
    out_second = capsys.readouterr().out
    assert "no degrade marker" in out_second.lower()


# ===========================================================================
# 16. Defensive — circuit_state failures must not crash loop_for_surface
# ===========================================================================

def test_loop_for_surface_tolerates_circuit_state_failure(db: Database):
    """If get_active_pattern raises (e.g. partial migration), loop_for_surface
    falls back to the QUALITY_LOOP_FLAGS lookup."""
    from unittest import mock

    surface = "tier1.edition_cover"
    with mock.patch(
        "cfb_rankings.circuit_state.get_active_pattern",
        side_effect=RuntimeError("simulated transient sqlite failure"),
    ):
        fn = quality_loop.loop_for_surface(surface, db=db)
    # Falls back to QUALITY_LOOP_FLAGS → loop_c_critic_revise.
    assert fn is quality_loop.loop_c_critic_revise
