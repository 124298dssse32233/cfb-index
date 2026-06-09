-- CFBD play-by-play storage — Wave 10 of player-page upgrade.
--
-- One row per play from CFBD /plays endpoint. Raw fields preserved
-- verbatim so we can re-derive any new metric without re-fetching.
-- Player attribution is computed downstream by parsing play_text
-- into cfbd_pbp_play_actors (separate table).

CREATE TABLE IF NOT EXISTS cfbd_pbp_plays (
    play_id              TEXT PRIMARY KEY,         -- CFBD play id (string)
    game_id              INTEGER NOT NULL,
    drive_id             TEXT,
    season_year          INTEGER NOT NULL,
    week                 INTEGER NOT NULL,
    season_type          TEXT NOT NULL DEFAULT 'regular',
    play_number          INTEGER,
    drive_number         INTEGER,
    offense              TEXT,                      -- team name
    defense              TEXT,
    offense_conference   TEXT,
    defense_conference   TEXT,
    offense_score        INTEGER,
    defense_score        INTEGER,
    home_team            TEXT,
    away_team            TEXT,
    period               INTEGER,
    clock_minutes        INTEGER,
    clock_seconds        INTEGER,
    yardline             INTEGER,
    yards_to_goal        INTEGER,
    down                 INTEGER,
    distance             INTEGER,
    yards_gained         INTEGER,
    scoring              INTEGER,                   -- 0/1
    play_type            TEXT,
    play_text            TEXT,
    ppa                  REAL,                      -- Predicted Points Added (CFBD EPA)
    wallclock            TEXT,
    ingested_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pbp_game        ON cfbd_pbp_plays(game_id);
CREATE INDEX IF NOT EXISTS idx_pbp_offense     ON cfbd_pbp_plays(offense, season_year);
CREATE INDEX IF NOT EXISTS idx_pbp_defense     ON cfbd_pbp_plays(defense, season_year);
CREATE INDEX IF NOT EXISTS idx_pbp_season_week ON cfbd_pbp_plays(season_year, week);

-- Player-attribution rows. One row per (play_id, actor_player_id, role).
-- Populated by the play_text parser; a single play can produce multiple
-- rows (e.g. QB passer + WR receiver + DB tackler).

CREATE TABLE IF NOT EXISTS cfbd_pbp_play_actors (
    play_id          TEXT NOT NULL,
    actor_player_id  INTEGER,
    actor_name_raw   TEXT NOT NULL,                 -- raw from play_text
    role             TEXT NOT NULL,                 -- 'passer'|'rusher'|'receiver'|'target'|'tackler'|'sacker'|'interceptor'
    yards            INTEGER,
    is_complete      INTEGER,                       -- 0/1 for pass plays
    is_touchdown     INTEGER,                       -- 0/1
    is_interception  INTEGER,                       -- 0/1
    is_sack          INTEGER,                       -- 0/1
    air_yards        INTEGER,                       -- parsed when known
    yac              INTEGER,                       -- yards after catch when known
    ingested_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_actors_play   ON cfbd_pbp_play_actors(play_id);
CREATE INDEX IF NOT EXISTS idx_actors_player ON cfbd_pbp_play_actors(actor_player_id);
CREATE INDEX IF NOT EXISTS idx_actors_role   ON cfbd_pbp_play_actors(role);

-- Per-player advanced metrics derived from PBP. Mirrors the schema
-- shape of the existing-but-empty player_advanced_metrics_season,
-- but lives separately so we can recompute idempotently without
-- touching legacy rows.

CREATE TABLE IF NOT EXISTS player_pbp_metrics_season (
    player_id       INTEGER NOT NULL,
    season_year     INTEGER NOT NULL,
    metric_id       TEXT    NOT NULL,
    value           REAL    NOT NULL,
    sample_size     INTEGER,
    percentile      REAL,
    rank_in_cohort  INTEGER,
    cohort_size     INTEGER,
    computed_at     TEXT    NOT NULL,
    PRIMARY KEY (player_id, season_year, metric_id)
);

CREATE INDEX IF NOT EXISTS idx_ppm_season_metric
    ON player_pbp_metrics_season(season_year, metric_id);
