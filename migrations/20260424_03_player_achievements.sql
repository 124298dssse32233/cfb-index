-- 20260424_03_player_achievements
-- Signature Bets S2.7 — achievements taxonomy cache.

CREATE TABLE IF NOT EXISTS achievement_catalog (
    achievement_id  TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    icon_slug       TEXT NOT NULL,
    description     TEXT NOT NULL,
    target_rarity   REAL,
    position_filter TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS player_achievements (
    player_id       INTEGER NOT NULL,
    achievement_id  TEXT    NOT NULL,
    season_year     INTEGER NOT NULL,
    unlock_context  TEXT,
    rarity_pct      REAL,
    meta_json       TEXT,
    unlocked_at     TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (player_id, achievement_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_player_achievements_player
    ON player_achievements(player_id, season_year);
