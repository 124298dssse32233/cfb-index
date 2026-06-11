-- Wave 4: Discourse Atlas cluster membership per (team, season)
CREATE TABLE IF NOT EXISTS team_discourse_clusters (
  cluster_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
  season_year INTEGER NOT NULL,
  cluster_id INTEGER NOT NULL,
  cluster_name TEXT NOT NULL,
  cluster_rank INTEGER NOT NULL,
  cluster_size INTEGER NOT NULL,
  shared_terms TEXT,
  model_version TEXT NOT NULL DEFAULT 'discourse-atlas-v1',
  computed_at_utc TEXT NOT NULL,
  UNIQUE(team_id, season_year)
);
CREATE INDEX IF NOT EXISTS idx_tdc_season
  ON team_discourse_clusters(season_year, cluster_id);
