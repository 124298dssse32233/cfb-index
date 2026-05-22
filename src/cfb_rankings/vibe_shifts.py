"""Sunday Vibe Shift Ledger — weekly ranked share-cards of who changed most.

This module renders ``/hub/vibe-shifts/<season>/<week>/`` as a ranked grid of
team cards, each with a per-team SVG share asset suitable for Twitter/X
posting. It is intentionally a standalone module rather than a section of
``reporting.py`` so the 25.8k-line monolith stops growing. The share-card
SVG renderer here is also the foundational dependency for R5 (Game Day
Cards) and R6 (Respect Gap Cards) per ``docs/octopus/next-roadmap.md``.

Data:
  - team_rating_deltas (per-game power/resume swings, ~318k rows)
  - games (for opponent / score context)
  - teams + team_brand (for name + primary color)

The module never crashes the build pipeline. Every public entry point is
wrapped to swallow database errors so the rest of the site can ship even
if the rating-deltas surface is empty.
"""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.common.cfb_calendar import cfb_week_label_for_window
from cfb_rankings.db import Database


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

# Sentinel level codes considered "relevant" for the editorial ledger. Small
# D-III shutouts technically produce the biggest power swings, but a fan
# audience cares about FBS first. Adding more levels here is a one-line knob.
_DEFAULT_LEVELS: tuple[str, ...] = ("FBS",)


def fetch_vibe_shifts(
    db: Database,
    season_year: int,
    week: int,
    *,
    limit: int = 10,
    levels: tuple[str, ...] = _DEFAULT_LEVELS,
) -> list[dict[str, Any]]:
    """Return the top ``limit`` |power_delta| swings for a given (season, week).

    Dedupes by latest ``model_run_id`` per (team, game) so re-runs of the
    model don't double-rank a team. Joins game context so each card knows
    the score, opponent, and W/L outcome.
    """
    placeholders = ", ".join(f"'{lvl}'" for lvl in levels) or "'FBS'"
    # Window function dedupes by latest model_run_id per (team, game) in
    # one O(n log n) pass over the prefilter rather than the correlated
    # ``max(...)`` subquery (which is O(n²) and timed out at 318k rows).
    sql = f"""
        with ranked as (
          select d.*,
                 row_number() over (
                   partition by d.team_id, d.game_id
                   order by d.model_run_id desc
                 ) as _rn
          from team_rating_deltas d
          join games g on g.game_id = d.game_id
          where g.season_year = :season and g.week = :week
        )
        select
          t.team_id,
          t.canonical_name as team_name,
          t.slug as team_slug,
          t.level_code,
          tb.primary_color as primary_color,
          c.conference_name,
          d.power_delta,
          d.pregame_power,
          d.postgame_power,
          d.offense_delta,
          d.defense_delta,
          d.special_teams_delta,
          d.resume_delta,
          d.opponent_quality_effect,
          d.dominance_effect,
          g.game_id,
          g.season_year,
          g.week,
          g.home_team_id,
          g.away_team_id,
          g.home_points,
          g.away_points,
          ht.canonical_name as home_name,
          ht.slug as home_slug,
          at.canonical_name as away_name,
          at.slug as away_slug
        from ranked d
        join games g on g.game_id = d.game_id
        join teams t on t.team_id = d.team_id
        left join team_brand tb on tb.team_id = t.team_id
        left join conferences c on c.conference_id = t.current_conference_id
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where d._rn = 1
          and t.level_code in ({placeholders})
        order by abs(d.power_delta) desc
        limit :lim
    """
    rows = db.query_all(sql, {"season": season_year, "week": week, "lim": limit}) or []
    out: list[dict[str, Any]] = []
    for r in rows:
        is_home = int(r["team_id"]) == int(r["home_team_id"])
        team_points = r["home_points"] if is_home else r["away_points"]
        opp_points = r["away_points"] if is_home else r["home_points"]
        opp_name = r["away_name"] if is_home else r["home_name"]
        opp_slug = r["away_slug"] if is_home else r["home_slug"]
        if team_points is None or opp_points is None:
            result = "TBD"
            score_text = f"vs {opp_name}"
            game_text = f"vs {opp_name}"
        else:
            tp, op = int(team_points), int(opp_points)
            result = "W" if tp > op else "L" if tp < op else "T"
            score_text = f"{tp}-{op}"
            location = "vs" if is_home else "@"
            game_text = f"{result} {tp}-{op} {location} {opp_name}"
        out.append({
            "team_id": int(r["team_id"]),
            "team_name": str(r["team_name"] or ""),
            "team_slug": str(r["team_slug"] or ""),
            "level_code": str(r["level_code"] or ""),
            "primary_color": str(r["primary_color"] or "#1a1a1a"),
            "conference_name": str(r["conference_name"] or ""),
            "power_delta": float(r["power_delta"] or 0.0),
            "pregame_power": float(r["pregame_power"] or 0.0),
            "postgame_power": float(r["postgame_power"] or 0.0),
            "offense_delta": float(r["offense_delta"] or 0.0),
            "defense_delta": float(r["defense_delta"] or 0.0),
            "special_teams_delta": float(r["special_teams_delta"] or 0.0),
            "resume_delta": float(r["resume_delta"] or 0.0),
            "opponent_quality_effect": float(r["opponent_quality_effect"] or 0.0),
            "dominance_effect": float(r["dominance_effect"] or 0.0),
            "result": result,
            "score_text": score_text,
            "game_text": game_text,
            "opponent_name": str(opp_name or ""),
            "opponent_slug": str(opp_slug or ""),
            "is_home": bool(is_home),
        })
    return out


def latest_vibe_shifts_week(
    db: Database,
    *,
    levels: tuple[str, ...] = _DEFAULT_LEVELS,
    min_games: int = 10,
) -> tuple[int, int] | None:
    """Return the most-recent (season, week) with ≥ ``min_games`` qualifying games.

    "Qualifying" = level ∈ ``levels`` AND has a rating-delta row.
    Returns ``None`` when no week qualifies (empty DB).
    """
    placeholders = ", ".join(f"'{lvl}'" for lvl in levels) or "'FBS'"
    sql = f"""
        select g.season_year, g.week, count(distinct g.game_id) as gc
        from team_rating_deltas d
        join games g on g.game_id = d.game_id
        join teams t on t.team_id = d.team_id
        where t.level_code in ({placeholders})
        group by g.season_year, g.week
        having gc >= :mg
        order by g.season_year desc, g.week desc
        limit 1
    """
    row = db.query_one(sql, {"mg": min_games})
    if not row:
        return None
    return int(row["season_year"]), int(row["week"])


# ---------------------------------------------------------------------------
# SVG share-card renderer
# ---------------------------------------------------------------------------


def _safe_hex(color: str | None, fallback: str = "#1a1a1a") -> str:
    """Validate an incoming hex color; fall back if it's garbage."""
    if not color:
        return fallback
    c = color.strip()
    if c.startswith("#") and len(c) in (4, 7):
        try:
            int(c[1:], 16)
            return c
        except ValueError:
            pass
    return fallback


def _contrast_text_color(hex_color: str) -> str:
    """Return '#FFFFFF' or '#0a0a0a' depending on brightness of the bg."""
    c = _safe_hex(hex_color)
    if len(c) == 4:
        r, g, b = (int(c[i] * 2, 16) for i in (1, 2, 3))
    else:
        r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    # Perceptual luminance
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#0a0a0a" if lum > 160 else "#FFFFFF"


def _format_delta(value: float, precision: int = 2) -> str:
    return f"{value:+.{precision}f}"


def render_vibe_shift_card_svg(
    card: dict[str, Any],
    *,
    week: int,
    season_year: int,
    rank: int,
) -> str:
    """Render one vibe-shift share card as a standalone SVG (1200x675).

    Single image. Twitter/X summary_large_image friendly. No JavaScript,
    no embedded fonts — uses system sans-serif via CSS fallbacks so it
    travels on social. Designed to be screenshottable + URL-fetchable.

    The card encodes one team's biggest weekly swing: the headline
    power delta, the four component deltas (offense / defense / special
    teams / resume), the actual game result, and the team-page URL in
    the footer.
    """
    bg = _safe_hex(card.get("primary_color"))
    fg = _contrast_text_color(bg)
    muted = "rgba(255,255,255,0.78)" if fg == "#FFFFFF" else "rgba(10,10,10,0.65)"
    accent = "#ffd000" if fg == "#FFFFFF" else "#9b1b1b"
    direction = "up" if card["power_delta"] >= 0 else "down"
    delta_color = "#7cf3a8" if fg == "#FFFFFF" else "#0d6831"
    if direction == "down":
        delta_color = "#ff7575" if fg == "#FFFFFF" else "#b00020"
    arrow = "▲" if direction == "up" else "▼"

    eyebrow = f"WEEK {week} · {season_year} · VIBE SHIFT #{rank}"
    team_name = card["team_name"]
    conf = card.get("conference_name") or card.get("level_code") or ""
    delta_str = _format_delta(card["power_delta"])
    pre, post = card["pregame_power"], card["postgame_power"]
    chips = [
        ("OFF", card["offense_delta"]),
        ("DEF", card["defense_delta"]),
        ("ST", card["special_teams_delta"]),
        ("RES", card["resume_delta"]),
    ]

    chip_x_start = 80
    chip_y = 470
    chip_w = 240
    chip_gap = 20
    chip_html = ""
    for i, (label, val) in enumerate(chips):
        cx = chip_x_start + i * (chip_w + chip_gap)
        chip_color = (
            "#7cf3a8" if (val > 0 and fg == "#FFFFFF") else
            "#0d6831" if (val > 0) else
            "#ff7575" if (val < 0 and fg == "#FFFFFF") else
            "#b00020" if (val < 0) else
            muted
        )
        chip_html += f"""
        <g>
          <rect x="{cx}" y="{chip_y}" width="{chip_w}" height="80" rx="12"
                fill="none" stroke="{muted}" stroke-width="2"/>
          <text x="{cx + chip_w / 2}" y="{chip_y + 30}" fill="{muted}"
                text-anchor="middle" font-size="20" font-weight="600"
                font-family="system-ui, -apple-system, sans-serif" letter-spacing="2">{escape(label)}</text>
          <text x="{cx + chip_w / 2}" y="{chip_y + 64}" fill="{chip_color}"
                text-anchor="middle" font-size="32" font-weight="800"
                font-family="system-ui, -apple-system, sans-serif"
                font-variant-numeric="tabular-nums">{escape(_format_delta(val))}</text>
        </g>
        """

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="Vibe Shift card for {escape(team_name)} week {week}">
  <defs>
    <linearGradient id="bg-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{bg}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{bg}" stop-opacity="0.82"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="675" fill="url(#bg-grad)"/>
  <!-- Top-left eyebrow -->
  <text x="80" y="92" fill="{muted}" font-size="22" font-weight="700"
        letter-spacing="4" font-family="system-ui, -apple-system, sans-serif">{escape(eyebrow)}</text>
  <!-- Team name -->
  <text x="80" y="200" fill="{fg}" font-size="92" font-weight="900"
        font-family="system-ui, -apple-system, sans-serif"
        textLength="{min(len(team_name) * 50, 1040)}" lengthAdjust="spacingAndGlyphs">{escape(team_name)}</text>
  <text x="80" y="244" fill="{muted}" font-size="24" font-weight="600"
        font-family="system-ui, -apple-system, sans-serif" letter-spacing="2">{escape(conf.upper())}</text>
  <!-- Delta hero number -->
  <text x="80" y="380" fill="{delta_color}" font-size="160" font-weight="900"
        font-family="system-ui, -apple-system, sans-serif"
        font-variant-numeric="tabular-nums">{arrow} {escape(delta_str)}</text>
  <text x="80" y="420" fill="{muted}" font-size="22" font-weight="600"
        font-family="system-ui, -apple-system, sans-serif" letter-spacing="1">POWER RATING SHIFT &nbsp;&nbsp;{pre:.1f} → {post:.1f}</text>
  <!-- Component chips -->
  {chip_html}
  <!-- Game context -->
  <text x="80" y="595" fill="{fg}" font-size="30" font-weight="700"
        font-family="system-ui, -apple-system, sans-serif">{escape(card['game_text'])}</text>
  <!-- Brand footer -->
  <text x="80" y="640" fill="{accent}" font-size="20" font-weight="800"
        font-family="system-ui, -apple-system, sans-serif" letter-spacing="3">CFB INDEX</text>
  <text x="1120" y="640" fill="{muted}" font-size="18" font-weight="600"
        font-family="system-ui, -apple-system, sans-serif" letter-spacing="1"
        text-anchor="end">/hub/vibe-shifts/{season_year}/{week}/</text>
</svg>"""


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------

_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vibe Shifts — {week_label} · {season_year} · CFB Index</title>
<meta name="description" content="The teams that changed the most this week. Ranked by absolute power-rating swing, with the why decomposed into offense, defense, special teams, and resume.">
{head_chrome}
<link rel="stylesheet" href="/assets/css/site.css">
<style>
  .vibe-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 24px; margin-top: 24px; }}
  .vibe-card {{ display: block; background: var(--card, #fff); border: 1px solid var(--border, #d8d8d8); border-radius: 16px; overflow: hidden; text-decoration: none; color: inherit; transition: transform .15s, box-shadow .15s; }}
  .vibe-card:hover {{ transform: translateY(-2px); box-shadow: 0 12px 28px rgba(0,0,0,.08); }}
  .vibe-card__img {{ display: block; width: 100%; height: auto; aspect-ratio: 16/9; background: #f5f5f5; }}
  .vibe-card__meta {{ padding: 16px 20px 20px; }}
  .vibe-card__rank {{ font-size: 11px; letter-spacing: 2px; font-weight: 700; color: var(--muted-foreground, #666); }}
  .vibe-card__team {{ font-size: 22px; font-weight: 800; margin: 4px 0 6px; }}
  .vibe-card__game {{ font-size: 14px; color: var(--muted-foreground, #555); margin-bottom: 10px; }}
  .vibe-card__delta {{ font-size: 32px; font-weight: 900; font-variant-numeric: tabular-nums; }}
  .vibe-card__delta--up {{ color: #0d6831; }}
  .vibe-card__delta--down {{ color: #b00020; }}
  .vibe-card__share-row {{ display: flex; gap: 8px; margin-top: 10px; font-size: 12px; }}
  .vibe-card__share-row a {{ color: var(--muted-foreground, #555); text-decoration: underline; }}
  .vibe-empty {{ padding: 32px; border: 2px dashed var(--border, #d8d8d8); border-radius: 16px; text-align: center; color: var(--muted-foreground, #666); }}
</style>
</head>
<body class="vibe-shifts-page">
<main class="site-shell" id="main-content">
  {hero_finding}
  <section class="hero">
    <p class="eyebrow">The Vibe Shift Ledger · {week_label}</p>
    <h1>Who changed the most this week.</h1>
    <p class="lede">Ten teams, ranked by the absolute size of their power-rating swing. Each card shows the headline number, where it came from (offense, defense, special teams, resume), and the actual game that produced it. Save the image; the argument's already there.</p>
    <p class="section-note">Sunday morning ritual. Updates after every model run.</p>
  </section>
  <section class="section">
    {body}
  </section>
  {methodology_footer}
</main>
</body>
</html>
"""


def _render_ledger_body(season_year: int, week: int, cards: list[dict[str, Any]]) -> str:
    if not cards:
        return '<div class="vibe-empty">No qualifying games for this week yet. Check back after kickoff.</div>'
    items: list[str] = []
    for rank, card in enumerate(cards, start=1):
        team_slug = card["team_slug"]
        team_name = card["team_name"]
        delta = card["power_delta"]
        delta_class = "vibe-card__delta--up" if delta >= 0 else "vibe-card__delta--down"
        delta_text = _format_delta(delta)
        svg_url = f"/hub/vibe-shifts/{season_year}/{week}/{escape(team_slug)}.svg"
        team_url = f"/teams/{escape(team_slug)}.html"
        items.append(f'''
        <a class="vibe-card" href="{team_url}">
          <img class="vibe-card__img" src="{svg_url}" alt="Vibe Shift card for {escape(team_name)} week {week}" loading="lazy"/>
          <div class="vibe-card__meta">
            <div class="vibe-card__rank">#{rank} · {escape(card.get("conference_name") or card.get("level_code") or "").upper()}</div>
            <div class="vibe-card__team">{escape(team_name)}</div>
            <div class="vibe-card__game">{escape(card["game_text"])}</div>
            <div class="vibe-card__delta {delta_class}">{escape(delta_text)} <span style="font-size:14px;font-weight:600;color:var(--muted-foreground,#666);">power</span></div>
            <div class="vibe-card__share-row">
              <a href="{svg_url}" download>Download share card</a>
              <span>·</span>
              <a href="{team_url}">Team page</a>
            </div>
          </div>
        </a>
        ''')
    return f'<div class="vibe-grid">{"".join(items)}</div>'


def render_vibe_shifts_index_html(
    season_year: int,
    week: int,
    cards: list[dict[str, Any]],
    *,
    today: date | None = None,
) -> str:
    """Render the Vibe Shifts index page.

    Args:
        season_year: Season being summarized (e.g. 2026).
        week: ISO calendar week the data was computed for. Used as a
            DB key, never surfaced raw in user-facing copy.
        cards: The list of card payloads to render.
        today: For the human-friendly week label. Defaults to date.today().
            Lets tests pin a stable label across rebuilds.
    """
    today = today or date.today()
    week_label = cfb_week_label_for_window(today, week, db=None)
    body = _render_ledger_body(season_year, week, cards)
    from cfb_rankings.common.head_chrome import render_head_chrome
    from cfb_rankings.dashboards import render_hero_finding, render_methodology_footer
    head_chrome = render_head_chrome(
        page_path=f"/hub/vibe-shifts/{season_year}/{week}/",
        title=f"Vibe Shifts — {week_label} · {season_year} · CFB Index",
        description=(
            "The teams that changed the most this week. Ranked by absolute "
            "power-rating swing, with the why decomposed into offense, "
            "defense, special teams, and resume."
        ),
        og_type="article",
    )

    # Dashboard archetype: hero finding zone — the top-card delta is
    # the page's defining number. Empty when no cards (offseason or
    # pre-kickoff weeks). Caption surfaces sample size + week.
    if cards:
        _top = cards[0]
        _top_delta = _format_delta(_top.get("power_delta", 0))
        _hero_finding_html = render_hero_finding(
            eyebrow=f"Vibe Shifts · {week_label}",
            number=_top_delta,
            sentence=(
                f"{escape(_top.get('team_name', 'Top mover'))} "
                f"posted the largest power-rating swing this week."
            ),
            caption=(
                f"{len(cards)} teams ranked &middot; week {week} of {season_year} season"
            ),
            aria_label="Biggest power swing this week",
        )
    else:
        _hero_finding_html = ""

    # Dashboard archetype: methodology footer at the bottom of the page,
    # paired with sample size text. Required by audit C3.
    _methodology_footer_html = render_methodology_footer(
        page="Vibe Shifts",
        sample_summary=(
            f"Sample: {len(cards)} teams ranked by absolute power swing"
            if cards else "Sample: no qualifying games yet this week"
        ),
        prefix="/",
    )

    return _PAGE_TEMPLATE.format(
        season_year=season_year, week=week, week_label=week_label, body=body,
        head_chrome=head_chrome,
        hero_finding=_hero_finding_html,
        methodology_footer=_methodology_footer_html,
    )


# ---------------------------------------------------------------------------
# Build entry points
# ---------------------------------------------------------------------------


def build_vibe_shifts_for_week(
    db: Database,
    season_year: int,
    week: int,
    output_dir: str | Path = "output/site",
    *,
    limit: int = 10,
) -> list[Path]:
    """Render the ledger page + per-team SVG share assets for one week.

    Writes to ``output/site/hub/vibe-shifts/<season>/<week>/index.html`` and
    ``.../<team-slug>.svg`` for each ranked team. Returns the list of paths
    written. Safe to call repeatedly; idempotent.
    """
    cards = fetch_vibe_shifts(db, season_year, week, limit=limit)
    out_dir = Path(output_dir) / "hub" / "vibe-shifts" / str(season_year) / str(week)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for rank, card in enumerate(cards, start=1):
        svg = render_vibe_shift_card_svg(card, week=week, season_year=season_year, rank=rank)
        svg_path = out_dir / f"{card['team_slug']}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        written.append(svg_path)
    index_path = out_dir / "index.html"
    index_path.write_text(render_vibe_shifts_index_html(season_year, week, cards), encoding="utf-8")
    written.append(index_path)
    return written


def build_vibe_shifts_section(
    db: Database,
    output_dir: str | Path = "output/site",
    *,
    max_weeks: int = 4,
    min_games: int = 10,
) -> list[Path]:
    """Render the latest ``max_weeks`` ledger pages.

    Picks the most-recent (season, week) with ≥ ``min_games`` games, plus up
    to ``max_weeks - 1`` immediately-prior weeks. Also writes a tiny
    ``/hub/vibe-shifts/index.html`` that redirects to the latest week so
    the URL ``/hub/vibe-shifts/`` always points somewhere current.

    Never raises; on any DB failure logs and returns ``[]``. The build
    pipeline can call this unconditionally.
    """
    try:
        latest = latest_vibe_shifts_week(db, min_games=min_games)
    except Exception as exc:
        print(f"[vibe-shifts] cannot determine latest week ({type(exc).__name__}): {exc}")
        return []
    if not latest:
        print("[vibe-shifts] no qualifying weeks in DB; section skipped")
        return []

    season_year, latest_week = latest
    weeks_to_build = list(range(max(1, latest_week - max_weeks + 1), latest_week + 1))
    written: list[Path] = []
    for w in weeks_to_build:
        try:
            written.extend(build_vibe_shifts_for_week(db, season_year, w, output_dir))
        except Exception as exc:
            print(f"[vibe-shifts] week {w} skipped ({type(exc).__name__}): {exc}")

    # Top-level redirect index so /hub/vibe-shifts/ doesn't 404.
    root = Path(output_dir) / "hub" / "vibe-shifts"
    root.mkdir(parents=True, exist_ok=True)
    redirect = (
        '<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url=/hub/vibe-shifts/{season_year}/{latest_week}/">'
        f'<title>Vibe Shifts</title>'
        f'<p>Redirecting to <a href="/hub/vibe-shifts/{season_year}/{latest_week}/">the latest ledger</a>.</p>'
    )
    redirect_path = root / "index.html"
    redirect_path.write_text(redirect, encoding="utf-8")
    written.append(redirect_path)
    return written
