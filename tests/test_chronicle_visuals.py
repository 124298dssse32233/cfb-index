"""Chronicle Visuals smoke tests.

Live-DB-backed test against cfb_rankings.db. The 2024 season is required to
have stable rows for the visuals we ship in v1. If the test runs in CI with
a fresh DB (no 2024 data), the live-render tests are skipped automatically.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def db():
    db_path = Path(__file__).resolve().parents[1] / "cfb_rankings.db"
    if not db_path.exists():
        pytest.skip("cfb_rankings.db not present — live-render tests skipped")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # Apply migration if missing
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='chronicle_visual_cache'"
    )
    if not cur.fetchone():
        mig = Path(__file__).resolve().parents[1] / "migrations" / "20260526_01_chronicle_visual_cache.sql"
        conn.executescript(mig.read_text())
        conn.commit()
    yield conn
    conn.close()


def test_visual_models_importable():
    from cfb_rankings.chronicle.visuals.models import (
        VisualSpec, VisualReceipt, VisualResult, VisualQualityScore,
        ChartFamily, VisualId, EntityScope, Annotation, ConfidenceBand,
    )
    spec = VisualSpec(
        visual_id=VisualId.STATEMENT_WIN_LADDER,
        chart_family=ChartFamily.WATERFALL,
        headline_finding="A clean one-sentence finding under one hundred characters.",
        data_query_id="statement_win_ladder_v1",
        entity_scope=EntityScope(slug="alabama", season_year=2024),
    )
    assert spec.headline_finding.startswith("A clean")
    assert spec.chart_family == ChartFamily.WATERFALL


def test_scorer_recalibrated_weights_sum_to_one():
    from cfb_rankings.chronicle.visuals import scorer
    total = (
        scorer.WEIGHT_CLARITY
        + scorer.WEIGHT_FAN_RELEVANCE
        + scorer.WEIGHT_DATA_DEPTH
        + scorer.WEIGHT_NOVELTY
        + scorer.WEIGHT_MOBILE_LEGIBILITY
        + scorer.WEIGHT_SCREENSHOT_VALUE
        + scorer.WEIGHT_EVIDENCE_STRENGTH
        + scorer.WEIGHT_VOICE_FIT
    )
    assert abs(total - 1.0) < 1e-9, f"weights must sum to 1.0; got {total}"


def test_scorer_returns_in_range():
    from cfb_rankings.chronicle.visuals.scorer import score_visual
    from cfb_rankings.chronicle.visuals.models import (
        VisualSpec, VisualReceipt, ChartFamily, VisualId, EntityScope, ConfidenceBand,
    )
    spec = VisualSpec(
        visual_id=VisualId.STATEMENT_WIN_LADDER,
        chart_family=ChartFamily.WATERFALL,
        headline_finding="Alabama won three statement games this season.",
        data_query_id="statement_win_ladder_v1",
        entity_scope=EntityScope(slug="alabama", season_year=2024),
    )
    receipt = VisualReceipt(
        query_id="statement_win_ladder_v1",
        source_tables=["team_rating_deltas", "games"],
        sample_n=8,
        confidence=ConfidenceBand.HIGH,
    )
    score = score_visual(spec, receipt)
    assert 0.0 <= score.total <= 1.0
    assert 0.0 <= score.clarity <= 1.0


def test_cache_key_deterministic():
    from cfb_rankings.chronicle.visuals.cache import compute_visual_cache_key
    args = dict(
        slug="alabama", entity_kind="team", season_year=2024, week_number=None,
        visual_id="statement_win_ladder", data_query_id="statement_win_ladder_v1",
        renderer_version="v1.0.0", data_fingerprint="abc123", schema_version="v3.0",
    )
    k1 = compute_visual_cache_key(**args)
    k2 = compute_visual_cache_key(**args)
    assert k1 == k2
    assert len(k1) == 32
    # Different fingerprint -> different key
    args["data_fingerprint"] = "xyz789"
    assert compute_visual_cache_key(**args) != k1


def test_registry_complete():
    from cfb_rankings.chronicle.visuals import registry, models
    for vid in (
        models.VisualId.STATEMENT_WIN_LADDER,
        models.VisualId.RETURNING_PRODUCTION_XRAY,
        models.VisualId.HEISMAN_RACE_BRAID,
        models.VisualId.ROSTER_REPLACEMENT_GRID,
    ):
        family = registry.get_chart_family(vid)
        query_fn = registry.get_query_function(vid)
        render_fn = registry.get_renderer_function(vid)
        assert family
        assert callable(query_fn)
        assert callable(render_fn)


def test_alabama_full_pipeline(db):
    """End-to-end: generate, score, store, fetch round-trip on real data."""
    cur = db.execute("SELECT 1 FROM team_rating_deltas LIMIT 1")
    if not cur.fetchone():
        pytest.skip("team_rating_deltas empty — live pipeline test skipped")

    from cfb_rankings.chronicle.visuals import generate_visuals_for_team, fetch_visual_cards
    # Pass the PREVIEW season (2025): preview visuals query 2025, retrospective
    # visuals auto-resolve to 2024 (posture-aware seasoning).
    results = generate_visuals_for_team(db, slug="alabama", season_year=2025, force_regenerate=True)
    assert len(results) >= 1, "expected at least 1 visual generated"

    # Every result has SVG content and a score
    for r in results:
        assert r.svg_html and "<svg" in r.svg_html
        assert 0.0 <= r.score.total <= 1.0
        assert r.spec.headline_finding

    # Round-trip via fetch (season_year=None -> posture-aware cross-season).
    # fetch dedups by visual_id, so it returns one card per distinct visual.
    cards = fetch_visual_cards(db, "alabama", season_year=None)
    distinct_ids = {r.spec.visual_id.value for r in results if not r.suppressed}
    assert len(cards) == len(distinct_ids)
    for c in cards:
        assert c["svg_html"] and "<svg" in c["svg_html"]
        assert c["visual_quality_score"] is not None


def test_force_regenerate_preserves_lkg_flag(db):
    """Regression: INSERT OR REPLACE must not nuke prior is_lkg=1 on force-regen."""
    cur = db.execute("SELECT 1 FROM team_rating_deltas LIMIT 1")
    if not cur.fetchone():
        pytest.skip("team_rating_deltas empty — skipping LKG test")

    from cfb_rankings.chronicle.visuals import (
        generate_visuals_for_team, promote_visual_lkg, VisualId,
    )
    # First pass — ensure a row exists. STATEMENT_WIN_LADDER is retrospective,
    # so passing preview-season 2025 makes it query 2024 (which has data).
    results = generate_visuals_for_team(
        db, slug="alabama", season_year=2025,
        visual_ids=[VisualId.STATEMENT_WIN_LADDER],
        force_regenerate=True,
    )
    assert results
    key = results[0].visual_cache_key

    # Promote to LKG
    assert promote_visual_lkg(db, key)
    row = db.execute(
        "SELECT is_lkg, lkg_promoted_at_utc FROM chronicle_visual_cache WHERE visual_cache_key = ?",
        (key,),
    ).fetchone()
    assert row["is_lkg"] == 1
    promoted_at = row["lkg_promoted_at_utc"]
    assert promoted_at

    # Force-regenerate — LKG MUST survive
    generate_visuals_for_team(
        db, slug="alabama", season_year=2025,
        visual_ids=[VisualId.STATEMENT_WIN_LADDER],
        force_regenerate=True,
    )
    after = db.execute(
        "SELECT is_lkg, lkg_promoted_at_utc FROM chronicle_visual_cache WHERE visual_cache_key = ?",
        (key,),
    ).fetchone()
    assert after["is_lkg"] == 1, "force-regenerate erased the LKG flag"
    assert after["lkg_promoted_at_utc"] == promoted_at, "LKG promotion timestamp was reset"


def test_no_double_escape_in_svg():
    """Regression: text() already escapes; renderers must not pre-escape."""
    from cfb_rankings.chronicle.visuals.families import ladder, braid
    # Opponent name with ampersand — single escape -> &amp; ; double escape -> &amp;amp;
    fake_ladder = {
        "rows": [{
            "game_id": 1, "week": 1, "opponent_slug": "tam",
            "opponent_name": "Texas A&M", "result_text": "W 10-3",
            "total_delta": 1.0, "power_delta": 0.5, "resume_delta": 0.5,
            "offense_delta": 0.5, "defense_delta": 0.5, "is_win": True,
            "is_top_result": True,
        }],
        "summary_stats": {},
    }
    out = ladder.render_statement_win_ladder(fake_ladder)
    assert "&amp;amp;" not in out["svg_html"], "ladder double-escapes opponent name"
    assert "Texas A&amp;M" in out["svg_html"], "ladder lost the ampersand entirely"

    fake_braid = {
        "rows": [{
            "player_id": 1, "player_name": "T&J Henderson",
            "team_slug": "alabama", "current_rank": 1,
            "history": [{"week": 1, "rank": 1, "latent_score": 1.0, "finalist_probability": 0.5}],
        }],
        "summary_stats": {"season_year": 2024, "snapshot_week": 1},
    }
    out2 = braid.render_heisman_race_braid(fake_braid)
    assert "&amp;amp;" not in out2["svg_html"], "braid double-escapes player name"


def test_renderer_produces_inline_svg():
    """Smoke renderer with synthetic data — no DB."""
    from cfb_rankings.chronicle.visuals.families import ladder
    fake = {
        "rows": [
            {
                "game_id": 1, "week": 4, "opponent_slug": "wisconsin",
                "opponent_name": "Wisconsin", "result_text": "W 42-10",
                "total_delta": 2.5, "power_delta": 1.5, "resume_delta": 1.0,
                "offense_delta": 1.2, "defense_delta": 0.8, "is_win": True,
                "is_top_result": True,
            },
            {
                "game_id": 2, "week": 6, "opponent_slug": "texas",
                "opponent_name": "Texas", "result_text": "W 21-14",
                "total_delta": 1.0, "power_delta": 0.6, "resume_delta": 0.4,
                "offense_delta": 0.4, "defense_delta": 0.6, "is_win": True,
            },
        ],
        "summary_stats": {"delta_spread": 1.5, "total_games": 2, "team_id": 277},
    }
    out = ladder.render_statement_win_ladder(fake)
    assert "<svg" in out["svg_html"]
    assert "Wisconsin" in out["svg_html"]
    assert out["headline_finding"]
    assert out["alt_text"]
