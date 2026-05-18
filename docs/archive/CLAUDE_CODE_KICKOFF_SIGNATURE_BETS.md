# Claude Code Kickoff — Signature Bets (The CFB-Nerd Experience)

**Context**: CFB Index's player page has the v5 design system in production (once the frontend migration kickoff completes) and a working data pipeline. This kickoff adds the twelve-to-fourteen signature features that make the page bespoke for the nerdy CFB audience — Hot-Take Engine, Anti-Take Engine, Rival Radar, Statistical Mirror Match, Achievements, Coaching Lineage, Live Signal Flow, Narrative Arc Board, and the ambient texture that makes every screenshot shareable.

**Source of truth**: `PLAYER_PAGE_SIGNATURE_BETS.md` in the repo. Read once at session start and reference by section number thereafter. Each task below inlines the essential spec so a `/clear` between tasks is safe.

**How to use**: open a fresh Claude Code session, paste the block below as your first message. Claude Code works through tasks in order, phase by phase. Stop conditions between every phase. Commit + SESSION_LOG entry per task.

---

```
You are shipping the CFB-nerd signature-bets layer on top of the v5 player
page system. Source of truth for every task: PLAYER_PAGE_SIGNATURE_BETS.md
in the repo root. Read it ONCE at session start, then reference by section
number (e.g., "§4 bet #2 Hot-Take Engine"). Do NOT re-read the whole brief
per task.

## Read first, in this order (once per session)
1. CLAUDE.md
2. PLAYER_PAGE_SIGNATURE_BETS.md — full read, ONCE. Then reference by §.
3. PLAYER_PAGE_WORLD_CLASS_BRIEF.md §8 (design craft — locked tokens)
4. figma-reference/player-page/README.md + src/styles/theme.css (tokens)
5. SESSION_LOG.md (see where prior tracks left off — player-data, fan-intel,
   frontend migration; do not disturb their output)

Do NOT read reporting.py whole. 16k lines. Grep for the render function
you need, then offset+limit read a tight range.
Do NOT read fan_intelligence.py whole. Use lines 1-80 for orientation and
Grep for the function you need.

## Model routing — enforce per task
- Opus (rare):
   * rules-engine design: Hot-Take scoring function, Anti-Take paired
     rules, Achievement taxonomy + rarity tuning, Signature Play scoring
     formula.
   * algorithmic math: Mirror Match similarity + cohort weighting,
     Scenario Explorer projection model.
   * editorial-voice template design: Narrative Arc Board act structure,
     Hot-Take defensibility criteria.
   * cross-cutting data-model judgment: Coaching Lineage graph schema.
   These produce SPEC documents Kevin can review before Sonnet implements.

- Sonnet (default — the workhorse):
   * implementing any specified feature end-to-end
   * Python render functions + Alpine directives + CSS rules
   * adapters, aggregators, CLI commands
   * glue between existing v5 tokens/primitives and new modules
   * writing tests and fixture data

- Haiku (via Task subagent only — for verification, never main-thread work):
   * row-count checks, grep sweeps, HTML validity checks
   * output-shape verification against a claimed contract
   * spot-checking generator output (Hot-Takes, Narrative Arc) for
     defensibility
   * before/after visual diff descriptions
   * a11y + keyboard-nav audits

Opus tasks produce specs; Sonnet tasks produce code. Never let Opus ship
what Sonnet can ship. Never let Sonnet verify what a Haiku subagent can
verify. Save main-thread tokens for implementation work.

## Token discipline — the hard rules
- Read the brief ONCE per session. Reference by §.
- reporting.py: Grep first, Read by range. Never a whole-file read.
- Multi-file audits: Task subagent (Haiku) returns a summary — do not
  tour files in the main thread.
- At 60% context full: stop at the next task boundary, commit, log,
  hand back. /clear is safe between task boundaries.
- Haiku subagent verification: every task ends with one. The subagent
  gets a tight verification prompt and returns pass/fail + evidence.
- Each task commits independently. Live site never breaks.

## Pre-flight defaults (already decided — do not re-litigate)
- Frontend migration (S.0-S.6) must be complete or nearly so before
  Phase S1 tasks below start. If not, Claude Code runs S.* frontend tasks
  first; signature-bets wait.
- CSS layer goes under @layer components in output/site/assets/
  cfb-index.css. Signature bet styles are nested under a .bet-* or
  bet-scoped class.
- Alpine 3.14 (self-hosted, pinned) is the interactivity runtime.
- URL state uses pushState, not replaceState.
- Progressive enhancement is mandatory: every bet must render a
  default-sensible state with JS disabled.
- All 8 voice principles from §2 of the brief apply. The 5s/30s reader
  discipline from §11 is load-bearing. Any bet that fails the reading-
  tier test does NOT ship.

## Repo conventions (for this track)
- Opus spec docs: docs/specs/signature_bets/{bet_name}_spec.md
- Python renderers: new section inside reporting.py, grep-findable by
  slug (e.g., "hot_take", "rival_radar"); keep each new function under
  200 lines.
- Data generators / engines: src/cfb_rankings/bets/{bet_name}.py
  (new top-level package — mirrors cohorts/, provenance/, ingest/).
- Tests: tests/bets/test_{bet_name}.py
- Alpine scripts: output/site/assets/js/bets/{bet-name}.js
- CSS component blocks: under @layer components in cfb-index.css
- CLI commands: python manage.py {bet-name}-{subcommand} added to cli.py
- Fixtures for generator QA: tests/fixtures/bets/{bet_name}/

## Phases (execute in order — each phase ends at a hand-back boundary)

═══════════════════════════════════════════════════════════════════════
  PHASE S1 — Texture + voice  (2 weeks of wall-clock, ~8-10 tasks)
═══════════════════════════════════════════════════════════════════════

Goal: make the page feel legitimate before introducing signature modules.
Low-risk, high-compounding changes. No new modules; layer on existing.

### TASK S1.1 — FI Glossary infrastructure (Sonnet)

Inputs:
 - SIGNATURE_BETS §4 Bet #5 (FI Glossary) and §11 (reading tiers)
 - Grep reporting.py for every Fan Intelligence term used: "Belief Dial",
   "Respect Gap", "Reality Gap", "Rival Heat", "Cohesion", "Sarcasm Risk",
   "Swing", "Main Character", "Archetype", "Cohort Divergence".

Outputs:
1. seeds/fi_glossary.yaml — 10+ terms, each with:
   - name (display)
   - slug (URL anchor)
   - one_line: ≤15-word synopsis
   - full: 60-word explanation
   - micro_example: 1-sentence concrete example
   - see_also: related terms
2. New render helper in reporting.py:
     render_glossary_icon(term_slug: str) -> str
   emits `<button class="fi-glossary" data-term="..." aria-label="...">?</button>`
3. Alpine directive at output/site/assets/js/bets/glossary.js:
     registers Alpine.data('glossary', ...) that loads the term JSON
     on click and opens a native <dialog> popover (mobile: bottom sheet).
4. CSS under @layer components: .fi-glossary button styles (small ?
   icon, muted color) + .fi-glossary-popover styles.
5. Apply render_glossary_icon() next to every FI eyebrow label across
   reporting.py. Grep for eyebrow renders; this is probably 10-12 call
   sites.
6. A methodology page at /methodology/fan-intelligence.html (may already
   exist — if so, add per-term anchors).

Acceptance:
 - `python manage.py build-site` runs clean.
 - Carr page shows ? icons next to every FI term.
 - Tap/hover opens a popover with the term's definition.
 - Keyboard: Tab focuses, Enter opens, Esc closes, Space re-opens.
 - Mobile: tap opens bottom sheet. Sheet dismissible by drag or X button.
 - Beginner test: a reader with no prior knowledge can learn what
   "Belief Dial" means in 5 seconds of interaction.

Haiku verification:
 - Open Carr's page + Watkins's page: count fi-glossary buttons; every
   FI eyebrow must have one.
 - Parse the YAML: every entry has all required fields.
 - Tab through the page with keyboard-only: every icon reachable.

### TASK S1.2 — Inline confidence chips (Sonnet)

Inputs:
 - SIGNATURE_BETS §5 smaller detail #3, §2 voice principle 3
 - Grep reporting.py for metric-render functions (percentile bars,
   stat cards, fingerprint cells).

Outputs:
1. New primitive function render_confidence_chip(sample: int,
   confidence_label: str) -> str that emits a tiny colored dot +
   optional sample count, e.g. `● HIGH · n=142`.
2. CSS tokens for confidence state:
     --confidence-high: oklch(0.65 0.15 145)  /* green */
     --confidence-medium: oklch(0.72 0.12 85) /* amber */
     --confidence-low: oklch(0.65 0.15 20)    /* red */
     --confidence-below-floor: oklch(0.5 0.02 250) /* muted grey */
3. Apply the chip to every metric render function. Grep-discover and
   inject at the known line for each metric.
4. Semantic rules:
   - sample ≥ 40 (or cohort-defined high threshold) → HIGH
   - 12 ≤ sample < 40 → MEDIUM
   - 4 ≤ sample < 12 → LOW (prefix stat with ~)
   - sample < 4 or below_floor flag → BELOW FLOOR (muted color, no value)

Acceptance:
 - Carr page: every percentile bar + stat card has a confidence chip.
 - Walkon page: the empty-state skeletons show BELOW FLOOR chips
   correctly; no false HIGH chips.
 - Chips visually subtle (--fs-meta, muted by default) — never louder
   than the metric itself.

Haiku verification:
 - Grep for render-metric calls; confirm 100% of them call
   render_confidence_chip.
 - Spot-check 5 player pages: chip states match expected based on
   sample data.

### TASK S1.3 — Era context + historical references (Opus for the data
     contract, Sonnet for implementation)

Opus sub-task (30-60 min, produces spec doc only):
 - Design era-context algorithm: for any (player, metric, season) tuple,
   find the historical comparable (same program / same conference / same
   era) and emit an era-context string.
 - Output: docs/specs/signature_bets/era_context_spec.md

Sonnet sub-task (2-4 hr, implements from spec):
Inputs:
 - era_context_spec.md
 - Grep reporting.py for record-eligible metric renders.

Outputs:
1. src/cfb_rankings/bets/era_context.py:
     compute_era_context(player_id, metric_id, season, value, cohort)
     -> {applicable: bool, text: str, target_ref: dict}
2. Apply to every record-eligible metric render in reporting.py. Era
   context string appears beneath the metric value: "Best by a ND QB
   since Brady Quinn 2006."
3. Graceful degradation: if no comparable exists (new program,
   under-10-year era), omit quietly.

Acceptance:
 - Carr page: era context appears on ≥5 metrics, all verifiable against
   the DB.
 - Watkins page: zero era-context strings (walk-on has no records).
 - No false positives: every era-context claim is empirically true.

Haiku verification:
 - Spot-check 10 era-context strings against the DB: each must be
   strictly correct. Pick strings that involve named historical players.

### TASK S1.4 — Weekly "What Changed" diff (Sonnet)

Inputs:
 - SIGNATURE_BETS §4 Bet #6

Outputs:
1. output/site/assets/js/bets/what-changed.js — Alpine component.
   - On page load, read localStorage[`cfb:last-visit:${playerSlug}`]
     (ISO date) and compare against current page's render timestamp
     + state hash.
   - If first visit: no diff rendered.
   - If returning: emit a What-Changed card ABOVE the Hero showing
     up to 5 bullet diffs.
2. Server side: reporting.py embeds a <script data-state="..." data-
   generated-at="..."> JSON blob per page with:
     { heisman_heat, standing_rung, room_mentions, outlook_updates,
       achievements_unlocked }
3. Alpine diffs last-visit state against current-load state and renders
   natural-language bullets:
     - "+3 Heisman Heat"
     - "Up 2 rungs in Standing"
     - "+14 mentions in The Room"
     - "New in 2026 Outlook: Davey O'Brien watch list"
     - "1 new achievement unlocked: Gunslinger"
4. CSS: subtle gold left-border card. Dismissible (X button → updates
   last-visit to now, clears the card).
5. Progressive enhancement: without JS, card doesn't render (it's a
   returning-visitor bonus, not critical content).

Acceptance:
 - First visit to Carr page: no card.
 - Come back after a simulated state change (manually edit the page's
   data-state): card renders with accurate bullets.
 - Dismiss: localStorage updates, card stays dismissed on reload.

Haiku verification:
 - Spot-check 5 pages' embedded JSON blobs for completeness.
 - Manual-script test: simulate return visit, confirm diff accuracy.

### TASK S1.5 — Tabular numerals + rhythm rule enforcement sweep (Sonnet)

Goal: ambient CSS pass that enforces the rhythm rule across every
metric-render site. Fast, mechanical, high-impact.

Outputs:
1. cfb-index.css @layer utilities:
   - .tabular-num { font-feature-settings: "tnum", "lnum"; }
   - .eyebrow-label { text-transform: uppercase; letter-spacing: 0.08em;
     font-size: var(--fs-meta); color: var(--muted-foreground);
     font-weight: 500; }
   - .metric-value { font-variant-numeric: tabular-nums lining-nums;
     font-weight: 700; font-size: var(--fs-h2); }
2. Grep reporting.py for metric renderings. Ensure every one has the
   three-class trio applied (eyebrow → metric-value + tabular-num →
   interpretation).
3. Audit + fix any hardcoded font-size / font-weight that violates the
   rhythm.

Acceptance:
 - Visual: every metric on every module follows bright-number-muted-
   label rhythm.
 - All number-bearing elements use tabular-nums (line up visually when
   stacked).

Haiku verification:
 - Grep the generated HTML for hardcoded font-size. Must be 0 outside
   skip-link / print critical CSS.
 - Scan for `font-weight:\s*[1-5]00` in metric-rendering lines: should
   be 0 (all heavy via --fs-* tokens).

### TASK S1.6 — Live Signal Flow infrastructure (Sonnet)

Goal: the event-driven signal bar ("🔴 LIVE · CARR COMMITS TO RETURN
FOR 2026 · 2h ago") per §4 Bet #13. This task builds the infrastructure
but no specific event triggers yet.

Inputs:
 - SIGNATURE_BETS §4 Bet #13

Outputs:
1. Migration: migrations/YYYYMMDD_NN_player_signal_events.sql creating
   player_signal_events table:
     - player_id, event_type, event_data_json, event_ts, decay_hours
     - indexes on (player_id, event_ts)
2. src/cfb_rankings/bets/signal_flow.py:
     emit_signal_event(player_id, event_type, data, decay_hours)
     fetch_active_signals(player_id, now) -> list[Signal]
3. reporting.py renders the signal bar above Hero when fetch_active_
   signals returns ≥1 Signal. Bar design per §4 Bet #13 (thin, gold
   left border, decaying opacity over 72h).
4. Alpine directive at /assets/js/bets/signal-flow.js for the bar's
   expand/collapse behavior + polling every 60s during an active event.

Acceptance:
 - Fresh DB: no signal bars render.
 - Manually INSERT a test event: signal bar appears on the player's
   page, styled correctly, decays over time.
 - No events → zero layout impact (bar hidden, not just transparent).

Haiku verification:
 - Migration runs idempotently.
 - Insert + fetch test passes.
 - Signal bar renders for 3 synthetic events at different decay stages.

### PHASE S1 CLOSE
Commit the 6 tasks above. Run a full site build. Ship. Hand back to Kevin.

═══════════════════════════════════════════════════════════════════════
  PHASE S2 — The big bets  (3-5 weeks, Opus-heavy for design)
═══════════════════════════════════════════════════════════════════════

### TASK S2.1 — Hot-Take Engine design (Opus)

Opus produces a spec document ONLY. No code.

Output: docs/specs/signature_bets/hot_take_spec.md
 - Defensibility criteria: every take backed by (rank, cohort, sample,
   methodology) quadruple.
 - Novelty scoring: how much the take surprises vs conventional wisdom.
 - Template library: 15-25 natural-language take templates (e.g.,
   "{Player}'s {metric} is higher than {comparison_cohort}").
 - Generation algorithm: scan player's metric profile → candidate takes
   → filter by defensibility gate → rank by novelty × stakes → select
   top 1 for the day.
 - Scheduled daily refresh logic.
 - Share-card generation: the image-ready export format.
 - QA workflow: flag button, editor review, auto-hold if flag rate > 3%.

Kevin reviews spec before S2.2 runs. Hand back.

### TASK S2.2 — Hot-Take Engine implementation (Sonnet)

Implements from hot_take_spec.md.

Outputs:
1. src/cfb_rankings/bets/hot_take.py:
     generate_hot_takes(player_id, season, week=None) -> list[HotTake]
     select_daily_take(player_id, today) -> HotTake | None
2. Template engine + defensibility gates per spec.
3. CLI: python manage.py player-hot-take <slug> [--seed daily]
4. Batch: compute_daily_hot_takes(db, date) populates a new
   player_daily_hot_take table for all eligible players nightly.
5. reporting.py renders the daily take as a card above The Room.
6. Share-card image generation: HTML snippet with cfbindex.com
   watermark, rendered to PNG via a headless browser or a static
   canvas-based helper (v1: static, nice-to-have).
7. Tests: tests/bets/test_hot_take.py with fixtures covering novel
   takes, filtered-out boring takes, defensibility-gate failures.

Acceptance:
 - Carr page: one Hot-Take card with a defensibly-true one-liner.
 - Walkon page: no Hot-Take card (gracefully absent, not "no data
   available" filler).
 - CLI emits the take + its math trail.

Haiku verification:
 - 30-take spot check across 30 players: every take must be verifiable
   against the DB. Report any that aren't.

### TASK S2.3 — Anti-Take Engine (Opus design + Sonnet implementation)

Opus sub-task: docs/specs/signature_bets/anti_take_spec.md
 - Paired-caveat design: given a Hot-Take, generate the honest counter.
 - Caveat library: common weaknesses (garbage-time, small sample, soft
   cohort, home-field asymmetry, etc.).
 - Pairing rule: every Hot-Take must have an Anti-Take, else the
   Hot-Take doesn't ship.

Sonnet sub-task:
Outputs:
1. Extend hot_take.py with generate_anti_take(hot_take) -> AntiTake.
2. reporting.py renders the Anti-Take as a sibling card directly below
   the Hot-Take with a quiet divider.
3. Tests: every Hot-Take in fixtures must have a paired Anti-Take.

Acceptance:
 - Carr page: Hot-Take + Anti-Take visibly paired, distinct voices.
 - Anti-Take is specific, not boilerplate. If it can only be boilerplate
   for a given take, the take is held.

Haiku verification:
 - Same 30-take spot check + verify every Anti-Take is specific and
   empirically accurate.

### TASK S2.4 — Rival Radar (Sonnet — the data pipeline exists)

Inputs:
 - SIGNATURE_BETS §4 Bet #1
 - Existing cohort pipeline from fan-intel work (rival_bucket data in
   player_week_conversation_features — player-mention extraction must
   be live, else this task is blocked and hands back).

Outputs:
1. src/cfb_rankings/bets/rival_radar.py:
     compute_rival_radar(player_id, season) -> RivalRadar with:
     mention_count_7d, mention_count_30d, peak_24h_moment,
     relative_fixation (vs avg opposing QB), sentiment_mix,
     obsession_score, per_rival_breakdown.
2. reporting.py render_rival_radar_card() — a new module between The
   Room and 2026 Outlook.
3. CSS + Alpine for per-rival sub-tab behavior.
4. Tests with synthetic multi-cohort fixtures.

Acceptance:
 - Carr page (once mention extraction is live): renders with Michigan/
   USC/Stanford obsession scores.
 - Graceful fallback: if player-mention extraction hasn't run, renders
   "Awaiting Signal" with a clear reason.
 - Reading tier test: 30-second lede reads correctly at a glance.

Haiku verification:
 - Synthetic fixture test: fixture values flow through to rendered HTML
   exactly.
 - a11y: per-rival sub-tabs are keyboard-navigable with aria-selected.

### TASK S2.5 — Statistical Mirror Match (Opus for math, Sonnet for code)

Opus sub-task: docs/specs/signature_bets/mirror_match_spec.md
 - Feature vector per position (QB/RB/WR/DB/OL/K/P): which percentile-
   normalized stats go into the vector.
 - Similarity metric: cosine similarity vs Mahalanobis vs other.
 - Cohort weighting: should similarity weight similar-era / same-
   conference higher?
 - False-positive guardrails: min similarity threshold, required min-
   sample per comparison point, exclusion of sub-50th-pct matches.
 - Nightly job design: precompute top-10 per player or compute on
   demand.

Sonnet sub-task:
Outputs:
1. src/cfb_rankings/bets/mirror_match.py:
     build_player_feature_vector(player_id, through_week) -> np.array
     find_mirror_matches(player_id, season, week, k=10) -> list[Match]
2. Nightly batch: compute_mirror_matches(db, season) populates
   player_mirror_matches table.
3. reporting.py render_mirror_match_card() — new small module nested
   in Peer Comparator.
4. "Show top 10" drawer via Alpine.
5. Tests.

Acceptance:
 - Carr page: mirror match card shows closest historical match with
   similarity %, context, outcome narrative.
 - Quality check: Carr's match is actually comparable (not a weird
   false positive).
 - Skeleton variant for freshmen without enough data.

Haiku verification:
 - Run 20 players' mirror matches through the Haiku subagent: each
   match should pass a "does this feel right" check — it can refuse
   any match it thinks is a false positive and ask for review.

### TASK S2.6 — Achievements taxonomy + rarity tuning (Opus)

Opus produces: docs/specs/signature_bets/achievements_spec.md
 - Taxonomy of 15-25 achievements covering: rare-percentile, historical-
   milestone, novelty, clutch, situational.
 - Per-achievement definition: criteria, min-sample, rarity target
   (% of all qualifying players who should hold it).
 - Detection algorithm.
 - Rendering spec: gold medallion, hover card, unlock context.

Kevin reviews spec + approves rarity distribution before S2.7 runs.

### TASK S2.7 — Achievements implementation (Sonnet)

Outputs:
1. src/cfb_rankings/bets/achievements.py:
     detect_achievements(player_id, season) -> list[Achievement]
     compute_achievement_rarity(achievement_id) -> float
2. Per-achievement detector functions (one per achievement in the
   taxonomy).
3. Nightly batch populates player_achievements table.
4. reporting.py render_achievement_ribbon() — near Hero, shows top-6
   achievements visible with hover drawer for the rest.
5. CSS: gold medallion + hover card + share button.
6. Share card generation per achievement.

Acceptance:
 - Carr page: 6+ achievements render, each with correct rarity.
 - Walkon page: 0 achievements, ribbon hidden.
 - Every achievement's rarity matches the spec's target within ±2%.

Haiku verification:
 - Sample 50 players: rarity distribution matches spec. Report
   any achievement that's >15% inflated or <1% rare (failure of
   rarity tuning).

### TASK S2.8 — Prediction Markets woven through Hero + Outlook (Sonnet)

Inputs:
 - SIGNATURE_BETS §4 Bet #9
 - Existing Kalshi / PolyMarket / sportsbook adapters in ingest/sources/
   (may need minor extension — if so, flag and ask).

Outputs:
1. src/cfb_rankings/bets/prediction_markets.py:
     fetch_player_market_signals(player_id, season) ->
       {heisman_futures, team_win_total, prop_markets, market_moves}
2. Update _render_hero_fingerprint to include "2026 Heisman Futures" cell
   with Kalshi/market name, odds, implied %, 4-week trajectory.
3. Update _render_2026_outlook to include market-move context.
4. Methodology footnote: "Prediction markets are third-party signals,
   not weighted into our scores. Sources: Kalshi, PolyMarket, FanDuel."

Acceptance:
 - Carr page: Heisman futures cell is live with real Kalshi data.
 - Market-move widget appears when odds shift >100 bps in 24h.
 - Graceful fallback when markets don't exist for a player: cell shows
   "Not yet listed on major futures markets."

Haiku verification:
 - Cross-check live Kalshi/PolyMarket odds against what's rendered.
 - Walkon page: no market data claimed (correct absence).

### TASK S2.9 — Coaching Lineage + System Context (Opus for schema,
     Sonnet for implementation)

Opus sub-task: docs/specs/signature_bets/coaching_lineage_spec.md
 - Graph schema: coach-coach relationships (mentor-to-mentee,
   previous-position chain).
 - Data sources for lineage (CFBD coaching_staff may be a start; may
   need secondary research).
 - System-fingerprint metrics (plays/gm, pass%, explosive%, tempo).
 - Render format: "{HC} Year {N} · OC {OC name} · scheme family +
   3-deep lineage."

Sonnet sub-task:
Outputs:
1. Migration: migrations/YYYYMMDD_NN_coaching_lineage.sql — coaches,
   coach_tenures, scheme_families, lineage_edges.
2. Seed: seeds/coaching_lineage.yaml — top-20 programs' current staff
   + 3-deep lineage (manual research; Opus/Kevin can fill the gaps).
3. src/cfb_rankings/bets/coaching_lineage.py — query + aggregation.
4. reporting.py render_coaching_lineage() — new small module near
   Supporting Cast.
5. Continuity chip in Hero cell: "Year 2 OC" / "NEW OC · YEAR 1".

Acceptance:
 - Carr page: coaching lineage renders Freeman → Denbrock → 3-deep
   lineage with system fingerprint.
 - Walkon page: same data renders (lineage is team-level, not player-
   dependent).

Haiku verification:
 - Verify 5 programs' lineages against publicly-known facts.

### PHASE S2 CLOSE
8 tasks. 4 Opus spec tasks. 4 (or 5) Sonnet implementation tasks. Commit,
summarize, hand back.

═══════════════════════════════════════════════════════════════════════
  PHASE S3 — Engagement layer  (3-4 weeks)
═══════════════════════════════════════════════════════════════════════

### TASK S3.1 — Cohort Divergence Map inside The Room (Sonnet)
Build the 2D scatter visualization per §4 Bet #10. Alpine + SVG.
Sub-cohort aggregation requires mention-author metadata — if sparse,
fall back to four-cohort view.

### TASK S3.2 — Signature Play surfacing (Opus for scoring, Sonnet)
Opus: per-play signature score formula (EPA × novelty × situational
weight × profile-fit).
Sonnet: nightly job that picks THE signature play per game + per
season. Render card under Signature Story.

### TASK S3.3 — Scenario Explorer (Opus for projection model, Sonnet)
Opus: projection model — user-supplied remaining-game stat deltas
→ projected career/season outcome vs historical benchmark.
Sonnet: slider widget in Alpine + server-side projection computation.

### TASK S3.4 — Narrative Arc Board (Opus template + manual top-20
     + Sonnet auto-gen for long tail)

Opus sub-task: design the 3-act narrative template + voice guidelines
for auto-generation + confidence-gate for deciding manual vs auto.

Kevin hand-authors top-20 players' arcs.

Sonnet sub-task: implement the auto-generator behind the confidence
gate. Flag-for-review workflow for anything auto-generated.

### PHASE S3 CLOSE
4 tasks. Ship, hand back.

═══════════════════════════════════════════════════════════════════════
  PHASE S4 — Polish + experiments  (ongoing)
═══════════════════════════════════════════════════════════════════════

Not a blocker on anything. Ship as time permits.

- Keyboard shortcuts + context menu (Sonnet).
- Screenshot mode (Sonnet).
- Draw-the-Line mini-game on trajectory cards (Sonnet).
- Historical "this day" chip (Sonnet).
- Page-change log at footer (Sonnet).
- Gilded Section (Opus for novelty-scoring algorithm, Sonnet for render).
- Rivalry splits in Splits module (Sonnet).
- Opponent-strength stripe under game-level stats (Sonnet).
- Screenshot-mode share image generation (Sonnet).
- A/B or qualitative tests: which features drive return visits? Which
  modules get most-screenshotted? Instrument and observe.

Each polish task: own commit, own SESSION_LOG entry.

═══════════════════════════════════════════════════════════════════════

## Stop conditions
- End of any phase (S1/S2/S3) — commit, summarize, hand back to Kevin.
- Context above 60% — stop at next task boundary.
- Opus spec disagreement — if the spec Opus produces doesn't match
  Kevin's intent from the brief, STOP. Never let Sonnet implement from
  a spec Kevin hasn't reviewed.
- Haiku verification failure — never ship a task that failed
  verification. Fix or escalate.
- Any schema change not covered here — AskUserQuestion.

## Per-task protocol (identical to prior kickoffs)
1. Announce: "Starting TASK S{N}.{M} — {name}. Model: {Opus|Sonnet}."
2. Read only what the task requires.
3. Implement / design.
4. Haiku subagent verification.
5. git commit -m "bets: S{N}.{M} — {one-line summary}"
6. Append 3 lines to SESSION_LOG.md.
7. Next task or stop per stop conditions.

## Begin
Verify frontend migration (S.0-S.6) is complete. If not, hand back — we
wait.

If yes, start with TASK S1.1 (FI Glossary infrastructure — Sonnet).

If SESSION_LOG.md doesn't have a bets section yet, append header:

# Signature Bets — Session Log

Then start logging S1.1.
```

---

## Operator notes (not part of the paste-in)

### Why this structure

- **One kickoff doc covers all four phases** (S1-S4) but tasks have stop-conditions between phases. Kevin ships S1, reviews with real data, then decides whether S2 is still right. The doc is read once; tasks are self-contained so `/clear` is safe between task boundaries.
- **Opus produces SPEC documents**, not code. Sonnet implements from specs. This gives Kevin a review gate between design and implementation on every expensive decision (hot-take defensibility, anti-take pairing, mirror-match math, achievements taxonomy, coaching lineage schema). If Kevin doesn't like the spec, it's easier to revise than to unwind Sonnet's implementation.
- **Haiku subagents for verification only.** They return pass/fail + evidence. Main thread never tours files. This is the biggest token saving — verification work is the majority of context spend in naive agent runs.
- **Bets package at `src/cfb_rankings/bets/`** — mirrors existing `cohorts/`, `provenance/`, `ingest/` packages. One file per bet. Keeps reporting.py lean.
- **Reading-tier discipline enforced per task.** Every task's acceptance criteria include "5s read works / 30s read works" where applicable. Any bet that fails the reading-tier test does NOT ship.

### Token economics, estimated

- **Phase S1**: ~6 tasks × ~40k tokens each main-thread + ~10k/task for Haiku subagents → ~300k tokens total. Sonnet-heavy. Moderate cost.
- **Phase S2**: ~8 tasks including 4 Opus specs. Opus specs: ~30k tokens each, high-quality-judgment work. Sonnet implementations: ~40k each. → ~500k tokens total. Higher cost, but Opus-spec-then-Sonnet is cheaper than running Opus end-to-end.
- **Phase S3**: ~200k tokens.
- **Phase S4**: ongoing, ~20k per task.

If Kevin does NOT model-route (everything as Opus or Sonnet), cost balloons 3-5×. The routing is the savings.

### Prioritization across all tracks right now

Kevin has FOUR parallel Claude Code tracks now. He's solo. Serialization matters.

My recommended order, honest:

1. **This week** — P.0 offseason hotfix (shipped or in-flight) + finish frontend migration S.2-S.6 (1-2 weeks). Critical path: nothing else lands on the v5 design without this.
2. **Next week** — P.1 phase detection + P.2 Offseason Status chip + player-mention extraction M.0-M.5 (these three don't collide — can run in parallel).
3. **Weeks 3-4** — Signature Bets Phase S1 (texture + voice) + P.3 2026 Outlook + P.7 Transfer portal. S1 waits for frontend migration; P.3/P.7 need P.1.
4. **Weeks 5-8** — Signature Bets Phase S2 (the big bets). This is where the product starts to feel special.
5. **Weeks 9+** — Signature Bets Phase S3/S4, Fan Intel Weeks 3-8 resume, Figma Stage 4.

If Kevin tries to do all four tracks simultaneously, progress slows because each session needs to re-orient. Better to finish the frontend migration cleanly, then rotate tracks weekly.

### When to pause and rethink

- If Hot-Take Engine Haiku QA shows flag-rate > 3% on first batch → STOP S2.2, revise spec.
- If Mirror Match spot-check finds > 2 false positives in 20 samples → STOP S2.5, revise math.
- If Achievements rarity distribution drifts > 15% from spec targets → STOP S2.7, re-tune.
- If any S1 task breaks the 5s/30s reading-tier test → STOP, revise the task scope before shipping.
- If frontend migration S.6 hasn't shipped by the time S1 is ready → wait. Don't layer bets on partial v5.

### The one sentence

Run this like the prior kickoffs — Opus designs, Sonnet implements, Haiku verifies, one task per commit, one phase per hand-back, reading-tier discipline non-negotiable, and the whole thing rolls through in 8-12 weeks of focused work.
