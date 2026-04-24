# Atomic Components

Small reusable components that modules compose from. Each is a single Figma variant plus CSS class. Live in `src/cfb_rankings/team_pages/templates/_atoms/` as Jinja partials.

## `Eyebrow`

Small-caps uppercase label above content blocks.

**HTML:**
```html
<span class="eyebrow">{{ text }}</span>
```

**CSS:**
```css
.eyebrow {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: var(--fw-medium);
  letter-spacing: var(--tracking-label);
  text-transform: uppercase;
  color: var(--color-text-subtle);
}
```

**Variants (via class modifiers):**
- `.eyebrow--accent` — uses `var(--color-accent-primary)` instead of subtle
- `.eyebrow--on-surface` — uses darker color for use on colored backgrounds

## `MetricTile`

A single-stat tile with optional delta chip. Used in metric rows (4-tile desktop, 2×2 mobile).

**HTML:**
```html
<div class="metric-tile">
  <span class="metric-tile__label">{{ label }}</span>
  <div class="metric-tile__value-row">
    <span class="metric-tile__value">{{ value }}</span>
    {% if delta %}
      <span class="metric-tile__delta metric-tile__delta--{{ delta_direction }}">
        {{ delta }}
      </span>
    {% endif %}
  </div>
  {% if context %}
    <span class="metric-tile__context">{{ context }}</span>
  {% endif %}
</div>
```

**CSS:**
```css
.metric-tile {
  background: var(--color-surface-card);
  border: var(--stroke-hair) solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  min-height: 48px; /* mobile touch target */
}
.metric-tile__label {
  font-size: var(--fs-label);
  letter-spacing: var(--tracking-label);
  text-transform: uppercase;
  color: var(--color-text-subtle);
}
.metric-tile__value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 2px;
}
.metric-tile__value {
  font-size: 17px;
  font-weight: var(--fw-medium);
  font-variant-numeric: tabular-nums;
}
.metric-tile__delta {
  font-size: 11px;
}
.metric-tile__delta--up    { color: var(--color-green-400); }
.metric-tile__delta--down  { color: var(--color-red-400); }
.metric-tile__delta--flat  { color: var(--color-text-muted); }
.metric-tile__context {
  font-size: 10px;
  color: var(--color-text-muted);
  margin-top: 2px;
}
```

## `BadgeChip`

Tag used on schedule cards for characterization ("the axis", "revenge", "trap", "sacred").

**HTML:**
```html
<span class="badge-chip badge-chip--{{ type }}">{{ text }}</span>
```

**Types:**
- `badge-chip--characterization` — fanbase's emotional map (amber)
- `badge-chip--revenge` — coral
- `badge-chip--trap` — gray
- `badge-chip--sacred` — gray muted
- `badge-chip--big` — amber heavy

**CSS:**
```css
.badge-chip {
  font-size: 9px;
  letter-spacing: 0.04em;
}
.badge-chip--characterization { color: var(--color-amber-800); }
.badge-chip--revenge         { color: var(--color-red-600); }
.badge-chip--trap            { color: var(--color-text-muted); }
.badge-chip--sacred          { color: var(--color-text-subtle); }
```

## `PullQuote`

Serif italic blockquote with attribution. Used in Chronicle cards, historical season deep-dives.

**HTML:**
```html
<blockquote class="pull-quote">
  <p class="pull-quote__text">{{ text }}</p>
  <cite class="pull-quote__attribution">— {{ attribution }}</cite>
</blockquote>
```

**CSS:**
```css
.pull-quote {
  margin: 0;
}
.pull-quote__text {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--color-text);
}
.pull-quote__attribution {
  font-size: var(--fs-caption);
  color: var(--color-text-subtle);
  margin-top: 8px;
  display: block;
  font-style: normal;
}
```

## `AspirationRung`

Single row within the aspiration ladder module. Left border color indicates tier.

**HTML:**
```html
<div class="aspiration-rung aspiration-rung--{{ tier }}{% if locked %} aspiration-rung--locked{% endif %}">
  <span class="aspiration-rung__name">{{ name }}</span>
  <span class="aspiration-rung__context">{{ context }}</span>
  <span class="aspiration-rung__odds">{{ odds }}</span>
</div>
```

**CSS:**
```css
.aspiration-rung {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  padding: 6px 10px;
  background: var(--color-surface-card);
  border-left: var(--stroke-heavy) solid var(--color-gray-400);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  font-size: 12px;
}
.aspiration-rung--achievable { border-left-color: var(--color-green-400); }
.aspiration-rung--stretch    { border-left-color: var(--color-amber-200); }
.aspiration-rung--dream      { border-left-color: var(--color-coral-400); }
.aspiration-rung--locked     {
  opacity: 0.6;
  border-left-color: var(--color-gray-400);
}
.aspiration-rung__name    { font-weight: var(--fw-medium); }
.aspiration-rung__context { color: var(--color-text-muted); }
.aspiration-rung__odds    { color: var(--color-text-muted); font-variant-numeric: tabular-nums; text-align: right; }
```

## `EventLogItem`

Single row within "what moved it" log. Timestamp + signed delta + description.

**HTML:**
```html
<div class="event-log-item">
  <time class="event-log-item__time">{{ timestamp }}</time>
  <span class="event-log-item__delta event-log-item__delta--{{ direction }}">{{ delta }}</span>
  <span class="event-log-item__description">{{ description }}</span>
</div>
```

**CSS:**
```css
.event-log-item {
  display: flex;
  gap: 10px;
  align-items: baseline;
  padding: 4px 0;
  font-size: 11px;
}
.event-log-item__time {
  color: var(--color-text-subtle);
  font-size: 10px;
  min-width: 72px;
  font-variant-numeric: tabular-nums;
}
.event-log-item__delta {
  min-width: 32px;
  font-variant-numeric: tabular-nums;
  font-weight: var(--fw-medium);
}
.event-log-item__delta--up   { color: var(--color-green-400); }
.event-log-item__delta--down { color: var(--color-red-400); }
.event-log-item__description { color: var(--color-text); line-height: 1.45; }
```

## `PercentileBar`

Horizontal bar showing percentile vs. peer set (used in Savant card).

**HTML:**
```html
<div class="percentile-bar">
  <span class="percentile-bar__label">{{ label }}{% if inverted %} <span class="percentile-bar__inverted">↓</span>{% endif %}</span>
  <div class="percentile-bar__track">
    <div class="percentile-bar__fill percentile-bar__fill--{{ band }}" style="width: {{ pct }}%;"></div>
  </div>
  <span class="percentile-bar__value percentile-bar__value--{{ band }}">{{ pct }}</span>
</div>
```

**Bands (by percentile):**
- 85-100: elite (navy-800)
- 65-84: strong (navy-400)
- 45-64: middle (gray-400)
- 25-44: concerning (coral-400)
- 0-24: crisis (red-600)

**CSS:**
```css
.percentile-bar {
  display: grid;
  grid-template-columns: 180px 1fr 40px;
  gap: 12px;
  align-items: center;
}
.percentile-bar__label { font-size: 11px; }
.percentile-bar__inverted { font-size: 9px; color: var(--color-text-subtle); }
.percentile-bar__track {
  height: 6px;
  background: var(--color-line-subtle);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.percentile-bar__fill--elite       { background: var(--color-navy-800); }
.percentile-bar__fill--strong      { background: var(--color-navy-400); }
.percentile-bar__fill--middle      { background: var(--color-gray-400); }
.percentile-bar__fill--concerning  { background: var(--color-coral-400); }
.percentile-bar__fill--crisis      { background: var(--color-red-600); }
.percentile-bar__value {
  font-size: 11px;
  font-weight: var(--fw-medium);
  font-variant-numeric: tabular-nums;
  text-align: right;
}
```

## `LiveDot`

Pulsing dot indicator for "live" status (Pulse module, game recap, current-week chip).

**HTML:**
```html
<span class="live-dot" aria-label="live"></span>
```

**CSS:**
```css
.live-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: var(--color-green-400);
  border-radius: var(--radius-full);
  animation: live-pulse 2s infinite;
}
@keyframes live-pulse {
  0%   { opacity: 1; transform: scale(1); }
  50%  { opacity: 0.4; transform: scale(1.4); }
  100% { opacity: 1; transform: scale(1); }
}
```

## `DividerRule`

Hairline horizontal divider.

**CSS:**
```css
.divider {
  border: 0;
  border-top: var(--stroke-hair) solid var(--color-line);
  margin: var(--sp-4) 0;
}
```
