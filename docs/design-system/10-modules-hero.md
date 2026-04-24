# Hero Modules

Modules that sit above the fold: team identity header, heritage strip, state-of-team paragraph, metric tile grid. These four form the team page's "announcement" — what a fan sees in the first 5 seconds.

## `TeamIdentityHeader`

**Role:** Program identity, current record, rank, next game. First thing on the page. Persistent context across scroll.

**HTML:**
```html
<header class="team-identity" data-program="{{ program_slug }}">
  <div class="team-identity__left">
    <h1 class="team-identity__name">{{ program.display_name }}</h1>
    <p class="team-identity__meta">
      {{ program.nickname }} · {{ conference_label }}{% if is_independent %} · est. {{ program.founded_football }}{% endif %}
    </p>
  </div>
  <div class="team-identity__right">
    <p class="team-identity__record">
      <strong>{{ season.record }}</strong>
      {% if season.ap_rank %} · #{{ season.ap_rank }} AP{% endif %}
    </p>
    <p class="team-identity__next-game">
      {% if next_game %}
        {{ next_game.location_prefix }} {{ next_game.opponent_short }} · {{ next_game.date_short }}{% if next_game.countdown %} · {{ next_game.countdown }}{% endif %}
      {% else %}
        season complete
      {% endif %}
    </p>
  </div>
</header>
```

**CSS:**
```css
.team-identity {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: var(--sp-6) 0;
  border-bottom: var(--stroke-hair) solid var(--color-line);
}
.team-identity__name {
  font-family: var(--font-sans);
  font-size: 22px;
  font-weight: var(--fw-medium);
  letter-spacing: -0.01em;
  margin: 0;
  color: var(--color-text);
}
.team-identity__meta {
  font-size: var(--fs-caption);
  color: var(--color-text-muted);
  margin: 2px 0 0;
}
.team-identity__right {
  text-align: right;
  font-size: var(--fs-caption);
}
.team-identity__record {
  font-weight: var(--fw-medium);
  color: var(--color-text);
  margin: 0;
}
.team-identity__next-game {
  color: var(--color-text-muted);
  margin: 2px 0 0;
}

@media (max-width: 768px) {
  .team-identity__name { font-size: 20px; }
}
```

**Context variants:**
- `.team-identity--post-win` — (optional) subtle green accent on the record
- `.team-identity--post-loss` — (optional) subtle red accent on the record; shows "(was #X)" after current rank
- `.team-identity--game-recap-mode` — shows pulsing red live-dot next to record if within 6 hours of a loss

## `HeritageStrip`

**Role:** Program silhouette in one sentence. Always above the fold. Preserves identity weight for blue-blood programs; for non-blue-bloods, surfaces whatever heritage they have honestly.

**HTML:**
```html
<aside class="heritage-strip">
  <span class="eyebrow">heritage</span>
  <p class="heritage-strip__text">{{ heritage_sentence }}</p>
  {% if expandable %}
    <button class="heritage-strip__expand">expand →</button>
  {% endif %}
</aside>
```

**Generation of `heritage_sentence`:** LLM builds from profile's `heritage` + `always_surface` fields. Examples:
- ND: "Since 1887 · 11 national titles · 7 Heismans · Rockne, Leahy, Parseghian, Holtz · this is the playoff era"
- UMass: "Since 1879 · 2003 FCS national champions · rejoined FBS 2012 · the flagship of New England football"
- Vanderbilt: "Since 1886 · 4 conference titles (all pre-1923) · the academic anchor of the SEC"

**CSS:**
```css
.heritage-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: var(--stroke-hair) solid var(--color-line);
}
.heritage-strip__text {
  font-size: var(--fs-caption);
  color: var(--color-text-muted);
  line-height: 1.5;
  margin: 0;
  flex: 1;
}
.heritage-strip__expand {
  font-size: 10px;
  color: var(--color-text-subtle);
  background: transparent;
  border: 0;
  cursor: pointer;
}
```

## `StateOfTeamParagraph`

**Role:** The editorial voice moment. One serif paragraph that tells the fan what kind of season/week this is. Regenerated weekly (in-season) or monthly (offseason) via `manage.py generate-narratives`.

**HTML:**
```html
<section class="state-of-team">
  <div class="state-of-team__eyebrow">
    <span class="eyebrow">the {{ season.year }} season · {{ week_or_phase }}</span>
  </div>
  <h2 class="state-of-team__headline">{{ season.thesis_headline }}</h2>
  <p class="state-of-team__body">{{ state_of_team_paragraph }}</p>
</section>
```

**Generation contract:**
- `state_of_team_paragraph` is LLM-generated per (team, week, outcome_context) tuple.
- Prompt uses profile's `identity_phrase`, `mantra`, `stock_phrases`, `never_use`, `always_surface`.
- Length: 2-4 sentences, ~40-80 words.
- Ends with program's mantra OR a sentence fragment that feels like a button.
- Voice register: from profile's `voice_register`.

**Examples (in-profile voice):**
- ND (post-win): *"Six-and-oh at the bye. LSU, Auburn still ahead. Process talk is back. The only question worth asking is about January."*
- UMass (overperforming): *"Three wins in five weeks. For this program, that's momentum. Missouri Saturday asks how real."*
- Vanderbilt (beat Alabama): *"4–1 after five, first time since 2012. Read that twice. The Tennessee game wasn't supposed to happen. Now make it feel like it should have."*

**CSS:**
```css
.state-of-team {
  padding: var(--sp-6) 0;
}
.state-of-team__eyebrow { margin-bottom: 4px; }
.state-of-team__headline {
  font-family: var(--font-serif);
  font-size: var(--fs-h2);
  line-height: var(--lh-h1);
  letter-spacing: var(--tracking-h1);
  font-weight: 400;
  color: var(--color-text);
  margin: 0 0 6px;
}
.state-of-team__body {
  font-family: var(--font-serif);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--color-text);
  margin: 0;
  max-width: 72ch;
}
```

**Context variants (drive the paragraph tone):**
- `.state-of-team--post-win` — light green accent on eyebrow
- `.state-of-team--post-loss` — muted red accent; paragraph uses reckoning voice template
- `.state-of-team--rivalry-week` — amber accent; paragraph uses coiled voice template
- `.state-of-team--offseason` — gray accent; paragraph uses patient / heritage-forward voice

## `MetricTileGrid`

**Role:** 4 stat tiles showing the current season's headline numbers. Desktop: 1×4 row. Mobile: 2×2 grid.

**Which tiles appear (program-tier dependent):**

| Tier | Tile 1 | Tile 2 | Tile 3 | Tile 4 |
|---|---|---|---|---|
| T1 (blue bloods) | AP rank | Record | SP+ | CFP odds |
| T2-3 (P4) | AP rank OR SP+ | Record | SP+ | Bowl odds or Conf rank |
| T4-5 (mid P4) | SP+ | Record | Bowl odds | Conf rank |
| T6-8 (G5) | Record | SP+ | Bowl odds | Mood |
| T9-10 (low G5) | Record | SP+ | YoY wins | Mood |

Resolver reads `profile.program_tier` and outputs the tile set.

**HTML:**
```html
<section class="metric-grid">
  {% for tile in tiles %}
    {% include "_atoms/metric_tile.html" %}
  {% endfor %}
</section>
```

**CSS:**
```css
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--sp-2);
  margin: var(--sp-4) 0;
}
@media (max-width: 768px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

## Ordering above the fold

On desktop (top → bottom):
1. TeamIdentityHeader
2. HeritageStrip
3. StateOfTeamParagraph
4. MetricTileGrid

On mobile: same order, all full-width.

State-resolver can override the heritage strip's visibility (hide on very thin-history programs where there's nothing to say).
