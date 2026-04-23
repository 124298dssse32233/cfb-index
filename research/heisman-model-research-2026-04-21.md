# Heisman Model Research

Date: April 21, 2026

This memo answers a specific product question:

How should this project build a serious, week-by-week model that ranks every FBS player by likelihood of winning the Heisman Trophy?

The answer is not "sort players by yards or touchdowns."

A world-class Heisman model has to behave like an award-voting model, not a fantasy leaderboard. It needs to know that quarterback is the default winning archetype, that team success matters enormously, that the award is decided before bowls, that only a few dozen players receive any votes in a typical year, and that rare exceptions like Charles Woodson, Travis Hunter, Ashton Jeanty, or Diego Pavia are exactly why the model should use strong priors instead of hard-coded gates.

## Executive summary

The best production design is a five-module system:

1. `Merit`
   A position-aware player performance score built from opponent-adjusted production, usage, dominance within position, and team context.

2. `Candidacy`
   A model for whether a player is genuinely in the Heisman conversation and likely to receive any votes.

3. `Voter salience`
   A model for how visible and nationally legible the player's case is to actual Heisman voters.

4. `Ballot share`
   A model for how much of the Heisman vote pool the player is expected to capture, conditioned on being a viable candidate.

5. `Forward simulation`
   A remaining-season path model that separates "best case so far" from "best chance to win by December."

The final public output should be:

- `nowcast_rank`
- `forecast_rank`
- `win_probability`
- `finalist_probability`
- `any_vote_probability`
- `expected_ballot_share`
- `latent_heisman_score`
- a stable full-FBS ordinal rank

That lets a Toledo running back rank somewhere deep in the list without pretending he has a realistic chance equal to a fringe SEC quarterback. The long tail still gets ordered, but the top of the board remains faithful to how the award actually behaves.

The strongest tracker should expose two distinct views:

1. `Nowcast`
   If voting happened today, how would the board look?

2. `Forecast`
   By the end of the regular season and conference championship games, who is most likely to actually win?

That split matters because a Heisman race is not only about what has happened. It is also about how much schedule, visibility, and statistical runway remain.

## Hard constraints from the real award

These are not optional modeling opinions. They are structural facts the model should respect.

### 1. The Heisman is a regular-season award

The Heisman Trust's balloting explainer says the award is decided before bowl season because the award is intended to honor the regular season.

Model implication:

- never use bowls or CFP semifinal/final performance in training labels or live features
- the final "official" model snapshot should stop after conference championship games
- late regular-season and conference-title-week games should carry especially high leverage because the same official explainer notes that in 2017, 89% of voters waited until after the final games were played before submitting ballots

Source:
- https://www.heisman.com/articles/heisman-balloting-how-it-works-2/

### 2. Ballots are ranked 3-2-1 ballots

The official Heisman balloting explainer says voters select three players and allocate 3 points for first, 2 for second, and 1 for third.

Model implication:

- do not model this as a simple binary winner-only task
- model either vote share or ranked-ballot utility
- store season-specific vote totals because the voter count can change over time

Source:
- https://www.heisman.com/articles/heisman-balloting-how-it-works-2/

### 3. The Heisman field is tiny compared to the FBS player universe

The official Heisman balloting explainer notes that 43 players received votes in 2017 and 48 in 2016.

Model implication:

- a one-stage "winner classifier" is the wrong framing
- the model should first learn who enters the vote-getting set at all
- class imbalance is extreme, so use staged targets

Source:
- https://www.heisman.com/articles/heisman-balloting-how-it-works-2/

### 4. Team success matters a lot

The Heisman Trust's wins/losses article says no Heisman winner has played for a team with four or more losses since 1969, and only one player in history won while playing on a team with a losing record.

Model implication:

- team wins, team rank, team title contention, and team visibility should be treated as structural features
- these should not be weak side inputs
- a player on a 7-5 or 6-6 team can still rank in the full list, but his win probability should be crushed unless he is producing one of the rarest seasons in modern history

Source:
- https://www.heisman.com/articles/wins-losses-and-the-heisman/

### 5. Position matters heavily

The Heisman Almanac snippet published on Heisman.com lists winners by position through the 2025 award:

- Running Back: 42
- Quarterback: 38
- Wide Receiver: 4
- End: 2
- Cornerback: 1
- CB/WR: 1

Model implication:

- position priors are mandatory
- but they should be learned, shrunk, and updateable, not hard-coded as absolute bans

Source:
- https://www.heisman.com/wp-content/uploads/2025/12/2025-Heisman-Trophy-Almanac-Final.pdf?x32098=

### 6. Modern Heisman is especially quarterback-centric

From the official winners list through the 2025 award, quarterbacks won 21 of the 26 Heismans from 2000 through 2025.

Model implication:

- the model's baseline should strongly prefer quarterbacks in the modern era
- running backs still need a real path
- wide receivers and defenders need extraordinary seasons plus team and narrative support

Sources:
- https://www.heisman.com/heisman-winners/
- https://www.heisman.com/wp-content/uploads/2025/12/2025-Heisman-Trophy-Almanac-Final.pdf?x32098=

### 7. Defense is not impossible, but the threshold is absurdly high

Official Heisman pages describe Charles Woodson as the only player to win while playing significant minutes on both sides of the ball since the two-platoon era began, and Travis Hunter as the first full-time two-way player to win since the early 1960s and the first to do so while playing major snaps both ways since Woodson.

Model implication:

- pure-defense candidates should get a very low baseline
- true two-way players need their own treatment, not a generic "DB" bucket
- defenders can still become finalists or even runner-up, as the official finalist lists show with Jabrill Peppers in 2016, Chase Young in 2019, and Aidan Hutchinson in 2021

Sources:
- https://www.heisman.com/heisman-winners/charles-woodson/
- https://www.heisman.com/heisman-winners/travis-hunter/
- https://www.heisman.com/voting-records/

### 8. Group of Five and non-blueblood candidates must remain alive

Official finalist lists show:

- 2024: Ashton Jeanty of Boise State was a finalist
- 2025: Diego Pavia of Vanderbilt was a finalist

Model implication:

- do not build a Power Four-only gate
- conference and brand matter, but they should be features, not absolute eligibility rules
- the correct design is "high hurdle for nontraditional candidates," not "impossible"

Source:
- https://www.heisman.com/voting-records/

## Product target: what the model should estimate

For each player `i` at week `w`, estimate:

1. `P_any_vote_i,w`
2. `P_finalist_i,w`
3. `E_share_i,w`
   Expected share of total ballot points
4. `P_win_i,w`

Then rank the entire FBS player universe primarily by `P_win_i,w`.

For a best-in-class product, maintain two parallel ranking views:

1. `nowcast_rank_i,w`
- sort by hidden current-ballot utility using only games already played

2. `forecast_rank_i,w`
- sort by end-of-regular-season win probability after simulating the remaining path

The `nowcast` is the cleanest answer to:

- who has earned the best Heisman case so far?

The `forecast` is the cleanest answer to:

- who is most likely to be holding the trophy in December?

Because most players will have tiny win probabilities, use a stable tie-break stack:

1. `P_win_i,w`
2. `P_finalist_i,w`
3. `P_any_vote_i,w`
4. `E_share_i,w`
5. `merit_score_i,w`

This gives you a full sorted list without lying about the meaning of the headline number.

## Useful mental model: every voter has a hidden full ballot

The user's framing is helpful and, mathematically, it is very close to the right way to think about the problem.

Imagine that every Heisman voter actually has a complete ordering of all FBS players:

```text
Player A > Player B > Player C > ... > Player N
```

In the real world, the Heisman process only reveals the top 3 names on each ballot.
So the official vote is best understood as a truncated or censored view of a deeper full ranking.

That leads to a cleaner hidden-variable target:

- `latent_heisman_score_i,w`

Interpretation:

- if voters were forced to rank every FBS player at week `w`, this is the player's expected position on those hidden full ballots
- the public full-FBS ranking should sort primarily by this latent score
- the official top-3 Heisman result is then just the visible top slice of that hidden ordering

This framing is especially useful for the long tail.

Why:

- most FBS players will have almost zero actual win probability
- but they still are not equal
- a strong Group of Five running back, an elite shutdown corner on a fringe top-25 team, and a productive but non-special Power Four receiver should not all collapse into the same bucket

So the right modeling story is:

1. estimate a latent full ordering for all players
2. derive real-world top-3 style outcomes from that ordering

## Best mathematical framing

If we were designing the cleanest underlying award model from scratch, the object we would estimate is a season-week utility:

```text
U_i,w = latent Heisman utility for player i at week w
```

Higher `U_i,w` means the player would tend to appear above other players on voters' hidden full ballots.

Then:

- public full-FBS rank = order by `U_i,w`
- `P_any_vote` = probability that `U_i,w` places the player inside the vote-receiving tier
- `P_finalist` = probability that `U_i,w` places the player in the top 4
- `P_win` = probability that `U_i,w` is highest in the field

In theory, the most principled way to fit this is with a listwise ranking model such as:

- Plackett-Luce
- Thurstone / Bradley-Terry style latent-comparison models
- listwise learning-to-rank on season snapshots

with the critical twist that the observed Heisman ballots are only partial rankings.

So the official top-3 ballot is not the ranking itself.
It is a censored observation of the top of the ranking.

That said, there is an important practical limitation:

- we usually do not have every individual ballot for every season in a machine-friendly historical dataset
- what we reliably have is aggregate outcome information: winner, finalists, total points, and vote counts

Because of that, the best production design for this repo is still:

- latent full-ordering mindset
- merit layer
- candidate gate
- voter-salience layer
- ballot-share model
- win simulation
- forward-season simulation

In other words:

- conceptually, use the hidden full-ballot view
- operationally, estimate it through staged observable targets

## What "world-class" means here

A world-class Heisman model should do five things at once:

1. Respect historical structure
- quarterback bias
- team record bias
- regular-season timing
- defensive rarity

2. Use opponent-adjusted player quality, not just raw box-score totals

3. Understand candidacy and narrative
- being statistically good is not the same as being in the Heisman race

4. Work weekly
- not just one final end-of-year board

5. Rank all FBS players
- including long-tail players with effectively zero chance but non-identical profiles

To become the best tracker rather than just a strong model, add two more standards:

6. Separate current case from future path
- a great tracker should distinguish "best résumé today" from "best chance by December"

7. Approximate actual voter exposure
- not every elite season is equally visible to voters
- salience should be modeled, but carefully regularized

## Recommended model architecture

The strongest practical design is a five-module system:

1. `Merit`
2. `Candidacy`
3. `Voter salience`
4. `Ballot share`
5. `Forward simulation`

### Layer 1: Merit

This layer answers:

"How strong is this player's season on the field, relative to what Heisman-level seasons look like at his position?"

This is not yet a Heisman probability. It is a football-performance layer.

Recommended output:

- `merit_score`
- `position_peer_percentile`
- `dominance_gap`

Implementation:

- build separate merit submodels by role family:
  - QB
  - RB
  - WR/TE
  - defense
  - two-way / hybrid
- standardize the outputs onto one latent scale

Why this split matters:

- quarterback and running back seasons have different statistical shapes
- defensive candidacy is driven more by outlier creation and rare events than by tackle volume
- a two-way player should not be reduced to only offense or only defense

### Layer 2: Candidacy gate

This layer answers:

"Is this player realistically in the Heisman vote universe?"

Target options:

- binary `received_any_votes`
- or binary `top_10_vote_getter`

This is the most important layer for ranking all FBS players.

Why:

- the real universe is roughly "a few dozen vote earners out of thousands of FBS players"
- a Toledo running back can still rank above an average Power Four backup because the gate output is continuous

### Layer 2B: Voter salience

This is one of the main additions that can make the tracker genuinely better than a stats board.

This layer answers:

"How visible, discussable, and nationally legible is this player's season to actual Heisman voters?"

This should not dominate the model.
But it absolutely exists in the real award.

Recommended salience features:

- AP rank and AP poll points of the player's team
- CFP rank when available
- number of games versus ranked teams
- number of wins over ranked teams
- game leverage and upset leverage
- conference championship path
- recent high-leverage performance spikes
- national-window proxy if schedule metadata exists
- optional narrative acceleration proxy from external sentiment systems if added later

The key idea:

- voters do not literally watch every FBS player the same way
- salience is part of the mechanism that turns merit into ballots

### Layer 3: Ballot share model

This layer answers:

"Among real candidates, how much of the Heisman vote would this player get?"

Target:

- normalized ballot-point share

Recommended form:

- softmax utility model across a season's candidate pool
- or, in the cleaner theoretical framing, a Plackett-Luce style top-of-ranking model where the observed Heisman ballot is only the revealed top 3 of a hidden full ordering

Conceptually:

```text
utility_i = position_prior_i + candidate_strength_i + narrative_strength_i
predicted_share_i = exp(utility_i) / sum_j exp(utility_j)
```

This is a better fit than plain regression on winner label because it respects the fact that voters distribute support across multiple plausible candidates in the same season.

The share model should also include interaction effects that simpler systems often miss:

- same-team candidate cannibalization
- same-position substitution near the top of the board
- conference clustering
- "one clear offensive engine" bonus versus "shared spotlight" penalty

### Final layer: Win simulation

Convert expected share into actual `P_win`.

Recommended approach:

- estimate season-level residual uncertainty from historical backtests
- simulate vote-share draws around the predicted shares
- compute how often each player finishes first

This gives:

- `P_win`
- `P_finalist`
- stable uncertainty-aware ordering

### Forward simulation

This is the biggest upgrade if the goal is "best tracker on the planet."

Most public Heisman boards are really only current leaderboards.
The best tracker should simulate the path from today to the voting deadline.

For each player, simulate:

1. remaining team results
2. remaining player opportunity
3. remaining player efficiency and raw output
4. resulting candidacy and ballot-share movement

Then aggregate to produce:

- end-of-season `P_win`
- end-of-season `P_finalist`
- distribution of likely finish positions

This is the right place to use the existing project strengths:

- power ratings
- game lines
- schedule data
- opponent strength

## Why a single one-stage model is not enough

If you train only on "winner vs. everyone else," you run into four problems:

1. only one positive label per season
2. the model will overlearn quarterback and top-team priors in a brittle way
3. long-tail ranking quality will be poor
4. it will not distinguish "interesting dark horse" from "not remotely in the race"

The correct structure is:

```text
player season quality -> candidate gate -> ballot share -> win probability
```

## Data strategy for this repo

This repo already has a lot of the team context needed for a strong Heisman model.

Live CFBD inspection on April 21, 2026 confirmed that `TeamsApi.get_fbs_teams(year=2025)` returns 136 FBS teams.

Model implication:

- the ranking universe is large enough that long-tail ordering logic matters
- many players will share effectively zero win probability, so secondary ordering keys are required

Another practical observation from live testing:

- bursty roster ingestion can trigger temporary `429 Too Many Requests` rate limits even when monthly quota is not exhausted

Engineering implication:

- build the player ingestion with caching, batching, retry-with-backoff, and resumable checkpoints
- otherwise the tracker will be brittle during large preseason or repair syncs

### Existing strengths in the workspace

The current database already includes:

- `teams`
- `games`
- `game_lines`
- `official_rankings`
- `team_game_advanced_stats`
- `power_ratings_weekly`
- `resume_ratings_weekly`
- `team_talent_snapshots`
- `returning_production`
- `transfer_entries`
- `player_source_ids`
- `players`
- `roster_entries`

That is good news because the team-context side of the model can directly reuse work already done for `Power` and `Resume`.

### Important current gap

As of April 21, 2026:

- `players` is empty in the local database
- `roster_entries` is empty
- `official_rankings` is empty locally

The schema is ready, but the player-side ingestion is not populated yet.

### Recommended new tables

Add these tables:

1. `player_week_stats`
- one row per player, season, week
- raw counting stats and per-game normalized stats

2. `player_week_adjusted_metrics`
- opponent-adjusted efficiency and value metrics
- separate metric rows or wide columns

3. `player_week_usage`
- usage share and role concentration

4. `heisman_vote_results`
- one row per player-season with official Heisman finish data

5. `heisman_features_weekly`
- materialized training and inference feature store

6. `heisman_rankings_weekly`
- public output table

### Recommended `heisman_vote_results` columns

- `season_year`
- `player_id`
- `player_name_raw`
- `team_name_raw`
- `position_raw`
- `winner_flag`
- `finalist_flag`
- `place`
- `first_place_votes`
- `second_place_votes`
- `third_place_votes`
- `total_points`
- `ballot_count`
- `vote_share`

This table should be sourced from official Heisman results, not third-party recap articles.

Primary source:
- https://www.heisman.com/voting-records/

## Recommended source usage

### Core sources

Use official and project-aligned sources first:

- Heisman Trust for labels and award mechanics
- CFBD for team context, rosters, player usage, player value metrics, polls, recruiting, talent, transfers, and play data

Primary references:
- https://www.heisman.com/articles/heisman-balloting-how-it-works-2/
- https://www.heisman.com/voting-records/
- https://www.heisman.com/heisman-winners/
- https://collegefootballdata.com/api-tiers
- https://blog.collegefootballdata.com/api-v2-is-now-in-general-availability/
- https://graphqldocs.collegefootballdata.com/

### Optional premium prior

If you want the best preseason and early-season realism, add a sportsbook-market prior.

Reason:

- Heisman futures odds compress a lot of information that is otherwise hard to recreate early:
  - expected team success
  - returning reputation
  - media visibility
  - likely volume
  - awards buzz

This should be one feature, not the target and not the whole model.

If you buy an odds feed, treat it as:

- highly useful preseason
- still useful through September
- less important once enough on-field evidence exists

Examples of commercial sports-data providers with odds infrastructure:
- https://docs.therundown.io/
- https://sportsdata.io/live-odds-api

## Player features: what actually matters

The model needs both football features and award-voting features.

### Shared feature groups

Every player-week should include:

1. Position and role
- position bucket
- two-way flag
- class year
- returning starter proxy

2. Team context
- current team power
- current team resume
- current win percentage
- expected final wins
- AP rank
- Coaches rank
- CFP rank when available
- conference strength
- strength of schedule

3. Attention and candidacy
- preseason team ranking
- preseason player prior
- prior-year production share
- prior-year award attention if available
- whether the player is the clear offensive centerpiece

4. Recency and moments
- exponentially weighted recent form
- last 2 to 4 games
- conference title game participation
- performance vs ranked teams
- upset wins as an underdog
- game leverage weighted spikes
- signature-game detector

5. Salience and visibility
- current AP poll points
- current CFP rank when available
- wins on nationally meaningful stages
- ranked-opponent exposure
- late-season relevance
- media/sentiment velocity if optional narrative feed is added

6. Dominance versus peers
- national percentile within position
- conference percentile within position
- gap to next-best player on his own team
- gap to national leader at the same position

### Signature moments and leverage

This deserves explicit treatment.

The best Heisman cases are often not just cumulative.
They contain one or more games that sharply change national perception.

The tracker should compute a `heisman_moment_index` from:

- opponent quality
- team leverage entering the game
- game result surprise
- player outlier performance relative to baseline
- week of season

This should be a feature, not an editorial override.

### Quarterback features

Quarterback features should dominate the model because modern Heisman does.

Recommended QB features:

- opponent-adjusted passing value
- total offense share
- passing usage overall
- passing downs usage
- red-zone touchdown responsibility
- interception avoidance
- rushing contribution
- explosive play rate
- total touchdowns responsible for
- yards per team pass attempt
- EPA or WEPA on designed runs and scrambles if available

Practical CFBD-aligned inputs:

- `AdjustedMetricsApi.get_adjusted_player_passing_stats`
- `PlayersApi.get_player_usage`
- player-season or player-game box scores
- play-by-play derived QB rushing split if needed

For the forecast model, quarterbacks should also get:

- projected remaining touchdowns responsible for
- probability of adding one or more signature wins
- downside from interception-prone tails in high-leverage games

### Running back features

Recommended RB features:

- opponent-adjusted rushing value
- rushing usage
- share of team rushing attempts
- share of team rushing TDs
- rushing yards per game
- explosive run rate
- red-zone share
- scrimmage-yard share
- receiving involvement
- games over 150 and 200 yards

Important design choice:

- do not reward only volume
- do not reward only efficiency
- Heisman backs need both

This is how a Jeanty-like season remains live.

For the forecast model, running backs need special attention to:

- carry sustainability
- game-script dependence
- offensive line continuity
- probability of one or two monster spotlight games

### Wide receiver / tight end features

Recommended WR/TE features:

- target share
- yard share
- touchdown share
- explosive reception rate
- yards per route proxy if routes are available
- receiving value relative to other WR seasons
- return value if material

CFBD does not currently expose a clean adjusted receiving metric through the same REST path used for adjusted passing and rushing.

So the best production approach is:

- compute receiving efficiency and dominance from play-by-play or game-level player stats
- then standardize it into the same merit framework

Wide receivers also need stronger same-team interaction terms than quarterbacks or running backs, because:

- elite WR candidacy often depends on a quarterback sharing or siphoning attention
- this can create real Heisman ceiling limits even for extraordinary seasons

### Defensive features

Defensive Heisman candidacy should be modeled, but with a much lower prior.

Recommended defensive features:

- sacks
- tackles for loss
- interceptions
- passes defended
- forced fumbles
- defensive touchdowns
- havoc share
- pressure or hurry proxies
- performance against elite opponents
- team defense strength

Important caution:

- tackle volume is not a Heisman feature by itself
- defense should be about rare impact events, disruption, and outlier season shape

### Two-way features

Two-way players need their own path.

Recommended two-way features:

- offensive merit
- defensive merit
- offensive usage share
- defensive event share
- snap or role breadth proxy
- return-game value if real
- unique-season flag for players clearing thresholds on both sides

This is the correct place to handle Woodson and Hunter style seasons.

Two-way players should also get a rarity bonus term that is learned from history but heavily regularized.

Reason:

- a truly unique season can outperform what a position-only prior would predict
- but the model should only pay for uniqueness when both production surfaces are real

## Team-context features are not optional

The Heisman is partly a player award and partly a "best season on a nationally relevant team" award.

For that reason, the model should explicitly use:

- `power_ratings_weekly`
- `resume_ratings_weekly`
- AP rank and AP poll points
- Coaches rank
- CFP rank when available
- team win percentage
- projected final wins
- conference championship path

The player model should sit on top of the team model, not beside it.

That is one of the biggest leverage advantages this repo already has.

For the forecast view, team context should be split into:

- what the team has already done
- what the team is still likely to do

That distinction is critical because:

- a player on a top-15 team with three major games left may have more Heisman runway than a player on a top-8 team whose best résumé moments are already over

## Position priors: strong, but learned

The model needs position priors, but not hard rules.

Recommended approach:

- use hierarchical intercepts by role family
- let those intercepts vary by era bucket
- shrink defensive roles strongly downward

Example role families:

- `QB`
- `RB`
- `WR_TE`
- `DEFENSE`
- `TWO_WAY`
- `OTHER`

This achieves the right behavior:

- quarterbacks lead by default
- running backs remain live
- wide receivers require rare dominance
- pure defense is almost always a longshot
- two-way outliers have an actual path

To make this stronger, estimate the priors by era bucket, such as:

- 2000 to 2009
- 2010 to 2016
- 2017 to present

This avoids letting older running-back-heavy eras distort the modern quarterback baseline too much.

## Historical targets: what to train on

The strongest training stack uses multiple targets.

### Target 1: any-vote

Binary label:

- `1` if player received any official Heisman votes
- `0` otherwise

Use for:

- candidate gate
- full-FBS ranking quality

### Target 2: finalist

Binary label:

- `1` if official finalist

Use for:

- top-of-board quality

### Target 3: normalized point share

Continuous label:

- `total_points / (3 * ballot_count)`

Use for:

- final vote-share estimation

### Target 4: winner

Binary label:

- `1` only for the winner

Use only as a secondary evaluation target, not the sole training label.

## Weekly snapshot construction

The training set should be built from historical player-week snapshots, not just final season totals.

For each season and each week:

1. build features using only information available through that week
2. join final Heisman results for that season
3. train the model to estimate what the race looked like at that point

This makes the product genuinely useful during the season.

One more refinement:

- label leakage prevention must be obsessive

For each historical week:

- only include polls published by that week
- only include games completed by that week
- only include remaining-schedule assumptions that would have been knowable then

Anything less will make the backtest look smarter than the real tracker will be.

Recommended phase buckets:

- preseason
- weeks 1 to 4
- weeks 5 to 8
- weeks 9 to conference championships

The model can either:

- fit separate calibrators by phase
- or include phase interactions in the main model

## Suggested modeling stack

### Production-first recommendation

Use:

1. position-specific merit models
- gradient boosted trees or generalized additive models

2. global candidacy model
- LightGBM / CatBoost / XGBoost style classifier
- calibrated with isotonic regression

3. voter-salience model
- lightweight model or calibrated feature layer for visibility and narrative exposure

4. ballot-share model
- softmax regression or other utility-based share model on candidate pool

5. simulation layer
- Monte Carlo over ballot-share residuals

6. remaining-season projection layer
- player stat projection
- team win-path projection
- salience-path projection

Why this is the best first build:

- strong nonlinear performance
- manageable engineering complexity
- easy weekly inference
- straightforward backtesting

### Research-grade upgrade

If you want the cleanest mathematical framing later, upgrade the share layer to a hierarchical Bayesian utility model with season and position effects.

That is more elegant, but not necessary for a strong first production version.

An especially strong research-grade version would combine:

- listwise partial-ranking likelihood for the top of the ballot
- hierarchical era and position priors
- explicit same-team interaction effects
- forward simulation for future path dependence

That is the closest thing to a true end-to-end Heisman election model.

## Evaluation: how to know the model is good

Evaluate by week and by season.

### Core metrics

- winner log loss
- finalist log loss
- any-vote Brier score
- NDCG@10
- Recall@4 for finalists
- mean rank of actual winner
- calibration error for `P_win`

### Sanity checks

The model should usually satisfy:

- top of board dominated by quarterbacks unless a truly rare season appears elsewhere
- a great Group of Five season can break into the top tier
- a pure defender can rank highly only when both production and team context are extreme
- players on middling teams should rarely show meaningful win probability
- multiple same-team players can appear, but one should usually separate as the main candidate
- nowcast and forecast can disagree in intuitive ways

Examples of healthy disagreement:

- a running back may lead the nowcast because of current production
- a quarterback may lead the forecast because of superior remaining schedule leverage and title path

### Backtest style

Use leave-one-season-out validation:

- train on all seasons except one
- predict the held-out season week by week
- repeat

This is especially important because the label count is small.

## Important CFBD implementation notes

### What works well

Live inspection on April 21, 2026 showed the official CFBD Python client supports:

- `TeamsApi.get_fbs_teams`
- `TeamsApi.get_roster`
- `RankingsApi.get_rankings`
- `PlayersApi.search_players`
- `PlayersApi.get_player_usage`
- `PlayersApi.get_transfer_portal`
- `AdjustedMetricsApi.get_adjusted_player_passing_stats`
- `AdjustedMetricsApi.get_adjusted_player_rushing_stats`

Those are enough to build much of the candidate and context layer.

### What needs validation before production

In live testing on April 21, 2026, the client path for `StatsApi.get_player_season_stats` returned empty lists for several offensive categories that should have had populated data.

Implication:

- do not trust that one client method blindly
- validate the raw REST endpoint directly
- or upgrade to a richer GraphQL workflow if you move to Tier 3
- or compute player-week stats from play-by-play / game player stat data

This matters because offensive counting stats remain essential for Heisman-style visibility.

That means player stat ingestion should be treated as a first-class data quality problem, not a background ETL detail.

### Why GraphQL is attractive

The CFBD GraphQL docs list:

- `adjustedPlayerMetrics`
- `gamePlayerStat`
- `poll`
- `athlete`
- `position`

That is a very strong long-term fit for a player-award model.

But GraphQL requires Tier 3 or higher access, so treat it as an upgrade path rather than a current dependency.

Source:
- https://graphqldocs.collegefootballdata.com/

## How the full ranking should work

The public table should include every active FBS player.

### Do not filter to only "known candidates"

That defeats the user's stated goal.

Instead:

- rank everybody
- keep the top section driven by `P_win`
- let the long tail be ordered by progressively weaker but still meaningful signals

For best product quality, show both:

- `If voting today`
- `Most likely to win`

That prevents one of the most common public misunderstandings:

- "best case so far" is not the same thing as "best chance by December"

### Recommended public columns

- rank
- player
- team
- position
- nowcast rank
- forecast rank
- Heisman win probability
- finalist probability
- candidate score
- key reason

### Recommended explanation strings

Each player should get a short explanation generated from top features, for example:

- "Elite opponent-adjusted passing value on a top-5 team"
- "Historic rushing dominance keeping a non-blueblood candidate alive"
- "Defensive outlier season, but position and team context remain major hurdles"

This is important because award models are narrative-heavy and users will want to understand why someone is high or low.

## How to handle a Toledo running back

This is the test case that reveals whether the model is thoughtful.

A Toledo running back should not be:

- hard-removed because he is from the MAC
- or inflated because he leads in raw rushing yards against weak defenses

The correct behavior is:

- he gets a real merit score if he is efficient, dominant, and carries a large team share
- he gets a lower candidacy score if Toledo is not nationally relevant
- he gets heavily penalized in the final share layer unless the season becomes nationally exceptional
- he can still move sharply upward in the forecast if Toledo has high-leverage remaining games and he is projected to keep stacking outlier production

That is how you end up with plausible ranks such as:

- top 50 for a true national dark horse
- top 200 for a monster Group of Five season with limited team ceiling
- top 500 to 800 for a strong but not nationally meaningful year

That is much more honest than flattening the whole back half of FBS into ties.

## Concrete implementation sequence for this repo

### Phase 1: data plumbing

1. Extend the CFBD client wrappers to cover:
- rankings
- roster
- FBS team discovery
- player search
- player usage
- adjusted player passing metrics
- adjusted player rushing metrics
- transfer portal

2. Populate player tables:
- `players`
- `player_source_ids`
- `roster_entries`

3. Build or validate player stat ingestion:
- direct REST
- GraphQL upgrade
- or play-by-play derived stats

### Phase 2: labels

4. Create `heisman_vote_results` from official Heisman data

5. Backfill seasons at least from 2000 forward

Reason:

- that gives enough modern-era signal while avoiding older-era positional patterns dominating the model too heavily

### Phase 3: feature store

6. Build `heisman_features_weekly`

Include:

- player merit stats
- team context
- priors
- recency
- peer dominance
- role flags

### Phase 4: modeling

7. Train merit submodels
8. Train candidate gate
9. Train voter-salience model
10. Train vote-share model
11. Add remaining-season forecast simulation
12. Calibrate probabilities
13. Run weekly backtests

### Phase 5: product surface

14. Materialize `heisman_rankings_weekly`
15. Add `nowcast` and `forecast` views
16. Add explanations and position badges
17. Add a "dark horses" slice and a "defenders watch" slice
18. Add "Heisman moment" movers after major weekends

## Final recommendation

If the goal is to build something that feels smart, realistic, and durable, the guiding rule should be:

Do not model the Heisman as "best player." Model it as "best player season that voters are likely to reward."

That means:

- strong position priors
- strong team-context features
- explicit voter-salience modeling
- opponent-adjusted player merit
- weekly candidate gating
- vote-share modeling
- remaining-season path simulation
- full-FBS ranking with stable tie-breaks

That is the cleanest path to a board where:

- the top looks realistic
- the top is better than a pure stat board because it distinguishes current résumé from future path
- a Boise State or Toledo star can still surface when deserved
- defenders are present but correctly treated as outliers
- the long tail stays ordered instead of collapsing into zeros

## Sources reviewed

- Heisman balloting explainer
  - https://www.heisman.com/articles/heisman-balloting-how-it-works-2/
- Heisman voting records and finalists
  - https://www.heisman.com/voting-records/
- Heisman winners archive
  - https://www.heisman.com/heisman-winners/
- Charles Woodson winner page
  - https://www.heisman.com/heisman-winners/charles-woodson/
- Travis Hunter winner page
  - https://www.heisman.com/heisman-winners/travis-hunter/
- Heisman wins/losses historical note
  - https://www.heisman.com/articles/wins-losses-and-the-heisman/
- Heisman Almanac PDF snippet surfaced via official search
  - https://www.heisman.com/wp-content/uploads/2025/12/2025-Heisman-Trophy-Almanac-Final.pdf?x32098=
- CollegeFootballData API tiers
  - https://collegefootballdata.com/api-tiers
- CFBD API v2 announcement
  - https://blog.collegefootballdata.com/api-v2-is-now-in-general-availability/
- CFBD GraphQL docs
  - https://graphqldocs.collegefootballdata.com/
- Plackett-Luce listwise learning with partitioned preference
  - https://proceedings.mlr.press/v130/ma21a.html
- Optional odds provider docs
  - https://docs.therundown.io/
  - https://sportsdata.io/live-odds-api
