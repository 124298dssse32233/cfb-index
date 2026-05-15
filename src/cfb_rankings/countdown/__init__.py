"""S1 Days-to-Kickoff countdown surface.

A daily lightweight refresh that writes two artifacts:
  - /kickoff/index.html — full landing page
  - /assets/countdown.json — small JSON consumed by sitewide countdown strip

Both are computed from cfb_calendar (KEY_EVENTS_<season> or games table).
No DB writes. No AI. No images. Just typography + a number.
"""
from .renderer import render_countdown

__all__ = ["render_countdown"]
