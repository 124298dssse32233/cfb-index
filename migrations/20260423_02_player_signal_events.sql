-- 20260423_02_player_signal_events
-- Live Signal Flow event store — Signature Bets S1.6 / §4 Bet #13.
-- Each row records a decaying event tied to a player (portal entry,
-- draft declaration, watch-list inclusion, Heisman odds swing, etc.).
-- The renderer on the player page surfaces any row whose
-- event_ts + decay_hours has not yet elapsed.
--
-- Idempotent: uses CREATE TABLE IF NOT EXISTS + dedup_key UNIQUE index
-- so backfills / retries never double-insert.

CREATE TABLE IF NOT EXISTS player_signal_events (
    player_signal_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id              INTEGER NOT NULL,
    event_type             TEXT    NOT NULL,      -- 'portal_entry', 'commit', 'injury', 'draft_declare', 'draft_pick',
                                                  -- 'watch_list', 'all_american', 'program_record', 'heisman_odds_swing',
                                                  -- 'major_news' (see src/cfb_rankings/bets/signal_flow.py for the canonical list)
    headline               TEXT    NOT NULL,      -- Render-ready headline, ≤ 80 chars
    sub_line               TEXT,                  -- Optional expanded line for the expanded bar state
    event_ts               TEXT    NOT NULL,      -- ISO8601 UTC (stored as TEXT per SQLite convention)
    decay_hours            REAL    NOT NULL DEFAULT 72.0,
    source_url             TEXT,                  -- Optional deep-link (beat article, odds board, etc.)
    source_name            TEXT,                  -- Human-readable source label
    event_data_json        TEXT,                  -- Optional payload for per-type expanded UI
    dedup_key              TEXT    NOT NULL,      -- Stable de-dup string; unique index below
    created_at             TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_signal_events_dedup
    ON player_signal_events(dedup_key);

CREATE INDEX IF NOT EXISTS idx_player_signal_events_player_ts
    ON player_signal_events(player_id, event_ts DESC);
