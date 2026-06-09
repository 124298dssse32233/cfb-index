"""Fanbase Health Index — Brief §11.1.

Composite 0-100 score that measures fanbase *vitality* — not happiness.
A fanbase can be unhappy and healthy (still engaged, still arguing) or
happy and unhealthy (apathetic, not showing up).

Brief verbatim (§11.1):

    "Components:
       - Volume trend  — conversation volume growing or shrinking YoY
       - Geographic reach — local market vs. spreading nationally
       - Cross-cohort engagement — multiple cohorts active, or just one
       - Ticket demand index — SeatGeek get-in price trend vs. baseline
       - Rival engagement — rival fanbases paying attention is a respect signal

     Rendered as a single composite needle gauge (0-100), labeled in
     four bands: Declining (0-25) / Stable (26-50) / Growing (51-75) /
     Surging (76-100). With a year-over-year delta chip."

Implementation note: full 5-signal composite needs sources we don't all
expose to the team-page renderer today (SeatGeek, Reddit-geo, Wikipedia
DMA). The renderer here uses whichever sub-signals are present and is
honest about confidence in the eyebrow.

Sub-signals supported today:
  + record_trend   from snapshot.wins/losses + YoY arc_rows
  + mood_volume    from mood.effective_n
  + cohort_engage  from divergence (proxy for cross-cohort presence)

Public API:
    render_fanbase_health(profile, snapshot, mood, divergence, arc_rows) -> str
    FANBASE_HEALTH_CSS                                                    -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


FANBASE_HEALTH_CSS = """
/* Fanbase Health Index — Brief §11.1 */
.fanbase-health {
  display: grid;
  gap: clamp(10px, 1.2vw, 14px);
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.fanbase-health__header {
  display: grid;
  gap: 4px;
}
.fanbase-health__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.fanbase-health__band {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(22px, 1.8vw + 10px, 30px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.fanbase-health__band--declining { color: #c95151; }
.fanbase-health__band--stable    { color: var(--accent-primary, #c9a24a); }
.fanbase-health__band--growing   { color: #2c8f5a; }
.fanbase-health__band--surging   { color: #c98c1a; }

.fanbase-health__gauge {
  position: relative;
  height: 14px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 999px;
  overflow: hidden;
}
.fanbase-health__gauge-fill {
  position: absolute;
  inset: 0;
  width: calc(var(--health-score, 50) * 1%);
  background: linear-gradient(90deg, #c95151 0%, var(--accent-primary, #c9a24a) 50%, #2c8f5a 100%);
  border-radius: 999px;
  transition: width 0.4s ease;
}
.fanbase-health__gauge-needle {
  position: absolute;
  top: -3px;
  bottom: -3px;
  left: calc(var(--health-score, 50) * 1%);
  width: 3px;
  background: var(--fg-primary);
  border-radius: 2px;
  transform: translateX(-50%);
}

.fanbase-health__legend {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 2px;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.fanbase-health__legend span { text-align: center; }
.fanbase-health__legend span:nth-child(1) { text-align: left; }
.fanbase-health__legend span:nth-child(4) { text-align: right; }

.fanbase-health__components {
  display: grid;
  gap: 4px;
  padding-top: 4px;
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.08));
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 12px;
  font-style: italic;
  color: var(--fg-secondary);
}
.fanbase-health__components-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: baseline;
  gap: 8px;
}
.fanbase-health__components-row strong {
  font-style: normal;
  color: var(--fg-primary);
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.fanbase-health__components-row em {
  font-style: normal;
  color: var(--accent-primary, #c9a24a);
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  font-weight: 600;
}
"""


# ---------------------------------------------------------------------------
# Score components
# ---------------------------------------------------------------------------

def _record_health(snapshot: TeamSnapshot, arc_rows: list[dict[str, Any]] | None) -> tuple[float | None, str]:
    """Score from current record + YoY delta. Returns (score 0-100, label)."""
    w = int(snapshot.wins or 0)
    l = int(snapshot.losses or 0)
    if w + l == 0:
        # Use last arc row's win pct as fallback in offseason.
        if arc_rows:
            sorted_rows = sorted(arc_rows, key=lambda r: int(r.get("season_year") or 0))
            if sorted_rows:
                last = sorted_rows[-1]
                lw = int(last.get("wins") or 0)
                ll = int(last.get("losses") or 0)
                if lw + ll > 0:
                    pct = lw / (lw + ll)
                    return (40 + pct * 50, f"Last season {lw}-{ll}")
        return (None, "No record yet")
    pct = w / (w + l)
    # Map 0.0 → 30, 0.5 → 55, 1.0 → 85; YoY delta nudges ±10.
    base = 30 + pct * 55
    nudge = 0.0
    if arc_rows and len(arc_rows) >= 2:
        sr = sorted(arc_rows, key=lambda r: int(r.get("season_year") or 0))
        prior = sr[-2]
        prior_w = int(prior.get("wins") or 0)
        prior_l = int(prior.get("losses") or 0)
        if prior_w + prior_l > 0:
            prior_pct = prior_w / (prior_w + prior_l)
            nudge = (pct - prior_pct) * 20  # +/- 20 swing
    score = max(0.0, min(100.0, base + nudge))
    return (score, f"{w}-{l} ({pct:.0%} win rate)")


def _mood_volume_health(mood: dict[str, Any] | None) -> tuple[float | None, str]:
    """Score from conversation volume — engaged fans = healthy."""
    if not mood:
        return (None, "No mood signal yet")
    eff = mood.get("effective_n") or 0
    try:
        eff = float(eff)
    except (TypeError, ValueError):
        eff = 0.0
    if eff <= 0:
        return (None, "Conversation pipeline quiet")
    # Effective-n in CFB ranges typically 0-500+; map log-linearly.
    import math
    score = 30 + 60 * (math.log10(max(1.0, eff)) / 3.0)  # 1→30, 10→50, 100→70, 1000→90
    score = max(0.0, min(100.0, score))
    return (score, f"{int(eff)} effective signal-N")


def _cohort_health(divergence: float | None) -> tuple[float | None, str]:
    """Score from cohort divergence — high divergence = active, engaged factions.
    Inverted from 'consensus' framing because a fanbase that argues is alive."""
    if divergence is None:
        return (None, "Cohort engagement awaiting")
    # divergence in [0, 2-ish]. Healthy band is 0.5-1.5; <0.3 = apathy, >2.0 = fractured panic.
    d = float(divergence)
    if d < 0.3:
        return (35, f"Divergence {d:.2f} — quiet")
    if d > 2.0:
        return (45, f"Divergence {d:.2f} — fracture risk")
    # Sweet spot 0.5-1.5 → ~75-85
    if 0.5 <= d <= 1.5:
        return (70 + (1.0 - abs(d - 1.0)) * 15, f"Divergence {d:.2f} — engaged")
    return (55, f"Divergence {d:.2f} — moderate")


# ---------------------------------------------------------------------------
# Band classification
# ---------------------------------------------------------------------------

def _band(score: float) -> tuple[str, str]:
    """Return (label, css_suffix) per brief §11.1 ladder."""
    if score < 26:
        return ("Declining", "declining")
    if score < 51:
        return ("Stable", "stable")
    if score < 76:
        return ("Growing", "growing")
    return ("Surging", "surging")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_fanbase_health(
    profile: Profile,
    snapshot: TeamSnapshot | None,
    mood: dict[str, Any] | None,
    divergence: float | None,
    arc_rows: list[dict[str, Any]] | None = None,
) -> str:
    """Render the Fanbase Health Index gauge (Brief §11.1)."""
    if snapshot is None:
        return ""

    components: list[tuple[str, float, str]] = []  # (label, score, note)

    rec_score, rec_note = _record_health(snapshot, arc_rows)
    if rec_score is not None:
        components.append(("On-Field", rec_score, rec_note))

    mood_score, mood_note = _mood_volume_health(mood)
    if mood_score is not None:
        components.append(("Volume", mood_score, mood_note))

    cohort_score, cohort_note = _cohort_health(divergence)
    if cohort_score is not None:
        components.append(("Cohort Engagement", cohort_score, cohort_note))

    if not components:
        # All signals empty — still render an honest empty card.
        return (
            '<section class="fanbase-health" aria-labelledby="fanbase-health-h" '
            'data-module="fanbase-health" data-state="empty" style="--health-score: 50;">'
            '<div class="fanbase-health__header">'
            '<p class="fanbase-health__eyebrow">Fanbase Health Index</p>'
            f'<h2 id="fanbase-health-h" class="fanbase-health__band fanbase-health__band--stable">Awaiting Signal</h2>'
            '</div>'
            '<div class="fanbase-health__gauge"><div class="fanbase-health__gauge-fill"></div><div class="fanbase-health__gauge-needle"></div></div>'
            '<div class="fanbase-health__legend">'
            '<span>Declining</span><span>Stable</span><span>Growing</span><span>Surging</span>'
            '</div>'
            '<div class="fanbase-health__components">'
            '<div class="fanbase-health__components-row">'
            '<span>Volume, on-field, and cohort signals pending — index activates as season data lands.</span>'
            '</div></div>'
            '</section>'
        )

    composite = sum(s for _, s, _ in components) / len(components)
    band_label, band_suffix = _band(composite)
    confidence = (
        "high" if len(components) >= 3
        else ("medium" if len(components) == 2 else "low")
    )
    program = escape(profile.program_name)

    comp_rows_html = "".join(
        f'<div class="fanbase-health__components-row">'
        f'<span><strong>{escape(label)}</strong> — {escape(note)}</span>'
        f'<em>{int(round(score))}</em>'
        f'</div>'
        for label, score, note in components
    )

    return f"""
<section class="fanbase-health" aria-labelledby="fanbase-health-h"
         data-module="fanbase-health" data-state="ready"
         data-confidence="{confidence}"
         style="--health-score: {composite:.0f};">
  <div class="fanbase-health__header">
    <p class="fanbase-health__eyebrow">Fanbase Health Index · {program} · {confidence} confidence</p>
    <h2 id="fanbase-health-h" class="fanbase-health__band fanbase-health__band--{band_suffix}">{escape(band_label)} ({int(round(composite))})</h2>
  </div>
  <div class="fanbase-health__gauge" role="img" aria-label="Fanbase health {int(round(composite))} out of 100">
    <div class="fanbase-health__gauge-fill"></div>
    <div class="fanbase-health__gauge-needle"></div>
  </div>
  <div class="fanbase-health__legend">
    <span>Declining</span><span>Stable</span><span>Growing</span><span>Surging</span>
  </div>
  <div class="fanbase-health__components">
    {comp_rows_html}
  </div>
</section>"""


__all__ = ["render_fanbase_health", "FANBASE_HEALTH_CSS"]
