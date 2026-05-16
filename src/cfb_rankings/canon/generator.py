"""Canon generation pipeline.

Per Sprint 11 brief §"LLM generation mechanism" (decision-and-document):
the editorial copy is authored directly in the build session — there is
no live Anthropic SDK call. This generator orchestrates:

  1. Load list metadata + authored entries from ``seed_authored``.
  2. Compute cohort splits via ``cohorts.compute_cohort_split``.
  3. Compute year-over-year rank deltas via ``data.fetch_prior_year_rank``.
  4. Run every paragraph + one-liner through ``voice_validator.validate``.
  5. Write list metadata, entries, revision-history snapshot.
  6. Return a generation report with validator pass-rate.

The generator is *idempotent*: re-running it for the same list_slug
replaces all entries atomically and re-snapshots revision history.

Sprint v5-1.5 batch-API note
----------------------------
Canon is currently seed-authored — there is no live LLM call to batch.
When a Canon list ever does take the LLM path (e.g. dynamic top-25
mid-season rewrites), ``regenerate_entries_batch`` is the planned entry
point: every entry shares the same editorial contract for the list
(stable across the full N entries), so caching the contract as the
batch's system prefix is the right shape. Until that path lands the
scaffold below is a no-op when called with seed-authored lists.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from .data import (
    CanonListMeta, CanonEntry,
    upsert_list_meta, replace_entries, record_revision_history,
    fetch_prior_year_rank,
)
from .cohorts import compute_cohort_split, label_divergence
from .voice_validator import batch_validate
from . import seed_authored


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------

@dataclass
class GenerationReport:
    list_slug: str
    entry_count: int
    paragraphs_validated: int
    oneliners_validated: int
    validator_passed: int
    validator_failed: int
    validator_failed_labels: list[str]
    pass_rate: float
    cohort_splits_computed: int
    rank_deltas_computed: int
    effort_buckets: dict[str, int]   # haiku / sonnet / opus equivalent counts


# --------------------------------------------------------------------------
# Top-level entry points
# --------------------------------------------------------------------------

def seed_list_metadata(con: sqlite3.Connection) -> int:
    """Seed all 3 canon_lists rows (idempotent)."""
    metas = seed_authored.list_metadatas()
    for m in metas:
        upsert_list_meta(con, m)
    con.commit()
    return len(metas)


def generate_canon_list(
    con: sqlite3.Connection,
    list_slug: str,
    *,
    edition_year: int = 2026,
) -> GenerationReport:
    """Generate one canon list end-to-end."""
    # 1) Pull authored entries.
    raw_entries = seed_authored.entries_for(list_slug)
    if not raw_entries:
        raise ValueError(f"no authored entries for list_slug={list_slug!r}")

    # 2) Cohort split — needs entry_slug + display_name + rank.
    cohort_input = [{
        "entity_slug": e.entity_slug,
        "entity_display_name": e.entity_display_name,
        "program_label": e.program_label,
        "rank": e.rank,
    } for e in raw_entries]
    splits = compute_cohort_split(con, cohort_input)

    # 3) Apply cohort + rank-delta to each entry.
    enriched: list[CanonEntry] = []
    rank_deltas_computed = 0
    cohort_splits_computed = 0
    for e in raw_entries:
        split = splits.get(e.entity_slug)
        if split:
            e.cohort_split_stat_rank = split.stat_rank
            e.cohort_split_casual_rank = split.casual_rank
            e.cohort_split_label = split.label
            cohort_splits_computed += 1

        prior = fetch_prior_year_rank(con, list_slug, e.entity_slug, edition_year)
        if prior is None:
            e.prior_year_rank = None
            e.rank_delta_label = "↑ NEW"
        else:
            e.prior_year_rank = prior
            delta = prior - e.rank
            if delta == 0:
                e.rank_delta_label = "→"
            elif delta > 0:
                e.rank_delta_label = f"↑ {delta}"
            else:
                e.rank_delta_label = f"↓ {-delta}"
            rank_deltas_computed += 1

        enriched.append(e)

    # 4) Validate. Paragraphs (top entries) and one-liners (all entries).
    items: list[tuple[str, str | None, str]] = []
    paragraphs_validated = 0
    oneliners_validated = 0
    for e in enriched:
        items.append((f"{e.entity_slug}::oneliner", e.summary_short, "oneliner"))
        oneliners_validated += 1
        if e.editorial_paragraph:
            items.append((f"{e.entity_slug}::paragraph",
                          e.editorial_paragraph, "paragraph"))
            paragraphs_validated += 1
    val = batch_validate(items)

    # 5) Persist.
    replace_entries(con, list_slug, enriched)
    record_revision_history(con, list_slug, edition_year, enriched)

    # Update entry_count on the list_meta row to match what landed.
    con.execute(
        "UPDATE canon_lists SET entry_count = ? WHERE list_slug = ?",
        (len(enriched), list_slug),
    )
    con.commit()

    # 6) Effort buckets — declared by the seed module per entry.
    effort = seed_authored.effort_buckets_for(list_slug)

    return GenerationReport(
        list_slug=list_slug,
        entry_count=len(enriched),
        paragraphs_validated=paragraphs_validated,
        oneliners_validated=oneliners_validated,
        validator_passed=len(val["passed"]),
        validator_failed=len(val["failed"]),
        validator_failed_labels=val["failed_labels"],
        pass_rate=val["rate"],
        cohort_splits_computed=cohort_splits_computed,
        rank_deltas_computed=rank_deltas_computed,
        effort_buckets=effort,
    )


# ---------------------------------------------------------------------------
# Sprint v5-1.5 — batch-ready scaffold (no-op until LLM path enabled)
# ---------------------------------------------------------------------------

_CANON_BATCH_SYSTEM = """You are writing one entry for a college football Canon list — a curated, \
opinionated ranked editorial product. The list's editorial contract is shared across every \
entry: same voice register, same word-count band, same constraints on attribution + \
comparative markers.

Each user message will carry the per-entry rank + display name + raw stat context. Your output \
for each entry is a JSON object with keys:
  "summary_short" (one-liner, <= 18 words, no marketing language)
  "editorial_paragraph" (3-5 sentences, fan-voice, 80-140 words, at least one comparative marker)
Return ONLY the JSON. No preamble. No markdown fences.
"""


def regenerate_entries_batch(
    con: sqlite3.Connection,
    list_slug: str,
    *,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 600,
    _meter: "Any" = None,
) -> dict[str, int]:
    """Batch LLM regeneration of one Canon list's entries.

    No-op when the list's seed entries are fully hand-authored (the
    current case for all 3 production lists). Reserved as the entry
    point for the dynamic-list path described in the module docstring.

    Submits one Anthropic Batch with a shared cached editorial contract
    + one job per entry. Each entry's user message carries only the
    per-row stat context, keeping the cached prefix dominant in input
    cost.

    ``_meter`` (Pattern A, optional): single meter for the entire batch.
    Currently always a no-op against seed-authored lists; reserved for
    when this path activates against dynamic lists.
    """
    from cfb_rankings.llm_runtime import CostMeter
    meter = _meter or CostMeter(
        ceiling_usd=2.0,
        label=f"canon.{list_slug}",
    )
    from cfb_rankings.llm_runtime_batch import BatchJob, submit_batch_offline_safe

    raw_entries = seed_authored.entries_for(list_slug)
    if not raw_entries:
        return {"list_slug": 0, "batched": 0, "updated": 0, "mode": "noop_no_entries"}

    # All current lists are fully seed-authored — we don't actually want
    # to overwrite hand-tuned copy. Skip when paragraphs are already
    # populated. The condition becomes more permissive when this path
    # gets activated for dynamic lists.
    needing_regen = [e for e in raw_entries if not (e.editorial_paragraph and e.summary_short)]
    if not needing_regen:
        return {"list_slug": len(raw_entries), "batched": 0, "updated": 0, "mode": "noop_all_authored"}

    jobs: list[BatchJob] = []
    for e in needing_regen:
        custom_id = f"canon-{list_slug}-{e.entity_slug}"
        user_prompt = (
            f"List: {list_slug}\n"
            f"Rank: {e.rank}\n"
            f"Entity: {e.entity_display_name} ({e.entity_slug})\n"
            f"Program label: {e.program_label}\n"
            f"Prior-year rank: {e.prior_year_rank if e.prior_year_rank is not None else 'NEW'}\n"
            "Write the entry now."
        )
        jobs.append(BatchJob(
            custom_id=custom_id,
            system_blocks=[
                {
                    "type": "text",
                    "text": _CANON_BATCH_SYSTEM,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                },
            ],
            messages=[{"role": "user", "content": user_prompt}],
            model=model,
            max_tokens=max_tokens,
            metadata={"entity_slug": e.entity_slug, "list_slug": list_slug},
        ))

    results = submit_batch_offline_safe(jobs, run_voice_validator=False)
    updated = 0
    # Real activation of this path would persist the updates back into the
    # entries list via replace_entries; here we just count the successes
    # because the seed-authored lists shouldn't be overwritten by LLM.
    for r in results:
        # Record batch cost. CostCeilingExceeded propagates out.
        if r.succeeded and (r.input_tokens or r.output_tokens):
            meter.record(
                r.model_used or model,
                {
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "cache_creation_input_tokens": int(r.cache_creation_input_tokens or 0),
                    "cache_read_input_tokens": int(r.cache_read_input_tokens or 0),
                },
                is_batch=True,
                cache_ttl="1h",
                note=f"canon.{list_slug}.{r.metadata.get('entity_slug')}",
            )
        if r.succeeded and r.text:
            updated += 1
    return {
        "list_slug": len(raw_entries),
        "batched": len(jobs),
        "updated": updated,
        "mode": "batch_dry_run",
    }
