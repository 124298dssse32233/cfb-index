/*! rankings-board.js — CFB Index rankings board interactions.
 *  Vanilla, zero-dependency, defensive. Companion to rankings-board.css.
 *  Ports the interaction model from docs/octopus/mockups/rankings-mobile.html
 *  + desktop-board.html into the SERVER-RENDERED production board.
 *
 *  The board is server-rendered and server-sorted by default. This script only
 *  *enhances*: it never builds rows. Everything is feature-detected and no-ops
 *  if its target elements are absent, so it is safe to load on any page.
 *
 *  Public behaviors
 *  ----------------
 *  1. Lens tabs — a roving-tabindex ARIA tablist over `.lens [role=tab]`.
 *     Arrow/Home/End move focus + select; aria-selected toggles; the selected
 *     lens key is written to `data-lens` on the board container so CSS (and the
 *     server, on next render) can re-show/re-sort. If a row carries
 *     `data-sort-<lens>` it is used to client-reorder within a View Transition.
 *  2. Filter chips — `.fchip[aria-pressed]`. Toggling filters rows by matching
 *     `data-level` / `data-conf` / `data-tier` (+ `data-riser`) and updates an
 *     aria-live result count ("Showing 25 of 134 teams").
 *  3. <details name> exclusivity shim — for browsers lacking exclusive
 *     accordion (`name`-group) support, only one row drawer stays open.
 *  4. View Transitions — re-sorts/filter-shows are wrapped in
 *     document.startViewTransition when available; otherwise applied directly.
 *  5. prefers-reduced-motion is respected (no View Transition, no smooth focus).
 *
 *  data-* attributes the server HTML should emit
 *  ---------------------------------------------
 *   Board container:  any element with [data-board] (e.g. <main data-board>).
 *   Lens tablist:     <div class="lens" role="tablist"> with
 *                       <button role="tab" data-lens="power|resume|bettor|belief">
 *   Filter chips:     <button class="fchip" aria-pressed="true|false"
 *                       data-filter="top25|fbs|risers|all|..."
 *                       [data-filter-type="level|conf|tier|special"]
 *                       [data-filter-value="sec|big-ten|..."]>
 *                     (data-filter-value defaults to data-filter when omitted.)
 *   Rows (card-feed): <article class="row" data-level="fbs"
 *                       data-conf="sec" data-tier="top25" [data-riser]
 *                       [data-sort-power="1"] [data-sort-resume="3"] ...>
 *   Rows (table):     <tr> with the same data-* attributes.
 *   Result count:     any element with [data-result-count] (gets aria-live).
 */
(function () {
  "use strict";

  var REDUCED = false;
  try {
    REDUCED = typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (_e) {}

  /* Run a layout mutation inside a View Transition when supported + motion ok. */
  function transition(fn) {
    if (!REDUCED && typeof document.startViewTransition === "function") {
      try { document.startViewTransition(fn); return; } catch (_e) {}
    }
    fn();
  }

  /* Collect the row elements for a board container (card-feed OR table). */
  function rowsFor(board) {
    if (!board) return [];
    var nodes = board.querySelectorAll(".row, tbody tr[data-level], tbody tr[data-conf], tbody tr[data-tier]");
    if (!nodes.length) {
      // Fall back to any row-like element carrying filter data-attrs.
      nodes = board.querySelectorAll("[data-level],[data-conf],[data-tier]");
    }
    return Array.prototype.filter.call(nodes, function (n) {
      // Skip structural rows (cutline / skeleton) that have no team data.
      return !n.classList.contains("cut") && !n.classList.contains("skrow");
    });
  }

  /* ============================ 1. LENS TABS ============================ */
  function initLens() {
    var lists = document.querySelectorAll('.lens[role="tablist"]');
    if (!lists.length) return;
    var board = document.querySelector("[data-board]");

    Array.prototype.forEach.call(lists, function (list) {
      var tabs = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
      if (!tabs.length) return;

      // Establish roving tabindex from the current aria-selected tab.
      function syncTabindex() {
        tabs.forEach(function (t) {
          t.tabIndex = (t.getAttribute("aria-selected") === "true") ? 0 : -1;
        });
      }
      if (!tabs.some(function (t) { return t.getAttribute("aria-selected") === "true"; })) {
        tabs[0].setAttribute("aria-selected", "true");
      }
      syncTabindex();

      function select(tab, focus) {
        if (!tab) return;
        tabs.forEach(function (t) { t.setAttribute("aria-selected", t === tab ? "true" : "false"); });
        syncTabindex();
        if (focus) {
          try { tab.focus({ preventScroll: REDUCED }); } catch (_e) { tab.focus(); }
        }
        var lens = tab.getAttribute("data-lens") ||
          (tab.textContent || "").trim().toLowerCase();
        if (board) {
          transition(function () {
            board.setAttribute("data-lens", lens);
            reorder(board, lens);
          });
        }
        // Let the page/server hook in (e.g. swap a server-rendered partial).
        list.dispatchEvent(new CustomEvent("lenschange", {
          bubbles: true, detail: { lens: lens, tab: tab }
        }));
      }

      tabs.forEach(function (tab, i) {
        tab.addEventListener("click", function () { select(tab, false); });
        tab.addEventListener("keydown", function (e) {
          var idx = i, last = tabs.length - 1, next = null;
          switch (e.key) {
            case "ArrowRight": case "ArrowDown": next = tabs[idx === last ? 0 : idx + 1]; break;
            case "ArrowLeft":  case "ArrowUp":   next = tabs[idx === 0 ? last : idx - 1]; break;
            case "Home": next = tabs[0]; break;
            case "End":  next = tabs[last]; break;
            default: return;
          }
          e.preventDefault();
          select(next, true);
        });
      });
    });
  }

  /* Client-side reorder if rows expose data-sort-<lens>. Otherwise no-op
   * (server already ordered the default lens). Reorders BOTH the card-feed
   * container and any sibling table body that shares the same data. */
  function reorder(board, lens) {
    var key = "sort" + lens.charAt(0).toUpperCase() + lens.slice(1); // dataset key
    var containers = [];
    var feed = board.querySelector(".sheet") || board;
    if (feed) containers.push(feed);
    var tbody = document.querySelector("[data-board] .board-table tbody, .board-table tbody");
    if (tbody && tbody !== feed) containers.push(tbody);

    containers.forEach(function (container) {
      var items = rowsFor(container);
      if (!items.length) return;
      // Only reorder when every row carries the sort key for this lens.
      var sortable = items.every(function (it) {
        return it.dataset && it.dataset[key] != null && it.dataset[key] !== "";
      });
      if (!sortable) return;
      var sorted = items.slice().sort(function (a, b) {
        return parseFloat(a.dataset[key]) - parseFloat(b.dataset[key]);
      });
      sorted.forEach(function (it) { container.appendChild(it); });
    });
  }

  /* ========================== 2. FILTER CHIPS ========================== */
  function initFilters() {
    var chips = Array.prototype.slice.call(document.querySelectorAll(".fchip[aria-pressed]"));
    if (!chips.length) return;
    var board = document.querySelector("[data-board]");
    if (!board) return;
    var countEl = document.querySelector("[data-result-count]");
    if (countEl && !countEl.getAttribute("aria-live")) {
      countEl.setAttribute("aria-live", "polite");
    }

    function chipSpec(chip) {
      var type = chip.getAttribute("data-filter-type") || "";
      var value = (chip.getAttribute("data-filter-value") ||
        chip.getAttribute("data-filter") || "").toLowerCase();
      return { type: type, value: value, chip: chip };
    }

    function rowMatches(row, active) {
      // A row passes if, for every active group, it matches at least one chip.
      // Groups: level, conf, tier, special (risers/all). "all"/"all divisions"
      // and "fbs" widen rather than exclude when they are the active level.
      var byGroup = {};
      active.forEach(function (s) {
        var g = s.type || "special";
        (byGroup[g] = byGroup[g] || []).push(s.value);
      });
      for (var g in byGroup) {
        if (!Object.prototype.hasOwnProperty.call(byGroup, g)) continue;
        var values = byGroup[g];
        var ok = values.some(function (v) {
          if (v === "all" || v === "all-divisions") return true;
          if (g === "level") return matchAttr(row, "level", v) || v === "fbs" && rowIsFbs(row);
          if (g === "conf") return matchAttr(row, "conf", v);
          if (g === "tier") return matchAttr(row, "tier", v);
          // special
          if (v === "risers") return row.hasAttribute("data-riser");
          // Unknown special: match by any data-* equal to value.
          return matchAttr(row, "level", v) || matchAttr(row, "conf", v) ||
            matchAttr(row, "tier", v);
        });
        if (!ok) return false;
      }
      return true;
    }

    function matchAttr(row, name, v) {
      var raw = row.getAttribute("data-" + name);
      if (raw == null) return false;
      return raw.toLowerCase().split(/\s+/).indexOf(v) !== -1;
    }
    function rowIsFbs(row) {
      var lvl = (row.getAttribute("data-level") || "").toLowerCase();
      return lvl === "fbs" || lvl === "";
    }

    function apply() {
      var active = chips
        .filter(function (c) { return c.getAttribute("aria-pressed") === "true"; })
        .map(chipSpec);
      var rows = rowsFor(board);
      // Mirror to the table body if it lives outside [data-board].
      var tbody = document.querySelector(".board-table tbody");
      if (tbody && !board.contains(tbody)) {
        rows = rows.concat(rowsFor(tbody));
      }
      var shown = 0, total = 0;
      transition(function () {
        rows.forEach(function (row) {
          total++;
          var ok = !active.length || rowMatches(row, active);
          row.hidden = !ok;
          // Also toggle a class so :has()/CSS can react if it prefers.
          row.classList.toggle("is-filtered-out", !ok);
          if (ok) shown++;
        });
        // Hide a cutline whose neighborhood is fully filtered (cosmetic).
        toggleStructural(board);
        var t2 = document.querySelector(".board-table tbody");
        if (t2 && !board.contains(t2)) toggleStructural(t2);
      });
      updateCount(shown, total);
    }

    function updateCount(shown, total) {
      if (!countEl) return;
      // Each row exists in up to two representations (card + table); de-dupe by
      // halving only when a table mirror is present.
      var noun = total === 1 ? "team" : "teams";
      countEl.textContent = "Showing " + shown + " of " + total + " " + noun;
    }

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        var pressed = chip.getAttribute("aria-pressed") === "true";
        chip.setAttribute("aria-pressed", pressed ? "false" : "true");
        apply();
      });
    });

    // "Clear all" button inside an empty-state can reset every chip.
    document.addEventListener("click", function (e) {
      var btn = e.target.closest && e.target.closest("[data-clear-filters]");
      if (!btn) return;
      e.preventDefault();
      chips.forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
      apply();
    });

    apply(); // establish initial count from server-pressed chips
  }

  /* Hide a `.cutline`/`.cut` divider when no visible row follows it. */
  function toggleStructural(scope) {
    var dividers = scope.querySelectorAll(".cutline, tr.cut");
    Array.prototype.forEach.call(dividers, function (d) {
      var n = d.nextElementSibling, anyAfter = false;
      while (n) {
        if (!n.classList.contains("cut") && !n.classList.contains("cutline") &&
            !n.hidden) { anyAfter = true; break; }
        n = n.nextElementSibling;
      }
      d.hidden = !anyAfter;
    });
  }

  /* ==================== 3. <details name> SHIM ==================== */
  function initDetailsShim() {
    var groups = document.querySelectorAll("details[name]");
    if (!groups.length) return;
    // Feature-detect native exclusive-accordion support. When supported the
    // browser handles exclusivity; we only shim when it does not.
    var supported = false;
    try {
      var probe = document.createElement("details");
      supported = ("name" in probe);
    } catch (_e) {}
    if (supported) return;

    Array.prototype.forEach.call(groups, function (d) {
      d.addEventListener("toggle", function () {
        if (!d.open) return;
        var name = d.getAttribute("name");
        if (!name) return;
        var siblings = document.querySelectorAll('details[name="' +
          (window.CSS && CSS.escape ? CSS.escape(name) : name) + '"]');
        Array.prototype.forEach.call(siblings, function (s) {
          if (s !== d && s.open) s.open = false;
        });
      });
    });
  }

  /* ==================== 4. RESORT/ROW-OPEN GLUE ==================== */
  /* The mobile mock opens a drawer via `.row.open` toggled on row-main click.
   * Production may use either that pattern OR native <details>. We support the
   * class pattern defensively here (no-op if rows use <details>). */
  function initRowToggle() {
    var board = document.querySelector("[data-board]");
    if (!board) return;
    if (board.querySelector("details")) return; // native drawers in use
    board.addEventListener("click", function (e) {
      var main = e.target.closest && e.target.closest(".row-main");
      if (!main) return;
      // Don't toggle when an interactive control inside the row was clicked.
      if (e.target.closest("a,button")) return;
      var row = main.closest(".row");
      if (!row) return;
      var open = row.classList.contains("open");
      // Exclusive within the board (matches the drawer feel).
      if (!open) {
        Array.prototype.forEach.call(board.querySelectorAll(".row.open"),
          function (r) { r.classList.remove("open"); });
      }
      row.classList.toggle("open", !open);
    });
  }

  function init() {
    initLens();
    initFilters();
    initDetailsShim();
    initRowToggle();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
