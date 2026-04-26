-- Sprint 16: The Mailbag — fan submission editorial

CREATE TABLE IF NOT EXISTS mailbag_submissions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  submitted_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
  submitter_email TEXT,                              -- nullable; we store if provided
  submitter_handle TEXT,                              -- "Andrew from Knoxville" — what we publish
  question_text   TEXT NOT NULL,
  topic_tags_json TEXT,                              -- ["realignment","sec","alabama"]
  status          TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','curated','answered','rejected','archived')),
  curator_notes   TEXT,
  rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS mailbag_editions (
  edition_slug    TEXT NOT NULL PRIMARY KEY,         -- '2026-w17' (Friday-anchored)
  publish_date    TEXT NOT NULL,                     -- 'YYYY-MM-DD'
  status          TEXT NOT NULL CHECK(status IN ('draft','published','retired')),
  generated_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
  notes           TEXT
);

CREATE TABLE IF NOT EXISTS mailbag_answers (
  edition_slug    TEXT NOT NULL,
  rank_position   INTEGER NOT NULL,                  -- 1..5
  submission_id   INTEGER NOT NULL,
  answer_body     TEXT NOT NULL,
  cited_sources_json TEXT NOT NULL,
  source_count    INTEGER NOT NULL,
  primary_topic   TEXT,
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model TEXT,
  PRIMARY KEY (edition_slug, rank_position),
  FOREIGN KEY (edition_slug) REFERENCES mailbag_editions(edition_slug),
  FOREIGN KEY (submission_id) REFERENCES mailbag_submissions(id)
);

CREATE INDEX IF NOT EXISTS idx_submissions_status
  ON mailbag_submissions(status, submitted_at_utc);
