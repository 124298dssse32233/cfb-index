"""Sparkline SVG generation for rankings page.

This module provides inline SVG sparklines showing rank trajectory over recent weeks,
adding historical context and visual interest to the rankings page.
"""

from typing import Optional
from cfb_rankings.db import Database


def render_rank_trajectory_sparkline(
    team_id: int,
    db: Database,
    width: int = 80,
    height: int = 24,
    weeks: int = 5
) -> str:
    """Generate SVG sparkline showing rank trajectory over recent weeks.

    Args:
        team_id: Team database ID
        db: Database connection
        width: SVG width in pixels
        height: SVG height in pixels
        weeks: Number of weeks to include

    Returns:
        Inline SVG string with polyline showing rank trend, or empty string if insufficient data
    """
    # Fetch historical ranks from team_week_summary
    rows = db.query_all("""
        SELECT week, rank
        FROM team_week_summary
        WHERE team_id = ?
          AND season_year = 2025
        ORDER BY week DESC
        LIMIT ?
    """, (team_id, weeks))

    if len(rows) < 2:
        return ""  # Not enough data for sparkline

    # Reverse to get chronological order (oldest → newest)
    data = list(reversed(rows))

    # Extract ranks
    ranks = [r["rank"] for r in data]

    # Normalize to fit SVG coordinate space
    min_rank = min(ranks)
    max_rank = max(ranks)
    rank_range = max(max_rank - min_rank, 1)  # Avoid division by zero

    points = []
    for i, rank in enumerate(ranks):
        x = (i / (len(ranks) - 1)) * width
        # Invert y-axis (lower rank = higher visually)
        y = height - ((rank - min_rank) / rank_range) * height
        points.append(f"{x:.1f},{y:.1f}")

    # Determine color based on trend
    first_rank = ranks[0]
    last_rank = ranks[-1]
    if last_rank < first_rank:
        stroke_color = "var(--green)"  # Rising (improving)
    elif last_rank > first_rank:
        stroke_color = "var(--red)"  # Falling (worsening)
    else:
        stroke_color = "var(--fg-muted)"  # Flat

    # Extract final point for circle
    final_x, final_y = points[-1].split(',')

    return f"""
<svg class="rank-sparkline" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <polyline
        points="{' '.join(points)}"
        fill="none"
        stroke="{stroke_color}"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
    />
    <circle
        cx="{final_x}"
        cy="{final_y}"
        r="3"
        fill="{stroke_color}"
    />
</svg>
""".strip()
