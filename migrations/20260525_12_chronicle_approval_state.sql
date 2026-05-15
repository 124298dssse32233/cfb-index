-- Sprint v5-1 Day 3 — Chronicle approval_state column + backfill.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Corrections #8 + #9 (#12 of 15).
--
-- Adds approval_state to team_chronicle_observations and backfills it from
-- the existing is_published column so the v5.3 render filter
-- ( WHERE approval_state IN ('auto_approved','human_approved') )
-- does not drop every existing row.
--
-- Mapping:
--   is_published = 1  -> 'auto_approved'    (already on the page, treat as auto-approved)
--   is_published = 0  -> 'queue_low_confidence' (sits in /admin queue for review)
--
-- Idempotence: gated by schema_migrations in apply_sql_migrations. The
-- backfill UPDATE is also guarded by `approval_state IS NULL` so even a
-- hypothetical re-run is safe.

BEGIN TRANSACTION;

ALTER TABLE team_chronicle_observations ADD COLUMN approval_state TEXT;

UPDATE team_chronicle_observations
   SET approval_state = CASE
        WHEN is_published = 1 THEN 'auto_approved'
        ELSE 'queue_low_confidence'
   END
 WHERE approval_state IS NULL;

CREATE INDEX IF NOT EXISTS idx_team_chron_approval_state
    ON team_chronicle_observations (approval_state, surfaced_rank);

COMMIT;
