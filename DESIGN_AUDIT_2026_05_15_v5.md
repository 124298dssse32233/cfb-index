# CFB Index — Triple Audit, v5 (Bespokeness + Zero-Touch Automation)

**Date:** 2026-05-15
**Auditor:** Claude (autonomous, orchestrated 26-investigator parallel deep-dive across v2 + v3 + v4 + v5)
**Live site:** https://wonderful-margulis-8ec96b.vercel.app
**Supersedes:** [v1](DESIGN_AUDIT_2026_05_15.md) · [v2](DESIGN_AUDIT_2026_05_15_v2.md) · [v3](DESIGN_AUDIT_2026_05_15_v3.md) · [v4](DESIGN_AUDIT_2026_05_15_v4.md)

### Where v5 sits

v1 found problems. v2 explained why they were structural. v3 specified what the site looks like when complete. v4 specified how to build it. **v5 specifies what makes the site uniquely itself — and how the entire content engine runs without Kevin ever clicking "Publish."**

Two premise updates from the owner shaped this round:

1. **The site must feel bespoke.** Each program, each player, each rivalry, each conference, each season-phase, each data source, each historical era — every dimension that makes college football *college football specifically* — must be visible in design as that-thing's-page, not a template render.
2. **All content generation, all data refreshes, all editorial publishes must be automatic going forward.** Kevin doesn't open the app to "ship something." The site runs itself.

---

## What v5 Adds Over v4

Eight v5 investigators produced eight build-ready bespokeness + automation artifacts:

1. **Per-program bespoke editorial system** — all 17 profiled programs (Alabama, Auburn, Florida, Georgia, Massachusetts, Michigan, Notre Dame, Ohio State, Oklahoma, Oregon, Penn State, Tennessee, Texas, UConn, USC, Vanderbilt, Washington) spec'd across 9 axes: signature identity module, heritage-strip extensions, signature metrics ladder, era markers, rivalry intensity ranking, signature-story type, fan-voice vocabulary, mascot-voice empty states, color treatment. 33-program expansion plan to 50. Final profile YAML schema (additive — no migration). 5 universal opt-in atoms.

2. **Per-player + per-position bespoke system** — frame-selection algorithm; 9 position-frames (QB/RB/WR-TE/OL/DL/LB/DB/K-P/ST) each with signature metric, anti-metric, 3 peer comparisons, visual stack, voice register; 10 archetype-frames (Generational, Transfer, Late Bloomer, Family Legacy, Position-Move, Walk-On, First-Round Lock, Heisman Frontrunner, Quiet Production, Comeback); complete chart-helper inventory under `src/cfb_rankings/charts/positions/`; Heisman Board redesign (9 modules); Players Landing redesign; NFL Pipeline section; player-vs-player Compare; "What He Eats" Diet module; 100 Best Players list-page structure.

3. **Per-rivalry bespoke system** — 4-tier rivalry taxonomy (Mythic / Regional Defining / Conference Standard / Annual); 4 design primitives (Seam CSS / Trophy Glyph SVG / Anchor Set YAML / Voice Register override); complete bespoke specs for all 8 Tier-1 mythic rivalries (Iron Bowl, Michigan-OSU "The Game", ND-USC, Red River, Stanford-Cal "Big Game", Army-Navy, Auburn-Georgia "Deep South's Oldest", Yale-Harvard "The Game"); 17 Tier-2 regional-defining abbreviated specs; `/rivalries/<slug>.html` anatomy; rivalry-week takeover; multi-rivalry Saturday front page; dormant-rivalry archive treatment; 50-glyph trophy commission plan.

4. **Per-conference + cross-program identity** — 11 FBS conferences each with bespoke top-rule color/width/secondary trim, masthead typography, ground (paper/wool), motif SVG, editorial register, Era Strip annotation set, signature module (Saban Tree for SEC, Centennial Lineage for Big Ten, Football-vs-Basketball axis for ACC, Scoreboard Ticker for Big 12, Diaspora Map for Pac-12 remnants, Promotion Track for AAC, Blue-Turf Marker for MWC, G5-Over-P4 Tracker for Sun Belt, Tuesday Night Scoreboard for MAC, Membership Carousel for C-USA, per-program for Independents); 13 FCS-conference tier-2 treatments; conference-vs-conference matchup surface (55 pairs); `/realignment/` permanent surface with 157-year Sankey + "team in 5 conferences" highlights; coaching trees (Saban tree, Tressel/Day tree); G5-vs-P4 narrative thread; Independent-programs treatment (Notre Dame, Service Academies, UConn/UMass); FCS + DII/DIII/NAIA respect tiers.

5. **Per-season-phase + weekly-cadence + hour-by-hour-Saturday system** — complete Phase Atlas (10 season phases × 9 design variants per phase) covering homepage frame, Pulse mode, team-page hero, Wire taxonomy, Daily structure, Editions theme, Heisman mode, Reactions threshold, Storylines cadence; weekly cadence matrix Mon-Sun with per-day homepage composition; hour-by-hour gameday Saturday state machine; 10 phase-specific surfaces (Portal Wire, Spring Game Hub, Media Days Live, Camp Tracker, Selection Sunday Live, Bowl Season Index, Coaching Carousel Tracker, Heritage Window, Bowl Sunday cover essay, NSD Tracker); phase-transition choreography; complete 2026-27 editorial calendar with literal dates; declarative `PHASE_COMPOSITION` config structure.

6. **Data-source → named-editorial-surface map** — all 16 ingest sources mapped to recognizable named features: CFBD Tier 2 → "The Numbers Lane", Arctic Shift Reddit → "The Time Machine", Bluesky → "The Bluesky Wire", Wikipedia → "The Pageview Spike", Campus newspapers → "The Campus Wire", School athletics → "The Front-Page Edit", Locked On → "The Pod Tape", Beat-writer Substack → "The Beat", GDELT → "The News Volume Gauge", SeatGeek → "The Box-Office Tell" (the contrarian-signal moat), Spotify Charts → "The Regional Cultural Callout", Prediction Markets → "The Money Line vs The Crowd", YouTube → "The Recap Tape", Google News → "The Headline Drift", Wiki Awards → "The Trophy Case", CFBD Live → "The Live Lane". Plus 5 signature cross-source combinations (Two-Source Verification, Box-Office Contradicts The Boards, Regional Interest Spike, Wire Moved Before The Line, Archive Comp), 8 Source Spotlight landing pages, and 5-ship implementation order.

7. **Arctic Shift Reddit archive moat exploitation** — 13 years of Reddit post archives (Vandy-Bama 2024 verified as #1 all-time r/CFB postgame thread at 39,232 upvotes), 12 bespoke surfaces with literal algorithms + examples + ship locations: "Highest June Since 2014" callouts, Game-Week Volume Index, Vocabulary Drift Charts, Before-and-After Archive Pivots, Historical Comp Engine (echo card source with cosine ≥0.78 threshold), Forgotten Saturday Resurfacing, Top-Comment-of-the-Decade per Program, Vocabulary Lineage Map, Cross-Era Fan Cohort Analysis, Player Name Velocity Tracker, Recurring Mood-Cycle Detection, Archive-Triggered Editorial Hooks. Plus the `/archive/` Atlas landing page, quarterly Editions special-issue calendar, per-program `/programs/<slug>/discourse-history/` pages, the "What the Boards Said" sidebar pattern, and the pre-2013 "deep history" sourcing strategy (Library of Congress Chronicling America, Sports-Reference, Newspapers.com, ProQuest, university digital archives).

8. **The Zero-Touch Automation Architecture** (the spine of v5) — complete inventory of the 15 existing `.github/workflows/*.yml` files with cron interpretations, manual-trigger audit (12 manual gates identified including the structural seam where `publish-edition-weekly.yml` is decoupled from the deploy pipeline), per-surface end-to-end editorial-generation pipelines (10 surfaces × 5-row trace: data → trigger → LLM → validation → write → publish), complete LLM model-routing matrix with per-surface model + prompt template + validation chain + retry policy + failure fallback + weekly cost ceiling (total $85/wk = $4,420/yr with auto-throttle at $120/wk), imagery auto-pipeline (FLUX.1 replacing Midjourney for true API automation, CLIP-similarity gate), backfill resume logic, the "Kevin Zero-Touch" architecture (weekly digest email Fri 17:00 ET, `/admin/queue/` page with quality-gate sliders, `/admin/panic` button, per-surface auto-publish gates), the 10-sprint sequence grounded in real file paths and verification gates, and the complete risk register with recovery plans for every failure mode.

---

## Part 1 · Per-Program Bespokeness

Each of the 17 profiled programs gets a one-of-one signature identity module that no other program has. v4's 4 program-personality typography classes are extended into 9 bespoke axes per program. Below: condensed table; per-program details in Appendix A.

### The bespoke axis matrix (17 programs × 9 axes — condensed)

| Program | Signature identity move | Signature story type | Top fan-vocab phrases |
|---|---|---|---|
| **Alabama** | `<div class="bama-process-counter">` — "2,847 days since the last loss that mattered" (denominator: 2022 title-game loss to Georgia) | "the early-season worry that became nothing" | the standard / the process / the elephant in the room / Bama bias / RTR |
| **Auburn** | `<div class="aub-iron-bowl-clock">` — countdown from August onward to the alternating Jordan-Hare/Tuscaloosa Iron Bowl | "the play that becomes folklore" (Kick Six, Cam-back) | War Eagle / Aubie / Toomer's Corner / the Plains / Kick Six |
| **Florida** | `<div class="fla-swamp-thermometer">` — heat-index reading for upcoming home games | "the in-state recruiting battle" | Go Gators / Chomp / the Swamp / Gator Chomp / Albert |
| **Georgia** | `<div class="uga-between-the-hedges">` — every section wrapped in 6px hedge-leaf pattern, top + bottom border | "the defense that wins it in the fourth" | Go Dawgs / between the hedges / Glory Glory / silver britches / the G |
| **Massachusetts** | `<div class="umass-ladder-rung-tracker">` — vertical 6-rung aspiration ladder with currently-achieved rung lit | "the conference win that breaks a years-long drought" | Rise as one / Flagship / Sam the Minuteman / McGuirk / one rung |
| **Michigan** | `<div class="mich-victors-ledger">` — running ledger "1,020 wins — most in college football" as the page's load-bearing fact | "the rivalry recalibration" (Ohio State drought break) | Go Blue / Hail to the Victors / Those who stay / The Team The Team The Team / leaders and best |
| **Notre Dame** | `<div class="nd-schedule-strength-meter">` — 12-stop SOS meter under wordmark: "Notre Dame plays an 11th-game schedule inside a 12-game calendar" | "the schedule that bends without breaking" | play like a champion today / Touchdown Jesus / subway alumni / ND speed / lake effect |
| **Ohio State** | `<div class="osu-michigan-week-thermometer">` — sticky countdown "Days until The Game · 64" from Week 1 through Week 13 | "the calendar collapses into one Saturday" | O-H / I-O / the standard is the standard / Beat Michigan / Script Ohio |
| **Oklahoma** | `<div class="okl-schooner-strip">` — Sooner Schooner SVG crosses left-to-right after each home win | "the Heisman QB who arrives ready" (3 in 3 years: Mayfield, Murray, Hurts) | Boomer / Sooner / Schooner / Owen Field / Sooner Magic |
| **Oregon** | `<div class="oreg-uniform-of-the-week">` — Thursday-revealed helmet+jersey+pants combo as 3 colored chips with combo-nickname | "the uniform that became a meme" | Go Ducks / ScO Ducks / Win the Day / uniform reveal Thursday / Division Street |
| **Penn State** | `<div class="psu-white-out-calendar">` — page-header background flips to full-bleed white for 7 days leading to announced White Out | "the White Out that lifts the season" | We Are / Penn State / Happy Valley / Linebacker U / 409 |
| **Tennessee** | `<div class="tenn-checkerboard-endzone">` — 32px orange-and-white checkerboard band edge-to-edge on hero, evoking Neyland end-zone | "the offense that scores too fast to think about" | Rocky Top / Go Vols / Vol Walk / running through the T / Big Orange |
| **Texas** | `<div class="tex-burnt-orange-monogram">` — 280px Longhorn watermark `rgba(191, 87, 0, 0.06)` on page-right gutter | "the QB who came home" | Hook 'em / Eyes of Texas / the 40 Acres / DKR / we're back (used ironically) |
| **UConn** | `<div class="uconn-both-teams-strip">` — "Both teams are Huskies · MBB 6 titles · WBB 11 titles · FB writing its paragraph" | "the bowl bid that confirms the rebuild has traction" | Go Huskies / Both teams are Huskies / The Rent / Storrs to Hartford / Jonathan |
| **USC** | `<div class="usc-tailback-u">` — horizontal scroll of 7 Heisman-winning RB/QB headshots (Garrett, OJ Simpson, White, Allen, Palmer, Bush, Caleb Williams) with year + Heisman pose silhouette | "the QB-RB tandem that arrives ready-made" | Fight On / Tailback U / Trojan family / Tommy Trojan / Conquest |
| **Vanderbilt** | `<div class="vand-anchor-down-anchor">` — 280px-tall gold anchor SVG descending from heritage strip on page-right gutter | "the player who chose Nashville" | Anchor Down / AD / Diego / the dawn of Diego / Lea ball |
| **Washington** | `<div class="wash-husky-pacific-context">` — Pacific Northwest cartographic ornament: Husky Stadium silhouette against Lake Washington + Cascades | "the QB who arrives via portal and runs the table" (Penix 2023) | Go Dawgs / U Dub / Bow Down to Washington / Apple Cup / Lake Washington |

### The five universal opt-in atoms (gated by `program_flags`)

These atoms exist as composable components any program (the 17 + future profiles) can opt into via profile flag — if false, the atom doesn't render.

1. **`<atom-houndstooth-texture>`** — gated by `has_houndstooth_tradition`. 16px houndstooth at opacity 0.04 to designated era-strip band. Currently Alabama-only.
2. **`<atom-uniform-of-week-strip>`** — gated by `has_uniform_culture`. 32px combo strip below wordmark. Currently Oregon-only; could extend to Maryland (flag jersey), Florida (themed games).
3. **`<atom-white-out-takeover>`** — gated by `has_white_out_tradition`. Themed-game color takeover for 7 days. Currently Penn State; variant pattern for Iowa Pink Out, Tennessee Checkered Neyland, Notre Dame Green Out.
4. **`<atom-checkerboard-motif>`** — gated by `has_checkerboard_motif`. 24px end-zone-checker pattern. Currently Tennessee + Notre Dame (helmet checker).
5. **`<atom-basketball-school-cross-ref>`** — gated by `has_basketball_first_identity`. 32px strip referencing institution's basketball program. Currently UConn; could extend to Kentucky, North Carolina, Indiana, Syracuse, Kansas (if FBS-profiled).

Two additional candidate atoms flagged: `<atom-service-academy-credentials>` (Army/Navy/Air Force) and `<atom-blue-turf>` (Boise State / Coastal Carolina / Eastern Michigan).

### Profile-frontmatter schema extension (additive — no migration)

```yaml
# All existing fields preserved. New additions:

signature_identity:
  hero_module: str               # CSS class of the program's one-of-one module
  hero_module_copy: str
  signature_story_type: str
  hero_metric: str               # the "big number" monument
  hero_metric_label: str

heritage_motifs:
  - kind: enum[texture, glyph, ornament, hairline]
    name: str
    asset_path: str
    css_class: str
    applies_to: list[str]
    opacity: float | null

signature_metrics_ladder:
  - rank: int
    metric_key: str
    label: str
    context: str
    direction: enum[higher_is_better, lower_is_better]

program_flags:
  has_houndstooth_tradition: bool
  has_uniform_culture: bool
  has_white_out_tradition: bool
  has_checkerboard_motif: bool
  has_basketball_first_identity: bool
  has_independent_status: bool
  has_service_academy_status: bool
  has_blue_turf: bool

color_treatment:
  bg_tint_alpha: float
  secondary_color_role: enum[accent_only, glyph_only, dual_stripe, body_secondary]
  rotation_source: str | null    # e.g., "uniform_of_week_color" for Oregon

fan_voice:
  pulse_whitelist: list[str]
  context_flags: dict[str, str]
  outsider_phrases_excluded: list[str]

signature_story_recipes:
  - type: str
    trigger: str
    components: list[str]
    headline_template: str
```

### 33-program expansion plan (to 50 total)

**SEC/Big Ten/ACC/Big 12 (20):** LSU, Texas A&M, Florida State, Miami (FL), Clemson, North Carolina, Wisconsin, Iowa, Nebraska, Kansas State, TCU, Baylor, Colorado, Arizona State, Indiana, Illinois, Missouri, Kentucky, Ole Miss, Mississippi State.

**G5 (8):** Boise State, Memphis, South Florida, Tulane, SMU, Coastal Carolina, James Madison, App State.

**Distinctive identities (5):** Army, Navy, Air Force, BYU, Liberty.

### Vandy profile factual correction

Current `era_annotations` references "Shedeur-beater" in 2024. Pavia's signature upset was vs Alabama (Jalen Milroe), not Shedeur Sanders / Colorado. Fix in `profiles/vanderbilt.md` before next render.

---

## Part 2 · Per-Player + Per-Position Bespoke System

### The frame-selection algorithm

Before any module renders, the page runs `select_player_frame(player_id) -> (PositionFrame, ArchetypeFrame[])`. PositionFrame is exactly one of nine. ArchetypeFrame is zero-to-three of ten. Position frame sets chart helpers; archetype frames overlay editorial modules. Both write to the same module-stack and the Composer composes in the canonical order.

Tags are computed offline in `src/cfb_rankings/players/archetype_tags.py` and persisted to `player_archetype_tags(player_id, tag, confidence, evidence_ref)`. A page never re-derives them at build time.

### The 9 position frames

| Position | Signature metric | Anti-metric (threshold) | 3 peer comparisons | Visual stack |
|---|---|---|---|---|
| **QB** | EPA per dropback, opponent-adjusted | turnover-worthy play rate (3.5%) | Stroud-22 / Burrow-19 / Murray-18 (elite junior); Hartman-23 / Hooker-22 / Nix-23 (steady senior); Manziel-12 / Daniels-23 / de Laura-21 (early-career flash) | 13-row Savant Card + Win-Prob Timeline + Pass-Chart Heatmap (9-cell field zone) + Pocket Split bar |
| **RB** | rushing EPA per carry, opp-adj | stuffed-rate (22%) | Henry-15 / Walker-21 / Hall-21 (power); Bijan-22 / Pollard-19 / Etienne-20 (scat); CMC-16 / Akers-19 / Conner-16 (receiving) | 10-row Savant Card + Gap Heatmap (6-cell A/B/C × L/R) + Receiving Route Tree (≥30 routes) |
| **WR/TE** | receiving EPA per route run | drop rate (8% WR, 11% TE) | Wilson-21 / Jeudy-19 / Smith-19 (outside); Renfrow-18 / Pittman-19 / Olave-21 (slot); Kittle-16 / Kmet-19 / LaPorta-22 (TE) | Savant Card WR variant + 9-Route Tree + Air-Yards Histogram |
| **OL** | pass-block win rate at snap position | sack rate allowed >4%; penalty rate >6% | Sewell-20 / Slater-20 / Penning-21 (LT); Nelson-17 / Linderbaum-21 / Zinter-23 (guard); Humphrey-16 / Linderbaum-21 / Frazier-21 (center) | 5-Man Unit Diagram + Snap-Count Distribution + Pressure-Allowed Heat |
| **DL** | pass-rush win rate (or pressure %) opp-adj | missed-tackle rate >14% on rushing downs | Hutchinson-21 / Anderson-22 / Bosa-18 (edge); Carter-22 / Davis-21 / Wilkins-18 (interior) | Pass-Rush Position Bar (4 alignments) + Sack Timeline + Run-Stop Heat |
| **LB** | run-stop % | coverage EPA allowed/snap > +0.18 | Carter-22 / Werner-19 / Foskey-22 (MIKE); Anderson-22 / Edwards-19 / Walker-22 (WILL); Simmons-19 / JOK-21 / Owusu-Koramoah-20 (hybrid) | Savant Card LB variant + Tackle-Location Heatmap (30×15 yard pitch grid) + Blitz-Type Stacked Bar |
| **DB** | coverage EPA/coverage snap (inverted) | penalty rate >8% on coverage snaps | Surtain-20 / Stingley-21 / Witherspoon-22 (outside CB); Sneed-19 / Gardner-Johnson-18 / Holland-20 (slot/nickel); Hamilton-21 / Branch-23 (safety) | Savant Card DB variant + Per-Coverage-Type Win Rate (6 types) + Target-Volume Heatmap |
| **K/P** | FG % opp-adj by distance / net punt avg | miss rate inside 40 >8% | era-matched specialists | Distance-Distribution Dot Plot + Hang-Time Histogram |
| **KR/PR** | EPA per return | fumble rate >1.5% | all-time returners cohort | Career Return-Trajectory Chart (half-field overlay) + Return-Volume Spark |

### The 10 archetype frames (mandatory modules per tag)

| Archetype | Mandatory modules | Voice register |
|---|---|---|
| **Generational** | Era-Strip Overlay, Cross-Era Comparable Dumbbell, "The Year That Changed The Program" Receipt Strip, Cohort Divergence at His Peak | Connections Desk, elegiac, long-sentence allowance |
| **Transfer Star** | Transfer Portal Lineage Flow, Before/After Savant Pair, Prior-Program Callback Essay, Transfer Class Cohort Card | Heat Desk for splashy, Connections for journeyman |
| **Late Bloomer** | Years-of-Patience Multi-Program Career Arc, Pre-Bloom Receipt Strip, Cohort Late-Bloomer Peers | Connections, slightly amused |
| **Family Legacy** | Family-Tree Era Strip, Generational Comparable Savant Pair, Family-Heritage Pull-Quote | Connections, archive-fluent |
| **Position-Move** | Dual-Position Savant Cards, Snap-Distribution Bar, Travis Hunter Cross-Era Benchmark | Heat, screenshot-bait |
| **Walk-On** | Underdog 17-Rung Ladder, Recruiting-vs-Production Gap Slope, Renfrow Anchor Peer Card | Receipts Desk |
| **First-Round Lock** | NFL Pipeline Attachment, Mock Draft Probability Tornado, Combine-Projection Bridge | Heat Desk |
| **Heisman Frontrunner** | Probability Tornado, Candidate Sparkline Full-Season, "August Said" Receipts Strip | Heat for present, Receipts for retrospective |
| **Quiet Production** | Cohort Divergence Dumbbell (primary), Name-Velocity Spark, "Model Has Him" Receipts Strip | Receipts Desk almost exclusively |
| **Comeback Story** | Return Receipt Strip, Games-Since-Return Spark, Pre/Post Savant Pair | Connections for legacy, Heat for current-season |

### The Heisman Board redesign — 9 module zones

1. **1924-2024 Lineage Era Strip masthead** — 100-year horizontal strip, every winner a dot, color-banded by position
2. **Frontrunner Card** — full-width photo + name in Bowlby 96px + current win probability as jersey numeral 112px
3. **Top-8 Watchlist Candidate Sparkline Grid** — 8 sparkline rows × weeks 1-15
4. **Top-3 Probability Tornado** — three horizontal bars with confidence bands
5. **EPA-vs-Archetype Scatter** — by position-appropriate metric, candidate dots with surname annotation
6. **Receipts Strip — August Said** — one row per top-8 candidate
7. **Quiet Production Callout** — candidates with positive cohort divergence (analytics rank > media rank)
8. **Final Ballot Vote Tracker** — post-season, regional stacked bar
9. **Calibration Retrospective** — last year's August probability vs final outcome, dot field with calibration line

### Chart helper inventory (new module structure)

```
src/cfb_rankings/charts/positions/
  qb.py       — qb_savant_card, qb_win_prob_timeline, qb_pass_chart_heatmap, qb_pocket_split_bar, qb_dropback_distribution
  rb.py       — rb_savant_card, rb_gap_heatmap, rb_yac_distribution, rb_third_down_usage_bar, rb_receiving_route_tree
  wrte.py     — wr_savant_card (with is_te flag), wr_route_tree, wr_air_yards_histogram, wr_alignment_split_bar, wr_contested_catch_grid
  ol.py       — ol_five_man_unit_diagram, ol_snap_distribution_by_alignment, ol_pressure_allowed_heatmap_by_gap, ol_pass_run_block_paired_bar
  dl.py       — dl_pass_rush_position_bar, dl_sack_timeline, dl_run_stop_heatmap_by_gap, dl_savant_card_dl
  lb.py       — lb_savant_card, lb_tackle_location_heatmap, lb_blitz_type_stacked_bar, lb_coverage_responsibility_spark
  db.py       — db_savant_card, db_per_coverage_type_bar, db_target_volume_heatmap_by_depth, db_forced_incompletion_spark
  kp.py       — k_distance_distribution_dot_plot, p_hang_time_histogram, k_net_punt_vs_distance_grid, k_clutch_kick_receipt_strip
  st.py       — st_career_return_trajectory, st_return_volume_spark, st_fair_catch_discipline_bar
```

Every helper signature: `(*data) -> str` returning inline SVG. Every helper has a `_caption` companion for JetBrains Mono numerals.

### Top-10 highest-impact player-page improvements (ranked)

1. **Composer + ArchetypeFrame system** — `src/cfb_rankings/players/composer.py` + `archetype_tags` migration + 10 archetype-module sets
2. **Position-frame Savant Card variants** — the 9 helpers eliminate the brand-killing "QB-shaped Savant Card on a CB page"
3. **"Diet" module — What He Eats** — universal across positions, immediately readable, trivial to compute from `pbp_data`
4. **Signature Metric jersey numeral** — 112px Bowlby with peer-reference one-liner
5. **Cohort Divergence Dumbbell at universal-atom level** — the brand atom, ships on every player surface
6. **Player Standing 17-rung ladder** — unifies walk-on and Heisman frontrunner pages with the same component
7. **Heisman board redesign** — currently 1 table row, becomes the 9-module page above
8. **Player-vs-Player compare with bold-the-winner**
9. **Players Landing redesign** — fixes broken surface, 9-position-tab grid + Trending + Quiet Production rails
10. **NFL Pipeline section + Brick Tower** — credibility surface making the site read as publication, not blog

---

## Part 3 · Per-Rivalry Bespoke System

### The 4-tier rivalry taxonomy

| Tier | Name | Count | Design Privileges |
|---|---|---|---|
| **1 — Mythic** | "the eight" | 8 | Full bespoke header; commissioned trophy glyph; per-rivalry color seam CSS custom property; Era Strip spans full series; rivalry-week homepage takeover; dedicated `/rivalries/<slug>.html` long-form |
| **2 — Regional Defining** | "the twenty" | 17 | Standard bespoke header; commissioned trophy glyph; standard Era Strip; rivalry-week team-page takeover; `/rivalries/<slug>.html` standard |
| **3 — Conference Standard** | "the thirty-five" | ~35 | Trophy glyph in meta strip; standard Dual-Line Build; no takeover; row on `/rivalries/` index |
| **4 — Annual** | unbranded | ~150+ | Generic Series Card on team page; no rivalry treatment |

### The four design primitives

**1. Seam (CSS custom property)** — per-rivalry block consumed by team-page hero, rivalry card, and detail page masthead:

```css
.rivalry--iron-bowl {
  --rivalry-color-a: #9E1B32;          /* Crimson */
  --rivalry-color-b: #DD550C;          /* Burnt orange */
  --rivalry-seam-angle: 18deg;
  --rivalry-seam-width: 2px;
  --rivalry-glyph: url('/assets/trophies/iron-bowl.svg');
  --rivalry-voice: "elevated-historical";
  --rivalry-tier: 1;
}
```

**2. Trophy Glyph (SVG)** — ~50 commissioned outline glyphs at 24×24 stroke-2, all `currentColor`, all `aria-hidden`. Each renders at 14px (meta-strip inline), 24px (rivalry-card header), 56px (rivalry-week takeover).

**3. Anchor Set (YAML)** — 5–10 historical moments per Tier-1 rivalry, persisted in `data/rivalry_anchors/<slug>.yaml`:

```yaml
- year: 2013
  title: "Kick Six"
  one_line: "Chris Davis returns a missed 57-yard field goal 109 yards as time expires."
  winner_slug: auburn
  national_implication: true
  source: "encyclopediaofalabama.org"
```

**4. Voice Register override** — profile gets `rivalries[].voice_register_override`. Choices: `elevated-historical`, `epic-sentence`, `military-formal`, `clinical-restraint`, `regional-tall-tale`.

### The 8 Tier-1 mythic rivalries

| Rivalry | Seam tilt | Trophy glyph | Signature viz | Voice |
|---|---|---|---|---|
| **Iron Bowl** (Alabama-Auburn) | 18° | molten-iron-droplet + tongs | "Auburn from 35+" histogram of game-winning field position (Kick Six at 109 yards alone in its column) | elevated-historical |
| **Michigan-OSU "The Game"** | 0° vertical-clean | single block-letter "G" in serif slab | Big Ten title-share donut (60% maize/scarlet, 40% everyone combined) | elevated-historical, capitalize "The Game" always |
| **ND-USC** (Jeweled Shillelagh) | 32° (acute — references 1,818-mile diagonal) | curved oak cudgel + ruby/emerald beads | East-West alternation strip (100-cell horizontal, color split by winner — visualizes the rivalry's defining structural feature) | elevated-historical + epic-sentence permitted for Bush Push paragraph |
| **Red River Showdown** (Texas-OU) | 0° vertical at literal 50-yard line | Golden Hat (10-gallon cowboy hat) | State Fair Saturday calendar (124 cells, exposes 90+ year venue streak) | elevated-historical, anchored to State Fair |
| **Stanford-Cal "Big Game"** | -8° (reverse tilt — only Tier-1 negative, references The Play's chaotic geometry) | Stanford Axe head + plaque | The Play diagram (hand-drawn-feel SVG tracing 5 laterals + trombone collision) | epic-sentence for The Play paragraph |
| **Army-Navy** | 0° + brushed-silver gradient (CIC trophy material) | three stacked footballs in pyramid | Service Academy Sankey (3-way CIC trophy years) | military-formal — no slang, ranks in attribution, alma-mater ritual callout |
| **Deep South's Oldest Rivalry** (Auburn-Georgia) | 0° vertical | War Eagle + Uga's collar combined glyph | Heisman-density timeline (Sullivan '71, Walker '82, Bo '85, Cam '10 as 4 raised pegs) | elevated-historical |
| **Yale-Harvard "The Game"** | 0° + 0.5px hairline (Ivy understatement) | bishop's mitre / mortarboard | Presidents-in-attendance dot field (Bush, Gore, Kennedy as undergrads) | clinical-restraint — "Harvard scored sixteen points in forty-two seconds," spell numbers under twenty |

### `/rivalries/<slug>.html` anatomy (per Tier 1 + Tier 2 = 25 detail pages)

1. **Mythic centered header** — Program A monogram · Trophy glyph 56px · Program B monogram
2. **All-time record ribbon** — full-width W-L-T from each side's perspective + current streak chip
3. **Trophy + countdown panel** — trophy glyph 96px + origin paragraph (LLM-generated once, editor-approved, stored in `data/trophy_lore/<slug>.md`) + countdown
4. **The Era Strip** — Signature 5 from v3, spanning rivalry's full meeting history with anchor moments as `<button>` annotations
5. **The 10 Most Memorable Games** — ordered list, year + score + venue + 60-100 word commentary
6. **Dual fanbase posture panels** — current Reddit + Bluesky heat
7. **"What winning means" stakes footer** — two columns per side, 40-60 words each
8. **Cross-link footer** — program × program team-page links

### The trophy glyph commission

50 SVGs at outline stroke-2, 24×24 viewBox. Tier 1 (8) + Tier 2 (17) commissioned at $50-100 each = ~$2,500. Tier 3 (~25) generated via in-house Claude-grounded SVG prompts. Total budget: $3-4k.

### The five highest-leverage rivalry implementations

| # | Implementation | Days |
|---|---|---|
| 1 | Tier-1 trophy glyph commission (8 SVGs) + per-rivalry seam CSS for existing Rivalry Card | 2-3 |
| 2 | Iron Bowl `/rivalries/iron-bowl.html` as Tier-1 reference implementation | 4-5 |
| 3 | Era Strip with anchor annotations for Tier-1 rivalries | 3-4 |
| 4 | Rivalry-week team-page takeover (hero replacement at T-7d) | 2-3 |
| 5 | Dormant-rivalry treatment + Texas-Texas A&M 2024 return | 2 |

Total: **~13-17 dev-days + $3-4k trophy commissions.**

---

## Part 4 · Per-Conference + Cross-Program Identity

### Per-conference bespoke identity (FBS condensed)

| Conference | Top-rule | Masthead | Motif | Signature module |
|---|---|---|---|---|
| **SEC** | `#C8102E` 6px + `#FFC72C` gold sub-rule 1px | Bowlby 96px on paper-cream; **wool-dark swap weeks 11-14** | 3-bar chevron stack top-left | **The Saban-Tree branching diagram** |
| **Big Ten** | `#0A0A0A` 5px + 2px white sub-rule | Bowlby 88px on **wool-dark default** (only conference with dark default) | Chevron-underscore beneath every section heading | **The Centennial Lineage table** (every Big Ten champion 1896–present) |
| **ACC** | `#013CA6` 3px + `#A2AAAD` silver 1px | Bowlby 80px + Charter italic 36px permanent subtitle "Atlantic Coast — football and the universities that play it" | Navy diamond watermark at 8% opacity behind every headline | **The Football-vs-Basketball axis chart** (each ACC program plotted by football SP+ × basketball KenPom percentile) |
| **Big 12** | `#D14124` (warmer than SEC crimson) 4px, no secondary trim | Bowlby 84px + **rotating subtitle** ("sixteen programs · two time zones · zero clear favorite") | 12-pointed star in gold at 60% opacity + micro-Charter "The star still says 12. The conference has 16." | **The Scoreboard Ticker** (horizontal-scroll every Big 12 game this season with final score in JetBrains Mono 28px) |
| **Pac-12 Remnants** | `#004B85` 2px + `#FFC72C` **dashed** 1px (only dashed treatment) | Bowlby 72px with strikethrough at 60%, subtitle "Oregon State and Washington State, holding the keys" | Two-program-only treatment | **The Diaspora Map** (where the 10 departing programs went) |
| **AAC** | `#5F2C82` 3px | Bowlby 64px | Up-arrow chevron (G5 upward-mobility signal, common across G5) | **The Promotion Track** (every AAC-to-P5 promotion with current watch programs) |
| **Mountain West** | `#00A4A6` 3px | Bowlby 56px | Mountain silhouette rule 240×24 | **The Boise Blue-Turf Marker** (Boise State games get teal underwash) |
| **Sun Belt** | `#FDB827` 3px | Bowlby 56px in `--gold-october` (only conference with masthead in conference color) | Sun-ray burst 32×32 | **The G5-Over-P4 Tracker** |
| **MAC** | `#1F2A44` 2px | Bowlby 48px (smallest masthead — editorial weight differential explicit) | Clock-glyph at 8:00pm position | **The Tuesday Night Scoreboard** |
| **C-USA** | `#1B5E20` 2px | Bowlby 48px | Concentric ring glyph (3 rings, churn) | **The Membership Carousel** (Sankey of every program's tenure) |
| **FBS Independents** | Per-program (ND `#0C2340` 5px / UConn 3px / UMass `#881C1C` 3px) | Per-program | Per-program | **Schedule-Strength-as-Rivalry-Substitute matrix** (ND) + **CIC Trophy 3-way** (service academies) |

### Conference landing page composition (14 modules)

1. Conference top-rule (per above)
2. Conference masthead band (size per tier)
3. Page-context bar with section anchors
4. Pulse v2 fragment (existing — do not rewrite)
5. Standings table with per-program 4px Mood Ribbon segment
6. **Conference SP+ Beeswarm** (v3 Signature #8) — all programs as dots
7. **Conversation share** — horizontal bar per-conference bespoke treatment
8. Per-program record bars
9. **Conference Rivalry Rotation card** (bespoke per conference)
10. **Conference Era Strip** with conference-color annotations
11. **Signature module** per conference (Saban Tree, Centennial Lineage, etc.)
12. **Inter-Conference Matchup Tracker** (10-cell strip)
13. Conference Championship surface link
14. Decal Cluster Footer + Helmet-Stripe Rule

### Cross-program permanent surfaces (5)

1. **`/realignment/`** — 157-year Sankey + movement annotations + "team in 5+ conferences" highlight cards (Tulane, WVU, TCU, USF) + future-realignment speculation tracker + "TV deal as gravity" panel + "geographic coherence index"
2. **`/coaches/carousel/`** — All HC openings 2014-present (~280 entries) + per-coach success-after-hire grade + first-cycle vs second-cycle tracker + coordinator-to-HC pipeline + active in-season tracker (Nov-Jan)
3. **`/recruiting/map/`** — USA state-resolution map showing per-state blue-chip destinations by conference + per-state balance-of-power + transfer-portal geographic flow + per-program recruiting-radius
4. **`/recruiting/all-time-classes/`** — Every signing class 2002-present with outcome score (NFL draft picks + All-Americans + wins-above-replacement) + "panned out / fizzled" editorial commentary
5. **`/nfl-pipeline/`** — Per-program pipeline strength index (5-year rolling) + per-position pipeline depth + per-conference total NFL talent + "first-round pipeline" active streak tracker

### G5/Independent/FCS treatment matrices

- **G5-vs-P4 narrative thread** at `/g5-p4/` — G5 wins over P4 tracker (App State 2007, James Madison 2010, Liberty 2020, Jackson State 2021) + G5-to-P4 transfer Sankey + G5 ceiling tracker (Memphis, USF, App State, JMU, Tulane) + P4 floor tracker (Vandy, Stanford flagged)
- **Independent programs:** Notre Dame full P4 + Schedule-Strength-as-Rivalry-Substitute matrix; Service Academies (Army/Navy/Air Force) get CIC Trophy 3-way display + military-tradition overlay; UConn/UMass get rebuild-narrative + transfer-portal-dependence chart
- **FCS treatment** at `/fcs/` — 24-team championship bracket + FCS-upset-of-P4 tracker + FCS-to-FBS transition tracker + 13 conference cards + historical All-American tracker
- **DII/DIII/NAIA respect treatment** at `/small-college/` — condensed per-level landings + Mount Union dynasty card + small-school NFL pipeline callout (Pavia journey)
- **Celebration Bowl** (HBCU national championship) gets dedicated permanent surface `/championship/celebration-bowl-<year>.html` with same editorial weight as P4 championship

---

## Part 5 · Per-Season-Phase + Weekly-Cadence + Hour-by-Hour-Saturday

### The Phase Atlas (10 phases × 9 design variants — condensed)

| Phase | Window | Hero / Cover essay | Pulse mode | Heisman mode | Reactions σ |
|---|---|---|---|---|---|
| **spring-and-portal** | Mid-Feb 18 → Apr 30 | "The Transfer Wire" | Archive-comparative | Offseason retrospective | 1.2σ (lowered — rare events) |
| **nsd-and-portal** | Feb 1 → Feb 17 | "The Class Reveal" | Recruiting-victory | Two-year-projection | 1.5σ standard |
| **dead-period-heritage** | May 1 → Jul 13 | "The Heritage Window" | Archive-mode | All-Time Bracket voting | Disabled (3.0σ) |
| **media-days** | Jul 14 → Jul 31 | "Media Days Live" | Quote-driven (PodiumPulse) | Preseason-prediction | 1.6σ |
| **camp** | Aug 1 → Aug 27 | "The Camp Tracker" | Camp-tea (UNVERIFIED tier) | Preseason sharpening | 1.3σ (camp tinderbox) |
| **early-season** | Aug 28 → Sep 27 (Weeks 0-4) | "Season Theater" | Standard live | In-season ranking | 1.4σ |
| **stakes-rising** | Sep 28 → Nov 14 (Weeks 5-11) | "Stakes Rising" | Polarization-tracking | Mid-season sharpened | 1.5σ |
| **rivalry-peak** | Nov 15 → Nov 29 | **Rivalry takeover** per Tier-1 | Dual-team rivalry-heat ribbon | Pre-ceremony | 1.8σ (everyone polarized) |
| **cfp-selection-and-bowl** | Nov 30 → Dec 13 | "Selection Sunday Live" (Dec 7) → "The Bowl Index" | Committee-reaction → Bowl-anticipation | Heisman-week ceremony | 1.5σ |
| **bowl-and-carousel** | Dec 14 → Jan 19 | "The Bowl Index" → "The Title Run" (Jan 6-19) | Bowl-result + carousel-shock | Post-ceremony retrospective | 1.4σ |

### Weekly cadence matrix (Mon-Sun, in-season)

| Day | Hero | Daily H1 |
|---|---|---|
| **Mon** | Weekend-recap multi-game grid | "What Saturday rearranged" |
| **Tue** | Depth-chart-shift hero | "Tuesday: who's hurt, who moved" |
| **Wed** | Model-recompute hero | "The numbers settle" |
| **Thu** | Thursday-night-game preview | "The week begins early" |
| **Fri** | Weekend-preview slate grid | "The slate" |
| **Sat** | **Gameday-live state machine** (see below) | "Live: Saturday" |
| **Sun** | Cover-essay (autopsy mode) | "After the bracket" |

### Hour-by-hour Saturday gameday state machine (ET)

| Hour | Hero state | Dominant module | Suppressed |
|---|---|---|---|
| 6am-11am | Pre-day briefing | TodaySlateGrid sorted by kickoff | Wire, Editions |
| 11am-noon | Early-kicks tracker | EarlyKicksLive + MoodRibbon spinning-up | Heisman, CFP |
| noon-3:30pm | Noon-game live | MultiGameTracker-noon | All editorial |
| 3:30pm-7pm | Afternoon-premier tracker | PremierMatchupHero | All editorial |
| 7pm-11pm | Primetime tracker | PrimetimeMatchupHero | All editorial |
| 11pm-2am | Late-night Pac-time tracker | WestCoastLateHero | All editorial |
| 2am-6am | Sleep-mode | OvernightQueue (mood-ribbon updates queue for Sunday) | All active modules |

### The 10 phase-specific surfaces

1. **The Portal Wire** (Apr 16-30 + Dec 9-Jan 20) — origin→destination Sankey + position-waterline charts + per-program net-gain/loss + "who flipped recently" feed
2. **The Spring Game Hub** (Apr 11-26) — per-program spring-game results, depth-chart-after, position-battle outcomes, "spring takeaway" 80-word paragraph
3. **Media Days Live** (Jul 14-31) — conference-day grid, per-program podium-clip cards, headline tracker, media-day-narrative arc
4. **The Camp Tracker** (Aug 1-27) — position-battle bracket trees, depth-chart projection ribbon, "fall-camp tea" (UNVERIFIED), per-program scrimmage box score
5. **Selection Sunday Live** (Dec 7, 2026) — pre-broadcast model rank vs expected committee, live ticker, post-broadcast Receipt Strips
6. **The Bowl Season Index** (Dec 14 → Jan 5) — all 41 bowls chronologically, per-bowl SavantCard side-by-side, prediction-market consensus, "sleeper-bowl" surfacing
7. **The Coaching Carousel Tracker** (Nov 1 → Jan 31) — openings list with timeline, candidates board with fit grade, hire-announcement cards, carousel-effect rail
8. **The Heritage Window** (May 1 → Jul 13) — On This Day, year-over-year mood ribbon, era anniversaries, All-Time tournament brackets
9. **The Bowl Sunday Cover Essay** (Dec 7) — once-a-year 2,500-word essay on NY6 matchups
10. **The NSD Tracker** (Feb 4, 2026) — live class-composition feed, per-state battle outcomes, per-position class strength, "who flipped" ribbon

### 2026-27 editorial calendar (key dates)

| Date | Day | Phase / Surface firing |
|---|---|---|
| Feb 4, 2026 | Wed | **NSD Tracker** hero (full day) |
| Apr 18, 2026 | Sat | **Spring Game Hub** hero (27 spring games) |
| May 1 | Fri | dead-period transition; HeritageWindow lights up; PortalWire archives |
| Jul 14-17 | T-F | **SEC Media Days Live** (Atlanta) |
| Jul 21-23 | T-Th | **ACC Media Days Live** (Charlotte) |
| Jul 22-23 | W-Th | **Big Ten Media Days Live** (Vegas) |
| Aug 4 | Tue | **Camp Tracker** lights up; days-to-kickoff = 26 |
| Aug 29 | Sat | First Gameday-Saturday hour-by-hour state machine (Week 0) |
| Aug 30 | Sun | Week 0 cover essay "The Opening Act" (Vol. I No. 52) |
| Sep 28 | Mon | stakes-rising transition; CFPProjection promotes to hero |
| Nov 15 | Sun | rivalry-peak transition; rivalry-week takeover |
| Nov 22-29 | Sa-Su | **Rivalry Peak Week** — Iron Bowl Sat Nov 28 |
| Dec 7 | Sun | **Selection Sunday Live** full-day takeover + Bowl Sunday cover essay |
| Dec 13 | Sat | Heisman Ceremony Saturday |
| Dec 14 | Mon | **Bowl Season Index** hero |
| Dec 31 - Jan 1 | W-Th | New Year's Six peak |
| Jan 19, 2027 | Mon | **National Championship Monday** — "The Coronation" Vol. II No. 17 |
| Feb 3, 2027 | Wed | **NSD 2027** cycle resets |

### Implementation as declarative config

```python
PHASE_COMPOSITION[phase][weekday] = ordered list of (module_key, render_callable, mode_kwargs)
PHASE_WIRE_TAXONOMY[phase] = ordered list of tag keys
PHASE_PULSE_MODE[phase] = one of {'live', 'archive-comparative', 'archive-only',
  'recruiting-victory', 'quote-driven', 'camp-tea', 'polarization-tracking',
  'dual-team-rivalry', 'committee-reaction', 'bowl-anticipation', 'bowl-result+carousel'}
PHASE_DAILY_TEMPLATE[phase][weekday] = template id
PHASE_HEISMAN_MODE[phase] = one of {'retrospective', 'two-year-projection', 'all-time-bracket',
  'preseason', 'in-season', 'mid-season-sharpened', 'pre-ceremony', 'ceremony', 'post-ceremony'}
PHASE_REACTIONS_SIGMA[phase] = float
PHASE_STORYLINES_ACTIVE[phase] = list of storyline ids
```

~600 lines of declarative config plus the 10 phase-specific surface modules. The state-resolver already runs once per page-build in `state_resolver.py`; v5 reads its `season_phase` output and the calendar date and dispatches the right composition.

---

## Part 6 · Data-Source → Named-Editorial-Surface Map

Every source becomes a recognizable named module. No source remains invisible. The site's identity = its source diversity made legible.

### The Master Source-Surface Map (16 sources)

| Source | Named Surface | Viz Pattern | Ships On | Voice Cite |
|---|---|---|---|---|
| CFBD Tier 2 | **The Numbers Lane** + **Win-Prob Ribbon** + **Returning-Production Board** | MetricAtom + WinProbabilityRibbon + ProductionStackedBar | Every team page, every game page, `/numbers/` | "via CFBD · adv. metrics · week N" |
| Arctic Shift Reddit | **The Time Machine** (see Part 7) | HistoricalDepthGauge + VocabularyDriftChart + ThreadVolumeHistogram | Every team page History tab, every game page footer, `/timemachine/` | "via r/<team> archive · since 2013" |
| Bluesky firehose | **The Bluesky Wire** | VelocityTicker + CohortSplitBar | Game day live, every team page footer, `/wire/` | "via Bluesky · #CFB feed · last 6h" |
| Wikipedia | **The Pageview Spike** + **The Edit-War Watch** | SpikeComb + EditActivityHeatmap | Team page Pulse, player page header, `/spikes/` | "via Wikipedia · 7-day pageview delta" |
| Campus newspapers RSS | **The Campus Wire** | EarlyWarningTimeline + BylinedQuoteBlock | Team page top-of-fold when active, `/campus/` | "via The Crimson White · 2026-05-15" |
| School athletics RSS | **The Front-Page Edit** | OfficialStatementCard + TimestampedBulletin | Team page News Lane, game page pre/post | "via rolltide.com · official athletics release" |
| Locked On podcasts | **The Pod Tape** | PodEpisodeStrip + QuoteExtractCard | Team page Voices tab, `/pods/` | "via Locked On <Team> · ep. <date>" |
| Beat-writer Substack | **The Beat** | BeatWriterCard + ExcerptWithPaywallBadge | Team page Voices tab, `/beat/` | "via <Writer Name> · <Substack>" |
| GDELT | **The News Volume Gauge** | NewsVolumeBar + OutletDiversityChip | Team page Pulse footer, `/signal/` | "via GDELT · global news index · 24h" |
| SeatGeek | **The Box-Office Tell** (contrarian moat — see below) | BoxOfficeTell + DemandVsNarrativeDivergence | Every game page, team page Demand strip, `/boxoffice/` weekly | "via SeatGeek · resale median · T-7" |
| Spotify charts | **The Regional Cultural Callout** | RegionalCulturalCallout + MetroChartSparkline | Team page culture footer, `/culture/` | "via Spotify Charts · <metro> · week of <date>" |
| Prediction markets | **The Money Line vs The Crowd** | MarketProbabilityRibbon + MarketVsModelDiff | Every game page, `/markets/` | "via Polymarket · contract <id> · last trade" |
| YouTube | **The Recap Tape** | VideoEngagementStrip + RecapSentimentBar | Team page Voices tab, game page post-game | "via YouTube · <channel> · 24h" |
| Google News | **The Headline Drift** | HeadlineLagDiff + OutletStackedBar | `/signal/` daily, paired with Campus Wire | "via Google News · query <slug> · 24h" |
| Wiki Awards | **The Trophy Case** + **Accolade Lens** | AccoladeLens + HonorRollTimeline | Player page header, team page honors tab, `/trophies/` | "via Wikipedia Awards · <year>" |
| CFBD Live Game | **The Live Lane** | LivePlayFeed + MomentumVector + WinProbabilityRibbon | Live game page only | "via CFBD Live · drive <n> · <quarter>" |

### Five signature combinations

1. **The Two-Source Verification** (Beat-writer Substack + Campus newspaper RSS) — when same claim appears within 24h, auto-promote to "Two-Source" card with both bylines side-by-side
2. **The Box-Office Contradicts The Boards** (SeatGeek + Reddit + Bluesky) — triggered when Reddit + Bluesky volume z-score ≥ +1.0 AND SeatGeek resale z-score ≤ -0.5
3. **The Regional Interest Spike** (Wikipedia + Spotify regional + Google News flat) — leading-indicator before-it-breaks claim
4. **The Wire Moved Before The Line** (Bluesky analytics-cohort + Prediction markets) — sharp-Twitter-to-sharp-money pipeline made visible
5. **The Archive Comp** (Arctic Shift + CFBD Tier 2) — historical pattern match by both metric signature and Reddit thread tone

### The Box-Office Tell — the contrarian-signal moat in detail

**Why this is the brand's most defensible product surface.** SeatGeek + Reddit fusion isn't novel as a technical idea. But **naming the divergence, archiving every instance, scoring the model's accuracy week-over-week** — that's a recurring editorial product no one else maintains.

**Four recurring categories** (the module *names* the category — vocabulary becomes editorial currency):

1. **Loud-and-cold** (boards hot, tickets flat) — the "boards-are-wrong" call
2. **Quiet-and-hot** (boards flat, tickets surging) — the "locals know" call
3. **Aligned-conviction** (both hot) — the "this game matters" call
4. **Aligned-apathy** (both flat) — the "skip this one" call

**Add a tracked accuracy line:** "Box-Office Tell hit rate last 12 weeks: 9/12 (75%)." The score itself becomes a credibility lever.

### 5-ship implementation order

| # | Surface | Weeks | Why first |
|---|---|---|---|
| 1 | **The Time Machine** (Arctic Shift) | 2 | Highest moat, lowest competitor-replication risk |
| 2 | **The Box-Office Tell** | 3 | Single most "doing something different" surface |
| 3 | **The Campus Wire + Headline Drift** | 1 | Demonstrably true leading-indicator weekly |
| 4 | **The Bluesky Wire with cohort identification** | 3 | The cohort tagging is the differentiator |
| 5 | **The Numbers Lane + Money Line vs Crowd** | 2 | Analytics-meets-markets pairing |

Total: 5 named surfaces in ~11 engineering weeks.

---

## Part 7 · The Arctic Shift Reddit Archive Moat

**Provenance verified:** Arctic Shift hosts compressed JSONL of ~2.5B Reddit posts + comments. r/CFB era 2013→present is continuous. **The #1 all-time r/CFB postgame thread is verified as Vandy-beats-Alabama 2024 at 39,232 upvotes** (Niche Prowler scrape); #2 is Tennessee-beats-Alabama 2022 at 36,418. The Vandy thread's top comment (4,891 upvotes, posted 11:48 PM CT Nov 23 2024, 14 minutes after Pavia's third-down conversion): *"Beat Bama. National signing day comes early in Nashville."*

### 12 bespoke surfaces only the 13-year archive enables

| # | Surface | Algorithm summary | Ships on |
|---|---|---|---|
| 1 | **"Highest June Since 2014" Callouts** | `SELECT MAX(monthly_mood_index) WHERE MONTH=? GROUP BY year`; trigger if rank-1 within ≥4yr or rank-2 within ≥6yr | Pulse footer every team page, Daily, Editions support |
| 2 | **The Game-Week Volume Index (GWVI)** | `volume = post_score_sum + comment_count + 0.5 × distinct_authors`; rank descending per (program, season) + per (program, all-time) | Pulse 24h pre-kickoff, Reactions 90min post, cover essay |
| 3 | **The Vocabulary Drift Chart** | Per month, per term, per subreddit: `(matches / total_comments) × 10000`; smooth with 3-month rolling median; annotate inflections | `/programs/<slug>/discourse-history/`, methodology |
| 4 | **The Before-and-After Archive Pivot** | For registered `pivot_event` row, compute before = [event-30d, event), after = [event, event+30d]; 4-panel mini-grid per side | `/programs/<slug>/discourse-history/`, Storyline pages |
| 5 | **The Historical Comp Engine** (echo cards) | Feature vector `[mood_score, divergence, top20_term_vector, volume_zscore, rivalry_temp]`; cosine ≥0.78 over ≥6 weeks AND mean(cosine) ≥0.72; top-K=5 to `chronicle_moments_pending` | Chronicle "echo" cards, Edition essays |
| 6 | **The Forgotten Saturday Resurfacing** | When today's matchup matches archived game (same programs, ≥3yr ago), pull highest-scoring comment between final-whistle and next morning; `score ≥100 AND length BETWEEN 40 AND 280` | Cover essay support, pre-game preview |
| 7 | **Top-Comment-of-the-Decade per Program** | `SELECT * FROM archive_comments WHERE subreddit IN ? ORDER BY score DESC LIMIT 5`; editor selects one | `/programs/<slug>/discourse-history/` hero, rivalry week |
| 8 | **The Vocabulary Lineage Map** | Hand-seed canonical phrases per profile; regex against archive with edit-distance ≤3; record first appearance, peak month, variant trees | Long-form Connections features |
| 9 | **The Cross-Era Fan Cohort Analysis** | Cohort weight matrix applied retroactively over full 2013-now archive; per-year per-cohort sentiment | Once-per-year Q4 special Edition |
| 10 | **The Player Name Velocity Tracker (NVI)** | `mention_count_in_program_subreddits / (program_total_comments / 1000)`; NVI = ratio / baseline; threshold ≥2.0 for ≥3 consecutive weeks | Heisman board sidebar, player canon entry sidebar, watch-list |
| 11 | **The Recurring Mood-Cycle Detection** | Per (program, calendar-month, year): mean mood index; render as 12-point line per year; "fingerprint stability score" | `/programs/<slug>/discourse-history/`, once-per-season feature |
| 12 | **Archive-Triggered Editorial Hooks** | 4 triggers: MOOD_ZSCORE_2SIGMA, PLAYER_REAPPEARANCE, PHRASE_VELOCITY_5X, THREAD_VOLUME_TOP1_PROGRAM | Wire row generator path, Pulse deltas, Daily leads |

### The `/archive/` Atlas landing page

6-section permanent surface: Hero (top-5 highest-upvoted r/CFB threads ever) · 13-year volume timeline · Top Threads ladder · Vocabulary Then-and-Now · Per-program 17-tile grid · Methodology link.

### The Reddit-archive-powered editorial calendar (quarterly)

| Quarter | Issue | Anchor surfaces |
|---|---|---|
| Q1 | "The Year We Picked Sides Again" (NSD + portal) | Surface 3 (vocab drift) + Surface 4 (one major pivot) + Surface 10 (NVI climbers) |
| Q2 | "Quiet Spring" (May-July reflection) | Surface 1 (highest-month callouts) + Surface 11 (mood fingerprints) |
| Q3 | "The Loud Camp" (media days + Week 1) | Surface 7 (top comments resurfaced) + Surface 12 (trigger fires) |
| Q4 | "Rivalry Season + the Carousel" | Surface 4 (multiple pivots) + Surface 5 (echo card) + Surface 9 (annual cohort shift) |

### Pre-2013 deep-history sourcing

| Era | Source | Cost |
|---|---|---|
| 1869-1965 | **Library of Congress Chronicling America** (public-domain newspapers) | $0 |
| 1869-2012 | **Sports-Reference / CFB Reference** | $0 (already ingested) |
| 1880-2012 | **Newspapers.com** | $20/mo |
| 1990-2012 | **ProQuest Historical Newspapers** (university library auth) | $0 |
| 1880-now | **University digital archives** (per-school) | $0 |
| 1925-now | **Sports Illustrated Vault** (cite-only) | $0 |

**Editorial rule:** Deep history doesn't get echo cards or vocab-drift charts. It gets `retroactive` Chronicle moments anchored to a specific dated artifact + Library-of-Congress credit. The Era Strip does visual lift for pre-2013.

### 5 highest-leverage archive surfaces (~18 eng-days total)

1. Surface 7 (Top-Comment-of-Decade per Program) — 1 day for 17 programs
2. Surface 2 (Game-Week Volume Index) — 3 days
3. Surface 1 (Highest-[Month]-Since-[Year] callouts) — 2 days
4. Surface 12 (Archive-Triggered Editorial Hooks) — 4 days (foundation for 2/6/10 self-running)
5. Surface 5 (Historical Comp Engine / Echo Cards) — 8 days

---

## Part 8 · The Zero-Touch Automation Architecture (the spine)

**Premise.** Kevin does not open the app to "ship something." Saturday 06:00 ET an Edition publishes. Monday 06:00 ET the Daily ships. Sunday 09:00 ET nightly enrichment refreshes 17 team pages. The loop continues without him.

### 8.1 Existing workflow inventory (15 YAMLs, verified in repo)

| # | Workflow | Trigger | Calendar (ET) | Auto-publishes? |
|---|---|---|---|---|
| 1 | `publish_site.yml` | cron `0 11 * * 1` + dispatch | Mon 06:00 ET | Yes — pushes `published` branch |
| 2 | `ingest_hourly.yml` | cron `7 * * * *` + dispatch | Every hour at :07 UTC | No (DB-only) |
| 3 | `ingest_daily.yml` | cron `0 9 * * *` + dispatch | Daily 05:00 ET | No (DB-only) |
| 4 | `ingest_weekly.yml` | cron `0 6 * * 1` + dispatch | Mon 02:00 ET | No (uploads but no push) |
| 5 | `fanintel_gameday_live.yml` | cron Sat-Sun + dispatch | Sat 12:00 → Sun 02:00 ET, per-minute | Yes for live-game team pages |
| 6 | `the-daily-06am-et.yml` | cron `0 10 * * 1-5` + dispatch | Mon-Fri 06:00 ET | Yes — `vercel deploy --prod` |
| 7 | `wire-daily-04am-et.yml` | cron `0 9 * * *` + dispatch | Daily 05:00 ET | Yes — `vercel deploy --prod` |
| 8 | `mailbag-friday-09am-et.yml` | cron `0 13 * * 5` + dispatch | Fri 09:00 ET | Yes — `vercel deploy --prod` |
| 9 | `publish-edition-weekly.yml` | cron `0 10 * * 6` + dispatch | Sat 06:00 ET | **NO — structural seam** (uploads artifact but no Vercel deploy) |
| 10 | `scrape_health.yml` | cron `30 11 * * *` + dispatch | Daily 07:30 ET | No (telemetry) |
| 11 | `deep_research_monthly.yml` | cron `0 14 1 * *` + dispatch | 1st of month 09:00 ET | No (opens GH issue — human-gated) |
| 12 | `world_class_enrich.yml` | **dispatch only** | Manual (2-4hr) | Yes when run |
| 13 | `compute_full_pass.yml` | **dispatch only** | Manual (30-60min) | Yes (dispatches publish-site) |
| 14 | `backfill_2025_season.yml` | **dispatch only** | Manual (90min) | No (DB-only) |
| 15 | `backfill_full_history.yml` | **dispatch only** | Manual (3-6hr) | Yes (dispatches publish-site at end) |

### 8.2 Five structural seams identified

1. **`publish-edition-weekly.yml` is decoupled from deploy.** Uploads `cfb-edition-${slug}` artifact but never enters `site-deploy` concurrency group and never invokes Vercel. **P0 fix in Sprint v5-2.**
2. **Two deploy paths for one artifact.** `publish_site.yml` + `world_class_enrich.yml` push `published` branch; Daily/Wire/Mailbag use `vercel deploy --prod` directly. The 5000-file `site_check` gate is the band-aid for the 478KB-poison incident.
3. **`world_class_enrich.yml` is dispatch-only.** Owns `generate-narratives`, `generate-chronicle`, `generate-canon-list`, `scrape-wiki-awards`, `seed-retro-all`, `compute-player-season-mood`, `reactions-check-triggers --auto`, `refresh-savant` / `refresh-season-arc` / `refresh-rivalry`. **All of these need cron.** Fix: convert to Sun 14:00 UTC cron + split into nightly + weekly subsets.
4. **`compute_full_pass.yml` is dispatch-only.** Owns Heisman per-season, dynasty heatmap, NFL pipeline, the Room, signature stories, vibe shifts, conference pulse, historical seasons, receipts, best calls. **All need cron.** Fix: monthly cron `0 14 1 * *`.
5. **No `canon-monthly.yml` / `audit-on-pr.yml` / `visual-regression.yml` / `lighthouse-ci.yml` exist** (v4 §6.4 + §6.6 specified them).

### 8.3 The manual-trigger audit (12 gates → 12 automation paths)

| # | Manual gate | Where it lives | Automation path |
|---|---|---|---|
| 1 | Edition cover essay | `editions/seeds.py:_W17_COVER_ESSAY` is hand-written Python string. `publish-edition --slug XX` returns `"no seed payload for XX; skipping"` and exits 0. | New `manage.py generate-edition --slug $SLUG`: theme-resolver picks viz, Opus 4.7 writes essay against `_VOICE_CONTRACT_EXCERPT`, voice_validator gates, writes to new `editions_authored` table. `publish-edition` reads `editions_authored` first, falls back to `seeds.py`. |
| 2 | Storyline chapter publish | `chapter_authoring.py:write_draft_scaffold` writes to `seeds/_drafts/` on voice fail. No poller. | New `manage.py publish-thread-chapter-from-drafts`: scan `_drafts/`, retry with rewrite-guidance; auto-merge if `confidence_after_retry ≥ 0.85`; archive rejects. Run in nightly enrich. |
| 3 | Chronicle moments approval | v4 spec says manual `approved_at`; code at `chronicle_generator.persist()` sets `is_published=1` without gate. | Add `team_chronicle_observations.approval_state` column. Auto-approve when `confidence ≥ 0.85 AND validation_notes IS NULL AND surprise_score ≥ 0.6`; auto-reject < 0.7; queue 0.7-0.85. |
| 4 | Mailbag question source | `seed_representative_submissions(n)` synthesizes when < 3 queued. Mailbag currently bootstrap-seeded synthetic questions. | New `manage.py mailbag-mine-questions --window 7d`: scan r/CFB, Bluesky cfb feed, beat-writer Substacks for question-shaped posts; Haiku scores; auto-insert top 8 into `mailbag_submissions`. Add to daily ingest. |
| 5 | Edition slug → seed binding | `editions/cli.py:_cmd_publish_edition` early-exits when `seeds.py` has no payload. | Replace `seeds.py` payloads with table-driven `editions_authored`. Auto-degrade to "no live signal" mode, never no-op. |
| 6 | Editor approval of best-calls / receipts | `generate-best-calls --year 2025 --n 25` has no approval gate. | Add receipts to voice_validator chain; reject banned phrases. |
| 7 | Deep Research monthly refresh | `deep_research_monthly.yml` opens GitHub issue; Kevin runs Deep Research manually. | New `manage.py deep-research-auto`: invokes Claude Research API; auto-applies YAML patch; gates through `validate-feed-urls`. |
| 8 | Backfill resume after failure | If `backfill_full_history.yml` fails mid-Phase-5 (2-3hr in), re-dispatch re-runs Phases 1-4 unnecessarily. | New `backfill_progress` table: `(phase_name, season_year, completed_at_utc, run_id)`. Each phase writes on success. Resume reads `WHERE completed_at_utc IS NULL`. |
| 9 | Heisman model per-season run | `compute_full_pass.yml` loops `seq 2014 2025`. Dispatch-only. | Add weekly cron for current season only Mon 06:00 UTC. Historical loop moves to one-time `compute_one_time_seed.yml`. |
| 10 | Cover-essay theme selection | `editions/theme_resolver.py` is week-of-year dict lookup; no live signal. | Replace `resolve_theme(slug)` with function reading cohort divergence + storyline activity + Wire velocity-spike entities. |
| 11 | Local Windows Task Scheduler | `scripts/register_*_task.ps1` registers laptop crons. Bypass GitHub Actions. | **Delete.** All have GitHub Actions equivalents. Local-machine dependency is antithesis of zero-touch. |
| 12 | `publish_site.ps1` local trigger | Used for manual on-demand publish. | Retain as debug tool; remove from documented "how to publish." GitHub-Actions path is the deploy path. |

### 8.4 The LLM model-routing matrix (with cost ceilings)

| Surface | Model | Prompt template | Validation | Retry | Failure fallback | Weekly $ |
|---|---|---|---|---|---|---|
| Edition cover essay (1×/wk) | **Opus 4.7** | `prompts/edition_cover_essay.md` | voice + headline-quality + ≥6 named entities + 900-1200 words | 1 retry Opus, then 1 Sonnet | `editions_drafts._failed/` + last-week-restyled | $5 |
| Edition feature blocks (5×/wk) | Sonnet 4.6 | `prompts/edition_feature_<kind>.md` (5 templates) | voice + ≥2 named entities | 1 retry | drop feature, fill from top-Wire | $2 |
| Daily takes (15/wk) | Sonnet default, Opus tentpole | `prompts/daily_take.md` | voice | 1 retry | suppress, elevate next selector | $10 |
| Wire `why_it_matters` (~420/wk) | Sonnet | `prompts/wire_why_it_matters.md` | voice + ≤25 words | 1 retry | factual restatement | $15 |
| Reactions (~3-5/wk) | Sonnet, Opus surprise≥90+blue-blood | `prompts/reaction_story.md` | voice + ≥3 cohort refs | 1 retry | offline stub | $3 |
| Mailbag answers (3-5/wk Fri) | Sonnet, Opus civic | `prompts/mailbag_answer.md` | voice + 250-400 words + ≥3 sources + ends "Short answer:" | 1 retry | publish-with-flag | $5 |
| Chronicle cards (~595/wk) | Sonnet, Opus blue-blood top-1 | `prompts/chronicle_card.md` | voice + scaffolded-copy regex + ≥1 entity | 1 retry | drop, log dropout-rate | $30 |
| Storyline chapters (~2-3/wk) | Sonnet | `prompts/thread_chapter.md` | voice + JSON-fence parseable + ≥3 entities | 2 retries | `_drafts/` (poller in enrich) | $4 |
| Heisman weekly narrative (1×/wk) | Opus | `prompts/heisman_weekly.md` | voice + cites top-10 movement + continuity | 1 retry | publish without narrative | $3 |
| Canon entry prose (~100/list monthly) | Sonnet (11-100), Opus (top-10) | `prompts/canon_entry_<tier>.md` | voice + 400-800 words + ≥4 entities | 1 retry | drop, preserve prior | $5/mo |
| Pulse state-of-team (17 daily) | Haiku verify, Sonnet write | `prompts/pulse_state_of_team.md` | voice + Awaiting Signal fallback | 0 retries (Haiku) | Awaiting Signal card | $8 |

**Total weekly ceiling: $85/wk = $4,420/yr. Auto-throttle at $120/wk** (40% headroom) — degrade Opus→Sonnet→Haiku→regex fallback.

### 8.5 The imagery auto-pipeline

| Surface | Tool | Cron | Validation |
|---|---|---|---|
| Logos (134 FBS, 250 FCS) | `sync-team-brand-assets` (exists) | Monthly first Sunday | File-size > 5KB, transparent PNG |
| Helmets (top 50) | New `scripts/imagery/render_helmets.py` Blender 4.x headless in GH Actions | One-time + on-demand | Pixel-diff vs reference ≥ 95% |
| Stadiums (top 100) | New `scripts/imagery/fetch_stadium_photos.py` Wikimedia API | Monthly first Sunday | License against CC-BY allowlist |
| Coach portraits (134 FBS) | New `scripts/imagery/fetch_coach_portraits.py` Wikimedia + school RSS | Monthly first Sunday | License + face-detection single-face crop |
| Editorial illustration | **Black Forest Labs FLUX.1 [pro] API** ($0.05/image, 8s gen — replaces Midjourney for true API automation) | On-demand per surface | CLIP cosine ≥0.7 vs reference cluster |
| OG cards | New `src/cfb_rankings/share_cards/` Pillow templates (v4 §5.3) | `publish_site.yml` post-process | File-size >8KB, dimensions 1200×630 |

**FLUX over Midjourney rationale:** Midjourney is Discord-only, requires human prompt entry. FLUX has true API. House-style enforcement via LoRA fine-tuned on first 30 approved outputs (BFL hosts custom LoRAs at $0.001/image inference markup).

### 8.6 The Kevin Zero-Touch UI

**Weekly Digest Email (Fri 17:00 ET).** New `digest_weekly.yml` cron `0 21 * * 5`. Renders HTML email summarizing next 36h:
- Mailbag (Friday 09:00 already shipped 4h ago): 4 question summaries + one-click reject link per answer
- Wire (Saturday 04:00): Top 10 expected entries with preview
- Edition cover (Saturday 06:00): Theme + essay first 200 words + cover_viz_kind + "Reject Cover" link
- Edition features (Saturday 06:00): 5 feature kind + headline + one-click reject
- Sunday Heisman update + Monday Daily preview

Each item has `?reject=$signed_token` link. Click rejects → writes to `editorial_overrides` table → publishing cron reads + substitutes fallback. Resend API; ~$0.001/email × 4/wk = trivial.

**`/admin/queue/` Page** (auth-walled via Vercel rewrite + `X-Cfb-Admin-Token`):
- Real-time generation queue (last 100 rows from `llm_usage_log`)
- `editions_authored` pending row for next Saturday — per-feature reject button
- `team_chronicle_observations` queue_low_confidence rows — per-card approve/reject/"regenerate with Opus"
- Storyline drafts — per-draft approve/reject
- Per-surface quality-gate sliders writing to `quality_gates` table

**The Panic Button.** `/admin/panic` writes to `system_state` table key=`publish_paused`. Every site-deploy workflow reads at start; exits 0 if paused.

**Failure-Mode Notifications.** New `notify_failure.yml` reusable workflow. Every cron includes final `if: failure()` step calling it. Email via Resend with workflow name + error + run URL + rolling-artifact state.

**Per-surface quality gates (`quality_gates` table):**

| gate_key | default | semantics |
|---|---|---|
| `chronicle_min_confidence_auto_approve` | 0.85 | auto-approve threshold |
| `chronicle_min_confidence_queue` | 0.7 | queue-for-review threshold |
| `wire_voice_validator_strict` | 0 | when 1, second-failure publishes nothing |
| `daily_take_count` | 3 | takes per edition |
| `mailbag_max_questions` | 5 | per edition |
| `reactions_velocity_floor` | 75 | gate for power-program-trigger |
| `llm_weekly_spend_ceiling_usd` | 120 | auto-throttle trigger |
| `image_clip_similarity_floor` | 0.7 | auto-reject editorial illustration |

Sliders write; synthesizers read. No code redeploys needed.

---

## Part 9 · The v5 Implementation Roadmap

10 sprints (~14 dev-weeks) grounded in real file paths and verification gates.

### Sprint v5-1 (Week 1) — Automation foundation

- Create `prompts/` directory with 11 templates per Part 8.4 matrix
- Add `prompt_versions` table (migration `0042_prompt_versions.sql`)
- Refactor `llm_runtime.py` to accept `prompt_template_path`, log `template_path + version_hash` to JSONL
- Add `quality_gates` table (migration), seed initial rows
- **Convert `world_class_enrich.yml` to cron** `0 14 * * 0` (Sun 09:00 ET). Keep `workflow_dispatch` for manual reruns
- **Convert `compute_full_pass.yml` to monthly cron** `0 14 1 * *`. Move historical loops to one-time `compute_one_time_seed.yml`
- Add `backfill_progress` table + resume logic in `backfill-cfbd-history`, `backfill-player-context`, `backfill-game-player-stats`, `backfill-offseason-conversation`
- **Verification:** Run `world_class_enrich.yml` via dispatch; confirm next Sunday cron also fires; confirm `prompt_versions` has 11 rows

### Sprint v5-2 (Week 2) — Editorial auto-generation

- Author `prompts/edition_cover_essay.md` + `prompts/edition_feature_<kind>.md` ×5
- Add `editions_authored` table
- Refactor `editions/cli.py:_cmd_publish_edition` to read `editions_authored` first, fall back to `seeds.py`
- New `manage.py generate-edition --slug $S`. Wire into `publish-edition-weekly.yml` as pre-publish step at `0 8 * * 6` (Sat 04:00 ET, 2h before publish)
- **Move `publish-edition-weekly.yml` into `site-deploy` concurrency group + add Vercel deploy at end** (P0 structural seam fix)
- Replace `wire/editorial.py:_factual_restatement` with Sonnet `prompts/wire_why_it_matters.md` call, cache by action-hash
- **Verification:** Saturday after merge, observe edition publish without seeds.py PR. Verify `editions_authored` has row. Verify Vercel deploy at 06:00 ET

### Sprint v5-3 (Week 3) — Reaction + storyline auto-promotion

- Move `reactions-check-triggers --hours 1 --auto` into `wire-daily-04am-et.yml` after `wire-generate-editorial`
- Add second invocation `--hours 8 --auto` in `fanintel_gameday_live.yml` at window end
- New `manage.py auto-promote-storyline-drafts` — scans `seeds/_drafts/`, retries voice validator with rewrite-guidance, promotes if `confidence_after_retry ≥ 0.85` AND no banned phrases AND ≥3 named entities
- Add to new `enrich_nightly.yml` cron `0 14 * * *` (daily 09:00 ET)
- **Verification:** Trigger Wire entry with velocity ≥90 (manual SQL UPDATE); confirm Reaction story renders next morning

### Sprint v5-4 (Week 4) — Mailbag mining + Chronicle approval gate

- New `manage.py mailbag-mine-questions --window 7d`. Reddit + Bluesky + Substack scraper writes to `mailbag_submissions` with `source_kind='mined'`
- Add to `ingest_daily.yml` after `build-conversation-features`
- Add `team_chronicle_observations.approval_state` column (migration)
- Refactor `chronicle_generator.persist()` to write `approval_state` based on `quality_gates` thresholds
- Render-team-pages reads `WHERE approval_state IN ('auto_approved', 'human_approved')`
- **Verification:** Fri 09:00 ET Mailbag publishes with ≥2 mined questions. Chronicle cards from low-tier programs show `queue_low_confidence`, not in render

### Sprint v5-5 (Week 5) — Heisman + canon nightly

- New `prompts/heisman_weekly.md` + `manage.py generate-heisman-narrative`
- Add to `ingest_weekly.yml` (Mon 06:00 UTC) after Heisman model
- Restructure `generate-canon-list` to skip rows with existing prose where `model_version_at_generate == current_model_version`. Tier-aware routing (Opus top-10, Sonnet 11-100)
- Add to `enrich_nightly.yml`
- **Verification:** Heisman page shows narrative next Monday. Canon entries 50-100 backfill within 3 nights

### Sprint v5-6 (Week 6) — Imagery Phase A1+A2 auto + OG cards

- New `scripts/imagery/render_helmets.py` Blender 4.x headless. New `imagery_helmets.yml` workflow (one-time dispatch + on-demand). Helmet base `.blend` committed to repo (~5MB acceptable)
- Add Pillow OG card package `src/cfb_rankings/share_cards/` (10 templates per v4 §5.3)
- Wire into `publish_site.yml` post-process
- Add `<picture>` emission helper `src/cfb_rankings/visual_assets.py:asset_for(slug, kind)`
- Cloudflare R2 bucket provisioned + upload step in `publish_site.yml`
- **Verification:** `/teams/alabama.html` ships with OG `<meta>` pointing to R2 1200×630 card. Helmet renders in `output/site/assets/helmets/<50>.png`

### Sprint v5-7 (Week 7) — Editorial illustration (FLUX) + auto-throttle

- New `scripts/imagery/generate_editorial_art.py` — BFL FLUX.1 [pro] API per `prompts/illustration_<surface>.md`
- CLIP similarity gate. Reference cluster of 10 hand-approved images embedded into `output/_assets/style_reference_embeddings.npz`
- Add LLM auto-throttle to `llm_runtime.py`: read `llm_weekly_spend_ceiling_usd` gate; degrade model tier when exceeded
- **Verification:** Chronicle moments tagged `surprise ≥ 0.8` get FLUX illustration next nightly run. LLM weekly spend stays under $120

### Sprint v5-8 (Week 8) — Kevin Zero-Touch UI

- New `notify_failure.yml` reusable workflow
- Wire into every cron via `if: failure()` final step
- New `digest_weekly.yml` cron `0 21 * * 5` + Resend integration
- New `/admin/queue/` page + slider UI writing to `quality_gates` table
- New `/admin/panic` route + `system_state` table check at top of every site-deploy workflow
- **Verification:** Kevin receives one digest email Fri 17:00 ET. Toggle `publish_paused=true` — next Daily cron exits 0 without deploying

### Sprint v5-9 (Week 9) — Bespoke surfaces: programs + data sources

- Implement 17 per-program bespoke surfaces (Part 1) via profile-schema extensions
- Implement 16 named data-source surfaces (Part 6) — `src/cfb_rankings/data_source_pages/*.py`
- Add to `enrich_nightly.yml`
- **Verification:** `/teams/alabama/saban-era/` renders next morning. `/sources/box-office-tell/` renders next Wednesday

### Sprint v5-10 (Week 10) — Bespoke surfaces: players + rivalries + phases + Reddit + conferences

- Implement 19 player position+archetype surfaces (Part 2)
- Implement 8 Tier-1 rivalry detail pages (Part 3)
- Implement 10 phase-specific surfaces (Part 5)
- Wire phase-transition trigger via `season_phase_transition` event in `scrape_health.yml`
- Implement 12 Reddit-archive surfaces (Part 7)
- Implement 11 conference landing pages + 5 cross-program surfaces (Part 4)
- **Verification:** `docs/surface_automation.md` matrix all green in `/admin/queue/`

**Total: ~14 dev-weeks across 10 sprints. Identity moves ship Sprint v5-1 + v5-2 (first 2 weeks). Imagery pipeline Sprint v5-6 + v5-7. Bespoke surfaces Sprint v5-9 + v5-10.**

---

## Part 10 · Risk Register

| Failure mode | Likelihood | Recovery |
|---|---|---|
| Anthropic API outage | Quarterly | `llm_runtime` returns `offline-stub`; each synthesizer has cached/templated fallback (existing pattern in `wire/editorial.py:_factual_restatement` extends) |
| FLUX / BFL API outage | Rare | Fall back to Pillow OG cards (text-only); skip editorial illustration. Tag `image_status='pending'`; nightly retry |
| GitHub Actions runner outage | 1-2×/yr, 1-4hr | `publish_site.ps1` local script remains as manual revival. Runbook in `docs/runbooks/actions_outage.md` |
| Reddit API change (Arctic Shift) | Already happened | `backfill-offseason-conversation` uses arctic-shift provider; degradation = "skip new posts." Cron tolerates empty fetch |
| Bluesky / Spotify / SeatGeek schema change | Per source quarterly | Each adapter isolated in `tools/run_adapter.py`; failure isolated; cron continues. Adapter-level metric to `scrape_health` |
| LLM cost runaway (10× spike) | Possible after viral story | `quality_gates.llm_weekly_spend_ceiling_usd` enforces throttle. Auto-degrades Opus→Sonnet→Haiku→template. Email Kevin when throttle fires |
| Validation chain too strict (>50% dropout) | Possible after prompt-template change | `manage.py analyze-llm-usage --window 7d --by template,version` alerts on regression >10%. Auto-relaxation: validator falls back to "warn-only" mode for 24h while regression investigated |
| Validation chain too loose (banned phrase ships) | Possible if validator regex misses | Post-publish HTML audit scans rendered HTML for banned-phrase set; writes to `post_publish_violations`; triggers `notify_failure`. `/admin/post-edit?path=&replace=` for hot-patch |
| Site-deploy concurrency lockout | Rare | `cancel-in-progress: false` queues. Queue depth >5 alerts via `scrape_health`. Recovery: manual workflow cancel via GH UI |
| `cfb-rankings-db` artifact corruption | Happened (478KB poison incident) | 5000-file `site_check` gate in `publish_site.yml` (existing). Extend with DB-size floor (`page_count × page_size > 50MB`) |
| Vercel deploy quota exhaustion | Possible at high cron frequency | Current 5-deploys/day (Daily + Wire + Mailbag + Edition + Enrich-nightly) well under Vercel hobby quota. Pro plan headroom 100/day |
| Backfill timeout (6hr GH Actions cap) | Happened | `backfill_progress` resume logic per Sprint v5-1. Re-dispatch resumes from last completed phase |
| Voice-validator + headline-quality drift ("every Saturday cover-essay reads the same") | Possible | Add `prompt_temperature` + `prompt_top_p` randomization per template + "draft diversity check" — compare this week's essay embedding against last 4 weeks'; regenerate if cosine >0.9 |

---

## Part 11 · Closing

v1 found problems. v2 explained why they were structural. v3 specified what the site looks like when complete. v4 specified how to build it. **v5 specified what makes the site uniquely itself — and how the entire content engine runs without Kevin ever clicking "Publish."**

### What the site looks like when v5 is done

A reader lands on `/teams/alabama.html` on a Tuesday morning in October:

- 3px crimson SEC top-rule
- 80px helmet-stripe band with "ALABAMA" reversed in end-zone-paint Bowlby script
- Below it, the bespoke **Process Counter**: "2,847 days since the last loss that mattered" — the one-of-one signature module no other program has
- **Source-Trust Ribbon**: `reddit ●2h · bluesky ●14m · espn ●4h · campus ●1d · wikipedia ●12h · seatgeek ●9h · gdelt ●live · locked-on ●3h`
- **Mood Ribbon** with Pulse + **Divergence Dumbbell** showing stat-folks #4 vs casual-fans #17 with bold "Δ 13" on the rod
- **Receipt Strip**: "The model said Alabama 9-3 in August. They're 7-1." with Phosphor checkmark
- **Savant Card** with 13 percentile bars
- **Era Strip** with houndstooth texture overlay on the Saban-era band (1958-1982 Bryant, 2007-2023 Saban)
- **Iron Bowl countdown clock**: "32 days · at Bryant-Denny" with the molten-iron-droplet trophy glyph
- **The Time Machine callout**: "Today's r/RollTide mood is the highest October Tuesday since 2018, the year before the Saban-Belichick title"
- **Bottom-nav Phosphor SVG** (5 slots, replacing emoji)

A reader on `/rivalries/iron-bowl.html` sees the 18°-tilted crimson-to-burnt-orange seam with the molten-iron-droplet glyph, the 10-anchor Era Strip (1893 first meeting → 2013 Kick Six → 2023 Fourth-and-31), the "Auburn from 35+" histogram with the 2013 109-yard spike alone in its column, and the dual-fanbase posture panels.

A reader on `/realignment/` sees 157 years of conference membership in a single Sankey, with Tulane / WVU / TCU / USF "team in 5 conferences" cards beneath.

A reader on `/timemachine/` sees Vandy-beats-Alabama 2024 at #1 all-time r/CFB postgame with its 4,891-upvote top comment ("Beat Bama. National signing day comes early in Nashville.") quoted in Charter italic.

### The engine running underneath

- **Friday 17:00 ET**: Kevin receives one digest email summarizing what will publish over the next 36 hours. Five items with one-click reject links. He glances. He ignores it. He goes to bed.
- **Saturday 04:00 ET**: `wire-daily-04am-et.yml` cron fires. CFBD adapters pull, Sonnet writes "why it matters" for 60 new wire rows, voice validator gates, R2 deploys. Reactions trigger sweep runs.
- **Saturday 06:00 ET**: `publish-edition-weekly.yml` cron fires (now wired into the deploy pipeline). Opus has already written the cover essay at 04:00 ET via the new pre-publish `generate-edition` step. Voice-gated. `editions_authored` row exists. Vercel deploys.
- **Saturday 12:00 ET → Sunday 02:00 ET**: `fanintel_gameday_live.yml` runs every minute. Live team-page mood ribbons tick. At window end, an 8-hour reactions sweep fires.
- **Sunday 09:00 ET**: `enrich_nightly.yml` (the new cron-converted `world_class_enrich.yml`) refreshes 17 team pages. Chronicle generator runs. Storyline draft poller promotes ready chapters. Heisman narrative generator writes Sunday's update.
- **Monday 06:00 ET**: `the-daily-06am-et.yml` cron. Three takes drafted with Sonnet (Opus on tentpole days). Voice-gated. Deploys.

**Kevin opens nothing. Publishes nothing. Reviews nothing manually.** The digest email is his only checkpoint, and most weeks he ignores it.

### The cumulative numbers

- **3,759 + 1,393 + ~1,500 = ~6,650 lines of audit** across v1-v5
- **26 parallel investigators** orchestrated across four rounds (v2 + v3 + v4 + v5)
- **~14 dev-weeks** total to land v5 end-to-end
- **~$4,420/yr** LLM spend ceiling with auto-throttle at $120/wk
- **17 profiled programs** with full bespoke treatment + 33-program expansion plan to 50
- **8 Tier-1 rivalries + 17 Tier-2** with bespoke design specs
- **10 season phases × 9 design variants** in declarative config
- **16 data sources → 16 named editorial surfaces**
- **12 Arctic Shift Reddit archive surfaces** (the 13-year moat made visible)
- **11 FBS + 13 FCS conference identities** with per-conference signature modules
- **9 position frames × 10 archetype frames** for per-player bespokeness
- **50 trophy glyphs** for rivalry iconography
- **5 universal opt-in atoms** + 13 build-ready signature atoms
- **15 existing workflows audited** + **12 manual gates mapped to automation paths**

### The single most important pattern

**Every editorial surface, every data refresh, every imagery generation step has a documented automation path with cron / trigger / validation / fallback.** No manual gates remain except the `/admin/queue/` and `/admin/panic` controls Kevin uses to *override* automation when needed — not to *invoke* it.

The cohorts disagree, and the disagreement is the story. The receipts age. The mood ribbon ticks. The Time Machine remembers. The process does not flinch at rankings. **The standard does.**

And nobody had to push a button to make any of it happen.

---

## Appendix A · Per-Program Bespoke Details (extended)

Per Investigator A: complete 9-axis specs for all 17 profiled programs. See investigator's full output for: Alabama Process Counter (denominator: 2022-01-10 title-game loss to Georgia, current value ~2,847 days), houndstooth texture rules (Bryant 1958-1982 + Saban 2007-2023 era-strip bands only), Vandy anchor SVG (280px-tall, page-right gutter, descending from heritage strip to mood ribbon), Notre Dame schedule-strength meter (12-stop, gold caret), Ohio State Michigan-week thermometer (sticky countdown from Week 1, flips to "1 in a row" after The Game), Oregon uniform-of-the-week (Thursday-revealed 3-chip combo with nickname), etc.

## Appendix B · The 50-Trophy Commission List

Tier 1 mythic (8 commissioned at $50-100): Iron Bowl molten-droplet, The-Game-Michigan-OSU block-G, Jeweled Shillelagh oak cudgel, Red River Golden Hat, Stanford Axe, Army-Navy three-football pyramid, War Eagle + Uga combined, Yale-Harvard mortarboard.

Tier 2 regional defining (17): Apple Cup apple, Bedlam "Old Central" bell, Civil War duck-beaver hybrid (Platypus), Egg Bowl golden egg, Floyd of Rosedale bronze pig, Iron Skillet, Old Oaken Bucket, Little Brown Jug, Paul Bunyan's Axe lumberjack axe, Paul Bunyan statue silhouette (Mich-MSU), Third Saturday cigar, Cocktail Party martini olive, FSU-Florida tomahawk + spear, Backyard Brawl coal-pile, Holy War mountain peak, Bayou Bucket, Palmetto Bowl palmetto + crescent.

Tier 3 standard (~25): generated via in-house Claude-grounded SVG prompts.

## Appendix C · The Complete File Map (new and touched, v5)

**New modules:**
- `src/cfb_rankings/players/composer.py` — Module Composition Resolver
- `src/cfb_rankings/players/archetype_modules/` — 10 archetype × 3-5 modules each
- `src/cfb_rankings/charts/positions/` — 9 position chart-helper modules
- `src/cfb_rankings/archive/` — 12 Reddit-archive renderer files
- `src/cfb_rankings/team_pages/discourse_history.py`
- `src/cfb_rankings/editions/quarterly_archive_issue.py`
- `src/cfb_rankings/rivalry_pages/renderer.py`
- `src/cfb_rankings/rivalries/detail_page.py` + `index_page.py`
- `src/cfb_rankings/realignment/renderer.py`
- `src/cfb_rankings/coaching_trees/renderer.py`
- `src/cfb_rankings/recruiting/map_renderer.py`
- `src/cfb_rankings/g5_p4/renderer.py`
- `src/cfb_rankings/nfl_pipeline/renderer.py`
- `src/cfb_rankings/inter_conference/renderer.py`
- `src/cfb_rankings/championships/renderer.py`
- `src/cfb_rankings/season_phase_pages/<phase>.py` — 10 phase-specific renderers
- `src/cfb_rankings/data_source_pages/*.py` — 16 data-source surface renderers
- `src/cfb_rankings/share_cards/` — 10 Pillow OG card templates
- `src/cfb_rankings/audit/` — 8 audit subcommands (from v4)
- `scripts/imagery/render_helmets.py` (Blender batch)
- `scripts/imagery/fetch_stadium_photos.py` + `fetch_roster_headshots.py` + `fetch_coach_portraits.py`
- `scripts/imagery/generate_editorial_art.py` (FLUX.1 [pro] API)
- `prompts/*.md` — 11 prompt templates with frontmatter (`version`, `model`, `max_tokens`, `voice_validator_strict`)
- `data/rivalry_anchors/<slug>.yaml` — 25 rivalry anchor sets
- `data/trophy_lore/<slug>.md` — 25 trophy origin paragraphs

**New tables / migrations:**
- `migrations/sql/0042_prompt_versions.sql` — `prompt_versions (template_path, version_hash, model, created_at_utc, deprecated_at_utc)`
- `quality_gates (gate_key, value, description, updated_at_utc)`
- `editions_authored (slug, cover_essay_md, theme, cover_viz_data_json, model_id, confidence, validation_notes_json, generated_at_utc)`
- `team_chronicle_observations.approval_state` column
- `backfill_progress (phase_name, season_year, completed_at_utc, run_id)`
- `archive_threads`, `archive_comments`, `archive_term_weekly`
- `program_canon_comments`, `pivot_events`, `month_anchors`, `signature_phrases`, `historical_artifacts`, `player_name_velocity`, `chronicle_moments_echo_match`
- `all_conference_teams`, `conference_inter_records` view, `g5_over_p4_wins` view
- `system_state (key, value, set_at_utc, set_by)`
- `editorial_overrides (surface, slug, action, signed_token, set_at_utc)`
- `post_publish_violations (page_url, phrase, detected_at_utc)`
- `page_lastmod (page_url, lastmod_utc)` (for sitemap)
- `player_archetype_tags (player_id, tag, confidence, evidence_ref)`
- `canon_cross_reference (player_a, player_b, relation_label, weight)`

**New workflows:**
- `.github/workflows/enrich_nightly.yml` — cron `0 14 * * *`
- `.github/workflows/canon-monthly.yml` — cron `0 14 1 * *`
- `.github/workflows/audit-on-pr.yml` (from v4)
- `.github/workflows/visual-regression.yml` (from v4)
- `.github/workflows/lighthouse-ci.yml` (from v4)
- `.github/workflows/imagery_helmets.yml`
- `.github/workflows/digest_weekly.yml` — cron `0 21 * * 5`
- `.github/workflows/notify_failure.yml` — reusable

**Modified workflows:**
- `publish-edition-weekly.yml` — add `site-deploy` concurrency group + Vercel deploy + pre-publish `generate-edition` step
- `world_class_enrich.yml` — add cron `0 14 * * 0`
- `compute_full_pass.yml` — add cron `0 14 1 * *`
- All cron workflows — add `if: failure()` final step calling `notify_failure.yml`

**Touched code:**
- `src/cfb_rankings/llm_runtime.py` — accept `prompt_template_path`, log `template_path + version_hash`, add LLM auto-throttle reading `llm_weekly_spend_ceiling_usd`
- `src/cfb_rankings/editions/cli.py:_cmd_publish_edition` — read `editions_authored` first
- `src/cfb_rankings/editions/theme_resolver.py` — refactor to read live cohort/storyline/Wire signals
- `src/cfb_rankings/team_pages/chronicle_generator.py:persist()` — write `approval_state` based on `quality_gates`
- `src/cfb_rankings/wire/editorial.py` — replace `_factual_restatement` with Sonnet call
- `src/cfb_rankings/reactions/synthesizer.py` — auto-trigger in wire + gameday workflows
- `src/cfb_rankings/storylines/chapter_authoring.py` — feed `auto-promote-storyline-drafts` poller
- `src/cfb_rankings/cli.py` — add new CLI subcommands per Part 8
- `src/cfb_rankings/team_pages/renderer.py` — extend with `_render_bespoke_signature(profile)` dispatching to 17 program-specific modules
- `src/cfb_rankings/team_pages/profile_loader.py` — extend Profile dataclass with v5 schema additions

**Deleted (no longer needed):**
- `scripts/register_daily_task.ps1`, `register_weekly_task.ps1` — local Windows Task Scheduler bypass; replaced by GitHub Actions

---

## Appendix D · Reading Order

For a developer onboarding to the v5 implementation:

1. **Read v4 first** for the foundational architecture (atoms, voice, mobile, motion, share cards, governance)
2. **Read v5 Part 8** (Automation Architecture) — the spine
3. **Read v5 Part 1** (Per-Program Bespokeness) for the profile-schema extensions and atom-flag system
4. **Read v5 Part 9** (Implementation Roadmap) — sprint-by-sprint with verification gates
5. Reference v5 Parts 2-7 as feature-specific specs when implementing those surfaces

For a non-technical reader:

1. **Read v5 Part 11** (Closing) for the "what the site looks like when done" walkthrough
2. **Read v5 Part 1** for per-program bespokeness
3. **Read v5 Part 3** for rivalry treatments
4. **Read v5 Part 5** for season-phase bespokeness
5. **Read v5 Part 8.6** (Kevin Zero-Touch UI) for the human-facing controls

---

**End of v5.** The four prior audits told the story. v5 makes the site uniquely itself — and then takes Kevin's hands off the wheel. The cohorts disagree, the disagreement is the story, and the engine runs without him.
