-- Sprint v5-1 Day 3 — EXTEND existing editions + edition_features tables.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Corrections #7 + #8 (#4 of 15).
--
-- Why this is NOT a new `editions_authored` table:
--   v5 (parent audit) proposed a parallel `editions_authored` table. v5.1
--   Review Correction #7 caught that the existing `editions.cover_essay_id`
--   FK at migrations/20260425_09_editions_schema.sql:28 already points to a
--   planned `cover_essays` table. A parallel `editions_authored` would
--   collide. Resolution: extend the existing editions + edition_features
--   tables with v5-2 authoring-pipeline columns and keep cover_essay_id as
--   a join key (or null) for the legacy path.
--
-- Idempotence:
--   SQLite has no `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. This file is
--   gated by schema_migrations in apply_sql_migrations (see
--   src/cfb_rankings/migrations.py): once recorded, the file is skipped.
--   Therefore each ALTER runs exactly once over the lifetime of a DB.

BEGIN TRANSACTION;

-- editions: v5-2 authoring-pipeline metadata.
-- cover_essay_md   — full markdown body produced by generate-edition
-- model_id         — generating model (e.g. 'claude-sonnet-4-5')
-- confidence       — quality_loop critic verdict score, 0.0-1.0
-- validation_notes_json — voice-validator + critic findings (json blob)
-- generated_at_utc — when the authoring pipeline last produced this row
ALTER TABLE editions ADD COLUMN cover_essay_md TEXT;
ALTER TABLE editions ADD COLUMN model_id TEXT;
ALTER TABLE editions ADD COLUMN confidence REAL;
ALTER TABLE editions ADD COLUMN validation_notes_json TEXT;
ALTER TABLE editions ADD COLUMN generated_at_utc TEXT;

-- edition_features: same provenance triple per feature block.
ALTER TABLE edition_features ADD COLUMN model_id TEXT;
ALTER TABLE edition_features ADD COLUMN confidence REAL;
ALTER TABLE edition_features ADD COLUMN validation_notes_json TEXT;

COMMIT;
