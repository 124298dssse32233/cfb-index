# CFB Stats Display Conformance Specification

**Date:** May 18, 2026  
**Purpose:** Canonical column/abbreviation/splits/historical/advanced vocabulary for CFB Index  
**Status:** Locked reference for player/team page implementation

---

## Executive Summary

This specification defines the **table-stakes baseline** for CFB Index stats display. Where major CFB sites agree, CFB Index must agree. Where they disagree, this spec picks the clearest convention. Where all competitors fail (notably mobile), CFB Index quietly does better.

**Core Principles:**
1. **Conformance over innovation** — Stats display is a place to not lose, not differentiate
2. **Fan-first abbreviations** — `CMP` not `Cmp`, `YDS` not `Yds`, `Y/A` not `AVG`
3. **Context with every number** — Rank, percentile, or cohort alongside raw values
4. **Mobile as the primary constraint** — Every table works at 390px viewport width
5. **Semantic HTML tables** — Real `<table>` elements, not div grids

**Design System Reconciliation:**
- All stats use `font-variant-numeric: tabular-nums` per `00-tokens.md`
- Percentile displays use red→grey→blue ramp per `31-chart-vocabulary.md`
- Confidence chips per `33-confidence-signaling.md` on all sample-dependent metrics
- Profile archetype per `30-page-archetypes.md` for player/team pages

---

## 1. Canonical Column Sequences

### 1.1 Player Passing — Standard Table

**Canonical order:** `Player | Team | POS | GP | CMP | ATT | CMP% | YDS | Y/A | LNG | TD | INT | SACK | RATE`

| Column | Header | Align | Definition | First Encounter Tooltip |
|--------|--------|-------|------------|------------------------|
| Player | Name | left | Full name with position badge | Link to player page |
| Team | Team | left | Team wordmark or abbreviated name | Link to team page |
| POS | Pos | center | Position abbreviation (QB/RB/WR/TE) | Position |
| GP | GP | center | Games Played | Games played this season |
| CMP | Cmp | center | Completions | Completed passes |
| ATT | Att | center | Attempts | Pass attempts |
| CMP% | CMP% | center | Completion Percentage | Completions divided by attempts |
| YDS | Yds | right | Passing Yards | Total passing yards |
| Y/A | Y/A | right | Yards per Attempt | Yards per pass attempt |
| LNG |Lng | center | Longest Completion | Longest pass play this season |
| TD | TD | center | Touchdown Passes | Touchdown passes thrown |
| INT | Int | center | Interceptions Thrown | Interceptions thrown |
| SACK | Sack | center | Times Sacked | Number of times sacked |
| RATE | Rate | right | NCAA Passer Rating | NCAA efficiency formula (not QBR) |

**Mobile (≤768px):** Hide `POS`, `LNG`, `SACK`. Core display: `Player | Team | GP | CMP | ATT | CMP% | YDS | Y/A | TD | INT | RATE`

**Advanced view (toggle):** Add `AY/A` (Adjusted Yards/Attempt) after `Y/A`, `TD%` and `INT%` before `SACK`

---

### 1.2 Player Rushing — Standard Table

**Canonical order:** `Player | Team | POS | GP | ATT | YDS | Y/A | LNG | TD | Y/G`

| Column | Header | Align | Definition | Tooltip |
|--------|--------|-------|------------|----------|
| Player | Name | left | Full name | Link to player page |
| Team | Team | left | Team wordmark | Link to team page |
| POS | Pos | center | Position (RB/WR/QB/TE) | Position |
| GP | GP | center | Games Played | Games played |
| ATT | Att | center | Rushing Attempts | Rush attempts |
| YDS | Yds | right | Rushing Yards | Total rushing yards |
| Y/A | Y/A | right | Yards per Carry | Yards per rush attempt |
| LNG |Lng | right | Longest Run | Longest rush this season |
| TD | TD | center | Rushing TDs | Rushing touchdowns |
| Y/G | Y/G | right | Yards per Game | Rushing yards per game |

**Mobile:** Hide `POS`, `LNG`. Core: `Player | Team | GP | ATT | YDS | Y/A | TD | Y/G`

---

### 1.3 Player Receiving — Standard Table

**Canonical order:** `Player | Team | POS | GP | REC | YDS | Y/R | LNG | TD | Y/G`

| Column | Header | Align | Definition | Tooltip |
|--------|--------|-------|------------|----------|
| Player | Name | left | Full name | Link to player page |
| Team | Team | left | Team wordmark | Link to team page |
| POS | Pos | center | Position (WR/TE/RB) | Position |
| GP | GP | center | Games Played | Games played |
| REC | Rec | center | Receptions | Pass receptions |
| YDS | Yds | right | Receiving Yards | Total receiving yards |
| Y/R | Y/R | right | Yards per Reception | Yards per catch |
| LNG |Lng | right | Longest Reception | Longest catch this season |
| TD | TD | center | Receiving TDs | Receiving touchdowns |
| Y/G | Y/G | right | Yards per Game | Receiving yards per game |

**Advanced view (toggle):** Add `TGT` (Targets), `CTCH%` (Catch Rate), `YAC` (Yards After Catch)

---

### 1.4 Defensive Line — Standard Table

**Canonical order:** `Player | Team | POS | GP | TKL | SOLO | AST | TFL | SACK | QBH | FF | FR | PD`

| Column | Header | Align | Definition | Tooltip |
|--------|--------|-------|------------|---------|
| Player | Name | left | Full name | Link to player page |
| Team | Team | left | Team wordmark | Link to team page |
| POS | Pos | center | Position (DT/DE/EDGE) | Position |
| GP | GP | center | Games Played | Games played |
| TKL | TKL | right | Total Tackles | SOLO + AST |
| SOLO | Solo | right | Solo Tackles | Unassisted tackles |
| AST | Ast | right | Assisted Tackles | Assists on tackles (half-tackles in NCAA) |
| TFL | TFL | right | Tackles for Loss | Tackles behind LOS |
| SACK | Sack | right | Sacks | Sacks (often listed with -YDS, half-sacks allowed) |
| QBH | QBH | right | QB Hurries / Hits | Pressures that didn't sack (where tracked) |
| FF | FF | center | Forced Fumbles | Strips that caused turnover |
| FR | FR | center | Fumble Recoveries | Recoveries (some sites also show FR-YDS / FR-TD) |
| PD | PD | center | Pass Deflections | Passes broken up at the line |

**Mobile:** `Player | Team | TKL | TFL | SACK | FF`

**Note on convention:** NCAA box scores list `SACK` separately from `TFL` even though a sack is a TFL; Sports-Reference shows both. CFB Index follows the NCAA convention — sacks are reported in their own column AND included in the TFL count. Tooltip on `TFL` must say so.

**Source convergence:** ESPN defensive leader tables expose `TOT / SOLO / AST / SACK / SACK-YDS / TFL / PD / INT / FF / FR` ([espn.com/college-football/stats/player](https://www.espn.com/college-football/stats/player)); Sports-Reference mirrors the structure with longer column lists. Convention is stable across sites.

---

### 1.5 Linebackers — Standard Table

**Canonical order:** `Player | Team | POS | GP | TKL | SOLO | AST | TFL | SACK | INT | PD | FF | FR`

Same column semantics as DL, but `INT` and `PD` move up because LBs operate in coverage more often than DL.

**Mobile:** `Player | Team | TKL | TFL | SACK | INT | PD`

---

### 1.6 Defensive Backs — Standard Table

**Canonical order:** `Player | Team | POS | GP | TKL | SOLO | AST | INT | INT-YDS | INT-TD | PD | PASS DEF | FF | FR`

| Column | Header | Align | Definition | Tooltip |
|--------|--------|-------|------------|---------|
| INT | INT | right | Interceptions | Picks |
| INT-YDS | INT Yds | right | Interception Return Yards | Return yards from INTs |
| INT-TD | INT TD | center | Pick-Sixes | INTs returned for TD |
| PD | PD | right | Pass Deflections | Passes broken up |
| PASS DEF | Pass Def | right | Total Passes Defended | INT + PD (NCAA's "passes defended") |
| TKL | TKL | right | Total Tackles | SOLO + AST |

**Mobile:** `Player | Team | TKL | INT | PD | PASS DEF`

**Source note:** Sports-Reference defensive tables organize as `Solo | Ast | Tot | Loss | Sk | Int | Yds | Avg | TD | PD | FR | Yds | TD | FF`. The `PASS DEF` summary (INT + PD) is an NCAA staple ([ncaa.com/stats/football/fbs](https://www.ncaa.com/stats/football/fbs)) that ESPN omits; CFB Index includes it because fans expect it from the official NCAA convention.

---

### 1.7 Kickers — Standard Table

**Canonical order:** `Player | Team | GP | FGM | FGA | FG% | LNG | 0-19 | 20-29 | 30-39 | 40-49 | 50+ | XPM | XPA | XP% | PTS`

| Column | Header | Align | Definition | Tooltip |
|--------|--------|-------|------------|---------|
| FGM | FGM | right | Field Goals Made | Field goals made |
| FGA | FGA | right | Field Goals Attempted | Field goals attempted |
| FG% | FG% | right | Field Goal Percentage | FGM ÷ FGA |
| LNG | Lng | right | Longest FG Made | Career or season longest |
| 0-19 / 20-29 / 30-39 / 40-49 / 50+ | range | center | Range buckets | Made/Attempted in distance bucket, e.g. `4/5` |
| XPM / XPA | XPM / XPA | right | Extra Points Made / Attempted | Routine for ESPN/CBS |
| XP% | XP% | right | Extra Point Percentage | XPM ÷ XPA |
| PTS | Pts | right | Total Points Scored | 3 × FGM + 1 × XPM |

**Mobile:** `Player | Team | FGM/FGA | FG% | LNG | PTS`

**Range bucket convention:** Display as `made/attempted` strings (`4/5`) rather than two columns per bucket — Sports-Reference does this and the density is appropriate.

---

### 1.8 Punters — Standard Table

**Canonical order:** `Player | Team | GP | PUNTS | YDS | AVG | NET | LNG | TB | I20 | FC | BLK`

| Column | Header | Align | Definition | Tooltip |
|--------|--------|-------|------------|---------|
| PUNTS | Punts | right | Total Punts | |
| YDS | Yds | right | Gross Punting Yards | Sum of gross yardage |
| AVG | Avg | right | Yards per Punt (gross) | Gross YDS ÷ PUNTS — acceptable here; pure punting context |
| NET | Net | right | Net Average | Net of return + touchback |
| LNG | Lng | right | Longest Punt | |
| TB | TB | center | Touchbacks | Punts ending in the end zone |
| I20 | In20 | center | Inside the 20 | Punts downed inside opponent 20 |
| FC | FC | center | Fair Catches Forced | Fair-catch return count |
| BLK | Blk | center | Punts Blocked | Blocked punts |

**Mobile:** `Player | Team | PUNTS | AVG | NET | I20`

**`AVG` use here is permitted** because the table is unambiguously punting — no risk of overloading with rush/receive averages.

---

### 1.9 Returners — Standard Table

**Canonical order:** `Player | Team | GP | KR | KR-YDS | KR-AVG | KR-LNG | KR-TD | PR | PR-YDS | PR-AVG | PR-LNG | PR-TD`

Use prefixes (`KR-` / `PR-`) when kick and punt returns appear in the same table; drop the prefix when the table is single-discipline.

**Mobile:** `Player | Team | KR-AVG | KR-TD | PR-AVG | PR-TD`

---

### 1.10 Team Offense — Standard Table

**Canonical order:** `Team | Conf | GP | PTS | PTS/G | YDS | YDS/G | Plays | Y/P | Pass YDS | Pass Y/G | Rush YDS | Rush Y/G | 1stD | 3D% | 4D% | RZ% | TO`

| Column | Header | Align | Definition | Tooltip |
|--------|--------|-------|------------|----------|
| Team | Team | left | Team name | Link to team page |
| Conf | Conf | center | Conference | Conference affiliation |
| GP | GP | center | Games Played | Games played |
| PTS | Pts | right | Points Scored | Total points |
| PTS/G |Pts/G | right | Points per Game | Points scored per game |
| YDS | Yds | right | Total Yards | Total offense yards |
| YDS/G |Yds/G | right | Yards per Game | Yards per game |
| Plays |Pl | center | Offensive Plays | Total offensive snaps |
| Y/P | Y/P | right | Yards per Play | Yards per offensive play |
| Pass YDS|Pass| right | Passing Yards | Total passing yards |
| Pass Y/G|P/G | right | Pass Yards per Game| Passing yards per game |
| Rush YDS|Rush| right | Rushing Yards | Total rushing yards |
| Rush Y/G|R/G | right | Rush Yards per Game| Rushing yards per game |
| 1stD | 1st | center | First Downs | Total first downs |
| 3D% | 3rd% | center | 3rd Down % | 3rd down conversion rate |
| 4D% | 4th% | center | 4th Down % | 4th down conversion rate |
| RZ% | RZ% | center | Red Zone % | Red zone TD rate |
| TO | TO | center | Turnovers | Total turnovers lost |

**Team Defense — Mirror Table**
Same columns with clear "Allowed" labeling: `PTS Allowed`, `YDS Allowed`, `YDS/G Allowed`, `Opp 3D%`, etc.

**Mobile:** Collapse to `Team | Conf | GP | PTS/G | YDS/G | Y/P | 3D% | RZ%`

**Source convergence:** CBS Sports total team table is `Team | GP | YDS | YDS/G | Pass YDS | Pass Y/G | Rush YDS | Rush Y/G | PTS | PTS/G` ([cbssports.com/college-football/stats/team/team/passing/all-conf/](https://www.cbssports.com/college-football/stats/team/team/passing/all-conf/)); ESPN exposes the same shape with sortable header links and category tabs ([espn.com/college-football/stats/team/\_/stat/passing](https://www.espn.com/college-football/stats/team/_/stat/passing)); FOX adds postseason filtering and a glossary footer ([foxsports.com/college-football/team-stats](https://www.foxsports.com/college-football/team-stats)). Sports-Reference team pages add a `SRS` column for strength-of-schedule context — CFB Index will omit `SRS` from the canonical table (replace with our own model rank chip).

---

### 1.11 Team Special Teams — Standard Table

**Canonical order:** `Team | Conf | GP | FG% | FG-LNG | XP% | KR-AVG | PR-AVG | NET PUNT | TB% | PUNT BLK | KICK BLK | RET TD`

**Why a separate table:** Special teams stats don't cluster cleanly with offense or defense. The expectation across NCAA / ESPN / Sports-Reference is that they live in their own page tab. CFB Index follows the same convention.

**Mobile:** `Team | Conf | FG% | NET PUNT | RET TD`

---

### 1.12 Team Situational — Standard Table

This is the "splits as a table" view: each row is the same team, each column a situation.

**Canonical order:** `Situation | PLAYS | YDS | Y/P | TD | 3D% | RZ TD%`

Rows include: `All`, `1st Down`, `2nd & Short`, `2nd & Long`, `3rd & Short`, `3rd & Medium`, `3rd & Long`, `4th Down`, `Red Zone`, `Goal-to-Go`, `2-Minute Drill`, `Leading`, `Trailing`, `Tied`.

**Source convergence:** Football Outsiders and CollegeFootballData both expose this shape (situation in rows, metric in columns) for advanced consumers ([collegefootballdata.com](https://collegefootballdata.com/)). The mainstream sites (ESPN/CBS) split situations across multiple pages instead — that's a usability cost CFB Index will avoid by putting situation-in-rows on the team page.

---

### 1.13 Abbreviation Dictionary — Canonical Mappings

| Concept | **Canonical** | Alternatives Found | Decision Rationale |
|---------|--------------|-------------------|-------------------|
| Games | `GP` (players), `G` (teams) | G, Games | `GP` unambiguous for players; `G` standard for teams |
| Completions | **`CMP`** | Cmp, Comp, Com | Uppercase clearest; matches ESPN/CBS convention |
| Attempts | **`ATT`** | Att, Attempts | Uppercase clearest; matches ESPN/CBS convention |
| Completion % | **`CMP%`** | PCT, Cmp%, % | `CMP%` encodes denominator; clearer than generic `PCT` |
| Yards | **`YDS`** | Yds, Yards | Uppercase clearest; matches ESPN/CBS over SR |
| Yards/Attempt | **`Y/A`** | AVG, YPA, Yds/A | `Y/A` precise; `AVG` overloaded across contexts |
| Yards/Game | **`YDS/G`** | Y/G, YPG, Yds/G | `YDS/G` self-documenting; `Y/G` for dense tables |
| Longest | **`LNG`** | Long, Lg | `LNG` unambiguous; ESPN convention |
| Touchdowns | **`TD`** | TDs, Touchdown | Universal; no alternative needed |
| Interceptions | **`INT`** | Int, Interceptions | Universal; no alternative needed |
| Rating | **`RATE`** | RTG, Rate, Pass Eff | `RATE` with tooltip: NCAA formula |
| Receptions | **`REC`** | Rec, Receptions, Catches | `REC` unambiguous; matches ESPN/CBS |
| Percent | **`%` suffix** | PCT, pct | Prefer `3D%`, `4D%`, `RZ%` over generic `PCT` |
| Total Tackles | **`TKL`** | TOT, Tackles, T | `TKL` matches ESPN; `TOT` ambiguous |
| Solo Tackles | **`SOLO`** | Solo, ST | `SOLO` clearest |
| Assisted Tackles | **`AST`** | Ast, A | `AST` matches ESPN |
| Tackles for Loss | **`TFL`** | Loss, TL | `TFL` universal in NCAA boxscores |
| Sacks | **`SACK`** | Sk, SACKS | `SACK` matches ESPN/CBS; tooltip notes half-sacks count as 0.5 |
| QB Hurries | **`QBH`** | Hurries, Hits, Pressures | `QBH` where tracked; site-specific |
| Forced Fumbles | **`FF`** | FumF, FFum | `FF` universal |
| Fumble Recoveries | **`FR`** | FumR, FRec | `FR` universal |
| Pass Deflections | **`PD`** | PBU, BrUp | `PD` matches ESPN; `PBU` is NFL convention |
| Passes Defended | **`PASS DEF`** | PD, PassDef | `PASS DEF` for INT+PD summary; NCAA convention |
| Field Goals Made | **`FGM`** | FG, Made | `FGM` matches NCAA/ESPN |
| Field Goals Attempted | **`FGA`** | Att, ATT | `FGA` matches NCAA/ESPN |
| FG Percentage | **`FG%`** | PCT, % | `FG%` encodes denominator |
| Extra Points Made/Attempted | **`XPM` / `XPA`** | PAT, EPM | `XPM/XPA` matches NCAA; avoid `PAT` ambiguity |
| Net Punting Avg | **`NET`** | NETAVG, NA | `NET` clearest |
| Inside the 20 | **`I20`** | In20, Inside20 | `I20` standard punter shorthand |
| Touchbacks | **`TB`** | Tb, TouchBk | `TB` universal |
| Kick Return / Punt Return | **`KR` / `PR`** | KOR, KickRet | `KR/PR` matches ESPN/CBS |

**Critical Rules:**
- Never use `AVG` in mixed tables — `Y/A`, `Y/R`, `Y/P` are precise
- Use uppercase for headers — `CMP` not `Cmp`, `YDS` not `Yds`
- Encode denominator in percentage — `CMP%`, `3D%`, `RZ%` not generic `%`
- `YDS/G` for mainstream UI, `Y/G` acceptable in dense tables

---

## 2. Splits Taxonomy — Table-Stakes vs Advanced

### 2.1 Table-Stakes Splits (Must Have)

These splits are expected on any serious CFB stats page:

| Split Category | Values | Display Context |
|---------------|--------|-----------------|
| **Season** | 2026, 2025, ... | Primary filter on all stat pages |
| **Venue** | Home, Away, Neutral | Player and team pages |
| **Conference** | SEC, B1G, ACC, B12, etc. | Filter on leaderboards |
| **Opponent Quality** | vs Ranked, vs Unranked | Player pages; Heisman context |
| **Game State** | Season, Game Log, Career | Player page navigation |
| **Time Frame** | Regular Season, Postseason | All stat views |
| **Down & Distance** | 3rd Down, 4th Down | Team offense/defense pages |
| **Field Zone** | Red Zone | Team offense/defense pages |

**Implementation:** Use tabbed interface or segmented control for 2-4 values; dropdown for 5+ values.

---

### 2.2 Advanced Splits (Nice to Have)

These splits differentiate premium analytics products:

| Split Category | Values | Display Context |
|---------------|--------|-----------------|
| **By Quarter** | Q1, Q2, Q3, Q4, OT | Advanced player/team pages |
| **By Half** | 1st Half, 2nd Half | Coach/analyst views |
| **Down & Distance** | Short (1-3), Medium (4-6), Long (7+) | Analytics views |
| **Field Position** | Own 1-19, Own 20-39, Midfield, Opp 39-20, Opp 19-1 | Advanced situational |
| **Score Margin** | Leading, Trailing, Tied, Garbage Time | Advanced analytics |
| **Pressure** | Clean Pocket, Under Pressure | PFF-style grades |
| **Play Type** | Play Action, RPO, Standard | Advanced QB analysis |
| **Target Depth** | Short (0-9), Intermediate (10-19), Deep (20+) | Advanced receiving |
| **Month** | August/Sept, Oct, Nov, Dec/Bowl | Historical trends |
| **Weather** | Clear, Rain, Snow, Wind, Dome | Betting/research filters |

**Implementation:** Collapse into "Advanced Splits" drawer or separate analytics tab.

---

## 3. Advanced Stat Presentation

### 3.1 Advanced Stat Display Format

| Metric | Display | Direction | First Encounter Copy |
|--------|---------|-----------|----------------------|
| **EPA/Play** | `+0.18` signed decimal | Higher offense, lower defense | "Expected points added per play; measures scoreboard value of each snap." |
| **Success Rate** | `52.3%` percentage | Higher offense, lower defense | "Share of plays that keep the offense on schedule (50% on 1st, 70% on 2nd, 100% on 3rd/4th)." |
| **Explosiveness** | `+0.45` EPA/success | Higher offense, lower defense | "Average EPA on successful plays; measures big-play capability." |
| **CPOE** | `+4.2%` signed % | Higher QB better | "Completion percentage over expected, adjusted for throw depth and pressure." |
| **QBR** | `77.3` (0-100) | Higher better | "ESPN's total QB contribution metric; includes pass, run, sack, penalty, and situation adjustments." |
| **PFF Grade** | `87.2` (0-100) + snaps | Higher better | "Film-based performance grade per play; 50 is average, 80+ is elite." |
| **AY/A** | `8.4` decimal | Higher better | "Adjusted yards per attempt; folds TD (+20) and INT (-45) value into passing efficiency." |
| **ANY/A** | `7.9` decimal/dropback | Higher better | "Adjusted net yards per attempt; includes sack, TD, INT adjustments. Rare in CFB." |

**Visual Treatment:**
- **Raw value** prominent, **rank/percentile** secondary in parentheses
- **Context badge** for top/bottom quartile (green/red chip per confidence system)
- **Definition on tap/hover** — never assume prior knowledge
- **Sample size chip** per `33-confidence-signaling.md` — e.g., "142 snaps · medium"

---

### 3.2 Percentile Display Conventions

Per `31-chart-vocabulary.md` (Percentile Bar pattern):

**Percentile Bar Format:**
```
PASS YARDS/GAME    87th pct ●━━━━━━━━━━━━━━━━━━━●━━━ vs FBS QBs
RUSH YARDS/GAME    34th pct ━━━━━●━━━━━━━━━━━━━━━━━ vs FBS QBs
RED ZONE TD%       92nd pct ●━━━━━━━━━━━━━━━━━━━━●━ vs FBS QBs
```

**Color Encoding:** Diverging red→grey→blue (Baseball Savant convention; blue = high)
- Inverted for inverted metrics (pressure-to-sack where low is good)

**Required Elements:**
- Stat label (left)
- Percentile value (e.g., "87th pct")
- Horizontal bar with value dot positioned at percentile
- Peer label (right) — e.g., "vs FBS QBs" or "vs P4 teams"
- Sample-size chip (see confidence-signaling doc)

---

## 4. Historical Depth Expectations

### 4.1 Historical Coverage by Site

| Site | Player Data Depth | Team Data Depth | Notes |
|------|-------------------|----------------|-------|
| Sports Reference | 1956-present | 1869-present | Gold standard for historical |
| ESPN | 2004-present | 2004-present | QBR back to 2004 |
| PFF | 2014-present | 2014-present | Grading era only |
| CollegeFootballData | 2014-present | 2014-present | Play-by-play era |
| CFB Index (target) | 2000-present (Phase 1) | 1956-present (Phase 1) | Building historical backfill |

**CFB Index Target:**
- **Phase 1 (v1.0):** Player pages 2000-present; team pages 1956-present
- **Phase 2 (v2.0):** Complete box-score backfill 1995-present
- **Phase 3 (v3.0):** Historical research pre-1956 for major programs

---

### 4.2 Historical Display Formats

**Player Pages:**
- Season-by-season rows (chronological, newest first)
- Career total row at bottom (sticky footer)
- Transfer grouping: rows grouped by school with subtotals
- Side-by-side comparison: select 2-4 players, show seasons in parallel columns

**Team Pages:**
- Year selector dropdown (all available seasons)
- Conference context: stats tagged by conference affiliation for that year
- YoY delta column: show change from previous season (+▲/-▼)
- Historical rank: final AP rank for that season

**Mobile (≤768px):**
- Season rows collapse to accordions (tap to expand full stat line)
- Career totals visible in summary card above table
- Side-by-side comparison becomes vertical stack

---

## 5. Cross-Link Patterns

### 5.1 Row-Level Cross-Links

| Table Type | Link Targets | Implementation |
|------------|-------------|----------------|
| Player passing | Player → player page, Team → team page | Name/team name are links |
| Team stats | Team → team page, Opponent → game page | Team names link; opponent column links to game |
| Game log | Opponent → team page, Date → game page | Opponent name and date are links |
| Leaderboards | All names → player pages | First column linked |

**Touch Target:** Minimum 44×44px per WCAG 2.5.5 AAA. Expand visible link area with padding if needed.

---

### 5.2 Comparison Views

**Player Comparison:**
- Select 2-4 players from same position
- Display side-by-side stat lines
- Highlight leader in each category (bold or color)
- Show differential: +X.X vs. comparison player

**Team Comparison:**
- Select 2-4 teams
- Mirror offense/defense tables
- Side-by-side splits (home/away, conference games)
- Head-to-head historical record

**URL State:** Encode comparison in URL for shareability:
- `/compare/players?id1=123&id2=456`
- `/compare/teams?id1=alabama&id2=georgia&season=2025`

---

## 6. Default Views, Default Sorts, Default Filters

The default state of a table is the strongest opinion the site holds about what the user is here to learn. The wrong defaults waste the most expensive moment in the session: the first impression after the page paints.

### 6.1 Default sort by page type

| Page | Default sort column | Direction | Why |
|------|--------------------|-----------|------|
| Season passing leaders | `YDS` | desc | What every fan came to see; Sports-Reference, ESPN, NCAA agree |
| Season rushing leaders | `YDS` | desc | Same logic |
| Season receiving leaders | `YDS` | desc | Same logic |
| Defensive leaders | `TKL` | desc | The volume primary; advanced view re-sorts by `SACK` or `INT` |
| Team offense leaderboard | `YDS/G` | desc | Per-game normalizes mid-season unevenness — matches ESPN/CBS convention |
| Team defense leaderboard | `YDS/G Allowed` | asc | Lower is better |
| Conference roster | Position-primary stat | desc | NEVER alphabetical (see Anti-Pattern #5) — alphabetical is the DBA default, not the fan default |
| Team page — Schedule | `Date` | asc earliest-first | Reading the season forward |
| Team page — Roster | `Class` then `Pos` | mixed | Conventional roster grouping; secondary sort by primary stat for that position |
| Player page — Season log | `Year` | desc newest-first | Career-tells-story-backwards; career total row stickies at bottom |
| Player page — Game log | `Date` | desc most-recent-first | Reverse-chronological is the convention; reading "what just happened" |
| Wire / Editions archive | `Date` | desc newest-first | News surface; recency is the headline |
| Anniversary | `Year` | asc (or pinned to "today") | Pivot is the date itself |

### 6.2 Default filter by page type

| Page | Default filter state |
|------|---------------------|
| All season leaderboards | Current season; All conferences; FBS only |
| Team offense/defense | Current season; All games (incl. bowl/playoff once played); Regular + Postseason combined |
| Player page | Current season as primary view, "Career" tab adjacent |
| Splits | "All" baseline visible, even when a specific split is selected — so the fan can compare |
| Game log | Current season; All games |
| Recruiting tables | Current cycle; National view; All positions |

**Source convergence:** The pattern of "default to most-common case, expose toggles inline" matches CBS (URL-based defaults), ESPN (route-encoded defaults), and TeamRankings (one-stat-per-page so the URL IS the default). The disagreement is whether to default to FBS only or include FCS — CFB Index follows sports-reference.com/cfb (FBS by default, FCS opt-in via filter).

### 6.3 Default views (named segmented controls)

Every primary stat table offers three named views, in this order:

1. **Standard** — what a fan expects, dense but readable. The canonical column orders in §1.
2. **Advanced** — adds rate stats, efficiency, situational percentages. Always available; never default.
3. **Splits** — re-orders rows from "one row per entity" to "one row per situation." Always available; never default.

**Implementation:** segmented control above the table, persists via `localStorage` (per the FBref pattern). URL fragment captures the view (`#view=advanced`) so deep-links share correctly.

**Anti-pattern to avoid:** per-column checkbox toggles. They're too granular for the median fan and they're how PFF makes tables intimidating. Three curated views is the maximum surface area.

### 6.4 URL state contract

Every filter, sort, and view choice must be encoded in the URL. The contract:

```
/<entity>/<id>/?season=2026&split=home&view=advanced&sort=yds&dir=desc
```

- `season` — 4-digit year
- `split` — slug from the splits taxonomy (§2)
- `view` — `standard | advanced | splits`
- `sort` — abbreviation token from §1.13
- `dir` — `asc | desc`

URL drives the table state; the table never updates without a corresponding URL change. This is the static-site equivalent of ESPN's `/sort/passingYardsPerGame` route encoding.

**EXTENDS the locked system.** The URL state contract is new but doesn't conflict with any design-system rule; it slots underneath the Profile and Database archetypes ([30-page-archetypes.md](../design-system/30-page-archetypes.md)).

---

## 7. Tooltip / Definition Behavior Baseline

Every advanced or non-obvious stat column carries a tooltip. The four sites do this four different ways; CFB Index picks one.

### 7.1 Convergence and divergence

| Site | Tooltip behavior | Mobile behavior |
|------|------------------|----------------|
| Sports-Reference | `data-tip` attribute on `<th>`; hover-revealed on desktop; mobile fallback inconsistent | Often broken on touch |
| ESPN | Glossary block below the table, not header-attached | Works on mobile but breaks context |
| CBS Sports | Inline definitions row directly under headers ("GP Games played, ATT Pass Attempts…") | Works on mobile; harms density |
| FOX Sports | Glossary footer below table | Works on mobile but breaks context |
| PFF | Header hover tooltip only | Broken on touch (Anti-Pattern #11) |
| FotMob (non-CFB) | Tap-triggered bottom sheet | Works everywhere |

### 7.2 CFB Index baseline (composite of best-in-class)

Every advanced or non-obvious column header is a tap target. Tap (or hover, on desktop) opens a popover containing:

1. **Full name** (not abbreviated): "Adjusted Yards per Attempt"
2. **One-sentence plain-English definition**: "Yards per pass attempt, with bonus credit for TDs and a heavy penalty for INTs."
3. **Formula in monospace**: `(YDS + 20·TD − 45·INT) / ATT`
4. **Benchmark line**: "Top 10% of FBS QBs in 2025 are above 9.0."
5. **Link to methodology**: `/methodology/glossary#ayoa`

**Sourcing convention:** the popover content lives in a single glossary table keyed by the canonical abbreviation token (§1.13). One source of truth, no drift across pages.

**Mobile:** the popover renders as a bottom sheet (per FotMob convention). Tap a column header → sheet slides up with the same content. One-tap dismiss restores the table.

**Desktop:** popover anchored to the `<th>`, 200ms hover delay, click also opens (so power users get fast hover and tablet users get tap-equivalent).

**Print stylesheet:** all tooltips expanded inline below the table caption — no hover dependency.

**Accessibility:** `<button>` inside the `<th>`, not a div with click handlers. `aria-describedby` references the popover content. Focus-visible ring matches design system token.

### 7.3 What does NOT need a tooltip

Basic counting stats (`YDS`, `TD`, `INT`, `GP`, `REC`, `ATT`, `CMP`) do not need tooltips — they're table stakes and a tooltip on every column would dilute the signal. The rule: if the abbreviation is in the §1.13 dictionary AND the concept is genuinely universal (a 13-year-old fan would know it), no tooltip. Everything else gets one.

### 7.4 Definition density

A modern CFB stats table should not exceed **5 unfamiliar abbreviations** without an above-the-fold "what these mean" affordance. The two satisfactory affordances:

- A segmented control to toggle between Standard (familiar columns only) and Advanced (adds rate stats).
- A persistent "Glossary" disclosure pinned below the table that expands inline.

PFF fails this test routinely (15+ advanced abbreviations on a single page with no help). CFB Index will not.

**EXTENDS the locked system.** Tooltip pattern is additive to design tokens; tooltip CSS reads from existing color and stroke tokens; the bottom-sheet pattern is documented in the Mobile Playbook deliverable.

---

## 8. Reconciliation with Locked Design System

### 6.1 Extends the Locked System (Additive, No Coordination)

| Finding | Design System Extension |
|---------|------------------------|
| Canonical column sequences | New `stats-table` component in team_pages module |
| Abbreviation dictionary | Extension to `00-tokens.md` (stats-abbreviations.css) |
| Splits taxonomy | New splits filter component (segmented control) |
| Advanced stat definitions | New tooltip/bottom-sheet pattern for metrics |
| Historical depth guidance | Informs data pipeline priorities |

### 6.2 Challenges the Locked System (Requires Window A/B Coordination)

| Finding | Conflict | Resolution Needed |
|---------|----------|-------------------|
| Mobile table behavior | `30-page-archetypes.md` assumes Profile archetype but no table pattern | Update archetype spec with table behavior |
| Percentile bar placement | `31-chart-vocabulary.md` defines percentile bar but not in tables | Clarify inline percentile bar treatment |
| Print stylesheet | Design system mentions print but no table-specific rules | Add `@media print` rules for tables |

### 6.3 Out-of-Scope for Locked Contracts

| Finding | Rationale |
|---------|-----------|
| API endpoints for splits | Technical implementation, not display contract |
| Database schema for historical data | Backend concern, not frontend spec |
| Performance budget targets | Already in design system; no conflict |
| Accessibility compliance | Already required by design system |

---

## 9. Implementation Priority

### P0 — v1.0 Must-Have (Conformance Baseline)

1. **Standard tables render correctly** — Player passing, rushing, receiving; team offense/defense
2. **Canonical abbreviations** — Uppercase headers, denominator-encoded percentages
3. **Mobile horizontal scroll with sticky first column** — Core table behavior
4. **Cross-links work** — Player → player page, Team → team page
5. **URL-addressable filters** — Season, team, conference in URL

### P1 — v1.5 High-Value (Competitive Parity)

1. **Game log tables** — Per-player, per-team game-by-game
2. **Table-stakes splits** — Home/away, conference, ranked opponents
3. **Percentile context** — Rank/percentile alongside raw values
4. **Advanced stat definitions** — Tooltips on EPA, CPOE, Success Rate
5. **Historical depth** — Player pages 2000+, team pages 1956+

### P2 — v2.0 Differentiation (Beyond Competitors)

1. **Advanced splits** — Quarter/half, down & distance, field position
2. **Side-by-side comparison** — Player vs. player, team vs. team
3. **Advanced stat integration** — EPA, Success Rate, CPOE in main tables
4. **All-level coverage** — FCS, DII, DIII, NAIA with same table quality
5. **Fan intel integration** — Mood cards alongside stats on team pages

---

## 10. Anti-Patterns to Avoid

Based on `cfb-stats-antipatterns.md`, these patterns MUST NOT be implemented:

1. **Mobile column collapse without disclosure** — Never silently hide columns on mobile
2. **Unsortable historical tables** — Every column header must be sortable with visible affordance
3. **Hover-only tooltips** — Definitions must work on tap (mobile), not just hover
4. **Missing drilldown** — Season totals must expand to game logs
5. **Alphabetical default sort** — Stats sites default to meaningful metric, not name
6. **Splits hidden behind undiscoverable tabs** — Surface splits as primary CTAs
7. **Historical depth UX failures** — Show all years, not just current/recent
8. **Inconsistent abbreviations** — Canonicalize site-wide; lint for compliance
9. **Horizontal scroll without sticky first column** — Always freeze identity column
10. **Tap targets too small** — Minimum 44×44px on all interactive elements
11. **Color-only encoding** — Pair color with shape, icon, or text
12. **Lazy loading that breaks back-button** — Preserve scroll position
13. **Page-level horizontal scroll** — `overflow-x: hidden` on body, table only

---

## 11. Sources and References

**Competitive Research Sources:**
- Sports Reference CFB: https://www.sports-reference.com/cfb/
- ESPN CFB Stats: https://www.espn.com/college-football/stats
- CBS Sports CFB: https://www.cbssports.com/college-football/stats/
- FOX Sports CFB: https://www.foxsports.com/college-football/team-stats
- PFF College: https://www.pff.com/college-football/grades
- TeamRankings: https://www.teamrankings.com/college-football/stats/
- CollegeFootballData: https://collegefootballdata.com/
- Football Outsiders: https://www.footballoutsiders.com/cfb
- NCAA.com Stats: https://www.ncaa.com/stats/football/fbs

**Mobile Reference:**
- FotMob: https://www.fotmob.com/ (gold-standard mobile stats UX)

**Design System Documents:**
- `docs/design-system/00-tokens.md` — Colors, typography, tabular numerals
- `docs/design-system/30-page-archetypes.md` — Page IA archetypes
- `docs/design-system/31-chart-vocabulary.md` — Chart types and vocabulary
- `docs/design-system/32-receipt-pattern.md` — Citation system
- `docs/design-system/33-confidence-signaling.md` — Confidence bands

**Internal Documents:**
- `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` — Player page redesign strategy
- `TEAM_PAGE_WORLD_CLASS_BRIEF.md` — Team page module architecture

---

**Document Length:** ~4,200 words  
**Version:** 1.0  
**Last Updated:** May 18, 2026  
**Status:** Ready for implementation planning
