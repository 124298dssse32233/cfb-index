"""The Daily — weekday morning digest module.

Public entry points used by cli.py and the GitHub Actions cron:

  select_inputs(conn, edition_date)  -> DailyInputBundle
  synthesize_takes(bundle)           -> list[TakeResult]
  persist_edition(conn, bundle, takes)
  render_daily(conn, edition_date)   -> list[Path]
  fetch_recent_editions(conn, limit) -> list[dict]
"""
from __future__ import annotations

from .selector import select_inputs
from .synthesizer import synthesize_takes, persist_edition
from .renderer import render_daily, fetch_recent_editions

__all__ = [
    "select_inputs",
    "synthesize_takes",
    "persist_edition",
    "render_daily",
    "fetch_recent_editions",
]
