# CFB Stats Column Conventions — Codex Research Report

**Compiled:** 2026-05-18  
**Source:** OpenAI Codex research via web search and public CFB stats sites

## 1. Column Grammar

The dominant table grammar is: **identity columns first, availability/volume next, efficiency next, explosive/long-play column if present, scoring/negative events, then a summary rating**. Passing is the most standardized. Rushing and receiving are more compact. Team tables are usually grouped by category: total, passing, rushing, points.

### Player Passing — Canonical Order

| Site | Observed Column Order | Notes |
|---|---|---|
| ESPN | `RK | Name | POS | CMP | ATT | CMP% | YDS | AVG | LNG | TD | INT | SACK | RTG` | ESPN uses `AVG` for YPA, `RTG` for passer rating |
| CBS Sports | `Player | GP | ATT | CMP | PCT | YDS | TD | INT | YDS/A | YDS/G | RATE` | Attempts-before-completions order |
| Sports-Reference | `Rk | Player | Team | Conf | G | Cmp | Att | Cmp% | Yds | TD | TD% | Int | Int% | Y/A | AY/A | Y/C | Y/G | Rate | Awards` | Richest traditional passer table |
| NCAA.com | `Rank | Name | Team | Cl | Position | G | Pass Att | Pass Com | Int | Pass Yds | Pass TD | Pass Eff` | Verbose official labels |

**Recommended canonical passing order:** `Player | Team | POS | GP | CMP | ATT | CMP% | YDS | Y/A | LNG | TD | INT | SACK | RATE`

- If space is tight, drop `LNG` and `SACK`
- If analytical, add `AY/A` after `Y/A`
- Use `RATE` or `RTG`, but explain NCAA pass efficiency (not ESPN QBR)

### Player Rushing — Canonical Order

| Site | Observed Column Order | Notes |
|---|---|---|
| ESPN | `RK | Name | POS | ATT | YDS | AVG | LNG | TD` | Compact leader-table |
| CBS Sports | `Player | GP | ATT | YDS | AVG | TD | YDS/G` | Omits long run |
| Sports-Reference | `Rk | Player | Team | Conf | G | Att | Yds | Y/A | TD | Y/G | Rec | Yds | Y/R | TD | Y/G | Plays | Yds | Avg | TD | Awards` | Scrimgage blended |

**Recommended rushing order:** `Player | Team | POS | GP | ATT | YDS | Y/A | LNG | TD | Y/G`

- `Y/A` is more precise than `AVG`, but `AVG` acceptable in pure rushing tables

### Player Receiving — Canonical Order

| Site | Observed Column Order | Notes |
|---|---|---|
| CBS Sports | `Player | GP | REC | YDS | AVG | TD | YDS/G` | Uses `REC`, not `Catches` |
| Sports-Reference | `Rk | Player | Team | Conf | G | Rec | Yds | Y/R | TD | Y/G | Att | Yds | Y/A | TD | Y/G | Plays | Yds | Avg | TD | Awards` | Scrimage blended |
| ESPN | `RK | Name | POS | REC | YDS | AVG | LNG | TD` | Mirrors rushing minimalism |

**Recommended receiving order:** `Player | Team | POS | GP | REC | YDS | Y/R | LNG | TD | Y/G`

- Add `TGT`, `Catch%`, `YAC`, or `YPRR` only in advanced/receiver-analysis views

### Team Offense/Defense — Canonical Order

| Site | Observed Column Order | Notes |
|---|---|---|
| CBS total table | `Team | GP | YDS | YDS/G | Pass YDS | Pass Y/G | Rush YDS | Rush Y/G | PTS | PTS/G` | Visually grouped |
| ESPN team stats | Total, passing, rushing, points categories; emphasizes `YDS/G` and `PTS/G` | Card-style leaders |
| NCAA passing | `Rank | Team | G | Pass Att | Pass Com | Int | Pass Yds | Yds/Att | Yds/Comp | Pass TD | YPG` | Official verbose style |

**Recommended team offense order:** `Team | Conf | GP | PTS | PTS/G | YDS | YDS/G | Plays | Y/P | Pass YDS | Pass Y/G | Rush YDS | Rush Y/G | 1stD | 3D% | 4D% | RZ% | TO`

For defense: mirror with clear labels — `YDS Allowed`, `YDS/G Allowed`, `PTS Allowed`, `Opp 3D%`

---

## 2. Abbreviation Conventions

| Concept | ESPN | CBS | Sports-Reference | NCAA | **Best Product Default** |
|---|---|---|---|---|---|
| Games | omitted / `G` | `GP` | `G` | `G` | `GP` for players, `G` for teams |
| Completions | `CMP` | `CMP` | `Cmp` | `Pass Com` | **`CMP`** |
| Attempts | `ATT` | `ATT` | `Att` | `Pass Att` | **`ATT`** |
| Completion % | `CMP%` | `PCT` | `Cmp%` | category-dependent | **`CMP%`** |
| Yards | `YDS` | `YDS` | `Yds` | `Pass Yds` | **`YDS`** |
| Yards/Attempt | `AVG` | `YDS/A` | `Y/A`, `AY/A` | `Yds/Att` | **`Y/A`** (use `AY/A` for adjusted) |
| Yards/Game | not shown | `YDS/G` | `Y/G` | `YPG` | **`YDS/G`** in UI, `Y/G` in dense tables |
| Long | `LNG` | omitted | sometimes absent | category-dependent | **`LNG`** |
| Touchdowns | `TD` | `TD` | `TD` | `Pass TD` | **`TD`** |
| Interceptions | `INT` | `INT` | `Int` | `Int` | **`INT`** |
| Rating | `RTG` | `RATE` | `Rate` | `Pass Eff` | **`RATE`** + tooltip: NCAA pass efficiency |
| Receptions | `REC` | `REC` | `Rec` | sometimes `No.` | **`REC`** |
| Rushing avg | `AVG` | `AVG` | `Y/A` | category-dependent | **`Y/A`** if mixed, `AVG` if simple |
| Percent | `%` suffix | `PCT` | `%` suffix | `Pct` | **Prefer `%` suffix** (`CMP%`, `3D%`, `RZ%`) |

**Key call:** `PCT` is CBS/NCAA-ish. `CMP%`, `3D%`, `4D%`, `RZ%` are clearer because they encode the denominator.

**`YPG`** is NCAA-friendly and works in cards. **`YDS/G`** is more self-documenting in tables.

**`AVG`** is overloaded (yards/attempt, yards/rush, yards/reception, punt average). Use `AVG` only in clearly scoped tables. Otherwise use `Y/A`, `Y/R`, `Y/P`, `YDS/G`.

---

## 3. Splits Taxonomy

Splits fall into **five families**. Table-stakes for a world-class CFB site:

### I. Venue/Context (Universal)
- `All`, `Home`, `Away`, `Neutral`
- Conference filters
- Conference/non-conference

### II. Schedule/Opponent (Culturally Important)
- FBS/FCS (if available)
- Regular season/postseason
- Bowl/playoff
- **Nice-to-have:** vs ranked teams, vs AP Top 25, vs winning teams, rivalry/championship games

### III. Game-State (Coach/Analyst Territory)
- Half, quarter
- Down and distance
- Field position
- Red zone, goal-to-go
- Score margin
- Garbage time
- Late & close

### IV. Conversion Zone (Table-stakes)
- Third down
- Fourth down
- Red zone
- Scoring offense/defense
- Time of possession
- Turnover margin
- Sacks, tackles for loss

### V. Play-Type (Analytics Bridge)
- Rush/pass
- Standard downs/passing downs
- Play action/non-play action
- Pressure/clean pocket
- Deep passing
- Short/intermediate/deep target depth
- Blitz, coverage, route
- Run direction

### VI. Environmental/Time (Least Standardized)
- By month
- Day/night
- Temperature, weather, surface
- Altitude

**Recommended table-stakes split set:** `Season`, `Game Log`, `Career`, `Home/Away/Neutral`, `Conference/Non-Conference`, `Opponent`, `Offense/Defense`, `Team/Opponent`, `Rush/Pass`, `3rd Down`, `4th Down`, `Red Zone`, `By Game/Week`, `Regular/Postseason`

**Advanced tier:** `Quarter/Half`, `Down & Distance`, `Field Position`, `Score State`, `Garbage Time`, `Opponent Strength`, `vs Ranked`, `Month`, `Weather`

---

## 4. Advanced Stat Presentation

Advanced CFB stats are usually **not mixed into primary box-score tables**. They appear in separate ranked views, glossary-backed analytics pages, or premium tools.

### ESPN Total QBR
Table order: `RK | Name | QBR | PAA | PLAYS | EPA | PASS | RUN | SACK | PEN | RAW`

- Season leaders, weekly leaders, all-time bests
- Season dropdowns back to 2004
- Qualifier note: 20 action plays per team game
- **Pattern:** One headline metric (`QBR`) plus components
- `RAW` shown because headline QBR is adjusted; `EPA`, `PASS`, `RUN`, `SACK`, `PEN` expose contribution buckets

### PFF Grades
- 0-100 scores, not counting stats
- Every player graded on every play
- Raw plus/minus converted to 0-100
- Facets: passing, rushing, receiving, pass blocking, run blocking, pass rush, run defense, coverage
- **First-encounter pattern:** Define grading scale, explain what the number is NOT, show facet grades, always include snap counts/sample size

### CFB Graphs
- Signed margin-style values with ranks
- Offense/defense, rush/pass split
- Columns: overall margin + `OVR`, `RUSH`, `PASS`, `RROE`
- **Pattern:** Raw value plus rank in same cell family; offense and defense mirrored

### CollegeFootballData
- Developer/data-export oriented
- Season-level: EPA, explosiveness, success rates, down splits, field position, havoc, efficiency
- Game-level: explosiveness, success rate, EPA, line yards, opportunity stats

### First-Encounter Copy Template (Staturdays pattern)

| Metric | Display | Direction | First Encounter Copy |
|---|---|---|---|
| `EPA/Play` | `+0.18` | Higher offense, lower defense | "Expected points added per play; measures scoreboard value of each snap." |
| `Success Rate` / `SR%` | percentage | Higher offense, lower defense | "Share of plays that keep the offense on schedule." |
| `Explosiveness` | EPA/success | Higher offense, lower defense | "How much value a team creates when a play succeeds." |
| `CPOE` | `+4.2%` | Higher QB better | "Completion percentage over expected, adjusted for throw difficulty." |
| `QBR` | 0-100 | Higher better | "ESPN's total QB contribution metric; includes pass, run, sack, penalty, and opponent/situation adjustments." |
| `PFF Grade` | 0-100 + snaps | Higher better | "Film-based performance grade for a player's role on each play." |
| `AY/A` | decimal | Higher better | "Adjusted yards per attempt; folds TD/INT value into passing efficiency." |
| `ANY/A` | decimal/dropback | Higher better | Rare in CFB; define sack treatment clearly if used |

---

## 5. Historical Depth

| Site | Depth | Notes |
|---|---|---|
| ESPN | 2004-2025 (player stats, QBR) | Season selectors, weekly, all-time views |
| Sports-Reference | 1869-present | Game results; player/season tables; deepest historical consumer DB |
| PFF | 2014-present (college) | Modern-era grading; 2006 for NFL |
| CFB Graphs | 2019-2025 | Modern analytics era only |
| CollegeFootballData | 1869-present (games), growing for advanced | Game master file; play-by-play by year |

**Best practice:**
- **Player pages:** `Season-by-season`, `Career total`, `Game log`, `Splits`
- **Team pages:** `Current season`, `Year selector`, `Conference rank`, `National rank`, `Opponent/defense mirror`
- **Comparison:** Side-by-side cards for players; mirrored offense-vs-defense tables for teams

The CFB-native expectation is not just "what is the number?" but "what is the rank, against what schedule, and over what sample?"

---

## Sources

- ESPN College Football Stats: https://www.espn.com/college-football/stats/player
- ESPN QBR: https://www.espn.com/college-football/qbr/_/qualified
- CBS Sports CFB: https://www.cbssports.com/college-football/stats/
- Sports Reference CFB: https://www.sports-reference.com/cfb/
- NCAA.com Stats: https://www.ncaa.com/stats/football/fbs
- PFF Grades: https://www.pff.com/grades
- PFF Signature Stats Glossary: https://www.pff.com/news/pro-pff-signature-statistics-a-glossary
- CFB Graphs: https://www.cfb-graphs.com/
- CollegeFootballData: https://collegefootballdata.com/
- cfbstats: https://www.cfbstats.com/
- Staturdays: https://staturdays.com/college-football-stats-explained/
