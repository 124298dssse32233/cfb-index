# CFB Index — Site-Quality Discovery (Phase 0)

**Date:** 2026-06-11
**Author:** Claude Code (primary verification agent) — `/octo:embrace` lifecycle, Phase 0 Discover
**Branch:** `feature/site-quality-2026-06-11`
**Method:** Every material finding below was verified first-party against the current branch, the canonical local `cfb_rankings.db`, generated `output/site/`, pipeline logs, workflows, and the live production alias `wonderful-margulis-8ec96b.vercel.app`. External-model (council) output is advisory only and is **not** the basis of any finding here.

> **Reading order:** §1 Verification ledger (audit leads → verdict + evidence) → §2 Confirmed problems (prioritized) → §3 Source→table→metric→module→page matrix → §4 Empty/dead tables → §5 Duplicate modules & dead UI → §6 Build/nav/smoke inconsistency → §7 Historical depth → §8 Provenance & registry reality → §9 Cleared / intentional / already-fixed → §10 DATA_SOURCES_EXPLAINED.md corrections.

---

## 0. Snapshot facts (verified 2026-06-11)

| Fact | Value | Evidence |
|---|---|---|
| DB tables | 192 | `SELECT count(*) FROM sqlite_master WHERE type='table'` |
| `cfb_rankings.db` | canonical local box DB | CLAUDE.md (box-first deploy) |
| Latest build | 2026-06-11T19:16Z | `output/site/_build_manifest.json` (`built_at`) |
| Season/phase | 2025 / week 21 / offseason | `_build_manifest.json`; `offseason_week_map`=11 rows |
| Newest conversation doc | 2026-06-11 18:46Z | `MAX(collected_at_utc)` — **collection is fresh** |
| Live homepage | 200 | `curl -I https://wonderful-margulis-8ec96b.vercel.app/` |

---

## 1. Verification ledger — every audit lead

Classification key: **CONFIRMED** (current problem) · **FIXED** (already addressed) · **INTENTIONAL** (design choice) · **STALE** (was true, now false) · **ENV** (environment-specific, no prod impact) · **CLEARED** (false positive) · **PARTIAL** (true but impact differs from lead).

| # | Audit lead | Verdict | Evidence (command / query / URL — verified 2026-06-11) |
|---|---|---|---|
| 1 | `/offseason/` and `/film-room/` return 404 live | **CONFIRMED** | `curl -o/dev/null -w %{http_code}` → both **404**. `output/site/` has no `offseason/` or `film-room/` dir. |
| 2 | Canonical publishing paths don't build the same hubs | **CONFIRMED** | `scripts/build_publish.ps1` (box, **primary** deployer) only logs `"offseason: skipping…"` — never calls the hub scripts. `.github/workflows/publish_site.yml:519-530` *does* call `build_offseason_leaderboards.py` + `build_film_room.py`. Box also calls `render-today-in-history` (L216) which the workflow omits; workflow calls offseason/film-room which box omits. |
| 3 | Live smoke suite omits globally linked routes | **CONFIRMED** | `scripts/smoke_test_live.py` checks 32 URLs `--fail-under 95`; list excludes `/offseason/`, `/film-room/`. So the 404s never trip the smoke alarm. |
| 4 | Large share of `conversation_documents` lack modern `source_id` | **CONFIRMED** | `194,972` rows, `43,479` (22.3%) have `source_id`. NULLs: reddit 146,843 / youtube 4,010 / board 633 / podcast 7. |
| 5 | Registry activation doesn't reflect collection health | **CONFIRMED** | `source_registry`: **all 84 rows `is_active=1`**. `scrape_health` today: 350 sources ran, 118 returned **0 rows** (e.g. `kalshi`,`seatgeek`,`spotify_charts`=0). Activation = config intent, not measured health. |
| 6 | Plays / drives / CFBD PBP empty | **CONFIRMED** | `plays`=0, `drives`=0, `cfbd_pbp_plays`=0, `cfbd_pbp_play_actors`=0. |
| 7 | Team Savant empty | **CONFIRMED** | `team_savant_weekly`=0. `refresh-savant` CLI exists (`cli.py:1778,3269`) but has never been run; needs `team_game_advanced_stats` (2025 only). Renderer hides cleanly when empty (`savant_card.py: if not rows: return ""`). |
| 8 | `prediction_ledger` / source profiles empty | **CONFIRMED** | `prediction_ledger`=0, `source_profiles`=0, `prediction_market_snapshots`=0. |
| 9 | Predictive claims unresolved | **CONFIRMED** | `predictive_claims`=266, **100% `outcome_resolved=0`**, all `outcome_verdict` NULL. Newest claim 2026-06-09. No resolution job has ever run. |
| 10 | Historical advanced-stat coverage incomplete | **CONFIRMED** | `team_game_advanced_stats` = **2025 only** (3,314). `games`/`player_game_stats` exist for 2020,2021,2022,**(no 2023)**,2024,2025 — irregular, partial backfill. |
| 11 | Player pages render duplicate legacy/v2 modules | **CONFIRMED** | In generated `players/fernando-mendoza-12763.html`: `peer-comparator`+`peer-comparator-v2`, `narrative-arc`+`narrative-arc-v2`, `scenario-explorer`+`scenario-explorer-v2`, `splits`+`splits-v2`, `supporting-cast`+`supporting-cast-v2`, **`player-standing` ×2**. (`mirror-match`, `coaching-lineage` are `v2 OR legacy` fallbacks — single render.) |
| 12 | Player pages expose unhelpful Live Signal Flow placeholder | **CONFIRMED** | `player_pages/live_signal_flow.py` always renders unless db/player_id is None; emits *"Live signal pipeline placeholder. Activates during season once conversation tracking lands."* with three `awaiting` bands. Present in generated QB page (grep count=1). |
| 13 | Polymarket `outcomePrices` parsing mishandles JSON-encoded strings | **PARTIAL** | Stored payload is the **string** `'["0.125","0.875"]'`. Write side (`prediction_markets.py:163-170`) does `float(outcomes[0])` → `float('[')` → caught → `prob_yes` dropped. `source_observations` polymarket = **300 rows, all `volume_usd`, 0 `prob_yes`**. **BUT** read side (`delusion.py:44-49`) `json.loads` the string defensively, so `delusion_premium_weekly` (10 rows) is correct. Real write-side defect, **low user-facing impact**. |
| 14 | Prod / local / rolling artifact diverge | **CONFIRMED (structural)** | Box `build_publish.ps1` is the only deploy path per CLAUDE.md (cloud cron retiring; cloud `cfb-rankings-db` artifact diverged player_id space). Box omits offseason/film-room → full-snapshot deploy clobbers them. Matches the 2026-06-10 wire/storylines/anniversary clobber class (memory: `deploy-clobber-root-cause`) which fixed those three but not these two. |
| 15 | `/the-room/` 404 | **CLEARED** | `/players/the-room.html` → **200**; nav/footer link the `.html` form, not top-level `/the-room/`. Not a broken promise. |
| 16 | `games_live` work needed | **INTENTIONAL/EXCLUDED** | `games_live`=0 and must stay so (prompt forbids live-game UI). Not a defect. |

---

## 2. Confirmed problems — prioritized

### P0 — Broken navigation promises (user-visible 404s)
- **`/offseason/` + `/film-room/` are linked in global nav but 404 in production.** Root cause: the box deployer (`build_publish.ps1`) doesn't generate them, and box deploys are **full snapshots**, so they're clobbered off prod. The cloud workflow that *does* build them is being retired. (Leads #1, #2, #14.)
- **The live smoke suite can't catch this** — neither route is in the 32-URL list. (Lead #3.)

### P1 — Truth/provenance integrity
- **77.7% of conversation docs have no `source_id`** — reddit/youtube/board legacy collectors write `source_name` but not the canonical `source_id`. (Lead #4.)
- **`source_registry.is_active` is meaningless as health** — all 84 active; many collect nothing. Health must be derived from `scrape_health`/`collection_ledger`, not the flag. (Lead #5.)
- **`DATA_SOURCES_EXPLAINED.md` overstates reality** — lists Kalshi/SeatGeek/podcasts/YouTube-comments/campus/athletics as "active/daily" though several are empty or stale today. (See §10.)

### P2 — Built-but-never-closed loops (must not be shown as accuracy)
- **Predictive claims (266) are 100% unresolved**; `prediction_ledger`, `source_profiles`, `editorial_citations`, `prediction_market_snapshots` all empty. The receipts/calibration machinery exists end-to-end in schema but the resolution + profile steps have never run. **Risk:** any surface that presents an unresolved claim as a "track record" would be dishonest. (Leads #8, #9.)
- **Polymarket `prob_yes` is 0% populated** (write-side string bug) — works today only because the one consumer reads raw payload. Any new consumer of `metric='prob_yes'` would get nothing. (Lead #13.)

### P3 — Empty derived datasets behind real modules
- **Team Savant** (`team_savant_weekly`=0) — command exists, never run; hides cleanly today. (Lead #7.)
- **Plays/drives/PBP=0** → `player_advanced_metrics*`, `player_pbp_metrics_season`, `player_mirror_matches` all 0. (Lead #6.)
- **Advanced stats = 2025 only**; no historical depth for trajectory/era comparisons. (Lead #10.)

### P4 — Frontend consolidation
- **5 duplicated player modules + `player-standing`×2** ship in every player page → wasted DOM, weaker hierarchy, repeated empty-states. (Lead #11.)
- **Live Signal Flow placeholder** ships an "awaiting / placeholder" scaffold in the live experience. (Lead #12.)

---

## 3. Source → raw table → derived table → metric → module → page matrix

Status columns: **Reg** (registered in `source_registry`) · **Coll** (collected ≤7d) · **Proc** (processed/derived rows exist) · **Rend** (rendered on a page) · **Health**.

| Source | Raw table(s) | Derived table(s) | Metric / feature | Module(s) | Page(s) | Reg | Coll | Proc | Rend | Health |
|---|---|---|---|---|---|:--:|:--:|:--:|:--:|---|
| Reddit (team/r-CFB) | `conversation_documents` (source_name=reddit, **source_id NULL**) | `team_conversation_daily`, `fanbase_mood_weekly`, `lexicon_term_daily`, `team_discourse_terms` | mood, lexicon, discourse | Fan Intelligence, Lexicon, Discourse Atlas, The Room | team, player, /fan-voice | ✅ | ✅ 140k/7d | ✅ | ✅ | **healthy but provenance-poor** |
| Bluesky curated | `conversation_documents` (source_id set) | same conversation pipeline | mood/discourse | Fan Intelligence | team/player | ✅ | ✅ 8,534/day | ✅ | ✅ | healthy |
| YouTube comments (team/nat) | `conversation_documents` (source_id NULL) | conversation pipeline | fan voice | Fan Intelligence | team/player | ✅ | ⚠️ team-comments **stale 05-13** | ✅ | ✅ | **stale (team)** |
| YouTube metadata | `source_observations` (youtube_meta) | buzz | attention | Backometer | team | ✅ | ✅ 2,289/day | ✅ | ✅ | healthy |
| Message boards | `conversation_documents` (board, source_id NULL) | conversation pipeline | die-hard voice | Fan Intelligence | team | ✅ | ⚠️ 633 total | ◑ | ✅ | thin |
| Podcasts (Locked On etc.) | `conversation_documents` (locked_on_*) | conversation pipeline | talking-heads voice | Discourse | team | ✅ | ✅ ~500/team | ✅ | ✅ | healthy |
| GDELT volume | `source_observations` (gdelt_volume) | `team_news_volume`(**0**) / backometer | news buzz | Backometer | team | ✅ | ✅ 69/day | ◑ | ✅ | healthy (volume); `team_news_volume` empty |
| GDELT tone | `source_observations` (gdelt_tone) | weekly tone | tone | (aggregate) | — | ✅ | ⚠️ **stale 05-13** | ◑ | — | stale |
| Wikipedia pv/edits | `source_observations` (wiki_pv/edits) | curiosity | attention | Backometer | team/player | ✅ | ✅ 147/32 day | ✅ | ✅ | healthy |
| Polymarket | `source_observations` (polymarket, **volume_usd only**) | `delusion_premium_weekly` (10) | market belief, delusion | Delusion hub, market chips | /hub/delusion, team/player | ✅ | ✅ 180/day | ◑ **prob_yes=0** | ✅ | **write-side bug (§1 #13)** |
| Kalshi | (none persisted) | — | market belief #2 | — | — | ✅ | ❌ **empty** | ❌ | ❌ | empty |
| SeatGeek | (none persisted) | — | ticket demand | — | — | ✅ | ❌ **empty** | ❌ | ❌ | empty |
| Spotify charts | (none persisted) | — | pod rank | — | — | ✅ | ❌ **0 rows** | ❌ | ❌ | empty |
| On3 NIL | `player_nil_valuations` (194) | — | NIL value | NIL chip | player | ✅ | (build) | ✅ | ✅ | healthy |
| CFBD — games/stats | `games`, `player_game_stats`, `team_game_advanced_stats`, `game_lines`, `game_weather`, `roster_entries`, `recruiting_entries`, `transfer_entries`, `returning_production`, `team_talent_snapshots`, `player_nfl_draft` | power/resume ratings, savant | rankings, profiles | Rankings, Team/Player pages, Recruiting Footprint, Draft Pipeline | most pages | ✅ | (build) | ✅ partial | ✅ | **advanced=2025-only; no 2023; PBP empty** |
| CFBD — plays/drives | `plays`(0), `drives`(0), `cfbd_pbp_*`(0) | `player_pbp_metrics_season`(0), `player_advanced_metrics`(0) | EPA/PPA splits, player advanced | (would feed Savant/player advanced) | team/player | ✅ | ❌ never ingested | ❌ | ❌ | **empty** |
| Wikipedia awards | `player_honors` (2,339) | accolades | honors | Selector Grid, Trophy Case | player | ✅ | (as needed) | ✅ | ✅ | healthy |
| Predictive extraction (LLM over docs) | `predictive_claims` (266) | `prediction_ledger`(0), `source_profiles`(0) | receipts/track record | Receipts | (planned) | n/a | ✅ extracted | ❌ **unresolved** | ❌ | **loop open (§1 #9)** |
| Team Savant (derived from CFBD adv) | `team_game_advanced_stats` (2025) | `team_savant_weekly`(**0**) | 13-metric percentiles | Savant card | team | n/a | n/a | ❌ never run | ❌ (hidden) | **not computed (§1 #7)** |

---

## 4. Empty / dead tables (0 rows) — selected, with disposition

| Table | Disposition |
|---|---|
| `plays`, `drives`, `cfbd_pbp_plays`, `cfbd_pbp_play_actors` | PBP never ingested → blocks Savant depth + player advanced metrics. **Backfill candidate (Phase 1).** |
| `team_savant_weekly` | Computable now from 2025 adv stats via `refresh-savant`. **Run it (Phase 1).** |
| `prediction_ledger`, `source_profiles`, `prediction_market_snapshots` | Receipts/calibration loop — schema present, never populated. **Operationalize (Phase 1/2).** |
| `editorial_citations` | Receipt-pattern citation store empty — verify whether receipts render from elsewhere or are dark. |
| `player_advanced_metrics`, `player_advanced_metrics_season`, `player_pbp_metrics_season`, `player_mirror_matches` | Depend on PBP. Mirror Match renders via a runtime fallback, not this table. |
| `team_news_volume`, `portal_moves`, `coaching_changes`, `team_historical_seasons` | Derived tables some modules may expect; confirm consumers before backfilling. `portal_moves`=0 but `transfer_entries`=14,804 (offseason hub should read the populated one). |
| `narrative_frame_stack`, `season_narrative_*`, `narrative_claim_stack`, `calendar_pressure`, `pipeline_checkpoints` | Chronicle scaffolding; empty is expected off-cycle. |
| `games_live`, `games_live_render_queue`, `game_predictions` | **Must stay empty** — live-game UI is out of scope. |

---

## 5. Duplicate modules & dead UI (player pages)

Verified in generated `output/site/players/fernando-mendoza-12763.html` (real, populated QB):

| Concept | Legacy renderer (reporting.py) | V2 renderer (player_pages) | Both render? |
|---|---|---|---|
| Peer comparator | `_render_v5_peer_comparator_card()` | `render_peer_comparator()` | **YES** (`peer-comparator` + `peer-comparator-v2`) |
| Narrative arc | `render_narrative_arc_card()` | `render_narrative_arc()` | **YES** |
| Scenario explorer | `render_scenario_explorer_card()` | `render_scenario_explorer()` | **YES** |
| Splits | `_render_v5_splits_card()` | `render_splits()` | **YES** |
| Supporting cast | `_render_v5_supporting_cast_card()` | `render_supporting_cast()` | **YES** |
| Player standing | (two standing renders) | `standing_rail.py` | **YES** (`player-standing` ×2) |
| Mirror match | `render_mirror_match_card()` | `render_mirror_match()` | No — `v2 OR legacy` fallback (single) |
| Coaching lineage | `render_coaching_lineage_card()` | `render_coaching_lineage()` | No — `v2 OR legacy` fallback (single) |

**Live Signal Flow:** `player_pages/live_signal_flow.py` always renders a placeholder (`data-state="awaiting"`, text *"Live signal pipeline placeholder…"*). Out of scope per the no-live-signal constraint and should be hidden/removed from the current experience (Phase 3).

**Consolidation rule:** keep the single strongest implementation per concept (the `… or fallback` pattern is the correct model — apply it to the 6 that currently double-render).

---

## 6. Build / nav / smoke inconsistency

| Hub | Box `build_publish.ps1` | Workflow `publish_site.yml` | On disk | Nav-linked | Live |
|---|:--:|:--:|:--:|:--:|:--:|
| storylines | ✅ | ✅ | ✅ | ✅ | 200 |
| wire | ✅ | ✅ | ✅ | ✅ | 200 |
| today-in-history (anniversary) | ✅ | ❌ | ✅ | ✅ | 200 |
| methodology | ✅ | ✅ | ✅ | ✅ | 200 |
| editions-archive | ✅ | ✅ | ✅ | ✅ | 200 |
| the-room (`/players/the-room.html`) | ✅ | ❌ | ✅ | ✅ | 200 |
| **offseason** | ❌ | ✅ | ❌ | ✅ | **404** |
| **film-room** | ❌ | ✅ | ❌ | ✅ | **404** |

**Root cause:** no single canonical build manifest. `_build_manifest.json` is a thin counts stub, not a route contract. The two deploy paths drifted; the box (now the only live deployer) is missing the two hubs the cloud path adds. **Fix shape (Phase 0):** one shared manifest of required routes; both paths build from it; build- and smoke-time assertions on every nav target.

**Global nav targets** (from `_site_nav()` in reporting.py): rankings, offseason, film-room, teams, players(spotlight), heisman, hub/vibe-shifts, programs, history, nfl-pipeline, about-model, conferences (+ action links matchups, compare). All resolve except offseason/film-room.

---

## 7. Historical depth & coverage

| Dataset | Seasons present | Gap |
|---|---|---|
| `games` | 2020, 2021, 2022, 2024, 2025 | **No 2023**; 2020/2022 partial counts |
| `player_game_stats` | 2020, 2021, 2022, 2024, 2025 | **No 2023** |
| `team_game_advanced_stats` | **2025 only** | No 2018-2024 |
| `player_nfl_draft` | (771 rows) | per CLAUDE.md 2018-2025 |

Phase 1 backfill must be **idempotent + resumable + rate-limited** and must verify each CFBD endpoint's real access/fields before committing — and must **not corrupt the rolling artifact** (build from the canonical box DB).

---

## 8. Provenance & registry reality

- **Provenance:** 22.3% `source_id` coverage. The gap is structural — legacy reddit/youtube/board adapters set `source_name` only. `scrape_health` keys on `reddit_rss_<team>` while docs carry `source_name='reddit'`, `source_id=NULL` — i.e. collection and document provenance use different identifier spaces. Reconstruction is defensible for these (map `source_name`+`source_channel` → canonical `source_id`); rows where origin can't be reconstructed should be labeled, not invented.
- **Registry health:** derive a real status from `scrape_health` (last run + rows>0 streak) and `collection_ledger` (`consecutive_failures`, `cooldown_until`), not `is_active`. 10 `collection_ledger` rows today — underused.
- **relevance_ml_score:** 51.3% coverage (100,000 scored — a capped soak). Per memory `relevance-status`, activation pending a 1-2 week soak.

---

## 9. Cleared / intentional / already-fixed / stale

- **CLEARED:** `/the-room/` 404 (it's `/players/the-room.html` = 200). Polymarket is *not* a user-facing outage (downstream-mitigated).
- **INTENTIONAL / EXCLUDED:** `games_live*`, `game_predictions` empty (live UI forbidden). `programs/<slug>.html` flat form. `/assets/...` absolute paths. "Awaiting Signal" fan-intel fallback.
- **STALE DOC:** `AGENTS.md` (2026-05-23) — says "17 profiled slugs" (now 119/119 FBS per CLAUDE.md + `ls profiles/*.md`), and its deploy section predates the 2026-06-10 box-first cutover. **Action:** supersede AGENTS.md by CLAUDE.md or refresh it.
- **ALREADY-FIXED (context):** wire/storylines/anniversary clobber (2026-06-10) — same class as the offseason/film-room bug, fixed for those three only.

---

## 10. DATA_SOURCES_EXPLAINED.md corrections (measured 2026-06-11)

`DATA_SOURCES_EXPLAINED.md` (refreshed today) lists these as active/daily; measured reality differs:

| Source | Doc says | Measured today | Correction |
|---|---|---|---|
| Kalshi | "Market belief, Daily" | `scrape_health` status=**empty**, 0 rows; no persisted rows | "registered; currently returning no data" |
| SeatGeek | "Ticket demand, Daily" | **empty**, 0 rows | "registered; not currently collecting" |
| YouTube comments (team) | "Casual fan voice, Daily" | **stale** (last 2026-05-13) | "intermittent / last collected 05-13" |
| Podcasts | "Daily (time-boxed)" | Locked-On RSS healthy; Finebaum/radio templates unproven | qualify by feed |
| Message boards | "Die-hard sentiment, Daily" | 633 docs total (thin) | "thin coverage" |
| GDELT tone | implied active | **stale** (05-13) | "weekly aggregate, currently stale" |
| Polymarket | "market belief" | volume only; `prob_yes` dropped | "belief via raw payload; numeric prob not persisted (bug)" |

The honest framing already in the doc ("No fake precision", "Awaiting Signal") is correct; the *per-source status table* needs to reflect collection outcomes, not registry intent. **Recommend** generating that table from `scrape_health` so it can't drift again.

---

## Appendix A — Reproduction commands

```bash
# Live nav check
for p in "" rankings/ offseason/ film-room/ players/the-room.html; do \
  curl -s -o /dev/null -w "%{http_code} /$p\n" "https://wonderful-margulis-8ec96b.vercel.app/$p"; done

# Table census
python -c "import sqlite3;c=sqlite3.connect('cfb_rankings.db').cursor();\
print([(t,c.execute(f'select count(*) from \"{t}\"').fetchone()[0]) for (t,) in \
c.execute(\"select name from sqlite_master where type='table'\")])"

# Provenance coverage
# select count(*), sum(source_id is not null) from conversation_documents;

# Predictive-claim resolution
# select outcome_resolved, count(*) from predictive_claims group by 1;   -> all 0

# Polymarket metric split (prob_yes missing)
# select metric, count(*) from source_observations where source_id='polymarket' group by 1;
```

— End of Phase 0 Discover —
