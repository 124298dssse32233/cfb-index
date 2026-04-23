"""VolNation (Tennessee) — TASK 5.4. XenForo-based; exposes forum RSS."""
from __future__ import annotations

from cfb_rankings.ingest.sources.boards._base import BoardRssAdapter


class VolNationAdapter(BoardRssAdapter):
    source_id = "board_volnation"
    feed_url = "https://www.volnation.com/forum/forums/primary-site.1/index.rss"
    adapter_version = "0.1.0"


__all__ = ["VolNationAdapter"]
