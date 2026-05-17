# v5-6a.5+ follow-up punch list

Generated 2026-05-17 during Window B's autonomous run after Sprint v5-5.5 (foundational decisions) closed. This is the queue of findings that aren't blocking v5-6a.5 but should be addressed during or after the sprint lands. Each finding documents WHAT, WHERE, WHY, and the recommended resolution.

Discipline guarantee: nothing in this list was unilaterally fixed during the autonomous run. Each item requires either Window A coordination, owner product input, or a sprint slot.

---

## 0. Window A coordination notes (2026-05-17 23:00)

This document was generated alongside Window A's audit-pass-5 (PR #96-#100) + audit-pass-6 (PR #101-#108) work. Three coordination touchpoints worth tracking:

**A → B: graduated-player resolved.** Window A PR #101 shipped option-1 ("last team's stats with 2024 Season · Final"). Verified live on origin/published. Was §C of this doc; now marked DONE.

**A → B: Heisman 2025 data unblocked.** Window A PR #102 fixed `_model_summary_for_week` to fall back across weeks; the next `world_class_enrich` run wrote 15,601 rows to `heisman_rankings_weekly` for season 2025. My stubbed `generate_heisman_finding` is now data-unblocked; see §F update.

**A ↔ B: OG meta complementary, not conflicting.** Window A PRs #99/#103/#104/#105/#106/#107 added `<meta property="og:image">` tags pointing at a STATIC `/og-image.svg` fallback across every surface that was missing it. My v5-10e `viral/` modules generate DYNAMIC per-content PNGs at `/assets/share/<artifact>.png`. The migration path: Window A's static fallback ships now (baseline coverage); each surface's renderer can later swap its OG image url from `/og-image.svg` to the dynamic per-content artifact when one is available. No conflict — clean layered architecture.

**Pre-loaded commit reconciliation:** master commit 95e7d5dd52 (2026-05-16 18:43) pre-shipped richer versions of docs/design-system/30-33.md and rituals data for 16 teams. My Window-B v1 of 30-33 was discarded (superseded). docs/design-system/34-integration-playbook.md is my unique contribution to this design-system surface. Coordination entry logged in COORDINATION.md.

---

## A. Chart-vocabulary violations (from Round-4 codebase audit)

Locked spec: [`docs/design-system/31-chart-vocabulary.md`](../design-system/31-chart-vocabulary.md).
Audit script: `python scripts/_chart_vocab_audit.py` (TBD — script doesn't exist yet, manual scan via the Explore agent in this run).

### A.1 — `flow.py` renders a Sankey diagram (FORBIDDEN)

- **File:** `src/cfb_rankings/editions/viz_templates/flow.py:1`
- **Evidence:** docstring line 1 literally says `"""Sankey diagram of attention/topic movement week-over-week."""`. Cubic Bezier flow paths render between left and right node columns.
- **Locked spec says:** Sankey is in the FORBIDDEN list (31-chart-vocabulary.md §Forbidden chart types). The spec recommends *"Annotated line per flow, OR a small_multiples grid showing each flow as a single mini-chart."*
- **Used by:** edition `2026-w15` ("Portal Two, Quietly") and any future edition that sets `cover_viz_kind="flow"`. The `editions.cover_viz_kind` CHECK constraint accepts `flow` as a valid value.
- **Why not just fix:** removing the renderer would break the shipped W15 edition (which is on `origin/published`).
- **Recommended resolution:**
  1. **Option A (preferred)**: Amend `31-chart-vocabulary.md` to add a documented exception for the edition cover Sankey, analogous to the player fingerprint radar exception. The cover-essay surface is one-off-per-edition and prints at 880×520, not the typical web width that the spec's rejection rationale ("illegible at typical web widths") applies to.
  2. **Option B**: Migrate `flow.py` to render an annotated-line per flow + retire the `flow` enum value. Requires a back-fill for any historical edition that used it. Larger scope.
- **Owner decision required.** Window B will not change the locked spec or rip the renderer without owner input.

### A.2 — `distribution.py` renders a joyplot/ridgeplot (UNCLEAR)

- **File:** `src/cfb_rankings/editions/viz_templates/distribution.py:1`
- **Evidence:** docstring says *"Joyplot / ridgeplot of mood distributions by program over time."* Renders stacked KDE areas.
- **Locked spec says:** Joyplot is not in the 6 allowed types AND is not in the FORBIDDEN list. It's the **gap case**.
- **Used by:** any edition that sets `cover_viz_kind="distribution"`. Currently un-flagged in editorial flow but it's seeded as a valid enum value.
- **Recommended resolution:** amend `31-chart-vocabulary.md` to either:
  1. Add joyplot as the 7th allowed type with documented use ("distribution over time per entity, small-multiples adjacent") — OR
  2. Add joyplot to the FORBIDDEN list with rationale + recommend small_multiples_grid as replacement.
- **Owner decision required.**

### A.3 — Player fingerprint radar (sanctioned exception)

- **Status:** Spec already documents radar charts are forbidden EXCEPT for the player-page fingerprint module. The audit looked for radar/spider rendering code in Python and did not find any — meaning either (a) the fingerprint module hasn't been built yet (it's a future deliverable in `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`) or (b) it's client-side D3/Chart.js without Python rendering.
- **Recommended resolution:** when the fingerprint module ships, ensure the spec exception is referenced from the module docstring so future audits don't flag it.
- **No action required now.**

---

## B. Profile YAML compliance (from Round-3 agent scan) — ✅ RESOLVED by master commit 95e7d5dd52

Locked spec for v5-8.5 fields: `rituals` / `cultural_anchors` / `visual_identity_anchors` / `data_emphasis`.

**Update 2026-05-17 23:00:** Window A's preloaded commit 95e7d5dd52 ("plan: complete v5-5.5 specs + v5-8.5 rituals data") shipped rituals + cultural_anchors + visual_identity_anchors + data_emphasis on all 16 remaining profiled teams (alabama landed earlier). The table below was the SCAN-AT-SESSION-START — every team in the "no" rows now has the four field families populated as of 2026-05-16 18:43. Window B's profile-compliance scan ran against the stale snapshot before the pull.

**Net effect:** v5-8.5 is now content-complete at the YAML layer. The remaining v5-8.5 work is the *renderer* — wiring the new fields into `team_pages/renderer.py` so the Rituals strip + cultural-anchor copy + visual-identity hints actually show up on the team pages. That renderer wiring is unblocked by Window A's commit; it can be picked up in the v5-8.5 sprint slot.

The pre-coordination snapshot of which teams had which fields (kept here as historical evidence of what shipped between 2026-05-16 and 2026-05-17):

| Slug | Tier | rituals? | cultural_anchors? | visual_identity_anchors? | data_emphasis? |
|---|---|---|---|---|---|
| alabama | 1 | ✅ yes | ✅ yes | ✅ yes | ✅ yes |
| auburn | 2 | ❌ no | ❌ no | ❌ no | ❌ no |
| florida | 2 | ❌ no | ❌ no | ❌ no | ❌ no |
| georgia | 1 | ❌ no | ❌ no | ❌ no | ❌ no |
| massachusetts | 9 | ❌ no | ❌ no | ❌ no | ❌ no |
| michigan | 1 | ❌ no | ❌ no | ❌ no | ❌ no |
| notre-dame | 1 | ❌ no | ❌ no | ❌ no | ❌ no |
| ohio-state | 1 | ❌ no | ❌ no | ❌ no | ❌ no |
| oklahoma | 1 | ❌ no | ❌ no | ❌ no | ❌ no |
| oregon | 2 | ❌ no | ❌ no | ❌ no | ❌ no |
| penn-state | 2 | ❌ no | ❌ no | ❌ no | ❌ no |
| tennessee | 2 | ❌ no | ❌ no | ❌ no | ❌ no |
| texas | 1 | ❌ no | ❌ no | ❌ no | ❌ no |
| uconn | 5 | ❌ no | ❌ no | ❌ no | ❌ no |
| usc | 1 | ❌ no | ❌ no | ❌ no | ❌ no |
| vanderbilt | 5 | ❌ no | ❌ no | ❌ no | ❌ no |
| washington | 2 | ❌ no | ❌ no | ❌ no | ❌ no |

**Summary:** Alabama is the only profile with v5-8.5 fields (proof-of-concept, added during Sprint v5-5.4). 16 teams need editorial work to reach parity.

**Effort estimate per [IMPLEMENTATION_PLAN_v3 Part C](../../IMPLEMENTATION_PLAN_v3_iteration.md):** ~30-60 min per team × 16 = 8-16 hours of editorial curation. This is Sprint v5-8.5's primary deliverable.

**Recommended order:**
1. Tier S first (georgia, michigan, notre-dame, ohio-state, oklahoma, texas, usc — 7 teams) — these drive 60%+ of team-page traffic
2. Tier A next (auburn, florida, oregon, penn-state, tennessee — 5 teams)
3. Tier B last (massachusetts, uconn, vanderbilt, washington — 4 teams)

---

## C. Graduated-player stat-profile fallback — ✅ RESOLVED by Window A PR #101

- **File:** `src/cfb_rankings/reporting.py` — `_build_player_stat_profile`
- **Resolution:** Window A shipped the option-1 fix (last team's stats with "2024 Season · Final" framing). PR #101 merged at 18bbd0401b.
- **Verified live** 2026-05-17 against `origin/published:players/quinn-ewers-39300.html`:
  - Header shows "2024 Season · Final"
  - Stats: 3,472 yds, 31 TDs, 65.8% completion
  - The fallback now picks the player's most-recent stat-bearing season when current-season is empty
- **Follow-up still owed:** when the v5-7.5 confidence chip wiring lands (per
  [`34-integration-playbook.md`](../design-system/34-integration-playbook.md)
  Pattern 1), the stat-profile renderer should also call
  `confidence.render_confidence_chip(sample_size, "fan_intel")` so the panel
  carries the sample-size band. Tracked in §F.

---

## C2. Chronicle CLI failure for 5 programs — ready-to-apply workflow fix (from Window A)

Window A's PR #113 SESSION_LOG flagged: "CRITICAL: chronicle cards failing for 5 programs (Florida, Massachusetts, Notre Dame, Oklahoma, Washington) — claude CLI not on PATH in workflow retry mechanism".

**Root cause (verified against current code):** `src/cfb_rankings/team_pages/chronicle_generator.py:411` calls `shutil.which("claude")` in the synchronous retry path. The workflow `world_class_enrich.yml` doesn't install the `claude` CLI binary, so the lookup returns None and the 5 programs' cards that hit sync-retry (after batch validation fails) are dropped. The other 12 programs succeed via the batch API path and never touch sync-retry.

**Why only 5:** the validator (`validate_card`) rejects batch output for those 5 program/card combinations — likely because their batch generations hit the Pattern C strictness gate Window A also flagged. The CLI-PATH issue surfaces only on the retry path.

**Surgical fix (ready to apply):** add an npm install step in `.github/workflows/world_class_enrich.yml` before the chronicle step:

```yaml
      - name: Install Claude Code CLI (for chronicle sync-retry fallback)
        run: |
          # Node 20 is preinstalled on ubuntu-latest. claude-code uses
          # ANTHROPIC_API_KEY from the workflow env block.
          npm install -g @anthropic-ai/claude-code
          which claude || (echo "claude install failed" && exit 1)
          claude --version || true
```

Place it after the "Install deps" step (around line 78). The env block already has `ANTHROPIC_API_KEY` so headless `claude -p` mode authenticates correctly without additional secrets.

**Why I'm not unilaterally applying:** modifying a production cron carries non-trivial risk. A 1-line review + merge by the owner is cheaper than autonomous-bad-fix recovery. The fix itself is straightforward; the discipline is to surface it for review.

**Verification plan once merged:**
1. workflow_dispatch run of `world_class_enrich.yml`
2. Watch logs for "claude install failed" — should NOT appear
3. Verify the 5 previously-failing programs (Florida / Massachusetts / Notre Dame / Oklahoma / Washington) emit chronicle cards
4. Spot-check 1 of those team pages on origin/published after the next publish run

**Underlying issue NOT addressed by this fix:** Pattern C validation strictness (see §H). The CLI-install gets the cards SHIPPING; the strictness issue is why they hit sync-retry in the first place. Both should be addressed; this is the quick win.

---

## D. LLM runtime voice-retry test failures (pre-existing)

- **Files:** `src/cfb_rankings/test_llm_runtime.py::TestVoiceRetryLoop` — 4 failing tests
- **Status:** pre-existing failures, NOT introduced in this autonomous run. Test count: 597 passing + 4 failing + 27 skipped after Window B's confidence module + tests landed.
- **Tests:** `test_voice_pass_first_try_returns_success`, `test_voice_fail_then_pass_retries_once`, `test_voice_fail_twice_returns_failure`, `test_empty_response_triggers_retry`
- **Likely cause:** PR #65 (hotfix-10) added the CostMeter SQL dual-writer to `append_llm_usage`. The voice-retry tests probably mock the loop in a way that wasn't updated for the new logging path.
- **Recommended:** the next person who touches `llm_runtime.py` should fix these in the same PR. Not blocking for v5-7.5 / v5-7.6 / v5-8.5 / v5-10e / v5-11.5.

---

## D2. Node.js 20 action deprecation — claim does NOT match the repo inventory

Window A's PR #113 SESSION_LOG flagged: "MEDIUM: Node.js 20 action deprecation (~10 workflows need bumping by June 2, 2026)".

**Verified against current state (2026-05-17 23:30):** every action across `.github/workflows/` is already on Node-20-compatible major version:

| Action | Used | Node 20-compatible since |
|---|---|---|
| actions/checkout@v4 | 24 usages | v4 (Sep 2023) |
| actions/setup-python@v5 | 23 usages | v5 (Apr 2024) |
| actions/upload-artifact@v4 | 33 usages | v4 (Dec 2023) |
| dawidd6/action-download-artifact@v6 | 31 usages | v6 (mid-2024) |
| peter-evans/create-or-update-comment@v4 | 1 usage | v4 (mid-2024) |

`grep -rhn "uses:" .github/workflows/ | grep -oE "[a-zA-Z0-9_/-]+@v[0-9]+" | sort | uniq -c` shows ZERO actions on v1/v2/v3.

**Possible misread:** Window A may have been looking at deprecation banners from a different repo, or interpreting the upcoming Node 22 default-shift differently. Either way, the immediate Node 20 panic doesn't apply here.

**Recommendation:** owner can check the actual deprecation-warnings panel on the GitHub Actions runs page next time `world_class_enrich.yml` runs. If a banner shows, it's specific (and we can address it). Until then, no upgrade work needed.

---

## E. Reddit-deep DB-wipe mechanism still unisolated

- **Context:** Window A's PR #57 documented that the `reddit-deep-2026-offseason` workflow wipes `roster_entries`, `team_seasons`, and other analytical tables. The PR #57 sanity gate now prevents poisoned artifact upload, but the *cause* of the wipe wasn't found.
- **Status confirmed today:** the worktree's `cfb_rankings.db` showed 110 rows in `conversation_documents` (down from 21,188 in earlier snapshots) and 0 rows in `games` / `power_ratings_weekly` / `heisman_market_odds_weekly` / `predictive_claims`. The wipe re-occurred.
- **Impact on this session:** my confidence calibration baseline ran with n=0 across all 5 domains. Fallback thresholds were written; the actual percentile-driven thresholds will populate when the DB recovers and `manage.py recompute-confidence-thresholds` runs again.
- **Recommended:** the next session should add a `git bisect`-style isolation harness on the reddit-deep workflow to find the wipe trigger. Track in the deferred-blocker queue.

---

## F. Tests for v5-7.5 hero_findings package (stubs)

- The `cfb_rankings.hero_findings` package shipped today is a SCAFFOLD. The four generators (`generate_hub_finding`, `generate_daily_finding`, `generate_heisman_finding`, `generate_team_finding`) all return `None`.
- The v5-7.5 sprint fills the generator bodies. The contract is:
  1. Read from real DB tables (`hub_issue_metadata`, `daily_takes`, `heisman_market_odds_weekly`, `fanbase_mood_weekly`)
  2. Build candidate findings + score them
  3. Return the winner or None if no candidate clears the confidence floor
- 8 tests for the scaffold ship today (API surface + render contract). The full sprint adds DB-backed tests for each generator.
- **Update 2026-05-17 23:00:** Window A's PR #102 fixed `_model_summary_for_week` to fall back across weeks, and the next `world_class_enrich` run wrote 15,601 rows to `heisman_rankings_weekly` for season 2025. So **`generate_heisman_finding` is now unblocked at the data level** — the v5-7.5 generator-body sprint can read real candidate odds against the live DB and produce real RACE_SHIFT findings. The local worktree DB still has 0 rows, which is fine — the generator runs against the production DB at render time.

---

## G. Audit script formalization

This autonomous run produced 6 ad-hoc audit scripts in `scripts/_mockup_*.py` and one inline agent dispatch. Recommended formalization:

| Script | Purpose |
|---|---|
| `scripts/_mockup_wcag_audit.py` | WCAG AA contrast verification on token pairs |
| `scripts/_mockup_a11y_audit.py` | HTML accessibility static check |
| `scripts/_mockup_consistency_audit.py` | Cross-archetype HTML pattern consistency |
| `scripts/_mockup_heading_audit.py` | Heading outline (one h1, no skipped levels) |
| `scripts/_mockup_cvd_audit.py` | Color-vision-deficiency simulation on chart palettes |
| `scripts/_mockup_link_audit.py` | Cross-mockup internal link resolution |

**Recommended:** roll these into a single `scripts/design_system_audit.py` that runs all six and exits non-zero on any finding. Wire into CI for the design-system surface.

---

## Status summary

| Item | Status | Blocks | Owner action needed |
|---|---|---|---|
| A.1 Sankey violation | Documented | nothing | YES — spec amend OR migration |
| A.2 Joyplot unclear | Documented | nothing | YES — spec amend |
| A.3 Player fingerprint exception | Track for future | nothing | when fingerprint ships |
| B Profile v5-8.5 fields | ✅ **YAML shipped** (master 95e7d5dd52); renderer wiring is the remaining v5-8.5 work | v5-8.5 renderer | NO — proceeds at sprint slot |
| C Graduated-player UX | ✅ **SHIPPED — Window A PR #101** | nothing | DONE (verified live) |
| D LLM runtime test failures | Pre-existing | nothing | NO — fix when next touched |
| E Reddit-deep wipe | Documented | calibration data | NO — track in next session |
| F hero_findings stubs | Scaffolded | v5-7.5 full impl | NO — proceeds at v5-7.5 |
| G Audit script formalization | ✅ **Shipped** as `scripts/design_system_audit.py` | nothing | DONE |

Generated by Window B autonomous run, 2026-05-17. References:
- [Sprint v5-5.4 mockup set](../mockups/index.html) — 11 surfaces, 33 polish rounds
- [Design-system docs](../design-system/) — 5 locked decisions (00, 30, 31, 32, 33)
- [Window B SESSION_LOG entry](../../SESSION_LOG.md) — Sprint v5-5.5 close + autonomous run
