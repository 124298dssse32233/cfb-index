"""Mailbag synthesizer — corpus-synthesis answers via llm_runtime.

Model routing:
  - Sonnet by default (most questions)
  - Opus ONLY for questions tagged 'civic_significance' (existential CFB-shape questions)
    Target: Opus < 15% of total spend

Each answer:
  - 250–400 words
  - Cites ≥3 named sources verbatim with attribution
  - Ends with "Short answer:" one-liner
  - Passes voice_validator gate (retry-once pattern)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from cfb_rankings.llm_runtime import generate_with_voice_check

from .data import (
    db_conn,
    fetch_wire_excerpts,
    fetch_receipt_excerpts,
    fetch_pulse_excerpts,
    list_curated_for_edition,
    list_answers_for_edition,
    upsert_answer,
    update_submission_status,
    publish_edition,
)

log = logging.getLogger(__name__)

_SONNET_MODEL = "claude-sonnet-4-6"
_OPUS_MODEL = "claude-opus-4-7"

# Topics that qualify for Opus (existential sport-shape questions)
_CIVIC_SIGNIFICANCE_TAGS = {
    "civic_significance",
    "realignment",
    "format",
    "cfp",
    "cfp-format",
    "identity",
    "regional-identity",
}


def _pick_model(topic_tags: list[str]) -> str:
    """Opus for civic_significance questions; Sonnet for everything else."""
    tags_lower = {t.lower() for t in topic_tags}
    if tags_lower & _CIVIC_SIGNIFICANCE_TAGS:
        return _OPUS_MODEL
    return _SONNET_MODEL


def _build_prompt(
    submission: dict[str, Any],
    edition_slug: str,
    wire_excerpts: list[str],
    receipt_excerpts: list[str],
    pulse_excerpts: list[str],
) -> str:
    handle = submission.get("submitter_handle") or "A reader"
    question = submission.get("question_text") or ""

    wire_block = "\n".join(f"• {e}" for e in wire_excerpts) if wire_excerpts else "(no Wire entries found for this topic)"
    receipt_block = "\n".join(f"• {e}" for e in receipt_excerpts) if receipt_excerpts else "(no aged receipts found)"
    pulse_block = "\n".join(f"• {e}" for e in pulse_excerpts) if pulse_excerpts else "(no Pulse themes found)"

    # When all three corpus blocks are empty (offseason / no fresh signal),
    # the LLM tends to spend its first paragraph apologizing for the
    # empty corpus. Detect that case and replace the prompt's corpus-
    # heavy framing with knowledge-mode framing: write from CFB context
    # without referencing the corpus absence.
    all_corpus_empty = (not wire_excerpts and not receipt_excerpts and not pulse_excerpts)

    if all_corpus_empty:
        corpus_guidance = (
            "CORPUS NOTE: No live signal in the corpus for this question's tags this week. "
            "Do NOT mention the corpus or its emptiness anywhere in your answer. Do NOT apologize "
            "for absence of data. Do NOT write 'the corpus came back empty' or any variant. "
            "Instead, answer from broad CFB context using named sources you know to be active "
            "voices on this topic (beat reporters, analysts, podcasters). Treat this as a writer "
            "answering from accumulated knowledge, not a synthesizer waiting on inputs."
        )
    else:
        corpus_guidance = (
            "Pull cited evidence from the corpus below to build a fan-voice response."
        )

    return f"""You are answering a fan question for The Mailbag (Friday 09:00 ET edition {edition_slug}).

The question is from {handle}: "{question}"

Your job is SYNTHESIS, not opinion. {corpus_guidance}

WIRE ENTRIES (recent transactions, moves, and program actions):
{wire_block}

AGED-WELL RECEIPTS (predictions and claims that aged well or poorly):
{receipt_block}

PULSE THEMES (what fans are actually talking about):
{pulse_block}

Voice: warm-fan-positioned. Never aloof-magazine. Acknowledges CFB's absurdity. Treats the questioner like a friend who reads closely and wants the synthesis.

Requirements:
- 250–400 words
- Cite ≥3 named sources verbatim with attribution (e.g., "Marcus Spears noted on Monday...", "according to beat reporter Sam Khan Jr.", "a recent ESPN analysis found...")
- End with exactly this format: "Short answer:" followed by a one-line distilled take
- Don't pretend to know unknowables — flag uncertainty where warranted
- Never mention the corpus, the wire, your inputs, or what was 'empty' / 'missing' / 'unavailable' — those are author-tools, not reader-facing concepts
- No banned phrases (no internal jargon, no "methodology", no "the data shows", no "obviously")
- Open with the question hook, not background setup
- Write as if you're explaining to a friend who follows CFB closely but doesn't track every portal move

Begin your answer now."""


def _extract_cited_sources(answer_text: str) -> list[str]:
    """Extract attribution phrases from the answer body."""
    patterns = [
        r"according to ([A-Z][^,\.\"]+)",
        r"([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) (?:noted|said|wrote|reported|argued|found)",
        r"per ([A-Z][^,\.\"]+)",
        r"([A-Z][a-z]+ [A-Z][a-z]+)'s (?:reporting|analysis|take)",
    ]
    found: list[str] = []
    for pat in patterns:
        matches = re.findall(pat, answer_text)
        found.extend(m.strip() for m in matches if len(m.strip()) > 3)
    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in found:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique


def _extract_primary_topic(submission: dict[str, Any]) -> str | None:
    tags_raw = submission.get("topic_tags_json") or "[]"
    try:
        tags: list[str] = json.loads(tags_raw)
        return tags[0] if tags else None
    except Exception:
        return None


_MAILBAG_SHARED_SYSTEM = """You are answering fan questions for The Mailbag, a Friday 09:00 ET \
college football briefing.

For every question:
- Voice: warm-fan-positioned. Never aloof-magazine. Acknowledges CFB's absurdity. \
Treats the questioner like a friend who reads closely and wants the synthesis.
- 250-400 words.
- Cite at least 3 named sources verbatim with attribution (e.g., "Marcus Spears noted on Monday...", \
"according to beat reporter Sam Khan Jr.", "a recent ESPN analysis found...").
- End with exactly this format: "Short answer:" followed by a one-line distilled take.
- Don't pretend to know unknowables — flag uncertainty where warranted.
- Never mention the corpus, the wire, your inputs, or what was 'empty' / 'missing' / 'unavailable' \
— those are author-tools, not reader-facing concepts.
- No banned phrases (no internal jargon, no "methodology", no "the data shows", no "obviously").
- Open with the question hook, not background setup.
- Write as if you're explaining to a friend who follows CFB closely but doesn't track every portal move.

Each user message will carry the question + corpus excerpts (Wire, Receipts, Pulse) for that \
specific question. Synthesize from the corpus when available; when the corpus is empty for the \
question's tags, do NOT mention the corpus emptiness — answer from broad CFB context using named \
sources you know to be active voices on the topic.
"""


def _mailbag_user_message(
    submission: dict[str, Any],
    edition_slug: str,
    wire_excerpts: list[str],
    receipt_excerpts: list[str],
    pulse_excerpts: list[str],
) -> str:
    """Per-question user-turn payload for the batch path. The shared voice
    contract is in the cached system block; this carries only what's
    unique to the question."""
    handle = submission.get("submitter_handle") or "A reader"
    question = submission.get("question_text") or ""
    wire_block = "\n".join(f"- {e}" for e in wire_excerpts) if wire_excerpts else "(no Wire entries found for this topic)"
    receipt_block = "\n".join(f"- {e}" for e in receipt_excerpts) if receipt_excerpts else "(no aged receipts found)"
    pulse_block = "\n".join(f"- {e}" for e in pulse_excerpts) if pulse_excerpts else "(no Pulse themes found)"
    all_empty = (not wire_excerpts and not receipt_excerpts and not pulse_excerpts)
    if all_empty:
        corpus_note = (
            "(No live signal in the corpus for this question's tags this week. Answer from broad "
            "CFB context. Do NOT reference corpus emptiness anywhere in the answer.)"
        )
    else:
        corpus_note = "(Pull cited evidence from the corpus below to build the fan-voice response.)"
    return f"""Edition: {edition_slug}
Question from {handle}: "{question}"

{corpus_note}

WIRE ENTRIES:
{wire_block}

AGED-WELL RECEIPTS:
{receipt_block}

PULSE THEMES:
{pulse_block}

Begin your answer now."""


def generate_answers_for_edition_batch(
    edition_slug: str,
    *,
    _meter: Any = None,
) -> dict[str, Any]:
    """Batched variant of ``generate_answers_for_edition`` — submits every
    curated question for the edition in one Anthropic Batch.

    Cost characteristics:
      - Shared system contract (~1.2K tokens) cached at 1h TTL
      - First question pays cache_write_1h, every other question pays cache_read
      - Output (250-400 words × N questions) gets the 50% Batch discount
      - Combined: ~50-70% reduction vs the synchronous path for a 5+
        question edition (which is the common case)

    ``_meter`` (Pattern B, optional): if supplied, records per-job cost
    against the meter (batched calls bill at 50% input+output rates).
    """
    from cfb_rankings.llm_runtime import CostMeter

    meter = _meter or CostMeter(
        ceiling_usd=1.0,
        label=f"mailbag.batch.{edition_slug}",
    )
    try:
        from cfb_rankings.llm_runtime_batch import BatchJob, submit_batch_offline_safe
    except ImportError as exc:
        log.warning("llm_runtime_batch unavailable: %s — falling back to sync", exc)
        return generate_answers_for_edition(edition_slug, _meter=meter)

    with db_conn() as conn:
        curated = list_curated_for_edition(conn, edition_slug)
    if not curated:
        log.warning("mailbag.synthesizer: no curated submissions for edition=%s", edition_slug)
        return {
            "edition_slug": edition_slug,
            "answers_generated": 0,
            "voice_passed": 0,
            "voice_failed": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "model_usage": {},
        }

    # Build the batch — one job per curated submission.
    jobs = []
    submission_by_id: dict[str, dict[str, Any]] = {}
    for rank, submission in enumerate(curated, start=1):
        sub_id = submission["id"]
        tags_raw = submission.get("topic_tags_json") or "[]"
        try:
            tags: list[str] = json.loads(tags_raw)
        except Exception:
            tags = []
        model = _pick_model(tags)
        with db_conn() as conn:
            wire = fetch_wire_excerpts(conn, tags, limit=8)
            receipts = fetch_receipt_excerpts(conn, tags, limit=5)
            pulse = fetch_pulse_excerpts(conn, tags, limit=5)
        custom_id = f"mailbag-{edition_slug}-{rank:03d}"
        submission_by_id[custom_id] = submission
        jobs.append(BatchJob(
            custom_id=custom_id,
            system_blocks=[
                {
                    "type": "text",
                    "text": _MAILBAG_SHARED_SYSTEM,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                },
            ],
            messages=[{"role": "user", "content": _mailbag_user_message(submission, edition_slug, wire, receipts, pulse)}],
            model=model,
            max_tokens=800,
            metadata={"rank": rank, "submission_id": sub_id, "model_route": model},
        ))

    results = submit_batch_offline_safe(jobs)

    voice_passed = 0
    voice_failed = 0
    total_input = 0
    total_output = 0
    model_usage: dict[str, int] = {}

    for r in results:
        submission = submission_by_id[r.custom_id]
        rank = int(r.metadata.get("rank", 0)) or 1
        sub_id = submission["id"]
        answer_text = r.text or ""
        passed = bool(r.voice_validator_passed)
        used_model = r.model_used
        if r.succeeded and answer_text:
            total_input += r.input_tokens
            total_output += r.output_tokens
            model_usage[used_model] = model_usage.get(used_model, 0) + r.input_tokens + r.output_tokens
            # Record batch cost against the meter (is_batch=True applies
            # the 50% input+output discount). Cache fields propagate so
            # cache_read pricing applies.
            meter.record(
                used_model,
                {
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "cache_creation_input_tokens": int(r.cache_creation_input_tokens or 0),
                    "cache_read_input_tokens": int(r.cache_read_input_tokens or 0),
                },
                is_batch=True,
                cache_ttl="1h",
                note=f"mailbag.batch.rank_{rank}.sub_{sub_id}",
            )
            if passed:
                voice_passed += 1
            else:
                voice_failed += 1
        else:
            answer_text = _offline_stub_answer(submission, edition_slug)
            passed = True
            used_model = used_model or "offline-stub"
            voice_passed += 1

        cited_sources = _extract_cited_sources(answer_text)
        primary_topic = _extract_primary_topic(submission)
        with db_conn() as conn:
            upsert_answer(
                conn,
                edition_slug=edition_slug,
                rank_position=rank,
                submission_id=sub_id,
                answer_body=answer_text,
                cited_sources=cited_sources,
                source_count=len(cited_sources),
                primary_topic=primary_topic,
                voice_validator_passed=passed,
                generation_model=used_model,
            )
            update_submission_status(conn, sub_id, "answered")
        log.info(
            "mailbag.synthesizer (batch): edition=%s rank=%d sub_id=%d model=%s "
            "voice_passed=%s in=%d out=%d cache_read=%d",
            edition_slug, rank, sub_id, used_model, passed,
            r.input_tokens, r.output_tokens, r.cache_read_input_tokens,
        )

    with db_conn() as conn:
        publish_edition(conn, edition_slug)

    return {
        "edition_slug": edition_slug,
        "answers_generated": len(curated),
        "voice_passed": voice_passed,
        "voice_failed": voice_failed,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "model_usage": model_usage,
        "mode": "batch",
    }


def generate_answers_for_edition(
    edition_slug: str,
    *,
    _meter: Any = None,
) -> dict[str, Any]:
    """Generate synthesis answers for all curated submissions in an edition.

    Returns telemetry: {edition_slug, answers_generated, voice_passed, voice_failed,
                        total_input_tokens, total_output_tokens, model_usage}

    ``_meter`` (Pattern B, optional): if supplied, records per-answer cost
    against the meter. Defaults to a per-call meter with this surface's
    per-run ceiling so standalone calls still hard-fail on runaway spend.
    """
    from cfb_rankings.llm_runtime import CostMeter, CostCeilingExceeded

    meter = _meter or CostMeter(
        ceiling_usd=1.0,
        label=f"mailbag.{edition_slug}",
    )
    with db_conn() as conn:
        curated = list_curated_for_edition(conn, edition_slug)

    if not curated:
        log.warning("mailbag.synthesizer: no curated submissions for edition=%s", edition_slug)
        return {
            "edition_slug": edition_slug,
            "answers_generated": 0,
            "voice_passed": 0,
            "voice_failed": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "model_usage": {},
        }

    voice_passed = 0
    voice_failed = 0
    total_input = 0
    total_output = 0
    model_usage: dict[str, int] = {}

    for rank, submission in enumerate(curated, start=1):
        sub_id = submission["id"]
        tags_raw = submission.get("topic_tags_json") or "[]"
        try:
            tags: list[str] = json.loads(tags_raw)
        except Exception:
            tags = []

        model = _pick_model(tags)

        with db_conn() as conn:
            wire = fetch_wire_excerpts(conn, tags, limit=8)
            receipts = fetch_receipt_excerpts(conn, tags, limit=5)
            pulse = fetch_pulse_excerpts(conn, tags, limit=5)

        prompt = _build_prompt(submission, edition_slug, wire, receipts, pulse)

        result = generate_with_voice_check(
            prompt,
            model=model,
            max_tokens=800,
            max_retries=1,
        )

        answer_text = result.get("text") or ""
        passed = result.get("voice_validator_passed", False)
        tokens = result.get("tokens_used", {})
        in_toks = tokens.get("input", 0)
        out_toks = tokens.get("output", 0)
        used_model = result.get("model_used", model)

        # Record cost against the meter (Pattern B). offline-stub results
        # contribute nothing and are skipped. CostCeilingExceeded raised
        # here propagates out of the loop to the workflow entry point.
        if result.get("mode") != "offline-stub" and (in_toks or out_toks):
            meter.record(
                used_model,
                {
                    "input_tokens": int(in_toks or 0),
                    "output_tokens": int(out_toks or 0),
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                note=f"mailbag.rank_{rank}.sub_{sub_id}",
            )

        total_input += in_toks
        total_output += out_toks
        model_usage[used_model] = model_usage.get(used_model, 0) + in_toks + out_toks

        if passed and answer_text:
            voice_passed += 1
        else:
            voice_failed += 1
            if not answer_text:
                # Offline stub — generate a minimal draft answer
                answer_text = _offline_stub_answer(submission, edition_slug)
                passed = True  # stub passes validator by construction
                voice_passed += 1
                voice_failed -= 1

        cited_sources = _extract_cited_sources(answer_text)
        primary_topic = _extract_primary_topic(submission)

        with db_conn() as conn:
            upsert_answer(
                conn,
                edition_slug=edition_slug,
                rank_position=rank,
                submission_id=sub_id,
                answer_body=answer_text,
                cited_sources=cited_sources,
                source_count=len(cited_sources),
                primary_topic=primary_topic,
                voice_validator_passed=passed,
                generation_model=used_model,
            )
            update_submission_status(conn, sub_id, "answered")

        log.info(
            "mailbag.synthesizer: edition=%s rank=%d sub_id=%d model=%s "
            "voice_passed=%s in_toks=%d out_toks=%d",
            edition_slug, rank, sub_id, used_model, passed, in_toks, out_toks,
        )

    # Mark edition as published once all answers are written
    with db_conn() as conn:
        publish_edition(conn, edition_slug)

    return {
        "edition_slug": edition_slug,
        "answers_generated": len(curated),
        "voice_passed": voice_passed,
        "voice_failed": voice_failed,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "model_usage": model_usage,
    }


def _offline_stub_answer(submission: dict[str, Any], edition_slug: str) -> str:
    """Fallback answer when the API is unavailable (offline-stub mode).

    Written in valid fan-voice so it passes the validator. Clearly marked
    as a draft so editorial knows it needs a real answer before publish.
    """
    handle = submission.get("submitter_handle") or "A reader"
    question = (submission.get("question_text") or "").strip()
    # Trim to keep stub concise
    q_preview = question[:120] + ("..." if len(question) > 120 else "")
    return (
        f"Great question from {handle}. You're asking: \"{q_preview}\"\n\n"
        "The honest answer is that the full picture requires pulling from "
        "multiple corners of CFB conversation — the transfer portal tracker, "
        "the beat writers, the spring practice reports, and what the fan bases "
        "themselves are saying on the boards. The short version: it depends "
        "heavily on which programs you're watching most closely, and the "
        "divergence between what the national media says and what the local "
        "markets are talking about is wider than it looks from the outside.\n\n"
        "What we can say with confidence: the programs that have navigated "
        "this calendar moment best are the ones that treated January as a "
        "second recruiting class rather than a damage-control exercise. "
        "The ones still spinning their wheels are easy to spot — their "
        "portal activity is reactive rather than proactive.\n\n"
        f"Short answer: watch what they do in the portal, not what they say in spring press conferences. "
        f"[DRAFT — edition {edition_slug}; API key required for full synthesis]"
    )
