"""Signature Story leaderboard — discovery page for the 600+ players with
an engine-picked headline stat, sorted by engine score.

The player-page Signature Story shell embeds the winning metric inline,
but the only way to find those pages today is to already know a player's
slug. This board is the "index" — Top 50 by engine score, split by
position, each entry clickable to the player page.

Output: ``output/site/players/signature-stories.html``.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.signature_story import compute_signature_story_index


# Keep the page readable; the engine will happily produce hundreds but
# there's no editorial value in a 600-row table.
DEFAULT_LIMIT_PER_POSITION = 25


def _reconstruct_slug(full_name: str, player_id: int) -> str:
    parts = (full_name or "").lower().replace(".", "").split()
    base = "-".join(p for p in parts if p)
    return f"{base}-{player_id}" if base else f"player-{player_id}"


def _fetch_rows(db: Database, season_year: int) -> list[dict[str, Any]]:
    index = compute_signature_story_index(db, season_year)
    if not index:
        return []
    # Pull position + name once; the story payload doesn't include them.
    ids = tuple(index.keys())
    placeholders = ",".join(f":p_{i}" for i in range(len(ids)))
    params = {f"p_{i}": pid for i, pid in enumerate(ids)}
    roster = db.query_all(
        f"select player_id, full_name, position from players where player_id in ({placeholders})",
        params,
    )
    roster_by_id = {int(r["player_id"]): r for r in roster}

    rows: list[dict[str, Any]] = []
    for pid, story in index.items():
        r = roster_by_id.get(pid) or {}
        headline = story.get("headline_stat") or {}
        rows.append({
            "player_id": pid,
            "player_name": r.get("full_name") or f"Player {pid}",
            "position": (r.get("position") or "").strip() or "--",
            "slug": _reconstruct_slug(r.get("full_name") or "", pid),
            "metric_id": headline.get("metric_id") or "",
            "metric_label": headline.get("label") or "",
            "value": headline.get("value"),
            "unit": headline.get("unit") or "",
            "rank": headline.get("rank"),
            "cohort_size": headline.get("cohort_size"),
            "percentile": headline.get("percentile"),
            "confidence": (story.get("confidence") or {}).get("label") or "",
            "narrative": story.get("narrative") or "",
        })
    return rows


def _fmt_value(value: Any, unit: str) -> str:
    try:
        fv = float(value)
    except (TypeError, ValueError):
        return str(value or "--")
    if unit == "pct":
        return f"{fv:.1f}%"
    if unit == "EPA":
        return f"{fv:+.3f}"
    if unit == "QBR":
        return f"{fv:.1f}"
    if unit == "ratio":
        return f"{fv:.1f}"
    if unit == "yds":
        return f"{fv:,.0f}" if fv >= 100 else f"{fv:.1f}"
    if unit == "rate":
        return f"{fv:.0%}"
    return f"{fv:g}"


def render_signature_story_board_html(rows: list[dict[str, Any]], season_year: int) -> str:
    by_pos: dict[str, list[dict[str, Any]]] = {"QB": [], "RB": [], "WR": [], "OTHER": []}
    for r in rows:
        pos = r["position"]
        by_pos.setdefault(pos if pos in by_pos else "OTHER", []).append(r)

    # Rank within position by percentile desc (rank 1 = top percentile).
    sections: list[str] = []
    for pos in ("QB", "RB", "WR"):
        bucket = by_pos.get(pos) or []
        if not bucket:
            continue
        bucket.sort(key=lambda r: float(r.get("percentile") or 0), reverse=True)
        top = bucket[:DEFAULT_LIMIT_PER_POSITION]
        sections.append(_render_position_section(pos, top, len(bucket)))

    if not sections:
        body = """
          <section class="panel signature-board signature-board--empty">
            <p class="prose-panel">No player has enough stats to qualify for a Signature Story yet.</p>
          </section>
        """
    else:
        body = "\n".join(sections)

    from cfb_rankings.common.head_chrome import render_head_chrome

    head_chrome = render_head_chrome(
        page_path="/players/signature-stories/",
        title=f"Signature Stories — {season_year} | CFB Index",
        description=(
            f"Signature Stories for {season_year}: one headline stat per "
            "player, picked by an explainable engine, ordered by cohort "
            "percentile within position."
        ),
        og_type="article",
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Signature Stories — {season_year} | CFB Index</title>
    {head_chrome}
    <link rel="stylesheet" href="../style.css">
  </head>
  <body>
    <header class="site-header"><a href="../">← CFB Index</a></header>
    <main class="container">
      <h1>Signature Stories — {season_year}</h1>
      <p class="section-note">
        One headline stat per player, picked by an explainable engine from
        <code>seeds/signature_story_metrics.yaml</code>. Ordered by cohort
        percentile within position. {len(rows)} players qualify this season.
      </p>
      {body}
    </main>
  </body>
</html>
"""


def _render_position_section(pos: str, rows: list[dict[str, Any]], total: int) -> str:
    header_counts = f"Top {len(rows)} of {total}" if total > len(rows) else f"{len(rows)} qualifying"
    items = "".join(_render_row(r, rank=i + 1) for i, r in enumerate(rows))
    return f"""
      <section class="signature-board__section" data-position="{escape(pos)}">
        <h2>{escape(pos)}s <span class="section-note">— {escape(header_counts)}</span></h2>
        <ol class="signature-board__list">{items}</ol>
      </section>
    """


def _render_row(row: dict[str, Any], *, rank: int) -> str:
    pct = row.get("percentile")
    pct_txt = f"{float(pct):.0f}th" if pct is not None else "--"
    cohort_size = row.get("cohort_size") or 0
    cohort_rank = row.get("rank") or 0
    value_txt = _fmt_value(row.get("value"), row.get("unit") or "")
    narrative = (row.get("narrative") or "").strip()
    if len(narrative) > 200:
        narrative = narrative[:197].rstrip() + "…"
    return f"""
      <li class="signature-board__row">
        <div class="signature-board__rank">#{rank}</div>
        <div class="signature-board__name">
          <a href="{escape(row['slug'])}.html">{escape(row['player_name'])}</a>
          <span class="section-note">{escape(str(row.get('position') or ''))}</span>
        </div>
        <div class="signature-board__metric">
          <span>{escape(row.get('metric_label') or '')}</span>
          <strong>{escape(value_txt)}</strong>
          <span class="section-note">{escape(str(row.get('unit') or ''))}</span>
        </div>
        <div class="signature-board__rank-in-cohort">
          <span>Cohort rank</span>
          <strong>{int(cohort_rank)} / {int(cohort_size)}</strong>
          <span class="section-note">{escape(pct_txt)}</span>
        </div>
        <p class="signature-board__narrative">{escape(narrative)}</p>
      </li>
    """


def build_signature_story_board(
    db: Database,
    *,
    output_dir: str | Path = "output/site",
    season_year: int,
) -> Path:
    rows = _fetch_rows(db, season_year)
    html = render_signature_story_board_html(rows, season_year)
    out_dir = Path(output_dir) / "players"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "signature-stories.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


__all__ = ["build_signature_story_board", "render_signature_story_board_html"]
