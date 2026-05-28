# Status — Week of 2026-05-28

**Last updated:** 2026-05-28 (autonomous execution session 3)
**Update cadence:** Every Friday
**Format:** Per workstream, four buckets — Last shipped / In flight / Blocked / Next action

> **Read this doc when:** picking up after time away, deciding what to work on this week, prepping a Friday standup. **For deeper context:** [VISION_2026_2027.md](VISION_2026_2027.md) (the 12-month plan), [DECISIONS.md](DECISIONS.md) (why-we-chose), [CLAUDE_CODE_LAUNCH_ROADMAP.md](CLAUDE_CODE_LAUNCH_ROADMAP.md) (operational state).

---

## This week's headline

**WS-01 Tier S DONE. WS-05 Adapter ecosystem largely unblocked.** 21 stale docs archived. Five canonical docs structured. All 21 decisions LOCKED. 7 commits pushed to master in autonomous session 3. The original 3-part ask (`numeric_observations` table / 7-adapter loud-fail triage / `team_coverage` consolidation) all shipped; spec self-corrected the "numeric_observations doesn't exist" diagnosis (it does — `source_observations` since April 2026). Empirical adapter unblock: source_observations 160→333 rows + conversation_documents +8,413 Bluesky posts + CI run unlocked YouTube 1,143 rows.

**Posture locked:** Compound-ship through 2026, perfect launch summer 2027 (D-002).
**Rhythm locked:** Day-of-week + season-phase cadence (D-019) — see `docs/editorial-rhythm.md`.
**Autonomy locked:** Tiered auto-publish with override (D-020).
**Hero locked:** Homepage + era page designs (D-021).
**All 18 other decisions:** locked autonomously per user "absolute best judgment" authorization.

**WS-01 Tier S shipped previously (in commits, not pushed):**
- Bucket label fix in `reddit_deep_2026_offseason.yml` ("team" → "fan")
- `cohort_divergence` wiring in `_assemble_player_page_data` + new `player_cohort_divergence_summary` helper in `bets/cohort_divergence.py`
- Chronicle LKG suppression flag in `team_pages/renderer.py` (`_SUPPRESS_LKG_CHRONICLE_OFFSEASON`)

**Session 3 commit log (all pushed to master):**
- `e2e23bfaaa7` WS-01 Tier S: adapter loud-fail + per-step granularity
- `47984a4f7a3` WS-01 Tier S: team_coverage table consolidation (D-016)
- `04903727907` docs: correct stale numeric_observations diagnosis
- `ea147a7e6a0` test: unblock pytest collection (1306 tests now collect, was 0)
- `a606cb5afb7` docs(STATUS): adapters unblocked, 173 new rows
- `ba66d377434` WS-05: BLUESKY_DEEP_PAGES 1→5 (5x backfill depth)
- `7bdb5fdfab3` WS-05: fix 3 bugs surfaced by adapter loud-fail (gdelt throttle / bluesky_feeds dead URI / kalshi offseason skip)

**Empirical wins (validated by 2026-05-28 18:40 UTC CI dispatch):**
- `source_observations`: 160 → 333+ rows (+5 numeric sources writing)
- `conversation_documents`: +8,413 Bluesky posts (Nov 2023 → today; 2.5 years history)
- YouTube unlocked in CI: 1,143 rows of CFB video metadata
- Loud-fail UI working: each adapter is now a visible per-step in Actions

**Next execution target:** Two items now need a user decision before more code lands (see WS-01 → Blocked): (1) D-016 reader migration is not the simple constant-deletion the spec implied — there's a circular bootstrap dependency, so it needs a corrected, signed-off interpretation; (2) `gdelt_volume` 0-rows is fetch-level IP rate-limiting (429), fixable only via a residential-IP runner — an infra tradeoff. `seatgeek` 0-rows verification remains open and is unblocked.

---

## Per-workstream status

### WS-01 — Foundation unblock
- **Last shipped (2026-05-28, session 2):**
  - ✅ Bucket label fix in `reddit_deep_2026_offseason.yml` (commit `0afee863`)
  - ✅ `cohort_divergence` wiring + new `player_cohort_divergence_summary` helper (commit `0afee863`)
  - ✅ Chronicle LKG suppression flag in renderer (commit `0afee863`)
  - ✅ Wave 25 + Player Wave-1 + Milestone A+B previously committed (memory was stale; verified via `git log`)
- **Last shipped (2026-05-28, session 3, PUSHED):**
  - ✅ Spec correction — `source_observations` already IS the numeric landing table; no parallel migration created (commit `04903727907`)
  - ✅ Adapter loud-fail — `tools/run_adapter.py` honors `AdapterRunResult.status` as exit code; 3 ingest workflows refactored (commit `e2e23bfaaa7`)
  - ✅ Adapter triage — root causes documented; smoke test post-seed proved diagnosis: source_observations went 160→333 rows, bluesky alone added 2,163 rows
  - ✅ `team_coverage` table — migration `20260602_05` + backfill script + 213 live rows / 155 distinct slugs (commit `47984a4f7a3`)
  - ✅ Test infrastructure unblocked — 3 broken test files fixed (syntax error + 2 importorskip guards); pytest collects 1,306 tests (was: 0) (commit `ea147a7e6a0`)
  - ✅ Code review pass — `octo:droids:octo-code-reviewer` ran, P1.2/P2.1/P2.2/P2.4 applied
  - ✅ `priority_teams` seeded — root-cause fix for 6 silent adapters
- **In flight:** None
- **Blocked — two items need a user decision (session 4, 2026-05-28):**
  1. **D-016 reader migration is NOT a simple "delete constants → readers query table".** Investigation found two hard constraints the locked decision's options didn't anticipate:
     - **Circular dependency:** `scripts/backfill_team_coverage.py` *imports* `STRUCTURAL_PRIMARIES` / `BLUEBLOOD_PROGRAMS` / `TOP_ENTITIES_*` / `PROFILED_SLUGS` to *populate* `team_coverage`. If those constants instead read from the table, the backfill can never bootstrap. → Those constants must remain the authoring source of truth; `team_coverage` is a *derived read surface*, not a replacement.
     - **No `db` in scope:** `classify_team()` (archetypes.py:421) is a pure function with no DB handle; migrating its lookups would ripple a `db` arg through all callers and break test purity.
     - **`team_coverage` is currently an orphan:** nothing reads it, nothing refreshes it (backfill is invoked by no build/workflow). Verified perfect-mirror of authoring sources today (struct 23=23, blueblood 19=19, 213 rows total) but it will silently drift the moment a constant changes, because `INSERT OR IGNORE` never removes rows for *deleted* slugs.
     - **Feasible completion (needs sign-off, since D-016 is LOCKED):** keep authoring constants; wire the idempotent backfill (with `--delete-first` full-refresh semantics) into the build so the table stays current; provide a thin `coverage.py` read helper *only if* a genuine cross-cutting reader appears (none exists today — building it now is premature). The literal "all consumers query the unified table" wording is partially infeasible.
  2. **`gdelt_volume` 0-rows root cause = fetch-level rate-limiting, NOT a parse bug.** Live probe from local IP returns HTTP 429; GDELT aggressively throttles datacenter/cloud IP ranges, so GitHub-hosted runners hit the same wall. Parse hardening won't help. Durable fix is an infra tradeoff: run `gdelt_volume` from the self-hosted Alienware runner (residential IP) vs. accept it as degraded/offseason-low-priority. Desktop-uptime fragility makes this your call.
- **Next action (pending the two decisions above):** if D-016 reinterpretation is approved → wire backfill into build + document corrected understanding in DECISIONS. If gdelt residential-IP is approved → move the daily gdelt step to `[self-hosted, alienware]`. Separately, `seatgeek` 0-rows still unverified (offseason-expected vs. genuine bug).
- **Spec:** [specs/01-foundation-unblock.md](specs/01-foundation-unblock.md)

### WS-02 — Classification + state machinery
- **Last shipped:** N/A — schemas exist (18-archetype taxonomy at `ingest/archetypes.py`, `fanbase_classification` table, `season_narrative_arc` table) but populators have never run
- **In flight:** None
- **Blocked:** UNBLOCKED — D-010 (10 arc frames) now LOCKED. Ready to start.
- **Next action:** Run `seed_taxonomy(db)` + `classify_all_fanbases(db, 2026)` to populate `fanbase_classification` (the existing classifier just needs invocation). Then build arc-frame populator per D-010.
- **Spec:** [specs/02-classification-state.md](specs/02-classification-state.md)

### WS-03 — Editorial profiles to 119
- **Last shipped:** 17 hand-authored profiles in `profiles/*.md` (current state, unchanged)
- **In flight:** None
- **Blocked:** UNBLOCKED — D-011 LOCKED (17 + 25 + 77). Voice LoRA training (D-014) feeds into this.
- **Next action:** Phase 2 (Aug 2026) — build LLM-draft pipeline for the 25 editorial_assisted profiles + voice_validator integration
- **Spec:** [specs/03-editorial-profiles.md](specs/03-editorial-profiles.md)

### WS-04 — Historical backfill (pre-2014)
- **Last shipped:** N/A — Phase 4 work
- **In flight:** None
- **Blocked:** UNBLOCKED — D-012 LOCKED (1936-2013 AP poll era first). Still deferred to Phase 4 by sequencing.
- **Next action:** Phase 4 (Jan 2027) — no action this quarter
- **Spec:** [specs/04-historical-backfill.md](specs/04-historical-backfill.md)

### WS-05 — Adapter ecosystem live
- **Last shipped (session 3, all PUSHED):**
  - ✅ Loud-fail unblock — runner + 3 workflows refactored; per-adapter steps visible in CI UI
  - ✅ `priority_teams` seeded — root cause of 6 silent adapters was empty table
  - ✅ Bluesky deep-pagination — default `BLUESKY_DEEP_PAGES` 1→5; local backfill 2,163→6,250 rows; CI run produced 5,927 fresh rows
  - ✅ 3 surfaced bugs fixed in commit `7bdb5fdfab3`:
    - `gdelt_volume`: throttle 1.5s→5s, backoff 2s→30s
    - `bluesky_feeds`: wired `seeds/bluesky_feeds.yaml` override + dropped dead default URI
    - `kalshi`: all 15 CFB tickers flagged `needs_research:true` (offseason; markets closed); loader honors the flag
  - ✅ **CI workflow_dispatch run (2026-05-28 18:40 UTC, all steps green):**
    - polymarket: 10 rows ✓
    - bluesky_curated: 5,927 rows ✓
    - **youtube_meta: 1,143 rows** ✓ (auth-gated unlock via Actions secret)
    - kalshi: empty (clean — offseason skip, no warnings)
    - bluesky_feeds: empty (clean — no feeds curated yet)
    - gdelt_volume: empty (still 0 rows even with new throttle; needs deeper debug — payload-shape change suspected)
    - seatgeek: empty (likely no events in offseason; needs verification)
- **In flight:** None
- **Blocked:** Not blocked
- **Next action:** `gdelt_volume` 0-rows is now diagnosed — fetch-level HTTP 429 (GDELT throttles datacenter IPs; not a payload/parse issue). Fix is residential-IP runner (infra decision, see WS-01 → Blocked). `seatgeek` 0-rows still needs offseason-vs-bug verification (unblocked).
- **Spec:** [specs/05-adapter-ecosystem.md](specs/05-adapter-ecosystem.md)

### WS-06 — Page archetype expansion (Coach / Game / Rivalry / Conference)
- **Last shipped:** Conference index pages (basic). Rivalry card module exists for in-team-page rendering.
- **In flight:** None
- **Blocked:** WS-02 must populate archetype data before Coach pages can render archetype-driven sections; coaches table doesn't exist yet
- **Next action:** Build `coaches` table from CFBD coaches data (we already ingest CFBD Coaches 2018-2024); populate `coaching_changes` as diffs
- **Spec:** [specs/06-page-archetypes.md](specs/06-page-archetypes.md)

### WS-07 — Era pages (CFP three-act)
- **Last shipped:** N/A
- **In flight:** None
- **Blocked:** WS-03 (profiles for the top-25) + structural data validation across all 13 CFP seasons
- **Next action:** Design the 6-section era page template; build for Alabama first as the prototype
- **Spec:** [specs/07-era-pages-cfp.md](specs/07-era-pages-cfp.md)

### WS-08 — Chart vocabulary expansion (6 → 9)
- **Last shipped:** Locked vocab at 6 types (`docs/design-system/31-chart-vocabulary.md`)
- **In flight:** None
- **Blocked:** Not blocked
- **Next action:** Implement Sankey component (portal flows) as the first new type; add to `charts/__init__.py` whitelist; update lint
- **Spec:** [specs/08-chart-vocabulary.md](specs/08-chart-vocabulary.md)

### WS-09 — Calibration ledger
- **Last shipped:** `confidence_calibration` table exists with 5 rows; design doc `docs/design-system/33-confidence-signaling.md` locked
- **In flight:** None
- **Blocked:** UNBLOCKED — D-015 LOCKED (continuous writes, Sunday-evening public summary, per-game override).
- **Next action:** Build `prediction_ledger` table + writer instrumentation across chips; outcome resolver runs weekly
- **Spec:** [specs/09-calibration-ledger.md](specs/09-calibration-ledger.md)

### WS-10 — Cross-archetype + entity graph
- **Last shipped:** N/A
- **In flight:** None
- **Blocked:** WS-06 (Coach/Game/Rivalry/Conference pages exist) before cross-archetype nav strip has anywhere to link
- **Next action:** Phase 4 work
- **Spec:** [specs/10-cross-archetype-entity-graph.md](specs/10-cross-archetype-entity-graph.md)

### WS-11 — Mobile + a11y + performance
- **Last shipped:** Static-site generator produces fast pages; mobile-renders mostly work
- **In flight:** None
- **Blocked:** Not blocked (can audit current state anytime)
- **Next action:** Phase 5 work (March 2027). Until then: enforce mobile-rendering checks in PR review.
- **Spec:** [specs/11-mobile-a11y-perf.md](specs/11-mobile-a11y-perf.md)

### WS-12 — Editorial cadence
- **Last shipped:** Daily/Wire/Mailbag pipelines running on cron (verified live per LAUNCH_ROADMAP). 8 active storyline threads. 32 storyline chapters.
- **In flight:** Storyline chapters have slipped to ~5 weeks since last update (April 21-23 was last)
- **Blocked:** Not blocked
- **Next action:** Add chapter-cadence alert. Build data-driven storyline candidate queue (see WS-02 transition events → storyline candidates).
- **Spec:** [specs/12-editorial-cadence.md](specs/12-editorial-cadence.md)

---

## Cross-cutting items

### Local LLM stack
- **Current:** Ollama running Mistral-Nemo 12B + Qwen3 8B on Alienware A1250
- **Target:** vLLM (FP8 + EAGLE-3) + Ollama coexistence per D-005
- **Next action:** Two-week setup sprint per VISION § 11 build order. Day 1-2: vLLM Blackwell install. Day 3-4: Qwen3-30B-A3B MoE benchmark.

### Chronicle cards
- **Current:** 189 LKG cards live on team pages, all repetitive Polymarket variations
- **Target:** Suppress immediately (D-004); regenerate after Phase 1 evidence diversity
- **Next action:** Run suppression patch (mark all `is_lkg=0` in `chronicle_card_cache`)

### Uncommitted work
- **Risk:** Wave 25 + Milestone A+B + Player Wave-1 work is uncommitted in working tree (per memory notes)
- **Next action:** Commit in 2-3 logical PRs this week before any other work touches those files

### Decisions waiting
- **0 OPEN decisions** — all 21 entries LOCKED as of 2026-05-28 autonomous session.
- New decisions get logged as encountered.
- User can request `/octo:debate` to challenge any LOCKED entry; new entry would supersede.

---

## What's NOT in scope this week

- Any code changes to `reporting.py` beyond the bucket label fix
- Any new chart types
- Any new page archetypes
- Any pre-2014 data backfill
- Any vLLM installation work (next week)

---

## Last week's deltas (for next Friday's snapshot)

This is the initial snapshot. Next week's STATUS.md will compare to this baseline:
- Workstreams that moved from Blocked → Next action
- Workstreams that shipped something
- Decisions that moved from OPEN → LOCKED
- Doc-archive count changes

---

## How to update this doc

Each Friday:
1. Re-read the per-workstream status; update each bucket
2. Move completed items from "In flight" to "Last shipped"
3. Move things that newly start from "Next action" to "In flight"
4. Add new blockers as they emerge
5. Update the "This week's headline" with the one-sentence summary
6. Commit the changes
