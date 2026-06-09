# Design Tokens

All tokens defined as CSS custom properties in `src/cfb_rankings/team_pages/styles/tokens.css`. Every module reads from these variables. Never hardcode color, size, or spacing values in module stylesheets.

## Colors — six ramps, seven stops each

```css
:root {
  /* Navy — analytical, tactical, trust */
  --color-navy-50:  #E6F1FB;
  --color-navy-100: #B5D4F4;
  --color-navy-200: #85B7EB;
  --color-navy-400: #378ADD;
  --color-navy-600: #185FA5;
  --color-navy-800: #0C447C;
  --color-navy-900: #042C53;

  /* Coral — emotional, reactive, warning */
  --color-coral-50:  #FAECE7;
  --color-coral-100: #F5C4B3;
  --color-coral-200: #F0997B;
  --color-coral-400: #D85A30;
  --color-coral-600: #993C1D;
  --color-coral-800: #712B13;
  --color-coral-900: #4A1B0C;

  /* Amber — heritage, peaks, celebration */
  --color-amber-50:  #FAEEDA;
  --color-amber-100: #FAC775;
  --color-amber-200: #EF9F27;
  --color-amber-400: #BA7517;
  --color-amber-600: #854F0B;
  --color-amber-800: #633806;
  --color-amber-900: #412402;

  /* Gray — neutral, structural */
  --color-gray-50:  #F1EFE8;
  --color-gray-100: #D3D1C7;
  --color-gray-200: #B4B2A9;
  --color-gray-400: #888780;
  --color-gray-600: #5F5E5A;
  --color-gray-800: #444441;
  --color-gray-900: #2C2C2A;

  /* Green — positive delta, live, up-trend */
  --color-green-50:  #E1F5EE;
  --color-green-100: #9FE1CB;
  --color-green-200: #5DCAA5;
  --color-green-400: #1D9E75;
  --color-green-600: #0F6E56;
  --color-green-800: #085041;
  --color-green-900: #04342C;

  /* Red — crisis, loss, alert */
  --color-red-50:  #FCEBEB;
  --color-red-100: #F7C1C1;
  --color-red-200: #F09595;
  --color-red-400: #E24B4A;
  --color-red-600: #A32D2D;
  --color-red-800: #791F1F;
  --color-red-900: #501313;
}
```

### Semantic color aliases (page-level)

```css
:root {
  --color-ink:        #141618;
  --color-text:       var(--color-ink);
  --color-text-muted: #6C6C6E;
  --color-text-subtle: #A0A0A2;
  --color-surface:    #FAFAF9;
  --color-surface-card: #FFFFFF;
  --color-line:       #E0DFDB;
  --color-line-subtle: rgba(20,22,24,0.08);
}
```

### Dark-mode variants (for iMessage-default rendering of share cards)

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-text:       #F4F2EC;
    --color-text-muted: #B4B2A9;
    --color-text-subtle: #6C6A65;
    --color-surface:    #1A1A18;
    --color-surface-card: #242220;
    --color-line:       rgba(244,242,236,0.08);
  }
}
```

## Typography — 9 sizes, 3 families (+ display + tabular numerals)

LOCKED 2026-05-16: Added `--font-display` (Bebas Neue) for hero findings + stadium-scoreboard
energy. Existing Inter + Source Serif Pro remain authoritative for UI + body. Tabular
numerals enforced site-wide on stat-class elements (see end of this section).

```css
:root {
  --font-sans:    'Inter', 'SF Pro Text', system-ui, sans-serif;
  --font-serif:   'Source Serif Pro', Georgia, 'Times New Roman', serif;
  --font-mono:    ui-monospace, 'SF Mono', Menlo, monospace;
  --font-display: 'Bebas Neue', 'Trade Gothic Bold Condensed', sans-serif;
  --font-ui:      var(--font-sans);  /* alias — used in v2-addendum sprints */
  --font-body:    var(--font-serif); /* alias — used in v2-addendum sprints */
  --font-tabular: var(--font-sans);  /* alias — use with tnum feature */

  /* Type scale */
  --fs-display:  clamp(48px, 6vw, 64px);    /* serif · hero titles */
  --fs-h1:       clamp(28px, 3.5vw, 32px);  /* serif · section titles */
  --fs-h2:       clamp(20px, 2.5vw, 22px);  /* serif italic · subhead */
  --fs-h3:       18px;                       /* sans 500 · module titles */
  --fs-body:     16px;                       /* serif · editorial body */
  --fs-body-sm:  14px;                       /* sans · UI body */
  --fs-label:    11px;                       /* sans 500 · eyebrows */
  --fs-caption:  11px;                       /* sans 400 · metadata */
  --fs-micro:    10px;                       /* sans · chart labels */

  /* Line heights */
  --lh-display: 1.1;
  --lh-h1:      1.25;
  --lh-h2:      1.45;
  --lh-body:    1.65;
  --lh-ui:      1.4;
  --lh-tight:   1.3;

  /* Tracking */
  --tracking-display: -0.03em;
  --tracking-h1:      -0.015em;
  --tracking-label:   0.11em;

  /* Weights — two only */
  --fw-regular: 400;
  --fw-medium:  500;
}

/* === LOCKED 2026-05-16: Tabular numerals enforcement === */
/* Every stat / number / data-cell uses tabular numerals so digits align in columns. */
/* Extended 2026-05-21 with attribute selectors to catch modern BEM stat classes
   (.csp__stat-value, .savant__metric-value, .signature-story__stat-value, etc.)
   per docs/research/cfb-stats-audit-2026-05-21.md P0. The BEM-suffix attribute
   selectors are intentionally broad — any class ending in __stat-value,
   __metric-value, __panel-value, __meta-value, or -delta gets tabular-nums
   without per-module enumeration. */
.stat, .number, .tabular,
td.numeric, .data-table td,
.percentile-value, .rank-value, .delta,
.hero-finding-number, .saturday-strip-score,

/* BEM-family modern stat classes — auto-covered by suffix */
[class$="__stat-value"], [class*="__stat-value "],
[class$="__metric-value"], [class*="__metric-value "],
[class$="__panel-value"], [class*="__panel-value "],
[class$="__meta-value"], [class*="__meta-value "],
[class$="__rcv-value"], [class*="__rcv-value "],
[class$="-delta"], [class*="-delta "],

/* Explicitly named gap classes from the 2026-05-21 audit */
.metric-cell, .impact-stat, .stat-card, .stat-grid {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
  font-family: var(--font-ui);
}

/* Variable-font preload tags belong in <head>:
   <link rel="preload" href="/fonts/inter-variable.woff2"
         as="font" type="font/woff2" crossorigin>
   <link rel="preload" href="/fonts/source-serif-pro-variable.woff2"
         as="font" type="font/woff2" crossorigin>
*/
```

## Spacing — 4px base grid

```css
:root {
  --sp-1:  4px;
  --sp-2:  8px;
  --sp-3:  12px;
  --sp-4:  16px;
  --sp-6:  24px;
  --sp-8:  32px;
  --sp-12: 48px;
  --sp-16: 64px;
  --sp-24: 96px;
}
```

## Radii — five tokens

```css
:root {
  --radius-sm:   3px;   /* inputs, small chips */
  --radius-md:   6px;   /* cards, buttons, badges */
  --radius-lg:   12px;  /* modules, containers */
  --radius-xl:   20px;  /* pages, modals */
  --radius-full: 9999px; /* pills, avatars */
}
```

## Stroke weights — three tokens

```css
:root {
  --stroke-hair:  0.5px;  /* dividers, tile borders */
  --stroke-std:   1px;    /* hover, focus, emphasis */
  --stroke-heavy: 2px;    /* accent top-borders, current-state */
}
```

## Program-variable tokens (set via runtime data attr)

```css
/* Applied at the page root via data-program or inline style */
[data-program] {
  --color-accent-primary:   /* from profile */;
  --color-accent-secondary: /* from profile */;
  --color-accent-gradient:  /* from profile */;
}

/* Examples */
[data-program="notre-dame"] {
  --color-accent-primary:   #0C2340; /* navy */
  --color-accent-secondary: #C99700; /* gold */
}
[data-program="alabama"] {
  --color-accent-primary:   #9E1B32; /* crimson */
  --color-accent-secondary: #FFFFFF;
}
```

## Breakpoints

```css
:root {
  --bp-mobile:  390px;  /* iPhone 15 Pro width */
  --bp-tablet:  768px;
  --bp-desktop: 1024px;
  --bp-wide:    1280px;
}
```

## Usage rules (for implementation)

1. All module CSS pulls from these variables. A module stylesheet should have very few literal color/size values.
2. Color use encodes meaning: navy for analytical, coral for emotional, amber for heritage/peaks, green for positive delta, red for crisis, gray for structural. Use 2-3 ramps max per page.
3. 400-stop is default accent weight. 600-stop for bold text on light. 800/900 for text on 50-stop surfaces.
4. Typography: serif for editorial (titles, prose, pull quotes). Sans for data and UI (metrics, labels, timestamps). Never mix mid-paragraph.
5. Spacing: stick to the 8 tokens. Never use 5px, 7px, 13px, etc.
6. Radii: sm for inputs, md for cards/badges, lg for modules, xl for pages, full for pills.
7. Strokes: hair is the default; std for hover; heavy only for the one element meant to lead the eye.

## Dark mode handling

- All module styles written with `:root` variables that auto-flip via `@media (prefers-color-scheme: dark)`.
- No hardcoded colors outside of `tokens.css`.
- Share-card renderer (Pillow) uses dark-mode tokens by default since iMessage is dark by default.
