"""Kickoff Countdown — Brief Part II §22.1 (offseason variant).

The brief's full Kickoff Check-In is a live ritual: a 15-minute
window at kickoff where fans tap "I'm watching." That requires
server state — out of scope for a static-site build.

This is the cousin module the brief opens with: a count-down to
the next kickoff that ALWAYS renders. It serves three states:

  OFFSEASON   → "247 days until kickoff. Season opens Aug 29."
  PRE-SEASON  → "12 days. vs Notre Dame. Saturday."
  GAME-WEEK   → "3 days · 18 hours. vs Michigan. Saturday 12:00 ET."
  GAMEDAY     → "Kickoff in 4 hours. vs Texas."
  LIVE        → "Live now."

The chip becomes a tiny universally-shared communal moment:
every team's page anchors itself in calendar time.

Data sources:
  - snapshot.next_game.start_time_utc when known.
  - Falls back to "Aug 30, current year" if the team has no
    scheduled next game.

Public API:
    render_kickoff_countdown(snapshot, today) -> str
    KICKOFF_COUNTDOWN_CSS                      -> str
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from html import escape

from .data import TeamSnapshot, GameResult


KICKOFF_COUNTDOWN_CSS = """
/* Kickoff Countdown — Brief Part II §22.1
 * One-line presence chip that anchors every team page in calendar time.
 */

.kickoff-countdown {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 14px;
  padding: 10px clamp(14px, 1.8vw, 18px);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, #c9a24a);
  border-radius: 10px;
  margin-bottom: clamp(16px, 2vw, 24px);
  font-variant-numeric: tabular-nums;
}
.kickoff-countdown__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.kickoff-countdown__number {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(24px, 2.0vw + 10px, 32px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--accent-primary, #c9a24a);
  margin: 0;
}
.kickoff-countdown__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  color: var(--fg-secondary);
  margin: 0;
}
.kickoff-countdown--live {
  border-left-color: #d94747;
}
.kickoff-countdown--live .kickoff-countdown__number {
  color: #d94747;
  animation: kickoff-live-pulse 1.4s ease-in-out infinite;
}
@keyframes kickoff-live-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.55; }
}
.kickoff-countdown--gameday  { border-left-color: #c98c1a; }
.kickoff-countdown--gameweek { border-left-color: #2c8f5a; }
.kickoff-countdown--offseason {
  border-left-color: rgba(255, 255, 255, 0.18);
}
.kickoff-countdown--offseason .kickoff-countdown__number {
  color: var(--fg-secondary);
}
"""


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    # Tolerate "2026-08-30 19:30:00" and "2026-08-30T19:30:00Z" and "...+00:00"
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.fromisoformat(s.replace(" ", "T").replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_delta(seconds: float) -> tuple[str, str]:
    """Return (big_number, story_qualifier) for the given remaining seconds."""
    seconds = max(0.0, seconds)
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days >= 7:
        return (f"{days} days", "until kickoff")
    if days >= 1:
        return (f"{days}d {hours}h", "until kickoff")
    if hours >= 1:
        return (f"{hours}h {minutes:02d}m", "until kickoff")
    if minutes >= 1:
        return (f"{minutes} min", "until kickoff")
    return ("Live now", "")


def _default_season_opener(today: date) -> datetime:
    """Approximate season-opener date for current cycle.

    CFB Week 0 typically falls on the final Saturday of August. If today
    is past Aug 31, default to next year's Aug 30.
    """
    year = today.year
    if today.month >= 9 or (today.month == 8 and today.day >= 31):
        year += 1
    # Aug 30 anchor — close enough as default; real games override this.
    return datetime(year, 8, 30, 17, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_kickoff_countdown(
    snapshot: TeamSnapshot | None,
    today: date | None = None,
) -> str:
    """Render the Kickoff Countdown chip (Brief §22.1 offseason variant)."""
    now = datetime.now(timezone.utc) if today is None else datetime.combine(
        today, datetime.min.time(), tzinfo=timezone.utc
    )

    next_game: GameResult | None = snapshot.next_game if snapshot else None
    kickoff_dt: datetime | None = None
    opponent_name: str | None = None
    is_home: bool | None = None
    if next_game is not None:
        kickoff_dt = _parse_iso(next_game.start_time_utc)
        opponent_name = next_game.opponent_name
        is_home = next_game.is_home

    if kickoff_dt is None:
        # Offseason fallback — use approximate season opener.
        kickoff_dt = _default_season_opener(now.date())
        opponent_name = None
        is_home = None

    delta = (kickoff_dt - now).total_seconds()
    big, qualifier = _format_delta(delta)

    # Mode classification + variant CSS class
    if delta <= 0:
        mode = "live"
        mode_label = "LIVE"
    elif delta < 6 * 3600:
        mode = "gameday"
        mode_label = "Gameday"
    elif delta < 14 * 86400:
        mode = "gameweek"
        mode_label = "Game Week"
    elif delta < 60 * 86400:
        mode = "preseason"
        mode_label = "Approaching"
    else:
        mode = "offseason"
        mode_label = "Offseason"

    story_parts: list[str] = []
    if opponent_name:
        loc = "vs" if is_home else "at"
        story_parts.append(f"{loc} {opponent_name}")
    # Render a UTC wall-clock reference; client-side JS can localize later.
    # Avoid %-d / %#d portability issues by formatting day as int.
    kickoff_label = (
        f"{kickoff_dt.strftime('%a %b')} {kickoff_dt.day} · "
        f"{kickoff_dt.strftime('%H:%M')} UTC"
    )
    story_parts.append(kickoff_label)
    story = " · ".join(story_parts)

    return (
        f'<section class="kickoff-countdown kickoff-countdown--{mode}" '
        'role="status" aria-live="polite" '
        f'data-module="kickoff-countdown" data-mode="{mode}" '
        f'data-kickoff-utc="{kickoff_dt.isoformat()}">'
        f'<p class="kickoff-countdown__eyebrow">{escape(mode_label)}</p>'
        f'<p class="kickoff-countdown__number">{escape(big)}</p>'
        + (f'<p class="kickoff-countdown__story">{escape(qualifier)} · {escape(story)}</p>'
           if qualifier else
           f'<p class="kickoff-countdown__story">{escape(story)}</p>')
        + '</section>'
    )


__all__ = [
    "render_kickoff_countdown",
    "KICKOFF_COUNTDOWN_CSS",
]
