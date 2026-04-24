"""GDELT volume adapter — TASK 2.7.

GDELT's free DOC 2.0 API exposes article counts per query per day. We pull
article volume for each ``priority_teams.google_news_query`` (or the team
name fallback) and store as source_observations. Tone is Tier C and lives in
``gdelt_tone`` (a separate, weekly adapter — TODO).

API: https://api.gdeltproject.org/api/v2/doc/doc?query=...&mode=TimelineVol&FORMAT=JSON
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.numeric_base import NumericSourceAdapter

logger = logging.getLogger(__name__)

_DOC_URL = (
    "https://api.gdeltproject.org/api/v2/doc/doc?"
    "query={query}&mode=TimelineVol&timespan={timespan}&FORMAT=JSON"
)


class GdeltVolumeAdapter(NumericSourceAdapter):
    source_id = "gdelt_volume"
    adapter_version = "0.2.0"
    min_seconds_between_requests = 1.5  # GDELT throttles aggressively
    # GDELT caps timespan at 2y. Normal hourly cron uses 7d; historical
    # backfill can set GDELT_TIMESPAN=2y via env for a one-shot pull.
    default_timespan = "7d"

    def fetch(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        teams = self.db.query_all(
            "select team_id, google_news_query from priority_teams "
            "where google_news_query is not null"
        )
        timespan = os.environ.get("GDELT_TIMESPAN", self.default_timespan)
        out: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for t in teams:
            q = urllib.parse.quote(t["google_news_query"])
            url = _DOC_URL.format(query=q, timespan=timespan)
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("gdelt fetch failed for team %s: %s", t["team_id"], exc)
                continue
            out.append((t, data))
        return out

    def parse(self, raw: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for team, data in raw:
            timeline = data.get("timeline") or []
            # GDELT TimelineVol returns one series with .data = [{date, value}]
            if not timeline:
                continue
            points = timeline[0].get("data") or []
            for p in points:
                date_str = p.get("date") or ""
                if len(date_str) < 8:
                    continue
                iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}T00:00:00Z"
                rows.append({
                    "entity_type": "team_query",
                    "entity_id": str(team["team_id"]),
                    "entity_label": team["google_news_query"],
                    "observed_at_utc": iso,
                    "metric": "article_count",
                    "value_numeric": float(p.get("value", 0)),
                    "sample_window": "1d",
                    "capture_url": "https://api.gdeltproject.org/api/v2/doc/doc",
                    "raw_payload_json": p,
                })
        return rows


__all__ = ["GdeltVolumeAdapter"]
