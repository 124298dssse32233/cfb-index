# WS-08 — Chart Vocabulary Expansion (6 → 9)

**Phase:** 2 (Jul–Aug 2026)
**Owner:** Claude execution
**Status:** Not blocked, can start anytime

## Goal

Extend the locked chart vocabulary from 6 to 9 types, preserving the same governance discipline (whitelist in `charts/__init__.py`, CI lint, locked use cases per type, forbidden list).

## Definition of perfect

- 9 chart types locked: existing 6 (Percentile Bar, Trajectory Spark, Bump Chart, Annotated Line, Small Multiples, Heatmap) + 3 new (Sankey, Choropleth, Network).
- **Sankey** — portal flows, recruiting class composition, coaching tree branching. Locked usage: actual flows only (NOT rank changes — use Bump).
- **Choropleth** — recruiting geography, fan-density maps, regional attention. Locked usage: geography is the point (NOT incidental).
- **Network** — coaching trees, conference realignment connections, rivalry constellations. Locked usage: ≤50 nodes (above that, use small multiples).
- Annotation overlay DSL (YAML) lets editorial add arrows + labels without touching SVG.
- Chart-card component is the single shared component all charts render through. Has: eyebrow, headline, lede, chart, x/y label, source-receipt footer, optional annotation overlay.
- CI lint catches any `def render_*_chart` outside `src/cfb_rankings/charts/`.

## Current state

- 6 chart types locked 2026-05-17 in `docs/design-system/31-chart-vocabulary.md` with editorial use cases + forbidden list.
- Implementation lives at `src/cfb_rankings/charts/__init__.py` (per design doc).
- No Sankey / Choropleth / Network implementations exist.
- Chart-card component is implicit (drift across surfaces — some charts have receipt footers, some don't).

## Dependencies

- **Blocks:** WS-07 (era pages benefit from Sankey for portal era), WS-06 (Network for coaching trees on Coach pages)
- **Blocked by:** Nothing

## Implementation approach

1. Implement Sankey first — portal flows data already exists (`transfer_entries` has 14,801 rows). Render a national portal-flow page + per-team Sankey on Coach pages.
2. Implement Choropleth second — recruiting geography. Use `player_recruiting_profiles` (20,392 rows) for HS-state-to-college-state flows. US-state choropleth + zoom to home-state regions.
3. Implement Network third — coaching trees. Requires WS-06 `coaches` table (succeed/predecessor relationships) — schedule after that lands.
4. Update `docs/design-system/31-chart-vocabulary.md` to "Locked at 9 types as of [date]." Add the 3 new types' use-when + use-NOT-when sections.
5. Build annotation DSL: YAML format that maps to SVG `<text>` + arrow `<path>` overlays. Wire to chart-card component.
6. Audit existing charts; refactor any that don't go through the shared chart-card component.

## Running gate

- Each of 9 chart types has at least one production render on the live site.
- CI lint enforces vocabulary lock.
- Every chart on every page renders through the shared chart-card component.
- Annotation DSL has at least 5 production examples.
- Mobile-renders at 320px legibly for every type.

## Decisions

- D-007 — Chart vocab expansion 6 → 9 — LOCKED

## Pointers

- `docs/design-system/31-chart-vocabulary.md`
- `src/cfb_rankings/charts/` (target for new types)
- VISION § 8 (workstream summary)
