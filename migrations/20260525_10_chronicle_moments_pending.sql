-- Sprint v5-1 Day 3 — Pending chronicle moments queue.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#10 of 15).
--
-- Buffer table that holds chronicle observation candidates BEFORE they are
-- promoted into team_chronicle_observations. The v5.3 chronicle pipeline:
--   1. detect candidate (stat anomaly / flashpoint / etc) -> insert here
--   2. quality_loop critic scores + voice validator
--   3. if confidence >= threshold, promote to team_chronicle_observations
--      with approval_state = 'auto_approved'
--   4. otherwise sit in /admin/queue for human review
-- This separation prevents low-confidence drafts from rendering.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS chronicle_moments_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER REFERENCES teams(team_id),
    program_slug TEXT,                              -- denormalized for fast filter
    season_year INTEGER,
    week INTEGER,
    card_type TEXT NOT NULL                         -- mirrors team_chronicle_observations.card_type
        CHECK (card_type IN (
            'anomaly','moment','flashpoint','echo','retroactive','player_arc'
        )),
    headline TEXT NOT NULL,
    body_md TEXT NOT NULL,
    stat_json TEXT,
    comparison_json TEXT,
    source_attribution TEXT,
    surprise_score REAL,
    state_signature TEXT,
    model_id TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    confidence REAL,                                 -- critic verdict 0..1
    validation_notes_json TEXT,
    queue_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (queue_status IN (
            'pending','approved','rejected','promoted','expired'
        )),
    decided_at_utc TEXT,
    decided_by TEXT,
    promoted_observation_id INTEGER,                 -- FK into team_chronicle_observations once promoted
    generated_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_chronicle_pending_status
    ON chronicle_moments_pending (queue_status, generated_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_chronicle_pending_team
    ON chronicle_moments_pending (team_id, season_year, week);

CREATE INDEX IF NOT EXISTS idx_chronicle_pending_program
    ON chronicle_moments_pending (program_slug, queue_status);

COMMIT;
