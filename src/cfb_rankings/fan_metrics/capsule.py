"""Fan-Intelligence Capsule — freeze a moment in CFB fandom to a durable artifact.

A capsule is a point-in-time snapshot of the four suite stats plus the slang of
the moment, sealed to a git-committed JSON under ``data/capsules/<label>.json``.
It is deliberately decoupled from the live DB: once sealed, the JSON is the
source of truth and the renderer reads it, so the capsule reproduces identically
forever — even after the DB is rebuilt and player_ids churn (the linkrot lesson).
That durability is the whole point of a *capsule*.

CLI:
    python manage.py seal-capsule --label 2026-06 [--title "Talking Season, Frozen"]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

CAPSULE_DIR = Path("data") / "capsules"


def _top_backometer(db: Database, season: int, limit: int = 6) -> list[dict[str, Any]]:
    from cfb_rankings.fan_metrics.backometer_render import latest_backometer_week, fetch_backometer_board
    latest = latest_backometer_week(db)
    if not latest:
        return []
    _, week = latest
    board = fetch_backometer_board(db, season, week)
    return [
        {"team": r["team_name"], "slug": r["team_slug"], "zone": r["zone"],
         "score": round(float(r["score"]), 1), "n": int(r["sample_size"])}
        for r in board["qualifying"][:limit]
    ]


def _top_rent_free(db: Database, limit: int = 6) -> list[dict[str, Any]]:
    from cfb_rankings.fan_metrics.rent_free import fetch_rent_free_pairs
    pairs = fetch_rent_free_pairs(db, limit=limit)
    return [
        {"rivalry": p["rivalry_name"], "rent_free": p["rent_free"]["name"],
         "obsessed": p["obsessed"]["name"], "ratio": p["ratio_label"],
         "dominant": p["obsessed_count"], "minor": p["rentfree_count"]}
        for p in pairs
    ]


def _aura_cuts(db: Database, season: int, limit: int = 6) -> dict[str, list[dict[str, Any]]]:
    from cfb_rankings.fan_metrics.aura_render import fetch_aura_board
    board = fetch_aura_board(db, season)

    def row(r: dict[str, Any]) -> dict[str, Any]:
        return {"player": r["full_name"], "pos": r["position"],
                "perception": round(float(r["perception_pctl"]), 0),
                "production": round(float(r["production_pctl"]), 0),
                "aura_tax": round(float(r["aura_tax"]), 0)}

    return {
        "most_aura": [row(r) for r in board["him_watch"][:limit]],
        "overhyped": [row(r) for r in board["overhyped"][:limit]],
        "underrated": [row(r) for r in board["underrated"][:limit]],
    }


def _top_delusion(db: Database, limit: int = 10) -> list[dict[str, Any]]:
    from cfb_rankings.fan_metrics.delusion_render import latest_delusion, fetch_delusion_board
    latest = latest_delusion(db)
    if not latest:
        return []
    season, week = latest
    board = fetch_delusion_board(db, season, week)
    return [
        {"team": r["team_name"], "verdict": r["verdict"],
         "belief": round(float(r["belief_score"]), 0), "market": round(float(r["market_pct"]), 1),
         "index": round(float(r["delusion_index"]), 0)}
        for r in board[:limit]
    ]


def _slang_of_the_moment(db: Database, days: int = 60, limit: int = 10) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select term_group, sum(doc_count) as docs
        from lexicon_term_daily
        where team_id is null and source_name = 'all'
          and as_of_date >= date('now', :win)
        group by term_group
        having docs > 0
        order by docs desc
        limit :lim
        """,
        {"win": f"-{int(days)} days", "lim": int(limit)},
    )
    return [{"term": r["term_group"], "docs": int(r["docs"])} for r in rows]


def seal_capsule(
    db: Database,
    *,
    label: str,
    title: str = "Talking Season, Frozen",
    sealed_on: str | None = None,
    season: int | None = None,
    out_dir: Path | str = CAPSULE_DIR,
) -> dict[str, Any]:
    """Gather the current suite state into a durable JSON artifact.

    ``sealed_on`` is an ISO date string (pass it in — the DB layer forbids
    Date.now()-style calls in some contexts; callers stamp it). When omitted,
    a SQLite ``date('now')`` is used.
    """
    if season is None:
        row = db.query_one("select max(season_year) as y from backometer_weekly")
        season = int(row["y"]) if row and row.get("y") is not None else 2025
    if sealed_on is None:
        row = db.query_one("select date('now') as d")
        sealed_on = str(row["d"]) if row else label

    capsule = {
        "label": label,
        "title": title,
        "sealed_on": sealed_on,
        "season": season,
        "backometer": _top_backometer(db, season),
        "rent_free": _top_rent_free(db),
        "aura": _aura_cuts(db, season),
        "delusion": _top_delusion(db),
        "slang": _slang_of_the_moment(db),
    }

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{label}.json"
    path.write_text(json.dumps(capsule, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("seal-capsule: wrote %s", path)
    return {"path": str(path), "label": label,
            "sections": sum(1 for k in ("backometer", "rent_free", "delusion", "slang") if capsule[k])}


def load_capsules(capsule_dir: Path | str = CAPSULE_DIR) -> list[dict[str, Any]]:
    """Load every sealed capsule JSON (newest label first)."""
    d = Path(capsule_dir)
    if not d.exists():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.json"), reverse=True):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return out


__all__ = ["seal_capsule", "load_capsules", "CAPSULE_DIR"]
