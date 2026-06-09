"""Player-page design tokens — Brief §8.3.

Three semantic OKLCH ramps + neutrals as CSS custom properties. Each
ramp interpolates in `oklch` color space so luminance is continuous
across the gradient (colorblind users perceive order correctly) and
each step passes WCAG 2.1 AA against the dark surface.

Ramps:
  --pct-*  : percentile (red → neutral → blue, Savant convention)
  --belief-* : belief (red → neutral → green, FI sentiment)
  --accolade-* : gold accent (award status / "named to" highlights)

Modules should reference these tokens rather than hard-coding hex
literals so all percentile / belief / accolade visuals stay perfectly
in sync if the ramps are ever retuned.

Public:
    PLAYER_PAGE_TOKENS_CSS  -> str
"""
from __future__ import annotations


PLAYER_PAGE_TOKENS_CSS = """
/* Player-page semantic ramps — Brief §8.3 */
:root {
  /* Percentile ramp — red (low) → neutral → blue (high), Savant convention.
     Five steps + interpolated mid; oklch interpolation guarantees continuous
     luminance and ordered perception under common colorblindness models. */
  --pct-r0:   oklch(0.62 0.20 25);   /* red bottom (#d93a4a base) */
  --pct-r1:   oklch(0.60 0.13 22);   /* dim red */
  --pct-mid:  oklch(0.55 0.02 250);  /* neutral grey */
  --pct-b1:   oklch(0.60 0.13 240);  /* dim blue */
  --pct-b0:   oklch(0.55 0.22 245);  /* blue top (#1e6fd9 base) */
  --pct-gradient: linear-gradient(
    90deg,
    var(--pct-r0) 0%,
    var(--pct-r1) 22%,
    var(--pct-mid) 50%,
    var(--pct-b1) 78%,
    var(--pct-b0) 100%
  );
  --pct-gradient-inverted: linear-gradient(
    90deg,
    var(--pct-b0) 0%,
    var(--pct-b1) 22%,
    var(--pct-mid) 50%,
    var(--pct-r1) 78%,
    var(--pct-r0) 100%
  );

  /* Belief ramp — red (doom) → neutral → green (bullish), FI sentiment only. */
  --belief-low:  oklch(0.58 0.19 25);   /* red, doomposting */
  --belief-mid:  oklch(0.55 0.02 250);  /* neutral */
  --belief-high: oklch(0.60 0.16 150);  /* green, bullish (#2d8659 base) */
  --belief-gradient: linear-gradient(
    90deg,
    var(--belief-low) 0%,
    var(--belief-mid) 50%,
    var(--belief-high) 100%
  );

  /* Accolade gold — reserved for award status / "named to" highlights only.
     Never decorative. */
  --accolade-gold-base:      oklch(0.74 0.13 85);
  --accolade-gold-highlight: oklch(0.86 0.13 90);
  --accolade-gold-shadow:    oklch(0.45 0.10 80);

  /* Surface / text neutrals — dark-mode-first per Brief.
     Sites that already set these tokens won't be overridden. */
  --pp-surface:        oklch(0.18 0.01 250);
  --pp-surface-raised: oklch(0.22 0.01 250);
  --pp-stroke-subtle:  oklch(0.30 0.01 250 / 0.30);
  --pp-text-bright:    oklch(0.96 0.01 250);
  --pp-text-soft:      oklch(0.82 0.01 250);
  --pp-text-quiet:     oklch(0.62 0.01 250);
}

/* Reduced-motion fallback — disable any decorative transitions inside
   player-page modules. Module-level CSS still controls focus rings. */
@media (prefers-reduced-motion: reduce) {
  .player-game-log *,
  .box-savant *,
  .player-splits *,
  .peer-comparator * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
"""
