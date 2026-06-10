# Daily Data-Pipeline Reliability — Implementation Plan

**Date:** 2026-06-09. **Plan-first** (nothing here is implemented yet). Fuses the codebase audit (`docs/data_pipeline_reliability_review.md`) with June-2026 deep-research on best-practice tooling for a solo dev on one Windows box. Goal: **correct, complete, consistent data published to live every single day** — the product's moat.

## Guiding verdict (what to adopt vs SKIP)
The research is emphatic: **do NOT over-engineer.** For one linear daily job on one box:
- ✅ **Keep:** the plain PowerShell script + Windows Task Scheduler. Add reliability *layers in-script*, don't change the runner.
- ❌ **Skip — overkill:** Prefect 3 / Dagster (an orchestrator needs PostgreSQL even on one box — extra moving parts for no gain here); Great Expectations (~107 deps, production-grade, steep); a metrics dashboard (per-run JSON + a dead-man's-switch + failure alerts cover observability for one person).
- ⚠️ **Skip on Windows:** Litestream (continuous SQLite replication) — actively maintained but **Windows is explicitly unsupported** ("use at your own risk") + a 2026 replication bug. Use simple daily snapshots instead. (Only revisit if the DB ever moves to WSL2/Linux.)

## The recommended lightweight stack (all free/local)
| Need | Tool/pattern | Why |
|---|---|---|
| Runner | **PowerShell + Task Scheduler** (keep) | right-sized for one daily job |
| Data-quality gate | **Hand-rolled SQL assertions** (Pandera later if wanted) | leanest; hits SQLite directly; fixes freshness/zero-row gaps |
| "Job didn't run" | **Healthchecks.io** dead-man's-switch (free tier / self-host) | catches crash, machine-down, scheduler-off — independent of exit code |
| Failure alerts | **Apprise** (`pip install apprise`) → ntfy/push + email | one call → many destinations |
| DB recoverability | **`VACUUM INTO` daily snapshot + `PRAGMA integrity_check`** + rotation | simple, restore = file copy; right for once-daily writes |
| Daily classifier | **batch step in `.venv-ml`**, Transformers streaming over NEW rows, **pinned `revision=<commit hash>`** | consistent with the backfill; keeps torch out of prod env |

---

## Phased plan (ordered by reliability-gained-per-hour)

### PHASE 0 — Stop the bleeding *(~half day; pure safety, no data-logic change)*
1. **Stop swallowing errors.** Make the `Run` wrapper accumulate failed step labels; `daily_ingest.ps1` exits **non-zero** if any data-critical step failed (keep adapters non-fatal). *(audit #8)*
2. **Build-success precondition.** Capture `build-site`'s exit code; **skip publish** if it failed (today publish runs unconditionally). *(audit 2.3)*
3. **DB snapshot before mutation.** At the top of `daily_ingest.ps1`: `VACUUM INTO backups\cfb_rankings_YYYY-MM-DD.db` + 7–14 day rotation. Bad day becomes recoverable. *(audit 2.4 / research §5)*
4. **Dead-man's-switch.** Healthchecks.io ping at the *end* of a successful run (`...; if ($?) { curl <ping-url> }` — PS-safe, not `&&`). If the daily job ever fails to run, you get pinged. *(audit 2.5 / research §4)*

### PHASE 1 — Can't-ship-bad-data gate *(~half day)*
5. **`verify-publish-readiness` step before publish** — hand-rolled SQL assertions that ABORT the publish on failure:
   - `PRAGMA integrity_check` = ok (+ `foreign_key_check`).
   - **Non-empty:** daily tables (`fanbase_mood_weekly`, `team_week_conversation_features`, cohort/player features) have rows for the current period; mood not all-zero/NULL.
   - **Freshness:** newest `conversation_documents`/feature timestamp within N days; today actually ingested new rows.
   - **Coverage anomaly:** today's ingest row-count vs a trailing 7-day median (alert on a big drop = a 403'd/broken feed). *(audit 2.1 / research §1–2)*
6. **Build manifest.** Write `output/site/_build_manifest.json` (built_at, row counts, week keys) **only on full build success**; publish aborts if it's missing/stale. *(audit 2.2)*
7. **Wire Apprise** so any gate failure fires a push/email immediately.

### PHASE 2 — Fix the silent-zero data bugs *(consistency; ~1 day)*
8. **Single `resolve_week(now) → (season_year, week, week_start, iso_key)`** used by BOTH the script and every handler — kills the 3-vocabulary mismatch that makes cohort/player-mood write 0 rows. *(audit 1.2)*
9. **Rolling fallback** in `_week_for_week_start` so `compute-mood-week`/`rivalry`/`lexicon` stop raising `ValueError` every day past the frozen 2026-04-06 map. *(audit 1.3)*
10. **Read-count assertions** in aggregators (warn/fail loudly on 0 rows read). *(audit 1.2)*
11. Add **`compute-player-season-mood`** to the daily flow; fix **`generate-team-preview-claims`** season (2026→`$CurSeason`). *(audit 1.4)*

### PHASE 3 — Classifier consistency *(the moat-quality fix; ~1 day)*
12. **Daily encoder classify step.** A `.venv-ml` script that classifies NEW `conversation_documents` with the **same pinned CardiffNLP encoder** as the one-time backfill — Transformers streaming/`KeyDataset` over new rows on the RTX 3090 — inserted in `daily_ingest.ps1` *after* collection/tagging, *before* `build-conversation-features`. **Pin `from_pretrained(..., revision="<commit hash>")`.** *(audit 1.1 / research §6)*
13. **Self-heal window:** re-classify a rolling recent window (not just brand-new rows) so any old-VADER stragglers converge to the encoder.
14. **Reconcile the two crons** (local box vs cloud `ingest_daily.yml`) so they don't classify differently — make the box authoritative or upgrade both.

### PHASE 4 — Re-enable + verify *(~half day)*
15. **Re-enable the daily scheduled tasks** (safe now: gates + alerts + backups exist) and watch one full clean run.
16. **Gating, content-aware post-publish check** — `smoke_test_live.py --check-freshness` reads the live `_build_manifest.json` and asserts it's < ~26h old + week-current; alert on fail. *(audit Tier 3)*

---

## Effort + sequencing
- **Phases 0–1 (~1 day total) deliver ~80% of the safety value** — after them, a bad/stale/empty day **cannot silently ship**, and you'll be alerted.
- **Phases 2–3 (~2 days)** deliver the *consistency/correctness* the moat depends on (no more silent-zero surfaces; classifier no longer drifts).
- **Phase 4 (~half day)** turns the daily auto-run back on, now safely.
- All single-threaded-safe; none require parallelizing the build.

## Open decisions for you (small)
- **Healthchecks:** free hosted tier (fastest) vs self-host? (Recommend hosted to start — 1 check, zero maintenance.)
- **Alert destination:** ntfy (phone push, free) vs email vs both? (Recommend ntfy + email.)
- **Snapshot retention:** 7 vs 14 days of DB copies (~1.4 GB each)? (Recommend 7; ~10 GB.)
