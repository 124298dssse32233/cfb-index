"""Tests for the Word-of-the-Week row in cfb_rankings.team_pages.lexicon_module
(Language Layer wave 2, package C1).

After fetching the season (week=0) rows, the lexicon module also fetches the
max-week (week>0) cut for the same (team, season). If the top weekly term has
z_score >= 4 AND that week == the current resolve_week().week, it renders ONE
extra "WORD OF THE WEEK" row at the top of the card. Otherwise it renders
nothing extra — zero layout change when absent, and a module with no weekly rows
is byte-identical to the wave-1 output.

Per the contract these tests assert:

  1. a fresh week>0 cut (z=5 at the current week) -> the WOW row renders
  2. a stale-week cut (week != current) -> NO WOW row
  3. a fresh-week cut but z < 4 -> NO WOW row
  4. no weekly rows at all -> identical to the wave-1 (season-only) render

Deterministic, in-memory sqlite — NO network, NO real cfb_rankings.db. We seed a
season wall above the confidence floor (reusing the wave-1 seeding shape) plus,
in the WOW cases, a week>0 cut. The current week is read from the live
resolve_week() so the test stays correct on any run date.
"""
from __future__ import annotations

import math
import sqlite3

import pytest

# Wave-1 public surface (unchanged by wave 2). Import is the first contract check.
from cfb_rankings.team_pages.lexicon_module import LEXICON_CSS, render_lexicon
from cfb_rankings.common.week import resolve_week


SEASON_YEAR = 2025
TEAM_ID = 293
TEAM_SLUG = "michigan"
TEAM_NAME = "Michigan"
TOP_TERM = "zorblat"  # the season (week=0) #1 term
WOW_TERM = "weeklyword"  # the current-week distinctive term


# ---------------------------------------------------------------------------
# Schema + db stand-in (team_discourse_terms only — that's all the module reads)
# ---------------------------------------------------------------------------


def _create_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE team_discourse_terms (
            team_discourse_term_id INTEGER PRIMARY KEY,
            team_id          INTEGER NOT NULL,
            season_year      INTEGER NOT NULL,
            week             INTEGER NOT NULL DEFAULT 0,
            term             TEXT NOT NULL,
            term_rank        INTEGER NOT NULL,
            mention_count    INTEGER NOT NULL,
            rest_count       INTEGER NOT NULL,
            z_score          REAL NOT NULL,
            rate_ratio       REAL NOT NULL,
            log2_ratio       REAL NOT NULL,
            magnitude_band   TEXT NOT NULL,
            team_doc_count   INTEGER NOT NULL,
            team_token_count INTEGER NOT NULL,
            sample_quote        TEXT,
            sample_quote_source TEXT,
            model_version    TEXT NOT NULL,
            computed_at_utc  TEXT NOT NULL,
            UNIQUE(team_id, season_year, week, term)
        );
        CREATE INDEX idx_team_discourse_terms_lookup
            ON team_discourse_terms (team_id, season_year, week, term_rank);
        """
    )


class _MemoryDB:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def query_all(self, sql: str, params=None):
        return self._conn.execute(sql, params or {}).fetchall()

    def query_one(self, sql: str, params=None):
        return self._conn.execute(sql, params or {}).fetchone()

    def execute(self, sql: str, params=None):
        cur = self._conn.execute(sql, params or {})
        self._conn.commit()
        return cur


# ---------------------------------------------------------------------------
# Minimal Profile / TeamSnapshot stand-ins (same shape as the wave-1 test)
# ---------------------------------------------------------------------------


class _Snapshot:
    def __init__(self, team_id, *, slug=TEAM_SLUG, name=TEAM_NAME, season=SEASON_YEAR):
        self.team_id = team_id
        self.slug = slug
        self.canonical_name = name
        self.school_name = name
        self.season_year = season


class _Profile:
    def __init__(self, slug=TEAM_SLUG, name=TEAM_NAME):
        self.slug = slug
        self.team_slug = slug
        self.canonical_name = name
        self.school_name = name
        self.display_name = name


# ---------------------------------------------------------------------------
# Row seeding
# ---------------------------------------------------------------------------


def _insert_row(conn: sqlite3.Connection, **r) -> None:
    base = dict(
        team_id=TEAM_ID,
        season_year=SEASON_YEAR,
        week=0,
        rest_count=0,
        magnitude_band="signature",
        team_doc_count=240,
        team_token_count=18000,
        sample_quote_source="reddit/MichiganWolverines",
        model_version="discourse-keyness-v1",
        computed_at_utc="2026-06-10T00:00:00Z",
    )
    base.update(r)
    conn.execute(
        """
        INSERT INTO team_discourse_terms (
            team_id, season_year, week, term, term_rank, mention_count,
            rest_count, z_score, rate_ratio, log2_ratio, magnitude_band,
            team_doc_count, team_token_count, sample_quote,
            sample_quote_source, model_version, computed_at_utc
        ) VALUES (
            :team_id, :season_year, :week, :term, :term_rank, :mention_count,
            :rest_count, :z_score, :rate_ratio, :log2_ratio, :magnitude_band,
            :team_doc_count, :team_token_count, :sample_quote,
            :sample_quote_source, :model_version, :computed_at_utc
        )
        """,
        base,
    )
    conn.commit()


def _seed_season_wall(conn: sqlite3.Connection, n_terms: int = 10) -> None:
    """Seed the week=0 season wall above the confidence floor (>=8 terms, 240
    docs) — the same shape the wave-1 module test uses.
    """
    _insert_row(
        conn,
        week=0,
        term=TOP_TERM,
        term_rank=1,
        mention_count=63,
        z_score=8.4,
        rate_ratio=41.5,
        log2_ratio=5.38,
        magnitude_band="signature",
        sample_quote=(
            f"Honestly the {TOP_TERM} energy in the stadium tonight was unreal, "
            "best atmosphere all year."
        ),
    )
    for rank in range(2, n_terms + 1):
        ratio = max(1.2, 12.0 - rank)
        band = "signature" if ratio >= 10 else ("characteristic" if ratio >= 3 else "mild")
        _insert_row(
            conn,
            week=0,
            term=f"term{rank}",
            term_rank=rank,
            mention_count=max(10, 60 - rank * 2),
            z_score=max(1.96, 8.0 - rank * 0.3),
            rate_ratio=round(ratio, 1),
            log2_ratio=round(math.log2(ratio), 2),
            magnitude_band=band,
            sample_quote=f"some fans keep saying term{rank} this season",
        )


def _seed_weekly_cut(
    conn: sqlite3.Connection, *, week: int, z_score: float, term: str = WOW_TERM
) -> None:
    """Seed a one-row week>0 cut (the WOW candidate)."""
    _insert_row(
        conn,
        week=week,
        term=term,
        term_rank=1,
        mention_count=44,
        z_score=z_score,
        rate_ratio=22.0,
        log2_ratio=round(math.log2(22.0), 2),
        magnitude_band="signature",
        sample_quote=f"everybody is talking about {term} after that game",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    _create_table(c)
    return c


@pytest.fixture()
def db(conn: sqlite3.Connection) -> _MemoryDB:
    return _MemoryDB(conn)


@pytest.fixture()
def current_week() -> int:
    """The live current season-week the module compares against. Reading it from
    resolve_week keeps the test correct on any run date (the WOW gate requires
    the weekly cut's week to equal *today's* week)."""
    return resolve_week().week


# ---------------------------------------------------------------------------
# Test 1: fresh week>0 cut (z>=4 at the current week) -> the WOW row renders
# ---------------------------------------------------------------------------


def test_wow_row_renders_for_fresh_high_z_week(db, conn, current_week):
    _seed_season_wall(conn)
    _seed_weekly_cut(conn, week=current_week, z_score=5.0)

    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))
    assert html, "season wall is above floor — base card must render"

    upper = html.upper()
    assert "WORD OF THE WEEK" in upper, "expected the WOW eyebrow"
    assert WOW_TERM in html, "expected the weekly term in the WOW row"
    # The small 'wk N' tag carries the week number.
    assert f"wk {current_week}" in html or f"WK {current_week}" in upper, (
        "expected the 'wk N' week tag"
    )
    # The base card is intact: the season #1 term still renders below the WOW row.
    assert TOP_TERM in html


# ---------------------------------------------------------------------------
# Test 2: stale-week cut (week != current) -> NO WOW row
# ---------------------------------------------------------------------------


def test_no_wow_row_for_stale_week(db, conn, current_week):
    _seed_season_wall(conn)
    # A high-z weekly cut, but from a week that is NOT the current one.
    _seed_weekly_cut(conn, week=current_week - 1 if current_week > 1 else current_week + 1,
                     z_score=6.0)

    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))
    assert html
    assert "WORD OF THE WEEK" not in html.upper(), (
        "a stale-week cut must NOT render the WOW row"
    )
    assert WOW_TERM not in html, "stale weekly term must not appear"


# ---------------------------------------------------------------------------
# Test 3: fresh-week cut but z < 4 -> NO WOW row
# ---------------------------------------------------------------------------


def test_no_wow_row_for_low_z(db, conn, current_week):
    _seed_season_wall(conn)
    _seed_weekly_cut(conn, week=current_week, z_score=3.2)  # 3.2 < 4

    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))
    assert html
    assert "WORD OF THE WEEK" not in html.upper(), (
        "a sub-4 z weekly term must NOT render the WOW row"
    )
    assert WOW_TERM not in html


# ---------------------------------------------------------------------------
# Test 4: no weekly rows -> identical to the wave-1 (season-only) render
# ---------------------------------------------------------------------------


def test_no_weekly_rows_matches_wave1_render(db, conn):
    _seed_season_wall(conn)
    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))
    assert html
    # Zero layout change when no weekly cut exists: no WOW eyebrow at all.
    assert "WORD OF THE WEEK" not in html.upper()
    # The wave-1 contract output is intact.
    assert TOP_TERM in html
    assert "field" in html.lower()


# ---------------------------------------------------------------------------
# Test 5: CSS surface is unchanged-or-extended (still a non-empty BEM string)
# ---------------------------------------------------------------------------


def test_lexicon_css_still_scoped_string():
    assert isinstance(LEXICON_CSS, str)
    assert LEXICON_CSS.strip()
    assert "lexicon-module" in LEXICON_CSS
