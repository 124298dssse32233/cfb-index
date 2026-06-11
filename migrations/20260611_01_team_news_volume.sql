-- team_news_volume: daily GDELT GKG article mention counts per team.
-- Written by the gdelt_gkg adapter (credential-free HTTP bulk-file path) and
-- also materialized from the BQ adapter's source_observations rows. Gives
-- page-level queries a fast lookup without a full source_observations scan.
--
-- source values:
--   'gdelt_gkg'     — HTTP masterfilelist bulk-file adapter (this module)
--   'gdelt_bq'      — BigQuery adapter (written post-hoc when BQ is enabled)
--   'gdelt_doc'     — legacy per-team DOC 2.0 API adapter
--
-- PK is (team_id, date, source) so rows from multiple adapter paths coexist
-- and can be compared; page layer picks max(mention_count) or prefers BQ.

CREATE TABLE IF NOT EXISTS team_news_volume (
    nvol_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id         INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    date            TEXT NOT NULL,          -- YYYY-MM-DD
    mention_count   INTEGER NOT NULL DEFAULT 0,
    source          TEXT NOT NULL DEFAULT 'gdelt_gkg',
    computed_at_utc TEXT NOT NULL,
    UNIQUE(team_id, date, source)
);

CREATE INDEX IF NOT EXISTS idx_tnv_team_date
    ON team_news_volume (team_id, date);

CREATE INDEX IF NOT EXISTS idx_tnv_date_team
    ON team_news_volume (date, team_id);
