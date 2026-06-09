-- WS-09: prediction ledger — the product's trust spine (per spec 09-calibration-ledger.md).
--
-- Every published model prediction logs one row here at record time. The weekly
-- outcome resolver fills resolved_at_utc / actual_value / accuracy_score once the
-- prediction's window has closed. The methodology page and per-team "we said X,
-- then Y happened" track-record sections read aggregates off this table.
--
-- D-015 (LOCKED): continuous ledger writes (this table), weekly public summary
-- (Sunday cron reads calibration_summary), per-game override (resolver may run
-- early for high-signal events).
--
-- Idempotency contract: prediction_id is DETERMINISTIC over
-- (model_id, entity_type, entity_id, prediction_kind, period_key). One row per
-- (entity, kind, window) per model — re-recording the same window upserts the
-- standing prediction rather than appending, and NEVER clobbers a resolution
-- already written by the resolver. (Per-revision history is a future table; the
-- ledger grades the final standing prediction for each window against outcome.)

CREATE TABLE IF NOT EXISTS prediction_ledger (
    prediction_id    TEXT    PRIMARY KEY,              -- sha1(model_id|entity_type|entity_id|prediction_kind|period_key)
    model_id         TEXT    NOT NULL,                 -- e.g. fanbase-classifier, heisman-model, season-wins
    model_version    TEXT,                             -- model's self-reported version at record time
    entity_type      TEXT    NOT NULL,                 -- team | player | game | conference
    entity_id        TEXT    NOT NULL,                 -- slug or stable id
    prediction_kind  TEXT    NOT NULL,                 -- archetype_assignment | cfp_make_field | season_wins | ...
    period_key       TEXT    NOT NULL,                 -- window the prediction is FOR (e.g. "2026" or "2026-W04")
    predicted_value  TEXT    NOT NULL,                 -- stringified label or number
    confidence_band  TEXT    NOT NULL DEFAULT 'unset'
                         CHECK (confidence_band IN ('high', 'medium', 'low', 'unset')),
    confidence_value REAL,                             -- optional numeric prob/confidence 0..1
    evidence_ref     TEXT,                             -- citation/source pointer for the receipt pattern
    observed_at_utc  TEXT    NOT NULL DEFAULT (datetime('now')),   -- first-seen (preserved across re-records)
    expires_at_utc   TEXT,                             -- when the outcome becomes resolvable
    -- resolution (written by resolve_due_predictions)
    resolved_at_utc  TEXT,
    actual_value     TEXT,
    accuracy_score   REAL,                             -- 0..1, kind-specific scoring
    resolution_note  TEXT,
    updated_at_utc   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_prediction_ledger_resolve
    ON prediction_ledger (resolved_at_utc, expires_at_utc);
CREATE INDEX IF NOT EXISTS idx_prediction_ledger_model
    ON prediction_ledger (model_id, prediction_kind, resolved_at_utc);
CREATE INDEX IF NOT EXISTS idx_prediction_ledger_entity
    ON prediction_ledger (entity_type, entity_id, prediction_kind);

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name = 'prediction_ledger';
