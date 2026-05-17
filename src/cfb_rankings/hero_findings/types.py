"""HeroFinding dataclass + FindingKind enum.

A hero finding is the single most-important number on a page: the
display-fonted value + a one-sentence interpretation + the sample-size
caption + the confidence chip. Every page archetype that has a hero
finding renders the same shape; the data shape carries everything the
renderer needs.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Literal


class FindingKind(str, enum.Enum):
    """What KIND of finding this is. Drives which generator produced it
    and which surfaces should accept it."""
    COHORT_DIVERGENCE = "cohort_divergence"       # e.g. Hub "47 of 130 fanbases diverged"
    BELIEF_DELTA = "belief_delta"                  # e.g. Team "-15 points this week"
    RACE_SHIFT = "race_shift"                      # e.g. Heisman "+18 market shift"
    ANNIVERSARY_ANCHOR = "anniversary_anchor"     # e.g. Today "On this day, 2014..."
    LEAD_CLAIM = "lead_claim"                      # e.g. Daily pulled-forward lead
    EDITION_LEAD = "edition_lead"                  # e.g. Edition cover essay lead
    FALLBACK_AVG_MOOD = "fallback_avg_mood"        # always-available baseline


@dataclass(frozen=True)
class HeroFinding:
    """One hero finding. Renderer-agnostic.

    Field semantics:
      kind             — which generator produced this (drives styling
                          conventions, e.g. anniversaries get a date chip)
      number           — the headline value, pre-formatted as the string
                          to render (e.g. "47 of 130", "−15", "+18%")
      sentence         — the one-line interpretation. May contain a single
                          ``<em>`` span for emphasis.
      sample_caption   — the "Sample: X mentions · Y sources · last 7 days"
                          line. Generated together with the chip.
      sample_size      — raw n for the chip (passed to confidence.band_for)
      confidence_domain — which confidence-calibration domain backs this
      confidence_override_label — optional label override (editorial soften)
      annotation_link  — optional permalink to the surface the finding
                          links to (e.g. /editions/2026-w19 for an
                          EDITION_LEAD finding)
      confidence_rank  — picker score (higher wins when multiple generators
                          produce findings for the same surface)
      sort_priority    — tiebreaker when ranks tie
    """
    kind: FindingKind
    number: str
    sentence: str
    sample_caption: str
    sample_size: int
    confidence_domain: Literal[
        "fan_intel", "historical", "model", "market", "prediction"
    ]
    confidence_override_label: str | None = None
    annotation_link: str | None = None
    confidence_rank: int = 0
    sort_priority: int = 0
    extras: dict = field(default_factory=dict)


__all__ = ["FindingKind", "HeroFinding"]
