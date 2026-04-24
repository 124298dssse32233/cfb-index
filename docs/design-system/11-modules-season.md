# Season Modules

The current-season theater view: schedule strip, mood sparkline, this-week callout, aspiration ladder. These are the "following the season right now" modules.

## `ScheduleStrip`

**Role:** Horizontal strip showing the current season's schedule. Each game is a card. Past games rendered with results; current week highlighted; future games rendered muted. On mobile, becomes a horizontal-scroll with current week centered on load.

**HTML:**
```html
<section class="schedule-strip">
  <div class="schedule-strip__header">
    <span class="eyebrow">the schedule</span>
    <span class="schedule-strip__hint">swipe · W{{ current_week }} centered</span>
  </div>
  <div class="schedule-strip__track">
    {% for game in games %}
      <article class="schedule-card schedule-card--{{ game.state }}">
        <time class="schedule-card__week">W{{ game.week }} · {{ game.date_short }}</time>
        <span class="schedule-card__opponent">{{ game.location_prefix }} {{ game.opponent_short }}</span>
        <strong class="schedule-card__result">{{ game.result_or_spread }}</strong>
        {% if game.chip %}
          <span class="badge-chip badge-chip--{{ game.chip_type }}">{{ game.chip }}</span>
        {% endif %}
      </article>
    {% endfor %}
  </div>
</section>
```

**Game states:**
- `schedule-card--won-marquee` — win vs. ranked opponent; amber fill
- `schedule-card--won-expected` — win vs. unranked; navy fill
- `schedule-card--lost-close` — close loss; gray fill
- `schedule-card--lost-blowout` — blowout loss; coral fill
- `schedule-card--current` — this week; bold outline, lightest fill
- `schedule-card--upcoming` — future game; transparent, hair border
- `schedule-card--upcoming-big` — future marquee game; amber outline + amber chip

**CSS:**
```css
.schedule-strip__header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.schedule-strip__track {
  display: flex;
  gap: 3px;
}
@media (max-width: 768px) {
  .schedule-strip__track {
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
  }
  .schedule-card {
    flex: 0 0 56px;
    scroll-snap-align: center;
  }
}

.schedule-card {
  flex: 1;
  min-width: 0;
  padding: 8px 4px;
  border: var(--stroke-hair) solid var(--color-line);
  border-radius: var(--radius-md);
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.schedule-card__week {
  font-size: 9px;
  color: var(--color-text-subtle);
  display: block;
}
.schedule-card__opponent {
  font-size: 11px;
  color: var(--color-text);
}
.schedule-card__result {
  font-size: 12px;
  font-weight: var(--fw-medium);
  font-variant-numeric: tabular-nums;
  margin-top: 3px;
}

.schedule-card--won-marquee {
  background: rgba(239, 159, 39, 0.14);
  border-color: var(--color-amber-200);
}
.schedule-card--won-marquee .schedule-card__result { color: var(--color-amber-600); }

.schedule-card--won-expected {
  background: rgba(55, 138, 221, 0.12);
  border-color: var(--color-navy-400);
}
.schedule-card--won-expected .schedule-card__result { color: var(--color-navy-800); }

.schedule-card--current {
  background: var(--color-surface);
  border: var(--stroke-heavy) solid var(--color-text);
  flex: 1.1;
}
.schedule-card--upcoming-big {
  background: rgba(239, 159, 39, 0.08);
  border: var(--stroke-std) solid var(--color-amber-200);
  flex: 1.15;
}
.schedule-card--upcoming-big .schedule-card__result { color: var(--color-text); }
```

## `MoodSparkline`

**Role:** Fan mood trajectory from preseason through current week, with projection forward. Sits below the schedule strip.

**HTML (SVG):**
```html
<section class="mood-sparkline">
  <div class="mood-sparkline__header">
    <span class="eyebrow">fanbase mood</span>
    <span class="mood-sparkline__range">preseason → now → projected</span>
  </div>
  <svg viewBox="0 0 600 42" class="mood-sparkline__svg" role="img" aria-label="Fan mood trajectory">
    <title>Mood from preseason to projected</title>
    <line x1="0" y1="24" x2="600" y2="24" stroke="var(--color-line-subtle)" stroke-width="0.5" stroke-dasharray="2,3"/>
    <!-- solid line: determinate (preseason through now) -->
    <path d="{{ solid_path_d }}" stroke="var(--color-navy-400)" stroke-width="1.8" fill="none"/>
    <!-- dashed line: projected forward -->
    <path d="{{ dashed_path_d }}" stroke="var(--color-navy-400)" stroke-width="1" fill="none" stroke-dasharray="3,2" opacity="0.55"/>
    <!-- points for each determinate week -->
    {% for point in solid_points %}
      <circle cx="{{ point.x }}" cy="{{ point.y }}" r="2.5" fill="var(--color-navy-400)"/>
    {% endfor %}
    <circle cx="{{ now_x }}" cy="{{ now_y }}" r="3.5" fill="var(--color-amber-200)"/>
  </svg>
</section>
```

**Generation:**
- Path coordinates computed at build time from weekly mood scores in `team_chronicle_observations` or a `team_mood_weekly` table.
- Solid path: preseason to current week.
- Dashed path: projected forward based on current trajectory + opponent difficulty.

## `ThisWeekCallout`

**Role:** A single-sentence callout about the upcoming game. Sits below mood sparkline. The loudest thing on the page on Thursday-Friday; muted on Monday-Tuesday.

**HTML:**
```html
<section class="this-week">
  <div class="this-week__eyebrow">
    <span class="eyebrow">this week · {{ game.location_prefix }} {{ game.opponent }} · {{ game.date_time }}</span>
  </div>
  <p class="this-week__text">{{ this_week_paragraph }}</p>
</section>
```

**Generation:** LLM-generated weekly. Uses profile's voice register + next-opponent's profile (for rival characterization) + spread + betting chips. Length 1-2 sentences.

Examples:
- ND (Purdue week): *"Freeman is 6–0 against non-Power opponents in his tenure. The margin is what tells us which version of the offense travels — the October version of 2024 or the November version. Hommel questionable (shoulder)."*
- UMass (Missouri week): *"At Missouri, Saturday noon. Kickoff is the first competitive football a program-crisis year has played. SP+ says 21-point spread; the fanbase says 'let's see what we've got.'"*

**CSS:**
```css
.this-week {
  padding: 10px 14px;
  background: var(--color-surface);
  border-left: var(--stroke-heavy) solid var(--color-text);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  margin: var(--sp-4) 0;
}
.this-week__eyebrow { margin-bottom: 4px; }
.this-week__text {
  font-size: var(--fs-body-sm);
  line-height: var(--lh-body);
  color: var(--color-text);
  margin: 0;
}
```

## `AspirationLadder`

**Role:** Program-specific aspiration rungs. Every program has 3-5 rungs from "achievable" to "dream." Dimmed rungs indicate "locked" states the program hasn't earned yet this season. Dynamically unlocks based on current performance.

**HTML:**
```html
<section class="aspiration-ladder">
  <div class="aspiration-ladder__header">
    <span class="eyebrow">what would make this season · the aspiration ladder</span>
  </div>
  <div class="aspiration-ladder__rungs">
    {% for rung in rungs %}
      {% include "_atoms/aspiration_rung.html" %}
    {% endfor %}
  </div>
  {% if ladder_footnote %}
    <p class="aspiration-ladder__footnote">{{ ladder_footnote }}</p>
  {% endif %}
</section>
```

**Source:** Pulls from profile's `aspiration_ladder` array. Each rung has `name`, `context`, and dynamic `odds` (computed from SP+ + schedule remaining + CFP probability model).

**Lock logic:**
- Rung is `unlocked` if odds ≥ 10% OR achievable given remaining schedule.
- Rung is `stretch` if odds 3-10%.
- Rung is `dream` if odds 1-3%.
- Rung is `locked` if odds < 1% AND program-tier baseline doesn't include this rung AND no current-season unlock conditions met.

**Dynamic unlocking example:**
- UMass baseline: "9+ wins" rung locked.
- UMass at 7-0 midseason: "9+ wins" unlocks (now 12% odds); copy shifts to "dream within reach."

**CSS:**
```css
.aspiration-ladder__rungs {
  display: grid;
  grid-template-columns: 1fr;
  gap: 4px;
  margin-top: 8px;
}
.aspiration-ladder__footnote {
  font-size: var(--fs-caption);
  color: var(--color-text-muted);
  line-height: 1.5;
  margin-top: 10px;
  font-style: italic;
}
```

## Ordering within current-season section

Desktop (and mobile):
1. ScheduleStrip
2. MoodSparkline
3. ThisWeekCallout
4. AspirationLadder (below the fold on mobile; above on desktop if hero-promoted)

Seasonal sentience can reorder these: rivalry-week-Friday promotes `ThisWeekCallout` to the top; mid-June promotes `AspirationLadder` down and hides ScheduleStrip (no current schedule).
