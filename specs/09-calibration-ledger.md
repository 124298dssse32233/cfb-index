# WS-09 — Calibration Ledger

**Phase:** 2–3 (Aug–Dec 2026)
**Owner:** Claude execution
**Status:** Blocked on D-015 (publication cadence)

## Goal

Every published prediction on the site logs to a `prediction_ledger`. Outcomes resolve weekly. Methodology page renders the live calibration history per model. **This is the product's trust spine** and the single biggest editorial differentiator vs ESPN/Athletic/247.

## Definition of perfect

- `prediction_ledger` table created. Schema: prediction_id, model_id, entity_type, entity_id, observed_at, prediction_kind (e.g., "cfp_make_field", "season_wins", "archetype_assignment"), predicted_value, confidence_band, expires_at, evidence_ref.
- Every chip on every page that renders a prediction also writes a row at render time. Instrumented via single decorator.
- Outcome resolver runs weekly. For each prediction whose `expires_at` has passed, looks up the actual outcome and writes `resolved_at`, `actual_value`, `accuracy_score` to the row.
- Methodology page renders per-model calibration history: "Last 100 predictions, 73% accurate within 1 SD" + per-entity drill-down.
- Confidence_calibration table (existing, 5 rows) gets weekly automated update per D-015.
- Public per-team "We said X, then Y happened" track record visible on each team page.

## Current state

- `confidence_calibration` table exists with 5 rows (~design-doc only).
- Design doc `docs/design-system/33-confidence-signaling.md` locked.
- No `prediction_ledger` table exists.
- No instrumentation; predictions are rendered without being logged.
- No outcome resolver.
- Methodology page exists but doesn't render calibration history.

## Dependencies

- **Blocks:** Editorial credibility framing (Phase 5 launch claim "we publish our confusion matrix")
- **Blocked by:** D-015 (publication cadence), WS-02 (predictions to track exist — archetype assignments, arc states), WS-05 (market data feeds for outcome comparison)

## Implementation approach

1. Lock D-015 — recommend: continuous ledger writes, weekly public summary.
2. Build `prediction_ledger` migration.
3. Build prediction-writing decorator. Every chip-rendering function that emits a prediction wraps through it.
4. Instrument existing prediction surfaces: archetype assignment (WS-02), Heisman model (existing), season-win projections (existing), Reality Gap (existing), etc.
5. Build outcome resolver cron. Walks past `expires_at` rows, joins to outcome tables (games, awards, transfers, archetype-future state), writes resolution.
6. Automate quarterly recalibration of `confidence_calibration` thresholds (per design doc).
7. Build methodology page renderer for live calibration history. Per-model accuracy chart + per-entity drill-down.
8. Build per-team "track record" section on team pages.

## Running gate

- `prediction_ledger` accumulates ≥10,000 rows in first month of in-season operation.
- Outcome resolver has resolved ≥80% of expired predictions within 7 days of expiry.
- Methodology page renders live calibration history.
- Per-team track record visible on at least 25 team pages.

## Decisions

- D-015 — Publication cadence — OPEN

## Pointers

- `docs/design-system/33-confidence-signaling.md`
- `src/cfb_rankings/confidence.py`
- VISION § 6 Layer 5 (Outcomes & Calibration)
