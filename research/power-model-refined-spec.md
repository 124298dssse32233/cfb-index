# College Football Power Models: Refined Best-in-Class Spec

Research date: 2026-04-20

Update:

- user confirmed they already have `CollegeFootballData Tier 2`

## What this memo does

This is the next iteration of the model research.

The goal is not just to summarize what smart public systems do. The goal is to define the model architecture we should actually build if we want:

- a genuinely strong `predictive` model
- a separate `resume / accomplishment` model
- a credible `single ranking across FBS, FCS, DII, and DIII`
- something that stays realistic given `TheSportsDB`, `CollegeFootballData Tier 2`, and public data we can actually access

The biggest conclusion remains the same:

`Do not build one master ranking.`

Build two primary models:

1. `Power`
   Forward-looking predictive strength.

2. `Resume`
   Backward-looking accomplishment and quality of season.

Then let the site show both.

That is what the best systems implicitly or explicitly do:

- `FPI` is predictive and spread-scaled.
- `SP+` is predictive and forward-facing.
- `FEI` is predictive and efficiency-driven, with separate strength-of-record style outputs.
- `Massey` separates `Power` from `Rating`.
- `Sagarin` separates `PREDICTOR` from overall `RATING`.
- `ESPN Strength of Record` and `Game Control` are explicitly accomplishment tools.
- `Resume SP+` is a separate lens from predictive SP+.

## Sources that matter most

- ESPN FPI: https://www.espn.com/college-football/fpi
- ESPN SP+ preseason methodology: https://www.espn.com/college-football/insider/story/_/id/30847607/college-football-preseason-sp%2B-projections
- ESPN 2025 initial SP+ weights: https://www.espn.com/college-football/insider/story?id=44011175
- ESPN returning production / transfers: https://www.espn.com/college-football/story/_/id/48259759/college-football-returning-production-2026-notre-dame-texas
- ESPN 2025 final SP+ / Resume SP+: https://www.espn.com/college-football/story/_/id/46128861/2025-college-football-sp%2B-rankings-all-136-fbs-teams
- ESPN SOR and Game Control explainer: https://www.espn.com/blog/statsinfo/post/_/id/96761/determining-the-most-deserving-teams
- FEI methodology and ratings: https://bcftoys.com/2025-fplus and https://bcftoys.squarespace.com/2022-fei/
- Massey theory: https://masseyratings.com/theory/massey.htm
- Sagarin ratings page: https://www.sagarin.com/sports/cfsend.htm
- NCAA football stats hub across FBS/FCS/DII/DIII: https://www.ncaa.org/sports/2013/11/19/ncaa-football-statistics
- NCAA FCS-over-FBS results: https://www.ncaa.com/news/football/article/fcs-wins-vs-fbs-teams-all-time-victories-upsets
- NCAA DII-over-FCS examples: https://www.ncaa.com/news/football/article/2019-09-07/we-tracked-every-dii-football-vs-fcs-upset-saturday-heres-how-they
- NCAA DII-over-DI example: https://www.ncaa.com/news/football/article/2021-09-04/dii-football-southern-connecticut-state-football-shocks-di-opponent-central
- NCAA DII rankings: https://www.ncaa.com/rankings/football/d2/regional-rankings
- NCAA DIII NPI rankings: https://www.ncaa.com/rankings/football/d3
- TheSportsDB docs: https://www.thesportsdb.com/documentation
- CollegeFootballData tiers: https://collegefootballdata.com/api-tiers
- CollegeFootballData homepage: https://collegefootballdata.com/
- CFBD public docs mirror for key endpoints:
  - roster: https://www.postman.com/api-evangelist/college-football-data/request/kscfaxn/team-rosters
  - returning production: https://www.postman.com/api-evangelist/college-football-data/request/iurlc67/team-returning-production-metrics
  - recruiting teams: https://www.postman.com/api-evangelist/college-football-data/request/m6boj5y/team-recruiting-rankings-and-ratings
  - talent composite: https://www.postman.com/api-evangelist/college-football-data/documentation/35240-b0b710ef-eea4-4c9d-87a5-47150f83c4db?entity=request-35240-7c35248b-e57b-46bf-bb66-e4705975ad93
- On3 transfer portal index page: https://www.on3.com/transfer-portal/team-rankings/football/2026/
- Bayesian paired-comparison overview with order effects and hierarchical extensions: https://pmc.ncbi.nlm.nih.gov/articles/PMC9374650/
- Dynamic Bradley-Terry model for time-varying team strength: https://academic.oup.com/jrsssc/article/62/1/135/7083168

## Best ideas we should steal

### From FPI

- Put the predictive model on a `point-differential` scale.
- Make it feed `win probability`, `projected spread`, `projected score`, and `season simulations`.

ESPN describes FPI as a measure of team strength meant to be the best predictor of future performance, expressed as points above or below average, then used in simulations.

### From SP+

- Keep `offense`, `defense`, and ideally `special teams` separate.
- Use `preseason priors` heavily early, then phase them out.
- Build priors from:
  - previous season performance
  - returning production
  - recruiting / talent
  - recent history
- Treat the model as `predictive`, not as a reward-for-wins system.

Bill Connelly's recent SP+ descriptions are especially useful because they already adapted to the portal era. In 2025 he described current preseason projection inputs roughly as:

- more than 60% from last year's rating plus returning production
- about 14% from recruiting and transfer quality
- a bit more than 20% from recent history

That is a very strong blueprint.

### From FEI

- Adjust for opponent quality.
- Work at the `drive / possession` level when data allows.
- Remove or heavily downweight `garbage time`.
- Separate `strength` from `strength of record`.

FEI is valuable because it focuses on scoring advantage per non-garbage possession, which is closer to sustainable team quality than raw points.

### From Massey and Sagarin

- Separate `power` from `rating`.
- Use Bayesian or prior-based correction early.
- Let schedule strength be implicit in the network of opponents.
- Model `home-field advantage`.

Massey explicitly says preseason ratings should be used as priors whose influence fades over time. Sagarin explicitly publishes both an overall `RATING` and a `PREDICTOR`.

### From SOR / Resume SP+ / Game Control

- Make the resume model schedule-relative.
- Measure not just whether you won, but how much you exceeded or fell short of what a benchmark strong team would be expected to do.
- Penalize losses in a direct, human-legible way.

Resume SP+ is particularly useful because it offers a simple public framing:

- cap margins
- compare actual margin to what a benchmark elite team would do
- apply an explicit loss penalty

### From paired-comparison / Bayesian ranking literature

- Use `hierarchical priors` instead of hard-coded ceilings.
- Use `order effects` for home field.
- Allow ratings to `change over time`.
- Show `uncertainty` instead of pretending every cross-level comparison is equally certain.

This is the right answer to the "how do we rank DIII vs FCS vs FBS without fake caps?" problem.

## The biggest design decision: no ceilings, only priors

You said you do not want hard-coded ceilings and floors for different levels.

That instinct is correct.

The best solution is:

- `soft level priors`
- `team-specific deviations`
- `uncertainty bands`
- `bridge-game calibration`

Not:

- "No DIII team can rank above X"
- "FBS always outranks FCS"
- "DII gets a permanent 20-point penalty"

### The right structure

Every team gets a latent strength:

`team_strength = level_mean + conference_mean + team_deviation`

Where:

- `level_mean` is a soft prior for FBS/FCS/DII/DIII
- `conference_mean` is a soft prior inside each level
- `team_deviation` is the team's own actual strength relative to its peers

Important:

- `level_mean` is not a cap
- `conference_mean` is not a cap
- `team_deviation` can push a team well above its level mean

That means:

- a top FCS team can absolutely land near or above mediocre FBS teams
- a top DII team can land above weaker FCS teams
- a dominant DIII team can rise higher than people expect if the evidence supports it

This is not theoretical. Public mixed-subdivision systems already show this kind of behavior:

- Sagarin's mixed-subdivision ratings place FCS teams such as `Villanova` and `Harvard` among FBS teams on the same table.
- SportsRatings' all-division score-margin model for 2025 placed `North Dakota State` above multiple FBS teams and `Montana State` in the same neighborhood as several G5 programs.
- NCAA documented six `DII over FCS` upsets in one Saturday in 2019, plus later `DII over DI` examples.
- NCAA also keeps an official running record of `FCS over FBS` wins, which happen every season.

The lesson is not that levels are meaningless.

The lesson is:

`levels matter as priors and averages, not as walls.`

## The predictive model we should build

Suggested public name:

`Power`

Suggested internal framing:

`neutral-field expected scoring margin versus an average opponent`

### Model objective

For any future game, output:

- projected spread
- projected total
- projected final score
- win probability
- upset probability
- confidence interval

### Ideal model structure

#### Version A: best possible with mixed data quality

Use a dynamic Bayesian state-space model with separate units:

- `Offense`
- `Defense`
- `Special Teams` where data supports it
- `Home field`
- `Game volatility`

At the game level:

- expected margin comes from team strength gap plus home field
- expected total comes from offensive and defensive scoring environment
- variance is estimated separately by level pairing, because FBS-FCS and DIII-DIII games do not behave identically

For score generation:

- if we only have final scores, use a robust score model with overdispersion
- if we have drive/play data, switch FBS/FCS to possession efficiency and non-garbage possessions

### Practical build recommendation

#### For all teams, always available backbone

Use a `score-based opponent-adjusted model` that works with just schedules and results:

- robust margin model
- separate offense and defense if possible
- diminishing returns for blowouts
- home-field advantage
- weekly recency weighting
- preseason priors that decay

This is the universal layer because it can cover FBS, FCS, DII, and DIII.

#### For FBS/FCS where better data exists

Overlay an `advanced-data enhancement layer`:

- drive efficiency
- play-by-play or advanced box scores
- success / explosiveness style proxies
- special teams
- garbage-time filtering

This gives us an asymmetrical system:

- all levels get ranked
- FBS/FCS are modeled more richly where the data supports it
- DII/DIII remain on the same scale through the common score-based backbone

That is better than forcing fake precision for DII/DIII or excluding them.

### Preseason priors

This is where a lot of edge lives.

The best public guidance here comes from SP+, plus the broader paired-comparison literature and the reality of portal-era roster churn.

#### Team prior mean

At preseason, set each team's prior strength from:

1. `Previous season final rating`
2. `Multi-year program baseline`
3. `Returning production / continuity`
4. `Roster talent`
5. `Transfer delta`
6. `Coaching continuity / change`
7. `Level and conference prior`

#### Recommended starting formula

For `FBS/FCS` teams with richer offseason data:

`Preseason Prior =`

- `40% previous season final Power`
- `20% three-year program baseline`
- `15% returning production`
- `10% team talent / recruiting`
- `10% transfer delta`
- `5% coaching continuity / change`

For `DII/DIII` teams without reliable recruiting/portal feeds:

`Preseason Prior =`

- `50% previous season final Power`
- `25% three-year program baseline`
- `10% returning roster continuity proxy`
- `10% official division-local ranking prior`
- `5% manual offseason adjustment`

Division-local ranking prior can come from public official sources such as:

- NCAA DIII `NPI`
- NCAA DII regional rankings
- D2Football / coaches-poll style inputs if we use them only as offseason priors, not in-season truth

### Transfers and lower-level movement

This is a subtle but important point.

Bill Connelly's 2026 returning-production notes are one of the best public clues here:

- incoming transfer production should be folded into returning production
- production from `sub-FBS transfers` should get `only half-credit` because translation upward is inconsistent

We should generalize that idea.

#### Our transfer rule

For roster priors, player movement across levels should be translated with `level-translation discounts`.

Example principle:

- same-level transfer: full credit
- FCS to G5: near full credit
- FCS to top-end P4: meaningful but discounted credit
- DII to FCS/FBS: larger discount
- DIII to DII/FCS: even larger discount

This should not be a one-size-fits-all hard table forever.
It should be estimated from historical player movement where we have data and manually initialized where we do not.

But the principle is right:

`moving up levels should help a prior, but not count 1:1.`

### In-season updating

The in-season update needs to balance three things:

- sustainability
- responsiveness
- protection against one-week noise

Recommended rules:

1. Use `weekly full-model re-estimation`, not only sequential Elo-style nudges.
2. Keep a `recency weight`, but do not overreact to one game.
3. Cap margin influence to prevent stat-padding.
4. Downweight or trim extreme garbage-time results.
5. Phase out preseason priors continuously from Week 1 through roughly Week 8-10.

### Home-field advantage

Do not use one fixed HFA for all NCAA football.

Estimate at least:

- a global home-field value
- level-pair adjustments
- optionally conference or team-specific deviations once enough data exists

Sagarin explicitly publishes home advantage, and the paired-comparison literature treats order effects as a standard model extension.

### What the predictive model should show on the site

- `Power Rank`
- `Projected Spread`
- `Projected Score`
- `Win Probability`
- `Power Trend`
- `Confidence`
- `Cross-Level Confidence`

That last field matters.

A DIII team ranked 74th nationally might have a point estimate above a weak FCS team, but if the graph connectivity is weak, we should say so.

That makes the model smarter and more trustworthy.

## The resume model we should build

Suggested public name:

`Resume`

This model answers:

`How impressive has the season actually been, given the schedule and the actual outcomes?`

### Model objective

The resume model should reward:

- quality wins
- road wins
- beating strong opponents by more than expected
- avoiding bad losses
- consistency across the full schedule

It should not try to guess who would win next week.

### Best structure

The best overall version is a blend of three ideas:

1. `Record Strength`
   How hard would this record be for a benchmark strong team to achieve?

2. `Performance Over Expectation`
   How much better or worse did you perform than expected game by game?

3. `Result Quality`
   How good are your best wins, how bad are your worst losses, and how many landmines did you avoid?

### Component 1: Record Strength

This is the SOR-style backbone.

Simulate each schedule using benchmark teams:

- `Elite benchmark`
- `Top-25 benchmark`
- `Top-50 benchmark`

Then ask:

- how often would each benchmark team match or exceed the team's actual record?

That gives us three useful public-facing numbers:

- `Resume-E`
- `Resume-25`
- `Resume-50`

This is better than a single black-box resume rank because it explains difficulty on multiple scales.

It also borrows a great FEI idea: separate record strength against different benchmark team classes.

### Component 2: Performance Over Expectation

This is our version of `Game Control` / `Resume SP+`.

For each game:

- take the team's `pregame expected margin`
- compare it to the actual margin
- cap the margin residual
- add location context
- weight by opponent quality

This avoids the classic resume problem where:

- a team gets equal credit for sleepwalking past a bad opponent and crushing a good one

Recommended game residual:

`Game Residual = Capped(Actual Margin - Expected Margin)`

Then apply:

- `road bonus`
- `neutral-site adjustment`
- `bad-loss multiplier`
- `weak-opponent blowout cap`

### Component 3: Result Quality

This is the explicitly human-readable layer.

Track:

- best wins
- worst losses
- wins over highly rated teams
- losses to low-rated teams
- away wins against strong teams

This can remain a smaller component in the full formula, but it is critical for trust and explainability.

### Recommended starting formula

Initial build:

`Resume Score =`

- `50% Record Strength`
- `30% Performance Over Expectation`
- `20% Result Quality`

Then tune weights by backtesting and sanity review.

If we want a more CFP-like public mode later, we can increase result quality slightly.
If we want a more analytics-pure mode, we can increase record strength and performance-over-expectation.

### Loss penalties

Resume SP+ is useful here because it does something simple and legible:

- compare performance to elite expectation
- then apply an explicit penalty for losses

We should do the same.

Recommended rule:

- every loss carries a base penalty
- bad losses carry an additional penalty
- close losses to elite teams carry a much smaller penalty

### What the resume model should show on the site

- `Resume Rank`
- `Best Wins`
- `Worst Loss`
- `Record Strength`
- `Resume Trend`
- `Performance vs Expectation`
- `Game Control`

The site should never hide the split between `Power` and `Resume`.
That split is part of the product.

## The all-level ranking problem

This is the hardest part and the part that can make the site special.

### The correct answer

Build one connected all-NCAA rating graph with:

- team-level latent strength
- level priors
- conference priors
- bridge-game calibration
- uncertainty estimates

### How to estimate level priors without hard caps

Use historical `bridge games`:

- FBS vs FCS
- FCS vs DII
- DII vs DI/FCS where available
- DII vs DIII and other lower-level bridges where available
- reclassification seasons
- transfer movement up and down levels as soft auxiliary evidence

This estimates:

- average level gap
- level-pair variance
- how quickly evidence should move a team away from its prior

### Why this is better than manual floors

Because real college football is lumpy.

Examples from current public evidence:

- NCAA's official FCS-over-FBS list shows these upsets happen regularly.
- NCAA documented `six DII-over-FCS upsets` in a single Saturday in 2019.
- NCAA also documented `Southern Connecticut State (DII) beating Central Connecticut State (DI)` in 2021.
- Sagarin's mixed-subdivision ratings routinely interleave FCS teams with FBS teams.

So we want a system that says:

- `most of the time` the higher level is stronger
- `sometimes` a lower-level elite is absolutely better than a higher-level struggler

That is exactly what a hierarchical prior model is built to express.

### Critical implementation rule

Do not treat cross-level rankings as equally certain.

Instead publish:

- `point estimate`
- `uncertainty`
- `cross-level confidence`

This is a major product differentiator.

Human pollsters and most public rankings do not do this well.

## Data reality: what SportsDB can and cannot support

### What TheSportsDB can support well

Officially documented and useful:

- team identities
- schedules
- full team season schedule
- event results
- venue data
- artwork / branding assets

That is enough for:

- score-based predictive modeling
- game-by-game rating changes
- year-by-year results
- schedule strength
- cross-level results networks

### What TheSportsDB does not solve by itself

Not enough for best-in-class modeling by itself:

- reliable returning production
- structured recruiting data
- transfer portal quality
- dependable play-by-play
- drive-level efficiency
- robust advanced team metrics
- rich team talent priors

So if we stay `SportsDB only`, we can still build:

- a very respectable all-level score-based model
- a strong resume model

But we cannot honestly claim to match FPI / SP+ / FEI quality on the predictive side.

## What CFBD Tier 2 changes

Because you already have `CollegeFootballData Tier 2`, we should stop thinking about CFBD as an optional enhancement.

It should be treated as a core model input for `FBS/FCS`.

That matters because the official tier page currently shows Tier 2 includes:

- team statistics
- player statistics
- recruiting data
- betting lines
- advanced metrics
- opponent-adjusted metrics
- live scoreboard
- live play-by-play

And the documented endpoint set includes:

- `roster`
- `player/returning`
- `recruiting/teams`
- `talent`
- drive data
- advanced box scores
- play-by-play

That immediately upgrades what is realistically possible:

- preseason priors become much better
- FBS/FCS predictive modeling can move much closer to SP+ / FEI style structure
- game projections can be trained and calibrated against richer feature sets
- resume quality can use stronger opponent-adjusted baselines

What it does `not` change:

- DII/DIII still do not have the same rich offseason and play-level public data coverage
- the all-level model should still be hybrid, with richer FBS/FCS inputs and score-network calibration across all levels

## The cheapest strong supplement

If you did not already have an advanced source, the best supplement would be:

`CollegeFootballData`

Why:

- their official pricing page currently lists:
  - `Tier 1: $1/month`
  - `Tier 2: $5/month`
- they explicitly include:
  - recruiting data
  - advanced metrics
  - opponent-adjusted metrics
  - team stats
  - player stats
  - betting lines
- their documented endpoints include:
  - `roster`
  - `player/returning`
  - `recruiting/teams`
  - `talent`
  - drive data
  - advanced box scores
  - play-by-play

This is an absurdly good complement to SportsDB.

### Recommended stack

#### Actual stack to build around

- `TheSportsDB`
  Use for universal schedules, results, artwork, broad site coverage, and team/event presentation.

- `CollegeFootballData Tier 2`
  Use as the default FBS/FCS analytics layer for offseason priors, advanced predictive features, opponent-adjusted metrics, drive/play features, and richer team-quality estimates.

- `NCAA official ranking/stat pages`
  Use as public reference priors for DII/DIII where structured roster/talent data is weaker.

- `Optional manual offseason layer`
  Use for lower-division coaching changes, returning stars, and context not covered by APIs.

### Important caveat

CFBD is strongest in `FBS/FCS`.

That means our final production model should be intentionally hybrid:

- `FBS/FCS`: enhanced with advanced-data priors and richer in-season signals
- `DII/DIII`: score-network model plus official public priors plus light human offseason adjustments

That is not a weakness.
That is the honest best-in-class solution under real-world public data constraints.

## What I would actually build

If the goal is "best overall," this is the architecture I would ship:

### Model 1: Power

`Power = predictive strength`

Core:

- one all-NCAA score-based backbone
- dynamic offense/defense ratings
- home field
- diminishing returns on blowouts
- preseason priors that fade
- level/conference priors with uncertainty

Enhancements:

- CFBD-driven FBS/FCS offseason priors
- CFBD drive / play / advanced-stat layer for FBS/FCS
- special teams split where supported
- betting-line based calibration checks for predictive accuracy

### Model 2: Resume

`Resume = accomplishment`

Core:

- schedule-relative record strength via simulations
- game-by-game performance over expectation
- explicit win-quality / bad-loss layer

Outputs:

- overall Resume rank
- Resume-E
- Resume-25
- Resume-50
- best wins
- worst losses

### Cross-level engine

- no ceilings
- no floors
- hierarchical priors
- bridge-game calibration
- cross-level uncertainty

### Human offseason layer

For the lower levels especially, add a curated preseason notebook or admin tool with:

- coaching changes
- returning star QB / All-America players
- major portal departures if known
- classification / scholarship context
- notable injuries or sanctions

That is not cheating.
That is what it takes to be better than brittle public-only models.

## Validation plan

### Predictive validation

Backtest:

- spread MAE
- score RMSE
- win-probability log loss
- Brier score
- calibration by probability bucket
- performance by season week
- performance by level pairing

Especially hold out:

- FBS vs FCS
- FCS vs DII
- DII vs DI/FCS bridge games

That is where the all-level system earns trust.

### Resume validation

Backtest:

- agreement with informed postseason consensus
- stability week to week
- quality-win identification
- bad-loss identification
- schedule-relative fairness across levels

Resume models are not judged by spread accuracy. They are judged by whether they tell the truth about what happened.

## Final recommendation

If you want the absolute best product we can realistically build:

1. Keep `Power` and `Resume` separate forever.
2. Use `SportsDB` as the universal site-data backbone.
3. Use your existing `CollegeFootballData Tier 2` membership as the default FBS/FCS analytics engine, not as an optional add-on.
4. Build the all-level ranking with `hierarchical priors`, not hard caps.
5. Show `uncertainty` and `cross-level confidence`.
6. Add a small `manual offseason adjustment` layer for under-covered lower-division teams.

That combination gives you something stronger than most public sites:

- more honest than poll-style rankings
- more interpretable than a black-box model
- more ambitious than FBS-only analytics sites
- more credible across divisions than sites that hard-code level ceilings

## Most important sentence

The best all-division college football model is not one that pretends levels are identical, and not one that hard-codes rigid level walls.

It is one that treats levels as `strong priors with uncertainty`, then lets actual games, connected schedules, roster signals, and time-varying performance decide where each team truly belongs.
