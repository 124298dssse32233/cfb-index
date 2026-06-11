"""Tests for cfb_rankings.team_pages.lexicon_module (Language Layer wave 1).

The module renders the "THE LEXICON" team-page card from team_discourse_terms.
Per the contract:

  - render_lexicon(db, profile, snapshot) -> str
  - CONFIDENCE FLOOR: return "" unless >= 8 terms AND team_doc_count >= 200.
  - When it renders, the HTML must contain the #1 term and an "xN.N the field"
    chip, and a receipt block built from the #1 term's sample_quote.

Tests run against an in-memory sqlite db (no network, no real cfb_rankings.db).
We feed the module a thin Database stand-in (query_all/query_one named-param
surface) and minimal Profile / TeamSnapshot stand-ins that expose the attrs the
sibling modules read (team_id, canonical_name, season_year, slug).
"""
from __future__ import annotations

import sqlite3
import math

import pytest

# First line of the contract being exercised: the module + its public API exist.
# Until the builder lands, these tests error on ImportError (a
# missing-implementation signal, not a logic bug).
from cfb_rankings.team_pages.lexicon_module import LEXICON_CSS, render_lexicon


SEASON_YEAR = 2025
TEAM_ID = 293
TEAM_SLUG = "michigan"
TEAM_NAME = "Michigan"
TOP_TERM = "zorblat"


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
    """Minimal Database stand-in (named-param query surface) over one conn."""

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
# Minimal Profile / TeamSnapshot stand-ins
#
# Sibling modules (rent_free_module) read snapshot.team_id and
# snapshot.canonical_name; fanbase_health reads snapshot.season_year. We expose
# all of those plus slug, which the structural/cohort line may use. Using a
# permissive stand-in (rather than the real dataclasses) keeps these tests
# decoupled from the full team_pages.data import graph.
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


def _seed_terms(
    conn: sqlite3.Connection,
    n_terms: int,
    *,
    team_id: int = TEAM_ID,
    season_year: int = SEASON_YEAR,
    team_doc_count: int = 240,
) -> None:
    """Seed n_terms ranked rows. Rank 1 is TOP_TERM with a known ratio + quote.

    log2_ratio descends down the wall so the module's weight-axis mapping has a
    real min..max spread to interpolate over. team_doc_count is identical across
    rows (it's a per-(team,season) corpus receipt, same on every row).
    """
    rows = []
    # #1 distinctive term: big ratio, a sample quote that embeds the term so the
    # receipt block can highlight it.
    rows.append(
        dict(
            term=TOP_TERM,
            term_rank=1,
            mention_count=63,
            rest_count=0,
            z_score=8.4,
            rate_ratio=41.5,
            log2_ratio=5.38,
            magnitude_band="signature",
            sample_quote=(
                f"Honestly the {TOP_TERM} energy in the stadium tonight was "
                "unreal, best atmosphere all year."
            ),
            sample_quote_source="reddit/MichiganWolverines",
        )
    )
    # Filler ranks 2..n with descending ratios spanning signature/characteristic.
    for rank in range(2, n_terms + 1):
        ratio = max(1.2, 12.0 - rank)  # 10.0, 9.0, ... down toward ~1.2
        band = "signature" if ratio >= 10 else ("characteristic" if ratio >= 3 else "mild")
        rows.append(
            dict(
                term=f"term{rank}",
                term_rank=rank,
                mention_count=max(10, 60 - rank * 2),
                rest_count=rank,
                z_score=max(1.96, 8.0 - rank * 0.3),
                rate_ratio=round(ratio, 1),
                log2_ratio=round(math.log2(ratio), 2),
                magnitude_band=band,
                sample_quote=f"some fans keep saying term{rank} this season",
                sample_quote_source="reddit/MichiganWolverines",
            )
        )

    for r in rows:
        conn.execute(
            """
            INSERT INTO team_discourse_terms (
                team_id, season_year, week, term, term_rank, mention_count,
                rest_count, z_score, rate_ratio, log2_ratio, magnitude_band,
                team_doc_count, team_token_count, sample_quote,
                sample_quote_source, model_version, computed_at_utc
            ) VALUES (
                :team_id, :season_year, 0, :term, :term_rank, :mention_count,
                :rest_count, :z_score, :rate_ratio, :log2_ratio, :magnitude_band,
                :team_doc_count, :team_token_count, :sample_quote,
                :sample_quote_source, 'discourse-keyness-v1', '2026-06-10T00:00:00Z'
            )
            """,
            dict(
                team_id=team_id,
                season_year=season_year,
                team_doc_count=team_doc_count,
                team_token_count=18000,
                **r,
            ),
        )
    conn.commit()


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


# ---------------------------------------------------------------------------
# Test 1: full render above the floor contains the #1 term + xN.N chip + receipt
# ---------------------------------------------------------------------------


def test_render_above_floor_has_top_term_and_chip(db, conn):
    _seed_terms(conn, n_terms=10, team_doc_count=240)
    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))

    assert html, "expected non-empty HTML above the confidence floor"
    assert TOP_TERM in html, "the #1 distinctive term must appear"
    # The 'x NN.N the field' chip. Format the engine stores rate_ratio=41.5,
    # which the module prints to one decimal as 'x41.5'. Accept either an
    # 'x41.5' token or the bare '41.5' (in case the 'x' is a separate element),
    # but the word "field" cohort copy must be present.
    assert ("x41.5" in html) or ("41.5" in html), (
        "expected the #1 term's ratio chip (x41.5) in the render"
    )
    assert "field" in html.lower(), "expected the 'the field' cohort copy"


def test_render_above_floor_has_receipt_quote_highlighted(db, conn):
    _seed_terms(conn, n_terms=10, team_doc_count=240)
    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))

    assert html
    # The receipt block carries the #1 term's sample quote text + provenance.
    assert "best atmosphere all year" in html, "expected the sample quote prose"
    assert "reddit/MichiganWolverines" in html, "expected the provenance line"
    # The #1 term's first occurrence in the quote is wrapped in a <mark>-styled
    # span — at minimum a <mark, <span class containing 'mark', or the BEM
    # highlight class must be present.
    assert ("<mark" in html.lower()) or ("mark" in html.lower()), (
        "expected the term highlighted via a <mark> / mark-styled span"
    )


# ---------------------------------------------------------------------------
# Test 2: below the term-count floor (< 8 terms) returns ""
# ---------------------------------------------------------------------------


def test_below_term_floor_returns_empty(db, conn):
    _seed_terms(conn, n_terms=7, team_doc_count=240)  # 7 < 8
    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))
    assert html == "", f"expected empty render below the 8-term floor, got {html!r}"


# ---------------------------------------------------------------------------
# Test 3: below the doc-count floor (< 200) returns ""
# ---------------------------------------------------------------------------


def test_below_doc_floor_returns_empty(db, conn):
    _seed_terms(conn, n_terms=10, team_doc_count=150)  # 150 < 200
    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))
    assert html == "", f"expected empty render below the 200-doc floor, got {html!r}"


# ---------------------------------------------------------------------------
# Test 4: no rows at all returns "" (graceful empty state)
# ---------------------------------------------------------------------------


def test_no_rows_returns_empty(db):
    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))
    assert html == "", "expected empty render when the team has no terms"


# ---------------------------------------------------------------------------
# Test 5: missing snapshot / team_id degrades to "" (page contract)
# ---------------------------------------------------------------------------


def test_missing_snapshot_returns_empty(db):
    assert render_lexicon(db, _Profile(), None) == ""


def test_missing_team_id_returns_empty(db, conn):
    _seed_terms(conn, n_terms=10, team_doc_count=240)
    assert render_lexicon(db, _Profile(), _Snapshot(None)) == ""


def test_none_db_returns_empty():
    assert render_lexicon(None, _Profile(), _Snapshot(TEAM_ID)) == ""


# ---------------------------------------------------------------------------
# Test 6: latest season is selected when multiple seasons exist
# ---------------------------------------------------------------------------


def test_picks_latest_season(db, conn):
    # An older season's term wall that, if (wrongly) chosen, would surface a
    # different #1 term. Latest = max(season_year) per the contract.
    _seed_terms(conn, n_terms=10, season_year=2024, team_doc_count=240)
    # Overwrite the 2024 #1 term to a distinct value so a season mix-up is
    # visible. (term is unique per (team,season,week); update rank-1 row.)
    conn.execute(
        """
        UPDATE team_discourse_terms
        SET term = 'oldword', sample_quote = 'old season oldword chatter'
        WHERE team_id = ? AND season_year = 2024 AND term_rank = 1
        """,
        (TEAM_ID,),
    )
    conn.commit()
    # The current season with the real #1 term.
    _seed_terms(conn, n_terms=10, season_year=2025, team_doc_count=240)

    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID, season=2025))
    assert html
    assert TOP_TERM in html, "should render the latest (2025) season's #1 term"
    assert "oldword" not in html, "must not pull the prior season's terms"


# ---------------------------------------------------------------------------
# Test 7: db text is HTML-escaped (no raw injection of term/quote)
# ---------------------------------------------------------------------------


def test_db_text_is_html_escaped(db, conn):
    _seed_terms(conn, n_terms=10, team_doc_count=240)
    # Poison the #1 term's quote with an HTML-breaking string. The module must
    # escape it (html.escape) so the raw '<script>' never reaches the markup.
    conn.execute(
        """
        UPDATE team_discourse_terms
        SET sample_quote = 'pre <script>alert(1)</script> post & "quote" energy'
        WHERE team_id = ? AND season_year = ? AND term_rank = 1
        """,
        (TEAM_ID, SEASON_YEAR),
    )
    conn.commit()

    html = render_lexicon(db, _Profile(), _Snapshot(TEAM_ID))
    assert html
    assert "<script>alert(1)</script>" not in html, "unescaped script tag leaked"
    assert "&lt;script&gt;" in html, "expected the script tag to be HTML-escaped"


# ---------------------------------------------------------------------------
# Test 8: LEXICON_CSS is a non-empty BEM-scoped stylesheet string
# ---------------------------------------------------------------------------


def test_lexicon_css_is_scoped_string():
    assert isinstance(LEXICON_CSS, str)
    assert LEXICON_CSS.strip(), "LEXICON_CSS must be non-empty"
    # BEM class prefix per the contract.
    assert "lexicon-module" in LEXICON_CSS
