-- Sprint 8.5: team/player pulse content cache
-- Stores LLM-generated themes + ledes so page renders read from DB,
-- not re-call the API on every build. One row per entity (slug+type).
CREATE TABLE IF NOT EXISTS team_pulse_cache (
    entity_slug         TEXT    NOT NULL,
    entity_type         TEXT    NOT NULL CHECK(entity_type IN ('team','player')),
    themes_json         TEXT,   -- JSON array of theme dicts
    lede                TEXT,
    lede_model          TEXT,
    voice_validator_passed INTEGER DEFAULT 0,
    generated_at_utc    TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (entity_slug, entity_type)
);
