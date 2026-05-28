# Workstream Specs Index

12 workstreams. Each has its own spec file with: goal, definition of perfect, current state, dependencies, implementation approach, running gate, decisions, pointers.

> **Read this when:** picking up a workstream after time away, scoping a PR, deciding execution order. **For the big picture:** [../VISION_2026_2027.md](../VISION_2026_2027.md).

## The 12 workstreams

| # | Spec | Goal | Phase | Status |
|---|---|---|---|---|
| 01 | [foundation-unblock](01-foundation-unblock.md) | Tier S mechanical fixes (bucket label, cohort wiring, numeric_observations table, loud-fail adapters, team_coverage, commit Wave 25) | 1 | Ready to start |
| 02 | [classification-state](02-classification-state.md) | Run existing fanbase archetype classifier; populate empty narrative-state tables; backtest against 12 CFP-era seasons | 1–2 | Blocked on D-010 |
| 03 | [editorial-profiles](03-editorial-profiles.md) | Expand 17 → 40 → 119 profiles via LLM-draft + human-review with voice_validator enforcement | 2–3 | Blocked on D-011 |
| 04 | [historical-backfill](04-historical-backfill.md) | Pre-2014 historical data (bowls, AP polls, Heisman, coaches, conference history) | 4 | Blocked on D-012; deferred |
| 05 | [adapter-ecosystem](05-adapter-ecosystem.md) | All 84 sources actually emitting rows (today: 2 of 84) | 1–2 | Blocked on WS-01 (numeric_observations) |
| 06 | [page-archetypes](06-page-archetypes.md) | Coach + Game + Rivalry + Conference page types built, populated, linked | 3 | Blocked on WS-02 + coaches table |
| 07 | [era-pages-cfp](07-era-pages-cfp.md) | Every FBS program's CFP-era page in three-act design | 2–3 | Blocked on WS-03 + structural validation |
| 08 | [chart-vocabulary](08-chart-vocabulary.md) | Lock chart vocab at 9 types (add Sankey, Choropleth, Network) | 2 | Not blocked |
| 09 | [calibration-ledger](09-calibration-ledger.md) | Every published prediction logged; weekly outcome resolver; public calibration history | 2–3 | Blocked on D-015 |
| 10 | [cross-archetype-entity-graph](10-cross-archetype-entity-graph.md) | Time-zoom nav strip; entity-graph hover-card preview; semantic search | 4 | Blocked on WS-06 + WS-07 |
| 11 | [mobile-a11y-perf](11-mobile-a11y-perf.md) | Lighthouse 100/100/100/100; mobile 320px; WCAG AA; SVG fallback for every chart | 5 | Not blocked; deferred |
| 12 | [editorial-cadence](12-editorial-cadence.md) | Wire daily, Mailbag weekly, storyline chapters bi-weekly; voice + receipt enforcement | continuous | Partial (running but slipping) |

## Adding a new workstream

If a 13th workstream emerges:

1. Open a `DECISIONS.md` entry stating why a new workstream is justified (and which existing workstream couldn't absorb it).
2. Number it sequentially (13, 14, …).
3. Use the spec template (any existing spec is a template).
4. Add to this index.
5. Update VISION § 8 (workstream table) and STATUS.md.

## Spec template (copy when adding new)

```markdown
# WS-NN — [Workstream Name]

**Phase:** N (date range)
**Owner:** [Claude execution | Editorial | etc.]
**Status:** [Ready | Blocked on D-XXX | In flight | Done]

## Goal

[One paragraph. What problem does this workstream solve? What's the outcome?]

## Definition of perfect

[5–7 bullet points. Specific. Testable.]

## Current state

[What exists today. What's missing.]

## Dependencies

- **Blocks:** [other workstreams]
- **Blocked by:** [other workstreams or decisions]

## Implementation approach

[Numbered steps. High-level. Not code.]

## Running gate

[Concrete evidence of "done." Measurable.]

## Decisions

[Cite DECISIONS.md entries that affect this workstream.]

## Pointers

[File paths, doc sections, external resources.]
```
