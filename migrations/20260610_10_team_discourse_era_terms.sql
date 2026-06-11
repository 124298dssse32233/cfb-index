CREATE TABLE IF NOT EXISTS team_discourse_era_terms (
  era_term_id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
  season_year INTEGER NOT NULL,
  term TEXT NOT NULL,
  term_rank INTEGER NOT NULL,
  mention_count INTEGER NOT NULL,
  rest_count INTEGER NOT NULL,
  z_score REAL NOT NULL,
  rate_ratio REAL NOT NULL,
  log2_ratio REAL NOT NULL,
  magnitude_band TEXT NOT NULL CHECK(magnitude_band IN ('signature','characteristic','mild')),
  team_season_doc_count INTEGER NOT NULL,
  team_season_token_count INTEGER NOT NULL,
  sample_quote TEXT,
  sample_quote_source TEXT,
  model_version TEXT NOT NULL DEFAULT 'discourse-eras-v1',
  computed_at_utc TEXT NOT NULL,
  UNIQUE(team_id, season_year, term)
);
CREATE INDEX IF NOT EXISTS idx_era_terms_team_season
  ON team_discourse_era_terms(team_id, season_year);
