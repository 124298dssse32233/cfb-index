# The Language Layer — Data Viz Spec (research-backed)

_Drafted 2026-06-10 from a four-thread state-of-the-art sweep (language-data viz canon ·
typography-as-data · sports/share-card products 2025-26 · chart-form deep dives).
Companion to [fan_lexicon_brief.md](fan_lexicon_brief.md). Design-system restrictions
waived per Kevin; these are the forms we build._

## The two laws (every surface obeys both)

1. **The printed number is the source of truth; geometry is the dramatization.**
   Every term carries its raw multiplier as a mono text chip ("×87.8"). This is what
   lets us use aggressive scales (log) honestly. Never a filled bar on a log axis
   (area-lie), never a broken axis (measurably misleads even after warnings).
2. **No claim without a receipt.** Every bar/dot/spike resolves to a verbatim,
   provenance-stamped fan quote within one screen-height (tap on interactive,
   printed below on static). The receipt block is a single component, built first.

## Component 0 — The Receipt Block (build before anything else)

Pattern: NPR annotated-Mueller-report + Genius annotation + KWIC concordance.
- Dark card, **serif quote** (source-medium styling, distinct from UI chrome)
- Team-color highlight span on the EXACT analyzed term — never the whole quote
- Mono provenance line: `r/MichiganWolverines · Nov 30 2025 · 4.2k upvotes`
- Unedited surrounding context (KWIC principle)
- Renders the existing citation wire format (design-system 32-receipt-pattern.md)

**KWIC detail view** (word-of-week, lexicon term tap): 8-10 occurrences, keyword
center-aligned in a fixed team-color column, flanks truncated with fade masks.
Nobody in sports media has this; corpus linguistics never made it beautiful.

## Per-surface decisions

### 1. The Lexicon → "the foundry catalog of a fanbase"
- **Hero**: the #1 word as a full-bleed viewport-scaled type specimen (Anton),
  mono metadata strip beneath: `×87.8 · RANK 1 · PEAK WK 12 · n=863`.
- **Body**: the **word wall** — Bertini's rules: sorted descending (sort IS the
  encoding), left-aligned shared baseline, ONE magnitude axis = variable-font
  weight 300→900 (Hepta Slab for display — near-constant width across weights;
  Recursive where mono voice is needed), size-ratio cap ~3.5×, mono `×NN.N` chip
  on every word. Sectioned like a foundry catalog: PLAYERS / COACHES / SLANG / ENEMIES.
- **Chart form** (where a chart, not a wall): **log-scaled lollipop** — dot position
  on log10 axis anchored at 1× (parity), gridlines at 1/3/10/30/100×, raw multiplier
  as right-gutter label, color = magnitude band (≥10× "signature" / 3-10×
  "characteristic" / <3× "mild"). "Log scale" printed near axis.
- Below-threshold terms grayed, not hidden ("statistically shy").
- VF cost: subset woff2 ≈ 30-60KB; weight-as-data is free at render on static pages.

### 2. The Leaderboard (new surface — highest virality/effort)
Pudding "Largest Vocabulary in Hip Hop" pattern (most-shared language viz ever):
**every FBS fanbase on ONE axis** per metric (profanity rate, optimism vocabulary,
rival-mention rate, lexical diversity) — team logos on the axis, external benchmarks
pinned ("average r/NFL fan," "Shakespeare n=5,170 unique words"). Fans screenshot
the neighborhood around THEIR team = 136 personal charts from one build.
NBA My Season framing on claims: "Xth of 136 fanbases."

### 3. Word of the Week → a type-specimen sheet
Format it as a font release (Archival Index aesthetic, on-trend 2026):
- Top: the word, monumental (Anton).
- Middle: **specimen waterfall as sparkline** — the word set 7× (Mon-Sun), each
  instance's font-weight mapped to that day's mention volume. A sparkline made of
  the word itself. Pure CSS, zero JS.
- Bottom: mono metadata grid — FAN DEFINITION / ×N vs SEASON BASELINE
  (Merriam-Webster "+2,400%" framing) / FIRST RECORDED / PEAK HOUR / SPECIMEN QUOTE.
- Term chips elsewhere use **betting-app pill states**: ▲ green price-up flash /
  ▼ red price-down ("'tampering' ▲ +340% this week") — grammar fans already read.
- Annotated single-line chart only when the spike's CAUSE is pinned (a game, a
  firing). Spike without cause is trivia; never multi-line spaghetti.

### 4. Eras → annotated era-band timeline (+ bump backbone)
- **Primary**: NYT-style **chapter banding** — season axis, tinted era bands,
  chapter title in display type (LLM-named via Chronicle), the 2-4 evidence terms
  + 1 receipt quote INSIDE each band. Band edges anchored at the week the new
  vocabulary crossed in (JS-divergence between adjacent weeks). Straight segments
  between real week boundaries — never smooth (fabricates change).
- **Drift backbone**: bump chart of term rank-by-week, ≤8 lines, 1-2 highlighted
  in team color, rest gray; label crossings ("'portal' overtook 'spring game' wk 3").
  Spotify Wrapped 2025 "Top Artist Sprint" = the emotional framing: storylines racing.
- **Showcase form** (tentpole): Pudding-democracy-2025 **dot matrix** — each dot =
  N posts containing the era term, lit dots = LLM-classified dominant sense
  (dread vs excitement around "portal"). Counting is commodity; classifying meaning
  with the local model is the moat. Mobile-perfect, fully static.
- **Banned**: streamgraphs (floating baseline, cliché, fabricated interpolation).
- Apple Music Replay relationship-verbs for season cards: "Comeback word: 'playoffs'
  (last seen 2021)" / "Loyalty word: 'Saban' (6 straight seasons top 10)."

### 5. Rivalry Mirror → fight card meets She Giggles, He Gallops
- **Header**: tale-of-the-tape — both team names stacked in condensed caps
  (Anybody Black ≈ free Knockout) flanking a centered ×.
- **Body**: **diverging tug-of-war lollipops** off a shared center spine on
  log-keyness — dots not bars, sorted by |keyness|, mono multiplier at each tip.
  Thin underline bar for honest magnitude under each sized word (size = poster,
  bar = proof).
- **The mirror word row**: the same word ("harbaugh") set twice, once per side,
  weight ∝ each side's usage rate — typography literally showing who owns the word.
- **Center column**: words both sides use at the same rate, small/gray/roman —
  shared language is its own finding.
- **Asymmetry is the headline, never a distortion**: normalize per-corpus (rate
  per 1k mentions) first; state volume imbalance explicitly ("OSU fans wrote 3× as
  much about Michigan"). Equal scales both sides, always.
- Receipts under each side. Desktop "explore" view: scattertext two-axis scatter
  (term rate side A vs side B, diagonal = shared) — mobile default stays lollipop.
- Underdog higher/lower mechanic for engagement: "Which fanbase said 'embarrassing'
  more this week?" — reveal is the payoff.

### 6. Fanbase Personality → FIFA card wrapping Savant bars
- **Source of truth**: 5 horizontal percentile bars, fixed 0-100 axis, **median
  tick at 50 visible**, percentile ramp color, right-gutter number. 5 traits max.
- **Identity wrapper**: card with archetype label in display type ("LOUD · LOYAL ·
  DOOMER"), team mark, **printed rarity** — "NERVOUS OPTIMISTS — 1 of 7 fanbases"
  (YouTube Recap 2025: rarity 0.1-30% printed on card = the share trigger).
- **Distribution-overlay dot** (Colin Morris mirrored histogram): each stat shown
  as your-team dot ON the all-FBS distribution — "97th percentile profanity" with
  the dot visibly in the tail. Converts percentiles into tribal pride.
- Pentagon/radar: ONLY as a small decorative sigil on the card (single entity,
  never overlaid, never the readable form).
- Future viral move: "Which fanbase do you talk like?" quiz (NYT dialect-quiz
  mechanic — the reader becomes the dataset; corpus already powers it).

### 7. Discourse Atlas → named cluster cards, not a scatter
- Raw UMAP scatter of 136 points = research toy. Ship **named neighborhood cards**:
  embed → cluster → LLM-label offline; each card = cluster name ("The Blue-Bloods
  Who Talk Like Pros"), member logos, 3-4 shared vocabulary traits.
- If a single map is wanted: **hex-tile grid** snapped (adjacency = similarity,
  no false precision), color by cluster, label centroids only.
- Caption honesty: "closeness = similar vocabulary; distances not to scale."

## Share-card spec (all surfaces)
- Design 9:16 (1080×1920) with content in the central 1080×1420 safe band
  (2026 Meta safe zones: 250px top, ~340px bottom); center-crop → 16:9 OG variant.
  Two exports, one composition.
- Card grammar: ONE huge number (Wrapped 2025 retreated to exactly this) + one
  claim type per card (rarity / identity / tribe) + team color & logo NON-NEGOTIABLE
  (Fox scorebug lesson: fans punish chrome novelty, reward team identity) + quiet
  wordmark attribution inside safe zone.
- The raw phone screenshot must already BE the card (bet-slip/Sleeper lesson —
  fans screenshot regardless; design for it).
- Recap cards must be MORE theatrical than the stats page (Letterboxd 2025 failure:
  recap that looks like the stats page doesn't get shared).
- Absurd units welcome (Reddit bananas): "OSU fans typed 14 Hamlets' worth of
  Michigan analysis in November."

## Typography stack additions (Noir-compatible)
- **Hepta Slab** (wght 1-900, near-constant width) — word-wall magnitude axis.
- **Anybody** (wght 100-900 + wdth 50-150) — Anton-adjacent condensed black WITH
  a data axis; fight-card stacks; era "voice" (width) sparingly, one flavor axis max.
- **Recursive** — data-bearing mono (Plex Mono has no VF; Recursive is its cousin).
- Big multipliers set like JERSEY NUMBERS (outlined block numerals), not like stats.
- Use registered CSS properties (font-weight) over font-variation-settings
  (axis-clobbering footgun); font-display: swap; subset to caps+digits.
- Scroll-driven reveals (animation-timeline): Chrome/Safari enhancement only,
  Firefox still flagged — never structural. Magnitude lives in the static frame
  (the screenshot test).

## Module naming (Prime Vision lesson)
Every surface ships as a NAMED product with a fixed visual signature — The Lexicon,
The Mirror, The Backometer (existing), Word of the Week, The Atlas. Named features
are discussable and meme-able; we already do this instinctively.

## Mockup deltas (apply to language_layer_mockup.html)
1. Lexicon filled bars → log-lollipops + magnitude-band colors (current bars are
   the area-lie this spec bans).
2. Word of the Week chips → specimen sheet with weight-waterfall.
3. Mirror → add tale-of-the-tape header, mirror-word row, explicit volume-asymmetry
   stat, dots instead of side text lists.
4. Personality cards → add archetype label + rarity line + median tick at 50.
5. Receipts → restyle as the Receipt Block component (serif quote + team-color
   term highlight + mono provenance).

## Build order
0. Receipt Block component (multiplies everything else)
1. Lexicon word wall + log-lollipop (engine output exists)
2. Word-of-the-week specimen sheet (weekly beat starts accruing era history)
3. Leaderboard (one build = 136 shareable team views)
4. Mirror fight card
5. Personality identity card
6. Era bands (needs weeks of in-season keyness history; backfill seeds it)
7. Atlas cluster cards (offseason tentpole)
