from __future__ import annotations

from typing import Any

from cfb_rankings.clients.base import JsonApiClient


class CfbdClient(JsonApiClient):
    def __init__(self, api_key: str, base_url: str, timeout_seconds: float = 30.0) -> None:
        super().__init__(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout_seconds=timeout_seconds,
        )

    def get_games(
        self,
        year: int,
        week: int | None = None,
        season_type: str = "regular",
        division: str | None = None,
        team: str | None = None,
        home: str | None = None,
        away: str | None = None,
        conference: str | None = None,
        game_id: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "seasonType": season_type}
        if week is not None:
            params["week"] = week
        if division:
            params["classification"] = division
        if team:
            params["team"] = team
        if home:
            params["home"] = home
        if away:
            params["away"] = away
        if conference:
            params["conference"] = conference
        if game_id is not None:
            params["id"] = game_id
        return self.get_json("/games", params=params)

    def get_lines(
        self,
        year: int | None = None,
        week: int | None = None,
        season_type: str = "regular",
        game_id: int | None = None,
        team: str | None = None,
        home: str | None = None,
        away: str | None = None,
        conference: str | None = None,
        provider: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "seasonType": season_type}
        if game_id is not None:
            params["gameId"] = game_id
        if week is not None:
            params["week"] = week
        if team:
            params["team"] = team
        if home:
            params["home"] = home
        if away:
            params["away"] = away
        if conference:
            params["conference"] = conference
        if provider:
            params["provider"] = provider
        return self.get_json("/lines", params=params)

    def get_weather(
        self,
        year: int,
        week: int | None = None,
        season_type: str = "regular",
        team: str | None = None,
        conference: str | None = None,
        classification: str | None = None,
        game_id: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "seasonType": season_type}
        if week is not None:
            params["week"] = week
        if team:
            params["team"] = team
        if conference:
            params["conference"] = conference
        if classification:
            params["classification"] = classification
        if game_id is not None:
            params["gameId"] = game_id
        return self.get_json("/games/weather", params=params)

    def get_advanced_game_stats(
        self,
        year: int,
        week: int | None = None,
        season_type: str = "regular",
        team: str | None = None,
        opponent: str | None = None,
        exclude_garbage_time: bool | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "seasonType": season_type}
        if week is not None:
            params["week"] = week
        if team:
            params["team"] = team
        if opponent:
            params["opponent"] = opponent
        if exclude_garbage_time is not None:
            params["excludeGarbageTime"] = exclude_garbage_time
        return self.get_json("/stats/game/advanced", params=params)

    def get_advanced_season_stats(
        self,
        year: int,
        team: str | None = None,
        exclude_garbage_time: bool | None = None,
        start_week: int | None = None,
        end_week: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year}
        if team:
            params["team"] = team
        if exclude_garbage_time is not None:
            params["excludeGarbageTime"] = exclude_garbage_time
        if start_week is not None:
            params["startWeek"] = start_week
        if end_week is not None:
            params["endWeek"] = end_week
        return self.get_json("/stats/season/advanced", params=params)

    def get_advanced_box_score(self, game_id: int) -> dict[str, Any]:
        return self.get_json("/game/box/advanced", params={"id": game_id})

    def get_drives(
        self,
        year: int,
        week: int,
        season_type: str = "regular",
        team: str | None = None,
        offense: str | None = None,
        defense: str | None = None,
        conference: str | None = None,
        offense_conference: str | None = None,
        defense_conference: str | None = None,
        classification: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "week": week, "seasonType": season_type}
        if team:
            params["team"] = team
        if offense:
            params["offense"] = offense
        if defense:
            params["defense"] = defense
        if conference:
            params["conference"] = conference
        if offense_conference:
            params["offenseConference"] = offense_conference
        if defense_conference:
            params["defenseConference"] = defense_conference
        if classification:
            params["classification"] = classification
        return self.get_json("/drives", params=params)

    def get_plays(
        self,
        year: int,
        week: int,
        season_type: str = "regular",
        team: str | None = None,
        offense: str | None = None,
        defense: str | None = None,
        offense_conference: str | None = None,
        defense_conference: str | None = None,
        conference: str | None = None,
        play_type: str | None = None,
        classification: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "week": week, "seasonType": season_type}
        if team:
            params["team"] = team
        if offense:
            params["offense"] = offense
        if defense:
            params["defense"] = defense
        if offense_conference:
            params["offenseConference"] = offense_conference
        if defense_conference:
            params["defenseConference"] = defense_conference
        if conference:
            params["conference"] = conference
        if play_type:
            params["playType"] = play_type
        if classification:
            params["classification"] = classification
        return self.get_json("/plays", params=params)

    def get_roster(
        self,
        year: int | None = None,
        team: str | None = None,
        classification: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if team:
            params["team"] = team
        if year is not None:
            params["year"] = year
        if classification:
            params["classification"] = classification
        return self.get_json("/roster", params=params)

    def get_returning_production(
        self,
        year: int | None = None,
        team: str | None = None,
        conference: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if year is not None:
            params["year"] = year
        if team:
            params["team"] = team
        if conference:
            params["conference"] = conference
        return self.get_json("/player/returning", params=params)

    def get_talent(self, year: int) -> list[dict[str, Any]]:
        return self.get_json("/talent", params={"year": year})

    def get_recruiting_teams(self, year: int, team: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year}
        if team:
            params["team"] = team
        return self.get_json("/recruiting/teams", params=params)

    def get_player_usage(
        self,
        year: int,
        conference: str | None = None,
        position: str | None = None,
        team: str | None = None,
        player_id: str | None = None,
        exclude_garbage_time: bool = False,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "excludeGarbageTime": exclude_garbage_time}
        if conference:
            params["conference"] = conference
        if position:
            params["position"] = position
        if team:
            params["team"] = team
        if player_id:
            params["playerId"] = player_id
        return self.get_json("/player/usage", params=params)

    def get_player_season_stats(
        self,
        year: int,
        conference: str | None = None,
        team: str | None = None,
        start_week: int | None = None,
        end_week: int | None = None,
        season_type: str = "regular",
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "seasonType": season_type}
        if conference:
            params["conference"] = conference
        if team:
            params["team"] = team
        if start_week is not None:
            params["startWeek"] = start_week
        if end_week is not None:
            params["endWeek"] = end_week
        if category:
            params["category"] = category
        return self.get_json("/stats/player/season", params=params)

    def get_rankings(
        self,
        year: int,
        week: int | None = None,
        season_type: str = "regular",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "seasonType": season_type}
        if week is not None:
            params["week"] = week
        return self.get_json("/rankings", params=params)

    def get_game_player_stats(
        self,
        year: int,
        week: int | None = None,
        season_type: str = "regular",
        team: str | None = None,
        conference: str | None = None,
        classification: str | None = None,
        category: str | None = None,
        game_id: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"year": year, "seasonType": season_type}
        if week is not None:
            params["week"] = week
        if team:
            params["team"] = team
        if conference:
            params["conference"] = conference
        if classification:
            params["classification"] = classification
        if category:
            params["category"] = category
        if game_id is not None:
            params["id"] = game_id
        return self.get_json("/games/players", params=params)

    def get_player_passing_wepa(
        self,
        year: int | None = None,
        team: str | None = None,
        conference: str | None = None,
        position: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if year is not None:
            params["year"] = year
        if team:
            params["team"] = team
        if conference:
            params["conference"] = conference
        if position:
            params["position"] = position
        return self.get_json("/wepa/players/passing", params=params)

    def get_player_rushing_wepa(
        self,
        year: int | None = None,
        team: str | None = None,
        conference: str | None = None,
        position: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if year is not None:
            params["year"] = year
        if team:
            params["team"] = team
        if conference:
            params["conference"] = conference
        if position:
            params["position"] = position
        return self.get_json("/wepa/players/rushing", params=params)

    def get_recruits(
        self,
        year: int | None = None,
        team: str | None = None,
        position: str | None = None,
        state: str | None = None,
        classification: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if year is not None:
            params["year"] = year
        if team:
            params["team"] = team
        if position:
            params["position"] = position
        if state:
            params["state"] = state
        if classification:
            params["classification"] = classification
        return self.get_json("/recruiting/players", params=params)

    def get_transfer_portal(self, year: int) -> list[dict[str, Any]]:
        return self.get_json("/player/portal", params={"year": year})

    def get_nfl_draft_picks(self, year: int) -> list[dict[str, Any]]:
        """Fetch NFL Draft picks for a draft year. CFBD /draft/picks
        returns college-to-NFL pick rows with collegeId / collegeTeam /
        name / position / round / pick / overall / nflTeam."""
        return self.get_json("/draft/picks", params={"year": year})

    def get_teams(
        self,
        year: int | None = None,
        conference: str | None = None,
        classification: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if year is not None:
            params["year"] = year
        if conference:
            params["conference"] = conference
        if classification:
            params["classification"] = classification
        return self.get_json("/teams", params=params)
