"""Team page renderer (v1.0, CFP-era scope).

Companion to src/cfb_rankings/reporting.py — reporting.py is the legacy 17.5k
line HTML generator; this module is the new clean path for the world-class
team-page rebuild. Nothing here imports reporting.py and vice-versa.

See TEAM_PAGE_WORLD_CLASS_BRIEF.md + TEAM_PAGE_ITERATION_LOG.md for the design
rationale. See migrations/20260424_05_team_pages_schema.sql for the schema.

Public entry points:

* ``render_team_page(db, slug, output_dir)`` — top-level render.
* ``resolve_state(profile, today, last_game, record, rank)`` — sentience.
* ``load_profile(slug)`` — read a ``profiles/<slug>.md`` file into a dict.
* ``generate_state_of_team(profile, state, context, model)`` — LLM-backed
  paragraph generator with deterministic template fallback.
"""
from __future__ import annotations

from .renderer import render_team_page, render_all_profiled_pages
from .state_resolver import PageState, resolve_state
from .profile_loader import load_profile, Profile, PROFILED_SLUGS

__all__ = [
    "render_team_page",
    "render_all_profiled_pages",
    "resolve_state",
    "PageState",
    "load_profile",
    "Profile",
    "PROFILED_SLUGS",
]
