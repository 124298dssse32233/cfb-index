"""Achievements — detectors + rarity pipeline (Signature Bets S2.7).

Spec: ``docs/specs/signature_bets/achievements_spec.md``. Seed:
``seeds/achievement_catalog.yaml``. Each achievement has a detector
function below; ``compute_achievements(db, season)`` runs them all and
writes unlocks + recomputed rarity to ``player_achievements``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML required") from exc

from cfb_rankings.db import Database


_CATALOG_PATH = (
    Path(__file__).resolve().parents[3] / "seeds" / "achievement_catalog.yaml"
)


@dataclass(frozen=True)
class Unlock:
    player_id: int
    achievement_id: str
    season_year: int
    unlock_context: str
    meta: dict[str, Any]


@lru_cache(maxsize=1)
def _load_catalog() -> list[dict[str, Any]]:
    data = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8")) or {}
    out: list[dict[str, Any]] = []
    for row in (data.get("achievements") or []):
        if not isinstance(row, dict) or not row.get("id"):
            continue
        out.append(
            {
                "id": str(row["id"]),
                "display_name": str(row.get("display_name") or row["id"]),
                "icon_slug": str(row.get("icon_slug") or "generic"),
                "description": str(row.get("description") or ""),
                "target_rarity": float(row.get("target_rarity") or 0.1),
                "position_filter": row.get("position_filter"),
                "detector": str(row.get("detector") or ""),
            }
        )
    return out


# -------------------------- Detectors -------------------------- #

def _detect_dual_threat(db: Database, season: int) -> list[Unlock]:
    """Top-50 in both WEPA passing-per-dropback and WEPA rushing-per-carry."""
    rows = db.query_all(
        "SELECT player_id, metric_name, metric_value "
        "FROM player_value_metrics "
        "WHERE season_year = :s "
        "  AND metric_name IN ('wepa_passing_per_dropback','wepa_rushing_per_carry')",
        {"s": season},
    )
    by_player: dict[int, dict[str, float]] = {}
    for r in rows:
        pid = int(r["player_id"])
        by_player.setdefault(pid, {})[r["metric_name"]] = float(r["metric_value"] or 0)
    # Rank ranking each metric; require top-50 in both.
    def rank_map(key: str) -> dict[int, int]:
        ranked = sorted(
            [(pid, vs[key]) for pid, vs in by_player.items() if key in vs],
            key=lambda x: x[1], reverse=True,
        )
        return {pid: idx + 1 for idx, (pid, _v) in enumerate(ranked)}

    pass_rank = rank_map("wepa_passing_per_dropback")
    rush_rank = rank_map("wepa_rushing_per_carry")
    out: list[Unlock] = []
    for pid in by_player.keys():
        pr = pass_rank.get(pid)
        rr = rush_rank.get(pid)
        if pr and rr and pr <= 50 and rr <= 50:
            out.append(
                Unlock(
                    player_id=pid,
                    achievement_id="achievement_dual_threat",
                    season_year=season,
                    unlock_context=(
                        f"#{pr} WEPA pass/drop + #{rr} WEPA rush/carry among qualifiers."
                    ),
                    meta={"pass_rank": pr, "rush_rank": rr},
                )
            )
    return out


def _detect_money_efficiency(db: Database, season: int) -> list[Unlock]:
    """Top-5 YPA among P4 + Notre Dame QBs (min 150 attempts)."""
    rows = db.query_all(
        "SELECT player_id, category, stat_type, stat_value_num "
        "FROM player_season_stats "
        "WHERE season_year = :s AND position = 'QB' "
        "  AND category = 'passing' "
        "  AND stat_type IN ('YPA','ATT') "
        "  AND stat_value_num IS NOT NULL",
        {"s": season},
    )
    by_player: dict[int, dict[str, float]] = {}
    for r in rows:
        pid = int(r["player_id"])
        by_player.setdefault(pid, {})[r["stat_type"]] = float(r["stat_value_num"])
    qualified = [
        (pid, vs.get("YPA")) for pid, vs in by_player.items()
        if vs.get("YPA") is not None and (vs.get("ATT") or 0) >= 150
    ]
    qualified.sort(key=lambda x: x[1], reverse=True)
    out: list[Unlock] = []
    for rank, (pid, ypa) in enumerate(qualified[:5], start=1):
        out.append(
            Unlock(
                player_id=pid,
                achievement_id="achievement_money_efficiency",
                season_year=season,
                unlock_context=f"#{rank} YPA at {ypa:.2f} among qualified QBs.",
                meta={"rank": rank, "ypa": ypa},
            )
        )
    return out


def _detect_program_benchmark(db: Database, season: int) -> list[Unlock]:
    """Season leader at position within the program for a headline metric."""
    unlocks: list[Unlock] = []
    # (stat_type_pattern, label)
    leaders: list[tuple[str, str, str]] = [
        ("passing", "YDS", "passing yards"),
        ("rushing", "YDS", "rushing yards"),
        ("receiving", "YDS", "receiving yards"),
    ]
    # Minimum meaningful volume so we don't badge "team leader with 5 yards".
    floors = {"passing": 500.0, "rushing": 300.0, "receiving": 300.0}
    for category, stat_type, label in leaders:
        floor = floors.get(category, 0.0)
        rows = db.query_all(
            "SELECT player_id, team_id, position, stat_value_num "
            "FROM player_season_stats "
            "WHERE season_year = :s AND category = :cat AND stat_type = :st "
            "  AND stat_value_num IS NOT NULL AND team_id IS NOT NULL "
            "  AND stat_value_num >= :floor "
            "ORDER BY team_id, stat_value_num DESC",
            {"s": season, "cat": category, "st": stat_type, "floor": floor},
        )
        seen: set[tuple[int, str]] = set()
        for r in rows:
            key = (int(r["team_id"]), str(r.get("position") or ""))
            if key in seen:
                continue
            seen.add(key)
            unlocks.append(
                Unlock(
                    player_id=int(r["player_id"]),
                    achievement_id="achievement_program_benchmark",
                    season_year=season,
                    unlock_context=f"Team leader in {label} ({int(float(r['stat_value_num']))}).",
                    meta={
                        "team_id": int(r["team_id"]),
                        "position": r["position"],
                        "metric": label,
                    },
                )
            )
    return unlocks


def _detect_mirror_elite(db: Database, season: int) -> list[Unlock]:
    """Top mirror-match >= 95% AND that match carries a Heisman / AA honor."""
    rows = db.query_all(
        "SELECT player_id, match_player_id, match_season_year, similarity_pct "
        "FROM player_mirror_matches "
        "WHERE season_year = :s AND match_slot = 1 AND similarity_pct >= 95",
        {"s": season},
    )
    out: list[Unlock] = []
    for r in rows:
        honor_row = db.query_one(
            "SELECT honor_name FROM player_honors "
            "WHERE player_id = :pid "
            "  AND (LOWER(honor_name) LIKE '%heisman%' "
            "       OR LOWER(honor_name) LIKE '%all-american%' "
            "       OR LOWER(honor_name) LIKE '%finalist%') "
            "LIMIT 1",
            {"pid": int(r["match_player_id"])},
        )
        if not honor_row:
            continue
        out.append(
            Unlock(
                player_id=int(r["player_id"]),
                achievement_id="achievement_mirror_elite",
                season_year=season,
                unlock_context=(
                    f"{int(r['similarity_pct'])}% similar to an honored "
                    f"{int(r['match_season_year'])} player."
                ),
                meta={
                    "match_player_id": int(r["match_player_id"]),
                    "match_season": int(r["match_season_year"]),
                    "similarity_pct": int(r["similarity_pct"]),
                    "match_honor": str(honor_row["honor_name"]),
                },
            )
        )
    return out


_VOLUME_THRESHOLDS: dict[str, tuple[str, str, float]] = {
    "QB": ("passing", "YDS", 2500.0),
    "RB": ("rushing", "YDS", 1200.0),
    "WR": ("receiving", "YDS", 900.0),
    "TE": ("receiving", "YDS", 900.0),
}


def _detect_volume_king(db: Database, season: int) -> list[Unlock]:
    out: list[Unlock] = []
    for pos, (cat, stat, threshold) in _VOLUME_THRESHOLDS.items():
        rows = db.query_all(
            "SELECT player_id, stat_value_num "
            "FROM player_season_stats "
            "WHERE season_year = :s AND position = :p "
            "  AND category = :c AND stat_type = :st "
            "  AND stat_value_num >= :thr",
            {"s": season, "p": pos, "c": cat, "st": stat, "thr": threshold},
        )
        for r in rows:
            out.append(
                Unlock(
                    player_id=int(r["player_id"]),
                    achievement_id="achievement_volume_king",
                    season_year=season,
                    unlock_context=(
                        f"{int(float(r['stat_value_num']))} {cat} yards — "
                        f"clears the {int(threshold):,}-{pos} volume bar."
                    ),
                    meta={"position": pos, "metric": f"{cat}_yds", "value": float(r["stat_value_num"])},
                )
            )
    return out


def _detect_honors_badge(db: Database, season: int) -> list[Unlock]:
    rows = db.query_all(
        "SELECT player_id, honor_name, season_year "
        "FROM player_honors "
        "WHERE season_year = :s "
        "  AND (LOWER(honor_name) LIKE '%heisman%' "
        "    OR LOWER(honor_name) LIKE '%all-american%' "
        "    OR LOWER(honor_name) LIKE '%all-america%' "
        "    OR LOWER(honor_name) LIKE '%davey%' "
        "    OR LOWER(honor_name) LIKE '%maxwell%' "
        "    OR LOWER(honor_name) LIKE '%camp%' "
        "    OR LOWER(honor_name) LIKE '%nagurski%' "
        "    OR LOWER(honor_name) LIKE '%biletnikoff%')",
        {"s": season},
    )
    seen: set[int] = set()
    out: list[Unlock] = []
    for r in rows:
        pid = int(r["player_id"])
        if pid in seen:
            continue
        seen.add(pid)
        out.append(
            Unlock(
                player_id=pid,
                achievement_id="achievement_honors_badge",
                season_year=season,
                unlock_context=f"Recognized on: {r['honor_name']}.",
                meta={"honor": str(r["honor_name"])},
            )
        )
    return out


_DETECTORS: dict[str, Callable[[Database, int], list[Unlock]]] = {
    "dual_threat":       _detect_dual_threat,
    "money_efficiency":  _detect_money_efficiency,
    "program_benchmark": _detect_program_benchmark,
    "mirror_elite":      _detect_mirror_elite,
    "volume_king":       _detect_volume_king,
    "honors_badge":      _detect_honors_badge,
}


# -------------------------- Pipeline --------------------------- #

def _upsert_catalog(db: Database) -> None:
    for row in _load_catalog():
        db.execute(
            "INSERT INTO achievement_catalog "
            "(achievement_id, display_name, icon_slug, description, "
            " target_rarity, position_filter, is_active) "
            "VALUES (:id, :dn, :ic, :d, :tr, :pf, 1) "
            "ON CONFLICT(achievement_id) DO UPDATE SET "
            "  display_name=excluded.display_name, "
            "  icon_slug=excluded.icon_slug, "
            "  description=excluded.description, "
            "  target_rarity=excluded.target_rarity, "
            "  position_filter=excluded.position_filter, "
            "  is_active=excluded.is_active",
            {
                "id": row["id"],
                "dn": row["display_name"],
                "ic": row["icon_slug"],
                "d": row["description"],
                "tr": float(row["target_rarity"]),
                "pf": row["position_filter"],
            },
        )


def compute_achievements(db: Database, season: int) -> int:
    """Run every active detector + upsert unlocks + recompute rarity.

    Returns the total count of unlocks written across all achievements.
    """
    _upsert_catalog(db)
    # Reset season slice so drops/thresholds-tightenings propagate.
    db.execute(
        "DELETE FROM player_achievements WHERE season_year = :s",
        {"s": season},
    )
    total = 0
    catalog = _load_catalog()
    cohort_sizes: dict[str, int] = {}
    for row in catalog:
        fn = _DETECTORS.get(row["detector"])
        if fn is None:
            continue
        unlocks = fn(db, season)
        for u in unlocks:
            db.execute(
                "INSERT INTO player_achievements "
                "(player_id, achievement_id, season_year, unlock_context, meta_json) "
                "VALUES (:pid, :aid, :s, :ctx, :mj) "
                "ON CONFLICT(player_id, achievement_id, season_year) DO UPDATE SET "
                "  unlock_context=excluded.unlock_context, meta_json=excluded.meta_json",
                {
                    "pid": u.player_id,
                    "aid": u.achievement_id,
                    "s": u.season_year,
                    "ctx": u.unlock_context,
                    "mj": json.dumps(u.meta, separators=(",", ":")),
                },
            )
            total += 1
        cohort_sizes[row["id"]] = len({u.player_id for u in unlocks})
    # Compute rarity relative to the league's eligible pool for this season.
    # Pool = distinct players with either value metrics or season stats; an
    # achievement that unlocks for N distinct players has rarity N/pool.
    qualified_row = db.query_one(
        "SELECT COUNT(DISTINCT player_id) AS n FROM ("
        "  SELECT player_id FROM player_value_metrics WHERE season_year = :s "
        "  UNION "
        "  SELECT player_id FROM player_season_stats WHERE season_year = :s "
        ")",
        {"s": season},
    )
    qualified = int((qualified_row or {}).get("n") or 0) or 1
    for aid, count in cohort_sizes.items():
        rarity = min(round(count / qualified * 100.0, 2), 100.0)
        db.execute(
            "UPDATE player_achievements SET rarity_pct = :r "
            "WHERE achievement_id = :aid AND season_year = :s",
            {"r": rarity, "aid": aid, "s": season},
        )
    return total


def fetch_player_achievements(
    db: Database, player_id: int, season: int
) -> list[dict[str, Any]]:
    rows = db.query_all(
        "SELECT pa.achievement_id, pa.unlock_context, pa.rarity_pct, pa.meta_json, "
        "       ac.display_name, ac.icon_slug, ac.description "
        "FROM player_achievements pa "
        "LEFT JOIN achievement_catalog ac ON ac.achievement_id = pa.achievement_id "
        "WHERE pa.player_id = :pid AND pa.season_year = :s "
        "ORDER BY pa.rarity_pct ASC NULLS LAST, pa.achievement_id ASC",
        {"pid": player_id, "s": season},
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            meta = json.loads(r["meta_json"]) if r.get("meta_json") else {}
        except (TypeError, ValueError):
            meta = {}
        out.append(
            {
                "achievement_id": r["achievement_id"],
                "display_name": r.get("display_name") or r["achievement_id"],
                "icon_slug": r.get("icon_slug") or "generic",
                "description": r.get("description") or "",
                "unlock_context": r.get("unlock_context") or "",
                "rarity_pct": r.get("rarity_pct"),
                "meta": meta,
            }
        )
    return out
