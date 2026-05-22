"""Fan Intelligence Hub v5 — publication page renderer.

Produces ``output/site/hub/index.html`` from data populated by the Phase 1 CLIs
(seed-archetypes, classify-fanbases, compute-mood-week, compute-rivalry-ratios,
mine-lexicon). Structure follows the Figma v5.1 spec (App.tsx section order):

  Masthead \u2192 Navigation \u2192 CoverHero \u2192 EditorNote \u2192
  N\u00b0 01 Mood Index \u2192 N\u00b0 02 Ticker \u2192 N\u00b0 03 Hype vs Reality \u2192
  N\u00b0 04 Taxonomy \u2192 N\u00b0 05 Rivalry Matrix \u2192 N\u00b0 06 Lexicon \u2192
  N\u00b0 07 Index Cards \u2192 N\u00b0 08 Commiseration \u2192 Footer

Every chart-bearing section emits a single ``<div class="hub-methodology">``
row so the page keeps one consistent methodology format (Phase 6.2).

The team-page archetype module ``render_team_archetype_module()`` is exposed
from this same file so team pages can import a single rendering function
(Phase 3 + Phase 7).
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
from html import escape
import json
from pathlib import Path

from cfb_rankings.common.cfb_calendar import (
    cfb_week_label,
    days_to_kickoff,
    is_in_season,
    is_offseason,
)
from typing import Any

from cfb_rankings.common.head_chrome import absolute_url
from cfb_rankings.db import Database
from cfb_rankings.visual_assets import resolve_team_brand
from cfb_rankings.ingest.archetypes import (
    archetype_by_slug,
    fetch_migration_sparkline,
    PRIMARY_ARCHETYPES,
    MODIFIERS,
)
from cfb_rankings.ingest.hub_data import (
    fetch_issue_metadata,
    fetch_mood_ticker,
    fetch_mood_week,
    fetch_rivalry_week,
    fetch_featured_lexicon,
    fetch_taxonomy_with_teams,
    fetch_modifiers,
    MOOD_SEED_047,
    ISSUE_047,
)


# ---------------------------------------------------------------------------
# Palette / tokens (mirrors Figma v5.1 design tokens)
# ---------------------------------------------------------------------------

PALETTE = {
    "paper": "#F3EEE4",
    "paper_warm": "#E8E1D2",
    "ink": "#0B0F14",
    "ink_muted": "#5A5954",
    "rule": "#B5AFA3",
    "gold": "#E0A300",
    "alert": "#B7281D",
    "michigan_blue": "#00274C",
    "michigan_maize": "#FFCB05",
    "alabama_houndstooth": "#828A8F",  # Phase 5 two-reds fix: render Alabama in houndstooth grey on the Mood Index chart only.
}


TEAM_COLOR_BY_SLUG: dict[str, dict[str, str]] = {
    "georgia": {"primary": "#BA0C2F", "abbr": "UGA", "texture": "pinstripe"},
    "texas": {"primary": "#BF5700", "abbr": "TEX"},
    "ohio-state": {"primary": "#BB0000", "abbr": "OSU", "texture": "diagonal"},
    "oregon": {"primary": "#007030", "abbr": "ORE"},
    "alabama": {"primary": "#9E1B32", "abbr": "ALA", "texture": "houndstooth"},
    "michigan": {"primary": "#00274C", "abbr": "MICH", "texture": "diagonal"},
    "penn-state": {"primary": "#041E42", "abbr": "PSU", "texture": "pinstripe"},
    "nebraska": {"primary": "#E41C38", "abbr": "NEB", "texture": "checker"},
    "texas-am": {"primary": "#500000", "abbr": "A&M"},
    "tennessee": {"primary": "#FF8200", "abbr": "TEN"},
    "usc": {"primary": "#990000", "abbr": "USC"},
    "florida": {"primary": "#0021A5", "abbr": "UF"},
    "miami": {"primary": "#F47321", "abbr": "MIA"},
    "notre-dame": {"primary": "#0C2340", "abbr": "ND", "texture": "checker"},
    "colorado": {"primary": "#CFB87C", "abbr": "CU"},
    "lsu": {"primary": "#461D7C", "abbr": "LSU"},
    "florida-state": {"primary": "#782F40", "abbr": "FSU"},
    "clemson": {"primary": "#F56600", "abbr": "CLEM"},
    "iowa": {"primary": "#FFCD00", "abbr": "IOWA"},
    "wisconsin": {"primary": "#C5050C", "abbr": "WIS", "texture": "diagonal"},
    "utah": {"primary": "#CC0000", "abbr": "UTAH"},
    "indiana": {"primary": "#990000", "abbr": "IND"},
    "kansas": {"primary": "#0051BA", "abbr": "KU"},
    "arizona": {"primary": "#003366", "abbr": "ARIZ"},
    "boise-state": {"primary": "#0033A0", "abbr": "BSU"},
    "appalachian-state": {"primary": "#222222", "abbr": "APP"},
    "smu": {"primary": "#C8102E", "abbr": "SMU"},
    "auburn": {"primary": "#03244D", "abbr": "AUB"},
    "oklahoma": {"primary": "#841617", "abbr": "OU"},
    "washington": {"primary": "#4B2E83", "abbr": "UW"},
    "stanford": {"primary": "#8C1515", "abbr": "STAN"},
    "california": {"primary": "#003262", "abbr": "CAL"},
    "army": {"primary": "#000000", "abbr": "ARMY"},
    "navy": {"primary": "#002F5F", "abbr": "NAVY"},
    "south-carolina": {"primary": "#73000A", "abbr": "SC"},
    "pittsburgh": {"primary": "#003594", "abbr": "PITT"},
    "iowa-state": {"primary": "#C8102E", "abbr": "ISU"},
    "northwestern": {"primary": "#4E2A84", "abbr": "NW"},
    "vanderbilt": {"primary": "#866D4B", "abbr": "VAN"},
    "jackson-state": {"primary": "#003DA5", "abbr": "JKST"},
    "prairie-view-am": {"primary": "#500778", "abbr": "PVAM"},
    "west-virginia": {"primary": "#002855", "abbr": "WVU"},
    "ole-miss": {"primary": "#14213D", "abbr": "MISS"},
    "mississippi": {"primary": "#14213D", "abbr": "MISS"},
    "arkansas": {"primary": "#9D2235", "abbr": "ARK"},
    "memphis": {"primary": "#003087", "abbr": "MEM"},
    "james-madison": {"primary": "#450084", "abbr": "JMU"},
    "liberty": {"primary": "#002147", "abbr": "LIB"},
    "kentucky": {"primary": "#00A9E0", "abbr": "KYS"},
    "ucla": {"primary": "#2D68C4", "abbr": "UCLA"},
    "texas-tech": {"primary": "#CC0000", "abbr": "TTU", "texture": "pinstripe"},
    "air-force": {"primary": "#003087", "abbr": "AF"},
}


def team_color(slug: str | None, fallback: str = "#5A5954") -> dict[str, str]:
    if not slug:
        return {"primary": fallback, "abbr": "—"}
    brand = resolve_team_brand(str(slug).strip().lower())
    primary = brand.primary_color if brand.primary_color else fallback
    abbr = brand.abbreviation if brand.abbreviation else str(slug).strip()[:4].upper()
    return {"primary": primary, "abbr": abbr}


def _ink_for(hex_color: str) -> str:
    """Return paper ink or white depending on team-color luminance (WCAG-ish)."""
    c = (hex_color or "").lstrip("#")
    if len(c) != 6:
        return "#FFFFFF"
    try:
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except ValueError:
        return "#FFFFFF"
    def _lin(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    lum = 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
    # Threshold tuned so CU khaki (#CFB87C, lum≈0.49) and Iowa gold render dark ink.
    return "#FFFFFF" if lum < 0.45 else PALETTE["ink"]


# Sanity asserts (cheap; run at import — keeps the contrast contract honest).
assert _ink_for("#BA0C2F") == "#FFFFFF"
assert _ink_for("#FFCD00") == PALETTE["ink"]


def _build_texture_defs(team_color_by_slug: dict, palette: dict) -> str:
    """Emit one <pattern> per (slug, texture) override in team_color_by_slug."""
    paper = palette["paper"]
    parts: list[str] = []
    for slug, info in team_color_by_slug.items():
        variant = info.get("texture")
        if not variant:
            continue
        ink = info["primary"]
        pid = f"tex-{variant}-{slug}"
        if variant == "houndstooth":
            parts.append(
                f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="8" height="8">'
                f'<rect width="8" height="8" fill="{paper}"/>'
                f'<rect x="0" y="0" width="4" height="4" fill="{ink}"/>'
                f'<rect x="4" y="2" width="2" height="2" fill="{ink}"/>'
                f'<rect x="2" y="4" width="2" height="2" fill="{ink}"/>'
                f'<rect x="6" y="6" width="2" height="2" fill="{ink}"/>'
                f'</pattern>'
            )
        elif variant == "pinstripe":
            parts.append(
                f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="2" height="4">'
                f'<rect width="2" height="4" fill="{paper}"/>'
                f'<rect x="0" y="0" width="1" height="4" fill="{ink}"/>'
                f'</pattern>'
            )
        elif variant == "diagonal":
            parts.append(
                f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="3" height="3" patternTransform="rotate(45)">'
                f'<rect width="3" height="3" fill="{paper}"/>'
                f'<rect x="0" y="0" width="1" height="3" fill="{ink}"/>'
                f'</pattern>'
            )
        elif variant == "checker":
            parts.append(
                f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="4" height="4">'
                f'<rect width="4" height="4" fill="{paper}"/>'
                f'<rect x="0" y="0" width="2" height="2" fill="{ink}"/>'
                f'<rect x="2" y="2" width="2" height="2" fill="{ink}"/>'
                f'</pattern>'
            )
    return "".join(parts)


FRIENDLY_MODEL_LABEL = "CFB Index v1"


# ---------------------------------------------------------------------------
# Shared partials
# ---------------------------------------------------------------------------


def render_masthead(issue_number: str, model_week: int | None, issue_date: str, updated_label: str | None = None) -> str:
    # Fallback label is offseason-aware. Most callers pass an explicit
    # "Updated {date}" so this is just a safety net.
    if updated_label is None:
        updated_label = "Updated this offseason" if is_offseason(date.today(), db=None) else "Updated this week"
    # In-season the bare "Model Week N" label is fine. Offseason it reads as
    # garbage to readers ("Model Week 20" in late May means nothing), so swap
    # in the phase + days-to-kickoff parenthetical. See cfb_calendar module.
    today = date.today()
    if model_week and is_in_season(today, db=None):
        mw = f"Model Week {int(model_week)}"
    elif model_week:
        # Offseason: replace 'Model Week N' with phase + countdown.
        mw = f"{cfb_week_label(today, db=None)}"
    else:
        mw = "Model Week \u2014"
    return f"""
    <div class="hub-masthead">
      <div class="hub-container hub-masthead-inner">
        <div class="hub-mast-left">
          <span>The CFB Index</span>
          <span class="hub-dot">\u00b7</span>
          <span>Fan Intelligence</span>
          <span class="hub-dot">\u00b7</span>
          <span>Vol V</span>
          <span class="hub-dot">\u00b7</span>
          <span>{escape(issue_number)}</span>
          <span class="hub-dot">\u00b7</span>
          <span>{escape(mw)}</span>
        </div>
        <div class="hub-mast-right">
          <span>{escape(issue_date)}</span>
          <span class="hub-dot">\u00b7</span>
          <span>{escape(updated_label)}</span>
          <span class="hub-pulse" aria-hidden="true"></span>
        </div>
      </div>
    </div>
    """


def render_nav(
    issue_number: str,
    prev_issue: str | None = None,
    next_issue: str | None = None,
    site_prefix: str = "../",
    retro: bool = False,
) -> str:
    # We don't yet have a stable URL scheme for prev/next hub issues — the
    # main hub is /hub/index.html and historical issues live under retro/.
    # Render the chevrons as inert spans so we don't ship dead href="#"
    # links to the live site. When the routing exists, swap back to <a>.
    prev_html = (
        f'<span class="hub-nav-chevron hub-nav-chevron--inert">&larr; {escape(prev_issue)}</span>'
        if prev_issue else ""
    )
    next_html = (
        f'<span class="hub-nav-chevron hub-nav-chevron--inert">{escape(next_issue)} preview &rarr;</span>'
        if next_issue else ""
    )
    retro_html = '<a href="./">Retro Archive</a>' if retro else ""
    return f"""
    <div class="hub-nav">
      <div class="hub-container hub-nav-inner">
        <div class="hub-nav-left">
          <a class="hub-nav-brand" href="{site_prefix}">THE CFB INDEX</a>
          {prev_html}
        </div>
        <nav class="hub-nav-menu">
          <a href="{site_prefix}rankings/">Rankings</a>
          <a href="{site_prefix}matchups/">Matchups</a>
          <a href="{site_prefix}teams/">Teams</a>
          <a href="{site_prefix}players/">Players</a>
          <a class="hub-nav-active" href="./">Hub</a>
          {retro_html}
          <a href="{site_prefix}archive/">Archive</a>
          <a href="{site_prefix}about-model/">The Model</a>
          <a class="hub-nav-subscribe" href="#">Subscribe</a>
        </nav>
        {next_html}
      </div>
    </div>
    """


def render_section_eyebrow(section_num: str, section_name: str) -> str:
    """Render an N\u00b0 XX eyebrow with optional rubric icon (Tier-1 art).

    Maps section_name \u2192 rubric slug. If a rubric exists for that section,
    prepends a 40px PNG icon. Missing-rubric sections render text-only
    (graceful fallback \u2014 caller doesn't need to know which sections have
    art). See src/cfb_rankings/illustrations.py for the URL emitter.
    """
    from cfb_rankings.illustrations import rubric_url

    # Map known section names \u2192 rubric slug. Inexact matches fall through
    # to "no icon" rather than emit a broken <img>. Keep this map narrow:
    # only confident pairings ship art.
    _name_to_rubric = {
        "the ticker": "the-ticker",
        "the matrix": "hype-vs-reality",  # The Matrix = hype-vs-reality matrix
        "the taxonomy": "the-taxonomy",
        "the rivalry": "the-rivalry",
        "the lexicon": "the-lexicon",
        "the index cards": "this-weeks-cards",
        "the mood index": "the-mood-index",
        "the commiseration": "the-commiseration",
    }
    # Strip suffixes like " \u00b7 N\u00b0 047" so "The Index Cards \u00b7 N\u00b0 047" maps
    name_key = section_name.split("\u00b7", 1)[0].strip().lower()
    slug = _name_to_rubric.get(name_key)
    icon_html = ""
    if slug:
        url = rubric_url(slug, size=40)
        if url:
            icon_html = (
                f'<img class="hub-eyebrow__rubric" src="{escape(url)}" '
                f'alt="" width="20" height="20" '
                f'loading="lazy" decoding="async" '
                f'style="vertical-align:middle;margin-right:8px;">'
            )
    return (
        f'<div class="hub-eyebrow">'
        f'{icon_html}{escape(section_num)} <span class="hub-gold-dot">\u00b7</span> {escape(section_name)}'
        f'</div>'
    )


def render_methodology_row(*parts: str, link_label: str = "methodology \u2192") -> str:
    """Canonical metadata row under every chart. Joins parts with a gold dot."""

    fragments = []
    for i, part in enumerate(parts):
        if i:
            fragments.append('<span class="hub-gold-dot">\u00b7</span>')
        fragments.append(f'<span>{escape(part)}</span>')
    if link_label:
        fragments.append('<span class="hub-gold-dot">\u00b7</span>')
        # site-absolute so this works from hub root (/hub/) AND hub/retro/<issue>/
        fragments.append(f'<a href="/about-model/">{escape(link_label)}</a>')
    return f'<div class="hub-methodology">{" ".join(fragments)}</div>'


def _issue_methodology(
    issue: dict[str, Any],
    section_key: str,
    fallback_parts: tuple[str, ...],
    *,
    link_label: str = "methodology \u2192",
) -> str:
    if not issue.get("is_retro"):
        return render_methodology_row(*fallback_parts, link_label=link_label)
    methodology = issue.get("methodology") or {}
    parts = methodology.get(section_key) or fallback_parts
    if isinstance(parts, dict):
        parts = parts.get("parts") or fallback_parts
    if not isinstance(parts, (list, tuple)):
        parts = fallback_parts
    return render_methodology_row(*(str(part) for part in parts), link_label=link_label)


def _row_source(row: dict[str, Any] | None) -> str:
    source = str((row or {}).get("source") or "computed").strip().lower()
    return source or "computed"


def _section_source(rows: list[dict[str, Any]] | None = None, *, issue: dict[str, Any] | None = None) -> str:
    sources = [_row_source(row) for row in (rows or [])]
    if issue is not None:
        sources.append(_row_source(issue))
    if any(source not in {"computed", "live"} for source in sources):
        return "editorial"
    return "computed"


def _provenance_label(source: str) -> str:
    normalized = source.strip().lower()
    if normalized == "computed":
        return "Live"
    if normalized == "curated":
        return "Curated"
    return "Editorial"


def render_provenance_badge(source: str) -> str:
    normalized = "computed" if source == "live" else source
    return (
        f'<span class="hub-provenance-badge" data-provenance="{escape(normalized)}">'
        f'{escape(_provenance_label(normalized))}</span>'
    )


def _section_attr(source: str) -> str:
    return f' data-provenance="{escape(source)}"'


def render_team_chip(slug: str | None, abbr: str | None = None, color: str | None = None, size: str = "sm") -> str:
    # Phase 2: delegated to visual_assets registry.
    # abbr/color kwargs remain in the signature for call-site compatibility but
    # are hints the registry is free to ignore in favor of the authoritative
    # override/DB/fallback chain.
    from cfb_rankings.visual_assets import team_chit_svg
    size_px = {"sm": 20, "md": 28, "lg": 36}.get(size, 20)
    return team_chit_svg(slug, size=size_px)


# ---------------------------------------------------------------------------
# Section 00: Cover hero
# ---------------------------------------------------------------------------


# Michigan 10-week mood trajectory (Feb 15 \u2192 Apr 22)
COVER_MICHIGAN_TRAJECTORY = [
    ("Feb 15", 73), ("Feb 22", 72), ("Mar 1", 71), ("Mar 8", 70),
    ("Mar 14", 68), ("Mar 22", 64), ("Mar 29", 61), ("Apr 5", 59),
    ("Apr 12", 58), ("Apr 22", 58),
]


def _render_cover_sparkline_svg(points: list[tuple[str, int]], *, width: int = 520, height: int = 320,
                                line_color: str = PALETTE["michigan_blue"],
                                endpoint_color: str = PALETTE["michigan_maize"],
                                moore_presser_week: str | None = "Mar 14",
                                reference_y: int | None = 67,
                                reference_label: str = "10-year average",
                                y_min: int = 50, y_max: int = 80) -> str:
    """Render the cover-hero line chart with endpoint dot + Moore-presser tick + reference line."""

    if not points:
        return ""
    pad_l, pad_r, pad_t, pad_b = 40, 80, 30, 40
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b

    def x_for(idx: int) -> float:
        return pad_l + (idx / max(1, len(points) - 1)) * chart_w

    def y_for(value: float) -> float:
        return pad_t + (1 - (value - y_min) / (y_max - y_min)) * chart_h

    # Line path
    path_d = "M " + " L ".join(f"{x_for(i):.1f},{y_for(v):.1f}" for i, (_, v) in enumerate(points))

    # Reference dashed line + label
    reference_svg = ""
    if reference_y is not None:
        ref_y = y_for(reference_y)
        reference_svg = (
            f'<line x1="{pad_l}" y1="{ref_y:.1f}" x2="{pad_l + chart_w:.1f}" y2="{ref_y:.1f}" '
            f'stroke="{PALETTE["ink_muted"]}" stroke-width="1" stroke-dasharray="4 4"/>'
            f'<text x="{pad_l + chart_w - 10:.1f}" y="{ref_y - 6:.1f}" '
            f'text-anchor="end" font-family="Source Serif 4,serif" font-style="italic" '
            f'font-size="11" fill="{PALETTE["ink_muted"]}">{escape(reference_label)}</text>'
        )

    # Moore-presser vertical tick
    presser_svg = ""
    if moore_presser_week is not None:
        for idx, (label, _) in enumerate(points):
            if label == moore_presser_week:
                x = x_for(idx)
                presser_svg = (
                    f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{pad_t + chart_h}" '
                    f'stroke="{PALETTE["ink_muted"]}" stroke-width="1" stroke-dasharray="2 3"/>'
                    f'<text x="{x + 4:.1f}" y="{pad_t + 14}" '
                    f'font-family="IBM Plex Mono,monospace" font-style="italic" font-size="10" '
                    f'fill="{PALETTE["ink_muted"]}">Moore presser</text>'
                )
                break

    # X-axis labels (horizontal, not rotated)
    x_labels = "".join(
        f'<text x="{x_for(i):.1f}" y="{pad_t + chart_h + 18:.1f}" '
        f'text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="10" '
        f'fill="{PALETTE["rule"]}">{escape(label)}</text>'
        for i, (label, _) in enumerate(points)
    )

    # Y-axis ticks
    y_ticks = ""
    for tick in range(y_min, y_max + 1, 10):
        y = y_for(tick)
        y_ticks += (
            f'<text x="{pad_l - 8:.1f}" y="{y + 3:.1f}" text-anchor="end" '
            f'font-family="IBM Plex Mono,monospace" font-size="10" '
            f'fill="{PALETTE["rule"]}" style="font-variant-numeric:tabular-nums;">{tick}</text>'
        )

    # Endpoint dot + label
    end_x = x_for(len(points) - 1)
    end_y = y_for(points[-1][1])
    endpoint_dot = (
        f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="5" fill="{endpoint_color}"/>'
        f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="2.5" fill="{line_color}"/>'
    )
    endpoint_label = (
        f'<text x="{end_x + 12:.1f}" y="{end_y + 4:.1f}" '
        f'font-family="IBM Plex Mono,monospace" font-size="11" font-weight="700" '
        f'fill="{PALETTE["ink"]}" style="font-variant-numeric:tabular-nums;">MICH {points[-1][1]}</text>'
    )

    # Dots
    dots = "".join(
        f'<circle cx="{x_for(i):.1f}" cy="{y_for(v):.1f}" r="2.5" fill="{line_color}"/>'
        for i, (_, v) in enumerate(points[:-1])
    )

    return f"""
    <svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Michigan mood trajectory">
      {reference_svg}
      {presser_svg}
      <path d="{path_d}" stroke="{line_color}" stroke-width="2.5" fill="none"/>
      {dots}
      {endpoint_dot}
      {endpoint_label}
      {y_ticks}
      {x_labels}
    </svg>
    """


def _render_retro_cover_art_svg(issue: dict[str, Any]) -> str:
    title = str(issue.get("retro_title") or issue.get("cover_headline") or "Retro Issue")
    words = title.upper().split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        projected = sum(len(item) for item in current) + len(word) + len(current)
        if projected > 18 and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    title_svg = "".join(
        f'<text x="36" y="{88 + idx * 54}" font-family="Bebas Neue,Impact,sans-serif" '
        f'font-size="48" fill="#0B0F14">{escape(line)}</text>'
        for idx, line in enumerate(lines[:3])
    )
    return f"""
    <svg viewBox="0 0 520 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Retro issue editorial cover card">
      <rect width="520" height="360" fill="#FFF4CF"/>
      <rect x="18" y="18" width="484" height="324" fill="none" stroke="#0B0F14" stroke-width="2"/>
      <rect x="36" y="260" width="448" height="52" fill="#0B0F14"/>
      <text x="36" y="54" font-family="IBM Plex Mono,monospace" font-size="13" font-weight="700" fill="#6F4D00" letter-spacing="2">
        {escape(str(issue.get("issue_number") or ""))} / EDITORIAL RECONSTRUCTION
      </text>
      {title_svg}
      <text x="56" y="293" font-family="IBM Plex Mono,monospace" font-size="14" font-weight="700" fill="#F3EEE4" letter-spacing="1.4">
        PUBLIC-RECORD SEED / {escape(str(issue.get("issue_date") or "").upper())}
      </text>
    </svg>
    """


def render_cover_hero(issue: dict[str, Any]) -> str:
    chart_svg = (
        _render_retro_cover_art_svg(issue)
        if issue.get("is_retro")
        else _render_cover_sparkline_svg(COVER_MICHIGAN_TRAJECTORY)
    )
    methodology = _issue_methodology(
        issue,
        "cover",
        ("Chart by The Index Desk", f"Model: {FRIENDLY_MODEL_LABEL}"),
        link_label="",
    )
    source = _section_source(issue=issue)
    provenance = render_provenance_badge(source) if issue.get("is_retro") else ""
    return f"""
    <section class="hub-cover"{_section_attr(source) if issue.get("is_retro") else ""}>
      <div class="hub-container">
        <div class="hub-cover-grid">
          <div class="hub-cover-left">
            <div class="hub-eyebrow">
              This Week&rsquo;s Cover <span class="hub-gold-dot">\u00b7</span> Fan Intelligence <span class="hub-gold-dot">\u00b7</span> {escape(issue["issue_number"])}
            </div>
            <h1 class="hub-display-xl">{escape(issue["cover_headline"])}</h1>
            <p class="hub-dek">{escape(issue["cover_dek"])}</p>
            <div class="hub-byline">
              By The CFB Index Model <span class="hub-gold-dot">\u00b7</span>
              Edited by The Staff <span class="hub-gold-dot">\u00b7</span>
              {escape(issue["issue_date"])}
              {provenance}
            </div>
            <blockquote class="hub-pull-quote">
              {escape(issue.get("pull_quote") or "")}
            </blockquote>
          </div>
          <div class="hub-cover-right">
            <div class="hub-cover-chart">{chart_svg}</div>
            <p class="hub-caption">{escape(issue["cover_chart_caption"])}</p>
            {methodology}
            <aside class="hub-also-reading">
              <div class="hub-eyebrow-sm">Also Reading</div>
              <div class="hub-also-list">
                <a href="#sec-01">Oregon passes Alabama</a>
                <span class="hub-gold-dot">\u00b7</span>
                <a href="#sec-02">The quiet Iowa floor</a>
                <span class="hub-gold-dot">\u00b7</span>
                <a href="#sec-07">Nebraska &ldquo;we&rsquo;re back&rdquo; at 47,392</a>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </section>
    """


# ---------------------------------------------------------------------------
# Editor's Note
# ---------------------------------------------------------------------------


def render_editor_note(issue: dict[str, Any]) -> str:
    body = str(issue.get("editor_note_body") or "").strip()
    return f"""
    <section class="hub-editor-note">
      <div class="hub-editor-inner">
        <div class="hub-eyebrow">
          Editor&rsquo;s Note <span class="hub-gold-dot">\u00b7</span> {escape(issue["issue_number"])}
        </div>
        <div class="hub-editor-body">
          <p class="hub-editor-paragraph">{escape(body)}</p>
          <p class="hub-editor-signoff">&mdash; the staff <span class="hub-gold-dot">\u00b7</span> {escape(issue["issue_date"])}</p>
        </div>
      </div>
    </section>
    """


# ---------------------------------------------------------------------------
# N\u00b0 01 \u2014 Mood Index flagship chart
# ---------------------------------------------------------------------------


MOOD_INDEX_TRAJECTORY: dict[str, list[tuple[str, int]]] = {
    "georgia":    [("Feb 15",92),("Feb 22",91),("Mar 1",92),("Mar 8",93),("Mar 14",93),("Mar 22",94),("Mar 29",94),("Apr 5",94),("Apr 12",94),("Apr 22",94)],
    "texas":      [("Feb 15",88),("Feb 22",89),("Mar 1",89),("Mar 8",90),("Mar 14",90),("Mar 22",91),("Mar 29",91),("Apr 5",91),("Apr 12",91),("Apr 22",91)],
    "ohio-state": [("Feb 15",85),("Feb 22",86),("Mar 1",86),("Mar 8",87),("Mar 14",88),("Mar 22",89),("Mar 29",89),("Apr 5",90),("Apr 12",90),("Apr 22",90)],
    "oregon":     [("Feb 15",82),("Feb 22",83),("Mar 1",84),("Mar 8",85),("Mar 14",86),("Mar 22",87),("Mar 29",87),("Apr 5",87),("Apr 12",87),("Apr 22",87)],
    "alabama":    [("Feb 15",78),("Feb 22",77),("Mar 1",76),("Mar 8",75),("Mar 14",74),("Mar 22",73),("Mar 29",72),("Apr 5",72),("Apr 12",72),("Apr 22",72)],
    "michigan":   [("Feb 15",73),("Feb 22",72),("Mar 1",71),("Mar 8",70),("Mar 14",68),("Mar 22",64),("Mar 29",61),("Apr 5",59),("Apr 12",58),("Apr 22",58)],
}

# Alabama override: use houndstooth grey to stay visually distinct from Ohio State
# (the two-reds fix from Phase 5). All other teams render in their primary color.
MOOD_INDEX_TEAM_COLORS: dict[str, str] = {
    "georgia": "#BA0C2F",
    "texas": "#BF5700",
    "ohio-state": "#BB0000",
    "oregon": "#007030",
    "alabama": PALETTE["alabama_houndstooth"],
    "michigan": PALETTE["michigan_blue"],
}


def _render_mood_index_chart_svg() -> str:
    width, height = 1080, 520
    pad_l, pad_r, pad_t, pad_b = 50, 260, 50, 50
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    y_min, y_max = 50, 100
    weeks = [w for w, _ in MOOD_INDEX_TRAJECTORY["georgia"]]
    n = len(weeks)

    def x_for(idx: int) -> float:
        return pad_l + (idx / max(1, n - 1)) * chart_w

    def y_for(value: float) -> float:
        return pad_t + (1 - (value - y_min) / (y_max - y_min)) * chart_h

    # Playoff-confidence reference line, labeled in chart-left whitespace (Phase 5 fix)
    ref_y = y_for(75)
    reference_svg = (
        f'<line x1="{pad_l}" y1="{ref_y:.1f}" x2="{pad_l + chart_w:.1f}" y2="{ref_y:.1f}" '
        f'stroke="{PALETTE["ink_muted"]}" stroke-width="1" stroke-dasharray="4 4"/>'
        f'<text x="{pad_l - 8:.1f}" y="{ref_y - 6:.1f}" text-anchor="end" '
        f'font-family="Source Serif 4,serif" font-style="italic" font-size="12" '
        f'fill="{PALETTE["ink_muted"]}">playoff confidence</text>'
    )

    # Lines for each team
    lines_svg: list[str] = []
    legend_items: list[tuple[str, int, int, str]] = []  # (slug, final_value, prev_value, color)
    for slug, points in MOOD_INDEX_TRAJECTORY.items():
        color = MOOD_INDEX_TEAM_COLORS[slug]
        path_d = "M " + " L ".join(f"{x_for(i):.1f},{y_for(v):.1f}" for i, (_, v) in enumerate(points))
        lines_svg.append(
            f'<path d="{path_d}" stroke="{color}" stroke-width="2.5" fill="none"/>'
        )
        legend_items.append((slug, points[-1][1], points[-2][1], color))

    # Legend on right rail, with 20px chip + delta chip
    legend_svg: list[str] = []
    legend_x = pad_l + chart_w + 20
    for i, (slug, final, prev, color) in enumerate(legend_items):
        y = pad_t + 30 + i * 52
        meta = team_color(slug)
        delta = final - prev
        delta_color = PALETTE["gold"] if delta > 0 else PALETTE["alert"] if delta < 0 else PALETTE["ink_muted"]
        delta_text = f"{delta:+d}" if delta != 0 else "0"
        legend_svg.append(
            f'<g transform="translate({legend_x:.1f},{y:.1f})">'
            f'<circle cx="10" cy="0" r="10" fill="{color}"/>'
            f'<text x="10" y="3" text-anchor="middle" '
            f'font-family="IBM Plex Mono,monospace" font-size="9" font-weight="700" '
            f'fill="#FFFFFF">{escape(meta["abbr"])}</text>'
            f'<text x="28" y="-3" font-family="IBM Plex Mono,monospace" font-size="10" '
            f'fill="{PALETTE["ink"]}" style="text-transform:uppercase;letter-spacing:0.06em;">{escape(slug.replace("-"," ").title())}</text>'
            f'<text x="28" y="13" font-family="IBM Plex Mono,monospace" font-size="13" font-weight="700" '
            f'fill="{color}" style="font-variant-numeric:tabular-nums;">{final}</text>'
            f'<text x="70" y="13" font-family="IBM Plex Mono,monospace" font-size="11" font-weight="700" '
            f'fill="{delta_color}" style="font-variant-numeric:tabular-nums;">{escape(delta_text)}</text>'
            f'</g>'
        )

    # Axis labels
    x_labels = "".join(
        f'<text x="{x_for(i):.1f}" y="{pad_t + chart_h + 18:.1f}" text-anchor="middle" '
        f'font-family="IBM Plex Mono,monospace" font-size="11" fill="{PALETTE["rule"]}" '
        f'style="font-variant-numeric:tabular-nums;">{escape(w)}</text>'
        for i, w in enumerate(weeks)
    )
    y_ticks = "".join(
        f'<text x="{pad_l - 12:.1f}" y="{y_for(t):.1f}" text-anchor="end" '
        f'font-family="IBM Plex Mono,monospace" font-size="11" fill="{PALETTE["rule"]}" '
        f'style="font-variant-numeric:tabular-nums;">{t}</text>'
        for t in range(y_min, y_max + 1, 10)
    )

    return f"""
    <svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Fanbase Mood Index 10-week trajectory" class="hub-mood-chart">
      {reference_svg}
      {''.join(lines_svg)}
      {''.join(legend_svg)}
      {x_labels}
      {y_ticks}
    </svg>
    """


def render_mood_index_section(issue: dict[str, Any]) -> str:
    chart = (
        _render_retro_cover_art_svg({**issue, "retro_title": "Mood Index Seed"})
        if issue.get("is_retro")
        else _render_mood_index_chart_svg()
    )
    methodology = _issue_methodology(
        issue,
        "mood_index",
        (
            "n = 2.4M conversations",
            "133 FBS fanbases",
            "bot-filtered",
            f"updated {escape_or_dash(issue.get('issue_date'))}",
        ),
    )
    source = _section_source(issue=issue)
    dek = str(
        issue.get("mood_index_dek")
        or "Confidence scores derived from 2.4M fan conversations. Zero is despair. One hundred is championship certainty."
    )
    badge = render_provenance_badge(source) if issue.get("is_retro") else ""
    return f"""
    <section id="sec-01" class="hub-section hub-section-paper"{_section_attr(source) if issue.get("is_retro") else ""}>
      <div class="hub-container">
        {render_section_eyebrow("N\u00b0 01", "The Signature Chart")}
        <h2 class="hub-display-l">The Fanbase Mood Index {badge}</h2>
        <p class="hub-dek">{escape(dek)}</p>
        <div class="hub-chart-wrap">{chart}</div>
        <p class="hub-caption">The historically confident fanbases sit at their lowest mark of the decade while Oregon quietly ascends.</p>
        {methodology}
      </div>
    </section>
    """


def escape_or_dash(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "\u2014"


# ---------------------------------------------------------------------------
# N\u00b0 02 \u2014 The Ticker (Mood movers)
# ---------------------------------------------------------------------------


def render_mood_ticker_section(ticker: dict[str, list[dict[str, Any]]], issue: dict[str, Any] | None = None) -> str:
    gainers = ticker.get("gainers") or []
    losers = ticker.get("losers") or []
    all_items = gainers + losers  # gainers first, losers second — 10 total
    is_retro = bool((issue or {}).get("is_retro"))
    source = _section_source(all_items, issue=issue) if is_retro else "computed"
    pills = "".join(_render_ticker_pill(row, show_badge=is_retro) for row in all_items)
    _is_off = is_offseason(date.today(), db=None)
    methodology = _issue_methodology(
        issue or {},
        "mood_ticker",
        (
            "n = 340K conversations over 7d",
            "bot-filtered",
            "updated this offseason" if _is_off else "updated this week",
        ),
    )
    badge = render_provenance_badge(source) if is_retro else ""
    _ticker_h2 = "The Offseason's Biggest Mood Movers" if _is_off else "This Week&rsquo;s Biggest Mood Movers"
    return f"""
    <section id="sec-02" class="hub-section hub-section-paper"{_section_attr(source) if is_retro else ""}>
      <div class="hub-container">
        {render_section_eyebrow("N\u00b0 02", "The Ticker")}
        <h2 class="hub-display-l">{_ticker_h2} {badge}</h2>
        <p class="hub-dek">Ten fanbases whose belief shifted hardest in the last seven days.</p>
        <div class="hub-ticker-grid">{pills}</div>
        <p class="hub-caption">The top five are gaining on coach news; the bottom five are losing on a single press conference each.</p>
        {methodology}
      </div>
    </section>
    """


def _render_ticker_pill(row: dict[str, Any], *, show_badge: bool = False) -> str:
    slug = str(row.get("slug") or "")
    delta = int(row.get("delta_from_prev_week") or 0)
    mood_score = int(row.get("mood_score") or 0)
    cause = str(row.get("top_cause_label") or "")
    meta = team_color(slug)
    delta_class = "hub-delta-pos" if delta > 0 else "hub-delta-neg" if delta < 0 else "hub-delta-zero"
    delta_text = f"{delta:+d}" if delta != 0 else "0"
    badge = render_provenance_badge(_row_source(row)) if show_badge else ""
    return f"""
    <article class="ticker-pill">
      <div class="hub-chip hub-chip-md" style="background:{meta['primary']};">{escape(meta['abbr'])}</div>
      <div class="ticker-pill-abbr">{escape(meta['abbr'])}</div>
      <div class="ticker-pill-score">{mood_score} {badge}</div>
      <div class="ticker-pill-delta {delta_class}">{escape(delta_text)}</div>
      <div class="ticker-pill-cause">&middot; {escape(cause)}</div>
    </article>
    """


# ---------------------------------------------------------------------------
# N\u00b0 03 \u2014 Hype vs Reality scatter (dark section)
# ---------------------------------------------------------------------------


HYPE_VS_REALITY: list[dict[str, Any]] = [
    {"slug": "georgia",       "hype": 95, "reality": 93, "abbr": "UGA",  "color": "#BA0C2F"},
    {"slug": "texas",         "hype": 89, "reality": 87, "abbr": "TEX",  "color": "#BF5700"},
    {"slug": "ohio-state",    "hype": 92, "reality": 88, "abbr": "OSU",  "color": "#BB0000"},
    {"slug": "oregon",        "hype": 86, "reality": 83, "abbr": "ORE",  "color": "#007030"},
    {"slug": "alabama",       "hype": 84, "reality": 78, "abbr": "ALA",  "color": "#9E1B32"},
    {"slug": "notre-dame",    "hype": 79, "reality": 68, "abbr": "ND",   "color": "#0C2340"},
    {"slug": "texas-am",      "hype": 75, "reality": 61, "abbr": "A&M",  "color": "#500000"},
    {"slug": "nebraska",      "hype": 72, "reality": 48, "abbr": "NEB",  "color": "#E41C38"},
    {"slug": "colorado",      "hype": 68, "reality": 54, "abbr": "CU",   "color": "#CFB87C"},
    {"slug": "michigan",      "hype": 61, "reality": 74, "abbr": "MICH", "color": "#00274C"},
    {"slug": "penn-state",    "hype": 64, "reality": 71, "abbr": "PSU",  "color": "#041E42"},
    {"slug": "usc",           "hype": 70, "reality": 65, "abbr": "USC",  "color": "#990000"},
    {"slug": "lsu",           "hype": 77, "reality": 75, "abbr": "LSU",  "color": "#461D7C"},
    {"slug": "tennessee",     "hype": 81, "reality": 79, "abbr": "TEN",  "color": "#FF8200"},
    {"slug": "florida-state", "hype": 73, "reality": 64, "abbr": "FSU",  "color": "#782F40"},
    {"slug": "clemson",       "hype": 78, "reality": 77, "abbr": "CLEM", "color": "#F56600"},
]


def _render_hype_scatter_svg() -> str:
    size = 600
    pad = 60
    chart = size - 2 * pad
    x_min, x_max = 40, 100

    def xy(reality: float, hype: float) -> tuple[float, float]:
        x = pad + ((reality - x_min) / (x_max - x_min)) * chart
        y = pad + (1 - (hype - x_min) / (x_max - x_min)) * chart
        return x, y

    # Diagonal reference
    x1, y1 = xy(x_min, x_min)
    x2, y2 = xy(x_max, x_max)
    diagonal = (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{PALETTE["ink_muted"]}" stroke-width="1" stroke-dasharray="4 4"/>'
    )

    # Quadrant watermarks (scaled to ~85% to stay inside bounds — Phase 5)
    quadrants = [
        ("DELUSIONAL",    pad + 10,              pad + 40,              "start"),
        ("JUSTIFIED",     pad + chart - 10,      pad + 40,              "end"),
        ("REALISTIC",     pad + 10,              pad + chart - 10,      "start"),
        ("SLEEPING GIANT", pad + chart - 10,     pad + chart - 10,      "end"),
    ]
    watermark_svg = ""
    for label, wx, wy, anchor in quadrants:
        watermark_svg += (
            f'<text x="{wx:.1f}" y="{wy:.1f}" text-anchor="{anchor}" '
            f'font-family="Bebas Neue,Impact,sans-serif" font-size="56" '
            f'fill="{PALETTE["paper"]}" fill-opacity="0.09" letter-spacing="0.04em">{escape(label)}</text>'
        )

    # Defs: team-specific textures + chit typography rule.
    defs_svg = (
        '<defs>'
        f'{_build_texture_defs(TEAM_COLOR_BY_SLUG, PALETTE)}'
        '<style>.chit text{font-variant-numeric:tabular-nums;}</style>'
        '</defs>'
    )

    # Plot points (two-tone chit; texture fill on color-collision overrides).
    outer_r, inner_r, halo_r = 14, 10, 24
    annotated_slugs = {"nebraska", "michigan"}

    # Pre-compute chit centers so we can detect collisions for leader-line labels.
    centers: list[tuple[float, float]] = [
        xy(float(t["reality"]), float(t["hype"])) for t in HYPE_VS_REALITY
    ]
    collision_threshold = 2.2 * outer_r
    offset_label_idx: set[int] = set()
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            dx = centers[i][0] - centers[j][0]
            dy = centers[i][1] - centers[j][1]
            if (dx * dx + dy * dy) ** 0.5 < collision_threshold:
                offset_label_idx.add(j)

    chips_svg: list[str] = []
    for idx, team in enumerate(HYPE_VS_REALITY):
        slug = str(team["slug"])
        x, y = centers[idx]
        info = TEAM_COLOR_BY_SLUG.get(slug, {})
        variant = info.get("texture")
        outer_fill = f"url(#tex-{variant}-{slug})" if variant else team["color"]
        word_color = _ink_for(team["color"])
        halo = (
            f'<circle cx="0" cy="0" r="{halo_r}" fill="none" '
            f'stroke="{PALETTE["gold"]}" stroke-width="1" opacity="0.35"/>'
            if slug in annotated_slugs else ""
        )
        if idx in offset_label_idx:
            wordmark = (
                f'<line x1="0" y1="0" x2="{outer_r + 6}" y2="-{outer_r + 6}" '
                f'stroke="{PALETTE["rule"]}" stroke-width="0.75"/>'
                f'<text x="{outer_r + 8}" y="-{outer_r + 4}" text-anchor="start" '
                f'font-family="IBM Plex Mono,monospace" font-size="9" font-weight="700" '
                f'fill="{PALETTE["paper"]}" letter-spacing="0.04em">{escape(team["abbr"])}</text>'
            )
        else:
            wordmark = (
                f'<text x="0" y="3" text-anchor="middle" '
                f'font-family="IBM Plex Mono,monospace" font-size="9" font-weight="700" '
                f'fill="{word_color}" letter-spacing="0.04em">{escape(team["abbr"])}</text>'
            )
        chips_svg.append(
            f'<g class="chit" transform="translate({x:.1f},{y:.1f})">'
            f'<title>{escape(slug)} \u2014 hype {int(team["hype"])}, reality {int(team["reality"])}</title>'
            f'{halo}'
            f'<circle cx="0" cy="0" r="{outer_r}" fill="{outer_fill}" '
            f'stroke="{PALETTE["paper"]}" stroke-width="1.5"/>'
            f'<circle cx="0" cy="0" r="{inner_r}" fill="{PALETTE["paper"]}" fill-opacity="0.12"/>'
            f'{wordmark}'
            f'</g>'
        )

    # Annotations (short form per Phase 5)
    neb_x, neb_y = xy(48, 72)
    mich_x, mich_y = xy(74, 61)
    annotations = (
        f'<line x1="{neb_x:.1f}" y1="{neb_y:.1f}" x2="{pad + 70:.1f}" y2="{pad + 90:.1f}" '
        f'stroke="{PALETTE["rule"]}" stroke-width="1"/>'
        f'<text x="{pad + 6:.1f}" y="{pad + 110:.1f}" '
        f'font-family="Source Serif 4,serif" font-style="italic" font-size="12" '
        f'fill="{PALETTE["paper"]}">Nebraska &mdash; peak delusion.</text>'
        f'<line x1="{mich_x:.1f}" y1="{mich_y:.1f}" x2="{pad + chart - 90:.1f}" y2="{pad + chart - 30:.1f}" '
        f'stroke="{PALETTE["rule"]}" stroke-width="1"/>'
        f'<text x="{pad + chart - 160:.1f}" y="{pad + chart - 12:.1f}" '
        f'font-family="Source Serif 4,serif" font-style="italic" font-size="12" '
        f'fill="{PALETTE["paper"]}">Michigan &mdash; underrated by its own.</text>'
    )

    # Y axis corner caption (per Phase 5: replace rotated axis title)
    axis_caption = (
        f'<text x="{pad:.1f}" y="{pad - 26:.1f}" '
        f'font-family="IBM Plex Mono,monospace" font-size="10" fill="{PALETTE["rule"]}">Y: Fan Hype \u00b7 X: Model Reality</text>'
    )

    return f"""
    <svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Hype vs Reality scatter" class="hub-hype-chart">
      {defs_svg}
      {watermark_svg}
      {diagonal}
      {''.join(chips_svg)}
      {annotations}
      {axis_caption}
    </svg>
    """


def render_hype_vs_reality_section(issue: dict[str, Any] | None = None) -> str:
    issue_data = issue or {}
    is_retro = bool(issue_data.get("is_retro"))
    chart = (
        _render_retro_cover_art_svg({**issue_data, "retro_title": "Hype Reality Seed"})
        if is_retro
        else _render_hype_scatter_svg()
    )
    source = _section_source(issue=issue_data) if is_retro else "computed"
    methodology = _issue_methodology(
        issue_data,
        "hype_reality",
        (
            "n = 2.4M conversations",
            "hype from sentiment",
            "reality from model",
            "updated this offseason" if is_offseason(date.today(), db=None) else "updated this week",
        ),
    )
    badge = render_provenance_badge(source) if is_retro else ""
    return f"""
    <section id="sec-03" class="hub-section hub-section-dark"{_section_attr(source) if is_retro else ""}>
      <div class="hub-container">
        {render_section_eyebrow("N\u00b0 03", "The Matrix")}
        <h2 class="hub-display-l hub-display-light">Hype vs Reality {badge}</h2>
        <p class="hub-dek hub-dek-light">Fan optimism plotted against model strength. The delusional live in the upper-left.</p>
        <div class="hub-chart-wrap hub-chart-dark">{chart}</div>
        <p class="hub-caption hub-caption-light">The diagonal runs from despair to destiny &mdash; everything north is wishfulness; everything south is quiet strength.</p>
        {methodology}
      </div>
    </section>
    """


# ---------------------------------------------------------------------------
# N\u00b0 04 \u2014 Taxonomy (18 archetypes + 8 modifiers)
# ---------------------------------------------------------------------------


def render_taxonomy_section(taxonomy_rows: list[dict[str, Any]], modifier_rows: list[dict[str, Any]]) -> str:
    cards = "".join(_render_archetype_card(row) for row in taxonomy_rows)
    modifier_strip = _render_modifier_strip(modifier_rows)
    return f"""
    <section id="sec-04" class="hub-section hub-section-paper">
      <div class="hub-container">
        {render_section_eyebrow("N\u00b0 04", "The Taxonomy")}
        <h2 class="hub-display-l">The eighteen fanbases of college football</h2>
        <p class="hub-dek">Every FBS fanbase sorts into one of eighteen primary archetypes (any of eight modifiers). Classification is probabilistic; primary archetype shown, secondary in parentheses.</p>
        <div class="hub-taxonomy-grid">{cards}</div>
        {modifier_strip}
      </div>
    </section>
    """


def _render_archetype_card(row: dict[str, Any]) -> str:
    from cfb_rankings.illustrations import totem_url
    top_teams = row.get("top_teams") or []
    team_chips_html = "".join(
        f'<span class="hub-team-chip-row">'
        f'{render_team_chip(str(team["slug"]), size="sm")}'
        f' <span class="hub-chip-match">{int(round(float(team["confidence"]) * 100))}%</span>'
        f'</span>'
        for team in top_teams
    )
    signature_phrase = str(row.get("signature_phrase") or "")
    sparkline = _render_archetype_migration_sparkline(row.get("top_teams") or [])
    # Tier-1 art: prepend the archetype's totem PNG (80px chip) when one
    # exists for this slug. Missing-totem archetypes degrade gracefully
    # to text-only headers. See illustrations.py + the visual concept
    # doc Tier-1 §1.1 for the per-archetype totem inventory.
    archetype_slug = str(row.get("slug") or "")
    totem_src = totem_url(archetype_slug, size=80)
    totem_html = ""
    if totem_src:
        totem_html = (
            f'<img class="archetype-card-totem" src="{escape(totem_src)}" '
            f'alt="" width="48" height="48" '
            f'loading="lazy" decoding="async" '
            f'style="display:block;margin-bottom:8px;">'
        )
    return f"""
    <article class="archetype-card">
      {totem_html}<h3 class="archetype-card-title">{escape(str(row['name']))}</h3>
      <p class="archetype-card-desc">{escape(str(row.get('description') or ''))}</p>
      <div class="archetype-card-teams">{team_chips_html}</div>
      <div class="archetype-card-phrase">
        <div class="archetype-card-phrase-label">Signature Phrase</div>
        <div class="archetype-card-phrase-body">Primary: <span class="archetype-signature">{signature_phrase}</span></div>
      </div>
      <div class="archetype-card-modifiers">
        <div class="archetype-card-modifier-label">Modifiers</div>
        <div class="archetype-card-modifier-row">
          <span class="modifier-chip"><span class="hub-gold-dot">\u00b7</span> Entrenched</span>
        </div>
      </div>
      <div class="archetype-card-spark">{sparkline}</div>
    </article>
    """


def _render_archetype_migration_sparkline(top_teams: list[dict[str, Any]]) -> str:
    """Render a tiny 6-point sparkline showing the aggregate membership count over 6 weeks.

    For v1 this is a synthetic flat line at the current count \u2014 real weekly history
    will plug in once the classifier runs weekly.
    """

    count = max(1, len(top_teams))
    width, height = 200, 40
    pad = 4
    points = [count, count, count, count, count, count]
    max_count = max(points)

    def x_for(i: int) -> float:
        return pad + (i / (len(points) - 1)) * (width - 2 * pad)

    def y_for(v: int) -> float:
        return (height - pad) - (v / max_count) * (height - 2 * pad - 10)

    path_d = "M " + " L ".join(f"{x_for(i):.1f},{y_for(v):.1f}" for i, v in enumerate(points))
    dots = "".join(f'<circle cx="{x_for(i):.1f}" cy="{y_for(v):.1f}" r="2" fill="{PALETTE["ink_muted"]}"/>' for i, v in enumerate(points))
    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" class="archetype-spark">'
        f'<path d="{path_d}" stroke="{PALETTE["rule"]}" stroke-width="1.5" fill="none"/>'
        f'{dots}'
        f'</svg>'
    )


def _render_modifier_strip(modifiers: list[dict[str, Any]]) -> str:
    from cfb_rankings.illustrations import modifier_url
    chip_parts = []
    for m in modifiers:
        slug = str(m.get("slug") or "")
        name = str(m.get("name") or "")
        glyph_src = modifier_url(slug, size=48)
        if glyph_src:
            glyph_html = (
                f'<img class="modifier-chip__glyph" src="{escape(glyph_src)}" '
                f'alt="" width="20" height="20" '
                f'loading="lazy" decoding="async" '
                f'style="vertical-align:middle;margin-right:6px;">'
            )
        else:
            glyph_html = '<span class="hub-gold-dot">\u00b7</span> '
        chip_parts.append(
            f'<span class="modifier-chip">{glyph_html}{escape(name)}</span>'
        )
    chips = "".join(chip_parts)
    return f"""
    <div class="hub-modifier-strip">
      <div class="hub-modifier-row">{chips}</div>
      <p class="hub-caption hub-caption-center">{"Every fanbase carries one primary archetype and one of eight modifiers." if is_offseason(date.today(), db=None) else "Every fanbase carries one primary archetype and, this week, one of eight modifiers."}</p>
    </div>
    """


# ---------------------------------------------------------------------------
# N\u00b0 05 \u2014 Rivalry Obsession Matrix
# ---------------------------------------------------------------------------


def render_rivalry_section(rivalries: list[dict[str, Any]], issue: dict[str, Any] | None = None) -> str:
    is_retro = bool((issue or {}).get("is_retro"))
    source = _section_source(rivalries, issue=issue) if is_retro else "computed"
    cells = "".join(_render_rivalry_cell(row, show_badge=is_retro) for row in rivalries)
    methodology = (
        _issue_methodology(
            issue or {},
            "rivalry",
            ("ratio from pair mentions", "bot-filtered", "updated this offseason" if is_offseason(date.today(), db=None) else "updated this week"),
        )
        if is_retro
        else ""
    )
    badge = render_provenance_badge(source) if is_retro else ""
    return f"""
    <section id="sec-05" class="hub-section hub-section-paper"{_section_attr(source) if is_retro else ""}>
      <div class="hub-container">
        {render_section_eyebrow("N\u00b0 05", "The Rivalry")}
        <h2 class="hub-display-l">Who&rsquo;s More Obsessed With Whom {badge}</h2>
        <p class="hub-dek">For every rivalry, one fanbase mentions the other more than they get mentioned back. The ratio is the tell. When it flips, something has changed.</p>
        <div class="hub-rivalry-grid">{cells}</div>
        <p class="hub-caption hub-caption-center">The ratio is the relationship. An asymmetric ratio means the relationship itself is asymmetric &mdash; one side still treats it as a rivalry, the other has moved on.</p>
        {methodology}
      </div>
    </section>
    """


def _render_rivalry_cell(row: dict[str, Any], *, show_badge: bool = False) -> str:
    a_slug = str(row.get("team_a_slug") or "")
    b_slug = str(row.get("team_b_slug") or "")
    leaning = int(row.get("leaning_team") or 0)
    ratio = float(row.get("ratio_dominant") or 1.0)
    a_meta = team_color(a_slug)
    b_meta = team_color(b_slug)
    total = ratio + 1.0
    if leaning == 1:
        a_width = (ratio / total) * 100
    elif leaning == 2:
        a_width = (1.0 / total) * 100
    else:
        a_width = 50.0
    b_width = 100.0 - a_width
    name = str(row.get("rivalry_name") or "")
    take = str(row.get("take") or "")
    badge = render_provenance_badge(_row_source(row)) if show_badge else ""
    return f"""
    <article class="rivalry-cell">
      <div class="rivalry-cell-name">{escape(name)}</div>
      <div class="rivalry-cell-chips">
        {render_team_chip(a_slug, size='sm')}
        {render_team_chip(b_slug, size='sm')}
      </div>
      <div class="rivalry-cell-bar">
        <div class="rivalry-cell-bar-a" style="width:{a_width:.1f}%;background:{a_meta['primary']};"></div>
        <div class="rivalry-cell-bar-b" style="width:{b_width:.1f}%;background:{b_meta['primary']};"></div>
      </div>
      <div class="rivalry-cell-ratio">{ratio:.1f}\u00d7 ratio {badge}</div>
      <p class="rivalry-cell-take">{take}</p>
    </article>
    """


# ---------------------------------------------------------------------------
# N\u00b0 06 \u2014 Lexicon of the Week
# ---------------------------------------------------------------------------


def render_lexicon_section(lexicon: dict[str, Any] | None, issue: dict[str, Any] | None = None) -> str:
    is_retro = bool((issue or {}).get("is_retro"))
    if not lexicon:
        return f"""
        <section id="sec-06" class="hub-section hub-section-paper"{_section_attr("editorial") if is_retro else ""}>
          <div class="hub-container">
            {render_section_eyebrow("N\u00b0 06", "The Lexicon")}
            <h2 class="hub-display-l">{"No featured phrase from the latest signal." if is_offseason(date.today(), db=None) else "No featured phrase this week."}</h2>
            <p class="hub-dek">The Lexicon of the Week lights up when a single phrase clears the spike threshold (+100% WoW), the volume floor (500+ mentions), and the sample-quote floor (3+ quotable uses).</p>
          </div>
        </section>
        """
    paragraphs = lexicon.get("narrative_paragraphs") or []
    paragraphs_html = "".join(f'<p>{escape(p)}</p>' for p in paragraphs)
    sparkline = _render_lexicon_sparkline(lexicon.get("trend") or [])
    quotes_html = "".join(_render_lexicon_quote(q) for q in (lexicon.get("sample_quotes") or []))
    source = _section_source([lexicon], issue=issue) if is_retro else "computed"
    methodology = _issue_methodology(
        issue or {},
        "lexicon",
        (
            f"Source: {int(lexicon.get('mention_count') or 0):,} {escape_or_dash(lexicon.get('related_team_name'))} fan conversations",
            escape_or_dash(lexicon.get("origin_community")),
            "r/CFB",
            "Eleven Warriors",
            "Twitter/X",
            "Rivals forums",
            "7d",
        ),
    )
    badge = render_provenance_badge(source) if is_retro else ""
    return f"""
    <section id="sec-06" class="hub-section hub-section-paper"{_section_attr(source) if is_retro else ""}>
      <div class="hub-container">
        {render_section_eyebrow("N\u00b0 06", "The Lexicon")}
        <h2 class="hub-display-l">&ldquo;{escape(str(lexicon.get('phrase') or ''))}&rdquo; {badge}</h2>
        <p class="hub-dek">{"The phrase that recently spiked in " + escape_or_dash(lexicon.get('related_team_name')) + " fan conversations, and what it means." if is_offseason(date.today(), db=None) else "The phrase that spiked in " + escape_or_dash(lexicon.get('related_team_name')) + " fan conversations this week, and what it means."}</p>
        <article class="lexicon-feature">
          <div class="lexicon-feature-left">{paragraphs_html}</div>
          <div class="lexicon-feature-right">
            <div class="lexicon-feature-spark">{sparkline}</div>
            <div class="lexicon-feature-quotes">{quotes_html}</div>
          </div>
        </article>
        {methodology}
      </div>
    </section>
    """


def _render_lexicon_sparkline(trend: list[dict[str, Any]]) -> str:
    if not trend:
        return ""
    width, height = 440, 140
    pad_l, pad_r, pad_t, pad_b = 14, 14, 10, 30
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    max_freq = max(int(p.get("frequency") or 0) for p in trend) or 1

    def x_for(i: int) -> float:
        return pad_l + (i / max(1, len(trend) - 1)) * chart_w

    def y_for(freq: int) -> float:
        return pad_t + (1 - (freq / max_freq)) * chart_h

    points = [(str(p.get("week") or ""), int(p.get("frequency") or 0)) for p in trend]
    path_d = "M " + " L ".join(f"{x_for(i):.1f},{y_for(v):.1f}" for i, (_, v) in enumerate(points))
    dots = "".join(f'<circle cx="{x_for(i):.1f}" cy="{y_for(v):.1f}" r="4" fill="#BB0000"/>' for i, (_, v) in enumerate(points))
    labels = "".join(
        f'<text x="{x_for(i):.1f}" y="{pad_t + chart_h + 18:.1f}" text-anchor="middle" '
        f'font-family="IBM Plex Mono,monospace" font-size="10" fill="{PALETTE["rule"]}">{escape(w)}</text>'
        for i, (w, _) in enumerate(points)
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" class="lexicon-spark">'
        f'<path d="{path_d}" stroke="#BB0000" stroke-width="2.5" fill="none"/>'
        f'{dots}{labels}'
        f'</svg>'
    )


def _render_lexicon_quote(quote: dict[str, Any]) -> str:
    text = str(quote.get("text") or "")
    source = str(quote.get("source") or "")
    dt = str(quote.get("date") or "")
    return f"""
    <div class="lexicon-quote">
      <p class="lexicon-quote-text">&ldquo;{escape(text)}&rdquo;</p>
      <div class="lexicon-quote-source">{escape(source)}, {escape(dt)}</div>
    </div>
    """


# ---------------------------------------------------------------------------
# N\u00b0 07 \u2014 Index Cards
# ---------------------------------------------------------------------------


def render_index_cards_section(issue: dict[str, Any]) -> str:
    cards = issue.get("cards") or ISSUE_047["cards"]
    is_retro = bool(issue.get("is_retro"))
    source = _section_source(cards, issue=issue) if is_retro else "computed"
    cards_html = "".join(
        _render_index_card(card, i, issue["issue_number"], issue["issue_date"], show_badge=is_retro)
        for i, card in enumerate(cards)
    )
    return f"""
    <section id="sec-07" class="hub-section hub-section-paper"{_section_attr(source) if is_retro else ""}>
      <div class="hub-container">
        {render_section_eyebrow("N\u00b0 07", f"The Index Cards \u00b7 {issue['issue_number']}")}
        <h2 class="hub-display-l">{"Latest cards" if is_offseason(date.today(), db=None) else "This week&rsquo;s cards"}</h2>
        <div class="hub-index-cards">{cards_html}</div>
        <p class="hub-caption hub-caption-center">All Index Cards are collectible. <a href="#">{"Save the latest cards" if is_offseason(date.today(), db=None) else "Save this week&rsquo;s cards"}</a> <span class="hub-gold-dot">\u00b7</span> <a href="/archive/">archive of all 47 issues &rarr;</a></p>
      </div>
    </section>
    """


def _render_index_card(
    card: dict[str, Any],
    index: int,
    issue_number: str,
    issue_date: str,
    *,
    show_badge: bool = False,
) -> str:
    team_abbr = str(card.get("team_abbr") or "")
    team_color_hex = str(card.get("team_color") or PALETTE["ink"])
    badge = render_provenance_badge(_row_source(card)) if show_badge else ""
    return f"""
    <article class="index-card" style="--card-accent:{team_color_hex};">
      <div class="index-card-accent" aria-hidden="true"></div>
      <div class="index-card-inner">
        <div class="index-card-header">THE CFB INDEX <span class="hub-gold-dot">\u00b7</span> {escape(issue_number)} <span class="hub-gold-dot">\u00b7</span> {escape(issue_date.upper())}</div>
        <div class="index-card-header">Index Card <span class="hub-gold-dot">\u00b7</span> {escape(issue_number)} <span class="hub-gold-dot">\u00b7</span> {index + 1} of 3</div>
        <h3 class="index-card-headline">{escape(str(card.get('headline') or ''))}</h3>
        <div class="index-card-stat">{escape(str(card.get('stat_number') or ''))} {badge}</div>
        <p class="index-card-label">{escape(str(card.get('stat_label') or ''))}</p>
        <div class="index-card-footer">
          <div class="index-card-punchline">{escape(str(card.get('punchline') or ''))}</div>
          <div class="index-card-chip"><span class="hub-chip hub-chip-md" style="background:{team_color_hex};">{escape(team_abbr)}</span></div>
        </div>
      </div>
    </article>
    """


# ---------------------------------------------------------------------------
# N\u00b0 08 \u2014 Commiseration block (dark)
# ---------------------------------------------------------------------------


def render_commiseration_section(issue: dict[str, Any]) -> str:
    body = str(issue.get("commiseration_body") or "")
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    paragraphs_html = "".join(f'<p>{escape(p)}</p>' for p in paragraphs)
    eyebrow = str(issue.get("commiseration_eyebrow") or "")
    return f"""
    <section id="sec-08" class="hub-section hub-section-dark hub-commiseration">
      <div class="hub-commiseration-inner">
        <div class="hub-eyebrow hub-eyebrow-light">N\u00b0 08 <span class="hub-gold-dot">\u00b7</span> {escape(eyebrow)}</div>
        <div class="hub-commiseration-body">
          {paragraphs_html}
          <p class="hub-commiseration-signoff">&mdash; the staff <span class="hub-gold-dot">\u00b7</span> {escape(str(issue['issue_date']))}</p>
        </div>
      </div>
    </section>
    """


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------


def render_hub_footer(issue: dict[str, Any]) -> str:
    return f"""
    <footer class="hub-footer">
      <div class="hub-container hub-footer-inner">
        <div class="hub-footer-brand">
          <div class="hub-footer-wordmark">THE CFB INDEX</div>
          <p class="hub-footer-tagline">Transforming college football conversations into intelligence.</p>
        </div>
        <div class="hub-footer-cols">
          <div>
            <div class="hub-footer-col-title">Publication</div>
            <a href="#">Subscribe \u00b7 Wednesdays 9AM ET \u2192</a>
            <a href="/archive/">Archive</a>
            <a href="/about-model/">The Model</a>
            <a href="/methodology/">Methodology</a>
          </div>
          <div>
            <div class="hub-footer-col-title">Explore</div>
            <a href="/rankings/">Rankings</a>
            <a href="/teams/">Teams</a>
            <a href="/players/">Players</a>
            <a href="/matchups/">Matchups</a>
            <a href="./">Hub</a>
          </div>
          <div>
            <div class="hub-footer-col-title">Legal</div>
            <a href="/attributions/">Attributions</a>
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
          </div>
        </div>
        <div class="hub-footer-rule"></div>
        <div class="hub-footer-meta">
          <div>
            <span>{escape(issue['issue_number'])}</span>
            <span class="hub-gold-dot">\u00b7</span>
            <span>{escape(issue['issue_date'])}</span>
            <span class="hub-gold-dot">\u00b7</span>
            <span>Next Issue Wednesday 9am ET</span>
            <span class="hub-pulse" aria-hidden="true"></span>
          </div>
          <div class="hub-footer-meta-small">
            133 FBS fanbases <span class="hub-gold-dot">\u00b7</span> 10 FBS conferences <span class="hub-gold-dot">\u00b7</span> 3,828 games since 2014
          </div>
          <div class="hub-footer-meta-small">
            Model: {FRIENDLY_MODEL_LABEL} <span class="hub-gold-dot">\u00b7</span> last cut {escape(issue['issue_date'])} <span class="hub-gold-dot">\u00b7</span> <a href="/about-model/">changelog \u2192</a>
          </div>
        </div>
      </div>
    </footer>
    """


# ---------------------------------------------------------------------------
# Top-level assembly
# ---------------------------------------------------------------------------


def render_hub_page_html(data: dict[str, Any]) -> str:
    issue = data["issue"]
    mood_ticker = data["mood_ticker"]
    rivalries = data["rivalries"]
    lexicon = data.get("lexicon")
    taxonomy = data["taxonomy"]
    modifier_rows = data["modifiers"]
    is_retro = bool(issue.get("is_retro") or data.get("is_retro"))

    css = _hub_css()
    masthead = render_masthead(
        issue_number=issue["issue_number"],
        model_week=issue.get("model_week"),
        issue_date=issue["issue_date"],
        updated_label=f"Updated {issue['issue_date']}",
    )
    nav = render_nav(
        issue["issue_number"],
        prev_issue=issue.get("prev_issue") or "N\u00b0 046",
        next_issue=issue.get("next_issue"),
        site_prefix=str(data.get("site_prefix") or "../"),
        retro=is_retro,
    )
    head_extra = str(data.get("head_extra") or "")
    body_extra = ' data-retro="true"' if is_retro else ""
    body_class = "hub-body hub-body-retro" if is_retro else "hub-body"
    retro_banner = str(issue.get("retro_banner_html") or "")

    page_title = f"Fan Intelligence Hub \u00b7 {issue['issue_number']} \u00b7 The CFB Index"
    meta_description = (
        f"{issue['cover_headline']} The Fan Intelligence Hub reads belief, respect, and rivalry heat "
        "across all 133 FBS fanbases."
    )

    # OG + Twitter meta (parallel to PR #99/#103/#104/#105/#106/#107).
    # The Fan Intelligence Hub is a share-bait magazine surface — links
    # to /hub/ should render as full preview cards.
    page_canonical = absolute_url("/hub/")
    og_image_url = absolute_url("/og-image.svg")
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>{escape(page_title)}</title>
    <meta name=\"description\" content=\"{escape(meta_description)}\">
    <link rel=\"canonical\" href=\"{escape(page_canonical, quote=True)}\">
    <meta property=\"og:site_name\" content=\"THE CFB INDEX\">
    <meta property=\"og:type\" content=\"website\">
    <meta property=\"og:url\" content=\"{escape(page_canonical, quote=True)}\">
    <meta property=\"og:title\" content=\"{escape(page_title)}\">
    <meta property=\"og:description\" content=\"{escape(meta_description)}\">
    <meta property=\"og:image\" content=\"{escape(og_image_url, quote=True)}\">
    <meta property=\"og:image:width\" content=\"1200\">
    <meta property=\"og:image:height\" content=\"630\">
    <meta name=\"twitter:card\" content=\"summary_large_image\">
    <meta name=\"twitter:url\" content=\"{escape(page_canonical, quote=True)}\">
    <meta name=\"twitter:title\" content=\"{escape(page_title)}\">
    <meta name=\"twitter:description\" content=\"{escape(meta_description)}\">
    <meta name=\"twitter:image\" content=\"{escape(og_image_url, quote=True)}\">
    {head_extra}
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
    <link href=\"https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:ital,wght@0,400;0,700;1,400&family=Source+Serif+4:ital,wght@0,400;0,700;1,400&display=swap\" rel=\"stylesheet\">
    <style>{css}</style>
  </head>
  <body class=\"{body_class}\"{body_extra}>
    <a class=\"hub-skip\" href=\"#hub-main\">Skip to content</a>
    {masthead}
    {nav}
    {retro_banner}
    <main id=\"hub-main\">
      {render_cover_hero(issue)}
      {render_editor_note(issue)}
      {render_mood_index_section(issue)}
      {render_mood_ticker_section(mood_ticker, issue)}
      {render_hype_vs_reality_section(issue)}
      {render_taxonomy_section(taxonomy, modifier_rows)}
      {render_rivalry_section(rivalries, issue)}
      {render_lexicon_section(lexicon, issue)}
      {render_index_cards_section(issue)}
      {render_commiseration_section(issue)}
    </main>
    {render_hub_footer(issue)}
  </body>
</html>
"""


def fetch_hub_data(db: Database, *, issue_number: str = "N\u00b0 047",
                   week_start: str = "2026-04-22", season_year: int = 2025) -> dict[str, Any]:
    issue_meta = fetch_issue_metadata(db, issue_number)
    if not issue_meta:
        issue_meta = {
            "issue_number": ISSUE_047["issue_number"],
            "issue_date": ISSUE_047["issue_date"],
            "week_start_date": ISSUE_047["week_start_date"],
            "model_week": ISSUE_047["model_week"],
            "cover_headline": ISSUE_047["cover_headline"],
            "cover_dek": ISSUE_047["cover_dek"],
            "cover_chart_caption": ISSUE_047["cover_chart_caption"],
            "editor_note_body": ISSUE_047["editor_note_body"],
            "pull_quote": ISSUE_047["cover_pull_quote"],
            "commiseration_eyebrow": ISSUE_047["commiseration_eyebrow"],
            "commiseration_body": ISSUE_047["commiseration_body"],
            "cards": ISSUE_047["cards"],
            "methodology": {},
        }
    return {
        "issue": issue_meta,
        "mood_ticker": fetch_mood_ticker(db, week_start, top_n=5),
        "rivalries": fetch_rivalry_week(db, week_start),
        "lexicon": fetch_featured_lexicon(db, week_start),
        "taxonomy": fetch_taxonomy_with_teams(db, season_year),
        "modifiers": fetch_modifiers(db),
    }


def build_hub_page(db: Database, output_dir: str | Path = "output/site",
                   issue_number: str = "N\u00b0 047",
                   week_start: str = "2026-04-22",
                   season_year: int = 2025) -> Path:
    hub_dir = Path(output_dir) / "hub"
    hub_dir.mkdir(parents=True, exist_ok=True)
    data = fetch_hub_data(db, issue_number=issue_number, week_start=week_start, season_year=season_year)
    html = render_hub_page_html(data)
    out_path = hub_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Team-page archetype module (Phase 3 + Phase 7)
# ---------------------------------------------------------------------------


def fetch_team_classification(db: Database, team_id: int, season_year: int) -> dict[str, Any] | None:
    row = db.query_one(
        """
        select fc.*, fat.name as archetype_name, fat.description as archetype_description
        from fanbase_classification fc
        left join fanbase_archetype_taxonomy fat
          on fat.kind = 'primary' and fat.slug = fc.primary_archetype_slug
        where fc.team_id = %(team_id)s
          and fc.season_year = %(season_year)s
        order by fc.classified_at desc
        limit 1
        """,
        {"team_id": team_id, "season_year": season_year},
    )
    if not row:
        return None
    try:
        row["modifier_slugs"] = json.loads(row.get("modifier_slugs_json") or "[]")
    except (TypeError, ValueError):
        row["modifier_slugs"] = []
    return row


def fetch_modifier_lookup(db: Database) -> dict[str, dict[str, Any]]:
    rows = db.query_all(
        "select slug, name, description from fanbase_archetype_taxonomy where kind = 'modifier'"
    )
    return {str(r["slug"]): r for r in rows}


def render_team_archetype_module(classification: dict[str, Any] | None,
                                 migration_rows: list[dict[str, Any]] | None,
                                 modifier_lookup: dict[str, dict[str, Any]] | None = None,
                                 hub_prefix: str = "../hub/") -> str:
    """Team-page insert: archetype block with primary, confidence, modifiers, and a 5-season sparkline.

    Used both on team season pages and as the offseason fallback for the Mood Card.
    """

    if not classification:
        return f'''
        <section class="team-archetype-module team-archetype-empty">
          <div class="team-archetype-header">
            <div class="team-archetype-eyebrow">Fanbase Archetype</div>
            <p class="team-archetype-blurb">Classification lights up once this team&rsquo;s season has enough signal.
              Read the full taxonomy at
              <a href="{hub_prefix}#sec-04">The Fan Intelligence Hub</a>.
            </p>
          </div>
        </section>
        '''

    modifier_lookup = modifier_lookup or {}
    modifier_slugs = classification.get("modifier_slugs") or []
    modifier_chip_parts: list[str] = []
    for slug in modifier_slugs:
        display = (modifier_lookup.get(slug) or {}).get("name") or slug.replace("-", " ").title()
        modifier_chip_parts.append(
            '<span class="modifier-chip"><span class="hub-gold-dot">\u00b7</span> '
            + escape(str(display)) + '</span>'
        )
    if modifier_chip_parts:
        modifier_chips = "".join(modifier_chip_parts)
    else:
        modifier_chips = '<span class="team-archetype-empty-row">No weekly modifier this issue.</span>'

    confidence = float(classification.get("primary_confidence") or 0.0)
    confidence_pct = int(round(confidence * 100))
    archetype_name = classification.get("archetype_name") or str(classification.get("primary_archetype_slug") or "").replace("-", " ").title()
    archetype_desc = str(classification.get("archetype_description") or "")
    signature_phrase = str(classification.get("signature_phrase") or "")
    migration_svg = _render_team_migration_sparkline(migration_rows or [])

    return f'''
    <section class="team-archetype-module">
      <div class="team-archetype-header">
        <div class="team-archetype-eyebrow">Fanbase Archetype</div>
        <h3 class="team-archetype-name">{escape(str(archetype_name))}</h3>
        <div class="team-archetype-confidence">Primary: {confidence_pct}% confidence</div>
      </div>
      <p class="team-archetype-desc">{escape(archetype_desc)}</p>
      <div class="team-archetype-phrase">
        <div class="team-archetype-phrase-label">SIGNATURE PHRASE</div>
        <div class="team-archetype-phrase-body">{signature_phrase}</div>
      </div>
      <div class="team-archetype-modifier-block">
        <div class="team-archetype-phrase-label">MODIFIERS</div>
        <div class="team-archetype-modifier-row">{modifier_chips}</div>
      </div>
      <div class="team-archetype-migration">
        <div class="team-archetype-phrase-label">5-Season Migration</div>
        {migration_svg}
      </div>
      <a class="team-archetype-link" href="{hub_prefix}#sec-04">See the full taxonomy \u2192</a>
    </section>
    '''


def _render_team_migration_sparkline(rows: list[dict[str, Any]]) -> str:
    """Render a 5-season sparkline plotting primary_confidence. Falls back to flat line if thin."""

    if not rows:
        rows = [{"season_year": None, "primary_confidence": 0.6}] * 5
    width, height = 280, 56
    pad_l, pad_r, pad_t, pad_b = 8, 8, 8, 18
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    values = [float(r.get("primary_confidence") or 0.6) for r in rows]

    def x_for(i: int) -> float:
        return pad_l + (i / max(1, len(values) - 1)) * chart_w

    def y_for(v: float) -> float:
        return pad_t + (1 - v) * chart_h

    path_d = "M " + " L ".join(f"{x_for(i):.1f},{y_for(v):.1f}" for i, v in enumerate(values))
    dots = "".join(f'<circle cx="{x_for(i):.1f}" cy="{y_for(v):.1f}" r="2.5" fill="{PALETTE["ink_muted"]}"/>' for i, v in enumerate(values))
    labels = "".join(
        f'<text x="{x_for(i):.1f}" y="{pad_t + chart_h + 12:.1f}" text-anchor="middle" '
        f'font-family="IBM Plex Mono,monospace" font-size="9" fill="{PALETTE["rule"]}">{escape(str(r.get("season_year") or ""))}</text>'
        for i, r in enumerate(rows)
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" class="team-archetype-spark">'
        f'<path d="{path_d}" stroke="{PALETTE["rule"]}" stroke-width="1.5" fill="none"/>'
        f'{dots}{labels}'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _hub_css() -> str:
    return """
    :root {
      --paper: #F3EEE4;
      --paper-warm: #E8E1D2;
      --paper-border: #E8E1D2;
      --ink: #0B0F14;
      --ink-muted: #5A5954;
      --rule: #B5AFA3;
      --gold: #E0A300;
      --alert: #B7281D;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; }
    .hub-body {
      background: var(--paper);
      color: var(--ink);
      font-family: 'Source Serif 4', Georgia, 'Times New Roman', serif;
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }
    a { color: inherit; text-decoration: none; }
    a:hover { color: var(--gold); }
    .hub-container { max-width: 1280px; margin: 0 auto; padding: 0 1.5rem; }
    .hub-skip {
      position: absolute; top: -40px; left: 0; background: var(--ink); color: var(--paper);
      padding: .75rem 1rem; font-family: 'IBM Plex Mono', monospace; font-size: .75rem;
      letter-spacing: 0.15em; text-transform: uppercase; z-index: 100;
    }
    .hub-skip:focus { top: 0; }
    .hub-dot, .hub-gold-dot { color: var(--gold); margin: 0 .5em; }
    .hub-pulse {
      display: inline-block; width: 8px; height: 8px; border-radius: 50%;
      background: var(--gold); margin-left: .75rem;
      animation: hub-pulse 2s ease-in-out infinite;
    }
    @keyframes hub-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .4; } }

    /* Masthead */
    .hub-masthead {
      background: var(--ink); color: var(--paper);
      border-bottom: 1px solid #5A5954;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase;
    }
    .hub-masthead-inner { height: 64px; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
    .hub-mast-left, .hub-mast-right { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }

    /* Nav */
    .hub-nav { background: var(--paper); color: var(--ink); border-bottom: 1px solid #5A5954; }
    .hub-nav-inner { height: 80px; display: flex; align-items: center; justify-content: space-between; }
    .hub-nav-left { display: flex; align-items: center; gap: 2rem; }
    .hub-nav-brand { font-family: 'Bebas Neue', Impact, sans-serif; font-size: 1.65rem; letter-spacing: -.01em; }
    .hub-nav-menu { display: flex; align-items: center; gap: 2rem; font-family: 'IBM Plex Mono', monospace; font-size: .825rem; }
    .hub-nav-active { border-bottom: 2px solid var(--gold); padding-bottom: 4px; }
    .hub-nav-subscribe { text-decoration: underline; text-underline-offset: 3px; }
    .hub-nav-chevron { font-family: 'IBM Plex Mono', monospace; font-size: .825rem; }
    .hub-nav-chevron--inert { color: var(--ink-muted, #888); cursor: default; }
    @media (max-width: 900px) { .hub-nav-menu { display: none; } }

    .hub-retro-banner {
      background: #FFF4CF; color: var(--ink); border-bottom: 1px solid rgba(224,163,0,.45);
      font-family: 'IBM Plex Mono', monospace; font-size: .78rem; letter-spacing: .08em;
      text-transform: uppercase; text-align: center; padding: .75rem 1rem;
    }

    /* Eyebrow */
    .hub-eyebrow {
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 1.25rem;
    }
    .hub-eyebrow-light { color: var(--rule); }
    .hub-eyebrow-sm { font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink-muted); margin-bottom: .75rem; }

    /* Cover */
    .hub-cover { background: var(--paper); border-bottom: 1px solid #5A5954; }
    .hub-cover .hub-container { padding-top: 5rem; padding-bottom: 5rem; }
    .hub-cover-grid { display: grid; grid-template-columns: 60% 40%; gap: 4rem; }
    @media (max-width: 900px) { .hub-cover-grid { grid-template-columns: 1fr; gap: 2rem; } }
    .hub-display-xl {
      font-family: 'Bebas Neue', Impact, sans-serif;
      font-size: clamp(3.5rem, 9vw, 8rem);
      line-height: 0.95; letter-spacing: -0.01em;
      margin: 0 0 2rem 0; color: var(--ink);
    }
    .hub-display-l {
      font-family: 'Bebas Neue', Impact, sans-serif;
      font-size: clamp(3rem, 6vw, 5rem);
      line-height: 0.95; letter-spacing: -0.005em;
      margin: 0 0 1.5rem 0; color: var(--ink);
    }
    .hub-display-light { color: var(--paper); }
    .hub-dek { font-size: clamp(1.05rem, 2vw, 1.35rem); line-height: 1.45; max-width: 48rem; margin: 0 0 2.5rem 0; }
    .hub-dek-light { color: var(--paper); }
    .hub-byline {
      font-family: 'IBM Plex Mono', monospace; font-size: .82rem;
      letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-muted);
      margin-bottom: 2rem; font-variant-numeric: tabular-nums;
    }
    .hub-pull-quote {
      border-left: 2px solid rgba(11,15,20,0.25); padding: 0 0 0 1.5rem;
      margin: 0; font-family: 'Source Serif 4', Georgia, serif;
      font-style: italic; font-size: 1rem; color: var(--ink-muted);
      line-height: 1.6;
    }
    .hub-cover-chart { margin-bottom: 1rem; }
    .hub-caption { font-family: 'Source Serif 4', Georgia, serif; font-style: italic; color: var(--ink-muted); font-size: 1rem; line-height: 1.55; margin: 0 0 .5rem 0; }
    .hub-caption-light { color: var(--rule); }
    .hub-caption-center { text-align: center; max-width: 48rem; margin: 1rem auto 0 auto; }
    .hub-methodology {
      font-family: 'IBM Plex Mono', monospace; font-size: 10px;
      color: var(--rule); margin-top: .75rem; letter-spacing: .02em;
      font-variant-numeric: tabular-nums;
    }
    .hub-methodology a { border-bottom: 1px dotted currentColor; }
    [data-provenance="editorial"] .hub-methodology,
    [data-provenance="curated"] .hub-methodology {
      border-top: 2px solid rgba(224,163,0,.45); padding-top: .55rem;
    }
    .hub-provenance-badge {
      display: inline-block; vertical-align: middle; margin-left: .45rem; padding: .16rem .42rem;
      border: 1px solid rgba(224,163,0,.55); border-radius: 999px; background: rgba(255,244,207,.82);
      color: #6f4d00; font-family: 'IBM Plex Mono', monospace; font-size: .62rem;
      letter-spacing: .1em; line-height: 1; text-transform: uppercase;
    }
    .hub-section-dark .hub-provenance-badge {
      background: rgba(255,244,207,.95); color: #6f4d00;
    }
    .hub-also-reading {
      background: #FFFFFF; border: 1px solid var(--paper-border); padding: 1rem; margin-top: 1.25rem;
    }
    .hub-also-list {
      font-family: 'Source Serif 4', Georgia, serif; font-size: .95rem; line-height: 1.7;
      display: flex; flex-wrap: wrap; align-items: center; gap: .35rem;
    }

    /* Editor's Note (drop cap + measure) */
    .hub-editor-note { background: var(--paper-warm); border-bottom: 1px solid #5A5954; }
    .hub-editor-inner { max-width: 64ch; margin: 0 auto; padding: 4rem 1.5rem; }
    .hub-editor-body { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.125rem; line-height: 1.65; color: var(--ink); }
    .hub-editor-paragraph::first-letter {
      font-family: 'Bebas Neue', Impact, sans-serif; font-size: 4rem; float: left;
      margin-right: 0.35em; line-height: 0.9; color: var(--ink);
    }
    .hub-editor-signoff { font-style: italic; color: var(--ink-muted); margin-top: 1.5rem; }

    /* Generic sections */
    .hub-section { border-bottom: 1px solid #5A5954; }
    .hub-section .hub-container { padding-top: 5rem; padding-bottom: 5rem; }
    .hub-section-paper { background: var(--paper); color: var(--ink); }
    .hub-section-dark { background: var(--ink); color: var(--paper); }
    .hub-section-dark .hub-display-l { color: var(--paper); }
    .hub-chart-wrap { margin: 1.5rem 0; }
    .hub-chart-dark svg { background: transparent; }
    .hub-mood-chart, .hub-hype-chart, .lexicon-spark, .archetype-spark, .team-archetype-spark { width: 100%; height: auto; }

    /* Ticker */
    .hub-ticker-grid { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 1rem; margin: 1rem 0 2rem; }
    @media (max-width: 1100px) { .hub-ticker-grid { grid-template-columns: repeat(5, 1fr); } }
    @media (max-width: 640px) { .hub-ticker-grid { grid-template-columns: repeat(2, 1fr); } }
    .ticker-pill { display: flex; flex-direction: column; align-items: center; text-align: center; gap: .25rem; }
    .ticker-pill-abbr { font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink); margin-top: .5rem; }
    .ticker-pill-score { font-family: 'Bebas Neue', Impact, sans-serif; font-size: 1.875rem; color: var(--ink); font-variant-numeric: tabular-nums; }
    .ticker-pill-delta { font-family: 'IBM Plex Mono', monospace; font-size: .75rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .hub-delta-pos { color: var(--gold); }
    .hub-delta-neg { color: var(--alert); }
    .hub-delta-zero { color: var(--ink-muted); }
    .ticker-pill-cause { font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: 10px; color: var(--ink-muted); margin-top: .25rem; }

    /* Team chips (reusable) */
    .hub-chip {
      display: inline-flex; align-items: center; justify-content: center;
      border-radius: 999px; font-family: 'IBM Plex Mono', monospace; font-weight: 700; color: #fff; line-height: 1;
      white-space: nowrap; flex-shrink: 0;
    }
    .hub-chip-sm { width: 24px; height: 24px; font-size: 9px; }
    .hub-chip-md { width: 28px; height: 28px; font-size: 10px; }
    .hub-chip-lg { width: 32px; height: 32px; font-size: 11px; }

    /* Taxonomy */
    .hub-taxonomy-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2rem; margin-bottom: 4rem; }
    @media (max-width: 800px) { .hub-taxonomy-grid { grid-template-columns: 1fr; } }
    .archetype-card { background: #FFFFFF; border: 1px solid var(--rule); padding: 2rem; }
    .archetype-card-title { font-family: 'Bebas Neue', Impact, sans-serif; font-size: 1.9rem; line-height: 1; margin: 0 0 1rem 0; letter-spacing: -.005em; color: var(--ink); }
    .archetype-card-desc { font-family: 'Source Serif 4', Georgia, serif; font-size: 1rem; line-height: 1.55; color: var(--ink); margin: 0 0 1.25rem 0; }
    .archetype-card-teams { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; margin-bottom: 1.5rem; }
    .hub-team-chip-row { display: inline-flex; align-items: center; gap: .5rem; }
    .hub-chip-match { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--ink-muted); font-variant-numeric: tabular-nums; }
    .archetype-card-phrase { border-top: 1px solid var(--paper-border); padding-top: 1rem; margin-bottom: 1rem; }
    .archetype-card-phrase-label, .archetype-card-modifier-label, .team-archetype-phrase-label {
      font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--ink-muted);
      letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: .5rem;
    }
    .archetype-card-phrase-body, .archetype-signature {
      font-family: 'IBM Plex Mono', monospace; font-style: italic; font-size: .875rem; color: var(--ink);
    }
    .archetype-card-modifiers { border-top: 1px solid var(--paper-border); padding-top: 1rem; margin-bottom: 1rem; }
    .archetype-card-modifier-row, .team-archetype-modifier-row { display: flex; flex-wrap: wrap; gap: .75rem; }
    .modifier-chip {
      display: inline-flex; align-items: center; gap: .25rem;
      font-family: 'IBM Plex Mono', monospace; font-size: 10px;
      letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink);
      background: #FFFFFF; border: 1px solid var(--rule); padding: .25rem .6rem; border-radius: 999px;
    }
    .archetype-card-spark { border-top: 1px solid var(--paper-border); padding-top: 1rem; }
    .hub-modifier-strip { border-top: 1px solid #5A5954; padding-top: 2rem; }
    .hub-modifier-row { display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center; margin-bottom: 1rem; }

    /* Rivalry */
    .hub-rivalry-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2rem; margin: 1rem 0 2rem; }
    @media (max-width: 1000px) { .hub-rivalry-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 640px) { .hub-rivalry-grid { grid-template-columns: 1fr; } }
    .rivalry-cell { background: #FFFFFF; border: 1px solid var(--rule); padding: 1.25rem; }
    .rivalry-cell-name { font-family: 'Bebas Neue', Impact, sans-serif; font-size: 1.15rem; margin-bottom: 1rem; letter-spacing: -.005em; }
    .rivalry-cell-chips { display: flex; gap: .75rem; margin-bottom: 1rem; }
    .rivalry-cell-bar { display: flex; height: 12px; overflow: hidden; margin-bottom: .75rem; background: var(--paper-warm); }
    .rivalry-cell-bar-a, .rivalry-cell-bar-b { height: 100%; }
    .rivalry-cell-ratio { font-family: 'IBM Plex Mono', monospace; font-size: .875rem; color: var(--ink); font-variant-numeric: tabular-nums; margin-bottom: .75rem; }
    .rivalry-cell-take { font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: .82rem; color: var(--ink-muted); margin: 0; line-height: 1.55; }

    /* Lexicon */
    .lexicon-feature { display: grid; grid-template-columns: 60% 40%; gap: 3rem; margin: 2rem 0 1rem; }
    @media (max-width: 900px) { .lexicon-feature { grid-template-columns: 1fr; gap: 2rem; } }
    .lexicon-feature-left p {
      font-family: 'Source Serif 4', Georgia, serif; font-size: 1rem; line-height: 1.65;
      margin: 0 0 1.25rem 0; color: var(--ink);
    }
    .lexicon-feature-spark { margin-bottom: 2rem; }
    .lexicon-feature-quotes { display: flex; flex-direction: column; gap: 1rem; }
    .lexicon-quote { background: #FFFFFF; border: 1px solid var(--paper-border); padding: 1rem; }
    .lexicon-quote-text { font-family: 'IBM Plex Mono', monospace; font-style: italic; font-size: 12px; color: var(--ink-muted); margin: 0; }
    .lexicon-quote-source { font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: var(--rule); margin-top: .5rem; }

    /* Index cards */
    .hub-index-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2rem; margin: 2rem 0 1rem; }
    @media (max-width: 900px) { .hub-index-cards { grid-template-columns: 1fr; } }
    .index-card { position: relative; background: var(--paper); border: 1px solid var(--ink); aspect-ratio: 1 / 1; overflow: hidden; }
    .index-card-accent { position: absolute; inset: 0 auto 0 0; width: 12px; background: var(--card-accent, var(--ink)); }
    .index-card-inner { padding: 2rem 2rem 2rem 2.5rem; height: 100%; display: flex; flex-direction: column; }
    .index-card-header { font-family: 'IBM Plex Mono', monospace; font-size: 9px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink-muted); margin-bottom: .25rem; }
    .index-card-headline { font-family: 'Bebas Neue', Impact, sans-serif; font-size: clamp(1.65rem, 2.5vw, 2.25rem); line-height: 0.95; margin: .75rem 0 1rem 0; letter-spacing: -.005em; color: var(--ink); }
    .index-card-stat { font-family: 'Bebas Neue', Impact, sans-serif; font-size: clamp(3rem, 5vw, 4.5rem); line-height: 1; margin-bottom: 1rem; color: var(--ink); font-variant-numeric: tabular-nums; }
    .index-card-label { font-family: 'Source Serif 4', Georgia, serif; font-size: .875rem; line-height: 1.55; color: var(--ink); margin: 0 0 auto 0; }
    .index-card-footer { display: flex; justify-content: space-between; align-items: flex-end; margin-top: 1rem; gap: 1rem; }
    .index-card-punchline { font-family: 'IBM Plex Mono', monospace; font-style: italic; font-size: .75rem; color: var(--ink-muted); }

    /* Commiseration */
    .hub-commiseration .hub-commiseration-inner { max-width: 720px; margin: 0 auto; padding: 5rem 1.5rem; }
    .hub-commiseration-body { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.125rem; line-height: 1.65; color: var(--paper); }
    .hub-commiseration-body p { margin: 0 0 1.5rem 0; }
    .hub-commiseration-signoff { font-style: italic; color: var(--rule); padding-top: 1rem; }

    /* Footer */
    .hub-footer { background: var(--ink); color: var(--paper); border-top: 1px solid #5A5954; }
    .hub-footer-inner { padding: 4rem 1.5rem; }
    .hub-footer-brand { margin-bottom: 3rem; }
    .hub-footer-wordmark { font-family: 'Bebas Neue', Impact, sans-serif; font-size: 3rem; margin-bottom: .75rem; }
    .hub-footer-tagline { font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: 1.125rem; color: var(--rule); margin: 0; }
    .hub-footer-cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3rem; margin-bottom: 4rem; }
    @media (max-width: 640px) { .hub-footer-cols { grid-template-columns: 1fr; gap: 2rem; } }
    .hub-footer-col-title { font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--gold); margin-bottom: 1rem; }
    .hub-footer-cols a { display: block; font-family: 'IBM Plex Mono', monospace; font-size: .82rem; margin-bottom: .5rem; }
    .hub-footer-rule { height: 1px; background: #5A5954; margin: 1rem 0 2rem; }
    .hub-footer-meta { font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.08em; color: var(--paper); display: flex; flex-direction: column; gap: 1rem; }
    .hub-footer-meta-small { font-size: 10px; color: var(--rule); font-variant-numeric: tabular-nums; }
    .hub-footer-meta > div:first-child { text-transform: uppercase; }

    /* Team-page archetype module */
    .team-archetype-module { background: #FFFFFF; border: 1px solid var(--rule); padding: 2rem; margin: 2rem 0; font-family: 'Source Serif 4', Georgia, serif; color: var(--ink); }
    .team-archetype-eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink-muted); margin-bottom: .75rem; }
    .team-archetype-name { font-family: 'Bebas Neue', Impact, sans-serif; font-size: 2rem; line-height: 1; letter-spacing: -.005em; margin: 0 0 .25rem 0; color: var(--ink); }
    .team-archetype-confidence { font-family: 'IBM Plex Mono', monospace; font-size: .875rem; color: var(--ink-muted); font-variant-numeric: tabular-nums; margin-bottom: 1rem; }
    .team-archetype-desc { font-size: 1rem; line-height: 1.55; margin: 0 0 1.25rem 0; }
    .team-archetype-phrase { border-top: 1px solid var(--paper-border); padding-top: 1rem; margin-bottom: 1rem; }
    .team-archetype-phrase-body { font-family: 'IBM Plex Mono', monospace; font-style: italic; font-size: .95rem; }
    .team-archetype-modifier-block { border-top: 1px solid var(--paper-border); padding-top: 1rem; margin-bottom: 1rem; }
    .team-archetype-migration { border-top: 1px solid var(--paper-border); padding-top: 1rem; margin-bottom: 1rem; }
    .team-archetype-link { font-family: 'IBM Plex Mono', monospace; font-size: .82rem; border-bottom: 1px dotted currentColor; }
    .team-archetype-empty-row { font-family: 'IBM Plex Mono', monospace; font-size: .82rem; color: var(--ink-muted); font-style: italic; }
    .team-archetype-empty .team-archetype-blurb { font-size: 1rem; color: var(--ink-muted); }
    """
