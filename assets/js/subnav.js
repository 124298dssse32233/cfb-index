/*! subnav.js — Sticky player-page subnav with IntersectionObserver
 *  scroll-spy. Frontend Migration S.5g.
 *
 *  Looks for a <nav class="player-subnav"> with anchor <a href="#id">
 *  links. For each anchor, observes the matching #id section. When a
 *  section is in view, sets aria-current="page" on its nav link. Also
 *  tracks scroll position to flip a `.is-stuck` class on the nav once
 *  scrolled past the page hero.
 */
(function () {
  function init() {
    var nav = document.querySelector('.player-subnav');
    if (!nav) return;
    var links = Array.prototype.slice.call(nav.querySelectorAll('a[href^="#"]'));
    if (!links.length) return;
    var sectionMap = {};
    links.forEach(function (link) {
      var id = link.getAttribute('href').slice(1);
      var section = document.getElementById(id);
      if (section) sectionMap[id] = link;
    });
    var sections = Object.keys(sectionMap).map(function (id) { return document.getElementById(id); });
    if (!sections.length || typeof IntersectionObserver === 'undefined') return;
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var id = entry.target.id;
        var link = sectionMap[id];
        if (!link) return;
        // Clear all aria-current first, then set on the active.
        links.forEach(function (l) { l.removeAttribute('aria-current'); });
        link.setAttribute('aria-current', 'page');
        // Auto-scroll the active link into view in the horizontal strip.
        try { link.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' }); } catch (_e) {}
      });
    }, { rootMargin: '-30% 0px -60% 0px' });
    sections.forEach(function (s) { observer.observe(s); });

    // Sticky-stuck class: flip when nav reaches top of viewport.
    var sentinel = document.createElement('div');
    sentinel.style.cssText = 'position:absolute;top:0;height:1px;width:1px;visibility:hidden;';
    nav.parentNode.insertBefore(sentinel, nav);
    var stickObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        nav.classList.toggle('is-stuck', !entry.isIntersecting);
      });
    });
    stickObserver.observe(sentinel);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
