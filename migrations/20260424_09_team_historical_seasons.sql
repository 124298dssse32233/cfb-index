-- Sprint 4 / Phase 2 — HistoricalSeasonDeepDive
-- One row per (team_slug, season_year) rendering as a "chapter" page at
-- output/site/teams/<slug>/seasons/<year>.html.
--
-- Spec: docs/design-system/13-modules-archive.md §HistoricalSeasonDeepDive.
-- Populated by src/cfb_rankings/team_pages/historical_season_content.py
-- (deterministic fallback) + the generate-historical-seasons CLI subcommand
-- (LLM path, Opus for editorial fields, Sonnet for moments).
--
-- Load-bearing design decisions:
--  * We key on `team_slug` (not team_id) because the bricks in season_arc_card.py
--    already link by slug (/teams/<slug>/seasons/<year>.html). Keeping the
--    slug as the natural key also survives CFBD team_id rotations.
--  * `defining_moments` is JSON: an array of {type, register, body}. Keeping
--    it in one column rather than a child table because it's a fixed-size
--    denormalised block (always 3 per season) read atomically per page.
--  * `pull_quote` is JSON: {text, source, date, is_generated}. `is_generated`
--    defaults to 0; when the LLM path produces a synthesized quote (no real
--    contemporaneous source found) the flag flips to 1 so downstream QA
--    can filter.
--  * `gap_year_flag` marks seasons where per-game data is unavailable (e.g.
--    Alabama 2017/2018 — CFP_HISTORY preserves the title but the games table
--    is empty). The renderer branches to the simplified layout for those.
-- Idempotent. CREATE IF NOT EXISTS only.

create table if not exists team_historical_seasons (
    team_historical_seasons_id integer primary key autoincrement,
    team_slug text not null,
    season_year integer not null,
    season_title text,                       -- evocative editorial phrase ("The Proof")
    season_thesis text,                      -- 1-2 sentences framing the season
    defining_moments_json text,              -- JSON array of 3 {type, register, body}
    pull_quote_json text,                    -- JSON {text, source, date, is_generated}
    legacy_paragraph text,                   -- "what it meant" closing
    gap_year_flag integer not null default 0,
    model_id text,                           -- 'claude-opus-4-7', 'template-fallback', etc.
    generated_at_utc text not null default current_timestamp,
    unique (team_slug, season_year)
);

create index if not exists idx_historical_seasons_slug_year
    on team_historical_seasons (team_slug, season_year);
