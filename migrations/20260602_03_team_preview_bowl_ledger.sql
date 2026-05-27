-- Team Preview — All-time bowl record ledger
-- Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §1.5, §2.4
--
-- Render rule (spec §1.5): only a row with verification_status in
-- ('verified','single_source') may be labelled an ALL-TIME bowl record. When
-- no ledger row exists, the renderer must fall back to "recent postseason
-- record" or suppress — it must never present CFBD-era postseason data as
-- all-time. cfb_rankings.team_preview.bowl_ledger.resolve_bowl_record_display
-- encodes that rule; tests pin it.

CREATE TABLE IF NOT EXISTS team_bowl_record_ledger (
    team_bowl_record_ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id                    INTEGER REFERENCES teams(team_id),
    slug                       TEXT    NOT NULL,
    wins                       INTEGER NOT NULL DEFAULT 0,
    losses                     INTEGER NOT NULL DEFAULT 0,
    ties                       INTEGER NOT NULL DEFAULT 0,
    appearances                INTEGER,
    first_bowl_year            INTEGER,
    last_bowl_year             INTEGER,
    last_bowl_name             TEXT,
    last_bowl_result           TEXT,
    source_name                TEXT    NOT NULL,
    source_url                 TEXT,
    source_retrieved_at        TEXT,
    verification_status        TEXT    NOT NULL DEFAULT 'single_source'
        CHECK (verification_status IN ('verified', 'single_source', 'conflict', 'missing')),
    notes_json                 TEXT    NOT NULL DEFAULT '{}',
    created_at_utc             TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at_utc             TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_bowl_record_ledger_unique
    ON team_bowl_record_ledger (slug, source_name);

CREATE INDEX IF NOT EXISTS idx_team_bowl_record_ledger_team
    ON team_bowl_record_ledger (team_id);
