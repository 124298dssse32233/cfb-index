"""Regression test for the fanbase-archetype percentile fix (2026-05-28).

Bug: ``classify_all_fanbases`` ranked every team against the full multi-level
power-ratings pool (FBS + FCS + DII + DIII, ~707 teams). FBS teams cluster at
the top of that pool, so nearly every FBS team landed at percentile >=0.80 and
the classifier collapsed onto the ``quiet-professional`` fallback. The fix ranks
each team only against peers at its own ``level_code``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.ingest.archetypes import (
    _percentiles_within_level,
    classify_all_fanbases,
    classify_team,
)
from cfb_rankings.migrations import apply_runtime_migrations

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"


def test_percentiles_ranked_within_level_not_cross_level() -> None:
    # 4 FBS teams + 6 FCS teams. FCS power ratings are all *higher* numerically
    # here to make the cross-level bug obvious: under the old cross-level rank,
    # the FBS teams would sit at the bottom; under per-level rank each cohort
    # spans the full 0..1 range independently.
    rows = [
        {"team_id": 1, "power_rating": 10.0, "level_code": "FBS"},
        {"team_id": 2, "power_rating": 20.0, "level_code": "FBS"},
        {"team_id": 3, "power_rating": 30.0, "level_code": "FBS"},
        {"team_id": 4, "power_rating": 40.0, "level_code": "FBS"},
        {"team_id": 11, "power_rating": 100.0, "level_code": "FCS"},
        {"team_id": 12, "power_rating": 110.0, "level_code": "FCS"},
        {"team_id": 13, "power_rating": 120.0, "level_code": "FCS"},
        {"team_id": 14, "power_rating": 130.0, "level_code": "FCS"},
        {"team_id": 15, "power_rating": 140.0, "level_code": "FCS"},
        {"team_id": 16, "power_rating": 150.0, "level_code": "FCS"},
    ]
    pct = _percentiles_within_level(rows, "power_rating")

    # Each level spans the full 0..1 range — top of its own cohort is 1.0,
    # bottom is 0.0 — regardless of the other level's absolute numbers.
    assert pct[1] == 0.0          # weakest FBS
    assert pct[4] == 1.0          # strongest FBS
    assert pct[11] == 0.0         # weakest FCS
    assert pct[16] == 1.0         # strongest FCS

    # The strongest FBS team must NOT be dragged down just because every FCS
    # rating is numerically larger (the old cross-level bug).
    assert pct[4] > pct[1]

    # A mid FBS team sits in the middle of its OWN cohort, not the bottom of
    # the pooled 10-team list (which would have been ~0.33).
    assert abs(pct[3] - (2 / 3)) < 1e-9


def test_single_team_level_does_not_divide_by_zero() -> None:
    # A lone team in its level must not divide-by-zero. rank 0 / max(1, 0) = 0.0
    # — deterministic and crash-free (the exact value is moot for a 1-team cohort).
    rows = [{"team_id": 99, "power_rating": 5.0, "level_code": "DIII"}]
    pct = _percentiles_within_level(rows, "power_rating")
    assert pct[99] == 0.0


# ---------------------------------------------------------------------------
# Band-gap closure (2026-05-28): the Rule-3 trajectory bands must be contiguous
# so percentiles in the old 0.25-0.45 and 0.70-0.80 gaps no longer collapse onto
# the undifferentiated quiet-professional fallback.
# ---------------------------------------------------------------------------

# A slug that is NOT seeded, structural, or a blueblood — so it falls through to
# the Rule-3 trajectory bands rather than a deterministic lock.
_UNSEEDED_SLUG = "test-generic-program"


@pytest.mark.parametrize(
    "power",
    [round(p / 100, 2) for p in range(0, 101, 1)],
)
def test_no_power_percentile_falls_through_to_fallback(power: float) -> None:
    # Every percentile in [0, 1] must land in a real trajectory band — never the
    # generic "fallback" note, which previously caught the band gaps.
    result = classify_team(_UNSEEDED_SLUG, power_percentile=power)
    assert result["notes"] != "fallback", f"power={power} dropped to fallback"
    assert result["notes"].startswith("trajectory-")


def test_former_gap_bands_now_classified() -> None:
    # Spot-check the two previously-uncovered ranges resolve to differentiated
    # archetypes rather than the fallback.
    lower_gap = classify_team(_UNSEEDED_SLUG, power_percentile=0.35)
    assert lower_gap["notes"] == "trajectory-lower-mid"
    assert lower_gap["primary_archetype_slug"] == "content-mid-major"

    upper_gap = classify_team(_UNSEEDED_SLUG, power_percentile=0.75)
    assert upper_gap["notes"] == "trajectory-strong"
    assert upper_gap["primary_archetype_slug"] == "quiet-professional"


def test_resume_gap_promotes_lower_mid_to_sleeper() -> None:
    # A lower-middle team that is outperforming its rating (resume - power >= .10)
    # reads as a Sleeper, not a down-phase mid-major.
    result = classify_team(_UNSEEDED_SLUG, power_percentile=0.30, resume_percentile=0.55)
    assert result["primary_archetype_slug"] == "sleeper"
    assert result["notes"] == "trajectory-rising"


def test_no_percentile_at_all_still_uses_fallback() -> None:
    # When NO percentile is available (no model run anywhere), the offseason
    # fallback is still the correct terminal behavior.
    result = classify_team(_UNSEEDED_SLUG, power_percentile=None)
    assert result["notes"] == "fallback"


# ---------------------------------------------------------------------------
# Offseason no-model-run fallback (2026-05-28): classifying a season with no
# completed power ratings must walk back to the last completed season's ratings
# (offseason-preview posture) instead of dropping every team to the fallback.
# ---------------------------------------------------------------------------


@pytest.fixture
def migrated_db(tmp_path: Path) -> Database:
    db = Database(f"sqlite:///{tmp_path / 'archetypes.db'}")
    db.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(db)
    return db


def _seed_prior_season_ratings(db: Database) -> list[str]:
    """Seed 2024 power ratings for 5 unseeded FBS teams; leave 2026 empty."""
    db.upsert_many(
        "levels",
        [{"level_code": "FBS", "level_name": "FBS", "sort_order": 1}],
        conflict_columns=["level_code"],
    )
    db.upsert_many(
        "seasons",
        [{"season_year": 2024}, {"season_year": 2026}],
        conflict_columns=["season_year"],
    )
    slugs = [f"offseason-test-{i}" for i in range(5)]
    teams = [
        {"team_id": 9001 + i, "canonical_name": f"Offseason Test {i}",
         "slug": slug, "level_code": "FBS", "is_active": 1}
        for i, slug in enumerate(slugs)
    ]
    db.upsert_many("teams", teams, conflict_columns=["team_id"])

    db.upsert_many(
        "model_runs",
        [{"model_run_id": 7001, "model_name": "test", "model_version": "t",
          "season_year": 2024, "week": 16, "data_cutoff_utc": "2024-12-01T00:00:00Z"}],
        conflict_columns=["model_run_id"],
    )
    power_rows = [
        {"model_run_id": 7001, "team_id": 9001 + i, "season_year": 2024, "week": 16,
         "power_rating": 10.0 * i, "offense_rating": 0.0, "defense_rating": 0.0,
         "special_teams_rating": 0.0, "tempo_rating": 0.0}
        for i in range(5)
    ]
    db.upsert_many(
        "power_ratings_weekly", power_rows,
        conflict_columns=["model_run_id", "team_id", "week"],
    )
    return slugs


def test_offseason_falls_back_to_last_completed_season(migrated_db: Database) -> None:
    slugs = _seed_prior_season_ratings(migrated_db)

    # Season 2026 has no completed model run — must borrow 2024's ratings.
    written = classify_all_fanbases(migrated_db, season_year=2026)
    assert written >= len(slugs)

    rows = migrated_db.query_all(
        """
        select t.slug, fc.notes
        from fanbase_classification fc
        join teams t on t.team_id = fc.team_id
        where fc.season_year = 2026 and t.slug like 'offseason-test-%'
        order by t.slug
        """
    )
    assert {r["slug"] for r in rows} == set(slugs)
    # Because 2024 ratings were applied, every team lands in a real trajectory
    # band — NOT the no-percentile "fallback".
    notes = {r["notes"] for r in rows}
    assert "fallback" not in notes, notes
    assert all(n.startswith("trajectory-") for n in notes), notes


def test_classification_stamped_with_requested_season_not_ratings_season(migrated_db: Database) -> None:
    _seed_prior_season_ratings(migrated_db)
    classify_all_fanbases(migrated_db, season_year=2026)

    # Rows are written under the requested season 2026, even though percentiles
    # were derived from the 2024 model run.
    season_2026 = migrated_db.query_one(
        "select count(*) as n from fanbase_classification where season_year = 2026"
    )
    assert season_2026 is not None and season_2026["n"] >= 5
