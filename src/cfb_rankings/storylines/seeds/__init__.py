"""Storyline thread seed modules.

Each seed module owns one thread. The module exports:
    THREAD   — dict matching storyline_threads schema
    CHAPTERS — list of dicts matching storyline_chapters schema (excluding id)

The `_metadata` module is the single source of truth for the 8 thread
metadata records and is what Phase 1 of Sprint 10 inserts. Phase 2 fills
the per-slug `*.py` modules with chapter content.

`THREAD_SEED_MODULES` is the registry the loader iterates. Adding a
thread means: append a record to `_metadata.THREADS`, create a sibling
module here, and add it to the registry below.
"""
from __future__ import annotations

from . import _metadata

# Per-slug chapter modules. Each is imported lazily by the loader so a
# missing module just yields zero chapters for that thread (used during
# Phase 1 metadata-only seeding).
_CHAPTER_MODULE_NAMES: tuple[str, ...] = (
    "twelve_team_playoff_settling",
    "realignment_endgame",
    "saban_to_deboer",
    "big_ten_reasserting",
    "nd_usc_rivalry_recalibrating",
    "coaching_carousel_2026_27",
    "vandy_renaissance",
    "portal_era_settling",
)


def iter_thread_metadata():
    """Yield the 8 thread metadata dicts."""
    yield from _metadata.THREADS


def iter_chapter_modules():
    """Yield (thread_slug, chapters_list) per registered chapter module.

    Modules that don't exist yet are skipped silently — Phase 1 runs
    before Phase 2 has authored any chapter content.
    """
    import importlib

    for module_name in _CHAPTER_MODULE_NAMES:
        try:
            module = importlib.import_module(
                f"cfb_rankings.storylines.seeds.{module_name}"
            )
        except ImportError:
            continue
        chapters = getattr(module, "CHAPTERS", None)
        thread_slug = getattr(module, "THREAD_SLUG", None)
        if not chapters or not thread_slug:
            continue
        yield thread_slug, chapters
