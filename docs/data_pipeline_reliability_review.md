# Daily Data-Pipeline Reliability Review

**Date:** 2026-06-09. **Goal:** ensure correct, complete, *consistent* data is crunched and published to the live site **every day** — the product's core advantage. Audit was read-only (3 parallel reviewers across pipeline correctness, classification consistency, and delivery/safety).

---

## TL;DR verdict

**The bones are solid; the danger is *silence*.** Almost every data step is idempotent (safe to re-run; no double-counting or corruption). The real risk is **silent staleness / silent partial data sailing to the live site**, because three things combine:
1. Every pipeline step **swallows its own failure** (`daily_ingest.ps1` always exits 0).
2. The **only daily publish gate counts FILES, not DATA** (≥3,500 files) — so an empty/stale/half-built dataset still ships.
3. The renderer **degrades gracefully to "No signal"** instead of failing — so missing data looks like a normal page.

Net: today, a day where the mood/cohort/player computations silently produced **zero rows** would still publish a complete-looking site, and the 30-minute smoke test (HTTP 200 only) would pass. **Nothing would tell us the data went stale.**

---

## ✅ What's already solid (don't touch)
- **Idempotency:** adapters dedupe on `dedup_key`; Reddit uses replace-existing; `build_conversation_features` does clean delete-then-upsert; models use new-run + failure cleanup; `build-site` regenerates per-directory. Re-running a day is safe.
- **Deploy atomicity:** the live alias only flips *after* a healthy upload (`publish_to_vercel.ps1`), so a failed upload leaves the prior site untouched.
- **A strong CI safety stack exists** (`publish_site.yml`: DB-health, team-count, chrome + player-page verification, page-weight) — **but it's wired into the WEEKLY GitHub cron, not the DAILY local path.** Most of the safety lives in the path that doesn't run daily.

---

## 🔴 Tier 1 — DATA CORRECTNESS / CONSISTENCY (the "cool data" itself)

### 1.1 Classifier drift — daily = VADER, our cleaned data = encoder *(the crux)*
Today's sentiment upgrade was a **one-time backfill** (CardiffNLP encoder). But **every live classification path still uses VADER** — single chokepoint `score_sentiment()` at `conversation_utils.py:530`; the encoder (`.venv-ml`) is wired into *nothing*. So **tomorrow's new comments get VADER-classified and drift away from the cleaned historical data.** Provenance literals `"vader+lexicon"` at `conversation.py:133/375/634`.
**Fix:** add a **post-collection daily classify step** using the `.venv-ml` encoder (reuse `scripts/sentiment_classify_staging.py` + the write logic in `migrate_sentiment_to_prod.py:132`), inserted in `daily_ingest.ps1` *after* collection/tagging and *before* `build-conversation-features`. Keeps the heavy ML env disjoint from prod `.venv`. (Alt: env-var backend swap inside `score_sentiment` — but that needs torch in `.venv`.) Also reconcile the two crons (local box vs `ingest_daily.yml`) so they don't classify differently.

### 1.2 Week/season key mismatch — silently zeroes cohort + player-mood
The daily script feeds **three different week vocabularies** into steps that must agree: ISO week (`2026-23`), season-week integer (`~41`, season 2025), and offseason-Monday. `compute-cohort-week`/`compute-divergence`/`compute-player-week-mood` read with the ISO key while the documents were written under season-2025/week-41 → **the query matches ~nothing → 0 rows written, silently.** (`cohorts/aggregate.py:159`, `player_aggregate.py:248`.)
**Fix:** one canonical `resolve_week(now) -> (season_year, week, week_start, iso_key)` helper used by **both** the script and every handler; add an assertion that reads return >0 rows.

### 1.3 Frozen offseason map — mood/rivalry/lexicon throw an error every day right now
`compute-mood-week`/`compute-rivalry-ratios`/`mine-lexicon` resolve the week through `offseason_week_map`, a **hand-authored table that ends 2026-04-06**. For any later date `_week_for_week_start` returns None → **`raise ValueError` every run** (`hub_data_compute.py:137`), swallowed by the harness. So mood/rivalry/lexicon have produced **no new rows since spring**.
**Fix:** rolling fallback in `_week_for_week_start` that maps any unmapped Monday to a computed `(season_year, offseason_week)` instead of returning None (reconciled with 1.2).

### 1.4 Two smaller correctness bugs
- `compute-player-season-mood` is **never run** in the daily flow → offseason player "Room" cards can't populate (`daily_ingest.ps1` section E). **Fix:** add it (idempotent).
- `generate-team-preview-claims` runs with **season 2026** while everything else uses **2025** (`daily_ingest.ps1:196`) → reads an empty layer. **Fix:** use `$CurSeason` consistently.

---

## 🟠 Tier 2 — SAFETY (can't-ship-garbage)

### 2.1 No data-quality gate before publish *(CRITICAL)*
The only daily gate is file-count ≥3500 (`publish_to_vercel.ps1:31`). A "complete but empty-data" build passes it and goes live.
**Fix:** before deploy, run a `verify-publish-readiness` check — reuse the existing `verify_db_artifact_healthy.py` (row-count floors) **plus** assert the daily tables are non-empty for the current week (`fanbase_mood_weekly`, cohort, player features) and mood isn't all-zero. Abort the publish on failure.

### 2.2 No freshness assertion — stale data can ship forever *(CRITICAL)*
Nothing checks the data is *today's*. If ingestion silently no-ops (expired key, bot-block, box asleep), the site re-publishes last week's data at HTTP 200 indefinitely (this exact "stale 7+ days" bug is documented).
**Fix:** write `output/site/_build_manifest.json` (built_at, latest mood/cohort week, row counts) **only on full build success**; post-publish, fetch it from the live alias and assert built_at < ~26h and week keys are current.

### 2.3 build-site success isn't a precondition for publish *(HIGH)*
`build-site` failure is swallowed (`daily_ingest.ps1:52`) and publish runs **unconditionally** (`:214`). A half-built tree that still has ≥3500 files will deploy.
**Fix:** capture `build-site` exit code; skip publish if non-zero. Use the manifest sentinel (2.2) as the "fully built" proof.

### 2.4 No DB backup before daily in-place mutation *(HIGH)*
`cfb_rankings.db` is mutated in place across ~9 sections with no snapshot → a corrupting day is locally unrecoverable.
**Fix:** at the top of `daily_ingest.ps1`, `Copy-Item` the DB to `backups/cfb_rankings_YYYY-MM-DD.db` with 7–14 day rotation. Cheap insurance.

### 2.5 No alerting on the daily path *(HIGH)*
A failed/empty daily run leaves only a log file; nothing notifies. (`notify_failure.yml` exists but only CI uses it.)
**Fix:** on any gate failure / non-zero build, open a GitHub issue (`gh issue create --label automation-failure`, pattern already in `emergency_publish.ps1`) or push/email.

---

## 🟡 Tier 3 — OBSERVABILITY (know it's right)
- Make the post-publish health check **gating + content-aware** (run `smoke_test_live.py --check-chrome --check-freshness` inline; abort/alert on fail). Today it's one non-gating `HEAD`.
- Surface **partial coverage**: compare today's `conversation_documents` insert count to the trailing median; warn/alert on a big drop (bulk adapters currently always exit 0, masking 403'd feeds).
- Make the `Run` wrapper **accumulate failed steps** and exit non-zero so Task Scheduler "green" actually means green.
- Tighten/relocate the **broken-link audit** into the daily readiness gate (current FAIL threshold of 500 is very permissive).

---

## Recommended order of implementation
1. **DB backup + build-success-precondition + freshness manifest** (2.4, 2.3, 2.2) — small, pure safety, immediately makes "a bad day can't ship/can be recovered" true.
2. **Data-quality gate before publish** (2.1) — reuse existing verifier + non-empty assertions.
3. **Encoder into daily classification** (1.1) — the consistency crux.
4. **Single `resolve_week()` + offseason-map fallback + read-count assertions** (1.2, 1.3) — stops the silent-zero pipelines.
5. **Player-season-mood + preview-claims season fix** (1.4).
6. **Alerting + gating smoke test + coverage/link checks** (2.5, Tier 3).

Each is a focused, testable change. None require parallelizing the build (kept single-threaded for determinism/safety, per owner decision).
