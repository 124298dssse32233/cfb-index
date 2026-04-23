# Anthropic Second-Brain Synthesis

Research date: 2026-04-21

## Purpose

This memo captures the most important conclusions from two Anthropic strategy-review runs so the thinking survives even if chat context is lost.

The raw outputs were saved to:

- `output/anthropic-study-design-review.md`
- `output/anthropic-fan-output-review.md`

## Core strategic conclusion

Anthropic strongly reinforced the same direction reached in local research:

- do **not** position this as `can vibes beat Vegas`
- do position it as `information diffusion intelligence` and `Fan Intelligence`

That means the product should focus on:

- how public conversation moves relative to markets
- where fans, rivals, and the broader public disagree
- which shocks or surprises change the story fastest

## What Anthropic thought was strongest

### On the premise

The strongest framing was:

- `Can we identify moments when public conversation moves faster than betting markets, or vice versa?`

Anthropic especially liked:

- event-driven lead-lag questions
- visibility and rivalry as amplifiers
- negative-sentiment asymmetry
- source-quality differences between beat-reporting style posts and generic fan chatter

### On the fan product

Anthropic pushed for:

- `Fan Intelligence`, not `sentiment analytics`
- disagreement as the hero
- a weekly editorial rhythm instead of a sterile dashboard

The most endorsed narrative modules were:

- `Overreaction Watch`
- `Respect Gap`
- `Panic Meter`
- `Rival Heat`
- `Market vs Mood`

## What Anthropic thought was weak

Anthropic explicitly warned against:

- promising that vibes can consistently beat the market
- claiming clean causation from observational data
- collapsing everything into one team sentiment score
- pretending the current stack supports tick-level market microstructure
- trying to build a real-time social-listening terminal in v1

## Best v1 product recommendation

The clearest combined recommendation is:

### Team level

- `Fan Pulse`
- `National Mood`
- `Rival Heat`
- `What Changed This Week`

### Weekly homepage / front page

- `Biggest Vibe Shifts This Week`
- `Market vs Mood Disagreements`
- `Most Panicked Fanbases`
- `Rival Heat Leaders`

### Matchup pages

- `Which fanbase is calmer`
- `What both sides are worried about`
- `Where the model, market, and mood disagree`

## Best chart directions

Anthropic repeatedly preferred:

- annotated slope charts
- dumbbell charts
- quadrant plots
- emotion ribbon charts
- small-multiple spark cards

It explicitly did **not** like:

- giant dashboard piles
- one-number summaries
- overly technical scoring language

## Best operating recommendation

Anthropic agreed that the current stack is good enough for v1 if we stay disciplined:

- Python batch jobs are fine
- CFBD Tier 2 is enough for v1
- the site should stay mostly static
- event-driven or daily refreshes beat fake real-time complexity

## Final synthesis

The best combined framing for this project is:

- a `Fan Intelligence` layer for college football
- built around `Fan Pulse`, `National Mood`, `Rival Heat`, and `Market vs Mood`
- told through weekly `Overreaction Watch`, `Respect Gap`, and `Panic Meter` storylines
- grounded in open-to-close betting lines now
- expanded later with snapshot tables for deeper event studies

## Launch-sequence update

After a later Anthropic review of the actual v1 data plan and schema, the strongest launch recommendation became even narrower:

- ship `FBS-only` first
- keep the product `team-level` first
- make the homepage a weekly editorial rhythm, not a live dashboard
- treat `game_line_snapshots`, `prediction_market_snapshots`, and broad player-level coverage as later phases

In other words:

- the schema can be broader than the first launch
- the first launch should still be ruthlessly focused
