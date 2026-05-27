"""Roster-reload builders: transfer position flow + reload summary.

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §2.3, §3.4, §10.

The hard requirement: portal ADDITIONS and portal LOSSES stay separate at the
position level — never collapsed into a single net number. Returning production,
draft loss, and recruiting reload are distinct signals layered on top.
"""

from __future__ import annotations

from typing import Any

_POSITION_FALLBACK = "UNK"


def build_transfer_position_rows(
    db: Any, slug: str, team_id: int, season_year: int, as_of_date: str,
) -> list[dict[str, Any]]:
    """One row per position: incoming vs outgoing portal flow, kept separate."""
    incoming = db.query_all(
        """
        select coalesce(nullif(trim(position), ''), :unk) position,
               count(*) c, avg(transfer_points) avg_pts, sum(transfer_points) tot_pts,
               max(transfer_points) top_pts
        from transfer_entries
        where season_year = :s and to_team_id = :t
        group by 1
        """,
        {"s": season_year, "t": team_id, "unk": _POSITION_FALLBACK},
    )
    outgoing = db.query_all(
        """
        select coalesce(nullif(trim(position), ''), :unk) position,
               count(*) c, avg(transfer_points) avg_pts, sum(transfer_points) tot_pts,
               max(transfer_points) top_pts
        from transfer_entries
        where season_year = :s and from_team_id = :t
        group by 1
        """,
        {"s": season_year, "t": team_id, "unk": _POSITION_FALLBACK},
    )
    inc = {r["position"]: r for r in incoming}
    out = {r["position"]: r for r in outgoing}

    rows: list[dict[str, Any]] = []
    for position in sorted(set(inc) | set(out)):
        i = inc.get(position)
        o = out.get(position)
        in_count = int(i["c"]) if i else 0
        out_count = int(o["c"]) if o else 0
        in_total = float(i["tot_pts"]) if i and i["tot_pts"] is not None else None
        out_total = float(o["tot_pts"]) if o and o["tot_pts"] is not None else None
        net_points = (in_total or 0.0) - (out_total or 0.0)
        # Starter risk: net outflow of bodies at a position with real production
        # leaving. Need filled: meaningful inflow where outflow was light.
        starter_risk = 1 if (out_count - in_count) >= 2 else 0
        need_filled = 1 if (in_count - out_count) >= 2 else 0
        rows.append({
            "team_id": team_id,
            "slug": slug,
            "season_year": season_year,
            "as_of_date": as_of_date,
            "position": position,
            "incoming_count": in_count,
            "incoming_avg_points": float(i["avg_pts"]) if i and i["avg_pts"] is not None else None,
            "incoming_total_points": in_total,
            "incoming_top_player_name": _top_player(db, season_year, team_id, position, "to") if i else None,
            "incoming_top_player_rating": float(i["top_pts"]) if i and i["top_pts"] is not None else None,
            "outgoing_count": out_count,
            "outgoing_avg_points": float(o["avg_pts"]) if o and o["avg_pts"] is not None else None,
            "outgoing_total_points": out_total,
            "outgoing_top_player_name": _top_player(db, season_year, team_id, position, "from") if o else None,
            "outgoing_top_player_rating": float(o["top_pts"]) if o and o["top_pts"] is not None else None,
            "net_count": in_count - out_count,
            "net_points": round(net_points, 4),
            "production_lost": out_total,
            "production_added": in_total,
            "starter_risk_flag": starter_risk,
            "need_filled_flag": need_filled,
            "confidence_band": "medium" if (in_count + out_count) >= 2 else "low",
        })
    return rows


def _top_player(db: Any, season_year: int, team_id: int, position: str, direction: str) -> str | None:
    col = "to_team_id" if direction == "to" else "from_team_id"
    pos_clause = (
        "coalesce(nullif(trim(te.position), ''), 'UNK') = :pos"
    )
    row = db.query_one(
        f"""
        select coalesce(p.full_name, te.from_team_name, te.to_team_name) name
        from transfer_entries te
        left join players p on p.player_id = te.player_id
        where te.season_year = :s and te.{col} = :t and {pos_clause}
        order by te.transfer_points desc
        limit 1
        """,
        {"s": season_year, "t": team_id, "pos": position},
    )
    return row["name"] if row and row["name"] else None


def build_roster_reload_summary(
    db: Any, slug: str, team_id: int, season_year: int, as_of_date: str,
    position_rows: list[dict[str, Any]], evidence: Any = None,
) -> dict[str, Any]:
    """Team-level reload story derived from the position rows + evidence bundle."""
    total_in = sum(r["incoming_count"] for r in position_rows)
    total_out = sum(r["outgoing_count"] for r in position_rows)
    in_points = sum((r["incoming_total_points"] or 0.0) for r in position_rows)
    out_points = sum((r["outgoing_total_points"] or 0.0) for r in position_rows)

    # Primary pressure = position with the largest net outflow of bodies.
    pressure = max(
        position_rows,
        key=lambda r: (r["outgoing_count"] - r["incoming_count"], r["outgoing_count"]),
        default=None,
    )
    repair = max(
        position_rows,
        key=lambda r: (r["incoming_count"] - r["outgoing_count"], r["incoming_count"]),
        default=None,
    )
    primary_pressure = pressure["position"] if pressure and (pressure["outgoing_count"] - pressure["incoming_count"]) >= 1 else None
    primary_repair = repair["position"] if repair and (repair["incoming_count"] - repair["outgoing_count"]) >= 1 else None

    returning_total = getattr(evidence, "returning_total", None) if evidence else None
    drafted = getattr(evidence, "drafted_count", 0) if evidence else 0

    portal_addition_score = round(in_points, 3)
    portal_loss_score = round(out_points, 3)
    continuity_score = round(returning_total, 3) if returning_total is not None else None
    volatility_score = round((total_in + total_out) / 50.0, 3)  # crude 0..~1 scale
    draft_loss_score = float(drafted)

    summary = {
        "transfer_in_total": total_in,
        "transfer_out_total": total_out,
        "transfer_in_points": round(in_points, 3),
        "transfer_out_points": round(out_points, 3),
        "drafted_count": drafted,
        "returning_total": returning_total,
    }

    return {
        "team_id": team_id,
        "slug": slug,
        "season_year": season_year,
        "as_of_date": as_of_date,
        "returning_profile_label": _returning_label(returning_total),
        "transfer_profile_label": _transfer_label(total_in, total_out),
        "draft_loss_label": _draft_label(drafted),
        "recruiting_reload_label": None,
        "primary_pressure_position": primary_pressure,
        "primary_repair_position": primary_repair,
        "reload_score": None,
        "continuity_score": continuity_score,
        "volatility_score": volatility_score,
        "portal_addition_score": portal_addition_score,
        "portal_loss_score": portal_loss_score,
        "draft_loss_score": draft_loss_score,
        "freshman_injection_score": None,
        "summary_json": summary,
        "confidence_band": "medium" if (total_in + total_out) >= 5 else "low",
    }


def _returning_label(returning_total: float | None) -> str | None:
    if returning_total is None:
        return None
    if returning_total >= 0.65:
        return "High continuity"
    if returning_total >= 0.45:
        return "Moderate continuity"
    return "Low continuity / heavy reload"


def _transfer_label(total_in: int, total_out: int) -> str:
    if total_in == 0 and total_out == 0:
        return "No portal activity recorded"
    if total_in - total_out >= 5:
        return "Net portal importer"
    if total_out - total_in >= 5:
        return "Net portal exporter"
    return "Balanced portal churn"


def _draft_label(drafted: int) -> str | None:
    if not drafted:
        return None
    if drafted >= 6:
        return f"Heavy NFL Draft loss ({drafted})"
    return f"NFL Draft departures ({drafted})"
