-- Language Layer Wave-2: fanbase "Voice Profile" personality aggregates (A4).
--
-- Output of src/cfb_rankings/discourse/voice_profile.py: per (team, season) a
-- single aggregation over conversation_document_targets (joined to the fan-voice
-- corpus, same source filter + city-sub exclusion as keyness) of optimism /
-- joy / anger / doom / sarcasm, plus cohort percentile ranks computed at write
-- time among teams clearing the per-season mention floor. One row per
-- (team, season). The engine is idempotent: it clears the whole season before
-- insert (no stale below-floor rows) and writes ONLY cohort members.
--
-- *_mean / *_share are the raw aggregate measures; *_pct are 0-100 cohort
-- percentile ranks; optimism_rank is the 1-based dense rank within the cohort
-- (1 = most optimistic). cohort_size = teams in the season at/above the floor.
--
-- Query patterns:
--   * Voice render: WHERE team_id=? ORDER BY season_year DESC LIMIT 1
--   * Latest season: SELECT MAX(season_year) WHERE team_id=?

BEGIN;

CREATE TABLE IF NOT EXISTS fanbase_voice_profile (
    fanbase_voice_profile_id INTEGER PRIMARY KEY,
    team_id          INTEGER NOT NULL,
    season_year      INTEGER NOT NULL,
    n_mentions       INTEGER NOT NULL,            -- team-team targets in the season above floor
    optimism_mean    REAL    NOT NULL,            -- avg(sentiment_score) [-1..1]
    joy_share        REAL    NOT NULL,            -- share emotion_primary in (joy, optimism)
    anger_share      REAL    NOT NULL,            -- share emotion_primary in (anger, disgust)
    doom_share       REAL    NOT NULL,            -- share emotion_primary in (fear, sadness, pessimism)
    sarcasm_mean     REAL    NOT NULL,            -- avg(coalesce(sarcasm_score, 0)) [0..1]
    optimism_pct     INTEGER NOT NULL,            -- 0-100 cohort percentile
    joy_pct          INTEGER NOT NULL,
    anger_pct        INTEGER NOT NULL,
    doom_pct         INTEGER NOT NULL,
    sarcasm_pct      INTEGER NOT NULL,
    optimism_rank    INTEGER NOT NULL,            -- 1-based dense rank within cohort (1 = most optimistic)
    cohort_size      INTEGER NOT NULL,            -- teams at/above the floor this season
    model_version    TEXT    NOT NULL,            -- 'discourse-voice-v1'
    computed_at_utc  TEXT    NOT NULL,
    UNIQUE(team_id, season_year)
);

CREATE INDEX IF NOT EXISTS idx_fanbase_voice_profile_season
    ON fanbase_voice_profile (season_year, optimism_rank);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='fanbase_voice_profile';
