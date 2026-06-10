# Rankings Redesign — Deep Research Dossier

**Compiled 2026-06-08.** Four parallel deep-research streams (web-sourced) feeding the v3 spec.
Companion to [`rankings_redesign_spec.md`](rankings_redesign_spec.md) and [`rankings_redesign_brief.md`](rankings_redesign_brief.md).
Confidence + source caveats preserved inline; this is decision-grade, not exhaustive.

---

## A. Mobile sports-data UX patterns (FotMob · Sofascore · ESPN · The Athletic · theScore · Robinhood · Polymarket · DK/FD)

**Adopt list (12):**
1. **Card-as-row, not a squeezed table** — each team = a self-contained card. [WebOsmotic 2025](https://webosmotic.com/blog/tables-best-practice-for-mobile-ux-design/)
2. **One dominant number per card** (FotMob 0–10) — lead with the composite; demote sub-stats. [FotMob](https://www.scribd.com/document/920258497/Stats-Definitions-FotMob)
3. **Tap-to-expand, 3 disclosure layers** (card → in-place expand → full page); never lose scroll position. [Robinhood](https://worldbusinessoutlook.com/how-the-robinhood-ui-balances-simplicity-and-strategy-on-mobile/)
4. **Inline movement + scrubbable sparkline** (▲3 + press-drag for any past week). [Robinhood Spark](https://github.com/robinhood/spark)
5. **Color as functional language** (green-up / red-down / grey-unset) — ties to our confidence bands.
6. **Frozen label column + horizontal scroll** for the "raw grid" mode; sticky header ≤3 cols, freeze at ≥4. [Ninja Tables 2025](https://ninjatables.com/sticky-headers-vs-fixed-columns/)
7. **Two-up compare tray** — pick 2 teams → side-by-side overlay. [SAP Fiori comparison](https://www.sap.com/design-system/fiori-design-web/v1-120/ui-elements/comparison-pattern)
8. **Bottom tab bar + personalized "My Teams" home** (followed teams float up). [theScore](https://www.thescore.com/news/2053218)
9. **Swipeable favorites carousel + sticky context header** (ESPN 2025). [ESPN Front Row](https://www.espnfrontrow.com/2025/08/dtc-launch-week-a-sports-fans-guide-to-the-enhanced-espn-app/)
10. **Filter/sort as visible chips above the list** — single cycling sort toggle, no buried menus.
11. **Premium micro-interactions** — roll numbers 200–300ms, haptics, instant confirm toasts. [avark 2026](https://avark.agency/learn/prediction-market-design-patterns)
12. **Liveness signal** — "Updated 2h ago" with a gentle pulse + skeleton loads (never spinners).

**Densest single reference:** the [avark prediction-market design patterns guide (2026)](https://avark.agency/learn/prediction-market-design-patterns) — card anatomy, progressive disclosure, micro-interaction specs map ~1:1 to a rankings card-feed.
**Negative lesson (The Athletic):** a pretty feed that stutters reads as broken — perceived speed + predictable nav are load-bearing.

---

## B. Revered ratings/stats presentations (KenPom · Baseball Savant · FBref · SP+ · FPI · 538 · Metaculus · Polymarket · Massey)

**Adopt list (10):**
1. **Rank-beside-every-number, one dense sortable table** (KenPom) — show each stat's value AND its rank inline. [KenPom glossary](https://kenpom.com/blog/ratings-glossary/)
2. **Diverging red→neutral→blue percentile sliders as the team "fingerprint"** (Baseball Savant). [MLB new-look](https://www.mlb.com/news/baseball-savant-statcast-player-pages-new-look)
3. **Percentile-vs-peer with the comparison pool STATED** (FBref) — print the denominator. [FBref scouting reports](https://fbref.com/en/about/scouting-reports-explained)
4. **Loudly separate predictive Power from earned Résumé** (SP+) — say what each is/isn't. [2026 SP+](https://www.espn.com/college-football/story/_/id/48306284/2026-college-football-sp+-rankings-138-fbs-teams)
5. **Simulate the season → probability table of stakes** (FPI: % win div / make CFP / win title). [NFL FPI](https://www.espn.com/nfl/fpi)
6. **Show the distribution, not the point estimate** — histogram + representative dots (538). [538 2020 design](https://fivethirtyeight.com/features/how-we-designed-the-look-of-our-2020-forecast/)
7. **Name the pivot** — a "snake"/tipping-point strip for the playoff bubble (538). [the snake](https://medium.com/@kevindewalt/fivethirtyeights-snake-is-data-visualization-genius-f9901be5a74a)
8. **Publish a calibration curve as a self-audit** (Metaculus). [track record](https://www.metaculus.com/questions/track-record/)
9. **Market accuracy: time-resolved track record + Brier** (Polymarket /accuracy page). [Polymarket accuracy](https://polymarket.com/accuracy)
10. **Consensus + self-grading meta-layer** (Massey "ranking-violation %"). [Massey composite](https://masseyratings.com/cf/compare.htm)

**The thread:** loved systems disclose *what the number is, what pool it's measured against, how much uncertainty surrounds it, and how often it's been right* — each legible **as a picture**, not prose.

---

## C. Novel mechanics to adapt (originality — outside CFB)

| # | Mechanic | Source | CFB-rankings adaptation | Novelty |
|---|---|---|---|---|
| 1 | **Skewed forecast fan chart** | [BoE fan charts](https://www.bankofengland.co.uk/quarterly-bulletin/1998/q1/the-inflation-report-projections-understanding-the-fan-chart) | Team strength/rank "fan chart" over remaining schedule; 9–0 team = downside-skewed fan | first-mover |
| 2 | **Hypothetical Outcome Plots (animated draws)** | [Hullman/Kay](https://pubmed.ncbi.nlm.nih.gov/30136961/) | "Possible final Top 25" animated loop — *feel* the variance; share asset | high |
| 3 | **Quantile dotplot (20 dots)** | [Kay et al.](https://users.eecs.northwestern.edu/~jhullman/research.html) | Playoff odds as "14 of 20 outcomes" in a table cell — honest, no boundary misread | first-mover |
| 4 | **Cone of uncertainty (anti-containment labeled)** | [NHC cone](https://www.nhc.noaa.gov/aboutcone.shtml) | Schedule "ranking cone" sized by our OWN week-N→final error; label "1 in 3 finish outside" | needs §10 data |
| 5 | **"You Draw It" predict-before-reveal** | [NYT Upshot](https://larryferlazzo.edublogs.org/2017/04/15/fascinating-depressing-you-draw-it-interactive-infographic-from-ny-times/) | "Draw this team's season" then reveal model line + score your error | first-mover |
| 6 | **Scrollytelling step-transitions** | [The Pudding](https://pudding.cool/process/how-to-make-dope-shit-part-3/) | Weekly "how the rankings moved" — one bump chart, narrated by scroll | underused |
| 7 | **Connected scatterplot (paired time series)** | [Haroz/Kosara](https://visualthinking.psych.northwestern.edu/publications/Connected_Scatterplot_Haroz_Kosara_Franconeri_2015.pdf) | Season as Offense(x) vs Defense(y) path — pivots become a signature | rare in CFB |
| 8 | **Bump chart, overtake-emphasis** | [DataViz Catalogue](https://datavizcatalogue.com/blog/chart-snapshot-bump-charts/) | Top-25 bump where every crossing is annotated ("Wk8: Ole Miss passes LSU") | differentiated |
| 9 | **"Rankings Wrapped" share card** | [Spotify Wrapped 2025](https://newsroom.spotify.com/2025-12-03/2025-wrapped-user-experience/) | Season-end swipeable share stack per team — biggest jump, percentile vs 134 | high-leverage |
| 10 | **Model calibration / accountability page** | [Metaculus](https://www.metaculus.com/questions/track-record/) | "How calibrated is our model?" curve + season Brier + plain verdict | first-mover in CFB |
| 11 | **Brier badge + poll leaderboard** | [Metaculus scoring](https://www.metaculus.com/notebooks/22486/a-primer-on-the-metaculus-scoring-rule/) | Score AP / Coaches / Committee vs realized outcomes — "whose ranking is right?" | spicy; after §10 |
| 12 | **"Program Stripes" (warming stripes)** | [warming stripes](https://en.wikipedia.org/wiki/Warming_stripes) | One stripe per season, color = final rank vs program baseline; merch-ready row-header | first-mover |

**Bonus:** Marey "gauntlet" SoS terrain chart (speculative); GitHub-Skyline-style 3D "Program Skyline" share asset (stretch).
**⚠️ Universal pitfall — the "containment effect":** every band/cone (#1, #4) gets misread as a hard in/out boundary (NHC's documented problem). **Prefer discrete framings (#3 quantile dotplots, #2 HOPs) wherever the misread stakes are high.**
**Build order (precedent → risk):** #9 Wrapped, #12 Stripes, #10 calibration, #8 bump first; #4 & #11 depend on #10's calibration data existing first.

---

## D. Dense-data web craft 2026 (the path to a <50KB-JS interactive board)

**Support: ✅ safe now · ⚠️ use with fallback · 🧪 enhancement-only.**
1. ✅ **Semantic `<table>` in a scrollable `role=region` wrapper** (`tabindex=0`); NEVER `display:block` a table (kills SR semantics). [Roselli](https://adrianroselli.com/2020/11/under-engineered-responsive-tables.html)
2. ✅ **Sticky first column** (`position:sticky;left:0`, `border-collapse:separate`) — comparable spine on scroll. [NN/g](https://www.nngroup.com/articles/mobile-tables/)
3. ✅ **CSS scroll-snap on column groups** + `scroll-padding-left` for the frozen spine.
4. ✅ **`<details name>` exclusive accordions** for expandable rows — ZERO JS (Baseline Sep 2025). [MDN](https://developer.mozilla.org/en-US/blog/html-details-exclusive-accordions/)
5. ✅ **`aria-sort` + `aria-live` status** for sortable columns (sort needs ~1KB JS; announce for SR parity). [Roselli](https://adrianroselli.com/2021/04/sortable-table-columns.html)
6. ⚠️ **CSS-only `:has()` filtering** (`:has(input:checked)`) — Baseline ~92%; guard with `@supports`. [css-tricks](https://css-tricks.com/the-radio-state-machine/)
7. ✅ **Popover API** for filter panels/menus — declarative top-layer, Esc/click-out, implicit `aria-expanded`. [Smashing](https://www.smashingmagazine.com/2026/03/getting-started-popover-api/)
8. ⚠️ **CSS anchor positioning** for tooltips — replaces Floating-UI/Popper (Baseline 2026, keep static fallback). [caniuse](https://caniuse.com/css-anchor-positioning)
9. ✅ **`content-visibility:auto` + `contain-intrinsic-size`** on board chunks — web.dev measured **~7× faster initial render**; the single biggest 668-row win. [web.dev](https://web.dev/articles/content-visibility)
10. 🧪 **Cross-document View Transitions** (row→team-page morph) — NOT Baseline (Firefox flagged); pure enhancement. [Chrome](https://developer.chrome.com/docs/web-platform/view-transitions/cross-document)
11. ⚠️ **Speculation Rules** prerender next page on hover — Chromium ~79%, no fallback cost. [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Speculation_Rules_API)
12. ✅ **Container queries** for cards that re-lay-out on their own width. [caniuse](https://caniuse.com/css-container-queries)
13. ✅ **Accessible SVG sparklines** (`role=img` + trend `aria-label` + hidden data-table fallback). [USWDS](https://designsystem.digital.gov/components/data-visualizations/)
14. ⚠️ **`prefers-reduced-motion` + scroll-driven animations** (off main thread; Safari laggard).
15. ⚠️ **`text-wrap:balance/pretty`** for headers + **`:has()` as a JS-deleter** for selected-row/active-filter styling.

**JS-budget math:** items 1,2,3,4,6,7,8,9,12,13,14,15 are **0 JS**. Only client sort (#5) + optional filter-counts/prerender need a few KB of Alpine — **a dense, interactive, 668-row board fits comfortably under 50KB.** This is the concrete answer to the perf risk Gemini raised.

---

## Synthesis → what changes in the spec (v3)
1. **Board = KenPom rank-beside-every-number**, rendered as a card-feed (mobile) / sticky-spine table (desktop), powered by `content-visibility` + `<details name>` + `:has()` filtering = near-zero JS.
2. **Uncertainty done right:** replace naive rank "bands" with **quantile dotplots** (playoff odds) + **fan charts** (season projection) + **HOPs** (share asset) — avoids the containment misread.
3. **Model Report Card gets a concrete form:** calibration curve + season Brier + accuracy-vs-weeks-out strip + plain verdict; later, a **poll-accountability leaderboard** (score AP/Coaches/Committee).
4. **Originality slate:** Tri-Rank + Cross-Division Bridge (ours) joined by **Program Stripes**, **Rankings Wrapped**, **connected-scatterplot season portrait**, **"You Draw It"**, **overtake-bump scrollyteller**.
5. **Fingerprint + denominator transparency:** Baseball-Savant percentile sliders in the drawer, each with its stated peer pool (FBref discipline) → reinforces receipts/confidence.
6. **Micro-interaction + nav layer:** roll-numbers, haptics, liveness pulse, scrubbable sparkline; bottom tab bar + My-Teams personalization + swipeable favorites.
7. **Craft commitments become specific** (the §D stack), making the perf budget achievable, not aspirational.

## Standing caveats
- **538 is defunct** (cite interactives as reference, not a live product). **FBref pool sizes vary** (state ours explicitly). **Polymarket accuracy figures are a live snapshot.** **Containment effect** governs all band/cone choices. **View Transitions + Speculation Rules are enhancement-only** — never gate content on them.
