"""Saturday Strip — mobile-only sticky-at-top primitive.

Sprint v5-7.6. Spec H.1 in IMPLEMENTATION_PLAN_v3_iteration.md. Mockup:
``docs/mockups/mockup_06_saturday_strip.html``.

The strip is 44px tall (56px expanded), pins to the top of the viewport
on mobile only (the desktop site uses full site nav), and renders one
of two states:

* **In-season** — live games scrolling horizontally. The current focus
  snaps leftmost. Each row carries the live indicator (pulsing red dot
  + LIVE chip) or a FINAL chip with optional UPSET tag.
* **Off-season** — countdown to kickoff + 4-5 recent portal markers
  (5-star commit, transfer in/out, camp-open marker, today-in-history).

The state shape is JSON-serializable so the same data can drive:
  1. Server-side render of the strip HTML (this module's
     ``render_strip_html``)
  2. ``/assets/saturday_strip.json`` payload consumed by the
     client-side auto-refresh tick (every 30s during games, 5 min for
     upcoming games, 1 hour off-season)
  3. A11y test that the strip's content is announceable as a list

This module does NOT do CFBD live-data fetching — that's the v5-7.6
pipeline's job. ``build_strip_state(db, today)`` reads from already-
populated tables (``games``, ``games_live``, ``conversation_documents``)
and returns the state dataclass.

Public API:
  StripState  — dataclass; the whole strip's data + render hints
  StripGame   — one game row in the in-season strip
  StripChip   — one off-season marker chip
  build_strip_state(db, today=date.today()) -> StripState
  render_strip_html(state: StripState) -> str
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import logging as _log
import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from ..common.cfb_calendar import (
    days_to_kickoff,
    human_phase_label,
    is_in_season,
)

if TYPE_CHECKING:
    from ..db import Database


log = _log.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

GameStatus = Literal["live", "final", "upcoming"]


@dataclass(frozen=True)
class StripGame:
    """One row in the in-season strip.

    Carries everything the render call needs — the renderer is dumb. The
    builder is responsible for sourcing live data + producing this row.
    """
    away_abbr: str
    home_abbr: str
    status: GameStatus
    away_points: int | None = None
    home_points: int | None = None
    period_clock: str | None = None   # "2Q · 4:32" when live
    kickoff_local: str | None = None  # "7:30 ET" when upcoming
    channel: str | None = None        # "CBS" / "ESPN" when upcoming
    upset_flag: bool = False
    href: str | None = None           # /programs/<slug>.html tap target


@dataclass(frozen=True)
class StripChip:
    """One off-season marker chip."""
    label: str                        # uppercase chip label, e.g. "★ COMMIT"
    body: str                         # e.g. "5★ QB Smith → TEX"
    kind: Literal["commit", "portal", "camp", "history", "draft", "other"] = "other"
    href: str | None = None


@dataclass(frozen=True)
class StripState:
    """The whole strip's state. JSON-serializable via dataclasses.asdict."""
    mode: Literal["in_season", "off_season"]
    generated_at_utc: str
    refresh_seconds: int              # client-side tick interval
    # In-season fields
    games: list[StripGame] = field(default_factory=list)
    # Off-season fields
    days_to_kickoff: int | None = None
    phase_label: str = ""
    chips: list[StripChip] = field(default_factory=list)
    # Common
    schema_version: str = "1.0"


# ---------------------------------------------------------------------------
# State builder
# ---------------------------------------------------------------------------

def build_strip_state(
    db: "Database | None" = None,
    *,
    today: _dt.date | None = None,
    season: int | None = None,
) -> StripState:
    """Build the strip state for ``today``.

    Chooses in-season vs off-season via ``cfb_calendar.is_in_season``.
    For in-season days the builder queries:
      - ``games_live`` for currently-playing games
      - ``games`` for FINAL games today + UPCOMING games today

    For off-season days the builder:
      - Computes ``days_to_kickoff(season)``
      - Pulls 4 chips from recent portal/commit/draft tables
      - Adds a today-in-history chip if one is available

    Empty state: when no live data exists (early-morning in-season, no
    games today), returns mode=in_season with empty ``games`` and the
    auto-refresh interval bumped to 5 min.
    """
    today = today or _dt.date.today()
    now_utc = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = _resolve_conn(db)
    in_season = is_in_season(today, conn)

    if in_season:
        games = _fetch_in_season_games(conn, today) if conn is not None else []
        # Faster tick when there's an actively playing game
        any_live = any(g.status == "live" for g in games)
        refresh = 30 if any_live else (300 if games else 600)
        return StripState(
            mode="in_season",
            generated_at_utc=now_utc,
            refresh_seconds=refresh,
            games=games,
        )
    # off-season
    season_year = season or (today.year if today.month >= 2 else today.year - 1)
    days = days_to_kickoff(today, season_year, conn) if conn is not None else None
    chips = _fetch_off_season_chips(conn, today) if conn is not None else []
    phase = (
        human_phase_label(today, conn) if conn is not None
        else "Off-season"
    )
    return StripState(
        mode="off_season",
        generated_at_utc=now_utc,
        refresh_seconds=3600,
        days_to_kickoff=days,
        phase_label=phase,
        chips=chips,
    )


def _resolve_conn(db: "Database | None") -> sqlite3.Connection | None:
    """Extract a raw sqlite3.Connection from the Database wrapper, if any."""
    if db is None:
        return None
    # The Database class manages a single connection at ._conn typically
    for attr in ("_conn", "conn", "connection"):
        c = getattr(db, attr, None)
        if isinstance(c, sqlite3.Connection):
            return c
    return None


def _fetch_in_season_games(
    conn: sqlite3.Connection,
    today: _dt.date,
) -> list[StripGame]:
    """Return live + final + upcoming games for ``today`` from the DB.

    Defensive: any of these tables may be empty in offseason or in
    partial DB snapshots. Returns [] on schema/data absence.
    """
    games: list[StripGame] = []
    try:
        cur = conn.execute(
            """
            SELECT
                gl.game_id, gl.status, gl.period, gl.clock,
                gl.home_points, gl.away_points,
                ht.short_name AS home_abbr, at.short_name AS away_abbr,
                ht.slug AS home_slug, at.slug AS away_slug
            FROM games_live gl
            JOIN games g ON gl.game_id = g.game_id
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE DATE(g.start_time_utc) = ?
              AND gl.status IN ('in_progress', 'live')
            ORDER BY gl.last_updated_utc DESC
            """,
            (today.isoformat(),),
        )
        for row in cur.fetchall():
            games.append(StripGame(
                away_abbr=row["away_abbr"] or "",
                home_abbr=row["home_abbr"] or "",
                status="live",
                away_points=row["away_points"],
                home_points=row["home_points"],
                period_clock=f"{row['period']}Q · {row['clock']}" if row["period"] and row["clock"] else None,
                href=f"/programs/{row['home_slug']}.html" if row["home_slug"] else None,
            ))
    except sqlite3.OperationalError:
        # games_live may not exist yet — graceful
        pass

    try:
        cur = conn.execute(
            """
            SELECT
                g.game_id, g.status,
                g.home_points, g.away_points,
                ht.short_name AS home_abbr, at.short_name AS away_abbr,
                ht.slug AS home_slug,
                strftime('%H:%M', g.start_time_utc) AS kickoff_utc
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE DATE(g.start_time_utc) = ?
            ORDER BY g.start_time_utc
            """,
            (today.isoformat(),),
        )
        for row in cur.fetchall():
            status = row["status"]
            if status in ("final", "completed"):
                # Crude upset flag: away_points > home_points (TODO: poll lines)
                upset = (row["away_points"] or 0) > (row["home_points"] or 0)
                games.append(StripGame(
                    away_abbr=row["away_abbr"] or "",
                    home_abbr=row["home_abbr"] or "",
                    status="final",
                    away_points=row["away_points"],
                    home_points=row["home_points"],
                    upset_flag=upset,
                    href=f"/programs/{row['home_slug']}.html" if row["home_slug"] else None,
                ))
            elif status in ("scheduled", "upcoming"):
                games.append(StripGame(
                    away_abbr=row["away_abbr"] or "",
                    home_abbr=row["home_abbr"] or "",
                    status="upcoming",
                    kickoff_local=row["kickoff_utc"],
                    href=f"/programs/{row['home_slug']}.html" if row["home_slug"] else None,
                ))
    except sqlite3.OperationalError:
        pass

    return games


def _fetch_off_season_chips(
    conn: sqlite3.Connection,
    today: _dt.date,
) -> list[StripChip]:
    """Return up to 5 off-season marker chips from recent ingest tables.

    Pulls from:
      - ``conversation_documents`` recent commit/transfer signal mentions
      - hard-coded camp-opens-Aug-3 chip when within 30 days
      - ``today-in-history`` chip if a notable historical event today

    All chips are best-effort; missing data → fewer chips, not failure.
    """
    chips: list[StripChip] = []

    # Camp-open marker (universal — Aug 3 anchor; adjust per cfb_calendar)
    camp_open = _dt.date(today.year, 8, 3)
    if camp_open >= today and (camp_open - today).days <= 30:
        chips.append(StripChip(
            label="CAMP",
            body=f"Opens {camp_open.strftime('%b %-d')}" if hasattr(_dt, 'strftime') else f"Opens Aug 3",
            kind="camp",
        ))

    # Best-effort recent commit/portal signal from conversation_documents
    try:
        cur = conn.execute(
            """
            SELECT title_text
            FROM conversation_documents
            WHERE (title_text LIKE '%commit%' OR title_text LIKE '%transfer%'
                   OR title_text LIKE '%portal%')
              AND COALESCE(external_created_at_utc, collected_at_utc)
                  > datetime('now', '-7 days')
            ORDER BY COALESCE(external_created_at_utc, collected_at_utc) DESC
            LIMIT 3
            """
        )
        for row in cur.fetchall():
            title = (row["title_text"] or "")[:60]
            if not title:
                continue
            kind: Literal["commit", "portal", "camp", "history", "draft", "other"]
            if "commit" in title.lower():
                kind = "commit"
                label = "★ COMMIT"
            elif "portal" in title.lower() or "transfer" in title.lower():
                kind = "portal"
                label = "PORTAL"
            else:
                kind = "other"
                label = "WIRE"
            chips.append(StripChip(label=label, body=title, kind=kind))
            if len(chips) >= 4:
                break
    except sqlite3.OperationalError:
        pass

    return chips


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

def render_strip_html(state: StripState) -> str:
    """Render the strip HTML matching mockup_06's lock structure.

    Returns the inner content (no <html>/<head>). Wraps in
    <header class="strip" data-strip-mode="..."> for the in-season state
    and <header class="strip-off" data-strip-mode="..."> for off-season.
    """
    if state.mode == "in_season":
        return _render_in_season(state)
    return _render_off_season(state)


def _render_in_season(state: StripState) -> str:
    if not state.games:
        # Empty state — common for in-season weekdays
        return (
            '<header class="strip" data-strip-mode="in_season" '
            f'data-refresh-seconds="{state.refresh_seconds}" '
            'aria-label="Saturday strip — no games today">'
            '<div class="strip__row"><span class="strip__empty">'
            'No games today.</span></div>'
            '</header>'
        )

    rows: list[str] = []
    for g in state.games:
        if g.status == "live":
            rows.append(_render_live_row(g))
        elif g.status == "final":
            rows.append(_render_final_row(g))
        else:
            rows.append(_render_upcoming_row(g))
    return (
        f'<header class="strip" data-strip-mode="in_season" '
        f'data-refresh-seconds="{state.refresh_seconds}" '
        f'data-generated-at="{_html.escape(state.generated_at_utc)}" '
        f'aria-label="Saturday strip — live games">'
        f'{"".join(rows)}'
        f'</header>'
    )


def _render_live_row(g: StripGame) -> str:
    away_pts = "" if g.away_points is None else str(g.away_points)
    home_pts = "" if g.home_points is None else str(g.home_points)
    clock = _html.escape(g.period_clock or "")
    return (
        '<div class="strip__row">'
        '<span class="live-dot" aria-hidden="true"></span>'
        '<span class="live-tag">LIVE</span>'
        f'<span class="strip__matchup">'
        f'<span>{_html.escape(g.away_abbr)}</span>'
        f'<span class="pts">{away_pts}</span>'
        f'<span aria-hidden="true">—</span>'
        f'<span>{_html.escape(g.home_abbr)}</span>'
        f'<span class="pts">{home_pts}</span>'
        '</span>'
        f'<span class="strip__clock">{clock}</span>'
        '</div>'
    )


def _render_final_row(g: StripGame) -> str:
    away_pts = "" if g.away_points is None else str(g.away_points)
    home_pts = "" if g.home_points is None else str(g.home_points)
    upset = '<span class="strip__upset">UPSET</span>' if g.upset_flag else ''
    return (
        '<div class="strip__row">'
        '<span class="strip__final">FINAL</span>'
        f'<span class="strip__matchup">'
        f'<span>{_html.escape(g.away_abbr)}</span>'
        f'<span class="pts">{away_pts}</span>'
        f'<span aria-hidden="true">—</span>'
        f'<span>{_html.escape(g.home_abbr)}</span>'
        f'<span class="pts">{home_pts}</span>'
        '</span>'
        f'{upset}'
        '</div>'
    )


def _render_upcoming_row(g: StripGame) -> str:
    kickoff = _html.escape(g.kickoff_local or "")
    channel = (
        f'<span class="strip__channel">{_html.escape(g.channel)}</span>'
        if g.channel else ''
    )
    return (
        '<div class="strip__row">'
        f'<span class="strip__upcoming-time">{kickoff}</span>'
        f'<span class="strip__matchup">'
        f'<span>{_html.escape(g.away_abbr)}</span>'
        f'<span aria-hidden="true">—</span>'
        f'<span>{_html.escape(g.home_abbr)}</span>'
        '</span>'
        f'{channel}'
        '</div>'
    )


def _render_off_season(state: StripState) -> str:
    items: list[str] = []
    if state.days_to_kickoff is not None:
        items.append(
            '<div class="strip-off__item">'
            f'<span class="strip-off__num">{state.days_to_kickoff}</span>'
            '<span class="strip-off__label">DAYS TO KICKOFF</span>'
            '</div>'
        )
    for chip in state.chips:
        items.append(
            '<div class="strip-off__item">'
            f'<span class="strip-off__chip">{_html.escape(chip.label)}</span>'
            f'<span>{_html.escape(chip.body)}</span>'
            '</div>'
        )
    return (
        f'<header class="strip-off" data-strip-mode="off_season" '
        f'data-refresh-seconds="{state.refresh_seconds}" '
        f'data-generated-at="{_html.escape(state.generated_at_utc)}" '
        f'aria-label="Off-season strip">'
        f'{"".join(items)}'
        f'</header>'
    )


__all__ = [
    "StripState",
    "StripGame",
    "StripChip",
    "build_strip_state",
    "render_strip_html",
]
