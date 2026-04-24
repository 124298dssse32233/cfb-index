# Team Page — World-Class Redesign Brief

**Status:** Strategy + IA + UX guidance. Companion to `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`.
**Owner:** Kevin (product), Claude (research + drafting).
**Last updated:** 2026-04-23.
**Scope:** All FBS team pages, designed to generalize down to FCS/D-II/D-III with graceful degradation.
**Reference pages audited:** Indiana, Alabama, Ohio State, James Madison, Montana State, Notre Dame (from `CFB_INDEX_AUDIT.md`).
**Related docs:**
- `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` — the sibling brief; design system shared.
- `FAN_INTEL_SOURCE_STRATEGY.md` — canonical source + cohort reference.
- `CFB_INDEX_AUDIT.md` — site-wide audit; team-page issues catalogued.
- `FAN_INTEL_BUILD_PLAN.md` — execution roadmap.
- `CLAUDE.md` — repo rules.

---

## 0. Why this doc exists

The player page brief established CFB Index's design language: FI as the spine, stats as the foundation, analytics as the exhibit. The 4-tier reading ladder, the 17-rung standing rail, the Savant card, the dark FI card, progressive disclosure everywhere — all of it lives there.

The team page cannot simply inherit this system. It must extend it, because teams are a fundamentally different entity class:

- A **player** has a career arc. A **team** has an *era arc* and a *dynasty arc* — multiple timescales that coexist on one page.
- A **player** is watched by fans. A **team** *has* fans — a fanbase that is itself an analytical object with health, fractures, archetypes, and inter-cohort divergence.
- A **player** competes against peers for individual honors. A **team** competes against history, against conference rivals, and against its own previous selves simultaneously.
- A **player's** supporting cast is a few receivers and linemen. A **team's** "supporting cast" is a recruiting pipeline, a coaching staff, a schedule, a conference, and a culture — all of which shape outcomes in ways no single player can.
- A **player** page has one clear forward-looking signal (accolade probability). A **team** page has five: win projection, conference standing, CFP probability, recruiting class rank, and coaching staff stability.

This brief answers the question: given everything the player page established, what does a world-class *team* page look like?

---

## 1. Team Page Philosophy

### The core thesis

> **The team page is a living argument about where this program stands — in the moment, in the season, in the era, and in history — told first through the emotional truth of its fanbase.**

The player page thesis was: *FI is the spine. Stats are the foundation. Analytics are the exhibit.*

For teams, the thesis extends: **FI is the spine. Results are the foundation. Context is the exhibit. Time is the axis.**

The key word is *time*. Teams exist at the intersection of multiple timescales simultaneously, and the best team page gives any fan — regardless of what they're hunting — a clean on-ramp to the timescale they care about. A casual fan who just watched Saturday's game wants "this week." A die-hard wants "this season." A historian wants "the Coach X era." An argument-settler wants "all-time vs. [rival]." The page must serve all four without burying any of them.

### Three layers, one page

Like the player page, the team page has three stacked layers — but they're recalibrated for team reality:

1. **The belief layer at the top** — In 5 seconds, you know what the fanbase believes about this team right now, where that diverges from reality, and what the nation thinks. Pure FI. Tribal, emotional, polarizing.
2. **The performance layer in the middle** — This week's result, the season arc, conference position, team-level savant card. Cleaner and more contextual than ESPN/SR. Every number has a rank, percentile, and trend.
3. **The context layer behind drawers** — Era arc, dynasty history, recruiting pipeline, coaching staff fingerprint, rivalry module, program trajectory. The analytical exhibit that makes a casual browser into a 20-minute reader.

### What this is *not*

- Not another stat aggregator. ESPN has stats. Sports Reference has stats. The page's claim to authority is *interpretation + belief*.
- Not a Wikipedia clone. Program history is a module, not the page.
- Not a recruiting database. 247Sports and On3 own that. The pipeline module is a *forward-looking signal*, not a roster tracker.
- Not a coaching biography. The staff module is about *scheme fingerprint* and *stability signal*, not résumés.

---

## 2. The Reading Ladder for Teams

The same four tiers from the player page, re-mapped to team-specific modules.

### 5-Second Read — The Identity Flash

The fan who arrives from a social share, a Google result, or a link in an argument needs to orient in five seconds. One number, one vibe, one trajectory.

**Modules:**
- **Team Identity Hero** — School wordmark, current record, current national/conference rank, team prestige rung (see §3), and the single most important FI signal right now (fanbase archetype label + mood headline).
- **Season Pulse Bar** — A compact 8-game result strip (W/L chips, color-coded) and a one-sentence state-of-the-program read: *"Alabama is 8-0, controlling their destiny, with a fanbase that's cautiously optimistic — the most restrained they've been at this stage in six years."*

**Design rule:** Everything in the 5-second zone must render in < 0.8s FCP. No JS dependency. Static HTML.

### 30-Second Read — The Casual Fan Ceiling

This is the ceiling for most mobile traffic arriving from social media or a Google search. They want the scoreboard version of the whole program. They'll leave after this zone if nothing pulls them deeper.

**Modules:**
- **"The Room on [Team]"** — The FI dark card (see §4). Fanbase mood, belief vs. reality, polarization, top storyline. One card, maximum signal density.
- **Season Snapshot** — Record, AP/Coaches rank (if ranked), SP+ rating, conference standing (games back / games ahead). Three tiles, each with a trend chip.
- **CFP/Bowl Probability** — Single tile: current probability of making the CFP (for P4) or a bowl game (for G5). With trajectory spark. This is the one forward-looking number every fan wants.
- **Next Game Context** — Opponent, Vegas line, model projection, days until kickoff. Lightweight — 4 cells.

**Design rule:** The 30-second zone must be scrollable without opening any drawer. No module in this zone requires a tap to get value.

### 5-Minute Read — The Engaged Fan

This fan came to *learn*, not just check. They'll spend 5+ minutes and might share something they found.

**Modules:**
- **Season Arc** — Week-by-week game results with SP+ opponent quality, margin of victory, and turning-point annotations. Compact table + trajectory line.
- **Team Savant Card** — 12-15 percentile bars (see §5). The screenshot-bait.
- **Rivalry Module** — The big one: head-to-head history, recent trajectory, fan heat readings (see §7).
- **Conference Lens** — Toggle: national frame vs. conference frame. Rankings, metrics, standing (see §10).

### Deep-Dive — The Analytics Fan / The Superfan / The Argument-Settler

**Modules:**
- **Era Arc** (the Coach X era, all-time) — Multi-timescale navigator (see §6).
- **Recruiting Pipeline** — Class rankings, commit momentum, portal net (see §8).
- **Coaching Staff Context** — Scheme fingerprint, coordinator ratings, staff stability (see §9).
- **Program Trajectory Arc** — 10-year prestige rung chart (see §11).
- **Full Schedule + Results Explorer** — Filterable/sortable game log with all analytical columns.
- **Peer Comparator** — Auto-picks 3 comparable programs by prestige, region, resources.

---

## 3. Team Standing / Prestige Rail

### Why the player ladder doesn't translate directly

The player ladder (R00 walk-on → R16 Heisman winner) is career-state at a point in time. A team's "standing" is multi-dimensional: there's *current season standing* (where are you in the national picture right now), *program prestige* (the accumulated weight of history + resources + recent success), and *era standing* (how does this specific stretch of seasons compare to the program's own past). These are three different concepts, and conflating them produces nonsense.

The solution: two separate rails that coexist on the page.

### 3.1 The Season Standing Rail — 9 rungs

Answers: *Where is this team in the national picture this season?*

```
RUNG 0 — Not in FBS (FCS / D-II / D-III)
RUNG 1 — FBS, sub-.500 / winless
RUNG 2 — FBS, bowl-ineligible but competitive
RUNG 3 — Bowl eligible (6+ wins, no ranking)
RUNG 4 — Ranked (AP/Coaches, 25-16)
RUNG 5 — Ranked (Top 15, 15-6)
RUNG 6 — Ranked Top 5 / CFP contender
RUNG 7 — CFP Quarterfinal / Semifinal
RUNG 8 — CFP Championship game
RUNG 9 — CFP National Champion
```

**Current-season placement:** Short-circuit cascade using AP rank → CFP selection committee ranking → SP+ top-25 → win count + bowl eligibility. Updated Mondays.

**UI:** Same horizontal rail concept as the player page. Filled marker at current rung, ghost marker at start-of-season projection (from preseason SP+), accolade gold for the championship rung. Below the rail: *"Alabama is a CFP Contender (Rung 6). Projected Rung 6 entering the season. No movement — they're exactly where the model expected them."*

### 3.2 The Program Prestige Rail — 7 tiers

Answers: *What kind of program is this, historically?*

This is the slower-moving, era-weighted signal. Fans don't need weekly updates on prestige. They need calibration — *is Notre Dame a blue blood? Is James Madison a mid-major ascender? Is Kansas recovering or collapsing?*

```
PRESTIGE TIER 1 — Regional Program (limited national profile)
PRESTIGE TIER 2 — Mid-Major Contender (G5 force, occasional national attention)
PRESTIGE TIER 3 — Power Program (consistent P4 presence, regional brand)
PRESTIGE TIER 4 — National Program (sustained top-25 expectations)
PRESTIGE TIER 5 — Blue Blood (generational elite; Alabama, Ohio State, Oklahoma, Michigan, Notre Dame, Clemson, USC, LSU, Texas, Georgia tier)
PRESTIGE TIER 6 — Dynasty Active (currently executing a multi-year elite run)
PRESTIGE TIER 7 — All-Time Great Era (historical peak, may be past)
```

**Placement:** Based on 5-year rolling SP+ average + national title count + AP poll top-10 frequency (10-year window) + recruiting rank (5-year average). Updated annually in preseason.

**UI:** Compact horizontal tier bar, not a full 17-rung rail. More like a brand meter. The team's tier name in large type: *"BLUE BLOOD."* Below: *"Historical peak: Tier 6 / Dynasty Active (2015–2021 Saban run). Current tier: Tier 5."* Allows for honest nuance — a team can be a Blue Blood (Tier 5) without currently being in a dynasty.

### 3.3 Historical Peak marker

Every team gets a ghost marker at their highest-ever achieved rung (both Season and Prestige). This one visual answers the nostalgic question every fan walks in with: *"Are we as good as we used to be?"*

---

## 4. "The Room on [Team]"

The FI dark card from the player page is the model — but teams need a substantially expanded version because the FI data is richer and the analytical dimensions are more complex.

### 4.1 The key difference: fanbases are analytical objects

For a player, "The Room on [Player]" captures what people *say about* someone. For a team, "The Room on [Team]" captures the fanbase as an entity *in itself* — its archetype, its internal fractures, its relationship to rival fanbases, and how it compares to where it was last week / last season / in the team's best era.

This distinction is product-defining. CFB Index isn't just measuring what people say about Alabama — it's measuring the *Alabama fanbase* as a force in the sport.

### 4.2 The five panels of the Team FI Card

**Panel 1 — Fanbase Archetype + Headline**

Lead with the archetype. Every fanbase has one, and it changes across the season. From the cohort system, we can derive:
- **Fanbase archetype label** — computed from the divergence score + belief direction + volatility. Example archetypes: *"The Believers"* (high sentiment, low divergence, consistent), *"The Siege Mentality"* (high belief despite external criticism, strong in-group cohesion), *"The Glass Half Full"* (moderate belief, lots of cope signaling), *"The Fractured Kingdom"* (high divergence, internal fights), *"The Quiet Observers"* (low volume, undecided), *"The Powder Keg"* (moderate season record, extremely high volatility in sentiment week-over-week), *"The Doomers"* (negative sentiment despite winning).
- **FI Headline** — one generated sentence capturing the week's dominant belief. *"Ohio State fans are projecting controlled confidence — the ceiling talk is back, but the skeptics haven't gone quiet."*
- **Belief Dial** — port from the existing `mood-meter-track` component. Doomposting → Mixed → Very Bullish. Current week pinned, last week and start-of-season as ghost ticks.

**Panel 2 — The Five-Axis Strip**

Five signals, each a compact meter:

1. **Reality Gap** — Fan belief vs. SP+ model rating. Signed + labeled: *"Fans are 0.8 SD more bullish than the model. They see something it doesn't."* or *"Fans are underrating this team despite a top-10 SP+."*
2. **Respect Gap** — Fan belief vs. national media perception. Uses Wikipedia edit activity + national Reddit/Bluesky mention sentiment as the national proxy. *"The country thinks less of this team than its own fans do — a chip-on-shoulder setup."*
3. **Cohort Divergence** — The stdev of sentiments across qualifying cohorts (from `team_cohort_divergence_week`). A segmented red/grey/green bar showing internal alignment. *"Die-hards bullish. Analytics cohort skeptical. Gen Z quiet. High internal friction."*
4. **Rival Heat** — The combined sentiment across rivalry-specific source filters. *"LSU fans: elevated. Texas A&M fans: obsessed. Ole Miss fans: curious."* Three rival pills, color-coded (blue = calm, amber = warm, red = hot).
5. **Volatility** — Week-over-week swing magnitude in the belief score. *"Sentiment swung +1.4 SD in the last 7 days — the biggest single-week jump since the Week 9 comeback against Georgia."*

**Panel 3 — Home vs. Away Mood Split** *(team-specific, no player equivalent)*

This is one of the most unique things CFB Index can surface. Home crowd energy and away fan behavior produce measurable differences in sentiment signal — SeatGeek ticket price splits, Reddit thread tone before home vs. away games, local market sentiment vs. national sentiment.

- **Home mood** — sentiment from local-market sources (local radio RSS, city subreddits, SeatGeek home listing counts) vs. the team's seasonal baseline.
- **Away mood** — national sentiment, away-ticket demand, away-fan posting volume (a proxy for road-game energy from the diaspora).
- **Delta** — *"This fanbase shows up louder at home than it does nationally — a typical regional-pride program."* vs. *"The traveling fan base is as fired up away as at home — national brand effect."*

**Panel 4 — Top Storylines**

Three ranked narratives this week, sourced from the conversation pipeline. Team-scoped (not player-scoped — those live on the player page). Examples:
- *"Offensive line criticism: a plurality of posts this week questioned pass protection, citing the sack rate trend."*
- *"The CFP seeding debate: fans split on whether a road win vs. a top-10 team is enough to jump two spots."*
- *"Portal anxiety: the coordinator departure rumor is driving outsized conversation vs. its likely impact."*

Each storyline has a **Platform Blend chip** showing which source tier it's coming from (`board_heavy`, `reddit_dominant`, `media_driven`, `cross-platform`) — so the fan knows if this is a fringe-board panic or a broad consensus concern.

**Panel 5 — The Confidence Badge**

Same as the player card: *"N mentions · high/moderate/low confidence."* The team has far more conversation volume than any individual player, so this should rarely be low — but when it is (off-season, G5 programs), the honest display protects the brand.

### 4.3 Empty/off-season state

Rather than "Awaiting Signal," the team FI card should pivot to the most recent in-season snapshot with an honest timestamp: *"Last full data: Week 21 (2025 season). Off-season signal is limited — sentiment reflects post-bowl reaction and spring portal discussion."* This is infinitely better than a blank card. Teams don't have off-seasons — their fanbases are always active.

---

## 5. Team Savant Card

The team equivalent of the QB Savant card. Same visual grammar — vertical percentile bars, red→grey→blue gradient, ordered best→most interesting→concerns — but with team-level metrics.

### 5.1 The 15 metrics

Ordered in the exact sequence they should render (best claim → story → concern):

**Offense side:**
1. **EPA/play** (opponent-adjusted) — The single best overall offensive efficiency metric
2. **Success Rate** (overall offense) — What percent of plays gain positive expected value
3. **Havoc-Adjusted Points Per Drive** — Drives that score adjusted for defense quality faced
4. **Explosive Play Rate** (10+, 20+ plays per game) — The fun-to-watch metric every fan cares about
5. **Red Zone TD Rate** — Efficiency inside the 20. Elite teams convert drives to TDs, not FGs
6. **3rd Down Conversion %** — Self-explanatory narrative gold

**Defense side:**
7. **EPA Allowed/play** (inverted — lower is better) — Flipped bar, labeled clearly
8. **Defensive Success Rate Allowed** (inverted) — Opponent's success rate against this D
9. **Havoc Rate** — Sacks + TFLs + passes disrupted per play. High havoc = dominant front
10. **Red Zone TD% Allowed** (inverted) — Goal-line stands matter enormously to fans
11. **3rd Down Stop Rate** — Complement to the offensive 3rd-down metric

**Special situations:**
12. **Turnover Margin** (per game, season-adjusted) — The luck/execution wildcard
13. **Field Position Battle** — Average starting field position vs. opponent average
14. **SP+ Rating** — The summary number, placed last so context precedes it
15. **Opponent-Adjusted SOS** — Strength of schedule chip, because everything else is meaningless without it

**Peer toggle:** vs. FBS / vs. Power-4 / vs. Conference / vs. All-time program (the last one is unique to teams).

**Narrative header line:** *"Elite: defensive havoc (97th). Strength: red zone defense (91st). Mixed: offensive explosiveness (58th). Concern: 3rd down offense (31st)."*

### 5.2 What's different from the player Savant card

- **Inverted bars** are more common (any defensive metric). Make the inversion visually obvious — a downward arrow icon, not just a flipped gradient — so fans don't mistake "lower is better" context.
- **The peer toggle includes an all-time program comparison** — unique to teams. *"Where does this year's Alabama defense rank against Alabama defenses since 2010?"* This is a feature no competitor offers.
- **Two-sided card** — offense and defense as two halves of the same card, not two separate modules. Tabs: Offense | Defense | Overall. The default is Overall (the most editorial-curated set), but hard-cores can split.

---

## 6. Season Arc vs. Era Arc vs. Dynasty Arc

This is the most complex module concept in the brief — and the one most unique to team pages. Players don't have eras. Teams live in them.

### 6.1 The time navigator — the central UX concept

A single horizontal timeline bar sits at the top of the "Arc" module. It has three zoom levels, toggled by pill:

- **This Season** — Week-by-week view of the current season
- **The [Coach] Era** — Every season under the current (or most recent) head coach, in one row per season
- **All-Time** — Every season in the program's recorded history, one row per decade

The magic is that the same underlying data powers all three views. The metrics don't change. The time window does. This is container-query and data-pagination architecture, not three separate modules.

### 6.2 Season Arc view ("This Season")

**Week-by-week game strip:**
- Opponent name + rank (at time of game)
- Result chip (W/L + score + margin color: green for blowout, yellow for close, red for loss)
- SP+ opponent quality percentile chip
- EPA/play for that game (tiny bar)
- Fan mood for that week (tiny belief dial reading from `team_week_conversation_features`)

The key innovation: **mood under results**. Every game row shows what the fanbase was feeling that week. The pattern is often more revealing than the results themselves. *"They won five straight but the mood dial never got above 'cautious' — the belief wasn't there even when the wins were."*

**Season trajectory line:** Above the game strip, a line chart of weekly SP+ rating (y) vs. week (x), with win/loss annotations. One visual, the whole story.

### 6.3 Era Arc view ("The [Coach] Era")

One row per season. Columns:
- Season year + Record
- Prestige Rung achieved (Season Rail rung number)
- SP+ rank at end of season
- Conference result (champion / division winner / also-ran)
- Bowl result (chip: win/loss + bowl game name)
- Fan mood at season end (the final-week belief reading)
- Net recruiting ranking for that class

**The era summary bar:** Automatically generate a one-line era thesis: *"Under Kirby Smart: 9 seasons, 2 national titles, 4 CFP appearances, 5 SEC titles. SP+ has never ranked below #7. Average recruiting rank: 2nd nationally. Fanbase mood has trended bullish since 2021."*

**Coach era comparison:** When viewing an era, show a peer bar: *"Comparable coaches entering their 9th season with similar resources: Nick Saban 2014, Urban Meyer 2011, Dabo Swinney 2021."* Not a copy of the player Peer Comparator — a program-level comparator.

### 6.4 Dynasty Arc view ("All-Time")

Decade-level aggregates, rendered as a horizon chart or step chart — not a table, because decade-level data is a visual story, not a lookup problem.

Key all-time data points per decade:
- Win% 
- National titles / CFP appearances
- Conference championships
- Consensus All-Americans produced
- Peak SP+ ranking achieved
- Average recruiting rank (where available)

**The "Are we there yet?" callout:** In the all-time view, annotate the current era vs. the program's historical peak. *"The 2015–2021 Alabama dynasty is the program's historical apex (Tier 7). The current era (2022–present) is tracking as Tier 5 — strong but not at that altitude."* This is the honest historical context every fan both fears and craves.

### 6.5 The "Timescale Switcher" UI pattern

The three-pill toggle (This Season / [Coach] Era / All-Time) should be persistent and sticky when the module is in view — not buried inside a drawer. When a fan switches timescales, the game strip / season table / decade chart swaps with a smooth transition (420ms data-entry animation, staggered rows). URL updates to reflect the timescale selection (shareable deep link: `/teams/alabama?arc=era`).

---

## 7. Rivalry Module

Rivalries are not a nice-to-have for a team page. They are a core identity primitive. For Alabama, *The Game* vs. Auburn is as central to the program's identity as any title. For Ohio State, the Michigan game *is* the season in some years. A team page without a world-class rivalry module is an incomplete product.

### 7.1 What a rivalry module must answer

A fan arrives at a rivalry module with one of four mental states:
1. **The historian** — *"Who has the all-time edge, and is the trend moving toward us?"*
2. **The argument-settler** — *"Are we actually better right now, or are we riding narrative?"*
3. **The emotional fan** — *"How is the other fanbase feeling? Are they scared? Are we scared?"*
4. **The game-week preparer** — *"What do I need to know before Saturday?"*

The module must serve all four without being a wall of data.

### 7.2 The Rivalry Card — component structure

Each rivalry gets its own card (max 3 featured rivalries per team, expandable to full rivalry history). The card has four zones:

**Zone 1 — Identity Header**

- Rivalry name (the proper noun: "Iron Bowl," "The Game," "Red River Shootout" — not "Alabama vs. Auburn"). Program detection auto-populates from a rivalry seed table.
- All-time record: large display type. *"27–22–1."* With a small trend indicator: *"Last 10: 6–4 →"*
- Current streak chip: *"BAMA 3-GAME STREAK"* in that program's colors.

**Zone 2 — The Four-Axis Rivalry Matrix** *(the analytical heart)*

Four percentile-bar-style readings, each with a plain-English label:

1. **Win Rate Trend** — Rolling 10-game win rate for each team, plotted together as a two-line spark. Tells you if the rivalry is equilibrating or running away.
2. **Performance Gap** — Average SP+ differential over the last 5 meetings. *"Alabama has outperformed by an average of 14.2 SP+ points. The gap is closing."* Or: *"The gap is actually larger than the scorelines suggest — Ohio State has been more efficient but less lucky."*
3. **Fan Heat Index** — Combined sentiment from rivalry-flagged FI sources for both fanbases in the week leading up to the game. Rendered as two opposing thermometers: your fanbase on the left, theirs on the right. *"Michigan fans at 82nd percentile heat (high obsession). Ohio State fans at 61st (elevated, not peak)."*
4. **Respect Gap** — A new, team-specific rivalry signal: do fans of Team A *respect* Team B, or do they dismiss them? Sourced from tone analysis of cross-team subreddit posts (r/cfb + rival team subs) + Bluesky cross-mention sentiment. *"Georgia fans grudgingly respect Alabama (mixed tone, not dismissive). Alabama fans see Georgia as the standard (elevated deference for a rival — unusual)."*

**Zone 3 — The Timeline**

A horizontal line chart: x = years, y = margin of victory (positive = your team won, negative = loss). Each point tappable to expand the game result + context. Below the chart, two annotation chips auto-populate:
- **Longest win streak** (with years)
- **Most memorable game** (by margin + context)

**Zone 4 — Game-Week Context** *(live when within 14 days of the rivalry game)*

- Current line (Vegas) + model prediction + fan pick % (from any available poll).
- *"Who needs this more"* — a model signal based on CFP implications, rivalry streak, and season momentum. *"Ohio State needs this game more — a loss eliminates them from CFP. Michigan is already in regardless."*
- *"Fan mood going in"* — the FI belief dial for both fanbases in the current week, side by side.
- This panel collapses (or shows historical equivalent) when the game is more than 14 days out.

### 7.3 Rivalry taxonomy (seeded data requirement)

Not all rivalries are equal. The module needs a seed table with:
- **Tier 1 rivalries** — Annual, identity-defining (Iron Bowl, The Game, Bedlam, Red River, Clean Old-Fashioned Hate). Full four-zone treatment.
- **Tier 2 rivalries** — Regular matchups with elevated stakes (SEC West divisional games, Big Ten crossovers). Abbreviated two-zone card.
- **Tier 3 rivalries** — Historical/occasional (The Battle for the Golden Hat, conference games played less than annually). Linked from program page, not team page.

Fan-submitted rivalry nominations (via a lightweight form) as a future P3 enhancement.

### 7.4 The Rivalry Module as FI showcase

This module is where the fan intelligence system proves its value most viscerally. Nobody else measures rival fanbase emotion with this precision. ESPN shows win-loss records. CFB Index shows *how scared the other fanbase is* — and that is a product that will get screenshot-shared before every rivalry game.

---

## 8. Recruiting Pipeline

Recruiting is the one forward-looking signal that genuinely differentiates team health analysis. A team that wins now but is recruiting poorly is a program in decline. A team that's struggling but signing top-5 classes is a program in ascent. This narrative — the gap between current performance and pipeline signal — is one of the most compelling stories in CFB.

CFB Index is *not* competing with 247Sports, On3, or Rivals on recruiting data granularity. Those sites have full-time recruiting reporters. We compete on *interpretation* — what does this pipeline mean for next year, this era, and program trajectory?

### 8.1 The Pipeline Module — three panels

**Panel 1 — Current Class Snapshot**

- Current class ranking (247Sports composite, displayed with explicit source attribution)
- Number of commits, average player rating, number of 5-stars / 4-stars
- **Commit Momentum Spark** — A tiny 8-week sparkline of class rank. Is it climbing or sliding?
- **Pipeline Grade** — A composite A-F interpretation: class rank × player development rate × historical conversion rate (high-rated recruit → NFL draft pick, sourced from CFBD). *"A-: Top-5 class nationally, but development conversion has been below peer programs for 3 years."*

**Panel 2 — Pipeline vs. Performance Gap** *(the interpretation layer)*

This is the module's most valuable contribution. Show the last 5 years of recruiting rank vs. SP+ rank, on the same chart. Two lines. The gap between them is the story.

- **Overperforming programs** (SP+ >> recruiting rank) — *"Iowa has consistently punched above their recruiting weight. Their development model is genuine."*
- **Underperforming programs** (recruiting rank >> SP+) — *"Texas has signed five consecutive top-10 classes. Conversion to wins has lagged. That's either a scheme problem or a development problem — or both."*
- **Aligned programs** (lines close together) — *"Alabama recruits like a #1 program and performs like one. Little mystery here."*

One auto-generated sentence below the chart. This is the kind of editorial interpretation that drives shares.

**Panel 3 — Portal Activity**

The transfer portal has changed recruiting so fundamentally that a pipeline module without it is incomplete. Show:
- **Net portal balance** (this off-season) — commits in vs. commits out. Signed: net positive = green chip, net negative = red chip.
- **Incoming class rating** — 247 composite of portal additions
- **Departure impact** — *"Lost 2 starters (CB, OG). Incoming portal fills: 1 of 2 positions addressed."*
- **Portal velocity** — how quickly the program moves in the portal window (early movers vs. late movers). Early portal success is a coaching staff efficiency signal.

### 8.2 What this module is NOT

- No individual recruit names unless they're publicly committed (no decommit speculation, no crystal ball content). This protects the product from the ethical issues of tracking minors.
- No "who they're targeting" lists. That's recruiting-reporter content. We analyze the results.
- No raw star ratings without interpretation. A 5-star in a poor development program is worth less than a 3-star in Iowa's system. Say that.

---

## 9. Coaching Staff Context

The coaching staff is a team's most important resource allocation decision. But coaching staff information is often either too granular (full staff biographies) or too thin (just the head coach's record). The team page needs a middle path: *scheme fingerprint* and *stability signal*.

### 9.1 The Staff Module — three panels

**Panel 1 — Head Coach Standing**

The head coach gets a compressed version of the Player Standing concept applied to coaching careers:
- **Coach Prestige Rung** — An 8-rung ladder: first-year starter → establishing → solid → strong → elite conference → national elite → dynasty builder → legend. Placement based on career win%, P5 record, CFP appearances, draft production.
- **Contract context** — Years remaining, whether they're an extension candidate or on the hot seat (sourced from beat writer RSS + odds markets like Kalshi coaching markets where available). Honest, not inflammatory.
- **Coach-era summary** — 2-3 sentences auto-generated: record, conference titles, CFP appearances under this coach.

**Panel 2 — Scheme Fingerprint** *(the analytical value-add)*

This is what no competitor offers in a usable form. Using CFBD play-by-play data, derive a scheme fingerprint for both offense and defense:

**Offensive fingerprint metrics (percentile bars):**
- Pass Rate Over Expected (PROE) — Are they more pass-heavy or run-heavy than their game situations suggest?
- Play-action rate — Critical for QB evaluation and for understanding if the scheme protects the QB
- Tempo — Seconds per play (fast vs. deliberate)
- RPO rate — The modern spreading metric
- Pre-snap motion rate — A complexity/sophistication signal

**Defensive fingerprint metrics (percentile bars):**
- Blitz rate vs. coverage shell (4-man rush vs. pressure packages)
- Man vs. zone tendency
- Cover-2 / Cover-3 / Cover-4 split (where data allows)
- Average down-and-distance where havoc events happen (early-down disruptor vs. 3rd-down specialists)

**Fingerprint label:** Distilled into one plain-English tag per unit: *"Offense: Slow-mesh RPO, below-average PROE — a deliberate, run-first identity despite the 4-star talent."* *"Defense: Two-high coverage, low blitz rate — bend-but-don't-break, counting on the secondary."*

This is the one place on the site where a fan gets a real answer to *"what does this team actually look like on the field?"* before they've watched a snap.

**Panel 3 — Staff Stability Signal**

Coordinator and staff turnover is one of the most underrated program health metrics. Track it.
- **Coordinator continuity score** — Number of years the current OC + DC have been in the building. High continuity = scheme depth. Low continuity = re-learning every year.
- **Staff turnover flag** — Has there been a coordinator change in the last 12 months? If yes, a chip: *"New OC: Year 1 of [Name]'s scheme."* This is a huge context flag for evaluating early-season results.
- **Hot seat signal** — If Kalshi / coaching market odds exist for the head coach, surface them as a probability chip (same Tier A sourcing rules as gambling markets). Label it clearly: *"Coaching market: 24% implied odds of a coaching change after this season."* Don't editorialize; just show the market.

---

## 10. The Conference Lens

Teams exist in two frames simultaneously: national and conference. A team ranked #12 nationally might be #2 in the SEC West — or #7 in the Big Ten. These are both true and both important, and the conference frame is often the more emotionally relevant one for fans in October.

### 10.1 The toggle

The Conference Lens is not a separate module — it's a **toggle applied to all data-driven modules**. A pill in the persistent module header: `[National ↔ Conference]`. When flipped to Conference, every percentile bar on the Savant Card recalculates against conference peers. Every ranking chip shows conference rank. The Prestige Rail shows conference-relative prestige.

This is a CSS class swap + DB query parameter change. The heavy lifting is on the data side (precomputing both reference populations), not the UI.

### 10.2 Conference Standing module

A dedicated compact module (30-second zone, below the season snapshot):
- Division standings (or overall standings for conferences without divisions)
- Magic number to win the conference (in-season) or *"X wins needed in [N] remaining games to be division champion"*
- SP+ ranking within conference — often different from the division standing due to schedule variation
- **Conference Respect Gap** — Does the national media overrate or underrate this conference? Show the SP+ average of the conference vs. the AP poll placement of conference teams. *"The SEC is ranked better in polls than SP+ suggests — a legacy bias signal."*

### 10.3 Conference Power Map (lightweight)

A compact table showing all conference teams ranked by SP+ + Record, with your team highlighted. Not a full rankings page — a positioning device. *"You are 3rd in the conference by SP+. The teams ranked above you are your direct path to the title game."*

---

## 11. New Bespoke Concepts for Teams

These concepts have no player equivalent. They are unique to team pages.

### 11.1 Fanbase Health Index

A composite score (0–100) that measures the *vitality* of a fanbase, not its current mood. A fanbase can be unhappy *and* healthy (still engaged, still arguing) or happy *and* unhealthy (apathetic, not showing up).

Components:
- **Volume trend** — Is conversation volume growing or shrinking vs. last year? (Reddit + Bluesky + board activity, normalized)
- **Geographic reach** — Is interest confined to the local market, or spreading nationally? (Wikipedia DMA data + Google Trends regional + Reddit geographic signals)
- **Cross-cohort engagement** — Are multiple cohorts (die-hards, casuals, Gen Z, analytics fans) active, or just one demographic segment?
- **Ticket demand index** — SeatGeek get-in price trend vs. historical baseline. A true revealed-preference metric.
- **Rival engagement** — Are rival fanbases paying attention? High rival-attention is a prestige signal. *"Alabama fans discussing you is a form of respect."*

Rendered as: a single composite needle gauge (0–100), labeled in four bands: *Declining* (0–25) / *Stable* (26–50) / *Growing* (51–75) / *Surging* (76–100). With a year-over-year delta chip.

### 11.2 Ceiling vs. Floor Season Projections

Every team page should surface a probability distribution, not a point estimate, for the season's possible outcomes.

Three scenarios, each with a probability:
- **Floor** — The pessimistic scenario, based on 1-SD downward variance in SP+, adjusted for roster attrition. *"6-6 regular season, bowl eligible, miss bowl if things go wrong."*
- **Base** — The model's central estimate. *"9-3 regular season, likely bowl appearance."*
- **Ceiling** — The optimistic scenario if things break right. *"11-1, CFP contender, conference title game."*

Rendered as a horizontal probability band — not three separate numbers, but a bell curve visualization showing the full probability mass. This is what's been done in weather forecasting for decades (cone of uncertainty) and sports analytics are just catching up. Every fan page becomes an argument about whether reality will hit the ceiling or the floor.

### 11.3 Home-Field Advantage Quantification

Home-field advantage varies enormously by program and venue. Jordan-Hare Stadium plays differently than Kinnick. The Swamp on a night game is not the same as a Tuesday noon kickoff in Ames.

Metrics:
- **Home EPA differential** — Teams' EPA/play at home vs. away, beyond what opponent quality would predict. This isolates genuine crowd effect.
- **Night game effect** — Separate EPA splits for day vs. night home games.
- **Venue rating** — A composite: crowd capacity vs. actual attendance, noise metric (decibel records where available + proxy via Reddit/board energy on home game days), opposing offense performance vs. baseline.

Rendered as: one composite tile in the team hero zone — *"Home-field advantage: Elite (94th percentile). Night games at Bryant-Denny have cost opponents an average of 0.06 EPA/play beyond what the opponent quality model predicts."*

### 11.4 Program Trajectory Arc

A 10-year rolling Prestige Rung chart — the team's own prestige history, plotted as a line. This is the all-time Arc view from §6, compressed into a compact visual for the hero zone.

The insight: trajectory direction matters more than absolute position for story. A program moving from Tier 3 to Tier 5 in five years (Georgia 2016–2022) is a more interesting story than a program holding at Tier 5 (static Alabama). The chart shows the slope.

**Trajectory label:** Generated automatically from the slope: *"Rising"* / *"Steady"* / *"Declining"* / *"Volatile"* (high standard deviation of rung over 10 years).

### 11.5 The "Quiet Years" Detector

A novel concept: some programs have elevated media profiles that dramatically exceed their actual on-field trajectory. The inverse is also true — sleeper programs doing genuine work that flies under the national radar. Identify both.

The signal: SP+ rank vs. media mention volume (GDELT + national Reddit mentions). Programs with high mention volume vs. low SP+ rank are *overexposed*. Programs with low mention volume vs. high SP+ rank are *underexposed*.

A small chip on the prestige rail: *"Media Overexposed: ranked #47 nationally in media mentions, #72 in SP+."* or *"Under the Radar: ranked #14 in SP+, #38 in media attention."* This is a feature that generates Twitter arguments, which is the point.

### 11.6 The Fanbase Fracture Detector

When `divergence_score` from `team_cohort_divergence_week` spikes above 1.5 SD from the team's own seasonal baseline, surface a **Fracture Alert** chip on the FI card: *"Unusual internal disagreement this week — the analytics cohort and the die-hard board cohort are reading this team in opposite directions."*

Explain the fracture: which cohorts are up, which are down, and what the dominant storyline is in each camp. This is the honest version of what talk radio does — instead of claiming a consensus, show the split.

### 11.7 The "Moment" Signal

A once-per-week editorial annotation: if an FI spike (±2 SD) happened in the last 7 days, auto-surface it as a banner on the FI card: *"A Moment happened: the Week 9 comeback vs. Georgia produced the largest single-game FI swing in the last 3 seasons. Belief jumped from 54 to 81 in 72 hours."*

The inverse is also possible and equally important: *"A Moment happened: the offensive coordinator resignation produced the largest negative swing of the season. Belief dropped 22 points in 48 hours."*

---

## 12. Information Architecture

### 12.1 Top-to-bottom page structure

The following is the canonical module order. Order is fixed; modules can be collapsed/hidden but not reordered by the user (we're making editorial decisions, not building a dashboard).

```
[ZONE: 5-SECOND — Always above the fold on both desktop and mobile]
1. Team Identity Hero
   - School wordmark + colors
   - Current record + season week
   - Season Standing Rung (compact pill)
   - Program Prestige Tier (compact pill)
   - Home-Field Advantage chip
   - FI Archetype label + Belief headline

[ZONE: 30-SECOND — First scroll on mobile, right side on desktop]
2. Season Pulse Bar
   - 8-game result strip (W/L chips)
   - Season trajectory spark
   - One-sentence state-of-the-program read

3. "The Room on [Team]" — FI dark card (full 5-panel version)

4. Season Snapshot Tiles
   - Record + SP+ Rank + AP/Coaches Rank + Conference Standing
   - CFP Probability tile (P4) / Bowl Probability tile (G5)
   - Next Game Context (when ≤ 14 days out)

[ZONE: 5-MINUTE — Second scroll zone]
5. Season Arc (This Season view, with Era/All-Time toggle)

6. Team Savant Card
   - Offense tab | Defense tab | Overall tab
   - 15 percentile bars, narrative header
   - National ↔ Conference toggle

7. Conference Lens (compact standing table + magic number)

8. Rivalry Module
   - Featured Rivalry 1 (auto-populated)
   - Featured Rivalry 2
   - "All Rivalries" expansion

[ZONE: DEEP-DIVE — Behind drawers, expanded on demand]
9. Coaching Staff Context
   - Head Coach Standing
   - Scheme Fingerprint (Offense + Defense)
   - Staff Stability Signal

10. Recruiting Pipeline
    - Current Class Snapshot
    - Pipeline vs. Performance Gap chart
    - Portal Activity

11. Program Trajectory Arc (10-year prestige chart)

12. Ceiling vs. Floor Season Projections

13. Fanbase Health Index

14. Peer Comparator (3 comparable programs)

15. Full Schedule + Results Explorer (filterable/sortable table)

[ZONE: EVERGREEN — Bottom of page, rarely changes]
16. Program History strip
    - All-time record, founding year, conference history
    - Notable alumni (NFL draft picks, Heisman winners)
    - Historical honors timeline (national titles, conference titles, consensus All-Americans)

17. Methodology + Data notes footer
```

### 12.2 Desktop layout

Two-column layout for zones 1-4 (hero + FI card side-by-side). Single-column for all subsequent zones, with max-width 1100px to preserve readable line lengths. The Arc module uses a 3-tab navigator as the full-width anchor. Rivalry module: two rivalry cards side-by-side in a 2-col grid.

### 12.3 Mobile layout

Everything stacks vertically. Zone 1 collapses to: wordmark, record, a single rung pill, the FI archetype label + headline, and the W/L strip. The FI card panel tabs become a horizontal snap-scroll. The Savant Card percentile bars are full-width (mobile-natural). The Rivalry module stacks cards vertically. Tables get pinned first columns and horizontal scroll.

**Mobile-specific priority call:** On mobile, the FI dark card moves *above* the Season Pulse Bar. Emotional truth before stats. On desktop, they can sit side-by-side.

### 12.4 The subnav

A sticky subnav (bottom of screen on mobile, below the hero on desktop) with 5 anchors: `Fan Intel | Season | Savant | Rivalries | Deep Dive`. This is the primary navigation within the page and the mechanism for getting to the deep-dive zone without scrolling through everything.

Keyboard shortcut: `F` for Fan Intel, `S` for Season, `V` for Savant, `R` for Rivalries, `D` for Deep Dive. `?` for shortcut overlay.

---

## 13. Competitive Benchmarks

### ESPN

**What they do well:** Brand familiarity, speed (pages are fast on mobile), game log is comprehensive, roster is easy to find. The AP ranking indicator on the team page header is clean.

**What they do poorly:** The team page is a stat aggregator with no editorial interpretation. No FI equivalent. No scheme fingerprint. No era context — a team's entire history is compressed into a record table. Rivalry pages don't exist as a concept — you have to go to the matchup page. Recruiting is outsourced to a link to ESPN recruiting, which is just a redirect to 247. There is zero attempt to quantify fanbase mood or program trajectory.

**Whitespace:** Everything above the fold. ESPN's above-fold team page is a photo, a record, and a game score. There's no editorial thesis about the team. The page doesn't have a point of view.

### CBS Sports

**What they do well:** SP+ integration is the best of the mainstream sites — they actually show SP+ on team pages. The team schedule view is clean. Social integration (highlights, embedded video) is better than ESPN.

**What they do poorly:** No FI layer. No scheme analysis. Recruiting is a footnote. The color scheme and design feel 2018. No progressive disclosure — the page is a flat scroll of widgets.

**Whitespace:** SP+ is there but uncontextualized — no percentile bar, no peer comparison. They show the number and nothing else.

### 247Sports

**What they do well:** Recruiting depth is unmatched — they own this space. The crystal ball / team recruiting score / commitment feeds are the gold standard. Team page layout is dense but predictable for power users. The boards are deeply integrated.

**What they do poorly:** The page is a recruiting database with a thin game results appendage. There's no performance analytics, no scheme data, no fan mood analysis. Their "Fan Sentiment" is a thumbs-up/thumbs-down poll widget — technically fan data, practically noise. The design is chaotic with ads.

**Whitespace:** The gap between recruiting data and performance interpretation is enormous. They know everything about who committed and nothing about what it means for the team's trajectory.

### Rivals / On3

**What they do well:** Both have excellent recruiting reporter networks. On3 has good NIL data. Rivals has the longest institutional knowledge base in recruiting.

**What they do poorly:** Team pages are almost exclusively recruiting-focused. On3's team page design is cleaner than 247 but still an ad-heavy scroll. Neither has any meaningful attempt at performance analytics or fan mood measurement.

**Whitespace:** Same as 247 — the translation layer between recruiting inputs and on-field outputs is nonexistent.

### The Athletic

**What they do well:** The best sports writing on the internet. Team-specific coverage is deep, beat reporters are excellent, and the editorial voice is genuinely authoritative. The subscription model means no ad noise.

**What they do poorly:** It's a publishing platform, not a data platform. Team pages are article feeds, not data surfaces. There's no SP+ integration, no scheme visualization, no FI layer. Rivalries get excellent long-form coverage but no live data module. The trade-off for editorial quality is zero analytics infrastructure.

**Whitespace:** The analytics exhibit layer. The Athletic writes about what SP+ means; CFB Index *shows* it. The Venn diagram between The Athletic's editorial depth and CFB Index's analytical depth is the product vision.

### The Summary Whitespace

No competitor offers:
1. **Fanbase mood as a first-class analytical object** — not a poll, a real measured system
2. **Scheme fingerprint** from play-by-play data, presented in plain English
3. **Era arc + dynasty arc** as a navigable UI, not just a record table
4. **Rivalry module with emotional + analytical dimensions** combined
5. **Pipeline vs. performance gap** as an interpretation layer over recruiting data
6. **Program trajectory arc** as a visual (not just a win-loss history table)
7. **Ceiling / Floor probability distribution** for the season

That's the product. All seven of those are either in this brief or directly implied by it.

---

## 14. Open Questions

**1. How do we handle the program page vs. team page split?**
The audit flagged that CFB Index currently ships two parallel systems: `/teams/<slug>.html` (current season, mood card) and `/programs/<slug>.html` (historical arc). The team page brief described here should probably *be* the unified page — current-season data on the primary scrollable surface, with the Arc module handling history. Should `programs/<slug>` be deprecated and folded into `teams/<slug>`? Or do they serve genuinely different use cases? This is the highest-priority IA decision before any design work starts.

**2. How do we handle G5/FCS/D-II/D-III degradation gracefully?**
The James Madison and Montana State audits show the current product gives G5/lower programs essentially the same page structure as Alabama — with most modules empty. A world-class team page for a G5 program isn't the same as Alabama's page with empty widgets. It should emphasize the right metrics for that competitive context. What's the graceful degradation spec? Which modules collapse, which get alternative content, and how do we preserve editorial quality for a program with thin data?

**3. What's the right data source for scheme fingerprint?**
Play-by-play data from CFBD gives us run/pass tendency, play-action rate, and formation proxies — but coverage quality is uneven for G5 games, and personnel groupings (21 personnel vs. 11 personnel) aren't available in CFBD v2 without significant inference work. PFF has personnel + scheme data but it's paywalled. Do we build from CFBD PBP (imperfect but accessible) or accept a partial product at launch?

**4. How do we handle coaching staff data programmatically?**
Current `reporting.py` pulls head coach records from CFBD, but coordinator data is largely unavailable in structured form. Coordinator identities require a combination of school athletic department scrapes + Wikipedia + ESPN staff pages. The `priority_teams` seed covers 20 programs — is a manual Cowork weekly sweep for coordinator data the right answer for launch, or do we accept "head coach only" until an automated source exists?

**5. What's the fanbase health index refresh cadence?**
The FI mood data is weekly (in-season) and ad-hoc (off-season). But the Fanbase Health Index is a slower-moving signal — year-over-year, not week-over-week. Should it refresh annually? Monthly? At what point does the update cadence matter less because the signal barely moves?

**6. Should rivalry heat data be its own pipeline, or an extension of the existing FI pipeline?**
The rivalry module's "Fan Heat Index" requires cross-team sentiment — specifically, what Team A fans are saying *about* Team B. The current FI pipeline is team-scoped (what fans of Team X are saying). A rivalry heat signal requires either (a) entity tagging in the conversation pipeline (parallel to the player entity tagging work) or (b) a dedicated rivalry-week source adapter that fires in rivalry game weeks. Option (b) is faster but less general. Which do we build first?

**7. How do we handle real-time game-week state without a full live-game infrastructure?**
The team page has natural game-week content (the "Next Game Context" panel, the game-week rivalry card, the pre-game FI pulse) that is most valuable on Thursday/Friday before a Saturday game and becomes stale by Sunday. The current build system is `python manage.py build-site` — a weekly batch rebuild. Is game-week content handled by a more frequent build (daily rebuild triggered by cron?), or by a lightweight JS fetch for the specific game-week tile only, so the rest of the page stays fully static?

---

## 15. Design Craft — Inherited and Extended

### 15.1 What the team page inherits directly from the player page design system

Everything in `PLAYER_PAGE_WORLD_CLASS_BRIEF.md §8` applies:
- Inter Display / Inter typography, fluid `clamp()` scale
- OKLCH three-ramp color system (percentile ramp / belief ramp / accolade gold)
- Four-role motion grammar (Reveal 240ms / State 180ms / Data-entry 420ms / Delight 800ms)
- 44×44 touch targets
- Dark mode default
- Four mandatory states per module (empty / loading / partial / error)
- FCP < 0.8s budget
- Progressive disclosure as the core interaction
- Shareable deep links on every tab/filter state
- Copy-on-tap for every stat

### 15.2 New design primitives unique to team pages

**Timeline Navigator** — The three-pill time-zoom component (This Season / Era / All-Time). Desktop: pill strip inline with the Arc module header. Mobile: full-width pill strip, sticky when the Arc module is in view.

**Rivalry Thermometer** — Two opposing vertical thermometers (your fanbase / their fanbase), rendered as a mirrored bar with the intensity reading as fill height. OKLCH cool→warm→hot gradient, not the percentile ramp (this is emotional temperature, not statistical rank). The one deliberate mixing of color semantics — justified because rivalry emotion is a distinct analytical dimension.

**Prestige Rune Bar** — A 7-step Prestige Tier pill bar (not the same as the 17-rung player rail — it's coarser and slower-moving). Filled solid at the current tier, outlined at all others. No ghost marker (prestige doesn't track week-to-week). A small "historical peak" label below the current tier's position.

**Cohort Divergence Stack** — A horizontal stacked bar showing the distribution of sentiments across qualifying cohorts. Green = bullish segments, grey = neutral, red = bearish. Each segment labeled on hover/tap with cohort name + sentiment score. The one place on the page where the FI system's multi-cohort architecture is made visible to the fan.

**Pipeline Gap Chart** — A two-line chart (recruiting rank + SP+ rank) with the gap between them shaded. The shade color: green if SP+ > recruiting rank (overperformer), red if recruiting rank > SP+ (underperformer). A simple visual that makes the pipeline-vs-performance story instantly readable.

### 15.3 The empty-state philosophy for teams

Teams have content even in the off-season. The "Awaiting Signal" default that plagues the current site should be retired in favor of intelligent fallbacks:

- **FI card in off-season:** Show the last in-season snapshot with clear timestamp + portal/spring practice season substitutes where available.
- **Recruiting pipeline in off-season:** This is when it's *most* relevant — class is being built. Always populated.
- **Season Arc in off-season:** Show the completed season's arc as the default, with "2025 Season" clearly labeled. Not an empty module.
- **Savant card in off-season:** Show end-of-season final metrics with "Final" chip. No need to update until next season's data flows.
- **Rivalry module in off-season:** All-time and trajectory data is always available. Game-week context panel collapses. The rivalry card is never empty.

The principle: **a team page should never look abandoned**. Programs don't stop existing in January. Fanbases don't go quiet. The page should reflect that.

---

## 16. Roadmap — P0 → P3 (Team Page Specific)

### P0 — Immediate structural fixes (1-2 weeks)

1. **Rename "Offensive Reminiscence" / "Defensive Reminiscence"** → "Offensive Comp" / "Defensive Comp" across all 297 FBS team cards. Simple `reporting.py` string change.
2. **Fix the "Stress Point: [win]" label bug** — the Best Wins / Bad Losses module is using the wrong labels. Fix the label logic.
3. **Fix the program page nav gap** — Surface current team pages (`/teams/<slug>.html`) in the primary nav, not just programs.
4. **Season Standing Rung** — Add the 9-rung season rail to the team hero zone. Placement cascade from AP rank → SP+ → win count. Renders for all FBS teams.
5. **Conference Standing module** — Compact standings table. Existing data in CFBD.

### P1 — Core fan experience (2-4 weeks)

6. **"The Room on [Team]" — all 5 panels** — Requires the FI pipeline to be populated. Blocked by FAN_INTEL_BUILD_PLAN Week 2+ completion. But the card component and empty-state should ship immediately.
7. **Team Savant Card** — 15 percentile bars from CFBD SP+ + PBP data. The biggest visual upgrade.
8. **Season Arc (This Season view)** — Game-by-game strip with opponent quality + fan mood underlay.
9. **Rivalry Module (Tier 1 rivalries)** — Seed the top 30 Tier 1 rivalries. Build the four-zone card component.
10. **Off-season FI state** — Replace "Awaiting Signal" across all team pages with timestamped last-season data.

### P2 — The differentiating layer (4-8 weeks)

11. **Era Arc + All-Time Arc** — Timeline navigator, coach-era aggregations.
12. **Coaching Staff Scheme Fingerprint** — PBP-derived scheme metrics for priority 20 teams first.
13. **Recruiting Pipeline module** — 247 composite integration + Portal activity.
14. **Fanbase Health Index** — Composite score from volume + geographic + ticket data.
15. **Program Prestige Rail** — 7-tier prestige placement for all FBS programs.

### P3 — Polish and new concepts (ongoing)

16. **Ceiling / Floor season projections** — SP+ variance model.
17. **Home-field advantage quantification** — EPA split analysis.
18. **Fanbase Fracture Detector** — Automated divergence alerts.
19. **Rival heat as real-time game-week signal** — Pre-game rivalry card live updates.
20. **Program Trajectory Arc** — 10-year prestige chart.

---

## 17. Opinionated Calls

- **Don't ship a separate `/programs/` page for current teams.** Merge history into the team page's Arc module. The nav confusion the audit identified is a product-credibility wound.
- **The FI card is the product differentiator — ship it with real data before the Savant Card.** A world-class Savant Card is a feature. A world-class FI card is a moat. Build the moat.
- **Naming matters.** "The Room on [Team]" is the right name. "Fan Pulse" (current name) is generic. "Mood Card" (current CSS class) is fine internally. The user-facing label should be "The Room on [Team]" — it implies gossip, insider knowledge, and argument, all at once.
- **Every number needs a rival comparison.** A team's EPA/play means more when you can see it next to their three biggest rivals. The conference toggle solves some of this; the rivalry module does the rest.
- **The Rivalry module is the most shareable thing on the page.** Build it to be screenshot-worthy by default. The Fan Heat Index side-by-side thermometer is the screenshot-bait.
- **Resist adding more modules before the existing ones are world-class.** The roadmap above is long. Better to have 7 exceptional modules than 14 adequate ones.
- **The off-season is not a problem to solve — it's an opportunity.** Recruiting class builds, portal movement, spring practice — all of this is high-interest, low-coverage content. The team page should be as compelling in April as it is in October.
- **Three color ramps. No more.** Percentile / Belief / Accolade Gold. The Rivalry Thermometer is the one justified exception — OKLCH cool→warm→hot — and it gets a unique label in the design token system (`--rivalry-heat-ramp`) so it never bleeds into the percentile ramp.

---

## 18. Session log

### 2026-04-23 — This brief
Kevin asked for a comprehensive strategic brief on world-class team page design, translating and extending the player page brief. Deep read of `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`, `FAN_INTEL_SOURCE_STRATEGY.md`, `CFB_INDEX_AUDIT.md`, and `FAN_INTEL_BUILD_PLAN.md`. Produced this document covering: team page philosophy, 4-tier reading ladder, two-rail prestige system (Season Standing 9-rung + Program Prestige 7-tier), "The Room on [Team]" 5-panel FI card, 15-metric Team Savant Card, Season/Era/Dynasty Arc module with time navigator, Rivalry Module (4-zone, Fan Heat Index), Recruiting Pipeline (3-panel with pipeline gap chart), Coaching Staff Context (scheme fingerprint + staff stability), Conference Lens (toggle pattern), 7 new bespoke team-only concepts (Fanbase Health Index, Ceiling/Floor projections, Home-field advantage quantification, Program Trajectory Arc, Quiet Years Detector, Fanbase Fracture Detector, The Moment Signal), full IA top-to-bottom, competitive benchmark analysis (ESPN / CBS / 247 / Rivals / On3 / The Athletic), 7 open questions, and full P0→P3 roadmap.

### 2026-04-23 (evening) — Part II addendum
Kevin asked for deep industry research specifically targeted at the **new generation of CFB fan** — "Twitter open, group-texting while half-watching games, wants vibe + stats + community." Four parallel research streams were commissioned: (1) new-gen fan behavior (second-screen, group chat, tribal identity, gambling, TikTok, NIL-era), (2) cross-industry inspiration (Spotify Wrapped, Robinhood, Letterboxd, Strava, Discord, Twitch, BeReal, Sleeper, Genius, Duolingo + 10 more), (3) competitor audit of team pages across CFB + NBA + NFL + Premier League + La Liga, (4) long-range narrative viz patterns (climate stripes, FT, Pudding, NYT, TradingView, F1, Spotify Wrapped). Findings synthesized into §19-§28 below. This is explicitly an *extension* of Parts 1-18 — the existing IA, reading ladder, FI card, Savant card, Arc module, rivalry module, and roadmap are unchanged. The new sections add: the hero Arc viz specification (century-to-snap zoom), screenshot-native design philosophy, synchronized communal moments (Wrapped, Kickoff Check-In, Hype Meter), the tribal voice system (per-team voice at scale), Discord-inspired tab architecture as IA overlay, year-round life, program similarity engine, community annotation layer, and a cross-industry pattern catalog. Raw research dumps archived in `research/team-page-newgen-research-2026-04-23.md`.

---

# Part II — The New-Gen Fan Lens

*§19–§28. Additive extensions. Existing IA (§12) stands; new layers compose on top of it.*

---

## 19. Who This User Actually Is

Parts 1-18 described a reading ladder — 5s / 30s / 5min / deep-dive — built around a fan who sits with the page and scans top-to-bottom. That user still exists, especially the die-hard. But the dominant 2026 CFB user is a different creature and the page has to serve them too, without compromising the die-hard.

**The second-screen primary user** (Deloitte Digital Media Trends 2024: 94% of Gen Z multi-tasks while watching TV; 44% say the social conversation around a live game is *more interesting* than the broadcast):

- Has Twitter/X open, iMessage group chat active, and the game on in the background.
- Leaves the TV gaze 3-4 times per minute during non-scoring sequences (Nielsen 2023-2024).
- Gets their emotional peak in the group chat, not the living room (YPulse 2024: 41% of 13-39 sports fans say so).
- **Links die in group chats. Screenshots live forever.** A URL shared in iMessage gets one click. A screenshotted card with our branding lives there permanently and spreads.
- Discovers teams *player-first, team-second.* Arch Manning's TikTok precedes Texas fandom. Deion Sanders' personality built Colorado's 2023-24 brand independent of record.
- Cares about spread, ATS, and player props as first-class stats. 54% of 21-34 fans bet on most CFB Saturdays (AGA 2024).
- Treats NIL and portal content as continuous soap opera, peaking in January and April but never dead.
- Speaks in tribal vocabulary (RTR, Hook 'Em, WDE, Boomer Sooner, O-H/I-O) and reads a page that lacks it as "generic."

**Product implication:** the brief's reading ladder (§2) is correct but insufficient. A fan may never scroll past the hero — they arrive from a friend's shared screenshot, spend 8 seconds confirming the vibe, and leave. The hero alone has to carry the full emotional argument about the team *and* be rippable as a standalone image. Every module below the fold has to pass the same test individually.

This isn't a contradiction of the existing brief — it's a sharpening of the constraint. The 5-second zone must be *shareable*, not merely scannable.

---

## 20. The Hero Arc Viz — Specification

Part 1 described the Arc module (§6) as a Season/Era/Dynasty time-navigator that sits within the 5-minute read zone. Research on long-range narrative viz (climate stripes, Our World in Data, Pudding's Hamilton, FT annotated lines, TradingView zoom, F1 braided rankings, Spotify Wrapped) argues for a **more aggressive version of the Arc that lives at the TOP of the page** as a visual identity anchor — not buried three scrolls down.

The retained §6 Arc is the *interactive explorer.* The proposed §20 Arc-as-Hero is a *glance-readable identity strip.* They can coexist — one above the fold, one in the deeper module.

### 20.1 The layered stack

```
  ┌─────────────────────────────────────────────────────────────┐
  │  HERO STRIPE — 130 bars, one per season                     │  ← 1.5-second glance
  │  era-adjusted strength, diverging color ramp                │
  │  [Bryant red][slump blue][Saban red][current...]            │
  ├─────────────────────────────────────────────────────────────┤
  │  ERA RIBBON — 6-10 named epochs, colored bands              │  ← editorial spine
  │  [Early Years][Bryant Dynasty][Post-Bryant][Stallings]...   │
  ├─────────────────────────────────────────────────────────────┤
  │  ANNOTATED LINE — SRS/win% normalized, FT-style callouts    │  ← the shape
  │  [line with direct labels: "14 titles", "Probation 1995"]   │
  ├─────────────────────────────────────────────────────────────┤
  │  REGIME RIBBON — parallel bands: coach / OC / DC / conf     │  ← context layers
  ├─────────────────────────────────────────────────────────────┤
  │  CONTEXT STRIP — brushable full-history mini-map            │  ← navigation
  └─────────────────────────────────────────────────────────────┘
```

All five layers share an x-axis. Width: full content column. Height: ~240px on desktop, ~180px on mobile (compressed stacking).

### 20.2 Era-adjustment math (the load-bearing decision)

Without era-adjustment, 1971 Alabama doesn't compare sensibly to 2024 Alabama and the whole viz feels arbitrary. Rival fans will notice first.

**Proposed composite per season:**

```
season_strength = 0.5 × SRS_percentile_within_15yr_rolling_window
                + 0.3 × (26 - final_AP_rank, clamped to [1,25] then normalized)
                + 0.2 × (win% - expected_win%_given_SOS)
```

- 15-year rolling windows define "era" statistically (not editorially), so 1971 Bama compares to 1956-1985 CFB peers, not 2010s peers.
- AP rank contribution caps out at 25 so unranked seasons don't blow up the signal.
- SOS-adjusted win% is the residual-effort term — credit for beating what you played, not for playing no one.
- Baseline and methodology **disclosed inline** on the hero stripe and on every share card. Climate-stripes lesson: people argue about the baseline, so don't hide it.

### 20.3 Era-naming (the editorial act)

Era boundaries from pure coaching regimes produce a lazy chart (ribbon reduces to "coach timeline"). Better: eras sometimes cross coaches (Texas's "Wishbone Dynasty" spans Royal → Akers) and sometimes split within a coach's tenure (pre-sanctions vs. post-sanctions Alabama under Stallings). Target 6-10 named eras per program.

**Every era is named in the fanbase's voice.** Alabama's eras read prestigious ("The Process Era"). Vanderbilt's read scrappy ("The First Golden Window"). Washington State's read defiant ("Cougs Back"). This is where §24 (Tribal Voice System) earns its keep.

### 20.4 Zoom model

Three altitudes, one interaction set (TradingView-style scroll + pinch, altitude chips as fallback for touch/keyboard):

- **Century** (default on first visit): hero stripe dominant, one bar per season.
- **Era** (click any era band): annotated line dominant, games vs. top-25 + titles + scandals surfaced.
- **Season** (click current-season bar): F1-style braided weekly AP ranking, game-by-game EPA, opponent cards.

**URL state encodes altitude + focus.** `/teams/alabama?arc=era&era=saban` lands someone on Saban's era. `/teams/alabama?arc=season&season=2011` lands on 2011. Back button works. Share link works. **This is non-negotiable for virality** — shared deep-links are the distribution engine.

### 20.5 Graceful degradation for thin-history programs

Coastal's Arc is 25 years. Liberty is barely on the timeline. Rules:

- Programs with <25 seasons: bars render at wider spacing. No padding with fake history.
- Programs with 0 claimed titles: trophy-case concept from §16 replaced by a "Moments" module (biggest upsets authored, conference wins, bowl W's). Story, not silence.
- Bottom-tier programs get a *different tonal template* for era names and state-of-team copy — "scrappy," "rebuilding," "cult favorite." Structure identical. Emphasis different. **Vandy's page is as carefully considered as Alabama's. That is the brand.**

---

## 21. Screenshot-Native Design & Share-Card Engine

**Core principle:** every module on the page is a potential social object that has to survive being ripped out as a PNG and dropped into iMessage with zero surrounding context.

### 21.1 Card-level constraints

Every card on the page must satisfy:

- Team mark + card title + **one headline number/stat** visible in the first 60% of vertical space.
- Site wordmark + URL slug in the bottom 10%.
- Team accent gradient, not neutral chrome.
- Dark-mode default (iMessage default environment).
- Renders legible at 1080×1350 (4:5 feed) and 1080×1920 (9:16 story).

### 21.2 The share-card renderer

Python (Pillow + matplotlib) pipeline, integrated into `reporting.py` build flow. Two modes:

- **Build-time pre-render** — static cards (weekly state, season arc, prestige rail, savant card, historical modules) emitted as PNG files next to each HTML page. Near-zero marginal cost on the existing build.
- **Request-time render** — dynamic cards (this-week's custom clipping, user-highlighted stat) behind a simple `/share/<team>/<module>.png` endpoint. Optional for P2+.

Each card gets a one-tap "Share as image" button. On mobile, this triggers the native share sheet; on desktop, it copies the PNG to clipboard + downloads.

### 21.3 The Wrapped stack

Post-bowl-Monday drop: 8-card vertical stack per team, Spotify-Wrapped-styled. Content per card:

1. Biggest win (opponent + score + 1-line why it mattered)
2. Heartbreak loss
3. Breakout player
4. Ranking trajectory (mini-sparkline)
5. Rivalry result
6. Recruiting class rank change
7. Deep-cut stat (team-specific — e.g., "Your kicker was top-3 in FG% from 40+")
8. Forward-looking "next season" card

Shareable individually or as a stack. **Simultaneous drop across all 130 teams creates the communal moment.** Every fanbase gets Wrapped on the same day — synchronized ritual. Computed off existing data pipeline. Copy templates pull from §24 voice system.

### 21.4 Per-module card specs (target list)

Screenshot-worthy export for each of the following, in priority order:

1. "The Room on [Team]" FI card (§4) — the highest-virality unit.
2. Rivalry card (§7) — the Fan Heat Index thermometer side-by-side.
3. Hero Arc stripe (§20) — the identity glance.
4. Team Savant Card (§5) — the stat dump.
5. Conference Power Map (§10) — "where we sit."
6. Ceiling/Floor projection (§11.2) — the preseason screenshot.
7. Program Similarity card (§26) — "2025 Alabama is most like…"
8. Season Arc strip (§6) — "here's the season."

If a card can't be screenshotted cleanly, the design is wrong.

---

## 22. Synchronized Communal Moments

Fans show up on Saturday. Our job is to engineer rituals Wednesday-Friday too, and offseason too. The BeReal/Wrapped insight: **scarcity + simultaneity creates a communal moment.**

### 22.1 Kickoff Check-In (live ritual)

A 15-minute window at each team's kickoff. Fans tap "I'm watching" from the team page. The count is displayed live: *"28,400 Buckeye fans checked in at kickoff."* No posting, no friending — just a count that registers presence. Cookie-based, no account required.

Outcome: a fan who taps check-in is 3× more likely to return after the game (conjecture from analog behaviors in Strava / BeReal). The number itself is a stat that joins the team's season record.

### 22.2 Hype Meter (live during games)

Twitch-style velocity sidebar, rendered as a waterfall of team-colored pills scrolling up. Each pill = one aggregated reaction per minute. Readers feel the crowd without reading individual messages. During blowouts: the pills slow. During comebacks: they flood.

Aggregated from: tap-reactions on live play cards + team-scoped social volume (X + Bluesky + Reddit posts per minute from the fan intel pipeline). Rate-limited, no raw text content — just the scroll-velocity vibe.

### 22.3 Weekly Fanbase Leaderboard

Which fanbase is most active on CFB Index this week? Top fanbases get a chip on their team page header ("Most-Read Tribe Week 7"). Bottom fanbases get a cheeky prompt in the mascot voice ("The Commodore has been napping. Y'all see this schedule?").

Duolingo's lesson: low-stakes public-in-a-small-pond competition drives engagement. This is ours.

### 22.4 Wrapped Drop Day

See §21.3. Single synchronized moment across all 130 teams post-bowl Monday.

### 22.5 "Moment Happened" banner

Covered in §11.7 of Part 1. In the new-gen lens, this is the single most viral individual card the system produces. Build the share-card template for it first.

---

## 23. Tab-as-Room — Discord-Inspired IA Overlay

Part 1 (§12.4) specified a subnav with 5 anchors: `Fan Intel | Season | Savant | Rivalries | Deep Dive`. That's a **scroll-anchor model** — the page is one long vertical document.

An alternative model, informed by the Discord research, is the **tab-as-room model** — the page is a multi-room hub, not a single document:

```
┌──────────────────────────────────────────────────────────────┐
│  PERSISTENT HEADER                                           │
│  [mark] [record] [rank] [next + spread] [share]              │
├──────────────────────────────────────────────────────────────┤
│  [PULSE] [FILM] [RECRUITING] [HISTORY] [MEMES]               │
├──────────────────────────────────────────────────────────────┤
│  (active tab content, deep-linkable)                         │
└──────────────────────────────────────────────────────────────┘
```

Mapping to existing modules:

- **Pulse** → Hero + FI card + Season Pulse + Savant + Season Arc. The default. The right-now.
- **Film** → Scheme Fingerprint + Xs/Os deep-dive + Drive cards + opponent scouting + Pro view toggle.
- **Recruiting** → Pipeline module + Portal activity + coach-hire tree + retrospective conversion data.
- **History** → Era Arc + Dynasty Arc + trophy case + Legends hub + coaching lineage + "on this day."
- **Memes** → Meme wall + copypasta library + tradition explainer + rival hate ledger.

### 23.1 Decision deferred, both designs valid

Scroll-anchor model advantages: one long document feels like the rest of the site (player pages, program pages); no state to manage; predictable for power users; SEO-friendlier.

Tab-as-room advantages: fandom is multi-purpose and Discord's architecture proves rooms feel more alive than a timeline; the `#memes` channel is a *real* retention driver; offseason content fits naturally into Recruiting + History tabs without padding the Pulse tab; mobile navigation is cleaner.

**Recommendation:** prototype both on Alabama. Ship whichever tests better in a small user test. This is a decision worth 1 week of exploration, not a bet made in the brief.

---

## 24. The Tribal Voice System — Scaling Voice to 130 Programs

Part 1 established FI archetype labels and empty-state philosophy (§15.3). The new-gen lens pushes this much further: **voice must be per-team and pervasive, not just in the FI card**.

### 24.1 What varies per team

- **Accent color + gradient** — sampled from program identity, not arbitrary.
- **Mascot voice** in all fallback / transitional / empty states. The current `Awaiting Signal` copy at `reporting.py:~14830` is generic — replaced by per-team lines: *"The Tree is meditating. Signal pending."* / *"The Buckeye's still cracking. Check back."*
- **Vocabulary set** — RTR, Hook 'Em, WDE, Geaux, Boomer Sooner baked into copy templates as sign-offs, greetings, section headers.
- **Era names** — fanbase-voiced. Alabama's "Process Era" vs. a generic "Saban Era."
- **State-of-team paragraph tone** — calibrated to where this program actually sits (dynasty / rebuild / chaos / purgatory / cult-favorite / rising / haunted).
- **Which modules lead** — Alabama leads with trophy case; Rutgers leads with schedule; Coastal leads with upsets-authored; Vandy leads with academic pride + "any given Saturday."

### 24.2 What stays identical

- Information architecture (same modules, same order within their tab).
- Viz grammar (Arc, Savant, Rivalry card — all structurally identical).
- Data honesty — era-adjustment methodology disclosed identically.
- Component vocabulary.

### 24.3 How to scale it

Voice lives in a new `team_voice` table:

```sql
team_voice(
  team_id,
  accent_hex,
  gradient_hex_pair,
  vocab_dict_json,           -- {"signoff": "Roll Tide", "greeting": "RTR", ...}
  mascot_voice_templates_json, -- {"awaiting_signal": "The Elephant is ...", ...}
  era_name_overrides_json,   -- {"1958-1982": "The Bryant Dynasty", ...}
  tonal_template             -- enum: dynasty / rebuild / cult / rising / haunted / ...
)
```

Seeded editorially for top-30 programs via LLM-with-human-review pass. Long-tail programs use `tonal_template` defaults with community-contributable overrides (P3). **Templates in `reporting.py` pull from this; no hand-authored per-week copy.** The system generates the voice.

### 24.4 The failure mode to avoid

Generic-template voice is worse than no voice. A Vanderbilt fan reading Alabama-flavored prose on their page is a trust-killer. The first 30 programs get hand-reviewed and tuned before any of the long tail ships. Better to have no voice on Liberty than the wrong voice.

---

## 25. Year-Round Life — Killing the January-to-August Dead Zone

Arsenal.com is never dead. Ohio State's ESPN page in June is a ghost town. This is a content-strategy failure shared by every CFB competitor — **the single biggest opportunity window in this entire brief.**

### 25.1 Seasonal content rotations

**April-June (Spring & portal):**
- Portal tracker dominates Pulse tab.
- "Spring game in one chart" card.
- Position battle explainer copy.
- NIL valuation deltas.

**June-July (Dead period):**
- "On this day" module rotates to featured position.
- Heritage deep-dives as rotating featured content ("The 1971 Nebraska team: revisiting the GOAT").
- Program similarity feature (§26).
- Legends hub gets daily spotlight cards.

**July-August (Camp):**
- Position-group preview cards.
- SP+ preseason projection as hero card.
- Schedule strength viz.
- Ceiling/Floor projections (§11.2) go live.

### 25.2 The principle

The system *generates* this content from existing data + editorial templates. The infrastructure is the product. A fan who checks their team page in June gets something *worth* checking. Over time, this habit compounds — returning in June means returning in August means returning every Saturday.

### 25.3 "On this day" module

Daily-rotated historical artifact surfaced on every team page. Sources: `honors.py`, `team_annotations` (new table, §20), game archives. Displayed in the mascot voice. *"On this day in 1979, Bear Bryant coached his 315th win, becoming college football's winningest coach. The Elephant remembers."*

Zero maintenance after the data is seeded. High emotional resonance. This is the kind of module that gets screenshotted and texted to a dad-group-chat.

---

## 26. Program Similarity Engine

"2025 Alabama is most similar to 2014 Florida State and 2017 Clemson."

Basketball Reference does this for players. **No CFB site does it for teams.**

### 26.1 Implementation

Cosine similarity on a per-season feature vector:

```
features = [
  SRS_percentile, PPG, PA/G, SOS_percentile, turnover_margin,
  returning_production_pct, recruiting_rank_prior_year,
  coach_tenure_year, conference_id_one_hot...
]
```

Compute nightly via a new CLI subcommand: `python manage.py compute-similarities`. Materialize a top-10-nearest-neighbors table per season-team. Query at build time.

### 26.2 Rendering

A compact card in the Pulse tab and in the History tab (different framings):

- Pulse framing: "This year's team is most like these past teams" — 3 cards with year, team, final record, one-line outcome.
- History framing: "This *era* is most like these past eras" — analogous but aggregated to era-level vectors.

Screenshot-worthy. Argument-fuel.

### 26.3 Why it works

It's a story-generator. Every fan's first question is "what does this team remind us of?" — and every answer is a thread: *"2025 Alabama is most similar to 2017 Clemson. 2017 Clemson lost to Alabama in the Sugar Bowl. What does that say about how this season ends?"* The page literally produces subjects for podcasts and group chats.

### 26.4 Honest caveats

- Similarity ≠ destiny. Disclose that the model finds statistical comps, not fate.
- Small-sample programs return noisy nearest-neighbors. Display confidence indicator.
- Methodology published. Rival fans will litigate.

---

## 27. Community Annotation Layer (Genius-Style)

Part 1 covered fan-intelligence *measurement* — the system listens. This section adds fan-intelligence *contribution* — the system lets fans speak.

### 27.1 What's annotatable

- **Any player name** on the roster or legends hub → fans add context (recruiting rating, transfer saga, hometown connection, backstory).
- **Any key play** on a game recap → fans annotate scheme, personnel, in-joke.
- **Any era** on the Arc → fans add a one-paragraph memoir of what that era felt like.

### 27.2 Moderation model

Three-tier:

1. **Read path (all users):** annotations display with contributor handle + date + upvotes.
2. **Submit path (signed-in users, P2+):** submissions enter a mod queue.
3. **Curation path (small trusted group):** approve, edit, merge, remove.

The Genius lesson: quality rises with volume + structured moderation. Don't ship this without moderation infrastructure.

### 27.3 The soft launch

Pre-account: seed with editorial annotations on the top-20 programs. Each annotation credited to "CFB Index Staff" or an invited beat writer. This establishes the visual vocabulary before any user-contributed content lands.

### 27.4 Why it matters

Annotation turns the page from a document into a *living archive.* It also turns readers into contributors — the Wikipedia effect — which is how you get 17k pages to feel curated when you have a small team.

---

## 28. Cross-Industry Pattern Catalog (Appendix)

The research surfaced 20 products. Ranked by transferability to a CFB team page:

| # | Product | Core mechanic | Team-page translation |
|---|---------|---------------|------------------------|
| 1 | Spotify Wrapped | Personal narrative from consumption data in vertical cards | Season Wrapped drop (§21.3) |
| 2 | Letterboxd | Taste-as-identity, friend-activity feed, half-star ratings | "This week's takes" rail; fans' Top 4 all-time players |
| 3 | Discord | Channels-as-architecture, role badges, persistent history | Tab-as-room IA (§23); role badges on comments |
| 4 | Strava | Segment leaderboards; kudos; runs as social objects | Every drive as a social object; segment leaderboards ("Most lopsided 4th Q of season") |
| 5 | Sleeper | League chat built into the product; recap bot persona | Rivalry chat rooms; recap-bot post after every game |
| 6 | Genius | Crowd-sourced annotations on primary content | Community annotation layer (§27) |
| 7 | BeReal | Scarcity + simultaneity = communal moment | Kickoff Check-In (§22.1) |
| 8 | Twitch live chat | Velocity + emotes as tribal language | Hype Meter (§22.2); per-team reactions/emotes |
| 9 | Robinhood / Public | Sentiment bar + "why is it moving" chip strip | Sentiment bar on team header; movement-explanation chips |
| 10 | Duolingo | Streaks, weekly leagues, mascot voice | Fan streaks; weekly fanbase leaderboard (§22.3); mascot voice (§24) |
| 11 | Stats Perform / Opta | Spatial + temporal momentum maps | Season momentum map |
| 12 | RateYourMusic / Pitchfork | Critic score vs. user score delta | Model rank vs. Fan rank delta as header stat |
| 13 | TikTok LIVE / Twitch IRL | Ambient viewing during downtime | Bye-week "ambient mode" with historical highlights |
| 14 | r/place / Twitch Plays Pokemon | Collective action with shared canvas | Annual "build the all-time team" collective vote |
| 15 | NBA Top Shot | Moments as timestamped artifacts | "Moment cards" for key plays, screenshot-native |
| 16 | Steam game pages | Tenure-gated reviews, "also follow" rail | Fan reviews gated by tenure; "Fans of this team also follow" rail |
| 17 | Goodreads | Year-in-review, shelves as identity | Fan shelves: "Teams I follow," "Rivals I loathe," "Dark horses" |
| 18 | Pokémon GO | Geotagged team claims | Stadium pages show "which fanbase claimed most check-ins here" |
| 19 | Glassdoor / Levels.fyi | Anonymous structured prompts + moderation | Anonymous coach ratings, gameday-experience scores |
| 20 | Bloomberg / TradingView | Dense data + social layer in same view | "Pro view" toggle; fan-published annotated charts |

### 28.1 The meta-patterns to make bets on

Three translatable mechanics recur across the top 10:

1. **Primary content becomes a social object.** Every drive, every game, every player needs a comment count, a reaction, and a share surface — not just the top-level team.
2. **Synchronized communal moments.** Engineer rituals Wed-Fri and offseason too, not just Saturday. Wrapped day, Kickoff Check-In, weekly leaderboard, Moment Happened.
3. **Identity scaffolding.** Let fans declare who they are beyond "root for Team X" — tenure, rival, all-time favorite, gameday habit. Identity surfaces are permanent page decorations.

---

## 29. Revised Open Questions (supplementing §14)

Adding to the seven open questions in Part 1:

**8. Scroll-anchor model (§12.4) vs. Tab-as-room model (§23) — which ships?** The research argues tab-as-room feels more alive but costs more to build and changes how the existing player/program pages relate to team pages. Worth a 1-week prototype.

**9. What's the moderation plan for the community annotation layer (§27)?** Shipping the read path is easy. Shipping the write path without moderation is reckless. Timeline decision: ship read-only with editorial seed content in P2, add write path in P3 once moderation tooling exists.

**10. Wrapped drop mechanics — synchronized across all 130 teams, or staggered by conference?** Recommend synchronized. The communal moment is the product.

**11. Program similarity — what's the minimum "era" for the era-level similarity vector to feel trustworthy?** Too short (<3 seasons) and it's noisy. Too long (>10) and it flattens distinct stretches. Propose 5-season rolling windows with explicit confidence display.

**12. Does the Share-Card engine live in `reporting.py` or a new module?** Cleaner to make it `src/cfb_rankings/share_cards/` with its own submodules per card type. Keeps `reporting.py` (already 17.5k lines per `CLAUDE.md`) from growing further.

---

## 30. Revised Roadmap Integration

Parts 1-18 specified P0-P3. The new-gen lens slots in as follows:

**P0 additions (immediate, 1-2 weeks):**
- Retire "Awaiting Signal" → per-team mascot voice fallback (§24.1). Requires `team_voice` table + seed data for top-20 programs.
- Era-adjustment methodology decision (§20.2) — specify, document, publish.

**P1 additions (core, 2-4 weeks):**
- Hero Arc stripe component (§20) — the 130-bar visual identity strip above the fold. Ships before the full zoomable Arc (§6) for time-to-value.
- Share-card renderer, build-time pre-render path (§21.2) — applied to FI card + Rivalry card first.
- Kickoff Check-In counter (§22.1) — lightweight cookie-based presence, no account required.

**P2 additions (differentiator, 4-8 weeks):**
- Full zoomable Arc (hero → era → season) with URL state (§20.4).
- Tab-as-room IA prototype (§23) on Alabama; ship site-wide if it wins the test.
- Tribal Voice System seeding for top-30 programs (§24.3).
- Program Similarity Engine (§26).
- Wrapped card stack generator (§21.3).

**P3 additions (polish + new primitives):**
- Community annotation layer (§27) — read path with editorial seeds first, write path behind moderation.
- Hype Meter live (§22.2).
- Weekly Fanbase Leaderboard (§22.3).
- "On this day" module (§25.3).
- Full year-round content rotations (§25.1).
- Long-tail program voice-seeding (§24 continued).

---

## 31. The One-Line Summary

**Every team page is a group chat waiting to happen. Design every card like someone is about to screenshot it. Design every season like Spotify Wrapped is already scheduled. Design every voice like the fanbase wrote it themselves. Do all that, and the page stops being a page — it becomes the tribe's home.**

---

# Part III — Post-iteration integration

**Status of this part:** Written 2026-04-24 after ~16 mockup iterations and ~12 Kevin-directed conceptual refinements. Parts I–II remain in force; Part III layers, sharpens, and in some places supersedes earlier specifications. Where Part III and earlier parts conflict, Part III is current.

**Reference companion:** `TEAM_PAGE_ITERATION_LOG.md` (chronological record of iterations, decisions, and Kevin's directional inputs).

---

## 32. Seasonal Sentience — temporal ebb-flow

The page is alive because it knows *what moment it is* and shifts emphasis accordingly. Two nested clocks govern:

**Annual clock (offseason → season → postseason):**
- January · bowl / coaching carousel / Wrapped drop
- February · NSD / portal window 1 closing
- March · spring practice begins
- April · spring game / draft anticipation
- May–June · dead period / heritage-forward
- July · SEC Media Days / magazine picks / camp preview
- August · camp / depth chart / preseason projections go live
- September · early season / identity-search
- October · stakes rising / bowl math emerges
- November · rivalry peak / CFP math intensifies
- December · CFP selection / bowl season

**Weekly clock (in-season, Sun → Sat):**
- Sunday · post-game autopsy
- Monday · licking wounds or basking (outcome-conditional)
- Tuesday · depth chart + injuries, reality sets in
- Wednesday · opponent pivot begins
- Thursday · matchup sharpens; hype builds
- Friday · anticipation peak; "this week" is the loudest thing
- Saturday · gameday (pre-game → live → post-game)

### 32.1 Implementation — two signals → one template variant

The daily build resolves a `state` object from two inputs:

- **Date signal:** offseason month / in-season day-of-week / postseason week
- **Context signal:** last game outcome (none / win / loss / close-loss / blowout-win / blowout-loss / upset-win / upset-loss), CFP status, rivalry-week flag

Resolves to *one of ~10 named anchor variants* (each editorially reviewed for voice quality), with contextual parameter overrides producing emergent states as needed. The real expressive range: roughly 25-30 meaningfully distinct configurations from the same components.

### 32.2 Named anchor variants

1. `standard-midweek` — Tue–Thu baseline in-season
2. `standard-friday` — anticipation building
3. `rivalry-week-friday` — amplified anticipation
4. `gameday-pre-kickoff` — Saturday morning
5. `post-win-sunday-monday` — basking + validating
6. `post-loss-sunday-monday` — reckoning + processing
7. `post-upset-win` — explosive; Chronicle dominates
8. `post-close-loss` — honest, what-if register
9. `selection-sunday` — projected-in / bubble / out (three sub-variants)
10. `dead-period-summer` — heritage-forward
11. `camp-open` — August optimism-building
12. `portal-window-active` — December + April

### 32.3 Three parameters every variant provides

- **Hero-priority rule** (which module claims the top slot): Pulse / Rivalry / Heritage / CFP Projection / Chronicle / Schedule-next / On-This-Day / Portal-Tracker — ~8 options
- **Copy tone** (which voice-template the state-of-team paragraph uses): wound / coiled / basking / patient / reckoning / euphoric / anxious / held-breath / optimistic / resolute — ~10 options
- **Accent color** (the emotional key): red / amber / navy / gray / coral / green — 6 options

~480 theoretical combinations; in practice ~25-30 meaningful states. Stored in `team_page_anchors.json`; resolver in `src/cfb_rankings/team_pages/state_resolver.py`.

---

## 33. Program-Tier Sentience — every program, its own terms

The single most important macro principle. Every module reshapes for the program it's rendering. A UMass page that foregrounds CFP odds insults the fanbase. A Vanderbilt page that renders like Alabama's fails every fan. The design system handles this through program profiles (§34) that drive module selection, metric framing, voice register, and aspiration scale.

### 33.1 Ten-tier taxonomy

1. Blue bloods (Alabama, Ohio State, Georgia, Texas, Michigan, Notre Dame, Oregon)
2. Established P4 (Oklahoma, LSU, USC, Penn State, Florida, Auburn)
3. Rising P4 (Indiana, SMU, Kansas, Missouri recently)
4. Mid P4 (most SEC/B1G/ACC/Big 12)
5. Lower P4 (Vanderbilt, Purdue, Rutgers, NW)
6. Top G5 / independents (Boise, Memphis, Liberty, UNLV, Tulane, ND pre-CFP)
7. Solid G5 (JMU, App State, Coastal, Louisiana, Toledo, Army, Navy)
8. Middle G5 (most MAC, most Sun Belt mid-tier)
9. Low G5 (UMass, Kent State, New Mexico State)
10. FCS (not in v1 scope)

### 33.2 What adapts per module

| Module | Contender (T1-T2) | Mid (T3-T5) | Non-contender (T6-T10) |
|---|---|---|---|
| Metric tiles | AP · SP+ · CFP odds · record | SP+ · record · bowl odds · conf rank | Record · SP+ · bowl odds · mood |
| Aspiration ladder | Semifinal → champion | 8 wins → conf title → CFP buzz | 6 wins → exceed last year → statement year |
| State-of-team register | Dynastic · expectant | Proving · grinding | Scrappy · proud · incremental |
| Chronicle tuning | Era-relative peaks | Program-relative progress | Program-historic progress |
| Top-25 opponent framing | Expected weekly | Occasional highlight | Rare, amplified |
| CFP math | Always | Conditional | Hidden unless unlocked |
| Rivalry weight | High | Very high | Highest (season's biggest stakes) |
| Heritage strip | Titles · Heismans · legendary coaches | Conference titles · notable alums | Founding year · FBS-era milestones |

### 33.3 Dynamic unlock conditions (override baseline tier)

- `wins >= 1.5 × baseline OR sp+_rank <= (tier_expected - 20)` → unlock higher-aspiration modules
- `wins <= 0.5 × baseline OR sp+_rank >= (tier_expected + 20)` → hide aspirational modules; rebuilding-frame copy
- Rivalry week always overrides weight regardless of tier
- Heritage anniversary unlocks heritage-promoted layout for a week

### 33.4 The aspiration ladder as new core module

Every team page gets an aspiration ladder. 3-5 rungs. Each rung: outcome name, realistic odds, one-sentence program-historic context. Rungs that are meaningfully out of reach render dimmed with "locked" annotation — dreams acknowledged, not promised. Unlocking happens dynamically as performance warrants.

Example (UMass 2026 at 3-2): *6 wins · first bowl since '18 · 31%* / *7 wins · doubles last year · 12%* / *8 wins · statement year · 3% · locked* / *9+ wins · never happened · 0.4% · locked*.

Example (Alabama 2026 baseline): *CFP appearance · 96%* / *CFP semifinal · 64%* / *Title game · 28%* / *National champion · 14%*.

Same module, completely different content, identical design system.

---

## 34. Program Profiles — editorial infrastructure

Each program has a hand-curated profile document in `profiles/<slug>.md`. The profile is not metadata *about* the program — it is the editorial infrastructure that drives every rendering decision. Edit a field → the rendered output updates everywhere that field reaches.

### 34.1 Profile structure (~45-50 fields per program)

**YAML frontmatter (structured data):**
- Identity: `team_id`, `program_name`, `display_name`, `program_slug`, `program_tier`
- Voice: `voice_register`, `tonal_template`, `identity_phrase`, `mantra`, `authored_by`, `editorial_review_status`
- Colors: `accent_hex`, `accent_hex_secondary`, `gradient_hex_pair`
- Vocab: `signoff`, `greeting`, `hashtags`, `selfname`, `stadium_short`
- Mascot voice: `awaiting_signal`, `empty_state`, `post_win`, `post_loss`
- Era name overrides: year-range → editorial era name
- Never use: list of prohibited copy frames (guardrail)
- Always surface: list of facts the page must feature
- Stock phrases: array of verbatim-use phrases
- Rivalries: tiered list with trophies, names, accent colors, notes
- Aspiration ladder: rungs with unlock conditions and context
- Heritage: structured facts (founded, titles, Heismans, stadium, etc.)

**Markdown body (editorial prose):**
- Identity and heritage
- Coaching lineage
- Notable players
- Fans and culture
- Voice and ethos (the most load-bearing section)
- Rivalries (narrative)
- Current context
- Program narratives (ongoing storylines)
- Aspiration framework (narrative)
- Chronicle tuning
- In-jokes and copypasta
- Taboos and sensitivities

### 34.2 Voice and ethos — the ~70% load-bearing section

Five fields do most of the work:
- `identity_phrase` — opens every state-of-team template
- `mantra` — signs off state-of-team paragraphs
- `stock_phrases` — verbatim in specific moments
- `never_use` — guardrails on LLM generation
- `always_surface` — positive-space emphasis

If these five fields are correct, the rest of the profile can be 80% right and the product still reads as bespoke. If these are wrong, no amount of good data saves the page.

### 34.3 Profiles in progress

- Alabama (tier 1 · dynastic-process) — by opus-editorial, draft
- Notre Dame (tier 1 · dynastic-with-question-mark) — by opus-editorial, draft
- Ohio State (tier 1 · dynastic-industrial) — by opus-editorial, draft
- Georgia (tier 1 · dominant-hungry) — by opus-editorial, draft
- Michigan (tier 1 · proud-institutional) — by opus-editorial, draft
- Texas (tier 1 · confident-texan) — by opus-editorial, draft
- USC (tier 1 · hollywood-dynastic) — by opus-editorial, draft
- Oregon (tier 2 · innovative-fashion-forward) — by opus-editorial, draft
- Penn State (tier 2 · blue-collar-dynastic) — by opus-editorial, draft
- Vanderbilt (tier 5 · defiant-academic) — by sonnet-editorial, draft
- UMass (tier 9 · scrappy-proud) — by sonnet-editorial, draft

### 34.4 Scaling to 130 programs

~4 hours of Claude-assisted research + ~30 min of human editorial review × 130 programs = ~600 hours total — roughly a 2-week dedicated sprint. Revisited every 2-3 years when programs fundamentally reposition.

Production: Claude Code in headless mode iterates through tier lists, drafting profiles from CFBD data + structured web research + the Vanderbilt template. Editorial review phase focused on voice & ethos section (the ~70% load-bearing fields). Long-tail programs use tonal defaults with minimal custom phrasing.

---

## 35. Game Recap Mode — the Saturday-night apex

The highest-stakes design moment in a fan's week. The 18-24 hours after a game ends. Fans are raw, processing, looking for calibration. The page has to deliver honesty without wailing, data without panic, path-forward without false hope.

### 35.1 Module stack (post-loss variant specifically)

1. **Header** — red pulsing dot, visible rank-drop, "final 2h 23m ago"
2. **State-of-team paragraph** in post-loss voice ("the version of it you wanted is not")
3. **Game-shape WP chart** with 3 annotated inflection points (peak / pivot / sealed)
4. **4-stat diagnosis row** — LLM-ranked from ~30 candidates by divergence from season baselines
5. **Pulse live-loss mode** — real-time mood crash with event-timestamped "what moved it" log
6. **Chronicle game edition** — 3 observations (anomaly + echo + retroactive) generated T+25-35 min after final
7. **CFP math revised** — pre-game vs. post-game percentages, "if win out" scenario, calibrated paragraph
8. **Footer** — next-update schedule, demoting schedule to one line

### 35.2 LLM workload sequence

- T+5 (final ingest): trigger
- T+15: state-of-team paragraph (voice template + game facts)
- T+20: 4-stat diagnosis row (divergence ranking)
- T+25: Chronicle anomaly + retroactive cards
- T+30: Chronicle echo card (pattern streak detection)
- T+35: CFP math paragraph (forecast delta + calibrated language)
- T+40: "what moved it" summary
- Page republishes by T+45

All via Claude Code + Max subscription. Parallel across ~65 programs on a Saturday. Budget: trivial at Max rates.

### 35.3 Mode-specific demotions

What disappears in game recap mode: rivalry card (that rivalry happened), full schedule strip (reduced to one-line footer), Arc (not this moment), era view (not this moment), program-context elements. The page knows this moment is *about what just happened*, not *where the program sits*.

---

## 36. The Chronicle — module spec (expanded from §23 Part II)

Weekly editorial intelligence module. LLM sweeps data and surfaces 3-5 observations per team per week. Each observation gets a card with distinct register per type. Six card types defined:

1. **Anomaly** (amber accent) — statistical outlier vs. historical distribution
2. **Moment** (coral accent) — cultural/social velocity signal
3. **Flashpoint** (navy accent) — next-opponent matchup intelligence
4. **Echo** (gray accent) — cross-era similarity or parallel
5. **Retroactive** (purple accent) — recontextualization of an earlier game/moment
6. **Player arc** (teal accent) — individual trajectory within a cohort comparison

### 36.1 Generation pattern

- Haiku preprocessing: scan ~1,000–5,000 candidate anomalies per team per week with oddity scores
- Sonnet ranking + writing: pick top-5, generate editorial prose, attribute sources
- Opus (rare): anchor-week curation (season opener, rivalry week, bowl games)

Ratio: ~1% of candidates ship. The LLM's real job is ranking by reader-surprise, not generating.

### 36.2 Three altitudes, same module

- **Weekly Chronicle** — this week's observations (in-season module)
- **Seasonal Chronicle** — the 10 discoveries that defined a season (inside historical season deep-dive)
- **Era Chronicle** — the 20 observations that characterize an era (inside CFP-era view)

Same architecture, different time windows.

### 36.3 Source attribution — non-negotiable

Every Chronicle card ends with a source line (CFBD tier 2 · SP+ · FI pipeline · cross-era cosine similarity · etc.). This is what separates editorial observation from generated slop — the reader sees the receipt.

---

## 37. Claude Code + Max Subscription — content generation architecture

### 37.1 Architectural decision

All build-time LLM content generation runs through Claude Code in headless mode, invoked via subprocess from Python scripts. Token usage counts against Kevin's Claude Max subscription rather than API billing.

### 37.2 Model routing rules

**Opus** — high-judgment architecture and editorial moments:
- New SQLite schema design
- Blue-blood program profile drafts (voice subtlety matters most)
- Anchor variant specifications for seasonal sentience
- Complex design architecture decisions
- Top-20-program editorial review

**Sonnet** — implementation workhorse:
- All HTML/CSS/Python code
- Standard program profile drafts (tier 2-6)
- Weekly state-of-team paragraph generation
- Chronicle observation ranking + writing
- Test writing, refactoring

**Haiku** — bulk and fast operations:
- Grep sweeps / file structure scans
- Bulk profile drafts for tier 7-10 (human review catches tone)
- Stat anomaly candidate generation (preprocessing before Sonnet ranking)
- One-line meeting annotations for historical season deep-dives (~17k units)
- Simple data transformations

### 37.3 Ratio: Haiku finds → Sonnet writes → Opus curates

General pattern. Haiku produces thousands of candidates; Sonnet picks and writes the top-K; Opus reviews the anchor moments that matter most. Minimizes cost while maintaining editorial quality where it counts.

### 37.4 Pattern for subcommands

- `python manage.py generate-narratives` — state-of-team + season units; Sonnet
- `python manage.py generate-chronicle` — weekly Chronicle observations; Haiku → Sonnet
- `python manage.py generate-profiles` — new program profile drafts; Opus for T1-2, Sonnet for T3-10
- `python manage.py refresh-moods` — weekly mood scores from FI pipeline; Python-native (no LLM)
- `python manage.py recap-game` — post-game recap mode generation; Sonnet

Each subcommand caches to SQLite; idempotent on re-run; logs token usage per invocation.

### 37.5 Caveats

- Max subscription fair-use limits — spread initial bulk across several days
- Claude Code headless is slower per call than direct API (seconds of setup overhead)
- Model selection constrained to what Max provides (Sonnet default, Opus for harder tasks)
- Fallback to direct Anthropic API for large-volume operations if Max throttles

---

## 38. Figma component inventory

All components built in `CFB Index — Team Page Design System` Figma file. Kevin has file access via his Figma team. Built as Cover-page sibling frames due to MCP persistence quirk; will be reorganized into proper pages during Kevin's Figma sessions.

### 38.1 Design tokens (30–40 definitions)

- Color: 6 ramps × 7 stops = 42 swatches (navy, coral, amber, gray, green, red)
- Typography: 9 sizes (Display serif → Micro sans)
- Spacing: 9 tokens (sp-1 / 4px → sp-24 / 96px)
- Radii: 5 tokens (radius-sm / 3px → radius-full / pill)
- Stroke: 3 weights (hair 0.5px / std 1px / heavy 2px)

All export to `tokens.css` as CSS custom properties at build time.

### 38.2 Atomic components (~10)

- MetricTile (variants: standard · with-delta · with-sparkline)
- BadgeChip (variants: default · characterization · sentiment)
- Eyebrow (small-caps labels)
- PullQuote (serif italic with attribution)
- DividerRule
- AspirationRung
- EventLogItem
- PercentileBar (Savant card unit)
- StatPill
- LiveDot (animated on implementation; static in Figma)

### 38.3 Module components (~22)

- TeamIdentityHeader (desktop + mobile variants)
- HeritageStrip
- StateOfTeamParagraph
- ScheduleStrip (horizontal-scroll mobile · desktop grid)
- MoodSparkline
- ThisWeekCallout
- ArcHeroStripe (131-season variant · 13-brick CFP-era variant)
- EraRibbon
- SeasonBrickIndex
- TrajectoryChart (two-line hero · context variant)
- PulseModule (composite)
- RivalryCard (composite, desktop + mobile)
- ChronicleCard (6 type variants)
- SavantCard
- AspirationLadder
- SeasonDeepDive (composite for historical season)
- CFPEraView (composite for era-level)
- GameRecapHero (composite for post-game mode)

### 38.4 Page templates (2)

- TeamPageDesktop (composition of all modules)
- TeamPageMobile (same composition, mobile variants)

### 38.5 Variant dimensions per component

Each module has three variant dimensions:
- **Viewport**: desktop / mobile
- **Priority**: hero / scroll / hidden
- **Context**: default / post-win / post-loss / rivalry-week / offseason

Not all modules have all context variants; most have 1-2.

---

## 39. Brand position

**"CFB Index is the only site in college football that renders every team's page with equal editorial care at that team's own level of stakes."**

Competitors that specifically fail at this:
- Sports-Reference — identical template for every program; UMass page visibly lower-effort than Alabama's
- ESPN — UMass page essentially a stub
- The Athletic — doesn't cover UMass at all
- 247/On3 — recruiting-focused; non-P4 as footnote
- Team official sites — merch funnels, not journalism

This position becomes defensible — *not* just marketable — through the program profile system (§34). A reader visiting UMass and Alabama pages sees that both were researched. Competitors can't match this without rebuilding their editorial product from scratch.

---

## 40. Revised operational roadmap

### Phase A — Foundation (weeks 1-2)

- `manage.py generate-narratives` subcommand via Claude Code + Max
- SQLite schema: `team_profiles`, `team_season_narratives`, `team_chronicle_observations`, `team_voice`
- New module: `src/cfb_rankings/team_pages/` (separate from `reporting.py`)
- First 10 program profiles (top-10 tier-1 programs) hand-reviewed
- Hero section HTML template rendering from profile + current-season data
- Mobile breakpoint + desktop breakpoint

### Phase B — Core modules (weeks 3-5)

- Current-season theater view (schedule strip, mood spark, state-of-team, this-week)
- Pulse module (live fan-intel)
- Aspiration ladder module
- Season archive + historical season deep-dive template
- Chronicle module (read path; 4 card types at minimum)

### Phase C — Advanced modules (weeks 6-8)

- Rivalry card with dual-trajectory + editorial meetings
- CFP-era multi-metric view
- Savant card
- Game recap mode templates (post-win + post-loss)
- Seasonal sentience resolver (anchor variants)

### Phase D — Profile library completion (parallel, weeks 2-6)

- Tier 1-2 profiles (~20 programs) by end of week 3 (Opus review)
- Tier 3-5 profiles (~50 programs) by end of week 5 (Sonnet draft + light review)
- Tier 6-10 profiles (~60 programs) by end of week 6 (Sonnet/Haiku batch + spot review)

### Phase E — Rollout (weeks 7-10)

- Ship ND team page first (end-to-end reference)
- Expand to top-20 programs
- Long-tail rollout; seasonal sentience production-tested through a full fall

### Phase F — Community + offseason (ongoing)

- Annotation layer (read path with editorial seeds first)
- Year-round content rotations (offseason content)
- Wrapped stack generator (post-bowl-Monday)
- Share-card renderer

---

## 41. Part III summary

Five macro principles now govern the team-page design:

1. **Program-tier sentience.** Every module reshapes per program. CFP odds don't render on UMass pages. Aspiration ladders replace generic CFP framing. Voice register adapts to the program's realistic ceiling.

2. **Seasonal sentience.** The page knows what moment it is and shifts emphasis by day-of-week and season-phase. ~10 named anchors + parameter overrides = ~25-30 meaningful states.

3. **Deep program profiles.** 45-50-field editorial documents per program that drive every rendering decision. The profile IS the editorial infrastructure; edits cascade everywhere.

4. **Chronicle module.** LLM-powered editorial intelligence at three altitudes (weekly, seasonal, era). 6 card types. Haiku-Sonnet-Opus routing. Source-attributed, screenshot-native.

5. **Claude Code + Max content pipeline.** All build-time LLM generation through Max subscription. Model routing optimizes cost and quality. Cached to SQLite. Idempotent subcommands.

Operational work from here is production, not concept. Build the Figma library, write the profiles, translate to HTML/CSS via Claude Code, ship to Notre Dame first, fan out by tier.

---

**End of Part III.**
