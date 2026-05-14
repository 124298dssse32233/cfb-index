/* ============================================================================
 * wcfb-enhancements.js — World-Class CFB Index behavior layer
 *
 * Loaded site-wide with `defer`. Strict mode, no global pollution beyond
 * `window.wcfb`. Idempotent: calling init twice is safe.
 *
 * Implements Phase 1.3 (emoji signposts), Phase 3.1 (tooltips),
 * Phase 4.3 (scroll reveals), Phase 6.1 (bottom nav), Phase 7.4 (dials).
 * ========================================================================= */
(function () {
  'use strict';
  if (window.wcfb && window.wcfb.__initialised) return;
  window.wcfb = window.wcfb || {};
  window.wcfb.__initialised = true;

  /* -------------------------------------------------------------------- */
  /* utilities                                                            */
  /* -------------------------------------------------------------------- */
  function onReady(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function isDarkPage() {
    // Heuristic: a page has a dark theme if html bg is dark OR body bg-0 is set
    var bg = getComputedStyle(document.documentElement).getPropertyValue('--bg-0').trim();
    return bg.startsWith('#0') || bg.startsWith('#1') || bg.startsWith('#2');
  }

  /* -------------------------------------------------------------------- */
  /* 1.3  Emoji signposts                                                 */
  /* Walk text nodes, decorate "↑3", "↓2", "elite tier" without HTML edit */
  /* -------------------------------------------------------------------- */
  // Use a content-walker that ONLY touches table cells, summary lines,
  // and small inline metric chips. Large prose paragraphs are skipped to
  // avoid emoji pollution.
  var SIGNPOST_SCOPE = [
    '.wcfb-stat-tile__delta',
    '.wcfb-sign',          // explicit opt-in
    '[data-wcfb-decorate]' // any other opt-in containers
  ].join(',');

  function decorateSignposts() {
    var nodes = document.querySelectorAll(SIGNPOST_SCOPE);
    nodes.forEach(function (el) {
      if (el.__wcfbDecorated) return;
      el.__wcfbDecorated = true;
      var text = el.textContent;
      // Up arrow / + / "rising"
      if (/(↑|\barrow_up\b|\bUP\s*\d|^\+\d|↑\s*\d|rising)/i.test(text)) {
        el.classList.add('wcfb-sign-up');
      } else if (/(↓|\barrow_down\b|\bDOWN\s*\d|^-\d|↓\s*\d|falling)/i.test(text)) {
        el.classList.add('wcfb-sign-down');
      } else if (/\belite\b/i.test(text)) {
        el.classList.add('wcfb-sign-elite');
      } else if (/\b(concern|alert|warning)\b/i.test(text)) {
        el.classList.add('wcfb-sign-warn');
      }
    });
  }

  /* -------------------------------------------------------------------- */
  /* 3.1  Interactive tooltips                                            */
  /* -------------------------------------------------------------------- */
  var tipPop = null;
  function ensureTipPop() {
    if (tipPop) return tipPop;
    tipPop = document.createElement('div');
    tipPop.className = 'wcfb-tip-pop';
    tipPop.setAttribute('role', 'tooltip');
    document.body.appendChild(tipPop);
    return tipPop;
  }

  function showTip(el) {
    var msg = el.getAttribute('data-wcfb-tip');
    if (!msg) return;
    var pop = ensureTipPop();
    pop.textContent = msg;
    pop.setAttribute('data-visible', 'true');
    var rect = el.getBoundingClientRect();
    var top = rect.bottom + window.scrollY + 8;
    var left = rect.left + window.scrollX;
    pop.style.top = top + 'px';
    // Clamp horizontally to viewport
    pop.style.left = Math.min(left, window.innerWidth - 340) + 'px';
  }
  function hideTip() {
    if (tipPop) tipPop.setAttribute('data-visible', 'false');
  }

  function bindTooltips() {
    document.querySelectorAll('[data-wcfb-tip]').forEach(function (el) {
      if (el.__wcfbTipBound) return;
      el.__wcfbTipBound = true;
      el.addEventListener('mouseenter', function () { showTip(el); });
      el.addEventListener('focus', function () { showTip(el); });
      el.addEventListener('mouseleave', hideTip);
      el.addEventListener('blur', hideTip);
    });
  }

  /* Auto-create tooltips for known glossary terms when the page has none */
  var GLOSSARY = {
    'Power':   'Power Rating: predicts future strength on a neutral field. Forward-looking.',
    'Resume':  'Resume Rating: backward-looking. Rewards quality wins and penalizes losses.',
    'SOS':     'Strength of Schedule: weighted average opponent rating.',
    'EPA':     'Expected Points Added: drive-level success metric, controlling for field position and down/distance.',
    'Belief':  'Fan Intelligence belief metric: aggregated fan-base conviction from social signals.'
  };
  function autoGlossary() {
    if (document.querySelector('[data-wcfb-tip]')) return; // already explicit
    // Only decorate inside dl.glossary or .metric-label spans to avoid grep'ing prose
    var scope = document.querySelectorAll('.metric-label, .wcfb-metric, dl.glossary dt');
    if (scope.length === 0) return;
    scope.forEach(function (el) {
      var key = el.textContent.trim();
      if (GLOSSARY[key] && !el.hasAttribute('data-wcfb-tip')) {
        el.setAttribute('data-wcfb-tip', GLOSSARY[key]);
      }
    });
  }

  /* -------------------------------------------------------------------- */
  /* 4.3  Scroll-based reveals                                            */
  /* -------------------------------------------------------------------- */
  function bindReveals() {
    if (!('IntersectionObserver' in window)) {
      // No-op fallback — reveal everything immediately
      document.querySelectorAll('.wcfb-reveal').forEach(function (el) {
        el.setAttribute('data-revealed', 'true');
      });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.setAttribute('data-revealed', 'true');
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    document.querySelectorAll('.wcfb-reveal').forEach(function (el) { io.observe(el); });
  }

  /* -------------------------------------------------------------------- */
  /* 6.1  Mobile bottom navigation (inject on every page <= 720px)        */
  /* -------------------------------------------------------------------- */
  var NAV_ITEMS = [
    { href: '/',              icon: '🏠', label: 'Home',  match: /^\/$/ },
    { href: '/rankings/',     icon: '📊', label: 'Rank',  match: /^\/rankings\// },
    { href: '/hub/',          icon: '💡', label: 'Hub',   match: /^\/hub\// },
    { href: '/compare/',      icon: '⚖️', label: 'Compare', match: /^\/compare\// },
    { href: '/methodology/',  icon: '📚', label: 'About', match: /^\/(methodology|about-model)/ }
  ];

  function injectBottomNav() {
    if (document.querySelector('.wcfb-bottom-nav')) return;
    var nav = document.createElement('nav');
    nav.className = 'wcfb-bottom-nav';
    nav.setAttribute('aria-label', 'Primary mobile navigation');
    var path = window.location.pathname;
    NAV_ITEMS.forEach(function (item) {
      var a = document.createElement('a');
      a.href = item.href;
      if (item.match.test(path)) a.setAttribute('aria-current', 'page');
      a.innerHTML = '<span class="wcfb-bottom-nav__icon" aria-hidden="true">' +
        item.icon + '</span>' + '<span>' + item.label + '</span>';
      nav.appendChild(a);
    });
    document.body.appendChild(nav);
  }

  /* -------------------------------------------------------------------- */
  /* 7.4  Probability dials                                               */
  /* Any element [data-wcfb-dial="<n>"] renders as a conic dial.           */
  /* -------------------------------------------------------------------- */
  function bindDials() {
    document.querySelectorAll('[data-wcfb-dial]').forEach(function (el) {
      if (el.__wcfbDialDone) return;
      el.__wcfbDialDone = true;
      var raw = parseFloat(el.getAttribute('data-wcfb-dial')) || 0;
      // accept 0..1 or 0..100
      var p = raw <= 1 ? raw * 100 : raw;
      p = Math.max(0, Math.min(100, Math.round(p)));
      el.classList.add('wcfb-dial');
      el.style.setProperty('--p', p);
      var band = p >= 67 ? 'high' : p >= 34 ? 'medium' : 'low';
      el.setAttribute('data-band', band);
      if (!el.querySelector('.wcfb-dial__label')) {
        var label = document.createElement('span');
        label.className = 'wcfb-dial__label';
        label.textContent = p + '%';
        el.appendChild(label);
      }
    });
  }

  /* -------------------------------------------------------------------- */
  /* Theme attribute — let CSS know what context we're in                 */
  /* -------------------------------------------------------------------- */
  function setThemeAttribute() {
    if (isDarkPage()) document.documentElement.setAttribute('data-wcfb-theme', 'dark');
  }

  /* -------------------------------------------------------------------- */
  /* Init                                                                 */
  /* -------------------------------------------------------------------- */
  onReady(function () {
    try { setThemeAttribute(); } catch (e) { /* swallow */ }
    try { autoGlossary(); } catch (e) {}
    try { bindTooltips(); } catch (e) {}
    try { decorateSignposts(); } catch (e) {}
    try { bindReveals(); } catch (e) {}
    try { injectBottomNav(); } catch (e) {}
    try { bindDials(); } catch (e) {}

    // Re-bind on DOM mutations (e.g. Alpine.js rendering)
    if ('MutationObserver' in window) {
      var mo = new MutationObserver(function () {
        try { bindTooltips(); } catch (e) {}
        try { decorateSignposts(); } catch (e) {}
        try { bindDials(); } catch (e) {}
      });
      mo.observe(document.body, { childList: true, subtree: true });
    }
  });

  /* Expose tiny API for future inline scripts */
  window.wcfb.refresh = function () {
    bindTooltips(); decorateSignposts(); bindDials();
  };
})();
