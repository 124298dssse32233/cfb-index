-- Team Preview — Roster reload (transfer position flow + reload summary)
-- Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §1.3, §1.4
--
-- Hard product requirement (spec §10): transfer ADDITIONS and transfer LOSSES
-- are kept as separate columns, never collapsed into a single net number. The
-- position snapshot stores incoming and outgoing independently so a renderer
-- can show "added 3 OL / lost 2 OL" rather than "net +1 OL".

CREATE TABLE IF NOT EXISTS team_transfer_position_snapshot (
    team_transfer_position_snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id                    INTEGER NOT NULL REFERENCES teams(team_id),
    slug                       TEXT    NOT NULL,
    season_year                INTEGER NOT NULL,
    as_of_date                 TEXT    NOT NULL,
    position                   TEXT    NOT NULL,                 -- 'QB','RB','OL','DL', ... or 'UNK'
    incoming_count             INTEGER NOT NULL DEFAULT 0,
    incoming_avg_points        REAL,
    incoming_total_points      REAL,
    incoming_top_player_name   TEXT,
    incoming_top_player_rating REAL,
    outgoing_count             INTEGER NOT NULL DEFAULT 0,
    outgoing_avg_points        REAL,
    outgoing_total_points      REAL,
    outgoing_top_player_name   TEXT,
    outgoing_top_player_rating REAL,
    net_count                  INTEGER NOT NULL DEFAULT 0,
    net_points                 REAL,
    production_lost            REAL,
    production_added           REAL,
    starter_risk_flag          INTEGER NOT NULL DEFAULT 0,
    need_filled_flag           INTEGER NOT NULL DEFAULT 0,
    confidence_band            TEXT    NOT NULL DEFAULT 'unset'
        CHECK (confidence_band IN ('high', 'medium', 'low', 'unset')),
    created_at_utc             TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_transfer_position_snapshot_unique
    ON team_transfer_position_snapshot (team_id, season_year, as_of_date, position);

CREATE INDEX IF NOT EXISTS idx_team_transfer_position_snapshot_lookup
    ON team_transfer_position_snapshot (slug, season_year, as_of_date);


-- One row per team / season / as-of: the headline roster story. Keeps the four
-- reload signals distinct (spec §3.4): returning production, portal additions,
-- portal losses, draft/graduation loss — plus HS recruiting reload.
CREATE TABLE IF NOT EXISTS team_roster_reload_snapshot (
    team_roster_reload_snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id                    INTEGER NOT NULL REFERENCES teams(team_id),
    slug                       TEXT    NOT NULL,
    season_year                INTEGER NOT NULL,
    as_of_date                 TEXT    NOT NULL,
    returning_profile_label    TEXT,
    transfer_profile_label     TEXT,
    draft_loss_label           TEXT,
    recruiting_reload_label    TEXT,
    primary_pressure_position  TEXT,
    primary_repair_position    TEXT,
    reload_score               REAL,
    continuity_score           REAL,
    volatility_score           REAL,
    portal_addition_score      REAL,
    portal_loss_score          REAL,
    draft_loss_score           REAL,
    freshman_injection_score   REAL,
    summary_json               TEXT    NOT NULL DEFAULT '{}',
    confidence_band            TEXT    NOT NULL DEFAULT 'unset'
        CHECK (confidence_band IN ('high', 'medium', 'low', 'unset')),
    created_at_utc             TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_roster_reload_snapshot_unique
    ON team_roster_reload_snapshot (team_id, season_year, as_of_date);

CREATE INDEX IF NOT EXISTS idx_team_roster_reload_snapshot_lookup
    ON team_roster_reload_snapshot (slug, season_year, as_of_date);
