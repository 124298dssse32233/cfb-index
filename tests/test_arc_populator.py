"""Tests for the D-010 narrative arc-frame populator.

Covers the data-backed frames (portal_class_arrival, archetype_transition),
idempotency, the season_narrative_state cache rebuild, and the graceful
empty-source degradation for the five frames whose feeds are not yet populated.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfb_rankings.chronicle.arc_populator import (
    ARC_FRAMES,
    populate_season_arcs,
)
from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{tmp_path / 'arcs.db'}")
    database.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(database)
    _seed_base(database)
    return database


def _seed_base(db: Database) -> None:
    db.upsert_many(
        "levels",
        [{"level_code": "FBS", "level_name": "FBS", "sort_order": 1},
         {"level_code": "FCS", "level_name": "FCS", "sort_order": 2}],
        conflict_columns=["level_code"],
    )
    db.upsert_many(
        "seasons",
        [{"season_year": y} for y in (2024, 2025, 2026)],
        conflict_columns=["season_year"],
    )
    teams = [
        {"team_id": 1, "canonical_name": "Alpha", "slug": "alpha", "level_code": "FBS"},
        {"team_id": 2, "canonical_name": "Bravo", "slug": "bravo", "level_code": "FBS"},
        {"team_id": 3, "canonical_name": "Charlie", "slug": "charlie", "level_code": "FBS"},
        {"team_id": 4, "canonical_name": "Delta FCS", "slug": "delta", "level_code": "FCS"},
    ]
    db.upsert_many("teams", teams, conflict_columns=["team_id"])


def _seed_portal(db: Database, season: int) -> None:
    rows = [
        # alpha = strongest class, bravo = weaker, delta = FCS (must be excluded)
        {"transfer_entry_id": 1, "season_year": season, "to_team_id": 1, "transfer_points": 50.0},
        {"transfer_entry_id": 2, "season_year": season, "to_team_id": 1, "transfer_points": 40.0},
        {"transfer_entry_id": 3, "season_year": season, "to_team_id": 2, "transfer_points": 10.0},
        {"transfer_entry_id": 4, "season_year": season, "to_team_id": 4, "transfer_points": 99.0},
    ]
    db.upsert_many("transfer_entries", rows, conflict_columns=["transfer_entry_id"])


def _seed_classification(db: Database, team_id: int, season: int, slug_arch: str, conf: float = 0.7) -> None:
    db.upsert_many(
        "fanbase_classification",
        [{"team_id": team_id, "season_year": season, "primary_archetype_slug": slug_arch,
          "primary_confidence": conf, "modifier_slugs_json": "[]", "signature_phrase": "",
          "classifier_version": "v1.0", "notes": "test"}],
        conflict_columns=["team_id", "season_year"],
    )


def test_arc_frames_are_the_ten_locked_d010_frames() -> None:
    assert set(ARC_FRAMES) == {
        "coaching_transition", "coordinator_carousel", "nil_collective_swing",
        "portal_class_arrival", "recruiting_class_arrival", "rivalry_reset",
        "archetype_transition", "market_belief_swing", "playoff_path_change",
        "dynasty_status_change",
    }
    assert len(ARC_FRAMES) == 10


def test_portal_class_arrival_opens_fbs_arcs_only(db: Database) -> None:
    _seed_portal(db, 2026)
    report = populate_season_arcs(db, 2026)

    assert report["per_frame"]["portal_class_arrival"] == 2  # alpha + bravo, NOT delta (FCS)

    arcs = db.query_all(
        """
        select t.slug, a.tension_score
        from season_narrative_arc a join teams t on t.team_id = a.team_id
        where a.frame = 'portal_class_arrival' and a.season_year = 2026
        order by a.tension_score desc
        """
    )
    slugs = [r["slug"] for r in arcs]
    assert slugs == ["alpha", "bravo"]
    assert "delta" not in slugs
    # Top class is normalised to tension 1.0; the weaker class is proportional.
    assert arcs[0]["tension_score"] == 1.0
    assert arcs[1]["tension_score"] < 1.0


def test_archetype_transition_opens_only_on_change(db: Database) -> None:
    # alpha changes archetype 2025 -> 2026; bravo stays the same.
    _seed_classification(db, 1, 2025, "quiet-professional")
    _seed_classification(db, 1, 2026, "content-mid-major", conf=0.66)
    _seed_classification(db, 2, 2025, "stockholm-syndrome")
    _seed_classification(db, 2, 2026, "stockholm-syndrome")

    report = populate_season_arcs(db, 2026)
    assert report["per_frame"]["archetype_transition"] == 1

    arcs = db.query_all(
        "select t.slug, a.tension_score from season_narrative_arc a "
        "join teams t on t.team_id = a.team_id where a.frame = 'archetype_transition'"
    )
    assert [r["slug"] for r in arcs] == ["alpha"]
    assert arcs[0]["tension_score"] == 0.66  # carries the new-archetype confidence


def test_data_gated_frames_report_empty_with_reason(db: Database) -> None:
    report = populate_season_arcs(db, 2026)
    for frame in ("coordinator_carousel", "nil_collective_swing",
                  "market_belief_swing", "playoff_path_change", "dynasty_status_change"):
        assert report["per_frame"][frame] == 0
        assert report["empty_reasons"][frame]  # a non-empty reason string


def test_idempotent_rerun_does_not_duplicate(db: Database) -> None:
    _seed_portal(db, 2026)
    _seed_classification(db, 1, 2025, "quiet-professional")
    _seed_classification(db, 1, 2026, "content-mid-major")

    first = populate_season_arcs(db, 2026)
    second = populate_season_arcs(db, 2026)
    assert first["arcs_total"] == second["arcs_total"]

    distinct = db.query_one(
        "select count(*) as n, count(distinct arc_id) as d from season_narrative_arc where season_year = 2026"
    )
    assert distinct["n"] == distinct["d"]  # no duplicate arc_ids


def test_state_cache_holds_open_arcs(db: Database) -> None:
    _seed_portal(db, 2026)
    populate_season_arcs(db, 2026)

    state = db.query_one(
        "select open_arcs_json, unresolved_tensions_json from season_narrative_state "
        "where team_id = 1 and season_year = 2026"
    )
    assert state is not None
    open_arcs = json.loads(state["open_arcs_json"])
    assert any(a["frame"] == "portal_class_arrival" for a in open_arcs)
    # alpha's top portal class has tension 1.0 >= the unresolved floor.
    unresolved = json.loads(state["unresolved_tensions_json"])
    assert any(u["frame"] == "portal_class_arrival" for u in unresolved)


def test_chronicle_pipeline_surfaces_populated_arcs(db: Database) -> None:
    # The Chronicle prompt-context builder must actually read the arcs we open
    # (regression: it previously queried a non-existent season_narrative_state
    # column shape and silently degraded to []).
    from cfb_rankings.chronicle.pipeline import PageTarget, _fetch_narrative_state

    _seed_portal(db, 2026)
    populate_season_arcs(db, 2026)

    team_target = PageTarget(entity_kind="team", slug="alpha", season_year=2026, week_number=0)
    state = _fetch_narrative_state(db, team_target)
    open_arcs = state["open_arcs"]
    assert open_arcs, "team with open arcs must surface them to the prompt"
    top = open_arcs[0]
    assert top["frame"] == "portal_class_arrival"
    assert top["arc_id"] == "alpha-2026-portal-class-arrival"
    assert top["summary"]  # a non-empty human-readable summary for the prompt
    assert "tension" in top["summary"]

    # Players are not team-keyed, so they degrade to the empty default.
    player_target = PageTarget(entity_kind="player", slug="alpha", season_year=2026, week_number=0)
    assert _fetch_narrative_state(db, player_target)["open_arcs"] == []
