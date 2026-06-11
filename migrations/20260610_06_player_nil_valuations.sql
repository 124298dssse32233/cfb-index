-- Player NIL valuation snapshots from On3 (and future sources).
-- Keyed by (player_id, as_of_date, source_name) so weekly scrapes
-- accumulate a historical series without duplicating.
CREATE TABLE IF NOT EXISTS player_nil_valuations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id      INTEGER NOT NULL REFERENCES players(player_id),
    as_of_date     TEXT    NOT NULL,  -- ISO date YYYY-MM-DD
    rank           INTEGER,           -- position in source ranking (1 = highest)
    valuation_usd  INTEGER,           -- estimated annual NIL value in dollars
    whisper_usd    INTEGER,           -- on3 "whisper" market rate, nullable
    source_name    TEXT    NOT NULL DEFAULT 'on3',
    source_url     TEXT,
    scraped_at     TEXT    NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_player_nil_snapshot
    ON player_nil_valuations (player_id, as_of_date, source_name);

CREATE INDEX IF NOT EXISTS ix_player_nil_player
    ON player_nil_valuations (player_id);

CREATE INDEX IF NOT EXISTS ix_player_nil_date
    ON player_nil_valuations (as_of_date DESC);
