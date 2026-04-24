-- 20260424_02_player_mirror_matches
-- Signature Bets S2.5 — Mirror Match cache. One row per (player,
-- season, match_slot). Idempotent via PRIMARY KEY + UPSERT.

CREATE TABLE IF NOT EXISTS player_mirror_matches (
    player_id              INTEGER NOT NULL,
    season_year            INTEGER NOT NULL,
    match_slot             INTEGER NOT NULL,   -- 1..k ordering
    match_player_id        INTEGER NOT NULL,
    match_season_year      INTEGER NOT NULL,
    similarity_pct         INTEGER NOT NULL,   -- 0..100
    feature_coverage_pct   INTEGER NOT NULL,   -- 0..100, non-median-fill share
    drivers_json           TEXT,               -- [{feature, self_pct, match_pct, delta}, …]
    generated_at           TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (player_id, season_year, match_slot)
);

CREATE INDEX IF NOT EXISTS idx_player_mirror_matches_player
    ON player_mirror_matches(player_id, season_year);
