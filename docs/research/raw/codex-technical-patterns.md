Reading additional input from stdin...
OpenAI Codex v0.129.0 (research preview)
--------
workdir: C:\Users\kevin\Downloads\Sports Website\.claude\worktrees\gallant-wiles-ecf987
model: gpt-5.5
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019e3c20-f9b5-7111-aeb9-29b1295584c6
--------
user
Conduct competitive research on COLLEGE FOOTBALL stats display sites. Write a comprehensive markdown report on TECHNICAL IMPLEMENTATION PATTERNS used by top CFB stats sites. Output the full report directly to stdout (do not write files).

SCOPE: How are stats tables actually built on these sites? Focus on technical anatomy, not data.

Sites to consider:
- sports-reference.com/cfb (canonical)
- ESPN.com/college-football, CBS Sports CFB, FOX Sports CFB, Yahoo CFB
- PFF College, TeamRankings, CollegeFootballData.com
- 247Sports, On3, Rivals
- FotMob (mobile reference)

For each site or pattern, document:
1. DOM strategy: real table vs CSS Grid vs flex
2. Sticky first column on mobile
3. Horizontal scroll vs reflow
4. Sortable column UX
5. Default sort and filter
6. Tooltip/definition behavior
7. Pagination/infinite-scroll/virtualization
8. Cross-link patterns
9. Accessibility (aria-sort, scope, keyboard)
10. Performance: lazy load, render budget
11. Print-friendly

End with IMPLEMENTATION RECOMMENDATIONS for a Python static-site CFB rankings/intel site with locked design system, tabular numerals enforced, target FCP under 1.5s.

Length: 2000-4000 words. Cite URLs where known. Be specific about which sites use which patterns.
codex
I’ll verify current pages and observable markup patterns from the listed sites, then synthesize the report directly in the response as requested.
web search: 
web search: site:sports-reference.com/cfb years college football standings stats table Sports Reference CFB
web search: 
web search: https://www.espn.com/college-football/stats
web search: 
web search: 'Passing Leaders' in https://www.cbssports.com/college-football/stats/
codex
The public HTML snapshots are accessible for several sites, but some outlets hydrate content client-side or gate bot-like fetches. I’ll separate directly observed markup from inferred behavior where the rendered page is protected.
2026-05-18T17:28:17.925622Z ERROR codex_core::tools::router: error=`"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "(Invoke-WebRequest -Uri 'https://www.sports-reference.com/cfb/years/2025-standings.html' -UseBasicParsing -TimeoutSec 15).Content.Substring(0,1000)"` rejected: blocked by policy
exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "(Invoke-WebRequest -Uri 'https://www.sports-reference.com/cfb/years/2025-standings.html' -UseBasicParsing -TimeoutSec 15).Content.Substring(0,1000)" in C:\Users\kevin\Downloads\Sports Website\.claude\worktrees\gallant-wiles-ecf987
 declined in 0ms:
`"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "(Invoke-WebRequest -Uri 'https://www.sports-reference.com/cfb/years/2025-standings.html' -UseBasicParsing -TimeoutSec 15).Content.Substring(0,1000)"` rejected: blocked by policy
web search: 
web search: 
web search: 
web search: Sports Reference stats_table data-stat sticky table sortable data-tip
web search: 
web search: 
web search: 
web search: TeamRankings college football team stats passing yards per game table
web search: 
web search: ESPN college football stats table class Table__TR Table__TH React sticky column mobile
web search: 
web search: https://www.cbssports.com/college-football/stats/team/team/passing/all-conf/
web search: 
web search: https://www.cbssports.com/college-football/stats/team/team/passing/all-conf/
web search: 
web search: 'NCAA FOOTBALL'
web search: 
web search: https://www.foxsports.com/college-football/team-stats
web search: 
web search: 'SHOW MORE' in https://www.foxsports.com/college-football/team-stats
web search: 
web search: https://www.foxsports.com/college-football/team-stats
web search: 
web search: FOX Sports stats table DOM column sticky table React
web search: 
web search: Yahoo Sports college football stats team stats table NCAA football 2025
web search: 
web search: 
web search: 
web search: 
web search: 
web search: PFF College football stats player grades table NCAA sortable sticky columns
web search: 
web search: https://www.pff.com/grades
web search: 
web search: https://www.teamrankings.com/college-football/stat/passing-yards-per-game
web search: 
web search: https://www.teamrankings.com/college-football/stat/passing-yards-per-game
web search: 
web search: https://www.teamrankings.com/college-football/stat/passing-yards-per-game
web search: 
web search: 247Sports football recruiting rankings table sortable composite player rank college football 2026
codex
# Competitive Research: CFB Stats Table Implementation Patterns

Research note: some large media sites gate full DOM inspection behind bot checks or client hydration. Where markup was directly visible, I state it directly; where not, I label the pattern as “appears” or “likely” based on rendered output, URL behavior, and known component conventions.

## Executive Takeaways

The strongest CFB stats-table implementations split into two camps:

1. **Reference/stat-first sites** like Sports Reference and TeamRankings use plain, crawlable, server-rendered tables. They are fast, printable, accessible at a baseline level, and degrade well.
2. **Media/product sites** like ESPN, CBS, FOX, Yahoo, PFF, On3/Rivals, and 247Sports use React/SPA or hybrid-rendered table-like components with richer filters, sort URLs, logos, modals, tabs, ads, and responsive card transforms. These are better for engagement but often weaker for print, accessibility, and first-load performance.

For a Python static-site CFB rankings/intel product with a locked design system and FCP under 1.5s, the right pattern is closer to Sports Reference plus TeamRankings: semantic HTML tables, server-rendered default sort, URL-addressable filters, optional progressive enhancement, sticky identity column on mobile, no virtualization for normal FBS-scale tables, and print CSS built in.

## Site Patterns

### Sports Reference / College Football Reference

Sources: https://www.sports-reference.com/cfb/, https://www.sports-reference.com/cfb/years/2025-passing.html, https://www.sports-reference.com/cfb/years/2025-standings.html

Sports Reference is the canonical “stats as documents” model. CFB pages expose real tabular content in crawlable HTML, with tables such as season passing, standings, school pages, and leaderboards rendered as actual tables rather than card feeds. Its broader Sports Reference table framework uses `stats_table`-style semantic tables with column metadata, sortable headers, wrapper containers, and historically `data-stat` / `data-tip` attributes for stat identity and definitions.

**DOM strategy:** native HTML tables. This is the right model for dense sports stats because it preserves column/row relationships, makes scraping possible, and allows browser-native copy/paste behavior.

**Mobile:** tables use horizontal scrolling rather than reflowing every row into cards. The newer Sports Reference table system supports frozen columns on some tables; older or simpler tables fall back to scroll-only. The practical pattern is: keep the rank/name/team identity columns visible where possible, but do not duplicate the table into a second mobile DOM.

**Sorting:** client-side column sorting is a major part of the UX. Headers act as sortable controls, with default sort determined by page context: passing pages default by a main leaderboard stat, standings by rank/SRS/win-loss context. Re-sorting is local and fast.

**Filters/defaults:** filters are usually page-level navigation rather than in-table controls: season pages, stat categories, school pages, conference/leader pages, and Stathead for advanced query filters. The default view is a complete canonical season/table, not an empty query builder.

**Tooltips/definitions:** Sports Reference has one of the better stat-definition traditions: abbreviated column headers often carry definitions through tooltip/popover behavior, and pages include notes/context. This keeps the table dense without forcing verbose headers.

**Pagination/virtualization:** mostly no virtualization for public tables. Full tables render in the document. This favors FCP/SEO/print and avoids scroll-jank complexity.

**Cross-links:** excellent. Player names, schools, seasons, box scores, awards, and leader pages are all linked. The primary entity cell is the link; not every numeric cell needs to be clickable.

**Accessibility:** baseline is stronger than most because real tables preserve semantics. Gaps likely remain around explicit `aria-sort` state and keyboard-discoverable tooltips, but the semantic base is correct.

**Performance/print:** strong. Server-rendered HTML and minimal dependency on hydration make these pages resilient. Printability is better than media sites because the table is real content, though wide tables still need print-specific handling.

### ESPN College Football

Sources: https://www.espn.com/college-football/stats, https://www.espn.com/college-football/stats/team/_/stat/passing

ESPN’s stats pages are React-driven media product pages. Search-rendered output shows real table content for team passing stats with URL-addressable sort paths such as `/sort/passingYardsPerGame` and category paths such as `/stat/passing`.

**DOM strategy:** ESPN appears to use React table components that render actual table structures or table-like components with classes such as `Table__TR` in ESPN’s broader stats system. Many ESPN stats views visually split the identity column from the numeric stat scroller, which allows the name/team column to remain fixed while the right side scrolls.

**Mobile:** horizontal scrolling dominates. Sticky or split first-column behavior is common in ESPN stat products, especially for player/team identity. It solves row-tracking but can feel heavy because the identity column can consume too much viewport width.

**Sorting:** sort is URL-addressable: metric and direction are encoded in route segments or query state. This is good for shareability and server/cache behavior. Header clicks update the route rather than merely mutating local state.

**Filters/defaults:** defaults are sport/category/year driven. Team stats default to total/offense views, with subcategories like Passing/Rushing/Points. Select controls and tabs are common.

**Tooltips/definitions:** ESPN often provides a glossary below stat tables, e.g. GP, CMP, ATT, YDS/G, RTG definitions. This is less elegant than header tooltips but better for mobile and print.

**Pagination/virtualization:** ESPN commonly limits long tables behind pagination or “show more” style behavior. It does not appear to rely on full virtualization for normal public CFB tables.

**Cross-links:** strong entity linking to team/player pages. ESPN also cross-links schedules, rosters, standings, and news.

**Accessibility:** mixed. Real table markup helps where present, but custom split-table scrolling can hurt screen-reader continuity. Header sort controls should expose `aria-sort`; this is not reliably visible in rendered snapshots.

**Performance/print:** weaker than reference sites because ESPN carries large app shell, ads, personalization, and hydration. Print is not a first-class table use case.

### CBS Sports CFB

Source: https://www.cbssports.com/college-football/stats/team/team/passing/all-conf/

CBS Sports exposes one of the clearer public CFB team-stat implementations. The passing team-stat page has conference filters, stat-category filters, Team/Opponent toggles, sortable header links, a definitions row/section, team-logo/name links, and pagination links.

**DOM strategy:** rendered output behaves like a real table. It is crawler-visible and organized as Team plus metric columns. The page likely uses server-rendered or hybrid-rendered table markup.

**Mobile:** likely horizontal scroll rather than row reflow. The table is too dense for card reflow, and CBS preserves a conventional leaderboard shape.

**Sticky first column:** not a defining feature. Identity cells are readable, but there is no strong evidence of a robust sticky first-column implementation.

**Sorting:** column headers are links. On the passing page, headers such as GP, ATT, CMP, PCT, YDS/G, YDS, and INT link to sorted variants. This is a strong pattern: sort state is shareable and crawlable.

**Default sort/filter:** page context sets both. `/passing/all-conf/` defaults to all conferences, team passing category, and a main passing-volume sort. Filters are explicit lists: All Conf, ACC, Big Ten, SEC, etc.; Total, Passing, Rushing, Receiving, and so on.

**Tooltips/definitions:** CBS shows definitions inline under headers or near the table: “GP Games played,” “ATT Pass Attempts,” “PCT Completion Percentage,” etc. That works well for mobile because definitions do not depend on hover.

**Pagination:** yes. The observed page has page links `1 2 3`, so it avoids rendering every team row at once.

**Cross-links:** team logos and names link to team pages. Recruiting and transfer links go out to 247Sports from the CBS CFB nav.

**Accessibility:** better than div-only grids if table semantics are present, but likely missing robust `aria-sort`. Header links are keyboard-accessible.

**Performance/print:** medium. Content is crawlable, but the CBS shell is ad/media-heavy. Print is not optimized.

### FOX Sports CFB

Source: https://www.foxsports.com/college-football/team-stats

FOX Sports uses a highly branded, React-like stats presentation. The CFB team stats page exposes filters for stat category, season, regular/postseason, and sortable metric headers. The rendered page includes a definitions footer: GP, COMP, PATT, ATT/G, PCT, PYDS, PYDS/G, PTD, etc.

**DOM strategy:** appears to be a table-like React/SSR grid. Rendered output exposes a matrix, but every row/cell is heavily linked to the team route. It may be native table markup with anchors in each cell, or a grid/list component that is serialized as table-like text.

**Mobile:** horizontal scroll is the likely main strategy. FOX keeps dense numeric columns instead of reflowing every row into cards.

**Sticky first column:** not clearly present. FOX ranks and team names appear as the left-side identity, but the pattern is more “scroll table” than “locked identity column.”

**Sorting:** column headers are links. A click on GP, COMP, PATT, PYDS/G, etc. changes the sorted metric. This is URL/share-friendly.

**Default sort/filter:** the passing stats page defaults to the current season, regular season, teams, and a passing-yardage-related ranking. Category tabs include Passing, Rushing, Kicking, Returning, Defensive, Downs, Yardage, Turnovers.

**Tooltips/definitions:** no heavy hover tooltip pattern. Definitions are listed below the table, which is mobile-safe and printable.

**Pagination:** public page shows a top slice, roughly 50 rows, with no obvious pagination in the rendered snapshot. This is a “leaderboard cap” pattern.

**Cross-links:** extremely aggressive; team name and many stat cells link to the same team page. This boosts clickability but can add noise for keyboard users.

**Accessibility:** mixed. Header links are good. If implemented as div/grid rather than real table, row/column semantics may be weak. Repeated same-row links can be tedious for assistive tech.

**Performance/print:** medium to weak. The rendered data is accessible to crawlers, but the app shell is substantial. Print is not a design priority.

### Yahoo Sports CFB

Sources: https://sports.yahoo.com/college-football/stats/, https://sports.yahoo.com/college-football/stats/team/?leagueStructure=ncaaf.struct.div.1&selectedTable=3

Yahoo’s main CFB stats landing page leans more toward responsive leaderboard cards than dense tables. The season leaders view shows rank, player/team identity, a few secondary stats, and one large primary stat value. Team stats pages use selected table state such as `selectedTable` and `sortStatId`.

**DOM strategy:** hybrid. Landing stats are card/list leaderboards; deeper team stats can behave more like tables. This is optimized for mobile scanning rather than spreadsheet-like comparison.

**Mobile:** reflow/card-first. Yahoo is one of the clearest examples of avoiding a 15-column mobile table by surfacing only a primary stat and a few secondary fields.

**Sticky first column:** generally not relevant on the card views.

**Sorting:** category chips/tabs such as Yards, Touchdowns, QB Rating, More drive sorting. Query params such as `sortStatId=PASSING_INTERCEPTIONS` make sort state addressable.

**Default sort/filter:** defaults to season leaders and selected tables. The main page shows top-five style leaderboards, not a complete statistical register.

**Tooltips/definitions:** minimal. Yahoo uses human-readable stat labels in the card itself, e.g. “Yds (Passing Yards),” reducing need for tooltips.

**Pagination/virtualization:** likely load-more or segmented deeper pages; main landing uses short lists.

**Cross-links:** strong to player/team pages through identity rows and images.

**Accessibility/performance/print:** card layouts can be accessible if headings and links are structured, but they are less useful for copy/paste and print. The Yahoo app shell and ads reduce performance predictability.

### PFF College

Sources: https://www.pff.com/grades, https://premium.pff.com/ncaa/positions/2025/REGPO/passing

PFF is not just a public stat table; it is a premium analytics product. Its own grades page describes PFF+ as supporting rankings by position, player grades, snap counts, team filters, Premium Stats, weekly grades, and position tables.

**DOM strategy:** premium app-style data grid. PFF likely uses div/grid or custom React table components rather than simple static tables, because the product requires many filters, modals, position views, snap thresholds, and premium gating.

**Mobile:** horizontal scroll plus condensed filters. For paid analytics, users tolerate more complex controls.

**Sticky first column:** likely for player identity in premium grids, because otherwise PFF’s many grade/stat columns become hard to track.

**Sorting/defaults:** sort by grade or selected metric; defaults depend on position, season, and snap minimums. Filters are core: league, year, season phase, position, team, week, minimum snaps/dropbacks/routes/etc.

**Tooltips/definitions:** important and likely present through hover/help states because PFF metrics are proprietary and abbreviated. Player modals are also a key behavior.

**Pagination/virtualization:** likely pagination or virtualization for large player universes. PFF handles far more rows than a 136-team FBS table.

**Cross-links:** player modals, profiles, premium stat pages, team filters, and article references.

**Accessibility/print/performance:** weakest fit for a static public rankings site. Rich grids and modals are powerful, but they add hydration cost, keyboard complexity, and poor print behavior.

### TeamRankings

Source: https://www.teamrankings.com/college-football/stat/passing-yards-per-game

TeamRankings is the best lightweight comparison point after Sports Reference. Each stat has a dedicated URL, e.g. passing yards per game. The page renders a complete ranked table with columns like Rank, Team, current season, Last 3, Last 1, Home, Away, and previous season. It includes season/date controls and notes about included games.

**DOM strategy:** real server-rendered table pattern. It is plain, crawlable, and dense.

**Mobile:** horizontal scroll, not card reflow. There is no strong sticky first-column pattern.

**Sorting/defaults:** the URL defines the stat, and the table defaults sorted by that stat. This removes ambiguity. Users navigate to another stat page rather than reconfiguring one mega-grid.

**Filters:** season and date controls. The page family provides related stat links rather than a giant in-table filter UI.

**Tooltips/definitions:** minimal. The stat page title and related-stat section carry the explanation.

**Pagination/virtualization:** none for FBS-scale data. Full table renders.

**Cross-links:** team names link to team pages; related stats link laterally.

**Accessibility/performance/print:** strong baseline because of static HTML and simple tables. It likely lacks modern `aria-sort`, but the structure is far better than custom grids. Print is workable with CSS.

### CollegeFootballData.com

Source: https://collegefootballdata.com/

CollegeFootballData is more of a data-access/API site than a consumer leaderboard UI. Its current positioning emphasizes API access, raw exports, rankings, downloads, and CSV-ready football data.

**DOM strategy:** documentation/query/export pattern, not a canonical public stat-table pattern. The technical lesson is backend-facing: expose stable data endpoints and downloads rather than forcing users through UI tables.

**Mobile/sticky/sort/pagination:** less relevant as a display reference. For a static rankings site, CFBD is more useful as a data pipeline reference than a UI reference.

**Cross-links:** endpoint/docs/download links matter more than row-level entity links.

**Accessibility/performance/print:** docs-style pages can be fast, but this is not a model for dense public rankings display.

### 247Sports, On3, Rivals

Sources: https://247sports.com/season/2026-football/compositeteamrankings/, https://www.on3.com/rivals/rankings/team/football/2026/?sort=score, https://www.on3.com/transfer-portal/winter-2026/football/

Recruiting sites are adjacent rather than pure stat sites, but they are relevant because they manage rank, rating, stars, status, school, position, and NIL/value columns.

**DOM strategy:** modern ranking tables often become responsive card/table hybrids. On3/Rivals rendered output repeats labels inside each row/card: Rank, 5-Stars, 4-Stars, Total Commits, Avg Rating, Avg NIL, Score. That suggests mobile-first card transformation rather than a pure spreadsheet.

**Mobile:** reflow into stacked rank cards is common. This is better for recruiting profiles than for numeric team-stat comparison.

**Sticky first column:** generally no. Recruiting pages preserve identity through card structure instead of sticky columns.

**Sorting/defaults:** URL query sort is common; On3/Rivals uses `?sort=score`. 247Sports rankings historically support class/year, composite vs internal ranking, position, state, and team/class views.

**Tooltips/definitions:** recruiting sites need definitions for composite, industry ranking, stars, score, NIL value, and status. These are usually handled with explanatory text or info affordances, not dense stat-header tooltips.

**Pagination/infinite scroll:** common because recruit lists are long. Pages often show rank slices with pagination or load-more.

**Cross-links:** very strong. Every player, team, school, commitment, and ranking page is a link target. This is the main thing to borrow.

**Accessibility/performance/print:** mixed to weak. Ads, images, cards, and dynamic filters reduce print value. Repeated labels can help mobile comprehension but may lose table semantics.

### FotMob Mobile Reference

Source: https://www.fotmob.com/

FotMob is not a college football stats site, but it is a useful mobile pattern reference. It avoids giant tables in many mobile contexts. Match stats, player lists, and leaderboards are presented as compact rows/cards with a primary metric, rank, visual indicator, and drill-down link.

**DOM strategy:** mobile app/list pattern, not dense table first.

**Mobile:** reflow is the primary strategy. Instead of sticky first columns, the row is designed around the key entity plus one or two important metrics.

**Sorting/filtering:** tabs, chips, and segmented controls. This is excellent for narrow screens but less efficient for analysts comparing 12 columns.

**Tooltips:** minimal; labels and context do the work.

**Recommendation value:** use FotMob’s pattern only for summary modules, top-five callouts, and “intel cards,” not for canonical rankings tables.

## Cross-Site Pattern Conclusions

**Real tables still win for serious stats.** Sports Reference and TeamRankings are easier to scan, scrape, print, and trust. ESPN/CBS/FOX add media polish but often increase friction.

**URL-addressable sorting is better than JS-only sorting.** ESPN, CBS, FOX, Yahoo, On3/Rivals all encode category or sort in URLs. A static site should do the same.

**Definitions should not depend on hover.** Sports Reference-style header tooltips are useful, but CBS/FOX glossary text is more mobile-safe. Best pattern: short header + tap/hover definition + glossary below.

**Avoid linking every cell.** FOX-style all-cell links inflate keyboard stops. Sports Reference/TeamRankings’ primary-entity link pattern is cleaner.

**Virtualization is unnecessary for normal CFB team tables.** FBS has roughly 130-140 teams. Render the table. Use pagination only for player/recruiting-scale lists.

## Implementation Recommendations For A Python Static-Site CFB Rankings/Intel Site

Use **semantic, server-rendered HTML tables** as the canonical component:

```html
<table class="stats-table">
  <caption>2026 Team Passing Efficiency Rankings</caption>
  <thead>
    <tr>
      <th scope="col" aria-sort="ascending">Rk</th>
      <th scope="col">Team</th>
      <th scope="col"><a href="?sort=epa_pass&dir=desc">Pass EPA</a></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">1</th>
      <td><a href="/teams/indiana/">Indiana</a></td>
      <td>0.287</td>
    </tr>
  </tbody>
</table>
```

For mobile, use **horizontal scroll plus sticky identity columns**, not card reflow for canonical rankings. Freeze `Rk` and `Team`; keep all numeric columns available. Add a subtle scroll shadow and make the scroll region keyboard-focusable.

Use CSS like:

```css
.stats-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.stats-table {
  border-collapse: separate;
  border-spacing: 0;
  font-variant-numeric: tabular-nums;
}

.stats-table th:first-child,
.stats-table td:first-child {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--surface);
}
```

Default each page to the metric implied by the URL: `/rankings/passing-efficiency/` sorts by passing efficiency descending. Filters should be **static URL state**, e.g. `?season=2026&division=fbs&conf=sec&sort=pass_epa&dir=desc`. Pre-render the most important combinations during the Python build.

For sorting, use header links first and optional JS enhancement second. Update `aria-sort` on the active header. Do not require JavaScript for the default table.

For definitions, use a three-layer model: short headers, accessible `<abbr title>` or popover buttons, and a glossary below the table. This covers desktop hover, mobile tap, screen readers, and print.

For performance under **1.5s FCP**, keep the table HTML static, inline critical CSS, avoid blocking web fonts, lazy-load logos, and keep optional JS under 10 KB gzipped. Do not hydrate the table. Do not virtualize team tables. For player tables over 500 rows, paginate statically by 100 rows and provide CSV download.

For print, add `@media print` rules: remove sticky positioning, remove overflow wrappers, hide nav/filter chrome, expand glossary, repeat table headers, and avoid row breaks where possible.

The final design target should be: **Sports Reference semantics, TeamRankings speed, CBS/FOX URL sorting, ESPN glossary discipline, Yahoo/FotMob summary cards only for non-canonical highlights, and none of the heavy premium-grid cost unless the page truly needs it.**
tokens used
167,491
# Competitive Research: CFB Stats Table Implementation Patterns

Research note: some large media sites gate full DOM inspection behind bot checks or client hydration. Where markup was directly visible, I state it directly; where not, I label the pattern as “appears” or “likely” based on rendered output, URL behavior, and known component conventions.

## Executive Takeaways

The strongest CFB stats-table implementations split into two camps:

1. **Reference/stat-first sites** like Sports Reference and TeamRankings use plain, crawlable, server-rendered tables. They are fast, printable, accessible at a baseline level, and degrade well.
2. **Media/product sites** like ESPN, CBS, FOX, Yahoo, PFF, On3/Rivals, and 247Sports use React/SPA or hybrid-rendered table-like components with richer filters, sort URLs, logos, modals, tabs, ads, and responsive card transforms. These are better for engagement but often weaker for print, accessibility, and first-load performance.

For a Python static-site CFB rankings/intel product with a locked design system and FCP under 1.5s, the right pattern is closer to Sports Reference plus TeamRankings: semantic HTML tables, server-rendered default sort, URL-addressable filters, optional progressive enhancement, sticky identity column on mobile, no virtualization for normal FBS-scale tables, and print CSS built in.

## Site Patterns

### Sports Reference / College Football Reference

Sources: https://www.sports-reference.com/cfb/, https://www.sports-reference.com/cfb/years/2025-passing.html, https://www.sports-reference.com/cfb/years/2025-standings.html

Sports Reference is the canonical “stats as documents” model. CFB pages expose real tabular content in crawlable HTML, with tables such as season passing, standings, school pages, and leaderboards rendered as actual tables rather than card feeds. Its broader Sports Reference table framework uses `stats_table`-style semantic tables with column metadata, sortable headers, wrapper containers, and historically `data-stat` / `data-tip` attributes for stat identity and definitions.

**DOM strategy:** native HTML tables. This is the right model for dense sports stats because it preserves column/row relationships, makes scraping possible, and allows browser-native copy/paste behavior.

**Mobile:** tables use horizontal scrolling rather than reflowing every row into cards. The newer Sports Reference table system supports frozen columns on some tables; older or simpler tables fall back to scroll-only. The practical pattern is: keep the rank/name/team identity columns visible where possible, but do not duplicate the table into a second mobile DOM.

**Sorting:** client-side column sorting is a major part of the UX. Headers act as sortable controls, with default sort determined by page context: passing pages default by a main leaderboard stat, standings by rank/SRS/win-loss context. Re-sorting is local and fast.

**Filters/defaults:** filters are usually page-level navigation rather than in-table controls: season pages, stat categories, school pages, conference/leader pages, and Stathead for advanced query filters. The default view is a complete canonical season/table, not an empty query builder.

**Tooltips/definitions:** Sports Reference has one of the better stat-definition traditions: abbreviated column headers often carry definitions through tooltip/popover behavior, and pages include notes/context. This keeps the table dense without forcing verbose headers.

**Pagination/virtualization:** mostly no virtualization for public tables. Full tables render in the document. This favors FCP/SEO/print and avoids scroll-jank complexity.

**Cross-links:** excellent. Player names, schools, seasons, box scores, awards, and leader pages are all linked. The primary entity cell is the link; not every numeric cell needs to be clickable.

**Accessibility:** baseline is stronger than most because real tables preserve semantics. Gaps likely remain around explicit `aria-sort` state and keyboard-discoverable tooltips, but the semantic base is correct.

**Performance/print:** strong. Server-rendered HTML and minimal dependency on hydration make these pages resilient. Printability is better than media sites because the table is real content, though wide tables still need print-specific handling.

### ESPN College Football

Sources: https://www.espn.com/college-football/stats, https://www.espn.com/college-football/stats/team/_/stat/passing

ESPN’s stats pages are React-driven media product pages. Search-rendered output shows real table content for team passing stats with URL-addressable sort paths such as `/sort/passingYardsPerGame` and category paths such as `/stat/passing`.

**DOM strategy:** ESPN appears to use React table components that render actual table structures or table-like components with classes such as `Table__TR` in ESPN’s broader stats system. Many ESPN stats views visually split the identity column from the numeric stat scroller, which allows the name/team column to remain fixed while the right side scrolls.

**Mobile:** horizontal scrolling dominates. Sticky or split first-column behavior is common in ESPN stat products, especially for player/team identity. It solves row-tracking but can feel heavy because the identity column can consume too much viewport width.

**Sorting:** sort is URL-addressable: metric and direction are encoded in route segments or query state. This is good for shareability and server/cache behavior. Header clicks update the route rather than merely mutating local state.

**Filters/defaults:** defaults are sport/category/year driven. Team stats default to total/offense views, with subcategories like Passing/Rushing/Points. Select controls and tabs are common.

**Tooltips/definitions:** ESPN often provides a glossary below stat tables, e.g. GP, CMP, ATT, YDS/G, RTG definitions. This is less elegant than header tooltips but better for mobile and print.

**Pagination/virtualization:** ESPN commonly limits long tables behind pagination or “show more” style behavior. It does not appear to rely on full virtualization for normal public CFB tables.

**Cross-links:** strong entity linking to team/player pages. ESPN also cross-links schedules, rosters, standings, and news.

**Accessibility:** mixed. Real table markup helps where present, but custom split-table scrolling can hurt screen-reader continuity. Header sort controls should expose `aria-sort`; this is not reliably visible in rendered snapshots.

**Performance/print:** weaker than reference sites because ESPN carries large app shell, ads, personalization, and hydration. Print is not a first-class table use case.

### CBS Sports CFB

Source: https://www.cbssports.com/college-football/stats/team/team/passing/all-conf/

CBS Sports exposes one of the clearer public CFB team-stat implementations. The passing team-stat page has conference filters, stat-category filters, Team/Opponent toggles, sortable header links, a definitions row/section, team-logo/name links, and pagination links.

**DOM strategy:** rendered output behaves like a real table. It is crawler-visible and organized as Team plus metric columns. The page likely uses server-rendered or hybrid-rendered table markup.

**Mobile:** likely horizontal scroll rather than row reflow. The table is too dense for card reflow, and CBS preserves a conventional leaderboard shape.

**Sticky first column:** not a defining feature. Identity cells are readable, but there is no strong evidence of a robust sticky first-column implementation.

**Sorting:** column headers are links. On the passing page, headers such as GP, ATT, CMP, PCT, YDS/G, YDS, and INT link to sorted variants. This is a strong pattern: sort state is shareable and crawlable.

**Default sort/filter:** page context sets both. `/passing/all-conf/` defaults to all conferences, team passing category, and a main passing-volume sort. Filters are explicit lists: All Conf, ACC, Big Ten, SEC, etc.; Total, Passing, Rushing, Receiving, and so on.

**Tooltips/definitions:** CBS shows definitions inline under headers or near the table: “GP Games played,” “ATT Pass Attempts,” “PCT Completion Percentage,” etc. That works well for mobile because definitions do not depend on hover.

**Pagination:** yes. The observed page has page links `1 2 3`, so it avoids rendering every team row at once.

**Cross-links:** team logos and names link to team pages. Recruiting and transfer links go out to 247Sports from the CBS CFB nav.

**Accessibility:** better than div-only grids if table semantics are present, but likely missing robust `aria-sort`. Header links are keyboard-accessible.

**Performance/print:** medium. Content is crawlable, but the CBS shell is ad/media-heavy. Print is not optimized.

### FOX Sports CFB

Source: https://www.foxsports.com/college-football/team-stats

FOX Sports uses a highly branded, React-like stats presentation. The CFB team stats page exposes filters for stat category, season, regular/postseason, and sortable metric headers. The rendered page includes a definitions footer: GP, COMP, PATT, ATT/G, PCT, PYDS, PYDS/G, PTD, etc.

**DOM strategy:** appears to be a table-like React/SSR grid. Rendered output exposes a matrix, but every row/cell is heavily linked to the team route. It may be native table markup with anchors in each cell, or a grid/list component that is serialized as table-like text.

**Mobile:** horizontal scroll is the likely main strategy. FOX keeps dense numeric columns instead of reflowing every row into cards.

**Sticky first column:** not clearly present. FOX ranks and team names appear as the left-side identity, but the pattern is more “scroll table” than “locked identity column.”

**Sorting:** column headers are links. A click on GP, COMP, PATT, PYDS/G, etc. changes the sorted metric. This is URL/share-friendly.

**Default sort/filter:** the passing stats page defaults to the current season, regular season, teams, and a passing-yardage-related ranking. Category tabs include Passing, Rushing, Kicking, Returning, Defensive, Downs, Yardage, Turnovers.

**Tooltips/definitions:** no heavy hover tooltip pattern. Definitions are listed below the table, which is mobile-safe and printable.

**Pagination:** public page shows a top slice, roughly 50 rows, with no obvious pagination in the rendered snapshot. This is a “leaderboard cap” pattern.

**Cross-links:** extremely aggressive; team name and many stat cells link to the same team page. This boosts clickability but can add noise for keyboard users.

**Accessibility:** mixed. Header links are good. If implemented as div/grid rather than real table, row/column semantics may be weak. Repeated same-row links can be tedious for assistive tech.

**Performance/print:** medium to weak. The rendered data is accessible to crawlers, but the app shell is substantial. Print is not a design priority.

### Yahoo Sports CFB

Sources: https://sports.yahoo.com/college-football/stats/, https://sports.yahoo.com/college-football/stats/team/?leagueStructure=ncaaf.struct.div.1&selectedTable=3

Yahoo’s main CFB stats landing page leans more toward responsive leaderboard cards than dense tables. The season leaders view shows rank, player/team identity, a few secondary stats, and one large primary stat value. Team stats pages use selected table state such as `selectedTable` and `sortStatId`.

**DOM strategy:** hybrid. Landing stats are card/list leaderboards; deeper team stats can behave more like tables. This is optimized for mobile scanning rather than spreadsheet-like comparison.

**Mobile:** reflow/card-first. Yahoo is one of the clearest examples of avoiding a 15-column mobile table by surfacing only a primary stat and a few secondary fields.

**Sticky first column:** generally not relevant on the card views.

**Sorting:** category chips/tabs such as Yards, Touchdowns, QB Rating, More drive sorting. Query params such as `sortStatId=PASSING_INTERCEPTIONS` make sort state addressable.

**Default sort/filter:** defaults to season leaders and selected tables. The main page shows top-five style leaderboards, not a complete statistical register.

**Tooltips/definitions:** minimal. Yahoo uses human-readable stat labels in the card itself, e.g. “Yds (Passing Yards),” reducing need for tooltips.

**Pagination/virtualization:** likely load-more or segmented deeper pages; main landing uses short lists.

**Cross-links:** strong to player/team pages through identity rows and images.

**Accessibility/performance/print:** card layouts can be accessible if headings and links are structured, but they are less useful for copy/paste and print. The Yahoo app shell and ads reduce performance predictability.

### PFF College

Sources: https://www.pff.com/grades, https://premium.pff.com/ncaa/positions/2025/REGPO/passing

PFF is not just a public stat table; it is a premium analytics product. Its own grades page describes PFF+ as supporting rankings by position, player grades, snap counts, team filters, Premium Stats, weekly grades, and position tables.

**DOM strategy:** premium app-style data grid. PFF likely uses div/grid or custom React table components rather than simple static tables, because the product requires many filters, modals, position views, snap thresholds, and premium gating.

**Mobile:** horizontal scroll plus condensed filters. For paid analytics, users tolerate more complex controls.

**Sticky first column:** likely for player identity in premium grids, because otherwise PFF’s many grade/stat columns become hard to track.

**Sorting/defaults:** sort by grade or selected metric; defaults depend on position, season, and snap minimums. Filters are core: league, year, season phase, position, team, week, minimum snaps/dropbacks/routes/etc.

**Tooltips/definitions:** important and likely present through hover/help states because PFF metrics are proprietary and abbreviated. Player modals are also a key behavior.

**Pagination/virtualization:** likely pagination or virtualization for large player universes. PFF handles far more rows than a 136-team FBS table.

**Cross-links:** player modals, profiles, premium stat pages, team filters, and article references.

**Accessibility/print/performance:** weakest fit for a static public rankings site. Rich grids and modals are powerful, but they add hydration cost, keyboard complexity, and poor print behavior.

### TeamRankings

Source: https://www.teamrankings.com/college-football/stat/passing-yards-per-game

TeamRankings is the best lightweight comparison point after Sports Reference. Each stat has a dedicated URL, e.g. passing yards per game. The page renders a complete ranked table with columns like Rank, Team, current season, Last 3, Last 1, Home, Away, and previous season. It includes season/date controls and notes about included games.

**DOM strategy:** real server-rendered table pattern. It is plain, crawlable, and dense.

**Mobile:** horizontal scroll, not card reflow. There is no strong sticky first-column pattern.

**Sorting/defaults:** the URL defines the stat, and the table defaults sorted by that stat. This removes ambiguity. Users navigate to another stat page rather than reconfiguring one mega-grid.

**Filters:** season and date controls. The page family provides related stat links rather than a giant in-table filter UI.

**Tooltips/definitions:** minimal. The stat page title and related-stat section carry the explanation.

**Pagination/virtualization:** none for FBS-scale data. Full table renders.

**Cross-links:** team names link to team pages; related stats link laterally.

**Accessibility/performance/print:** strong baseline because of static HTML and simple tables. It likely lacks modern `aria-sort`, but the structure is far better than custom grids. Print is workable with CSS.

### CollegeFootballData.com

Source: https://collegefootballdata.com/

CollegeFootballData is more of a data-access/API site than a consumer leaderboard UI. Its current positioning emphasizes API access, raw exports, rankings, downloads, and CSV-ready football data.

**DOM strategy:** documentation/query/export pattern, not a canonical public stat-table pattern. The technical lesson is backend-facing: expose stable data endpoints and downloads rather than forcing users through UI tables.

**Mobile/sticky/sort/pagination:** less relevant as a display reference. For a static rankings site, CFBD is more useful as a data pipeline reference than a UI reference.

**Cross-links:** endpoint/docs/download links matter more than row-level entity links.

**Accessibility/performance/print:** docs-style pages can be fast, but this is not a model for dense public rankings display.

### 247Sports, On3, Rivals

Sources: https://247sports.com/season/2026-football/compositeteamrankings/, https://www.on3.com/rivals/rankings/team/football/2026/?sort=score, https://www.on3.com/transfer-portal/winter-2026/football/

Recruiting sites are adjacent rather than pure stat sites, but they are relevant because they manage rank, rating, stars, status, school, position, and NIL/value columns.

**DOM strategy:** modern ranking tables often become responsive card/table hybrids. On3/Rivals rendered output repeats labels inside each row/card: Rank, 5-Stars, 4-Stars, Total Commits, Avg Rating, Avg NIL, Score. That suggests mobile-first card transformation rather than a pure spreadsheet.

**Mobile:** reflow into stacked rank cards is common. This is better for recruiting profiles than for numeric team-stat comparison.

**Sticky first column:** generally no. Recruiting pages preserve identity through card structure instead of sticky columns.

**Sorting/defaults:** URL query sort is common; On3/Rivals uses `?sort=score`. 247Sports rankings historically support class/year, composite vs internal ranking, position, state, and team/class views.

**Tooltips/definitions:** recruiting sites need definitions for composite, industry ranking, stars, score, NIL value, and status. These are usually handled with explanatory text or info affordances, not dense stat-header tooltips.

**Pagination/infinite scroll:** common because recruit lists are long. Pages often show rank slices with pagination or load-more.

**Cross-links:** very strong. Every player, team, school, commitment, and ranking page is a link target. This is the main thing to borrow.

**Accessibility/performance/print:** mixed to weak. Ads, images, cards, and dynamic filters reduce print value. Repeated labels can help mobile comprehension but may lose table semantics.

### FotMob Mobile Reference

Source: https://www.fotmob.com/

FotMob is not a college football stats site, but it is a useful mobile pattern reference. It avoids giant tables in many mobile contexts. Match stats, player lists, and leaderboards are presented as compact rows/cards with a primary metric, rank, visual indicator, and drill-down link.

**DOM strategy:** mobile app/list pattern, not dense table first.

**Mobile:** reflow is the primary strategy. Instead of sticky first columns, the row is designed around the key entity plus one or two important metrics.

**Sorting/filtering:** tabs, chips, and segmented controls. This is excellent for narrow screens but less efficient for analysts comparing 12 columns.

**Tooltips:** minimal; labels and context do the work.

**Recommendation value:** use FotMob’s pattern only for summary modules, top-five callouts, and “intel cards,” not for canonical rankings tables.

## Cross-Site Pattern Conclusions

**Real tables still win for serious stats.** Sports Reference and TeamRankings are easier to scan, scrape, print, and trust. ESPN/CBS/FOX add media polish but often increase friction.

**URL-addressable sorting is better than JS-only sorting.** ESPN, CBS, FOX, Yahoo, On3/Rivals all encode category or sort in URLs. A static site should do the same.

**Definitions should not depend on hover.** Sports Reference-style header tooltips are useful, but CBS/FOX glossary text is more mobile-safe. Best pattern: short header + tap/hover definition + glossary below.

**Avoid linking every cell.** FOX-style all-cell links inflate keyboard stops. Sports Reference/TeamRankings’ primary-entity link pattern is cleaner.

**Virtualization is unnecessary for normal CFB team tables.** FBS has roughly 130-140 teams. Render the table. Use pagination only for player/recruiting-scale lists.

## Implementation Recommendations For A Python Static-Site CFB Rankings/Intel Site

Use **semantic, server-rendered HTML tables** as the canonical component:

```html
<table class="stats-table">
  <caption>2026 Team Passing Efficiency Rankings</caption>
  <thead>
    <tr>
      <th scope="col" aria-sort="ascending">Rk</th>
      <th scope="col">Team</th>
      <th scope="col"><a href="?sort=epa_pass&dir=desc">Pass EPA</a></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">1</th>
      <td><a href="/teams/indiana/">Indiana</a></td>
      <td>0.287</td>
    </tr>
  </tbody>
</table>
```

For mobile, use **horizontal scroll plus sticky identity columns**, not card reflow for canonical rankings. Freeze `Rk` and `Team`; keep all numeric columns available. Add a subtle scroll shadow and make the scroll region keyboard-focusable.

Use CSS like:

```css
.stats-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.stats-table {
  border-collapse: separate;
  border-spacing: 0;
  font-variant-numeric: tabular-nums;
}

.stats-table th:first-child,
.stats-table td:first-child {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--surface);
}
```

Default each page to the metric implied by the URL: `/rankings/passing-efficiency/` sorts by passing efficiency descending. Filters should be **static URL state**, e.g. `?season=2026&division=fbs&conf=sec&sort=pass_epa&dir=desc`. Pre-render the most important combinations during the Python build.

For sorting, use header links first and optional JS enhancement second. Update `aria-sort` on the active header. Do not require JavaScript for the default table.

For definitions, use a three-layer model: short headers, accessible `<abbr title>` or popover buttons, and a glossary below the table. This covers desktop hover, mobile tap, screen readers, and print.

For performance under **1.5s FCP**, keep the table HTML static, inline critical CSS, avoid blocking web fonts, lazy-load logos, and keep optional JS under 10 KB gzipped. Do not hydrate the table. Do not virtualize team tables. For player tables over 500 rows, paginate statically by 100 rows and provide CSV download.

For print, add `@media print` rules: remove sticky positioning, remove overflow wrappers, hide nav/filter chrome, expand glossary, repeat table headers, and avoid row breaks where possible.

The final design target should be: **Sports Reference semantics, TeamRankings speed, CBS/FOX URL sorting, ESPN glossary discipline, Yahoo/FotMob summary cards only for non-canonical highlights, and none of the heavy premium-grid cost unless the page truly needs it.**
