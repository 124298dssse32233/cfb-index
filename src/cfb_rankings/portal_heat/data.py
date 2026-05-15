"""Data access for the Portal Heat Index.

Queries `portal_moves` for last-N-day churn per program, optionally
weighted by `player_recruiting_profiles.stars` when a matching name is
found. Falls back to raw count when no star rating exists.

Per DESIGN_AUDIT v5_4 §S3, the surface ranks programs by net Δ talent
(entries - exits). A "program" is anything with a `to_team_slug` or
`from_team_slug` value in portal_moves — we don't try to resolve all
FBS programs because the page is rank-25 by activity, not a full
directory.

Key concepts:
  - entries = moves where the program is the destination (to_team_slug)
  - exits   = moves where the program is the origin (from_team_slug)
  - net     = entries - exits (talent-weighted when possible)
  - top movers = up to 3 names per program, ordered entries-first then date

The functions accept the project's `Database` wrapper, a raw
`sqlite3.Connection`, or anything implementing `query_all`/`query_one`.
Tests pass raw connections; production passes `Database`.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Protocol

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortalMover:
    """A single portal move surfaced inside a program card."""

    player_name: str
    position: str | None
    announced_date: str  # ISO date string (YYYY-MM-DD) for cross-platform sort
    direction: str       # 'in' if the program is the destination, 'out' otherwise
    counterpart_slug: str | None  # the other side's slug (from_slug if in, to_slug if out)
    counterpart_display: str | None
    stars: int | None    # 0-5 when known from player_recruiting_profiles, else None


@dataclass
class ProgramChurn:
    """Aggregate churn for one program over the configured window."""

    program_slug: str
    program_display: str
    primary_color: str | None = None
    secondary_color: str | None = None
    entries: int = 0
    exits: int = 0
    weighted_entries: float = 0.0
    weighted_exits: float = 0.0
    net_delta: float = 0.0
    top_movers: list[PortalMover] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DB tolerance — accept either project's Database wrapper or a raw connection.
# ---------------------------------------------------------------------------

class _QueryAllProto(Protocol):
    def query_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...


def _query_all(db: Any, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run a query against either Database or sqlite3.Connection."""
    if hasattr(db, "query_all"):
        return db.query_all(query, params or {})
    # Raw sqlite3 connection path. Convert ``:name`` → ``:name`` (sqlite3
    # already supports that), set row_factory if missing, and return dicts.
    conn: sqlite3.Connection = db
    if conn.row_factory is None:
        conn.row_factory = sqlite3.Row
    cur = conn.execute(query, params or {})
    return [dict(r) for r in cur.fetchall()]


def _table_exists(db: Any, table: str) -> bool:
    rows = _query_all(
        db,
        "select 1 from sqlite_master where type='table' and name = :n",
        {"n": table},
    )
    return bool(rows)


# ---------------------------------------------------------------------------
# Star-weighting strategy.
# ---------------------------------------------------------------------------
#
# When player_recruiting_profiles has a matching row keyed on case-folded
# player full_name (joined via the `players` table), we treat the recruit
# stars as the move's talent weight using a geometric curve:
#
#   5★ -> 8.0
#   4★ -> 4.0
#   3★ -> 2.0
#   2★ -> 1.0
#   else / unknown -> 1.0
#
# This matches the canon used in `team_pages/render` for recruiting
# weight without depending on it (avoids the heavy import). Unknown
# always defaults to 1.0 so empty-stars data degrades to raw counts.

_STAR_WEIGHT = {5: 8.0, 4: 4.0, 3: 2.0, 2: 1.0, 1: 1.0, 0: 1.0}


def _weight(stars: int | None) -> float:
    if stars is None:
        return 1.0
    try:
        return _STAR_WEIGHT.get(int(stars), 1.0)
    except (TypeError, ValueError):
        return 1.0


# ---------------------------------------------------------------------------
# Star lookup — best-effort join through `players` table.
# ---------------------------------------------------------------------------

def _star_lookup(db: Any) -> dict[str, int]:
    """Build a {lower(name) -> stars} dict from player_recruiting_profiles.

    Only counts the most-recent profile per player; null/zero stars are
    excluded. Returns {} if either source table is missing — keeps the
    renderer DB-tolerant when running on a minimal test schema.
    """
    if not (_table_exists(db, "player_recruiting_profiles") and _table_exists(db, "players")):
        return {}
    try:
        rows = _query_all(
            db,
            """
            select lower(p.full_name) as name_key, max(pp.stars) as stars
            from player_recruiting_profiles pp
            join players p on p.player_id = pp.player_id
            where pp.stars is not null and pp.stars > 0
              and p.full_name is not null and trim(p.full_name) <> ''
            group by lower(p.full_name)
            """,
        )
    except sqlite3.Error as exc:
        log.debug("portal_heat.data: star_lookup failed (%s) — falling back to raw count", exc)
        return {}
    return {r["name_key"]: int(r["stars"]) for r in rows if r.get("stars") is not None}


# ---------------------------------------------------------------------------
# Team-brand color lookup.
# ---------------------------------------------------------------------------

def _color_lookup(db: Any) -> dict[str, tuple[str | None, str | None]]:
    """Return {slug -> (primary_hex, secondary_hex)} for FBS programs.

    Sources colors from team_brand_assets when available
    (asset_kind='color', variant='primary'|'secondary'). Empty dict if
    the table doesn't exist or contains no color rows.
    """
    if not _table_exists(db, "team_brand_assets") or not _table_exists(db, "teams"):
        return {}
    try:
        rows = _query_all(
            db,
            """
            select t.slug, tba.variant, tba.local_path, tba.source_url
            from team_brand_assets tba
            join teams t on t.team_id = tba.team_id
            where tba.asset_kind = 'color' and tba.is_active = 1
            """,
        )
    except sqlite3.Error as exc:
        log.debug("portal_heat.data: color_lookup failed (%s)", exc)
        return {}
    out: dict[str, tuple[str | None, str | None]] = {}
    for r in rows:
        slug = r.get("slug")
        if not slug:
            continue
        # color is encoded in local_path or source_url depending on import path
        hex_val = (r.get("local_path") or r.get("source_url") or "").strip() or None
        primary, secondary = out.get(slug, (None, None))
        if (r.get("variant") or "").lower() == "primary":
            primary = hex_val
        elif (r.get("variant") or "").lower() == "secondary":
            secondary = hex_val
        out[slug] = (primary, secondary)
    return out


# ---------------------------------------------------------------------------
# Display-name lookup — fall back gracefully when teams table absent.
# ---------------------------------------------------------------------------

def _display_lookup(db: Any) -> dict[str, str]:
    if not _table_exists(db, "teams"):
        return {}
    try:
        rows = _query_all(
            db,
            "select slug, coalesce(short_name, canonical_name) as display from teams where slug is not null",
        )
    except sqlite3.Error:
        return {}
    return {r["slug"]: r["display"] or r["slug"] for r in rows if r.get("slug")}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def last_entry_age_days(db: Any, *, now: datetime | None = None) -> int | None:
    """Return days since the most-recent portal_moves row, or None when empty.

    Used to render the empty-state ("Portal cool — last entry N days ago")
    when no rows fall within the window.
    """
    if not _table_exists(db, "portal_moves"):
        return None
    rows = _query_all(
        db,
        "select max(announced_date) as last_d from portal_moves",
    )
    if not rows or not rows[0].get("last_d"):
        return None
    try:
        last = datetime.fromisoformat(str(rows[0]["last_d"])[:10])
    except ValueError:
        return None
    now = now or datetime.utcnow()
    return max(0, (now.date() - last.date()).days)


def compute_net_delta(churn: ProgramChurn) -> float:
    """Net Δ talent — talent-weighted entries minus exits."""
    return churn.weighted_entries - churn.weighted_exits


def fetch_program_churn(
    db: Any,
    *,
    days: int = 14,
    limit: int = 25,
    now: datetime | None = None,
) -> list[ProgramChurn]:
    """Return Top-N programs by net Δ talent over the last `days` window.

    Empty list when portal_moves has no rows in the window (the renderer
    branches to its empty-state in that case).

    Args:
        db:    Database wrapper or sqlite3.Connection.
        days:  Lookback window in days. Default 14.
        limit: Maximum programs to return. Default 25.
        now:   Override "today" for tests.
    """
    if not _table_exists(db, "portal_moves"):
        return []
    now = now or datetime.utcnow()
    cutoff = now.date().isoformat()

    rows = _query_all(
        db,
        """
        select player_name, position,
               from_team_slug, to_team_slug,
               announced_date
        from portal_moves
        where announced_date >= date(:today, :since)
        order by announced_date desc, portal_move_id desc
        """,
        {"today": cutoff, "since": f"-{int(days)} days"},
    )
    if not rows:
        return []

    stars_by_name = _star_lookup(db)
    colors = _color_lookup(db)
    display = _display_lookup(db)

    per_program: dict[str, ProgramChurn] = {}

    def _bucket(slug: str) -> ProgramChurn:
        if slug not in per_program:
            primary, secondary = colors.get(slug, (None, None))
            per_program[slug] = ProgramChurn(
                program_slug=slug,
                program_display=display.get(slug) or _slug_to_display(slug),
                primary_color=primary,
                secondary_color=secondary,
            )
        return per_program[slug]

    for r in rows:
        name = (r.get("player_name") or "").strip()
        position = r.get("position")
        date_str = r.get("announced_date") or ""
        from_slug = (r.get("from_team_slug") or "").strip() or None
        to_slug = (r.get("to_team_slug") or "").strip() or None
        stars = stars_by_name.get(name.lower()) if name else None
        weight = _weight(stars)

        # Destination program: counts as an entry.
        if to_slug:
            prog = _bucket(to_slug)
            prog.entries += 1
            prog.weighted_entries += weight
            if len(prog.top_movers) < 6:
                prog.top_movers.append(PortalMover(
                    player_name=name or "Player",
                    position=position,
                    announced_date=str(date_str)[:10],
                    direction="in",
                    counterpart_slug=from_slug,
                    counterpart_display=(display.get(from_slug) if from_slug else None),
                    stars=stars,
                ))
        # Origin program: counts as an exit.
        if from_slug:
            prog = _bucket(from_slug)
            prog.exits += 1
            prog.weighted_exits += weight
            if len(prog.top_movers) < 6:
                prog.top_movers.append(PortalMover(
                    player_name=name or "Player",
                    position=position,
                    announced_date=str(date_str)[:10],
                    direction="out",
                    counterpart_slug=to_slug,
                    counterpart_display=(display.get(to_slug) if to_slug else None),
                    stars=stars,
                ))

    # Compute net + trim top movers to 3 (entries first, then date desc).
    for prog in per_program.values():
        prog.net_delta = compute_net_delta(prog)
        prog.top_movers = sorted(
            prog.top_movers,
            key=lambda m: (
                0 if m.direction == "in" else 1,
                # Negate date so newest sorts first within direction
                # without depending on platform-specific date parsing.
                -_iso_date_key(m.announced_date),
                -(m.stars or 0),
            ),
        )[:3]

    ranked = sorted(
        per_program.values(),
        key=lambda p: (-p.net_delta, -p.weighted_entries, -p.entries, p.program_slug),
    )
    return ranked[: int(limit)]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _iso_date_key(iso_str: str) -> int:
    """Sortable int key from a YYYY-MM-DD string. Returns 0 on parse error."""
    try:
        # Strip dashes -> YYYYMMDD -> int. Safe & deterministic, no datetime.
        return int(iso_str[:10].replace("-", ""))
    except (ValueError, AttributeError, TypeError):
        return 0


def _slug_to_display(slug: str) -> str:
    """Best-effort prettifier when the teams table didn't supply a name."""
    return " ".join(part.capitalize() for part in (slug or "").split("-")) or slug


__all__ = [
    "ProgramChurn",
    "PortalMover",
    "compute_net_delta",
    "fetch_program_churn",
    "last_entry_age_days",
]
