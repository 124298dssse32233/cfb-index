/* Receipt pattern — mobile tap-reveal for citation markers
 * -------------------------------------------------------------------------
 * On desktop the CSS :hover tooltip handles citation labels. On mobile
 * (no hover), tap reveals an inline expansion below the marker.
 *
 * Defensive: the script no-ops gracefully when no .citation nodes exist.
 * Listener uses event delegation so dynamically-inserted citations work too.
 *
 * Spec: docs/design-system/32-receipt-pattern.md §"Tap-reveal"
 */
(function () {
  'use strict';
  if (typeof document === 'undefined') return;

  // Hover-capable devices already get the CSS tooltip — skip the JS.
  var noHover = window.matchMedia &&
    window.matchMedia('(hover: none), (pointer: coarse)').matches;

  function ensureDetail(citationEl) {
    var existing = citationEl.nextElementSibling;
    if (existing && existing.classList.contains('citation-detail')) {
      return existing;
    }
    var detail = document.createElement('span');
    detail.className = 'citation-detail';
    detail.setAttribute('role', 'note');
    detail.style.display = 'block';
    detail.style.marginTop = '0.4em';
    detail.style.padding = '0.5em 0.75em';
    detail.style.fontSize = '13px';
    detail.style.fontWeight = '400';
    detail.style.lineHeight = '1.45';
    detail.style.background = 'var(--bg-card-raised, #1e2330)';
    detail.style.border =
      '1px solid var(--stroke-default, rgba(255,255,255,0.08))';
    detail.style.borderRadius = '6px';
    detail.style.color = 'var(--fg-primary, #f5f6fa)';
    detail.style.fontFamily = 'var(--font-body)';
    var label = citationEl.getAttribute('data-cite-label') || '';
    var url = citationEl.getAttribute('data-cite-url') || '';
    var kind = citationEl.getAttribute('data-cite-kind') || '';
    detail.appendChild(document.createTextNode(label));
    if (url) {
      detail.appendChild(document.createTextNode(' '));
      var link = document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'View source →';
      link.style.color = 'var(--accent-primary)';
      detail.appendChild(link);
    }
    if (kind) {
      detail.setAttribute('data-kind', kind);
    }
    citationEl.parentNode.insertBefore(detail, citationEl.nextSibling);
    return detail;
  }

  document.addEventListener('click', function (event) {
    if (!noHover) return;
    var target = event.target;
    if (!target) return;
    var citationEl = target.closest && target.closest('.citation');
    if (!citationEl) return;
    var anchor = target.closest && target.closest('a');
    if (anchor && anchor.getAttribute('href') &&
        anchor.getAttribute('href').indexOf('#cite-') === 0) {
      // Let the in-page anchor navigation happen — that's the
      // desired fallback when JS misfires.
      return;
    }
    event.preventDefault();
    var expanded = citationEl.getAttribute('aria-expanded') === 'true';
    citationEl.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    var detail = ensureDetail(citationEl);
    detail.style.display = expanded ? 'none' : 'block';
  }, false);
})();
