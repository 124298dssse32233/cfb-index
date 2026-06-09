"""Tests for ``sync_cfbd_team_locations`` (teams.state backfill).

Teams are created from CFBD *game* payloads, which carry no location, so
``teams.state`` ships empty site-wide — silently breaking the Recruiting
Footprint home-state highlight and blocking every geography chart. This sync
hits the location-bearing ``/teams`` endpoint and fills the blanks.

DB-free of the real cfb_rankings.db: a fresh temp DB + a fake CFBD client whose
``get_teams`` returns a hand-built payload, so it runs in CI without a key.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.ingest.cfbd import sync_cfbd_team_locations
from cfb_rankings.migrations import apply_runtime_migrations
from cfb_rankings.storage import Repository, TeamIdentity

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"


class _FakeClient:
    """Minimal stand-in exposing only ``get_teams``."""

    def __init__(self, payload: list[dict]) -> None:
        self._payload = payload
        self.calls: list[dict] = []

    def get_teams(self, year=None, conference=None, classification=None):
        self.calls.append({"year": year, "classification": classification})
        return self._payload


@pytest.fixture
def repo_db(tmp_path: Path) -> tuple[Repository, Database]:
    db = Database(f"sqlite:///{tmp_path / 'loc.db'}")
    db.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(db)
    repo = Repository(db)
    repo.seed_levels()
    return repo, db


def _state_of(db: Database, team_id: int) -> str | None:
    row = db.query_one("select state, city from teams where team_id = :t", {"t": team_id})
    return row["state"] if row else None


def test_backfills_state_matched_by_source_id(repo_db) -> None:
    repo, db = repo_db
    # Team created the way game ingest creates it: cfbd source id, no location.
    team_id = repo.get_or_create_team(
        "cfbd", "333",
        TeamIdentity(canonical_name="Alabama", level_code="FBS", conference_name="SEC"),
    )
    assert _state_of(db, team_id) is None

    client = _FakeClient([
        {"id": 333, "school": "Alabama", "classification": "fbs",
         "conference": "SEC", "location": {"city": "Tuscaloosa", "state": "AL"}},
    ])
    n = sync_cfbd_team_locations(repo, db, client, season=2025)

    assert n == 1
    assert _state_of(db, team_id) == "AL"
    row = db.query_one("select city from teams where team_id = :t", {"t": team_id})
    assert row["city"] == "Tuscaloosa"


def test_falls_back_to_name_match_when_source_id_unknown(repo_db) -> None:
    repo, db = repo_db
    # Created under a *different* source id, so /teams id 999 won't resolve via
    # team_source_ids — name match must catch it.
    team_id = repo.get_or_create_team(
        "espn", "abc",
        TeamIdentity(canonical_name="Oregon", level_code="FBS", conference_name="Big Ten"),
    )

    client = _FakeClient([
        {"id": 999, "school": "Oregon", "classification": "fbs",
         "conference": "Big Ten", "location": {"city": "Eugene", "state": "OR"}},
    ])
    n = sync_cfbd_team_locations(repo, db, client, season=2025)

    assert n == 1
    assert _state_of(db, team_id) == "OR"


def test_unmatched_team_is_skipped_not_fatal(repo_db) -> None:
    repo, db = repo_db
    client = _FakeClient([
        {"id": 7, "school": "Nonexistent State", "classification": "fbs",
         "location": {"city": "Nowhere", "state": "ZZ"}},
    ])
    # No team in the DB to match — returns 0, raises nothing.
    assert sync_cfbd_team_locations(repo, db, client, season=2025) == 0


def test_empty_location_payload_is_skipped(repo_db) -> None:
    repo, db = repo_db
    team_id = repo.get_or_create_team(
        "cfbd", "55",
        TeamIdentity(canonical_name="Georgia", level_code="FBS"),
    )
    client = _FakeClient([
        {"id": 55, "school": "Georgia", "location": {}},
        {"id": 55, "school": "Georgia"},  # no location key at all
    ])
    assert sync_cfbd_team_locations(repo, db, client, season=2025) == 0
    assert _state_of(db, team_id) is None


def test_does_not_clobber_existing_state_with_blank(repo_db) -> None:
    repo, db = repo_db
    team_id = repo.get_or_create_team(
        "cfbd", "1",
        TeamIdentity(canonical_name="Texas", level_code="FBS", state="TX"),
    )
    assert _state_of(db, team_id) == "TX"
    # Payload carries a city but a blank state — must not wipe the existing TX.
    client = _FakeClient([
        {"id": 1, "school": "Texas", "location": {"city": "Austin", "state": ""}},
    ])
    n = sync_cfbd_team_locations(repo, db, client, season=2025)
    assert n == 1  # city did update, so the row counts
    assert _state_of(db, team_id) == "TX"
    row = db.query_one("select city from teams where team_id = :t", {"t": team_id})
    assert row["city"] == "Austin"


def test_passes_classification_through_to_client(repo_db) -> None:
    repo, db = repo_db
    client = _FakeClient([])
    sync_cfbd_team_locations(repo, db, client, season=2024, classification="fbs")
    assert client.calls == [{"year": 2024, "classification": "fbs"}]
