"""Peer Comparator — Brief §4.9.

Auto-picks 3 closest peers by fingerprint distance across the box_savant
percentile vector, then renders a side-by-side comparison. Brief calls
for radar (desktop) + vertical percentile bar stack (mobile); we ship
the bar stack only (works at every breakpoint, mobile-first).

The "respect-gap grid" (model vs fan vs national belief) is deferred
until player FI lands — for now the comparator shows percentile bars
only, with a footer note that respect-gap returns when player belief
ingest completes.

Public API:
    render_peer_comparator(db, player_id, season_year, position) -> str
    PEER_COMPARATOR_CSS                                          -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .box_savant import compute_savant_bars, _position_bucket, _POSITION_BUCKETS


PEER_COMPARATOR_CSS = """
/* Peer Comparator module */
.peer-comparator {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.peer-comparator__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.peer-comparator__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 0.72rem;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0;
}
.peer-comparator__title {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.peer-comparator__pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 12px 0;
}
.peer-comparator__pill {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.10);
  font-size: 0.78rem;
  color: var(--text-soft, rgba(255,255,255,0.85));
}
.peer-comparator__pill--focal {
  background: var(--accolade-gold-base, #d1a23a);
  color: #15161a;
  font-weight: 600;
  border-color: var(--accolade-gold-base, #d1a23a);
}
.peer-comparator__pill-team {
  font-size: 0.70rem;
  color: var(--text-quiet, rgba(255,255,255,0.55));
}
.peer-comparator__pill--focal .peer-comparator__pill-team {
  color: rgba(0,0,0,0.55);
}
.peer-comparator__pill-sim {
  font-size: 0.66rem;
  color: var(--text-quiet, rgba(255,255,255,0.5));
  margin-left: 4px;
}
.peer-comparator__pill--focal .peer-comparator__pill-sim {
  color: rgba(0,0,0,0.55);
}
.peer-comparator__grid {
  display: grid;
  gap: 8px;
}
.peer-comparator__metric {
  display: grid;
  grid-template-columns: 10rem 1fr;
  align-items: center;
  gap: 12px;
}
.peer-comparator__metric-label {
  font-size: 0.80rem;
  color: var(--text-soft, rgba(255,255,255,0.78));
}
.peer-comparator__bars {
  display: grid;
  gap: 4px;
}
.peer-comparator__bar {
  display: grid;
  grid-template-columns: 1fr 3.5rem;
  align-items: center;
  gap: 8px;
}
.peer-comparator__bar-fill {
  position: relative;
  height: 8px;
  border-radius: 6px;
  background: rgba(255,255,255,0.05);
  overflow: hidden;
}
.peer-comparator__bar-fill > span {
  display: block;
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--pct-mid, #6b7280) 0%,
    var(--pct-b1, #4a78c4) 60%,
    var(--pct-b0, #1e6fd9) 100%
  );
  border-radius: 6px;
}
.peer-comparator__bar--focal .peer-comparator__bar-fill > span {
  background: var(--accolade-gold-base, #d1a23a);
}
.peer-comparator__bar-value {
  text-align: right;
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.65));
  font-weight: 500;
}
.peer-comparator__bar--focal .peer-comparator__bar-value {
  color: var(--accolade-gold-base, #d1a23a);
  font-weight: 600;
}
.peer-comparator__bar-label {
  font-size: 0.66rem;
  color: var(--text-quiet, rgba(255,255,255,0.5));
}
.peer-comparator__footnote {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  font-size: 0.72rem;
  color: var(--text-quiet, rgba(255,255,255,0.5));
  line-height: 1.45;
}
.peer-comparator--empty {
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-style: italic;
  padding: 14px;
}
@media (max-width: 640px) {
  .peer-comparator__metric {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  .peer-comparator__metric-label { font-size: 0.74rem; }
}
"""


def _peer_pool_query(
    db, season_year: int, position_bucket: str, exclude_player_id: int,
    limit: int = 80,
) -> list[dict[str, Any]]:
    """Return candidate peer player rows ranked by total volume in the bucket.

    We restrict by `player_season_stats.position` to keep the cohort honest.
    We rank by gate-metric (passing ATT for QB, rushing CAR for RB, etc.)
    so the closest peers are starters, not deep reserves.
    """
    members = _POSITION_BUCKETS.get(position_bucket, ())
    if not members:
        return []
    placeholders = ",".join(f"'{m}'" for m in members)
    gate_cat, gate_st = _gate_for_bucket(position_bucket)
    rows = db.query_all(
        f"""
        with player_latest as (
            select player_id, max(week) as max_week
              from player_season_stats
             where season_year = :s
               and category = :gate_cat
               and stat_type = :gate_st
               and position in ({placeholders})
             group by player_id
        ),
        ranked as (
            select pss.player_id, pss.stat_value_num as vol,
                   pss.team_name
              from player_season_stats pss
              join player_latest pl on pl.player_id = pss.player_id
                                   and pl.max_week  = pss.week
             where pss.season_year = :s
               and pss.category = :gate_cat
               and pss.stat_type = :gate_st
               and pss.position in ({placeholders})
               and pss.player_id != :pid
        )
        select r.player_id, r.team_name, r.vol, p.full_name
          from ranked r
          left join players p on p.player_id = r.player_id
         order by r.vol desc
         limit :lim
        """,
        {
            "s": season_year, "gate_cat": gate_cat, "gate_st": gate_st,
            "pid": exclude_player_id, "lim": limit,
        },
    )
    return list(rows)


def _gate_for_bucket(position_bucket: str) -> tuple[str, str]:
    if position_bucket == "QB":
        return "passing", "ATT"
    if position_bucket == "RB":
        return "rushing", "CAR"
    if position_bucket in {"WR", "TE"}:
        return "receiving", "REC"
    if position_bucket == "DEF":
        return "defensive", "TOT"
    return "passing", "ATT"


def _bars_to_vector(bars: list[dict[str, Any]]) -> dict[str, float]:
    """Map metric (category, stat_type) → percentile."""
    return {(b["category"], b["stat_type"]): b["percentile"] for b in bars}


def _distance(focal: dict, peer: dict) -> float | None:
    """Euclidean distance over shared percentile axes."""
    shared = [k for k in focal if k in peer]
    if len(shared) < 4:
        return None
    sq = 0.0
    for k in shared:
        d = focal[k] - peer[k]
        sq += d * d
    return (sq / len(shared)) ** 0.5


def _similarity_score(distance: float | None) -> int:
    """Map distance (0 = identical, ~100 = max possible) → similarity 0-100."""
    if distance is None:
        return 0
    return max(0, min(100, int(round(100 - distance))))


def render_peer_comparator(
    db, player_id: int | None, season_year: int | None,
    position: str | None = None,
) -> str:
    if db is None or player_id is None or season_year is None:
        return ""

    focal_bars = compute_savant_bars(db, int(player_id), int(season_year), position or "")
    if len(focal_bars) < 4:
        return (
            '<section class="peer-comparator peer-comparator--empty" '
            'data-module="peer-comparator-v2" data-state="empty">'
            'Peer Comparator returns once this player clears the Savant metric '
            'floor (4+ scored bars).'
            '</section>'
        )
    focal_vec = _bars_to_vector(focal_bars)

    # Fetch focal player metadata
    focal_meta = db.query_all(
        "select full_name from players where player_id = :pid",
        {"pid": int(player_id)},
    )
    focal_name = focal_meta[0]["full_name"] if focal_meta else "Player"
    focal_team_rows = db.query_all(
        """
        select team_name
          from player_season_stats
         where player_id = :pid and season_year = :s
         order by week desc limit 1
        """,
        {"pid": int(player_id), "s": int(season_year)},
    )
    focal_team = focal_team_rows[0]["team_name"] if focal_team_rows else ""

    bucket = _position_bucket(position or "")
    peer_pool = _peer_pool_query(db, int(season_year), bucket, int(player_id))
    if not peer_pool:
        return (
            '<section class="peer-comparator peer-comparator--empty" '
            'data-module="peer-comparator-v2" data-state="empty">'
            'No qualifying peer pool for this position bucket yet.'
            '</section>'
        )

    scored: list[dict[str, Any]] = []
    for cand in peer_pool[:60]:
        cand_bars = compute_savant_bars(
            db, int(cand["player_id"]), int(season_year), position or "",
        )
        if len(cand_bars) < 4:
            continue
        cand_vec = _bars_to_vector(cand_bars)
        d = _distance(focal_vec, cand_vec)
        if d is None:
            continue
        scored.append({
            "player_id": int(cand["player_id"]),
            "full_name": cand.get("full_name") or "—",
            "team_name": cand.get("team_name") or "",
            "distance": d,
            "similarity": _similarity_score(d),
            "bars": cand_bars,
        })
    scored.sort(key=lambda x: x["distance"])
    top3 = scored[:3]
    if not top3:
        return (
            '<section class="peer-comparator peer-comparator--empty" '
            'data-module="peer-comparator-v2" data-state="empty">'
            'No peer matched the focal fingerprint above the similarity floor.'
            '</section>'
        )

    # Build pill row
    pills_html = (
        '<span class="peer-comparator__pill peer-comparator__pill--focal">'
        f'{escape(focal_name)}'
        f'<span class="peer-comparator__pill-team">{escape(focal_team)}</span>'
        '</span>'
    )
    for p in top3:
        pills_html += (
            '<span class="peer-comparator__pill">'
            f'{escape(p["full_name"])}'
            f'<span class="peer-comparator__pill-team">{escape(p["team_name"])}</span>'
            f'<span class="peer-comparator__pill-sim">· {p["similarity"]}% sim</span>'
            '</span>'
        )

    # Build per-metric comparison grid using focal_bars as the order spine.
    grid_parts: list[str] = []
    for b in focal_bars:
        key = (b["category"], b["stat_type"])
        rows_html: list[str] = []
        # focal first
        rows_html.append(
            '<div class="peer-comparator__bar peer-comparator__bar--focal">'
            '<div class="peer-comparator__bar-fill">'
            f'<span style="width:{b["percentile"]:.1f}%"></span>'
            '</div>'
            f'<div class="peer-comparator__bar-value">{int(round(b["percentile"]))}<br/>'
            f'<span class="peer-comparator__bar-label">{escape(focal_name.split()[-1])}</span></div>'
            '</div>'
        )
        for p in top3:
            pvec = _bars_to_vector(p["bars"])
            pct = pvec.get(key)
            if pct is None:
                continue
            rows_html.append(
                '<div class="peer-comparator__bar">'
                '<div class="peer-comparator__bar-fill">'
                f'<span style="width:{pct:.1f}%"></span>'
                '</div>'
                f'<div class="peer-comparator__bar-value">{int(round(pct))}<br/>'
                f'<span class="peer-comparator__bar-label">{escape(p["full_name"].split()[-1])}</span></div>'
                '</div>'
            )
        grid_parts.append(
            '<div class="peer-comparator__metric">'
            f'<div class="peer-comparator__metric-label">{escape(b["label"])}</div>'
            f'<div class="peer-comparator__bars">{"".join(rows_html)}</div>'
            '</div>'
        )

    grid_html = "".join(grid_parts)

    return (
        '<section class="peer-comparator" '
        f'data-module="peer-comparator-v2" data-state="ready" data-peers="{len(top3)}">'
        '<header class="peer-comparator__head">'
        '<div>'
        '<p class="peer-comparator__eyebrow">Peer Comparator · Fingerprint match</p>'
        '<p class="peer-comparator__title">Three closest profiles by box-rate percentile</p>'
        '</div>'
        f'<span class="peer-comparator__meta">{len(top3)} peers · '
        f'{len(focal_bars)} metric{"s" if len(focal_bars)!=1 else ""}</span>'
        '</header>'
        f'<div class="peer-comparator__pills">{pills_html}</div>'
        f'<div class="peer-comparator__grid">{grid_html}</div>'
        '<p class="peer-comparator__footnote">Closest peers chosen by Euclidean distance '
        'across the box-rate percentile vector. Respect-gap grid (model vs fan vs national '
        'belief) returns when player-FI ingest completes.</p>'
        '</section>'
    )
