-- Sprint v5-1 Day 3 — Per-surface backfill progress tracking.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#3 of 15).
--
-- Supports `backfill_full_history.yml` resume logic. Each row records the
-- last-processed cursor for a (surface, partition_key) tuple so a workflow
-- can resume mid-stream after a timeout or failure. partition_key is free
-- form (e.g. 'season=2024' or 'program=alabama&week=7').

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS backfill_progress (
    surface TEXT NOT NULL,                          -- e.g. 'archive_threads', 'chronicle', 'canon'
    partition_key TEXT NOT NULL,                    -- arbitrary cursor scope identifier
    cursor_value TEXT,                              -- e.g. last processed thread_id / ISO date
    status TEXT NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('queued','in_progress','done','failed','skipped')),
    rows_processed INTEGER NOT NULL DEFAULT 0,
    rows_skipped INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    started_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at_utc TEXT,
    PRIMARY KEY (surface, partition_key)
);

CREATE INDEX IF NOT EXISTS idx_backfill_progress_status
    ON backfill_progress (surface, status);

CREATE INDEX IF NOT EXISTS idx_backfill_progress_updated
    ON backfill_progress (updated_at_utc DESC);

COMMIT;
