# WS-10 — Cross-Archetype Navigation + Entity Graph

**Phase:** 4 (Jan–Mar 2027)
**Owner:** Claude execution
**Status:** Blocked on WS-06 + WS-07 (target pages must exist)

## Goal

Every page becomes a hypertext node in the CFB knowledge graph. Two mechanisms: (1) cross-archetype time-zoom navigation strip on every page; (2) every entity reference inline-renders with hover-card preview.

## Definition of perfect

- **Time-zoom strip:** Horizontal nav on every archetype-typed page. For entities that exist in multiple archetypes, links: TODAY (Pulse view) · This Week (Beat) · This Month (Arc) · Season 2026 (Tentpole) · CFP Era 2014– (Anniversary). Strip renders only the views that exist for the entity.
- **Hover-card preview:** Every entity reference (`[[team:usc]]`, `[[coach:lincoln-riley]]`, etc.) in editorial copy + chip text inline-renders with a hover-card showing the entity's current archetype, key 2026 storyline, 1-line context.
- **Entity graph queryable** via cmdk: "every coach who succeeded a Saban disciple" returns a ranked list with snippet previews.
- **Backlink discovery:** Every entity page shows "This entity is referenced by: [N other pages]" with click-through.

## Current state

- Cross-archetype navigation doesn't exist; pages live in isolation.
- Some inline links exist (mostly editor-curated, not entity-graph-driven).
- cmdk index exists at `src/cfb_rankings/cmdk/index_builder.py` but doesn't power semantic search.
- Backlinks don't exist.

## Dependencies

- **Blocks:** Phase 5 "perfect" launch (recursive product framing is a launch promise)
- **Blocked by:** WS-06 (Coach/Game/Rivalry/Conference pages must exist as cross-link targets), WS-07 (era pages), WS-05 (Nomic embedding for semantic search), `entity_resolver` not yet built

## Implementation approach

1. Build `entity_resolver` — single function that takes `(entity_kind, entity_id)` and returns the list of pages that exist for that entity across all archetypes.
2. Build time-zoom strip component. Renders only existing pages. Active tab highlighted. Mobile-responsive (collapses to dropdown at <500px).
3. Build `[[entity_id]]` inline-link convention in Markdown. Renderer parses + inserts hover-card metadata.
4. Build hover-card component. Server-rendered with key facts; JS-progressive enhancement for keyboard nav.
5. Wire Nomic Embed V2 (per VISION § 11) over all entity pages → semantic search index. Expose via cmdk.
6. Build backlink crawler — walks rendered HTML, extracts entity references, builds reverse index. Render "Referenced by" on each entity page.

## Running gate

- Time-zoom strip on 100% of archetype-typed pages.
- Hover-card preview on ≥80% of inline entity references.
- cmdk semantic search returns useful results for 10 test queries.
- Backlinks visible on top-200 entity pages.

## Decisions

- None blocking (downstream of locked WS-06 + WS-07)

## Pointers

- `src/cfb_rankings/cmdk/index_builder.py` (existing search index, needs upgrade)
- VISION § 5 (5-horizon model), § 11 (Nomic embedding tier)
