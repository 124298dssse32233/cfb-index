-- v5-7.5 foundation slice — confidence_calibration table.
-- Locked spec: docs/design-system/33-confidence-signaling.md
-- Module: src/cfb_rankings/confidence.py
--
-- Stores quarterly per-domain percentile thresholds that drive the
-- confidence-chip band on every named metric across the site. One row
-- per (domain, quarter). UPSERT on the unique constraint so the
-- recompute CLI is idempotent within a quarter.

CREATE TABLE IF NOT EXISTS confidence_calibration (
    calibration_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain                      TEXT NOT NULL,
    quarter                     TEXT NOT NULL,
    p10_threshold               INTEGER NOT NULL,
    p25_threshold               INTEGER NOT NULL,
    p75_threshold               INTEGER NOT NULL,
    sample_size_at_calibration  INTEGER NOT NULL,
    computed_at_utc             TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (domain IN ('fan_intel', 'historical', 'model', 'market', 'prediction')),
    CHECK (p10_threshold >= 0),
    CHECK (p25_threshold >= p10_threshold),
    CHECK (p75_threshold >= p25_threshold),
    CHECK (sample_size_at_calibration >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_confidence_calibration_domain_quarter
    ON confidence_calibration(domain, quarter);

CREATE INDEX IF NOT EXISTS idx_confidence_calibration_recent
    ON confidence_calibration(domain, computed_at_utc DESC);
