"""HTML renderer for the CFP-era page (WS-07).

Self-contained: inline CSS so the page renders faithfully from ``file://``
(matching the team_pages convention) for local headless-screenshot review.
Consumes an ``EraSummary`` from :mod:`cfb_rankings.era_pages.data`.

Editorial posture (D-004 offseason): no LLM ledes. Section prose is
structural — it states what the data shows and lets the chart carry the
argument. Sections with no data are omitted entirely.
"""
from __future__ import annotations

import html
from typing import Any

from ..charts import (
    ANNOTATION_CSS,
    CHART_CARD_CSS,
    Annotation,
    render_annotation_overlay,
    render_chart_card,
)
from ..dynasty_heatmap import _percentile_color
from .data import ACTS, DefiningGame, EraSummary

# A single-season percentile drop must be at least this steep to earn a
# "steepest fall" callout — keeps the inflection annotation off flat trajectories.
_FALL_MIN_PCT = 20.0

# --- chart geometry ---------------------------------------------------------
_CHART_W = 880
_CHART_H = 360
_PAD_L = 48
_PAD_R = 24
_PAD_T = 28
_PAD_B = 40

# soft act-band backgrounds (founding cool / transition neutral / expansion warm)
_ACT_BAND = {
    "founding": "#eef2f8",
    "transition": "#f4f1ea",
    "expansion": "#faf0e8",
}
_ACT_RULE = {
    "founding": "#5d7ea8",
    "transition": "#b9b1a0",
    "expansion": "#e07b3a",
}

_DEFINING_RANK = {
    "CFP National Championship": 5,
    "CFP Semifinal": 4,
    "CFP Playoff": 4,
    "CFP Quarterfinal": 3,
    "CFP First Round": 2,
}


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _x_for(year: int, year_start: int, year_end: int) -> float:
    span = max(1, year_end - year_start)
    frac = (year - year_start) / span
    return _PAD_L + frac * (_CHART_W - _PAD_L - _PAD_R)


def _inv_x(x: float, year_start: int, year_end: int) -> float:
    span = max(1, year_end - year_start)
    frac = (x - _PAD_L) / (_CHART_W - _PAD_L - _PAD_R)
    return year_start + frac * span


def _y_for(pct: float) -> float:
    frac = pct / 100.0
    return _PAD_T + (1.0 - frac) * (_CHART_H - _PAD_T - _PAD_B)


def _select_era_annotations(summary: EraSummary) -> list[Annotation]:
    """Pick up to three structural callouts for the trajectory (no LLM, D-004).

    Priority: the championship spine (first national title), the peak season,
    and the steepest single-season fall. Each season is annotated at most once,
    so a flat or title-less program simply gets fewer callouts.
    """
    seasons = [s for s in summary.seasons if s.percentile is not None]
    if len(seasons) < 2:
        return []
    ys, ye = summary.year_start, summary.year_end

    def _xy(s: Any) -> tuple[float, float]:
        return _x_for(s.year, ys, ye), _y_for(s.percentile)

    by_year = {s.year: s for s in seasons}
    anns: list[Annotation] = []
    used: set[int] = set()

    title_years = sorted(g.year for g in summary.defining_games if g.is_title and g.won)
    if title_years and title_years[0] in by_year:
        yr = title_years[0]
        n = len(title_years)
        x, y = _xy(by_year[yr])
        head = "National title" if n == 1 else f"{n} national titles"
        anns.append(Annotation(x, y, [head, f"first in {yr}" if n > 1 else str(yr)],
                               placement="above-right"))
        used.add(yr)

    peak = max(seasons, key=lambda s: s.percentile)
    if peak.year not in used:
        x, y = _xy(peak)
        anns.append(Annotation(x, y, ["Peak of the era",
                                      f"{peak.year} · {peak.wins}–{peak.losses}"]))
        used.add(peak.year)

    worst_delta, worst = 0.0, None
    for a, b in zip(seasons, seasons[1:]):
        delta = a.percentile - b.percentile
        if delta > worst_delta:
            worst_delta, worst = delta, b
    if worst is not None and worst_delta >= _FALL_MIN_PCT and worst.year not in used:
        x, y = _xy(worst)
        anns.append(Annotation(x, y, ["Steepest fall", str(worst.year)],
                               placement="below-right"))
        used.add(worst.year)

    return anns


def _trajectory_svg(summary: EraSummary) -> str:
    ys, ye = summary.year_start, summary.year_end
    parts: list[str] = [
        f'<svg class="era-chart" viewBox="0 0 {_CHART_W} {_CHART_H}" '
        f'role="img" aria-label="Within-season power percentile, {ys} to {ye}" '
        f'preserveAspectRatio="xMidYMid meet">'
    ]

    # act bands + labels
    for ad in ACTS:
        band_start = max(ad.year_start, ys)
        band_end = ye if ad.year_end is None else min(ad.year_end, ye)
        if band_end < ys or band_start > ye:
            continue
        x0 = _x_for(band_start - 0.5, ys, ye)
        x1 = _x_for(band_end + 0.5, ys, ye)
        x0 = max(_PAD_L, x0)
        x1 = min(_CHART_W - _PAD_R, x1)
        w = max(0.0, x1 - x0)
        parts.append(
            f'<rect x="{x0:.1f}" y="{_PAD_T}" width="{w:.1f}" '
            f'height="{_CHART_H - _PAD_T - _PAD_B}" fill="{_ACT_BAND[ad.key]}"/>'
        )
        parts.append(
            f'<text x="{x0 + 6:.1f}" y="{_CHART_H - _PAD_B - 8:.1f}" class="era-band-label" '
            f'fill="{_ACT_RULE[ad.key]}">{_esc(ad.label.upper())}</text>'
        )

    # y gridlines at 0/25/50/75/100
    for g in (0, 25, 50, 75, 100):
        y = _y_for(g)
        parts.append(
            f'<line x1="{_PAD_L}" y1="{y:.1f}" x2="{_CHART_W - _PAD_R}" '
            f'y2="{y:.1f}" class="era-grid"/>'
        )
        parts.append(
            f'<text x="{_PAD_L - 8}" y="{y + 3:.1f}" class="era-axis-y">{g}</text>'
        )

    # the percentile line + dots
    pts = [(s.year, s.percentile) for s in summary.seasons if s.percentile is not None]
    if len(pts) >= 2:
        d = []
        for i, (yr, pct) in enumerate(pts):
            x = _x_for(yr, ys, ye)
            y = _y_for(pct)
            d.append(f'{"M" if i == 0 else "L"}{x:.1f} {y:.1f}')
        parts.append(f'<path d="{" ".join(d)}" class="era-line"/>')

    # Editorial callouts (shared annotation DSL). Years that get a prose
    # callout skip the bare star — the callout already carries the story.
    annotations = _select_era_annotations(summary)
    annotated_years = {int(round(_inv_x(a.x, ys, ye))) for a in annotations}

    # title-win seasons get a star marker so the championship spine is legible
    title_win_years = {g.year for g in summary.defining_games if g.is_title and g.won}
    for s in summary.seasons:
        if s.percentile is None:
            continue
        x = _x_for(s.year, ys, ye)
        y = _y_for(s.percentile)
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" '
            f'fill="{_percentile_color(s.percentile)}" stroke="#fff" stroke-width="1.5"/>'
        )
        # year on x-axis
        parts.append(
            f'<text x="{x:.1f}" y="{_CHART_H - _PAD_B + 16}" '
            f'class="era-axis-x">{s.year % 100:02d}</text>'
        )
        # mark national-title seasons with a compact star above the dot
        if s.year in title_win_years and s.year not in annotated_years:
            parts.append(
                f'<text x="{x:.1f}" y="{y - 10:.1f}" class="era-annot">&#9733;</text>'
            )

    parts.append(
        render_annotation_overlay(
            annotations, width=_CHART_W, height=_CHART_H, accent="#c79200"
        )
    )
    parts.append("</svg>")
    return "".join(parts)


def _stat_sheet_html(summary: EraSummary) -> str:
    ss = summary.stat_sheet
    w, l = ss["record"]
    cells: list[tuple[str, str]] = []
    cells.append(("Record", f"{w}–{l}"))
    if ss.get("win_pct") is not None:
        cells.append(("Win %", f'{ss["win_pct"] * 100:.1f}%'))
    cells.append(("National titles", str(ss["titles"])))
    if ss.get("playoff_appearances"):
        cells.append(("Playoff games", str(ss["playoff_appearances"])))
    if ss.get("best_season") is not None:
        cells.append(("Peak season", f'{ss["best_season"]}'))
    if ss.get("avg_percentile") is not None:
        cells.append(("Avg. percentile", f'{ss["avg_percentile"]:.0f}'))
    if ss.get("nfl_draftees"):
        cells.append(("NFL draftees", str(ss["nfl_draftees"])))

    items = "".join(
        f'<div class="era-stat"><span class="era-stat-v">{_esc(v)}</span>'
        f'<span class="era-stat-k">{_esc(k)}</span></div>'
        for k, v in cells
    )
    return f'<div class="era-statsheet">{items}</div>'


def _acts_html(summary: EraSummary) -> str:
    rows = []
    for act in summary.acts:
        w, l = act.record
        avg = act.avg_percentile
        avg_txt = f"{avg:.0f}" if avg is not None else "—"
        rule = _ACT_RULE.get(act.key, "#999")
        rows.append(
            f'<div class="era-act" style="border-left-color:{rule}">'
            f'<div class="era-act-head"><span class="era-act-name">{_esc(act.label)}</span>'
            f'<span class="era-act-span">{_esc(act.span_label)}</span></div>'
            f'<p class="era-act-blurb">{_esc(act.blurb)}</p>'
            f'<div class="era-act-meta">{w}–{l} &middot; avg percentile {avg_txt}</div>'
            f"</div>"
        )
    return f'<div class="era-acts">{"".join(rows)}</div>'


def _defining_games_html(summary: EraSummary) -> str:
    games = sorted(
        summary.defining_games,
        key=lambda g: (_DEFINING_RANK.get(g.label, 1), g.won, g.year),
        reverse=True,
    )[:5]
    if not games:
        return ""
    rows = []
    for g in games:
        res = "W" if g.won else "L"
        res_cls = "win" if g.won else "loss"
        title_tag = '<span class="era-title-tag">TITLE</span>' if g.is_title else ""
        rows.append(
            f'<li class="era-game">'
            f'<span class="era-game-year">{g.year}</span>'
            f'<span class="era-game-label">{_esc(g.label)}{title_tag}</span>'
            f'<span class="era-game-opp">vs {_esc(g.opponent)}</span>'
            f'<span class="era-game-score {res_cls}">{res} {g.team_points}–{g.opp_points}</span>'
            f"</li>"
        )
    return (
        '<section class="era-section"><h2>Defining games</h2>'
        f'<ul class="era-games">{"".join(rows)}</ul></section>'
    )


def _coaches_html(summary: EraSummary) -> str:
    if not summary.coaches:
        return ""
    ys, ye = summary.year_start, summary.year_end
    span = max(1, ye - ys)
    bars = []
    for cs in summary.coaches:
        start = max(cs.year_start, ys)
        end = min(cs.year_end, ye)
        left = (start - ys) / (span + 1) * 100
        width = (end - start + 1) / (span + 1) * 100
        bars.append(
            f'<div class="era-coach-row">'
            f'<span class="era-coach-name">{_esc(cs.name)}</span>'
            f'<span class="era-coach-track">'
            f'<span class="era-coach-bar" style="left:{left:.1f}%;width:{width:.1f}%"></span></span>'
            f'<span class="era-coach-years">{cs.year_start}–{cs.year_end}</span>'
            f"</div>"
        )
    note = ""
    if summary.coaches_partial_from and summary.coaches_partial_from > ys:
        note = (
            f'<p class="era-note">Coach records begin {summary.coaches_partial_from}.</p>'
        )
    return (
        '<section class="era-section"><h2>Coaches of the era</h2>'
        f'<div class="era-coaches">{"".join(bars)}</div>{note}</section>'
    )


def _roster_html(summary: EraSummary) -> str:
    draft_seasons = [(s.year, s.draftees) for s in summary.seasons if s.draftees]
    total = summary.stat_sheet.get("nfl_draftees", 0)
    if not total:
        return ""
    maxd = max(n for _, n in draft_seasons) if draft_seasons else 1
    bars = []
    for yr, n in draft_seasons:
        h = max(4, n / maxd * 80)
        bars.append(
            f'<div class="era-draft-col" title="{n} drafted from the {yr} roster">'
            f'<span class="era-draft-bar" style="height:{h:.0f}px"></span>'
            f'<span class="era-draft-n">{n}</span>'
            f'<span class="era-draft-y">{yr % 100:02d}</span></div>'
        )
    return (
        '<section class="era-section"><h2>Roster of the era</h2>'
        f'<p class="era-lede">{total} players drafted into the NFL across the CFP era.</p>'
        f'<div class="era-draft">{"".join(bars)}</div></section>'
    )


def _forward_html(summary: EraSummary) -> str:
    f = summary.forward
    nyr = f.get("next_season")
    yr_n = nyr - summary.year_start + 1 if nyr else None
    coach = f.get("current_coach")
    coach_txt = f" under {_esc(coach)}" if coach else ""
    head = f"Entering Year {yr_n}" if yr_n else "Looking ahead"
    return (
        '<section class="era-section era-forward">'
        f"<h2>{head}</h2>"
        f'<p class="era-lede">The {nyr} season opens the next chapter of the expansion era'
        f"{coach_txt}. "
        f'<a href="{_esc(f.get("team_url", "#"))}">See the {summary.year_start}–'
        f'{summary.year_end} program page &rarr;</a></p></section>'
    )


_CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f7f6f3;color:#1b1b1b;
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.5}
.era-wrap{max-width:960px;margin:0 auto;padding:32px 20px 80px}
.era-hero{border-bottom:3px solid #1b1b1b;padding-bottom:18px;margin-bottom:28px}
.era-kicker{font-family:'Bebas Neue',Impact,sans-serif;letter-spacing:.12em;
  font-size:15px;color:#a01818;text-transform:uppercase;margin:0 0 4px}
.era-title{font-family:'Bebas Neue',Impact,sans-serif;font-size:54px;line-height:.95;
  margin:0;text-transform:uppercase;letter-spacing:.01em}
.era-sub{font-family:'Source Serif Pro',Georgia,serif;font-size:18px;color:#555;margin:8px 0 0}
.era-statsheet{display:flex;flex-wrap:wrap;gap:0;border:1px solid #ddd;border-radius:8px;
  overflow:hidden;margin:24px 0 36px;background:#fff}
.era-stat{flex:1 1 110px;padding:16px 14px;text-align:center;border-right:1px solid #eee}
.era-stat:last-child{border-right:none}
.era-stat-v{display:block;font-family:'Bebas Neue',Impact,sans-serif;font-size:30px;
  font-variant-numeric:tabular-nums;color:#1b1b1b}
.era-stat-k{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;
  color:#888;margin-top:2px}
.era-section{margin:40px 0}
.era-section h2{font-family:'Bebas Neue',Impact,sans-serif;font-size:26px;letter-spacing:.04em;
  text-transform:uppercase;border-bottom:2px solid #e3e1db;padding-bottom:6px;margin:0 0 16px}
.era-lede{font-family:'Source Serif Pro',Georgia,serif;font-size:16px;color:#444;margin:0 0 16px}
.era-chart-wrap{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px}
.era-chart{width:100%;height:auto;display:block}
.era-grid{stroke:#ececec;stroke-width:1}
.era-line{fill:none;stroke:#1b1b1b;stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}
.era-axis-y{font-size:11px;fill:#aaa;text-anchor:end;font-variant-numeric:tabular-nums}
.era-axis-x{font-size:11px;fill:#999;text-anchor:middle;font-variant-numeric:tabular-nums}
.era-band-label{font-family:'Bebas Neue',Impact,sans-serif;font-size:13px;letter-spacing:.12em;
  opacity:.55}
.era-annot{font-size:15px;fill:#c79200;text-anchor:middle}
.era-acts{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.era-act{background:#fff;border:1px solid #e3e1db;border-left:4px solid #999;
  border-radius:6px;padding:14px 16px}
.era-act-head{display:flex;justify-content:space-between;align-items:baseline}
.era-act-name{font-family:'Bebas Neue',Impact,sans-serif;font-size:20px;letter-spacing:.03em}
.era-act-span{font-size:12px;color:#888;font-variant-numeric:tabular-nums}
.era-act-blurb{font-family:'Source Serif Pro',Georgia,serif;font-size:14px;color:#555;
  margin:8px 0}
.era-act-meta{font-size:12px;color:#999;font-variant-numeric:tabular-nums}
.era-games{list-style:none;padding:0;margin:0}
.era-game{display:grid;grid-template-columns:48px 1fr auto auto;gap:12px;align-items:center;
  padding:10px 0;border-bottom:1px solid #eee}
.era-game-year{font-family:'Bebas Neue',Impact,sans-serif;font-size:18px;color:#888;
  font-variant-numeric:tabular-nums}
.era-game-label{font-weight:600;font-size:14px}
.era-title-tag{background:#a01818;color:#fff;font-size:9px;letter-spacing:.08em;
  padding:1px 5px;border-radius:3px;margin-left:8px;vertical-align:middle}
.era-game-opp{font-size:13px;color:#666}
.era-game-score{font-variant-numeric:tabular-nums;font-weight:600;font-size:14px}
.era-game-score.win{color:#1a7a3a}
.era-game-score.loss{color:#a01818}
.era-coaches{background:#fff;border:1px solid #e3e1db;border-radius:6px;padding:14px 16px}
.era-coach-row{display:grid;grid-template-columns:140px 1fr 84px;gap:12px;align-items:center;
  padding:6px 0}
.era-coach-name{font-size:13px;font-weight:600}
.era-coach-track{position:relative;height:14px;background:#f0eee8;border-radius:7px}
.era-coach-bar{position:absolute;top:0;height:14px;background:#5d7ea8;border-radius:7px}
.era-coach-years{font-size:12px;color:#888;text-align:right;font-variant-numeric:tabular-nums}
.era-draft{display:flex;align-items:flex-end;gap:8px;height:120px;padding-top:8px}
.era-draft-col{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;
  flex:1}
.era-draft-bar{width:60%;max-width:28px;background:#e07b3a;border-radius:3px 3px 0 0}
.era-draft-n{font-size:11px;color:#666;margin-top:3px;font-variant-numeric:tabular-nums}
.era-draft-y{font-size:10px;color:#aaa;font-variant-numeric:tabular-nums}
.era-forward a{color:#a01818;text-decoration:none;font-weight:600}
.era-note{font-size:12px;color:#999;margin:8px 0 0}
@media(max-width:600px){
  .era-title{font-size:38px}
  .era-game{grid-template-columns:40px 1fr;row-gap:2px}
  .era-coach-row{grid-template-columns:100px 1fr 60px}
}
"""


def render_era_page(summary: EraSummary) -> str:
    conf = f' &middot; {_esc(summary.conference)}' if summary.conference else ""
    body = [
        '<div class="era-wrap">',
        '<header class="era-hero">',
        '<p class="era-kicker">The CFP Era · 2014–present</p>',
        f'<h1 class="era-title">{_esc(summary.program_name)}</h1>',
        f'<p class="era-sub">Twelve seasons in three acts{conf}</p>',
        "</header>",
        _stat_sheet_html(summary),
        '<section class="era-section"><h2>The three-act trajectory</h2>',
        '<div class="era-chart-wrap">',
        render_chart_card(
            _trajectory_svg(summary),
            lede="Within-season power percentile against the FBS cohort, season by season.",
            source="CFB Index · power ratings",
        ),
        "</div>",
        _acts_html(summary),
        "</section>",
        _defining_games_html(summary),
        _coaches_html(summary),
        _roster_html(summary),
        _forward_html(summary),
        "</div>",
    ]
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_esc(summary.program_name)} — The CFP Era</title>"
        f"<style>{_CSS}{ANNOTATION_CSS}{CHART_CARD_CSS}</style></head><body>{''.join(body)}</body></html>"
    )
