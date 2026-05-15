-- Sprint v5-1 Day 3 — Mailbag source_kind column.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#13 of 15).
--
-- Adds source_kind to mailbag_submissions so the v5-4 mailbag-mine-questions
-- pipeline can mark whether a question came from Reddit, Bluesky, Substack
-- comments, the web form, or was hand-seeded. Renderer can group "From
-- Reddit" / "From the form" sections on the mailbag page.
--
-- Idempotence: gated by schema_migrations in apply_sql_migrations.

BEGIN TRANSACTION;

ALTER TABLE mailbag_submissions ADD COLUMN source_kind TEXT;

-- Backfill: rows that arrived before this migration came in via the
-- legacy web form (the only intake path that existed pre-v5-4).
UPDATE mailbag_submissions
   SET source_kind = 'web_form'
 WHERE source_kind IS NULL;

CREATE INDEX IF NOT EXISTS idx_mailbag_submissions_source_kind
    ON mailbag_submissions (source_kind, submitted_at_utc DESC);

COMMIT;
