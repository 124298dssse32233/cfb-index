# Octopus Next-Roadmap — Make CFB Index Addictive for Data-Native Fanatics

_Dated 2026-05-12. Follows the Octopus audit at `docs/octopus/discover.md` + `define.md` + `deliver.md`. Two-provider research (Codex + Gemini) folded into one ranked roadmap, plus three original picks Claude is adding._

## Reader's prompt

You came back to CFB Index on a Wednesday in May. Indiana is your team. You want to know:

- _How does my team's season compare to its own decade?_ Currently → no single visual answers this.
- _Who's running away with the Heisman this week?_ Currently → a 14.99 MB board you scroll endlessly.
- _Which game on Saturday will matter the most — not just have the best teams?_ Currently → no slate that ranks games by narrative volatility.
- _Which fanbase had the biggest vibe shift this weekend?_ Currently → `/reactions/` has post-game blurbs, but no ranked ledger of the week's mood deltas.
- _Are we tracking like a CFP run, or like 2012 Indiana?_ Currently → no comp engine.

Every feature below is named **because that question has no current good answer on the site.**

## Operating principles

1. **Static-first.** Most viz here is server-rendered SVG. JS only where interaction genuinely compounds.
2. **One template engine, many outputs.** A single share-card renderer powers Game Day, Vibe Shift, Heisman Path, Respect Gap. Build it once.
3. **The model is the moat.** Don't ship anything ESPN/On3/247 ships. Lean into Power+Resume splits, fan-intel cohorts, four-division universe.
4. **Weekly rituals make habits.** Each feature gets a day-of-week assignment so a fan can plan to come back.

---

## The roadmap, ranked

Each feature: **affordance**, **data + status**, **where it slots in**, **why a fan returns weekly**, **why ESPN/On3/247/PFF/SP+ don't ship it**, **rough effort**.

### R1. 🥇 Sunday Vibe Shift Ledger _(Codex's #1 pick, agreed)_

**Affordance.** A weekly post-game ledger at `/hub/vibe-shifts/<season>/<week>/` with ten ranked cards: "Biggest belief gain," "Biggest belief loss," "Hottest take," "Worst loss arc," "Best win arc," each as a single shareable image (PNG + OG-card) with before/after Power, Resume, and Fan Pulse.

**Data.** `team_rating_deltas` (318,500 rows ✅), `team_game_conversation_features` (1,441 rows 🟡), `fanbase_mood_weekly` (62 rows 🟡 thin but growing), `games` (27,515 rows ✅), `team_aliases` for OG image branding. Ledger generator runs at `MODEL_WEEK + 1`, lands the cards by Sunday morning.

**Slots in.** New section under `/hub/`. Each card cross-links to:
- `/reactions/<team>-<game>/` for the game blurb (route already exists)
- The team page's Game Impact Board for context
- `/storylines/<thread>` if the team is in an active narrative thread

**Why fans return weekly.** Sunday morning is when fans relitigate Saturday's emotional damage. A ranked ledger of "who changed the most" is exactly the artifact CFB Twitter trades on Sunday-Tuesday. The card produces a single image worth screenshotting.

**Why nobody else ships it.** ESPN recaps the games; PFF grades the snaps; nobody quantifies how _the season's emotional reality_ changed. This is the product CFB Index uniquely can ship because of the fan-intel layer.

**Effort.** 1 week. Bulk of work is the share-card SVG renderer (reusable across R5, R6, R7).

---

### R2. 🥈 Saturday Watch Board _(Codex)_

**Affordance.** New page at `/watchlist/<season>/<week>/`. Every FBS-relevant game ranked by **narrative volatility** = weighted blend of (upset risk, model–market disagreement, weather weirdness, mood combustibility, cohort divergence, conference-race stakes). Each row has a one-sentence "why this matters" + a link to `/matchups/<a>-vs-<b>`.

**Data.** `games`, `game_predictions`, `game_lines`, `game_weather` (14,711 rows ✅), `power_ratings_weekly`, `resume_ratings_weekly`, `team_cohort_week`, `team_cohort_divergence_week` (2,830 rows ✅). All present.

**Slots in.** Top-level `/watchlist/`. Linked from homepage, `/matchups/`, and `/daily/`. Friday night + Saturday morning are the visit times.

**Why fans return weekly.** Every CFB fan asks "which games matter this weekend?" on Friday. No site answers that with a real model-aware narrative score — they all show schedule + odds + projection separately. This collapses those into one sortable, opinionated slate.

**Why nobody else ships it.** ESPN's "Saturday slate" is editorial. SP+ ranks by projection only. CBS's slate has odds. None of them rank by _narrative volatility_, because none of them have a fan-intel layer to model "mood combustibility."

**Effort.** 1.5 weeks. The combustibility score itself is the hard part — needs a small ranking-of-rankings pass on six input signals.

---

### R3. 🥉 Season Doppelganger _(Codex + Gemini both surfaced)_

**Affordance.** On every team page, a new module under "Program Arc" that says:

> _"Through Week 11, 2025 Indiana is tracking most like:_
> _① 2014 TCU (final: #6 AP, no playoff), similarity 0.91_
> _② 2017 UCF (final: #6 AP, undefeated), similarity 0.88_
> _③ 2021 Cincinnati (final: CFP semi loss), similarity 0.86"_

With trajectory overlay — three faint "ghost" lines on the season rating arc chart.

**Data.** `power_ratings_weekly` (575k rows ✅), `resume_ratings_weekly` (520k rows ✅), `team_rating_deltas` (318k rows ✅). The similarity-comp infrastructure already exists for `_render_reminiscence_cards` — extend the same kernel to in-season-trajectory matching instead of end-of-season profiles.

**Slots in.** Profiled team pages (17 slugs) and legacy team pages (662 slugs). Replaces the "Reminiscence" / "Comp" cards on team pages with a richer, in-season-aware version.

**Why fans return weekly.** The comp shifts every week. "Last week we tracked like 2017 UCF; this week we slid to 2014 TCU" is a hookable update. It's a way of telling the fan the model's forecast _emotionally_, not just as a number.

**Why nobody else ships it.** Sports Reference stores history; nobody turns history into a live mirror. ESPN's "FPI" doesn't have an in-season comp engine. SP+ doesn't comp.

**Effort.** 1 week using existing similarity kernel.

---

### R4. Dynasty Heatmap _(Gemini)_

**Affordance.** New page at `/history/heatmap/`. A grid: programs on y-axis (FBS ~130), years on x-axis (1970–present), each cell colored by that team-season's final Power Rating percentile. Warm = dominant, cool = irrelevant. Hover/tap a cell → tooltip with record, conference rank, postseason result. **One image, fifty years of CFB.**

**Data.** Historical season summaries already feed `/history/`'s "Best By Level / Greatest Loaded Seasons / Closest To Program Peak" surfaces — same underlying data, new visualization. May need a backfill to extend to 1970 if data only goes to 2014.

**Slots in.** Linked from `/history/` as the headline visual. Also embedded above the program-arc on every team page.

**Why fans return weekly.** This isn't a weekly-return feature — it's a **first-visit converter**. A new visitor sees this and immediately understands the site is serious about history. Returns happen via deep-linking from social: every CFB era takes ("Miami in the 80s" / "USC in the Carroll years" / "Alabama's reign") generate share-traffic.

**Why nobody else ships it.** Sports Reference has the data but won't ever ship a viz this opinionated. ESPN doesn't think historically. The Athletic has the editorial chops but lacks the model.

**Effort.** 1 week to render, possibly longer if backfill is needed.

---

### R5. Game Day Cards _(Gemini's #1 pick)_

**Affordance.** For every FBS game, auto-generated pre-game shareable image (`<og:image>` + a `/share/games/<a>-vs-<b>.png`). Vertical card with: Team A helmet vs Team B helmet, model win probability, Vegas line, fan mood deltas, one-line "the case for each side" copy. Screenshottable.

**Data.** `games`, `game_predictions`, `game_lines`, `fanbase_mood_weekly`, `team_brand_assets`. All present (1,305 rows in `team_brand_assets`).

**Slots in.** Generated as part of weekly build. Used as `<og:image>` on `/matchups/<a>-vs-<b>`. Also published to `/share/games/` so fans can grab the raw image. Eventually a Twitter/X bot can post them automatically.

**Why fans return weekly.** Game day mornings, every fanbase reaches for "the case for us." A clean, model+market+mood card lands that reach. Fans share → fans see CFB Index wordmark → fans visit.

**Why nobody else ships it.** ESPN's pregame cards don't carry a model+market+mood triad. The Athletic doesn't auto-generate. Twitter/X bots from ESPN are reach-of-net-but-low-signal.

**Effort.** 1 week. Shares the SVG renderer with R1.

---

### R6. Respect Gap Scoreboard _(Gemini's #7, promoted from card to standing page)_

**Affordance.** A standing page at `/respect-gap/`. Every FBS team ranked by **|own_fan_belief − national_belief|**. Top 10 "Underrated" (own fans more bullish than national), top 10 "Overrated" (national more bullish than own fans), filterable by conference. Click into any team → a paragraph and a chart showing the gap movement over the season.

**Data.** `team_week_conversation_features` (2,019 rows ✅), per-cohort sentiment splits already computed.

**Slots in.** Top-level `/respect-gap/`. Linked from `/hub/` and from the team page's Mood Card. A weekly snapshot also publishes a share card (top 5 of each list).

**Why fans return weekly.** Every fanbase wants to know "where do we rank in this leaderboard?" — both flavors. It's the closest thing CFB has to a moral-scoreboard.

**Why nobody else ships it.** ESPN/CBS/Fox don't have the fan-intel data. PFF doesn't do fan sentiment. This is the leaderboard nobody else can build, and it's where the fan-intel investment pays off most visibly.

**Effort.** 0.5 weeks (data already computed).

---

### R7. Player Stat Wormholes _(Codex)_

**Affordance.** Every percentile chip on a player page (`#14/367 (96th pct)`) becomes a click target → opens a lightweight modal/sheet showing:
- Top 10 in this stat
- Closest 4 players to this player in the cohort
- Closest historical comp (across seasons in the archive)
- A share card for this stat

**Data.** `player_season_stats` (1.16M rows ✅), `player_game_stats` (4.58M rows ✅), `player_advanced_metrics` (177k ✅). All present.

**Slots in.** Player pages — turns existing chips into entry points. No new top-level routes.

**Why fans return weekly.** Stat-chasing is the most addictive CFB behavior of all. "Who's ahead of my QB in YPA?" is the chip-click. Every chip becomes a rabbit hole that returns to another player page → time on site compounds.

**Why nobody else ships it.** PFF gates grades behind a paywall. ESPN lists stats without context. Sports Reference does percentiles but no in-cohort modal.

**Effort.** 1 week. The data is dense; the UX choice is "modal vs. dedicated page" — I'd go modal for first iteration to keep total route count bounded.

---

### R8. The NFL Pipeline _(Claude — original)_

**Affordance.** Per program, a new module at the bottom of the team page (and a top-level `/nfl-pipeline/` overview page): "**[Program] sent N players to the NFL in 2014-2025, ranked by round and longevity.**" Visual: a draft-class scatter where the y-axis is NFL longevity (years), the x-axis is the year drafted, dots colored by round (Day 1/Day 2/Day 3/UDFA). Top-of-page summary: avg picks per year, picks-per-recruiting-class ratio, hit-rate by class.

**Data.** `player_nfl_draft` (3,077 rows ✅). Currently unused by any user-facing surface I could find.

**Slots in.** Team pages (new module). New top-level `/nfl-pipeline/` page that ranks all 130 FBS programs by 12-year NFL output. Linked from the homepage.

**Why fans return weekly.** During the season, less so. During April-May (draft) and August (NFL preview), enormous. This is the offseason mode the site is missing.

**Why nobody else ships it.** 247 does recruiting trajectories. PFF rates current college players. On3 does NIL valuations. NFL.com does the draft itself. **Nobody connects the recruiting class → on-field performance → NFL pipeline as one program-level story.** That's the gap.

**Effort.** 1 week. Data is clean; viz is a single scatter + a table.

---

### R9. Recruit-vs-Result Delta _(Claude — original)_

**Affordance.** A program-level chart that overlays two lines:
- The program's recruiting class ranking by year (from `recruiting_entries`)
- The program's final Power Rating ranking that same year

The gap shows "outperformed talent" (Indiana, James Madison) or "underperformed talent" (USC, FSU, Texas A&M at various points). A small badge on the team page header reads: **"Talent ROI: +12 since 2019"** (positive = beating recruiting expectations) or "Talent ROI: -8".

**Data.** `recruiting_entries` (1,885 rows 🟡 — thin per-program, ~3 years per FBS team), `power_ratings_weekly` (575k ✅), `resume_ratings_weekly` (520k ✅).

**Slots in.** Team pages (header badge + a new chart module). Linked from `/history/` and `/about-model/` as a "what the model sees that recruiting rankings don't" callout.

**Why fans return weekly.** Recruiting is a year-round religion. A "your team is over/underperforming its recruiting class" badge is identity-forming. Off-season fuel.

**Why nobody else ships it.** 247 ships the recruiting; nobody ships the **delta**. The delta is the interesting number — it's what reveals coaching/development as a measurable variable.

**Effort.** 1.5 weeks. Cleaning the recruiting data thin spots is the hard part.

---

### R10. Receipts Court _(Codex — but downgraded)_

**Affordance.** A weekly page at `/receipts/<season>/<week>/` that grades the site's own preceding-week takes (model picks, Heisman board predictions, daily takes) against what actually happened. Verdicts: ✅ aged well, 🤡 aged poorly, 😐 neither.

**Data.** Route `/receipts/` exists but underlying claim store is sparse. `daily_takes` only has 21 rows; `predictive_claims` empty. **This feature isn't ready until the claim-emission infrastructure populates more.**

**Status.** **Defer for 4–6 weeks** until the daily/wire/edition pipelines have enough volume to score. Reopen once `daily_takes` and the prediction stores have ~200+ rows of season-long takes to grade. The page should ship with maybe one season's worth of receipts to feel substantial.

---

## Provider disagreement, preserved

Codex picked Sunday Vibe Shift Ledger as #1. Gemini picked Game Day Cards as #1. **Disagreement reflects a real product question:** is the priority for a fan _Sunday post-mortem_ (Codex) or _Saturday pregame_ (Gemini)?

My read: Sunday Vibe Shift Ledger wins on cold-start because (a) it's higher-margin editorially (it tells a fan something they don't know yet about what happened to their team's reality), and (b) the share-card renderer it requires powers Game Day Cards for free as a side effect. Build R1 first, then R5 nearly comes for free. **Ranking reflects this.**

Codex omitted the Dynasty Heatmap and 30-Game Form Chart; Gemini omitted Saturday Watch Board, Rivalry Heat Pages, Player Stat Wormholes. Neither suggested NFL Pipeline or Recruit-vs-Result Delta. Both gaps were legitimate, hence Claude's additions.

## What I dropped from the providers' lists

- **30-Game Form Chart (Gemini #1).** Useful but redundant with the Season Doppelganger trajectory overlay. Doppelganger does the work + adds the comp narrative; just one chart wins over two.
- **Rivalry Heat Pages (Codex #5).** Concept is right but the underlying `rivalry_obsession_weekly` table has only 41 rows. Build the dataset first; a dedicated page is premature.
- **Wednesday Heisman Path Cards (Codex #2).** Worthy but better unlocked AFTER M-2 (Heisman page virtualization) lands. Otherwise the Path Cards link into a 15MB page; UX is dead-on-arrival.

## Sequencing — 8-week sprint plan

| Week | Build | Reuses |
|---|---|---|
| 1 | R1 Sunday Vibe Shift Ledger + share-card SVG renderer (core dependency) | — |
| 2 | R5 Game Day Cards | R1's share renderer |
| 3 | R3 Season Doppelganger | Existing similarity kernel |
| 4 | R6 Respect Gap Scoreboard | Existing cohort data |
| 5 | R2 Saturday Watch Board | — |
| 6 | R8 NFL Pipeline | — |
| 7 | R4 Dynasty Heatmap | — |
| 8 | R9 Recruit-vs-Result Delta | — |

R7 (Player Stat Wormholes) and R10 (Receipts Court) are queued for the following sprint, contingent on data volume.

## What this looks like at the end

After this roadmap ships, a CFB fan's weekly visit cadence becomes:

- **Mon-Tue:** Read `/hub/vibe-shifts/` (Sunday's ledger), share the card for your team
- **Wed:** Heisman board (after M-2 lands) and any movement in Season Doppelganger
- **Thu:** Look at the Saturday Watch Board, queue games
- **Fri:** Glance at the `/respect-gap/` page; argue with friends
- **Sat:** Open Game Day Cards in group chats; refresh `/watchlist/` between games
- **Sun morning:** Open the new Vibe Shift Ledger and start the loop again

Compared to a fan's current weekly cadence (visit homepage, scroll, find nothing fresh) → that's a 7x return frequency.

That is what "addictive" looks like on a site whose moat is a model, not a video team.

---

## Cross-references

- `docs/octopus/discover.md` — current-state audit (Phase 1)
- `docs/octopus/define.md` — fix charter (Phase 2)
- `docs/octopus/develop.md` — what was shipped (Phase 3)
- `docs/octopus/deliver.md` — adversarial review + scoring (Phase 4)
- `OCTOPUS_AUDIT_2026-05-12.md` — 2-min summary at repo root

Deferred items not consumed by this roadmap (still open):
- M-1: real fan-intel entity matching (defensive guard shipped; NER + alias lookup still owed)
- M-2: Heisman board virtualization (R2/R3 don't block on it, but Wednesday Heisman Path Cards do)
- A-1: converge or freeze the two team-page renderers
- A-2: `/teams/` vs `/programs/` consolidation
- A-3: `reporting.py` decomposition
- A-4: repo root cleanup
