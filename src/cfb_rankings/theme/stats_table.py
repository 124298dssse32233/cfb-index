"""Stats Table Renderer (World-Class CFB Stats Display)

Generates semantic HTML stat tables with canonical column sequences,
mobile-first responsive behavior, and proper accessibility attributes.

Spec: docs/research/cfb-stats-conformance-spec.md
Anti-patterns: docs/research/cfb-stats-antipatterns.md
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


# =============================================================================
# CANONICAL COLUMN DEFINITIONS
# =============================================================================

class ColumnAlign(Enum):
    """Text alignment for table columns."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass(frozen=True)
class ColumnDef:
    """Definition for a table column."""
    id: str  # CSS-safe ID for sorting/filtering
    header: str  # Display header (uppercase canonical: CMP, ATT, YDS)
    align: ColumnAlign = ColumnAlign.LEFT
    sortable: bool = True
    advanced: bool = False  # If True, shown in Advanced view only
    definition: str | None = None  # Tap-triggered definition content


# Canonical column sequences per spec
PASSING_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("pos", "Pos", ColumnAlign.CENTER, advanced=True),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("cmp", "CMP", ColumnAlign.CENTER, definition="Completed passes"),
    ColumnDef("att", "Att", ColumnAlign.CENTER, definition="Pass attempts"),
    ColumnDef("cmp_pct", "CMP%", ColumnAlign.CENTER, definition="Completions divided by attempts"),
    ColumnDef("yds", "Yds", ColumnAlign.RIGHT, definition="Total passing yards"),
    ColumnDef("yds_per_att", "Y/A", ColumnAlign.RIGHT, definition="Yards per pass attempt"),
    ColumnDef("lng", "Lng", ColumnAlign.CENTER, advanced=True, definition="Longest pass play"),
    ColumnDef("td", "TD", ColumnAlign.CENTER, definition="Touchdown passes thrown"),
    ColumnDef("int", "Int", ColumnAlign.CENTER, definition="Interceptions thrown"),
    ColumnDef("sack", "Sack", ColumnAlign.CENTER, advanced=True, definition="Times sacked"),
    ColumnDef("rate", "Rate", ColumnAlign.RIGHT, definition="NCAA pass efficiency formula (not QBR)"),
]

RUSHING_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("pos", "Pos", ColumnAlign.CENTER, advanced=True),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("att", "Att", ColumnAlign.CENTER, definition="Rush attempts"),
    ColumnDef("yds", "Yds", ColumnAlign.RIGHT, definition="Total rushing yards"),
    ColumnDef("yds_per_att", "Y/A", ColumnAlign.RIGHT, definition="Yards per rush attempt"),
    ColumnDef("lng", "Lng", ColumnAlign.RIGHT, advanced=True, definition="Longest rush"),
    ColumnDef("td", "TD", ColumnAlign.CENTER, definition="Rushing touchdowns"),
    ColumnDef("yds_per_gm", "Y/G", ColumnAlign.RIGHT, definition="Rushing yards per game"),
]

RECEIVING_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("pos", "Pos", ColumnAlign.CENTER, advanced=True),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("rec", "Rec", ColumnAlign.CENTER, definition="Pass receptions"),
    ColumnDef("yds", "Yds", ColumnAlign.RIGHT, definition="Total receiving yards"),
    ColumnDef("yds_per_rec", "Y/R", ColumnAlign.RIGHT, definition="Yards per catch"),
    ColumnDef("lng", "Lng", ColumnAlign.RIGHT, advanced=True, definition="Longest reception"),
    ColumnDef("td", "TD", ColumnAlign.CENTER, definition="Receiving touchdowns"),
    ColumnDef("yds_per_gm", "Y/G", ColumnAlign.RIGHT, definition="Receiving yards per game"),
]

TEAM_OFFENSE_COLUMNS = [
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("conf", "Conf", ColumnAlign.CENTER),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("pts", "Pts", ColumnAlign.RIGHT, definition="Points scored"),
    ColumnDef("pts_per_gm", "Pts/G", ColumnAlign.RIGHT, definition="Points per game"),
    ColumnDef("yds", "Yds", ColumnAlign.RIGHT, definition="Total offense yards"),
    ColumnDef("yds_per_gm", "Yds/G", ColumnAlign.RIGHT, definition="Yards per game"),
    ColumnDef("plays", "Pl", ColumnAlign.CENTER, definition="Offensive plays"),
    ColumnDef("yds_per_play", "Y/P", ColumnAlign.RIGHT, definition="Yards per offensive play"),
    ColumnDef("pass_yds", "Pass", ColumnAlign.RIGHT, definition="Passing yards"),
    ColumnDef("pass_yds_per_gm", "P/G", ColumnAlign.RIGHT, definition="Pass yards per game"),
    ColumnDef("rush_yds", "Rush", ColumnAlign.RIGHT, definition="Rushing yards"),
    ColumnDef("rush_yds_per_gm", "R/G", ColumnAlign.RIGHT, definition="Rush yards per game"),
    ColumnDef("first_downs", "1st", ColumnAlign.CENTER, definition="Total first downs"),
    ColumnDef("third_down_pct", "3rd%", ColumnAlign.CENTER, definition="3rd down conversion rate"),
    ColumnDef("fourth_down_pct", "4th%", ColumnAlign.CENTER, definition="4th down conversion rate"),
    ColumnDef("red_zone_pct", "RZ%", ColumnAlign.CENTER, definition="Red zone TD rate"),
    ColumnDef("turnovers", "TO", ColumnAlign.CENTER, definition="Total turnovers"),
]

# Team defense mirrors offense with "Allowed" labels
TEAM_DEFENSE_COLUMNS = [
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("conf", "Conf", ColumnAlign.CENTER),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("pts_allowed", "Pts", ColumnAlign.RIGHT, definition="Points allowed"),
    ColumnDef("pts_allowed_per_gm", "Pts/G", ColumnAlign.RIGHT, definition="Points allowed per game"),
    ColumnDef("yds_allowed", "Yds", ColumnAlign.RIGHT, definition="Total yards allowed"),
    ColumnDef("yds_allowed_per_gm", "Yds/G", ColumnAlign.RIGHT, definition="Yards allowed per game"),
    ColumnDef("yds_allowed_per_play", "Y/P", ColumnAlign.RIGHT, definition="Yards allowed per play"),
    ColumnDef("pass_yds_allowed", "Pass", ColumnAlign.RIGHT, definition="Passing yards allowed"),
    ColumnDef("pass_yds_allowed_per_gm", "P/G", ColumnAlign.RIGHT, definition="Pass yards allowed per game"),
    ColumnDef("rush_yds_allowed", "Rush", ColumnAlign.RIGHT, definition="Rushing yards allowed"),
    ColumnDef("rush_yds_allowed_per_gm", "R/G", ColumnAlign.RIGHT, definition="Rush yards allowed per game"),
    ColumnDef("opp_third_down_pct", "3rd%", ColumnAlign.CENTER, definition="Opponent 3rd down conversion rate"),
    ColumnDef("opp_fourth_down_pct", "4th%", ColumnAlign.CENTER, definition="Opponent 4th down conversion rate"),
    ColumnDef("opp_red_zone_pct", "RZ%", ColumnAlign.CENTER, definition="Opponent red zone TD rate"),
]


# Defensive Line — conformance spec §1.4.
# Order: Player | Team | POS | GP | TKL | SOLO | AST | TFL | SACK | QBH | FF | FR | PD
DL_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("pos", "Pos", ColumnAlign.CENTER, advanced=True),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("tkl", "TKL", ColumnAlign.RIGHT, definition="Total tackles (SOLO + AST)"),
    ColumnDef("solo", "Solo", ColumnAlign.RIGHT, advanced=True, definition="Unassisted tackles"),
    ColumnDef("ast", "Ast", ColumnAlign.RIGHT, advanced=True, definition="Assisted tackles (half-tackle in NCAA scoring)"),
    ColumnDef("tfl", "TFL", ColumnAlign.RIGHT, definition="Tackles for loss; NCAA convention counts sacks in this total"),
    ColumnDef("sack", "Sack", ColumnAlign.RIGHT, definition="Sacks (half-sacks count as 0.5)"),
    ColumnDef("qbh", "QBH", ColumnAlign.RIGHT, advanced=True, definition="QB hurries / pressures where tracked"),
    ColumnDef("ff", "FF", ColumnAlign.CENTER, definition="Forced fumbles"),
    ColumnDef("fr", "FR", ColumnAlign.CENTER, definition="Fumble recoveries"),
    ColumnDef("pd", "PD", ColumnAlign.CENTER, advanced=True, definition="Pass deflections at the line"),
]

# Linebackers — conformance spec §1.5.
# Order: Player | Team | POS | GP | TKL | SOLO | AST | TFL | SACK | INT | PD | FF | FR
LB_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("pos", "Pos", ColumnAlign.CENTER, advanced=True),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("tkl", "TKL", ColumnAlign.RIGHT, definition="Total tackles (SOLO + AST)"),
    ColumnDef("solo", "Solo", ColumnAlign.RIGHT, advanced=True, definition="Unassisted tackles"),
    ColumnDef("ast", "Ast", ColumnAlign.RIGHT, advanced=True, definition="Assisted tackles"),
    ColumnDef("tfl", "TFL", ColumnAlign.RIGHT, definition="Tackles for loss"),
    ColumnDef("sack", "Sack", ColumnAlign.RIGHT, definition="Sacks"),
    ColumnDef("int", "Int", ColumnAlign.RIGHT, definition="Interceptions"),
    ColumnDef("pd", "PD", ColumnAlign.RIGHT, definition="Pass deflections"),
    ColumnDef("ff", "FF", ColumnAlign.CENTER, definition="Forced fumbles"),
    ColumnDef("fr", "FR", ColumnAlign.CENTER, definition="Fumble recoveries"),
]

# Defensive Backs — conformance spec §1.6.
# Order: Player | Team | POS | GP | TKL | SOLO | AST | INT | INT-YDS | INT-TD | PD | PASS DEF | FF | FR
DB_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("pos", "Pos", ColumnAlign.CENTER, advanced=True),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("tkl", "TKL", ColumnAlign.RIGHT, definition="Total tackles"),
    ColumnDef("solo", "Solo", ColumnAlign.RIGHT, advanced=True, definition="Unassisted tackles"),
    ColumnDef("ast", "Ast", ColumnAlign.RIGHT, advanced=True, definition="Assisted tackles"),
    ColumnDef("int", "Int", ColumnAlign.RIGHT, definition="Interceptions"),
    ColumnDef("int_yds", "Int Yds", ColumnAlign.RIGHT, advanced=True, definition="Interception return yards"),
    ColumnDef("int_td", "Int TD", ColumnAlign.CENTER, definition="Pick-sixes"),
    ColumnDef("pd", "PD", ColumnAlign.RIGHT, definition="Pass deflections"),
    ColumnDef("pass_def", "Pass Def", ColumnAlign.RIGHT, definition="Passes defended (INT + PD); NCAA convention"),
    ColumnDef("ff", "FF", ColumnAlign.CENTER, advanced=True, definition="Forced fumbles"),
    ColumnDef("fr", "FR", ColumnAlign.CENTER, advanced=True, definition="Fumble recoveries"),
]

# Kickers — conformance spec §1.7.
# Range buckets stored as `made/attempted` strings (e.g. "4/5") per Sports-Reference convention.
KICKING_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("fgm", "FGM", ColumnAlign.RIGHT, definition="Field goals made"),
    ColumnDef("fga", "FGA", ColumnAlign.RIGHT, definition="Field goals attempted"),
    ColumnDef("fg_pct", "FG%", ColumnAlign.RIGHT, definition="Field goal make rate"),
    ColumnDef("lng", "Lng", ColumnAlign.RIGHT, definition="Longest field goal made"),
    ColumnDef("fg_0_19", "0-19", ColumnAlign.CENTER, advanced=True, definition="Made/attempted from 0-19 yards"),
    ColumnDef("fg_20_29", "20-29", ColumnAlign.CENTER, advanced=True, definition="Made/attempted from 20-29 yards"),
    ColumnDef("fg_30_39", "30-39", ColumnAlign.CENTER, advanced=True, definition="Made/attempted from 30-39 yards"),
    ColumnDef("fg_40_49", "40-49", ColumnAlign.CENTER, advanced=True, definition="Made/attempted from 40-49 yards"),
    ColumnDef("fg_50_plus", "50+", ColumnAlign.CENTER, advanced=True, definition="Made/attempted from 50+ yards"),
    ColumnDef("xpm", "XPM", ColumnAlign.RIGHT, definition="Extra points made"),
    ColumnDef("xpa", "XPA", ColumnAlign.RIGHT, definition="Extra points attempted"),
    ColumnDef("xp_pct", "XP%", ColumnAlign.RIGHT, advanced=True, definition="Extra point make rate"),
    ColumnDef("pts", "Pts", ColumnAlign.RIGHT, definition="Total points scored (3×FGM + XPM)"),
]

# Punters — conformance spec §1.8.
# `AVG` here is acceptable because the table is unambiguously punting.
PUNTING_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("punts", "Punts", ColumnAlign.RIGHT, definition="Total punts"),
    ColumnDef("yds", "Yds", ColumnAlign.RIGHT, definition="Gross punting yards"),
    ColumnDef("punt_avg", "Avg", ColumnAlign.RIGHT, definition="Gross yards per punt"),
    ColumnDef("net", "Net", ColumnAlign.RIGHT, definition="Net average after returns and touchback penalty"),
    ColumnDef("lng", "Lng", ColumnAlign.RIGHT, definition="Longest punt"),
    ColumnDef("tb", "TB", ColumnAlign.CENTER, advanced=True, definition="Touchbacks (punts into the end zone)"),
    ColumnDef("i20", "In20", ColumnAlign.CENTER, definition="Punts downed inside opponent 20-yard line"),
    ColumnDef("fc", "FC", ColumnAlign.CENTER, advanced=True, definition="Fair catches forced"),
    ColumnDef("blk", "Blk", ColumnAlign.CENTER, advanced=True, definition="Punts blocked"),
]

# Returners — conformance spec §1.9.
# When kick + punt returns appear in the same table, use KR- / PR- prefixes.
RETURNING_COLUMNS = [
    ColumnDef("player", "Player", ColumnAlign.LEFT, sortable=False),
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("kr", "KR", ColumnAlign.RIGHT, definition="Kick returns"),
    ColumnDef("kr_yds", "KR Yds", ColumnAlign.RIGHT, definition="Kick return yards"),
    ColumnDef("kr_avg", "KR Avg", ColumnAlign.RIGHT, definition="Yards per kick return"),
    ColumnDef("kr_lng", "KR Lng", ColumnAlign.RIGHT, advanced=True, definition="Longest kick return"),
    ColumnDef("kr_td", "KR TD", ColumnAlign.CENTER, definition="Kick-return touchdowns"),
    ColumnDef("pr", "PR", ColumnAlign.RIGHT, definition="Punt returns"),
    ColumnDef("pr_yds", "PR Yds", ColumnAlign.RIGHT, definition="Punt return yards"),
    ColumnDef("pr_avg", "PR Avg", ColumnAlign.RIGHT, definition="Yards per punt return"),
    ColumnDef("pr_lng", "PR Lng", ColumnAlign.RIGHT, advanced=True, definition="Longest punt return"),
    ColumnDef("pr_td", "PR TD", ColumnAlign.CENTER, definition="Punt-return touchdowns"),
]

# Team Special Teams — conformance spec §1.11.
TEAM_SPECIAL_TEAMS_COLUMNS = [
    ColumnDef("team", "Team", ColumnAlign.LEFT, sortable=False),
    ColumnDef("conf", "Conf", ColumnAlign.CENTER),
    ColumnDef("gp", "GP", ColumnAlign.CENTER),
    ColumnDef("fg_pct", "FG%", ColumnAlign.RIGHT, definition="Team field goal make rate"),
    ColumnDef("fg_lng", "FG Lng", ColumnAlign.RIGHT, advanced=True, definition="Longest field goal made by the team"),
    ColumnDef("xp_pct", "XP%", ColumnAlign.RIGHT, advanced=True, definition="Team extra-point make rate"),
    ColumnDef("kr_avg", "KR Avg", ColumnAlign.RIGHT, definition="Team kick-return average"),
    ColumnDef("pr_avg", "PR Avg", ColumnAlign.RIGHT, definition="Team punt-return average"),
    ColumnDef("net_punt", "Net Punt", ColumnAlign.RIGHT, definition="Team net punting average"),
    ColumnDef("tb_pct", "TB%", ColumnAlign.CENTER, advanced=True, definition="Touchback rate (lower is better for punting)"),
    ColumnDef("punt_blk", "Punt Blk", ColumnAlign.CENTER, advanced=True, definition="Punts blocked by team"),
    ColumnDef("kick_blk", "Kick Blk", ColumnAlign.CENTER, advanced=True, definition="Kicks blocked by team"),
    ColumnDef("ret_td", "Ret TD", ColumnAlign.CENTER, definition="Special-teams touchdowns scored"),
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class StatRow:
    """A single row of stats (player or team)."""
    # Identity columns (required)
    name: str
    slug: str | None = None  # For link generation
    team: str | None = None
    team_slug: str | None = None
    position: str | None = None

    # Stat values (use underscore keys matching ColumnDef.id)
    values: dict[str, str | int | float | None] = field(default_factory=dict)

    # Optional cross-link target
    link_url: str | None = None
    link_type: Literal["player", "team", "opponent", "game"] | None = None


@dataclass
class TableConfig:
    """Configuration for stats table rendering."""
    table_id: str = "stats-table"
    css_class: str = "wcfb-stats-table"
    wrap_class: str = "wcfb-stats-wrap"
    columns: list[ColumnDef] = field(default_factory=list)
    default_sort: str | None = None  # Column ID for default sort
    default_sort_dir: Literal["asc", "desc"] = "desc"
    show_advanced: bool = False  # If False, hide advanced columns
    mobile_collapse: bool = False  # If True, hide specified columns on mobile


# =============================================================================
# RENDERER
# =============================================================================

class StatsTableRenderer:
    """Renders world-class CFB stats tables."""

    def __init__(
        self,
        config: TableConfig,
        rows: list[StatRow],
    ):
        self.config = config
        self.rows = rows
        self._visible_columns = self._get_visible_columns()

    def _get_visible_columns(self) -> list[ColumnDef]:
        """Get columns that should be visible based on config."""
        if self.config.show_advanced:
            return self.config.columns
        return [c for c in self.config.columns if not c.advanced]

    def _render_cell(
        self,
        column: ColumnDef,
        row: StatRow,
        is_header: bool = False,
    ) -> str:
        """Render a single table cell."""
        if is_header:
            return self._render_header_cell(column)
        return self._render_data_cell(column, row)

    def _render_header_cell(self, column: ColumnDef) -> str:
        """Render a table header cell with sort affordance."""
        if not column.sortable:
            safe_header = _html.escape(column.header)
            return f'<th scope="col">{safe_header}</th>'

        # Sortable header with button (44×44px tap target)
        safe_id = _html.escape(column.id)
        safe_header = _html.escape(column.header)
        is_default = (column.id == self.config.default_sort)
        default_dir = self.config.default_sort_dir if is_default else ""

        attrs = [
            f'class="wcfb-align-{column.align.value}"',
            f'data-sort="{safe_id}"',
        ]
        if is_default:
            attrs.append(f'aria-sort="{default_dir == "desc" and "descending" or "ascending"}"')

        def_trigger = ""
        if column.definition:
            safe_def = _html.escape(column.definition)
            def_trigger = f'<span class="wcfb-def-trigger" data-def="{safe_def}" aria-label="Definition">?</span>'

        return f"""<th {" ".join(attrs)}>
  <button class="wcfb-sort-btn" type="button">
    <span>{safe_header}</span>
    <svg class="wcfb-sort-icon" width="8" height="8" viewBox="0 0 8 8" fill="currentColor" aria-hidden="true">
      <path d="M4 0L0 6h8L4 0z"/>
    </svg>
    {def_trigger}
  </button>
</th>"""

    def _render_data_cell(self, column: ColumnDef, row: StatRow) -> str:
        """Render a data cell with proper alignment and links."""
        # Special handling for identity columns
        if column.id == "player":
            return self._render_player_cell(row)
        if column.id == "team":
            return self._render_team_cell(row)

        # Standard stat value
        value = row.values.get(column.id, "")
        if value is None:
            value = ""

        # Format numeric values
        if isinstance(value, float):
            value = f"{value:.1f}" if value % 1 else f"{int(value)}"
        elif isinstance(value, int):
            value = str(value)
        else:
            value = str(value)

        safe_value = _html.escape(value)
        align_class = f"wcfb-align-{column.align.value}"

        return f'<td class="{align_class}">{safe_value}</td>'

    def _render_player_cell(self, row: StatRow) -> str:
        """Render the player name cell with link."""
        safe_name = _html.escape(row.name)

        if row.link_url and row.link_type == "player":
            safe_url = _html.escape(row.link_url)
            return f'<td class="wcfb-align-left"><a href="{safe_url}" class="wcfb-cross-link">{safe_name}</a></td>'

        return f'<td class="wcfb-align-left">{safe_name}</td>'

    def _render_team_cell(self, row: StatRow) -> str:
        """Render the team cell with link."""
        team = row.team or ""
        safe_team = _html.escape(team)

        if row.team_slug and row.link_url:
            safe_url = _html.escape(row.link_url)
            return f'<td class="wcfb-align-left"><a href="{safe_url}" class="wcfb-cross-link">{safe_team}</a></td>'

        return f'<td class="wcfb-align-left">{safe_team}</td>'

    def render(self) -> str:
        """Render the complete stats table."""
        rows_html = []

        # Header row
        headers = [self._render_cell(col, None, is_header=True) for col in self._visible_columns]
        rows_html.append(f"<thead><tr>{''.join(headers)}</tr></thead>")

        # Data rows
        body_rows = []
        for row in self.rows:
            cells = [self._render_cell(col, row) for col in self._visible_columns]
            body_rows.append(f"<tr>{''.join(cells)}</tr>")
        rows_html.append(f"<tbody>{''.join(body_rows)}</tbody>")

        table_html = "\n".join(rows_html)

        safe_id = _html.escape(self.config.table_id)
        safe_table_class = _html.escape(self.config.css_class)
        safe_wrap_class = _html.escape(self.config.wrap_class)

        return f"""<div class="{safe_wrap_class}" id="{safe_id}-wrap">
<table class="{safe_table_class}" id="{safe_id}">
{table_html}
</table>
</div>"""


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def render_passing_table(
    rows: list[StatRow],
    table_id: str = "passing-stats",
    show_advanced: bool = False,
    default_sort: str = "yds",
) -> str:
    """Render a passing stats table with canonical column sequence."""
    config = TableConfig(
        table_id=table_id,
        columns=PASSING_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_rushing_table(
    rows: list[StatRow],
    table_id: str = "rushing-stats",
    show_advanced: bool = False,
    default_sort: str = "yds",
) -> str:
    """Render a rushing stats table with canonical column sequence."""
    config = TableConfig(
        table_id=table_id,
        columns=RUSHING_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_receiving_table(
    rows: list[StatRow],
    table_id: str = "receiving-stats",
    show_advanced: bool = False,
    default_sort: str = "yds",
) -> str:
    """Render a receiving stats table with canonical column sequence."""
    config = TableConfig(
        table_id=table_id,
        columns=RECEIVING_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_team_offense_table(
    rows: list[StatRow],
    table_id: str = "offense-stats",
    default_sort: str = "yds_per_gm",
) -> str:
    """Render a team offense stats table with canonical column sequence."""
    config = TableConfig(
        table_id=table_id,
        columns=TEAM_OFFENSE_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_team_defense_table(
    rows: list[StatRow],
    table_id: str = "defense-stats",
    default_sort: str = "yds_allowed_per_gm",
) -> str:
    """Render a team defense stats table with canonical column sequence."""
    config = TableConfig(
        table_id=table_id,
        columns=TEAM_DEFENSE_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="asc",  # Lower is better for defense
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_dl_table(
    rows: list[StatRow],
    table_id: str = "dl-stats",
    show_advanced: bool = False,
    default_sort: str = "tfl",
) -> str:
    """Render a defensive-line stats table (conformance spec §1.4).

    Default sort is TFL: linemen are valued for backfield disruption, not
    raw tackle count. Linebacker tables default to TKL instead.
    """
    config = TableConfig(
        table_id=table_id,
        columns=DL_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_lb_table(
    rows: list[StatRow],
    table_id: str = "lb-stats",
    show_advanced: bool = False,
    default_sort: str = "tkl",
) -> str:
    """Render a linebacker stats table (conformance spec §1.5).

    Default sort is total tackles — the volume metric most expected on LB
    leaderboards. Re-sort to SACK or INT for specialty views.
    """
    config = TableConfig(
        table_id=table_id,
        columns=LB_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_db_table(
    rows: list[StatRow],
    table_id: str = "db-stats",
    show_advanced: bool = False,
    default_sort: str = "pass_def",
) -> str:
    """Render a defensive-backs stats table (conformance spec §1.6).

    Default sort is PASS DEF (INT + PD), the NCAA convention summary for
    coverage production. Re-sort to INT for ball-hawk-only leaderboards.
    """
    config = TableConfig(
        table_id=table_id,
        columns=DB_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_kicking_table(
    rows: list[StatRow],
    table_id: str = "kicking-stats",
    show_advanced: bool = False,
    default_sort: str = "pts",
) -> str:
    """Render a kicking stats table (conformance spec §1.7).

    Default sort is total points (the kicker's contribution to the
    scoreboard). FG% is the secondary view for accuracy-first comparison.
    """
    config = TableConfig(
        table_id=table_id,
        columns=KICKING_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_punting_table(
    rows: list[StatRow],
    table_id: str = "punting-stats",
    show_advanced: bool = False,
    default_sort: str = "net",
) -> str:
    """Render a punting stats table (conformance spec §1.8).

    Default sort is NET average — the metric that reflects actual field-
    position impact after returns and touchback penalty. Gross AVG is
    cosmetic by comparison.
    """
    config = TableConfig(
        table_id=table_id,
        columns=PUNTING_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_returning_table(
    rows: list[StatRow],
    table_id: str = "returning-stats",
    show_advanced: bool = False,
    default_sort: str = "kr_avg",
) -> str:
    """Render a returners stats table (conformance spec §1.9)."""
    config = TableConfig(
        table_id=table_id,
        columns=RETURNING_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
        show_advanced=show_advanced,
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


def render_team_special_teams_table(
    rows: list[StatRow],
    table_id: str = "special-teams-stats",
    default_sort: str = "net_punt",
) -> str:
    """Render a team special-teams stats table (conformance spec §1.11)."""
    config = TableConfig(
        table_id=table_id,
        columns=TEAM_SPECIAL_TEAMS_COLUMNS,
        default_sort=default_sort,
        default_sort_dir="desc",
    )
    renderer = StatsTableRenderer(config, rows)
    return renderer.render()


# =============================================================================
# ASSET HELPERS
# =============================================================================

def render_stats_assets_head(
    *,
    css_url: str = "/assets/stats_table.css",
    js_url: str = "/assets/stat_definitions.js",
) -> str:
    """Emit the <head> assets for the stats table component.

    Output shape:
        <link rel="stylesheet" href="/assets/stats_table.css">
        <script defer src="/assets/stat_definitions.js"></script>
    """
    safe_css = _html.escape(css_url)
    safe_js = _html.escape(js_url)
    return f"""<link rel="stylesheet" href="{safe_css}">
<script defer src="{safe_js}"></script>"""


__all__ = [
    # Data structures
    "ColumnAlign",
    "ColumnDef",
    "StatRow",
    "TableConfig",
    # Renderer
    "StatsTableRenderer",
    # Factory functions
    "render_passing_table",
    "render_rushing_table",
    "render_receiving_table",
    "render_team_offense_table",
    "render_team_defense_table",
    # Asset helpers
    "render_stats_assets_head",
]
