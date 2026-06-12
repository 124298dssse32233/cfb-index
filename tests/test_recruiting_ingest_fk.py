"""Regression: recruiting ingest must anchor a pre-window recruit class year.

``player_recruiting_profiles.season_year`` FK-references ``seasons``. Recruit
classes reach back to ``season - 5``, so any recent backfill ingests classes
(e.g. 2018 / 2019) that predate the seasons-table data window (2020+). Before the
fix, that pre-window class raised ``FOREIGN KEY constraint failed`` and aborted
the WHOLE upsert batch — which is why every roster/preseason re-ingest exited 1
on the recruiting tail and no pre-2020 recruit profile ever persisted.

``_ingest_player_recruiting`` now calls ``repository.ensure_season(season)``
first. This test fails (FK crash) if that anchoring line is removed.
"""
from __future__ import annotations

from pathlib import Path

from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations
from cfb_rankings.storage import Repository
from cfb_rankings.ingest.cfbd import _ingest_player_recruiting


def _fresh_db(tmp_path: Path) -> tuple[Database, Repository]:
    db = Database(f"sqlite:///{tmp_path / 'test.db'}")
    schema = Path(__file__).resolve().parents[1] / "research" / "cfb-data-schema-sqlite.sql"
    db.apply_sql_file(schema)
    apply_runtime_migrations(db)
    repository = Repository(db)
    repository.seed_levels()
    # Only the data-window season exists — a pre-2020 recruit class is unanchored.
    repository.ensure_season(2025)
    return db, repository


def _seasons(db: Database) -> set[int]:
    return {int(row["season_year"]) for row in db.query_all("select season_year from seasons")}


def test_recruiting_ingest_anchors_prewindow_class_year(tmp_path):
    db, repository = _fresh_db(tmp_path)
    assert 2018 not in _seasons(db)  # precondition: pre-window class is unanchored

    # A 2018 HS class (predates the 2020 data window). Pre-fix this raised
    # sqlite3.IntegrityError: FOREIGN KEY constraint failed and aborted the batch.
    rows = [{"id": "rec-2018-1", "name": "Pre Window Recruit", "stars": 4}]
    _ingest_player_recruiting(repository, db, rows, 2018)  # must NOT raise

    assert 2018 in _seasons(db)  # the class year got anchored by ensure_season
    written = db.query_all(
        "select season_year from player_recruiting_profiles "
        "where source_recruit_id = %(sid)s",
        {"sid": "rec-2018-1"},
    )
    assert written and int(written[0]["season_year"]) == 2018
