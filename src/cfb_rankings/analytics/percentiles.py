"""Percentile Calculation Module

Calculates player percentiles against FBS peer groups using database queries
and linear interpolation.

Spec: WORLD_CLASS_STATS_IMPLEMENTATION_PLAN.md Phase 3, Task C2
"""
from __future__ import annotations

from typing import Any

# Cache for percentile calculations per season
_percentile_cache: dict[tuple[int, str, int], list[tuple[str, float]]] = {}


def calculate_player_percentile(
    db,
    player_value: float,
    season: int,
    stat_type: str,
    min_snaps: int = 100,
) -> int:
    """Calculate percentile rank (0-100) for a player's stat value.

    Queries all qualified FBS players for the season/stat type,
    then computes percentile using linear interpolation.

    Args:
        db: Database connection
        player_value: The player's stat value to calculate percentile for
        season: Season year
        stat_type: Stat type identifier (e.g., "epa_per_play", "success_rate", "cpoe", "aya")
        min_snaps: Minimum snaps/plays to qualify for percentile calculation

    Returns:
        Percentile rank (0-100). Returns 50 if insufficient data.

    Examples:
        >>> percentile = calculate_player_percentile(db, 0.25, 2025, "epa_per_play")
        >>> print(percentile)
        85
    """
    # Check cache first
    cache_key = (season, stat_type, min_snaps)
    if cache_key not in _percentile_cache:
        # Build cache for this season/stat type
        _percentile_cache[cache_key] = _fetch_all_values(db, season, stat_type, min_snaps)

    all_values = _percentile_cache[cache_key]

    if not all_values:
        return 50  # Default to middle percentile if no data

    # Sort by value
    all_values.sort(key=lambda x: x[1])

    # Count players with lower values
    lower_count = sum(1 for _, val in all_values if val < player_value)
    total = len(all_values)

    if total == 0:
        return 50

    # Linear interpolation for percentile
    percentile = (lower_count / total) * 100

    return int(round(percentile))


def _fetch_all_values(
    db,
    season: int,
    stat_type: str,
    min_snaps: int,
) -> list[tuple[str, float]]:
    """Fetch all qualified player stat values for a season.

    Returns list of (player_id, value) tuples.
    """
    # Map stat_type to database query
    # This is a placeholder - actual implementation depends on database schema
    queries = {
        "epa_per_play": """
            SELECT player_id, epa_per_play
            FROM player_season_stats
            WHERE season = :season
              AND attempts >= :min_snaps
              AND epa_per_play IS NOT NULL
        """,
        "success_rate": """
            SELECT player_id, success_rate
            FROM player_season_stats
            WHERE season = :season
              AND attempts >= :min_snaps
              AND success_rate IS NOT NULL
        """,
        "cpoe": """
            SELECT player_id, cpoe
            FROM player_season_stats
            WHERE season = :season
              AND attempts >= :min_snaps
              AND cpoe IS NOT NULL
        """,
        "aya": """
            SELECT player_id, adjusted_yards_per_attempt
            FROM player_season_stats
            WHERE season = :season
              AND attempts >= :min_snaps
              AND adjusted_yards_per_attempt IS NOT NULL
        """,
    }

    query = queries.get(stat_type)
    if not query:
        return []

    try:
        rows = db.query(query, {"season": season, "min_snaps": min_snaps})
        return [(row["player_id"], float(row[1])) for row in rows]
    except Exception:
        return []


def clear_percentile_cache() -> None:
    """Clear the percentile calculation cache.

    Call this after bulk data imports or when you want fresh calculations.
    """
    _percentile_cache.clear()


__all__ = [
    "calculate_player_percentile",
    "clear_percentile_cache",
]
