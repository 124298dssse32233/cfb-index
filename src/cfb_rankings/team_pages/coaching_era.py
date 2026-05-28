"""Coaching Era Strip chip — surfaces the current head coach + their tenure
length + the previous head coach + the most-recent coaching transition.

Sources from `team_seasons.head_coach` (populated by CFBD /coaches ingest).
Audit T28 fragment / Brief §6.5 ("coaching era strip").

Falls back to "Awaiting Signal" when head_coach is null for the current
season. Otherwise renders the coach name + tenure start year + previous
coach with their tenure window.

Public API:
    render_coaching_era_strip(db, profile, snapshot) -> str
    COACHING_ERA_STRIP_CSS                           -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


COACHING_ERA_STRIP_CSS = """
/* Coaching Era Strip chip */
.coaching-era {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px 22px;
  align-items: center;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-secondary, var(--accent-primary, #c9a24a));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.coaching-era__head { display: grid; gap: 4px; }
.coaching-era__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.coaching-era__name {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.4vw + 10px, 30px);
  font-weight: 400;
  letter-spacing: 0.02em;
  line-height: 1;
  color: var(--fg-primary);
  margin: 0;
}
.coaching-era__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 56ch;
}
.coaching-era__chips {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  flex-wrap: wrap;
}
.coaching-era__chip {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  color: var(--fg-secondary);
}
.coaching-era__chip--era {
  color: var(--accent-primary, #c9a24a);
  border-color: rgba(201, 162, 74, 0.35);
}
.coaching-era__era-link {
  display: inline-block;
  margin-top: 10px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--accent-primary, #c9a24a);
  text-decoration: none;
}
.coaching-era__era-link:hover { text-decoration: underline; }
.coaching-era__tenure {
  display: grid;
  gap: 4px;
  text-align: right;
}
.coaching-era__tenure-years {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(28px, 2vw + 10px, 40px);
  line-height: 1;
  color: var(--accent-primary, #c9a24a);
}
.coaching-era__tenure-label {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--fg-muted);
  text-transform: uppercase;
}
@media (max-width: 640px) {
  .coaching-era { grid-template-columns: 1fr; }
  .coaching-era__tenure { text-align: left; }
}
"""


def _fetch_coach_tenure(db, team_id: int) -> list[dict[str, Any]]:
    """Returns ordered list of (season_year, head_coach) descending."""
    rows = db.query_all(
        """
        select season_year, head_coach
          from team_seasons
         where team_id = :tid and head_coach is not null
         order by season_year desc
        """,
        {"tid": team_id},
    )
    return rows


def render_coaching_era_strip(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    rows = _fetch_coach_tenure(db, int(snapshot.team_id))
    if not rows:
        return ""

    # The first row is most recent year + coach. Walk back to find tenure start.
    current_coach = rows[0].get("head_coach")
    current_year = int(rows[0].get("season_year"))

    tenure_start = current_year
    for r in rows[1:]:
        if r.get("head_coach") == current_coach:
            tenure_start = int(r.get("season_year"))
        else:
            break

    tenure_years = current_year - tenure_start + 1

    # Find previous coach
    previous_coach = None
    previous_end = None
    previous_start = None
    for r in rows:
        coach = r.get("head_coach")
        year = int(r.get("season_year"))
        if coach != current_coach:
            if previous_coach is None:
                previous_coach = coach
                previous_end = year
                previous_start = year
            elif coach == previous_coach:
                previous_start = year
            else:
                break

    if tenure_years == 1:
        if previous_coach:
            story = (
                f"{escape(current_coach)} took over from {escape(previous_coach)} "
                f"for the {current_year} season."
            )
        else:
            story = f"{escape(current_coach)}'s first year — new era under way."
    elif tenure_years <= 3:
        story = (
            f"{escape(current_coach)} in year {tenure_years} of the rebuild. "
            f"The methodology is taking shape."
        )
    elif tenure_years <= 7:
        story = (
            f"{escape(current_coach)} has held the program for {tenure_years} seasons — "
            "the era is established."
        )
    else:
        story = (
            f"{escape(current_coach)} into year {tenure_years} — a multi-decade era "
            "by modern CFB standards."
        )

    chips: list[str] = [
        f'<span class="coaching-era__chip coaching-era__chip--era">'
        f'Era {escape(current_coach)} · {tenure_start}–present</span>'
    ]
    if previous_coach and previous_start:
        if previous_start == previous_end:
            window = str(previous_end)
        else:
            window = f"{previous_start}–{previous_end}"
        chips.append(
            f'<span class="coaching-era__chip">Prev: {escape(previous_coach)} '
            f'({escape(window)})</span>'
        )

    chips_html = "".join(chips)

    # Crosslink to the full CFP-era page when the program qualifies (>= MIN_SEASONS).
    era_link = ""
    try:
        from cfb_rankings.era_pages import era_page_available, era_page_relpath
        if era_page_available(db, int(snapshot.team_id)):
            era_link = (
                f'<a class="coaching-era__era-link" '
                f'href="/{era_page_relpath(profile.slug)}">'
                f"The full CFP-era story &rarr;</a>"
            )
    except Exception:
        era_link = ""

    program = escape(profile.program_name)
    return f"""
<section class="coaching-era" aria-labelledby="coaching-era-h"
         data-module="coaching-era" data-state="ready" data-tenure-years="{tenure_years}">
  <div class="coaching-era__head">
    <p class="coaching-era__eyebrow">Coaching Era · {program}</p>
    <h2 id="coaching-era-h" class="coaching-era__name">{escape(current_coach)}</h2>
    <p class="coaching-era__story">{story}</p>
    <div class="coaching-era__chips">{chips_html}</div>
    {era_link}
  </div>
  <div class="coaching-era__tenure">
    <span class="coaching-era__tenure-years">{tenure_years}</span>
    <span class="coaching-era__tenure-label">{'year' if tenure_years == 1 else 'years'} · era</span>
  </div>
</section>"""


__all__ = ["render_coaching_era_strip", "COACHING_ERA_STRIP_CSS"]
