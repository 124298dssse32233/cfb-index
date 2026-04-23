# College Football Power Rankings / Stats Site Research

Research date: 2026-04-20

## Goal

Build the most interesting and best-looking college football power rankings and stats site on the internet, with a signature feature: a single power ranking that spans all levels of college football, so a D3 team can rank above an FCS team, and an FCS team can rank above an FBS team.

## Executive take

The current market is fragmented:

- `ESPN`, `FOX Sports`, `On3`, and `NCAA.com` win on reach, credibility, and basic utility.
- `Sports-Reference`, `Massey Ratings`, and `TeamRankings` win on depth and density.
- `StatMuse`, `Sofascore`, and `Opta Analyst` win on product feel, discoverability, or storytelling.

No current college football product cleanly combines:

- premium visual design
- deep stats exploration
- great mobile usability
- cross-division power rankings
- story-first editorial packaging
- model transparency

That is the opening.

## Important constraint

Some sources expose full rendered page structure; others mostly expose text, metadata, and navigation. Visual/style notes below are partly direct observation from current pages and partly inference from current IA, branding, and known product patterns. Treat the visual judgments as high-confidence directional guidance, not pixel-perfect audits.

## Best current reference sites

### 1. ESPN College Football FPI

Link: https://www.espn.com/college-football/fpi

What it does best:

- Feels authoritative and mainstream.
- Makes predictive rankings feel "official."
- Gives users immediate utility with tabs for `FPI`, `Resume`, and `Efficiencies`.
- Connects rankings to simulations, projections, playoff odds, and season outcomes.

What the source confirms:

- ESPN describes FPI as "the best predictor of a team's performance going forward."
- Projected results are based on `20,000 simulations`.
- The page supports season and conference filters and exposes team-level ranking tables.

Source notes:

- ESPN FPI page: https://www.espn.com/college-football/fpi
- ESPN says: "The Football Power Index (FPI) is a measure of team strength..." and projections are based on `20,000 simulations`. That text was present on the page as of `January 20, 2026`.

What it looks like in product terms:

- Clean broadcast-network utility.
- Dense but legible tables.
- Strong information scent because users already understand the ESPN shell.
- More functional than beautiful.

What to borrow:

- Multiple ranking lenses on the same entity set.
- Daily-updating predictive framing.
- Immediate table access with filters.
- Projections tied to rankings.

What not to copy:

- The generic network-shell feel.
- Heavy dependence on plain sortable tables as the main experience.
- A design language that feels interchangeable with every other major sports page.

### 2. On3 College Football Rankings

Link: https://www.on3.com/college/rankings/football/

What it does best:

- Connects rankings to the modern college football ecosystem: NIL, recruiting, transfer portal, teams, and player value.
- Gives the ranking table a more "sports-media product" feel than a pure data page.
- Surfaces several model dimensions in one table: `Pwr`, `Off`, `Def`, `HFA`, `SoS`, `Score`.

What the source confirms:

- The page includes conference filters and a multi-column ranking table.
- The broader site is tightly integrated with player rankings, NIL valuation, recruiting, and transfer portal surfaces.

What it looks like in product terms:

- Modern media/database hybrid.
- More current and commercially polished than older stat sites.
- Closer to a subscription sports product than a pure analytics lab.

What to borrow:

- Ecosystem thinking around teams, players, recruiting, NIL, and transfers.
- Multi-factor tables that make the ranking feel earned.
- Conference-based exploration.

What not to copy:

- Over-expanding scope too early into every adjacent college football business line.
- Letting the rankings page become just another table in a content farm.

### 3. Sports-Reference College Football

Link: https://www.sports-reference.com/cfb/

What it does best:

- The cleanest database mentality in sports.
- Extraordinary trust from serious users.
- Deep player, team, season, and historical coverage.
- Makes users feel like the data probably exists somewhere on the site.

What the source confirms:

- The site positions itself as "The complete source for current and historical college football players, schools, scores and leaders."
- Team pages include stats, rosters, schedules, game logs, splits, and advanced stats.
- It emphasizes history and breadth of coverage.

What it looks like in product terms:

- Spreadsheet-brain elegance.
- Minimal visual drama.
- Extremely strong utility and credibility.
- Loved by heavy users, not aspirational as a design object.

What to borrow:

- Information completeness.
- Historical depth.
- Reliable team and player pages.
- The feeling that every number can be traced and contextualized.

What not to copy:

- The plain, old-web look.
- Low emotional energy.
- Weak editorial framing and weak visual hierarchy for casual fans.

### 4. Massey Ratings

Links:

- Rankings hub: https://masseyratings.com/ranks?s=cf&t=1404
- Methodology: https://masseyratings.com/theory/massey.htm
- Ranking comparison background: https://masseyratings.com/cf/aboutcomp.htm

What it does best:

- Handles the "how do we compare teams across uneven schedules?" question seriously.
- Preserves a strong computer-rankings identity.
- Highlights the meta-landscape of many ranking systems.
- Feels built by someone who cares about the math more than the gloss.

What the source confirms:

- Massey publishes `rating`, `power`, `offense`, `defense`, `home advantage`, and schedule-strength concepts.
- The methodology uses only score, venue, and date for the core ratings model.
- The ranking comparison has historically aggregated many different ranking systems into a comparison surface.

Why it matters for your idea:

- This is one of the closest spiritual precedents for cross-context team comparison.
- It normalizes the idea that one ranking surface can reconcile mismatched schedules and leagues.

What it looks like in product terms:

- Extremely old-school.
- Dense, utilitarian, and math-first.
- Powerful for experts, intimidating for almost everyone else.

What to borrow:

- Clear distinction between "rating" and "power."
- Cross-system comparison thinking.
- Methodology transparency.

What not to copy:

- The visual design.
- The initial intimidation factor.
- JS/loading friction and dated interaction model.

### 5. TeamRankings

Representative current pages:

- https://www.teamrankings.com/college-football/matchup/washington-maryland-week-6-2025/power-ratings
- https://www.teamrankings.com/college-football/matchup/michigan-maryland-week-13-2025/power-ratings

What it does best:

- Converts predictive/rating concepts into betting-adjacent matchup tooling.
- Gives users many contextual slices quickly: predictive, recent form, home, away, conference, first half, second half, schedule strength, luck, consistency.
- Excellent "comparison utility" even if the site is not visually strong.

What the source confirms:

- Matchup pages expose layered power ratings, schedule strength, luck, and consistency in a compact format.
- The site treats each game as a structured analytics object, not just a scoreboard item.

What it looks like in product terms:

- Practical and dense.
- Built for grinders.
- Closer to a tool than a brand experience.

What to borrow:

- Head-to-head comparison modules.
- "Different contexts, different ratings" framing.
- The idea that a single team should have multiple useful analytical states.

What not to copy:

- Clutter.
- Generic utility-page aesthetics.
- Betting-site adjacency if you want a broader fan brand.

### 6. NCAA.com stats and scoreboard

Links:

- Stats: https://www.ncaa.com/stats/football/fbs
- Scoreboard: https://www.ncaa.com/scoreboard/football/fbs

What it does best:

- Official credibility.
- Clear separation by subdivision: `FBS`, `FCS`, `DII`, `DIII`.
- Useful scoreboard, standings, stats, video, history, and bracket context.

What the source confirms:

- NCAA scoreboard navigation explicitly links scores, CFP bracket, schedule, rankings, standings, stats, video, and history.
- The stats pages surface official leaders and team rankings across many categories.

Why it matters for your idea:

- The NCAA surface reinforces division boundaries.
- Your product opportunity is to preserve those identities while still building a unified "all levels" comparison layer above them.

What it looks like in product terms:

- Official, broad, somewhat generic.
- Useful but not emotionally distinctive.

What to borrow:

- Multi-division navigation.
- Official-data feel.
- Easy path from scoreboard to stats to history.

What not to copy:

- Institutional blandness.
- Overly generic layouts.

### 7. FOX Sports college football polls

Link: https://www.foxsports.com/college-football/polls

What it does best:

- Very straightforward poll navigation.
- Clear switching between `playoff selection committee`, `associated press`, and `usa today coaches poll`.
- Strong awareness of fan mental models around polling.

What the source confirms:

- The page supports several ranking modes inside one surface.
- It lives next to scores, schedule, stats, odds, news, and videos.

What it looks like in product terms:

- Broad sports portal.
- Direct, easy, but not differentiated.

What to borrow:

- Poll mode switching.
- Keeping "human polls" adjacent to "computer power" rather than forcing users to choose one worldview.

What not to copy:

- Portal sameness.
- Thin analytical differentiation.

### 8. StatMuse

Link: https://www.statmuse.com/

Representative CFB query surface:

- https://www.statmuse.com/cfb/ask/college-football-top-25-teams-stats

What it does best:

- Natural-language discovery.
- Makes sports data feel conversational and approachable.
- Strong loop of trending queries and examples.

What the source confirms:

- The site has first-class surfaces for `Trending`, `Examples`, and `Data & Glossary`.
- It prominently surfaces trending players, teams, and searches.
- It supports a dedicated `CFB` section.

What it looks like in product terms:

- Search-first, modern, friendly, social.
- More approachable to casual users than a pure stats table.
- High curiosity factor.

What to borrow:

- Query-first entry points like "Who is the best 8-3 team in the country?" or "Show me every D2 team with an offense strong enough to beat the average FCS defense."
- Search suggestions and trending prompts.
- Strong explanatory glossaries.

What not to copy:

- Relying on search alone as the primary IA.
- Treating the site as a stat answer bot instead of a designed destination.

### 9. Sofascore

Links:

- Homepage: https://www.sofascore.com/
- News note on product scale: https://www.sofascore.com/news/sofascore-among-top-sports-apps-in-2026/

What it does best:

- Real-time, multi-sport product fluency.
- Extremely strong event-state navigation: live, finished, upcoming.
- A product mindset that is clearly optimized for fast scanning and habitual use.

What the source confirms:

- Sofascore emphasizes live scores, fixtures, statistics, league tables, highlights, and odds.
- The product organizes around `All`, `Live`, `Finished`, and `Upcoming`.
- Sofascore highlighted itself as among top global sports apps in 2026 based on Sensor Tower reporting.

What it looks like in product terms:

- Fast, app-native, polished, scan-friendly.
- Highly optimized for habitual checking.

What to borrow:

- Event-state navigation.
- Fast mobile-first scan patterns.
- Strong card architecture.

What not to copy:

- A generic multi-sport shell that makes college football feel like just another tile.
- Too much emphasis on "live score app" patterns if your differentiator is rankings and story.

### 10. Opta Analyst

Links:

- About: https://theanalyst.com/about-us
- NFL competition page: https://theanalyst.com/competition/nfl
- Bundesliga competition page: https://theanalyst.com/competition/bundesliga
- Global power rankings explainer: https://theanalyst.com/articles/power-rankings-your-club-ranked
- FBS articles: https://theanalyst.com/competition/fbs/articles

What it does best:

- "Turning stats into stories."
- The best reference for a premium editorial-plus-data sports product.
- Uses stats, predictions, leaderboards, power rankings, and visual modules as part of a narrative brand.

What the source confirms:

- Opta describes itself as a data-focused editorial destination built to make advanced stats compelling and understandable.
- Competition hubs can include tabs for `Overview`, `Articles`, `Standings`, `Rankings`, `Player Ratings`, `Scores & Schedules`, `Stats`, `Power Rankings`, `Table`, and `Fixtures`.
- The global power rankings article explains a hierarchical Elo-style system across leagues and countries.

Why it matters for your idea:

- The closest design/editorial model for your site is not "another rankings table."
- It is a premium data storytelling site where rankings become the anchor for stories, tools, and community argument.

What to borrow:

- Editorial packaging around data.
- Distinct visual modules.
- Competition landing pages with tabs and mixed content types.
- An explainer page that makes a complicated model feel fun.

What not to copy:

- Too much article-led sprawl before the product core is strong.
- Hiding the best data behind vague editorial labels.

### 11. CollegeFootballData.com

Links:

- Main site: https://collegefootballdata.com/
- API tiers: https://collegefootballdata.com/api-tiers
- GraphQL docs: https://graphqldocs.collegefootballdata.com/
- SP+ trends explorer: https://collegefootballdata.com/sp/trends
- Win probability calculator: https://collegefootballdata.com/win-probability
- Visualization article: https://blog.collegefootballdata.com/data-driven-college-football-visualizations/

Why it matters even though you already have another data source:

- It is a strong example of productized CFB analytics.
- It shows that fans will engage with explorer-style tools and model surfaces, not just articles and tables.
- It reinforces that modern CFB users want exports, notebooks, APIs, advanced metrics, and calculators.

What the source confirms:

- The site now positions itself around API access, training packs, data exporter tools, and model workflows.
- Advanced metrics include EPA/PPA and opponent-adjusted metrics.
- It also ships interactive surfaces like a win probability calculator and SP+ team trends explorer.

What to borrow:

- Calculator and explorer modules.
- Direct bridges from model output to deeper team pages and raw data.
- Serious-user tooling without abandoning a clean UI.

What not to copy:

- Building the product primarily for developers.
- Letting "tooling" crowd out brand and fan delight.

## Cross-site patterns worth stealing

### Pattern 1: More than one ranking lens

The strongest ranking products do not stop at a single ordered list.

Common winning pattern:

- predictive rating
- resume/value rating
- offense/defense splits
- schedule strength
- trend / recent form
- simulation or projection outputs

Implication for your site:

The all-levels ranking should be the flagship, but it should sit beside companion lenses:

- `Power`
- `Resume`
- `Ceiling`
- `Recent Form`
- `Offense`
- `Defense`
- `Spoiler Index`

### Pattern 2: Ranking pages must lead somewhere

The best surfaces are not dead-end tables.

Good downstream paths:

- team page
- game preview
- matchup simulator
- trend explorer
- roster/depth snapshot
- schedule difficulty view
- historical comps

Implication:

Every team row on your rankings page should unfold into richer context, not just a static number.

### Pattern 3: Fans want both authority and argument

`ESPN` and `NCAA.com` win authority.
`Massey` and `TeamRankings` win seriousness.
`StatMuse` and `Opta Analyst` win curiosity and shareability.

Implication:

Your brand should feel trustworthy enough to cite and provocative enough to debate.

### Pattern 4: The best products reduce cognitive load without dumbing down

`StatMuse` does this with conversational entry.
`Sofascore` does it with fast event-state scanning.
`Opta Analyst` does it with narrative framing.

Implication:

Advanced analytics should be progressively disclosed:

- headline first
- "why is this team here?" second
- full model inputs last

### Pattern 5: Modern sports products feel alive

Alive means:

- daily movement
- arrows and risers/fallers
- strength-of-schedule shifts
- matchup implications
- watchlist surfaces
- weekly editorial takes

Implication:

Your site should feel like a living power market, not a PDF ranking posted on Sunday night.

## Common weaknesses in the current market

These are the gaps you can exploit:

- `too many plain tables`
- `too little visual drama`
- `division silos remain rigid`
- `advanced analytics often feel academic`
- `many sites are useful but not lovable`
- `great articles often sit far away from great tools`
- `few products make fans understand cross-level comparisons intuitively`

## The big opportunity: a single all-levels ranking

This is the killer differentiator.

Most current public college football products stop at:

- FBS only
- subdivision-specific leaderboards
- official polls
- conference views

Your wedge is:

`One coherent ranking for every college football team in America, with clear confidence and context.`

That is interesting because:

- It breaks the usual walls.
- It creates instant argument.
- It lets small-school fans participate in the same national conversation.
- It creates lots of surprising objects: best D2 team vs average FCS team, top D3 spoilers, "how good is the 40th-best team in Division II really?", etc.

## How to make cross-division rankings believable

This is the product problem, not just the model problem.

The model can be smart and still fail if users cannot understand why a D3 team is above an FCS team.

So the site needs explanation layers:

### 1. Global rating plus confidence

Each team needs:

- global power rating
- global rank
- subdivision rank
- confidence band / uncertainty

Example:

- `Mary Hardin-Baylor`
- `Global Rank: 118`
- `D3 Rank: 1`
- `Estimated strength: between low-tier FCS and high-tier D2`
- `Confidence: medium`

### 2. "Why this team is here"

Each team page should explain:

- top wins
- margin profile
- opponent quality
- efficiency profile
- cross-division anchor games
- how much is direct evidence versus inferred network strength

### 3. Comparison tools

Users need fast ways to compare:

- Team A vs Team B
- division median vs division median
- best D2 offense vs weakest FBS defense
- "could this team hang in FCS?"

### 4. Explicit caveats

Be honest about:

- sparse cross-division game links
- lower confidence at lower levels
- larger uncertainty for isolated schedules

If you are honest, the product becomes more trustworthy, not less.

## Product concept that can actually win

Working concept:

`An editorial-grade college football intelligence site with the most beautiful all-levels power ranking on the web.`

Not just a stat site.
Not just a blog.
Not just a rankings table.

It should feel like:

- `Opta Analyst` for product vision
- `StatMuse` for discoverability
- `Sofascore` for scan speed
- `Sports-Reference` for depth
- `Massey` for model seriousness
- but with a design system that is unmistakably its own

## Recommended information architecture

### 1. Home

Hero modules:

- all-levels top 25
- biggest risers/fallers
- playoff-caliber teams at every level
- "today's most interesting mismatches"
- feature story

Secondary modules:

- offense leaders
- defense leaders
- best resumes
- strongest conferences
- trending teams

### 2. Rankings

Sub-tabs:

- Global Power
- FBS
- FCS
- DII
- DIII
- NAIA if your data/model supports it later

Controls:

- subdivision filter
- conference filter
- week/date selector
- minimum games
- offense/defense toggle
- recent form window

### 3. Team pages

Must include:

- global rank + subdivision rank
- profile radar or stat bars
- offense/defense split
- schedule graph
- game log with opponent strength
- top wins / worst losses
- recent form
- matchup simulator
- historical trend
- "teams like this"

### 4. Matchup pages

For any two teams:

- projected line
- win probability
- offense vs defense matchup table
- common-opponent network if available
- path of evidence across divisions

### 5. Story pages

Examples:

- Why the No. 1 D2 team would rank 78th nationally
- The best 3-loss team in America, regardless of level
- The giant-killer index
- The soft-schedule trap list
- The teams rising fastest in true power

### 6. Glossary / model explainer

This page matters a lot.

It should explain:

- what power means
- what resume means
- why cross-division comparison is possible
- where uncertainty comes from
- how schedule normalization works

## What the site should look like

High-level direction:

- More premium magazine than sportsbook.
- More cinematic than spreadsheet.
- More intelligent than loud.

### Visual direction

- Use bold college-football atmosphere without falling into generic sports TV graphics.
- Build around a strong type system and a real editorial grid.
- Use dense data cards with excellent spacing.
- Make team-color accents intentional, not chaotic.
- Use motion for rank movement, confidence shifts, and matchup transitions.

### Visual patterns to favor

- dark-ink or deep-field backgrounds with warm brass, bone, or signal-orange accents
- oversized ranking numerals
- helmet/logo chips used sparingly
- data cards that feel collectible
- slope charts, quadrant plots, and riser/faller strips
- "story modules" between tables so the page breathes

### Visual patterns to avoid

- generic sportsbook greens and reds everywhere
- endless zebra-striped tables
- too many tiny logos with no hierarchy
- ESPN clone layouts
- default dashboard SaaS vibes
- fake futuristic neon nonsense

## Feature ideas that feel fresh

### The Global Top 134+

The obvious signature list.

But make it richer:

- every row expandable
- confidence bands
- movement sparkline
- offense/defense mini-bars
- "best possible division" badge

### The Division Crossover Lens

Questions this answers:

- Which D2 teams profile like FCS teams?
- Which FCS teams profile like mid-tier FBS teams?
- Which FBS teams are secretly weaker than elite lower-level teams?

This is one of the most interesting surfaces you could build.

### The Strength Ladder

A visual showing overlapping strength distributions for:

- FBS
- FCS
- DII
- DIII

This would instantly communicate where divisions overlap.

### Rank Movement Theater

Weekly or daily:

- risers
- fallers
- volatility leaders
- "paper tigers"
- "better than their record"

### Best Team You Have Never Watched

An editorial/data hybrid surface that spotlights lower-level teams worthy of national attention.

### Resume vs Power map

One of the most useful, shareable charts:

- x-axis: resume
- y-axis: power

Quadrants:

- contenders
- fraud watch
- dangerous underseed
- fun but flawed

### Game Quality and Chaos surfaces

Rank each upcoming matchup by:

- raw power
- upset potential
- pace/points potential
- playoff implications
- weirdness index

## Positioning statement

You should not market this as:

- "yet another college football stats site"

You should market it more like:

- `the national intelligence layer for college football`
- `the site that ranks every team in America on one scale`
- `the most beautiful way to understand who is actually good`

## MVP recommendation

If you want the smartest first version, ship this:

### MVP pages

- Home
- Global Rankings
- Team Page
- Matchup Compare
- Model Explainer

### MVP data outputs

- global power rating
- offense rating
- defense rating
- schedule strength
- recent form
- rank movement
- confidence score

### MVP editorial modules

- biggest risers/fallers
- best teams by division
- crossover candidates
- best upcoming games

## Design principle for the ranking itself

Do not make the main ranking page just a sortable table.

It should behave like a layered editorial object:

- top section: premium hero / narrative
- middle: expandable ranked list
- side modules: risers, crossovers, strongest units
- deeper layer: filters, compare, export

If the page opens with only a table, you are leaving the biggest branding opportunity on the table.

## Strategic conclusion

The market leaders prove there is demand for:

- predictive ratings
- official stat hubs
- natural-language discovery
- matchup compare tools
- editorial data storytelling

But nobody currently owns the combination of:

- best-in-class design
- all-levels comparison
- transparent model
- deep team pages
- truly modern sports-product feel

That is the lane.

If this site is executed well, the cross-division ranking is not a niche feature. It is the thing that makes the whole brand memorable.

## Sources

- ESPN College Football FPI: https://www.espn.com/college-football/fpi
- ESPN College Football Stats: https://www.espn.com/college-football/stats
- FOX Sports College Football Polls: https://www.foxsports.com/college-football/polls
- NCAA FBS scoreboard: https://www.ncaa.com/scoreboard/football/fbs
- NCAA FBS stats: https://www.ncaa.com/stats/football/fbs
- On3 college football rankings: https://www.on3.com/college/rankings/football/
- Sports-Reference college football: https://www.sports-reference.com/cfb/
- Massey Ratings theory: https://masseyratings.com/theory/massey.htm
- Massey ranking comparison background: https://masseyratings.com/cf/aboutcomp.htm
- Massey ratings hub: https://masseyratings.com/ranks
- TeamRankings example matchup page: https://www.teamrankings.com/college-football/matchup/washington-maryland-week-6-2025/power-ratings
- TeamRankings example matchup page: https://www.teamrankings.com/college-football/matchup/michigan-maryland-week-13-2025/power-ratings
- StatMuse homepage: https://www.statmuse.com/
- StatMuse CFB example query: https://www.statmuse.com/cfb/ask/college-football-top-25-teams-stats
- Sofascore homepage: https://www.sofascore.com/
- Sofascore app popularity note: https://www.sofascore.com/news/sofascore-among-top-sports-apps-in-2026/
- Opta Analyst about: https://theanalyst.com/about-us
- Opta Analyst NFL competition page: https://theanalyst.com/competition/nfl
- Opta Analyst Bundesliga competition page: https://theanalyst.com/competition/bundesliga
- Opta Analyst power rankings explainer: https://theanalyst.com/articles/power-rankings-your-club-ranked
- Opta Analyst FBS article hub: https://theanalyst.com/competition/fbs/articles
- CollegeFootballData main site: https://collegefootballdata.com/
- CollegeFootballData API tiers: https://collegefootballdata.com/api-tiers
- CFBD GraphQL docs: https://graphqldocs.collegefootballdata.com/
- CollegeFootballData SP+ trends explorer: https://collegefootballdata.com/sp/trends
- CollegeFootballData win probability calculator: https://collegefootballdata.com/win-probability
- CFBD visualization article: https://blog.collegefootballdata.com/data-driven-college-football-visualizations/
