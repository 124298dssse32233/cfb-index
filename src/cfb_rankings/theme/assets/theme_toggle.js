/* Theme toggle (Sprint v5-11.5 dark mode foundation)
 * -------------------------------------------------------------------------
 * Self-contained vanilla JS — no framework dep. Behaviors:
 *   - Click [data-theme-toggle] cycles system → light → dark → system
 *   - Persists choice to localStorage as 'cfb-theme-pref'
 *   - Applies to <html> as data-theme="light|dark" (system removes attr)
 *   - Tooltip shows "Switch to <next>"
 *   - Listens to prefers-color-scheme changes when in system mode
 *     and emits a 'cfb-theme-changed' CustomEvent so other components
 *     can react (e.g. chart re-renderers)
 *   - Programmatic API: window.cfbTheme.{set, cycle, current, system}
 *
 * Spec: docs/octopus/v5_11_5_sprint_brief.md §"Cmd-K toggle hook"
 */
(function () {
  'use strict';
  if (typeof document === 'undefined') return;

  var STORAGE_KEY = 'cfb-theme-pref';
  var ORDER = ['system', 'light', 'dark'];
  var ROOT = document.documentElement;

  // ---- State + persistence ----
  function readPref() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      if (v === 'light' || v === 'dark' || v === 'system') return v;
    } catch (e) { /* unavailable */ }
    return 'system';
  }

  function writePref(value) {
    try { localStorage.setItem(STORAGE_KEY, value); } catch (e) { /* quota */ }
  }

  // ---- Apply theme ----
  function apply(pref) {
    if (pref === 'light' || pref === 'dark') {
      ROOT.setAttribute('data-theme', pref);
    } else {
      ROOT.removeAttribute('data-theme');
    }
    updateButtons(pref);
    // Notify any listeners that the effective theme has changed
    document.dispatchEvent(new CustomEvent('cfb-theme-changed', {
      detail: { pref: pref, effective: effectiveTheme() }
    }));
  }

  // ---- Compute the effective theme (resolves 'system' to actual mode) ----
  function effectiveTheme() {
    var pref = readPref();
    if (pref === 'light' || pref === 'dark') return pref;
    return window.matchMedia &&
           window.matchMedia('(prefers-color-scheme: light)').matches
      ? 'light' : 'dark';
  }

  // ---- Cycle through states ----
  function cycle() {
    var current = readPref();
    var idx = ORDER.indexOf(current);
    var next = ORDER[(idx + 1) % ORDER.length];
    writePref(next);
    apply(next);
    return next;
  }

  // ---- Set explicit state ----
  function setTheme(pref) {
    if (ORDER.indexOf(pref) < 0) return false;
    writePref(pref);
    apply(pref);
    return true;
  }

  // ---- Update toggle buttons ----
  function updateButtons(pref) {
    var nextLabel = {
      'system': 'Switch to light',
      'light': 'Switch to dark',
      'dark': 'Switch to system'
    }[pref] || '';
    var buttons = document.querySelectorAll('[data-theme-toggle]');
    for (var i = 0; i < buttons.length; i++) {
      var btn = buttons[i];
      btn.setAttribute('data-state', pref);
      btn.setAttribute('data-next-label', nextLabel);
      btn.setAttribute(
        'aria-label',
        'Theme: ' + pref + '. Click to ' +
        (nextLabel || 'change').toLowerCase() + '.'
      );
      btn.setAttribute('aria-pressed', pref === 'system' ? 'false' : 'true');
      // Build icons + click handler if not already done
      ensureButtonContent(btn);
    }
  }

  function ensureButtonContent(btn) {
    if (btn.dataset.themeReady === '1') return;
    btn.dataset.themeReady = '1';
    btn.setAttribute('type', 'button');
    btn.innerHTML =
      // System icon — circle half-filled
      '<svg class="theme-toggle__icon theme-toggle__icon--system" viewBox="0 0 24 24" aria-hidden="true">' +
      '<path d="M12 3a9 9 0 100 18 9 9 0 000-18zm0 2v14a7 7 0 010-14z"/>' +
      '</svg>' +
      // Sun icon
      '<svg class="theme-toggle__icon theme-toggle__icon--light" viewBox="0 0 24 24" aria-hidden="true">' +
      '<path d="M12 17a5 5 0 100-10 5 5 0 000 10zm0-13a1 1 0 011 1v1.5a1 1 0 11-2 0V5a1 1 0 011-1zm0 15a1 1 0 011 1V21a1 1 0 11-2 0v-1a1 1 0 011-1zM5 12a1 1 0 011-1H4.5a1 1 0 110 2H6a1 1 0 01-1-1zm14 0a1 1 0 011-1h-1.5a1 1 0 110 2H20a1 1 0 01-1-1zM6.34 6.34a1 1 0 011.41 0l1.06 1.06a1 1 0 11-1.41 1.41L6.34 7.75a1 1 0 010-1.41zm9.19 9.19a1 1 0 011.41 0l1.06 1.06a1 1 0 11-1.41 1.41l-1.06-1.06a1 1 0 010-1.41zM6.34 17.66a1 1 0 010-1.41l1.06-1.06a1 1 0 111.41 1.41L7.75 17.66a1 1 0 01-1.41 0zm9.19-9.19a1 1 0 010-1.41l1.06-1.06a1 1 0 111.41 1.41l-1.06 1.06a1 1 0 01-1.41 0z"/>' +
      '</svg>' +
      // Moon icon
      '<svg class="theme-toggle__icon theme-toggle__icon--dark" viewBox="0 0 24 24" aria-hidden="true">' +
      '<path d="M20 14.5A8 8 0 019.5 4a8.5 8.5 0 1010.5 10.5z"/>' +
      '</svg>';
  }

  // ---- Wire up clicks via delegation ----
  document.addEventListener('click', function (e) {
    var target = e.target;
    if (!target) return;
    var btn = target.closest && target.closest('[data-theme-toggle]');
    if (!btn) return;
    e.preventDefault();
    cycle();
  });

  // ---- React to OS-level prefers-color-scheme changes when in system mode ----
  if (window.matchMedia) {
    var mql = window.matchMedia('(prefers-color-scheme: light)');
    var listener = function () {
      if (readPref() === 'system') {
        // Re-emit so listeners can re-render
        document.dispatchEvent(new CustomEvent('cfb-theme-changed', {
          detail: { pref: 'system', effective: effectiveTheme() }
        }));
      }
    };
    if (mql.addEventListener) mql.addEventListener('change', listener);
    else if (mql.addListener) mql.addListener(listener);
  }

  // ---- Initial state ----
  // Wait for DOM so [data-theme-toggle] buttons exist
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { apply(readPref()); });
  } else {
    apply(readPref());
  }

  // ---- Public API ----
  window.cfbTheme = {
    current: readPref,
    effective: effectiveTheme,
    cycle: cycle,
    set: setTheme,
    system: function () { return setTheme('system'); }
  };
})();
