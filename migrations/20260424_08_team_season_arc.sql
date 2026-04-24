-- CFPEraView (sprint 3) — per-team-season archive row driving the 13-brick chapter index
-- and the dual-line trajectory chart on the team page.
-- Populated by src/cfb_rankings/team_pages/season_arc_loader.py.
--
-- Design notes:
--  * One row per (team_id, season_year). 2014 onward is the CFP era.
--  * ap_rank_final is the last-week AP ranking (NULL for seasons/teams outside
--    the current DB's 2020+ AP coverage).
--  * cfp_flag / title_game_flag are hand-annotated in the loader from canonical
--    CFP history — the DB's postseason flags alone can't reliably distinguish
--    a CFP semifinal loss from a standard bowl loss.
--  * quality_score is a 0-100 normalisation driven primarily by win%, boosted
--    by AP rank when available. Serves as the trajectory chart's mood proxy
--    until per-season historical fan-intel exists.
--  * brick_state is the pre-computed CSS class flag the renderer uses to pick
--    the brick colour (winning / peak / title-era / crisis / current).
-- Idempotent. CREATE IF NOT EXISTS only.

create table if not exists team_season_arc (
    team_season_arc_id integer primary key autoincrement,
    team_id integer not null references teams(team_id),
    season_year integer not null,
    wins integer not null default 0,
    losses integer not null default 0,
    ties integer not null default 0,
    win_pct real,                               -- wins / (wins+losses+ties)
    ap_rank_final integer,                      -- NULL if not polled / pre-AP coverage
    sp_plus_final real,                         -- power_ratings_weekly.power_rating, max week
    cfp_flag integer not null default 0,        -- 1 = program made CFP this season
    title_game_flag integer not null default 0, -- 1 = reached national championship game
    title_won_flag integer not null default 0,  -- 1 = won the national championship
    is_crisis integer not null default 0,       -- 1 = losing season (a visual cue)
    is_current integer not null default 0,      -- 1 = this is the most recent season for the team
    mood_score_avg real,                        -- season-mean net sentiment × 50 + 50 (0-100), NULL if no signal
    quality_score real,                         -- 0-100 computed; drives the SVG mood line when mood is NULL
    brick_state text,                           -- 'winning' | 'peak' | 'title-era' | 'crisis' | 'current' | 'baseline'
    bowl_game_name text,                        -- 'Rose Bowl' / 'CFP Championship' / null
    notes_json text,                            -- bag: { 'head_coach': ..., 'key_result': ... }
    generated_at_utc text not null default current_timestamp,
    unique (team_id, season_year)
);

create index if not exists idx_season_arc_team_year
    on team_season_arc (team_id, season_year);
create index if not exists idx_season_arc_cfp
    on team_season_arc (cfp_flag, season_year);
