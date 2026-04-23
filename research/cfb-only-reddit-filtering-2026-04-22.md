# CFB-Only Reddit Filtering Audit

Last updated: April 22, 2026

## Purpose

This memo captures the current state of the Reddit fan-source collector after tightening it toward `college football only`.

The product requirement is now explicit:

- keep the site `CFB only`
- avoid obvious leakage from basketball, baseball, softball, or generic campus chatter
- do not overconstrain school subreddits so hard that we throw away most real offseason football conversation

## What changed locally

We added:

- a Reddit-specific CFB relevance gate in `src/cfb_rankings/conversation_utils.py`
- stronger cleanup so re-running the collector replaces old `query-match` and `source-prior` target rows for the same source scope
- source-prior handling for direct school-subreddit listing pulls
- stronger rejection for:
  - off-topic / free-talk threads
  - obvious basketball shorthand such as `SF`, `PG`, `SG`, `PF`
  - obvious other-sport keywords when there is no real football anchor

## Current live test

Command run:

```bash
python manage.py collect-reddit-plan --season 2025 --week 21 --plan research\reddit-community-plan-v1.json
```

Current result:

- `53` total Reddit docs kept
- `44` kept in `fan` bucket
- `4` kept in `national`
- `5` kept in `rival`

## What now looks good

These sources currently look mostly or entirely CFB-relevant:

- `MichiganWolverines`
- `OhioStateFootball`
- `LSUFootball`
- much of `georgiabulldogs`

Representative good examples:

- `Several shots of the Maize vs. Blue Spring Game from yesterday:`
- `What do you expect to be different in terms of QB coaching at Michigan?`
- `Spring Game Recruiting Visitor List`
- `Updated Lsu Spring depth charts (offense/defense)`
- `How do you rate the QB2 battle just based on G-Day?`
- `Class of 2027 3 star edge Stevan Thornton commits to Alabama`

## What still leaks through

Despite the tighter heuristics, some clearly non-CFB or semantically ambiguous posts still survive in broad school subreddits.

Examples still present after the latest run:

- `Auburn transfer F, Elyjah Freeman, commits to Texas`
- `[Grubbs] Boise State transfer center Drew Fielder commits to Alabama`
- `Incoming Portal Athletes`
- `Who would you rank as Florida’s biggest rival in Men’s Basketball?`

Important note:

- at least one of these survives because the body text contains mixed-sport discussion that mentions football, which can fool a rule-based filter even when the post is fundamentally about basketball

## Why this is hard

The remaining errors are not just keyword errors.

They are source-prior and semantic disambiguation problems:

- `portal`
- `commit`
- `transfer`
- `depth chart`
- `season`

These can all be football, but they also appear in basketball and other sports.

For school subreddits that are not football-dedicated, a pure rules layer faces a real tradeoff:

- if we get stricter, we lose real football offseason chatter
- if we stay looser, we keep obvious non-football bleed

## Current options

### Option A: heuristics only

Keep improving regex/keyword rules and accept that some mixed-sport leakage will remain.

Pros:

- cheapest
- simplest
- no new runtime dependency

Cons:

- likely never fully trustworthy on mixed school subreddits
- easy to keep fighting edge cases forever

### Option B: heuristics first, then cheap LLM disambiguation only for ambiguous source-prior posts

Use local heuristics to:

- auto-accept obvious football posts
- auto-reject obvious non-football posts
- send only the ambiguous remainder to Anthropic

Pros:

- best precision/recall balance
- should stay within budget if only ambiguous posts are sent
- preserves school-subreddit coverage better than strict heuristics alone

Cons:

- adds a second-pass dependency
- needs a small cache / reproducibility plan

### Option C: prune the mixed subreddits for v1

Keep only the clearly football-leaning sources for now and drop the broadest mixed subs until later.

Pros:

- cleanest v1 data
- simple to operate

Cons:

- less coverage
- may lose some fun team-specific offseason chatter

## Question for Anthropic

For a `CFB-only` fan product with a `~$50/month` budget and a `Python + SQLite + static-site` workflow:

- Which of the three options above is the best v1 choice?
- If the answer is `Option B`, what is the cleanest way to define `ambiguous` so costs stay low and the system stays understandable for a non-technical operator?

## Anthropic answer

The latest Anthropic review is saved at:

- `output/anthropic-cfb-only-filtering-review.md`

Bottom line from that review:

- long-term best path: `Option B`
- practical v1 move right now: keep local heuristics first, keep the ambiguous volume small, and stay operationally simple
- cost discipline recommendation: keep the Anthropic slice narrow and cap it hard rather than trying to semantically classify the entire corpus

## Current repo recommendation

For this repo today, the cleanest operational compromise is:

1. use the stronger local CFB-only heuristics now
2. use the narrower source set in `research/reddit-community-plan-cfb-safe-v2.json` for the live site
3. add an Anthropic ambiguity pass only after we decide we need broader school-subreddit coverage than the safe v2 plan can provide
