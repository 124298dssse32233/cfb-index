-- Chronicle: Pipeline Checkpoints
-- Per-stage outputs for idempotent retry. Each pipeline run produces a sequence
-- of stage outputs (planner -> writer -> fact_critic -> voice_critic ->
-- collision_critic -> refiner). If a downstream stage fails, we resume from the
-- last good checkpoint instead of regenerating from scratch (token-cost savings
-- plus determinism for QA).
--
-- (cache_key, stage, attempt) is unique — if a stage is retried it gets attempt=2,
-- attempt=3, etc., so we can audit all attempts.
--
-- FK (documented): cache_key -> chronicle_card_cache.cache_key

BEGIN;

CREATE TABLE IF NOT EXISTS pipeline_checkpoints (
    checkpoint_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key          TEXT    NOT NULL,
    stage              TEXT    NOT NULL CHECK (stage IN ('planner', 'writer', 'fact_critic', 'voice_critic', 'collision_critic', 'refiner')),
    attempt            INTEGER NOT NULL DEFAULT 1,
    output_json        TEXT    NOT NULL,
    tokens_input       INTEGER,
    tokens_output      INTEGER,
    wall_clock_ms      INTEGER,
    status             TEXT    NOT NULL CHECK (status IN ('ok', 'retry', 'failed')),
    error_message      TEXT,
    created_at_utc     TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (cache_key, stage, attempt)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_checkpoints_resume
    ON pipeline_checkpoints (cache_key, stage);

CREATE INDEX IF NOT EXISTS idx_pipeline_checkpoints_status
    ON pipeline_checkpoints (status, created_at_utc);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_checkpoints';
