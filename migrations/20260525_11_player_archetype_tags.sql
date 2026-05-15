-- Sprint v5-1 Day 3 — Player archetype taxonomy.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#11 of 15).
--
-- Backs the v5-10a player-page archetype frames ("Game Manager Plus",
-- "Air-Raid Trigger", "Bell-Cow Back", etc). Many-to-many: a player can
-- carry multiple archetype tags per season with different confidence
-- scores. Renderer reads top-N by confidence for the archetype badge.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS player_archetype_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_external_id TEXT NOT NULL,                -- CFBD player id (string, matches roster_entries.external_id)
    player_slug TEXT NOT NULL,
    season_year INTEGER NOT NULL,
    archetype_slug TEXT NOT NULL,                    -- e.g. 'game-manager-plus','air-raid-trigger'
    archetype_label TEXT NOT NULL,                   -- human display label
    position_group TEXT,                             -- 'QB','RB','WR','TE','OL','EDGE','LB','DB','ST'
    confidence REAL NOT NULL DEFAULT 0.0,            -- 0..1
    source TEXT NOT NULL DEFAULT 'auto'              -- 'auto'|'human'|'imported'
        CHECK (source IN ('auto','human','imported')),
    model_id TEXT,                                   -- model that emitted the tag
    rationale_md TEXT,                               -- short editorial blurb
    stat_json TEXT,                                  -- supporting stats blob
    is_primary INTEGER NOT NULL DEFAULT 0,           -- 1 = top archetype shown in hero badge
    assigned_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (player_external_id, season_year, archetype_slug)
);

CREATE INDEX IF NOT EXISTS idx_player_archetype_player_season
    ON player_archetype_tags (player_external_id, season_year, confidence DESC);

CREATE INDEX IF NOT EXISTS idx_player_archetype_slug
    ON player_archetype_tags (archetype_slug, season_year, confidence DESC);

CREATE INDEX IF NOT EXISTS idx_player_archetype_primary
    ON player_archetype_tags (player_slug, season_year)
    WHERE is_primary = 1;

CREATE INDEX IF NOT EXISTS idx_player_archetype_position
    ON player_archetype_tags (position_group, season_year, confidence DESC);

COMMIT;
