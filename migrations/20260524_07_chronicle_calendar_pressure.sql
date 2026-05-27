-- Chronicle: Calendar Pressure
-- A small per-(entity, week) vector that gives the Planner ~50 tokens of "what's
-- coming up?" context without forcing it to scan the full schedule table. The
-- Planner uses these flags to bias frame selection (rivalry week => surface
-- rivalry-specific arcs; anniversary => prefer retroactive cards).
--
-- is_decade_anniversary triggers when an exact-decade prior event matches the
-- current week (e.g., Week 7 2025 vs Week 7 2015 same matchup). The payload
-- carries enough context that the Writer can compose retroactive copy.
--
-- FKs (documented):
--   entity_id -> players(player_id) | teams(team_id)
--   season_year -> seasons(season_year)

BEGIN;

CREATE TABLE IF NOT EXISTS calendar_pressure (
    entity_kind                              TEXT    NOT NULL CHECK (entity_kind IN ('player', 'team')),
    entity_id                                INTEGER NOT NULL,
    season_year                              INTEGER NOT NULL,
    week_number                              INTEGER NOT NULL,
    weeks_to_rivalry                         INTEGER,
    rivalry_name                             TEXT,
    weeks_to_conf_championship_eligibility   INTEGER,
    season_defining_game_next                INTEGER NOT NULL DEFAULT 0,
    cfp_implication_weight                   REAL    NOT NULL DEFAULT 0.0,
    is_bye_week                              INTEGER NOT NULL DEFAULT 0,
    is_rivalry_week                          INTEGER NOT NULL DEFAULT 0,
    is_championship_week                     INTEGER NOT NULL DEFAULT 0,
    is_bowl_week                             INTEGER NOT NULL DEFAULT 0,
    is_decade_anniversary                    INTEGER NOT NULL DEFAULT 0,
    anniversary_payload_json                 TEXT,
    computed_at_utc                          TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (entity_kind, entity_id, season_year, week_number)
);

CREATE INDEX IF NOT EXISTS idx_calendar_pressure_rivalry_week
    ON calendar_pressure (season_year, week_number, is_rivalry_week);

CREATE INDEX IF NOT EXISTS idx_calendar_pressure_anniversary
    ON calendar_pressure (season_year, week_number, is_decade_anniversary);

CREATE INDEX IF NOT EXISTS idx_calendar_pressure_defining
    ON calendar_pressure (season_year, week_number, season_defining_game_next);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='calendar_pressure';
