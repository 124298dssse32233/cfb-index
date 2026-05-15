"""Tests for the Transfer Portal Heat Index (S3) surface.

Covers:
    1. portal_moves UPSERT helper from wire/ingestion.py
       (the Sprint v5-1 Day 4 Adapter 1)
    2. Net-delta computation (entries - exits, star-weighted)
    3. Empty-state rendering (table empty -> valid HTML page)
    4. Smoke imports for the public surface (__init__.py)

Tests build their own minimal SQLite schemas so they do not depend on
the project's full migration tree. The portal_moves columns match
``src/cfb_rankings/migrations.py:1462`` exactly (player_name,
announced_date, slugs, etc.) — see
``DESIGN_AUDIT_2026_05_15_v5_4.md`` Part 5 Adapter 1.

Cross-platform: paths use pathlib, sql uses ISO date strings, no
strftime tokens that differ between Linux/Windows.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Test harness: minimal portal_moves schema + helpers.
# ---------------------------------------------------------------------------

PORTAL_MOVES_DDL = """
create table if not exists portal_moves (
  portal_move_id integer primary key autoincrement,
  player_name text not null,
  from_team_id integer,
  to_team_id integer,
  from_team_slug text,
  to_team_slug text,
  position text,
  announced_date text not null,
  summary text not null,
  issue_number text,
  sources_json text not null default '[]',
  ingested_at text not null default current_timestamp
);
create unique index if not exists idx_portal_moves_upsert_key
  on portal_moves (player_name, announced_date, coalesce(from_team_slug, ''));
create index if not exists idx_portal_moves_lookup
  on portal_moves (announced_date, player_name);
"""

TEAMS_DDL = """
create table if not exists teams (
  team_id integer primary key autoincrement,
  slug text unique,
  canonical_name text,
  school_name text,
  short_name text,
  level_code text,
  is_active integer default 1
);
"""


def _fresh_db(tmp_path: Path) -> sqlite3.Connection:
    """Return a fresh sqlite3.Connection with portal_moves + teams ready."""
    conn = sqlite3.connect(str(tmp_path / "test_portal_heat.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(PORTAL_MOVES_DDL + TEAMS_DDL)
    conn.commit()
    return conn


def _insert_portal_move(
    conn: sqlite3.Connection,
    *,
    name: str,
    announced: str,
    from_slug: str | None,
    to_slug: str | None,
    position: str = "WR",
) -> None:
    conn.execute(
        """
        insert into portal_moves
            (player_name, from_team_slug, to_team_slug,
             position, announced_date, summary)
        values (?, ?, ?, ?, ?, ?)
        """,
        (name, from_slug, to_slug, position, announced, f"{name} portal move"),
    )
    conn.commit()


def _insert_team(
    conn: sqlite3.Connection,
    *,
    slug: str,
    canonical: str | None = None,
    short: str | None = None,
    level: str = "FBS",
) -> int:
    cur = conn.execute(
        """
        insert into teams (slug, canonical_name, school_name, short_name, level_code, is_active)
        values (?, ?, ?, ?, ?, 1)
        """,
        (slug, canonical or slug.replace("-", " ").title(), canonical or slug, short, level),
    )
    conn.commit()
    return int(cur.lastrowid)


# ===========================================================================
# Smoke import
# ===========================================================================

def test_smoke_import_package_surface():
    """The package re-exports the expected public symbols (Part 4 of brief)."""
    from cfb_rankings import portal_heat
    assert hasattr(portal_heat, "ProgramChurn")
    assert hasattr(portal_heat, "PortalMover")
    assert hasattr(portal_heat, "fetch_program_churn")
    assert hasattr(portal_heat, "last_entry_age_days")
    assert hasattr(portal_heat, "render_index")
    assert hasattr(portal_heat, "render_all")
    assert hasattr(portal_heat, "compute_net_delta")


def test_smoke_import_renderer_module():
    """Direct module import path works (used by cli.py)."""
    from cfb_rankings.portal_heat import renderer as r
    assert callable(r.render_index)
    assert callable(r.render_all)


def test_smoke_import_data_module():
    """Direct data module import works (used by tests + future builders)."""
    from cfb_rankings.portal_heat import data as d
    assert callable(d.fetch_program_churn)
    assert callable(d.last_entry_age_days)


# ===========================================================================
# Part 1: portal_moves UPSERT
# ===========================================================================

class _DatabaseShim:
    """Minimal stand-in for cfb_rankings.db.Database backed by a single
    sqlite3 connection. Implements the small surface the upsert helper
    actually uses: ``execute(query, params_dict)``.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def execute(self, query: str, params=None) -> None:
        # The helper passes a dict of named params (`:name`) — sqlite3
        # supports those natively. ``_normalize_query`` in the real
        # Database wrapper is a no-op for queries already using ``:name``.
        self._conn.execute(query, params or {})
        self._conn.commit()


def test_upsert_inserts_new_row(tmp_path):
    """First call inserts; portal_moves row count goes from 0 to 1."""
    from cfb_rankings.wire.ingestion import _persist_portal_move

    conn = _fresh_db(tmp_path)
    db = _DatabaseShim(conn)

    _persist_portal_move(
        db,
        item={"firstName": "Aiden", "lastName": "Carter"},
        player_name="Aiden Carter",
        position="WR",
        transfer_date=datetime(2026, 5, 10, 12, 0),
        from_slug="florida",
        to_slug="alabama",
        from_team_id=None,
        to_team_id=None,
        origin_name="Florida",
        destination_name="Alabama",
    )

    rows = conn.execute("select * from portal_moves").fetchall()
    assert len(rows) == 1
    assert rows[0]["player_name"] == "Aiden Carter"
    assert rows[0]["from_team_slug"] == "florida"
    assert rows[0]["to_team_slug"] == "alabama"
    assert rows[0]["announced_date"] == "2026-05-10"
    assert rows[0]["position"] == "WR"
    # sources_json defaults populated.
    assert "CFBD" in rows[0]["sources_json"]


def test_upsert_dedups_on_same_key(tmp_path):
    """Re-inserting the same (name, date, from_slug) updates rather than
    duplicates. The renderer must NOT see two rows for one move."""
    from cfb_rankings.wire.ingestion import _persist_portal_move

    conn = _fresh_db(tmp_path)
    db = _DatabaseShim(conn)

    common = dict(
        player_name="Aiden Carter",
        position="WR",
        transfer_date=datetime(2026, 5, 10),
        from_slug="florida",
        from_team_id=None,
        to_team_id=None,
        origin_name="Florida",
    )

    # First insert -> Alabama
    _persist_portal_move(
        db, item={}, to_slug="alabama", destination_name="Alabama", **common,
    )
    # Second insert (same key) -> destination flipped to LSU. UPSERT must
    # update the existing row, not create a duplicate.
    _persist_portal_move(
        db, item={}, to_slug="lsu", destination_name="LSU", **common,
    )

    rows = conn.execute(
        "select * from portal_moves order by portal_move_id"
    ).fetchall()
    assert len(rows) == 1, "UPSERT should dedup, not duplicate"
    assert rows[0]["to_team_slug"] == "lsu", "destination flip should overwrite"


def test_upsert_distinct_when_from_slug_differs(tmp_path):
    """Two different transfers with same name+date but different origins
    produce two rows (the conflict key includes from_team_slug)."""
    from cfb_rankings.wire.ingestion import _persist_portal_move

    conn = _fresh_db(tmp_path)
    db = _DatabaseShim(conn)

    base = dict(
        player_name="John Doe",
        position="LB",
        transfer_date=datetime(2026, 5, 12),
        from_team_id=None,
        to_team_id=None,
        destination_name="USC",
        to_slug="usc",
    )
    _persist_portal_move(
        db, item={}, from_slug="oregon", origin_name="Oregon", **base,
    )
    _persist_portal_move(
        db, item={}, from_slug="utah", origin_name="Utah", **base,
    )

    rows = conn.execute("select * from portal_moves").fetchall()
    assert len(rows) == 2


# ===========================================================================
# Part 2: net-delta calculation
# ===========================================================================

def test_net_delta_count_only_when_no_stars(tmp_path):
    """Without player_recruiting_profiles, weight=1 for every move so
    net delta == entries - exits."""
    from cfb_rankings.portal_heat.data import fetch_program_churn

    conn = _fresh_db(tmp_path)
    today = date(2026, 5, 15)

    # Alabama: 3 in, 1 out -> net +2
    _insert_portal_move(conn, name="A", announced="2026-05-14",
                        from_slug="florida", to_slug="alabama")
    _insert_portal_move(conn, name="B", announced="2026-05-13",
                        from_slug="lsu", to_slug="alabama")
    _insert_portal_move(conn, name="C", announced="2026-05-12",
                        from_slug="auburn", to_slug="alabama")
    _insert_portal_move(conn, name="D", announced="2026-05-12",
                        from_slug="alabama", to_slug="texas")

    # Florida: 0 in, 1 out -> net -1
    # LSU:    0 in, 1 out -> net -1
    # Auburn: 0 in, 1 out -> net -1
    # Texas:  1 in, 0 out -> net +1

    churn = fetch_program_churn(
        conn, days=30,
        now=datetime.combine(today, datetime.min.time()),
    )
    by_slug = {c.program_slug: c for c in churn}
    assert by_slug["alabama"].entries == 3
    assert by_slug["alabama"].exits == 1
    assert by_slug["alabama"].net_delta == pytest.approx(2.0)
    assert by_slug["texas"].net_delta == pytest.approx(1.0)
    assert by_slug["florida"].net_delta == pytest.approx(-1.0)
    # Ranking: Alabama first (highest net).
    assert churn[0].program_slug == "alabama"


def test_net_delta_with_stars_weighting(tmp_path):
    """When player_recruiting_profiles has stars, the net delta uses the
    star weight curve (5★=8, 4★=4, 3★=2)."""
    from cfb_rankings.portal_heat.data import fetch_program_churn

    conn = _fresh_db(tmp_path)
    # Build players + player_recruiting_profiles tables — we want
    # _star_lookup to fire and pull weights.
    conn.executescript("""
        create table if not exists players (
          player_id integer primary key autoincrement,
          full_name text
        );
        create table if not exists player_recruiting_profiles (
          player_recruiting_profile_id integer primary key autoincrement,
          player_id integer,
          stars integer,
          season_year integer
        );
    """)
    conn.execute("insert into players (full_name) values (?)", ("Five Star Aiden",))
    conn.execute(
        "insert into player_recruiting_profiles (player_id, stars, season_year) values (?, ?, ?)",
        (1, 5, 2025),
    )
    conn.execute("insert into players (full_name) values (?)", ("Three Star Brett",))
    conn.execute(
        "insert into player_recruiting_profiles (player_id, stars, season_year) values (?, ?, ?)",
        (2, 3, 2025),
    )
    conn.commit()

    # Alabama gets a 5-star (weight 8). Texas gets a 3-star (weight 2).
    _insert_portal_move(conn, name="Five Star Aiden", announced="2026-05-14",
                        from_slug="florida", to_slug="alabama")
    _insert_portal_move(conn, name="Three Star Brett", announced="2026-05-14",
                        from_slug="florida", to_slug="texas")

    churn = fetch_program_churn(
        conn, days=14,
        now=datetime(2026, 5, 15),
    )
    by_slug = {c.program_slug: c for c in churn}
    # Alabama net = 8 (5-star in), Texas net = 2 (3-star in).
    assert by_slug["alabama"].net_delta == pytest.approx(8.0)
    assert by_slug["texas"].net_delta == pytest.approx(2.0)
    # Florida lost both, net = -10
    assert by_slug["florida"].net_delta == pytest.approx(-10.0)
    # Alabama outranks Texas.
    assert churn[0].program_slug == "alabama"


def test_window_filter_excludes_old_rows(tmp_path):
    """Rows older than `days` window are excluded from churn."""
    from cfb_rankings.portal_heat.data import fetch_program_churn

    conn = _fresh_db(tmp_path)
    # Within window
    _insert_portal_move(conn, name="Recent", announced="2026-05-10",
                        from_slug="ucla", to_slug="usc")
    # Outside window (35 days before now)
    _insert_portal_move(conn, name="Stale", announced="2026-04-10",
                        from_slug="ucla", to_slug="usc")

    churn = fetch_program_churn(
        conn, days=14, now=datetime(2026, 5, 15),
    )
    by_slug = {c.program_slug: c for c in churn}
    assert by_slug["usc"].entries == 1
    # Stale row excluded.
    movers = by_slug["usc"].top_movers
    assert all(m.player_name != "Stale" for m in movers)


def test_top_movers_limited_to_three(tmp_path):
    """Per spec, each program card shows at most 3 top movers."""
    from cfb_rankings.portal_heat.data import fetch_program_churn

    conn = _fresh_db(tmp_path)
    for i in range(7):
        _insert_portal_move(
            conn, name=f"Player {i}",
            announced=f"2026-05-{10+i:02d}",
            from_slug="lsu", to_slug="alabama",
        )

    churn = fetch_program_churn(conn, days=30, now=datetime(2026, 5, 20))
    by_slug = {c.program_slug: c for c in churn}
    assert len(by_slug["alabama"].top_movers) == 3


# ===========================================================================
# Part 3: empty-state rendering
# ===========================================================================

def test_render_empty_state_when_no_rows(tmp_path):
    """When portal_moves has zero rows in the window, render_index still
    produces a valid HTML file."""
    from cfb_rankings.portal_heat.renderer import render_index

    conn = _fresh_db(tmp_path)
    out_dir = tmp_path / "site_out" / "portal-heat"
    path = render_index(
        conn, output_dir=out_dir, days=14,
        now=datetime(2026, 5, 15),
    )
    assert path.exists()
    body = path.read_text(encoding="utf-8")
    assert "<html" in body.lower()
    assert "Portal Heat" in body or "Transfer Portal Heat" in body
    # Empty-state message present (the renderer's branch fires).
    assert "Portal cool" in body or "lights up" in body
    # No program cards rendered.
    assert 'class="card"' not in body


def test_render_empty_state_with_old_rows(tmp_path):
    """If portal_moves has rows but all outside the window, the renderer
    falls through to empty-state with an age message."""
    from cfb_rankings.portal_heat.renderer import render_index

    conn = _fresh_db(tmp_path)
    _insert_portal_move(conn, name="Old", announced="2026-01-01",
                        from_slug="x", to_slug="y")

    out_dir = tmp_path / "site_out" / "portal-heat"
    path = render_index(
        conn, output_dir=out_dir, days=14,
        now=datetime(2026, 5, 15),
    )
    body = path.read_text(encoding="utf-8")
    # Should reference days-ago via last_entry_age_days helper.
    assert "Portal cool" in body
    # And no actual cards.
    assert 'class="card"' not in body


def test_render_with_rows_includes_card(tmp_path):
    """When real rows exist, render produces a card per program."""
    from cfb_rankings.portal_heat.renderer import render_index

    conn = _fresh_db(tmp_path)
    _insert_portal_move(conn, name="Hot Take", announced="2026-05-14",
                        from_slug="lsu", to_slug="alabama")
    _insert_portal_move(conn, name="Other", announced="2026-05-13",
                        from_slug="florida", to_slug="alabama")

    out_dir = tmp_path / "site_out" / "portal-heat"
    path = render_index(
        conn, output_dir=out_dir, days=14,
        now=datetime(2026, 5, 15),
    )
    body = path.read_text(encoding="utf-8")
    assert 'class="card"' in body
    # Alabama (top entry program) appears.
    assert "alabama" in body.lower()
    # Top-mover name surfaces.
    assert "Hot Take" in body


def test_render_includes_days_to_kickoff_paren(tmp_path):
    """The hero header includes the days-to-kickoff parenthetical
    sourced from cfb_calendar.cfb_week_label."""
    from cfb_rankings.portal_heat.renderer import render_index

    conn = _fresh_db(tmp_path)
    out_dir = tmp_path / "site_out" / "portal-heat"
    path = render_index(
        conn, output_dir=out_dir, days=14,
        now=datetime(2026, 5, 15),
    )
    body = path.read_text(encoding="utf-8")
    # Aug 22, 2026 kickoff - May 15, 2026 = 99 days.
    assert "days to kickoff" in body


# ===========================================================================
# Part 4: helpers
# ===========================================================================

def test_last_entry_age_days_returns_none_when_empty(tmp_path):
    from cfb_rankings.portal_heat.data import last_entry_age_days
    conn = _fresh_db(tmp_path)
    assert last_entry_age_days(conn, now=datetime(2026, 5, 15)) is None


def test_last_entry_age_days_basic(tmp_path):
    from cfb_rankings.portal_heat.data import last_entry_age_days
    conn = _fresh_db(tmp_path)
    _insert_portal_move(conn, name="X", announced="2026-05-10",
                        from_slug="a", to_slug="b")
    age = last_entry_age_days(conn, now=datetime(2026, 5, 15))
    assert age == 5


def test_compute_net_delta_function():
    """The helper is a pure subtraction — verify directly."""
    from cfb_rankings.portal_heat.data import (
        ProgramChurn, compute_net_delta,
    )
    c = ProgramChurn(
        program_slug="x", program_display="X",
        weighted_entries=10.0, weighted_exits=4.0,
    )
    assert compute_net_delta(c) == pytest.approx(6.0)


def test_fetch_returns_empty_when_table_missing(tmp_path):
    """If the portal_moves table doesn't exist, fetch returns [] (not raise)."""
    from cfb_rankings.portal_heat.data import fetch_program_churn
    conn = sqlite3.connect(str(tmp_path / "no_schema.db"))
    conn.row_factory = sqlite3.Row
    churn = fetch_program_churn(conn, days=14, now=datetime(2026, 5, 15))
    assert churn == []
