-- Player Signature Story cache — Wave 8 of player-page upgrade.
--
-- Stores the LLM-generated 2-3 sentence narrative for the
-- #signature-story module on each player page. Generator inputs:
-- top Savant bars, CFB Index composite score, signature play,
-- standing rung. Content hash lets us invalidate when inputs change.

CREATE TABLE IF NOT EXISTS player_signature_story (
    player_id        INTEGER NOT NULL,
    season_year      INTEGER NOT NULL,
    content_hash     TEXT    NOT NULL,
    story_text       TEXT    NOT NULL,
    headline         TEXT,
    pull_quote       TEXT,
    model_id         TEXT,
    n_metrics_used   INTEGER,
    generated_at     TEXT    NOT NULL,
    PRIMARY KEY (player_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_player_signature_story_season
    ON player_signature_story(season_year);
