/*! the-room.js — Alpine component for "The Room on [Player]" (S.4).
 *  Reads per-cohort buckets from the host element's data-cohorts JSON
 *  and the initial cohort id from data-initial. Hydrates from URL
 *  ?room=<id> when present (overrides data-initial).
 */
document.addEventListener('alpine:init', function () {
  if (!window.Alpine) return;
  window.Alpine.data('theRoom', function (cohortsJson, initial) {
    var cohorts = {};
    try { cohorts = JSON.parse(cohortsJson || '{}'); } catch (_e) {}
    var keys = Object.keys(cohorts);
    var urlChoice = (window.urlState && window.urlState.get('room')) || null;
    var startCohort = (urlChoice && cohorts[urlChoice]) ? urlChoice :
                      (initial && cohorts[initial]) ? initial :
                      keys[0];
    return {
      cohort: startCohort,
      cohorts: cohorts,
      get active() { return this.cohorts[this.cohort] || {}; },
      selectCohort: function (id) {
        if (!this.cohorts[id]) return;
        if (this.cohorts[id].score == null && this.cohorts[id].sample === 0) {
          /* Allow click but show awaiting body — handled via x-show on
           * `active.score === null` in the template. */
        }
        this.cohort = id;
        if (window.urlState) window.urlState.set('room', id);
      },
      init: function () {
        var self = this;
        // Re-sync cohort from URL on browser back/forward.
        window.addEventListener('popstate', function () {
          var fromUrl = window.urlState && window.urlState.get('room');
          if (fromUrl && self.cohorts[fromUrl] && self.cohort !== fromUrl) {
            self.cohort = fromUrl;
          }
        });
      },
      isActive: function (id) { return this.cohort === id; },
      dialClass: function () {
        var s = this.active.score;
        if (s == null) return 'the-room__dial-fill--neutral';
        if (s >= 70) return 'the-room__dial-fill--positive';
        if (s >= 40) return 'the-room__dial-fill--neutral';
        return 'the-room__dial-fill--negative';
      },
      scoreClass: function () {
        var s = this.active.score;
        if (s == null) return '';
        if (s >= 70) return 'the-room__score--positive';
        if (s < 40) return 'the-room__score--negative';
        return '';
      },
      archetypeFor: function () {
        var s = this.active.score;
        if (s == null) return 'Awaiting per-cohort signal';
        if (s >= 70) return 'Grounded Optimism';
        if (s >= 40) return 'Mixed Sentiment';
        return 'Skeptical';
      },
      formattedSample: function () {
        var n = (this.active.sample || 0);
        try { return n.toLocaleString() + ' mentions'; } catch (_e) { return n + ' mentions'; }
      },
      confidenceBand: function () {
        var n = (this.active.sample || 0);
        if (n >= 40) return 'high';
        if (n >= 12) return 'medium';
        if (n >= 4) return 'low';
        return 'below-floor';
      },
      confidenceLabelText: function () {
        var explicit = this.active && this.active.confidence;
        if (explicit) return String(explicit).toUpperCase();
        var band = this.confidenceBand();
        return band === 'below-floor' ? 'BELOW FLOOR' :
               band === 'medium'      ? 'MEDIUM' :
               band === 'low'         ? 'LOW' :
                                        'HIGH';
      },
      trajectoryPoints: function () {
        var pts = (this.active.trajectory || []);
        if (!pts.length) return '';
        return pts.map(function (val, idx) {
          var x = (idx / Math.max(1, pts.length - 1)) * 400;
          var y = 60 - (val / 100) * 60;
          return x + ',' + y;
        }).join(' ');
      },
      trajectoryEndY: function () {
        var pts = (this.active.trajectory || []);
        if (!pts.length) return 30;
        return 60 - (pts[pts.length - 1] / 100) * 60;
      },
    };
  });
});
