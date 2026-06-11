CREATE TABLE IF NOT EXISTS player_discourse_terms (
  pdesc_id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
  season_year INTEGER NOT NULL,
  term TEXT NOT NULL,
  term_rank INTEGER NOT NULL,
  window_count INTEGER NOT NULL,
  global_count INTEGER NOT NULL,
  z_score REAL NOT NULL,
  rate_ratio REAL NOT NULL,
  log2_ratio REAL NOT NULL,
  total_windows INTEGER NOT NULL,
  sample_quote TEXT,
  sample_quote_source TEXT,
  model_version TEXT NOT NULL DEFAULT 'discourse-descriptors-v1',
  computed_at_utc TEXT NOT NULL,
  UNIQUE(player_id, season_year, term)
);
CREATE INDEX IF NOT EXISTS idx_player_desc_player_season
  ON player_discourse_terms(player_id, season_year);
