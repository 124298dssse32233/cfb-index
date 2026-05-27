"""Idempotent upserts for the team-preview tables.

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §1, §11.

All writes go through ``Database.upsert_many`` keyed on the unique indexes from
the migrations, so re-running any builder at the same ``as_of_date`` overwrites
rows in place rather than appending duplicates.
"""

from __future__ import annotations

import json
from typing import Any

from cfb_rankings.team_preview.evidence import TeamEvidence
from cfb_rankings.team_preview.season_path import SeasonPathProjection


def upsert_preview_snapshot(db: Any, ev: TeamEvidence, *, snapshot_kind: str = "offseason") -> None:
    row = {
        "team_id": ev.team_id,
        "slug": ev.slug,
        "season_year": ev.season_year,
        "as_of_date": ev.as_of_date,
        "snapshot_kind": snapshot_kind,
        "prior_season_year": ev.prior_season_year,
        "prior_wins": ev.prior_wins,
        "prior_losses": ev.prior_losses,
        "prior_ties": ev.prior_ties,
        "prior_final_ap_rank": ev.prior_final_ap_rank,
        "prior_final_coaches_rank": ev.prior_final_coaches_rank,
        "prior_final_cfp_rank": ev.prior_final_cfp_rank,
        "conference_id": ev.conference_id,
        "conference_name": ev.conference_name,
        "is_independent": 1 if ev.is_independent else 0,
        "schedule_known": 1 if ev.schedule_known else 0,
        "first_game_id": ev.first_game_id,
        "first_game_start_utc": ev.first_game_start_utc,
        "first_game_opponent_id": ev.first_game_opponent_id,
        "first_game_opponent_name": ev.first_game_opponent_name,
        "power_prior_rating": ev.power_prior_rating,
        "resume_prior_rating": ev.resume_prior_rating,
        "talent_rank": ev.talent_rank,
        "talent_score": ev.talent_score,
        "recruiting_rank": ev.recruiting_rank,
        "recruiting_score": ev.recruiting_score,
        "returning_total": ev.returning_total,
        "returning_offense": ev.returning_offense,
        "returning_defense": ev.returning_defense,
        "returning_qb": ev.returning_qb,
        "returning_ol": ev.returning_ol,
        "transfer_in_count": ev.transfer_in_count,
        "transfer_out_count": ev.transfer_out_count,
        "transfer_net_count": ev.transfer_net_count,
        "drafted_count": ev.drafted_count,
        "draft_capital_lost": ev.draft_capital_lost,
        "confidence_band": ev.confidence_band,
        "missing_sources_json": json.dumps(ev.missing_sources),
        "source_fingerprint": ev.source_fingerprint,
    }
    db.upsert_many(
        "team_preview_snapshot",
        [row],
        conflict_columns=["team_id", "season_year", "as_of_date", "snapshot_kind"],
        update_columns=[c for c in row if c not in
                        ("team_id", "season_year", "as_of_date", "snapshot_kind")],
    )
    # updated_at_utc is not in the row dict; bump it explicitly.
    db.execute(
        "update team_preview_snapshot set updated_at_utc = datetime('now') "
        "where team_id = :t and season_year = :s and as_of_date = :d and snapshot_kind = :k",
        {"t": ev.team_id, "s": ev.season_year, "d": ev.as_of_date, "k": snapshot_kind},
    )


def upsert_season_path(
    db: Any, slug: str, team_id: int, season_year: int, as_of_date: str,
    projections: list[SeasonPathProjection], source_fingerprint: str | None = None,
) -> None:
    rows = []
    for p in projections:
        rows.append({
            "team_id": team_id,
            "slug": slug,
            "season_year": season_year,
            "as_of_date": as_of_date,
            "scenario": p.scenario,
            "regular_season_wins": p.regular_season_wins,
            "regular_season_losses": p.regular_season_losses,
            "conference_title_game": 1 if p.conference_title_game else 0,
            "conference_title_result": p.conference_title_result,
            "bowl_or_cfp_path": p.bowl_or_cfp_path,
            "postseason_wins": p.postseason_wins,
            "postseason_losses": p.postseason_losses,
            "final_wins": p.final_wins,
            "final_losses": p.final_losses,
            "final_ties": p.final_ties,
            "path_label": p.path_label,
            "rationale": p.rationale,
            "model_version": p.model_version,
            "confidence_band": p.confidence_band,
            "source_fingerprint": source_fingerprint,
        })
    db.upsert_many(
        "team_season_path_projection",
        rows,
        conflict_columns=["team_id", "season_year", "as_of_date", "scenario", "model_version"],
    )


def upsert_transfer_position_rows(db: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    db.upsert_many(
        "team_transfer_position_snapshot",
        rows,
        conflict_columns=["team_id", "season_year", "as_of_date", "position"],
    )


def upsert_roster_reload(db: Any, row: dict[str, Any]) -> None:
    if "summary_json" in row and not isinstance(row["summary_json"], str):
        row["summary_json"] = json.dumps(row["summary_json"])
    db.upsert_many(
        "team_roster_reload_snapshot",
        [row],
        conflict_columns=["team_id", "season_year", "as_of_date"],
    )


def upsert_bowl_ledger_rows(db: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    db.upsert_many(
        "team_bowl_record_ledger",
        rows,
        conflict_columns=["slug", "source_name"],
        update_columns=[c for c in rows[0] if c not in ("slug", "source_name")],
    )
    # Bump updated_at_utc only for the (slug, source_name) rows we just wrote —
    # NOT every row in the table. A blanket UPDATE would rewrite the timestamp
    # of untouched teams on every import, destroying its meaning.
    for r in rows:
        db.execute(
            "update team_bowl_record_ledger set updated_at_utc = datetime('now') "
            "where slug = :s and source_name = :src",
            {"s": r["slug"], "src": r["source_name"]},
        )
