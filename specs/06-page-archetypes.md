# WS-06 — Page Archetype Expansion (Coach / Game / Rivalry / Conference)

**Phase:** 3 (Oct–Dec 2026)
**Owner:** Claude execution
**Status:** Blocked on WS-02 (archetype data) + `coaches` table creation

## Goal

Build four new first-class page archetypes. Each gets its own design template inheriting from the locked 6 IA archetypes (`docs/design-system/30-page-archetypes.md`).

## Definition of perfect

- **Coach pages:** Every active FBS head coach has a page. Sections: career arc, year-by-year team results, NFL output during tenure, coaching tree position (succeeded X, came from Y), defining games, archetype assignment.
- **Game pages:** Every defining-era game has a page. Sections: full play-by-play (where data exists), mood data (post-game fan sentiment), market data (pre-game implied probability vs final), post-game narrative, defining-moment timestamp.
- **Rivalry pages:** Every named rivalry has a page. Sections: all-time record, intensity score (composite of W-L + fanbase mood swing + NFL transfers + recruiting head-to-head), recent meetings, defining games, current temperature.
- **Conference pages:** Every conference has a page. Sections: current member list, realignment history, era retrospectives, member-comparison tool, current state assessment.
- All four archetypes register in the page-archetype lock; CI catches drift.

## Current state

- `coaching_era.py` module exists for team-page rendering.
- `rivalry_card.py` module exists for team-page rendering.
- Conference index pages exist (basic).
- No standalone Coach pages, Game pages, or Rivalry pages.
- `coaches` table does not exist; coaches are referenced by name in `roster_entries` but not as first-class entities.
- `coaching_changes` table exists (empty).

## Dependencies

- **Blocks:** WS-10 (cross-archetype nav strip needs all archetypes to exist)
- **Blocked by:** WS-02 (archetype data for coaches), `coaches` table creation, structural data

## Implementation approach

1. Build `coaches` table from CFBD data (we ingest CFBD Coaches 2018-2024 per CLAUDE.md). Schema: coach_id, full_name, current_team_id, tenure_start_year, tenure_end_year, archetype (joins to WS-02 coach archetype work).
2. Populate `coaching_changes` from year-over-year diffs in CFBD data.
3. Build Coach page archetype + renderer. Iterate Alabama (DeBoer) as prototype.
4. Build Game page archetype. Iterate one CFP-era classic as prototype (e.g., 2017 UCF vs Auburn).
5. Build Rivalry page archetype. Iterate Iron Bowl as prototype.
6. Build full Conference page archetype. Iterate SEC as prototype.
7. Roll out across all active coaches, all defining games (top-25 vs top-25 + postseason), all named rivalries, all 12 conferences.

## Running gate

- ~120 Coach pages exist (one per active HC + recent former HCs).
- ~150 Game pages exist (defining games of CFP era).
- ~30 Rivalry pages exist (named rivalries with first-class treatment).
- 12 Conference pages exist with current realignment state.

## Decisions

- D-018 — Player narrative arc generation scope (related: defines "priority players" cohort that affects which games get Game pages)

## Pointers

- `docs/design-system/30-page-archetypes.md` (lock)
- `src/cfb_rankings/team_pages/coaching_era.py`
- `src/cfb_rankings/team_pages/rivalry_card.py`
- VISION § 8 (workstream summary)
