-- Lexicon term daily counts — curated fan-slang watchlist (Fan Intelligence suite).
-- Daily aggregates per term group, attributed to teams via conversation_document_targets.
-- Aggregates survive any future raw-text purge; written by `manage.py track-lexicon`.
-- team_id NULL = corpus-wide row. source_name 'all' = aggregated across sources.
CREATE TABLE IF NOT EXISTS lexicon_term_daily (
    lexicon_term_daily_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_group        TEXT    NOT NULL,
    as_of_date        TEXT    NOT NULL,
    season_year       INTEGER,
    week              INTEGER,
    team_id           INTEGER REFERENCES teams (team_id),
    source_name       TEXT    NOT NULL DEFAULT 'all',
    doc_count         INTEGER NOT NULL DEFAULT 0,
    mention_count     INTEGER NOT NULL DEFAULT 0,
    computed_at_utc   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_lexicon_term_daily_group_date
  ON lexicon_term_daily (term_group, as_of_date);
CREATE INDEX IF NOT EXISTS idx_lexicon_term_daily_team_date
  ON lexicon_term_daily (team_id, as_of_date);
