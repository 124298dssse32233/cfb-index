from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Optional

from cfb_rankings.config import AppConfig
from cfb_rankings.db import Database

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GENERIC_PRIMARY = "#5A5954"
_GENERIC_ABBR = "TEAM"
_PAPER = "#F3EEE4"
_INK = "#0B0F14"


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TeamBrand:
    slug: str
    abbreviation: str
    primary_color: str
    secondary_color: Optional[str]
    mascot: Optional[str]
    texture: Optional[str]           # override-only field
    logo_local_path: Optional[str]   # site-relative path
    logo_dark_local_path: Optional[str]


# ---------------------------------------------------------------------------
# Module-level cache state
# ---------------------------------------------------------------------------

_BRAND_CACHE: dict[str, TeamBrand] = {}
_DB_BRAND_ROWS: dict[str, dict[str, Any]] = {}
_DB_ASSET_ROWS: dict[str, dict[str, Optional[str]]] = {}
_DB_LOADED: bool = False


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def refresh_cache() -> None:
    """Clear all caches and reset the loaded flag."""
    global _DB_LOADED
    _BRAND_CACHE.clear()
    _DB_BRAND_ROWS.clear()
    _DB_ASSET_ROWS.clear()
    _DB_LOADED = False


def _ensure_db_loaded() -> None:
    global _DB_LOADED
    if _DB_LOADED:
        return
    brand_rows, asset_rows = _load_db_rows()
    _DB_BRAND_ROWS.update(brand_rows)
    _DB_ASSET_ROWS.update(asset_rows)
    _DB_LOADED = True


def _load_db_rows() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Optional[str]]]]:
    """Load brand and asset rows from DB. Returns empty dicts on any failure."""
    try:
        config = AppConfig.from_env()
        db = Database(config.database_url)

        brand_rows_raw = db.query_all(
            """
            select t.slug, b.primary_color, b.secondary_color,
                   b.mascot_name, b.abbreviation_short
              from teams t
              left join team_brand b on b.team_id = t.team_id
             where t.slug is not null and t.slug <> ''
            """,
            {},
        )
        brand_rows: dict[str, dict[str, Any]] = {}
        for row in brand_rows_raw:
            slug = row.get("slug")
            if slug:
                brand_rows[slug] = {
                    "primary_color": row.get("primary_color"),
                    "secondary_color": row.get("secondary_color"),
                    "mascot_name": row.get("mascot_name"),
                    "abbreviation_short": row.get("abbreviation_short"),
                }

        asset_rows_raw = db.query_all(
            """
            select t.slug, a.asset_kind, a.local_path
              from team_brand_assets a
              join teams t on t.team_id = a.team_id
             where a.is_active = 1
               and a.source_name = 'cfbd'
               and a.asset_kind in ('logo_primary', 'logo_dark')
             order by a.fetched_at_utc desc
            """,
            {},
        )
        # Build {slug: {asset_kind: local_path}}, first-seen wins (most-recent due to ORDER BY desc).
        asset_rows: dict[str, dict[str, Optional[str]]] = {}
        for row in asset_rows_raw:
            slug = row.get("slug")
            kind = row.get("asset_kind")
            path = row.get("local_path")
            if slug and kind:
                if slug not in asset_rows:
                    asset_rows[slug] = {}
                if kind not in asset_rows[slug]:
                    asset_rows[slug][kind] = path

        return brand_rows, asset_rows

    except Exception:
        # Graceful degradation: DB file or tables may not exist on first-run bootstrap.
        return {}, {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _override_for(slug: str) -> dict[str, Any]:
    """Lazy import of TEAM_COLOR_BY_SLUG to avoid circular imports."""
    from cfb_rankings.hub_page import TEAM_COLOR_BY_SLUG  # noqa: PLC0415
    return TEAM_COLOR_BY_SLUG.get(slug) or {}


def _ink_for(hex_color: str) -> str:
    """Return dark ink or white depending on perceived brightness of hex_color.

    Uses the ITU-R BT.601 luma formula: (r*299 + g*587 + b*114) / 1000.
    Values > 140 (out of 255) are considered light → use dark ink; else white.
    """
    c = (hex_color or "").lstrip("#")
    if len(c) != 6:
        return "#FFFFFF"
    try:
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except ValueError:
        return "#FFFFFF"
    luma = (r * 299 + g * 587 + b * 114) / 1000
    return _INK if luma > 140 else "#FFFFFF"


def _generic_abbr(slug: Optional[str]) -> str:
    """Return a 4-char uppercase abbreviation from slug, or 'TEAM' if slug is empty."""
    if not slug:
        return _GENERIC_ABBR
    return slug[:4].upper()


def _fallback(slug: Optional[str]) -> TeamBrand:
    """Return a generic TeamBrand for unknown or missing slugs."""
    return TeamBrand(
        slug=slug or "",
        abbreviation=_generic_abbr(slug),
        primary_color=_GENERIC_PRIMARY,
        secondary_color=None,
        mascot=None,
        texture=None,
        logo_local_path=None,
        logo_dark_local_path=None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_team_brand(slug: Optional[str]) -> TeamBrand:
    """Resolve full TeamBrand for a team slug.

    Resolution precedence (highest → lowest):
    1. TEAM_COLOR_BY_SLUG override  — primary_color, abbreviation, texture
    2. DB team_brand row            — secondary_color, mascot; fills primary/abbr if override absent
    3. Generic fallback             — #5A5954, 4-char slug upper, all other fields None
    """
    # Normalise slug
    if not slug:
        return _fallback(None)
    slug = str(slug).strip()
    if not slug:
        return _fallback("")

    # Return cached result if present
    if slug in _BRAND_CACHE:
        return _BRAND_CACHE[slug]

    _ensure_db_loaded()

    override = _override_for(slug)
    db_brand = _DB_BRAND_ROWS.get(slug, {})
    db_assets = _DB_ASSET_ROWS.get(slug, {})

    # primary_color: override wins; fall back to DB, then generic
    primary_color: str = (
        override.get("primary")
        or db_brand.get("primary_color")
        or _GENERIC_PRIMARY
    )

    # abbreviation: override wins; fall back to DB abbreviation_short, then slug[:4]
    abbreviation: str = (
        override.get("abbr")
        or db_brand.get("abbreviation_short")
        or _generic_abbr(slug)
    )

    # texture: override only
    texture: Optional[str] = override.get("texture")

    # secondary_color and mascot: DB only
    secondary_color: Optional[str] = db_brand.get("secondary_color")
    mascot: Optional[str] = db_brand.get("mascot_name")

    # logo paths: DB assets only
    logo_local_path: Optional[str] = db_assets.get("logo_primary")
    logo_dark_local_path: Optional[str] = db_assets.get("logo_dark")

    brand = TeamBrand(
        slug=slug,
        abbreviation=abbreviation,
        primary_color=primary_color,
        secondary_color=secondary_color,
        mascot=mascot,
        texture=texture,
        logo_local_path=logo_local_path,
        logo_dark_local_path=logo_dark_local_path,
    )
    _BRAND_CACHE[slug] = brand
    return brand


def team_chit_svg(slug: Optional[str], size: int = 20, *, on_dark: bool = False) -> str:
    """Render a two-tone circular team chit as an SVG string.

    Outer circle: team primary color with paper/ink stroke.
    Inner circle: paper at 0.12 opacity (highlight ring).
    Wordmark: abbreviation in IBM Plex Mono 700, auto-contrasted.
    """
    brand = resolve_team_brand(slug)
    r = size / 2
    inner_r = r * (10 / 14)
    stroke_color = _INK if on_dark else _PAPER
    text_color = _ink_for(brand.primary_color)
    font_size = max(7, round(size * 9 / 28))
    abbr = escape(brand.abbreviation)
    title = escape(brand.slug or "")

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" '
        f'viewBox="-{r} -{r} {size} {size}" '
        f'class="team-chit">'
        f"<title>{title}</title>"
        f'<circle r="{r}" fill="{brand.primary_color}" '
        f'stroke="{stroke_color}" stroke-width="1.5"/>'
        f'<circle r="{inner_r:.2f}" fill="{_PAPER}" fill-opacity="0.12"/>'
        f'<text x="0" y="0" '
        f'dominant-baseline="central" text-anchor="middle" '
        f'font-family="IBM Plex Mono,monospace" font-weight="700" '
        f'font-size="{font_size}" fill="{text_color}">'
        f"{abbr}</text>"
        f"</svg>"
    )
    return svg


def team_logo_src(slug: Optional[str], variant: str = "primary") -> Optional[str]:
    """Return the site-relative logo path for a team.

    variant='primary' → logo_local_path
    variant='dark'    → logo_dark_local_path
    Any other variant → None (Phase 3 concern)
    """
    brand = resolve_team_brand(slug)
    if variant == "primary":
        return brand.logo_local_path
    if variant == "dark":
        return brand.logo_dark_local_path
    return None
