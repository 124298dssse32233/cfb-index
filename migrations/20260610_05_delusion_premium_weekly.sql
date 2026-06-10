-- Delusion Premium — fanbase belief vs betting-market title odds.
-- belief_score = Backometer (fan optimism, 0-100); market_pct = implied 2027
-- title probability from Polymarket (source_observations raw_payload outcomePrices).
-- delusion_index = belief percentile - market percentile within the contender
-- cohort (signed: + = fans believe more than the market, - = market darling).
-- The December "Sharpest Fanbase" calibration payoff is built on this weekly history.
-- Computed by `manage.py compute-delusion-premium`.
CREATE TABLE IF NOT EXISTS delusion_premium_weekly (
    delusion_premium_weekly_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id           INTEGER NOT NULL REFERENCES teams (team_id),
    season_year       INTEGER NOT NULL,
    week              INTEGER NOT NULL,
    week_start_date   TEXT,
    belief_score      REAL    NOT NULL,
    belief_low_signal INTEGER NOT NULL DEFAULT 0,
    belief_pctl       REAL    NOT NULL DEFAULT 0,
    market_pct        REAL    NOT NULL,
    market_pctl       REAL    NOT NULL DEFAULT 0,
    market_source     TEXT    NOT NULL DEFAULT 'polymarket',
    market_observed_at TEXT,
    delusion_index    REAL    NOT NULL DEFAULT 0,
    raw_gap           REAL    NOT NULL DEFAULT 0,
    cohort_size       INTEGER NOT NULL DEFAULT 0,
    rank              INTEGER,
    verdict           TEXT,
    computed_at_utc   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_delusion_premium_weekly_unique
  ON delusion_premium_weekly (team_id, season_year, week);
CREATE INDEX IF NOT EXISTS idx_delusion_premium_weekly_board
  ON delusion_premium_weekly (season_year, week, delusion_index);
