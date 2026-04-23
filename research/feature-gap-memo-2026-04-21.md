# CFB Atlas Feature Gap Memo

Date: April 21, 2026

## What the best current CFB sites do well

- ESPN FPI keeps the predictive story simple and sticky: a single strength number, offense/defense/special teams components, and season simulations that update daily. Its current FPI page says projected results are based on 20,000 simulations and that the ratings are meant to be the best predictor of future performance. Source: [ESPN FPI](https://www.espn.com/college-football/fpi)
- TeamRankings wins on decision support. Individual matchup pages branch into power ratings, efficiency stats, stat splits, game logs, head-to-head, common opponents, line movement, travel analysis, and injury reports. Source: [TeamRankings matchup example](https://www.teamrankings.com/college-football/matchup/huskies-terrapins-week-6-2025/power-ratings)
- Game on Paper wins on football texture. The site surfaces team leaderboards, player leaderboards, previews, live game cards, and a clear stat glossary, with data sourced from ESPN and CollegeFootballData. Source: [Game on Paper CFB](https://gameonpaper.com/CFB/)
- CFB HUB / Terranalytics wins on breadth and interactivity. Its live feature set includes adjustable power-ranking weights, team comparison, portal tracking, recruiting geography, dynasty views, NFL pipeline views, rivalry pages, and an interactive map. Source: [CFB HUB](https://cfb.terranalytics.com/)
- On3 wins the offseason attention battle by turning roster movement into a product. Its Team Transfer Portal Index explicitly measures a school's portal cycle relative to its own roster, not relative to other schools. Source: [On3 transfer portal team rankings](https://www.on3.com/transfer-portal/team-rankings/football/2024/)
- College Football Reference / Stathead wins on historical depth and queryability. The site is valuable because fans and researchers can move from team pages into finder-style exploration instead of stopping at a static summary. Source: [College Football Reference](https://www.football-reference.com/cfb/)

## What college football fans repeatedly come back for

- Resume arguments. Tools like Ain't Played Nobody exist almost entirely because CFB fans love arguing "who has earned it" instead of only "who is better." Source: [Ain't Played Nobody](https://www.aintplayednobody.com/)
- Territory / imperialism maps. These are sticky because they turn every Saturday into a visible land-grab story with trash-talk value, not just a box score. Source: [Imperialism Map](https://www.imperialismmap.com/)
- Playoff simulators and bracket builders. Fans want to test paths, swap winners, and instantly see how the field changes. Source: [CFB Labs playoff simulator](https://www.cfblabs.com/college-football-playoff-simulator)
- Fan-driven polling and favorites. Projects like Rankrly show that people enjoy creating their own ballots, setting favorite teams, and seeing how consensus changes week to week. Source: [Rankrly discussion](https://www.reddit.com/r/CFB/comments/1nl5gj4/i_built_a_fanpowered_college_football_ranking/)
- Recruiting and portal visualization. Recruiting dashboards and portal indexes get revisited because they give fans something meaningful to track between games and between seasons. Sources: [On3 transfer portal team rankings](https://www.on3.com/transfer-portal/team-rankings/football/2024/), [CFB HUB](https://cfb.terranalytics.com/)

## Where our site is still behind right now

- We now have rankings, team pages, matchup projections, weekly archive pages, conference pages, and a real compare page. That is a strong base.
- We still do not have a true playoff simulator or bracket room, which is one of the biggest engagement drivers in the sport.
- We do not yet have an imperialism or territory layer, which is one of the most naturally viral college-football-native visual products.
- We do not yet have a full roster-strength / portal-impact / recruiting-prior layer on team pages, even though that is essential to preseason power and offseason attention.
- We do not yet have rich live or near-live game pages driven by play-by-play, win probability, drive summaries, and "how the game turned" storytelling.
- We do not yet have a historical query layer that lets fans explore teams, eras, seasons, and opponents the way Sports Reference / Stathead does.
- We do not yet have user-side personalization like favorites, saved compare links, or weekly watchlists.

## What we can support with the data stack we have

- CollegeFootballData Tier 2 is strong enough to support much more than we are currently showing. The official access-tiers page lists recruiting data, advanced metrics, opponent-adjusted metrics, live scoreboard, and live play-by-play in Tier 2. Source: [CollegeFootballData API tiers](https://collegefootballdata.com/api-tiers)
- That means we can build a more serious preseason prior using returning production, recruiting/talent, transfer movement proxies, and opponent-adjusted efficiency rather than relying only on prior-year carryover.
- We should treat SportsDB as a secondary enrichment source rather than the primary football backbone. In our local testing, the SportsDB football leagues list appears heavily weighted toward Division I coverage, so it is useful for logos, badges, and media polish but not sufficient for an all-level competitive model by itself.
- Our cross-level database and modeling work across FBS, FCS, Division II, and Division III remains the true moat. Most popular public sites stop at FBS, or at best DI, while our product can own the "single football universe" concept if we execute it well.

## Recommended build order from here

1. Build a playoff room and bracket simulator for the 2025 season structure, including FBS playoff, FCS bracket, and the lower-division postseason context where available.
2. Build an imperialism / territory experience across all NCAA levels, because it is highly visual, memorable, and differentiated.
3. Add offseason roster-strength pages using recruiting, portal, and returning-production priors so preseason rankings feel best-in-class.
4. Add live or postgame game pages with play-by-play, drive summaries, leverage swings, and win-probability storytelling.
5. Expand compare into compare v2 with shareable URLs, historical compare mode, common-opponent score context, and phase filters.
6. Add a historical explorer layer so users can query eras, opponents, program arcs, and multi-year team profiles instead of only reading static pages.
7. Add favorites, saved teams, and watchlists so repeat visitors have a reason to come back between Saturdays.

## Product takeaway

- The best CFB products do not just publish rankings. They give fans a way to argue, simulate, compare, relive, and recruit.
- Our site is already moving in the right direction on rankings, team pages, weekly replay, and compare.
- The highest-upside next frontier is turning the site into an ecosystem of arguments and worlds: playoff room, compare room, map room, and roster room.
