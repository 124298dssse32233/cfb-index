"""Theme toggle (Sprint v5-11.5 dark mode foundation).

Self-contained light/dark/system theme toggle component. Pairs with the
``tokens-bridge.css`` PoC (already shipped in docs/design-system/assets/
via PR #122) to provide a complete dark-mode-toggle solution.

The toggle:
  * Three states — light / dark / system (respect prefers-color-scheme)
  * Persists choice to localStorage (key: cfb-theme-pref)
  * Applies via [data-theme="light"|"dark"] attribute on <html>
  * Triggers an early-script (FOUC prevention) to set the attribute
    before first paint

Markup is injected on first activation, but the toggle button is opt-in
via a placeholder element:

    <button class="theme-toggle" data-theme-toggle></button>

Or the host page can call ``window.cfbTheme.cycle()`` programmatically.

Asset files:
  * src/cfb_rankings/theme/assets/theme_toggle.css — button + dialog
    styling, var() fallback chains for cross-renderer compatibility
  * src/cfb_rankings/theme/assets/theme_toggle.js — toggle logic,
    localStorage persistence, programmatic API
  * src/cfb_rankings/theme/assets/theme_init.js — TINY FOUC-prevention
    script that reads localStorage + sets data-theme synchronously
    BEFORE the page renders. MUST load in <head>, not deferred.

Integration into the host page (Window A's lane):

  <!DOCTYPE html>
  <html>
  <head>
    <script>{theme_init.js inlined}</script>    <!-- FOUC fix, NOT deferred -->
    <link rel="stylesheet" href="/assets/tokens-bridge.css">
    <link rel="stylesheet" href="/assets/theme_toggle.css">
    ...
    <script defer src="/assets/theme_toggle.js"></script>
  </head>
  <body>
    <header>
      <button class="theme-toggle" data-theme-toggle></button>
    </header>
  </body>
  </html>

Spec: docs/octopus/v5_11_5_sprint_brief.md §"Part 2 — Path C"
"""

from .render import (
    THEME_INIT_SCRIPT,
    render_theme_toggle_button,
    render_theme_assets_head,
)

__all__ = [
    "THEME_INIT_SCRIPT",
    "render_theme_toggle_button",
    "render_theme_assets_head",
]
