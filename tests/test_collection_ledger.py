"""Unit tests for the stale-first rotation ledger (cadence architecture)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.ingest.collection_ledger import mark_fail, mark_ok, select_batch


@pytest.fixture()
def db():
    tmp = Path(tempfile.mkdtemp()) / "ledger.db"
    d = Database(str(tmp))
    d.execute(
        """
        create table collection_ledger (
          source text not null, entity text not null,
          last_ok_at text, last_attempt_at text, next_due_at text, cursor text,
          consecutive_failures integer not null default 0, cooldown_until text,
          primary key (source, entity)
        )
        """
    )
    return d


def test_never_collected_first_then_stalest(db):
    NOW = "2026-06-10T12:00:00Z"
    # team A collected (due far future), B collected (due near past), C never seen
    mark_ok(db, "gdelt", "A", NOW, interval_hours=72)          # due ~+72h
    mark_ok(db, "gdelt", "B", "2026-06-01T00:00:00Z", interval_hours=1)  # due in the past
    batch = select_batch(db, "gdelt", ["A", "B", "C"], budget=3, now_iso=NOW)
    assert batch[0] == "C", f"never-collected should be first: {batch}"
    assert batch.index("B") < batch.index("A"), f"stalest-due before fresher: {batch}"


def test_budget_limits_slice(db):
    batch = select_batch(db, "gdelt", [str(i) for i in range(100)], budget=46, now_iso="2026-06-10T12:00:00Z")
    assert len(batch) == 46


def test_cooldown_excludes_entity(db):
    NOW = "2026-06-10T12:00:00Z"
    mark_fail(db, "gdelt", "X", NOW)  # sets cooldown_until in the future
    batch = select_batch(db, "gdelt", ["X", "Y"], budget=5, now_iso=NOW)
    assert "X" not in batch and "Y" in batch, f"cooling-down entity excluded: {batch}"


def test_mark_ok_clears_failures_and_cooldown(db):
    NOW = "2026-06-10T12:00:00Z"
    mark_fail(db, "gdelt", "Z", NOW)
    mark_ok(db, "gdelt", "Z", NOW, interval_hours=72)
    row = db.query_one("select consecutive_failures, cooldown_until, next_due_at from collection_ledger where source='gdelt' and entity='Z'")
    assert row["consecutive_failures"] == 0
    assert row["cooldown_until"] is None
    assert row["next_due_at"] is not None
    # and it's now eligible again
    assert "Z" in select_batch(db, "gdelt", ["Z"], budget=5, now_iso=NOW)


def test_escalating_cooldown(db):
    NOW = "2026-06-10T12:00:00Z"
    mark_fail(db, "gdelt", "E", NOW)
    c1 = db.query_one("select cooldown_until, consecutive_failures from collection_ledger where entity='E'")
    mark_fail(db, "gdelt", "E", NOW)
    c2 = db.query_one("select cooldown_until, consecutive_failures from collection_ledger where entity='E'")
    assert c2["consecutive_failures"] == 2
    assert str(c2["cooldown_until"]) > str(c1["cooldown_until"]), "cooldown should escalate"
