/*! context-menu.js — right-click actions on metric elements
 *  (Signature Bets S4.12 / §5 item 17).
 *
 *  Any element with data-metric="{label}|{value}" opens a small menu
 *  on right-click (contextmenu event) with:
 *    - Why this number?  (opens methodology glossary, tries to guess slug)
 *    - Copy as tweet     (writes a one-line summary to clipboard)
 *    - Copy page URL
 *    - Compare to another player  (future — today scrolls to Peer Comparator)
 *
 *  Falls back to the browser's default context menu when the target
 *  isn't metric-tagged. Keyboard users: Shift+F10 is the native
 *  equivalent and the same handler picks it up.
 */
(function () {
  'use strict';

  var MENU_ID = 'cfb-ctx-menu';

  function ensureMenu() {
    var m = document.getElementById(MENU_ID);
    if (m) return m;
    m = document.createElement('div');
    m.id = MENU_ID;
    m.className = 'cfb-ctx-menu';
    m.setAttribute('role', 'menu');
    m.setAttribute('aria-hidden', 'true');
    m.style.display = 'none';
    m.innerHTML =
      '<button role="menuitem" data-action="why">Why this number?</button>' +
      '<button role="menuitem" data-action="tweet">Copy as tweet</button>' +
      '<button role="menuitem" data-action="url">Copy page URL</button>' +
      '<button role="menuitem" data-action="compare">Compare to another player</button>';
    document.body.appendChild(m);
    m.addEventListener('click', function (ev) {
      var btn = ev.target && ev.target.closest('[data-action]');
      if (!btn) return;
      var action = btn.getAttribute('data-action');
      handleAction(action, currentTarget);
      hideMenu();
    });
    return m;
  }

  var currentTarget = null;

  function showMenu(x, y, target) {
    var m = ensureMenu();
    currentTarget = target;
    m.style.display = 'grid';
    m.setAttribute('aria-hidden', 'false');
    // Keep inside viewport.
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    m.style.left = Math.min(x, vw - 260) + 'px';
    m.style.top  = Math.min(y, vh - 200) + 'px';
  }

  function hideMenu() {
    var m = ensureMenu();
    m.style.display = 'none';
    m.setAttribute('aria-hidden', 'true');
    currentTarget = null;
  }

  function metricInfo(target) {
    if (!target) return { label: '', value: '' };
    var raw = target.getAttribute('data-metric') || '';
    var parts = raw.split('|');
    return { label: (parts[0] || '').trim(), value: (parts[1] || '').trim() };
  }

  function handleAction(action, target) {
    var info = metricInfo(target);
    var url = location.href;
    switch (action) {
      case 'why':
        if (window.fiGlossary && typeof window.fiGlossary.open === 'function') {
          // Guess a slug — kebab-case the label.
          var slug = info.label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
          if (slug) window.fiGlossary.open(slug);
          else window.location.href = '/methodology/fan-intelligence.html#glossary';
        } else {
          window.location.href = '/methodology/fan-intelligence.html#glossary';
        }
        return;
      case 'tweet': {
        var text = info.label && info.value
          ? info.value + ' ' + info.label + ' — ' + url
          : document.title + ' — ' + url;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).catch(function () { /* noop */ });
        }
        return;
      }
      case 'url':
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(url).catch(function () { /* noop */ });
        }
        return;
      case 'compare': {
        var peer = document.getElementById('peer-comparator');
        if (peer) peer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
      }
    }
  }

  function onContextMenu(ev) {
    var target = ev.target && ev.target.closest ? ev.target.closest('[data-metric]') : null;
    if (!target) return;
    ev.preventDefault();
    showMenu(ev.clientX, ev.clientY, target);
  }

  function onDocClick(ev) {
    var m = document.getElementById(MENU_ID);
    if (!m || m.style.display === 'none') return;
    if (m.contains(ev.target)) return;
    hideMenu();
  }

  function boot() {
    document.addEventListener('contextmenu', onContextMenu);
    document.addEventListener('click', onDocClick);
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') hideMenu();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
