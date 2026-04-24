# Archive Modules

Modules that contextualize the current season against the program's broader arc: CFP-era view (zoomed-out trajectory) and historical season deep-dive (season-as-chapter).

## `CFPEraView`

**Role:** Zoomed-out multi-metric view of the program's CFP-era history. Two-line trajectory chart (mood + AP rank) across 2014-current with CFP appearances annotated as vertical gold lines. Below the chart: 13-season brick index + editorial closing paragraph + peer-context footer.

**Structure:**
1. Header — era title + thesis
2. 5-column meta strip (record · CFP appearances · title games · top-10 finishes · titles)
3. Trajectory chart (SVG, 640×200)
4. 13-season brick index (compact clickable cards linking to season deep-dives)
5. Closing paragraph (serif, editorial)
6. 3 peer-context stats footer

**HTML outline:**
```html
<section class="cfp-era-view">
  <header>
    <span class="eyebrow">the era · {{ start_year }} through now</span>
    <h2 class="cfp-era-view__title">The CFP Era</h2>
    <p class="cfp-era-view__thesis">{{ era_thesis_paragraph }}</p>
  </header>

  <dl class="cfp-era-view__meta">
    <!-- 5 dt/dd pairs: record, CFP, title games, top-10, titles -->
  </dl>

  <div class="cfp-era-view__chart-frame">
    <header class="cfp-era-view__chart-header">
      <span class="eyebrow">mood across the era · external rank for context</span>
      <div class="cfp-era-view__legend">...</div>
    </header>
    <svg viewBox="0 0 640 210">
      <!-- gridlines (3) -->
      <!-- CFP appearance vertical markers (amber) with labels -->
      <!-- AP rank polyline (thin, navy, opacity 0.75) -->
      <!-- Mood polyline (thick, coral) -->
      <!-- annotation dots for key peaks/valleys with callouts -->
      <!-- era ribbon at bottom (coaching regimes) -->
      <!-- x-axis labels every 2 years + "now" at rightmost -->
    </svg>
  </div>

  <section class="cfp-era-view__chapters">
    <span class="eyebrow">chapters · tap any to open the archive</span>
    <div class="cfp-era-view__chapter-grid">
      {% for season in cfp_era_seasons %}
        <a href="/teams/{{ team.slug }}/seasons/{{ season.year }}" class="season-brick season-brick--{{ season.state }}">
          <span class="season-brick__year">{{ season.year_short }}</span>
          <span class="season-brick__record">{{ season.record }}</span>
        </a>
      {% endfor %}
    </div>
  </section>

  <div class="cfp-era-view__closing">
    <p class="cfp-era-view__closing-text">{{ closing_paragraph }}</p>
  </div>

  <dl class="cfp-era-view__peer-footer">
    <!-- 3 dt/dd pairs: era avg SP+, era mood avg, gap-from-#1 -->
  </dl>
</section>
```

**Chart data contracts:**
- `ap_rank_points` — 13 normalized values (higher is better, 0-100) for AP rank each year
- `mood_points` — 13 mood scores (0-100) averaged per season
- `cfp_appearances` — array of years with CFP bids, used for vertical annotations
- `era_ribbon_bands` — array of `{coach, start_x, end_x}` for the ribbon at y=170
- `key_annotations` — 2-4 callouts for major moments (the bottom, the peak, the title game) with (x, y, label)

**Season brick states:**
- `season-brick--winning` — navy 10% bg, navy border
- `season-brick--peak` — amber 18% bg, amber border (for CFP years)
- `season-brick--title-era` — amber 22% bg, amber border, 500 weight (for the featured title-game year)
- `season-brick--crisis` — red 15% bg, red border (for losing season)
- `season-brick--current` — transparent, 1.5px ink border
- `season-brick--data-gap` — striped neutral bg, "—" record, canonical CFP badge if applicable (use this when no per-game data exists but canonical `CFP_HISTORY` carries a title/appearance)
- `season-brick--partial-data` — dimmed record color (muted), italic `(partial)` suffix after record, same border as `--baseline` (use this when the DB has an incomplete season — e.g. 8-0 with games missing — to avoid rendering a mid-season snapshot as if it were the final record). Loader is responsible for detecting: mark partial when `games_played < expected_games_for_era(year)`.
- `season-brick--baseline` — default state for any season without peak/title/crisis/current/gap/partial classification

**Chart polish requirements (v1.1 — post-sprint-3 audit):**
- `viewBox` must be `0 0 640 210` (was 180) to make room for era ribbon at y=186–200.
- **Era ribbon** renders at bottom of chart. Each band is a colored rect with 28% opacity + coach-name label in 9px uppercase Inter Semi Bold. Example for Alabama: Saban band 2014–2023 in crimson-at-28%, DeBoer band 2024–now in crimson-at-40% (incoming regime brighter than steady-state). Ribbon is load-bearing narratively — it lets the viewer see the coaching regime behind the trajectory shape.
- **Year labels** render every 2 years at y=205, in `--fg-subtle` 10px Inter Medium. Rightmost label is `NOW` in `--accent-primary` 10px Semi Bold + letter-spacing 1.
- **CFP vertical markers** (gold) extend full chart height with 4px dot at top and "CFP" label in 9px Semi Bold 18px above the dot.
- **Key annotations** (2–4 per arc) render as `<text>` with serif italic 10px, positioned inside the chart near the annotated polyline point. Required format:
  - `{ x_index: int (0-based season index), y: "mood"|"ap", label: str, color: token }` — renderer computes pixel coords.
- **AP polyline coverage** — must include every season with an AP final poll rank, not just seasons with recent data. If a season's AP rank is unknown, break the polyline there (render as two separate `<polyline>` elements) rather than interpolating.
- **Quality polyline segment breaks** — already working post-sprint-3 (confirmed on Alabama render: two polylines flanking the 2017–2018 data gap). Keep this contract stable.

## `HistoricalSeasonDeepDive`

**Role:** A single season rendered as a "chapter" in the program's ongoing story. Used for any historical CFP-era season. Accessed by clicking a season brick.

**Structure:**
1. Archive nav (← prev season · chapter N of 13 · next season →)
2. Serif title + italic thesis (both LLM-generated per season)
3. 5-column meta strip (record · final result · AP · SP+ · era)
4. "The shape of the season" SVG — game-by-game result cards + mood trajectory curve
5. Defining moments — 3 cards (color-coded by emotional register — blue/amber/red)
6. Pull quote from the era (attributed to contemporaneous publication)
7. Legacy paragraph ("what it meant")
8. Footer nav (← prev · current position · next →)

**HTML outline:**
```html
<article class="historical-season">
  <nav class="historical-season__archive-nav">
    <span class="eyebrow">the archive · {{ year }}</span>
    <a href="{{ prev_year_url }}">← {{ prev_year }}</a>
    <a href="{{ next_year_url }}">{{ next_year }} →</a>
  </nav>

  <header class="historical-season__header">
    <h1 class="historical-season__title">{{ year }} — {{ season_title }}</h1>
    <p class="historical-season__thesis">{{ season_thesis }}</p>
  </header>

  <dl class="historical-season__meta">
    <!-- 5 dt/dd pairs -->
  </dl>

  <section class="historical-season__shape">
    <span class="eyebrow">the shape — week-by-week, with what the fanbase felt</span>
    <svg viewBox="0 0 620 150">
      <!-- game result cards (12-13 across) -->
      <!-- mood curve below game row -->
      <!-- crash if post-game result was loss (red line segment) -->
      <!-- key annotations for defining moments -->
    </svg>
  </section>

  <section class="historical-season__moments">
    <span class="eyebrow">defining moments</span>
    <div class="historical-season__moments-grid">
      {% for moment in defining_moments %}
        <article class="moment-card moment-card--{{ moment.register }}">
          <span class="eyebrow">the {{ moment.type }}</span>
          <p class="moment-card__body">{{ moment.body }}</p>
        </article>
      {% endfor %}
    </div>
  </section>

  <figure class="historical-season__pull-quote">
    <blockquote class="pull-quote__text">"{{ pull_quote.text }}"</blockquote>
    <figcaption class="pull-quote__attribution">— {{ pull_quote.source }}, {{ pull_quote.date }}</figcaption>
  </figure>

  <section class="historical-season__legacy">
    <span class="eyebrow">what it meant</span>
    <p class="historical-season__legacy-text">{{ legacy_paragraph }}</p>
  </section>

  <footer class="historical-season__footer-nav">
    <!-- previous / chapter-position / next -->
  </footer>
</article>
```

**Generation contracts (per season):**
- `season_title` — LLM-generated; evocative editorial phrase ("The Proof", "The Miracle Run", "The Bottom"). One-time generation per season.
- `season_thesis` — LLM-generated; 1-2 sentences that frame what this season was. Updates if season is re-opened from current to historical.
- `defining_moments` — 3 cards with type (switch/announcement/gap) and register (blue for turning points, amber for triumphs, red for crashes).
- `pull_quote` — Actual contemporaneous quote (preferred) or LLM-generated quote in the voice of a contemporaneous writer. Attributed with year + publication.
- `legacy_paragraph` — LLM-generated; connects forward and backward to other seasons in the program's arc.

**Defining moment cards — color by register:**
- `moment-card--turning-point` — navy-400 left-border
- `moment-card--triumph` — amber-200 left-border
- `moment-card--crash` — red-600 left-border

**CSS:**
```css
.historical-season__title {
  font-family: var(--font-serif);
  font-size: var(--fs-display);
  line-height: var(--lh-display);
  letter-spacing: var(--tracking-display);
  font-weight: 400;
}
.historical-season__thesis {
  font-family: var(--font-serif);
  font-size: var(--fs-h2);
  line-height: var(--lh-h2);
  color: var(--color-text-muted);
  font-style: italic;
  margin-top: 10px;
}
.historical-season__moments-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 768px) {
  .historical-season__moments-grid { grid-template-columns: 1fr; }
}

.moment-card {
  padding: 11px 14px;
  background: var(--color-surface-card);
  border: var(--stroke-hair) solid var(--color-line);
  border-radius: var(--radius-md);
  border-left-width: 2px;
}
.moment-card--turning-point { border-left-color: var(--color-navy-400); }
.moment-card--triumph       { border-left-color: var(--color-amber-200); }
.moment-card--crash         { border-left-color: var(--color-red-600); }
.moment-card__body {
  font-family: var(--font-serif);
  font-size: 14px;
  line-height: var(--lh-body);
  margin: 4px 0 0;
}
```
