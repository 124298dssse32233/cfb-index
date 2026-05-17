"""Command-K search foundation (Sprint v5-11.5 pre-work).

Builds the searchable index JSON that the future Cmd-K overlay will
fetch. Spec: docs/octopus/v5_11_5_sprint_brief.md §"Part 3 — Command-K
spec."

The index is intentionally a single static JSON file (~500KB-1MB) so
the client fetches once + searches client-side. No server-side search
endpoint needed. Indexed item categories:

  * Teams       — every team_id with a slug (FBS + FCS + DII/DIII)
  * Profiles    — every slug with a file in `profiles/*.md`
  * Players     — current-season active rosters (filtered, not all 130k+)
  * Editions    — daily + mailbag + edition records
  * Conferences — every active conference
  * Methodology — pages under `/methodology/`

Public API:
    from cfb_rankings.cmdk import (
        SearchItem,
        ItemKind,
        build_search_index,
        write_search_index,
        index_teams,
        index_profiles,
        index_players,
        index_editions,
        index_conferences,
        index_methodology,
    )

The wire-up into the global header overlay (cmdk.js + cmdk.css) is
Window A's lane. This package only ships the index builder.
"""

from .types import (
    ItemKind,
    SearchItem,
    KIND_VALUES,
)
from .index_builder import (
    build_search_index,
    write_search_index,
    index_teams,
    index_profiles,
    index_players,
    index_editions,
    index_conferences,
    index_methodology,
)

__all__ = [
    "ItemKind",
    "SearchItem",
    "KIND_VALUES",
    "build_search_index",
    "write_search_index",
    "index_teams",
    "index_profiles",
    "index_players",
    "index_editions",
    "index_conferences",
    "index_methodology",
]
