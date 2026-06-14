"""Tests for the belief visual family + the shared Editorial Grammar.

Covers (design-system 73/76/77):
  - the Editorial Grammar is reused by every belief/player renderer (one look);
  - renderers are deterministic and score above the suppression floor;
  - the honesty gates fire (offseason/thin belief suppresses);
  - the entity-aware registry keeps player visuals out of the team pipeline.

Synthetic-fixture tests run anywhere; DB-backed gating tests skip without
cfb_rankings.db.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.chronicle.visuals.models import (
    VisualId, VisualSpec, VisualReceipt, EntityScope, ConfidenceBand, ChartFamily,
)
from cfb_rankings.chronicle.visuals.scorer import score_visual, VISUAL_SUPPRESS_THRESHOLD
from cfb_rankings.chronicle.visuals.families.mood import render_fan_mood_braid, render_home_away_mind
from cfb_rankings.chronicle.visuals.families.perception import render_perception_vs_tape
from cfb_rankings.chronicle.visuals.families.scatter import render_cfp_bubble_wall, render_talent_yield_curve
from cfb_rankings.chronicle.visuals.families.signals import render_delta_dna, render_continuity_stress_test
from cfb_rankings.chronicle.visuals.families.ladder import render_statement_win_ladder
from cfb_rankings.chronicle.visuals.families.waterfall import render_returning_production_xray
from cfb_rankings.chronicle.visuals.families.braid import render_heisman_race_braid
from cfb_rankings.chronicle.visuals.families.tilemosaic import render_roster_replacement_grid
from cfb_rankings.chronicle.visuals.families.conveyor import render_draft_pipeline_conveyor
from cfb_rankings.chronicle.visuals import registry


# --------------------------------------------------------------------------- #
# Synthetic fixtures (in-season, representative) — no DB required
# --------------------------------------------------------------------------- #

FMB = {"query_id": "fan_mood_braid_v1", "source_tables": ["backometer_weekly", "power_ratings_weekly", "teams"],
       "rows": [
           {"belief": 86, "model": 64, "gap": 22, "subject": True, "label": "Ohio State"},
           {"belief": 99, "model": 52, "gap": 47, "subject": False, "label": "Texas A&M"},
           {"belief": 8, "model": 96, "gap": -88, "subject": False, "label": "Indiana"},
           {"belief": 55, "model": 50, "gap": 5, "subject": False, "label": None},
           {"belief": 40, "model": 46, "gap": -6, "subject": False, "label": None},
       ],
       "sample_n": 540, "confidence": "high", "limitations": [], "summary_stats": {
           "team_name": "Ohio State", "belief_pctile": 86, "model_pctile": 64, "spots": 18, "n_cohort": 120,
           "gap_rank": 7, "zone": "cooking", "delta_wow": 6.2, "sample_size": 540, "belief_week": 10,
           "power_week": 10, "season_year": 2026, "is_offseason": False}}

HAM = {"query_id": "home_away_mind_v1", "source_tables": ["team_week_conversation_features", "teams"],
       "rows": [], "sample_n": 420, "confidence": "high", "limitations": [], "summary_stats": {
           "team_name": "Ohio State", "week": 10, "season_year": 2026, "fan_net": 0.34, "national_net": 0.05,
           "belonging_gap": 0.29, "n_fan": 420, "n_national": 210}}

PVT = {"query_id": "perception_vs_tape_v1",
       "source_tables": ["player_week_conversation_features", "player_value_metrics", "players"],
       "sample_n": 95, "confidence": "high", "limitations": [],
       "rows": [{"x": 95, "y": 82, "name": "Carson Beck", "subject": True, "peer": False},
                {"x": 99, "y": 41, "name": "Brendan Sorsby", "subject": False, "peer": True},
                {"x": 50, "y": 99, "name": "Test Topprod", "subject": False, "peer": True},
                {"x": 30, "y": 20, "name": "Joe Cohort", "subject": False, "peer": False}],
       "summary_stats": {"player_id": 1, "player_name": "Carson Beck", "position": "QB", "metric": "wepa_passing",
                         "season_year": 2025, "prod_season": 2024, "n_cohort": 47, "hype_pctile": 95,
                         "prod_pctile": 82, "quadrant": "PROVEN", "hype_mentions": 1500}}

CFP = {"query_id": "cfp_bubble_wall_v1",
       "source_tables": ["official_rankings", "power_ratings_weekly", "resume_ratings_weekly", "teams"],
       "sample_n": 25, "confidence": "high", "limitations": [],
       "rows": [{"x": 0.82, "y": 0.78, "label": "Alabama", "slug": "alabama", "peer_label": False},
                {"x": 0.95, "y": 0.92, "label": "Georgia", "slug": "georgia", "peer_label": True},
                {"x": 0.40, "y": 0.72, "label": "Ole Miss", "slug": "ole-miss", "peer_label": True},
                {"x": 0.60, "y": 0.55, "label": "Tennessee", "slug": "tennessee", "peer_label": False}],
       "summary_stats": {"anchor_slug": "alabama", "season_year": 2025, "snapshot_week": 12, "n_teams": 25}}

TYC = {"query_id": "talent_yield_curve_v1",
       "source_tables": ["team_talent_snapshots", "player_nfl_draft", "teams"],
       "sample_n": 60, "confidence": "medium", "limitations": [],
       "rows": [{"x": 0.90, "y": 0.70, "label": "Ohio State", "slug": "ohio-state", "peer_label": False},
                {"x": 0.95, "y": 0.95, "label": "Georgia", "slug": "georgia", "peer_label": True},
                {"x": 0.50, "y": 0.82, "label": "Iowa", "slug": "iowa", "peer_label": True},
                {"x": 0.30, "y": 0.25, "label": "Kansas", "slug": "kansas", "peer_label": False}],
       "summary_stats": {"anchor_slug": "ohio-state", "season_year": 2024, "n_programs": 60}}

DDNA = {"query_id": "delta_dna_v1", "source_tables": ["team_rating_deltas"],
        "sample_n": 12, "confidence": "high", "limitations": [],
        "rows": [{"power_delta": d} for d in [1.2, -0.8, 2.1, 0.3, -1.5, 1.8, 0.6, -0.4, 2.3, 0.9, -0.2, 1.1]],
        "summary_stats": {"season_year": 2024, "archetype": "boom-built", "volatility": 1.3, "mean_delta": 0.6}}

CST = {"query_id": "continuity_stress_test_v1", "source_tables": ["returning_production", "teams"],
       "sample_n": 5, "confidence": "medium", "limitations": [],
       "rows": [{"key": "QB", "label": "QB room", "value": 0.90, "league_avg": 0.55},
                {"key": "OL", "label": "O-line", "value": 0.40, "league_avg": 0.60},
                {"key": "OFF", "label": "Offense", "value": 0.70, "league_avg": 0.62},
                {"key": "DEF", "label": "Defense", "value": 0.65, "league_avg": 0.60},
                {"key": "TOT", "label": "Overall", "value": 0.68, "league_avg": 0.60}],
       "summary_stats": {"season_year": 2025, "stressed_key": "OL", "stressed_label": "O-line",
                         "anchored_label": "QB room", "overall_value": 0.68, "overall_avg": 0.60}}

SWL = {"query_id": "statement_win_ladder_v1", "source_tables": ["team_rating_deltas", "games", "teams"],
       "sample_n": 4, "confidence": "high", "limitations": [],
       "rows": [{"total_delta": 3.1, "result_text": "W 27-10", "opponent_name": "Georgia", "opponent_slug": "georgia", "is_win": True, "is_top_result": True},
                {"total_delta": 1.4, "result_text": "W 31-24", "opponent_name": "Ole Miss", "opponent_slug": "ole-miss", "is_win": True, "is_top_result": False},
                {"total_delta": 0.8, "result_text": "W 20-17", "opponent_name": "LSU", "opponent_slug": "lsu", "is_win": True, "is_top_result": False},
                {"total_delta": -1.2, "result_text": "L 14-21", "opponent_name": "Texas", "opponent_slug": "texas", "is_win": False, "is_top_result": False}],
       "summary_stats": {"delta_spread": 4.3}}

RPX = {"query_id": "returning_production_xray_v1", "source_tables": ["returning_production", "teams"],
       "sample_n": 2, "confidence": "medium", "limitations": [],
       "rows": [{"label": "Offense", "value": 0.72}, {"label": "Defense", "value": 0.55}],
       "summary_stats": {"season_year": 2025, "league_avg_offense": 0.60, "league_avg_defense": 0.58,
                         "returning_qb": 0.90, "returning_ol": 0.65}}

HRB = {"query_id": "heisman_race_braid_v1", "source_tables": ["heisman_rankings_weekly", "player_game_stats"],
       "sample_n": 8, "confidence": "high", "limitations": [],
       "rows": [{"player_name": "Arch Manning", "team_slug": "texas", "current_rank": 1,
                 "history": [{"week": 1, "rank": 4, "finalist_probability": 0.20}, {"week": 5, "rank": 2, "finalist_probability": 0.40}, {"week": 9, "rank": 1, "finalist_probability": 0.62}]},
                {"player_name": "Dylan Raiola", "team_slug": "nebraska", "current_rank": 2,
                 "history": [{"week": 1, "rank": 1, "finalist_probability": 0.50}, {"week": 5, "rank": 3, "finalist_probability": 0.30}, {"week": 9, "rank": 2, "finalist_probability": 0.25}]},
                {"player_name": "Carson Beck", "team_slug": "miami", "current_rank": 3,
                 "history": [{"week": 1, "rank": 2, "finalist_probability": 0.30}, {"week": 5, "rank": 4, "finalist_probability": 0.20}, {"week": 9, "rank": 3, "finalist_probability": 0.18}]}],
       "summary_stats": {"snapshot_week": 9, "season_year": 2025}}

RRG = {"query_id": "roster_replacement_grid_v1", "source_tables": ["transfer_entries", "teams"],
       "sample_n": 8, "confidence": "medium", "limitations": [],
       "rows": [{"position": "QB", "incoming_n": 1, "outgoing_n": 0, "net_n": 1},
                {"position": "WR", "incoming_n": 3, "outgoing_n": 2, "net_n": 1},
                {"position": "OL", "incoming_n": 1, "outgoing_n": 4, "net_n": -3},
                {"position": "DB", "incoming_n": 2, "outgoing_n": 2, "net_n": 0}],
       "summary_stats": {"season_year": 2025, "total_incoming": 7, "total_outgoing": 8, "net_movement": -1,
                         "biggest_upgrade_pos": "WR", "biggest_hole_pos": "OL"}}

DPC = {"query_id": "draft_pipeline_conveyor_v1", "source_tables": ["player_nfl_draft", "teams"],
       "sample_n": 5, "confidence": "high", "limitations": [],
       "rows": [{"position": "WR", "capital": 8.0, "picks": 2, "first_rounder": True, "incoming_replacements": 1},
                {"position": "OL", "capital": 5.0, "picks": 2, "first_rounder": False, "incoming_replacements": 0},
                {"position": "DB", "capital": 3.0, "picks": 1, "first_rounder": False, "incoming_replacements": 2}],
       "summary_stats": {"draft_year": 2025, "total_picks": 5, "total_capital": 16, "top_position": "WR",
                         "top_position_picks": 2, "exposed_position": "OL", "top_position_first_rounder": True}}

ALL_RENDER = [(render_fan_mood_braid, FMB), (render_home_away_mind, HAM), (render_perception_vs_tape, PVT),
              (render_cfp_bubble_wall, CFP), (render_talent_yield_curve, TYC),
              (render_delta_dna, DDNA), (render_continuity_stress_test, CST),
              (render_statement_win_ladder, SWL), (render_returning_production_xray, RPX),
              (render_heisman_race_braid, HRB), (render_roster_replacement_grid, RRG),
              (render_draft_pipeline_conveyor, DPC)]


@pytest.mark.parametrize("render,qr", ALL_RENDER)
def test_renderer_uses_shared_grammar(render, qr):
    out = render(qr)
    svg = out["svg_html"]
    # Shared grammar chrome: cream paper bg, accessible role, human credit line.
    assert "#f6f1e6" in svg            # grammar-owned paper background
    assert 'role="img"' in svg         # grammar-owned accessibility
    assert "Source: CFB Index" in svg  # consistent human credit line
    # Upshot restraint: the gimmicks are gone.
    assert "ed-grain" not in svg and "VERIFIED LIVE" not in svg
    assert out["headline_finding"] and out["alt_text"]
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")


@pytest.mark.parametrize("render,qr", ALL_RENDER)
def test_renderer_is_deterministic(render, qr):
    assert render(qr)["svg_html"] == render(qr)["svg_html"]


@pytest.mark.parametrize("render,qr", ALL_RENDER)
def test_world_class_definition_of_done(render, qr):
    """THE QUALITY GATE (doc 77 §7). Every grammar-based visual must pass all of
    these — the codified, enforced 'world-class' bar. A new visual joins the gate
    by adding a synthetic fixture to ALL_RENDER above. This is the systematic
    mechanism that keeps the whole library at NYT-Upshot quality by construction."""
    out = render(qr)
    svg = out["svg_html"]
    h = out["headline_finding"]
    # 1. finding-AS-headline: a sentence stating the conclusion, not a topic label
    assert 24 <= len(h) <= 120 and h.strip()[-1] in ".!?", f"weak headline: {h!r}"
    # 2. shared grammar chrome (one publication look) + accessibility
    assert "#f6f1e6" in svg and 'role="img"' in svg and out["alt_text"]
    # 3. human credit line — never raw table/column/metric jargon
    assert "Source: CFB Index" in svg
    for jargon in ("backometer_weekly", "power_ratings_weekly", "wepa_passing",
                   "team_week_conversation_features", "_pctile"):
        assert jargon not in svg, f"jargon leaked into the chart: {jargon}"
    # 4. Upshot restraint — the gimmicks must never come back
    assert "ed-grain" not in svg and "VERIFIED LIVE" not in svg
    # 5. typography: design font FIRST, Georgia only as fallback (the ordering bug)
    assert "'Source Serif Pro'" in svg
    assert "Georgia,'Source Serif" not in svg, "font-order regression: Georgia must not precede the design serif"
    # 6. mobile: one responsive SVG with the media-query type scale (doc 77 §5)
    assert "@media (max-width:640px)" in svg and 'class="ed-headline"' in svg
    # 6b. motion is OPTIONAL (a per-type research call — owner ruling 2026-06-14):
    #     not every viz needs it. But IF present it must be scroll-driven AND
    #     reduced-motion-safe (implemented perfectly or not at all).
    if 'class="ed-anim"' in svg:
        assert "@keyframes ed-rise" in svg and "prefers-reduced-motion" in svg
    # 6c. interactivity is OPTIONAL too. But IF a point is interactive (data-tip),
    #     it MUST carry a native <title> fallback (zero-JS / accessible).
    if 'data-tip="' in svg:
        assert "<title>" in svg
    # 7. deterministic (same data -> identical pixels)
    assert render(qr)["svg_html"] == svg


@pytest.mark.parametrize("vid,render,qr", [
    (VisualId.FAN_MOOD_BRAID, render_fan_mood_braid, FMB),
    (VisualId.HOME_AWAY_MIND, render_home_away_mind, HAM),
    (VisualId.PERCEPTION_VS_TAPE, render_perception_vs_tape, PVT),
])
def test_render_scores_above_floor(vid, render, qr):
    out = render(qr)
    spec = VisualSpec(visual_id=vid, chart_family=ChartFamily.RANGE_PLOT,
                      headline_finding=out["headline_finding"], data_query_id=qr["query_id"],
                      entity_scope=EntityScope(slug="x", season_year=2026),
                      annotations=out["annotations"], alt_text=out["alt_text"])
    rec = VisualReceipt(query_id=qr["query_id"], source_tables=qr["source_tables"],
                        sample_n=qr["sample_n"], confidence=ConfidenceBand(qr["confidence"]))
    assert score_visual(spec, rec).total >= VISUAL_SUPPRESS_THRESHOLD


def test_perception_quadrant_headlines():
    # The finding-headline keys off the quadrant.
    over = dict(PVT); over_ss = dict(PVT["summary_stats"]); over_ss["quadrant"] = "OVERHYPED"; over["summary_stats"] = over_ss
    assert "doesn't back" in render_perception_vs_tape(over)["headline_finding"]


# --------------------------------------------------------------------------- #
# Entity-aware registry — player visuals must NOT be in the team pipeline
# --------------------------------------------------------------------------- #

def test_player_visual_not_in_team_registry():
    team = {v.value for v in registry.list_registered_visuals()}
    player = {v.value for v in registry.list_registered_player_visuals()}
    assert "perception_vs_tape" in player
    assert "perception_vs_tape" not in team          # would misfire on team slugs
    assert "fan_mood_braid" in team
    # getters span both registries
    assert registry.get_query_function(VisualId.PERCEPTION_VS_TAPE) is not None
    assert registry.get_chart_family(VisualId.PERCEPTION_VS_TAPE) == ChartFamily.ANNOTATED_SCATTER


# --------------------------------------------------------------------------- #
# DB-backed honesty gates + entity-aware generation (skip without DB)
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def db():
    p = Path(__file__).resolve().parents[1] / "cfb_rankings.db"
    if not p.exists():
        pytest.skip("cfb_rankings.db not present")
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_belief_suppresses_in_offseason(db):
    from cfb_rankings.chronicle.visuals.queries import query_fan_mood_braid, query_home_away_mind
    # 2025 is offseason in this DB → the belief family must suppress (sample_n == 0).
    assert query_fan_mood_braid(db, slug="ohio-state", season_year=2025)["sample_n"] == 0
    assert query_home_away_mind(db, slug="ohio-state", season_year=2025)["sample_n"] == 0


def test_perception_generates_for_real_player(db, tmp_path):
    from cfb_rankings.chronicle.visuals.queries import query_perception_vs_tape
    row = db.execute("SELECT player_id FROM players WHERE LOWER(full_name)='carson beck'").fetchone()
    if not row:
        pytest.skip("reference player not in DB")
    qr = query_perception_vs_tape(db, player_id=row[0], season_year=2025)
    if qr["sample_n"] == 0:
        pytest.skip("no live player cohort in this DB")
    ss = qr["summary_stats"]
    assert ss["quadrant"] in {"PROVEN", "UNDERRATED", "OVERHYPED", "OFF THE RADAR"}
    assert 0 <= ss["hype_pctile"] <= 100 and 0 <= ss["prod_pctile"] <= 100

    # entity-aware generation caches under entity_kind='player' (use a DB copy).
    # Use sqlite's backup API for a CONSISTENT copy — a raw file copy of a live
    # db can land mid-write and read back "database disk image is malformed".
    src = Path(__file__).resolve().parents[1] / "cfb_rankings.db"
    copy = tmp_path / "vis.db"
    _src_ro = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    conn = sqlite3.connect(str(copy))
    _src_ro.backup(conn)
    _src_ro.close()
    conn.row_factory = sqlite3.Row
    from cfb_rankings.chronicle.visuals import generate_visuals_for_player
    slug = f"carson-beck-{row[0]}"
    res = generate_visuals_for_player(conn, slug=slug, season_year=2025)
    assert any(not r.suppressed for r in res)
    ek = conn.execute("SELECT entity_kind FROM chronicle_visual_cache WHERE slug=?", (slug,)).fetchone()
    conn.close()
    assert ek and ek[0] == "player"
