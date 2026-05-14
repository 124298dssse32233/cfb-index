/*! glossary.js — Fan Intelligence `?` popover (Bet #5, S1.1).
 *  Companion data file: fi-glossary-data.js (generated from
 *  seeds/fi_glossary.yaml; sets window.__FI_GLOSSARY__).
 *
 *  Usage: any element with `data-fi-glossary-term="<slug>"` opens the
 *  popover for that term on click or Enter/Space. The popover is a
 *  native <dialog> so Esc-to-close and the backdrop come free.
 *
 *  Progressive enhancement: if JS is disabled or the data file hasn't
 *  loaded yet, the `?` buttons act as <a href="/methodology/fan-
 *  intelligence.html#glossary-<slug>"> fallbacks.
 */
(function () {
  'use strict';

  var DIALOG_ID = 'fi-glossary-dialog';
  var METHODOLOGY_URL = '/methodology/fan-intelligence.html';

  function ensureDialog() {
    var dlg = document.getElementById(DIALOG_ID);
    if (dlg) return dlg;
    dlg = document.createElement('dialog');
    dlg.id = DIALOG_ID;
    dlg.className = 'fi-glossary-popover';
    dlg.setAttribute('aria-labelledby', 'fi-glossary-name');
    dlg.innerHTML = [
      '<form method="dialog" class="fi-glossary-popover__form">',
      '  <header class="fi-glossary-popover__header">',
      '    <p class="fi-glossary-popover__eyebrow">Fan Intelligence glossary</p>',
      '    <h2 class="fi-glossary-popover__name" id="fi-glossary-name"></h2>',
      '    <button class="fi-glossary-popover__close" type="submit" value="close" aria-label="Close glossary">&times;</button>',
      '  </header>',
      '  <p class="fi-glossary-popover__one-line"></p>',
      '  <p class="fi-glossary-popover__full"></p>',
      '  <p class="fi-glossary-popover__micro"><span class="fi-glossary-popover__micro-label">Example &middot; </span><span class="fi-glossary-popover__micro-body"></span></p>',
      '  <p class="fi-glossary-popover__see-also" hidden><span class="fi-glossary-popover__see-label">See also &middot; </span><span class="fi-glossary-popover__see-body"></span></p>',
      '  <p class="fi-glossary-popover__footer"><a class="fi-glossary-popover__method-link" href="' + METHODOLOGY_URL + '">Full methodology &rarr;</a></p>',
      '</form>'
    ].join('');
    document.body.appendChild(dlg);
    return dlg;
  }

  function fillDialog(dlg, term) {
    dlg.querySelector('.fi-glossary-popover__name').textContent = term.name;
    dlg.querySelector('.fi-glossary-popover__one-line').textContent = term.one_line;
    dlg.querySelector('.fi-glossary-popover__full').textContent = term.full;
    dlg.querySelector('.fi-glossary-popover__micro-body').textContent = term.micro_example;
    var see = (term.see_also || []).filter(Boolean);
    var seeWrap = dlg.querySelector('.fi-glossary-popover__see-also');
    var seeBody = dlg.querySelector('.fi-glossary-popover__see-body');
    if (see.length && window.__FI_GLOSSARY__) {
      var links = see.map(function (slug) {
        var other = window.__FI_GLOSSARY__[slug];
        var label = other ? other.name : slug;
        return '<button type="button" class="fi-glossary-popover__see-link" data-fi-glossary-term="' + slug + '">' + label + '</button>';
      });
      seeBody.innerHTML = links.join(' &middot; ');
      seeWrap.hidden = false;
    } else {
      seeWrap.hidden = true;
    }
    var methodLink = dlg.querySelector('.fi-glossary-popover__method-link');
    methodLink.setAttribute('href', METHODOLOGY_URL + '#glossary-' + term.slug);
  }

  function openGlossary(slug) {
    var data = window.__FI_GLOSSARY__ || {};
    var term = data[slug];
    if (!term) {
      // Data not loaded — let the <a> fallback handle it (native nav).
      window.location.href = METHODOLOGY_URL + '#glossary-' + slug;
      return;
    }
    var dlg = ensureDialog();
    fillDialog(dlg, term);
    if (typeof dlg.showModal === 'function') {
      try { dlg.showModal(); }
      catch (_e) { dlg.setAttribute('open', ''); }
    } else {
      dlg.setAttribute('open', '');
    }
  }

  function onDocClick(event) {
    var btn = event.target && event.target.closest
      ? event.target.closest('[data-fi-glossary-term]')
      : null;
    if (!btn) return;
    var slug = btn.getAttribute('data-fi-glossary-term');
    if (!slug) return;
    event.preventDefault();
    openGlossary(slug);
  }

  // Enter/Space already trigger click on <button>; for <a> fallback we
  // still call preventDefault above so native nav doesn't also fire.

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      document.addEventListener('click', onDocClick);
    });
  } else {
    document.addEventListener('click', onDocClick);
  }

  // Expose for programmatic callers (e.g., a future "press ? to open
  // global glossary" keyboard shortcut — kickoff §5 item 16).
  window.fiGlossary = { open: openGlossary };
})();
