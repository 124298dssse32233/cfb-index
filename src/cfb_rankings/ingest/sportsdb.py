from __future__ import annotations

from cfb_rankings.clients.sportsdb import SportsDbClient
from cfb_rankings.ingest.common import maybe_int, parse_datetime
from cfb_rankings.storage import Repository, TeamIdentity


def ingest_sportsdb_league(
    repository: Repository,
    client: SportsDbClient,
    league_id: int,
    season: int,
    level_code: str,
    conference_name: str,
) -> None:
    repository.ensure_season(season)

    teams = client.list_league_teams(league_id)
    for team in teams:
        team_id = str(team.get("idTeam") or team.get("id"))
        if not team_id:
            continue
        repository.get_or_create_team(
            "sportsdb",
            team_id,
            TeamIdentity(
                canonical_name=str(team.get("strTeam") or team.get("strTeamShort") or "Unknown Team"),
                school_name=str(team.get("strTeam") or "Unknown Team"),
                short_name=str(team.get("strTeamShort") or team.get("strTeam") or "Unknown Team"),
                level_code=level_code,
                conference_name=conference_name,
                city=str(team.get("strCity") or "") or None,
                state=str(team.get("strStadiumLocation") or "") or None,
                country=str(team.get("strCountry") or "USA"),
            ),
        )

    events = client.list_season_events(league_id, str(season))
    for event in events:
        home_id = repository.find_team_id("sportsdb", str(event.get("idHomeTeam") or ""))
        away_id = repository.find_team_id("sportsdb", str(event.get("idAwayTeam") or ""))
        if home_id is None or away_id is None:
            continue

        payload = {
            "season_year": season,
            "season_type": "regular",
            "week": maybe_int(event.get("intRound")) or 0,
            "start_time_utc": parse_datetime(str(event.get("strTimestamp") or event.get("dateEvent"))),
            "status": str(event.get("strStatus") or ("Final" if event.get("intHomeScore") else "Scheduled")),
            "neutral_site": bool(event.get("strVenue") and event.get("strHomeTeam") != event.get("strVenue")),
            "venue_id": None,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_points": maybe_int(event.get("intHomeScore")),
            "away_points": maybe_int(event.get("intAwayScore")),
            "attendance": maybe_int(event.get("intSpectators")),
            "notes": str(event.get("strSeason") or ""),
        }
        repository.get_or_create_game("sportsdb", str(event.get("idEvent")), payload)
