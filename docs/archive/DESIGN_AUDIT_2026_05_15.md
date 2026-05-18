# CFB Index — Triple Audit

**Date:** 2026-05-15
**Auditor:** Claude (autonomous)
**Live site:** https://wonderful-margulis-8ec96b.vercel.app
**Branch:** claude/romantic-euclid-fd39e3
**Scope:** Visual / UX (Part A) · Code & Architecture (Part B) · Proprietary-Advantage Visibility (Part C)
**Methodology:** Navigated 18 pages on the live site via the Chrome MCP, introspected the DOM (computed styles, font stacks, chart counts, module presence) on each, then cross-referenced findings against the source renderers, the canonical design-token spec (`docs/design-system/00-tokens.md`), the shipped CSS (`output/site/assets/cfb-index.f3924a06eced.css`, `src/cfb_rankings/team_pages/assets/*.css`, `tools/wcfb_enhancements/wcfb-enhancements.css`), and the proprietary-data architecture documented in `FAN_INTEL_SOURCE_STRATEGY.md`, `TEAM_PAGE_WORLD_CLASS_BRIEF.md`, and the `docs/design-system/` module specs.

---

## Executive Summary

### TL;DR (three bullets)

- **The site has one world-class section and seven generic ones.** `/teams/<profiled-slug>.html` (17 programs, e.g. Alabama) and `/hub/` are genuinely Athletic-tier — bespoke modules, percentile bars, sparklines, 28 inline charts, magazine numbering. Everything else — Wire, Daily, Mailbag, Reactions, Canon, Storylines, Conferences, Heisman, Players, History — is a wall of text with zero charts and falls back to Georgia or Times New Roman on at least three pages.
- **The proprietary-data moat is real but invisible outside two pages.** Bluesky, Wikipedia, campus newspapers, podcasts, SeatGeek, GDELT, prediction markets, beat-writer RSS are all ingested (13 source adapters in `src/cfb_rankings/ingest/sources/`) and computed into `fan_intelligence.py` features (belief, reality_gap, respect_gap, cohesion, swing, rival_heat, archetype, sarcasm_risk, _confidence). Of those, **only `/hub/` visualizes them at scale and only profiled team pages surface a watered-down Pulse module.** `team_savant_weekly`, `fanbase_mood_weekly`, `source_observations`, `storyline_threads`, `games_predictive_claims`, `claim_outcomes`, `player_conversation_features`, `team_pulse_cache` — **none of these are referenced anywhere in `reporting.py`** (verified by grep). The Reactions page is the cohort-divergence moat shipped as four plain-text headlines on a dark page.
- **There are four competing design-token systems and a mobile nav that pretends the desktop site doesn't exist.** Canonical spec `00-tokens.md` describes 6 ramps × 7 stops with `--color-navy-400`/`--color-text`. Shipped `team_pages/assets/tokens.css` ships a dark-default system with `--bg-0`/`--fg-primary`/`--pct-low`. `tools/wcfb_enhancements/wcfb-enhancements.css` adds a third layer prefixed `--wcfb-*`. `docs/design-system/unified-design-tokens.md` (dated 2026-05-13, two days ago) is a fourth, just-written reconciliation attempt that acknowledges "4+ design languages." The mobile bottom nav exposes 5 destinations (`/`, `/rankings/`, `/hub/`, `/compare/`, `/methodology/`) using **emoji glyphs** — 🏠📊💡⚖️📚 — and omits Teams, Players, Heisman, Programs, History, Editions, Wire entirely.

### Overall rating vs. ESPN / 538 / Athletic

| Section | Rating | Note |
|---|---|---|
| `/hub/` (Fan Intel Hub) | **8.5 / 10** | The crown jewel. Magazine numbering, 28 charts, sentence-led headlines, mood-mover bars. The only page on the site I would screenshot for an investor deck. |
| Profiled `/teams/<slug>.html` (17 slugs) | **7.5 / 10** | Hero + Pulse + Savant + Rivalry + Era arc is genuinely premium architecture. Pulse drops to "Awaiting Signal" in mid-May because the offseason ingest hasn't landed signal; rivalry trajectory is a placeholder IMG. |
| Homepage (Editions cover) | **7 / 10** | Editorial newspaper aesthetic — Source Serif Pro, roman-numeral section numbering, beat-writer "Aged Well %" — is genuinely distinctive. Lacks any chart anchor above the fold. |
| Unprofiled `/teams/<slug>.html` (647 slugs) | **4 / 10** | Sans-serif light theme. No logo (no `<img>` rendered). Substantial sections present (Performance Narrative, Game Impact Board, Betting Lens, Efficiency Dashboard) but they read as raw text with no visual hierarchy. Different design language from profiled siblings. |
| Wire | **4 / 10** | 110-row table, no filters, no source-attribution chips, 9,533px scroll. |
| Daily | **3.5 / 10** | Three text paragraphs. Georgia (not Source Serif). Zero images. |
| Mailbag | **4 / 10** | Six Q&A pairs of pure prose, 6,601px scroll. |
| Reactions | **3 / 10** | Three text-link cards on a dark page. This is the cohort-divergence moat shipped as a blog index. |
| Canon | **5 / 10** | Three list entries with sentence-led headlines. No cover art, no per-list visual identity. Individual entry (CJ Stroud) has zero images and zero charts. |
| Storylines | **5 / 10** | Eight thread titles. No Active/Dormant pills, no chapter counts visualized, no thread-anatomy graphic. Brief calls for these explicitly. |
| Compare | **4 / 10** | Two pickers + "wcfb-compare__empty" placeholder. The framework (logos, pane logos, dotted rows) is in `wcfb-enhancements.css` but data isn't wired in. |
| Players (`/the-room`, `/spotlight`) | **2 / 10** | Both pages **769px tall** — under one viewport. `spotlight.html` falls back to **Times New Roman** because no font is loaded. |
| `/history/heatmap/` | **2 / 10** | One SVG total. Times New Roman fallback. 769px tall. The "Twelve seasons. Every program. One image." page has no image. |
| Editions archive | **4.5 / 10** | Four article cards, decent typography, no cover art per issue. |
| Conferences | **5 / 10** | 61 conference cards, zero charts, no league identity glyphs. |
| Heisman | **3 / 10** | 1 table row total. Off-season — but the page should still surface the model's predictive structure. |
| Methodology (Fan Intel) | **6 / 10** | 15,061px tall, real source taxonomy (Tier A/B/C/D), 0 charts. The page that should hero the multi-source pipeline has zero pictures of the pipeline. |
| Rankings | **6 / 10** | 75+ filter chips (level, conference, sort, range), no logos in rows, tables are flat. Filter UI is the strongest non-team-page interaction on the site. |

**Aggregate, hero-weighted:** ~**5.4 / 10**. The ceiling exists (Hub, Alabama). The floor is broken (Players, Heatmap, Reactions).

### Top 5 highest-leverage fixes (impact × effort)

1. **Adopt the team_pages module pattern across Wire, Reactions, Canon, Players, Storylines, Daily.** All of them have rich sub-renderer packages (`src/cfb_rankings/{wire,reactions,canon,mailbag,editions}/renderer.py`) but currently emit prose. Reuse the Hero/Pulse/Chronicle/Savant/Rivalry composition vocabulary on those pages. **Effort:** 2–3 sprints. **Impact:** moves five F-tier pages to B/A-tier.
2. **Wire as a triage console, not a 110-row table.** Add IMPACT filter chips (MAJOR/MOVES SEC/MOVES BIG TEN/MINOR), source-attribution chips per row ("ESPN · 2h", "247 · 6h"), conference logo column, and a sticky filter rail. The data model already has `impact` and `program` per row — just visualize them. **Effort:** 3–5 days. **Impact:** turns the Wire into a daily-use product.
3. **Surface the source ecosystem as a live freshness ribbon on every team page (or at minimum the homepage).** `src/cfb_rankings/ingest/sources/` has 13 adapters, `source_observations` table has freshness per signal per team, `provenance/freshness_page.py` exists. Render this as `reddit ✓ 2h · espn ✓ 4h · campus ✓ 1d · sb-nation ✓ 6h · gdelt ✓ live` chip strip below the hero. **Effort:** 2–3 days. **Impact:** the moat finally becomes visible — and creates the strongest trust signal any analytics site can ship.
4. **Bottom-nav rebuild with bespoke glyphs and parity with desktop.** Replace 🏠📊💡⚖️📚 emoji with a 5–8-icon SVG sprite. Either expose the full taxonomy under a hamburger or rotate destinations contextually (e.g. add Wire and Editions). **Effort:** 1–2 days. **Impact:** removes the single loudest "this is a hobby project" signal.
5. **Fix the broken low-effort pages.** `/players/spotlight.html`, `/players/the-room.html`, `/history/heatmap/` are all 769px tall and missing fonts. Either ship real content or temporarily 301 them to `/players/` directory under a "coming soon" treatment. **Effort:** 1 day. **Impact:** removes the three lowest-quality entry points from the navigable surface.

---

## Moat Visibility Scorecard

For each unique data moat in `FAN_INTEL_SOURCE_STRATEGY.md` and the CLAUDE.md proprietary list — current state and the reference treatment that would surface it.

### 1. CFBD Patreon Tier 2 advanced metrics (EPA, PPA, success rate, explosiveness, opponent-adjusted, win-prob, weather, talent composite, returning production, transfer portal)

- **Rating:** Underexposed
- **Where it appears today:** Only on profiled team pages (17 slugs) via `SavantCard` — a 13-metric percentile card with bars, peer-set toggle (FBS/P4/Conference/Program 2014+), narrative header. Verified live on `/teams/alabama.html`.
- **Where it should appear:** Every team page (664 slugs), every player page, the Compare page, the Wire (as IMPACT-prediction context). Also: the cover essay on the homepage should embed at least one inline EPA-vs-baseline chart.
- **Reference treatment:** ESPN's "matchup predictor" arc gauge; The Athletic's `Bill Connelly weekly column` SP+ ribbon graphs; 538's "vs replacement" sparklines.
- **Concrete next step:** Lift `render_savant_card` from `src/cfb_rankings/team_pages/savant_card.py` and parametrize it for unprofiled programs with a degraded-data variant. The data is in `team_savant_weekly` — verified by `grep team_savant_weekly src/cfb_rankings/reporting.py` returning **0 hits**.

### 2. Multi-source fan-intelligence pipeline (Bluesky, Wikipedia, campus newspapers, RSS, podcasts, GDELT, SeatGeek, Spotify, prediction markets, YouTube, wiki awards)

- **Rating:** Hidden
- **Where it appears today:** Only on `/methodology/fan-intelligence.html`, as a *text taxonomy* (Tier A/B/C/D source list). Zero charts on a page that is 15,061px tall.
- **Where it should appear:** Most importantly — as a **per-team source-freshness ribbon** on every team page. Secondly — as a "where this story came from" attribution strip on every Wire row, every Reaction, every Daily story, every Mailbag answer. Currently `srcAttribCount: 0` on Wire.
- **Reference treatment:** Bloomberg terminal's data-feed status strip; The Athletic's article footers ("Sources: …"); FT live blog "data updates every 60s" pill.
- **Concrete next step:** `src/cfb_rankings/provenance/freshness_page.py` already exists. Lift a "freshness ribbon" partial out of it and inject into the team-page hero, the Wire row, and the homepage cover meta. Tier A signals (Reddit, beat-writer RSS, ESPN) get a green dot; Tier C/D get gray. Updates render last-update time as relative (`2h ago`).

### 3. Fanbase classification (audience cohort labels per team)

- **Rating:** Hidden
- **Where it appears today:** Computed in `src/cfb_rankings/cohorts/aggregate.py`, `cohorts/divergence.py`, `cohorts/player_aggregate.py`. Aggregated into `fanbase_cohort_weekly` table. **`grep fanbase_cohort_weekly src/cfb_rankings/reporting.py` returns 0 hits.**
- **Where it should appear:** Below the team hero as a chip strip — "Diehards · Casuals · Stat folks · Dormant fans · Conversation cohort split" with mini bar showing weight per cohort. The Hub page has a section called "The eighteen fanbases of college football" — that engine should drive every team page's identity layer.
- **Reference treatment:** Pollster crosstabs (NYT election needle by demographic); Reddit's per-sub audience breakdown.
- **Concrete next step:** Add a `_render_fanbase_cohort_strip(profile, db)` to `src/cfb_rankings/team_pages/renderer.py` and call it from the hero render. Pull from `fanbase_cohort_weekly` directly.

### 4. Weekly mood (sentiment over time)

- **Rating:** Adequate on `/hub/` and on the profiled team Pulse card · Hidden elsewhere
- **Where it appears today:** Pulse module on profiled team pages (when above floor — currently mid-May offseason floor is hit, so it shows "Awaiting Signal" / n=0 on Alabama). Verified `_render_trajectory()` and `_render_velocity()` in `src/cfb_rankings/team_pages/renderer.py` exist and render 7-week bars. Hub page surfaces `Fanbase Mood Index` and `This Week's Biggest Mood Movers` with multiple charts.
- **Where it should appear:** Every team page (profiled and unprofiled), the homepage hero (a "national mood" national chart), the Daily ("today's mood-mover programs"), the Wire (next to each row).
- **Reference treatment:** Stockcharts ribbon; The Athletic's CFP Selection-Committee meter; Polymarket's price-over-time chart.
- **Concrete next step:** The Pulse module is genuinely good — the issue is data flow, not UI. Add a `mood_lookback_60d` query path that fills the sparkline from `fanbase_mood_weekly` history even when the most-recent week is below floor. Currently the floor rule blanks both the number AND the sparkline.

### 5. Cohort divergence (when stat-folks and die-hards disagree)

- **Rating:** Hidden
- **Where it appears today:** On the homepage cover essay copy ("Where the Stat Folks and the Regular Fans Disagree About the Big 12"). On Reactions index as four plain text headlines. On the Canon entry (CJ Stroud has a `canon-entry__cohort` section). On Hub.
- **Where it should appear:** As a dueling-bars visualization wherever a cohort split exists. On the homepage as one of the I/II/III/IV cover features. On every team page below Pulse. On `/reactions/` as **the** visual: a horizontal split-bar showing "stat folks ↑ 78%" vs "die-hards ↓ 22%" per wire event.
- **Reference treatment:** NYT "How different demographics felt" split bars; ESPN's "experts vs. fans" picks bar.
- **Concrete next step:** Build a `CohortDivergenceBar` atom (HTML + CSS) and use it everywhere `_belief_*` or `divergence_score` is in scope. `_belief_from_row`, `_reality_gap`, `_respect_gap` already compute this in `fan_intelligence.py`.

### 6. Storyline threads (Active/Dormant editorial arcs)

- **Rating:** Underexposed
- **Where it appears today:** Homepage right rail (eight thread titles with `4 CH.` chip but no Active/Dormant pill). `/storylines/` index — eight headings, no pills, no chart of thread density, no anatomy graphic. `_fetch_storylines` exists in `fan_intelligence.py` line 1063.
- **Where it should appear:** Each thread page should have a chapter-anatomy visualization (a vertical timeline of dated chapters with their "weight" or impact). The homepage and /storylines/ index should show Active threads as **bright pills**, Dormant as muted, with chapter count and last-updated freshness. Each profiled team page should surface the storylines naming that team as an "active narrative" inset.
- **Reference treatment:** The Athletic's "Series" rails; FiveThirtyEight's election-day "Storylines we're watching" sidebar; FT's "Big Read" archive.
- **Concrete next step:** Add `ThreadPill` atom with `--active|--dormant` variants. Wire `storyline_threads` table (currently 0 hits in `reporting.py`) into homepage cover and team page sidebar.

### 7. Reaction stories (auto-triggered when cohorts diverge on a wire event)

- **Rating:** Hidden (this is the most-tragic surface-mismatch on the site)
- **Where it appears today:** `/reactions/` index — three text headlines on a dark page. No images, no cohort split bar, no source attribution.
- **Where it should appear:** Each reaction should be a **magazine card** — small cover image (school logo + the player photo if applicable), the cohort-split mini-bar as cover art ("Casuals: hype +42 · Stat folks: meh −18"), source venues listed below ("Reddit thread, ESPN piece, Bluesky burst"), one-line LLM-curated quote per cohort, and a one-line stake. The list page should be a 3-column magazine grid like The Athletic's Series page.
- **Reference treatment:** The Athletic Series cards; Substack's tile-based archive view; NYT "Year in Stories."
- **Concrete next step:** This is the single biggest editorial-tooling win available — the data quality is already there in `reactions/cohort_divergence.py`, `reactions/synthesizer.py`, `reactions/triggers.py`. The renderer just emits prose. Rewrite `reactions/renderer.py` to follow the `chronicle-card` pattern from `docs/design-system/12-modules-intel.md`.

### 8. Signature stories per player

- **Rating:** Hidden
- **Where it appears today:** Nowhere on the surfaces I navigated. Canon individual player entries (e.g. `/canon/the-100-best-players-cfp-era/cj-stroud.html`) have a `canon-entry__paragraph-wrap` section that may be the signature story, but it renders as one block of prose with no visual anchor.
- **Where it should appear:** On `/players/<slug>` (which is currently broken — pages 769px tall). On hover on Canon list rows. On Heisman tracker rows. On team-page player-arc Chronicle cards.
- **Concrete next step:** The `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` and the "Accolade Lens spec" referenced in CLAUDE.md exist — execute the brief. Currently `players/spotlight.html` literally renders with `font-family: "Times New Roman"` because no font is loaded.

### 9. Chronicle observation cards (anomaly / moment / flashpoint / echo / retroactive / player_arc)

- **Rating:** Adequate on profiled team pages · Hidden elsewhere
- **Where it appears today:** Profiled team pages (`_render_chronicle_section` in `team_pages/renderer.py`) — though the live Alabama snapshot didn't show Chronicle cards, the renderer exists and the design spec (`docs/design-system/12-modules-intel.md` lines 113-253) is precise — 6 card types with colored top borders (amber/coral/navy/gray/navy-800/green-200).
- **Where it should appear:** Homepage — as one of the cover-essay anchors. Editions — as the day's "Chronicle of record." Wire — as inline anomaly callouts mid-table. Storylines — as the building blocks of each thread.
- **Concrete next step:** Lift the Chronicle module into a shared partial and call from `editions/article_renderer.py` and `_render_home_meta_row` in `reporting.py:13927`. The data is in `team_chronicle_observations`.

### 10. Power ratings + Heisman model receipts (predictive claims tracked)

- **Rating:** Hidden
- **Where it appears today:** The homepage Voices module has "89% AGED WELL" / "82% AGED WELL" / "77% AGED WELL" beat-writer cards — that's the predictive-claim audit. But `/heisman/` itself has 1 table row and no model receipts; `/rankings/` is a flat table with no "model said X, X happened" markers; `games_predictive_claims` and `claim_outcomes` tables are referenced **0 times in `reporting.py`** (grep verified).
- **Where it should appear:** Every game row in the Wire ("model gave X 62% to win, X won"). Every team page hero ("the model said this team would be 9-3, they're 11-4"). Every Heisman row ("model called Williams a top-3 finalist, finished 4th"). The "% Aged Well" treatment used on Voices should be applied to **our own** model output, not only to beat writers.
- **Reference treatment:** 538's "calibration plots" (their crown jewel); Polymarket's price-vs-resolution charts; Vegas line tracking.
- **Concrete next step:** Build a `ReceiptStrip` atom — claim, prediction, outcome, age. Wire `games_predictive_claims` + `claim_outcomes` into the team-page hero and the rankings movement column.

### 11. Canon lists with cohort splits

- **Rating:** Underexposed
- **Where it appears today:** Canon index lists three lists. CJ Stroud entry has `canon-entry__cohort` section (the cohort-split content) but as text, no visual.
- **Where it should appear:** Every Canon entry should hero the "Stat folks rank #14 / Fans rank #28 / Consensus #20" as a horizontal divergence bar (we already saw this exact treatment hinted at on the homepage Canon callout: "STAT FOLKS / FANS / consensus"). Lift it out as an atom.
- **Concrete next step:** `src/cfb_rankings/canon/renderer.py` should include a `_render_cohort_divergence_bar(stat_rank, fan_rank, consensus_rank)` partial.

### 12. Hub computed evidence (every Hub row has evidence JSON)

- **Rating:** Adequate
- **Where it appears today:** `/hub/` is the strongest page on the site. 28 charts, 9,671px scroll, magazine numbering ("N° 047"), real sentence-led headlines ("Michigan's belief is at a decade low.")
- **Where it should appear:** This treatment should be the template for Daily, Reactions, Wire-on-mobile, Canon list pages.
- **Concrete next step:** Use `/hub/` as the visual reference and lift its module composition to the rest of the editorial surface.

---

## Per-Page Verdicts

> Evidence approach: navigated via `mcp__Claude_in_Chrome__navigate`, introspected via `javascript_tool` and `read_page` (accessibility tree). Computed-style and DOM-fingerprint queries captured per page below.

### `/` — Homepage (Editions cover, vol. I N° 17)

- **Status:** **Pass with reservations**
- **Evidence:** `bg: rgb(246, 241, 230)` (paper), `font: Source Serif Pro`, 9 desktop nav links, hero h1 = "After the Bracket", `scrollHeight: 10597`, roman-numeral section numbering visible (II through XIII), "FEATURED THREAD · 4 CHAPTERS · The Vandy Renaissance" with 7 archive threads, "THE CANON · ENTRY OF THE WEEK" surfaces CJ Stroud with cohort divergence ("STAT FOLKS · FANS · consensus") — *this is the divergence bar atom waiting to be lifted*. Voices module surfaces "Bill Connelly Espn 89% AGED WELL / 14 TAKES TRACKED."
- **Top 3 visual fixes**
  - **No chart above the fold.** The "Cover · Cohort velocity index" SVG is the only chart on the page and lives below the cover essay. Promote it to a hero strip directly under the wordmark — the strongest signal for "this is data journalism, not a blog." File: `src/cfb_rankings/editions/article_renderer.py` (cover renderer).
  - **Storyline pills lack Active/Dormant status.** All 8 threads show "4 CH. ARCHIVE" with no distinction between active and dormant. Add `--active` and `--dormant` ThreadPill variants in `src/cfb_rankings/team_pages/templates/_atoms/thread_pill.html`-style partial. The data exists.
  - **Voices "Aged Well %" should also surface OUR claims.** Right now it audits beat writers. The strongest possible move is the same panel for our own predictions: "CFB Index power rating · 87% aged well · 412 receipts tracked." File: `_render_home_meta_row` at `src/cfb_rankings/reporting.py:13927`.
- **Mobile:** Bottom nav appears at `<720px` (verified in `tools/wcfb_enhancements/wcfb-enhancements.css:287`). It uses emoji glyphs and only links to 5 destinations — see Global Quick Wins.
- **Moat surface:** Hero ✓ (editions cohort velocity) · Voices ✓ (claim-tracking) · Storylines ⚠️ (no pills) · Canon ✓ (divergence) · Wire ✓ (8 rows preview) · Mood/Pulse ✗ (national mood missing) · Source freshness ✗

### `/rankings/`

- **Status:** **Needs Work**
- **Evidence:** Title "2025 Season Rankings", 75+ filter chips (level, conference, sort, range), no `<img>` logos in rows (we verified `hasLogo: false` on team pages; rankings inherits this gap), `viewportW: 1586`, no inline sparklines visible in the accessibility tree.
- **Top 3 visual fixes**
  - **No team logos in rows.** Every modern rankings page (ESPN, AP, CBS, The Athletic) shows logo + wordmark per row. `tools/inject_rankings_logos.py` exists in the repo (mentioned in CLAUDE.md "Asset gaps") — execute it. File: `tools/inject_rankings_logos.py`.
  - **No movement sparklines per row.** The CSS for `.rank-sparkline` exists at `src/cfb_rankings/team_pages/assets/tokens.css:321` but the rankings page doesn't render them. Wire `rank_history_weekly` (or equivalent) into the row partial.
  - **Filter UI is dense and undifferentiated.** 75 chips for level/conference/sort/range are presented as flat select+chip rows. Cluster them: "QUICK FILTERS" (Top 25, Top 100, All teams) as primary; "DRILL" (Level, Conference) as secondary; "SORT" as tertiary. File: `_render_rankings_*` in `reporting.py` (grep `render_rankings`).
- **Mobile:** Tokens.css has `@media (max-width: 640px)` block at line 363 that turns `#rankingsTableBody tr` into stacked cards using `data-label` pseudo-content — good pattern. Verify it fires on the live site.
- **Moat surface:** SP+ values visible ⚠️ (no comparative ramp); Power/Resume duality ✓; movement ✗; receipts ✗.

### `/teams/alabama.html` — profiled, world-class renderer

- **Status:** **Pass**
- **Evidence:** Hero with logo, identity bar with rank chips, heritage strip ("Founded 1892 · Titles · Conf titles · Heismans · CFP · Bowls · Stadium Bryant-Denny · Legacy Paul W. 'Bear' Bryant"), Savant Card with peer-set toggle (FBS/Power-4/Conference/Program 2014+) and 13 percentile rows organized into offense / defense (with inverted notation) / hidden-math, Rivalry card with all-time/streak/trophy/next strip plus dual posture panels, Era card with title chips ("Title #4 of the Process", "13-0 · Title #6"), coach regimes ribboned (SABAN / DEBOER), 9 historical-season chapter links. Footer reads "team-pages v1.0 · sentience dead-period-summer". `bg: var(--bg-0)` (dark theme).
- **Top 3 visual fixes**
  - **Rivalry heat trajectory is a placeholder `<img alt="Rivalry heat trajectory placeholder">`.** Render a real SVG line chart of weekly fan-intel volume per side over 4 weeks to kickoff. The data engine exists in `cohorts/`. File: `src/cfb_rankings/team_pages/rivalry_card.py`, function `render_rivalry_card`.
  - **Pulse falls to "Awaiting Signal · n=0" in mid-May.** The floor rule is correct, but the sparkline blanks even when historical data is available. Add `mood_lookback_60d` query path. File: `src/cfb_rankings/team_pages/renderer.py:_render_trajectory` and `data.py:fetch_mood_snapshot` — broaden the window.
  - **No source-freshness ribbon.** A 4-chip strip below the hero ("reddit ✓ 2h · espn ✓ 6h · campus ✓ 1d · sb-nation ✓ 12h") would make the multi-source moat visible without adding a screen. File: new `_render_freshness_ribbon` in `team_pages/renderer.py`, pulling from `source_observations` (currently 0 references in `reporting.py`).
- **Mobile:** `team-pages/assets/styles.css` has `@media (max-width: 640px)` reducing logo from 80→56px (line 41). Hero metrics tiles stack — verify all 4 fit at 375px width.
- **Moat surface:** Savant ✓ HERO · Pulse ⚠️ (data-flow issue) · Rivalry ⚠️ (placeholder chart) · Era arc ✓ · Chronicle ⚠️ (no cards rendered on Alabama at this snapshot) · Source freshness ✗

### `/teams/memphis.html` — legacy renderer

- **Status:** **Needs Work**
- **Evidence:** `bg: rgb(250, 250, 250)` (light), `font: Inter`, `hasLogo: false`, 13 site-shell/topbar/nav classes, sections include `team-shell`, `hero team-hero premium-team-hero`, `team-stat-tile` (×4), then a different rendering pattern. Stylesheets: `cfb-index.89cc354d9863.css` + `wcfb-enhancements.css` (note: hash differs from the bundle in `output/site/assets/` — investigate cache/CDN drift). Sub-headings present: "Cohort Signal", "Fanbase Archetype?", "Performance Narrative", "Season Rating Journey", "Game Impact Board", "Betting Lens", "Week 3 vs Troy" (game card), "Market Game Log", "Efficiency Dashboard", "Historical comps pending".
- **Top 3 visual fixes**
  - **No logo, even though `output/site/assets/team-art/memphis/` exists.** Wire `team_logo_src(slug)` into the legacy template the same way `team_pages/renderer.py` does. File: `reporting.py` legacy team-page renderer (grep `team-shell` to locate).
  - **Two design languages on one site.** Memphis renders sans-serif light theme; Alabama renders sans-serif dark theme; both call themselves "the team page." Pick one for the 647 unprofiled programs. Recommendation: a degraded-data variant of the team_pages v2 renderer that omits Pulse/Rivalry when data isn't available but keeps the hero + Savant + Arc.
  - **Section headings present but no visual hierarchy.** "Performance Narrative", "Game Impact Board", "Betting Lens" are all `<h2>` with no eyebrow, no color, no module border. Adopt the eyebrow atom from `docs/design-system/01-atoms.md`.
- **Moat surface:** Cohort Signal ⚠️ (heading present, treatment unclear) · Betting Lens ⚠️ (per-game cards) · Efficiency Dashboard ⚠️ (no chart) · Pulse ✗ · Rivalry ✗ · Savant ✗.

### `/wire/`

- **Status:** **Needs Work**
- **Evidence:** `bg: rgb(246, 241, 230)` (paper), `Source Serif Pro`, h1 "Every move. Every read.", 1 table, 110 rows, 5 columns (WHEN / PROGRAM / ACTION / WHY IT MATTERS / IMPACT), `scrollHeight: 9533`, **`srcAttribCount: 0`** (no source attribution chips per row), **`hasFilters: false`** (no filter UI), 0 charts, 0 images.
- **Top 3 visual fixes**
  - **Add filter chips above the table.** IMPACT (MAJOR/MINOR/MOVES SEC/MOVES BIG TEN/MOVES ACC/MOVES B12), CONFERENCE, DATE RANGE. Sticky on scroll. File: `src/cfb_rankings/wire/renderer.py`.
  - **Add source-attribution chip per row.** Each wire event has a source (ESPN, 247, On3, beat-writer Twitter). The data is in `source_observations` and on the wire ingest record. Render as small chip column. Trust signal × 110 rows.
  - **Add IMPACT visual encoding.** Currently "MAJOR" / "MOVES SEC" / "MINOR" are plain text in the rightmost column. Promote IMPACT to a left-edge color stripe (red / amber / gray) using `tokens.css` color ramps. Conference badges in 5×5 logos cluster could replace the current text "MOVES SEC" chip.
- **Mobile:** Wire table needs `data-wcfb-card-mobile` attribute to trigger the mobile card transform at `tools/wcfb_enhancements/wcfb-enhancements.css:333`. Verify it's set in `wire/renderer.py`.
- **Moat surface:** Wire signal ⚠️ (visible but flat) · Source attribution ✗ (the moat) · Impact prediction ✗ (no "model says this matters X%") · Cohort-divergence inline ✗.

### `/daily/`

- **Status:** **Needs Work**
- **Evidence:** Title "The Daily — Thursday, May 14th, 2026", `bg: rgb(248, 246, 240)` (yet another paper variant — see Global Tokens Drift), `font: Georgia` (NOT Source Serif — drift), 3 h2 stories, 0 images, 0 charts, `scrollHeight: 2507`.
- **Top 3 visual fixes**
  - **Wrong font.** Computed font is Georgia; Wire on the same theme is Source Serif Pro. Trace through the cascade and unify. File: locate Daily template; check that `cfb-index.f3924a06eced.css` is loaded.
  - **Three text paragraphs with zero visual anchor.** Each Daily story should hero one chart — a mood-shift bar, a Wire-impact tally, a Hub mood-mover sparkline. Even a single inline-SVG anchor per story changes the page completely.
  - **No edition number / no provenance.** The homepage announces "VOL. I · NO. 17". The Daily should similarly badge "DAILY · NO. 213" with masthead + author byline structure. File: Daily renderer.
- **Mobile:** Three stacked stories should work fine at 375px — verify no fixed widths in the daily CSS scope.
- **Moat surface:** Daily storyline curation ⚠️ (good copy, no surface) · Wire callouts ✗ · Mood-mover ✗.

### `/mailbag/`

- **Status:** **Needs Work**
- **Evidence:** Title "The Mailbag — 2026-w20", `bg: rgb(246, 241, 230)` paper, `Source Serif Pro`, h1 "The Mailbag", 6 Q&A pairs (`qaPairs: 6`), 0 charts, `scrollHeight: 6601`.
- **Top 3 visual fixes**
  - **No visual differentiation between questions and answers.** Mark questions with serif italic + small-cap "Q ·" eyebrow; answers with body serif. Adopt the `eyebrow` atom from `docs/design-system/01-atoms.md`.
  - **No reader attribution treatment.** Each Q should have masthead-style attribution: "From RJ in Knoxville · submitted 2d ago." Builds reader-relationship moat.
  - **No related-data callouts.** A mailbag question about Iowa's tempo should pull the Iowa Savant card percentile bars as an inline asset. The Savant card atom is already built — embed it.
- **Mobile:** Q&A vertical stack should be fine. Verify `min-height: 44px` on submit form CTAs.
- **Moat surface:** Editorial voice ✓ · Data-as-evidence ✗.

### `/reactions/`

- **Status:** **Broken** (the surface most catastrophically mismatched with its moat)
- **Evidence:** `bg: rgb(12, 14, 16)` (dark), `font: -apple-system` (not Inter, not Source Serif — third font drift), h1 "Reaction Stories", h2 "Latest 3 Stories", 3 h3 cards with truncated headlines (e.g. "USC Lands LB GianCarlo Rufo from Georgetown — And the Fanbase Didn't React the W"), 0 images, 0 charts, `scrollHeight: 937`.
- **Top 3 visual fixes**
  - **Each reaction is a cohort-divergence event by definition** (per `reactions/cohort_divergence.py`). The card *must* surface the divergence — a horizontal bar showing "Casuals +42 enthusiasm · Stat folks −18 enthusiasm." Without the bar, the headline alone reads like a teaser link. File: `src/cfb_rankings/reactions/renderer.py`.
  - **No cover art per card.** A reaction story about USC + Rufo needs at minimum a Georgetown logo + USC logo composite. The brief mentions "magazine-style cards with cover art" — implement the atom: small 2-logo composite, headline, divergence bar, source-venue chip strip.
  - **Switch font stack to Inter Display + Source Serif headline.** Currently falling back to system-ui because no font is loaded on the page.
- **Mobile:** With only 3 cards, 1-col stack is fine. Add `data-wcfb-touch` to ensure 44px touch targets on the cards.
- **Moat surface:** Cohort divergence (the explicit reason these stories exist) ✗ — invisible.

### `/canon/`

- **Status:** **Needs Work**
- **Evidence:** `bg: rgb(11, 13, 18)` (dark, matches team_pages tokens.css `--bg-0`), `font: Inter`, h1 "The lists that settle the era's arguments — or start them." Three lists: "The 100 Best Players of the CFP Era", "The 25 Best Coaching Hires of the 2020s", "The 50 Most Defining Games of the CFP Era". 0 images, 0 charts, 15 cards.
- **Top 3 visual fixes**
  - **No per-list cover treatment.** Three lists deserve three distinct cover-art treatments — player headshot grid for the 100; coach portrait stack for the 25; goalpost-and-confetti for the 50.
  - **List entries are flat.** The 100 Best Players doesn't show the cohort-divergence bar at the list-index level (it's only on individual entries). Promote the divergence bar to the list index — turns a flat list into an argument.
  - **No "how the lists work" upfront.** There's a "How the lists work" h2 at the bottom — this is the trust-building methodology section that should hero, not coda. Move above the list.

### `/canon/the-100-best-players-cfp-era/cj-stroud.html` — individual canon entry

- **Status:** **Pass with reservations**
- **Evidence:** Dark theme, Inter font, h1 "C.J. Stroud", title shows "#20 · The 100 Best Players of the CFP Era", 5 sections (`canon-entry__statline`, `canon-entry__paragraph-wrap`, `canon-entry__cohort` "Cohort divergence", `canon-entry__delta` "Year-over-year", `canon-entry__cross-references` "Related"). 0 images, 0 charts, `scrollHeight: 1569`.
- **Top 3 visual fixes**
  - **The `canon-entry__cohort` section is the page's editorial argument — visualize it.** Add a horizontal divergence bar atom in the `_render_cohort_divergence` partial.
  - **No headshot, no team logo.** Even one image — a small Ohio State logo with player name — would change first-impression substantially.
  - **`canon-entry__statline` should be a 4-tile MetricTile cluster** from `01-atoms.md` (TD / INT / Comp % / SP+ EPA), not a sentence.

### `/storylines/`

- **Status:** **Needs Work**
- **Evidence:** Dark theme `#0b0d12`, Inter font, h1 "Storyline Threads", 8 thread h2 headings (Vandy Renaissance, Coaching Carousel, Big Ten Reasserting, 12-Team Playoff Settling, Realignment Endgame, Portal Era Settling, ND-USC, Saban-to-DeBoer Transition). No `<pill>` / `<status>` / `<badge>` elements found. 0 charts. `scrollHeight: 1397`.
- **Top 3 visual fixes**
  - **Active vs Dormant pills.** The data model supports this distinction; render `--active` (bright accent) and `--dormant` (gray, lower opacity) ThreadPill variants.
  - **Chapter-density mini visualization per thread row.** Eight horizontal dots showing chapter cadence per thread — like an EKG of editorial momentum.
  - **No thread-anatomy view.** Click into a thread and you'd want a vertical timeline of dated chapters with weight indicators. The Vandy Renaissance has "4 CHAPTERS" — show those four chapters as a timeline.

### `/players/spotlight.html` and `/players/the-room.html`

- **Status:** **Broken**
- **Evidence (spotlight):** Title "Players — 2025", `bg: rgba(0,0,0,0)` (transparent!), `font: "Times New Roman"` (raw, no Source Serif or Inter loaded), h1 "Players — 2025", only one h2 "The Room", `scrollHeight: 769` (one viewport, no content).
- **Evidence (the-room):** Title "Players in The Room — 2025", `bg: rgb(250, 250, 250)` (light), `font: Inter`, h1 absent, `imgCount: 0`, `chartCount: 0`, `scrollHeight: 769`.
- **Top 3 visual fixes**
  - **Both pages render in under one viewport with no real content.** This is the most-broken surface on the site. Either ship real content per `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` (referenced in CLAUDE.md) or 301-redirect to a "players coming soon" treatment.
  - **Times New Roman fallback on `spotlight.html`** means the page isn't loading a CSS bundle. Inspect for missing `<link rel="stylesheet">` in that template.
  - **`the-room.html` has classes `the-room-page`, `panel`, `wcfb-bottom-nav` but no module content rendered.** The renderer (`src/cfb_rankings/team_pages/the_room_renderer.py`, per CLAUDE.md memory note) needs its stub template fixed — the user's previous memory confirms this was partially polished but visual issues remain.

### `/heisman/`

- **Status:** **Needs Work**
- **Evidence:** Light bg `#fafafa`, Inter font, h1 "A full-board Heisman model, not just a top-three list.", 2 sub-headings ("Fast Read", "Board Controls"), **1 table row total**, 0 charts.
- **Top 3 visual fixes**
  - **Off-season fallback content missing.** It's May, season is closed, no candidate rows are live. The page should hero "How the model called 2025" (a calibration retrospective) — that turns dead-air into a moat showcase.
  - **No model receipts.** Even with one row, surface "model said Jeanty top-3 with 38% probability, finished 6th — confidence calibration plot below."
  - **No board controls actually visible** — "Board Controls" heading suggests filters but the accessibility tree doesn't show any controls.

### `/hub/`

- **Status:** **Pass — site standard-bearer**
- **Evidence:** `bg: rgb(243, 238, 228)` (yet ANOTHER paper variant — token drift), **`font: "Source Serif 4"`** (a fourth font variant — neither Source Serif Pro nor Inter), 28 charts inline, `scrollHeight: 9671`, magazine numbering "N° 047", h1 "Michigan's belief is at a decade low.", section headings: "The Fanbase Mood Index", "This Week's Biggest Mood Movers", "Hype vs Reality", "The eighteen fanbases of college football", "Who's More Obsessed With Whom", "'5-star trust me'", "This week's cards", "NEBRASKA IS NOT BACK".
- **Top 3 visual fixes**
  - **Lock the font.** "Source Serif 4" needs a Google Fonts or self-hosted `@font-face`. Otherwise different visitors see different families.
  - **Background `#f3eee4` does not match Wire/Mailbag/Editions `#f6f1e6`.** Unify on one paper token.
  - **The 28 charts here should be the visual library for the rest of the site.** Catalog them and lift to atoms — they're the most-developed visual language anywhere on the product.
- **Mobile:** This page is the strongest mobile candidate too — its sentence-led headlines work on phones. Verify chart SVGs are responsive.
- **Moat surface:** Mood ✓ HERO · Cohort split ✓ HERO · Reality gap ✓ · Conversation cards ✓ · Fanbase archetypes ✓. This page IS the moat made visible.

### `/compare/`

- **Status:** **Needs Work**
- **Evidence:** `bg: rgb(246, 241, 230)`, `font: Inter`, h1 "Compare two programs.", `hasSearch: false`, 0 images, 0 charts, `scrollHeight: 1030`. The CSS in `tools/wcfb_enhancements/wcfb-enhancements.css` has 80+ lines for `.wcfb-compare__pickers`, `__panes`, `__pane-logo`, `__row`, `__empty` — but the live page hasn't loaded data into them.
- **Top 3 visual fixes**
  - **Wire the pickers to data.** The framework is built; the renderer (`tools/wcfb_enhancements/build_compare.py`) likely needs an invocation in the build pipeline.
  - **Compare should surface Savant percentiles head-to-head.** Side-by-side mirrored percentile bars per metric — the most visually compelling treatment available for the 13-metric data.
  - **No deep-link URL state.** A compare URL should encode `?a=alabama&b=auburn` for shareable diffs.

### `/conferences/`

- **Status:** **Needs Work**
- **Evidence:** Light bg, Inter font, h1 "The sport gets more interesting when leagues have identity.", 61 conference cards, **0 charts**, 0 images, `scrollHeight: 6806`.
- **Top 3 visual fixes**
  - **No conference identity glyphs.** SEC, Big Ten, ACC, Big 12 all collapse to plain text. League logos exist in CFBD; render small SVG logos per card.
  - **No comparative metric per conference.** "Average SP+", "EPA per play", "Schedule strength" — surface even one number per row + a sparkline.
  - **61 cards on one page with no filter or sort.** Apply the rankings-page filter UX pattern to conferences too.

### `/editions/`

- **Status:** **Needs Work**
- **Evidence:** Paper bg, Source Serif Pro, h1 "Every issue.", 4 article cards, 0 images, `scrollHeight: 3395`.
- **Top 3 visual fixes**
  - **No cover art per edition.** Each issue should have a cover treatment — a cohort-velocity chart for that week, a Chronicle card preview, or a generated cover composition. `editions/theme_resolver.py` and `viz_templates/` directory exist — wire them in.
  - **Date scrub / archive timeline.** 4 cards is too few to need this, but as more issues accrete, a year-by-year nav is needed.
  - **No "Latest" hero treatment.** The most-recent edition should hero with full-width cover treatment + 2-3 secondary articles. Currently all 4 are equal weight.

### `/methodology/fan-intelligence.html`

- **Status:** **Needs Work** (highest-leverage methodology page; lowest visual investment)
- **Evidence:** `bg: rgba(0,0,0,0)` transparent, `font: -apple-system` (system-ui — no font loaded), h1 "Fan Intelligence — Methodology", 12 h2/h3 headings ("Current coverage", "Sources with runs in the last 7 days", "What we publish, and how we label it", "Effective sample size & the floor rule", "Source catalog", "Tier A", "Tier B", "Tier C", "Tier D", "Cohort weight matrix", "Known coverage gaps", "Weight governance"), 0 charts, **`scrollHeight: 15061`** (longest page on the site).
- **Top 3 visual fixes**
  - **Surface the source ecosystem as a live diagram.** A force-directed graph (Reddit → mood; Wikipedia → interest; SeatGeek → demand; etc.) would communicate the moat in 2 seconds where 15,061px of text doesn't.
  - **Tier A/B/C/D should be a color-coded matrix.** Currently rendered as text headings.
  - **No live freshness counters per source.** "Reddit · last ingest 23 min ago · 1,243 mentions today" per source = trust × 1000.

### `/history/heatmap/`

- **Status:** **Broken**
- **Evidence:** Title "Dynasty Heatmap — 2014-2025", `bg: rgba(0,0,0,0)` transparent, `font: "Times New Roman"` (raw fallback), h1 "Twelve seasons. Every program. One image.", **1 SVG total**, **`cellCount: 1`** (the headline promises a heatmap of every program; one cell exists), `scrollHeight: 769`.
- **Fix:** The page literally promises "one image" and ships one cell. Either render the actual heatmap (the data is in `team_season_arc` which the Era card on team pages already pulls from) or 301 to a working page.

---

## Global Quick Wins

Each is a one-line fix that improves the entire site.

1. **Consolidate to ONE paper background token.** Today: `#f6f1e6` (Wire, Mailbag, Editions, Compare), `#f8f6f0` (Daily), `#fafafa` (Memphis, Rankings, Conferences, Heisman, Players), `#f3eee4` (Hub). Pick `#f6f1e6` as canonical paper, `#fafafa` as "data surface light," and migrate.
2. **Consolidate to ONE dark surface token.** Today: `#0b0d12` (team_pages, Canon, Storylines), `#0c0e10` (Reactions). Both are nearly the same color but they're not the same value.
3. **Load Inter Display + Source Serif Pro globally via one `@font-face` declaration in the main bundle.** Three pages (spotlight, heatmap, methodology) fall back to Times New Roman or system-ui because no font is loaded.
4. **Add `data-wcfb-card-mobile` to every table on every page.** The mobile-card transform CSS is built (`wcfb-enhancements.css:333`) — opt-in attribute is missing on Wire, Rankings, Conferences.
5. **Replace emoji bottom-nav glyphs with a 5-icon SVG sprite.** 🏠📊💡⚖️📚 → custom-line icons that match the editorial register.
6. **Add a `<link rel="stylesheet">` audit script** that fails the build if a generated page references a hash that doesn't match the latest CSS bundle. Memphis loaded `cfb-index.89cc354d9863.css` while `output/site/assets/` lists `cfb-index.f3924a06eced.css` — cache drift.
7. **Add an accent-color hex normalizer** — `team_brand_assets` is referenced once in `reporting.py:5187`. Verify every team page calls `[data-program]` body attribute so per-team accents work on legacy pages too.
8. **Plumb `--accent-primary` from `team_brand_assets.primary_color` into the Memphis-style legacy renderer too** — currently only the team_pages v2 renderer reads it.
9. **Wire the freshness ribbon onto homepage cover + every team-page hero** — single highest trust-building visual the codebase can produce with existing data.
10. **Apply the `_render_cohort_divergence` bar from `canon/cj-stroud.html` to Reactions, Wire callouts, and homepage Voices module** — the atom exists at one canon entry, lift to global.

---

## Big Swings

Larger redesign opportunities. Each is named, justified, sized, and referenced.

### B1. The Source-Ecosystem Ribbon

**What:** A horizontal 8–13-chip strip below every team-page hero (and homepage cover) showing live freshness per signal source — `reddit ✓ 2h`, `bluesky ✓ 14m`, `espn ✓ 4h`, `247 ✓ 1d`, `campus ✓ 6h`, `sb-nation ✓ 3h`, `wikipedia ✓ 12h`, `seatgeek ✓ 9h`.
**Why:** The proprietary moat is literally invisible everywhere except `/methodology/fan-intelligence.html` as text. Visualizing it = differentiating from ESPN in one line.
**Effort:** 3 days (atom + data plumb + render).
**Reference:** Bloomberg terminal header; The Athletic article footer "Sources:" line.

### B2. The Receipts Strip

**What:** A "model said this, here's what happened" component on every team page hero + every game row in the Wire + every Heisman row. Three states: `pending`, `aged_well`, `aged_poorly`.
**Why:** The homepage Voices module already does this for **beat writers**. Applying the same treatment to our own model output is the highest-credibility move available.
**Effort:** 1 week (atom + `games_predictive_claims` × `claim_outcomes` query + per-surface render).
**Reference:** 538 calibration plots; Polymarket prediction-vs-outcome.

### B3. Reactions Magazine Cards

**What:** Rebuild `/reactions/` from three text-link headings to a 3-column magazine grid. Each card: 2-logo composite cover (Georgetown + USC, etc.), bold headline, **cohort-divergence horizontal bar** as the visual hero of each card, source-venue chip strip, one-line LLM-curated quote per cohort.
**Why:** Reactions is the cohort-divergence moat made editorial — and it currently ships as a blog index.
**Effort:** 1 sprint (renderer rewrite + atom + data wiring).
**Reference:** The Athletic Series cards; Substack tile archive.

### B4. Storyline Anatomy View

**What:** Each `/storylines/<thread>/` page becomes a vertical timeline of dated chapters with chapter weight (impact) and active/dormant status. Mini "EKG" on the index page per thread.
**Why:** Storylines are the editorial container for everything else — but on `/storylines/` they're eight headings.
**Effort:** 1 sprint.
**Reference:** NYT investigation timelines; FT Big Read archive.

### B5. The Compare Slam

**What:** Two-team Savant-card mirror. Two side-by-side percentile bars per metric, with the bigger value rendered as a horizontal "win" bar in team color. Schedule overlap callouts. Era arc dual-overlay.
**Why:** Compare exists, framework is built, data is in `team_savant_weekly`. Currently `/compare/` is two empty pickers.
**Effort:** 1 week.
**Reference:** Sports-Reference's H2H view; NBA.com Compare.

### B6. Heatmap of Heritage

**What:** `/history/heatmap/` renders the actual heatmap — 12 seasons × all 134 FBS programs, color-coded by AP rank or SP+. Hover for season detail. Click for the team-page Era card.
**Why:** The page promises "one image" of the era and ships zero.
**Effort:** 1 week (one renderer, one SVG layout).
**Reference:** NYT 100 years of presidents; FT inflation heatmap.

### B7. Player Pages, World-Class Brief Execution

**What:** Per `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`, execute the QB-first player-page redesign with Accolade Lens, Signature Stories, cohort divergence on rankings.
**Why:** Two of the most-trafficked navigation links (Players → spotlight, Players → the-room) ship as 769px-tall stubs.
**Effort:** 1 sprint (brief is written; data engines exist; renderer wire-up needed).

### B8. Conference Pages with Identity

**What:** Each league gets a tonal palette and a glyph; the `/conferences/` index renders a Stockcharts-style "league heat" panel — small chart per league showing weekly EPA gap, total volume, mood.
**Why:** "The sport gets more interesting when leagues have identity" — the headline. Right now identity is one h3 per league.
**Effort:** 1 week.

### B9. Editions Cover Generator

**What:** Each weekly edition gets a generated cover image (logo composite or SVG with that issue's cohort-velocity chart). Renders to `/editions/<issue>/cover.png` and surfaces on `/editions/` archive.
**Why:** Editions archive currently presents as text article cards. Magazines have covers.
**Effort:** 1 sprint (Pillow renderer + viz_templates wire-up; templates dir exists).
**Reference:** The New Yorker covers; FT Weekend; Bloomberg Businessweek.

### B10. Daily as a Dashboard

**What:** Replace 3-paragraph Daily with a Bloomberg-terminal-style dashboard: top-3 mood movers (with sparklines), latest Wire events (with impact chips), today's storyline-arc updates (Active/Dormant), one Chronicle card hero, freshness footer.
**Why:** The Daily is the morning entry point. Text-only kills habit formation.
**Effort:** 1 week.

---

## Mobile-First Findings

Tested via accessibility-tree inspection + computed-style readback + CSS code reading (Chrome MCP's `resize_window` resizes the OS window but not the rendered viewport, so true 375px live-DOM verification wasn't possible — recommendations below are derived from CSS code + DOM measurement at 1586px).

### Confirmed mobile patterns (good)

- `tools/wcfb_enhancements/wcfb-enhancements.css:287` — bottom nav appears at `(max-width: 720px)` with `position: fixed`, `safe-area-inset-bottom` honored, `min-height: 44px`.
- `team_pages/assets/styles.css:39` — logo scales 80→56px at `(max-width: 640px)`.
- `team_pages/assets/tokens.css:363` — rankings table rows transform to cards at `(max-width: 640px)` via `data-label` pseudo-content.
- `team_pages/assets/tokens.css:121` — `--content-side-pad: clamp(16px, 4vw, 32px)`.

### Mobile-specific issues

- **Bottom nav uses emoji glyphs.** Each `<a>` label is "🏠Home", "📊Rank", "💡Hub", "⚖️Compare", "📚About" — render varies by OS (different on iOS vs Android vs Windows Chrome).
- **Bottom nav and topbar nav don't match.** Desktop topbar exposes 9 destinations (Rankings/Teams/Players/Heisman/Programs/History/Editions/Wire/How It Works). Bottom nav exposes 5 (Home/Rank/Hub/Compare/About). Mobile users cannot reach Teams, Players, Heisman, Programs, History, Editions, Wire from the bottom bar.
- **No hamburger menu.** `hasHamburger: false` at multiple checkpoints. At narrow widths, the desktop topbar of 9 links either wraps awkwardly or scrolls horizontally — verified via topbar `scrollWidth > clientWidth` check (currently no overflow at 1586px, but the markup pattern is at-risk).
- **Wire (110 rows) lacks `data-wcfb-card-mobile`.** The CSS supports table→card transformation but the attribute opt-in is missing. Verified by the raw text dump of Wire showing structured table cells.
- **Heatmap (`/history/heatmap/`) at 769px tall** is desktop-too-narrow regardless of viewport — the page is empty on every size.
- **Touch targets on Wire impact chips ("MAJOR", "MOVES SEC")** — render as inline text, not buttons. Even if non-interactive they're a visual button affordance that should hit 44px square.
- **`/players/spotlight.html` has `bg: rgba(0,0,0,0)`** — transparent body means viewport color shows through. Even when the device's safari background is white, this is non-deterministic on mobile dark mode.
- **`@media (prefers-color-scheme: dark)` is honored** in `wcfb-enhancements.css:40` — good — but `00-tokens.md` shows dark-mode tokens that the actual `team_pages/tokens.css` doesn't re-implement (`team_pages` is dark-by-default, not light-with-dark-fallback). So a system-light user on a team page sees the dark theme; a system-dark user on the homepage sees the light theme. Acceptable but document the intent.

### Specific breakpoint failures to fix

| Page | Width | Failure |
|---|---|---|
| `/wire/` | 375px | 5-column table will horizontal-scroll without `data-wcfb-card-mobile` |
| `/conferences/` | 375px | 61 cards in one column = scroll-fatigue. Add letter index or filter |
| `/rankings/` | 375px | 75 filter chips wrap to ~10 rows of chips. Cluster + collapse "more filters" into a sheet |
| `/teams/alabama.html` | 375px | Hero `.hero__heritage` has 9 inline `<span>` items; verify wrap doesn't break grid |
| Editions article | 375px | Roman numeral section numbers ("VIII.") become visually heavier than the headline at small width — verify type ramp |
| Methodology | 375px | 15,061px scroll with no in-page TOC is a tablet/phone reading death-march. Add sticky in-page nav |

---

## Asset Gaps

### What we NEED but don't have

- **Helmets per program.** 664 slugs × 0 helmets = 0% coverage. CLAUDE.md and the team-page brief both reference helmet imagery; only `logo_primary.png` + `logo_dark.png` exist per team. Confirmed by `find output/site/assets/team-art -name "*helmet*"` returning empty.
- **Wordmarks per program.** Same coverage: 0%.
- **Conference logos.** Used inline implicitly on Wire IMPACT chips ("MOVES SEC") and Conferences index, but no SVG asset library exists.
- **Bespoke iconography for bottom nav.** Currently emoji.
- **Trophy / award glyphs.** "Iron Bowl" trophy on Alabama rivalry card is text-only.
- **Cover art per Edition.** Editions archive renders article cards without imagery.
- **Cover art per Reaction story.** Reactions index has zero images.
- **Player headshots.** Canon entries (e.g. CJ Stroud) have zero images.
- **Stadium photography / silhouettes.** Heritage strip mentions "Bryant-Denny Stadium" as text only.
- **Source-platform logos** (Reddit, Bluesky, ESPN, 247, SB Nation, etc.) for the freshness ribbon when built.
- **`@font-face` declarations** for Inter Display, Source Serif Pro, JetBrains Mono. Currently three pages fall back to Times New Roman or system-ui because the bundle doesn't load fonts.

### What we HAVE but aren't using

- **`team_brand_assets` table with hex colors per team.** Referenced 1× in `reporting.py:5187` (a SELECT 1 existence check). Not applied to legacy team pages. Hex value is available; the `team_pages` v2 renderer reads `profile.accent_hex` per profile (only 17 profiles). The 647 unprofiled teams have a database row with their color but no surface uses it.
- **`tools/inject_rankings_logos.py`** exists in the repo (per CLAUDE.md "Build script parameter discipline" note) — not invoked anywhere visible.
- **`tools/wcfb_enhancements/wcfb-enhancements.css`** with 14 useful patterns (disclosure, tooltip, skeleton, lift, dial, compare panes) — only some pages opt in.
- **`docs/design-system/00-tokens.md`** — a finished, well-considered color/type system that 0% of the shipped CSS actually uses (the shipped CSS uses a different vocabulary).
- **`docs/design-system/01-atoms.md` to `14-modules-game-recap.md`** — eight design-system spec files defining atoms (Eyebrow, MetricTile, BadgeChip, PullQuote, AspirationRung, EventLogItem, PercentileBar, LiveDot, DividerRule) and modules (Pulse, Chronicle, Rivalry, Savant, GameRecap). Some live in `team_pages/assets/styles.css` and ship; most do not.
- **`src/cfb_rankings/ingest/sources/`** — 13 source adapters (Bluesky, campus_news, cfbd_live_game, gdelt_volume, google_news, podcasts_meta, prediction_markets, rss_family, seatgeek, spotify_charts, wiki_awards, wikipedia, youtube_meta) all running but none of their freshness or per-team-volume data surfaces visually.
- **`src/cfb_rankings/cohorts/`** — `aggregate.py`, `divergence.py`, `player_aggregate.py` — computed-cohort engine. Surfaces on `/hub/` and individual canon entries; doesn't appear in the team page hero or wire callouts.
- **`src/cfb_rankings/provenance/freshness_page.py`** — designed for showing source freshness. Not surfaced as a ribbon on team or homepage.
- **`src/cfb_rankings/fan_intelligence.py`** — 1408 lines with `_belief_*`, `_reality_gap`, `_respect_gap`, `_cohesion_*`, `_swing_*`, `_rival_heat`, `_archetype`, `_sarcasm_risk_from_row`, `_confidence`. Surfaces extensively on `/hub/`; minimally on profiled team pages; nowhere else.

---

## Code-Level Recommendations

### Files that need refactoring

- **`src/cfb_rankings/reporting.py` (26,528 lines).** Single-file monolith. The CLAUDE.md correctly warns "DON'T read whole." Move per-section renderers into the existing sub-packages: `_render_home_*` → `editions/homepage_renderer.py` (partially done — line 5384 already delegates); `_render_history_*` → new `history/` package; `_render_player_*` → `players_landing/` (the existing module). Each move is a low-risk symbol relocation.
- **`tools/wcfb_enhancements/wcfb-enhancements.css` (556 lines).** Introduces a fourth token system (`--wcfb-*`) atop the existing three. Either fold its tokens into a single shared root (recommended) or document the layering policy explicitly.
- **`output/site/assets/cfb-index.f3924a06eced.css` (5,842 lines).** The hash in the live Memphis page (`89cc354d9863`) doesn't match this on-disk hash. Cache or deployment drift — verify Vercel rebuild config.

### Renderers that should adopt the team_pages v2 pattern

In order of impact × effort fit:

1. **`reactions/renderer.py`** — strongest mismatch between data quality and visual treatment.
2. **`wire/renderer.py`** — 110 rows × no filters × no source attribution.
3. **`canon/renderer.py`** — three list pages each deserve a per-list cover treatment + cohort-divergence visualization at list-index level.
4. **`mailbag/renderer.py`** — could embed Savant percentile bars as inline evidence atoms.
5. **`reporting.py` `_render_player_*` family (10+ functions)** — players section is broken; rebuild against `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`.
6. **`reporting.py` legacy team-page renderer (Memphis pattern)** — give unprofiled teams a degraded variant of the v2 layout: hero + Savant (when data ≥ FLOOR_GROWING) + Arc + empty-state for Pulse/Rivalry.

### CSS to consolidate

```
docs/design-system/00-tokens.md          (canonical spec, light-mode-first, 6 ramps × 7 stops)
docs/design-system/unified-design-tokens.md   (just-written reconciliation, 2 days old)
output/site/assets/cfb-index.f3924a06eced.css  (5,842-line shipped main bundle)
src/cfb_rankings/team_pages/assets/tokens.css  (429-line shipped team-page tokens, dark-default)
src/cfb_rankings/team_pages/assets/styles.css  (540-line shipped team-page styles)
src/cfb_rankings/team_pages/assets/{rivalry,savant,season_arc,historical_season}_card.css  (~1,200 lines)
tools/wcfb_enhancements/wcfb-enhancements.css  (556-line site-wide enhancement layer with own --wcfb-* tokens)
```

Recommendation: pick `team_pages/assets/tokens.css` as the canonical (it's the most-developed of the shipped artifacts), align `00-tokens.md` to it (or rewrite tokens.css to match 00-tokens.md if the docs are authoritative), then collapse `wcfb-enhancements.css` `--wcfb-*` aliases to reference the canonical tokens via `var()`. Migrate light-theme pages to a single `@media (prefers-color-scheme: light)` overlay rather than maintaining per-section bg hex variants.

### Build-script parameter discipline (existing)

CLAUDE.md already warns several CLI subcommands take `--season` as `required=True`. Audit found no violation in the current build pipeline but worth maintaining the guidance.

### Specific symbol-level fixes

- `src/cfb_rankings/team_pages/renderer.py:_render_pulse` — broaden mood lookback to 60d so sparkline renders during offseason floor.
- `src/cfb_rankings/team_pages/rivalry_card.py:render_rivalry_card` — replace the placeholder `<img alt="Rivalry heat trajectory placeholder">` with a real two-line SVG sparkline.
- `src/cfb_rankings/team_pages/renderer.py` — add `_render_freshness_ribbon(slug)` and call from `_render_hero`.
- `src/cfb_rankings/reactions/renderer.py` — rebuild against `docs/design-system/12-modules-intel.md` ChronicleCard pattern with cohort-divergence bar as cover art.
- `src/cfb_rankings/wire/renderer.py` — add filter chips, IMPACT left-stripe encoding, source-attribution chip per row.
- `src/cfb_rankings/canon/renderer.py` — add `_render_cohort_divergence_bar()` partial + invoke per list-index row.
- `src/cfb_rankings/team_pages/renderer.py:_render_chronicle_section` — already exists; ensure data flow into `team_chronicle_observations` is populated for offseason cards (currently 0 cards rendered on Alabama hero).

---

## Proprietary-Advantage Recommendations

This is the largest section because it's the highest-leverage. For each moat: the visual treatment that would make us obviously, demonstrably non-generic.

### P1. The Live-Source Ribbon (rank-1 differentiator)

A single horizontal strip below every team-page hero (and the homepage cover). Eight tiny chips. Each chip:

```
[reddit ●] 2h    [bluesky ●] 14m    [espn ●] 4h    [247 ●] 1d
[campus ●] 6h    [sb-nation ●] 3h   [wikipedia ●] 12h    [seatgeek ●] 9h
```

Dot color = Tier (green / amber / gray for A / B / D source classes from methodology).
Hover = "last 247 ingest: 1d 2h — 12 hits, last mention 'Saban returns to recruiting trail.'"

Why this wins: it's the only visual that *no other CFB analytics site can copy without first building the pipeline*. The pipeline exists. Surface it.

### P2. The Receipts Strip (proves the model)

Every team-page hero header gets a 1-line:

```
THE MODEL · Sept 1 said "Auburn 6-6, mid-pack SEC." · They're 11-4. · ↑ Aged Well 84%
```

Every Heisman board row gets a "What we said in September" line.
Every Wire transfer row gets a "Model gave this 38% impact, watching" tag.

Why this wins: it's the same UX as the homepage Voices "Aged Well %" — applied to **our own** model. Highest-credibility move on the board.

### P3. Cohort-Divergence Bar (everywhere)

A two-bar horizontal: stat-folks ←→ casuals/diehards, dialed to the divergence_score. Render as a 60-second-glance graphic on:
- Every Wire row (when the divergence threshold is crossed)
- Every Reaction story card (as the cover art — see Big Swing B3)
- Every Canon entry (as the argument — see canon/cj-stroud.html `canon-entry__cohort`)
- Every team-page Pulse module (next to the mood number)
- The homepage "where the stat folks and regular fans disagree" callout (currently text-only)

Why this wins: cohort divergence is the *editorial container* for every other moat. Visualize the container; everything that fits in it becomes more readable.

### P4. The Pulse Sparkline as the National Anchor

Build `/national-mood/` — a single page showing all 134 FBS fanbases' mood as a 7-week sparkline grid, sorted by current mood or by mood-velocity. Color-code by trend direction. This is the single most "Bloomberg terminal" thing the site can do with existing data.

Alternative: embed this as a homepage hero strip — a national-mood ribbon above the editions cover.

### P5. Pulse-Module Floor-Rule Visualization

The Pulse module's `_render_pulse_badge` currently renders "n=0 · awaiting signal" as a flat chip. Visualize the FLOOR_AWAITING (30) → FLOOR_GROWING (100) → full-fidelity ramp as a thermometer-style fill. Turns a placeholder into a graphic that demonstrates the moat's rigor.

### P6. Chronicle Cards as the Editorial Currency

`docs/design-system/12-modules-intel.md` defines 6 card types — `anomaly` (amber), `moment` (coral), `flashpoint` (navy), `echo` (gray), `retroactive` (navy-800), `player_arc` (green-200). Each with a colored top border. Lift this atom and embed on:
- Daily (one Chronicle card per morning, hero)
- Editions cover (3 Chronicle cards as below-hero rail)
- Wire (inline `anomaly` and `flashpoint` cards mid-table when triggered)
- Storyline thread pages (Chronicle cards as the chapter atoms)

### P7. Storyline-Anatomy EKG

Each storyline thread on `/storylines/` index gets a 12-dot horizontal "EKG" showing chapter cadence over the last 12 weeks. Dot size = chapter weight. Color = Active (accent) / Dormant (gray). Clicking expands the timeline.

Why this wins: storylines are an editorial vertical that *only* an LLM-augmented sportswriter can produce at this cadence. Currently presented as eight unstyled headings.

### P8. Per-Player Conversation Pulse

On every player canon entry / player page, surface the `player_conversation_features` data (mentioned in CLAUDE.md, 0 references in `reporting.py` per grep) as:
- A tiny mood sparkline next to the headshot
- A "conversation velocity vs. baseline" multiple
- One LLM-curated representative quote per cohort

This is exactly the Pulse module shrunk to a player-card atom. Same visual vocabulary across team and player surfaces = recognizable design language.

### P9. Reactions as Cover Magazine

(See Big Swing B3.) Every reaction story = card with cohort-divergence as cover art. The trigger logic in `reactions/triggers.py` produces these auto-generated when cohorts diverge ≥X — there is no other CFB analytics site that builds this content. **Currently shipping as plain links.**

### P10. Honors as Per-Card Glyphs

`player_honors` table has Heisman / All-American / etc. markers. `team_honors` table similar. Render these as bespoke iconography (small gold glyph, small bronze glyph) on:
- Player canon entries
- Heisman board rows (with year ribbon)
- Team page heritage strip (currently "Heismans · " as text)
- Roster history tables (currently no glyph)

Even one bespoke glyph (a small laurel for an All-American) elevates the entire site visually.

### P11. CFBD Tier-2 Visualizations Everywhere

The Savant card is the strongest treatment on the site. Lift its `PercentileBar` atom (defined in `docs/design-system/01-atoms.md`) to:
- Wire rows that mention a team's specific weakness
- Compare page (head-to-head mirror bars)
- Conference index (conference-aggregate percentile bars)
- Player canon entries (per-stat percentile bars)
- Editions cover-essay inline anchors

This is mechanical work — the atom is built, just call it more places.

### P12. The Aspiration Ladder

`docs/design-system/01-atoms.md` line 153 defines `AspirationRung` — a left-border-color-coded rung (green achievable / amber stretch / coral dream / gray locked). I didn't see it deployed on any page during the audit. Surface this on team pages as "what this season could become": three rungs, dynamically updated week-to-week. Currently the team page hero metric tile is "BOWL STATUS — Eligible" — a single tile. Aspiration ladder is the visual upgrade.

---

## Appendix: Audit Evidence Summary

### Pages navigated

| URL | Live h1 | Computed bg | Computed font | Charts | Imgs | Scroll px | Status |
|---|---|---|---|---|---|---|---|
| `/` | After the Bracket | #f6f1e6 | Source Serif Pro | 1+ inline SVG | 0 | 10597 | Pass |
| `/rankings/` | (filter UI) | #fafafa | Inter | 0 | 0 | n/a | Needs Work |
| `/teams/alabama.html` | Alabama | dark `--bg-0` | Inter Display | placeholder img + arc SVG | 1 logo | n/a | Pass |
| `/teams/memphis.html` | Memphis | #fafafa | Inter | 0 | 0 | n/a | Needs Work |
| `/wire/` | Every move. Every read. | #f6f1e6 | Source Serif Pro | 0 | 0 | 9533 | Needs Work |
| `/daily/` | (story h2s) | #f8f6f0 | Georgia | 0 | 0 | 2507 | Needs Work |
| `/mailbag/` | The Mailbag | #f6f1e6 | Source Serif Pro | 0 | 0 | 6601 | Needs Work |
| `/reactions/` | Reaction Stories | #0c0e10 | system-ui | 0 | 0 | 937 | Broken |
| `/canon/` | The lists that settle… | #0b0d12 | Inter | 0 | 0 | 1224 | Needs Work |
| `/canon/.../cj-stroud.html` | C.J. Stroud | dark | Inter | 0 | 0 | 1569 | Pass w/res. |
| `/storylines/` | Storyline Threads | #0b0d12 | Inter | 0 | 0 | 1397 | Needs Work |
| `/players/spotlight.html` | Players — 2025 | transparent | **Times New Roman** | 0 | 0 | **769** | Broken |
| `/players/the-room.html` | (no h1) | #fafafa | Inter | 0 | 0 | **769** | Broken |
| `/heisman/` | A full-board Heisman… | #fafafa | Inter | 0 | 0 | 1569 | Needs Work |
| `/hub/` | Michigan's belief is at a decade low. | #f3eee4 | **Source Serif 4** | **28** | 0 | 9671 | Pass |
| `/compare/` | Compare two programs. | #f6f1e6 | Inter | 0 | 0 | 1030 | Needs Work |
| `/conferences/` | The sport gets more interesting… | #fafafa | Inter | 0 | 0 | 6806 | Needs Work |
| `/editions/` | Every issue. | #f6f1e6 | Source Serif Pro | 0 | 0 | 3395 | Needs Work |
| `/methodology/fan-intelligence.html` | Fan Intelligence — Methodology | transparent | **system-ui** | 0 | 0 | 15061 | Needs Work |
| `/history/heatmap/` | Twelve seasons. Every program. One image. | transparent | **Times New Roman** | 1 | 0 | **769** | Broken |

### Token-system fragmentation (the single most-actionable systemic finding)

```
docs/design-system/00-tokens.md
  → --color-navy-400, --color-text, --color-surface, --fs-body, --sp-4

docs/design-system/unified-design-tokens.md  (2 days old, reconciliation attempt)
  → --bg-primary, --fg-primary, --accent-primary, --fs-base, --space-4

src/cfb_rankings/team_pages/assets/tokens.css  (shipped, dark-default)
  → --bg-0, --fg-primary, --accent-primary, --fs-body, --sp-4, --pct-low/high

output/site/assets/cfb-index.f3924a06eced.css  (shipped, ~5,842 lines)
  → mixed; uses both --color-* and --bg-* in places

tools/wcfb_enhancements/wcfb-enhancements.css  (shipped, 556 lines, site-wide overlay)
  → --wcfb-accent, --wcfb-bg-card, --wcfb-fg-primary
```

Five vocabularies. Two of them (`00-tokens.md`, `unified-design-tokens.md`) are spec docs that don't match shipping reality. One (`team_pages/tokens.css`) is the closest thing to a canonical artifact and ships only on profiled team pages. One (`cfb-index.f3924a06eced.css`) is the main site bundle. One (`wcfb-enhancements.css`) is a fourth layer with its own prefix.

**Recommendation:** Promote `team_pages/assets/tokens.css` to `output/site/assets/tokens.css` as the single source of truth. Rewrite all spec docs to reference the shipping file. Migrate `cfb-index.f3924a06eced.css` and `wcfb-enhancements.css` to use the canonical token names. Add a CI test that fails if any module CSS file declares a non-token color hex.

### Font fragmentation

Five font families observed across the live site:
- **Source Serif Pro** — Homepage, Wire, Mailbag, Editions
- **Georgia** — Daily (drift — should be Source Serif)
- **Source Serif 4** — Hub (drift — different variant)
- **Inter Display** — Alabama team page
- **Inter** — Memphis, Rankings, Canon, Storylines, Conferences, Heisman, the-room, Compare
- **system-ui** — Reactions, Methodology (no font loaded)
- **Times New Roman** — players/spotlight, history/heatmap (no font loaded, browser default)

**Recommendation:** Ship `@font-face` declarations for "Inter Display" and "Source Serif Pro" + "Source Serif 4" (one variant) in the main bundle. Pages that fall back to Times New Roman or system-ui are missing the bundle entirely — fix the template's `<link rel="stylesheet">`.

### Navigation fragmentation

| Surface | Links exposed |
|---|---|
| Homepage topbar (desktop) | Rankings, Teams, Players, Heisman, Programs, History, Editions, Wire, How It Works (9) |
| Memphis topbar (legacy renderer) | Power Rankings, Teams, Players, Heisman, Vibe Shifts, Programs, History, NFL Pipeline, The Model, Analysis, Weekly Archive, Matchup Simulator, Compare Teams (13) |
| Mobile bottom nav (all pages) | 🏠Home, 📊Rank, 💡Hub, ⚖️Compare, 📚About (5, emoji glyphs) |

**Recommendation:** One canonical top-nav list (8 items max). One canonical bottom-nav list (5 items, same destinations as the top-nav's most-used). Replace emoji with bespoke SVG icons.

---

## Closing

The product has a 7-out-of-10 ceiling already shipped on two surfaces (`/hub/` and profiled team pages). The data pipeline is genuinely unique. The design system docs are sophisticated and well-considered. **The gap between what the codebase can produce and what the live site shows is the single biggest opportunity on the board.** Closing that gap doesn't require new data or new architecture — it requires lifting four atoms (cohort-divergence bar, freshness ribbon, receipts strip, Chronicle card) into the surfaces that don't have them, retiring three token vocabularies in favor of one, and shipping the player-page brief that's already written.

Estimated total effort to move the entire site to a uniform 7/10: **4–6 sprints**. Estimated effort to ship the Top 5 fixes alone: **1 sprint**.

The most-tragic single line item: **`reactions/`** — the cohort-divergence editorial moat — currently ships as three text-link headings on a dark page. Fixing this one page produces the largest demo-day delta the codebase can give you.
