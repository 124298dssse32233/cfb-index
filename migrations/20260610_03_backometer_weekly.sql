-- Backometer — weekly fanbase belief score (0-100) with named zones + hysteresis.
-- Computed by `manage.py compute-backometer` from team_week_conversation_features
-- (belief composite per fan_intelligence._belief_from_row, rescaled -100..100 -> 0..100).
-- zone is sticky: changes only when score crosses a boundary by >= 3 pts or holds
-- across 2 consecutive weeks (see docs/design-system/40-noir-subbrand.md §5).
CREATE TABLE IF NOT EXISTS backometer_weekly (
    backometer_weekly_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id          INTEGER NOT NULL REFERENCES teams (team_id),
    season_year      INTEGER NOT NULL,
    week             INTEGER NOT NULL,
    week_start_date  TEXT    NOT NULL,
    score            REAL    NOT NULL,
    zone             TEXT    NOT NULL,
    raw_zone         TEXT    NOT NULL,
    delta_wow        REAL,
    sample_size      INTEGER NOT NULL DEFAULT 0,
    source_count     INTEGER NOT NULL DEFAULT 0,
    is_low_signal    INTEGER NOT NULL DEFAULT 0,
    is_offseason     INTEGER NOT NULL DEFAULT 0,
    components_json  TEXT,
    annotations_json TEXT,
    computed_at_utc  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_backometer_weekly_unique
  ON backometer_weekly (team_id, season_year, week);
CREATE INDEX IF NOT EXISTS idx_backometer_weekly_week
  ON backometer_weekly (season_year, week);
