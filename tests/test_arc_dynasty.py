"""Tests for the D-022 dynasty_status_change arc detector.

The detector reuses the Dynasty Heatmap signal: a trailing-window average of a
team's within-season power-rating percentile. A team "enters" dynasty status
when that trailing average crosses the 85th-percentile threshold upward, and
"exits" when it crosses downward. The detector degrades to a no-op (with a
reason) when the DB lacks contiguous seasons; here we seed enough seasons to
force one clean enter and one clean exit crossing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.chronicle.arc_populator import populate_season_arcs
from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"

# alpha enters, bravo exits; both are in the FBS allowlist.
_FBS = frozenset({"alpha", "bravo"})
_SEASONS = (2023, 2024, 2025, 2026)
_FILLERS = list(range(11, 19))  # team_ids 11..18, ratings 10..17 (stable mid-pack)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{tmp_path / 'dynasty.db'}")
    database.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(database)
    _seed(database)
    return database


def _seed(db: Database) -> None:
    db.upsert_many(
        "levels",
        [{"level_code": "FBS", "level_name": "FBS", "sort_order": 1}],
        conflict_columns=["level_code"],
    )
    db.upsert_many(
        "seasons",
        [{"season_year": y} for y in _SEASONS],
        conflict_columns=["season_year"],
    )
    db.upsert_many(
        "model_runs",
        [{"model_run_id": y, "model_name": "test", "model_version": "v1",
          "season_year": y, "data_cutoff_utc": f"{y}-05-28T00:00:00Z"} for y in _SEASONS],
        conflict_columns=["model_run_id"],
    )
    teams = [
        {"team_id": 1, "canonical_name": "Alpha", "slug": "alpha", "level_code": "FBS"},
        {"team_id": 2, "canonical_name": "Bravo", "slug": "bravo", "level_code": "FBS"},
    ]
    for i, tid in enumerate(_FILLERS):
        teams.append({"team_id": tid, "canonical_name": f"Filler{tid}",
                      "slug": f"f{tid}", "level_code": "FBS"})
    db.upsert_many("teams", teams, conflict_columns=["team_id"])

    # Within-year ratings → within-year percentiles (10-team cohort each year):
    #   alpha: 2023 bottom, 2024-2026 top  → trailing avg crosses 85 UPWARD
    #   bravo: 2023-2025 top, 2026 bottom  → trailing avg crosses 85 DOWNWARD
    alpha_by_year = {2023: 1.0, 2024: 100.0, 2025: 100.0, 2026: 100.0}
    bravo_by_year = {2023: 99.0, 2024: 99.0, 2025: 99.0, 2026: 1.0}
    powers = []
    pid = 0
    for year in _SEASONS:
        pid += 1
        powers.append(_power(pid, year, 1, year, alpha_by_year[year]))
        pid += 1
        powers.append(_power(pid, year, 2, year, bravo_by_year[year]))
        for j, tid in enumerate(_FILLERS):
            pid += 1
            powers.append(_power(pid, year, tid, year, 10.0 + j))
    db.upsert_many("power_ratings_weekly", powers,
                   conflict_columns=["power_rating_weekly_id"])


def _power(pid: int, run_id: int, team_id: int, season: int, rating: float) -> dict:
    return {
        "power_rating_weekly_id": pid, "model_run_id": run_id, "team_id": team_id,
        "season_year": season, "week": 15, "power_rating": rating,
        "offense_rating": 0.0, "defense_rating": 0.0,
        "special_teams_rating": 0.0, "tempo_rating": 0.0,
    }


def _dynasty_arcs(db: Database):
    return db.query_all(
        """
        select t.slug, a.arc_id, a.tension_score
        from season_narrative_arc a join teams t on t.team_id = a.team_id
        where a.frame = 'dynasty_status_change' and a.season_year = 2026
        order by t.slug
        """
    )


def test_dynasty_enter_and_exit_crossings_fire(db: Database) -> None:
    report = populate_season_arcs(db, 2026, fbs_slugs=_FBS)
    assert report["per_frame"]["dynasty_status_change"] == 2

    arcs = _dynasty_arcs(db)
    by_slug = {r["slug"]: r for r in arcs}
    assert set(by_slug) == {"alpha", "bravo"}

    # Discriminator is embedded in the arc_id ({slug}-{season}-{frame}-{enter|exit}).
    assert by_slug["alpha"]["arc_id"].endswith("-enter")
    assert by_slug["bravo"]["arc_id"].endswith("-exit")

    # Both are large, decisive crossings → high tension (clamped to the 1.0 ceiling).
    assert by_slug["alpha"]["tension_score"] == pytest.approx(1.0)
    assert by_slug["bravo"]["tension_score"] == pytest.approx(1.0)


def test_dynasty_no_op_when_no_power_data(tmp_path: Path) -> None:
    """With no power_ratings_weekly rows the detector must degrade to a no-op
    with a reason, not raise — the local/offseason path."""
    database = Database(f"sqlite:///{tmp_path / 'empty.db'}")
    database.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(database)
    database.upsert_many("levels", [{"level_code": "FBS", "level_name": "FBS", "sort_order": 1}],
                         conflict_columns=["level_code"])
    database.upsert_many("seasons", [{"season_year": y} for y in _SEASONS],
                         conflict_columns=["season_year"])
    database.upsert_many("teams",
                         [{"team_id": 1, "canonical_name": "Alpha", "slug": "alpha", "level_code": "FBS"}],
                         conflict_columns=["team_id"])

    report = populate_season_arcs(database, 2026, fbs_slugs=_FBS)
    assert report["per_frame"]["dynasty_status_change"] == 0
    assert report["empty_reasons"]["dynasty_status_change"]


def test_dynasty_arc_is_idempotent(db: Database) -> None:
    first = populate_season_arcs(db, 2026, fbs_slugs=_FBS)
    second = populate_season_arcs(db, 2026, fbs_slugs=_FBS)
    assert first["per_frame"]["dynasty_status_change"] == 2
    assert second["per_frame"]["dynasty_status_change"] == 2
    rows = _dynasty_arcs(db)
    assert len(rows) == 2  # no duplicate arc_ids on rerun
