"""Eleven Warriors forum (Ohio State) — TASK 5.6. Blog+forum hybrid."""
from __future__ import annotations

from cfb_rankings.ingest.sources.boards._base import BoardRssAdapter


class ElevenWarriorsAdapter(BoardRssAdapter):
    source_id = "board_11warriors"
    feed_url = "https://www.elevenwarriors.com/forum/recent/index.rss"
    adapter_version = "0.1.0"


__all__ = ["ElevenWarriorsAdapter"]
