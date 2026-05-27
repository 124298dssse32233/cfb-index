-- Chronicle: Narrative Frame Stack
-- 3 to 5 immutable thesis sentences per player, set at Week 1, midseason-reviewable.
-- A "frame" is a long-arc thesis the Chronicle pipeline anchors all weekly cards against.
-- Frames are immutable once set, but can be SUPERSEDED at midseason (recorded, not deleted)
-- so we keep a full audit trail of how a player's story changed.
--
-- Query patterns:
--   * Active-frame lookup for Planner: WHERE player_id=? AND season_year=? AND superseded_at_week IS NULL
--   * Historical: WHERE player_id=? AND season_year=? ORDER BY frame_order, set_at_week
--
-- FKs (documented, not enforced per SQLite project convention):
--   player_id -> players(player_id)
--   season_year -> seasons(season_year)

BEGIN;

CREATE TABLE IF NOT EXISTS narrative_frame_stack (
    player_id                INTEGER NOT NULL,
    season_year              INTEGER NOT NULL,
    frame_id                 TEXT    NOT NULL,                              -- slug, e.g., "burdened_virtuoso"
    frame_text               TEXT    NOT NULL,                              -- the thesis sentence (<=200 chars)
    frame_order              INTEGER NOT NULL,                              -- 1-5 presentation order
    set_at_week              INTEGER NOT NULL,                              -- week the frame was established
    superseded_at_week       INTEGER,                                       -- null = active
    superseded_by_frame_id   TEXT,                                          -- replacement frame slug
    confidence               REAL    NOT NULL DEFAULT 1.0,
    created_at_utc           TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (player_id, season_year, frame_id),
    CHECK (frame_order BETWEEN 1 AND 5),
    CHECK (length(frame_text) <= 200)
);

CREATE INDEX IF NOT EXISTS idx_narrative_frame_stack_active
    ON narrative_frame_stack (player_id, season_year, superseded_at_week);

CREATE INDEX IF NOT EXISTS idx_narrative_frame_stack_set_week
    ON narrative_frame_stack (season_year, set_at_week);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='narrative_frame_stack';
