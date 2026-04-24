/*! signal-flow.js — Live Signal Flow bar behaviour (Signature Bets S1.6).
 *
 *  The server renders the bar when fetch_active_signals() returned ≥ 1
 *  signal for a player; this script adds expand/collapse + fades the
 *  bar's opacity as its decay window runs out.
 *
 *  The server also embeds data-remaining-fraction (0..1) per event;
 *  we read it on tick and bind opacity. When fraction reaches 0 we
 *  hide the bar entirely — a reader on a stale cached page doesn't
 *  see a signal that has since expired.
 */
(function () {
  'use strict';

  var TICK_MS = 60 * 1000;

  function fractionFor(event) {
    var start = event.getAttribute('data-event-ts');
    var decay = parseFloat(event.getAttribute('data-decay-hours') || '72');
    if (!start || !(decay > 0)) return 0;
    var startMs = Date.parse(start);
    if (isNaN(startMs)) return 0;
    var elapsedMs = Date.now() - startMs;
    var totalMs = decay * 3600 * 1000;
    return Math.max(0, Math.min(1, 1 - elapsedMs / totalMs));
  }

  function updateOpacity(host) {
    var events = host.querySelectorAll('.signal-flow__event');
    var anyActive = false;
    events.forEach(function (ev) {
      var frac = fractionFor(ev);
      if (frac <= 0) {
        ev.hidden = true;
      } else {
        ev.hidden = false;
        anyActive = true;
        // Floor the visual opacity at 0.45 so old-but-still-live signals
        // remain readable; bright right after emission, muted at the end.
        ev.style.opacity = (0.45 + 0.55 * frac).toFixed(2);
      }
    });
    if (!anyActive) host.hidden = true;
  }

  function wireExpand(host) {
    var toggle = host.querySelector('.signal-flow__toggle');
    if (!toggle) return;
    toggle.addEventListener('click', function () {
      var expanded = host.getAttribute('aria-expanded') === 'true';
      host.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    });
  }

  function boot() {
    var host = document.querySelector('[data-signal-flow]');
    if (!host) return;
    wireExpand(host);
    updateOpacity(host);
    setInterval(function () { updateOpacity(host); }, TICK_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
