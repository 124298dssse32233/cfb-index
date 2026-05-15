-- Sprint v5-1 Day 3 — Per-surface circuit-breaker state.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3 (#16, from v5.3 carryover);
--       DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8.
--
-- Distinct from the global flags in system_state.circuit_break_* — this is
-- the fine-grained per-surface circuit breaker that quality_loop.py trips
-- using v5.3 Part 3's 3-rung escalation:
--   Rung 1: warn — high failure rate, keep running
--   Rung 2: degrade — fall back to single-shot loop (no critic)
--   Rung 3: open — skip the surface entirely; alert via notify_failure.yml
--
-- One row per (surface, scope) — scope='global' for surface-wide breakers,
-- or a partition like program_slug for per-team breakers.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS circuit_state (
    surface TEXT NOT NULL,                           -- 'edition_cover','daily','chronicle', etc
    scope TEXT NOT NULL DEFAULT 'global',            -- 'global' or partition key (e.g. program slug)
    rung INTEGER NOT NULL DEFAULT 0                  -- 0=closed,1=warn,2=degraded,3=open
        CHECK (rung BETWEEN 0 AND 3),
    state TEXT NOT NULL DEFAULT 'closed'
        CHECK (state IN ('closed','warn','degraded','open')),
    failure_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    last_failure_at_utc TEXT,
    last_failure_reason TEXT,
    last_success_at_utc TEXT,
    opened_at_utc TEXT,                              -- when state first flipped to 'open'
    half_open_at_utc TEXT,                           -- when to retry (cooldown end)
    last_updated_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    PRIMARY KEY (surface, scope)
);

CREATE INDEX IF NOT EXISTS idx_circuit_state_open
    ON circuit_state (state, last_updated_utc DESC)
    WHERE state IN ('degraded','open');

CREATE INDEX IF NOT EXISTS idx_circuit_state_surface
    ON circuit_state (surface, state);

COMMIT;
