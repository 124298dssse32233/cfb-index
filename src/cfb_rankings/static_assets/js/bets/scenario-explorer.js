/*! scenario-explorer.js — Scenario Explorer Alpine component
 *  (Signature Bets S3.3 / §4 Bet #12).
 *
 *  Reads the payload embedded via data-scenario-payload on the host
 *  <article>. Two sliders (remaining games, per-game projection)
 *  recompute the projected season value and the resulting rank in
 *  the cohort on every input.
 */
document.addEventListener('alpine:init', function () {
  if (!window.Alpine) return;
  window.Alpine.data('scenarioExplorer', function (payloadJson) {
    var payload = {};
    try { payload = JSON.parse(payloadJson || '{}'); } catch (_e) {}
    return {
      payload: payload,
      remaining: payload.default_remaining_games || 4,
      perGame: payload.default_per_game_projection || 0,
      get projectedTotal() {
        return Math.max(0, (this.payload.current_value || 0) +
          Number(this.remaining) * Number(this.perGame));
      },
      get projectedRank() {
        var values = this.payload.cohort_values_sorted || [];
        var proj = this.projectedTotal;
        // Descending sort → first index where value <= proj is the rank.
        for (var i = 0; i < values.length; i++) {
          if (values[i] <= proj) return i + 1;
        }
        return values.length + 1;
      },
      get rankShift() {
        return (this.payload.current_rank || 0) - this.projectedRank;
      },
      formattedValue: function (val) {
        var unit = this.payload.unit || '';
        if (unit === 'pct' || unit === 'rate') return (val || 0).toFixed(1) + '%';
        if (unit === 'EPA') return (val > 0 ? '+' : '') + (val || 0).toFixed(3);
        if (unit === 'yds') return Math.round(val || 0).toLocaleString();
        return String(val);
      },
    };
  });
});
