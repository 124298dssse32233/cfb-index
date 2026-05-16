-- Sprint v5-3 — owner Interrupt 2: per-surface CostMeter ceilings + 24-hour
-- rolling aggregate auto-disable.
--
-- Two tables:
--   1. `surface_spend_events` — append-only log of (surface, ts_utc, cost_usd)
--      events. The 24-hour rolling aggregate is computed by summing rows
--      with ts_utc >= now() - 24h. Older rows are pruned by a periodic
--      DELETE in `cfb_rankings.circuit_state.prune_old_events`; tests rely
--      on the table holding events past 24h until that's called.
--   2. `surface_degrade_state` — one row per surface that has been
--      auto-disabled. When `should_auto_disable` flips True, an upsert
--      writes a row here; `get_active_pattern` consults it before reading
--      `config.QUALITY_LOOP_FLAGS`. Cleared by
--      `manage.py quality-loop-reenable <surface>` after human review.
--
-- The existing `circuit_state` table (migration 16) is failure-rate based
-- and orthogonal to these tables. We deliberately keep the two state
-- machines separate so future work can evolve them independently without
-- breaking the rung-3 weekly-ceiling code path.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS surface_spend_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    surface TEXT NOT NULL,
    ts_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cost_usd REAL NOT NULL CHECK (cost_usd >= 0),
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_surface_spend_events_surface_ts
    ON surface_spend_events (surface, ts_utc DESC);

CREATE TABLE IF NOT EXISTS surface_degrade_state (
    surface TEXT PRIMARY KEY,
    degrade_pattern TEXT NOT NULL,
    breached_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    breached_spend_usd REAL NOT NULL,
    ceiling_usd REAL NOT NULL,
    reason TEXT
);

COMMIT;
