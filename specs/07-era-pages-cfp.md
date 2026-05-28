# WS-07 — Era Pages (CFP Three-Act Design)

**Phase:** 2–3 (Aug–Dec 2026)
**Owner:** Claude execution
**Status:** Blocked on WS-03 (profile depth) + structural data validation

## Goal

Every FBS program has an era page that tells its CFP-era story in three acts (Founding 2014-2020 / Transition 2021-2023 / Expansion 2024-present). This is the page-archetype that delivers "we are a repository" most concretely.

## Definition of perfect

- Every FBS program has a `/programs/<slug>/era/cfp/` page rendering the 6-section design.
- 6 sections: (1) Era stat sheet (above-fold facts), (2) Three-act trajectory chart, (3) Defining games (5 most-cited), (4) Coaches of the era (Gantt), (5) Roster of the era (drafted + All-Conference), (6) Entering Year 13 (forward-look bridge).
- Three acts visually delineated by colored backgrounds + annotation markers.
- LLM-generated three-paragraph ledes (one per act) pass voice_validator + receipt-pattern density (≥1/200 words).
- Cross-link to relevant `storyline_threads` where they overlap (e.g., Alabama era page links to `saban-to-deboer` thread).
- Top-25 programs additionally have pre-2014 decade pages once WS-04 completes.

## Current state

- No era pages exist. `historical_season_page.py` exists for individual-season historical pages but not multi-season era summaries.
- Structural data (power ratings, resume, bowls, NFL pipeline) covers 2014-2025 — sufficient for the three-act trajectory chart.
- 17 hand-authored profiles can support tier-1 era pages; remaining 102 wait on WS-03.

## Dependencies

- **Blocks:** WS-10 (cross-archetype nav strip needs era pages as a time-zoom target)
- **Blocked by:** WS-03 (profile depth for editorial register), WS-02 (archetype + arc data for the "what story did this era tell" framing)

## Implementation approach

1. Design + lock the 6-section template. Single shared layout component.
2. Build Alabama era page as the prototype. Iterate copy, chart density, annotation discipline.
3. Generate three-paragraph ledes via Chronicle pipeline (one Chronicle card per act). Voice + receipt enforcement.
4. Roll out to top-25 programs by Sep 30 2026.
5. Roll out to remaining FBS (using `editorial_assisted` and `minimal` profile tiers as input) by Mar 2027.
6. Era pages get the cross-archetype nav strip (WS-10) linking back to Pulse / Beat / Arc / Season views of same entity.

## Running gate

- 25 era pages live by end of Phase 2 (Sep 2026).
- 119 era pages live by end of Phase 3 (Dec 2026).
- Every era page renders three-act trajectory chart with proper sub-era backgrounds.
- Every Chronicle-generated lede passes voice + receipt validators.

## Decisions

- D-001 — Data horizon 2014 — LOCKED
- Related: D-011 (profile tiers), D-014 (voice LoRA)

## Pointers

- VISION § 4 (CFP era frame), § 5 (5-horizon model)
- Existing prototype reference: NOTRE_DAME_PAGE_EXAMPLE.md (still in root — possible reference, not yet validated)
