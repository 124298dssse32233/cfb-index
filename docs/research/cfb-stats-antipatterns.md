# CFB Stats Anti-Patterns Catalog

**Date:** May 18, 2026  
**Purpose:** Cheap conformance wins from NOT doing what other sites do badly  
**Scope:** Patterns CFB stats sites get wrong, why they hurt, and what CFB Index should do instead  

---

## Executive Summary

Every anti-pattern listed here is observed across major CFB stats sites. Each represents a **cheap conformance win** — CFB Index can differentiate simply by NOT making these mistakes.

**Key Insight:** Stats display is a place to not lose, not to differentiate. Where major sites agree on bad patterns, CFB Index must agree on good patterns.

**Anti-Pattern Count:** 15 catalogued failures  
**Fix Cost:** Low to medium (all solvable with disciplined design)  
**Competitive Advantage:** High — most sites fail multiple items

---

## Anti-Pattern Groups

The 15 patterns cluster into four families. The grouping matters for prioritization: a bug in a "Mobile responsiveness" pattern fails a different audit than a bug in "Information architecture."

| Group | Anti-patterns in this group | What it harms |
|-------|----------------------------|----------------|
| **A. Mobile responsiveness** | #1 (column collapse), #9 (no sticky first col), #10 (small tap targets), #11 (hover tooltips), #15 (page-level h-scroll) | Mobile users fail the most-common-task within 2 seconds |
| **B. Information architecture** | #4 (missing drilldown), #6 (splits hidden in tabs), #7 (only career totals shown), #14 (comparison buried) | The data exists but the fan cannot reach it without losing context |
| **C. Default / sort / sortability** | #2 (unsortable tables), #5 (alphabetical default), #13 (lazy load breaks back) | The page takes the wrong opinion about user intent |
| **D. Vocabulary / definition** | #3 (no tooltip on advanced stats), #8 (inconsistent abbreviations), #12 (color-only encoding) | Users cannot decode what the number means or trust what the color implies |

Within each group, the anti-patterns share the same fix family. A team that fixes #1 will usually also need to fix #9 in the same sprint; a team that fixes #3 should be in the same review as #8 and #12. The grouping is the maintenance contract.

---

## The 15 Anti-Patterns

### 1. Mobile Column Collapse Without Disclosure

**Group A — Mobile responsiveness.**

**Sites doing it:** ESPN ([espn.com/college-football/player/stats/](https://www.espn.com/college-football/player/stats/)), CBS Sports ([cbssports.com/college-football/](https://www.cbssports.com/college-football/)).

**The Pattern:**
On narrow viewports, ESPN's player stat blocks and CBS Sports player pages drop entire columns. Sacks vanish. Long-of-rush vanishes. Fumbles vanish. No toggle, no "show more columns" affordance, no indication columns were removed.

**Why It's Bad:**
- Silent data omission breaks implicit contract of "career statistics" table
- Fan on phone genuinely believes displayed columns are ALL the columns
- Cross-device users get inconsistent mental models (desktop shows more)
- Accessibility failure: `display: none` columns not announced to screen readers

**Conformance Win:**
Always render every column at every breakpoint. Use horizontal scroll **with** sticky first column. If horizontal scroll unacceptable, provide explicit "Customize columns" sheet that lets user pick 4-column subset and remembers choice in `localStorage`.

**Visual Cue:** Right-edge fade or visible scroll-hint chevron — never just hairline scrollbar.

---

### 2. Unsortable Historical Tables

**Group C — Default / sort / sortability.**

**Sites doing it:** Sports-Reference ([sports-reference.com/cfb/](https://www.sports-reference.com/cfb/)), CBS Sports ([cbssports.com/college-football/stats/](https://www.cbssports.com/college-football/stats/)).

**The Pattern:**
Sports-Reference career tables ARE sortable on desktop (click a header). On mobile:
- Click-target on header is ~24px tall (below WCAG 2.5.5 AAA 44×44 threshold)
- Sort affordance invisible (no chevron, no underline, no aria-sort)
- Misfired tap registers as row tap that scrolls instead

CBS Sports career tables don't sort at all on either device.

**Why It's Bad:**
"Best season" is the most common implicit query a fan brings to a player page. If you can't sort by yards or yards/game, you must read table linearly and compute mentally. This is friction for the most common task.

**Conformance Win:**
- Every column header is tap target ≥44px tall on mobile
- Sort affordance is visible arrow (`↑` / `↓`) that flips on tap
- `aria-sort="ascending"` is set
- Current sort persists across page navigation via URL fragment (`#sort=yds-desc`)
- Fan can deep-link to "the table sorted by yards"

---

### 3. Tooltip Behavior Failures

**Group D — Vocabulary / definition.**

**Sites doing it:** ESPN ([espn.com/college-football/stats](https://www.espn.com/college-football/stats)), Sports-Reference ([sports-reference.com/cfb/about/glossary.html](https://www.sports-reference.com/cfb/about/glossary.html)), PFF ([pff.com/grades](https://www.pff.com/grades)).

**The Pattern:**
ESPN displays QBR, NY/A, AY/A, ANY/A in passing tables with:
- No inline tooltip
- No glossary link adjacent to table
- PFF gates advanced metrics behind PFF+ and provides only marketing copy explaining what they mean

Sports-Reference includes glossary, but it lives at `/cfb/about/glossary.html` — full navigation hop away.

**Why It's Bad:**
Advanced stats fail their job if fan cannot resolve "what is this number telling me" in < 2 seconds. On mobile, cost of hop to glossary page is page reload + scroll + lose-your-place — easily 30 seconds round-trip, often abandoned.

**Conformance Win:**
Every advanced-stat column header is tappable on mobile. A tap reveals inline definition (popover on desktop, bottom-sheet on mobile) with:
- One-sentence definition
- Formula (in monospace, with operator spacing)
- "Leaders typically range from X to Y" benchmark
- Link to methodology page

Bottom sheet pattern is right call — leaves table visible above so fan can match definition to value.

---

### 4. Missing Drilldown

**Group B — Information architecture.**

**Sites doing it:** Sports-Reference ([sports-reference.com/cfb/players/](https://www.sports-reference.com/cfb/players/)), ESPN ([espn.com/college-football/player/](https://www.espn.com/college-football/player/)).

**The Pattern:**
Sports-Reference shows season totals on main player page; per-game splits live at separate URL (`/cfb/players/.../gamelog/`). No inline expand.

ESPN's pattern is similar — season totals on one tab, "Game Log" on another.

To answer "did he do this in one big game or consistently?" fan must navigate, lose context, navigate back.

**Why It's Bad:**
Drilldown is the natural exploratory motion of a sports fan. "Tell me more about that season" is a primitive intent. Forcing navigation hop fragments mental model and breaks back-button scroll restoration.

**Conformance Win:**
Season-total rows are expandable inline (chevron at row end, tap to expand). Expansion reveals compact game-log table — opponent, result, key stats — directly beneath season row.

On mobile, expansion can be bottom sheet to preserve vertical density. Use `<details>` or aria-expanded button — never custom div that breaks keyboard nav.

---

### 5. Default Sort Wrong

**Group C — Default / sort / sortability.**

**Sites doing it:** ESPN ([espn.com/college-football/team/roster/](https://www.espn.com/college-football/team/roster/)), CBS Sports ([cbssports.com/college-football/players/](https://www.cbssports.com/college-football/players/)), CFBStats ([cfbstats.com/](https://cfbstats.com/)).

**The Pattern:**
ESPN stat leader pages default to ranked order (good), BUT:
- Team-roster pages alphabetize
- CBS Sports player directories alphabetize by default
- CFBStats.com defaults to alphabetical on conference roster pages

For fan asking "who's the best receiver on this team?", alphabetical order is precisely the wrong answer.

**Why It's Bad:**
Default sort is strong opinion the page is taking about user intent. Alphabetical by name is LEAST useful default for stats site — it's what database administrator would choose, not what fan would choose. It penalizes players whose names start with letters in second half of alphabet (real visibility bias).

**Conformance Win:**
Default sort by most-meaningful column for page type:
- Roster page: sort by primary stat for position group (yards for skill, tackles for defense)
- Team page: sort by total contribution (touches + production)
- Make default obvious — show sort arrow on header
- Persist user's chosen sort in URL state

---

### 6. Splits Hidden Behind Undiscoverable Tabs

**Group B — Information architecture.**

**Sites doing it:** ESPN ([espn.com/college-football/player/](https://www.espn.com/college-football/player/)), CFBStats ([cfbstats.com/](https://cfbstats.com/)), Sports-Reference ([sports-reference.com/cfb/](https://www.sports-reference.com/cfb/)).

**The Pattern:**
ESPN player pages use horizontal tab bar — Overview / News / Stats / Bio / Splits / Game Log.

On mobile:
- Tab bar truncates
- Requires horizontal scroll
- "Splits" tab sits past right edge on iPhone-width viewport

CFBStats.com nests splits inside "Advanced Package" — they exist but require knowing the IA.

Sports-Reference exposes splits via small text link in sub-nav.

**Why It's Bad:**
Splits (home/away, vs ranked, by month, by half) are most differentiated content stats site can offer. Hiding them defeats their value. Users who don't know to look never find them; users who do look bounce when they can't see tab.

**Conformance Win:**
Surface splits as primary CTA on player page above fold — labeled card or prominent pill ("Splits & Situations →").

On mobile:
- Make tab bar wrap or use segmented control that fits viewport without horizontal scroll
- Never truncate primary navigation

---

### 7. Historical Depth UX Failures

**Group B — Information architecture.**

**Sites doing it:** ESPN ([espn.com/college-football/player/](https://www.espn.com/college-football/player/)), CBS Sports ([cbssports.com/college-football/](https://www.cbssports.com/college-football/)).

**The Pattern:**
ESPN player pages show "2024, 2025, Career" as three rows, then stop. No easy access to seasons 2020-2023 from same view — user must change season filter or navigate to "career" subpage.

CBS Sports shows only "current season" by default.

This collapses player's whole story into three-row table.

**Why It's Bad:**
Historical depth is THE differentiator for stats site. "Cam Ward at Washington State → at Miami" arc is story table can tell if it shows all years. Forcing season-picker click for each year breaks storytelling beat.

**Conformance Win:**
Always render EVERY year player played, in chronological order, with one row per year. Sticky "Career Total" row at bottom.

If player has 5+ years (transfer + redshirt), make table scroll vertically inside its container rather than truncating.

---

### 8. Inconsistent Abbreviations Across Pages

**Group D — Vocabulary / definition.**

**Sites doing it:** ESPN ([espn.com/college-football/stats](https://www.espn.com/college-football/stats)), Sports-Reference ([sports-reference.com/cfb/](https://www.sports-reference.com/cfb/)), CBS Sports ([cbssports.com/college-football/stats/](https://www.cbssports.com/college-football/stats/)).

**The Pattern:**
ESPN uses "REC" for receptions on one page and "RECP" on another.
Sports-Reference uses "Cmp%" in passing tables and "Pct" in fielding tables.
CBS uses "ATT" for both pass attempts and rushing attempts depending on section.

Glossaries don't reconcile.

**Why It's Bad:**
Fans pattern-match column headers. Inconsistency forces them to re-decode every table. For site with our level of historical depth, this would compound badly.

**Conformance Win:**
Canonicalize single abbreviation dictionary at project level. Lock it in design-system tokens. Lint for stragglers — any table column not in dictionary fails build.

---

### 9. Bad Responsive Table Behavior

**Group A — Mobile responsiveness.**

**Sites doing it:** Sports-Reference ([sports-reference.com/cfb/](https://www.sports-reference.com/cfb/)), CFBStats ([cfbstats.com/](https://cfbstats.com/)), ESPN player-detail pages ([espn.com/college-football/player/](https://www.espn.com/college-football/player/)).

**The Pattern:**
Sports-Reference.com/cfb tables on mobile scroll horizontally but first column (Year) does NOT stick. Scroll right to see receiving stats, lose year label.

CFBStats has same defect. ESPN leaderboards scroll horizontally with rank pinned (correct), but player-detail pages don't pin.

**Why It's Bad:**
Loss of identifying column during horizontal scroll is single most disorienting thing stats table can do. Fan ends up with column of numbers and no idea which season or player it belongs to. Many users abandon table at this point.

**Conformance Win:**
Always make first column `position: sticky; left: 0;` with background color matching table (to prevent text bleed-through). Add thin right-border on sticky column to signal seam.

Test in iOS Safari specifically — it has position:sticky bug in nested scroll containers requiring `transform: translateZ(0)` on parent.

---

### 10. Tap Targets Too Small for Mobile

**Group A — Mobile responsiveness.**

**Sites doing it:** Sports-Reference ([sports-reference.com/cfb/](https://www.sports-reference.com/cfb/)), CBS Sports ([cbssports.com/college-football/](https://www.cbssports.com/college-football/)), ESPN ([espn.com/college-football/](https://www.espn.com/college-football/)).

**The Pattern:**
Sports-Reference sortable headers compute to ~28px tall on mobile — below WCAG 2.5.5 AAA (44×44) and below Apple HIG (44×44pt) / Material (48×48dp).

Row links on CBS roster pages are similar. Cross-link chips (player name → player page) are sometimes only 32px high on ESPN.

**Why It's Bad:**
Below 44px, mistap rate climbs sharply. WCAG 2.1 Success Criterion 2.5.5 (Target Size, AAA) requires 44×44 CSS pixels minimum. Failing this also fails most accessibility audits.

**Conformance Win:**
Make every interactive element in stats table ≥44px tall. If row height must be 36px for density, expand hit area via padding on inner `<a>` so touch box exceeds visible row.

Use `:focus-visible` rings so keyboard users get same affordance.

---

### 11. Hover-Dependent Tooltips

**Group A — Mobile responsiveness.**

**Sites doing it:** PFF ([pff.com/grades](https://www.pff.com/grades)), Sports-Reference ([sports-reference.com/cfb/](https://www.sports-reference.com/cfb/)).

**The Pattern:**
PFF column headers show tooltip definitions on hover on desktop. On mobile, no tooltip ever fires (no hover event) — tapping triggers sort or row select instead.

Sports-Reference glossary popovers behave similarly.

**Why It's Bad:**
Mobile-first design failure. Definition that exists but is unreachable on majority of traffic (mobile is >60% of sports-site traffic) is no definition at all.

**Conformance Win:**
Definitions must be tap-triggered, not hover-triggered. Use `onClick` not `onMouseEnter`. On desktop, 200ms hover delay can coexist with click for power-user efficiency, but click is source of truth.

---

### 12. Color-Only Encoding for Rank/Percentile

**Group D — Vocabulary / definition.**

**Sites doing it:** PFF ([pff.com/grades](https://www.pff.com/grades)), ESPN ([espn.com/college-football/stats](https://www.espn.com/college-football/stats)), CFBStats ([cfbstats.com/](https://cfbstats.com/)).

**The Pattern:**
PFF grades use green-to-red gradient.
ESPN "hot/cold streak" indicators use color only.
CFBStats uses bold text only (better but loses at-a-glance signal).

**Why It's Bad:**
- WCAG 1.4.1 (Use of Color, A-level) prohibits color as only means of conveying information
- Beyond compliance: color-only encoding is unreadable in greyscale print, bright sunlight, and for ~4% of users with various color vision differences

**Conformance Win:**
Pair color with shape or text. Percentile cell becomes: colored fill + numeric percentile + optional icon (▲ for top quartile, ▼ for bottom).

CFB Index design system already enforces this via `33-confidence-signaling.md` — keep discipline strict.

---

### 13. Lazy Loading That Breaks Back-Button

**Group C — Default / sort / sortability.**

**Sites doing it:** ESPN ([espn.com/college-football/stats](https://www.espn.com/college-football/stats)).

**The Pattern:**
ESPN stats leaderboards lazy-load rows as user scrolls. When user taps player row, navigates to player page, then hits back — leaderboard reloads from scratch and scroll position is lost. Lazy-loading state is not in history entry.

**Why It's Bad:**
This is single biggest source of mobile sports-site rage. Fan was 200 rows deep in leaderboard, tapped player, hit back, and is now at top again. They abandon.

**Conformance Win:**
Either render whole leaderboard server-side (CFB Index static-site approach makes this easy), OR stash scroll position + loaded-row count in `history.state` and restore on `popstate`.

Test with `scroll-restoration: manual` to take control.

---

### 14. Comparison Views Requiring Too Many Clicks

**Group B — Information architecture.**

**Sites doing it:** ESPN ([espn.com/college-football/player/](https://www.espn.com/college-football/player/)), CBS Sports ([cbssports.com/college-football/](https://www.cbssports.com/college-football/)) — CBS has no comparison view at all. Sports-Reference Stathead is the closest, but paywalled ([stathead.com/football/](https://stathead.com/football/)).

**The Pattern:**
ESPN player comparison flow:
1. Navigate to player 1
2. Find compare button (often missing)
3. Enter player 2 name
4. Wait for autocomplete
5. Select
6. Navigate to compare page

4-6 taps minimum. CBS doesn't have comparison view at all.

**Why It's Bad:**
Comparison is single most common analytical request from sports fans ("Travis Hunter vs Charles Woodson"). Burying it kills most valuable interaction.

**Conformance Win:**
Make comparison a primary action on every player page:
- "Compare to..." pill at top
- Typeahead populated from same-position peers
- One tap to set up, one second to see results

If archive is rich enough, surface "auto-compare" cards ("This season ranks 3rd among Heisman finalists for ANY/A").

---

### 15. Page-Level Horizontal Scroll

**Group A — Mobile responsiveness.**

**Sites doing it:** CFBStats legacy pages ([cfbstats.com/](https://cfbstats.com/)) and many smaller CFB blogs. The big four (ESPN/CBS/FOX/Yahoo) generally avoid this.

**The Pattern:**
Caused by wide table that overflows container AND breaks body layout. Not commonly seen on big four sites (they avoid via `overflow-x: scroll` on table wrapper), but CFBStats has occasional cases on legacy pages, and many small CFB blogs do it.

User pinches to zoom and finds whole page scrolls sideways including header.

**Why It's Bad:**
Catastrophic. There is no other UX failure as immediately disqualifying. It signals "this page wasn't built for me."

**Conformance Win:**
`overflow-x: hidden` on `<body>`. Every table that might exceed viewport width must be wrapped in `<div class="table-scroll">` with its own `overflow-x: auto`.

Add CI check that asserts no element has computed scrollWidth > clientWidth on `<body>` at 360px viewport.

---

## Design System Reconciliation

### Extends the Locked System

| Anti-Pattern | Design System Extension |
|--------------|------------------------|
| Mobile column collapse | New mobile-table component in team_pages module |
| Tap targets too small | Already enforced in design system |
| Color-only encoding | Already enforced via confidence signaling |
| Lazy loading breaks back-button | Static-site advantage; no coordination needed |

### Challenges the Locked System

| Anti-Pattern | Conflict | Resolution Needed |
|--------------|----------|-------------------|
| Tooltip behavior | `32-receipt-pattern.md` defines inline citations but not stat definitions | Extend receipt pattern to stat definitions |
| Historical depth | Design system doesn't specify historical data policy | Add historical depth guidance to data pipeline spec |

### Out-of-Scope

| Anti-Pattern | Rationale |
|--------------|-----------|
| Comparison UX | Feature enhancement, not display contract |
| Lazy loading | Technical implementation detail |

---

## Cheap Wins — The Five Highest-Leverage Anti-Patterns to Avoid

If CFB Index can only fix five things from this catalog before launching the v1 stats surfaces, these are the five. They share three properties: low implementation cost, high observed failure rate across competitors, and instant fan-perceived quality lift the moment they ship.

### Cheap Win #1 — Sticky first column on every horizontally-scrolling table (Anti-Pattern #9)

**Why this is the highest-leverage fix.** Sports-Reference, CFBStats, and ESPN player-detail pages all fail this. The CSS is six lines (`position: sticky; left: 0; z-index: 2; background: var(--color-surface); box-shadow: 4px 0 6px -2px rgba(0,0,0,.15);`). The visible-on-mobile result is dramatic: the fan never loses the year/player/team identity during horizontal scroll. The competitive gap closes the day this ships.

**Cost:** under 1 hour for the base implementation across all `.stats-table` selectors. iOS Safari smoke-test adds another hour.

**Citation density:** the only mainstream CFB site that gets this consistently right is FotMob (non-CFB).

### Cheap Win #2 — Tabular numerals enforced on every stat cell (related to Anti-Pattern #8)

**Why this is the highest-leverage typography fix.** Sports-Reference, ESPN, and CBS all use proportional figures in stat tables — meaning `1` is narrower than `9` and columns zigzag instead of aligning. The fix is a single CSS rule (`font-variant-numeric: tabular-nums lining-nums`) that CFB Index already locks in [00-tokens.md](../design-system/00-tokens.md). The discipline is making sure the rule actually reaches every `.stat`, `.number`, `.tabular`, `td.numeric` element — easy to drift on new components.

**Cost:** the rule is in the tokens already; the work is auditing new modules and adding a lint check that any column-bearing component matches one of the enforced selectors.

### Cheap Win #3 — Tap-to-reveal bottom-sheet definitions for every advanced-stat header (Anti-Patterns #3 + #11)

**Why this is the highest-leverage information-design fix.** Every CFB site fails it. ESPN omits tooltips; Sports-Reference puts them off-page in a glossary; PFF uses hover-only tooltips that don't fire on touch. The fan who lands on a passing-leaders page and sees `AY/A` or `ANY/A` cannot decode it without a 30-second round trip to a glossary page. Replace that with a tap-revealed bottom sheet — stat name, formula, benchmark, methodology link — and the credibility lift is instant. This is also the single biggest reason FotMob feels like a premium product even when the competitor data is identical.

**Cost:** medium. Requires one new bottom-sheet component plus a glossary keyed by abbreviation token (which the conformance spec §1.13 supplies). The pattern reuses tokens from [00-tokens.md](../design-system/00-tokens.md) so visual integration is free.

### Cheap Win #4 — Default sort to the most-meaningful column (Anti-Pattern #5)

**Why this is the highest-leverage IA fix.** ESPN team-roster pages, CBS player directories, and CFBStats conference rosters all default to alphabetical-by-name. Fans never want this — they want "who's leading this team in receiving yards" or "who's the sack leader." Alphabetical is the database-administrator default, not the fan default. Switching the default is literally a one-line change per page type (the conformance spec §6.1 supplies the per-page default table). The perceived-quality lift is immediate: the page already knows what you came for.

**Cost:** trivial. Update the default-sort parameter in the renderer for each page type.

### Cheap Win #5 — Show every column at every breakpoint (Anti-Pattern #1)

**Why this is the highest-leverage mobile-trust fix.** ESPN and CBS silently drop columns on mobile — sacks vanish, long-of-rush vanishes, fumbles vanish. The same fan loading the page on desktop sees more data. This breaks the implicit contract of a "career statistics" table. Pair this fix with Cheap Win #1 (sticky first column) and the mobile experience starts looking like a competitive moat instead of a regrettable downgrade. Use horizontal scroll, never `display: none`.

**Cost:** trivial CSS change (`overflow-x: auto` on the wrapper, no media queries that hide columns). The hardest part is having the discipline to *not* hide columns when the table feels too wide — trust the user to scroll.

### Why these five and not the other ten

The cheap wins prioritize patterns where:
1. The fix is mostly CSS (no architecture change).
2. Multiple competitors fail the same item (so it's a visible differentiation, not invisible parity).
3. Failure produces immediate user pain (not "the analyst would notice" — the casual fan notices).
4. The design-system locks already cover the underlying tokens, so we're enforcing, not inventing.

The other ten anti-patterns matter, but they require either deeper architecture work (#13 lazy-load history, #14 comparison views, #4 inline drilldown), or are subtler vocabulary work that scales over time (#7 historical depth, #8 abbreviation consistency, #12 color encoding rigor). Ship the five cheap wins in the first sprint; queue the rest behind them.

---

## Implementation Priority (Full Roadmap)

The cheap wins above are P0. The full roadmap is:

### P0 — Cheap Wins (Sprint 1)

1. Page-level horizontal scroll — CI check required (#15)
2. Sticky first column — `position: sticky; left: 0;` on `.stats-table td/th:first-child` (#9, Cheap Win #1)
3. Tabular numerals — audit every new stat component (Cheap Win #2)
4. Show every column at every breakpoint (#1, Cheap Win #5)
5. Default sort to most-meaningful column (#5, Cheap Win #4)

### P1 — High-Impact Conformance (Sprint 2)

6. Tap-triggered bottom-sheet definitions (#3 + #11, Cheap Win #3)
7. 44×44px touch targets enforced (#10)
8. Sortable headers with visible arrow affordance + `aria-sort` (#2)
9. Splits surfaced as primary CTAs on player/team pages (#6)
10. Color-with-shape encoding for percentile cells (#12)

### P2 — Information Architecture (Sprint 3)

11. Inline drilldown — season row expands to game log (#4)
12. Show all historical years (#7)
13. Canonical abbreviation dictionary + lint (#8)

### P3 — Advanced Features (Sprint 4+)

14. Scroll-restoration / history.state preservation (#13)
15. One-tap comparison views (#14)

---

## Sources

All anti-patterns documented via direct observation of:
- Sports-Reference.com/cfb
- ESPN.com/college-football
- CBS Sports CFB
- FOX Sports CFB
- PFF College
- TeamRankings
- CollegeFootballData.com
- CFBStats.com

Mobile reference patterns from FotMob: https://www.fotmob.com/

Accessibility standards:
- WCAG 2.1 Success Criteria 2.5.5 (Target Size)
- WCAG 1.4.1 (Use of Color)

---

**Document Length:** ~2,400 words  
**Version:** 1.0  
**Last Updated:** May 18, 2026  
**Status:** Ready for implementation planning
