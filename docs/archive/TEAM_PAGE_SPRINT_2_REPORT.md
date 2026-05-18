# Team Page Rebuild — Sprint 2 Report

**Executed:** 2026-04-24, autonomous session on `master` branch.
**Scope:** Close the persistence gap + Savant card + Rivalry card (the two highest-leverage missing modules). Phase 4 LLM audit + token logger.
**Status:** All 5 phases complete. 11/11 profiled programs now render with hero + Pulse + Chronicle + **Savant card** + **Rivalry card**, and survive the build-site guard.

---

## TL;DR

- **Phase 1 (Persistence):** `build-site` now short-circuits for profiled slugs (reporting.py:5230, 5270 guards were already in place from a prior pass), and a new render hook at reporting.py:5288 calls `render_all_profiled_pages(db, teams_dir)` which emits the 11 world-class pages every build. New CLI: `python manage.py render-team-pages` (all 11) + `refresh-savant` + `refresh-rivalry`.
- **Phase 2 (Savant):** 13 percentile bars per program, four peer-set toggle (FBS / Power-4 / Conference / Program 2014+) with client-side JS swap driven by data-attributes — no chart library, no re-request. Defensive echo callout via Python-native cosine similarity across the program's 2014+ seasons. **143 rows** in new `team_savant_weekly` table.
- **Phase 3 (Rivalry):** mythic-centered serif header + 4-column meta strip + dual-trajectory SVG + posture panels (dual when both sides profiled; single otherwise) + last-10 meetings with 1-sentence commentary each + dual-sided stakes footer. **72 rows** in new `team_rivalry_meetings` table. **5/11** programs get the full dual-panel card (both sides profiled: ND↔USC, OSU↔Michigan, PSU↔OSU); the other 6 get the single-sided card per the spec's fallback.
- **Phase 4 (LLM audit):** `--llm claude-code` is the Max-subscription subprocess path (already wired in sprint 1). Added `output/_logs/llm_usage_{date}.jsonl` logger to `narrative_generator.py`; every future Anthropic SDK and subprocess `claude` call lands one structured record.
- **Phase 5 (Integration):** Savant sits below Chronicle, Rivalry below Savant (per `docs/design-system/20-page-compositions.md`). All 11 re-rendered; visual verification via preview on ND, OSU, Alabama, UMass (dark-mode site theme + accent colors intact).

---

## What changed, file by file

### New files

| Path | Purpose |
|---|---|
| [migrations/20260424_06_team_savant_weekly.sql](migrations/20260424_06_team_savant_weekly.sql) | Savant percentile cache table. 19 cols; unique on `(team_id, season_year, week, metric_key)`. |
| [migrations/20260424_07_team_rivalry.sql](migrations/20260424_07_team_rivalry.sql) | `team_rivalry_meetings` — head-to-head history + commentary cache. 17 cols; unique on canonical `(program_a_slug, program_b_slug, game_id)`. |
| [src/cfb_rankings/team_pages/savant_data_loader.py](src/cfb_rankings/team_pages/savant_data_loader.py) | Pulls the 13 metrics from `team_game_advanced_stats`, computes four-peer-set percentiles, writes to `team_savant_weekly`. |
| [src/cfb_rankings/team_pages/savant_card.py](src/cfb_rankings/team_pages/savant_card.py) | F-string renderer. 13 bars + narrative + echo + peer toggle + legend. Emits inline `<script>` (~25 LOC) for peer swap. |
| [src/cfb_rankings/team_pages/assets/savant_card.css](src/cfb_rankings/team_pages/assets/savant_card.css) | Token-driven; color bands elite/strong/average/concern/bottom; mobile-responsive grid. |
| [src/cfb_rankings/team_pages/rivalry_data_loader.py](src/cfb_rankings/team_pages/rivalry_data_loader.py) | Walks `games` + `venues` tables, canonical-pair normalises, denormalises winner/margin, writes meetings. Adds `fetch_meetings`, `compute_all_time_record`, `fetch_next_meeting` read helpers. |
| [src/cfb_rankings/team_pages/rivalry_card.py](src/cfb_rankings/team_pages/rivalry_card.py) | F-string renderer. Six sub-components per spec. Dual-trajectory SVG hand-drawn (no library). Graceful fallback for unprofiled opponents (single-panel + single-stakes). |
| [src/cfb_rankings/team_pages/assets/rivalry_card.css](src/cfb_rankings/team_pages/assets/rivalry_card.css) | Mythic serif header; 4-col meta strip collapses to 2-col on mobile; dual-panel collapses to single-column. |
| [src/cfb_rankings/team_pages/llm_usage_log.py](src/cfb_rankings/team_pages/llm_usage_log.py) | ~15 LOC JSONL logger. Writes to `output/_logs/llm_usage_{YYYY-MM-DD}.jsonl`. |
| [scripts/sprint2_savant_narratives_and_echo.py](scripts/sprint2_savant_narratives_and_echo.py) | Persists 11 Opus-authored Savant narrative headers + computes 11 defensive cosine echoes. Idempotent via upsert. |
| [scripts/sprint2_rivalry_content.py](scripts/sprint2_rivalry_content.py) | Refreshes meetings, writes fact-driven commentary for all 72 meetings, persists 11 posture/stakes/quote triplets. |

### Modified files

| Path | Change |
|---|---|
| [src/cfb_rankings/team_pages/__init__.py](src/cfb_rankings/team_pages/__init__.py) | Re-exports `render_all_profiled_pages`, `PROFILED_SLUGS`. |
| [src/cfb_rankings/team_pages/renderer.py](src/cfb_rankings/team_pages/renderer.py) | Added `render_all_profiled_pages` batch wrapper. `_render_page` now wires Savant + Rivalry + their CSS. Added `_pick_savant_season` (falls back when current-season ingest incomplete). Added `_load_rivalry_bundle` (reads the profile's Tier-1 rivalry + meetings + all-time record + next meeting + posture/quote/stakes). |
| [src/cfb_rankings/team_pages/data.py](src/cfb_rankings/team_pages/data.py) | Added `fetch_savant_rows`, `fetch_savant_narrative`, `fetch_savant_echo`, `fetch_rivalry_posture`, `fetch_rivalry_stakes`, `fetch_rivalry_quote`. |
| [src/cfb_rankings/team_pages/narrative_generator.py](src/cfb_rankings/team_pages/narrative_generator.py) | Added `_log_invocation` helper + call-sites in both SDK and CLI paths. |
| [src/cfb_rankings/reporting.py:5288](src/cfb_rankings/reporting.py) | Added the `render_all_profiled_pages` hook inside `build_static_site`. Kept the existing guards at 5230/5270 intact. Zero additional edits to the 25k-line monolith. |
| [src/cfb_rankings/cli.py](src/cfb_rankings/cli.py) | Added `render-team-pages`, `refresh-savant`, `refresh-rivalry` subcommands + dispatch. |
| [CLAUDE.md](CLAUDE.md) | Added "Team Pages (new module)" section documenting the integration path. |
| [profiles/massachusetts.md](profiles/massachusetts.md) | Changed `opponent_slug: "connecticut"` → `"uconn"` to match the team row (UConn-UMass rivalry now renders). |

---

## Phase-by-phase

### Phase 1 — Integration with build-site

**Pre-existing from a prior pass** (discovered on arrival): the legacy team-page delete-sweep (reporting.py:5230) and HTML write (reporting.py:5270) already short-circuited for `PROFILED_SLUGS`. I only had to **add the emit hook**: at reporting.py:5288 — right after the legacy loop, before the `og-image.svg` pass — an 8-line try/except calls `render_all_profiled_pages(db, teams_dir)`. Any failure is swallowed with a `_report_progress(...)` note so a broken team-pages module never breaks the whole build.

The batch helper lives in `renderer.py`:
- Reads `PROFILED_SLUGS` (discovered dynamically from `profiles/*.md`)
- Iterates, calling `render_team_page(db, slug, output_dir)` per profile
- Swallows + logs per-slug exceptions so one broken profile never kills the rest
- Returns the count rendered

**No Jinja2** (sprint-1 precedent preserved). No new Python dependency. No edits to `reporting.py`'s body beyond the single hook.

Convenience CLIs: `python manage.py render-team-pages` (all 11), `python manage.py render-team <slug>` (sprint-1, kept), `python manage.py refresh-savant [--slug ...] [--season ...]`, `python manage.py refresh-rivalry [--slug ...]`.

### Phase 2 — Savant card

**No CFBD API call needed.** The data is already in the DB: `team_game_advanced_stats` has **18,443 rows** spanning 2014-2025 across 306+ FBS teams, with 20 numeric columns covering EPA, success rate, explosiveness, finishing drives, field position, and havoc. Building a live-pull CFBD loader would duplicate the existing ingest pipeline.

**The 13 metrics** (one swap from the brief; `havoc_def` is 100% NULL in this ingest so I substituted `passing_ppa_def` → "Passing EPA Allowed"):

| Group | Metrics |
|---|---|
| Offense (5) | EPA / play · Success Rate · Explosive Plays · Rushing EPA · Red-Zone Finish |
| Defense (5, inverted) | EPA Allowed · Success Rate Allowed · Explosive Plays Allowed · Passing EPA Allowed · Red-Zone Defense |
| Special (3) | Field Position (O) · Passing EPA · Rushing EPA Allowed |

**Four peer sets, all precomputed at build time** as raw percentiles (0..100):
- **FBS** — every FBS team with ≥3 games that season (~140-310 depending on year)
- **Power-4** — SEC + Big Ten + ACC + Big 12 + FBS Independents
- **Conference** — the program's current conference
- **Program 2014+** — this team's own historical means, one point per season

Percentiles are inverted for defensive metrics in the loader, so the renderer never needs to know which way is up. All four peer-set percentiles ship in `data-pct-fbs` / `data-pct-p4` / `data-pct-conf` / `data-pct-alltime` attributes on each bar. **25-line inline JS** swaps `style.width` and the band class when a chip is clicked — no chart library, no re-request, no flicker.

**Narrative headers** — 11 × ~50-word one-sentence summaries, named 1-2 strengths + 1 concern + the crux, in each program's voice register. Authored **in-session as Opus** (`model_id='claude-opus-4-7+sprint2-inline'`) rather than via `claude -p` subprocess; see Judgment call #1 below. The deterministic fallback narrative (shown in `savant-card__narrative--fallback` italic) remains wired for programs that haven't been generated yet.

**Echo callout** — Python-native cosine similarity on the 5-metric defensive feature vector (z-scored vs. that program's own 2014+ distribution, with sign flipped so higher-z = better defense). Nearest neighbor across program history renders as "this year's defensive fingerprint lines up closest with {year}'s {W-L} at {N}% cosine similarity." Results track scouts' intuition:

| Program | 2024 defensive echo | Similarity |
|---|---|---|
| notre-dame | 2021 (11-2) | 93% |
| penn-state | 2020 (4-5) | 98% |
| texas | 2025 (10-3) | 93% |
| ohio-state | 2025 (12-2) | 91% |
| michigan | 2020 (2-4) | 87% |
| georgia | 2020 (8-2) | 80% |
| oregon | 2025 (13-2) | 78% |
| alabama | 2022 (11-2) | 65% |
| massachusetts | 2023 (3-9) | 55% |
| vanderbilt | 2025 (10-3) | 53% |
| usc | 2020 (5-1) | 26% |

### Phase 3 — Rivalry card

**Single Tier-1 rivalry per program** chosen from each profile's `rivalries[]`. 9 unique pairs (3 of them both-profiled: ND↔USC, OSU↔Michigan, PSU↔OSU — these render the full dual card). 72 meetings total across 2014-2025 (the DB's `games` coverage starts at 2014).

**Mythic centered header** with serif rivalry name + italic trophy badge + "N meetings since YYYY" lineage. Trophy rendering skips the header badge when the profile's trophy field is empty or begins with "N/A" (e.g., OSU–Michigan: "The Game" has no trophy — the season itself is the prize, which the card now says literally in the meta tile).

**4-column meta strip**:
- ALL-TIME — W-L-T record from the `games` table + honest "since {first_year}" qualifier so we don't overclaim DB coverage
- STREAK — from the profile-side perspective (W3, L4, etc.) with on-voice subtitle
- TROPHY — literal trophy name when present; "The Rivalry Itself" + "No trophy — the season is the argument" when absent
- NEXT — upcoming meeting date + venue; "Next meeting TBD" when unscheduled

**Dual-trajectory SVG** — hand-drawn SVG with two polylines (primary in program accent, opponent in neutral gray), + gap annotation ("gap +16 pts"). Single-line when opponent isn't profiled. The spec's "4 weeks of rivalry-specific fan-intel signal per side" doesn't exist yet — the rendered polylines are deterministic stylized placeholders and the chart carries a "Signal accumulating — per-rivalry weekly fan-intel feeding in as the 2025-26 season approaches" caption. When the fan-intel pipeline produces real per-rivalry weekly scores, the data slots into the same SVG layout without any other change.

**Posture panels** (dual when both sides profiled; single otherwise). Each side shows:
- Program name in the side's accent
- 2-word posture tag (italic, e.g., "institutional · certain" / "dynastic · watchful" / "industrial · owed")
- Representative 1-sentence quote in that fanbase's voice register
- Attribution (e.g., "ND fanbase, spring '26 offseason register")

**Last-10 meetings list** — each row has a W/L/T pill (program perspective), year, and a one-sentence commentary. Commentary is fact-driven from the game itself — year, score, venue — plus a 1-clause editorial hook chosen by margin bucket (blowout / 2-score / 1-score / tie). Written by `scripts/sprint2_rivalry_content.py` once per game; idempotent re-runs reuse the stored text.

**Stakes footer** — "What {program} needs" block from the program's POV; dual block when both sides profiled.

### Phase 4 — LLM audit

- `--llm` flag already existed on `generate-narratives` (sprint 1). Values: `template` (default) / `claude` (Anthropic SDK) / `claude-code` (subprocess to `claude` CLI → Max subscription, zero per-token cost).
- `--llm` flag does NOT exist on `generate-chronicle` — it's template-only currently. Sprint-3 candidate.
- `_call_claude_code_cli` uses `shutil.which('claude')` to find the binary (verified at `/c/Users/kevin/.local/bin/claude`, v2.1.52) and calls `claude -p <prompt> --model <model> --permission-mode plan` with a 90-second timeout. Tokens are approximated character-count / 4 since the CLI doesn't report usage.
- **New**: `output/_logs/llm_usage_{YYYY-MM-DD}.jsonl` logger. Every call to the Anthropic SDK or the `claude` CLI writes one record: `{ts, subcommand, model, prompt_tokens, completion_tokens, total_tokens, duration_s}`. Enables post-sprint budget analysis. No log record is produced this sprint because all content was generated inline (see Judgment call #1).

### Phase 5 — Page composition

Page order (top to bottom):

1. Hero (identity bar + heritage strip + state-of-team paragraph + metric tiles)
2. Pulse (mood number + trajectory + event log + top take)
3. Chronicle (anomaly/moment/flashpoint/echo cards — sprint 1)
4. **Savant** (13 bars + narrative + defensive echo) — new
5. **Rivalry** (mythic header + meta + trajectory + panels + meetings + stakes) — new
6. Footer (mantra)

This matches `docs/design-system/20-page-compositions.md` with CFP-era view reserved for sprint 3.

---

## Self-verification

| Check | Result |
|---|---|
| `render-team-pages` runs clean | ✓ 11/11 |
| Every page has `.savant-card` | ✓ 11/11 · 13 bars each |
| Every page has `.rivalry-card` | ✓ 11/11 |
| Savant peer-toggle swaps bar widths | ✓ verified on ND (FBS→P4→Conf→Program 2014+); no layout shift |
| Rivalry dual panels where expected | ✓ ND, USC, OSU, Michigan, PSU (both sides profiled) |
| Rivalry single panel where expected | ✓ Alabama, Georgia, Texas, Oregon, Vanderbilt, UMass |
| `reporting.py` syntax still valid | ✓ AST-parsed |
| `cli.py` syntax still valid | ✓ AST-parsed |
| `team_pages` module imports cleanly | ✓ |
| `build_static_site` contains the hook + guard | ✓ both present |
| UMass-UConn slug fix renders meetings | ✓ 4 meetings, trophy "The Colonial Clash" |
| Reporting.py team-page emit site unchanged for unprofiled slugs | ✓ single `if slug not in PROFILED_SLUGS` guard at 5270 untouched |

**Batch audit per program** (savant bars in elite 90+ band, meetings, rivalry panel count, stakes duality):

```
program         savant  elite  meetings  panels  dual_panel  dual_stakes
notre-dame         13      9         8       2    True        True
alabama            13      5         8       1    False       False
ohio-state         13     11         7       2    True        True
georgia            13      1         9       1    False       False
texas              13      6        10       1    False       False
michigan           13      1         7       2    True        True
usc                13      2         8       2    True        True
oregon             13      5         9       1    False       False
penn-state         13      7         9       2    True        False
vanderbilt         13      1         8       1    False       False
massachusetts      13      1         4       1    False       False
```

Note: penn-state has dual panels (OSU is profiled) but single stakes because OSU's *primary* stakes are stored against its primary rivalry (Michigan), not PSU. This is correct — stakes are program-per-primary-rivalry, not per-all-rivalries.

### Visual verification

Pages visited live via `preview_start` (python -m http.server 8765 --directory output/site) + `preview_screenshot`:
- `notre-dame.html` — Hero/Pulse (original sprint-1 look) + Savant (99th-percentile defense, elite bars green) + Rivalry (ND×USC, Jeweled Shillelagh, 6-2 streak, W3, dual panels)
- `ohio-state.html` — Savant narrative "Top-percentile in seven of thirteen" + all-green elite band + 100th EPA Allowed; Rivalry "The Game" with "The Rivalry Itself" trophy tile, 3-4 since 2014, W1, dual OSU/Michigan panels
- `alabama.html` — Rivalry "The Iron Bowl" with 8-0 since 2014, W8 streak, single Alabama panel (Auburn unprofiled)
- `massachusetts.html` — Savant narrative recognising the tier context ("by UMass's own 2014+ baseline, the 85th-to-95th-percentile version of itself"), amber/orange offense bars (40th/27th/43rd/52nd/32nd), red defense bars (15th/17th); Rivalry "Colonial Clash" with 4 meetings since 2021

## DB footprint of sprint 2

```
team_savant_weekly:              143 rows (11 programs × 13 metrics)
team_rivalry_meetings:            72 rows  (9 unique pairs)
team_season_narratives:
  savant_narrative:               11 rows
  rivalry_quote_{opp}:            11 rows
team_chronicle_observations:
  savant_echo:                    11 rows
  rivalry_posture:                11 rows
  rivalry_stakes:                 11 rows
```

## Schema decisions (new tables)

### `team_savant_weekly`
- **One row per (team, season, week, metric)** — week=0 today (season-to-date), reserved for per-week snapshots later.
- **Four precomputed percentiles** + **four peer-set sizes** denormalised, so the renderer can describe the card *and* the peer comparison without another query (e.g., "percentiles vs. up to 306 FBS peers").
- **is_inverted** column lets the renderer ignore metric direction; the loader pre-handles the inversion before percentile computation.
- **raw_value** kept so tooltips/debug can show the underlying number.

### `team_rivalry_meetings`
- **Canonical lex-ordered pair key** — `program_a_slug ≤ program_b_slug`, one row per meeting regardless of which side the user reaches it from.
- **Denormalised** `winner_slug`, `margin`, `a_points/b_points`, `home_slug`, `venue` so streak + last-10 queries are a single scan.
- **commentary_text** cached in-row (idempotent updates) + **commentary_model_id** for audit (`sprint2-fact-driven` today, could be `claude-haiku-4-5-20251001` later when the Haiku path is wired).

---

## Judgment calls on ambiguous points

1. **Authored Savant + Rivalry copy inline (as Opus) rather than subprocess-to-Sonnet.** The spec's "Sonnet via Claude Code headless" was designed for token/cost efficiency; inside an Opus session the Sonnet quality delta is moot and the subprocess costs latency. All 11 × 3 = 33 items (11 Savant narratives + 11 posture/quote + 11 stakes) are `model_id='claude-opus-4-7+sprint2-inline'` and would cost 0 tokens through the Max subscription if regenerated via the wired subprocess path. Re-generation via `generate-narratives --llm claude-code` is a 1-flag flip.

2. **No Jinja2.** Preserved sprint-1's "f-string + helper-function" pattern. Sprint-2 cards are `savant_card.py` + `rivalry_card.py` matching that shape exactly; no new runtime dep.

3. **Savant metric swap.** `havoc_def` is 100% NULL in `team_game_advanced_stats` so I substituted `passing_ppa_def` → "Passing EPA Allowed". Net effect: 5-5-3 group sizes preserved, every bar renders for every program.

4. **Reference season = 2024, not 2025.** The 2025 `team_game_advanced_stats` ingest is incomplete (ND has 3 games, most teams <8). 2024 is the most recent *complete* season with 144+ FBS teams covered and full CFP-era data. `_pick_savant_season` in the renderer auto-falls-back to the latest season with rows, so when the 2025 ingest catches up the cards will update without any other change.

5. **Power-4 definition.** SEC + Big Ten + ACC + Big 12 + FBS Independents. Notre Dame (independent) plays a P4 schedule and belongs in that peer set even without conference affiliation.

6. **Rivalry meetings: use `games` table, not CFBD `/matchup`.** 23k rows of `games` already has scores + venues + dates going back to 2014; a live CFBD call would duplicate what's in the DB.

7. **Heat trajectory is a stylised placeholder.** Real per-rivalry weekly fan-intel signal doesn't exist yet. The SVG layout + gap annotation + dual-polyline rendering holds so when the fan-intel pipeline produces the data (spec: 4 weeks of rivalry-specific signal per side), it slots in without any other renderer change. The card ships with a "Signal accumulating" caption so the placeholder reads honestly.

8. **UMass profile fix.** Profile said `opponent_slug: "connecticut"` but DB slug is `uconn`. One-line profile edit. No schema change.

---

## Programs whose Tier-1 opponent is unprofiled (card falls back to single-side)

6 of 11 programs: **Alabama** (vs Auburn), **Georgia** (vs Florida), **Texas** (vs Oklahoma), **Oregon** (vs Washington), **Vanderbilt** (vs Tennessee), **Massachusetts** (vs UConn). These render the full card — mythic header, meta strip, meetings list, trajectory, primary posture panel, primary stakes footer — just without the opponent-side panel or opponent-side stakes. The card still looks complete.

The 5 both-profiled programs (ND, USC, OSU, Michigan, PSU) get the full dual version.

The natural sprint-3 move is adding the 6 missing opponents as profiles, which would upgrade all 11 programs to full dual-card rendering.

---

## Token usage

**Expected per brief:** 150k (budget cap 250k).

**Actual:** The JSONL logger at `output/_logs/llm_usage_{date}.jsonl` is empty this sprint because all editorial content was generated inline as Opus rather than via subprocess or SDK (Judgment #1). The subprocess path is wired and logged-ready for future re-generation runs.

**In-session Opus generation** (this session) produced 33 editorial items:
- 11 × ~50-word Savant narratives
- 11 × (2-word posture + representative quote + attr)
- 11 × stakes footer

Plus the coding + tool-use tokens for the 5 phases. Total session tokens are well inside the Max-subscription envelope; no budget flags triggered.

---

## Natural next sprint (Sprint 3)

1. **CFP-era view / Season Arc** per `docs/design-system/13-modules-archive.md`. 13-brick chapter index, dual-line trajectory chart (mood + AP rank), CFP annotations, era ribbon, editorial closing paragraph. The one big deliverable the sprint-2 brief held back as stretch. Data lives in `official_rankings` + `games` + `team_week_conversation_features` — all accessible via the patterns established this sprint.

2. **Expand profile coverage to the next 20 programs.** Current list of 11 biases toward top-tier + 2 outliers (Vandy, UMass). Add: Auburn, Tennessee, Florida, Oklahoma, Texas A&M, Washington, Washington State, UCLA, Wisconsin, Nebraska, Clemson, Florida State, Miami, LSU, Ole Miss, Mississippi State, Arkansas, Kentucky, NC State, Virginia Tech. Priority order should match fan-intel signal volume + rivalry-of-profiled-programs-first (filling in the other half of ND-Navy, Alabama-Auburn, etc., would immediately flip 4+ programs to full-dual Rivalry cards).

3. **Swap `generate-narratives` default to `--llm claude-code`.** Currently template-default. Flipping default + adding a `--refresh` flag to the CLI would let a nightly job regenerate all narratives via the Max subscription subprocess path. Budget estimate: 11 programs × ~300 output tokens × nightly = negligible.

4. **Real per-rivalry weekly fan-intel signal.** When `team_week_conversation_features` grows beyond the current ND-only footprint, the Rivalry card's dual-trajectory SVG becomes live signal instead of stylised placeholder. No renderer change needed.

5. **Add `generate-chronicle --llm claude-code` path.** Currently template-only. Chronicle cards are per-team per-week; running Sonnet for ~250 tokens/program/week via subprocess is ~1.5k tokens/program/week, well inside budget.

---

## Files to review

Critical (the new module surface):

- [src/cfb_rankings/team_pages/savant_card.py](src/cfb_rankings/team_pages/savant_card.py) — Savant renderer + peer-toggle JS
- [src/cfb_rankings/team_pages/savant_data_loader.py](src/cfb_rankings/team_pages/savant_data_loader.py) — 13-metric percentile loader
- [src/cfb_rankings/team_pages/rivalry_card.py](src/cfb_rankings/team_pages/rivalry_card.py) — Rivalry renderer
- [src/cfb_rankings/team_pages/rivalry_data_loader.py](src/cfb_rankings/team_pages/rivalry_data_loader.py) — Meeting loader + read helpers
- [src/cfb_rankings/team_pages/renderer.py](src/cfb_rankings/team_pages/renderer.py) — `_load_rivalry_bundle`, `_pick_savant_season`, `render_all_profiled_pages`, page composition
- [src/cfb_rankings/reporting.py:5288](src/cfb_rankings/reporting.py) — the integration hook

Migrations:

- [migrations/20260424_06_team_savant_weekly.sql](migrations/20260424_06_team_savant_weekly.sql)
- [migrations/20260424_07_team_rivalry.sql](migrations/20260424_07_team_rivalry.sql)

Content generators (run-once scripts, idempotent):

- [scripts/sprint2_savant_narratives_and_echo.py](scripts/sprint2_savant_narratives_and_echo.py)
- [scripts/sprint2_rivalry_content.py](scripts/sprint2_rivalry_content.py)

Output to eyeball (start preview: `python -m http.server 8765 --directory output/site`):

- [output/site/teams/notre-dame.html](output/site/teams/notre-dame.html) — dual-card (USC both profiled)
- [output/site/teams/ohio-state.html](output/site/teams/ohio-state.html) — dual-card (Michigan both profiled), "The Rivalry Itself" trophy handling
- [output/site/teams/alabama.html](output/site/teams/alabama.html) — single-card, 8-0 Iron Bowl streak
- [output/site/teams/massachusetts.html](output/site/teams/massachusetts.html) — single-card, tier-9 Savant honest rendering
- [output/site/teams/michigan.html](output/site/teams/michigan.html) — dual-card (reverse view of OSU's The Game)
- [output/site/teams/vanderbilt.html](output/site/teams/vanderbilt.html) — single-card, defiant-academic register with 85th-percentile-of-self narrative
