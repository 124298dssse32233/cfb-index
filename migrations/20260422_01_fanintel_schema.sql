-- Fan Intelligence schema additions — STRATEGY §5 (2026-04-22).
-- Idempotent. Contains only CREATE TABLE / CREATE INDEX statements.
-- Column additions on existing tables live in cfb_rankings.migrations
-- (apply_runtime_migrations) because SQLite ALTER TABLE is not idempotent.

-- ------------------------------------------------------------------
-- schema_migrations: tracks which migration files have been applied.
-- ------------------------------------------------------------------
create table if not exists schema_migrations (
    migration_id text primary key,
    applied_at_utc text not null default current_timestamp,
    note text
);

-- ------------------------------------------------------------------
-- team_cohort_week: aggregated cohort-level sentiment per team-week.
-- Effective-N floor enforced in aggregator before write.
-- ------------------------------------------------------------------
create table if not exists team_cohort_week (
    team_id integer not null references teams(team_id),
    cohort text not null,
    week text not null,
    effective_n real not null,
    sentiment_score real,
    volume integer not null default 0,
    top_source_ids text,
    confidence_tier text not null,
    created_at_utc text not null default current_timestamp,
    updated_at_utc text not null default current_timestamp,
    primary key (team_id, cohort, week)
);

create index if not exists idx_team_cohort_week_week
    on team_cohort_week (week);
create index if not exists idx_team_cohort_week_team
    on team_cohort_week (team_id, week);

-- ------------------------------------------------------------------
-- team_cohort_divergence_week: cross-cohort stdev per team-week.
-- ------------------------------------------------------------------
create table if not exists team_cohort_divergence_week (
    team_id integer not null references teams(team_id),
    week text not null,
    divergence_score real,
    num_cohorts_qualifying integer not null default 0,
    created_at_utc text not null default current_timestamp,
    updated_at_utc text not null default current_timestamp,
    primary key (team_id, week)
);

create index if not exists idx_team_cohort_divergence_week_week
    on team_cohort_divergence_week (week);

-- ------------------------------------------------------------------
-- scrape_health: per-source per-run health beacon.
-- Read by `manage.py scrape-health`.
-- ------------------------------------------------------------------
create table if not exists scrape_health (
    source_id text not null,
    run_date text not null,
    rows_inserted integer,
    status text not null,
    error_message text,
    run_started_at_utc text,
    run_finished_at_utc text,
    adapter_version text,
    primary key (source_id, run_date)
);

create index if not exists idx_scrape_health_status
    on scrape_health (status, run_date);

-- ------------------------------------------------------------------
-- priority_teams: per-team config consumed by all adapters.
-- team_id is PK + FK to teams.
-- ------------------------------------------------------------------
create table if not exists priority_teams (
    team_id integer primary key references teams(team_id),
    rank_priority integer not null default 0,
    reddit_team_sub text,
    reddit_alumni_sub text,
    reddit_city_sub text,
    wiki_team_page text,
    wiki_coach_page text,
    wiki_qb_page text,
    google_news_query text,
    youtube_team_channel_id text,
    youtube_fan_channels text,
    bluesky_team_handle text,
    bluesky_beat_handles text,
    message_board_primary text,
    message_board_secondary text,
    campus_newspaper_feed text,
    substack_feeds text,
    beat_writer_rss text,
    athletic_dept_feed text,
    seatgeek_team_slug text,
    twitch_channels text,
    sports_radio_shows text,
    head_coach_bsky text,
    head_coach_ig text,
    tiktok_creators text,
    locked_on_rss text,
    needs_research integer not null default 0,
    last_config_refresh text,
    created_at_utc text not null default current_timestamp,
    updated_at_utc text not null default current_timestamp
);

create index if not exists idx_priority_teams_rank
    on priority_teams (rank_priority);
