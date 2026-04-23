# Offseason Fan Delight Deep Research

Research date: 2026-04-22

Companion files:

- `research/offseason-modules-calendar-2026-04-21.md`
- `research/offseason-modules-recommendation-2026-04-21.md`
- `research/fan-intelligence-flagship-roadmap-2026-04-21.md`
- `research/unique-concepts-market-honesty-2026-04-22.md`
- `research/offseason-homepage-execution-2026-04-22.md`
- `output/anthropic-offseason-fan-delight-review.md`
- `output/anthropic-offseason-viz-review.md`

## Purpose

This memo answers a narrower and more practical question:

- what will actually keep college-football fans engaged from `April 22, 2026` until kickoff
- what this repo can realistically provide
- what visual forms will feel premium and fun instead of like commodity offseason sludge

The emphasis here is:

- fan delight
- revisitation
- readable narrative
- proprietary framing
- stack realism

not:

- trying to imitate ESPN breadth
- becoming a full recruiting service
- pretending to be a real-time newswire

## What the current offseason actually looks like

The `2026` offseason calendar matters because the product should move with the sport's real attention cycles.

### Verified `2026` anchor dates

- `Big 12` football media days are `July 7-8, 2026`
- `ACC` football media days are `July 15-17, 2026`
- `SEC` football media days are `July 20-23, 2026`
- `Big Ten` football media days are `July 28-30, 2026`
- `ACC` teams open `Week 0` on `August 29, 2026`, including games in `Brazil` and `Ireland`

Important implication:

- `July` is the biggest offseason tentpole month
- `late August` is not abstract preview season anymore
- it is the final belief-and-certainty window before real football starts

Sources:

- Big 12 media days: https://big12sports.com/news/2025/12/22/big-12-football-media-days-to-return-to-the-star-in-2026-and-2027.aspx
- ACC schedule / Week 0: https://theacc.com/news/2026/1/26/acc-unveils-2026-football-schedule.aspx
- SEC media days: https://www.secsports.com/news/2026/04/sec-announces-appearance-schedule-for-2026-football-media-days
- Big Ten media days: https://bigten.org/fb/article/59800/

## Why the offseason product opportunity is stronger now

The changing spring-game environment creates more need for interpretation products.

ESPN reported that `19` Power Four programs had canceled their spring games in the cited cycle, with some replacing them with scrimmages, showcases, or other fan events. Coaches explicitly tied this to:

- transfer-portal pressure
- tampering concerns
- longer seasons
- changing roster economics

That means the offseason is increasingly defined by:

- less clean public access
- more rumor, spin, and uncertainty
- more need for a product that interprets belief and perception

Source:

- https://www.espn.com/college-football/story/_/id/44152063/2025-college-football-spring-game-changes

## What fans demonstrably care about

## 1. Football is still the dominant fandom lane

The Siena / St. Bonaventure `2025` American Sports Fanship Survey found:

- `70%` of respondents considered themselves football fans
- `47%` said football was their favorite sport

Source:

- https://www.sbu.edu/docs/default-source/news/siena_sbu-survey1.pdf

## 2. College fandom is deep, sticky, and identity-heavy

Samford's SEC fan-engagement study describes highly engaged fans in terms like:

- affection
- commitment
- dependability
- intimacy

and explicitly frames deep fandom as something that develops over time rather than overnight.

That matters because it supports a product built around:

- identity
- self-image
- internal disagreement
- loyalty
- emotional coping

not just:

- raw football transactions

Source:

- https://www.samford.edu/sports-analytics/fans/2014/sec-study

## 3. College football is a massive and durable audience

Learfield says college sports fans are:

- highly passionate
- highly affluent
- heavily tied to tradition

and estimates `195M` total fans across college sports.

Playfly adds several useful directional signals:

- college football regular-season attendance exceeded `42.3M` in the cited release
- younger fans were broadly positive or neutral on realignment
- younger fans were broadly positive on NIL

Implication:

- the offseason product should not assume fans only care about games
- they care about identity, change, and what the sport is becoming

Sources:

- https://fanbasereport.learfield.com/
- https://playfly.com/press-releases/playfly-sports-leaders-in-sports-fan-data-release-latest-playfly-fan-score-college-football-edition/

## 4. Fans clearly enjoy fanbase sentiment projects

Independent Reddit fan projects measuring:

- fanbase sentiment
- best and worst fanbases
- flair censuses
- conference superlatives

got real traction on `r/CFB` and related conference subreddits.

That does not prove scientific representativeness.

But it does prove:

- fans enjoy seeing fandom quantified
- they like conference-level superlatives
- they will spend time with comparative fan anthropology

Source:

- https://www.reddit.com/r/CFB/comments/18q0c4j/reddits_cfb_fan_sentiment_survey_results_1600/

## What mainstream offseason content already does well

The current major-outlet mix is pretty stable:

- way-too-early top 25s
- post-spring updates
- transfer-portal winners and losers
- impact transfers
- preseason team tiers
- "most to prove" lists
- conference power comparisons

Representative examples:

- ESPN `SP+` rankings and spring-updated top 25s
- On3 composite top-25 content
- CBS transfer-portal winners / impact additions
- SI offseason primers and spring takeaways

Implication:

- we should not try to win by producing a slightly different top-25 article
- we should use those commodity angles only as scaffolding around proprietary fan-intelligence surfaces

Representative links:

- https://www.espn.com/college-football/story/_/id/48306284/2026-college-football-sp%2B-rankings-138-fbs-teams
- https://www.espn.com/college-football/story/_/id/48370187/2026-college-football-way-too-early-top-25-spring-update
- https://www.on3.com/news/way-too-early-top-25-composite-sports-outlets-experts-predict-college-football-rankings-for-2026//
- https://www.cbssports.com/college-football/news/college-footballs-top-100-transfer-portal-players-for-2026/
- https://www.cbssports.com/college-football/news/2026-college-football-transfer-portal-winners-losers/amp/
- https://www.si.com/college-football/offseason-primer-everything-that-could-change-before-2026-kickoff

## What our stack can realistically support

Based on the current repo and validation docs, the real v1 source stack is:

- `CFBD Tier 2` for football structure, roster context, returning production, recruiting, advanced metrics, schedules, and betting lines
- `Reddit` collection validated locally, with `JSON` plus `RSS` fallback
- `conversation_storylines` already stored in the local database
- `YouTube` as the most sensible next expansion
- `Anthropic` for critique, editorial labeling, and strategy pressure-testing

The stack is **not**:

- real-time social listening
- full intraday line microstructure
- live campus-reporting intelligence
- complete player-level public sentiment resolution

Operationally, the right cadence remains:

- batch
- weekly/editorial
- static-site-first

Sources:

- `docs/cfbd-tier2-and-safe-operations.md`
- `research/conversation-intelligence-runtime-validation-2026-04-21.md`

## The strongest offseason product thesis now

The strongest offseason site is:

- a `fan anthropology magazine`
- a `belief-tracking lab`
- a `premium argument engine`

It is not:

- a generic preview annual
- a recruiting database clone
- a betting tout site
- a real-time dashboard

This means the best modules should answer one of these questions:

- `How are we feeling right now?`
- `What changed since last time I checked?`
- `Are we more bullish than the evidence supports?`
- `Who cannot stop talking about us?`
- `Which fanbases are splitting, panicking, or coping?`

## Best recurring offseason modules

These are the strongest `April -> August` modules after combining outside research, Anthropic review, and current stack reality.

## 1. Team Mood Card

Status:

- clear flagship
- already partially implemented in code

Fan itch:

- `How are we doing in the discourse?`

Why it wins:

- works for every team
- easy to understand
- instantly shareable
- creates a reason to revisit every week

Best visual form:

- team-branded magazine card
- large state labels
- confidence ribbon
- progressive disclosure into details

## 2. Shock Index

Status:

- best next major module
- not fully implemented yet

Fan itch:

- `What surprised everyone most?`

Why it wins:

- surprise is a stronger organizing concept than generic positivity
- creates the natural homepage heartbeat
- can work in offseason around:
  - portal shocks
  - coach / QB news
  - media-day quote spikes
  - preseason ranking shocks

Best visual form:

- ranked shock boards
- annotated waterfall / delta views
- event callouts

## 3. Respect Gap Census

Fan itch:

- `Are we overhyped or underrated?`

Why it wins:

- arguable
- conference-comparable
- works in offseason when national narratives harden faster than actual evidence

Best visual form:

- dumbbell chart
- fan vs national split
- conference small multiples

## 4. Fanbase Civil War Watch

Fan itch:

- `How divided are we internally?`

Why it wins:

- internal disagreement is more interesting than average mood
- thrives in QB battles, coaching uncertainty, preseason hype cycles, and post-spring ambiguity

Best visual form:

- split-room cards
- disagreement ribbon
- sample quote rail

## 5. Living Rent-Free

Fan itch:

- `Who cannot stop talking about us?`

Why it wins:

- rivalry and obsession are core college-football energy
- less generic than `most hated`
- useful all offseason

Best visual form:

- rival heat matrix
- attention heat map
- network / matrix board

## 6. Hope Inventory

Fan itch:

- `What are fans clinging to?`

Why it wins:

- very strong in April, May, and June
- helps explain how middling or wounded programs sustain excitement
- turns roster churn into emotional language

Best visual form:

- stack-ranked coping pillars
- issue cards
- optimism shelf

## 7. Storyline Gravity

Fan itch:

- `Which offseason story keeps getting bigger?`

Why it wins:

- explains why some teams dominate oxygen without actual games
- works for June drift and July media-days cycles

Best visual form:

- storyline river
- topic share ribbons
- story growth ladders

## 8. Media Days Reality Check

Fan itch:

- `Who is selling hope and who actually has the substance?`

Why it wins:

- perfect July tentpole
- aligns to actual conference calendar
- mixes quotes, national narrative, fan belief, and roster / model structure

Best visual form:

- quote-energy vs reality quadrant
- conference mood boards
- team dossier cards

## 9. Camp Panic Meter

Fan itch:

- `Whose fanbase is suddenly sweating?`

Why it wins:

- perfect for early August
- bridges uncertainty, rumors, injuries, depth-chart nerves, and last-minute expectation swings

Best visual form:

- fear leaderboard
- panic small multiples
- confidence-to-panic deltas

## 10. Preseason Truth Detector

Fan itch:

- `Which offseason story is real and which one is vibes only?`

Why it wins:

- strongest late-July through August
- gives the model / market / mood intersection a clean public use
- does not require betting-alpha claims

Best visual form:

- `Model vs Mood vs Market` quadrant
- badge-based labels such as:
  - `Grounded`
  - `Hopeful`
  - `Selling A Dream`
  - `Too Low On Themselves`

## Best visual grammar for the site

The visual strategy should favor:

- card-first mobile layouts
- strong team identity colors
- progressive disclosure
- story annotations
- charts that answer one fan question immediately

The best outside visual-design evidence here is:

- `Omnioculars`, which argues fans need embedded, context-rich visual explanations rather than analyst-only views
- `SportsBuddy`, which argues sports storytelling gets stronger when narrative and visual explanation are fused
- the `data comics` paper, which found comics improved enjoyment, focus, recall, and overall engagement compared with standard infographics

Implication:

- some of our best offseason surfaces should feel like:
  - `data comics`
  - `cinematic team dossiers`
  - `argument cards`
  - `annotated story graphics`

not:

- plain sortable tables
- generic line charts
- dashboard walls

Sources:

- Omnioculars: https://arxiv.org/abs/2209.00202
- SportsBuddy: https://arxiv.org/abs/2502.08621
- Data comics study: https://doi.org/10.1145/3290605.3300483

## Best visual patterns by module

## Use aggressively

- `Mood Rivers`
  - best for belief over time
- `Quadrant Plots`
  - best for `model vs market vs mood`
- `Dumbbell Charts`
  - best for `Respect Gap`
- `Heat Maps / Matrices`
  - best for rivalry obsession and conference mood maps
- `Small-Multiple Spark Cards`
  - best for conference roundups and mobile scanning
- `Annotated Waterfalls`
  - best for `Shock Index` and belief shifts
- `Data Comics`
  - best for one weekly marquee story

## Avoid as primary forms

- giant plain tables
- word clouds
- unlabeled sentiment scales
- dashboard pages with too many equal-weight widgets
- charts without annotations
- charts that require hover to make sense on mobile

## Month-by-month recommendation

## Late April

Center of gravity:

- `Spring Exit Survey`
- `Who Gained Belief After Spring`
- `QB Panic Meter`
- `Hope Inventory`
- `Fanbase Civil War Watch`

Best marquee visual:

- `Post-Spring Belief Reset` board

## May

Center of gravity:

- `Respect Gap Census`
- `Offseason Identity Cards`
- `Most Fragile Contenders`
- `Programs Outsiders Keep Getting Wrong`

Best marquee visual:

- `Identity Formation` conference boards

## June

Center of gravity:

- `Storyline Gravity`
- `Summer Vibe Stalls`
- `Recruiting Euphoria / Paranoia`
- `Rival Heat Map`

Best marquee visual:

- `Summer Narrative Drift` river / ribbon boards

## July

Center of gravity:

- `Media Days Reality Check`
- `Conference Respect Gap`
- `Quote Energy vs Fan Mood`
- `Who Is Selling Hope Best`

Best marquee visual:

- conference `Mood Maps` and `Reality Check` quadrants

## August

Center of gravity:

- `Camp Panic Meter`
- `Delusion Meter`
- `Preseason Truth Detector`
- `AP Poll vs Fan Pulse`
- `Week 0 Vibe Board`

Best marquee visual:

- `Truth Detector` quadrant plus `Week 0` belief board

## What to cut or de-emphasize

These are not strong enough as the brand center.

## Cut as core identity

- generic roster guides
- generic schedule survival as a main product lane
- real-time alerts
- beat-Vegas framing
- depth-chart rumor boards
- player-by-player national tracking
- full recruiting-service behavior

## Keep only as support

- roster reality checks
- schedule difficulty context
- portal summaries

These are useful when they support a stronger proprietary story such as:

- `Why fans got more bullish after spring`
- `Why this contender suddenly looks fragile`
- `Why the quote energy does not match the evidence`

## Product rule to hold the line on

Because the user explicitly does **not** want the site centered on:

- roster guides
- schedule survival
- generic expert authority

any Anthropic or outside recommendation in those directions should be treated as:

- secondary support context

not:

- the public brand center

That means the Anthropic visual review is useful for:

- card design
- visual hierarchy
- visual forms

but its stronger `schedule survival` push should be moderated by the repo's broader strategic direction.

## Best v1 shape from this research

If the site wants the best chance of becoming habit-forming before kickoff, the cleanest recurring bundle is:

1. `Team Mood Card`
2. `Shock Index`
3. `Respect Gap Census`
4. `Fanbase Civil War Watch`
5. `Living Rent-Free`
6. `What Changed This Week`
7. one monthly tentpole:
   - `Media Days Reality Check` in July
   - `Preseason Truth Detector` in August

## Strategic takeaway

The winning offseason product is not:

- the site that publishes the most preseason content

It is:

- the site that best captures what college-football fans are feeling, arguing about, lying to themselves about, and obsessing over while the season is still coming into focus

That is the lane this stack can realistically own.
