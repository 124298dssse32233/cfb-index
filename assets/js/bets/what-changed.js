/*! what-changed.js — "since your last visit" diff card (Signature Bets S1.4).
 *
 *  Reads the page's embedded <script id="page-state"> JSON snapshot,
 *  compares it against the reader's prior snapshot stored in
 *  localStorage, and renders a dismissible card above the hero with up
 *  to 5 natural-language bullets describing what moved.
 *
 *  Progressive enhancement: without JS, the container is an empty
 *  <div data-what-changed> and nothing renders. First visits never
 *  render (prior snapshot missing). Dismissing the card writes a
 *  "seen-version" entry so it stays hidden until the next build bumps
 *  the page-state version hash.
 */
(function () {
  'use strict';

  var KEY_PREFIX = 'cfb:last-visit:';
  var MAX_BULLETS = 5;

  function readState() {
    var el = document.getElementById('page-state');
    if (!el) return null;
    try { return JSON.parse(el.textContent || '{}'); }
    catch (_e) { return null; }
  }

  function readSlug() {
    var el = document.getElementById('page-state');
    return el ? (el.getAttribute('data-player-slug') || '') : '';
  }

  function readLastVisit(slug) {
    try {
      var raw = window.localStorage.getItem(KEY_PREFIX + slug);
      return raw ? JSON.parse(raw) : null;
    } catch (_e) { return null; }
  }

  function writeLastVisit(slug, state) {
    try {
      window.localStorage.setItem(
        KEY_PREFIX + slug,
        JSON.stringify({
          version: state.version,
          generated_at: state.generated_at,
          payload: {
            heisman_heat:   state.heisman_heat,
            standing_rung:  state.standing_rung,
            room_mentions:  state.room_mentions,
            outlook_updates: state.outlook_updates || [],
            achievements:   state.achievements || [],
          },
          seen_at: new Date().toISOString(),
        })
      );
    } catch (_e) { /* localStorage full / disabled — silently degrade */ }
  }

  function signedDelta(now, prior, label, opts) {
    if (now == null || prior == null) return null;
    var diff = Number(now) - Number(prior);
    if (!diff) return null;
    var sign = diff > 0 ? '+' : '';
    var extras = (opts && opts.suffix) ? (' ' + opts.suffix) : '';
    return sign + diff + ' ' + label + extras;
  }

  function listDelta(now, prior, singular, pluralize) {
    now = Array.isArray(now) ? now : [];
    prior = Array.isArray(prior) ? prior : [];
    var priorSet = {};
    prior.forEach(function (k) { priorSet[String(k)] = 1; });
    var added = now.filter(function (k) { return !priorSet[String(k)]; });
    if (!added.length) return null;
    if (added.length === 1) return 'New ' + singular + ': ' + added[0];
    var plural = pluralize || (singular + 's');
    return added.length + ' new ' + plural + ': ' + added.join(', ');
  }

  function computeBullets(current, prior) {
    var out = [];
    var p = (prior && prior.payload) || {};
    var rungDelta = signedDelta(current.standing_rung, p.standing_rung, 'rung', { suffix: 'in Standing' });
    if (rungDelta) out.push(rungDelta);
    var heisman = (function () {
      if (current.heisman_heat == null || p.heisman_heat == null) return null;
      var delta = Number(p.heisman_heat) - Number(current.heisman_heat);
      if (!delta) return null;
      // lower rank = "up" in Heisman; flip sign for natural reading.
      var sign = delta > 0 ? '+' : '';
      return sign + delta + ' Heisman Heat';
    })();
    if (heisman) out.push(heisman);
    var roomDelta = signedDelta(current.room_mentions, p.room_mentions, 'mentions', { suffix: 'in The Room' });
    if (roomDelta) out.push(roomDelta);
    var outlookDelta = listDelta(current.outlook_updates, p.outlook_updates, 'outlook update', 'outlook updates');
    if (outlookDelta) out.push(outlookDelta);
    var achDelta = listDelta(current.achievements, p.achievements, 'achievement', 'achievements unlocked');
    if (achDelta) out.push(achDelta);
    return out.slice(0, MAX_BULLETS);
  }

  function render(host, bullets, current, slug) {
    var ul = bullets.map(function (b) { return '<li>' + b + '</li>'; }).join('');
    host.innerHTML =
      '<article class="what-changed" role="status" aria-label="Updates since your last visit">' +
      '  <header class="what-changed__header">' +
      '    <p class="what-changed__eyebrow">Since your last visit</p>' +
      '    <button class="what-changed__dismiss" type="button" aria-label="Dismiss">&times;</button>' +
      '  </header>' +
      '  <ul class="what-changed__bullets">' + ul + '</ul>' +
      '</article>';
    var dismiss = host.querySelector('.what-changed__dismiss');
    dismiss.addEventListener('click', function () {
      writeLastVisit(slug, current);
      host.innerHTML = '';
    });
  }

  function boot() {
    var host = document.querySelector('[data-what-changed]');
    if (!host) return;
    var current = readState();
    var slug = readSlug();
    if (!current || !slug) return;
    var prior = readLastVisit(slug);
    if (!prior) {
      writeLastVisit(slug, current);
      return;
    }
    if (prior.version === current.version) {
      // Same build + same state hash — nothing to tell them.
      return;
    }
    var bullets = computeBullets(current, prior);
    if (!bullets.length) {
      // State hash changed but no user-facing bullets — still record so
      // the reader doesn't see a stale comparison on the next visit.
      writeLastVisit(slug, current);
      return;
    }
    render(host, bullets, current, slug);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
