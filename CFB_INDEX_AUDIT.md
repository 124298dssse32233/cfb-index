# CFB Index — Full Site Audit

_Done against the local build at `output/site/` on 2026-04-22 (Model Week 21, power-resume-v0.1.0). I audited the homepage, rankings, Heisman board, 6 player pages (Mendoza, Love, Brown, Curry, Manning, Smith), 6 team pages (Indiana, Alabama, Ohio State, James Madison, Montana State, Notre Dame), matchups, compare, conferences, archive, history, about-model, and programs pages — 35+ pages total — plus the site's smoke screenshots. The Chrome extension can't drive `file://` URLs, so I did this as a structural / copy / data audit with the rendered screenshots as visual reference. That actually catches a category of bugs a browser walkthrough can't (unrendered template leaks, copy contradictions, IA mismatches)._

---

## 1. Top-line verdict

**Is this compelling yet? Partially.** The editorial voice is already unusually strong for CFB — headlines like "Settle the argument without opening ten tabs", "The archive should argue back", "Built for argument, not dashboards", "Which Fanbase Is Calmer / What Fans Are Afraid Of / Rival Timelines On Fire" — this is writing no mainstream CFB site has. The structural ambition (one football universe from FBS to D-III, power vs. resume separated, a fan-intelligence layer layered on top of a real model) is also genuinely distinctive. The About-Model page is the strongest single surface: serious, honest, name-checks SP+/FEI/Massey/Colley in the right way.

**What's world-class already.**

- The editorial copy voice across hero sections, compare/matchups taglines, and the About-Model explanation. This reads like The Athletic if it had an analytics department, not like ESPN or On3.
- The Power-vs-Resume separation and how it's framed. That conceptual clarity is rare and it's the site's biggest analytical moat.
- The player page skeleton. Eleven sections, position-adaptive headers ("Why this is a two-channel quarterback case" / "Why this is more than a rushing profile" / "Why this is a rare defensive case"), traditional stats first with percentiles inline (`#14/367 (96th pct)`), advanced metrics below — the information architecture is better than Sports Reference and more editorial than ESPN.
- The fact that the Heisman board includes a "Best non-QB / Best G5 case / Best defensive case" fast-read panel. That's the kind of detail that shows the product thinks about the sport.
- The Matchups page ambition: Market vs Model vs Mood as three side-by-side lenses is a genuinely original framing that mainstream sites don't attempt.

**What most holds it back.**

1. **The entire Fan Intelligence layer is empty across every team page** — Fan Pulse, Reality Check, Respect Gap, Swing Meter, Cohesion, Rival Heat, Top Storylines — all showing "Awaiting Signal" on Indiana, Alabama, Ohio State, James Madison, Montana State, Notre Dame. Six teams, six pages, zero populated mood data. The homepage's signature "Mood Board" section is also empty with the honest-but-product-ruinous eyebrow "The Mood Board, Warming Up." The site's signature differentiator currently shows as a blank promise on every surface.
2. **The homepage is a 5.2MB single file that inlines all 667 team snapshots into the Smart Board.** That is not a homepage — that is the full rankings page pasted into the homepage. A real fan who hits this on mobile is going to wait forever and scroll through hundreds of teams to find anything else.
3. **The Heisman page is a 14.7MB HTML file with 15,363 unique player links.** That's most of D-I/D-II/D-III pushed into one DOM. It will be close to unusable on mid-tier hardware.
4. **The product says "premium" and then shows `power-resume-v0.1.0` and "72 NCAA-eligible team records" on the homepage** — both trust-eroding because the site has 667 team pages and an 8-year archive. The version string is honest but reads as beta; the 72-teams stat directly contradicts the Smart Board.
5. **There are two parallel team-page systems** (`/teams/<slug>.html` current-season with Mood Card, and `/programs/<slug>.html` historical arc) and **the primary nav only links to Programs** — so a new user has no one-click path from the top of the site to a current team page. They can only get there through rankings or the Smart Board.
6. **The Heisman page has "Pac-12" as a live conference filter.** In 2025 that's effectively Oregon State + Washington State, and those two appear in the rankings conference list as "Pac-12" too — so the filter is real but cosmetic. It's a data-era footgun and fans will notice.
7. **"Offensive Reminiscence" and "Defensive Reminiscence" as repeated section names across 297 team cards.** "Reminiscence" is the wrong word for what looks like a historical-comp module. It reads as either a translation error or an LLM-style flourish that nobody challenged. This is on hundreds of team cards.

**Most important actual bugs (detailed below).**

- Mendoza's Honors Timeline lists him as both "2025 Heisman Trophy Finalist" and "2025 Heisman Trophy Winner" in adjacent rows, while the Heisman By Year table on the same page shows his win probability at 14.2%. Internal contradiction on the flagship player page.
- History page has broken links: `../programs/.html` (empty slug) and `../teams/illinois-college.html` (404 — the program exists, the team page doesn't).
- Homepage Data Pulse says "72 NCAA-eligible team records and 72 active conferences" but the site ships 667 team pages and 73 conference pages.
- Archive IA implies a week-by-week re-playable history for 8 seasons, but 2014 / 2015 / 2020 / 2021 / 2022 / 2023 / 2024 each have exactly one snapshot. Only 2025 has 7 weekly snapshots. That's not an archive — it's a current-season archive plus 7 historical bookmarks.
- Archive 2020 entry labels a snapshot "Week 38" which does not match any real CFB week number and is especially jarring for the COVID-shortened 2020 season.
- Homepage's Smart Board inline team cards label the Best Wins / Bad Losses module with content like `Best Signal: beat Oregon 56-22 / Stress Point: beat Miami 27-21` — Indiana's "Stress Point" is a win. Label/data mismatch.
- Homepage Team Identity cards use internal module labels ("Best Signal", "Stress Point") that don't match the section heading ("Best Wins / Bad Losses").
- Player pages end with a section literally titled **"Player Card Blueprint"** that explains to the user "these are the next modules that would turn it into a true player dossier instead of a season snapshot" — i.e., a future-roadmap block leaked onto every player's public page.

---

## 2. Page-by-page audit

### A. Homepage (`/index.html`)

**What's working.**

- The hero H1 "How college football is actually feeling this week." is distinctive and mood-first — not another "College Football Rankings Week 15" headline. The subtitle ("A single football universe for FBS through Division III, paired with a proprietary fan-intelligence layer that reads the belief, respect, and rivalry heat around every team. Built for argument, not dashboards.") lands the positioning in 40 words.
- The 13 below-the-fold sections sketch a real product: Mood Board, Smart Board, Power vs. Resume, Highlight Cards, Strength Ladder, Matchup Studio, Conference Power Map, Debate Desk, Weekly Replay, Market Reality Check, History Lab, Data Pulse, Subdivision Footprint. Taken in total, the homepage says "this is the argument room, the research room, and the selection room" — which matches the product thesis.
- The "Premium Analytics Platform" eyebrow + 2025 Season / Model Week 21 / Games Loaded context bar gives the page a scoreboard-style anchoring that most blog-style CFB sites lack.
- The copy "Methodology — How we build this" is a small thing but it's the right trust hook for a fan who's skeptical of another ranking.

**What's not working.**

- The first module below the hero is "The Mood Board, Warming Up" — i.e., a sign announcing the signature feature is off. It's intellectually honest ("these modules stay intentionally empty rather than printing fake precision"), but the user-experience translation is "signature feature: coming soon." Every sub-card (Biggest Vibe Shifts / Respect Gap Leaders / Rival Heat Leaders / Main Character Of The Week) is a description, not a data card. A first-time fan sees nothing concrete above the rankings.
- The Smart Board inlines every team in every division into the homepage DOM. 667 team cards. 4.27 MB of Smart Board alone. It makes the homepage visually dense and means "scroll to the good stuff" takes forever.
- The Data Pulse section says "72 NCAA-eligible team records and 72 active conferences are currently surfaced on the site layer" and "Current model version power-resume-v0.1.0 was last cut at 2026-04-21 23:53:25." Both undercut the premium framing. 667 team pages / 73 conference pages ship to prod; "72" is wrong or mislabeled. "v0.1.0" in the Data Pulse widget is a versioning choice that screams beta on a page calling itself Premium Analytics Platform.
- "Matchup Studio" on the homepage renders a raw `<select>` with 130+ team options in a linear dropdown. There's no searchable typeahead. Fan picks Team A → scrolls through 130 options → repeats for Team B.

**Bugs / broken states.**

- Homepage Smart Board team cards each render a "Best Wins / Bad Losses" heading but the content inside labels things "Best Signal" / "Stress Point" — inconsistent label system. On Indiana specifically, "Stress Point: beat Miami 27-21" is nonsensical on the face of it (the stress point is a win, not a loss).
- Every inline team card uses the h3 "Offensive Reminiscence" / "Defensive Reminiscence" (297 occurrences each — one per FBS team). This is almost certainly meant to be "Historical Comp" / "Plays Like" / "Resembles". "Reminiscence" is the wrong English word for historical similarity. Appears on hundreds of cards.
- Data Pulse numeric claim ("72 NCAA-eligible team records") contradicts the Smart Board (667) and the Subdivision Footprint below.
- Matchup Studio `<select>` options include Alabama State (FCS), Jackson State (FCS), Stephen F. Austin (FCS), Tarleton State (FCS) intermixed with Indiana (FBS), Ohio State (FBS), etc. — they're level-tagged but unordered. Getting from "Ohio State" to "Alabama" means scrolling past 40+ unrelated teams.

**Biggest UX risks.**

- A fan who opens this during the offseason (which is right now, 2026-04-22) sees "Mood Board, Warming Up" + an enormous static rankings list + a matchup dropdown that won't fit on a phone. Nothing on the screen is fresh, interactive, or hot. The homepage needs an offseason mode.
- The sheer DOM size on mobile will make the first-contentful-paint bad and kill scroll performance. A 5.2MB single file isn't just an engineering concern — users will feel it.

**Best opportunities to improve.**

- Replace the empty Mood Board placeholder with real offseason-relevant content: transfer portal pulse, returning production leaders, recruiting board movers, spring game reactions. If the conversation pipeline is pre-season-quiet, substitute with what IS signal.
- Stop inlining the Smart Board. Replace with a top-25 ranked teaser and an "All 667" link to `/rankings/`. Page weight drops ~4MB and the homepage starts being a homepage.
- Kill the "72 NCAA-eligible team records" claim or make it make sense. Just say "667 teams across FBS, FCS, D-II, D-III, 73 conferences, 3,828 games since 2014."

**Concrete fixes.**

- Rename every "Offensive Reminiscence" / "Defensive Reminiscence" to "Offensive Comp" / "Defensive Comp" or "Plays Like" / "Defends Like".
- Remove `power-resume-v0.1.0` from the user-facing Data Pulse. Internal metadata; not user copy.
- On homepage Smart Board cards, fix the "Best Wins / Bad Losses" heading to match the labels used inside, OR change "Stress Point: beat Miami 27-21" to something that fits a win (e.g., "Closest call: Miami 27-21").
- Swap the `<select>` dropdowns in Matchup Studio for a typeahead search with recent teams pinned.

---

### B. Rankings page (`/rankings/index.html`)

**What's working.**

- H1 "2025 Season across every level." — clean.
- Six sections: Selection Room Readout, Rankings Board Controls, Power vs. Resume Analysis, Strength Ladder, Debate Starters, Historical Context. The framing ("selection room") matches the product thesis and is a better metaphor than a plain table.
- Three dropdown filters — Level (All / FBS / FCS / D-II / D-III), Conference, Sort by (Published rank / Power / Resume / Team A-Z). These are the right filters.
- 667 team rows is the correct scope for "the whole universe." Power and Resume as co-equal columns is a serious choice.

**What's not working.**

- The rankings page *also* inlines every team's cards (Team Identity / Best Wins / Bad Losses / Fraud Watch / Historical Context / Overall Team Profile). That explodes the page to 763k chars / ~230 `Team Identity` h3 occurrences. A rankings page should be a list with drilldown, not a list of full profiles.
- Conference dropdown includes "Pac-12" grouping Washington State (rank 65) and Oregon State (rank 184) — technically correct for 2025 but fan-facing confusing.
- No indication on the column headers which sort direction is active (beyond the dropdown value). No arrow indicators.
- The "Selection Room Readout" h2 sounds great but the content under it is a paragraph of copy, not a committee-style ranked tier teaser. The metaphor is stronger than the execution.

**Bugs / broken states.**

- A stale h3 literal `${escapeHtml(team.team_name)}` appears inside the HTML — this is inside a client-side `<template>`, so it won't be visible in most cases, but it's in the rendered DOM. A browser with JS disabled would see it. Wrap these template placeholders in a `<template>` element (if not already) or at minimum `style="display:none"`.
- `Loading team context...` is used as a placeholder h3 in the Historical Context focus widget. Also in the DOM as static text — if hydration fails, the page shows this forever.
- "No teams found" appears once — fine as an empty-state string, but verify it's actually used.

**Biggest UX risks.**

- A "casual" fan who filters to Big Ten / Sort by Resume expects to see the Big Ten sorted by Resume. If JS filter isn't bulletproof on this 763k-char DOM, the interaction lags or snaps.

**Best opportunities to improve.**

- Make this page a compact, fast ranking table (team name, record, power, resume, trend arrow, conf pill) and move the per-team detail into a slideout / row-expansion rather than pre-rendered. This is also how ESPN, On3, and Fox all present rankings — dense table, detail on click.
- Add sticky column headers so sort state and filters stay visible while scrolling.

**Concrete fixes.**

- Move "Historical Context" and related deep modules either to their own page or to a side panel. Don't inline them 667 times.
- Put active sort indicator on the chosen column header.
- Clean up the template literals so they don't ship to production HTML.

---

### C. Heisman board (`/heisman/index.html`)

**What's working.**

- H1 "A full-board Heisman model, not just a top-three list." — nails the positioning.
- Column headers Rank / Player / Team / Pos / **Nowcast / Forecast / Win / Finalist / Ballot** — the five analytical concepts the product is built around all appear as sortable columns. That's legitimately original vs. ESPN's "Heisman Watch" (three names + a paragraph).
- Position filter includes Defense explicitly. Conference filter covers all FBS conferences. Sort dropdown covers Current rank / Win probability / Finalist probability / Ballot share / Player A-Z. Power-user friendly.
- Fast Read tile explicitly surfaces a "Best non-QB / Best Group of Five case / Best defensive case" stack. This is exactly the narrative architecture a fan wants (vs. "here are three QBs, goodnight"). Byrum Brown at #5 overall for South Florida is a legit G5 representation.
- The Board Controls copy: "Search the full board by player, team, conference, or position, then flip between raw order and probability views." Clean, plain-English.

**What's not working.**

- The page ships a 14.7MB HTML file. That is the largest page in the product. With 15,363 player links embedded, it's effectively a pre-rendered database query. Phones will struggle. This is the page most at risk of making the site feel broken on mid-tier hardware.
- Column "Nowcast" and "Forecast" appear only once each in the rendered HTML (as column headers). The concepts aren't explained anywhere on the page. A real fan will not know what Nowcast vs. Forecast means. Either a row of definition chips above the table, or hover tooltips, or both.
- The "Best defensive case" surfaces Caden Curry as the top defensive player — at **rank #637 overall**. The framing says "best defensive case" but the rank says "defense barely charts." The model is being honest but the UI is saying two contradictory things: "we include defensive players" and "defensive players are nowhere near the conversation." The editorial treatment should explicitly name that tension.
- Conference filter includes Pac-12, which in 2025 effectively means Oregon State + Washington State. Neither will be in a Heisman race.

**Bugs / broken states.**

- "No external Heisman futures prior is lo[aded]" text fragment — suggests a model fallback when external futures markets aren't loaded. Probably fine, but verify it doesn't render as visible text.
- Page size is a bug in itself. A 15MB Heisman board is a correctness-but-not-viable experience.

**Biggest UX risks.**

- A fan arrives, loves the Win / Finalist / Ballot columns, sorts by Ballot share → model returns a rank flip that makes sense but the probability decimals are small and the rows look visually identical. The probability display has to be scannable at a glance — right now the numbers are text without magnitude bars.

**Best opportunities to improve.**

- Move the 15k-row board server-side or paginate / virtual-scroll. Show top 50 by default; load more on click.
- Add a Heisman primer row: "Nowcast = where the race stands right now. Forecast = where we think it ends up. Win = chance to win. Finalist = chance to be in NYC. Ballot = vote share." 25 words total. Users won't guess these meanings.
- Give each probability column an inline sparkline / bar so fans can eyeball the gap between #1 and #5.

**Concrete fixes.**

- Add position-filtered sub-boards (QB top 10 / RB top 10 / WR top 10 / Defense top 10) as one-click tabs.
- Cap defensive "Best case" framing with the honest note that no defensive player is inside the top 100.
- Remove Pac-12 as a conference option for 2025+, or show it with a note ("Pac-12 after 2024 realignment").

---

### D. Player pages (`/players/*.html`)

I went deep on: Fernando Mendoza (QB, Indiana, Heisman #1), Jeremiyah Love (RB, Notre Dame), Byrum Brown (QB, South Florida — G5), Caden Curry (DE, Ohio State — defense), Arch Manning (QB, Texas), Jeremiah Smith (WR, Ohio State).

**What's working — and this is where the product is strongest.**

- Shared skeleton across all player pages: Hero card with four top-line concepts (Current nowcast / Season forecast / Win probability / Best official finish), then Story → Current Season Production → Identity & Role → Recruiting Pedigree → Transfer Arc → Trophy Case → Honors Timeline → Heisman By Year → Roster Timeline. The sequence matches how a fan actually forms an opinion.
- Position-adaptive second headline: "Why this is a two-channel quarterback case" for QBs, "Why this is more than a rushing profile" for RBs, "Why the profile pops beyond receiving" for WRs, "Why this is a rare defensive case" for DEF. That's editorial judgment baked into the data — no mainstream site does this.
- Traditional Stats block is exactly the scoreboard layout fans want: Season / Team / CMP / ATT / CMP% / YDS / YPA / TD / INT / RTG / LNG / SACK, with a Career row underneath. Rushing stats for a QB are below the passing block — again the right hierarchy.
- Percentile context inline on each stat (`3,535 pass yards — 41 TD 6 INT — #14/367 (96th pct)`). Sports Reference gives percentiles; ESPN never does. This is the most valuable single element on the player page.
- Advanced Metrics block clearly labeled "Advanced layer — Usage, value, and context — Advanced metrics second — Usage, value, and opponent-adjusted context." Physical separation from the traditional stats. Correct hierarchy.
- "30-second read" tag at the top of the identity block (`High-volume passer | Highly efficient | Vertical threat`) — this is the "what kind of player is this in 20 seconds" answer the product spec asked for, and it's nailed.
- Recruiting Pedigree on Mendoza correctly shows "2-star — No. 2149 recruit — Composite 0.7933 — Signed with California 2022" — that data is accurate and not every site carries it.

**What's not working.**

- Every player page ends with a section titled **"Player Card Blueprint"** that begins "The card now has narrative, stats, identity, and award context. These are the next modules that would turn it into a true player dossier instead of a season snapshot." That is an internal roadmap note talking directly to the user. It says "this page is incomplete." It's on Mendoza's page. It's on Manning's page. It's on every page. Delete it or move it behind a staff-only flag.
- The label "Honors pipeline is ready" appears on several pages (Brown, Curry, Manning, Smith) in place of populated honors. That's the engine's "no data yet" placeholder. Fine during development; not fine as production copy for the #2 and #3 players in the Heisman race.
- "All-American" and "All-Conference" never appear in the HTML on the players I sampled — even for the presumptive Heisman top-3. Either the awards data isn't loaded, or it's labeled differently. Mendoza's Honors Timeline only has two rows (Finalist + Winner), both just for Heisman. No Big Ten Player of the Year, no All-Big Ten, no AP All-American. For a player the model ranks #1 in the country, this is a thin trophy case.
- The Trophy Case on Mendoza reads "1 finalist season — Invited into the official finalist tier in 2025. That belongs in the trophy case, not buried in a table." Great copy voice. But there's only one item in the trophy case. Feels sparse.

**Bugs / broken states (serious).**

- **Data contradiction on Fernando Mendoza's page.** The Honors Timeline lists TWO rows for 2025:
  - "2025 | Heisman Trophy **Finalist** | national_award | Indiana | Heisman Trust | Finalist | QB | Big Ten"
  - "2025 | Heisman Trophy **Winner** | national_award | Indiana | Heisman Trust | Winner | QB | Big Ten"

  ...meanwhile the Heisman By Year table on the same page has: "2025 | Indiana | QB | Rank 3 | Forecast #1 | Win **14.2%** | Finalist **74.2%** | Official Finish: **Tracked** | Points: -- | W21 snapshot | Big Ten | Official finalist".

  So the awards ledger says Mendoza won the 2025 Heisman, but the model's own probability says 14.2% win equity. Either the Honors Timeline is pulling in projected/scenario data as if it were real honors (serious), or Mendoza actually did win and the probability table is stale (less serious but still wrong), or there's a double-entry bug. Whichever — a fan who looks at this page closely will catch it and lose trust.

- Caden Curry's defensive page is mostly correct but the "Why this is a rare defensive case" framing followed by "Current nowcast / Forecast / Win / Finalist" — his Nowcast is #637. That is consistent across the data but the page pushes Heisman framing hard for a player whose Heisman case is real only in the "it's nice to include defenders" sense. Either lean into the G5/defensive editorial more, or don't.

- "Percentile" as a raw word appears 0 times; the format is `#14/367 (96th pct)`. Minor but "pct" isn't immediately readable. Consider spelling percentile once as a chip legend.

**Biggest UX risks.**

- The Player Card Blueprint section shipping to users is the biggest credibility risk on these pages. Delete it before any more eyes see it.
- The contradiction on Mendoza's honors will get screenshotted and shared.
- Empty "Honors pipeline is ready" blocks on top-5 Heisman candidates will make fans question whether the site knows who these players actually are.

**Best opportunities to improve.**

- Fix the Mendoza honors contradiction and audit the underlying data pipeline: are projected awards being written to the same table as actual awards?
- Populate All-American / All-Conference / Conference POY for real 2025 award winners.
- Add one fan-facing "why he's here" sentence under the 30-second read that references what actually happened this season (signature wins, CFP games, etc.).
- Add game log tab for game-by-game stats — right now the page has season and career rows but no per-game line.

**Concrete fixes.**

- Delete or feature-flag off the "Player Card Blueprint" section.
- Change "Honors pipeline is ready" to "Awards will appear as selector lists publish (Dec–Jan)." Or show the actual award once it's loaded.
- Resolve: is Mendoza a 2025 Heisman Winner in the Honors Timeline, or not? And make the Win/Finalist probability table match.

---

### E. Team pages (`/teams/*.html`)

Same skeleton across all 6 teams I sampled. 16 h2 sections, consistent. Hero card with Record / Power / Resume / Net Points. Subnav for Program History / Matchup Simulator / Compare Teams / Back To Rankings.

**What's working.**

- Hero stack is clean: team name, conference, rank pill, and a 2x2 stat grid with Record / Power / Resume / Net Points. Indiana: 16-0 / +24.6 / 100 / +479. Scannable in under 5 seconds. That matches the product spec.
- The sequence Performance Narrative → Game Impact Board → Betting Lens → Market Game Log → Efficiency Dashboard → Why The Model Has Them Here → Placement Context → Closest Neighbors → Historical Snapshot → Program Arc → Season Phase Split → Loaded History Signals → Impact Cards → Schedule → Year-By-Year is coherent if dense. It's a proper dossier.
- "Why The Model Has Them Here" is a great module concept. If it does what it says — explains the team's rank in plain English — it's a differentiator.
- Season Rating Journey as a line chart with hoverable game markers is the right visualization for a team page.
- The Week-by-Week Impact Cards (`Week 4 vs Illinois`, `Week 11 vs Penn State`, `Week 20 vs Oregon`) capture the season's most important games.

**What's not working — the big one.**

- **The Team Mood Card on every single team page is empty.** I checked Indiana (#1), Alabama, Ohio State, James Madison, Montana State, Notre Dame — all six show:
  - Confidence: No signal
  - Fan sample not yet published
  - Fan Pulse: Awaiting Signal
  - Reality Check: Awaiting Signal
  - Respect Gap: Awaiting Signal
  - Swing Meter: Awaiting Signal
  - Cohesion: Awaiting Signal
  - Rival Heat: Awaiting Signal
  - Top Storylines: Storylines light up automatically once the weekly conversation sample clears the publish gate.

  The Mood Card is the second module below the hero on every team page. It takes up significant screen real estate. And it's blank on every team. The site's signature fan-intelligence feature is showing a description of what it would show if it worked.

  The copy is honest ("we only publish with at least 12 clean mentions from several distinct authors. Until then, this card shows the frame, not the number") — but this isn't a reasonable production state for the defining feature of the product. Until the pipeline publishes, the Mood Card should be collapsed, tabbed behind a "Live Fan Intelligence (populating Dec–Jan)" badge, or replaced with an offseason analogue (transfer portal chatter, returning production, spring game takes).

- "Program History" link from team page goes to `/programs/indiana.html` which is a *different* page than `/teams/indiana.html`. Both exist, both have H1 "Indiana", both feel like team pages. The distinction (current-season view vs. historical-arc view) isn't visually obvious. Users will get lost between them.

- The Smart Board inline card on the homepage has a heading "Best Wins / Bad Losses" but labels values "Best Signal" / "Stress Point" — the team page uses "Game Impact Board" for similar content. Three different label systems for what is conceptually the same module.

**Bugs / broken states.**

- Indiana: "Record 16-0" / "Net Points +479" — if this is data the model actually outputs for 2025 Indiana it's a remarkable claim. In real life Indiana was 11-2 in 2024 with a CFP first-round loss; 16-0 implies a national championship run with playoff games included. Either this is genuine 2025 season data (the model's final week 21 board) or it's generated/simulated data. Either way the team page should make it obvious which.
- On the Indiana team page, "Rival Heat: Awaiting Signal" under the Mood Card is next to a Rival Heat tile that does describe itself ("Rival Heat tracks mockery, fear, and obsession from rival fanbases.") — but has no rival teams listed. For Indiana vs. Purdue / Ohio State / Michigan — all obvious rivals — this should at minimum pre-populate the rival list even without mood scores.
- The "Year-By-Year Results" block on team pages contains rows like `W15 W18 W20 W21` which are week-result codes with no visible legend. A new user has to guess W=Win, L=Loss, numbers=week. Add a one-line legend.

**Biggest UX risks.**

- The empty Fan Intelligence block, seen on every team page, will make casual fans think the site is abandoned.
- The `/teams/` vs `/programs/` duality will send users to the wrong page repeatedly.
- Record + probability data that might be projected/simulated presented alongside actual schedule results creates ambiguity about what's real vs. modeled.

**Best opportunities to improve.**

- Ship an offseason Mood Card variant that's populated from transfer portal, coaching changes, returning production, and spring game reactions. Swap automatically when in-season chatter drops below the publish threshold.
- Collapse `/programs/` into `/teams/` as a tab or section. Don't maintain two pages.
- Add a small "Model Snapshot: Week 21" watermark so users understand the record and numbers are the model's end-of-season state.

**Concrete fixes.**

- On every team page, if fan sample hasn't cleared the publish gate, collapse the Mood Card behind a single chip/button ("Fan Intelligence — offseason, re-opens in August"). Don't show 7 empty sub-tiles.
- Add a W/L/number legend above Year-By-Year Results.
- Resolve `/teams/` vs `/programs/` naming and nav.

---

### F. Fan Intelligence / Sentiment / Conversation features

This is the most important and most underdeveloped surface.

**What's working conceptually.**

- The framework itself is strong and differentiated: Fan Pulse (how a fanbase feels), Respect Gap (how the fanbase feels vs. how outsiders talk), Rival Heat (how rivals talk about this team), Swing Meter (how violently mood moves week-over-week), Cohesion (internal fanbase agreement vs. civil war), Reality Check (fanbase vs. the actual model). These are genuinely original concepts and each one has a plain-English definition. The copy for each is short, specific, and memorable ("teams living rent-free in rival fanbases this week").
- The explicit honesty about threshold-gating ("we only publish with at least 12 clean mentions from several distinct authors... rather than printing fake precision") is the right editorial instinct. Mainstream sites hallucinate fan sentiment; this one refuses to.
- Top Storylines framing: "Source: public conversation collected from Reddit & supplemental feeds. We split fan, national, and rival audiences before scoring." Good transparency.

**What's not working — and it's structural, not copy.**

- **Every single fan-intelligence tile is empty on every team page right now, and has been empty on the homepage module too.** Across 6 team pages sampled: 0 populated. Homepage Mood Board: 0 populated. The entire feature is offline. Keyword counts across the homepage: "National Mood" 0x, "Market vs Mood" 0x, "Model vs Market" 0x, "Reality Gap" 0x, "Swing Meter" 0x — these concepts are supposed to be signature but don't even appear in the homepage HTML outside of descriptions.
- The empty Mood Card on the team page is arranged as a 7-tile grid. Seven empty tiles feels dramatically more broken than one empty tile. Even if the data really isn't ready, the UX shouldn't punish the user with seven repetitions of "Awaiting Signal."
- The user's differentiators — Respect Gap, Rival Heat, Market vs Mood, Model vs Market — mostly appear only as module labels or descriptions, not as actual data surfaces. The Matchups page does have "Which Fanbase Is Calmer / What Fans Are Afraid Of / Rival Timelines On Fire" as H3s which is the best fan-intelligence surface anywhere in the product. Those headings are fantastic. But even those tiles need to be confirmed populated.
- "Market vs Mood" vs "Model vs Market" — the site uses both phrasings. Pick one. The homepage has a "Market Reality Check" section. The Matchups page has "Market vs Model vs Mood." Needs a unified vocabulary.

**Bugs / concerns.**

- The empty Mood Card is not actually a bug — it's by design — but it is the single most damaging UX state on the site.
- The Rival Heat tile should at least list the rival teams pre-populated even when scores are null. For Indiana, obvious candidates are Ohio State, Purdue, Michigan. Showing "rival teams: —" while claiming to track rivalry heat is weaker than showing the rival teams without scores.
- On the homepage, the Mood Board section description for "Main Character Of The Week" is "Whichever team the broader sport cannot stop talking about." That's a great product tagline. Use it bigger when the feature actually ships.

**Biggest UX risks.**

- Fans who came for the mood/sentiment layer will bounce within 30 seconds. The concept is the product's moat; the emptiness is the product's biggest liability.
- Once the pipeline turns on, the signal-to-noise has to be good enough that fans find it worth returning. If the first published Fan Pulse reads as hand-wavy, the trust hit is permanent.

**Best opportunities to improve.**

- Ship an always-on fallback layer: historical fan-intelligence from past seasons. If the live sample hasn't cleared the publish threshold, show last season's Respect Gap leaders, Rival Heat finalists, biggest Vibe Shifts from 2024. That gives users a taste of what the feature does even in offseason silence.
- Add a short "How this works" chip next to every Fan Intelligence tile that a fan can tap to see a 2-sentence methodology + a representative example. Lowers the "what is this" bounce.
- Pre-seed rival lists. Indiana's Rival Heat tile should show Ohio State / Michigan / Purdue as pills even when the scores are null.
- Consolidate "Market vs Mood" / "Model vs Market" / "Market Reality Check" into one vocabulary and use it everywhere.

**Concrete fixes.**

- Collapse the empty Mood Card on team pages into a single CTA ("Fan Intelligence re-opens in [month]") instead of 7 empty tiles.
- Populate at least one concrete example per concept with historical data so new visitors can understand what Fan Pulse / Respect Gap / Rival Heat feel like.
- Kill duplicate "Main Character Of The Week" module on the homepage; replace with a live example as soon as data is on.

---

### G. Matchups and Compare

**What's working.**

- Matchups H1: "Model, market, mood — who actually wins the fight?" That's a better matchup-page headline than any I can think of in the space. The three-lens framing (Model / Market / Mood) is the product's biggest conceptual contribution and here it's front and center.
- Matchups sections: Neutral-Field Matchup Studio, Market vs Model vs Mood, Quick-Load Scenarios. Clean structure.
- H3s like "Which Fanbase Is Calmer", "What Fans Are Afraid Of", "Rival Timelines On Fire" are the best-named modules on the entire site. They sound like bar arguments in progress, not dashboards.
- Compare H1: "Settle the argument without opening ten tabs." — top-shelf editorial hook. Compare sections: Comparison Board, Why Team A or Team B, Season Phase Split, Component Battle, Shared Opponents, Quick-Load Arguments.
- The Quick-Load Arguments on Compare give context-labeled preset pairs: "Best team vs. best resume — Indiana vs. Ohio State — The most classic committee argument on the board." / "Top FCS bridge test — BYU vs. North Dakota State — How the best FCS team stacks up against a quality FBS profile." / "Division bridge — Delaware State vs. Ferris State — A cleaner look at the gap between the top of Division II and the lower edge of strong FCS territory." This is editorial with teeth.
- Matchups has the same Quick-Load treatment with different named scenarios.

**What's not working.**

- Compare and Matchups both cover "pick two teams and see the comparison." The distinction (Matchups = predictive/game simulation; Compare = structural argument) isn't obvious from the nav. A user will bounce between them looking for the same tool. The Matchups H1 emphasizes "who wins the fight" — predictive — but the Market-vs-Model-vs-Mood framing is more about argument than simulation. Needs positioning clarity.
- Both pages are large (588k Matchups, 2.6MB Compare). Compare in particular has the same inline-team-card problem.
- "Rival Timelines On Fire" on the Matchups page is a stunning H3 but if the underlying mood data is empty (as shown everywhere else), the module is another empty placeholder behind a great headline.

**Bugs / broken states.**

- JSON state object leaks visible in some extracted HTML — likely inside a `<script>` tag used for client-side rehydration, which is fine, but a misconfigured rendering could surface it. Double-check it's wrapped.
- No obvious empty-state handling if a user selects two teams with no head-to-head history for "Shared Opponents."

**Biggest UX risks.**

- Users hit Compare, love the headline, try it, see empty mood surfaces, leave.
- Users don't understand Compare vs. Matchups and use the wrong tool.

**Best opportunities to improve.**

- Add a single-sentence differentiation above each page: "Use Matchups when you want a game simulation. Use Compare when you want a side-by-side season argument."
- Make the "Market vs Model vs Mood" module the visual anchor of Matchups. Three columns, one team pick, three verdicts — this is the kind of shareable layout that will travel on social.

**Concrete fixes.**

- Clarify Matchups vs. Compare in the nav with micro-descriptions.
- Ship at least one Quick-Load scenario on each page with real live data (Market odds vs. Model delta vs. Mood tilt) even if it's a cached example.

---

### H. Conferences

**What's working.**

- 73 conference pages is genuinely ambitious. All three divisions of FCS and D-II/D-III are covered.
- FBS conferences follow `fbs-<slug>.html` naming consistent with `dii-*` and `diii-*` — clean URL hygiene.
- Each conference page has Conference Snapshot / League Drivers / `<Conference> Team Board` — minimal but structured.

**What's not working.**

- Conference pages are small (~88k) and follow the same three-section skeleton across FBS/D-II/D-III. For the SEC vs. the American Rivers Conference (D-III), that's an odd symmetry — SEC deserves more editorial treatment.
- No visible cross-linking to conference championship history, cross-conference matchups, or a "Conference Power Map" from the conference pages themselves. The homepage has a Conference Power Map section — the conference pages should be the detailed version.

**Bugs / broken states.**

- None immediately obvious.

**Biggest UX risks.**

- A fan who navigates to `/conferences/fbs-sec.html` from the nav expects SEC content worthy of the SEC. They get a three-section skeleton page. That will underperform expectations.

**Best opportunities to improve.**

- Tier conference pages by level. FBS conferences get more editorial (signature games of the year, POY candidates, rivalry heat, CFP resume angle). D-II/D-III conferences can stay minimal.

**Concrete fixes.**

- Add conference-specific Heisman mini-board (top 3 Heisman candidates from the conference).
- Add conference-specific power/resume scatter plot.
- Add cross-conference Head-to-Head so SEC vs. Big Ten arguments have a home.

---

### I. Archive & History

**Archive — what's working.**

- H1 "Replay the board the way fans actually remember a season." — another strong editorial headline.
- 2025 has 7 weekly snapshots (weeks 21, 16, 9, 7, 4, 3, 1). The current-season snapshot replay is legit.
- Split by season makes the IA obvious.

**Archive — what's not working.**

- Every historical season (2014, 2015, 2020, 2021, 2022, 2023, 2024) has exactly **one** snapshot. That is not an archive — it's a bookmark. The page header promises "the way fans remember a season" but you can't re-play most seasons week by week.
- 2020 snapshot labeled "Week 38" — no CFB season has a Week 38. 2020 was a shortened, scrambled season due to COVID. This is either a calendar-week-of-year label misused as week-of-season, or an off-by-many error. Very noticeable.
- The jump from "2014" to "2015" to "2020" skips 2016/17/18/19 entirely. Fans will notice gaps in supposed "history."

**History — what's working.**

- H1 "The archive should argue back." — best editorial line on the site.
- Twelve sections: Best By Level, Greatest Loaded Seasons, Strongest Loaded Teams, Closest To Program Peak, Best Two-Year Runs, Turnarounds, Dynasty Track, Roughest Loaded Seasons, Hard Landings, Season Almanac, History Explorer, How Teams Start The Next Season. Each one is a real fan argument surface.
- Four "<Level> Historical Peak" h3s (FBS / FCS / D-II / D-III) — covers the full universe.
- Large page (4.9MB) but the content density is actually justified here — this is where deep history lives.

**History — what's not working.**

- Broken link: `../programs/.html` (empty slug — a template variable was never substituted).
- Broken link: `../teams/illinois-college.html` — Illinois College is a real D-III program that has a `/programs/illinois-college.html` page but NOT a `/teams/illinois-college.html`. The `/teams/` page doesn't exist, but History links to it. 404 waiting to happen.
- "How Teams Start The Next Season" sections with copy "The last version of a team matters / One season should not erase the whole arc / Continuity keeps ratings sticky" — great editorial voice, but placed oddly at the bottom of a history page. This is really about the model's preseason prior logic — that probably belongs on About-Model, not History.

**Biggest UX risks.**

- The archive IA promises more than it delivers and the Week 38 label is a visible bug.
- Broken links on the History page damage credibility on the surface most likely to attract repeat visits.

**Best opportunities to improve.**

- Either fill in the missing weeks for historical seasons, or rename Archive to "Season Finales" and scope down the promise.
- Audit all link interpolation. The empty-slug `../programs/.html` proves the templater is shipping at least one bad link.
- Rename 2020 "Week 38" to what it actually is (Week 17? Final poll?).

---

### J. About-Model

**What's working.**

- This is the strongest single page on the site. H1: "Two models, one football universe." The Power Model / Resume Model sections do exactly what they need to: explain Power is forward-looking, Resume is backward-looking, they're intentionally kept separate, and both anchor to the same 2025 season identity.
- Namechecks SP+ / FEI / Massey / Colley in the right way — places the project in the serious college-football analytics family without claiming to be them.
- "How Teams Start A New Season" section is a credible preseason priors explanation.
- "Season Identity Rules" handles the January-bowl-games-belong-to-prior-season rule cleanly.
- Research Principles and Data Stack both deliver legitimate transparency.

**What's not working.**

- "The current local build is surfacing 72 NCAA-eligible team records, 72 active conferences, and 3,828 completed games" — same 72/72 bug as the homepage. On the credibility page, of all places.
- No visual — the page is all prose. Even one diagram (a Power vs. Resume scatter across seasons, or a chart of how preseason priors decay as games come in) would make it memorable.

**Bugs / broken states.**

- The 72/72 claim.
- No H3s — the entire page is an H1 + 8 H2s. That's fine for a short manifesto-style page but means the in-page table-of-contents anchors are shallow.

**Best opportunities to improve.**

- Add one hero chart at the top — something like "How the 2025 season moved Indiana's Power rating week by week." That turns abstract "we do power and resume" into a visceral proof point.
- Add a "See it in action" chip at the end of each subsection linking to the concrete module where that methodology shows up.

**Concrete fixes.**

- Fix the 72/72 number.
- Add a diagram / chart.
- Add a "when would I use Power vs. Resume" one-liner near the top.

---

## 3. Compared to major CFB sites

**Where this site is already better than ESPN / On3 / 247 / CBS / Fox / Sports Reference.**

- Editorial voice. Nothing in mainstream CFB reads like "Settle the argument without opening ten tabs" or "The archive should argue back" or "Which Fanbase Is Calmer." The copy is the best in the space right now.
- Power / Resume separation. ESPN's FPI shows predictive power only. CBS and Fox show human polls only. This site shows both, keeps them conceptually separate, and puts them on equal visual footing. Sports Reference has SRS/SOS but doesn't split them this way for a fan audience.
- Heisman is a full-board model with Nowcast / Forecast / Win / Finalist / Ballot columns. ESPN's Heisman Watch is a paragraph and three names. The site's Fast Read tile (Best non-QB / Best G5 / Best Defensive) is a better narrative handle than anything mainstream.
- Player pages have percentiles inline, position-adaptive framing headers, and a Recruiting Pedigree + Transfer Arc combo on the same page. No mainstream site does this in one place.
- A single universe for FBS + FCS + D-II + D-III is unique. Mainstream sites cover D-I with an occasional hat-tip to FCS playoffs; this site treats them as co-equal.

**Where this site is worse.**

- Performance. Homepage is 5.2MB; Heisman is 14.7MB. ESPN and On3 load faster even on slow connections. This will bleed mobile users.
- Fan intelligence layer is the signature feature and it's empty. ESPN and On3 don't try to do this, but at least their features work. A broken-looking flagship feature loses to a non-existent one.
- Real-time freshness. Offseason state on this site (2026-04-22) looks stale — W21 snapshot, empty mood, no transfer portal heat, no spring game coverage. ESPN dominates offseason with recruiting news and transfer portal trackers. The site has no offseason mode.
- Conference pages are thin compared to 247's conference hubs or The Athletic's conference verticals.
- No scores / scoreboard / live game mode — this isn't what the site is for, but a CFB fan's first Saturday question is "what's the score" and there's no answer here. Either add a minimal scoreboard or explicitly position as "not a scoreboard, a selection room."

**Where this site is more ambitious but not yet polished.**

- The Matchups "Market vs Model vs Mood" framing. Conceptually new. Executionally still empty-tiled because the mood layer isn't live.
- The Compare "Quick-Load Arguments" editorial presets. Strong concept, could be stronger execution with real Market/Model/Mood deltas visible on each preset card.
- The History page's "Dynasty Track / Turnarounds / Hard Landings" section lineup. Very unique; the data behind it needs visual treatment to land.
- 667 team pages deep across divisions is ambitious. Right now the per-team pages get thinner at lower levels. A fan of a D-II program will not find content depth matching an FBS program.

**Where it has true proprietary upside.**

- The Power vs. Resume scatter, the Heisman full-board, and the Fan Intelligence framework are each things nobody else ships. If all three are real and populated, this site has an identity no competitor can match.
- The integration of a predictive model + market odds + fan sentiment on a single matchup page ("Model vs Market vs Mood") is an honest-to-God new product surface. If it's populated with real data, it's the kind of thing fans will screenshot and tweet weekly.

---

## 4. Prioritized action list — Top 10 changes next

Ordered by real-fan impact. Bugs and UX/design improvements are tagged.

1. **[BUG → UX]** Ship a populated Fan Intelligence fallback. Either turn the pipeline on, or replace every empty Mood Card / Mood Board with an offseason surrogate (transfer portal chatter, returning production, spring game reactions, last-season mood replay). The current "7 tiles of Awaiting Signal" on every team is the single worst UX on the site.
2. **[BUG]** Fix the Fernando Mendoza Honors Timeline vs. Heisman By Year contradiction. Either he's the 2025 Heisman Winner or his win probability is 14.2% — can't be both. Audit the awards table for projected-vs-actual leakage across all player pages.
3. **[BUG]** Delete the "Player Card Blueprint" roadmap section from every player page. It tells users the page is unfinished. Ship it internally if you want, but not on production.
4. **[UX]** Stop inlining all 667 team cards into the homepage. Replace Smart Board with a Top 25 teaser and a link to `/rankings/`. Homepage drops ~4MB, mobile users stop bouncing.
5. **[UX]** Fix the `/teams/<slug>` vs. `/programs/<slug>` split. Either consolidate into one page (with a "Current Season / Program Arc" tab toggle) or make the nav expose both clearly. Right now the nav only links to Programs, so the signature `/teams/` page is undiscoverable from the top level.
6. **[BUG]** Fix history page broken links — `../programs/.html` (empty slug template bug) and `../teams/illinois-college.html` (404). Run a link-checker over the full site.
7. **[UX]** Rename "Offensive Reminiscence" / "Defensive Reminiscence" everywhere. "Reminiscence" is the wrong word for historical comp. Replace with "Offensive Comp" / "Defensive Comp" or "Plays Like" / "Defends Like". Appears on ~300 team cards.
8. **[BUG]** Reconcile the "72 NCAA-eligible team records" claim on homepage and About-Model with the 667 team pages actually shipping. Either the number is wrong or the copy is misleading. Remove `power-resume-v0.1.0` from user-facing Data Pulse while you're there.
9. **[UX]** Paginate or virtual-scroll the Heisman board. 15,363 players in one DOM is not viable on phones. Ship a Top 50 default with "load more" and a per-position mini-board.
10. **[UX]** Add a tiny Nowcast / Forecast / Win / Finalist / Ballot legend on the Heisman page. Five terms, 25 words total, saves every new fan a guess.

---

## 5. Closers

**Three things that would make this site feel dramatically more premium.**

- One large hero visualization on the homepage above the fold that moves — a live Power vs. Resume scatter where teams animate in as you load, or a weekly Season Rating Journey for the top team. Right now the homepage hero is a paragraph and a four-stat strip. A premium sports product leads with a visual.
- A consistent typographic rhythm. The site currently has headings that range from editorial ("The archive should argue back") to internal ("Player Card Blueprint") to module labels ("Offensive Reminiscence"). Pick a single editorial voice and enforce it. One tier of display type, one tier of section type, one tier of module type. Ruthlessly.
- Remove everything that signals beta. `v0.1.0`, "Player Card Blueprint", "Honors pipeline is ready", "Awaiting Signal" x 7 per team. The site sounds like a founder journaling. Fans want to land on a finished surface.

**Three things that would make it more addictive / revisit-worthy.**

- A weekly Main Character / Biggest Vibe Shift / Rival Heat top 3 push as a standing module on the homepage. Even if it's small, making a weekly "mood drop" is what gets fans back every Monday.
- A shareable Compare output. Every Compare result should produce a single-image screenshot-ready card ("Indiana vs. Ohio State — Model says IU +2.3 — Market says OSU -1.5 — Mood says IU calmer") with the site's wordmark. Fans will tweet it; the site gets free distribution.
- A Saturday live lens — even without live scores, even just a live "what's moving in the model this hour" ticker. Gives fans a reason to keep the tab open during games.

**Three things that would make the sentiment / fan-intelligence layer feel truly signature.**

- One weekly "Main Character of the Week" long-form — the team that won the week in fan conversation, with the data under it (Respect Gap, Rival Heat, Vibe Shift, representative posts). Build the weekly habit around that single piece.
- A "Respect Gap Scoreboard" as its own standing page (not a tile) — showing every FBS team ranked by the gap between how their own fans talk about them and how the national conversation talks about them. That's a leaderboard no other site has and every fan will want to know where their team lands.
- Rival Heat duels — side-by-side "what Auburn fans say about Alabama" vs. "what Alabama fans say about Auburn" with representative post citations and a numerical heat delta. Shareable, rivalry-specific, honest, and unprecedented. If this works, it's the feature the site gets known for.

---

_Audit run against local build `power-resume-v0.1.0` @ 2026-04-21 23:53:25 UTC. 35+ pages reviewed structurally; screenshots reviewed where available._
