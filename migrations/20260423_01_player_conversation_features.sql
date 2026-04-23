-- 20260423_01_player_conversation_features
-- Add player-scoped parallel to team_week_conversation_features so Feature B
-- ("The Room on [Player]") can aggregate mood by player_id, using the same
-- grammar and gates as the team-scope aggregates.
--
-- Schema decisions (see research/player_mention_sparsity_2026-04-22.md):
--   - `conversation_document_targets` already has player_id + target_type, so
--     the raw row-level data model is unchanged.
--   - This migration adds the aggregate/materialized parallel table only.
--   - Same bucket vocabulary as team scope: `fan|rival|national|media`.
--   - New column `top_quote_json` carries the representative pull-quote per
--     kickoff spec — team-scope didn't need this; player mood does.

CREATE TABLE IF NOT EXISTS player_week_conversation_features (
    player_week_conversation_feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_year               INTEGER NOT NULL,
    week                      INTEGER NOT NULL,
    player_id                 INTEGER NOT NULL,
    team_id                   INTEGER,                 -- player's affiliated team at time of mention
    source_name               TEXT,
    audience_bucket           TEXT NOT NULL,           -- fan | rival | national | media
    mention_count             INTEGER NOT NULL DEFAULT 0,
    unique_author_count       INTEGER NOT NULL DEFAULT 0,
    positive_doc_count        INTEGER NOT NULL DEFAULT 0,
    neutral_doc_count         INTEGER NOT NULL DEFAULT 0,
    negative_doc_count        INTEGER NOT NULL DEFAULT 0,
    mean_sentiment_score      REAL,
    net_sentiment_score       REAL,
    joy_share                 REAL,
    anger_share               REAL,
    fear_share                REAL,
    trust_share               REAL,
    sadness_share             REAL,
    surprise_share            REAL,
    attention_score           REAL,
    sample_quality_score      REAL,
    sarcasm_risk              TEXT,                    -- low|moderate|high
    top_storyline_json        TEXT,
    top_quote_json            TEXT,                    -- {text, author_pseudonym, source_url, sentiment_score}
    sample_n                  INTEGER,
    sample_window             TEXT,
    confidence_floor          TEXT,
    model_version             TEXT,
    created_at                TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pwcf_player_season_week
    ON player_week_conversation_features(player_id, season_year, week);

CREATE INDEX IF NOT EXISTS idx_pwcf_player_bucket
    ON player_week_conversation_features(player_id, audience_bucket, season_year, week);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pwcf_keys
    ON player_week_conversation_features(
        player_id, season_year, week, COALESCE(source_name, ''), audience_bucket
    );
