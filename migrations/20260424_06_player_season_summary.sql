-- 20260424_06_player_season_summary
-- Pre-computed per-season summary for the Development Trajectory chart
-- (PLAYER_PAGE_SEASON_PHASE_DESIGN §8.2 / Autopilot v1 TASK 7.3).
--
-- One row per (player_id, season_year). Carries the composite CFB Index
-- score and a JSON array of milestone markers to render as dots above
-- the trajectory line. Additive, reversible (DROP TABLE).

CREATE TABLE IF NOT EXISTS player_season_summary (
    player_season_summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id          INTEGER NOT NULL,
    season_year        INTEGER NOT NULL,
    team_id            INTEGER,
    position           TEXT,
    class_year         TEXT,
    cfb_index_score    REAL,                            -- 0..100 composite
    games_played       INTEGER,
    snap_count_proxy   INTEGER,                          -- usage share × games
    wepa_total         REAL,                             -- pass + rush WEPA aggregate
    milestones_json    TEXT,                             -- JSON array of {type,label,date}
    is_projected       INTEGER NOT NULL DEFAULT 0,       -- 1 for 2026 preseason projection
    computed_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pss_player_season
    ON player_season_summary(player_id, season_year);

CREATE INDEX IF NOT EXISTS idx_pss_season
    ON player_season_summary(season_year);

CREATE INDEX IF NOT EXISTS idx_pss_team_season
    ON player_season_summary(team_id, season_year) WHERE team_id IS NOT NULL;
