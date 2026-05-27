"""Career-retrospective Standing — Brief §7.6 / Wave 18.

For alumni and seniors-post-bowl: a cross-season standing rail showing
each season this player played, with peak rung highlighted. The
in-season variant (standing_rail.py) shows a single-season position
on the 17-rung ladder; this variant shows the multi-season ARC.

A player qualifies for the career-retrospective variant when:
  • They have NFL draft entries, OR
  • Their last player_season_stats season < current_year - 1, OR
  • They have 3+ seasons of stats

This module is COMPLEMENTARY to standing_rail — it can render
alongside on an alumni page, OR replace standing_rail entirely when
no in-season data is meaningful.

Public API:
    render_career_standing(db, player_id) -> str
    CAREER_STANDING_CSS                   -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .standing_aggregator import build_standing_payload


CAREER_STANDING_CSS = """
/* Career-retrospective Standing */
.career-standing {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accolade-gold-base, #d1a23a);
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.career-standing__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.career-standing__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.career-standing__title {
  font-size: 1.05rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.career-standing__peak {
  font-size: 0.80rem;
  color: var(--accolade-gold-base, #d1a23a);
  font-weight: 600;
}
.career-standing__seasons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.career-standing__season {
  background: rgba(255,255,255,0.018);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 12px 14px;
  position: relative;
}
.career-standing__season--peak {
  border-color: var(--accolade-gold-base, #d1a23a);
  background: rgba(209, 162, 58, 0.06);
}
.career-standing__season-year {
  font-size: 0.70rem; letter-spacing: 0.12em;
  color: var(--text-quiet, rgba(255,255,255,0.55));
}
.career-standing__season-team {
  font-size: 0.78rem;
  color: var(--text-soft, rgba(255,255,255,0.80));
  margin: 2px 0;
}
.career-standing__season-rung {
  font-size: 1.0rem;
  font-weight: 700;
  color: var(--text-bright, rgba(255,255,255,0.92));
  margin: 4px 0 0 0;
}
.career-standing__season--peak .career-standing__season-rung {
  color: var(--accolade-gold-base, #d1a23a);
}
.career-standing__season-tier {
  font-size: 0.70rem;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin-top: 2px;
}
.career-standing__peak-pin {
  position: absolute;
  top: -8px; right: -8px;
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  background: var(--accolade-gold-base, #d1a23a);
  color: #15161a;
  border-radius: 50%;
  font-size: 0.66rem; font-weight: 700;
  letter-spacing: 0;
}
.career-standing__nfl-badge {
  display: inline-block;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.66rem;
  letter-spacing: 0.08em;
  color: var(--text-soft, rgba(255,255,255,0.78));
  margin-top: 8px;
}
"""


_RUNG_NAMES = {
    0: "Walk-on",
    1: "Backup",
    2: "Rotation",
    3: "Starter",
    4: "Regular contributor",
    5: "Solid starter",
    6: "Quality starter",
    7: "All-Conf 2nd",
    8: "All-Conf 1st",
    9: "All-Am 3rd",
    10: "All-Am 2nd",
    11: "All-Am 1st",
    12: "POY",
    13: "Watch-list honoree",
    14: "POY finalist",
    15: "Heisman finalist",
    16: "Heisman winner",
}
_TIER_LABELS = {
    1: "Floor",
    2: "Established",
    3: "Quality starter",
    4: "All-Conference",
    5: "National recognition",
    6: "National honors",
}


def _all_seasons_for_player(db, player_id: int) -> list[dict[str, Any]]:
    """Return distinct seasons + position + team for this player."""
    rows = db.query_all(
        """
        with player_latest as (
            select season_year, max(week) as max_week
              from player_season_stats
             where player_id = :pid
             group by season_year
        )
        select distinct pss.season_year, pss.position, pss.team_name
          from player_season_stats pss
          join player_latest pl on pl.season_year = pss.season_year
                               and pl.max_week  = pss.week
         where pss.player_id = :pid
         order by pss.season_year asc
        """,
        {"pid": player_id},
    )
    return list(rows)


def _nfl_draft(db, player_id: int) -> dict[str, Any] | None:
    rows = db.query_all(
        """
        select draft_year, round, pick, overall, nfl_team
          from player_nfl_draft
         where player_id = :pid
         order by draft_year desc limit 1
        """,
        {"pid": player_id},
    )
    return dict(rows[0]) if rows else None


def render_career_standing(db, player_id: int | None) -> str:
    if db is None or player_id is None:
        return ""
    seasons = _all_seasons_for_player(db, int(player_id))
    if len(seasons) < 2:
        return ""  # career-retrospective only makes sense for multi-season

    # Compute standing for each season
    enriched: list[dict[str, Any]] = []
    peak_rung = -1
    peak_idx = -1
    for i, s in enumerate(seasons):
        sy = int(s["season_year"])
        pos = (s.get("position") or "").strip()
        team = (s.get("team_name") or "").strip()
        try:
            payload = build_standing_payload(db, int(player_id), sy, pos)
        except Exception:
            payload = None
        rung_id = None
        tier_label = None
        if isinstance(payload, dict):
            rung_id = payload.get("current_rung_id")
            tier = payload.get("current_tier")
            if isinstance(tier, int):
                tier_label = _TIER_LABELS.get(tier)
        if isinstance(rung_id, int) and rung_id > peak_rung:
            peak_rung = rung_id
            peak_idx = i
        enriched.append({
            "year": sy, "position": pos, "team": team,
            "rung_id": rung_id, "tier_label": tier_label,
        })

    if peak_rung < 0:
        return ""  # no Standing data for any season

    nfl = _nfl_draft(db, int(player_id))

    # Season cards
    season_cards: list[str] = []
    for i, e in enumerate(enriched):
        is_peak = (i == peak_idx)
        rung_id = e["rung_id"]
        rung_text = (
            f"R{rung_id:02d} · {_RUNG_NAMES.get(int(rung_id), '—')}"
            if isinstance(rung_id, int) else "—"
        )
        cls = " career-standing__season--peak" if is_peak else ""
        pin = ('<span class="career-standing__peak-pin" title="Peak season">★</span>'
               if is_peak else "")
        season_cards.append(
            f'<div class="career-standing__season{cls}">'
            f'{pin}'
            f'<p class="career-standing__season-year">{e["year"]}</p>'
            f'<p class="career-standing__season-team">{escape(e["team"] or "—")}'
            f'{" · " + escape(e["position"]) if e["position"] else ""}</p>'
            f'<p class="career-standing__season-rung">{escape(rung_text)}</p>'
            f'<p class="career-standing__season-tier">'
            f'{escape(e["tier_label"] or "")}'
            f'</p>'
            '</div>'
        )

    nfl_block = ""
    if nfl:
        nfl_block = (
            f'<div class="career-standing__nfl-badge">'
            f'NFL Draft {nfl["draft_year"]} · Rd {nfl["round"]}, Pick {nfl["pick"]} '
            f'· #{nfl["overall"]} overall · {escape(str(nfl.get("nfl_team") or ""))}'
            '</div>'
        )

    peak_label = f"Peak: R{peak_rung:02d} {_RUNG_NAMES.get(peak_rung, '')} · {enriched[peak_idx]['year']}"
    return (
        '<section class="career-standing" '
        f'data-module="career-standing" data-state="ready" '
        f'data-seasons="{len(seasons)}">'
        '<header class="career-standing__head">'
        '<div>'
        '<p class="career-standing__eyebrow">Career arc · Season-by-season Standing</p>'
        f'<p class="career-standing__title">'
        f'{len(seasons)} seasons on the ladder'
        '</p>'
        '</div>'
        f'<span class="career-standing__peak">{escape(peak_label)}</span>'
        '</header>'
        f'<div class="career-standing__seasons">{"".join(season_cards)}</div>'
        f'{nfl_block}'
        '</section>'
    )
