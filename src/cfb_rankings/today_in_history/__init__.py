"""S5 — Today in CFB History (offseason safety-net surface).

Renders ``/anniversary/today/`` with three priority tiers:

  1. ``archive_threads``     — high-engagement r/CFB submissions on
                                same MM-DD across prior years (written
                                by ``archive_retro_daily.yml`` +
                                ``ingest/sources/archive_retro.py``).
  2. ``team_chronicle_observations`` — same MM-DD across profiled teams.
                                These are the editorial cards already
                                generated for team pages, lifted into a
                                date-keyed view.
  3. ``historical_seasons_summary``  — week-anchored "this week N years
                                ago in the polls" data (optional table
                                — falls through if missing).

If ALL three tiers come up empty, we still emit a valid page with the
"Quiet day in CFB history — no big anniversaries today" empty state.
The page is the offseason safety net — it must never 404.

Spec:
  * IMPLEMENTATION_PLAN.md Part 5 Adapter 3 (powers archive_threads)
  * DESIGN_AUDIT_2026_05_15_v5_4.md Part 4 S5 + Part 5.
"""
from __future__ import annotations

from .data import AnniversaryCard, gather_today_in_history_cards
from .renderer import (
    render_today_in_history_html,
    render_today_in_history_page,
)

__all__ = [
    "AnniversaryCard",
    "gather_today_in_history_cards",
    "render_today_in_history_html",
    "render_today_in_history_page",
]
