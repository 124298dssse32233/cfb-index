# College Football Power Model Research

Research date: 2026-04-20

## Goal

Design two different rating systems for the site:

1. `Predictive model`
   The forward-looking model that answers: "What would the spread / score / win probability be in the next game?"

2. `Resume / quality model`
   The backward-looking model that answers: "How impressive has this team actually been based on what happened?"

The key lesson from the best public systems is that these should not be the same model.

## Executive conclusion

If you want to be best-in-class, you should not build one blended ranking and call it a day.

The strongest public systems separate:

- `power` from `resume`
- `sustainable performance` from `actual accomplishment`
- `expected future strength` from `what a team has earned so far`

That is not a cosmetic distinction. It is the heart of why the best models stay useful.

### The best public precedents

- `ESPN FPI` is explicitly predictive and forward-looking.
- `ESPN Strength of Record` and `Game Control` are explicitly résumé / accomplishment tools.
- `SP+` is explicitly predictive and not résumé-based.
- `Massey` explicitly separates `Power` from `Rating`.
- `Sagarin` explicitly has a `PREDICTOR` column and a different overall `RATING`.
- `FEI` provides opponent-adjusted team strength plus separate strength-of-record measures.
- `F+` shows the value of ensembling top predictive systems rather than trusting only one.
- `CFP` selection tools now explicitly emphasize both schedule strength and a separate `record strength` concept.

That is the blueprint.

## The best systems and what they teach us

### 1. ESPN FPI

Source:

- https://www.espn.com/college-football/fpi

What ESPN says:

- FPI is "meant to be the best predictor of a team's performance going forward for the rest of the season."
- FPI represents how many points above or below average a team is.
- Projections are based on `20,000 simulations` using FPI, results to date, and remaining schedule.

Implications:

- Predictive power should live on a point-spread scale.
- The core rating should be translatable into game forecasts.
- A power model should feed a simulation layer, not just a ranking table.

### 2. ESPN Strength of Record and résumé metrics

Sources:

- https://www.espn.com/blog/statsinfo/post/_/id/96761/determining-the-most-deserving-teams
- https://www.espn.com/college-football/story/_/page/weeklyscenario110521/how-strength-record-determine-college-football-playoff-field

What ESPN says:

- FPI is forward-looking and measures who is "most powerful."
- Résumé metrics are backward-looking and measure who is "most deserving."
- `Strength of Record` measures the chance an average Top-25 team would have that team's record or better against that schedule.
- `Game Control` evaluates how a team went about winning or losing using in-game win probability rather than just final score.

Implications:

- Your second model should not just be "predictive power but with more weight on wins."
- The correct resume framing is schedule-relative accomplishment.
- The strongest retrospective model combines actual results with quality-of-performance context.

### 3. SP+

Sources:

- https://www.espn.com/college-football/insider/story/_/id/35375426/college-football-sp%2B-rankings-bowl-games
- https://www.espn.com/college-football/insider/story/_/id/30847607/college-football-preseason-sp%2B-projections
- https://www.espn.com/college-football/insider/story/_/id/32000492/college-football-2021-updated-preseason-sp%2B-rankings

What Connelly says:

- SP+ is "a tempo- and opponent-adjusted measure of college football efficiency."
- It is intended to be "predictive and forward facing."
- It is "not a résumé ranking."
- Preseason SP+ projections are built from:
  - returning production
  - recent recruiting
  - recent history

Important details:

- Last year's SP+ plus returning production make up more than two-thirds of the preseason formula.
- Recruiting makes up about one-quarter.
- Previous multi-year history is a smaller stabilizing input.

Implications:

- Best-in-class predictive models use priors.
- Those priors are not arbitrary; they are roster continuity, talent base, and program health.
- Tempo-adjustment matters because raw per-game stats lie.

### 4. FEI

Sources:

- https://bcftoys.com/glossary
- https://www.bcftoys.com/2019-fei-w15/
- https://withasideofpod.nd.edu/episodes/2-17-on-football-rankings-and-measuring-efficiency-brian-fremeau-fei/

What Fremeau says:

- FEI is based on `opponent-adjusted possession efficiency`.
- FEI represents the `per non-garbage possession` scoring advantage a team would be expected to have on a neutral field against an average opponent.
- FEI offense, defense, and special teams are rated separately.
- Strength-of-record variants exist for average, good, and elite team baselines:
  - `AWD`
  - `GWD`
  - `EWD`

Important details:

- FEI focuses on `non-garbage` possessions.
- It is built on drives / possessions, not just final scores.
- It also explicitly separates `team strength` from `strength of record`.

Implications:

- Garbage time filtering is a serious best practice.
- Possession-level modeling is stronger than raw final score modeling.
- Special teams should not be ignored if you want a truly sharp predictive model.

### 5. F+

Sources:

- https://bcftoys.com/2025-fplus
- https://www.bcftoys.com/

What it teaches:

- `F+` combines FEI and SP+.
- Overall team, offense, defense, and special teams ratings are standardized and combined.

Implication:

- Ensembling top predictive approaches often beats ideological purity.
- A best-in-class public-facing model can combine multiple strong components into one projection layer.

### 6. Massey Ratings

Source:

- https://masseyratings.com/theory/massey.htm

What Massey says:

- `Rating` = overall assessment of performance to date.
- `Power` = estimated team strength going forward.
- Inputs are only score, venue, and date.
- The model uses a `Game Outcome Function` with diminishing returns on margin.
- Bayesian correction is then used to reward teams that win consistently.

Implications:

- If you are limited to score/venue/date, you can still build something smart.
- Diminishing returns on blowouts are important.
- Separating `power` from `rating` is foundational, not optional.

### 7. Sagarin

Source:

- https://www.sagarin.com/sports/cfsend.htm

What Sagarin says:

- `PREDICTOR` is such that score is the only thing that matters and is "a very good predictor of future games."
- `GOLDEN_MEAN` uses actual scores in a different way and is also score-based.
- `RECENT` weights recent play more heavily.
- Overall `RATING` is a synthesis of these score-based methods.

Implications:

- Good modeling systems often carry multiple views of team strength at once.
- Recency is useful, but should be an explicit layer rather than an invisible distortion.
- A synthesis / ensemble can outperform any one score-based lens.

### 8. TeamRankings

Sources:

- https://www.teamrankings.com/college-football/team/maryland-terrapins/rankings
- https://www.teamrankings.com/college-football/matchup/wolverines-terrapins-week-13-2025/over-under-analysis
- https://www.teamrankings.com/blog/press/teamrankings-on-espn-sportscenter-announcing-the-predictor

What TeamRankings says:

- Their current `Predictive Rating` is designed solely for predictive purposes.
- Using preseason priors improves predictive accuracy, though the prior impact decreases over time.
- Their prediction surfaces expose multiple models side by side:
  - Official TR Pick
  - Similar Games
  - Decision Tree

Implications:

- Best-in-class forecasting products often use more than one predictive engine.
- Even if one model is primary, auxiliary models are useful for consensus, uncertainty, and diagnostics.
- Priors should decay over time.

### 9. Opta global power rankings

Source:

- https://theanalyst.com/articles/power-rankings-your-club-ranked

What Opta says:

- Their system is a `hierarchical Elo-based rating system`.
- It uses more than `2,500,000 games since 1990`.
- It is explicitly built to compare teams across leagues that rarely or never play one another.
- Elo ratings are then transformed onto a 0-100 power ranking scale.

Implications for your all-levels college football idea:

- Cross-ecosystem ranking is realistic if you treat the sport as a connected graph.
- Hierarchical Elo is one of the cleanest ways to bridge separate sub-leagues and tiers.
- A public-facing rank scale can sit on top of a more technical latent rating.

### 10. CFP's new record-strength direction

Sources:

- https://www.espn.com/college-football/story/_/id/46027603/cfp-selection-committee-use-enhanced-metrics
- https://www.espn.com/college-football/story/_/page/weeklyscenario110521/how-strength-record-determine-college-football-playoff-field

What changed:

- The CFP’s schedule-strength tool now applies greater weight to games against strong opponents.
- A new `record strength` metric was added to assess how teams performed against that schedule.
- The intent is to reward wins over high-quality opponents, minimize the penalty for losing to strong teams, give minimal reward for beating weak teams, and impose a greater penalty for losing to weak teams.

Implications:

- This is exactly the logic your resume/quality model should capture.
- The current direction of elite decision-making in the sport is moving toward schedule-aware accomplishment, not raw record.

## What the best-in-class systems agree on

Across these sources, there is overwhelming agreement on a few principles:

### Predictive model principles

- Use opponent adjustment.
- Use tempo or possession normalization.
- Use preseason priors that decay.
- Separate offense and defense, and preferably special teams too.
- Model home field.
- Downweight garbage time / diminishing returns on blowouts.
- Output ratings in point-spread terms.
- Simulate seasons from the power ratings.

### Resume / quality model principles

- Reward actual wins over good teams.
- Reduce reward for beating bad teams.
- Minimize punishment for losses to strong teams.
- Punish bad losses heavily.
- Compare accomplishment relative to schedule, not in raw record space.
- Consider not only record but some "control" / dominance context where available.

## Recommended architecture for your site

You asked for two models. The best answer is:

### Model A: Predictive Power

Purpose:

- forecast point spread
- forecast total
- forecast win probability
- simulate season outcomes
- rank teams by expected future strength

Public label ideas:

- `Power`
- `Projection`
- `Predictive Rating`

### Model B: Resume / Quality

Purpose:

- rank teams based on what they have accomplished
- evaluate schedule-relative quality of wins and losses
- support "most deserving" conversations
- explain why a 9-3 team can have a stronger or weaker résumé than an 11-1 team

Public label ideas:

- `Resume`
- `Record Strength`
- `Quality`
- `Accomplishment`

## How I would build the predictive model

### Best-in-class version

If you want the closest thing to FPI / SP+ / FEI quality, the predictive stack should look like this:

#### Layer 1: Preseason prior

Inputs:

- previous season final power
- multi-year program strength
- returning production
- portal-adjusted roster continuity
- recruiting / talent base
- coaching changes

Why:

- This is standard among the strongest predictive systems.
- It makes early-season estimates much better.

#### Layer 2: In-season latent team strength

Ideal structure:

- offense power
- defense power
- special teams power
- home field adjustment
- recency modifier

Ideal unit:

- per possession or per drive

Why:

- This is where FEI and SP+ are strongest.

#### Layer 3: Result assimilation

Update each game using:

- opponent strength
- location
- score margin
- diminishing returns cap
- garbage-time adjustment
- recency weighting

Why:

- Massey and Sagarin both highlight the need for diminishing returns.
- Fremeau highlights non-garbage possessions.

#### Layer 4: Matchup translator

Take Team A and Team B ratings and produce:

- expected spread
- expected total
- win probability

Potential mechanics:

- additive offense vs defense means
- pace / possessions estimate
- scoring distribution simulation
- Monte Carlo score distribution

#### Layer 5: Ensemble sanity layer

Blend:

- core power model
- similar-games analog model
- tree/GBM matchup model

Why:

- TeamRankings shows value in multiple predictive lenses.
- F+ shows value in combining strong systems.

## How I would build the resume / quality model

This should not just reuse the predictive rating.

### Best-in-class version

#### Component 1: Record strength

Core question:

- How hard would it be for an average / good / elite team to match this record against this schedule?

This is directly aligned with:

- ESPN SOR
- FEI AWD / GWD / EWD
- CFP record strength

#### Component 2: Win quality / loss quality

Each result gets value based on:

- opponent quality at game time
- location
- margin / control
- whether the result exceeded or missed expectation

Rules of thumb:

- Beating a great team matters a lot.
- Losing to a great team hurts less.
- Beating a weak team matters very little.
- Losing to a weak team hurts a lot.

#### Component 3: Game control / dominance

If you have play-by-play:

- use in-game win probability
- use drive efficiency
- use non-garbage possessions

If you do not:

- approximate with capped margin versus expectation
- scoreline shape
- opponent-adjusted dominance

#### Component 4: Schedule strength

The schedule term should not be a bonus tacked on at the end.
It should be built into the record-strength and result-value calculations themselves.

#### Component 5: Zero reward for boring obvious wins

This is a huge best practice and often missing from amateur models.

- If Team X is expected to beat a bad team by 24 and wins by 27, that should barely move the resume needle.
- If Team X loses that game, it should move a lot.

## The actual model recommendation

If I were designing this for your site, I would use:

### Predictive model

`Hierarchical possession-adjusted power model with priors and score simulation`

Concrete structure:

- latent offense rating
- latent defense rating
- optional special teams rating
- home field
- cross-division translation layer
- preseason prior
- recency decay
- diminishing margin cap
- spread / total simulator

### Resume / quality model

`Schedule-relative accomplishment model with record strength plus game quality`

Concrete structure:

- strength-of-record backbone
- opponent-quality win values
- opponent-quality loss penalties
- capped margin-over-expectation
- game-control bonus if detailed data exists
- bad-loss penalties amplified
- weak-win rewards compressed

## Best-in-class cross-division strategy

This is where your site can be special.

The strongest path is:

### Under-the-hood rating scale

Keep a latent internal strength scale that is not division-bound.

Possible options:

- Elo-like
- points-above-average
- possession-efficiency above average

### Cross-division bridge

Use all available inter-division and inter-subdivision games as anchor edges.

Then:

- propagate strength through the full game graph
- estimate uncertainty bands where connection density is weak

This is closer in spirit to:

- Opta global power rankings
- Massey network equilibrium

than to AP-poll-style ranking.

### Public-facing scale

Expose:

- Global Power rank
- Division rank
- confidence / uncertainty

That keeps the cross-level list fun without pretending the certainty is identical everywhere.

## What SportsDB can and cannot support

This is the hard truth.

### If you only use SportsDB

You can build:

- score-based predictive ratings
- schedule-adjusted power
- home-field adjustments
- Elo / Massey / Sagarin-style systems
- résumé / record-strength style models using results and opponent strength

You cannot build a truly top-tier FEI / SP+ style model because you will not have dependable:

- play-by-play data
- drive-level data
- robust team unit stats
- non-garbage possession segmentation
- detailed roster quality inputs

### So what is the practical consequence?

With `SportsDB only`, your ceiling is:

- very good `score-result-power` modeling
- not true `best-public-analytics-grade` predictive modeling

With an added source like `CollegeFootballData` or equivalent play-by-play / advanced data:

- you can build something much closer to FEI/SP+/FPI quality

## My honest recommendation

### Short version

If "absolute best-in-class" is the standard, add a second data source for advanced modeling.

### Minimum viable elite stack

- `SportsDB`
  for team identity, schedules, historical results, artwork, basic event data

- `play-by-play / advanced data source`
  for possessions, efficiency, EPA-like context, garbage-time filtering, unit modeling

### If you refuse to add another source

Then I would build:

#### Predictive

- cross-division hierarchical Elo / Massey hybrid
- score-based with diminishing returns
- preseason priors from multi-year history
- spread / total simulation layer

#### Resume

- SOR-style record strength
- opponent-quality result scoring
- small dominance term from capped margin over expectation

That would still be strong and differentiated, just not as rich as the best public analytic systems.

## Final product recommendation

Ship these as clearly distinct surfaces:

### `Power`

- "How strong is this team right now?"
- "What would they be favored by against Team B?"
- "What is their projected win probability next week?"

### `Resume`

- "How impressive has this season actually been?"
- "How hard was this record to achieve?"
- "How much did this team truly earn?"

If you blur those into one number, you will lose the smartest thing about the best systems in the market.

## Sources

- ESPN FPI: https://www.espn.com/college-football/fpi
- ESPN SOR / Game Control explainer: https://www.espn.com/blog/statsinfo/post/_/id/96761/determining-the-most-deserving-teams
- ESPN Strength of Record article: https://www.espn.com/college-football/story/_/page/weeklyscenario110521/how-strength-record-determine-college-football-playoff-field
- Bill Connelly SP+ preseason factors: https://www.espn.com/college-football/insider/story/_/id/30847607/college-football-preseason-sp%2B-projections
- Bill Connelly SP+ updated preseason approach: https://www.espn.com/college-football/insider/story/_/id/32000492/college-football-2021-updated-preseason-sp%2B-rankings
- Bill Connelly SP+ description: https://www.espn.com/college-football/insider/story/_/id/35375426/college-football-sp%2B-rankings-bowl-games
- FEI glossary and definitions: https://bcftoys.com/glossary
- FEI ratings definition: https://www.bcftoys.com/2019-fei-w15/
- F+ ratings: https://bcftoys.com/2025-fplus
- Massey theory: https://masseyratings.com/theory/massey.htm
- Sagarin ratings page: https://www.sagarin.com/sports/cfsend.htm
- TeamRankings predictive rating note: https://www.teamrankings.com/college-football/team/maryland-terrapins/rankings
- TeamRankings multiple models example: https://www.teamrankings.com/college-football/matchup/wolverines-terrapins-week-13-2025/over-under-analysis
- TeamRankings Similar Games mention: https://www.teamrankings.com/blog/press/teamrankings-on-espn-sportscenter-announcing-the-predictor
- Opta power rankings methodology: https://theanalyst.com/articles/power-rankings-your-club-ranked
- CFP enhanced metrics / record strength: https://www.espn.com/college-football/story/_/id/46027603/cfp-selection-committee-use-enhanced-metrics
