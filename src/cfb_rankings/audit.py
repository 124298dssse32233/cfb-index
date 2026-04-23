from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

from cfb_rankings.db import Database


MAJOR_TABLES: tuple[tuple[str, str], ...] = (
    ("games", "Games"),
    ("postseason_games", "Postseason Games"),
    ("team_seasons", "Team Seasons"),
    ("roster_entries", "Roster Entries"),
    ("player_season_stats", "Player Season Stats"),
    ("player_usage_season", "Player Usage"),
    ("player_value_metrics", "Player Value Metrics"),
    ("player_game_stats", "Player Game Stats"),
    ("player_honors", "Player Honors"),
    ("heisman_vote_results", "Heisman Vote Results"),
    ("official_rankings", "Official Rankings"),
    ("transfer_entries", "Transfer Portal"),
    ("player_recruiting_profiles", "Player Recruiting"),
)


def write_data_coverage_audit(db: Database, output_path: str = "output/data-coverage-audit.md") -> str:
    rows = _season_coverage_rows(db)
    max_season_row = db.query_one("select max(season_year) as season_year from seasons") or {}
    max_season = int(max_season_row.get("season_year") or 0)
    seasons = list(range(2014, max_season + 1)) if max_season >= 2014 else []

    lines: list[str] = [
        "# Data Coverage Audit",
        "",
        "This file is a local archive health report for the static-site pipeline.",
        "",
        "## Season Coverage",
        "",
        "| Season | Games | Postseason | Team Seasons | Rosters | Player Season Stats | Player Usage | Player Value | Player Game Stats | Honors | Heisman Votes | Official Rankings | Transfers | Recruiting |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    coverage_map = {int(row["season_year"]): row for row in rows}
    for season in seasons:
        row = coverage_map.get(season, {})
        lines.append(
            "| "
            + " | ".join(
                [
                    str(season),
                    str(int(row.get("games") or 0)),
                    str(int(row.get("postseason_games") or 0)),
                    str(int(row.get("team_seasons") or 0)),
                    str(int(row.get("roster_entries") or 0)),
                    str(int(row.get("player_season_stats") or 0)),
                    str(int(row.get("player_usage_season") or 0)),
                    str(int(row.get("player_value_metrics") or 0)),
                    str(int(row.get("player_game_stats") or 0)),
                    str(int(row.get("player_honors") or 0)),
                    str(int(row.get("heisman_vote_results") or 0)),
                    str(int(row.get("official_rankings") or 0)),
                    str(int(row.get("transfer_entries") or 0)),
                    str(int(row.get("player_recruiting_profiles") or 0)),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Gaps To Watch",
            "",
        ]
    )
    gaps = _coverage_gap_lines(rows)
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- No obvious coverage gaps were detected in the major audit tables.")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_data_coverage_sidecar(output_path=path, seasons=seasons, rows=rows, gaps=gaps)
    return str(path)


def write_player_archive_audit(db: Database, output_path: str = "output/player-archive-audit.md") -> str:
    rows = _expand_player_archive_rows(db, _player_archive_rows(db))
    lines: list[str] = [
        "# Player Archive Audit",
        "",
        "This file checks how complete the player-data archive is by season, with an emphasis on the FBS historical layer currently supported by the CFBD backfill workflow.",
        "",
        "## Season Coverage",
        "",
        "| Season | Season Shell | Completed FBS Games | FBS Games With Player Stats | Player-Stat Coverage | FBS Postseason Games | Postseason Games With Player Stats | Rosters | Player Season Stats | Player Usage | Player Value | Honors | Heisman Votes | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in rows:
        completed_games = int(row.get("completed_fbs_games") or 0)
        covered_games = int(row.get("fbs_games_with_player_stats") or 0)
        coverage_pct = 0.0 if completed_games <= 0 else (100.0 * covered_games / completed_games)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(int(row["season_year"])),
                    "Yes" if bool(row.get("season_present")) else "No",
                    str(completed_games),
                    str(covered_games),
                    f"{coverage_pct:.0f}%",
                    str(int(row.get("completed_fbs_postseason_games") or 0)),
                    str(int(row.get("fbs_postseason_games_with_player_stats") or 0)),
                    str(int(row.get("roster_entries") or 0)),
                    str(int(row.get("player_season_stats") or 0)),
                    str(int(row.get("player_usage_season") or 0)),
                    str(int(row.get("player_value_metrics") or 0)),
                    str(int(row.get("player_honors") or 0)),
                    str(int(row.get("heisman_vote_results") or 0)),
                    _player_archive_status(row),
                ]
            )
            + " |"
        )

    status_counts = _player_archive_status_counts(rows)
    priority_rows = _player_archive_priority_rows(rows)

    lines.extend(
        [
            "",
            "## Readiness Summary",
            "",
            "| Status | Seasons |",
            "| --- | ---: |",
        ]
    )
    for status, count in status_counts:
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            "## Recovery Priorities",
            "",
        ]
    )
    if priority_rows:
        lines.extend(
            [
                "| Season | Priority | Why It Matters |",
                "| --- | --- | --- |",
            ]
        )
        for row in priority_rows:
            lines.append(
                f"| {int(row['season_year'])} | {row['priority_label']} | {row['reason']} |"
            )
    else:
        lines.append("- No obvious player-archive recovery priorities were detected.")

    lines.extend(
        [
            "",
            "## Gaps To Watch",
            "",
        ]
    )

    gaps = _player_archive_gap_lines(rows)
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- No obvious player-archive gaps were detected.")

    missing_samples = _missing_player_stat_game_samples(db)
    lines.extend(
        [
            "",
            "## Missing Game Samples",
            "",
        ]
    )
    if missing_samples:
        lines.extend(
            [
                "| Season | Week | Phase | Matchup |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for row in missing_samples:
            lines.append(
                f"| {int(row['season_year'])} | {int(row.get('week') or 0)} | {row.get('season_phase') or 'regular season'} | "
                f"{row['home_team_name']} vs {row['away_team_name']} |"
            )
    else:
        lines.append("- No uncovered completed FBS games were sampled.")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_player_archive_sidecar(
        output_path=path,
        rows=rows,
        status_counts=status_counts,
        priority_rows=priority_rows,
        gaps=gaps,
        missing_samples=missing_samples,
    )
    return str(path)


def write_awards_archive_audit(db: Database, output_path: str = "output/awards-archive-audit.md") -> str:
    rows = _awards_archive_rows(db)
    lines: list[str] = [
        "# Awards Archive Audit",
        "",
        "This file tracks structured player-awards coverage by season. It is meant to answer a different question than the player-stat audit: do we have meaningful honors context, and how broad is it?",
        "",
        "## Season Coverage",
        "",
        "| Season | Season Shell | Honor Rows | Distinct Awards | Distinct Selectors | Heisman Winner Rows | Heisman Finalist Rows | Heisman Vote Rows | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(int(row["season_year"])),
                    "Yes" if bool(row.get("season_present")) else "No",
                    str(int(row.get("honor_rows") or 0)),
                    str(int(row.get("distinct_awards") or 0)),
                    str(int(row.get("distinct_selectors") or 0)),
                    str(int(row.get("heisman_winner_rows") or 0)),
                    str(int(row.get("heisman_finalist_rows") or 0)),
                    str(int(row.get("heisman_vote_rows") or 0)),
                    _awards_archive_status(row),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Coverage Read",
            "",
        ]
    )
    gaps = _awards_archive_gap_lines(rows)
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- No obvious structured-awards gaps were detected.")

    lines.extend(
        [
            "",
            "## Award Labels Present",
            "",
        ]
    )
    labels = _award_label_counts(db)
    if labels:
        lines.extend(
            [
                "| Award Label | Rows |",
                "| --- | ---: |",
            ]
        )
        for row in labels:
            lines.append(f"| {row['honor_name']} | {int(row['row_count'])} |")
    else:
        lines.append("- No structured award labels are currently loaded.")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_awards_archive_sidecar(output_path=path, rows=rows, gaps=gaps, labels=labels)
    return str(path)


def write_archive_readiness_audit(
    db: Database,
    output_path: str = "output/archive-readiness-audit.md",
) -> str:
    coverage_rows = _season_coverage_rows(db)
    player_rows = _expand_player_archive_rows(db, _player_archive_rows(db))
    awards_rows = _awards_archive_rows(db)
    seasons = _archive_seasons(db)
    coverage_map = {int(row["season_year"]): row for row in coverage_rows}
    player_map = {int(row["season_year"]): row for row in player_rows}
    awards_map = {int(row["season_year"]): row for row in awards_rows}
    publish = _published_output_metrics()
    audit_artifacts = _audit_artifact_rows()
    season_readiness_rows = _archive_readiness_rows(seasons, coverage_map, player_map, awards_map)
    ready_seasons = sum(1 for row in season_readiness_rows if row["overall_status"] == "Ready")
    in_progress_seasons = sum(1 for row in season_readiness_rows if row["overall_status"] == "In Progress")
    foundational_gap_seasons = sum(1 for row in season_readiness_rows if row["overall_status"] == "Foundational gap")
    critical_gaps = _archive_readiness_gap_lines(season_readiness_rows)
    next_actions = _archive_next_actions(season_readiness_rows, publish, audit_artifacts)

    lines: list[str] = [
        "# Archive Readiness Audit",
        "",
        "This file is the operator-facing control panel for the local archive. It combines season shells, player layers, awards context, postseason continuity, and publish health into one view.",
        "",
        "## Executive Read",
        "",
        f"- Seasons in archive range: `{len(season_readiness_rows)}`",
        f"- Fully ready seasons: `{ready_seasons}`",
        f"- In-progress seasons: `{in_progress_seasons}`",
        f"- Foundational-gap seasons: `{foundational_gap_seasons}`",
        f"- Team pages built: `{publish['team_pages']}`",
        f"- Program pages built: `{publish['program_pages']}`",
        f"- Player pages built: `{publish['player_pages']}`",
        "",
        "## Publish Footprint",
        "",
        "| Artifact | Status | Evidence |",
        "| --- | --- | --- |",
    ]

    for label, status, evidence in _published_artifact_rows(publish):
        lines.append(f"| {label} | {status} | {evidence} |")

    lines.extend(
        [
            "",
            "## Audit Artifacts",
            "",
            "| Audit | Status | Evidence |",
            "| --- | --- | --- |",
        ]
    )
    for label, status, evidence in audit_artifacts:
        lines.append(f"| {label} | {status} | {evidence} |")

    lines.extend(
        [
            "",
            "## Season Readiness Matrix",
            "",
            "| Season | Competition | Player Layer | Awards Layer | Postseason Player Stats | Overall |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in season_readiness_rows:
        lines.append(
            f"| {row['season_year']} | {row['competition_status']} | {row['player_status']} | "
            f"{row['awards_status']} | {row['postseason_status']} | {row['overall_status']} |"
        )

    lines.extend(
        [
            "",
            "## Critical Gaps",
            "",
        ]
    )
    if critical_gaps:
        lines.extend(f"- {gap}" for gap in critical_gaps)
    else:
        lines.append("- No critical archive blockers were detected.")

    lines.extend(
        [
            "",
            "## Recommended Next Actions",
            "",
        ]
    )
    if next_actions:
        lines.extend(f"- {action}" for action in next_actions)
    else:
        lines.append("- No immediate operator action is required.")

    recovery_commands = _archive_recovery_commands(season_readiness_rows)
    lines.extend(
        [
            "",
            "## Suggested Recovery Commands",
            "",
        ]
    )
    if recovery_commands:
        lines.extend(f"- `{command}`" for command in recovery_commands)
    else:
        lines.append("- No concrete recovery commands were generated for the current archive state.")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_archive_readiness_sidecar(
        output_path=path,
        publish=publish,
        audit_artifacts=audit_artifacts,
        season_readiness_rows=season_readiness_rows,
        critical_gaps=critical_gaps,
        next_actions=next_actions,
        recovery_commands=recovery_commands,
    )
    return str(path)


def _season_coverage_rows(db: Database) -> list[dict[str, int]]:
    return db.query_all(
        """
        with base as (
          select season_year
          from seasons
        )
        select
          b.season_year,
          (select count(*) from games g where g.season_year = b.season_year) as games,
          (select count(*) from games g where g.season_year = b.season_year and g.season_type = 'postseason') as postseason_games,
          (select count(*) from team_seasons ts where ts.season_year = b.season_year) as team_seasons,
          (select count(*) from roster_entries re where re.season_year = b.season_year) as roster_entries,
          (select count(*) from player_season_stats pss where pss.season_year = b.season_year) as player_season_stats,
          (select count(*) from player_usage_season pus where pus.season_year = b.season_year) as player_usage_season,
          (select count(*) from player_value_metrics pvm where pvm.season_year = b.season_year) as player_value_metrics,
          (select count(*) from player_game_stats pgs where pgs.season_year = b.season_year) as player_game_stats,
          (select count(*) from player_honors ph where ph.season_year = b.season_year) as player_honors,
          (select count(*) from heisman_vote_results hvr where hvr.season_year = b.season_year) as heisman_vote_results,
          (select count(*) from official_rankings orw where orw.season_year = b.season_year) as official_rankings,
          (select count(*) from transfer_entries te where te.season_year = b.season_year) as transfer_entries,
          (select count(*) from player_recruiting_profiles prp where prp.season_year = b.season_year) as player_recruiting_profiles
        from base b
        order by b.season_year
        """
    )


def _archive_readiness_rows(
    seasons: list[int],
    coverage_map: dict[int, dict[str, int]],
    player_map: dict[int, dict[str, int | bool]],
    awards_map: dict[int, dict[str, int | bool]],
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for season in seasons:
        coverage = coverage_map.get(season, {})
        player = player_map.get(season, {})
        awards = awards_map.get(season, {})
        games = int(coverage.get("games") or 0)
        team_seasons = int(coverage.get("team_seasons") or 0)
        postseason_games = int(coverage.get("postseason_games") or 0)
        player_status = _player_archive_status(player)
        awards_status = _awards_archive_status(awards)
        player_ready = player_status == "Ready"
        competition_ready = games > 0 and team_seasons > 0
        awards_ready = awards_status not in {"No awards loaded", "Missing season shell"}
        postseason_ready = (
            "Ready"
            if postseason_games == 0
            else (
                "Ready"
                if int(player.get("fbs_postseason_games_with_player_stats") or 0) >= int(player.get("completed_fbs_postseason_games") or 0)
                else "Gap"
            )
        )
        if not competition_ready and player_status in {"Missing season shell", "Unloaded"}:
            overall = "Foundational gap"
        elif competition_ready and player_ready and awards_ready and postseason_ready == "Ready":
            overall = "Ready"
        else:
            overall = "In Progress"

        rows.append(
            {
                "season_year": season,
                "competition_status": "Ready" if competition_ready else "Gap",
                "player_status": player_status,
                "awards_status": awards_status,
                "postseason_status": postseason_ready,
                "overall_status": overall,
            }
        )
    return rows


def _archive_readiness_gap_lines(rows: list[dict[str, str | int]]) -> list[str]:
    gaps: list[str] = []
    missing_foundational = [str(row["season_year"]) for row in rows if row["competition_status"] == "Gap"]
    if missing_foundational:
        gaps.append(
            "Foundational competition data is still missing or incomplete in these seasons: "
            + ", ".join(missing_foundational)
            + "."
        )

    player_gap_years = [
        str(row["season_year"])
        for row in rows
        if str(row["player_status"]) not in {"Ready"}
    ]
    if player_gap_years:
        gaps.append(
            "Game-level or season-level player archive work is still incomplete in these seasons: "
            + ", ".join(player_gap_years)
            + "."
        )

    postseason_gap_years = [
        str(row["season_year"])
        for row in rows
        if str(row["postseason_status"]) == "Gap"
    ]
    if postseason_gap_years:
        gaps.append(
            "Completed postseason games still lack full player-stat attachment in these seasons: "
            + ", ".join(postseason_gap_years)
            + "."
        )

    awards_heisman_only_years = [
        str(row["season_year"])
        for row in rows
        if str(row["awards_status"]) == "Heisman only"
    ]
    if awards_heisman_only_years:
        gaps.append(
            "Structured awards are still Heisman-only in these seasons, so richer honors storytelling is not ready yet: "
            + ", ".join(awards_heisman_only_years)
            + "."
        )
    return gaps


def _archive_next_actions(
    season_rows: list[dict[str, str | int]],
    publish: dict[str, int | str | bool],
    audit_artifacts: list[tuple[str, str, str]],
) -> list[str]:
    actions: list[str] = []
    missing_seasons = [str(row["season_year"]) for row in season_rows if row["overall_status"] == "Foundational gap"]
    player_priority = [str(row["season_year"]) for row in season_rows if str(row["player_status"]) in {"Game shell only", "Player context partial", "Game stats partial", "Game stats partial (postseason missing)", "In progress", "Unloaded", "Missing season shell"}]
    postseason_priority = [str(row["season_year"]) for row in season_rows if str(row["postseason_status"]) == "Gap"]
    if missing_seasons:
        actions.append(
            "When CFBD connectivity is available, restore foundational season/game shells first for: " + ", ".join(missing_seasons) + "."
        )
    if player_priority:
        actions.append(
            "Prioritize player-context and game-player-stat backfills for: " + ", ".join(player_priority[:8]) + "."
        )
    if postseason_priority:
        actions.append(
            "Postseason player-game stats are still the cleanest archive win in: " + ", ".join(postseason_priority[:8]) + "."
        )
    missing_audits = [label for label, status, _evidence in audit_artifacts if status != "Complete"]
    if missing_audits:
        actions.append("Rebuild missing audit outputs: " + ", ".join(missing_audits) + ".")
    if not bool(publish.get("site_home_present")) or not bool(publish.get("rankings_present")):
        actions.append("Re-run `python manage.py build-published` once the data layer is stable so the published site matches the archive state.")
    return actions


def _archive_recovery_commands(season_rows: list[dict[str, str | int]]) -> list[str]:
    commands: list[str] = []

    foundational_years = [
        int(row["season_year"])
        for row in season_rows
        if row["overall_status"] == "Foundational gap"
    ]
    if foundational_years:
        for start_year, end_year in _year_ranges(foundational_years):
            commands.append(
                f"powershell -ExecutionPolicy Bypass -File scripts\\backfill_cfbd_logged.ps1 -StartSeason {start_year} -EndSeason {end_year} -IncludePostseason"
            )

    player_context_years = [
        int(row["season_year"])
        for row in season_rows
        if str(row["player_status"]) in {"Game shell only", "Player context partial", "Unloaded", "Missing season shell"}
    ]
    if player_context_years:
        for start_year, end_year in _year_ranges(player_context_years):
            commands.append(
                f"powershell -ExecutionPolicy Bypass -File scripts\\backfill_player_context_logged.ps1 -StartSeason {start_year} -EndSeason {end_year}"
            )

    game_stat_years = [
        int(row["season_year"])
        for row in season_rows
        if str(row["player_status"]) in {"Game shell only", "Game stats partial", "Game stats partial (postseason missing)", "Unloaded", "Missing season shell"}
        or str(row["postseason_status"]) == "Gap"
    ]
    if game_stat_years:
        for start_year, end_year in _year_ranges(game_stat_years):
            commands.append(
                f"powershell -ExecutionPolicy Bypass -File scripts\\backfill_game_player_stats_logged.ps1 -StartSeason {start_year} -EndSeason {end_year} -IncludePostseason -DryRun -MaxWeeks 12"
            )
            commands.append(
                f"powershell -ExecutionPolicy Bypass -File scripts\\backfill_game_player_stats_logged.ps1 -StartSeason {start_year} -EndSeason {end_year} -IncludePostseason"
            )

    awards_only_years = [
        int(row["season_year"])
        for row in season_rows
        if str(row["awards_status"]) == "Heisman only"
    ]
    if awards_only_years:
        commands.append(
            "python manage.py import-player-honors --csv <path-to-broader-awards-csv> --source-name manual"
        )

    commands.append("powershell -ExecutionPolicy Bypass -File scripts\\safe_refresh_local_health.ps1 -StartSeason 2014 -EndSeason 2025")
    return commands


def _year_ranges(years: list[int]) -> list[tuple[int, int]]:
    ordered = sorted(set(years))
    if not ordered:
        return []
    ranges: list[tuple[int, int]] = []
    start = ordered[0]
    end = ordered[0]
    for year in ordered[1:]:
        if year == end + 1:
            end = year
            continue
        ranges.append((start, end))
        start = year
        end = year
    ranges.append((start, end))
    return ranges


def _published_output_metrics() -> dict[str, int | str | bool]:
    site_root = Path("output/site")
    team_dir = site_root / "teams"
    program_dir = site_root / "programs"
    player_dir = site_root / "players"
    conference_dir = site_root / "conferences"
    archive_dir = site_root / "archive"
    site_home = site_root / "index.html"
    rankings_page = Path("output/rankings.html")
    return {
        "site_home_present": site_home.exists(),
        "rankings_present": rankings_page.exists(),
        "site_home_timestamp": _format_timestamp(site_home),
        "rankings_timestamp": _format_timestamp(rankings_page),
        "team_pages": _html_file_count(team_dir),
        "program_pages": _html_file_count(program_dir),
        "player_pages": _html_file_count(player_dir),
        "conference_pages": _html_file_count(conference_dir),
        "archive_pages": _html_file_count(archive_dir),
    }


def _published_artifact_rows(publish: dict[str, int | str | bool]) -> list[tuple[str, str, str]]:
    return [
        (
            "Site Home",
            "Complete" if bool(publish["site_home_present"]) else "Pending",
            f"`output/site/index.html` updated {publish['site_home_timestamp']}.",
        ),
        (
            "Rankings Report",
            "Complete" if bool(publish["rankings_present"]) else "Pending",
            f"`output/rankings.html` updated {publish['rankings_timestamp']}.",
        ),
        (
            "Team Pages",
            "Complete" if int(publish["team_pages"]) > 0 else "Pending",
            f"{int(publish['team_pages'])} HTML files under `output/site/teams`.",
        ),
        (
            "Program Pages",
            "Complete" if int(publish["program_pages"]) > 0 else "Pending",
            f"{int(publish['program_pages'])} HTML files under `output/site/programs`.",
        ),
        (
            "Player Pages",
            "Complete" if int(publish["player_pages"]) > 0 else "Pending",
            f"{int(publish['player_pages'])} HTML files under `output/site/players`.",
        ),
        (
            "Conference Pages",
            "Complete" if int(publish["conference_pages"]) > 0 else "Pending",
            f"{int(publish['conference_pages'])} HTML files under `output/site/conferences`.",
        ),
        (
            "Archive Pages",
            "Complete" if int(publish["archive_pages"]) > 0 else "Pending",
            f"{int(publish['archive_pages'])} HTML files under `output/site/archive`.",
        ),
    ]


def _audit_artifact_rows() -> list[tuple[str, str, str]]:
    artifacts = [
        ("Data Coverage Audit", Path("output/data-coverage-audit.md")),
        ("Player Archive Audit", Path("output/player-archive-audit.md")),
        ("Awards Archive Audit", Path("output/awards-archive-audit.md")),
        ("Competition Integrity Audit", Path("output/competition-integrity-audit.md")),
        ("Program History Audit", Path("output/program-history-integrity-audit.md")),
        ("History Load Status", Path("output/history-load-status.md")),
    ]
    rows: list[tuple[str, str, str]] = []
    for label, path in artifacts:
        sidecar = path.with_suffix(".json")
        evidence = f"`{path.as_posix()}` updated {_format_timestamp(path)}."
        if sidecar.exists():
            evidence += f" JSON sidecar present at `{sidecar.as_posix()}` updated {_format_timestamp(sidecar)}."
        rows.append(
            (
                label,
                "Complete" if path.exists() else "Pending",
                evidence,
            )
        )
    return rows


def _html_file_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for file_path in path.rglob("*.html") if file_path.is_file())


def _format_timestamp(path: Path) -> str:
    if not path.exists():
        return "missing"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def _write_archive_readiness_sidecar(
    *,
    output_path: Path,
    publish: dict[str, int | str | bool],
    audit_artifacts: list[tuple[str, str, str]],
    season_readiness_rows: list[dict[str, str | int]],
    critical_gaps: list[str],
    next_actions: list[str],
    recovery_commands: list[str],
) -> None:
    payload = {
        "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "markdownPath": output_path.as_posix(),
        "publishFootprint": {
            "siteHomePresent": bool(publish["site_home_present"]),
            "rankingsPresent": bool(publish["rankings_present"]),
            "siteHomeUpdated": str(publish["site_home_timestamp"]),
            "rankingsUpdated": str(publish["rankings_timestamp"]),
            "teamPages": int(publish["team_pages"]),
            "programPages": int(publish["program_pages"]),
            "playerPages": int(publish["player_pages"]),
            "conferencePages": int(publish["conference_pages"]),
            "archivePages": int(publish["archive_pages"]),
        },
        "auditArtifacts": [
            {"label": label, "status": status, "evidence": evidence}
            for label, status, evidence in audit_artifacts
        ],
        "seasonReadiness": season_readiness_rows,
        "summary": {
            "seasonCount": len(season_readiness_rows),
            "readySeasons": sum(1 for row in season_readiness_rows if row["overall_status"] == "Ready"),
            "inProgressSeasons": sum(1 for row in season_readiness_rows if row["overall_status"] == "In Progress"),
            "foundationalGapSeasons": sum(1 for row in season_readiness_rows if row["overall_status"] == "Foundational gap"),
        },
        "criticalGaps": critical_gaps,
        "recommendedNextActions": next_actions,
        "suggestedRecoveryCommands": recovery_commands,
    }
    _write_json_sidecar(output_path, payload)


def _write_data_coverage_sidecar(
    *,
    output_path: Path,
    seasons: list[int],
    rows: list[dict[str, int]],
    gaps: list[str],
) -> None:
    coverage_map = {int(row["season_year"]): row for row in rows}
    season_rows: list[dict[str, int]] = []
    for season in seasons:
        row = coverage_map.get(season, {})
        season_rows.append(
            {
                "seasonYear": season,
                "games": int(row.get("games") or 0),
                "postseasonGames": int(row.get("postseason_games") or 0),
                "teamSeasons": int(row.get("team_seasons") or 0),
                "rosterEntries": int(row.get("roster_entries") or 0),
                "playerSeasonStats": int(row.get("player_season_stats") or 0),
                "playerUsage": int(row.get("player_usage_season") or 0),
                "playerValue": int(row.get("player_value_metrics") or 0),
                "playerGameStats": int(row.get("player_game_stats") or 0),
                "playerHonors": int(row.get("player_honors") or 0),
                "heismanVoteResults": int(row.get("heisman_vote_results") or 0),
                "officialRankings": int(row.get("official_rankings") or 0),
                "transferEntries": int(row.get("transfer_entries") or 0),
                "playerRecruitingProfiles": int(row.get("player_recruiting_profiles") or 0),
            }
        )

    payload = {
        "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "markdownPath": output_path.as_posix(),
        "summary": {
            "seasonCount": len(season_rows),
            "startSeason": season_rows[0]["seasonYear"] if season_rows else None,
            "endSeason": season_rows[-1]["seasonYear"] if season_rows else None,
        },
        "seasonCoverage": season_rows,
        "gapsToWatch": gaps,
    }
    _write_json_sidecar(output_path, payload)


def _write_player_archive_sidecar(
    *,
    output_path: Path,
    rows: list[dict[str, int | bool | str]],
    status_counts: list[tuple[str, int]],
    priority_rows: list[dict[str, str | int]],
    gaps: list[str],
    missing_samples: list[dict[str, str | int]],
) -> None:
    season_coverage = []
    for row in rows:
        completed_games = int(row.get("completed_fbs_games") or 0)
        covered_games = int(row.get("fbs_games_with_player_stats") or 0)
        coverage_pct = 0.0 if completed_games <= 0 else (100.0 * covered_games / completed_games)
        season_coverage.append(
            {
                "seasonYear": int(row["season_year"]),
                "seasonPresent": bool(row.get("season_present")),
                "completedFbsGames": completed_games,
                "fbsGamesWithPlayerStats": covered_games,
                "playerStatCoveragePct": round(coverage_pct, 1),
                "completedFbsPostseasonGames": int(row.get("completed_fbs_postseason_games") or 0),
                "fbsPostseasonGamesWithPlayerStats": int(row.get("fbs_postseason_games_with_player_stats") or 0),
                "rosterEntries": int(row.get("roster_entries") or 0),
                "playerSeasonStats": int(row.get("player_season_stats") or 0),
                "playerUsage": int(row.get("player_usage_season") or 0),
                "playerValue": int(row.get("player_value_metrics") or 0),
                "playerHonors": int(row.get("player_honors") or 0),
                "heismanVoteResults": int(row.get("heisman_vote_results") or 0),
                "status": _player_archive_status(row),
            }
        )

    payload = {
        "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "markdownPath": output_path.as_posix(),
        "seasonCoverage": season_coverage,
        "readinessSummary": [{"status": status, "seasonCount": count} for status, count in status_counts],
        "recoveryPriorities": [
            {
                "seasonYear": int(row["season_year"]),
                "priority": str(row["priority_label"]),
                "reason": str(row["reason"]),
            }
            for row in priority_rows
        ],
        "gapsToWatch": gaps,
        "missingGameSamples": [
            {
                "seasonYear": int(row["season_year"]),
                "week": int(row.get("week") or 0),
                "phase": str(row.get("season_phase") or "regular season"),
                "matchup": f"{row['home_team_name']} vs {row['away_team_name']}",
            }
            for row in missing_samples
        ],
    }
    _write_json_sidecar(output_path, payload)


def _write_awards_archive_sidecar(
    *,
    output_path: Path,
    rows: list[dict[str, int | bool]],
    gaps: list[str],
    labels: list[dict[str, int | str]],
) -> None:
    season_coverage = [
        {
            "seasonYear": int(row["season_year"]),
            "seasonPresent": bool(row.get("season_present")),
            "honorRows": int(row.get("honor_rows") or 0),
            "distinctAwards": int(row.get("distinct_awards") or 0),
            "distinctSelectors": int(row.get("distinct_selectors") or 0),
            "heismanWinnerRows": int(row.get("heisman_winner_rows") or 0),
            "heismanFinalistRows": int(row.get("heisman_finalist_rows") or 0),
            "heismanVoteRows": int(row.get("heisman_vote_rows") or 0),
            "status": _awards_archive_status(row),
        }
        for row in rows
    ]
    status_counts: dict[str, int] = {}
    for row in season_coverage:
        status = str(row["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    payload = {
        "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "markdownPath": output_path.as_posix(),
        "seasonCoverage": season_coverage,
        "summary": {
            "seasonCount": len(season_coverage),
            "statusCounts": [
                {"status": status, "seasonCount": count}
                for status, count in sorted(status_counts.items())
            ],
        },
        "gapsToWatch": gaps,
        "awardLabelsPresent": [
            {"honorName": str(row["honor_name"]), "rowCount": int(row["row_count"])}
            for row in labels
        ],
    }
    _write_json_sidecar(output_path, payload)


def _write_json_sidecar(output_path: Path, payload: dict[str, object]) -> None:
    output_path.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _coverage_gap_lines(rows: list[dict[str, int]]) -> list[str]:
    gaps: list[str] = []
    for row in rows:
        season = int(row["season_year"])
        games = int(row.get("games") or 0)
        postseason = int(row.get("postseason_games") or 0)
        rosters = int(row.get("roster_entries") or 0)
        season_stats = int(row.get("player_season_stats") or 0)
        usage = int(row.get("player_usage_season") or 0)
        value_metrics = int(row.get("player_value_metrics") or 0)
        game_player = int(row.get("player_game_stats") or 0)
        honors = int(row.get("player_honors") or 0)
        heisman_votes = int(row.get("heisman_vote_results") or 0)
        rankings = int(row.get("official_rankings") or 0)
        team_seasons = int(row.get("team_seasons") or 0)

        if season >= 2014 and games == 0 and team_seasons == 0 and (honors > 0 or heisman_votes > 0):
            gaps.append(
                f"{season} currently exists only as an awards shell: honors are loaded, but no games or team-season rows are present yet."
            )
            continue
        if season >= 2014 and games == 0 and team_seasons == 0 and honors == 0 and heisman_votes == 0:
            gaps.append(f"{season} has no local archive footprint yet.")
            continue

        if games and season >= 2014 and season < 2020 and postseason == 0:
            gaps.append(f"{season} has games loaded but no postseason rows yet.")
        if games and rosters == 0 and season >= 2021:
            gaps.append(f"{season} has schedule/game data but no roster archive yet.")
        if games and season_stats == 0 and season >= 2021:
            gaps.append(f"{season} has schedule/game data but no player season stats yet.")
        if season_stats and usage == 0:
            gaps.append(f"{season} has player season stats but no player usage snapshot.")
        if season_stats and value_metrics == 0:
            gaps.append(f"{season} has player season stats but no player value metrics snapshot.")
        if games and game_player == 0:
            gaps.append(f"{season} has game data but no game-level player stat archive yet.")
        if season >= 2014 and honors == 0:
            gaps.append(f"{season} has no structured player honors loaded yet.")
        if honors and season >= 2014 and heisman_votes == 0:
            gaps.append(f"{season} has honors loaded but no Heisman vote/finalist results yet.")
        if season >= 2020 and games and rankings == 0:
            gaps.append(f"{season} has team/game data but no official rankings loaded.")
    return gaps


def _player_archive_rows(db: Database) -> list[dict[str, int]]:
    return db.query_all(
        """
        with base as (
          select season_year
          from seasons
        ),
        completed_fbs_games as (
          select
            g.season_year,
            count(*) as completed_fbs_games,
            sum(case when g.season_type = 'postseason' then 1 else 0 end) as completed_fbs_postseason_games
          from games g
          join teams ht on ht.team_id = g.home_team_id
          join teams at on at.team_id = g.away_team_id
          left join team_seasons hts
            on hts.team_id = g.home_team_id
           and hts.season_year = g.season_year
          left join team_seasons ats
            on ats.team_id = g.away_team_id
           and ats.season_year = g.season_year
          where g.home_points is not null
            and g.away_points is not null
            and coalesce(hts.level_code, ht.level_code) = 'FBS'
            and coalesce(ats.level_code, at.level_code) = 'FBS'
          group by g.season_year
        ),
        covered_fbs_games as (
          select
            g.season_year,
            count(distinct g.game_id) as fbs_games_with_player_stats,
            count(distinct case when g.season_type = 'postseason' then g.game_id end) as fbs_postseason_games_with_player_stats
          from games g
          join player_game_stats pgs on pgs.game_id = g.game_id
          join teams ht on ht.team_id = g.home_team_id
          join teams at on at.team_id = g.away_team_id
          left join team_seasons hts
            on hts.team_id = g.home_team_id
           and hts.season_year = g.season_year
          left join team_seasons ats
            on ats.team_id = g.away_team_id
           and ats.season_year = g.season_year
          where coalesce(hts.level_code, ht.level_code) = 'FBS'
            and coalesce(ats.level_code, at.level_code) = 'FBS'
          group by g.season_year
        )
        select
          b.season_year,
          coalesce(cfg.completed_fbs_games, 0) as completed_fbs_games,
          coalesce(cvg.fbs_games_with_player_stats, 0) as fbs_games_with_player_stats,
          coalesce(cfg.completed_fbs_postseason_games, 0) as completed_fbs_postseason_games,
          coalesce(cvg.fbs_postseason_games_with_player_stats, 0) as fbs_postseason_games_with_player_stats,
          (select count(*) from roster_entries re where re.season_year = b.season_year) as roster_entries,
          (select count(*) from player_season_stats pss where pss.season_year = b.season_year) as player_season_stats,
          (select count(*) from player_usage_season pus where pus.season_year = b.season_year) as player_usage_season,
          (select count(*) from player_value_metrics pvm where pvm.season_year = b.season_year) as player_value_metrics,
          (select count(*) from player_honors ph where ph.season_year = b.season_year) as player_honors,
          (select count(*) from heisman_vote_results hvr where hvr.season_year = b.season_year) as heisman_vote_results
        from base b
        left join completed_fbs_games cfg on cfg.season_year = b.season_year
        left join covered_fbs_games cvg on cvg.season_year = b.season_year
        order by b.season_year
        """
    )


def _expand_player_archive_rows(db: Database, rows: list[dict[str, int]]) -> list[dict[str, int | bool]]:
    seasons = _archive_seasons(db)
    coverage_map = {int(row["season_year"]): row for row in rows}
    season_presence = {
        int(row["season_year"])
        for row in db.query_all("select season_year from seasons order by season_year")
    }
    expanded_rows: list[dict[str, int | bool]] = []
    for season in seasons:
        source_row = coverage_map.get(season, {})
        expanded_rows.append(
            {
                "season_year": season,
                "season_present": season in season_presence,
                "completed_fbs_games": int(source_row.get("completed_fbs_games") or 0),
                "fbs_games_with_player_stats": int(source_row.get("fbs_games_with_player_stats") or 0),
                "completed_fbs_postseason_games": int(source_row.get("completed_fbs_postseason_games") or 0),
                "fbs_postseason_games_with_player_stats": int(source_row.get("fbs_postseason_games_with_player_stats") or 0),
                "roster_entries": int(source_row.get("roster_entries") or 0),
                "player_season_stats": int(source_row.get("player_season_stats") or 0),
                "player_usage_season": int(source_row.get("player_usage_season") or 0),
                "player_value_metrics": int(source_row.get("player_value_metrics") or 0),
                "player_honors": int(source_row.get("player_honors") or 0),
                "heisman_vote_results": int(source_row.get("heisman_vote_results") or 0),
            }
        )
    return expanded_rows


def _awards_archive_rows(db: Database) -> list[dict[str, int | bool]]:
    seasons = _archive_seasons(db)
    season_presence = {
        int(row["season_year"])
        for row in db.query_all("select season_year from seasons order by season_year")
    }
    coverage = {
        int(row["season_year"]): row
        for row in db.query_all(
            """
            select
              s.season_year,
              (select count(*) from player_honors ph where ph.season_year = s.season_year) as honor_rows,
              (select count(distinct honor_name) from player_honors ph where ph.season_year = s.season_year) as distinct_awards,
              (select count(distinct selector) from player_honors ph where ph.season_year = s.season_year and coalesce(selector, '') <> '') as distinct_selectors,
              (select count(*) from player_honors ph where ph.season_year = s.season_year and lower(ph.honor_name) like '%heisman%' and lower(coalesce(ph.honor_team, '')) = 'winner') as heisman_winner_rows,
              (select count(*) from player_honors ph where ph.season_year = s.season_year and lower(ph.honor_name) like '%heisman%' and lower(coalesce(ph.honor_team, '')) = 'finalist') as heisman_finalist_rows,
              (select count(*) from heisman_vote_results hvr where hvr.season_year = s.season_year) as heisman_vote_rows
            from seasons s
            order by s.season_year
            """
        )
    }
    expanded: list[dict[str, int | bool]] = []
    for season in seasons:
        row = coverage.get(season, {})
        expanded.append(
            {
                "season_year": season,
                "season_present": season in season_presence,
                "honor_rows": int(row.get("honor_rows") or 0),
                "distinct_awards": int(row.get("distinct_awards") or 0),
                "distinct_selectors": int(row.get("distinct_selectors") or 0),
                "heisman_winner_rows": int(row.get("heisman_winner_rows") or 0),
                "heisman_finalist_rows": int(row.get("heisman_finalist_rows") or 0),
                "heisman_vote_rows": int(row.get("heisman_vote_rows") or 0),
            }
        )
    return expanded


def _player_archive_gap_lines(rows: list[dict[str, int]]) -> list[str]:
    gaps: list[str] = []
    for row in rows:
        season = int(row["season_year"])
        completed_games = int(row.get("completed_fbs_games") or 0)
        covered_games = int(row.get("fbs_games_with_player_stats") or 0)
        postseason_games = int(row.get("completed_fbs_postseason_games") or 0)
        covered_postseason_games = int(row.get("fbs_postseason_games_with_player_stats") or 0)
        rosters = int(row.get("roster_entries") or 0)
        season_stats = int(row.get("player_season_stats") or 0)
        usage = int(row.get("player_usage_season") or 0)
        value = int(row.get("player_value_metrics") or 0)
        honors = int(row.get("player_honors") or 0)
        heisman_votes = int(row.get("heisman_vote_results") or 0)
        season_present = bool(row.get("season_present"))

        if not season_present:
            gaps.append(f"{season} is completely absent from the local archive tables and still needs an initial season shell.")
            continue

        if completed_games and covered_games == 0:
            gaps.append(f"{season} has completed FBS games but no game-level player stats loaded.")
        elif completed_games and covered_games < completed_games:
            gaps.append(f"{season} has player-game stats for only {covered_games} of {completed_games} completed FBS games.")
        if postseason_games and covered_postseason_games == 0:
            gaps.append(f"{season} has completed FBS postseason games but no postseason player-game stats loaded.")
        if season_stats and rosters == 0:
            gaps.append(f"{season} has player season stats loaded without roster rows.")
        if season_stats and usage == 0:
            gaps.append(f"{season} has player season stats loaded but no player usage snapshot.")
        if season_stats and value == 0:
            gaps.append(f"{season} has player season stats loaded but no player value metrics snapshot.")
        if honors and heisman_votes == 0:
            gaps.append(f"{season} has player honors loaded but no Heisman vote results.")
    return gaps


def _player_archive_status(row: dict[str, int | bool]) -> str:
    season_present = bool(row.get("season_present"))
    completed_games = int(row.get("completed_fbs_games") or 0)
    covered_games = int(row.get("fbs_games_with_player_stats") or 0)
    postseason_games = int(row.get("completed_fbs_postseason_games") or 0)
    covered_postseason_games = int(row.get("fbs_postseason_games_with_player_stats") or 0)
    rosters = int(row.get("roster_entries") or 0)
    season_stats = int(row.get("player_season_stats") or 0)
    usage = int(row.get("player_usage_season") or 0)
    value = int(row.get("player_value_metrics") or 0)

    if not season_present:
        return "Missing season shell"
    if completed_games == 0 and rosters == 0 and season_stats == 0:
        return "Unloaded"
    if completed_games > 0 and covered_games == 0 and season_stats == 0:
        return "Game shell only"
    if season_stats > 0 and (usage == 0 or value == 0):
        return "Player context partial"
    if completed_games > 0 and covered_games < completed_games:
        if postseason_games > 0 and covered_postseason_games == 0:
            return "Game stats partial (postseason missing)"
        return "Game stats partial"
    if completed_games > 0 and covered_games >= completed_games:
        return "Ready"
    return "In progress"


def _awards_archive_status(row: dict[str, int | bool]) -> str:
    if not bool(row.get("season_present")):
        return "Missing season shell"
    honor_rows = int(row.get("honor_rows") or 0)
    distinct_awards = int(row.get("distinct_awards") or 0)
    winner_rows = int(row.get("heisman_winner_rows") or 0)
    finalist_rows = int(row.get("heisman_finalist_rows") or 0)
    vote_rows = int(row.get("heisman_vote_rows") or 0)

    if honor_rows == 0:
        return "No awards loaded"
    if winner_rows >= 1 and finalist_rows >= 3 and vote_rows >= 3 and distinct_awards <= 2:
        return "Heisman only"
    if distinct_awards > 2:
        return "Broader awards coverage"
    return "Partial honors coverage"


def _player_archive_status_counts(rows: list[dict[str, int | bool]]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for row in rows:
        status = _player_archive_status(row)
        counts[status] = counts.get(status, 0) + 1
    order = {
        "Ready": 0,
        "Game stats partial": 1,
        "Game stats partial (postseason missing)": 2,
        "Player context partial": 3,
        "Game shell only": 4,
        "In progress": 5,
        "Unloaded": 6,
        "Missing season shell": 7,
    }
    return sorted(counts.items(), key=lambda item: (order.get(item[0], 99), item[0]))


def _awards_archive_gap_lines(rows: list[dict[str, int | bool]]) -> list[str]:
    gaps: list[str] = []
    heisman_only_years: list[int] = []
    for row in rows:
        season = int(row["season_year"])
        season_present = bool(row.get("season_present"))
        honor_rows = int(row.get("honor_rows") or 0)
        distinct_awards = int(row.get("distinct_awards") or 0)
        winner_rows = int(row.get("heisman_winner_rows") or 0)
        finalist_rows = int(row.get("heisman_finalist_rows") or 0)
        vote_rows = int(row.get("heisman_vote_rows") or 0)

        if not season_present:
            gaps.append(f"{season} has no local season shell, so no awards archive can attach to it yet.")
            continue
        if honor_rows == 0:
            gaps.append(f"{season} has no structured awards rows loaded.")
            continue
        if winner_rows == 0:
            gaps.append(f"{season} has honor rows but no Heisman winner row.")
        if finalist_rows == 0:
            gaps.append(f"{season} has honor rows but no Heisman finalist rows.")
        if vote_rows == 0:
            gaps.append(f"{season} has honor rows but no Heisman vote-result rows.")
        if distinct_awards <= 2 and honor_rows > 0:
            heisman_only_years.append(season)

    if heisman_only_years:
        ranges = ", ".join(str(season) for season in heisman_only_years)
        gaps.append(
            f"The structured awards archive is still Heisman-only in these seasons: {ranges}. Broader award families such as position awards, All-America, and conference honors are not loaded yet."
        )
    return gaps


def _award_label_counts(db: Database) -> list[dict[str, int | str]]:
    return db.query_all(
        """
        select honor_name, count(*) as row_count
        from player_honors
        group by honor_name
        order by row_count desc, honor_name asc
        """
    )


def _player_archive_priority_rows(rows: list[dict[str, int | bool]]) -> list[dict[str, int | str]]:
    priorities: list[dict[str, int | str]] = []
    for row in rows:
        season = int(row["season_year"])
        season_present = bool(row.get("season_present"))
        completed_games = int(row.get("completed_fbs_games") or 0)
        covered_games = int(row.get("fbs_games_with_player_stats") or 0)
        postseason_games = int(row.get("completed_fbs_postseason_games") or 0)
        covered_postseason_games = int(row.get("fbs_postseason_games_with_player_stats") or 0)
        season_stats = int(row.get("player_season_stats") or 0)
        usage = int(row.get("player_usage_season") or 0)
        value = int(row.get("player_value_metrics") or 0)

        if not season_present:
            priorities.append(
                {
                    "season_year": season,
                    "priority_rank": 0,
                    "priority_label": "Foundational gap",
                    "reason": "The season is completely absent locally, so every downstream archive layer is blocked.",
                }
            )
            continue
        if completed_games > 0 and covered_games == 0:
            priorities.append(
                {
                    "season_year": season,
                    "priority_rank": 1,
                    "priority_label": "High",
                    "reason": f"Completed FBS games are loaded, but 0 of {completed_games} have game-level player stats.",
                }
            )
            continue
        if season_stats > 0 and (usage == 0 or value == 0):
            missing_layers: list[str] = []
            if usage == 0:
                missing_layers.append("usage")
            if value == 0:
                missing_layers.append("value metrics")
            priorities.append(
                {
                    "season_year": season,
                    "priority_rank": 2,
                    "priority_label": "Medium",
                    "reason": f"Player season stats exist, but the {', '.join(missing_layers)} layer is still missing.",
                }
            )
            continue
        if postseason_games > 0 and covered_postseason_games == 0:
            priorities.append(
                {
                    "season_year": season,
                    "priority_rank": 3,
                    "priority_label": "Medium",
                    "reason": f"Regular-season archive is ahead of postseason coverage: 0 of {postseason_games} completed FBS postseason games have player stats.",
                }
            )
            continue
        if completed_games > 0 and covered_games < completed_games:
            priorities.append(
                {
                    "season_year": season,
                    "priority_rank": 4,
                    "priority_label": "Medium",
                    "reason": f"Only {covered_games} of {completed_games} completed FBS games currently have player stats.",
                }
            )

    priorities.sort(key=lambda row: (int(row["priority_rank"]), -int(row["season_year"])))
    return priorities[:8]


def _archive_seasons(db: Database, start_season: int = 2014) -> list[int]:
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
          union all
          select season_year from player_season_stats
          union all
          select season_year from player_game_stats
        ) season_years
        """
    ) or {}
    max_season = int(row.get("max_season") or 0)
    if max_season < start_season:
        return []
    return list(range(start_season, max_season + 1))


def _missing_player_stat_game_samples(db: Database) -> list[dict[str, int | str]]:
    return db.query_all(
        """
        with completed_fbs_games as (
          select
            g.game_id,
            g.season_year,
            g.week,
            g.season_phase,
            ht.canonical_name as home_team_name,
            at.canonical_name as away_team_name
          from games g
          join teams ht on ht.team_id = g.home_team_id
          join teams at on at.team_id = g.away_team_id
          left join team_seasons hts
            on hts.team_id = g.home_team_id
           and hts.season_year = g.season_year
          left join team_seasons ats
            on ats.team_id = g.away_team_id
           and ats.season_year = g.season_year
          where g.home_points is not null
            and g.away_points is not null
            and coalesce(hts.level_code, ht.level_code) = 'FBS'
            and coalesce(ats.level_code, at.level_code) = 'FBS'
        )
        select
          cfg.season_year,
          cfg.week,
          cfg.season_phase,
          cfg.home_team_name,
          cfg.away_team_name
        from completed_fbs_games cfg
        left join (
          select distinct game_id
          from player_game_stats
        ) pgs on pgs.game_id = cfg.game_id
        where pgs.game_id is null
        order by cfg.season_year desc, cfg.week desc, cfg.home_team_name asc, cfg.away_team_name asc
        limit 20
        """
    )
