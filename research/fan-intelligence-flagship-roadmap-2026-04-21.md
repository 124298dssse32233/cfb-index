# Fan Intelligence Flagship Roadmap

Research date: 2026-04-21

Companion files:

- `research/proprietary-fan-intelligence-ideation-2026-04-21.md`
- `research/cfb-fan-delight-viz-brief-2026-04-21.md`
- `research/conversation-intelligence-v1-data-plan-2026-04-21.md`
- `output/anthropic-proprietary-fan-lab-review.md`

## Purpose

This memo locks in the clearest strategic direction after several rounds of local research and Anthropic second-brain review.

The main correction is:

- move away from making the site feel like a generic preseason magazine
- move toward a proprietary `fan intelligence` product built from public-web conversation collection and football context

## Directional decision

The strongest offseason and early-launch identity is **not**:

- roster guides
- schedule survival guides
- generic top-25 opinion content
- trying to out-columnist ESPN, CBS, or On3

The strongest identity **is**:

- `fan anthropology`
- `belief tracking`
- `narrative drift`
- `respect gap`
- `rival hostility`
- `market vs mood`

The site should feel like:

- a `college football fan lab`
- a `discourse observatory`
- an `argument engine`

not:

- a generic preview annual with some charts

## Why this premise makes sense

This lane makes sense because it fits the actual moat we are building.

That moat is not secret data.

It is:

- collecting the right public discussion consistently
- separating fan, rival, and broader-national viewpoints
- joining that discussion to football structure
- packaging the result into recurring, readable, funny, and arguable outputs

This also avoids the weakest version of the premise:

- `can vibes beat Vegas?`

The stronger version is:

- `how are fans feeling?`
- `how are outsiders talking?`
- `where do those things disagree with the market or the model?`

That is explainable, honest, and much more fun.

## Flagship experience

The clearest first flagship should be a **Team Mood Card**.

This should be the first thing a fan sees on a team page and the first truly ownable product surface on the site.

### Team Mood Card core pieces

- `Fan Pulse`
- `National Mood`
- `Respect Gap`
- `Rival Heat`
- `Belief Shift`
- `Top Storylines`

### What it should answer instantly

- `How are our fans feeling right now?`
- `How is everyone else talking about us?`
- `Are we more optimistic than the national conversation?`
- `What are rivals mocking or fearing?`
- `What changed since last week?`

### Why this is the right flagship

- it is easy to explain
- it is different from mainstream preseason coverage
- it turns proprietary collection into a shareable artifact
- it does not require fake expert authority
- it fits the current team-level conversation pipeline

## Best recurring modules

These are the most promising recurring homepage and editorial modules.

### 1. Biggest Vibe Shifts

- biggest week-over-week gainers and losers in belief
- strongest recurring heartbeat for the front page

### 2. Most Panicked Fanbases

- focused on fear, dread, and defensive language
- especially useful after spring and during camp

### 3. Respect Gap Leaders

- teams whose own fans are far more bullish than outsiders
- or the reverse

### 4. Main Character Of The Week

- which team or program the broader sport cannot stop discussing
- good for national fascination and click-through

### 5. Rival Heat Leaders

- who rivals are mocking, fearing, or obsessing over most
- brings true college-football texture

### 6. Fanbase Civil War Watch

- teams with the most internal disagreement
- more interesting than a flat sentiment average

### 7. Belief Vs Reality

- conversation optimism versus model or market structure
- best place for `Delusion Meter`

### 8. What Everyone Is Arguing About

- storyline-driven roundup
- turns topic extraction into readable editorial packaging

## Best team-page modules after the flagship card

After the Team Mood Card, the next team-page modules should be:

- `Vibe Over Time`
- `What Changed This Week`
- `Top Storylines`
- `Rival Heat Breakdown`
- `Belief vs Reality`

The team page should feel like:

- a living team identity profile

not:

- a warehouse shelf of unrelated widgets

## Best matchup-page uses

The matchup page should use the conversation layer selectively.

Best uses:

- `Which fanbase is calmer`
- `What both sides are worried about`
- `Market vs Mood`
- `Model vs Market vs Mood`

This is where betting context becomes entertaining without requiring trading-terminal precision.

## April through August content rhythm

The offseason roadmap should follow real college-football attention cycles, but the framing should stay conversation-first.

### April

Core frame:

- `post-spring emotional reset`

Best categories:

- `Spring Exit Survey`
- `Who Gained Belief After Spring`
- `Who Left Spring More Nervous`
- `QB Panic Meter`
- `Hope Inventory`

Avoid:

- fake April portal frenzy framing

### May

Core frame:

- `identity formation`

Best categories:

- `Respect Gap Census`
- `National Fascination Board`
- `Most Fragile Contenders`
- `Fanbase Civil War Watch`
- `Programs Outsiders Keep Getting Wrong`

### June

Core frame:

- `summer discourse drift`

Best categories:

- `Storyline Gravity`
- `What Fans Are Lying To Themselves About`
- `Biggest Summer Vibe Stalls`
- `Rival Heat Map`
- `Recruiting Weekend Mood, Not Recruitnik Rankings`

Important note:

- if recruiting is covered in this month, it should be covered as fan reaction, expectation, and identity narrative
- it should not become a full expert recruiting service

### July

Core frame:

- `media days and conference mood season`

Best categories:

- `Media Days Reality Check`
- `Conference Respect Gap Boards`
- `Quote Energy vs Fan Mood`
- `Main Character Of The Week`
- `Who Is Selling Hope Best`

This should be the biggest offseason tentpole month.

### August

Core frame:

- `certainty theater meets real uncertainty`

Best categories:

- `Delusion Meter`
- `Camp Panic Meter`
- `Preseason Truth Detector`
- `AP Poll vs Fan Pulse`
- `Week 0 Vibe Board`

## What to kill or postpone

These ideas are tempting, but they are the wrong center of gravity.

### Kill as core identity

- generic roster guides
- generic schedule survival guides
- broad expert top-25 commentary
- trying to produce opinion authority on everything

### Postpone until later

- player-level sport-wide sentiment coverage
- real-time alerting
- prediction-market-heavy features
- deep intraday market lead-lag claims
- full lower-division rollout for conversation features

These may still become useful extensions, but they should not define v1.

## What the stack can realistically support

The current stack is well matched to this direction.

### Current fit

- Python batch jobs are fine
- SQLite is fine because it is a build database, not a live user-serving dependency
- static publishing is fine
- `REQUEST_TIMEOUT_SECONDS=60` is a reasonable default

### Operational shape

- keep heavy ingest and backfills out of the live chat loop when possible
- prefer logged or background-style runs for large jobs
- use batch refreshes and editorial rhythms instead of pretending to be real-time

### Recommended scope discipline

- `FBS-only` first
- `team-level` first
- `Reddit + YouTube + selective Bluesky` first
- publish only when sample sizes are healthy enough to trust

## Immediate build sequence

The best next build order is:

1. solidify the `Team Mood Card` data contract and reporting shape
2. build homepage modules for `Biggest Vibe Shifts`, `Respect Gap Leaders`, and `Most Panicked Fanbases`
3. add a human-readable `What Changed This Week` explanation layer
4. expand sources carefully after the team-level product feels sharp

## Final decision rule

If a feature makes the site feel like:

- `we collected something interesting about college football fandom`

it is probably on strategy.

If a feature mainly makes the site feel like:

- `we wrote another preseason guide because that is what sports sites do`

it is probably off strategy.
