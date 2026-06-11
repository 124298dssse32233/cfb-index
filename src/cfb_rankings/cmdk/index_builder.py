"""Build the Cmd-K search index JSON.

Each `index_<category>` function returns a list of SearchItem records.
``build_search_index`` aggregates all six. ``write_search_index`` is
the build-time entry point — emits ``output/site/search-index.json``.

Player indexing is deliberately bounded: ~14k players is plenty; we
don't include the full 130k roster history. The bound is enforced
via the ``players_max`` argument (default 15000).

All functions degrade gracefully on missing tables — sqlite3.OperationalError
becomes an empty list. This lets the index builder run on partially-
migrated databases without crashing the site build.
"""

from __future__ import annotations

import json
import logging as _log
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from .types import SearchItem

if TYPE_CHECKING:
    from ..db import Database


log = _log.getLogger(__name__)


# ---------------------------------------------------------------------------
# Teams + profiles
# ---------------------------------------------------------------------------

def index_teams(
    db: "Database",
    *,
    profiled_slugs: frozenset[str] | None = None,
) -> list[SearchItem]:
    """Index every team_id with a slug.

    Tier mapping:
      1 → profiled (slug in profiled_slugs)
      2 → FBS (level_code = 'FBS')
      3 → FCS
      4 → DII / DIII / other
    """
    profiled = profiled_slugs or frozenset()
    try:
        rows = db.query_all(
            """
            SELECT t.team_id, t.slug, t.school_name, t.short_name,
                   t.level_code, c.conference_short_name AS conf_short
            FROM teams t
            LEFT JOIN conferences c
              ON c.conference_id = t.current_conference_id
            WHERE t.slug IS NOT NULL AND t.slug != ''
              AND (t.is_active IS NULL OR t.is_active = 1)
            ORDER BY t.school_name
            """,
        )
    except sqlite3.OperationalError as e:
        log.warning("index_teams: %s", e)
        return []
    items: list[SearchItem] = []
    for r in rows:
        slug = r["slug"]
        if slug in profiled:
            continue  # profiled teams go through index_profiles with tier 1
        name = r["school_name"] or r["short_name"] or slug
        level = (r["level_code"] or "").upper()
        if level == "FBS":
            tier = 2
        elif level == "FCS":
            tier = 3
        else:
            tier = 4
        conf = r["conf_short"] or ""
        subtitle = f"{level}{' · ' + conf if conf else ''}".strip(" · ") or "Team"
        items.append(SearchItem(
            kind="team",
            title=name,
            url=f"/teams/{slug}.html",
            subtitle=subtitle,
            tier=tier,
        ))
    return items


def index_profiles(
    db: "Database",
    *,
    profiled_slugs: frozenset[str] | None = None,
) -> list[SearchItem]:
    """Index every profiled team (slug in profiled_slugs).

    Always tier 1. ``profiled_slugs`` defaults to discovering from disk
    (the same list ``reporting.py`` uses).
    """
    if profiled_slugs is None:
        profiled_slugs = _discover_profiled_slugs()
    if not profiled_slugs:
        return []
    placeholders = ",".join("?" * len(profiled_slugs))
    try:
        rows = db.query_all(
            f"""
            SELECT slug, school_name, short_name
            FROM teams
            WHERE slug IN ({placeholders})
            ORDER BY school_name
            """,
            tuple(profiled_slugs),
        )
    except sqlite3.OperationalError as e:
        log.warning("index_profiles: %s", e)
        return []
    items: list[SearchItem] = []
    for r in rows:
        slug = r["slug"]
        name = r["school_name"] or r["short_name"] or slug
        items.append(SearchItem(
            kind="profile",
            title=name,
            url=f"/teams/{slug}.html",
            subtitle="Profiled program",
            tier=1,
        ))
    return items


def _discover_profiled_slugs() -> frozenset[str]:
    """Discover profile slugs from disk."""
    try:
        profiles_dir = Path(__file__).resolve().parents[3] / "profiles"
        if not profiles_dir.is_dir():
            return frozenset()
        return frozenset(p.stem for p in profiles_dir.glob("*.md"))
    except Exception:
        return frozenset()


# ---------------------------------------------------------------------------
# Players (bounded — current-season rosters or top-N by signal)
# ---------------------------------------------------------------------------

def index_players(
    db: "Database",
    *,
    players_max: int = 15000,
    season_year: int | None = None,
) -> list[SearchItem]:
    """Index a bounded subset of players.

    Selection priority:
      1. Players with a row in player_season_stats for season_year
         (most recent season with stats by default)
      2. Players with any active roster row

    We cap at ``players_max`` (default 15000) to keep the JSON payload
    under ~1MB minified.
    """
    try:
        if season_year is None:
            # Find the latest season with player_season_stats rows
            row = db.query_one(
                "SELECT MAX(season_year) AS y FROM player_season_stats"
            )
            season_year = int(row["y"]) if row and row["y"] else None
    except sqlite3.OperationalError:
        season_year = None
    if season_year is None:
        return []
    try:
        rows = db.query_all(
            """
            SELECT DISTINCT p.player_id, p.full_name, p.first_name,
                   p.last_name, p.position, p.home_state,
                   t.slug AS team_slug, t.short_name AS team_short
            FROM player_season_stats pss
            JOIN players p ON p.player_id = pss.player_id
            LEFT JOIN teams t ON t.team_id = pss.team_id
            WHERE pss.season_year = ?
              AND p.full_name IS NOT NULL AND p.full_name != ''
            ORDER BY pss.season_year DESC, p.full_name
            LIMIT ?
            """,
            (season_year, players_max),
        )
    except sqlite3.OperationalError as e:
        log.warning("index_players: %s", e)
        return []
    items: list[SearchItem] = []
    for r in rows:
        name = r["full_name"]
        if not name:
            continue
        position = (r["position"] or "").upper()
        team = r["team_short"] or ""
        subtitle_parts = [p for p in (position, team) if p]
        subtitle = " · ".join(subtitle_parts)
        items.append(SearchItem(
            kind="player",
            title=name,
            url=f"/players/{r['player_id']}.html",
            subtitle=subtitle,
            tier=5,
        ))
    return items


# ---------------------------------------------------------------------------
# Editions + mailbag
# ---------------------------------------------------------------------------

def index_editions(db: "Database") -> list[SearchItem]:
    """Index editions table (Edition tentpole pieces)."""
    try:
        rows = db.query_all(
            """
            SELECT edition_slug, edition_number, volume, publish_date,
                   theme_title
            FROM editions
            WHERE status IS NULL OR status NOT IN ('draft', 'unpublished')
            ORDER BY publish_date DESC, edition_number DESC
            """,
        )
    except sqlite3.OperationalError as e:
        log.warning("index_editions: %s", e)
        return []
    items: list[SearchItem] = []
    for r in rows:
        slug = r["edition_slug"]
        theme = r["theme_title"] or f"Edition {r['edition_number'] or slug}"
        date = r["publish_date"] or ""
        items.append(SearchItem(
            kind="edition",
            title=theme,
            url=f"/editions/{slug}/",
            subtitle=f"Edition · {date}".strip(" ·"),
            tier=2,
        ))
    return items


def index_mailbag(db: "Database") -> list[SearchItem]:
    """Index mailbag_editions (separate from edition tentpoles)."""
    try:
        rows = db.query_all(
            """
            SELECT edition_slug, publish_date, status
            FROM mailbag_editions
            WHERE status IS NULL OR status NOT IN ('draft', 'unpublished')
            ORDER BY publish_date DESC
            """,
        )
    except sqlite3.OperationalError as e:
        log.warning("index_mailbag: %s", e)
        return []
    items: list[SearchItem] = []
    for r in rows:
        slug = r["edition_slug"]
        date = r["publish_date"] or ""
        items.append(SearchItem(
            kind="mailbag",
            title=f"Mailbag — {slug}",
            url=f"/mailbag/{slug}/",
            subtitle=f"Reader Q&A · {date}".strip(" ·"),
            tier=3,
        ))
    return items


# ---------------------------------------------------------------------------
# Conferences
# ---------------------------------------------------------------------------

# Conference standalone-name normalization + page-slug derivation mirror
# reporting.py::_clean_conference_name / ::_conference_slug — keep in sync.
# WHY (WP-0.2b, 2026-06-11): conference detail pages are named
# "{level}-{kebab(name)}.html" (e.g. "fbs-sec.html"), NOT
# "{conference_slug}.html". In production conferences.conference_slug is NULL
# for every row, and the previous SELECT also referenced display_name /
# member_count columns that do not exist — so the query raised
# OperationalError and conferences were silently dropped from search entirely.
# We now read only real columns, derive the page slug the renderer uses, and
# (when a site_dir is known) emit only conferences whose page file exists so
# search never links to a 404.
_CONF_STANDALONE = {
    "FBS": "FBS Independents", "FCS": "FCS Independents",
    "DII": "Independent DII", "DIII": "Independent DIII",
}


def _conf_clean_name(value: str) -> str:
    v = (value or "").strip()
    return _CONF_STANDALONE.get(v, v)


def _conf_page_slug(conference_name: str, level_code: str) -> str:
    raw = f"{level_code} {conference_name}".lower().strip()
    raw = raw.replace("&", " and ").replace("'", "").replace(".", "")
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-") or f"{level_code.lower()}-conference"


def index_conferences(
    db: "Database",
    *,
    site_dir: str | Path | None = None,
) -> list[SearchItem]:
    """Index active conferences as search items.

    Resolves each conference to its real detail-page slug
    ("{level}-{kebab(name)}", e.g. "fbs-sec"). A populated ``conference_slug``
    column is honored first (legacy/test path). When ``site_dir`` is provided
    the candidate page must exist on disk or the entry is skipped — this keeps
    dead links out of the index even as conference coverage changes.
    """
    try:
        rows = db.query_all(
            """
            SELECT conference_id, conference_name, conference_short_name,
                   conference_slug, level_code
            FROM conferences
            WHERE is_active IS NULL OR is_active = 1
            ORDER BY conference_name
            """,
        )
    except sqlite3.OperationalError as e:
        log.warning("index_conferences: %s", e)
        return []

    conf_dir = (Path(site_dir) / "conferences") if site_dir is not None else None
    items: list[SearchItem] = []
    seen: set[str] = set()
    for r in rows:
        name = _conf_clean_name(r["conference_name"] or r["conference_short_name"] or "")
        level = (r["level_code"] or "").strip()
        # Candidate slugs, most-specific first: explicit column, then derived
        # ("{level}-{kebab(name)}"). A name with no level can't map to a real
        # page (pages are always level-prefixed), so it is not derivable.
        candidates: list[str] = []
        if r["conference_slug"]:
            candidates.append(r["conference_slug"])
        if name and level:
            candidates.append(_conf_page_slug(name, level))

        slug: str | None = None
        if conf_dir is not None:
            for cand in candidates:
                if (conf_dir / f"{cand}.html").is_file():
                    slug = cand
                    break
        elif candidates:
            slug = candidates[0]
        if not slug:
            continue

        url = f"/conferences/{slug}.html"
        if url in seen:
            continue
        seen.add(url)

        subtitle = level.upper()
        short = (r["conference_short_name"] or "").strip()
        if short and short.upper() != (name or "").upper():
            subtitle = f"{subtitle} · {short}".strip(" ·")
        items.append(SearchItem(
            kind="conference",
            title=name or slug,
            url=url,
            subtitle=subtitle,
            tier=3,
        ))
    return items


# ---------------------------------------------------------------------------
# Methodology pages — static fixture (these don't live in the DB)
# ---------------------------------------------------------------------------

_METHODOLOGY_PAGES: tuple[tuple[str, str, str], ...] = (
    ("Fan Intelligence", "/methodology/fan-intelligence.html",
     "How we read the fanbase"),
    ("Freshness", "/methodology/freshness.html",
     "How current is each metric?"),
    ("Citations", "/methodology/citations.html",
     "Where our claims come from"),
    ("Confidence Signaling", "/methodology/confidence.html",
     "How we calibrate the chips"),
    ("Receipt Pattern", "/methodology/receipts.html",
     "Our editorial citation system"),
    ("Methodology Index", "/methodology/",
     "All methodology pages"),
)


def index_methodology() -> list[SearchItem]:
    """Hardcoded list of methodology pages.

    These don't live in the database; they're rendered from Python source
    so the canonical list is in `provenance/methodology_index_page.py`.
    Keep this list in sync (audited by test).
    """
    items: list[SearchItem] = []
    for title, url, subtitle in _METHODOLOGY_PAGES:
        items.append(SearchItem(
            kind="methodology",
            title=title,
            url=url,
            subtitle=subtitle,
            tier=4,
        ))
    return items


# ---------------------------------------------------------------------------
# Aggregator + writer
# ---------------------------------------------------------------------------

def build_search_index(
    db: "Database",
    *,
    players_max: int = 15000,
    season_year: int | None = None,
    profiled_slugs: frozenset[str] | None = None,
    site_dir: str | Path | None = None,
) -> list[SearchItem]:
    """Build the full search index. Order matters for stable JSON output:
    profiles → teams → conferences → editions → mailbag → players → methodology.

    ``site_dir`` (the output site root, e.g. ``output/site``) lets indexers
    that link to per-entity detail pages verify the page exists before emitting
    a result — currently used by ``index_conferences`` to avoid dead links.
    """
    if profiled_slugs is None:
        profiled_slugs = _discover_profiled_slugs()
    items: list[SearchItem] = []
    items += index_profiles(db, profiled_slugs=profiled_slugs)
    items += index_teams(db, profiled_slugs=profiled_slugs)
    items += index_conferences(db, site_dir=site_dir)
    items += index_editions(db)
    items += index_mailbag(db)
    items += index_players(db, players_max=players_max, season_year=season_year)
    items += index_methodology()
    return items


def write_search_index(
    db: "Database",
    output_path: str | Path,
    *,
    players_max: int = 15000,
    season_year: int | None = None,
    profiled_slugs: frozenset[str] | None = None,
    minify: bool = True,
) -> tuple[Path, int]:
    """Build + write the index JSON. Returns (path, item_count).

    ``minify=False`` emits indent=2 for inspection; default is minified
    one-line for production payload.
    """
    out_path = Path(output_path)
    items = build_search_index(
        db,
        players_max=players_max,
        season_year=season_year,
        profiled_slugs=profiled_slugs,
        # The site root is the parent of the index file (output/site/), which
        # is exactly where per-entity detail pages live for existence checks.
        site_dir=out_path.parent,
    )
    payload = {
        "items": [item.as_dict() for item in items],
        "schema_version": 1,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if minify:
        out_path.write_text(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return out_path, len(items)


__all__ = [
    "build_search_index",
    "write_search_index",
    "index_teams",
    "index_profiles",
    "index_players",
    "index_editions",
    "index_mailbag",
    "index_conferences",
    "index_methodology",
]
