-- 20260424_04_player_signature_plays
-- Signature Bets S3.2 — per-player signature-moment cache.

CREATE TABLE IF NOT EXISTS player_signature_plays (
    player_id      INTEGER NOT NULL,
    season_year    INTEGER NOT NULL,
    game_id        INTEGER NOT NULL,
    week           INTEGER,
    metric_id      TEXT,
    stat_value     REAL,
    score          REAL,
    opponent_name  TEXT,
    home_away      TEXT,
    result_label   TEXT,
    gloss          TEXT,
    generated_at   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (player_id, season_year)
);
