"""Players landing page — /players/index.html.

Combines top cuts from the Signature Story board and The Room board
into one landing, so the single "Players" nav entry leads readers to
both surfaces.

Layout: two panels.
  1. Signature Stories — top 3 per position (QB/RB/WR) by percentile,
     with a "see all" link to /players/signature-stories.html.
  2. The Room — every live mood card (short list), with a link to
     /players/the-room.html for the full board.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.fan_intelligence import compute_player_mood_index
from cfb_rankings.signature_story import compute_signature_story_index


SS_PREVIEW_PER_POSITION = 3


def _reconstruct_slug(full_name: str, player_id: int) -> str:
    parts = (full_name or "").lower().replace(".", "").split()
    base = "-".join(p for p in parts if p)
    return f"{base}-{player_id}" if base else f"player-{player_id}"


def _gather(db: Database, season_year: int, week: int) -> dict[str, Any]:
    room_index = compute_player_mood_index(db, season_year, week)
    ss_index = compute_signature_story_index(db, season_year)
    all_ids = set(room_index) | set(ss_index)
    if not all_ids:
        return {"room": [], "ss_by_pos": {}}
    placeholders = ",".join(f":p_{i}" for i in range(len(all_ids)))
    params = {f"p_{i}": pid for i, pid in enumerate(all_ids)}
    roster = db.query_all(
        f"select player_id, full_name, position from players where player_id in ({placeholders})",
        params,
    )
    roster_by_id = {int(r["player_id"]): r for r in roster}

    def _name_pos(pid: int) -> tuple[str, str]:
        r = roster_by_id.get(pid) or {}
        return (r.get("full_name") or f"Player {pid}", (r.get("position") or "").strip() or "--")

    room_rows = []
    for pid, story in room_index.items():
        name, pos = _name_pos(pid)
        room_rows.append({
            "pid": pid, "name": name, "position": pos,
            "slug": _reconstruct_slug(name, pid),
            "belief": (story.get("belief") or {}).get("score"),
            "archetype": story.get("archetype") or "--",
            "mentions": (story.get("sample") or {}).get("mentions") or 0,
            "bucket": story.get("primary_bucket") or "fan",
            "confidence": (story.get("confidence") or {}).get("label") or "--",
        })
    room_rows.sort(key=lambda r: int(r["mentions"]), reverse=True)

    ss_by_pos: dict[str, list[dict[str, Any]]] = {"QB": [], "RB": [], "WR": []}
    for pid, story in ss_index.items():
        name, pos = _name_pos(pid)
        if pos not in ss_by_pos:
            continue
        head = story.get("headline_stat") or {}
        ss_by_pos[pos].append({
            "pid": pid, "name": name, "position": pos,
            "slug": _reconstruct_slug(name, pid),
            "metric_label": head.get("label") or "",
            "value": head.get("value"),
            "unit": head.get("unit") or "",
            "rank": head.get("rank"),
            "cohort_size": head.get("cohort_size"),
            "percentile": head.get("percentile"),
            "narrative": story.get("narrative") or "",
        })
    for pos in ss_by_pos:
        ss_by_pos[pos].sort(key=lambda r: float(r.get("percentile") or 0), reverse=True)
        ss_by_pos[pos] = ss_by_pos[pos][:SS_PREVIEW_PER_POSITION]
    return {"room": room_rows, "ss_by_pos": ss_by_pos}


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


def render_players_landing_html(payload: dict[str, Any], season_year: int) -> str:
    room_rows = payload["room"]
    ss_by_pos = payload["ss_by_pos"]

    if room_rows:
        room_cards = "".join(_room_card(r) for r in room_rows[:6])
        room_count = len(room_rows)
        room_panel = f"""
          <section class="players-landing__panel">
            <div class="players-landing__panel-head">
              <h2>The Room</h2>
              <a href="the-room.html" class="players-landing__see-all">See all {room_count} →</a>
            </div>
            <p class="section-note">
              Players whose fan conversation has cleared the publication floor
              (≥12 mentions, ≥4 unique authors) this season.
            </p>
            <div class="players-landing__grid">{room_cards}</div>
          </section>
        """
    else:
        room_panel = """
          <section class="players-landing__panel players-landing__panel--empty">
            <div class="players-landing__panel-head"><h2>The Room</h2></div>
            <p class="mood-waiting-banner">Awaiting Signal — publishing starts once corpus density clears the floor.</p>
          </section>
        """

    if any(ss_by_pos.values()):
        pos_blocks = []
        for pos in ("QB", "RB", "WR"):
            rows = ss_by_pos.get(pos) or []
            if not rows:
                continue
            items = "".join(_ss_row(r) for r in rows)
            pos_blocks.append(f"""
              <div class="players-landing__ss-col" data-position="{pos}">
                <h3>{pos}s</h3>
                <ol class="players-landing__ss-list">{items}</ol>
              </div>
            """)
        ss_panel = f"""
          <section class="players-landing__panel">
            <div class="players-landing__panel-head">
              <h2>Signature Stories</h2>
              <a href="signature-stories.html" class="players-landing__see-all">See all →</a>
            </div>
            <p class="section-note">
              One headline stat per player, picked by an explainable engine —
              ranked by cohort percentile within position.
            </p>
            <div class="players-landing__ss-cols">{''.join(pos_blocks)}</div>
          </section>
        """
    else:
        ss_panel = ""

    from cfb_rankings.common.head_chrome import render_head_chrome

    title = f"Players — {season_year}"
    head_chrome = render_head_chrome(
        page_path="/players/landing/",
        title=f"{title} | CFB Index",
        description=(
            f"Player landing for the {season_year} season — Heisman watch, "
            "Signature Stories, prospect cohorts, and every player card on "
            "the site."
        ),
        og_type="article",
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | CFB Index</title>
    {head_chrome}
    <link rel="stylesheet" href="../style.css">
  </head>
  <body>
    <header class="site-header"><a href="../">← CFB Index</a></header>
    <main class="container players-landing">
      <h1>{escape(title)}</h1>
      <p class="prose-panel">
        Two lenses on every player worth watching. <strong>Signature
        Stories</strong> are the engine's top statistical case — the
        single number that makes the strongest argument for that player
        right now. <strong>The Room</strong> tracks who fans are
        actually <em>talking about</em> — own fans, rivals, national
        media — with a belief score that quantifies whether the
        conversation runs warm or cold. Together they answer two
        different questions: "who's playing best?" and "who's
        everyone watching?"
      </p>
      {ss_panel}
      {room_panel}
    </main>
  </body>
</html>
"""


def _room_card(row: dict[str, Any]) -> str:
    belief_txt = "--"
    b = row.get("belief")
    if b is not None:
        try: belief_txt = f"{float(b):+.1f}"
        except (TypeError, ValueError): pass
    return f"""
      <article class="players-landing__room-card">
        <h3><a href="{escape(row['slug'])}.html">{escape(row['name'])}</a></h3>
        <span class="section-note">{escape(row['position'])} · {escape(row['bucket'])}</span>
        <div class="players-landing__room-figs">
          <div><span>Belief</span><strong>{escape(belief_txt)}</strong></div>
          <div><span>{escape(row['archetype'])}</span></div>
          <div><span>Mentions</span><strong>{int(row['mentions'])}</strong></div>
        </div>
      </article>
    """


def _ss_row(row: dict[str, Any]) -> str:
    val = _fmt_value(row.get("value"), row.get("unit") or "")
    pct = row.get("percentile")
    pct_txt = f"{float(pct):.0f}th" if pct is not None else "--"
    rank = row.get("rank") or 0
    cohort = row.get("cohort_size") or 0
    return f"""
      <li class="players-landing__ss-row">
        <a href="{escape(row['slug'])}.html">{escape(row['name'])}</a>
        <div class="players-landing__ss-meta">
          <span>{escape(row.get('metric_label') or '')}</span>
          <strong>{escape(val)}</strong>
          <span class="section-note">#{rank}/{cohort} · {escape(pct_txt)}</span>
        </div>
      </li>
    """


def build_players_landing(
    db: Database,
    *,
    output_dir: str | Path = "output/site",
    season_year: int,
    week: int = 1,
) -> Path:
    """Write the player spotlight page.

    Output is `/players/spotlight.html` — a deliberate sibling to the
    existing all-players directory at `/players/index.html`, which
    already serves as a scrollable grid of every player card. The
    spotlight is the curated landing for readers who want the headline
    stats + live mood cards, not a full roster browse.
    """
    payload = _gather(db, season_year, week)
    html = render_players_landing_html(payload, season_year)
    out_dir = Path(output_dir) / "players"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "spotlight.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def render_home_player_spotlight(
    db: Database,
    *,
    season_year: int,
    week: int = 1,
) -> str:
    """Compact homepage preview: top Signature Story + top Room card.

    One 2-column strip for the home page. Empty string when no data
    qualifies so the home layout can drop the panel cleanly.
    """
    try:
        payload = _gather(db, season_year, week)
    except Exception:
        return ""

    room_rows = payload.get("room") or []
    ss_by_pos = payload.get("ss_by_pos") or {}
    # Pick the single most interesting Signature Story across QB/RB/WR.
    best_ss: dict[str, Any] | None = None
    for pos in ("QB", "RB", "WR"):
        bucket = ss_by_pos.get(pos) or []
        if not bucket:
            continue
        top = bucket[0]
        pct = top.get("percentile") or 0
        if best_ss is None or float(pct) > float(best_ss.get("percentile") or 0):
            best_ss = top
    best_room = room_rows[0] if room_rows else None

    if best_ss is None and best_room is None:
        return ""

    ss_block = ""
    if best_ss is not None:
        val = _fmt_value(best_ss.get("value"), best_ss.get("unit") or "")
        pct = best_ss.get("percentile")
        pct_txt = f"{float(pct):.0f}th percentile" if pct is not None else ""
        rank_txt = ""
        if best_ss.get("rank") and best_ss.get("cohort_size"):
            rank_txt = f"#{best_ss['rank']} of {best_ss['cohort_size']}"
        ss_block = f"""
          <article class="home-player-spotlight__card home-player-spotlight__card--ss">
            <span class="eyebrow">Signature Story — {escape(best_ss['position'])}</span>
            <h3><a href="players/{escape(best_ss['slug'])}.html">{escape(best_ss['name'])}</a></h3>
            <p class="home-player-spotlight__line">
              <strong>{escape(val)}</strong>
              <span class="section-note">{escape(best_ss.get('metric_label') or '')}</span>
            </p>
            <p class="section-note">{escape(rank_txt)} · {escape(pct_txt)}</p>
            <a class="home-player-spotlight__more" href="players/signature-stories.html">See all →</a>
          </article>
        """

    room_block = ""
    if best_room is not None:
        belief_txt = "--"
        b = best_room.get("belief")
        if b is not None:
            try: belief_txt = f"{float(b):+.1f}"
            except (TypeError, ValueError): pass
        room_block = f"""
          <article class="home-player-spotlight__card home-player-spotlight__card--room">
            <span class="eyebrow">The Room — {escape(best_room['position'])}</span>
            <h3><a href="players/{escape(best_room['slug'])}.html">{escape(best_room['name'])}</a></h3>
            <p class="home-player-spotlight__line">
              <strong>Belief {escape(belief_txt)}</strong>
              <span class="section-note">{escape(best_room.get('archetype') or '')}</span>
            </p>
            <p class="section-note">
              {int(best_room.get('mentions') or 0)} mentions · {escape(best_room.get('bucket') or 'fan')} bucket
            </p>
            <a class="home-player-spotlight__more" href="players/the-room.html">See all →</a>
          </article>
        """
    elif ss_block:
        # No live Room card yet; the side of the strip renders an Awaiting
        # Signal stub so the layout doesn't collapse.
        room_block = """
          <article class="home-player-spotlight__card home-player-spotlight__card--room home-player-spotlight__card--empty">
            <span class="eyebrow">The Room</span>
            <h3>Awaiting Signal</h3>
            <p class="section-note">
              Player mood cards light up once fan conversation clears the
              publication floor. <a href="players/the-room.html">How we gate this</a>.
            </p>
          </article>
        """

    return f"""
      <section class="home-player-spotlight panel">
        <header class="home-player-spotlight__head">
          <h2>Player Spotlight</h2>
          <a class="section-note" href="players/spotlight.html">Full spotlight →</a>
        </header>
        <div class="home-player-spotlight__grid">{ss_block}{room_block}</div>
      </section>
    """


__all__ = [
    "build_players_landing",
    "render_players_landing_html",
    "render_home_player_spotlight",
]
