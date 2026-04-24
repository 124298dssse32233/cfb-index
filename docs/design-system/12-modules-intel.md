# Intelligence Modules

The proprietary-data modules that are CFB Index's editorial moat: Pulse (live fan sentiment), Chronicle (LLM-gleaned observations), Rivalry Card (dueling fanbase analytics), Savant Card (stat density).

## `PulseModule`

**Role:** Bloomberg-terminal aesthetic surfacing the live fan-intelligence signal. Updates daily.

**Structure:**
1. Header row — live dot + title + freshness timestamp + velocity-vs-baseline
2. Primary row (3 cols) — mood number + 72-hour trajectory SVG + conversation velocity
3. "What moved it" event log — timestamped deltas
4. Topics row — top 3-4 weekly conversation topics with sentiment bars
5. Gap cards — reality gap + respect gap + cohort divergence (3 compact cards)
6. Takes — 3 representative quotes with source attribution
7. Footer — conversation-venue links (subreddit, hashtag, board)

**HTML (outline):**
```html
<section class="pulse">
  <header class="pulse__header">
    <div class="pulse__title">
      <span class="live-dot"></span>
      <span class="pulse__title-text">The Pulse · live</span>
      <span class="eyebrow">updated {{ freshness_relative }}</span>
    </div>
    <span class="pulse__stats">{{ signal_count }} signals / 7 days · {{ velocity_multiple }}x baseline</span>
  </header>

  <div class="pulse__primary">
    <!-- mood summary -->
    <!-- trajectory svg -->
    <!-- velocity block -->
  </div>

  <section class="pulse__what-moved-it">
    <span class="eyebrow">what moved it · last 72 hrs</span>
    {% for event in events_72h %}
      {% include "_atoms/event_log_item.html" %}
    {% endfor %}
  </section>

  <div class="pulse__mid-grid">
    <section class="pulse__topics"> ... </section>
    <section class="pulse__gaps"> ... </section>
  </div>

  <section class="pulse__takes">
    <span class="eyebrow">the takes · curated from {{ signal_count }} signals</span>
    <div class="pulse__takes-grid">
      {% for take in takes %}
        <article class="pulse-take pulse-take--{{ take.sentiment }}">
          <blockquote class="pulse-take__quote">"{{ take.text }}"</blockquote>
          <cite class="pulse-take__source">{{ take.source }}</cite>
        </article>
      {% endfor %}
    </div>
  </section>

  <footer class="pulse__footer">
    <span class="eyebrow">live in the conversation</span>
    <ul class="pulse__venues">
      {% for venue in venues %}
        <li><a href="{{ venue.url }}">{{ venue.name }}</a> · <span>{{ venue.activity }}</span></li>
      {% endfor %}
    </ul>
  </footer>
</section>
```

**Data contracts:**
- `mood_current` (0-100)
- `mood_delta_7d` (signed)
- `mood_baseline_label` (e.g., "highest Freeman-era")
- `velocity_multiple` (current posts/hr divided by 4-week baseline)
- `events_72h` — array of `{timestamp, delta, description}` objects from the FI pipeline
- `topics` — top 3-4 topics with sentiment scores and volume percentages
- `gaps` — `{reality_gap_value, respect_gap_value, divergence_score}` from fan-intel pipeline
- `takes` — 3 LLM-curated representative quotes, each with sentiment-diversity ranking
- `venues` — conversation venues with activity metric per venue

**Generation pattern:**
- Python query builds the raw signals from fan-intel tables.
- Claude Code headless generates: event descriptions (plain English from FI signal log), take selection + writing (from top-K Reddit/board posts), topic labels (clusters from weekly content).
- Cached to `team_chronicle_observations` table keyed by `(team_id, week_start_date)`.
- Rebuilds nightly.

**CSS (partial):**
```css
.pulse {
  background: var(--color-surface-card);
  border: var(--stroke-hair) solid var(--color-line);
  border-top: var(--stroke-heavy) solid var(--color-red-600);
  border-radius: var(--radius-md);
  padding: 18px 22px;
}
.pulse__primary {
  display: grid;
  grid-template-columns: 0.9fr 1.4fr 1fr;
  gap: 18px;
  padding: 12px 0;
  border-top: var(--stroke-hair) solid var(--color-line);
  border-bottom: var(--stroke-hair) solid var(--color-line);
}
@media (max-width: 768px) {
  .pulse__primary {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}
```

## `ChronicleCard`

**Role:** Individual LLM-gleaned editorial observation card. Each card is one of 6 types with a distinct visual accent. Lives inside a `ChronicleModule` that contains 4-6 cards per week.

**Card types:**

| Type | Accent | What it surfaces |
|---|---|---|
| `anomaly` | amber top-border | statistical outlier vs. historical distribution |
| `moment` | coral top-border | cultural/social velocity signal |
| `flashpoint` | navy top-border | next-opponent matchup intelligence |
| `echo` | gray top-border | cross-era similarity or parallel |
| `retroactive` | purple (use navy-800) top-border | recontextualization of earlier season moment |
| `player_arc` | teal (use green-200) top-border | individual trajectory within cohort |

**HTML:**
```html
<article class="chronicle-card chronicle-card--{{ card.type }}">
  <span class="eyebrow chronicle-card__type">the {{ card.type_label }}</span>
  <h3 class="chronicle-card__headline">{{ card.headline }}</h3>
  {% if card.data_visualization %}
    <div class="chronicle-card__viz">{{ card.data_visualization | safe }}</div>
  {% endif %}
  {% if card.body %}
    <p class="chronicle-card__body">{{ card.body }}</p>
  {% endif %}
  <footer class="chronicle-card__source">
    <span class="eyebrow">source: {{ card.source }}</span>
  </footer>
</article>
```

**Generation — see `docs/CHRONICLE_EDITORIAL_BRIEF.md` for full voice contract.**

The Chronicle pipeline has four stages and reads from six proprietary data streams. Cards that pass validation must (a) name a specific person/date/play beyond the program name, (b) not contain any banned self-referential scaffolding phrase, (c) make a comparison or connection (not just a restatement), and (d) cite a real source in a fan-readable attribution format.

### Stage 1 — Multi-stream candidate scan (Haiku, parallel)

| Stream | Signal | Produces card type |
|---|---|---|
| Savant / gamelog | Percentile outliers (≥95th or ≤5th), streaks, situational splits | anomaly |
| Fan-intel pipeline | Cohort conversation velocity ≥ 2× baseline, top Bluesky posts, board threads, beat-writer headlines | moment |
| Archive (2014–now) | Cosine similarity on season-shape features vs. current season | echo |
| Rivalry archive | Upcoming game vs. profiled rival, last-meeting detail, both sides' trajectories | flashpoint |
| Past Chronicle cards | Framings from earlier weeks now overturned by later events | retroactive |
| Player trajectories + fan-intel | Player-level stat trends + name-velocity spikes | player-arc |

Each candidate emits `(evidence, source_citation, suggested_card_type, oddity_score, date_window)`.

### Stage 2 — Ranking (Sonnet)

Rank ~30 candidates to top 4–6 by: surprise score, voice-fit, evidence strength, recency × durability, diversity (max 2 of any one card type per week).

### Stage 3 — Writing (Sonnet; Opus for top-3 blue-blood cards weekly)

Prompt must include verbatim from `profiles/<slug>.md`: `voice_register`, `identity_phrase`, `mantra`, `stock_phrases`, `mascot_voice`, `era_name_overrides`. Must include the full anti-scaffolding banned-phrase list as negative prompt. Body 2–3 sentences max. Headline must contain a specific noun beyond program name.

### Stage 4 — Validation (Haiku)

Gate every generated card against four checks (proper noun, no banned phrases, comparative structure, acceptable attribution format). One retry on failure. Second failure: drop the card. Log dropout rate per program per week as voice-quality telemetry.

### Source attribution formats (mandatory — see brief Rule 7)

Never "CFB Index game-log stat engine." Acceptable formats:
- `OneFootDown · Mon` (real source + relative date)
- `from the Kelly-era archive` (archive citation with era name)
- `from 14 beat-writer pieces this week` (cluster citation)
- `gamelog · 2014–now` (historical pattern — acceptable for anomaly type only)
- `conversation velocity · Bluesky firehose` (fan-intel citation)
- `from the 2022 season archive · Freeman-era year one` (archive + era)

If no real source can be cited, the card does not ship.

### Banned phrases (drop on detection)

`sample`, `stat engine`, `pipeline`, `tier 1/2` (as taxonomy), `pattern is` (as subject), `summary stat`, `compression of outcome`, `flattening of`, `Every season produces`, `this table`, `this card`, `methodology`, `the engine`, `our algorithm`.

**Wrapper — `ChronicleModule`:**
```html
<section class="chronicle">
  <header class="chronicle__header">
    <span class="eyebrow">the chronicle · this week</span>
    <span class="chronicle__stats">{{ card_count }} observations curated from {{ candidate_count }} candidates</span>
  </header>
  <div class="chronicle__hero-card">
    <!-- the week's top observation, full-width with viz -->
  </div>
  <div class="chronicle__grid">
    <!-- 3 smaller cards in a 3-column grid (desktop) / 1-column (mobile) -->
  </div>
  <div class="chronicle__full-width">
    <!-- one more full-width card (echo or retroactive) -->
  </div>
</section>
```

**CSS:**
```css
.chronicle-card {
  background: var(--color-surface-card);
  border: var(--stroke-hair) solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 14px 18px;
}
.chronicle-card--anomaly    { border-top: var(--stroke-heavy) solid var(--color-amber-200); }
.chronicle-card--moment     { border-top: var(--stroke-heavy) solid var(--color-coral-400); }
.chronicle-card--flashpoint { border-top: var(--stroke-heavy) solid var(--color-navy-400); }
.chronicle-card--echo       { border-top: var(--stroke-heavy) solid var(--color-gray-400); }
.chronicle-card--retroactive{ border-top: var(--stroke-heavy) solid var(--color-navy-800); }
.chronicle-card--player-arc { border-top: var(--stroke-heavy) solid var(--color-green-200); }

.chronicle-card__headline {
  font-family: var(--font-serif);
  font-size: var(--fs-h2);
  line-height: var(--lh-h1);
  letter-spacing: var(--tracking-h1);
  font-weight: 400;
  margin: 4px 0 0;
  color: var(--color-text);
}
.chronicle-card__body {
  font-family: var(--font-serif);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--color-text);
  margin: 12px 0 0;
}
.chronicle-card__source {
  margin-top: 12px;
}

.chronicle__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin: 12px 0;
}
@media (max-width: 768px) {
  .chronicle__grid { grid-template-columns: 1fr; }
}
```

## `RivalryCard`

**Role:** Rivalry module surfacing meta + dual fanbase heat + recent meetings + this-year stakes. Shown for each Tier-1 rivalry; Tier-2 rivalries get an abbreviated version.

**Structure:**
1. Mythic centered header (serif proper noun + "[Program] × [Opponent] · N meetings since YYYY")
2. 4-column meta strip (all-time record · streak · trophy · countdown)
3. Dual-trajectory heat chart showing both fanbases' rivalry-heat over 4 weeks to kickoff
4. Two posture-labeled fanbase panels side-by-side (heat number + posture tag + representative quote + source)
5. Editorial last-ten meetings list (year · score · home/away · one-line commentary)
6. "This year's stakes" footer (date/venue/time · line · dual-perspective needs-copy)

**HTML (outline):** ~100 lines; see `TEAM_PAGE_ITERATION_LOG.md` item 5 (Rivalry Card prototype) for visual reference.

**Trajectory chart:** two lines on one SVG (ND solid navy, opponent solid coral), both building from left (4 weeks out) to kickoff (right); solid portion is determined, dashed portion is projected. Gap annotated with "+15" or similar on the chart.

**Posture panels:** each program's current rivalry-heat score + 2-word "posture" tag from profile (e.g., "dismissive · confident" for ND, "anxious · bargaining" for USC) + one LLM-curated representative quote + source attribution.

**Meetings list:** last 10 historical meetings with scores. Each meeting has a 1-sentence editorial note generated by LLM (one-time per historical game) with year-context + memorable detail.

**Stakes footer:** for each side, one-sentence "what winning/losing means for them" — CFP path impact, coach hot-seat implications, rivalry streak implications.

## `SavantCard`

**Role:** 13-metric percentile card for the deep-dive data audience. Peer-set toggle (FBS / P4 / conference / all-time program). LLM-written narrative header above the bars.

**Structure:**
1. Header — peer-set toggle chips + narrative header
2. Offense section — 6 metrics with percentile bars
3. Defense section — 5 metrics (inverted with ↓ glyph + clarifier)
4. Special-situations section — 3 metrics
5. Color-ramp legend
6. Source attribution

**HTML:**
```html
<section class="savant-card">
  <header class="savant-card__header">
    <span class="eyebrow">the savant card · {{ program.display_name }} · {{ peer_set_label }}</span>
    <div class="savant-card__toggle">
      {% for peer in peer_sets %}
        <button class="toggle-chip{% if peer.selected %} toggle-chip--selected{% endif %}">{{ peer.label }}</button>
      {% endfor %}
    </div>
    <p class="savant-card__narrative">{{ narrative_header }}</p>
  </header>

  <div class="savant-card__section">
    <span class="eyebrow">offense · best → concern</span>
    {% for metric in offense_metrics %}
      {% include "_atoms/percentile_bar.html" %}
    {% endfor %}
  </div>

  <div class="savant-card__section">
    <div class="savant-card__section-header">
      <span class="eyebrow">defense</span>
      <span class="savant-card__inverted-note">all metrics inverted — higher percentile = harder to play against</span>
    </div>
    {% for metric in defense_metrics %}
      {% include "_atoms/percentile_bar.html" %}
    {% endfor %}
    {% if echo_similarity %}
      <p class="savant-card__echo">echo: {{ echo_similarity.comp_year }} · {{ echo_similarity.score }} similarity</p>
    {% endif %}
  </div>

  <div class="savant-card__section">
    <span class="eyebrow">hidden math · special situations</span>
    {% for metric in special_metrics %}
      {% include "_atoms/percentile_bar.html" %}
    {% endfor %}
  </div>

  <div class="savant-card__legend">
    <!-- color bands -->
  </div>

  <footer class="savant-card__source">
    <span class="eyebrow">sources · CFBD tier 2 · SP+ · opponent-adjusted through {{ as_of_date }}</span>
  </footer>
</section>
```

**Data contracts:**
- `metrics` — array of `{label, percentile, band, inverted}` objects
- `narrative_header` — LLM-generated sentence summarizing the percentiles (elite strengths + concerns + crux)
- `echo_similarity` — cross-era cosine similarity (from Chronicle echo computation)
- `peer_sets` — list of available peer comparisons

**Narrative header generation prompt (abbreviated):**
> Given these 13 percentile bars, write one sentence that tells the fan what the card is saying. Name the top 1-2 strengths, the top 1 concern, and the crux of where this team lives. 40-50 words. No hedging.

**Example outputs:**
- *"Elite in run defense prevention. Strength in red zone on both sides. Mixed on offensive explosiveness. Concern at third-down conversion — the line between 'good team' and 'title team' lives here."*
- *"Bottom-quartile in EPA per play allowed. Above-average in turnovers forced. The offense is running out of oxygen on long fields. Fix the run defense or the season ends at 6-6."*

**CSS:** standard module framing + percentile bars as documented in atoms spec.
