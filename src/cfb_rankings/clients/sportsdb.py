from __future__ import annotations

from typing import Any

from cfb_rankings.clients.base import JsonApiClient


class SportsDbClient:
    def __init__(self, api_key: str, base_url: str, timeout_seconds: float = 30.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.v1_client = JsonApiClient(
            base_url=f"{self.base_url}/api/v1/json/{api_key}",
            timeout_seconds=timeout_seconds,
        )
        self.v2_client = JsonApiClient(
            base_url=f"{self.base_url}/api/v2/json/{api_key}",
            timeout_seconds=timeout_seconds,
        )

    def lookup_team(self, team_id: int) -> list[dict[str, Any]]:
        payload = self.v1_client.get_json("/lookupteam.php", {"id": team_id})
        return payload.get("teams", []) or []

    def lookup_venue(self, venue_id: int) -> list[dict[str, Any]]:
        payload = self.v1_client.get_json("/lookupvenue.php", {"id": venue_id})
        return payload.get("venues", []) or []

    def search_all_leagues(self, country: str = "United States", sport: str = "American Football") -> list[dict[str, Any]]:
        payload = self.v1_client.get_json("/search_all_leagues.php", {"c": country, "s": sport})
        return payload.get("countries", []) or []

    def list_league_teams(self, league_id: int) -> list[dict[str, Any]]:
        try:
            payload = self.v2_client.get_json(f"/list/teams/{league_id}")
            return payload.get("teams", []) or []
        except Exception:
            payload = self.v1_client.get_json("/lookup_all_teams.php", {"id": league_id})
            return payload.get("teams", []) or []

    def list_league_seasons(self, league_id: int) -> list[dict[str, Any]]:
        try:
            payload = self.v2_client.get_json(f"/list/seasons/{league_id}")
            return payload.get("seasons", []) or []
        except Exception:
            payload = self.v1_client.get_json("/search_all_seasons.php", {"id": league_id})
            return payload.get("seasons", []) or []

    def list_season_events(self, league_id: int, season: str) -> list[dict[str, Any]]:
        payload = self.v1_client.get_json("/eventsseason.php", {"id": league_id, "s": season})
        return payload.get("events", []) or []
