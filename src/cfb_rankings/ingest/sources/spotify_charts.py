"""Spotify podcast chart adapter — TASK 2.8.

Spotify's public Podcast Charts endpoint exposes weekly top shows per category.
For CFB we track the ``sports`` category (Spotify does not break out CFB as a
dedicated category in public charts; we post-filter by show-title keyword match
against a curated list).

Auth: Spotify client-credentials flow with ``SPOTIFY_CLIENT_ID`` +
``SPOTIFY_CLIENT_SECRET``. No user scopes needed.

Landing rows: one per (show, week, chart_rank).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.numeric_base import NumericSourceAdapter

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_CHART_URL = (
    "https://api.spotify.com/v1/browse/categories/{category}/playlists"
    "?limit=50&offset=0"
)

# Curated CFB show keywords — any chart entry whose name matches wins a row.
_CFB_KEYWORDS = (
    "college football", "cfb", "saturday down south", "locked on",
    "paul finebaum", "gameday", "split zone", "the solid verbal",
)


class SpotifyChartsAdapter(NumericSourceAdapter):
    source_id = "spotify_charts"
    adapter_version = "0.1.0"
    min_seconds_between_requests = 0.5

    def __init__(self, db: Database,
                 client_id: str | None = None, client_secret: str | None = None) -> None:
        super().__init__(db)
        self.client_id = client_id or os.environ.get("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
        self._access_token: str | None = None

    def _get_token(self) -> str:
        if self._access_token:
            return self._access_token
        if not (self.client_id and self.client_secret):
            raise RuntimeError("SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET required")
        creds = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        from urllib.request import Request, urlopen
        req = Request(
            _TOKEN_URL,
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.user_agent,
            },
        )
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self._access_token = data["access_token"]
        return self._access_token

    def fetch(self) -> dict[str, Any]:
        token = self._get_token()
        try:
            raw = self.http_get(
                _CHART_URL.format(category="0JQ5DAudkNjCgYMM0TZXDw"),  # sports category
                headers={"Authorization": f"Bearer {token}"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("spotify charts fetch failed: %s", exc)
            return {}
        return json.loads(raw.decode("utf-8"))

    def parse(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        now = _utcnow_iso()
        items = ((raw.get("playlists") or {}).get("items")) or []
        rank = 0
        for item in items:
            name = (item.get("name") or "").lower()
            if not any(kw in name for kw in _CFB_KEYWORDS):
                continue
            rank += 1
            show_id = item.get("id") or name
            url = (item.get("external_urls") or {}).get("spotify")
            rows.append({
                "entity_type": "spotify_show",
                "entity_id": show_id,
                "entity_label": item.get("name"),
                "observed_at_utc": now,
                "metric": "chart_rank",
                "value_numeric": float(rank),
                "value_text": item.get("name"),
                "sample_window": "1w",
                "capture_url": url,
                "canonical_url": url,
                "raw_payload_json": item,
                "dedup_key": self.make_dedup_key(self.source_id, show_id, "chart_rank", now, "day"),
            })
        return rows


def _utcnow_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["SpotifyChartsAdapter"]
