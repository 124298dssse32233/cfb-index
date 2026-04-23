# College Football Modeling Research

Date: April 20, 2026

This note translates established college-football ranking ideas into practical product and model decisions for this project.

## Core sources reviewed

- CollegeFootballData API v2 announcement
  - https://blog.collegefootballdata.com/api-v2-is-now-in-general-availability/
- BCF Toys FEI explanation
  - https://www.bcftoys.com/2019-fei-w15/
- BCF Toys glossary
  - https://bcftoys.com/glossary
- Massey Ratings description
  - https://masseyratings.com/theory/massey.htm
- Colley Matrix method paper
  - https://www.colleyrankings.com/matrate.pdf
- SP+ high-level description from Bill Connelly at ESPN
  - https://insider.espn.com/college-football/insider/story/_/id/39276178/utils

## What the best systems are actually doing

### 1. The best predictive systems care about efficiency, not just scoreboard margins

SP+ is described by Bill Connelly as a tempo-adjusted and opponent-adjusted measure of efficiency.

FEI is explicitly possession-based. Fremeau defines FEI as opponent-adjusted possession efficiency, representing the per-possession scoring advantage a team would expect to have on a neutral field against an average opponent. The glossary also makes an important college-football-specific point: FEI-style metrics focus on non-garbage possessions.

Implication for this project:

- The long-term predictive model should move toward per-drive and eventually per-play efficiency.
- Score-only modeling is acceptable as a fallback, but it should be treated as a lower-resolution approximation.
- When drives and advanced game stats are missing, the model should degrade gracefully instead of pretending equal certainty.

### 2. The best public systems separate predictive strength from résumé strength

Massey explicitly distinguishes between "rating" and "power." Power is the better measure of future potential, while rating is more merit-based and can use a Bayesian win-loss correction. Colley goes even farther in the deservedness direction by ignoring margin entirely and relying on wins, losses, and schedule structure.

Implication for this project:

- Keep two separate rankings.
- Power should remain forward-looking and margin/efficiency based.
- Resume should explicitly reward the body of work, including strong wins and consistent winning.
- Do not collapse the two into one number on the product surface.

### 3. College football requires strong schedule and graph logic because the network is sparse

Colley emphasizes the core problem directly: lots of teams, few games, and incomplete overlap. Massey also notes that ratings become interdependent through chains of opponents and opponents' opponents.

This project has an even harder problem because it combines FBS, FCS, DII, and DIII into one graph.

Implication for this project:

- Cross-level comparisons should depend on actual connectivity, not fixed ceilings.
- Teams in isolated subgraphs should remain more heavily shrunk toward priors.
- Cross-level confidence should be a first-class product concept, not a hidden backend detail.

### 4. Time weighting matters

Massey applies exponential time weighting to make recent games count more heavily. That maps well to actual fan intuition in college football, especially as injuries, lineup changes, and development reshape teams during the season.

Implication for this project:

- Keep weekly exponential decay in the predictive model.
- Consider separate decay curves by use case:
  - faster decay for predictive power
  - slower decay for resume

### 5. Diminishing returns on blowouts is important

Massey explicitly describes a diminishing-returns game outcome function. This is one of the oldest and best anti-run-up mechanisms in football ratings.

Implication for this project:

- Keep margin caps or another diminishing-returns transform.
- Big wins should matter, but 63-7 should not be treated as linearly more informative than 38-10.

### 6. Preseason priors should exist, but they should fade

Massey discusses preseason ratings and prior distributions whose influence diminishes over time. Connelly's SP+ preseason discussions also reinforce that priors matter a lot in August and much less by late October and November.

Implication for this project:

- Preseason priors should blend:
  - prior season power
  - level baseline
  - returning production
  - roster/talent/recruiting/transfer indicators when available
- Priors should fade materially as games accumulate.
- Lower-connectivity teams should keep more prior influence for longer.

### 7. Garbage time handling is not optional in football

FEI's glossary is a strong reminder here: many of its rate stats are built specifically on non-garbage possessions.

Implication for this project:

- Garbage time should eventually affect:
  - drive weights
  - play weights
  - postgame team-delta explanations
- Until full possession-level ingestion is stable, large-margin second-half inflation should stay partially discounted by margin caps.

## Product implications

### Front page

The homepage should feel like a serious CFB analytics publication, not a dashboard export.

Recommended front-page ingredients:

- ranked rail with movement
- premium summary cards
- expandable featured-team drawers
- power-vs-resume scatter
- strength ladder by subdivision
- visible uncertainty framing for cross-level comparisons

### Team pages

The team page should answer these questions immediately:

- How good is this team right now?
- What has happened week by week?
- Which results drove the rating up or down?
- What profile does this team have relative to peers?
- What does the multi-year story look like?

### Rankings UX

Users need to understand that:

- Power is predictive
- Resume is retrospective
- Cross-level confidence reflects graph evidence

That framing is not a footnote. It is central to trust.

## Concrete next model upgrades

### Predictive model

1. Make cross-level shrinkage dynamic and evidence-sensitive
- already partially implemented
- continue calibrating by level and by connectivity

2. Introduce explicit possession-level power when data exists
- prioritize drives before full play-by-play
- move from score-only approximations toward per-drive scoring margin

3. Separate offense, defense, and special teams more cleanly
- current model stores these fields
- future work should tie them to real drive/play splits where available

4. Make bowl/playoff handling phase-aware
- postseason should still live under the same `season_year`
- some postseason games may deserve lower predictive weight when roster continuity is badly broken

### Resume model

1. Add stronger strength-of-record logic
- FEI's "good team" and "elite team" schedule/record concepts are useful inspiration
- we should benchmark actual records against multiple team-strength baselines

2. Add phase-aware result value
- regular season, conference title, playoff, bowl, and final should not all feel identical in the product layer
- the model should avoid arbitrary ad hoc bonuses, but the presentation can still give phase context

3. Reduce blowout dependence
- resume should care more about who you beat and whether you won than about maximizing margin

## Data strategy implications

CFBD should remain the primary source.

Why:

- official season/game structure
- advanced stats
- drive data
- roster/talent/recruiting/returning production
- API direction is clear in v2

SportsDB remains useful mainly for presentation enrichment:

- identity metadata
- venue metadata
- logos and artwork

## Recommended next implementation sequence

1. Improve cross-level calibration further using observed connectivity bands
2. Add visible confidence badges and notes on ranking/team pages
3. Start consuming more possession-level signal from drives where available
4. Add richer front-page featured-team cards with true movement and profile comps
5. Add team-page sections for best wins, worst losses, and season phase splits
