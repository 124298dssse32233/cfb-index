# CFB Index — Triple Audit, v3 (Imagery + Visual Identity)

**Date:** 2026-05-15
**Auditor:** Claude (autonomous, orchestrated 12-investigator parallel deep-dive across v2 + v3)
**Live site:** https://wonderful-margulis-8ec96b.vercel.app
**Supersedes:** [v1](DESIGN_AUDIT_2026_05_15.md) (problem-finding), [v2](DESIGN_AUDIT_2026_05_15_v2.md) (deep architectural)
**Reads as:** A standalone build-spec for the imagery + identity layer. v3 doesn't restate v1/v2 — it answers the question they left vague: *what does this site look like when it's done?*

### Premise updates from the owner (since v2)

1. **This is a personal, non-commercial site.** Fair-use latitude is wide. Use any logo, glyph, or platform mark needed — Reddit snoo, ESPN bug, On3 mark, 247 wordmark, AP byline, Getty editorial credit. The v2 source-platform licensing matrix that restricted ESPN/247/On3/SBN to text-only is now obsolete. **Treat brand marks as freely usable, with attribution.**
2. **"The right amount of images, graphics, charts for this caliber of website"** is the explicit ask. v3 answers this with measured peer benchmarks and a per-surface prescription.
3. **A 4-hour historical-data backfill is in flight.** Content emptiness on player pages, NFL pipeline, dynasty heatmap, signature stories resolves on `publish-site` auto-trigger at the end of the run. The structural recommendations below stand regardless.

---

## What v3 Adds Over v2

v3 was produced by six parallel investigators on orthogonal imagery dimensions, plus integrating the fair-use clarification. New artifacts:

1. **Quantitative imagery-density benchmark** vs ESPN, The Athletic, FiveThirtyEight, NYT Upshot, Bloomberg, On3, The Ringer, Pro Football Reference — 27 reference pages counted, organized by page type. Empirically: peer team pages ship 20–30 photos + 25–50 glyphs; CFB Index ships 0 photos on 16 of 18 surfaces and 0 charts on 14 of 18.
2. **Per-page imagery prescription** — current → target counts (photos, charts, glyphs, illustrations) for every shipping CFB Index surface.
3. **A 12-motif CFB Visual Vocabulary** drawn from college football's actual iconographic tradition: helmet stripe, reward decal, yard-line stripe dividers, end-zone field paint, marching-band uniform trim, goalpost silhouette, rivalry-trophy iconography, CFP bracket geometry, pylon cube, conference academic-seal badges, press-box scoreboard typography, letterman varsity-patch.
4. **Color identity rules specific to college football** — team-page tinting, conference top-border, rivalry-week color seam, color-clash separator, golden-hour `#e8a93a` accent, stadium-shadow contrast tones, dusk-game tile treatment.
5. **Typography moves drawn from CFB tradition** — jersey-block numerals (Bowlby One SC or Druk Condensed), scoreboard-display LED-styled scores, stadium-signage display face (Stymie / Knockout / Recoleta Stencil), warm-neutral grounds.
6. **The Five Signature Visualizations** — Mood Ribbon, Divergence Dumbbell, Savant Card, Receipt Strip, Era Strip. These five together are the data-vis identity of the brand.
7. **The 28-pattern Encoding Catalog** — every CFB Index data type mapped to a specific named viz pattern with peer reference and ship location.
8. **The Banned Patterns** — pies, donuts, radars, 3D anything, rainbow heatmaps, default Chart.js. Refuse list.
9. **Chart-library decision** — Python-written inline SVG (matches NYT Upshot's Archie pipeline) for 13 of 14 patterns; Observable Plot only at build-time for Sankey. Drop-in `src/cfb_rankings/charts/svg.py` module spec'd with 30-line code example.
10. **Imagery sourcing pipeline** — Phase A (logos + helmets + source marks, 2–3 days, $0), Phase B (stadiums + headshots + coach portraits, 1–2 weeks, $0), Phase C (editorial illustration ongoing, ~$10/mo Midjourney). Cloudflare R2 storage; $0 indefinitely at this scale.
11. **Editorial illustration system** — Brad-Holland-meets-Edward-Hopper-meets-Christoph-Niemann style. Midjourney v7 prompt scaffolding + three template prompts for Chronicle moments / Storyline anatomy / Era cards.
12. **Scroll-tied editorial storytelling** — 10-pattern catalog, Scrollama-primary + GSAP-targeted recommendation, 19-day implementation budget, must-have-3 (Editions pinned cinematic intro, Player career-arc self-drawing, Dynasty heatmap progressive fill).

---

## Part 1 · The Imagery Question — "Right Amount" Quantified

### Peer-publication empirical norms

Investigator A counted imagery elements across 27 reference pages from ESPN, The Athletic, FiveThirtyEight (archived), NYT Upshot, Bloomberg, On3, The Ringer, Pro Football Reference. Median norms per page type:

| Page type | Photos (median) | Charts (median) | Glyphs (median) | Above-fold imagery |
|---|---:|---:|---:|---:|
| **Team page** | 20–30 | 0–1 (data tab: 4–8) | 25–50 | 4–8 |
| **List / index** (rankings, schedule, wire, big board) | 30–100 | 0 | 80–150 | 6–25 |
| **Homepage** | 15–47 | 0 | 12–45 | 3–6 |
| **Feature article** | 1–6 | 0–4 | 0–8 | 1–2 |
| **Forecast / dashboard** | 0–1 | 32–64 | 32 | 8–12 |
| **Methodology / explainer** | 1 | 4–8 | 0 | 1–2 |
| **Player page (reference)** | 0–1 | 2–4 | 8–14 | 1 |

**Strongest cross-outlet rule:** list and index surfaces are glyph-saturated — one team logo per row × 25–130 rows. Team pages average 20–30 photos (On3 ships 28/47/18 across Alabama/Ohio State/Georgia). Feature articles are photo-sparse but illustration/chart-bearing (1 hero photo + 0–4 inline charts at 538/Upshot/Bloomberg, 1 bespoke illustration at Ringer/Bloomberg).

### CFB Index per-surface prescription (current → target)

| Surface | Photos | Charts | Glyphs | What to add |
|---|---|---|---|---|
| **Homepage `/`** | 0 → 6–10 | 0 → 2–3 | ~12 → 30 | Cohort-divergence bar + mood-trajectory sparkline + 4 hero photos for Wire/Daily/Reactions/Canon teasers |
| **Team page (profiled, 17 slugs)** | 0 → 4–8 | 5 → 8–12 | ~20 → 40 | Stadium hero photo, headshot grid (5 key players), opponent-helmet rail (12 logos), real rivalry-trajectory SVG |
| **Team page (legacy, 647 slugs)** | 0 → 2 | 0 → 4 | ~10 → 25 | Stadium photo hero; ship Savant percentile bars (4 charts) + opponent-logo rail |
| **Wire `/wire/`** | 0 → 15+ | 0 → 1 | ~6 → 60 | One team-logo glyph per row + small headshot for high-profile items + mood-mover sparkline header |
| **Daily `/daily/`** | 0 → 3 | 0 → 4 | ~5 → 20 | Hero photo + top-3 mood-mover chart + featured-game scorecard |
| **Mailbag `/mailbag/`** | 0 → 1 | 0 → 1 | ~2 → 6 | Author headshot byline + reader-question card cluster + inline chart per data-relevant answer |
| **Reactions `/reactions/`** | 0 → 4 | 0 → 2 | ~3 → 12 | Game scorecard + mood-shift chart + cohort-divergence bar (cover art) + headshot quotes |
| **Canon `/canon/`** | 0 → 25 | 0 → 1 | ~5 → 30 | Per-list cover treatment: headshot grid (the 100), coach portraits (the 25), goalpost glyph (the 50) |
| **Storylines** | 0 → 6 | 0 → 2 | ~5 → 15 | Beat-writer headshots (1 per storyline) + arc-chart + 4 hero photos |
| **Players** | 0 → 30+ | 0 → 4 | 0 → 20 | Full headshot grid + position chips + per-position leader sparklines |
| **Heisman** | 0 → 8 | 0 → 6 | ~5 → 20 | Candidate headshots × 8 + weekly probability sparkline grid + EPA scatter + position-chip rail |
| **Hub `/hub/`** | 0 → 6 | **28 → 28** | ~15 → 30 | Maintain chart density; add 6 candidate-photo embeds in Mood Movers; lift module pattern elsewhere |
| **Compare** | 0 → 4 | 0 → 8 | ~4 → 20 | Two team logos + top-5 headshot rail per side + side-by-side mini-charts × 8 |
| **Conferences** | 0 → 0–4 | 0 → 4 | ~10 → 64 | Per-league glyph SVG sprite + comparative-metric chart per league |
| **Editions** | 0 → 3 | 0 → 2 | ~5 → 12 | Generated cover image per issue (Pillow + viz_templates) + roman numeral display |
| **Methodology** | 0 → 2 | 0 → 6 | ~5 → 25 | Force-directed source graph + tier matrix + per-source freshness counters + 8 source brand-marks |
| **History heatmap** | 0 → 0 | 1 → 1 (the heatmap) | 0 → 12 | Render the actual heatmap from `team_season_arc` |

### Four imagery patterns 100% absent on CFB Index (universal at peers)

1. **Per-game scorecards with team logos + score + key-stat line.** ESPN schedule pages render 12 helmet-logo pairs above the fold; Sports-Reference renders this as season log table with logo + score + opponent-logo per row. CFB Index renders schedules/results as plain text with no logos.
2. **Beat-writer / author headshots inline in bylines.** AP, ESPN, The Athletic, Ringer, On3 ship 24–32px circular author photos next to bylines, plus 80px headshots in author-cards. Bloomberg has author photos on every feature opener. CFB Index has zero author imagery on Mailbag, Daily, Reactions, Wire.
3. **Stadium / venue photography at team-page hero.** ESPN 2025 rebrand crops helmets and stadium macro photography across team pages; On3 and Athletic open team pages with hero photo (saturated stadium shot + team-color gradient + headshot strip). All 17 profiled CFB Index team pages render flat color band instead.
4. **Brand-mark composites for list covers + conference identity.** Bloomberg manipulates Druk/Neue Haas as illustration; NYT Magazine alternates pure-type covers with arresting photo crops; Ringer commissions bespoke illustration per feature; 538's old archive used 6×6 team-logo grid as navigation atom. CFB Index renders `/canon/`, `/conferences/`, `/editions/`, `/storylines/` as text headlines on solid backgrounds.

---

## Part 2 · The CFB Visual Vocabulary

College football has the richest iconographic tradition of any American sport. Twelve repeating motifs that should appear (subtly, consistently) throughout the site:

| # | Motif | Description | Ship locations |
|---|---|---|---|
| 1 | **Helmet stripe** | 6px team-color rule with 2px `--field-white` outline above/below — the helmet's center stripe | Top of every team page (full-bleed band); CFP bracket divider; section headers on rivalry pages |
| 2 | **Reward decal** | 14–18px circular accent in team color, slightly tilted — the accreting Ohio-State-buckeye-leaf / Florida-State-tomahawk merit-decal pattern | Player accolade lens (one decal per honor); "milestones" track on team page; Heisman shortlist badges; trophy-case section on rivalry pages |
| 3 | **Yard-line stripe (5-yard tick)** | Solid 2px `--field-white` rule interrupted at 25% and 75% by short perpendicular ticks (5-yard hash) | Section dividers between content modules; horizontal rules between mood card and belief block |
| 4 | **End-zone field paint** | Full-bleed saturated team color with script or block lettering reversed in `--field-white` (Tennessee checkerboard / Notre Dame diagonal / Ohio State Block O per-program variants) | Team-page hero (program name reversed across a saturated team-color band); rivalry-week takeover banners |
| 5 | **Marching-band uniform trim** | Gold metallic 1px hairline + parallel 3px line with reflective gradient (`linear-gradient(90deg, #c8a85c, #f5e6a8, #c8a85c)`) | Dividers between *editorial* sections (not data); Honor Roll separators; The Room board top-rule |
| 6 | **Goalpost silhouette** | A bracket-shape glyph — the Y-frame | "Best wins" list bullets; conversion-rate stat icon; ranked-vs-ranked wins flag |
| 7 | **Rivalry-trophy iconography** | One-line outline glyph per profiled rivalry: Old Oaken Bucket, Floyd of Rosedale, Stanford Axe, Little Brown Jug, Iron Skillet, Jeweled Shillelagh, Paul Bunyan's Axe | Rivalry pages (header glyph); rivalry-week home-page modules; matchup preview cards |
| 8 | **CFP bracket geometry** | Branching lines, seed-numbered nodes — the structural metaphor of the 12-team bracket | CFP page (literal); season-arc visualization showing path; win-out scenarios branch tree |
| 9 | **Pylon / endzone corner cube** | Vivid orange (`#ff6a13`) 4-sided color block as "scoring zone" / "this metric counts" indicator | Red-zone efficiency stat tile; corner-radius treatment on important metric cards (clipped corner) |
| 10 | **Conference academic-seal badge** | Banded, layered, founding-year-dated shields — academic-seal vocabulary not pro-league shield | Standings tables (conference column); conference landing pages; team-page lineage |
| 11 | **Press-box typography** | Chunky condensed all-caps, squared terminals, even stroke — pre-videoboard Daktronics scoreboard letterform | Live score readouts; final-score tiles; week-by-week result strip |
| 12 | **Letterman patch** | Chenille varsity-letter aesthetic: felt-on-felt outline, drop-shadow, slight tilt | Conference-champion badge; All-American tag; bowl-win indicator on schedule rows |

### Three repeating motif marks (drop-in CSS / SVG primitives)

**Motif A — Yard-line stripe divider** (use between major content sections):

```css
.divider-yardline {
  height: 4px;
  background: var(--field-white);
  position: relative;
}
.divider-yardline::before,
.divider-yardline::after {
  content: ''; position: absolute; top: -4px; height: 12px; width: 2px;
  background: var(--field-white);
}
.divider-yardline::before { left: 25%; }
.divider-yardline::after  { left: 75%; }
```

**Motif B — Helmet-stripe rule** (top of team pages, between season epochs): 6px team-primary horizontal rule with 1px `--field-white` line bisecting it lengthwise.

**Motif C — Decal cluster (footer mark):** 3-decal cluster (~14px each) in team-primary, slightly overlapping in pyramid arrangement. Replaces generic footer copyright bullet. On the site-wide footer, three accreted "honors" from the user's followed team's week (Heisman shortlist position, AP movement, signature win).

### Anti-patterns — design moves that read NFL / generic-sports rather than CFB

- **Iridescent jersey-fabric textures** (NFL Sunday Ticket aesthetic)
- **Scrolling team-news ticker** (broadcast-TV)
- **Stadium-photo hero with crowd shots** (stock and interchangeable)
- **Shield logo treatment** (pro-league vocabulary — college uses seals, scripts, beasts)
- **Sleek black-and-team-color gradients** (2010s sports-network look)
- **Aggressive italic/oblique sans-serif** ("forward-leaning speed type" reads NASCAR; college reads upright, ceremonial)
- **Glassmorphism / depth-of-field blur** (fights CFB's flat-color, crisp-edge idiom)
- **Generic fall-foliage stock photography** (use type and color to evoke autumn, not a maple-leaf border)
- **Animated hands grabbing UI elements** (broadcast move — kitsch on static site)

---

## Part 3 · Color Identity for College Football

CFB's color tradition is **maximally saturated, primary-color, and unmediated** — unlike NFL (uniformly desaturated for broadcast) or NBA (modernized by brand consultants). Apple Cup is cardinal vs. blue; Iron Bowl is crimson vs. burnt orange; Big House is maize vs. scarlet. Lean in.

### Rules

**Team-page tinting:** When a user is on `/teams/alabama.html`, every interactive element pulls from `--team-primary` (#9E1B32) and `--team-secondary` (#828A8F). Section backgrounds get a 4% wash. Stat tiles get a 1px `--team-primary` left border. Avoid full-bleed flooding — CFB color is structural, not decorative.

**Conference identity:** A thin top-border (3px) across every page tied to a conference identifies league loyalty before any chrome loads:

| Conference | Top-rule color |
|---|---|
| SEC | `#C8102E` |
| Big Ten | `#0A0A0A` |
| ACC | `#013CA6` |
| Big 12 | `#C8102E` (warm undertone) |
| Mountain West / Pac-12 remnants | teal `#00A4A6` |
| AAC | purple `#5F2C82` |
| Sun Belt | sun-gold `#FDB827` |

**Rivalry-week color seam:** Hard 50/50 diagonal split at page header during rivalry weekends — both teams' primaries meeting at center. **No gradient blend** — the seam is the point. CFB rivalries are oppositional; design should be too.

**Color-clash rule:** When two team colors vibrate badly (red on green, orange on blue at saturation), insert a 4px `--field-white` separator. Mimics referee jersey neutralizing two color-clad teams.

**Saturation discipline:** Team colors stay saturated; *neutrals* desaturate. Site chrome is warm-neutral (wool letterman jacket): `#1c1614` near-black, `#f4ede0` paper-cream, `#8b7355` saddle-brown for body text on cream. This wool/leather/parchment ground is what lets primary team colors sing.

### The "Fall Saturday Feel" — specific moves

- **Warm-neutral ground.** `--bg-paper: #f4ede0` (cream with yellow undertone) in light mode; `--bg-wool: #1c1614` (wool-jacket brown-black) in dark mode. Pure white and pure black both read tech-sterile.
- **Golden-hour accent.** `--gold-october: #e8a93a` — the marching-band-button color. Not yellow, not gold — *October-five-PM gold*. Used sparingly: hover on stat tiles, live-game indicator, current-week marker on schedule.
- **Stadium-shadow contrast.** Dark mode uses brown-black (`#1c1614`) with `#3d2f28` shadow tones — the long shadow cast by the east stands at 4pm kickoff. Avoid pure `#000`.
- **Brass-band 220ms transitions.** All interactive transitions default to 220ms ease-in-out (cadence of marching-band step, 120 BPM, 8-to-5). Long enough to feel ceremonial, short enough to feel responsive. No springy/bouncy easing.
- **Dusk-game schedule rows.** Night games (kickoff after 7pm) get a dark-blue underwash (`#0e1426`, navy stadium-sky); afternoon games stay cream. Communicates a fall Saturday's arc — noon kickoffs cream, 3:30 cream-gold, primetime navy.
- **Subtle paper grain.** 3% noise overlay over the cream ground — texture of newsprint and gameday-program covers. Imperceptible until you look.
- **Marching-band gold trim.** Anywhere a 1px hairline border would normally appear (cards, table borders, input frames), substitute the metallic-gold gradient hairline from Motif §A. Tiny per instance; adds up to a sport-specific texture across the whole site.

### Color token migration (folding v2 + v3)

Final canonical token set in `src/cfb_rankings/common/design_tokens.py`:

```python
COLORS = {
    # Grounds
    "paper":         "#f4ede0",   # cream, light-mode bg
    "wool":          "#1c1614",   # wool-jacket brown-black, dark-mode bg
    "wool_shadow":   "#3d2f28",   # stadium-shadow tone
    "field_white":   "#ffffff",   # 100% pure for yard-line stripe / end-zone paint only

    # Type
    "ink":           "#141618",   # body type on paper
    "ink_muted":     "#8b7355",   # saddle-brown — secondary type on paper
    "ink_inverse":   "#f4ede0",   # body type on wool

    # Brand accents
    "gold_october":  "#e8a93a",   # the singular CTA / hover / live indicator
    "brass_hairline":"linear-gradient(90deg,#c8a85c 0%,#f5e6a8 50%,#c8a85c 100%)",

    # Semantic
    "crimson":       "#9e1b32",   # narrative weight, crisis
    "alert":         "#d93025",   # MAJOR-impact chip only
    "grass":         "#3a7d35",   # ambient-positive / live / up-trend
    "concrete":      "#8a8c88",   # neutral structural (warm gray)
    "burntorange":   "#c4622d",   # emotion / controversy / rivalry coral

    # CFP / pylon
    "pylon":         "#ff6a13",   # red-zone / scoring zone

    # Conferences (3px top-rule per page)
    "conf_sec":      "#c8102e",
    "conf_big10":    "#0a0a0a",
    "conf_acc":      "#013ca6",
    "conf_big12":    "#c8102e",
    "conf_mwc":      "#00a4a6",
    "conf_aac":      "#5f2c82",
    "conf_sunbelt":  "#fdb827",
}
```

Every renderer imports from this single source. The 5 hardcoded "gold" hex values from v2 are retired.

---

## Part 4 · Typography for College Football

### Five faces, four uses

| Face | Use | License | Notes |
|---|---|---|---|
| **Charter** or Libre Baskerville | Editorial body (sustained prose: Mailbag, Daily, Canon, cover essays) | SIL OFL (free) | v2 migration — replaces Source Serif Pro; metrically denser, sharper, authority |
| **Inter Display** | UI labels, metric tiles, eyebrows, nav | SIL OFL (free) | Already in tokens.css |
| **Bowlby One SC** or Druk Condensed | **Jersey-block numerals** — score readouts, ranking numbers, jersey callouts | Bowlby One SC: free / Druk: commercial | Numerals only; chunky condensed sans, squared terminals, even stroke, near-uniform width (NCAA block 8" minimum — no thin strokes — baked into the form) |
| **Recoleta Stencil** or Knockout | Stadium-signage display — hero headlines on team-page splash | Both commercial; Stymie is free alternative | Big, hand-touched, slightly weathered — references painted-on-fence campus signage |
| **JetBrains Mono** | Chart callouts, monospace data labels | SIL OFL (free) | Already in v2 spec |

### Type moves drawn from CFB tradition

**Scoreboard-display scores.** Final scores render as bright-on-dark tile, all-caps, with 2px outer ring and "LED dot" texture (2×2 SVG noise overlay at 8% opacity). Evokes Daktronics LED scoreboards without literal pixel-art kitsch.

**Marching-band trim as section break.** Section endings get a 2-line rule: 1px metallic-gold hairline + 4px gap + 3px metallic-gold rule. NOT below H2 (too noisy). Only between *major page sections* (after mood card, before schedule, etc.).

**Numerals as pageantry.** Heisman vote counts, win streaks, attendance figures get the jersey-block treatment at display size. Mundane stats stay in humanist sans.

**Editorial body discipline.** Body copy stays literary, not journalistic. The Athletic's CFB section reads longform; type should encourage reading. Generous leading (1.65), no condensed/space-saving moves, max 65ch width.

### Font-loading recipe (drop-in code from v2, finalized)

Three pages currently fall back to Times New Roman because no font is loaded. Fix:

```
output/site/assets/fonts/
  charter-var.woff2              # variable, latin subset
  inter-var.woff2                # variable
  bowlby-one-sc.woff2            # jersey numerals
  recoleta-stencil-headline.woff2  # display only
  jetbrains-mono-var.woff2       # mono
output/site/assets/fonts.css     # @font-face + size-adjust metrics
vercel.json                      # cache headers
```

`fonts.css` declares each face with `font-display: optional` + a metrically-matched fallback (Georgia for Charter; Arial for Inter; Impact for Bowlby; Menlo for JetBrains) using `size-adjust` + `ascent-override` + `descent-override` + `line-gap-override` to prevent CLS. Vercel headers cache fonts at `max-age=31536000, immutable`.

Every renderer's `<head>` emits the preload + stylesheet trio through a single shared `_render_head_chrome()` helper. The three Times-New-Roman pages bypassed this — fix the bypass.

---

## Part 5 · The Five Signature Visualizations

If a reader sees a screenshot from CFB Index out of context, these five patterns should be how they recognize the brand. **Five, not eight.** This is the canonical data-vis palette.

### Signature 1 — The Mood Ribbon

**Atmospheric signature.** A horizon-style horizontal ribbon, 24px tall, 52 weeks wide. Saturation encodes belief intensity; hue encodes valence (warm = belief, cool = doubt). Single zero-line bisects it; current week is a black tick. Reads as a heartbeat strip.

**Lives on:** masthead of every team page; repeated mini-form on Hub; embedded inline on Daily and Reactions when relevant.

**Peer references:** NYT Upshot election-needle colorband; FT recession bars.

### Signature 2 — The Divergence Dumbbell

**Editorial signature.** The thesis of CFB Index is *cohorts disagree, and the disagreement is the story.* Two dots on a horizontal rank axis (1–25), connected by thick gray rod. One dot is `ChartBar` (stat-folks), the other `Smiley` (casuals). Rod thickness encodes magnitude of disagreement. Bold delta number lives on the rod itself ("Δ 14").

**Lives on:** universal atom — every Reaction card (as cover art), every Wire row with cohort split, every Canon entry, every Player Accolade Lens, every Mailbag answer with cohort relevance, homepage Voices module. **This is Move C from v2 — the single most-important brand atom to ship.**

**Peer references:** Pudding/Polygraph diverging-pair plots; FT "deviation" dumbbells.

### Signature 3 — The Savant Card

**Credibility signature.** Stacked horizontal sliders, 13 metrics tall. Each is a 100-width gray track with a colored capsule positioned at the percentile. Capsule color is a 2-stop diverging ramp (slate → crimson). Number lives inside the capsule. Borrowed visual grammar from Baseball Savant earns instant analytical authority.

**Lives on:** every player page (Accolade Lens section); every team page (existing implementation — formalize); a compressed 4-metric variant on Wire callouts and Mailbag inline.

**Peer references:** [Baseball Savant Statcast player pages](https://www.mlb.com/news/baseball-savant-statcast-player-pages-new-look).

### Signature 4 — The Receipt Strip / Verdict Tile

**Journalism signature.** The site's voice is "we said this, here's what happened." A horizontal slab with two stacked rows: top = preseason projection (gray ghost type, struck-through if wrong), bottom = current reality in serif display weight. Delta arrow on right with colored chevron.

Compressed variant — "Verdict Tile" — collapses to one row, three cells (Claim / Outcome / Verdict). Verdict is a Phosphor glyph (`Check` / `X` / `MinusCircle`) plus 4 monospace words.

**Lives on:** `/receipts/` index + inline on every team-page hero + Wire rows when claim resolves + Heisman board calibration retrospective + Daily morning ledger.

**Peer references:** FiveThirtyEight calibration plots; Polymarket prediction-vs-outcome.

### Signature 5 — The Era Strip

**Time-depth signature.** CFB Index's moat is historical context (Arctic Shift back to 2013, 12-year SP+, regime tracking). A horizontal multi-track strip, 12 tracks tall: SP+ line, AP-final dot, Coach (color-band background), Conference (label band on top). Hairline divider per season.

Already partially shipping on team pages — formalize and lift to a shared atom. Era backgrounds shade (pre-bowl / bowl-era / BCS / CFP-4 / CFP-12).

**Lives on:** every profiled team page; lifted to Canon era pages; small-form on conference landing pages.

**Peer references:** Bloomberg-style horizontal regime strips; NYT "Lifelines."

### How the five compose

One for the **present mood**, one for the **editorial frame**, one for the **player layer**, one for the **predictive ledger**, one for **history**. Every other chart on the site should look like it shares a family with these — same hairline grids, same Phosphor glyph endcaps, same JetBrains Mono callouts, same warm-neutral grounds.

---

## Part 6 · The 28-Pattern Encoding Catalog

Every CFB data type mapped to a specific named visualization. (Compressed table; full descriptions in Investigator D output.)

| # | Data type | Pattern | Peer reference | Ships on |
|---|---|---|---|---|
| 1 | Team mood over time | **Mood Ribbon** (Sig 1) | NYT election needle | Hub + every team page |
| 2 | Cohort divergence | **Divergence Dumbbell** (Sig 2) | Pudding diverging plots | Universal atom — 7 surfaces |
| 3 | Pre-season vs current SP+ | **Receipt Strip** (Sig 4) | Athletic "What we got wrong" | Receipts page + team hero |
| 4 | Game win-prob time series | **Win-Prob Timeline** | ESPN gamecast / NYT live-game | `/games/<id>.html` + game logs |
| 5 | Player percentile bars | **Savant Card** (Sig 3) | Baseball Savant | Every player page |
| 6 | Recruiting class vs P5 avg | **Composite Spread** | FT above/below-trend | Team page recruiting module |
| 7 | Returning production % | **Position Stack** | (custom) | Team page roster |
| 8 | Conference SP+ distribution | **Conference Beeswarm** | FT Visual Vocabulary beeswarm | `/conferences/` |
| 9 | Weekly rank movement | **Bump Chart (Top-25)** | NYT/Upshot ranking bumps | `/rankings/` + team page mini |
| 10 | Transfer portal flow | **Tiered Sankey** | Reuters migration flows | `/transfer-portal/` |
| 11 | Heisman model probability | **Candidate Sparkline Grid** | Athletic MVP tracker | `/heisman/` + Hub during season |
| 12 | Rivalry heat trajectory | **Dual-Line Build** | NYT election dual-candidate | Replaces Alabama page placeholder `<img>` |
| 13 | Historical season arc | **Era Strip** (Sig 5) | Bloomberg regime strips | Every team page |
| 14 | Bowl + CFP probability | **Probability Tornado** | 538 playoff boxes | Team Outlook module + `/playoff/` |
| 15 | Fan-conversation velocity | **Baseline Halo** | Polymarket volume-vs-base | Hub Heat + Pulse |
| 16 | Source-mention mix | **Source Bar Stack** | NYT "Where the news came from" | Source-Trust Ribbon + Daily + Wire |
| 17 | Hype vs reality gap | **Gap Slope** | NYT expectations vs outcomes | Hub (canonize) |
| 18 | Wikipedia interest spike | **Spike Comb** | NYT search-trends comb | Player Buzz + team Wikipedia card |
| 19 | Calendar density | **Year Heatcal** | GitHub contributions | `/freshness/` + Hub footer |
| 20 | Dynasty heatmap | **Dynasty Grid** | NYT "Decades of warming" | `/history/heatmap/` (fix this URL) |
| 21 | Predictive claim outcomes | **Verdict Tile** (Sig 4 compressed) | Pudding "Did our model work?" | Receipts + team Chronicle cards |
| 22 | Roster composition | **Class × Position Waffle** | NYT "Who's in Congress" | Team roster module |
| 23 | NFL pipeline | **Draft Pick Brick Tower** | FT tower charts | Team Pipeline module |
| 24 | All-American density | **Honor Dot Field** | NYT every Olympic medal | Team Honors + `/honors/` |
| 25 | Stadium / attendance trends | **Capacity Ribbon** | FT utilization | Team facilities |
| 26 | Coaching tenure ribbon | **Regime Bar** | Bloomberg CEO tenure | Inside Era Strip + `/coaches/` |
| 27 | Postseason history | **Era Marker Timeline** | NYT historical timelines | Team Postseason module |
| 28 | Conference realignment | **Realignment Sankey-over-Time** | NYT "How parties shifted" | `/realignment/` + `/conferences/` |

### Banned Patterns (refuse list)

- **Pie / donut charts.** Banned. Source-mention mix, roster composition, conference share — all have better encodings. Donuts signal "executive dashboard," not "editorial product."
- **Default 3-color stacked column charts.** The Tableau-default look is a tell. If a comparison wants stacked bars, use the Source Bar Stack (#16) treatment with custom palette and Phosphor glyphs in-segment.
- **Speedometers / gauges / KPI tiles with a needle.** "Belief at 42%" rendered as a car dashboard is a dead encoding. Use Probability Tornado (#14) or Mood Ribbon slice.
- **Word clouds.** Frequency ≠ importance, and the visual is junk-food.
- **Radar / spider charts** for player metrics. Savant Card outperforms radar on every comprehension axis. Radar gets shape-bias and rotational artifacts.
- **Generic line charts with axis defaults and Chart.js grid.** If a time series ships, it must have the house treatment: serif annotations, hairline grid (or none), Phosphor endcaps, JetBrains Mono callouts. Chart.js out-of-the-box is the signature of a tutorial, not a publication.
- **3D anything.** Including isometric bars, drop-shadow columns, perspective ribbons. Site reads paper, not PowerPoint.
- **Bubble maps where bubble area is the only encoding.** Hard to compare areas; use beeswarm (#8) or dot fields (#24).
- **Generic heatmaps with rainbow scales.** The Dynasty Grid (#20) uses a deliberate slate→crimson diverging ramp tied to site palette. Viridis and jet are off-brand.
- **"Top 10" horizontal bar charts with default sort.** If a ranking shipped as a flat bar chart, it failed the Bump Chart (#9) test — rankings move, the chart should show the motion.

---

## Part 7 · Chart Library Decision

**The pick: server-side Python-written inline SVG (primary) + Observable Plot (build-time fallback for Sankey only).**

**Three-sentence defense.** The build is already Python → static HTML shipping 69k pages with zero JS runtime — bolting a 150kB+ JS charting library to every page just to draw a sparkline is the opposite of editorial polish, it's the cost-center. FiveThirtyEight and NYT Upshot ship inline SVG written by their build scripts for ~90% of their charts and only reach for D3/Plot when interactivity earns its weight; this is what `reporting.py` already does on `/hub/`, and the 28 charts there are proof the pattern scales. Observable Plot gets the fallback slot only because its terse-than-D3 syntax compiles to the same SVG primitives we'd otherwise write by hand, and can run server-side at build time via `vl-convert` or Node-subprocess for the one genuinely-complex Sankey layout.

### Hard cuts

- **Chart.js** — canvas-based, kills a11y (canvas is not screen-reader-friendly), and the editorial polish ceiling is too low.
- **Highcharts** — commercial license cost + enterprise dashboard aesthetic.
- **Plotly** — bundle weight too heavy (~3MB unsplit / ~700kB split).
- **ECharts** — capable but the aesthetic is hard to escape.

### Per-pattern rendering decisions

13 of 14 patterns are pure Python inline SVG. Observable Plot earns its keep only on Sankey (and even there: run at build time, write the resulting SVG to disk).

### Drop-in `charts/svg.py` module (30-line code example)

```python
# src/cfb_rankings/charts/svg.py
from html import escape
from typing import Sequence

def sparkline(values: Sequence[float], *, width: int = 120, height: int = 28,
              stroke: str = "currentColor", title: str = "") -> str:
    """Inline SVG sparkline. Zero JS. A11y-labeled. Drop into any HTML string."""
    if not values:
        return f'<svg width="{width}" height="{height}" role="img" aria-label="No data"></svg>'
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    step = width / max(len(values) - 1, 1)
    pts = " ".join(
        f"{i * step:.1f},{height - ((v - lo) / span) * height:.1f}"
        for i, v in enumerate(values)
    )
    last_x = (len(values) - 1) * step
    last_y = height - ((values[-1] - lo) / span) * height
    label = escape(title or f"Trend: {values[0]:.1f} to {values[-1]:.1f}")
    return (
        f'<svg class="cfb-sparkline" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{label}">'
        f'<title>{label}</title>'
        f'<polyline fill="none" stroke="{stroke}" stroke-width="1.5" '
        f'stroke-linejoin="round" stroke-linecap="round" points="{pts}"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2" fill="{stroke}"/>'
        f'</svg>'
    )

# In reporting.py / team_pages / wire / reactions / mailbag / daily:
# from cfb_rankings.charts.svg import sparkline, percentile_bar, divergence_dumbbell, mood_ribbon, ...
# html += sparkline(team.mood_last_7_weeks, title=f"{team.name} mood, last 7 weeks")
```

Then `manage.py build-site` works exactly as today — no new build step, no Node dependency, no bundler. Each chart helper lives in `charts/svg.py`. `reporting.py` calls them and concatenates the returned strings into HTML.

### Migration plan for `/hub/`'s 28 existing inline SVGs

**Keep them. Lift the helpers into `charts/svg.py`, then refactor in place.**

1. **Audit pass (1 hour):** grep `reporting.py` for the existing 28 SVG sites — they're already shaped like the helper above, just inlined.
2. **Extract pass (~3 hours):** move each unique SVG-writing block into a named function in `charts/svg.py`. Rename inline call sites to use the helper. Visual diff one page before/after — should be byte-identical.
3. **Generalize pass (~4 hours):** parameterize against design-system tokens.
4. **Expand pass (ongoing):** every team page, every program page now has `from .charts.svg import *` available. Chart-shaped placeholders on profiled team pages become two-line Python calls.

**Do not** rewrite the 28 SVGs to use a JS library. They work, they're fast, they're zero-kB, and they're the proof point that the editorial-SVG-from-Python approach scales.

---

## Part 8 · Imagery Sourcing Pipeline

Mapped per category in three phases. **Total cost: ~$10/month (Midjourney sub); $0 for storage at this scale.**

### Per-category source matrix

| Category | Primary source | Coverage | Cost | Notes |
|---|---|---|---|---|
| FBS logos (134) | ESPN CDN `a.espncdn.com/i/teamlogos/ncaa/500/{id}.png` | ~100% | $0 | Fair-use editorial |
| FBS logos fallback | CFBD `/teams/fbs` `logos[]` | ~100% | $0 (already in pipeline) | Same |
| FCS logos (~129) | ESPN CDN + CFBD non-FBS | ~95% | $0 | Same |
| DII/DIII/NAIA logos (~400) | School athletics scrape + Wikipedia | ~70–80% | $0 | Falls back to wordmark/text |
| Wordmarks | School brand/media-kit pages (`brand.<school>.edu`, `<school>sports.com/media-resources`) | ~90% FBS, ~50% lower | $0 | Editorial press use |
| Helmet renders | Blender batch render (one base mesh + per-school recolor) | 100% by construction | ~1 build-day one-time | Original work; you own it |
| Stadium photos | Wikimedia Commons `Category:<Stadium>` (CC-BY-SA) + school media kits + Flickr CC | ~80% FBS, ~30% lower | $0 | Credit photographer; cache locally |
| Stadium illustrations (fallback) | Midjourney v7 panoramic | 100% by construction | ~$10 one-time burst | You own outputs |
| Player headshots — active | School roster scrape (universal — every athletics site has them) | ~98% FBS rosters | $0 | Press headshots; fair-use |
| Player headshots — historical | Wikipedia (top ~200), Pro Football Reference (NFL pipeline ~3k) | ~30% historical | $0 | Same |
| Coach portraits | School athletics Coach pages | ~100% active | $0 | Universal coverage |
| Action / game photography | Skip Getty/AP scrape — substitute with illustrations | ~5% | $0 | Use Midjourney illustration instead |
| Editorial illustration | Midjourney v7 (primary), Flux locally (volume) | unlimited | $10/mo MJ + GPU time | You own outputs |
| Historical / Canon | Library of Congress `loc.gov/free-to-use/football/` + university digital archives | ~40% pre-1970 | $0 | Public domain — credit LOC |
| Conference logos (11) | Wikipedia + conference media kits | 100% | $0 | Fair-use |
| Source-platform marks | Reddit, Bluesky, ESPN, On3, 247Sports, SB Nation, Locked On, Spotify, Wikipedia W, SeatGeek — each platform's brand page | 100% | $0 | Attribution + linking standard practice; fair-use latitude per owner |

### Phase A — Sprint immediate (2–3 days, ~$0)

**A1. All 664 program logos**, two sizes (500 + 100 dark/light variants), keyed by CFBD `school` slug. Walk `/teams/fbs` and `/teams` from CFBD → resolve to ESPN CDN URLs → cache locally to `output/site/assets/logos/{slug}.png` + `{slug}@2x.png`.

**A2. Helmet renders for top 50 programs.** Base `.blend` from BlenderKit (`Football Helmet by Rick Van Dyk`, GPL). Python `bpy` script: load school colors (CFBD has primary/secondary already in DB), swap shell + stripe + facemask materials, place procedural decal plane with school's logo PNG, render 3/4-angle at 1200×900 transparent PNG. ~3 sec/helmet × 50 = 3 minutes on any modern GPU. Output to `output/site/assets/helmets/{slug}.png`.

**A3. Source-platform marks** — Reddit snoo, Bluesky butterfly, ESPN, On3, 247Sports, SB Nation, Locked On, Spotify, Wikipedia W, SeatGeek. Each platform's official press/brand page → one SVG per source → `output/site/assets/sources/{platform}.svg`. Inline as `<use>` references in the Source-Trust Ribbon.

**A4. Conference logos (11)** — Wikipedia / official conference media-kit SVGs → `output/site/assets/conferences/{slug}.svg`.

### Phase B — Photography pass (1–2 weeks, ~$0)

**B1. Stadium photos for top 50 FBS programs.** Wikimedia Commons API: for each stadium name, query `categorymembers` → pick highest-resolution `image/jpeg` with permissive license → download with attribution metadata. Fallback: school athletics media-kit landing page. Output: `output/site/assets/stadiums/{slug}.jpg` (1600w + 800w responsive variants).

**B2. Player headshots for top 200 active players** (Heisman watch list + top QBs + projected first-rounders). Script: visit `<school>sports.com/sports/football/roster/<player-slug>`, find headshot `<img>` (most are at predictable `/imgproxy/.../headshot.jpg`), download. Output: `output/site/assets/players/{cfbd_player_id}.jpg`. Cache source URL in DB for roster-update re-fetches.

**B3. Coach portraits — all 134 FBS head coaches.** Same scrape pattern, `/coaches/{slug}`.

### Phase C — Editorial illustration system (ongoing, ~$10/mo)

**C1. Cover art for Chronicle cards** — one illustration per published Chronicle moment (~20/season).

**C2. Storyline hero illustrations** — one per active Storyline anatomy (~50/season).

**C3. Reactions / Mood-card flair** — generated per "loud" mood card weekly (~10/week × 16 weeks).

**C4. Historical era covers** — one per decade card in Canon (1880s–2020s = 15 covers, one-time).

### Editorial illustration style guide

**Style direction:** *Brad Holland conceptual realism × Edward Hopper light-and-mood × Christoph Niemann reductive geometry.* Painterly but considered; never glossy or AI-default. High-contrast moody light, restrained palette tied to school colors, with significant negative space the page can hold its own typography against.

**Midjourney v7 prompt scaffolding:**

```
{subject phrase}, editorial illustration in the style of a New York Times
Magazine cover, painterly gouache textures, dramatic chiaroscuro lighting,
restrained two-color palette of {primary_hex} and {secondary_hex} with
warm cream paper background, conceptual composition with significant
negative space top and right for headline typography, reductive shapes,
visible brush strokes, no photographic realism, no glossy AI rendering
--ar 3:2 --style raw --stylize 250 --v 7
```

**Negative anchors (always include):** `--no glossy, lens flare, 3D render, photoreal, generic stadium, anime, vector flat, gradient mesh, stock illustration, AI shimmer`

**Three template prompts:**

1. **Chronicle moment (event-driven):** `{verb-phrase like "the goal-line stand"}, single figure or two figures in silhouette against {stadium archetype}, charged stillness rather than action,` + scaffold.
2. **Storyline anatomy (concept-driven):** `conceptual visual metaphor for {storyline phrase like "the rebuild that wouldn't take"}, symbolic object on flat field,` + scaffold.
3. **Era card (historical):** `period-accurate illustration evoking {decade}, leather helmets if pre-1960, faded newsprint texture overlay,` + scaffold.

**Tool routing.** Midjourney v7 for hero covers (artistic punch wins). Flux 1.1 Pro locally for high-volume mood-card flair (zero per-image cost; fine-tune a LoRA on the first 30 approved MJ outputs to lock house style). DALL-E / GPT Image 2 only when art-directed composition with embedded text labels is needed (rare).

### Automation pipeline — new `scripts/imagery/`

Each script idempotent + invoked from `publish_site.ps1`:

| Script | Purpose | Output |
|---|---|---|
| `fetch_logos.py` | Walk CFBD `/teams` + `/teams/fbs`, pull `logos[]`, download to local cache | `output/site/assets/logos/{slug}.{png,webp}` |
| `fetch_conferences.py` | Static list of 11 → Wikipedia SVG → local | `output/site/assets/conferences/{slug}.svg` |
| `fetch_stadium_photos.py` | Wikimedia Commons API per stadium, license filter, attribution stored alongside | `output/site/assets/stadiums/{slug}.{jpg,webp}` + `{slug}.attr.json` |
| `fetch_roster_headshots.py` | For each team in `top_active_players` view, scrape `<school>sports.com/.../roster/{slug}`. 1 req/sec, retries with backoff | `output/site/assets/players/{player_id}.jpg` |
| `render_helmets.py` | Driver: `blender -b helmet_base.blend -P helmet_render.py -- --slug=<x>` per program | `output/site/assets/helmets/{slug}.png` |
| `generate_editorial_art.py` | Read `chronicle_moments` + `storylines` tables for un-illustrated rows, call Midjourney/Flux API, cache local | `output/site/assets/editorial/{moment_id}.jpg` |
| `optimize_imagery.py` | Final pass: resize to responsive (320 / 640 / 1280 / 1920w), encode WebP + AVIF, write manifest | All variants + `imagery_manifest.json` |

`reporting.py` and `team_pages/` look up imagery via single helper `asset_for(slug, kind)` reading the manifest, returns best-fit URL with `<picture>` fallback. Kinds: `helmet`, `stadium`, `headshot`, `hero`, etc.

Attribution: every Wikimedia/LOC asset writes sidecar `.attr.json` with `{title, author, license, source_url}` — surfaced at the bottom of any page using it.

### Storage + serving — Cloudflare R2 + Cloudflare Images

- **3,500 assets × ~120 KB average** (post-WebP) = ~420 MB. Comfortably under R2's 10 GB free tier indefinitely.
- R2 wins over Vercel Blob because of zero egress fees.
- Cloudflare Images on top gives 5,000 free transformations/month — enough for initial cache fill; steady-state runs on cache hits.
- `https://img.cfbindex.com/` as public bucket binding. `output/site/` keeps only CSS hash bundle + manifest JSON. All `<img>` tags emit `srcset` pointing at `img.cfbindex.com`. Build step uploads only deltas (hash-compare local vs remote metadata).
- Local dev: same scripts cache into `output/site/assets/` (gitignored) so `python manage.py build-site` works offline; upload-to-R2 step runs only in `publish_site.ps1`.

---

## Part 9 · Scroll-Tied Editorial Storytelling

The third axis of "premium editorial" — after typography and imagery — is **scroll-tied storytelling**. The NYT Snow Fall (2012) lineage. Pudding.cool's signature. Bloomberg's Big Take features. The pattern where the visual *changes as you scroll* through prose.

### Library recommendation: Scrollama primary, GSAP ScrollTrigger for 3 targeted surfaces

**Scrollama** ([repo](https://github.com/russellsamora/scrollama)) is the default. IntersectionObserver-based, ~3 KB, zero dependencies. Step-callback model maps 1:1 onto the patterns Editions / Canon / Storylines / Hub need. Battle-tested at Pudding for exactly this kind of editorial work.

For three surfaces specifically — Editions cover cinematic, Player career-arc SVG draw, Rivalry build-to-kickoff sequence — layer in **GSAP ScrollTrigger** (now [100% free for commercial use](https://gsap.com/docs/v3/Plugins/ScrollTrigger/)). Avoid Lenis / Locomotive Scroll — they hijack native scroll, break accessibility, and v2's a11y audit already flagged assistive-tech surface area.

### Must-have-3 — the surfaces that earn the complexity

1. **Editions cover essay opens with a pinned cinematic intro.** Pattern 4 (pinned cinematic) + Pattern 2 (step-by-step chart reveal mid-essay). Full-bleed scene that animates 3 beats (week label morphs, hero stat counts up, hero photo desaturates as overlay text drops). Mid-essay, supporting chart pins and reveals series one paragraph at a time. **Highest-leverage editorial signal of ambition** — Snow Fall lineage works precisely because the pinned hero is unambiguous about ambition. Without this, every other surface still reads as "well-designed blog."

2. **Player profile career arc draws itself on scroll.** Pattern 6 (SVG line-drawing). Sports stories *are* time-series at their core; a self-drawing arc tied to scroll is the rare scroll-tied move that genuinely earns its complexity because the reader's eye and the prose lock together as the player's career unfolds. **This is the move that gets CFB Index shared by analytics-Twitter.**

3. **Dynasty heatmap fills progressively as you scroll a program's history.** Pattern 5 (progressive fill-in). The Pudding's responsive-scrollytelling guide is explicit: change-over-time is the one justification that survives the mobile compromise. A 12-season heatmap that fills chronologically while annotations call out coaching changes, NCAA sanctions, and titles is the "I am reading something serious" moment for the Programs section — the section with the most pages (662 unprofiled + 17 profiled) and therefore the most leverage.

### Full pattern catalog — 10 patterns mapped to CFB Index surfaces

| # | Pattern | CFB Index ship | Library |
|---|---|---|---|
| 1 | Sticky-graphic + scrubbed annotations | Editions essay mid-section | Scrollama |
| 2 | Step-by-step chart-element reveal | Canon entries; Hub stories | Scrollama |
| 3 | Parallax foreground/background | Storyline thread hero | Scrollama (subtle) |
| 4 | Pinned cinematic section | **Editions cover** (must-have) | GSAP |
| 5 | Heatmap progressive fill-in | **Dynasty heatmap** (must-have) | Scrollama + D3 transition |
| 6 | SVG morphing / line-drawing | **Player career arc** (must-have) | GSAP DrawSVG |
| 7 | Scrubbed image sequence | Rivalry build-to-kickoff (marquee games only) | GSAP |
| 8 | Year-by-year timeline activation | Storyline thread anatomy | Scrollama |
| 9 | Step-driven map / spatial reveal | Realignment Sankey-over-time | Scrollama |
| 10 | Lottie waypoints | Cover-essay accents | Scrollama + Lottie |

### Implementation budget — 19 days, 4 weekly slices

| Surface | Days |
|---|---|
| Shared infrastructure (Scrollama bundle, `prefers-reduced-motion` gate, sticky-side CSS partial, reusable `scrolly-step` Jinja macro) | 2.5 |
| Editions cover essay (pin + reveal) | 3.5 |
| Storyline thread anatomy | 1.5 |
| Canon entries | 1.0 |
| Player profile (career-arc draw + Accolade Lens pin) | 3.0 |
| Dynasty heatmap progressive fill | 2.0 |
| Rivalry card image-sequence countdown | 2.5 |
| Mood-mover Hub 7-week reveal | 1.5 |
| Reduced-motion fallbacks + iOS viewport testing + manual pause control | 1.5 |
| **Total** | **~19 days** |

### Accessibility note (WCAG 2.3.3)

`prefers-reduced-motion: reduce` must short-circuit all scroll-tied animations to static reveals — chart elements appear at full position, no transition, on initial mount. The v2 audit found 15 motion declarations firing even with reduced-motion on. Fix that first; scroll-tied work compounds the bug class if left unfixed.

---

## Part 10 · Updated Roadmap (Folding v1 + v2 + v3)

The full body of v1 + v2 + v3 sequences into 6 sprints (~10 dev-weeks).

### Sprint 9.5 — Foundation (1 week)

- Build `src/cfb_rankings/common/design_tokens.py` — canonical color/font/spacing source. Token values from Part 3.
- Migrate every renderer to import from it (Wire, Mailbag, Reactions, Daily, Storylines, Editions, Hub, team_pages).
- Add `@font-face` recipe — Charter + Inter + Bowlby One SC + Recoleta Stencil + JetBrains Mono — via `output/site/assets/fonts.css`.
- Build single `_render_head_chrome()` helper so every renderer's `<head>` emits preload + stylesheet trio. Fixes the three Times-New-Roman pages.
- Externalize team-page inline CSS to `/assets/team-page.css` (saves ~300 KB across 150 pages).
- Move every `--motion-*` declaration into `prefers-reduced-motion: reduce` block.
- Replace `#c9a24a` accent (fails WCAG AA) with `#996c00` or shift paper bg to `#fafafa`.

### Sprint 10 — Atoms + Charts Library (1 week)

- Build `src/cfb_rankings/charts/svg.py` per Part 7 — sparkline, percentile_bar, divergence_dumbbell, mood_ribbon, era_strip, receipt_strip, savant_card, dynasty_grid, beeswarm, sankey (Plot at build-time), heatcal, win_prob_timeline, bump_chart.
- Build `src/cfb_rankings/common/atoms.py` — extract reusable components from `team_pages/savant_card.py`, `rivalry_card.py`, etc.
- Add `CohortDivergenceBar` atom (Signature 2) — **this is Move C, the universal brand atom**.
- Add `SourceTrustRibbon` atom (Move B from v2).
- Add `ReceiptStrip` + `VerdictTile` atoms (Signature 4).
- Add `MoodRibbon` atom (Signature 1).
- Add pull-quote, drop-cap, marginalia, body-width-cap as global utility styles.
- Wire source-attribution chip column into Wire.
- Fix Reactions to actually call `_sentiment_bar()` in archive render (helper exists, never invoked).
- Replace bottom-nav emojis with Phosphor SVG sprite + bespoke 12-glyph commission triggered.

### Sprint 11 — Imagery Pipeline (1 week)

- Phase A: `fetch_logos.py` + `fetch_conferences.py` + Phosphor source-platform marks via `<use>` references + 12-glyph bespoke commission delivered.
- `render_helmets.py` — Blender batch for top 50 programs.
- Phase B kickoff: `fetch_stadium_photos.py` + `fetch_roster_headshots.py` for top 200 + `fetch_coach_portraits.py` for all 134 FBS coaches.
- Cloudflare R2 bucket provisioned + upload step in `publish_site.ps1`.
- Build the `asset_for(slug, kind)` helper + `<picture>` emission pattern.

### Sprint 12 — Renderer Rebuilds (2 weeks)

- Rebuild `reactions/renderer.py` to magazine-card pattern using `CohortDivergenceBar` as cover art (Big Swing B3 from v2).
- Rebuild `wire/renderer.py` to triage console with filters, IMPACT left-stripe, source-attribution chips, team-logo column, mobile card transform.
- Rebuild `daily/renderer.py` to Bloomberg-terminal-style dashboard (Big Swing B10).
- Add `ThreadPill` (Active/Dormant) + chapter-density EKG to `storylines/renderer.py`.
- Fix `/players/spotlight.html`, `/players/the-room.html`, `/history/heatmap/` rendering pathologies (Times New Roman fallback, 769px stubs).
- Wire `Compare` to data + ship Savant mirror bars (Basketball-Reference pattern).
- Lift cohort-divergence bar from text to SVG atom on the homepage Canon callout.

### Sprint 13 — Identity + Methodology (2 weeks)

- Add `--bg-tint: rgba(var(--accent-rgb), 0.04)` per program to profiled team pages.
- Add 4 program personality typography classes (`.program--blue-blood`, `.program--contender`, `.program--regional`, `.program--rebuild`).
- Build heritage trophy shelf SVG icon row.
- Replace rivalry-trajectory `<img>` placeholder with real Dual-Line Build SVG.
- Broaden Pulse `mood_lookback_60d` to render sparkline during low-floor weeks.
- Ship `SourceTrustRibbon` below every team-page hero + on homepage cover (Move B full surface).
- Rewrite `/methodology/fan-intelligence.html` with force-directed source graph + Tier matrix grid + live per-source freshness counters.
- Ship CFB Visual Vocabulary primitives (Motif A yard-line divider; Motif B helmet-stripe rule; Motif C decal-cluster footer).

### Sprint 14 — Editorial Polish (2 weeks)

- Scroll-tied storytelling Phase 1: shared infrastructure (Scrollama bundle, `prefers-reduced-motion` gate, sticky-side CSS, reusable `scrolly-step` macro).
- Editions cover essay pinned cinematic intro (GSAP).
- Player profile career-arc self-drawing on scroll (GSAP DrawSVG).
- Dynasty heatmap progressive fill on scroll (Scrollama + D3 transition).
- Phase C editorial illustration kickoff: Midjourney v7 for Chronicle covers + Storyline heroes; Flux LoRA fine-tune from first 30 approved outputs.
- Editions cover generator (Pillow + `viz_templates/`) — one generated cover per issue.
- Sortable-column highlights on Wire + Rankings.
- Chart-on-scroll reveal across every inline SVG via IntersectionObserver.

### Sprint 15 — Polish Tail (1 week)

- Storyline thread anatomy timeline (Scrollama).
- Rivalry build-to-kickoff scrubbed image sequence for marquee games only.
- Mood-mover Hub 7-week reveal (Scrollama).
- Convert team-art PNGs → WebP, ship `<picture>` fallback everywhere.
- A11y final pass: WCAG contrast fixes, touch-target audit, heading-hierarchy sweep, reduced-motion verification.
- Lazy-load team OG images on archive/index pages.

**Total: ~10 dev-weeks across 6 sprints.** Identity moves (Cohort-Divergence Bar atom, Source-Trust Ribbon, Masthead typography, CFB Visual Vocabulary primitives) ship in Sprint 9.5 + 10 — the first two weeks. Imagery pipeline lights up Sprint 11. Renderer rebuilds Sprint 12. The site is recognizably itself by end of Sprint 13.

---

## Part 11 · The Closing Question

**"What does this site look like when it's done?"**

A reader lands on `/teams/alabama.html`. Above the masthead: a 3px crimson conference-rule (SEC). Below: a helmet-stripe band — crimson with a thin white center stripe — running through the program name in reversed end-zone-paint script ("ALABAMA"). To the right, a Source-Trust Ribbon: `reddit ●2h · bluesky ●14m · espn ●4h · campus ●1d · wikipedia ●12h · seatgeek ●9h · gdelt ●live · locked-on ●3h`. Tier-A sources green-dotted, Tier-D gray. Hover reveals "last Reddit ingest: 14 min ago — 1,243 mentions today across r/CFB, r/Alabamafootball, r/RollTide."

Below the ribbon, the Pulse module — a Mood Ribbon (Signature 1) at 24px tall × 52 weeks wide, current week tick in `--gold-october`. Next to it, a Divergence Dumbbell (Signature 2) showing stat-folks rank 4 vs casual-fans rank 12 with a bold "Δ 8" on the rod.

Yard-line stripe divider (Motif A). Below: the Savant Card (Signature 3) — 13 horizontal percentile bars with peer-set toggle (FBS / Power-4 / Conference / Program 2014+), capsules in a slate→crimson diverging ramp, JetBrains Mono numerals inside each capsule.

Marching-band gold-trim section divider (the metallic-gradient 2-rule). Below: the Era Strip (Signature 5) — 12 horizontal tracks showing SP+ line, AP-final dots, Coach color-band background (SABAN → DEBOER), CFP-bid stars. Bracket-eligible years marked with CFP bracket geometry (Motif #8).

Section break. Receipt Strip (Signature 4): "THE MODEL · Sept 1 said Alabama 9-3, mid-SEC contender. They're 11-4. · ↑ Aged Well 84%." Verdict Tile in JetBrains Mono.

Player rail: five Phosphor `User` placeholders with headshot photos from the school athletics roster scrape, jersey numbers in Bowlby One SC overlay, position chip beneath, mini Savant 4-metric variant on hover.

Heritage trophy shelf — three reward-decals (Motif #2) — 3 national titles in `--crimson`, 8 CFP-bid stars in `--gold-october`, 6 Heisman laurel-glyphs in brass. Clickable to era archives.

Rivalry card — Iron Bowl. Two-line Dual-Line Build SVG (Pattern #12) showing 4-week build to kickoff, Alabama in crimson line and Auburn in burnt-orange. Trophy iconography (Motif #7) — the Iron Bowl trophy outline. Below: posture panels, last-10 meetings with editorial commentary.

Footer: marching-band gold-hairline trim. Decal-cluster footer mark (Motif C). "© 2026 CFB INDEX · BUILT FOR THE OFFSEASON · VOL. I · NO. 17 · MASTHEAD: EDITOR'S DESK · RECEIPTS DESK · COHORT DESK · CONNECTIONS DESK · FAN-VOICE DESK."

Reader scrolls back to top. The Mood Ribbon reveals itself bar-by-bar via IntersectionObserver (chart-on-scroll). At the bottom of the page, a subtle 3% paper-grain noise overlay catches the eye. The page reads dense but unhurried — like a magazine, not an app.

**Nothing on the page is generic-sports.** Every decorative move comes from somewhere specific in college football's century-long iconographic tradition. The data is dense, the visuals are crafted, the typographic register is editorial, the color palette is unmistakably Saturday afternoon in October. A screenshot, cropped to any module, is recognizably CFB Index.

This is the site when it's done.

---

## Appendices

### A. Investigator outputs (summary)

| # | Investigator | Output |
|---|---|---|
| 1 (v2) | DB schema | 5 empty moat tables, backfill-aware matrix |
| 2 (v2) | Renderer architecture | 15-renderer quality matrix; 5 hardcoded gold hex values |
| 3 (v2) | Competitive references | 15+ named treatments with URLs across 8 categories |
| 4 (v2) | Icons / fonts | Phosphor primary + 12-glyph commission + font-loading recipe |
| 5 (v2) | Design critique | Typography psychology + CFB color palette + 3 brand-identity moves |
| 6 (v2) | A11y / perf | WCAG contrast failures + perf measurements (77 MB images, 300 KB inline-CSS dupe) |
| A (v3) | Imagery density benchmark | 27 reference pages counted; per-page-type norms; CFB Index gap quantified |
| B (v3) | Chart library | Python-SVG primary + Observable Plot for Sankey; `charts/svg.py` drop-in |
| C (v3) | Photo / illustration sourcing | 3-phase pipeline; Cloudflare R2 storage; Midjourney style guide |
| D (v3) | Data-vis pattern catalog | 28 patterns × CFB data types; 5 signature visualizations; banned-pattern list |
| E (v3) | CFB iconic visual language | 12-motif vocabulary + color/typography/motif rules; fall-Saturday-feel recipe |
| F (v3) | Scroll-tied storytelling | Scrollama + GSAP; must-have-3; 19-day budget |

### B. The five token-system files retired

`docs/design-system/00-tokens.md`, `docs/design-system/unified-design-tokens.md`, `output/site/assets/cfb-index.f3924a06eced.css` (token portions), `src/cfb_rankings/team_pages/assets/tokens.css`, `tools/wcfb_enhancements/wcfb-enhancements.css` (`--wcfb-*` prefix). All consolidated into `src/cfb_rankings/common/design_tokens.py` per Part 3.

### C. The five hardcoded gold hex values retired

`#c9a24a` (Wire, Mailbag, wcfb-enhancements), `#E0A300` (Hub), `#f4c95d` (Reactions), `#c5b358` (team_pages default), `#FFB800` (main bundle focus ring) → single `--gold-october: #e8a93a` per Part 3.

### D. Source attribution

This audit was produced via twelve parallel investigations across two phases (v2 + v3), orchestrated by Claude. Specific factual claims about peer publications are sourced inline. Specific code-line and grep-result claims are cited to file paths in the local working tree. The CFB Visual Vocabulary draws on ESPN's 2025 College Football rebrand (Behance, ESPN Front Row, NewscastStudio writeups), The Athletic editorial design portfolio, Pudding scrollytelling guides, FT Visual Vocabulary, and the design-system spec docs already in `docs/design-system/`.
