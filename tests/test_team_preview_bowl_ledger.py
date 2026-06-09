"""Bowl-record label correctness — the site must never lie about scope.

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §1.5, §2.4, §6, §10.

The cardinal rule under test: only a ledger row whose verification_status is
'verified' or 'single_source' may be labelled an ALL-TIME bowl record. Anything
else falls back to a clearly-scoped recent-era record or is suppressed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.team_preview.bowl_ledger import (
    import_bowl_ledger,
    load_bowl_ledger_seed,
    resolve_bowl_record_display,
)

ROOT = Path(__file__).resolve().parents[1]
_LEDGER_MIGRATION = ROOT / "migrations" / "20260602_03_team_preview_bowl_ledger.sql"


# --- label resolution -------------------------------------------------------

@pytest.mark.parametrize("status", ["verified", "single_source"])
def test_trustworthy_ledger_yields_all_time_label(status: str) -> None:
    row = {"wins": 47, "losses": 26, "ties": 3,
           "verification_status": status, "source_name": "media-guide"}
    d = resolve_bowl_record_display(row)
    assert d.is_all_time is True
    assert d.scope == "all_time"
    assert "All-time" in d.label
    assert d.record == "47-26-3"
    assert d.suppress is False


@pytest.mark.parametrize("status", ["conflict", "missing"])
def test_untrustworthy_status_is_never_all_time(status: str) -> None:
    row = {"wins": 47, "losses": 26, "ties": 0, "verification_status": status,
           "source_name": "scrape"}
    # Even with a recent-era fallback available, scope must not be all_time.
    d = resolve_bowl_record_display(
        row, recent_postseason_wins=3, recent_postseason_losses=2)
    assert d.is_all_time is False
    assert d.scope == "recent_era"
    assert "All-time" not in d.label


def test_no_ledger_falls_back_to_recent_era() -> None:
    d = resolve_bowl_record_display(
        None, recent_postseason_wins=3, recent_postseason_losses=2)
    assert d.is_all_time is False
    assert d.scope == "recent_era"
    assert "Recent postseason" in d.label
    assert d.record == "3-2"
    assert d.suppress is False


def test_nothing_available_is_suppressed() -> None:
    d = resolve_bowl_record_display(None)
    assert d.scope == "unavailable"
    assert d.is_all_time is False
    assert d.suppress is True


def test_all_time_record_formats_ties_only_when_present() -> None:
    with_ties = resolve_bowl_record_display(
        {"wins": 10, "losses": 5, "ties": 2, "verification_status": "verified"})
    no_ties = resolve_bowl_record_display(
        {"wins": 10, "losses": 5, "ties": 0, "verification_status": "verified"})
    assert with_ties.record == "10-5-2"
    assert no_ties.record == "10-5"


def test_recent_era_label_is_scoped() -> None:
    d = resolve_bowl_record_display(
        None, recent_postseason_wins=1, recent_postseason_losses=4,
        recent_era_label="2018-2024")
    assert "2018-2024" in d.label
    assert d.scope == "recent_era"


# --- seed loading + import --------------------------------------------------

@pytest.fixture
def ledger_db(tmp_path: Path) -> Database:
    d = Database(f"sqlite:///{tmp_path / 'bowl.db'}")
    d.apply_sql_file(_LEDGER_MIGRATION)
    d.execute(
        "create table teams (team_id integer primary key, slug text unique, "
        "canonical_name text)"
    )
    d.execute("insert into teams (team_id, slug, canonical_name) values "
              "(1, 'alabama', 'Alabama'), (2, 'akron', 'Akron')")
    return d


def _write_csv(tmp_path: Path) -> Path:
    p = tmp_path / "bowls.csv"
    p.write_text(
        "slug,wins,losses,ties,appearances,verification_status,source_name,notes\n"
        "alabama,47,26,3,76,verified,sports-reference,blue blood\n"
        "ghost-team,1,0,0,1,single_source,scrape,not in teams\n",
        encoding="utf-8",
    )
    return p


def test_load_seed_csv_normalises_rows(tmp_path: Path) -> None:
    rows = load_bowl_ledger_seed(_write_csv(tmp_path))
    assert len(rows) == 2
    bama = next(r for r in rows if r["slug"] == "alabama")
    assert bama["wins"] == 47 and bama["losses"] == 26 and bama["ties"] == 3
    assert bama["verification_status"] == "verified"
    assert "blue blood" in bama["notes_json"]


def test_import_matches_team_ids_and_keeps_unmatched(ledger_db: Database, tmp_path: Path) -> None:
    result = import_bowl_ledger(ledger_db, _write_csv(tmp_path), as_of="2026-05-25")
    assert result["rows"] == 2
    assert result["matched_team_id"] == 1   # alabama matched, ghost-team not
    assert result["unmatched"] == 1

    stored = ledger_db.query_one(
        "select team_id, wins, losses, ties, verification_status, source_retrieved_at "
        "from team_bowl_record_ledger where slug = 'alabama'")
    assert stored["team_id"] == 1
    assert stored["verification_status"] == "verified"
    assert stored["source_retrieved_at"] == "2026-05-25"

    # The imported row drives an honest all-time label downstream.
    display = resolve_bowl_record_display(stored)
    assert display.is_all_time is True
    assert display.record == "47-26-3"


def test_import_is_idempotent(ledger_db: Database, tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path)
    import_bowl_ledger(ledger_db, csv_path, as_of="2026-05-25")
    import_bowl_ledger(ledger_db, csv_path, as_of="2026-05-25")
    count = ledger_db.query_one(
        "select count(*) c from team_bowl_record_ledger where slug = 'alabama'")
    assert count["c"] == 1
