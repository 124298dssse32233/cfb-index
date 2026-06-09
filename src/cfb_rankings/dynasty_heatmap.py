"""Dynasty Heatmap — programs × years grid colored by final-power percentile.

R4 from docs/octopus/next-roadmap.md. A single visual that lets a fan see
which programs were dominant in which years, ranked by twelve-year average.
The kind of "fifty years in one image" artifact Sports Reference has the
data for but never ships. Renders at ``/history/heatmap/``.

Data:
  - ``power_ratings_weekly`` — final-week power per (team, season)
  - ``teams`` + ``conferences`` for labels + grouping

Defensive: the public ``build_dynasty_heatmap`` entry point never raises;
on DB error it logs and returns ``[]`` so the site build pipeline keeps
going even if this module is broken.
"""

from __future__ import annotations

from bisect import bisect_left
from html import escape

from cfb_rankings.utils import ordinal_suffix as _ordinal
from pathlib import Path
from typing import Any

from cfb_rankings.charts import (
    ANNOTATION_CSS,
    Annotation,
    CHART_CARD_CSS,
    render_annotation_overlay,
    render_chart_card,
)
from cfb_rankings.db import Database


# Year range for the headline visual. 2014 is when the CFP era begins;
# 2025 is the most-recent complete season in the data. Configurable here
# so future seasons just need a constant bump.
DEFAULT_YEAR_START = 2014
DEFAULT_YEAR_END = 2025


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


def fetch_final_powers(
    db: Database,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
    *,
    level_code: str = "FBS",
) -> list[dict[str, Any]]:
    """Return one row per (team, season) with the team's final-week power.

    Window function picks the latest week per (team, year); a correlated
    subquery here would be O(n²) on the 575k-row table.
    """
    sql = """
        with final_power as (
          select pw.team_id, pw.season_year, pw.power_rating,
                 row_number() over (
                   partition by pw.team_id, pw.season_year
                   order by pw.week desc
                 ) as rn
          from power_ratings_weekly pw
        )
        select
          fp.team_id,
          fp.season_year,
          fp.power_rating,
          t.canonical_name as team_name,
          t.slug as team_slug,
          t.level_code,
          c.conference_name
        from final_power fp
        join teams t on t.team_id = fp.team_id
        left join conferences c on c.conference_id = t.current_conference_id
        where fp.rn = 1
          and t.level_code = :level
          and fp.season_year between :ys and :ye
        order by fp.season_year, t.canonical_name
    """
    rows = db.query_all(
        sql,
        {"level": level_code, "ys": year_start, "ye": year_end},
    ) or []
    return [
        {
            "team_id": int(r["team_id"]),
            "season_year": int(r["season_year"]),
            "power_rating": float(r["power_rating"] or 0.0),
            "team_name": str(r["team_name"] or ""),
            "team_slug": str(r["team_slug"] or ""),
            "level_code": str(r["level_code"] or ""),
            "conference_name": str(r["conference_name"] or ""),
        }
        for r in rows
    ]


def compute_year_percentiles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Augment each row with ``percentile`` ∈ [0, 100] within its year cohort.

    Percentile = (n_below + n_equal / 2) / n_total — the "midrank" definition,
    which is robust to ties and stable for visualization.
    """
    by_year: dict[int, list[float]] = {}
    for r in rows:
        by_year.setdefault(r["season_year"], []).append(r["power_rating"])
    year_sorted = {y: sorted(vals) for y, vals in by_year.items()}

    out: list[dict[str, Any]] = []
    for r in rows:
        year = r["season_year"]
        vals_sorted = year_sorted[year]
        v = r["power_rating"]
        # Number of values strictly less than v
        lo = bisect_left(vals_sorted, v)
        # Number of values equal to v (handle ties via midrank)
        hi = lo
        while hi < len(vals_sorted) and vals_sorted[hi] == v:
            hi += 1
        n_equal = hi - lo
        midrank = lo + (n_equal / 2.0)
        pct = 100.0 * midrank / max(len(vals_sorted), 1)
        out.append({**r, "percentile": pct})
    return out


# ---------------------------------------------------------------------------
# Color mapping
# ---------------------------------------------------------------------------


def _percentile_color(pct: float) -> str:
    """Map a percentile ∈ [0, 100] to a warm-to-cool hex color.

    Stops:
      0  – cool deep blue  (#1f3a68)
      25 – muted blue      (#5d7ea8)
      50 – neutral gray    (#d8d2c4)
      75 – warm orange     (#e07b3a)
      100 – hot red        (#a01818)
    Linearly interpolated between stops in sRGB.
    """
    stops = [
        (0.0, (31, 58, 104)),
        (25.0, (93, 126, 168)),
        (50.0, (216, 210, 196)),
        (75.0, (224, 123, 58)),
        (100.0, (160, 24, 24)),
    ]
    p = max(0.0, min(100.0, pct))
    for i in range(len(stops) - 1):
        a_p, a_rgb = stops[i]
        b_p, b_rgb = stops[i + 1]
        if p <= b_p:
            t = (p - a_p) / (b_p - a_p) if b_p > a_p else 0.0
            r = int(round(a_rgb[0] + t * (b_rgb[0] - a_rgb[0])))
            g = int(round(a_rgb[1] + t * (b_rgb[1] - a_rgb[1])))
            b = int(round(a_rgb[2] + t * (b_rgb[2] - a_rgb[2])))
            return f"#{r:02x}{g:02x}{b:02x}"
    last = stops[-1][1]
    return f"#{last[0]:02x}{last[1]:02x}{last[2]:02x}"


# ---------------------------------------------------------------------------
# SVG grid renderer
# ---------------------------------------------------------------------------


def _team_index(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the y-axis: one entry per team, sorted by 12-year avg percentile (desc).

    Excludes teams with < 6 seasons of data so the rendering stays clean
    (a one-year fluke shouldn't anchor at the top of the leaderboard).
    """
    by_team: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        by_team.setdefault(r["team_id"], []).append(r)
    teams: list[dict[str, Any]] = []
    for team_id, items in by_team.items():
        if len(items) < 6:
            continue
        first = items[0]
        avg_pct = sum(i["percentile"] for i in items) / len(items)
        teams.append({
            "team_id": team_id,
            "team_name": first["team_name"],
            "team_slug": first["team_slug"],
            "conference_name": first["conference_name"],
            "level_code": first["level_code"],
            "avg_percentile": avg_pct,
            "n_seasons": len(items),
        })
    teams.sort(key=lambda r: (-r["avg_percentile"], r["team_name"]))
    return teams


def _peak_dynasty_annotation(
    teams: list[dict[str, Any]],
    cell_lookup: dict[tuple[int, int], dict[str, Any]],
    years: list[int],
    *,
    label_w: int,
    cell_w: int,
    cell_h: int,
    header_h: int,
) -> list[Annotation]:
    """One NYT-Upshot callout on the era's dynasty at its single best season.

    The takeaway cards name the dynasty in prose; this puts the same claim ON
    the chart — a marker on the program's brightest cell so the eye lands on
    the top warm band without reading a caption. Mirrors the era-trajectory
    annotation discipline (the chart self-narrates). Empty when there's no data.
    """
    if not teams or not years:
        return []
    dynasty = teams[0]
    tid = dynasty["team_id"]
    # Brightest season = max within-year percentile across the displayed window.
    peak_year: int | None = None
    peak_pct = -1.0
    for yi, year in enumerate(years):
        cell = cell_lookup.get((tid, year))
        if cell is None:
            continue
        pct = float(cell["percentile"])
        if pct > peak_pct:
            peak_pct = pct
            peak_year = year
    if peak_year is None:
        return []

    ci = years.index(peak_year)
    cx = label_w + ci * cell_w + (cell_w - 1) / 2.0
    cy = header_h + 0 * cell_h + (cell_h - 1) / 2.0  # dynasty is row 0

    # Place below the dot so the box never collides with the year header; swing
    # left when the peak sits in the right half so the box stays on-canvas.
    placement = "below-left" if ci >= len(years) / 2 else "below-right"
    return [
        Annotation(
            cx,
            cy,
            [
                f"{dynasty['team_name']}, {peak_year}",
                f"{peak_pct:.0f}th percentile — its peak",
            ],
            placement=placement,
        )
    ]


def render_dynasty_heatmap_svg(
    rows: list[dict[str, Any]],
    *,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
    cell_h: int = 16,
    cell_w: int = 52,
    label_w: int = 220,
    header_h: int = 64,
    footer_h: int = 80,
    annotate: bool = True,
) -> str:
    """Return a self-contained SVG of the dynasty heatmap.

    One row per qualifying team (≥ 6 seasons of data), one column per
    year in [year_start, year_end]. Cells are colored by within-year
    percentile. Hover tooltip via SVG ``<title>``.
    """
    teams = _team_index(rows)
    years = list(range(year_start, year_end + 1))
    # Map (team_id, year) -> row for O(1) lookup
    cell_lookup: dict[tuple[int, int], dict[str, Any]] = {
        (r["team_id"], r["season_year"]): r for r in rows
    }

    width = label_w + len(years) * cell_w + 32
    height = header_h + len(teams) * cell_h + footer_h

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Dynasty heatmap of college football programs {year_start}-{year_end}" '
        f'style="font-family: system-ui, -apple-system, sans-serif; background: #fff;">'
    )

    # Header: year labels
    parts.append('<g class="dh-header">')
    for i, year in enumerate(years):
        x = label_w + i * cell_w + cell_w / 2
        parts.append(
            f'<text x="{x:.0f}" y="{header_h - 18}" text-anchor="middle" '
            f'font-size="13" font-weight="700" fill="#0a0a0a">{year}</text>'
        )
    parts.append(
        f'<line x1="0" y1="{header_h - 6}" x2="{width}" y2="{header_h - 6}" stroke="#999" stroke-width="1"/>'
    )
    parts.append('</g>')

    # Rows
    parts.append('<g class="dh-rows">')
    for ri, team in enumerate(teams):
        y = header_h + ri * cell_h
        # Team label (right-aligned, then a gap before cells)
        parts.append(
            f'<a href="/programs/{escape(team["team_slug"])}.html">'
            f'<text x="{label_w - 12}" y="{y + cell_h - 4}" '
            f'text-anchor="end" font-size="11" font-weight="600" fill="#0a0a0a">'
            f'{escape(team["team_name"])}</text></a>'
        )
        # Cells per year
        for ci, year in enumerate(years):
            cell = cell_lookup.get((team["team_id"], year))
            x = label_w + ci * cell_w
            if cell is None:
                # Empty cell — light hatched fill
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{cell_w - 1}" height="{cell_h - 1}" '
                    f'fill="#f0eee9" stroke="#e1ddd2" stroke-width="0.5"/>'
                )
                continue
            color = _percentile_color(cell["percentile"])
            title = (
                f'{escape(team["team_name"])} · {year} · '
                f'Power {cell["power_rating"]:+.2f} · '
                f'{cell["percentile"]:.0f}th pct'
            )
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - 1}" height="{cell_h - 1}" '
                f'fill="{color}">'
                f'<title>{title}</title></rect>'
            )
        # Average percentile badge to the right of each row
        avg_x = label_w + len(years) * cell_w + 8
        parts.append(
            f'<text x="{avg_x}" y="{y + cell_h - 4}" font-size="10" '
            f'fill="#666" font-variant-numeric="tabular-nums">'
            f'{team["avg_percentile"]:.0f}</text>'
        )
    parts.append('</g>')

    # Footer legend
    fy = header_h + len(teams) * cell_h + 28
    parts.append('<g class="dh-legend">')
    parts.append(
        f'<text x="{label_w - 12}" y="{fy}" text-anchor="end" font-size="11" '
        f'font-weight="700" fill="#0a0a0a">Within-year percentile →</text>'
    )
    legend_w = 240
    legend_x = label_w
    for i in range(0, 101, 5):
        seg_w = legend_w / 20
        cx = legend_x + (i / 5) * seg_w
        parts.append(
            f'<rect x="{cx:.1f}" y="{fy - 12}" width="{seg_w:.1f}" height="14" '
            f'fill="{_percentile_color(i)}" stroke="none"/>'
        )
    for label_pct in (0, 50, 100):
        cx = legend_x + (label_pct / 100) * legend_w
        parts.append(
            f'<text x="{cx:.0f}" y="{fy + 16}" font-size="10" text-anchor="middle" '
            f'fill="#666">{label_pct}</text>'
        )
    parts.append(
        f'<text x="{legend_x + legend_w + 36}" y="{fy}" font-size="11" fill="#666">'
        f'Empty = not in {next(iter(rows))["level_code"] if rows else "FBS"} that year</text>'
    )
    parts.append('</g>')

    # Editorial overlay: a single callout on the era's dynasty at its peak so
    # the chart narrates its own headline (annotation discipline, WS-08). Lives
    # inside this viewBox, so it scales with the chart on mobile.
    if annotate:
        overlay = render_annotation_overlay(
            _peak_dynasty_annotation(
                teams, cell_lookup, years,
                label_w=label_w, cell_w=cell_w, cell_h=cell_h, header_h=header_h,
            ),
            width=width,
            height=height,
        )
        if overlay:
            parts.append(overlay)

    parts.append('</svg>')
    return "".join(parts)


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------

_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dynasty Heatmap — {year_start}-{year_end} · CFB Index</title>
<meta name="description" content="Every FBS program, every year from {year_start} through {year_end}, colored by where it finished in that year's power-rating distribution. One image, twelve seasons of the CFP era.">
{head_chrome}
<link rel="stylesheet" href="/assets/css/site.css">
<style>
  .dh-wrap {{ overflow-x: auto; margin: 24px 0; border: 1px solid var(--border, #d8d8d8); border-radius: 12px; }}
  .dh-wrap svg {{ display: block; max-width: 100%; height: auto; }}
  .dh-eyebrow {{ font-size: 13px; letter-spacing: 2px; color: var(--muted-foreground, #666); font-weight: 700; }}
  .dh-takeaways {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin: 24px 0; }}
  .dh-takeaway {{ padding: 16px; border: 1px solid var(--border, #d8d8d8); border-radius: 10px; }}
  .dh-takeaway__label {{ font-size: 11px; letter-spacing: 1.5px; color: var(--muted-foreground, #666); font-weight: 700; }}
  .dh-takeaway__value {{ font-size: 20px; font-weight: 800; margin: 4px 0 6px; }}
  .dh-takeaway__why {{ font-size: 13px; color: var(--muted-foreground, #555); line-height: 1.4; }}
  .dh-wrap .chart-card {{ margin: 0; }}
{chart_card_css}
{annotation_css}
</style>
</head>
<body class="dynasty-heatmap-page">
<main class="site-shell" id="main-content">
  <section class="hero">
    <p class="eyebrow">The Dynasty Heatmap · {year_start}-{year_end}</p>
    <h1>Twelve seasons. Every program. One image.</h1>
    <p class="lede">Each row is a college football program. Each column is a year. Each cell is colored by where that team finished in its year's power-rating distribution — warm for dominant, cool for irrelevant. Teams are sorted by twelve-year average percentile, so the rows at the top are the programs that ran the era.</p>
    <p class="section-note">The CFP era as a single argument. Hover any cell for the year-specific power rating + percentile.</p>
  </section>
  <section class="section">
    <div class="dh-takeaways">
      {takeaways_html}
    </div>
  </section>
  <section class="section">
    <div class="dh-wrap">
      {svg_html}
    </div>
    <p class="muted" style="margin-top:8px;font-size:13px;">
      Number to the right of each row = twelve-year average percentile. Cells use within-year percentile, so a 50 in 2022 means "median FBS team in 2022" — not the same absolute power rating as a 50 in 2014.
    </p>
  </section>
  <section class="section">
    <h2>How to read it</h2>
    <p>Look for <strong>solid warm bands</strong> — those are dynasties. Look for <strong>swings from cool to warm</strong> — those are turnarounds (Indiana 2024-25, James Madison's FBS arrival). Look for <strong>warm-then-cool collapses</strong> — those are hard landings (USC post-2017, FSU 2024).</p>
    <p class="muted">Full methodology at <a href="/about-model/">/about-model/</a>.</p>
  </section>
</main>
</body>
</html>
"""


def _build_takeaways_html(teams: list[dict[str, Any]], rows: list[dict[str, Any]]) -> str:
    """Three single-stat cards above the heatmap — anchors the eye."""
    if not teams:
        return '<p class="muted">No data yet.</p>'
    # Dynasty: top by 12-year avg percentile
    dynasty = teams[0]
    # Hard landing: program with the largest negative slope (recent dropoff)
    by_team_recent_avg: dict[int, tuple[float, float]] = {}
    for r in rows:
        avg = by_team_recent_avg.setdefault(r["team_id"], (0.0, 0.0))
        # Track sum, count for two halves
        # (simplified: just store sum of last 4 years pct vs first 4)
    # Simpler: scan teams list for the one with biggest decline early-vs-late
    team_year_pcts: dict[int, dict[int, float]] = {}
    for r in rows:
        team_year_pcts.setdefault(r["team_id"], {})[r["season_year"]] = r["percentile"]
    declines: list[tuple[float, dict[str, Any]]] = []
    rises: list[tuple[float, dict[str, Any]]] = []
    years_sorted = sorted({r["season_year"] for r in rows})
    if len(years_sorted) >= 6:
        early = years_sorted[: len(years_sorted) // 2]
        late = years_sorted[-(len(years_sorted) // 2):]
        for t in teams:
            yps = team_year_pcts.get(t["team_id"], {})
            early_vals = [yps[y] for y in early if y in yps]
            late_vals = [yps[y] for y in late if y in yps]
            if len(early_vals) < 3 or len(late_vals) < 3:
                continue
            delta = (sum(late_vals) / len(late_vals)) - (sum(early_vals) / len(early_vals))
            if delta < 0:
                declines.append((delta, t))
            else:
                rises.append((delta, t))
    hard_landing = (
        sorted(declines, key=lambda x: x[0])[0][1]
        if declines else None
    )
    return_to_relevance = (
        sorted(rises, key=lambda x: -x[0])[0][1]
        if rises else None
    )

    cards: list[str] = []
    cards.append(
        '<div class="dh-takeaway">'
        '<div class="dh-takeaway__label">CFP-ERA DYNASTY</div>'
        f'<div class="dh-takeaway__value">{escape(dynasty["team_name"])}</div>'
        f'<div class="dh-takeaway__why">{int(dynasty["avg_percentile"])}{_ordinal(int(dynasty["avg_percentile"]))} percentile average across {dynasty["n_seasons"]} seasons — the program with the most concentrated dominance of the bracket era.</div>'
        '</div>'
    )
    if hard_landing:
        cards.append(
            '<div class="dh-takeaway">'
            '<div class="dh-takeaway__label">HARDEST LANDING</div>'
            f'<div class="dh-takeaway__value">{escape(hard_landing["team_name"])}</div>'
            f'<div class="dh-takeaway__why">Biggest drop from the first half of the window to the second. The hardest fall on the board.</div>'
            '</div>'
        )
    if return_to_relevance:
        cards.append(
            '<div class="dh-takeaway">'
            '<div class="dh-takeaway__label">RETURN TO RELEVANCE</div>'
            f'<div class="dh-takeaway__value">{escape(return_to_relevance["team_name"])}</div>'
            f'<div class="dh-takeaway__why">Biggest rise from the first half of the window to the second. The era\'s clearest comeback.</div>'
            '</div>'
        )
    return "".join(cards)


def render_dynasty_heatmap_page(
    rows: list[dict[str, Any]],
    *,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
) -> str:
    from cfb_rankings.common.head_chrome import render_head_chrome

    teams = _team_index(rows)
    svg = render_dynasty_heatmap_svg(
        rows, year_start=year_start, year_end=year_end,
    )
    # Route the heatmap through the shared chart-card shell so it carries the
    # standardized source-receipt footer (WS-08 "every chart renders through
    # the shared component"). The page hero owns the headline/lede.
    chart_html = render_chart_card(
        svg,
        source=f"CFB Index · final-week closing power rating per season, {year_start}-{year_end}",
    )
    takeaways_html = _build_takeaways_html(teams, rows)
    head_chrome = render_head_chrome(
        page_path="/history/heatmap/",
        title=f"Dynasty Heatmap — {year_start}-{year_end} · CFB Index",
        description=(
            f"Every FBS program, every year from {year_start} through "
            f"{year_end}, colored by where it finished in that year's "
            "power-rating distribution. One image, twelve seasons of "
            "the CFP era."
        ),
        og_type="article",
    )
    return _PAGE_TEMPLATE.format(
        year_start=year_start,
        year_end=year_end,
        svg_html=chart_html,
        takeaways_html=takeaways_html,
        head_chrome=head_chrome,
        chart_card_css=CHART_CARD_CSS,
        annotation_css=ANNOTATION_CSS,
    )


# ---------------------------------------------------------------------------
# Build entry point
# ---------------------------------------------------------------------------


def build_dynasty_heatmap(
    db: Database,
    output_dir: str | Path = "output/site",
    *,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
) -> list[Path]:
    """Render ``/history/heatmap/`` (index.html + a downloadable share-card SVG).

    Defensive: never raises. Returns ``[]`` on DB error.
    """
    try:
        raw = fetch_final_powers(db, year_start=year_start, year_end=year_end)
    except Exception as exc:
        print(f"[dynasty-heatmap] fetch failed ({type(exc).__name__}): {exc}")
        return []
    if not raw:
        print("[dynasty-heatmap] no power_ratings_weekly data in window; skipping")
        return []
    enriched = compute_year_percentiles(raw)

    out_dir = Path(output_dir) / "history" / "heatmap"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # 1) Page
    page_html = render_dynasty_heatmap_page(
        enriched, year_start=year_start, year_end=year_end,
    )
    page_path = out_dir / "index.html"
    page_path.write_text(page_html, encoding="utf-8")
    written.append(page_path)

    # 2) Standalone share-card SVG (same renderer, downloadable). No annotation
    # overlay here: it's class-styled and a bare .svg carries no stylesheet, so
    # the callout only renders on the page (which ships ANNOTATION_CSS).
    svg = render_dynasty_heatmap_svg(
        enriched, year_start=year_start, year_end=year_end, annotate=False,
    )
    svg_path = out_dir / f"dynasty-heatmap-{year_start}-{year_end}.svg"
    svg_path.write_text(svg, encoding="utf-8")
    written.append(svg_path)

    return written
