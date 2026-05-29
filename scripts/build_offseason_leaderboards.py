"""National + Conference Offseason Leaderboards Hub — horizontal-discovery surface.

Answers "who's #1 at X nationally / in my conference, and where does my team
rank?" — the biggest gap from the 2026-05-25 ideation probe. Built to the
Octopus UI/UX design pass: an editorial ranking-card system (not a flat grid)
— flagship argument board + 2x2 grid, a #1 leader spotlight per board, mini-
bars normalized within each board, gold reserved for emphasis, and a
conference-grouped section with a chip jump-rail. Powered entirely by data
already in the DB (2026 portal+draft, 2025 returning production+talent).

Usage: python scripts/build_offseason_leaderboards.py
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "cfb_rankings.db"
OUT = ROOT / "output" / "site" / "offseason" / "index.html"

GOLD, NAVY, INK, MUTED, CREAM = "#c9a24a", "#1f2c4d", "#1a1a1a", "#7a7a7a", "#f6f1e6"
POS, NEG = "#3f7d54", "#b3402f"  # movement only, not brand
_today = _dt.date.today()
UPDATED = f"{_today.strftime('%B')} {_today.day}, {_today.year}"


@dataclass
class Row:
    slug: str | None
    name: str
    abbr: str
    value_fmt: str
    raw: float
    sub: str = ""


@dataclass
class Board:
    key: str
    title: str
    dek: str
    methodology: str
    rows: list[Row] = field(default_factory=list)
    higher_is_better: bool = True
    leader_blurb: str = ""


def _conn():
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    return c


def _latest(c, table, col="season_year"):
    r = c.execute(f"SELECT MAX({col}) m FROM {table}").fetchone()
    return r["m"] if r else None


# --- Portal flow Sankey (WS-08): national level-migration of the cycle -------

_ORIGIN_BUCKETS = ("FBS", "FCS", "Lower")
_DEST_BUCKETS = ("FBS", "FCS", "Lower", "Uncommitted")


def _origin_bucket(level: str | None) -> int:
    if level == "FBS":
        return 0
    if level == "FCS":
        return 1
    return 2  # DII / DIII / JUCO / NAIA / unknown


def _dest_bucket(level: str | None) -> int:
    if level == "FBS":
        return 0
    if level == "FCS":
        return 1
    if level in ("DII", "DIII"):
        return 2
    return 3  # to_level NULL -> still uncommitted / not yet landed


def _portal_flow_section(c, season) -> str:
    """National transfer-portal flow Sankey: origin level -> destination level
    for the given cycle. Powered by the existing flow viz template (WS-08)."""
    from cfb_rankings.editions.viz_templates import render as render_viz

    raw = c.execute(
        """
        SELECT from_level_code AS f, to_level_code AS t, COUNT(*) AS n
        FROM transfer_entries WHERE season_year = :sy
        GROUP BY from_level_code, to_level_code
        """,
        {"sy": season},
    ).fetchall()
    if not raw:
        return ""

    link_counts: dict[tuple[int, int], int] = {}
    left_totals = [0] * len(_ORIGIN_BUCKETS)
    right_totals = [0] * len(_DEST_BUCKETS)
    for row in raw:
        i = _origin_bucket(row["f"])
        j = _dest_bucket(row["t"])
        n = int(row["n"])
        link_counts[(i, j)] = link_counts.get((i, j), 0) + n
        left_totals[i] += n
        right_totals[j] += n

    left_nodes = [
        {"label": lbl, "value": left_totals[i], "color": NAVY}
        for i, lbl in enumerate(_ORIGIN_BUCKETS) if left_totals[i]
    ]
    right_nodes = [
        {"label": lbl, "value": right_totals[j], "color": (MUTED if lbl == "Uncommitted" else GOLD)}
        for j, lbl in enumerate(_DEST_BUCKETS) if right_totals[j]
    ]
    # Re-index after dropping empty buckets.
    left_remap = {orig: new for new, (orig, _) in enumerate(
        [(i, t) for i, t in enumerate(left_totals) if t])}
    right_remap = {orig: new for new, (orig, _) in enumerate(
        [(j, t) for j, t in enumerate(right_totals) if t])}
    links = [
        {"from": left_remap[i], "to": right_remap[j], "value": n}
        for (i, j), n in sorted(link_counts.items(), key=lambda kv: -kv[1])
        if i in left_remap and j in right_remap
    ]

    total = sum(int(r["n"]) for r in raw)
    fcs_up = link_counts.get((1, 0), 0)
    uncommitted = right_totals[3]
    svg = render_viz("flow", {
        "title": f"Where the {season} portal moved",
        "left_label": "LEFT THIS LEVEL",
        "right_label": "LANDED AT",
        "left_nodes": left_nodes,
        "right_nodes": right_nodes,
        "links": links,
        "caption": (f"{total:,} tracked entries — {fcs_up} climbed FCS→FBS, "
                    f"{uncommitted:,} still uncommitted."),
        "source": "CFB Index · transfer_entries",
    })
    return f"""
  <h2 class="sec" id="flow">Talent Migration</h2>
  <div class="board" style="overflow-x:auto;">
    <div class="dek">The full {season} portal cycle as a flow — which level each transfer left, and where they landed. Band width is player count.</div>
    <div style="min-width:680px;">{svg}</div>
  </div>"""


# --- Portal program network (WS-08, chart type #9): who feeds whom ----------
_NET_NODES = 16     # busiest programs to put on the ring
_NET_EDGE_MIN = 2   # a "pipeline" is ≥2 players moving the same direction


def _transfer_network_section(c, season) -> str:
    """Directed circular-chord network of the busiest portal pipelines this
    cycle — FBS→FBS player movement among the ``_NET_NODES`` highest-volume
    programs (edges thinned to real pipelines of ≥``_NET_EDGE_MIN`` players).
    Powered by the centralised charts.render_network (WS-08 chart type #9)."""
    from cfb_rankings.charts import NetworkEdge, NetworkNode, render_network

    raw = c.execute(
        """
        SELECT te.from_team_id AS f, te.to_team_id AS t,
               COALESCE(NULLIF(tf.short_name, ''), tf.canonical_name) AS fn,
               COALESCE(NULLIF(tt.short_name, ''), tt.canonical_name) AS tn,
               COUNT(*) AS n
        FROM transfer_entries te
        JOIN teams tf ON tf.team_id = te.from_team_id AND tf.level_code = 'FBS'
        JOIN teams tt ON tt.team_id = te.to_team_id AND tt.level_code = 'FBS'
        WHERE te.season_year = :sy
          AND te.from_team_id IS NOT NULL AND te.to_team_id IS NOT NULL
          AND te.from_team_id <> te.to_team_id
        GROUP BY te.from_team_id, te.to_team_id
        """,
        {"sy": season},
    ).fetchall()
    if not raw:
        return ""

    name: dict[int, str] = {}
    volume: dict[int, int] = {}
    for r in raw:
        name[r["f"]] = r["fn"]
        name[r["t"]] = r["tn"]
        volume[r["f"]] = volume.get(r["f"], 0) + r["n"]
        volume[r["t"]] = volume.get(r["t"], 0) + r["n"]

    top = [tid for tid, _ in sorted(volume.items(), key=lambda kv: -kv[1])[:_NET_NODES]]
    keep = set(top)
    edges = [
        NetworkEdge(source=str(r["f"]), target=str(r["t"]), weight=float(r["n"]))
        for r in raw
        if r["f"] in keep and r["t"] in keep and r["n"] >= _NET_EDGE_MIN
    ]
    if not edges:
        return ""

    # Only ring programs that actually carry a kept pipeline, so the chart never
    # shows an isolated dot. Order by volume desc for a deterministic layout.
    linked = {e.source for e in edges} | {e.target for e in edges}
    nodes = [
        NetworkNode(id=str(tid), label=name[tid], weight=float(volume[tid]))
        for tid in top if str(tid) in linked
    ]
    if len(nodes) < 2:
        return ""

    svg = render_network(
        nodes, edges,
        caption=(f"Each arc is a portal pipeline of {_NET_EDGE_MIN}+ players "
                 f"between two of the {len(nodes)} busiest FBS programs this "
                 f"cycle; the arrow points to where they landed. Dot size = "
                 f"total portal traffic."),
        accent=NAVY,
        label_color=INK,
    )
    if not svg:
        return ""
    return f"""
  <h2 class="sec" id="network">Portal Pipelines</h2>
  <div class="board">
    <div class="dek">The {season} carousel as a web — which programs feed each other. The thickest arcs are the established pipelines.</div>
    {svg}
  </div>"""


def _pct(v) -> float:
    # returning_production columns are fractions (0..~1.05); a few exceed 1.0
    # slightly. Treat anything <= 1.5 as a fraction to scale to a percent.
    x = float(v or 0)
    pct = x * 100 if x <= 1.5 else x
    return min(100.0, pct)  # cap: returning PPA can exceed 100% (artifact); reads odd to fans


# ---------------------------------------------------------------------------
# Board data
# ---------------------------------------------------------------------------

def _portal_rows(c, season, conference_id=None, limit=25) -> list[Row]:
    conf = "AND t.current_conference_id = :cid" if conference_id else ""
    params = {"sy": season}
    if conference_id:
        params["cid"] = conference_id
    rows = c.execute(
        f"""
        WITH inc AS (SELECT to_team_id tid, SUM(COALESCE(transfer_points,0)) pts, COUNT(*) n
                     FROM transfer_entries WHERE season_year=:sy AND to_team_id IS NOT NULL GROUP BY to_team_id),
             outg AS (SELECT from_team_id tid, SUM(COALESCE(transfer_points,0)) pts, COUNT(*) n
                      FROM transfer_entries WHERE season_year=:sy AND from_team_id IS NOT NULL GROUP BY from_team_id)
        SELECT t.slug, t.canonical_name nm, cf.conference_short_name abbr,
               COALESCE(inc.pts,0)-COALESCE(outg.pts,0) net, COALESCE(inc.n,0) in_n, COALESCE(outg.n,0) out_n
        FROM teams t
        LEFT JOIN inc ON inc.tid=t.team_id
        LEFT JOIN outg ON outg.tid=t.team_id
        LEFT JOIN conferences cf ON cf.conference_id=t.current_conference_id
        WHERE t.level_code='FBS' AND t.is_active=1 {conf}
          AND (inc.tid IS NOT NULL OR outg.tid IS NOT NULL)
        ORDER BY net DESC LIMIT :lim
        """, {**params, "lim": limit}).fetchall()
    return [Row(r["slug"], r["nm"], r["abbr"] or "", f"{r['net']:+.0f}", float(r["net"]),
                f"{r['in_n']} in · {r['out_n']} out") for r in rows]


def _returning_rows(c, season, conference_id=None, limit=25, ascending=False) -> list[Row]:
    conf = "AND t.current_conference_id = :cid" if conference_id else ""
    order = "ASC" if ascending else "DESC"
    params = {"sy": season}
    if conference_id:
        params["cid"] = conference_id
    rows = c.execute(
        f"""
        SELECT t.slug, t.canonical_name nm, cf.conference_short_name abbr,
               rp.returning_total v, rp.returning_qb qb
        FROM returning_production rp JOIN teams t ON t.team_id=rp.team_id
        LEFT JOIN conferences cf ON cf.conference_id=t.current_conference_id
        WHERE rp.season_year=:sy AND t.level_code='FBS' AND t.is_active=1 {conf}
        ORDER BY rp.returning_total {order} LIMIT :lim
        """, {**params, "lim": limit}).fetchall()
    return [Row(r["slug"], r["nm"], r["abbr"] or "", f"{_pct(r['v']):.0f}%", _pct(r["v"]),
                f"QB {_pct(r['qb']):.0f}% back") for r in rows]


def _draft_rows(c, draft_year, limit=25) -> list[Row]:
    rows = c.execute(
        """
        SELECT t.slug, t.canonical_name nm, cf.conference_short_name abbr,
               COUNT(*) picks, SUM(MAX(1, 8-COALESCE(d.round,7))) cap,
               SUM(CASE WHEN d.overall<=32 THEN 1 ELSE 0 END) r1
        FROM player_nfl_draft d JOIN teams t ON t.team_id=d.college_team_id
        LEFT JOIN conferences cf ON cf.conference_id=t.current_conference_id
        WHERE d.draft_year=:dy AND t.level_code='FBS'
        GROUP BY d.college_team_id ORDER BY cap DESC LIMIT :lim
        """, {"dy": draft_year, "lim": limit}).fetchall()
    return [Row(r["slug"], r["nm"], r["abbr"] or "", f"{r['picks']}", float(r["picks"]),
                (f"{r['r1']} first-round" if r["r1"] else "drafted")) for r in rows]


def _talent_rows(c, season, conference_id=None, limit=25) -> list[Row]:
    conf = "AND t.current_conference_id = :cid" if conference_id else ""
    params = {"sy": season}
    if conference_id:
        params["cid"] = conference_id
    rows = c.execute(
        f"""
        SELECT t.slug, t.canonical_name nm, cf.conference_short_name abbr, ts.talent_score v
        FROM team_talent_snapshots ts JOIN teams t ON t.team_id=ts.team_id
        LEFT JOIN conferences cf ON cf.conference_id=t.current_conference_id
        WHERE ts.season_year=:sy AND t.level_code='FBS' AND t.is_active=1 {conf}
        ORDER BY ts.talent_score DESC LIMIT :lim
        """, {**params, "lim": limit}).fetchall()
    return [Row(r["slug"], r["nm"], r["abbr"] or "", f"{float(r['v'] or 0):.0f}", float(r["v"] or 0),
                "talent composite") for r in rows]


def national_boards(c) -> list[Board]:
    psy = _latest(c, "transfer_entries")
    rsy = _latest(c, "returning_production")
    tsy = _latest(c, "team_talent_snapshots")
    dy = _latest(c, "player_nfl_draft", "draft_year")
    boards = [
        Board("portal", f"Portal Kings", "Who won the transfer portal — net talent added, not just bodies.",
              f"net transfer points, {psy} cycle", _portal_rows(c, psy), True),
        Board("returning", "Most Returning Production", "The rosters bringing back the most from last season.",
              f"returning production %, {rsy}", _returning_rows(c, rsy), True),
        Board("draft", "NFL Draft Factories", "Most talent sent to the NFL — and now to replace.",
              f"{dy} draft picks (round-weighted)", _draft_rows(c, dy), True),
        Board("talent", "Roster Talent", "Composite recruiting talent on hand entering 2026.",
              f"talent composite, {tsy}", _talent_rows(c, tsy), True),
        Board("reload", "Biggest Reloads", "Fewest returners — the rebuild jobs of the offseason.",
              f"returning production %, {rsy}", _returning_rows(c, rsy, ascending=True), False),
    ]
    for b in boards:
        if b.rows:
            b.leader_blurb = _leader_blurb(b)
    return boards


def _leader_blurb(b: Board) -> str:
    r0 = b.rows[0]
    rest = b.rows[1:]
    med = sorted(x.raw for x in b.rows)[len(b.rows)//2] if b.rows else 0
    gap = abs(r0.raw - (rest[0].raw if rest else r0.raw))
    if b.key == "portal":
        return f"{r0.name} added the most net portal talent in the country — {r0.value_fmt} points clear of the field."
    if b.key == "returning":
        return f"{r0.name} returns {r0.value_fmt} of last season's production, among the most continuous rosters in FBS."
    if b.key == "draft":
        return f"{r0.name} sent {r0.value_fmt} players to the NFL — the most draft talent any program has to replace."
    if b.key == "talent":
        return f"{r0.name} carries the top recruiting-talent composite on hand entering 2026."
    if b.key == "reload":
        return f"{r0.name} brings back the least production in FBS — the offseason's biggest rebuild."
    return f"{r0.name} leads the board."


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _bar(raw: float, lo: float, hi: float) -> str:
    if hi == lo:
        frac = 0.5
    else:
        frac = (raw - lo) / (hi - lo)
    frac = max(0.04, min(1.0, frac))
    return (f'<span class="mb"><span class="mb-fill" style="width:{frac*100:.1f}%"></span></span>')


def _team_link(r: Row) -> str:
    nm = escape(r.name)
    return f'<a href="/teams/{escape(r.slug)}.html">{nm}</a>' if r.slug else nm


def _render_board(b: Board, compact: bool = False, max_rows: int = 10, flagship: bool = False) -> str:
    if not b.rows:
        return ""
    raws = [r.raw for r in b.rows]
    lo, hi = min(raws), max(raws)
    # bars always read "longer = leader of THIS board"
    def barval(r): return r.raw if b.higher_is_better else (hi - r.raw + lo)
    blo = min(barval(r) for r in b.rows); bhi = max(barval(r) for r in b.rows)

    lead = b.rows[0]
    spotlight = f"""
    <div class="spot">
      <div class="spot-rk">1</div>
      <div class="spot-main">
        <div class="spot-team">{_team_link(lead)}<span class="conf">{escape(lead.abbr)}</span></div>
        <div class="spot-blurb">{escape(b.leader_blurb)}</div>
      </div>
      <div class="spot-val">{escape(lead.value_fmt)}</div>
    </div>"""

    body_rows = []
    rows = b.rows[1:max_rows]
    for i, r in enumerate(rows, start=2):
        body_rows.append(
            f'<li class="row"><span class="rk">{i}</span>'
            f'<span class="tm">{_team_link(r)}<span class="conf">{escape(r.abbr)}</span></span>'
            f'<span class="val">{escape(r.value_fmt)}</span>'
            f'{_bar(barval(r), blo, bhi)}'
            f'<span class="sub">{escape(r.sub)}</span></li>'
        )
    cls = "board compact" if compact else ("board flagship" if flagship else "board")
    return f"""<section class="{cls}" id="board-{escape(b.key)}">
  <div class="board-head"><h3>{escape(b.title)}</h3><span class="meth">{escape(b.methodology)}</span></div>
  <p class="dek">{escape(b.dek)}</p>
  {spotlight}
  <ol class="rows">{''.join(body_rows)}</ol>
</section>"""


def conference_sections(c) -> str:
    psy = _latest(c, "transfer_entries")
    rsy = _latest(c, "returning_production")
    confs = c.execute(
        """
        SELECT cf.conference_id cid, cf.conference_name nm, cf.conference_short_name abbr, COUNT(*) n
        FROM teams t JOIN conferences cf ON cf.conference_id=t.current_conference_id
        WHERE t.level_code='FBS' AND t.is_active=1 AND cf.conference_name NOT IN ('FBS','FBS Independents')
        GROUP BY cf.conference_id HAVING n>=8
        ORDER BY n DESC, cf.conference_name
        """).fetchall()
    chips = []
    sections = []
    for cf in confs:
        cid, nm, abbr = cf["cid"], cf["nm"], (cf["abbr"] or cf["nm"])
        anchor = f"conf-{cid}"
        chips.append(f'<a class="chip" href="#{anchor}">{escape(abbr)}</a>')
        portal = Board("portal", f"{abbr} Portal Kings", f"Top net-talent portal hauls in the {nm}.",
                       f"net transfer points, {psy}", _portal_rows(c, psy, conference_id=cid, limit=5), True)
        ret = Board("returning", f"{abbr} Returning Most", f"Most production back in the {nm}.",
                    f"returning %, {rsy}", _returning_rows(c, rsy, conference_id=cid, limit=5), True)
        for b in (portal, ret):
            if b.rows:
                b.leader_blurb = _leader_blurb(b)
        mini = "".join(_render_board(b, compact=True, max_rows=5) for b in (portal, ret) if b.rows)
        if mini:
            sections.append(f'<div class="conf-sec" id="{anchor}"><h3 class="conf-title">{escape(nm)}</h3><div class="conf-grid">{mini}</div></div>')
    chip_rail = f'<nav class="chip-rail" aria-label="Jump to conference">{"".join(chips)}</nav>'
    return chip_rail + "\n".join(sections)


def build() -> None:
    c = _conn()
    nat = national_boards(c)
    flagship = next((b for b in nat if b.key == "portal"), nat[0])
    rest = [b for b in nat if b is not flagship]
    flagship_html = _render_board(flagship, compact=False, max_rows=12, flagship=True)
    grid_html = "".join(_render_board(b, compact=True, max_rows=8) for b in rest)
    latest_cycle = _latest(c, "transfer_entries")
    flow_html = _portal_flow_section(c, latest_cycle)
    network_html = _transfer_network_section(c, latest_cycle)
    conf_html = conference_sections(c)

    from cfb_rankings.charts import NETWORK_CSS

    page = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offseason Leaderboards · 2026 · CFB Index</title>
<meta name="description" content="National and conference college football offseason leaderboards: portal winners, returning production, NFL draft factories, roster talent, biggest reloads — every FBS team ranked heading into 2026.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&family=Source+Serif+4:ital@0;1&display=swap" rel="stylesheet">
<style>
  :root{{--gold:{GOLD};--navy:{NAVY};--ink:{INK};--muted:{MUTED};--cream:{CREAM};--pos:{POS};--neg:{NEG};}}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--cream);color:var(--ink);font-family:'Source Serif 4',Georgia,serif;}}
  .nav-strip{{padding:11px 20px;border-bottom:1px solid rgba(0,0,0,.1);font:600 13px Inter,sans-serif;}}
  .nav-strip a{{color:var(--navy);text-decoration:none;margin-right:16px;}}
  .wrap{{max-width:1120px;margin:0 auto;padding:22px 20px 72px;}}
  .hero{{border-bottom:2px solid var(--gold);padding-bottom:16px;margin-bottom:24px;}}
  h1{{font-family:'Bebas Neue',Impact,sans-serif;font-size:clamp(34px,6vw,56px);letter-spacing:.03em;margin:.1em 0;line-height:1;}}
  .thesis{{color:var(--ink);max-width:62ch;margin:6px 0 10px;font-size:16px;}}
  .stamp{{font:600 11px Inter,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);}}
  .jumps{{margin-top:12px;}} .jumps a{{font:700 12px Inter,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--navy);text-decoration:none;margin-right:14px;border-bottom:2px solid var(--gold);}}
  h2.sec{{font-family:'Bebas Neue',Impact,sans-serif;font-size:26px;letter-spacing:.04em;margin:30px 0 14px;border-left:4px solid var(--gold);padding-left:10px;}}
  .grid{{display:grid;grid-template-columns:1fr;gap:18px;}}
  @media(min-width:840px){{.grid{{grid-template-columns:1fr 1fr;}}}}
  .board{{background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:10px;padding:16px 18px;}}
  .board.flagship{{border-left:4px solid var(--gold);}}
  .board-head{{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;}}
  .board h3{{font-family:'Bebas Neue',Impact,sans-serif;font-size:22px;letter-spacing:.03em;margin:0;}}
  .meth{{font:600 10px Inter,sans-serif;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);}}
  .dek{{color:var(--muted);font-style:italic;font-size:13px;margin:2px 0 12px;}}
  .spot{{display:grid;grid-template-columns:46px 1fr auto;align-items:center;gap:10px;background:linear-gradient(90deg,color-mix(in srgb,var(--gold) 14%,#fff),#fff);border:1px solid color-mix(in srgb,var(--gold) 40%,transparent);border-radius:8px;padding:10px 12px;margin-bottom:10px;}}
  .spot-rk{{font-family:'Bebas Neue',Impact,sans-serif;font-size:40px;line-height:1;color:var(--gold);text-align:center;}}
  .spot-team{{font:700 17px Inter,sans-serif;}} .spot-team a{{color:var(--navy);text-decoration:none;}}
  .spot-blurb{{font-family:'Source Serif 4',Georgia,serif;font-size:12.5px;color:var(--ink);opacity:.85;margin-top:2px;line-height:1.35;}}
  .spot-val{{font:700 26px Inter,sans-serif;font-variant-numeric:tabular-nums lining-nums;color:var(--ink);}}
  .conf{{font:600 10px Inter,sans-serif;color:var(--muted);margin-left:7px;letter-spacing:.04em;}}
  ol.rows{{list-style:none;margin:0;padding:0;}}
  .row{{display:grid;grid-template-columns:26px minmax(0,1fr) 64px 72px auto;align-items:center;gap:8px;padding:5px 2px;border-bottom:1px solid rgba(0,0,0,.05);}}
  .row .rk{{font:600 13px Inter,sans-serif;color:var(--muted);font-variant-numeric:tabular-nums;}}
  .row .tm{{font:600 14px Inter,sans-serif;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}} .row .tm a{{color:var(--navy);text-decoration:none;}}
  .row .val{{text-align:right;font:700 14px Inter,sans-serif;font-variant-numeric:tabular-nums lining-nums;}}
  .mb{{display:inline-block;height:7px;background:rgba(0,0,0,.07);border-radius:4px;overflow:hidden;}}
  .mb-fill{{display:block;height:100%;background:var(--navy);border-radius:4px;}}
  .row .sub{{font:400 10px Inter,sans-serif;color:var(--muted);text-align:right;white-space:nowrap;}}
  .chip-rail{{display:flex;gap:7px;overflow-x:auto;padding:4px 0 12px;-webkit-overflow-scrolling:touch;}}
  .chip{{flex:0 0 auto;font:700 12px Inter,sans-serif;text-decoration:none;color:var(--navy);background:#fff;border:1px solid rgba(0,0,0,.12);border-radius:999px;padding:5px 12px;}}
  .chip:hover{{border-color:var(--gold);}}
  .conf-sec{{margin:18px 0 6px;scroll-margin-top:16px;}}
  .conf-title{{font-family:'Bebas Neue',Impact,sans-serif;font-size:20px;letter-spacing:.03em;margin:0 0 8px;}}
  .conf-grid{{display:grid;grid-template-columns:1fr;gap:14px;}}
  @media(min-width:760px){{.conf-grid{{grid-template-columns:1fr 1fr;}}}}
  .board.compact .spot{{grid-template-columns:38px 1fr auto;padding:8px 10px;}} .board.compact .spot-rk{{font-size:32px;}} .board.compact .spot-val{{font-size:20px;}}
  @media(max-width:520px){{
    .row{{grid-template-columns:22px minmax(0,1fr) auto;row-gap:2px;}}
    .row .mb,.row .sub{{grid-column:2 / -1;justify-self:start;width:100%;}}
    .row .mb{{width:60%;}}
  }}
{NETWORK_CSS}
</style></head><body>
<div class="nav-strip"><a href="/">← CFB Index</a><a href="/rankings/">Rankings</a><a href="/chronicle/">The Chronicle</a><strong>Offseason Leaderboards</strong></div>
<div class="wrap">
  <header class="hero">
    <div class="stamp">Updated {escape(UPDATED)} · 2026 offseason</div>
    <h1>Offseason Leaderboards</h1>
    <p class="thesis">Who won the offseason? National and conference boards for the transfer portal, returning production, NFL exits, and roster talent — every FBS team ranked heading into 2026. Tap a team for the full file.</p>
    <div class="jumps"><a href="#national">National</a><a href="#flow">Talent Migration</a><a href="#network">Portal Pipelines</a><a href="#conference">By Conference</a></div>
  </header>

  <h2 class="sec" id="national">National Boards</h2>
  {flagship_html}
  <div class="grid">{grid_html}</div>
{flow_html}
{network_html}
  <h2 class="sec" id="conference">By Conference</h2>
  {conf_html}
</div></body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    n = sum(len(b.rows) for b in nat)
    print(f"[offseason-leaderboards] wrote {OUT} · {len(nat)} national boards · {n} national rows · conference sections added")


if __name__ == "__main__":
    build()
