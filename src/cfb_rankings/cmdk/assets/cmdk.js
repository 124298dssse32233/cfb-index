/* Command-K overlay (Sprint v5-11.5 foundation)
 * -------------------------------------------------------------------------
 * Self-contained vanilla JS — no framework dependency. Behavior:
 *   - Cmd-K (macOS) / Ctrl-K (Win/Linux) opens the overlay
 *   - Clicking any [data-cmdk-trigger] opens it
 *   - Esc, click on backdrop, or click on an item closes it
 *   - Up/Down keys navigate; Enter follows the selected item.url
 *   - Index is fetched once from window.CMDK_INDEX_URL or
 *     "/search-index.json", cached in sessionStorage on success
 *   - Empty input shows a grouped "browse all" view (top items per kind)
 *
 * Customize via window.CMDK_CONFIG:
 *   {
 *     indexUrl: "/search-index.json",
 *     maxResults: 24,
 *     placeholder: "Search teams, players, editions…",
 *   }
 *
 * No HTML required in the page — the script injects nodes on first
 * activation. Safe to load with <script defer> in the global header.
 *
 * Spec: docs/octopus/v5_11_5_sprint_brief.md §Part 3
 */
(function () {
  'use strict';
  if (typeof document === 'undefined') return;

  // ---- Configuration ----
  var CONFIG = Object.assign({
    indexUrl: '/search-index.json',
    maxResults: 24,
    placeholder: 'Search teams, players, editions…',
    storageKey: 'cmdk:index-v1',
    storageTtlMs: 6 * 60 * 60 * 1000  // 6 hours
  }, window.CMDK_CONFIG || {});

  // ---- State ----
  var index = null;           // { items: [], schema_version: 1 }
  var dialog = null;          // .cmdk-dialog DOM node
  var backdrop = null;
  var input = null;
  var resultsEl = null;
  var selectedIdx = 0;
  var currentItems = [];      // currently rendered items in order
  var indexLoading = false;
  var openCount = 0;

  // ---- Build the DOM (idempotent) ----
  function build() {
    if (dialog) return;
    backdrop = document.createElement('div');
    backdrop.className = 'cmdk-backdrop';
    backdrop.setAttribute('aria-hidden', 'true');
    backdrop.addEventListener('click', close);

    dialog = document.createElement('div');
    dialog.className = 'cmdk-dialog';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-label', 'Search');
    dialog.setAttribute('aria-hidden', 'true');

    // Input row
    var inputWrap = document.createElement('div');
    inputWrap.className = 'cmdk-input-wrap';
    inputWrap.innerHTML =
      '<svg class="cmdk-input-icon" viewBox="0 0 20 20" aria-hidden="true">' +
      '<path d="M9 2a7 7 0 015.29 11.59l4.06 4.06-1.42 1.41-4.05-4.06A7 7 0 119 2zm0 2a5 5 0 100 10 5 5 0 000-10z"/>' +
      '</svg>';
    input = document.createElement('input');
    input.className = 'cmdk-input';
    input.type = 'text';
    input.placeholder = CONFIG.placeholder;
    input.setAttribute('aria-label', 'Search query');
    input.setAttribute('aria-controls', 'cmdk-results');
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('spellcheck', 'false');
    input.addEventListener('input', onInput);
    input.addEventListener('keydown', onKeyDown);
    inputWrap.appendChild(input);

    var shortcut = document.createElement('span');
    shortcut.className = 'cmdk-shortcut';
    shortcut.textContent = 'Esc';
    inputWrap.appendChild(shortcut);

    dialog.appendChild(inputWrap);

    // Results region
    resultsEl = document.createElement('div');
    resultsEl.className = 'cmdk-results';
    resultsEl.id = 'cmdk-results';
    resultsEl.setAttribute('role', 'listbox');
    dialog.appendChild(resultsEl);

    // Footer hints
    var footer = document.createElement('div');
    footer.className = 'cmdk-footer';
    footer.innerHTML =
      '<span><span class="cmdk-footer__key">↑↓</span>navigate</span>' +
      '<span><span class="cmdk-footer__key">↵</span>open</span>' +
      '<span><span class="cmdk-footer__key">esc</span>close</span>';
    dialog.appendChild(footer);

    document.body.appendChild(backdrop);
    document.body.appendChild(dialog);
  }

  // ---- Index loading ----
  function loadIndex() {
    if (index) return Promise.resolve(index);
    // Try sessionStorage cache
    try {
      var raw = sessionStorage.getItem(CONFIG.storageKey);
      if (raw) {
        var cached = JSON.parse(raw);
        if (
          cached && cached.ts &&
          (Date.now() - cached.ts) < CONFIG.storageTtlMs &&
          cached.payload && Array.isArray(cached.payload.items)
        ) {
          index = cached.payload;
          return Promise.resolve(index);
        }
      }
    } catch (e) { /* ignore */ }

    if (indexLoading) {
      return new Promise(function (resolve) {
        var t = setInterval(function () {
          if (index) {
            clearInterval(t);
            resolve(index);
          }
        }, 50);
      });
    }

    indexLoading = true;
    return fetch(CONFIG.indexUrl, { cache: 'force-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error('cmdk: index fetch failed ' + r.status);
        return r.json();
      })
      .then(function (payload) {
        if (!payload || !Array.isArray(payload.items)) {
          throw new Error('cmdk: malformed index payload');
        }
        index = payload;
        try {
          sessionStorage.setItem(CONFIG.storageKey, JSON.stringify({
            ts: Date.now(), payload: payload
          }));
        } catch (e) { /* ignore quota */ }
        return index;
      })
      .catch(function (err) {
        console.warn('[cmdk] failed to load index:', err);
        index = { items: [], schema_version: 0 };
        return index;
      })
      .finally(function () {
        indexLoading = false;
      });
  }

  // ---- Search logic ----
  function search(query) {
    if (!index || !index.items) return [];
    var q = (query || '').trim().toLowerCase();
    if (!q) {
      // Browse mode — top items grouped by kind
      return topByKind(index.items, CONFIG.maxResults);
    }
    var tokens = q.split(/\s+/).filter(Boolean);
    var hits = [];
    for (var i = 0; i < index.items.length; i++) {
      var item = index.items[i];
      var hay = (item.title + ' ' + (item.subtitle || '') + ' ' +
                 (item.aliases || []).join(' ')).toLowerCase();
      var score = 0;
      var allTokensFound = true;
      for (var j = 0; j < tokens.length; j++) {
        var tok = tokens[j];
        var idx = hay.indexOf(tok);
        if (idx < 0) {
          allTokensFound = false;
          break;
        }
        score += 100 - Math.min(idx, 80);
        // Boost: token-start match on title is best
        if (item.title.toLowerCase().indexOf(tok) === 0) score += 50;
      }
      if (allTokensFound) {
        // Apply tier penalty — lower tier = better
        score -= ((item.tier || 5) - 1) * 8;
        hits.push({ item: item, score: score });
      }
    }
    hits.sort(function (a, b) { return b.score - a.score; });
    return hits.slice(0, CONFIG.maxResults).map(function (h) { return h.item; });
  }

  function topByKind(items, maxTotal) {
    // Show up to N items per kind, alternating, capped at maxTotal
    var perKindCap = 4;
    var byKind = {};
    items.forEach(function (it) {
      var k = it.kind || 'other';
      if (!byKind[k]) byKind[k] = [];
      if (byKind[k].length < perKindCap) byKind[k].push(it);
    });
    var kinds = Object.keys(byKind);
    // Preferred order: profile, team, edition, mailbag, conference, player, methodology
    var orderPref = [
      'profile', 'team', 'edition', 'mailbag',
      'conference', 'player', 'methodology'
    ];
    kinds.sort(function (a, b) {
      var ai = orderPref.indexOf(a);
      var bi = orderPref.indexOf(b);
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
    });
    var out = [];
    kinds.forEach(function (k) {
      byKind[k].forEach(function (it) {
        if (out.length < maxTotal) out.push(it);
      });
    });
    return out;
  }

  // ---- Rendering ----
  function renderResults(items, isBrowse) {
    currentItems = items;
    selectedIdx = 0;
    if (!items.length) {
      resultsEl.innerHTML =
        '<div class="cmdk-empty">No matches.' +
        '<div class="cmdk-empty__hint">Try a partial team name or player.</div>' +
        '</div>';
      return;
    }
    // Group by kind for browse mode, flat list otherwise
    var html = '';
    if (isBrowse) {
      var groups = groupByKind(items);
      Object.keys(groups).forEach(function (kind) {
        html += '<div class="cmdk-group">';
        html += '<div class="cmdk-group__label">' + escapeHtml(kindLabel(kind)) + '</div>';
        groups[kind].forEach(function (item) {
          html += renderItem(item);
        });
        html += '</div>';
      });
    } else {
      html += '<div class="cmdk-group">';
      items.forEach(function (item) { html += renderItem(item); });
      html += '</div>';
    }
    resultsEl.innerHTML = html;
    // Wire item clicks
    var nodes = resultsEl.querySelectorAll('.cmdk-item');
    for (var i = 0; i < nodes.length; i++) {
      (function (idx) {
        nodes[idx].addEventListener('click', function (e) {
          e.preventDefault();
          selectedIdx = idx;
          followSelection();
        });
      })(i);
    }
    updateSelection();
  }

  function renderItem(item) {
    var subtitle = item.subtitle
      ? '<span class="cmdk-item__subtitle">' + escapeHtml(item.subtitle) + '</span>'
      : '';
    return (
      '<a class="cmdk-item" role="option" aria-selected="false" ' +
      'href="' + escapeAttr(item.url) + '" data-url="' + escapeAttr(item.url) + '">' +
      '<span class="cmdk-item__kind cmdk-item__kind--' + escapeAttr(item.kind) + '">' +
      escapeHtml(kindLabel(item.kind)) +
      '</span>' +
      '<span class="cmdk-item__title">' + escapeHtml(item.title) + '</span>' +
      subtitle +
      '</a>'
    );
  }

  function groupByKind(items) {
    var groups = {};
    items.forEach(function (it) {
      var k = it.kind || 'other';
      if (!groups[k]) groups[k] = [];
      groups[k].push(it);
    });
    return groups;
  }

  function kindLabel(kind) {
    return ({
      profile: 'Profile',
      team: 'Team',
      player: 'Player',
      edition: 'Edition',
      mailbag: 'Mailbag',
      conference: 'Conference',
      methodology: 'Methodology'
    })[kind] || kind;
  }

  function updateSelection() {
    var nodes = resultsEl.querySelectorAll('.cmdk-item');
    for (var i = 0; i < nodes.length; i++) {
      var sel = i === selectedIdx;
      nodes[i].setAttribute('aria-selected', sel ? 'true' : 'false');
      if (sel) {
        // Scroll into view if needed
        var node = nodes[i];
        var rect = node.getBoundingClientRect();
        var parentRect = resultsEl.getBoundingClientRect();
        if (rect.top < parentRect.top || rect.bottom > parentRect.bottom) {
          node.scrollIntoView({ block: 'nearest' });
        }
      }
    }
  }

  // ---- Event handlers ----
  function onInput(e) {
    var q = e.target.value;
    var hits = search(q);
    renderResults(hits, !q.trim());
  }

  function onKeyDown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (currentItems.length) {
        selectedIdx = (selectedIdx + 1) % currentItems.length;
        updateSelection();
      }
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (currentItems.length) {
        selectedIdx = (selectedIdx - 1 + currentItems.length) % currentItems.length;
        updateSelection();
      }
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      followSelection();
    }
  }

  function followSelection() {
    var item = currentItems[selectedIdx];
    if (!item) return;
    close();
    if (item.url && item.url[0] === '/') {
      window.location.href = item.url;
    } else if (item.url) {
      window.open(item.url, '_blank', 'noopener,noreferrer');
    }
  }

  // ---- Open/close ----
  function open() {
    build();
    openCount += 1;
    dialog.setAttribute('aria-hidden', 'false');
    backdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    input.value = '';
    resultsEl.innerHTML = '';
    loadIndex().then(function () {
      // Show top-by-kind on first open
      var initial = search('');
      renderResults(initial, true);
    });
    // Defer focus until next tick so the input is in the DOM
    setTimeout(function () { input && input.focus(); }, 0);
  }

  function close() {
    if (!dialog) return;
    dialog.setAttribute('aria-hidden', 'true');
    backdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  // ---- Global keybind ----
  document.addEventListener('keydown', function (e) {
    var isMac = /Mac|iPhone|iPad/.test(navigator.platform);
    var modPressed = isMac ? e.metaKey : e.ctrlKey;
    if (modPressed && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      open();
    }
  });

  // ---- Trigger button delegation ----
  document.addEventListener('click', function (e) {
    var target = e.target;
    if (!target) return;
    var trigger = target.closest && target.closest('[data-cmdk-trigger]');
    if (trigger) {
      e.preventDefault();
      open();
    }
  });

  // ---- Utilities ----
  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escapeAttr(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Expose for testing / programmatic use
  window.cmdk = {
    open: open,
    close: close,
    search: function (q) {
      if (!index) {
        return loadIndex().then(function () { return search(q); });
      }
      return Promise.resolve(search(q));
    },
    _state: function () {
      return {
        indexLoaded: !!index,
        itemCount: index ? index.items.length : 0,
        openCount: openCount
      };
    }
  };
})();
