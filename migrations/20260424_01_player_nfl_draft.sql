-- 20260424_01_player_nfl_draft
-- NFL Draft results landing table for Autopilot v1 TASK 4.5.
--
-- One row per drafted college player. Keyed on (draft_year, round, pick)
-- since pick is unique within a draft. player_id is nullable because CFBD
-- sometimes lacks a collegeId for smaller-school prospects; we keep the
-- row regardless so downstream analytics never silently drop a pick.
--
-- Additive migration, reversible (DROP TABLE). No changes to existing tables.

CREATE TABLE IF NOT EXISTS player_nfl_draft (
    player_nfl_draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_year          INTEGER NOT NULL,
    round               INTEGER NOT NULL,
    pick                INTEGER NOT NULL,             -- pick within round
    overall             INTEGER,                       -- pick overall (1..262ish)
    player_id           INTEGER,                       -- FK to players when resolvable
    player_name         TEXT,                          -- as published by source
    position            TEXT,                          -- QB/RB/WR/OL/DL/LB/DB/K/P/LS
    height_inches       INTEGER,
    weight_lbs          INTEGER,
    college_team_id     INTEGER,                       -- FK to teams when resolvable
    college_team_name   TEXT,
    college_conference  TEXT,
    nfl_team            TEXT NOT NULL,
    nfl_team_abbr       TEXT,
    source_name         TEXT NOT NULL DEFAULT 'cfbd',
    source_player_id    TEXT,                          -- e.g. CFBD collegeId
    raw_payload_json    TEXT,
    ingested_at_utc     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_player_nfl_draft_year_round_pick
    ON player_nfl_draft(draft_year, round, pick);

CREATE INDEX IF NOT EXISTS idx_player_nfl_draft_player
    ON player_nfl_draft(player_id) WHERE player_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_player_nfl_draft_year
    ON player_nfl_draft(draft_year);

CREATE INDEX IF NOT EXISTS idx_player_nfl_draft_college_team
    ON player_nfl_draft(college_team_id) WHERE college_team_id IS NOT NULL;
