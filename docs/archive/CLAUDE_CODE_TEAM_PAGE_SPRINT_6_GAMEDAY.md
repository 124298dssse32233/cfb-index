# Claude Code — Team Page Sprint 6: Live Gameday Mode

Paste this whole document into a fresh Claude Code session **only after Pulse Wire-Up and Chronicle Rebuild sessions have both fully landed and been committed.** This sprint builds on infrastructure those two sprints ship. Sonnet default; Opus for the state-of-team post-game paragraphs (editorial load-bearing, outcome-variant voice); Haiku for WP annotation ranking. Target budget: ~300k tokens.

---

## Why this sprint matters

Week 1 of the 2026 season is four months away. Live gameday mode is where the product becomes visceral — a fan watching ND–USC sees the Pulse spike in real time, the WP chart populate, Chronicle cards arrive at T+35 / T+90 / T+180 post-whistle, the page transition from live-tracker to recap-chapter. Nothing else on the product carries that wow factor.

The constraint: we must build AND rehearse this now, against simulated gameflow, because there are no real games to test on for four months. The sprint includes a rehearsal harness so September is a known-working system, not a debut.

---

## Context documents — read these first in this order

1. `docs/design-system/14-modules-game-recap.md` — existing spec
2. **Figma mockup** — `Alabama · Post-Iron-Bowl · Game Recap Mode` node on Cover page of `eGIVOKDIFSmo1yM1LShLQx` (node id `58:2`). Design-of-record. Full stack: mode banner → GameRecapHero (identity row + final score + state-of-team + WP chart + 4-stat diagnosis) → PulseLiveLoss (mood card + trajectory + top venues + what-moved-it-last-6h + 3 takes) → ChronicleGameEdition (3 cards) → CFPMathRevised → NextGameFooter → state-transition design note.
3. `docs/CHRONICLE_EDITORIAL_BRIEF.md` — mandatory voice contract. Chronicle game-edition cards MUST pass the Beat-Writer Test + Stage-4 validation gate.
4. `src/cfb_rankings/team_pages/state_resolver.py` — extend for post-game states
5. `src/cfb_rankings/team_pages/renderer.py` — extend for game-recap mode hero swap
6. `src/cfb_rankings/team_pages/chronicle_generator.py` — extend with game-edition pipeline
7. `src/cfb_rankings/team_pages/narrative_generator.py` — extend with post-game state-of-team variants
8. `src/cfb_rankings/fan_intelligence.py` — Pulse live-loss variant integration
9. `CLAUDE.md` §team_pages — integration with build-site, PROFILED_SLUGS guard

---

## Phase 1 — Live-gameday state infrastructure

### 1.1 Extend state_resolver with outcome-typed post-game states

Current state_resolver handles `post-loss-sunday-monday` and `post-win-sunday-monday` as coarse states. Sprint 6 needs finer granularity matching the Figma mockup's five modes:

| state | hours_since_final | outcome_category | derivation |
|---|---|---|---|
| `game-recap-win-clear`   | 0–24h | win_margin ≥ 10, not an upset | expected result, confident register |
| `game-recap-win-upset`   | 0–24h | win_margin any, opponent was favored by ≥ 7 pre-game spread | amber-accented, Chronicle-dominant |
| `game-recap-loss-close`  | 0–24h | loss_margin ≤ 7 | coral-accented, measured register |
| `game-recap-loss-blowout`| 0–24h | loss_margin ≥ 14 | red-accented, rebuilding register |
| `game-recap-loss-upset`  | 0–24h | loss vs. opponent favored by ≤ 3 (or team was favored) | red-accented, crisis register |
| `post-game-monday-tuesday` | 24–72h | any | standard state-of-team returns; game-edition Chronicle cards pinned |

Pre-game spread comes from `team_cohort_week` fan-intel feed where Kalshi / Polymarket markets are aggregated, or from CFBD if market data is thin. Both are already ingested via sprint-5-era fan intel.

### 1.2 Game-state polling infrastructure

New table `games_live` (migration):
```sql
CREATE TABLE games_live (
    game_id INTEGER PRIMARY KEY,
    home_team_slug TEXT NOT NULL,
    away_team_slug TEXT NOT NULL,
    kickoff_at DATETIME NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('scheduled','in_progress','final')),
    current_quarter INTEGER,
    time_remaining TEXT,
    home_score INTEGER,
    away_score INTEGER,
    home_wp REAL,           -- current win probability
    last_play_text TEXT,
    final_at DATETIME,
    wp_timeseries_json TEXT, -- array of {t, home_wp, event} sampled every ~30s during game
    events_log_json TEXT,    -- array of scoring plays + key events for "what moved it"
    updated_at DATETIME NOT NULL
);
```

Adapter: `src/cfb_rankings/ingest/sources/cfbd_live_game.py` — polls CFBD live-game endpoint every 60s during kickoff-to-final windows. Writes to `games_live`. GitHub Actions workflow: `fanintel-gameday-live.yml` — runs every 1 minute on Saturdays kickoff-to-midnight ET.

### 1.3 Post-game state activation

On state transition from `in_progress` to `final`:
1. Set `games_live.final_at = now`
2. Invalidate cache for both teams' pages
3. Enqueue T+5, T+15, T+20, T+25, T+30, T+35, T+40, T+45 generation jobs
4. Each job re-renders the team page with progressively more populated game-recap content

### 1.4 Cache + re-render cadence per the spec

- T+5:  Swap hero to `GameRecapHero` with final score + stub diagnosis ("processing")
- T+15: `state_of_team_post_game` paragraph lands (Opus, outcome-variant voice)
- T+20: `diagnosis_stats` populate (Sonnet selects top 4 from ~30 divergence-ranked candidates)
- T+25–30: `chronicle_cards_post_game` 3 cards land (see Phase 3)
- T+35: `cfp_math_revised` paragraph lands
- T+40: `events_72h` summary finalized (aggregates fan-intel pipeline)
- T+45: Final republish

### Self-verification Phase 1

- Migration applies cleanly, `games_live` table created
- Mock a final-state row for a past game (Alabama 2024 vs Auburn fake data) and verify state_resolver returns `game-recap-loss-close` or whatever outcome_category the mock represents
- Re-render Alabama team page; hero module swaps to GameRecapHero

---

## Phase 2 — GameRecapHero module

Match the Figma mockup at node `58:2` (Cover page, `Alabama · Post-Iron-Bowl · Game Recap Mode`).

### 2.1 Hero structure

New renderer: `src/cfb_rankings/team_pages/game_recap_hero.py`

Output HTML per spec `14-modules-game-recap.md` §GameRecapHero. Key components:

1. **Mode banner** — red-bordered pill at page top: live dot + "GAME RECAP MODE · {outcome_category}" + "FINAL · {freshness} · STANDARD VIEW RETURNS {next_update_label}"
2. **Identity row** — wordmark + record (with rank-drop inline: "AP #6 (was #3)") + score block (loser muted, winner in opponent's primary accent color)
3. **State-of-team paragraph** — serif, in outcome-variant voice. See Phase 2.3.
4. **WP chart** — 880×148 SVG with 3 annotation dots (peak / pivot / sealed). See Phase 2.4.
5. **4-stat diagnosis row** — 4 cards across, color-coded (concern/bad/ok/strength) per band

### 2.2 Outcome-variant accent colors

From profile `accent_hex` as base; modulate per outcome_category:
- `win-clear`: program accent, unchanged
- `win-upset`: amber `#d9a55e` dominant
- `loss-close`: coral `#d95e7c` accents
- `loss-blowout`: red `#c04a4a` accents
- `loss-upset`: red accents + "crisis register" copy-tone flag set for Phase 3

### 2.3 state_of_team_post_game paragraph generation (Opus)

Prompt structure — voice is highest-stakes editorial in the product, so Opus always:

```
ROLE: Write the single paragraph that anchors Alabama's page for the next 24 hours after a loss to Auburn in the Iron Bowl.

PROGRAM VOICE (verbatim from profile):
- voice_register: <verbatim>
- identity_phrase: <verbatim>
- mantra: <verbatim>
- stock_phrases: <verbatim>
- never_use: <verbatim>

OUTCOME: loss-close. Final 24-31 at Jordan-Hare. Bama led 24-17 at halftime, gave up 14 unanswered in the 4Q.

OUTCOME REGISTER: reckoning. Not catastrophizing. Not bargaining. The register of a program accepting what just happened without flinching or posturing.

STRUCTURE: 2-4 sentences. 60-100 words. First sentence must be a factual statement of what happened. Remaining sentences carry the program's voice processing it. Must reference a specific element of the game (Jordan-Hare, rivalry name, quarter, specific play phase). No generic gestures.

BANNED PHRASES: sample, pipeline, every season produces, this table, pattern is, compression of outcome, methodology.

BEAT-WRITER TEST: Could a sharp columnist for this program have written this paragraph Sunday morning? If no, rewrite.
```

Generate one paragraph per outcome × program combination. At 17 profiled programs × 5 outcome categories = 85 potential paragraphs — but we generate on-demand per actual game, not prebuild. Cache keyed by `(team_slug, game_id)`.

### 2.4 WP chart generator

Pre-rendered SVG at build time from `games_live.wp_timeseries_json`.

- viewBox `0 0 600 148`
- Gridlines at 0%, 25%, 50%, 75%, 100%
- Quarter dividers (vertical, at t=quarter_boundary)
- WP polyline (coral for loss, navy for win, thick 2.5px)
- 3 annotation dots: Haiku selects peak / pivot / sealed
  - **Peak** = highest WP value reached by the team
  - **Pivot** = the WP inflection point with largest single-play ΔWP (opponent's best play)
  - **Sealed** = the moment WP crossed a threshold for the last time (e.g., final crossing of 50% for a loss)
- Labels on annotations in serif italic 10px

### 2.5 Diagnosis stats selection

~30 stat candidates computed from the game: rush YPC, pass YPA, 3rd-down conv, red-zone TD%, TO margin, explosive plays allowed, sack rate, pressure rate, avg field position, 2H points, opponent 2H points, time of possession, penalty yards, first downs, 4th-down decisions and outcomes, ...

Rank each by divergence from team's season-to-date baseline (z-score). Sonnet picks top 4 with:
- At least 1 concern (band: concern) — the one the fanbase will talk about
- At least 1 that cites program history ("worst IB since '13")
- Each with a 1-line caption ≤ 35 characters

### Self-verification Phase 2

- Render Alabama page with a mock final-score row (Bama 24, Auburn 31). Visual match to Figma mockup.
- Run all 5 outcome categories against ND (mock each), confirm accent colors + state-of-team register shifts correctly.
- WP chart renders with 3 labeled annotations, not more, not less.

---

## Phase 3 — Chronicle Game Edition cards

Generate 3 cards post-final in the T+25–30 window. Cards MUST pass the CHRONICLE_EDITORIAL_BRIEF.md validation gate. Reuse the Stage 3 writing + Stage 4 validation infrastructure from the Chronicle Rebuild sprint.

### 3.1 Card slots

1. **Anomaly** — A stat from the just-ended game that is a program-historical outlier. E.g., "3.1 YPC — Alabama's worst in an Iron Bowl since 2013." Data source: gamelog vs historical distribution for this program in this rivalry / this opponent-type.

2. **Echo** — A pattern in the game that rhymes with an earlier season. E.g., "The second half looked like 2019 at Auburn." Data source: cosine similarity between this game's in-game flow features (WP shape, scoring cadence, split margins) and prior seasons' defining losses from historical_season archive.

3. **Retroactive** — A card framing from earlier this season whose meaning has been overturned by today's result. E.g., "The O-line concerns we wrote off after LSU came back today." Data source: team_chronicle_observations for this team this season + the new game's tape.

### 3.2 Generation

Route through the Chronicle pipeline from the Chronicle Rebuild sprint. Only addition: a `game_edition=True` flag that:
- Restricts candidates to the just-ended game's evidence
- Tightens the date window to T-24h through T+30min
- Requires the attribution field to cite a specific play / quarter / stat from the game, not a season-level source

### 3.3 Cohort-divergence bonus card (stretch)

If fan-intel has cohort divergence data for this game (analytics cohort vs. casual-vibes cohort reading the same game differently), consider a 4th game-edition card of type `divergence`:

> **The analytics room and the bar saw different games.**
> The analytics cohort spent the second half noting that Bama's defensive EPA was still positive — that they were getting stops on a per-play basis and Auburn was winning with field position, not execution. The casual cohort spent it watching the score. Both are right. Only one is comfortable.

Only generate this card when fan-intel has enough signal to warrant it (effective_n ≥ 100 on both cohorts).

### Self-verification Phase 3

- For mock Alabama–Auburn 24-31 loss: generate 3 game-edition cards. Paste into chat for Beat-Writer Test.
- Run validation gate: each card must cite a specific play/quarter/stat, pass the banned-phrase check, and attribute correctly (e.g., "gamelog · Iron Bowl 2025 · Q4 breakdown" is acceptable).

---

## Phase 4 — Offseason rehearsal harness

We have no real games for 4 months. Build a simulation tool so we rehearse now.

### 4.1 Simulate-game CLI

New subcommand: `python manage.py simulate-game`

```
python manage.py simulate-game \
    --home alabama --away auburn \
    --final-home 24 --final-away 31 \
    --wp-curve mock-close-loss.json \
    --events-log mock-iron-bowl-events.json \
    [--persist]
```

Behavior:
1. Inserts a row into `games_live` with status='final', the final score, mocked WP curve, mocked events log
2. Flips state_resolver for both teams to `game-recap-<outcome_category>`
3. Runs the full T+5 through T+45 pipeline against the mocked game
4. Renders both team pages into `output/site/teams/<slug>.html`
5. If `--persist`, leaves the mock in the DB for visual inspection; otherwise marks it `simulated=true` in a column so it's filterable out of production queries

### 4.2 Mock WP curves and events logs

Create `tests/fixtures/mock_games/` with 5 ready-to-run scenarios matching the 5 outcome categories:
- `mock-win-clear.json` — ND beats Rice 45-3, WP stays above 80% all game
- `mock-win-upset.json` — UMass beats Oklahoma State 27-24 in OT, WP swings wildly
- `mock-loss-close.json` — Alabama loses to Auburn 24-31 (Figma scenario), WP peaks at 88% then collapses
- `mock-loss-blowout.json` — ND loses to OSU 14-45, WP under 30% by Q3
- `mock-loss-upset.json` — Georgia loses to Vanderbilt 17-20, no WP above 40%, late Vandy FG

Each fixture is realistic enough to exercise the full pipeline.

### 4.3 Rehearsal report

After `simulate-game` runs, print:
- State resolved to: `game-recap-loss-close`
- Hero rendered: GameRecapHero (Alabama variant, coral accent)
- state_of_team paragraph (Opus) — length, voice register, word count
- Diagnosis stats selected (4 stats, bands)
- Chronicle cards generated (3 cards, types, validation pass/fail)
- CFP math revised: pre % / now % / if-win-out %
- Token usage for this simulation

### 4.4 Offseason rehearsal test plan

Run all 5 scenarios against all 11 programs that have those outcomes plausibly (some programs would not upset a Tier-1 opponent realistically — that's fine; skip those).

Full test matrix: ~35 simulated game runs. Token budget per simulation: ~15k (Opus state-of-team + 3 Chronicle Opus-or-Sonnet + pipeline). 35 × 15k ≈ 525k. Cut scope if tight — run 5–10 of the highest-judgment scenarios and leave the rest for human-triggered tests.

### Self-verification Phase 4

- All 5 mock fixtures execute end-to-end without errors
- Resulting HTML renders match the Figma mockup structurally
- No banned-phrase leakage in any generated copy
- Rehearsal report is complete and parseable

---

## Decision authority

Autonomous on: exact WP annotation selection heuristics, diagnosis-stat ranking weights, mock-fixture content, variant accent tuning.

Stop and flag only if:
- The Pulse Wire-Up or Chronicle Rebuild infrastructure hasn't landed yet — if grep shows those sprints incomplete, stop and report
- `games_live` schema doesn't match what CFBD's live-game endpoint returns — propose revisions, stop
- Any outcome category's state_of_team paragraph (Opus output) reads off-voice for blue-blood programs — flag and stop
- Token usage approaches 400k mid-run — pause, report, check

---

## Report back with

1. **Phase 1** — migration + state_resolver update confirmation; mock final-state row test per outcome_category
2. **Phase 2** — Alabama-vs-Auburn mock render compared side-by-side to Figma mockup. Screenshots. State-of-team paragraphs generated for all 5 outcome categories × 3 voice-contrast programs (Alabama, ND, UMass) — paste all 15 paragraphs for Kevin's Beat-Writer Test
3. **Phase 3** — 3 game-edition Chronicle cards for the Alabama mock. Validation pass/fail. Beat-Writer Test input.
4. **Phase 4** — all 5 mock fixtures' rehearsal reports. Token usage per fixture.
5. Total token usage by phase + model. Validate Opus cost is <25% of total.
6. Natural next: typically either (a) broader simulation across all 11 programs to stress-test voice at volume, (b) the post-24h transition page (day 2 after game — how does the page look then?), or (c) live-game in-progress mode (pre-final states).

Report at end, not between phases. Good luck.
