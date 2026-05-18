# CFB Index — Triple Audit, v4 (Build-Ready Translation)

**Date:** 2026-05-15
**Auditor:** Claude (autonomous, orchestrated 18-investigator parallel deep-dive across v2 + v3 + v4)
**Live site:** https://wonderful-margulis-8ec96b.vercel.app
**Supersedes:** [v1](DESIGN_AUDIT_2026_05_15.md) (problems), [v2](DESIGN_AUDIT_2026_05_15_v2.md) (architecture), [v3](DESIGN_AUDIT_2026_05_15_v3.md) (imagery + identity)
**Reads as:** the build spec. v3 said *what the site looks like*; v4 says *how to ship it*.

---

## What v4 Adds Over v3

Six v4 investigators produced six implementation-translation artifacts:

1. **13 build-ready atoms** — Python signatures, HTML markup, CSS, props, ARIA, mobile variants, reduced-motion behavior, edge cases, ship locations, composition rules. Ready to paste into `src/cfb_rankings/common/atoms.py` + `output/site/assets/atoms.css`.
2. **10-section editorial voice stylebook** — voice description, 10+ headline-template categories with 30+ examples, comprehensive banned-phrases list (pipeline-leakage + AI-tell + sports-cliché + program-cliché), 5 desk sub-voices, attribution format, per-surface copy patterns, profile schema extensions, 5-question headline-quality checklist, 250-word in-voice Alabama Pulse example.
3. **Mobile-first complete redesign** — mobile design-system foundation (type-scale floors, spacing tokens, sticky-element hierarchy), 5-slot Phosphor bottom-nav + hamburger drawer, per-surface mobile patterns (Wire swipeable cards, Rankings filter sheet, Compare tabbed-swipe, Hub virtualization), full above-the-fold composition for all 18 pages at 375×667 + 390×844, the 5 highest-impact mobile fixes (~9 dev-days).
4. **Motion-choreography spec** — 5 easing curves + 7 durations + 4 staggers, per-element-type hover/focus/active/disabled table, page-load reveal sequence with stagger timings, per-chart entry choreographies for all 14 patterns, data-update tween rules, sticky behaviors, View Transitions API plumbing, 3 micro-delight moments capped at 0.22 overshoot, complete reduced-motion override matrix, the corrected 220ms brass-band-cadence math, 11 forbidden motion patterns.
5. **Share-card + SEO + structured-data system** — per-surface Pillow OG card visual specs, full Pillow rendering pipeline + module skeleton, `render_head_chrome()` Python helper emitting OG/Twitter/JSON-LD/canonical/feed-discovery, 8-shard sitemap-index strategy at 69k pages, 12-file RSS+Atom+JSON-Feed system, JSON-LD schemas per page type (SportsTeam / Person / NewsArticle / Article / Organization / WebSite / BreadcrumbList), 10-bullet audit of current `_meta_tags()`.
6. **Build/deploy governance + performance budgets** — 8 `manage.py audit-*` subcommands wired into CI, performance budgets per page type (LCP / TBT / CLS / weight ceilings), Playwright visual-regression on 8 representative pages × 2 viewports, design-token-drift detection script, content governance rules (Chronicle approval queue, Storyline state machine, Pulse floor, world-class-enrich triggers), editorial publication cadence matrix, 5 CI workflows (audit-on-pr, visual-regression, lighthouse-ci, canon-monthly), cache strategy with Vercel route-pattern headers, browser-support matrix with feature-fallback rules, 10 build upgrades ranked (~17.5 dev-days).

---

## Part 1 · The 13 Build-Ready Atoms

Each atom below is a complete spec — Python signature, HTML output, CSS, props, A11y, mobile variant, reduced-motion behavior, edge cases, ship locations, composition rules. Reads top-to-bottom as a developer reference. Token names use v3 canonical (`--paper`, `--wool`, `--gold-october`, `--ink`, etc.) which the `common/design_tokens.py` build-time generator resolves into either v3 names or backward-compat aliases for shipped CSS.

### 1.1 MoodRibbon — Signature 1 (atmospheric)

**Purpose.** 52-week belief trajectory as a horizon strip, readable at a glance from any masthead.

**Visual.** 24px tall × full module width. Each week = 1/52 vertical slice. Hue encodes valence (cool slate → warm crimson); saturation encodes magnitude. 0.5px `--field-white` zero-line bisects horizontally; current week is 2px `--ink` vertical tick with `--gold-october` dot above.

```python
def mood_ribbon(
    weekly_values: list[float | None],
    *,
    current_week_idx: int | None = None,
    width: int = 624, height: int = 24,
    title: str = "", title_id: str | None = None,
) -> str: ...
```

Values are zero-centered (-1.0 doom .. +1.0 belief). `None` cells render as `--concrete` 8%.

```html
<svg class="cfb-mood-ribbon" width="624" height="24" viewBox="0 0 624 24"
     role="img" aria-labelledby="mr-tt" aria-describedby="mr-dd">
  <title id="mr-tt">Alabama mood, 52 weeks</title>
  <desc id="mr-dd">Peak Sept 21 +0.74, trough Nov 9 -0.41, current +0.18.</desc>
  <g class="cfb-mood-ribbon__cells"><!-- 52 rects --></g>
  <line class="cfb-mood-ribbon__zero" x1="0" y1="12" x2="624" y2="12"/>
  <line class="cfb-mood-ribbon__current" x1="468" y1="0" x2="468" y2="24"/>
  <circle class="cfb-mood-ribbon__current-dot" cx="468" cy="-3" r="2.5"/>
</svg>
```

```css
.cfb-mood-ribbon__zero    { stroke: var(--field-white); stroke-width: 0.5; opacity: 0.55; }
.cfb-mood-ribbon__current { stroke: var(--ink); stroke-width: 2; }
.cfb-mood-ribbon__current-dot { fill: var(--gold-october); }
```

**A11y.** `role="img"` + `aria-labelledby` → `<title>` + `aria-describedby` → `<desc>` with auto-generated peak/trough/current. Not keyboard-focusable (decorative summary; full data lives in adjacent text).

**Mobile (<640px).** Height stays 24px; width 100%. Current-week dot moves inside strip (y=12) to survive top-edge cropping. `vector-effect="non-scaling-stroke"` on the zero-line.

**Reduced motion.** Static.

**Edge cases.** Empty list → `''`. Single point → one 12px cell centered. All-None → flat `--concrete` band with `<desc>Awaiting signal</desc>`. <52 entries → left-padded with `--concrete` 8%. Dark mode → fills via `color-mix(in oklab, var(--crimson) X%, var(--wool) Y%)`.

**Ships on.** Team-page `_render_hero` (replaces 7-bar trajectory); Hub row teaser (220×16 variant); Daily lede; signature stories.

**Composition.** Flush above hero record/rank chip row (8px gap). Never two stacked. May sit beside JerseyBlockNumeral (current mood number) with 16px gap.

### 1.2 DivergenceDumbbell — Signature 2 (the brand atom)

**Purpose.** Render the thesis — *cohorts disagree, the disagreement is the story* — as a recognizable atom usable anywhere cohort split exists.

**Visual.** 200×40px horizontal axis (rank 1 left → rank 25 right). Two dots: `ChartBar` glyph in `--conf-acc` (stat-folks), `Smiley` glyph in `--burntorange` (casuals). Connected by 4–10px rod whose thickness encodes |Δ|. Bold `Δ 14` in `--ink` JetBrains Mono on rod with 2px `--paper` halo.

```python
def divergence_dumbbell(
    stat_rank: int, fan_rank: int,
    *, width: int = 200, height: int = 44,
    title: str = "", inline_label: bool = True,
) -> str: ...
```

```css
.cfb-dumbbell { font-family: var(--font-mono); }
.cfb-dumbbell__rod { stroke: var(--concrete); stroke-linecap: round; }
.cfb-dumbbell__delta { fill: var(--ink); font-size: 11px; font-weight: 700;
  paint-order: stroke; stroke: var(--paper); stroke-width: 3; text-anchor: middle; }
.cfb-dumbbell__dot--stat circle { fill: var(--conf-acc); }
.cfb-dumbbell__dot--fan  circle { fill: var(--burntorange); }
```

**A11y.** `<title>` auto-emits `"Stat folks #N, fans #N. Disagreement: M spots."` Phosphor glyphs `aria-hidden`.

**Mobile.** Width 160px, rod thickness 80%, Δ-text below rod (y=30). 1/13/25 ticks collapse to just 1/25 below 140px.

**Edge cases.** Equal ranks → overlapping dots, rod 0, Δ="0" muted. Unranked side → outlined ring with `?`, dashed rod, Δ="UR". |Δ| ≥ 20 → rod thickness clamps at 10px.

**Ships on.** *Universal atom* — Reactions cover art (280×56 variant), Wire rows with cohort split, Mailbag inline, Players Accolade Lens, Hub Voices, Canon entries, homepage callout.

### 1.3 SavantCard — Signature 3 (credibility)

Already shipping in `src/cfb_rankings/team_pages/savant_card.py`. Formalize signature with new `compact=True` variant for Wire/Mailbag:

```python
def savant_card(
    profile: Profile, rows: list[SavantRow], *,
    narrative: str | None = None, echo: dict | None = None,
    season_year: int, compact: bool = False,
) -> str: ...
```

`compact=True` returns top-4 bars (highest |percentile − 50|) only, no narrative/echo/footer.

```css
.savant-card--compact { background: transparent; border: 0; padding: 0; }
.savant-card--compact .savant-card__bar-row { height: 18px; }
.savant-card--compact .savant-card__capsule { font-size: 11px; padding: 1px 6px; }
```

**A11y.** Each bar row `role="img"` + `aria-label="{metric}: {value}, {percentile}th percentile vs {peer_set}"`. Toggle chips are `<button aria-pressed>`.

**Mobile.** Bars 24px tall; metric name above track (not inline). Compact = always single column.

**Ships on.** Every team page; every player page; `compact=True` on Wire callouts + Mailbag inline + Heisman shortlist.

### 1.4 ReceiptStrip — Signature 4

**Purpose.** Anchor the "we said this, here's what happened" voice as an atom.

```python
def receipt_strip(*,
    claim_text: str, claim_value: str,
    reality_text: str, reality_value: str,
    verdict: str,         # "wrong" | "right" | "tbd" | "partial"
    width: int | None = None,
    date_iso: str = "",
) -> str: ...
```

```html
<aside class="cfb-receipt" data-verdict="wrong" aria-label="Receipt: preseason #4, current #19">
  <div class="cfb-receipt__rows">
    <p class="cfb-receipt__claim">
      <span class="cfb-receipt__eyebrow">Aug 24 ·</span>
      <s>We said <strong>Ohio State #4 nationally.</strong></s>
    </p>
    <p class="cfb-receipt__reality">Today they sit <strong>#19.</strong></p>
  </div>
  <div class="cfb-receipt__chevron" aria-hidden="true">
    <svg viewBox="0 0 16 16" width="16" height="16"><use href="#phosphor-arrow-down"/></svg>
    <span class="cfb-receipt__delta">−15</span>
  </div>
</aside>
```

```css
.cfb-receipt { display: grid; grid-template-columns: 1fr 56px; gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4); background: var(--paper);
  border-left: 3px solid var(--concrete); border-radius: var(--radius-sm); }
.cfb-receipt[data-verdict="wrong"]   { border-left-color: var(--alert); }
.cfb-receipt[data-verdict="right"]   { border-left-color: var(--grass); }
.cfb-receipt[data-verdict="partial"] { border-left-color: var(--gold-october); }
.cfb-receipt__claim   { font: italic 14px/1.45 var(--font-serif); color: var(--ink-muted); }
.cfb-receipt__reality { font: 16px/1.45 var(--font-serif); color: var(--ink); }
```

**Mobile.** Grid collapses single-column; chevron becomes 56×24 right-aligned banner above rows.

**Ships on.** `/receipts/`; team-page hero (one per profiled program with tracked claim); Wire inline; Heisman calibration retrospective; Daily ledger; Chronicle "retroactive" cards.

### 1.5 VerdictTile — Signature 4 compressed

3-cell row (Claim 32% / Outcome 32% / Verdict 36%) with brass-gold cell separators.

```python
def verdict_tile(
    claim: str, outcome: str, verdict_glyph: str, verdict_text: str,
    *, verdict: str = "right",
) -> str: ...
```

```css
.cfb-verdict { display: grid; grid-template-columns: 1fr 1fr 1.2fr;
  font: 12px/1.3 var(--font-mono); border: 1px solid var(--stroke-default);
  border-radius: var(--radius-sm); overflow: hidden; }
.cfb-verdict__claim    { color: var(--ink-muted); text-decoration: line-through; }
.cfb-verdict__judgment { color: var(--alert); display: inline-flex; gap: 4px; }
.cfb-verdict[data-verdict="right"] .cfb-verdict__judgment { color: var(--grass); }
```

**Ships on.** Daily morning-ledger footer; Wire when claim resolves; Receipts condensed view; team-page Era Strip annotations.

### 1.6 EraStrip — Signature 5 (time-depth)

12-track horizontal multi-track strip: top track = conference label band; coach color-band background per-tenure; SP+ line spanning width with AP-final dots overlaid; era classifications (CFP-12 / CFP-4 / BCS / pre-bowl) on bottom track. Hairline brass-gold dividers between seasons.

```python
def era_strip(
    seasons: list[SeasonRow], *,
    width: int = 624, height: int = 140, title: str = "",
    coach_bands: list[CoachBand] | None = None,
    era_bands: list[EraBand] | None = None,
) -> str: ...
```

**Mobile.** Drops to 8 seasons (most recent), height 100px, year labels every other column. Touch-scroll horizontally if `seasons > 8`.

**Reduced motion.** No path-draw animation; line draws instantly. Scrollama reveal becomes 0ms cross-fade.

**Ships on.** Every profiled team page (last major module); legacy team-page bottom section; Canon era pages; Conference landing pages (single-track variant); Player career-arc page.

### 1.7 SourceTrustRibbon — Move B (the moat made visible)

Horizontal row of 8 chips, each ~88×40px. Source SVG mark (24×24) left, 2-line text right (source name 11px caps; freshness "12m ago" mono), 6px round Tier dot top-right — `--grass` (Tier 1), `--gold-october` (Tier 2), `--concrete` (Tier 3). Stale chips (>24h) get 40% opacity.

```python
def source_trust_ribbon(
    sources: list[SourceChip],   # {key, name, freshness_min, tier}
    *, title: str = "Sources", show_legend: bool = True,
) -> str: ...
```

```css
.cfb-source-chip { position: relative; display: grid;
  grid-template-columns: 24px 1fr; gap: var(--sp-2); align-items: center;
  padding: var(--sp-2) var(--sp-3); background: var(--bg-2);
  border-radius: var(--radius-sm); min-width: 88px; }
.cfb-source-chip[data-freshness="stale"] { opacity: 0.4; }
.cfb-source-chip__dot { position: absolute; top: 4px; right: 4px;
  width: 6px; height: 6px; border-radius: 50%; }
.cfb-source-chip[data-tier="1"] .cfb-source-chip__dot { background: var(--grass); }
```

**Mobile.** Chips flex-1 (~50% width, 2 per row); show only 6 most-recent if `sources.length > 6`.

**Ships on.** Every page footer above main `<footer>` (slim 6-chip variant); Methodology (full 8-chip + legend); Daily/Wire mast (12-chip extended).

### 1.8–1.13 CFB Motif Atoms

| Atom | Purpose | Key spec |
|---|---|---|
| **YardLineDivider** (Motif A) | Section break with 5-yard hash ticks | `def yard_line_divider(*, label: str|None = None, tinted: bool = False)`. Ticks at 25%/75% (shift to 30%/70% at <640px). Replaces every `<hr>` in CFB Index. |
| **HelmetStripeRule** (Motif B) | Full-bleed team-page top band | `def helmet_stripe_rule(*, accent_primary: str|None = None)`. 6px tall (5px on mobile), 1px `--field-white` bisecting line, auto-flips line to `--ink` for near-white team colors. |
| **DecalClusterFooter** (Motif C) | 3-decal pyramid footer mark | `def decal_cluster_footer(decals: list[Decal], *, mantra: str = "")`. 14px circles in `--accent-primary`, slight tilt, Phosphor `Trophy`/`Star`/`Lightning` icons. |
| **CFBackgroundTexture** | 3% paper grain noise overlay | `<body class="cfb-page-grain">` + inline SVG noise base64-data-URI. Disabled inside `.savant-card`, `.cfb-receipt`, `.cfb-mood-ribbon` containers. Print stylesheet drops it. |
| **DuskGameRow** | Dark-navy underwash for night games on schedule | `def schedule_row(opponent, opponent_logo_url, kickoff_iso, result, is_dusk: bool|None = None)`. Auto-derive `is_dusk` from kickoff hour ≥ 19:00. Moon glyph in `--gold-october` at kickoff cell. |
| **JerseyBlockNumeral** | Bowlby One SC display numerals | `def jersey_numeral(value, *, size="lg", label="", accent=False, title="")`. Sizes sm/md/lg/xl = 32/48/72/112px; scales 25% smaller on mobile. `font-display: optional` with Impact fallback. |

### Cross-cutting infrastructure

**Token migration.** `common/design_tokens.py` exports `COLORS` (v3 names) + `CSS_VAR_MAP` (alias `--paper` → `--bg-0`, `--ink` → `--fg-primary`, `--gold-october` → `--accolade-gold`, etc.). `atoms.css` is generated from this map at build-time via `python manage.py build-atoms-css` so a single rename pass migrates everything.

**Phosphor sprite.** All `<use href="#phosphor-*">` references resolve to a single inlined SVG sprite emitted by `_render_head_chrome()`. Add `<symbol id="phosphor-{name}">` definitions to `output/site/assets/phosphor-sprite.svg`. Same pattern for `#src-*` source marks.

**File system.**
- `src/cfb_rankings/common/atoms.py` — 13 Python helpers (~700 lines total)
- `src/cfb_rankings/common/design_tokens.py` — `COLORS`, `CSS_VAR_MAP`, `TYPE_SCALE`, `FONTS`, `emit_root_css()`
- `output/site/assets/atoms.css` — generated, cached at `max-age=31536000`
- `output/site/assets/phosphor-sprite.svg`
- `output/site/assets/fonts/bowlby-one-sc.woff2`

**Rollout order (by leverage):**

1. `JerseyBlockNumeral + HelmetStripeRule + DecalClusterFooter` → `_render_page_chrome()` — instant brand signal on 69k pages
2. `DivergenceDumbbell` → Reactions/Wire/Mailbag — the brand atom
3. `MoodRibbon` → team-page hero replacing existing trajectory
4. `SourceTrustRibbon` → shared footer
5. `ReceiptStrip + VerdictTile` → `/receipts/` index
6. `EraStrip` formalization on team pages
7. `YardLineDivider` → replacing existing `<hr>` calls
8. `DuskGameRow` → schedule renderers
9. `CFBackgroundTexture` → `<body>` last (sanity-check chart contrast)

---

## Part 2 · The Editorial Voice Stylebook

### 2.1 Voice description

CFB Index writes like a beat writer who took the FiveThirtyEight job. The register sits where Bill Connelly's analytical warmth crosses Joe Posnanski's narrative patience and rests against The Athletic's editorial discipline — quantitatively confident the way 538 was confident, but earned out of paying attention to one sport for ten years rather than out of a methodology page. The voice is not Spencer Hall's: it knows the joke is there and declines to make it. It is not broadcast register: no must-win Saturdays, no exclamation points, no "folks." It is the register of someone who has read every beat writer for every program every Monday for a decade, kept the receipts, and writes one sentence longer than anyone else would because the extra clause is where the read lives.

The voice does not narrate the data. It tells you what the data told it about Tennessee in the second quarter, and then it tells you what Knoxville is saying about that, and then it stops.

### 2.2 Headline templates (10 categories × 3 examples each)

Every CFB Index headline is **a sentence with a proper noun and a comparative claim.** Not a slug, not a topic tag.

**Sentence-led data headlines.** *Michigan's belief is at a decade low.* / *Texas is two cohorts having two seasons.* / *Kalen DeBoer's third-and-long defense is the best in Tuscaloosa since 2020.*

**Cohort-divergence headlines.** *The stat folks think LSU is fine. The fans don't.* / *Oregon's analytics fanbase is at peak; its casuals are six weeks behind.* / *Penn State splits 14 ranks between the people who watch the games and the people who watch the box scores.*

**Receipt-call headlines.** *The Boise prediction aged well.* / *We had Florida State at 9-3. They're 4-7.* / *The Vandy ceiling we set in August has already been broken twice.*

**Storyline-chapter headlines.** *Chapter 4: Sherrone Moore's grace period ends in Iowa City.* / *The Auburn quarterback room, year three.* / *Belief has stopped arriving for Florida.*

**Chronicle-card headlines (per type).**
- *Anomaly:* *Eight straight, and the only one that wasn't double digits was at Stanford.*
- *Moment:* *The Syracuse scoreboard said 70. The boards said Morrison.*
- *Flashpoint:* *Saturday in Athens is the season's load-bearing wall.*
- *Echo:* *The QB room is 2022's room, shuffled.*
- *Retroactive:* *What looked like a tune-up at Purdue reads now as the season's hinge.*
- *Player-arc:* *Faison has the drop-catch streak Avery Davis had in 2021.*

**Wire-event headlines (verbed, dated, mover named).** *Pavia returns; Vanderbilt's win equity moves +2.4.* / *Klubnik benched for a series; LSU's mood ribbon cools 11%.* / *DeBoer extends Holmon Wiggins; Tuscaloosa exhales.*

**Mailbag-question headlines (question rendered, not labeled).** *Why did the model love Tulane in week 3?* / *Is Penn State's offense actually broken or did it just play three road games?* / *How do you score a coach who inherits a 12-team CFP?*

**Reaction-story headlines (what the fanbase did).** *Alabama lost by one and the cohorts went separate ways.* / *Tennessee won and barely anybody on Bluesky said the word "Heupel."* / *The Iowa-Wisconsin score was 13-10. The board threads were 11,400 posts long.*

**Daily morning-story headlines.** *Saturday rearranged the Big 12. The model isn't surprised.* / *Three programs hit a season-high belief number; one of them was Indiana.* / *The Pac-12 remnants had their best Saturday since realignment.*

**Edition-cover-essay + Canon-entry headlines.** *After the Bracket.* / *Volume II: Eight Programs in Search of an Identity.* / *Diego Pavia, the year Vanderbilt beat Alabama.* / *Manti Te'o, before and after.*

### 2.3 Banned phrases (refuse list)

**Pipeline / system leakage** — card explains itself: *sample*, *stat engine*, *pipeline*, *the engine*, *our algorithm*, *methodology* (except on `/methodology/`), *the model output*, *robust signal*, *signal-to-noise*, *data-driven* (as adjective), *summary stat*, *compression of outcome*, *a flattening of*, *the pattern is*.

**Internal taxonomy leakage.** *tier 1/2/3* (user-facing), bare *cohort* without adjective, *the fan-intel pipeline*, *Awaiting Signal* (internal fallback string only).

**Generic gestures.** *Every season produces…*, *In this league…*, *In a year like this…*, *Here's the thing*, *The numbers don't lie*, *At the end of the day*, *To be clear*, *Make no mistake*, *That said*, *Don't sleep on*.

**AI-tell phrases.** *delve into*, *it's worth noting*, *it's important to note*, *moreover*, *furthermore*, *robust*, *leverage* (verb), *myriad*, *plethora*, *tapestry*, *landscape* (figurative), *navigate* (figurative), *unlock potential*, *journey*, *deep dive*, *take a closer look*, *let's explore*, *in conclusion*, *holistic*, *paradigm*, *ecosystem*. Em-dashes as filler — replace with period or colon. Em-dash allowed when carrying meaning. **Three em-dashes in a paragraph = rewrite.**

**Sports clichés.** *must-win* (every game is for someone — if elimination, say so), *statement game*, *Heisman moment* (loose use), *all-time great* (without specificity), *the GOAT*, *blue-chip prospect*, *back to the drawing board*, *changing of the guard*, *war chest*, *cupboard isn't bare*, *fired-up*, *gutsy call*, *gritty win*, *bend-but-don't-break defense*, *team of destiny*, *playing inspired football*, *putting on a clinic*, *the dean of college football*, *Saturdays in the South*, *between the hedges* (Georgia only), *the Big House* (Michigan only).

**Program-cliché trap doors** — extend per profile `never_use` lists.

### 2.4 Five desk sub-voices

| Desk | Surfaces | Register | Sentence length | Sign-off |
|---|---|---|---|---|
| **Editor's Desk** | Homepage cover essay, Editions opener | Literary, paced — Athletic longform × New Yorker section opener | 22–28 avg, range 4–40 | Roman-numeral section breaks, no kicker |
| **Receipts Desk** | `/receipts/`, Verdict Tile, team-page Receipt Strip | Dry, ledger-keeper, slightly amused — *Significant Digits* + beat-writer memory | 10–16 (two-sentence cards) | *Aged well.* / *Aged badly.* / *Aging.* / *Verdict pending.* |
| **Cohort Desk** | Hub, Pulse, every Reaction story | Even-handed, sociological — both readings are real readings | 14–22 | (mandatory) cohorts, Δ magnitude, source streams |
| **Connections Desk** | Chronicle, Echo cards, historical-archive pulls, Era Strip annotations | Thoughtful, occasionally elegiac, archive-fluent — Posnanski in a research library | Variable; longest sentences when warranted | A year, a name, an archive reference |
| **Fan-Voice Desk** | Pulse top-take, Mailbag answers, Wire commentary, reader-quote pulls | Conversational, second-person allowed — smartest poster in the group chat | 8–18 | Platform + date + thread or handle |

### 2.5 Attribution format

CFB Index attributes by what a fan would call the source at a bar, never by what the pipeline calls it internally.

**Acceptable forms:**
- Beat writer / blog with date: `OneFootDown · Mon`, `South Bend Tribune · 2d`, `Locked On Tide · Tue ep.`
- Platform aggregate: `from 14 beat-writer pieces this week`, `r/CFB · top thread Sat night`
- Archive citation with era: `from the Kelly-era archive`, `via 2018 Cotton Bowl recap`
- Historical pattern (anomaly cards only): `gamelog · 2014-now`
- Fan-intel velocity citation: `conversation velocity · Bluesky firehose`
- Public data source: `Savant card, CFBD data`, `SP+ · Connelly`
- Model self-citation (Receipts Desk only): `CFB Index · Sept 1 preseason ledger`

**Banned forms:** `CFB Index game-log stat engine`, `CFB Index pipeline`, `the model's output`, `our analysis indicates`, `data shows` (without source).

**The attribution gate:** if a piece of copy can't resolve to a URL, a thread, a dated archive, or a named public data source, it ships without attribution or it doesn't ship.

### 2.6 Per-surface copy patterns (compressed)

| Surface | Length | Structure | Voice rules |
|---|---|---|---|
| Daily morning story | 180–280w | 1-sentence lede yesterday's verb → 3–5 ¶ each anchored to one program → closer points at today (no "stay tuned") | Always opens with named program. Roman-numeral section breaks if >3 programs |
| Mailbag answer | 120–260w | Direct answer in sentence 1 (no preamble) → middle has the read + one cited stat or cohort divergence → close names what would change the answer | Sign-off: italicized byline + desk. No "Hope this helps" |
| Wire row | 60–90 chars | `[Verb-led sentence]. [One-clause consequence].` | Never "Reports indicate" / "Sources say." If hedging needed, event isn't ready |
| Reaction story | 80w | 3 sentences: (1) cohort split named (2) platform-level evidence (3) forward-looking | Cover art: Divergence Dumbbell with Δ rendered |
| Chronicle card body | 2–3 sentences | (per card type — anomaly/moment/flashpoint/echo/retroactive/player-arc) | See §2.2 for exemplars |
| Pulse top-take | 14–22w one sentence | Attributed to platform + date | Must come from `profile.stock_phrases` or real quoted post — never generic |
| Methodology copy | Direct | No metaphors, no "under the hood" | "CFB Index ingests…" not "our system" / "the engine" |
| Editions cover essay | 600–1100w | I — lede (drop cap) → II — evidence → III — the cut → optional IV — look-forward | Closes with *— The Editors* + edition number + date |
| Player canon entry | Opening 2–3 sentences | Name + era + the one thing he was | Savant Card stat-line + cohort-divergence sentence (mandatory) |

### 2.7 Tense / person / point-of-view

- **Tense.** Past for what happened. Present for current condition. Future only when scheduled, never speculative.
- **First-person plural ("we")** allowed only on Editor's Desk + Receipts Desk with editorial verb.
- **First-person singular ("I")** banned. Bylines are desks.
- **Second-person ("you")** allowed only on Mailbag answers + Pulse fan-voice line.
- **Sentence fragments** — encouraged when carrying weight. Once per card, once per paragraph.
- **Contractions** — allowed everywhere except Methodology.

### 2.8 Profile schema extensions

Add to every `profiles/*.md` (existing fields: `voice_register`, `tonal_template`, `identity_phrase`, `mantra`, `vocab`, `mascot_voice`, `era_name_overrides`, `never_use`, `always_surface`, `stock_phrases`, `rivalries`, `aspiration_ladder`, `heritage`):

- `headline_pattern_preferences` — which §2.2 categories lead for this program
- `forbidden_program_clichés` — extends `never_use` with program-specific
- `signature_metrics_to_lead_with` — 2–3 metrics this fanbase reads first
- `pull_quote_sources` — 3–5 fan-platform threads/blogs that get priority citation
- `era_signoff_overrides` — what the closer line reads for each era

### 2.9 Headline-quality checklist (5-question rubric)

Every headline must pass all 5 before shipping:

1. **Proper noun present?** Program, coach, player, stadium, year. *"Belief is fading"* fails.
2. **Comparative structure present?** *"since"*, *"the longest"*, *"a decade low"*, *"first since"*, *"only"*, *"more than any"*.
3. **Zero banned phrases?** Run against §2.3.
4. **Real attribution available for the body?** §2.5 forms must resolve.
5. **Voice fit?** If you swap program name out and headline still reads, voice hasn't bitten — pull from `profile.voice_register` and rewrite.

### 2.10 House example (250w, in-voice Alabama Pulse post-Tennessee one-point loss)

> **Tuscaloosa lost a game it didn't lose.**
>
> Tennessee 24, Alabama 23. The fourth-quarter possession was eleven plays for forty-two yards and one missed kick. Jalen Milroe was 22-of-31 for 287 and a touchdown that didn't count because a tackle was lined up two feet behind the ball. The Third Saturday's all-time series ledger moved one tick the wrong direction and nothing else about Alabama actually moved.
>
> The two cohorts in the fanbase are now eleven ranks apart on where this team finishes. The stat folks have Alabama at #6 — same SP+ as the Saturday before, same explosive-play rate (14.1%, top-three nationally), same secondary tackling grade (no change). The boards have Alabama at #17 — Tide 100's Sunday morning thread was the platform's longest of the year and the most-quoted post was *"the standard isn't kicking field goals."*
>
> Both readings are correct. The model is reading the season; the boards are reading the eight minutes of clock that decided it.
>
> DeBoer's third-and-long defense is still the best in Tuscaloosa since 2020. The Heisman board still has Milroe in the top six. The CFP path didn't actually close — a one-loss SEC champion has been in every twelve-team field projected this fall. What changed is the temperature of the room, and the temperature of the room is a real signal in Tuscaloosa specifically — this is the fanbase that turned on Mike Shula in 48 hours and turned on Steve Sarkisian's playcall in 48 minutes.
>
> The process does not flinch at rankings. The standard does.
>
> *— The Editors, Cohort Desk · cohort divergence · analytics vs boards*

---

## Part 3 · Mobile-First Substrate

### 3.1 The mobile design system foundation

#### Type scale (mobile-floor of v3 clamp scale)

| Token | Mobile floor | Desktop ceiling | Use |
|---|---:|---:|---|
| `--fs-hero` | 32px | 56px | Team-page wordmark, edition cover |
| `--fs-display` | 24px | 40px | Section H2 |
| `--fs-headline` | 19px | 24px | Module H3 |
| `--fs-headline-sm` | 16px | 18px | Card titles |
| `--fs-body-serif` | 17px | 18px | Editorial prose |
| `--fs-body-ui` | 15px | 15px | UI labels |
| `--fs-label` | 11px | 12px | Eyebrows, chip labels |
| `--fs-mono-data` | 13px | 14px | JetBrains Mono numerals |

Implementation: `clamp(<mobile>, <vw>, <desktop>)` — vw is 2.5vw for `--fs-hero`, 1.5vw for `--fs-display`, 1vw for `--fs-headline`. **Mobile floors anchor to 375px iPhone SE, not "what looks ok at 720px."**

#### Spacing tokens

Add to `tokens.css`:

```css
:root {
  --m-gutter: 16px;
  --m-mod-gap: 24px;
  --m-card-pad: 14px;
  --touch-min: 44px;
  --touch-comfort: 48px;
  --bottom-nav-h: 64px;
  --bottom-nav-clearance: calc(var(--bottom-nav-h) + env(safe-area-inset-bottom));
  --m-sticky-top: 44px;
  --m-sticky-anchor: 36px;
}
@media (min-width: 720px) {
  :root { --m-gutter: 24px; --m-mod-gap: 40px; --m-card-pad: 24px; }
}
```

#### Sticky-element hierarchy (max one per page)

1. **Bottom nav** (always, fixed, ~64px + safe-area)
2. **Page-context bar** — sticky-top, 44px, page title + contextual action (filter/share/edition selector)
3. **Section anchor strip** — only on Hub, Team, Editions, Methodology. 36px horizontal-scroll chips
4. **Read-progress hairline** — 2px gradient, on long-form editorial only

Multiple sticky bars stacked is the #1 mobile design failure mode.

### 3.2 Mobile navigation redesign (5-slot Phosphor + drawer)

Replace the current emoji bottom-nav with 5 Phosphor glyphs:

| Slot | Glyph | Label | Destination | Rationale |
|---|---|---|---|---|
| 1 | `House` | Home | `/` | Anchor, escape hatch |
| 2 | `ListNumbers` | Rank | `/rankings/` | Highest-traffic surface |
| 3 | `Pulse` | **Hub** | `/hub/` | Crown jewel — center slot |
| 4 | `Newspaper` | Wire | `/wire/` | Daily-return product |
| 5 | `DotsThree` | More | (opens drawer) | All other 13 destinations |

**Active-state encoding (three signals stacked, not one):**
1. Glyph fill: muted → `--gold-october`
2. Label color: `--wcfb-fg-muted` → `--wcfb-fg-primary`
3. 2px `--gold-october` rule flush with bar's top edge, full slot width

Three signals prevent the colorblind accessibility failure.

**Hamburger drawer (`<dialog>`):** opens at 85% viewport from bottom (bottom-nav visible underneath as orientation anchor). Three groups:

- **Daily intake (4):** Daily · Wire · Reactions · Mailbag
- **The work (5):** Rankings · Hub · Compare · Conferences · Heisman
- **The library (5):** Canon · Storylines · Editions · Players · Methodology

Top 60px is `SearchTeams` field with client-side autocomplete from 134-FBS-team JSON (~8KB).

**Contextual rotation:** Editions surface rotates slot 4 to "Edition" (`BookOpen` glyph) exposing Edition-TOC. Team page rotates slot 4 to "Team-jump" opening section-anchor strip. One level deep only.

**Top brand bar removed on mobile.** Replace with 44px **page-context bar**: left = `CaretLeft` back, center = page title 14px Inter Medium truncated middle, right = contextual action.

### 3.3 Mobile-specific patterns (B.1–B.6)

**B.1 Wire on mobile — swipeable cards, not 110-row table**

Each row → 96px-tall card:
- 4px left stripe encodes IMPACT (red MAJOR / amber MINOR / blue MOVES-CONF)
- 32px team logo
- 2-line action text
- Source chip + impact chip stacked
- Right-arrow chevron suggests tap-to-detail

Filter chips → **bottom sheet** (triggered from page-context bar's `Funnel` glyph + count badge). Sheet: segmented IMPACT control, conference multi-select chip rail (horizontal scroll), date range segmented, source multi-select. Sticky "Reset" / "Apply (N)" at sheet bottom.

Pull-to-refresh native pattern. Infinite scroll with sentinel at row 50, "showing 50 of 312 events" footer counter.

**B.2 Rankings on mobile — sort dropdown + filter sheet**

Sort dropdown sheet (8 sort options, persistent). Filter sheet identical pattern to Wire — Conference, Level, Range, Bowl-eligible toggle. 12 chips not 75.

Row format (72px tall): Bowlby One SC rank numeral 28px · 32px logo · team name + record on row 1 · conference + composite metric on row 2 · 4px Mood Ribbon segment (last 5 weeks) on row 3 · movement indicator (Phosphor `CaretUp` + delta).

Each row is the tap target — 72px exceeds 44px floor.

**B.3 Compare on mobile — tabbed single-pane with swipe**

```
[Team A picker]  [Team B picker]
─────────────────────────────────
| ● Alabama   | ○ Auburn   |    ← tabs
─────────────────────────────────
[active team's pane content]
```

Persistent **metric strip** at top of pane: 8 mini-metrics where each metric shows *both* teams' values inline (`SP+: 18.4 vs 9.1 →`), color-coded by who's ahead. This is the comparison's editorial payoff — visible without swiping.

CSS scroll-snap (no JS library) — `scroll-snap-type: x mandatory`.

**B.4 Team page on mobile — stack, don't tab**

Tab interfaces lose 60% of users at the first tab (Nielsen Norman 2023). Stack vertically in this order:

1. Conference top-rule (3px)
2. Helmet-stripe band (80px)
3. Page-context bar substitute: sticky 44px with section anchor strip (7 chips: Pulse · Savant · Schedule · Roster · History · Rivalry · Honors)
4. Pulse (Mood Ribbon + Divergence Dumbbell — 200px)
5. Receipt Strip (80px)
6. Savant Card (580px — full credibility module, not teaser)
7. Schedule (~432px)
8. Era Strip (280px)
9. Rivalry card (360px)
10. Honors trophy shelf (160px)
11. Footer

Total scroll ~2,400px. Every signature visualization reachable in 4 thumb-flicks.

**B.5 Editions cover essay on mobile — no pinned cinematic**

GSAP scroll-scrub is **desktop-only** (768px+ media query). Mobile gets graceful degradation:

- Static cover hero (320px tall, 16:10), edition number in Bowlby 64px, title in Recoleta Stencil 32px, lede in Charter 17px/1.55
- Section anchor strip (sticky after cover scrolls past): roman numerals **I · II · III · IV · V**, each tap scrolls to that desk's anchor
- Body: stacked desk sections, each opened by `<details>` accordion below first paragraph

**B.6 Hub on mobile — virtualize 28 charts via section anchors**

6 sections become anchor chips in sticky strip. Charts render as low-detail SVG placeholder (title + caption + 80px ghost outline) by default. IntersectionObserver hydrates full chart when within 1 viewport. Once hydrated, stays hydrated.

### 3.4 Per-surface mobile compositions (above-the-fold at 375×667)

Each page's above-the-fold spec is in v4 Investigator C's full output. Key inflection points:

- **Homepage:** Helmet-stripe band → date eyebrow → hero (240px) → section anchors → "What's Live" rail teases (3 cards visible)
- **Team page:** Conference rule → helmet-stripe band → section anchors → Mood Ribbon + top half of Divergence Dumbbell + Pulse caption-headline = 343px (editorial frame above fold)
- **Wire:** Page-context bar + active-filter chips + 5 wire cards × 96px = 556px (full thumb)
- **Hub:** Section anchors + first chart placeholder (charts hydrate on scroll)
- **Methodology:** Page masthead + intro lede + first chart placeholder + sticky in-page TOC

### 3.5 Mobile accessibility

- **Reduced-motion:** all `transition` / `animation` / `transform` rules live inside `@media (prefers-reduced-motion: no-preference)` wrapper. **Reverse the polarity** from "declare always, suppress conditionally."
- Scrollytelling JS init returns early if `window.matchMedia('(prefers-reduced-motion: reduce)').matches`.
- **Touch-target floor: 44×44.** Audit Rankings filter chips (currently 24px), Wire IMPACT labels, footer link clusters, Mailbag expand carets.
- **Screen-reader landmarks.** Bottom nav `<nav aria-label="Primary">`, each tab `aria-current="page"` when active. Drawer `<dialog>` (HTML-native focus-trap + Escape). Filter sheets `<dialog aria-label="Filters">`.
- **Pinch-zoom: never block.** Verify viewport meta does NOT include `maximum-scale=1` or `user-scalable=no`. Layout must reflow at 200% zoom without horizontal scroll.

### 3.6 The 5 highest-impact mobile fixes (~9 dev-days)

| # | Fix | Days | Files |
|---|---|---|---|
| 1 | Replace emoji bottom nav with 5-slot Phosphor + drawer | 1.5 | `wcfb-enhancements.css:282-328`, `reporting.py` chrome helper, new `phosphor.svg` |
| 2 | Wire 110-row table → swipeable cards + filter sheet | 3 | `wire/renderer.py` (453 lines), `wcfb-enhancements.css`, new `wcfb-filter-sheet.js` (~3KB) |
| 3 | Mobile type scale + spacing tokens added to `tokens.css` | 0.5 | `team_pages/assets/tokens.css`, `wcfb-enhancements.css` |
| 4 | Filter-sheet pattern for Rankings | 2 | `reporting.py` rankings filters, `wcfb-enhancements.css` |
| 5 | `_render_head_chrome()` helper + critical-CSS extraction | 2 | New `common/head_chrome.py`; route every renderer through it; externalize team-page CSS |

---

## Part 4 · Motion Choreography

### 4.1 Token system (final)

**5 easing curves:**

| Token | cubic-bezier | Use | Emotion |
|---|---|---|---|
| `--ease-brass-band` | `cubic-bezier(0.4, 0.0, 0.2, 1)` | Default state transitions (hover, focus, active) | Marching-band step cadence |
| `--ease-snap` | `cubic-bezier(0.2, 0.0, 0.0, 1.0)` | Reveals, IO entries | Curtain rising |
| `--ease-press` | `cubic-bezier(0.4, 0.0, 1.0, 1.0)` | Active / pressed states | Pad-collapse — weight transferring |
| `--ease-data` | `cubic-bezier(0.16, 1, 0.3, 1)` | Chart draws, percentile bar fills | Stat resolving |
| `--ease-delight` | `cubic-bezier(0.34, 1.20, 0.64, 1.0)` | Receipt verdict, Dumbbell threshold pulse | The "got it right" half-smile. Never above 0.22 overshoot |

**7 durations:**

| Token | ms | Use |
|---|---:|---|
| `--dur-instant` | 80 | Tap acknowledgment, focus ring snap |
| `--dur-state` | 180 | Hover lifts, color shifts |
| `--dur-brass` | 220 | **Default transition duration** |
| `--dur-reveal` | 320 | Single-element IntersectionObserver entry |
| `--dur-data-short` | 420 | Sparkline, single percentile bar |
| `--dur-data-long` | 680 | Mood Ribbon 52-bar build, Bump chart |
| `--dur-delight` | 800 | Receipt verdict, page-turn, hero reveal |

**4 staggers:**

```
--stagger-tight: 24ms       /* same-row chips, table cells, ribbon bars */
--stagger-default: 56ms     /* card grids */
--stagger-editorial: 96ms   /* hero stack, page-load sequence */
--stagger-bump: 140ms       /* bump-chart per rank line */
```

### 4.2 Hover / focus / active / disabled per element type

Every transition declares **specific properties** (never `transition: all`).

| Element | Hover | Focus-visible | Active | Disabled |
|---|---|---|---|---|
| Button (primary) | `translateY(-1px)`, background +4% luminance, `--motion-state` | 2px `var(--accent-primary)` ring 2px offset, fade 80ms `--ease-snap` | `scale(0.97)` 80ms `--ease-press` | `opacity: 0.42; cursor: not-allowed` |
| Button (ghost) | `border-color` + `color` to accent, 180ms `--ease-brass-band` | Same ring | `scale(0.98)` 80ms | Same |
| Link (inline editorial) | `text-decoration-color` fades 0.3→1.0 alpha, 180ms | 2px ring 1px offset, ring = link color | No transform | `color: var(--ink-muted); pointer-events: none` |
| Card | `translateY(-2px)`, border-color to accent 0.6α, `filter: drop-shadow(0 12px 28px rgba(0,0,0,0.22))`, 220ms `--ease-brass-band` | Outline 2px outside border, 3px offset | `translateY(0) scale(0.995)` 100ms | `opacity: 0.55; filter: grayscale(0.4)` |
| Chip | `background-color` shift, `--motion-state` | 2px ring inside chip pill 80ms | Background to selected instantly (0ms) | `opacity: 0.45` |
| Tab | `color` to ink-primary; underline grows 0→100% width 220ms `--ease-snap`, anchored on hover side | 2px ring around label | Underline snaps full instantly; content cross-fade 180ms | `opacity: 0.4; pointer-events: none` |
| Table row | `background-color` → `rgba(var(--accent-rgb), 0.06)`, 180ms | 2px left border in accent, no offset | `background-color` darken 4% 80ms | `opacity: 0.5`, no hover |
| Nav item | `color` shift + 1px underline draw L→R 220ms | 2px ring + 1px offset using `--accent-primary` | Underline anchors solid | `opacity: 0.5` |
| Sort header | `color` to ink-primary; arrow glyph fades 0.3→1.0 180ms | 2px ring on `<th>` content | Arrow rotates 180° 220ms `--ease-brass-band`; row reorder uses §4.4 FLIP | Inactive sort: arrow 0.25α |

**Universal rule:** every focus ring uses `outline` (not `box-shadow`) so it composites without forcing layout.

### 4.3 Page-load reveal sequence (t = 0 → 800ms)

```
t=0      Above-fold static present (HTML rendered, no opacity tricks)
         Hero background tint fade-in 240ms ease-snap
         Hero photo (if present) crossfades 320ms once decoded

t=80     Hero title (h1, jersey-block) fade + translateY(8px→0), 320ms ease-snap
t=176    Hero subtitle fade + translateY(6px→0), 280ms ease-snap
t=272    Source Trust Ribbon slides from -8px, 260ms ease-snap

t=368    Hero metric tile #1 fade + translateY(12px→0), 300ms ease-snap
t=424      tile #2 (stagger 56ms)
t=480      tile #3
t=536      tile #4

t=632    Pulse module ribbon container fade-in (opacity 0→1), 200ms snap
t=712    Pulse data-ribbon fill animation begins

t≥800    Below-fold content blocked on IntersectionObserver
         Footer marching-band trim: SVG stroke-dashoffset 600ms ease-data
         on first paint only, fires when footer crosses 90% viewport
```

**No element shifts layout during sequence.** All entries use `transform` + `opacity` only. Reserved space allocated at t=0.

### 4.4 Scroll-tied animations (GSAP for must-have-3, Scrollama elsewhere)

**Editions pinned cinematic intro (GSAP ScrollTrigger).** Pin for 100vh of scroll. Four beats scrubbed by scroll position. Beat 1 (0-22%): week label morphs in. Beat 2 (22-48%): hero stat counts up, photo desaturates 100→28%. Beat 3 (48-78%): overlay headline drops from translateY(-32px)→0. Beat 4 (78-100%): unpin; overlay fades. **Disabled at <768px.**

**Inline chart entries (IntersectionObserver).** Threshold 0.15; fires once (`unobserve` after).

**Player career-arc DrawSVG (GSAP scrubbed).** Path's `stroke-dashoffset` maps linearly from `pathLength` (top) → `0` (bottom). No easing on scrub itself.

**Dynasty heatmap progressive fill (Scrollama + CSS).** Column-major L→R order. 80ms stagger between columns; within column, rows fill simultaneously. Each cell `background-color` from `var(--surface-2)` to data color, 280ms `--ease-data`.

**Mood Ribbon reveal (IntersectionObserver, block-staggered).** 52 bars, each grows `height: 0→final` 320ms `--ease-data`, stagger 24ms. Total 1568ms — the longest single reveal, owned by the brand.

### 4.5 Chart entry animations (per pattern)

| Pattern | Choreography | Total ms |
|---|---|---:|
| Sparkline | `stroke-dashoffset: pathLength→0`, `--ease-data` | 420 |
| Percentile bar | `width: 0→value%` from left; tick fades at t+200ms | 420 |
| Divergence dumbbell | Dots fade-in + scale 0.6→1; rod extends scaleX 0→1 from program-side at t+160ms | 480 |
| Bump chart | Lines draw L→R `stroke-dashoffset`; per-rank stagger 140ms each 520ms `--ease-data` | 1640 (8 lines cap) |
| Mood ribbon | Bars grow bottom-up; stagger 24ms each 320ms `--ease-data` | 1568 |
| Heatmap | Column-major L→R 80ms stagger each cell 280ms `--ease-data` | 1240 |
| Era Strip | Segments `clip-path: inset(0 100% 0 0)→inset(0 0 0 0)` L→R 80ms stagger each 380ms | 860 |
| Savant card | 8 bars L→R 24ms stagger each 420ms `--ease-data` | 612 |
| Win-prob timeline | Path L→R 680ms `--ease-data`; event markers pop in at their x | 680 |
| Cohort Divergence | Axis appears 80ms; capsule slides translateX 420ms `--ease-data`; Δ counts up parallel | 500 |

All chart entries fire on IntersectionObserver threshold 0.15. Target **total chart resolution under 800ms** (Mood Ribbon excepted).

### 4.6 Data-update animations (toggle peer-set, change year, sort, filter)

| Update | Choreography | ms |
|---|---|---:|
| Numeric count-up | Tween old→new with `--ease-data` | 480 |
| Bar width change | `width` (or `scaleX`) transitions with `--motion-data` | 420 |
| Bar reorder (sort) | FLIP technique: capture, inverse transform, animate `transform: none` with `--ease-brass-band` | 320 |
| Filter toggle | Bars not in filter: `opacity 1→0.18, filter: saturate(0.2)`; in-filter brighten in parallel 220ms `--ease-brass-band` | 220 |
| Era Strip year-pick | Cross-fade in place: outgoing 1→0, incoming 0→1 240ms `--ease-snap` simultaneous | 240 |

**Springs are never used for data updates.** Spring overshoot misreads as "the number bounced" — on a stat card it implies imprecision. Springs reserved for §4.8 micro-delights.

### 4.7 Sticky element behaviors

**Read-progress bar.** `scrollY > 80px` activates. Bar's `width` bound to `scrollY / (documentHeight - viewportHeight)` — direct mapping, no easing. Container fade-in 200ms `--ease-snap`. Background `var(--paper)` 0.92α with `backdrop-filter: blur(12px) saturate(140%)`.

**Sticky source-trust ribbon (team pages).** Activates when hero 80% scrolled past. Position fixed top:0. Background goes card → frosted (`backdrop-filter: blur(10px)`, `rgba(var(--paper-rgb), 0.86)`), `--motion-state` transition.

**Sticky section anchors.** `position: sticky; top: var(--read-progress-height)`. Active anchor's underline slides L→R 220ms `--ease-brass-band`. Linear, no spring.

### 4.8 View Transitions API + page transitions

Use where supported. Default cross-fade 280ms `--ease-snap` via `document.startViewTransition()`.

**Named transitions:**
- `view-transition-name: hero-team-logo` on team-page hero crest → carries across when navigating between profiled teams
- `view-transition-name: edition-cover` on Editions cards → expands into edition's cover on click. 420ms `--ease-snap`
- `view-transition-name: canon-entry-header` on Canon list rows → continues into entry detail title

**Fallback (no View Transitions):** `opacity 1→0` 140ms outgoing, `0→1` 240ms incoming.

**Team-color tint crossfade:** Between profiled team pages, `--bg-tint` on `<body>` animates via `background-color` transition 320ms `--ease-snap` before new content paints. `prefers-reduced-motion: reduce` skips — switches instantly.

### 4.9 Three micro-delight moments

All three use `--ease-delight` with overshoot exactly 0.20.

1. **Receipt Strip verdict resolves.** Tile starts `opacity: 0, scale(0.86)`. At reveal: `opacity 1, scale 1.0`, 420ms `--ease-delight`. Phosphor checkmark draws via `stroke-dashoffset` 320ms `--ease-data`, starting +120ms. Total 440ms.
2. **Cohort Divergence Dumbbell Δ-exceeds-threshold pulse.** When |Δ| > 2σ, program dot pulses **once**: `scale(1)→scale(1.18)→scale(1)` 600ms custom keyframe + `filter: drop-shadow` glow 0→0.4→0α. Fires once on chart entry.
3. **Pulse module beats prior baseline.** When current week's mood exceeds prior 4-week rolling baseline by >1σ: latest bar gets 1.2s glow cycle. Fires twice with 600ms gap, then stops.

### 4.10 Reduced-motion override matrix

`@media (prefers-reduced-motion: reduce)` block. **Critical fix from v2:** all `--motion-*` declarations must live inside this block (v2 found 15 declarations firing despite reduce).

```css
@media (prefers-reduced-motion: reduce) {
  :root {
    --dur-instant: 0ms; --dur-state: 0ms; --dur-brass: 0ms;
    --dur-reveal: 0ms; --dur-data-short: 0ms; --dur-data-long: 0ms;
    --dur-delight: 0ms;
    --stagger-tight: 0ms; --stagger-default: 0ms;
    --stagger-editorial: 0ms; --stagger-bump: 0ms;
  }
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

JS-side: `motion.js` checks `window.matchMedia('(prefers-reduced-motion: reduce)').matches` before instantiating Scrollama / GSAP. If true, IO runs but only toggles `.is-visible` (no animation; CSS handles final state). GSAP ScrollTrigger pins are `.disable()`d.

All 3 micro-delights **disabled entirely** with reduce. Editions pinned cinematic — **pin disabled**; section scrolls normally with statics. Career-arc — appears fully drawn at t=0. Heatmap — all cells final color at t=0.

### 4.11 The 220ms brass-band rule (corrected)

Competitive marching bands march at 120 BPM with 8-to-5 stride. 60,000ms ÷ 120 = 500ms per beat. **An 8-to-5 step = one beat = 500ms.** v3's claim of "8-to-5 step = 250ms" was the half-beat (sixteenth-notes at 120 BPM, faster show-band styles).

**Reconciled rule:** 220ms is just under one half-beat (250ms). Reads as "between half-steps" — slightly faster than half-beat, decisively slower than sixteenth. Emotionally: measured roll-step, never sprint. Keep 220ms; don't claim mathematical derivation in copy.

### 4.12 Forbidden motion patterns

1. `transition: all` — forces layout-thrashing
2. Bouncy easing with overshoot > 0.22
3. Animating `box-shadow` — repaints every frame. Use `filter: drop-shadow()` on parent
4. Animating `width` / `height` / `top` / `left` for layout-changing entries. Use `transform: scaleX` / `translateY`
5. **Duration ceilings:** state never > 320ms (target 180-220), reveal never > 800ms (target 280-420), delight never > 1200ms (target 400-800). Mood Ribbon's 1568ms is the documented exception.
6. Spinning loaders. Use skeleton screens (1.6s `--ease-brass-band` shimmer)
7. Parallax translating > 12% of element's height (WCAG 2.3.3 motion-sickness)
8. Auto-play motion looping > 2× without user input
9. Hover effects changing layout (border-width changes pushing neighbors)
10. `scroll-behavior: smooth` globally — apply only to in-page anchors
11. Mixing `--ease-press` with reveals or `--ease-delight` with state — each ease has one role

---

## Part 5 · Share Cards + SEO + Structured Data

### 5.1 Universal OG card spec

- **Canvas:** 1200×630 (OG/Twitter/LinkedIn/Slack/Discord baseline) — PNG
- **Retina for iMessage:** 2400×1260 (iMessage requires 2400×1260 for reliable full-width rendering — 1200×630 falls back to thumb-card). Emit both. `og:image` points to 2400×1260
- **Safe area:** 80px padding all sides; critical content inside center 66% to survive Slack/iMessage square-crop
- **Color mode:** wool-dark by default (iMessage opens dark mode for ~70% of users)
- **Wordmark lockup bottom-left, every card:** "THE CFB INDEX" in Inter Display 22px, letter-spacing 0.4em, `--gold-october` on wool, `--ink` on paper
- **Conference top-rule:** 6px band at top, conference color per `COLORS["conf_*"]`. No conference → gold_october
- **Typography pair:** Bowlby One SC display, Charter body, Inter Display metadata

### 5.2 Per-surface card compositions

| Surface | Ground | Headline | Imagery |
|---|---|---|---|
| Homepage | wool-dark | "Week 11 · The Index" Bowlby 96px | Mood-trajectory sparkline 40% opacity behind |
| Editions cover | wool-dark | Issue title Recoleta Stencil 88px italic | Roman numeral 280px height 8% opacity top-right + viz panel 40% width right |
| Team page (profiled) | program-tint gradient | Program name Bowlby 120px | Team logo 240×240 top-right (alpha PNG) + helmet-stripe motif 6px rule across middle |
| Player canon entry | wool-dark | Player surname Bowlby 120px, given name Charter italic 36px above | Headshot 360px circle right + Accolade Lens 4-capsule bottom |
| Wire entry | destination-team tint | Player name Bowlby 96px | Origin-school logo → arrow → destination-school logo (both 96×96) |
| Daily story | paper-cream | Headline Charter italic 64px max 3 lines | Featured scorecard bottom-right + mood-movers sparkline 360×60 bottom |
| Reaction story | program-tint with diagonal seam if rivalry | Game result Bowlby 88px | 2 team logos 160×160 separated by seam + Cohort Divergence Dumbbell 400×80 bottom |
| Storyline thread | wool-dark | Title Recoleta Stencil 80px | Arc chart 30% opacity behind + beat-writer headshot 96px bottom-left |
| Mailbag question | paper-cream | Question Charter italic 56px + 120px gold open-quote glyph | Type-led, no image |
| Methodology | wool-dark | Section name Bowlby 96px | Source brand-mark grid 5×2 at 24% opacity behind |

### 5.3 The Pillow pipeline (`src/cfb_rankings/share_cards/`)

```
share_cards/
  __init__.py                  # render_card(page_type, page_data) -> Path
  renderer.py
  templates/
    base.py                    # _draw_wordmark, _draw_conference_rule, _draw_safe_area
    homepage.py
    editions_cover.py
    team_page.py
    player_canon.py
    wire_entry.py
    daily_story.py
    reaction_story.py
    storyline_thread.py
    mailbag_question.py
    methodology.py
  fonts.py                     # FONT_CACHE singleton @ import
  assets.py                    # logo + headshot loader with PIL.Image.open cache
  paths.py                     # output_path_for(page_type, slug) -> Path
```

Font registration once at import via `@lru_cache(maxsize=128)` on `font(family, size, italic=False)` returning `ImageFont.FreeTypeFont` with `layout_engine=ImageFont.Layout.RAQM`.

**Cache strategy.** Key by `sha1((template_id, data_dict_canonical_json, FONT_VERSION))` stored as `share-cards/{type}/{slug}.png.meta.json`. On every `build-site`, compute new hash; skip if match. Regenerate when: team primary_color changes, record/rank changes, new Edition publishes, player honor added, Wire entry created.

**Output path:** `output/site/assets/share-cards/{type}/{slug}.png` — flat, deterministic. Date-keyed for Daily/Mailbag (`share-cards/daily/2026-11-08.png`).

### 5.4 The `render_head_chrome()` helper

Single function at `src/cfb_rankings/common/head_chrome.py`. Replaces existing `_meta_tags()` at `reporting.py:13755`.

```python
def render_head_chrome(
    page_type: Literal["home","team","player","editions","wire","daily",
                       "reaction","storyline","mailbag","methodology","canon"],
    page_data: dict,
    *, base_url: str = "https://cfbindex.com",
) -> str: ...
```

**Emits in order:**
- charset, viewport, theme-color (per `prefers-color-scheme`), color-scheme
- `<title>` (per page-type template — see §5.5)
- description (155-char target, 160 hard cap)
- `<link rel="canonical">`
- Open Graph (site_name, type, title, description, image absolute HTTPS, image:width=2400, image:height=1260, image:alt, url, locale)
- Twitter Card (`summary_large_image`, site, title, description, image, image:alt)
- Font preloads (charter-var.woff2 + inter-var.woff2 + bowlby-one-sc.woff2)
- `<link rel="stylesheet" href="/assets/fonts.css">` + `tokens.css`
- Feed discovery — RSS + Atom + JSON Feed `<link rel="alternate">` per editorial surface
- `<link rel="sitemap" type="application/xml" href="/sitemap-index.xml">`
- JSON-LD structured data block (per page type, see §5.6)

### 5.5 Title templates per page type

| Type | Template |
|---|---|
| home | `The CFB Index — Where the data and the eye test disagree` |
| team | `{Program} {Mascot} — CFB Index` |
| player | `{Given} {Surname} — {Position}, {School} — CFB Index` |
| editions | `Issue {roman}: {Title} — CFB Index Editions` |
| wire | `{Player} transfers to {Destination} — The Wire` |
| daily | `The Daily — {weekday}, {date}` |
| reaction | `{Winner} {ws}, {Loser} {ls}: Reaction — CFB Index` |
| storyline | `{Title} — Storyline — CFB Index` |
| mailbag | `Mailbag: {Question-truncated-50ch} — CFB Index` |
| methodology | `{Section} — Methodology — CFB Index` |

### 5.6 JSON-LD per page type

**Team page** — `SportsTeam` + `Article` `@graph`:

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SportsTeam",
      "@id": "https://cfbindex.com/teams/alabama#team",
      "name": "Alabama Crimson Tide", "sport": "American Football",
      "url": "https://cfbindex.com/teams/alabama.html",
      "logo": "https://cfbindex.com/assets/logos/alabama.png",
      "image": "https://cfbindex.com/assets/share-cards/teams/alabama.png",
      "homeLocation": {"@type": "Place", "name": "Bryant–Denny Stadium",
        "address": {"@type": "PostalAddress", "addressLocality": "Tuscaloosa",
                    "addressRegion": "AL", "addressCountry": "US"}},
      "memberOf": [{"@type": "SportsOrganization", "name": "NCAA Division I FBS"},
                   {"@type": "SportsOrganization", "name": "Southeastern Conference"}],
      "coach": {"@type": "Person", "name": "Kalen DeBoer", "jobTitle": "Head Coach"}
    },
    {
      "@type": "Article",
      "mainEntityOfPage": "https://cfbindex.com/teams/alabama.html",
      "headline": "Alabama Crimson Tide — CFB Index",
      "image": "https://cfbindex.com/assets/share-cards/teams/alabama.png",
      "datePublished": "2025-08-23T00:00:00Z",
      "dateModified": "2026-11-08T14:22:00Z",
      "about": {"@id": "https://cfbindex.com/teams/alabama#team"},
      "publisher": {"@id": "https://cfbindex.com/#org"}
    }
  ]
}
```

**Other schemas:** `Person + Article` for player canon entry, `NewsArticle` for Editions / Wire / Daily / Reactions, `WebPage + BreadcrumbList` for methodology, `Organization + WebSite` for root site (with `SearchAction` potential action).

### 5.7 Sitemap strategy at 69k pages

**Topology:** one `/sitemap-index.xml` → references 8 shard sitemaps. None exceed 50k URLs at current scale.

```
/sitemap-index.xml                  (8 children, ~1KB)
/sitemap-teams.xml                  (~679 slugs × seasons → ~5k URLs)
/sitemap-players.xml                (~25k player canon entries)
/sitemap-editions.xml               (~50 editions + sub-pages)
/sitemap-wire.xml                   (~8k wire entries)
/sitemap-canon.xml                  (~400 URLs)
/sitemap-storylines.xml             (~200 storylines + children)
/sitemap-methodology.xml            (~30 URLs)
/sitemap-news.xml                   (Google News sitemap: last 48h Daily/Reactions/Wire)
```

**Priority + changefreq matrix:**

| Sitemap | priority | changefreq | lastmod source |
|---|---:|---|---|
| teams | 0.9 | weekly | `team_pages_meta.updated_at` |
| players | 0.7 | weekly | `player_canon.last_honor_added_at` |
| editions | 1.0 | weekly | `editions.published_at` |
| wire | 0.8 | daily | `wire_entries.created_at` (immutable) |
| canon | 0.7 | weekly | `canon_lists.last_revised_at` |
| storylines | 0.8 | daily in-season, weekly off | MAX of children |
| methodology | 0.5 | monthly | git commit time |
| news | n/a | n/a | last 48h only |

**Lastmod plumbing — recommended addition:** add `page_lastmod (page_url, lastmod_utc)` table populated by each renderer at write time. ~5 LOC per renderer.

**Builder:** `python manage.py build-sitemap` — new CLI subcommand. Writes all 9 files. Gzip on by default for sitemaps >5MB. Adds `Sitemap: https://cfbindex.com/sitemap-index.xml` to `/robots.txt`.

### 5.8 RSS feed system

One feed per editorial surface, three formats each — 12 feed files. **Recommend Atom 1.0 as canonical**, RSS 2.0 compatibility, JSON Feed 1.1 bonus.

```
/feed/editions.{xml,atom,json}
/feed/daily.{xml,atom,json}
/feed/wire.{xml,atom,json}
/feed/storylines.{xml,atom,json}
```

Item structure includes `<media:thumbnail>` pointing at the OG card. Feed discovery via `<link rel="alternate">` in `<head>` (page-type-filtered).

Builder: `python manage.py build-feeds`. Limits each feed to most-recent 50 items.

### 5.9 The 10 fixes to current `<head>`

Audit of `_meta_tags()` at `reporting.py:13755`:

1. **No `<link rel="canonical">`** — phantom URL variants getting indexed
2. **`og:image` is relative `og-image.svg`** — per OG spec MUST be absolute HTTPS; Bluesky / Discord / Slack silently drop relative
3. **No `og:url`** — Bluesky CardyB and Discord use this to dedupe and display source domain
4. **No `theme-color`** — Discord uses this for embed's signature left border
5. **No `<title>` in `_meta_tags()`** — page title set elsewhere or not at all. Confirm every renderer uses `render_head_chrome()`
6. **No JSON-LD anywhere** — zero structured data across 69k pages. **Single biggest SEO win available.** Google Knowledge Graph can't recognize Alabama as `SportsTeam`, players as `Person`, Editions as `NewsArticle`
7. **OG image is SVG, not PNG** — `_render_og_image_svg` writes SVG inline, but **iMessage, Discord, and Bluesky do not render SVG OG images.** Move to Pillow PNG
8. **No `og:image:alt`** — required for accessibility + Slack screen reader integrations
9. **No `<meta name="viewport">`** — without it iOS Safari sets 980px layout viewport
10. **No feed discovery** — even if RSS feeds get built, without `<link rel="alternate">` browser feed-detection extensions and IFTTT-style aggregators can't find them

**Bonus #11:** current `_meta_tags()` doesn't accept page-type discriminator. Replacement `render_head_chrome(page_type, page_data)` is the load-bearing refactor for all 10 above.

---

## Part 6 · Governance + Performance Budgets

### 6.1 Eight `manage.py audit-*` subcommands

Each is a leaf module under `src/cfb_rankings/audit/`. Returns exit code 0/1. CI chains them sequentially with `set -e`. Total runtime <90s on `output/site/`.

| Command | What it does |
|---|---|
| `audit-tokens` | Fail if any module CSS contains a color literal not in `design_tokens.py`. Regex `#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(`. Allowlist: `viz_templates/`, `# token-exempt` comments. |
| `audit-fonts` | Every HTML page must `<link rel="preload">` Charter + Inter and load `/assets/fonts.css`. Must NOT declare CSS `font-family` starting with `Times New Roman` / `Times` / `serif` unqualified. v2 found 3 pages bypassing — gate refuses to ship those. |
| `audit-dead-code` | AST sweep on `reporting.py` + siblings. Finds `FunctionDef` / `ClassDef` defined but never referenced + not exported from `__init__.py` + not matched by allowlist (CLI / Flask / `@cli.command` decorators). v3 flagged `_render_history_*` and `_render_player_*` orphans — this audit makes their continued existence a build failure. |
| `audit-images` | Parses every HTML with `lxml`; collects every `<img src>`, `srcset`, CSS `url()`, `<source srcset>`. Resolves against local `output/site/assets/` + R2 imagery manifest. Fails on 404. |
| `audit-headings` | Fail on (a) any page with no `<h1>`, (b) multiple `<h1>` on one page, (c) `h1→h3` jumps skipping `h2`, (d) headings with only icon glyphs / `&nbsp;` / empty text. |
| `audit-aria` | (1) Every `<img>` has `alt` (empty allowed for decorative — must be `alt=""`). (2) Every `<button>`, `<a role=button>`, `<input type=button|submit>`, and label-less `<input>` has text content OR `aria-label` OR `aria-labelledby`. (3) Every `role="tablist"` contains only `role="tab"` children with `aria-selected` (not `aria-pressed`). |
| `audit-perf` | Measures bytes of inline `<style>` + inline `<script>` + total HTML + external stylesheet count + image count. Compares against `audit/perf-budgets.json`. Fails any page exceeding budget. v2 measured ~300KB inline-CSS dupe on team pages — this gate prevents reintroduction. |
| `audit-tokens-drift` | Compares canonical `design_tokens.py` against shipped CSS variables in `tokens.css` + design-system docs. Reports drift in either direction. `--allow-drift=N` for incremental migration. |

**Wire-up:**

```powershell
# publish_site.ps1 — appended after audit-links
$audits = @("audit-tokens", "audit-fonts", "audit-dead-code", "audit-images",
            "audit-headings", "audit-aria", "audit-perf", "audit-tokens-drift")
foreach ($a in $audits) {
  python -u manage.py $a
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

### 6.2 Performance budgets per page type

Targets calibrated against peer publications on Moto G Power 4G (Lighthouse mobile preset). LCP ≤ 2.0s is tighter than Google's "good" (2.5s) because every page is pre-rendered HTML — there is no SSR latency, so the budget is the static-site ceiling. TBT and CLS targets are universal; **weight** varies.

| Surface | LCP | TBT | CLS | INP (RUM) | Total | CSS | JS | Img | Fonts | Req |
|---|---|---|---|---|---|---|---|---|---|---|
| Homepage / Editions cover | 1.8s | 150ms | 0.05 | 200ms | 350 KB | 60 KB | 20 KB | 220 KB | 2 | 18 |
| Team page (profiled) | 2.0s | 200ms | 0.05 | 200ms | 480 KB | 80 KB | 30 KB | 320 KB | 2 | 24 |
| Team page (legacy) | 1.6s | 100ms | 0.05 | 200ms | 200 KB | 50 KB | 0 KB | 120 KB | 2 | 12 |
| Wire / list pages | 1.8s | 150ms | 0.05 | 200ms | 380 KB | 60 KB | 15 KB | 260 KB | 2 | 30 |
| Daily / Mailbag / Reactions | 1.8s | 150ms | 0.05 | 200ms | 320 KB | 60 KB | 10 KB | 180 KB | 2 | 18 |
| Hub (data-dense) | 2.4s | 250ms | 0.10 | 250ms | 600 KB | 100 KB | 40 KB | 380 KB | 2 | 28 |
| Methodology | 1.5s | 100ms | 0.05 | 200ms | 200 KB | 50 KB | 0 KB | 120 KB | 2 | 10 |

**Enforcement:** `lighthouse-ci.yml` runs LHCI against 14 representative pages (2 per surface category) with `numberOfRuns: 3` to average noise. `lighthouserc.js` assertions block maps directly to the table above.

The 2-fonts ceiling is non-negotiable: Charter + Inter preloaded. JetBrains Mono loaded but not preloaded (code blocks only). Bowlby + Recoleta are display-only with `font-display: optional`.

### 6.3 Visual-regression testing (Playwright)

**Tool: Playwright `toHaveScreenshot()`.** Defended against Percy ($150/mo unnecessary for solo product), BackstopJS (older, less maintained), Chromatic (Storybook-coupled).

**8 representative pages × 2 viewports = 16 snapshots per PR:**

1. `/` (homepage)
2. `/teams/alabama.html` (profiled blue-blood)
3. `/teams/akron.html` (legacy low-data)
4. `/wire/` (list dense)
5. `/hub/` (data-dense)
6. `/editions/2026-w15/` (editorial cover)
7. `/reactions/` (magazine cards)
8. `/compare/?a=alabama&b=georgia` (interactive composition)

Viewports: `{1440, 900}` desktop + `{390, 844}` iPhone 14 portrait.

**Config:**

```ts
export default defineConfig({
  testDir: './tests/visual',
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.02, threshold: 0.2, animations: 'disabled' } },
  use: { baseURL: process.env.PREVIEW_URL, screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 900 } } },
    { name: 'mobile',  use: { viewport: { width: 390,  height: 844 } } },
  ],
  updateSnapshots: 'missing',
});
```

`maxDiffPixelRatio: 0.02` (2%) is tighter than Ensono's 5% default because our renders are deterministic Python — no React hydration jitter. `threshold: 0.2` handles font anti-aliasing. Dynamic content (timestamps, "live" mood dot) gets `.mask([page.locator('[data-volatile]')])` — every renderer adds `data-volatile` to freshness-sensitive elements.

**Baseline approval:** Committed under `tests/visual/__snapshots__/`. PR that changes a surface intentionally: run `npx playwright test --update-snapshots` against preview URL, commit new baselines. PR description must include "Visual baselines updated: [list]" — enforced by `pr-checklist.yml` scanning PR body.

### 6.4 Content governance — `docs/content-governance.md`

**Section 1 — Chronicle moment definition.** A row in `chronicle_moments` with `confidence ≥ 0.7`, `magnitude ≥ 1.5σ from team baseline`, at least one supporting `source_observation` from a Tier A or B source. Automated nightly; editor reviews `chronicle_moments_pending` queue Saturday morning before edition publish. **No moment ships without manual `approved_at` timestamp.**

**Section 2 — Storyline lifecycle.** Active if `last_chapter_published_at` within 21 days AND `chapter_count ≥ 2`. Dormant if 21–90 days. Archived if >90 days. State transitions automatic via `manage.py refresh-storylines-state`. Editor can pin `state='Active'` with `state_override_until` timestamp.

**Section 3 — Pulse "Awaiting Signal" floor.** Codified in `fan_intelligence.py`. <10 fan observations across last 14 days OR <3 distinct source platforms → emit `AwaitingSignalCard()`. **Do not patch fallback string;** fix upstream collection if program with active signal is misclassified.

**Section 4 — World-class-enrich trigger.** Three triggers: (a) cron Sunday 14:00 UTC, (b) profile added to `profiles/*.md`, (c) `chronicle_moments_pending` queue exceeds 20 rows. Never fires automatically on publish-site path.

**Section 5 — Wire ingestion vs curation.** Wire is ingested: `wire-daily-04am-et.yml` pulls from `source_observations` joined to `chronicle_moments`, ranks by `impact_score × recency_decay`. Editor does not hand-curate Wire rows. Suppression list (`docs/wire-suppress.yml`) is the only manual lever. Wire's editorial voice lives in `why_it_matters` column — LLM-generated then editor-approved.

**Section 6 — Masthead.** Kevin Sherrin, Editor. Hardcoded in `_render_footer()`. AI-assisted articles get Source-Trust ribbon footer; no "Generated by Claude" credit.

### 6.5 Editorial publication cadence

| Surface | Cadence | Workflow file |
|---|---|---|
| Editions cover | Weekly Saturday 06:00 ET | `publish-edition-weekly.yml` (exists) |
| The Daily | Daily 06:00 ET | `the-daily-06am-et.yml` (exists) |
| The Wire | Continuous batched 04:00 ET refresh | `wire-daily-04am-et.yml` (exists) |
| Reactions | Continuous event-triggered (cohort-divergence δ ≥ 14 OR cross-platform \|Δ\| ≥ 0.5σ) | extend `fanintel_gameday_live.yml` |
| Mailbag | Weekly Friday 09:00 ET (queue depth ≥ 7) | `mailbag-friday-09am-et.yml` (exists) |
| Storylines | Per-chapter manual | `manage.py publish-storyline-chapter --slug <x>` |
| Canon | Monthly first Sunday | NEW: `canon-monthly.yml` |
| Pulse / Mood | Daily ingest, weekly render | `ingest_daily.yml` + `publish-edition-weekly.yml` |
| Heisman | Weekly Sunday + post-Saturday games | extend `world_class_enrich.yml` |
| NFL Pipeline | Monthly off-season, weekly in-season | existing |

**Saturday is the keystone.** Friday 09:00 ET Mailbag → Saturday 04:00 ET Wire refresh → Saturday 06:00 ET Edition cover. Sunday is rest-pulse (no scheduled publish) — gameday Reactions reach front page uncontested. Monday 06:00 ET Daily resumes the loop.

### 6.6 CI workflows

**`.github/workflows/audit-on-pr.yml`** — runs all 8 audits + audit-links on every PR against a `--fast --limit-slugs 20` rebuild. Uploads violations as artifact on failure.

**`.github/workflows/visual-regression.yml`** — waits for Vercel preview URL, health-checks, runs Playwright tests against preview, uploads playwright-report on failure.

**`.github/workflows/lighthouse-ci.yml`** — runs LHCI against 14 representative URLs from `lighthouserc.js`, asserts performance + a11y categories + LCP / TBT / CLS thresholds per §6.2.

**`.github/workflows/canon-monthly.yml`** — NEW. First Sunday of month, cron 14:00 UTC. Runs `python manage.py build-canon-monthly` then triggers publish-site.

**`.github/workflows/publish_site.yml`** — existing, gate adding `if: success()` dependency on `audit-on-pr`.

### 6.7 Cache strategy at 69k pages

Extend `vercel.json` with per-tier `headers` blocks:

```json
{
  "headers": [
    { "source": "/assets/fonts/(.*)",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}] },
    { "source": "/assets/cfb-index.([a-f0-9]+).css",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}] },
    { "source": "/assets/(logos|helmets|stadiums|conferences)/(.*)",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=2592000, stale-while-revalidate=86400"}] },
    { "source": "/teams/(.*).html",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=3600, stale-while-revalidate=86400"}] },
    { "source": "/wire/(.*)",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=300, stale-while-revalidate=3600"}] },
    { "source": "/editions/(.*).html",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=86400, stale-while-revalidate=604800"}] },
    { "source": "/(daily|mailbag|reactions|hub)/(.*)",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=1800, stale-while-revalidate=86400"}] },
    { "source": "/methodology/(.*)",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=86400, stale-while-revalidate=604800"}] }
  ]
}
```

Fonts + hashed CSS bundle are immutable (content hash in filename). Logos/helmets change rarely (re-uploaded only on Phase A/B re-runs) — 30-day cache + 1-day SWR. Team pages 1h cache + 24h SWR (Pulse refreshes weekly, mood daily). Wire 5-min cache (triage console). Editions 1-day (effectively immutable until next Saturday).

### 6.8 Browser-support matrix

**Tier 1 (full fidelity):** Last 2 versions Chrome / Firefox / Safari / Edge desktop. iOS Safari 15+. Android Chrome on Android 10+. ~96% US sports-traffic share per StatCounter 2026.

**Tier 2 (graceful degradation):** Safari 14, iOS 14, Firefox ESR. Pages render; scroll-tied animations don't.

**Features requiring Tier-2 fallback:**

- **View Transitions API** — fallback: hard navigation. Wrap every use in `if (document.startViewTransition) { … } else { location.href = … }`
- **CSS Container queries** — fallback: media query at fixed breakpoints
- **CSS subgrid** — fallback: `display: grid` with explicit row sizing
- **`color-mix()`** — fallback: precomputed `rgba()` per team (build-time baked into `output/site/assets/team-tints.css`)
- **Scrollama / GSAP** — load conditionally on `'IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches`

**Service worker / offline: explicitly none.** 17–69k-page site is not an offline use case. Adding a service worker introduces cache-coherence risk (stale Pulse data) not worth the offline benefit. Documented refusal in `docs/content-governance.md`.

### 6.9 The 10 build upgrades ranked by impact (~17.5 dev-days)

1. **Ship `design_tokens.py` + `audit-tokens-drift`** — collapses 5 token vocabularies + 5 gold hex drifts. Every subsequent fix is easier. **3 days. Highest leverage.**
2. **`audit-fonts` gate** — pre-empts v2-discovered Times-New-Roman fallback. Adds head-chrome helper. **1 day.**
3. **`audit-perf` with inline-CSS-bytes ceiling** — eliminates 300 KB duplication. Forces extraction to shared modules. **2 days.**
4. **Playwright visual-regression on 8-page set** — 16-snapshot diff per PR. **3 days.**
5. **Lighthouse CI on 14 URLs with Part-6.2 budget assertions** — pins LCP/TBT/CLS/weight per surface. **2 days.**
6. **`audit-dead-code` AST sweep on `reporting.py`** — deletes `_render_history_*` + `_render_player_*` orphans. Pins file budget below 28,000 lines. **2 days.**
7. **`vercel.json` per-tier Cache-Control headers** — explicit caching by route pattern. **0.5 days.**
8. **`audit-aria` + `audit-headings`** — catches v2 WCAG findings before merge. **2 days.**
9. **`docs/content-governance.md` + cadence matrix codified into workflow `cron:` lines** — Saturday 06:00 ET / Daily / Wire / Mailbag explicit. Adds `canon-monthly.yml`. **1 day.**
10. **`audit-images` + R2 imagery manifest contract** — prevents Phase-A/B/C imagery shipping broken `<img>`. **1 day after Phase-A starts.**

---

## Part 7 · The Cumulative Sprint Roadmap (v3 + v4 merged)

10 sprints, ~14 dev-weeks total. Identity moves ship Sprint 9.5 + 10 (first 2 weeks). Imagery pipeline Sprint 11. Renderer rebuilds Sprint 12. Site recognizably itself by end of Sprint 13. Editorial polish + scrollytelling Sprint 14–15. Build hardening Sprint 16. Polish tail Sprint 17.

### Sprint 9.5 — Foundation (1 week)

- Build `src/cfb_rankings/common/design_tokens.py` — single source for colors / fonts / spacing
- Migrate every renderer to import from it (Wire, Mailbag, Reactions, Daily, Storylines, Editions, Hub, team_pages)
- Add `@font-face` recipe: Charter + Inter + Bowlby One SC + Recoleta Stencil + JetBrains Mono → `output/site/assets/fonts.css`
- Build `_render_head_chrome()` helper — single point for `<head>` emission. Fixes three Times-New-Roman pages
- Externalize team-page inline CSS to `/assets/team-page.css` (saves ~300 KB across 150 pages)
- Move every `--motion-*` declaration into `prefers-reduced-motion: reduce` block (v2 fix)
- Replace `#c9a24a` accent (fails WCAG AA) with `#996c00` or shift paper bg to `#fafafa`

### Sprint 10 — Atom Library + Motion Foundation (1 week)

- Build `src/cfb_rankings/charts/svg.py` per v3 — 14 chart helpers
- Build `src/cfb_rankings/common/atoms.py` — 13 atoms per Part 1
- Add `CohortDivergenceBar` (Move C) — **highest-leverage brand atom**
- Add `SourceTrustRibbon` (Move B)
- Add `ReceiptStrip` + `VerdictTile`
- Add `MoodRibbon`
- Add motion token system per Part 4.1: `--ease-brass-band`, `--ease-snap`, `--ease-press`, `--ease-data`, `--ease-delight` + 7 durations + 4 staggers
- Add pull-quote, drop-cap, marginalia, body-width-cap as global utility styles
- Wire source-attribution chip column into Wire (`source` data already loaded, never rendered)
- Fix Reactions to actually call `_sentiment_bar()` in archive render (helper exists, never invoked)
- Remove storylines "Sprint 13 placeholder" stub
- Replace bottom-nav emojis with Phosphor SVG sprite (5-slot per Part 3.2) + bespoke 12-glyph commission triggered

### Sprint 11 — Imagery Pipeline (1 week)

- Phase A: `fetch_logos.py` + `fetch_conferences.py` + Phosphor source-platform marks (`<use>` references) + 12-glyph bespoke commission delivered
- `render_helmets.py` — Blender batch for top 50 programs
- Phase B kickoff: `fetch_stadium_photos.py` (Wikimedia Commons API) + `fetch_roster_headshots.py` for top 200 active players + `fetch_coach_portraits.py` for all 134 FBS
- Cloudflare R2 bucket provisioned + upload step in `publish_site.ps1`
- Build `asset_for(slug, kind)` helper + `<picture>` emission pattern
- `audit-images` audit subcommand wired

### Sprint 12 — Renderer Rebuilds (2 weeks)

- Rebuild `reactions/renderer.py` to magazine-card pattern using `CohortDivergenceBar` as cover art (Big Swing B3)
- Rebuild `wire/renderer.py` to triage console (filters, IMPACT left-stripe, source-attribution chips, team-logo column, mobile card transform via `data-wcfb-card-mobile`)
- Rebuild `daily/renderer.py` to Bloomberg-terminal dashboard (Big Swing B10)
- Add `ThreadPill` (Active/Dormant) + chapter-density EKG to `storylines/renderer.py`
- Fix `/players/spotlight.html`, `/players/the-room.html`, `/history/heatmap/` rendering pathologies
- Wire `Compare` to data + ship Savant mirror bars (Basketball-Reference pattern; Part 3.3 B.3 for mobile tabbed-swipe)
- Lift cohort-divergence bar from text to SVG atom on homepage Canon callout

### Sprint 13 — Identity + Methodology (2 weeks)

- Add `--bg-tint: rgba(var(--accent-rgb), 0.04)` per program to profiled team pages
- Add 4 program personality typography classes (`.program--blue-blood`, `.program--contender`, `.program--regional`, `.program--rebuild`)
- Build heritage trophy shelf SVG icon row
- Replace rivalry-trajectory `<img>` placeholder with real Dual-Line Build SVG
- Broaden Pulse `mood_lookback_60d` to render sparkline during low-floor weeks
- Ship `SourceTrustRibbon` below every team-page hero + on homepage cover (Move B full surface)
- Rewrite `/methodology/fan-intelligence.html` with force-directed source graph + Tier matrix grid + live per-source freshness counters
- Ship CFB Visual Vocabulary primitives (Motif A yard-line divider; Motif B helmet-stripe rule; Motif C decal-cluster footer)

### Sprint 14 — Share Cards + SEO + Editorial Polish (2 weeks)

- Build `src/cfb_rankings/share_cards/` package per Part 5.3 — 10 Pillow templates
- Migrate every renderer to `render_head_chrome()` — emits OG/Twitter/JSON-LD/canonical/feed-discovery
- `python manage.py build-sitemap` + `build-feeds` CLI subcommands; chain in `publish_site.ps1`
- 8-shard sitemap-index + 12 feed files
- Submit `/sitemap-index.xml` to Google Search Console
- Phase C editorial illustration kickoff: Midjourney v7 for Chronicle covers + Storyline heroes; Flux LoRA fine-tune from first 30 approved outputs
- Editions cover generator (Pillow + `viz_templates/`) — one generated cover per issue
- Chart-on-scroll reveal across every inline SVG via IntersectionObserver

### Sprint 15 — Scroll-tied Storytelling (2 weeks)

- Shared infrastructure: Scrollama bundle, `prefers-reduced-motion` gate, sticky-side CSS, reusable `scrolly-step` macro
- Editions cover essay pinned cinematic intro (GSAP — desktop only)
- Player profile career-arc self-drawing on scroll (GSAP DrawSVG — desktop only)
- Dynasty heatmap progressive fill on scroll (Scrollama + D3 transition)
- Mobile graceful-degradation: static covers, IntersectionObserver-driven static SVG reveal
- Storyline thread anatomy timeline
- Rivalry build-to-kickoff scrubbed image sequence for marquee games

### Sprint 16 — Editorial Voice + Build Governance (2 weeks)

- Land editorial voice stylebook per Part 2 in `docs/editorial-voice.md`
- Extend `profiles/*.md` schema with new fields (`headline_pattern_preferences`, `forbidden_program_clichés`, `signature_metrics_to_lead_with`, `pull_quote_sources`, `era_signoff_overrides`) for 17 profiled programs
- Add Chronicle generation validation gate (5-question headline checklist + banned-phrases scan)
- Ship 8 `manage.py audit-*` subcommands per Part 6.1
- Wire all 8 into `audit-on-pr.yml` + `publish_site.ps1`
- Ship Playwright `visual-regression.yml` + 16-snapshot baseline set
- Ship `lighthouse-ci.yml` + `lighthouserc.js` with §6.2 budgets
- Extend `vercel.json` with §6.7 per-tier cache headers
- Land `docs/content-governance.md` + `canon-monthly.yml` workflow

### Sprint 17 — Polish Tail + Mobile Hardening (1 week)

- 5 highest-impact mobile fixes per Part 3.6 (most already shipped via Sprint 9.5–13; verify and close gaps)
- Wire mobile pattern (B.1): swipeable cards + filter bottom sheet
- Rankings mobile pattern (B.2): sort dropdown + filter sheet
- Compare mobile pattern (B.3): tabbed single-pane with swipe
- A11y final pass: WCAG contrast verification, touch-target audit, heading-hierarchy sweep, reduced-motion verification
- Convert team-art PNGs → WebP, ship `<picture>` fallback site-wide
- Lazy-load team OG images on archive/index pages

**Total: ~14 dev-weeks across 10 sprints.**

---

## Part 8 · Closing

v1 found problems. v2 explained why they were structural. v3 specified what the site should look like when complete. **v4 is the harness that holds it.**

The site as it shipped at audit time was a 5.6/10 aggregate with two surfaces (Hub at 8.5, profiled team pages at 7.5) carrying the brand promise and 14+ surfaces clustered around 4 — competent text presentation, zero proprietary visualization. The data pipeline was genuinely unique: CFBD Tier 2 (30k calls/month), Arctic Shift Reddit archive (back to 2013), Wikipedia pageviews + edits, Locked On podcasts, campus newspapers, Spotify charts, school athletics RSS, Bluesky firehose, GDELT, SeatGeek, prediction markets, beat-writer Substacks, YouTube. The design-system specs were sophisticated. The gap between what the codebase could produce and what the live site showed was the entire opportunity.

v4 closes that gap with:

1. **13 build-ready atoms** at `src/cfb_rankings/common/atoms.py` — Python signatures + HTML + CSS + props + a11y + mobile + edge cases for Mood Ribbon, Divergence Dumbbell (the brand atom), Savant Card, Receipt Strip, Verdict Tile, Era Strip, Source-Trust Ribbon, Yard-Line Divider, Helmet-Stripe Rule, Decal Cluster Footer, CFB Background Texture, Dusk Game Row, Jersey Block Numeral.
2. **A 10-section editorial voice stylebook** that locks the words to the visuals — voice description, headline templates per category with 30+ in-voice examples, comprehensive banned-phrases list (pipeline-leakage / AI-tell / sports-cliché / program-cliché), 5 desk sub-voices with full register specs, attribution format, per-surface copy patterns, profile schema extensions, 5-question headline-quality checklist, 250-word house example.
3. **A mobile-first substrate** with type-scale floors anchored to iPhone SE, sticky-element hierarchy, 5-slot Phosphor bottom nav with hamburger drawer (replacing 5 emoji glyphs), per-surface patterns (Wire swipeable cards, Rankings filter sheet, Compare tabbed-swipe, Hub virtualization), above-the-fold compositions for all 18 pages, the 5 highest-impact mobile fixes at ~9 dev-days.
4. **A motion choreography spec** with 5 easing curves + 7 durations + 4 staggers as canonical tokens, per-element-type interaction states, page-load reveal sequence with stagger timings, per-chart entry choreographies for all 14 patterns, View Transitions API plumbing with 3 named transitions, 3 micro-delight moments capped at 0.22 overshoot, complete reduced-motion override matrix, 11 forbidden patterns.
5. **A share-card + SEO + structured-data system** with per-surface Pillow OG card visual specs, complete Pillow rendering pipeline + module skeleton, `render_head_chrome()` helper, 8-shard sitemap-index at 69k pages, 12-file RSS + Atom + JSON-Feed system, JSON-LD schemas per page type, audit of current `<head>` (0 JSON-LD anywhere; SVG OG silently dropped by iMessage/Discord/Bluesky).
6. **A governance + performance budget layer** with 8 `manage.py audit-*` subcommands wired into CI, LCP/TBT/CLS/weight ceilings per surface, Playwright visual-regression on 8 representative pages × 2 viewports, design-token-drift detection, content governance rules (Chronicle approval / Storyline state machine / Pulse floor / world-class-enrich triggers), editorial publication cadence matrix, 5 CI workflows, cache strategy with Vercel per-route headers, browser-support matrix with feature-fallback rules.

**The closing test.** A reader on a 375×667 iPhone SE lands on `/teams/alabama.html`. Above the fold:

- 3px crimson conference rule (SEC)
- 80px helmet-stripe band — crimson with thin white center stripe — running through "ALABAMA" reversed in end-zone-paint script (Bowlby One SC)
- Sticky 44px section-anchor strip exposing 7 modules of the page
- 24px Mood Ribbon spanning 343px wide — current week ticked in `--gold-october` Phosphor dot
- Divergence Dumbbell showing stat-folks #6 vs casual-fans #17 with bold "Δ 11" on rod
- "Tuscaloosa lost a game it didn't lose." in Charter 17px above the Receipt Strip

Below the fold, four thumb-flicks deep, the Era Strip ends the page. Every signature visualization is reachable in fewer flicks than it takes to open the App Store.

The bottom nav pins 5 destinations in Phosphor glyphs against wool-jacket dark. The page reads dense but navigable — like Bloomberg on a phone, not like ESPN.

Build-side: every PR runs the 8 audits + Playwright + Lighthouse before merge. The 5 hardcoded gold hex values cannot return. The Times New Roman fallback cannot reappear. The 300 KB of duplicate inline CSS cannot reaccrete. The 18 dead `_render_history_*` / `_render_player_*` functions cannot survive. The auditing isn't decoration — it's the load-bearing structure that converts v1–v3 from a one-time fix into a permanent floor.

The site reads like a magazine, not an app. The cohorts disagree, and the disagreement is the story. The receipts age. The mood ribbon ticks. The standard does not flinch at rankings.

**That is the site when it's done.**

---

## Appendices

### A. The 18 investigators across v2 + v3 + v4

| Wave | # | Investigator | Output |
|---|---|---|---|
| v2 | 1 | DB schema audit | 5 empty moat tables + backfill-aware matrix |
| v2 | 2 | Renderer architecture survey | 15-renderer quality matrix; 5 hardcoded gold hex values |
| v2 | 3 | Competitive references | 15+ named treatments across 8 categories |
| v2 | 4 | Icons / fonts | Phosphor primary + 12-glyph commission + font-loading recipe |
| v2 | 5 | Design critique | Typography psychology + CFB color palette + 3 brand-identity moves |
| v2 | 6 | A11y / perf | WCAG contrast failures + 77MB images + 300KB CSS dupe |
| v3 | A | Imagery density benchmark | 27 reference pages quantified; per-surface gap |
| v3 | B | Chart library selection | Python-SVG primary + `charts/svg.py` drop-in |
| v3 | C | Photo / illustration sourcing | 3-phase pipeline; Cloudflare R2; Midjourney style guide |
| v3 | D | Data-vis pattern catalog | 28 patterns; 5 signature visualizations; banned list |
| v3 | E | CFB iconic visual language | 12-motif vocabulary; fall-Saturday-feel recipe |
| v3 | F | Scroll-tied storytelling | Scrollama + GSAP; must-have-3; 19-day budget |
| v4 | A | Build-ready atom specs | 13 atoms with Python+HTML+CSS+a11y+edge cases |
| v4 | B | Editorial voice stylebook | 10-section voice guide + 250-word in-voice example |
| v4 | C | Mobile-first redesign | Per-surface compositions + 5 highest-impact fixes |
| v4 | D | Motion choreography | 5 easings + 7 durations + 4 staggers + reduced-motion matrix |
| v4 | E | Share cards + SEO + structured data | Pillow pipeline + sitemap-index + RSS/Atom/JSON Feed |
| v4 | F | Build/deploy governance | 8 `audit-*` subcommands + perf budgets + CI workflows |

### B. New files created by v4 work

- `src/cfb_rankings/common/atoms.py`
- `src/cfb_rankings/common/design_tokens.py`
- `src/cfb_rankings/common/head_chrome.py`
- `src/cfb_rankings/charts/svg.py`
- `src/cfb_rankings/share_cards/` (10 templates + base + fonts + assets + paths)
- `src/cfb_rankings/seo/sitemap.py` + `seo/feeds.py` + `seo/jsonld.py`
- `src/cfb_rankings/audit/` (8 audit modules)
- `output/site/assets/atoms.css` (generated)
- `output/site/assets/phosphor-sprite.svg`
- `output/site/assets/fonts/{charter,inter,bowlby,recoleta,jetbrains}.woff2`
- `output/site/assets/fonts.css`
- `tests/visual/__snapshots__/`
- `playwright.config.ts`
- `lighthouserc.js`
- `.github/workflows/{audit-on-pr,visual-regression,lighthouse-ci,canon-monthly}.yml`
- `docs/content-governance.md`
- `docs/editorial-voice.md`

### C. Token migration alias map

The `CSS_VAR_MAP` in `design_tokens.py` aliases v3 names to currently-shipped CSS variable names for migration:

```
--paper           → --bg-0
--wool            → --bg-0 (dark-mode equivalent)
--ink             → --fg-primary
--ink-muted       → --fg-muted
--ink-subtle      → --fg-subtle
--gold-october    → --accolade-gold
--concrete        → --fg-muted
--grass           → --tone-green
--alert           → --tone-red
--burntorange     → --tone-coral (legacy alias; rename Sprint 12)
--crimson         → --accent-primary (in team-page context)
--field-white     → #ffffff (always)
```

---

**End of v4.** The four audits — v1 problem-finding, v2 architectural deep-dive, v3 imagery + identity, v4 build-ready translation — together specify a complete redesign from current state to shipped product. **Total: ~3,100 lines across four documents. Total ~14 dev-weeks to land.** The work is mapped sprint-by-sprint, atom-by-atom, audit-by-audit. The cohorts disagree, and the disagreement is the story.
