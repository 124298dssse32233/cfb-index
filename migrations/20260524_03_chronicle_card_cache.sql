-- Chronicle: Card Cache
-- Canonical store for every generated card. Cache key is SHA-256(slug || week ||
-- card_type || evidence_hash || prompt_template_id || model_id || model_version ||
-- schema_version) truncated to 32 hex chars (128 bits — collision-safe at our volume).
--
-- Supersession model: when a card is regenerated with new evidence or a new prompt
-- template, the OLD row is left in place with superseded_at_utc set to now(), and a
-- NEW row is written with superseded_at_utc IS NULL. This lets us:
--   * answer "what was the active card for player X in week N at time T?" via temporal scan
--   * diff regenerations for prompt-template QA
--   * promote a known-good prior version back to LKG without resurrecting deleted rows
--
-- LKG (Last-Known-Good): when a generation pipeline fails Critic gates, the most
-- recent is_lkg=1 row for (slug, card_type) is served instead. LKG promotion is a
-- separate write that flips is_lkg=1 + lkg_promoted_at_utc.
--
-- Query patterns:
--   * Active-card render: WHERE slug=? AND season_year=? AND week_number=? AND card_type=? AND superseded_at_utc IS NULL
--   * LKG fallback: WHERE entity_kind=? AND slug=? AND card_type=? AND is_lkg=1 ORDER BY lkg_promoted_at_utc DESC LIMIT 1
--   * Trend analysis: WHERE card_type=? AND created_at_utc >= ?

BEGIN;

CREATE TABLE IF NOT EXISTS chronicle_card_cache (
    cache_key                    TEXT    PRIMARY KEY,                      -- sha256(...)[:32]
    slug                         TEXT    NOT NULL,                          -- player or team slug
    entity_kind                  TEXT    NOT NULL CHECK (entity_kind IN ('player', 'team', 'conference', 'rivalry')),
    season_year                  INTEGER,
    week_number                  INTEGER,
    card_type                    TEXT    NOT NULL,                          -- 'flashpoint' | 'player_arc' | 'echo' | 'retroactive' | 'heisman_trajectory' | 'moment_of_year' | 'devil_card'
    slot_index                   INTEGER,                                   -- 0-based slot on page (null = singleton)
    card_content_json            TEXT    NOT NULL,                          -- validated Pydantic JSON
    card_html                    TEXT,                                      -- optional pre-rendered HTML
    evidence_hash                TEXT    NOT NULL,                          -- sha256(sorted-JSON evidence)
    prompt_template_id           TEXT    NOT NULL,
    model_id                     TEXT    NOT NULL,
    model_version                TEXT    NOT NULL,
    schema_version               TEXT    NOT NULL,
    confidence_band              TEXT    NOT NULL CHECK (confidence_band IN ('high', 'medium', 'low', 'unset')),
    voice_critic_score           REAL,
    fact_critic_score            REAL,
    collision_critic_score       REAL,
    factscore_atomic             REAL,                                      -- FActScore atomic-fact-support
    word_count                   INTEGER,
    is_lkg                       INTEGER NOT NULL DEFAULT 0,                -- 1 = Last-Known-Good
    lkg_promoted_at_utc          TEXT,
    generation_attempt           INTEGER NOT NULL DEFAULT 1,
    wall_clock_ms                INTEGER,
    created_at_utc               TEXT    NOT NULL DEFAULT (datetime('now')),
    superseded_at_utc            TEXT                                       -- null = current
);

CREATE INDEX IF NOT EXISTS idx_chronicle_card_cache_active
    ON chronicle_card_cache (slug, season_year, week_number, card_type, superseded_at_utc);

CREATE INDEX IF NOT EXISTS idx_chronicle_card_cache_lkg
    ON chronicle_card_cache (entity_kind, is_lkg);

CREATE INDEX IF NOT EXISTS idx_chronicle_card_cache_trend
    ON chronicle_card_cache (card_type, created_at_utc);

CREATE INDEX IF NOT EXISTS idx_chronicle_card_cache_evidence
    ON chronicle_card_cache (evidence_hash);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='chronicle_card_cache';
