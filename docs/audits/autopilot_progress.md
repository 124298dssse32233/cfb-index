# CFB Index Autopilot v1 — Progress Tracker

**Kickoff date:** 2026-04-23
**Goal:** bring every ingestable data source current from 2022-09-01 to today, turn the
GitHub Actions cron into real persistent ingestion, and self-audit so the site
updates without Kevin manually asking. Commit per task, log every outcome.

Tick a box only after:
1. The task's `Verify:` line has been satisfied (Haiku subagent / pytest / grep /
   row-count — whichever the task names).
2. A commit `autopilot: TASK X.N — {summary}` has landed.
3. A dated line appended to `SESSION_LOG.md`.

Defaults policy, autonomy rules, and stop conditions live in
`CLAUDE_CODE_KICKOFF_AUTOPILOT.md` — this file is the checklist only.

---

## Workstream 0 — Orientation + data inventory

- [x] TASK 0.1 — Read-first + progress tracker (Sonnet)
- [x] TASK 0.2 — DB inventory (Sonnet + Haiku)
- [x] TASK 0.3 — Scrape-health baseline (Haiku subagent)

## Workstream 1 — CFBD deep backfill

- [x] TASK 1.1 — Connectivity preflight (Haiku subagent)
- [x] TASK 1.2 — Full CFBD history backfill, 2022-2025 regular + postseason (Sonnet) — _effectively complete: data already loaded from prior backfills (252k-277k plays/season for 2022-2024); autopilot re-run failed on a WAL lock, WAL mode now enabled._
- [ ] TASK 1.3 — 2026 in-season + offseason refresh (Sonnet)
- [x] TASK 1.4 — PBP-derived advanced metrics table (Opus design; Sonnet implement)
- [ ] TASK 1.5 — Advanced metrics backfill 2022-2025 (Sonnet)
- [x] TASK 1.6 — Extend Signature Story seed with PBP metrics (Opus seed, Sonnet smoke)
- [x] TASK 1.7 — Weekly CFBD auto-refresh wiring (Sonnet)

## Workstream 2 — Conversation corpus backfill (2022 → today)

- [ ] TASK 2.1 — Reddit historical plan (Opus)
- [ ] TASK 2.2 — Reddit backfill runner (Sonnet)
- [ ] TASK 2.3 — Execute Reddit backfill (Sonnet, long-running)
- [ ] TASK 2.4 — Bluesky historical backfill (Sonnet)
- [ ] TASK 2.5 — Message board backfill (Sonnet, per-board)
- [ ] TASK 2.6 — RSS-family activation (Sonnet)
- [ ] TASK 2.7 — Google News RSS activation (Sonnet)
- [ ] TASK 2.8 — Podcast ASR selective (Sonnet — optional)

## Workstream 3 — Tier-A numeric observation backfill

- [ ] TASK 3.1 — Wikipedia pageviews + edits backfill (Sonnet)
- [ ] TASK 3.2 — GDELT volume backfill (Sonnet)
- [ ] TASK 3.3 — Prediction markets historical (Sonnet)
- [ ] TASK 3.4 — SeatGeek live start (Sonnet)
- [ ] TASK 3.5 — YouTube metadata live start (Sonnet)
- [ ] TASK 3.6 — Spotify charts weekly start (Sonnet)
- [ ] TASK 3.7 — Google Trends weekly (Cowork — playbook only)

## Workstream 4 — Honors, awards, draft, NIL backfill

- [ ] TASK 4.1 — All-America scraper (Sonnet)
- [ ] TASK 4.2 — All-Conference scraper (Sonnet)
- [ ] TASK 4.3 — Position awards backfill (Sonnet)
- [ ] TASK 4.4 — Freshman AA + Shaun Alexander (Sonnet)
- [ ] TASK 4.5 — NFL Draft backfill (Sonnet)
- [ ] TASK 4.6 — Mock draft adapter (Sonnet)
- [ ] TASK 4.7 — NIL valuations snapshot (Sonnet — best effort)
- [ ] TASK 4.8 — Watch lists ingestor (Sonnet)

## Workstream 5 — Player-mention extraction at scale

- [ ] TASK 5.1 — Dry-run the tagger on the full corpus (Sonnet)
- [ ] TASK 5.2 — Tagger tuning (Opus) — only if 5.1 precision < 0.9
- [ ] TASK 5.3 — Commit tagger run on full corpus (Sonnet)
- [ ] TASK 5.4 — Compute player mood weekly + season rollups (Sonnet)
- [ ] TASK 5.5 — Rebuild player pages + spot-check (Sonnet)
- [ ] TASK 5.6 — The Room board + Signature Story board (Sonnet)

## Workstream 6 — Fan Intelligence aggregation backfill

- [ ] TASK 6.1 — Team weekly features (Sonnet)
- [ ] TASK 6.2 — Cohort aggregation backfill (Sonnet)
- [ ] TASK 6.3 — Divergence backfill (Sonnet)
- [ ] TASK 6.4 — Hub v5 weekly data (Sonnet)
- [ ] TASK 6.5 — Storylines refresh (Sonnet)

## Workstream 7 — Phase-aware site + offseason modules

- [ ] TASK 7.1 — Phase detection (Sonnet)
- [ ] TASK 7.2 — Offseason Status chip + 2026 Outlook module (Sonnet)
- [ ] TASK 7.3 — Development Trajectory module (Sonnet)
- [ ] TASK 7.4 — Methodology page global-nav link (Opus single-edit, Haiku diff)
- [ ] TASK 7.5 — Phase S1 voice layer (Sonnet)
- [ ] TASK 7.6 — Draft Day Live skeleton (Sonnet)

## Workstream 8 — Autopilot: real persistence + scheduling + monitoring

- [ ] TASK 8.1 — DB persistence strategy (Opus decision, Sonnet wire)
- [ ] TASK 8.2 — Seed + migrate on every workflow bootstrap (Sonnet)
- [ ] TASK 8.3 — Adapter orchestrator (Sonnet)
- [ ] TASK 8.4 — scrape_health alerting (Sonnet)
- [ ] TASK 8.5 — Weekly site rebuild + publish (Sonnet)
- [ ] TASK 8.6 — Monthly deep-research refresh trigger (Sonnet)
- [ ] TASK 8.7 — Freshness page (Sonnet)
- [ ] TASK 8.8 — Autopilot dashboard CLI (Sonnet)

## Workstream 9 — End-to-end audit

- [ ] TASK 9.1 — Autopilot v1 audit (Opus synthesis + multi-Haiku verification)

---

**Total tasks:** 59 (3 + 7 + 8 + 7 + 8 + 6 + 5 + 6 + 8 + 1).
