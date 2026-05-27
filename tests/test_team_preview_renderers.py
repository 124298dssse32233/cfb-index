"""Milestone B render-correctness tests (Path and Bowl Correctness).

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §8 Milestone B.

Stop conditions pinned here:
  * ceiling_floor: a top team can show a ceiling record EXCEEDING 12 games
    (regular season + conference title + CFP) when a season-path projection is
    present; the heuristic fallback still caps at a 12-game frame.
  * bowl_history: CFBD-era postseason data is NEVER labelled "all-time"; only a
    verified/single_source ledger row earns an all-time label.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from cfb_rankings.team_pages.bowl_history import render_bowl_history
from cfb_rankings.team_pages.ceiling_floor import render_ceiling_floor


def _records(html: str) -> list[str]:
    return re.findall(r'scenario-record">([^<]+)<', html)


# --- ceiling_floor: B.2 ----------------------------------------------------

def test_ceiling_can_exceed_twelve_games_with_projection() -> None:
    profile = SimpleNamespace(program_name="Alabama")
    snapshot = SimpleNamespace(team_id=1, season_year=2026, wins=11, losses=2)
    season_path = {
        "floor":   {"final_wins": 8,  "final_losses": 5, "final_ties": 0,
                    "bowl_or_cfp_path": "bowl", "conference_title_result": "none"},
        "base":    {"final_wins": 10, "final_losses": 3, "final_ties": 0,
                    "bowl_or_cfp_path": "cfp_first_round", "conference_title_result": "none"},
        "ceiling": {"final_wins": 16, "final_losses": 0, "final_ties": 0,
                    "bowl_or_cfp_path": "national_champion", "conference_title_result": "win"},
    }
    html = render_ceiling_floor(profile, snapshot, [], season_path=season_path)
    assert 'data-source="projection"' in html
    assert "16-0" in _records(html)
    # The ceiling scenario totals 16 games — proof it broke the 12-game ceiling.
    ceiling = _records(html)[-1]
    w, l = (int(x) for x in ceiling.split("-")[:2])
    assert w + l > 12


def test_heuristic_fallback_caps_at_twelve_games() -> None:
    profile = SimpleNamespace(program_name="Akron")
    snapshot = SimpleNamespace(team_id=2, season_year=2026, wins=5, losses=7)
    arc = [{"season_year": 2024, "wins": 5, "losses": 7}]
    html = render_ceiling_floor(profile, snapshot, arc, season_path=None)
    assert 'data-source="heuristic"' in html
    for rec in _records(html):
        w, l = (int(x) for x in rec.split("-")[:2])
        assert w + l == 12


def test_partial_projection_set_falls_back() -> None:
    # Only two scenarios present -> must not render a misleading band.
    profile = SimpleNamespace(program_name="Auburn")
    snapshot = SimpleNamespace(team_id=3, season_year=2026, wins=8, losses=4)
    partial = {"floor": {"final_wins": 6, "final_losses": 6, "final_ties": 0,
                         "bowl_or_cfp_path": "none", "conference_title_result": "none"}}
    html = render_ceiling_floor(profile, snapshot, [{"season_year": 2024, "wins": 8, "losses": 4}],
                                season_path=partial)
    assert 'data-source="heuristic"' in html


# --- bowl_history: B.4 -----------------------------------------------------

class _StubDB:
    def __init__(self, ledger_rows: list[dict]) -> None:
        self._ledger = ledger_rows

    def query_all(self, sql: str, params: dict | None = None) -> list[dict]:
        flat = " ".join(sql.split())
        if "from games" in flat:
            return [
                {"season_year": 2024, "start_time_utc": "2024-12-31", "home_team_id": 277,
                 "away_team_id": 9, "home_points": 13, "away_points": 19, "notes": "CFP"},
                {"season_year": 2023, "start_time_utc": "2023-12-31", "home_team_id": 277,
                 "away_team_id": 8, "home_points": 27, "away_points": 20, "notes": "Bowl"},
            ]
        if "team_bowl_record_ledger" in flat:
            return list(self._ledger)
        return []


_PROFILE = SimpleNamespace(program_name="Alabama")
_SNAP = SimpleNamespace(team_id=277, slug="alabama")


def test_verified_ledger_renders_all_time_label() -> None:
    db = _StubDB([{"slug": "alabama", "wins": 47, "losses": 26, "ties": 3,
                   "appearances": 76, "last_bowl_year": 2024, "last_bowl_name": "x",
                   "last_bowl_result": "L", "source_name": "sr",
                   "verification_status": "verified"}])
    html = render_bowl_history(db, _PROFILE, _SNAP)
    assert "All-time bowls: 47-26-3" in html


def test_no_ledger_never_says_all_time() -> None:
    html = render_bowl_history(_StubDB([]), _PROFILE, _SNAP)
    assert "Recent postseason" in html
    assert "all-time" not in html.lower()


def test_conflict_ledger_falls_back_to_recent_era() -> None:
    db = _StubDB([{"slug": "alabama", "wins": 99, "losses": 1, "ties": 0,
                   "appearances": 1, "last_bowl_year": 2024, "last_bowl_name": "x",
                   "last_bowl_result": "W", "source_name": "scrape",
                   "verification_status": "conflict"}])
    html = render_bowl_history(db, _PROFILE, _SNAP)
    assert "All-time" not in html
    assert "Recent postseason" in html
    # The unverified 99-1 figure must never reach the page.
    assert "99-1" not in html
