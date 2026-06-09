"""Milestone C tests for roster-reload summary and renderer."""

from __future__ import annotations

from types import SimpleNamespace

from cfb_rankings.team_pages.roster_reload import (
    _quality_verdict,
    _rating,
    render_roster_reload,
)
from cfb_rankings.team_preview.roster_reload import build_roster_reload_summary


def test_roster_reload_summary_keeps_recruiting_signal() -> None:
    evidence = SimpleNamespace(returning_total=0.68, drafted_count=4,
                               recruiting_rank=8, recruiting_score=286.5)
    position_rows = [
        {"position": "OL", "incoming_count": 3, "outgoing_count": 1,
         "incoming_total_points": 18.0, "outgoing_total_points": 5.0},
        {"position": "DL", "incoming_count": 1, "outgoing_count": 4,
         "incoming_total_points": 4.0, "outgoing_total_points": 19.0},
    ]

    row = build_roster_reload_summary(
        db=None,
        slug="alabama",
        team_id=1,
        season_year=2026,
        as_of_date="2026-05-25",
        position_rows=position_rows,
        evidence=evidence,
    )

    assert row["returning_profile_label"] == "High continuity"
    assert row["recruiting_reload_label"] == "Top-10 recruiting reload (#8)"
    assert row["primary_repair_position"] == "OL"
    assert row["primary_pressure_position"] == "DL"
    assert row["portal_addition_score"] == 22.0
    assert row["portal_loss_score"] == 24.0
    assert row["freshman_injection_score"] is not None
    assert row["reload_score"] is not None


def test_roster_reload_renderer_splits_roster_concepts() -> None:
    profile = SimpleNamespace(program_name="Alabama")
    snapshot = SimpleNamespace(team_id=1, season_year=2026)
    reload_row = {
        "team_id": 1,
        "season_year": 2026,
        "as_of_date": "2026-05-25",
        "continuity_score": 0.68,
        "returning_profile_label": "High continuity",
        "primary_repair_position": "OL",
        "primary_pressure_position": "DL",
        "draft_loss_label": "NFL Draft departures (4)",
        "recruiting_reload_label": "Top-10 recruiting reload (#8)",
        "freshman_injection_score": 0.946,
        "summary_json": {
            "transfer_in_total": 12,
            "transfer_out_total": 9,
            "drafted_count": 4,
            "recruiting_rank": 8,
        },
    }
    positions = [
        {"position": "OL", "incoming_count": 3, "outgoing_count": 1,
         "incoming_top_player_name": "Portal Tackle", "outgoing_top_player_name": None,
         "starter_risk_flag": 0, "need_filled_flag": 1},
        {"position": "DL", "incoming_count": 1, "outgoing_count": 4,
         "incoming_top_player_name": None, "outgoing_top_player_name": "Edge Starter",
         "starter_risk_flag": 1, "need_filled_flag": 0},
    ]

    html = render_roster_reload(profile, snapshot, reload_row, positions)

    assert 'data-module="roster-reload"' in html
    assert "Returning Production" in html
    assert "Portal Additions" in html
    assert "Portal Losses" in html
    assert "Draft Loss" in html
    assert "Recruiting Reload" in html
    assert "12" in html
    assert "9" in html
    assert "#8" in html
    assert "OL" in html and "DL" in html


def test_quality_verdict_prefers_upstream_flags() -> None:
    # Upstream flags win even when net_points would say otherwise.
    assert _quality_verdict({"starter_risk_flag": 1, "net_points": 5.0}) == ("Starter Risk", "down")
    assert _quality_verdict({"need_filled_flag": 1, "net_points": -5.0}) == ("Need Filled", "up")


def test_quality_verdict_falls_back_to_net_points() -> None:
    assert _quality_verdict({"net_points": 1.2}) == ("Upgrade", "up")
    assert _quality_verdict({"net_points": -1.2}) == ("Downgrade", "down")
    assert _quality_verdict({"net_points": 0.1, "incoming_count": 1}) == ("Even", "even")
    # No activity at all -> no verdict.
    assert _quality_verdict({}) == ("", "")


def test_rating_stamp_formats_and_guards() -> None:
    assert "0.96" in _rating(0.96)
    assert "roster-reload__rating" in _rating(0.96)
    assert _rating(None) == ""
    assert _rating(0) == ""
    assert _rating("bad") == ""


def test_renderer_surfaces_quality_signal() -> None:
    profile = SimpleNamespace(program_name="Alabama")
    snapshot = SimpleNamespace(team_id=1, season_year=2026)
    reload_row = {
        "team_id": 1, "season_year": 2026, "as_of_date": "2026-05-25",
        "continuity_score": 0.43, "returning_profile_label": "Low continuity",
        "summary_json": {"transfer_in_total": 17, "transfer_out_total": 24},
    }
    positions = [
        {"position": "WR", "incoming_count": 1, "outgoing_count": 6,
         "incoming_top_player_name": "Noah Rogers", "incoming_top_player_rating": 0.90,
         "outgoing_top_player_name": "Isaiah Horton", "outgoing_top_player_rating": 0.96,
         "net_points": -4.39, "starter_risk_flag": 1, "need_filled_flag": 0},
    ]

    html = render_roster_reload(profile, snapshot, reload_row, positions)

    assert "Starter Risk" in html
    assert "roster-reload__flag--down" in html
    assert "0.96" in html and "0.90" in html
    assert "roster-reload__rating" in html
