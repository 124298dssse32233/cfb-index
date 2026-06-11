"""Aura / Him Watch hub + share cards (Group Chat Noir, perception/violet).

Renders ``/hub/him-watch/<season>/`` as the Aura leaderboard: the most-hyped
QBs and RBs with their perception-vs-production gap, plus "paying aura tax"
(overhyped) and "underrated" cuts. Per-player 1200x675 gap cards (violet AURA
bar over a chalk PRODUCTION bar — the asymmetry IS the card). Aura is
fan-perception data -> violet quarantine. Clones the backometer_render shape.

Data: player_aura_weekly (written by `manage.py compute-aura`).
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.fan_metrics.aura import MENTION_FLOOR
from cfb_rankings.fan_metrics.backometer_render import (
    CHALK,
    GROUND,
    HAIRLINE,
    RECEIPT,
    SURFACE,
    _DISPLAY_STACK,
    _MONO_STACK,
    _SANS_STACK,
    og_card_meta,
)
from cfb_rankings.utils import slugify

AURA = "#9D6BFF"
AURA_TEXT = "#B794FF"

VERDICT_WORD = {
    "aura_tax": "AURA TAX",
    "underrated": "UNDERRATED",
    "matched": "HYPE = TAPE",
    "low_signal": "LOW SIGNAL",
}


def _player_href(player_id: int, full_name: str) -> str:
    return f"/players/{slugify(full_name)}-{player_id}.html"


def latest_aura_season(db: Database) -> int | None:
    row = db.query_one("select max(season_year) as y from player_aura_weekly")
    if not row or row.get("y") is None:
        return None
    return int(row["y"])


def fetch_aura_board(db: Database, season: int) -> dict[str, list[dict[str, Any]]]:
    rows = db.query_all(
        """
        select a.*, p.full_name,
               coalesce(v.team_name, '') as team_name
        from player_aura_weekly a
        join players p on p.player_id = a.player_id
        left join (
            select player_id, team_name,
                   row_number() over (partition by player_id order by plays desc) rn
            from player_value_metrics where season_year = :season
        ) v on v.player_id = a.player_id and v.rn = 1
        where a.season_year = :season and a.is_low_signal = 0
        """,
        {"season": season},
    )
    him_watch = sorted(rows, key=lambda r: (-float(r["aura_score"]), -int(r["mention_count"])))
    overhyped = sorted(
        [r for r in rows if r["verdict"] == "aura_tax"],
        key=lambda r: -float(r["aura_tax"]),
    )
    underrated = sorted(
        [r for r in rows if r["verdict"] == "underrated"],
        key=lambda r: float(r["aura_tax"]),
    )
    return {"him_watch": him_watch, "overhyped": overhyped, "underrated": underrated}


# ---------------------------------------------------------------------------
# Percentile-bar fragment (shared by card + hub)
# ---------------------------------------------------------------------------

def _pctl_bars_svg(
    row: dict[str, Any], *, x0: float, x1: float, y0: float, bar_h: float, gap: float
) -> str:
    track = x1 - x0
    perc = float(row["perception_pctl"])
    prod = float(row["production_pctl"])

    def bar(y: float, label: str, pctl: float, fill: str, value_label: str) -> str:
        w = max(2.0, (pctl / 100.0) * track)
        return (
            f'<text x="{x0:.0f}" y="{y - 8:.0f}" fill="{RECEIPT}" font-size="{max(13, bar_h*0.42):.0f}" '
            f'font-family="{_MONO_STACK}">{escape(label)}</text>'
            f'<rect x="{x0:.0f}" y="{y:.0f}" width="{track:.0f}" height="{bar_h:.0f}" rx="6" fill="{SURFACE}"/>'
            f'<rect x="{x0:.0f}" y="{y:.0f}" width="{w:.1f}" height="{bar_h:.0f}" rx="6" fill="{fill}"/>'
            f'<text x="{x1:.0f}" y="{y + bar_h*0.7:.0f}" fill="{CHALK}" text-anchor="end" '
            f'font-size="{max(15, bar_h*0.5):.0f}" font-weight="700" font-family="{_SANS_STACK}" '
            f'font-variant-numeric="tabular-nums">{escape(value_label)}</text>'
        )

    return (
        bar(y0, "✦ AURA — FAN PERCEPTION", perc, AURA, f"{perc:.0f}th")
        + bar(y0 + bar_h + gap + 22, "PRODUCTION — ON-FIELD", prod, "rgba(237,230,214,0.82)", f"{prod:.0f}th")
    )


# ---------------------------------------------------------------------------
# Share card (1200x675)
# ---------------------------------------------------------------------------

def render_aura_card_svg(row: dict[str, Any], *, season: int) -> str:
    name = str(row["full_name"])
    pos = str(row["position"])
    team = str(row.get("team_name") or "")
    tax = float(row["aura_tax"])
    verdict = VERDICT_WORD.get(str(row["verdict"]), "AURA")
    tax_str = f"{tax:+.0f}"
    bars = _pctl_bars_svg(row, x0=80, x1=1120, y0=330, bar_h=58, gap=40)
    sub = " · ".join(x for x in (pos, team) if x)
    receipt = (
        f"n={int(row['mention_count']):,} mentions · {escape(str(row['cohort_label']))} · "
        f"production={escape(str(row['production_metric']))}"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="Aura: {escape(name)} {escape(verdict)} {tax_str}">
  <rect x="0" y="0" width="1200" height="675" rx="24" fill="{GROUND}"/>
  <rect x="1.5" y="1.5" width="1197" height="672" rx="23" fill="none" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="80" y="78" fill="{RECEIPT}" font-size="22" letter-spacing="4"
        font-family="{_MONO_STACK}">AURA™ · HIM WATCH · {season}</text>
  <text x="80" y="150" fill="{CHALK}" font-size="56" font-weight="800"
        font-family="{_SANS_STACK}">{escape(name)}</text>
  <text x="80" y="196" fill="{RECEIPT}" font-size="24"
        font-family="{_MONO_STACK}">{escape(sub)}</text>
  <text x="80" y="288" fill="{AURA_TEXT}" font-size="76"
        font-family="{_DISPLAY_STACK}" letter-spacing="1">{escape(verdict)}</text>
  <text x="1120" y="180" fill="{AURA_TEXT}" text-anchor="end" font-size="120"
        font-family="{_DISPLAY_STACK}" font-variant-numeric="tabular-nums">{escape(tax_str)}</text>
  <text x="1120" y="226" fill="{RECEIPT}" text-anchor="end" font-size="22"
        font-family="{_MONO_STACK}">AURA TAX</text>
  {bars}
  <line x1="80" y1="608" x2="1120" y2="608" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="80" y="644" fill="{RECEIPT}" font-size="19"
        font-family="{_MONO_STACK}">{escape(receipt)}</text>
  <text x="1120" y="644" fill="{RECEIPT}" text-anchor="end" font-size="19"
        font-family="{_MONO_STACK}">cfbindex.com</text>
</svg>"""


# ---------------------------------------------------------------------------
# Hub
# ---------------------------------------------------------------------------

_HUB_CSS = f"""
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {GROUND}; color: {CHALK}; font-family: {_SANS_STACK};
    font-feature-settings: "tnum"; line-height: 1.5; padding: 40px 16px 80px;
  }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  .eyebrow {{
    font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500; color: {RECEIPT};
    letter-spacing: .12em; text-transform: uppercase; margin-bottom: 10px;
  }}
  h1 {{
    font-family: {_DISPLAY_STACK}; font-weight: 400; text-transform: uppercase;
    font-size: clamp(40px, 7vw, 62px); line-height: 1.05; margin-bottom: 8px;
  }}
  .lede {{ color: {RECEIPT}; font-size: 15px; max-width: 62ch; margin-bottom: 36px; }}
  h2.section {{
    font-family: {_MONO_STACK}; font-size: 13px; font-weight: 500; letter-spacing: .12em;
    text-transform: uppercase; color: {AURA_TEXT}; margin: 36px 0 14px;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 8px; }}
  th {{
    font-family: {_MONO_STACK}; font-size: 10.5px; font-weight: 500; letter-spacing: .1em;
    text-transform: uppercase; color: {RECEIPT}; text-align: left;
    padding: 6px 8px; border-bottom: 1px solid {HAIRLINE};
  }}
  th.num, td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td {{ padding: 9px 8px; border-bottom: 1px solid {HAIRLINE}; }}
  td a {{ color: {CHALK}; text-decoration: none; font-weight: 600; }}
  td a:hover {{ color: {AURA_TEXT}; }}
  .pos {{ color: {RECEIPT}; font-family: {_MONO_STACK}; font-size: 12px; }}
  .tax-pos {{ color: {AURA_TEXT}; font-weight: 700; }}
  .tax-neg {{ color: #8FD14F; font-weight: 700; }}
  .mini {{
    display: inline-block; width: 86px; height: 8px; border-radius: 4px;
    background: {SURFACE}; vertical-align: middle; overflow: hidden;
  }}
  .mini > i {{ display: block; height: 100%; border-radius: 4px; }}
  .foot {{
    margin-top: 44px; padding-top: 16px; border-top: 1px solid {HAIRLINE};
    font-family: {_MONO_STACK}; font-size: 12px; color: {RECEIPT};
  }}
  .foot a {{ color: {RECEIPT}; }}
"""


def _row_html(r: dict[str, Any], rank: int | None = None) -> str:
    href = _player_href(int(r["player_id"]), str(r["full_name"]))
    tax = float(r["aura_tax"])
    tax_cls = "tax-pos" if tax >= 0 else "tax-neg"
    perc = float(r["perception_pctl"])
    prod = float(r["production_pctl"])
    rank_cell = f'<td class="num">{rank}</td>' if rank is not None else ""
    return (
        f"<tr>{rank_cell}"
        f'<td><a href="{escape(href)}">{escape(str(r["full_name"]))}</a> '
        f'<span class="pos">{escape(str(r["position"]))}</span></td>'
        f'<td><span class="mini"><i style="width:{perc:.0f}%;background:{AURA}"></i></span> '
        f'<span class="num">{perc:.0f}</span></td>'
        f'<td><span class="mini"><i style="width:{prod:.0f}%;background:rgba(237,230,214,0.82)"></i></span> '
        f'<span class="num">{prod:.0f}</span></td>'
        f'<td class="num {tax_cls}">{tax:+.0f}</td>'
        f"</tr>"
    )


def render_aura_index_html(season: int, board: dict[str, list[dict[str, Any]]]) -> str:
    def table(rows: list[dict[str, Any]], ranked: bool = False, limit: int = 25) -> str:
        head = (
            "<tr>"
            + ("<th class='num'>#</th>" if ranked else "")
            + "<th>Player</th><th>Aura (perception)</th><th>Production</th><th class='num'>Aura tax</th></tr>"
        )
        body = "".join(
            _row_html(r, rank=(i + 1) if ranked else None)
            for i, r in enumerate(rows[:limit])
        )
        return f"<table>{head}{body}</table>"

    him = table(board["him_watch"], ranked=True, limit=25)
    over = table(board["overhyped"], limit=10) if board["overhyped"] else "<p class='lede'>No qualifying overhyped players this week.</p>"
    under = table(board["underrated"], limit=10) if board["underrated"] else "<p class='lede'>No qualifying underrated players this week.</p>"

    title = f"Him Watch — Aura {season}"
    og_desc = "Aura: which players fans hype vs what the tape says. Perception minus production = aura tax."
    top = board["him_watch"][0] if board["him_watch"] else None
    og_img = (
        f"/hub/him-watch/{season}/{slugify(str(top['full_name']))}-{int(top['player_id'])}.png"
        if top else None
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
<link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{_HUB_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">CFB Index · Fan Intelligence · {season}</div>
  <h1>Him Watch</h1>
  <p class="lede">Aura is how much fans talk about a player; production is what the tape says
  (weighted EPA). We rank both as percentiles within position, and the gap — <b>aura tax</b> —
  is the story. Positive = more hype than tape; negative = quietly producing. QBs and RBs
  only for now (we don't have an honest receiving production metric yet). Players under
  {MENTION_FLOOR} mentions are withheld.</p>

  <h2 class="section">The Board — most aura</h2>
  {him}
  <h2 class="section">Paying aura tax — hype outruns the tape</h2>
  {over}
  <h2 class="section">Underrated — the tape outruns the hype</h2>
  {under}

  <div class="foot">
    Method: perception = season mention volume, percentile-ranked in position cohort ·
    production = wepa (weighted EPA per play), same cohort · cohort = ≥100 snaps ·
    <a href="/methodology/fan-intelligence.html">full methodology →</a>
  </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Build entry point
# ---------------------------------------------------------------------------

def build_aura_section(
    db: Database,
    output_dir: str | Path = "output/site",
    *,
    card_limit: int = 24,
) -> list[Path]:
    try:
        season = latest_aura_season(db)
        if season is None:
            print("[aura] no player_aura_weekly rows; section skipped")
            return []
        board = fetch_aura_board(db, season)
    except Exception as exc:  # noqa: BLE001
        print(f"[aura] fetch failed ({type(exc).__name__}): {exc}")
        return []
    if not board["him_watch"]:
        print("[aura] no players cleared the floor; section skipped")
        return []

    out_dir = Path(output_dir) / "hub" / "him-watch" / str(season)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for row in board["him_watch"][:card_limit]:
        svg = render_aura_card_svg(row, season=season)
        pslug = f"{slugify(str(row['full_name']))}-{int(row['player_id'])}"
        svg_path = out_dir / f"{pslug}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        written.append(svg_path)
    index_path = out_dir / "index.html"
    index_path.write_text(render_aura_index_html(season, board), encoding="utf-8")
    written.append(index_path)

    root = Path(output_dir) / "hub" / "him-watch"
    root.mkdir(parents=True, exist_ok=True)
    redirect = (
        '<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url=/hub/him-watch/{season}/">'
        "<title>Him Watch</title>"
        f'<p>Redirecting to <a href="/hub/him-watch/{season}/">the latest board</a>.</p>'
    )
    (root / "index.html").write_text(redirect, encoding="utf-8")
    written.append(root / "index.html")
    return written


__all__ = ["build_aura_section", "render_aura_card_svg", "render_aura_index_html"]
