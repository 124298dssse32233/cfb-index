-- Rivalry Card (sprint 2) — historical head-to-head meetings + editorial commentary.
-- Writes are produced by src/cfb_rankings/team_pages/rivalry_data_loader.py.
-- The renderer reads last-10 meetings for a (program_a, program_b) pair and
-- draws the meetings list + derives all-time record + streak from these rows.
--
-- Design:
--  * Canonical keying — program_a_slug is always lexicographically ≤ program_b_slug
--    so each meeting is stored once regardless of which side the user lands on.
--  * game_id links to the underlying games row for score/venue lookup.
--  * commentary_text is the 1-sentence editorial note per meeting (LLM-generated
--    one-time per game; idempotent re-renders reuse the stored line).
--  * winner_slug, margin are denormalised from games for hot-path filtering
--    (streak computation, "N of the last M").
-- Idempotent. CREATE IF NOT EXISTS only.

create table if not exists team_rivalry_meetings (
    team_rivalry_meeting_id integer primary key autoincrement,
    program_a_slug text not null,                -- lex-lower slug
    program_b_slug text not null,                -- lex-higher slug
    game_id integer references games(game_id),
    season_year integer not null,
    week integer,
    game_date text,                              -- ISO8601 date (start_time_utc truncated)
    home_slug text,                              -- which side was home
    a_points integer,
    b_points integer,
    winner_slug text,                            -- a / b / tie / NULL if upcoming
    margin integer,                              -- (a_points - b_points), positive = A won
    venue text,
    commentary_text text,                        -- 1-sentence editorial note
    commentary_model_id text,
    is_complete integer not null default 1,     -- 0 = upcoming/scheduled
    generated_at_utc text not null default current_timestamp,
    unique (program_a_slug, program_b_slug, game_id)
);

create index if not exists idx_rivalry_pair
    on team_rivalry_meetings (program_a_slug, program_b_slug, season_year desc);
create index if not exists idx_rivalry_game
    on team_rivalry_meetings (game_id);
