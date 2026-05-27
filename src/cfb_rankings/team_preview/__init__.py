"""Deterministic team-preview evidence layer (Milestone A).

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md.

This package is the "truth layer" the 2026 team-preview product sits on. It is
deliberately disjoint from rendering: it gathers deterministic facts, projects
final-season-aware records, and persists them to first-class tables. LLM prose
(Milestone D) and renderer modules (Milestone B/C) consume these rows but never
replace them.

Public builder entrypoints (called by the CLI in cfb_rankings.cli):
  * build_team_preview_snapshots
  * compute_season_path_projections
  * build_roster_reload_snapshots
"""

from __future__ import annotations

from typing import Any

from cfb_rankings.team_preview.evidence import (
    build_norm_context,
    build_team_evidence,
    canonical_fbs_slugs,
    to_season_path_inputs,
)
from cfb_rankings.team_preview.persistence import (
    upsert_preview_snapshot,
    upsert_roster_reload,
    upsert_season_path,
    upsert_transfer_position_rows,
)
from cfb_rankings.team_preview.roster_reload import (
    build_roster_reload_summary,
    build_transfer_position_rows,
)
from cfb_rankings.team_preview.season_path import project_season_path

__all__ = [
    "build_team_preview_snapshots",
    "compute_season_path_projections",
    "build_roster_reload_snapshots",
    "resolve_slugs",
]


def resolve_slugs(slugs: list[str] | None) -> list[str]:
    """Resolve an explicit slug list, or the canonical real-FBS set."""
    return list(slugs) if slugs else sorted(canonical_fbs_slugs())


def build_team_preview_snapshots(
    db: Any, season_year: int, as_of_date: str, slugs: list[str] | None = None,
) -> dict[str, int]:
    """Build + persist team_preview_snapshot for each team. Returns counts."""
    targets = resolve_slugs(slugs)
    norm = build_norm_context(db, season_year)
    written = skipped = 0
    for slug in targets:
        ev = build_team_evidence(db, slug, season_year, as_of_date, norm)
        if ev is None:
            skipped += 1
            continue
        upsert_preview_snapshot(db, ev)
        written += 1
    return {"targets": len(targets), "written": written, "skipped": skipped}


def compute_season_path_projections(
    db: Any, season_year: int, as_of_date: str, slugs: list[str] | None = None,
) -> dict[str, int]:
    """Compute + persist floor/base/ceiling projections for each team."""
    targets = resolve_slugs(slugs)
    norm = build_norm_context(db, season_year)
    written = skipped = 0
    for slug in targets:
        ev = build_team_evidence(db, slug, season_year, as_of_date, norm)
        if ev is None:
            skipped += 1
            continue
        projections = project_season_path(to_season_path_inputs(ev))
        upsert_season_path(
            db, ev.slug, ev.team_id, season_year, as_of_date,
            projections, source_fingerprint=ev.source_fingerprint,
        )
        written += 1
    return {"targets": len(targets), "written": written, "skipped": skipped}


def build_roster_reload_snapshots(
    db: Any, season_year: int, as_of_date: str, slugs: list[str] | None = None,
) -> dict[str, int]:
    """Build + persist transfer position snapshots + roster reload summary."""
    targets = resolve_slugs(slugs)
    norm = build_norm_context(db, season_year)
    written = skipped = position_rows_total = 0
    for slug in targets:
        ev = build_team_evidence(db, slug, season_year, as_of_date, norm)
        if ev is None:
            skipped += 1
            continue
        position_rows = build_transfer_position_rows(
            db, ev.slug, ev.team_id, season_year, as_of_date
        )
        upsert_transfer_position_rows(db, position_rows)
        position_rows_total += len(position_rows)
        summary = build_roster_reload_summary(
            db, ev.slug, ev.team_id, season_year, as_of_date, position_rows, evidence=ev
        )
        upsert_roster_reload(db, summary)
        written += 1
    return {
        "targets": len(targets),
        "written": written,
        "skipped": skipped,
        "position_rows": position_rows_total,
    }
