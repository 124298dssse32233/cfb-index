-- Sprint v5-1 Day 3 — Canon model_version_at_generate column.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#14 of 15).
--
-- Adds model_version_at_generate to canon_entries so v5-5 can:
--   * Detect entries authored under an older model and regenerate selectively
--   * Surface "Updated YYYY-MM-DD — new model" notes on canon pages
--   * Run cohort-level QA: re-score outputs from a specific model version
--
-- Idempotence: gated by schema_migrations in apply_sql_migrations.

BEGIN TRANSACTION;

ALTER TABLE canon_entries ADD COLUMN model_version_at_generate TEXT;

CREATE INDEX IF NOT EXISTS idx_canon_entries_model_version
    ON canon_entries (model_version_at_generate)
    WHERE model_version_at_generate IS NOT NULL;

COMMIT;
