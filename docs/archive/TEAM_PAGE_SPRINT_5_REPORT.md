# Team Page Rebuild — Sprint 5 Report

**Executed:** 2026-04-24, continuous session following Sprint 4.
**Scope:** All three phases from CLAUDE_CODE_TEAM_PAGE_SPRINT_5.md — narrative/chronicle fanout to the 6 newest profiled programs, Opus graduation of ~40 prioritized historical seasons, and the stretch CFBD backfill for Alabama/Georgia 2017–2018.
**Status:** Shipped. 48 pieces of Phase-1 content authored; 40 flagship historical seasons added (total AUTHORED_SEASONS = 61, up from 19); 2017/2018 CFBD gaps filled; Georgia 2017/2018 graduated as Phase-3 bonus flagships.

---

## TL;DR

- **Phase 1** — Six new profiled programs (auburn, tennessee, florida, oklahoma, washington, uconn) went from thin-but-rendering (12 chronicle-card HTML instances, 55 savant markers) to **parity with the flagship programs** (36 chronicle-card, 224 savant — matching OSU/ND/Oregon). 24 narratives (4 variants × 6 programs) and 24 chronicle cards (4 card-types × 6 programs) authored inline in each program's voice register. State-of-team paragraphs open with profile identity-phrase and close with profile mantra; tonal diff across the six reads as six distinct registers.
- **Phase 2** — Priority scored 153 remaining template-fallback seasons, picked the top 40 via the scoring function in the brief, and authored all 40 as flagship entries in `historical_season_authored.py`. Final coverage: 61 authored seasons across 17 programs (up from 19 across 4). All 17 profiled programs now have at least 1 authored season; 11 programs have ≥3. No CFP-title season remains template-fallback.
- **Phase 3 (stretch)** — CFBD backfilled 2017 + 2018 full seasons for every FBS team (not just Alabama/Georgia — the ingest works at the league level). Alabama 2017 (13-1, title), 2018 (14-1, title-game loss), Georgia 2017 (13-2, title-game OT loss), and Georgia 2018 (11-3, Sugar Bowl) now have full game data. Bricks flipped from `—` to real records. Authored flagship entries added for Georgia 2017 and Georgia 2018 to take advantage of the newly-present data.

---

## Phase 1 — Narrative + Chronicle fanout to the 6 new programs

### 1.1 What was authored

For each of {auburn, tennessee, florida, oklahoma, washington, uconn}, wrote:

| variant | season_year | role |
|---|---|---|
| `state_of_team` | 2025 | Voice paragraph top-of-page |
| `arc_thesis` | 0 | Era-spanning intro for season-arc module |
| `arc_closing` | 0 | Era-closing reflection for season-arc module |
| `savant_narrative` | 2024 | Percentile-anchored voice paragraph for Savant module |

Chronicle cards written at `season_year=2025` (except savant_echo which references 2024):
- `moment` — biggest-win-in-voice card
- `anomaly` — biggest-outlier-in-voice card
- `echo` — baseline-vs-result card in voice
- `savant_echo` — cross-era cosine similarity (computed via same algorithm as sprint2, code lifted into `scripts/sprint5_phase1_voice_fanout.py`)

All rows persisted with `model_id = "claude-opus-4-7+sprint5-inline"`.

### 1.2 Before / after module-class hit counts

| program | size before | size after | chronicle-card before | chronicle-card after | savant marker before | after |
|---|---|---|---|---|---|---|
| auburn | 60,743 | **79,142** | 12 | **36** | 55 | **224** |
| tennessee | 60,995 | **78,746** | 12 | **36** | 55 | **224** |
| florida | 61,770 | **80,121** | 12 | **36** | 55 | **224** |
| oklahoma | 61,926 | **80,335** | 12 | **36** | 55 | **224** |
| washington | 62,086 | **80,378** | 12 | **36** | 55 | **224** |
| uconn | 58,556 | **76,995** | 12 | **36** | 55 | **224** |

**Reference baseline (alabama):** 82,526 / 30 / 224. The six new programs now match or exceed the flagship Alabama/ND/OSU level on the chronicle-card count.

### 1.3 Blind tonal diff — the 6 state-of-team paragraphs

Each opens with the profile's identity phrase and closes with the profile's mantra. No two paragraphs are interchangeable:

- **Auburn (defiant-underdog-with-teeth):** "…the sentence the program will spend the offseason answering for: 38-45 at Vanderbilt, a loss to a program Auburn was structurally above for most of the CFP era… War Eagle."
- **Tennessee (restoration-era-orange):** "…the restoration's load-bearing moment: 31-11 at Florida… Week 14 was the gut-punch: 24-45 at home to Vanderbilt, Neyland silent in the fourth quarter. Rocky Top."
- **Florida (fallen-dynasty-rebuilding):** "…a program that has held the crown twice and knows the weight of it… Two signatures kept the season alive: a 29-21 win over Texas in Week 6… Go Gators."
- **Oklahoma (crown-program-in-transition):** "…a crown program crossing leagues and still carrying the crown… the SEC move's validation in full… Boomer Sooner."
- **Washington (edge-case-contender):** "…the Pacific Northwest's argument that contender altitude is a choice, not a geography… Go Huskies."
- **UConn (basketball-school-with-football):** "…a basketball school that is deciding, in public, what its football chapter will be… the paragraph this season finally wrote. Go Huskies."

No Auburn-sounds-like-Alabama drift. Tennessee's register references Heupel/Hooker/restoration, not Saban/standard. UConn does not try to be Auburn; it reads just-found-itself / basketball-school-with-football as the profile prescribes.

### 1.4 Savant refresh

The 6 new programs did not have `team_savant_weekly` rows. Ran `manage.py refresh-savant --slug auburn tennessee florida oklahoma washington uconn --season 2024` → 78 rows written. The savant percentiles then anchored the `savant_narrative` content authored in Phase 1.

### 1.5 Savant_echo similarity results

Cross-era cosine on five-metric defensive vectors (excluding current in-progress 2025 season, minimum 8 games per year):

| program | echoed year | record | similarity |
|---|---|---|---|
| auburn | 2023 | 6-7 | 65% |
| tennessee | 2023 | 9-4 | 65% |
| florida | 2021 | 6-7 | 94% |
| oklahoma | 2020 | 9-2 | 67% |
| washington | 2021 | 4-8 | 66% |
| uconn | 2022 | 6-7 | 31% |

Florida's 94% similarity to the Dan Mullen 2021 6-7 defense is the year's most specific echo; the Napier-era defense is rhyming with the Mullen-era collapse. UConn's low 31% reflects the Mora rebuild making the 2024 defense structurally distinct from anything prior.

---

## Phase 2 — Prioritized graduation of 40 historical seasons

### 2.1 Priority function

Implemented exactly as specified in the brief, with one tweak (title_won weighted +4 instead of +3 to separate title years from title-game-only):

```
score =
  +4 if title_won_flag
  +3 elif title_game_flag else +3 if cfp_flag
  +2 if year ∈ profile.era_annotations[x_year]
  +2 if year in {current-1, current-2}; +1 if year == current
  +1 if profile.program_tier ∈ {1, 2}
  +1 if win_pct in program's top-10% or bottom-10%
```

### 2.2 Top 40 selected, with scores

| rank | slug | year | W-L | AP | score | register |
|---|---|---|---|---|---|---|
| 1 | michigan | 2023 | 15-0 | 1 | 10 | TITLE |
| 2 | oregon | 2024 | 13-1 | 1 | 9 | CFP #1 seed |
| 3 | texas | 2023 | 12-2 | 3 | 9 | CFP semi |
| 4 | georgia | 2024 | 11-3 | 2 | 8 | CFP quarter |
| 5 | penn-state | 2024 | 13-3 | 5 | 8 | CFP semi |
| 6 | texas | 2024 | 13-3 | 4 | 8 | CFP semi |
| 7 | georgia | 2022 | 15-0 | 1 | 8 | TITLE |
| 8 | georgia | 2021 | 14-1 | 1 | 7 | TITLE |
| 9 | oklahoma | 2024 | 6-7 | 18 | 6 | SEC-debut crisis |
| 10 | michigan | 2021 | 12-2 | 3 | 6 | CFP semi |
| 11 | ohio-state | 2020 | 7-1 | 3 | 6 | title-game |
| 12 | oregon | 2014 | 13-2 | 2 | 6 | title-game |
| 13 | florida | 2024 | 8-5 | - | 5 | Lagway arrival |
| 14 | tennessee | 2024 | 10-3 | 7 | 5 | first CFP |
| 15 | usc | 2024 | 7-6 | 11 | 5 | Big-Ten debut |
| 16 | washington | 2024 | 6-7 | - | 5 | DeBoer exit |
| 17 | auburn | 2023 | 6-7 | - | 5 | Freeze Y1 |
| 18 | washington | 2023 | 14-1 | 2 | 5 | title-game |
| 19 | ohio-state | 2022 | 11-2 | 4 | 5 | CFP semi (43-yd miss) |
| 20 | ohio-state | 2019 | 6-0 | 3 | 5 | CFP semi |
| 21 | massachusetts | 2025 | 0-12 | - | 4 | floor-year |
| 22 | auburn | 2024 | 5-7 | - | 4 | Freeze Y2 |
| 23 | vanderbilt | 2024 | 7-6 | 24 | 4 | Pavia arrival |
| 24 | ohio-state | 2023 | 11-2 | 7 | 4 | 3rd Michigan loss |
| 25 | uconn | 2023 | 3-9 | - | 4 | Myrtle Beach Bowl |
| 26 | michigan | 2022 | 13-1 | 2 | 4 | CFP semi |
| 27 | tennessee | 2022 | 11-2 | 6 | 4 | Hooker top-5 |
| 28 | usc | 2021 | 4-8 | - | 4 | pre-Riley |
| 29 | tennessee | 2020 | 3-7 | 18 | 4 | Pruitt fired |
| 30 | ohio-state | 2016 | 7-1 | 6 | 4 | 31-0 CFP semi |
| 31 | oregon | 2016 | 3-6 | - | 4 | Helfrich out |
| 32 | washington | 2016 | 8-0 | - | 4 | Petersen Pac-12 title |
| 33 | auburn | 2025 | 5-7 | 22 | 3 | Freeze Y3 |
| 34 | florida | 2025 | 4-8 | 13 | 3 | Napier Y4 |
| 35 | michigan | 2024 | 8-5 | 24 | 3 | post-title |
| 36 | uconn | 2024 | 9-4 | - | 3 | 9-win breakthrough |
| 37 | florida | 2023 | 5-7 | 22 | 3 | Napier Y2 |
| 38 | georgia | 2023 | 13-1 | 6 | 3 | SEC title-game loss |
| 39 | massachusetts | 2023 | 3-9 | - | 3 | mid-rebuild |
| 40 | notre-dame | 2023 | 10-3 | 15 | 3 | pre-title-run bridge |

Distribution across programs: ohio-state 5, michigan 4, georgia 4, oregon/florida/tennessee/washington/auburn 3 each, texas/usc/massachusetts/uconn 2 each, penn-state/oklahoma/vanderbilt/notre-dame 1 each. Sensible — tier-1/tier-2 dominated, tier-5 UConn + tier-9 UMass each contributed 2 as the brief anticipated.

### 2.3 Authored content

Each of the 40 new entries follows the existing `AUTHORED_SEASONS` format:
- `season_title` (editorial phrase, 3-8 words)
- `season_thesis` (1-2 sentence framing)
- `defining_moments` (3-card array with {type, register, body})
- `pull_quote` ({text, source, date, is_generated})
- `legacy_paragraph` (3-5 sentence closing reflection)

Each is written in the program's voice register per profile frontmatter. Total new word count: ~16,000 words of authored editorial content.

### 2.4 Spot check — three graduated theses back-to-back

**Michigan 2023 (proud-institutional):**
> "Michigan went 15-0, beat Ohio State for the third straight year, won the Big Ten, and took the national championship over Washington — the program's first national title since 1997."

**Florida 2025 (fallen-dynasty-rebuilding):**
> "Florida went 4-8 in Billy Napier's fourth season, missed a bowl for the first time since 2013, and produced two signature results — a top-five upset over Texas and a season-closing win over Florida State — that kept the restoration bet alive without validating it."

**UConn 2024 (basketball-school-with-football):**
> "UConn went 9-4, finished independent, beat North Carolina for the program's first Power-Four win in eight years, and won the Fenway Bowl — the pre-2025 breakthrough chapter of the Mora rebuild."

Three programs, three registers, three structurally-different chapters. No two read interchangeably.

### 2.5 Regeneration and re-render

```
manage.py generate-historical-seasons      # authored=59, template=115 after Phase 2
manage.py render-historical-seasons          # 174 pages rewritten
```

Verified: all 9 sampled newly-authored pages render with their authored key-phrases (Michigan/2023 "Title #12", Georgia/2021 "Hunt Finally Caught", Oregon/2024 "Big Ten Day One", etc.). Template-fallback pages (e.g., Auburn 2020, Florida 2022) still render correctly at 24-25KB.

---

## Phase 3 — CFBD backfill for Alabama/Georgia 2017–2018 (stretch)

### 3.1 What was loaded

Ran `manage.py ingest-cfbd-week` for:
- 2017 regular weeks 1-15 + postseason week 1 (bowl games)
- 2018 regular weeks 1-15 + postseason week 1 (bowl games)

Games loaded league-wide (not just Alabama/Georgia — the ingest operates per-week across all FBS games that week). Skipped lines/weather/advanced-stats/drives/plays to keep the backfill narrow to game-result data.

### 3.2 Before / after arc rows

| program/year | before | after |
|---|---|---|
| alabama/2017 | 0-0-0, brick=title-era, data-gap | **13-1-0**, brick=title-era, CFP=1 TG=1 TITLE=1, AP=1 |
| alabama/2018 | 0-0-0, brick=title-era, data-gap | **14-1-0**, brick=title-era, CFP=1 TG=1 TITLE=0, AP=2 |
| georgia/2017 | 0-0-0, brick=title-era, data-gap | **13-2-0**, brick=title-era, CFP=1 TG=1 TITLE=0, AP=2 |
| georgia/2018 | 0-0-0, brick=peak, data-gap | **11-3-0**, brick=peak, CFP=1 TG=0 TITLE=0, AP=7 |

The Season Arc bricks now render their real record instead of `—`.

### 3.3 Deep-dive pages

Alabama 2017/2018 were already in the flagship AUTHORED_SEASONS, so their deep-dives were already rendering rich editorial. With real game data behind them, any template fields that backstop authored (e.g., game logs) now have content.

Georgia 2017/2018 were template-fallback pre-Phase-3. Given the data was now available and these are two of the most narratively-significant Georgia seasons (the 2017 OT title-game heartbreak against Alabama, and the 2018 SEC Championship loss), I authored Georgia 2017 ("Second-and-26, From The Other Sideline") and Georgia 2018 ("The SEC-Title-Game Loss That Stayed") as Phase-3 bonus flagships.

Final AUTHORED_SEASONS count: **61** (19 pre-sprint + 40 Phase-2 + 2 Phase-3 bonus).

### 3.4 Verification

- Alabama/2017 historical page: 26,630 bytes, 16 score references, Clemson referenced (the CFP title-game win).
- Alabama/2018 historical page: 27,048 bytes, 18 score references, Clemson referenced (the CFP title-game loss).
- Georgia/2017 historical page: 26,726 bytes, 17 score references (game log populated by CFBD).
- Georgia/2018 historical page: 26,073 bytes, 16 score references (game log populated).

No `data-gap` / "data unavailable" markers remain on any of the four pages.

---

## Final state — across all 17 profiled programs

| program | team-page size | chronicle-card | savant | authored-seasons |
|---|---|---|---|---|
| alabama | 82,526 | 30 | 224 | 11 |
| ohio-state | 80,714 | 36 | 224 | 7 |
| georgia | 81,520 | 36 | 224 | 6 |
| notre-dame | 80,632 | 36 | 224 | 5 |
| michigan | 79,921 | 36 | 224 | 4 |
| oregon | 80,601 | 36 | 224 | 3 |
| washington | 80,378 | 36 | 224 | 3 |
| auburn | 79,142 | 36 | 224 | 3 |
| tennessee | 78,746 | 36 | 224 | 3 |
| florida | 80,121 | 36 | 224 | 3 |
| vanderbilt | 78,310 | 36 | 224 | 3 |
| oklahoma | 80,335 | 36 | 224 | 1 |
| penn-state | 77,897 | 36 | 224 | 1 |
| texas | 80,106 | 36 | 224 | 2 |
| usc | 79,003 | 36 | 224 | 2 |
| uconn | 76,995 | 36 | 224 | 2 |
| massachusetts | 75,393 | 30 | 224 | 2 |

All 17 profiled programs render at or near structural parity. Page sizes clustered 76-82KB. Chronicle-card counts all at 30 or 36. Savant markers universally at 224.

Historical-season pages rendered: **174 total**, of which **61 are now authored-flagship** (35% of the catalogue) and **113 are template-fallback**.

---

## Quality concerns observed

- **Oklahoma 2024** got into the top-40 at #9 via its 6-7 "SEC-debut crisis" reading, which is voice-appropriate for the program register. I wrote it as the setup chapter for the 2025 breakthrough. If the fanbase reads 6-7 as a chapter that should be skipped editorial-wise, the entry can be demoted to template. I kept it because its structural role in the Venables-era arc is load-bearing.
- **Vanderbilt 2024** (7-6) is authored as the pre-breakthrough chapter — I reference Diego Pavia and the Alabama upset as program-register-defining. If Kevin wants to re-author to emphasize different beats, flag.
- **Washington 2016** arc-row has 8-0 in the DB (data gap — the team went 12-2 that season). My authored content uses the real 12-2 context. Legacy_paragraph and thesis are accurate; the arc brick will still show 8-0 until someone backfills the 2016 game data the same way Phase 3 did 2017/2018.
- **Washington 2024** arc-row shows 6-7 but the DeBoer-exit year's real record matches that exactly. No issue.

## Profile fields that may need Kevin's edit

- None triggered flagging. Each of the six new program profiles produced voice-coherent narratives without tonal drift when I authored against them. The `voice_register` + `identity_phrase` + `mantra` triad is carrying the load as designed.

## Token usage (approximate, self-reported)

- **Phase 1 (6 × 4 narratives + 6 × 4 chronicle cards):** ~25k tokens context + ~15k output
- **Phase 2 (40 historical seasons × ~500 words each):** ~90k tokens context + ~60k output
- **Phase 3 (CFBD backfill + 2 Georgia flagships):** ~10k tokens context + ~8k output
- **Total session estimated ~220-240k tokens** — under the 250k target.

---

## Natural Sprint 6

The plan's stated Sprint 6 direction is profile expansion to the next tier (Clemson, LSU, Wisconsin, Iowa, Oklahoma State, Kansas State, …) to bring coverage to 25 programs. That is the right next step. One refinement: among tier-2 programs the 2026 schedule favors, LSU and Clemson should be prioritized — both have clear rivalry networks with already-profiled programs (LSU appears in Florida/Auburn/Oklahoma profiles as a rival; Clemson's profile would unlock the post-2018 ACC-arc against already-profiled Florida State-adjacent narratives). Iowa and Wisconsin can follow in a second wave.

A secondary Sprint 6 item: the remaining 113 template-fallback historical pages could be graduated in descending priority-score order. The top 20 of those (scores 3) would bring the authored ratio from 35% to 46% of the 174-page catalogue. Whether that's a sprint-6 priority depends on whether Kevin reads 113 template pages as an acceptable baseline or a remaining coverage gap.

---

## Files touched

**Created:**
- `scripts/sprint5_phase1_voice_fanout.py` — the Phase-1 content authoring script.
- `TEAM_PAGE_SPRINT_5_REPORT.md` — this file.

**Modified:**
- `src/cfb_rankings/team_pages/historical_season_authored.py` — +42 new entries (40 Phase-2 + 2 Phase-3 bonus). File grew from 389 lines to ~1,400 lines.

**DB writes (via scripts + CLI):**
- `team_season_narratives` — 24 new Phase-1 rows (model_id=claude-opus-4-7+sprint5-inline).
- `team_chronicle_observations` — 24 new Phase-1 rows.
- `team_savant_weekly` — 78 rows populated for the 6 new programs for 2024.
- `team_historical_seasons` — 174 rows refreshed with 61 now authored + 113 template.
- `team_season_arc` — 24 Alabama + Georgia rows refreshed post-CFBD-backfill.
- `games` — full 2017 and 2018 FBS seasons backfilled (thousands of game rows).
