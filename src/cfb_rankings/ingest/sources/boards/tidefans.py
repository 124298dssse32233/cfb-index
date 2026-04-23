"""TideFans (Alabama) — TASK 5.5. XenForo-based; exposes forum RSS."""
from __future__ import annotations

from cfb_rankings.ingest.sources.boards._base import BoardRssAdapter


class TideFansAdapter(BoardRssAdapter):
    source_id = "board_tidefans"
    feed_url = "https://www.tidefans.com/forums/alabama-football.2/index.rss"
    adapter_version = "0.1.0"


__all__ = ["TideFansAdapter"]
