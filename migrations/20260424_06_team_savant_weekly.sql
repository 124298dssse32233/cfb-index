-- Team Savant (sprint 2) — pre-computed percentiles for the 13-metric Savant Card.
-- Writes are produced by src/cfb_rankings/team_pages/savant_data_loader.py.
-- The renderer reads back one-row-per-(team,season,week,metric) and inlines
-- each peer-set percentile as a data-attribute on the percentile bar so the
-- toggle can swap widths without re-hitting the server.
--
-- Idempotent. CREATE IF NOT EXISTS only.

create table if not exists team_savant_weekly (
    team_savant_weekly_id integer primary key autoincrement,
    team_id integer not null references teams(team_id),
    season_year integer not null references seasons(season_year),
    week integer not null,                       -- 0 = season-to-date; >0 = through-week-N snapshot
    metric_key text not null,                    -- 'epa_play' | 'success_rate_off' | ...
    metric_group text not null,                  -- 'offense' | 'defense' | 'special'
    metric_label text not null,                  -- 'EPA / play' (human label)
    is_inverted integer not null default 0,      -- 1 for defense (lower raw = better → invert before percentile)
    raw_value real,                              -- team's season-to-date mean of the underlying metric
    pct_vs_fbs real,                             -- 0..100 percentile vs. every FBS team that season
    pct_vs_p4 real,                              -- 0..100 percentile vs. Power-4 + Independents that season
    pct_vs_conf real,                            -- 0..100 percentile vs. team's current conference (same season)
    pct_vs_alltime real,                         -- 0..100 percentile vs. 2014+ all-FBS seasons for this program
    sample_size integer,                         -- games in this team-season that contributed
    peer_set_size_fbs integer,                   -- size of the FBS peer distribution
    peer_set_size_p4 integer,
    peer_set_size_conf integer,
    peer_set_size_alltime integer,
    generated_at_utc text not null default current_timestamp,
    unique (team_id, season_year, week, metric_key)
);

create index if not exists idx_savant_team_season_week
    on team_savant_weekly (team_id, season_year, week);
create index if not exists idx_savant_metric
    on team_savant_weekly (metric_key, season_year);
