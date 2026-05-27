"""Player-pages modules — new world-class chrome for /players/<slug>.html.

Mirrors the team_pages/ package pattern. Each module has a render_*()
function + CSS constant. Modules are injected into the legacy
reporting.py render_player_page_html via additional sections.

Modules in this package:
  - coaching_lineage : Current HC + position coach + tenure context
  - mirror_match     : Historical fingerprint match (closest similar player)
  - live_signal_flow : Top-of-page live-signal placeholder
  - standing_rail    : 17-rung player Standing rail (Brief §7)
"""
from __future__ import annotations

from .coaching_lineage import render_coaching_lineage, COACHING_LINEAGE_CSS
from .mirror_match import render_mirror_match, MIRROR_MATCH_CSS
from .live_signal_flow import render_live_signal_flow, LIVE_SIGNAL_FLOW_CSS
from .standing_rail import render_standing_rail, STANDING_RAIL_CSS
from .heisman_trajectory import render_heisman_trajectory, HEISMAN_TRAJECTORY_CSS
from .career_arc import render_career_arc, CAREER_ARC_CSS
from .development_trajectory import render_development_trajectory, DEVELOPMENT_TRAJECTORY_CSS
from .selector_grid import render_selector_grid, SELECTOR_GRID_CSS
from .game_log import render_game_log, GAME_LOG_CSS
from .box_savant import render_box_savant, BOX_SAVANT_CSS
from .splits import render_splits, SPLITS_CSS
from .peer_comparator import render_peer_comparator, PEER_COMPARATOR_CSS
from .design_tokens import PLAYER_PAGE_TOKENS_CSS
from .supporting_cast import render_supporting_cast, SUPPORTING_CAST_CSS
from .narrative_arc_renderer import render_narrative_arc, NARRATIVE_ARC_CSS
from .narrative_arc_generator import fetch_narrative_arc
from .nil_draft import render_nil_draft, NIL_DRAFT_CSS
from .scenario_explorer import render_scenario_explorer, SCENARIO_EXPLORER_CSS
from .career_standing import render_career_standing, CAREER_STANDING_CSS
from .trophy_case import render_trophy_case, TROPHY_CASE_CSS
from .sparklines import build_stat_sparklines, SPARKLINE_CSS


__all__ = [
    "render_coaching_lineage",
    "COACHING_LINEAGE_CSS",
    "render_mirror_match",
    "MIRROR_MATCH_CSS",
    "render_live_signal_flow",
    "LIVE_SIGNAL_FLOW_CSS",
    "render_standing_rail",
    "STANDING_RAIL_CSS",
    "render_heisman_trajectory",
    "HEISMAN_TRAJECTORY_CSS",
    "render_career_arc",
    "CAREER_ARC_CSS",
    "render_development_trajectory",
    "DEVELOPMENT_TRAJECTORY_CSS",
    "render_selector_grid",
    "SELECTOR_GRID_CSS",
    "render_game_log",
    "GAME_LOG_CSS",
    "render_box_savant",
    "BOX_SAVANT_CSS",
    "render_splits",
    "SPLITS_CSS",
    "render_peer_comparator",
    "PEER_COMPARATOR_CSS",
    "PLAYER_PAGE_TOKENS_CSS",
    "render_supporting_cast",
    "SUPPORTING_CAST_CSS",
    "render_narrative_arc",
    "NARRATIVE_ARC_CSS",
    "fetch_narrative_arc",
    "render_nil_draft",
    "NIL_DRAFT_CSS",
    "render_scenario_explorer",
    "SCENARIO_EXPLORER_CSS",
    "render_career_standing",
    "CAREER_STANDING_CSS",
    "render_trophy_case",
    "TROPHY_CASE_CSS",
    "build_stat_sparklines",
    "SPARKLINE_CSS",
]
