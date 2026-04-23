pragma foreign_keys = on;

create table if not exists levels (
  level_code text primary key,
  level_name text not null,
  sort_order integer not null
);

create table if not exists conferences (
  conference_id integer primary key autoincrement,
  conference_name text not null,
  conference_short_name text,
  level_code text not null references levels(level_code),
  subdivision text,
  is_active integer not null default 1
);

create table if not exists venues (
  venue_id integer primary key autoincrement,
  venue_name text not null,
  city text,
  state text,
  country text,
  latitude real,
  longitude real,
  altitude_ft integer,
  capacity integer,
  sportsdb_venue_id integer
);

create table if not exists teams (
  team_id integer primary key autoincrement,
  canonical_name text not null,
  school_name text,
  short_name text,
  slug text not null unique,
  level_code text not null references levels(level_code),
  current_conference_id integer references conferences(conference_id),
  city text,
  state text,
  country text default 'USA',
  venue_id integer references venues(venue_id),
  is_active integer not null default 1,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists team_source_ids (
  team_source_id integer primary key autoincrement,
  team_id integer not null references teams(team_id),
  source_name text not null,
  source_team_id text not null,
  source_slug text,
  source_team_name text,
  is_primary integer not null default 0,
  unique (source_name, source_team_id)
);

create table if not exists seasons (
  season_year integer primary key,
  season_label text,
  start_date text,
  end_date text
);

create table if not exists team_seasons (
  team_season_id integer primary key autoincrement,
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  level_code text not null references levels(level_code),
  conference_id integer references conferences(conference_id),
  head_coach text,
  offensive_coordinator text,
  defensive_coordinator text,
  official_preseason_rank integer,
  official_preseason_rating real,
  continuity_proxy real,
  manual_offseason_points real not null default 0,
  notes text,
  unique (team_id, season_year)
);

create table if not exists team_aliases (
  team_alias_id integer primary key autoincrement,
  team_id integer not null references teams(team_id),
  alias_text text not null,
  alias_normalized text not null,
  alias_type text not null default 'manual',
  season_year integer references seasons(season_year),
  source_name text not null default 'manual',
  is_active integer not null default 1,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_team_aliases_unique
  on team_aliases (team_id, alias_normalized, alias_type, season_year);

create index if not exists idx_team_aliases_lookup
  on team_aliases (alias_normalized, season_year, is_active);

create table if not exists games (
  game_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  season_type text not null,
  season_phase text,
  week integer,
  source_week integer,
  start_time_utc text,
  status text not null,
  neutral_site integer not null default 0,
  venue_id integer references venues(venue_id),
  home_team_id integer not null references teams(team_id),
  away_team_id integer not null references teams(team_id),
  home_points integer,
  away_points integer,
  attendance integer,
  notes text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists game_source_ids (
  game_source_id integer primary key autoincrement,
  game_id integer not null references games(game_id),
  source_name text not null,
  source_game_id text not null,
  unique (source_name, source_game_id)
);

create index if not exists idx_games_season_week on games (season_year, season_type, week);
create index if not exists idx_games_home_team on games (home_team_id);
create index if not exists idx_games_away_team on games (away_team_id);

create table if not exists game_lines (
  game_line_id integer primary key autoincrement,
  game_id integer not null references games(game_id),
  provider text,
  spread_home_open real,
  spread_home_close real,
  total_open real,
  total_close real,
  moneyline_home_open integer,
  moneyline_home_close integer,
  moneyline_away_open integer,
  moneyline_away_close integer,
  line_timestamp_utc text
);

create unique index if not exists idx_game_lines_game_id on game_lines (game_id);

create table if not exists game_line_snapshots (
  game_line_snapshot_id integer primary key autoincrement,
  game_id integer not null references games(game_id),
  provider text not null,
  source_name text not null default 'cfbd',
  spread_home real,
  total_points real,
  moneyline_home integer,
  moneyline_away integer,
  snapshot_time_utc text not null,
  raw_payload_json text,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_game_line_snapshots_unique
  on game_line_snapshots (game_id, provider, source_name, snapshot_time_utc);

create index if not exists idx_game_line_snapshots_game
  on game_line_snapshots (game_id, snapshot_time_utc);

create table if not exists game_weather (
  game_weather_id integer primary key autoincrement,
  game_id integer not null unique references games(game_id),
  temperature_f real,
  wind_mph real,
  humidity_pct real,
  precipitation_mm real,
  conditions_text text
);

create table if not exists players (
  player_id integer primary key autoincrement,
  full_name text not null,
  first_name text,
  last_name text,
  position text,
  hometown text,
  home_state text,
  created_at text not null default current_timestamp
);

create table if not exists player_source_ids (
  player_source_id integer primary key autoincrement,
  player_id integer not null references players(player_id),
  source_name text not null,
  source_player_id text not null,
  unique (source_name, source_player_id)
);

create table if not exists player_aliases (
  player_alias_id integer primary key autoincrement,
  player_id integer not null references players(player_id),
  team_id integer references teams(team_id),
  season_year integer references seasons(season_year),
  alias_text text not null,
  alias_normalized text not null,
  alias_type text not null default 'manual',
  source_name text not null default 'manual',
  is_active integer not null default 1,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_player_aliases_unique
  on player_aliases (player_id, alias_normalized, alias_type, season_year);

create index if not exists idx_player_aliases_lookup
  on player_aliases (alias_normalized, season_year, team_id, is_active);

create table if not exists roster_entries (
  roster_entry_id integer primary key autoincrement,
  player_id integer not null references players(player_id),
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  jersey text,
  position text,
  class_year text,
  height_inches real,
  weight_lbs real,
  hometown text,
  home_city text,
  home_state text,
  home_country text,
  home_latitude real,
  home_longitude real,
  home_county_fips text,
  is_returning_player integer,
  unique (player_id, team_id, season_year)
);

create table if not exists roster_source_snapshots (
  roster_source_snapshot_id integer primary key autoincrement,
  player_id integer references players(player_id),
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  source_name text not null default 'cfbd',
  source_player_id text not null default '',
  payload_json text not null,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_roster_source_snapshots_unique
  on roster_source_snapshots (team_id, season_year, source_name, source_player_id);

create index if not exists idx_roster_source_snapshots_player
  on roster_source_snapshots (player_id, season_year);

create table if not exists player_recruiting_profiles (
  player_recruiting_profile_id integer primary key autoincrement,
  player_id integer references players(player_id),
  season_year integer not null references seasons(season_year),
  recruit_type text,
  source_name text not null default 'cfbd',
  source_recruit_id text not null default '',
  source_athlete_id text,
  team_id integer references teams(team_id),
  school_name text,
  committed_team text,
  position text,
  stars integer,
  rating real,
  national_rank integer,
  height_inches real,
  weight_lbs real,
  city text,
  state_province text,
  country text,
  latitude real,
  longitude real,
  county_fips text,
  notes text,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_player_recruiting_profiles_unique
  on player_recruiting_profiles (source_name, source_recruit_id);

create index if not exists idx_player_recruiting_profiles_player
  on player_recruiting_profiles (player_id, season_year);

create index if not exists idx_player_recruiting_profiles_team
  on player_recruiting_profiles (team_id, season_year);

create table if not exists recruiting_entries (
  recruiting_entry_id integer primary key autoincrement,
  player_id integer references players(player_id),
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  class_key text not null default 'team',
  stars integer,
  rating real,
  position text,
  source_name text not null default 'cfbd'
);

create unique index if not exists idx_recruiting_entries_team_year_key
  on recruiting_entries (team_id, season_year, source_name, class_key);

create table if not exists team_talent_snapshots (
  team_talent_snapshot_id integer primary key autoincrement,
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  talent_score real,
  talent_rank integer,
  source_name text not null default 'cfbd',
  unique (team_id, season_year, source_name)
);

create table if not exists returning_production (
  returning_production_id integer primary key autoincrement,
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  returning_total real,
  returning_offense real,
  returning_defense real,
  returning_qb real,
  returning_ol real,
  total_ppa real,
  total_passing_ppa real,
  total_receiving_ppa real,
  total_rushing_ppa real,
  percent_ppa real,
  percent_passing_ppa real,
  percent_receiving_ppa real,
  percent_rushing_ppa real,
  usage_rate real,
  passing_usage_rate real,
  receiving_usage_rate real,
  rushing_usage_rate real,
  source_name text not null default 'cfbd',
  unique (team_id, season_year, source_name)
);

create table if not exists transfer_entries (
  transfer_entry_id integer primary key autoincrement,
  player_id integer references players(player_id),
  season_year integer not null references seasons(season_year),
  from_team_id integer references teams(team_id),
  to_team_id integer references teams(team_id),
  from_level_code text references levels(level_code),
  to_level_code text references levels(level_code),
  position text,
  rating real,
  transfer_points real,
  transfer_stars integer,
  transfer_date text,
  eligibility text,
  from_team_name text,
  to_team_name text,
  source_name text,
  notes text
);

create table if not exists player_honors (
  player_honor_id integer primary key autoincrement,
  player_id integer not null references players(player_id),
  season_year integer not null references seasons(season_year),
  week integer,
  team_id integer references teams(team_id),
  conference_name text,
  honor_scope text not null,
  honor_name text not null,
  selector text,
  honor_team text,
  position text,
  placement integer,
  consensus_flag integer not null default 0,
  unanimous_flag integer not null default 0,
  source_name text not null default 'manual',
  source_url text,
  notes text,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_player_honors_unique
  on player_honors (
    player_id,
    season_year,
    week,
    honor_scope,
    honor_name,
    selector,
    honor_team,
    position,
    source_name
  );

create index if not exists idx_player_honors_player
  on player_honors (player_id, season_year, honor_scope, week);

create table if not exists official_rankings (
  official_ranking_id integer primary key autoincrement,
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  week integer,
  ranking_system text not null,
  region text,
  rank_value integer,
  rating_value real
);

create unique index if not exists idx_official_rankings_unique
  on official_rankings (team_id, season_year, week, ranking_system, ifnull(region, ''));

create table if not exists heisman_rankings_weekly (
  heisman_ranking_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  week integer not null,
  player_id integer not null references players(player_id),
  team_id integer references teams(team_id),
  model_run_id integer,
  source_name text not null default 'model',
  rank_overall integer,
  nowcast_rank integer,
  forecast_rank integer,
  latent_score real,
  win_probability real,
  finalist_probability real,
  any_ballot_probability real,
  expected_ballot_share real,
  market_implied_probability real,
  market_american_odds integer,
  market_provider text,
  notes text,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_heisman_rankings_weekly_unique
  on heisman_rankings_weekly (season_year, week, player_id, model_run_id, source_name);

create index if not exists idx_heisman_rankings_weekly_board
  on heisman_rankings_weekly (season_year, week, rank_overall, nowcast_rank, forecast_rank);

create index if not exists idx_heisman_rankings_weekly_player
  on heisman_rankings_weekly (player_id, season_year, week);

create table if not exists heisman_vote_results (
  heisman_vote_result_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  player_id integer not null references players(player_id),
  team_id integer references teams(team_id),
  source_name text not null default 'official-heisman',
  place integer,
  winner_flag integer not null default 0,
  finalist_flag integer not null default 0,
  first_place_votes integer,
  second_place_votes integer,
  third_place_votes integer,
  total_points integer,
  ballot_count integer,
  notes text,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_heisman_vote_results_unique
  on heisman_vote_results (season_year, player_id, source_name);

create index if not exists idx_heisman_vote_results_player
  on heisman_vote_results (player_id, season_year, place);

create table if not exists player_season_stats (
  player_season_stat_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  week integer not null,
  season_type text not null default 'both',
  player_id integer references players(player_id),
  team_id integer references teams(team_id),
  source_name text not null default 'cfbd',
  source_player_id text not null default '',
  team_name text,
  player_name text,
  conference_name text,
  position text,
  category text not null,
  stat_type text not null,
  stat_value_text text,
  stat_value_num real,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_player_season_stats_unique
  on player_season_stats (season_year, week, season_type, source_name, source_player_id, team_name, category, stat_type);

create index if not exists idx_player_season_stats_player
  on player_season_stats (player_id, season_year, week);

create index if not exists idx_player_season_stats_team
  on player_season_stats (team_id, season_year, week, category);

create table if not exists player_usage_season (
  player_usage_season_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  week integer not null,
  player_id integer references players(player_id),
  team_id integer references teams(team_id),
  source_name text not null default 'cfbd',
  source_player_id text not null default '',
  team_name text,
  player_name text,
  conference_name text,
  position text,
  usage_overall real,
  usage_pass real,
  usage_rush real,
  usage_first_down real,
  usage_second_down real,
  usage_third_down real,
  usage_standard_downs real,
  usage_passing_downs real,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_player_usage_season_unique
  on player_usage_season (season_year, week, source_name, source_player_id, team_name);

create index if not exists idx_player_usage_season_player
  on player_usage_season (player_id, season_year, week);

create index if not exists idx_player_usage_season_team
  on player_usage_season (team_id, season_year, week);

create table if not exists player_value_metrics (
  player_value_metric_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  week integer not null,
  player_id integer references players(player_id),
  team_id integer references teams(team_id),
  source_name text not null default 'cfbd',
  source_player_id text not null default '',
  team_name text,
  player_name text,
  conference_name text,
  position text,
  metric_name text not null,
  metric_value real,
  plays integer,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_player_value_metrics_unique
  on player_value_metrics (season_year, week, source_name, metric_name, source_player_id, team_name);

create index if not exists idx_player_value_metrics_player
  on player_value_metrics (player_id, season_year, week, metric_name);

create index if not exists idx_player_value_metrics_team
  on player_value_metrics (team_id, season_year, week, metric_name);

create table if not exists heisman_market_odds_weekly (
  heisman_market_odds_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  week integer not null,
  player_id integer references players(player_id),
  team_id integer references teams(team_id),
  provider text not null,
  source_name text not null default 'external-market',
  source_player_key text not null default '',
  player_name text,
  team_name text,
  market_name text not null default 'heisman',
  american_odds integer,
  decimal_odds real,
  implied_probability real,
  notes text,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_heisman_market_odds_weekly_unique
  on heisman_market_odds_weekly (season_year, week, provider, source_name, source_player_key, market_name);

create index if not exists idx_heisman_market_odds_weekly_player
  on heisman_market_odds_weekly (player_id, season_year, week, market_name);

create index if not exists idx_heisman_market_odds_weekly_lookup
  on heisman_market_odds_weekly (season_year, week, provider, market_name, player_name);

create table if not exists prediction_market_snapshots (
  prediction_market_snapshot_id integer primary key autoincrement,
  provider text not null,
  source_name text not null default 'prediction-market',
  market_key text not null,
  market_type text not null,
  event_key text,
  season_year integer references seasons(season_year),
  week integer,
  game_id integer references games(game_id),
  team_id integer references teams(team_id),
  player_id integer references players(player_id),
  market_title text,
  outcome_label text not null default '',
  implied_probability real,
  last_price real,
  best_bid real,
  best_ask real,
  volume real,
  open_interest real,
  liquidity real,
  snapshot_time_utc text not null,
  source_url text,
  raw_payload_json text,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_prediction_market_snapshots_unique
  on prediction_market_snapshots (provider, market_key, outcome_label, snapshot_time_utc);

create index if not exists idx_prediction_market_snapshots_game
  on prediction_market_snapshots (game_id, snapshot_time_utc);

create index if not exists idx_prediction_market_snapshots_team
  on prediction_market_snapshots (team_id, season_year, week, snapshot_time_utc);

create index if not exists idx_prediction_market_snapshots_player
  on prediction_market_snapshots (player_id, season_year, week, snapshot_time_utc);

create table if not exists conversation_collection_runs (
  conversation_collection_run_id integer primary key autoincrement,
  source_name text not null,
  collection_scope text not null default 'team',
  target_label text,
  season_year integer references seasons(season_year),
  week integer,
  source_run_id text,
  source_dataset_id text,
  started_at_utc text not null default current_timestamp,
  finished_at_utc text,
  status text not null default 'running',
  request_count integer,
  item_count integer,
  notes text,
  raw_config_json text
);

create index if not exists idx_conversation_collection_runs_source
  on conversation_collection_runs (source_name, started_at_utc);

create index if not exists idx_conversation_collection_runs_status
  on conversation_collection_runs (status, started_at_utc);

create table if not exists conversation_documents (
  conversation_document_id integer primary key autoincrement,
  collection_run_id integer references conversation_collection_runs(conversation_collection_run_id),
  source_name text not null,
  source_document_id text not null,
  source_parent_document_id text,
  source_author_id text,
  source_author_name text,
  source_channel text,
  source_subchannel text,
  source_url text,
  content_type text not null,
  language_code text,
  title_text text,
  body_text text,
  external_created_at_utc text not null,
  collected_at_utc text not null default current_timestamp,
  like_count integer,
  reply_count integer,
  repost_count integer,
  view_count integer,
  is_deleted integer not null default 0,
  is_removed integer not null default 0,
  raw_payload_json text,
  unique (source_name, source_document_id)
);

create index if not exists idx_conversation_documents_source_time
  on conversation_documents (source_name, external_created_at_utc);

create index if not exists idx_conversation_documents_channel_time
  on conversation_documents (source_channel, external_created_at_utc);

create table if not exists conversation_document_targets (
  conversation_document_target_id integer primary key autoincrement,
  conversation_document_id integer not null references conversation_documents(conversation_document_id),
  season_year integer references seasons(season_year),
  week integer,
  game_id integer references games(game_id),
  team_id integer references teams(team_id),
  player_id integer references players(player_id),
  target_type text not null,
  target_key text not null default '',
  target_label text,
  affiliation_team_id integer references teams(team_id),
  audience_bucket text not null default 'unknown',
  mention_role text not null default 'primary',
  sentiment_label text,
  sentiment_score real,
  emotion_primary text,
  emotion_secondary text,
  sarcasm_score real,
  toxicity_score real,
  confidence_score real,
  model_provider text,
  model_name text,
  model_version text,
  is_primary_target integer not null default 0,
  notes text
);

create unique index if not exists idx_conversation_document_targets_unique
  on conversation_document_targets (conversation_document_id, target_key, audience_bucket, mention_role);

create index if not exists idx_conversation_document_targets_team
  on conversation_document_targets (team_id, season_year, week, audience_bucket);

create index if not exists idx_conversation_document_targets_player
  on conversation_document_targets (player_id, season_year, week, audience_bucket);

create index if not exists idx_conversation_document_targets_game
  on conversation_document_targets (game_id, audience_bucket);

create table if not exists team_conversation_daily (
  team_conversation_daily_id integer primary key autoincrement,
  team_id integer not null references teams(team_id),
  as_of_date text not null,
  season_year integer references seasons(season_year),
  week integer,
  source_name text not null default 'all',
  audience_bucket text not null default 'all',
  mention_count integer not null default 0,
  unique_author_count integer,
  positive_doc_count integer not null default 0,
  neutral_doc_count integer not null default 0,
  negative_doc_count integer not null default 0,
  mean_sentiment_score real,
  net_sentiment_score real,
  joy_share real,
  anger_share real,
  fear_share real,
  trust_share real,
  sadness_share real,
  surprise_share real,
  attention_score real,
  sample_quality_score real,
  top_terms_json text,
  created_at text not null default current_timestamp,
  unique (team_id, as_of_date, source_name, audience_bucket)
);

create index if not exists idx_team_conversation_daily_team
  on team_conversation_daily (team_id, as_of_date, audience_bucket);

create index if not exists idx_team_conversation_daily_week
  on team_conversation_daily (season_year, week, audience_bucket);

create table if not exists team_week_conversation_features (
  team_week_conversation_feature_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  week integer not null,
  team_id integer not null references teams(team_id),
  source_name text not null default 'all',
  audience_bucket text not null default 'all',
  mention_count integer not null default 0,
  unique_author_count integer,
  positive_doc_count integer not null default 0,
  neutral_doc_count integer not null default 0,
  negative_doc_count integer not null default 0,
  mean_sentiment_score real,
  net_sentiment_score real,
  joy_share real,
  anger_share real,
  fear_share real,
  trust_share real,
  sadness_share real,
  surprise_share real,
  attention_score real,
  sample_quality_score real,
  top_storyline_json text,
  created_at text not null default current_timestamp,
  unique (season_year, week, team_id, source_name, audience_bucket)
);

create index if not exists idx_team_week_conversation_features_team
  on team_week_conversation_features (team_id, season_year, week, audience_bucket);

create index if not exists idx_team_week_conversation_features_week
  on team_week_conversation_features (season_year, week, audience_bucket, mention_count);

create table if not exists team_game_conversation_features (
  team_game_conversation_feature_id integer primary key autoincrement,
  game_id integer not null references games(game_id),
  team_id integer not null references teams(team_id),
  season_year integer references seasons(season_year),
  week integer,
  source_name text not null default 'all',
  audience_bucket text not null default 'all',
  window_label text not null,
  period_start_utc text,
  period_end_utc text,
  mention_count integer not null default 0,
  unique_author_count integer,
  positive_doc_count integer not null default 0,
  neutral_doc_count integer not null default 0,
  negative_doc_count integer not null default 0,
  mean_sentiment_score real,
  net_sentiment_score real,
  joy_share real,
  anger_share real,
  fear_share real,
  trust_share real,
  sadness_share real,
  surprise_share real,
  attention_score real,
  sample_quality_score real,
  top_storyline_json text,
  created_at text not null default current_timestamp,
  unique (game_id, team_id, source_name, audience_bucket, window_label)
);

create index if not exists idx_team_game_conversation_features_game
  on team_game_conversation_features (game_id, team_id, audience_bucket, window_label);

create index if not exists idx_team_game_conversation_features_team
  on team_game_conversation_features (team_id, season_year, week, audience_bucket);

create table if not exists conversation_storylines (
  conversation_storyline_id integer primary key autoincrement,
  season_year integer references seasons(season_year),
  week integer,
  game_id integer references games(game_id),
  team_id integer references teams(team_id),
  source_name text not null default 'all',
  audience_bucket text not null default 'all',
  window_label text,
  period_start_utc text,
  period_end_utc text,
  storyline_rank integer not null,
  storyline_key text not null default '',
  storyline_label text not null,
  storyline_summary text,
  keywords_json text,
  representative_source_urls_json text,
  sample_document_count integer,
  llm_provider text,
  llm_model text,
  created_at text not null default current_timestamp
);

create unique index if not exists idx_conversation_storylines_unique
  on conversation_storylines (
    season_year,
    week,
    game_id,
    team_id,
    source_name,
    audience_bucket,
    window_label,
    storyline_rank
  );

create index if not exists idx_conversation_storylines_team
  on conversation_storylines (team_id, season_year, week, audience_bucket);

create index if not exists idx_conversation_storylines_game
  on conversation_storylines (game_id, audience_bucket, window_label);

create table if not exists drives (
  drive_id integer primary key autoincrement,
  game_id integer not null references games(game_id),
  source_drive_id text,
  offense_team_id integer not null references teams(team_id),
  defense_team_id integer not null references teams(team_id),
  period integer,
  drive_number integer,
  start_yardline integer,
  end_yardline integer,
  play_count integer,
  yards integer,
  result text,
  points_scored integer,
  is_garbage_time integer not null default 0
);

create index if not exists idx_drives_game on drives (game_id);
create index if not exists idx_drives_offense on drives (offense_team_id);
create unique index if not exists idx_drives_game_source on drives (game_id, source_drive_id);

create table if not exists plays (
  play_id integer primary key autoincrement,
  game_id integer not null references games(game_id),
  drive_id integer references drives(drive_id),
  source_play_id text,
  offense_team_id integer not null references teams(team_id),
  defense_team_id integer not null references teams(team_id),
  period integer,
  clock_minutes integer,
  clock_seconds integer,
  down integer,
  distance integer,
  yard_line integer,
  play_type text,
  yards_gained integer,
  epa real,
  ppa real,
  success_flag integer,
  home_win_prob real,
  is_garbage_time integer not null default 0
);

create index if not exists idx_plays_game on plays (game_id);
create index if not exists idx_plays_drive on plays (drive_id);
create unique index if not exists idx_plays_game_source on plays (game_id, source_play_id);

create table if not exists team_game_advanced_stats (
  team_game_advanced_stat_id integer primary key autoincrement,
  game_id integer not null references games(game_id),
  team_id integer not null references teams(team_id),
  opponent_team_id integer not null references teams(team_id),
  offense_ppa real,
  defense_ppa real,
  success_rate_off real,
  success_rate_def real,
  explosiveness_off real,
  explosiveness_def real,
  rushing_ppa_off real,
  rushing_ppa_def real,
  passing_ppa_off real,
  passing_ppa_def real,
  finishing_drives_off real,
  finishing_drives_def real,
  havoc_off real,
  havoc_def real,
  field_position_off real,
  field_position_def real,
  source_name text not null default 'cfbd',
  unique (game_id, team_id, source_name)
);

create table if not exists opponent_adjusted_team_week (
  opponent_adjusted_team_week_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  week integer not null,
  team_id integer not null references teams(team_id),
  metric_name text not null,
  raw_value real,
  adjusted_value real,
  percentile real,
  sample_size integer,
  model_version text not null,
  unique (season_year, week, team_id, metric_name, model_version)
);

create table if not exists model_runs (
  model_run_id integer primary key autoincrement,
  model_name text not null,
  model_version text not null,
  season_year integer not null references seasons(season_year),
  week integer,
  data_cutoff_utc text not null,
  notes text,
  created_at text not null default current_timestamp
);

create table if not exists preseason_prior_components (
  preseason_prior_component_id integer primary key autoincrement,
  season_year integer not null references seasons(season_year),
  team_id integer not null references teams(team_id),
  level_points real not null default 0,
  conference_points real not null default 0,
  prev_season_points real not null default 0,
  program_baseline_points real not null default 0,
  returning_production_points real not null default 0,
  talent_points real not null default 0,
  transfer_points real not null default 0,
  coach_points real not null default 0,
  qb_continuity_points real not null default 0,
  continuity_proxy_points real not null default 0,
  official_rank_points real not null default 0,
  manual_offseason_points real not null default 0,
  prior_mean real not null,
  prior_sd real not null,
  unique (season_year, team_id)
);

create table if not exists level_strength_weekly (
  level_strength_weekly_id integer primary key autoincrement,
  model_run_id integer not null references model_runs(model_run_id),
  level_code text not null references levels(level_code),
  level_mean real not null,
  level_sd real,
  unique (model_run_id, level_code)
);

create table if not exists conference_strength_weekly (
  conference_strength_weekly_id integer primary key autoincrement,
  model_run_id integer not null references model_runs(model_run_id),
  conference_id integer not null references conferences(conference_id),
  conference_mean real not null,
  conference_sd real,
  unique (model_run_id, conference_id)
);

create table if not exists power_ratings_weekly (
  power_rating_weekly_id integer primary key autoincrement,
  model_run_id integer not null references model_runs(model_run_id),
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  week integer not null,
  power_rating real not null,
  offense_rating real not null,
  defense_rating real not null,
  special_teams_rating real not null,
  tempo_rating real not null,
  prior_mean real,
  posterior_sd real,
  cross_level_confidence real,
  schedule_connectivity real,
  unique (model_run_id, team_id, week)
);

create index if not exists idx_power_week on power_ratings_weekly (season_year, week, power_rating desc);

create table if not exists resume_ratings_weekly (
  resume_rating_weekly_id integer primary key autoincrement,
  model_run_id integer not null references model_runs(model_run_id),
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  week integer not null,
  resume_score real not null,
  record_strength_score real not null,
  performance_over_expectation_score real not null,
  result_quality_score real not null,
  best_win_score real,
  worst_loss_score real,
  schedule_strength_score real,
  unique (model_run_id, team_id, week)
);

create index if not exists idx_resume_week on resume_ratings_weekly (season_year, week, resume_score desc);

create table if not exists strength_of_record_benchmarks (
  strength_of_record_benchmark_id integer primary key autoincrement,
  model_run_id integer not null references model_runs(model_run_id),
  team_id integer not null references teams(team_id),
  benchmark_name text not null,
  benchmark_power real not null,
  match_or_exceed_prob real not null,
  score_value real not null,
  unique (model_run_id, team_id, benchmark_name)
);

create table if not exists game_predictions (
  game_prediction_id integer primary key autoincrement,
  model_run_id integer not null references model_runs(model_run_id),
  game_id integer not null references games(game_id),
  home_power_pre real,
  away_power_pre real,
  predicted_home_points real,
  predicted_away_points real,
  predicted_spread_home real,
  predicted_total real,
  home_win_probability real,
  upset_probability real,
  volatility real,
  unique (model_run_id, game_id)
);

create table if not exists team_rating_deltas (
  team_rating_delta_id integer primary key autoincrement,
  model_run_id integer not null references model_runs(model_run_id),
  game_id integer not null references games(game_id),
  team_id integer not null references teams(team_id),
  pregame_power real,
  postgame_power real,
  power_delta real,
  offense_delta real,
  defense_delta real,
  special_teams_delta real,
  resume_delta real,
  opponent_quality_effect real,
  dominance_effect real,
  garbage_time_discount real,
  location_effect real,
  explanation_json text,
  unique (model_run_id, game_id, team_id)
);

create table if not exists manual_team_adjustments (
  manual_team_adjustment_id integer primary key autoincrement,
  team_id integer not null references teams(team_id),
  season_year integer not null references seasons(season_year),
  week integer,
  adjustment_scope text not null,
  points_delta real not null,
  reason text not null,
  created_at text not null default current_timestamp
);

create index if not exists idx_team_source_ids_lookup on team_source_ids (source_name, source_team_id);
create index if not exists idx_player_source_ids_lookup on player_source_ids (source_name, source_player_id);
