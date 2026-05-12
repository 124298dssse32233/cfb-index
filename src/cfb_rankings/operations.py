from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from time import sleep
from typing import Any

from cfb_rankings.audit import (
    write_archive_readiness_audit,
    write_awards_archive_audit,
    write_data_coverage_audit,
    write_player_archive_audit,
)
from cfb_rankings.clients.cfbd import CfbdClient
from cfb_rankings.config import AppConfig
from cfb_rankings.db import Database
from cfb_rankings.integrity import (
    write_competition_integrity_audit,
    write_program_history_integrity_audit,
)
from cfb_rankings.reporting import audit_site_links


# Link-audit severity thresholds. Tiered rather than binary because a real
# site of 67k pages will always have a small surface of long-tail dead
# links (e.g. small-school teams without ranking pages, draft picks whose
# canon player pages haven't been built). A binary 0/>0 check makes the
# maintenance validator permanently FAIL and the daily P0 alert noise out
# the genuinely-urgent failures.
LINK_AUDIT_WARN_THRESHOLD = 50
LINK_AUDIT_FAIL_THRESHOLD = 500


SEASON_STAGE_LABELS: tuple[tuple[str, str], ...] = (
    ("teamBackfill", "Team/Game Backfill"),
    ("teamSeasonSync", "Season Team Sync"),
    ("playerContext", "Player Context"),
    ("gamePlayerStats", "Game Player Stats"),
)

GLOBAL_STAGE_LABELS: tuple[tuple[str, str], ...] = (
    ("honorsImport", "Honors Import"),
    ("publishedBuild", "Published Build"),
    ("coverageAudit", "Coverage Audit"),
    ("playerArchiveAudit", "Player Archive Audit"),
    ("awardsArchiveAudit", "Awards Archive Audit"),
    ("historyStatus", "History Status"),
)


def check_cfbd_connectivity(config: AppConfig, season: int) -> dict[str, Any]:
    if not config.cfbd_api_key:
        return {
            "ok": False,
            "code": "missing_api_key",
            "message": "CFBD_API_KEY is not configured.",
        }

    client = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
    try:
        rankings = client.get_rankings(year=season, week=1, season_type="regular")
    except Exception as exc:
        text = str(exc)
        code = "request_failed"
        if "blocked" in text.lower() or "WinError 10013" in text:
            code = "network_blocked"
        elif "HTTP 401" in text or "HTTP 403" in text:
            code = "auth_failed"
        return {
            "ok": False,
            "code": code,
            "message": text,
        }

    return {
        "ok": True,
        "code": "ok",
        "message": f"CFBD connectivity check succeeded for season {season}.",
        "payload_count": len(rankings or []),
    }


def write_history_load_status(
    db: Database,
    output_path: str = "output/history-load-status.md",
    start_season: int | None = None,
    end_season: int | None = None,
) -> str:
    state_path = find_history_load_state_file(start_season=start_season, end_season=end_season)
    lines: list[str] = [
        "# History Load Status",
        "",
        "This file tracks resumable multi-season archive progress.",
        "",
    ]

    if state_path is None:
        inferred_rows = _inferred_history_rows(db, start_season=start_season, end_season=end_season)
        inferred_global_steps = _inferred_global_steps(
            db,
            output_path=output_path,
            start_season=start_season,
            end_season=end_season,
        )
        archive_snapshot_rows = _archive_snapshot_rows(db)
        lines.extend(
            [
                "## Current State",
                "",
                "- No resumable history-load state file was found in `output/logs`.",
                "- Start the archive loader with `powershell -ExecutionPolicy Bypass -File scripts\\load_history_2014_forward.ps1 -StartSeason 2014 -EndSeason 2025` to create one.",
                "- Until a state file exists, this report falls back to inferred progress from the local archive tables.",
                "",
            ]
        )
        _append_inferred_global_steps(lines, db, output_path=output_path, start_season=start_season, end_season=end_season)
        lines.extend([""])
        _append_inferred_progress(lines, inferred_rows)
        lines.extend([""])
        _append_archive_snapshot(lines, db)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _write_history_load_status_sidecar(
            output_path=path,
            state_mode="inferred",
            state_file=None,
            range_start=start_season or 2014,
            range_end=end_season or _archive_max_season(db),
            season_rows=inferred_rows,
            global_steps=inferred_global_steps,
            archive_snapshot_rows=archive_snapshot_rows,
        )
        return str(path)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    season_entries = state.get("seasons") or {}
    global_stages = state.get("globalStages") or {}
    state_start = int(state.get("startSeason") or start_season or 0)
    state_end = int(state.get("endSeason") or end_season or 0)
    season_keys = sorted(int(season) for season in season_entries.keys())
    total_seasons = len(season_keys)
    complete_seasons = sum(
        1
        for season in season_keys
        if all(bool((season_entries.get(str(season)) or {}).get(stage)) for stage, _label in SEASON_STAGE_LABELS)
    )
    local_artifact_steps = _inferred_global_steps(
        db,
        output_path=output_path,
        start_season=state_start or start_season,
        end_season=state_end or end_season,
    )
    inferred_rows = _inferred_history_rows(db, start_season=state_start or start_season, end_season=state_end or end_season)
    archive_snapshot_rows = _archive_snapshot_rows(db)

    lines.extend(
        [
            "## Overview",
            "",
            f"- State file: `{state_path.as_posix()}`",
            f"- Range: `{state_start}` through `{state_end}`",
            f"- Updated: `{state.get('updatedAt') or 'unknown'}`",
            f"- Fully complete seasons: `{complete_seasons}/{total_seasons}`",
            "",
            "## Stage Totals",
            "",
            "| Stage | Complete Seasons |",
            "| --- | ---: |",
        ]
    )
    for stage, label in SEASON_STAGE_LABELS:
        completed = sum(1 for season in season_keys if bool((season_entries.get(str(season)) or {}).get(stage)))
        lines.append(f"| {label} | {completed}/{total_seasons} |")

    lines.extend(
        [
            "",
            "## Global Finish Steps",
            "",
            "| Step | Status |",
            "| --- | --- |",
        ]
    )
    for stage, label in GLOBAL_STAGE_LABELS:
        status = "Complete" if bool(global_stages.get(stage)) else "Pending"
        lines.append(f"| {label} | {status} |")

    lines.extend([""])
    _append_inferred_global_steps(
        lines,
        db,
        output_path=output_path,
        start_season=state_start or start_season,
        end_season=state_end or end_season,
        title="## Local Artifact Check",
        intro="These checks come from local files and archive tables. They help confirm whether the finish-step outputs actually exist on disk.",
    )

    lines.extend(
        [
            "",
            "## Per-Season Progress",
            "",
            "| Season | Team/Game Backfill | Season Team Sync | Player Context | Game Player Stats | Overall |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for season in season_keys:
        row = season_entries.get(str(season)) or {}
        stage_marks = [_stage_mark(bool(row.get(stage))) for stage, _label in SEASON_STAGE_LABELS]
        overall = "Complete" if all(mark == "Done" for mark in stage_marks) else "In Progress"
        lines.append(f"| {season} | {' | '.join(stage_marks)} | {overall} |")

    lines.extend([""])
    _append_inferred_progress(
        lines,
        inferred_rows,
        title="## Inferred Local Progress",
        intro="These checks come directly from the local database and are useful when the checkpoint state may be stale or incomplete.",
    )
    lines.extend([""])
    _append_archive_snapshot(lines, db)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_history_load_status_sidecar(
        output_path=path,
        state_mode="checkpoint",
        state_file=state_path,
        range_start=state_start,
        range_end=state_end,
        season_rows=[
            {
                "seasonYear": season,
                "teamBackfill": bool((season_entries.get(str(season)) or {}).get("teamBackfill")),
                "teamSeasonSync": bool((season_entries.get(str(season)) or {}).get("teamSeasonSync")),
                "playerContext": bool((season_entries.get(str(season)) or {}).get("playerContext")),
                "gamePlayerStats": bool((season_entries.get(str(season)) or {}).get("gamePlayerStats")),
                "overallComplete": all(
                    bool((season_entries.get(str(season)) or {}).get(stage))
                    for stage, _label in SEASON_STAGE_LABELS
                ),
            }
            for season in season_keys
        ],
        global_steps={
            "checkpoint": {
                stage: {
                    "status": "Complete" if bool(global_stages.get(stage)) else "Pending",
                    "label": label,
                }
                for stage, label in GLOBAL_STAGE_LABELS
            },
            "localArtifactCheck": local_artifact_steps,
        },
        archive_snapshot_rows=archive_snapshot_rows,
        inferred_rows=inferred_rows,
        updated_at=str(state.get("updatedAt") or "unknown"),
    )
    return str(path)


def find_history_load_state_file(start_season: int | None = None, end_season: int | None = None) -> Path | None:
    logs_dir = Path("output/logs")
    if not logs_dir.exists():
        return None

    if start_season is not None and end_season is not None:
        explicit = logs_dir / f"history-load-state-{start_season}-{end_season}.json"
        if explicit.exists():
            return explicit

    candidates = sorted(logs_dir.glob("history-load-state-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _append_archive_snapshot(lines: list[str], db: Database) -> None:
    seasons = _archive_snapshot_rows(db)
    if not seasons:
        return

    lines.extend(
        [
            "## Local Archive Snapshot",
            "",
            "| Season | Games | Team Seasons | Rosters | Player Season Stats | Player Game Stats | Honors | Heisman Votes |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in seasons:
        lines.append(
            f"| {int(row['season_year'])} | "
            f"{int(row.get('games') or 0)} | "
            f"{int(row.get('team_seasons') or 0)} | "
            f"{int(row.get('roster_entries') or 0)} | "
            f"{int(row.get('player_season_stats') or 0)} | "
            f"{int(row.get('player_game_stats') or 0)} | "
            f"{int(row.get('player_honors') or 0)} | "
            f"{int(row.get('heisman_vote_results') or 0)} |"
        )


def _archive_snapshot_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select
          s.season_year,
          (select count(*) from games g where g.season_year = s.season_year) as games,
          (select count(*) from team_seasons ts where ts.season_year = s.season_year) as team_seasons,
          (select count(*) from roster_entries re where re.season_year = s.season_year) as roster_entries,
          (select count(*) from player_season_stats pss where pss.season_year = s.season_year) as player_season_stats,
          (select count(*) from player_game_stats pgs where pgs.season_year = s.season_year) as player_game_stats,
          (select count(*) from player_honors ph where ph.season_year = s.season_year) as player_honors,
          (select count(*) from heisman_vote_results hvr where hvr.season_year = s.season_year) as heisman_vote_results
        from seasons s
        where s.season_year >= 2014
        order by s.season_year
        """
    )


def _append_inferred_global_steps(
    lines: list[str],
    db: Database,
    *,
    output_path: str,
    start_season: int | None = None,
    end_season: int | None = None,
    title: str = "## Inferred Finish Steps",
    intro: str = "These checks infer whether the final archive artifacts and audits exist locally, even when no resumable state file is available.",
) -> None:
    steps = _inferred_global_steps(db, output_path=output_path, start_season=start_season, end_season=end_season)
    lines.extend(
        [
            title,
            "",
            intro,
            "",
            "| Step | Status | Evidence |",
            "| --- | --- | --- |",
        ]
    )
    for stage, label in GLOBAL_STAGE_LABELS:
        step = steps.get(stage) or {}
        status = step.get("status") or "Pending"
        evidence = step.get("evidence") or "No local evidence found."
        lines.append(f"| {label} | {status} | {evidence} |")


def _inferred_global_steps(
    db: Database,
    *,
    output_path: str,
    start_season: int | None = None,
    end_season: int | None = None,
) -> dict[str, dict[str, str]]:
    season_floor = start_season or 2014
    season_ceiling = end_season or _archive_max_season(db)
    if season_ceiling < season_floor:
        season_ceiling = season_floor

    awards_row = db.query_one(
        """
        select
          (select count(*) from player_honors where season_year between %(start_season)s and %(end_season)s) as honors_count,
          (select count(*) from heisman_vote_results where season_year between %(start_season)s and %(end_season)s) as heisman_count
        """,
        {"start_season": season_floor, "end_season": season_ceiling},
    ) or {}
    honors_count = int(awards_row.get("honors_count") or 0)
    heisman_count = int(awards_row.get("heisman_count") or 0)

    report_path = Path(output_path)
    site_index = Path("output/site/index.html")
    rankings_page = Path("output/rankings.html")
    integrity_audit = Path("output/competition-integrity-audit.md")
    player_archive_audit = Path("output/player-archive-audit.md")
    awards_archive_audit = Path("output/awards-archive-audit.md")

    return {
        "honorsImport": {
            "status": "Complete" if honors_count > 0 or heisman_count > 0 else "Pending",
            "evidence": f"{honors_count} honors rows and {heisman_count} Heisman vote rows found for {season_floor}-{season_ceiling}.",
        },
        "publishedBuild": _artifact_step(
            status="Complete" if site_index.exists() and rankings_page.exists() else "Pending",
            evidence=_joined_evidence(
                [
                    _artifact_detail(site_index, label="site home"),
                    _artifact_detail(rankings_page, label="rankings page"),
                ]
            ),
        ),
        "coverageAudit": _artifact_step_from_path(integrity_audit, label="competition integrity audit"),
        "playerArchiveAudit": _artifact_step_from_path(player_archive_audit, label="player archive audit"),
        "awardsArchiveAudit": _artifact_step_from_path(awards_archive_audit, label="awards archive audit"),
        "historyStatus": {
            "status": "Complete",
            "evidence": f"Current report target is `{report_path.as_posix()}` and was generated by this command.",
        },
    }


def _artifact_step_from_path(path: Path, *, label: str) -> dict[str, str]:
    return _artifact_step(
        status="Complete" if path.exists() else "Pending",
        evidence=_artifact_detail(path, label=label),
    )


def _artifact_step(*, status: str, evidence: str) -> dict[str, str]:
    return {"status": status, "evidence": evidence}


def _artifact_detail(path: Path, *, label: str) -> str:
    if not path.exists():
        return f"{label} missing (`{path.as_posix()}`)."
    modified = path.stat().st_mtime
    timestamp = datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M")
    return f"{label} present (`{path.as_posix()}`, updated {timestamp})."


def _joined_evidence(parts: list[str]) -> str:
    return " ".join(part for part in parts if part)


def _stage_mark(done: bool) -> str:
    return "Done" if done else "Pending"


def _append_inferred_progress(
    lines: list[str],
    rows: list[dict[str, Any]],
    *,
    title: str = "## Inferred Progress",
    intro: str = "These stage marks are inferred from the local database rather than from the resumable loader state file.",
) -> None:
    if not rows:
        lines.extend([title, "", "- No local seasons were available for inferred progress.", ""])
        return

    total_seasons = len(rows)
    lines.extend(
        [
            title,
            "",
            intro,
            "",
            "| Stage | Complete Seasons |",
            "| --- | ---: |",
        ]
    )
    for stage, label in SEASON_STAGE_LABELS:
        completed = sum(1 for row in rows if bool(row.get(stage)))
        lines.append(f"| {label} | {completed}/{total_seasons} |")

    lines.extend(
        [
            "",
            "| Season | Team/Game Backfill | Season Team Sync | Player Context | Game Player Stats | Awards Layer | Overall |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        awards_mark = _stage_mark(bool(row.get("awardsLayer")))
        stage_marks = [_stage_mark(bool(row.get(stage))) for stage, _label in SEASON_STAGE_LABELS]
        overall = "Complete" if all(mark == "Done" for mark in stage_marks) else "In Progress"
        lines.append(f"| {int(row['season_year'])} | {' | '.join(stage_marks)} | {awards_mark} | {overall} |")


def _inferred_history_rows(
    db: Database,
    start_season: int | None = None,
    end_season: int | None = None,
) -> list[dict[str, Any]]:
    season_floor = start_season or 2014
    archive_max = _archive_max_season(db)
    season_ceiling = end_season or archive_max
    if season_ceiling < season_floor:
        season_ceiling = season_floor

    observed_rows = db.query_all(
        """
        select
          s.season_year,
          (select count(*) from games g where g.season_year = s.season_year) as games,
          (select count(*) from team_seasons ts where ts.season_year = s.season_year) as team_seasons,
          (select count(*) from roster_entries re where re.season_year = s.season_year) as roster_entries,
          (select count(*) from player_season_stats pss where pss.season_year = s.season_year) as player_season_stats,
          (select count(*) from player_usage_season pus where pus.season_year = s.season_year) as player_usage_season,
          (select count(*) from player_value_metrics pvm where pvm.season_year = s.season_year) as player_value_metrics,
          (select count(*) from player_game_stats pgs where pgs.season_year = s.season_year) as player_game_stats,
          (select count(*) from player_honors ph where ph.season_year = s.season_year) as player_honors,
          (select count(*) from heisman_vote_results hvr where hvr.season_year = s.season_year) as heisman_vote_results
        from seasons s
        where s.season_year between %(start_season)s and %(end_season)s
        order by s.season_year
        """,
        {"start_season": season_floor, "end_season": season_ceiling},
    )
    observed_map = {int(row["season_year"]): row for row in observed_rows}
    rows: list[dict[str, Any]] = []
    for season in range(season_floor, season_ceiling + 1):
        row = observed_map.get(season, {})
        games = int(row.get("games") or 0)
        team_seasons = int(row.get("team_seasons") or 0)
        roster_entries = int(row.get("roster_entries") or 0)
        player_season_stats = int(row.get("player_season_stats") or 0)
        player_usage = int(row.get("player_usage_season") or 0)
        player_value = int(row.get("player_value_metrics") or 0)
        player_game_stats = int(row.get("player_game_stats") or 0)
        player_honors = int(row.get("player_honors") or 0)
        heisman_votes = int(row.get("heisman_vote_results") or 0)
        rows.append(
            {
                "season_year": season,
                "teamBackfill": games > 0,
                "teamSeasonSync": team_seasons > 0,
                "playerContext": roster_entries > 0 or player_season_stats > 0 or player_usage > 0 or player_value > 0,
                "gamePlayerStats": player_game_stats > 0,
                "awardsLayer": player_honors > 0 or heisman_votes > 0,
            }
        )
    return rows


def _archive_max_season(db: Database) -> int:
    row = db.query_one(
        """
        select max(season_year) as max_season
        from (
          select season_year from seasons
          union all
          select season_year from games
          union all
          select season_year from player_honors
          union all
          select season_year from heisman_vote_results
        ) season_years
        """
    ) or {}
    return int(row.get("max_season") or 2014)


def refresh_local_health_artifacts(
    db: Database,
    *,
    start_season: int | None = 2014,
    end_season: int | None = None,
    site_dir: str = "output/site",
    output_path: str = "output/local-health-refresh.md",
    skip_link_audit: bool = False,
    verbose: bool = False,
) -> str:
    def emit(message: str) -> None:
        if verbose:
            print(message, flush=True)

    generated: list[tuple[str, str]] = []
    emit("[local-health] writing data coverage audit...")
    generated.append(("Data Coverage Audit", write_data_coverage_audit(db=db)))
    emit("[local-health] writing player archive audit...")
    generated.append(("Player Archive Audit", write_player_archive_audit(db=db)))
    emit("[local-health] writing awards archive audit...")
    generated.append(("Awards Archive Audit", write_awards_archive_audit(db=db)))
    emit("[local-health] writing competition integrity audit...")
    generated.append(("Competition Integrity Audit", write_competition_integrity_audit(db=db)))
    emit("[local-health] writing program history audit...")
    generated.append(("Program History Audit", write_program_history_integrity_audit(db=db)))
    emit("[local-health] writing history load status...")
    generated.append(
        (
            "History Load Status",
            write_history_load_status(
                db=db,
                start_season=start_season,
                end_season=end_season,
            ),
        )
    )
    emit("[local-health] writing archive readiness audit...")
    generated.append(("Archive Readiness Audit", write_archive_readiness_audit(db=db)))

    if skip_link_audit:
        emit("[local-health] skipping site link audit by request.")
        broken_links: list[dict[str, str]] | None = None
    else:
        emit("[local-health] auditing built-site links...")
        broken_links = _audit_site_links_with_retry(site_dir=site_dir, emit=emit)
        emit(f"[local-health] site link audit complete: {len(broken_links)} broken links.")

    model_snapshot = _latest_model_snapshot_summary(db)
    freshness_notes, freshness_commands = _local_health_freshness_notes(
        generated=generated,
        model_snapshot=model_snapshot,
        site_dir=site_dir,
    )
    lines: list[str] = [
        "# Local Health Refresh",
        "",
        "This file is generated by `refresh-local-health` and summarizes the latest local audit pass.",
        "",
        "## Generated Artifacts",
        "",
        "| Artifact | Path | JSON Sidecar | Updated |",
        "| --- | --- | --- | --- |",
    ]
    for label, path_str in generated:
        path = Path(path_str)
        sidecar = path.with_suffix(".json")
        sidecar_cell = f"`{sidecar.as_posix()}`" if sidecar.exists() else "n/a"
        lines.append(f"| {label} | `{path.as_posix()}` | {sidecar_cell} | {_path_timestamp(path)} |")

    lines.extend(
        [
            "",
            "## Model Freshness",
            "",
        ]
    )
    if model_snapshot is None:
        lines.append("- No modeled weekly snapshot is currently available in the local database.")
    else:
        lines.extend(
            [
                f"- Latest power snapshot: season `{model_snapshot['season_year']}` week `{model_snapshot['week']}`",
                f"- Snapshot rows: `{model_snapshot['row_count']}`",
                f"- Latest model run timestamp: `{model_snapshot['created_at']}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Freshness Read",
            "",
        ]
    )
    if freshness_notes:
        lines.extend(f"- {note}" for note in freshness_notes)
    else:
        lines.append("- No obvious freshness drift was detected between the current model snapshot and the published artifacts.")

    lines.extend(
        [
            "",
            "## Freshness Actions",
            "",
        ]
    )
    if freshness_commands:
        lines.extend(f"- `{command}`" for command in freshness_commands)
    else:
        lines.append("- No publish-refresh action is currently required.")

    lines.extend(
        [
            "",
            "## Site Link Audit",
            "",
            f"- Site directory checked: `{Path(site_dir).as_posix()}`",
            f"- Broken internal links: `{'skipped' if broken_links is None else len(broken_links)}`",
            "",
        ]
    )
    if broken_links is None:
        lines.append("- Site link audit was skipped for this run.")
    elif broken_links:
        lines.extend(
            [
                "| File | Href | Reason |",
                "| --- | --- | --- |",
            ]
        )
        for item in broken_links[:25]:
            lines.append(
                f"| {item.get('file') or ''} | {item.get('href') or ''} | {item.get('reason') or ''} |"
            )
        if len(broken_links) > 25:
            lines.extend(["", f"- Additional broken links not shown here: `{len(broken_links) - 25}`"])
    else:
        lines.append("- No broken internal links were detected in the built site.")

    lines.extend(
        [
            "",
            "## Machine-Readable Bundle",
            "",
            "- Structured rollup: `output/maintenance-bundle.json`",
            "- Action queue: `output/maintenance-action-queue.md`",
            "",
            "## Suggested Daily Sequence",
            "",
            "1. Run `powershell -ExecutionPolicy Bypass -File scripts\\safe_refresh_local_health.ps1`.",
            "2. Open `output/local-health-refresh.md` first for the quick read.",
            "3. If needed, drill into `output/archive-readiness-audit.md` and `output/history-load-status.md` for deeper backlog detail.",
            "4. Use the matching `.json` sidecars when an automation or script needs structured maintenance data instead of markdown scraping.",
        ]
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_local_health_sidecar(
        output_path=path,
        generated=generated,
        model_snapshot=model_snapshot,
        freshness_notes=freshness_notes,
        freshness_commands=freshness_commands,
        broken_links=broken_links,
        site_dir=site_dir,
    )
    return str(path)


def validate_maintenance_outputs(
    *,
    output_path: str = "output/maintenance-validation.md",
    local_health_path: str = "output/local-health-refresh.json",
    bundle_path: str = "output/maintenance-bundle.json",
    queue_path: str = "output/maintenance-action-queue.json",
    allow_p0: bool = False,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    local_health = _load_json_check(Path(local_health_path), "Local Health", checks)
    bundle = _load_json_check(Path(bundle_path), "Maintenance Bundle", checks)
    queue = _load_json_check(Path(queue_path), "Maintenance Action Queue", checks)

    if isinstance(local_health, dict):
        site_link_audit = local_health.get("siteLinkAudit") or {}
        if site_link_audit.get("skipped"):
            _append_validation_check(checks, "Site link audit", "WARN", "Site link audit was skipped.")
        else:
            count = int(site_link_audit.get("brokenLinkCount") or 0)
            if count == 0:
                _append_validation_check(checks, "Site link audit", "PASS", "No broken links reported.")
            elif count < LINK_AUDIT_WARN_THRESHOLD:
                _append_validation_check(
                    checks,
                    "Site link audit",
                    "WARN",
                    f"{count} broken links reported (under WARN threshold of {LINK_AUDIT_WARN_THRESHOLD}).",
                )
            elif count < LINK_AUDIT_FAIL_THRESHOLD:
                _append_validation_check(
                    checks,
                    "Site link audit",
                    "WARN",
                    f"{count} broken links reported (cleanup needed; FAIL threshold is {LINK_AUDIT_FAIL_THRESHOLD}).",
                )
            else:
                _append_validation_check(
                    checks,
                    "Site link audit",
                    "FAIL",
                    f"{count} broken links reported (over FAIL threshold of {LINK_AUDIT_FAIL_THRESHOLD}).",
                )

        freshness = local_health.get("freshness") or {}
        _append_validation_check(
            checks,
            "Artifact freshness",
            "PASS" if bool(freshness.get("isFresh")) else "FAIL",
            "Published artifacts are fresh." if bool(freshness.get("isFresh")) else "Freshness drift was reported.",
        )

        for artifact in local_health.get("artifacts", []):
            label = str(artifact.get("label") or "Artifact")
            markdown_path = Path(str(artifact.get("path") or ""))
            _append_validation_check(
                checks,
                f"{label} markdown",
                "PASS" if markdown_path.exists() else "FAIL",
                f"`{markdown_path.as_posix()}` {'exists' if markdown_path.exists() else 'is missing'}.",
            )
            sidecar_value = artifact.get("sidecarPath")
            if sidecar_value:
                _load_json_check(Path(str(sidecar_value)), f"{label} sidecar", checks)

    if isinstance(bundle, dict):
        for artifact in bundle.get("artifacts", []):
            label = str(artifact.get("label") or "Artifact")
            payload = artifact.get("payload")
            if isinstance(payload, dict) and payload.get("parseError"):
                _append_validation_check(
                    checks,
                    f"{label} bundle payload",
                    "FAIL",
                    f"Bundle captured JSON parse error: {payload['parseError']}",
                )
            elif artifact.get("jsonPath") and payload is None:
                _append_validation_check(
                    checks,
                    f"{label} bundle payload",
                    "FAIL",
                    "Bundle sidecar path exists but parsed payload is empty.",
                )
            else:
                _append_validation_check(checks, f"{label} bundle payload", "PASS", "Payload parsed.")

    if isinstance(queue, dict):
        summary = queue.get("summary") or {}
        p0_count = int(summary.get("p0") or 0)
        if p0_count > 0 and not allow_p0:
            _append_validation_check(checks, "P0 action queue", "FAIL", f"{p0_count} P0 actions are open.")
        elif p0_count > 0:
            _append_validation_check(checks, "P0 action queue", "WARN", f"{p0_count} P0 actions are open but allowed.")
        else:
            _append_validation_check(checks, "P0 action queue", "PASS", "No P0 actions are open.")

        for index, action in enumerate(queue.get("actions", []), start=1):
            details = action.get("commandDetails") or []
            missing = [
                str(detail_index)
                for detail_index, detail in enumerate(details, start=1)
                if not all(key in detail for key in ("command", "mode", "networkRequired", "expectedWeight", "safetyRead"))
            ]
            if missing:
                _append_validation_check(
                    checks,
                    f"Action {index} command metadata",
                    "FAIL",
                    "Missing command metadata in detail row(s): " + ", ".join(missing) + ".",
                )
            else:
                _append_validation_check(
                    checks,
                    f"Action {index} command metadata",
                    "PASS",
                    f"{len(details)} command detail rows include safety metadata.",
                )

    fail_count = sum(1 for check in checks if check["status"] == "FAIL")
    warn_count = sum(1 for check in checks if check["status"] == "WARN")
    status = "PASS" if fail_count == 0 else "FAIL"
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Maintenance Validation",
        "",
        "This report validates the generated maintenance JSON layer so automation can trust it.",
        "",
        "## Summary",
        "",
        f"- Status: `{status}`",
        f"- Failures: `{fail_count}`",
        f"- Warnings: `{warn_count}`",
        f"- Checks: `{len(checks)}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        lines.append(f"| {check['name']} | {check['status']} | {check['detail']} |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {
        "generatedAtUtc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "markdownPath": output.as_posix(),
        "status": status,
        "ok": fail_count == 0,
        "summary": {
            "failures": fail_count,
            "warnings": warn_count,
            "checks": len(checks),
        },
        "checks": checks,
    }
    output.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _path_timestamp(path: Path) -> str:
    if not path.exists():
        return "missing"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def _latest_model_snapshot_summary(db: Database) -> dict[str, Any] | None:
    return db.query_one(
        """
        select
          mr.season_year,
          mr.week,
          mr.created_at,
          (
            select count(*)
            from power_ratings_weekly p
            where p.season_year = mr.season_year
              and p.week = mr.week
          ) as row_count
        from model_runs mr
        where exists (
          select 1
          from power_ratings_weekly p
          where p.model_run_id = mr.model_run_id
        )
        order by mr.season_year desc, mr.week desc, mr.model_run_id desc
        limit 1
        """
    )


def _local_health_freshness_notes(
    *,
    generated: list[tuple[str, str]],
    model_snapshot: dict[str, Any] | None,
    site_dir: str,
) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    commands: list[str] = []
    if model_snapshot is None:
        return notes, commands

    snapshot_created_at = _parse_timestamp(str(model_snapshot.get("created_at") or ""))
    site_index = Path(site_dir) / "index.html"
    rankings_page = Path("output/rankings.html")
    history_status = next((Path(path_str) for label, path_str in generated if label == "History Load Status"), None)
    archive_readiness = next((Path(path_str) for label, path_str in generated if label == "Archive Readiness Audit"), None)

    if snapshot_created_at is None:
        notes.append("The latest model run exists, but its timestamp could not be parsed for freshness comparisons.")
        return notes, commands

    site_index_time = _file_mtime_utc(site_index)
    if site_index_time and site_index_time < snapshot_created_at:
        notes.append(
            f"`output/site/index.html` is older than the latest model snapshot ({_path_timestamp_utc(site_index)} vs {_format_utc(snapshot_created_at)})."
        )
        commands.append("powershell -ExecutionPolicy Bypass -File safe_publish_site.ps1")

    rankings_time = _file_mtime_utc(rankings_page)
    if rankings_time and rankings_time < snapshot_created_at:
        notes.append(
            f"`output/rankings.html` is older than the latest model snapshot ({_path_timestamp_utc(rankings_page)} vs {_format_utc(snapshot_created_at)})."
        )
        commands.append("powershell -ExecutionPolicy Bypass -File safe_publish_site.ps1")

    for label, path in (("history status", history_status), ("archive readiness audit", archive_readiness)):
        if path is None:
            continue
        artifact_time = _file_mtime_utc(path)
        if artifact_time and artifact_time < snapshot_created_at:
            notes.append(
                f"The {label} report predates the latest model snapshot ({_path_timestamp_utc(path)} vs {_format_utc(snapshot_created_at)})."
            )

    deduped_commands = list(dict.fromkeys(commands))
    return notes, deduped_commands


def _file_mtime_utc(path: Path) -> datetime | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def _parse_timestamp(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _path_timestamp_utc(path: Path) -> str:
    timestamp = _file_mtime_utc(path)
    if timestamp is None:
        return "missing"
    return _format_utc(timestamp)


def _load_json_check(path: Path, label: str, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not path.exists():
        _append_validation_check(checks, label, "FAIL", f"`{path.as_posix()}` is missing.")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _append_validation_check(checks, label, "FAIL", f"`{path.as_posix()}` is invalid JSON: {exc}.")
        return None
    _append_validation_check(checks, label, "PASS", f"`{path.as_posix()}` parsed successfully.")
    return payload


def _append_validation_check(checks: list[dict[str, Any]], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _write_history_load_status_sidecar(
    *,
    output_path: Path,
    state_mode: str,
    state_file: Path | None,
    range_start: int,
    range_end: int,
    season_rows: list[dict[str, Any]],
    global_steps: dict[str, Any],
    archive_snapshot_rows: list[dict[str, Any]],
    inferred_rows: list[dict[str, Any]] | None = None,
    updated_at: str | None = None,
) -> None:
    payload = {
        "generatedAtUtc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "markdownPath": output_path.as_posix(),
        "stateMode": state_mode,
        "stateFile": None if state_file is None else state_file.as_posix(),
        "range": {
            "startSeason": int(range_start),
            "endSeason": int(range_end),
        },
        "updatedAt": updated_at,
        "seasonRows": season_rows,
        "globalSteps": global_steps,
        "archiveSnapshot": archive_snapshot_rows,
    }
    if inferred_rows is not None:
        payload["inferredRows"] = inferred_rows
    output_path.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _audit_site_links_with_retry(site_dir: str, emit: Any) -> list[dict[str, str]]:
    first_pass = _revalidate_broken_links(site_dir=site_dir, broken_links=audit_site_links(site_dir=site_dir))
    if not first_pass:
        return first_pass

    target_missing_count = sum(1 for item in first_pass if item.get("reason") == "target missing")
    if target_missing_count < 100:
        return first_pass

    emit(
        "[local-health] large target-missing link count detected; retrying once "
        "in case the static tree was mid-refresh."
    )
    sleep(2)
    return _revalidate_broken_links(site_dir=site_dir, broken_links=audit_site_links(site_dir=site_dir))


def _revalidate_broken_links(site_dir: str, broken_links: list[dict[str, str]]) -> list[dict[str, str]]:
    root = Path(site_dir).resolve()
    filtered: list[dict[str, str]] = []
    for item in broken_links:
        if item.get("reason") != "target missing":
            filtered.append(item)
            continue

        file_value = item.get("file") or ""
        href_value = item.get("href") or ""
        if not file_value or not href_value:
            filtered.append(item)
            continue

        href, _, _ = href_value.partition("#")
        href, _, _ = href.partition("?")
        target = (root / file_value).parent.joinpath(href).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            filtered.append(item)
            continue
        if not target.exists():
            filtered.append(item)
    return filtered


def _write_local_health_sidecar(
    *,
    output_path: Path,
    generated: list[tuple[str, str]],
    model_snapshot: dict[str, Any] | None,
    freshness_notes: list[str],
    freshness_commands: list[str],
    broken_links: list[dict[str, str]] | None,
    site_dir: str,
) -> None:
    payload = {
        "generatedAtUtc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "markdownPath": output_path.as_posix(),
        "maintenanceBundlePath": "output/maintenance-bundle.json",
        "maintenanceActionQueuePath": "output/maintenance-action-queue.md",
        "artifacts": [
            {
                "label": label,
                "path": Path(path_str).as_posix(),
                "sidecarPath": _existing_sidecar_path(Path(path_str)),
                "updated": _path_timestamp(Path(path_str)),
                "sidecarUpdated": _path_timestamp(Path(_existing_sidecar_path(Path(path_str)))) if _existing_sidecar_path(Path(path_str)) else None,
            }
            for label, path_str in generated
        ],
        "modelSnapshot": None
        if model_snapshot is None
        else {
            "seasonYear": int(model_snapshot.get("season_year") or 0),
            "week": int(model_snapshot.get("week") or 0),
            "createdAtUtc": str(model_snapshot.get("created_at") or ""),
            "rowCount": int(model_snapshot.get("row_count") or 0),
        },
        "freshness": {
            "notes": freshness_notes,
            "actions": freshness_commands,
            "isFresh": len(freshness_notes) == 0,
        },
        "siteLinkAudit": {
            "siteDir": Path(site_dir).as_posix(),
            "skipped": broken_links is None,
            "brokenLinkCount": None if broken_links is None else len(broken_links),
            "sample": [] if broken_links is None else broken_links[:25],
        },
    }
    sidecar_path = output_path.with_suffix(".json")
    sidecar_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    bundle = _write_maintenance_bundle(local_health=payload, generated=generated)
    _write_maintenance_action_queue(bundle=bundle)


def _existing_sidecar_path(path: Path) -> str | None:
    sidecar = path.with_suffix(".json")
    if not sidecar.exists():
        return None
    return sidecar.as_posix()


def _write_maintenance_bundle(*, local_health: dict[str, Any], generated: list[tuple[str, str]]) -> dict[str, Any]:
    artifact_payloads: list[dict[str, Any]] = []
    for label, path_str in generated:
        markdown_path = Path(path_str)
        sidecar_path = markdown_path.with_suffix(".json")
        parsed_payload: dict[str, Any] | None = None
        if sidecar_path.exists():
            try:
                parsed_payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                parsed_payload = {"parseError": str(exc)}

        artifact_payloads.append(
            {
                "label": label,
                "markdownPath": markdown_path.as_posix(),
                "jsonPath": sidecar_path.as_posix() if sidecar_path.exists() else None,
                "updated": _path_timestamp(markdown_path),
                "jsonUpdated": _path_timestamp(sidecar_path) if sidecar_path.exists() else None,
                "payload": parsed_payload,
            }
        )

    bundle = {
        "generatedAtUtc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "localHealth": local_health,
        "artifacts": artifact_payloads,
    }
    bundle_path = Path("output/maintenance-bundle.json")
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return bundle


def _write_maintenance_action_queue(*, bundle: dict[str, Any]) -> None:
    actions = _maintenance_action_rows(bundle)
    md_path = Path("output/maintenance-action-queue.md")
    json_path = md_path.with_suffix(".json")
    md_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Maintenance Action Queue",
        "",
        "This file is generated by `refresh-local-health` from the machine-readable audit sidecars.",
        "",
        "## Queue",
        "",
    ]
    if actions:
        lines.extend(
            [
                "| Priority | Area | Action | Evidence |",
                "| --- | --- | --- | --- |",
            ]
        )
        for action in actions:
            lines.append(
                f"| {action['priority']} | {action['area']} | {action['title']} | {action['evidence']} |"
            )
    else:
        lines.append("- No immediate maintenance actions were generated.")

    lines.extend(["", "## Suggested Commands", ""])
    command_rows = [
        (action["priority"], action["title"], detail)
        for action in actions
        for detail in action.get("commandDetails", [])
    ]
    if command_rows:
        lines.extend(
            [
                "| Priority | Command | Type | Network | Weight | Source |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for priority, title, detail in command_rows:
            network = "yes" if detail["networkRequired"] else "no"
            lines.append(
                f"| {priority} | `{detail['command']}` | {detail['mode']} | {network} | "
                f"{detail['expectedWeight']} | {title} |"
            )
    else:
        lines.append("- No command-ready actions were generated.")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {
        "generatedAtUtc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "markdownPath": md_path.as_posix(),
        "bundlePath": "output/maintenance-bundle.json",
        "summary": {
            "actionCount": len(actions),
            "p0": sum(1 for action in actions if action["priority"] == "P0"),
            "p1": sum(1 for action in actions if action["priority"] == "P1"),
            "p2": sum(1 for action in actions if action["priority"] == "P2"),
        },
        "actions": actions,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _maintenance_action_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    local_health = bundle.get("localHealth") or {}
    artifacts = {
        str(artifact.get("label") or ""): artifact.get("payload") or {}
        for artifact in bundle.get("artifacts", [])
        if isinstance(artifact, dict)
    }
    actions: list[dict[str, Any]] = []

    site_link_audit = local_health.get("siteLinkAudit") or {}
    broken_links = site_link_audit.get("brokenLinkCount")
    if isinstance(broken_links, int) and broken_links >= LINK_AUDIT_WARN_THRESHOLD:
        # Tiered priority — small counts are cleanup, large counts are structural.
        # See LINK_AUDIT_*_THRESHOLD comment at module top.
        if broken_links >= LINK_AUDIT_FAIL_THRESHOLD:
            priority = "P0"
            title = "Fix broken internal links before trusting the published site."
            evidence = f"{broken_links} broken links were reported (over FAIL threshold {LINK_AUDIT_FAIL_THRESHOLD})."
        else:
            priority = "P1"
            title = "Clean up broken internal links."
            evidence = f"{broken_links} broken links were reported (over WARN threshold {LINK_AUDIT_WARN_THRESHOLD})."
        actions.append(
            _action(
                priority,
                "Publish Health",
                title,
                evidence,
                ["python manage.py audit-links --site-dir output/site --strict"],
                "local-health",
            )
        )

    freshness = local_health.get("freshness") or {}
    if not bool(freshness.get("isFresh", True)):
        actions.append(
            _action(
                "P0",
                "Publish Health",
                "Rebuild published outputs so the site catches up to the database.",
                "; ".join(str(note) for note in freshness.get("notes", [])) or "Freshness drift was detected.",
                [str(command) for command in freshness.get("actions", [])],
                "local-health",
            )
        )

    archive = artifacts.get("Archive Readiness Audit") or {}
    summary = archive.get("summary") or {}
    if int(summary.get("foundationalGapSeasons") or 0) > 0:
        gap_seasons = [
            str(row.get("season_year"))
            for row in archive.get("seasonReadiness", [])
            if row.get("overall_status") == "Foundational gap"
        ]
        actions.append(
            _action(
                "P1",
                "Historical Archive",
                "Restore foundational season and game shells for historical gap years.",
                "Foundational gaps: " + ", ".join(gap_seasons) + ".",
                _commands_containing(archive, "backfill_cfbd_logged.ps1"),
                "archive-readiness",
            )
        )

    player = artifacts.get("Player Archive Audit") or {}
    player_priorities = player.get("recoveryPriorities") or []
    if player_priorities:
        priority_seasons = ", ".join(str(row.get("seasonYear")) for row in player_priorities[:8])
        actions.append(
            _action(
                "P1",
                "Player Archive",
                "Continue FBS player-context and game-player-stat recovery.",
                f"Top priority seasons: {priority_seasons}.",
                _commands_containing(archive, "backfill_player_context_logged.ps1")
                + _commands_containing(archive, "backfill_game_player_stats_logged.ps1"),
                "player-archive",
            )
        )

    awards = artifacts.get("Awards Archive Audit") or {}
    awards_summary = awards.get("summary") or {}
    heisman_only = next(
        (
            int(row.get("seasonCount") or 0)
            for row in awards_summary.get("statusCounts", [])
            if row.get("status") == "Heisman only"
        ),
        0,
    )
    if heisman_only > 0:
        actions.append(
            _action(
                "P1",
                "Awards Archive",
                "Broaden structured awards beyond Heisman-only coverage.",
                f"{heisman_only} seasons are still Heisman-only.",
                _commands_containing(archive, "import-player-honors"),
                "awards-archive",
            )
        )

    competition = artifacts.get("Competition Integrity Audit") or {}
    competition_summary = competition.get("summary") or {}
    placeholder_count = int(competition_summary.get("genericPlaceholderTeamSeasons") or 0)
    if placeholder_count > 0:
        actions.append(
            _action(
                "P2",
                "Competition Integrity",
                "Clean generic placeholder conference rows so team identities read correctly.",
                f"{placeholder_count} team-season rows still use generic FBS/FCS/DII/DIII conference labels.",
                ["python manage.py sync-team-seasons --start-season 2014 --end-season 2025"],
                "competition-integrity",
            )
        )

    same_day_count = int(competition_summary.get("sameDayTeamCollisions") or 0)
    if same_day_count > 0:
        actions.append(
            _action(
                "P2",
                "Competition Integrity",
                "Review same-day team collisions for duplicate or split-source game rows.",
                f"{same_day_count} same-day team collision rows were detected.",
                ["python manage.py audit-competition-integrity --output output/competition-integrity-audit.md"],
                "competition-integrity",
            )
        )

    program = artifacts.get("Program History Audit") or {}
    program_summary = program.get("summary") or {}
    overlap_count = int(program_summary.get("overlappingProgramIdentities") or 0)
    if overlap_count > 0:
        actions.append(
            _action(
                "P2",
                "Program History",
                "Review overlapping program identities before trusting long-arc history pages.",
                f"{overlap_count} overlapping same-name program identity rows were detected.",
                ["python manage.py audit-program-history --output output/program-history-integrity-audit.md"],
                "program-history",
            )
        )

    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    return sorted(actions, key=lambda action: (priority_order.get(str(action["priority"]), 9), str(action["area"])))


def _action(
    priority: str,
    area: str,
    title: str,
    evidence: str,
    commands: list[str],
    source: str,
) -> dict[str, Any]:
    return {
        "priority": priority,
        "area": area,
        "title": title,
        "evidence": evidence,
        "commands": [command for command in commands if command],
        "commandDetails": [_command_detail(command) for command in commands if command],
        "source": source,
    }


def _commands_containing(archive_payload: dict[str, Any], needle: str) -> list[str]:
    return [
        str(command)
        for command in archive_payload.get("suggestedRecoveryCommands", [])
        if needle in str(command)
    ]


def _command_detail(command: str) -> dict[str, Any]:
    normalized = command.lower()
    network_required = any(
        marker in normalized
        for marker in (
            "backfill_cfbd_logged.ps1",
            "backfill_player_context_logged.ps1",
            "backfill_game_player_stats_logged.ps1",
            "sync-team-seasons",
        )
    )
    dry_run = "-dryrun" in normalized or "--dry-run" in normalized
    audit_only = "audit-" in normalized or "refresh-local-health" in normalized
    full_backfill = "backfill" in normalized and not dry_run
    import_manual = "import-player-honors" in normalized

    if dry_run:
        mode = "preview"
        expected_weight = "light"
        safety_read = "Preview only; should not fetch or write source data."
    elif audit_only:
        mode = "audit"
        expected_weight = "light"
        safety_read = "Offline diagnostic command."
    elif import_manual:
        mode = "manual import"
        expected_weight = "medium"
        safety_read = "Requires a curated CSV path before it is runnable."
    elif full_backfill:
        mode = "backfill"
        expected_weight = "heavy"
        safety_read = "Logged heavy job with wrapper preflight; run only when network access is available."
    else:
        mode = "repair"
        expected_weight = "medium" if network_required else "light"
        safety_read = "Maintenance command generated from local audit state."

    return {
        "command": command,
        "mode": mode,
        "networkRequired": network_required,
        "expectedWeight": expected_weight,
        "safetyRead": safety_read,
    }
