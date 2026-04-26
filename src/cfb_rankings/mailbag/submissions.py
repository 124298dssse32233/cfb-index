"""Mailbag submission intake.

Public API:
  - submit_question(handle, email, question_text) — server-side intake
  - seed_representative_submissions(n) — bootstrap seeder
  - list_queued(limit) — queue inspection

The submission form at /mailbag/submit/ uses `mailto:mailbag@cfbindex.local`
for now. A future sprint wires Resend/Postmark to replace the mailto action
with real server-side intake calling submit_question().
"""
from __future__ import annotations

import logging
from typing import Any

from .data import (
    db_conn,
    insert_submission,
    list_queued_submissions,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Representative seed topics — cover current calendar moments.
# These are editorial-seed rows (submitter_email='editorial-seed@cfbindex.local').
# Future cycles replace them with real fan submissions.
# ---------------------------------------------------------------------------

_SEED_QUESTIONS: list[dict[str, Any]] = [
    {
        "handle": "Marcus from Columbus",
        "question_text": (
            "With the late transfer portal window closing, which programs actually "
            "improved their rosters and which ones are just spinning their wheels? "
            "Everyone claims to have 'fixed' their offensive line but is any of it real?"
        ),
        "topic_tags": ["transfer-portal", "roster", "offensive-line"],
    },
    {
        "handle": "Diane from Tuscaloosa",
        "question_text": (
            "The NFL draft fallout always reshapes the recruiting landscape — who "
            "benefits most from the early-round guys going pro? I'm thinking about "
            "the schools that lose elite players but suddenly have playing time to offer."
        ),
        "topic_tags": ["nfl-draft", "recruiting", "playing-time"],
    },
    {
        "handle": "Jorge from Austin",
        "question_text": (
            "Spring practice reports are always hype, but is there any program where "
            "the spring buzz actually matches reality by September? Which team's "
            "spring storyline should I actually believe this year?"
        ),
        "topic_tags": ["spring-practice", "preseason", "hype"],
    },
    {
        "handle": "Tyler from Ann Arbor",
        "question_text": (
            "Conference realignment feels like it's slowing down, but is it? "
            "What's the honest read on whether we're in a stable equilibrium or "
            "just a brief pause before the next round of musical chairs?"
        ),
        "topic_tags": ["realignment", "conference", "big-ten", "sec"],
    },
    {
        "handle": "Cassandra from Nashville",
        "question_text": (
            "The 12-team CFP is one season old. Which program has been most helped "
            "by the expanded field — a team that would have been left out under the "
            "old system but now has a legitimate path? And which program got the "
            "worst of the new format?"
        ),
        "topic_tags": ["cfp", "playoff", "realignment", "format"],
    },
    {
        "handle": "Patrick from Knoxville",
        "question_text": (
            "What does a 'rebuilding year' actually mean for the programs recruiting "
            "at the highest level? Is there really such a thing anymore when the "
            "transfer portal means a team can reload in January?"
        ),
        "topic_tags": ["rebuilding", "transfer-portal", "recruiting", "roster"],
    },
    {
        "handle": "Amara from Gainesville",
        "question_text": (
            "Summer camp season is about to start. Beyond the obvious blue-bloods, "
            "which mid-major is doing something interesting on the recruiting trail "
            "that deserves more national attention?"
        ),
        "topic_tags": ["recruiting", "mid-major", "summer-camps", "depth"],
    },
]


def submit_question(
    handle: str,
    email: str | None,
    question_text: str,
    *,
    topic_tags: list[str] | None = None,
) -> int:
    """Server-side intake for a fan submission. Returns the new submission id.

    This is the function a future Resend/Postmark webhook handler will call.
    The submit form at /mailbag/submit/ is currently mailto-based.
    """
    if not handle or not handle.strip():
        raise ValueError("submitter_handle is required")
    if not question_text or not question_text.strip():
        raise ValueError("question_text is required")

    with db_conn() as conn:
        sub_id = insert_submission(
            conn,
            handle=handle.strip(),
            email=(email or "").strip() or None,
            question_text=question_text.strip(),
            topic_tags=topic_tags,
        )
    log.info("mailbag.submissions: new submission id=%d handle=%r", sub_id, handle)
    return sub_id


def seed_representative_submissions(n: int = 5) -> list[int]:
    """Plant n representative questions for pipeline bootstrapping.

    Seeded rows are flagged with submitter_email='editorial-seed@cfbindex.local'
    so they're filterable (and replaceable) when real submissions arrive.

    Returns the list of inserted submission IDs.
    """
    seeds = _SEED_QUESTIONS[:max(1, min(n, len(_SEED_QUESTIONS)))]
    inserted_ids: list[int] = []

    with db_conn() as conn:
        for seed in seeds:
            sub_id = insert_submission(
                conn,
                handle=seed["handle"],
                email="editorial-seed@cfbindex.local",
                question_text=seed["question_text"],
                topic_tags=seed.get("topic_tags"),
            )
            inserted_ids.append(sub_id)
            log.info(
                "mailbag.submissions: seeded id=%d handle=%r",
                sub_id, seed["handle"],
            )

    return inserted_ids


def list_queued(limit: int = 50) -> list[dict[str, Any]]:
    """Return queued submissions for curator review."""
    with db_conn() as conn:
        return list_queued_submissions(conn, limit=limit)
