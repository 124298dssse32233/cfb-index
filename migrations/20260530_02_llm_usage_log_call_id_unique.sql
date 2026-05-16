-- Priority 2 (2026-05-16) — dedup llm_usage_log via call_id INSERT OR IGNORE.
--
-- llm_usage_log.call_id column already exists (migration 15). Adding a
-- partial unique index lets the two writers — quality_loop._emit_telemetry
-- and CostMeter.record() — share a call_id for the same underlying LLM
-- call, and have the second insert silently no-op via INSERT OR IGNORE.
--
-- WHERE call_id IS NOT NULL is critical: pre-call_id rows (everything
-- before 2026-05-16 22:30) have NULL call_ids and must remain unique-free
-- to avoid migration failure on existing data.

CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_usage_log_call_id_unique
    ON llm_usage_log(call_id) WHERE call_id IS NOT NULL;
