# Claude Code — Team Page Engineering Sprint

Copy-paste this entire document into Claude Code as the sprint kickoff prompt. Claude Code should execute autonomously, make judgment calls without stopping, and report only at the end.

---

## Context documents — read these first

Before any code, read the following files in order:

1. `TEAM_PAGE_WORLD_CLASS_BRIEF.md` (Parts I, II, III — full strategic brief)
2. `TEAM_PAGE_ITERATION_LOG.md` (chronological iteration record)
3. `docs/design-system/00-tokens.md` (design tokens spec)
4. `docs/design-system/01-atoms.md` (atomic components spec)
5. `docs/design-system/10-modules-hero.md` (hero modules spec)
6. `docs/design-system/11-modules-season.md` (season modules spec)
7. `docs/design-system/12-modules-intel.md` (intelligence modules spec)
8. `docs/design-system/13-modules-archive.md` (archive modules spec)
9. `docs/design-system/14-modules-game-recap.md` (game recap mode spec)
10. `docs/design-system/20-page-compositions.md` (page composition spec)
11. `profiles/notre-dame.md` (reference profile; also alabama, ohio-state, georgia, michigan, texas, oregon, usc, penn-state, vanderbilt, massachusetts)
12. `CLAUDE.md` (repo rules — especially don't touch `reporting.py`)

---

## Goal

Ship an end-to-end static-rendering pipeline for Notre Dame's team page using the new design system. Target deliverable: `output/site/teams/notre-dame.html` renders correctly on desktop (1440px) and mobile (390px) breakpoints, driven by real profile data + current-season SQLite data + LLM-generated editorial content.

After ND ships, fan out to Alabama, Ohio State, Georgia, Michigan, Texas, Oregon, USC, Penn State, Vanderbilt, UMass (the 10 programs with complete profiles).

---

## Deliverables

### Phase 1 — Infrastructure (execute first, no external LLM calls yet)

1. **SQLite schema migration** in `migrations/NNN_team_pages_schema.sql`:
   - `team_profiles` (stores YAML frontmatter from profile files as JSONB blob + normalized key fields)
   - `team_season_narratives` (state-of-team paragraphs per team-week + season titles/theses/legacy per historical season)
   - `team_chronicle_observations` (weekly Chronicle cards with card_type enum, content, source, week_stamp)
   - `team_voice` (accent_hex, vocab JSON, mascot templates JSON, era name overrides JSON) — may consolidate with team_profiles
   - `team_aspiration_ladders` (rungs with dynamic odds computed from SP+ + schedule)

   Test: migration runs cleanly on current `cfb_rankings.db`. Back up first. Existing `reporting.py` build still works after migration.

2. **New module scaffold** at `src/cfb_rankings/team_pages/`:
   - `__init__.py`
   - `renderer.py` — top-level `render_team_page(team_slug, state=None) -> str`
   - `state_resolver.py` — given team + now, returns state object with hero_module, copy_tone, accent_color, promoted/demoted/hidden modules
   - `narrative_generator.py` — calls Claude Code headless subprocess, caches to SQLite
   - `profile_loader.py` — parses YAML frontmatter + markdown body from `profiles/<slug>.md`
   - `aspiration_calculator.py` — computes rung odds from SP+ + remaining schedule
   - `chronicle_generator.py` — stat anomaly preprocessing (Haiku) + ranking/writing (Sonnet)
   - `templates/` — Jinja2 templates matching module HTML from specs
   - `styles/tokens.css` — CSS custom properties from 00-tokens.md
   - `styles/modules/*.css` — one file per module from spec docs
   - `static/` — icons, live-dot animations, any SVG chrome

   Do NOT touch `reporting.py`. All new code in this module.

3. **Parser for profile files.** Reads `profiles/<slug>.md`:
   - Extracts YAML frontmatter as dict
   - Parses markdown body sections by H1 heading (Identity and heritage, Coaching lineage, etc.)
   - Returns a `Profile` dataclass with structured access

4. **State resolver implementation.** Given (team, now, last_game_outcome), returns state object per §20 of page-compositions spec. Include:
   - Offseason vs. in-season detection
   - Day-of-week in-season logic
   - Post-game mode activation (within 24h of final)
   - Rivalry-week detection
   - Program-tier baseline module selection
   - Dynamic unlock conditions from profile thresholds

### Phase 2 — Templates and styles

5. **Jinja2 templates** for every module in the spec docs:
   - `_atoms/` — metric_tile.html, aspiration_rung.html, event_log_item.html, percentile_bar.html, etc.
   - `modules/` — team_identity_header.html, heritage_strip.html, state_of_team.html, schedule_strip.html, mood_sparkline.html, this_week.html, aspiration_ladder.html, pulse.html, chronicle.html, chronicle_card.html, rivalry_card.html, savant_card.html, cfp_era_view.html, historical_season.html, game_recap_hero.html, next_game_footer.html
   - `pages/` — team_page_desktop.html (composes modules per state), team_page_mobile.html (same composition, mobile variants)
   - `partials/` — reusable sub-templates

6. **CSS implementation** — one file per module. Pull from tokens only; no hardcoded colors/spacing. Desktop-first with mobile breakpoint at 768px. Implement touch targets, snap scroll, and accessibility (keyboard nav, screen-reader labels) per specs.

7. **SVG generators** — Python functions that produce static SVG strings for:
   - Mood sparkline (preseason → now → projected)
   - Rivalry dual-trajectory chart
   - CFP-era multi-metric view (2 polylines + annotations + era ribbon + brick index)
   - Game-recap WP chart (during post-game mode)
   - Historical-season shape viz

   All pre-rendered at build time. No client-side chart library.

### Phase 3 — Content generation (requires Claude Code + Max subprocess)

8. **`manage.py generate-narratives` subcommand:**
   - Arguments: `--team <slug>` (single team) or `--all` (all profiles)
   - For each team × week combination, generates state-of-team paragraph using:
     - Profile voice_register, identity_phrase, mantra, stock_phrases
     - Never-use guardrails applied as negative prompt
     - Current week context (opponent, spread, last result)
   - Writes to `team_season_narratives` table
   - Logs token usage per run
   - Default model: Sonnet. Flag `--opus-program` forces Opus for blue-blood profiles.

9. **`manage.py generate-chronicle` subcommand:**
   - For each team × week, produces 4-6 Chronicle cards.
   - Haiku preprocessing pass: scans stats for anomalies, returns candidates with oddity scores
   - Sonnet ranking + writing pass: picks top-K per card type, writes editorial prose, attributes sources
   - Writes to `team_chronicle_observations`
   - Card types covered in v1: anomaly, flashpoint, echo (retroactive and moment and player-arc in v2)

10. **`manage.py render-team <slug>` subcommand:**
    - Loads profile, current-season data, generated narratives, chronicle cards
    - Calls state-resolver
    - Renders Jinja template
    - Writes `output/site/teams/<slug>.html`
    - Generates PNG share cards for each shareable module via Pillow
    - Returns exit code 0 on success

### Phase 4 — Notre Dame end-to-end

11. Run `generate-narratives --team notre-dame` and `generate-chronicle --team notre-dame`.
12. Run `render-team notre-dame`.
13. Open generated HTML in a headless browser (via playwright-python or similar), verify:
    - Desktop layout renders at 1440px without horizontal overflow
    - Mobile layout renders at 390px without horizontal overflow
    - All modules present in correct order for the resolved state
    - All generated copy reads on-voice for Notre Dame
    - All data populates correctly (no template errors, no missing fields)
    - SVGs render with correct dimensions
    - Touch targets ≥ 44pt on mobile
    - No accessibility violations (headings in order, alt text, keyboard nav)
14. Take screenshots at both breakpoints; save to `output/site/teams/_screenshots/notre-dame-desktop.png` and `-mobile.png`.

### Phase 5 — Fan out to the remaining 9 profiled programs

Repeat steps 11-14 for: alabama, ohio-state, georgia, michigan, texas, oregon, usc, penn-state, vanderbilt, massachusetts.

Each program's page should feel distinctly on-voice. Test specifically: does UMass read differently from Alabama? Does Vanderbilt's register carry self-aware-underdog without lapsing into cute? Does Oregon's fashion-forward voice come through without being kitsch?

---

## Model routing rules

- **Opus**: schema design (Phase 1.1), blue-blood profile-voice fine-tuning (ND, Alabama, OSU, Georgia, Michigan, Texas, USC), anchor-state narrative templates (post-loss, post-upset-win, selection-sunday).

- **Sonnet**: all code (Phases 1.2-1.4, Phase 2, Phase 3 subcommands), standard weekly narrative generation, Chronicle card ranking + writing, testing and refactoring.

- **Haiku**: file search / grep, stat anomaly candidate preprocessing for Chronicle generation, bulk annotation passes.

When unsure, default Sonnet. Escalate to Opus only when genuine editorial subtlety is at stake.

---

## Decision authority (act autonomously on all of these)

- Schema column types, constraints, indexes
- File/function/class naming within the new module
- Template structure within the spec's design language
- How to handle edge cases in profile fields (some fields may be absent for thin-history programs — degrade gracefully)
- Whether to use Anthropic SDK vs. subprocess for Claude calls (prefer subprocess → Claude Code headless)
- Which specific stats to surface per program
- Which of the candidate Chronicle observations to write up
- Error handling for missing data (log warning, render what's available, never fail the build)

**Only stop and flag if:**
- A foundational architectural conflict with existing `cfb_rankings` module structure forces a choice with significant downstream implications
- The profile files or spec docs contradict each other on a load-bearing point
- Required data doesn't exist in SQLite or CFBD and no reasonable fallback exists (rare)
- Max subscription token usage approaches 500k for this sprint (pause and report)

---

## Self-verification before reporting done

- Migration runs cleanly; `cfb_rankings.db` has new tables; `python manage.py build-site` still succeeds.
- `python manage.py render-team notre-dame` produces valid HTML that renders in a browser.
- All 10 profiled programs render via `manage.py render-team <slug>` without errors.
- Generated state-of-team paragraphs for all 10 programs are coherent and tonally distinct.
- Chronicle cards for each program pass a sanity check (actually mention the program; cite real data).
- Mobile breakpoint tests at 390pt without horizontal scroll.
- Desktop breakpoint tests at 1440pt and 1920pt without layout breaks.
- Share cards (PNG) render for hero modules and load correctly when opened as standalone images.
- Total Max subscription token usage under ~500k for this sprint.

---

## Report back with

At the end of the sprint, report:

1. **Summary of what's working, rendering, and passing self-checks** — one paragraph per phase.
2. **Screenshots** (desktop + mobile) of each of the 10 team pages. Save to `output/site/_sprint_screenshots/`. Kevin will review voice quality.
3. **Schema decisions and tradeoffs** — rationale for load-bearing choices.
4. **Token usage breakdown** — by model, by subcommand. Note any anomalous high-cost operations.
5. **Judgment calls made on ambiguous points** + reasoning for each.
6. **Concrete blockers encountered** (if any) with proposed resolution.
7. **Quality-of-voice assessment** — read all 10 generated state-of-team paragraphs back-to-back; note any that drift from profile voice.
8. **Natural next sprint** — what's the highest-leverage work from where you landed.

---

## Additional context

- Kevin is on Claude Max subscription; Claude Code headless invocation is the generation path, not direct Anthropic API.
- The Figma design system lives at `https://www.figma.com/design/eGIVOKDIFSmo1yM1LShLQx`. Tokens in `00-tokens.md` already match Figma's current state.
- `reporting.py` is 17.5k lines; do NOT touch it. New work lives entirely in `src/cfb_rankings/team_pages/`.
- The existing static-site pipeline runs via `manage.py build-site`. Integrate the new render path as an additional `render-team` subcommand; do not replace the existing build.
- All CFBD data, SP+ ratings, and fan intelligence signals are already flowing into `cfb_rankings.db`. Query the existing schema; don't re-ingest.

If you complete the sprint early, extend scope to either:
- (a) Writing the remaining 5-8 Chronicle card types at full fidelity across all 10 programs.
- (b) Implementing the Savant card with real CFBD tier-2 data for all 10 programs.
- (c) Building the historical season deep-dive template and generating it for ND's 2018 and 2024 seasons.

Your call based on what's most load-bearing.

Good luck. Report at end, not between steps.
