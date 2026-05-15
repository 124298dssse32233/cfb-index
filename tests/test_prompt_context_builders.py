"""Smoke tests for ``cfb_rankings.prompt_context.builders``.

Every builder must:

1. Return a ``dict`` with the manifest keys defined in
   ``DESIGN_AUDIT_2026_05_15_v5_3.md`` Part 4.
2. Survive a *completely empty* in-memory SQLite database — i.e. when
   none of the upstream tables exist. The builder is expected to catch
   :class:`sqlite3.Error` per missing table and return empty lists / None
   for the affected key, but never raise.
3. Survive a database with *some* tables present but no rows — still
   return shape-stable empty results.

This is the integration contract the prompt-assembly path relies on:
the renderer can call any builder regardless of how much of the schema
has shipped.
"""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from cfb_rankings.prompt_context import builders as B


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_db() -> sqlite3.Connection:
    """In-memory SQLite with zero tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def minimal_db() -> sqlite3.Connection:
    """In-memory SQLite with the *bare minimum* tables present.

    We CREATE TABLE but never INSERT — so every helper that successfully
    runs its SQL gets back an empty result set. This exercises the
    "no rows" branch separately from the "missing table" branch.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # teams — needed for slug → team_id lookups
    cur.execute(
        """
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY,
            school_slug TEXT
        )
        """
    )

    # players
    cur.execute(
        """
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            full_name TEXT
        )
        """
    )

    # editions / edition_features
    cur.execute(
        """
        CREATE TABLE editions (
            edition_slug TEXT PRIMARY KEY,
            publish_date TEXT,
            theme_title TEXT,
            theme_dek TEXT,
            status TEXT,
            canon_entry_slug TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE edition_features (
            id INTEGER PRIMARY KEY,
            edition_slug TEXT,
            feature_kind TEXT,
            title TEXT,
            body_markdown TEXT,
            canon_entry_slug TEXT
        )
        """
    )

    # storylines
    cur.execute(
        """
        CREATE TABLE storyline_threads (
            thread_slug TEXT PRIMARY KEY,
            title TEXT,
            dek TEXT,
            accent_hex TEXT,
            status TEXT,
            primary_program_slugs TEXT,
            primary_conference_slug TEXT,
            voice_register_source TEXT,
            chapter_count INTEGER,
            last_chapter_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE storyline_chapters (
            id INTEGER PRIMARY KEY,
            thread_slug TEXT,
            chapter_number INTEGER,
            title TEXT,
            dek TEXT,
            body_markdown TEXT,
            byline TEXT,
            published_at TEXT,
            referenced_chapter_ids TEXT,
            referenced_sources_json TEXT,
            pull_quote TEXT
        )
        """
    )

    # wire_entries
    cur.execute(
        """
        CREATE TABLE wire_entries (
            id INTEGER PRIMARY KEY,
            occurred_at TEXT,
            program_slug TEXT,
            program_display TEXT,
            actor_kind TEXT,
            action TEXT,
            why_it_matters TEXT,
            impact_label TEXT,
            impact_color TEXT,
            historical_comp TEXT,
            source_name TEXT,
            related_thread_slug TEXT,
            fan_intel_velocity_spike INTEGER
        )
        """
    )

    # predictive_claims (v5.3 'receipts')
    cur.execute(
        """
        CREATE TABLE predictive_claims (
            id INTEGER PRIMARY KEY,
            source_kind TEXT,
            source_slug TEXT,
            claim_summary_short TEXT,
            surprise_index REAL,
            outcome_verdict TEXT,
            outcome_text TEXT,
            outcome_resolved INTEGER,
            outcome_resolved_at TEXT,
            aged_well_pct REAL
        )
        """
    )

    # team_chronicle_observations
    cur.execute(
        """
        CREATE TABLE team_chronicle_observations (
            team_chronicle_observation_id INTEGER PRIMARY KEY,
            team_id INTEGER,
            season_year INTEGER,
            week INTEGER,
            card_type TEXT,
            headline TEXT,
            body_md TEXT,
            source_attribution TEXT,
            surprise_score REAL,
            is_published INTEGER,
            generated_at_utc TEXT
        )
        """
    )

    # mailbag
    cur.execute(
        """
        CREATE TABLE mailbag_submissions (
            id INTEGER PRIMARY KEY,
            submitter_handle TEXT,
            question_text TEXT,
            topic_tags_json TEXT,
            status TEXT,
            submitted_at_utc TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE mailbag_answers (
            edition_slug TEXT,
            rank_position INTEGER,
            primary_topic TEXT,
            answer_body TEXT,
            generation_model TEXT
        )
        """
    )

    # canon
    cur.execute(
        """
        CREATE TABLE canon_entries (
            id INTEGER PRIMARY KEY,
            list_slug TEXT,
            rank INTEGER,
            entity_kind TEXT,
            entity_slug TEXT,
            entity_display_name TEXT,
            program_slug TEXT,
            program_label TEXT,
            era_label TEXT,
            summary_short TEXT,
            editorial_paragraph TEXT,
            statline TEXT,
            cohort_split_stat_rank INTEGER,
            cohort_split_casual_rank INTEGER,
            cohort_split_label TEXT,
            prior_year_rank INTEGER,
            rank_delta_label TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE canon_revision_history (
            list_slug TEXT,
            edition_year INTEGER,
            entity_slug TEXT,
            rank_in_year INTEGER
        )
        """
    )

    # fanbase / mood / lexicon
    cur.execute(
        """
        CREATE TABLE fanbase_mood_weekly (
            mood_weekly_id INTEGER PRIMARY KEY,
            team_id INTEGER,
            week_start_date TEXT,
            mood_score INTEGER,
            delta_from_prev_week INTEGER,
            top_cause_token TEXT,
            top_cause_label TEXT,
            sample_size INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE team_cohort_week (
            team_id INTEGER,
            cohort TEXT,
            week TEXT,
            effective_n REAL,
            sentiment_score REAL,
            volume INTEGER,
            top_source_ids TEXT,
            confidence_tier TEXT,
            PRIMARY KEY (team_id, cohort, week)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE team_cohort_divergence_week (
            team_id INTEGER,
            week TEXT,
            divergence_score REAL,
            num_cohorts_qualifying INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE rivalry_obsession_weekly (
            rivalry_weekly_id INTEGER PRIMARY KEY,
            rivalry_slug TEXT,
            rivalry_name TEXT,
            team_a_id INTEGER,
            team_b_id INTEGER,
            week_start_date TEXT,
            a_mentions_b_count INTEGER,
            b_mentions_a_count INTEGER,
            ratio_dominant REAL,
            leaning_team INTEGER,
            take TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE lexicon_weekly (
            lexicon_weekly_id INTEGER PRIMARY KEY,
            phrase TEXT,
            week_start_date TEXT,
            mention_count INTEGER,
            spike_pct_wow REAL,
            origin_community TEXT,
            related_team_id INTEGER,
            sample_quotes_json TEXT,
            narrative TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE fanbase_classification_history (
            classification_history_id INTEGER PRIMARY KEY,
            team_id INTEGER,
            season_year INTEGER,
            primary_archetype_slug TEXT,
            primary_confidence REAL,
            modifier_slugs_json TEXT
        )
        """
    )

    # power ratings
    cur.execute(
        """
        CREATE TABLE power_ratings_weekly (
            power_rating_weekly_id INTEGER PRIMARY KEY,
            team_id INTEGER,
            season_year INTEGER,
            week INTEGER,
            model_run_id INTEGER,
            power_rating REAL,
            offense_rating REAL,
            defense_rating REAL
        )
        """
    )

    # team_profiles + team_brand
    cur.execute(
        """
        CREATE TABLE team_profiles (
            team_id INTEGER PRIMARY KEY,
            program_slug TEXT,
            program_tier INTEGER,
            voice_register TEXT,
            identity_phrase TEXT,
            mantra TEXT,
            tonal_template TEXT,
            profile_json TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE team_brand (
            team_brand_id INTEGER PRIMARY KEY,
            team_id INTEGER,
            primary_color TEXT,
            secondary_color TEXT,
            mascot_name TEXT,
            abbreviation_short TEXT
        )
        """
    )

    # heisman
    cur.execute(
        """
        CREATE TABLE heisman_rankings_weekly (
            heisman_ranking_id INTEGER PRIMARY KEY,
            season_year INTEGER,
            week INTEGER,
            player_id INTEGER,
            team_id INTEGER,
            rank_overall INTEGER,
            nowcast_rank INTEGER,
            forecast_rank INTEGER,
            latent_score REAL,
            win_probability REAL,
            finalist_probability REAL,
            any_ballot_probability REAL,
            market_implied_probability REAL,
            market_american_odds INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE heisman_market_odds_weekly (
            heisman_market_odds_id INTEGER PRIMARY KEY,
            season_year INTEGER,
            week INTEGER,
            player_id INTEGER,
            player_name TEXT,
            team_name TEXT,
            provider TEXT,
            american_odds INTEGER,
            decimal_odds REAL,
            implied_probability REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE heisman_vote_results (
            heisman_vote_result_id INTEGER PRIMARY KEY,
            season_year INTEGER,
            player_id INTEGER,
            place INTEGER,
            winner_flag INTEGER,
            finalist_flag INTEGER,
            first_place_votes INTEGER,
            total_points INTEGER
        )
        """
    )

    # player stats
    cur.execute(
        """
        CREATE TABLE player_game_stats (
            player_game_stat_id INTEGER PRIMARY KEY,
            game_id INTEGER,
            season_year INTEGER,
            week INTEGER,
            season_type TEXT,
            team_id INTEGER,
            player_id INTEGER,
            category TEXT,
            stat_type TEXT,
            stat_value_text TEXT,
            stat_value_num REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE player_usage_season (
            player_usage_season_id INTEGER PRIMARY KEY,
            player_id INTEGER,
            season_year INTEGER,
            week INTEGER,
            usage_overall REAL,
            usage_pass REAL,
            usage_rush REAL,
            usage_first_down REAL,
            usage_passing_downs REAL,
            usage_standard_downs REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE player_value_metrics (
            player_value_metric_id INTEGER PRIMARY KEY,
            player_id INTEGER,
            season_year INTEGER,
            week INTEGER,
            metric_name TEXT,
            metric_value REAL,
            plays INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE player_season_summary (
            player_season_summary_id INTEGER PRIMARY KEY,
            player_id INTEGER,
            season_year INTEGER,
            team_id INTEGER,
            position TEXT,
            class_year TEXT,
            cfb_index_score REAL,
            games_played INTEGER,
            snap_count_proxy INTEGER,
            wepa_total REAL,
            milestones_json TEXT,
            is_projected INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE player_honors (
            player_honor_id INTEGER PRIMARY KEY,
            player_id INTEGER,
            season_year INTEGER,
            week INTEGER,
            honor_scope TEXT,
            honor_name TEXT,
            selector TEXT,
            honor_team TEXT,
            position TEXT,
            placement INTEGER,
            consensus_flag INTEGER,
            unanimous_flag INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE player_nfl_draft (
            player_nfl_draft_id INTEGER PRIMARY KEY,
            draft_year INTEGER,
            round INTEGER,
            pick INTEGER,
            overall INTEGER,
            player_id INTEGER,
            player_name TEXT,
            position TEXT,
            college_team_id INTEGER,
            nfl_team TEXT,
            nfl_team_abbr TEXT
        )
        """
    )

    # conversations + source_observations
    cur.execute(
        """
        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY,
            source_name TEXT,
            source_author_name TEXT,
            source_channel TEXT,
            source_url TEXT,
            title_text TEXT,
            body_text TEXT,
            external_created_at_utc TEXT,
            is_deleted INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE source_observations (
            source_observation_id INTEGER PRIMARY KEY,
            source_id TEXT,
            entity_type TEXT,
            entity_id TEXT,
            entity_label TEXT,
            observed_at_utc TEXT,
            metric TEXT,
            value_numeric REAL,
            value_text TEXT,
            sample_window TEXT,
            capture_url TEXT
        )
        """
    )

    # offseason_week_map
    cur.execute(
        """
        CREATE TABLE offseason_week_map (
            season_year INTEGER,
            week INTEGER,
            phase TEXT,
            label TEXT
        )
        """
    )

    # daily
    cur.execute(
        """
        CREATE TABLE daily_editions (
            edition_date TEXT PRIMARY KEY,
            status TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE daily_takes (
            edition_date TEXT,
            rank_position INTEGER,
            headline TEXT,
            primary_entity_slug TEXT,
            primary_entity_type TEXT
        )
        """
    )

    # prediction market snapshots
    cur.execute(
        """
        CREATE TABLE prediction_market_snapshots (
            id INTEGER PRIMARY KEY,
            provider TEXT,
            market_key TEXT,
            market_type TEXT,
            team_id INTEGER,
            outcome_label TEXT,
            implied_probability REAL,
            last_price REAL,
            snapshot_time_utc TEXT
        )
        """
    )

    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Per-builder smoke tests — empty DB (no tables at all)
# ---------------------------------------------------------------------------


def test_edition_cover_context_empty_db(empty_db):
    """Builder must not crash on a totally empty DB; must return the
    full set of manifest keys."""
    ctx = B.build_edition_cover_context(2026, 5, empty_db)
    assert isinstance(ctx, dict)
    expected = {
        "season",
        "week",
        "prior_4_covers",
        "cohort_mood_dumbbell",
        "rank_disagreements",
        "active_storylines",
        "major_wire_7d",
        "resolved_receipts",
        "top_chronicle_moments",
        "season_phase",
    }
    assert expected.issubset(ctx.keys())
    # All list-shaped fields default to []
    for key in (
        "prior_4_covers",
        "cohort_mood_dumbbell",
        "rank_disagreements",
        "active_storylines",
        "major_wire_7d",
        "resolved_receipts",
        "top_chronicle_moments",
    ):
        assert ctx[key] == [], f"{key} should be empty list, got {ctx[key]!r}"


def test_daily_lead_context_empty_db(empty_db):
    ctx = B.build_daily_lead_context(date(2026, 5, 15), empty_db)
    expected = {
        "date",
        "week_iso",
        "headline_entity_slug",
        "headline_entity_team_id",
        "mood_delta_7d",
        "mood_same_week_1yr_ago",
        "cohort_transitions",
        "cohort_divergence",
        "archive_threads",
        "recent_daily_headlines",
        "power_delta_7d",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["headline_entity_slug"] is None
    assert ctx["archive_threads"] == []


def test_heisman_weekly_context_empty_db(empty_db):
    ctx = B.build_heisman_weekly_context(2026, 7, empty_db)
    expected = {
        "season",
        "week",
        "top_10",
        "market_odds",
        "vote_history_archetype_comps",
        "last_4_games_top_5",
        "conversation_volume_top_5",
        "archive_threads",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["top_10"] == []
    assert ctx["last_4_games_top_5"] == []


def test_storyline_chapter_context_empty_db(empty_db):
    ctx = B.build_storyline_chapter_context("portal-szn-2026", empty_db)
    expected = {
        "thread_slug",
        "thread",
        "last_3_chapters",
        "wire_per_primary_program",
        "conversation_quotes",
        "source_observations",
        "prior_referenced_sources",
        "archive_threads",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["thread"] is None
    assert ctx["last_3_chapters"] == []
    assert ctx["wire_per_primary_program"] == []


def test_mailbag_context_empty_db(empty_db):
    ctx = B.build_mailbag_context(42, empty_db)
    expected = {
        "question_id",
        "question",
        "topic_tags",
        "conversation_quotes",
        "fanbase_classification_history",
        "archive_threads",
        "past_mailbag_answers",
        "active_storylines_matching",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["question"] is None
    assert ctx["topic_tags"] == []


def test_reaction_context_empty_db(empty_db):
    ctx = B.build_reaction_context(999, empty_db)
    expected = {
        "wire_id",
        "wire",
        "historical_comp",
        "cohort_divergence",
        "archive_threads",
        "mood_delta_7d",
        "recruiting_rank",
        "player_season_context",
        "player_honors",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["wire"] is None
    assert ctx["cohort_divergence"] == []


def test_chronicle_context_empty_db(empty_db):
    ctx = B.build_chronicle_context("alabama", 7, empty_db)
    expected = {
        "program_slug",
        "week",
        "team_id",
        "candidate_observations_evidence",
        "recent_chronicle_headlines",
        "fanbase_classification_history",
        "power_ratings_sparkline_6y",
        "player_archetype_peers",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["team_id"] is None
    assert ctx["recent_chronicle_headlines"] == []


def test_team_narrative_context_empty_db(empty_db):
    ctx = B.build_team_narrative_context("oregon", empty_db)
    expected = {
        "program_slug",
        "team_id",
        "signature_metrics_ladder",
        "mood_arc_12w",
        "nfl_alumni_active",
        "recruiting_trajectory_5y",
        "recent_edition_mentions",
        "top_chronicle_90d",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["team_id"] is None
    assert ctx["recent_edition_mentions"] == []


def test_pulse_state_context_empty_db(empty_db):
    ctx = B.build_pulse_state_context("texas", empty_db)
    expected = {
        "program_slug",
        "team_id",
        "cohort_transitions_4w",
        "mood_arc_4w",
        "mood_same_week_1yr_ago",
        "cohort_divergence_4w",
        "lexicon_spikes",
        "wire_7d",
        "rivalry_obsession_weekly",
        "power_delta_7d",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["team_id"] is None


def test_wire_why_it_matters_context_empty_db(empty_db):
    ctx = B.build_wire_why_it_matters_context(123, empty_db)
    expected = {
        "wire_id",
        "wire",
        "archetype_history_5yr",
        "recruiting_rank",
        "nfl_pipeline",
        "team_brand",
        "mood_delta_7d",
        "prediction_market_snapshots",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["wire"] is None


def test_canon_top10_context_empty_db(empty_db):
    ctx = B.build_canon_top10_context("greatest-players-of-cfp-era", 1, empty_db)
    expected = {
        "list_slug",
        "rank",
        "entry",
        "prior_year_entry",
        "cohort_split",
        "final_power_rank",
        "nfl_drafted_from_season",
        "top_chronicle_3",
        "archive_thread",
        "prior_editions",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["entry"] is None
    assert ctx["nfl_drafted_from_season"] == []


def test_player_season_narrative_context_empty_db(empty_db):
    ctx = B.build_player_season_narrative_context(7, 2025, empty_db)
    expected = {
        "player_id",
        "season",
        "player",
        "season_games",
        "usage",
        "value_metrics",
        "season_summary",
        "honors",
        "heisman_position",
        "archetype_peers",
        "nfl_pipeline_program_history",
        "conversation_quotes",
        "team_brand",
        "chronicle_tie_ins",
    }
    assert expected.issubset(ctx.keys())
    assert ctx["player"] is None
    assert ctx["season_games"] == []
    assert ctx["archetype_peers"] == []


# ---------------------------------------------------------------------------
# Minimal-DB sanity — tables exist but empty
# ---------------------------------------------------------------------------


def test_all_builders_run_on_minimal_db(minimal_db):
    """Every builder runs cleanly when all manifest tables exist but
    carry zero rows. This is the "happy empty" state right after a
    fresh ``apply_runtime_migrations`` on a new DB."""
    # exercise each builder once
    assert B.build_edition_cover_context(2026, 5, minimal_db)
    assert B.build_daily_lead_context(date(2026, 5, 15), minimal_db)
    assert B.build_heisman_weekly_context(2026, 7, minimal_db)
    assert B.build_storyline_chapter_context("realignment-2026", minimal_db)
    assert B.build_mailbag_context(1, minimal_db)
    assert B.build_reaction_context(1, minimal_db)
    assert B.build_chronicle_context("alabama", 7, minimal_db)
    assert B.build_team_narrative_context("oregon", minimal_db)
    assert B.build_pulse_state_context("texas", minimal_db)
    assert B.build_wire_why_it_matters_context(1, minimal_db)
    assert B.build_canon_top10_context("greatest-coaches", 5, minimal_db)
    assert B.build_player_season_narrative_context(1, 2025, minimal_db)


def test_minimal_db_resolves_slug_to_team_id(minimal_db):
    """Helper smoke test: slug → team_id resolves when rows exist."""
    minimal_db.execute(
        "INSERT INTO teams (team_id, school_slug) VALUES (?, ?)",
        (42, "alabama"),
    )
    minimal_db.commit()
    ctx = B.build_chronicle_context("alabama", 7, minimal_db)
    assert ctx["team_id"] == 42


def test_minimal_db_returns_inserted_wire_row(minimal_db):
    """Helper smoke test: when a wire row exists, the builder returns
    its dict, not None. Confirms the SQL is correct (not just falling
    through to the error branch)."""
    minimal_db.execute(
        """
        INSERT INTO wire_entries
            (id, occurred_at, program_slug, program_display, actor_kind,
             action, why_it_matters, impact_label, impact_color,
             source_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            7,
            "2026-05-14T12:00:00",
            "alabama",
            "Alabama",
            "player",
            "Portal QB commit",
            "Why it matters body",
            "MAJOR",
            "amber",
            "247Sports",
        ),
    )
    minimal_db.commit()
    ctx = B.build_wire_why_it_matters_context(7, minimal_db)
    assert ctx["wire"] is not None
    assert ctx["wire"]["program_slug"] == "alabama"
    assert ctx["wire"]["impact_label"] == "MAJOR"


# ---------------------------------------------------------------------------
# Direct helper sanity (private, but exercised through the public surface)
# ---------------------------------------------------------------------------


def test_rows_helper_returns_empty_on_missing_table(empty_db):
    """Public-style smoke: the internal ``_rows`` helper must swallow
    sqlite3.Error and return ``[]`` on a missing-table query."""
    out = B._rows(empty_db, "SELECT * FROM no_such_table")
    assert out == []


def test_row_helper_returns_none_on_missing_table(empty_db):
    out = B._row(empty_db, "SELECT * FROM no_such_table")
    assert out is None
