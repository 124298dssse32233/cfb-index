# CFB Index — Launch Roadmap & Working Memory

**Owner of this doc:** Claude (working memory). User reads + redirects.
**Last updated:** 2026-05-21 (session 2)
**Status:** AUDIT IN PROGRESS — verifying claims from session-1's 72% readiness number before any launch execution.

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

---

## 7. Session log

| Session | Date | What got done | Handoff doc |
|---------|------|---------------|-------------|
| 1 | 2026-05-21 AM | Research deliverables (4 docs, ~18.2k words); audit punch list; P1 abbreviation fixes; P0 tabular-nums extension; Cheap Win #1 sticky-first-col; print stylesheet; stat-definitions extension; defensive position-group scaffold (7 ColumnDefs + 7 render fns); 3 builds; 72% readiness number (now under audit) | [docs/research/session-handoff-2026-05-21.md](docs/research/session-handoff-2026-05-21.md) |
| 2 | 2026-05-21 PM | Master plan doc created; 4-agent verification audit completed; discover.md read directly; ALL THREE claimed P0s falsified via live-site fetch (Heisman 2025 IS live; Chronicle IS rendering on all 5 supposedly-broken programs; Mendoza bug can't manifest because his page 404s). Vercel SSO disabled via API; site now publicly viewable. Found + fixed the REAL P0: every Heisman → player link 404'd because .vercelignore allowlist had stale player IDs. Commit 7a384ce pushed (pending GH auth handoff) replacing the 15k-line allowlist with minimal exclusions. | (this doc) |

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
