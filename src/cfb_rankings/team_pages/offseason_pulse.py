"""Offseason Pulse module — surfaces the four CFBD-tier-2 data feeds that
collectively answer the offseason question every fan walks in with:
*"how is my program shaping up for next season?"*

Components (all sourced from already-ingested CFBD tables):

  1. Recruiting Class    -- `recruiting_entries` team-aggregate rating + national rank
  2. Returning Production -- `returning_production` total returning % + QB flag
  3. Talent Composite     -- `team_talent_snapshots` 247 composite + national rank
  4. Transfer Activity    -- `transfer_entries` net incoming/outgoing this cycle

The module honors graceful degradation. Any individual cell falls back to an
"Awaiting Signal" pill in mascot voice when its underlying row is missing.
The wrapper renders only if ≥2 of the 4 cells have signal (otherwise the
whole module returns "" and the page skips it).

Brief mapping:
  Brief §11.4 trajectory chip  → forward-looking sibling
  Brief Part III §32 sentience → "OFFSEASON · COMMITMENT SEASON" tone
  Audit T9 Recruiting          → this module IS the resolution at team level

Public API:
    render_offseason_pulse(db, profile, snapshot) -> str
    OFFSEASON_PULSE_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


OFFSEASON_PULSE_CSS = """
/* Offseason Pulse module */
.offseason-pulse {
  margin-bottom: clamp(20px, 3vw, 32px);
  padding: clamp(16px, 2.2vw, 24px) clamp(18px, 2.4vw, 28px);
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.015) 50%,
    rgba(0, 0, 0, 0.08) 100%
  );
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, #c9a24a);
  border-radius: 14px;
  font-variant-numeric: tabular-nums;
}
.offseason-pulse__header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: clamp(12px, 1.6vw, 18px);
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 10px;
}
.offseason-pulse__title {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(18px, 1.2vw + 10px, 24px);
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.offseason-pulse__cycle {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.offseason-pulse__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: clamp(10px, 1.4vw, 16px);
}
@media (max-width: 720px) {
  .offseason-pulse__grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 380px) {
  .offseason-pulse__grid { grid-template-columns: 1fr; }
}
.offseason-pulse__cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: clamp(10px, 1.4vw, 14px) clamp(12px, 1.6vw, 16px);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
  border-radius: 10px;
  min-height: 88px;
}
.offseason-pulse__cell--empty {
  background: rgba(255, 255, 255, 0.012);
  border-style: dashed;
}
.offseason-pulse__cell-eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.offseason-pulse__cell-headline {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.6vw + 8px, 32px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--fg-primary);
  margin: 2px 0 0 0;
}
.offseason-pulse__cell-headline--positive { color: #4f9d6b; }
.offseason-pulse__cell-headline--warning  { color: #c98c1a; }
.offseason-pulse__cell-headline--negative { color: #c95151; }

.offseason-pulse__cell-context {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  color: var(--fg-secondary);
  margin: 0;
}
.offseason-pulse__cell-narrative {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 12px;
  font-style: italic;
  line-height: 1.35;
  color: var(--fg-secondary);
  margin: 4px 0 0 0;
}
.offseason-pulse__cell-empty-pill {
  display: inline-block;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
  background: rgba(255, 255, 255, 0.04);
  border-radius: 999px;
  padding: 3px 8px;
  margin-top: 4px;
}
"""


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

def _latest_team_recruiting(db, team_id: int) -> dict[str, Any] | None:
    """Most recent team-level recruiting class for this team."""
    rows = db.query_all(
        """
        select season_year, rating, source_name
          from recruiting_entries
         where team_id = :tid and class_key = 'team' and rating is not null
         order by season_year desc
         limit 1
        """,
        {"tid": team_id},
    )
    if not rows:
        return None
    return rows[0]


def _national_recruiting_rank(db, season_year: int, rating: float) -> int | None:
    """How many FBS teams have a strictly-higher class rating for this season."""
    rows = db.query_all(
        """
        select count(*) as ahead
          from recruiting_entries
         where season_year = :s
           and class_key = 'team'
           and rating is not null
           and rating > :r
        """,
        {"s": season_year, "r": rating},
    )
    if not rows:
        return None
    return int(rows[0].get("ahead") or 0) + 1


def _latest_returning_production(db, team_id: int) -> dict[str, Any] | None:
    rows = db.query_all(
        """
        select season_year, returning_total, returning_offense,
               returning_defense, returning_qb
          from returning_production
         where team_id = :tid
         order by season_year desc
         limit 1
        """,
        {"tid": team_id},
    )
    if not rows:
        return None
    return rows[0]


def _latest_talent_composite(db, team_id: int) -> dict[str, Any] | None:
    rows = db.query_all(
        """
        select season_year, talent_score, talent_rank
          from team_talent_snapshots
         where team_id = :tid and talent_score is not null
         order by season_year desc
         limit 1
        """,
        {"tid": team_id},
    )
    if not rows:
        return None
    return rows[0]


def _national_talent_rank(db, season_year: int, score: float) -> int | None:
    rows = db.query_all(
        """
        select count(*) as ahead
          from team_talent_snapshots
         where season_year = :s
           and talent_score is not null
           and talent_score > :sc
        """,
        {"s": season_year, "sc": score},
    )
    if not rows:
        return None
    return int(rows[0].get("ahead") or 0) + 1


def _transfer_activity(db, team_id: int) -> dict[str, Any] | None:
    """Net incoming + outgoing transfers across the most recent cycle."""
    rows = db.query_all(
        """
        select season_year,
               sum(case when to_team_id = :tid then 1 else 0 end) as incoming,
               sum(case when from_team_id = :tid then 1 else 0 end) as outgoing
          from transfer_entries
         where (to_team_id = :tid or from_team_id = :tid)
         group by season_year
         order by season_year desc
         limit 1
        """,
        {"tid": team_id},
    )
    if not rows:
        return None
    row = rows[0]
    if not row.get("incoming") and not row.get("outgoing"):
        return None
    return row


# ---------------------------------------------------------------------------
# Cell render
# ---------------------------------------------------------------------------

def _cell(eyebrow: str, headline: str, context: str, narrative: str,
          tone: str = "") -> str:
    tone_cls = f" offseason-pulse__cell-headline--{tone}" if tone else ""
    return (
        '<div class="offseason-pulse__cell" data-ready="true">'
        f'<p class="offseason-pulse__cell-eyebrow">{escape(eyebrow)}</p>'
        f'<p class="offseason-pulse__cell-headline{tone_cls}">{escape(headline)}</p>'
        f'<p class="offseason-pulse__cell-context">{escape(context)}</p>'
        f'<p class="offseason-pulse__cell-narrative">{escape(narrative)}</p>'
        '</div>'
    )


def _empty_cell(eyebrow: str, awaiting_voice: str) -> str:
    return (
        '<div class="offseason-pulse__cell offseason-pulse__cell--empty" data-ready="false">'
        f'<p class="offseason-pulse__cell-eyebrow">{escape(eyebrow)}</p>'
        '<span class="offseason-pulse__cell-empty-pill">Awaiting signal</span>'
        f'<p class="offseason-pulse__cell-narrative">{escape(awaiting_voice)}</p>'
        '</div>'
    )


def _recruiting_cell(db, profile: Profile, team_id: int) -> tuple[str, bool]:
    row = _latest_team_recruiting(db, team_id)
    awaiting = (profile.mascot_voice.get("awaiting_signal", "Awaiting signal.")
                if profile.mascot_voice else "Awaiting signal.")
    if not row:
        return _empty_cell("Recruiting Class", awaiting), False
    rating = float(row.get("rating") or 0.0)
    season = int(row.get("season_year"))
    rank = _national_recruiting_rank(db, season, rating)
    if rank is None:
        return _empty_cell("Recruiting Class", awaiting), False
    if rank <= 10:
        tone, story = "positive", "Top-10 class. Talent floor reset upward."
    elif rank <= 25:
        tone, story = "positive", "Top-25 class. Recruiting infrastructure is competitive."
    elif rank <= 60:
        tone, story = "", "Mid-major recruiting tier. Development becomes the lever."
    else:
        tone, story = "warning", "Outside the recruiting top 60. Roster gaps must close via portal."
    return _cell(
        eyebrow="Recruiting Class",
        headline=f"#{rank} nationally",
        context=f"{season} cycle · 247 composite rating {rating:.1f}",
        narrative=story,
        tone=tone,
    ), True


def _returning_cell(db, profile: Profile, team_id: int) -> tuple[str, bool]:
    row = _latest_returning_production(db, team_id)
    awaiting = (profile.mascot_voice.get("awaiting_signal", "Awaiting signal.")
                if profile.mascot_voice else "Awaiting signal.")
    if not row or row.get("returning_total") is None:
        return _empty_cell("Returning Production", awaiting), False
    total = float(row.get("returning_total") or 0.0) * 100
    qb = row.get("returning_qb")
    season = int(row.get("season_year"))

    qb_chunk = ""
    if qb is not None:
        try:
            qb_pct = float(qb) * 100
            if qb_pct >= 90:
                qb_chunk = "QB returns."
            elif qb_pct >= 50:
                qb_chunk = "QB room mostly intact."
            elif qb_pct >= 10:
                qb_chunk = "QB transition under way."
            else:
                qb_chunk = "QB position open."
        except (TypeError, ValueError):
            pass

    if total >= 75:
        tone = "positive"
        story = f"Top-tier continuity. {qb_chunk}".strip()
    elif total >= 60:
        tone = "positive"
        story = f"Above-average continuity. {qb_chunk}".strip()
    elif total >= 45:
        tone = ""
        story = f"Mid-pack continuity. {qb_chunk}".strip()
    else:
        tone = "warning"
        story = f"Heavy roster turnover. {qb_chunk}".strip()

    return _cell(
        eyebrow="Returning Production",
        headline=f"{total:.0f}%",
        context=f"{season} cycle · CFBD weighted",
        narrative=story or "Continuity measure from prior-year usage.",
        tone=tone,
    ), True


def _talent_cell(db, profile: Profile, team_id: int) -> tuple[str, bool]:
    row = _latest_talent_composite(db, team_id)
    awaiting = (profile.mascot_voice.get("awaiting_signal", "Awaiting signal.")
                if profile.mascot_voice else "Awaiting signal.")
    if not row:
        return _empty_cell("Talent Composite", awaiting), False
    score = float(row.get("talent_score") or 0.0)
    rank_val = row.get("talent_rank")
    season = int(row.get("season_year"))

    rank: int | None = None
    if rank_val is not None:
        try:
            rank = int(rank_val)
        except (TypeError, ValueError):
            rank = None
    if rank is None:
        rank = _national_talent_rank(db, season, score)

    tone = ""
    story = "247 composite — multi-year roster talent average."
    if rank is not None:
        if rank <= 10:
            tone, story = "positive", "Elite roster talent. Ceiling assumptions follow."
        elif rank <= 25:
            tone, story = "positive", "Top-25 roster talent. Year-over-year stability."
        elif rank <= 60:
            tone, story = "", "Mid-tier talent base. Coaching/scheme is the differentiator."
        else:
            story = "Outside the talent top 60. The wins must be earned in development."
        headline = f"#{rank} nationally"
    else:
        headline = f"{score:.1f}"

    return _cell(
        eyebrow="Talent Composite",
        headline=headline,
        context=f"{season} cycle · 247 composite {score:.1f}",
        narrative=story,
        tone=tone,
    ), True


def _transfer_cell(db, profile: Profile, team_id: int) -> tuple[str, bool]:
    row = _transfer_activity(db, team_id)
    awaiting = (profile.mascot_voice.get("awaiting_signal", "Awaiting signal.")
                if profile.mascot_voice else "Awaiting signal.")
    if not row:
        return _empty_cell("Transfer Activity", awaiting), False
    incoming = int(row.get("incoming") or 0)
    outgoing = int(row.get("outgoing") or 0)
    season = int(row.get("season_year"))
    net = incoming - outgoing

    if net >= 5:
        tone, story = "positive", "Net positive portal cycle. Roster augmented at need positions."
    elif net >= 0:
        tone, story = "", "Balanced portal cycle. In/out roughly even."
    elif net >= -5:
        tone, story = "", "Mildly negative cycle. Departure outpaced arrivals."
    else:
        tone, story = "warning", "Heavy outflow cycle. Roster reset under way."

    sign = "+" if net > 0 else ""
    return _cell(
        eyebrow="Transfer Activity",
        headline=f"{sign}{net} net",
        context=f"{season} cycle · in {incoming} / out {outgoing}",
        narrative=story,
        tone=tone,
    ), True


# ---------------------------------------------------------------------------
# Public render
# ---------------------------------------------------------------------------

def render_offseason_pulse(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    team_id = int(snapshot.team_id)

    cells: list[str] = []
    signals = 0

    rec_html, rec_ok = _recruiting_cell(db, profile, team_id)
    cells.append(rec_html)
    signals += 1 if rec_ok else 0

    ret_html, ret_ok = _returning_cell(db, profile, team_id)
    cells.append(ret_html)
    signals += 1 if ret_ok else 0

    tal_html, tal_ok = _talent_cell(db, profile, team_id)
    cells.append(tal_html)
    signals += 1 if tal_ok else 0

    trn_html, trn_ok = _transfer_cell(db, profile, team_id)
    cells.append(trn_html)
    signals += 1 if trn_ok else 0

    if signals < 2:
        # Not enough signal to surface the module.
        return ""

    program = escape(profile.program_name)
    return f"""
<section class="offseason-pulse" aria-labelledby="offseason-pulse-h"
         data-module="offseason-pulse" data-state="ready" data-signal-count="{signals}">
  <div class="offseason-pulse__header">
    <h2 id="offseason-pulse-h" class="offseason-pulse__title">Offseason Pulse · {program}</h2>
    <span class="offseason-pulse__cycle">Roster · Recruiting · Portal</span>
  </div>
  <div class="offseason-pulse__grid">
    {''.join(cells)}
  </div>
</section>"""


__all__ = ["render_offseason_pulse", "OFFSEASON_PULSE_CSS"]
