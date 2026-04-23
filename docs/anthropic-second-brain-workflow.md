# Anthropic Second-Brain Workflow

Last updated: April 21, 2026

## Purpose

This document explains how to use Anthropic as a second-brain collaborator for this project without turning it into an expensive or context-fragile workflow.

## Add the API key

Store the key in the repo-root `.env` file:

```env
ANTHROPIC_API_KEY=your_actual_key_here
```

The Anthropic helper scripts now load the repo-root `.env` file automatically, so adding the key there is enough for the next run.

## Current Anthropic helpers

### 1. `scripts/anthropic_stats_page_review.py`

Use this when you want a critique of an already-rendered player page or stats page.

Best for:

- UX critiques
- information architecture feedback
- screenshot-aware design review

### 2. `scripts/anthropic_cfb_strategy_review.py`

Use this when you want Anthropic to review local project docs and answer a focused strategy question.

Best for:

- challenging the premise of a feature
- choosing the best v1 scope
- sharpening research questions
- deciding what outputs will delight fans

### 3. `scripts/anthropic_player_page_benchmark_review.py`

Use this when you want a screenshot-aware benchmark comparison between your player page and major sports sites.

Best for:

- side-by-side player page benchmarking
- readability audits against ESPN / CBS / FOX / Sports Reference
- deciding where your page is already winning
- deciding what still feels less trustworthy or less familiar than a major sports property
- stress-testing data-viz ideas

### 4. `scripts/anthropic_site_benchmark_review.py`

Use this when you want a screenshot-aware critique of a broader site page such as:

- homepage
- rankings page
- team page
- matchup page

Best for:

- premium-feel critique
- mobile versus desktop hierarchy review
- figuring out why the site still feels second-tier
- deciding what visual system and page structure changes matter most next

## Recommended use cases

Use Anthropic selectively for:

- product critique
- narrative framing
- prioritization
- naming and copy polish
- challenging hidden assumptions

Do **not** use Anthropic as the default processor for the entire raw text corpus.

That would be:

- unnecessarily expensive
- slower
- harder to reproduce
- worse than using local models for first-pass scoring

## Example commands

## Review the study design

```bash
python scripts/anthropic_cfb_strategy_review.py --doc research/sentiment-market-study-design-2026-04-21.md --doc research/cfb-fan-delight-viz-brief-2026-04-21.md --question "What is the strongest v1 feature set for a college football fan site that wants to compare public mood, betting markets, and model disagreement without overpromising?"
```

## Ask Anthropic to challenge the premise

```bash
python scripts/anthropic_cfb_strategy_review.py --doc research/sentiment-market-study-design-2026-04-21.md --doc docs/cfbd-tier2-and-safe-operations.md --question "Which parts of this premise are genuinely strong and which parts are fake precision given our current data and stack?"
```

## Review a rendered page

```bash
python scripts/anthropic_stats_page_review.py --html output/site/players/example-player.html --image tmp_player_desktop.png --image tmp_player_mobile.png
```

## Benchmark your page against major sites

```bash
python scripts/anthropic_player_page_benchmark_review.py --html output/site/players/example-player.html --image "Our desktop=output/player_desktop.png" --image "Our mobile=output/player_mobile.png" --image "ESPN mobile=output/benchmark_espn_player_mobile.png" --image "CBS desktop=output/benchmark_cbs_player.png"
```

## Review a site-level page

```bash
python scripts/anthropic_site_benchmark_review.py --html output/site/index.html --image "Home desktop=output/site/_smoke-home-desktop.png" --image "Home mobile=output/site/_smoke-home-mobile.png" --focus "Review this homepage like a real fan and a senior sports-product designer."
```

## Cost discipline

To keep costs sane:

- send `2-4` focused docs, not the whole repo
- ask one sharp question at a time
- keep responses strategic, not huge
- use Anthropic after local analysis has already narrowed the decision

## Best operating pattern

The best pattern is:

1. do local research and data prep first
2. write a focused project memo
3. ask Anthropic to critique the memo
4. fold the critique back into internal docs

That keeps the context durable even if the chat thread is lost.
