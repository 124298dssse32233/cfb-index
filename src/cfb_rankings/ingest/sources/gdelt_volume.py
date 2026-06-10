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
    adapter_version = "0.5.0"
    # GDELT DOC 2.0 enforces ~1 request / 5s, so an all-138 sweep is an ~11.5-min
    # floor before any 429. We no longer cap teams or fight backoff: instead we
    # ROTATE via collection_ledger (stalest-due slice each run) inside a hard
    # wall-clock BUDGET, so every team is covered over a rolling window and a run
    # can never grind for hours. (Replaced the v0.4 Tier-1+2 cap + circuit breaker;
    # see docs/pipeline_cadence_architecture_2026-06.md.) GDELT is a decoupled,
    # best-effort cross-check — per-team Google News (collected for all 138) is the
    # primary news-volume signal.
    min_seconds_between_requests = 5.0
    backoff_seconds = 15.0
    max_attempts = 2
    default_timespan = "7d"
    # Rotation: ~46 teams/run x 72h interval => all 138 covered every ~3 days.
    rotation_batch = 46
    rotation_interval_hours = 72.0
    budget_seconds = 480.0  # 8-min hard wall-clock box per run

    def fetch(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        from cfb_rankings.ingest.collection_ledger import Budget, mark_fail, mark_ok, select_batch

        teams = self.db.query_all(
            "select team_id, google_news_query from priority_teams "
            "where google_news_query is not null"
        )
        by_id = {str(t["team_id"]): t for t in teams}
        batch = select_batch(
            self.db, self.source_id, list(by_id.keys()),
            budget=int(os.environ.get("GDELT_BATCH", str(self.rotation_batch))),
        )
        timespan = os.environ.get("GDELT_TIMESPAN", self.default_timespan)
        clock = Budget(float(os.environ.get("GDELT_BUDGET_SECONDS", str(self.budget_seconds))))
        out: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for tid in batch:
            if clock.expired():
                logger.info("gdelt: wall-clock budget reached; deferring %d teams to next run",
                            len(batch) - len(out))
                break
            t = by_id[tid]
            url = _DOC_URL.format(query=urllib.parse.quote(t["google_news_query"]), timespan=timespan)
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("gdelt fetch failed for team %s: %s", tid, exc)
                mark_fail(self.db, self.source_id, tid)
                continue
            mark_ok(self.db, self.source_id, tid, interval_hours=self.rotation_interval_hours)
            out.append((t, data))
        logger.info("gdelt: collected %d/%d batch teams (rotation over all %d)",
                    len(out), len(batch), len(by_id))
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
