from __future__ import annotations

import time

from cfb_rankings.clients.cfbd import CfbdClient
from cfb_rankings.db import Database
from cfb_rankings.models.heisman import HeismanModelRunner
from cfb_rankings.models.power import PowerModelRunner
from cfb_rankings.models.resume import ResumeModelRunner


def run_weekly_models(
    db: Database,
    model_version: str,
    season: int,
    through_week: int,
    cfbd_client: CfbdClient | None = None,
    include_heisman: bool = True,
) -> int:
    overall_start = time.time()
    _log_progress(
        f"Starting weekly model pipeline for season {season} through week {through_week} "
        f"using version {model_version}."
    )
    notes = "Combined Power + Resume + Heisman run" if include_heisman else "Combined Power + Resume run"
    model_run_row = db.query_one(
        """
        insert into model_runs (model_name, model_version, season_year, week, data_cutoff_utc, notes)
        values ('weekly-rankings', %(model_version)s, %(season)s, %(week)s, CURRENT_TIMESTAMP, %(notes)s)
        returning model_run_id
        """,
        {
            "model_version": model_version,
            "season": season,
            "week": through_week,
            "notes": notes,
        },
    )
    if model_run_row is None:
        raise RuntimeError("Failed to create weekly model run")

    model_run_id = int(model_run_row["model_run_id"])
    _log_progress(f"Created model run {model_run_id}.")
    try:
        power_runner = PowerModelRunner(db, model_version)
        power_start = time.time()
        _log_progress("Power model started.")
        weekly_states = power_runner.run(model_run_id, season, through_week)
        _log_progress(f"Power model finished in {time.time() - power_start:.1f}s.")

        resume_runner = ResumeModelRunner(db, model_version)
        resume_start = time.time()
        _log_progress("Resume model started.")
        resume_runner.run(model_run_id, season, through_week, weekly_states)
        _log_progress(f"Resume model finished in {time.time() - resume_start:.1f}s.")

        if include_heisman:
            heisman_runner = HeismanModelRunner(db, model_version)
            heisman_start = time.time()
            _log_progress("Heisman model started.")
            heisman_runner.run(
                model_run_id=model_run_id,
                season=season,
                through_week=through_week,
                cfbd_client=cfbd_client,
            )
            _log_progress(f"Heisman model finished in {time.time() - heisman_start:.1f}s.")
        _log_progress(
            f"Weekly model pipeline finished successfully in {time.time() - overall_start:.1f}s."
        )
        return model_run_id
    except Exception as exc:
        _log_progress(f"Model pipeline failed: {exc}. Cleaning up partial model run {model_run_id}.")
        _cleanup_model_run(db, model_run_id)
        raise


def _cleanup_model_run(db: Database, model_run_id: int) -> None:
    child_tables = [
        "team_rating_deltas",
        "game_predictions",
        "strength_of_record_benchmarks",
        "resume_ratings_weekly",
        "power_ratings_weekly",
        "heisman_rankings_weekly",
        "conference_strength_weekly",
        "level_strength_weekly",
    ]
    for table in child_tables:
        db.execute(f"delete from {table} where model_run_id = %(model_run_id)s", {"model_run_id": model_run_id})
    db.execute("delete from model_runs where model_run_id = %(model_run_id)s", {"model_run_id": model_run_id})


def _log_progress(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[models][{timestamp}] {message}", flush=True)
