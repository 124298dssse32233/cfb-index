-- Canonical rivalry pairs — static bootstrap for the Rent Free pipeline.
-- Breaks the circular dependency where _load_rival_pairs read rivalry_obsession_weekly,
-- which is only written by compute-rivalry-ratios, which needs team_week_rival_mentions,
-- which _build_rival_mention_rows only populates for pairs from rivalry_obsession_weekly.
-- Seeded from seeds/rivalry_pairs.yaml via `manage.py seed-rivalry-pairs`.
CREATE TABLE IF NOT EXISTS rivalry_pairs (
    rivalry_pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rivalry_slug    TEXT    NOT NULL UNIQUE,
    rivalry_name    TEXT    NOT NULL,
    team_a_id       INTEGER NOT NULL REFERENCES teams (team_id),
    team_b_id       INTEGER NOT NULL REFERENCES teams (team_id),
    tier            TEXT    NOT NULL DEFAULT 'classic',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rivalry_pairs_team_a ON rivalry_pairs (team_a_id);
CREATE INDEX IF NOT EXISTS idx_rivalry_pairs_team_b ON rivalry_pairs (team_b_id);
