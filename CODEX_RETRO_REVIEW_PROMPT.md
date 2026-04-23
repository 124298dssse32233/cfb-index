# Codex — Second-Opinion Review Prompt

## Who you are on this task

You are an independent senior engineering reviewer looking at a plan for a new feature in someone else's codebase. You have not been part of the planning conversation. Your job is to pressure-test the plan against the actual code before it gets implemented, so implementation doesn't start from a wrong premise.

**You are not implementing.** Do not write production code. Do not edit files under `src/` or `output/`. Draft small code snippets only inline in your review to illustrate a specific point.

**You are not rewriting.** If the plan is mostly right, say so and point at the specific things to tighten, not a full redo.

**You are adversarial in service of accuracy.** The product's entire value proposition is that its published numbers are defensible. Your job is to find every place the plan produces numbers that look real but aren't, or claims the code can do something it can't.

## What the project is

Static-site college-football rankings + fan-intelligence product. Python generator → SQLite → ~17k HTML pages under `output/site/`. Full project orientation is in `CLAUDE.md` at the repo root — read it first. Two things to internalize:

- Data keying is split: conversation features use integer `(season_year, week)`; Hub v5 features use date-string `week_start_date`. This split is real and intentional.
- Editorial voice lives in publication-final Python dicts (see `src/cfb_rankings/ingest/hub_data.py`'s `ISSUE_047`). "Seed" and "compute" are two distinct runtime paths into the same tables.

## The task the plan is for

The user wants to publish a **retroactive weekly offseason magazine** covering Jan 19 (CFP Championship) through Apr 22 (today). Ten issues, mirroring the existing Issue N° 047 format. Every number on every page has to be either computed from live data or clearly tagged editorial-seed — no made-up-looking numbers dressed as real stats.

## Files to read, in order

### The three planning memos (read these, then review them)

1. `research/retro-offseason-content-plan-2026-04-22.md` — the editorial/week scaffold and data-model implications. First pass.
2. `research/retro-offseason-accuracy-and-seeding-plan-2026-04-22.md` — formulas and calibration. Second pass. Some parts superseded by the third pass.
3. `research/retro-offseason-execution-plan-2026-04-22.md` — corrected formulas (SQL over `team_week_conversation_features`), new-code module map, Phase A vs Phase B split. **This is the canonical brief; evaluate this one most carefully.** The earlier two are context for how we got here.

### Code files to cross-reference (do not modify)

Only read the specific line ranges indicated or use `rg` to find the symbols. **Do not read `src/cfb_rankings/reporting.py` whole — it's 17.5k lines.**

- `CLAUDE.md` — project orientation + key line numbers for reporting.py.
- `src/cfb_rankings/fan_intelligence.py` — read fully (~935 lines). The v1 mood card pipeline. Pay attention to `fetch_team_mood_profile`, `fetch_fan_intel_board`, `_belief_from_row`, `_reality_gap`, `_respect_gap`, `_cohesion_from_row`, `_swing_from_history`, `_rival_heat`, `_empty_profile`, and the constants `MIN_MENTIONS_FOR_SIGNAL`, `MIN_AUTHORS_FOR_SIGNAL`.
- `src/cfb_rankings/ingest/conversation.py` — read fully (~1293 lines). Reddit collector + feature builder. Pay attention to `collect_reddit_watchlist`, `collect_reddit_subreddit_listing`, `build_conversation_features`, `_build_watchlist`, and how `(season_year, week)` keys flow through.
- `src/cfb_rankings/clients/reddit.py` — read fully (194 lines). The unauth'd Reddit client with RSS fallback. This is the object the Pullpush adapter in Phase B must match the interface of.
- `src/cfb_rankings/conversation_utils.py` — read `score_sentiment`, `is_probably_cfb_reddit_post`. The plan's sentiment math depends on `score_sentiment` returning a VADER compound score in `[-1, 1]`.
- `src/cfb_rankings/ingest/hub_data.py` — read fully (~614 lines). Issue N° 047 seed data, the three seed loaders (`seed_mood_week`, `seed_rivalry_week`, `seed_lexicon_week`), and the fetchers. This is the file `hub_data_retro.py` will mirror.
- `src/cfb_rankings/cli.py` — read the full file (~1236 lines). Confirm exactly which CLI subcommands exist today and where `compute-mood-week` / `compute-rivalry-ratios` / `mine-lexicon` dispatch to (they currently only run the seed path — verify this at lines ~1276-1302).
- `research/cfb-data-schema-sqlite.sql` — grep for `team_week_conversation_features`, `team_conversation_daily`, `conversation_storylines`, `fanbase_mood_weekly`, `rivalry_obsession_weekly`, `lexicon_weekly`, `hub_issue_metadata`. Confirm column lists match the formulas in the execution plan.
- `research/offseason-publishing-queue-and-build-order-2026-04-22.md` — the forward calendar (Apr 22 → kickoff). Context only; do not re-plan the forward calendar.

## What I want you to evaluate

### Pass 1: compatibility

For every claim in `retro-offseason-execution-plan-2026-04-22.md`, decide: **true, false, or partially true** against the actual code. Report only the ones that are not fully true. Specifically:

1. Does every SQL formula in §"Revised formulas" reference columns that actually exist in `team_week_conversation_features` / `team_conversation_daily` / `power_ratings_weekly` / `model_runs`? Name any column that doesn't exist or has a different name.
2. Are the three "new columns" the plan proposes to add to `team_week_conversation_features` (`pro_coach_count`, `anti_coach_count`, `rival_mention_count`) the minimal set to support the formulas, or is there already a column the plan could reuse? Check the emotion-share columns (`anger_share`, etc.) — can `anger_share` substitute for an anti-coach count in some cases?
3. The plan claims `compute-mood-week`, `compute-rivalry-ratios`, `mine-lexicon` all currently only run the seed path. Verify by reading `cli.py:1276-1302`. Report if this is off.
4. The plan claims the Reddit client cannot reach Jan 19 posts from April. Verify by reading `clients/reddit.py` — confirm or refute.
5. The plan claims `build_conversation_features`'s pregame/postgame windowing will cleanly produce zero game-level rows for offseason weeks with no games, while still producing team-week rows. Verify by reading `build_conversation_features` end-to-end.
6. The plan specifies a new `retro-calibrate` subcommand with ten directional checks. For each check, confirm the data source needed exists (or can be built in Phase B) before the check could run.

### Pass 2: accuracy

Find the places where the plan will produce numbers that *look* computed but aren't defensible. Examples of what I mean:

- A formula that divides by a potentially zero denominator with no guard.
- A percentile rank computed over a too-small population (e.g., only 8 FBS teams have data that week).
- A lexicon spike threshold that will fire on Reddit outages (volume drops → baseline collapses → any signal looks like a spike).
- A Shock Index window that straddles a timezone boundary and double-counts a day.
- A coach-aliases regex that matches a player name (e.g., "Kelly" the coach vs. "Kelly" the WR).

Be specific — file + function + line where possible. If the plan doesn't specify code yet (because it's a plan), name the risk as a pre-implementation caveat the implementer must handle.

### Pass 3: the P0/P1 split

The plan separates Phase A (seeded-only, ships this week) from Phase B (computed, ships in 2–3 weeks). Pressure-test this:

- Can Phase A actually ship this week with the stated 1-day engineering budget? What in the new-code map is underestimated?
- If Phase B is delayed indefinitely (or doesn't pass calibration), does Phase A still stand alone as an honest product? Or does Phase A accidentally imply claims Phase B was supposed to back up?
- The plan says provenance badges switch from "Editor" to "Live" when Phase B lands. Is this reversible if a post-hoc correction is needed? What happens to the issue if one team's numbers fail calibration but the rest pass?

### Pass 4: what's missing

Name up to 5 things the plan doesn't address that it should. Examples of what might be missing:

- Search-engine indexing policy for retro pages (do we want Google showing these as "current"? They're retroactive).
- Caching / CDN invalidation when Phase B overwrites Phase A numbers.
- Editorial review workflow for lexicon-discovery candidates.
- Monitoring / alerting on Pullpush rate-limit errors during the backfill.
- An escape hatch for a team or week we have to pull entirely (e.g., if Michigan fans brigade a subreddit and skew the numbers).

If you think of no more than 1–2 gaps, report only those. Don't pad.

### Pass 5: model routing for implementation

The repo has a model-routing convention in `CLAUDE.md`: Sonnet default, Opus for schema/data decisions and cross-cutting copy, Haiku for verification and grep sweeps via subagents. Given the task list in the execution plan's new-code map, recommend which tasks are best routed to which model. Flag any task where the default (Sonnet) is wrong.

## Output format

Return a single markdown document with these sections in this order:

```
# Retro Offseason Plan — Review Findings

## Verdict
One sentence: ship as-is / ship with changes / do not ship.

## Compatibility gaps
Table with: claim | reality | file:line | severity (blocker|major|minor).
Only list mismatches. If everything lines up, write "none found."

## Accuracy risks
Bulleted list. Each bullet names the formula / code path + the risk + a one-line mitigation.

## P0/P1 split review
~200 words. Is Phase A shippable alone? What does Phase B gate on?

## Gaps
Up to 5 things the plan doesn't address. One paragraph each.

## Model routing
Table with: task | recommended model | reason. Only list tasks where default Sonnet is wrong.

## The one thing I'd change first
One paragraph naming the single highest-leverage change to make before any code is written.
```

Keep the whole review under 1,500 words. If you need to go longer, you're padding.

## Ground rules

- Every claim in your review needs a concrete anchor: file path + line number, or SQL column name from `research/cfb-data-schema-sqlite.sql`, or a CLI subcommand name from `cli.py`. No hand-waving.
- If you haven't read a file and the claim depends on it, say "not verified against source" rather than guessing.
- Do not invent CFB events or facts. The sources in the research memos are the source of truth for what happened between Jan 19 and Apr 22, 2026. If you want to argue an event is wrong, cite a counter-source; otherwise trust the memos' event ledger.
- Do not propose renaming the feature, changing the editorial voice, or restructuring the ten-issue scaffold. Those decisions are settled. Review the *execution*, not the *concept*.
- If you find a blocker, stop and report it before continuing. A single blocker saves more time than ten polish notes.

## Why this review matters

The existing `CLAUDE_CODE_FIX_PROMPT.md` in this repo is the house style for prioritized implementation briefs (P0-P3). Your review feeds into a successor brief. Anything you flag as a blocker gets fixed in the plan before P0 code is written. Anything you flag as a minor polish gets batched into P2 or P3.

Don't be diplomatic. Be specific.
