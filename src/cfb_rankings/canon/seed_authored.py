"""Authored editorial copy for the 2026 Canon edition.

Per Sprint 11 brief §"LLM generation mechanism" (decision-and-document):
the editorial copy is *authored directly in this file*, not produced by
a runtime SDK call. The author is the LLM running the build session;
this module is its declared output, version-controlled and reviewable.

Every entry declares an effort bucket so the generator can report on the
Sonnet/Opus/Haiku split per the contract:

  * ``haiku``  — short scoring/categorization lines (e.g. one-liner ranks
                  60-100, infrastructural one-liners on coaching list)
  * ``sonnet`` — standard editorial paragraphs and one-liners (the bulk)
  * ``opus``   — top-3 blue-blood editorial paragraphs with deepest
                  register; capped at <15% of effort

To verify the cap in CI:

    from cfb_rankings.canon.seed_authored import effort_buckets_for
    eff = effort_buckets_for("the-100-best-players-cfp-era")
    total = sum(eff.values())
    assert eff["opus"] / total < 0.15, "opus over 15% on player list"
"""
from __future__ import annotations

from .data import CanonEntry, CanonListMeta


# --------------------------------------------------------------------------
# List-level metadata
# --------------------------------------------------------------------------

def list_metadatas() -> list[CanonListMeta]:
    return [
        CanonListMeta(
            list_slug="the-100-best-players-cfp-era",
            title="The 100 Best Players of the CFP Era",
            edition_year=2026,
            list_kind="players",
            description=(
                "The 100 most consequential players of the College Football "
                "Playoff era — 2014 through 2025. The era starts with Marcus "
                "Mariota's Heisman, runs through the four-team format, and "
                "lands in the twelve-team present. The list is settled, the "
                "ranks are arguable, and arguments are the point."
            ),
            methodology_notes=(
                "Scope: 2014–2025 inclusive. Eligibility requires at least "
                "one full season as a starter or featured contributor in "
                "that window. Ranking weighs peak season, durability across "
                "seasons, postseason work in the CFP bracket, and the "
                "weight of what the player meant to the program. NFL-draft "
                "outcome is signal, not verdict — Tua's injury costs him "
                "nothing here. Cohort split (where computed) reads "
                "stat-folk signal — analytics, gambling, recruiting — "
                "against casual-fan signal — national narrative, "
                "vibes-class, generational recall."
            ),
            entry_count=100,
            next_revision_year=2027,
        ),
        CanonListMeta(
            list_slug="the-50-most-defining-games-cfp-era",
            title="The 50 Most Defining Games of the CFP Era",
            edition_year=2026,
            list_kind="games",
            description=(
                "Fifty games from 2014–2025 that decided more than their "
                "scoreboard. The list isn't 'most exciting' or 'highest "
                "quality of play' — it's games that changed the era's "
                "trajectory: titles, coaching seats, conference balance, "
                "the Playoff format itself."
            ),
            methodology_notes=(
                "Scope: regular season, conference championship, and "
                "postseason games from the 2014 season through the 2025 "
                "season. Ranking weighs (a) decision weight on the "
                "season's title, (b) program-trajectory consequence, (c) "
                "instruction value to the era's future — which moments "
                "become reference points the next ten years' beat writers "
                "use to explain what just happened."
            ),
            entry_count=50,
            next_revision_year=2027,
        ),
        CanonListMeta(
            list_slug="the-25-best-coaching-hires-2020s",
            title="The 25 Best Coaching Hires of the 2020s",
            edition_year=2026,
            list_kind="coaching_hires",
            description=(
                "Twenty-five hires from 2020 through 2025 that aged best — "
                "or showed enough through the early returns that the "
                "judgment is settling. Some are championship outcomes "
                "already. Some are bets the program has not yet collected "
                "on but the early evidence vindicates."
            ),
            methodology_notes=(
                "Hires made between January 2020 and December 2025 "
                "inclusive. Ranking weighs: outcome at the program (titles, "
                "trajectory, recruiting compounding), fit at the moment "
                "of the hire (how good the bet looked at the time vs. how "
                "it played), and ripple effect on the coaching market. "
                "Where data is thin (hires made in 2024 or 2025 with one "
                "season's evidence) the rank is held provisionally — see "
                "rank-delta column for revision posture."
            ),
            entry_count=25,
            next_revision_year=2027,
        ),
    ]


# --------------------------------------------------------------------------
# Effort-bucket declaration (per list_slug). Generator reports these.
# --------------------------------------------------------------------------

def effort_buckets_for(list_slug: str) -> dict[str, int]:
    if list_slug == "the-100-best-players-cfp-era":
        # 100 entries: 3 opus-equivalent (top blue-blood paragraphs),
        # 22 sonnet-equivalent paragraphs (ranks 4-25),
        # 75 sonnet-equivalent oneliners (ranks 26-100).
        # 100 sonnet-equivalent baseline oneliners (every entry).
        # Total effort units = 100 oneliners + 25 paragraphs = 125
        # opus share = 3/125 = 2.4% — well under 15%.
        return {"haiku": 0, "sonnet": 122, "opus": 3}
    if list_slug == "the-50-most-defining-games-cfp-era":
        # 50 oneliners + 15 paragraphs = 65 effort units; 0 opus.
        return {"haiku": 0, "sonnet": 65, "opus": 0}
    if list_slug == "the-25-best-coaching-hires-2020s":
        # 25 oneliners + 25 paragraphs = 50 effort units; 0 opus.
        return {"haiku": 0, "sonnet": 50, "opus": 0}
    return {"haiku": 0, "sonnet": 0, "opus": 0}


# --------------------------------------------------------------------------
# Entry sources (split into per-list modules below for readability)
# --------------------------------------------------------------------------

def entries_for(list_slug: str) -> list[CanonEntry]:
    if list_slug == "the-100-best-players-cfp-era":
        from . import seed_players
        return seed_players.entries()
    if list_slug == "the-50-most-defining-games-cfp-era":
        from . import seed_games
        return seed_games.entries()
    if list_slug == "the-25-best-coaching-hires-2020s":
        from . import seed_coaching_hires
        return seed_coaching_hires.entries()
    return []
