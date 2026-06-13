"""Player Savant Card — visual 12-percentile-bar block.

`PLAYER_PAGE_WORLD_CLASS_BRIEF.md §4.5` ("Advanced Savant card"):
    "Vertical stack of ~12 percentile bars, red→grey→blue OKLCH gradient
     … ordered best → most interesting → concerns, with a one-line
     narrative header. Cohort toggle vs. FBS / vs. Power-4 /
     vs. Heisman-probable / vs. his own career."

§3 #1 (Percentile Bar primitive): "Savant-style gradient bar, value
pinned, peer label beside. Inverted variant for metrics where
low-is-good (pressure-to-sack, turnover-worthy plays)."

The 12 canonical QB metrics from §4.5:
    1. EPA / dropback
    2. CPOE
    3. Success rate
    4. Explosive-play rate (20+)
    5. aDOT
    6. Deep-ball accuracy (20+ air yards)
    7. Pressure-to-sack rate (inverted)
    8. 3rd-down EPA
    9. Red-zone TD rate
    10. Play-action EPA split
    11. Scramble EPA
    12. Turnover-worthy play rate (inverted)

The existing `_render_v5_savant_card` in reporting.py emits the same
data as TEXT placement labels ("Elite (≥p90)"). This module renders
the same data as VISUAL gradient bars per brief intent — they
coexist; this one ships above the legacy text version (audit Sprint
C piece).

Data contract — `savant_payload` dict produced by
`_assemble_player_page_data` line ~9881:
    {
      "metrics": [
        {
          "metric": str,
          "value": float,
          "cohorts": {
            "p4": {"p10":, "p25":, "p50":, "p75":, "p90":, "n":},
            "g5": {...}, "all": {...},
          }
        },
        ...
      ]
    }

Public API:
    render_player_savant_card(savant, season=None) -> str
    PLAYER_SAVANT_CSS_BLOCK                          -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


# Brief §4.5 — 12 canonical QB metrics, in priority order. Data sources
# may name these differently; loose-match patterns below let any
# reasonably-named metric snap to its slot.
CANONICAL_QB_METRICS: tuple[tuple[str, str, bool], ...] = (
    # (display_name, match_patterns_pipe, inverted=lower-is-better)
    ("EPA / dropback",               "epa_per_dropback|epa_dropback|epa_pass",         False),
    ("CPOE",                         "cpoe|completion_above|completion_pct_over",      False),
    ("Success rate",                 "success_rate|sr_pass",                            False),
    ("Explosive rate (20+)",         "explosive|explosive_rate|20yd",                   False),
    ("aDOT",                         "adot|avg_depth|avg_target",                       False),
    ("Deep-ball accuracy",           "deep_ball|deep_accuracy|deep_pct|20plus_air",     False),
    ("Pressure-to-sack",             "pressure_to_sack|sack_under_pressure|ptp",        True),
    ("3rd-down EPA",                 "third_down_epa|3rd_down_epa|epa_third",           False),
    ("Red-zone TD rate",             "red_zone_td|rz_td|rz_rate",                       False),
    ("Play-action EPA",              "play_action_epa|pa_epa",                          False),
    ("Scramble EPA",                 "scramble_epa|scr_epa",                            False),
    ("Turnover-worthy play rate",    "turnover_worthy|twp|int_worthy",                  True),
)


PLAYER_SAVANT_CSS_BLOCK = """
/* Player Savant Card — Sprint C (PLAYER_PAGE_WORLD_CLASS_BRIEF §4.5)
 *
 * Visual gradient bars in red→grey→blue OKLCH per brief §3 #1.
 * Each bar = one metric. Bar fill % = percentile placement; bar color
 * = pct-low / pct-mid / pct-high tokens; pin marker = exact value.
 *
 * Reads --team-accent from enclosing .team-shell for the cohort
 * toggle button.
 */

.player-savant {
  --psv-track:    rgba(255, 255, 255, 0.06);
  --psv-stroke:   rgba(255, 255, 255, 0.10);
  --psv-bar-low:  var(--pct-low,  #c04a4a);
  --psv-bar-mid:  var(--pct-mid,  #888780);
  --psv-bar-high: var(--pct-high, #3570b5);
  --psv-text:     var(--fg-primary, #1a1a1a);
  --psv-meta:     var(--fg-muted,   #6f6f6f);

  display: grid;
  gap: clamp(16px, 1.8vw, 22px);
  padding: clamp(18px, 2.2vw, 28px) clamp(20px, 2.4vw, 32px);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--psv-stroke);
  border-radius: 16px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}

.player-savant__header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.player-savant__eyebrow {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--psv-meta);
  margin: 0;
}
.player-savant__title {
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: clamp(24px, 2vw + 10px, 32px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--psv-text);
  margin: 0;
}
.player-savant__narrative {
  font-family: 'Source Serif Pro', Georgia, serif;
  font-size: clamp(14px, 0.3vw + 13px, 16px);
  line-height: 1.5;
  color: var(--fg-secondary, var(--psv-text));
  margin: 0;
  max-width: 70ch;
}

/* === Cohort toggle pills === */
.player-savant__cohort {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--psv-stroke);
  border-radius: 8px;
  align-self: start;
}
.player-savant__cohort-pill {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 6px 10px;
  background: transparent;
  border: 0;
  color: var(--psv-meta);
  cursor: default;
  border-radius: 6px;
  min-height: 30px;
}
.player-savant__cohort-pill[data-active="true"] {
  background: var(--team-accent, var(--psv-bar-high));
  color: #ffffff;
}

/* === Bars === */

.player-savant__bars {
  display: grid;
  gap: 10px;
}

.player-savant__row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) 56px minmax(0, 2fr) 64px;
  gap: 12px;
  align-items: center;
  padding: 8px 0;
  border-top: 1px solid var(--psv-stroke);
}
.player-savant__row:first-child { border-top: none; }

.player-savant__metric {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: var(--psv-text);
}

.player-savant__value {
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: 20px;
  font-weight: 400;
  text-align: right;
  color: var(--psv-text);
  line-height: 1;
}

.player-savant__bar {
  position: relative;
  height: 14px;
  background: var(--psv-track);
  border-radius: 8px;
  overflow: hidden;
}
.player-savant__bar-fill {
  position: absolute;
  inset: 0;
  border-radius: 8px;
  background: linear-gradient(
    90deg,
    var(--psv-bar-low) 0%,
    var(--psv-bar-mid) 50%,
    var(--psv-bar-high) 100%
  );
  clip-path: inset(0 calc(100% - var(--pct, 50%)) 0 0 round 8px);
}
.player-savant__bar--inverted .player-savant__bar-fill {
  background: linear-gradient(
    90deg,
    var(--psv-bar-high) 0%,
    var(--psv-bar-mid) 50%,
    var(--psv-bar-low) 100%
  );
}
.player-savant__bar-pin {
  position: absolute;
  top: -3px;
  bottom: -3px;
  left: var(--pct, 50%);
  width: 3px;
  background: var(--psv-text);
  border-radius: 2px;
  transform: translateX(-50%);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.6);
}

.player-savant__pct {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--psv-meta);
  text-align: right;
  white-space: nowrap;
}
.player-savant__pct[data-band="high"]  { color: var(--psv-bar-high); }
.player-savant__pct[data-band="mid"]   { color: var(--psv-bar-mid); }
.player-savant__pct[data-band="low"]   { color: var(--psv-bar-low); }

.player-savant__row--awaiting .player-savant__metric { color: var(--psv-meta); }
.player-savant__row--awaiting .player-savant__value,
.player-savant__row--awaiting .player-savant__bar-fill,
.player-savant__row--awaiting .player-savant__bar-pin {
  opacity: 0.45;
}
.player-savant__row--awaiting .player-savant__pct {
  font-style: italic;
}

@media (max-width: 600px) {
  .player-savant__row {
    grid-template-columns: minmax(0, 1fr) 48px;
    grid-template-areas:
      "metric value"
      "bar    bar"
      "pct    pct";
    gap: 4px 8px;
  }
  .player-savant__metric { grid-area: metric; }
  .player-savant__value  { grid-area: value; }
  .player-savant__bar    { grid-area: bar; margin: 6px 0 0; }
  .player-savant__pct    { grid-area: pct; text-align: left; }
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match_canonical(metric_name: str) -> tuple[str, bool] | None:
    """Match a raw metric name to a canonical brief slot.
    Returns (display_name, inverted) or None if no match.
    """
    if not metric_name:
        return None
    norm = metric_name.lower().replace("-", "_").replace(" ", "_")
    for display, patterns, inverted in CANONICAL_QB_METRICS:
        for p in patterns.split("|"):
            if p and p in norm:
                return (display, inverted)
    return None


def _percentile_from_band(value: float, band: dict[str, Any]) -> tuple[int | None, str]:
    """Compute approximate percentile + band label from a percentile band.
    Returns (pct_int, band_label) where band_label is "high"/"mid"/"low"/"unknown".
    Linear-interpolates between known cut points.
    """
    if not band or value is None:
        return (None, "unknown")
    try:
        v = float(value)
    except (TypeError, ValueError):
        return (None, "unknown")
    pts: list[tuple[int, float]] = []
    for pct in (10, 25, 50, 75, 90):
        bv = band.get(f"p{pct}")
        if bv is not None:
            try:
                pts.append((pct, float(bv)))
            except (TypeError, ValueError):
                pass
    if len(pts) < 2:
        return (None, "unknown")
    # Off ends
    if v <= pts[0][1]:
        return (max(1, pts[0][0] - 2), "low")
    if v >= pts[-1][1]:
        return (min(99, pts[-1][0] + 2), "high")
    # Linear interp between cuts
    for i in range(len(pts) - 1):
        p_lo, v_lo = pts[i]
        p_hi, v_hi = pts[i + 1]
        if v_lo <= v <= v_hi:
            if v_hi == v_lo:
                p = p_lo
            else:
                frac = (v - v_lo) / (v_hi - v_lo)
                p = int(round(p_lo + frac * (p_hi - p_lo)))
            band_label = (
                "high" if p >= 70 else
                "mid" if p >= 40 else
                "low"
            )
            return (p, band_label)
    return (None, "unknown")


def _format_value(v: Any) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(f) < 1:
        return f"{f:.3f}"
    if abs(f) < 10:
        return f"{f:.2f}"
    return f"{f:.1f}"


def _narrative_from_metrics(matched: list[tuple[str, int]], position: str = "QB") -> str:
    """Single-line plain-English narrative from the matched metrics."""
    if not matched:
        return (
            "Advanced opponent-adjusted percentile bars are coming soon for this player."
        )
    high = [name for name, pct in matched if pct >= 70]
    low = [name for name, pct in matched if pct <= 30]
    bits: list[str] = []
    if high:
        bits.append("Elite: " + ", ".join(high[:3]))
    if low:
        bits.append("Concerns: " + ", ".join(low[:2]))
    if not bits:
        bits.append("Reads as a mid-tier profile across the board.")
    return " · ".join(bits) + "."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_player_savant_card(
    savant: dict[str, Any] | None,
    *,
    season: int | str | None = None,
    position: str = "QB",
    cohort: str = "p4",
) -> str:
    """Render the player Savant card with visual percentile bars."""
    payload = savant or {}
    raw_metrics = payload.get("metrics") or []

    # Index raw metrics by canonical slot (first match wins; raw order preserved
    # otherwise for non-canonical metrics we still want to render).
    by_canonical: dict[str, tuple[dict[str, Any], bool]] = {}
    extra_metrics: list[dict[str, Any]] = []
    matched_for_narrative: list[tuple[str, int]] = []
    for m in raw_metrics:
        name = str(m.get("metric") or "")
        match = _match_canonical(name)
        if match is not None:
            canonical_display, inverted = match
            if canonical_display not in by_canonical:
                by_canonical[canonical_display] = (m, inverted)
        else:
            extra_metrics.append(m)

    # Build 12 brief-mandated rows in fixed order
    rows_html: list[str] = []
    for display, _patterns, inverted in CANONICAL_QB_METRICS:
        entry = by_canonical.get(display)
        if entry is None:
            # Awaiting placeholder — brief §8.8 honest empty-state
            rows_html.append(
                '<div class="player-savant__row player-savant__row--awaiting" '
                f'aria-label="{escape(display)} — awaiting data">'
                f'<span class="player-savant__metric">{escape(display)}</span>'
                '<span class="player-savant__value">—</span>'
                '<div class="player-savant__bar">'
                '<span class="player-savant__bar-fill" style="--pct: 0%;"></span>'
                '</div>'
                '<span class="player-savant__pct">awaiting</span>'
                '</div>'
            )
            continue
        m, inv = entry
        value = m.get("value")
        band = (m.get("cohorts") or {}).get(cohort) or {}
        pct, band_label = _percentile_from_band(value, band)
        if pct is None:
            pct_display = "n/a"
            pct_attr = "unknown"
            fill_pct = 0
        else:
            # For inverted metrics, the visual fill should reflect "goodness"
            # not raw position — so a low pressure-to-sack rate (good) fills
            # from the high (blue) end.
            display_pct = (100 - pct) if inv else pct
            fill_pct = display_pct
            pct_display = f"{display_pct}th pct"
            pct_attr = (
                "high" if display_pct >= 70 else
                "mid" if display_pct >= 40 else
                "low"
            )
            matched_for_narrative.append((display, display_pct))
        inv_cls = " player-savant__bar--inverted" if inv else ""
        value_str = _format_value(value)
        rows_html.append(
            '<div class="player-savant__row">'
            f'<span class="player-savant__metric">{escape(display)}</span>'
            f'<span class="player-savant__value">{escape(value_str)}</span>'
            f'<div class="player-savant__bar{inv_cls}">'
            f'<span class="player-savant__bar-fill" style="--pct: {fill_pct}%;"></span>'
            f'<span class="player-savant__bar-pin" style="--pct: {fill_pct}%;"></span>'
            '</div>'
            f'<span class="player-savant__pct" data-band="{pct_attr}">{pct_display}</span>'
            '</div>'
        )

    narrative = _narrative_from_metrics(matched_for_narrative, position=position)
    season_text = f"{position} · {escape(str(season))}" if season else position

    # Cohort pills (decorative — Alpine interactivity is in the legacy v5 card)
    cohort_pills_html = "".join(
        f'<span class="player-savant__cohort-pill" data-active="{("true" if c == cohort else "false")}">{label}</span>'
        for c, label in (("p4", "P4"), ("g5", "G5"), ("all", "All FBS"))
    )

    return f"""
<section class="player-savant" aria-labelledby="player-savant-h" data-module="player-savant">
  <div class="player-savant__header">
    <p class="player-savant__eyebrow">Advanced Savant · {escape(season_text)}</p>
    <h2 id="player-savant-h" class="player-savant__title">Percentile Card</h2>
    <p class="player-savant__narrative">{escape(narrative)}</p>
    <div class="player-savant__cohort" role="group" aria-label="Peer cohort">
      {cohort_pills_html}
    </div>
  </div>
  <div class="player-savant__bars" role="list" aria-label="12 advanced metrics with percentile bars">
    {''.join(rows_html)}
  </div>
</section>
"""


__all__ = [
    "render_player_savant_card",
    "PLAYER_SAVANT_CSS_BLOCK",
    "CANONICAL_QB_METRICS",
]
