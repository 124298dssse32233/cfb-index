"""WS-12: rank WS-02 narrative arcs into an editorial storyline candidate queue.

The narrative-arc machine (``season_narrative_arc``) detects per-team story
tension automatically. The editorial layer (``storyline_threads``) is
hand-authored. This module bridges them: it reads live arcs, ranks them by
``tension_score`` weighted by editorial frame value, dedupes against teams that
an active thread already covers, and writes a *proposed* candidate row per arc.

Per DECISIONS D-020 this is an editor's pull-list, never an auto-publisher. The
populator refreshes ranking fields on every run but preserves ``review_status``
so a human's promoted/dismissed verdict survives the daily cron.
"""
from __future__ import annotations

import json
from typing import Any

from ..db import Database

# Editorial value of each D-010 frame, independent of a single arc's tension.
# A coaching change is inherently more story-worthy than a recruiting blurb even
# at equal tension. Unknown frames fall back to DEFAULT_FRAME_WEIGHT.
FRAME_WEIGHTS: dict[str, float] = {
    "coaching_transition": 1.00,
    "rivalry_reset": 0.90,
    "archetype_transition": 0.85,
    "program_tier_shift": 0.80,
    "portal_class_arrival": 0.75,
    "cfp_projection": 0.70,
    "recruiting_class_arrival": 0.65,
    "coordinator_transition": 0.60,
    "nil_collective_shift": 0.55,
    "expectation_recalibration": 0.50,
}
DEFAULT_FRAME_WEIGHT = 0.50

# An arc whose team is already covered by an active editorial thread is still
# surfaced (the arc may add a fresh beat) but heavily de-prioritised so net-new
# stories float to the top of the queue.
COVERED_PENALTY = 0.25

# Only arcs that are still live are worth pitching as new editorial.
_CANDIDATE_ARC_STATUSES = ("open", "closure_eligible")


def latest_arc_season(db: Database) -> int | None:
    """Newest season_year that has any live arc.

    The arc populator stamps arcs for the *upcoming* season (e.g. 2026 mid-2026),
    while the daily CI computes SEASON as the last completed season in the
    offseason. A bare `--season=2025` would then find an empty arc table and
    silently no-op; this lets the caller fall back to where the arcs actually are.
    """
    row = db.query_one(
        "select max(season_year) as y from season_narrative_arc "
        "where status in ({statuses})".format(
            statuses=", ".join(f"'{s}'" for s in _CANDIDATE_ARC_STATUSES)
        ),
        {},
    )
    if not row or row.get("y") is None:
        return None
    return int(row["y"])


def _active_thread_coverage(db: Database) -> dict[str, str]:
    """Map team_slug -> thread_slug for every team an active thread already covers."""
    coverage: dict[str, str] = {}
    rows = db.query_all(
        "select thread_slug, primary_program_slugs from storyline_threads "
        "where status = 'active'",
        {},
    )
    for row in rows:
        raw = row.get("primary_program_slugs") or "[]"
        try:
            slugs = json.loads(raw)
        except (TypeError, ValueError):
            slugs = []
        for slug in slugs:
            # First active thread to claim a slug wins the attribution.
            coverage.setdefault(str(slug), str(row["thread_slug"]))
    return coverage


def _headline_hint(frame: str, team_slug: str | None) -> str:
    label = (team_slug or "team").replace("-", " ").title()
    pretty_frame = frame.replace("_", " ")
    return f"{label}: {pretty_frame}"


def populate_storyline_candidates(
    db: Database,
    season_year: int,
    *,
    commit: bool = False,
) -> dict[str, Any]:
    """Rank live narrative arcs for ``season_year`` into storyline candidates.

    Returns a summary dict. With ``commit=False`` (default) nothing is written —
    the caller can inspect ``candidates_ranked`` to preview the queue.
    """
    def _fetch(season: int) -> list[dict[str, Any]]:
        return db.query_all(
            """
            select a.arc_id, a.team_id, a.season_year, a.frame, a.status,
                   a.tension_score, a.confirming_evidence_count,
                   t.slug as team_slug
              from season_narrative_arc a
              left join teams t on t.team_id = a.team_id
             where a.season_year = :season
               and a.status in ({statuses})
            """.format(
                statuses=", ".join(f"'{s}'" for s in _CANDIDATE_ARC_STATUSES)
            ),
            {"season": season},
        )

    arcs = _fetch(season_year)
    arc_season = season_year
    if not arcs:
        fallback = latest_arc_season(db)
        if fallback is not None and fallback != season_year:
            arc_season = fallback
            arcs = _fetch(fallback)

    coverage = _active_thread_coverage(db)

    rows: list[dict[str, Any]] = []
    for arc in arcs:
        frame = str(arc["frame"])
        team_slug = arc.get("team_slug")
        tension = float(arc.get("tension_score") or 0.0)
        frame_weight = FRAME_WEIGHTS.get(frame, DEFAULT_FRAME_WEIGHT)
        covered_by = coverage.get(team_slug) if team_slug else None

        priority = tension * frame_weight
        if covered_by:
            priority *= COVERED_PENALTY

        rows.append(
            {
                "candidate_id": str(arc["arc_id"]),
                "arc_id": str(arc["arc_id"]),
                "team_id": int(arc["team_id"]),
                "team_slug": team_slug,
                "season_year": int(arc["season_year"]),
                "frame": frame,
                "arc_status": str(arc["status"]),
                "tension_score": round(tension, 4),
                "frame_weight": frame_weight,
                "priority_score": round(priority, 4),
                "confirming_evidence_count": int(arc.get("confirming_evidence_count") or 0),
                "covered_by_thread": covered_by,
                "review_status": "proposed",
                "headline_hint": _headline_hint(frame, team_slug),
            }
        )

    rows.sort(key=lambda r: r["priority_score"], reverse=True)

    summary: dict[str, Any] = {
        "season_year": season_year,
        "arc_season": arc_season,
        "arcs_scanned": len(arcs),
        "candidates_ranked": len(rows),
        "covered_count": sum(1 for r in rows if r["covered_by_thread"]),
        "rows_written": 0,
        "top": [(r["candidate_id"], r["priority_score"]) for r in rows[:5]],
    }

    if commit and rows:
        # Refresh ranking fields but PRESERVE review_status + created_at_utc so an
        # editor's verdict and the original surfacing time both survive re-runs.
        db.upsert_many(
            "storyline_candidate",
            rows,
            conflict_columns=["candidate_id"],
            update_columns=[
                "arc_id",
                "team_id",
                "team_slug",
                "season_year",
                "frame",
                "arc_status",
                "tension_score",
                "frame_weight",
                "priority_score",
                "confirming_evidence_count",
                "covered_by_thread",
                "headline_hint",
            ],
        )
        # review_status + created_at_utc are intentionally NOT in update_columns,
        # so an editor's verdict and the original surfacing time survive re-runs.
        # Bump updated_at_utc on every row we just refreshed.
        db.execute(
            "update storyline_candidate set updated_at_utc = datetime('now') "
            "where season_year = :season",
            {"season": season_year},
        )
        summary["rows_written"] = len(rows)

    return summary
