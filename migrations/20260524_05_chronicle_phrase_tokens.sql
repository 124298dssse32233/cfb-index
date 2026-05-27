-- Chronicle: Narrative Phrase Tokens + Claim Stack
-- Two related tables that power "quiet callback" voice:
--   1. narrative_phrase_tokens — recurring images / epithets / metric anchors.
--      Example: last week's "the metronome" reappears as "the metronome wobbled" with
--      no "as we noted last week" scaffolding. Pure stylistic callback.
--   2. narrative_claim_stack — prior takes. Only surfaced when CONTRADICTED.
--      Example: a Week 4 claim ("Auburn's defense is the SEC's best front seven") gets
--      reversed_at_week=8 when Week 8 evidence flips it. Only then does the Writer
--      acknowledge "what we said in Week 4 has not held up."
--
-- Together: quiet continuity when the story is steady, explicit reversal when it isn't.
--
-- FKs (documented):
--   entity_id -> players(player_id) when entity_kind='player'
--   entity_id -> teams(team_id) when entity_kind='team'
--   narrative_claim_stack.reversed_by_card_cache_key -> chronicle_card_cache.cache_key

BEGIN;

CREATE TABLE IF NOT EXISTS narrative_phrase_tokens (
    token_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_kind        TEXT    NOT NULL CHECK (entity_kind IN ('player', 'team')),
    entity_id          INTEGER NOT NULL,
    season_year        INTEGER NOT NULL,
    phrase             TEXT    NOT NULL,
    phrase_kind        TEXT    NOT NULL CHECK (phrase_kind IN ('epithet', 'metric_anchor', 'recurring_image', 'comparable')),
    first_used_week    INTEGER NOT NULL,
    last_used_week     INTEGER NOT NULL,
    use_count          INTEGER NOT NULL DEFAULT 1,
    is_retired         INTEGER NOT NULL DEFAULT 0,                          -- 1 if VoiceCritic flagged overuse
    created_at_utc     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_narrative_phrase_tokens_active
    ON narrative_phrase_tokens (entity_kind, entity_id, season_year, is_retired);

CREATE INDEX IF NOT EXISTS idx_narrative_phrase_tokens_phrase
    ON narrative_phrase_tokens (phrase);

CREATE TABLE IF NOT EXISTS narrative_claim_stack (
    claim_id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_kind                   TEXT    NOT NULL CHECK (entity_kind IN ('player', 'team')),
    entity_id                     INTEGER NOT NULL,
    season_year                   INTEGER NOT NULL,
    claim_summary                 TEXT    NOT NULL,                         -- <=200 chars
    claim_polarity                TEXT    NOT NULL CHECK (claim_polarity IN ('positive', 'negative', 'neutral')),
    set_at_week                   INTEGER NOT NULL,
    reversed_at_week              INTEGER,                                  -- null = still active
    reversed_by_card_cache_key    TEXT,                                     -- FK -> chronicle_card_cache.cache_key
    created_at_utc                TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (length(claim_summary) <= 200)
);

CREATE INDEX IF NOT EXISTS idx_narrative_claim_stack_active
    ON narrative_claim_stack (entity_kind, entity_id, season_year, reversed_at_week);

CREATE INDEX IF NOT EXISTS idx_narrative_claim_stack_reversed_by
    ON narrative_claim_stack (reversed_by_card_cache_key);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name IN ('narrative_phrase_tokens', 'narrative_claim_stack');
