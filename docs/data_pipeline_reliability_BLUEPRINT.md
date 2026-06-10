# Daily Pipeline Reliability — Build-Ready Blueprint

**Date:** 2026-06-09. **Status: design only — nothing implemented.** Consolidates three code-grounded design reviews (data-quality gate + safety nets; week-key unification; daily encoder classify) into one build order. Companion to `data_pipeline_reliability_review.md` (audit) and `data_pipeline_reliability_PLAN.md` (strategy).

---

## ⭐ Three cross-cutting insights that shape everything

1. **The gate must ship WARN-not-FAIL for the data tables — because 4 of 6 are empty/frozen RIGHT NOW.** A live-DB probe found: `team_cohort_week` = 0 rows, `player_week_conversation_features` = 0 rows, `team_week_conversation_features` stale (keyed 2025/wk41), `fanbase_mood_weekly` frozen at 2026-04-22. These are the exact silent-zero bugs Phase 2 fixes. So the publish gate ships with those as **WARN** (visible, non-blocking) + a `--strict` flag (`VERIFY_STRICT_MOOD=1`) to promote them to hard-fail **the day Phase 2 lands**. Otherwise the gate would block your publish every single day starting now. *(Only `integrity_check`, `foreign_key_check`, and "conversation_documents got fresh rows today" are hard-fail from day one — those are reliably populated: 150,690 docs in the last 24h.)*

2. **The week-key fix only works if producer and consumer move together.** The root cause is numeric: producers stamp `(season_year=2025, week=42)`; consumers query ISO `(2026, 24)` → 0 rows; mood raises `ValueError` (frozen calendar). Fixing the calendar alone is NOT enough — the fallback must resolve to the *same* `(2025, 42)` the producer wrote. So `resolve_week()` + the `daily_ingest.ps1` switch + the map fallback **must ship in one commit**, or rows still won't match.

3. **The manifest *check* and *writer* must ship together.** The publish gate aborts if `_build_manifest.json` is missing — so the step that writes it must land in the same change, or the first publish after this aborts (exit 4).

---

## Build order (each item = file:line + the change)

### PHASE 0 — Safety nets *(half day; pure additions, no data-logic change)*
- **0.1 Stop swallowing errors.** `scripts/daily_ingest.ps1:49-53` — replace the `Run` wrapper so it accumulates `$script:FailedSteps`; add `-Critical` to the data-critical calls (`:131` cohort, `:137` mood, `:160` features, `:199` build-site, `:200` editions); at `:218` exit non-zero if any critical step failed. Adapters stay non-fatal.
- **0.2 DB snapshot before mutation.** Insert after `:79`: `VACUUM INTO backups\cfb_rankings_YYYY-MM-DD.db` (via the venv python, not `sqlite3.exe`) + keep newest 7. (~9 GB.) Non-critical (a failed backup shouldn't block).
- **0.3 Build-success precondition for publish.** Replace `:214-216` so section K only runs if `build-site` isn't in `$FailedSteps`.
- **0.4 Healthchecks dead-man's-switch.** Before the final exit: GET `$env:HEALTHCHECK_URL` on clean run, `/fail` otherwise. PS-safe (`; if ($?){...}`, not `&&`). **Needs:** add `HEALTHCHECK_URL=...` to `.env` (auto-loaded by the existing `:30-38` loader).

### PHASE 1 — Can't-ship-bad-data gate *(half day)*
- **1.1 New `manage.py verify-publish-readiness`** — parser after `cli.py:85`, handler after `cli.py:2169`, 3 date helpers after `cli.py:7202`. Uses `db.query_all/query_one` with `:name` params (the `%(name)s`→`:name` normalizer means **never type `now()`** — use `datetime('now', ...)`). Assertions (real columns, probed):
  - HARD: `PRAGMA integrity_check`=ok; `PRAGMA foreign_key_check`=0; `conversation_documents.collected_at_utc` within 2d; ≥200 docs in last 24h.
  - WARN→HARD(`--strict`): non-empty current-period rows in `team_conversation_daily`(as_of_date), `fanbase_mood_weekly`(week_start_date) + mood not all-zero, `team_week_conversation_features`(season,week), `team_cohort_week`(YYYY-WW), `player_week_conversation_features`(season,week).
  - WARN: today's doc count vs trailing-7d median (skip if <3 baseline days — offseason cadence is bursty).
  - Exit `2` on any hard-fail.
- **1.2 Build manifest.** Write `output/site/_build_manifest.json` (built_at, conv_docs count, week key) **only on clean build** — script-side snippet after `daily_ingest.ps1:199` (lower risk than editing the generator).
- **1.3 Publish gate.** `publish_to_vercel.ps1` after `:31`: run `verify-publish-readiness` (abort/exit 3 on fail) + assert manifest exists & <26h (exit 4). Resolve the venv python the way daily_ingest does.

### PHASE 2 — Kill the silent-zero bugs *(~1 day; consistency)*
- **2.1 `resolve_week()`** — new `src/cfb_rankings/common/week.py` (+ `__init__.py`). Canonical key = the **season-week integer** (what producers + the `games` table already use); also returns `week_start_date` (Monday) + `iso_key` whose components are the *same* `(season_year, week)`.
- **2.2 Switch all callers:** `daily_ingest.ps1:64-75` (replace the 3 derived keys with one `resolve_week()` call — fixes the `$Now.Year` vs `$CurSeason` off-season year bug), `weekly_deep.ps1:49-52,61`. Producer/consumer Python bodies need **no change** (they already take `season,week`); only the script-derived values change.
- **2.3 Frozen-map rolling fallback** — `hub_data_compute.py:_week_for_week_start` (~`:22-37`): explicit map → legacy retro → **else `resolve_week(week_start)` → (season_year, week)**, so mood/rivalry/lexicon resolve to the producer's pair instead of raising `ValueError`. *(Recommended add: a `seed-current-offseason-week` upsert so `mine-lexicon`'s `offseason_week_map` JOIN finds the live week too.)*
- **2.4 Zero-row warnings** in `compute_cohort_week` (+ return `rows_read`), `compute_player_week_mood`, `compute_mood_week_from_features`/rivalry/lexicon (add a module logger to `hub_data_compute.py`).
- **2.5 Two fixes:** add `compute-player-season-mood --season $CurSeason` after `daily_ingest.ps1:153`; fix `generate-team-preview-claims` to `--season $CurSeason` (`:196`, was hard-coded calendar 2026).
- **Risk:** pure read-path alignment for the integer-keyed tables (no rewrite/dup). Only `team_cohort_week`/`divergence` (TEXT week) change written key — old rows were ~always 0-cell; new key can't collide (PK). Optional one-time `DELETE FROM team_cohort_week; DELETE FROM team_cohort_divergence_week;` to clear cosmetic staleness. Upserts make re-runs idempotent.

### PHASE 3 — Classifier consistency *(~1 day; the moat-quality fix)*
- **3.1 New `scripts/sentiment_classify_daily.py`** (runs in `.venv-ml`): reuses the staging script's model-load/normalization + the migrate script's backup+UPDATE pattern. Selects docs whose targets aren't yet at `model_version='cardiffnlp-encoder-stack-v1'` **OR** within a rolling 14-day self-heal window; classifies each doc's text once via the 3 **pinned** heads on the 3090; fans labels to all the doc's targets. Snapshots prior values to `cdt_sentiment_backup_vader` (shared with the migrator → `--revert` still works). Idempotent (deterministic argmax + skip-filter + per-chunk commits).
  - **Pinned commit SHAs** (from the HF API `/api/models/<repo>` `.sha`):
    - sentiment `cardiffnlp/twitter-roberta-base-sentiment-latest` → `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`
    - emotion `...-emotion-multilabel-latest` → `30a56d88e47e493f08f93c786d49c526550b55b9`
    - irony `...-irony` → `3bf8f118bdf6b00c99658151ef10c9a0b9afd6bf`
- **3.2 Insertion:** new section **E.5** at `daily_ingest.ps1:156` (after player pipeline, **before** `build-conversation-features` at `:160`), invoked with the `.venv-ml` interpreter explicitly (cross-env); no-op + log if `.venv-ml` absent.
- **3.3 Provenance:** keep the collectors' `vader+lexicon`/`conversation-v1` literals (honest pre-encoder state + they're the selection key). Unify the encoder `model_name` (`cardiffnlp-encoder-stack` backfill vs `...-v1` daily) — pick one. *(Also retrofit the 3 `revision=` pins into `sentiment_classify_staging.py` so future backfills are reproducible.)*
- **3.4 Cross-cron:** the box is authoritative; in `.github/workflows/ingest_daily.yml` disable `build-conversation-features` (line ~109) + `classify-player-sentiment` (~111) so the cloud artifact never aggregates VADER labels. (Optional defense-in-depth: add `AND cdt.model_version='cardiffnlp-encoder-stack-v1'` to the `build_conversation_features` reader.)

### PHASE 4 — Re-enable + verify *(half day)*
- **4.1** Re-enable `CFBIndex-FanintelDaily`/`Weekly` scheduled tasks (safe now). Flip `--strict` on once Phase 2's data is confirmed flowing.
- **4.2** Make the post-publish check gating + content-aware: `smoke_test_live.py --check-freshness` reads the live `_build_manifest.json`, asserts <26h + week-current, alerts via Apprise on fail.

---

## File-change manifest
| File | Phase | Change |
|---|---|---|
| `scripts/daily_ingest.ps1` | 0,2,3 | Run-wrapper+exit; VACUUM snapshot; publish precondition; Healthcheck ping; resolve_week call; E.5 classify; player-season-mood; preview-claims season; manifest writer |
| `scripts/publish_to_vercel.ps1` | 1 | verify-publish-readiness gate + manifest check |
| `src/cfb_rankings/cli.py` | 1,2 | verify-publish-readiness parser+handler+helpers; print rows_read |
| `src/cfb_rankings/common/week.py` (+`__init__.py`) | 2 | new `resolve_week()` |
| `src/cfb_rankings/ingest/hub_data_compute.py` | 2 | map rolling fallback + zero-row warnings + module logger |
| `src/cfb_rankings/cohorts/aggregate.py`, `player_aggregate.py`, `divergence.py` | 2 | zero-row warnings; `rows_read` |
| `scripts/sentiment_classify_daily.py` (new) | 3 | daily encoder classify (.venv-ml) |
| `scripts/weekly_deep.ps1` | 2 | resolve_week for $CurSeason/Monday |
| `.github/workflows/ingest_daily.yml` | 3 | disable cloud feature/sentiment compute |
| `.env` | 0 | `HEALTHCHECK_URL=`, optional `APPRISE_URL=` |

## Decisions needed from you (defaults marked ✅)
1. **Job monitor:** Healthchecks.io **free hosted** ✅ vs self-host. *(Adds `HEALTHCHECK_URL` to `.env`.)*
2. **Alerts to:** ntfy phone push + email ✅ / one only. *(Adds `APPRISE_URL`.)*
3. **DB snapshot retention:** 7 days ✅ / 14.
4. **Encoder `model_name` unification:** standardize both to `cardiffnlp-encoder-stack` ✅ (vs leave the harmless `-v1` split).
5. **Cloud cron:** disable its feature/sentiment compute ✅ (box authoritative) vs keep + add encoder filter.
6. **Build sequencing:** ship Phase 0 → 1 first (safety) ✅, validate a run, then 2 → 3.

## Effort
Phase 0+1 ≈ 1 day → after which **bad/stale/empty data cannot silently ship + you're alerted**. Phase 2+3 ≈ 2 days → consistency/moat. Phase 4 ≈ ½ day → daily auto-run back on. All single-threaded-safe.
