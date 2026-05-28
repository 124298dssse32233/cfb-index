"""D-010 narrative arc-frame populator.

Walks the event ledger and opens/closes the 10 LOCKED narrative arc frames
(see DECISIONS.md#D-010) into ``season_narrative_arc``, then rebuilds the
``season_narrative_state`` JSON cache per (team, season).

Each frame is a self-contained detector that returns a list of arc openings.
A detector whose event source is not yet populated returns ``[]`` (with a
reason recorded in the run report), so the populator degrades gracefully during
the offseason and fills in automatically as the upstream data lands — no
schema change or wiring change needed when, e.g., the coordinator feed turns on.

Frames currently backed by live data (offseason 2026): ``portal_class_arrival``,
``archetype_transition``, ``coaching_transition``, ``recruiting_class_arrival``,
``rivalry_reset``. The remaining five (``coordinator_carousel``,
``nil_collective_swing``, ``market_belief_swing``, ``playoff_path_change``,
``dynasty_status_change``) are wired with open/close semantics but their event
sources are empty today, so they emit nothing yet.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from cfb_rankings.db import Database

# The 10 LOCKED frames (DECISIONS.md#D-010). Order is the canonical display order.
ARC_FRAMES: tuple[str, ...] = (
    "coaching_transition",
    "coordinator_carousel",
    "nil_collective_swing",
    "portal_class_arrival",
    "recruiting_class_arrival",
    "rivalry_reset",
    "archetype_transition",
    "market_belief_swing",
    "playoff_path_change",
    "dynasty_status_change",
)

# Human-readable summary fragments per frame, used when surfacing open arcs to
# the Chronicle prompt (the normalised arc rows carry no prose summary).
FRAME_LABELS: dict[str, str] = {
    "coaching_transition": "new head coach taking over",
    "coordinator_carousel": "coordinator change reshaping a unit",
    "nil_collective_swing": "NIL/collective shift reshaping the roster",
    "portal_class_arrival": "a top transfer-portal class arriving",
    "recruiting_class_arrival": "a top recruiting class arriving",
    "rivalry_reset": "a rivalry result reversing the streak",
    "archetype_transition": "the fanbase's identity shifting",
    "market_belief_swing": "the betting market's belief swinging",
    "playoff_path_change": "the playoff path shifting",
    "dynasty_status_change": "the program's dynasty status changing",
}


def arc_summary(frame: str, tension: float) -> str:
    """One-line human-readable summary for an open arc (for the prompt block)."""
    label = FRAME_LABELS.get(frame, frame.replace("_", " "))
    return f"{label} (tension {float(tension):.2f})"


# How many teams a "top-N class secured" frame opens an arc for.
TOP_CLASS_CUTOFF = 25

# Open arcs whose tension is at/above this are surfaced as unresolved tensions.
UNRESOLVED_TENSION_FLOOR = 0.5


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _arc_id(slug: str, season: int, frame: str, discriminator: str | None = None) -> str:
    base = f"{slug}-{season}-{frame.replace('_', '-')}"
    return f"{base}-{discriminator}" if discriminator else base


def _opening(team_id: int, slug: str, season: int, frame: str, week: int,
             tension: float, *, confirming: int = 1, disconfirming: int = 0,
             discriminator: str | None = None) -> dict[str, Any]:
    return {
        "arc_id": _arc_id(slug, season, frame, discriminator),
        "team_id": int(team_id),
        "season_year": int(season),
        "frame": frame,
        "status": "open",
        "opened_at_week": int(week),
        "tension_score": round(float(max(0.0, min(1.0, tension))), 3),
        "confirming_evidence_count": int(confirming),
        "disconfirming_evidence_count": int(disconfirming),
    }


# ---------------------------------------------------------------------------
# Detectors — one per frame. Each returns (openings, reason_when_empty).
# ---------------------------------------------------------------------------


def _detect_portal_class_arrival(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """portal_class_arrival — top-25 incoming portal class by aggregate transfer points."""
    rows = db.query_all(
        """
        select te.to_team_id as team_id, t.slug,
               count(*) as moves, sum(coalesce(te.transfer_points, 0)) as pts
        from transfer_entries te
        join teams t on t.team_id = te.to_team_id and t.level_code = 'FBS'
        where te.season_year = %(season)s and te.to_team_id is not null
        group by te.to_team_id, t.slug
        having pts > 0
        order by pts desc
        limit %(cutoff)s
        """,
        {"season": season, "cutoff": TOP_CLASS_CUTOFF},
    )
    if not rows:
        return [], "no transfer_entries for season"
    top_pts = max(float(r["pts"]) for r in rows) or 1.0
    out = [
        _opening(r["team_id"], str(r["slug"]), season, "portal_class_arrival", week,
                 tension=float(r["pts"]) / top_pts, confirming=int(r["moves"]))
        for r in rows
    ]
    return out, ""


def _detect_recruiting_class_arrival(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """recruiting_class_arrival — top-25 signing class by class rating for this season."""
    rows = db.query_all(
        """
        select re.team_id, t.slug,
               max(coalesce(re.rating, 0)) as class_rating, count(*) as signees
        from recruiting_entries re
        join teams t on t.team_id = re.team_id and t.level_code = 'FBS'
        where re.season_year = %(season)s and re.team_id is not null
        group by re.team_id, t.slug
        having class_rating > 0
        order by class_rating desc
        limit %(cutoff)s
        """,
        {"season": season, "cutoff": TOP_CLASS_CUTOFF},
    )
    if not rows:
        return [], "no recruiting_entries for season"
    top_rating = max(float(r["class_rating"]) for r in rows) or 1.0
    out = [
        _opening(r["team_id"], str(r["slug"]), season, "recruiting_class_arrival", week,
                 tension=float(r["class_rating"]) / top_rating, confirming=int(r["signees"]))
        for r in rows
    ]
    return out, ""


def _detect_archetype_transition(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """archetype_transition — primary fanbase archetype changed season-over-season."""
    rows = db.query_all(
        """
        select a.team_id, t.slug, a.primary_confidence as cur_conf
        from fanbase_classification a
        join fanbase_classification b
          on b.team_id = a.team_id and b.season_year = a.season_year - 1
        join teams t on t.team_id = a.team_id and t.level_code = 'FBS'
        where a.season_year = %(season)s
          and a.primary_archetype_slug <> b.primary_archetype_slug
        """,
        {"season": season},
    )
    if not rows:
        return [], "no season-over-season archetype changes"
    out = [
        _opening(r["team_id"], str(r["slug"]), season, "archetype_transition", week,
                 tension=float(r["cur_conf"] or 0.6))
        for r in rows
    ]
    return out, ""


def _detect_coaching_transition(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """coaching_transition — head coach changed from the prior season."""
    rows = db.query_all(
        """
        select a.team_id, t.slug
        from team_seasons a
        join team_seasons b on b.team_id = a.team_id and b.season_year = a.season_year - 1
        join teams t on t.team_id = a.team_id and t.level_code = 'FBS'
        where a.season_year = %(season)s
          and coalesce(a.head_coach, '') <> ''
          and coalesce(b.head_coach, '') <> ''
          and a.head_coach <> b.head_coach
        """,
        {"season": season},
    )
    if not rows:
        return [], "no head_coach changes (or head_coach unpopulated for season)"
    # A first-year coach is high narrative tension regardless of pedigree.
    out = [
        _opening(r["team_id"], str(r["slug"]), season, "coaching_transition", week, tension=0.75)
        for r in rows
    ]
    return out, ""


def _detect_rivalry_reset(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """rivalry_reset — a rivalry game outcome reversed the prior meeting's winner."""
    meetings = db.query_all(
        """
        select program_a_slug, program_b_slug, season_year, winner_slug
        from team_rivalry_meetings
        where winner_slug is not null and coalesce(is_complete, 0) = 1
        order by program_a_slug, program_b_slug, season_year
        """
    )
    if not meetings:
        return [], "no completed rivalry meetings"
    # Walk each program-pair in chronological order; an arc opens in `season`
    # when that season's meeting flips the immediately-preceding winner.
    last_winner: dict[tuple[str, str], str] = {}
    openings: list[dict[str, Any]] = []
    slug_to_id = _fbs_slug_to_id(db)
    for m in meetings:
        pair = tuple(sorted((str(m["program_a_slug"]), str(m["program_b_slug"]))))
        winner = str(m["winner_slug"])
        prev = last_winner.get(pair)
        if prev is not None and prev != winner and int(m["season_year"]) == season:
            for slug in pair:
                tid = slug_to_id.get(slug)
                if tid is not None:
                    openings.append(
                        _opening(tid, slug, season, "rivalry_reset", week, tension=0.6,
                                 discriminator=[s for s in pair if s != slug][0])
                    )
        last_winner[pair] = winner
    if not openings:
        return [], "no rivalry winner-reversals in season"
    return openings, ""


def _detect_coordinator_carousel(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """coordinator_carousel — OC/DC change. Source columns are unpopulated today."""
    rows = db.query_all(
        """
        select a.team_id, t.slug
        from team_seasons a
        join team_seasons b on b.team_id = a.team_id and b.season_year = a.season_year - 1
        join teams t on t.team_id = a.team_id and t.level_code = 'FBS'
        where a.season_year = %(season)s
          and (
            (coalesce(a.offensive_coordinator, '') <> '' and coalesce(b.offensive_coordinator, '') <> ''
             and a.offensive_coordinator <> b.offensive_coordinator)
            or
            (coalesce(a.defensive_coordinator, '') <> '' and coalesce(b.defensive_coordinator, '') <> ''
             and a.defensive_coordinator <> b.defensive_coordinator)
          )
        """,
        {"season": season},
    )
    if not rows:
        return [], "coordinator fields unpopulated"
    out = [
        _opening(r["team_id"], str(r["slug"]), season, "coordinator_carousel", week, tension=0.55)
        for r in rows
    ]
    return out, ""


def _detect_nil_collective_swing(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """nil_collective_swing — NIL/collective/revenue-share event. No structured source yet."""
    return [], "no NIL event source"


def _detect_market_belief_swing(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """market_belief_swing — implied prob moved >20pp in 4w. prediction_market_snapshots empty."""
    snap = db.query_one("select count(*) as n from prediction_market_snapshots")
    if not snap or int(snap["n"]) == 0:
        return [], "prediction_market_snapshots empty"
    return [], "market-swing detection not yet implemented (source present)"


def _detect_playoff_path_change(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """playoff_path_change — CFP projection shifted >2 seeds. No weekly projection feed yet."""
    return [], "no weekly CFP projection feed"


def _detect_dynasty_status_change(db: Database, season: int, week: int) -> tuple[list[dict[str, Any]], str]:
    """dynasty_status_change — prestige tier crossed 5<->6. team_profiles.program_tier empty."""
    return [], "program_tier unpopulated"


_DETECTORS: dict[str, Callable[[Database, int, int], tuple[list[dict[str, Any]], str]]] = {
    "coaching_transition": _detect_coaching_transition,
    "coordinator_carousel": _detect_coordinator_carousel,
    "nil_collective_swing": _detect_nil_collective_swing,
    "portal_class_arrival": _detect_portal_class_arrival,
    "recruiting_class_arrival": _detect_recruiting_class_arrival,
    "rivalry_reset": _detect_rivalry_reset,
    "archetype_transition": _detect_archetype_transition,
    "market_belief_swing": _detect_market_belief_swing,
    "playoff_path_change": _detect_playoff_path_change,
    "dynasty_status_change": _detect_dynasty_status_change,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fbs_slug_to_id(db: Database) -> dict[str, int]:
    rows = db.query_all(
        "select team_id, slug from teams where level_code = 'FBS' and coalesce(is_active, 1) = 1"
    )
    return {str(r["slug"]): int(r["team_id"]) for r in rows}


# ---------------------------------------------------------------------------
# Populator
# ---------------------------------------------------------------------------


def populate_season_arcs(db: Database, season_year: int, *, week: int = 0,
                         frames: tuple[str, ...] = ARC_FRAMES) -> dict[str, Any]:
    """Open arcs for every active frame and rebuild the per-team state cache.

    Idempotent: arcs key on a deterministic ``arc_id`` so re-running refreshes
    tension/evidence in place without duplicating. Returns a run report with a
    per-frame count and the reason any frame emitted nothing.
    """

    per_frame: dict[str, int] = {}
    reasons: dict[str, str] = {}
    all_openings: list[dict[str, Any]] = []

    for frame in frames:
        detector = _DETECTORS.get(frame)
        if detector is None:
            reasons[frame] = "unknown frame"
            per_frame[frame] = 0
            continue
        openings, reason = detector(db, season_year, week)
        per_frame[frame] = len(openings)
        if not openings:
            reasons[frame] = reason
        all_openings.extend(openings)

    now = _now_iso()
    if all_openings:
        for opening in all_openings:
            opening["updated_at_utc"] = now
        db.upsert_many(
            "season_narrative_arc",
            all_openings,
            conflict_columns=["arc_id"],
            # Preserve opened_at_week + created_at_utc on re-run; refresh the rest.
            update_columns=[
                "status",
                "tension_score",
                "confirming_evidence_count",
                "disconfirming_evidence_count",
                "updated_at_utc",
            ],
        )

    teams_touched = _rebuild_state_cache(db, season_year, now)

    return {
        "season_year": season_year,
        "week": week,
        "arcs_total": len(all_openings),
        "per_frame": per_frame,
        "empty_reasons": reasons,
        "teams_with_state": teams_touched,
    }


def _rebuild_state_cache(db: Database, season_year: int, now: str) -> int:
    """Refresh season_narrative_state JSON blobs from the normalised arc rows."""

    arcs = db.query_all(
        """
        select team_id, arc_id, frame, opened_at_week, status, tension_score
        from season_narrative_arc
        where season_year = %(season)s
        order by team_id, tension_score desc
        """,
        {"season": season_year},
    )
    by_team: dict[int, list[dict[str, Any]]] = {}
    for arc in arcs:
        by_team.setdefault(int(arc["team_id"]), []).append(arc)

    state_rows: list[dict[str, Any]] = []
    for team_id, team_arcs in by_team.items():
        open_arcs = []
        resolved_arcs = []
        unresolved = []
        for arc in team_arcs:
            entry = {
                "arc_id": arc["arc_id"],
                "frame": arc["frame"],
                "opened_week": int(arc["opened_at_week"]),
                "status": arc["status"],
                "tension_score": float(arc["tension_score"]),
            }
            if arc["status"] in ("resolved", "reversed"):
                resolved_arcs.append(entry)
            else:
                open_arcs.append(entry)
                if float(arc["tension_score"]) >= UNRESOLVED_TENSION_FLOOR:
                    unresolved.append({"frame": arc["frame"], "tension_score": float(arc["tension_score"])})
        state_rows.append(
            {
                "team_id": team_id,
                "season_year": season_year,
                "open_arcs_json": json.dumps(open_arcs),
                "resolved_arcs_json": json.dumps(resolved_arcs),
                "unresolved_tensions_json": json.dumps(unresolved),
                "last_reconciled_at_week": 0,
                "last_reconciled_at_utc": now,
                "updated_at_utc": now,
            }
        )

    if state_rows:
        db.upsert_many(
            "season_narrative_state",
            state_rows,
            conflict_columns=["team_id", "season_year"],
            update_columns=[
                "open_arcs_json",
                "resolved_arcs_json",
                "unresolved_tensions_json",
                "last_reconciled_at_week",
                "last_reconciled_at_utc",
                "updated_at_utc",
            ],
        )
    return len(state_rows)
