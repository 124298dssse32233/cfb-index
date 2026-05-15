-- Sprint v5-1 Day 3 — DB-backed LLM usage log.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#15 of 15).
--
-- The existing JSONL append-only file at output/_llm_usage_log.jsonl stays
-- the durable primary record. This DB-backed mirror exists so the v5-1
-- auto-throttle can compute weekly spend with a single SUM() query against
-- llm_weekly_spend_ceiling_usd (quality_gates row), and so the /admin
-- queue can render a table.
--
-- Writers: team_pages.llm_usage_log.append_llm_usage() (extended in v5-1
-- to mirror its JSONL write into this table inside the same transaction).
-- Quality_loop adds loop_pattern/critic_role/critic_score/revise_count/
-- fell_back fields per v5.3 Part 3.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS llm_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT,                                    -- uuid; mirrors JSONL row id
    invoked_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    iso_week TEXT NOT NULL,                          -- e.g. '2026-W21' for fast weekly SUM
    surface TEXT NOT NULL,                           -- 'edition_cover','daily','chronicle','wire', etc
    model_id TEXT NOT NULL,                          -- 'claude-sonnet-4-5','claude-opus-4-7'...
    prompt_version TEXT,                             -- joins to prompt_versions
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_input_tokens INTEGER NOT NULL DEFAULT 0,
    cache_creation_input_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,              -- computed at write time
    latency_ms INTEGER,
    success INTEGER NOT NULL DEFAULT 1,
    error_kind TEXT,
    -- Quality-loop telemetry (v5.3 Part 3):
    loop_pattern TEXT,                               -- 'a_single_shot','b_single_critic','c_critic_revise','d_adversarial','e_continuity'
    critic_role TEXT,                                -- 'voice','headline','factuality','engagement','continuity'
    critic_score REAL,                               -- 0..1
    revise_count INTEGER NOT NULL DEFAULT 0,
    fell_back INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_iso_week
    ON llm_usage_log (iso_week, model_id);

CREATE INDEX IF NOT EXISTS idx_llm_usage_invoked
    ON llm_usage_log (invoked_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_llm_usage_surface
    ON llm_usage_log (surface, invoked_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_llm_usage_loop_pattern
    ON llm_usage_log (loop_pattern, invoked_at_utc DESC)
    WHERE loop_pattern IS NOT NULL;

COMMIT;
