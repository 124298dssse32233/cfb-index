-- Sprint 14: The Daily — morning digest tables

CREATE TABLE IF NOT EXISTS daily_editions (
  edition_date     TEXT NOT NULL PRIMARY KEY,  -- 'YYYY-MM-DD' ET
  generated_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
  status           TEXT NOT NULL CHECK(status IN ('draft','published','retired')),
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model TEXT,
  notes            TEXT
);

CREATE TABLE IF NOT EXISTS daily_takes (
  edition_date  TEXT NOT NULL,
  rank_position INTEGER NOT NULL CHECK(rank_position IN (1,2,3)),
  headline      TEXT NOT NULL,
  body          TEXT NOT NULL,
  primary_entity_slug TEXT,           -- e.g., 'alabama' or 'caleb-williams'
  primary_entity_type TEXT,           -- 'team' | 'player' | 'conference' | 'event'
  source_count  INTEGER NOT NULL,
  cited_sources_json TEXT NOT NULL,   -- ["The Athletic — Stewart Mandel", ...]
  fueled_by_json TEXT NOT NULL,       -- {"wire_ids":[...], "thread_ids":[...], "pulse_spikes":[...]}
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model TEXT,
  PRIMARY KEY (edition_date, rank_position),
  FOREIGN KEY (edition_date) REFERENCES daily_editions(edition_date)
);

CREATE TABLE IF NOT EXISTS daily_inputs_snapshot (
  edition_date    TEXT NOT NULL PRIMARY KEY,
  wire_count      INTEGER NOT NULL,
  active_thread_count INTEGER NOT NULL,
  pulse_spike_count INTEGER NOT NULL,
  receipt_resolution_count INTEGER NOT NULL,
  inputs_json     TEXT NOT NULL,
  FOREIGN KEY (edition_date) REFERENCES daily_editions(edition_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_takes_entity
  ON daily_takes(primary_entity_slug, primary_entity_type);
