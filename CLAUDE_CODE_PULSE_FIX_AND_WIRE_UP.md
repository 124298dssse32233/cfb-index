# Claude Code — Pulse Rendering Fixes + Fan Intel Wire-Up

Paste this whole document into a fresh Claude Code session — **run this in parallel to Sprint 5** (which is executing historical-season Opus graduation + narrative fanout for the 6 new programs). This prompt does not touch anything Sprint 5 is touching. Sonnet default; Haiku for triage sweeps; Opus not needed. Budget: ~100k tokens.

---

## Context

Two work streams collapsed into one sprint because they share the Pulse module:

**(A) Two visible rendering bugs on the Pulse module** (from Kevin's screenshot of the ND team page):
- "WHAT MOVED IT — LAST 14 DAYS" is hardcoded — currently showing Wk 12/13/14 of the 2024 season (4 months old, not 14 days).
- Left-side sparkline renders as floating "+29" / "+63" labels with no bars, plus an orphan "conversation velocity · off-season floor" caption.

**(B) Fan intelligence wire-up.** Infrastructure is 85% built (41 commits, 25+ adapters, cohort aggregators, floor-rule). GitHub Actions `fanintel-ingest-hourly` has been running cleanly for ~24 hours (14 successful runs @ 2m each). Data is flowing into `source_observations`; Pulse module still reads from the legacy 2024-game-deltas fallback and needs to be rewired to the live pipeline.

Fixing (A) + wiring (B) together makes sense because the sparkline and the label both depend on the Pulse data provider, which is what (B) rewires.

---

## Coordination with Sprint 5 (running in another Claude Code window)

Sprint 5 is touching:
- `src/cfb_rankings/team_pages/historical_season_generator.py`
- `src/cfb_rankings/team_pages/narrative_generator.py`
- `src/cfb_rankings/team_pages/chronicle_generator.py`
- `profiles/*.md` (6 new program profiles)
- Historical-season rendered HTML
- `team_season_narratives` + `team_chronicle_observations` tables

**This prompt must not touch any of those.** You own:
- Pulse template + renderer (`src/cfb_rankings/team_pages/` — the Pulse-specific files only)
- Pulse data-provider function (likely `fan_intelligence.py` or a new `team_pages/pulse_data.py`)
- `team_cohort_week` + `source_observations` reads (read-only)
- `seeds/` YAML feed-URL rewrites (Sprint 5 isn't touching these)
- One surgical nav-tuple addition in `reporting.py` at line ~11717

If a file conflict shows up, stop and report. Do not try to merge.

---

## Context documents — read these first

1. `FAN_INTEL_SOURCE_STRATEGY.md` §5 (schema) and §7 (floor rule: <30 = Awaiting Signal, 30–100 = sample-size badge, ≥100 = full render)
2. `src/cfb_rankings/cohorts/aggregate.py` — team_cohort_week output shape
3. `src/cfb_rankings/fan_intelligence.py` — `fetch_team_mood_profile` signature
4. Locate the Pulse template + data provider in `src/cfb_rankings/team_pages/` — grep for `pulse__mood`, `pulse__title`, `LAST 14 DAYS`, or `spring and portal`
5. `SESSION_LOG.md` — current fan-intel commit baseline
6. `CLAUDE.md` §Fan Intelligence system + §"Don't touch reporting.py" (single-line nav-tuple addition in Phase 4 is the only exception)

---

## Phase 0 — Discover what's already flowing (5 min)

GitHub Actions has been running for ~24h; there should be data.

```
python manage.py fanintel-status
sqlite3 cfb_rankings.db "SELECT source_key, COUNT(*), MAX(observed_at) FROM source_observations GROUP BY source_key ORDER BY 3 DESC;"
sqlite3 cfb_rankings.db "SELECT team_slug, week, effective_n FROM team_cohort_week ORDER BY week DESC, effective_n DESC LIMIT 40;"
```

Report:
- Per source: row count + freshness
- Which priority teams (if any) already have `team_cohort_week` rows and their effective_n
- Whether the hourly cron is writing to `scrape_health` and what success/error rate

Don't take action in Phase 0 — just observe. This informs decisions in Phase 3.

---

## Phase 1 — Pulse rendering fixes (data-independent, ship first)

Both fixes should work regardless of whether fan-intel data is flowing. Ship them first so Kevin's screenshot bugs are gone even if Phase 3's rewire hits a snag.

### 1.1 State-aware "WHAT MOVED IT" label + content

Current behavior: `<header>` on the right-side Pulse panel hardcodes "LAST 14 DAYS" and the body shows the last 3 game results from 2024.

New behavior: the label and content vary by `seasonal_state` (already resolved by `state_resolver.py`):

| seasonal_state | Label | Content |
|---|---|---|
| `in-season-regular` | LAST 14 DAYS | Last 2–3 games + any mid-week events |
| `post-loss-sunday-monday` | LAST 72 HOURS | Just-finished game + any reactions |
| `post-win-sunday-monday` | LAST 72 HOURS | Just-finished game + any reactions |
| `rivalry-week` | RIVALRY WEEK · BUILD-UP | Opponent history + build-up signals |
| `dead-period-summer` | OFFSEASON · LAST 30 DAYS | Portal moves, coaching news, recruiting |
| `spring-and-portal` | SPRING & PORTAL · LAST 30 DAYS | Portal entries/commits, spring practice milestones, staff news |
| `selection-sunday` | SELECTION SUNDAY | Bracket scenarios + CFP math |

**Implementation:**
- Find the string "LAST 14 DAYS" in the Pulse template. Replace with a template variable (e.g. `{{ pulse.moved_it_label }}`).
- The Pulse data provider returns the label by looking up `seasonal_state`.
- For the content list: in offseason states, query portal + coaching-news + recruiting tables (whatever exists) instead of the games table. If no offseason events exist yet, render 1–2 placeholder items like "Spring practice window open · portal window reopens <date>" driven by date arithmetic, NOT from the 2024 games table.

Do NOT show 2024 game results when seasonal_state is offseason. That's the core bug.

### 1.2 Sparkline fix

Current behavior: left side of the Pulse module shows floating "+29" and "+63" labels with no bars, plus orphan "conversation velocity · off-season floor" caption below.

New behavior (two-mode):

**Mode A (live signal, effective_n ≥ 30):**
- Render sparkline with one bar per day for the last 14 days (or whatever window matches the seasonal_state)
- Bars colored by direction (green = up, red = down, muted = flat)
- Delta labels at peaks only, not orphaned
- Caption: "conversation velocity · <period>"

**Mode B (no signal, effective_n < 30):**
- Hide the entire sparkline slot
- Hide the caption
- The right-side "what moved it" panel + takes area still render

Implement Mode B as the day-1 default. Wire Mode A so it activates when the data provider reports `effective_n ≥ 30` AND non-null `sparkline_points`. Control via a single conditional in the template.

### 1.3 Re-render + verify

Re-render all 11 profiled programs:
```
python manage.py render-team-pages
```

Open any one of them (e.g., Notre Dame) and verify visually:
- "LAST 14 DAYS" gone, replaced by "SPRING & PORTAL · LAST 30 DAYS"
- Right-side events list no longer shows 2024 game deltas; instead shows portal/spring/coaching content
- Sparkline slot is either rendering real bars or completely absent (no floating numbers)

---

## Phase 2 — Feed-URL triage (Haiku, 15 min)

`python manage.py scrape-health --show-errors`

Take top 10 failures by priority: Tier-1 beat writers > campus newspapers > podcasts > boards > Substacks. For each:
- Use Haiku to grep the URL + WebFetch to check status
- For 301/302 redirects: rewrite the `seeds/*.yaml` to the final URL
- For 403 Cloudflare-gated: add a realistic User-Agent to the adapter's HTTP headers
- For 404: mark the source_instance `needs_research=true` so Kevin can fix it manually next week
- Commit the YAML + adapter edits, do not delete rows

Report the 10 URLs, actions taken, and whether each is now healthy.

---

## Phase 3 — Pulse data provider rewire

### 3.1 Re-compute cohorts for current week

```
python manage.py compute-cohort-week --week=current
python manage.py compute-divergence --week=current
```

Report effective_n per priority team. Expected distribution on day-1 (after ~24h of single-source flow): a handful of blue-bloods (Alabama, OSU, Georgia, Texas, ND) may cross the floor with Wikipedia + Bluesky combined; the rest stay "Awaiting Signal" which is the correct product behavior.

### 3.2 Rewire the Pulse data provider

Find the current Pulse data provider (likely a function in `team_pages/` that returns the data the Pulse template consumes). Replace its internals with a call to `fetch_team_mood_profile` / `team_cohort_week` via the existing `fan_intelligence.py` infrastructure.

Contract for the rewired provider:
```python
def fetch_pulse(team_slug: str, as_of: datetime) -> PulseState:
    """
    Returns a PulseState dataclass/dict with:
      mood_number: int | None         # None → renders as "—"
      mood_delta: int | None          # None → hidden
      velocity: str                   # QUIET | STIRRING | LOUD | ROARING
      seasonal_state: str             # from state_resolver
      moved_it_label: str             # from the seasonal_state table in Phase 1.1
      moved_it: list[MovedEvent]      # events matching the seasonal window
      takes: list[Take]               # when effective_n >= 30; else fallback to profile.stock_phrases
      effective_n: int
      sparkline_points: list[float] | None  # None when effective_n < 30
    """
```

Implementation notes:
- Preserve existing seasonal-sentience logic. The offseason "QUIET" state is specced, not a bug — keep it.
- `moved_it` in offseason reads from portal + coaching-news + recruiting sources (not from conversation signal — those don't require effective_n floor).
- `takes` in offseason falls back to `profile.stock_phrases` when live conversation signal is below floor. Rotate which stock phrase appears per week (deterministic hash on `team_slug + week_number`) so the same fan doesn't see the same phrase every visit.
- `mood_number` reads from `team_cohort_week.mood_score` aggregated across cohorts, with the floor rule applied.

### 3.3 Floor-rule badge treatment

Add small metadata badges to the Pulse footer based on effective_n:
- <30: `<badge class="pulse__badge pulse__badge--awaiting">n=<count> · awaiting signal</badge>` in fg-subtle 9px
- 30–100: `<badge class="pulse__badge pulse__badge--growing">n=<count> · sample growing</badge>`
- ≥100: no badge (full-fidelity render is the norm)

CSS in the same file that owns Pulse styles.

---

## Phase 4 — Methodology nav hook (30-second surgical edit)

Per `CLAUDE.md:11717–11723`, add ONE entry to the nav tuples:

```python
("Methodology", "/methodology/fan-intelligence.html", "How we measure the Pulse"),
```

- Confirm `output/site/methodology/fan-intelligence.html` already exists (auto-generated by `provenance/methodology_page.py`; if missing, run `python manage.py generate-methodology-page` first)
- Add the single tuple to the nav list
- No other changes to `reporting.py`

---

## Phase 5 — Self-verification + re-render

```
python manage.py render-team-pages
```

Spot-check on disk (use grep, not full reads):

**Every profiled program:**
- Pulse module renders
- `LAST 14 DAYS` hardcoded string no longer present anywhere in `output/site/teams/`
- No orphaned `+29` / `+63` sparkline-adjacent labels

**Blue-bloods (Alabama, OSU, Georgia, Texas, ND):**
- Either a real mood number OR "—" with a small `n=<count> · awaiting signal` badge — never a number without floor justification
- Sparkline present iff effective_n ≥ 30; absent otherwise (no middle state)

**UMass + Vanderbilt + new 6 programs:**
- Pulse renders in below-floor state (em-dash, no sparkline, stock-phrase takes, offseason event list)

**Methodology nav:**
- Main nav has a Methodology link
- Clicking through renders a readable /methodology/fan-intelligence.html page

---

## Decision authority

Autonomous on: exact PulseState shape, template variable names, sparkline color logic, badge wording, User-Agent strings for Cloudflare-gated adapters, which portal/coaching/recruiting table to read for offseason events.

Stop and flag only if:
- Sprint 5 has edited a file you need to edit (in that case, wait or report — no merge attempts)
- Pulse template refactor would touch >3 files outside `team_pages/` — stop and report
- `team_cohort_week` schema doesn't match what `aggregate.py` claims to write — report discrepancy
- No portal/coaching/recruiting tables exist at all — fall back to date-driven placeholder items and note the gap

---

## Report back with

1. Phase 0 — data-state snapshot (source row counts + freshness + team_cohort_week coverage)
2. Phase 1 — before/after screenshot of ND Pulse (the one Kevin flagged). Confirm no "LAST 14 DAYS" string anywhere
3. Phase 2 — triage table (10 URLs, action, new health status)
4. Phase 3 — list of teams that crossed floor on day-1, list that remain "Awaiting Signal"
5. Phase 4 — methodology nav link rendering
6. Phase 5 — self-verification results + any regression concerns
7. Token usage
8. Natural next: typically either (a) wait 3–5 days for cross-source signal depth, (b) enable more adapters, or (c) seed additional priority teams

Report at end, not between phases.
