# College Football Model Math Spec

Research date: 2026-04-20

This document converts the earlier research into an implementation-ready model spec.

It is intentionally opinionated. The goal is not to list every possible modeling choice. The goal is to define the exact architecture we should build first.

## Product stance

We will maintain two separate public models:

1. `Power`
   Predictive. Answers who would be favored tomorrow.

2. `Resume`
   Retrospective. Answers who has built the strongest season so far.

We will also maintain one shared hidden layer:

3. `All-Level Strength Graph`
   The cross-division engine that keeps FBS, FCS, DII, and DIII on one scale without hard ceilings or floors.

## Data stance

### Default source usage

- `TheSportsDB`
  Canonical site presentation backbone for team identity, schedules, event results, league metadata, venue info, and image assets.

- `CollegeFootballData Tier 2`
  Canonical analytics backbone for FBS and FCS.
  Use for rosters, recruiting, talent, advanced box scores, opponent-adjusted metrics, betting lines, weather, drives, and play-by-play.

- `NCAA official ranking/stat pages`
  Public offseason and in-season reference priors for DII and DIII.

- `Manual curated layer`
  Small but important offseason adjustments for lower levels, coaching changes, star QB continuity, and known roster shocks not covered cleanly by public APIs.

### Coverage rule by level

- `FBS/FCS`
  Full predictive stack.

- `DII/DIII`
  Shared score-based backbone, official-public priors, lighter offseason modeling, and more uncertainty.

This is the honest best-in-class solution under current public-data constraints.

## Canonical notation

For team `i` in season `s` before week `w`:

- `P_i,w`
  Overall predictive power in points above average on a neutral field.

- `O_i,w`
  Offensive rating in points above average against an average defense.

- `D_i,w`
  Defensive rating in points prevented versus an average offense.

- `ST_i,w`
  Special teams rating in points above average.

- `T_i,w`
  Tempo rating used only for totals and pace-sensitive projections.

- `L_i`
  NCAA level for team `i`: FBS, FCS, DII, or DIII.

- `C_i`
  Conference for team `i`.

- `sigma_i,w`
  Posterior uncertainty of the team's predictive rating.

We will always expose:

- `P_i,w`
- `Resume_i,w`
- `sigma_i,w`
- `cross_level_confidence_i,w`

## Model 1: Power

## What Power means

`Power` is the expected neutral-field scoring margin versus an average NCAA team on the shared site scale.

In public terms:

- if Team A is `+18.2` and Team B is `+10.7`
- Team A should be about `7.5` points better on a neutral field before matchup, pace, and venue adjustments

## Power decomposition

We decompose power into four latent components:

```text
P_i,w = O_i,w + D_i,w + ST_i,w
```

`T_i,w` is tracked separately because tempo matters more for totals than spread.

This decomposition gives us:

- predictive spreads from `P`
- predictive scores from `O`, `D`, `ST`, and `T`
- a cleaner team page story
- a way to diagnose whether a team wins with offense, defense, or both

## Preseason prior model

The preseason prior is where we should steal most aggressively from SP+, roster-based systems, and common sense.

We do not set a team's initial power directly from polls.
We estimate it from structured inputs translated into points.

### Shared prior structure

For every team:

```text
P_i,0 ~ Normal(mu_i,0, sigma_i,0^2)
```

Where:

```text
mu_i,0 = level_mu[L_i] + conf_mu[C_i] + team_prior_i
```

And:

```text
team_prior_i = offseason_prev_i
              + offseason_program_i
              + offseason_roster_i
              + offseason_talent_i
              + offseason_transfer_i
              + offseason_coach_i
              + offseason_manual_i
```

### FBS/FCS prior formula

For FBS and FCS, use:

```text
team_prior_i =
    0.45 * PrevSeasonPts_i
  + 0.15 * ProgramBaselinePts_i
  + 0.15 * ReturningProductionPts_i
  + 0.10 * TalentPts_i
  + 0.08 * TransferPts_i
  + 0.04 * CoachPts_i
  + 0.03 * QBContinuityPts_i
```

These weights are the starting point, not sacred law.
They intentionally reflect the public SP+ pattern:

- strong weight on prior-year quality
- meaningful but not overwhelming weight on returning production
- real but smaller weight on recruiting and transfers
- modest weight on multi-year history and continuity

### DII/DIII prior formula

For DII and DIII, use:

```text
team_prior_i =
    0.55 * PrevSeasonPts_i
  + 0.25 * ProgramBaselinePts_i
  + 0.10 * OfficialRankPts_i
  + 0.05 * ContinuityProxyPts_i
  + 0.05 * ManualOffseasonPts_i
```

Why this is different:

- lower divisions do not have equally rich recruiting and portal feeds
- official public rankings are more useful as soft prior input
- we need a small manual layer to avoid obviously stale priors

### Translating offseason features into points

Each offseason input should live in the same unit: `points above average`.

That means we do not directly plug raw recruiting ranks or returning-production percentages into the formula.
We first convert them into point values using historical regressions.

#### Previous season points

```text
PrevSeasonPts_i = 0.70 * FinalPower_i,last_year
                + 0.20 * FinalPower_i,two_years_ago
                + 0.10 * FinalPower_i,three_years_ago
```

Use only completed seasons where the team played a minimum-quality schedule.

#### Program baseline points

```text
ProgramBaselinePts_i = weighted_mean_of_last_3_to_5_year_end_ratings
```

This is separate from `PrevSeasonPts_i` because some programs repeatedly reload better than one-season snapshots imply.

#### Returning production points

Train a regression from CFBD returning-production features to future in-season power:

```text
ReturningProductionPts_i =
    b0
  + b1 * z(returning_offense_pct)
  + b2 * z(returning_defense_pct)
  + b3 * z(returning_qb_prod)
  + b4 * z(returning_ol_prod)
```

If side-of-ball metrics are available, build:

- `ReturningProductionPtsOff_i`
- `ReturningProductionPtsDef_i`

Then map those to `O_i,0` and `D_i,0`.

#### Talent points

Use CFBD talent and recruiting signals:

```text
TalentPts_i =
    c0
  + c1 * z(team_talent_score)
  + c2 * z(recruiting_4yr_avg)
  + c3 * z(blue_chip_ratio)
```

If `blue_chip_ratio` is not directly available, omit it and re-estimate the coefficients.

#### Transfer points

Transfer is important, but the public structured data is less stable than recruiting.

Start with:

```text
TransferPts_i =
    d1 * z(team_transfer_class_score)
  + d2 * z(incoming_qb_delta)
  - d3 * z(outgoing_production_loss)
```

If we do not have stable structured team transfer scores for all teams:

- keep this feature for FBS/FCS only
- fallback to `0`
- let `ManualOffseasonPts_i` absorb known major portal shocks

#### Coaching points

```text
CoachPts_i =
    e1 * I(returning_head_coach)
  + e2 * I(returning_off_coord)
  + e3 * I(returning_def_coord)
  + e4 * recent_coach_performance_delta
```

This is a small term.
It should matter, but it should not swing ratings wildly on its own.

#### QB continuity points

```text
QBContinuityPts_i =
    f1 * I(returning_starting_qb)
  + f2 * z(returning_qb_epa)
  + f3 * z(qb_experience)
```

This is separated because quarterback continuity often deserves its own explicit treatment.

### Prior uncertainty

We should not start every team with the same uncertainty.

Use:

```text
sigma_i,0 =
    4.5 for FBS with full CFBD prior coverage
    5.5 for FCS with strong CFBD coverage
    7.0 for DII
    7.5 for DIII
```

Then adjust:

- `-0.5` if prior-quality inputs are unusually rich and stable
- `+0.5 to +1.5` if team continuity is unclear, coach changed, or data coverage is weak

This matters because the model should move lower-coverage teams faster when evidence arrives.

## Cross-division priors without hard caps

This is one of the core product ideas.

We do not set ceilings or floors by level.
We set `soft level means` and let the schedule graph move teams off those means.

### Hierarchical prior

```text
level_mu[FBS] = fixed reference at 0 for scaling
level_mu[FCS] ~ Normal(hist_gap_FCS_vs_FBS, tau_level^2)
level_mu[DII] ~ Normal(hist_gap_DII_vs_FCS, tau_level^2)
level_mu[DIII] ~ Normal(hist_gap_DIII_vs_DII, tau_level^2)
```

Each conference also gets a soft prior:

```text
conf_mu[c] ~ Normal(level_mu[level_of_c], tau_conf^2)
```

Each team then gets:

```text
mu_i,0 = level_mu[L_i] + conf_mu[C_i] + team_prior_i
```

This gives us:

- realistic average separation between levels
- no artificial walls
- room for exceptional lower-level teams to outrank weak higher-level teams

### How to estimate level gaps

Estimate level gaps from:

- historical bridge games
- historical betting lines where available
- reclassification years
- rare but informative cross-level upsets

Use the shared predictive model itself to re-estimate these gaps annually.
Do not hard-code them forever.

## In-season update model

The full production model should be a dynamic regularized system, not plain Elo.

### Weekly state evolution

For each team component:

```text
theta_i,w ~ Normal(theta_i,w-1, q_theta^2)
```

Where `theta` can be:

- `O`
- `D`
- `ST`
- `T`

Suggested starting weekly evolution noise:

```text
q_O  = 1.1
q_D  = 1.0
q_ST = 0.5
q_T  = 0.4
```

Interpretation:

- offense and defense are allowed to move modestly week to week
- special teams and tempo move more slowly

### Observation layers

For every completed game, collect:

#### Universal layer, all levels

- final score
- capped margin
- location
- rest differential if available
- season phase

#### Rich layer, FBS/FCS

- drive success
- points per drive
- EPA or PPA
- success rate
- explosiveness
- finishing drives
- havoc
- field position
- garbage-time filtered variants
- weather

#### Training-only calibration layer

- closing betting spread
- closing total

Use betting lines for training and calibration.
Do not let the public model become "the market with lipstick."

### Score projection equations

For game `g` with home team `h` and away team `a`:

```text
mu_home =
    base_pts[level_pair_g, week_bucket]
  + O_h,w
  - D_a,w
  + 0.5 * (ST_h,w - ST_a,w)
  + 0.5 * HFA[level_pair_g]
  + pace_adj_g
  + env_adj_g
  + matchup_adj_home_g
```

```text
mu_away =
    base_pts[level_pair_g, week_bucket]
  + O_a,w
  - D_h,w
  + 0.5 * (ST_a,w - ST_h,w)
  - 0.5 * HFA[level_pair_g]
  + pace_adj_g
  + env_adj_g
  + matchup_adj_away_g
```

Then:

```text
pred_margin_g = mu_home - mu_away
pred_total_g  = mu_home + mu_away
```

### Pace adjustment

```text
pace_adj_g = p1 * T_h,w + p2 * T_a,w
```

Start with `p1 = p2 = 0.5`.
Tune later with out-of-sample total prediction error.

### Environment adjustment

Environment matters mostly for totals.

```text
env_adj_g =
    w1 * weather_wind_g
  + w2 * weather_precip_g
  + w3 * altitude_flag_g
  + w4 * extreme_temp_flag_g
```

Use this only where we have reliable data.
If weather is missing, default to `0`.

### Matchup adjustment

Only use matchup adjustments where the data is rich enough.
That means mostly FBS and FCS.

```text
matchup_adj_home_g =
    m1 * (adj_rush_off_h - adj_rush_def_a)
  + m2 * (adj_pass_off_h - adj_pass_def_a)
  + m3 * (adj_explosive_off_h - adj_explosive_def_a)
  + m4 * (adj_havoc_allowed_h - adj_havoc_created_a)
```

Do the same symmetrically for the away team.

For DII and DIII, set `matchup_adj = 0` until rich structured features exist.

## Opponent-adjusted feature engine

This is where CFBD's public ridge-regression methodology is extremely useful.

For FBS and FCS, each week we should re-estimate opponent-adjusted versions of key stats using a ridge model:

```text
stat ~ offense_team + defense_team + home_field + constant
```

Run this for:

- EPA or PPA per play
- success rate
- explosiveness
- passing efficiency
- rushing efficiency
- finishing drives
- havoc
- field position

Then store:

- raw value
- opponent-adjusted value
- percentile

These opponent-adjusted features then feed the predictive update model.

## Weekly estimation objective

At the end of each week, estimate the current latent team states by minimizing:

```text
Loss =
    lambda_margin * Sum huber(capped_margin_g - pred_margin_g)
  + lambda_points * Sum [(home_pts_g - mu_home_g)^2 + (away_pts_g - mu_away_g)^2]
  + lambda_adv * Sum robust(feature_residuals_g)
  + lambda_market * Sum (closing_spread_g - pred_margin_g)^2
  + lambda_prior * Sum ((theta_i,w - theta_i,w-1)^2 / q_theta^2)
  + lambda_ridge * ||Theta_w||^2
```

Suggested starting values:

```text
lambda_margin = 0.40
lambda_points = 0.15
lambda_adv    = 0.30
lambda_market = 0.10
lambda_prior  = 0.05
```

Notes:

- `huber()` protects against one weird game blowing up the ratings
- `capped_margin_g` should cap blowouts, recommended at `28`
- `feature_residuals_g` should use garbage-time filtered advanced stats where possible
- `lambda_market` is for calibration, not imitation

### Garbage time rule

Use non-garbage variants whenever possible.

If only final scores exist:

```text
capped_margin_g = clamp(actual_margin_g, -28, 28)
```

If play-by-play exists:

- remove or sharply downweight plays after the win probability becomes extreme
- compute non-garbage PPA, success rate, and finishing drives

### Prior fade-out schedule

Preseason priors should not vanish instantly or linger forever.

Use:

```text
prior_weight_week(w) = max(0.10, exp(-0.35 * (w - 1)))
```

Approximate behavior:

- Week 1: heavy prior influence
- Week 4: meaningful but reduced
- Week 8: mostly earned on-field signal
- Week 10+: only a light stabilizer remains

## Win probability and score simulation

After we estimate team states, simulate games.

### Base win probability

```text
win_prob_home = Phi(pred_margin_g / sigma_game_g)
```

Where:

- `Phi` is the standard normal CDF
- `sigma_game_g` is matchup-specific game volatility

Estimate `sigma_game_g` by level pairing:

- FBS vs FBS
- FBS vs FCS
- FCS vs FCS
- FCS vs DII
- DII vs DII
- DII vs DIII
- DIII vs DIII

This is important because cross-level games are not all equally noisy.

### Simulation layer

Run Monte Carlo simulations for:

- individual games
- weekly slates
- season outcomes
- championship odds

Use simulated scores, not just win/loss draws, so downstream products can include:

- projected record distributions
- expected points for and against
- upset watch

## Cross-level confidence

Cross-level comparison should not be presented with fake certainty.

### Connectivity-adjusted confidence

Define:

```text
connectivity_i,w = log(1 + bridge_games_2hop_i,w) / log(12)
```

Clamp to `[0, 1]`.

Then:

```text
cross_level_confidence_i,w =
    100
  * connectivity_i,w
  * max(0, 1 - sigma_i,w / 10)
```

Interpretation:

- a team with low posterior uncertainty and lots of bridge-game connectivity gets high cross-level confidence
- a team deep in an isolated DIII cluster gets a lower confidence score even if the point estimate is strong

This is one of the most important honesty features on the site.

## Model 2: Resume

`Resume` should be built from predictive expectations, but it should not equal predictive power.

It should answer:

`How much has this team actually accomplished against its schedule?`

## Resume components

Resume will combine three components:

1. `Record Strength`
2. `Performance Over Expectation`
3. `Result Quality`

### Component A: Record Strength

This is the backbone.

For each team, compute how hard its record would be for several benchmark teams to achieve against the same schedule.

Benchmarks:

- `Elite`
- `Top25`
- `Top50`

For benchmark `b` on each game `g`:

```text
p_g,b = win_prob(benchmark_b vs opponent_g at site_g)
```

Then calculate the Poisson-binomial probability that the benchmark would match or exceed the team's actual win total:

```text
RS_i,b = -log10(Pr(X_b >= actual_wins_i))
```

Where `X_b` is the total wins from the schedule-specific Bernoulli draws.

Then blend:

```text
RecordStrength_i =
    0.50 * z(RS_i,Elite)
  + 0.30 * z(RS_i,Top25)
  + 0.20 * z(RS_i,Top50)
```

Why this is better than one benchmark:

- elite benchmark captures very top-end accomplishment
- top-25 benchmark captures playoff or major-bowl quality
- top-50 benchmark captures general schedule difficulty

### Component B: Performance Over Expectation

For each completed game:

```text
actual_margin_i,g = capped_non_garbage_margin
expected_margin_i,g = pregame_pred_margin
residual_i,g = clamp(actual_margin_i,g - expected_margin_i,g, -21, 21)
```

Location multiplier:

```text
loc_mult_i,g =
    1.10 for road games
    1.03 for neutral games
    0.95 for home games
```

Opponent multiplier:

```text
opp_mult_i,g = 0.75 + 0.50 * sigmoid(opp_power_i,g / 7)
```

Bad-loss multiplier:

```text
bad_loss_mult_i,g =
    1.50 if team lost and opp_power_i,g < -5
    1.20 if team lost and opp_power_i,g between -5 and 0
    1.00 otherwise
```

Game value:

```text
POEGame_i,g = residual_i,g * loc_mult_i,g * opp_mult_i,g * bad_loss_mult_i,g
```

Aggregate:

```text
POE_i = mean(POEGame_i,g over all completed games)
```

No heavy recency weighting here.
Resume is about the whole season.

### Component C: Result Quality

This is the human-legible layer.

For wins:

```text
WinValue_i,g =
    I(win)
  * loc_mult_i,g
  * [0.70 * sigmoid((opp_power_i,g - 3) / 6)
     + 0.30 * sigmoid((actual_margin_i,g - expected_margin_i,g) / 7)]
```

For losses:

```text
LossCost_i,g =
    I(loss)
  * loc_mult_i,g
  * [0.70 * sigmoid((-opp_power_i,g - 1) / 6)
     + 0.30 * sigmoid((expected_margin_i,g - actual_margin_i,g) / 7)]
```

Then:

```text
ResultQuality_i =
    0.60 * mean(top_4(WinValue_i,g))
  - 0.90 * mean(top_2(LossCost_i,g))
  + 0.30 * mean(all_other_game_values_i,g)
```

If there are fewer than four wins or two losses, average what exists.

### Final Resume score

```text
Resume_i =
    0.50 * z(RecordStrength_i)
  + 0.30 * z(POE_i)
  + 0.20 * z(ResultQuality_i)
```

This is the public default.

It is easy to explain and still flexible enough to tune after backtesting.

## Weekly publishing workflow

Each week after games finish:

1. Ingest SportsDB schedules and final scores.
2. Ingest CFBD advanced box, drives, plays, weather, and betting lines where available.
3. Recompute opponent-adjusted FBS/FCS features.
4. Re-estimate Power states.
5. Recompute pregame expectations for all completed games using the frozen pregame snapshots.
6. Recompute Resume.
7. Publish:
   - current Power
   - current Resume
   - game projections
   - team page rating deltas

## Freeze rule for team pages

To explain rating movement properly:

- store a `pregame` power snapshot
- store a `postgame` power snapshot
- store the `delta`

That delta should be decomposed into:

- opponent quality effect
- result effect
- dominance effect
- garbage-time reduction
- home/road context

This becomes one of the best team-page features on the entire site.

## Validation targets

### Power

Backtest:

- spread MAE
- score RMSE
- total MAE
- win-probability log loss
- Brier score
- calibration by probability bucket
- calibration by level pairing
- calibration by season week

### Resume

Backtest:

- agreement with informed postseason consensus
- stability from week to week
- best-win recognition
- bad-loss recognition
- fairness across schedule strength and levels

### Cross-level engine

Backtest separately on:

- FBS vs FCS
- FCS vs DII
- DII vs DI/FCS
- DII vs DIII when available

If this layer is wrong, the whole site concept gets shaky.

## First build recommendation

Ship in three phases:

### Phase 1

- score-based all-level Power
- public Resume
- priors from previous season plus manual lower-level priors

### Phase 2

- CFBD opponent-adjusted features for FBS/FCS
- advanced predictive layer
- totals and score projections

### Phase 3

- richer offseason prior model
- player-informed transfer adjustments
- uncertainty bands
- cross-level confidence surfacing everywhere

## Bottom line

The model should be:

- predictive enough to forecast games well
- honest enough to separate power from resume
- ambitious enough to rank all levels together
- transparent enough that users can follow why a team moved

That is the combination that can make this site feel different from everything else on the internet.
