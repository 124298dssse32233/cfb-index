"""Evidence-gated preview thesis module."""

from __future__ import annotations

import html
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


# Human-readable labels for claim kinds
_KIND_LABELS: dict[str, str] = {
    "record_projection": "Record projection",
    "roster_reload": "Roster reload",
    "portal": "Transfer portal",
    "draft": "NFL Draft",
    "schedule": "Schedule",
    "bowl": "Bowl history",
    "fan_intel": "Fan sentiment",
    "recruiting": "Recruiting",
}


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
    confidence_label = "Evidence-validated" if confidence == "unset" else f"{confidence.title()} confidence"
    date_label = str(claim.get("as_of_date") or "")
    # Label the PREVIEW season the claim targets (e.g. 2026), not the snapshot's
    # latest *game* season (which lags to 2024 while game data catches up).
    season_label = str(claim.get("season_year") or snapshot.season_year)

    # Build evidence chips from supporting_claims
    supporting = payload.get("supporting_claims") or []
    chips_html = ""
    if isinstance(supporting, list) and supporting:
        chips: list[str] = []
        seen_kinds: set[str] = set()
        for item in supporting:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "")
            text = str(item.get("text") or "").strip()
            if not text or kind in seen_kinds:
                continue
            seen_kinds.add(kind)
            label = _KIND_LABELS.get(kind, kind.replace("_", " ").title())
            chips.append(
                f'<li class="preview-thesis__chip">'
                f'<span class="preview-thesis__chip-label">{html.escape(label)}</span>'
                f'<span class="preview-thesis__chip-text">{html.escape(text)}</span>'
                f'</li>'
            )
        if chips:
            chips_html = (
                '<ul class="preview-thesis__chips" aria-label="Supporting evidence">'
                + "".join(chips[:4])
                + "</ul>"
            )

    return f"""
<section class="preview-thesis" aria-labelledby="preview-thesis-h" data-confidence="{html.escape(confidence)}">
  <div class="preview-thesis__meta">
    <span>2026 Preview Thesis</span>
    <span>{html.escape(season_label)}</span>
    <span class="preview-thesis__badge">{html.escape(confidence_label)}</span>
  </div>
  <h2 class="preview-thesis__title" id="preview-thesis-h">{html.escape(headline)}</h2>
  <p class="preview-thesis__body">{html.escape(body)}</p>
  {chips_html}
  <div class="preview-thesis__receipt">
    <span>Data as of {html.escape(date_label)}</span>
    <span>&middot;</span>
    <span>Validated against program evidence</span>
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
.preview-thesis__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .4rem .7rem;
  font: 700 .72rem/1.2 var(--font-sans);
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: .2rem;
}
.preview-thesis__badge {
  background: color-mix(in srgb, var(--accent-primary) 22%, transparent);
  color: var(--accent-primary);
  border-radius: 4px;
  padding: .15em .55em;
  font-size: .68rem;
  letter-spacing: .06em;
}
.preview-thesis__title {
  margin: .45rem 0 .4rem;
  font: 700 clamp(1.28rem, 2.2vw, 1.95rem)/1.08 var(--font-display);
  letter-spacing: 0;
  color: var(--text);
}
.preview-thesis__body {
  max-width: 76ch;
  margin: 0 0 .75rem;
  font: 500 clamp(.98rem, 1.25vw, 1.08rem)/1.55 var(--font-sans);
  color: var(--text);
}
.preview-thesis__chips {
  list-style: none;
  margin: 0 0 .8rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: .35rem;
}
.preview-thesis__chip {
  display: flex;
  align-items: baseline;
  gap: .5rem;
  font-size: .84rem;
  line-height: 1.45;
  color: var(--text);
}
.preview-thesis__chip-label {
  flex-shrink: 0;
  font: 700 .66rem/1.2 var(--font-sans);
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--accent-primary);
  min-width: 6rem;
}
.preview-thesis__chip-text {
  color: var(--text-secondary, var(--text-muted));
  font-size: .88rem;
}
.preview-thesis__receipt {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .4rem .6rem;
  font: 400 .72rem/1.2 var(--font-sans);
  letter-spacing: .05em;
  color: var(--text-muted);
  border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
  padding-top: .65rem;
  margin-top: .2rem;
}
@media (max-width: 540px) {
  .preview-thesis {
    padding: 1rem;
  }
  .preview-thesis__meta {
    font-size: .66rem;
    gap: .35rem .55rem;
  }
  .preview-thesis__title {
    font-size: 1.28rem;
    line-height: 1.12;
  }
  .preview-thesis__chip-label {
    min-width: 5rem;
  }
}
"""
