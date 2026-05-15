"""S4 Recruit Watch Board surface.

Renders /recruit-board/<class_year>/index.html — top-25 programs by
weighted recruiting class strength. Reads player_recruiting_profiles.

Public API:
    render_recruit_board(db, *, class_year, output_dir) -> dict
"""
from .renderer import render_recruit_board

__all__ = ["render_recruit_board"]
