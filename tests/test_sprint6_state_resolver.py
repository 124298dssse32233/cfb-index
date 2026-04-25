"""Sprint 6 — outcome category + game-recap state-transition tests.

Locks in the classification matrix from the spec so future edits to
state_resolver don't silently regress the 5-mode taxonomy.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from cfb_rankings.team_pages.profile_loader import Profile
from cfb_rankings.team_pages.state_resolver import (
    _classify_outcome,
    _resolve_game_recap_anchor,
    _post_game_24_72h_register,
    _hours_since,
    resolve_state,
)


# --------------------------------------------------------------------------
# _classify_outcome — the core spec matrix
# --------------------------------------------------------------------------

class TestClassifyOutcome:
    def test_win_clear_with_favored_spread(self):
        assert _classify_outcome(margin=14, pre_game_spread=-7.5) == "win-clear"

    def test_win_clear_close_win_no_spread(self):
        # Without spread info, close wins default to win-clear
        assert _classify_outcome(margin=7, pre_game_spread=None) == "win-clear"

    def test_win_upset_dog_by_10(self):
        assert _classify_outcome(margin=10, pre_game_spread=10.5) == "win-upset"

    def test_win_upset_dog_by_exactly_7(self):
        assert _classify_outcome(margin=3, pre_game_spread=7.0) == "win-upset"

    def test_win_upset_threshold_below_7_is_clear(self):
        # Dog by less than 7 doesn't qualify as upset
        assert _classify_outcome(margin=10, pre_game_spread=6.9) == "win-clear"

    def test_loss_close_dog_by_10_loss_by_3(self):
        assert _classify_outcome(margin=-3, pre_game_spread=10.0) == "loss-close"

    def test_loss_blowout_dog_by_10_loss_by_21(self):
        assert _classify_outcome(margin=-21, pre_game_spread=10.0) == "loss-blowout"

    def test_loss_upset_favored_team_loses(self):
        # Team favored by 7.5, loses by 7 → loss-upset (was favored)
        assert _classify_outcome(margin=-7, pre_game_spread=-7.5) == "loss-upset"

    def test_loss_upset_pickem_loses(self):
        # Within 3-point pick'em window, any loss is loss-upset
        assert _classify_outcome(margin=-7, pre_game_spread=2.0) == "loss-upset"

    def test_loss_upset_blowout_when_favored(self):
        # Spec: "loss-upset" when team was favored, regardless of margin
        assert _classify_outcome(margin=-14, pre_game_spread=-7.0) == "loss-upset"

    def test_loss_blowout_no_spread(self):
        # Without spread, big margin → blowout
        assert _classify_outcome(margin=-28, pre_game_spread=None) == "loss-blowout"

    def test_loss_close_no_spread(self):
        # Without spread, small margin → close
        assert _classify_outcome(margin=-3, pre_game_spread=None) == "loss-close"

    def test_loss_close_mid_margin_no_spread(self):
        # 8-13 point loss with no spread defaults to close
        assert _classify_outcome(margin=-10, pre_game_spread=None) == "loss-close"


# --------------------------------------------------------------------------
# _resolve_game_recap_anchor — outcome → (anchor, hero, tone, accent)
# --------------------------------------------------------------------------

class TestGameRecapAnchor:
    @pytest.mark.parametrize("cat,expected", [
        ("win-clear",   ("game-recap-win-clear",   "game-recap", "confident",  "green")),
        ("win-upset",   ("game-recap-win-upset",   "game-recap", "vindicated", "amber")),
        ("loss-close",  ("game-recap-loss-close",  "game-recap", "reckoning",  "coral")),
        ("loss-blowout",("game-recap-loss-blowout","game-recap", "wound",      "red")),
        ("loss-upset",  ("game-recap-loss-upset",  "game-recap", "crisis",     "red")),
    ])
    def test_each_outcome_maps_correctly(self, cat, expected):
        assert _resolve_game_recap_anchor(cat) == expected

    def test_unknown_outcome_falls_back_to_loss_close(self):
        # Defensive: unknown categories don't crash, default to safe register
        result = _resolve_game_recap_anchor("not-a-real-category")
        assert result[1] == "game-recap"
        # Tone falls back to reckoning
        assert result[2] == "reckoning"


# --------------------------------------------------------------------------
# _post_game_24_72h_register — softer Mon/Tue register
# --------------------------------------------------------------------------

class TestPostGame24To72hRegister:
    @pytest.mark.parametrize("cat,expected_tone,expected_accent", [
        ("win-clear",    "basking",     "green"),
        ("win-upset",    "vindicated",  "amber"),
        ("loss-close",   "reckoning",   "coral"),
        ("loss-blowout", "wound",       "red"),
        ("loss-upset",   "crisis",      "red"),
    ])
    def test_each_outcome_register(self, cat, expected_tone, expected_accent):
        tone, accent = _post_game_24_72h_register(cat)
        assert tone == expected_tone
        assert accent == expected_accent


# --------------------------------------------------------------------------
# _hours_since — freshness math
# --------------------------------------------------------------------------

class TestHoursSince:
    def test_returns_positive_for_past_iso(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        h = _hours_since(past, today=date.today())
        assert h is not None
        assert 2.9 < h < 3.1

    def test_handles_z_suffix(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        h = _hours_since(past, today=date.today())
        assert h is not None
        assert 1.9 < h < 2.1

    def test_naive_iso_assumed_utc(self):
        # SQLite stores datetimes without explicit tz — interpret as UTC
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
        h = _hours_since(past, today=date.today())
        assert h is not None
        assert 0.9 < h < 1.1

    def test_returns_none_on_garbage(self):
        assert _hours_since("not-a-date", today=date.today()) is None

    def test_returns_none_on_empty(self):
        assert _hours_since("", today=date.today()) is None
        assert _hours_since(None, today=date.today()) is None


# --------------------------------------------------------------------------
# resolve_state — the 24h cliff: game_recap_active flips to False at hour 24
# --------------------------------------------------------------------------

def _stub_profile() -> Profile:
    """Minimal profile object for state-resolver tests."""
    return Profile(
        slug="test",
        team_id=1,
        program_tier=1,
        voice_register="dynastic",
        tonal_template="dynastic-process",
        identity_phrase="",
        mantra="",
        frontmatter={},
        sections={},
        source_path=None,  # type: ignore
    )


def _stub_snapshot(season_year: int = 2025):
    """Minimal TeamSnapshot stub with no last_game so non-live branches stay quiet."""
    snap = MagicMock()
    snap.season_year = season_year
    snap.wins = 0
    snap.losses = 0
    snap.ties = 0
    snap.ap_rank = None
    snap.coaches_rank = None
    snap.cfp_rank = None
    snap.last_game = None
    snap.next_game = None
    snap.season_complete = False
    snap.recent_games = []
    return snap


class TestResolveStateLiveTransitions:
    def test_2h_post_loss_is_game_recap_active(self):
        profile = _stub_profile()
        snap = _stub_snapshot()
        live_meta = {
            "status": "final",
            "home_team_slug": "opponent",
            "away_team_slug": "test",
            "home_score": 31,
            "away_score": 24,
            "pre_game_spread_home": -10.0,  # opp favored, test was dog
            "final_at_utc": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        }
        state = resolve_state(profile, snap, live_game_meta=live_meta)
        assert state.game_recap_active is True
        assert state.outcome_category == "loss-close"
        assert state.anchor_variant == "game-recap-loss-close"

    def test_27h_post_loss_falls_to_post_game_monday(self):
        """At hour 25-72, game-recap deactivates and post-game-monday-tuesday takes over."""
        profile = _stub_profile()
        snap = _stub_snapshot()
        live_meta = {
            "status": "final",
            "home_team_slug": "opponent",
            "away_team_slug": "test",
            "home_score": 31,
            "away_score": 24,
            "pre_game_spread_home": -10.0,
            "final_at_utc": (datetime.now(timezone.utc) - timedelta(hours=27)).isoformat(),
        }
        state = resolve_state(profile, snap, live_game_meta=live_meta)
        assert state.game_recap_active is False
        assert state.anchor_variant == "post-game-monday-tuesday"
        # Outcome category persists for downstream Chronicle pinning
        assert state.outcome_category == "loss-close"

    def test_75h_post_loss_falls_off_post_game_window(self):
        """Beyond 72h, fetch_recent_final_for_team would return None — but if
        a live_meta still leaks through, the soft window has ended."""
        profile = _stub_profile()
        snap = _stub_snapshot()
        live_meta = {
            "status": "final",
            "home_team_slug": "opponent",
            "away_team_slug": "test",
            "home_score": 31,
            "away_score": 24,
            "pre_game_spread_home": -10.0,
            "final_at_utc": (datetime.now(timezone.utc) - timedelta(hours=75)).isoformat(),
        }
        state = resolve_state(profile, snap, live_game_meta=live_meta)
        assert state.game_recap_active is False
        # Anchor falls through to season-phase resolution
        assert state.anchor_variant != "game-recap-loss-close"
        assert state.anchor_variant != "post-game-monday-tuesday"

    def test_no_live_meta_no_game_recap(self):
        profile = _stub_profile()
        snap = _stub_snapshot()
        state = resolve_state(profile, snap, live_game_meta=None)
        assert state.game_recap_active is False
        assert state.outcome_category is None

    def test_team_not_in_meta_no_game_recap(self):
        profile = _stub_profile()  # slug='test'
        snap = _stub_snapshot()
        live_meta = {
            "status": "final",
            "home_team_slug": "team-a",
            "away_team_slug": "team-b",
            "home_score": 24,
            "away_score": 21,
            "final_at_utc": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        }
        state = resolve_state(profile, snap, live_game_meta=live_meta)
        # 'test' isn't either team — should not flip into game-recap
        assert state.game_recap_active is False
        assert state.outcome_category is None

    def test_in_progress_status_is_not_game_recap(self):
        """Game-recap fires only on status='final', not in_progress."""
        profile = _stub_profile()
        snap = _stub_snapshot()
        live_meta = {
            "status": "in_progress",
            "home_team_slug": "test",
            "away_team_slug": "opponent",
            "home_score": 14,
            "away_score": 7,
            "final_at_utc": None,
        }
        state = resolve_state(profile, snap, live_game_meta=live_meta)
        assert state.game_recap_active is False
        assert state.outcome_category is None


class TestSpreadSignFlippingForAwayTeam:
    """When the rendering team is away, spread_for_team is the opposite sign
    of spread_home (which is always stored from the home team's perspective)."""

    def test_away_team_dog_sees_positive_spread(self):
        profile = _stub_profile()
        snap = _stub_snapshot()
        # Home favored by 10 (spread_home = -10) → away test team is +10 dog.
        live_meta = {
            "status": "final",
            "home_team_slug": "opponent",
            "away_team_slug": "test",
            "home_score": 31,
            "away_score": 24,
            "pre_game_spread_home": -10.0,
            "final_at_utc": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        }
        state = resolve_state(profile, snap, live_game_meta=live_meta)
        assert state.pre_game_spread == 10.0  # team-perspective: dog by 10
        assert state.outcome_category == "loss-close"

    def test_home_team_favored_sees_negative_spread(self):
        profile = _stub_profile()
        snap = _stub_snapshot()
        live_meta = {
            "status": "final",
            "home_team_slug": "test",
            "away_team_slug": "opponent",
            "home_score": 24,
            "away_score": 31,
            "pre_game_spread_home": -7.0,  # test was favored at home
            "final_at_utc": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        }
        state = resolve_state(profile, snap, live_game_meta=live_meta)
        assert state.pre_game_spread == -7.0  # team-perspective: favored by 7
        # Lost as a 7-point favorite → loss-upset
        assert state.outcome_category == "loss-upset"


# --------------------------------------------------------------------------
# Smoke: as_dict carries Sprint 6 fields for state_signature persistence
# --------------------------------------------------------------------------

def test_page_state_dict_carries_sprint6_fields():
    profile = _stub_profile()
    snap = _stub_snapshot()
    live_meta = {
        "status": "final",
        "home_team_slug": "test",
        "away_team_slug": "opponent",
        "home_score": 24,
        "away_score": 21,
        "pre_game_spread_home": -3.0,
        "final_at_utc": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    }
    state = resolve_state(profile, snap, live_game_meta=live_meta)
    d = state.as_dict()
    assert "outcome_category" in d
    assert "pre_game_spread" in d
    assert "hours_since_final" in d
    assert "game_recap_active" in d
    assert "game_id" in d
    assert d["outcome_category"] == "win-clear"
    assert d["game_recap_active"] is True
