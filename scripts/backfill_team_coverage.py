"""One-time backfill: populate team_coverage from the 6 cohort source structures.

Per DECISIONS.md#D-016 (team_coverage migration) + specs/01-foundation-unblock.md.
Run after migration `20260602_05_team_coverage.sql` has been applied.

Sources (matches the migration docstring + source_origin enum):

    PROFILED_SLUGS               → tier='authored'
    seeds/priority_teams.yaml    → tier='priority_intelligence' (uses rank_priority)
    TOP_ENTITIES_FULL            → tier='pulse_full'
    TOP_ENTITIES_PARTIAL         → tier='pulse_partial'
    BLUEBLOOD_PROGRAMS           → tier='blueblood_pedigree'
    STRUCTURAL_PRIMARIES         → tier='structural_identity' (writes archetype_slug)

Idempotent via the UNIQUE(team_slug, tier) constraint — reruns no-op via
INSERT OR IGNORE. To force a full refresh, DELETE FROM team_coverage first.

Usage:

    python scripts/backfill_team_coverage.py
    python scripts/backfill_team_coverage.py --delete-first
    python scripts/backfill_team_coverage.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cfb_rankings.config import AppConfig
from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations


def _load_priority_teams_yaml() -> list[dict]:
    import yaml
    path = _REPO / "seeds" / "priority_teams.yaml"
    if not path.exists():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return doc.get("teams", []) or []


def _slugify(name: str) -> str:
    """Local slugifier sized to the current priority_teams.yaml values.

    Intentionally simple: lowercase + space→hyphen + strip ' and '.'. Does
    NOT call `cfb_rankings.utils.slugify` because that pipeline does
    aggressive transforms (`st.` → `state`, drops `university`/`college`,
    `&` → `and`) that would diverge from PROFILED_SLUGS and BLUEBLOOD_PROGRAMS
    for edge cases like "Texas A&M". If the YAML grows beyond simple
    ASCII names, pick ONE canonical slugifier and migrate every reader at
    once — do not paper over the divergence here.
    """
    return name.lower().replace(" ", "-").replace("'", "").replace(".", "")


def _gather_rows() -> list[dict]:
    """Collect every (slug, tier, origin) row we will insert."""
    rows: list[dict] = []

    # 1. authored — PROFILED_SLUGS
    from cfb_rankings.team_pages.profile_loader import PROFILED_SLUGS
    for slug in sorted(PROFILED_SLUGS):
        rows.append({
            "team_slug": slug,
            "tier": "authored",
            "source_origin": "profiled_yaml",
            "archetype_slug": None,
            "rank_priority": None,
            "notes": None,
        })

    # 2. priority_intelligence — seeds/priority_teams.yaml
    for t in _load_priority_teams_yaml():
        slug = _slugify(t.get("team_name") or "")
        if not slug:
            continue
        rows.append({
            "team_slug": slug,
            "tier": "priority_intelligence",
            "source_origin": "priority_teams_yaml",
            "archetype_slug": None,
            "rank_priority": t.get("rank_priority"),
            "notes": None,
        })

    # 3 + 4. pulse_full / pulse_partial — TOP_ENTITIES_*
    from cfb_rankings.team_pages.pulse_state import (
        TOP_ENTITIES_FULL, TOP_ENTITIES_PARTIAL,
    )
    for slug in sorted(TOP_ENTITIES_FULL):
        rows.append({
            "team_slug": slug,
            "tier": "pulse_full",
            "source_origin": "top_entities_full",
            "archetype_slug": None,
            "rank_priority": None,
            "notes": None,
        })
    for slug in sorted(TOP_ENTITIES_PARTIAL):
        rows.append({
            "team_slug": slug,
            "tier": "pulse_partial",
            "source_origin": "top_entities_partial",
            "archetype_slug": None,
            "rank_priority": None,
            "notes": None,
        })

    # 5. blueblood_pedigree — BLUEBLOOD_PROGRAMS
    from cfb_rankings.ingest.archetypes import BLUEBLOOD_PROGRAMS
    for slug in sorted(BLUEBLOOD_PROGRAMS):
        rows.append({
            "team_slug": slug,
            "tier": "blueblood_pedigree",
            "source_origin": "blueblood_programs",
            "archetype_slug": None,
            "rank_priority": None,
            "notes": None,
        })

    # 6. structural_identity — STRUCTURAL_PRIMARIES (dict: slug → archetype_slug)
    from cfb_rankings.ingest.archetypes import STRUCTURAL_PRIMARIES
    for slug, archetype_slug in sorted(STRUCTURAL_PRIMARIES.items()):
        rows.append({
            "team_slug": slug,
            "tier": "structural_identity",
            "source_origin": "structural_primaries",
            "archetype_slug": archetype_slug,
            "rank_priority": None,
            "notes": None,
        })

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delete-first", action="store_true",
                        help="Truncate team_coverage before insert (force-refresh).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show row counts per tier without writing.")
    args = parser.parse_args()

    config = AppConfig.from_env()
    db = Database(config.database_url)
    apply_runtime_migrations(db)

    # Sanity check: table must exist post-migration.
    if not db.query_one(
        "select name from sqlite_master where type='table' and name='team_coverage'"
    ):
        print("ERROR: team_coverage table missing — migration not applied", file=sys.stderr)
        return 2

    rows = _gather_rows()

    by_tier: dict[str, int] = {}
    for r in rows:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
    print(f"Gathered {len(rows)} rows across {len(by_tier)} tiers:")
    for tier, n in sorted(by_tier.items()):
        print(f"  {tier:24s} {n:>4d}")

    if args.dry_run:
        print("--dry-run set; no writes performed")
        return 0

    if args.delete_first:
        db.execute("delete from team_coverage")
        print("Truncated team_coverage")

    before = db.query_one("select count(*) as n from team_coverage")["n"]
    # Batched insert — 213 rows trivially small but execute_many is one fsync
    # vs N, and INSERT OR IGNORE makes reruns no-op on UNIQUE(slug, tier).
    db.execute_many(
        """
        insert or ignore into team_coverage (
            team_slug, tier, source_origin, archetype_slug,
            rank_priority, notes
        ) values (
            :team_slug, :tier, :source_origin, :archetype_slug,
            :rank_priority, :notes
        )
        """,
        rows,
    )
    after = db.query_one("select count(*) as n from team_coverage")["n"]
    inserted = after - before
    skipped = len(rows) - inserted
    print(f"Inserted {inserted} new rows; {skipped} were already present")

    total = db.query_one("select count(*) as n from team_coverage")["n"]
    distinct_slugs = db.query_one(
        "select count(distinct team_slug) as n from team_coverage"
    )["n"]
    print(f"team_coverage now has {total} rows covering {distinct_slugs} distinct team_slug values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
