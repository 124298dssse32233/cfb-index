"""Renderer-level wiring tests for the team-preview truth layer.

Milestone B path/bowl correctness is not just module logic; the profiled
team-page renderer must pass the deterministic truth rows into those modules.
These tests pin that contract at the `_render_page` seam.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import cfb_rankings.team_pages.renderer as renderer_module
from cfb_rankings.team_pages.data import TeamSnapshot
from cfb_rankings.team_pages.profile_loader import Profile
from cfb_rankings.team_pages.state_resolver import PageState


class _NullDB:
    def query_all(self, sql: str, params: dict | None = None) -> list[dict]:
        return []

    def query_one(self, sql: str, params: dict | None = None) -> dict | None:
        return None


class _PostseasonDB(_NullDB):
    def query_all(self, sql: str, params: dict | None = None) -> list[dict]:
        flat = " ".join(sql.split()).lower()
        if "from games" in flat:
            return [
                {
                    "season_year": 2024,
                    "start_time_utc": "2024-12-31",
                    "home_team_id": 333,
                    "away_team_id": 9,
                    "home_points": 13,
                    "away_points": 19,
                    "notes": "CFP",
                },
                {
                    "season_year": 2023,
                    "start_time_utc": "2023-12-31",
                    "home_team_id": 333,
                    "away_team_id": 8,
                    "home_points": 27,
                    "away_points": 20,
                    "notes": "Bowl",
                },
            ]
        return []


def _make_profile() -> Profile:
    return Profile(
        slug="alabama",
        team_id=333,
        program_tier=1,
        voice_register="Process-Believer",
        tonal_template="basking",
        identity_phrase="Process",
        mantra="Roll Tide.",
        frontmatter={"team_id": 333, "program_tier": 1, "display_name": "Alabama"},
        sections={},
        source_path=Path("profiles/alabama.md"),
    )


def _make_snapshot() -> TeamSnapshot:
    return TeamSnapshot(
        team_id=333,
        slug="alabama",
        canonical_name="Alabama",
        school_name="University of Alabama",
        level_code="FBS",
        conference_id=1,
        conference_name="SEC",
        season_year=2026,
        wins=11,
        losses=2,
        ties=0,
        ap_rank=1,
        coaches_rank=1,
        cfp_rank=1,
    )


def _make_state() -> PageState:
    return PageState(
        today=date(2026, 5, 26),
        season_year=2026,
        season_phase="OFFSEASON",
        day_of_week_label="Tuesday",
        is_in_season=False,
        anchor_variant="dead-period-summer",
        hero_priority="heritage",
        copy_tone="basking",
        accent_key="amber",
        program_tier=1,
        voice_register="Process-Believer",
        tonal_template="basking",
    )


def test_render_page_wires_preview_truth_rows_into_modules(monkeypatch) -> None:
    season_path = {
        "floor": {"final_wins": 8, "final_losses": 5, "final_ties": 0},
        "base": {"final_wins": 10, "final_losses": 3, "final_ties": 0},
        "ceiling": {"final_wins": 16, "final_losses": 0, "final_ties": 0},
    }
    bowl_ledger_row = {
        "slug": "alabama",
        "wins": 47,
        "losses": 26,
        "ties": 3,
        "verification_status": "verified",
    }
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        renderer_module,
        "fetch_team_season_path",
        lambda db, team_id: season_path,
    )
    monkeypatch.setattr(
        renderer_module,
        "fetch_bowl_ledger_row",
        lambda db, slug: bowl_ledger_row,
    )

    def fake_render_ceiling_floor(profile, snapshot, arc_rows, season_path=None):
        seen["season_path"] = season_path
        return '<section data-test="ceiling-floor">path</section>'

    def fake_render_bowl_history(db, profile, snapshot, ledger_row=None):
        seen["ledger_row"] = ledger_row
        return '<section data-test="bowl-history">bowl</section>'

    monkeypatch.setattr(renderer_module, "render_ceiling_floor", fake_render_ceiling_floor)
    monkeypatch.setattr(renderer_module, "render_bowl_history", fake_render_bowl_history)

    html_out = renderer_module._render_page(
        profile=_make_profile(),
        snapshot=_make_snapshot(),
        state=_make_state(),
        mood={},
        divergence=None,
        sp_rating=None,
        state_of_team=None,
        chronicle_cards=[],
        savant_rows=[],
        savant_narrative=None,
        savant_echo=None,
        savant_season=None,
        rivalry_bundle=None,
        arc_rows=[],
        arc_thesis=None,
        arc_closing=None,
        db=_NullDB(),
    )

    assert seen["season_path"] is season_path
    assert seen["ledger_row"] is bowl_ledger_row
    assert 'data-test="ceiling-floor"' in html_out
    assert 'data-test="bowl-history"' in html_out


def test_render_page_surfaces_projection_and_verified_bowl_copy(monkeypatch) -> None:
    season_path = {
        "floor": {
            "final_wins": 8,
            "final_losses": 5,
            "final_ties": 0,
            "bowl_or_cfp_path": "bowl",
            "conference_title_result": "none",
        },
        "base": {
            "final_wins": 10,
            "final_losses": 3,
            "final_ties": 0,
            "bowl_or_cfp_path": "cfp_first_round",
            "conference_title_result": "none",
        },
        "ceiling": {
            "final_wins": 16,
            "final_losses": 0,
            "final_ties": 0,
            "bowl_or_cfp_path": "national_champion",
            "conference_title_result": "win",
        },
    }
    bowl_ledger_row = {
        "slug": "alabama",
        "wins": 47,
        "losses": 26,
        "ties": 3,
        "appearances": 76,
        "last_bowl_year": 2024,
        "last_bowl_name": "x",
        "last_bowl_result": "L",
        "source_name": "media-guide",
        "verification_status": "verified",
    }

    monkeypatch.setattr(
        renderer_module,
        "fetch_team_season_path",
        lambda db, team_id: season_path,
    )
    monkeypatch.setattr(
        renderer_module,
        "fetch_bowl_ledger_row",
        lambda db, slug: bowl_ledger_row,
    )

    for name in (
        "render_conference_standing",
        "render_home_field_advantage",
        "render_moment_of_year",
        "render_schedule_strength",
        "render_offseason_pulse",
        "render_recent_form",
        "render_statement_wins",
        "render_top_commits",
        "render_nfl_draft_pipeline",
        "render_coaching_era_strip",
        "render_recruiting_footprint",
        "render_top_players",
        "render_on_this_day",
    ):
        monkeypatch.setattr(renderer_module, name, lambda *args, **kwargs: "")

    html_out = renderer_module._render_page(
        profile=_make_profile(),
        snapshot=_make_snapshot(),
        state=_make_state(),
        mood={},
        divergence=None,
        sp_rating=None,
        state_of_team=None,
        chronicle_cards=[],
        savant_rows=[],
        savant_narrative=None,
        savant_echo=None,
        savant_season=None,
        rivalry_bundle=None,
        arc_rows=[],
        arc_thesis=None,
        arc_closing=None,
        db=_PostseasonDB(),
    )

    assert 'data-source="projection"' in html_out
    assert "16-0" in html_out
    assert "All-time bowls: 47-26-3" in html_out
    # The verified ledger must drive the verdict, not the recent-era fallback.
    # Match the recent-era VERDICT format ("Recent postseason (YYYY-YYYY): W-L")
    # specifically — the year-pills row carries a static aria-label
    # "Recent postseason appearances" that is honest and always present.
    assert "Recent postseason (" not in html_out
