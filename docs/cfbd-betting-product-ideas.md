# CFBD Betting Data Ideas

Last reviewed: April 21, 2026

Official references:
- https://collegefootballdata.com/api-tiers
- https://api.collegefootballdata.com/api-docs.json
- https://graphqldocs.collegefootballdata.com/

## What Tier 2 gives us

Per the official CFBD tier page, Tier 2 includes:
- Historical betting lines
- Weather data
- Live scoreboard
- Live play-by-play
- 30,000 REST API calls per month

Tier 2 does **not** include GraphQL subscriptions. Those start at Tier 3+.

## What the REST betting endpoint actually returns

The `/lines` endpoint returns betting games and each game can include multiple provider rows.

Available line-level fields:
- `provider`
- `spread`
- `formattedSpread`
- `spreadOpen`
- `overUnder`
- `overUnderOpen`
- `homeMoneyline`
- `awayMoneyline`

Useful filters we can apply:
- `gameId`
- `year`
- `seasonType`
- `week`
- `team`
- `home`
- `away`
- `conference`
- `provider`

## Core product truth

The best use of CFBD betting data on our site is **not** to turn the site into a picks page.

The best use is to:
- explain how the market saw a game
- compare our model to the market
- measure how teams perform against expectation
- reveal line movement and disagreement
- make team and conference pages more interesting

That gives us something fans actually care about while still feeling premium and analytics-driven.

## Best immediate features

### 1. Market vs. Model on every matchup

For each game page or schedule row:
- Market spread
- Market total
- Our predicted spread
- Our predicted total
- Edge = our number minus market number

Why this matters:
- instantly tells users where our model is most different from consensus
- creates a clear “why the model likes this game” hook
- makes predictive ratings more tangible

### 2. Team ATS profile

On team pages:
- Straight-up record
- Against-the-spread record
- Over/under record
- Average closing spread
- Average result vs spread
- Average total result vs market total

Useful labels:
- `market darlings`
- `market laggers`
- `cover machine`
- `over team`
- `under grinder`

### 3. Schedule-level expectation board

On the team schedule:
- closing spread
- closing total
- cover result
- total result
- rating delta from the game

This would tell a much richer story than just W/L:
- Did they win but fail to impress?
- Did they lose but gain respect?
- Were they consistently undervalued?

### 4. Weekly “market misses” module

Home page or rankings page cards:
- biggest spread upset
- biggest line movement game
- biggest total miss
- team that keeps beating the number

This is fun, familiar, and easy to scan.

### 5. Conference market strength page

Conference pages should include:
- average closing spread vs non-conference opponents
- ATS record in non-conference games
- average cover margin
- how often the conference outperforms market expectation

This is a natural extension of your conference ranking idea and gives us a market-based lens that fans immediately understand.

## Best premium features

### 6. Line movement storytelling

Because CFBD gives us open and current/closing numbers, we can show:
- open spread vs close spread
- open total vs close total
- magnitude of movement
- whether the move was “right”

Great visual treatments:
- mini arrow spark
- “opened -3, closed -6.5”
- “steam toward home favorite”
- “late buyback before kickoff”

Best use cases:
- matchup page
- weekly recap page
- rivalry/game hub

### 7. Closing line value tracker

If we later store our own published predictions at the time they were generated, we can measure:
- whether a user following our model would have beaten the close
- whether our model was ahead of the market early in the week

Important:
- this is best positioned as a model evaluation tool, not gambling advice

### 8. “Fraud check” / “earned it” using market expectation

For each team:
- expected wins from closing lines
- actual wins
- expected margin from closing spreads
- actual margin

This yields a very readable team summary:
- `+1.8 wins above market expectation`
- `won 4 more points per game than the closing spread implied`

That is more intuitive to fans than abstract uncertainty fields.

### 9. Program-history market pages

For program pages:
- best ATS seasons
- worst ATS seasons
- seasons where a team dramatically outperformed expectation
- seasons where the market loved them too much

This fits perfectly with your historical-context push.

### 10. Cross-level market bridge

For cross-division storytelling:
- when FCS or DII teams face FBS opponents, compare actual margin to market expectation
- identify programs that repeatedly outperform market assumptions against higher levels

This is one of the cleanest ways to make your all-level product feel credible.

## Fun features fans would actually use

### 11. Vegas respect meter

For each team:
- how often favored
- biggest number they laid
- biggest number they got
- largest move toward them all season

### 12. Heartbreak / backdoor index

Track:
- covers decided by 3 points or fewer relative to spread
- totals decided by 3 points or fewer relative to the number

This would be extremely shareable.

### 13. Chaos Saturday recap

Weekly page:
- biggest outright upset vs moneyline
- biggest favorite to fail to cover
- biggest over/under surprise

### 14. Market disagreement board

If multiple providers are present:
- provider spread range
- provider total range
- widest disagreement games of the week

This is a subtle but premium feature that feels “Bloomberg terminal” rather than generic sports blog.

### 15. Blind resume vs market respect

For rankings:
- compare current rank to average market expectation over the season
- show teams with elite results but modest market respect
- show teams the market kept believing in despite uneven outcomes

## Best UX surfaces

### Home page

Best betting modules:
- Market vs Model spotlight
- Weekly market misses
- Teams outperforming expectation
- Biggest movers from open to close

### Rankings page

Add optional columns or expandable details:
- ATS
- expected wins
- wins above market
- average cover margin

These should be optional or inside the expandable row, not always in the main table.

### Team page

Best place for betting data:
- season ATS/O-U card
- schedule expectation board
- line movement mini chart
- “won above expectation” summary

### Conference page

Best place for betting data:
- non-conference ATS summary
- average spread edge vs other leagues
- best and worst market-performing programs

## What I would build first

Highest-value sequence:

1. Add ATS / over-under grading to each game.
2. Add team-page betting summary cards.
3. Add `expected wins vs actual wins` and `wins above market`.
4. Add a home-page `market misses` module.
5. Add conference ATS and expectation-outperformance summaries.

That sequence gives users something they instantly understand and makes the site feel much richer without turning it into a gambling product.

## Important editorial stance

We should frame this data as:
- market expectation
- price discovery
- team evaluation
- model benchmarking

We should avoid framing the site as:
- a tout service
- lock-of-the-week content
- pure gambling advice

That positioning is better for trust, better for brand, and more aligned with the premium analytics direction.

## Technical next step

The data is already mostly there for the basics because we store:
- open spread
- close spread
- open total
- close total
- moneylines
- game results

So the immediate implementation path is:
- compute ATS result per game
- compute total result per game
- compute team and conference market-overperformance summaries
- expose them in reporting

This is one of the strongest near-term upgrades available from CFBD Tier 2.
