from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.utils import is_site_eligible_team


GENERIC_CONFERENCE_NAMES = {"FBS", "FCS", "DII", "DIII"}
MAX_COMPLETED_GAMES_BY_LEVEL = {
    "FBS": 18,
    "FCS": 17,
    "DII": 16,
    "DIII": 15,
}


def write_competition_integrity_audit(
    db: Database,
    output_path: str = "output/competition-integrity-audit.md",
) -> str:
    latest_snapshot = _latest_snapshot(db)
    postseason_carryover = _postseason_carryover_rows(db)
    regular_future_year = _regular_future_year_rows(db)
    duplicate_signatures = _duplicate_game_signature_rows(db)
    same_day_collisions = _same_day_team_collision_rows(db)
    level_transitions = _level_transition_rows(db)
    current_identity_drift = _current_identity_drift_rows(db)
    generic_placeholders = _generic_placeholder_rows(db)
    latest_snapshot_placeholder_rows = _latest_snapshot_placeholder_rows(db, latest_snapshot)
    cross_level_issues = _latest_snapshot_cross_level_issues(db, latest_snapshot)

    lines: list[str] = [
        "# Competition Integrity Audit",
        "",
        "This file checks season continuity, duplicate-risk rows, level transitions, and latest-board labeling health.",
        "",
        "## Latest Snapshot",
        "",
    ]
    if latest_snapshot is None:
        lines.append("- No model snapshot exists yet.")
    else:
        lines.append(
            f"- Latest modeled snapshot: season `{int(latest_snapshot['season_year'])}` week `{int(latest_snapshot['week'])}` "
            f"(model run `{int(latest_snapshot['model_run_id'])}`)."
        )

    lines.extend(
        [
            "",
            "## Season Continuity",
            "",
            f"- Postseason games stored under the prior fall season but played in the next calendar year: `{len(postseason_carryover)}`",
            f"- Regular-season games whose UTC calendar year is later than `season_year`: `{len(regular_future_year)}`",
            "",
        ]
    )

    if postseason_carryover:
        lines.extend(
            [
                "### Next-Calendar Postseason Samples",
                "",
                "| Season | Date | Week | Phase | Matchup |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for row in postseason_carryover[:12]:
            lines.append(
                f"| {int(row['season_year'])} | {row['game_date']} | {int(row.get('week') or 0)} | "
                f"{row.get('season_phase') or 'postseason'} | {row['home_team_name']} vs {row['away_team_name']} |"
            )
        lines.append("")

    if regular_future_year:
        lines.extend(
            [
                "### Regular-Season Calendar-Year Mismatches",
                "",
                "These rows are suspicious because they are not postseason but landed in a later calendar year.",
                "",
                "| Season | Date | Week | Matchup |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for row in regular_future_year[:12]:
            lines.append(
                f"| {int(row['season_year'])} | {row['game_date']} | {int(row.get('week') or 0)} | "
                f"{row['home_team_name']} vs {row['away_team_name']} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Duplicate And Collision Checks",
            "",
            f"- Exact duplicate game signatures `(season, home, away, start_time_utc)`: `{len(duplicate_signatures)}`",
            f"- Teams with more than one game on the same UTC date: `{len(same_day_collisions)}`",
            "",
        ]
    )

    if duplicate_signatures:
        lines.extend(
            [
                "### Duplicate Signature Rows",
                "",
                "| Season | Start Time UTC | Matchup | Copies |",
                "| --- | --- | --- | ---: |",
            ]
        )
        for row in duplicate_signatures[:20]:
            lines.append(
                f"| {int(row['season_year'])} | {row['start_time_utc']} | {row['home_team_name']} vs {row['away_team_name']} | "
                f"{int(row['copies'])} |"
            )
        lines.append("")

    if same_day_collisions:
        lines.extend(
            [
                "### Same-Day Team Collisions",
                "",
                "| Season | Date | Team | Games On Day | Completed Games | Sample Matchups |",
                "| --- | --- | --- | ---: | ---: | --- |",
            ]
        )
        for row in same_day_collisions[:20]:
            lines.append(
                f"| {int(row['season_year'])} | {row['game_date']} | {row['team_name']} | {int(row['games_on_day'])} | "
                f"{int(row['completed_games'])} | {row['sample_matchups']} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Level And Conference Integrity",
            "",
            f"- Current `teams` fallback identity rows drifting from the latest `team_seasons` season: `{len(current_identity_drift)}`",
            f"- Team-season rows using generic placeholder conferences like `FBS` or `FCS`: `{len(generic_placeholders)}`",
            f"- Explicit season-to-season level changes captured in `team_seasons`: `{len(level_transitions)}`",
            "",
        ]
    )

    if current_identity_drift:
        lines.extend(
            [
                "### Current Team Identity Drift",
                "",
                "| Team | Latest Season | Current Level | Latest Season Level | Current Conference | Latest Season Conference |",
                "| --- | ---: | --- | --- | --- | --- |",
            ]
        )
        for row in current_identity_drift[:30]:
            lines.append(
                f"| {row['team_name']} | {int(row['latest_season_year'])} | {row.get('current_level_code') or ''} | "
                f"{row.get('latest_level_code') or ''} | {row.get('current_conference_name') or ''} | "
                f"{row.get('latest_conference_name') or ''} |"
            )
        lines.append("")

    if generic_placeholders:
        lines.extend(
            [
                "### Generic Placeholder Conference Rows",
                "",
                "These are the highest-risk rows for bad level labeling or fake conference identity.",
                "",
                "| Season | Team | Level | Conference |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in generic_placeholders[:30]:
            lines.append(
                f"| {int(row['season_year'])} | {row['team_name']} | {row['level_code']} | {row['conference_name']} |"
            )
        lines.append("")

    if level_transitions:
        lines.extend(
            [
                "### Level Changes",
                "",
                "Some of these are legitimate reclassification moves. Others deserve a closer look if the school is clearly known to be stable.",
                "",
                "| Team | Season | Previous Level | Current Level | Conference |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for row in level_transitions[:40]:
            lines.append(
                f"| {row['team_name']} | {int(row['season_year'])} | {row['prev_level']} | {row['level_code']} | "
                f"{row.get('conference_name') or ''} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Latest Board Integrity",
            "",
            f"- Latest snapshot rows using generic placeholder conferences: `{len(latest_snapshot_placeholder_rows)}`",
            f"- Cross-level neighbor logic returning a same-level peer: `{len(cross_level_issues)}`",
            "",
        ]
    )

    if latest_snapshot_placeholder_rows:
        lines.extend(
            [
                "### Latest Snapshot Placeholder Rows",
                "",
                "| Rank | Team | Level | Conference | Power | Site Eligible |",
                "| ---: | --- | --- | --- | ---: | --- |",
            ]
        )
        for row in latest_snapshot_placeholder_rows[:30]:
            eligible = is_site_eligible_team(str(row.get("level_code") or ""), row.get("conference_name"))
            lines.append(
                f"| {int(row['overall_rank'])} | {row['team_name']} | {row['level_code']} | {row.get('conference_name') or ''} | "
                f"{float(row.get('power_rating') or 0.0):.2f} | {'yes' if eligible else 'no'} |"
            )
        lines.append("")

    if cross_level_issues:
        lines.extend(
            [
                "### Cross-Level Peer Issues",
                "",
                "| Team | Team Level | Returned Peer | Peer Level |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in cross_level_issues[:20]:
            lines.append(
                f"| {row['team_name']} | {row['team_level']} | {row['peer_name']} | {row['peer_level']} |"
            )
        lines.append("")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_competition_integrity_sidecar(
        output_path=path,
        latest_snapshot=latest_snapshot,
        postseason_carryover=postseason_carryover,
        regular_future_year=regular_future_year,
        duplicate_signatures=duplicate_signatures,
        same_day_collisions=same_day_collisions,
        level_transitions=level_transitions,
        current_identity_drift=current_identity_drift,
        generic_placeholders=generic_placeholders,
        latest_snapshot_placeholder_rows=latest_snapshot_placeholder_rows,
        cross_level_issues=cross_level_issues,
    )
    return str(path)


def write_program_history_integrity_audit(
    db: Database,
    output_path: str = "output/program-history-integrity-audit.md",
) -> str:
    suspicious_records = _suspicious_program_record_rows(db)
    overlapping_program_ids = _overlapping_program_identity_rows(db)
    impossible_point_totals = _impossible_scoring_rows(db)

    lines: list[str] = [
        "# Program History Integrity Audit",
        "",
        "This file checks whether long-arc program pages are telling believable season stories.",
        "",
        "## Season Record Sanity",
        "",
        "Completed-game thresholds used for quick anomaly scans:",
        "",
    ]

    for level_code in ("FBS", "FCS", "DII", "DIII"):
        lines.append(f"- `{level_code}`: flag anything above `{MAX_COMPLETED_GAMES_BY_LEVEL[level_code]}` completed games")

    lines.extend(
        [
            "",
            f"- Suspicious season records above the level threshold: `{len(suspicious_records)}`",
            f"- Program identities split across multiple team IDs with overlapping seasons: `{len(overlapping_program_ids)}`",
            f"- Completed games with impossible negative scores: `{len(impossible_point_totals)}`",
            "",
        ]
    )

    if suspicious_records:
        lines.extend(
            [
                "### Suspicious Season Records",
                "",
                "| Season | Team | Level | Conference | Record | Completed Games | Postseason Games | Threshold |",
                "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
            ]
        )
        for row in suspicious_records[:60]:
            record = f"{int(row.get('wins') or 0)}-{int(row.get('losses') or 0)}"
            ties = int(row.get("ties") or 0)
            if ties:
                record += f"-{ties}"
            lines.append(
                f"| {int(row['season_year'])} | {row['team_name']} | {row['level_code']} | {row.get('conference_name') or ''} | "
                f"{record} | {int(row.get('completed_games') or 0)} | {int(row.get('postseason_games') or 0)} | "
                f"{int(row.get('max_allowed_games') or 0)} |"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "### Suspicious Season Records",
                "",
                "- No season records exceeded the quick sanity thresholds.",
                "",
            ]
        )

    if overlapping_program_ids:
        lines.extend(
            [
                "### Overlapping Program Identities",
                "",
                "These rows mean the same canonical school name is attached to multiple internal team IDs during overlapping seasons.",
                "That is the main structural risk for doubled historical records on program pages.",
                "",
                "| Team Name | Team ID A | Team ID B | Overlap Start | Overlap End | Seasons A | Seasons B |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in overlapping_program_ids[:40]:
            lines.append(
                f"| {row['team_name']} | {int(row['team_id_a'])} | {int(row['team_id_b'])} | "
                f"{int(row['overlap_start'])} | {int(row['overlap_end'])} | "
                f"{int(row['season_count_a'])} | {int(row['season_count_b'])} |"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "### Overlapping Program Identities",
                "",
                "- No overlapping same-name program identities were detected.",
                "",
            ]
        )

    if impossible_point_totals:
        lines.extend(
            [
                "### Impossible Scoring Rows",
                "",
                "| Season | Week | Matchup | Home Points | Away Points | Status |",
                "| --- | ---: | --- | ---: | ---: | --- |",
            ]
        )
        for row in impossible_point_totals[:30]:
            lines.append(
                f"| {int(row['season_year'])} | {int(row.get('week') or 0)} | {row['home_team_name']} vs {row['away_team_name']} | "
                f"{int(row.get('home_points') or 0)} | {int(row.get('away_points') or 0)} | {row.get('status') or ''} |"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "### Impossible Scoring Rows",
                "",
                "- No negative completed-game scores were detected.",
                "",
            ]
        )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_program_history_integrity_sidecar(
        output_path=path,
        suspicious_records=suspicious_records,
        overlapping_program_ids=overlapping_program_ids,
        impossible_point_totals=impossible_point_totals,
    )
    return str(path)


def _write_competition_integrity_sidecar(
    *,
    output_path: Path,
    latest_snapshot: dict[str, Any] | None,
    postseason_carryover: list[dict[str, Any]],
    regular_future_year: list[dict[str, Any]],
    duplicate_signatures: list[dict[str, Any]],
    same_day_collisions: list[dict[str, Any]],
    level_transitions: list[dict[str, Any]],
    current_identity_drift: list[dict[str, Any]],
    generic_placeholders: list[dict[str, Any]],
    latest_snapshot_placeholder_rows: list[dict[str, Any]],
    cross_level_issues: list[dict[str, Any]],
) -> None:
    payload = {
        "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "markdownPath": output_path.as_posix(),
        "latestSnapshot": None
        if latest_snapshot is None
        else {
            "modelRunId": int(latest_snapshot["model_run_id"]),
            "seasonYear": int(latest_snapshot["season_year"]),
            "week": int(latest_snapshot["week"]),
        },
        "summary": {
            "postseasonCarryoverGames": len(postseason_carryover),
            "regularFutureYearGames": len(regular_future_year),
            "duplicateGameSignatures": len(duplicate_signatures),
            "sameDayTeamCollisions": len(same_day_collisions),
            "currentIdentityDriftRows": len(current_identity_drift),
            "genericPlaceholderTeamSeasons": len(generic_placeholders),
            "levelTransitions": len(level_transitions),
            "latestSnapshotPlaceholderRows": len(latest_snapshot_placeholder_rows),
            "crossLevelPeerIssues": len(cross_level_issues),
        },
        "seasonContinuity": {
            "postseasonCarryoverSamples": _trim_rows(postseason_carryover, 25),
            "regularFutureYearRows": _trim_rows(regular_future_year, 25),
        },
        "duplicateAndCollisionChecks": {
            "duplicateSignatureRows": _trim_rows(duplicate_signatures, 25),
            "sameDayTeamCollisionRows": _trim_rows(same_day_collisions, 25),
        },
        "levelAndConferenceIntegrity": {
            "currentIdentityDriftRows": _trim_rows(current_identity_drift, 50),
            "genericPlaceholderRows": _trim_rows(generic_placeholders, 100),
            "levelTransitionRows": _trim_rows(level_transitions, 100),
        },
        "latestBoardIntegrity": {
            "latestSnapshotPlaceholderRows": _trim_rows(latest_snapshot_placeholder_rows, 50),
            "crossLevelPeerIssues": _trim_rows(cross_level_issues, 50),
        },
    }
    _write_json_sidecar(output_path, payload)


def _write_program_history_integrity_sidecar(
    *,
    output_path: Path,
    suspicious_records: list[dict[str, Any]],
    overlapping_program_ids: list[dict[str, Any]],
    impossible_point_totals: list[dict[str, Any]],
) -> None:
    payload = {
        "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "markdownPath": output_path.as_posix(),
        "thresholds": MAX_COMPLETED_GAMES_BY_LEVEL,
        "summary": {
            "suspiciousSeasonRecords": len(suspicious_records),
            "overlappingProgramIdentities": len(overlapping_program_ids),
            "impossiblePointTotals": len(impossible_point_totals),
        },
        "suspiciousSeasonRecords": _trim_rows(suspicious_records, 100),
        "overlappingProgramIdentities": _trim_rows(overlapping_program_ids, 100),
        "impossibleScoringRows": _trim_rows(impossible_point_totals, 100),
    }
    _write_json_sidecar(output_path, payload)


def _trim_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return rows[:limit]


def _write_json_sidecar(output_path: Path, payload: dict[str, object]) -> None:
    output_path.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _latest_snapshot(db: Database) -> dict[str, Any] | None:
    return db.query_one(
        """
        select mr.model_run_id, mr.season_year, mr.week
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


def _postseason_carryover_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select
          g.season_year,
          substr(g.start_time_utc, 1, 10) as game_date,
          g.week,
          g.season_phase,
          ht.canonical_name as home_team_name,
          at.canonical_name as away_team_name
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where g.season_type = 'postseason'
          and cast(substr(g.start_time_utc, 1, 4) as integer) > g.season_year
        order by g.start_time_utc asc, g.game_id asc
        """
    )


def _regular_future_year_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select
          g.season_year,
          substr(g.start_time_utc, 1, 10) as game_date,
          g.week,
          ht.canonical_name as home_team_name,
          at.canonical_name as away_team_name
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where g.season_type <> 'postseason'
          and cast(substr(g.start_time_utc, 1, 4) as integer) > g.season_year
        order by g.start_time_utc asc, g.game_id asc
        """
    )


def _duplicate_game_signature_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select
          g.season_year,
          g.start_time_utc,
          ht.canonical_name as home_team_name,
          at.canonical_name as away_team_name,
          count(*) as copies
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        group by g.season_year, g.home_team_id, g.away_team_id, g.start_time_utc
        having count(*) > 1
        order by copies desc, g.season_year desc, g.start_time_utc desc
        """
    )


def _same_day_team_collision_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        with appearances as (
          select
            g.season_year,
            substr(g.start_time_utc, 1, 10) as game_date,
            g.home_team_id as team_id,
            case when g.home_points is not null and g.away_points is not null then 1 else 0 end as completed_flag,
            ht.canonical_name || ' vs ' || at.canonical_name as matchup
          from games g
          join teams ht on ht.team_id = g.home_team_id
          join teams at on at.team_id = g.away_team_id
          union all
          select
            g.season_year,
            substr(g.start_time_utc, 1, 10) as game_date,
            g.away_team_id as team_id,
            case when g.home_points is not null and g.away_points is not null then 1 else 0 end as completed_flag,
            ht.canonical_name || ' vs ' || at.canonical_name as matchup
          from games g
          join teams ht on ht.team_id = g.home_team_id
          join teams at on at.team_id = g.away_team_id
        ),
        rolled as (
          select
            season_year,
            game_date,
            team_id,
            count(*) as games_on_day,
            sum(completed_flag) as completed_games,
            group_concat(matchup, ' | ') as sample_matchups
          from appearances
          group by season_year, game_date, team_id
          having count(*) > 1
        )
        select
          r.season_year,
          r.game_date,
          t.canonical_name as team_name,
          r.games_on_day,
          r.completed_games,
          r.sample_matchups
        from rolled r
        join teams t on t.team_id = r.team_id
        order by r.season_year desc, r.game_date desc, t.canonical_name asc
        """
    )


def _suspicious_program_record_rows(db: Database) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        with completed_results as (
          select
            g.season_year,
            g.season_type,
            g.home_team_id as team_id,
            case when g.home_points > g.away_points then 1 else 0 end as win_flag,
            case when g.home_points < g.away_points then 1 else 0 end as loss_flag,
            case when g.home_points = g.away_points then 1 else 0 end as tie_flag
          from games g
          where g.home_points is not null and g.away_points is not null
          union all
          select
            g.season_year,
            g.season_type,
            g.away_team_id as team_id,
            case when g.away_points > g.home_points then 1 else 0 end as win_flag,
            case when g.away_points < g.home_points then 1 else 0 end as loss_flag,
            case when g.away_points = g.home_points then 1 else 0 end as tie_flag
          from games g
          where g.home_points is not null and g.away_points is not null
        ),
        season_rollup as (
          select
            season_year,
            team_id,
            sum(win_flag) as wins,
            sum(loss_flag) as losses,
            sum(tie_flag) as ties,
            count(*) as completed_games,
            sum(case when season_type = 'postseason' then 1 else 0 end) as postseason_games
          from completed_results
          group by season_year, team_id
        )
        select
          sr.season_year,
          sr.team_id,
          t.canonical_name as team_name,
          coalesce(ts.level_code, t.level_code) as level_code,
          c.conference_name,
          sr.wins,
          sr.losses,
          sr.ties,
          sr.completed_games,
          sr.postseason_games
        from season_rollup sr
        join teams t on t.team_id = sr.team_id
        left join team_seasons ts
          on ts.team_id = sr.team_id
         and ts.season_year = sr.season_year
        left join conferences c on c.conference_id = ts.conference_id
        order by sr.completed_games desc, sr.season_year desc, t.canonical_name asc
        """
    )

    suspicious: list[dict[str, Any]] = []
    for row in rows:
        level_code = str(row.get("level_code") or "")
        conference_name = None if row.get("conference_name") is None else str(row.get("conference_name"))
        if not is_site_eligible_team(level_code, conference_name):
            continue
        max_allowed_games = MAX_COMPLETED_GAMES_BY_LEVEL.get(level_code, 18)
        completed_games = int(row.get("completed_games") or 0)
        if completed_games > max_allowed_games:
            suspicious.append(
                {
                    **row,
                    "level_code": level_code,
                    "conference_name": conference_name,
                    "max_allowed_games": max_allowed_games,
                }
            )
    return suspicious


def _overlapping_program_identity_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        with team_season_bounds as (
          select
            t.team_id,
            t.canonical_name,
            min(ts.season_year) as first_season,
            max(ts.season_year) as last_season,
            count(*) as season_count
          from teams t
          join team_seasons ts on ts.team_id = t.team_id
          group by t.team_id, t.canonical_name
        )
        select
          a.canonical_name as team_name,
          a.team_id as team_id_a,
          b.team_id as team_id_b,
          max(a.first_season, b.first_season) as overlap_start,
          min(a.last_season, b.last_season) as overlap_end,
          a.season_count as season_count_a,
          b.season_count as season_count_b
        from team_season_bounds a
        join team_season_bounds b
          on lower(a.canonical_name) = lower(b.canonical_name)
         and a.team_id < b.team_id
        where max(a.first_season, b.first_season) <= min(a.last_season, b.last_season)
        order by team_name asc, overlap_start desc
        """
    )


def _impossible_scoring_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select
          g.season_year,
          g.week,
          g.status,
          ht.canonical_name as home_team_name,
          at.canonical_name as away_team_name,
          g.home_points,
          g.away_points
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where g.home_points is not null
          and g.away_points is not null
          and (g.home_points < 0 or g.away_points < 0)
        order by g.season_year desc, g.week desc, g.game_id desc
        """
    )


def _level_transition_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        with transitions as (
          select
            t.canonical_name as team_name,
            ts.season_year,
            ts.level_code,
            c.conference_name,
            lag(ts.level_code) over (partition by ts.team_id order by ts.season_year) as prev_level
          from team_seasons ts
          join teams t on t.team_id = ts.team_id
          left join conferences c on c.conference_id = ts.conference_id
        )
        select team_name, season_year, prev_level, level_code, conference_name
        from transitions
        where prev_level is not null
          and prev_level <> level_code
        order by season_year desc, team_name asc
        """
    )


def _current_identity_drift_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        with latest as (
          select team_id, max(season_year) as latest_season_year
          from team_seasons
          group by team_id
        )
        select
          t.canonical_name as team_name,
          latest.latest_season_year,
          t.level_code as current_level_code,
          ts.level_code as latest_level_code,
          current_conf.conference_name as current_conference_name,
          latest_conf.conference_name as latest_conference_name
        from teams t
        join latest on latest.team_id = t.team_id
        join team_seasons ts
          on ts.team_id = t.team_id
         and ts.season_year = latest.latest_season_year
        left join conferences current_conf on current_conf.conference_id = t.current_conference_id
        left join conferences latest_conf on latest_conf.conference_id = ts.conference_id
        where coalesce(t.level_code, '') <> coalesce(ts.level_code, '')
           or coalesce(t.current_conference_id, -1) <> coalesce(ts.conference_id, -1)
        order by latest.latest_season_year desc, t.canonical_name asc
        """
    )


def _generic_placeholder_rows(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select
          ts.season_year,
          t.canonical_name as team_name,
          ts.level_code,
          c.conference_name
        from team_seasons ts
        join teams t on t.team_id = ts.team_id
        left join conferences c on c.conference_id = ts.conference_id
        where c.conference_name in ('FBS', 'FCS', 'DII', 'DIII')
        order by ts.season_year desc, t.canonical_name asc
        """
    )


def _latest_snapshot_placeholder_rows(db: Database, latest_snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if latest_snapshot is None:
        return []
    return db.query_all(
        """
        with ranked as (
          select
            row_number() over (
              order by p.power_rating desc, coalesce(r.resume_score, 0) desc, t.canonical_name asc
            ) as overall_rank,
            t.canonical_name as team_name,
            coalesce(ts.level_code, t.level_code) as level_code,
            c.conference_name,
            p.power_rating
          from power_ratings_weekly p
          join teams t on t.team_id = p.team_id
          left join team_seasons ts
            on ts.team_id = p.team_id
           and ts.season_year = p.season_year
          left join conferences c on c.conference_id = ts.conference_id
          left join resume_ratings_weekly r
            on r.model_run_id = p.model_run_id
           and r.team_id = p.team_id
           and r.week = p.week
          where p.model_run_id = %(model_run_id)s
            and p.week = %(week)s
        )
        select *
        from ranked
        where conference_name in ('FBS', 'FCS', 'DII', 'DIII')
        order by overall_rank asc
        """,
        {
            "model_run_id": int(latest_snapshot["model_run_id"]),
            "week": int(latest_snapshot["week"]),
        },
    )


def _latest_snapshot_cross_level_issues(db: Database, latest_snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if latest_snapshot is None:
        return []
    rows = db.query_all(
        """
        select
          t.slug,
          t.canonical_name as team_name,
          coalesce(ts.level_code, t.level_code) as level_code,
          p.power_rating,
          coalesce(r.resume_score, 0) as resume_score
        from power_ratings_weekly p
        join teams t on t.team_id = p.team_id
        left join team_seasons ts
          on ts.team_id = p.team_id
         and ts.season_year = p.season_year
        left join conferences c on c.conference_id = ts.conference_id
        left join resume_ratings_weekly r
          on r.model_run_id = p.model_run_id
         and r.team_id = p.team_id
         and r.week = p.week
        where p.model_run_id = %(model_run_id)s
          and p.week = %(week)s
        order by p.power_rating desc, coalesce(r.resume_score, 0) desc, t.canonical_name asc
        """,
        {
            "model_run_id": int(latest_snapshot["model_run_id"]),
            "week": int(latest_snapshot["week"]),
        },
    )
    normalized_rows = [
        row
        for row in rows
        if row.get("level_code")
    ]
    issues: list[dict[str, Any]] = []
    for row in normalized_rows:
        team_level = str(row.get("level_code") or "")
        candidates = [
            candidate
            for candidate in normalized_rows
            if str(candidate.get("slug") or "") != str(row.get("slug") or "")
            and str(candidate.get("level_code") or "") != team_level
        ]
        if not candidates:
            continue
        best = min(
            candidates,
            key=lambda candidate: (
                abs(float(candidate.get("power_rating") or 0.0) - float(row.get("power_rating") or 0.0)),
                abs(float(candidate.get("resume_score") or 0.0) - float(row.get("resume_score") or 0.0)),
            ),
        )
        if str(best.get("level_code") or "") == team_level:
            issues.append(
                {
                    "team_name": str(row.get("team_name") or ""),
                    "team_level": team_level,
                    "peer_name": str(best.get("team_name") or ""),
                    "peer_level": str(best.get("level_code") or ""),
                }
            )
    return issues
