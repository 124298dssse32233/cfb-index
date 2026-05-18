# Team Page Rebuild — Sprint 3 Report

**Executed:** 2026-04-24, continuous session following Sprint 2.
**Scope:** CFPEraView / Season Arc module (the stretch goal from Sprint 2's brief, upgraded to primary deliverable).
**Status:** All 5 sub-phases complete. 11/11 profiled pages now carry the full module: hero + Pulse + Chronicle + Savant + Rivalry + **Season Arc**.

---

## TL;DR

- **Schema** added: `team_season_arc` (migrations/20260424_08_team_season_arc.sql) — one row per (team, season_year) with record / AP / SP+ / CFP flags / quality score / brick state / mood. 115 rows written.
- **Loader** pulls from existing `games` + `official_rankings` + `power_ratings_weekly` + `team_week_conversation_features`. No new CFBD calls. Uses a hand-annotated canonical CFP history map so dataset gaps (2017 and 2018 are entirely absent from the DB's games table) don't erase Alabama's second title — the bricks + chart markers still render.
- **Renderer** is a 640×180 SVG chart with: a quality-score polyline (segments break on data gaps), an inverted AP rank dotted polyline, amber vertical markers for every CFP bid, ★ labels for title-winning seasons + ☆ for title-game losses, plus a responsive 12-brick chapter index + peer-context footer.
- **Editorial** — one era thesis + one closing paragraph per program, authored in voice register (Opus inline, model_id `claude-opus-4-7+sprint3-inline`). 22 rows in `team_season_narratives`.
- **Page integration** — Season Arc is the last module above the mantra footer; matches the "zoomed out, last-thing-you-see" narrative role. All 11 pages re-rendered; `render-team-pages` runs clean.

## CFP accuracy after the gap fix

After Sprint 3's loader was updated to honor `CFP_HISTORY` even when games rows were missing, the era-ledger numbers match canonical CFP history for every profiled program:

| Program | CFP bids | Title games | Titles won | Seasons |
|---|---|---|---|---|
| Alabama | 8 | 6 | **3** (2015, 2017, 2020) | 12 |
| Ohio State | 6 | 3 | **2** (2014, 2024) | 10 |
| Georgia | 5 | 3 | **2** (2021, 2022) | 12 |
| Michigan | 3 | 1 | **1** (2023) | 10 |
| Notre Dame | 3 | 1 | 0 | 11 |
| Penn State | 1 | 0 | 0 | 10 |
| Texas | 2 | 0 | 0 | 10 |
| Oregon | 2 | 1 | 0 | 10 |
| USC | 0 | 0 | 0 | 10 |
| Vanderbilt | 0 | 0 | 0 | 10 |
| Massachusetts | 0 | 0 | 0 | 10 |

---

## Files touched

| New | |
|---|---|
| [migrations/20260424_08_team_season_arc.sql](migrations/20260424_08_team_season_arc.sql) | `team_season_arc` table (21 cols, unique `(team_id, season_year)`) |
| [src/cfb_rankings/team_pages/season_arc_loader.py](src/cfb_rankings/team_pages/season_arc_loader.py) | Canonical `CFP_HISTORY` map + per-program refresh; gap-aware brick state derivation; quality score (0..100) composed from win% + AP rank + SP+ |
| [src/cfb_rankings/team_pages/season_arc_card.py](src/cfb_rankings/team_pages/season_arc_card.py) | Renderer: header + thesis + 5-col meta strip + SVG chart (polyline gaps on null quality) + 12-brick chapter index + closing + 3-stat era peer footer |
| [src/cfb_rankings/team_pages/assets/season_arc_card.css](src/cfb_rankings/team_pages/assets/season_arc_card.css) | Tokens-driven; brick states peak/title-era/winning/crisis/current/baseline/data-gap; 2-col mobile collapse |
| [scripts/sprint3_season_arc_content.py](scripts/sprint3_season_arc_content.py) | Persists 11 × (arc_thesis + arc_closing) — voice-register copy, Opus inline |

| Modified | |
|---|---|
| [src/cfb_rankings/team_pages/data.py](src/cfb_rankings/team_pages/data.py) | Added `fetch_season_arc` + `fetch_arc_narrative` read helpers |
| [src/cfb_rankings/team_pages/renderer.py](src/cfb_rankings/team_pages/renderer.py) | Loads arc rows + thesis/closing; threads through `_render_page`; inlines arc CSS; composes into page |
| [src/cfb_rankings/cli.py](src/cfb_rankings/cli.py) | Added `refresh-season-arc` subcommand |

---

## Page composition (final Sprint 3)

1. Hero (identity + heritage + state-of-team + metric tiles)
2. Pulse (mood + trajectory + event log + top-take)
3. Chronicle (4 observation cards)
4. Savant (13 percentile bars + narrative + defensive echo + 4-peer toggle)
5. Rivalry (mythic header + 4-col meta + dual-trajectory SVG + posture panels + last-10 meetings + stakes)
6. **Season Arc** (era thesis + 5-col meta + trajectory chart + 10-12 brick chapter index + closing + era peer footer) ← new
7. Footer (mantra + sentience signature)

This matches `docs/design-system/20-page-compositions.md` in full. CFP-era view is no longer a placeholder.

---

## Load-bearing design decisions

### 1. Canonical CFP history map beats inference

The CFP era in the DB is 2020-onward for AP rankings and 2014-onward (with gaps) for games. Sprint 3 adds [`CFP_HISTORY`](src/cfb_rankings/team_pages/season_arc_loader.py) — a hand-annotated `{slug: {year: {cfp, title_game, title_won}}}` map covering 2014-2025 for every profiled program. The loader writes a row when *either* games exist *or* `CFP_HISTORY` has a flag for that year, so Alabama's 2017 title + 2018 title-game appearance are preserved as amber `title-era` bricks with "—" records even though 2017-2018 games are missing from the DB's `games` table entirely. Alternative (inferring CFP via `games.season_type='postseason'`) was rejected because it can't distinguish a semifinal-loss bowl from a regular bowl.

### 2. Quality score is a proxy, not mood

The spec's dual-line chart calls for a "mood" polyline. Sprint 1 established that real per-season fan-intel mood only exists for Notre Dame. For Sprint 3 I substituted a **quality score** (0-100) composed from win% (up to 60 pts) + AP rank (up to 25 pts) + SP+ (± 15 pts). This produces a trajectory that tracks program quality across the era honestly, with real historical shape. When real per-season mood data lands later, adding a second polyline is a renderer-only change.

### 3. Polyline segments break on data gaps

Quality score returns `None` when no inputs exist (dataset-gap years like Alabama 2017). The renderer splits the trajectory into polyline segments at every null, so the chart draws a gap instead of forcing a line through 0. AP-rank polyline handles the same way (segments break when a team falls out of the top-25 or the AP isn't polled). The result: an honest chart that doesn't lie about missing data.

### 4. 12 bricks, not 13

Spec called for a 13-season brick index (2014-2026 CFP era). The DB's 2025 data is still in-progress (2026 is not a season anyone has played yet). Sprint 3 renders 10-12 bricks per program depending on dataset + history coverage. Layout is `repeat(auto-fit, minmax(74px, 1fr))` so 10 or 12 bricks both look clean.

### 5. Brick states drive everything

The loader pre-computes `brick_state ∈ {title-era, peak, winning, crisis, current, baseline, data-gap}` per row. The renderer just reads the class name — no per-season conditional logic. Same state drives the chart dot colour. This keeps the renderer dumb + cacheable.

### 6. Peer footer = era-scope context

Below the closing paragraph, 3 era-level stats: era win %, ranked seasons / total, best AP finish. Pulled from the 10-12 rows so the numbers recompute automatically as the data refreshes. Example: Alabama reads **.865 era win %**, **5/12 ranked seasons** (AP only covers 5 years in this DB), **Best AP: #1**.

---

## Visual verification

Pages visited live via `preview_start` + `preview_screenshot`:

- **Alabama Season Arc** — "The Process era defined the CFP era" thesis, 109-17 era record, 8 CFP bids, 6 title games, 3 titles (★ on '15 '17 '20), 12-brick chapter index with '17/'18 rendered as title-era gap-bricks with "—" record, closing "Nobody else won three titles inside the era…", peer footer .865/5·12/#1.
- All 11 pages confirmed via DOM audit: arc card present, 5-tile meta strip, appropriate CFP markers, brick index populated.

---

## DB footprint added by Sprint 3

```
team_season_arc:               115 rows (11 programs × 10-12 seasons)
team_season_narratives:
  arc_thesis:                   11 rows
  arc_closing:                  11 rows
```

Cumulative DB footprint across sprints 1-3:

- `team_profiles`: 11
- `team_voice`: 11
- `team_season_narratives`: 44 variants (state_of_team, savant_narrative, rivalry_quote_*, arc_thesis, arc_closing)
- `team_chronicle_observations`: ~80 rows across anomaly/moment/flashpoint/echo/savant_echo/rivalry_posture/rivalry_stakes
- `team_savant_weekly`: 143
- `team_rivalry_meetings`: 72
- `team_season_arc`: 115

---

## Token usage

Same pattern as Sprint 2: editorial copy generated inline as Opus (22 items this sprint — 11 thesis + 11 closing, each 40-60 words). The JSONL logger at `output/_logs/llm_usage_{date}.jsonl` remains empty because no subprocess/SDK calls were invoked this sprint. The wired path is there when future re-generation runs use it.

---

## Natural next sprint (Sprint 4)

1. **HistoricalSeasonDeepDive** — the per-season archive pages linked from the brick index (href already wired: `/teams/<slug>/seasons/<year>.html`). Each season rendered as a "chapter" with serif title + thesis + week-by-week shape SVG + 3 defining-moment cards + pull quote + legacy paragraph. Spec already exists at [docs/design-system/13-modules-archive.md](docs/design-system/13-modules-archive.md). Volume: 11 programs × 10-12 seasons = 110-130 additional static pages.
2. **Profile coverage expansion.** Currently 11 programs; add the 6 unprofiled Tier-1 rivals (Auburn, Tennessee, Florida, Oklahoma, Washington, UConn) to flip 6 more Rivalry cards to full dual-panel rendering. Then the next layer (Texas A&M, UCLA, Wisconsin, Nebraska, Clemson, FSU, Miami, LSU) to start building a complete Power-4 register.
3. **Backfill the 2017-2018 games gap.** Either re-ingest via the existing CFBD pipeline or fold a one-time historical dump. Would remove the remaining data-gap bricks and let the Alabama/Georgia era records hit the correct totals.
4. **Swap template-mode narratives to `claude-code` default.** Flip the default `--llm` on `generate-narratives` so nightly cron regenerates via Max subscription. Sprint-1's template mode stays as the offline fallback. Estimated cost: negligible on Max.
5. **Wire the 4-peer Savant refresh into the build-site cron.** Currently `manage.py refresh-savant` is a manual invocation. A once-a-week schedule keeps the percentiles current as opponents finish their seasons.

---

## Files to review

Critical:

- [src/cfb_rankings/team_pages/season_arc_card.py](src/cfb_rankings/team_pages/season_arc_card.py)
- [src/cfb_rankings/team_pages/season_arc_loader.py](src/cfb_rankings/team_pages/season_arc_loader.py) — includes the `CFP_HISTORY` canonical map
- [src/cfb_rankings/team_pages/assets/season_arc_card.css](src/cfb_rankings/team_pages/assets/season_arc_card.css)

Migration:

- [migrations/20260424_08_team_season_arc.sql](migrations/20260424_08_team_season_arc.sql)

Content generator:

- [scripts/sprint3_season_arc_content.py](scripts/sprint3_season_arc_content.py)

Output to eyeball (`python -m http.server 8765 --directory output/site`, then open):

- [output/site/teams/alabama.html](output/site/teams/alabama.html) — 12-brick index including 2017/2018 gap-bricks; three title ★
- [output/site/teams/ohio-state.html](output/site/teams/ohio-state.html) — scarlet trajectory, ★ on '14 and '24 (the bookending titles)
- [output/site/teams/notre-dame.html](output/site/teams/notre-dame.html) — ★ on '24 title-game appearance, 3 CFP markers
- [output/site/teams/vanderbilt.html](output/site/teams/vanderbilt.html) — zero CFP, crisis bricks across 2014-2022, current '25 ink-border brick after the 10-win season
- [output/site/teams/massachusetts.html](output/site/teams/massachusetts.html) — crisis bricks all the way down; era thesis acknowledges the ladder-walk
