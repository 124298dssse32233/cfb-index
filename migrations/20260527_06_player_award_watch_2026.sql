-- Wave 25 / Phase 1 — Player Award Watch 2026
--
-- Preseason 2026 award watch list mentions per player. Seeded from ESPN
-- way-too-early Heisman + Phil Steele projections + On3 returning QB
-- rankings. Refreshed automatically when official watch lists drop
-- June 15 - July 15 2026 (new ingest module, Wave 26).
--
-- Heisman is intentionally open to all positions including WR (Jeremiah
-- Smith 2026 archetype) and DB/LB (Charles Woodson 1997 precedent).

CREATE TABLE IF NOT EXISTS player_award_watch_2026 (
    player_id        INTEGER NOT NULL,
    season_year      INTEGER NOT NULL DEFAULT 2026,
    award_slug       TEXT    NOT NULL,   -- 'heisman','maxwell','davey_obrien','doak_walker','biletnikoff','mackey','nagurski','bednarik','butkus','thorpe','outland','rimington','lou_groza','ray_guy'
    list_type        TEXT    NOT NULL,   -- 'odds_top10','watchlist_official','media_predict','futures_book','position_ranking'
    position_rank    INTEGER,            -- 1-N within this list (e.g. #1 Heisman favorite)
    priority         INTEGER NOT NULL DEFAULT 5,   -- render order; lower = higher priority badge
    source           TEXT    NOT NULL,
    source_url       TEXT,
    as_of            TEXT    NOT NULL,
    notes            TEXT,
    PRIMARY KEY (player_id, season_year, award_slug, list_type)
);

CREATE INDEX IF NOT EXISTS idx_player_award_watch_2026_pid_pri
    ON player_award_watch_2026(player_id, priority);
CREATE INDEX IF NOT EXISTS idx_player_award_watch_2026_award
    ON player_award_watch_2026(award_slug, season_year);
