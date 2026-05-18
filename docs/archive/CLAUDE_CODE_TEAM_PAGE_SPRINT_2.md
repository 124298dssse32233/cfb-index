# Claude Code — Team Page Engineering Sprint 2

Copy-paste this entire document into Claude Code as the sprint-2 kickoff prompt. Same rules as sprint 1: execute autonomously, make judgment calls without stopping, report only at the end.

---

## Context — read these first

1. `TEAM_PAGE_SPRINT_1_REPORT.md` (what you shipped in sprint 1)
2. `TEAM_PAGE_WORLD_CLASS_BRIEF.md` Parts I, II, III (canonical brief)
3. `docs/design-system/12-modules-intel.md` (Savant + Rivalry + Pulse + Chronicle specs — Savant and Rivalry are sprint-2 targets)
4. `docs/design-system/00-tokens.md` and `01-atoms.md` (tokens and atomic components — already implemented in sprint 1; reuse)
5. `CLAUDE.md` (repo rules — don't touch `reporting.py`)
6. `src/cfb_rankings/team_pages/` (your sprint-1 output; you're extending this module, not rebuilding)

---

## Sprint goal

Close the persistence gap and add the two highest-leverage missing modules. By end of sprint: (1) build-site no longer overwrites the world-class team pages, (2) Savant card renders on all 11 profiled programs, (3) Rivalry card renders for each program's Tier-1 rivalry, (4) all LLM generation routed through Claude Code headless on Max subscription.

After this sprint, the 11 pages should be: persistent through build-site regressions, stat-dense (via Savant), and dramatically differentiated by rivalry context. The remaining big miss — Season Arc / CFP-era view — is sprint 3.

---

## Deliverables

### Phase 1 — Wire into build-site (do first; blocks everything else)

1. **Add `render_team_pages()` hook into the existing `build-site` pipeline.** The cleanest integration:
   - Add a new step to the build-site sequence that calls `team_pages.render_all(profiled_only=True)` which iterates the 11 profiles and writes to `output/site/teams/<slug>.html`.
   - Modify the legacy `reporting.py` team-page output path to *skip* any slug present in `profiles/` directory. Profiled programs get the new renderer; unprofiled programs keep the legacy output until Sprint 3+ expands profile coverage.
   - Use a discovery pattern: on build start, read `profiles/*.md`, extract slugs, pass the set to both renderers.
   - Do NOT edit reporting.py body — add a single guard at the team-page emit site that checks the profiled-slugs set and short-circuits.
   - Run `manage.py build-site` post-integration and confirm the 11 world-class pages survive; confirm the other 657 programs still get legacy output.

2. **Add a `manage.py render-team-pages` convenience subcommand** that runs just the team-pages render step (for iteration without full build-site cycles).

3. **Document the integration** in a one-paragraph section added to `CLAUDE.md` under a new "Team Pages (new module)" heading. Note the skip-hook in reporting.py and the render ordering.

### Phase 2 — Savant card

Spec: `docs/design-system/12-modules-intel.md` §SavantCard.

4. **Build `SavantCard` Jinja template + CSS** at `src/cfb_rankings/team_pages/templates/modules/savant_card.html` and `styles/modules/savant_card.css`. Reuse existing `PercentileBar` atom.

5. **CFBD tier-2 data integration.** The 13 metrics live in CFBD's advanced-stats endpoints. Write a `savant_data_loader.py` helper that:
   - Pulls offense: EPA/play, Success Rate, Havoc-adj PPG, Explosive Play Rate, Red Zone TD Rate, 3rd Down Conversion
   - Pulls defense (inverted): EPA Allowed/play, Success Rate Allowed, Havoc Rate, Red Zone TD% Allowed, 3rd Down Stop Rate
   - Pulls special situations: Field Position Battle, Turnover Margin, SOS-Adjusted
   - Computes percentiles vs. four peer sets: FBS, Power-4, program conference, program all-time (2014+ from your team_season_narratives / CFBD archive)
   - Caches to a new `team_savant_weekly` SQLite table (team_id, week, metric_key, pct_vs_fbs, pct_vs_p4, pct_vs_conf, pct_vs_alltime, raw_value)

6. **Peer-toggle mechanism.** Pre-compute bar widths for all four peer sets at build time; store as data-attributes on each percentile bar (e.g., `data-pct-fbs="91" data-pct-p4="85"`). Tiny vanilla JS (~20 lines) swaps `.percentile-bar__fill` widths when toggle chips are clicked. No chart library.

7. **LLM-generated narrative header** via Claude Code headless (`--llm claude`, Sonnet). Prompt template:
   > Given these 13 percentile bars for {program} through week {N}, write one 40-50 word sentence that tells the fan what the card is saying. Name top 1-2 strengths, top 1 concern, and the crux. No hedging. Use the program's voice register: {voice_register}. Follow profile's never_use guardrails.
   Cache to `team_chronicle_observations` with card_type='savant_narrative'.

8. **Echo callout** in defense section. Cross-era cosine similarity: compute feature vectors for each defensive unit from 2014+ program history; find nearest-neighbor defensive profile across all program-seasons. Display as "echo: {year} · {similarity} similarity" in the defense section header. Python-native; no LLM required.

### Phase 3 — Rivalry card

Spec: `docs/design-system/12-modules-intel.md` §RivalryCard.

9. **Build `RivalryCard` Jinja template + CSS.** Six sub-components:
   - Mythic-centered header (serif proper noun from profile's rivalries[0].name or .trophy)
   - 4-column meta strip (all-time / streak / trophy / countdown)
   - Dual-trajectory heat chart (SVG, 2 polylines + gap annotation)
   - Two posture-labeled panels with representative quotes
   - Editorial meetings list (last 10 with 1-sentence commentary)
   - "What each side needs" stakes footer

10. **Rivalry data loader.** Historical meeting results exist in CFBD; pull all-time head-to-head, streaks, last 10 meetings with scores, venues, dates. Cache to new `team_rivalry_meetings` SQLite table keyed by (program_a_slug, program_b_slug, date).

11. **Posture labels per fanbase per rivalry week.** LLM-classified 2-word posture tags from profile voice_register × current-week fan-intel signal. Sonnet prompt:
   > Given {program_A}'s voice register ({A_register}) and {program_B}'s current fan-intel signal pattern (sentiment: {X}, volatility: {Y}, volume: {Z}), produce a 2-word posture tag for {A}'s fanbase going into this rivalry week. Examples: "dismissive · confident" / "anxious · bargaining" / "coiled · hopeful". One tag per side.

12. **Representative quote selection.** For each side of the rivalry, rank top-K posts/signals from the fan-intel pipeline this week, select one that matches the posture label, lightly edit for length (≤15 words), cite source (subreddit/board/handle). Sonnet for selection + light edit. Cache to `team_chronicle_observations` with card_type='rivalry_posture_quote'.

13. **Editorial meetings commentary.** For each of the last 10 meetings in each Tier-1 rivalry, generate a single sentence of context naming the key play / stakes / register. One-time generation per meeting, ~170 meetings total across the 11 programs' Tier-1 rivalries. **Use Haiku for bulk generation** — short, factual, fast. Cache to `team_rivalry_meetings.commentary` column.

14. **Dual-trajectory heat chart.** Compute 4 weeks of rivalry-specific fan-intel signal per side; plot as 2 polylines in SVG, annotate the gap with a "+N" callout. Pre-rendered at build time; no client-side chart.

15. **Stakes footer.** For each side: one sentence on what winning/losing means (CFP-path impact, coach hot-seat, rivalry streak). Sonnet, program-voice-aware.

### Phase 4 — Swap to `--llm claude`

16. **Audit current LLM call sites** in `narrative_generator.py`, `chronicle_generator.py`, and the new savant/rivalry generators. Confirm each routes through Claude Code headless (`subprocess` invocation) not direct Anthropic API.

17. **Add `--llm` flag** to all `manage.py generate-*` subcommands if not already present. Values: `claude` (default, uses Claude Code headless → Max subscription) or `api` (direct Anthropic API, for large-batch fallback). Document the distinction.

18. **Token budget tracking.** Add a simple per-invocation logger that writes to `output/_logs/llm_usage_{date}.jsonl` — one line per Claude Code invocation with subcommand, model, input+output tokens, duration. Enables post-sprint budget analysis.

### Phase 5 — Page integration

19. **Add Savant + Rivalry cards to the page composition** per `docs/design-system/20-page-compositions.md`. Savant goes below Chronicle; Rivalry goes above CFP-era view (or replaces CFP-era placeholder).

20. **Re-render all 11 profiled pages** via `manage.py render-team-pages` after new modules land.

21. **Run `build-site` regression** to confirm the 11 pages survive the build. This is the self-verification gate — if any of the 11 revert to legacy output, Phase 1 integration is broken.

### Stretch goal (if sprint completes early)

22. **CFP-era view / Season Arc** per `docs/design-system/13-modules-archive.md`. Full two-line trajectory chart (mood + AP rank), CFP annotations, era ribbon, 13-brick chapter index, editorial closing paragraph. Most ambitious remaining module; only tackle if the four phases above are solid.

---

## Model routing rules — token-minimized

This sprint is mostly implementation, not editorial generation. Expected token usage is LOW.

**Opus**: skip entirely for this sprint. No new profile drafts; no load-bearing editorial architecture. If you reach for Opus, stop and reconsider.

**Sonnet**: all code (Phases 1-5), Savant narrative headers (~11 × 50 words = ~550 output tokens), Rivalry posture labels (~22 × 4 words), representative quote selection+edit, stakes footer per program. Estimated total: ~50k tokens.

**Haiku**: grep/file ops, CFBD data format inspection, bulk meetings commentary (~170 meetings × 1 sentence each = ~5,100 short generations). Estimated total: ~100k tokens.

**Total expected budget: ~150k tokens** (vs. sprint 1's ~500k budget). Significantly cheaper because this sprint reuses infrastructure and adds mostly deterministic code + tight LLM bursts.

If token usage exceeds 250k, stop and report — something has gone wrong.

---

## Decision authority (act autonomously)

Same as sprint 1. Make judgment calls on:
- Schema column types for new tables
- File/function naming within the new module
- Template structure within the spec's design language
- CFBD endpoint selection for tier-2 data (pick the one with the best coverage)
- Peer-set cutoff dates (FBS = all, P4 = 2024+ conference alignment, Conference = current)
- Edge cases: programs missing Tier-1 rivalries, rivalries with <10 historical meetings, meetings with incomplete data
- Error handling (log warning, render what's available, never fail the build)

**Only stop and flag if:**
- CFBD tier-2 advanced stats have access/throttle issues that block 5+ programs
- The build-site integration creates a performance problem (full build takes >3x baseline)
- Meetings data is systematically missing for major rivalries

---

## Self-verification before reporting done

- `build-site` regression passes (exit 0, 668 programs rendered, 11 profiled pages are world-class version, 657 unprofiled pages are legacy version).
- All 11 pages render with Savant card visible.
- All 11 pages render with Rivalry card for the Tier-1 rivalry (or gracefully skip if the Tier-1 is un-profiled, e.g., Notre Dame's USC rivalry renders since both are profiled; if a program's Tier-1 opponent is unprofiled, fall back to meta-strip only, no heat trajectory).
- Savant percentile toggles work (FBS → P4 → Conference → All-time); bar widths swap without layout shift.
- Rivalry heat trajectory SVGs render with correct dual-line + gap annotation.
- `llm_usage_{date}.jsonl` log exists and has entries from the sprint.
- Total Max subscription token usage under 250k.

---

## Report back with

1. **Summary** — one paragraph per phase.
2. **Screenshots** of each of the 11 pages post-sprint (`output/site/_sprint2_screenshots/`).
3. **Schema decisions** for the new tables (`team_savant_weekly`, `team_rivalry_meetings`).
4. **Integration approach for build-site** — specifically how `reporting.py` was guarded without editing its body.
5. **Token usage breakdown** by model and subcommand.
6. **Judgment calls made on ambiguous points.**
7. **Any programs whose Tier-1 rivalry fell back to meta-strip only** (due to unprofiled opponent).
8. **Natural next sprint** — likely Season Arc + expanding profile coverage to the next 20 programs.

---

## Additional context

- Your sprint-1 work is canon. Don't rewrite; extend.
- `reporting.py` is 17.5k lines — one small guard addition is OK; anything more requires a different approach.
- Build-site runtime matters. If integration adds >30s to total build time, profile and optimize.
- The Rivalry card is the higher-ambition deliverable; give it more care than Savant.
- `--llm claude` routing is the token-efficiency lever; confirm it's actually using Max subscription, not silently falling back to API.

Report at end, not between steps.
