-- Sprint v5-1 Day 3 — Quality gates / runtime tunables.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#2 of 15).
--
-- Key/value store for operational thresholds that the auto-throttle + /admin
-- queue UI flip without a deploy. Default seeded value:
--   llm_weekly_spend_ceiling_usd = 50
-- which the v5-1 throttle reads when summing llm_usage_log spend for the
-- week. Adding a new gate is a normal INSERT/UPDATE; the slider UI in v5-8
-- writes here.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS quality_gates (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,                             -- stringified; coerced at read site
    value_kind TEXT NOT NULL DEFAULT 'string'
        CHECK (value_kind IN ('string','int','float','bool','json')),
    description TEXT,                                -- human-readable note for /admin UI
    updated_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT                                  -- 'human' | 'auto_throttle' | model_id
);

CREATE INDEX IF NOT EXISTS idx_quality_gates_updated
    ON quality_gates (updated_at_utc DESC);

-- Seed: weekly LLM spend ceiling (v5.1 budget = $50/week ~ $1,300/yr cap).
INSERT OR IGNORE INTO quality_gates (key, value, value_kind, description, updated_by)
VALUES (
    'llm_weekly_spend_ceiling_usd',
    '50',
    'float',
    'Weekly Anthropic API spend ceiling in USD. Read by llm_runtime auto-throttle.',
    'migration_v5_1'
);

COMMIT;
