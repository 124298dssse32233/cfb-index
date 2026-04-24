# Claude Code — Team Page Sprint 4

Paste this whole document into a fresh Claude Code session. Execute autonomously. Sonnet for code and editorial, Haiku for bulk grep/rename sweeps. Target token budget: ~180k.

---

## Context

Sprints 1–3 are shipped. 11 profiled programs render the full world-class stack (hero + Pulse + Chronicle + Savant + Rivalry + Season Arc). `PROFILED_SLUGS` guard in `reporting.py` prevents `build-site` from clobbering. Canonical `CFP_HISTORY` map preserves 2017–2018 title years across DB gaps.

Sprint 4 does three things: polish the shipped Season Arc, build `HistoricalSeasonDeepDive` (per-season archive pages), and expand profile coverage so the 6 single-sided Rivalry cards flip to dual-panel.

---

## Context documents — read these first

1. `TEAM_PAGE_SPRINT_3_REPORT.md` — where you just landed
2. `docs/design-system/13-modules-archive.md` — **updated this session** with polish spec for Season Arc + existing HistoricalSeasonDeepDive spec
3. `profiles/` — existing 11 program profile files as the format reference
4. `src/cfb_rankings/team_pages/season_arc_loader.py` + `season_arc_card.py` — what you shipped in sprint 3; polish happens here
5. `migrations/20260424_08_team_season_arc.sql` — for any new columns needed
6. `CLAUDE.md` — **don't touch `reporting.py`** (especially after the `PROFILED_SLUGS` guard)

---

## Phase 1 — Season Arc polish (shipped module, visible drift)

Audit ran against the rendered `output/site/teams/alabama.html`. Six issues to fix. Spec updates are in `13-modules-archive.md` §chart-polish-requirements.

1. **Partial-data brick state.** Alabama '16 renders "8-0" and '19 renders "6-0" — those are incomplete DB snapshots leaking as if final records. Add `season-brick--partial-data` state (dimmed record color + italic `(partial)` suffix, or just dim the record and drop the misleading value in favor of "—"). Loader detects by comparing `games_played` to expected games for that year/era. Gap-year '17 '18 currently render "—" correctly; don't break that.

2. **Era ribbon.** Bump chart `viewBox` from `0 0 640 180` to `0 0 640 210`. Render coach-regime ribbon at y=186–200. Each band: colored rect at 28% opacity + 9px Semi Bold uppercase coach-name label at the band's leftmost 8px. Pull regime boundaries from a new profile field `coaching_regimes: [{coach, start_year, end_year}]` — add that field to all 11 existing profiles (Haiku can do this in bulk; each profile needs 1–2 regimes in the CFP era).

3. **Year labels.** Render `'14 '16 '18 '20 '22 '24 NOW` at y=205. `'14…'24` in `--fg-subtle` 10px Medium. `NOW` in `--accent-primary` 10px Semi Bold + letter-spacing 1.

4. **Key annotations.** Add 2–4 per arc. Extend profile schema with `era_annotations: [{x_year: int, y_source: "mood"|"ap", label: str, color: "red"|"amber"|"gold"|"navy"}]`. For each program, Opus writes annotations (high editorial judgment — this is arc storytelling). Examples: Alabama '16 "The Kick Six year after" (no — that's '13, pre-era) — actual Alabama annotations should reference '15 title, '20 title, '21 Heisman / loss to Georgia, '23 SEC champ → CFP miss. ND: '16 "The 4-8 bottom", '18 "Cotton Bowl humbling", '24 "Title game at last". Keep to 3 per program for v1.1.

5. **CFP vertical markers.** Already render as gold dots at top — extend them to full chart height as 1px amber verticals with the "CFP" 9px label 18px above the dot. This reinforces era shape.

6. **AP polyline coverage.** Currently Alabama's AP polyline has 4 points (lines 1997–2003 in rendered HTML). It should include every season with a final AP rank, not just recent. Check the data pipeline — likely querying only a narrow window. Expand to full era. If a season lacks AP data, split into two polylines at the gap (already the pattern for quality-score polyline).

### Self-verification for Phase 1
- Render Alabama and ND arcs. Open in browser. Confirm: ribbon visible at bottom, year labels readable, annotations in serif italic, NOW marker in gold, CFP markers full-height, AP polyline spans every ranked season.
- For all 11 programs, confirm `season-brick--partial-data` doesn't activate for any verified-final season (no false positives on Alabama '15, '20 etc.).

---

## Phase 2 — HistoricalSeasonDeepDive

Spec: `docs/design-system/13-modules-archive.md` §HistoricalSeasonDeepDive (existing, unchanged).

Figma mockup (design-of-record): Alabama 2020, node `Alabama · 2020 · Historical Season` on Cover page of Figma file `eGIVOKDIFSmo1yM1LShLQx`. Built this session.

1. **Schema.** New table `team_historical_seasons` with: `team_slug`, `year`, `season_title` (LLM-generated editorial phrase), `season_thesis` (1–2 sentences), `defining_moments` (JSONB: array of `{type, register, body}`), `pull_quote` (JSONB: `{text, source, date}`), `legacy_paragraph` (LLM-generated). One row per team-year, 12 rows per profiled program (132 rows across the 11). Migration `migrations/20260424_NN_historical_seasons.sql`.

2. **Rendering.** New file `src/cfb_rankings/team_pages/historical_season_page.py`. Output path: `output/site/teams/<slug>/seasons/<year>.html`. Links from Season Arc bricks already point here (see rendered HTML line 2021 for reference).

3. **Template.** Use Jinja if the existing renderer uses Jinja; otherwise match whatever pattern `season_arc_card.py` uses. Full 8-section structure per spec: archive-nav → title+thesis → 5-col meta → shape-of-season SVG → defining moments (3 cards) → pull quote → legacy paragraph → footer-nav.

4. **Shape-of-season SVG** (620×150): game result cards left-to-right + mood curve below. 12 game cards. Each card: 38px wide, color-coded W/L + rank-of-opponent chip. Mood curve drawn as polyline y=100–140. Defining-moment callouts attached to specific games.

5. **Gap-year handling.** For 2017/2018 on Alabama and any other `--data-gap` seasons, render a simplified variant: show what's canonical (record from `CFP_HISTORY`, title outcome, coach), render the header + meta strip + pull quote (if an archival one exists) + legacy paragraph, and replace shape-of-season SVG with a "this chapter is preserved from canonical record; per-game data unavailable" placeholder. Do NOT fail the page.

6. **Content generation.** `manage.py generate-historical-seasons` subcommand.
   - Opus for `season_title` + `season_thesis` + `legacy_paragraph` (these are editorial load-bearing, one-time-per-season). Reuse voice from `profiles/<slug>.md`.
   - Sonnet for `defining_moments` cards (3 per season).
   - Pull quotes: try to find a contemporaneous quote first (prompt Opus to recall one from the program's coverage that year — Alabama 2020 has plenty of them); if none available, fallback to an LLM-generated quote attributed to a placeholder like "contemporaneous coverage" — mark with `_generated: true` so we know it's not a verified source. Prefer real over generated.
   - Total LLM load: ~132 seasons × 4 Opus fields ≈ medium. Budget accordingly.

7. **Cross-link from Season Arc.** Already happening in sprint 3 (bricks render as `<a href="/teams/<slug>/seasons/<year>.html">`). Confirm all links resolve to a rendered page after this phase.

### Self-verification for Phase 2
- Render Alabama 2020 historical season. Visual check against Figma mockup. The 2020 season should feel like a chapter in a book, not a stat page.
- Render Alabama 2017 (gap-year variant). Should gracefully show canonical title info + a note about data availability. No Jinja errors, no blank sections.
- Render ND 2024 (the "Title game at last" season). Voice should be Notre-Dame-inflected.
- Render one crisis-state season (ND 2016 4-8, or similar). Register should shift to red/melancholic.
- All 132 season pages build without template errors.

---

## Phase 3 — Expand profile coverage (6 new Tier-1 rival profiles)

Currently 11 profiled programs → 6 of their rivalry cards render single-sided because the opponent isn't profiled. Adding these 6 flips those cards to full dual-panel.

Programs to profile (all Tier-1 or -2):
- **Auburn** — Alabama's rival. Voice: defiant-underdog, cow-bell energy, "Iron Bowl" identity.
- **Tennessee** — Alabama + Georgia rival. Voice: restoration-era (Heupel), "Rocky Top" iconography.
- **Florida** — Georgia + Tennessee rival. Voice: fallen-dynasty-rebuilding, Spurrier ghost.
- **Oklahoma** — Texas rival, now SEC. Voice: Big-8-to-SEC reinvention, Stoops-then-Venables era.
- **Washington** — Oregon rival, 2023 CFP runners-up, DeBoer-to-Fisch transition. Voice: edge-case-contender.
- **UConn** — UMass rival (both FBS-independents). Voice: just-found-itself, basketball-school-with-football.

Each profile follows the existing format: YAML frontmatter with ~15 structured fields + 12 markdown sections. Read `profiles/notre-dame.md` as the reference; keep the same structure. Opus for voice & ethos + identity phrase + mantra + mascot voice (the editorial heart). Sonnet for rivalries + aspiration ladder + heritage data + chronicle tuning.

After profiles land, regenerate affected rivalry cards so they render dual-panel. Test: Auburn should show in Alabama's Rivalry module as a full-opposing panel with Auburn's posture + last meeting + trajectory chart on both sides, not just a one-sided "vs. Auburn" summary.

### Self-verification for Phase 3
- Six new profile files exist, each with full 15-field YAML + 12 markdown sections.
- The 6 previously single-sided Rivalry cards on profiled programs now render dual-panel.
- Spot-check voice tonally: Auburn's voice should read different from Alabama's (defiant-underdog vs. crown). Tennessee should read different from Florida (restoration vs. fallen-dynasty). UConn should read different from UMass (basketball-school-with-football vs. scrappy-proud).

---

## Decision authority (act autonomously)

- Schema column types, migration naming
- LLM routing exceptions (if Haiku handles a task Sonnet was scoped for, note it in report)
- Visual polish details not explicitly specced (annotation positioning fine-tuning, ribbon opacity tweaks)
- Handling of unusual historical data (coaching mid-season changes, vacated wins, etc.) — log the choice and move on
- Quote sourcing — prefer real; if generated, flag

**Stop and flag only if:**
- `CFP_HISTORY` map needs a change you're not confident about (ask Kevin)
- Voice-register drift is severe on one of the 6 new profiles (ask Kevin to review before fanning out)
- Token budget approaches 300k (pause, report)

---

## Report back with

1. Phase 1 polish — confirmation each of 6 items shipped + screenshot of Alabama arc before/after.
2. Phase 2 — screenshot of Alabama 2020, Alabama 2017 (gap-year variant), ND 2024, and one crisis-era season. Quality-of-voice assessment (3 paragraphs back-to-back from three tonally-distinct seasons).
3. Phase 3 — confirmation of 6 profile files + 6 dual-panel rivalry cards. Note any voice-drift concerns.
4. Token usage by phase + model.
5. Natural sprint 5.

Report at end, not between phases. Good luck.
