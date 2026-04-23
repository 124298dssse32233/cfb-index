# Unique Concepts Market Honesty

Research date: 2026-04-22

Companion files:

- `research/unique-concepts-hardening-2026-04-22.md`
- `research/fan-intelligence-flagship-roadmap-2026-04-21.md`
- `research/fanbase-mood-system-design-2026-04-21.md`
- `research/sentiment-market-study-design-2026-04-21.md`
- `output/anthropic-unique-concepts-hardening-review.md`

## Purpose

This memo locks the next refinement after the outside-research hardening pass and the latest Anthropic second-brain review.

The goal is to answer three questions clearly:

- which concepts should become public signature modules
- which concepts should stay internal, later-phase, or be killed
- how to keep the `market + mood` angle interesting without making fragile `beat Vegas` claims

## Core conclusion

The product is strongest when it acts like a:

- `fan anthropology lab`
- `belief tracking system`
- `college football discourse observatory`

It is weakest when it drifts into:

- generic sports opinion media
- one-number sentiment theater
- implied sportsbook-alpha promises

The site does **not** need to prove that fan mood predicts betting markets to have a strong premise.

It only needs to show:

- how fans are feeling
- how outsiders are talking
- what surprised people
- where belief, football structure, and the market disagree

That is already distinctive, fun, and durable.

## What the market literature actually supports

## 1. Social data can add information to markets in specific contexts

Brown, Rambaccussing, Reade, and Rossi (`2018`) found that aggregate Twitter tone contained information not fully reflected in live Betfair prices during soccer matches, especially right after goals and red cards.

Useful implication:

- social reaction can help interpret football events

Bad implication to avoid:

- `social sentiment generally beats betting markets`

This is most relevant to:

- `Shock Index`
- postgame `Belief Shift`
- event-annotated mood timelines

Source:

- https://centaur.reading.ac.uk/73480/1/BetfairTwitterEI_revisedv2.pdf

## 2. Pre-event buzz can matter, but alpha claims are fragile

Ramirez, Reade, and Singleton (`2023`) found that a relative Wikipedia-buzz measure predicted bookmaker mispricing in women's tennis.

But Clegg and Cartlidge (`2025`) later showed that a correction and cleaned extension removed most of the apparent profitability, with later periods suggesting weaker or disappearing edge.

Useful implication:

- attention and buzz are real signals worth tracking

Bad implication to avoid:

- `if we collect enough chatter we will discover a repeatable betting edge`

This matters because it argues for:

- descriptive `Mood vs Market`
- explanatory `What Moved The Number`

instead of:

- predictive `bet this because the fans are onto something`

Sources:

- https://centaur.reading.ac.uk/106488/9/1-s2.0-S0169207022001091-main.pdf
- https://arxiv.org/abs/2306.01740

## 3. Precision of extraction matters more than corpus size

`TwitterPaul` found that high-precision extraction from a medium-sized dataset was more valuable than low-precision extraction from a giant noisy corpus.

Useful implication:

- tighter source discipline beats maximal scraping

That supports:

- careful team aliasing
- fan/rival/national bucket separation
- confidence gating
- human-reviewable weekly outputs

Source:

- https://arxiv.org/abs/1211.6496

## What should become signature public modules

These are the clearest public modules for a first differentiated product.

## 1. Team Mood Card

This remains the flagship.

Why:

- it is easy to explain
- it fits the current pipeline
- it converts proprietary collection into a shareable object
- it answers the fan's first question instantly

Core public pieces:

- `Fan Pulse`
- `Reality Check`
- `Swing Meter`
- `Cohesion`
- `Respect Gap`
- `Rival Heat`

## 2. Shock Index

This should become the strongest homepage heartbeat.

Definition:

- football surprise times conversation movement

Why it works:

- surprise is behaviorally grounded
- it ties mood to football reality
- it is more legible than raw sentiment deltas

Best uses:

- biggest weekly shock boards
- postgame reaction modules
- annotated trend charts

## 3. Respect Gap

This is one of the best recurring identity modules.

Definition:

- how much more or less bullish the fanbase is than outside conversation

Why it works:

- instantly arguable
- easy to visualize
- does not require expert-columnist authority

## 4. Fanbase Civil War Watch

This should remain a visible public module.

Why:

- disagreement is more interesting than average mood
- it captures internal fracture, not just negativity
- it gives team pages personality

Best framing:

- disagreement
- split camps
- fanbase fracture

not:

- generic negativity

## 5. What Changed This Week

This is the best packaging layer.

Why:

- it turns metrics into narrative
- it explains movement in football language
- it helps the product feel editorial rather than robotic

## What should stay internal or later-phase

These concepts are promising, but should not define v1.

## 1. Loyalty Temperature

Strong later-phase idea.

Why not v1:

- needs more longitudinal behavior evidence
- easier to overstate than to measure well

Best future use:

- season-level fanbase identity cards
- offseason attachment profiles

## 2. Spillover Risk

Useful internal prioritization tool.

Why not public yet:

- abstract
- hard to explain cleanly
- more valuable for editorial triage than casual fan delight

## 3. In-Group / Out-Group Split

Very promising, but likely phase two.

Why not first:

- it depends on stronger language modeling
- easy to produce confusing outputs if entity targeting is noisy

Best future use:

- rivalry week modules
- matchup pages
- national-versus-fan identity cards

## 4. Player and coach love/hate boards

Potentially fun, but should wait until targeting, sarcasm handling, and sample quality are more robust.

Why:

- higher reputational risk
- easier to embarrass the product with false readings

## What to kill or de-emphasize

## 1. `Can vibes beat Vegas?`

This is the wrong framing.

Why:

- it invites the wrong standard of proof
- it overpromises
- it shifts the product toward a betting tout identity

## 2. One-number sentiment scores

This is both weak and boring.

Why:

- fake precision
- poor fan legibility
- easier for users to distrust

## 3. Generic offseason preview content as core identity

This should stay secondary.

Why:

- crowded market
- weak moat
- depends on analyst authority more than product differentiation

## 4. Real-time alert positioning

Avoid claiming the site is a real-time social-listening terminal.

Why:

- expensive operationally
- fragile for a small team
- not required for a lovable fan product

## Naming and framing guidance

Use names that feel like fan products, not NLP dashboards.

Prefer:

- `Team Mood Card`
- `Shock Index`
- `Respect Gap`
- `Reality Check`
- `Swing Meter`
- `Fanbase Civil War Watch`
- `What Changed This Week`

Avoid:

- `sentiment score`
- `emotion classifier`
- `market inefficiency detector`
- `prediction alpha`

## Market-angle framing rules

The public market story should be:

- `Mood vs Market`
- `Fans vs The Number`
- `What The Spread Says vs What The Fanbase Believes`
- `Where The Market, Model, and Mood Disagree`

The public market story should **not** be:

- `our social model beats the books`
- `fans know better than Vegas`
- `here is the profitable signal`

Good public uses:

- contextualizing hype or panic
- showing when fans are more optimistic than the line
- annotating surprise reactions after big results

Bad public uses:

- betting recommendations
- claims of causal market impact without strong design
- high-frequency line-movement interpretation that the current stack is not built to support

## Product rules that protect credibility

## 1. Keep audience buckets separate

Never collapse:

- fan
- rival
- national

into one mood number.

## 2. Publish labels, not fake decimals

Prefer:

- `Bullish`
- `Grounded`
- `Swingy`
- `Split`

over:

- `71.4`
- `0.63`

## 3. Tie changes to football events

Every major movement should be interpretable through:

- a result
- a roster event
- a quote cycle
- a market move

## 4. Use confidence gates aggressively

Thin, sarcastic, or bucket-leaky samples should not become headline cards.

## 5. Keep the public cadence weekly/editorial

That is the best match for:

- the current Python + SQLite workflow
- a small-team publishing model
- the level of methodological honesty the product should maintain

## Recommended priority order

1. `Team Mood Card`
2. `Shock Index`
3. `Respect Gap`
4. `Fanbase Civil War Watch`
5. `What Changed This Week`
6. `Rival Heat`
7. `Hope Inventory`
8. `Loyalty Temperature` later

## Strategic takeaway

The strongest version of this site is not:

- a sentiment tracker
- a betting model
- a recruiting magazine

It is:

- a visually strong fan-intelligence product that measures belief, surprise, disagreement, and identity in public college-football conversation

That is the lane to keep hardening.
