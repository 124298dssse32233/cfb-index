"""Theme module (World-Class CFB Stats Display)

Components:
  * Theme toggle (Sprint v5-11.5 dark mode foundation)
  * Stats table renderer with canonical column sequences
  * Percentile bar component with red→grey→blue diverging scale
  * Tap-triggered stat definitions (bottom sheet mobile, popover desktop)

Theme toggle:
  * Three states — light / dark / system (respect prefers-color-scheme)
  * Persists choice to localStorage (key: cfb-theme-pref)
  * Applies via [data-theme="light"|"dark"] attribute on <html>

Stats tables:
  * Canonical column sequences per docs/research/cfb-stats-conformance-spec.md
  * Mobile-first: sticky first column, 44×44px tap targets, tabular numerals
  * Cross-link patterns for player/team/opponent navigation
  * Sortable headers with URL state persistence

Percentile bars:
  * Red→grey→blue diverging scale (Baseball Savant convention)
  * Sample-size confidence chips per docs/design-system/33-confidence-signaling.md

Stat definitions:
  * Tap-triggered on mobile, hover on desktop
  * One-sentence definition + formula + benchmark + methodology link

Specs:
  * docs/research/cfb-stats-conformance-spec.md
  * docs/research/cfb-stats-mobile-playbook.md
  * docs/research/cfb-stats-antipatterns.md
  * docs/design-system/31-chart-vocabulary.md
"""

from .render import (
    THEME_INIT_SCRIPT,
    render_theme_toggle_button,
    render_theme_assets_head,
)
from .stats_table import (
    ColumnAlign,
    ColumnDef,
    StatRow,
    TableConfig,
    StatsTableRenderer,
    render_passing_table,
    render_rushing_table,
    render_receiving_table,
    render_team_offense_table,
    render_team_defense_table,
    render_stats_assets_head,
)
from .percentile_bar import (
    PercentileBand,
    SampleSize,
    PercentileBar,
    PercentileBarRenderer,
    PercentileCardRenderer,
    render_percentile_bar,
    render_percentile_card,
    render_percentile_bars_grid,
    render_sample_badge,
    calculate_percentile,
    format_raw_value,
    percentile_tier_class,
)
from .player_stats import (
    convert_season_stat_section,
    render_player_passing_section,
    render_player_rushing_section,
    render_player_receiving_section,
    render_all_player_season_stat_tables,
)

__all__ = [
    # Theme toggle
    "THEME_INIT_SCRIPT",
    "render_theme_toggle_button",
    "render_theme_assets_head",
    # Stats table
    "ColumnAlign",
    "ColumnDef",
    "StatRow",
    "TableConfig",
    "StatsTableRenderer",
    "render_passing_table",
    "render_rushing_table",
    "render_receiving_table",
    "render_team_offense_table",
    "render_team_defense_table",
    "render_stats_assets_head",
    # Percentile bar
    "PercentileBand",
    "SampleSize",
    "PercentileBar",
    "PercentileBarRenderer",
    "PercentileCardRenderer",
    "render_percentile_bar",
    "render_percentile_card",
    "render_percentile_bars_grid",
    "render_sample_badge",
    "calculate_percentile",
    "format_raw_value",
    "percentile_tier_class",
    # Player stats integration
    "convert_season_stat_section",
    "render_player_passing_section",
    "render_player_rushing_section",
    "render_player_receiving_section",
    "render_all_player_season_stat_tables",
]
