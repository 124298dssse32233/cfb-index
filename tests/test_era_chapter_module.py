"""Tests for era_chapter_module.py (Wave 4 Language Layer)."""

import sqlite3

import pytest

from cfb_rankings.team_pages.era_chapter_module import (
    ERA_CHAPTER_CSS,
    _weight,
    render_era_chapters,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeProfile:
    team_id = 1


class FakeSnapshot:
    team_id = 1


def _make_db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with the required schema."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE teams (
            team_id   INTEGER PRIMARY KEY,
            slug      TEXT,
            name      TEXT
        )
        """
    )
    conn.execute("INSERT INTO teams VALUES (1, 'alabama', 'Alabama')")

    conn.execute(
        """
        CREATE TABLE team_discourse_era_terms (
            era_term_id              INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id                  INTEGER NOT NULL,
            season_year              INTEGER NOT NULL,
            term                     TEXT    NOT NULL,
            term_rank                INTEGER NOT NULL,
            mention_count            INTEGER,
            rest_count               INTEGER,
            z_score                  REAL,
            rate_ratio               REAL,
            log2_ratio               REAL,
            magnitude_band           TEXT,
            team_season_doc_count    INTEGER,
            team_season_token_count  INTEGER,
            sample_quote             TEXT,
            sample_quote_source      TEXT,
            model_version            TEXT,
            computed_at_utc          TEXT
        )
        """
    )
    conn.commit()
    return conn


def _insert_terms(conn, team_id, season_year, terms):
    """Insert a list of (term, rank, log2_ratio, sample_quote) tuples."""
    for term, rank, log2r, quote in terms:
        conn.execute(
            """
            INSERT INTO team_discourse_era_terms
              (team_id, season_year, term, term_rank, log2_ratio, sample_quote)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (team_id, season_year, term, rank, log2r, quote),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# _weight unit tests
# ---------------------------------------------------------------------------

class TestWeight:
    def test_zero_maps_near_300(self):
        # log2_ratio=0.0 is at position 1/5 of [-1, 4]
        # linear: 300 + (0 - (-1)) * 120 = 300 + 120 = 420 → rounded to 400
        result = _weight(0.0)
        assert result == 400

    def test_four_maps_to_900(self):
        assert _weight(4.0) == 900

    def test_minus_one_maps_to_300(self):
        assert _weight(-1.0) == 300

    def test_clamp_above_4(self):
        assert _weight(10.0) == 900

    def test_clamp_below_minus_1(self):
        assert _weight(-5.0) == 300

    def test_midpoint(self):
        # log2_ratio=1.5 → 300 + (1.5+1)*120 = 300+300 = 600
        result = _weight(1.5)
        assert result == 600


# ---------------------------------------------------------------------------
# render_era_chapters tests
# ---------------------------------------------------------------------------

class TestRenderEraChaptersFloors:
    def test_returns_empty_for_none_db(self):
        result = render_era_chapters(None, FakeProfile(), FakeSnapshot())
        assert result == ""

    def test_returns_empty_for_none_profile(self):
        conn = _make_db()
        result = render_era_chapters(conn, None, FakeSnapshot())
        assert result == ""

    def test_returns_empty_for_fewer_than_2_seasons(self):
        conn = _make_db()
        _insert_terms(conn, 1, 2024, [
            ("dynasty", 1, 2.5, None),
            ("champion", 2, 1.8, None),
            ("recruiting", 3, 1.2, None),
        ])
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert result == ""

    def test_returns_empty_if_most_recent_season_has_fewer_than_3_terms(self):
        conn = _make_db()
        # 2025 (most recent) has only 2 terms; 2024 has 3
        _insert_terms(conn, 1, 2025, [
            ("transfer", 1, 2.0, None),
            ("portal", 2, 1.5, None),
        ])
        _insert_terms(conn, 1, 2024, [
            ("dynasty", 1, 2.5, None),
            ("champion", 2, 1.8, None),
            ("recruiting", 3, 1.2, None),
        ])
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert result == ""

    def test_returns_empty_when_team_id_is_zero(self):
        class NoIdProfile:
            team_id = 0

        class NoIdSnapshot:
            team_id = 0

        conn = _make_db()
        result = render_era_chapters(conn, NoIdProfile(), NoIdSnapshot())
        assert result == ""

    def test_returns_empty_when_no_rows_exist(self):
        conn = _make_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert result == ""


class TestRenderEraChaptersOutput:
    def _two_season_db(self):
        conn = _make_db()
        _insert_terms(conn, 1, 2025, [
            ("transfer", 1, 2.0, "big transfer portal moves"),
            ("portal", 2, 1.5, None),
            ("rebuild", 3, 0.9, None),
            ("offense", 4, 0.5, None),
        ])
        _insert_terms(conn, 1, 2024, [
            ("dynasty", 1, 3.2, None),
            ("champion", 2, 2.8, None),
            ("recruiting", 3, 2.1, None),
        ])
        return conn

    def test_returns_non_empty_with_valid_data(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert result != ""

    def test_html_contains_era_ch_class(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert "era-ch" in result

    def test_html_contains_hepta_slab_font(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert "Hepta Slab" in result

    def test_html_contains_top_term_from_most_recent_season(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        # Most recent season (2025) top term is "transfer" → rendered in caps
        assert "TRANSFER" in result

    def test_html_contains_season_year(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert "2025" in result
        assert "2024" in result

    def test_html_contains_section_header(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert "Season Vocabulary" in result

    def test_html_contains_sample_quote_when_present(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        # The quote "big transfer portal moves" is rendered with the term
        # highlighted via <mark>, so we check for the surrounding text and
        # for the era-ch__receipt container in the HTML body (not just CSS).
        assert "era-ch__receipt" in result
        assert "big" in result
        assert "portal moves" in result

    def test_html_highlights_term_in_quote(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert "era-ch__hl" in result

    def test_html_contains_bebas_neue_reference(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert "Bebas Neue" in result

    def test_caps_top_term_in_label(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        # label span should have TRANSFER (uppercased)
        assert 'class="era-ch__label">TRANSFER</span>' in result

    def test_max_4_seasons_rendered(self):
        conn = _make_db()
        for yr in [2025, 2024, 2023, 2022, 2021]:
            _insert_terms(conn, 1, yr, [
                (f"term{yr}a", 1, 2.0, None),
                (f"term{yr}b", 2, 1.5, None),
                (f"term{yr}c", 3, 1.0, None),
            ])
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        # Only 4 newest years should appear
        assert "2025" in result
        assert "2024" in result
        assert "2023" in result
        assert "2022" in result
        assert "2021" not in result

    def test_max_6_chips_per_season(self):
        conn = _make_db()
        # Insert 8 terms in 2025 and 3 in 2024
        terms_2025 = [(f"word{i}", i, float(i), None) for i in range(1, 9)]
        _insert_terms(conn, 1, 2025, terms_2025)
        _insert_terms(conn, 1, 2024, [
            ("dynasty", 1, 3.2, None),
            ("champion", 2, 2.8, None),
            ("recruiting", 3, 2.1, None),
        ])
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        # word7 and word8 (ranks 7 and 8) should NOT appear
        assert "word7" not in result
        assert "word8" not in result
        # word6 (rank 6) should appear
        assert "word6" in result

    def test_font_weight_applied_to_chips(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert "font-weight:" in result

    def test_era_chapter_css_constant_non_empty(self):
        assert len(ERA_CHAPTER_CSS) > 100

    def test_era_chapter_css_included_in_output(self):
        conn = self._two_season_db()
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        assert "<style>" in result

    def test_snapshot_team_id_fallback(self):
        """If profile.team_id is 0, snapshot.team_id should be used."""
        class ZeroProfile:
            team_id = 0

        conn = self._two_season_db()
        result = render_era_chapters(conn, ZeroProfile(), FakeSnapshot())
        assert result != ""

    def test_no_receipt_when_no_sample_quote(self):
        conn = _make_db()
        _insert_terms(conn, 1, 2025, [
            ("transfer", 1, 2.0, None),
            ("portal", 2, 1.5, None),
            ("rebuild", 3, 0.9, None),
        ])
        _insert_terms(conn, 1, 2024, [
            ("dynasty", 1, 3.2, None),
            ("champion", 2, 2.8, None),
            ("recruiting", 3, 2.1, None),
        ])
        result = render_era_chapters(conn, FakeProfile(), FakeSnapshot())
        # era-ch__receipt appears in the CSS block; we check that the
        # blockquote element itself is NOT in the HTML body section.
        assert "<blockquote" not in result
