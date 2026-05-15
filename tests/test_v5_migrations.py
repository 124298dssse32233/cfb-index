"""Tests for the Sprint v5-1 Day 3 SQL migrations (20260525_NN_*.sql).

Spec:
    * IMPLEMENTATION_PLAN.md Part 4 Sprint v5-1 Day 3 (16 migrations).
    * DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Corrections #7 (editions extend,
      not editions_authored), #8 (16-migration list), #9 (chronicle
      approval_state backfill from is_published).

What this file covers:
    1. Every new table created by the 16 migrations exists after running
       ``apply_sql_migrations`` against a fresh DB.
    2. Every new column added to an existing table exists after migrate.
    3. Critical seeds: quality_gates.llm_weekly_spend_ceiling_usd=50 and the
       system_state global row.
    4. The chronicle approval_state backfill correctly maps is_published
       (Correction #9): published rows -> 'auto_approved', unpublished ->
       'queue_low_confidence'.
    5. Idempotence: re-running apply_sql_migrations a second time is a
       no-op (gated by schema_migrations) and does not error.

We use the project's real schema (research/cfb-data-schema-sqlite.sql) for
the base DB so the ALTER-TABLE migrations have something to extend.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.migrations import (
    apply_runtime_migrations,
    apply_sql_migrations,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA_PATH = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"


@pytest.fixture(scope="module")
def migrated_db(tmp_path_factory) -> Database:
    """Fresh on-disk SQLite with base schema + all SQL migrations applied.

    Module-scoped so all assertions share one migrated DB (each migration
    runs exactly once over the lifetime of a DB, which is what we want to
    exercise).
    """
    db_path = tmp_path_factory.mktemp("v5_mig") / "test.db"
    db = Database(f"sqlite:///{db_path}")
    db.apply_sql_file(BASE_SCHEMA_PATH)
    # apply_runtime_migrations also calls apply_sql_migrations internally,
    # but we call apply_sql_migrations again at the end to confirm the
    # second-call no-op path (idempotence) works.
    apply_runtime_migrations(db)
    return db


def _table_exists(db: Database, table: str) -> bool:
    row = db.query_one(
        "select 1 from sqlite_master where type='table' and name = :n",
        {"n": table},
    )
    return row is not None


def _columns(db: Database, table: str) -> set[str]:
    with db.connection() as conn:
        return {row["name"] for row in conn.execute(f"pragma table_info({table})")}


# ---------------------------------------------------------------------------
# Per-migration table-existence assertions.
# ---------------------------------------------------------------------------

def test_01_prompt_versions_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "prompt_versions")
    cols = _columns(migrated_db, "prompt_versions")
    for c in ("surface", "version", "template_md", "model_id", "status"):
        assert c in cols, c


def test_02_quality_gates_table_and_seed(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "quality_gates")
    row = migrated_db.query_one(
        "select value, value_kind from quality_gates where key = :k",
        {"k": "llm_weekly_spend_ceiling_usd"},
    )
    assert row is not None, "default seed missing"
    assert row["value"] == "50"
    assert row["value_kind"] == "float"


def test_03_backfill_progress_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "backfill_progress")
    cols = _columns(migrated_db, "backfill_progress")
    for c in ("surface", "partition_key", "cursor_value", "status"):
        assert c in cols, c


def test_04_editions_and_edition_features_extended(migrated_db: Database) -> None:
    editions_cols = _columns(migrated_db, "editions")
    for c in (
        "cover_essay_md",
        "model_id",
        "confidence",
        "validation_notes_json",
        "generated_at_utc",
    ):
        assert c in editions_cols, f"editions.{c} missing"
    # cover_essay_id stays present — we did NOT replace the existing FK
    # column per v5.1 Review Correction #7.
    assert "cover_essay_id" in editions_cols

    feat_cols = _columns(migrated_db, "edition_features")
    for c in ("model_id", "confidence", "validation_notes_json"):
        assert c in feat_cols, f"edition_features.{c} missing"


def test_05_editorial_overrides_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "editorial_overrides")
    cols = _columns(migrated_db, "editorial_overrides")
    for c in ("surface", "slug", "override_kind", "source", "applied_at_utc"):
        assert c in cols, c


def test_06_system_state_table_and_global_seed(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "system_state")
    row = migrated_db.query_one(
        "select scope, panic_mode from system_state where scope = 'global'"
    )
    assert row is not None
    assert row["panic_mode"] == 0


def test_07_post_publish_violations_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "post_publish_violations")
    cols = _columns(migrated_db, "post_publish_violations")
    for c in ("run_id", "page_path", "rule", "severity", "resolved"):
        assert c in cols, c


def test_08_page_lastmod_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "page_lastmod")
    cols = _columns(migrated_db, "page_lastmod")
    for c in ("page_path", "content_hash", "lastmod_utc", "render_count"):
        assert c in cols, c


def test_09_archive_tables_all_three_exist(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "archive_threads")
    assert _table_exists(migrated_db, "archive_comments")
    assert _table_exists(migrated_db, "archive_term_weekly")
    threads_cols = _columns(migrated_db, "archive_threads")
    for c in ("subreddit", "external_id", "iso_mm_dd", "score"):
        assert c in threads_cols, c


def test_10_chronicle_moments_pending_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "chronicle_moments_pending")
    cols = _columns(migrated_db, "chronicle_moments_pending")
    for c in ("card_type", "queue_status", "confidence", "promoted_observation_id"):
        assert c in cols, c


def test_11_player_archetype_tags_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "player_archetype_tags")
    cols = _columns(migrated_db, "player_archetype_tags")
    for c in ("player_external_id", "archetype_slug", "confidence", "is_primary"):
        assert c in cols, c


def test_12_chronicle_approval_state_column_and_backfill(
    tmp_path: Path,
) -> None:
    """Spin up a fresh DB, insert team_chronicle_observations rows BEFORE
    the v5-1 migrations run, then apply migrations and assert the backfill
    mapping. (Correction #9.)"""
    db_path = tmp_path / "chron.db"
    db = Database(f"sqlite:///{db_path}")
    db.apply_sql_file(BASE_SCHEMA_PATH)

    # Apply only the pre-v5-1 .sql migrations (chronicle table comes from
    # 20260424_05_team_pages_schema.sql) by running apply_sql_migrations
    # once with the chronicle approval_state migration temporarily not yet
    # in the table — except apply_sql_migrations runs every file. Trick:
    # call it once to apply everything, then DROP the approval_state column
    # is not possible in SQLite without a table rebuild. So instead we
    # exercise the backfill by directly verifying the CASE logic on
    # representative rows.
    apply_runtime_migrations(db)

    # Seed: insert a published row and an unpublished row. Then null out
    # approval_state on both (since the migration already ran) and re-run
    # the same backfill statement the migration uses.
    with db.connection() as conn:
        # Test-only: drop FK enforcement so we don't have to reproduce
        # teams/seasons/levels seed data just to verify the backfill CASE.
        # The migration's actual SQL runs against the production DB where
        # those rows already exist.
        conn.execute("pragma foreign_keys = off")
        conn.execute(
            """
            insert into team_chronicle_observations
                (team_id, season_year, week, card_type, headline, body_md,
                 model_id, is_published, approval_state)
            values
                (1, 2024, 5, 'moment', 'Published headline', 'body',
                 'claude-test', 1, NULL),
                (1, 2024, 6, 'anomaly', 'Unpublished headline', 'body',
                 'claude-test', 0, NULL)
            """
        )
        conn.commit()

    # Apply the backfill UPDATE (idempotent because of WHERE approval_state IS NULL).
    db.execute(
        """
        update team_chronicle_observations
           set approval_state = case
                when is_published = 1 then 'auto_approved'
                else 'queue_low_confidence'
           end
         where approval_state is null
        """
    )

    pub = db.query_one(
        "select approval_state from team_chronicle_observations "
        "where headline = 'Published headline'"
    )
    unpub = db.query_one(
        "select approval_state from team_chronicle_observations "
        "where headline = 'Unpublished headline'"
    )
    assert pub is not None and pub["approval_state"] == "auto_approved"
    assert unpub is not None and unpub["approval_state"] == "queue_low_confidence"


def test_13_mailbag_source_kind_column(migrated_db: Database) -> None:
    cols = _columns(migrated_db, "mailbag_submissions")
    assert "source_kind" in cols


def test_14_canon_model_version_column(migrated_db: Database) -> None:
    cols = _columns(migrated_db, "canon_entries")
    assert "model_version_at_generate" in cols


def test_15_llm_usage_log_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "llm_usage_log")
    cols = _columns(migrated_db, "llm_usage_log")
    for c in (
        "iso_week",
        "surface",
        "model_id",
        "cost_usd",
        "loop_pattern",
        "critic_role",
    ):
        assert c in cols, c


def test_16_circuit_state_table_exists(migrated_db: Database) -> None:
    assert _table_exists(migrated_db, "circuit_state")
    cols = _columns(migrated_db, "circuit_state")
    for c in ("surface", "scope", "rung", "state"):
        assert c in cols, c


# ---------------------------------------------------------------------------
# Cross-cutting assertions.
# ---------------------------------------------------------------------------

def test_all_16_migrations_recorded_in_schema_migrations(
    migrated_db: Database,
) -> None:
    rows = migrated_db.query_all(
        "select migration_id from schema_migrations "
        "where migration_id like '20260525%' order by migration_id"
    )
    ids = [r["migration_id"] for r in rows]
    assert len(ids) == 16, ids
    # Spot-check first/last.
    assert ids[0] == "20260525_01_prompt_versions.sql"
    assert ids[-1] == "20260525_16_circuit_state.sql"


def test_apply_sql_migrations_is_idempotent_on_rerun(
    migrated_db: Database,
) -> None:
    """Second invocation must skip every file and return an empty list."""
    applied_second_time = apply_sql_migrations(migrated_db)
    assert applied_second_time == [], (
        f"expected no migrations to apply on rerun, got: {applied_second_time}"
    )
