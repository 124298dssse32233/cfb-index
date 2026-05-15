from __future__ import annotations

from pathlib import Path

from cfb_rankings.db import Database

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _ensure_column(db: Database, table: str, column: str, definition: str) -> None:
    if not db.column_exists(table, column):
        db.execute(f"alter table {table} add column {column} {definition}")


def _table_exists(db: Database, table: str) -> bool:
    row = db.query_one(
        "select name from sqlite_master where type='table' and name = :name",
        {"name": table},
    )
    return row is not None


def apply_sql_migrations(db: Database) -> list[str]:
    """Apply every .sql file in the migrations/ directory, idempotently.

    Tracked in `schema_migrations` once created by the earliest file. Files
    recorded in `schema_migrations` are skipped on subsequent runs so that
    non-idempotent statements (e.g. ``ALTER TABLE ... ADD COLUMN``) are safe
    to land in .sql files for v5-1 onwards. Historically the rule was that
    files had to be CREATE IF NOT EXISTS only and column additions had to
    move into ``apply_runtime_migrations``; both patterns are now supported.

    Returns the list of file names that were applied this invocation (i.e.
    excludes those already recorded in ``schema_migrations``).
    """
    if not _MIGRATIONS_DIR.exists():
        return []
    applied: list[str] = []
    files = sorted(p for p in _MIGRATIONS_DIR.glob("*.sql") if p.is_file())
    for path in files:
        # Skip files already recorded in schema_migrations (table created by
        # the earliest migration). On the first ever run schema_migrations
        # does not yet exist, so the check short-circuits and every file
        # runs once. After the first apply, this guard keeps non-idempotent
        # statements from re-executing.
        if _table_exists(db, "schema_migrations"):
            row = db.query_one(
                "select 1 from schema_migrations where migration_id = :mid",
                {"mid": path.name},
            )
            if row is not None:
                continue
        db.apply_sql_file(path)
        if _table_exists(db, "schema_migrations"):
            db.execute(
                "insert or ignore into schema_migrations (migration_id, note) "
                "values (:migration_id, :note)",
                {"migration_id": path.name, "note": "applied via migrations module"},
            )
        applied.append(path.name)
    return applied


def _apply_fanintel_column_additions(db: Database) -> None:
    """Column additions for STRATEGY §5. Idempotent via _ensure_column.

    Paired with migrations/20260422_01_fanintel_schema.sql for the table
    creations. Keep both in sync.
    """
    # source_registry: extend existing table with STRATEGY §5 fields.
    if _table_exists(db, "source_registry"):
        _ensure_column(db, "source_registry", "source_id", "text")
        _ensure_column(db, "source_registry", "tier", "text")
        _ensure_column(db, "source_registry", "ingest_method", "text")
        _ensure_column(db, "source_registry", "terms_url", "text")
        _ensure_column(db, "source_registry", "license", "text")
        _ensure_column(db, "source_registry", "retention_days", "integer")
        _ensure_column(db, "source_registry", "cohort_weights", "text")
        _ensure_column(db, "source_registry", "cohort_weights_rationale", "text")
        _ensure_column(db, "source_registry", "cohort_weights_updated_at", "text")
        _ensure_column(db, "source_registry", "max_publication_form", "text")
        # UNIQUE index on source_id once populated lets FKs reference it.
        db.execute(
            "create unique index if not exists idx_source_registry_source_id "
            "on source_registry (source_id) where source_id is not null"
        )

    # conversation_documents: provenance fields.
    if _table_exists(db, "conversation_documents"):
        _ensure_column(db, "conversation_documents", "source_id", "text")
        _ensure_column(db, "conversation_documents", "source_tier", "text")
        _ensure_column(db, "conversation_documents", "demographic_slice", "text")
        _ensure_column(db, "conversation_documents", "geographic_origin", "text")
        _ensure_column(db, "conversation_documents", "author_identity_class", "text")
        _ensure_column(db, "conversation_documents", "capture_url", "text")
        _ensure_column(db, "conversation_documents", "canonical_url", "text")
        _ensure_column(db, "conversation_documents", "retention_policy", "text")
        _ensure_column(db, "conversation_documents", "ingestion_adapter_version", "text")
        _ensure_column(db, "conversation_documents", "dedup_key", "text")
        db.execute(
            "create index if not exists idx_conversation_documents_source_id "
            "on conversation_documents (source_id)"
        )
        db.execute(
            "create index if not exists idx_conversation_documents_dedup "
            "on conversation_documents (dedup_key) where dedup_key is not null"
        )

    # Aggregate tables: sample_n / sample_window / confidence_floor / model_version
    # added as-spec per STRATEGY §5 (decision 2026-04-22: add all four even
    # where overlapping columns exist; reconcile in aggregator code).
    for table in (
        "team_week_conversation_features",
        "fanbase_mood_weekly",
        "rivalry_obsession_weekly",
        "lexicon_weekly",
    ):
        if _table_exists(db, table):
            _ensure_column(db, table, "sample_n", "integer")
            _ensure_column(db, table, "sample_window", "text")
            _ensure_column(db, table, "confidence_floor", "text")
            _ensure_column(db, table, "model_version", "text")


def apply_runtime_migrations(db: Database) -> None:
    _ensure_column(db, "games", "season_phase", "text")
    if not db.column_exists("games", "source_week"):
        db.execute("alter table games add column source_week integer")
        db.execute("update games set source_week = week where source_week is null")
    _ensure_column(db, "roster_entries", "home_city", "text")
    _ensure_column(db, "roster_entries", "home_latitude", "real")
    _ensure_column(db, "roster_entries", "home_longitude", "real")
    _ensure_column(db, "roster_entries", "home_county_fips", "text")
    _ensure_column(db, "returning_production", "total_ppa", "real")
    _ensure_column(db, "returning_production", "total_passing_ppa", "real")
    _ensure_column(db, "returning_production", "total_receiving_ppa", "real")
    _ensure_column(db, "returning_production", "total_rushing_ppa", "real")
    _ensure_column(db, "returning_production", "percent_ppa", "real")
    _ensure_column(db, "returning_production", "percent_passing_ppa", "real")
    _ensure_column(db, "returning_production", "percent_receiving_ppa", "real")
    _ensure_column(db, "returning_production", "percent_rushing_ppa", "real")
    _ensure_column(db, "returning_production", "usage_rate", "real")
    _ensure_column(db, "returning_production", "passing_usage_rate", "real")
    _ensure_column(db, "returning_production", "receiving_usage_rate", "real")
    _ensure_column(db, "returning_production", "rushing_usage_rate", "real")
    db.execute(
        """
        create table if not exists roster_source_snapshots (
          roster_source_snapshot_id integer primary key autoincrement,
          player_id integer references players(player_id),
          team_id integer not null references teams(team_id),
          season_year integer not null references seasons(season_year),
          source_name text not null default 'cfbd',
          source_player_id text not null default '',
          payload_json text not null,
          created_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_roster_source_snapshots_unique
          on roster_source_snapshots (team_id, season_year, source_name, source_player_id)
        """
    )
    db.execute(
        """
        create index if not exists idx_roster_source_snapshots_player
          on roster_source_snapshots (player_id, season_year)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_player_recruiting_profiles_unique
          on player_recruiting_profiles (source_name, source_recruit_id)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_recruiting_profiles_player
          on player_recruiting_profiles (player_id, season_year)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_recruiting_profiles_team
          on player_recruiting_profiles (team_id, season_year)
        """
    )
    db.execute(
        """
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
          notes text,
          created_at text not null default current_timestamp
        )
        """
    )
    _ensure_column(db, "heisman_rankings_weekly", "market_implied_probability", "real")
    _ensure_column(db, "heisman_rankings_weekly", "market_american_odds", "integer")
    _ensure_column(db, "heisman_rankings_weekly", "market_provider", "text")
    _ensure_column(db, "transfer_entries", "transfer_stars", "integer")
    _ensure_column(db, "transfer_entries", "transfer_date", "text")
    _ensure_column(db, "transfer_entries", "eligibility", "text")
    _ensure_column(db, "transfer_entries", "from_team_name", "text")
    _ensure_column(db, "transfer_entries", "to_team_name", "text")
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
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
          )
        """
    )
    db.execute(
        """
        create index if not exists idx_player_honors_player
          on player_honors (player_id, season_year, honor_scope, week)
        """
    )
    db.execute(
        """
        create unique index if not exists idx_heisman_rankings_weekly_unique
          on heisman_rankings_weekly (season_year, week, player_id, model_run_id, source_name)
        """
    )
    db.execute(
        """
        create index if not exists idx_heisman_rankings_weekly_board
          on heisman_rankings_weekly (season_year, week, rank_overall, nowcast_rank, forecast_rank)
        """
    )
    db.execute(
        """
        create index if not exists idx_heisman_rankings_weekly_player
          on heisman_rankings_weekly (player_id, season_year, week)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_heisman_vote_results_unique
          on heisman_vote_results (season_year, player_id, source_name)
        """
    )
    db.execute(
        """
        create index if not exists idx_heisman_vote_results_player
          on heisman_vote_results (player_id, season_year, place)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_player_season_stats_unique
          on player_season_stats (
            season_year,
            week,
            season_type,
            source_name,
            source_player_id,
            team_name,
            category,
            stat_type
          )
        """
    )
    db.execute(
        """
        create index if not exists idx_player_season_stats_player
          on player_season_stats (player_id, season_year, week)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_season_stats_team
          on player_season_stats (team_id, season_year, week, category)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_player_usage_season_unique
          on player_usage_season (season_year, week, source_name, source_player_id, team_name)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_usage_season_player
          on player_usage_season (player_id, season_year, week)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_usage_season_team
          on player_usage_season (team_id, season_year, week)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_player_value_metrics_unique
          on player_value_metrics (season_year, week, source_name, metric_name, source_player_id, team_name)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_value_metrics_player
          on player_value_metrics (player_id, season_year, week, metric_name)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_value_metrics_team
          on player_value_metrics (team_id, season_year, week, metric_name)
        """
    )
    db.execute(
        """
        create table if not exists player_game_stats (
          player_game_stat_id integer primary key autoincrement,
          game_id integer not null references games(game_id),
          season_year integer not null references seasons(season_year),
          week integer,
          season_type text not null default 'regular',
          team_id integer references teams(team_id),
          player_id integer references players(player_id),
          source_name text not null default 'cfbd',
          source_player_id text not null default '',
          team_name text,
          conference_name text,
          player_name text,
          category text not null,
          stat_type text not null,
          stat_value_text text,
          stat_value_num real,
          created_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_player_game_stats_unique
          on player_game_stats (
            game_id,
            team_id,
            source_name,
            source_player_id,
            category,
            stat_type
          )
        """
    )
    db.execute(
        """
        create index if not exists idx_player_game_stats_player
          on player_game_stats (player_id, season_year, week, category)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_game_stats_team
          on player_game_stats (team_id, season_year, week, category)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_heisman_market_odds_weekly_unique
          on heisman_market_odds_weekly (
            season_year,
            week,
            provider,
            source_name,
            source_player_key,
            market_name
          )
        """
    )
    db.execute(
        """
        create index if not exists idx_heisman_market_odds_weekly_player
          on heisman_market_odds_weekly (player_id, season_year, week, market_name)
        """
    )
    db.execute(
        """
        create index if not exists idx_heisman_market_odds_weekly_lookup
          on heisman_market_odds_weekly (season_year, week, provider, market_name, player_name)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_team_aliases_unique
          on team_aliases (team_id, alias_normalized, alias_type, season_year)
        """
    )
    db.execute(
        """
        create index if not exists idx_team_aliases_lookup
          on team_aliases (alias_normalized, season_year, is_active)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_player_aliases_unique
          on player_aliases (player_id, alias_normalized, alias_type, season_year)
        """
    )
    db.execute(
        """
        create index if not exists idx_player_aliases_lookup
          on player_aliases (alias_normalized, season_year, team_id, is_active)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_game_line_snapshots_unique
          on game_line_snapshots (game_id, provider, source_name, snapshot_time_utc)
        """
    )
    db.execute(
        """
        create index if not exists idx_game_line_snapshots_game
          on game_line_snapshots (game_id, snapshot_time_utc)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_prediction_market_snapshots_unique
          on prediction_market_snapshots (provider, market_key, outcome_label, snapshot_time_utc)
        """
    )
    db.execute(
        """
        create index if not exists idx_prediction_market_snapshots_game
          on prediction_market_snapshots (game_id, snapshot_time_utc)
        """
    )
    db.execute(
        """
        create index if not exists idx_prediction_market_snapshots_team
          on prediction_market_snapshots (team_id, season_year, week, snapshot_time_utc)
        """
    )
    db.execute(
        """
        create index if not exists idx_prediction_market_snapshots_player
          on prediction_market_snapshots (player_id, season_year, week, snapshot_time_utc)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_collection_runs_source
          on conversation_collection_runs (source_name, started_at_utc)
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_collection_runs_status
          on conversation_collection_runs (status, started_at_utc)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_documents_source_time
          on conversation_documents (source_name, external_created_at_utc)
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_documents_channel_time
          on conversation_documents (source_channel, external_created_at_utc)
        """
    )
    _ensure_column(db, "conversation_documents", "raw_text_purged_at_utc", "text")
    _ensure_column(db, "conversation_documents", "raw_payload_purged_at_utc", "text")
    _ensure_column(db, "conversation_documents", "raw_retention_policy", "text")

    db.execute(
        """
        create table if not exists source_registry (
          source_registry_id integer primary key autoincrement,
          source_name text not null,
          provider_name text not null default '',
          source_kind text not null,
          confidence_tier text not null default 'unknown',
          publication_mode text not null default 'computed',
          collection_method text not null default '',
          cost_monthly_usd real,
          terms_profile text not null default '',
          raw_text_retention_days integer,
          raw_payload_retention_days integer,
          requires_oauth integer not null default 0,
          allows_historical_backfill integer not null default 0,
          source_url text,
          notes text,
          is_active integer not null default 1,
          created_at text not null default current_timestamp,
          updated_at text not null default current_timestamp,
          unique (source_name, provider_name, source_kind)
        )
        """
    )
    db.upsert_many(
        "source_registry",
        [
            {
                "source_name": "reddit",
                "provider_name": "reddit_api",
                "source_kind": "conversation",
                "confidence_tier": "primary_forward",
                "publication_mode": "computed",
                "collection_method": "oauth_api",
                "cost_monthly_usd": 0.0,
                "terms_profile": "oauth_required_delete_compliance",
                "raw_text_retention_days": 2,
                "raw_payload_retention_days": 2,
                "requires_oauth": 1,
                "allows_historical_backfill": 0,
                "source_url": "https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki",
                "notes": "Forward Reddit collection must aggregate quickly and purge raw user text after feature extraction.",
                "is_active": 1,
            },
            {
                "source_name": "reddit",
                "provider_name": "arctic_shift",
                "source_kind": "conversation_archive",
                "confidence_tier": "archive_backfill",
                "publication_mode": "computed_archive",
                "collection_method": "public_archive_api",
                "cost_monthly_usd": 0.0,
                "terms_profile": "unofficial_no_uptime_guarantee",
                "raw_text_retention_days": 2,
                "raw_payload_retention_days": 2,
                "requires_oauth": 0,
                "allows_historical_backfill": 1,
                "source_url": "https://github.com/ArthurHeitmann/arctic_shift/tree/master/api",
                "notes": "Historical Reddit archive useful for retro backfills; publish with archive provenance, not official live provenance.",
                "is_active": 1,
            },
            {
                "source_name": "reddit",
                "provider_name": "pullpush",
                "source_kind": "conversation_archive",
                "confidence_tier": "fallback_archive",
                "publication_mode": "computed_archive",
                "collection_method": "public_archive_api",
                "cost_monthly_usd": 0.0,
                "terms_profile": "unofficial_availability_variable",
                "raw_text_retention_days": 2,
                "raw_payload_retention_days": 2,
                "requires_oauth": 0,
                "allows_historical_backfill": 1,
                "source_url": "https://pullpush.io/",
                "notes": "Fallback only; verify coverage before trusting any backfill window.",
                "is_active": 1,
            },
            {
                "source_name": "cfbd",
                "provider_name": "collegefootballdata",
                "source_kind": "sports_facts",
                "confidence_tier": "primary_facts",
                "publication_mode": "computed",
                "collection_method": "authenticated_api",
                "cost_monthly_usd": 10.0,
                "terms_profile": "api_key_patron_tier",
                "raw_text_retention_days": None,
                "raw_payload_retention_days": None,
                "requires_oauth": 0,
                "allows_historical_backfill": 1,
                "source_url": "https://collegefootballdata.com/api-tiers",
                "notes": "Recommended low-cost source for CFB facts, model inputs, live scoreboard, and play-by-play.",
                "is_active": 1,
            },
            {
                "source_name": "gdelt",
                "provider_name": "gdelt",
                "source_kind": "news_corroboration",
                "confidence_tier": "citation_support",
                "publication_mode": "citation_or_directional",
                "collection_method": "public_api",
                "cost_monthly_usd": 0.0,
                "terms_profile": "public_news_metadata",
                "raw_text_retention_days": None,
                "raw_payload_retention_days": 30,
                "requires_oauth": 0,
                "allows_historical_backfill": 1,
                "source_url": "https://www.gdeltproject.org/",
                "notes": "Use for media pulse and corroborating source discovery, not fan mood scoring.",
                "is_active": 1,
            },
        ],
        conflict_columns=["source_name", "provider_name", "source_kind"],
        update_columns=[
            "confidence_tier",
            "publication_mode",
            "collection_method",
            "cost_monthly_usd",
            "terms_profile",
            "raw_text_retention_days",
            "raw_payload_retention_days",
            "requires_oauth",
            "allows_historical_backfill",
            "source_url",
            "notes",
            "is_active",
        ],
    )
    db.execute(
        """
        create table if not exists conversation_raw_retention_audit (
          retention_audit_id integer primary key autoincrement,
          source_name text not null,
          provider_name text,
          cutoff_utc text not null,
          documents_examined integer not null default 0,
          documents_purged integer not null default 0,
          dry_run integer not null default 0,
          notes text,
          created_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_conversation_document_targets_unique
          on conversation_document_targets (conversation_document_id, target_key, audience_bucket, mention_role)
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_document_targets_team
          on conversation_document_targets (team_id, season_year, week, audience_bucket)
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_document_targets_player
          on conversation_document_targets (player_id, season_year, week, audience_bucket)
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_document_targets_game
          on conversation_document_targets (game_id, audience_bucket)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_team_conversation_daily_team
          on team_conversation_daily (team_id, as_of_date, audience_bucket)
        """
    )
    db.execute(
        """
        create index if not exists idx_team_conversation_daily_week
          on team_conversation_daily (season_year, week, audience_bucket)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_team_week_conversation_features_team
          on team_week_conversation_features (team_id, season_year, week, audience_bucket)
        """
    )
    db.execute(
        """
        create index if not exists idx_team_week_conversation_features_week
          on team_week_conversation_features (season_year, week, audience_bucket, mention_count)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_team_game_conversation_features_game
          on team_game_conversation_features (game_id, team_id, audience_bucket, window_label)
        """
    )
    db.execute(
        """
        create index if not exists idx_team_game_conversation_features_team
          on team_game_conversation_features (team_id, season_year, week, audience_bucket)
        """
    )
    db.execute(
        """
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
        )
        """
    )
    db.execute(
        """
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
          )
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_storylines_team
          on conversation_storylines (team_id, season_year, week, audience_bucket)
        """
    )
    db.execute(
        """
        create index if not exists idx_conversation_storylines_game
          on conversation_storylines (game_id, audience_bucket, window_label)
        """
    )
    db.execute(
        """
        update seasons
        set season_label = cast(season_year as text) || ' Season'
        where season_label is null
           or season_label = cast(season_year as text)
        """
    )

    # -----------------------------------------------------------------------
    # Fan Intelligence Hub v5 — archetype taxonomy, classifications, weekly
    # mood, rivalry obsession ratios, and lexicon phrase mining.
    # -----------------------------------------------------------------------
    db.execute(
        """
        create table if not exists fanbase_archetype_taxonomy (
          taxonomy_id integer primary key autoincrement,
          kind text not null check (kind in ('primary', 'modifier')),
          slug text not null,
          name text not null,
          description text not null default '',
          signature_phrase text not null default '',
          half_life text not null default 'medium',
          display_order integer not null default 0,
          updated_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_fanbase_archetype_taxonomy_slug
          on fanbase_archetype_taxonomy (kind, slug)
        """
    )
    db.execute(
        """
        create table if not exists fanbase_classification (
          classification_id integer primary key autoincrement,
          team_id integer not null references teams(team_id),
          season_year integer not null references seasons(season_year),
          primary_archetype_slug text not null,
          primary_confidence real not null default 0.0,
          modifier_slugs_json text not null default '[]',
          signature_phrase text not null default '',
          classifier_version text not null default 'v1.0',
          notes text,
          classified_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_fanbase_classification_unique
          on fanbase_classification (team_id, season_year)
        """
    )
    db.execute(
        """
        create table if not exists fanbase_classification_history (
          classification_history_id integer primary key autoincrement,
          team_id integer not null references teams(team_id),
          season_year integer not null references seasons(season_year),
          primary_archetype_slug text not null,
          primary_confidence real not null default 0.0,
          modifier_slugs_json text not null default '[]',
          classifier_version text not null default 'v1.0',
          classified_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_fanbase_classification_history_unique
          on fanbase_classification_history (team_id, season_year, classifier_version)
        """
    )
    db.execute(
        """
        create table if not exists fanbase_mood_weekly (
          mood_weekly_id integer primary key autoincrement,
          team_id integer not null references teams(team_id),
          week_start_date text not null,
          mood_score integer not null,
          delta_from_prev_week integer not null default 0,
          top_cause_token text not null default '',
          top_cause_label text not null default '',
          sample_size integer not null default 0,
          ingested_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_fanbase_mood_weekly_unique
          on fanbase_mood_weekly (team_id, week_start_date)
        """
    )
    db.execute(
        """
        create index if not exists idx_fanbase_mood_weekly_week
          on fanbase_mood_weekly (week_start_date)
        """
    )
    db.execute(
        """
        create table if not exists rivalry_obsession_weekly (
          rivalry_weekly_id integer primary key autoincrement,
          rivalry_slug text not null,
          rivalry_name text not null,
          team_a_id integer not null references teams(team_id),
          team_b_id integer not null references teams(team_id),
          week_start_date text not null,
          a_mentions_b_count integer not null default 0,
          b_mentions_a_count integer not null default 0,
          ratio_dominant real not null default 1.0,
          leaning_team integer not null default 0,
          take text not null default '',
          ingested_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_rivalry_obsession_weekly_unique
          on rivalry_obsession_weekly (rivalry_slug, week_start_date)
        """
    )
    db.execute(
        """
        create table if not exists lexicon_weekly (
          lexicon_weekly_id integer primary key autoincrement,
          phrase text not null,
          week_start_date text not null,
          mention_count integer not null default 0,
          spike_pct_wow real not null default 0.0,
          origin_community text not null default '',
          related_team_id integer references teams(team_id),
          sample_quotes_json text not null default '[]',
          trend_json text not null default '[]',
          narrative text not null default '',
          featured integer not null default 0,
          ingested_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_lexicon_weekly_unique
          on lexicon_weekly (phrase, week_start_date)
        """
    )
    db.execute(
        """
        create index if not exists idx_lexicon_weekly_featured
          on lexicon_weekly (week_start_date, featured)
        """
    )
    db.execute(
        """
        create table if not exists hub_issue_metadata (
          hub_issue_id integer primary key autoincrement,
          issue_number text not null,
          week_start_date text not null,
          issue_date text not null,
          model_week integer,
          cover_headline text not null default '',
          cover_dek text not null default '',
          cover_chart_caption text not null default '',
          editor_note_body text not null default '',
          pull_quote text not null default '',
          commiseration_team_slug text not null default '',
          commiseration_eyebrow text not null default '',
          commiseration_body text not null default '',
          cards_json text not null default '[]',
          ingested_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_hub_issue_metadata_unique
          on hub_issue_metadata (issue_number)
        """
    )

    for table_name in (
        "fanbase_mood_weekly",
        "rivalry_obsession_weekly",
        "lexicon_weekly",
    ):
        _ensure_column(db, table_name, "source", "text not null default 'computed'")
        _ensure_column(db, table_name, "sample_authors", "integer not null default 0")
        _ensure_column(db, table_name, "confidence", "real not null default 1.0")

    _ensure_column(
        db,
        "hub_issue_metadata",
        "methodology_row_json",
        "text not null default '{}'",
    )

    db.execute(
        """
        create table if not exists team_week_rival_mentions (
          rival_mention_id integer primary key autoincrement,
          team_id integer not null references teams(team_id),
          rival_team_id integer not null references teams(team_id),
          season_year integer not null references seasons(season_year),
          week integer not null,
          mention_count integer not null default 0,
          source_name text not null default 'reddit',
          audience_bucket text not null default 'fan',
          sample_authors integer not null default 0,
          confidence real not null default 1.0,
          created_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_team_week_rival_mentions_unique
          on team_week_rival_mentions (
            team_id,
            rival_team_id,
            season_year,
            week,
            source_name,
            audience_bucket
          )
        """
    )

    db.execute(
        """
        create table if not exists offseason_week_map (
          season_year integer not null references seasons(season_year),
          offseason_week integer not null,
          week_start_date text not null,
          issue_number text not null,
          issue_title text not null,
          slug text not null,
          model_week integer,
          sources_json text not null default '[]',
          ingested_at text not null default current_timestamp,
          primary key (season_year, offseason_week)
        )
        """
    )
    db.execute(
        """
        create unique index if not exists idx_offseason_week_map_issue
          on offseason_week_map (issue_number)
        """
    )
    db.execute(
        """
        create unique index if not exists idx_offseason_week_map_date
          on offseason_week_map (week_start_date)
        """
    )

    db.execute(
        """
        create table if not exists coaching_changes (
          coaching_change_id integer primary key autoincrement,
          team_id integer references teams(team_id),
          team_slug text not null,
          coach_name text not null,
          role text not null,
          change_type text not null,
          announced_date text not null,
          summary text not null,
          issue_number text,
          sources_json text not null default '[]',
          ingested_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_coaching_changes_lookup
          on coaching_changes (team_slug, announced_date, coach_name)
        """
    )

    db.execute(
        """
        create table if not exists portal_moves (
          portal_move_id integer primary key autoincrement,
          player_name text not null,
          from_team_id integer references teams(team_id),
          to_team_id integer references teams(team_id),
          from_team_slug text,
          to_team_slug text,
          position text,
          announced_date text not null,
          summary text not null,
          issue_number text,
          sources_json text not null default '[]',
          ingested_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_portal_moves_lookup
          on portal_moves (announced_date, player_name)
        """
    )
    # Unique index for UPSERT support — Sprint v5-1 Day 4 (Adapter 1).
    # The plan called for (player_external_id, entered_at_utc), but the
    # actual schema has player_name + announced_date instead. We add
    # from_team_slug to disambiguate cases where two players with the
    # same name enter the portal on the same day from different teams.
    db.execute(
        """
        create unique index if not exists idx_portal_moves_upsert_key
          on portal_moves (player_name, announced_date, coalesce(from_team_slug, ''))
        """
    )

    db.execute(
        """
        create table if not exists spring_events (
          spring_event_id integer primary key autoincrement,
          team_id integer references teams(team_id),
          team_slug text,
          event_date text not null,
          event_type text not null,
          headline text not null,
          summary text not null,
          issue_number text,
          sources_json text not null default '[]',
          ingested_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_spring_events_lookup
          on spring_events (event_date, team_slug, event_type)
        """
    )

    db.execute(
        """
        create table if not exists phrase_mentions_weekly (
          phrase text not null,
          season_year integer not null references seasons(season_year),
          week integer not null,
          mention_count integer not null default 0,
          document_count integer not null default 0,
          source_name text not null default 'reddit',
          audience_bucket text not null default 'fan',
          sample_quotes_json text not null default '[]',
          ingested_at text not null default current_timestamp,
          primary key (phrase, season_year, week, source_name, audience_bucket)
        )
        """
    )

    db.execute(
        """
        create table if not exists hub_provenance_audit (
          audit_id integer primary key autoincrement,
          table_name text not null,
          row_key_json text not null,
          old_value_json text not null,
          new_value_json text not null,
          old_source text not null,
          new_source text not null,
          run_id text,
          reason text not null,
          changed_at text not null default current_timestamp
        )
        """
    )

    # Phase 2 — team brand + brand assets (CFBD)
    _ensure_column(db, "teams", "cfbd_classification", "text")
    db.execute(
        """
        create table if not exists team_brand (
          team_brand_id integer primary key autoincrement,
          team_id integer not null unique references teams(team_id),
          primary_color text,
          secondary_color text,
          mascot_name text,
          abbreviation_short text,
          source_name text not null default 'cfbd',
          source_updated_utc text,
          notes text,
          created_at text not null default current_timestamp
        )
        """
    )
    db.execute(
        """
        create table if not exists team_brand_assets (
          team_brand_asset_id integer primary key autoincrement,
          team_id integer not null references teams(team_id),
          asset_kind text not null,
          variant text,
          source_name text not null,
          source_url text,
          local_path text not null,
          content_hash text,
          width integer,
          height integer,
          fetched_at_utc text not null default current_timestamp,
          is_active integer not null default 1
        )
        """
    )
    db.execute(
        """
        create index if not exists idx_team_brand_assets_lookup
          on team_brand_assets (team_id, asset_kind, is_active)
        """
    )
    db.execute(
        """
        create unique index if not exists idx_team_brand_assets_unique
          on team_brand_assets (team_id, asset_kind, variant, source_name)
        """
    )

    # Fan Intelligence schema (STRATEGY §5, 2026-04-22).
    apply_sql_migrations(db)
    _apply_fanintel_column_additions(db)
