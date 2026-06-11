-- Language Layer Wave-2: rivalry "Mirror" store (A3).
--
-- Output of the discourse mirror engine (src/cfb_rankings/discourse/mirror.py):
-- for a rivalry pair (T, R) it windows fan docs of T that mention R (+/-12 tokens
-- around the rival mention), strips all school-name words / both teams' structural
-- terms / stopwords / junk / generic seed, then contrasts side T-about-R vs side
-- R-about-T with the Wave-1 weighted log-odds. One row per surviving term per
-- (team, rival, season). The engine is idempotent per (team_id, rival_team_id,
-- season_year): it DELETEs the prior rows for that key before re-inserting.
--
-- side_token_count + rival_mention_doc_count carry the per-side volume so the
-- team-page Mirror module can disclose "N fan posts mention them / M mention us"
-- without a second query. sample_quote is a single toxicity-gated verbatim receipt.
--
-- Query patterns:
--   * Mirror render (this team's side): WHERE team_id=? AND season_year=? ORDER BY term_rank
--   * Reciprocal (rival's side):        WHERE team_id=<rival> AND rival_team_id=<this> AND season_year=?

BEGIN;

CREATE TABLE IF NOT EXISTS team_discourse_mirror (
    team_discourse_mirror_id INTEGER PRIMARY KEY,
    team_id                  INTEGER NOT NULL,           -- the side doing the talking
    rival_team_id            INTEGER NOT NULL,           -- the side being talked about
    season_year              INTEGER NOT NULL,
    term                     TEXT    NOT NULL,
    term_rank                INTEGER NOT NULL,           -- 1 = most distinctive on this side
    window_count             INTEGER NOT NULL,           -- raw count in this side's rival-mention windows
    z_score                  REAL    NOT NULL,
    side_token_count         INTEGER NOT NULL,           -- total window tokens on this side (volume disclosure)
    rival_mention_doc_count  INTEGER NOT NULL,           -- docs of T that mention R (volume disclosure)
    sample_quote             TEXT,                       -- one verbatim receipt (40-220 chars, toxicity-gated)
    sample_quote_source      TEXT,                       -- e.g. 'reddit/MichiganWolverines'
    model_version            TEXT    NOT NULL,           -- 'discourse-mirror-v1'
    computed_at_utc          TEXT    NOT NULL,
    UNIQUE(team_id, rival_team_id, season_year, term)
);

CREATE INDEX IF NOT EXISTS idx_team_discourse_mirror_rank
    ON team_discourse_mirror (team_id, rival_team_id, season_year, term_rank);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='team_discourse_mirror';
