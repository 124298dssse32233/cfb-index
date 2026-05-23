"""Top Players chip — surfaces the most-impactful 2024 players on the
roster as a 5-row list. Brief §11.6 ("the names that matter").

Sources from player_season_stats. For each team we compute the top 5
players by their headline position metric:
  - QB: passing yards
  - RB: rushing yards
  - WR/TE: receiving yards
  - Defense: tackles or sacks (composite)

Falls back to "Awaiting Signal" when no stats exist for the team.

Public API:
    render_top_players(db, profile, snapshot) -> str
    TOP_PLAYERS_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


TOP_PLAYERS_CSS = """
/* Top Players chip */
.top-players {
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-secondary, var(--accent-primary, #c9a24a));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.top-players__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
  margin-bottom: 10px;
}
.top-players__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.top-players__year {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
}
.top-players__list {
  display: grid;
  gap: 6px;
}
.top-players__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  gap: 12px 14px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
  border-radius: 6px;
  align-items: baseline;
}
.top-players__rank {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 13px;
  color: var(--accent-primary, #c9a24a);
  font-weight: 700;
  min-width: 22px;
}
.top-players__name {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(14px, 0.9vw + 8px, 17px);
  letter-spacing: 0.02em;
  color: var(--fg-primary);
  line-height: 1.1;
}
.top-players__pos {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.top-players__stat {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  color: var(--fg-secondary);
  text-align: right;
  min-width: 96px;
}
.top-players__stat strong {
  color: var(--accent-primary, #c9a24a);
  font-weight: 700;
}
"""


def _slug_from_name(name: str) -> str:
    import re
    s = (name or "").lower().strip()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    return s.strip("-")


def _fetch_position_leaders(db, team_id: int, season_year: int) -> list[dict[str, Any]]:
    """Return up to 5 top players using a position-weighted aggregate.

    Rather than category-specific lookups, we pick the leading scorer per
    headline category (passing YDS / rushing YDS / receiving YDS / tackles)
    and assemble the top-5 by composite "impact" score.
    """
    rows = db.query_all(
        """
        with final_week as (
          select player_id, category, stat_type, max(week) as wk
            from player_season_stats
           where team_id = :tid and season_year = :s
             and category in ('passing','rushing','receiving','defensive')
             and stat_type in ('YDS','TOT','SACKS')
           group by player_id, category, stat_type
        )
        select pss.player_id, pss.player_name, pss.position, pss.category,
               pss.stat_type, pss.stat_value_num
          from player_season_stats pss
          join final_week fw
            on fw.player_id = pss.player_id
           and fw.category = pss.category
           and fw.stat_type = pss.stat_type
           and fw.wk = pss.week
         where pss.team_id = :tid
           and pss.season_year = :s
           and pss.stat_value_num is not null
        """,
        {"tid": team_id, "s": season_year},
    )
    # Aggregate by player_id — pick HIGHEST-VALUE category for each player.
    by_player: dict[int, dict[str, Any]] = {}
    for r in rows:
        pid = r.get("player_id")
        if pid is None:
            continue
        pid = int(pid)
        val = float(r.get("stat_value_num") or 0)
        cat = r.get("category") or ""
        stat = r.get("stat_type") or ""
        if pid not in by_player or val > by_player[pid].get("value", 0):
            by_player[pid] = {
                "player_id": pid,
                "name": r.get("player_name") or "Unknown",
                "position": r.get("position") or "",
                "category": cat,
                "stat_type": stat,
                "value": val,
            }
    if not by_player:
        return []

    # Rank by category-relative score: scale values so different cats compare.
    # Use rough scaling factors based on typical season totals.
    SCALE = {
        ("passing", "YDS"): 1.0 / 4000,
        ("rushing", "YDS"): 1.0 / 1500,
        ("receiving", "YDS"): 1.0 / 1200,
        ("defensive", "TOT"): 1.0 / 100,
        ("defensive", "SACKS"): 1.0 / 12,
    }
    scored = []
    for p in by_player.values():
        sf = SCALE.get((p["category"], p["stat_type"]), 1.0 / 1000)
        p["score"] = p["value"] * sf
        scored.append(p)
    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored[:5]


def render_top_players(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    players = _fetch_position_leaders(
        db, int(snapshot.team_id), int(snapshot.season_year),
    )
    if not players:
        return ""

    rows_html: list[str] = []
    for idx, p in enumerate(players, start=1):
        name = p.get("name") or "Unknown"
        pos = p.get("position") or ""
        cat = p.get("category") or ""
        stat = p.get("stat_type") or ""
        val = p.get("value") or 0
        cat_label = {
            "passing": "PASS",
            "rushing": "RUSH",
            "receiving": "REC",
            "defensive": "DEF",
        }.get(cat, cat.upper())
        if val >= 100:
            v_label = f"{int(val):,}"
        else:
            v_label = f"{val:.1f}"
        rows_html.append(
            f"""<div class="top-players__row">
  <span class="top-players__rank">{idx}.</span>
  <span class="top-players__name">{escape(str(name))}</span>
  <span class="top-players__pos">{escape(str(pos) or cat_label)}</span>
  <span class="top-players__stat"><strong>{v_label}</strong> {escape(stat.lower())} ({escape(cat_label.lower())})</span>
</div>"""
        )

    return f"""
<section class="top-players" aria-labelledby="top-players-h"
         data-module="top-players" data-state="ready">
  <div class="top-players__head">
    <p class="top-players__eyebrow" id="top-players-h">Top Players · {snapshot.season_year}</p>
    <span class="top-players__year">{snapshot.season_year}</span>
  </div>
  <div class="top-players__list">{''.join(rows_html)}</div>
</section>"""


__all__ = ["render_top_players", "TOP_PLAYERS_CSS"]
