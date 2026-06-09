"""Regression tests for Milestone A review fixes.

Covers two defects found in the multi-LLM review of the team-preview truth
layer (docs/specs/team-preview-implementation-plan-2026-05-26.md):

  * persistence.upsert_bowl_ledger_rows bumped updated_at_utc on EVERY row of
    team_bowl_record_ledger (no WHERE clause), rewriting the timestamp of
    untouched teams on every import.
  * readiness collapsed multi-source ledger rows with an arbitrary {slug: row}
    dict, which could let a 'conflict'/'missing' row shadow a 'verified' one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.team_preview.persistence import upsert_bowl_ledger_rows
from cfb_rankings.team_preview.readiness import best_ledger_rows

ROOT = Path(__file__).resolve().parents[1]
_LEDGER_MIGRATION = ROOT / "migrations" / "20260602_03_team_preview_bowl_ledger.sql"

_SENTINEL = "2000-01-01 00:00:00"


@pytest.fixture
def ledger_db(tmp_path: Path) -> Database:
    d = Database(f"sqlite:///{tmp_path / 'bowl.db'}")
    # team_bowl_record_ledger has an FK to teams(team_id); create a minimal
    # parent table so FK enforcement is satisfied (rows here use NULL team_id).
    d.execute("create table teams (team_id integer primary key, slug text unique)")
    d.apply_sql_file(_LEDGER_MIGRATION)
    return d


def _row(slug: str, source: str = "seed", **kw: object) -> dict[str, object]:
    base = {
        "slug": slug, "wins": 1, "losses": 0, "ties": 0,
        "source_name": source, "verification_status": "single_source",
    }
    base.update(kw)
    return base


# --- persistence: timestamp scoping ----------------------------------------

def test_bowl_import_does_not_touch_other_rows_timestamp(ledger_db: Database) -> None:
    upsert_bowl_ledger_rows(ledger_db, [_row("akron")])
    # Force a known, stale timestamp on the untouched team.
    ledger_db.execute(
        "update team_bowl_record_ledger set updated_at_utc = :ts where slug = 'akron'",
        {"ts": _SENTINEL},
    )

    # Importing a DIFFERENT slug must leave akron's timestamp untouched.
    upsert_bowl_ledger_rows(ledger_db, [_row("alabama", wins=47, losses=26, ties=3)])

    akron = ledger_db.query_one(
        "select updated_at_utc from team_bowl_record_ledger where slug = 'akron'")
    assert akron["updated_at_utc"] == _SENTINEL, \
        "import of another team rewrote akron's updated_at_utc"


def test_bowl_import_bumps_only_touched_row(ledger_db: Database) -> None:
    upsert_bowl_ledger_rows(ledger_db, [_row("akron"), _row("alabama")])
    ledger_db.execute(
        "update team_bowl_record_ledger set updated_at_utc = :ts", {"ts": _SENTINEL})

    upsert_bowl_ledger_rows(ledger_db, [_row("alabama", wins=48)])

    rows = {
        r["slug"]: r["updated_at_utc"]
        for r in ledger_db.query_all(
            "select slug, updated_at_utc from team_bowl_record_ledger")
    }
    assert rows["akron"] == _SENTINEL              # untouched
    assert rows["alabama"] != _SENTINEL            # re-imported -> refreshed


# --- readiness: best-row selection -----------------------------------------

def test_best_ledger_rows_prefers_verified_over_conflict() -> None:
    rows = [
        {"slug": "alabama", "verification_status": "conflict", "source_name": "scrape"},
        {"slug": "alabama", "verification_status": "verified", "source_name": "guide"},
        {"slug": "alabama", "verification_status": "missing", "source_name": "stub"},
    ]
    best = best_ledger_rows(rows)
    assert best["alabama"]["verification_status"] == "verified"


def test_best_ledger_rows_order_independent() -> None:
    verified = {"slug": "auburn", "verification_status": "verified", "source_name": "a"}
    single = {"slug": "auburn", "verification_status": "single_source", "source_name": "b"}
    # Whichever order they arrive in, verified wins.
    assert best_ledger_rows([verified, single])["auburn"]["source_name"] == "a"
    assert best_ledger_rows([single, verified])["auburn"]["source_name"] == "a"


def test_best_ledger_rows_keeps_one_per_slug() -> None:
    rows = [
        {"slug": "akron", "verification_status": "single_source", "source_name": "x"},
        {"slug": "alabama", "verification_status": "verified", "source_name": "y"},
    ]
    best = best_ledger_rows(rows)
    assert set(best) == {"akron", "alabama"}
