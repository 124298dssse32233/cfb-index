# Status — Week of 2026-05-28

**Last updated:** 2026-05-28 (autonomous execution session 9)
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

**Next execution target:** Both prior blockers RESOLVED (session 4, 2026-05-28): (1) D-016 closed via the corrected derived-read-surface mechanism — `team_coverage` is auto-synced from the authoring constants on every build via `coverage.sync_team_coverage(db)`, guarded by a CI drift test; (2) `gdelt_volume` moved to the self-hosted Alienware runner (residential IP) on a daily cadence in `ingest_gdelt_daily.yml`. `seatgeek` 0-rows verification remains the only open WS-01 item and is unblocked.

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
- **Last shipped (2026-05-28, session 4):**
  - ✅ **D-016 CLOSED** — both prior blockers resolved with the corrected mechanism. Authoring constants + `profiles/*.md` stay the source of truth; `team_coverage` is a *derived read surface* re-synced from those sources on every build via `coverage.sync_team_coverage(db)` (atomic truncate-and-reinsert, wired into `reporting.build_static_site`). `coverage.py` provides the canonical read helpers (`slugs_in_tier`, `coverage_tiers`, `archetype_for`); `backfill_team_coverage.py` is now a thin CLI over the same sync. Drift is prevented two ways: build-time full-refresh prunes removed slugs, and `tests/test_team_coverage_sync.py` (5 tests) pins the table as a byte-exact mirror of the authoring sources. Satisfies the D-016 byte-identical gate trivially (no render-path reader repointed). Execution note appended to `DECISIONS.md#D-016`.
  - ✅ **`gdelt_volume` fixed** — moved out of `ingest_hourly.yml` into new `ingest_gdelt_daily.yml` on `[self-hosted, alienware]` (residential IP, daily cron `0 13 * * *`, `workflow_dispatch` timespan input for backfill). Root cause was fetch-level HTTP 429 throttling of datacenter/cloud IPs; residential IP + daily cadence (article counts are a daily metric) fixes both. Same shared-artifact DB pattern as the other ingest workflows.
  - ✅ **`kalshi` adapter fixed (real bug, not offseason)** — the seed stored **event** tickers (`KXNCAAF-27`) but `KalshiAdapter` called `/markets/{ticker}`, which 404s for an event ticker, so it silently 0-rowed *every* run, even in-season. Rewrote `fetch()` to call `/events/{ticker}` and fan each event out into its per-team binary markets. Live-verified 2026-05-28: 13 events now expand to **270 active markets** (was 1 broken call). All currently 0-volume (markets open but pre-season illiquid → 0 rows is correct now; rows flow automatically once liquid ~Aug). Seed corrected: `KXHEISMAN-26`→`KXHEISMAN-27` (wrong year), 2 events with no live Kalshi series flagged `needs_research`. New offline event-expansion test in `test_numeric_adapters.py`.
  - ✅ **Auth-gated adapters now skip cleanly instead of loud-failing** — `seatgeek`/`youtube_meta`/`spotify_charts` raised a bare `RuntimeError` on missing secret, which `SourceAdapter.run()` caught as `status='error'` → exit 1, flooding CI with red Xs for keys not yet rolled out. Added `AdapterConfigError(RuntimeError)` in `base.py`; `run()` now maps it to `status='skipped'` (exit 0 + warn). The three adapters raise it in their secret check. `run_adapter.py`'s `except RuntimeError` is now belt-and-suspenders. New offline test asserts a secret-less `SeatGeekAdapter().run()` returns `skipped`/0 rows. This means the **seatgeek "0-rows" diagnosis is resolved structurally**: with no `SEATGEEK_CLIENT_ID` it now reports `skipped`, not a false failure — the live in-season row-flow check is an operational follow-up gated on the secret being set in GitHub Actions (not a code bug).
- **In flight:** None
- **Blocked:** Live `seatgeek` row-flow verification needs `SEATGEEK_CLIENT_ID` set as a GitHub Actions secret (operational, not code). Adapter is correct and now skips gracefully without it.
- **Next action:** Move to WS-02 — run `seed_taxonomy(db)` + `classify_all_fanbases(db, 2026)`.
- **Spec:** [specs/01-foundation-unblock.md](specs/01-foundation-unblock.md)

### WS-02 — Classification + state machinery (~50% complete)
- **Last shipped (session 9, local — pending push):** ✅ **`dynasty_status_change` arc frame lit up (D-022 LOCKED).** Replaced the stub detector with a real one that reuses the **Dynasty Heatmap signal** rather than inventing a 6th classification axis: a team's trailing-3-season average of its within-season power-rating percentile. A program **enters** dynasty status when that average crosses the 85th percentile upward, **exits** when it crosses downward; arc `discriminator` = `enter`/`exit`, tension scales with crossing magnitude (enter base 0.7, exit 0.6). Detector degrades to a no-op-with-reason when the DB lacks contiguous seasons (local/offseason) and fires in CI/prod where `power_ratings_weekly` is dense (2014–2025 confirmed live). **6 of 10 arc frames now data-backed.** 3 new tests in `tests/test_arc_dynasty.py` (synthetic enter+exit crossings, no-op-when-empty, idempotency).
- **Last shipped (session 8, local — pending push):** ✅ **Non-FBS arc noise fixed at the source.** `teams.level_code` is dirty (NAIA schools — Reinhardt, Jamestown, College of Idaho — mislabeled `'FBS'`), so the archetype detector opened arcs for them. Added an injectable real-FBS allowlist gate to `populate_season_arcs` (`fbs_slugs`, defaulting to `_real_fbs_slugs()` reading `profiles/*.md`, the same authority `chronicle/pipeline.py` uses) **plus a self-healing prune** that deletes the season's stale non-FBS arcs left by earlier pre-gate runs (upsert never deletes). Live 2026 re-run: **110→67 open arcs**, the 3 NAIA arcs gone. Candidate queue gained a mirror prune for orphaned candidates → **110→67 candidates, 0 NAIA, 0 orphans**. 9 arc + 9 candidate tests pass.
- **Last shipped (session 7, PUSHED `063ba35839f`):** ✅ **Chronicle pipeline now consumes D-010 open arcs.** `_fetch_narrative_state` had queried a `season_narrative_state` column shape that never existed (`entity_slug`/`summary`/`started_week`/per-arc `status`), so it always threw and degraded `open_arcs` to `[]` — the populated arcs never reached the prompt. Rewired to read the normalised `season_narrative_arc` joined to `teams` by slug, surfacing top-tension open arcs with a synthesised `summary` (new `arc_summary()` helper). Team-keyed only; other entity kinds stay empty. Regression test in `tests/test_arc_populator.py`.
- **Last shipped (session 7, PUSHED `899c8869c2b`):** ✅ **`populate-arcs` wired into daily CI** — new "Populate narrative arcs" step in `ingest_daily.yml` runs after classify-fanbases, so `season_narrative_arc` + `season_narrative_state` rebuild daily on the production DB.
- **Last shipped (session 7, PUSHED `a4f7fb75029`):** ✅ **D-010 arc-frame populator** — `src/cfb_rankings/chronicle/arc_populator.py` + `populate-arcs` CLI. Runs all 10 LOCKED arc frames into `season_narrative_arc` and rebuilds the `season_narrative_state` cache (open/resolved/unresolved-tension JSON blobs). 5 frames are data-backed today (`portal_class_arrival`, `archetype_transition`, `coaching_transition`, `recruiting_class_arrival`, `rivalry_reset`); the other 5 degrade gracefully to empty-with-reason until feeds land (`coordinator_carousel`, `nil_collective_swing`, `market_belief_swing`, `playoff_path_change`, `dynasty_status_change`). Local 2026 run: **110 arcs across 99 teams** (25 portal + 85 archetype-transition), idempotent re-run preserves arc_ids + opened_at_week. 6 tests in `tests/test_arc_populator.py`.
- **Last shipped (session 7, PUSHED `2dac4863c09`):** ✅ **Offseason no-model-run fallback + Rule-3 band-gap closure.** (1) `classify_all_fanbases` now walks back to the last *completed* season's ratings when the requested season has no `power_ratings_weekly` (offseason-preview posture) — classification rows still stamped with the requested season, only percentiles derive from the borrowed season. (2) Rule-3 trajectory bands are now contiguous, eliminating the 0.25–0.45 and 0.70–0.80 gaps that dropped to fallback. Local 2026 FBS re-run: 87 content-mid-major / 64 quiet-professional / only 16 fallback (those 16 are NAIA programs mislabeled FBS with zero 2024 ratings — a data-coverage gap, not a band gap). Tests extended in `tests/test_archetype_percentiles.py`.
- **Last shipped (session 5, local):** `seed-archetypes` (26 rows), `classify-fanbases` (2,920 rows across 4 seasons), `build-conversation-features` (~858 rows) — confirmed locally against Alienware DB
- **Last shipped (session 6, wired into CI):** `seed-archetypes` appended to idempotent seed block in `ingest_daily.yml`; new "Classify fanbases" step added after bridge-tables step — runs `classify-fanbases --season=$SEASON --classifier-version v1.0 --backfill-history 1` daily so classifications propagate to production DB
- **Last shipped (session 4 cont., 2026-05-28):** ✅ **Fixed classifier cross-level percentile skew** — `classify_all_fanbases` ranked every team against the full multi-level `power_ratings_weekly` pool (~707 teams: FBS+FCS+DII+DIII). FBS teams cluster at the top of that pool, so ~80% landed at percentile ≥0.80 → `trajectory-strong` → the `quiet-professional` fallback. For 2024 (the last season with completed model runs) the FBS distribution was 149/189 quiet-professional (79%). Now `_percentiles_within_level()` ranks each team only against `level_code` peers: 2024 FBS rebalances to plurality `content-mid-major` 85, `quiet-professional` 64 (30 legit top-quintile + 30 band-gap fallback + 4 seeded), with the seeded/structural archetypes intact. New `tests/test_archetype_percentiles.py` (2 tests) pins within-level ranking.
- **In flight:** None
- **Blocked:** None
- **Next action:** Build the 4 remaining data-gated arc-frame feeds: coordinator OC/DC source (`coordinator_carousel`), NIL event source (`nil_collective_swing`), weekly CFP-projection feed (`playoff_path_change`), and prediction-market snapshots in-season (`market_belief_swing`). Each lands automatically once its source table fills — no populator change needed.
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
  - ✅ **Curated-feed team tagging gap CLOSED (session 7, PUSHED):** `bluesky_curated` (8,413 docs) + `substack_*` arrived with zero `conversation_document_targets`, so they fed nothing into mood/cohort features. Root cause: reddit tags at collection time; the player tagger only scans docs that already have a team target. New `tag-team-mentions` CLI (`src/cfb_rankings/ingest/team_name_tagger.py`, 11 tests) scans untagged curated docs for team-alias mentions and writes team targets. Precision-first: collision-drop, common-word stoplist + length floor (acronym whitelist), word-boundary match, span-containment suppression of short aliases nested in longer ones ("Florida" in "Florida State") and in NFL team names ("Houston" in "Houston Texans"). Wired into `ingest_daily.yml` BEFORE `tag-player-mentions` (commits `493d72c8e95`, `66b605ed335`). Local end-to-end proof: `--commit` wrote **7,572 team targets** across 8,523 curated docs; player tagger then reached **11,361 docs / 1,320 matches** (was 0 unreachable). Prod propagation is the next scheduled `ingest_daily` run.
  - ✅ **Player-tagger offseason no-op FIXED (session 7, PUSHED `895e6e7a62b`):** Surfaced while verifying the above. The daily `tag-player-mentions --season=$SEASON` runs with the *upcoming* season, which has no player stats in the offseason → empty index → silent no-op (had been tagging zero players for months, even reddit). Added `latest_player_stats_season()` + a year-agnostic empty-index fallback to the latest season that has stats. Targets still stamped with the docs-season; only the name index is borrowed. New regression test.
- **In flight:** None
- **Blocked:** Not blocked
- **Next action:** `gdelt_volume` 0-rows is now diagnosed — fetch-level HTTP 429 (GDELT throttles datacenter IPs; not a payload/parse issue). Fix is residential-IP runner (infra decision, see WS-01 → Blocked). `seatgeek` 0-rows still needs offseason-vs-bug verification (unblocked). Verify the next `ingest_daily` run actually writes curated-feed team targets (watch the new tag-team-mentions step's `rows_written`).
- **Spec:** [specs/05-adapter-ecosystem.md](specs/05-adapter-ecosystem.md)

### WS-06 — Page archetype expansion (Coach / Game / Rivalry / Conference)
- **Last shipped:** Conference index pages (basic). Rivalry card module exists for in-team-page rendering.
- **In flight:** None
- **Blocked:** Real WS-06 deliverable (Coach pages) is a Phase-4 design lift, also gated on WS-02 player/coach archetype data.
- **Finding (session 9):** The previously-planned `coaches` + `coaching_changes` tables were **deprioritized as speculative scaffolding** — no live surface would consume them. The live coaching surface (`team_pages/coaching_era.py`, the Coaching Era Strip on every world-class team page) already derives current coach, tenure length, and previous-coach window by walking `team_seasons.head_coach` inline; it needs no normalized coaching tables. The `coaching_transition` arc frame likewise diffs `team_seasons.head_coach` directly and is gated only on 2025/2026 coach data (CFBD coaches ingest currently covers 2018-2024 — a data-horizon gap, not code). Build the coaches dimension table when Coach *pages* are actually scheduled (Phase 4) and there's a consumer.
- **Next action:** Phase-4 — design the Coach page archetype template; build the `coaches`/`coaching_changes` tables then, as the page's backing store.
- **Spec:** [specs/06-page-archetypes.md](specs/06-page-archetypes.md)

### WS-07 — Era pages (CFP three-act)
- **Last shipped (session 9, local — pending push):** ✅ **Era-page prototype built end-to-end and verified against real 12-season data.** New `src/cfb_rankings/era_pages/` package (`data.py` assembly + `renderer.py` self-contained HTML/inline-CSS + `__init__.py`). `build_era_summary(db, slug, *, end_season=2025)` reuses the **Dynasty Heatmap signal** (`fetch_final_powers` + `compute_year_percentiles`) for the three-act trajectory, joins games for records + defining games, `team_seasons.head_coach` for the coach Gantt, and `player_nfl_draft` for the roster-of-era bars. All 6 spec sections render: stat sheet, SVG three-act trajectory (sub-era colored bands + gold-star title markers), defining games (top-5 by round), coaches Gantt, roster draft bars, forward bridge. Returns `None` below `MIN_SEASONS=8` (offseason/sparse guard). CLI `render-era-page <slug>...` writes `output/site/programs/<slug>/era/cfp/index.html`. **Verified against the prod DB artifact:** Alabama (147-22, 3 titles, declining acts 99→97→88 telling the post-Saban cliff) and Georgia (137-27, 2016 dip → back-to-back-title climb) render with genuinely distinct chart shapes — the viz carries narrative signal. 9 tests in `tests/test_era_pages.py` (synthetic 12-season cohort).
- **Also shipped (session 9, local — pending push):** ✅ **Build-pipeline wiring + crosslink.** `era_pages/build.py` adds `render_all_era_pages(db, programs_dir)` (renders every qualifying FBS program; `build_era_summary` None-guard silently skips sub-8-season programs), `render_era_page_for` (single, shared with the CLI), and `era_page_available(db, team_id)` (cheap MIN_SEASONS eligibility check). `reporting.build_static_site` now calls `render_all_era_pages` right after the team-pages-v2 render, writing to `/programs/<slug>/era/cfp/`. The world-class team page links to the era page from the Coaching Era Strip (`coaching_era.py`), guarded by `era_page_available` so the link only appears when the page exists. Verified: Alabama team page emits `href="/programs/alabama/era/cfp/"`; batch-render of alabama/georgia/massachusetts = 3/3 (UMass qualifies — FBS since 2012). **Era pages ship to prod on the next `publish-site` run.**
- **Blocked:** Full top-25 rollout still benefits from WS-03 profiles for editorial ledes, but the structural page no longer needs them (D-004 offseason posture = structural prose, no LLM ledes).
- **Next action:** None — live on next publish. Re-enable per-act LLM ledes when Chronicle un-suppresses post-offseason (D-004).
- **Spec:** [specs/07-era-pages-cfp.md](specs/07-era-pages-cfp.md)

### WS-08 — Chart vocabulary expansion (6 → 9)
- **Last shipped:** Locked vocab at 6 types (`docs/design-system/31-chart-vocabulary.md`)
- **Shipped (2026-05-28, session 8):** First live Sankey surface. The `flow` viz template (`editions/viz_templates/flow.py`) already existed; wired it to real data via a national portal-flow section on `/offseason/` — origin level (FBS/FCS/Lower) → destination level (FBS/FCS/Lower/Uncommitted) for the latest cycle, band width = player count. 4,422 tracked 2026 entries; honest caption (564 FCS→FBS climbers, 1,011 still uncommitted). Builder `scripts/build_offseason_leaderboards.py` already runs in `publish_site.yml`, so it deploys with no new wiring.
- **Shipped (2026-05-28, session 9):** Per-team portal flow was already live (`team_pages/roster_reload.py`, fed by `team_roster_reload_snapshot` + `team_transfer_position_snapshot`, 127 programs / 1,518 position rows in prod). The gap was **quality**: the position ledger showed headcount only (`in 1 · out 6`) and discarded the populated rating/points columns. Enhanced `_position_row` to surface the #1 underserved fan signal — top-player composite ratings inline (`Isaiah Horton 0.96`) plus a per-position **Upgrade / Downgrade / Even / Starter Risk / Need Filled** verdict derived from upstream flags then net rating-points. Verified against prod DB for Alabama (WR Starter Risk after losing a .96 and keeping a .90; OT Downgrade; IOL/DL Upgrade). 4 new tests.
- **In flight:** None
- **Blocked:** Not blocked
- **Next action:** None required. A single-team origin-level/conference Sankey was considered and **declined** as low-value (one destination node, a few origin buckets — signal already carried by the position ledger + the national flow). The two remaining new chart types (beyond Sankey) are unscheduled.
- **Spec:** [specs/08-chart-vocabulary.md](specs/08-chart-vocabulary.md)

### WS-09 — Calibration ledger
- **Last shipped (2026-05-28, session 8):** `prediction_ledger` table FOUNDATION live (migration `20260602_07`). `src/cfb_rankings/calibration/ledger.py` provides the real write path (`record_prediction`, idempotent on a deterministic id, preserves first-seen + resolution across re-records), the weekly outcome resolver (`resolve_due_predictions` + per-kind `OUTCOME_RESOLVERS`), and the methodology/Sunday-summary aggregate (`calibration_summary`, per-model + per-band). First live surface instrumented: fanbase archetype assignments (`record_archetype_predictions`, real-FBS allowlist-gated like the arc populator). CLI: `prediction-ledger --action {record-archetypes,record-season-wins,resolve,summary}`. **Second live surface added (session 8):** preseason season-win projections (`record_season_win_predictions`, `model_id="season-path"`, `prediction_kind="season_wins"`) — reads `team_season_path_projection` base scenario at its latest `as_of_date` per team, FBS-gated, expires mid-January. New resolver `_resolve_season_wins` grades vs the `games` table (score = `max(0, 1 - |pred-actual|/4)`), correctly returns "regular season not yet played" for unplayed 2026. 11 tests pass. Real DB: 127 archetype + 127 season-win 2026 preseason predictions logged (Alabama base 10 wins, high band, captured 2026-05-27 — the prediction is now on record *before* the outcome, which is the whole point of a calibration ledger).
- **Rendered page shipped (session 8):** `/methodology/calibration.html` — the public confusion matrix (`provenance/calibration_page.py`, rendered by `build-methodology`, linked from `/methodology/`). Renders `calibration_summary` live: overall accuracy, per-surface (model+kind) breakdown, per-band table, and a "pending — awaiting outcome" state for not-yet-gradeable preseason predictions. **CI-wired:** `publish_site.yml` now runs `record-archetypes` + `record-season-wins` + `resolve` immediately before `build-methodology`, and the rolling `cfb-rankings-db` artifact is re-uploaded, so the ledger accumulates first-seen history across publishes. 12 tests pass (added renderer test).
- **In flight:** None
- **Blocked:** Heisman surface is genuinely gated (no 2026 rankings exist yet; `heisman_vote_results` is empty everywhere so no resolvable outcome). Remaining cross-surface instrumentation (Reality Gap) + per-team track-record sections + game/award resolvers are Phase 2-3 (in-season) — the running gate is "≥10k rows in first in-season month."
- **Next action:** When the season opens: (1) wrap remaining prediction-rendering chips through `record_prediction`; (2) add resolvers for game/award kinds; (3) add per-team "we said X, then Y" track-record section to team pages; (4) wire `resolve` into a Sunday cron (D-015 cadence B).
- **Spec:** [specs/09-calibration-ledger.md](specs/09-calibration-ledger.md)

### WS-10 — Cross-archetype + entity graph
- **Last shipped:** N/A
- **In flight:** None
- **Blocked:** WS-06 (Coach/Game/Rivalry/Conference pages exist) before cross-archetype nav strip has anywhere to link
- **Next action:** Phase 4 work
- **Spec:** [specs/10-cross-archetype-entity-graph.md](specs/10-cross-archetype-entity-graph.md)

### WS-11 — Mobile + a11y + performance
- **Last shipped:** Static-site generator produces fast pages; mobile-renders mostly work
- **Audit (2026-05-28, session 9):** Spot-audited the two flagship surfaces against the prod DB at 390px. Both clean — no fixes warranted. Team page (`alabama`): 0 fixed/min-width CSS rules ≥360px (all wide `min-width` values live inside `@media (min-width:…)` breakpoints = mobile-first, not overflow); 1/1 img alt'd, 12/12 SVGs carry `role`+`aria-label`, single `h1`, ordered headings, the lone empty-text button is the theme toggle with `aria-label`. Era page (`era/cfp`): SVG uses `viewBox`+`preserveAspectRatio`+`.era-chart{width:100%;height:auto}` (scales, no overflow), `*{box-sizing:border-box}`, `max-width` containers, viewport meta, single `h1`. No code change — recording evidence so the PR-review enforcement note below is grounded.
- **In flight:** None
- **Blocked:** Not blocked (can audit current state anytime)
- **Next action:** Phase 5 work (March 2027). Until then: enforce mobile-rendering checks in PR review (baseline = clean per the session-9 audit above).
- **Spec:** [specs/11-mobile-a11y-perf.md](specs/11-mobile-a11y-perf.md)

### WS-12 — Editorial cadence
- **Last shipped:** Daily/Wire/Mailbag pipelines running on cron (verified live per LAUNCH_ROADMAP). 8 active storyline threads. 32 storyline chapters. **Data-driven storyline candidate queue LIVE** (commit `4cd39637fc2`): `storyline_candidate` table + `build-storyline-candidates` CLI ranks open `season_narrative_arc` rows by tension×frame-weight, dedupes against active-thread-covered teams, preserves editor `review_status` across re-runs (D-020 human-reviewed lane). Wired into `ingest_daily.yml` after `populate-arcs`. Verified locally: 110 candidates ranked from 110 arcs (top: memphis/uconn/north-texas portal classes).
- **In flight:** Storyline chapters have slipped to ~5 weeks since last update (April 21-23 was last). Candidate-queue editorial loop is complete: ranked queue → `build-storyline-candidates --digest` writes `output/storyline-candidates.md` (net-new vs covered, Promoted section) → `review-storyline-candidate --id --status` records promoted/dismissed verdicts that survive the daily re-rank. Commits `4cd39637fc2` / `56ab347e473` / `4bcd2ed474e`.
- **Shipped (2026-05-28, session 8):** Cadence dashboard (spec approach #1 + running-gate "surfaces what's overdue") — `storylines/cadence_dashboard.py` → `manage.py editorial-cadence` writes `output/editorial-cadence.md` (+ JSON): last-published-per-surface vs staleness thresholds (Wire 3d / Daily 4d / Mailbag 8d / chapters 14d / Editions 35d), flags overdue + per-active-thread staleness. Wired report-only into `ingest_daily.yml`; `--strict` exits non-zero for future CI gating. 3 tests. Local run immediately flags all 8 threads stale (35-38d) + Daily/Mailbag overdue — the documented slip, now machine-visible.
- **Blocked:** Not blocked
- **Next action:** Author chapters off the promoted candidates (close the chapter-cadence slip) — this is LLM/editorial work, not a code gap. Cadence dashboard now makes the slip auto-visible each morning.
- **Spec:** [specs/12-editorial-cadence.md](specs/12-editorial-cadence.md)

---

## Cross-cutting items

### Local LLM stack
- **Current:** Ollama running Mistral-Nemo 12B + Qwen3 8B on Alienware A1250
- **Target:** vLLM (FP8 + EAGLE-3) + Ollama coexistence per D-005
- **Next action:** Two-week setup sprint per VISION § 11 build order. Day 1-2: vLLM Blackwell install. Day 3-4: Qwen3-30B-A3B MoE benchmark.

### Chronicle cards
- **Current (session 8 — VERIFIED LIVE):** ✅ **D-004 suppression satisfied on prod.** Verified `wonderful-margulis-8ec96b.vercel.app/teams/alabama.html` (200) ships **no AI-Narratives section** (renderer flag `_SUPPRESS_LKG_CHRONICLE_OFFSEASON=True`, committed `0afee863cdc`), and the standalone `/chronicle/` + `/chronicle/alabama.html` return **404** (never deployed). The repetitive Polymarket cards only ever existed in stale **local** `output/` — classic local-vs-live trap. Hardened `scripts/render_chronicle_site_pages.py` with a matching `_SUPPRESS_CHRONICLE_OFFSEASON` guard so a manual/CI run can't regress prod (now writes a clean "returns at kickoff" landing placeholder + removes stale per-team pages). 189 LKG rows remain in `chronicle_card_cache` untouched for Phase-2 regeneration.
- **Target:** Regenerate after Phase 1 evidence diversity (post-WS-05 + voice corpus). Per D-004 Revisit, re-evaluate after Week 4 of the 2026 season once game evidence is flowing.
- **Next action:** None until regeneration. To reverse suppression, flip both `_SUPPRESS_*` flags to False.

### Uncommitted work
- **Resolved (session 9):** The Wave-25 / Milestone A+B / Player Wave-1 work flagged here is **already committed** (verified `git status` clean of tracked modifications; matches memory `project_team_preview_milestone_a` + `project_player_pages_wave_2026_05_27`). Only untracked items remaining are session-scratch scripts under `.claude/`, two design-spec drafts in `docs/specs/`, and one untracked visual-regression test — none at risk of being clobbered by code work.
- **Next action:** None — risk cleared.

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
