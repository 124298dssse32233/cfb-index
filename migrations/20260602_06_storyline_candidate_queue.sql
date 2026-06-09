-- WS-12: data-driven storyline candidate queue.
--
-- Bridges the WS-02 narrative-arc machine (season_narrative_arc) to the
-- hand-authored editorial layer (storyline_threads). A populator ranks open
-- arcs by tension x frame-weight and writes them here as *proposed* candidates.
-- This is an editor's pull-list, NOT an auto-publish surface (per DECISIONS D-020:
-- narrative editorial stays in the human-reviewed lane).
--
-- Idempotency contract: candidate_id == arc_id (1:1 with the source arc). Re-runs
-- refresh the ranking fields but MUST preserve review_status, so an editor's
-- promoted/dismissed verdict is never clobbered by the daily populator.

CREATE TABLE IF NOT EXISTS storyline_candidate (
    candidate_id              TEXT    PRIMARY KEY,   -- == source arc_id
    arc_id                    TEXT    NOT NULL,
    team_id                   INTEGER NOT NULL,
    team_slug                 TEXT,
    season_year               INTEGER NOT NULL,
    frame                     TEXT    NOT NULL,
    arc_status                TEXT    NOT NULL,
    tension_score             REAL    NOT NULL DEFAULT 0.0,
    frame_weight              REAL    NOT NULL DEFAULT 0.0,
    priority_score            REAL    NOT NULL DEFAULT 0.0,
    confirming_evidence_count INTEGER NOT NULL DEFAULT 0,
    covered_by_thread         TEXT,                  -- active thread_slug already covering this team, else NULL
    review_status             TEXT    NOT NULL DEFAULT 'proposed'
                                  CHECK (review_status IN ('proposed', 'promoted', 'dismissed')),
    headline_hint             TEXT,
    created_at_utc            TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at_utc            TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_storyline_candidate_season_priority
    ON storyline_candidate (season_year, review_status, priority_score);

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name = 'storyline_candidate';
