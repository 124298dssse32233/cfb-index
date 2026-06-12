-- Data Health Spine — snapshot persistence (Wave 0 active-guard layer).
-- ADDITIVE ONLY: two NEW tables in the data_health_* namespace. Never alters,
-- references, or touches any existing/product table — the checker keeps reading
-- the DATA tables strictly read-only; only snapshots.persist() opens a separate
-- read-WRITE connection and writes ONLY to these two tables.
--
-- Applied (and recorded once in schema_migrations) by the runner in
-- src/cfb_rankings/migrations.py apply_sql_migrations(), which globs every
-- migrations/*.sql file in name order. Pure CREATE IF NOT EXISTS, so it is also
-- safe to re-run before the runner has stamped it.
--
-- data_health_snapshot — one row per `verify_data_health.py --snapshot` run:
--   the run header + the computed gate. The normalized per-assertion rows live
--   in data_health_result, keyed by snapshot_id (run-header / result-rows split,
--   per the spec "Snapshot schema": a versioned JSON-shaped result set, NOT one
--   wide row).
--   db_fingerprint — cheap stable identity of the DATA db at run time (size +
--   mtime + a schema hash of a few spine tables). Defends the box-DB vs
--   cloud-artifact divergence class: two runs over different DBs fingerprint
--   differently even when the gate looks the same.
--   passrates_json / counts_json — the gate's passrates + counts dicts, stored
--   as JSON text (stdlib json; no new deps, no extra columns to migrate later).
CREATE TABLE IF NOT EXISTS data_health_snapshot (
    snapshot_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    run_utc        TEXT,
    overall        TEXT,
    db_fingerprint TEXT,
    passrates_json TEXT,
    counts_json    TEXT,
    summary        TEXT
);

CREATE INDEX IF NOT EXISTS idx_data_health_snapshot_run
  ON data_health_snapshot (run_utc);

-- data_health_result — the normalized CheckResult rows for one snapshot. One row
-- per assertion (check_id), mirroring data_health.checks.base.CheckResult minus
-- evidence_sql (kept out of persistence: it is reproducibility detail for the
-- live report, not trend state, and bloats the snapshot store). Diffing two
-- snapshots' freshness rows yields the source add/retire/newly-failing deltas
-- (no separate event-log table — derived, per the spec).
CREATE TABLE IF NOT EXISTS data_health_result (
    snapshot_id INTEGER,
    check_id    TEXT,
    pillar      TEXT,
    dataset     TEXT,
    season      INTEGER,
    status      TEXT,
    severity    TEXT,
    detail      TEXT
);

CREATE INDEX IF NOT EXISTS idx_data_health_result_snapshot
  ON data_health_result (snapshot_id);

CREATE INDEX IF NOT EXISTS idx_data_health_result_pillar
  ON data_health_result (snapshot_id, pillar);
