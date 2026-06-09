"""Accolade streams + standing aggregator tests.

Live-DB smoke tests against cfb_rankings.db (skipped if not present).
Pure unit tests cover the position-award catalog, renderer empty-state,
and rung-narrative table.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def db():
    db_path = Path(__file__).resolve().parents[1] / "cfb_rankings.db"
    if not db_path.exists():
        pytest.skip("cfb_rankings.db not present")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_position_catalog_complete():
    from cfb_rankings.player_pages.accolade_streams import (
        POSITION_AWARDS, awards_for_position,
    )
    for pos in ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "K", "P"):
        assert pos in POSITION_AWARDS
        catalog = POSITION_AWARDS[pos]
        assert catalog
        # Every position bucket ends with All-America
        assert catalog[-1][0] == "all_america", f"{pos} missing All-America terminator"
    # Position normalization
    assert awards_for_position("QB")[-1][0] == "all_america"
    assert awards_for_position("OG")[-1][0] == "all_america"  # OG -> OL bucket
    assert awards_for_position("CB")[-1][0] == "all_america"  # CB -> DB bucket
    assert awards_for_position("BAD_POS")[-1][0] == "all_america"  # default


def test_rung_table_matches_canonical_spec():
    """RUNG_TABLE must match PLAYER_PAGE_WORLD_CLASS_BRIEF.md §7.2 exactly.

    The renderer (_STANDING_RUNGS in reporting.py) indexes its label table by
    the rung number this aggregator emits, so the two MUST agree or every
    player mislabels (the 2026-05-26 'All-Americans shown as National watch'
    regression). This test pins the canonical semantics.
    """
    from cfb_rankings.player_pages.standing_aggregator import RUNG_TABLE
    label_by_rung = {n: lbl.lower() for (n, lbl, _, _) in RUNG_TABLE}
    # Key rungs that the cascade depends on (substring checks)
    assert "walk-on" in label_by_rung[0]
    assert "scout" in label_by_rung[1] or "redshirt" in label_by_rung[1]
    assert "deep reserve" in label_by_rung[2]
    assert "impact starter" in label_by_rung[7]
    assert "watch" in label_by_rung[8]
    assert "all-conference" in label_by_rung[10] and "1st" in label_by_rung[10]
    assert "fringe" in label_by_rung[11] or "national watch" in label_by_rung[11]
    assert label_by_rung[12] == "all-american"
    assert "consensus" in label_by_rung[13]
    assert "unanimous" in label_by_rung[14]
    assert "finalist" in label_by_rung[15]
    assert "winner" in label_by_rung[16]


def test_aa_classification_lands_above_national_watch(db):
    """A 1st-team NCAA-selector All-American must classify >= R12, never R11.

    Regression guard for the bug where 1st-team AAs rendered as 'National
    watch' (R11) because the aggregator used a non-canonical ladder.
    """
    cur = db.execute(
        """SELECT player_id FROM player_honors
           WHERE season_year=2024 AND honor_scope='all_america'
             AND selector IN ('AP','AFCA','FWAA','WCFF','SN')
             AND (placement IN (1,'1st team','first') OR lower(coalesce(honor_team,''))='first')
           LIMIT 1"""
    )
    row = cur.fetchone()
    if not row:
        pytest.skip("no NCAA-selector 1st-team AA in DB")
    from cfb_rankings.player_pages.standing_aggregator import classify_rung
    rung = classify_rung(db, row["player_id"], 2024)
    assert rung is not None and rung >= 12, (
        f"1st-team All-American classified to R{rung} (should be >= R12 All-American)"
    )


def test_rung_narrative_for_every_rung():
    from cfb_rankings.player_pages.standing_aggregator import (
        RUNG_TABLE, narratives_for_rung,
    )
    for rung_id, *_ in RUNG_TABLE:
        n = narratives_for_rung(rung_id)
        assert n["why_here"], f"missing why_here for rung {rung_id}"


def test_empty_state_renderer():
    from cfb_rankings.player_pages.accolade_streams import render_accolade_tabs_html
    assert "populate" in render_accolade_tabs_html([])
    # All-empty streams still emit tabs
    streams = [
        {"award_key": "heisman", "award_name": "Heisman", "data_state": "empty",
         "probability_pct": None, "current_rank": None, "trajectory": [],
         "what_needs_to_happen": "awaiting", "selector_breakdown": None},
    ]
    html = render_accolade_tabs_html(streams)
    assert "acc-tab" in html
    assert "Awaiting tracker" in html


def test_heisman_stream_live_winner(db):
    """Dillon Gabriel (pid=11737) was #1 in heisman_rankings_weekly week 16, 2024."""
    cur = db.execute(
        "SELECT 1 FROM heisman_rankings_weekly WHERE player_id=11737 AND season_year=2024 LIMIT 1"
    )
    if not cur.fetchone():
        pytest.skip("Dillon Gabriel heisman data missing")
    from cfb_rankings.player_pages.accolade_streams import build_heisman_stream
    s = build_heisman_stream(db, 11737, 2024)
    assert s["data_state"] == "ready"
    assert s["current_rank"] == 1
    assert s["probability_pct"] is not None
    assert len(s["trajectory"]) >= 3


def test_standing_payload_classifies_heisman_winner(db):
    cur = db.execute(
        "SELECT 1 FROM heisman_rankings_weekly WHERE player_id=11737 AND season_year=2024 LIMIT 1"
    )
    if not cur.fetchone():
        pytest.skip("heisman seed data missing")
    from cfb_rankings.player_pages.standing_aggregator import build_standing_payload
    payload = build_standing_payload(db, 11737, 2024, "QB")
    assert payload is not None
    # Gabriel was #1 in the model in week 16 — but the actual trophy went to
    # someone else. Without a confirmed-winner row in player_honors, the
    # classifier caps at R15 (finalist tier). This is intentional after a
    # 2026-05-24 fix that distinguishes model nowcast from official ballot.
    assert payload["current_rung_id"] in (15, 16), (
        f"expected finalist or winner rung, got {payload['current_rung_id']}"
    )
    # Canonical §7.2 ladder: R15/R16 use generic "Player-of-the-Year" language
    # (the ladder is position-agnostic; Heisman is just the QB-visible instance).
    why = payload["narratives"]["why_here"].lower()
    assert "player-of-the-year" in why or "heisman" in why
    # Position-aware: QB gets 5 awards
    assert len(payload["accolade_streams"]) == 5
    award_keys = [s["award_key"] for s in payload["accolade_streams"]]
    assert award_keys == [
        "heisman", "davey_obrien", "manning", "unitas", "all_america",
    ]


def test_position_resolves_from_honors_when_hint_blank(db):
    """Corrupted/blank players.position must fall back to clean AA-honors position."""
    cur = db.execute(
        "SELECT player_id FROM player_honors WHERE honor_scope='all_america' "
        "AND position='QB' LIMIT 1"
    )
    row = cur.fetchone()
    if not row:
        pytest.skip("no QB all-america honors in DB")
    from cfb_rankings.player_pages.accolade_streams import (
        resolve_player_position, build_accolade_streams_for_position,
    )
    pid = row["player_id"]
    # Blank hint should resolve to QB from honors, yielding the 5-tab QB set
    resolved = resolve_player_position(db, pid, 2024, "")
    assert resolved == "QB"
    streams = build_accolade_streams_for_position(db, pid, 2024, "")
    keys = [s["award_key"] for s in streams]
    assert "davey_obrien" in keys, "QB-specific award missing after position resolution"
    assert keys[-1] == "all_america"


def test_v5_standing_card_renders_populated_payload(db):
    """End-to-end: aggregator -> v5 renderer produces real tab body."""
    cur = db.execute(
        "SELECT 1 FROM heisman_rankings_weekly WHERE player_id=11737 AND season_year=2024 LIMIT 1"
    )
    if not cur.fetchone():
        pytest.skip("heisman seed data missing")
    from cfb_rankings.player_pages.standing_aggregator import build_standing_payload
    from cfb_rankings.reporting import _render_v5_player_standing_card
    payload = build_standing_payload(db, 11737, 2024, "QB")
    html = _render_v5_player_standing_card(payload)
    assert "acc-tabs" in html, "accolade tabs missing from rendered card"
    assert "acc-tile-value" in html, "probability tile missing"
    assert "Heisman" in html
    # Real probability % appears (Gabriel's was 84.3 in week 16)
    assert "%" in html
