-- 20260424_01_hot_take_cache
-- Signature Bets S2.2 — Hot-Take Engine cache + editorial hold table.
--
-- `player_daily_hot_take`  :  one row per (player, date); latest
--                             selected take, defensibility quadruple,
--                             score. Idempotent per-day selection.
-- `hot_take_template_holds`:  deny-list populated by the editorial
--                             review workflow; templates listed here
--                             are skipped during take selection.

CREATE TABLE IF NOT EXISTS player_daily_hot_take (
    player_id       INTEGER NOT NULL,
    as_of_date      TEXT    NOT NULL,         -- YYYY-MM-DD
    template_id     TEXT    NOT NULL,
    metric_id       TEXT    NOT NULL,
    rendered_text   TEXT    NOT NULL,
    meta_json       TEXT    NOT NULL,         -- defensibility quadruple
    score           REAL    NOT NULL,
    generated_at    TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (player_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS hot_take_template_holds (
    template_id   TEXT    PRIMARY KEY,
    reason        TEXT    NOT NULL,
    held_at       TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
