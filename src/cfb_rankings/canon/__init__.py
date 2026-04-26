"""The Canon — annual canonical lists for CFB Index.

Sprint 11 ships three lists at v1:
  * ``the-100-best-players-cfp-era`` — 100 entries (top 25 with editorial paragraphs)
  * ``the-50-most-defining-games-cfp-era`` — 50 entries (top 15 with editorial paragraphs)
  * ``the-25-best-coaching-hires-2020s`` — 25 entries (all with editorial paragraphs)

Public surface (entry points used by the CLI and homepage):

    from cfb_rankings.canon import (
        LIST_SLUGS,
        seed_list_metadata,
        generate_canon_list,
        render_canon_list,
        render_canon_index,
        render_all_canon,
        load_featured_entry,
    )

The module is disjoint from ``team_pages``, ``editions``, ``storylines``,
``wire``, ``receipts``. It reads from ``profiles/*.md`` and the SQLite
database; it never imports from those sibling modules.
"""
from __future__ import annotations

# Public list slugs (canonical IDs used everywhere — CLI, JSON, templates).
LIST_SLUGS: tuple[str, ...] = (
    "the-100-best-players-cfp-era",
    "the-50-most-defining-games-cfp-era",
    "the-25-best-coaching-hires-2020s",
)

# Lazy re-exports — keep the import-time graph small. Importing
# ``cfb_rankings.canon`` for the slug tuple should not pull in YAML, the
# editorial seed module, or sqlite3.
def __getattr__(name: str):
    if name in {
        "seed_list_metadata", "generate_canon_list",
    }:
        from .generator import seed_list_metadata, generate_canon_list
        return {
            "seed_list_metadata": seed_list_metadata,
            "generate_canon_list": generate_canon_list,
        }[name]
    if name in {
        "render_canon_list", "render_canon_index", "render_all_canon",
    }:
        from .renderer import (
            render_canon_list, render_canon_index, render_all_canon,
        )
        return {
            "render_canon_list": render_canon_list,
            "render_canon_index": render_canon_index,
            "render_all_canon": render_all_canon,
        }[name]
    if name == "load_featured_entry":
        from .data import load_featured_entry
        return load_featured_entry
    raise AttributeError(f"module 'cfb_rankings.canon' has no attribute {name!r}")
