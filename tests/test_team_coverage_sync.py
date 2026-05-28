"""Drift-guard for team_coverage (DECISIONS.md#D-016).

team_coverage is a derived read surface re-synced from the authoring
constants on every build. This test pins the invariant: after
``sync_team_coverage`` the table is a byte-exact mirror of its authoring
sources. If someone edits a constant and the table diverges, this fails
loudly — and because the build calls the same sync, a green test means the
shipped table matches the constants.

Uses a fresh temp DB (NOT the gitignored cfb_rankings.db) so it runs in CI.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.coverage import (
    _slugify,
    archetype_for,
    coverage_tiers,
    slugs_in_tier,
    sync_team_coverage,
)
from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"


@pytest.fixture
def migrated_db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{tmp_path / 'coverage.db'}")
    db.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(db)
    return db


def _expected_priority_slugs() -> set[str]:
    from cfb_rankings.coverage import _load_priority_teams_yaml
    return {
        _slugify(t.get("team_name") or "")
        for t in _load_priority_teams_yaml()
        if (t.get("team_name") or "").strip()
    }


def test_each_tier_mirrors_its_authoring_source(migrated_db: Database) -> None:
    from cfb_rankings.ingest.archetypes import (
        BLUEBLOOD_PROGRAMS,
        STRUCTURAL_PRIMARIES,
    )
    from cfb_rankings.team_pages.profile_loader import PROFILED_SLUGS
    from cfb_rankings.team_pages.pulse_state import (
        TOP_ENTITIES_FULL,
        TOP_ENTITIES_PARTIAL,
    )

    sync_team_coverage(migrated_db)

    assert slugs_in_tier(migrated_db, "authored") == set(PROFILED_SLUGS)
    assert slugs_in_tier(migrated_db, "pulse_full") == set(TOP_ENTITIES_FULL)
    assert slugs_in_tier(migrated_db, "pulse_partial") == set(TOP_ENTITIES_PARTIAL)
    assert slugs_in_tier(migrated_db, "blueblood_pedigree") == set(BLUEBLOOD_PROGRAMS)
    assert slugs_in_tier(migrated_db, "structural_identity") == set(STRUCTURAL_PRIMARIES)
    assert slugs_in_tier(migrated_db, "priority_intelligence") == _expected_priority_slugs()


def test_structural_archetype_values_match(migrated_db: Database) -> None:
    from cfb_rankings.ingest.archetypes import STRUCTURAL_PRIMARIES

    sync_team_coverage(migrated_db)
    for slug, archetype_slug in STRUCTURAL_PRIMARIES.items():
        assert archetype_for(migrated_db, slug) == archetype_slug


def test_sync_is_idempotent(migrated_db: Database) -> None:
    first = sync_team_coverage(migrated_db)
    second = sync_team_coverage(migrated_db)
    assert first == second
    total = migrated_db.query_one("select count(*) as n from team_coverage")["n"]
    assert total == sum(first.values())


def test_sync_prunes_stale_rows(migrated_db: Database) -> None:
    """A slug no longer in any authoring source must be removed on re-sync."""
    sync_team_coverage(migrated_db)
    migrated_db.execute(
        "insert into team_coverage (team_slug, tier, source_origin) "
        "values ('ghost-team', 'authored', 'profiled_yaml')"
    )
    assert "ghost-team" in slugs_in_tier(migrated_db, "authored")

    sync_team_coverage(migrated_db)  # full refresh
    assert "ghost-team" not in slugs_in_tier(migrated_db, "authored")
    assert coverage_tiers(migrated_db, "ghost-team") == set()


def test_top_program_spans_multiple_tiers(migrated_db: Database) -> None:
    """Alabama is authored + pulse_full + blueblood — proves multi-tier rows."""
    sync_team_coverage(migrated_db)
    tiers = coverage_tiers(migrated_db, "alabama")
    assert {"authored", "pulse_full", "blueblood_pedigree"} <= tiers
