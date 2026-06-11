"""Discourse keyness — the Language Layer engine.

Computes per-team distinctive vocabulary ("The Lexicon") from the fan-voice
corpus via weighted log-odds with an informative Dirichlet prior, and stores it
in ``team_discourse_terms`` for the team-page Lexicon module.

Public entry point: :func:`cfb_rankings.discourse.keyness.compute_team_keyness`.
"""
from __future__ import annotations

from .keyness import MODEL_VERSION, compute_team_keyness

__all__ = ["compute_team_keyness", "MODEL_VERSION"]
