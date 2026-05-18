# Claude Code — Fan Intel Wire-Up + Pulse Module Rewire

Paste this entire document into a fresh Claude Code session. Execute autonomously. Sonnet default; Haiku for grep sweeps and feed-URL triage; Opus only for the Pulse module renderer rewrite (schema-reading logic is load-bearing). Target token budget: ~120k.

**Prereq:** GitHub Secrets already provisioned by Kevin 1–2 days ago (CFBD, YouTube, SeatGeek, Spotify, Anthropic). Wikipedia / Bluesky / GDELT / Kalshi / Polymarket need no auth. Assume crons MAY have already been running — check before re-running adapters from scratch.

---

## Context

Fan intelligence infrastructure is built (41 commits, 25+ source adapters, cohort aggregators, floor-rule enforcement). What's missing: data flowing, and the Pulse module on team pages reading from the flowing data instead of the legacy 2024-game-deltas fallback.

Prior work: `FAN_INTEL_BUILD_PLAN.md`, `FAN_INTEL_SOURCE_STRATEGY.md`, `SESSION_LOG.md` (41 commits baseline 2026-04-22), `CLAUDE.md` §Fan Intelligence system.

---

## Context documents — read these first

1. `SESSION_LOG.md` — current state at commit 41
2. `FAN_INTEL_SOURCE_STRATEGY.md` §5 (schema) and §7 (floor rule)
3. `src/cfb_rankings/cohorts/aggregate.py` — output shape of team_cohort_week
4. `src/cfb_rankings/fan_intelligence.py` — `fetch_team_mood_profile` signature
5. `src/cfb_rankings/team_pages/` — find the Pulse template + renderer (where "QUIET · spring and portal" copy lives and where "last 14 days" event log is hardcoded)
6. `CLAUDE.md` — don't touch reporting.py outside the `PROFILED_SLUGS` guard we added in sprint 3

---

## Phase 0 — Check what's already flowing (5 min)

Before touching anything:

```
python manage.py fanintel-status
sqlite3 cfb_rankings.db "SELECT source_key, COUNT(*) as rows, MAX(observed_at) as latest FROM source_observations GROUP BY source_key ORDER BY latest DESC;"
sqlite3 cfb_rankings.db "SELECT team_slug, week, effective_n FROM team_cohort_week ORDER BY week DESC LIMIT 30;"
```

Report which sources already have rows and how fresh. If crons have been running since Kevin provisioned secrets, Wikipedia / Bluesky / GDELT likely have 24–48h of data already. If so:
- Skip Phase 1.2 adapter-runs entirely (data's flowing, don't duplicate)
- Go directly to Phase 1.3 (feed triage on whatever's still failing) and Phase 1.4 (cohort computation)

If Phase 0 shows empty tables, assume crons are scheduled but not executing — fall through to full Phase 1.

## Phase 1 — Data activation (skip if Phase 0 shows data flowing)

### 1.1 Run migrations and seeds

```
python manage.py apply-migrations
python manage.py seed-source-registry
python manage.py seed-priority-teams
python manage.py seed-source-instances
python manage.py seed-feed-instances
python manage.py fanintel-status
```

Confirm all green. If any seed command fails, report the traceback and stop.

### 1.2 Run the 5 auth-free adapters manually

```
python manage.py run-adapter wikipedia
python manage.py run-adapter bluesky-curated
python manage.py run-adapter gdelt-volume
python manage.py run-adapter kalshi
python manage.py run-adapter polymarket
```

For each: report rows ingested, scrape_health status, and any API-shape surprises. If Bluesky firehose requires too long a run for a one-shot, scope it to a 60-second window.

### 1.3 Feed-URL triage (top 10 failures)

`python manage.py scrape-health --show-errors` lists the 47 failing feeds. Take the top 10 by priority (prioritize: beat writers for Tier-1 programs > campus newspapers > podcasts > boards > Substacks).

For each: use Haiku to grep + WebFetch to check whether the URL 404'd, redirected, or went private. For redirects, rewrite the seed YAML. For 404s, mark the row as `needs_research=true` in source_instances so Kevin can fix on his next pass. For 403s (common with Cloudflare-fronted sites), add a realistic User-Agent to the adapter.

Commit the YAML fixes. Do not remove rows; only rewrite URLs or mark needs_research.

### 1.4 Compute cohort aggregations

```
python manage.py compute-cohort-week --week=current
python manage.py compute-divergence --week=current
```

Report effective_n per cohort per priority team. Expected on day-1 (single-source): most teams at effective_n < 30 → "Awaiting Signal" rendering is correct. A few (Alabama, OSU, Georgia, Texas, ND) may cross the floor with just Wikipedia + Bluesky combined; confirm.

---

## Phase 2 — Pulse module rewire (main task)

### 2.1 Locate the Pulse module renderer

The Pulse module is in `src/cfb_rankings/team_pages/`. Find:
- The template that renders `<section class="pulse">`
- The data-provider function that feeds it
- Where "QUIET · spring and portal · signal ramps back in camp" is emitted
- Where the "WHAT MOVED IT — LAST 14 DAYS" event log is emitted (this is currently showing the last 3 games of the 2024 season, which is 4 months old, not 14 days)

Read only what you need — don't load the whole module.

### 2.2 Rewire data flow

Replace the current Pulse data-provider with one that reads from `team_cohort_week` + `source_observations` via `fetch_team_mood_profile`. Preserve the existing seasonal-sentience logic (offseason = quiet state) but source the numbers from live signal, not from game-delta hardcodes.

Contract for the new Pulse provider:
```python
def fetch_pulse(team_slug: str, as_of: datetime) -> PulseState:
    """
    Returns:
      mood_number: int | None  # None = below floor → renders "—"
      mood_delta: int | None   # vs prior week
      velocity: str            # "QUIET" | "STIRRING" | "LOUD" | "ROARING"
      seasonal_state: str      # from state_resolver (spring-and-portal, rivalry-week, etc.)
      moved_it: list[MovedEvent]  # 3-5 events — games, portal moves, signings, social spikes — from the appropriate window for the seasonal_state
      takes: list[Take]        # when available; fallback to profile.stock_phrases when not
      effective_n: int         # for floor-rule display
      sparkline_points: list[float] | None  # None if below floor
    """
```

### 2.3 Fix the "WHAT MOVED IT" label bug

The "LAST 14 DAYS" label is hardcoded. Make it state-aware:

| seasonal_state | label |
|---|---|
| in-season (regular) | LAST 14 DAYS |
| post-loss-sunday-monday | LAST 72 HOURS |
| rivalry-week | RIVALRY WEEK · BUILD-UP |
| dead-period-summer | OFFSEASON · LAST 30 DAYS |
| spring-and-portal | SPRING & PORTAL · LAST 30 DAYS |
| selection-sunday | SELECTION SUNDAY |

And the content of the event log must match the window. In `spring-and-portal`, events should be: portal entries/commits, spring practice milestones, transfer-portal wins, coaching-staff news — NOT game deltas from last fall.

### 2.4 Fix the broken sparkline

From Kevin's screenshot, the sparkline on the left side of the Pulse module is rendering as floating "+29" and "+63" labels with no bars. Either:
(a) render the sparkline properly from `sparkline_points` when `effective_n >= 30`, with one bar per datapoint, colored by direction; OR
(b) hide the entire sparkline slot (including caption "conversation velocity · off-season floor") when no sparkline data is available.

Prefer (b) for day-1 state. Implement (a) as the activation path — when signal arrives, sparkline appears. Guard with the same floor rule as the mood number.

### 2.5 Floor-rule visual treatment

When `effective_n < 30`:
- Mood number: "—" (already correct)
- Mood delta: hidden (not "--")
- Sparkline: hidden entirely (see 2.4)
- "What moved it" event log: still shows (uses game-schedule + portal data, not conversation signal — this is OK below floor)
- Takes section: falls back to `profile.stock_phrases`
- Small effective_n badge at bottom of Pulse: "n=<count> · awaiting signal" in fg-subtle 9px

When `30 <= effective_n < 100`:
- All the above activates
- Show a small "n=<count> · sample size growing" badge
- Sparkline displays with reduced opacity (0.7)

When `effective_n >= 100`:
- Full-fidelity render, no badge

### 2.6 Re-render all 11 profiled programs

```
python manage.py render-team-pages
```

Capture module-class hit counts and effective_n per team. Report which programs crossed the floor on day-1 with just the 5 auth-free adapters.

---

## Phase 3 — Methodology nav hook (tiny surgical edit)

Per CLAUDE.md nav tuples at `reporting.py:11717–11723`, add one entry:

```python
("Methodology", "/methodology/fan-intelligence.html", "How we measure the Pulse"),
```

Confirm `output/site/methodology/fan-intelligence.html` exists (auto-generated by `provenance/methodology_page.py`). Do not refactor anything else in reporting.py. This is surgical.

---

## Decision authority

Autonomous: adapter-run error recovery, YAML URL rewrites, Pulse template structure changes, exact wording of the state-aware event-log label, whether to hide or display sparkline slot below floor.

Stop and flag only if:
- GitHub Secrets turn out not to be provisioned → report which ones are missing, stop before touching hourly cron
- Schema shape doesn't match the `fetch_pulse` contract I wrote above → propose a revised contract and stop
- Pulse template refactor touches more than 2 files outside `team_pages/` → stop and report

---

## Self-verification

- Wikipedia adapter ran, source_observations table has ≥500 rows
- `fanintel-status` shows at least 5 adapters green
- `team_cohort_week` has rows for all 11 priority teams for current week
- All 11 team pages rendered; none errored
- Alabama page: Pulse mood card renders "—" with "spring-and-portal" state-aware label (not "LAST 14 DAYS"). Sparkline either hidden or populated. Takes area shows stock phrase from profile.
- A team that crosses floor (likely Alabama with Wikipedia + Bluesky) shows effective_n badge
- Methodology page reachable from main nav
- No regression on historical-season pages or other modules

---

## Report back with

1. Per-adapter row counts + scrape_health statuses (table form)
2. Feed-URL triage: which 10 were looked at, which rewritten, which flagged needs_research
3. Pulse rewire summary: files touched, contract delta if any, screenshots of Alabama + ND + UMass Pulse states post-rewire
4. Floor-rule crossings: which of 11 programs crossed 30 on day-1; estimate when the rest will (need 2-5 more adapters enabled, typically)
5. Token usage by phase + model
6. Natural next step — usually: GitHub Actions cron enablement + 24h wait + re-compute → broader floor crossings

Report at end, not between phases.
