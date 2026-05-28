# Status — Week of 2026-05-28

**Last updated:** 2026-05-28 (autonomous execution session 3)
**Update cadence:** Every Friday
**Format:** Per workstream, four buckets — Last shipped / In flight / Blocked / Next action

> **Read this doc when:** picking up after time away, deciding what to work on this week, prepping a Friday standup. **For deeper context:** [VISION_2026_2027.md](VISION_2026_2027.md) (the 12-month plan), [DECISIONS.md](DECISIONS.md) (why-we-chose), [CLAUDE_CODE_LAUNCH_ROADMAP.md](CLAUDE_CODE_LAUNCH_ROADMAP.md) (operational state).

---

## This week's headline

**Planning + capture pass complete. WS-01 Tier S execution begun.** 21 stale docs archived. Five canonical docs structured (VISION + LAUNCH_ROADMAP + DECISIONS + STATUS + specs/). **All 21 architectural decisions LOCKED** (D-001 through D-021 — autonomous best-judgment authorization). 12 workstream specs scaffolded. Editorial rhythm + autonomous operation model + hero design locks all committed. 4 doc commits + 1 WS-01 Tier S code commit shipped (not pushed).

**Posture locked:** Compound-ship through 2026, perfect launch summer 2027 (D-002).
**Rhythm locked:** Day-of-week + season-phase cadence (D-019) — see `docs/editorial-rhythm.md`.
**Autonomy locked:** Tiered auto-publish with override (D-020).
**Hero locked:** Homepage + era page designs (D-021).
**All 18 other decisions:** locked autonomously per user "absolute best judgment" authorization.

**WS-01 Tier S shipped previously (in commits, not pushed):**
- Bucket label fix in `reddit_deep_2026_offseason.yml` ("team" → "fan")
- `cohort_divergence` wiring in `_assemble_player_page_data` + new `player_cohort_divergence_summary` helper in `bets/cohort_divergence.py`
- Chronicle LKG suppression flag in `team_pages/renderer.py` (`_SUPPRESS_LKG_CHRONICLE_OFFSEASON`)

**WS-01 Tier S shipped THIS session (session 3, uncommitted):**
- **Stale spec corrected:** `source_observations` (migration `20260423_01`) already IS the numeric-observations landing table per its docstring + 7 adapters subclassing `NumericSourceAdapter`. Spec 01 + STATUS now reflect this — no parallel `numeric_observations` table created (would violate the "don't propose parallel systems" rule).
- **Adapter loud-fail refactor:** `tools/run_adapter.py` now exits 1 on `AdapterRunResult.status == "error"`, with `--fail-on-empty` / `--fail-on-skipped` opt-in flags (was: unconditional exit 0, swallowed every adapter exception). Dropped `set +e` + bare `echo done` from `ingest_hourly.yml`, `ingest_daily.yml`, `ingest_weekly.yml`; each adapter is now its own step with `continue-on-error: true` for optional/auth-gated adapters. Polymarket alone is hard-fail (it's the known-good baseline).
- **Adapter triage (read-only, 2 parallel agents):** root causes for 0-row adapters identified — wiki_pv / wiki_edits / gdelt_volume / bluesky_curated / bluesky_feeds all depend on `priority_teams` columns (`wiki_team_page`, `google_news_query`, `bluesky_beat_handles`) being seeded. seatgeek / youtube_meta / spotify_charts: secrets ARE wired but seed columns are empty. Fixes captured as Phase 1 follow-up; not landing this session.
- **`team_coverage` consolidation (D-016):** migration `20260602_05_team_coverage.sql` + `scripts/backfill_team_coverage.py`. 213 rows live across 6 tiers (authored 127, blueblood_pedigree 19, priority_intelligence 21, pulse_full 5, pulse_partial 18, structural_identity 23), 155 distinct team slugs. UNIQUE(team_slug, tier) makes backfill idempotent.
- **Code-review pass on the diff:** ran `octo:droids:octo-code-reviewer`, applied P1.2 (google_news_all continue-on-error), P2.1 (drop redundant index), P2.2 (`execute_many` instead of N+1 inserts), P2.4 (remove no-op `--allow-empty` flag); P1.1 (canonical slugify divergence) documented inline as known divergence vs `utils.slugify`.

**Next execution target:** Migrate the 6 cohort-source READER sites (cli.py / reporting.py / chronicle_pattern_e.py / pulse_state.py / archetypes.py) to query `team_coverage` instead of importing Python constants. Once all readers migrate, the import-time constants become dead code and can be removed. Then re-seed the 7 silent adapters' upstream columns in `priority_teams` so they can actually find work to do.

---

## Per-workstream status

### WS-01 — Foundation unblock
- **Last shipped (2026-05-28, session 2):**
  - ✅ Bucket label fix in `reddit_deep_2026_offseason.yml` (commit `0afee863`)
  - ✅ `cohort_divergence` wiring + new `player_cohort_divergence_summary` helper (commit `0afee863`)
  - ✅ Chronicle LKG suppression flag in renderer (commit `0afee863`)
  - ✅ Wave 25 + Player Wave-1 + Milestone A+B previously committed (memory was stale; verified via `git log`)
- **Last shipped (2026-05-28, session 3, UNCOMMITTED):**
  - ✅ Spec correction — `source_observations` already IS the numeric landing table; no parallel migration created
  - ✅ Adapter loud-fail — `tools/run_adapter.py` honors `AdapterRunResult.status` as exit code; 3 ingest workflows refactored
  - ✅ Adapter triage — root causes documented for 6 zero-row adapters (all upstream-seed-data issues, no code bugs)
  - ✅ `team_coverage` table — migration `20260602_05` + `scripts/backfill_team_coverage.py` + 213 live rows
  - ✅ Code review pass — `octo:droids:octo-code-reviewer` ran, P1.2/P2.1/P2.2/P2.4 applied
- **In flight:** Commit of session 3 changes (4 logical commits expected, not pushed)
- **Blocked:** Not blocked
- **Next action:** Migrate 6 cohort-source readers (cli.py / reporting.py / pulse_state.py / archetypes.py / etc.) to query `team_coverage` instead of importing Python constants. Then re-seed `priority_teams` upstream columns for the 7 silent adapters.
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
- **Last shipped:** Polymarket adapter (160 rows in `source_observations`); Reddit r/CFB collector (9,212 docs); Substack RSS (110 docs)
- **Last shipped (session 3):**
  - ✅ Loud-fail unblock — workflows + runner no longer swallow adapter exceptions, so the next cron run will surface actual failure modes
  - ✅ Triage diagnoses captured (Wikipedia/GDELT/Bluesky/YouTube/SeatGeek/Spotify all blocked on missing `priority_teams` seed columns, NOT code bugs; Kalshi false-positive path-bug claim from agent verified-and-rejected)
- **In flight:** None
- **Blocked:** UNBLOCKED — `source_observations` table already exists and is the correct write target; loud-fail now in place
- **Next action:** Re-seed `priority_teams` columns: `wiki_team_page`, `wiki_coach_page`, `google_news_query`, `bluesky_beat_handles`, `seatgeek_team_slug`, `youtube_team_channel_id`. Each seeds an adapter that today writes 0 rows. After re-seed, watch the next 24h of `ingest_hourly` runs in CI to confirm rows land.
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
