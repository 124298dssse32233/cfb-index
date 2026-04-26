-- Sprint 15: The Reaction Story — auto-triggered cohort divergence pieces

CREATE TABLE IF NOT EXISTS reaction_stories (
  slug              TEXT NOT NULL PRIMARY KEY,    -- e.g., 'arch-manning-leaves-texas'
  triggered_by_wire_id INTEGER NOT NULL,
  triggered_at_utc  TEXT NOT NULL,
  triggered_by_velocity REAL NOT NULL,
  primary_entity_slug TEXT NOT NULL,
  primary_entity_type TEXT NOT NULL CHECK(primary_entity_type IN ('team','player','coach','conference','event')),
  headline          TEXT NOT NULL,
  dek               TEXT NOT NULL,
  body              TEXT NOT NULL,
  surprise_index    REAL,                         -- 0–100
  status            TEXT NOT NULL CHECK(status IN ('draft','published','retired')),
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model  TEXT,
  cited_sources_json TEXT NOT NULL,
  notes             TEXT,
  FOREIGN KEY (triggered_by_wire_id) REFERENCES wire_entries(id)
);

CREATE TABLE IF NOT EXISTS reaction_cohort_splits (
  story_slug   TEXT NOT NULL,
  cohort       TEXT NOT NULL CHECK(cohort IN ('stat_folks','casual_fans','die_hards')),
  stance       TEXT NOT NULL,                     -- one-line summary of cohort take
  representative_quotes_json TEXT NOT NULL,       -- 2–3 verbatim quotes with attribution
  sentiment_score REAL,                           -- -1..+1 cohort mean
  volume_share REAL,                              -- share of total mention volume
  PRIMARY KEY (story_slug, cohort),
  FOREIGN KEY (story_slug) REFERENCES reaction_stories(slug)
);

CREATE INDEX IF NOT EXISTS idx_reactions_entity
  ON reaction_stories(primary_entity_slug, primary_entity_type);
CREATE INDEX IF NOT EXISTS idx_reactions_published
  ON reaction_stories(status, triggered_at_utc DESC);
