-- Chronicle: Slop Observations
-- Batch-level drift detection metrics. After each generation batch (e.g., Sunday
-- flashpoint sweep for Week 12), we measure linguistic diversity and slop signals
-- across the whole batch, not just per-card. This catches:
--   * gradual drift toward AI-slop phrasing across many cards (per-card critics miss it)
--   * banlist phrases that crept past per-card filters
--   * em-dash overuse as a corpus-level tic
--   * 4-gram novelty collapse vs prior 4-week corpus
--
-- MTLD (Measure of Textual Lexical Diversity) is the canonical type-token-ratio
-- metric robust to text length. We track median + p25 + p75 to detect tail compression.
--
-- flagged_for_review=1 trips the manual-review workflow before the batch ships.
--
-- Query patterns:
--   * Batch lookup: WHERE batch_id=?
--   * Trend: WHERE created_at_utc >= ? ORDER BY created_at_utc DESC

BEGIN;

CREATE TABLE IF NOT EXISTS chronicle_slop_observations (
    obs_id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id                     TEXT    NOT NULL,                          -- e.g., "2026-w12-sunday-flashpoint"
    card_count                   INTEGER NOT NULL,
    mtld_median                  REAL,
    mtld_p25                     REAL,
    mtld_p75                     REAL,
    ngram_novelty_4gram          REAL,                                      -- vs prior 4-week corpus, 0-1
    slop_fingerprint_score       REAL,                                      -- count of banlist hits
    banlist_top_offenders_json   TEXT,                                      -- {"phrase": count, ...}
    em_dash_density_per_100w     REAL,
    flagged_for_review           INTEGER NOT NULL DEFAULT 0,
    created_at_utc               TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chronicle_slop_observations_batch
    ON chronicle_slop_observations (batch_id);

CREATE INDEX IF NOT EXISTS idx_chronicle_slop_observations_trend
    ON chronicle_slop_observations (created_at_utc);

CREATE INDEX IF NOT EXISTS idx_chronicle_slop_observations_flagged
    ON chronicle_slop_observations (flagged_for_review, created_at_utc);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='chronicle_slop_observations';
