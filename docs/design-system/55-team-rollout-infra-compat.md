# 55 — Team Story Card: Rollout & Infrastructure-Compatibility Plan

_Status: ROLLOUT PLAN (critique-hardened v2). Created 2026-06-11 from a read-only audit of the live team-page pipeline, migrations, CI guardrails, and the build sequence. v2 fixes the coverage-guard key contradiction (tables carry BOTH `program_slug` and `team_id`, §0/§3) and the bible-storage overclaim (§9). Ensures docs 50–54 land cleanly. No code written; planning only. The team analog of [[46-rollout-and-infra-compat]]._

---

## 0. Three audit findings that de-risk the rollout

1. **The coverage guard is team-keyed — so the new tables carry BOTH keys (review fix).** `verify_module_coverage.py` counts derived tables by `team_id` and opens a daily gh issue when one goes dark ([[build-failure-philosophy]]). The narrative tables must key on the stable **`program_slug`** (the linkrot fix, finding 3) — but `slug`-only tables would be invisible to a `team_id`-counting guard. Resolution: **every new table carries both `program_slug` (the stable narrative key) AND `team_id` (for the guard + standard joins).** `program_slug` is the canonical key for narrative continuity; `team_id` is a denormalized convenience column kept in sync at write time. Then the guard works day one with no join.
2. **The state-thread pattern is already proven.** `resolve_state` runs once and threads `PageState` to all modules ([[54-integration-with-live-team-system]] §0). ProgramNarrativeState is the same shape, richer — no new architectural risk, just a bigger payload on a proven rail.
3. **The stable key already exists as a convention.** Profiled programs are keyed on the **slug** (`PROFILED_SLUGS`, discovered from `profiles/*.md` at import). All new narrative tables key on `program_slug` (+ `season_year` + `week`), so the bible/changelog survive re-ingest — the team-side answer to the player `external_id` linkrot fix ([[deploy-clobber-root-cause]]).

---

## 1. Pipeline insertion points (mapped to `build_publish.ps1`)

The nightly build runs ordered `Run` blocks; `$ErrorActionPreference="Continue"`, only `-Critical` steps accumulate into `$FailedSteps`. **Every new narrative compute step is NON-critical** (matches the Language-Layer E.5–E.9 pattern and the graceful-degradation philosophy — failures must NOT abort the publish, [[build-failure-philosophy]]).

| New step | Insert after | -Critical? |
|---|---|---|
| `compute-coach-pressure` (tenure + anchor + gates) | the fan-metric block (near `compute-backometer`) | **No** |
| Team Fan-Ledger detectors | after the discourse/keyness enrich | **No** |
| Lead Resolver + claims + `program_bible` update | after detectors | **No** |
| Confident-compiler LLM voice (extend pulse/chronicle) | GENERATE (near pulse/chronicle) | **No** |
| Crown RENDER | inside `team_pages.render_all_profiled_pages` (the `build-site` step) | inherits `build-site` `-Critical` |
| Coverage-guard entries | verify step | non-critical (opens issue) |

`build-site` **wipes** `output/site` and is `-Critical`; the crown renders *inside* `render_team_page`, so it ships in the full snapshot — no post-build patching (the crown is per-page, not a nav route, so it is not exposed to the `/wire`/`/storylines` partial-render clobber, [[deploy-clobber-root-cause]]). Deterministic detectors that don't need the freshest render can move to **collect.ps1 enrich** (5 AM) to keep `build-site` lean.

---

## 2. Reuse map (what the audit confirmed is live)

| Need | Live asset | Action |
|---|---|---|
| Stable program anchor | `PROFILED_SLUGS` / `profiles/*.md` slug | key all new tables on `program_slug` |
| State-thread rail | `resolve_state` → `PageState` (once per render) | extend into ProgramNarrativeState |
| State-hash / cache | `team_season_narratives.state_signature` | reuse as the bible signature |
| Belief + displacement | `backometer_weekly` (score/zone/delta_wow/is_low_signal/is_offseason) | the fanbase character + Flip Point + floor |
| Calendar / why-now | `chronicle_calendar_pressure` | lead eligibility + freshness budget |
| Discourse + tribal | `team_conversation_daily`, `pulse_themes`, `audience_bucket`, keyness | ledger detectors + Tribal Lens |
| LLM voice loop | `pulse_lede` (Opus), chronicle (Ollama), `narrative_generator` | extend with the content model |
| Grounding / eval / LKG | `chronicle/{source_trust,evidence_sources,eval,lkg,antislop}`, `_cards_lkg/` | point the engine at these |
| Silent-dark guard | `verify_module_coverage.py` (team-keyed) | register the new tables |
| Render slot | `render_team_page` section assembly | add the crown at the top |

---

## 3. New schema (migrations)

Follow the live convention exactly: `migrations/YYYYMMDD_NN_description.sql`, `BEGIN TRANSACTION; CREATE TABLE IF NOT EXISTS …; COMMIT;` (idempotent). All carry **`program_slug` (canonical) + `team_id` (denormalized, for the coverage guard, §0.1)** + `season_year` / `week`.

- `coaching_tenure` — hand-seeded (slug, coach, start_year, contract_through, buyout_usd, source_url). ~119 rows ([[53-program-succession-coaching-carousel]] §3).
- `coach_pressure_weekly` — pressure score, phase, evidence_level, components_json, the three gates' state.
- `team_ledger_scores` — Standard/Grievance/Grudge/Hope scores per program-week ([[56-team-fan-ledger-detectors]]).
- `program_bible` + `program_bible_snapshots` — persistent state + the changelog (identity, lead_state, logline, logline_locked_event_id, standard_gap, data_coverage_flag). May extend `team_season_narratives` rather than add a table — reconcile (§9).

> New tables are "young," so `verify_module_coverage` won't judge them until they establish a baseline — safe to register from day one.

---

## 4. Render integration + the CSS gotcha

- New self-contained module → injected once at the top of `render_team_page`, with **graceful `""` fallback** (matches the existing world-class sections; a render error can never blank a page or trip `live_smoke_test`).
- **CSS-injection gotcha (hit live before — the ERA_CHAPTER_CSS bug):** an injected CSS constant must NOT contain its own `<style>…</style>` tags — they close the renderer's outer `<style>` early and dump raw CSS into the body. The crown's CSS constant is **RAW CSS only**.
- **Tribal-Lens delivery:** one inline `application/json` payload + a sub-1 KB toggle script mutating `data-story-field` text targets ([[51-team-narrative-engine]] §5). One card DOM tree, not three.
- Use the **locked tokens** + Noir scope ([[00-tokens]], [[40-noir-subbrand]]) — no 4th font, no unscoped dark styles.
- **Snapshot-first id resolution:** resolve `team_id` from the snapshot/slug, not stale profile YAML (the other live bug).

---

## 5. CI / guardrail compatibility

| Guardrail | Risk | Mitigation |
|---|---|---|
| `verify_world_class_team_pages.py` (fails build on legacy `premium-team-hero` chrome) | the crown alters hero chrome and trips it | the crown is **additive** to the `team-page` world-class chrome; never reintroduces premium-hero markup |
| `live_smoke_test.yml` (28 URLs/30min, issue <95%) | a crown error 500s a team page | graceful `""` fallback; crown is additive |
| `verify_module_coverage.py` (team-keyed) | a new detector silently goes dark | register `coach_pressure_weekly` / `team_ledger_scores` / `program_bible` |
| Full-snapshot clobber ([[deploy-clobber-root-cause]]) | partial render drops the crown | renders inside `build-site` across all profiled pages |
| `chronicle-validate-pr.yml` | tests must pass | add unit tests in the chronicle/pytest pattern (287 exist) |
| DB-artifact health guards (19 workflows) | unaffected — box-native compute | crown computes against the canonical box DB |

---

## 6. Performance / scale budget

- **Resolver + detectors:** O(teams × characters × windows) ≈ a few thousand rows over ~119 teams — trivial, pure SQL/Python.
- **Coach pressure:** 14-day rolling keyness over the relevance-filtered corpus — bounded by the existing keyness cost.
- **LLM voice:** ~119 pages is **orders of magnitude** below the ~69k player pages — the GPU budget is barely a constraint ([[58-team-build-philosophy]]). State-signature regen (already the pattern) keeps it to "who changed today."

---

## 7. Graceful-degradation discipline (non-negotiable)

Per [[build-failure-philosophy]], the pipeline degrades **silently** by design — so every new piece needs the trio: **(a)** non-critical `Run` (never blocks the deploy), **(b)** `""` render fallback (never breaks a page), AND **(c)** a coverage-guard entry (a silent death opens a gh issue). (a)+(b) without (c) is how a dead engine ships green for weeks.

---

## 8. Concurrent-edit safety (right now)

A separate window is editing the live site. To minimize merge surface: the crown is a **self-contained new file** touching `team_pages/renderer.py` in exactly **one minimal spot** (the crown section assignment in `render_team_page`). Everything else is the new module + new tables + new migration + new `coaching_tenure` seed. **This session writes only docs — no code, no DB, no `output/site/**`.**

---

## 9. Open reconciliations (decide before building)

1. **Bible storage** — extend `team_season_narratives` (+ `state_signature`) vs a new `program_bible` table. Recommend: a new table for the lead_state/claims, reusing `state_signature` semantics.
2. **Detector home** — enrich (collect.ps1, 5 AM) vs build (9 AM). Recommend: deterministic detectors in enrich, LLM voice + render in build.
3. **Indexed lens** — National-as-crawlable-H1 vs Home ([[50-team-story-card]] §10). Recommend: index National.
4. **Institution character data** — how far to build the rev-share/NIL-collective signal vs discourse-only v1 ([[52-cfb-team-content-model]] §8).

## 10. Provenance

Read-only audit 2026-06-11 of `team_pages/renderer.py`, `build_publish.ps1`, `migrations/`, `.github/workflows/`, `verify_module_coverage.py`, `verify_world_class_team_pages.py`, `backometer.py`. Mirrors [[46-rollout-and-infra-compat]]. Builds on [[50-team-story-card]]…[[54-integration-with-live-team-system]].
