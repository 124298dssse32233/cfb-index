"""Canonical query surface for ``team_coverage`` (per DECISIONS.md#D-016).

D-016 consolidates 6 disjoint cohort structures into one queryable table.
During execution (2026-05-28, session 4) we discovered the literal
"delete the constants, all readers query the table" framing is partly
infeasible: ``scripts/backfill_team_coverage.py`` and ``sync_team_coverage``
below *import* the authoring constants to populate the table, so inverting
them into table-readers would create a circular bootstrap. ``classify_team``
in ``ingest/archetypes.py`` is also a pure function with no ``db`` handle.

Resolved interpretation (see D-016 execution note):

* The authoring constants stay the **source of truth** — they're the edit
  point and the bootstrap input. ``profiles/*.md`` likewise stays the
  source of truth for the ``authored`` tier.
* ``team_coverage`` is a **derived, denormalized read surface**. It is
  re-synced from the authoring sources on every build (wired into
  ``reporting.build_static_site``), so it cannot drift.
* New, *cross-cutting* consumers — anything that needs to ask "what is
  team X's coverage across all dimensions?" or "give me every team in
  tier Y" — query this module instead of importing 6 Python structures.
  The existing per-dimension authoring consumers keep their constants.

The 6 tiers and their authoring sources:

    authored               ← team_pages.profile_loader.PROFILED_SLUGS (profiles/*.md)
    priority_intelligence  ← seeds/priority_teams.yaml (carries rank_priority)
    pulse_full             ← team_pages.pulse_state.TOP_ENTITIES_FULL
    pulse_partial          ← team_pages.pulse_state.TOP_ENTITIES_PARTIAL
    blueblood_pedigree     ← ingest.archetypes.BLUEBLOOD_PROGRAMS
    structural_identity    ← ingest.archetypes.STRUCTURAL_PRIMARIES (carries archetype_slug)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Slug normalization — see _slugify docstring for why this is local.
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Local slugifier sized to the current priority_teams.yaml values.

    Intentionally simple: lowercase + space→hyphen + strip ``'`` and ``.``.
    Does NOT call ``cfb_rankings.utils.slugify`` because that pipeline does
    aggressive transforms (``st.`` → ``state``, drops ``university``/
    ``college``, ``&`` → ``and``) that would diverge from PROFILED_SLUGS and
    BLUEBLOOD_PROGRAMS for edge cases like "Texas A&M". If the YAML grows
    beyond simple ASCII names, pick ONE canonical slugifier and migrate every
    reader at once — do not paper over the divergence here.
    """
    return name.lower().replace(" ", "-").replace("'", "").replace(".", "")


def _load_priority_teams_yaml() -> list[dict[str, Any]]:
    import yaml

    path = _REPO / "seeds" / "priority_teams.yaml"
    if not path.exists():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return doc.get("teams", []) or []


# ---------------------------------------------------------------------------
# Gather: read every authoring source into the row shape team_coverage wants.
# ---------------------------------------------------------------------------

def gather_rows() -> list[dict[str, Any]]:
    """Collect every (slug, tier, origin) row from the authoring sources.

    Pure read of the authoring constants/files — no DB access — so the
    backfill can bootstrap the table from a clean slate.
    """
    rows: list[dict[str, Any]] = []

    # 1. authored — PROFILED_SLUGS (filesystem-derived from profiles/*.md)
    from cfb_rankings.team_pages.profile_loader import PROFILED_SLUGS
    for slug in sorted(PROFILED_SLUGS):
        rows.append({
            "team_slug": slug, "tier": "authored",
            "source_origin": "profiled_yaml",
            "archetype_slug": None, "rank_priority": None, "notes": None,
        })

    # 2. priority_intelligence — seeds/priority_teams.yaml
    for t in _load_priority_teams_yaml():
        slug = _slugify(t.get("team_name") or "")
        if not slug:
            continue
        rows.append({
            "team_slug": slug, "tier": "priority_intelligence",
            "source_origin": "priority_teams_yaml",
            "archetype_slug": None, "rank_priority": t.get("rank_priority"),
            "notes": None,
        })

    # 3 + 4. pulse_full / pulse_partial — TOP_ENTITIES_*
    from cfb_rankings.team_pages.pulse_state import (
        TOP_ENTITIES_FULL, TOP_ENTITIES_PARTIAL,
    )
    for slug in sorted(TOP_ENTITIES_FULL):
        rows.append({
            "team_slug": slug, "tier": "pulse_full",
            "source_origin": "top_entities_full",
            "archetype_slug": None, "rank_priority": None, "notes": None,
        })
    for slug in sorted(TOP_ENTITIES_PARTIAL):
        rows.append({
            "team_slug": slug, "tier": "pulse_partial",
            "source_origin": "top_entities_partial",
            "archetype_slug": None, "rank_priority": None, "notes": None,
        })

    # 5. blueblood_pedigree — BLUEBLOOD_PROGRAMS
    from cfb_rankings.ingest.archetypes import BLUEBLOOD_PROGRAMS
    for slug in sorted(BLUEBLOOD_PROGRAMS):
        rows.append({
            "team_slug": slug, "tier": "blueblood_pedigree",
            "source_origin": "blueblood_programs",
            "archetype_slug": None, "rank_priority": None, "notes": None,
        })

    # 6. structural_identity — STRUCTURAL_PRIMARIES (dict: slug → archetype_slug)
    from cfb_rankings.ingest.archetypes import STRUCTURAL_PRIMARIES
    for slug, archetype_slug in sorted(STRUCTURAL_PRIMARIES.items()):
        rows.append({
            "team_slug": slug, "tier": "structural_identity",
            "source_origin": "structural_primaries",
            "archetype_slug": archetype_slug, "rank_priority": None, "notes": None,
        })

    return rows


# ---------------------------------------------------------------------------
# Sync: atomically refresh the whole table from the authoring sources.
# ---------------------------------------------------------------------------

_INSERT_SQL = """
    insert into team_coverage (
        team_slug, tier, source_origin, archetype_slug, rank_priority, notes
    ) values (
        :team_slug, :tier, :source_origin, :archetype_slug, :rank_priority, :notes
    )
"""


def sync_team_coverage(db: Database) -> dict[str, int]:
    """Full-refresh ``team_coverage`` from the authoring sources, atomically.

    Truncate-and-reinsert (not INSERT OR IGNORE) so a slug *removed* from an
    authoring constant is removed from the table too — INSERT OR IGNORE only
    ever adds. The delete + insert run in a single transaction, so a crash
    mid-sync rolls back rather than leaving the table empty.

    Returns per-tier row counts. Safe to call on every build: pure-Python
    gather + one tiny transaction (~200 rows).
    """
    rows = gather_rows()
    with db.connection() as conn:
        conn.execute("delete from team_coverage")
        if rows:
            conn.executemany(_INSERT_SQL.strip(), rows)
        conn.commit()

    by_tier: dict[str, int] = {}
    for r in rows:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
    return by_tier


# ---------------------------------------------------------------------------
# Read helpers — the unified query surface for cross-cutting consumers.
# ---------------------------------------------------------------------------

def slugs_in_tier(db: Database, tier: str) -> set[str]:
    """Every team_slug in ``tier`` (e.g. 'blueblood_pedigree')."""
    return {
        r["team_slug"]
        for r in db.query_all(
            "select team_slug from team_coverage where tier = :tier",
            {"tier": tier},
        )
    }


def coverage_tiers(db: Database, slug: str) -> set[str]:
    """Every tier a given team belongs to (0..6)."""
    return {
        r["tier"]
        for r in db.query_all(
            "select tier from team_coverage where team_slug = :slug",
            {"slug": slug},
        )
    }


def archetype_for(db: Database, slug: str) -> str | None:
    """The structural-identity archetype_slug for a team, or None."""
    row = db.query_one(
        "select archetype_slug from team_coverage "
        "where team_slug = :slug and tier = 'structural_identity'",
        {"slug": slug},
    )
    return row["archetype_slug"] if row else None


__all__ = [
    "gather_rows",
    "sync_team_coverage",
    "slugs_in_tier",
    "coverage_tiers",
    "archetype_for",
]
