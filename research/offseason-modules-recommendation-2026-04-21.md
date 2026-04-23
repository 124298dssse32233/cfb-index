# Offseason Modules Recommendation

Research date: 2026-04-21

Companion files:

- `research/offseason-modules-calendar-2026-04-21.md`
- `output/anthropic-offseason-modules-review.md`

## Executive conclusion

The best offseason product from `April` through `August` is **not** a giant buffet of every possible topic.

The best product is a focused package built around three things:

1. `Roster Reality`
2. `Schedule Path`
3. `Preseason Debate`

That is the strongest overlap between:

- what fans actually revisit in the offseason
- what the current repo can support
- what a solo operator can ship without drowning

## The three evergreen page families

### 1. Roster Reality Check

This should be the centerpiece offseason family.

Core question:

- what materially changed about this team since last season?

Best ingredients from the current stack:

- returning production
- transfer entries
- recruiting entries
- roster snapshots
- preseason model priors

Best submodules:

- `What stayed`
- `What left`
- `What arrived`
- `Position-group strength shifts`
- `Continuity score`
- `Roster stability vs volatility`

Why it wins:

- it is the cleanest bridge between hard data and fan emotion
- it gives every fanbase a reason to check in
- it supports both team pages and homepage roundups

### 2. Schedule Survival Guide

This should be the second evergreen family.

Core question:

- how hard is the path, and where does the season swing?

Best submodules:

- `Path to 10 wins`
- `Trap games`
- `Swing games`
- `Backloaded vs frontloaded schedule`
- `Best and worst timing spots`
- `Playoff path difficulty`

Why it wins:

- schedule talk is one of the few universally engaging offseason topics
- it gets more relevant as the summer moves forward
- it does not require live ingestion drama

### 3. Preseason Truth Detector

This should be the main debate family.

Core question:

- what does the market say, what does the model say, and what does roster reality say?

Best submodules:

- `Market vs model`
- `Returning production vs price`
- `Overhyped vs underhyped`
- `Belief vs structural reality`
- `Most fragile contenders`
- `Most underrated rebuilds`

Why it wins:

- it creates argument fuel
- it differentiates the site from generic top-25 lists
- it naturally becomes more powerful in July and August

## The recurring card layer

Do not try to make every offseason surface evergreen and heavy.

Add two recurring card types instead.

### 1. Belief Meter

Use for:

- which teams gained or lost credibility this week
- spring takeaway changes
- depth-chart clarity
- camp news impact
- late-summer expectation shifts

This is the most fan-friendly recurring card because it feels editorial and alive.

### 2. Market Watch

Use for:

- biggest preseason line shifts
- win-total disagreements
- market vs returning-production outliers
- model vs public expectation gaps

This is the best recurring betting-adjacent card because it is interesting without pretending to be a gambling terminal.

## The tentpole event page

### Media Days Reality Check

This should be the signature July feature.

Use the actual `2026` media-days calendar:

- Big 12: `July 7-8`
- ACC: `July 15-17`
- SEC: `July 20-23`
- Big Ten: `July 28-30`

Best modules inside the tentpole:

- conference power tiers
- who has real reasons for optimism
- who is selling empty hope
- model vs quote energy
- awards and playoff buzz reality checks

Why this matters:

- July is when the national preseason argument machine fully turns on
- this is the cleanest tentpole for a smart-fan site that wants personality

## Month-by-month editorial plan

### April

Primary lane:

- `Roster Reality`

Best categories:

- Spring Exit Survey
- Continuity Board
- Biggest Unit Swings
- Newcomer Fit Check
- Ceiling vs Collapse
- QB Battle / Coordinator Clarity

What to avoid:

- fake April portal urgency

Why:

- the football transfer window is no longer an April core event
- April should be about interpreting spring, not chasing a portal cycle that moved to January

### May

Primary lanes:

- `Roster Reality`
- `Schedule Path`

Best categories:

- Path to 10 Wins
- Returning Production Leaders
- Most Improved Rosters
- Most Fragile Contenders
- Pressure Index
- Visit Season Primer

What to avoid:

- generic national top-25 churn with no structural insight

### June

Primary lanes:

- `Schedule Path`
- `Recruiting / Class Shape`

Best categories:

- Official Visit Season
- Class Need Match
- Recruiting Momentum by Position
- Summer Volatility Board
- Biggest Roster Reset Teams
- Best / Worst Schedule Timing

What to avoid:

- products that require verified real-time recruiting collection if the feed is not ready

### July

Primary lanes:

- `Preseason Debate`
- `Media Days Reality Check`

Best categories:

- Conference Reality Check
- Preseason Tiers
- Awards Buzz vs Reality
- Market vs Model
- Respect Gap
- Teams Selling Hope vs Teams Built for It

What to avoid:

- bland transcript or quote dumps

### August

Primary lanes:

- `Preseason Debate`
- launch into actual games

Best categories:

- Camp Risers / Fallers
- Certainty Index
- Most Volatile Depth Charts
- Week 0 / Week 1 Launchpad
- Upset Radar
- Season Confidence Meter

What to avoid:

- heavy player-by-player national tracking that is too labor-intensive for a solo operator

## What should be cut or delayed

### Cut for this offseason

- `April portal pulse` as a central category
- live social sentiment products
- giant recruiting trackers that assume perfect source coverage
- national all-team dashboards with shallow insight

### Delay until later

- player-level recruiting storytelling at full scale
- deep player-level sentiment
- always-on social intelligence
- real-time alerting
- fully dynamic cross-conference simulation layers

## Best initial scope

Do not start with all `136+` FBS teams.

Recommended first scope:

- `10-25` headline teams
- the playoff-adjacent teams
- the biggest fanbases
- the most talked-about rebuilds

Then expand once the experience feels sharp.

## Best visual modules

Best chart types for this plan:

- dumbbell charts
- annotated slope charts
- quadrant plots
- stacked roster bars
- small-multiple spark cards

Avoid:

- word clouds
- 3D charts
- giant dashboard pages

## Stack-fit conclusion

This plan is realistic for the current project because it mainly depends on:

- CFBD offseason data already in the repo
- precomputed static generation
- moderate recurring refreshes
- explanation and presentation, not huge new ingestion systems

The actual leverage point is not more infrastructure.

The leverage point is:

- turning existing offseason data into pages and cards that feel like college football arguments, not backend tables

## Recommended build order

1. Build `Roster Reality Check`
2. Build `Schedule Survival Guide`
3. Build `Preseason Truth Detector`
4. Add `Belief Meter` and `Market Watch` cards
5. Ship `Media Days Reality Check` as the July tentpole

If only one thing gets built first, it should be:

- `Roster Reality Check`

That is the clearest offseason differentiator and the strongest use of the current stack.
