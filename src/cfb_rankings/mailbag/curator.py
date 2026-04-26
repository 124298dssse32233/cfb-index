"""Mailbag curator — selects 3–5 submissions for a given edition.

Scoring dimensions (all weighted, all Haiku-compatible):
  1. Topic freshness   — recent Wire/Pulse activity on the question's tags
  2. Cohort breadth    — can the answer serve stat crowd, casual fans, AND diehards?
  3. Question quality  — specific > vague, original > duplicate, narrative > yes/no
  4. Entity variety    — no two questions share the same primary entity

Bootstrap path: if fewer than 3 real submissions exist, seeds representative
questions via submissions.seed_representative_submissions().
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from .data import (
    db_conn,
    fetch_wire_excerpts,
    list_queued_submissions,
    update_submission_status,
    upsert_edition,
    edition_publish_date,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

_W_FRESHNESS = 0.35
_W_BREADTH = 0.25
_W_QUALITY = 0.25
_W_VARIETY = 0.15

# Phrases suggesting a binary yes/no question (lower quality score)
_BINARY_PATTERNS = re.compile(
    r"\b(is|are|will|can|does|did|has|have|should|would)\b.{0,60}\?$",
    re.IGNORECASE,
)

# Phrases that indicate broad narrative framing (higher quality)
_NARRATIVE_SIGNALS = re.compile(
    r"\b(what does|why is|how does|explain|tell me about|what happened|"
    r"which program|what's the honest|what should I|who benefits)\b",
    re.IGNORECASE,
)

# Multi-cohort signal words — presence suggests the answer will serve everyone
_COHORT_SIGNALS = {
    "stat": 1,
    "epa": 1,
    "analytics": 1,
    "numbers": 1,
    "data": 1,
    "history": 1,
    "historically": 1,
    "rivalry": 1,
    "tradition": 1,
    "fan": 1,
    "fans": 1,
    "recruit": 1,
    "recruiting": 1,
    "transfer": 1,
    "portal": 1,
    "playoff": 1,
    "cfp": 1,
    "national": 1,
    "conference": 1,
}


def _score_freshness(submission: dict[str, Any], wire_excerpts: list[str]) -> float:
    """Higher score when there's recent Wire activity on this question's topics."""
    if not wire_excerpts:
        return 0.2  # some baseline — question may still be worth answering
    # More excerpts = topic is more active right now
    return min(1.0, len(wire_excerpts) / 5.0)


def _score_breadth(submission: dict[str, Any]) -> float:
    """Proxy: count multi-cohort signal words in the question text."""
    text = (submission.get("question_text") or "").lower()
    hits = sum(1 for word in _COHORT_SIGNALS if word in text)
    return min(1.0, hits / 3.0)


def _score_quality(submission: dict[str, Any]) -> float:
    """Penalize binary yes/no questions; reward narrative framing."""
    text = submission.get("question_text") or ""
    score = 0.5  # baseline
    if _NARRATIVE_SIGNALS.search(text):
        score += 0.3
    if _BINARY_PATTERNS.search(text):
        score -= 0.2
    # Reward longer, more specific questions
    words = len(text.split())
    if words >= 30:
        score += 0.2
    elif words < 12:
        score -= 0.15
    return max(0.0, min(1.0, score))


def _primary_entity(submission: dict[str, Any]) -> str:
    """Guess primary entity from topic_tags_json for variety enforcement."""
    tags_raw = submission.get("topic_tags_json") or "[]"
    try:
        tags: list[str] = json.loads(tags_raw)
    except Exception:
        tags = []
    if tags:
        return tags[0].lower()
    # Fallback: first distinctive noun in question
    text = (submission.get("question_text") or "").lower()
    for word in text.split():
        clean = re.sub(r"[^a-z]", "", word)
        if len(clean) > 5:
            return clean
    return "misc"


def curate_for_edition(
    edition_slug: str,
    *,
    max_answers: int = 5,
    min_answers: int = 3,
) -> dict[str, Any]:
    """Select 3–5 submissions from the queue for this edition.

    Sets selected submissions to status='curated', rejected to status='rejected'.
    Creates/updates the mailbag_editions row.

    Returns: {edition_slug, selected_ids, rejected_ids, bootstrap_seeded}
    """
    from .submissions import seed_representative_submissions

    with db_conn() as conn:
        queued = list_queued_submissions(conn, limit=100)

        bootstrap_seeded = False
        if len(queued) < min_answers:
            need = min_answers - len(queued)
            log.info(
                "mailbag.curator: only %d queued submissions; seeding %d bootstrap rows",
                len(queued), need + 2,
            )
            seed_representative_submissions(need + 2)
            queued = list_queued_submissions(conn, limit=100)
            bootstrap_seeded = True

        # Score every candidate
        scored: list[tuple[float, dict[str, Any]]] = []
        for sub in queued:
            tags_raw = sub.get("topic_tags_json") or "[]"
            try:
                tags: list[str] = json.loads(tags_raw)
            except Exception:
                tags = []

            wire = fetch_wire_excerpts(conn, tags, limit=6)
            f = _score_freshness(sub, wire)
            b = _score_breadth(sub)
            q = _score_quality(sub)
            total = _W_FRESHNESS * f + _W_BREADTH * b + _W_QUALITY * q + _W_VARIETY * 1.0
            scored.append((total, sub))

        # Sort descending
        scored.sort(key=lambda x: x[0], reverse=True)

        selected: list[dict[str, Any]] = []
        used_entities: set[str] = set()

        for _score, sub in scored:
            if len(selected) >= max_answers:
                break
            entity = _primary_entity(sub)
            if entity in used_entities:
                continue
            used_entities.add(entity)
            selected.append(sub)

        selected_ids = [s["id"] for s in selected]
        rejected_ids = [
            s["id"] for _score, s in scored if s["id"] not in selected_ids
        ]

        publish_date = edition_publish_date(edition_slug)
        upsert_edition(
            conn,
            edition_slug=edition_slug,
            publish_date=publish_date,
            status="draft",
            notes=f"Curated {len(selected_ids)} questions from {len(queued)} queued.",
        )

        for sub_id in selected_ids:
            update_submission_status(
                conn,
                sub_id,
                "curated",
                curator_notes=f"Selected for edition {edition_slug}",
            )
        for sub_id in rejected_ids:
            update_submission_status(
                conn,
                sub_id,
                "rejected",
                rejection_reason=f"Not selected for edition {edition_slug} (lower score or entity overlap)",
            )

    log.info(
        "mailbag.curator: edition=%s selected=%d rejected=%d bootstrap=%s",
        edition_slug, len(selected_ids), len(rejected_ids), bootstrap_seeded,
    )
    return {
        "edition_slug": edition_slug,
        "selected_ids": selected_ids,
        "rejected_ids": rejected_ids,
        "bootstrap_seeded": bootstrap_seeded,
        "publish_date": publish_date,
    }
