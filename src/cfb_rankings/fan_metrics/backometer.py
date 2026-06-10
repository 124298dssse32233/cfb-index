"""The Backometer — weekly fanbase belief on a 0-100 scale with named zones.

Reuses the Pulse belief composite (``fan_intelligence._belief_from_row``,
-100..+100) weighted across a team-week's conversation feature rows, rescaled
to 0..100 the same way ``_reality_gap`` does. On top of the raw score this adds
the product layer from docs/design-system/40-noir-subbrand.md:

- named zones (words live in seeds/noir_zone_labels.yaml — copy, not code)
- hysteresis: the published zone changes only when the score clears the new
  zone's boundary by >= HYSTERESIS_PTS, or the raw zone holds for 2 straight
  weeks — no flip-flopping screenshots at a 79/80 boundary
- publication floor: weeks under MIN_SAMPLE mentions are flagged low-signal;
  the score is still stored (history stays continuous) but renderers must
  show the LOW SIGNAL state, never a confident verdict on n=12

CLI:
    python manage.py compute-backometer --season YYYY [--weeks 22 23 41]
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from cfb_rankings.common.week import resolve_week
from cfb_rankings.db import Database
from cfb_rankings.fan_intelligence import _belief_from_row

logger = logging.getLogger(__name__)

DEFAULT_ZONE_LABELS_FILE = Path("seeds") / "noir_zone_labels.yaml"

# Architecture (stable): zone id -> inclusive lower bound on the 0-100 scale.
ZONE_BOUNDS: list[tuple[str, float]] = [
    ("so_back", 80.0),
    ("cooking", 60.0),
    ("uneasy", 40.0),
    ("cooked", 20.0),
    ("so_over", 0.0),
]
HYSTERESIS_PTS = 3.0
MIN_SAMPLE = 200

_DEFAULT_LABELS = {
    "so_back": "SO BACK",
    "cooking": "COOKING",
    "uneasy": "UNEASY",
    "cooked": "COOKED",
    "so_over": "IT'S SO OVER",
}


def load_zone_labels(path: Path | str = DEFAULT_ZONE_LABELS_FILE) -> dict[str, str]:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        labels = {str(k): str(v) for k, v in (raw.get("zones") or {}).items()}
        return {**_DEFAULT_LABELS, **labels}
    except FileNotFoundError:
        return dict(_DEFAULT_LABELS)


def zone_for_score(score: float) -> str:
    for zone_id, lower in ZONE_BOUNDS:
        if score >= lower:
            return zone_id
    return "so_over"


def _zone_boundary(zone_id: str) -> float:
    for zid, lower in ZONE_BOUNDS:
        if zid == zone_id:
            return lower
    return 0.0


def _sticky_zone(
    score: float,
    raw_zone: str,
    prev_zone: str | None,
    prev_raw_zone: str | None,
) -> str:
    """Hysteresis: keep the previous published zone on shallow crossings."""
    if prev_zone is None or raw_zone == prev_zone:
        return raw_zone
    # The raw zone held for two consecutive weeks -> let it through.
    if prev_raw_zone == raw_zone:
        return raw_zone
    # Distance past the boundary between prev_zone and raw_zone must clear
    # HYSTERESIS_PTS. Moving up crosses raw_zone's lower bound; moving down
    # falls under prev_zone's lower bound.
    if score >= _zone_boundary(prev_zone):
        boundary = _zone_boundary(raw_zone)
        cleared = score - boundary
    else:
        boundary = _zone_boundary(prev_zone)
        cleared = boundary - score
    return raw_zone if cleared >= HYSTERESIS_PTS else prev_zone


def _monday_for_week(season_year: int, week: int) -> str:
    """Reverse-resolve (season, week) -> Monday via the canonical resolver."""
    probe = date.today()
    probe -= timedelta(days=probe.weekday())  # this week's Monday
    for _ in range(170):  # ~3.25 years of Mondays
        wk = resolve_week(probe)
        if wk.season_year == season_year and wk.week == week:
            return probe.strftime("%Y-%m-%d")
        probe -= timedelta(days=7)
    return ""


def compute_backometer(
    db: Database,
    *,
    season: int,
    weeks: list[int] | None = None,
) -> dict[str, int]:
    """Compute backometer_weekly for a season (optionally limited to weeks)."""
    params: dict[str, Any] = {"season": season}
    week_clause = ""
    if weeks:
        placeholders = ",".join(f":w_{i}" for i in range(len(weeks)))
        params.update({f"w_{i}": int(w) for i, w in enumerate(weeks)})
        week_clause = f"and week in ({placeholders})"

    rows = db.query_all(
        f"""
        select *
        from team_week_conversation_features
        where season_year = :season
          and audience_bucket in ('fan', 'unknown', 'national')
          {week_clause}
        """,
        params,
    )
    if not rows:
        return {"team_weeks": 0, "low_signal": 0}

    by_team_week: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_team_week[(int(row["team_id"]), int(row["week"]))].append(row)

    # Walk weeks in order so hysteresis sees each team's prior published zone.
    prior = {
        (int(r["team_id"])): r
        for r in db.query_all(
            """
            select team_id, week, score, zone, raw_zone
            from backometer_weekly
            where season_year = :season
            order by week
            """,
            {"season": season},
        )
    }
    prev_zone_by_team: dict[int, str] = {t: str(r["zone"]) for t, r in prior.items()}
    prev_raw_by_team: dict[int, str] = {t: str(r["raw_zone"]) for t, r in prior.items()}
    prev_score_by_team: dict[int, float] = {t: float(r["score"]) for t, r in prior.items()}

    monday_cache: dict[int, str] = {}
    out_rows: list[dict[str, Any]] = []
    low_signal = 0
    for (team_id, week) in sorted(by_team_week, key=lambda key: (key[1], key[0])):
        feature_rows = by_team_week[(team_id, week)]
        total_mentions = sum(max(0, int(r.get("mention_count") or 0)) for r in feature_rows)
        weighted = 0.0
        for r in feature_rows:
            mentions = max(1, int(r.get("mention_count") or 0))
            belief = _belief_from_row(r)
            weighted += belief["score"] * mentions
        score_pm100 = weighted / max(1, sum(max(1, int(r.get("mention_count") or 0)) for r in feature_rows))
        score = round((score_pm100 + 100.0) / 2.0, 1)  # -100..100 -> 0..100

        raw_zone = zone_for_score(score)
        zone = _sticky_zone(
            score, raw_zone,
            prev_zone_by_team.get(team_id),
            prev_raw_by_team.get(team_id),
        )
        is_low = 1 if total_mentions < MIN_SAMPLE else 0
        low_signal += is_low

        if week not in monday_cache:
            monday_cache[week] = _monday_for_week(season, week)
        wk_meta = resolve_week(monday_cache[week]) if monday_cache[week] else None

        delta = None
        if team_id in prev_score_by_team:
            delta = round(score - prev_score_by_team[team_id], 1)

        out_rows.append(
            {
                "team_id": team_id,
                "season_year": season,
                "week": week,
                "week_start_date": monday_cache[week],
                "score": score,
                "zone": zone,
                "raw_zone": raw_zone,
                "delta_wow": delta,
                "sample_size": total_mentions,
                "source_count": len({str(r.get("source_name") or "") for r in feature_rows}),
                "is_low_signal": is_low,
                "is_offseason": 0 if (wk_meta and wk_meta.in_season) else 1,
                "components_json": json.dumps(
                    {
                        "belief_pm100": round(score_pm100, 2),
                        "buckets": sorted({str(r.get("audience_bucket") or "") for r in feature_rows}),
                        "min_sample": MIN_SAMPLE,
                    }
                ),
                "annotations_json": None,
            }
        )
        prev_zone_by_team[team_id] = zone
        prev_raw_by_team[team_id] = raw_zone
        prev_score_by_team[team_id] = score

    db.upsert_many(
        "backometer_weekly",
        out_rows,
        conflict_columns=["team_id", "season_year", "week"],
        update_columns=[
            "week_start_date", "score", "zone", "raw_zone", "delta_wow",
            "sample_size", "source_count", "is_low_signal", "is_offseason",
            "components_json",
        ],
    )
    logger.info(
        "compute-backometer: season=%d team_weeks=%d low_signal=%d",
        season, len(out_rows), low_signal,
    )
    return {"team_weeks": len(out_rows), "low_signal": low_signal}


__all__ = ["compute_backometer", "zone_for_score", "load_zone_labels", "MIN_SAMPLE"]
