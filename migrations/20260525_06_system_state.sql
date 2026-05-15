-- Sprint v5-1 Day 3 — Global system state (/admin/panic + circuit-break).
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#6 of 15).
--
-- Singleton key/value store for global runtime flags read on every workflow
-- entry point. The /admin/panic page (v5-8) flips `panic_mode=1` to halt
-- all LLM-spending operations until a human clears it. The circuit_break
-- columns let the auto-throttle disable specific subsystems without taking
-- the whole pipeline down.
--
-- Conceptually a single row per `scope` (default scope = 'global').

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS system_state (
    scope TEXT PRIMARY KEY DEFAULT 'global',
    panic_mode INTEGER NOT NULL DEFAULT 0,           -- 1 = halt all LLM work
    panic_reason TEXT,
    panic_engaged_at_utc TEXT,
    panic_engaged_by TEXT,                            -- github_handle / 'auto_throttle'
    circuit_break_llm INTEGER NOT NULL DEFAULT 0,     -- 1 = no Anthropic calls
    circuit_break_images INTEGER NOT NULL DEFAULT 0,  -- 1 = no OpenAI Images calls
    circuit_break_publish INTEGER NOT NULL DEFAULT 0, -- 1 = skip Vercel deploy step
    last_updated_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_by TEXT,
    notes TEXT
);

-- Seed the global row so reads never have to handle NULL.
INSERT OR IGNORE INTO system_state (scope, panic_mode, last_updated_by, notes)
VALUES ('global', 0, 'migration_v5_1', 'initial seed');

COMMIT;
