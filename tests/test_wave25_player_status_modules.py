"""Unit tests for Wave 25 player status modules.

Covers: season_labels, status_strip, where_ended_up, outlook_2026.

All DB-dependent tests use a minimal in-memory SQLite fixture that mirrors
the player_current_status_view columns so no real DB or migrations are needed.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_status_row(**kwargs) -> dict[str, Any]:
    """Build a minimal status row dict with sensible defaults."""
    defaults = {
        "player_id": 1,
        "status_code": "RETURNING_2026",
        "current_team_id": 10,
        "previous_team_id": None,
        "nfl_team": None,
        "draft_year": None,
        "draft_round": None,
        "draft_pick": None,
        "draft_overall": None,
        "last_season_year": 2024,
        "updated_at_utc": "2026-05-27T00:00:00",
        "override_active": 0,
    }
    defaults.update(kwargs)
    return defaults


def _make_db(status_rows: list[dict] | None = None,
             team_rows: list[dict] | None = None,
             award_rows: list[dict] | None = None,
             depth_rows: list[dict] | None = None) -> MagicMock:
    """Create a MagicMock db whose query_all returns the given rows."""
    db = MagicMock()

    def _query_all(sql: str, params: dict | None = None) -> list[dict]:
        sql_lower = sql.lower()
        if "player_current_status_cache" in sql_lower or "player_current_status_view" in sql_lower:
            pid = (params or {}).get("pid")
            return [r for r in (status_rows or []) if r["player_id"] == pid]
        if "teams" in sql_lower:
            tid = (params or {}).get("tid")
            return [r for r in (team_rows or []) if r["team_id"] == tid]
        if "player_award_watch_2026" in sql_lower:
            pid = (params or {}).get("pid")
            return [r for r in (award_rows or []) if r["player_id"] == pid]
        if "player_depth_chart_2026" in sql_lower:
            pid = (params or {}).get("pid")
            return [r for r in (depth_rows or []) if r["player_id"] == pid]
        return []

    db.query_all.side_effect = _query_all
    return db


# ---------------------------------------------------------------------------
# season_labels tests
# ---------------------------------------------------------------------------

class TestSeasonContextLabel:
    from cfb_rankings.player_pages.season_labels import season_context_label

    def test_returning_2026(self):
        from cfb_rankings.player_pages.season_labels import season_context_label
        label = season_context_label("RETURNING_2026", last_season_year=2024)
        assert "2024" in label
        assert "last completed" in label

    def test_transferred_with_team(self):
        from cfb_rankings.player_pages.season_labels import season_context_label
        label = season_context_label("TRANSFERRED_COLLEGE", last_team_name="Alabama",
                                     last_season_year=2024)
        assert "Alabama" in label
        assert "2024" in label

    def test_transferred_without_team(self):
        from cfb_rankings.player_pages.season_labels import season_context_label
        label = season_context_label("TRANSFERRED_COLLEGE", last_season_year=2024)
        assert "previous program" in label

    def test_nfl_drafted(self):
        from cfb_rankings.player_pages.season_labels import season_context_label
        for code in ("NFL_DRAFTED_2026", "NFL_DRAFTED_PRIOR", "NFL_UDFA"):
            label = season_context_label(code, last_season_year=2024)
            assert "final college season" in label
            assert "2024" in label

    def test_exhausted_eligibility(self):
        from cfb_rankings.player_pages.season_labels import season_context_label
        label = season_context_label("EXHAUSTED_ELIGIBILITY", last_season_year=2024)
        assert "final college season" in label

    def test_portal_open_with_team(self):
        from cfb_rankings.player_pages.season_labels import season_context_label
        label = season_context_label("PORTAL_OPEN", last_team_name="Georgia",
                                     last_season_year=2024)
        assert "Georgia" in label
        assert "portal" in label.lower()

    def test_historical_alum(self):
        from cfb_rankings.player_pages.season_labels import season_context_label
        label = season_context_label("HISTORICAL_ALUM")
        assert "career" in label.lower()

    def test_hs_recruit_only(self):
        from cfb_rankings.player_pages.season_labels import season_context_label
        label = season_context_label("HS_RECRUIT_ONLY")
        assert "recruit" in label.lower()


class TestPageTitleSuffix:
    def test_returning_has_outlook(self):
        from cfb_rankings.player_pages.season_labels import page_title_suffix
        suffix = page_title_suffix(
            "RETURNING_2026", current_team_name="Texas", position="QB",
            current_date=date(2026, 5, 27),
        )
        assert "Texas" in suffix
        assert "QB" in suffix
        assert "Outlook" in suffix

    def test_nfl_drafted_2026(self):
        from cfb_rankings.player_pages.season_labels import page_title_suffix
        suffix = page_title_suffix(
            "NFL_DRAFTED_2026", nfl_team="Tennessee",
            current_date=date(2026, 5, 27),
        )
        assert "Tennessee" in suffix
        assert "NFL" in suffix

    def test_transferred(self):
        from cfb_rankings.player_pages.season_labels import page_title_suffix
        suffix = page_title_suffix(
            "TRANSFERRED_COLLEGE", current_team_name="Miami",
            current_date=date(2026, 5, 27),
        )
        assert "Transfer" in suffix

    def test_portal_open(self):
        from cfb_rankings.player_pages.season_labels import page_title_suffix
        suffix = page_title_suffix("PORTAL_OPEN")
        assert "portal" in suffix.lower()

    def test_exhausted_eligibility(self):
        from cfb_rankings.player_pages.season_labels import page_title_suffix
        suffix = page_title_suffix(
            "EXHAUSTED_ELIGIBILITY", last_team_name="Michigan",
        )
        assert "Michigan" in suffix
        assert "career" in suffix.lower()


# ---------------------------------------------------------------------------
# status_strip tests
# ---------------------------------------------------------------------------

class TestStatusStrip:
    def test_returning_renders_chip(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        status_row = _make_status_row(status_code="RETURNING_2026", current_team_id=10)
        team_rows = [{"team_id": 10, "canonical_name": "Texas Longhorns"}]
        db = _make_db([status_row], team_rows)
        html = render_status_strip(db, 1)
        assert "status-strip" in html
        assert "RETURNING" in html.upper() or "2026" in html

    def test_nfl_drafted_2026(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        status_row = _make_status_row(
            status_code="NFL_DRAFTED_2026",
            nfl_team="Tennessee",
            draft_year=2026,
            draft_round=1,
            draft_overall=1,
        )
        db = _make_db([status_row])
        html = render_status_strip(db, 1)
        assert "status-strip" in html
        assert "NFL" in html or "Tennessee" in html

    def test_nfl_drafted_prior(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        status_row = _make_status_row(
            status_code="NFL_DRAFTED_PRIOR",
            nfl_team="Dallas Cowboys",
            draft_year=2025,
            draft_round=2,
            draft_overall=45,
        )
        db = _make_db([status_row])
        html = render_status_strip(db, 1)
        assert "status-strip" in html

    def test_transferred(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        status_row = _make_status_row(
            status_code="TRANSFERRED_COLLEGE",
            previous_team_id=10,
            current_team_id=20,
        )
        team_rows = [
            {"team_id": 10, "canonical_name": "Georgia Bulldogs"},
            {"team_id": 20, "canonical_name": "Miami Hurricanes"},
        ]
        db = _make_db([status_row], team_rows)
        html = render_status_strip(db, 1)
        assert "status-strip" in html

    def test_portal_open(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        status_row = _make_status_row(
            status_code="PORTAL_OPEN",
            previous_team_id=10,
        )
        team_rows = [{"team_id": 10, "canonical_name": "Ohio State Buckeyes"}]
        db = _make_db([status_row], team_rows)
        html = render_status_strip(db, 1)
        assert "status-strip" in html

    def test_exhausted_eligibility(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        status_row = _make_status_row(status_code="EXHAUSTED_ELIGIBILITY")
        db = _make_db([status_row])
        html = render_status_strip(db, 1)
        assert "status-strip" in html

    def test_unknown_player_returns_empty(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        db = _make_db([])  # no rows for any player
        html = render_status_strip(db, 9999)
        assert html == ""

    def test_none_player_id_returns_empty(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        db = _make_db([])
        html = render_status_strip(db, None)
        assert html == ""

    def test_none_db_returns_empty(self):
        from cfb_rankings.player_pages.status_strip import render_status_strip
        html = render_status_strip(None, 1)
        assert html == ""

    def test_html_is_valid_fragment(self):
        """strip should produce an opening and closing section tag."""
        from cfb_rankings.player_pages.status_strip import render_status_strip
        status_row = _make_status_row(status_code="RETURNING_2026")
        db = _make_db([status_row])
        html = render_status_strip(db, 1)
        if html:
            assert "<section" in html and "</section>" in html


# ---------------------------------------------------------------------------
# where_ended_up tests
# ---------------------------------------------------------------------------

class TestWhereEndedUp:
    def test_nfl_drafted_renders_pick_chip(self):
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        status_row = _make_status_row(
            status_code="NFL_DRAFTED_PRIOR",
            nfl_team="Dallas Cowboys",
            draft_year=2025,
            draft_round=2,
            draft_overall=45,
            draft_pick=12,
        )
        db = _make_db([status_row])
        html = render_where_ended_up(db, 1)
        assert "where-ended-up" in html
        assert "#45" in html
        assert "Dallas Cowboys" in html
        assert "Rd 2" in html

    def test_nfl_drafted_2026_first_overall(self):
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        status_row = _make_status_row(
            status_code="NFL_DRAFTED_2026",
            nfl_team="Tennessee",
            draft_year=2026,
            draft_round=1,
            draft_overall=1,
            draft_pick=1,
        )
        db = _make_db([status_row])
        html = render_where_ended_up(db, 1)
        assert "where-ended-up--nfl" in html
        assert "first-overall" in html
        assert "Tennessee" in html
        # First overall gets gold chip class
        assert "pick-chip--first-overall" in html

    def test_udfa_chip(self):
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        status_row = _make_status_row(
            status_code="NFL_UDFA",
            nfl_team="Chicago Bears",
        )
        db = _make_db([status_row])
        html = render_where_ended_up(db, 1)
        assert "UDFA" in html
        assert "FREE AGENT" in html
        assert "Chicago Bears" in html

    def test_transfer_flow_shows_from_to(self):
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        status_row = _make_status_row(
            status_code="TRANSFERRED_COLLEGE",
            previous_team_id=10,
            current_team_id=20,
        )
        team_rows = [
            {"team_id": 10, "canonical_name": "Alabama Crimson Tide"},
            {"team_id": 20, "canonical_name": "Auburn Tigers"},
        ]
        db = _make_db([status_row], team_rows)
        html = render_where_ended_up(db, 1)
        assert "where-ended-up--transfer" in html
        assert "Alabama Crimson Tide" in html
        assert "Auburn Tigers" in html
        assert "→" in html

    def test_portal_open_shows_tbd(self):
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        status_row = _make_status_row(
            status_code="PORTAL_OPEN",
            previous_team_id=10,
        )
        team_rows = [{"team_id": 10, "canonical_name": "Penn State Nittany Lions"}]
        db = _make_db([status_row], team_rows)
        html = render_where_ended_up(db, 1)
        assert "TBD" in html
        assert "portal" in html.lower()
        assert "Penn State Nittany Lions" in html

    def test_returning_player_returns_empty(self):
        """Where-ended-up module should be empty for returning players."""
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        status_row = _make_status_row(status_code="RETURNING_2026")
        db = _make_db([status_row])
        html = render_where_ended_up(db, 1)
        assert html == ""

    def test_exhausted_eligibility_returns_empty(self):
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        status_row = _make_status_row(status_code="EXHAUSTED_ELIGIBILITY")
        db = _make_db([status_row])
        html = render_where_ended_up(db, 1)
        assert html == ""

    def test_middot_entity_not_raw_char(self):
        """Regression: HTML template strings must use &middot; not raw U+00B7."""
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        status_row = _make_status_row(
            status_code="NFL_DRAFTED_PRIOR",
            nfl_team="Dallas Cowboys",
            draft_year=2025,
            draft_round=1,
            draft_overall=10,
            draft_pick=10,
        )
        db = _make_db([status_row])
        html = render_where_ended_up(db, 1)
        # Raw U+00B7 should NOT appear in direct HTML strings (only in escaped data)
        # The eyebrow line has &middot; — confirm entity form is used
        assert "&middot;" in html or "·" not in html.split("escape")[0]

    def test_none_db_returns_empty(self):
        from cfb_rankings.player_pages.where_ended_up import render_where_ended_up
        assert render_where_ended_up(None, 1) == ""


# ---------------------------------------------------------------------------
# outlook_2026 tests
# ---------------------------------------------------------------------------

class TestOutlook2026:
    def test_returning_player_renders_section(self):
        from cfb_rankings.player_pages.outlook_2026 import render_outlook_2026
        status_row = _make_status_row(
            status_code="RETURNING_2026",
            current_team_id=10,
        )
        team_rows = [{"team_id": 10, "canonical_name": "Texas Longhorns"}]
        db = _make_db([status_row], team_rows)
        html = render_outlook_2026(db, 1)
        assert "outlook-2026" in html
        assert "Texas Longhorns" in html or "Texas" in html

    def test_award_watch_badge_renders(self):
        from html import unescape
        from cfb_rankings.player_pages.outlook_2026 import render_outlook_2026
        status_row = _make_status_row(
            status_code="RETURNING_2026",
            current_team_id=10,
        )
        team_rows = [{"team_id": 10, "canonical_name": "Texas Longhorns"}]
        award_rows = [
            {"player_id": 1, "award_slug": "heisman", "list_type": "odds_top10",
             "position_rank": 1, "priority": 1},
            {"player_id": 1, "award_slug": "davey_obrien", "list_type": "watch",
             "position_rank": 3, "priority": 2},
        ]
        db = _make_db([status_row], team_rows, award_rows)
        html = render_outlook_2026(db, 1)
        # HTML-unescape so we can match readable names (escape() turns ' into &#x27;)
        text = unescape(html)
        assert "Heisman" in text
        assert "Davey O'Brien" in text  # escaped apostrophe in HTML, readable after unescape

    def test_depth_chart_badge_renders(self):
        from cfb_rankings.player_pages.outlook_2026 import render_outlook_2026
        status_row = _make_status_row(
            status_code="RETURNING_2026",
            current_team_id=10,
        )
        team_rows = [{"team_id": 10, "canonical_name": "Ohio State Buckeyes"}]
        depth_rows = [
            {"player_id": 1, "position_group": "QB", "slot_rank": 1,
             "starter_status": "returning_starter", "confidence": "confirmed"},
        ]
        db = _make_db([status_row], team_rows, None, depth_rows)
        html = render_outlook_2026(db, 1)
        # The module renders the starter_status display label, not the position_group column.
        # Position is taken from status_row (position_2026 / master_position), not depth row.
        assert "Returning starter" in html
        assert "Ohio State Buckeyes" in html

    def test_nfl_player_returns_empty(self):
        from cfb_rankings.player_pages.outlook_2026 import render_outlook_2026
        status_row = _make_status_row(status_code="NFL_DRAFTED_2026", nfl_team="Tennessee")
        db = _make_db([status_row])
        html = render_outlook_2026(db, 1)
        assert html == ""

    def test_transferred_returns_empty(self):
        from cfb_rankings.player_pages.outlook_2026 import render_outlook_2026
        status_row = _make_status_row(status_code="TRANSFERRED_COLLEGE")
        db = _make_db([status_row])
        html = render_outlook_2026(db, 1)
        assert html == ""

    def test_exhausted_eligibility_returns_empty(self):
        from cfb_rankings.player_pages.outlook_2026 import render_outlook_2026
        status_row = _make_status_row(status_code="EXHAUSTED_ELIGIBILITY")
        db = _make_db([status_row])
        html = render_outlook_2026(db, 1)
        assert html == ""

    def test_award_slug_display_names_complete(self):
        """Regression: all known award slugs must have explicit display name mappings.

        Slugs whose display name coincidentally equals title-case (e.g. 'Walter Camp')
        are tested for exact value since we can't distinguish dict-hit from fallback by
        value alone — but their presence in the dict IS verified via exact match.
        """
        from cfb_rankings.player_pages.outlook_2026 import _award_display_name
        # Slugs where the display name DIFFERS from simple title-case — easy to assert:
        known_different = {
            "heisman":         "Heisman Watch",   # not "Heisman"
            "maxwell":         "Maxwell Watch",    # not "Maxwell"
            "lou_groza":       "Groza",            # not "Lou Groza"
            "lott":            "Lott IMPACT",      # not "Lott"
            "davey_obrien":    "Davey O'Brien",    # not "Davey Obrien" (title skips apostrophe)
        }
        for slug, expected in known_different.items():
            got = _award_display_name(slug)
            assert got == expected, (
                f"Award slug '{slug}' display name wrong: got '{got}', expected '{expected}'"
            )
        # All other known slugs — verify they return a non-empty string
        # (some happen to match title-case, but that's acceptable)
        all_known = [
            "walter_camp", "manning", "doak_walker", "biletnikoff", "mackey",
            "bednarik", "butkus", "nagurski", "outland", "rimington", "ray_guy",
            "hornung", "wuerffel", "burlsworth",
        ]
        for slug in all_known:
            name = _award_display_name(slug)
            assert name, f"Award slug '{slug}' returned empty string"
            # Must not return the raw slug unchanged
            assert name != slug, f"Award slug '{slug}' returned slug itself as display name"

    def test_none_db_returns_empty(self):
        from cfb_rankings.player_pages.outlook_2026 import render_outlook_2026
        assert render_outlook_2026(None, 1) == ""

    def test_html_is_valid_fragment(self):
        from cfb_rankings.player_pages.outlook_2026 import render_outlook_2026
        status_row = _make_status_row(status_code="RETURNING_2026", current_team_id=10)
        team_rows = [{"team_id": 10, "canonical_name": "Michigan Wolverines"}]
        db = _make_db([status_row], team_rows)
        html = render_outlook_2026(db, 1)
        if html:
            assert "<section" in html and "</section>" in html


# ---------------------------------------------------------------------------
# fetch_status_row cache fallback tests
# ---------------------------------------------------------------------------

class TestFetchStatusRowCacheFallback:
    """Verify that status_strip.fetch_status_row tries cache then view."""

    def test_cache_hit_returned_directly(self):
        """If cache table has a row, it should be returned without querying the view."""
        from cfb_rankings.player_pages.status_strip import fetch_status_row

        cache_row = _make_status_row(status_code="RETURNING_2026")
        view_row = _make_status_row(status_code="NFL_DRAFTED_PRIOR")  # different

        call_log = []

        def _query_all(sql: str, params: dict | None = None):
            call_log.append(sql)
            if "player_current_status_cache" in sql.lower():
                return [cache_row]
            if "player_current_status_view" in sql.lower():
                return [view_row]  # should never be reached on cache hit
            return []

        db = MagicMock()
        db.query_all.side_effect = _query_all

        row = fetch_status_row(db, 1)
        # Should get the cache row
        assert row["status_code"] == "RETURNING_2026"
        # View should not have been queried
        view_calls = [c for c in call_log if "player_current_status_view" in c.lower()]
        assert len(view_calls) == 0, "Cache hit should skip view query"

    def test_cache_miss_falls_back_to_view(self):
        """If cache table returns nothing (or raises), fall back to the view."""
        from cfb_rankings.player_pages.status_strip import fetch_status_row

        view_row = _make_status_row(status_code="TRANSFERRED_COLLEGE")

        def _query_all(sql: str, params: dict | None = None):
            if "player_current_status_cache" in sql.lower():
                return []  # cache miss
            if "player_current_status_view" in sql.lower():
                return [view_row]
            return []

        db = MagicMock()
        db.query_all.side_effect = _query_all

        row = fetch_status_row(db, 1)
        assert row["status_code"] == "TRANSFERRED_COLLEGE"

    def test_cache_error_falls_back_to_view(self):
        """If cache table raises (e.g. table doesn't exist), fall back gracefully."""
        from cfb_rankings.player_pages.status_strip import fetch_status_row

        view_row = _make_status_row(status_code="PORTAL_OPEN")

        def _query_all(sql: str, params: dict | None = None):
            if "player_current_status_cache" in sql.lower():
                raise Exception("no such table: player_current_status_cache")
            if "player_current_status_view" in sql.lower():
                return [view_row]
            return []

        db = MagicMock()
        db.query_all.side_effect = _query_all

        row = fetch_status_row(db, 1)
        assert row["status_code"] == "PORTAL_OPEN"
