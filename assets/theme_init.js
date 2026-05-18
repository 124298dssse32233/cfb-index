/* Theme init — FOUC prevention. MUST load synchronously in <head>.
 * -------------------------------------------------------------------------
 * Reads cfb-theme-pref from localStorage. If "light" or "dark", sets
 * data-theme on <html> BEFORE first paint, so the page renders correctly.
 * If "system" or unset, removes data-theme and lets prefers-color-scheme
 * decide.
 *
 * Keep this script tiny. The full toggle UI loads via theme_toggle.js
 * (deferred). This is just the synchronous attribute-setter.
 *
 * Spec: docs/octopus/v5_11_5_sprint_brief.md §"Part 2 — Path C"
 */
(function () {
  try {
    var pref = localStorage.getItem('cfb-theme-pref');
    var root = document.documentElement;
    if (pref === 'light' || pref === 'dark') {
      root.setAttribute('data-theme', pref);
    } else {
      root.removeAttribute('data-theme');
    }
  } catch (e) { /* localStorage unavailable — silently fall through to OS pref */ }
})();
