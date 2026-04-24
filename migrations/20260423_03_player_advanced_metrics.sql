-- 20260423_03_player_advanced_metrics
-- Player-advanced-metric landing tables for Autopilot v1 TASK 1.4.
--
-- Kickoff brief (CLAUDE_CODE_KICKOFF_AUTOPILOT.md, TASK 1.4): persist
-- player-level advanced metrics (EPA/dropback, CPOE, pressure-to-sack,
-- 3rd-down EPA, red-zone TD%, aDOT, deep-ball, play-action splits,
-- scramble EPA, turnover-worthy-play rate, success rate, explosive-play
-- rate). Plus RB/WR variants as the data supports.
--
-- Schema decisions:
-- - Generic (player_id, season_year, week, metric_id) key so future
--   metric additions never require a migration.
-- - metric_id is a free-form TEXT. The canonical list of metric_ids
--   lives in src/cfb_rankings/metrics/player_advanced.py (METRICS registry).
-- - value is REAL. sample_size is INTEGER — "how many plays went into
--   this number?" — so consumers can apply a floor gate analogous to
--   the FI effective_n floor.
-- - cohort_id is an optional string (e.g. "p4_qbs_min_80_dropbacks") so
--   Signature Story can reference a pre-computed peer set.
-- - Season rollup is a separate table so the weekly table can keep its
--   row-count pure (13 metrics × ~1.2k QBs × ~20 weeks ≈ 300k/year is
--   fine for SQLite; we don't need a view).
-- - Additive migration, reversible (DROP TABLE). NO changes to existing
--   tables.

CREATE TABLE IF NOT EXISTS player_advanced_metrics (
    player_advanced_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id                 INTEGER NOT NULL,
    season_year               INTEGER NOT NULL,
    week                      INTEGER NOT NULL,            -- 0 = full-season rollup, 1..20 = regular + postseason
    metric_id                 TEXT NOT NULL,               -- e.g. 'epa_per_dropback'
    value                     REAL,                         -- NULL when sample_size insufficient
    sample_size               INTEGER NOT NULL DEFAULT 0,   -- plays / dropbacks / attempts behind the value
    cohort_id                 TEXT,                         -- optional peer cohort key
    metric_version            TEXT,                         -- algorithm version (semver)
    computed_at               TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pam_player_season_week_metric
    ON player_advanced_metrics(player_id, season_year, week, metric_id);

CREATE INDEX IF NOT EXISTS idx_pam_season_metric
    ON player_advanced_metrics(season_year, metric_id);

CREATE INDEX IF NOT EXISTS idx_pam_cohort_season
    ON player_advanced_metrics(cohort_id, season_year);


CREATE TABLE IF NOT EXISTS player_advanced_metrics_season (
    player_advanced_metrics_season_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id                 INTEGER NOT NULL,
    season_year               INTEGER NOT NULL,
    metric_id                 TEXT NOT NULL,
    value                     REAL,
    sample_size               INTEGER NOT NULL DEFAULT 0,
    cohort_id                 TEXT,
    percentile                REAL,                         -- within cohort_id, 0..100; NULL if cohort missing
    rank_in_cohort            INTEGER,
    cohort_size               INTEGER,
    metric_version            TEXT,
    computed_at               TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pams_player_season_metric
    ON player_advanced_metrics_season(player_id, season_year, metric_id);

CREATE INDEX IF NOT EXISTS idx_pams_season_metric
    ON player_advanced_metrics_season(season_year, metric_id);

CREATE INDEX IF NOT EXISTS idx_pams_cohort_season_metric
    ON player_advanced_metrics_season(cohort_id, season_year, metric_id);
