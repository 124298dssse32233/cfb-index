# Historical Context And Preseason Priors

Date: April 21, 2026

## Why this memo exists

The site now has enough multi-season data to stop treating history as a footnote.

For a world-class college-football product, previous seasons need to matter in two different ways:

1. Statistical context
- Prior seasons should shape preseason power ratings, especially before enough new games exist.
- That prior should reflect recent on-field quality, roster continuity, and talent inputs.

2. Product context
- Users want the current board to have memory.
- They care about questions like:
  - Is this the best season this program has had in years?
  - Is the team actually better than last year, or just running hot on the schedule?
  - What are the greatest and worst seasons in the loaded archive?
  - Is this conference rising or falling across seasons?

That means the site should treat history as part of the main experience, not as a separate dusty archive.

## What the best public systems do

### ESPN FPI

FPI is explicitly a forward-looking strength rating, expressed in points above or below average, and used for future projections and simulations.

Source:
- https://www.espn.com/blog/statsinfo/post/_/id/109828/reintroducing-espns-college-football-power-index

Takeaway:
- The predictive rating should stay on a point-based scale that translates naturally into spreads, win probabilities, and matchup previews.

### Bill Connelly's SP+

SP+ is the clearest public blueprint for how prior seasons should affect preseason power.

Connelly's preseason descriptions consistently emphasize that the projection is built from:
- last year's rating
- returning production
- recruiting / talent
- recent program history
- portal-era roster context

One especially useful public summary described the preseason mix as roughly:
- a bit more than 60% from last year's rating plus returning production
- about 14% from recruiting and transfer quality
- a bit more than 20% from recent history

Sources:
- https://www.espn.com/college-football/story/_/id/28649423/college-football-teams-most-returning-production-2020I
- https://www.espn.com/college-football/insider/story/_/id/30847607/college-football-preseason-sp%2B-projections
- https://www.espn.com/college-football/insider/story?id=44011175

Takeaway:
- We should not start every new season from scratch.
- We should also not let last season overwhelm current-season evidence forever.
- The right answer is strong preseason shrinkage that fades as the season unfolds.

### FEI

FEI remains important because it focuses on opponent-adjusted possession efficiency and non-garbage possessions.

Sources:
- https://bcftoys.com/glossary
- https://bcftoys.com/2025-fplus

Takeaway:
- Historical and predictive storytelling should eventually include drive-level and play-level quality, not only record and score margin.
- If we want the site to feel elite, users need both season narratives and sustainable-efficiency signals.

### KenPom conference logic

KenPom's conference ratings framing is useful because it is not just a naive average of team ratings. The conference question is closer to:

"How strong would a hypothetical average team have to be to go .500 in this league?"

Source:
- https://kenpom.com/blog/ratings-methodology-update/

Takeaway:
- Historical conference pages should show both depth and top-end quality.
- A conference's strength across time should read like an ecosystem, not a flat average.

## What our current data stack can and cannot do

### What Tier 2 CFBD is strong enough to support

The official CollegeFootballData tiers page says Tier 2 includes:
- advanced metrics
- opponent-adjusted metrics
- recruiting data
- live scoreboard
- live play-by-play

Source:
- https://collegefootballdata.com/api-tiers

That is more than enough for:
- team history pages with richer rating movement
- possession-aware or play-aware team narratives
- recruiting and talent-aware preseason priors
- strong archival leaderboards

### Where the data constraints still matter

The GraphQL docs show transfer-related queries, but those appear under Tier 3 access.

Source:
- https://graphqldocs.collegefootballdata.com/

Takeaway:
- We should not assume premium transfer data is available in the current setup.
- For now, the preseason prior should lean on:
  - previous season power
  - recent program baseline
  - returning production
  - talent composite
  - recruiting team score
  - roster continuity proxy
- If Tier 3 or another source is added later, transfer-specific adjustments can become much stronger.

### SportsDB's role

SportsDB is still useful, but not as the main historical/model backbone.

Best use cases:
- logos
- venue metadata
- presentation enrichment

Weak use case:
- all-level historical football modeling

## Product strategy: how history should show up on the site

### Home page

The landing page should not just show "who is good now." It should answer:

- What is the strongest loaded season?
- Which program just made the biggest year-over-year jump?
- Which program has sustained elite power across multiple loaded seasons?
- Which programs are volatile enough that priors should be treated carefully?

The correct homepage treatment is a `History Lab` section with premium cards, not a buried archive link.

### Rankings page

The rankings page should treat history as argument fuel.

Recommended historical modules:
- greatest loaded seasons
- strongest loaded teams
- biggest year-over-year risers / falls
- conference movement across seasons
- archive timeline that shows how the board changed week by week

### Team pages

Team pages should treat history as a core explainer.

The ideal historical stack for every team page:
- Program Arc chart
  - bars for win rate
  - line for end-of-season power
- Loaded History Signals cards
  - strongest loaded team
  - best loaded resume
  - year-over-year swing
  - roughest loaded season
- Year-by-year table with:
  - record
  - final rank
  - end power
  - end resume
  - scoring margin

This is the right product move because fans rarely want a current-season page with no memory.

### Future history products

The next wave after the current implementation should be:

1. Program pages beyond a single season
- full historical timeline
- all-time best and worst seasons
- greatest single-game upsets
- best wins by era

2. Historical league pages
- conference power across seasons
- rise/fall tables
- era comparisons

3. Queryable "Stathead-like" explorer
- best seasons by level
- best two-year runs
- biggest turnarounds
- most stable programs
- best DII or DIII teams on the all-level board

4. Historical similarity engine
- this season's team compared to loaded predecessors
- strongest match by offense / defense / overall profile

## Model strategy: how previous seasons should affect power

### The right high-level rule

The preseason prior should be built from:

- subdivision baseline
- previous season end power
- weighted recent program baseline
- current conference environment
- returning production
- quarterback continuity
- talent and recruiting
- roster continuity proxy
- transfer balance if and when trustworthy data is available

### The wrong rule

Do not use:
- hard ceilings by level
- fully manual overrides for whole subdivisions
- pure last-year carryover with no roster context

### The right public framing

Users do not need a giant table of internal scaffolding terms.

They do need a simple story:
- this team starts higher because it has earned it across recent seasons and still brings back real strength
- this team starts lower because last year's performance was thin and the roster foundation changed

So the frontend should emphasize:
- historical strength
- continuity
- roster carryover
- offseason context

And avoid jargon-heavy internal uncertainty labels unless they are helping a specific experience.

## Immediate build implications for this repo

### Already worth shipping now

- Historical season ledger shared across the homepage, rankings page, and team pages
- Program Arc chart with both win rate and end-of-season power
- Year-by-year team tables with final rank, end power, and end resume
- Homepage / rankings page historical context cards

### Next backend work that matters most

1. Populate offseason tables for the loaded seasons
- `returning_production`
- `team_talent_snapshots`
- `recruiting_entries`
- `roster_entries`

2. Continue backfilling older seasons
- more years make the history layer dramatically better
- more years also improve recent-program-baseline priors

3. Add a smoother preseason ingestion path
- current preseason roster ingestion should not require manually naming every team forever

4. If available later, add transfer-specific priors
- either through higher-tier CFBD access or a high-quality secondary source

## Product thesis

If the site wants to feel like the best college-football analytics destination on the internet, history cannot be a static archive.

It needs to be:
- visible on the homepage
- integrated into the rankings experience
- central to team pages
- directly tied to how preseason power is built

That is how the product becomes both smarter and more addictive.
