"""Evidence-gated preview thesis module."""

from __future__ import annotations

import html
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


def render_preview_thesis(
    profile: Profile,
    snapshot: TeamSnapshot,
    claim: dict[str, Any] | None,
) -> str:
    if not claim:
        return ""
    payload = claim.get("payload") or {}
    headline = str(payload.get("headline") or "").strip()
    body = str(payload.get("body") or "").strip()
    if not headline or not body:
        return ""
    confidence = str(claim.get("confidence_band") or payload.get("confidence_band") or "unset")
    confidence_label = "Validated" if confidence == "unset" else f"{confidence.title()} confidence"
    source = str(claim.get("model_backend") or "validated")
    date_label = str(claim.get("as_of_date") or "")
    # Label the PREVIEW season the claim targets (e.g. 2026), not the snapshot's
    # latest *game* season (which lags to 2024 while game data catches up).
    season_label = str(claim.get("season_year") or snapshot.season_year)
    return f"""
<section class="preview-thesis" aria-labelledby="preview-thesis-h" data-confidence="{html.escape(confidence)}">
  <div class="preview-thesis__meta">
    <span>Validated Preview Thesis</span>
    <span>{html.escape(season_label)}</span>
  </div>
  <h2 class="preview-thesis__title" id="preview-thesis-h">{html.escape(headline)}</h2>
  <p class="preview-thesis__body">{html.escape(body)}</p>
  <div class="preview-thesis__receipt">
    <span>{html.escape(confidence_label)}</span>
    <span>{html.escape(source)}</span>
    <span>{html.escape(date_label)}</span>
  </div>
</section>
"""


PREVIEW_THESIS_CSS = """
/* Evidence-gated preview thesis */
.preview-thesis {
  border: 1px solid color-mix(in srgb, var(--accent-primary) 36%, var(--border));
  border-radius: 8px;
  padding: clamp(1rem, 2vw, 1.4rem);
  background: color-mix(in srgb, var(--accent-primary) 9%, var(--surface));
  overflow-wrap: anywhere;
}
.preview-thesis__meta,
.preview-thesis__receipt {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem .8rem;
  font: 700 .72rem/1.2 var(--font-sans);
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.preview-thesis__title {
  margin: .45rem 0 .45rem;
  font: 700 clamp(1.28rem, 2.2vw, 1.95rem)/1.08 var(--font-display);
  letter-spacing: 0;
  color: var(--text);
}
.preview-thesis__body {
  max-width: 76ch;
  margin: 0 0 .9rem;
  font: 500 clamp(.98rem, 1.25vw, 1.08rem)/1.55 var(--font-sans);
  color: var(--text);
}
@media (max-width: 540px) {
  .preview-thesis {
    padding: 1rem;
  }
  .preview-thesis__meta,
  .preview-thesis__receipt {
    gap: .4rem .65rem;
    font-size: .66rem;
    letter-spacing: .06em;
  }
  .preview-thesis__title {
    font-size: 1.28rem;
    line-height: 1.12;
  }
}
"""
