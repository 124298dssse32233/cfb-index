# WS-04 — Historical Backfill (Pre-2014)

**Phase:** 4 (Jan–Mar 2027)
**Owner:** Claude execution
**Status:** Blocked on D-012 (backfill scope); deferred until Phase 4

## Goal

Extend the structural data layer from CFP-era-only (2014+) to AP-poll-era depth (1936+) and curated all-time records (1869-1935). Honor the difference between Owned / Borrowed / Inherited data via visual + typographic distinction.

## Definition of perfect

- Bowl game results ingested 1902–2013 from Sports Reference + CFB Reference (~1,200 bowls).
- AP poll history ingested 1936–2013 (~3,900 poll-weeks).
- Heisman finalists + winners ingested 1935–2013 (~80 winners + ~400 finalists).
- Coaches with HC tenures ingested 1869–2013 from public sources.
- Conference membership history ingested 1869–2013 (needed for realignment timeline pages).
- All-time records page queryable ("Has any team done X").
- Pre-2014 visual distinction: Era 2 (1998-2013) = lighter ink; Era 3 (pre-1998) = archive-style typography.

## Current state

- Zero pre-2014 rows in any structural table.
- Game-level data starts 2018 (per CLAUDE.md "Game data maxes at 2024; forward tables have 2025").
- Coach data starts 2018.

## Dependencies

- **Blocks:** Era pages with pre-2014 acts (WS-07 covers CFP-era acts only), all-time records page, realignment timeline, decade pages for top-25 programs.
- **Blocked by:** D-012 (scope: full 1869 vs 1936 start)

## Implementation approach

1. Lock D-012 — recommend 1936-2013 first (AP poll era), pre-1936 in a later phase.
2. Build CFB Reference + Sports Reference scrapers (respecting robots.txt + rate limits + ToS).
3. Schema additions: extend `games` table to support pre-CFP-era fields (e.g., `is_bowl_official_pre_1934` flag); add `coaches_historical` table; add `conference_membership_history`.
4. Scrape + load in seasonal chunks. Validation: spot-check 5 random seasons per decade against alternative sources (Wikipedia, newspapers archive).
5. Build "Borrowed era" visual distinction in renderer (different palette, lighter borders, era-marker chip on every page citing source).
6. Build all-time records query engine + page.

## Running gate

- 78 seasons (1936-2013) of AP polls in DB.
- ~1,200 bowl results in DB.
- Every era page distinguishes Owned vs Borrowed vs Inherited typographically.
- All-time records page exists and answers ≥10 example queries from a stress-test list.

## Decisions

- D-012 — Pre-2014 backfill scope — OPEN

## Pointers

- VISION § 4 (CFP era frame includes pre-2014 framing)
- Sports Reference + CFB Reference URLs (to be documented in this spec when scraping starts)
