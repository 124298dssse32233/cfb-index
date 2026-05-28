# Architectural Decisions Log

**Format:** Append-only ADR (Architecture Decision Record). Each decision gets a numbered entry. Past entries are never edited — if a decision changes, a new entry references and supersedes the old one.

**Purpose:** When someone asks "why did we choose X over Y?", this is the authoritative answer. Cited as `DECISIONS.md#D-NNN` in PRs, specs, and conversations.

**Owner:** Claude appends entries as decisions are made. User reviews + can revoke or revise via a new entry.

---

## How to read this doc

Each decision has the form:

```
## D-NNN — [Short title] — [STATUS]

**Date:** YYYY-MM-DD
**Status:** LOCKED | OPEN | SUPERSEDED-BY-D-NNN
**Context:** What's the situation that requires a decision
**Considered:** Options A, B, C with brief tradeoffs
**Decided:** What was chosen
**Reason:** Why
**Affects:** Which workstreams / files / surfaces this gates
**Revisit:** When/why this might need re-examination
```

**Status meanings:**
- `LOCKED` — decision is final until explicitly revoked by a later entry
- `OPEN` — discussed but not yet committed; downstream work that depends on it is blocked
- `SUPERSEDED-BY-D-NNN` — historical; the cited later entry is now authoritative

---

# LOCKED DECISIONS

## D-001 — Data horizon starts 2014 (CFP Era) — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** CFB Index has structural + game data going back to 2014 only (12 completed seasons through 2025 + 2026 prep). User confirmed this is when the heavy ingest lift began, and 2014 is the first CFP season.
**Considered:**
- A) Push backfill to pre-2014 first, claim deeper era framing
- B) Frame "Modern Era 2015+" as a more aspirational horizon
- C) Anchor at 2014, frame as "CFP Era (2014-present)"
**Decided:** C
**Reason:** 2014 is a natural editorial anchor (first CFP season) that fans recognize. Pre-2014 is borrowed/inherited and gets visual distinction. Three sub-eras within the CFP era give every team a multi-act story.
**Affects:** All era pages, narrative-state machine training, calibration backtests, historical claim discipline.
**Revisit:** Only if pre-2014 backfill (Phase 4) reveals data quality good enough to claim first-party status pre-2014.
**Related memory:** [project_data_horizon_2014.md](file:///C:/Users/kevin/.claude/projects/C--Users-kevin-Downloads-Desktop-Transfer-Sports-Website/memory/project_data_horizon_2014.md)

---

## D-002 — Posture A: Compound-ship through 2026 — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** Need to decide whether to (A) ship continuous improvements publicly throughout 2026 toward a perfect launch in 2027, or (B) stay quiet and build privately for a single coordinated 2027 launch.
**Considered:**
- A) Compound-ship: public momentum compounds, calibration ledger accumulates real outcomes, editorial team gets reps
- B) Quiet build: every page is finished when seen, single marketing moment
**Decided:** A
**Reason:** Three load-bearing reasons. (1) The calibration ledger requires public predictions to earn credibility — quiet building denies us a season of trackable predictions. (2) CFB 2026 is unmissable content; skipping the season to perfect the chrome is the wrong trade. (3) Iterative shipping makes the perfect launch better, not worse — every shipped surface is one fewer to debug in launch week.
**Affects:** Entire 12-month sequencing. Phase 1 starts immediately with public-visible improvements.
**Revisit:** If editorial voice atrophies under shipping pressure (the hidden risk), reconsider in Q4 2026 retro.

---

## D-003 — No parallel state machine; extend existing archetype system — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** Initial proposal was a "narrative state machine" with 9 generic states (Ascending, Stealth Climber, Fragile Contender, etc.). Codebase audit revealed an existing 18-archetype + 8-modifier fanbase taxonomy at `src/cfb_rankings/ingest/archetypes.py` with editorial flavor (signature phrases, half-life metadata, structural locks, confidence scoring).
**Considered:**
- A) Build the proposed 9-state machine in parallel
- B) Extend the existing 18+8 archetype system with transition discipline + audit trail + backtest validation
**Decided:** B
**Reason:** The proposed 9 states map almost cleanly onto the existing 8 modifiers but lose the editorial voice, signature phrases, and structural locks. Building a parallel system would double technical debt while shipping a more confused product.
**Affects:** Workstream 02 (Classification + State Machinery). The "state machine" work becomes "run the existing classifier weekly + add transition discipline + populate the empty `fanbase_classification` + `_history` tables."
**Revisit:** If the existing 18-archetype taxonomy proves insufficient after 2026 season validation, consider extension (more archetypes) but never replacement.

---

## D-004 — Chronicle cards: suppress current LKG, regenerate after evidence diversity heals — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** 189 LKG Chronicle cards live on team pages. Every card is some variation of "Polymarket says team X has Y% to win 2027 CFP" — the same fact rewritten 5+ times per team in financial-analyst register. Root cause: in offseason, the only structured evidence flowing is Polymarket data; pipeline is correctly working with what it has.
**Considered:**
- A) Scrap the Chronicle pipeline entirely
- B) Keep current cards as-is until the data layer is healed
- C) Suppress all current LKG cards immediately; regenerate after evidence sources diversify + voice corpus expands
**Decided:** C
**Reason:** The pipeline is sophisticated infrastructure (14 modules, 8 DB tables, voice validator, fact-critic, LKG fallback, calibration scoring) that would be lost in scrap. The cards themselves are editorially worthless right now and hurt the site's perception. Suppress is reversible; scrap is not.
**Affects:** Workstream 02 secondary deliverable. Phase 1 includes the suppression patch. Regeneration scheduled for Phase 2 after offseason evidence sources are wired in.
**Revisit:** After Week 4 of the 2026 season, evaluate whether Chronicle produces meaningfully different output once game evidence is flowing.

---

## D-005 — Local LLM runtime: vLLM batch + Ollama interactive — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** Hardware is Alienware A1250 with RTX 5070 (12GB Blackwell, native FP4/FP8). Currently running Ollama with Mistral-Nemo 12B + Qwen3 8B. May 2026 research shows vLLM has ~19× throughput vs Ollama at 8 concurrent requests on consumer Blackwell, with native FP8 support being meaningfully better quality+speed than Q4_K_M GGUF.
**Considered:**
- A) Stay all-Ollama (operational simplicity)
- B) Migrate fully to vLLM (peak throughput)
- C) Two-runtime coexistence: vLLM for batch/production, Ollama for interactive/hot-swap
**Decided:** C
**Reason:** Single-request latency is nearly identical between the two, so Ollama's interactive experience stays the same. Batch workloads (Chronicle regeneration, mass classification, mass embedding) get vLLM's throughput. Marquee model (Mistral Small 24B or Qwen3-30B-A3B MoE) hot-swapped through Ollama keeps complexity manageable. VRAM coordination via time-sharing.
**Affects:** Workstream 05 (Adapter Ecosystem) downstream consumers. Chronicle pipeline reconfiguration. Voice LoRA training (Unsloth).
**Revisit:** Benchmarking phase. If Qwen3-30B-A3B MoE doesn't hit 24 tok/s on this specific hardware due to DDR5 bandwidth limits, fall back to dense Qwen 2.5 14B + Mistral Small 24B.

---

## D-006 — 6-bucket audience taxonomy (replacing single-bucket default) — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** Every one of 8,005 `conversation_document_targets` rows currently has `audience_bucket='national'` because the default in `collect_reddit_watchlist` is `'national'` and no other collector has ever run. The reader at `bets/cohort_divergence.py:21-27` expects 4 buckets (fan/rival/national/media). The deep workflow writes an unrecognized 5th value (`'team'`).
**Considered:**
- A) Keep the 4-bucket model, fix label mismatches
- B) Expand to 6 buckets to properly model the editorial spectrum
**Decided:** B — 6 buckets: `fan | rival | national | media | recruit | insider`
**Reason:** Recruit-network and insider buckets are editorially distinct from fan + media. Modeling them as separate buckets enables future surfaces (recruit-network lens, insider-only signals) without schema changes.
**Affects:** `bets/cohort_divergence.py`, `conversation.py`, deep workflow YAML, every consumer of the audience_bucket field.
**Revisit:** If "recruit" or "insider" buckets stay empty for 6+ months post-launch, consolidate back to 4.

---

## D-007 — Chart vocabulary expansion: 6 → 9 (Sankey + Choropleth + Network only) — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** Locked chart vocabulary at 6 types (Percentile Bar, Trajectory Spark, Bump Chart, Annotated Line, Small Multiples, Heatmap) with CI lint enforcement. Discussion proposed 8 net-new types; audit showed 4 were redundant (Calendar Heatmap → Heatmap, Annotated Timeline → Annotated Line, Slope Chart → Bump Chart, Radar → already exception for Player Fingerprint).
**Considered:**
- A) Keep at 6 (preserves editorial discipline)
- B) Add only the 3 genuinely net-new (Sankey for portal flows, Choropleth for recruiting geography, Network for coaching trees)
- C) Add 4 (B + Streamgraph)
**Decided:** B
**Reason:** Streamgraph is too visually noisy for the editorial register. The other three serve genuine gaps that can't be covered by the existing 6. Locking at 9 with the same governance (`charts/__init__.py` whitelist, CI lint) preserves discipline.
**Affects:** Workstream 08 (Chart Vocabulary Expansion). `docs/design-system/31-chart-vocabulary.md` updates to "Locked at 9 types as of [date]."
**Revisit:** Only if a specific surface needs a chart type none of the 9 can represent.

---

## D-008 — Doc structure: VISION + LAUNCH_ROADMAP + DECISIONS + STATUS + specs/ — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** Repo root had 49 .md plan docs including 3 attempting to be canonical master plan (CLAUDE_CODE_LAUNCH_ROADMAP, WORLD_CLASS_CFB_INDEX_MASTER_PLAN, ROADMAP_TO_COMPLETE) plus 14 SESSION_*_WRAP files and various proposals/punchlists. User explicitly flagged the "don't create parallel systems" concern.
**Considered:**
- A) Create one new MASTER_PLAN.md that supersedes everything (perpetuates the "next definitive doc" pattern)
- B) Extend CLAUDE_CODE_LAUNCH_ROADMAP (the canonical operational doc) with vision content (mixes operational + aspirational)
- C) Five-doc structure with clear separation of concerns: VISION (aspirational, quarterly update) + LAUNCH_ROADMAP (operational, per-session update) + DECISIONS (append-only ADR) + STATUS (weekly delta) + specs/ (per-workstream)
**Decided:** C
**Reason:** Each doc type has a distinct role and update cadence. Adding a sixth canonical doc would repeat the failure. Archived 21 stale docs to `docs/archive/` to free the root.
**Affects:** All future planning artifacts. CLAUDE.md gets a navigation pointer update.
**Revisit:** If a sixth doc type emerges as needed (e.g., a separate "open questions tracker"), evaluate whether it can fold into one of the five.

---

# OPEN DECISIONS (gating work)

These need resolution before downstream workstreams crystallize. Listed in priority order.

## D-009 — Naming: "Fan Belief" vs "Fanbase Awareness" — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** Today's player-page chip reads "FAN BELIEF" with offseason fallback "Awaiting." But the data we actually measure in offseason is volume/attention, not belief. Belief is an in-season concept (mood swings tied to outcomes). Two different things deserve two different labels.
**Considered:**
- A) Keep "Fan Belief" year-round; accept the chip says "Awaiting" all offseason
- B) Phase-swap: "Fanbase Awareness" in offseason → "Fan Belief" in-season (chip relabels based on `season_phase`)
- C) Two separate chips that both exist year-round
**Decided:** B — phase-aware label matches the actual data being measured. Site already has phase-aware banner infrastructure (`_MONTH_TO_PHASE` enum in `state_resolver.py`).
**Reason:** "Belief" implies prediction-with-stakes, which fans only have during games. Offseason measurement is volume/attention — calling it "Belief" misrepresents what the number is. Two labels, one chip, swap on phase. Already integrated into editorial rhythm (D-019).
**Affects:** All player page + team page Fan Belief chips. Phase-swap trigger lives in renderer.
**Revisit:** If user wants a different naming, request `/octo:debate` to challenge.

## D-010 — The 10 narrative arc frames — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** `season_narrative_arc` schema exists empty. Need to define the canonical set of arc frames so the populator can categorize events.
**Considered:**
- A) Lock at 10 frames as proposed
- B) Add 11th for "House settlement / revenue sharing" events
- C) Remove `nil_collective_swing` as too noisy
**Decided:** A — lock at 10 as proposed. House settlement events get classified under `nil_collective_swing` (revenue-share is part of the broader NIL ecosystem). `nil_collective_swing` stays because NIL is now mature roster strategy per VISION § 2.
**The 10 locked frames:**
1. `coaching_transition` — head coach hire. Opens on hire announcement; closes after first season completed.
2. `coordinator_carousel` — OC/DC change. Opens on announcement; closes after first season under new coordinator.
3. `nil_collective_swing` — NIL fundraising, collective news, or scandal event. Opens on event; closes when class/season impact measurable.
4. `portal_class_arrival` — top-25 portal class secured. Opens on portal-window close; closes after first season of those players.
5. `recruiting_class_arrival` — top-25 recruiting class secured. Opens on signing day; closes at year 3 of that class.
6. `rivalry_reset` — rivalry-game outcome reverses a streak. Opens on game; closes at next meeting.
7. `archetype_transition` — fanbase archetype changes. Opens on transition event; closes when stable for 2+ seasons.
8. `market_belief_swing` — market implied prob moves >20pp in 4w. Opens on swing; closes when outcome resolves.
9. `playoff_path_change` — CFP-projection shift >2 seeds. Opens on shift; closes at season end.
10. `dynasty_status_change` — prestige tier crosses 5↔6. Opens on crossing; closes when stable for 2 seasons.
**Reason:** 10 is the right number — enough to categorize the events that actually drive narratives, few enough that the editorial register stays distinct per frame. Each has clear open + close conditions for the populator.
**Affects:** `season_narrative_arc` populator (WS-02). Each arc opens/closes via event-ledger triggers.
**Revisit:** If a major event class emerges that doesn't fit any frame (e.g., the House settlement revenue-share era requires its own treatment), request `/octo:debate` for an 11th frame.

**Execution note (2026-05-28, session 7, `a4f7fb75029`):** Populator shipped at `src/cfb_rankings/chronicle/arc_populator.py` (`populate-arcs` CLI). Of the 10 frames, **5 are data-backed today** and **5 degrade gracefully to empty-with-reason** until their feeds exist:
- **Live:** `portal_class_arrival` (transfer_entries, top-25 FBS by transfer_points), `archetype_transition` (fanbase_classification season-over-season change), `coaching_transition` (team_seasons head_coach diff), `recruiting_class_arrival` (recruiting_entries top-25 FBS), `rivalry_reset` (team_rivalry_meetings winner reversal).
- **Data-gated (returns [] + reason):** `coordinator_carousel` (no OC/DC source), `nil_collective_swing` (no NIL event source), `market_belief_swing` (prediction_market_snapshots empty in offseason), `playoff_path_change` (no weekly CFP-projection feed), `dynasty_status_change` (program_tier unpopulated).
- First local run (season 2026): 110 arcs across 99 teams (25 portal + 85 archetype-transition). Idempotent — re-run preserves arc_ids + opened_at_week. Not yet wired into CI (next action in STATUS WS-02).

## D-011 — Profile expansion targets — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** Currently 17 hand-authored editorial profiles in `profiles/*.md`. Scaling to 119 by mid-2027 means a mix of full editorial + LLM-drafted + minimal.
**Considered:**
- A) 17 full + 25 assisted + 77 minimal (preserves voice quality)
- B) 30 full + 30 assisted + 59 minimal (more authoring, scarcer reviews)
- C) 17 full + all 102 remaining LLM-drafted with voice_validator (fastest scaling, voice risk)
**Decided:** A — 17 editorial_full + 25 editorial_assisted + 77 minimal.
**Reason:** Voice quality is the moat. 17 hand-authored are the gold standard and can't be diluted. 25 LLM-drafted-then-reviewed is the right scaling for top-25 P4 + top-15 G5 in Phase 2-3. 77 minimal-frontmatter-only covers the long tail with at minimum: primary_subreddit, accent_hex, mantra, identity_phrase, never_use list. Option C trades voice for coverage too aggressively; Option B over-commits review capacity.
**Affects:** WS-03 (Editorial Profiles). LLM-draft pipeline scope. Reviewer time budget.
**Revisit:** If voice_validator pass rate on editorial_assisted holds well (>95%), consider expanding to 30-35 in Phase 4.

## D-012 — Pre-2014 backfill scope — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** Phase 4 work includes historical backfill from public sources (Sports Reference, CFB Reference, Wikipedia).
**Considered:**
- A) 1936–2013 first (AP poll era), pre-1936 as season 2
- B) All the way to 1869 (CFB invented) in one push
- C) Just bowl results to 1902 + Heisman to 1935, skip AP polls
**Decided:** A — Phase 4 backfills 1936-2013 (AP poll era). Pre-1936 backfilled in season 2.
**Reason:** AP poll era gives ~80 years of polled rankings — the richest editorial substrate. Pre-1936 is more selective scrape (bowl results + major-conference champions + Heisman from 1935) and can wait. Option B over-commits Phase 4 to undifferentiated history. Option C undersells the era pages by missing poll context.
**Affects:** WS-04 (Historical Backfill). Era pages get "Borrowed" treatment for 1936-2013, "Inherited" for pre-1936.
**Revisit:** If user wants pre-1936 sooner, request to advance into Phase 5.

## D-013 — Refuse list lock — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** VISION_2026_2027.md § 13 lists 12 things we refuse to build. Each represents scope discipline over 12 months.
**Considered:**
- A) Lock the 12-item list as written
- B) Loosen individual items (PWA might be OK; comments on Mailbag only; NotebookLM podcast might be high-leverage)
- C) Add to the list (e.g., refuse all forms of fan submissions)
**Decided:** A — lock the 12-item list as-is.
**Reason:** The list is the discipline; loosening individual items invites scope creep. PWA = web (already covered). Comments dilute the publication framing. Podcast generation is a 2027 question; if NotebookLM-style auto-podcast emerges as obviously high-leverage, it can be revisited via DECISIONS entry — but not by loosening this lock pre-emptively.
**Affects:** PR triage. Anything in the refuse list gets immediate rejection unless this decision is revoked first.
**Revisit:** Quarterly review. If a refuse-list item shows clear evidence of being wrong (e.g., a competitor demonstrates the high-leverage NotebookLM pattern is genuinely killer), open a new entry to specifically revoke that item with reasoning.

## D-014 — Voice LoRA: how many adapters — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** Phase 2 work includes training voice LoRAs on Unsloth. Options for how many adapters to train.
**Considered:**
- A) 1 general-CFB-voice adapter
- B) 4–5 adapters per editorial register (game-week, offseason, recruiting hype, columnist-essay, beat-writer)
- C) 18 adapters per fanbase archetype (Anxious Dynasty voice, Stockholm Syndrome voice, etc.)
**Decided:** B — train 5 adapters per editorial register. Per-archetype adapters (Option C) revisited in Phase 4 if voice corpus density per archetype proves sufficient (need ~500-1000 examples per adapter).
**The 5 register adapters:**
1. `game-week-voice` — Monday autopsy / Wednesday matchup / Friday Mailbag / Sunday synthesis
2. `offseason-voice` — patient longitudinal, May-July dead-period content
3. `recruiting-hype-voice` — NSD coverage, top-class commit posts, portal arrivals
4. `columnist-essay-voice` — long-form editorial, era page ledes
5. `beat-writer-voice` — Tuesday depth chart, injury reports, press takeaways
**Reason:** Option A is too undifferentiated for "bespoke to CFB." Option C is too granular for current voice corpus depth (we have 329 passages; per-archetype would need ~9k for 18 adapters). Option B aligns adapters to editorial rhythm (D-019) — each adapter has a clear use case in the calendar.
**Affects:** Phase 2 voice corpus curation scope. Unsloth training queue. Chronicle pipeline routing logic.
**Revisit:** Phase 4 quarterly review — expand to per-archetype if corpus depth supports it.

## D-015 — Calibration ledger publication cadence — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** Calibration page renders the live model accuracy history. When does it publish?
**Considered:**
- A) Continuously (every chip update writes a row; methodology page reads live)
- B) Weekly snapshot (Friday cron writes the week's calibration)
- C) Per-game (game results trigger calibration update)
**Decided:** A for the ledger writes, B for the public summary, C as a special-case override.
**Reason:** Continuous writes are operationally simplest and feed all consumers. Weekly Sunday-evening public summary aligns with editorial rhythm (Sunday synthesis day per D-019). Per-game updates trigger only when a major model accuracy event happens (e.g., 5+ predictions resolve in one game with notable accuracy delta) — these become Wire stories.
**Affects:** WS-09 (Calibration Ledger). Methodology page rendering. Sunday Daily content slot.
**Revisit:** If the weekly summary feels too late (e.g., during Heisman race), consider mid-week interim snapshots.

## D-016 — `team_coverage` migration timing — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** Consolidating 6 overlapping cohort lists (PROFILED_SLUGS, priority_teams.yaml, TOP_ENTITIES_FULL/PARTIAL, BLUEBLOOD_PROGRAMS, STRUCTURAL_PRIMARIES) into one `team_coverage` table.
**Considered:**
- A) Phase 1 week 2 (early, touches everything)
- B) Phase 2 (after foundation unblock is verified stable)
- C) Defer to Phase 3 (cleanup work, not new features)
**Decided:** A — Phase 1 week 2.
**Reason:** Touches ~6 files but publish_site behavior should be byte-identical before/after. Doing it early prevents "if I add a team now I have to touch 5 places" friction for the next 12 months. Risk is contained — entire migration is one-time data move + 6-file refactor.
**Affects:** WS-01 (Foundation Unblock). 6 cohort sources get deprecated. All consumers query the unified table.
**Revisit:** If the migration takes >1 week, evaluate whether to pause and split the consumers across multiple PRs.

**Execution note (2026-05-28, session 4) — decision intent preserved, mechanism corrected:**
During execution the literal "delete the constants, all readers query the table" mechanism proved partly infeasible, for two reasons the Considered options didn't surface:
1. **Circular bootstrap.** The backfill (`scripts/backfill_team_coverage.py` → `coverage.sync_team_coverage`) *imports* the authoring constants (`PROFILED_SLUGS`, `TOP_ENTITIES_*`, `BLUEBLOOD_PROGRAMS`, `STRUCTURAL_PRIMARIES`) to *populate* `team_coverage`. If those same constants instead read from the table, nothing can ever seed it. `profiles/*.md` is likewise the documented source of truth for the `authored` tier (CLAUDE.md).
2. **No `db` in the hot path.** `classify_team()` (`ingest/archetypes.py`) is a pure function with no `db` handle; making its lookups query the table would ripple a `db` arg through every caller and break test purity for zero behavior gain.

**Corrected mechanism (intent unchanged — still "one place to query coverage"):**
- Authoring constants + `profiles/*.md` remain the **source of truth** (the edit point + bootstrap input).
- `team_coverage` is a **derived, denormalized read surface**, re-synced from the authoring sources on *every build* via `coverage.sync_team_coverage(db)` (wired into `reporting.build_static_site`). Truncate-and-reinsert in one transaction, so it can't drift and a removed slug is pruned.
- **Cross-cutting** consumers (anything asking "team X's coverage across all dimensions" or "every team in tier Y") query `cfb_rankings.coverage` helpers (`slugs_in_tier`, `coverage_tiers`, `archetype_for`). Per-dimension authoring consumers keep their constants.
- Drift-guard: `tests/test_team_coverage_sync.py` pins the table == authoring-sources invariant on a temp DB (CI-safe).
- The "publish_site byte-identical" gate is satisfied trivially: no render-path reader was repointed, so output is unchanged. The benefit ("add a team in one place, it propagates") is delivered because any edit to an authoring source auto-syncs into the unified table on the next build.

This is an implementation clarification, not a re-litigation: the decision (A — consolidate in Phase 1, unified queryable table) stands; only the constant-inversion mechanism was replaced with auto-sync because inversion was circular.

## D-017 — Octopus invocation policy — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** Decided where Octopus adds value (see VISION § 20). Need to confirm specific invocation triggers.
**Considered:**
- A) Trigger by workstream phase entry (e.g., `/octo:tdd` automatically when classifier work begins)
- B) Trigger by PR risk score (e.g., `/octo:review` on any PR touching >10 files)
- C) Manual invocation only (Claude proposes; user approves)
**Decided:** C for the next 90 days, then evaluate at quarterly review.
**Reason:** Automatic triggers add cost + complexity before we know if the patterns are reliable on Windows (memory notes orchestrators have stalled). Manual gives us 90 days of observation. Quarterly review (Sep 2026) decides whether to automate.
**Affects:** How Claude proposes Octopus usage in execution turns. Octopus cost budget.
**Revisit:** Sep 2026 quarterly review. If patterns are reliable + cost-justified, automate the highest-value triggers (probably `/octo:review` on PRs touching classification or calibration code).

## D-019 — Editorial rhythm: day-of-week + season-phase enums lock — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** The codebase has `_DOW_LABEL` and `_MONTH_TO_PHASE` enums in `state_resolver.py` driving `PageState` at render time. Editorial intent for each day/phase has been informally discussed but never documented. Locking the rhythm enables autonomous operation + bespoke per-day content.
**Considered:**
- A) Keep enums as code-only, document informally per surface
- B) Lock editorial intent in a doc; require all auto-publish to respect the rhythm
- C) Rewrite the enums with new labels first, then document
**Decided:** B — document in VISION § 17 + `docs/editorial-rhythm.md` (detailed); keep existing enum labels (they're working).
**Reason:** Day-of-week + season-phase rhythm is what makes the site feel like a CFB publication rather than a generic data product. Locking the rhythm enables autonomous operation per D-020. Existing labels are sound and don't need renaming.
**Affects:** All editorial surfaces (Wire, Mailbag, Chronicle, storyline chapters). Auto-publish gates per D-020.
**Revisit:** If a major calendar shift happens (e.g., CFP expands further, season length changes), revisit. Otherwise stable.

---

## D-020 — Autonomous operation model — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** User wants the site to operate quasi-autonomously each quarter with one-click override. Different flow for in-season vs offseason. Effort target: ~30 min/week in-season, ~15 min/week offseason, ~2h/quarter for review.
**Considered:**
- A) Full autonomy from day 1 — everything auto-publishes, user reviews after
- B) Full review queue — nothing auto-publishes without explicit approval (slow, doesn't scale)
- C) Tiered autonomy: chip-level renders auto-publish unconditionally; editorial cards auto-publish if pass voice + fact + receipt gates at confidence ≥ medium; profile/archetype-system/refuse-list changes always require approval. Override via `/retract`, `/amend`, `/freeze` one-shots.
**Decided:** C
**Reason:** Tiered autonomy is the only realistic way to operate the 5-doc + 12-workstream product over 12 months with one editor. The gates are real (voice_validator, fact_critic, receipt density, calibration band) — autonomy is only as trustworthy as the gates. Three pre-conditions before going fully autonomous: ≥3 months of calibration data + voice_validator coverage at every editorial surface + override workflow tested end-to-end.
**Affects:** Every workstream. Calibration ledger (WS-09) becomes load-bearing as autonomous trust gate. Voice LoRA + voice_validator extension (WS-12) becomes load-bearing. Override CLI commands need to exist.
**Revisit:** Quarterly review (per § 17 cadence). If calibration drift exceeds tolerance or off-voice content slips through, tighten the gates.

---

## D-021 — Hero design locks (homepage + era page) — LOCKED

**Date:** 2026-05-28
**Status:** LOCKED
**Context:** Two surfaces anchor the product experience: homepage and team era page. Discussed in conversation but not previously locked at the design-system level.
**Considered:**
- A) Leave design implicit; let it evolve
- B) Lock specific design contracts for both surfaces
**Decided:** B
**Reason:** These two surfaces are the "first impression" and the "deepest claim" of the product. Locking the design contract prevents drift and enables CI checks (e.g., homepage must have all 6 surfaces; era page must have all 6 sections).
**Locked design:**
- **Homepage:** 6 surfaces, top to bottom — Narrative-state weather map / What changed in 24h / 5-chip strip / CFP Era anchor / 3-section nav / Methodology footer. See VISION § 18.1.
- **Team Era Page:** 6 sections — Era stat sheet / Three-act trajectory / Defining games / Coaches of era / Roster of era / Entering Year 13. See VISION § 18.2.
- **Current-season Team Page:** Time-zoom strip at top linking to all archetype views of the entity. See VISION § 18.3.
**Affects:** WS-07 (era pages), WS-10 (cross-archetype nav), homepage renderer.
**Revisit:** Only via explicit user revocation.

---

## D-018 — Player narrative arc generation scope — LOCKED

**Date locked:** 2026-05-28 (autonomous best-judgment per user authorization)
**Status:** LOCKED
**Context:** `player_narrative_arc` table has 194 rows (out of ~70k players). 3-act schema (opening/pivot/finish). Phase 2 expands this.
**Considered:**
- A) Top-200 priority players (projected starters + Heisman watch + portal arrivals)
- B) Top-500 players (broader coverage)
- C) Every player on a 2026 depth chart (~5,000)
**Decided:** A for Phase 2 (top-200), expand to B (top-500) in Phase 3 if voice quality holds.
**Reason:** Voice quality at scale is the risk. Top-200 covers the players fans actually search for (every projected P4 starting QB + top RB/WR/edge + Heisman watch list + top portal arrivals). Expanding to 500 in Phase 3 adds the rest of the projected starters across all 119 FBS. Option C is overcommitment — 5,000 arcs at ~30s each is 40 hours of GPU time per regeneration and dilutes voice quality.
**Affects:** WS-02 (Classification + State). Chronicle pipeline player-side queue. LLM compute budget.
**Revisit:** End of Phase 3 — if top-500 arcs are passing voice_validator at >95%, expand to top-1000 in Phase 4.

---

# DECISION TEMPLATE (copy when adding new)

```
## D-NNN — [Short title] — [LOCKED | OPEN | SUPERSEDED-BY-D-NNN]

**Date:** YYYY-MM-DD
**Status:**
**Context:**
**Considered:**
- A)
- B)
**Decided:**
**Reason:**
**Affects:**
**Revisit:**
```

---

# META-RULES FOR THIS DOC

1. **Append-only.** Never edit a past decision's body. To change a decision, add a new entry that supersedes it.
2. **Cite by ID.** PRs, specs, status notes reference `DECISIONS.md#D-NNN`. Makes the trail searchable.
3. **OPEN decisions block work.** Workstreams that depend on an OPEN decision should not start their code work until the decision is LOCKED.
4. **`/octo:debate` candidates.** Entries marked as such are good candidates for multi-AI debate when the time comes to lock them.
5. **Quarterly review.** At the end of each quarter, re-read this doc. Any decision that was wrong gets a new entry, not an edit. The wrong-decision-+-correction pair is the historical record.
