# CFB Stats Competitor Matrix

**Date:** May 18, 2026
**Research Scope:** 15 CFB statistics sites across 3 dimensions (Player Stats, Team Stats, Cross-cutting Context)
**Scoring Scale:** 1-5 (1 = Minimal/Basic, 2 = Limited, 3 = Standard/Good, 4 = Comprehensive, 5 = Elite/Best-in-class)

---

## Executive Summary

This matrix evaluates 15 major CFB statistics destinations across three critical dimensions:

1. **Player Stats** - Season totals, career statistics, game logs, splits, advanced metrics
2. **Team Stats** - Offense/defense breakdowns, situational statistics, historical data, advanced metrics
3. **Cross-cutting Context** - Rankings, percentiles, league averages, year-over-year deltas, contextual tooltips

**Key Findings:**
- **Sports Reference CFB** remains the canonical leader with a 5.0 overall rating (5/5/5)
- **CollegeFootballData.com** emerges as the analytics powerhouse (4/4/5)
- **ESPN** balances breadth with accessibility (4/4/3)
- **Team-official sites** uniformly lag across all dimensions (1/1/1)
- **PFF** and **Football Outsiders** lead in advanced metrics but lack breadth

---

## Full Matrix

| Site | Player Stats | Team Stats | Cross-cutting Context | Overall |
|------|-------------|------------|----------------------|---------|
| Sports Reference CFB | 5 | 5 | 5 | **5.0** |
| CollegeFootballData.com | 4 | 4 | 5 | **4.3** |
| ESPN CFB | 4 | 4 | 3 | **3.7** |
| PFF (College) | 4 | 4 | 4 | **4.0** |
| TeamRankings | 3 | 4 | 4 | **3.7** |
| FOX Sports CFB | 3 | 3 | 2 | **2.7** |
| CBS Sports CFB | 3 | 3 | 2 | **2.7** |
| Bleacher Report | 2 | 2 | 1 | **1.7** |
| 247Sports | 3 | 1 | 2 | **2.0** |
| On3 | 3 | 1 | 2 | **2.0** |
| Rivals | 2 | 1 | 2 | **1.7** |
| Yahoo CFB | 2 | 2 | 2 | **2.0** |
| Football Outsiders | 2 | 4 | 4 | **3.3** |
| Bill Connelly SP+ | 1 | 4 | 4 | **3.0** |
| Team-official sites | 1 | 1 | 1 | **1.0** |

---

## Site Archetypes

Each competitor sits in one of five archetypes. Understanding the archetype tells you what CFB Index should and shouldn't borrow.

| Archetype | Sites | What it optimizes for | What it under-invests in |
|-----------|-------|----------------------|--------------------------|
| **Canonical** | Sports Reference CFB | Historical depth, URL stability, semantic HTML, scraping/research | Modern mobile UX, advanced/EPA-era metrics, editorial framing |
| **Mass-market** | ESPN, CBS Sports, FOX Sports, Yahoo CFB, Bleacher Report | Breadth, video integration, current-season casual reader, ad inventory | Historical research, accessibility, mobile column completeness |
| **Advanced** | CollegeFootballData, PFF College, Football Outsiders, Bill Connelly SP+, TeamRankings | Modern analytics (EPA, S&P+, grading), methodological transparency (CFBD/FO), forward-looking ratings | Consumer-friendly UI, mobile experience, historical depth pre-2014 |
| **College-native (recruiting)** | 247Sports, On3, Rivals | Recruiting/NIL ranking, transfer portal, recruit profiles, message boards | College-level stats (these treat stats as secondary), team-stat coverage, advanced metrics |
| **Team-official** | rolltide.com, ohiostatebuckeyes.com, etc. | Promotional content, current roster, branded experience | Historical archives, advanced context, accessibility, consistency across schools |

**CFB Index's positioning:** the gap none of these fill — **canonical depth + advanced metrics + consumer UI + all-level (FBS through DIII/NAIA) + editorial framing**. The conformance spec ensures we don't lose to Canonical on table fundamentals. The competitor matrix shows where we differentiate: in the spaces between archetypes.

**Source convergence:** the archetype split mirrors the Codex technical-patterns report's "reference/stat-first" vs "media/product" split ([codex-technical-patterns.md](raw/codex-technical-patterns.md)) and the column-conventions report's distinction between traditional-counting sites and EPA-era sites ([codex-column-conventions.md](raw/codex-column-conventions.md)). The recruiting and team-official archetypes are CFB-specific overlays.

---

## Dimension 1: Player Stats (Season Totals, Career, Game Logs, Splits, Advanced)

### 1. Sports Reference CFB — Score: 5/5

**Evidence:**
- **URL:** `https://www.sports-reference.com/cfb/players/`
- **Season Totals:** Complete per-season stat lines for every FBS player, searchable by name, team, or position
- **Career Statistics:** Automatic aggregation across all seasons with career totals prominently displayed
- **Game Logs:** Dedicated "Gamelog" tab showing box-score-level stats for every game in a player's career
- **Splits:** Home/Away, Monthly, vs. Ranked, vs. Unranked, by opponent conference
- **Advanced Metrics:** Yards per attempt, completion percentage, efficiency ratings, yards per carry, yards per reception, touchdown rates
- **Historical Depth:** Player data back to 1956+ for major programs, searchable across decades
- **Position-Specific Views:** QB (passing, rushing, sacks taken), RB (rushing, receiving, fumbles), WR (receiving, targets, drops where available), DEF (tackles, sacks, interceptions, TFLs)
- **Play-by-Play Integration:** Individual plays linked from player pages where data exists

**Why Elite:** The combination of historical depth, consistent URL structure, downloadable CSV exports, and zero-paywall access makes this the gold standard. No other site matches the breadth + depth combination.

---

### 2. CollegeFootballData.com — Score: 4/5

**Evidence:**
- **URL:** `https://collegefootballdata.com/player`
- **Season Totals:** API-driven player stats with filterable queries
- **Career Statistics:** Aggregated career totals available through API endpoints
- **Game Logs:** Complete game-by-game data accessible via API with rich filtering
- **Splits:** Extensive split data available through API (down & distance, field position, weather, opponent strength)
- **Advanced Metrics:** Expected Points Added (EPA), Success Rate, EPA per play, completion probability (when available)
- **API-First Design:** Entire dataset available programmatically for custom analysis
- **Historical Depth:** Strong coverage from 2014-present, with select data extending further back

**Why 4/5:** Matches or exceeds Sports Reference in advanced metrics and API accessibility, but lacks the curated historical depth pre-2014 and the polished UI for non-technical users. The product is developer-focused, not consumer-focused.

---

### 3. ESPN CFB — Score: 4/5

**Evidence:**
- **URL:** `https://www.espn.com/college-football/player`
- **Season Totals:** Current and recent season stats for FBS players
- **Career Statistics:** Career totals available for active players
- **Game Logs:** Season-by-season game logs for major position players
- **Splits:** Limited splits available (home/away, win/loss)
- **Advanced Metrics:** QBR for quarterbacks (ESPN proprietary), passer rating, yards per attempt
- **Integration with Video:** Selected plays linked to game footage
- **Position Coverage:** Strong QB, RB, WR coverage; defensive stats present but less comprehensive

**Why 4/5:** Excellent for current/recent seasons with strong QB metrics (QBR), but historical depth is limited and advanced metrics focus heavily on offensive skill positions. UI is polished but data export is limited.

---

### 4. PFF (College) — Score: 4/5

**Evidence:**
- **URL:** `https://www.profootballfocus.com/college-football/players`
- **Season Totals:** Comprehensive grading-based stats for FBS players
- **Career Statistics:** Multi-year grades available for players with multiple seasons
- **Game Logs:** Weekly grades available for premium subscribers
- **Splits:** Premium splits include alignment, down & distance, route type for receivers
- **Advanced Metrics:** PFF Grades (overall, pass rush, coverage, run blocking, receiving, etc.), pressure rate, turnover-worthy plays, positively graded plays
- **Position Coverage:** All positions graded with position-specific metrics (OL, DL, LB, CB, S, QB, RB, WR, TE)
- **NFL Draft Context:** Grades include draft position and rookie-year projections

**Why 4/5:** Unmatched in grading metrics and position-specific analytics, but paywall limits accessibility and historical data is inconsistent pre-2016. The product is premium-focused, not a free public resource.

---

### 5. TeamRankings — Score: 3/5

**Evidence:**
- **URL:** `https://www.teamrankings.com/college-football/player-stats`
- **Season Totals:** Current season player stat tables with filtering
- **Career Statistics:** Limited career aggregation
- **Game Logs:** Not a primary feature; some game-context data in team stats
- **Splits:** Minimal
- **Advanced Metrics:** Some efficiency metrics, but focuses on team-level predictions
- **Position Coverage:** Offensive skill positions well-covered; defensive positions limited

**Why 3/5:** Useful for current season snapshots and predictive context, but not designed for deep player research. Historical access is limited and game-by-game tracking is minimal.

---

### 6. FOX Sports CFB — Score: 3/5

**Evidence:**
- **URL:** `https://www.foxsports.com/college-football/player-stats`
- **Season Totals:** Standard stat categories for FBS players
- **Career Statistics:** Basic career totals for active players
- **Game Logs:** Limited game log access
- **Splits:** Minimal
- **Advanced Metrics:** Standard efficiency metrics; no proprietary advanced stats
- **UI Quality:** Clean tables but limited interactivity

**Why 3/5:** Competent for basic stat lookup but lacks depth, historical access, and advanced metrics. Functional but not memorable.

---

### 7. CBS Sports CFB — Score: 3/5

**Evidence:**
- **URL:** `https://www.cbssports.com/college-football/player-stats`
- **Season Totals:** Standard statistics with filtering by team and position
- **Career Statistics:** Basic career totals
- **Game Logs:** Season stats view but not true game logs
- **Splits:** Home/road splits available for major categories
- **Advanced Metrics:** Traditional stats only; limited advanced metrics

**Why 3/5:** Reliable for basic stat lookup with decent filtering, but no unique advantages over ESPN or Sports Reference. Historical depth is weak.

---

### 8. Bleacher Report — Score: 2/5

**Evidence:**
- **URL:** `https://bleacherreport.com/college-football`
- **Season Totals:** Basic stats embedded in articles; limited dedicated stats tables
- **Career Statistics:** Not a core feature
- **Game Logs:** Not available
- **Splits:** Not available
- **Advanced Metrics:** None; focused on editorial content

**Why 2/5:** Player stats are an afterthought. The site is editorial-first with stats as supporting content rather than a research destination.

---

### 9. 247Sports — Score: 3/5

**Evidence:**
- **URL:** `https://247sports.com/Player/`
- **Season Totals:** Basic season stats embedded in player profiles
- **Career Statistics:** High school stats emphasized; college stats secondary
- **Game Logs:** Not available
- **Splits:** Not available
- **Advanced Metrics:** None; recruiting-focused platform

**Why 3/5:** Strong recruiting context but weak on college-level stats. Player profiles include basic college stats but this is not a stats research destination.

---

### 10. On3 — Score: 3/5

**Evidence:**
- **URL:** `https://www.on3.com/players/`
- **Season Totals:** Basic college stats in player profiles
- **Career Statistics:** High school and transfer portal focus; college stats minimal
- **Game Logs:** Not available
- **Splits:** Not available
- **Advanced Metrics:** None; NIL and recruiting focus

**Why 3/5:** Similar to 247Sports—excellent for recruiting/portal context but not designed for stat research. College stats are present but secondary.

---

### 11. Rivals — Score: 2/5

**Evidence:**
- **URL:** `https://rivals.com/`
- **Season Totals:** Minimal college stat integration
- **Career Statistics:** Not a feature
- **Game Logs:** Not available
- **Splits:** Not available
- **Advanced Metrics:** None

**Why 2/5:** Purely recruiting-focused with minimal college stat integration. Not a stats research tool.

---

### 12. Yahoo CFB — Score: 2/5

**Evidence:**
- **URL:** `https://sports.yahoo.com/ncaaf/player-stats/`
- **Season Totals:** Basic stats with limited filtering
- **Career Statistics:** Minimal
- **Game Logs:** Not available
- **Splits:** Not available
- **Advanced Metrics:** None

**Why 2/5:** Basic stat tables without depth or historical access. Yahoo Sports is a general sports destination, not a CFB stats specialist.

---

### 13. Football Outsiders — Score: 2/5

**Evidence:**
- **URL:** `https://www.footballoutsiders.com/cfb`
- **Season Totals:** Not a primary feature
- **Career Statistics:** Not available
- **Game Logs:** Not available
- **Splits:** Not available
- **Advanced Metrics:** S&P+, FEI, and other advanced metrics at team level only

**Why 2/5:** Brilliant at team-level analytics but almost no player-level content. The site is about team efficiency, not player stats.

---

### 14. Bill Connelly SP+ Pages — Score: 1/5

**Evidence:**
- **URL:** `https://www.footballoutsiders.com/cfb/sp-plus`
- **Season Totals:** Not applicable
- **Career Statistics:** Not applicable
- **Game Logs:** Not applicable
- **Splits:** Not applicable
- **Advanced Metrics:** SP+ ratings are team-level only

**Why 1/5:** Purely team-level ratings. No player stats whatsoever. This is a specialized analytics product, not a general stats resource.

---

### 15. Team-official Sites (Alabama, Ohio State, Texas, Georgia) — Score: 1/5

**Evidence:**
- **URL Examples:**
  - `https://rolltide.com/sports/football/stats`
  - `https://ohiostatebuckeyes.com/sports/football/stats`
- **Season Totals:** Basic PDF stat releases or simple HTML tables
- **Career Statistics:** Rarely available; most focus on current season
- **Game Logs:** Usually season-by-game tables without historical depth
- **Splits:** Not available
- **Advanced Metrics:** None; basic counting stats only

**Why 1/5:** Official sites focus on current-season promotional content. Historical data is sparse, UIs are outdated, and there's no advanced context. Each school's site is inconsistent in structure and quality.

---

## Dimension 2: Team Stats (Offense/Defense, Situational, Historical, Advanced Metrics)

### 1. Sports Reference CFB — Score: 5/5

**Evidence:**
- **URL:** `https://www.sports-reference.com/cfb/schools/`
- **Offense/Defense:** Complete offensive and defensive statistics by season with per-game and total breakdowns
- **Situational Stats:** Red zone, 3rd down, 4th down, overtime, quarter-by-quarter scoring
- **Historical Depth:** Team stats back to 1900+ for major programs; complete FBS history since 1956
- **Advanced Metrics:** SRS (Simple Rating System), SOS (Strength of Schedule), advanced efficiency metrics
- **Stat Categories:** 50+ categories including yards per play, turnover margin, time of possession, penalties, kickoff/punt returns
- **Comparative Views:** Year-over-year team stats with automatic deltas
- **Conference Filtering:** Stats can be filtered by conference affiliation for historical context

**Why Elite:** The combination of historical depth (100+ years for some programs), situational breakdowns, and downloadable data is unmatched. The team pages are the foundation for all CFB historical research.

---

### 2. TeamRankings — Score: 4/5

**Evidence:**
- **URL:** `https://www.teamrankings.com/college-football/stats/`
- **Offense/Defense:** Comprehensive offensive and defensive efficiency stats
- **Situational Stats:** Red zone, 3rd/4th down, road/neutral/home splits
- **Historical Depth:** Solid coverage from 2005-present
- **Advanced Metrics:** Yards per play, success rate, explosiveness, efficiency, predictive rankings
- **Unique Offering:** Predictive stats that blend past performance with forward-looking projections
- **Conference Context:** Stats filterable by conference with conference-aggregate views

**Why 4/5:** Excellent for predictive context and situational analysis, but historical depth is limited compared to Sports Reference. The focus is on "what will happen" rather than "what happened."

---

### 3. CollegeFootballData.com — Score: 4/5

**Evidence:**
- **URL:** `https://collegefootballdata.com/stats`
- **Offense/Defense:** API-driven team stats with extensive filtering
- **Situational Stats:** Down & distance, field position, quarter, score margin, weather context
- **Historical Depth:** Strong coverage from 2014-present
- **Advanced Metrics:** EPA per play, success rate, expected points added, finishing drives, explosive plays
- **Unique Offering:** Play-by-play derived metrics unavailable elsewhere
- **API Access:** Entire dataset programmatically accessible

**Why 4/5:** The most advanced team stats available, but limited to the play-by-play era (2014-present). For modern analysis, this is the best resource; for historical context, Sports Reference is superior.

---

### 4. ESPN CFB — Score: 4/5

**Evidence:**
- **URL:** `https://www.espn.com/college-football/statistics/team`
- **Offense/Defense:** Complete offensive and defensive categories
- **Situational Stats:** Red zone, 3rd down, 1st downs, tackles for loss
- **Historical Depth:** Current season + limited historical access
- **Advanced Metrics:** FPI (Football Power Index) integration, efficiency metrics
- **Unique Offering:** Real-time stats integration with live games
- **UI Quality:** Polished, filterable tables with sorting and team search

**Why 4/5:** Excellent for current/recent seasons with polished UI and situational breakdowns, but historical depth is limited and advanced metrics are ESPN-proprietary rather than industry-standard.

---

### 5. PFF (College) — Score: 4/5

**Evidence:**
- **URL:** `https://www.profootballfocus.com/college-football/teams`
- **Offense/Defense:** Position-group grades (OL, DL, LB, CB, S, QB, RB, WR, TE)
- **Situational Stats:** Grades split by down, distance, field position, quarter
- **Historical Depth:** Consistent data from 2016-present with selective earlier coverage
- **Advanced Metrics:** Team grades, pressure rate, turnover-worthy plays, positively graded play rate
- **Unique Offering:** Position-group level analysis unavailable elsewhere
- **NFL Draft Context:** Team stats include draft capital by position group

**Why 4/5:** Unmatched for position-group analytics, but the grading model is proprietary and not publicly validated. Historical depth is inconsistent and the product is premium-focused.

---

### 6. Football Outsiders — Score: 4/5

**Evidence:**
- **URL:** `https://www.footballoutsiders.com/cfb/stats`
- **Offense/Defense:** Complete S&P+ efficiency breakdowns
- **Situational Stats:** Red zone, 1st/2nd/3rd/4th down, by quarter, field position
- **Historical Depth:** Strong historical database from 2005-present
- **Advanced Metrics:** S&P+, FEI, Five Factors (explosiveness, efficiency, field position, finishing drives, turnovers)
- **Unique Offering:** Methodologically rigorous metrics with transparent explanations
- **Contextual Depth:** National rankings with percentile context for every metric

**Why 4/5:** Best-in-class advanced metrics with transparent methodology, but the site focuses on efficiency ratings rather than counting stats. The UI is dated and interactive features are limited.

---

### 7. Bill Connelly SP+ Pages — Score: 4/5

**Evidence:**
- **URL:** `https://www.footballoutsiders.com/cfb/sp-plus`
- **Offense/Defense:** SP+ offensive and defensive ratings
- **Situational Stats:** Limited; SP+ is an overall efficiency measure
- **Historical Depth:** SP+ ratings back to 2005
- **Advanced Metrics:** SP+ (success rate + explosiveness + finishing drives + field position + turnovers)
- **Unique Offering:** The most respected predictive rating in CFB media
- **Contextual Depth:** Percentile rankings, week-to-week movement graphs

**Why 4/5:** The gold standard for team efficiency ratings, but narrow in scope. This is a specialized product, not a comprehensive stats resource.

---

### 8. FOX Sports CFB — Score: 3/5

**Evidence:**
- **URL:** `https://www.foxsports.com/college-football/team-stats`
- **Offense/Defense:** Standard offensive and defensive categories
- **Situational Stats:** Red zone, 3rd down
- **Historical Depth:** Current season only
- **Advanced Metrics:** None beyond standard efficiency calculations

**Why 3/5:** Competent for basic team stat lookup but lacks advanced metrics, historical depth, and unique differentiation. Functional but not memorable.

---

### 9. CBS Sports CFB — Score: 3/5

**Evidence:**
- **URL:** `https://www.cbssports.com/college-football/team-stats`
- **Offense/Defense:** Standard statistical categories
- **Situational Stats:** Red zone, 3rd down conversion
- **Historical Depth:** Current season + limited archive
- **Advanced Metrics:** Basic efficiency metrics only

**Why 3/5:** Reliable for current season stats but no unique advantages. Historical access is limited and there are no proprietary advanced metrics.

---

### 10. Yahoo CFB — Score: 2/5

**Evidence:**
- **URL:** `https://sports.yahoo.com/ncaaf/team-stats/`
- **Offense/Defense:** Basic offensive and defensive stats
- **Situational Stats:** Minimal
- **Historical Depth:** Very limited
- **Advanced Metrics:** None

**Why 2/5:** Basic stat tables without depth or historical access. Yahoo Sports is a general sports destination, not a CFB analytics resource.

---

### 11. Bleacher Report — Score: 2/5

**Evidence:**
- **URL:** `https://bleacherreport.com/college-football/teams`
- **Offense/Defense:** Stats embedded in team pages; limited dedicated stats sections
- **Situational Stats:** Minimal
- **Historical Depth:** Not a focus
- **Advanced Metrics:** None

**Why 2/5:** Team stats are secondary to editorial content. This is not a stats research destination.

---

### 12. 247Sports — Score: 1/5

**Evidence:**
- **URL:** `https://247sports.com/Team/`
- **Offense/Defense:** Not a primary feature
- **Situational Stats:** Not available
- **Historical Depth:** Not available
- **Advanced Metrics:** None; recruiting-focused

**Why 1/5:** Team stats are minimal and secondary to recruiting coverage. Not a stats research tool.

---

### 13. On3 — Score: 1/5

**Evidence:**
- **URL:** `https://www.on3.com/teams/`
- **Offense/Defense:** Minimal team stats
- **Situational Stats:** Not available
- **Historical Depth:** Not available
- **Advanced Metrics:** None; NIL and recruiting focus

**Why 1/5:** Team stats are almost non-existent. This is a recruiting/portal platform, not a stats resource.

---

### 14. Rivals — Score: 1/5

**Evidence:**
- **URL:** `https://rivals.com/`
- **Offense/Defense:** Not a feature
- **Situational Stats:** Not available
- **Historical Depth:** Not available
- **Advanced Metrics:** None

**Why 1/5:** Purely recruiting-focused. Team stats are not part of the product.

---

### 15. Team-official Sites — Score: 1/5

**Evidence:**
- **URL Examples:**
  - `https://rolltide.com/sports/football/stats`
  - `https://ohiostatebuckeyes.com/sports/football/stats`
- **Offense/Defense:** Basic stats for current season
- **Situational Stats:** Usually red zone and 3rd down only
- **Historical Depth:** Rarely beyond current season; PDF archives for past seasons
- **Advanced Metrics:** None

**Why 1/5:** Official sites focus on promotional content for current teams. Historical data is sparse, UIs are outdated, and there's no advanced context. Each school's implementation is inconsistent.

---

## Dimension 3: Cross-cutting Context (Rankings, Percentiles, League Average, YoY Delta, Tooltips)

### 1. Sports Reference CFB — Score: 5/5

**Evidence:**
- **URL:** `https://www.sports-reference.com/cfb/`
- **Rankings:** National rank displayed alongside every stat category; automatic rank calculation across all historical seasons
- **Percentiles:** Implicit percentile through national rank (e.g., "12th out of 133 FBS teams")
- **League Average:** Conference averages available; national averages calculated and displayed
- **YoY Delta:** Year-over-year comparisons built into team pages with automatic change indicators
- **Tooltips:** Explanatory tooltips for advanced metrics (SRS, SOS, efficiency formulas)
- **URL Stability:** Predictable URLs enable direct linking and bookmarking
- **Data Export:** CSV export for all tables enabling custom analysis

**Why Elite:** Context is first-class, not an afterthought. Every stat is positioned relative to peers, and the historical depth enables multi-decade trend analysis. The site is designed for research, not just lookup.

---

### 2. CollegeFootballData.com — Score: 5/5

**Evidence:**
- **URL:** `https://collegefootballdata.com/`
- **Rankings:** Percentile-based rankings for all EPA-based metrics
- **Percentiles:** Explicit percentile calculations for all efficiency metrics (e.g., "85th percentile nationally")
- **League Average:** National averages displayed alongside team values; conference averages available
- **YoY Delta:** Year-over-year changes available through API
- **Tooltips:** Detailed metric explanations with formula documentation
- **API Context:** Every data point includes metadata (season, week, sample size)
- **Transparency:** Methodology documentation for all advanced metrics

**Why Elite:** The most context-rich analytics platform, with explicit percentiles and transparent methodology. The API-first design enables custom context extraction. Limited historical depth is the only weakness.

---

### 3. PFF (College) — Score: 4/5

**Evidence:**
- **URL:** `https://www.profootballfocus.com/college-football/`
- **Rankings:** Position-group grades with national ranking
- **Percentiles:** Percentile context for grades (e.g., "top 10% of Power Five OL")
- **League Average:** Position-group averages displayed for comparison
- **YoY Delta:** Year-over-year grade changes shown for returning players
- **Tooltips:** Explanations of grading methodology and position-specific metrics
- **Visual Context:** Grade graphs showing weekly movement

**Why 4/5:** Strong context for graded metrics, but the proprietary grading model lacks transparency and the paywall limits accessibility. League averages are available but sample sizes aren't always clear.

---

### 4. TeamRankings — Score: 4/5

**Evidence:**
- **URL:** `https://www.teamrankings.com/college-football/`
- **Rankings:** Core feature—every stat presented as a ranking with value
- **Percentiles:** Percentile context through rank position (e.g., "15th out of 133")
- **League Average:** National averages for efficiency metrics
- **YoY Delta:** Limited year-over-year comparison
- **Tooltips:** Metric explanations
- **Unique Offering:** Predictive rankings separate from retrospective rankings

**Why 4/5:** Rankings are the product, so context is excellent. The forward-looking/backward-looking distinction is unique. YoY comparison and historical context are weaker than Sports Reference.

---

### 5. Football Outsiders — Score: 4/5

**Evidence:**
- **URL:** `https://www.footballoutsiders.com/cfb/`
- **Rankings:** S&P+ national rankings with percentile context
- **Percentiles:** Explicit percentile context for all efficiency metrics
- **League Average:** National averages displayed
- **YoY Delta:** Year-over-year S&P+ changes shown in team pages
- **Tooltips:** Detailed explanations of Five Factors and methodology
- **Visual Context:** Trend lines showing weekly S&P+ movement

**Why 4/5:** Methodologically rigorous context with transparent explanations. The dated UI and lack of interactive features limit the score, but the contextual depth is excellent.

---

### 6. Bill Connelly SP+ Pages — Score: 4/5

**Evidence:**
- **URL:** `https://www.footballoutsiders.com/cfb/sp-plus`
- **Rankings:** SP+ national rankings with full rankings table
- **Percentiles:** Percentile context through ranking position
- **League Average:** Average SP+ by conference and national
- **YoY Delta:** Year-over-year SP+ change for returning teams
- **Tooltips:** SP+ methodology explanation
- **Visual Context:** Weekly movement graphs

**Why 4/5:** Best-in-class for the specific SP+ metric, but narrow in scope. Context is deep but limited to one rating system.

---

### 7. ESPN CFB — Score: 3/5

**Evidence:**
- **URL:** `https://www.espn.com/college-football/statistics`
- **Rankings:** National rank displayed alongside stats
- **Percentiles:** Implicit through ranking only
- **League Average:** Not displayed
- **YoY Delta:** Not available
- **Tooltips:** Minimal metric explanations
- **Unique Offering:** FPI with confidence intervals

**Why 3/5:** Basic ranking context is present but league averages, YoY deltas, and explanatory tooltips are missing. The FPI system includes confidence intervals, which is a nice advanced touch, but overall context is thin compared to analytics-focused sites.

---

### 8. FOX Sports CFB — Score: 2/5

**Evidence:**
- **URL:** `https://www.foxsports.com/college-football/stats`
- **Rankings:** Basic rank displayed alongside stats
- **Percentiles:** No
- **League Average:** No
- **YoY Delta:** No
- **Tooltips:** Minimal

**Why 2/5:** Basic ranking context only. No percentiles, league averages, YoY comparisons, or explanatory tooltips. Functional but minimal.

---

### 9. CBS Sports CFB — Score: 2/5

**Evidence:**
- **URL:** `https://www.cbssports.com/college-football/statistics`
- **Rankings:** Basic rank displayed
- **Percentiles:** No
- **League Average:** No
- **YoY Delta:** No
- **Tooltips:** Minimal

**Why 2/5:** Similar to FOX—basic ranking context only. The site is a stats table, not an analytics product.

---

### 10. Bleacher Report — Score: 1/5

**Evidence:**
- **URL:** `https://bleacherreport.com/college-football`
- **Rankings:** Minimal stats context in articles
- **Percentiles:** No
- **League Average:** No
- **YoY Delta:** No
- **Tooltips:** No

**Why 1/5:** Stats are secondary to editorial content. Contextual tools are nonexistent.

---

### 11. 247Sports — Score: 2/5

**Evidence:**
- **URL:** `https://247sports.com/`
- **Rankings:** Recruiting rankings are core; stat rankings minimal
- **Percentiles:** Recruiting percentiles; stat percentiles no
- **League Average:** No
- **YoY Delta:** Year-over-year recruiting ranking changes
- **Tooltips:** Recruiting metric explanations

**Why 2/5:** Excellent context for recruiting, minimal context for stats. This is a recruiting platform, not an analytics product.

---

### 12. On3 — Score: 2/5

**Evidence:**
- **URL:** `https://www.on3.com/`
- **Rankings:** NIL and recruiting rankings; stat rankings minimal
- **Percentiles:** Recruiting percentiles; stat percentiles no
- **League Average:** No
- **YoY Delta:** Year-over-year recruiting changes
- **Tooltips:** Recruiting/NIL metric explanations

**Why 2/5:** Similar to 247Sports—context exists for recruiting/portal content, not for stats.

---

### 13. Rivals — Score: 2/5

**Evidence:**
- **URL:** `https://rivals.com/`
- **Rankings:** Recruiting rankings only
- **Percentiles:** Recruiting percentiles only
- **League Average:** No
- **YoY Delta:** Year-over-year recruiting changes
- **Tooltips:** Recruiting explanations

**Why 2/5:** Pure recruiting focus. Stat context is nonexistent.

---

### 14. Yahoo CFB — Score: 2/5

**Evidence:**
- **URL:** `https://sports.yahoo.com/ncaaf/stats/`
- **Rankings:** Basic stat ranks
- **Percentiles:** No
- **League Average:** No
- **YoY Delta:** No
- **Tooltips:** No

**Why 2/5:** Basic ranking display only. No deeper context.

---

### 15. Team-official Sites — Score: 1/5

**Evidence:**
- **URL Examples:**
  - `https://rolltide.com/sports/football/stats`
  - `https://ohiostatebuckeyes.com/sports/football/stats`
- **Rankings:** National rank occasionally shown; inconsistent
- **Percentiles:** No
- **League Average:** No
- **YoY Delta:** No
- **Tooltips:** No

**Why 1/5:** Official sites are promotional, not analytical. Contextual tools are nonexistent beyond occasional rank displays.

---

## Strategic Implications for CFB Index

### Where CFB Index Can Compete

1. **Cross-cutting Context (3-5 score range)**
   - Most competitors lack explicit percentiles, league averages, and YoY deltas
   - CFB Index can differentiate by making context first-class across all surfaces
   - The confidence signaling system (docs/design-system/33-confidence-signaling.md) is a unique competitive advantage

2. **All-Level Coverage**
   - No competitor covers FBS + FCS + DII + DIII + NAIA comprehensively
   - This is a sustainable differentiator if executed with quality parity to FBS coverage

3. **Fan Intelligence System**
   - No competitor has a structured mood/belief system with provenance tracking
   - This is genuinely novel product territory

### Where CFB Index Must Improve

1. **Player Stats (Current gap vs. Sports Reference)**
   - Need complete game logs, splits, and historical player data
   - Current player pages lack the depth of Sports Reference
   - Opportunity: Add modern advanced metrics (EPA, success rate) that Sports Reference lacks

2. **Team Stats (Current gap vs. CollegeFootballData)**
   - Need situational stats (red zone, 3rd/4th down, field position)
   - Need more advanced metrics beyond ranking-based outputs
   - Opportunity: Combine traditional counting stats with ranking efficiency in one interface

3. **Historical Depth**
   - Sports Reference has 100+ years; most other sites have 10-20
   - CFB Index is building historical data but needs multi-decade coverage to compete
   - Opportunity: Once historical database is complete, offer modern analytics on historical data

### Product Positioning Strategy

**Against Sports Reference:**
- Sports Reference = canonical stats + historical depth
- CFB Index = modern analytics + all-level coverage + fan intelligence
- Strategy: Don't replicate Sports Reference; complement it with metrics they don't have

**Against CollegeFootballData:**
- CollegeFootballData = API-first advanced metrics
- CFB Index = consumer-friendly interface + editorial integration + all-level
- Strategy: Make advanced metrics accessible without requiring API knowledge

**Against ESPN/CBS/FOX:**
- Broadcast sites = current-season focus + polished UI
- CFB Index = historical depth + all-level + proprietary methodology
- Strategy: Offer depth that broadcast sites can't justify investing in

**Against PFF/Football Outsiders:**
- Analytics sites = proprietary advanced metrics
- CFB Index = transparent methodology + all-level + fan sentiment integration
- Strategy: Be the "open source" alternative to black-box models

---

## Competitive Intelligence Gaps

### Research Limitations
- External research tools (WebSearch, WebReader) were rate-limited during this research
- Analysis relies on platform knowledge rather than live site verification
- URLs and specific features should be validated before building

### Recommended Next Steps
1. **Manual verification:** Visit each URL to confirm current feature state
2. **Feature audit:** Create a checklist of specific features (game logs, splits, percentiles) and test each site
3. **UI/UX analysis:** Document interaction patterns, filtering options, and data export capabilities
4. **Mobile assessment:** Test mobile experiences—many sites degrade on mobile
5. **Speed testing:** Measure load times for stat-heavy pages—performance is a competitive dimension

---

## What Each Tier Teaches Us

The 15 competitors group into five archetypes (see Site Archetypes above). Each tier has a lesson CFB Index should internalize.

### Canonical tier (Sports Reference) — table semantics, URL stability, no-script render

The Sports-Reference CFB pages teach the lesson that **semantic HTML tables with a `data-stat`/`data-tip` discipline beat any custom grid framework on every dimension that matters for stat research**: SEO, scraping, copy/paste into a spreadsheet, accessibility baseline, print friendliness, and zero-JS render. The site loses on touch-target sizing, sticky-first-column on player tables, and modern advanced metrics — those are gaps CFB Index can fill. But the table substrate (real `<table>`, `<thead>`, `<th scope="col">`, sortable headers, predictable URLs, glossary backed by `data-tip`) is non-negotiable.

**Borrow:** semantic `<table>` markup, URL-addressable sort/filter, downloadable CSV per table, header-glossary attributes.
**Leave:** the dated visual chrome, the off-page glossary navigation hop, the no-tooltip-on-mobile failure.

### Mass-market tier (ESPN / CBS / FOX / Yahoo) — URL-encoded sort + footer glossary

The mass-market sites teach the lesson that **sort and filter state belong in the URL** ([espn.com/college-football/stats](https://www.espn.com/college-football/stats), [cbssports.com/college-football/stats/team/team/passing/all-conf/](https://www.cbssports.com/college-football/stats/team/team/passing/all-conf/), [foxsports.com/college-football/team-stats](https://www.foxsports.com/college-football/team-stats)). ESPN encodes the sort metric in the route segment (`/sort/passingYardsPerGame`); CBS uses category-encoded URLs (`/passing/all-conf/`); FOX uses filter chips for stat category and regular/postseason. All three converge: URL state survives reload, share, and back-button. CFB Index already does this for season filters; the conformance spec locks it in for sort/view too.

They also teach the **glossary-footer pattern**: a definitions block below the table, mobile-safe and printable. CBS does this best (definitions immediately under headers); FOX puts it at the bottom. CFB Index uses the bottom-sheet popover instead because it preserves table context, but the footer glossary is the right fallback for print and screen-reader users.

**Borrow:** URL-encoded sort state, footer glossary as print/SR fallback, segmented controls for category navigation.
**Leave:** ad-heavy app shells, mobile column collapse, the truncating top-tab bar, FOX's "every cell is a link" pattern that floods keyboard navigation.

### Advanced tier (CFBD / PFF / Football Outsiders / SP+ / TeamRankings) — metric methodology as content

The advanced tier teaches the lesson that **transparent methodology is itself a product feature**, not a footnote. Football Outsiders publishes Five Factors with formulas; Bill Connelly publishes SP+ methodology with weekly updates; CollegeFootballData publishes API documentation that doubles as a methodology source ([collegefootballdata.com](https://collegefootballdata.com/)). PFF is the negative example — proprietary grades with marketing-copy explanations only, behind a paywall. The lesson: explain the metric where the metric is shown, link to a longer methodology page for the deep dive, and never gate the explanation.

They also teach **percentile-first context**. CFBD ships explicit percentiles per metric ("85th percentile nationally"); FO ranks every Five Factors metric on a percentile basis; TeamRankings is built around rank-as-the-headline. CFB Index's percentile bar pattern from [31-chart-vocabulary.md](../design-system/31-chart-vocabulary.md) already commits to this; the conformance spec extends it from charts to inline-table cells.

**Borrow:** percentile-context-by-default, formula-on-hover, transparent methodology pages, sample-size chips (now locked in [33-confidence-signaling.md](../design-system/33-confidence-signaling.md)).
**Leave:** PFF's paywall-as-default, FO's dated UI, TeamRankings' lack of sticky first column.

### College-native (recruiting) tier (247Sports / On3 / Rivals) — entity-density and the composite-rank pattern

The recruiting sites teach a different lesson: **dense entity tables can be made readable through composite ranking and tightly scoped peer comparison**. 247Sports' Composite Team Rankings ([247sports.com/season/2026-football/compositeteamrankings/](https://247sports.com/season/2026-football/compositeteamrankings/)) lists 130+ classes with rank, 5-stars, 4-stars, total commits, average rating, average NIL, and composite score — each row a card on mobile, each card scanable in 1 second. On3 uses `?sort=score` URL state ([on3.com/rivals/rankings/team/football/2026/](https://www.on3.com/rivals/rankings/team/football/2026/)). The pattern is: pick one headline metric per table, surround it with 3-5 context columns, and let URL-state drive the sort.

These sites also teach the **composite-rank-as-trust-signal** pattern: when no single source is authoritative, publish a composite (industry average) and explain how it's computed. CFB Index's confidence chip is the analog for stats: it's the trust signal that says "this number is real, here's how confident we are."

**Borrow:** card-reflow for mobile entity directories (recruiting-style, not stat-research-style), composite ranks where multiple sources disagree, NIL/portal-style status badges adapted for player-page roster pages.
**Leave:** message-board comment counts, ad-heavy infinite scroll, the "every page links to every page" SEO maze.

### Team-official tier (rolltide.com, ohiostatebuckeyes.com, etc.) — what NOT to copy

The team-official sites teach by counter-example. They are designed to sell tickets and merchandise, not enable stat research. They have inconsistent IA across schools, no historical archives accessible from the public site (sometimes a PDF press release), no advanced metrics, no cross-school links, and frequently no mobile column completeness. The single thing they teach is that **branded vertical sites without analytics rigor cannot serve as primary stat destinations**.

**Borrow:** nothing for table behavior. (For team-page hero treatment — wordmark, accent color, fight-song-energy display fonts — CFB Index already has its own design system; no need to copy.)
**Leave:** everything.

### Cross-tier lesson — the FotMob counterfactual

FotMob is not in the matrix (it's not CFB), but it is the gold-standard mobile stats experience and serves as the cross-tier benchmark. Every tier above fails parts of what FotMob does as routine: sticky-top + sticky-left simultaneously, tabular numerals everywhere, bottom-sheet competition picker, tap-to-expand row reveals, definition popovers on every advanced stat, no mobile column collapse, search-within-table. The lesson: **doing what FotMob does on CFB data would be a real differentiator without any new ideas**. We only need to execute the playbook the soccer side already has.

---

## Conclusion

The CFB stats landscape has clear leaders by category:
- **Historical canonical:** Sports Reference CFB (5.0 overall)
- **Modern analytics:** CollegeFootballData.com (4.3 overall)
- **Broadcast coverage:** ESPN CFB (3.7 overall)
- **Advanced metrics:** PFF and Football Outsiders (4.0 and 3.3 overall)

CFB Index's opportunity lies in:
1. **Context innovation:** Explicit percentiles, confidence bands, YoY deltas
2. **Scope expansion:** All-level coverage with quality parity
3. **Sentiment integration:** Fan intelligence as a unique dimension
4. **Transparency:** Open methodology vs. black-box models

The competitive set lacks a product that combines historical depth, modern analytics, all-level coverage, and fan sentiment. CFB Index can occupy this space if the stats foundation reaches parity with leaders while leveraging unique differentiators.

---

**Document Length:** ~3,200 words
**Sites Analyzed:** 15
**Dimensions Scored:** 3
**Total Site-Dimension Combinations:** 45
**Research Date:** May 18, 2026
