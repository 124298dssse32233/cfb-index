/*! url-state.js — small helper for ?param=value URL sync.
 *  Frontend Migration S.4. Uses pushState (not replaceState) so the
 *  browser back/forward buttons restore prior cohort selections.
 */
(function () {
  if (window.urlState) return;
  window.urlState = {
    get: function (key) {
      try {
        return new URLSearchParams(window.location.search).get(key);
      } catch (_e) {
        return null;
      }
    },
    set: function (key, value) {
      try {
        var params = new URLSearchParams(window.location.search);
        if (value == null || value === '') {
          params.delete(key);
        } else {
          params.set(key, String(value));
        }
        var qs = params.toString();
        var url = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
        window.history.pushState({}, '', url);
      } catch (_e) {
        /* no-op — URL sync is non-critical */
      }
    },
  };
})();
