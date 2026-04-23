"""Tigerdroppings (LSU) — TASK 5.2. RSS-listing + Cowork body-fill hybrid."""
from __future__ import annotations

from cfb_rankings.ingest.sources.boards._base import BoardRssAdapter


class TigerdroppingsAdapter(BoardRssAdapter):
    source_id = "board_tigerdroppings"
    feed_url = "https://www.tigerdroppings.com/rss/forum/lsu-sports.rss"
    adapter_version = "0.1.0"


__all__ = ["TigerdroppingsAdapter"]
