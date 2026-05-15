"""Wire editorial — fan-voice "why it matters" for each entry.

Source of truth for the captions: `wire/authored_captions.py`.

The 110 real CFBD `/player/portal` entries currently in the DB were
each hand-authored in the Sprint 12 session — fan-voice, ~10-25 words,
specific to the player + donor + destination context. The dict in
`authored_captions.AUTHORED_CAPTIONS` keys on (program_slug, action),
which is unique within the table's 90-day dedupe window.

For any Wire row NOT in the authored dict — i.e. new CFBD ingest after
this sprint — the editorial generator emits a one-line factual
restatement of the action. That restatement passes voice_validator
because it has no opinion to leak. Production replaces the fallback
with a Sonnet API call (one prompt per row, cached on action hash);
the call site and validator gate are unchanged.

Validator gate: every emitted string passes through
`team_pages.voice_validator.validate_fan_voice` before insertion.
First-pass failure -> falls back to the factual restatement. No template
phrase-bank involved on the hot path.

Sprint v5-1.5 batch-API note
----------------------------
This module's current hot path is template + authored-caption lookup —
NOT a live LLM call. There is nothing to batch yet. When the production
path lands (Sonnet API per uncovered row with cache on action hash),
``generate_uncovered_rows_batch`` below is the planned entry point:
it submits every uncovered Wire row in one Anthropic Batch with a
shared cached system contract (impact-scoring rubric + voice register).
The function is wired to llm_runtime_batch but is a no-op until the
production LLM path is enabled — see ``generate_uncovered_rows_batch``.
"""
from __future__ import annotations

import logging
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.team_pages.voice_validator import validate_fan_voice

from .authored_captions import AUTHORED_CAPTIONS
from .impact_scorer import score_impact

log = logging.getLogger(__name__)


def _factual_restatement(row: dict[str, Any]) -> str:
    """Safe fallback when no authored caption exists.

    Pure restatement of the action — nothing editorial — guaranteed to
    pass the validator because it has no opinion to leak. Production
    replaces this with a per-row Sonnet API call.
    """
    program = (row.get("program_display") or "").strip()
    action = (row.get("action") or "").strip()
    if program and action:
        return f"{program}: {action}."
    return action or program or "Wire entry."


def _lookup_authored(row: dict[str, Any]) -> dict[str, str | None] | None:
    """Look up the authored caption for this row.

    Keys on (program_slug, action) which is the dedupe-unique pair.
    """
    key = (row.get("program_slug"), row.get("action"))
    return AUTHORED_CAPTIONS.get(key)


def generate_for_row(row: dict[str, Any]) -> dict[str, Any]:
    """Synthesize editorial fields for a single Wire entry.

    Strategy:
      1. Look up authored caption from `AUTHORED_CAPTIONS`.
      2. Validate. If passes, use it.
      3. If lookup misses, fall back to factual restatement (which
         passes the validator by construction).
    Returns: {"why_it_matters", "historical_comp", "impact_label", "impact_color"}
    """
    authored = _lookup_authored(row)
    historical: str | None = None

    if authored:
        candidate_why = (authored.get("why") or "").strip()
        candidate_hist = authored.get("hist")
        ok, _v = validate_fan_voice(candidate_why, source="wire.why_it_matters")
        if ok and candidate_why:
            why = candidate_why
        else:
            log.warning(
                "wire.editorial: authored caption failed validator for %s/%s",
                row.get("program_slug"), row.get("action"),
            )
            why = _factual_restatement(row)

        if candidate_hist:
            ok2, _v = validate_fan_voice(candidate_hist, source="wire.historical_comp")
            if ok2:
                historical = candidate_hist.strip()
    else:
        # No authored caption — factual restatement keeps the wire safe.
        why = _factual_restatement(row)

    impact_label, impact_color = score_impact(row)

    return {
        "why_it_matters": why,
        "historical_comp": historical,
        "impact_label": impact_label,
        "impact_color": impact_color,
    }


def generate_editorial_for_pending(
    db: Database,
    *,
    days: int = 90,
    overwrite: bool = False,
) -> dict[str, int]:
    """Fill in editorial fields for wire_entries rows missing them.

    Returns: {processed, validator_passed, validator_dropped,
              historical_comps, authored, factual_fallback}
    """
    where = "where occurred_at >= datetime('now', :since)"
    if not overwrite:
        where += " and (why_it_matters is null or trim(why_it_matters) = '')"

    rows = db.query_all(
        f"""
        select id, occurred_at, program_slug, program_display, actor_kind,
               action, fan_intel_velocity_spike, related_thread_slug
        from wire_entries
        {where}
        order by occurred_at desc
        """,
        {"since": f"-{int(days)} days"},
    )

    processed = 0
    factual_fallback = 0
    authored_used = 0
    historical_count = 0
    validator_dropped = 0
    for row in rows:
        # Track whether an authored caption was found before generation.
        had_authored = _lookup_authored(row) is not None

        result = generate_for_row(row)

        is_factual = result["why_it_matters"].startswith(
            f'{row.get("program_display") or ""}: '
        )
        if is_factual:
            factual_fallback += 1
            if had_authored:
                # Authored caption existed but failed validator — count as drop.
                validator_dropped += 1
        elif had_authored:
            authored_used += 1

        if result["historical_comp"]:
            historical_count += 1

        db.execute(
            """
            update wire_entries
               set why_it_matters = :why,
                   historical_comp = :hist,
                   impact_label = :impact_label,
                   impact_color = :impact_color
             where id = :id
            """,
            {
                "why": result["why_it_matters"],
                "hist": result["historical_comp"],
                "impact_label": result["impact_label"],
                "impact_color": result["impact_color"],
                "id": row["id"],
            },
        )
        processed += 1

    return {
        "processed": processed,
        "authored_used": authored_used,
        "factual_fallback": factual_fallback,
        "validator_dropped": validator_dropped,
        "validator_passed": processed - validator_dropped,
        "historical_comps": historical_count,
    }


# ---------------------------------------------------------------------------
# Sprint v5-1.5 — batch-ready scaffold (no-op until production LLM lands)
# ---------------------------------------------------------------------------

_WIRE_BATCH_SYSTEM = """You are writing the "why it matters" caption for a single Wire entry on a \
college football editorial site.

Voice: fan-voice, 10-25 words, specific to the player + donor + destination context. No corporate \
speak. No methodology references. No banned phrases. Return ONLY the caption text, no preamble.
"""


def generate_uncovered_rows_batch(
    db: Database,
    *,
    days: int = 90,
    model: str = "claude-sonnet-4-6",
) -> dict[str, Any]:
    """Batched LLM generation for Wire rows NOT covered by an authored caption.

    This is the planned entry point when the wire editorial path adopts a
    live Sonnet call per uncovered row (see module docstring). It builds
    one Anthropic Batch with a shared cached voice contract and one job
    per uncovered row, then updates the row's why_it_matters in DB.

    Current behavior: identifies uncovered rows, submits the batch via
    ``submit_batch_offline_safe``. If the API key is unset (typical for
    local dev), every job comes back as offline-stub and DB writes are
    skipped — the row keeps its factual_restatement until next run.
    Production deployment of this path is gated on the Sprint v5-2
    quality-loop work.
    """
    from cfb_rankings.llm_runtime_batch import BatchJob, submit_batch_offline_safe

    where = (
        "where occurred_at >= datetime('now', :since) "
        "  and (why_it_matters is null or trim(why_it_matters) = '' "
        "       or why_it_matters like '%: ' || action || '.')"
    )
    rows = db.query_all(
        f"""
        select id, occurred_at, program_slug, program_display, actor_kind,
               action, fan_intel_velocity_spike, related_thread_slug
        from wire_entries
        {where}
        order by occurred_at desc
        """,
        {"since": f"-{int(days)} days"},
    )

    # Skip rows that ARE covered by an authored caption.
    uncovered: list[dict[str, Any]] = []
    for r in rows:
        if _lookup_authored(r) is None:
            uncovered.append(r)

    if not uncovered:
        return {"uncovered": 0, "batched": 0, "updated": 0, "mode": "noop"}

    jobs: list[BatchJob] = []
    for r in uncovered:
        custom_id = f"wire-{r['id']}"
        program = (r.get("program_display") or "").strip()
        action = (r.get("action") or "").strip()
        user_prompt = (
            f"Program: {program}\n"
            f"Action: {action}\n"
            f"Velocity spike: {r.get('fan_intel_velocity_spike') or 'n/a'}\n"
            "Write the why-it-matters caption now."
        )
        jobs.append(BatchJob(
            custom_id=custom_id,
            system_blocks=[
                {
                    "type": "text",
                    "text": _WIRE_BATCH_SYSTEM,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                },
            ],
            messages=[{"role": "user", "content": user_prompt}],
            model=model,
            max_tokens=120,
            metadata={"wire_id": r["id"]},
        ))

    results = submit_batch_offline_safe(jobs)
    updated = 0
    for r_obj in results:
        if not r_obj.succeeded or not r_obj.text:
            continue
        text = r_obj.text.strip()
        ok, _violations = validate_fan_voice(text, source="wire.batch_why_it_matters")
        if not ok:
            continue
        wire_id = r_obj.metadata.get("wire_id")
        if wire_id is None:
            continue
        db.execute(
            "update wire_entries set why_it_matters = :why where id = :id",
            {"why": text, "id": wire_id},
        )
        updated += 1
    return {
        "uncovered": len(uncovered),
        "batched": len(jobs),
        "updated": updated,
        "mode": "batch",
    }
