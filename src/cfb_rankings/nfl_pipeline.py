"""The NFL Pipeline — 12 years of the NFL Draft, ranked by program.

R8 from docs/octopus/next-roadmap.md (a Claude-original feature; neither
Codex nor Gemini surfaced it). Renders ``/nfl-pipeline/`` as a single
leaderboard page that turns ``player_nfl_draft`` (3,077 unused rows) into
the most compelling offseason surface on the site.

Why this exists: 247 ships recruiting; PFF rates current college players;
On3 covers NIL; NFL.com covers the draft itself. None of them connect
the recruiting class → on-field performance → NFL pipeline as ONE
program-level story. This page is the missing connector.

Data:
  - ``player_nfl_draft`` (year, round, pick, overall, college_team_id,
    position, NFL team) — 3,077 rows spanning 2014-2025

Defensive: ``build_nfl_pipeline`` never raises; on DB error logs and
returns ``[]``.
"""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database


DEFAULT_YEAR_START = 2014
DEFAULT_YEAR_END = 2025


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


def fetch_pipeline_summary(
    db: Database,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
) -> list[dict[str, Any]]:
    """Return one row per program with twelve-year + recent-three-year picks.

    Counts: total picks, round-1 picks, "Day 1+2" (rounds 1-3) picks, and
    the recent-3-year subset so the table can show "is the pipeline still
    flowing" alongside "did it flow historically."
    """
    sql = """
        with by_year as (
          select
            d.college_team_id as team_id,
            d.draft_year,
            count(*) as picks,
            sum(case when d.round = 1 then 1 else 0 end) as r1,
            sum(case when d.round <= 3 then 1 else 0 end) as d12
          from player_nfl_draft d
          where d.draft_year between :ys and :ye
            and d.college_team_id is not null
          group by d.college_team_id, d.draft_year
        )
        select
          t.team_id,
          t.canonical_name as team_name,
          t.slug as team_slug,
          t.level_code,
          c.conference_name,
          sum(by_year.picks) as picks_total,
          sum(by_year.r1) as r1_total,
          sum(by_year.d12) as d12_total,
          sum(case when by_year.draft_year >= :recent_start then by_year.picks else 0 end) as picks_recent,
          sum(case when by_year.draft_year >= :recent_start then by_year.r1 else 0 end) as r1_recent
        from by_year
        join teams t on t.team_id = by_year.team_id
        left join conferences c on c.conference_id = t.current_conference_id
        group by t.team_id
        having picks_total > 0
        order by picks_total desc, r1_total desc, t.canonical_name
    """
    rows = db.query_all(
        sql,
        {"ys": year_start, "ye": year_end, "recent_start": year_end - 2},
    ) or []
    return [
        {
            "team_id": int(r["team_id"]),
            "team_name": str(r["team_name"] or ""),
            "team_slug": str(r["team_slug"] or ""),
            "level_code": str(r["level_code"] or ""),
            "conference_name": str(r["conference_name"] or ""),
            "picks_total": int(r["picks_total"] or 0),
            "r1_total": int(r["r1_total"] or 0),
            "d12_total": int(r["d12_total"] or 0),
            "picks_recent": int(r["picks_recent"] or 0),
            "r1_recent": int(r["r1_recent"] or 0),
        }
        for r in rows
    ]


def fetch_top_positions(
    db: Database,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
) -> list[dict[str, Any]]:
    """For each position, the top program that produced it."""
    sql = """
        with by_pos as (
          select position, college_team_id, count(*) as n
          from player_nfl_draft
          where draft_year between :ys and :ye
            and position is not null and position != ''
            and college_team_id is not null
          group by position, college_team_id
        )
        select bp.position, t.canonical_name as team_name, t.slug as team_slug, bp.n
        from by_pos bp
        join teams t on t.team_id = bp.college_team_id
        where (bp.position, bp.n) in (
          select position, max(n) from by_pos group by position
        )
        order by bp.n desc
        limit 14
    """
    rows = db.query_all(sql, {"ys": year_start, "ye": year_end}) or []
    return [
        {
            "position": str(r["position"] or ""),
            "team_name": str(r["team_name"] or ""),
            "team_slug": str(r["team_slug"] or ""),
            "n": int(r["n"] or 0),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------


def _format_signed_delta(recent: int, total: int, years_recent: int, years_total: int) -> str:
    """Return a "+X/yr vs avg" annotation: is the recent pace above or
    below the program's twelve-year average?
    """
    if years_total <= 0:
        return ""
    avg_per_year = total / years_total
    recent_per_year = recent / years_recent if years_recent > 0 else 0.0
    delta = recent_per_year - avg_per_year
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}/yr"


def _render_leaderboard_rows(summary: list[dict[str, Any]], window_years: int, recent_years: int) -> str:
    parts: list[str] = []
    for rank, row in enumerate(summary, start=1):
        delta = _format_signed_delta(
            row["picks_recent"], row["picks_total"], recent_years, window_years,
        )
        delta_cls = "trend-up" if delta.startswith("+") else "trend-down"
        team_link = f'<a href="/teams/{escape(row["team_slug"])}.html">{escape(row["team_name"])}</a>'
        parts.append(f"""
        <tr>
          <td class="rank-cell">{rank}</td>
          <td class="team-cell">{team_link}<span class="submetric">{escape(row["conference_name"])}</span></td>
          <td class="metric-cell">{row["picks_total"]}</td>
          <td class="metric-cell">{row["r1_total"]}</td>
          <td class="metric-cell">{row["d12_total"]}</td>
          <td class="metric-cell">{row["picks_recent"]}</td>
          <td class="metric-cell">{row["r1_recent"]}</td>
          <td class="metric-cell trend {delta_cls}">{escape(delta)}</td>
        </tr>
        """)
    return "".join(parts)


def _render_position_chips(positions: list[dict[str, Any]]) -> str:
    if not positions:
        return ""
    chips: list[str] = []
    for p in positions:
        if p["n"] < 3:  # require ≥3 to feel meaningful
            continue
        chips.append(f"""
        <a class="pos-chip" href="/teams/{escape(p["team_slug"])}.html">
          <span class="pos-chip__pos">{escape(p["position"])}</span>
          <span class="pos-chip__team">{escape(p["team_name"])}</span>
          <span class="pos-chip__n">{p["n"]} picks</span>
        </a>
        """)
    return f'<div class="pos-chip-row">{"".join(chips)}</div>'


_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The NFL Pipeline — 12 years of the Draft by program · CFB Index</title>
<meta name="description" content="Every college football program ranked by NFL Draft output {year_start}-{year_end}. Picks, first-rounders, recent pipeline pace, and the position each program develops best.">
{head_chrome}
<link rel="stylesheet" href="/assets/css/site.css">
<style>
  .pipeline-summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 24px 0; }}
  .pipeline-stat {{ padding: 18px; border: 1px solid var(--border, #d8d8d8); border-radius: 12px; }}
  .pipeline-stat__label {{ font-size: 11px; letter-spacing: 1.5px; color: var(--muted-foreground, #666); font-weight: 700; }}
  .pipeline-stat__value {{ font-size: 28px; font-weight: 900; margin: 6px 0 4px; font-variant-numeric: tabular-nums; }}
  .pipeline-stat__why {{ font-size: 13px; color: var(--muted-foreground, #555); }}
  .pipeline-table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 16px; }}
  .pipeline-table th, .pipeline-table td {{ padding: 10px 12px; border-bottom: 1px solid var(--border, #eaeaea); text-align: left; }}
  .pipeline-table th {{ font-size: 11px; letter-spacing: 1px; font-weight: 700; color: var(--muted-foreground, #666); text-transform: uppercase; background: var(--card, #f9f8f6); }}
  .pipeline-table .rank-cell {{ width: 40px; font-variant-numeric: tabular-nums; color: var(--muted-foreground, #666); }}
  .pipeline-table .metric-cell {{ font-variant-numeric: tabular-nums; text-align: right; width: 80px; }}
  .pipeline-table .team-cell .submetric {{ display: block; font-size: 11px; color: var(--muted-foreground, #666); margin-top: 2px; }}
  .trend.trend-up {{ color: #0d6831; font-weight: 700; }}
  .trend.trend-down {{ color: #b00020; font-weight: 700; }}
  .pos-chip-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; margin: 16px 0; }}
  .pos-chip {{ display: block; padding: 12px; border: 1px solid var(--border, #d8d8d8); border-radius: 10px; text-decoration: none; color: inherit; transition: transform .15s; }}
  .pos-chip:hover {{ transform: translateY(-2px); }}
  .pos-chip__pos {{ display: block; font-size: 11px; letter-spacing: 2px; color: var(--muted-foreground, #666); font-weight: 700; }}
  .pos-chip__team {{ display: block; font-size: 17px; font-weight: 800; margin: 2px 0; }}
  .pos-chip__n {{ display: block; font-size: 12px; color: var(--muted-foreground, #555); }}
</style>
</head>
<body class="nfl-pipeline-page">
<main class="site-shell" id="main-content">
  <section class="hero">
    <p class="eyebrow">The NFL Pipeline · {year_start}-{year_end}</p>
    <h1>Who actually develops NFL talent?</h1>
    <p class="lede">Twelve drafts. Three thousand picks. Sorted by which programs put the most players in the league — and which ones are still doing it right now versus running on twelve-year reputation.</p>
    <p class="section-note">247 ships recruiting; PFF rates the current season; NFL.com covers the draft. Nobody else connects recruiting → development → draft as one program-level story. This page is the missing connector.</p>
  </section>

  <section class="section">
    <div class="pipeline-summary">
      {summary_cards}
    </div>
  </section>

  <section class="section">
    <h2>The leaderboard</h2>
    <p class="section-note">Sorted by total picks {year_start}-{year_end}. "Recent pace" = picks-per-year over the last three drafts vs the program's twelve-year average. Green = above pace; red = below.</p>
    <div style="overflow-x:auto;">
      <table class="pipeline-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Program</th>
            <th>Picks</th>
            <th>R1</th>
            <th>Day 1+2</th>
            <th>Last 3</th>
            <th>R1 last 3</th>
            <th>Recent pace</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard_rows}
        </tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <h2>Position factories</h2>
    <p class="section-note">For each position, the program with the most NFL picks since {year_start}.</p>
    {position_chips}
  </section>

  <section class="section">
    <p class="muted">Sourced from the per-pick draft archive. Recruiting and on-field performance live on the team pages; the pipeline column closes the loop.</p>
  </section>
</main>
</body>
</html>
"""


def _build_summary_cards(summary: list[dict[str, Any]], year_start: int, year_end: int) -> str:
    if not summary:
        return ""
    top = summary[0]
    total_picks = sum(r["picks_total"] for r in summary)
    total_r1 = sum(r["r1_total"] for r in summary)
    # Most-improved program: largest positive recent-pace delta
    recent_years = 3
    window_years = year_end - year_start + 1
    movers: list[tuple[float, dict[str, Any]]] = []
    for r in summary:
        if r["picks_total"] < 10:  # too small a sample
            continue
        avg = r["picks_total"] / max(window_years, 1)
        rec = r["picks_recent"] / max(recent_years, 1)
        movers.append((rec - avg, r))
    rising = sorted(movers, key=lambda x: -x[0])[:1]
    rising_label = ""
    if rising:
        delta, t = rising[0]
        rising_label = f"{t['team_name']} +{delta:.1f}/yr"

    return f"""
    <div class="pipeline-stat">
      <div class="pipeline-stat__label">TWELVE-YEAR LEADER</div>
      <div class="pipeline-stat__value">{escape(top["team_name"])}</div>
      <div class="pipeline-stat__why">{top["picks_total"]} picks · {top["r1_total"]} first-rounders since {year_start}</div>
    </div>
    <div class="pipeline-stat">
      <div class="pipeline-stat__label">TOTAL PICKS, ERA</div>
      <div class="pipeline-stat__value">{total_picks:,}</div>
      <div class="pipeline-stat__why">{total_r1:,} of them in the first round</div>
    </div>
    <div class="pipeline-stat">
      <div class="pipeline-stat__label">PIPELINE RISING</div>
      <div class="pipeline-stat__value">{escape(rising_label.split(' +')[0]) if rising_label else "—"}</div>
      <div class="pipeline-stat__why">{escape(rising_label.split(' ', 1)[1]) if rising_label else ""} above their twelve-year average over the last three drafts.</div>
    </div>
    """


def render_pipeline_landing_html(
    summary: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    *,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
    top_n: int = 50,
) -> str:
    from cfb_rankings.common.head_chrome import render_head_chrome

    summary_cards = _build_summary_cards(summary, year_start, year_end)
    window_years = year_end - year_start + 1
    leaderboard_rows = _render_leaderboard_rows(summary[:top_n], window_years, 3)
    position_chips = _render_position_chips(positions)
    head_chrome = render_head_chrome(
        page_path="/nfl-pipeline/",
        title=f"The NFL Pipeline — 12 years of the Draft by program · CFB Index",
        description=(
            f"Every college football program ranked by NFL Draft output "
            f"{year_start}-{year_end}. Picks, first-rounders, recent "
            "pipeline pace, and the position each program develops best."
        ),
        og_type="article",
    )
    return _PAGE_TEMPLATE.format(
        year_start=year_start,
        year_end=year_end,
        summary_cards=summary_cards,
        leaderboard_rows=leaderboard_rows,
        position_chips=position_chips,
        head_chrome=head_chrome,
    )


# ---------------------------------------------------------------------------
# Build entry point
# ---------------------------------------------------------------------------


def build_nfl_pipeline(
    db: Database,
    output_dir: str | Path = "output/site",
    *,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
    top_n: int = 50,
) -> list[Path]:
    """Render ``/nfl-pipeline/index.html``.

    Defensive: never raises. Returns ``[]`` on DB error.
    """
    try:
        summary = fetch_pipeline_summary(db, year_start=year_start, year_end=year_end)
        positions = fetch_top_positions(db, year_start=year_start, year_end=year_end)
    except Exception as exc:
        print(f"[nfl-pipeline] fetch failed ({type(exc).__name__}): {exc}")
        return []
    if not summary:
        print("[nfl-pipeline] no draft rows in window; skipping")
        return []

    out_dir = Path(output_dir) / "nfl-pipeline"
    out_dir.mkdir(parents=True, exist_ok=True)
    html = render_pipeline_landing_html(
        summary, positions, year_start=year_start, year_end=year_end, top_n=top_n,
    )
    page_path = out_dir / "index.html"
    page_path.write_text(html, encoding="utf-8")
    return [page_path]
