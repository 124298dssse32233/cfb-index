-- College football site data schema
-- Drafted for SportsDB + CFBD Tier 2 + derived models
-- Date: 2026-04-20
-- Target: PostgreSQL

create table levels (
  level_code text primary key,
  level_name text not null,
  sort_order int not null
);

create table conferences (
  conference_id bigserial primary key,
  conference_name text not null,
  conference_short_name text,
  level_code text not null references levels(level_code),
  subdivision text,
  is_active boolean not null default true
);

create table venues (
  venue_id bigserial primary key,
  venue_name text not null,
  city text,
  state text,
  country text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  altitude_ft int,
  capacity int,
  sportsdb_venue_id bigint
);

create table teams (
  team_id bigserial primary key,
  canonical_name text not null,
  school_name text,
  short_name text,
  slug text not null unique,
  level_code text not null references levels(level_code),
  current_conference_id bigint references conferences(conference_id),
  city text,
  state text,
  country text default 'USA',
  venue_id bigint references venues(venue_id),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table team_source_ids (
  team_source_id bigserial primary key,
  team_id bigint not null references teams(team_id),
  source_name text not null,
  source_team_id text not null,
  source_slug text,
  source_team_name text,
  is_primary boolean not null default false,
  unique (source_name, source_team_id)
);

create table seasons (
  season_year int primary key,
  season_label text,
  start_date date,
  end_date date
);

create table team_seasons (
  team_season_id bigserial primary key,
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  level_code text not null references levels(level_code),
  conference_id bigint references conferences(conference_id),
  head_coach text,
  offensive_coordinator text,
  defensive_coordinator text,
  official_preseason_rank int,
  official_preseason_rating numeric(8,3),
  continuity_proxy numeric(8,3),
  manual_offseason_points numeric(8,3) not null default 0,
  notes text,
  unique (team_id, season_year)
);

create table games (
  game_id bigserial primary key,
  season_year int not null references seasons(season_year),
  season_type text not null,
  week int,
  start_time_utc timestamptz,
  status text not null,
  neutral_site boolean not null default false,
  venue_id bigint references venues(venue_id),
  home_team_id bigint not null references teams(team_id),
  away_team_id bigint not null references teams(team_id),
  home_points int,
  away_points int,
  attendance int,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table game_source_ids (
  game_source_id bigserial primary key,
  game_id bigint not null references games(game_id),
  source_name text not null,
  source_game_id text not null,
  unique (source_name, source_game_id)
);

create index idx_games_season_week on games (season_year, season_type, week);
create index idx_games_home_team on games (home_team_id);
create index idx_games_away_team on games (away_team_id);

create table game_lines (
  game_line_id bigserial primary key,
  game_id bigint not null references games(game_id),
  provider text,
  spread_home_open numeric(8,3),
  spread_home_close numeric(8,3),
  total_open numeric(8,3),
  total_close numeric(8,3),
  moneyline_home_open int,
  moneyline_home_close int,
  moneyline_away_open int,
  moneyline_away_close int,
  line_timestamp_utc timestamptz
);

create unique index idx_game_lines_game_id on game_lines (game_id);

create table game_weather (
  game_weather_id bigserial primary key,
  game_id bigint not null unique references games(game_id),
  temperature_f numeric(5,2),
  wind_mph numeric(5,2),
  humidity_pct numeric(5,2),
  precipitation_mm numeric(6,2),
  conditions_text text
);

create table players (
  player_id bigserial primary key,
  full_name text not null,
  first_name text,
  last_name text,
  position text,
  hometown text,
  home_state text,
  created_at timestamptz not null default now()
);

create table player_source_ids (
  player_source_id bigserial primary key,
  player_id bigint not null references players(player_id),
  source_name text not null,
  source_player_id text not null,
  unique (source_name, source_player_id)
);

create table roster_entries (
  roster_entry_id bigserial primary key,
  player_id bigint not null references players(player_id),
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  jersey text,
  position text,
  class_year text,
  height_inches numeric(5,2),
  weight_lbs numeric(6,2),
  hometown text,
  home_city text,
  home_state text,
  home_country text,
  home_latitude numeric(9,6),
  home_longitude numeric(9,6),
  home_county_fips text,
  is_returning_player boolean,
  unique (player_id, team_id, season_year)
);

create table roster_source_snapshots (
  roster_source_snapshot_id bigserial primary key,
  player_id bigint references players(player_id),
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  source_name text not null default 'cfbd',
  source_player_id text not null default '',
  payload_json text not null,
  created_at timestamptz not null default now()
);

create unique index idx_roster_source_snapshots_unique
  on roster_source_snapshots (team_id, season_year, source_name, source_player_id);

create index idx_roster_source_snapshots_player
  on roster_source_snapshots (player_id, season_year);

create table recruiting_entries (
  recruiting_entry_id bigserial primary key,
  player_id bigint references players(player_id),
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  class_key text not null default 'team',
  stars int,
  rating numeric(8,4),
  position text,
  source_name text not null default 'cfbd'
);

create unique index idx_recruiting_entries_team_year_key
  on recruiting_entries (team_id, season_year, source_name, class_key);

create table team_talent_snapshots (
  team_talent_snapshot_id bigserial primary key,
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  talent_score numeric(8,3),
  talent_rank int,
  source_name text not null default 'cfbd',
  unique (team_id, season_year, source_name)
);

create table returning_production (
  returning_production_id bigserial primary key,
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  returning_total numeric(8,3),
  returning_offense numeric(8,3),
  returning_defense numeric(8,3),
  returning_qb numeric(8,3),
  returning_ol numeric(8,3),
  total_ppa numeric(10,3),
  total_passing_ppa numeric(10,3),
  total_receiving_ppa numeric(10,3),
  total_rushing_ppa numeric(10,3),
  percent_ppa numeric(8,5),
  percent_passing_ppa numeric(8,5),
  percent_receiving_ppa numeric(8,5),
  percent_rushing_ppa numeric(8,5),
  usage_rate numeric(8,5),
  passing_usage_rate numeric(8,5),
  receiving_usage_rate numeric(8,5),
  rushing_usage_rate numeric(8,5),
  source_name text not null default 'cfbd',
  unique (team_id, season_year, source_name)
);

create table transfer_entries (
  transfer_entry_id bigserial primary key,
  player_id bigint references players(player_id),
  season_year int not null references seasons(season_year),
  from_team_id bigint references teams(team_id),
  to_team_id bigint references teams(team_id),
  from_level_code text references levels(level_code),
  to_level_code text references levels(level_code),
  position text,
  rating numeric(8,4),
  transfer_points numeric(8,3),
  source_name text,
  notes text
);

create table official_rankings (
  official_ranking_id bigserial primary key,
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  week int,
  ranking_system text not null,
  region text,
  rank_value int,
  rating_value numeric(8,3)
);

create unique index idx_official_rankings_unique
  on official_rankings (team_id, season_year, week, ranking_system, coalesce(region, ''));

create table heisman_rankings_weekly (
  heisman_ranking_id bigserial primary key,
  season_year int not null references seasons(season_year),
  week int not null,
  player_id bigint not null references players(player_id),
  team_id bigint references teams(team_id),
  model_run_id bigint,
  source_name text not null default 'model',
  rank_overall int,
  nowcast_rank int,
  forecast_rank int,
  latent_score numeric(12,5),
  win_probability numeric(10,6),
  finalist_probability numeric(10,6),
  any_ballot_probability numeric(10,6),
  expected_ballot_share numeric(10,6),
  market_implied_probability numeric(10,6),
  market_american_odds int,
  market_provider text,
  notes text,
  created_at timestamptz not null default now()
);

create unique index idx_heisman_rankings_weekly_unique
  on heisman_rankings_weekly (season_year, week, player_id, model_run_id, source_name);

create index idx_heisman_rankings_weekly_board
  on heisman_rankings_weekly (season_year, week, rank_overall, nowcast_rank, forecast_rank);

create index idx_heisman_rankings_weekly_player
  on heisman_rankings_weekly (player_id, season_year, week);

create table heisman_vote_results (
  heisman_vote_result_id bigserial primary key,
  season_year int not null references seasons(season_year),
  player_id bigint not null references players(player_id),
  team_id bigint references teams(team_id),
  source_name text not null default 'official-heisman',
  place int,
  winner_flag boolean not null default false,
  finalist_flag boolean not null default false,
  first_place_votes int,
  second_place_votes int,
  third_place_votes int,
  total_points int,
  ballot_count int,
  notes text,
  created_at timestamptz not null default now()
);

create unique index idx_heisman_vote_results_unique
  on heisman_vote_results (season_year, player_id, source_name);

create index idx_heisman_vote_results_player
  on heisman_vote_results (player_id, season_year, place);

create table player_season_stats (
  player_season_stat_id bigserial primary key,
  season_year int not null references seasons(season_year),
  week int not null,
  season_type text not null default 'both',
  player_id bigint references players(player_id),
  team_id bigint references teams(team_id),
  source_name text not null default 'cfbd',
  source_player_id text not null default '',
  team_name text,
  player_name text,
  conference_name text,
  position text,
  category text not null,
  stat_type text not null,
  stat_value_text text,
  stat_value_num numeric(14,5),
  created_at timestamptz not null default now()
);

create unique index idx_player_season_stats_unique
  on player_season_stats (season_year, week, season_type, source_name, source_player_id, team_name, category, stat_type);

create index idx_player_season_stats_player
  on player_season_stats (player_id, season_year, week);

create index idx_player_season_stats_team
  on player_season_stats (team_id, season_year, week, category);

create table player_usage_season (
  player_usage_season_id bigserial primary key,
  season_year int not null references seasons(season_year),
  week int not null,
  player_id bigint references players(player_id),
  team_id bigint references teams(team_id),
  source_name text not null default 'cfbd',
  source_player_id text not null default '',
  team_name text,
  player_name text,
  conference_name text,
  position text,
  usage_overall numeric(10,6),
  usage_pass numeric(10,6),
  usage_rush numeric(10,6),
  usage_first_down numeric(10,6),
  usage_second_down numeric(10,6),
  usage_third_down numeric(10,6),
  usage_standard_downs numeric(10,6),
  usage_passing_downs numeric(10,6),
  created_at timestamptz not null default now()
);

create unique index idx_player_usage_season_unique
  on player_usage_season (season_year, week, source_name, source_player_id, team_name);

create index idx_player_usage_season_player
  on player_usage_season (player_id, season_year, week);

create index idx_player_usage_season_team
  on player_usage_season (team_id, season_year, week);

create table player_value_metrics (
  player_value_metric_id bigserial primary key,
  season_year int not null references seasons(season_year),
  week int not null,
  player_id bigint references players(player_id),
  team_id bigint references teams(team_id),
  source_name text not null default 'cfbd',
  source_player_id text not null default '',
  team_name text,
  player_name text,
  conference_name text,
  position text,
  metric_name text not null,
  metric_value numeric(14,5),
  plays int,
  created_at timestamptz not null default now()
);

create unique index idx_player_value_metrics_unique
  on player_value_metrics (season_year, week, source_name, metric_name, source_player_id, team_name);

create index idx_player_value_metrics_player
  on player_value_metrics (player_id, season_year, week, metric_name);

create index idx_player_value_metrics_team
  on player_value_metrics (team_id, season_year, week, metric_name);

create table heisman_market_odds_weekly (
  heisman_market_odds_id bigserial primary key,
  season_year int not null references seasons(season_year),
  week int not null,
  player_id bigint references players(player_id),
  team_id bigint references teams(team_id),
  provider text not null,
  source_name text not null default 'external-market',
  source_player_key text not null default '',
  player_name text,
  team_name text,
  market_name text not null default 'heisman',
  american_odds int,
  decimal_odds numeric(10,5),
  implied_probability numeric(10,6),
  notes text,
  created_at timestamptz not null default now()
);

create unique index idx_heisman_market_odds_weekly_unique
  on heisman_market_odds_weekly (season_year, week, provider, source_name, source_player_key, market_name);

create index idx_heisman_market_odds_weekly_player
  on heisman_market_odds_weekly (player_id, season_year, week, market_name);

create index idx_heisman_market_odds_weekly_lookup
  on heisman_market_odds_weekly (season_year, week, provider, market_name, player_name);

create table drives (
  drive_id bigserial primary key,
  game_id bigint not null references games(game_id),
  source_drive_id text,
  offense_team_id bigint not null references teams(team_id),
  defense_team_id bigint not null references teams(team_id),
  period int,
  drive_number int,
  start_yardline int,
  end_yardline int,
  play_count int,
  yards int,
  result text,
  points_scored int,
  is_garbage_time boolean not null default false
);

create index idx_drives_game on drives (game_id);
create index idx_drives_offense on drives (offense_team_id);
create unique index idx_drives_game_source on drives (game_id, source_drive_id);

create table plays (
  play_id bigserial primary key,
  game_id bigint not null references games(game_id),
  drive_id bigint references drives(drive_id),
  source_play_id text,
  offense_team_id bigint not null references teams(team_id),
  defense_team_id bigint not null references teams(team_id),
  period int,
  clock_minutes int,
  clock_seconds int,
  down int,
  distance int,
  yard_line int,
  play_type text,
  yards_gained int,
  epa numeric(10,4),
  ppa numeric(10,4),
  success_flag boolean,
  home_win_prob numeric(8,5),
  is_garbage_time boolean not null default false
);

create index idx_plays_game on plays (game_id);
create index idx_plays_drive on plays (drive_id);
create unique index idx_plays_game_source on plays (game_id, source_play_id);

create table team_game_advanced_stats (
  team_game_advanced_stat_id bigserial primary key,
  game_id bigint not null references games(game_id),
  team_id bigint not null references teams(team_id),
  opponent_team_id bigint not null references teams(team_id),
  offense_ppa numeric(10,4),
  defense_ppa numeric(10,4),
  success_rate_off numeric(8,5),
  success_rate_def numeric(8,5),
  explosiveness_off numeric(10,4),
  explosiveness_def numeric(10,4),
  rushing_ppa_off numeric(10,4),
  rushing_ppa_def numeric(10,4),
  passing_ppa_off numeric(10,4),
  passing_ppa_def numeric(10,4),
  finishing_drives_off numeric(10,4),
  finishing_drives_def numeric(10,4),
  havoc_off numeric(10,4),
  havoc_def numeric(10,4),
  field_position_off numeric(10,4),
  field_position_def numeric(10,4),
  source_name text not null default 'cfbd',
  unique (game_id, team_id, source_name)
);

create table opponent_adjusted_team_week (
  opponent_adjusted_team_week_id bigserial primary key,
  season_year int not null references seasons(season_year),
  week int not null,
  team_id bigint not null references teams(team_id),
  metric_name text not null,
  raw_value numeric(12,5),
  adjusted_value numeric(12,5),
  percentile numeric(8,5),
  sample_size int,
  model_version text not null,
  unique (season_year, week, team_id, metric_name, model_version)
);

create table model_runs (
  model_run_id bigserial primary key,
  model_name text not null,
  model_version text not null,
  season_year int not null references seasons(season_year),
  week int,
  data_cutoff_utc timestamptz not null,
  notes text,
  created_at timestamptz not null default now()
);

create table preseason_prior_components (
  preseason_prior_component_id bigserial primary key,
  season_year int not null references seasons(season_year),
  team_id bigint not null references teams(team_id),
  level_points numeric(8,3) not null default 0,
  conference_points numeric(8,3) not null default 0,
  prev_season_points numeric(8,3) not null default 0,
  program_baseline_points numeric(8,3) not null default 0,
  returning_production_points numeric(8,3) not null default 0,
  talent_points numeric(8,3) not null default 0,
  transfer_points numeric(8,3) not null default 0,
  coach_points numeric(8,3) not null default 0,
  qb_continuity_points numeric(8,3) not null default 0,
  continuity_proxy_points numeric(8,3) not null default 0,
  official_rank_points numeric(8,3) not null default 0,
  manual_offseason_points numeric(8,3) not null default 0,
  prior_mean numeric(8,3) not null,
  prior_sd numeric(8,3) not null,
  unique (season_year, team_id)
);

create table level_strength_weekly (
  level_strength_weekly_id bigserial primary key,
  model_run_id bigint not null references model_runs(model_run_id),
  level_code text not null references levels(level_code),
  level_mean numeric(8,3) not null,
  level_sd numeric(8,3),
  unique (model_run_id, level_code)
);

create table conference_strength_weekly (
  conference_strength_weekly_id bigserial primary key,
  model_run_id bigint not null references model_runs(model_run_id),
  conference_id bigint not null references conferences(conference_id),
  conference_mean numeric(8,3) not null,
  conference_sd numeric(8,3),
  unique (model_run_id, conference_id)
);

create table power_ratings_weekly (
  power_rating_weekly_id bigserial primary key,
  model_run_id bigint not null references model_runs(model_run_id),
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  week int not null,
  power_rating numeric(8,3) not null,
  offense_rating numeric(8,3) not null,
  defense_rating numeric(8,3) not null,
  special_teams_rating numeric(8,3) not null,
  tempo_rating numeric(8,3) not null,
  prior_mean numeric(8,3),
  posterior_sd numeric(8,3),
  cross_level_confidence numeric(8,3),
  schedule_connectivity numeric(8,3),
  unique (model_run_id, team_id, week)
);

create index idx_power_week on power_ratings_weekly (season_year, week, power_rating desc);

create table resume_ratings_weekly (
  resume_rating_weekly_id bigserial primary key,
  model_run_id bigint not null references model_runs(model_run_id),
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  week int not null,
  resume_score numeric(8,3) not null,
  record_strength_score numeric(8,3) not null,
  performance_over_expectation_score numeric(8,3) not null,
  result_quality_score numeric(8,3) not null,
  best_win_score numeric(8,3),
  worst_loss_score numeric(8,3),
  schedule_strength_score numeric(8,3),
  unique (model_run_id, team_id, week)
);

create index idx_resume_week on resume_ratings_weekly (season_year, week, resume_score desc);

create table strength_of_record_benchmarks (
  strength_of_record_benchmark_id bigserial primary key,
  model_run_id bigint not null references model_runs(model_run_id),
  team_id bigint not null references teams(team_id),
  benchmark_name text not null,
  benchmark_power numeric(8,3) not null,
  match_or_exceed_prob numeric(12,8) not null,
  score_value numeric(8,3) not null,
  unique (model_run_id, team_id, benchmark_name)
);

create table game_predictions (
  game_prediction_id bigserial primary key,
  model_run_id bigint not null references model_runs(model_run_id),
  game_id bigint not null references games(game_id),
  home_power_pre numeric(8,3),
  away_power_pre numeric(8,3),
  predicted_home_points numeric(8,3),
  predicted_away_points numeric(8,3),
  predicted_spread_home numeric(8,3),
  predicted_total numeric(8,3),
  home_win_probability numeric(8,5),
  upset_probability numeric(8,5),
  volatility numeric(8,3),
  unique (model_run_id, game_id)
);

create table team_rating_deltas (
  team_rating_delta_id bigserial primary key,
  model_run_id bigint not null references model_runs(model_run_id),
  game_id bigint not null references games(game_id),
  team_id bigint not null references teams(team_id),
  pregame_power numeric(8,3),
  postgame_power numeric(8,3),
  power_delta numeric(8,3),
  offense_delta numeric(8,3),
  defense_delta numeric(8,3),
  special_teams_delta numeric(8,3),
  resume_delta numeric(8,3),
  opponent_quality_effect numeric(8,3),
  dominance_effect numeric(8,3),
  garbage_time_discount numeric(8,3),
  location_effect numeric(8,3),
  explanation_json jsonb,
  unique (model_run_id, game_id, team_id)
);

create table manual_team_adjustments (
  manual_team_adjustment_id bigserial primary key,
  team_id bigint not null references teams(team_id),
  season_year int not null references seasons(season_year),
  week int,
  adjustment_scope text not null,
  points_delta numeric(8,3) not null,
  reason text not null,
  created_at timestamptz not null default now()
);

create index idx_team_source_ids_lookup on team_source_ids (source_name, source_team_id);
create index idx_player_source_ids_lookup on player_source_ids (source_name, source_player_id);
