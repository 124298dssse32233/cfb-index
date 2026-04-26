"""Edition theme resolver.

Given a publish_date and (optionally) a fan-intel signal context, picks the
edition's theme_title, theme_dek, and cover_viz_kind. For seeded editions
(2026-w14..w17) the resolver returns hardcoded curated themes — these were
authored as part of Sprint 9 to ground the framework with high-quality
content. For unseeded future dates, the resolver falls back to a calendar-
phase + signal-driven heuristic.

Calendar phases (from CONFERENCE_PULSE_OFFSEASON_PLAYBOOK.md):
    Apr early   — spring-game season
    Apr mid     — portal window 2 / draft prep
    Apr late    — post-draft reset
    May–Jun     — recruiting + summer-quiet
    Jul         — media-day buildup
    Aug         — preseason ignition
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ThemeChoice:
    theme_title: str
    theme_dek: str
    cover_viz_kind: str


# Hand-curated themes for the four seeded editions. Each dek is 24-32 words,
# fan-voice register, italic-displayable. Each viz_kind is selected to match
# the editorial subject of the cover essay.
SEEDED_THEMES: dict[str, ThemeChoice] = {
    "2026-w14": ThemeChoice(
        theme_title="The Spring-Game Issue",
        theme_dek=(
            "Eight stadiums opened their gates in April. The fans who showed up "
            "told us more about where this season points than any depth chart will."
        ),
        cover_viz_kind="heatmap",
    ),
    "2026-w15": ThemeChoice(
        theme_title="Portal Two, Quietly",
        theme_dek=(
            "The second window closed on a Wednesday. Nobody noticed because the "
            "draft was Thursday — but the rosters that won the spring just got rewritten."
        ),
        cover_viz_kind="flow",
    ),
    "2026-w16": ThemeChoice(
        theme_title="The Post-Draft Reset",
        theme_dek=(
            "Twenty-three first-round picks left college football in 72 hours. "
            "What got drafted was the last residue of the playoff-era roster build."
        ),
        cover_viz_kind="rank_shift",
    ),
    "2026-w17": ThemeChoice(
        theme_title="After the Bracket",
        theme_dek=(
            "The first 12-team field is in the books. Every program now lives "
            "inside one of three conversations — and the gap between them is the "
            "story of the offseason."
        ),
        cover_viz_kind="gap",
    ),
}


def resolve_theme(edition_slug: str, publish_date: date | None = None) -> ThemeChoice:
    """Return the theme for ``edition_slug``. Falls back to a calendar-phase
    heuristic when the slug is not in the seeded set."""
    if edition_slug in SEEDED_THEMES:
        return SEEDED_THEMES[edition_slug]
    if publish_date is None:
        # Default to the most recent seeded theme as a safe fallback.
        return SEEDED_THEMES["2026-w17"]
    return _calendar_fallback(publish_date)


def _calendar_fallback(d: date) -> ThemeChoice:
    month = d.month
    if month == 4 and d.day <= 7:
        return ThemeChoice(
            theme_title="Spring Reports",
            theme_dek=(
                "Practice opened in 134 places this month. The signals come "
                "out scattered — we sort the ones that actually moved a needle."
            ),
            cover_viz_kind="distribution",
        )
    if month in (5, 6):
        return ThemeChoice(
            theme_title="The Quiet Months",
            theme_dek=(
                "Nothing happens in May. Which is why everything that does "
                "happen in May means more than it should."
            ),
            cover_viz_kind="field",
        )
    if month == 7:
        return ThemeChoice(
            theme_title="Media-Day Tells",
            theme_dek=(
                "Coaches say more in 60 seconds at the lectern than they will "
                "across an entire November. We read what they didn't say."
            ),
            cover_viz_kind="drift",
        )
    if month == 8:
        return ThemeChoice(
            theme_title="Ignition",
            theme_dek=(
                "Twelve weeks of preseason talk land on Saturday. The gap "
                "between the talk and the first kickoff is the only honest measure."
            ),
            cover_viz_kind="gap",
        )
    return ThemeChoice(
        theme_title="The Offseason Issue",
        theme_dek=(
            "Conversation hasn't stopped since January. We sort what's "
            "moving the room from what's filling time."
        ),
        cover_viz_kind="gap",
    )
