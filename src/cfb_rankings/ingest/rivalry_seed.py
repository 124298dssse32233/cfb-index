"""Canonical rivalry-pairs seed loader (Rent Free bootstrap).

The rival-mention pipeline had a circular dependency: ``_load_rival_pairs``
read its pair universe from ``rivalry_obsession_weekly``, which is only
written by ``compute-rivalry-ratios``, which reads
``team_week_rival_mentions``, which ``_build_rival_mention_rows`` only
populates for pairs from ``rivalry_obsession_weekly``. An empty table stayed
empty forever. This module loads a static, editorially-curated pair list
(``seeds/rivalry_pairs.yaml``) into the ``rivalry_pairs`` table;
``_load_rival_pairs`` unions it in so the cycle has an entry point.

CLI:
    python manage.py seed-rivalry-pairs [--pairs-file seeds/rivalry_pairs.yaml]
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

DEFAULT_PAIRS_FILE = Path("seeds") / "rivalry_pairs.yaml"


def seed_rivalry_pairs(
    db: Database,
    *,
    pairs_file: Path | str = DEFAULT_PAIRS_FILE,
) -> dict[str, Any]:
    """Upsert canonical rivalry pairs, resolving team slugs to ids.

    Unresolvable slugs are skipped and reported, never guessed — a typo in the
    seed must not silently create a phantom rivalry.
    """
    raw = yaml.safe_load(Path(pairs_file).read_text(encoding="utf-8")) or {}
    entries = raw.get("pairs") or []

    slug_rows = db.query_all("select team_id, slug from teams where slug is not null")
    team_by_slug = {str(r["slug"]): int(r["team_id"]) for r in slug_rows}

    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for entry in entries:
        slug_a = str(entry.get("slug_a") or "").strip()
        slug_b = str(entry.get("slug_b") or "").strip()
        name = str(entry.get("name") or f"{slug_a} / {slug_b}").strip()
        tier = str(entry.get("tier") or "classic").strip()
        team_a_id = team_by_slug.get(slug_a)
        team_b_id = team_by_slug.get(slug_b)
        if team_a_id is None or team_b_id is None or team_a_id == team_b_id:
            unresolved.append(f"{slug_a} vs {slug_b}")
            continue
        # Stable orientation: lower team_id is always team_a, matching
        # compute_rivalry_ratios_from_features' `team_id < rival_team_id` join.
        if team_a_id > team_b_id:
            team_a_id, team_b_id = team_b_id, team_a_id
            slug_a, slug_b = slug_b, slug_a
        rows.append(
            {
                "rivalry_slug": f"{slug_a}-vs-{slug_b}",
                "rivalry_name": name,
                "team_a_id": team_a_id,
                "team_b_id": team_b_id,
                "tier": tier,
                "is_active": 1,
            }
        )

    if rows:
        db.upsert_many(
            "rivalry_pairs",
            rows,
            conflict_columns=["rivalry_slug"],
            update_columns=["rivalry_name", "team_a_id", "team_b_id", "tier", "is_active"],
        )
    if unresolved:
        logger.warning("seed-rivalry-pairs: %d unresolved slugs: %s", len(unresolved), unresolved)
    return {"loaded": len(rows), "unresolved": unresolved}


__all__ = ["seed_rivalry_pairs", "DEFAULT_PAIRS_FILE"]
