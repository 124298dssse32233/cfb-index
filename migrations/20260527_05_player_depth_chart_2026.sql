-- Wave 25 / Phase 1 — Player Depth Chart 2026
--
-- Per-player 2026 depth-chart slot. Seeded manually for top-100 marquee
-- players. Augmented later by On3/247 scrapes (Wave 26).

CREATE TABLE IF NOT EXISTS player_depth_chart_2026 (
    player_id        INTEGER NOT NULL,
    season_year      INTEGER NOT NULL DEFAULT 2026,
    position_group   TEXT    NOT NULL,    -- 'QB','RB','WR','TE','OL','DL','LB','DB','K','P'
    slot_rank        INTEGER NOT NULL,    -- 1=starter, 2=backup, 3=depth
    starter_status   TEXT    NOT NULL,    -- 'projected_starter','returning_starter','co_starter','backup','depth','camp_competition'
    confidence       TEXT    NOT NULL DEFAULT 'projected',   -- 'projected'|'confirmed'
    source           TEXT    NOT NULL,    -- 'manual_editorial'|'on3_scrape'|'247_scrape'|'athletic_site'|'inferred'
    source_url       TEXT,
    as_of            TEXT    NOT NULL,
    notes            TEXT,
    PRIMARY KEY (player_id, season_year, position_group)
);

CREATE INDEX IF NOT EXISTS idx_player_depth_chart_2026_pid
    ON player_depth_chart_2026(player_id);
