-- Wave 4: KWIC fan-quote storage per (team, season, term)
CREATE TABLE IF NOT EXISTS team_discourse_term_quotes (
  quote_id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
  season_year INTEGER NOT NULL,
  week INTEGER NOT NULL DEFAULT 0,
  term TEXT NOT NULL,
  quote_text TEXT NOT NULL,
  quote_source TEXT,
  position_index INTEGER NOT NULL DEFAULT 0,
  computed_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tdtq_team_season_term
  ON team_discourse_term_quotes(team_id, season_year, week, term);
