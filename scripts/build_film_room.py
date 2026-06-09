"""Film Room — the proprietary model's "receipts."

Two franchises competitors literally cannot copy, both from archived model
history (per-game team_rating_deltas + weekly Heisman latent trajectories):

  1. Best Loss / Worst Win — games where the model disagreed with the
     scoreboard: losses it still rated highly, wins it docked.
  2. Heisman Truth Serum — when the model knew first, and who climbed fastest.

Editorial ranking-card system reused from the Offseason Leaderboards design
pass: #1 spotlight, mini-bars, gold-for-emphasis, tabular numerals, crop-safe.
Retrospective (2024) but framed as evergreen "what our model saw" receipts.

Usage: python scripts/build_film_room.py
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "cfb_rankings.db"
OUT = ROOT / "output" / "site" / "film-room" / "index.html"
GOLD, NAVY, INK, MUTED, CREAM = "#c9a24a", "#1f2c4d", "#1a1a1a", "#7a7a7a", "#f6f1e6"
POS, NEG = "#3f7d54", "#b3402f"
_t = _dt.date.today()
UPDATED = f"{_t.strftime('%B')} {_t.day}, {_t.year}"


def _conn():
    c = sqlite3.connect(str(DB)); c.row_factory = sqlite3.Row; return c


def _season(c):
    r = c.execute("SELECT MAX(season_year) m FROM team_rating_deltas d JOIN games g ON g.game_id=d.game_id").fetchone()
    return r["m"] if r and r["m"] else 2024


def _games_deltas(c, season, wins: bool, order_desc: bool, limit=10):
    """FBS games: wins=False -> losses; order by resume_delta."""
    sign = ">" if wins else "<"
    order = "DESC" if order_desc else "ASC"
    rows = c.execute(
        f"""
        SELECT t.slug, t.canonical_name tm, opp.canonical_name opp,
               d.resume_delta rd, d.power_delta pd,
               CASE WHEN d.team_id=g.home_team_id THEN g.home_points ELSE g.away_points END pf,
               CASE WHEN d.team_id=g.home_team_id THEN g.away_points ELSE g.home_points END pa,
               g.week wk
        FROM team_rating_deltas d
        JOIN games g ON g.game_id=d.game_id
        JOIN teams t ON t.team_id=d.team_id
        JOIN teams opp ON opp.team_id=(CASE WHEN d.team_id=g.home_team_id THEN g.away_team_id ELSE g.home_team_id END)
        WHERE g.season_year=:sy AND g.home_points IS NOT NULL AND t.level_code='FBS'
          AND d.resume_delta IS NOT NULL
          AND (CASE WHEN d.team_id=g.home_team_id THEN g.home_points-g.away_points
                    ELSE g.away_points-g.home_points END) {sign} 0
        ORDER BY d.resume_delta {order} LIMIT :lim
        """, {"sy": season, "lim": limit}).fetchall()
    return rows


def _heisman_first_knew(c, season, limit=10):
    rows = c.execute(
        """
        WITH t5 AS (SELECT player_id, MIN(week) fw FROM heisman_rankings_weekly
                    WHERE season_year=:sy AND rank_overall<=5 GROUP BY player_id)
        SELECT p.full_name nm, tm.canonical_name team, tm.slug, t5.fw,
               (SELECT MAX(latent_score) FROM heisman_rankings_weekly h2
                WHERE h2.player_id=t5.player_id AND h2.season_year=:sy) peak,
               (SELECT MIN(rank_overall) FROM heisman_rankings_weekly h3
                WHERE h3.player_id=t5.player_id AND h3.season_year=:sy) best
        FROM t5 JOIN players p ON p.player_id=t5.player_id
        LEFT JOIN heisman_rankings_weekly hr ON hr.player_id=t5.player_id AND hr.season_year=:sy AND hr.week=t5.fw
        LEFT JOIN teams tm ON tm.team_id=hr.team_id
        ORDER BY t5.fw ASC, peak DESC LIMIT :lim
        """, {"sy": season, "lim": limit}).fetchall()
    return rows


def _heisman_risers(c, season, limit=10):
    rows = c.execute(
        """
        WITH wk AS (SELECT player_id, MIN(week) fw, MAX(week) lw FROM heisman_rankings_weekly
                    WHERE season_year=:sy AND rank_overall IS NOT NULL GROUP BY player_id)
        SELECT p.full_name nm, tm.canonical_name team, tm.slug,
               first_h.rank_overall start_rank, last_h.rank_overall end_rank
        FROM wk
        JOIN players p ON p.player_id=wk.player_id
        JOIN heisman_rankings_weekly first_h ON first_h.player_id=wk.player_id AND first_h.season_year=:sy AND first_h.week=wk.fw
        JOIN heisman_rankings_weekly last_h ON last_h.player_id=wk.player_id AND last_h.season_year=:sy AND last_h.week=wk.lw
        LEFT JOIN teams tm ON tm.team_id=last_h.team_id
        WHERE first_h.rank_overall IS NOT NULL AND last_h.rank_overall IS NOT NULL
          AND last_h.rank_overall <= 50 AND first_h.rank_overall <= 200
          AND first_h.rank_overall - last_h.rank_overall >= 3
        ORDER BY (first_h.rank_overall - last_h.rank_overall) DESC LIMIT :lim
        """, {"sy": season, "lim": limit}).fetchall()
    return rows


# --- rendering helpers (shared design system) ---

def _bar(frac):
    frac = max(0.04, min(1.0, frac))
    return f'<span class="mb"><span class="mb-fill" style="width:{frac*100:.1f}%"></span></span>'


def _dbar(value, max_abs):
    """Zero-centered diverging bar — positive grows right (green), negative left
    (red) from a center axis. The signature visual that separates the Verdict
    Desk from the rank leaderboards."""
    if max_abs <= 0:
        max_abs = 1.0
    frac = max(-1.0, min(1.0, value / max_abs))
    half = abs(frac) * 50.0
    if frac >= 0:
        seg = f'<span class="db-pos" style="left:50%;width:{half:.1f}%"></span>'
    else:
        seg = f'<span class="db-neg" style="right:50%;width:{half:.1f}%"></span>'
    return f'<span class="db"><span class="db-axis"></span>{seg}</span>'


def _tlink(slug, name):
    nm = escape(name or "")
    return f'<a href="/teams/{escape(slug)}.html">{nm}</a>' if slug else nm


def _board(board_id, title, dek, meth, spotlight_html, rows_html):
    return f"""<section class="board" id="{escape(board_id)}">
  <div class="board-head"><h3>{escape(title)}</h3><span class="meth">{escape(meth)}</span></div>
  <p class="dek">{escape(dek)}</p>
  {spotlight_html}
  <ol class="rows">{rows_html}</ol>
</section>"""


def _spot(rk_label, team_html, blurb, val):
    return f"""<div class="spot"><div class="spot-rk">{escape(rk_label)}</div>
      <div class="spot-main"><div class="spot-team">{team_html}</div><div class="spot-blurb">{escape(blurb)}</div></div>
      <div class="spot-val">{escape(val)}</div></div>"""


def build_best_loss(c, season):
    losses = _games_deltas(c, season, wins=False, order_desc=True, limit=10)
    if not losses:
        return ""
    rd_max = max(abs(r["rd"]) for r in losses) or 1
    lead = losses[0]
    spot = _spot("L", f'{_tlink(lead["slug"], lead["tm"])} <span class="conf">vs {escape(lead["opp"])}</span>',
                 f'Lost {lead["pf"]}-{lead["pa"]}, but the model still credited the performance — its best loss of {season}.',
                 f'+{lead["rd"]:.2f}')
    rows = []
    for i, r in enumerate(losses[1:], 2):
        rows.append(f'<li class="row"><span class="rk">{i}</span>'
                    f'<span class="tm">{_tlink(r["slug"], r["tm"])}<span class="conf">L {r["pf"]}-{r["pa"]} vs {escape(r["opp"])}</span></span>'
                    f'<span class="val pos">+{r["rd"]:.2f}</span>{_dbar(r["rd"], rd_max)}'
                    f'<span class="sub">resume still rose</span></li>')
    return _board("best-loss", "Best Losses", "Defeats the model refused to punish — close fights with strong teams that still raised the resume.",
                  f"resume delta in a loss · {season}", spot, "".join(rows))


def build_worst_win(c, season):
    wins = _games_deltas(c, season, wins=True, order_desc=False, limit=10)
    if not wins:
        return ""
    rd_min = min(r["rd"] for r in wins)
    rd_span = max(abs(rd_min), 0.01)
    lead = wins[0]
    spot = _spot("W", f'{_tlink(lead["slug"], lead["tm"])} <span class="conf">vs {escape(lead["opp"])}</span>',
                 f'Won {lead["pf"]}-{lead["pa"]}, but the model docked it — the emptiest win of {season}.',
                 f'{lead["rd"]:.2f}')
    rows = []
    for i, r in enumerate(wins[1:], 2):
        rows.append(f'<li class="row"><span class="rk">{i}</span>'
                    f'<span class="tm">{_tlink(r["slug"], r["tm"])}<span class="conf">W {r["pf"]}-{r["pa"]} vs {escape(r["opp"])}</span></span>'
                    f'<span class="val neg">{r["rd"]:.2f}</span>{_dbar(r["rd"], rd_span)}'
                    f'<span class="sub">resume slipped</span></li>')
    return _board("worst-win", "Worst Wins", "Victories the model saw through — wins that quietly cost a team resume value.",
                  f"resume delta in a win · {season}", spot, "".join(rows))


def build_first_knew(c, season):
    rows_data = _heisman_first_knew(c, season)
    if not rows_data:
        return ""
    lead = rows_data[0]
    spot = _spot(f"W{lead['fw']}", f'{_tlink(lead["slug"], lead["nm"])} <span class="conf">{escape(lead["team"] or "")}</span>',
                 f'The model had {lead["nm"].split()[-1]} in its top five by Week {lead["fw"]} — earlier than the national conversation.',
                 f'pk {lead["peak"]:.1f}')
    peak_max = max(r["peak"] or 0 for r in rows_data) or 1
    rows = []
    for i, r in enumerate(rows_data[1:], 2):
        rows.append(f'<li class="row"><span class="rk">{i}</span>'
                    f'<span class="tm">{_tlink(r["slug"], r["nm"])}<span class="conf">{escape(r["team"] or "")}</span></span>'
                    f'<span class="val">W{r["fw"]}</span>{_bar((r["peak"] or 0)/peak_max)}'
                    f'<span class="sub">peak #{r["best"]}</span></li>')
    return _board("first-knew", "When the Model Knew", "The week each contender first cracked the model's top five — its earliest reads on the race.",
                  f"first top-5 week · {season}", spot, "".join(rows))


def build_risers(c, season):
    rows_data = _heisman_risers(c, season)
    if not rows_data:
        return ""
    lead = rows_data[0]
    climb = lead["start_rank"] - lead["end_rank"]
    spot = _spot("↑", f'{_tlink(lead["slug"], lead["nm"])} <span class="conf">{escape(lead["team"] or "")}</span>',
                 f'Climbed from #{lead["start_rank"]} to #{lead["end_rank"]} — the biggest Heisman-model riser of {season}.',
                 f'+{climb}')
    climb_max = max((r["start_rank"]-r["end_rank"]) for r in rows_data) or 1
    rows = []
    for i, r in enumerate(rows_data[1:], 2):
        cl = r["start_rank"] - r["end_rank"]
        rows.append(f'<li class="row"><span class="rk">{i}</span>'
                    f'<span class="tm">{_tlink(r["slug"], r["nm"])}<span class="conf">{escape(r["team"] or "")}</span></span>'
                    f'<span class="val pos">+{cl}</span>{_bar(cl/climb_max)}'
                    f'<span class="sub">#{r["start_rank"]}→#{r["end_rank"]}</span></li>')
    return _board("risers", "Biggest Risers", "Who the model warmed to most across the season — largest climb in Heisman rank.",
                  f"rank climb, first→last week · {season}", spot, "".join(rows))


def build():
    c = _conn()
    season = _season(c)
    bl, ww = build_best_loss(c, season), build_worst_win(c, season)
    fk, ri = build_first_knew(c, season), build_risers(c, season)
    page = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Film Room · Model Receipts · CFB Index</title>
<meta name="description" content="The CFB Index model's receipts: best losses and worst wins of {season}, plus when the Heisman model knew first. Archived per-game and weekly model history no one else publishes.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&family=Source+Serif+4:ital@0;1&display=swap" rel="stylesheet">
<style>
  :root{{--gold:{GOLD};--navy:{NAVY};--ink:{INK};--muted:{MUTED};--cream:{CREAM};--pos:{POS};--neg:{NEG};}}
  *{{box-sizing:border-box;}} body{{margin:0;background:var(--cream);color:var(--ink);font-family:'Source Serif 4',Georgia,serif;}}
  .nav-strip{{padding:11px 20px;border-bottom:1px solid rgba(0,0,0,.1);font:600 13px Inter,sans-serif;}}
  .nav-strip a{{color:var(--navy);text-decoration:none;margin-right:16px;}}
  .wrap{{max-width:1120px;margin:0 auto;padding:22px 20px 72px;}}
  .hero{{border-bottom:2px solid var(--gold);padding-bottom:16px;margin-bottom:24px;}}
  h1{{font-family:'Bebas Neue',Impact,sans-serif;font-size:clamp(34px,6vw,56px);letter-spacing:.03em;margin:.1em 0;line-height:1;}}
  .thesis{{max-width:64ch;margin:6px 0 10px;font-size:16px;}}
  .stamp{{font:600 11px Inter,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);}}
  .jumps{{margin-top:12px;}} .jumps a{{font:700 12px Inter,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--navy);text-decoration:none;margin-right:14px;border-bottom:2px solid var(--gold);}}
  h2.sec{{font-family:'Bebas Neue',Impact,sans-serif;font-size:26px;letter-spacing:.04em;margin:30px 0 6px;border-left:4px solid var(--gold);padding-left:10px;}}
  .sec-note{{color:var(--muted);font-style:italic;font-size:13px;margin:0 0 14px;padding-left:14px;}}
  .grid{{display:grid;grid-template-columns:1fr;gap:18px;}} @media(min-width:840px){{.grid{{grid-template-columns:1fr 1fr;}}}}
  .board{{background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:10px;padding:16px 18px;}}
  .board-head{{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;}}
  .board h3{{font-family:'Bebas Neue',Impact,sans-serif;font-size:22px;letter-spacing:.03em;margin:0;}}
  .meth{{font:600 10px Inter,sans-serif;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);}}
  .dek{{color:var(--muted);font-style:italic;font-size:13px;margin:2px 0 12px;}}
  .spot{{display:grid;grid-template-columns:46px 1fr auto;align-items:center;gap:10px;background:linear-gradient(90deg,color-mix(in srgb,var(--gold) 14%,#fff),#fff);border:1px solid color-mix(in srgb,var(--gold) 40%,transparent);border-radius:8px;padding:10px 12px;margin-bottom:10px;}}
  .spot-rk{{font-family:'Bebas Neue',Impact,sans-serif;font-size:34px;line-height:1;color:var(--gold);text-align:center;}}
  .spot-team{{font:700 16px Inter,sans-serif;}} .spot-team a{{color:var(--navy);text-decoration:none;}}
  .spot-blurb{{font-size:12.5px;opacity:.85;margin-top:2px;line-height:1.35;}}
  .spot-val{{font:700 22px Inter,sans-serif;font-variant-numeric:tabular-nums lining-nums;}}
  .conf{{font:600 10px Inter,sans-serif;color:var(--muted);margin-left:7px;letter-spacing:.03em;}}
  ol.rows{{list-style:none;margin:0;padding:0;}}
  .row{{display:grid;grid-template-columns:24px minmax(0,1fr) 58px 72px auto;align-items:center;gap:8px;padding:5px 2px;border-bottom:1px solid rgba(0,0,0,.05);}}
  .row .rk{{font:600 13px Inter,sans-serif;color:var(--muted);font-variant-numeric:tabular-nums;}}
  .row .tm{{font:600 13.5px Inter,sans-serif;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}} .row .tm a{{color:var(--navy);text-decoration:none;}}
  .row .val{{text-align:right;font:700 14px Inter,sans-serif;font-variant-numeric:tabular-nums lining-nums;}}
  .val.pos{{color:var(--pos);}} .val.neg{{color:var(--neg);}}
  .mb{{display:inline-block;height:7px;background:rgba(0,0,0,.07);border-radius:4px;overflow:hidden;}}
  .mb-fill{{display:block;height:100%;background:var(--navy);border-radius:4px;}}
  .db{{position:relative;display:inline-block;height:10px;width:100%;}}
  .db-axis{{position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(0,0,0,.25);}}
  .db-pos{{position:absolute;top:1px;bottom:1px;background:var(--pos);border-radius:0 3px 3px 0;}}
  .db-neg{{position:absolute;top:1px;bottom:1px;background:var(--neg);border-radius:3px 0 0 3px;}}
  .row .sub{{font:400 10px Inter,sans-serif;color:var(--muted);text-align:right;white-space:nowrap;}}
  @media(max-width:520px){{.row{{grid-template-columns:20px minmax(0,1fr) auto;row-gap:2px;}}.row .mb,.row .sub{{grid-column:2/-1;justify-self:start;}}.row .mb{{width:55%;}}}}
</style></head><body>
<div class="nav-strip"><a href="/">← CFB Index</a><a href="/offseason/index.html">Offseason</a><a href="/rankings/index.html">Rankings</a><a href="/chronicle/">The Chronicle</a><strong>Film Room</strong></div>
<div class="wrap">
  <header class="hero">
    <div class="stamp">Model receipts · {season} season</div>
    <h1>Film Room</h1>
    <p class="thesis">What our model saw that the scoreboard and the polls didn't. Archived per-game and week-by-week model history — the kind of receipts no other site keeps.</p>
    <div class="jumps"><a href="#scoreboard-lies">Scoreboard Lies</a><a href="#truth-serum">Heisman Truth Serum</a></div>
  </header>

  <h2 class="sec" id="scoreboard-lies">Scoreboard Lies</h2>
  <p class="sec-note">The model grades the performance, not the final score. These are the {season} games where the two disagreed most.</p>
  <div class="grid">{bl}{ww}</div>

  <h2 class="sec" id="truth-serum">Heisman Truth Serum</h2>
  <p class="sec-note">Week-by-week, the Heisman model leaves a paper trail. Here's when it knew — and who it warmed to fastest.</p>
  <div class="grid">{fk}{ri}</div>
</div></body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"[film-room] wrote {OUT} · season {season} · 4 boards")


if __name__ == "__main__":
    build()
