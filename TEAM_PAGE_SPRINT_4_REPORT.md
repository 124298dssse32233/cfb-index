# Team Page Rebuild — Sprint 4 Report

**Executed:** 2026-04-24, continuous session following Sprint 3.
**Scope:** All three phases from CLAUDE_CODE_TEAM_PAGE_SPRINT_4.md — Season Arc polish (v1.1), HistoricalSeasonDeepDive module, and profile-coverage expansion.
**Status:** Shipped. 17 profiled programs (was 11). 174 historical-season pages rendering. All 6 previously single-sided Rivalry cards now dual-panel.

---

## TL;DR

- **Phase 1 (Season Arc polish):** 5 of 6 polish items shipped in full; #6 (AP polyline coverage) partially addressed via a hand-annotated `FINAL_AP_HISTORY` map that fills 2014–2019 + 2021 for all 11 original programs. The remaining hole (no AP data in DB for pre-2020) is a data-ingest task, not a renderer bug. viewBox is now `0 0 640 210`, era ribbon bands render per profile, year-labels run `'14 '16 ... '24 NOW`, CFP markers extend full chart height with a "CFP" eyebrow, and era annotations (editorial callouts) render per profile.
- **Phase 2 (HistoricalSeasonDeepDive):** Full infrastructure plus content. New table `team_historical_seasons` (174 rows). New renderer at [historical_season_page.py](src/cfb_rankings/team_pages/historical_season_page.py) + CSS. Two CLI subcommands: `generate-historical-seasons` and `render-historical-seasons`. Integrated into `render_all_profiled_pages` so the build-site path picks up all 174 pages automatically. 19 flagship seasons hand-authored (Alabama's full 12-season era + 4 ND + 2 OSU + 2 Vandy); 155 template-fallback rows ready for Opus graduation via the CLI path.
- **Phase 3 (Profile expansion):** 6 new Tier-1 rival profiles shipped (Auburn, Tennessee, Florida, Oklahoma, Washington, UConn). Each follows the existing Alabama/Notre-Dame format: ~15-field YAML + 12 markdown sections + coaching_regimes + era_annotations. Voice tonally distinct across all six. The 6 previously-single-sided Rivalry cards on profiled programs now render full dual-panel with opponent voice.

---

## Phase 1 — Season Arc polish (v1.1)

### 1. Partial-data brick state — SHIPPED

New loader logic: `_is_partial_record()` marks any non-current season with fewer games in the DB than the era's regular-season floor (12 for pre-2020, 9 for 2020 COVID year). The partial flag is stored in `notes_json` and read at render time so it composes with `brick_state` instead of replacing it:

- **Alabama 2016** (was rendering "8-0" as title-era) — now shows `—` with italic muted record text + title-era gold retained. Tooltip shows `ingest incomplete (snapshot 8-0)`.
- **Alabama 2019** (was rendering "6-0" as baseline) — brick_state = `partial-data`; `—` record.
- **Vanderbilt 2016 / 2019** — same treatment.

No false positives on verified-final seasons (Alabama 2015, 2020, etc.). Confirmed via DOM assertion across all 11 profiled programs.

### 2. Era ribbon — SHIPPED

`viewBox` expanded to `0 0 640 210`. New profile field `coaching_regimes: [{coach, start_year, end_year}]` added to all 11 original profiles. `_render_era_ribbon()` draws colored bands at 28% opacity (40% for the current-era band to emphasize direction) with 9px uppercase coach-name labels at each band's leftmost 4px. Accent-colored bands anchor to brand.

Examples:
- Alabama: Saban band 2014–2023 + DeBoer band 2024– (brighter)
- ND: Kelly band 2014–2021 + Freeman band 2022–
- Michigan: Hoke/Harbaugh/Moore three bands
- Oregon: Helfrich / Taggart / Cristobal / Lanning four bands

### 3. Year labels — SHIPPED

`'14 '16 '18 '20 '22 '24 NOW` at y=205 in `.arc-chart__xlabel` (muted grey 10px Medium). Rightmost label `NOW` in `.arc-chart__xlabel--now` (accent-primary 10px Semi Bold, letter-spacing 0.08em).

### 4. Key annotations — SHIPPED

New profile field `era_annotations: [{x_year, y_source, label, color}]`. Renderer: `_render_era_annotations()` positions labels near the anchor metric (quality polyline or AP lane), staggers above/below based on y, draws dashed leader line in annotation color, renders text in serif italic 10px.

Editorial content authored inline for all 11 programs, 3–4 annotations each (42 total annotations across the 11 arcs). Examples:

- **Alabama:** "Title #4 of the Process" (2015), "13-0 · Title #6" (2020), "Lost title to Georgia" (2021), "First miss since 2007" (2024)
- **Notre Dame:** "The 4-8 bottom" (2016), "Cotton Bowl semi loss" (2018), "Title game, at last" (2024)
- **Michigan:** "5-7 · Hoke's last year" (2014), "First CFP · Ohio State finally" (2021), "15-0 · Title #12" (2023)
- **Vanderbilt:** "3-9 · Mason year one" (2014), "COVID 0-9 · Mason out" (2020), "Shedeur-beater · 7-6" (2024), "10-win breakthrough" (2025)

### 5. CFP vertical markers — SHIPPED

Markers now extend full chart height (y_top − 2 to y_bottom) with a top gold dot + 9px "CFP" eyebrow 8px above the dot. Title-winning seasons keep the ★ label inside the chart at y_top + 10; title-game seasons keep the ☆. Non-title CFP seasons render with just the dot + CFP eyebrow.

### 6. AP polyline coverage — PARTIAL (data-layer augmented)

The DB's `official_rankings` table only holds AP Top 25 rows for 2020 + 2022–2025. Sprint 4 added a hand-annotated `FINAL_AP_HISTORY` map in [season_arc_loader.py](src/cfb_rankings/team_pages/season_arc_loader.py) that fills 2014–2019 + 2021 for the 11 profiled programs (66 data points). The loader's `_fetch_final_ap()` now prefers DB and falls back to the map. Alabama's AP polyline now has 11 points (up from 4); Notre Dame 8 (up from 3); Georgia, Ohio State, Michigan, Oregon each gain 5–7 points.

**Known gap:** This is not true polyline coverage for unprofiled programs. A nightly re-ingest of the AP historical poll is the follow-up — flagged as Sprint 5 item.

---

## Phase 2 — HistoricalSeasonDeepDive

### Schema

New migration: [migrations/20260424_09_team_historical_seasons.sql](migrations/20260424_09_team_historical_seasons.sql). One row per (team_slug, season_year):

| Column | Purpose |
|---|---|
| `team_slug` | Natural key (survives CFBD team_id rotations) |
| `season_year` | 2014+ CFP-era seasons |
| `season_title` | Evocative editorial phrase ("The Pandemic Crown") |
| `season_thesis` | 1–2 sentence season framing |
| `defining_moments_json` | JSON array of 3 `{type, register, body}` |
| `pull_quote_json` | JSON `{text, source, date, is_generated}` |
| `legacy_paragraph` | "What it meant" closing |
| `gap_year_flag` | 1 when per-game data unavailable (2017/2018 Alabama) |
| `model_id` | `authored-inline` / `template-fallback` / `claude-opus-4-7` |

174 rows written: 19 authored + 155 template-fallback.

### Renderer

New file: [src/cfb_rankings/team_pages/historical_season_page.py](src/cfb_rankings/team_pages/historical_season_page.py) — 8-section layout per spec:

1. Archive nav (top) — prev/next season + chapter N of M + back-to-team
2. Serif title + italic thesis
3. 5-col meta strip — record · final result · AP final · SP+ · era
4. "The shape of the season" SVG — game-result cards (38–42px wide, color-coded W/L/T, opponent abbreviation + score + CFP badge) + cumulative W–L polyline below
5. Defining moments — 3 cards (navy turning-point / amber triumph / red crash / grey shift)
6. Pull quote — blockquote + attribution (with `synthesized` badge when `is_generated=true`)
7. Legacy paragraph
8. Archive nav (footer) — mirror

Output path: `output/site/teams/<slug>/seasons/<year>.html`. Links from Season Arc bricks resolve directly (the brick `href` already points there from Sprint 3).

CSS: [src/cfb_rankings/team_pages/assets/historical_season.css](src/cfb_rankings/team_pages/assets/historical_season.css) — tokens-driven, responsive 3-col moments grid collapsing to 1-col at 640px, 5-col meta collapsing to 2-col, serif display type, navy/amber/red register borders on moment cards.

### Gap-year variant

When the arc row exists but `games` is empty (Alabama 2017/2018), the renderer substitutes the shape SVG with a dashed-stripe placeholder:

> *"This chapter is preserved from canonical CFP record; per-game data is unavailable in the current ingest. The title, the outcome, and the coaching regime are load-bearing; the weekly arc is not reconstructable."*

Header + 5-col meta + moments + quote + legacy all render normally. Confirmed on Alabama 2017 (Title #5 · Overtime in Atlanta) and 2018 (Clemson, Again) — both gap-year variants rendering with full editorial content, just no game grid.

### Content generator

Two paths, one CLI:

**`manage.py generate-historical-seasons`** — precedence order:
1. `AUTHORED_SEASONS` dict in [historical_season_authored.py](src/cfb_rankings/team_pages/historical_season_authored.py) — hand-authored flagship content.
2. `build_template_season()` in [historical_season_content.py](src/cfb_rankings/team_pages/historical_season_content.py) — deterministic fallback from profile voice + arc row + games log.
3. (Future) Opus-authored via LLM subprocess — the hook is in place; the API call is stubbed.

**`--force-template`** flag skips authored content for re-generation testing.

### Flagship authored seasons (19)

Hand-authored inline in this session, voice-calibrated per program:

| Program | Authored |
|---|---|
| **Alabama** | 2014 · 2015 · 2016 · 2017 · 2018 · 2019 · 2020 · 2021 · 2022 · 2023 · 2024 (11 of 12 — 2025 is current) |
| **Notre Dame** | 2016 · 2018 · 2020 · 2024 |
| **Ohio State** | 2014 · 2024 |
| **Vanderbilt** | 2020 · 2025 |

These exercise the renderer across its variants: title-era (Alabama 2015/2020), title-game (ND 2024), gap-year (Alabama 2017/2018), CFP semifinal loss (ND 2020), crisis (ND 2016 / Vandy 2020), current-season template (Vandy 2025), career bookend (Alabama 2023 Saban retirement), DeBoer transition (Alabama 2024).

### Voice-of-quality cross-check

Three paragraphs back-to-back from three tonally-distinct seasons:

**Alabama 2020 (dynastic-process, triumphant):**
> *"2020 is the Process era's statistical peak. A 13-0 season, a Heisman wide receiver, the best scoring offense in Alabama history, and a title game won by 28. The chapter's legacy inside Alabama: this team is the one the next ten rosters will be measured against. The chapter's legacy outside: the pandemic did not level the field; it exposed which programs had the infrastructure to execute through chaos. Alabama had the infrastructure. The title was not a COVID-year asterisk; it was a structural advantage made visible."*

**Notre Dame 2016 (dynastic-with-question-mark, at the bottom):**
> *"2016 is Notre Dame's modern-era bottom — a 4-8 season under a coach who had produced double-digit wins three of the previous four years. The chapter's legacy is not the record; it is the response. The Elko/Long hiring cycle, the schematic overhaul, and the 10-3 2017 Citrus Bowl season all flow from this year's end. In Notre Dame's long-arc voice, 2016 is not a season the program asks anyone to forget; it is a season the program used to argue against complacency in every subsequent year."*

**Vanderbilt 2025 (scrappy-proud, breakthrough):**
> *"2025 is the chapter the Vanderbilt fanbase has been writing drafts of since 2013. A ten-win year, a ranked finish, an SEC record that fills its own column. The chapter's legacy is not pretending to be something the program is not — it is not arguing for title contention. It is arguing for a place inside the SEC's middle tier where the program's academic filter and constrained recruiting footprint are not liabilities, they are the structural choices the program makes on purpose."*

These land in distinct registers: Alabama's voice is institutional-confident, Notre Dame's is retrospective-earnest about the bottom, Vanderbilt's is proud-calibrated. The register does not collapse across programs — that was the measurement.

### Build integration

`render_all_profiled_pages()` in [renderer.py](src/cfb_rankings/team_pages/renderer.py) now calls `render_all_historical_seasons()` after the 17 profile pages, so `build-site` picks up all 174 archive pages without additional wiring. One call wrote 174 pages; per-row errors are logged but don't fail the build.

---

## Phase 3 — 6 new Tier-1 rival profiles

All six shipped with full YAML frontmatter + 12-section markdown body + coaching_regimes + era_annotations:

| Slug | team_id | Register | Tier | Identity phrase |
|---|---|---|---|---|
| `auburn` | 140 | defiant-underdog-with-teeth | 2 | "Auburn is the program the SEC West cannot schedule around." |
| `tennessee` | 151 | restoration-era-orange | 2 | "Tennessee is a program that remembers what it was and is writing the sequel." |
| `florida` | 294 | fallen-dynasty-rebuilding | 2 | "Florida is a program that has held the crown twice and knows the weight of it." |
| `oklahoma` | 280 | crown-program-in-transition | 1 | "Oklahoma is a crown program crossing leagues and still carrying the crown." |
| `washington` | 365 | edge-case-contender | 2 | "Washington is the Pacific Northwest's argument that contender altitude is a choice, not a geography." |
| `uconn` | 209 | basketball-school-with-football | 5 | "UConn is a basketball school that is deciding, in public, what its football chapter will be." |

### Dual-panel rivalry cards flipped

All 6 previously-single-sided Rivalry modules now render full dual-panel with distinct opponent voice:

| Program | Opponent | Opponent posture | Opponent voice excerpt |
|---|---|---|---|
| Alabama | **Auburn** | `defiant · state-claimant` | "The ledger favors them. The state is still ours half the time..." |
| Oregon | **Washington** | `steady · neighborly` | "The Apple Cup got a new conference and so did this one..." |
| Texas | **Oklahoma** | `crown-bearing · relocated` | "The Golden Hat belongs to whoever wins it on the second Saturday..." |
| Massachusetts | **UConn** | `quiet · dual-identity` | "Both teams are Huskies. One of us is named for the other's cousin..." |
| Georgia | **Florida** | `proud · rebuilding` | "Jacksonville is still Jacksonville. The Okefenokee argument is older..." |
| Vanderbilt | **Tennessee** | `dominant · annoyed` | "In-state means we always show up. The ledger says so." |

Written via [scripts/sprint4_rivalry_opposite_posture.py](scripts/sprint4_rivalry_opposite_posture.py) — 6 posture + 6 stakes + 6 quotes written to `team_chronicle_observations` and `team_season_narratives`.

### Voice-differentiation spot-check

Per the sprint's tonal-drift check:

- **Auburn (defiant-underdog-with-teeth)** reads genuinely different from Alabama (dynastic-process). Auburn's voice carries the edged-underdog-with-claim register; Alabama's carries the institutional-confident-standard register. The divergence is visible in the identity phrase and the mascot-voice strings.
- **Tennessee (restoration-era-orange)** reads different from Florida (fallen-dynasty-rebuilding). Tennessee's voice is rebuild-proud — actively writing the sequel. Florida's voice is crown-held-twice — practically honest about where the peaks were.
- **UConn (basketball-school-with-football)** reads different from UMass (scrappy-proud-at-small-scale). UConn leans into the basketball-first institutional identity as feature, not apology; UMass leans into the structural-outsider-working-uphill identity as honest-not-romanticized.

No voice-drift concerns on any of the six. None of the six reads like it was pattern-matched off the Alabama/Notre-Dame templates.

---

## Files touched

### New
| File | Role |
|---|---|
| [migrations/20260424_09_team_historical_seasons.sql](migrations/20260424_09_team_historical_seasons.sql) | Schema |
| [src/cfb_rankings/team_pages/historical_season_page.py](src/cfb_rankings/team_pages/historical_season_page.py) | 8-section page renderer + gap-year variant |
| [src/cfb_rankings/team_pages/historical_season_content.py](src/cfb_rankings/team_pages/historical_season_content.py) | Deterministic template fallback generator |
| [src/cfb_rankings/team_pages/historical_season_authored.py](src/cfb_rankings/team_pages/historical_season_authored.py) | 19 flagship authored seasons (AUTHORED_SEASONS) |
| [src/cfb_rankings/team_pages/historical_season_generator.py](src/cfb_rankings/team_pages/historical_season_generator.py) | Upsert + precedence logic |
| [src/cfb_rankings/team_pages/assets/historical_season.css](src/cfb_rankings/team_pages/assets/historical_season.css) | Season-chapter CSS |
| [profiles/auburn.md](profiles/auburn.md) | Full profile |
| [profiles/tennessee.md](profiles/tennessee.md) | Full profile |
| [profiles/florida.md](profiles/florida.md) | Full profile |
| [profiles/oklahoma.md](profiles/oklahoma.md) | Full profile |
| [profiles/washington.md](profiles/washington.md) | Full profile |
| [profiles/uconn.md](profiles/uconn.md) | Full profile |
| [scripts/sprint4_rivalry_opposite_posture.py](scripts/sprint4_rivalry_opposite_posture.py) | Opposite-side posture content for 6 new pairs |

### Modified
| File | Change |
|---|---|
| [src/cfb_rankings/team_pages/season_arc_loader.py](src/cfb_rankings/team_pages/season_arc_loader.py) | FINAL_AP_HISTORY map; partial-data detection; notes_json persists is_partial |
| [src/cfb_rankings/team_pages/season_arc_card.py](src/cfb_rankings/team_pages/season_arc_card.py) | viewBox 210; era ribbon; annotations; full-height CFP markers; NOW label; is_partial read |
| [src/cfb_rankings/team_pages/assets/season_arc_card.css](src/cfb_rankings/team_pages/assets/season_arc_card.css) | Ribbon band / label / annotation / CFP dot / NOW label / partial-data + is-partial brick modifier |
| [src/cfb_rankings/team_pages/data.py](src/cfb_rankings/team_pages/data.py) | fetch_season_arc returns notes_json |
| [src/cfb_rankings/team_pages/renderer.py](src/cfb_rankings/team_pages/renderer.py) | render_all_profiled_pages also calls render_all_historical_seasons |
| [src/cfb_rankings/cli.py](src/cfb_rankings/cli.py) | generate-historical-seasons + render-historical-seasons subcommands |
| All 11 original [profiles/*.md](profiles) | Added coaching_regimes + era_annotations fields |

---

## DB footprint added by Sprint 4

```
team_historical_seasons:       174 rows  (19 authored + 155 template)
team_chronicle_observations:   +12 rows  (6 opposite posture + 6 opposite stakes)
team_season_narratives:        +6 rows   (rivalry_quote_* for new opponents)
team_profiles / team_voice:    +6 each   (6 new profiles)
team_season_arc:               +59 rows  (6 new programs × ~10 seasons)
team_rivalry_meetings:         +33 rows  (Alabama-Auburn, Georgia-Florida, etc.)
```

Cumulative DB footprint across sprints 1–4:

- `team_profiles`: **17**
- `team_voice`: **17**
- `team_season_narratives`: **~60**
- `team_chronicle_observations` (published): **~90**
- `team_savant_weekly`: 143
- `team_rivalry_meetings`: **114**
- `team_season_arc`: **174**
- `team_historical_seasons`: **174** ← new

---

## Filesystem output

```
output/site/teams/<slug>.html              × 17 profiled (+6 new since Sprint 3)
output/site/teams/<slug>/seasons/*.html    × 174 historical-season pages (all new)
output/site/teams/*.html                   669 legacy pages (unchanged)
```

All historical-season routes resolve 200 from the preview server; navigation prev/next chains walk cleanly.

---

## Token usage by phase + model

All generation happened inline in the Opus 4.7 session — no subprocess LLM calls invoked. The `output/_logs/llm_usage_{date}.jsonl` logger remains empty; the wired path is tested and ready for the Opus-backed fan-out.

Approximate inline-author load by phase:

| Phase | Work | Approximate output volume |
|---|---|---|
| Phase 1 | 6 polish items · 42 annotations · 3 CSS/code files touched | ~1.5k editorial + code |
| Phase 3 | 6 full profiles × (YAML + 12 sections) | ~14k words editorial |
| Phase 2 (authored) | 19 flagship seasons × (title + thesis + 3 moments + quote + legacy) | ~12k words editorial |
| Phase 2 (infra) | Schema + renderer + generator + CLI + CSS | ~1.2k code |
| Phase 2 (template) | 155 deterministic rows from profile/arc/games inputs | 0 tokens (generated) |
| **Total inline editorial** | | **~28k words** |

Model breakdown: all work was Opus 4.7 inline. No Sonnet or Haiku subagent calls this sprint (the Haiku bulk-sweep path was not exercised; profile edits were fast enough to author directly).

---

## Known limits / Sprint 5 candidates

1. **Opus graduation for 155 template-fallback seasons.** The template path produces defensible but tonally-flat content. An Opus pass over all non-authored (slug, year) pairs — via the `generate-historical-seasons` subcommand with an `--llm opus` switch — is the natural next step. The schema, renderer, and CLI are ready; only the Anthropic-SDK call needs wiring.
2. **AP poll pre-2020 ingest.** FINAL_AP_HISTORY fills 66 points by hand for the 11 profiled programs. A nightly ingest of the AP final poll for 2014–2019 + 2021 into `official_rankings` would let the loader derive it and would cover unprofiled programs as well.
3. **Historical season pages for unprofiled programs.** The renderer works off the arc-rows table keyed by team_id; pulling in all ~130 FBS programs would require arc + historical-seasons rows for each. Scope call: is the CFP-era-archive feature scoped to profiled programs only, or broader?
4. **Backfill 2017-2018 Alabama/Georgia/etc. game rows.** Eliminates the gap-year variant entirely and reconnects the trajectory polyline.
5. **`team_profiles` + `team_voice` upsert for the 6 new programs.** Already done this session. Next: run `generate-narratives` for them so their hero state-of-team paragraphs aren't mascot-voice fallbacks.
6. **Savant / Chronicle / state-of-team content for the 6 new programs.** The team pages render, but the modules beyond rivalry are content-sparse. This is the natural fanout for Sprint 5 Phase 1.
7. **Pull-quote sourcing.** Template-fallback quotes are marked `is_generated=True` and attributed to "fanbase voice." Real contemporaneous-source retrieval (e.g., via an archive lookup) would reduce the synthesized-quote count from 155 to a much smaller number.

---

## Natural Sprint 5

1. **Run `generate-narratives` + `generate-chronicle` for the 6 new profiles** to fill out Pulse / state-of-team / chronicle cards beyond the shared-rivalry flip. Pure content fan-out, no code.
2. **Opus pass over the 155 template-fallback historical seasons.** One-time editorial load via the `generate-historical-seasons` CLI; the Anthropic SDK call path needs finishing (template mode runs today, LLM mode is the one-week task).
3. **Backfill 2017-2018 Alabama + Georgia + other pre-2020 games.** Either re-ingest via CFBD or fold in a historical dump; eliminates the gap-year variant and widens the Alabama/Georgia era trajectory resolution.
4. **Add player-page historical tabs** — the same chapter-by-chapter archive pattern lifts naturally into player careers (Derrick Henry 2015, DeVonta Smith 2020, etc.). Sprint 4's infrastructure is reusable.
5. **Build-site integration for the 6 new programs.** Confirm `publish_site.ps1` picks up the new profiles correctly under the legacy-team-page delete sweep; smoke-test on a staging run before a full production publish.
