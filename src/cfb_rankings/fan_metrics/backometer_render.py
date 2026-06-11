"""Backometer hub + share cards — the Noir suite's flagship surface.

Renders ``/hub/backometer/<season>/<week>/`` as a board of qualifying teams
(n >= floor), each with a "fanbase on a heart monitor" chart and a 1200x675
standalone SVG share card, plus a LOW SIGNAL section that honors the
publication floor instead of hiding it. Clones the vibe_shifts module shape:
standalone module, per-week dirs, root redirect, never crashes the build.

Visual language: docs/design-system/40-noir-subbrand.md (Group Chat Noir).
Forced-dark by design — these are screenshot surfaces. Share cards use font
fallbacks (Anton -> Arial Narrow -> sans) so the standalone .svg travels.

Data: backometer_weekly (written by `manage.py compute-backometer`).
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.common.head_chrome import absolute_url
from cfb_rankings.db import Database
from cfb_rankings.fan_metrics.backometer import MIN_SAMPLE, load_zone_labels


def og_card_meta(title: str, description: str, image_site_path: str | None) -> str:
    """Standard og:image + twitter:card block for a Noir hub page.

    ``image_site_path`` is a site-relative path to the representative card PNG;
    it is absolutized so social crawlers see a full URL (OG spec requirement).
    """
    from html import escape as _esc
    tags = [
        f'<meta property="og:title" content="{_esc(title)}">',
        f'<meta property="og:description" content="{_esc(description)}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="THE CFB INDEX">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{_esc(title)}">',
        f'<meta name="twitter:description" content="{_esc(description)}">',
    ]
    if image_site_path:
        img = _esc(absolute_url(image_site_path))
        tags += [
            f'<meta property="og:image" content="{img}">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="675">',
            f'<meta name="twitter:image" content="{img}">',
        ]
    return "".join(tags)

# Noir tokens (spec §3) — duplicated as constants because share-card SVGs are
# standalone files that cannot reference site CSS variables.
GROUND = "#101418"
SURFACE = "#1B2128"
CHALK = "#EDE6D6"
RECEIPT = "#B8B2A4"
HAIRLINE = "rgba(237,230,214,0.10)"
UP = "#2EE07C"
DOWN = "#FF4E42"

ZONE_COLORS = {
    "so_back": "#2EE07C",
    "cooking": "#8FD14F",
    "uneasy": "#A8A294",
    "cooked": "#F0883E",
    "so_over": "#FF4E42",
}

_DISPLAY_STACK = "Anton, 'Arial Narrow', 'Helvetica Neue', sans-serif"
_MONO_STACK = "'IBM Plex Mono', ui-monospace, 'Courier New', monospace"
_SANS_STACK = "Inter, system-ui, -apple-system, sans-serif"


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def latest_backometer_week(db: Database) -> tuple[int, int] | None:
    row = db.query_one(
        """
        select season_year, max(week) as week
        from backometer_weekly
        where season_year = (select max(season_year) from backometer_weekly)
        group by season_year
        """
    )
    if not row or row.get("week") is None:
        return None
    return int(row["season_year"]), int(row["week"])


def fetch_backometer_board(db: Database, season_year: int, week: int) -> dict[str, Any]:
    rows = db.query_all(
        """
        select b.*, t.canonical_name as team_name, t.slug as team_slug
        from backometer_weekly b
        join teams t on t.team_id = b.team_id
        where b.season_year = :season and b.week = :week
        order by b.score desc
        """,
        {"season": season_year, "week": week},
    )
    qualifying = [r for r in rows if not int(r.get("is_low_signal") or 0)]
    low_signal = [r for r in rows if int(r.get("is_low_signal") or 0)]
    low_signal.sort(key=lambda r: -int(r.get("sample_size") or 0))
    return {"qualifying": qualifying, "low_signal": low_signal}


def fetch_backometer_trail(
    db: Database, season_year: int, team_id: int, thru_week: int
) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select week, score, zone, sample_size, is_low_signal, week_start_date
        from backometer_weekly
        where season_year = :season and team_id = :team_id and week <= :week
        order by week
        """,
        {"season": season_year, "team_id": team_id, "week": thru_week},
    )


# ---------------------------------------------------------------------------
# Heart-monitor SVG fragment (shared by card + hub)
# ---------------------------------------------------------------------------

def _monitor_svg_fragment(
    trail: list[dict[str, Any]],
    *,
    x0: float, x1: float, y_top: float, y_bottom: float,
    zone_color: str,
    clip_prefix: str,
) -> str:
    """The trace + baseline + green/ember masses, mapped into a pixel box.

    Score 0-100 maps to y_bottom..y_top; baseline 50 sits mid-box. Low-signal
    weeks render as gaps in the trace (spec §6: never interpolate through a
    gap), drawn as separate polyline segments.
    """
    if not trail:
        return ""
    y_mid = (y_top + y_bottom) / 2.0

    def x_for(i: int) -> float:
        if len(trail) == 1:
            return (x0 + x1) / 2.0
        return x0 + (x1 - x0) * (i / (len(trail) - 1))

    def y_for(score: float) -> float:
        return y_bottom - (max(0.0, min(100.0, score)) / 100.0) * (y_bottom - y_top)

    points = [
        (x_for(i), y_for(float(r["score"])), bool(int(r.get("is_low_signal") or 0)))
        for i, r in enumerate(trail)
    ]

    # Split into contiguous qualifying segments; low-signal weeks break the line.
    segments: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for (px, py, low) in points:
        if low:
            if current:
                segments.append(current)
                current = []
        else:
            current.append((px, py))
    if current:
        segments.append(current)

    parts: list[str] = []
    # Area masses use the full trail (including low-signal weeks at reduced
    # certainty) so the season shape stays readable; the broken trace carries
    # the honesty signal.
    poly_pts = " ".join(f"{px:.1f},{py:.1f}" for (px, py, _low) in points)
    closed = f"{poly_pts} {points[-1][0]:.1f},{y_mid:.1f} {points[0][0]:.1f},{y_mid:.1f}"
    parts.append(
        f'<defs>'
        f'<clipPath id="{clip_prefix}-above"><rect x="0" y="0" width="1200" height="{y_mid:.1f}"/></clipPath>'
        f'<clipPath id="{clip_prefix}-below"><rect x="0" y="{y_mid:.1f}" width="1200" height="675"/></clipPath>'
        f'</defs>'
    )
    parts.append(f'<polygon clip-path="url(#{clip_prefix}-above)" fill="rgba(46,224,124,0.16)" points="{closed}"/>')
    parts.append(f'<polygon clip-path="url(#{clip_prefix}-below)" fill="rgba(255,78,66,0.16)" points="{closed}"/>')
    parts.append(
        f'<line x1="{x0:.1f}" y1="{y_mid:.1f}" x2="{x1:.1f}" y2="{y_mid:.1f}" '
        f'stroke="rgba(237,230,214,0.25)" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{x0:.1f}" y="{y_mid + 22:.1f}" fill="{RECEIPT}" font-size="16" '
        f'font-family="{_MONO_STACK}">BASELINE · 50</text>'
    )
    for seg in segments:
        if len(seg) == 1:
            parts.append(f'<circle cx="{seg[0][0]:.1f}" cy="{seg[0][1]:.1f}" r="4" fill="{CHALK}"/>')
        else:
            seg_pts = " ".join(f"{px:.1f},{py:.1f}" for (px, py) in seg)
            parts.append(
                f'<polyline fill="none" stroke="{CHALK}" stroke-width="3.5" '
                f'stroke-linejoin="round" stroke-linecap="round" points="{seg_pts}"/>'
            )
    # Terminal dot on the final point (whatever its signal state).
    tx, ty, _ = points[-1]
    parts.append(
        f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="9" fill="{zone_color}" stroke="{GROUND}" stroke-width="3"/>'
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Share card (1200x675 standalone SVG)
# ---------------------------------------------------------------------------

def render_backometer_card_svg(
    row: dict[str, Any],
    trail: list[dict[str, Any]],
    *,
    season_year: int,
    week: int,
    zone_labels: dict[str, str],
) -> str:
    zone_id = str(row.get("zone") or "uneasy")
    zone_color = ZONE_COLORS.get(zone_id, ZONE_COLORS["uneasy"])
    zone_word = zone_labels.get(zone_id, zone_id.upper())
    score = float(row.get("score") or 0.0)
    n = int(row.get("sample_size") or 0)
    sources = int(row.get("source_count") or 0)
    team = str(row.get("team_name") or "")
    delta = row.get("delta_wow")
    is_off = int(row.get("is_offseason") or 0)
    week_label = (
        f"WEEK OF {row.get('week_start_date')}" if is_off and row.get("week_start_date")
        else f"WEEK {week} · {season_year}"
    )
    delta_txt = ""
    if delta is not None:
        arrow = "▲" if float(delta) >= 0 else "▼"
        d_color = UP if float(delta) >= 0 else DOWN
        delta_txt = (
            f'<text x="1120" y="208" fill="{d_color}" text-anchor="end" font-size="30" '
            f'font-family="{_MONO_STACK}">{arrow} {abs(float(delta)):.1f} WOW</text>'
        )

    monitor = _monitor_svg_fragment(
        trail, x0=80, x1=1120, y_top=300, y_bottom=545,
        zone_color=zone_color, clip_prefix="bm",
    )
    source_word = "source" if sources == 1 else "sources"
    receipt = (
        f"n={n:,} fan conversations · {sources} {source_word} · sarcasm-adjusted · "
        f"floor n≥{MIN_SAMPLE}"
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="The Backometer: {escape(team)} is {escape(zone_word)} at {score:.0f}">
  <rect x="0" y="0" width="1200" height="675" rx="24" fill="{GROUND}"/>
  <rect x="1.5" y="1.5" width="1197" height="672" rx="23" fill="none" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="80" y="78" fill="{RECEIPT}" font-size="22" letter-spacing="4"
        font-family="{_MONO_STACK}">THE BACKOMETER™ · {escape(week_label)}</text>
  <text x="80" y="135" fill="{CHALK}" font-size="40" font-weight="700"
        font-family="{_SANS_STACK}">{escape(team)}</text>
  <text x="80" y="248" fill="{zone_color}" font-size="104"
        font-family="{_DISPLAY_STACK}" letter-spacing="2">{escape(zone_word)}</text>
  <text x="1120" y="160" fill="{zone_color}" text-anchor="end" font-size="120"
        font-family="{_DISPLAY_STACK}" font-variant-numeric="tabular-nums">{score:.0f}</text>
  {delta_txt}
  <text x="80" y="330" fill="{UP}" font-size="16" font-family="{_MONO_STACK}">SO BACK ↑</text>
  <text x="80" y="572" fill="{DOWN}" font-size="16" font-family="{_MONO_STACK}">IT'S SO OVER ↓</text>
  {monitor}
  <line x1="80" y1="608" x2="1120" y2="608" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="80" y="644" fill="{RECEIPT}" font-size="20"
        font-family="{_MONO_STACK}">{escape(receipt)}</text>
  <text x="1120" y="644" fill="{RECEIPT}" text-anchor="end" font-size="20"
        font-family="{_MONO_STACK}">cfbindex.com</text>
</svg>"""


# ---------------------------------------------------------------------------
# Hub page
# ---------------------------------------------------------------------------

_HUB_CSS = f"""
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {GROUND}; color: {CHALK};
    font-family: {_SANS_STACK}; font-feature-settings: "tnum";
    line-height: 1.5; padding: 40px 16px 80px;
  }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  .eyebrow {{
    font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500;
    color: {RECEIPT}; letter-spacing: .12em; text-transform: uppercase;
    margin-bottom: 10px;
  }}
  h1 {{
    font-family: {_DISPLAY_STACK}; font-weight: 400; text-transform: uppercase;
    font-size: clamp(40px, 7vw, 62px); line-height: 1.05; margin-bottom: 8px;
  }}
  .lede {{ color: {RECEIPT}; font-size: 15px; max-width: 62ch; margin-bottom: 40px; }}
  .card {{
    background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 12px;
    margin-bottom: 28px; overflow: hidden;
  }}
  .card svg {{ display: block; width: 100%; height: auto; }}
  .card-foot {{
    display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
    padding: 10px 18px; border-top: 1px solid {HAIRLINE};
    font-family: {_MONO_STACK}; font-size: 12px; color: {RECEIPT};
  }}
  .card-foot a {{ color: {RECEIPT}; }}
  .low {{ margin-top: 44px; }}
  .low h2 {{
    font-family: {_MONO_STACK}; font-size: 13px; font-weight: 500;
    letter-spacing: .12em; color: {RECEIPT}; text-transform: uppercase;
    margin-bottom: 12px;
  }}
  .low table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  .low td {{ padding: 8px 6px; border-bottom: 1px solid {HAIRLINE}; }}
  .low td.num {{ text-align: right; font-variant-numeric: tabular-nums; color: {RECEIPT}; }}
  .foot {{
    margin-top: 48px; padding-top: 16px; border-top: 1px solid {HAIRLINE};
    font-family: {_MONO_STACK}; font-size: 12px; color: {RECEIPT};
  }}
  .foot a {{ color: {RECEIPT}; }}
"""


def render_backometer_index_html(
    season_year: int,
    week: int,
    board: dict[str, Any],
    *,
    zone_labels: dict[str, str],
) -> str:
    qualifying = board["qualifying"]
    low_signal = board["low_signal"]
    low_label = escape(str(zone_labels.get("low_signal_label", "LOW SIGNAL")))

    cards_html = ""
    for row in qualifying:
        slug = escape(str(row["team_slug"]))
        cards_html += (
            f'<div class="card">{row["_svg"]}'
            f'<div class="card-foot">'
            f'<span><a href="/teams/{slug}.html">{escape(str(row["team_name"]))} team page →</a></span>'
            f'<span><a href="{slug}.png" download>download card</a></span>'
            f"</div></div>\n"
        )

    low_rows = "".join(
        f"<tr><td>{escape(str(r['team_name']))}</td>"
        f"<td class='num'>n={int(r.get('sample_size') or 0)}</td>"
        f"<td class='num'>last score {float(r.get('score') or 0):.0f}</td></tr>"
        for r in low_signal[:40]
    )
    low_html = (
        f'<section class="low"><h2>{low_label} — under the n≥{MIN_SAMPLE} floor '
        f"(scores tracked, verdicts withheld)</h2><table>{low_rows}</table></section>"
        if low_rows else ""
    )

    title = f"The Backometer — {season_year} week {week}"
    og_desc = "Weekly fanbase belief, 0-100, from real fan conversations. We're so back / it's so over — with receipts."
    og_img = (
        f"/hub/backometer/{season_year}/{week}/{qualifying[0]['team_slug']}.png"
        if qualifying else None
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · CFB Index</title>
<meta name="description" content="{escape(og_desc)}">
{og_card_meta(title, og_desc, og_img)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{_HUB_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">CFB Index · Fan Intelligence · {escape(str(season_year))} · week {week}</div>
  <h1>The Backometer™</h1>
  <p class="lede">Weekly fanbase belief on a 0–100 scale, computed from real fan conversations
  across Reddit, YouTube, podcasts, and boards — sarcasm-adjusted, sample-floored, and
  honest about uncertainty. Verdicts only publish above n≥{MIN_SAMPLE} conversations.</p>
  {cards_html}
  {low_html}
  <div class="foot">
    Methodology: belief composite over weekly conversation features · zone labels are
    editorial and reviewed against our own slang-lifecycle tracker · hysteresis keeps
    verdicts from flip-flopping at boundaries ·
    <a href="/methodology/fan-intelligence.html">full methodology →</a>
  </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Build entry points (never crash the build)
# ---------------------------------------------------------------------------

def build_backometer_for_week(
    db: Database,
    season_year: int,
    week: int,
    output_dir: str | Path = "output/site",
) -> list[Path]:
    zone_labels = load_zone_labels()
    board = fetch_backometer_board(db, season_year, week)
    if not board["qualifying"] and not board["low_signal"]:
        return []
    out_dir = Path(output_dir) / "hub" / "backometer" / str(season_year) / str(week)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for row in board["qualifying"]:
        trail = fetch_backometer_trail(db, season_year, int(row["team_id"]), week)
        svg = render_backometer_card_svg(
            row, trail, season_year=season_year, week=week, zone_labels=zone_labels,
        )
        row["_svg"] = svg
        svg_path = out_dir / f"{row['team_slug']}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        written.append(svg_path)
    index_path = out_dir / "index.html"
    index_path.write_text(
        render_backometer_index_html(season_year, week, board, zone_labels=zone_labels),
        encoding="utf-8",
    )
    written.append(index_path)
    return written


def build_backometer_section(
    db: Database,
    output_dir: str | Path = "output/site",
    *,
    max_weeks: int = 4,
) -> list[Path]:
    """Render the latest weeks' boards + a root redirect. Never raises."""
    try:
        latest = latest_backometer_week(db)
    except Exception as exc:  # noqa: BLE001
        print(f"[backometer] cannot determine latest week ({type(exc).__name__}): {exc}")
        return []
    if not latest:
        print("[backometer] no backometer_weekly rows; section skipped")
        return []
    season_year, latest_week = latest
    written: list[Path] = []
    for w in range(max(1, latest_week - max_weeks + 1), latest_week + 1):
        try:
            written.extend(build_backometer_for_week(db, season_year, w, output_dir))
        except Exception as exc:  # noqa: BLE001
            print(f"[backometer] week {w} skipped ({type(exc).__name__}): {exc}")
    root = Path(output_dir) / "hub" / "backometer"
    root.mkdir(parents=True, exist_ok=True)
    redirect = (
        '<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url=/hub/backometer/{season_year}/{latest_week}/">'
        "<title>The Backometer</title>"
        f'<p>Redirecting to <a href="/hub/backometer/{season_year}/{latest_week}/">the latest board</a>.</p>'
    )
    redirect_path = root / "index.html"
    redirect_path.write_text(redirect, encoding="utf-8")
    written.append(redirect_path)
    return written


__all__ = [
    "build_backometer_section",
    "build_backometer_for_week",
    "render_backometer_card_svg",
    "render_backometer_index_html",
    "fetch_backometer_board",
    "fetch_backometer_trail",
    "latest_backometer_week",
]
