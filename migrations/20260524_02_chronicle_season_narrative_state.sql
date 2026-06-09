-- Chronicle: Season Narrative State
-- Per (team, season) memory of arc structure. Two stores by design:
--   1. season_narrative_state — one row per (team, season). JSON blobs of open / resolved /
--      unresolved arcs. Optimised for fast READ by the Planner ("what arcs are alive?").
--   2. season_narrative_arc — normalised per-arc rows. Optimised for batch analytics
--      ("how long do reversal arcs typically stay open?"). The JSON blob in (1) is the
--      cache; (2) is the source of truth for analytics.
--
-- Trade-off rationale: writing both adds ~2x storage cost per arc update, but the
-- read-path Planner needs sub-ms arc lookups and the analytics layer needs proper
-- WHERE/JOIN. SQLite json1 lets us avoid this duplication later if needed, but the
-- duplication is the explicit choice today.
--
-- FKs (documented):
--   team_id -> teams(team_id)
--   season_year -> seasons(season_year)

BEGIN;

CREATE TABLE IF NOT EXISTS season_narrative_state (
    team_id                      INTEGER NOT NULL,
    season_year                  INTEGER NOT NULL,
    open_arcs_json               TEXT    NOT NULL DEFAULT '[]',  -- [{arc_id, frame, opened_week, confirming_evidence[], disconfirming_evidence[], status, tension_score}, ...]
    resolved_arcs_json           TEXT    NOT NULL DEFAULT '[]',
    unresolved_tensions_json     TEXT    NOT NULL DEFAULT '[]',
    last_reconciled_at_week      INTEGER,
    last_reconciled_at_utc       TEXT,
    created_at_utc               TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at_utc               TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (team_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_season_narrative_state_reconciled
    ON season_narrative_state (season_year, last_reconciled_at_week);

CREATE TABLE IF NOT EXISTS season_narrative_arc (
    arc_id                       TEXT    PRIMARY KEY,             -- e.g., "auburn-2025-underdog-redemption"
    team_id                      INTEGER NOT NULL,
    season_year                  INTEGER NOT NULL,
    frame                        TEXT    NOT NULL,                -- thesis-level label
    status                       TEXT    NOT NULL CHECK (status IN ('open', 'closure_eligible', 'resolved', 'reversed')),
    opened_at_week               INTEGER NOT NULL,
    closed_at_week               INTEGER,
    tension_score                REAL    NOT NULL DEFAULT 0.0,
    confirming_evidence_count    INTEGER NOT NULL DEFAULT 0,
    disconfirming_evidence_count INTEGER NOT NULL DEFAULT 0,
    created_at_utc               TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at_utc               TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_season_narrative_arc_team_season_status
    ON season_narrative_arc (team_id, season_year, status);

CREATE INDEX IF NOT EXISTS idx_season_narrative_arc_status_closed
    ON season_narrative_arc (status, closed_at_week);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name IN ('season_narrative_state', 'season_narrative_arc');
