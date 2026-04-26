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
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

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
