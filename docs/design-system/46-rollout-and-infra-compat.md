# 46 — Rollout & Infrastructure-Compatibility Plan

_Status: ROLLOUT PLAN (v1). Created 2026-06-11 from a read-only audit of the live pipeline, migrations, CI guardrails, and the build sequence. Ensures docs 41–45 land cleanly on the running system. No code written; planning only._

---

## 0. Three audit findings that de-risk the whole thing

1. **The linkrot problem is already solved.** `player_archetype_tags` (and the convention across the live schema) keys on **`player_external_id`** — the stable CFBD string id (matches `roster_entries.external_id`), NOT the unstable internal `player_id`. The bible / beats / succession tables MUST key on `player_external_id`, and the changelog survives re-ingest. This was my biggest flagged risk ([[deploy-clobber-root-cause]]) — the codebase already has the answer.
2. **An archetype table already exists.** `player_archetype_tags` (migration 20260525_11) is many-to-many with `confidence`, `is_primary`, `position_group`, `rationale_md`, `model_id`, `source ∈ {auto,human,imported}`. It already backs *positional-role* archetypes (Game-Manager-Plus, Air-Raid-Trigger, Bell-Cow-Back). **Reconciliation needed:** our *narrative* archetypes (Transfer Saga, Quiet Workhorse, Phenom) are a different axis — store them in the same table under a distinct `archetype_slug` namespace (e.g. `narr:transfer-saga`) or a `kind` column, reusing all the plumbing.
3. **There's already a "silent-blank module" guard.** `verify_module_coverage.py` watches derived tables vs a baseline and opens a daily gh issue when one goes dark (the exact failure that bit the stack on 2026-06-11: compute died, sources green, modules blank — [[build-failure-philosophy]]). **Our new narrative tables must be registered in this guard**, or the silent-degradation philosophy will hide a dead engine.

---

## 1. Pipeline insertion points (mapped to `build_publish.ps1`)

The nightly build (9 AM Task Scheduler) runs ordered `Run` blocks. `$ErrorActionPreference="Continue"`; only `-Critical` steps accumulate into `$FailedSteps` → non-zero exit. **Every new narrative compute step is NON-critical** (matches the E.5–E.9 Language-Layer pattern: "failures must NOT abort the publish"). Placement:

| New step | Insert after | -Critical? |
|---|---|---|
| Succession detector (throne-line, Filling-the-Shoes) | E (player pipeline) / F.5 (aura) | **No** |
| Fan-Ledger detectors (keyness lexicons) | E.7–E.9 (Language Layer) | **No** |
| Two-axis + narrative-archetype classifier | after detectors | **No** |
| `player_bible` update + snapshots | after classifier | **No** |
| LLM voice (extend `signature_story`) | H (board builders, near `build-signature-story-board`) | **No** |
| Story-card RENDER | inside `build-site` (step I) | inherits build-site `-Critical` |
| Coverage-guard entries | verify step (J area) | non-critical (opens issue) |

`build-site` **wipes** `output/site` and is `-Critical`; the card renders *inside* it (reporting.py injection), so it ships in the full snapshot — no post-build patching needed (unlike /storylines, /wire which patch in after).

Deterministic detectors that don't need the freshest render can also move to the **enrich** stage of `collect.ps1` (5 AM) to keep `build-site` lean.

---

## 2. Reuse map (what the audit confirmed is already live)

| Need | Live asset | Action |
|---|---|---|
| Stable player anchor | `player_external_id` convention | key all new tables on it |
| Archetype storage | `player_archetype_tags` | extend with a narrative namespace |
| Temporal / why-now | `chronicle_calendar_pressure` (20260524_07) | read for the phase + heartbeat |
| Succession data | `player_depth_chart_2026`, `player_current_status_view` v4, `roster_entries`, `transfer_entries` | feed the throne-line |
| LLM voice loop | `signature_story_generator`, `narrative_arc_generator` (+ caches) | extend with CFB content model |
| Grounding/eval/LKG | `chronicle/{source_trust,evidence_sources,eval,lkg,antislop}` | point the engine at these |
| Offseason projection | `outlook_2026.py` | extend into Hope-Economy mode |
| Discourse + tribal | `conversation_documents/_targets` (`audience_bucket`), `player_week_conversation_features`, keyness engine | ledger detectors + Tribal Lens |
| Silent-dark guard | `verify_module_coverage.py` | register new tables |
| Render slot | `page_data["new_*_html"]` (reporting.py ~L9310–9450) | add `new_story_card_html` |

---

## 3. New schema (migrations)

Follow the live convention exactly: `migrations/YYYYMMDD_NN_description.sql`, `BEGIN TRANSACTION; CREATE TABLE IF NOT EXISTS …; COMMIT;` (idempotent, re-runnable). All keyed on `player_external_id` + `season_year`.

- `narrative_beats` — NEL output (beat_type, summary, 5 salience axes, valence, evidence_json, framing, confidence, source_plane).
- `player_bible` + `player_bible_snapshots` — persistent state + the changelog (identity, permanent/current beats, arc_state, logline, logline_locked_event_id, data_coverage_flag).
- `player_succession` / `throne_line` — role-holder per (team, position, season), predecessor/heir/clock, shoes-read, portal-chain.
- `player_ledger_scores` — the five fan-ledger scores per player-week.
- narrative archetypes → reuse `player_archetype_tags` (namespaced) — *no new table*.

> Migrations are applied by the standard migrate step; new tables are "young" so `verify_module_coverage` won't judge them until they establish a baseline (it only judges established tables — safe rollout).

---

## 4. Render integration + the CSS gotcha

- New self-contained module `player_pages/story_card.py` → `page_data["new_story_card_html"]`, injected once at the top of the player template, with **graceful `""` fallback** (matches the ~30 existing sections; a render error can never blank a page or trip `live_smoke_test`).
- **CSS-injection gotcha (we hit this live this session):** an injected CSS constant must NOT contain its own `<style>…</style>` tags — they close the renderer's outer `<style>` block early and dump raw CSS into the body (the ERA_CHAPTER_CSS bug). The card's CSS constant is **raw CSS only**; the renderer injects it inside the page's `<style>`.
- Use the **locked design tokens** ([[docs/design-system/00-tokens]]) and the Noir sub-brand scope ([[noir-subbrand-direction]]) — do not introduce a 4th font or unscoped dark styles.
- **Snapshot-first id resolution** (the other live bug): resolve `team_id` from the snapshot/slug, not stale profile YAML.

---

## 5. CI / guardrail compatibility

| Guardrail | Risk | Mitigation |
|---|---|---|
| `live_smoke_test.yml` (28 URLs/30min, issue at <95%) | a card render error 500s a player page | graceful `""` fallback; the card is additive |
| `verify_module_coverage.py` | new engine silently goes dark | register the new tables (player-count variant) |
| `verify_world_class_team_pages.py` | only if we add *team* cards (premium-hero guard) | player cards unaffected; defer team cards |
| `chronicle-validate-pr.yml` | tests must pass | add unit tests in the chronicle/pytest pattern (287 tests exist) |
| Full-snapshot clobber ([[deploy-clobber-root-cause]]) | partial render drops sections | card renders inside `build-site` (every player page), not a separate section |
| `publish_to_vercel.ps1` pre-deploy gate (WP-0.6) | aborts a clobbering snapshot | unaffected — card is per-page, not a nav route |

---

## 6. Performance / scale budget

- **Succession detector:** O(teams × positions × seasons) ≈ a few thousand rows — trivial, pure SQL.
- **Ledger detectors:** run over the **relevance-filtered** corpus (use `relevance_ml_score`); bounded by existing keyness cost.
- **LLM voice:** tiered (top-N players) + content-hash regen (already the `signature_story` pattern) — fits the Ollama nightly budget; the long tail stays deterministic-only.
- **Render:** `build-site` already emits ~23k player pages; the card adds per-page deterministic HTML assembly — measure the delta, and push heavy compute to the cache tables (read-only at render time).

---

## 7. Graceful-degradation discipline (non-negotiable, per [[build-failure-philosophy]])

The pipeline degrades **silently** by design — so every new piece needs: (a) non-critical `Run` so it never blocks the deploy, (b) `""` render fallback so a missing input never breaks a page, AND (c) **a coverage-guard entry** so a silent death opens a gh issue. (a)+(b) without (c) is how a dead engine ships green for weeks.

---

## 8. Concurrent-edit safety (right now)

`reporting.py` is being edited in another task window. To minimize merge-conflict surface when this is built later: the card is a **self-contained new file** (`player_pages/story_card.py`) touching `reporting.py` in exactly **two minimal spots** — one `page_data["new_story_card_html"] = …` assignment near the other `new_*_html` keys, and one `{new_story_card_html}` slot in the player template. Everything else lives in the new module + new tables + new migration. Nothing in this session edits code.

---

## 9. Open reconciliations (decide before building)

1. **Archetype namespace** — narrative archetypes in `player_archetype_tags` (namespaced `narr:`) vs a new table. Recommend: reuse, namespaced.
2. **Team cards** — the model (43/44) generalizes to teams, but that trips the world-class-team-page guard; scope v1 to **players only**.
3. **Detector home** — enrich (collect.ps1, 5 AM) vs build (build_publish.ps1, 9 AM). Recommend: deterministic detectors in enrich, LLM voice + render in build.
4. **`player_external_id` everywhere** — confirm every new table keys on it (the anchor that prevents changelog linkrot).

---

## 10. Provenance

Read-only audit 2026-06-11 of `scripts/build_publish.ps1`, `scripts/_pipeline_common.ps1`, `migrations/` (~100 files), `.github/workflows/` (32), `scripts/verify_module_coverage.py`, `migrations/20260525_11_player_archetype_tags.sql`, and `src/cfb_rankings/{chronicle,player_pages}/`. Builds on [[41-player-story-card]], [[42-player-narrative-engine]], [[43-cfb-native-content-model]], [[44-succession-engine]], [[45-integration-with-live-system]].
