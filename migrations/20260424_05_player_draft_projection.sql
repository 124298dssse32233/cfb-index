-- 20260424_05_player_draft_projection
-- Mock-draft projections landing table — Autopilot v1 TASK 4.6.
-- PLAYER_PAGE_SEASON_PHASE_DESIGN.md §11.
--
-- One row per (player, source, snapshot_date). A player may accumulate
-- many snapshots as analysts update their boards through draft season.
-- projected_pick + projected_round capture the board position; a
-- future aggregator combines ~4 sources into a consensus band.
--
-- Additive, reversible (DROP TABLE). No changes to existing tables.

CREATE TABLE IF NOT EXISTS player_draft_projection (
    player_draft_projection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id           INTEGER NOT NULL,
    source_name         TEXT NOT NULL,                -- kiper | jeremiah | walter | cbs | etc.
    snapshot_date       TEXT NOT NULL,                -- YYYY-MM-DD of this mock release
    projected_round     INTEGER,
    projected_pick      INTEGER,                       -- overall pick
    projected_team_id   INTEGER,
    projected_team_name TEXT,
    overall_rank        INTEGER,                       -- analyst's Big Board rank (when published)
    position_rank       INTEGER,                       -- per-position rank (when published)
    confidence_note     TEXT,
    source_url          TEXT,
    raw_payload_json    TEXT,
    ingested_at_utc     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pdp_player_source_snapshot
    ON player_draft_projection(player_id, source_name, snapshot_date);

CREATE INDEX IF NOT EXISTS idx_pdp_snapshot_source
    ON player_draft_projection(snapshot_date, source_name);

CREATE INDEX IF NOT EXISTS idx_pdp_player
    ON player_draft_projection(player_id);
