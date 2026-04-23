# Player Page — World-Class Redesign Brief

**Status:** Strategy + IA + UX guidance. Not yet an implementation plan; a future pass will spec reporting.py changes.
**Owner:** Kevin (product), Claude (research + drafting), Figma (visual design — forthcoming).
**Last updated:** 2026-04-22.
**Scope of v1:** Quarterback pages. Designed to generalize to every position — see §8.
**Reference page used during research:** `output/site/players/cj-carr-4788.html` (CJ Carr, Notre Dame QB, 2025 Heisman-probable, Wk 21 snapshot).
**Related docs:**
- `CFB_INDEX_AUDIT.md` — broader product audit this fits into.
- `CLAUDE_CODE_FIX_PROMPT.md` — active P0-P3 fix queue; player-page work slots alongside, not inside.
- `CLAUDE.md` — repo rules (DON'T edit `output/site/**`, DON'T read `reporting.py` whole, etc.).
- `src/cfb_rankings/fan_intelligence.py` — FI framework that becomes this page's spine.
- `src/cfb_rankings/reporting.py:2280` — `_assemble_player_page_data()` (entry point for upgrades).
- `docs/player_honors_import.md`, `docs/cfbd-tier2-and-safe-operations.md` — existing data-layer context.

---

## 0. Why this doc exists

CFB Index's edge over ESPN/247/On3/SR is interpretation, not data. The QB page is where a casual fan should form a *feeling* about a player in 5 seconds, and an analytical fan should find every metric they want behind progressive disclosure. Today's page is competent but gets neither job done cleanly:

- It reads like a stat dashboard, not an editorial product.
- It carries zero Fan Intelligence (FI is currently team-scoped only — confirmed by grepping the codebase for `player_mentions` / `player_week_conversation_features` — nothing exists).
- It's missing table-stakes legacy-site features (game log, splits, percentile visualizations, trajectory charts).
- It ships with empty placeholder trophy cases in Week 21 for a Heisman-probable QB.

This brief is the durable plan for fixing that across research → design → build.

---

## 1. Thesis

The QB page should feel like three experiences stacked on one URL, in this order:

1. **The vibe read at the top** — in 5 seconds you know what fans, the model, and the country all think of the player *right now*, and where those diverge. Pure FI.
2. **The traditional box-score foundation** — cleaner, more contextual than ESPN/SR. Every stat has a rank, a percentile chip, an 8-week spark.
3. **The analytical exhibit** — Savant-style percentile card, splits, pass chart, peer comparator. Tucked behind progressive disclosure so casuals don't drown.

FI is the spine. Traditional stats are the foundation. Advanced stats are the exhibit.

---

## 2. UX principles — the reading ladder

Every module on the page must explicitly serve one of four reading tiers. If it doesn't fit, it doesn't belong.

- **5-second read** — Hero + QB Fingerprint Card. Name, team, one number, one vibe, one trajectory spark.
- **30-second read** — Fan Intel card, top 3 stats with percentile chips, current accolade probabilities. This is the ceiling for a casual-fan arrival from a social link. They should leave informed, not drowned.
- **5-minute read** — Game log, splits, full Accolade Lens, peer comparator, Signature Story.
- **Deep-dive** — Advanced Savant card, pass chart, full stat explorer, scheme/supporting-cast context. All behind one "Analytics" drawer.

**Design rule:** No module mixes tiers. A 5-minute table does not sneak into the 30-second zone. A 5-second card is not padded with 30-second detail. Clean tiering is what makes the page legible to both audiences on the same URL.

**Design rule:** Progressive disclosure is the core interaction pattern. Default-collapsed drawers, tabbed modules, expandable rows. Never a wall of data on first paint. (Nielsen Norman / IxDF progressive-disclosure literature is the reference.)

**Design rule:** Every number has context. "24 TD" alone reads worse than "24 TD (94th pct · vs FBS QBs · #30/391)." No bare numbers anywhere on the page.

**Design rule:** Three semantic color ramps, no more:
- **Percentile ramp** — red → grey → blue (Baseball Savant convention; blue = high for stats; invert for inverted metrics like pressure-to-sack).
- **Belief ramp** — red → grey → green (FI fan sentiment; green = bullish).
- **Accolade accent** — gold, reserved exclusively for award probability and status.
Mixing these semantics anywhere breaks the whole page.

---

## 3. UX primitives — design atoms Figma should build first

Nine reusable components. Every module composes from these.

1. **Percentile Bar** — Savant-style gradient bar, value pinned, peer label beside. Desktop inline inside 3-col grid; mobile full-width with label stacked above. Inverted variant for metrics where low-is-good (pressure-to-sack, turnover-worthy plays).
2. **Belief Dial** — Horizontal meter Doomposting → Mixed → Very Bullish, current score as pin, last-week and season-baseline as faint ticks, confidence band underneath. Port from existing `mood-meter-track` / `mood-meter-fill` CSS in `reporting.py` (team Mood Card).
3. **Trajectory Spark** — 160×40px sparkline used everywhere: Heisman nowcast, 8-week stat rates, accolade probability, belief week-over-week. Dotted baseline for "start of season," solid line = current.
4. **Eyebrow → Number → Narrative** — Every card has this exact grammar. 12px uppercase eyebrow ("Heisman Heat" / "Fan Belief" / "vs. Pressure"), big display-font number (Bebas Neue), one 14px sentence of plain-English read.
5. **Drawer** — Existing `<details class="player-stats-drawer">` pattern. Sharpen affordance (clearer "▸ Show advanced" / "▾ Hide").
6. **Tab Bar** — ≤4 tabs, pill shape, active inverts ink/bg. Mobile: horizontal scroll, not dropdown.
7. **Chip** — Three sizes × three colors (neutral/positive/negative). Used for rank, percentile, peer label.
8. **Pill Comparator** — 1-4 player pills with headshot/initials + team dot + X to unpin. Mobile collapses to chip strip.
9. **Selector Grid** — The Accolade Lens's signature component. Grid of pills, one per All-America selector (AP/FWAA/AFCA/WCFF/SN/SI/Athletic/PFF/CFN/Athlon/Steele), gold when named to 1st team, silver for 2nd, grey empty. See §7.

**Every primitive needs:** desktop + mobile + loading + empty + error states.

---

## 4. Page information architecture (top to bottom)

### 4.1 Hero — "QB Fingerprint"

Three-column desktop, single-column mobile.

- **Left (identity)** — Display-font name, team wordmark + conference, position / class / #number / measurables stacked. Hero photo *if available*; otherwise a monogram tile in team accent. Don't fake photos.
- **Middle (the fingerprint)** — Five vibe cells, each an Eyebrow → Number → Narrative block:
  1. **CFB Index QB Score** (0-100 composite: opponent-adjusted EPA + CPOE + VOR passer).
  2. **Heisman Heat** (current rank + 8-week spark + ballot/finalist/win probability).
  3. **Fan Belief** (Belief Dial inline + archetype label: "Hype Train" / "Grounded" / "Doomer Ball").
  4. **Respect Gap** (fan score − national score, signed).
  5. **Reality Gap** (fan belief vs. structural percentile; green/orange/blue by alignment).
- **Right (accolade ribbon)** — Stacked mini-cards for the top 3 live accolades. For QB: Heisman · Davey O'Brien · Consensus All-American. Each shows probability + rank + trajectory spark.

Background: subtle diagonal gradient tinted in team accent at 6% opacity. `--team-accent` token already wired.

**Mobile:** vertical stack; five vibe cells become a horizontal snap-scroll; accolade ribbon becomes a 3-chip row above the first fold.

### 4.2 Fan Intel — "The Room on [Player]"

One dark card (reuse `.mood-card` CSS), four panels:

1. **Belief header** — archetype chip, Belief Dial, one-sentence narrative, sample confidence badge ("142 mentions · high confidence" via `_confidence()` gates).
2. **Three-axis strip** — Reality Gap · Respect Gap · Swing · Polarization cohesion stack (green/grey/red segmented bar).
3. **Storylines** — top 3 ranked narratives from `_fetch_storylines()` filtered by `player_id` (see §6 for the data pipeline extension required).
4. **Rival Heat pills** — per-rival fanbase tone. ("USC fans grudgingly respect · Michigan fans dismissive · Alabama fans quiet.")

**Empty state:** low-conversation players fall back to team mood with honest copy: *"Not enough player-specific chatter yet. Belief below reflects Notre Dame's team Mood Card."* Reuse `mood-waiting-banner`.

### 4.3 Accolade Lens — see §7 below (big generalization)

### 4.4 Current Season Production — traditional stats, done better

- **Stat summary ribbon** — keep 3-tile pattern; each tile gets percentile chip + 8-week spark.
- **Game log** (NEW, P0) — compact table: week, result (W/L + score chip), opponent (with rank + logo), CMP/ATT/YDS/TD/INT/YPA/RTG, one auto-generated 1-line note. Mobile: horizontal scroll with pinned first column OR tap-to-expand row.
- **Season tables with context row** — each season row gets a subline: *"Team 10-3 · Offense #12 SP+ · OC: Mike Denbrock · Scheme: RPO-heavy."*
- **Inline definition tooltips on every column header** — extend `metric-help-bubble` to traditional tables.
- **Stat Explorer drawer** — keep today's filterable/sortable table, default-collapsed.

### 4.5 Advanced Metrics — Savant card

One block. Vertical stack of ~12 percentile bars, red→grey→blue gradient. Above the bars, one narrative line: *"Elite: deep-ball accuracy (94th). Strength: 3rd-down EPA (88th). Concern: pressure-to-sack (34th)."*

Ordered **best → most interesting → concerns** (not alphabetical) so the eye gets the story:

1. EPA / dropback
2. CPOE
3. Success rate
4. Explosive-play rate (20+)
5. aDOT
6. Deep-ball accuracy (20+ air yards)
7. Pressure-to-sack rate (inverted)
8. 3rd-down EPA
9. Red-zone TD rate
10. Play-action EPA split
11. Scramble EPA
12. Turnover-worthy play rate (inverted)

**Peer toggle:** vs. FBS / vs. Power-4 / vs. Heisman-probable / vs. his own career. Same pills as hero.

**Definition drawer:** tap any metric name → full explanation opens.

### 4.6 Splits — four tabs

Situational · Defense quality · Home/Road · Pocket (clean vs. pressure). Compact tables, every cell gets a percentile chip. Pocket tab is the screenshot-bait — "clean: 0.38 EPA/dropback (92nd) · pressure: −0.08 (24th)."

### 4.7 Signature Story

**Generated, not templated.** Offline job picks top 3 salient facts (highest-percentile stat, signature game, storyline leader, recruiting→production delta, respect gap) and generates prose. Stored to DB, regenerated on data change. Renders inside a simple `.prose-panel` with one highlighted pull-quote. No stat tiles crowding it.

### 4.8 Accolade Trajectory

Multi-line chart: x = weeks 1-15, y = probability %. One line each for Heisman · Davey O'Brien · Consensus All-America · All-Conference. Toggle any on/off. Annotate weeks where a big game moved the needle ("Wk 9 · vs USC · +14 Heisman"). Hover/tap reveals the belief dial for that week.

### 4.9 Peer Comparator

Default auto-picks 3 closest Heisman-model peers. Four pill-slots at top (pin/unpin). Below:
- Radar (desktop) / vertical percentile bar stack (mobile) of the 12 advanced metrics.
- **Respect-gap grid** — mini table: model score, fan belief, national belief, respect gap. *Unique to CFB Index.*

### 4.10 Supporting Cast & Scheme Context

Small module, high signal. From team-level data we already have:
- OL pressure allowed (percentile).
- WR drop rate / contested catch % (aggregated receivers).
- OC fingerprint — run rate, play-action rate, PROE (pass rate over expected).
- Scheme fit tag — *"Thrives in PA-heavy / structured systems; his OC ranks 12th in PA rate."*

### 4.11 Trophy Case + Honors Timeline

Keep at bottom. These become **confirmed past honors only**. Accolade Lens is the live-projection future. Distinct visual treatment.

### 4.12 NIL + Draft

Small card: On3 NIL valuation, 247 composite rating, NFL mock draft consensus range (for juniors/seniors). Bounded — not the page.

### 4.13 Bio / Recruiting / Transfer / Roster Timeline

Keep as-is. Durable Wikipedia strip at the bottom.

---

## 5. Mobile (≥65% of users) — non-negotiable patterns

- **Rule:** nothing wider than the viewport unless it scrolls horizontally inside its own container, or restacks vertically. No horizontal *page* scroll ever.
- **Hero fingerprint:** vertical stack; five vibe cells horizontal snap-scroll.
- **Accolade Lens:** tab bar horizontal scroll; ladder rotates to horizontal; Selector Grid 3-wide.
- **Advanced Savant card:** vertical bars, unchanged — mobile-first naturally.
- **Tables (game log, splits, season):** horizontal scroll with pinned first column OR tap-to-expand per row.
- **FI Mood Card:** stacks; Belief Dial stays full-width.
- **Peer Comparator:** pills as horizontal chip strip; percentile bars stack vertically per metric.

Target tap target ≥44×44. No pinch-to-zoom. Thumb-friendly nav.

---

## 6. Data sources — what unlocks what

| Source | Access | Unlocks |
|---|---|---|
| **CFBD API v2 (tier 2/3)** | Paid, we have it | Box-score stats, `player_usage`, `pbp_data` with EPA/WPA, `cfbd_game_box_advanced`, `cfbd_metrics_wepa_players_passing/rushing`, 2025 clutch-aware WP. Engine. |
| **CFBD play-by-play** | Same | Compute aDOT, pressure-proxy, play-action splits, deep-ball, red-zone, 3rd-down, pass-chart dots. Everything in §4.5 lives here. |
| **CFBD GraphQL (tier 3)** | Paid | Faster queries, real-time subs — future live in-game FI. |
| **cfbfastR / sportsdataverse** | Free | Reference implementation for EPA/CPOE math; rolling-EPA vignettes. |
| **ESPN QBR leaderboard** | Free (value public, formula proprietary) | Legacy-familiar number alongside our model. |
| **Sports Reference CFB** | Free scrape | Historical comparisons beyond CFBD coverage. |
| **PFF public articles** | Free, citation-only | Can cite top-10 rankings; cannot scrape grades. |
| **On3 NIL / 247 composite** | Free (on player page) | NIL card, recruiting context. |
| **NFL mock draft aggregators** (Walter, Drafttek, NFLMockDraftDatabase) | Free scrape | Draft projection card. |
| **Reddit + X conversation sample** (existing FI pipeline) | We already have | Extend to player-entity tagging to power "The Room on [Player]." |

**The one new ingestion dependency:** player-entity tagging in the conversation pipeline.

Today, FI primitives in `src/cfb_rankings/fan_intelligence.py` operate on `team_week_conversation_features` / `team_conversation_daily` / `conversation_storylines` — all team-scoped. A grep of the codebase for `player_mentions` / `player_conversation` / `entity_id` returned nothing. To light up the "The Room on [Player]" module, we need a parallel `player_week_conversation_features` table (same shape, keyed on `player_id`) and `storylines` rows tagged with `entity_type='player'`.

Until that's built, every player-FI module **must** gracefully fall back to the team Mood Card with honest empty-state copy. No fake player belief. The existing `_empty_profile()` pattern in `fan_intelligence.py` is the template.

---

## 7. Player Standing — the universal status ladder

### 7.1 Why we re-scoped this module

Iteration 2 called this "Accolade Lens" and oriented it around awards. That only sings for the top 1% of CFB. A QB3 at Vanderbilt loads the page and sees "Heisman probability: <1%" on an empty trophy case — a dead module for 95% of players.

**Player Standing** replaces the Accolade Lens as the page's primary status hub. It answers the one question every fan walks in with: *how good is this guy, actually, right now?* One module, 17 rungs, same component for a walk-on and for the Heisman frontrunner. The rung changes; the grammar doesn't. Awards become *tabs inside* Standing — where they belong, as one stream of evidence for rung placement — not a parallel module.

### 7.2 The 17-rung ladder

Six perceptually distinct tiers, 17 rungs total. Tier count matches ~4-7 chunks of working memory; rung count gives enough internal resolution to show real in-season movement.

```
TIER 0 — Not on team
  R00  Walk-on (preferred / recruited / invited)
  R01  Scout team / redshirt development

TIER 1 — On the 2-deep
  R02  Deep reserve (rostered, no meaningful snaps)
  R03  Backup (3rd down / situational / emergency)
  R04  Rotational (15-40% snap share, package player)

TIER 2 — Starter
  R05  Part-time starter (injury fill-in, split QB room)
  R06  Starter (>60% snap share, not a difference-maker)
  R07  Impact starter (above-average production for conference)

TIER 3 — Recognized
  R08  Watch-list name (on 1+ major award watch list)
  R09  All-Conference HM / 2nd team
  R10  All-Conference 1st team
  R11  National watch / fringe All-America

TIER 4 — Elite
  R12  All-American (1+ of 5 NCAA-recognized selectors)
  R13  Consensus All-American (3 of 5)
  R14  Unanimous All-American (all 5)

TIER 5 — Apex
  R15  National Player-of-the-Year finalist
  R16  National Player-of-the-Year winner / Heisman winner
```

**"Canonized"** (Hall of Fame, retired numbers, all-time teams) is *not* a rung — it's a permanent ribbon on the hero for alumni whose status transcends the in-season ladder.

### 7.3 Placement cascade (how a player lands on a rung)

Short-circuit cascade — first rule that applies wins, weekly.

1. **Official POTY outcomes.** Trophy winner → R16. Invited finalist → R15. (Source: `ingest/honors.py` + weekly awards-board scraper.)
2. **All-America outcomes.** Unanimous → R14. Consensus → R13. 1+ NCAA-recognized selector → R12. National fringe or midseason AA list → R11.
3. **All-Conference outcomes.** 1st team → R10. 2nd team / HM → R09. (Source: conference pressers Monday after conference championship.)
4. **Watch-list / preseason mentions.** On 1+ major award watch list, no hardware yet → R08.
5. **Production gates** (no awards yet).
   - Snap% ≥ 60 AND production percentile ≥ 75 at position → R07.
   - Snap% ≥ 60 → R06.
   - Snap% 40-60 → R05.
   - Snap% 15-40 → R04.
   - Snap% < 15 AND on gameday roster → R03.
6. **Roster-only signals.** On roster, depth chart ≥ 3, no snaps → R02. Scout-team / redshirt flag → R01. Preferred walk-on, signed but not yet enrolled → R00.

Snap% comes from play-by-play; production percentile is WEPA per opportunity for skill players, composite PFF-style for OL/defense. When snap data is unavailable (common for Group of 5), fall back to depth chart + stat-based heuristics + mention volume in FI.

### 7.4 Three reads, one module (progressive disclosure)

**5-second read — The Rail.** Full-width horizontal rail. 17 tick marks. Filled gold marker at the current rung; faint ghost marker at last season's rung. The current rung's name in large type above ("IMPACT STARTER"). That's it — position at a glance, trajectory implied.

**30-second read — The Tier Pills.** Six tier labels below the rail (On-team / 2-deep / Starter / Recognized / Elite / Apex). Current tier's pill is solid; others outlined. Tap a tier → rail zooms into that tier's rungs with names visible.

**5-minute read — The Rung Drawer.** Tap the current-rung marker → bottom sheet (mobile) / right drawer (desktop) with:
- **Why he's here** — the specific signal that placed him. *"Started all 11 games at 78% snap share. WEPA/dropback = 0.31, 74th percentile among P4 QBs."*
- **What moves him up** — next rung's gate in plain English. *"Crack national top-25 in WEPA/dropback, or get named to FWAA's midseason All-America team."*
- **What moves him down** — honest downside. *"If his snap share drops below 60%, he slides to Starter."*
- **Trajectory sparkline** — weekly rung history over the season.
- **Peer strip** — 4 players currently at this exact rung (calibration: *"oh, same rung as Dante Moore and Garrett Nussmeier"*).

**Deep-dive — Accolade Tabs (nested inside Standing).** Under the rail, a tab strip of award streams relevant to this player's position. Each tab is the previous iteration's Accolade Lens content — probability tiles, trajectory, selector grid, "what needs to happen" narrative. These live *inside* Standing because they answer the question "okay, he's R08 watch-list — what specifically is he being watched for?"

### 7.5 Awards taxonomy (tab content inside the rail)

NCAA-recognized *official* All-America selectors (since 2002): AP, AFCA, FWAA, Sporting News, Walter Camp. ≥3 of 5 = **Consensus**; all 5 = **Unanimous**. Full 2025 selector pool (14 bodies): add SI, The Athletic, USA Today, ESPN, CBS Sports, PFF, CFN, Athlon, Phil Steele.

Award streams, organized:

- **National Player of the Year:** Heisman · Walter Camp · Maxwell · AP POTY · SN POTY.
- **Position awards (QB):** Davey O'Brien · Manning · Johnny Unitas Golden Arm.
- **Other-position specialty awards:** Archie Griffin · Bednarik · Nagurski · Outland · Biletnikoff · Mackey · Thorpe · Lou Groza · Ray Guy.
- **Freshman honors:** Shaun Alexander FOY (FWAA) · FWAA Freshman All-America · On3 True Freshman AA · 247 True Freshman AA · conference All-Freshman teams.
- **All-America:** Consensus · Unanimous · each individual selector's 1st/2nd/3rd.
- **All-Conference:** SEC / B1G / ACC / B12 / etc. first/second/third, coaches' vs. media vote where both exist.
- **Weekly honors:** Walter Camp POTW · Davey O'Brien QB of the Week · conference weekly awards · watch lists.

Every tab renders the same four fields: *where he stands now*, *what it would take*, *trajectory*, *official result*. Inside each tab, three zones: left ladder (award-specific sub-rungs Watch → Conf → AA → POTY), middle three probability tiles (Win · Finalist · Ballot), right auto-generated "what needs to happen" narrative. Below: the **Selector Grid** — pill grid, one chip per selector, gold/silver/HM/empty. Still the single best "how real is this honor" visualization in sports.

### 7.6 Polymorphism

**By position.** Same 17-rung spine for every player. Only the accolade tab set changes:
- DB → Nagurski · Bednarik · Thorpe · All-America · All-Conference.
- WR → Biletnikoff · All-America · All-Conference.
- TE → Mackey · All-America · All-Conference.
- OL → Outland · All-America · All-Conference.
- K/P → Groza / Guy · All-America · All-Conference.

Placement logic shifts slightly (OL has no "production" in the stat sense — swap to pressure-rate-allowed, sack rate, PFF grade) but the ladder visual stays identical so fans can compare a punter to a Heisman QB on the same scale.

**By career stage.** Two hero modes:
- **Active** — live rail, current-rung marker, trajectory spark, weekly updates.
- **Career retrospective** (seniors post-bowl, NFL alumni) — rail becomes a cross-season arc, each season a rung, peak rung highlighted, Canonized ribbon pinned above when applicable.

---

## 8. Design Craft — typography, color, motion, states

The design-system layer. Everything here is enforced via tokens + component props so modules can't drift.

### 8.1 Design language (three disciplines, married)

Borrow ruthlessly:

- **Baseball Savant** — the red→grey→blue diverging percentile pill. Color encodes *rank among peers*, not good/bad. Fluent across sports-literate fans. Keep it exactly.
- **Apple Sports / Fitness** — number-first typography, one huge number instead of twelve small ones, achievement-ring motion. Borrow the hierarchy and the ring metaphor for award probabilities.
- **Linear / Raycast** — restraint. No gradient backgrounds, no drop shadows, no decorative illustration. Every pixel earns its place.

Actively *don't* borrow: ESPN's wall-of-tiles overwhelm, 247Sports' ad-heavy flex-dumps, Awwwards-winning "hero scroll reveal" player pages (gorgeous, but 15 seconds to reach a stat — wrong for a data product).

### 8.2 Typography

**Single family.** Inter Display for headings and UI, Inter for body. No secondary "elegant" serif. Serifs read as nostalgic on sports pages, and we're not nostalgic — we're current.

**Fluid scale via `clamp()`** — kills 80% of breakpoints; supported in every 2026 browser.

```css
--fs-display: clamp(2.5rem, 5vw + 1rem, 5.5rem);    /* hero number */
--fs-h1:      clamp(1.75rem, 2.5vw + 0.5rem, 3rem);
--fs-h2:      clamp(1.25rem, 1.5vw + 0.25rem, 1.75rem);
--fs-body:    clamp(0.9375rem, 0.25vw + 0.875rem, 1.0625rem);
--fs-meta:    clamp(0.75rem, 0.1vw + 0.75rem, 0.8125rem);
```

**The rhythm rule (most important typography call on a stats page):** every *number that is a data point* is tabular-nums + slightly heavier than its label. Every *label* is uppercase eyebrow, 11-12px, letter-spacing 0.08em, de-emphasized. Bright number, quiet label. Violating this is the cardinal sin that makes ESPN's pages feel cluttered.

### 8.3 Color system (final)

Three semantic ramps + one neutral scale. No decorative colors.

- **Percentile ramp** — `oklch`-interpolated red `#d93a4a` → neutral `#6b7280` → blue `#1e6fd9`. Every percentile.
- **Belief ramp** — red `#c0392b` → neutral → green `#2d8659`. FI signals only.
- **Accolade gold** — `#c9a227` base, `#e4c76b` highlight. Reserved exclusively for honors, winner glow, achievement rings. Never decorative.
- **Neutrals** — 10-step OKLCH grey scale, dark-mode-first. Surface `oklch(0.18 0.01 250)`, text `oklch(0.95 0.01 250)`.

All three ramps pass WCAG 2.1 AA: 3:1 for graphical elements, 4.5:1 for text, against both primary surface and its mid-step. OKLCH interpolation means luminance is continuous, so colorblind users perceive order correctly.

**Dark mode is the default**, light mode is supported but secondary — most traffic arrives in the evening.

### 8.4 Motion grammar

Motion is structural, not decorative. Four roles, exact durations + easings:

| Role | Duration | Easing | Example |
|---|---|---|---|
| Reveal | 240ms | `cubic-bezier(0.22, 1, 0.36, 1)` (out-quart) | Drawer opening, bottom sheet rising |
| State change | 180ms | `cubic-bezier(0.4, 0, 0.2, 1)` (standard) | Tier pill selection, filter toggle |
| Data entry | 420ms total, 30ms stagger | `ease-out-cubic` | Rail marker settling after refresh |
| Delight | 800ms | `cubic-bezier(0.34, 1.56, 0.64, 1)` (overshoot) | Achievement ring on rung-up. Max 3× per page load |

Cap any single animation at 500ms — anything longer breaks flow. Linear easing forbidden (objects never move at constant speed in the real world). All motion wrapped in `@media (prefers-reduced-motion: reduce)` → instant, no exceptions.

### 8.5 Interaction craft

- **Every tappable thing** has distinct hover / active / focus. Hover: 4% surface lift. Active: inset shadow. Focus: 2px gold outline, 4px offset.
- **Nothing is hover-only.** Tooltips become bottom sheets on touch. Every hover drawer has a tap equivalent.
- **Copy-on-tap.** Long-press a stat → clipboard. Pros do this.
- **Shareable deep links.** Every tab state, open drawer, filter combo updates the URL. The sleeper feature that makes a stats site go viral.
- **Keyboard nav.** Tab order through hero → rail → tabs. Arrow keys move the rung marker inside the rail. `?` opens a shortcut overlay.

### 8.6 Data-viz craft

- **Sparklines** — 44px tall mobile (thumb), 32px desktop (denser). Terminal value always a filled dot with a label. Axis ticks forbidden inside a sparkline.
- **Percentile pills** — the atomic unit. 88×22px, Savant ramp, 3:1-contrast filled white circle at value position. Label left, value right.
- **Pass charts** — field-oriented SVG (not Cartesian scatter). Hex-bin on large samples, dots under 100 attempts. Blue = completion, grey = incomplete, gold = TD, red = INT (the only red that isn't percentile).
- **Game logs + stat explorer** — share one virtualized `<StatTable>` primitive. Sticky header, sticky first column (opponent), row hover, light zebra.
- **Trajectory lines** — weekly values with an annotated band at the "to stay in current rung" threshold. Fan sees at a glance when he slipped.

### 8.7 Mobile as the primary design target

~65% of traffic. Mobile-first, not desktop-adapted-down.

- **Bottom sheets for every drawer.** Never full-screen unless the content *is* the user's goal. Modal for destructive actions, non-modal for exploration. Drag handle, tap-outside-to-dismiss, hardware back dismisses.
- **Thumb zones.** Primary CTAs and tab bars in the bottom third. Hero up top; sticky subnav at the bottom on mobile, top on desktop.
- **Horizontal scroll for tabs** with scroll-snap. Fade gradient on the right edge signals "more →" without a scrollbar.
- **44×44 minimum touch targets.** Every pill, tab, row, chip.
- **Container queries.** Modules adapt to their slot, not the viewport. Same FI card at 100% of a narrow phone and at 50% of a desktop two-column — one component, any context.

### 8.8 The four states every module must design

- **Empty.** Specific, honest copy. Never "No data available." For Signature Story on a freshman backup: *"He hasn't written his page yet. We'll start filling it in when he gets snaps."*
- **Loading.** Shape-accurate skeletons, never generic spinners. Fade in at 200ms, not before.
- **Partial.** Show what we have, place honest placeholders for what we don't. *"Snap data unavailable for Group of 5 games this week."* Never hide a module for incompleteness.
- **Error.** Plain English, retry action, way to reach us. Never a stack trace.

### 8.9 Accessibility (beyond WCAG minimum)

- All three ramps pass 3:1/4.5:1 at every step.
- Every data point has a screenreader-friendly sibling (`aria-label` on every percentile pill: *"WEPA per dropback: 0.31, 74th percentile among Power 4 QBs"*).
- `prefers-reduced-motion` collapses every animation.
- `prefers-contrast: more` swaps neutrals for high-contrast + thicker borders.
- 44×44 targets everywhere (WCAG 2.2 SC 2.5.8).
- Focus ring gold, 2px, 4px offset, never suppressed.
- Skip-to-content link. Strict heading hierarchy for screen-reader landmark nav.

### 8.10 Performance budget

Static-site advantage — be ambitious:

- First Contentful Paint < 0.8s on 4G.
- Largest Contentful Paint (hero number) < 1.2s.
- Cumulative Layout Shift < 0.02. Hero numbers reserve their space from frame 1.
- JS payload per player page: < 35KB gzipped. Rail, FI card, stats tables, Signature Story all work without JS. Tabs, filters, pass chart are progressive enhancements.
- Images: WebP + AVIF, sizes + srcset, zero layout shift on load.
- Fonts: `font-display: swap` with metric-matched fallback (invisible FOUT).

---

## 9. Figma handoff brief

Give Figma the existing CJ Carr HTML file + the repo's token files + this doc. Commission work in this order:

1. **Tokens pass** — extend existing CSS custom properties with:
   - Percentile gradient ramp (red → grey → blue, 5 stops + neutral).
   - Belief ramp (red → grey → green).
   - Accolade gold accent (reserved exclusively for award probability/status).
   - Motion tokens for drawer expand/collapse.
2. **Ten primitives** (§3 + Standing Rail): Percentile Bar · Belief Dial · Trajectory Spark · Eyebrow/Number/Narrative · Drawer · Tab Bar · Chip · Pill Comparator · Selector Grid · **Standing Rail** (17-rung tick bar, tier pills, rung drawer). Each with desktop + mobile + loading + empty + error.
3. **Hero Fingerprint** — two breakpoints, all five cells, collapsed + expanded, Canonized ribbon variant for alumni.
4. **Player Standing module** — rail + tier pills + rung drawer. Then accolade tabs nested inside: Heisman tab fully designed, then grammar applied to Davey O'Brien · All-American · All-Conference to prove polymorphism. Demonstrate at three rung extremes: walk-on (R00), impact starter (R07), Heisman finalist (R15).
5. **FI "The Room on [Player]"** — one fully realized card.
6. **Advanced Savant card** — one fully realized.
7. **Game log + Splits** — desktop + mobile.
8. **Peer Comparator** — 3-slot default.

**Figma file structure:**
- Page 1: *Principles* — 4-tier reading ladder, color semantics, motion grammar table, state matrix.
- Page 2: *Tokens & primitives* — type scale, three color ramps, ten primitives (all states).
- Page 3: *Hero + Player Standing* — the crown jewels, designed to polish.
- Page 4: *Modules* — FI, Savant, Splits, Signature Story, Game Log, Peer Comp, Supporting Cast.
- Page 5: *Full page flow* — 1400 / 768 / 375 breakpoints.
- Page 6: *Standing extremes* — walk-on, scout team, backup, rotational, starter, All-Conference, AA, Heisman finalist, Heisman winner, Canonized alumni.
- Page 7: *States* — low-data, mid-data, partial, error, loading.

---

## 10. Roadmap — P0 → P3

### P0 — visible within 1 week (high-impact, mostly existing data)

1. **Player Standing rail — 17 rungs.** Placement cascade rules #2-5 (awards + production gates + roster signals). No accolade tabs yet, no FI tie-in. Renders for every rostered player, not just stars.
2. **Hero Fingerprint redesign.** Name, team, current rung tag, composite score, trajectory spark. Canonized ribbon variant ready for alumni.
3. **Design tokens.** Fluid-type `clamp()` scale, three color ramps (OKLCH), motion tokens, dark-mode-first surfaces, container queries on every module.
4. **Game log table.** Pure CFBD player game stats. Biggest legacy parity gap.
5. **Percentile chips + 8-week sparklines on every stat row.** Biggest "feels fancier than ESPN" delta for least work.

### P1 — 2-3 weeks

6. **Accolade tabs nested inside Standing** — Heisman, Davey O'Brien, Manning, Unitas for QBs first. Includes Selector Grid.
7. **Signature Story generator** — build-time LLM, feature-flagged, "flag this" link.
8. **Advanced Savant card from CFBD pbp** (EPA/db, CPOE, success, explosive, aDOT, deep ball, PA split, red-zone, 3rd-down, pressure-to-sack).
9. **Splits tabs** — situational, defense quality, home/road, clean vs. pressure.
10. **Watch list + weekly awards ingestion** feeding placement cascade rule #4. (`src/cfb_rankings/ingest/honors.py` already the start.)

### P2 — the differentiator phase

11. **Extend conversation pipeline to player entities.** The real investment. Unlocks full "Room on [Player]" module, player-scoped Vibe Shifts on the homepage board.
12. **Peer Comparator + respect-gap grid.**
13. **Pass chart + Supporting Cast Context module.**
14. **Accolade tab polymorphism** — every award stream, every position. DB/WR/TE/OL/K/P tab sets.
15. **Career-retrospective Standing variant** — cross-season rail for seniors post-bowl and alumni.

### P3 — polish

16. **"What needs to happen"** scenarios per accolade stream (extended).
17. **NIL + draft card.**
18. **Live game mode** (requires CFBD tier-3 + real-time infra).

---

## 11. Opinionated calls (the things worth arguing about)

- **Don't ship a carousel hero.** ESPN/247 do and it always looks dated. One strong editorial hero + one spark > slideshow.
- **Collapse advanced by default, preview one wow-line above the fold.** Casuals don't want a radar in their face.
- **Every number gets context** — rank + percentile + cohort. No bare numbers.
- **Don't add live-game features until player-FI is in.** FI is the moat. Live is table stakes. Build the moat first.
- **Signature Story must be generated, not hand-curated.** Otherwise 400+ QBs get uneven coverage and voice drifts. Store prompt + facts, regenerate on data change.
- **Page is a weekly product, not a season page.** Hero numbers, FI belief, trajectory, Signature Story all move Monday morning. That's the ritual that brings people back.
- **Hero fingerprint is non-negotiable.** Everything else is negotiable. Nail the fingerprint, the rest composes.
- **Don't ship without the Selector Grid.** The single best design idea in this doc.
- **Three semantic color ramps. No more.** Percentile / Belief / Accolade. Mixing breaks the page.
- **Accolade Lens is polymorphic from day one.** Never ship a QB-only version.
- **Resist the urge to chart everything.** Three charts max on the page: Savant card, Accolade Trajectory, optional Pass Chart. The rest is tables, percentile bars, and prose.

---

## 12. Open questions (Kevin)

- Are we OK committing to the CFBD tier-3 GraphQL subscription to enable real-time features in P3, or is tier-2 the ceiling for now?
- Should the player-entity conversation pipeline be a separate P1.5 project given its scope, or assumed as part of P2?
- For the Accolade Lens, do we want to scrape On3 / 247 All-Freshman team releases ourselves, or accept a gap until an aggregator publishes them?
- Preference on hero photo policy: licensed headshots, no photos (monograms only), or AI-generated team-colored silhouettes as fallback?
- Signature Story generator: self-hosted small LLM on a schedule, or API call via Anthropic during the weekly build?

---

## 13. Appendix — references

- [Baseball Savant percentile rankings leaderboard](https://baseballsavant.mlb.com/leaderboard/percentile-rankings) — percentile-card UX bible.
- [Nielsen Norman — Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) · [IxDF — Progressive Disclosure (2026)](https://ixdf.org/literature/topics/progressive-disclosure) — tiering rationale.
- [Figma — Top Web Design Trends 2026](https://www.figma.com/resource-library/web-design-trends/) — current visual-language context.
- [nfelo — NFL QB Rankings](https://www.nfeloapp.com/qb-rankings/) · [nfelo — Era-Adjusted QB](https://www.nfeloapp.com/qb-rankings/era-adjusted/) — single-number + comparator UX.
- [PFF — How PFF grades QB play](https://www.pff.com/news/pro-how-pff-grades-quarterback-play) — grade semantics, big-time throw / turnover-worthy play definitions.
- [Pro-Football-Reference — About our advanced stats](https://www.pro-football-reference.com/about/advanced_stats.htm) — aDOT / IAY / CAY / YAC definitions.
- [NFL Next Gen Stats data dictionary](https://nflreadr.nflverse.com/articles/dictionary_nextgen_stats.html) — time-to-throw / aggressiveness / completion-probability.
- [CFBD API Access Tiers](https://collegefootballdata.com/api-tiers) · [CFBD REST v2 GA](https://blog.collegefootballdata.com/api-v2-is-now-in-general-availability/) · [CFBD 2025 Win Probability overhaul (clutch-aware)](https://blog.collegefootballdata.com/revamping-win-probability-2025/).
- [cfbfastR function reference](https://cfbfastr.sportsdataverse.org/reference/index.html) · [cfbd_pbp_data](https://cfbfastr.sportsdataverse.org/reference/cfbd_pbp_data.html) — reference implementation for EPA/CPOE/WPA math.
- [Wikipedia — 2025 All-America team](https://en.wikipedia.org/wiki/2025_All-America_college_football_team) · [Wikipedia — All-America selectors & criteria](https://en.wikipedia.org/wiki/All-America_college_football_team) · [Wikipedia — Unanimous All-Americans](https://en.wikipedia.org/wiki/List_of_unanimous_All-Americans_in_college_football).
- [FWAA — 2025 Freshman All-America](https://www.sportswriters.net/fwaa/news/2026/01/14/fwaa-unveils-25th-anniversary-freshman-all-america-team) · [Wikipedia — Shaun Alexander FOY](https://en.wikipedia.org/wiki/Shaun_Alexander_Freshman_of_the_Year_Award) · [Wikipedia — Maxwell Award](https://en.wikipedia.org/wiki/Maxwell_Award) · [Sports Reference — Awards & Honors Index](https://www.sports-reference.com/cfb/awards/index.html).
- [On3 transfer portal + NIL](https://www.on3.com/transfer-portal/) — NIL valuation source.

---

## 14. Session log (for context-compression recovery)

### 2026-04-22 — Iteration 1 (research + initial brainstorm)
Kevin asked for deep research on making QB pages world-class. Heavy FI spine, whatever data it takes. Deliverable: brainstorm in chat. Claude audited CJ Carr page (`output/site/players/cj-carr-4788.html`), read `fan_intelligence.py` structure, grepped player-page render paths in `reporting.py` (confirmed `_assemble_player_page_data` at line 2280, no player-FI integration). Web research on CFBD tier-2, PFF grading, NGS, QBR, PFR advanced stats, Baseball Savant, nfelo. Produced iteration-1 brainstorm covering module list, FI extension plan, data sources, P0-P3 roadmap.

### 2026-04-22 — Iteration 2 (UX + Accolade generalization)
Kevin asked to refine with design/UX as the star, note that Figma will design from the guidance, and generalize Heisman to All-American / All-Conference / All-Freshman / other awards. Claude web-researched the full CFB awards landscape (NCAA-recognized selectors, All-Freshman taxonomy, position awards), Baseball Savant percentile-card UX, progressive-disclosure principles, nfelo design. Produced iteration-2 brainstorm introducing the 4-tier reading ladder, 9 UX primitives, Hero Fingerprint spec, Accolade Lens generalization with Selector Grid, mobile-first patterns, Figma handoff brief.

### 2026-04-22 — This brief
Consolidated both iterations into this single durable doc for future sessions / Figma / Kevin. Supersedes the chat transcript for planning purposes.

### 2026-04-22 — Iteration 3 (Player Standing + Design Craft)
Kevin: *"i like the accolade lens module, but it should go further than that. it should have more rungs including like starter, benchwarmer, etc. then focus on doing deep research to make the design, UX and frontend absolutely perfect for everything."*

Reframing: Accolade Lens was award-centric → only worked for the top 1%. Generalized into **Player Standing** — 17 rungs across 6 tiers (walk-on → scout team → deep reserve → backup → rotational → part-time starter → starter → impact starter → watch-list → All-Conf HM → All-Conf 1st → National watch → All-American → Consensus AA → Unanimous AA → POTY finalist → POTY/Heisman winner). Placement via short-circuit cascade: official outcomes → selector outcomes → conference outcomes → watch lists → snap%/production gates → roster-only signals. Accolade Lens becomes **nested tabs inside Standing** instead of a parallel module. "Canonized" (HOF, retired numbers) is a hero ribbon, not a rung.

Deep UX/design research this iteration: Baseball Savant player page redesign, The Athletic storytelling, F1 telemetry dashboards, Strava progression/trophy case, Apple Fitness achievement rings, NFL NGS, progressive disclosure 2025 best practices, WCAG-accessible diverging palettes (OKLCH), fluid typography + container queries 2026, mobile bottom-sheet patterns, Linear/Raycast microinteraction standards, sports data-table design (sticky headers, virtualization, row hover).

Locked in new §8 **Design Craft**: Inter/Inter Display single family, fluid `clamp()` scale, three OKLCH ramps passing WCAG 2.1 AA at every step, four-role motion grammar (Reveal 240ms / State 180ms / Data-entry 420ms stagger / Delight 800ms overshoot), universal hover/active/focus, copy-on-tap, shareable deep links, keyboard nav, sparkline/percentile-pill/pass-chart/table specs, mobile-first (bottom sheets, thumb zones, container queries, 44×44 targets), four mandatory states per module (empty/loading/partial/error), a11y beyond WCAG, performance budget (FCP <0.8s, LCP <1.2s, CLS <0.02, JS <35KB).

Doc changes: §7 rewritten as Player Standing. New §8 Design Craft added. §9/§10 renumbered. Figma handoff (§9) updated — ten primitives now (adds Standing Rail), six-page Figma file structure, "Standing extremes" page added. Roadmap (§10) reshuffled: Standing rail + design tokens + Hero Fingerprint moved into P0; accolade tabs + Signature Story generator + Savant + Splits in P1; FI player pipeline + Peer Comp + Pass Chart + polymorphism + career-retrospective variant in P2.
