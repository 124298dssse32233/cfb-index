"""Prompt-context builders for Tier-1 LLM surfaces.

Each builder in :mod:`cfb_rankings.prompt_context.builders` pulls a
specific shape of proprietary data from the SQLite DB to construct a
context dict for one Tier-1 LLM prompt. The shape of each context dict
is defined by ``DESIGN_AUDIT_2026_05_15_v5_3.md`` Part 4 — the
proprietary-data manifest that makes every Tier-1 surface unfakeable.

Cross-cutting design rules (see audit Part 4 §"Cross-cutting rules"):

1. Always inject prior-N continuity rows of the same surface.
2. Always inject 6-year same-week comparators where applicable.
3. Always inject cohort *transitions*, not static values.
4. Always include verbatim source quotes from ``conversation_documents``.
5. For 17 profiled programs, inject ``signature_metrics_ladder`` current
   values.

Every builder catches :class:`sqlite3.Error` and returns empty / ``None``
for the affected manifest key rather than crashing the whole call. This
lets the prompt-assembly path degrade gracefully when an upstream table
has not yet been populated (or, during early sprints, does not yet
exist).
"""
