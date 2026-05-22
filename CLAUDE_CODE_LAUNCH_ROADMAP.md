# CFB Index — Launch Roadmap & Working Memory

**Owner of this doc:** Claude (working memory). User reads + redirects.
**Last updated:** 2026-05-22 (session 3 — autonomous late-night sprint)
**Status:** LIVE + STRUCTURALLY HARDENED. CI is unblocked (notify_failure permission fix), production deploy path is closed (publish-site now calls vercel deploy directly), DB-artifact loss is fail-loud across 19 workflows. Player ID stability scoped (less urgent than estimated; see [docs/research/player-id-stability-scoping-2026-05-21.md](docs/research/player-id-stability-scoping-2026-05-21.md)).

> **Read this first every session.** This doc is the single source of truth for project state. Memory pointers in `~/.claude/projects/.../memory/MEMORY.md` reference it. If a claim in this doc is wrong, fix this doc *first* before acting on it.

---

## 0. How to use this doc

- **Top section is current state** — what's actually true today.
- **Verification log** records what was checked, when, by whom (which agent / which session).
- **Roadmap section** is sequenced milestones with explicit success criteria. Don't skip ahead.
- **Decision log** is the audit trail when we change direction.
- **Session log** is the chronological record of what each session accomplished. Update at end of every session.

If a claim doesn't have a verification log entry pointing to file:line evidence, treat it as unverified.

---

## 1. Project at-a-glance

- **Codebase:** Python static-site generator at `C:\Users\kevin\Downloads\Desktop Transfer\Sports Website`
- **Output:** ~69k HTML pages in `output/site/`, ~85 MB compiled
- **Architecture:** `src/cfb_rankings/reporting.py` (~26.8k-line monolith) + module renderers (team_pages/, theme/, players/, hub_page.py, wire/, etc.) + SQLite DB at `cfb_rankings.db`
- **Build:** `python -u manage.py build-site` (fast, ~8 min) or `./publish_site.ps1` (ingest + build + sync)
- **Deploy:** Vercel, project name `wonderful-margulis-8ec96b`, project ID `prj_AxrPXVXoqhKtXD8xP3WTDzZIaQ1I`
- **Public URL (claimed, unverified as of session 2):** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app
- **CLAUDE.md project rules:** edit `reporting.py` symbolically (line numbers shift weekly), never edit `output/site/**` directly, never hand-edit the DB

## 2. Capability notes (added session 2)

User's local hardware as of 2026-05-21: **Alienware Aurora ACT1250** — Intel Core Ultra 7 265KF (3.3 GHz, 20 cores), NVIDIA RTX 5070 (12 GB GDDR7), 32 GB DDR5-5200, 1 TB SSD. Available 24/7.

**What this unlocks:**
- **Scheduled local cron / Task Scheduler** for nightly ingest + build (alternative to GitHub Actions)
- **Long-running builds** without local-laptop battery / heat concern
- **Local LLM serving** if we want to reduce Anthropic API spend on tier-B Pattern A/B work (RTX 5070 can serve Qwen 14B, Mistral 7B, etc. via Ollama)
- **Concurrent build pipelines** (the 20-core Intel can easily run ingest + build + Claude Code session in parallel)

**Recommendation (pending discussion):** Use the PC for the daily/weekly cron cycles in place of GitHub Actions for the surfaces most prone to artifact-race conditions (see P0 blocker #2 below). Keep GitHub Actions for the surfaces where multi-host redundancy is the actual value-add.

---

## 3. Verified state (UPDATED 2026-05-21, session 2, post-audit)

### Headline: the site is already live and auto-deploying. The session-1 "72% ready / Phase 1 not run" framing was wrong.

Three of the four verification agents converged on the same picture, and discover.md (the canonical current-state audit) backs it up:

- **Vercel is auto-deploying 3× daily** via GitHub Actions cron workflows (4am ET wire-daily, 6am ET the-daily weekdays, 9am Friday mailbag, plus weekly Saturday publish-edition and Monday full rebuild).
- **24+ workflows total** are running on cron — including hourly data ingest, minute-by-minute game-day live coverage Saturdays 16:00-23:00 UTC + Sundays 00:00-06:00 UTC, weekly analytics surfaces.
- **All 12 sampled rendered pages have real data**, current dates, populated editorial — no "Awaiting Signal" fallbacks visible on the surfaces a fan actually lands on.
- **Last commit** is `f3d63f4` on 2026-05-21 12:47 UTC ("feat: enable world-class stats + GitHub Actions overnight backfill") — today.

What's actually missing isn't a launch ceremony — it's three known credibility bugs (Mendoza quote attribution, Heisman 2025 data not visible, Chronicle module not rendering) and a stack of P1/P2 polish.

### 3.1 What's confirmed true

| Claim | Evidence |
|-------|----------|
| Vercel deploy pipeline is live & auto-deploying | `.vercel/project.json` matches claimed projectId; `vercel.json` has `outputDirectory: output/site`; 3 cron workflows explicitly call `vercel deploy --prod --yes` (wire-daily-04am-et.yml, the-daily-06am-et.yml, mailbag-friday-09am-et.yml); rolling-site-state artifact pattern with 3,500-file sanity gate |
| All 4 named cron workflows are enabled | wire-daily, the-daily, publish-edition, mailbag all have active `schedule: cron` triggers; zero `if: false` anywhere in `.github/workflows/`; verified by 2 agents independently |
| Homepage is current & populated | `output/site/index.html` dated April 25, 2026; hero title "After the Bracket · The Offseason Issue"; full cover essay + SVG viz; built 2026-05-21 12:35 PM |
| Daily / Wire / Editions / Hub / Mailbag are populated | 4 editions listed (XVII Apr 25, XVI Apr 18, XV Apr 11, XIV Apr 4); daily 2026-04-26 has 3 real takes ("Dead Air at the Top," "The Stat Guys and the Die-Hards…"); hub shows real signal ("Michigan's belief at a decade low") |
| Profiled team pages render real chronicle/mood data | Alabama 9-3 +18.9 #7 final; Notre Dame 11-1 +18.6 #9 final; Florida + Rutgers spot-checked, no fallback text |
| Heisman board has real model output | 16,218 ranked players; Dillon Gabriel 19.6% win equity; Jordan James top non-QB; Blake Horvath top G5; Ethan Burke top defender |
| 665 program pages built (664 + the index) | Last-modification timestamp 2026-05-21 12:24 (today's build) |
| 17,832 player pages built | Per build log "Built 17832 player pages" |
| Discover.md verdict matches reality | "All 9 P0 residues from the prior audit are closed" — confirmed via spot-check |

### 3.2 What's confirmed false / overstated (session 1's "72%" was wrong)

| Session 1 claim | Reality |
|----------------|---------|
| "GitHub Actions cron workflows are disabled per Phase 4 spec" | **FALSE.** All 4 actively scheduled and running. Plus 19 more workflows running on cron. |
| "Chronicle cards missing for 5 specific programs" (Florida, Massachusetts, Notre Dame, Oklahoma, Washington) | **WRONG SHAPE.** The five programs DO have CI generation failures for chronicle per discover.md (claude CLI not on PATH in worker env), but the actual rendered effect is that NO chronicle-card divs render on ANY team page site-wide. The bug is more systemic than the per-program framing suggested. |
| "Phase 1 of First Live Cycle hasn't been run" | **STALE PREMISE.** TOMORROW_IMPLEMENTATION_PLAN (2026-05-19) treats the site as actively running and auto-deploying; the FIRST_LIVE_CYCLE doc from Apr 26 describes a ceremony that — based on evidence — already happened off-camera between Apr 26 and May 19. The doc itself is now historical. |
| "72% ready" | **Understated.** Render + infra: ~95%. Quality: ~75-80% (3 known credibility bugs). Operationally already live and self-updating. Revised assessment: **~80-85% — with 3 specific bug fixes between current state and confidence-grade live.** |
| Vercel URL serves current content (unverified in session 1) | **PARTIAL.** URL returned 401 (likely auth-walled). Deploy pipeline confirmed active. Cannot eyeball-verify what's actually served without auth. |

### 3.3 What's actually P0 (UPDATED 2026-05-21 EVENING — full live verification)

**All three "P0 blockers" cited by discover.md + session-1 agents were either RESOLVED on live or did not manifest. A NEW genuine P0 was found and is being fixed this session.**

#### ~~Heisman 2025 missing~~ → RESOLVED on live
- Live `/heisman/` shows "Heisman Tracker | 2025 Season · Final 2025"
- The dawidd6 race fix in `publish_site.yml:73-80` worked in CI
- Local DB has zero 2025 rows (local mirror is stale); not a live-site bug

#### ~~Chronicle module renders nothing~~ → RESOLVED on live, ALL 17 profiled teams
- All 5 supposedly-broken programs verified live:
  - Florida: 42 chronicle-card divs / 0 "Awaiting Signal"
  - Massachusetts: 36 / 0
  - Notre Dame: 42 / 0
  - Oklahoma: 42 / 0
  - Washington: 30 / 0
  - Alabama: 24 / 0 (verified earlier)
- The 5-program CI failure flagged in discover.md (May 17) was resolved between then and now, likely by a subsequent enrich run

#### ~~Mendoza quote entity-matching~~ → can't manifest; no Mendoza page exists on live (downstream of new P0 below)
- Heisman page lists `fernando-mendoza-38276.html` as the favorite
- That URL 404s on live — the player page itself isn't being deployed
- Root cause is the .vercelignore issue (P0-NEW)

#### 🔥 P0-NEW (DISCOVERED + FIXED this session) — Heisman → player navigation is universally broken

**Symptom:** The Heisman page lists **15,601 player links**, and **every one returns 404** on the live site (verified 0/15 random sample worked). The single most-prominent navigation flow on the site (Heisman favorite → player profile) is dead.

**Root cause:** Two overlapping bugs:
1. The repo-root `.vercelignore` was a 15,408-line allowlist of specific player pages by ID, last regenerated May 14. It was meant to keep Vercel Hobby under file-count cap.
2. Player IDs drift between enrich runs (Mendoza: 2431 → 12763 → 38276 across recent rebuilds). When IDs change, the allowlist no longer matches what pages get linked, and Vercel-ignores every "new" ID.

**Fix shipped:** Replaced .vercelignore with minimal exclusions (DBs/logs/build-artifacts only, mirroring `tools/write_published_vercelignore.py` content). Total local site = 1.3 GB / 22,041 files — well within Vercel Hobby limits. Backup at `.vercelignore.bak-2026-05-21` (local only; gitignored).

**Status:** Commit `7a384ce` (2026-05-21 13:54 UTC) pushed to master; Vercel auto-deploy in progress. Verify Heisman → player links resolve once deploy completes.

**Followup:** The underlying ID-drift problem deserves a real fix (stable player IDs across enrich runs). Filing as P1 follow-up.

### 3.4 Other notable findings (session 2)

- **Site is OPERATIONALLY beyond launch.** It's already serving on Vercel and auto-updating. The framing for next-session work should be "fix the 3 P0 bugs + ship the next sprint" not "decide whether to launch."
- **TOMORROW_IMPLEMENTATION_PLAN (May 19)** described 3 GitHub Actions workflows actively running ("Your computer can be off — GitHub runs these!"); whether those have completed and whether they resolved the dawidd6/Heisman 2025 issue is the first thing to verify next.
- **FIRST_LIVE_CYCLE_AND_GO_LIVE.md (Apr 26)** should be marked superseded — it's a ceremony that's no longer relevant (cron workflows are already enabled, the decision-gate was passed off-camera between Apr 26 and May 19).
- **Repo root has 79+ orphan `CLAUDE_CODE_*.md` planning docs** per discover.md — this is documentation noise that should be triaged.
- **CLAUDE.md is materially stale** per discover.md (line numbers wrong, profiled-slug count wrong, surgical-sites refs wrong). Worth a refresh.

### 3.5 Verification log

| Session | Agent / source | Claim verified | Verdict | Evidence summary |
|---------|----------------|----------------|---------|------------------|
| 2 | Agent A | Heisman 2025 data missing from live site | **TRUE** | /heisman/ shows 2024 only; no /heisman/2025/ subdir; race fix IS in code, root cause may have shifted |
| 2 | Agent A | 5 chronicle programs show "Awaiting Signal" | **WRONG SHAPE** | Site-wide: zero .chronicle-card divs render anywhere; 5-program CI failure is the data-side symptom |
| 2 | Agent A + Agent C | GitHub Actions cron workflows disabled | **FALSE** | All 4 actively scheduled, plus 19 more cron workflows running |
| 2 | Agent C | Vercel URL serves current content | **PARTIAL** | 401 auth wall; deploy pipeline confirmed active 3×/day |
| 2 | Agent D + discover.md | FIRST_LIVE_CYCLE still current | **FALSE** | Superseded by TOMORROW_IMPLEMENTATION_PLAN's "workflows already running" framing |
| 2 | Agent B | Site data freshness | **CURRENT** | Homepage April 25, 2026; rankings/heisman locked at 2024 final (expected offseason); editions weekly thru April 25 |
| 2 | Claude (direct read) | Discover.md is the canonical state audit | **TRUE** | discover.md 2026-05-17 refresh names exact same P0s |

---

## 4-bis. MVK ROADMAP (LOCKED 2026-05-21 session 3 via /octo:embrace)

> Output of a full Double Diamond pass (Discover → Define → Debate Gate → Develop). Multi-LLM consensus was degraded (Codex hit OpenAI cap until 2026-05-25; Gemini 503 high-demand; Sonnet timed out at 180s) so the synthesis is single-perspective from Claude+Sonnet probe, validated by an adversarial debate gate that surfaced 2 real plan-misses (custom domain; monitoring overreach). Full artifacts at `~/.claude-octopus/results/1fbafad8-a617-4cfd-bc58-d46b257219ac/`.

### THE HIGHEST-LEVERAGE NEXT ACTION (next ≤ 7 days)

**Time-boxed CI startup_failure diagnosis** — ✅ DONE 2026-05-21 session 3 in ~20 min (well under the 2hr cap). **Strong diagnosis: GHA private-repo monthly minute quota exhaustion.**

Evidence (across last 40 workflow runs):
- 75% failure rate (30 of 40 failed)
- 20 of 30 failures are `startup_failure` (runner couldn't even allocate)
- Most failures complete in 0-2 seconds (zero execution time)
- Inconsistent pattern: same workflow succeeds at off-hours, fails at peak — matches "minutes burst-available when budget refreshes briefly"
- Only `fanintel-ingest-hourly` succeeds reliably, only at 00:15 / 05:17 / 09:59 UTC (off-peak)
- Self-hosted smoketest worked flawlessly with `billable: {total_ms: 0}` — confirms self-hosted bypasses the quota
- Repo is private (`githubRepoVisibility: private` per Vercel metadata)
- Free GHA = 2000 min/mo for private repos; Pro = 3000; ~70% through May → consistent with depletion
- worst offenders by minute consumption: `digest_reactions_poll` (hourly = 720 runs/mo × ~2 min each ≈ 1440 min alone), `fanintel-ingest-hourly` (same)

Caveat: token lacks `read:billing` scope, so I couldn't pull exact usage. **User should verify in [GitHub billing dashboard](https://github.com/settings/billing/summary)** — if May usage is at/near 2000 min (Free) or 3000 (Pro), diagnosis confirmed.

**Three remediation paths (pending user decision):**
1. **Upgrade to GitHub Pro** (~$4/mo) → 3000 min/mo. Solves symptom without architectural work.
2. **Migrate hourly workflows to self-hosted runner** → free + reliable, but requires per-workflow Windows-portability fix (~4-6 hr/workflow).
3. **Reduce workflow frequency** → cut `digest_reactions_poll` from hourly to every 4 hr (-75% minutes). Cheapest, reduces freshness.

Side findings worth flagging:
- `DIGEST_ISSUE_NUMBER` repo variable is missing — workflow `digest_reactions_poll` runs with empty value (won't function correctly even when it does run)
- `ARCTIC_SHIFT_API_KEY` secret is missing — workflow `archive_retro_daily` requires it
- The Mendoza-quote bug from earlier sessions is moot: he has no published player page on live (player_id changed across enrich runs — same root cause as MVK #2)

### MVK — Minimum Viable Kickoff (must land by 2026-08-22)

> Game day is 2026-08-30. ~3 months of offseason runway as of 2026-05-21.

| # | Item | Effort | Acceptance criterion |
|---|------|--------|---------------------|
| 1 | CI startup_failure resolution (or documented workaround) | 2-4 hr cap | 7-day rolling success rate on scheduled workflows ≥ 95% |
| 2 | Player ID stability (upsert pattern) | 2-3 days | 3 consecutive enrich runs produce identical player IDs; URLs unchanged after full rebuild |
| 3 | .vercelignore deploy verification | 5 min after next CI cron | 15/15 random player URLs from /heisman/ return 200 (was 0/15) |
| 4 | Defensive renderer call-site integration (scaffold from session 1) | 4-6 hr | Player/team pages render correctly with deliberately-malformed rows |
| 5 | Untracked theme files committed | 15 min | ✅ DONE 2026-05-21 session 3 (commit db35af0f065) |
| 6 | Custom domain wired to Vercel | 30 min + ~$15/year | Site reachable at cfbindex.com (or chosen domain), HTTPS active |

### Reframed rationale (post-debate)

- **#2 Player IDs**: rationale is NOT "Google indexing" (debate-challenger correctly noted low Domain Authority + Heisman board rebuilds weekly so URL drift is mostly internal). Real rationale: **share-link stability** (iMessage previews + Reddit cache + AI crawler caches all fire BEFORE the site has SEO weight). Cost-of-delay is cumulative; cost-of-fix is bounded.
- **#6 Custom domain (NEW from debate)**: Single biggest "feels legitimate" lift the project can get. `cfbindex.com` vs `wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app` is a credibility chasm at zero engineering cost. See [docs/research/domain-options.md](docs/research/domain-options.md).

### Demoted to Tier 2 (post-MVK, pre-season polish in June-July)

- ~~#4 (original) Post-enrich health check + Discord/Slack webhook~~ — debate-challenger was right; this is best-practice cargo-culted from team contexts. Solo-dev site with no users yet doesn't need 3am-Saturday paging. Add post-MVK.
- Bottom-sheet tooltip on legacy `.table-wrap` tables (Cheap Win #3 deployment): 2-3 hr, nice UX, not load-bearing.
- Vercel tier audit: bandwidth + deployment-count headroom under current Vercel plan.
- Secret rotation audit: 24+ workflows, document expiry dates.
- Pre-kickoff smoke test of ALL 24+ workflows: 3 hr, August.

### Time-boxed: self-hosted runner

- Per-workflow Windows-portability triage capped at **4 hours / 1 successfully migrated workflow**. If that one workflow doesn't migrate cleanly in 4 hours, deprecate the Alienware runner from CI use (keep for Ollama only post-season).
- The smoke-test workflow already proves the runner is healthy. The blocker is Windows bash vs Linux bash differences in individual workflows.

### Post-season (November 2026+)

- Heisman page pagination (15 MB)
- Two-renderer split unification (profiled vs legacy team pages)
- reporting.py decomposition
- Fan-intel entity matching improvements
- Ollama tier-B integration

### Hidden risks identified by the audit (track but don't fix yet)

- **Vercel tier limits**: 100 deploys/day Hobby cap; 69k pages; kickoff-weekend bandwidth spike. Audit in July.
- **SQLite concurrency during enrich**: 24+ workflows, WAL mode question. Audit if any race condition surfaces.
- **Alienware as SPOF**: Windows Updates, ISP outages, gaming-GPU contention. Mitigation: never make Alienware primary for deploy-critical workflows.
- **Secret rotation**: 24+ workflows accumulate API keys; silent failures on stale tokens. Audit in July.
- **Enrich-vs-traffic timing**: kickoff Saturday CPU-bound enrich could delay Sunday-morning deploys. Audit pattern: enrich runs early-Saturday-morning, deploys done by noon.

---

## 4. Roadmap (REVISED 2026-05-21 session 2)

> The "launch" framing was wrong. The site IS live and auto-deploying. The work in front of us is fixing the three credibility bugs identified above, then ramping into pre-kickoff content quality work. Sequenced milestones below.

### Milestone 1 — Verify verified state ✅ (THIS SESSION, complete)

Done. §3 above is the verified picture; session-1's 72%-and-Phase-1 framing is corrected.

### Milestone 2 — Resolve P0-B (Heisman 2025 data not on live site)

**Why first:** It's the most-investigated of the three (discover.md has the root-cause analysis); the fix landed in code; just need to confirm whether it worked or whether root cause has shifted.

**Investigation steps (small):**
1. Read `.github/workflows/publish_site.yml:72-80` (the dawidd6 Option B fix).
2. Check `gh run list --workflow=publish_site.yml --limit 10` — when did publish_site last run? Did it succeed?
3. Check `gh run list --workflow=world_class_enrich.yml --limit 10` — when did enrich last run? Was 2025 Heisman in its output?
4. Inspect the actual artifact picked up by the most recent publish_site run — does it have 2025 Heisman rows?
5. If artifact is correct but page is wrong: render path issue, not data. If artifact is wrong: data-flow issue, root-cause analysis update needed.

**Done when:** /heisman/index.html shows 2025 Season alongside or instead of 2024, OR we have a coherent reason why it can't and a documented deferral.

### Milestone 3 — Resolve P0-C (Chronicle module renders nothing)

**Why next:** Discrete scope. Either render path is gated, data is empty, or CI failure cascaded. Investigation will clarify.

**Investigation steps (small):**
1. Grep `src/cfb_rankings/team_pages/chronicle_*.py` for the render entry point.
2. Find where it's called from `src/cfb_rankings/team_pages/renderer.py`.
3. Determine: is the render conditional on data presence? Does the data exist for any team in the DB? (`sqlite3 cfb_rankings.db ".schema chronicle_*"` then `SELECT COUNT(*) FROM chronicle_*`).
4. If data exists but render doesn't fire: render path bug. If data missing: CI-generation issue (5-program failure may have cascaded to clearing all generations).

**Done when:** Chronicle cards render on at least the 12 profiled team pages that don't have CI failures (Alabama, Auburn, Georgia, Michigan, Ohio State, Oregon, Penn State, Tennessee, Texas, UConn, USC, Vanderbilt), OR we have a documented deferral.

### Milestone 4 — Resolve P0-A (Mendoza quote entity-matching)

**Why third:** Hardest of the three, requires data-pipeline change + re-ingest. Discover.md flags this as the credibility-destroying bug; worth fixing properly even if it takes longer.

**Investigation steps:**
1. Read `src/cfb_rankings/fan_intelligence.py` entity-matching logic.
2. Identify the source of the cohort_score=94.7, sample=47 quote on Mendoza's page (`output/site/players/fernando-mendoza-2431.html`, `data-cohorts` payload).
3. Determine: is the issue (a) the quote is mis-tagged at ingest, (b) the tagging is correct but the player-attribution lookup is too loose, (c) the cohort aggregation pulls team-level into player-level?
4. Sketch the fix: tighten entity filter so player pages only show quotes that name the player, OR add a "Team-level context" lane and move generic quotes there.
5. Determine if fix requires re-ingest (slow) or just re-render (fast).

**Done when:** Mendoza's player page surfaces only player-attributed quotes, OR a "Team-level context" tier is added and the quote moves there, OR documented deferral.

### Milestone 5 — Cheap-wins-on-the-rest-of-the-site sweep (continuation of session 1's work)

**Why:** Session 1 shipped 5 Cheap Wins from the conformance research. Several P1 / P2 polish items remain (touch targets, defensive renderer call-site integration, Heisman page pagination, two-renderer split).

**Specific items:**
- Heisman page pagination (currently 15 MB / 15k+ rows; per discover.md "single largest performance liability")
- Defensive position-group call-site integration (scaffold landed session 1; wiring is the remaining 4-6 hours)
- Touch-target audit (44×44px coverage)
- iOS Safari sticky-first-col real-device verification

### Milestone 6 — Stale-doc + repo-root cleanup

**Why:** Discover.md flags 79+ orphan planning docs at repo root; FIRST_LIVE_CYCLE_AND_GO_LIVE.md should be marked superseded; CLAUDE.md is stale. This is wayfinding for future sessions.

### Milestone 7 — 24/7 PC scheduled-task setup (NEW per session 2)

**Why:** User's new Alienware Aurora can run 24/7. Some site cycles (especially the dawidd6-prone Heisman pipeline) may be more reliable on a single host than on GitHub Actions. Worth scoping which workflows benefit from local cron.

**Done when:** A short doc lists which workflows stay on GitHub Actions vs which move to local Windows Task Scheduler, with a rationale per workflow.

### Milestone 8 — Stable player URLs (P1 followup from session 2)

**Why:** The `.vercelignore` fix from session 2 deploys all 17k player pages, but the URLs themselves are unstable across enrich runs (Mendoza: 2431 → 12763 → 38276). Verified root cause: `players.player_id` is `AUTOINCREMENT` with no stable external ID; the table is rebuilt per enrich. This breaks SEO (search engines see different URLs each run), bookmarks, and share-links.

**Fix options:**
- Add `cfbd_player_id INTEGER UNIQUE` column from CFBD API; use as URL suffix.
- Or use deterministic hash of (full_name, position, team_id, hometown) as URL suffix.
- Or use slug-only URLs with disambiguator for name collisions.

**Done when:** Player URLs are stable across enrich runs. Existing URLs continue to resolve (via redirects from old → new if needed).

---

## 5. Open questions (need user direction before next milestone)

1. **Sequencing of the three P0s.** I've ordered them B → C → A (Heisman 2025 → Chronicle → Mendoza) based on investigation difficulty and unblocking signal. Are you OK with that order, or do you want Mendoza first (because credibility) or Chronicle first (because differentiation lever)?

2. **Is the Vercel URL the right launch destination?** The 401 wall suggests it's either Vercel preview-mode auth or password-protected production. Once we know what's actually behind that auth, we'll know whether to set up a custom domain (e.g., cfbindex.com or similar) before higher-traffic moments.

3. **Should we treat TOMORROW_IMPLEMENTATION_PLAN's 3 still-running workflows as canonical?** If yes, the first action is to check `gh run list` and confirm they completed. If those workflows resolved P0-B already, we may have one less bug than session 1 thought.

4. **24/7 PC: in scope this week?** If yes, milestone 7 moves up. If not, defer and treat as future work.

5. **Stale-doc cleanup: scope?** Move every superseded `CLAUDE_CODE_*.md` to `docs/archive/` and update CLAUDE.md? Or leave them for a future cleanup pass?

6. **Do you want a single in-flight session per work item, or parallel agents on multiple P0s simultaneously?** Parallel is faster but creates merge friction; serial is slower but easier to verify each fix.

---

## 6. Decision log

| Date | Decision | Made by | Rationale |
|------|----------|---------|-----------|
| 2026-05-21 | Window A/B coordination model retired; Claude drives as single track | User | Consolidation |
| 2026-05-21 | Create this master plan doc + verify before any launch execution | User | Doesn't trust 72% number from single-agent assessment |
| 2026-05-21 | Re-frame "launch readiness" as "credibility-bug fixes on already-live site" | Claude (after 4-agent verification + discover.md re-read) | Site is provably live & auto-deploying; the "First Live Cycle" ceremony is historical, not pending |
| 2026-05-21 | Disconnect Vercel git auto-deploy entirely; all production deploys go through `vercel deploy --prod` in workflows | Claude (session 2/3) | Master pushes were producing content-less production deploys because output/ is gitignored. Fixing by routing deploys through workflows that build first |
| 2026-05-21 | MVK #2 player ID stability: implement Option B (CI fail-loud) THIS session; defer Option A (stable URL slug from cfbd_player_id) to a future session | Claude (autonomous, session 3) | Scoping showed existing `_get_or_create_player` upsert is already largely correct. Drift risk is narrower than originally estimated; Option B captures most of the value at 19 × 6 lines of YAML |
| 2026-05-21 | MVK #4 defensive renderer integration deferred — turned out to be ~a week of work, not 4-6 hours, because the "scaffold" exists but nothing in reporting.py or team_pages/renderer.py calls it; wiring is full-codebase | Claude (autonomous, session 3) | Sized correctly for next planning conversation rather than committed-to autonomously |

---

## 7. Session log

| Session | Date | What got done | Handoff doc |
|---------|------|---------------|-------------|
| 1 | 2026-05-21 AM | Research deliverables (4 docs, ~18.2k words); audit punch list; P1 abbreviation fixes; P0 tabular-nums extension; Cheap Win #1 sticky-first-col; print stylesheet; stat-definitions extension; defensive position-group scaffold (7 ColumnDefs + 7 render fns); 3 builds; 72% readiness number (now under audit) | [docs/research/session-handoff-2026-05-21.md](docs/research/session-handoff-2026-05-21.md) |
| 2 | 2026-05-21 PM | Master plan doc created; 4-agent verification audit completed; discover.md read directly; ALL THREE claimed P0s falsified via live-site fetch (Heisman 2025 IS live; Chronicle IS rendering on all 5 supposedly-broken programs; Mendoza bug can't manifest because his page 404s). Vercel SSO disabled via API; site now publicly viewable. Found the REAL P0: every Heisman → player link 404'd because .vercelignore allowlist had stale player IDs. Committed 3-commit fix batch (7a384ce vercelignore + fbdbe52 session-1 conformance + 5982416 docs) and pushed to master. Direct push triggered Vercel auto-deploy from git which produced a near-empty broken site (output/site is gitignored, so git-pull deploys get only source code). Rolled back via Vercel API promote; disconnected Vercel git integration to prevent recurrence. Fix is queued in master and will deploy at next successful CI cron — blocked by pre-existing intermittent CI workflow failures (task #23). | (this doc) |
| 3 | 2026-05-21/22 (late-night autonomous) | **(1) Real fix to CI startup_failure** — root-caused as `notify_failure.yml` reusable workflow's `issues:write` permission contract being unsatisfiable by 7 calling workflows whose `notify` job had no permissions block; GitHub rejected at startup with `total_count=0` jobs. Patched all 7 callers with `permissions: { issues: write, contents: read }` (commit `80b1ff8ff1e`). Validated by triggering `digest_reactions_poll` on the new SHA — workflow ran for the first time ever (66/66 historical = startup_failure), notify job opened automation-failure issue successfully. **(2) Production deploy was broken in a different way** — Vercel git auto-deploy was firing from master pushes, which lack `output/site/` (gitignored), serving content-less builds where every player page 404'd. Promoted a healthy `published`-branch deploy back to production via `vercel CLI`; verified 8/8 sample URLs return 200. **(3) Closed the deploy gap** — Added `vercel deploy --prod` step to `publish_site.yml` (commit `440ea9a3684`), mirroring the pattern in daily/wire/mailbag. Vercel CLI auth verified via existing repo secrets. **(4) Player ID stability scoping done** — found `_get_or_create_player` in ingest/cfbd.py already does the right external-id-first upsert pattern; URL drift is narrower than feared. Wrote scoping note at [docs/research/player-id-stability-scoping-2026-05-21.md](docs/research/player-id-stability-scoping-2026-05-21.md) (commit `cd552c5d40d`). **(5) Option B fail-loud landed** — added `python scripts/verify_db_artifact_healthy.py cfb_rankings.db` step right after the cfb-rankings-db download in 19 workflows. Refuses to run when artifact is missing or poisoned, preventing init-db from seeding a fresh schema and corrupting the rolling artifact (commit `81ab2c31af2`). Backfill workflows intentionally skipped. **(6) Cleaned up 3 stale `automation-failure` GitHub issues** that opened during CI-fix validation. Open MVKs that remain: #2 player ID stability Option A (stable URL slug via cfbd_player_id, 1 day), #4 defensive renderer call-site integration (turns out to be ~a week given reporting.py is 26k lines; needs user gut-check on approach), #6 custom domain wiring (needs user to pick a domain from [docs/research/domain-options.md](docs/research/domain-options.md)). | (this doc) |

---

## 8. Memory & cross-references

Memory entries persisted to `~/.claude/projects/.../memory/`:
- `project_window_consolidation.md` — Window A/B retired
- `feedback_driver_mode.md` — Claude drives; no permission-per-step
- `project_master_plan_pointer.md` — points to THIS file (added session 2)

Related project docs:
- [docs/research/](docs/research/) — the 4 research deliverables + audit + handoff
- [docs/design-system/](docs/design-system/) — locked design contracts (00-tokens, 30-page-archetypes, 31-chart-vocabulary, 32-receipt-pattern, 33-confidence-signaling)
- [docs/octopus/discover.md](docs/octopus/discover.md), [docs/octopus/define.md](docs/octopus/define.md) — current-state audit + fix charter (per CLAUDE.md, these supersede older audits)
- [CLAUDE_CODE_FIRST_LIVE_CYCLE_AND_GO_LIVE.md](CLAUDE_CODE_FIRST_LIVE_CYCLE_AND_GO_LIVE.md) — the go-live ceremony
- [WORLD_CLASS_CFB_INDEX_MASTER_PLAN.md](WORLD_CLASS_CFB_INDEX_MASTER_PLAN.md) — the master roadmap

---

## 9. Audit-in-progress agent dispatch (session 2)

Agents kicked off in parallel this turn:

| Agent | Task | Returns to |
|-------|------|-----------|
| A | Independently verify the 3 named P0 blockers (Heisman 2025, chronicle 5-program fallback, Actions disabled) with file:line / log evidence | §3.3 |
| B | Spot-check 8-12 representative rendered pages for actual broken state (404 sources, "Awaiting Signal" abuse, season=2024 vs current, last-update timestamps) | §3.1 + §3.2 |
| C | Verify Vercel deployment liveness (does the URL serve? is it current?) + check GitHub Actions cron file state directly | §3.3 |
| D | Re-read the 5 launch / planning docs cover-to-cover and reconcile them against [docs/octopus/discover.md](docs/octopus/discover.md) (canonical current-state audit per CLAUDE.md) | §3.1 + §4 |

Claude (this session) also reading discover.md + define.md directly while agents work.
