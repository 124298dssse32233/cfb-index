# Wave 25 Implementation Plan — Player Page 2026 Offseason Posture

**Generated:** 2026-05-27
**Spec:** [WAVE_25_SPEC.md](WAVE_25_SPEC.md)
**Plan provenance:** Multi-agent synthesis (codebase audit, CFBD feasibility,
risk/reconciliation/test plan) plus locked-spec multi-AI probe outputs at
`/c/Users/kevin/.claude-octopus/results/8fc664fe-…/`.
**Status:** Ready to execute. Total estimated effort: **~2,800 LOC + ~1,640 LOC tests + ~75 SQL** spanning 7 commits across 6 phases.

---

## Executive Summary

1. **Wave 25 is a 6-phase, 7-commit push.** Phase 1 stands up the status taxonomy + override layer + 2026 NFL draft / roster / portal ingest. Phases 2-4 deliver the three new modules. Phase 5 retrofits the re-labeling pass. Phase 6 verifies + deploys.
2. **Status Strip (Module 1) can ship today for Type B/D.** Existing `player_nfl_draft` already has 2025 draft rows (Gabriel/Sanders/Ward/Jeanty). Type A returning + Type B 2026-rookie + Type C transferred all gate on Phase 1 ingest, which is **3 minutes of CFBD calls** for steps 1-4 plus a manual override seed for top-100 marquee players.
3. **The biggest single risk is CFBD `/draft/picks?year=2026` returning empty in May 2026** (R1.1, high/high). CFBD typically lags league-of-record 2-6 weeks post-draft. Fallback scrape against pro-football-reference is mandatory pre-work, not an emergency response.

---

## §1. Phased breakdown with dependencies

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1 — DATA LAYER                                  [~6 hr work]  │
│   1.1 Migrations (override + 3 new tables + view)     [30 min]      │
│   1.2 Apply migrations + index creation               [10 min]      │
│   1.3 Probe CFBD endpoints (curl smoke test)          [10 min]      │
│   1.4 Pull /draft/picks?year=2026 (fallback ready)    [10 min]      │
│   1.5 Pull /player/portal?year=2026                   [5 min]       │
│   1.6 Pull /player/returning?year=2026 (or derive)    [5 min]       │
│   1.7 Pull /roster?year=2026 per-team (134 calls)     [~3 min]      │
│   1.8 Manual override seed for top 100 players        [~2 hr]       │
│   1.9 Sanity-check player_current_status_view rows    [15 min]      │
│   ───────────────── GATE: Phase 1 verification ──────────────────   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ PHASE 2      │      │ PHASE 3      │      │ PHASE 4      │
│ Status Strip │      │ 2026 Outlook │      │ Where-Ended  │
│ (all archs)  │      │ (Type A)     │      │ (Type B + C) │
│ [~4 hr]      │      │ [~6 hr]      │      │ [~5 hr]      │
│              │      │              │      │              │
│ Renders for  │      │ Depth + cast │      │ NFL or       │
│ every player │      │ + awards     │      │ transfer     │
│              │      │              │      │ destination  │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             ▼
                  ┌────────────────────────┐
                  │ PHASE 5 — RELABELING   │
                  │ season_context_label() │
                  │ [~3 hr]                │
                  └────────────┬───────────┘
                               │
                               ▼
                  ┌────────────────────────┐
                  │ PHASE 6 — VERIFY+DEPLOY│
                  │ Tests + smoke + ship   │
                  │ [~4 hr]                │
                  └────────────────────────┘

Total wall time: ~24-30 focused hours, plus 2-3 days elapsed for
manual override seed verification + parallel-stream reconciliation.

PARALLELISM OPPORTUNITIES:
- Phases 2, 3, 4 are INDEPENDENT once Phase 1 lands. Three workstreams.
- Phase 5 can START on the season_context_label() function in parallel with
  Phases 2-4, but the call-site replacements must wait for Phase 2 to settle
  the new section ordering in reporting.py.
```

---

## §2. CFBD Data Ingest Specs

### 2.1 `/draft/picks` — 2026 NFL Draft results

| Field | Value |
|---|---|
| **Path** | `GET /draft/picks?year=2026` |
| **Tier** | Free (Patreon key only buys rate-limit headroom) |
| **Expected rows** | 257 picks (fixed-size draft); ~220-230 from FBS programs |
| **Client method** | `CfbdClient.get_nfl_draft_picks(year)` at `src/cfb_rankings/clients/cfbd.py:381-385` |
| **Ingest fn** | `ingest_draft_year(db, client, 2026)` at `src/cfb_rankings/ingest/draft.py:76` |
| **Backfill time** | 1 request, ~1 sec wall |
| **Gotchas** | (a) `name` field in v2 vs `playerName` in v1 — existing code handles both; (b) ~8-10% picks have NULL `collegeId` (small-school FCS) — name-match fallback; (c) `position` is NFL position, may differ from CFBD roster position |
| **May-2026 risk** | **HIGH** — CFBD historically lags 2-6 weeks post-draft. Sanity-probe first |
| **Fallback** | Scrape `https://www.pro-football-reference.com/years/2026/draft.htm` (single HTML table, 257 rows, ~2 sec) via new `scripts/scrape_2026_draft_nflcom.py` |

### 2.2 `/player/portal` — 2026 transfer portal

| Field | Value |
|---|---|
| **Path** | `GET /player/portal?year=2026` |
| **Expected rows** | 4,800-5,500 total; ~3,400-3,900 FBS-resolvable |
| **Client method** | `CfbdClient.get_transfer_portal(year)` at `clients/cfbd.py:378-379` |
| **Ingest fn** | `_ingest_transfer_portal()` at `ingest/cfbd.py:947`. **Full-refresh**, NOT upsert — safe to re-run, do NOT parallelize with model jobs |
| **Backfill time** | 1 request, ~2 sec (largest single CFBD payload, ~3-5MB JSON) |
| **Gotchas** | `destination` is NULL for ~10-15% by May (post Jan 2-16 window). January is the only major portal window for 2026 per new NCAA rules |
| **Fallback** | On3 portal tracker scrape (`https://www.on3.com/transfer-portal/wire/football/`) |

### 2.3 `/roster` — 2026 FBS rosters

| Field | Value |
|---|---|
| **Path** | `GET /roster?year=2026&team={team}&classification=fbs` (per-team) |
| **Expected rows** | 12,000-13,500 total (134 teams × ~95 players) |
| **Client method** | `CfbdClient.get_roster(year, team, classification)` at `clients/cfbd.py:202-215` |
| **Ingest fn** | `_ingest_roster()` at `ingest/cfbd.py:897` |
| **Backfill time** | **Per-team for reliability**: 134 reqs × ~1s = ~2.5 min |
| **Gotchas** | (a) Spring snapshot is incomplete — incoming freshmen not always listed, outgoing portal players sometimes still attached to old team; (b) classification-wide snapshot occasionally drops smaller programs (UMass, Kennesaw observed); per-team always returns; (c) NO depth-chart / starter status in roster data |
| **May-2026 risk** | MED — partial data is the norm; July is when it stabilizes |
| **Fallback** | Per-team scrape of official athletics site rosters |

### 2.4 `/player/returning` — team-level returning production

| Field | Value |
|---|---|
| **Path** | `GET /player/returning?year=2026` |
| **Expected rows** | Exactly 134 (one per FBS team) |
| **Client method** | `CfbdClient.get_returning_production(year, team, conference)` at `clients/cfbd.py:217-230` |
| **Backfill time** | 1 request, ~1 sec |
| **Gotchas** | (a) Computed lazily from 2025 game logs — may be empty if CFBD hasn't finalized 2025 PPA; (b) **offense-only** — no defensive returning production; we'd need to compute defensive returning from roster diff + prior-year snap counts locally; (c) Returning % can exceed 100% in rare cases — clip in display |
| **Fallback** | If endpoint returns `[]`, compute locally: join `roster_entries` 2025 vs 2026 by `player_id`, weight by 2025 PPA. Tag `source_name='derived_local'` |

### 2.5 Awards / preseason watch lists — **GAP**

**No `/awards` endpoint exists in CFBD v2.** Confirmed via api-docs.json + grep across `src/cfb_rankings/`.

| Source | Watch list | Players | URL |
|---|---|---|---|
| Maxwell | All positions | ~85 | https://maxwellfootballclub.org/awards/maxwell-award/ |
| Davey O'Brien | QB | ~35 | https://www.daveyobrien.org/award/watch-list/ |
| Doak Walker | RB | ~85 | https://sportsawards.smu.edu/doak-walker-award/ |
| Biletnikoff | WR | ~50 | https://www.biletnikoffaward.com/watch-list/ |
| Mackey, Rimington, Outland, Bednarik, Butkus, Thorpe, Lombardi | various | varies | single-page rosters |
| Heisman | (no preseason list by tradition) | — | Use sportsbook futures via existing `prediction_markets.py` |

**TIMING:** Watch lists drop **June 15 - July 15 2026**. Too early in May. Schedule new `src/cfb_rankings/ingest/watch_lists.py` cron for **July 20, 2026**. For Wave 25 v1, manual seed top-50 returners from ESPN way-too-early Heisman + Phil Steele projections.

### 2.6 Depth charts — **HARD GAP**

**No CFBD endpoint exists.** Confirmed via api-docs.json. Closest is `/play/types` (play classification, not depth charts).

| Source | Coverage | Notes |
|---|---|---|
| On3 (`/teams/{slug}/depth-chart/`) | All 134 FBS | Best coverage, server-rendered HTML, no JS required. ~5 min for 134 scrape |
| 247Sports | All 134 FBS | Aggressive rate limits |
| ESPN | ~80 of 134 FBS in offseason | Spotty until fall |
| Athletic sites | ~40% in May | Spotty |

**RECOMMENDED:** **Defer real depth-chart ingest to August 20, 2026.** Spring depth charts are speculative — every program holds open competitions through August. Until then, derive projected depth from `(roster_entries × prior-year snap shares × portal-in/portal-out)` purely from local data. Build the `team_depth_chart` table now keyed by `(team_id, season_year, position, slot_rank)`. New `src/cfb_rankings/ingest/depth_charts.py` module scheduled for Aug 20.

### 2.7 Wave 25 ingest sequence (recommended order)

```
1. /draft/picks year=2026         # 1 req, ~1 sec     CRITICAL — sanity probe first
2. /player/portal year=2026       # 1 req, ~2 sec     (full-refresh, runs alone)
3. /player/returning year=2026    # 1 req, ~1 sec     (may be empty; have fallback)
4. /roster year=2026 per-team     # 134 reqs, ~3 min
5. Award watch lists              # DEFER to Jul 20 cron
6. Depth charts                   # DEFER to Aug 20 cron
```

**Total May 2026 ingest time: ~3 min** for steps 1-4. Existing `ingest_cfbd_preseason()` at `ingest/cfbd.py:137` already chains these — no new orchestration needed.

**Pre-flight sanity check (run THIS BEFORE Phase 1.4):**
```bash
curl -s -H "Authorization: Bearer $CFBD_PATREON_KEY" \
  "https://api.collegefootballdata.com/draft/picks?year=2026" | jq 'length'
# expect: 257   (if 0 → activate fallback scraper before proceeding)

curl -s -H "Authorization: Bearer $CFBD_PATREON_KEY" \
  "https://api.collegefootballdata.com/player/portal?year=2026" | jq 'length'
# expect: 3000-5500

curl -s -H "Authorization: Bearer $CFBD_PATREON_KEY" \
  "https://api.collegefootballdata.com/player/returning?year=2026" | jq 'length'
# expect: 134   (if <50 → use derived-local fallback)

curl -s -H "Authorization: Bearer $CFBD_PATREON_KEY" \
  "https://api.collegefootballdata.com/roster?year=2026&team=Alabama" | jq 'length'
# expect: 100-120
```

---

## §3. Module Implementation Specs

### 3.1 Module 1 — Player Status Strip

| Property | Value |
|---|---|
| **File** | `src/cfb_rankings/player_pages/status_strip.py` |
| **Estimated LOC** | ~280 Python + ~140 CSS |
| **Closest analog** | `career_standing.py` (277/120 LOC — same header-rail strip pattern) |
| **Public API** | `render_status_strip(db, player_id) -> str`, `STATUS_STRIP_CSS` |
| **Depends on** | `player_current_status_view` (§4.1 of spec), `player_status_override` table |
| **Renders for** | Every player, every archetype |
| **Reuses** | Design tokens (`design_tokens.py` already exports `--belief-high`, `--accolade-gold-base`, `--text-quiet`, `--stroke-subtle`, `--space-4..6`) — all Strip accent colors come for free |
| **Mobile** | Stack vertically <640px; collapse "as-of" to tooltip <375px |

### 3.2 Module 2 — 2026 Outlook (Type A only)

| Property | Value |
|---|---|
| **File** | `src/cfb_rankings/player_pages/outlook_2026.py` |
| **Estimated LOC** | ~340 Python + ~180 CSS |
| **Closest analog** | `heisman_trajectory.py` (227 LOC) + `career_standing.py` (~120 CSS for `__seasons` grid) — three SQL queries per spec §4.3 are non-trivial |
| **Public API** | `render_outlook_2026(db, player_id, team_id) -> str`, `OUTLOOK_2026_CSS` |
| **Depends on** | `player_status_view`, `player_depth_chart_2026`, `team_preview_roster_reload`, `team_seasons` (2025 vs 2026 diff for OC continuity), `player_award_watch_2026`, `team_returning_production` |
| **Renders for** | Only `status_code = 'RETURNING_2026'` |
| **Reuses** | `_team_year_aggregates` and `_scheme_tag` from `supporting_cast.py:22` (already imported by `season_context.py`) — OC continuity line gets this for free |
| **Cells** | Depth Chart · Supporting Cast · Award Watch (3-card row) |

### 3.3 Module 3 — Where They Ended Up (Type B + C)

| Property | Value |
|---|---|
| **File** | `src/cfb_rankings/player_pages/where_ended_up.py` |
| **Estimated LOC** | ~260 Python + ~160 CSS |
| **Closest analog** | `nil_draft.py` (187 LOC) — single-card destination panel. Wave 25 adds 2nd variant (transfer flow) + 2 date-framing branches (2026 rookie vs prior-year NFL) |
| **Public API** | `render_where_ended_up(db, player_id, status_code) -> str`, `WHERE_ENDED_UP_CSS` |
| **Depends on** | `player_nfl_draft`, `player_status_view`, NFL franchise logo assets |
| **Renders for** | `status_code IN ('NFL_DRAFTED_2026', 'NFL_DRAFTED_PRIOR', 'NFL_UDFA', 'TRANSFERRED_COLLEGE', 'PORTAL_OPEN')` |
| **Reuses** | `career_standing.py:251-258` already renders an NFL draft badge from `player_nfl_draft` — lift `_nfl_draft` helper (`career_standing.py:174-184`) + HTML scaffold wholesale |
| **Two variants** | 5A: NFL destination (pick chip + team logo + role projection) · 5B: Transfer flow (from → to logos + projected role) |

### 3.4 Module 4 — season_context_label() (re-labeling helper)

| Property | Value |
|---|---|
| **File** | `src/cfb_rankings/player_pages/season_labels.py` |
| **Estimated LOC** | ~80 Python, no CSS |
| **Closest analog** | `_current_season_production_title` at `reporting.py:11764` (~20 LOC) + 11-code branch + title-tag variants |
| **Public API** | `season_context_label(status_code, last_team_name, last_season_year, current_team_name, current_date=None) -> str` |
| **Replaces** | `reporting.py:11764` `_current_season_production_title()` body — gets a call-site swap, not a full rewrite |

### 3.5 Integration touch-points in reporting.py

**A. Import block (`reporting.py:9096-9118`)** — add 3 imports inside the `from cfb_rankings.player_pages import (...)` block at line **~9118** (after `render_season_context`):
```python
render_status_strip as _render_status_strip_v2,
render_outlook_2026 as _render_outlook_v2,
render_where_ended_up as _render_where_ended_v2,
```

**B. Status-code derivation (NEW)** — add ~15 LOC at line **9095** (start of v2 try block) to query `player_current_status_view` once and cache locally:
```python
status_row = db.query_one(
    "SELECT * FROM player_current_status_view WHERE player_id = :pid",
    {"pid": player_id},
)
status_code = (status_row or {}).get("status_code") or "HISTORICAL_ALUM"
page_data["status"] = dict(status_row or {})
```

**C. Page-data population** — add 3 lines after line 9229:
```python
page_data["new_status_strip_html"] = _render_status_strip_v2(db, player_id)
page_data["new_outlook_2026_html"] = (
    _render_outlook_v2(db, player_id, _primary_team_id)
    if status_code == "RETURNING_2026" else ""
)
page_data["new_where_ended_up_html"] = _render_where_ended_v2(db, player_id, status_code)
```

Mirror three `""` defaults in the except fallback at **lines 9269-9290**.

**D. HTML template injection**
- **Status Strip**: insert at line **19505** (after breadcrumbs `</div>`, before `_render_qb_fingerprint_hero` at 19506):
  ```python
  {player_data.get("new_status_strip_html") or ""}
  ```
- **2026 Outlook**: insert as new `<section class="section player-anchor-section" id="outlook-2026">` block between line **19526** and 19528, mirroring how `accolade-trajectory` is conditionally rendered at lines 19535-19539
- **Where They Ended Up**: insert as parallel new section between lines 19526 and 19528, same conditional pattern

**E. CSS bundle (`reporting.py:5219-5253`)** — add 3 imports inside `_player_pages_v2_css()` at line **5243**:
```python
STATUS_STRIP_CSS as _SS_CSS,
OUTLOOK_2026_CSS as _OL_CSS,
WHERE_ENDED_UP_CSS as _WE_CSS,
```
Append `+ _SS_CSS + _OL_CSS + _WE_CSS` to the concat at **line 5253**.

**F. `__init__.py` exports** — add 3 import lines + 6 `__all__` entries.

---

## §4. Database migrations (filenames + ordering)

Latest migration on disk: `20260527_05_player_id_alias_honors_expanded.sql`. Skip to `_06`.

```
migrations/20260527_06_player_status_override.sql      # spec §3.4 override table
migrations/20260527_07_player_current_status_view.sql  # spec §3.4 view
migrations/20260527_08_player_depth_chart_2026.sql     # Module 2 cell 1 source
migrations/20260527_09_player_award_watch_2026.sql     # Module 2 cell 3 source
```

**Indexes (CRITICAL for build performance):**
```sql
CREATE INDEX IF NOT EXISTS idx_player_status_override_pid
  ON player_status_override(player_id);
CREATE INDEX IF NOT EXISTS idx_player_depth_chart_2026_pid
  ON player_depth_chart_2026(player_id);
CREATE INDEX IF NOT EXISTS idx_player_award_watch_2026_pid_pri
  ON player_award_watch_2026(player_id, priority);
CREATE INDEX IF NOT EXISTS idx_player_nfl_draft_pid_year
  ON player_nfl_draft(player_id, draft_year);
CREATE INDEX IF NOT EXISTS idx_team_returning_production_team_season
  ON team_returning_production(team_id, season);
```

**The `last_team` CTE perf gotcha** (§3.4 of spec):
- The placeholder `last_team` CTE scans `player_season_stats` (1.3M rows) for every page render — 17,000 × full-scan is unacceptable
- **Fix:** add `player_last_team_cache` materialized table populated once at build start
- Migration: `20260527_10_player_last_team_cache.sql` with `(player_id PK, team_id, team_name, last_year, snap_count, games_played)`

---

## §5. Risk Register (by phase)

### Phase 1 — Data Layer

| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| **R1.1** | **CFBD `/draft/picks?year=2026` returns empty in May 2026.** Historical lag 2-6 weeks post-draft. Without it, every 2026 draftee (Allar, Beck, Mendoza, ~250 players) silently falls through to EXHAUSTED_ELIGIBILITY. | **HIGH** | **HIGH** | (a) Probe endpoint as Phase 1 step 1.3 — single curl; (b) if empty, ship one-shot `scripts/scrape_2026_draft_nflcom.py` against pro-football-reference (1 HTML table, ~250 rows) writing `source='pfr_scrape_2026'`; (c) seed top-50 via `player_status_override` so marquee pages are never wrong even if both ingests fail |
| R1.2 | **CFBD `/roster?year=2026` returns partial.** Rosters often incomplete until late June. Type A vs Type C resolution mis-fires for transfer-heavy programs. | med | high | (a) Compare row count vs 2025; if <80%, flag as partial and DO NOT promote `RETURNING_2026` from view; (b) require override row for any top-100 player whose 2026 roster row is missing; (c) `roster_confidence` column on view so renderer can fall back to amber "Status pending verification" |
| R1.3 | **Override table sprawl.** Manual seeds become source-of-truth and rot. Six months from now nobody remembers Allar's status was hand-pasted. | med | med | (a) Add `expires_at` column (default 90 days); (b) view does `COALESCE(o.status_code WHERE o.expires_at > CURRENT_TIMESTAMP, computed_code)`; (c) nightly job logs override-vs-computed drift to `logs/status_override_drift_<date>.log`; (d) require `set_by` + `notes` NOT NULL |

### Phase 2 — Module 1 Status Strip

| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| R2.1 | **Strip renders before Wave 1-24 visual verification is complete.** A bad CSS class shoves the entire page down — parallel team-preview screenshot diffs flag as regression. | high | med | (a) Build behind `RENDER_STATUS_STRIP=1` env flag for first build; (b) generate before/after PNGs via headless Edge for 8 marquee pages and compare; (c) ship strip with `contain: layout` to prevent layout escape; (d) merge AFTER team-preview claim validation lands |
| R2.2 | **Stale archetype rendering.** Allar still shows "Returning for 2026" because resolver hits roster_2026 row from March. Status flips only after Phase 1 step 1.4 succeeds. | med | high | (a) Resolution order (spec §3.3) puts NFL draft BEFORE roster; (b) build-time assertion: for every player_id with 2026 draft row, assert no 2026 roster row OR override is present; (c) sanity-test top-50 returners in `tests/test_wave_25_status_strip.py`; (d) override seed is the safety net |
| R2.3 | **WR Heisman watch (Jeremiah Smith) suppressed by accident.** If award_watch render filters by `position IN ('QB','RB')` anywhere, Smith's badge silently drops. Instant credibility hit. | med | med | (a) `AWARD_POSITION_ELIGIBILITY` config dict keyed by `award_slug → set of positions`; Heisman maps to `{'QB','RB','WR','TE'}`; (b) dedicated test `test_jeremiah_smith_heisman_badge_renders()`; (c) lint: grep for hardcoded position filter near award rendering |

### Phase 3 — Module 2 (2026 Outlook)

| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| R3.1 | **`team_preview_roster_reload` row missing or NULL fields** for non-marquee Type A programs. Renderer NPEs or shows "0/5 OL starters" reading as "rebuilt line" when reality is unknown. | med | med | (a) Treat NULL ≠ 0 — render "OL continuity unknown" in `--text-quiet`; (b) spec §4.5 fallback to team-level `/returning` percentage; (c) integration test against Manning/Lagway/Smith + one mid-tier program (Vandy, UConn) |
| R3.2 | **Cohort drift across 2025→2026.** A player who transferred mid-portal (Beck UGA→Miami→drafted Arizona) has multiple `player_season_stats` rows where team_id differs by year. The `last_team` CTE `MAX(season_year)` → returns whichever row sqlite picks first. Renders wrong "previous_team" in variant 5B. | med | high | (a) `last_team` CTE selects by `(season_year DESC, snap_count DESC, games_played DESC)`; (b) add canonical `player_team_history` view if multi-team-per-year cases >5%; (c) test case covers Beck Georgia→Miami→Arizona chain explicitly |
| R3.3 | **Manual depth-chart and award-watch seeds become silent source-of-truth.** Worse than R1.3 — these are pure editorial. Two months in, nobody knows whether "projected starter" came from a coach quote or vibe. | high | med | (a) Both tables get `source TEXT NOT NULL` and `source_url TEXT` (`'manual_editorial'`, `'cfbd_returning'`, `'on3_scrape'`); (b) renderer surfaces "Source: {source}" as tooltip; (c) `scripts/audit_manual_seeds.py` weekly to `logs/seed_audit_<date>.json` |

### Phase 4 — Module 3 (Where They Ended Up)

| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| R4.1 | **NFL logo URL rot.** Offseason rebrand silently ships stale glyph. Three rebrands in last decade. | low | med | (a) Abbreviation-based filenames (`ari.svg`, `was.svg`); (b) `<img>` `onerror` falls back to colored initials per spec §5.4; (c) annual June 1 refresh task |
| R4.2 | **NFL_DRAFTED_PRIOR mis-framing.** Gabriel/Sanders/Ward/Jeanty pages render "2026 rookie season" because `draft_year` check uses `>= 2025` instead of `= 2026`. Fans spot it instantly. | med | med | (a) Subtitle template is pure function `nfl_subtitle(draft_year, current_year)`; unit test 2024/2025/2026 cases; (b) spec §5.2 explicitly distinguishes; (c) golden test against four named players |
| R4.3 | **Drafted-AND-portal collision.** Phase 1 ingest order lands portal before draft in a partial run, view flickers on Strip status. Caching layers could pin wrong status for hours. | low | high | (a) Resolution order (§3.3) hard-coded; verify CTE join order does NOT reorder by accident; (b) idempotency test: run resolver twice, assert identical; (c) deploy with `Cache-Control: max-age=300` until status stabilizes |

### Phase 5 — Re-labeling

| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| R5.1 | **`season_context_label()` hardcodes 2026/2025.** Must take `current_date` param. Default to `date.today()` breaks tests with fixed clocks. | high | med | (a) Require explicit pass-through from caller, `date.today()` only inside a single helper; (b) parametrize tests over 2026-05-27 / 2026-11-15 / 2027-05-27; (c) lint rule: no literal `2026` in `season_labels.py` |
| R5.2 | **Grep-replace of "Current Season Production" misses occurrences inside JS strings, `<title>` tags, non-template concatenations in `reporting.py` (26.8k lines).** | high | med | (a) Replace via Edit tool with explicit context, NOT grep -r sed; (b) post-replace `grep -nE 'Current Season|2024 Stats' src/cfb_rankings/reporting.py` MUST return zero hits or annotated `# wave-25-keep`; (c) build-time assertion |
| R5.3 | **`<title>` tag SEO regression.** Sudden archetype-aware title change drops search rankings. | med | med | (a) Preserve `{Name}` as first token always; (b) `<link rel="canonical">` keeps URL stable; (c) fallback to old format for any `status_code IS NULL`; (d) sitemap.xml regen part of build |

### Phase 6 — Verify + Deploy

| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| R6.1 | **Vercel alias rotation gotcha** (2026-05-23 incident). Short alias doesn't auto-rotate. Wave 25 ships to per-deploy URL no human visits. | low | high | (a) Verify `vercel alias set` step still in `publish_site.yml`; (b) post-deploy smoke test hits short alias + checks for `data-module="player-status-strip"` DOM marker; (c) memory note already documents |
| R6.2 | **`live_smoke_test.yml` 28-URL sample doesn't include new Strip-only pages.** Render regression doesn't trigger <95% gate. | med | med | (a) Add 4 Wave 25 URLs (Manning/Allar/Beck/Gabriel) with assertions for Status Strip text content; (b) assertions check archetype-correct strings, not just 200 OK |
| R6.3 | **CI guardrail `verify_world_class_team_pages.py` doesn't cover player pages.** Future commit rips out the Strip; nothing fails. | med | high | (a) Promote `scripts/verify_player_pages_wave_complete.py` from suggestion to requirement; (b) hard-fail build if `status_code IN TYPE_A_CODES` and no `data-module="outlook-2026"`; (c) wire into `build-site` post-render hook |

---

## §6. Reconciliation Strategy

The parallel work-stream landed Wave 1-3 modules + extensive reporting.py edits. My uncommitted Wave 22-24 work touches overlapping files. Wave 25 will edit reporting.py again.

### Step 1 — Snapshot local state

```bash
git status --short
git diff --stat
git stash push -m "wave-22-24-uncommitted-2026-05-27" \
  src/cfb_rankings/player_pages/season_context.py \
  src/cfb_rankings/player_pages/supporting_cast.py \
  src/cfb_rankings/player_pages/game_log.py \
  src/cfb_rankings/player_pages/box_savant.py \
  src/cfb_rankings/player_pages/composite_score.py \
  src/cfb_rankings/reporting.py
git status  # confirm clean
git fetch origin master
git log --oneline HEAD..origin/master  # what's incoming
git merge --ff-only origin/master  # refuse if non-ff
```

**If `--ff-only` refuses**: STOP. Inspect `git log --oneline master..HEAD` before proceeding. Do NOT `git pull --rebase` blind.

### Step 2 — Identify conflicts

```bash
git stash show -p stash@{0} --stat
git stash apply --index stash@{0}
git status  # any "both modified" = conflict
```

Classify each conflict:
- **Pure addition** (new module file like `season_context.py`) — apply as-is, zero risk
- **Both-touched non-overlap** (different functions in reporting.py) — auto-merges, verify by reading result
- **Both-touched overlap** (same `page_data["new_*_html"]` block) — hand-merge, ADD local key alongside parallel keys

### Step 3 — Surgical merge per file

| File | Strategy |
|---|---|
| New file local-only | Apply from stash, zero risk |
| New file parallel-only | Already on master, leave it |
| reporting.py — page_data dict block | Hand-merge: add local key alongside parallel keys, additive only |
| reporting.py — unrelated function | git auto-merge, verify import |
| box_savant.py, composite_score.py (both touched) | `git log -p f546545991c` to see parallel intent. If local was bug fix, keep both. If parallel superseded, DROP local and re-derive |

NEVER `git stash pop` until every file resolves. Use `git stash apply` so stash remains recovery point.

### Step 4 — Validation that Wave 1-24 still works

```bash
# Syntax + import
python -c "import src.cfb_rankings.reporting; import src.cfb_rankings.player_pages; print('ok')"

# Subset tests
python -m pytest tests/test_player_pages_*.py -x --tb=short
python -m pytest tests/test_team_preview_*.py -x --tb=short

# Smoke build + visual diff
python manage.py render-player arch-manning carson-beck --output-dir /tmp/wave-25-merge-smoke
msedge.exe --headless --screenshot=/tmp/manning-postmerge.png file:///tmp/wave-25-merge-smoke/players/arch-manning.html
# Compare against /tmp/manning-premerge.png captured BEFORE stash

# CI guardrail
python scripts/verify_world_class_team_pages.py
```

If any fails, `git reset --hard origin/master && git stash apply stash@{0}` restores known-good. Only after 4a-4e pass: `git stash drop stash@{0}`.

### Step 5 — Commit strategy (7 commits)

```
Commit 1: chore(player-pages): merge uncommitted Wave 22-24 work
Commit 2: feat(player-pages): Wave 25 Phase 1 — status taxonomy + migrations
Commit 3: feat(player-pages): Wave 25 Phase 2 — Status Strip module
Commit 4: feat(player-pages): Wave 25 Phase 3 — 2026 Outlook module
Commit 5: feat(player-pages): Wave 25 Phase 4 — Where They Ended Up
Commit 6: refactor(player-pages): Wave 25 Phase 5 — season_context_label
Commit 7: feat(verify): Wave 25 Phase 6 — CI guardrail + smoke URLs
```

Each commit independently passes `python -c "import …"` and the relevant test file. Bisect-friendly. Push after commit 2 (data layer is safe alone), then commit 4 (Strip+Outlook live), then final push after commit 7. **Do NOT batch all 7 into a single push** — gives the parallel work-stream no chance to react.

---

## §7. Manual Data Seeding Plan

### 7.1 Top 100 manual override seed (Phase 1 step 1.8)

**Estimated time: ~2 hours of focused editorial work.**

For each of the top 100 marquee players, verify status from official sources and write to `data/seeds/player_status_override_2026.json`:

```json
{
  "version": "2026-05-27",
  "seeds": [
    {
      "player_id": 4870906,
      "canonical_name": "Arch Manning",
      "status_code": "RETURNING_2026",
      "current_team": "Texas",
      "set_by": "editorial_2026_05_27",
      "source_url": "https://texaslonghorns.com/sports/football/roster/arch-manning/16963",
      "expires_at": "2026-08-27",
      "notes": "Confirmed QB1 for 2026; spring practice depth chart shows him 1st team"
    },
    {
      "player_id": null,
      "canonical_name": "Drew Allar",
      "status_code": "NFL_DRAFTED_2026",
      "draft_year": 2026, "draft_round": 3, "draft_pick": 79, "nfl_team": "Pittsburgh Steelers",
      "set_by": "editorial_2026_05_27",
      "source_url": "https://www.psu.edu/news/intercollegiate-athletics/story/eight-nittany-lions-taken-2026-nfl-draft",
      "expires_at": null,
      "notes": "2026 Draft Rd 3 to Steelers; was projected returning starter through April"
    }
    // ... 98 more
  ]
}
```

**Top 100 composition:**
- Top 25 returning QBs (Heisman watch + Davey/Manning candidates)
- Top 25 returning skill players (Doak, Biletnikoff, Mackey watch)
- Top 25 returning defenders (Butkus, Thorpe, Nagurski watch)
- All 2026 NFL Draft round 1-3 picks (~100, dedupe with above)
- Notable Type C transfers (10-20 players)

Source mix:
- ESPN way-too-early Heisman (Feb 9 2026)
- On3 top returning QBs (Feb 27 2026)
- Phil Steele preseason projections (when published in June)
- 2026 NFL Draft official results (pro-football-reference + team press releases)

### 7.2 Depth-chart seed (Phase 3 prep)

**Estimated time: ~3 hours.**

Manually seed `player_depth_chart_2026` for **all returning starters at top 50 programs** (per AP/Coaches preseason poll proxy). Format:

```sql
INSERT INTO player_depth_chart_2026 (player_id, season_year, position_group, slot_rank, starter_status, confidence, source, source_url, as_of)
VALUES (4870906, 2026, 'QB', 1, 'projected_starter', 'high', 'manual_editorial',
        'https://texaslonghorns.com/sports/football/roster/arch-manning/16963', '2026-05-27');
```

Coverage target: ~5 starters per top-50 team = ~250 manual rows.

### 7.3 Award-watch seed (Phase 3 prep)

**Estimated time: ~1 hour for v1.**

Manually populate `player_award_watch_2026` from ESPN/On3 May 2026 preseason articles:

| Award | Players to seed | Source |
|---|---|---|
| Heisman | Top 20 odds-board (incl. Smith, Manning, Lagway, etc.) | ESPN futures + On3 |
| Maxwell | Top 20 | ESPN |
| Davey O'Brien | Top 10 QBs | ESPN |
| Doak Walker | Top 10 RBs | ESPN |
| Biletnikoff | Top 10 WRs | ESPN |
| Mackey | Top 5 TEs | ESPN |
| Nagurski/Bednarik/Butkus/Thorpe | Top 5 per | ESPN |

**Total seed rows: ~120.** Future automation: scrape official award pages when watch lists drop June 15 - July 15 2026.

---

## §8. Test Plan (~1,640 LOC)

### 8.1 Test file inventory

| File | LOC | Scope |
|---|---|---|
| `tests/test_wave_25_status_resolution.py` | ~280 | View + override unit tests, all 11 status codes |
| `tests/test_wave_25_status_strip.py` | ~220 | Module 1 render unit + integration |
| `tests/test_wave_25_outlook.py` | ~250 | Module 2 render + supporting-cast + award-watch |
| `tests/test_wave_25_where_ended_up.py` | ~230 | Module 3 variant 5A + 5B |
| `tests/test_wave_25_season_labels.py` | ~180 | Re-labeling pass, date-aware |
| `tests/test_wave_25_visual_regression.py` | ~160 | Headless Edge snapshot diff |
| `tests/test_wave_25_edge_cases.py` | ~200 | All taxonomy entries + callouts |
| `tests/fixtures/wave_25_seed_players.py` | ~120 | Player seed factory |
| **Total** | **~1,640 LOC** | |

### 8.2 Concrete test cases by player

| Player | Test focus | Status code | Critical assertion |
|---|---|---|---|
| Arch Manning | RETURNING_2026 happy path | `RETURNING_2026` | Outlook + Strip render, no Where-Ended-Up |
| **Drew Allar** | **Stale roster vs new draft row (the R2.2 regression guard)** | `NFL_DRAFTED_2026` | Resolution order beats stale roster_2026 row WITHOUT needing an override |
| Cam Ward | NFL_DRAFTED_PRIOR + identity drift (3 player_ids) | `NFL_DRAFTED_PRIOR` | Subtitle says "Entering 2nd NFL season"; all three player_id aliases resolve to same canonical |
| Carson Beck | Multi-team history → drafted (the R3.2 cohort drift test) | `NFL_DRAFTED_2026` | `last_team` resolves to Miami (not Georgia) via deterministic CTE ordering |
| **Jeremiah Smith** | **WR Heisman watch (R2.3 anomaly test)** | `RETURNING_2026` | HTML contains BOTH `outlook-2026__award--heisman` AND `outlook-2026__award--biletnikoff` |
| Historical alumnus | `HISTORICAL_ALUM` defensive fallback | `HISTORICAL_ALUM` | No NPE, generic "Career Stats" label |
| Walk-on (sparse) | Graceful empty | `HISTORICAL_ALUM` | Amber "Status pending verification" pill |
| Override player | Editorial override beats computed | from override | Includes expiry test: advance clock, override decays |

### 8.3 Edge-case coverage

Single file `tests/test_wave_25_edge_cases.py` covers spec §9 + §12 callouts:

1. Portal-and-UDFA same week — drafted wins
2. Logo 404 → initials fallback
3. CFBD 429 missing `Retry-After` → default 60s
4. `season_context_label` parametrized over 2026/2027 dates
5. `PORTAL_WITHDREW` resolution path
6. Co-starter amber accent in Outlook cell
7. Full OL returning gold pill
8. Rebuilt-line red warning pill
9. `HS_RECRUIT_ONLY` rare path
10. Defensive fallback for NULL status_code

### 8.4 Visual regression

Headless Edge + PNG hash comparison against committed baselines in `tests/baselines/wave_25/`. Soft-assert on hash mismatch (CSS micro-shifts shouldn't break CI); hard-fail only on >5% pixel diff. Pairs:
- Arch Manning (full + mobile 375px)
- Carson Beck (full + mobile)
- Dillon Gabriel (full)

---

## §9. Performance Budget

### 9.1 Current baseline
- Full publish (per CLAUDE.md): ~50 min
- 17,000 player pages
- Per-page render: ~3-5ms baseline before Wave 25

### 9.2 Wave 25 per-page added work
| Query | Cost | Notes |
|---|---|---|
| `player_current_status_view` | 1-3 ms | 5 LEFT JOINs, PK lookup on `players` |
| `player_depth_chart_2026` | 0.5 ms | PK lookup |
| `player_award_watch_2026` | 0.5 ms | Indexed by player_id |
| `team_preview_roster_reload + team_seasons ×2 + team_returning_production` | 5-10 ms | **THE SLOW ONE** — needs index |
| **Total per page** | **~12 ms** | |

### 9.3 Build-time delta
17,000 pages × 12 ms = **~3.5 minutes added to full build**. Brings 50min → ~53-54min. **Acceptable.**

### 9.4 Critical perf gotchas (must address)
- ❌ **`player_season_stats` (1.3M rows) in `last_team` CTE** — placeholder in spec §3.4. For 17k pages = 17k re-aggregations. **Fix:** materialize `player_last_team_cache` table at build start (migration `_10`)
- ❌ **JOIN to `player_nfl_draft` without index** — add `idx_player_nfl_draft_pid_year`
- ❌ **2026 roster fallback to `player_season_stats`** (spec §3.4 placeholder) — full-scan per page. Replace with real `player_roster_2026` BEFORE deploying

### 9.5 Build-time measurement plan
- Pre-Wave-25 baseline: `time python manage.py build-site --output-dir /tmp/baseline 2>&1 | tail`
- Post-Wave-25: same command, compare wall-clock
- Per-page sample profile: instrument `_assemble_player_page_data` with `time.perf_counter()` around new queries; log every 1000th page to `logs/build_perf_<date>.log`
- Hard guard: if total build > 65 min, halt and profile

---

## §10. Verification Gates

Each phase has a binary GO/NO-GO gate. Don't proceed if any gate fails.

### Gate 1 (after Phase 1)
- [ ] All 4 migrations applied (`SELECT name FROM sqlite_master` returns the 4 new tables + view)
- [ ] CFBD probe returns expected row counts for all 4 endpoints (see §2.7 probe block)
- [ ] `player_current_status_view` returns rows for ≥10,000 player_ids
- [ ] Manual override seed loaded: `SELECT COUNT(*) FROM player_status_override` returns ≥100
- [ ] Top-10 marquee players resolve to correct status codes (Manning RETURNING, Allar NFL_DRAFTED_2026, Beck NFL_DRAFTED_2026, etc.)

### Gate 2 (after Phase 2 — Status Strip)
- [ ] `import status_strip` succeeds without error
- [ ] `render_status_strip(db, manning_id)` produces ≥500 chars containing `data-status-code="RETURNING_2026"`
- [ ] All 11 status codes have a render path that produces non-empty output
- [ ] Visual smoke on 8 marquee pages — Strip renders, no layout shift on QB Fingerprint below
- [ ] `tests/test_wave_25_status_strip.py` passes 100%

### Gate 3 (after Phase 3 — Outlook)
- [ ] `import outlook_2026` succeeds
- [ ] Outlook renders for Manning + Smith + Lagway (Type A)
- [ ] Outlook DOES NOT render for Allar / Beck / Gabriel (non-Type-A)
- [ ] Award watch shows Heisman badge for Jeremiah Smith (WR Heisman anomaly test)
- [ ] OC continuity shows correctly for ≥3 spot-check teams (Texas, Penn State, Florida)
- [ ] `tests/test_wave_25_outlook.py` passes 100%

### Gate 4 (after Phase 4 — Where Ended Up)
- [ ] `import where_ended_up` succeeds
- [ ] Variant 5A renders for Allar/Beck (2026 draft) AND Gabriel/Sanders/Ward/Jeanty (2025 draft)
- [ ] Subtitle correctly distinguishes "2026 rookie season" vs "Entering 2nd NFL season"
- [ ] Variant 5B renders for any active Type C transfer
- [ ] NFL logos load for top 32 franchises (no 404s, initials fallback works)
- [ ] `tests/test_wave_25_where_ended_up.py` passes 100%

### Gate 5 (after Phase 5 — Relabeling)
- [ ] `grep -nE 'Current Season|2024 Stats' src/cfb_rankings/reporting.py` returns zero hits OR only `# wave-25-keep` annotated lines
- [ ] `season_context_label()` returns correct strings for all 11 status codes × 3 dates (today, 2026-11-15, 2027-05-27)
- [ ] `<title>` tag is archetype-aware for all 11 codes
- [ ] `tests/test_wave_25_season_labels.py` passes 100%

### Gate 6 (after Phase 6 — Verify+Deploy)
- [ ] `scripts/verify_player_pages_wave_complete.py` passes (extended with Wave 25 checks)
- [ ] `live_smoke_test.yml` includes 4 Wave 25 URLs with archetype-correct assertions
- [ ] Full build wall-clock ≤ 65 min
- [ ] Visual regression baselines updated
- [ ] All 7 commits push cleanly with no merge conflicts

---

## §11. Deploy Strategy

**Use local Vercel deploy per memory note `project_vercel_local_deploy`.** Rationale:
- The runner DB artifact may not have the Wave 25 manual override seed (it lives in the local DB).
- CI cron workflow takes ~50 min and rotates the alias automatically — but the override seed isn't on CI's DB unless we explicitly upload it.
- Local deploy: `vercel build --prod --yes && vercel deploy --prebuilt --prod --yes --archive=tgz` then `vercel alias set <deploy-url> wonderful-margulis-8ec96b.vercel.app`.

**Pre-deploy checklist:**
1. All Gate 1-6 GREEN
2. Visual regression baselines committed to repo
3. `data/seeds/player_status_override_2026.json` committed (the manual seed file)
4. CI smoke test `live_smoke_test.yml` updated with Wave 25 URL assertions
5. README touch noting Wave 25 module is live (for future-archeology)

**Deploy day (estimated 30 min total):**
1. `python manage.py build-site` (30-50 min, do this last)
2. `vercel build --prod --yes` (5 min)
3. `vercel deploy --prebuilt --prod --yes --archive=tgz` (3-5 min for 6.4GB upload? memory says archive helps)
4. `vercel alias set <deploy-url> wonderful-margulis-8ec96b.vercel.app` (instant)
5. Smoke test the alias hits Wave 25 DOM markers (`curl -s https://wonderful-margulis-8ec96b.vercel.app/players/arch-manning | grep 'player-status-strip'`)

---

## §12. Post-Launch Iteration Plan

### 12.1 First 48 hours
- Monitor `logs/status_override_drift_<date>.log` for unexpected drift
- Watch for fan-reported errors via /r/CFB sub (no automated alert; manual scan)
- Spot-check 20 random player pages (use `python scripts/random_player_smoke.py --n 20`)

### 12.2 First week
- Audit manual seeds: `scripts/audit_manual_seeds.py` to surface any rows where override and computed status disagree
- Flag any "high-traffic" players (Heisman frontrunners) whose pages render incorrectly — fast-track override fixes
- Refine vocabulary based on user feedback (Twitter screenshots, etc.)

### 12.3 First month
- Backfill any missed 2026 draft picks if CFBD endpoint finally returns full data
- Re-run depth-chart and award-watch ingest as official watch lists publish (June 15 - July 15)
- Capture pre-fall-camp depth chart from On3 scrape (~Aug 10)
- Update fall-camp depth charts (~Aug 20-25 when programs publish week 1 charts)

### 12.4 Editorial override workflow (the hot loop)
When an editor needs to correct a player's status RIGHT NOW (e.g. a player declares transfer mid-summer):

```bash
# 1. Edit the override seed JSON
vim data/seeds/player_status_override_2026.json

# 2. Apply the change
python manage.py apply-status-overrides --season 2026

# 3. Rebuild just that player's page (incremental render)
python manage.py render-player <slug> --output-dir output/site

# 4. Local deploy
vercel deploy --prebuilt --prod --yes
vercel alias set <url> wonderful-margulis-8ec96b.vercel.app
```

Total time from notice to live: **~5-10 minutes**. This is the key advantage of the override layer.

---

## §13. Out of Scope (explicit, for clarity)

**NOT in Wave 25:**
- NIL valuation integration (Wave 26 — needs On3 API or scrape)
- Player headshots / photos (Wave 27 — needs licensing decision)
- NFL 2025-season stats integration for prior-year draftees (Wave 26)
- Multi-AI auto-correction of stale archetypes (Wave 28+ — override is v1 mechanism)
- Live in-game depth-chart updates during 2026 season (Wave 28)
- Real-time portal status during portal window (Wave 30 — separate streaming pipeline)
- Position-specific 2026 Outlook variants (e.g. RB Doak-watch vs WR Biletnikoff-watch — Wave 26)
- Multi-year career-arc storytelling for retired players (already shipped in `career_standing.py`)
- Awards-specific landing pages (Wave 30)
- "Spring Game performance" module (Wave 26 if we get the data)

---

## §14. Open Questions for User Decision

1. **NFL 2025-season stats** — for Gabriel/Sanders/Ward/Jeanty in their 2nd NFL season, should "Where They Ended Up" show their 2025 NFL stats, or just the destination card? **Recommend:** destination card only for Wave 25; defer NFL stat integration to Wave 26.

2. **Type C "transferred" data** — none of the original example players are actually Type C anymore (Beck/Mendoza drafted). Do we want to find Type C examples in DB (LJ Martin Florida State, Maalik Murphy → Oregon State, etc.) and verify variant 5B renders, or accept Type C is rare for marquee names in May 2026?

3. **NIL valuation** — On3 prominently shows NIL. Include in Outlook? (Needs new data source — On3 API or scrape; not in DB today.)

4. **Manual override scope** — Phase 1 step 1.8 says "top 100 marquee players." How is that list defined? **Suggest:** top 50 per position cohort + all 2026 NFL Draft picks + all 2025 NFL Draft picks who are still active.

5. **Player photos** — Status Strip optionally accepts a player headshot. License available? **Recommend:** defer to Wave 27; team logos only for now.

6. **Season-phase gate sharpness** — should Status Strip suppress entirely during in-season weeks, or just change copy? **Recommend:** change copy ("Active · {team} {position} · Week {N}") but never suppress.

7. **Override audit trail** — should `player_status_override.set_by` accept free text, or a controlled vocabulary of operator usernames? **Recommend:** controlled vocabulary (`editorial_2026_05_27`, `ops_kevin_2026`, etc.) — easier to audit later.

8. **Award position eligibility** — Heisman maps to `{QB, RB, WR, TE}` per spec. Should it also include defenders? (Charles Woodson 1997 set the precedent.) **Recommend:** include `DB, EDGE, LB` but make their Heisman badges rarer (e.g. only show if odds-board has them top-30).

---

## §15. Key File References (absolute paths)

| Item | Path |
|---|---|
| Spec | `C:\Users\kevin\Downloads\Desktop Transfer\Sports Website\WAVE_25_SPEC.md` |
| This plan | `C:\Users\kevin\Downloads\Desktop Transfer\Sports Website\WAVE_25_IMPLEMENTATION_PLAN.md` |
| Session intent | `C:\Users\kevin\Downloads\Desktop Transfer\Sports Website\.claude\session-intent.md` |
| Module init | `src/cfb_rankings/player_pages/__init__.py` |
| Closest LOC analog (Strip) | `src/cfb_rankings/player_pages/career_standing.py` |
| Closest LOC analog (Where-Ended-Up) | `src/cfb_rankings/player_pages/nil_draft.py` |
| Reuse target (supporting cast helpers) | `src/cfb_rankings/player_pages/supporting_cast.py:22` |
| Reuse target (season-title to replace) | `src/cfb_rankings/reporting.py:11764-11784` |
| reporting.py CSS bundle integration | `reporting.py:5219-5253` |
| reporting.py page_data integration | `reporting.py:9091-9290` |
| reporting.py HTML template injection | `reporting.py:19505` (Strip), `19526` (Outlook + Where-Ended-Up) |
| CFBD client | `src/cfb_rankings/clients/cfbd.py:9-385` |
| Draft ingest | `src/cfb_rankings/ingest/draft.py:76-144` |
| Roster ingest | `src/cfb_rankings/ingest/cfbd.py:897-945` |
| Returning production ingest | `src/cfb_rankings/ingest/cfbd.py:731-764` |
| Portal ingest | `src/cfb_rankings/ingest/cfbd.py:947-1040` |
| Migrations dir | `migrations/` — next slots `20260527_06..10` |

---

## §16. Execution Trigger

To start Wave 25:

```bash
# 1. Reconcile (Step 1-5 of §6)
git status && git fetch origin master && git merge --ff-only origin/master

# 2. Phase 1 sanity probe (BEFORE writing any code)
bash scripts/probe_cfbd_2026.sh
# If draft endpoint empty: bash scripts/scrape_2026_draft_pfr.sh first

# 3. Apply migrations
python manage.py apply-migrations
# Confirms 20260527_06..10 land

# 4. Seed override JSON manually (~2 hours)
$EDITOR data/seeds/player_status_override_2026.json
python manage.py apply-status-overrides --season 2026

# 5. Implement Phase 2-6 per §3, gated by §10
# Each phase: write code → run tests → render smoke → commit

# 6. Final build + deploy per §11
```

---

*Plan synthesized from three parallel research agents (codebase audit, CFBD
endpoint feasibility, risk register + reconciliation + test plan) over ~10
minutes of multi-AI work. Each section is cross-checked against the locked
spec at WAVE_25_SPEC.md and verified against live web sources (2026 NFL Draft
results, ESPN/On3 player pages, CFBD api-docs.json) as of 2026-05-27.*
