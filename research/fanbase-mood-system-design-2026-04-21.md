# Fanbase Mood System Design

Research date: 2026-04-21

Companion files:

- `research/fan-intelligence-flagship-roadmap-2026-04-21.md`
- `research/proprietary-fan-intelligence-ideation-2026-04-21.md`
- `research/conversation-intelligence-v1-data-plan-2026-04-21.md`
- `output/anthropic-fanbase-mood-system-review.md`

## Purpose

This memo turns the core product instinct into a concrete system:

- quantify how bullish or bearish each fanbase is
- estimate whether that belief is grounded or ahead of reality
- measure how violently it swings with results
- capture how unified or fractured the fanbase is internally

The goal is not to create one magic score.

The goal is to create a **fanbase belief profile** that feels:

- explainable
- arguable
- funny in the right way
- grounded enough to publish repeatedly

## Core decision

The right product is **not**:

- one global sentiment score per team

The right product is:

- a small set of explainable axes that together describe a fanbase's temperament

That means the site should say:

- `this fanbase is bullish`
- `it is more bullish than the evidence supports`
- `it swings hard after results`
- `it is currently split internally`

instead of:

- `Team X has a sentiment score of 0.71`

## The four core axes

The cleanest public system is a four-axis profile.

### 1. Belief Level

Question:

- `How bullish or bearish is this fanbase about its own team right now?`

This is the core `Fan Pulse` axis.

Public labels:

- `Very Bullish`
- `Bullish`
- `Cautiously Hopeful`
- `Uneasy`
- `Bearish`

Internal metric:

- `belief_score`

Best inputs from the current schema:

- `team_week_conversation_features.net_sentiment_score`
- `mean_sentiment_score`
- `positive_doc_count`
- `negative_doc_count`
- `trust_share`
- `fear_share`
- `sample_quality_score`

Recommended internal logic:

- build a weighted composite from net sentiment, positive-vs-negative share, and trust-minus-fear emotion balance
- do **not** let attention volume itself define belief
- downweight low-quality samples

Simple v1 formula shape:

- `belief_score_raw = 0.60 * net_sentiment_score + 0.25 * (trust_share - fear_share) + 0.15 * sentiment_balance`
- where `sentiment_balance = (positive_doc_count - negative_doc_count) / max(mention_count, 1)`

Then:

- rescale to a simple `-100 to +100` internal band
- bucket into public labels

### 2. Reality Gap

Question:

- `Is this fanbase's level of belief supported by structural reality, or is it ahead of the evidence?`

This is the axis that unlocks:

- `Realistic`
- `Unrealistic`
- `Pessimistic`
- `Overconfident`

Important rule:

- `realistic` is **not** detected from text directly
- it is derived by comparing fan belief to football structure

Public module names:

- `Reality Check`
- `Belief vs Reality`

Public labels:

- `Grounded`
- `A Little Ahead Of The Evidence`
- `Hype Train`
- `A Little Too Low`
- `Doomer Ball`

Internal metrics:

- `structural_support_score`
- `belief_gap_score`

Recommended structural support inputs:

### Offseason support inputs

- preseason power percentile
- returning production percentile
- talent / recruiting percentile
- transfer / continuity stability signal

### In-season support inputs

- current power rating percentile
- market expectation or implied win probability where available
- residual offseason prior early in the season

Practical rule:

- use forward-looking structure more than resume
- resume can help context, but belief should be compared mainly against what the team appears to be, not just what it has already banked

Simple v1 formula shape:

- offseason: `0.45 * preseason_power + 0.25 * returning_production + 0.20 * talent + 0.10 * continuity`
- in-season: `0.55 * power_percentile + 0.30 * market_expectation + 0.15 * preseason_prior`

Then:

- `belief_gap_score = belief_percentile - structural_support_score`

Interpretation:

- positive gap = fanbase is more optimistic than the evidence
- negative gap = fanbase is lower on the team than the evidence

This is the best place for `Delusion Meter`, but with an important product nuance:

- `Delusion Meter` is a great leaderboard and article label
- `Reality Check` is the safer default label on team pages

### 3. Swing Factor

Question:

- `How quickly and violently does this fanbase mood swing with results?`

This is the most important refinement to the concept.

It turns the project from:

- static sentiment labeling

into:

- fanbase behavior tracking

Public module names:

- `Swing Meter`
- `Belief Shift`
- `Roller Coaster Index`

Public labels:

- `Steady`
- `Reactive`
- `Swingy`
- `Full Roller Coaster`

Internal metrics:

- `volatility_score`
- later `result_sensitivity_score`

### Best v1 version

For v1, keep it simple:

- rolling average of absolute week-over-week change in `belief_score`

Example:

- `volatility_score = avg(abs(belief_score_t - belief_score_t-1)) over last 3-5 weekly windows`

This is easy to explain and easy to ship.

### Better v2 version

Once pregame/postgame windows are consistently populated:

- measure belief change from pregame to postgame
- compare that change to how surprising the result was

That becomes:

- `result_sensitivity_score`

Conceptually:

- if a small, expected event creates a huge mood swing, the fanbase is fragile and highly reactive
- if even a big surprise barely moves mood, the fanbase is emotionally steady or already anchored

This is where `how quickly it swings with results` becomes truly special.

Recommended later formula shape:

- `result_sensitivity = abs(postgame_belief - pregame_belief) / max(surprise_index, floor)`

Where `surprise_index` can use:

- closing spread surprise
- model win-probability surprise
- or a simpler upset banding system in early versions

### 4. Cohesion

Question:

- `Is the fanbase broadly aligned, or is it in a civil war?`

This is distinct from belief level.

A fanbase can be:

- bullish and unified
- bullish but fractured
- bearish and unified
- mixed and at war with itself

Public module names:

- `Cohesion`
- `Fanbase Civil War Watch`

Public labels:

- `United`
- `Tense`
- `Split`
- `Civil War`

Internal metric:

- `disagreement_score`

Recommended inputs:

- positive share
- negative share
- neutral share
- document-level polarity spread when available later

Simple v1 logic:

- use a combination of sentiment entropy and direct positive-vs-negative polarization

Practical formula shape:

- `polarization = 4 * pos_share * neg_share`
- `disagreement_score = 0.7 * polarization + 0.3 * entropy(pos, neutral, neg)`

This works because:

- a 50/50 positive-negative split is more interesting than bland neutrality
- not every mixed sample is truly a civil war

## The two best comparison axes

After the four core axes, two comparison metrics matter most.

### Respect Gap

Question:

- `Are this team's fans more optimistic or pessimistic than outsiders?`

Definition:

- `fan belief - national belief`

Public use:

- homepage leaderboard
- team card secondary stat

This is stronger than a raw sentiment score because disagreement is the story.

### Rival Heat

Question:

- `How much mockery, fear, or obsession is coming from rival audiences?`

Definition:

- a weighted rival attention plus rival negativity measure

Public use:

- team page
- rivalry pages
- weekly leaders

## Public-facing product shape

The best fan-facing package is a **Team Mood Card** with:

- `Fan Pulse`
- `Reality Check`
- `Swing Meter`
- `Cohesion`
- `Respect Gap`
- `Rival Heat`
- `Top Storylines`

### The team card should answer

- `How do our fans feel?`
- `Are we grounded or getting carried away?`
- `Do we overreact to results?`
- `Are we united or fighting?`
- `Do outsiders respect us?`

## Archetypes that fans will instantly understand

A big improvement is to combine the axes into fanbase archetypes.

Do not make these the only thing published, but they are excellent editorial packaging.

### Good archetypes

- `Grounded Believers`
- `Hype Train`
- `Scarred But Sane`
- `Too Low On Ourselves`
- `Doomer Ball`
- `Roller Coaster`
- `Civil War`

### Suggested mapping

- high belief + low reality gap = `Grounded Believers`
- high belief + high positive reality gap = `Hype Train`
- low belief + roughly grounded gap = `Scarred But Sane`
- low belief + strong negative reality gap = `Too Low On Ourselves`
- high volatility = `Roller Coaster`
- high disagreement = `Civil War`

This gives the site more personality than sterile scorecards.

## What should be public versus internal only

This distinction matters a lot.

### Public-facing by default

- `Fan Pulse`
- `Reality Check`
- `Swing Meter`
- `Cohesion`
- `Respect Gap`
- `Rival Heat`
- `Belief Shift`

### Internal or lightly exposed only

- raw sentiment model outputs
- exact composite weights
- low-confidence samples
- per-source diagnostic breakdowns
- detailed sarcasm and toxicity controls
- experimental `result_sensitivity_score` until pre/post windows are strong enough

Rule:

- fans should see readable conclusions and maybe a simple score band
- they should not see a pile of fragile classifier internals

## Naming guidance

Use sports-media language, not analytics-lab language.

### Good public names

- `Fan Pulse`
- `Reality Check`
- `Swing Meter`
- `Belief Shift`
- `Respect Gap`
- `Rival Heat`
- `Civil War Watch`
- `Hope Inventory`

### Bad public names

- `sentiment coefficient`
- `polarity output`
- `behavioral volatility estimator`
- `optimism classifier`
- `engagement-weighted emotion score`

## What would be fake precision

Avoid these traps.

### 1. One-number certainty

Do not act like:

- `belief score = 73.4`

is a precise truth.

Use:

- bands
- labels
- arrows
- week-over-week movement

### 2. Directly labeling realism from text alone

You cannot read comments and decide:

- `this fanbase is realistic`

without comparing them to football context.

### 3. Publishing on thin samples

Minimum publish rules should remain aggressive:

- at least `20` resolved documents
- at least `5` distinct authors when available
- avoid cases where one thread dominates the sample

### 4. Letting rivals define fan mood

Keep audience buckets separate.

Never let:

- rival mockery

bleed into:

- the team's actual fan pulse

### 5. Using the harshest labels everywhere

`Delusion Meter` and `Doomer Ball` are fun.

But they work better as:

- leaderboards
- weekly columns
- feature cards

than as the permanent default tone on every team page.

## Best v1

The strongest v1 is:

- `FBS-only`
- `team-level`
- mostly `weekly`
- centered on the four-axis fanbase profile

### Ship first

- `Fan Pulse`
- `Reality Check`
- `Swing Meter` using week-over-week movement
- `Cohesion`
- `Respect Gap`

### Delay until later

- player-level mood
- fully robust pregame/postgame elasticity
- prediction-market integrations
- universal lower-division coverage

## Best immediate build sequence

1. define `belief_score` from existing weekly fan-bucket features
2. define `structural_support_score` from existing preseason and model context
3. compute `belief_gap_score`
4. compute rolling `volatility_score`
5. compute `disagreement_score`
6. render a `Team Mood Card` from those outputs

## Final product test

If a fan sees the card and says:

- `that is exactly how our fanbase acts`

the system is working.

If the reaction is:

- `I don't know what this number means`

the system is failing, no matter how smart the math looks internally.
