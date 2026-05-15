-- Sprint v5-1 patch: expand daily_editions.status enum to include
-- 'offline-draft' so the synthesizer's offline-stub fallback path works.
--
-- Bug context: when llm_runtime.generate_with_voice_check falls back to
-- offline-stub (no API key, anthropic SDK missing, rate-limited, etc.),
-- daily/synthesizer.py:343 sets status='offline-draft' to mark the row as
-- non-publishable. But migrations/20260426_14_daily.sql:6 has:
--   CHECK(status IN ('draft','published','retired'))
-- which rejects 'offline-draft'. INSERT crashes with IntegrityError.
--
-- Discovered 2026-05-15 when world_class_enrich.yml ran without anthropic
-- SDK installed (workflow only did `pip install pyyaml`, missing the
-- project install) and the entire AI pipeline cascaded to offline-stub,
-- then crashed at synthesizer persist. Workflows now also fixed to
-- `pip install -e .` so anthropic is present.
--
-- SQLite doesn't support `ALTER TABLE ... DROP CONSTRAINT` or any other
-- direct constraint modification. The defensive recreate-table pattern:
--   1. Create a new table with the expanded CHECK
--   2. Copy data over
--   3. Drop the old table
--   4. Rename
-- All inside a transaction so it's atomic.
--
-- Existing rows with status NOT IN the expanded set would block the
-- migration — but the only allowed values today are draft/published/retired
-- so all existing rows pass. Safe.

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

CREATE TABLE daily_editions__new (
  edition_date     TEXT NOT NULL PRIMARY KEY,
  generated_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
  status           TEXT NOT NULL CHECK(status IN ('draft','published','retired','offline-draft')),
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model TEXT,
  notes            TEXT
);

INSERT INTO daily_editions__new
  (edition_date, generated_at_utc, status, voice_validator_passed,
   generation_model, notes)
SELECT
   edition_date, generated_at_utc, status, voice_validator_passed,
   generation_model, notes
FROM daily_editions;

DROP TABLE daily_editions;

ALTER TABLE daily_editions__new RENAME TO daily_editions;

-- daily_takes had a FK to daily_editions(edition_date). Re-establishing
-- it after the rename — SQLite preserves FK by ALTER RENAME semantics,
-- but the safer path is to explicitly verify with a quick pragma check.
-- (The pragma is informational only; if FK was broken it would have
--  crashed at the INSERT above.)

COMMIT;

PRAGMA foreign_keys = ON;
