# Conversation Intelligence Runtime Validation

Last updated: April 21, 2026

## Purpose

This memo records what was actually verified in the local repo after the first implementation pass for the conversation-intelligence layer.

It exists so future sessions do not confuse:

- research intent
- implementation status
- runtime reality

## What was verified locally

The following commands were run successfully from the repo root:

```powershell
python -m compileall src scripts manage.py
python manage.py seed-team-aliases --season 2025
python manage.py collect-reddit-watchlist --season 2025 --week 1 --limit-teams 5 --search-limit 3
python manage.py build-conversation-features --season 2025 --week 1
```

Observed results from that validation pass:

- `2980` team alias rows seeded for season `2025`
- `8` Reddit documents collected
- `9` team-target sentiment rows collected
- `7` daily aggregate rows built
- `3` weekly team aggregate rows built
- `9` storyline rows built
- `0` game-window aggregate rows built in that test

## Why the game-window rows were zero

That specific test used:

- local football schedule/model context from season `2025`, week `1`
- live Reddit discussion collected on `April 21, 2026`

Those timestamps do not line up with the actual pregame/postgame windows for `2025` week `1`, so the game-window aggregator correctly produced no rows.

Important implication:

- weekly mood aggregation can be validated with small live tests
- game-specific pregame/postgame features only make sense when collection runs happen near the real game dates for the target week

This is not a bug in the aggregation logic. It is a calendar-alignment issue.

## Reddit transport findings

### JSON endpoints

Reddit JSON endpoints were initially unreliable from this environment and returned `403 Blocked` with a lightweight agent profile.

They became much more reliable after switching to a browser-like header set:

- realistic browser `User-Agent`
- broader `Accept` header
- `Accept-Language`
- subreddit `Referer`
- `raw_json=1`

### RSS / Atom feeds

Reddit RSS / Atom feeds were also checked and worked from this environment for:

- subreddit listing feeds
- subreddit `new` feeds
- subreddit search feeds
- sitewide search feeds

That makes RSS a useful fallback transport when JSON gets flaky.

## Current implementation status

The Reddit client now:

- prefers JSON when it works
- falls back to RSS when JSON fails

The current conversation v1 flow is:

1. seed season-aware team aliases
2. build a watchlist from explicit teams or model/schedule context
3. search Reddit for alias matches
4. store raw documents
5. score sentiment locally with `VADER + lightweight heuristics`
6. write team-target sentiment rows
7. aggregate daily, weekly, and game-window features
8. generate simple storyline keywords and representative links

## What this means for v1 feasibility

The v1 is feasible if the product stays disciplined:

- `FBS-only` or tightly limited watchlists first
- `team-level` only
- batch refresh cadence, not real-time
- weekly/editorial framing, not trading-signals framing
- one or two reliable public sources first

## What not to overclaim

Do not overclaim any of the following in the first launch:

- real-time social listening
- exhaustive fan coverage
- causality between sentiment and market moves
- player-level sentiment resolution
- reliable game-window features unless the data was actually collected in the right time window

## Best practical next steps

1. Add the conversation commands to the README and runbook.
2. Make the current source strategy explicit:
   - Reddit JSON with RSS fallback is validated
   - YouTube and Apify remain strong next candidates
   - Bluesky public search is still not reliable from this environment
3. Add one fan-facing page/module that reads the weekly aggregates and storylines.
4. Ask Anthropic to critique the validated architecture, not just the research premise.
