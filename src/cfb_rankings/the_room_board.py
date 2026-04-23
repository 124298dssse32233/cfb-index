"""Players in The Room — discovery page for live player-scope mood cards.

The core player-page modules live inside 17k HTML files; without a
leaderboard surface, nobody finds the 2–3 players whose mood cards
actually cleared the floor. This builder writes a small standalone page
that lists every player whose ``The Room`` card renders ``data-state="ready"``
today, with belief score, bucket, confidence, and the representative
quote.

Output: ``output/site/players/the-room.html``. The page is idempotent —
re-running overwrites it cleanly.

CLI: ``python manage.py build-the-room-board [--season YYYY] [--week N]``.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.fan_intelligence import compute_player_mood_index


def _fetch_rows(db: Database, season_year: int, week: int) -> list[dict[str, Any]]:
    """Return one row per live Room card, ordered by mention_count desc."""
    index = compute_player_mood_index(db, season_year, week)
    if not index:
        return []
    rows: list[dict[str, Any]] = []
    for pid, story in index.items():
        player = db.query_one(
            "select full_name, position from players where player_id = :pid",
            {"pid": pid},
        )
        name = (player or {}).get("full_name") or f"Player {pid}"
        position = (player or {}).get("position") or ""
        slug = _reconstruct_slug(name, pid)
        rows.append({
            "player_id": pid,
            "player_name": name,
            "position": position,
            "slug": slug,
            "belief": (story.get("belief") or {}).get("score"),
            "belief_label": (story.get("belief") or {}).get("label") or "",
            "archetype": story.get("archetype") or "",
            "confidence": (story.get("confidence") or {}).get("label") or "",
            "scope": story.get("scope") or "",
            "primary_bucket": story.get("primary_bucket") or "",
            "mentions": (story.get("sample") or {}).get("mentions") or 0,
            "authors": (story.get("sample") or {}).get("authors") or 0,
            "top_quote_text": (story.get("top_quote") or {}).get("text"),
            "top_quote_author": (story.get("top_quote") or {}).get("author_pseudonym"),
            "top_quote_source": (story.get("top_quote") or {}).get("source_url"),
        })
    rows.sort(key=lambda r: int(r["mentions"]), reverse=True)
    return rows


def _reconstruct_slug(full_name: str, player_id: int) -> str:
    parts = (full_name or "").lower().replace(".", "").split()
    base = "-".join(p for p in parts if p)
    return f"{base}-{player_id}" if base else f"player-{player_id}"


def render_the_room_board_html(rows: list[dict[str, Any]], season_year: int, week: int) -> str:
    if not rows:
        body = """
          <section class="panel the-room-board the-room-board--empty">
            <p class="prose-panel">
              No player in this season has cleared the mention floor yet.
              We'll publish cards as soon as corpus density picks up — for
              in-season data, that usually means Monday mornings after Week 1.
            </p>
            <p class="section-note mood-waiting-banner">Awaiting Signal</p>
          </section>
        """
    else:
        cards = "".join(_render_card(r) for r in rows)
        body = f"""
          <p class="section-note">
            {len(rows)} player{'s' if len(rows) != 1 else ''} with enough
            conversation signal to publish a mood card this
            {"week" if any(r["scope"] == "weekly" for r in rows) else "season"}.
            Gated at {_floor_copy()}.
          </p>
          <section class="the-room-board__grid">{cards}</section>
        """

    title = f"Players in The Room — {season_year}"
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | CFB Index</title>
    <link rel="stylesheet" href="../style.css">
  </head>
  <body>
    <header class="site-header"><a href="../">← CFB Index</a></header>
    <main class="container">
      <h1>{escape(title)}</h1>
      {body}
    </main>
  </body>
</html>
"""


def _floor_copy() -> str:
    from cfb_rankings.fan_intelligence import (
        MIN_AUTHORS_FOR_SIGNAL,
        MIN_MENTIONS_FOR_SIGNAL,
    )
    return f"≥{MIN_MENTIONS_FOR_SIGNAL} mentions and ≥{MIN_AUTHORS_FOR_SIGNAL} unique authors"


def _render_card(row: dict[str, Any]) -> str:
    belief_txt = "--"
    belief_score = row.get("belief")
    if belief_score is not None:
        try:
            belief_txt = f"{float(belief_score):+.1f}"
        except (TypeError, ValueError):
            belief_txt = "--"

    quote_block = ""
    if row.get("top_quote_text"):
        src_url = row.get("top_quote_source") or ""
        attrib = escape(str(row.get("top_quote_author") or "fan"))
        attrib_html = f'<a href="{escape(src_url)}">{attrib}</a>' if src_url else attrib
        quote_block = f"""
          <blockquote class="the-room-board__quote">
            <p>{escape(str(row["top_quote_text"])[:220])}</p>
            <cite>— {attrib_html}</cite>
          </blockquote>
        """
    scope_label = (
        "season rollup" if row.get("scope") == "season" else "this week"
    )
    bucket = row.get("primary_bucket") or "fan"
    return f"""
      <article class="the-room-board__card"
               data-module="the-room-board-card"
               data-primary-bucket="{escape(bucket)}">
        <header class="the-room-board__header">
          <h2><a href="{escape(row["slug"])}.html">{escape(row["player_name"])}</a></h2>
          <span class="the-room-board__meta">{escape(str(row["position"] or ""))} · {escape(scope_label)}</span>
        </header>
        <div class="the-room-board__figures">
          <div><span>Belief</span><strong>{escape(belief_txt)}</strong></div>
          <div><span>Archetype</span><strong>{escape(str(row.get("archetype") or "--"))}</strong></div>
          <div><span>Mentions</span><strong>{int(row["mentions"])}</strong></div>
          <div><span>Authors</span><strong>{int(row["authors"])}</strong></div>
          <div><span>Primary</span><strong>{escape(bucket)}</strong></div>
          <div><span>Confidence</span><strong>{escape(str(row.get("confidence") or "--"))}</strong></div>
        </div>
        {quote_block}
      </article>
    """


def build_the_room_board(
    db: Database,
    *,
    output_dir: str | Path = "output/site",
    season_year: int,
    week: int = 1,
) -> Path:
    rows = _fetch_rows(db, season_year, week)
    html = render_the_room_board_html(rows, season_year, week)
    out_dir = Path(output_dir) / "players"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "the-room.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


__all__ = ["build_the_room_board", "render_the_room_board_html"]
