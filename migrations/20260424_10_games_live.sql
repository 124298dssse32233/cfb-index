-- Sprint 6 — Live Gameday Mode infrastructure.
--
-- games_live is the polling target for the CFBD live-game adapter. One row
-- per (season_year, week, home_team_id, away_team_id) — the renderer pulls
-- from here to know whether a team is mid-game, just finalized, or whether
-- their previous game was within the 24h game-recap window.
--
-- The wp_timeseries_json blob carries an array of {t_seconds_since_kickoff,
-- home_wp, event} samples (~30s cadence during in-progress; one final sample
-- per scoring play). events_log_json carries the "what moved it" feed that
-- annotates the WP chart.

create table if not exists games_live (
    games_live_id integer primary key autoincrement,
    game_id integer references games(game_id),
    season_year integer not null,
    week integer,
    home_team_id integer references teams(team_id),
    away_team_id integer references teams(team_id),
    home_team_slug text not null,
    away_team_slug text not null,
    kickoff_at_utc text not null,
    status text not null check(status in ('scheduled','in_progress','final')),
    current_quarter integer,
    time_remaining text,
    home_score integer,
    away_score integer,
    home_wp real,
    last_play_text text,
    final_at_utc text,
    pre_game_spread_home real,           -- spread_home convention: negative = home favored
    wp_timeseries_json text,
    events_log_json text,
    simulated integer not null default 0,
    updated_at_utc text not null default current_timestamp
);

create unique index if not exists idx_games_live_unique
    on games_live (season_year, week, home_team_slug, away_team_slug);

create index if not exists idx_games_live_team_status
    on games_live (home_team_slug, status, final_at_utc);

create index if not exists idx_games_live_team_status_away
    on games_live (away_team_slug, status, final_at_utc);

create index if not exists idx_games_live_status_kickoff
    on games_live (status, kickoff_at_utc);

-- Render-job queue. Sprint 6 §1.3: on transition from in_progress→final, we
-- enqueue T+5/15/20/25/30/35/40/45 jobs. A worker (or simulate-game CLI)
-- consumes this in order. Idempotent — same (game_id, t_offset_minutes) is
-- a no-op insert.
create table if not exists games_live_render_queue (
    queue_id integer primary key autoincrement,
    games_live_id integer not null references games_live(games_live_id),
    team_slug text not null,
    t_offset_minutes integer not null,
    scheduled_at_utc text not null,
    completed_at_utc text,
    status text not null default 'pending' check(status in ('pending','running','done','failed')),
    last_error text,
    created_at_utc text not null default current_timestamp
);

create unique index if not exists idx_games_live_render_queue_unique
    on games_live_render_queue (games_live_id, team_slug, t_offset_minutes);

create index if not exists idx_games_live_render_queue_pending
    on games_live_render_queue (status, scheduled_at_utc);
