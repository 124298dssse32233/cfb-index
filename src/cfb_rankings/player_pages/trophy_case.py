"""Trophy Case v2 — Brief §4.11 / Wave 21.

Distinct visual treatment for confirmed past honors. Groups honors by
stream (All-America consensus, All-America selectors, All-Conference,
position awards, freshman honors, weekly recognition) and surfaces
the highest tier per stream.

The detailed selector-by-selector view lives in selector_grid.py;
this module is the high-level "what awards he won" answer.

Public API:
    render_trophy_case(db, player_id) -> str
    TROPHY_CASE_CSS                   -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


TROPHY_CASE_CSS = """
/* Trophy Case v2 */
.trophy-case-v2 {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: linear-gradient(
    135deg,
    rgba(209, 162, 58, 0.04) 0%,
    rgba(255, 255, 255, 0.025) 60%
  );
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accolade-gold-base, #d1a23a);
  border-radius: 12px;
}
.trophy-case-v2__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.trophy-case-v2__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--accolade-gold-base, #d1a23a); margin: 0;
  font-weight: 600;
}
.trophy-case-v2__title {
  font-size: 1.05rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.trophy-case-v2__count {
  font-size: 0.76rem; color: var(--text-quiet, rgba(255,255,255,0.55));
}
.trophy-case-v2__streams {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}
.trophy-case-v2__stream {
  background: rgba(255,255,255,0.020);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 12px 14px;
  position: relative;
}
.trophy-case-v2__stream--top {
  border-color: var(--accolade-gold-base, #d1a23a);
  background: rgba(209, 162, 58, 0.08);
}
.trophy-case-v2__stream-label {
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0 0 6px 0;
}
.trophy-case-v2__stream--top .trophy-case-v2__stream-label {
  color: var(--accolade-gold-base, #d1a23a);
}
.trophy-case-v2__stream-headline {
  font-size: 1.0rem; font-weight: 700;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.trophy-case-v2__stream--top .trophy-case-v2__stream-headline {
  color: var(--accolade-gold-base, #d1a23a);
}
.trophy-case-v2__stream-detail {
  margin-top: 4px;
  font-size: 0.74rem;
  color: var(--text-soft, rgba(255,255,255,0.70));
  line-height: 1.4;
}
.trophy-case-v2__stream-medal {
  position: absolute;
  top: 10px; right: 10px;
  font-size: 1.1rem;
  filter: drop-shadow(0 1px 1px rgba(0,0,0,0.4));
}
.trophy-case-v2__empty {
  padding: 14px;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-style: italic;
}
"""


def _fetch_honors(db, player_id: int) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select honor_scope, honor_name, selector, placement,
               season_year, consensus_flag, unanimous_flag, position
          from player_honors
         where player_id = :pid
         order by season_year desc
        """,
        {"pid": player_id},
    )
    return list(rows)


def _all_america_summary(honors: list[dict[str, Any]]) -> tuple[str, str, str] | None:
    """Return (label, headline, detail) for the All-America stream."""
    aa = [h for h in honors if h["honor_scope"] == "all_america"]
    if not aa:
        return None
    by_year: dict[int, list[dict[str, Any]]] = {}
    for h in aa:
        sy = int(h["season_year"])
        by_year.setdefault(sy, []).append(h)
    # Take most recent year; report tier
    latest = max(by_year.keys())
    latest_aa = by_year[latest]
    selectors_first = [h for h in latest_aa if h.get("placement") == 1 and h.get("selector")]
    # Tier detection: prefer explicit honor-name signals over selector-count heuristics.
    # unanimous_flag is not yet populated in our data (all 0), so rely on the
    # "All-America (Consensus)" honor_name as the definitive consensus marker.
    # Never infer "Unanimous" purely from selector count — that over-promotes consensus picks.
    has_unanimous = any(h.get("unanimous_flag") for h in latest_aa)
    has_consensus = any("consensus" in (h.get("honor_name") or "").lower() for h in latest_aa)
    has_any = bool(selectors_first) or has_consensus
    if has_unanimous:
        return ("ALL-AMERICA · UNANIMOUS",
                f"Unanimous AA ({latest})",
                f"Named to {len(selectors_first)} first-team selectors")
    if has_consensus:
        n = len(selectors_first)
        detail = f"{n} first-team selectors" if n else f"{len(latest_aa)} selector mentions"
        return ("ALL-AMERICA · CONSENSUS",
                f"Consensus AA ({latest})",
                detail)
    if has_any:
        return ("ALL-AMERICA",
                f"Named All-American ({latest})",
                f"{len(selectors_first)} selectors honored him")
    # Has AA entries but no 1st-team placement — likely 2nd/3rd or just a list mention
    return ("ALL-AMERICA",
            f"All-America honors ({latest})",
            f"{len(latest_aa)} mentions across the selector pool")


def _all_conference_summary(honors: list[dict[str, Any]]) -> tuple[str, str, str] | None:
    ac = [h for h in honors if h["honor_scope"] == "all_conference"]
    if not ac:
        return None
    by_year: dict[int, list[dict[str, Any]]] = {}
    for h in ac:
        by_year.setdefault(int(h["season_year"]), []).append(h)
    latest = max(by_year.keys())
    rows = by_year[latest]
    first_team = any(h.get("placement") == 1 for h in rows)
    second_team = any(h.get("placement") == 2 for h in rows)
    # If no explicit placement, infer tier from selector count:
    # 4+ selectors all agreeing = almost certainly 1st team.
    # 2-3 selectors = probably 1st team but show modest label.
    null_placement_count = sum(1 for h in rows if h.get("placement") is None)
    if not first_team and not second_team and null_placement_count >= 4:
        first_team = True  # inferred
    elif not first_team and not second_team and null_placement_count >= 2:
        first_team = True  # inferred with lower confidence
    if first_team:
        label = "ALL-CONFERENCE · 1ST TEAM"
        headline = f"All-Conf 1st team ({latest})"
    elif second_team:
        label = "ALL-CONFERENCE · 2ND TEAM"
        headline = f"All-Conf 2nd team ({latest})"
    else:
        label = "ALL-CONFERENCE"
        headline = f"All-Conf mention ({latest})"
    names = sorted({(h.get("honor_name") or "") for h in rows if h.get("honor_name")})
    detail = ", ".join(names[:3]) + (f" +{len(names)-3} more" if len(names) > 3 else "")
    return (label, headline, detail)


def _position_award_summary(honors: list[dict[str, Any]]) -> tuple[str, str, str] | None:
    # Position awards (Davey, Doak, Biletnikoff, Outland, Thorpe, etc.)
    POSITION_KEYWORDS = [
        "davey", "doak", "biletnikoff", "outland", "thorpe", "nagurski",
        "bednarik", "butkus", "manning", "unitas", "mackey", "groza",
        "ray guy", "maxwell", "walter camp", "heisman",
    ]
    pa = [h for h in honors
          if any(k in (h.get("honor_name") or "").lower() for k in POSITION_KEYWORDS)]
    if not pa:
        return None
    by_year: dict[int, list[dict[str, Any]]] = {}
    for h in pa:
        by_year.setdefault(int(h["season_year"]), []).append(h)
    latest = max(by_year.keys())
    rows = by_year[latest]
    headline = ", ".join({(h.get("honor_name") or "").replace("Award", "").strip() for h in rows[:3]})
    return ("POSITION AWARDS", headline, f"{latest} season")


def _freshman_summary(honors: list[dict[str, Any]]) -> tuple[str, str, str] | None:
    fa = [h for h in honors
          if "freshman" in (h.get("honor_name") or "").lower()
          or h.get("honor_scope") == "freshman_all_america"]
    if not fa:
        return None
    by_year: dict[int, list[dict[str, Any]]] = {}
    for h in fa:
        by_year.setdefault(int(h["season_year"]), []).append(h)
    latest = max(by_year.keys())
    return ("FRESHMAN HONORS",
            f"Freshman recognition ({latest})",
            f"{len(by_year[latest])} mention(s)")


def render_trophy_case(db, player_id: int | None) -> str:
    if db is None or player_id is None:
        return ""
    honors = _fetch_honors(db, int(player_id))
    if not honors:
        return ""

    streams: list[tuple[str, str, str, bool, str]] = []
    # Each entry: (label, headline, detail, is_top, medal_glyph)
    aa = _all_america_summary(honors)
    if aa:
        label, headline, detail = aa
        is_top = "UNANIMOUS" in label or "CONSENSUS" in label
        streams.append((label, headline, detail, is_top, "🏆" if is_top else "🥇"))
    pa = _position_award_summary(honors)
    if pa:
        streams.append((pa[0], pa[1], pa[2], False, "🏅"))
    ac = _all_conference_summary(honors)
    if ac:
        is_top = "1ST TEAM" in ac[0]
        streams.append((ac[0], ac[1], ac[2], is_top, "🥈" if is_top else "🎖"))
    fr = _freshman_summary(honors)
    if fr:
        streams.append((fr[0], fr[1], fr[2], False, "🎓"))

    if not streams:
        return ""

    def _esc(text: str) -> str:
        """Escape HTML and normalize middle-dot U+00B7 to &middot; entity."""
        return escape(text).replace('·', '&middot;')

    stream_cards: list[str] = []
    for label, headline, detail, is_top, medal in streams:
        cls = " trophy-case-v2__stream--top" if is_top else ""
        stream_cards.append(
            f'<div class="trophy-case-v2__stream{cls}">'
            f'<span class="trophy-case-v2__stream-medal">{medal}</span>'
            f'<p class="trophy-case-v2__stream-label">{_esc(label)}</p>'
            f'<p class="trophy-case-v2__stream-headline">{_esc(headline)}</p>'
            f'<p class="trophy-case-v2__stream-detail">{_esc(detail)}</p>'
            '</div>'
        )

    return (
        '<section class="trophy-case-v2" '
        f'data-module="trophy-case-v2" data-state="ready" '
        f'data-streams="{len(streams)}">'
        '<header class="trophy-case-v2__head">'
        '<div>'
        '<p class="trophy-case-v2__eyebrow">Trophy Case &middot; Confirmed honors</p>'
        '<p class="trophy-case-v2__title">What the selectors said</p>'
        '</div>'
        f'<span class="trophy-case-v2__count">{len(honors)} entries</span>'
        '</header>'
        f'<div class="trophy-case-v2__streams">{"".join(stream_cards)}</div>'
        '</section>'
    )
