"""Google News RSS adapter — TASK 3.6.

Per-team Google News query RSS (polled every 4h by the hourly ingest cron).
Query string comes from ``priority_teams.google_news_query``.
"""
from __future__ import annotations

import urllib.parse
from typing import Any

from cfb_rankings.ingest.sources.base import BaseRssAdapter
from cfb_rankings.ingest.sources.campus_news import CampusNewsAdapter

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class GoogleNewsAdapter(CampusNewsAdapter):
    """One instance per priority_teams row. ``source_id=google_news_{team_slug}``."""

    def __init__(self, db, team_id: int, team_slug: str, query: str) -> None:
        self.source_id = f"google_news_{team_slug.lower()}"
        self.feed_url = _GOOGLE_NEWS_RSS.format(query=urllib.parse.quote(query))
        self.team_id = team_id
        BaseRssAdapter.__init__(self, db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        row = super().row_from_entry(entry)
        if row is None:
            return None
        row.update({
            "source_id": self.source_id,
            "source_tier": "B",
            "author_identity_class": "verified_media",
            "demographic_slice": "aggregated_press",
            "retention_policy": "aggregated_only",
        })
        return row


__all__ = ["GoogleNewsAdapter"]
