"""Tests for scripts/verify_module_coverage.py — the baseline-aware coverage
gate for computed module tables.

Exercises the regression logic the live first-run can't: established module goes
dark -> flagged; un-established module empty -> NOT flagged (no false alarm on a
feature that never launched, e.g. Atlas/KWIC on 2026-06-11); healthy module ->
recorded; regressed value -> NOT written back (baseline not poisoned).
"""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "verify_module_coverage.py"
_spec = importlib.util.spec_from_file_location("verify_module_coverage", _SCRIPT)
mc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mc)

_TEST_SQL = ("SELECT COUNT(DISTINCT team_id) FROM t "
             "WHERE season_year=(SELECT MAX(season_year) FROM t)")


def _conn_with(n_teams: int) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (team_id INTEGER, season_year INTEGER)")
    conn.executemany("INSERT INTO t VALUES (?, 2025)", [(i,) for i in range(n_teams)])
    conn.commit()
    return conn


def _single_signal(monkeypatch):
    monkeypatch.setattr(mc, "SIGNALS", [("test_mod", "test module", _TEST_SQL)])


def _hist(counts):
    return {"test_mod": [{"date": f"2026-06-{i+1:02d}", "count": c} for i, c in enumerate(counts)]}


def test_established_module_going_dark_is_flagged(monkeypatch):
    _single_signal(monkeypatch)
    history = _hist([100, 98, 102, 101, 99])  # 5 established days
    conn = _conn_with(0)                        # module dark today
    findings, stats = mc.evaluate(conn, history, "2026-06-11")
    assert stats["degraded"] == 1
    assert findings[0]["key"] == "test_mod"
    assert findings[0]["today"] == 0
    # Don't-poison: the 0 must NOT be appended; baseline stays the good run.
    assert all(e["count"] > 0 for e in history["test_mod"])
    assert len(history["test_mod"]) == 5


def test_unestablished_module_empty_is_not_flagged(monkeypatch):
    _single_signal(monkeypatch)
    history = _hist([100, 100])  # only 2 prior builds < MIN_ACTIVE_BUILDS
    conn = _conn_with(0)
    findings, stats = mc.evaluate(conn, history, "2026-06-11")
    assert stats["degraded"] == 0
    assert stats["unestablished"] == 1
    # Recorded for future baseline-building.
    assert history["test_mod"][-1] == {"date": "2026-06-11", "count": 0}


def test_healthy_module_is_recorded_not_flagged(monkeypatch):
    _single_signal(monkeypatch)
    history = _hist([100, 98, 102, 101, 99])
    conn = _conn_with(90)  # within tolerance
    findings, stats = mc.evaluate(conn, history, "2026-06-11")
    assert stats["degraded"] == 0
    assert stats["judged"] == 1
    assert history["test_mod"][-1] == {"date": "2026-06-11", "count": 90}
    assert len(history["test_mod"]) == 6


def test_partial_drop_above_floor_is_ok(monkeypatch):
    _single_signal(monkeypatch)
    history = _hist([100, 100, 100, 100, 100])
    conn = _conn_with(30)  # 30% of median 100 -> above 25% floor
    findings, stats = mc.evaluate(conn, history, "2026-06-11")
    assert stats["degraded"] == 0


def test_drop_below_floor_is_flagged(monkeypatch):
    _single_signal(monkeypatch)
    history = _hist([100, 100, 100, 100, 100])
    conn = _conn_with(20)  # 20% of median -> below 25% floor
    findings, stats = mc.evaluate(conn, history, "2026-06-11")
    assert stats["degraded"] == 1


def test_missing_table_does_not_crash(monkeypatch):
    # Schema drift (table renamed/dropped) -> query errors -> signal skipped with
    # a warning, gate stays up (returns no finding, no crash).
    monkeypatch.setattr(mc, "SIGNALS",
                        [("gone", "missing table", "SELECT COUNT(*) FROM does_not_exist")])
    conn = sqlite3.connect(":memory:")
    findings, stats = mc.evaluate(conn, {}, "2026-06-11")
    assert findings == []
    assert stats["judged"] == 0
