"""Player Stats Integration Helpers

Bridges the existing reporting.py data structures with the new world-class
stats table components. Converts legacy season_stat_tables format to
StatRow objects for the StatsTableRenderer.

This approach avoids expanding the already-large reporting.py (27k lines)
and keeps stats logic modular and testable (per Gemini review recommendation).
"""

from __future__ import annotations

from typing import Any
from .stats_table import (
    ColumnDef,
    ColumnAlign,
    StatRow,
    TableConfig,
    StatsTableRenderer,
)


# =============================================================================
# DATA CONVERSION HELPERS
# =============================================================================

def convert_season_stat_section(
    section: dict[str, Any],
    player_name: str,
    player_slug: str | None = None,
) -> tuple[list[StatRow], list[ColumnDef]]:
    """Convert a legacy season_stat_tables section to new format.

    Args:
        section: Legacy dict with 'columns', 'rows', 'title', etc.
        player_name: Player name for the identity column
        player_slug: Player slug for link generation

    Returns:
        Tuple of (list of StatRow, list of ColumnDef)
    """
    # Extract column definitions
    legacy_columns = section.get("columns") or []
    stat_columns = [
        ColumnDef(
            id=_slugify(str(label)),
            header=str(label).upper(),
            align=ColumnAlign.RIGHT,
            sortable=True,
        )
        for label in legacy_columns
    ]

    # Add identity columns at the front
    season_col = ColumnDef("season", "Season", ColumnAlign.LEFT, sortable=False)
    team_col = ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False)
    all_columns = [season_col, team_col] + stat_columns

    # Convert rows
    stat_rows = []
    for row in section.get("rows") or []:
        stat_row = StatRow(
            name=str(row.get("season_label") or "--"),
            link_url=_player_season_link(player_slug, row) if player_slug else None,
            link_type="player",
            team=str(row.get("team_name") or ""),
            team_slug=row.get("team_slug"),
            values={
                "season": str(row.get("season_label") or "--"),
                "team": str(row.get("team_name") or "--"),
            },
        )

        # Add stat values from cells
        for cell in row.get("cells") or []:
            cell_label = str(cell.get("label") or "")
            cell_value = cell.get("value")
            stat_row.values[_slugify(cell_label)] = cell_value

        stat_rows.append(stat_row)

    return stat_rows, all_columns


def _slugify(text: str) -> str:
    """Convert column label to CSS-safe ID."""
    return text.lower().replace("/", "_").replace(" ", "-").replace("%", "pct")


def _player_season_link(player_slug: str | None, row: dict[str, Any]) -> str | None:
    """Generate link to player season detail."""
    if not player_slug:
        return None
    # For now, link to the player page itself
    # Future: link to specific season anchor
    return f"../players/{player_slug}.html"


# =============================================================================
# FACTORY FUNCTIONS FOR PLAYER PAGES
# =============================================================================

def render_player_passing_section(
    section: dict[str, Any],
    player_name: str,
    player_slug: str | None = None,
    table_id: str = "player-passing-stats",
) -> str:
    """Render a passing stats section in world-class format.

    Converts legacy season_stat_tables section to new format and renders
    with canonical column sequence and mobile-first responsive behavior.
    """
    rows, columns = convert_season_stat_section(section, player_name, player_slug)

    # Use canonical passing columns if available, otherwise use converted columns
    from .stats_table import PASSING_COLUMNS

    # Try to map legacy columns to canonical ones
    # For now, use the converted columns to preserve existing data
    config = TableConfig(
        table_id=table_id,
        columns=columns,
        default_sort="yds" if any(c.id == "yds" for c in columns) else columns[2].id,
        default_sort_dir="desc",
    )

    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_player_rushing_section(
    section: dict[str, Any],
    player_name: str,
    player_slug: str | None = None,
    table_id: str = "player-rushing-stats",
) -> str:
    """Render a rushing stats section in world-class format."""
    rows, columns = convert_season_stat_section(section, player_name, player_slug)

    config = TableConfig(
        table_id=table_id,
        columns=columns,
        default_sort="yds" if any(c.id == "yds" for c in columns) else columns[2].id,
        default_sort_dir="desc",
    )

    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_player_receiving_section(
    section: dict[str, Any],
    player_name: str,
    player_slug: str | None = None,
    table_id: str = "player-receiving-stats",
) -> str:
    """Render a receiving stats section in world-class format."""
    rows, columns = convert_season_stat_section(section, player_name, player_slug)

    config = TableConfig(
        table_id=table_id,
        columns=columns,
        default_sort="yds" if any(c.id == "yds" for c in columns) else columns[2].id,
        default_sort_dir="desc",
    )

    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_all_player_season_stat_tables(
    season_stat_tables: list[dict[str, Any]],
    player_name: str,
    player_slug: str | None = None,
    use_legacy: bool = True,
) -> str:
    """Render all player season stat tables.

    Args:
        season_stat_tables: List of legacy stat table sections
        player_name: Player name
        player_slug: Player slug for links
        use_legacy: If True, use legacy renderer; if False, use new world-class renderer

    Returns:
        HTML string for all tables
    """
    if not season_stat_tables:
        return '<p class="footer-note">Season-by-season stat tables will appear here as soon as older player stat seasons are loaded into the local database.</p>'

    if use_legacy:
        # Fall back to existing rendering (preserves current behavior)
        from cfb_rankings.reporting import _render_player_season_stat_table
        return "".join(_render_player_season_stat_table(section) for section in season_stat_tables)

    # Use new world-class renderer
    tables_html = []
    for i, section in enumerate(season_stat_tables):
        title = str(section.get("title") or "").lower()
        table_id = f"player-stats-{i}"

        if "passing" in title:
            tables_html.append(render_player_passing_section(section, player_name, player_slug, table_id))
        elif "rushing" in title:
            tables_html.append(render_player_rushing_section(section, player_name, player_slug, table_id))
        elif "receiving" in title:
            tables_html.append(render_player_receiving_section(section, player_name, player_slug, table_id))
        else:
            # Generic rendering for other stat types
            rows, columns = convert_season_stat_section(section, player_name, player_slug)
            config = TableConfig(table_id=table_id, columns=columns)
            renderer = StatsTableRenderer(config, rows)
            tables_html.append(renderer.render())

    return "\n".join(tables_html)


__all__ = [
    "convert_season_stat_section",
    "render_player_passing_section",
    "render_player_rushing_section",
    "render_player_receiving_section",
    "render_all_player_season_stat_tables",
]
