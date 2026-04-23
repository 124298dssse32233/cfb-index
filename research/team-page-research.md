# College Football Team Page Research

Research date: 2026-04-20

## Goal

Design a team page that is better than current college football team pages, while staying honest about what can actually be powered by your current data source: `TheSportsDB` premium plan (`$9/month`).

The user explicitly wants at least:

- week-by-week schedule
- how the team's rating moved up or down based on each result
- year-by-year results
- amazing data visualization of the above and whatever else makes the page special

This memo focuses on:

- what the best current team pages do
- what features are worth copying
- what is realistic with SportsDB
- what must be computed by us
- what should not be promised unless we add another data source

## Executive take

The best team page for this project should be:

- part profile
- part timeline
- part rating explainer
- part history museum
- part visualization lab

Most current college football team pages are good at one or two of those jobs, not all five.

The strongest version of your team page is:

`a cinematic team dossier anchored by a season timeline and a historical rating story`

That means the page should not open with a generic stats table. It should open with:

- a strong team identity header
- a current strength snapshot
- a week-by-week rating story
- visual proof of why the ranking believes what it believes

## What current team pages do well

### Sports-Reference team pages

Representative source:

- https://www.sports-reference.com/cfb/schools/alabama/index.html

What stands out:

- Exceptional historical framing.
- School history, record totals, championships, bowl history, ranking history, Heisman winners, stadium, and location all appear as core profile data.
- Strong "this is the definitive archive" energy.

What to borrow:

- School-history framing.
- Lifetime record context.
- Awards / championships / national relevance.
- Lots of linked statistical sub-pages from the same team object.

Gap:

- Not visually exciting.
- More archive than product.

### ESPN team pages

Representative sources:

- https://www.espn.com/college-football/team/_/id/333/alabama-crimson-tide
- https://www.espn.com/college-football/team/stats/_/type/team/name/ala
- https://www.espn.com/college-football/team/roster/_/id/333/alabama-crimson-tide

What stands out:

- Good shell for `Home`, `Schedule`, `Statistics`, and `Roster`.
- Efficient team-level summary metrics like points for, points against, and national rank.
- Clear modular tabs for fans who just want the basics quickly.

What to borrow:

- Fast-access top-line cards.
- Obvious tab structure.
- Lightweight schedule/stat/roster navigation.

Gap:

- Still feels like a utility page inside a giant network shell.
- Not much soul.

### On3 team pages

Representative sources:

- https://www.on3.com/college/alabama-crimson-tide/
- https://www.on3.com/teams/alabama-crimson-tide/

What stands out:

- Feels alive because it merges team identity with current context: recruiting, NIL, message boards, schedule, and headlines.
- Strong community/media energy.
- Makes the team page feel like a living hub, not just a record page.

What to borrow:

- "Living team hub" mindset.
- Trending story modules.
- Team-specific news / watchlist / recruiting adjacency if you expand later.

Gap:

- Heavy content/community emphasis can distract from the actual data product.

### Sofascore team pages

Representative source:

- https://www.sofascore.com/american-football/team/alabama-crimson-tide/4312

What stands out:

- `Recent form` is treated as a first-class object.
- The matches tab shows results/fixtures cleanly.
- A `performance and form graph` is a key concept, not a buried extra.
- Team info, venue, roster, and upcoming/previous match context are easy to scan.

What to borrow:

- Recent form strip.
- Performance/form graph concept.
- Last 10 / last 100 match scan patterns.
- Mobile-first information density.

Gap:

- Geared more toward results-following than deep analytical explanation.

### CollegeFootballData trends surfaces

Representative source:

- https://collegefootballdata.com/sp/trends

What stands out:

- Trend lines are used as the team-level jump point.
- The tool explicitly encourages hopping from trend view to team page, metrics explorer, box scores, and data exporter.

What to borrow:

- Trends as a primary layer, not a secondary one.
- Multiple related surfaces attached to the same team.
- Team pages should be launch pads to compare, inspect, and explain.

### Game on Paper

Representative source:

- https://gameonpaper.com/CFB/

What stands out:

- Strong preview/game view framing.
- Honest note that some values may be estimated due to data availability.
- Treats visual analytics as a core product, not decoration.

What to borrow:

- Honesty about data quality.
- Analysis-first game and team storytelling.
- A "glossary + model note" culture around the visuals.

## What SportsDB can realistically power well

Primary official docs:

- Pricing: https://www.thesportsdb.com/pricing
- Documentation: https://www.thesportsdb.com/documentation
- Data guide: https://www.thesportsdb.com/docs_api_data
- Artwork guide: https://www.thesportsdb.com/docs_artwork

### Confirmed strengths

SportsDB premium at `$9/month` includes:

- `Full Premium JSON sports data`
- `100 requests per minute`
- `V2 API`
- `YouTube sports highlight links`
- `2 min livescore` for selected pro leagues, including NFL but not specifically college football in the pricing bullets

The docs confirm API support for:

- `lookup/team`
- `lookup/event`
- `lookup/event_results`
- `lookup/event_stats`
- `lookup/event_timeline`
- `lookup/event_lineup`
- `list/teams`
- `list/seasons`
- `list/players`
- `schedule/full/team`
- `schedule/league/{leagueId}/{season}`

The docs also confirm team artwork fields such as:

- `strBadge`
- `strLogo`
- `strFanart1-4`
- `strBanner`
- `strEquipment`

And core team/event fields such as:

- team identity, venue, stadium capacity, location, colors, social links, descriptions
- event season, round, date, time, opponent, venue, scores, status, country, city

## Important SportsDB constraints

These are the biggest product constraints for your site.

### Constraint 1: NCAA football coverage is explicitly marked incomplete

TheSportsDB’s own American football league directory labels `NCAA Division 1` as `League Incomplete`, and the page key explains this means the league needs artwork or details for teams and players.

Source:

- https://www.thesportsdb.com/Sport/American-Football

### Constraint 2: college football team metadata can be stale or sparse

Example:

- The Alabama team page still says the team is currently coached by `Nick Saban`, even though the same page header shows `Kalen DeBoer`.

Source:

- https://www.thesportsdb.com/team/136168-alabama

Implication:

- Team descriptions should not be trusted blindly as current factual text.
- For user-facing bios, we should either sanitize/cross-check, or keep them secondary.

### Constraint 3: many NCAA football event pages have missing timelines and lineups

Examples on current event pages show:

- `No timeline found..`
- `No lineup players found (Login to add)`

Source:

- https://www.thesportsdb.com/event/2400645-indiana-vs-alabama
- https://www.thesportsdb.com/event/2392368-oklahoma-vs-alabama

Implication:

- Do not make play-by-play or lineup-driven components mandatory for the team page.
- Treat event timeline/stat endpoints as opportunistic enhancements, not guaranteed inputs.

### Constraint 4: standings / tables are not a strong college football primitive here

The official docs describe `Lookup League Table` as limited to `featured soccer leagues only`.

Source:

- https://www.thesportsdb.com/documentation

Implication:

- For college football standings, conference records, division standings, and playoff placement logic, assume we need to derive or maintain our own layer rather than rely on SportsDB tables.

### Constraint 5: player/roster completeness is uneven

Current NCAA football team pages often show very small player counts or no players at all.

Examples:

- Alabama page shows `Showing 0 to 3 (Total: 3)`
- Indiana State shows `Showing 0 to 0 (Total: 0)`

Sources:

- https://www.thesportsdb.com/team/136168-alabama
- https://www.thesportsdb.com/team/137030-Indiana-State

Implication:

- Roster modules should be optional or soft-launched.
- Do not center the initial team page around complete roster/player stat experiences unless you verify team-by-team coverage.

### Constraint 6: historical season coverage exists, but looks uneven

The NCAA Division 1 league page currently lists many seasons, but the page also carries the `League Incomplete` label.

Source:

- https://www.thesportsdb.com/league/4479-ncaa-division-1

Implication:

- `Year-by-year results` is realistic.
- `Full historical advanced team stat archives` are not safe to promise from SportsDB alone.

## What this means for your required features

### 1. Week-by-week schedule and how the rating changed

This is very realistic.

How to power it:

- Pull the full team season schedule from SportsDB.
- Store every game with opponent, date, home/away/neutral inference, result, score, round, season.
- Compute your own rating snapshots after every completed game or every week.

Important:

- SportsDB does not give you "rating before game" or "rating delta."
- That must be derived and persisted by your own model.

Verdict:

- `Yes, strong MVP feature`
- `Derived by us, not directly from API`

### 2. Year-by-year results

This is also realistic, with some caution.

How to power it:

- Use league seasons plus full season schedules.
- Aggregate each season into W-L record, postseason outcome, best win, worst loss, average opponent rating, final power rating, division rank, national rank.

Caution:

- Some historical coverage may be missing or uneven.
- The site must gracefully handle incomplete seasons rather than pretending everything is perfect.

Verdict:

- `Yes, strong core feature`
- `Dependent on historical schedule coverage`

### 3. Amazing data visualization

This is where your site can win hardest.

Because SportsDB may be incomplete for player-level and event-stat detail, the page should focus on:

- schedule-driven visuals
- result-driven visuals
- rating-driven visuals
- history-driven visuals

Those are exactly the things you can control.

## Recommended team page architecture

### Section 1: Hero

Must show:

- team name, badge, wordmark / logo lockup
- current global rank
- current division rank
- current power rating
- offense / defense split
- record
- conference / subdivision
- stadium / city
- current trend arrow

Nice touches:

- team-color gradient background using extracted palette
- fanart/banner from SportsDB when available
- helmet or badge medallion treatment

### Section 2: Season Rating Story

This should be the star.

Core module:

- `Rating Over Time` line chart by game/week

Each point:

- opponent
- score
- win/loss
- rating before
- rating after
- delta

Enhancements:

- color code by result
- thicker line for current season
- hover card with "why the model moved"

This is the single cleanest answer to the user's request.

### Section 3: Schedule Timeline

A visually rich schedule list, not a boring table.

Each row should show:

- week / date
- opponent
- location
- score
- opponent current rank or rating
- pregame win probability
- rating delta
- result classification

Suggested tags:

- `Expected Win`
- `Bad Loss`
- `Quality Win`
- `Statement Win`
- `Coin Flip`
- `Upset`

This row design can become one of the signature motifs of the whole site.

### Section 4: Season Shape

Recommended visuals:

- `Result beads` or `form strip` across the schedule
- `Cumulative wins above expectation`
- `Offense and defense rating split over time`
- `Strength of schedule by week`

These visuals tell the season as an arc, not just a list.

### Section 5: Historical Arc

If year-by-year data is available, this should be huge.

Recommended visuals:

- `Year-by-Year Power Rating` line chart
- `Year-by-Year Record` bars
- `Final national rank by season`
- `Best season / worst season / longest rise / biggest crash`

This is where your page becomes re-visit worthy beyond current season fandom.

### Section 6: Resume and Opponent Quality

Great surface for your rankings brand.

Recommended visuals:

- `Wins and losses plotted by opponent strength`
- `Average opponent rating`
- `Best win ladder`
- `Loss quality meter`

Why it matters:

- It makes the model legible.
- It shows why 8-4 Team A might outrank 10-2 Team B.

### Section 7: Profile Radar or Stat Spine

Because SportsDB team-stat coverage may be uneven for CFB, I recommend prioritizing model-derived team profile metrics over raw API stat fields.

Examples:

- offense power
- defense power
- explosiveness proxy
- consistency
- schedule toughness
- volatility
- close-game luck
- blowout ability

Even if some of those are heuristic rather than play-by-play-based, they create identity.

## Best visualization ideas for your team page

These are the highest-value visuals for this project.

### 1. Rating Delta Schedule

Best first visual.

Design:

- horizontal schedule rows
- a delta bar at the far right
- green = gained rating
- red = lost rating
- gray = little movement

Why it wins:

- Instantly understandable
- unique to your model
- perfect for mobile and desktop

### 2. Power River

A smoothed season trend line that looks like a river or waveform across the schedule.

Enhancements:

- opponent badges as markers
- postseason shaded band
- byes as breaks

### 3. Resume vs Power Scatter

Plot the team against all peers.

Why it works:

- shows whether the team is overperforming or underperforming record
- easy to compare divisions and conferences

### 4. Opponent Ladder

Order the team's games by opponent strength instead of date.

This creates a second view of the season:

- best win
- strongest opponent faced
- weakest loss
- "how many top-50 caliber teams did they survive?"

### 5. History Skyline

A year-by-year skyline chart where each bar is a season and height is final power rating.

Layer:

- championships
- playoff seasons
- coaching eras

### 6. Volatility Meter

How much the team's rating swings from week to week.

This is fun because it creates identities:

- stable powerhouse
- boom-bust chaos team
- late-season riser
- paper tiger collapse

### 7. Schedule Difficulty Ribbon

A ribbon under the season chart showing opponent strength each week.

This helps explain why a close win may have boosted rating more than a blowout over a weak team.

### 8. Season Fingerprint

A compact identity card:

- offense
- defense
- schedule
- consistency
- clutch factor
- dominance

Great for sharing and comparing teams.

## Team page modules by implementation realism

### Safe with SportsDB + your own model

- current team profile
- current season schedule
- results and scores
- opponent list
- year-by-year records
- rating-over-time charts
- rating deltas by game
- historical rating arc
- venue / city / branding / artwork
- trophy / championship callouts where data exists

### Probably possible, but verify team-by-team

- roster modules
- player modules
- lineup cards
- per-event stat summaries
- YouTube highlight embeds
- venue pages / stadium imagery

### Risky to promise from SportsDB alone

- complete player stat databases
- reliable play-by-play driven EPA visuals
- universal event timelines
- conference standings logic
- rich depth charts
- fully accurate historical coaching and metadata text
- guaranteed lower-division completeness

## Strong recommendation for v1

Build the team page around what you can guarantee:

### Core v1

- hero profile
- season rating story
- schedule timeline
- historical seasons table
- historical rating line
- best wins / worst losses
- team identity profile card

### Optional v1 if present

- roster snapshot
- highlights
- lineups
- event stat cards

### Do not anchor v1 around

- play-by-play charts
- full player stat leaderboards
- standings
- deep recruiting / NIL

## Data model recommendation

To make the team page great, create your own normalized layer on top of SportsDB.

### Store these raw entities

- teams
- seasons
- events / games
- venues
- players when available
- event stats / lineups / timelines when available
- artwork URLs

### Derive these stable product fields

- pregame team rating
- postgame team rating
- rating delta
- opponent strength at game time
- opponent strength now
- schedule difficulty score
- result quality label
- season summary record
- final season rating
- trend over last N games
- volatility score

That derived layer is what makes the site yours instead of a thin API wrapper.

## Recommended copy and UX patterns

The user should never wonder "why did the rating move?"

Each game row should answer it in one sentence:

- `Beat No. 34 Georgia by 11. Rating +2.4 because it was a high-leverage win over an elite opponent.`
- `Lost at No. 7 Oregon by 3. Rating -0.2 because the performance was stronger than the result.`
- `Beat FCS opponent by 35. Rating +0.1 because the model expected a comfortable win.`

This is one of the best product decisions you can make.

## Final recommendation

The best team page for this project is not:

- a stats dump
- a roster dump
- or a plain schedule page

It is:

`a beautifully visual season-and-history dashboard centered on rating movement`

That choice is also the best fit for your current data constraints.

SportsDB can give you enough to build:

- team identity
- schedules
- opponents
- scores
- seasons
- artwork

And your model can give you the real magic:

- movement
- context
- explanation
- comparability across all levels

## Sources

- TheSportsDB pricing: https://www.thesportsdb.com/pricing
- TheSportsDB docs: https://www.thesportsdb.com/documentation
- TheSportsDB data guide: https://www.thesportsdb.com/docs_api_data
- TheSportsDB artwork guide: https://www.thesportsdb.com/docs_artwork
- TheSportsDB American Football leagues: https://www.thesportsdb.com/Sport/American-Football
- TheSportsDB NCAA Division 1 league page: https://www.thesportsdb.com/league/4479-ncaa-division-1
- TheSportsDB Alabama team page: https://www.thesportsdb.com/team/136168-alabama
- TheSportsDB Indiana vs Alabama event page: https://www.thesportsdb.com/event/2400645-indiana-vs-alabama
- TheSportsDB Oklahoma vs Alabama event page: https://www.thesportsdb.com/event/2392368-oklahoma-vs-alabama
- Sports-Reference Alabama school history: https://www.sports-reference.com/cfb/schools/alabama/index.html
- ESPN Alabama team home: https://www.espn.com/college-football/team/_/id/333/alabama-crimson-tide
- ESPN Alabama team stats: https://www.espn.com/college-football/team/stats/_/type/team/name/ala
- ESPN Alabama roster: https://www.espn.com/college-football/team/roster/_/id/333/alabama-crimson-tide
- On3 Alabama team page: https://www.on3.com/college/alabama-crimson-tide/
- Sofascore Alabama Crimson Tide team page: https://www.sofascore.com/american-football/team/alabama-crimson-tide/4312
- CollegeFootballData SP+ trends: https://collegefootballdata.com/sp/trends
- Game on Paper CFB: https://gameonpaper.com/CFB/
