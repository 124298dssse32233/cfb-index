"""YouTube metadata adapter — TASK 2.5.

For every ``priority_teams.youtube_team_channel_id`` (and each element in the
``youtube_fan_channels`` JSON array), pull the channel's recent uploads and
capture per-video views + comment count. Stored as one source_observations
row per (video, metric).

Requires ``YOUTUBE_API_KEY`` environment variable. Uses the free 10k-unit
daily quota; at ~3 units per uploads-playlist lookup we stay <5%.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.numeric_base import NumericSourceAdapter

logger = logging.getLogger(__name__)

_CHANNEL_URL = (
    "https://www.googleapis.com/youtube/v3/channels?part=contentDetails"
    "&id={channel_id}&key={key}"
)
_PLAYLIST_URL = (
    "https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails"
    "&playlistId={playlist_id}&maxResults=10&key={key}"
)
_VIDEOS_URL = (
    "https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics"
    "&id={video_ids}&key={key}"
)


class YouTubeMetaAdapter(NumericSourceAdapter):
    source_id = "youtube_meta"
    adapter_version = "0.1.0"
    min_seconds_between_requests = 0.2

    def __init__(self, db: Database, api_key: str | None = None) -> None:
        super().__init__(db)
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")

    def _resolve_uploads_playlist(self, channel_id: str) -> str | None:
        try:
            data = json.loads(self.http_get(
                _CHANNEL_URL.format(channel_id=channel_id, key=self.api_key)
            ).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("youtube channel lookup failed for %s: %s", channel_id, exc)
            return None
        items = data.get("items") or []
        if not items:
            return None
        return ((items[0].get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")

    def _recent_video_ids(self, playlist_id: str) -> list[str]:
        try:
            data = json.loads(self.http_get(
                _PLAYLIST_URL.format(playlist_id=playlist_id, key=self.api_key)
            ).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("youtube playlist fetch failed for %s: %s", playlist_id, exc)
            return []
        return [
            (i.get("contentDetails") or {}).get("videoId")
            for i in (data.get("items") or [])
            if (i.get("contentDetails") or {}).get("videoId")
        ]

    def _video_stats(self, video_ids: list[str]) -> list[dict[str, Any]]:
        if not video_ids:
            return []
        try:
            data = json.loads(self.http_get(
                _VIDEOS_URL.format(video_ids=",".join(video_ids), key=self.api_key)
            ).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("youtube videos lookup failed: %s", exc)
            return []
        return data.get("items") or []

    def fetch(self) -> list[dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY env var is required")
        teams = self.db.query_all(
            "select team_id, youtube_team_channel_id, youtube_fan_channels from priority_teams"
        )
        channels: list[tuple[int, str, str]] = []  # (team_id, channel_id, role)
        for t in teams:
            if t.get("youtube_team_channel_id"):
                channels.append((t["team_id"], t["youtube_team_channel_id"], "team"))
            if t.get("youtube_fan_channels"):
                try:
                    fans = json.loads(t["youtube_fan_channels"])
                except Exception:  # noqa: BLE001
                    fans = []
                for cid in fans or []:
                    channels.append((t["team_id"], cid, "fan"))

        all_videos: list[dict[str, Any]] = []
        for team_id, channel_id, role in channels:
            uploads = self._resolve_uploads_playlist(channel_id)
            if not uploads:
                continue
            vids = self._recent_video_ids(uploads)
            stats = self._video_stats(vids)
            for v in stats:
                v["_team_id"] = team_id
                v["_channel_id"] = channel_id
                v["_role"] = role
                all_videos.append(v)
        return all_videos

    def parse(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        now_iso = _utcnow_iso()
        for v in raw:
            stats = v.get("statistics") or {}
            snip = v.get("snippet") or {}
            video_id = v.get("id")
            if not video_id:
                continue
            url = f"https://www.youtube.com/watch?v={video_id}"
            base = {
                "entity_type": f"youtube_video_{v.get('_role', 'team')}",
                "entity_id": video_id,
                "entity_label": snip.get("title"),
                "observed_at_utc": now_iso,
                "sample_window": "instant",
                "capture_url": url,
                "canonical_url": url,
                "raw_payload_json": {
                    "team_id": v.get("_team_id"),
                    "channel_id": v.get("_channel_id"),
                    "channel_title": snip.get("channelTitle"),
                    "published_at": snip.get("publishedAt"),
                    "statistics": stats,
                },
            }
            for metric_key, stat_key in (
                ("video_views", "viewCount"),
                ("video_likes", "likeCount"),
                ("video_comments", "commentCount"),
            ):
                val = stats.get(stat_key)
                if val is None:
                    continue
                out.append({
                    **base, "metric": metric_key,
                    "value_numeric": float(int(val)),
                    "dedup_key": self.make_dedup_key(
                        self.source_id, video_id, metric_key, now_iso,
                    ),
                })
        return out


def _utcnow_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["YouTubeMetaAdapter"]
