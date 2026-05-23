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


__all__ = [
    "render_coaching_lineage",
    "COACHING_LINEAGE_CSS",
    "render_mirror_match",
    "MIRROR_MATCH_CSS",
    "render_live_signal_flow",
    "LIVE_SIGNAL_FLOW_CSS",
    "render_standing_rail",
    "STANDING_RAIL_CSS",
]
