/*! keyboard-shortcuts.js — power-user navigation (Signature Bets S4.1).
 *
 *  Bindings (ignored while focus is inside an editable field):
 *   ?        — open the global FI glossary popover
 *   J / K    — next / prev player-anchor section
 *   G {a-z}  — jump to a specific section (2-key chord, 1500ms timeout)
 *   S        — toggle screenshot mode (sets body[data-screenshot-mode])
 *   /        — focus the peer search, if present
 *   C        — copy the current URL (incl. query state) to clipboard
 *   [ / ]    — prev / next game in game-scoped modules (placeholder; today
 *              dispatches `cfb:game-nav` events for future per-module wiring)
 *   Esc      — exit screenshot mode / close dialogs (native dialog
 *              already handles; we set body attr off too)
 *
 *  Progressive enhancement: without JS, the page works unchanged — these
 *  are add-ons. No visual affordance today; follow-up ships a "?" help
 *  overlay in its own task.
 */
(function () {
  'use strict';

  var CHORD_MS = 1500;
  var CHORD_LEAD = 'g';

  // Map second chord key → css-selector / anchor id.
  var CHORD_TARGETS = {
    r: '#the-room',                // Room
    s: '#signature-story',         // Story / Signature
    m: '#achievements',            // Moments (nearest = achievements block)
    a: '#achievements',            // Achievements
    v: '#rival-radar',             // riVal radar
    c: '#peer-comparator',         // Comparator
    l: '#supporting-cast',         // Lineage (near Supporting Cast)
    p: '#current-heisman-lens',    // Heisman Pulse / current lens
    b: '#bio-tabs',                // Bio
    t: '#trophy-case',             // Trophy case
    i: '#identity-role',           // Identity
  };

  var chordPrimed = 0;   // timestamp
  function chordActive() { return (Date.now() - chordPrimed) < CHORD_MS; }

  function isEditableTarget(el) {
    if (!el) return false;
    if (el.isContentEditable) return true;
    var tag = (el.tagName || '').toUpperCase();
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
    return false;
  }

  function getAllAnchors() {
    return Array.from(document.querySelectorAll('.player-anchor-section[id]'));
  }

  function currentAnchorIndex(anchors) {
    var y = window.scrollY + 80;
    var idx = 0;
    for (var i = 0; i < anchors.length; i++) {
      if (anchors[i].offsetTop <= y) idx = i;
      else break;
    }
    return idx;
  }

  function scrollToSection(sel) {
    var el = typeof sel === 'string' ? document.querySelector(sel) : sel;
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    // Update hash without triggering jump.
    if (el.id) {
      history.replaceState(null, '', '#' + el.id);
    }
  }

  function nextSection(delta) {
    var anchors = getAllAnchors();
    if (!anchors.length) return;
    var i = currentAnchorIndex(anchors);
    var j = Math.max(0, Math.min(anchors.length - 1, i + delta));
    scrollToSection(anchors[j]);
  }

  function openGlossaryPopover() {
    if (window.fiGlossary && typeof window.fiGlossary.open === 'function') {
      window.fiGlossary.open('belief-dial');
      return;
    }
    // Fallback — methodology page.
    window.location.href = '/methodology/fan-intelligence.html#glossary';
  }

  function toggleScreenshotMode() {
    var body = document.body;
    var on = body.getAttribute('data-screenshot-mode') === 'on';
    body.setAttribute('data-screenshot-mode', on ? 'off' : 'on');
  }

  function copyCurrentUrl() {
    var url = location.href;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).catch(function () { /* noop */ });
    }
    // Toast: best-effort; if none exists, silently succeed.
    var toast = document.querySelector('[data-kb-toast]');
    if (toast) {
      toast.textContent = 'URL copied to clipboard';
      toast.setAttribute('data-open', 'true');
      setTimeout(function () { toast.setAttribute('data-open', 'false'); }, 1800);
    }
  }

  function focusPeerSearch() {
    var input = document.querySelector('[data-peer-search]')
             || document.querySelector('.peer-comparator__search')
             || document.querySelector('input[type="search"]');
    if (input) {
      input.focus();
      if (input.select) input.select();
    }
  }

  function dispatchGameNav(dir) {
    window.dispatchEvent(new CustomEvent('cfb:game-nav', { detail: { dir: dir } }));
  }

  function onKeydown(ev) {
    if (isEditableTarget(ev.target)) return;
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    var key = (ev.key || '').toLowerCase();

    if (chordActive()) {
      chordPrimed = 0;
      var sel = CHORD_TARGETS[key];
      if (sel) {
        scrollToSection(sel);
        ev.preventDefault();
        return;
      }
      return;
    }

    switch (key) {
      case '?':
        openGlossaryPopover();
        ev.preventDefault();
        return;
      case 'j':
        nextSection(1);
        ev.preventDefault();
        return;
      case 'k':
        nextSection(-1);
        ev.preventDefault();
        return;
      case 'g':
        chordPrimed = Date.now();
        ev.preventDefault();
        return;
      case 's':
        toggleScreenshotMode();
        ev.preventDefault();
        return;
      case '/':
        focusPeerSearch();
        ev.preventDefault();
        return;
      case 'c':
        copyCurrentUrl();
        ev.preventDefault();
        return;
      case '[':
        dispatchGameNav('prev');
        ev.preventDefault();
        return;
      case ']':
        dispatchGameNav('next');
        ev.preventDefault();
        return;
      case 'escape':
        document.body.setAttribute('data-screenshot-mode', 'off');
        return;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      document.addEventListener('keydown', onKeydown);
    });
  } else {
    document.addEventListener('keydown', onKeydown);
  }

  // Expose for debugging / test.
  window.cfbKeyboard = {
    scrollToSection: scrollToSection,
    nextSection: nextSection,
    openGlossary: openGlossaryPopover,
    toggleScreenshot: toggleScreenshotMode,
  };
})();
