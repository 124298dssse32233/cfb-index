"""Receipts + The Long-Shot That Hit infrastructure (Sprint 13).

Modules:
    extract        — predictive-claim extraction over the corpus
    consensus      — historical consensus snapshots (Vegas/polls/SP+/corpus)
    surprise       — Surprise Index quantification
    resolve        — outcome resolution (auto + editorial)
    best_calls     — annual canonical list ("25 Best Calls of <year>") editorial
    source_profiles— per-source profile pages
    render         — receipts surface rendering
    voice_validator— banned-phrase / voice-contract check
    seed           — manual + chronicle/canon seed extraction
    runtime        — shared helpers (DB connection, slug normalization, paths)

Editorial framing rules (from EDITORIAL_POSITIONING_AND_CONTENT_TYPES.md):
    1. Celebratory not gotcha.
    2. Quantification mandatory — every claim displays its Surprise Index.
    3. Verbatim quotes — the original take is shown unedited.
    4. Named sources — never anonymous; we're crediting predictors.
    5. Aged-poorly takes are framed gently — "before the season turned"
       not "they were wrong about everything."
"""
from __future__ import annotations

__all__ = [
    "extract",
    "consensus",
    "surprise",
    "resolve",
    "best_calls",
    "source_profiles",
    "render",
    "voice_validator",
    "seed",
    "runtime",
]
