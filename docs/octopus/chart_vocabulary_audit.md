# Chart Vocabulary Audit — 2026-05-18

_Inventory of every chart-rendering surface in the live site, classified against the locked `docs/design-system/31-chart-vocabulary.md` allowed-six taxonomy. Pairs with `docs/octopus/implementation_plan_visual_system.md` Phase 2B (chart vocabulary enforcement)._

The spec locks **six allowed chart types**:

1. **Percentile Bar** (Baseball Savant style)
2. **Trajectory Spark** (160×40px inline sparkline)
3. **Bump Chart** (ranking movement)
4. **Annotated Line** (NYT-Upshot style)
5. **Small Multiples Grid** (Tufte / Bloomberg)
6. **Heatmap**

And **explicitly forbids** pie, donut, vertical bar (without percentile encoding), radar (except Player Fingerprint), 3D, and word clouds.

The spec also calls for centralization at `src/cfb_rankings/charts/__init__.py`, which **does not currently exist** (verified). All chart rendering is scattered across `reporting.py` + isolated modules.

---

## Inventory

### APPROVED (matches one of the six)

| # | Surface | File · Function | Spec match | Evidence |
|---|---|---|---|---|
| 1 | **Rank sparkline** (inline next to rankings rows) | `src/cfb_rankings/rankings_sparklines.py` · `_render_*` | Trajectory Spark | 80×24px SVG polyline; red/green/gray sentiment coding; 5-week rolling — within the 160×40 sparkline budget |
| 2 | **Cover sparkline** (10-year trend hero graphic) | `src/cfb_rankings/hub_page.py` lines ~428–680 | Annotated Line | 520×320px line with reference baseline + endpoint markers — larger than spark, so reclassified as Annotated Line per the spec's size guidance |
| 3 | **Mood Index 10-week trajectory** (hub) | `src/cfb_rankings/hub_page.py` lines ~668–750 | Annotated Line | Multi-team line chart with legend + reference threshold line + axes — matches NYT-Upshot annotated pattern |
| 4 | **Dynasty heatmap** (programs × years, 2014–2025) | `src/cfb_rankings/dynasty_heatmap.py` lines ~193–390 | Heatmap | 52×16px cells with within-year percentile color stops; matches sequential single-hue requirement |
| 5 | **Edition heatmap template** | `src/cfb_rankings/editions/viz_templates/heatmap.py` | Heatmap | Reusable calendar heatmap; data-driven grid w/ cream→gold→navy interpolation |
| 6 | **Savant card percentile bars** (profiled team pages) | `src/cfb_rankings/team_pages/savant_card.py` lines ~39–198 | Percentile Bar | 13 bars (5 off, 5 def, 3 ST) with peer-set toggle; CSS-driven fills, no D3 — exact Baseball Savant pattern |
| 7 | **Season Arc card chart** (profiled team pages) | `src/cfb_rankings/team_pages/season_arc_card.py` lines ~123–314 | Annotated Line | 2014+ trajectory with era ribbon overlay + annotation markers |
| 8 | **Team Journey chart** (legacy team pages) | `reporting.py` · `_render_team_journey_chart` lines ~21221–21272 | Annotated Line | Full-width single-series line, 860×360 viewBox, hoverable markers, opponent-level ring annotations, legend — fits annotated-line spec at full size |

**Eight surfaces are clean.** Trajectory + Annotated Line dominate (5 of 8), then Heatmap (2), then Percentile Bar (1).

### FORBIDDEN (violates the locked vocabulary)

| # | Surface | File · Function | Violation | Severity |
|---|---|---|---|---|
| F1 | **Program history chart** (10-season win-rate bars + power-rating polyline overlay) | `reporting.py` · `_render_history_chart` lines ~18348–18410 | Vertical bar without percentile encoding | **HIGH** — explicit spec violation. Bar height = raw `wins/games`, not percentile. Recommend: drop the bars, keep the polyline as a trajectory spark with annotations for notable seasons. |
| F2 | **Weekly delta blocks** (per-game delta as a column of vertical bars) | `reporting.py` · `_render_weekly_delta_blocks` lines ~21275+ | Vertical bar without percentile encoding | **MEDIUM** — same pattern: bar height = `abs(delta) * scaler`, not percentile. Recommend: reformat as a trajectory spark of cumulative delta, or as a horizontal divergent bar with neutral-grey center. |

**Two violations, both in the legacy team-pages render path** (`reporting.py`, the 26.8k-line monolith). Neither touches the world-class `team_pages/` renderer (the profiled-program path), which means profiled programs (17 slugs) already escape these violations.

### AMBIGUOUS (custom rendering that doesn't cleanly fit the taxonomy)

| # | Surface | File · Function | Why ambiguous | Recommendation |
|---|---|---|---|---|
| A1 | **Cohort divergence scatter** (player page) | `reporting.py` lines ~3870–3915 | 2D continuous scatter (belief × intensity, bubble size = mentions) — none of the six fit; closest would be a heatmap if discretized, but as continuous scatter, it's outside the vocabulary | Either (a) discretize to a heatmap, or (b) add **Scatter Plot** as the 7th allowed type with locked spec — propose in COORDINATION.md before any new scatter is added |
| A2 | **Rival Radar card** (player page) | `reporting.py` · `render_rival_radar_card` lines ~4576–4652 | The **name** is "radar" but the render is metric tiles + horizontal stacked sentiment bar — NOT a radar chart. The audit's first-pass auto-classification flagged this as FORBIDDEN; on closer read it's a metric-tile-grid + horizontal stack | Re-tag: NOT a radar chart. This is an approved-style metric-tile composition. Consider renaming the product feature to drop the misleading "Radar" word — or leave the brand name and document the chart-as-tile-row pattern in `docs/design-system/01-atoms.md` |

### NOT AUDITED

- **Player Fingerprint radar** — the one exception the spec allows. Not verified in this pass; per `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` it's a planned Phase 3 module (not yet built into renderer). When it ships, it's covered by the explicit spec exception.
- **Client-side JS-built charts** — none found in current `static_assets/js/`. The site is server-rendered SVG end-to-end as of 2026-05-18.

---

## Summary

- **8 APPROVED surfaces** — Trajectory + Annotated Line dominate (5/8); Heatmap and Percentile Bar each have 2 and 1 respectively.
- **2 FORBIDDEN surfaces** — both in legacy `reporting.py` team-pages render path; profiled programs (`team_pages/`) are already clean.
- **2 AMBIGUOUS surfaces** — cohort divergence scatter (genuinely outside the 6), Rival Radar (misleading name, actually approved metric-tile composition).
- **0 centralization** — `src/cfb_rankings/charts/__init__.py` does not exist. All chart rendering is scattered.

## Phase 2B follow-up tasks

The implementation plan's Phase 2B (chart vocabulary enforcement) needs four concrete tasks:

1. **Refactor F1 + F2** (legacy team-pages bar charts) — drop the bars, keep the trajectory polyline + annotations. Both are isolated rendering helpers in `reporting.py`; surgical refactor with no schema changes.
2. **Decide on A1** (cohort divergence scatter) — propose Scatter Plot as the 7th allowed type, OR discretize into a heatmap. The 7th type proposal is the cleaner long-term answer if scatter plots are needed for player-comparison surfaces.
3. **Re-tag A2** (Rival Radar) — either rename the product feature to "Rival Pressure" / "Rival Heat" / "Rival Spotlight", OR keep the name and add a docs/design-system/01-atoms.md entry describing the metric-tile + stacked-sentiment-bar composition.
4. **Build `src/cfb_rankings/charts/__init__.py`** — centralize the 6 approved renderers per the spec's "Implementation" section. Lint rule that fails CI if new chart-rendering functions are defined outside this module.

The estimated total for Phase 2B is 1–1.5 weeks if all four tasks ship together, or surgical per-task if shipped separately.

---

## Verification trail

This audit was generated by an Explore subagent (broad code search) then **verified by hand** against the actual code:

- Confirmed all 6 referenced module paths exist (`ls` check)
- Read `rival_radar.py` + the `render_rival_radar_card` HTML emitter to verify the FORBIDDEN classification was wrong (it's not a radar chart)
- Read `_render_history_chart` to confirm `rect` elements with `height` proportional to `win_pct` — confirmed vertical-bar-without-percentile violation
- Read `_render_team_journey_chart` to confirm full-width annotated line, not ambiguous
- Read cohort divergence scatter to confirm it's genuine 2D continuous scatter outside the vocabulary

Per the project memory rule: "Octopus briefs need verification — generated audit briefs have repeatedly misdiagnosed architecture; verify each claim against current code before executing." This audit was held to that bar.
