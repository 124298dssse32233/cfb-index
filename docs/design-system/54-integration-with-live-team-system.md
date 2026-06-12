# 54 — Integration: How the Team Story Card Fits the Live System ("The Spine")

_Status: INTEGRATION MAP (critique-hardened v2). Created 2026-06-11 from the grounding audit of the running `team_pages/` renderer + pipeline. Answers "how does the crown (docs 50–53) consolidate what we already render?" The headline (review-corrected from a hand-wavy "~60–70%"): **the once-and-thread state rail, the fanbase belief signal, the page mode, the per-program voice, and the LKG/eval machinery already exist; the resolver, the coach source, the ledger detectors, the program bible, and the lens payload are net-new** (§3). Consolidation + elevation, not greenfield. The team analog of [[45-integration-with-live-system]]._

---

## 0. The big realization (and the de-risk)

The crown is not greenfield. The most important architectural pattern Codex proposed — *compute one narrative state, project it to many modules* — **already exists**:

- `render_all_profiled_pages(db, output_dir, today, season_year)` (in `team_pages/renderer.py`) → `render_team_page(...)` resolves `PageState` **exactly once** via `resolve_state(profile, snapshot, today, live_game_meta)` and threads that single object to every downstream module. PageState is NOT recomputed per module. _(Line numbers shift weekly — grep `resolve_state` / `render_all_profiled_pages`, do not trust historical numbers, per [[CLAUDE.md]].)_
- `team_season_narratives` already carries a `state_signature` column — Codex's cache/state-hash, already in the schema.
- LKG already exists: `output/site/_cards_lkg/`, `chronicle_card_cache.is_lkg`, a 14-day staleness badge ([[CLAUDE.md]]).
- `backometer_weekly` already materializes belief + `delta_wow` + hysteresis + `is_low_signal` + `is_offseason`.

So the **ProgramNarrativeState** ([[51-team-narrative-engine]] §9) is `PageState` **promoted** — same once-and-thread pattern, richer payload (lead, claims, standard_gap, freshness, render_tier). The crown is the spine that the page already half-has.

---

## 1. The live pipeline (where everything runs)

```
collect.ps1   (Task Scheduler, ~5:00 AM)
  → CFBD pulls (results, rankings, recruiting, portal, draft, coaches)
  → discourse pulls + enrich (sentiment, keyness, audience_bucket)
  → fan-metric computes (compute-backometer, delusion, rivalry-obsession)

build_publish.ps1   (Task Scheduler, ~9:00 AM)
  → GENERATE: pulse_lede / pulse_themes (Opus), chronicle cards (Ollama), narrative_generator
  → RENDER: reporting.py + team_pages.render_all_profiled_pages → HTML
  → DEPLOY: full-snapshot publish to Vercel
```

The crown slots into **GENERATE** (its resolver + claims + LLM voice write to a cache table) and **RENDER** (the new top-of-page section inside `render_team_page`). Deterministic detectors (coach pressure, ledgers) can live in **collect.ps1 enrich** (5 AM) to keep the build lean.

---

## 2. Module disposition — ABSORB / ORCHESTRATE / LEAVE-ALONE

The danger is adding a 25th module. The crown's job is the opposite: be the spine that makes the other ~24 cohere. Three relationships:

| Live module | Relationship | What changes |
|---|---|---|
| `pulse_lede.py` (Opus fan-voice lede) | **ABSORB** | The crown's logline replaces the pulse lede's visible prose. Pulse *computation* (mood, themes, quotes) becomes an **input** to the crown, not a competing headline. |
| `state_resolver.py` / `PageState` | **ABSORB (extend)** | `page_mode` / `copy_tone` / `accent_key` become **fields in ProgramNarrativeState**. `state_resolver` keeps computing the mode; it stops being the only thing that narrates from it. |
| `pulse_themes.py` / `pulse_state.py` | **ORCHESTRATE** | Feed the discourse plane + the confidence meter; the themes grid stays below as evidence. |
| `aspiration_ladder.py` / `ceiling_floor.py` / `program_prestige_bar.py` | **ORCHESTRATE** | The crown states the next dramatic threshold (the Standard-Gap, [[52-cfb-team-content-model]] §2); the ladder below *explains* it. |
| `rivalry_card.py` / `rivalry_data_loader.py` | **ORCHESTRATE** | The crown references the rival only when rivalry wins/supports the lead; the card owns the detailed history + matchup. |
| `coaching_era.py` | **ORCHESTRATE** | The crown characterizes the regime + hot-seat phase ([[53-program-succession-coaching-carousel]]); the strip owns the chronology. |
| `hero_arc_stripe.py` / `page_tone_strip.py` | **COORDINATE** | The strip stays as the wide visual; the crown reads its mode. Decide identity-row ownership ([[50-team-story-card]] §10). |
| `fanbase_health` / `backometer` / `delusion` / `rent_free` / `recruiting_footprint` / `top_commits` / `roster_reload` / `on_this_day` / `bowl_history` / savant / etc. | **LEAVE ALONE** | Detailed modules stay as the evidence locker below the fold. The crown points down at them; it never duplicates them. |

**The contradiction firewall — scoped honestly (review fix).** The firewall is **not** a promise of global consistency across all ~24 modules (the LEAVE-ALONE modules keep computing their own numbers and aren't migrated). It is narrower and real: the crown owns a small set of **shared typed predicates** (`page_mode`, `lead`, `standard_gap`, `coach_phase`, `aspiration_rung`), and the validator only guarantees that no element which *renders one of those predicates* contradicts the crown. ABSORB/ORCHESTRATE modules consume the predicate from `ProgramNarrativeState`; LEAVE-ALONE modules are exposition that don't assert those predicates at all (a recruiting map can't contradict a coach-phase claim it never makes). Global consistency would require migrating every interpretive module to read claims — out of scope for v1; the firewall covers the predicates that matter.

---

## 3. What is genuinely net-new (the build list)

1. **The crown renderer** — one top-of-page section in `team_pages` + the lead/claims composition ([[50-team-story-card]], [[51-team-narrative-engine]] §9). Consolidates pulse + state + aspiration + a lede into one card.
2. **The Lead Resolver** ([[51-team-narrative-engine]] §3) — deterministic Python over the six characters' level + displacement. `backometer.delta_wow` gives the fanbase character's displacement for free.
3. **`coach_pressure_weekly` + `coaching_tenure`** ([[53-program-succession-coaching-carousel]]) — the protagonist character that has no data today.
4. **Team Fan-Ledger detectors** ([[56-team-fan-ledger-detectors]]) — Standard/Grievance/Grudge/Hope, team-grain, on the existing encoder pass.
5. **`program_bible` + snapshots** ([[51-team-narrative-engine]] §7) — extends `team_season_narratives` + `state_signature` into the unified state + changelog.
6. **The Tribal Lens payload + toggle** ([[51-team-narrative-engine]] §5) — off `audience_bucket` (already collected).

Net-new is mostly **deterministic Python + the coach table**. The LLM layer (pulse/chronicle) is already proven; it just gets the richer ProgramNarrativeState as input.

---

## 4. The smallest shippable slice (v0 — no new LLM, no risk)

A deterministic crown that ships into the live render today:
- a new `team_pages/story_card.py` → injected at the top of `render_team_page`, graceful `""` fallback;
- the **ProgramNarrativeState** built from **existing** signals only: `PageState` (mode/tone), `backometer_weekly` (belief + delta_wow + zone → the lead's displacement + the Flip Point), standings/rankings (the Standard-Gap + path object), and the **Lead Resolver** picking the character from those;
- **one new deterministic detector**: `coach_pressure_weekly` at Level 1–2 only (tenure + Performance Anchor; no LLM, no Level-3 buyout claims yet);
- composition picks the lead; the logline is **templated** from the profile voice (`narrative_generator.py` template mode is already publishable because the voice lives in `profiles/*.md`);
- no model in the loop → zero eval/GPU risk.

This proves the spine on real pages with the existing data. The confident-compiler LLM voice (extending pulse/chronicle) and the full ledger + Level-3 hot-seat layers come after. Does v0 mirror the player v0? Mostly — but the team page's **existing pulse + backometer change the first slice**: the player v0 needed a new succession detector to have anything to say; the team v0 already has belief + mode + standings, so the v0 crown is a *consolidation render*, with the coach detector as the one new signal.

**v0 is not literally "one file" (review fix) — the honest minimum change set:** (1) a new `team_pages/story_card.py` renderer; (2) the deterministic lead-resolver as a small module; (3) the `coaching_tenure` migration + hand-seed; (4) a `coach_pressure_weekly` compute (Level 1–2) wired as a non-critical `Run`; (5) one render-injection line in `render_team_page`; (6) unit tests in the chronicle/pytest pattern; (7) coverage-guard registration. It is *schema-light and LLM-free*, but it is a handful of coordinated changes, not a single file.

---

## 5. Phased build, mapped to the pipeline

| Phase | What | Where it runs |
|---|---|---|
| **0** | `story_card.py` + ProgramNarrativeState from existing signals; templated logline; deterministic lead resolver | RENDER (team_pages) |
| **1** | `coach_pressure_weekly` + `coaching_tenure` (Level 1–2 gates) | enrich (collect.ps1) |
| **2** | Team Fan-Ledger detectors (Standard/Grievance/Grudge/Hope) | enrich |
| **3** | full Lead Resolver (level + multi-window displacement + hysteresis) + claims validator | GENERATE |
| **4** | `program_bible` + snapshots (changelog) + freshness labeling | GENERATE |
| **5** | confident-compiler LLM voice (extend pulse/chronicle) + Tribal Lens payload + Level-3 hot seat | GENERATE (Ollama/Opus) |
| **6** | eval gate + LKG (reuse `chronicle/eval.py`, `_cards_lkg/`) | GENERATE |

Each phase ships standalone and degrades gracefully ([[57-team-dependency-degradation-matrix]]).

---

## 6. Honest risks / watch-items

- **Stable key.** The bible/claims/coach tables must key on the **program slug** (the PROFILED_SLUGS anchor), never a re-ingesting id — the team-side analog of the player `external_id` linkrot fix ([[deploy-clobber-root-cause]]).
- **Full-snapshot clobber.** The crown must render for every profiled team or risk dropping it off prod ([[deploy-clobber-root-cause]]); ship behind the graceful-`""` pattern, inside `build-site`.
- **`verify_world_class_team_pages.py`** hard-fails the build if a real FBS team ships legacy `premium-team-hero` chrome — the crown must be additive to the world-class `team-page` chrome, never replace it in a way that trips this guard.
- **Concurrent edit.** `reporting.py` / team_pages may be edited in another window — the crown is a self-contained new file touching the renderer in one inject spot ([[55-team-rollout-infra-compat]] §8).
- **Two LLM systems.** pulse = cloud Opus; chronicle = local Ollama. The crown must pick a lane per tier ([[58-team-build-philosophy]]) — it does not assume local-only.

## 7. Bottom line

The vision in docs 50–53 lands on a system that already computes its page state once and threads it everywhere, already has belief + mode + standings + pulse + LKG + the calendar. **The first real build is a small, schema-light, LLM-free change set** (§4 — `story_card.py` + the resolver reading existing signals + the coach detector + migration/seed + injection + tests + coverage) that consolidates what's there and proves the spine — everything else layers onto proven infrastructure.

## 8. Provenance

Grounding audit 2026-06-11 of `team_pages/renderer.py` (`render_all_profiled_pages` / `resolve_state` once-and-thread), `backometer.py`/`backometer_weekly`, `team_season_narratives` (state_signature), the Chronicle runtime + `_cards_lkg/`, and `build_publish.ps1`. Mirrors [[45-integration-with-live-system]]. Builds on [[50-team-story-card]], [[51-team-narrative-engine]], [[52-cfb-team-content-model]], [[53-program-succession-coaching-carousel]].
