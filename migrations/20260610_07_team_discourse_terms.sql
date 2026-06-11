-- Language Layer Wave-1: per-team distinctive-vocabulary store ("The Lexicon").
--
-- Output of the discourse keyness engine (src/cfb_rankings/discourse/keyness.py):
-- weighted log-odds w/ informative Dirichlet prior of each (team, season) fan-voice
-- corpus vs the same-season rest-of-corpus. One row per distinctive term per
-- (team, season, week-cut). week=0 is the season-level cut; week>0 is reserved for
-- future weekly cuts. The engine is idempotent per (team_id, season_year, week):
-- it DELETEs the prior rows for that key before re-inserting (see compute_team_keyness).
--
-- Receipts columns (team_doc_count / team_token_count) carry the corpus size so the
-- team-page renderer can apply confidence floors (>= 8 terms AND >= 200 docs) without
-- a second query. sample_quote is a single toxicity-gated verbatim receipt (<=220 chars).
--
-- Query patterns:
--   * Lexicon render: WHERE team_id=? AND season_year=? AND week=0 ORDER BY term_rank
--   * Latest season:  SELECT MAX(season_year) WHERE team_id=? AND week=0

BEGIN;

CREATE TABLE IF NOT EXISTS team_discourse_terms (
    team_discourse_term_id INTEGER PRIMARY KEY,
    team_id                INTEGER NOT NULL,
    season_year            INTEGER NOT NULL,
    week                   INTEGER NOT NULL DEFAULT 0,   -- 0 = season-cut; >0 reserved for weekly cuts
    term                   TEXT    NOT NULL,
    term_rank              INTEGER NOT NULL,             -- 1 = most distinctive
    mention_count          INTEGER NOT NULL,
    rest_count             INTEGER NOT NULL,
    z_score                REAL    NOT NULL,
    rate_ratio             REAL    NOT NULL,             -- plain "x the field" ratio
    log2_ratio             REAL    NOT NULL,
    magnitude_band         TEXT    NOT NULL,             -- 'signature' (>=10x) | 'characteristic' (3-10x) | 'mild' (<3x)
    team_doc_count         INTEGER NOT NULL,             -- corpus size receipts for confidence floors
    team_token_count       INTEGER NOT NULL,
    sample_quote           TEXT,                         -- one verbatim receipt (<=220 chars, toxicity-gated)
    sample_quote_source    TEXT,                         -- e.g. 'reddit/MichiganWolverines'
    model_version          TEXT    NOT NULL,             -- 'discourse-keyness-v1'
    computed_at_utc        TEXT    NOT NULL,
    UNIQUE(team_id, season_year, week, term)
);

CREATE INDEX IF NOT EXISTS idx_team_discourse_terms_rank
    ON team_discourse_terms (team_id, season_year, week, term_rank);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='team_discourse_terms';
