# Sentiment, Betting Markets, And Prediction Markets Study Design

Research date: 2026-04-21

## Purpose

This memo answers the practical version of the question:

- does the core premise make sense?
- what should we study first?
- what should we not claim?
- can we do this with the current stack, APIs, and budget?

It is written for the current repo reality:

- `CFBD Tier 2` for core football data
- Python batch jobs
- SQLite for local build state
- a mostly static published site
- modest external-data budget

## Bottom line

Yes, the premise makes sense, but only if we phrase it carefully.

The strongest version of the idea is **not**:

- `can fan vibes beat Vegas?`

The strongest version is:

- `when does public conversation contain information or noise that the market has not fully absorbed yet?`
- `when do markets move first and public sentiment follows?`
- `when do both move together because a real football event or news shock hit at the same time?`

That reframing matters because the literature does **not** support a clean, universal claim that generic sentiment reliably leads markets. It supports a narrower and more interesting claim:

- sentiment sometimes matters
- the effect is concentrated in high-attention settings
- the effect is often tied to visibility, fan avidity, recent performance, or breaking-news interpretation
- naive sentiment signals are easy to overstate

## What existing research suggests

### 1. Sports betting markets are not immune to sentiment

Greg Durham and Tod Perry's paper on the college-football wagering market found that uninformative expert picks, recent against-the-spread performance, high-visibility teams, and high-fan-avidity teams were related to intraweek spread movement. But the paper also found that trading strategies designed to exploit this were only `marginally profitable at best`.

Practical meaning for us:

- public bias can show up in the market
- but market efficiency and arbitrage limit easy alpha
- this is a better product and research question than a pure betting model promise

### 2. Social media can help around event interpretation, not just raw mood

Research on soccer betting markets and Twitter found that social media activity helped identify moments where betting prices were temporarily inefficient, especially right after salient events like goals or red cards. The useful signal was not just generic chatter volume. It was concentrated around how information got interpreted and who was doing the posting.

Practical meaning for us:

- event studies are stronger than broad season-long vibe claims
- source quality matters
- timing matters
- `after-shock interpretation` may be more predictive than aggregate positivity

### 3. Markets can lag breaking public information

Research on prediction markets and Twitter around a political news shock found delayed market adjustment and evidence of post-news drift. The paper argues that prices sometimes moved slowly, especially until important accounts and traditional media amplified the event.

Practical meaning for us:

- public conversation can sometimes lead a market
- but the mechanism may be `information diffusion`, not mood alone
- the best question is often `who moved first during a shock?`

### 4. Sentiment alone is a weak abstraction

Stance-detection and aspect-based-sentiment research both warn that:

- sentiment and stance are different
- short social text is noisy
- user-generated text is unstructured and ambiguous

That matters a lot for college football:

- a post can praise a quarterback and still argue the team is overrated
- rivals can use positive-sounding sarcasm to attack
- fans can be negative in tone while still deeply supportive

Practical meaning for us:

- use team or player targeted scoring, not one document-level label
- separate `fan sentiment`, `national sentiment`, and `rival sentiment`
- expect sarcasm, profanity, and memes to break brittle models

## The best first questions to ask

These are the questions most worth building around.

### Question 1

`Does pregame public sentiment help explain open-to-close line movement after controlling for football strength and context?`

Why this is strong:

- we already have `open` and `close` fields in `game_lines`
- CFBD provides weather, advanced stats, and team context
- it produces a clean, understandable output

### Question 2

`Are sentiment effects larger for brand-name teams, rivalry games, ranked matchups, or teams with larger fanbases?`

Why this is strong:

- it matches the literature on visibility and fan avidity
- it creates fan-friendly stories
- it is much more plausible than claiming one effect across all games

### Question 3

`Does negative sentiment move markets more than positive sentiment?`

Why this is strong:

- panic, scandal, and injury chatter may matter more than optimism
- fans intuitively understand asymmetry
- it creates better narratives than a generic average score

### Question 4

`After a surprise event, does the market move first or does public conversation move first?`

Why this is strong:

- it creates the most interesting future feature
- it fits event-study methods
- it is the cleanest version of the `vice versa` question

Important caveat:

- this is a `later-phase` question unless we build line or market snapshot tables

### Question 5

`How much of next-48-hour sentiment is explained by market surprise versus game outcome itself?`

Why this is strong:

- it flips the direction and asks whether markets shape the story fans tell
- it produces a genuinely interesting editorial angle

## Questions we should avoid

These are tempting, but they are too loose or misleading for v1.

### Avoid 1

`Can vibes beat the market?`

Why to avoid it:

- it collapses multiple mechanisms into one slogan
- it encourages overfitting
- it sets the wrong user expectation

### Avoid 2

`Does social sentiment cause betting lines?`

Why to avoid it:

- with observational data, causation is hard to claim
- many line moves and social reactions share the same underlying cause
- open and close lines alone do not identify mechanism

### Avoid 3

`Can we build one sentiment score per team?`

Why to avoid it:

- it hides disagreement between fans, rivals, and neutral observers
- it is boring product-wise
- it throws away the most interesting structure

### Avoid 4

`Can we do tick-level lead-lag now?`

Why to avoid it:

- not with the current `game_lines` table
- we do not yet store full line history or repeated market snapshots

### Avoid 5

`Can we cover every team and every player at all levels from day one?`

Why to avoid it:

- the budget will break from coverage, not model cost
- lower divisions should be selective until demand proves out

## What is feasible now

## Core market side

Already available now:

- `CFBD` open and close betting lines
- weather
- advanced box-score context
- schedule and opponent context
- historical backfill through the existing Python pipeline

What this supports immediately:

- pregame open-to-close studies
- model-vs-market disagreement features
- postgame surprise tagging

What this does **not** yet support:

- true intraday line-move tracing
- provider-by-provider movement histories
- second-by-second lead-lag analysis

## Public conversation side

The current best low-cost mix remains:

- `Reddit` for fan and rival discourse
- `YouTube comments` for highly emotional postgame or highlight reaction
- `Bluesky` for open-public chatter
- `search/news discovery` for national narrative detection

This is timely enough for:

- daily or several-times-per-day updates
- pregame and postgame studies
- weekly fan-product features

This is not ideal for:

- truly high-frequency live trading-style products

## Prediction market side

For prediction markets, the realistic near-term path is:

- `Kalshi` public market data for accessible market-price snapshots
- `Polymarket` public data as a read-only market signal if useful

Important practical constraint:

- prediction markets are better for `futures`, `awards`, and `headline event probabilities` than for pretending we have a complete sportsbook-like game-side microstructure on day one

## What is feasible on the current stack and budget

Yes, this is doable without moving away from Python right now.

### Why it is feasible

- the public site can stay static
- heavy work happens in batch jobs
- the research layer mostly adds scheduled ingestion plus derived tables
- model cost is not the budget problem
- collection scope is the budget problem

### Sensible budget frame

Under a `$50/month` ceiling, a disciplined v1 is realistic.

The safest allocation is roughly:

- `CFBD Tier 2`: already part of the core stack
- `Reddit/Search collection`: modest `Apify` usage
- `YouTube`: official API first
- `Bluesky`: public endpoints
- `Anthropic`: selective strategy or summarization usage, not blanket processing

### Where the budget can fail

- trying to collect every team every day
- treating player-level coverage as always-on for the full sport
- scraping too much text that nobody reads

## Best v1 empirical design

Do **not** start with Granger-causality papers and advanced time-series jargon.

For this project, the best v1 design is:

### Step 1: Build a clean game-level dataset

One row per game with:

- team ids
- season and week
- opening spread and total
- closing spread and total
- line movement
- team strength features
- rank / brand / rivalry indicators
- weather
- sentiment features by source layer
- emotion features
- attention volume

### Step 2: Start with interpretable comparisons

Before formal models, answer:

- what happens when sentiment is in the top decile?
- what happens when sentiment and market disagree?
- what happens when rivalry heat is high?

This is much easier to trust and explain.

### Step 3: Run a baseline residual model

Model expected line movement from football variables first.

Then ask:

- does sentiment explain residual movement?

That is much better than throwing sentiment into a giant soup of features on day one.

### Step 4: Hold out future weeks

Use a strict time split.

Do not let future weeks leak into earlier model fitting.

### Step 5: Reserve event studies for phase two

Once we have snapshot tables, we can study:

- injury rumors
- quarterback benching talk
- poll releases
- viral highlight clips
- coach news

## Recommended product framing

The site should present this as `market + conversation intelligence`, not as a black-box predictive oracle.

The strongest fan-facing outputs are:

- `Fan Pulse`
- `National Mood`
- `Rival Heat`
- `Market Drift`
- `Model vs Market`
- `Why The Vibe Shifted`

That creates something more interesting than a dashboard and more honest than promising gambling alpha.

## Current technical recommendation

Build this in two phases.

### Phase 1

- use the current static-site and batch-pipeline architecture
- add sentiment source ingestion and derived aggregation tables
- focus on `open-to-close` line movement and weekly storylines
- keep coverage mostly `FBS`

### Phase 2

- add `game_line_snapshots`
- add `prediction_market_snapshots`
- add event-study tooling
- expand to awards and futures pages

## Sources checked

Primary or official sources reviewed for this memo:

- Durham and Perry, `The Impact of Sentiment on Point Spreads in the College Football Wagering Market`
  - https://www.ubplj.org/index.php/jpm/article/view/433
- Vaughan Williams and Reade, `Prediction markets, social media and information efficiency`
  - https://centaur.reading.ac.uk/66748/1/bigotgate_151215.pdf
- `Using Social Media to Identify Market Inefficiencies`
  - https://www2.gwu.edu/~forcpgm/2016-002.pdf
- Burnham, `Stance Detection: A Practical Guide to Classifying Political Beliefs in Text`
  - https://arxiv.org/abs/2305.01723
- Han, `A study of aspect-based sentiment analysis in social media`
  - https://mdsoar.org/items/dadb0ead-5c65-4bf6-b846-6167329ccf94
- `CFBD API tiers`
  - https://collegefootballdata.com/api-tiers
- `Kalshi market data quick start`
  - https://docs.kalshi.com/getting_started/quick_start_market_data
- `Polymarket quickstart`
  - https://docs.polymarket.com/quickstart
- `Polymarket geoblock`
  - https://docs.polymarket.com/api-reference/geoblock

Supporting internal project docs:

- `research/sentiment-analysis-research.md`
- `research/sentiment-implementation-spec.md`
- `docs/cfbd-tier2-and-safe-operations.md`
