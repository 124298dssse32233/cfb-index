"""Page Tone Strip — Brief Part III §32 (Seasonal Sentience visible layer).

The state_resolver computes accent_key, anchor_variant, season_phase,
and copy_tone every render. Until now none of those signals SHOWED on
the page — every team page looked the same in May and on a Saturday.

This module surfaces the seasonal-sentience state as a compact pill
strip right under the hero. The page literally says what mode it's in:

    OFFSEASON · DEAD PERIOD · HERITAGE MODE          ← May/June
    MEDIA DAYS · RESET                                ← July
    CAMP · COILED · WEEK 0 IN T-MINUS N               ← August
    EARLY SEASON · ANTICIPATION · FRIDAY              ← Sept Friday
    STAKES RISING · MATCHUP SHARPENS · WEDNESDAY      ← mid-Oct Wed
    RIVALRY PEAK · HYPE PEAKS · THURSDAY              ← rivalry week
    GAMEDAY · 14:00 KICK                              ← Saturday
    AUTOPSY · LICKING WOUNDS                          ← post-loss
    BASKING                                            ← post-win
    BOWL SEASON · CARROUSEL · POST-FINAL              ← Dec/Jan
    CFP SELECTION                                     ← early Dec

Brief verbatim (§32):

    "The page should feel different in May than it does on a Saturday.
     A team page in November rivalry week is not the same product as a
     team page in March. Seasonal sentience is the system that makes
     this difference visible — not just to the model, but to the eye."

Public API:
    render_page_tone_strip(state) -> str
    PAGE_TONE_STRIP_CSS           -> str
"""
from __future__ import annotations

from html import escape

from .state_resolver import PageState


# ---------------------------------------------------------------------------
# Phase / tone → readable label.
# ---------------------------------------------------------------------------

PHASE_LABELS: dict[str, str] = {
    "bowl-and-carousel":         "Bowl Season",
    "nsd-and-portal":            "Signing Day · Portal",
    "spring-and-portal":         "Spring · Portal",
    "dead-period-heritage":      "Dead Period",
    "media-days":                "Media Days",
    "camp":                      "Fall Camp",
    "early-season":              "Early Season",
    "stakes-rising":             "Stakes Rising",
    "rivalry-peak":              "Rivalry Peak",
    "cfp-selection-and-bowl":    "CFP Selection",
}

DOW_LABELS: dict[str, str] = {
    "licking-wounds-or-basking": "Monday",
    "depth-chart-injuries":      "Tuesday",
    "matchup-sharpens":          "Wednesday",
    "hype-peaks":                "Thursday",
    "anticipation":              "Friday",
    "gameday":                   "Gameday",
    "autopsy":                   "Sunday",
}

TONE_LABELS: dict[str, str] = {
    "basking":     "Basking",
    "reckoning":   "Reckoning",
    "patient":     "Patient",
    "coiled":      "Coiled",
    "resolute":    "Resolute",
    "anticipation":"Anticipation",
    "ritualistic": "Ritualistic",
    "heritage":    "Heritage Mode",
    "moment":      "A Moment",
    "diagnostic":  "Diagnostic",
    "hype":        "Hype",
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

PAGE_TONE_STRIP_CSS = """
/* Page Tone Strip — Brief Part III §32. Makes seasonal sentience visible.
 *
 * The body carries data-page-tone (accent_key) + data-page-phase + data-page-anchor
 * so downstream CSS can react. This strip is the explicit visible signal.
 */

.page-tone-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
  padding: 8px clamp(12px, 1.5vw, 18px);
  margin: 0 0 clamp(12px, 2vw, 20px) 0;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, #c9a24a);
  border-radius: 8px;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.page-tone-strip__chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.page-tone-strip__chip + .page-tone-strip__chip::before {
  content: "·";
  margin-right: 4px;
  opacity: 0.4;
}
.page-tone-strip__chip--accent {
  color: var(--accent-primary, #c9a24a);
}
.page-tone-strip__chip--live {
  color: var(--accent-secondary, var(--accent-primary, #c9a24a));
}
.page-tone-strip__pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-secondary, var(--accent-primary, #c9a24a));
  display: inline-block;
  margin-right: 6px;
  animation: page-tone-pulse 2s ease-in-out infinite;
}
@keyframes page-tone-pulse {
  0%, 100% { opacity: 0.45; transform: scale(1.0); }
  50%      { opacity: 1.0;  transform: scale(1.25); }
}

/* Tone-keyed accents — modulates the strip border-left and live dot. */
body[data-page-tone="red"]    .page-tone-strip { border-left-color: #d94747; }
body[data-page-tone="amber"]  .page-tone-strip { border-left-color: #c98c1a; }
body[data-page-tone="green"]  .page-tone-strip { border-left-color: #2c8f5a; }
body[data-page-tone="navy"]   .page-tone-strip { border-left-color: #2e4d8a; }
body[data-page-tone="coral"]  .page-tone-strip { border-left-color: #e07060; }
body[data-page-tone="gray"]   .page-tone-strip { border-left-color: rgba(255,255,255,0.25); }

/* Sentience-driven background tint on the whole page, very subtle. */
body[data-page-tone="amber"] { background-image: radial-gradient(circle at 12% -10%, rgba(201, 140, 26, 0.05), transparent 35%); }
body[data-page-tone="green"] { background-image: radial-gradient(circle at 88% -10%, rgba(44, 143, 90, 0.04), transparent 35%); }
body[data-page-tone="red"]   { background-image: radial-gradient(circle at 50% -10%, rgba(217, 71, 71, 0.05), transparent 35%); }
body[data-page-tone="navy"]  { background-image: radial-gradient(circle at 50% -10%, rgba(46, 77, 138, 0.04), transparent 40%); }

@media (max-width: 540px) {
  .page-tone-strip {
    font-size: 10px;
    letter-spacing: 0.10em;
  }
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _outcome_label(state: PageState) -> str | None:
    if not state.outcome_category:
        return None
    return {
        "win-clear":    "Post-win — basking",
        "win-upset":    "Upset win — Moment",
        "loss-close":   "Post-loss — reckoning",
        "loss-blowout": "Post-loss — diagnostic",
        "loss-upset":   "Upset loss — fracture risk",
    }.get(state.outcome_category)


def _live_chip(state: PageState) -> str | None:
    """If a game finalized within last 24h or one is happening today, surface it."""
    if state.game_recap_active:
        return "Game Recap Mode"
    if state.hours_since_final is not None and state.hours_since_final < 24:
        return f"Just played · {int(state.hours_since_final)}h ago"
    if state.day_of_week_label == "gameday" and state.is_in_season:
        return "Gameday"
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_page_tone_strip(state: PageState) -> str:
    """Render the Page Tone Strip (seasonal-sentience visible layer)."""
    chips: list[tuple[str, str]] = []

    # Phase chip
    phase_label = PHASE_LABELS.get(state.season_phase, state.season_phase.replace("-", " ").title())
    chips.append(("page-tone-strip__chip page-tone-strip__chip--accent", phase_label))

    # In-season vs offseason explicit
    if not state.is_in_season:
        chips.append(("page-tone-strip__chip", "Offseason"))

    # Day-of-week (only in-season)
    if state.is_in_season:
        dow = DOW_LABELS.get(state.day_of_week_label, "")
        if dow:
            chips.append(("page-tone-strip__chip", dow))

    # Tone chip
    tone_label = TONE_LABELS.get(state.copy_tone, state.copy_tone.title() if state.copy_tone else "")
    if tone_label:
        chips.append(("page-tone-strip__chip", tone_label))

    # Outcome chip (post-game)
    outcome_label = _outcome_label(state)
    if outcome_label:
        chips.append(("page-tone-strip__chip page-tone-strip__chip--live", outcome_label))

    # Live/recap chip
    live_label = _live_chip(state)
    if live_label and not outcome_label:
        chips.append((
            "page-tone-strip__chip page-tone-strip__chip--live",
            f'<span class="page-tone-strip__pulse" aria-hidden="true"></span>{escape(live_label)}',
        ))

    # Rivalry chip
    if state.rivalry_this_week and state.is_in_season:
        opp = state.rivalry_this_week.get("opponent_name") or state.rivalry_this_week.get("rival_slug") or ""
        if opp:
            chips.append((
                "page-tone-strip__chip page-tone-strip__chip--live",
                f"Rivalry Week vs {escape(str(opp))}",
            ))
        else:
            chips.append(("page-tone-strip__chip page-tone-strip__chip--live", "Rivalry Week"))

    chip_html = "".join(
        f'<span class="{cls}">{label}</span>'
        for cls, label in chips
    )

    return (
        '<section class="page-tone-strip" role="status" aria-live="polite" '
        f'aria-label="Page mode for {escape(state.season_phase)}" '
        f'data-tone="{escape(state.accent_key)}" '
        f'data-anchor="{escape(state.anchor_variant)}">'
        f'{chip_html}'
        '</section>'
    )


__all__ = [
    "render_page_tone_strip",
    "PAGE_TONE_STRIP_CSS",
    "PHASE_LABELS",
    "DOW_LABELS",
    "TONE_LABELS",
]
