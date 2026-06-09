-- Team Preview — Core deterministic snapshot + season-path projection
-- Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §1.1, §1.2
-- Milestone A "truth layer". These tables are the deterministic fact bundle
-- every preview renderer consumes; LLM prose (claim cache, migration 04) sits
-- on top and never substitutes for these rows.
--
-- Idempotency: written via cfb_rankings.team_preview.persistence using
-- Database.upsert_many on the (team_id, season_year, as_of_date, ...) unique
-- keys below, so re-running a builder at the same as-of date overwrites in
-- place rather than appending duplicates.

CREATE TABLE IF NOT EXISTS team_preview_snapshot (
    team_preview_snapshot_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id                    INTEGER NOT NULL REFERENCES teams(team_id),
    slug                       TEXT    NOT NULL,
    season_year                INTEGER NOT NULL,
    as_of_date                 TEXT    NOT NULL,                 -- YYYY-MM-DD
    snapshot_kind              TEXT    NOT NULL DEFAULT 'offseason'
        CHECK (snapshot_kind IN ('offseason', 'preseason', 'live', 'postseason')),
    -- Prior completed season (latest season with a full game record; may lag
    -- the calendar year if regular-season games for the most recent year are
    -- not yet loaded — stored explicitly so the lag is never hidden).
    prior_season_year          INTEGER,
    prior_wins                 INTEGER,
    prior_losses               INTEGER,
    prior_ties                 INTEGER,
    prior_final_ap_rank        INTEGER,
    prior_final_coaches_rank   INTEGER,
    prior_final_cfp_rank       INTEGER,
    conference_id              INTEGER REFERENCES conferences(conference_id),
    conference_name            TEXT,
    is_independent             INTEGER NOT NULL DEFAULT 0,
    -- Schedule truth. schedule_known=0 means no future schedule is loaded for
    -- season_year; renderers must NOT invent a kickoff date in that case.
    schedule_known             INTEGER NOT NULL DEFAULT 0,
    first_game_id              INTEGER REFERENCES games(game_id),
    first_game_start_utc       TEXT,
    first_game_opponent_id     INTEGER REFERENCES teams(team_id),
    first_game_opponent_name   TEXT,
    -- Strength priors / class signals (best-available; source season recorded
    -- in source_fingerprint / missing_sources_json when it lags season_year).
    power_prior_rating         REAL,
    resume_prior_rating        REAL,
    talent_rank                INTEGER,
    talent_score               REAL,
    recruiting_rank            INTEGER,
    recruiting_score           REAL,
    returning_total            REAL,
    returning_offense          REAL,
    returning_defense          REAL,
    returning_qb               REAL,
    returning_ol               REAL,
    transfer_in_count          INTEGER NOT NULL DEFAULT 0,
    transfer_out_count         INTEGER NOT NULL DEFAULT 0,
    transfer_net_count         INTEGER NOT NULL DEFAULT 0,
    drafted_count              INTEGER NOT NULL DEFAULT 0,
    draft_capital_lost         REAL,
    confidence_band            TEXT    NOT NULL DEFAULT 'unset'
        CHECK (confidence_band IN ('high', 'medium', 'low', 'unset')),
    missing_sources_json       TEXT    NOT NULL DEFAULT '[]',
    source_fingerprint         TEXT,
    created_at_utc             TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at_utc             TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_preview_snapshot_unique
    ON team_preview_snapshot (team_id, season_year, as_of_date, snapshot_kind);

CREATE INDEX IF NOT EXISTS idx_team_preview_snapshot_season
    ON team_preview_snapshot (season_year, as_of_date);

CREATE INDEX IF NOT EXISTS idx_team_preview_snapshot_slug
    ON team_preview_snapshot (slug, season_year);


-- Final-season-aware floor / base / ceiling. One row per scenario. The record
-- math must stay internally consistent (enforced by
-- cfb_rankings.team_preview.season_path.validate_projection):
--   * national_champion  => postseason_losses = 0 (won out)
--   * any other CFP path  => exactly one postseason loss (the elimination game)
--   * independents        => conference_title_game = 0, result = 'none'
--   * bowl/CFP path appears only when the regular-season projection supports it
CREATE TABLE IF NOT EXISTS team_season_path_projection (
    team_season_path_projection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id                    INTEGER NOT NULL REFERENCES teams(team_id),
    slug                       TEXT    NOT NULL,
    season_year                INTEGER NOT NULL,
    as_of_date                 TEXT    NOT NULL,
    scenario                   TEXT    NOT NULL
        CHECK (scenario IN ('floor', 'base', 'ceiling')),
    regular_season_wins        INTEGER NOT NULL,
    regular_season_losses      INTEGER NOT NULL,
    conference_title_game      INTEGER NOT NULL DEFAULT 0,
    conference_title_result    TEXT    NOT NULL DEFAULT 'none'
        CHECK (conference_title_result IN ('win', 'loss', 'none')),
    bowl_or_cfp_path           TEXT    NOT NULL DEFAULT 'none'
        CHECK (bowl_or_cfp_path IN (
            'none', 'bowl', 'cfp_first_round', 'cfp_quarterfinal',
            'cfp_semifinal', 'cfp_title', 'national_champion')),
    postseason_wins            INTEGER NOT NULL DEFAULT 0,
    postseason_losses          INTEGER NOT NULL DEFAULT 0,
    final_wins                 INTEGER NOT NULL,
    final_losses               INTEGER NOT NULL,
    final_ties                 INTEGER NOT NULL DEFAULT 0,
    path_label                 TEXT,
    rationale                  TEXT,
    model_version              TEXT    NOT NULL DEFAULT 'season_path_v1',
    confidence_band            TEXT    NOT NULL DEFAULT 'unset'
        CHECK (confidence_band IN ('high', 'medium', 'low', 'unset')),
    source_fingerprint         TEXT,
    created_at_utc             TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_season_path_projection_unique
    ON team_season_path_projection (team_id, season_year, as_of_date, scenario, model_version);

CREATE INDEX IF NOT EXISTS idx_team_season_path_projection_lookup
    ON team_season_path_projection (slug, season_year, as_of_date, scenario);
