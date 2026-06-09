# WS-02 — Classification + State Machinery

**Phase:** 1–2 (Jun–Aug 2026)
**Owner:** Claude execution
**Status:** Blocked on D-010 (lock the 10 arc frames)

## Goal

Take the existing-but-empty classification schemas and actually run them end-to-end. Add transition discipline + audit trail + 12-season backtest validation. No parallel system (see D-003).

## Definition of perfect

- `fanbase_classification` table populated weekly for all 119 FBS teams via the existing classifier at `src/cfb_rankings/ingest/archetypes.py`.
- `fanbase_classification_history` captures every primary-archetype transition with from/to + driving metric.
- Transition discipline enforced: 4-week cooldown for primary archetype; 1-week for modifiers; 2-week confirmation at new threshold.
- `season_narrative_arc` populated for all 119 FBS teams using the 10 locked arc frames (D-010).
- `season_narrative_state.open_arcs_json` / `resolved_arcs_json` / `unresolved_tensions_json` updated weekly.
- `player_archetype_tags` populated for top-200 priority players via position-aware classifier.
- 12-season backtest published on methodology page: classifier applied retroactively against 2014-2025, hand-validated against known-story teams (2017 UCF, 2023 FSU, 2022 Tennessee, etc.).

## Current state

- Schema: comprehensive and existing.
- Data: `fanbase_archetype_taxonomy` (0 rows), `fanbase_classification` (0), `fanbase_classification_history` (0), `player_archetype_tags` (0), `season_narrative_arc` (0), `season_narrative_state` (0). Population gap is the whole problem.
- Classifier code: `archetypes.py:421 classify_team()` exists and is sound; just never invoked weekly.

## Dependencies

- **Blocks:** WS-06 (Coach archetype assignment), WS-09 (calibration ledger needs predictions to track), WS-12 (storyline candidate queue reads transitions)
- **Blocked by:** D-010 (lock arc frames) and WS-01 (cohort_divergence wiring)

## Implementation approach

1. Run `seed_taxonomy(db)` + `classify_all_fanbases(db, 2026)` immediately — populates current archetype assignments.
2. Build weekly cron that re-runs classification + writes to `_history` on transitions.
3. Add transition discipline wrapper around classifier (cooldown, confirmation logic).
4. Define + implement the 10 arc frames (per D-010). Each frame has open + close conditions.
5. Build `season_narrative_arc` populator that walks events (transfers, recruits, coach changes, archetype transitions, market moves) and opens/closes arcs.
6. Build player-archetype classifier (position-aware) for top-200 priority players.
7. Run 12-season backtest. Tune thresholds. Publish methodology page.

## Running gate

- Every FBS team has a current archetype assignment in `fanbase_classification`.
- Every FBS team has ≥1 open arc in `season_narrative_arc` (offseason will be quieter than in-season).
- Top-200 players have entries in `player_archetype_tags`.
- Methodology page renders 12-season backtest accuracy per archetype.

## Decisions

- D-003 — No parallel state machine — LOCKED
- D-010 — 10 arc frames — OPEN (gating)
- D-022 — "Dynasty status" signal definition — LOCKED (2026-05-28): dynasty status = trailing-3-season average of within-season power-rating percentile (the Dynasty Heatmap signal), elite threshold 85th pct, enter/exit on threshold crossings. Reuses the existing power signal rather than a 6th classification axis (per D-003). Lights up the `dynasty_status_change` arc frame — **6 of 10 frames now data-backed.**

## Pointers

- `src/cfb_rankings/ingest/archetypes.py` (the classifier)
- `src/cfb_rankings/chronicle/arc_populator.py` (the 10-frame arc populator; `_detect_dynasty_status_change` per D-022)
- `src/cfb_rankings/dynasty_heatmap.py` (`fetch_final_powers` + `compute_year_percentiles` — the dynasty signal source)
- VISION § 4 (5-layer signal model), § 7 (cohesion principle)
- DECISIONS D-003, D-010, D-022
