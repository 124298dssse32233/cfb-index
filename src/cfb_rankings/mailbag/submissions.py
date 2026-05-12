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
    {
        "handle": "Brendan from South Bend",
        "question_text": (
            "Notre Dame's QB room going into next season — is it actually settled, or "
            "is the staff just letting the spring battle play out without saying so? "
            "The depth chart whispers don't match what the coordinator's saying publicly."
        ),
        "topic_tags": ["notre-dame", "quarterback", "depth-chart", "spring"],
    },
    {
        "handle": "Reese from Eugene",
        "question_text": (
            "What does it actually take to be a 'Big Ten team' in the new alignment "
            "era? Oregon, Washington, USC, UCLA — are they fully assimilated yet, "
            "or is there still a Pac-12 hangover working its way through the rosters?"
        ),
        "topic_tags": ["realignment", "big-ten", "pac-12", "culture"],
    },
    {
        "handle": "Drew from Lubbock",
        "question_text": (
            "NIL collectives one year into the official era — which program clearly "
            "figured out the operational side, and which one is still treating it "
            "like a press release? I'm watching collective hires more than coordinator hires."
        ),
        "topic_tags": ["nil", "collectives", "front-office", "operations"],
    },
    {
        "handle": "Sophie from Lincoln",
        "question_text": (
            "Nebraska. Just — Nebraska. They keep getting close to figuring it out and "
            "then doing something that looks like 2018. What's the honest framework "
            "for whether they actually break through this season or it's another false dawn?"
        ),
        "topic_tags": ["nebraska", "rebuilding", "fan-voice", "big-ten"],
    },
    {
        "handle": "Hank from Stillwater",
        "question_text": (
            "Mike Gundy and Oklahoma State always feel like they should be Big 12 "
            "contenders and then aren't. With the conference reshuffled, is this "
            "their easiest path in a decade or are we about to find out they only "
            "looked good against old Big 12 defenses?"
        ),
        "topic_tags": ["oklahoma-state", "big-12", "gundy", "coaching"],
    },
    {
        "handle": "Lila from Stanford",
        "question_text": (
            "Academic-first programs in the new era — Stanford, Northwestern, Duke. "
            "Is there a structural advantage anymore, or is the portal era making "
            "the academic-fit pitch into a recruiting handicap? Asking as someone who "
            "watched the Cardinal roster get gutted."
        ),
        "topic_tags": ["stanford", "academic-fit", "portal", "recruiting"],
    },
    {
        "handle": "Marcus from Athens",
        "question_text": (
            "Quarterback development cycles — is anyone doing it right? It feels like "
            "every program is just hoping their portal QB hits, with almost no patience "
            "for the four-year develop-from-freshman model anymore. Which coaching staff "
            "is still doing development the old way and getting away with it?"
        ),
        "topic_tags": ["quarterback", "development", "coaching", "portal"],
    },
    {
        "handle": "Carla from Boulder",
        "question_text": (
            "Colorado after Deion — sustainable or a personality cult? When the "
            "national-attention bump fades, what's actually left? Asking earnestly, "
            "not snarkily; the on-field results are interesting but the program "
            "scaffolding still feels thin to me."
        ),
        "topic_tags": ["colorado", "coaching", "branding", "sustainability"],
    },
    {
        "handle": "Tomás from Coral Gables",
        "question_text": (
            "Miami's been one big move away from contention for a decade now. Cristobal's "
            "rebuild has the right pieces on paper. What's the actual blocker — "
            "coaching, culture, conference, or something more systemic in how the program operates?"
        ),
        "topic_tags": ["miami", "acc", "rebuild", "coaching"],
    },
    {
        "handle": "Eli from Norman",
        "question_text": (
            "Oklahoma's SEC adjustment — first year was rough by their standards. Is "
            "this a one-year roster-construction problem or the start of a 'we don't "
            "actually have the depth for this league' decade?"
        ),
        "topic_tags": ["oklahoma", "sec", "realignment", "depth"],
    },
    {
        "handle": "Priya from Pullman",
        "question_text": (
            "Pac-12 reconstitution — the new look with Boise State, Fresno State, San "
            "Diego State, etc. Is this actually a viable football conference or are we "
            "watching the slow death of the Group of Five tier as a meaningful category?"
        ),
        "topic_tags": ["pac-12", "group-of-five", "realignment", "tier"],
    },
    {
        "handle": "Walt from Morgantown",
        "question_text": (
            "Defensive coordinator turnover this offseason was wild. Which hire feels "
            "underrated and which one is going to look bad by October? I'm specifically "
            "watching the schools that promoted from within vs. went outside."
        ),
        "topic_tags": ["coaching", "defense", "coordinator", "hiring"],
    },
    {
        "handle": "Brenda from Lawrence",
        "question_text": (
            "Lance Leipold and Kansas football — is the ceiling actually a Big 12 "
            "championship game appearance now, or are we still in 'feel-good story' "
            "territory? The roster suggests something more, but I want a sanity check."
        ),
        "topic_tags": ["kansas", "big-12", "leipold", "ceiling"],
    },
    {
        "handle": "Vince from Tallahassee",
        "question_text": (
            "FSU's exit drama from the ACC — what's the actual realistic timeline, "
            "and where do they land? The legal posturing has been going on long enough "
            "that I genuinely can't tell anymore which scenarios are leverage plays "
            "and which are real."
        ),
        "topic_tags": ["florida-state", "acc", "realignment", "lawsuit"],
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

    Dedup behavior: any seed whose `question_text` already exists in the
    submissions table is skipped. The previous version always picked
    `_SEED_QUESTIONS[:n]` so every week's mailbag re-curated the same
    seven questions — every edition (w17, w18, w19, w20...) ended up
    publishing identical content. With dedup, once a seed has been
    picked up by any edition, it can't be re-seeded.

    Returns the list of inserted submission IDs.
    """
    inserted_ids: list[int] = []

    with db_conn() as conn:
        existing_texts: set[str] = set()
        try:
            rows = conn.execute(
                "SELECT question_text FROM mailbag_submissions"
            ).fetchall()
            for row in rows:
                txt = row[0] if not isinstance(row, dict) else row.get("question_text")
                if txt:
                    existing_texts.add(txt.strip())
        except Exception:
            # Table might not exist on first run — fall through with empty set.
            existing_texts = set()

        # Pick the first n seeds whose question_text isn't already in the
        # submissions table. If all seeds are exhausted, the pool is empty
        # and the curator will see fewer queued rows — which is the right
        # signal that we've run out of evergreen offseason questions and
        # need real submissions (or an explicit "no mailbag this week"
        # decision) rather than recycling.
        available = [s for s in _SEED_QUESTIONS
                     if s["question_text"].strip() not in existing_texts]
        if not available:
            log.info(
                "mailbag.submissions: all %d seed questions exhausted; "
                "no new seeds planted",
                len(_SEED_QUESTIONS),
            )
            return []
        seeds = available[:max(1, min(n, len(available)))]

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
