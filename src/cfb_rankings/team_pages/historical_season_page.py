"""HistoricalSeasonDeepDive renderer — per-season archive chapter.

Spec: ``docs/design-system/13-modules-archive.md`` §HistoricalSeasonDeepDive.

Output: ``output/site/teams/<slug>/seasons/<year>.html``.

Page anatomy (eight sections, ordered top-to-bottom):

  1. Archive nav — prev/next season + chapter position + back-to-team.
  2. Serif title + italic thesis (LLM-authored, stored in ``team_historical_seasons``).
  3. 5-col meta strip — record, final result, AP final, SP+ final, era name.
  4. "The shape of the season" SVG — 12-wide game-card grid + mood polyline.
  5. Defining moments — 3 cards (register-color-coded).
  6. Pull quote — attributed figcaption.
  7. Legacy paragraph — "what it meant".
  8. Footer nav — mirror of the archive nav.

Gap-year variant: when the DB has no per-game rows but canonical CFP history
preserves the season (Alabama 2017/2018), we render a simplified layout:
header + 5-col meta (with "—" for per-game-derived fields) + pull quote (if
available) + legacy paragraph + a single "chapter preserved from canonical
record; per-game data unavailable" placeholder instead of the shape SVG.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from cfb_rankings.common.head_chrome import render_head_chrome

from .profile_loader import Profile, load_profile


_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


# ------------------------------------------------------------------------
# Public entrypoints
# ------------------------------------------------------------------------

def render_historical_season_page(
    db,
    slug: str,
    year: int,
    output_dir: Path | str,
) -> Path:
    """Render a single season's chapter page. Writes to
    ``<output_dir>/<slug>/seasons/<year>.html`` and returns the path.
    """
    profile = load_profile(slug)
    season_row = _fetch_historical_season(db, slug, year)
    arc_row = _fetch_arc_row(db, profile.team_id, year) if profile.team_id else None
    games = _fetch_games(db, profile.team_id, year) if profile.team_id else []
    siblings = _fetch_sibling_years(db, profile.team_id) if profile.team_id else []
    body = _render_page(profile, year, season_row, arc_row, games, siblings)

    out_root = Path(output_dir)
    out_dir = out_root / slug / "seasons"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{year}.html"
    out_path.write_text(body, encoding="utf-8")
    return out_path


def render_all_historical_seasons(
    db,
    output_dir: Path | str,
) -> int:
    """Render every historical-season page for every profiled program.

    Writes one page per (slug, season_year) that has a row in
    team_season_arc. Safe to call repeatedly.
    """
    from .profile_loader import PROFILED_SLUGS
    count = 0
    errors: list[tuple[str, int, str]] = []
    for slug in sorted(PROFILED_SLUGS):
        try:
            profile = load_profile(slug)
        except Exception:
            continue
        if not profile.team_id:
            continue
        years = [r["season_year"] for r in _fetch_sibling_years(db, profile.team_id)]
        for year in years:
            try:
                render_historical_season_page(db, slug, year, output_dir)
                count += 1
            except Exception as exc:
                errors.append((slug, year, f"{type(exc).__name__}: {exc}"))
    if errors:
        for slug, year, msg in errors:
            print(f"  historical-seasons: {slug}/{year} failed — {msg}")
    return count


# ------------------------------------------------------------------------
# Data access
# ------------------------------------------------------------------------

def _fetch_historical_season(db, slug: str, year: int) -> dict[str, Any] | None:
    return db.query_one(
        """
        select season_title, season_thesis,
               defining_moments_json, pull_quote_json, legacy_paragraph,
               gap_year_flag, model_id
        from team_historical_seasons
        where team_slug = :s and season_year = :y
        """,
        {"s": slug, "y": year},
    )


def _fetch_arc_row(db, team_id: int, year: int) -> dict[str, Any] | None:
    return db.query_one(
        """
        select season_year, wins, losses, ties, win_pct,
               ap_rank_final, sp_plus_final,
               cfp_flag, title_game_flag, title_won_flag,
               brick_state, quality_score, notes_json
        from team_season_arc
        where team_id = :tid and season_year = :y
        """,
        {"tid": team_id, "y": year},
    )


def _fetch_sibling_years(db, team_id: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select season_year
        from team_season_arc
        where team_id = :tid
        order by season_year asc
        """,
        {"tid": team_id},
    )


def _fetch_games(db, team_id: int, year: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select week, season_type, start_time_utc,
               home_team_id, away_team_id,
               home_points, away_points,
               (select school_name from teams where team_id = g.home_team_id) as home_name,
               (select school_name from teams where team_id = g.away_team_id) as away_name,
               neutral_site
        from games g
        where season_year = :y
          and status in ('Final','final','FINAL')
          and (home_team_id = :tid or away_team_id = :tid)
        order by start_time_utc
        """,
        {"tid": team_id, "y": year},
    )


# ------------------------------------------------------------------------
# Page composition
# ------------------------------------------------------------------------

def _render_page(
    profile: Profile,
    year: int,
    season_row: dict[str, Any] | None,
    arc_row: dict[str, Any] | None,
    games: list[dict[str, Any]],
    siblings: list[dict[str, Any]],
) -> str:
    sibling_years = [r["season_year"] for r in siblings]
    prev_year, next_year = _neighbors(sibling_years, year)
    chapter_idx = sibling_years.index(year) + 1 if year in sibling_years else 0
    chapter_total = len(sibling_years)

    # Gap-year detection: no per-game rows AND arc row exists (canonical CFP history
    # preserved the year). The simplified layout kicks in for these.
    is_gap_year = bool(arc_row) and len(games) == 0 and (
        (season_row and season_row.get("gap_year_flag")) or
        ((arc_row.get("brick_state") in ("title-era", "peak")) and
         ((arc_row.get("wins") or 0) + (arc_row.get("losses") or 0) == 0))
    )

    title = (season_row or {}).get("season_title") or f"Season {year}"
    thesis = (season_row or {}).get("season_thesis") or ""
    legacy = (season_row or {}).get("legacy_paragraph") or ""

    moments = _parse_json_list((season_row or {}).get("defining_moments_json"))
    pull_quote = _parse_json_dict((season_row or {}).get("pull_quote_json"))

    era_name = _era_for(profile, year)
    final_result = _final_result(arc_row or {})

    accent_primary = profile.accent_hex
    accent_secondary = profile.accent_hex_secondary or accent_primary

    tokens_css = (_ASSETS_DIR / "tokens.css").read_text(encoding="utf-8")
    styles_css = (_ASSETS_DIR / "historical_season.css").read_text(encoding="utf-8")

    nav_top = _render_archive_nav(profile, year, prev_year, next_year, chapter_idx, chapter_total)
    header_html = _render_header(year, title, thesis)
    meta_html = _render_meta_strip(arc_row or {}, final_result, era_name)
    if is_gap_year:
        shape_html = _render_gap_placeholder()
    else:
        shape_html = _render_shape(profile, games, arc_row or {})
    moments_html = _render_moments(moments)
    pullquote_html = _render_pull_quote(pull_quote)
    legacy_html = _render_legacy(legacy, profile, arc_row or {})
    nav_bottom = _render_archive_nav(
        profile, year, prev_year, next_year, chapter_idx, chapter_total,
        is_footer=True,
    )

    page_title = f"{profile.program_name} {year} — {title} — CFB Index"
    head_chrome_block = render_head_chrome(
        page_path=f"/teams/{profile.slug}/seasons/{year}.html",
        title=page_title,
        description=f"{profile.program_name} — {year} season archive · {title}.",
        og_type="article",
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(page_title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{html.escape(profile.program_name)} — {year} season archive · {html.escape(title)}.">
<meta name="theme-color" content="{accent_primary}">
{head_chrome_block}
<style>
{tokens_css}

body {{
  --accent-primary: {accent_primary};
  --accent-secondary: {accent_secondary};
  --accent-gradient: linear-gradient(135deg, {accent_primary}, {accent_secondary});
  font-family: var(--font-sans, system-ui, sans-serif);
  background: var(--surface-page, #fafafa);
  color: var(--text-primary, #111);
  margin: 0;
  padding: 0;
}}

{styles_css}
</style>
</head>
<body>
<main class="historical-season">
  {nav_top}
  {header_html}
  {meta_html}
  {shape_html}
  {moments_html}
  {pullquote_html}
  {legacy_html}
  {nav_bottom}
</main>
</body>
</html>
"""


# ------------------------------------------------------------------------
# Section renderers
# ------------------------------------------------------------------------

def _render_archive_nav(
    profile: Profile,
    year: int,
    prev_year: int | None,
    next_year: int | None,
    chapter_idx: int,
    chapter_total: int,
    is_footer: bool = False,
) -> str:
    cls = "historical-season__archive-nav" + (
        " historical-season__archive-nav--footer" if is_footer else ""
    )
    prev_html = (
        f'<a class="historical-season__archive-link historical-season__archive-link--prev" '
        f'href="/teams/{profile.slug}/seasons/{prev_year}.html">'
        f'← {prev_year}</a>'
        if prev_year else '<span class="historical-season__archive-disabled">—</span>'
    )
    next_html = (
        f'<a class="historical-season__archive-link historical-season__archive-link--next" '
        f'href="/teams/{profile.slug}/seasons/{next_year}.html">'
        f'{next_year} →</a>'
        if next_year else '<span class="historical-season__archive-disabled">—</span>'
    )
    back_html = (
        f'<a class="historical-season__archive-team" href="/teams/{profile.slug}.html">'
        f'{html.escape(profile.program_name)} · back to program</a>'
    )
    return f"""<nav class="{cls}" aria-label="Season archive navigation">
  <div class="historical-season__archive-row">
    {prev_html}
    <span class="historical-season__archive-center">
      <span class="historical-season__archive-eyebrow">THE ARCHIVE · {year}</span>
      <span class="historical-season__archive-chapter">Chapter {chapter_idx} of {chapter_total}</span>
    </span>
    {next_html}
  </div>
  <div class="historical-season__archive-back">{back_html}</div>
</nav>"""


def _render_header(year: int, title: str, thesis: str) -> str:
    thesis_html = (
        f'<p class="historical-season__thesis">{html.escape(thesis)}</p>'
        if thesis else ""
    )
    return f"""<header class="historical-season__header">
  <h1 class="historical-season__title"><span class="historical-season__year">{year}</span>
    <span class="historical-season__em-dash">—</span>
    <span class="historical-season__phrase">{html.escape(title)}</span>
  </h1>
  {thesis_html}
</header>"""


def _render_meta_strip(arc_row: dict[str, Any], final_result: str, era_name: str) -> str:
    w = arc_row.get("wins") or 0
    l = arc_row.get("losses") or 0
    t = arc_row.get("ties") or 0
    if w + l + t == 0:
        record = "—"
    else:
        record = f"{w}-{l}" + (f"-{t}" if t else "")
    ap_final = arc_row.get("ap_rank_final")
    ap_txt = f"#{ap_final}" if ap_final else "—"
    sp_final = arc_row.get("sp_plus_final")
    sp_txt = f"{sp_final:+.1f}" if sp_final is not None else "—"
    tiles = [
        ("RECORD", record, ""),
        ("FINAL RESULT", final_result, ""),
        ("AP FINAL", ap_txt, "post-bowls"),
        ("SP+", sp_txt, "last-week"),
        ("ERA", era_name, ""),
    ]
    tile_html = "".join(
        f"""<div class="historical-season__meta-tile">
          <span class="historical-season__meta-label">{html.escape(lbl)}</span>
          <span class="historical-season__meta-value">{html.escape(val)}</span>
          <span class="historical-season__meta-sub">{html.escape(sub)}</span>
        </div>"""
        for lbl, val, sub in tiles
    )
    return f'<div class="historical-season__meta">{tile_html}</div>'


def _render_shape(
    profile: Profile,
    games: list[dict[str, Any]],
    arc_row: dict[str, Any],
) -> str:
    """The shape-of-season SVG: 620×150 viewBox with game cards + mood polyline.

    Layout: up to 14 game cards across. Each card 38px wide, color-coded
    W/L/T with the opponent name (abbreviated) + final-score inside. Below
    the card row, a smoothed polyline running y=100..140 reflects the
    net-W-L trajectory through the season (cumulative W - L · 10 centered
    around y=120).
    """
    if not games:
        return _render_gap_placeholder()

    team_id = profile.team_id or 0
    # Normalise each game to (week, outcome, margin, opp, score_str)
    normalised: list[dict[str, Any]] = []
    cum_wl = 0
    for g in games:
        is_home = int(g["home_team_id"]) == team_id
        team_pts = g["home_points"] if is_home else g["away_points"]
        opp_pts = g["home_points"] if not is_home else g["away_points"]
        opp_name = g["away_name"] if is_home else g["home_name"]
        if team_pts is None or opp_pts is None:
            continue
        if team_pts > opp_pts:
            outcome = "W"
            cum_wl += 1
        elif team_pts < opp_pts:
            outcome = "L"
            cum_wl -= 1
        else:
            outcome = "T"
        normalised.append({
            "week": g["week"],
            "outcome": outcome,
            "margin": (team_pts - opp_pts),
            "opp": opp_name or "Opp",
            "venue": "vs" if is_home else "@",
            "score": f"{team_pts}-{opp_pts}",
            "cum_wl": cum_wl,
            "is_post": (g["season_type"] == "postseason"),
        })

    # Layout geometry — give 620-wide total; card width scales to fit.
    n = len(normalised)
    margin_x = 22
    top_y = 20
    card_h = 56
    chart_w = 620 - (margin_x * 2)
    slot_w = chart_w / max(n, 1)
    card_w = min(42, slot_w - 4)
    gap = (slot_w - card_w)

    cards_svg: list[str] = []
    for i, g in enumerate(normalised):
        x = margin_x + i * slot_w + gap / 2
        outcome_cls = {
            "W": "shape-card--win",
            "L": "shape-card--loss",
            "T": "shape-card--tie",
        }.get(g["outcome"], "shape-card")
        post_badge = '<tspan class="shape-card__post">CFP</tspan>' if g["is_post"] else ""
        opp_abbr = _abbr(g["opp"])
        cards_svg.append(
            f"""
  <g class="shape-card {outcome_cls}" transform="translate({x:.1f}, {top_y})">
    <rect class="shape-card__rect" x="0" y="0" width="{card_w:.1f}" height="{card_h}" rx="3" />
    <text class="shape-card__outcome" x="{card_w/2:.1f}" y="15" text-anchor="middle">{g['outcome']}</text>
    <text class="shape-card__opp" x="{card_w/2:.1f}" y="30" text-anchor="middle">{html.escape(g['venue'])} {html.escape(opp_abbr)}</text>
    <text class="shape-card__score" x="{card_w/2:.1f}" y="44" text-anchor="middle">{html.escape(g['score'])}</text>
    {f'<text class="shape-card__post" x="{card_w/2:.1f}" y="54" text-anchor="middle">CFP</text>' if g['is_post'] else ''}
  </g>"""
        )

    # Mood polyline (cumulative W-L mapped to y-space 100..140).
    line_y_top = 105.0
    line_y_bot = 140.0
    max_abs = max(abs(g["cum_wl"]) for g in normalised) or 1
    pts: list[str] = []
    for i, g in enumerate(normalised):
        x = margin_x + i * slot_w + slot_w / 2
        # +max_abs → near top (good), -max_abs → near bottom (bad)
        pct = (g["cum_wl"] + max_abs) / (2 * max_abs)
        y = line_y_bot - pct * (line_y_bot - line_y_top)
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = f'<polyline class="shape-line" points="{" ".join(pts)}" />'
    # Dots for each game on the polyline
    dots = "\n  ".join(
        f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="2.5" class="shape-line__dot" />'
        for p in pts
    )

    baseline = (
        f'<line class="shape-line__baseline" x1="{margin_x}" y1="{(line_y_top + line_y_bot) / 2:.1f}" '
        f'x2="{margin_x + chart_w:.1f}" y2="{(line_y_top + line_y_bot) / 2:.1f}" />'
    )

    svg = f"""<svg class="historical-season__shape-svg" viewBox="0 0 620 150" role="img"
        aria-label="Game-by-game shape of the {arc_row.get('season_year') or ''} season">
  {''.join(cards_svg)}
  {baseline}
  {polyline}
  {dots}
</svg>"""

    return f"""<section class="historical-season__shape">
  <div class="historical-season__shape-header">
    <span class="historical-season__eyebrow">THE SHAPE — week-by-week · cumulative W–L below</span>
  </div>
  {svg}
</section>"""


def _render_gap_placeholder() -> str:
    return """<section class="historical-season__shape historical-season__shape--gap">
  <div class="historical-season__shape-header">
    <span class="historical-season__eyebrow">THE SHAPE — preserved from canonical record</span>
  </div>
  <div class="historical-season__gap-placeholder">
    <p>This chapter is preserved from canonical CFP record; per-game data is unavailable in the current ingest.
    The title, the outcome, and the coaching regime are load-bearing; the weekly arc is not reconstructable.</p>
  </div>
</section>"""


def _render_moments(moments: list[dict[str, Any]]) -> str:
    if not moments:
        return ""
    cards_html = []
    for m in moments:
        register = str(m.get("register") or "turning-point")
        mtype = str(m.get("type") or "moment")
        body = str(m.get("body") or "").strip()
        if not body:
            continue
        cards_html.append(f"""<article class="moment-card moment-card--{html.escape(register)}">
  <span class="moment-card__type">THE {html.escape(mtype.upper())}</span>
  <p class="moment-card__body">{html.escape(body)}</p>
</article>""")
    if not cards_html:
        return ""
    return f"""<section class="historical-season__moments">
  <span class="historical-season__eyebrow">DEFINING MOMENTS</span>
  <div class="historical-season__moments-grid">
    {''.join(cards_html)}
  </div>
</section>"""


def _render_pull_quote(quote: dict[str, Any] | None) -> str:
    if not quote:
        return ""
    text = str(quote.get("text") or "").strip()
    if not text:
        return ""
    source = str(quote.get("source") or "").strip()
    date = str(quote.get("date") or "").strip()
    is_generated = bool(quote.get("is_generated"))
    attribution_bits = [b for b in (source, date) if b]
    attribution = " · ".join(attribution_bits) if attribution_bits else "contemporaneous coverage"
    gen_badge = (
        '<span class="pull-quote__generated" title="LLM-synthesized in the contemporaneous voice; '
        'not a verified quote">· synthesized</span>' if is_generated else ''
    )
    return f"""<figure class="historical-season__pull-quote">
  <blockquote class="pull-quote__text">"{html.escape(text)}"</blockquote>
  <figcaption class="pull-quote__attribution">— {html.escape(attribution)}{gen_badge}</figcaption>
</figure>"""


def _render_legacy(legacy: str, profile: Profile, arc_row: dict[str, Any]) -> str:
    if not legacy:
        # Deterministic fallback — 1-sentence closing
        year = arc_row.get("season_year")
        w = arc_row.get("wins") or 0
        l = arc_row.get("losses") or 0
        if arc_row.get("title_won_flag"):
            legacy = f"{year} is one of the titled chapters — a year that joined the short list of {profile.program_name} seasons that end with a crown."
        elif arc_row.get("title_game_flag"):
            legacy = f"{year} ended one game short of the crown. The title-game trip is the chapter's load-bearing fact; the close was the season."
        elif arc_row.get("cfp_flag"):
            legacy = f"{year} reached the CFP — the modern era's table-stakes benchmark — and sits in {profile.program_name}'s peak-tier chapters."
        elif (l > w):
            legacy = f"{year} is a losing-side chapter. The record ({w}-{l}) does not soften into legacy; the program metabolizes it and moves on."
        else:
            legacy = f"{year} ({w}-{l}) is a middle chapter — the kind of season that doesn't write headlines but fills the ledger."
    return f"""<section class="historical-season__legacy">
  <span class="historical-season__eyebrow">WHAT IT MEANT</span>
  <p class="historical-season__legacy-text">{html.escape(legacy)}</p>
</section>"""


# ------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------

def _neighbors(years: list[int], year: int) -> tuple[int | None, int | None]:
    if year not in years:
        return None, None
    i = years.index(year)
    prev = years[i - 1] if i > 0 else None
    nxt = years[i + 1] if i < len(years) - 1 else None
    return prev, nxt


def _era_for(profile: Profile, year: int) -> str:
    """Read `era_name_overrides` (e.g. '2007-2023': 'The Process Era') and
    return the era name containing `year`. Falls back to a regime name from
    `coaching_regimes` if no override matches.
    """
    eras = profile.era_name_overrides or {}
    for span, name in eras.items():
        try:
            start_s, end_s = span.split("-", 1)
            start = int(start_s) if start_s else None
            end = int(end_s) if end_s else None
        except ValueError:
            continue
        if (start is None or start <= year) and (end is None or year <= end):
            return name
    regimes = profile.frontmatter.get("coaching_regimes") or []
    for r in regimes:
        try:
            s = int(r.get("start_year"))
            e_raw = r.get("end_year")
            e = int(e_raw) if e_raw is not None else 9999
        except (TypeError, ValueError):
            continue
        if s <= year <= e:
            return f"The {r.get('coach', 'Regime')} Era"
    return "—"


def _final_result(arc_row: dict[str, Any]) -> str:
    if arc_row.get("title_won_flag"):
        return "National Champion"
    if arc_row.get("title_game_flag"):
        return "CFP Title Game"
    if arc_row.get("cfp_flag"):
        return "CFP Appearance"
    brick_state = arc_row.get("brick_state")
    if brick_state == "crisis":
        return "Losing season"
    if brick_state == "current":
        return "In-progress"
    if brick_state == "data-gap":
        return "Data gap"
    w = arc_row.get("wins") or 0
    l = arc_row.get("losses") or 0
    if w + l == 0:
        return "—"
    if w >= 10:
        return f"{w}-win season"
    if w >= 6:
        return "Bowl season"
    return "Non-bowl season"


def _parse_json_list(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return list(val) if isinstance(val, list) else []


def _parse_json_dict(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        val = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return dict(val) if isinstance(val, dict) else None


_ABBR_OVERRIDES = {
    "Mississippi State": "Miss St",
    "Ole Miss": "Ole Miss",
    "Texas A&M": "Texas A&M",
    "Oklahoma State": "Okla St",
    "Washington State": "Wash St",
    "Penn State": "Penn St",
    "Ohio State": "Ohio St",
    "Michigan State": "Mich St",
    "Michigan": "Michigan",
    "Notre Dame": "ND",
    "Florida State": "FSU",
    "Iowa State": "Iowa St",
    "North Carolina": "UNC",
    "South Carolina": "S Caro",
    "Oklahoma": "Okla",
}


def _abbr(name: str) -> str:
    if name in _ABBR_OVERRIDES:
        return _ABBR_OVERRIDES[name]
    # Collapse common suffixes
    base = name.replace("University of ", "").strip()
    if len(base) <= 8:
        return base
    # Take first word + common abbrevs
    parts = base.split()
    if len(parts) == 1:
        return parts[0][:6]
    return (parts[0][:4] + " " + parts[-1][:3])[:9]
