"""CFBD Tier 2 Advanced Stats Client

Fetches advanced metrics (EPA, Success Rate, CPOE, AY/A) for players and teams
from CollegeFootballData.com tier 2 endpoints.

Caching: 24-hour cache to avoid rate limits.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cfb_rankings.config import cfbd_api_key, cfbd_base_url
import requests


# Cache configuration
_CACHE_DIR = Path.home() / ".cfbd-cache"
_CACHE_TTL = timedelta(hours=24)


def _cache_path(cache_key: str) -> Path:
    """Get the cache file path for a given key."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{cache_key}.json"


def _get_cached(cache_key: str) -> dict[str, Any] | None:
    """Get cached response if available and not expired."""
    cache_file = _cache_path(cache_key)
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data.get("cached_at", ""))
        if datetime.now() - cached_at < _CACHE_TTL:
            return data.get("response")
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    return None


def _set_cached(cache_key: str, response: dict[str, Any] | list[dict[str, Any]]) -> None:
    """Cache a response with timestamp."""
    cache_file = _cache_path(cache_key)
    data = {
        "cached_at": datetime.now().isoformat(),
        "response": response,
    }
    cache_file.write_text(json.dumps(data), encoding="utf-8")


def fetch_player_advanced_stats(
    player_id: str | int,
    season: int,
    *,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Fetch advanced stats for a player from CFBD tier 2.

    Args:
        player_id: CFBD player ID
        season: Season year
        use_cache: If True, use cached responses when available

    Returns:
        Dict with advanced stats including EPA, success rate, CPOE, AY/A.
        Returns empty dict if player not found or on error.
    """
    cache_key = f"player_advanced_{player_id}_{season}"

    if use_cache:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

    try:
        url = f"{cfbd_base_url}/player/advanced"
        params = {"year": season, "player": player_id}
        headers = {}
        if cfbd_api_key:
            headers["Authorization"] = f"Bearer {cfbd_api_key}"

        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Cache successful response
        _set_cached(cache_key, data)
        return data

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            # Player not found - log warning and return empty dict
            import logging
            logging.getLogger(__name__).warning(
                f"CFBD 404: player {player_id} season {season} not found"
            )
            return {}
        raise
    except (requests.RequestException, json.JSONDecodeError) as e:
        import logging
        logging.getLogger(__name__).error(
            f"CFBD fetch error for player {player_id}: {e}"
        )
        return {}


def fetch_team_advanced_stats(
    team: str,
    season: int,
    *,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Fetch advanced stats for a team from CFBD tier 2.

    Args:
        team: Team slug (e.g., "georgia", "ohio-state")
        season: Season year
        use_cache: If True, use cached responses when available

    Returns:
        List of dicts with team advanced stats. Empty list if error.
    """
    cache_key = f"team_advanced_{team}_{season}"

    if use_cache:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

    try:
        url = f"{cfbd_base_url}/team/advanced"
        params = {"year": season, "team": team}
        headers = {}
        if cfbd_api_key:
            headers["Authorization"] = f"Bearer {cfbd_api_key}"

        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Cache successful response
        _set_cached(cache_key, data)
        return data if isinstance(data, list) else []

    except (requests.RequestException, json.JSONDecodeError) as e:
        import logging
        logging.getLogger(__name__).error(
            f"CFBD fetch error for team {team}: {e}"
        )
        return []


__all__ = [
    "fetch_player_advanced_stats",
    "fetch_team_advanced_stats",
]
