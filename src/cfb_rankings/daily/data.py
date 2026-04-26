"""Shared data types and constants for The Daily module."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Tentpole calendar — high-fan-resonance dates where take #1 routes to Opus
# ---------------------------------------------------------------------------

TENTPOLE_DATES: set[str] = {
    # CFP Selection / Championship
    "2026-12-07",  # CFP Selection Sunday (est.)
    "2027-01-20",  # CFP National Championship (est.)
    # Signing Day
    "2026-12-17",  # Early Signing Period opens
    "2027-02-05",  # National Signing Day
    # Heisman Week
    "2026-12-12",  # Heisman Trophy presentation (est.)
    # NFL Draft Week 1
    "2027-04-23",  # NFL Draft Day 1
    "2027-04-24",  # NFL Draft Day 2
    # Bowl / Playoff games — updated each cycle
    "2026-12-20",  # Bowl season opens
    "2027-01-01",  # New Year's Six
}


def is_tentpole(edition_date: str) -> bool:
    """Return True if this date is in the tentpole calendar."""
    return edition_date in TENTPOLE_DATES


# ---------------------------------------------------------------------------
# Input bundle
# ---------------------------------------------------------------------------

@dataclass
class WireCandidate:
    wire_id: int
    program_slug: str
    program_display: str
    action: str
    why_it_matters: str
    source_name: str
    occurred_at: str
    velocity_score: float
    impact_label: str

    def fan_resonance(self, now_iso: str) -> float:
        """velocity × recency_decay (1.0 at 0h, ~0.5 at 24h)."""
        from datetime import datetime, timezone
        try:
            then = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
            now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
            hours_ago = max(0.0, (now - then).total_seconds() / 3600)
        except Exception:
            hours_ago = 12.0
        recency = max(0.1, 1.0 - (hours_ago / 48.0))
        return self.velocity_score * recency


@dataclass
class ThreadCandidate:
    thread_slug: str
    title: str
    dek: str
    chapter_excerpt: str
    primary_program_slugs: list[str]
    last_chapter_at: str
    engagement_proxy: float  # chapter_count × follower_count


@dataclass
class PulseSpike:
    entity_slug: str
    entity_type: str
    lede: str
    themes_json: str
    mood_delta: float  # vs 7d trailing (synthetic if no baseline)


@dataclass
class ResolvedReceipt:
    claim_id: int
    source_slug: str
    source_display: str
    claim_summary_short: str
    outcome_verdict: str
    surprise_index: float
    claim_text: str


@dataclass
class DailyInputBundle:
    edition_date: str
    wire_candidates: list[WireCandidate] = field(default_factory=list)
    thread_candidates: list[ThreadCandidate] = field(default_factory=list)
    pulse_spikes: list[PulseSpike] = field(default_factory=list)
    resolved_receipts: list[ResolvedReceipt] = field(default_factory=list)

    # snapshot counts for DB persistence
    @property
    def wire_count(self) -> int:
        return len(self.wire_candidates)

    @property
    def active_thread_count(self) -> int:
        return len(self.thread_candidates)

    @property
    def pulse_spike_count(self) -> int:
        return len(self.pulse_spikes)

    @property
    def receipt_resolution_count(self) -> int:
        return len(self.resolved_receipts)

    def to_inputs_json(self) -> str:
        return json.dumps({
            "wire_candidates": [
                {"id": w.wire_id, "slug": w.program_slug, "action": w.action,
                 "source": w.source_name, "velocity": w.velocity_score}
                for w in self.wire_candidates
            ],
            "thread_candidates": [
                {"slug": t.thread_slug, "title": t.title, "engagement": t.engagement_proxy}
                for t in self.thread_candidates
            ],
            "pulse_spikes": [
                {"slug": p.entity_slug, "type": p.entity_type, "delta": p.mood_delta}
                for p in self.pulse_spikes
            ],
            "resolved_receipts": [
                {"id": r.claim_id, "source": r.source_slug,
                 "verdict": r.outcome_verdict, "surprise": r.surprise_index}
                for r in self.resolved_receipts
            ],
        })


# ---------------------------------------------------------------------------
# Take result
# ---------------------------------------------------------------------------

@dataclass
class TakeResult:
    rank_position: int
    headline: str
    body: str
    primary_entity_slug: str
    primary_entity_type: str
    cited_sources: list[str]
    fueled_by: dict[str, Any]
    voice_validator_passed: bool
    generation_model: str


# ---------------------------------------------------------------------------
# Canonical voice register examples (embedded, not DB-sourced)
# These provide the voice calibration reference in synthesis prompts.
# ---------------------------------------------------------------------------

VOICE_EXAMPLES: list[str] = [
    (
        "Ohio State's spring depth chart isn't just a list — it's the clearest signal yet "
        "that Ryan Day has decided this offense belongs to Will Howard. The starter designation "
        "next to Howard's name landed with a thud in Columbus, where fans spent six months "
        "arguing the opposite. Watch what happens to portal activity in the next 72 hours."
    ),
    (
        "Georgia's portal board is doing that thing it does — quietly, efficiently, without "
        "any of the drama other programs manufacture around these decisions. Kirby Smart "
        "confirmed Wednesday that the staff had identified two positions of 'immediate need.' "
        "In Athens, that phrase is a flare gun, not a press release. The offer tracker is "
        "already moving."
    ),
    (
        "The weirdest part of Saturday's outcome isn't the final score — it's what the "
        "numbers underneath it say about where Michigan's defensive identity actually is "
        "right now. Stewart Mandel flagged the third-down conversion rate in The Athletic "
        "on Sunday morning. That's the number to watch when Michigan State comes to town."
    ),
]
