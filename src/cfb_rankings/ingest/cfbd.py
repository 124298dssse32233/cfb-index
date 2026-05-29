from __future__ import annotations

import json
from typing import Any

from cfb_rankings.clients.cfbd import CfbdClient
from cfb_rankings.db import Database
from cfb_rankings.ingest.common import (
    maybe_float,
    maybe_int,
    normalize_competition_week,
    normalize_cfbd_classification,
    normalize_season_phase,
    normalize_status,
    parse_datetime,
)
from cfb_rankings.storage import Repository, TeamIdentity
from cfb_rankings.utils import normalize_name


def ingest_cfbd_week(
    repository: Repository,
    db: Database,
    client: CfbdClient,
    season: int,
    week: int,
    season_type: str = "regular",
    include_lines: bool = True,
    include_weather: bool = True,
    include_advanced_game_stats: bool = True,
    include_drives: bool = True,
    include_plays: bool = True,
    include_game_player_stats: bool = False,
    game_player_stat_classifications: list[str] | None = None,
) -> None:
    repository.ensure_season(season)
    _log_week_step(season, week, season_type, "loading games")
    games = _safe_fetch(lambda: client.get_games(year=season, week=week, season_type=season_type), "games")
    if games:
        _ingest_games(repository, games, season)
    elif not _has_local_games_for_week(db, season=season, week=week, season_type=season_type):
        raise RuntimeError(f"Could not load games for season {season}, week {week}, {season_type}.")
    if include_lines:
        _log_week_step(season, week, season_type, "loading betting lines")
        _ingest_lines(
            repository,
            db,
            _safe_fetch(lambda: client.get_lines(year=season, week=week, season_type=season_type), "lines"),
        )
    else:
        _log_week_step(season, week, season_type, "skipping betting lines")
    if include_weather:
        _log_week_step(season, week, season_type, "loading weather")
        _ingest_weather(
            repository,
            db,
            _safe_fetch(lambda: client.get_weather(year=season, week=week, season_type=season_type), "weather"),
        )
    else:
        _log_week_step(season, week, season_type, "skipping weather")
    if include_advanced_game_stats:
        _log_week_step(season, week, season_type, "loading advanced game stats")
        _ingest_advanced_game_stats(
            repository,
            db,
            _safe_fetch(
                lambda: client.get_advanced_game_stats(year=season, week=week, season_type=season_type),
                "advanced game stats",
            ),
        )
    else:
        _log_week_step(season, week, season_type, "skipping advanced game stats")
    if include_drives:
        _log_week_step(season, week, season_type, "loading drives")
        _ingest_drives(
            repository,
            db,
            _safe_fetch(lambda: client.get_drives(year=season, week=week, season_type=season_type), "drives"),
        )
    else:
        _log_week_step(season, week, season_type, "skipping drives")
    if include_plays:
        _log_week_step(season, week, season_type, "loading plays")
        _ingest_plays(
            repository,
            db,
            _safe_fetch(lambda: client.get_plays(year=season, week=week, season_type=season_type), "plays"),
        )
    else:
        _log_week_step(season, week, season_type, "skipping plays")
    if include_game_player_stats:
        _log_week_step(season, week, season_type, "loading game player stats")
        player_game_rows: list[dict[str, Any]] = []
        classifications = _game_stat_classifications_for_week(
            db,
            season=season,
            week=week,
            season_type=season_type,
            requested=game_player_stat_classifications,
        )
        _log_week_step(
            season,
            week,
            season_type,
            f"targeting game player stat classifications: {', '.join(classification.upper() for classification in classifications)}",
        )
        for classification in classifications:
            _log_week_step(season, week, season_type, f"loading game player stats for {classification.upper()}")
            player_game_rows.extend(
                _safe_fetch(
                    lambda cl=classification: client.get_game_player_stats(
                        year=season,
                        week=week,
                        season_type=season_type,
                        classification=cl,
                    ),
                    f"game player stats {classification}",
                )
            )
        _ingest_game_player_stats(
            repository,
            db,
            player_game_rows,
            season=season,
            week=week,
            season_type=season_type,
        )
    else:
        _log_week_step(season, week, season_type, "skipping game player stats")
    if include_drives or include_plays:
        _log_week_step(season, week, season_type, "deriving possession metrics")
        _derive_possession_quality_metrics(db, season=season, week=week, season_type=season_type)
    else:
        _log_week_step(season, week, season_type, "skipping possession metric derivation")


def ingest_cfbd_preseason(
    repository: Repository,
    db: Database,
    client: CfbdClient,
    season: int,
    teams: list[str],
    classification: str | None = None,
) -> None:
    repository.ensure_season(season)
    print(f"[CFBD preseason] {season}: loading returning production...", flush=True)
    _ingest_returning_production(repository, db, client.get_returning_production(season), season)
    print(f"[CFBD preseason] {season}: loading talent composites...", flush=True)
    _ingest_talent(repository, db, client.get_talent(season), season)
    print(f"[CFBD preseason] {season}: loading team recruiting summaries...", flush=True)
    _ingest_recruiting(repository, db, client.get_recruiting_teams(season), season)
    print(f"[CFBD preseason] {season}: loading transfer portal...", flush=True)
    _ingest_transfer_portal(repository, db, client.get_transfer_portal(season), season)
    if teams:
        for index, team in enumerate(teams, start=1):
            print(f"[CFBD preseason] {season}: loading roster {index}/{len(teams)} for {team}...", flush=True)
            _ingest_roster(repository, db, client.get_roster(team=team, year=season), season)
    elif classification:
        print(f"[CFBD preseason] {season}: loading classification-wide roster snapshot for {classification.upper()}...", flush=True)
        _ingest_roster(repository, db, client.get_roster(year=season, classification=classification), season)
    recruit_start_year = max(2000, season - 5)
    for recruit_season in range(recruit_start_year, season + 1):
        print(f"[CFBD preseason] {season}: loading player recruiting class {recruit_season}...", flush=True)
        recruit_rows: list[dict[str, Any]] = []
        for recruit_classification in ("HighSchool", "JUCO", "PrepSchool"):
            recruit_rows.extend(
                _safe_fetch(
                    lambda year=recruit_season, rc=recruit_classification: client.get_recruits(year=year, classification=rc),
                    f"player recruiting {recruit_season} {recruit_classification}",
                )
            )
        if not recruit_rows:
            recruit_rows = _safe_fetch(
                lambda year=recruit_season: client.get_recruits(year=year),
                f"player recruiting {recruit_season} fallback",
            )
        _ingest_player_recruiting(repository, db, recruit_rows, recruit_season)


def sync_cfbd_team_seasons(
    repository: Repository,
    db: Database,
    client: CfbdClient,
    seasons: list[int],
) -> None:
    for season in seasons:
        repository.ensure_season(season)
        week_rows = db.query_all(
            """
            select distinct season_type, source_week
            from games
            where season_year = %(season)s
              and source_week is not null
            order by
              case season_type
                when 'regular' then 1
                when 'postseason' then 2
                else 3
              end,
              source_week
            """,
            {"season": season},
        )
        if not week_rows:
            continue
        seen: set[tuple[str, int]] = set()
        for row in week_rows:
            season_type = str(row.get("season_type") or "regular")
            week = int(row.get("source_week") or 0)
            if week <= 0 or (season_type, week) in seen:
                continue
            seen.add((season_type, week))
            games = _safe_fetch(
                lambda st=season_type, w=week: client.get_games(year=season, week=w, season_type=st),
                f"games {season} {season_type} week {week}",
            )
            if games:
                _ingest_games(repository, games, season)


def sync_cfbd_team_locations(
    repository: Repository,
    db: Database,
    client: CfbdClient,
    season: int,
    classification: str | None = None,
) -> int:
    """Backfill ``teams.city`` / ``teams.state`` from the CFBD ``/teams`` endpoint.

    Teams are created from game payloads, which carry no location, so
    ``teams.state`` is empty site-wide. That silently breaks the Recruiting
    Footprint home-state highlight and blocks every geography chart. The
    location-bearing ``/teams`` endpoint is never hit during normal ingest;
    this closes that gap. Returns the number of teams whose location was set.

    Only fills blanks (``coalesce``) so a future authoritative source can't be
    clobbered, and never overwrites a non-empty value with an empty one.
    """
    teams = _safe_fetch(
        lambda: client.get_teams(year=season, classification=classification),
        f"team locations {season}",
    )
    updated = 0
    for team in teams:
        location = team.get("location") or {}
        state = str(location.get("state") or "").strip()
        city = str(location.get("city") or "").strip()
        if not state and not city:
            continue

        team_id: int | None = None
        source_id = team.get("id")
        if source_id is not None:
            team_id = repository.find_team_id("cfbd", str(source_id))
        if team_id is None:
            school = str(team.get("school") or "").strip()
            if school:
                level_code = normalize_cfbd_classification(
                    team.get("classification"),
                    str(team.get("conference") or ""),
                )
                team_id = repository.match_team_by_name(school, level_code)
        if team_id is None:
            continue

        db.execute(
            """
            update teams
            set city = coalesce(nullif(%(city)s, ''), city),
                state = coalesce(nullif(%(state)s, ''), state),
                updated_at = CURRENT_TIMESTAMP
            where team_id = %(team_id)s
            """,
            {"city": city, "state": state, "team_id": team_id},
        )
        updated += 1
    return updated


def _log_week_step(season: int, week: int, season_type: str, message: str) -> None:
    print(f"[CFBD] {season} {season_type} week {week}: {message}...", flush=True)


def _ingest_games(repository: Repository, games: list[dict[str, Any]], season: int) -> None:
    for game in games:
        raw_week = maybe_int(game.get("week")) or 0
        season_type = str(game.get("seasonType") or "regular")
        start_time_utc = parse_datetime(str(game.get("startDate")))
        home_name = str(game.get("homeTeam"))
        away_name = str(game.get("awayTeam"))
        home_level_code = normalize_cfbd_classification(
            game.get("homeClassification"),
            str(game.get("homeConference") or ""),
        )
        away_level_code = normalize_cfbd_classification(
            game.get("awayClassification"),
            str(game.get("awayConference") or ""),
        )
        home_conference = str(game.get("homeConference") or home_level_code)
        away_conference = str(game.get("awayConference") or away_level_code)

        home_team_id = repository.get_or_create_team(
            "cfbd",
            str(game.get("homeId") or f"team:{season}:{home_name}"),
            TeamIdentity(
                canonical_name=home_name,
                school_name=home_name,
                short_name=home_name,
                level_code=home_level_code,
                conference_name=home_conference,
            ),
        )
        repository.upsert_team_season(
            team_id=home_team_id,
            season_year=season,
            level_code=home_level_code,
            conference_name=home_conference,
        )

        away_team_id = repository.get_or_create_team(
            "cfbd",
            str(game.get("awayId") or f"team:{season}:{away_name}"),
            TeamIdentity(
                canonical_name=away_name,
                school_name=away_name,
                short_name=away_name,
                level_code=away_level_code,
                conference_name=away_conference,
            ),
        )
        repository.upsert_team_season(
            team_id=away_team_id,
            season_year=season,
            level_code=away_level_code,
            conference_name=away_conference,
        )

        payload = {
            "season_year": season,
            "season_type": season_type,
            "season_phase": normalize_season_phase(
                season_type,
                str(game.get("notes") or ""),
            ),
            "week": normalize_competition_week(season, season_type, raw_week, start_time_utc),
            "source_week": raw_week,
            "start_time_utc": start_time_utc,
            "status": normalize_status(bool(game.get("completed")), maybe_int(game.get("homePoints")), maybe_int(game.get("awayPoints"))),
            "neutral_site": bool(game.get("neutralSite")),
            "venue_id": None,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_points": maybe_int(game.get("homePoints")),
            "away_points": maybe_int(game.get("awayPoints")),
            "attendance": maybe_int(game.get("attendance")),
            "notes": str(game.get("notes") or ""),
        }
        repository.get_or_create_game("cfbd", str(game.get("id")), payload)


def _ingest_lines(repository: Repository, db: Database, lines: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for line in lines:
        game_id = _find_game_id(repository, line)
        if game_id is None:
            continue
        lines_items = line.get("lines") or []
        best_line = lines_items[-1] if lines_items else {}
        rows.append(
            {
                "game_id": game_id,
                "provider": str(best_line.get("provider") or "cfbd"),
                "spread_home_open": maybe_float(best_line.get("spreadOpen")),
                "spread_home_close": maybe_float(best_line.get("spread")),
                "total_open": maybe_float(best_line.get("overUnderOpen")),
                "total_close": maybe_float(best_line.get("overUnder")),
                "moneyline_home_open": maybe_int(best_line.get("homeMoneylineOpen")),
                "moneyline_home_close": maybe_int(best_line.get("homeMoneyline")),
                "moneyline_away_open": maybe_int(best_line.get("awayMoneylineOpen")),
                "moneyline_away_close": maybe_int(best_line.get("awayMoneyline")),
                "line_timestamp_utc": parse_datetime(str(line.get("startDate"))),
            }
        )
    db.upsert_many("game_lines", rows, conflict_columns=["game_id"], update_columns=[column for column in rows[0].keys() if column != "game_id"] if rows else None)


def _ingest_weather(repository: Repository, db: Database, weather_rows: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for weather in weather_rows:
        game_id = _find_game_id(repository, weather)
        if game_id is None:
            continue
        rows.append(
            {
                "game_id": game_id,
                "temperature_f": maybe_float(weather.get("temperature")),
                "wind_mph": maybe_float(weather.get("windSpeed")),
                "humidity_pct": maybe_float(weather.get("humidity")),
                "precipitation_mm": maybe_float(weather.get("precipitation")),
                "conditions_text": str(weather.get("weatherCondition") or ""),
            }
        )
    db.upsert_many("game_weather", rows, conflict_columns=["game_id"], update_columns=[column for column in rows[0].keys() if column != "game_id"] if rows else None)


def _ingest_advanced_game_stats(repository: Repository, db: Database, box_scores: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for box_score in box_scores:
        game_id = _find_game_id(repository, box_score)
        if game_id is None:
            continue

        team_id = repository.resolve_game_team_id(game_id, str(box_score.get("team")))
        opponent_id = repository.resolve_game_team_id(game_id, str(box_score.get("opponent")))
        if team_id is None or opponent_id is None:
            continue
        offense = box_score.get("offense") or {}
        defense = box_score.get("defense") or {}
        rushing_off = offense.get("rushingPlays") or {}
        rushing_def = defense.get("rushingPlays") or {}
        passing_off = offense.get("passingPlays") or {}
        passing_def = defense.get("passingPlays") or {}
        rows.append(
            {
                "game_id": game_id,
                "team_id": team_id,
                "opponent_team_id": opponent_id,
                "offense_ppa": maybe_float(offense.get("ppa")),
                "defense_ppa": maybe_float(defense.get("ppa")),
                "success_rate_off": maybe_float(offense.get("successRate")),
                "success_rate_def": maybe_float(defense.get("successRate")),
                "explosiveness_off": maybe_float(offense.get("explosiveness")),
                "explosiveness_def": maybe_float(defense.get("explosiveness")),
                "rushing_ppa_off": maybe_float(rushing_off.get("ppa")),
                "rushing_ppa_def": maybe_float(rushing_def.get("ppa")),
                "passing_ppa_off": maybe_float(passing_off.get("ppa")),
                "passing_ppa_def": maybe_float(passing_def.get("ppa")),
                "finishing_drives_off": None,
                "finishing_drives_def": None,
                "havoc_off": None,
                "havoc_def": None,
                "field_position_off": None,
                "field_position_def": None,
                "source_name": "cfbd",
            }
        )
    db.upsert_many("team_game_advanced_stats", rows, conflict_columns=["game_id", "team_id", "source_name"])


def _ingest_drives(repository: Repository, db: Database, drives: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for drive in drives:
        game_id = _find_game_id(repository, drive)
        offense_team_id = repository.resolve_game_team_id(game_id, str(drive.get("offense"))) if game_id is not None else None
        defense_team_id = repository.resolve_game_team_id(game_id, str(drive.get("defense"))) if game_id is not None else None
        if game_id is None or offense_team_id is None or defense_team_id is None:
            continue
        rows.append(
            {
                "game_id": game_id,
                "source_drive_id": str(drive.get("id") or ""),
                "offense_team_id": offense_team_id,
                "defense_team_id": defense_team_id,
                "period": maybe_int(drive.get("startPeriod")),
                "drive_number": maybe_int(drive.get("driveNumber")),
                "start_yardline": maybe_int(drive.get("startYardsToGoal")),
                "end_yardline": maybe_int(drive.get("endYardsToGoal")),
                "play_count": maybe_int(drive.get("plays")),
                "yards": maybe_int(drive.get("yards")),
                "result": str(drive.get("driveResult") or drive.get("result") or ""),
                "points_scored": _drive_points_scored(drive),
                "is_garbage_time": bool(drive.get("garbageTime") or False),
            }
        )
    db.upsert_many("drives", rows, conflict_columns=["game_id", "source_drive_id"])


def _ingest_plays(repository: Repository, db: Database, plays: list[dict[str, Any]]) -> None:
    drive_lookup_rows = db.query_all(
        """
        select drive_id, game_id, source_drive_id
        from drives
        where source_drive_id is not null
        """
    )
    drive_lookup = {
        (int(row["game_id"]), str(row["source_drive_id"])): int(row["drive_id"])
        for row in drive_lookup_rows
    }
    rows: list[dict[str, Any]] = []
    for play in plays:
        game_id = _find_game_id(repository, play)
        offense_team_id = repository.resolve_game_team_id(game_id, str(play.get("offense"))) if game_id is not None else None
        defense_team_id = repository.resolve_game_team_id(game_id, str(play.get("defense"))) if game_id is not None else None
        if game_id is None or offense_team_id is None or defense_team_id is None:
            continue
        source_drive_id = str(play.get("driveId") or "")
        rows.append(
            {
                "game_id": game_id,
                "drive_id": drive_lookup.get((game_id, source_drive_id)),
                "source_play_id": str(play.get("id") or ""),
                "offense_team_id": offense_team_id,
                "defense_team_id": defense_team_id,
                "period": maybe_int(play.get("period")),
                "clock_minutes": maybe_int(play.get("clock", {}).get("minutes") if isinstance(play.get("clock"), dict) else None),
                "clock_seconds": maybe_int(play.get("clock", {}).get("seconds") if isinstance(play.get("clock"), dict) else None),
                "down": maybe_int(play.get("down")),
                "distance": maybe_int(play.get("distance")),
                "yard_line": maybe_int(play.get("yardline") or play.get("yardLine") or play.get("yardsToGoal")),
                "play_type": str(play.get("playType") or ""),
                "yards_gained": maybe_int(play.get("yardsGained")) or 0,
                "epa": maybe_float(play.get("epa")),
                "ppa": maybe_float(play.get("ppa")),
                "success_flag": _play_success_flag(play),
                "home_win_prob": maybe_float(play.get("homeWinProb") or play.get("homeWinProbability")),
                "is_garbage_time": bool(play.get("garbageTime") or False),
            }
        )
    db.upsert_many("plays", rows, conflict_columns=["game_id", "source_play_id"])


def _ingest_game_player_stats(
    repository: Repository,
    db: Database,
    game_stat_rows: list[dict[str, Any]],
    season: int,
    week: int,
    season_type: str,
) -> None:
    rows: list[dict[str, Any]] = []
    seen_games: set[int] = set()
    for game_payload in game_stat_rows:
        game_id = _find_game_id(repository, game_payload)
        if game_id is None:
            continue
        seen_games.add(game_id)
        for team_payload in game_payload.get("teams") or []:
            team_name = str(team_payload.get("team") or "").strip()
            if not team_name:
                continue
            team_id = repository.resolve_game_team_id(game_id, team_name)
            if team_id is None:
                continue
            conference_name = str(team_payload.get("conference") or "").strip() or None
            for category_payload in team_payload.get("categories") or []:
                category_name = str(category_payload.get("name") or "").strip()
                if not category_name:
                    continue
                for stat_type_payload in category_payload.get("types") or []:
                    stat_type_name = str(stat_type_payload.get("name") or "").strip()
                    if not stat_type_name:
                        continue
                    for athlete_payload in stat_type_payload.get("athletes") or []:
                        source_player_id = str(athlete_payload.get("id") or "").strip()
                        player_name = str(athlete_payload.get("name") or "").strip()
                        if not player_name or normalize_name(player_name) == "team":
                            continue
                        player_id = _resolve_or_create_game_stat_player(
                            db=db,
                            team_id=team_id,
                            season=season,
                            source_player_id=source_player_id,
                            player_name=player_name,
                            category_name=category_name,
                            team_name=team_name,
                        )
                        stat_text = str(athlete_payload.get("stat") or "").strip()
                        rows.append(
                            {
                                "game_id": game_id,
                                "season_year": season,
                                "week": week,
                                "season_type": season_type,
                                "team_id": team_id,
                                "player_id": player_id,
                                "source_name": "cfbd",
                                "source_player_id": source_player_id,
                                "team_name": team_name,
                                "conference_name": conference_name,
                                "player_name": player_name,
                                "category": category_name,
                                "stat_type": stat_type_name,
                                "stat_value_text": stat_text,
                                "stat_value_num": _maybe_stat_number(stat_text),
                            }
                        )
    if seen_games:
        db.execute_many(
            """
            delete from player_game_stats
            where game_id = :game_id
              and source_name = 'cfbd'
            """,
            [{"game_id": game_id} for game_id in seen_games],
        )
    db.upsert_many(
        "player_game_stats",
        rows,
        conflict_columns=["game_id", "team_id", "source_name", "source_player_id", "category", "stat_type"],
    )


def _derive_possession_quality_metrics(db: Database, season: int, week: int, season_type: str) -> None:
    drive_rows = db.query_all(
        """
        select
          d.drive_id,
          d.game_id,
          d.offense_team_id,
          d.defense_team_id,
          d.start_yardline,
          d.end_yardline,
          d.points_scored
        from drives d
        join games g on g.game_id = d.game_id
        where g.season_year = %(season)s
          and g.week = %(week)s
          and g.season_type = %(season_type)s
        """,
        {"season": season, "week": week, "season_type": season_type},
    )
    if not drive_rows:
        return

    play_rows = db.query_all(
        """
        select drive_id, yard_line
        from plays p
        join games g on g.game_id = p.game_id
        where g.season_year = %(season)s
          and g.week = %(week)s
          and g.season_type = %(season_type)s
          and p.drive_id is not null
        """,
        {"season": season, "week": week, "season_type": season_type},
    )

    min_yards_to_goal_by_drive: dict[int, int] = {}
    for play in play_rows:
        drive_id = int(play["drive_id"])
        yard_line = maybe_int(play.get("yard_line"))
        if yard_line is None:
            continue
        existing = min_yards_to_goal_by_drive.get(drive_id)
        if existing is None or yard_line < existing:
            min_yards_to_goal_by_drive[drive_id] = yard_line

    team_rows: dict[tuple[int, int, int], dict[str, Any]] = {}
    for drive in drive_rows:
        game_id = int(drive["game_id"])
        offense_team_id = int(drive["offense_team_id"])
        defense_team_id = int(drive["defense_team_id"])
        start_yards_to_goal = maybe_int(drive.get("start_yardline"))
        end_yards_to_goal = maybe_int(drive.get("end_yardline"))
        points_scored = maybe_int(drive.get("points_scored")) or 0
        drive_id = int(drive["drive_id"])

        best_yards_to_goal = min_yards_to_goal_by_drive.get(drive_id)
        if best_yards_to_goal is None:
            candidates = [value for value in (start_yards_to_goal, end_yards_to_goal) if value is not None]
            best_yards_to_goal = min(candidates) if candidates else None
        scoring_opportunity = best_yards_to_goal is not None and best_yards_to_goal <= 40
        start_field_position = None if start_yards_to_goal is None else 100.0 - float(start_yards_to_goal)

        offense_key = (game_id, offense_team_id, defense_team_id)
        offense_row = team_rows.setdefault(
            offense_key,
            {
                "game_id": game_id,
                "team_id": offense_team_id,
                "opponent_team_id": defense_team_id,
                "source_name": "cfbd",
                "_field_pos_off": [],
                "_field_pos_def": [],
                "_finish_pts_off": [],
                "_finish_pts_def": [],
            },
        )
        defense_key = (game_id, defense_team_id, offense_team_id)
        defense_row = team_rows.setdefault(
            defense_key,
            {
                "game_id": game_id,
                "team_id": defense_team_id,
                "opponent_team_id": offense_team_id,
                "source_name": "cfbd",
                "_field_pos_off": [],
                "_field_pos_def": [],
                "_finish_pts_off": [],
                "_finish_pts_def": [],
            },
        )

        if start_field_position is not None:
            offense_row["_field_pos_off"].append(start_field_position)
            defense_row["_field_pos_def"].append(start_field_position)
        if scoring_opportunity:
            offense_row["_finish_pts_off"].append(float(points_scored))
            defense_row["_finish_pts_def"].append(float(points_scored))

    rows: list[dict[str, Any]] = []
    for row in team_rows.values():
        rows.append(
            {
                "game_id": row["game_id"],
                "team_id": row["team_id"],
                "opponent_team_id": row["opponent_team_id"],
                "field_position_off": _mean_float(row["_field_pos_off"]),
                "field_position_def": _mean_float(row["_field_pos_def"]),
                "finishing_drives_off": _mean_float(row["_finish_pts_off"]),
                "finishing_drives_def": _mean_float(row["_finish_pts_def"]),
                "source_name": row["source_name"],
            }
        )

    db.upsert_many("team_game_advanced_stats", rows, conflict_columns=["game_id", "team_id", "source_name"])


def _game_stat_classifications_for_week(
    db: Database,
    season: int,
    week: int,
    season_type: str,
    requested: list[str] | None = None,
) -> list[str]:
    normalized_requested = _normalize_requested_game_stat_classifications(requested)
    if normalized_requested:
        return normalized_requested
    rows = db.query_all(
        """
        select distinct lower(level_code) as level_code
        from (
          select coalesce(home_ts.level_code, home_t.level_code) as level_code
          from games g
          join teams home_t on home_t.team_id = g.home_team_id
          left join team_seasons home_ts
            on home_ts.team_id = home_t.team_id
           and home_ts.season_year = g.season_year
          where g.season_year = %(season)s
            and g.week = %(week)s
            and g.season_type = %(season_type)s
          union all
          select coalesce(away_ts.level_code, away_t.level_code) as level_code
          from games g
          join teams away_t on away_t.team_id = g.away_team_id
          left join team_seasons away_ts
            on away_ts.team_id = away_t.team_id
           and away_ts.season_year = g.season_year
          where g.season_year = %(season)s
            and g.week = %(week)s
            and g.season_type = %(season_type)s
        ) levels
        where level_code is not null
        """,
        {"season": season, "week": week, "season_type": season_type},
    )
    mapping = {"fbs": "fbs", "fcs": "fcs", "dii": "ii", "diii": "iii"}
    classifications: list[str] = []
    for row in rows:
        normalized = str(row.get("level_code") or "").strip().lower()
        classification = mapping.get(normalized)
        if classification and classification not in classifications:
            classifications.append(classification)
    return classifications or ["fbs", "fcs", "ii", "iii"]


def _normalize_requested_game_stat_classifications(requested: list[str] | None) -> list[str]:
    if not requested:
        return []
    normalized: list[str] = []
    aliases = {
        "fbs": "fbs",
        "fcs": "fcs",
        "ii": "ii",
        "dii": "ii",
        "division ii": "ii",
        "iii": "iii",
        "diii": "iii",
        "division iii": "iii",
    }
    for value in requested:
        key = str(value or "").strip().lower()
        classification = aliases.get(key)
        if classification and classification not in normalized:
            normalized.append(classification)
    return normalized


def _ingest_returning_production(repository: Repository, db: Database, rows_in: list[dict[str, Any]], season: int) -> None:
    rows: list[dict[str, Any]] = []
    for item in rows_in:
        team_id = repository.match_team_by_name(str(item.get("team")), level_code="FBS")
        if team_id is None:
            continue
        percent_ppa = maybe_float(item.get("percentPPA"))
        percent_passing_ppa = maybe_float(item.get("percentPassingPPA"))
        rows.append(
            {
                "team_id": team_id,
                "season_year": season,
                # Legacy columns remain for compatibility. The v2-specific fields below are the reliable source.
                "returning_total": percent_ppa,
                "returning_offense": percent_ppa,
                "returning_defense": None,
                "returning_qb": percent_passing_ppa,
                "returning_ol": None,
                "total_ppa": maybe_float(item.get("totalPPA")),
                "total_passing_ppa": maybe_float(item.get("totalPassingPPA")),
                "total_receiving_ppa": maybe_float(item.get("totalReceivingPPA")),
                "total_rushing_ppa": maybe_float(item.get("totalRushingPPA")),
                "percent_ppa": percent_ppa,
                "percent_passing_ppa": percent_passing_ppa,
                "percent_receiving_ppa": maybe_float(item.get("percentReceivingPPA")),
                "percent_rushing_ppa": maybe_float(item.get("percentRushingPPA")),
                "usage_rate": maybe_float(item.get("usage")),
                "passing_usage_rate": maybe_float(item.get("passingUsage")),
                "receiving_usage_rate": maybe_float(item.get("receivingUsage")),
                "rushing_usage_rate": maybe_float(item.get("rushingUsage")),
                "source_name": "cfbd",
            }
        )
    db.upsert_many("returning_production", rows, conflict_columns=["team_id", "season_year", "source_name"])


def _ingest_talent(repository: Repository, db: Database, rows_in: list[dict[str, Any]], season: int) -> None:
    rows: list[dict[str, Any]] = []
    for item in rows_in:
        team_id = repository.match_team_by_name(str(item.get("team")), level_code="FBS")
        if team_id is None:
            continue
        rows.append(
            {
                "team_id": team_id,
                "season_year": season,
                "talent_score": maybe_float(item.get("talent")),
                "talent_rank": maybe_int(item.get("rank")),
                "source_name": "cfbd",
            }
        )
    db.upsert_many("team_talent_snapshots", rows, conflict_columns=["team_id", "season_year", "source_name"])


def _ingest_recruiting(repository: Repository, db: Database, rows_in: list[dict[str, Any]], season: int) -> None:
    rows: list[dict[str, Any]] = []
    for item in rows_in:
        team_id = repository.match_team_by_name(str(item.get("team")), level_code="FBS")
        if team_id is None:
            continue
        rows.append(
            {
                "player_id": None,
                "team_id": team_id,
                "season_year": season,
                "class_key": "team",
                "stars": maybe_int(item.get("stars")),
                "rating": maybe_float(item.get("points")),
                "position": None,
                "source_name": "cfbd",
            }
        )
    db.upsert_many("recruiting_entries", rows, conflict_columns=["team_id", "season_year", "source_name", "class_key"])


def _ingest_player_recruiting(repository: Repository, db: Database, rows_in: list[dict[str, Any]], season: int) -> None:
    recruit_rows: list[dict[str, Any]] = []
    for item in rows_in:
        source_recruit_id = str(item.get("id") or "").strip()
        athlete_id = str(item.get("athleteId") or "").strip()
        if not source_recruit_id and not athlete_id:
            continue
        full_name = str(item.get("name") or "").strip()
        if not full_name:
            full_name = "Unknown Recruit"
        player_id = _match_player_for_recruit(db, athlete_id, source_recruit_id)
        if player_id is None:
            player_id = _get_or_create_player(
                db,
                athlete_id,
                full_name,
                {
                    "firstName": full_name.split(" ", 1)[0] if " " in full_name else full_name,
                    "lastName": full_name.split(" ", 1)[1] if " " in full_name else "",
                    "position": item.get("position"),
                    "homeCity": item.get("city"),
                    "homeState": item.get("stateProvince"),
                },
            )
        if source_recruit_id:
            _upsert_player_source_ids(db, player_id, "cfbd-recruit", [source_recruit_id])
        team_name = str(item.get("committedTo") or item.get("committed_team") or "").strip()
        team_id = repository.match_team_by_name(team_name, level_code="FBS") if team_name else None
        hometown_info = item.get("hometownInfo") if isinstance(item.get("hometownInfo"), dict) else {}
        recruit_rows.append(
            {
                "player_id": player_id,
                "season_year": season,
                "recruit_type": str(item.get("recruitType") or "").strip() or None,
                "source_name": "cfbd",
                "source_recruit_id": source_recruit_id or athlete_id,
                "source_athlete_id": athlete_id or None,
                "team_id": team_id,
                "school_name": str(item.get("school") or "").strip() or None,
                "committed_team": team_name or None,
                "position": str(item.get("position") or "").strip() or None,
                "stars": maybe_int(item.get("stars")),
                "rating": maybe_float(item.get("rating")),
                "national_rank": maybe_int(item.get("ranking")),
                "height_inches": maybe_float(item.get("height")),
                "weight_lbs": maybe_float(item.get("weight")),
                "city": str(item.get("city") or "").strip() or None,
                "state_province": str(item.get("stateProvince") or "").strip() or None,
                "country": str(item.get("country") or "").strip() or None,
                "latitude": maybe_float(hometown_info.get("latitude")),
                "longitude": maybe_float(hometown_info.get("longitude")),
                "county_fips": str(hometown_info.get("fipsCode") or "").strip() or None,
                "notes": json.dumps(
                    {
                        "recruitType": item.get("recruitType"),
                        "school": item.get("school"),
                        "committedTo": item.get("committedTo"),
                    },
                    sort_keys=True,
                ),
            }
        )
    db.upsert_many(
        "player_recruiting_profiles",
        recruit_rows,
        conflict_columns=["source_name", "source_recruit_id"],
        update_columns=[
            "player_id",
            "season_year",
            "recruit_type",
            "source_athlete_id",
            "team_id",
            "school_name",
            "committed_team",
            "position",
            "stars",
            "rating",
            "national_rank",
            "height_inches",
            "weight_lbs",
            "city",
            "state_province",
            "country",
            "latitude",
            "longitude",
            "county_fips",
            "notes",
        ],
    )


def _ingest_roster(repository: Repository, db: Database, roster: list[dict[str, Any]], season: int) -> None:
    roster_rows: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []
    for player in roster:
        team_id = repository.match_team_by_name(str(player.get("team")), level_code="FBS")
        if team_id is None:
            continue
        source_player_id = str(player.get("id") or "").strip()
        full_name = _cfbd_player_full_name(player)
        player_id = _get_or_create_player(db, source_player_id, full_name, player)
        _upsert_player_source_ids(db, player_id, "cfbd-recruit", _cfbd_recruit_ids(player))
        roster_rows.append(
            {
                "player_id": player_id,
                "team_id": team_id,
                "season_year": season,
                "jersey": str(player.get("jersey") or ""),
                "position": str(player.get("position") or ""),
                "class_year": str(player.get("year") or ""),
                "height_inches": maybe_float(player.get("height")),
                "weight_lbs": maybe_float(player.get("weight")),
                "hometown": str(player.get("homeCity") or player.get("hometown") or ""),
                "home_city": str(player.get("homeCity") or ""),
                "home_state": str(player.get("homeState") or ""),
                "home_country": str(player.get("homeCountry") or ""),
                "home_latitude": maybe_float(player.get("homeLatitude")),
                "home_longitude": maybe_float(player.get("homeLongitude")),
                "home_county_fips": str(player.get("homeCountyFIPS") or ""),
                "is_returning_player": None,
            }
        )
        snapshot_rows.append(
            {
                "player_id": player_id,
                "team_id": team_id,
                "season_year": season,
                "source_name": "cfbd",
                "source_player_id": source_player_id or full_name,
                "payload_json": json.dumps(player, sort_keys=True),
            }
        )
    db.upsert_many("roster_entries", roster_rows, conflict_columns=["player_id", "team_id", "season_year"])
    db.upsert_many(
        "roster_source_snapshots",
        snapshot_rows,
        conflict_columns=["team_id", "season_year", "source_name", "source_player_id"],
        update_columns=["player_id", "payload_json"],
    )


def _ingest_transfer_portal(repository: Repository, db: Database, rows_in: list[dict[str, Any]], season: int) -> None:
    db.execute(
        """
        delete from transfer_entries
        where season_year = %(season)s
          and source_name = 'cfbd'
        """,
        {"season": season},
    )

    transfer_rows: list[dict[str, Any]] = []
    for item in rows_in:
        full_name = " ".join(
            part for part in [str(item.get("firstName") or "").strip(), str(item.get("lastName") or "").strip()] if part
        ).strip() or "Unknown Player"
        player_id = _get_or_create_player(db, "", full_name, item)
        from_team_name = str(item.get("origin") or "").strip()
        to_team_name = str(item.get("destination") or "").strip()
        from_team_id = repository.match_team_by_name(from_team_name) if from_team_name else None
        to_team_id = repository.match_team_by_name(to_team_name) if to_team_name else None
        rating = maybe_float(item.get("rating"))
        stars = maybe_int(item.get("stars"))
        transfer_rows.append(
            {
                "player_id": player_id,
                "season_year": season,
                "from_team_id": from_team_id,
                "to_team_id": to_team_id,
                "from_level_code": _team_level_code(db, from_team_id, season),
                "to_level_code": _team_level_code(db, to_team_id, season),
                "position": str(item.get("position") or ""),
                "rating": rating,
                "transfer_points": rating if rating is not None else (float(stars) if stars is not None else 1.0),
                "transfer_stars": stars,
                "transfer_date": str(item.get("transferDate") or "").strip() or None,
                "eligibility": str(item.get("eligibility") or "").strip() or None,
                "from_team_name": from_team_name or None,
                "to_team_name": to_team_name or None,
                "source_name": "cfbd",
                "notes": json.dumps(
                    {
                        "origin": from_team_name or None,
                        "destination": to_team_name or None,
                        "transferDate": item.get("transferDate"),
                        "stars": stars,
                        "eligibility": item.get("eligibility"),
                    },
                    sort_keys=True,
                ),
            }
        )

    db.execute_many(
        """
        insert into transfer_entries (
          player_id,
          season_year,
          from_team_id,
          to_team_id,
          from_level_code,
          to_level_code,
          position,
          rating,
          transfer_points,
          transfer_stars,
          transfer_date,
          eligibility,
          from_team_name,
          to_team_name,
          source_name,
          notes
        )
        values (
          %(player_id)s,
          %(season_year)s,
          %(from_team_id)s,
          %(to_team_id)s,
          %(from_level_code)s,
          %(to_level_code)s,
          %(position)s,
          %(rating)s,
          %(transfer_points)s,
          %(transfer_stars)s,
          %(transfer_date)s,
          %(eligibility)s,
          %(from_team_name)s,
          %(to_team_name)s,
          %(source_name)s,
          %(notes)s
        )
        """,
        transfer_rows,
    )


def _get_or_create_player(db: Database, source_player_id: str, full_name: str, player: dict[str, Any]) -> int:
    if source_player_id:
        existing = db.query_one(
            """
            select player_id
            from player_source_ids
            where source_name = 'cfbd' and source_player_id = %(source_player_id)s
            """,
            {"source_player_id": source_player_id},
        )
        if existing:
            return int(existing["player_id"])

    player_id: int | None = None
    if not source_player_id:
        matches = db.query_all(
            """
            select player_id, position, hometown, home_state
            from players
            where lower(full_name) = lower(%(full_name)s)
            """,
            {"full_name": full_name},
        )
        compatible_matches = [row for row in matches if _player_row_is_compatible(row, player)]
        if len(compatible_matches) == 1:
            player_id = int(compatible_matches[0]["player_id"])

    if player_id is None:
        row = db.query_one(
            """
            insert into players (full_name, first_name, last_name, position, hometown, home_state)
            values (%(full_name)s, %(first_name)s, %(last_name)s, %(position)s, %(hometown)s, %(home_state)s)
            returning player_id
            """,
            {
                "full_name": full_name,
                "first_name": str(player.get("firstName") or "").strip() or (full_name.split(" ")[0] if " " in full_name else full_name),
                "last_name": str(player.get("lastName") or "").strip() or (full_name.split(" ", 1)[1] if " " in full_name else ""),
                "position": str(player.get("position") or ""),
                "hometown": str(player.get("homeCity") or player.get("hometown") or ""),
                "home_state": str(player.get("homeState") or ""),
            },
        )
        if row is None:
            raise RuntimeError("Failed to create player")
        player_id = int(row["player_id"])

    if source_player_id:
        _upsert_player_source_ids(db, player_id, "cfbd", [source_player_id])
    return player_id


def _resolve_or_create_game_stat_player(
    db: Database,
    team_id: int,
    season: int,
    source_player_id: str,
    player_name: str,
    category_name: str,
    team_name: str,
) -> int:
    if source_player_id:
        existing = db.query_one(
            """
            select player_id
            from player_source_ids
            where source_name = 'cfbd'
              and source_player_id = %(source_player_id)s
            """,
            {"source_player_id": source_player_id},
        )
        if existing is not None:
            return int(existing["player_id"])

    roster_match = db.query_one(
        """
        select p.player_id
        from roster_entries re
        join players p on p.player_id = re.player_id
        where re.team_id = %(team_id)s
          and re.season_year = %(season_year)s
          and lower(p.full_name) = lower(%(player_name)s)
        order by re.roster_entry_id desc
        limit 1
        """,
        {"team_id": team_id, "season_year": season, "player_name": player_name},
    )
    if roster_match is not None:
        player_id = int(roster_match["player_id"])
        if source_player_id:
            _upsert_player_source_ids(db, player_id, "cfbd", [source_player_id])
        return player_id

    category_position_map = {
        "passing": "QB",
        "rushing": "RB",
        "receiving": "WR",
        "interceptions": "DB",
        "kicking": "K",
        "punting": "P",
        "puntReturns": "WR",
        "kickReturns": "WR",
        "fumbles": "",
    }
    return _get_or_create_player(
        db,
        source_player_id,
        player_name,
        {
            "name": player_name,
            "position": category_position_map.get(category_name, ""),
            "team": team_name,
        },
    )


def _cfbd_player_full_name(player: dict[str, Any]) -> str:
    first_name = str(player.get("firstName") or "").strip()
    last_name = str(player.get("lastName") or "").strip()
    full_name = " ".join(part for part in [first_name, last_name] if part).strip()
    if full_name:
        return full_name
    return str(player.get("name") or "Unknown Player")


def _cfbd_recruit_ids(player: dict[str, Any]) -> list[str]:
    raw_ids = player.get("recruitIds") or []
    if not isinstance(raw_ids, list):
        return []
    recruit_ids: list[str] = []
    for value in raw_ids:
        recruit_id = str(value or "").strip()
        if recruit_id:
            recruit_ids.append(recruit_id)
    return recruit_ids


def _upsert_player_source_ids(db: Database, player_id: int, source_name: str, source_ids: list[str]) -> None:
    rows = [
        {
            "player_id": player_id,
            "source_name": source_name,
            "source_player_id": source_id,
        }
        for source_id in dict.fromkeys(source_ids)
        if source_id
    ]
    db.upsert_many(
        "player_source_ids",
        rows,
        conflict_columns=["source_name", "source_player_id"],
        update_columns=["player_id"],
    )


def _team_level_code(db: Database, team_id: int | None, season: int) -> str | None:
    if team_id is None:
        return None
    row = db.query_one(
        """
        select coalesce(ts.level_code, t.level_code) as level_code
        from teams t
        left join team_seasons ts
          on ts.team_id = t.team_id
         and ts.season_year = %(season)s
        where t.team_id = %(team_id)s
        """,
        {"season": season, "team_id": team_id},
    )
    return None if row is None or row.get("level_code") is None else str(row["level_code"])


def _match_player_for_recruit(db: Database, athlete_id: str, recruit_id: str) -> int | None:
    candidate_sources = []
    if athlete_id:
        candidate_sources.extend(
            [
                ("cfbd", athlete_id),
                ("cfbd-recruit", athlete_id),
            ]
        )
    if recruit_id:
        candidate_sources.append(("cfbd-recruit", recruit_id))
    for source_name, source_player_id in candidate_sources:
        row = db.query_one(
            """
            select player_id
            from player_source_ids
            where source_name = %(source_name)s
              and source_player_id = %(source_player_id)s
            """,
            {"source_name": source_name, "source_player_id": source_player_id},
        )
        if row is not None:
            return int(row["player_id"])
    return None


def _player_row_is_compatible(row: dict[str, Any], player: dict[str, Any]) -> bool:
    comparisons = [
        (str(row.get("position") or "").strip().lower(), str(player.get("position") or "").strip().lower()),
        (str(row.get("hometown") or "").strip().lower(), str(player.get("homeCity") or player.get("hometown") or "").strip().lower()),
        (str(row.get("home_state") or "").strip().lower(), str(player.get("homeState") or "").strip().lower()),
    ]
    for existing_value, incoming_value in comparisons:
        if existing_value and incoming_value and existing_value != incoming_value:
            return False
    return True


def _find_game_id(repository: Repository, payload: dict[str, Any]) -> int | None:
    source_game_id = payload.get("gameId") or payload.get("id")
    if source_game_id is None:
        return None
    row = repository.db.query_one(
        """
        select game_id
        from game_source_ids
        where source_name = 'cfbd' and source_game_id = %(source_game_id)s
        """,
        {"source_game_id": str(source_game_id)},
    )
    return int(row["game_id"]) if row else None


def _safe_fetch(fetcher: Any, label: str) -> list[dict[str, Any]]:
    try:
        result = fetcher()
        return result if isinstance(result, list) else []
    except Exception as exc:
        print(f"Skipping CFBD {label}: {exc}")
        return []


def _maybe_stat_number(value: str | None) -> float | None:
    text = str(value or "").strip()
    if not text or "/" in text or text in {"--", "-", "N/A"}:
        return None
    try:
        return maybe_float(text)
    except (TypeError, ValueError):
        return None


def _has_local_games_for_week(db: Database, season: int, week: int, season_type: str) -> bool:
    row = db.query_one(
        """
        select count(*) as game_count
        from games
        where season_year = %(season)s
          and (week = %(week)s or coalesce(source_week, -1) = %(week)s)
          and season_type = %(season_type)s
        """,
        {"season": season, "week": week, "season_type": season_type},
    )
    return bool(row and int(row.get("game_count") or 0) > 0)


def _drive_points_scored(drive: dict[str, Any]) -> int:
    start_score = maybe_int(drive.get("startOffenseScore")) or 0
    end_score = maybe_int(drive.get("endOffenseScore")) or 0
    return max(0, end_score - start_score)


def _play_success_flag(play: dict[str, Any]) -> bool | None:
    play_type = str(play.get("playType") or "").lower()
    if any(
        keyword in play_type
        for keyword in (
            "kickoff",
            "punt",
            "field goal",
            "extra point",
            "pat",
            "timeout",
            "end period",
            "end of game",
        )
    ):
        return None

    down = maybe_int(play.get("down"))
    distance = maybe_int(play.get("distance"))
    yards_gained = maybe_int(play.get("yardsGained"))
    if down is None or distance is None or yards_gained is None:
        ppa = maybe_float(play.get("ppa"))
        return None if ppa is None else ppa > 0.0

    if down == 1:
        threshold = 0.5 * distance
    elif down == 2:
        threshold = 0.7 * distance
    else:
        threshold = float(distance)
    return float(yards_gained) >= threshold


def _mean_float(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))
