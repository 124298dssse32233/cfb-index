# Game Recap Mode

The highest-stakes surface on the product. Active from ~2 hours post-final through Sunday afternoon. Post-loss variant is the design-critical case; post-win is a variant.

**Activation:** state-resolver detects game within last ~24 hours; swaps module priorities; updates copy register to post-win or post-loss voice templates.

## `GameRecapHero`

**Role:** The top-of-page module post-game. Replaces the standard season theater until ~24 hours after final.

**Structure:**
1. Team identity row with recap chrome (live red dot, rank-drop visible, "final Xh Ym ago")
2. Large final score display (ND 17 · USC 28)
3. State-of-team paragraph in post-loss (or post-win) voice
4. Game-shape WP chart (SVG) with 3 annotated inflection points
5. 4-stat diagnosis row — stats chosen by LLM from ~30 candidates by divergence-from-season-baseline

**HTML outline:**
```html
<article class="game-recap-hero" data-mode="{{ result_type }}">
  <header class="game-recap-hero__header">
    <div class="game-recap-hero__team">
      <h1>{{ team.display_name }}</h1>
      <p class="game-recap-hero__meta">
        {{ season.record }} · #{{ ap_rank }} AP
        {% if ap_rank_prev %}<span class="team-identity__rank-drop">(was #{{ ap_rank_prev }})</span>{% endif %}
        · {{ game_summary_fragment }}
      </p>
    </div>
    <div class="game-recap-hero__final">
      <p class="game-recap-hero__score">
        <span class="{{ team_side_class }}">{{ team.short }} {{ team_score }}</span>
        <span class="game-recap-hero__score-separator">·</span>
        <span class="{{ opponent_side_class }}">{{ opponent.short }} {{ opponent_score }}</span>
      </p>
      <p class="game-recap-hero__freshness">
        <span class="live-dot game-recap-hero__dot--{{ result_type }}"></span>
        <span class="eyebrow">final · {{ freshness_relative }} ago</span>
      </p>
    </div>
  </header>

  <section class="game-recap-hero__state">
    <span class="eyebrow game-recap-hero__state-eyebrow">after</span>
    <p class="game-recap-hero__paragraph">{{ state_of_team_post_game }}</p>
  </section>

  <section class="game-recap-hero__wp-chart">
    <header class="game-recap-hero__chart-header">
      <span class="eyebrow">the shape of the game · win probability</span>
      <span class="game-recap-hero__chart-note">peak: {{ wp_peak_pct }}% at {{ wp_peak_time }}</span>
    </header>
    <svg viewBox="0 0 600 148">
      <!-- gridlines, quarter dividers -->
      <!-- WP line (coral if loss, navy if win) -->
      <!-- 3 annotation dots with text (peak / pivot / sealed) -->
    </svg>
    <div class="game-recap-hero__diagnosis">
      {% for stat in diagnosis_stats %}
        <div class="diagnosis-stat">
          <span class="eyebrow">{{ stat.label }}</span>
          <span class="diagnosis-stat__value diagnosis-stat__value--{{ stat.band }}">{{ stat.value }}</span>
        </div>
      {% endfor %}
    </div>
  </section>
</article>
```

**Variants:**
- `data-mode="win-clear"` — navy dot, blue accents
- `data-mode="win-upset"` — amber accents (Chronicle-dominant page)
- `data-mode="loss-close"` — coral dot, measured register
- `data-mode="loss-blowout"` — red dot, rebuilding-register
- `data-mode="loss-upset"` — red dot, crisis register

## LLM generation pipeline

Triggered on final-score ingest (T+5 min).

**T+15:** `state_of_team_post_game` paragraph. Prompt uses:
- Profile voice_register (determines tone)
- Game facts (final score, game location, margin category)
- Post-result template (wound / basking / reckoning / euphoric)
- Length: 2-4 sentences

**T+20:** `diagnosis_stats` selection. Python ranks ~30 candidate stats by divergence from team's season-to-date baseline. Sonnet picks top 4 with short 1-3-word labels + writes a 1-line caption each.

Examples:
- *"Rush yds allowed: 223 · worst in Freeman era"*
- *"3rd down conv: 4/14"*
- *"TO margin: −2"*
- *"2nd half pts: 0"*

**T+25-30:** `chronicle_cards_post_game` (3 cards):
- Anomaly: stat outlier vs. historical distribution
- Echo: pattern detection across seasons (e.g., "7th straight road loss where ND led at halftime")
- Retroactive: recontextualization linking back to earlier-season note (e.g., "Miami run-defense concerns we wrote off in September returned today")

**T+35:** `cfp_math_revised` paragraph. Forecast model computes pre-game vs. post-game CFP odds + "if win out" scenario. Sonnet writes calibrated 1-2 sentences: not catastrophizing, not Pollyanna. "Not closed. Not open either."

**T+40:** `events_72h` summary. Aggregates FI pipeline events during and after the game into a chronological log.

**T+45:** Page republishes.

All runs via Claude Code headless on Kevin's Max subscription.

## Additional recap mode modules

Below the `GameRecapHero`, the page stacks:

### `PulseLiveLossMode`

Full Pulse module styled with recap-specific variant: red top-border, mood number in red, "what moved it" shows in-game events with signed deltas. See §12 for Pulse module structure.

### `ChronicleGameEdition`

3 Chronicle cards generated in the post-game pipeline. Same HTML as standard Chronicle cards; content and accents match result register.

### `CFPMathRevisedPanel`

Small panel:
```html
<section class="cfp-math-revised">
  <span class="eyebrow">cfp math · revised</span>
  <dl class="cfp-math-revised__grid">
    <div><dt>pre-game</dt><dd>{{ pre_pct }}%</dd></div>
    <div><dt>now</dt><dd class="cfp-math-revised__now">{{ post_pct }}% <small>{{ delta }}</small></dd></div>
    <div><dt>if win out</dt><dd>{{ scenario_pct }}%</dd></div>
  </dl>
  <p class="cfp-math-revised__paragraph">{{ cfp_math_paragraph }}</p>
</section>
```

### `NextGameFooter`

Reduced to single line under the recap:
```html
<footer class="next-game-footer">
  <span class="eyebrow">next: {{ next_game.opponent_short }} · {{ next_game.location }} · {{ next_game.date_time }}</span>
  <span class="eyebrow next-game-footer__update">next update: {{ next_update_label }}</span>
</footer>
```

## State-resolver logic (recap mode activation)

```python
def resolve_page_state(team, now):
    last_game = team.latest_completed_game()
    hours_since_final = (now - last_game.final_at).total_seconds() / 3600

    if hours_since_final < 24:
        return f"game-recap-{last_game.outcome_type}"

    if hours_since_final < 48 and now.weekday() == 0:  # Monday
        return f"post-{last_game.outcome_type}-monday"

    # ... other state resolutions ...
```

Post-recap-mode (24h+), page reverts to standard season theater view but retains the `state_of_team` paragraph written at T+15. That paragraph persists in `team_season_narratives` table keyed by `(team_id, week_number)` for the rest of the week.

## CSS (partial)

```css
.game-recap-hero {
  background: var(--color-surface-card);
  border: var(--stroke-hair) solid var(--color-line);
  border-radius: var(--radius-lg);
  padding: 24px 28px;
}
.game-recap-hero__dot--loss-close,
.game-recap-hero__dot--loss-blowout,
.game-recap-hero__dot--loss-upset {
  background: var(--color-red-600);
}
.game-recap-hero__dot--win-clear,
.game-recap-hero__dot--win-upset {
  background: var(--color-green-400);
}
.game-recap-hero__paragraph {
  font-family: var(--font-serif);
  font-size: 19px;
  line-height: var(--lh-body);
  color: var(--color-text);
}
.diagnosis-stat__value--concern   { color: var(--color-red-600); }
.diagnosis-stat__value--strength  { color: var(--color-green-600); }
```
