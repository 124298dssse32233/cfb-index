"""Wrapped stack — Brief §21.3.

Spotify-Wrapped-styled retrospective per team. Drops post-bowl-Monday
as a synchronized communal moment across all 130 programs.

Brief verbatim (§21.3):

    "Post-bowl-Monday drop: 8-card vertical stack per team, Spotify-
     Wrapped-styled. Content per card:
       1. Biggest win (opponent + score + 1-line why it mattered)
       2. Heartbreak loss
       3. Breakout player
       4. Ranking trajectory (mini-sparkline)
       5. Rivalry result
       6. Recruiting class rank change
       7. Deep-cut stat (team-specific)
       8. Forward-looking 'next season' card

     Shareable individually or as a stack. Simultaneous drop across
     all 130 teams creates the communal moment."

Implementation: 6 cards computable from existing data right now. The
other 2 (Breakout player, Recruiting class rank change) need data we
don't surface to the team-page renderer today — they're stubbed for
filling in later.

The whole stack only renders during the "Wrapped window" — bowl-week
through spring (Jan-Mar). Outside that window the module returns
empty so it doesn't clutter the August page.

Public API:
    render_wrapped_stack(profile, snapshot, arc_rows, today) -> str
    WRAPPED_STACK_CSS                                          -> str
"""
from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot, GameResult


WRAPPED_STACK_CSS = """
/* Wrapped stack — Brief §21.3
 * Vertical card stack, each card claims its own viewport vibe.
 */
.wrapped-stack {
  display: grid;
  gap: clamp(10px, 1.4vw, 18px);
  padding: clamp(18px, 2.4vw, 28px) clamp(18px, 2.6vw, 32px);
  background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.0));
  border: 1px solid var(--stroke-default, rgba(255,255,255,0.10));
  border-radius: 16px;
  margin-bottom: clamp(20px, 3vw, 32px);
}
.wrapped-stack__header {
  display: grid;
  gap: 4px;
}
.wrapped-stack__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.wrapped-stack__title {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(28px, 2.5vw + 12px, 42px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.wrapped-stack__cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: clamp(8px, 1.2vw, 14px);
}
.wrapped-stack__card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, #c9a24a);
  border-radius: 10px;
}
.wrapped-stack__card[data-card-kind="win"]       { border-left-color: #2c8f5a; }
.wrapped-stack__card[data-card-kind="loss"]      { border-left-color: #c95151; }
.wrapped-stack__card[data-card-kind="rivalry"]   { border-left-color: #c98c1a; }
.wrapped-stack__card[data-card-kind="trajectory"]{ border-left-color: var(--accent-secondary, var(--accent-primary, #c9a24a)); }
.wrapped-stack__card[data-card-kind="forward"]   { border-left-color: #5a7fc9; }
.wrapped-stack__card-kind {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.wrapped-stack__card-headline {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(18px, 1.2vw + 8px, 22px);
  font-weight: 400;
  line-height: 1.05;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
}
.wrapped-stack__card-story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.45;
  color: var(--fg-secondary);
}
"""


# ---------------------------------------------------------------------------
# Window check
# ---------------------------------------------------------------------------

def _is_wrapped_window(today: date) -> bool:
    """The brief drop window is post-bowl-Monday through spring.

    Rough heuristic: Jan-Mar (after CFP final ≈ Jan 13-20).
    """
    return today.month in (1, 2, 3)


# ---------------------------------------------------------------------------
# Card builders
# ---------------------------------------------------------------------------

def _biggest_win(games: list[GameResult]) -> dict[str, str] | None:
    wins = [g for g in games if g.outcome == "W" and g.margin is not None]
    if not wins:
        return None
    g = max(wins, key=lambda g: g.margin or 0)
    loc = "vs" if g.is_home else "at"
    return {
        "kind": "win",
        "label": "Biggest Win",
        "headline": f"{g.team_points}-{g.opp_points} {loc} {g.opponent_name}",
        "story": (
            f"Week {g.week} of {g.season_year}. Margin of {g.margin}. "
            "The result that became the season's screenshot."
        ),
    }


def _heartbreak_loss(games: list[GameResult]) -> dict[str, str] | None:
    losses = [g for g in games if g.outcome == "L" and g.margin is not None]
    if not losses:
        return None
    # Closest loss is the heartbreak.
    g = max(losses, key=lambda g: g.margin or -1000)  # margin is negative for losses; max → closest
    loc = "vs" if g.is_home else "at"
    return {
        "kind": "loss",
        "label": "Heartbreak Loss",
        "headline": f"{g.team_points}-{g.opp_points} {loc} {g.opponent_name}",
        "story": (
            f"Week {g.week} of {g.season_year}. Lost by {-(g.margin or 0)}. "
            "The one that lingered."
        ),
    }


def _trajectory_card(snapshot: TeamSnapshot, arc_rows: list[dict[str, Any]]) -> dict[str, str] | None:
    if not arc_rows:
        return None
    # Compare end-of-season AP rank to prior season.
    sorted_rows = sorted(arc_rows, key=lambda r: int(r.get("season_year") or 0))
    if len(sorted_rows) < 2:
        return None
    last = sorted_rows[-1]
    prior = sorted_rows[-2]
    last_ap = last.get("ap_rank_final")
    prior_ap = prior.get("ap_rank_final")
    if last_ap is None and prior_ap is None:
        return None
    last_w = int(last.get("wins") or 0)
    prior_w = int(prior.get("wins") or 0)
    delta_w = last_w - prior_w
    if last_ap is not None and prior_ap is not None:
        delta_ap = int(prior_ap) - int(last_ap)
        direction = "climbed" if delta_ap > 0 else ("slipped" if delta_ap < 0 else "held")
        story = (
            f"Finished AP #{int(last_ap)} after entering at AP #{int(prior_ap)} — "
            f"{direction} {abs(delta_ap)} {'spot' if abs(delta_ap)==1 else 'spots'}."
        )
        headline = f"AP #{int(last_ap)}"
    else:
        story = f"Finished {last_w}-{int(last.get('losses') or 0)} ({delta_w:+d} wins YoY)."
        headline = f"{last_w}-{int(last.get('losses') or 0)}"
    return {
        "kind": "trajectory",
        "label": "Trajectory",
        "headline": headline,
        "story": story,
    }


def _rivalry_card(profile: Profile, games: list[GameResult]) -> dict[str, str] | None:
    riv_list = profile.rivalries or []
    riv_slugs = {(r.get("rival_slug") or r.get("slug") or "").lower() for r in riv_list}
    if not riv_slugs:
        return None
    matches = [g for g in games if (g.opponent_slug or "").lower() in riv_slugs and g.outcome in ("W", "L")]
    if not matches:
        return None
    # Most recent rivalry game wins.
    g = matches[-1]
    loc = "vs" if g.is_home else "at"
    if g.outcome == "W":
        story = f"Beat {g.opponent_name} {g.team_points}-{g.opp_points}{' on the road' if not g.is_home else ' at home'}. The trophy stayed."
    else:
        story = f"Lost to {g.opponent_name} {g.team_points}-{g.opp_points}{' on the road' if not g.is_home else ' at home'}. The 12-month wait begins."
    return {
        "kind": "rivalry",
        "label": "The Rivalry",
        "headline": f"{g.outcome} {g.team_points}-{g.opp_points} {loc} {g.opponent_name}",
        "story": story,
    }


def _deep_cut_card(snapshot: TeamSnapshot) -> dict[str, str] | None:
    """A team-specific deep-cut stat. With limited data we surface
    final-record + best-margin context as the deep-cut."""
    wins = int(snapshot.wins or 0)
    losses = int(snapshot.losses or 0)
    if wins + losses == 0:
        return None
    win_pct = wins / (wins + losses)
    return {
        "kind": "trajectory",
        "label": "Deep Cut",
        "headline": f"{wins}-{losses}",
        "story": (
            f"Finished the year at {win_pct:.1%}. "
            f"The shape of the season hides under the record — "
            f"weekly mood and resume math live in the Pulse."
        ),
    }


def _forward_card(profile: Profile, snapshot: TeamSnapshot) -> dict[str, str]:
    program = profile.program_name
    mantra = profile.mantra or "On to next year."
    return {
        "kind": "forward",
        "label": "Next Season",
        "headline": "The Page Turns",
        "story": (
            f"{program}'s {int(snapshot.season_year) + 1} season starts the clock. "
            f"The schedule lands in May, fall camp opens in August, kickoff lands "
            f"late August. {mantra}"
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_wrapped_stack(
    profile: Profile,
    snapshot: TeamSnapshot,
    arc_rows: list[dict[str, Any]] | None = None,
    today: date | None = None,
) -> str:
    """Render the Wrapped stack when in-window (Jan-Mar)."""
    today = today or date.today()
    if not _is_wrapped_window(today):
        return ""

    games = snapshot.recent_games or []
    cards: list[dict[str, str]] = []

    for builder in (
        lambda: _biggest_win(games),
        lambda: _heartbreak_loss(games),
        lambda: _trajectory_card(snapshot, arc_rows or []),
        lambda: _rivalry_card(profile, games),
        lambda: _deep_cut_card(snapshot),
    ):
        c = builder()
        if c:
            cards.append(c)
    # Forward card always renders — it's the page turn.
    cards.append(_forward_card(profile, snapshot))

    if len(cards) < 3:
        # Not enough material to make a stack feel like a stack.
        return ""

    cards_html: list[str] = []
    for c in cards:
        cards_html.append(
            f'<div class="wrapped-stack__card" data-card-kind="{escape(c["kind"])}">'
            f'<span class="wrapped-stack__card-kind">{escape(c["label"])}</span>'
            f'<span class="wrapped-stack__card-headline">{escape(c["headline"])}</span>'
            f'<span class="wrapped-stack__card-story">{escape(c["story"])}</span>'
            '</div>'
        )

    program = escape(profile.program_name)
    return f"""
<section class="wrapped-stack" aria-labelledby="wrapped-stack-h"
         data-module="wrapped-stack" data-state="ready">
  <div class="wrapped-stack__header">
    <p class="wrapped-stack__eyebrow">{program} · {snapshot.season_year} Wrapped</p>
    <h2 id="wrapped-stack-h" class="wrapped-stack__title">The Year in {len(cards)} Cards</h2>
  </div>
  <div class="wrapped-stack__cards" role="list">
    {''.join(cards_html)}
  </div>
</section>"""


__all__ = ["render_wrapped_stack", "WRAPPED_STACK_CSS"]
