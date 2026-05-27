"""Narrative Arc renderer — displays the 3-act story from cache."""
from __future__ import annotations

from html import escape


NARRATIVE_ARC_CSS = """
/* Narrative Arc — 3-act season story */
.narrative-arc-v2 {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
}
.narrative-arc-v2__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 14px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.narrative-arc-v2__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.narrative-arc-v2__title {
  font-size: 1.05rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.narrative-arc-v2__acts {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
}
@media (max-width: 900px) {
  .narrative-arc-v2__acts { grid-template-columns: 1fr; gap: 10px; }
}
.narrative-arc-v2__act {
  background: rgba(255,255,255,0.020);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 14px 16px;
  position: relative;
  display: flex; flex-direction: column; gap: 8px;
}
.narrative-arc-v2__act::before {
  content: ""; position: absolute; left: 0; top: 14px; bottom: 14px;
  width: 3px; border-radius: 3px;
  background: var(--accolade-gold-base, #d1a23a);
  opacity: 0.45;
}
.narrative-arc-v2__act--opening::before { opacity: 0.30; }
.narrative-arc-v2__act--pivot::before   { opacity: 0.55; }
.narrative-arc-v2__act--finish::before  { opacity: 0.85; }
.narrative-arc-v2__act-num {
  font-size: 0.64rem; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--accolade-gold-base, #d1a23a);
  font-weight: 600;
  padding-left: 10px;
}
.narrative-arc-v2__act-label {
  font-size: 0.80rem; font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
  padding-left: 10px;
}
.narrative-arc-v2__act-text {
  font-size: 0.92rem; line-height: 1.5;
  color: var(--text-soft, rgba(255,255,255,0.82));
  padding-left: 10px;
  margin: 0;
}
.narrative-arc-v2__footnote {
  margin-top: 10px;
  font-size: 0.66rem; color: var(--text-quiet, rgba(255,255,255,0.5));
  font-style: italic;
}
.narrative-arc-v2--empty {
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-style: italic;
  padding: 14px;
}
"""


def render_narrative_arc(arc: dict | None) -> str:
    if not arc or not arc.get("opening_text"):
        return (
            '<section class="narrative-arc-v2 narrative-arc-v2--empty" '
            'data-module="narrative-arc-v2" data-state="empty">'
            'A 3-act season arc returns once this player has six or more games '
            'on the ledger.'
            '</section>'
        )
    return (
        '<section class="narrative-arc-v2" '
        'data-module="narrative-arc-v2" data-state="ready">'
        '<header class="narrative-arc-v2__head">'
        '<div>'
        '<p class="narrative-arc-v2__eyebrow">Narrative Arc · Season in three acts</p>'
        '<p class="narrative-arc-v2__title">How the season unfolded</p>'
        '</div>'
        '<span class="narrative-arc-v2__meta">AI-written from the game log</span>'
        '</header>'
        '<div class="narrative-arc-v2__acts">'
        '<article class="narrative-arc-v2__act narrative-arc-v2__act--opening">'
        '<p class="narrative-arc-v2__act-num">Act I</p>'
        '<p class="narrative-arc-v2__act-label">Opening</p>'
        f'<p class="narrative-arc-v2__act-text">{escape(arc["opening_text"])}</p>'
        '</article>'
        '<article class="narrative-arc-v2__act narrative-arc-v2__act--pivot">'
        '<p class="narrative-arc-v2__act-num">Act II</p>'
        '<p class="narrative-arc-v2__act-label">Pivot</p>'
        f'<p class="narrative-arc-v2__act-text">{escape(arc["pivot_text"])}</p>'
        '</article>'
        '<article class="narrative-arc-v2__act narrative-arc-v2__act--finish">'
        '<p class="narrative-arc-v2__act-num">Act III</p>'
        '<p class="narrative-arc-v2__act-label">Finish</p>'
        f'<p class="narrative-arc-v2__act-text">{escape(arc["finish_text"])}</p>'
        '</article>'
        '</div>'
        '<p class="narrative-arc-v2__footnote">Generated locally from the player&rsquo;s game log; '
        'facts grounded in box-score data.</p>'
        '</section>'
    )
