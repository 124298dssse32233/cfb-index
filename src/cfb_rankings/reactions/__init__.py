"""The Reaction Story — Sprint 15.

Auto-fires when a Wire entry crosses a velocity threshold. Synthesizes the
news event into a quantified cohort-divergence piece: what stat folks said
vs. casual fans vs. die-hards, and why the split matters.

Public API:
    from cfb_rankings.reactions import triggers, synthesizer, renderer
    from cfb_rankings.reactions.triggers import check_triggers
    from cfb_rankings.reactions.synthesizer import generate_reaction
    from cfb_rankings.reactions.renderer import render_all, render_story
"""
from __future__ import annotations
