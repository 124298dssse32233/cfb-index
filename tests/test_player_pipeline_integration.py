"""End-to-end integration test for the Feature B pipeline.

Proves the whole chain works against a fixture DB, from raw corpus to
rendered template:

    conversation_documents + team targets
        → tag_player_mentions            (writes player targets)
        → compute_player_week_mood       (writes aggregate rows)
        → fetch_player_mood_profile      (has_data=True)
        → _render_the_room_card          (ready state, no --empty)

If any layer of the pipeline regresses, this test fails — so it's the
cheapest safety net for when the ingestion pipeline finally starts
populating player_id on real data.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.cohorts.player_aggregate import compute_player_week_mood
from cfb_rankings.fan_intelligence import fetch_player_mood_profile
from cfb_rankings.ingest.player_name_tagger import tag_player_mentions


SEASON = 2025
WEEK = 12
CARR_ID = 4788


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    db_path = tmp_path / "pipeline.db"
    conn = sqlite3.connect(db_path)
    _schema(conn)
    _seed(conn)
    conn.commit()
    conn.close()
    return Database(str(db_path))


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            full_name TEXT, position TEXT
        );
        CREATE TABLE player_value_metrics (
            player_value_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER, player_id INTEGER, team_id INTEGER,
            team_name TEXT, player_name TEXT, conference_name TEXT,
            position TEXT, metric_name TEXT, metric_value REAL, plays INTEGER
        );
        CREATE TABLE player_season_stats (
            player_season_stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER, player_id INTEGER, team_id INTEGER,
            team_name TEXT, player_name TEXT, conference_name TEXT,
            position TEXT, category TEXT, stat_type TEXT, stat_value_num REAL
        );
        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT, source_author_id TEXT, source_author_name TEXT,
            source_url TEXT, capture_url TEXT,
            body_text TEXT, title_text TEXT,
            like_count INTEGER DEFAULT 0, reply_count INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0
        );
        CREATE TABLE conversation_document_targets (
            conversation_document_target_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_document_id INTEGER NOT NULL,
            season_year INTEGER, week INTEGER,
            team_id INTEGER, player_id INTEGER,
            target_type TEXT, target_key TEXT, target_label TEXT,
            affiliation_team_id INTEGER, audience_bucket TEXT,
            sentiment_score REAL, emotion_primary TEXT, sarcasm_score REAL,
            confidence_score REAL, is_primary_target INTEGER DEFAULT 0
        );
        CREATE TABLE player_week_conversation_features (
            player_week_conversation_feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER NOT NULL, week INTEGER NOT NULL,
            player_id INTEGER NOT NULL, team_id INTEGER,
            source_name TEXT, audience_bucket TEXT NOT NULL,
            mention_count INTEGER DEFAULT 0, unique_author_count INTEGER DEFAULT 0,
            positive_doc_count INTEGER DEFAULT 0,
            neutral_doc_count INTEGER DEFAULT 0,
            negative_doc_count INTEGER DEFAULT 0,
            mean_sentiment_score REAL, net_sentiment_score REAL,
            joy_share REAL, anger_share REAL, fear_share REAL,
            trust_share REAL, sadness_share REAL, surprise_share REAL,
            attention_score REAL, sample_quality_score REAL,
            sarcasm_risk TEXT, top_storyline_json TEXT, top_quote_json TEXT,
            sample_n INTEGER, sample_window TEXT,
            confidence_floor TEXT, model_version TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX ux_pwcf_keys ON player_week_conversation_features (
            player_id, season_year, week, COALESCE(source_name, ''), audience_bucket
        );
        """
    )


def _seed(conn: sqlite3.Connection) -> None:
    # Make Carr a real active 2025 QB so the tagger index includes him.
    conn.execute("INSERT INTO players VALUES (?,?,?)", (CARR_ID, "C.J. Carr", "QB"))
    conn.execute(
        """INSERT INTO player_value_metrics
           (season_year, player_id, team_id, team_name, player_name,
            conference_name, position, metric_name, metric_value, plays)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (SEASON, CARR_ID, 1, "Notre Dame", "C.J. Carr",
         "FBS Independents", "QB", "wepa_passing", 0.41, 307),
    )

    # 15 fan documents that mention Carr — enough to clear MIN_MENTIONS_FOR_SIGNAL.
    for i in range(15):
        body = (
            f"C.J. Carr is carrying Notre Dame right now — absolute QB1 vibes. "
            f"That deep ball in the Stanford game was something else ({i})."
        )
        cur = conn.execute(
            """INSERT INTO conversation_documents
               (source_name, source_author_id, source_author_name, body_text,
                like_count, reply_count)
               VALUES (?,?,?,?,?,?)""",
            ("reddit_notredame", f"nd_fan_{i}", f"ndFaithful{i}", body, 20, 3),
        )
        doc_id = cur.lastrowid
        # Team target (Notre Dame, fan) with positive sentiment.
        conn.execute(
            """INSERT INTO conversation_document_targets
               (conversation_document_id, season_year, week, team_id,
                target_type, audience_bucket, sentiment_score, emotion_primary,
                confidence_score, is_primary_target)
               VALUES (?,?,?,?,?,?,?,?,?,1)""",
            (doc_id, SEASON, WEEK, 1, "team", "fan", 0.6, "trust", 0.9),
        )


# ---------------------------------------------------------------------------
# The integration test
# ---------------------------------------------------------------------------


def test_raw_docs_to_rendered_card(db: Database) -> None:
    # Stage 1 — nothing player-scoped exists yet.
    pre = db.query_all(
        "select count(*) as n from conversation_document_targets where target_type='player'",
        {},
    )
    assert pre[0]["n"] == 0

    # Profile with zero rows: skeleton.
    empty_profile = fetch_player_mood_profile(db, CARR_ID, SEASON, WEEK)
    assert empty_profile["has_data"] is False

    # Stage 2 — run the tagger in commit mode.
    tag_result = tag_player_mentions(db, season_year=SEASON, commit=True)
    assert tag_result["rows_written"] > 0, "tagger should have matched Carr's full name in 15 docs"

    # Stage 3 — run the aggregator.
    agg_result = compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    assert agg_result["players_touched"] >= 1
    assert agg_result["cells_written"] >= 1

    # Stage 4 — the reader now sees data for Carr.
    profile = fetch_player_mood_profile(db, CARR_ID, SEASON, WEEK)
    assert profile["has_data"] is True, (
        "end-to-end pipeline broke: tagger + aggregator ran but reader still sees no signal"
    )
    # Belief should trend positive (all 15 source docs have sentiment_score=0.6
    # which is firmly above POS_CUTOFF).
    assert (profile["belief"] or {}).get("score") is not None
    assert profile["belief"]["score"] > 0

    # Stage 5 — the Figma shell template renders the ready state.
    # We import the renderer directly; calling build-site is prohibitive for
    # a unit test.
    from cfb_rankings.reporting import _render_the_room_card
    html = _render_the_room_card(profile, "C.J. Carr")
    assert 'data-state="ready"' in html
    assert "the-room--empty" not in html
    assert "C.J. Carr" in html


def test_empty_pipeline_leaves_renderer_in_skeleton_state(db: Database) -> None:
    """Without running the tagger/aggregator, the renderer still emits a valid card."""
    # No tagger, no aggregator — everything empty.
    profile = fetch_player_mood_profile(db, CARR_ID, SEASON, WEEK)
    from cfb_rankings.reporting import _render_the_room_card
    html = _render_the_room_card(profile, "C.J. Carr")
    assert 'data-state="empty"' in html
    assert "the-room--empty" in html
    assert "Awaiting Signal" in html


def test_season_rollup_surfaces_card_when_no_single_week_clears(db: Database) -> None:
    """Fragmented mentions across weeks should unlock the card via rollup.

    Each doc in the fixture is week=12; to exercise rollup, we add 8 more
    docs spread across weeks 13–20 so no single week clears the 12-mention
    floor but the season total does.
    """
    from cfb_rankings.cohorts.player_aggregate import compute_player_season_mood
    from cfb_rankings.fan_intelligence import compute_player_mood_index

    # The fixture already seeded 15 fan-bucket team targets at week=12.
    # Move most of them to later weeks so week=12 drops below the floor.
    conn = sqlite3.connect(db._path)
    conn.execute(
        """
        update conversation_document_targets
           set week = case
                        when conversation_document_id % 4 = 0 then 13
                        when conversation_document_id % 4 = 1 then 14
                        when conversation_document_id % 4 = 2 then 15
                        else 16
                      end
         where target_type = 'team'
        """
    )
    conn.commit()
    conn.close()

    # First ensure the tagger is live and the weekly aggregates reflect the spread.
    tag_player_mentions(db, season_year=SEASON, commit=True)
    # Aggregate every week in which we have data.
    for wk in (12, 13, 14, 15, 16):
        compute_player_week_mood(db, f"{SEASON}-{wk:02d}")

    # Weekly-only reader, primary week=12: no single week clears.
    weekly_only = compute_player_mood_index(
        db, SEASON, WEEK, fallback_to_season_rollup=False,
    )
    assert CARR_ID not in weekly_only, (
        "weekly-only path should NOT surface Carr — no single week has 12 mentions"
    )

    # Run the season rollup.
    season_result = compute_player_season_mood(db, SEASON)
    assert season_result["cells_written"] >= 1

    # Reader with rollup fallback: Carr surfaces via the season path.
    with_rollup = compute_player_mood_index(
        db, SEASON, WEEK, fallback_to_season_rollup=True,
    )
    assert CARR_ID in with_rollup, "season rollup fallback should unlock Carr"
    story = with_rollup[CARR_ID]
    assert story["scope"] == "season"
    assert story["week"] == 0
    assert story["primary_bucket"] == "fan"
    assert story["sample"]["mentions"] >= 12
    assert "Season" in story["updated_label"]


def test_primary_bucket_prefers_fan_over_national(db: Database) -> None:
    """When BOTH fan and national clear the floor, belief must come from fan."""
    from cfb_rankings.cohorts.player_aggregate import compute_player_season_mood
    from cfb_rankings.fan_intelligence import compute_player_mood_index

    # Add 14 national-bucket targets with NEGATIVE sentiment; fan already has
    # 15 positive at week=12. Both clear the floor, but fan must win.
    conn = sqlite3.connect(db._path)
    for i in range(14):
        cur = conn.execute(
            """INSERT INTO conversation_documents
               (source_name, source_author_id, body_text, like_count)
               VALUES (?,?,?,?)""",
            ("cfb_national", f"nat_author_{i}", f"Eh, Carr is overrated ({i})", 1),
        )
        doc_id = cur.lastrowid
        conn.execute(
            """INSERT INTO conversation_document_targets
               (conversation_document_id, season_year, week, team_id,
                target_type, audience_bucket, sentiment_score, emotion_primary,
                confidence_score, is_primary_target)
               VALUES (?,?,?,?,?,?,?,?,?,1)""",
            (doc_id, SEASON, WEEK, 1, "team", "national", -0.4, "anger", 0.9),
        )
    conn.commit()
    conn.close()

    tag_player_mentions(db, season_year=SEASON, commit=True)
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    compute_player_season_mood(db, SEASON)

    profile = compute_player_mood_index(db, SEASON, WEEK)[CARR_ID]
    assert profile["primary_bucket"] == "fan", (
        "fan should win when both buckets clear gates — rival/national must not drive belief"
    )
    # Fan belief trends positive (sentiment=0.6 baseline).
    assert profile["belief"]["score"] > 0


def test_aggregator_reruns_cleanly_after_new_docs(db: Database) -> None:
    """Second tag + aggregate pass doesn't duplicate rows."""
    tag_player_mentions(db, season_year=SEASON, commit=True)
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")

    # Count rows after first pass.
    first = db.query_all(
        "select count(*) as n from player_week_conversation_features",
        {},
    )
    first_count = first[0]["n"]

    # Re-run both without new data.
    tag_player_mentions(db, season_year=SEASON, commit=True)
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    second = db.query_all(
        "select count(*) as n from player_week_conversation_features",
        {},
    )
    assert second[0]["n"] == first_count, "aggregator duplicated rows on re-run"
