-- Aura — player perception (fan mentions) vs production (on-field value),
-- percentile-ranked within position cohort. aura_tax = perception - production
-- (positive = more hype than tape; negative = underrated). Fan Intelligence suite.
-- Computed by `manage.py compute-aura` from conversation_document_targets
-- (perception) + player_value_metrics (production, wepa_passing/rushing).
CREATE TABLE IF NOT EXISTS player_aura_weekly (
    player_aura_weekly_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id         INTEGER NOT NULL REFERENCES players (player_id),
    season_year       INTEGER NOT NULL,
    week              INTEGER NOT NULL,
    week_start_date   TEXT,
    position          TEXT    NOT NULL,
    cohort_label      TEXT    NOT NULL,
    cohort_size       INTEGER NOT NULL DEFAULT 0,
    mention_count     INTEGER NOT NULL DEFAULT 0,
    perception_pctl   REAL    NOT NULL DEFAULT 0,
    production_metric TEXT,
    production_value  REAL,
    production_plays  INTEGER,
    production_pctl   REAL    NOT NULL DEFAULT 0,
    aura_score        REAL    NOT NULL DEFAULT 0,
    aura_tax          REAL    NOT NULL DEFAULT 0,
    verdict           TEXT,
    is_low_signal     INTEGER NOT NULL DEFAULT 0,
    computed_at_utc   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_aura_weekly_unique
  ON player_aura_weekly (player_id, season_year, week);
CREATE INDEX IF NOT EXISTS idx_player_aura_weekly_board
  ON player_aura_weekly (season_year, week, aura_score);
