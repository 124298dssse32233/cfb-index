"""Shared BoardRssAdapter for boards that expose a forum-listing RSS feed."""
from __future__ import annotations

from typing import Any

from cfb_rankings.ingest.sources.base import BaseRssAdapter
from cfb_rankings.ingest.sources.campus_news import CampusNewsAdapter


class BoardRssAdapter(CampusNewsAdapter):
    """Base for message-board adapters.

    Subclasses set:
      - ``source_id``   (e.g. ``board_tigerdroppings``)
      - ``feed_url``    (forum listing RSS)
      - ``team_id``     (priority_teams.team_id)
    """

    source_id: str = ""
    feed_url: str = ""

    def __init__(self, db, team_id: int) -> None:
        self.team_id = team_id
        if not self.source_id or not self.feed_url:
            raise ValueError(
                f"{type(self).__name__} must set source_id + feed_url"
            )
        BaseRssAdapter.__init__(self, db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        row = super().row_from_entry(entry)
        if row is None:
            return None
        row.update({
            "source_id": self.source_id,
            "source_tier": "B",
            "author_identity_class": "pseudonymous",
            "demographic_slice": "hardcore_board",
            "retention_policy": "aggregated_only",
            "content_type": "thread_summary",
            "body_text": None,   # listing-only; body filled in via Cowork sweep
        })
        return row


__all__ = ["BoardRssAdapter"]
