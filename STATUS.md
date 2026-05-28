# Status — Week of 2026-05-28

**Last updated:** 2026-05-28 (initial snapshot)
**Update cadence:** Every Friday
**Format:** Per workstream, four buckets — Last shipped / In flight / Blocked / Next action

> **Read this doc when:** picking up after time away, deciding what to work on this week, prepping a Friday standup. **For deeper context:** [VISION_2026_2027.md](VISION_2026_2027.md) (the 12-month plan), [DECISIONS.md](DECISIONS.md) (why-we-chose), [CLAUDE_CODE_LAUNCH_ROADMAP.md](CLAUDE_CODE_LAUNCH_ROADMAP.md) (operational state).

---

## This week's headline

Planning + capture pass complete. 21 stale docs archived. Five canonical docs structured (VISION + LAUNCH_ROADMAP + DECISIONS + STATUS + specs/). 11 architectural decisions locked, 8 still open. 12 workstream specs scaffolded. Editorial rhythm + autonomous operation model both locked.

**Posture locked:** Compound-ship through 2026, perfect launch summer 2027 (D-002).
**Rhythm locked:** Day-of-week + season-phase cadence (D-019) — see `docs/editorial-rhythm.md`.
**Autonomy locked:** Tiered auto-publish with override (D-020).
**Hero locked:** Homepage + era page designs (D-021).

**Next execution target:** Workstream 01 (Foundation Unblock) — Tier S mechanical fixes.

---

## Per-workstream status

### WS-01 — Foundation unblock
- **Last shipped:** Nothing yet (workstream just defined)
- **In flight:** None
- **Blocked:** Not blocked
- **Next action:** Bucket label fix in `reddit_deep_2026_offseason.yml` (1-token change); commit uncommitted Wave 25 + Milestone A+B + Player Wave-1 work
- **Spec:** [specs/01-foundation-unblock.md](specs/01-foundation-unblock.md)

### WS-02 — Classification + state machinery
- **Last shipped:** N/A — schemas exist (18-archetype taxonomy at `ingest/archetypes.py`, `fanbase_classification` table, `season_narrative_arc` table) but populators have never run
- **In flight:** None
- **Blocked:** D-010 (lock the 10 arc frames) before populator can be built
- **Next action:** Run `seed_taxonomy(db)` + `classify_all_fanbases(db, 2026)` to populate `fanbase_classification` (the existing classifier just needs invocation)
- **Spec:** [specs/02-classification-state.md](specs/02-classification-state.md)

### WS-03 — Editorial profiles to 119
- **Last shipped:** 17 hand-authored profiles in `profiles/*.md` (current state, unchanged)
- **In flight:** None
- **Blocked:** D-011 (profile expansion target ratios) before pipeline scope can be locked
- **Next action:** Decide D-011, then build LLM-draft pipeline for tier-2 profiles
- **Spec:** [specs/03-editorial-profiles.md](specs/03-editorial-profiles.md)

### WS-04 — Historical backfill (pre-2014)
- **Last shipped:** N/A — Phase 4 work
- **In flight:** None
- **Blocked:** D-012 (backfill scope) before scraper plan can be built
- **Next action:** Phase 4 (Jan 2027) — no action this quarter
- **Spec:** [specs/04-historical-backfill.md](specs/04-historical-backfill.md)

### WS-05 — Adapter ecosystem live
- **Last shipped:** Polymarket adapter (160 rows in `source_observations`); Reddit r/CFB collector (9,212 docs); Substack RSS (110 docs)
- **In flight:** None
- **Blocked:** Need `numeric_observations` table (Phase 1) for 7 silent adapters to have a write target
- **Next action:** Create `numeric_observations` migration; redirect Wikipedia/GDELT/SeatGeek/YouTube/Spotify/Kalshi/Bluesky adapters to it; kill `|| echo "skipped"` pattern
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
- **Blocked:** D-015 (publication cadence) before public-facing surface can be designed
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
- 10 OPEN decisions in DECISIONS.md (D-009 through D-018)
- D-013 (refuse list lock) + D-016 (team_coverage migration timing) + D-017 (Octopus policy) can be locked at any time without blocking specific work
- D-009 (Fan Belief naming) + D-010 (arc frames) are good `/octo:debate` candidates

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
