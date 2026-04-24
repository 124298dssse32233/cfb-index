"""Statistical Mirror Match — "closest historical fingerprint" (S2.5).

Spec: ``docs/specs/signature_bets/mirror_match_spec.md``. Builds
percentile-normalized feature vectors per position, cosine-similarity-
ranks every same-position player against each target, and caches the
top-k to ``player_mirror_matches``.

Today's DB coverage (passing 2024–2025, rushing/receiving 2025) means
most targets will return zero matches above the 75 floor. The
infrastructure lights up with a historical backfill.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from cfb_rankings.db import Database


MIN_SIMILARITY_PCT = 75
MIN_DOMINANT_SAMPLE = 150
MIN_COVERAGE_PCT = 50

# Feature sets per position — (feature_id, category, stat_type, dominant).
# `dominant=True` means this feature carries the min-sample guardrail
# (MIN_DOMINANT_SAMPLE).
_POSITION_FEATURES: dict[str, list[tuple[str, str, str, bool]]] = {
    "QB": [
        ("passing_yds",    "passing", "YDS", True),
        ("passing_tds",    "passing", "TD",  False),
        ("passing_pct",    "passing", "PCT", False),
        ("passing_ypa",    "passing", "YPA", False),
        ("rushing_yds_qb", "rushing", "YDS", False),
        ("rushing_ypc_qb", "rushing", "YPC", False),
    ],
    "RB": [
        ("rushing_yds",    "rushing",   "YDS", True),
        ("rushing_ypc",    "rushing",   "YPC", False),
        ("rushing_tds",    "rushing",   "TD",  False),
        ("receiving_yds",  "receiving", "YDS", False),
        ("receiving_ypr",  "receiving", "YPR", False),
    ],
    "WR": [
        ("receiving_yds",  "receiving", "YDS", True),
        ("receiving_ypr",  "receiving", "YPR", False),
        ("receiving_tds",  "receiving", "TD",  False),
        ("receiving_rec",  "receiving", "REC", False),
    ],
}


@dataclass(frozen=True)
class MirrorMatch:
    match_player_id: int
    match_player_name: str
    match_team_name: str | None
    match_season: int
    similarity_pct: int
    coverage_pct: int
    drivers: list[dict[str, Any]]


def _fetch_player_stat_map(
    db: Database, season: int, position: str
) -> dict[int, dict[str, tuple[float, int]]]:
    """Return {player_id: {(category,stat_type): (value, sample_proxy)}}
    for every player of ``position`` in ``season``.

    The sample_proxy is the player's ATT / CAR / REC on the feature's
    category where that's the natural volume anchor; otherwise None.
    """
    rows = db.query_all(
        "SELECT player_id, category, stat_type, stat_value_num "
        "FROM player_season_stats "
        "WHERE season_year = :s AND position = :p "
        "  AND stat_value_num IS NOT NULL",
        {"s": season, "p": position},
    )
    out: dict[int, dict[str, tuple[float, int]]] = {}
    for r in rows:
        pid = int(r["player_id"])
        key = f"{r['category']}|{r['stat_type']}"
        out.setdefault(pid, {})[key] = (float(r["stat_value_num"]), 0)
    # Sample-size proxy: attempts (QB), carries (RB), receptions (WR).
    proxy_rows = db.query_all(
        "SELECT player_id, category, stat_type, stat_value_num "
        "FROM player_season_stats "
        "WHERE season_year = :s AND position = :p "
        "  AND stat_type IN ('ATT','CAR','REC')",
        {"s": season, "p": position},
    )
    for r in proxy_rows:
        pid = int(r["player_id"])
        key = f"{r['category']}|{r['stat_type']}"
        if pid in out and key in out[pid]:
            v = out[pid][key][0]
            out[pid][key] = (v, int(v))
    return out


def _build_percentile_map(
    stat_map: dict[int, dict[str, tuple[float, int]]],
    key: str,
) -> dict[int, float]:
    """Rank players by a specific (category|stat_type) key, return 0..100."""
    values = [
        (pid, vs.get(key, (None, 0))[0]) for pid, vs in stat_map.items()
    ]
    present = [(pid, v) for pid, v in values if v is not None]
    if not present:
        return {}
    present.sort(key=lambda pv: pv[1], reverse=True)
    n = len(present)
    out: dict[int, float] = {}
    for idx, (pid, _v) in enumerate(present):
        # Best → 100; worst → 100/N.
        out[pid] = round((1.0 - idx / max(n, 1)) * 100.0, 2)
    return out


def _build_feature_vectors(
    db: Database, season: int, position: str
) -> tuple[dict[int, list[float]], dict[int, list[bool]], dict[int, int]]:
    """Return (vectors, present_mask, dominant_sample_by_player).

    vectors: {player_id: [percentile_or_50]}
    present_mask: {player_id: [bool per feature — True when not median-filled]}
    """
    features = _POSITION_FEATURES.get(position) or []
    if not features:
        return {}, {}, {}
    stat_map = _fetch_player_stat_map(db, season, position)

    # Per-feature percentile maps
    feat_keys = [f"{cat}|{stat}" for (_f, cat, stat, _d) in features]
    pct_maps = {k: _build_percentile_map(stat_map, k) for k in feat_keys}

    dominant_sample: dict[int, int] = {}
    for pid, vs in stat_map.items():
        for (_fid, cat, _stat, dominant) in features:
            if not dominant:
                continue
            vkey_att = f"{cat}|ATT"
            vkey_car = f"{cat}|CAR"
            vkey_rec = f"{cat}|REC"
            sample = 0
            for k in (vkey_att, vkey_car, vkey_rec):
                if k in vs and vs[k][1] > sample:
                    sample = vs[k][1]
            dominant_sample[pid] = sample
            break

    vectors: dict[int, list[float]] = {}
    mask: dict[int, list[bool]] = {}
    for pid in stat_map.keys():
        vec = []
        pres = []
        for k in feat_keys:
            v = pct_maps.get(k, {}).get(pid)
            if v is None:
                vec.append(50.0)
                pres.append(False)
            else:
                vec.append(float(v))
                pres.append(True)
        vectors[pid] = vec
        mask[pid] = pres
    return vectors, mask, dominant_sample


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def _similarity_pct(a: list[float], b: list[float]) -> int:
    sim = _cosine(a, b)
    return int(round(max(0.0, sim) * 100.0))


def _coverage_pct(mask_self: list[bool], mask_other: list[bool]) -> int:
    total = len(mask_self)
    both = sum(1 for s, o in zip(mask_self, mask_other) if s and o)
    return int(round(both / max(total, 1) * 100.0))


def _player_display(db: Database, player_id: int, season: int) -> tuple[str, str | None]:
    row = db.query_one(
        "SELECT p.full_name AS name, pss.team_name AS team "
        "FROM players p "
        "LEFT JOIN player_season_stats pss "
        "  ON pss.player_id = p.player_id AND pss.season_year = :s "
        "WHERE p.player_id = :pid "
        "LIMIT 1",
        {"pid": player_id, "s": season},
    )
    if not row:
        return (f"Player {player_id}", None)
    return (str(row.get("name") or f"Player {player_id}"), row.get("team"))


def find_mirror_matches(
    db: Database, player_id: int, season: int, *, k: int = 10
) -> list[MirrorMatch]:
    """Return the top-k mirror matches above MIN_SIMILARITY_PCT."""
    row = db.query_one(
        "SELECT position FROM players WHERE player_id = :pid",
        {"pid": player_id},
    )
    position = str((row or {}).get("position") or "").strip().upper()
    if position not in _POSITION_FEATURES:
        return []

    # Pool = same position across every available season. The DB doesn't
    # carry 15-year history today; pool is naturally small.
    season_rows = db.query_all(
        "SELECT DISTINCT season_year FROM player_season_stats "
        "WHERE position = :p AND season_year <= :s",
        {"p": position, "s": season},
    )
    seasons = sorted({int(r["season_year"]) for r in season_rows})
    if not seasons:
        return []

    # Target's vector (this season).
    vecs_self, mask_self, samples_self = _build_feature_vectors(
        db, season, position
    )
    if player_id not in vecs_self:
        return []
    self_vec = vecs_self[player_id]
    self_mask = mask_self[player_id]

    features = _POSITION_FEATURES[position]
    feat_ids = [f for (f, _c, _s, _d) in features]

    candidates: list[MirrorMatch] = []
    for match_season in seasons:
        vecs_pool, mask_pool, samples_pool = _build_feature_vectors(
            db, match_season, position
        )
        for pid, vec in vecs_pool.items():
            if pid == player_id and match_season == season:
                continue
            if samples_pool.get(pid, 0) < MIN_DOMINANT_SAMPLE:
                continue
            cov = _coverage_pct(self_mask, mask_pool[pid])
            if cov < MIN_COVERAGE_PCT:
                continue
            sim = _similarity_pct(self_vec, vec)
            if sim < MIN_SIMILARITY_PCT:
                continue
            drivers = [
                {
                    "feature": feat_ids[i],
                    "self_pct": round(self_vec[i], 1),
                    "match_pct": round(vec[i], 1),
                    "delta": round(self_vec[i] - vec[i], 1),
                }
                for i in range(len(self_vec))
            ]
            drivers.sort(key=lambda d: abs(d["delta"]))
            name, team = _player_display(db, pid, match_season)
            candidates.append(
                MirrorMatch(
                    match_player_id=pid,
                    match_player_name=name,
                    match_team_name=team,
                    match_season=match_season,
                    similarity_pct=sim,
                    coverage_pct=cov,
                    drivers=drivers[:5],
                )
            )

    candidates.sort(key=lambda m: (-m.similarity_pct, -m.coverage_pct))
    return candidates[:k]


def store_matches(
    db: Database, player_id: int, season: int, matches: list[MirrorMatch]
) -> None:
    db.execute(
        "DELETE FROM player_mirror_matches "
        "WHERE player_id = :pid AND season_year = :s",
        {"pid": player_id, "s": season},
    )
    for slot, m in enumerate(matches, start=1):
        db.execute(
            "INSERT INTO player_mirror_matches "
            "(player_id, season_year, match_slot, match_player_id, "
            " match_season_year, similarity_pct, feature_coverage_pct, "
            " drivers_json) "
            "VALUES (:pid, :s, :slot, :mpid, :ms, :sim, :cov, :dj)",
            {
                "pid": player_id,
                "s": season,
                "slot": slot,
                "mpid": m.match_player_id,
                "ms": m.match_season,
                "sim": m.similarity_pct,
                "cov": m.coverage_pct,
                "dj": json.dumps(m.drivers, separators=(",", ":")),
            },
        )


def compute_mirror_matches(
    db: Database, season: int, *, k: int = 10
) -> int:
    """Populate player_mirror_matches for every candidate player."""
    rows = db.query_all(
        "SELECT DISTINCT player_id FROM player_season_stats "
        "WHERE season_year = :s",
        {"s": season},
    )
    n = 0
    for r in rows:
        pid = int(r["player_id"])
        matches = find_mirror_matches(db, pid, season, k=k)
        if matches:
            store_matches(db, pid, season, matches)
            n += 1
    return n


def fetch_cached_matches(
    db: Database, player_id: int, season: int, *, k: int = 10
) -> list[MirrorMatch]:
    rows = db.query_all(
        "SELECT match_slot, match_player_id, match_season_year, "
        "       similarity_pct, feature_coverage_pct, drivers_json "
        "FROM player_mirror_matches "
        "WHERE player_id = :pid AND season_year = :s "
        "ORDER BY match_slot ASC LIMIT :k",
        {"pid": player_id, "s": season, "k": int(k)},
    )
    if not rows:
        return []
    out: list[MirrorMatch] = []
    for r in rows:
        name, team = _player_display(
            db, int(r["match_player_id"]), int(r["match_season_year"])
        )
        try:
            drivers = json.loads(r["drivers_json"]) if r.get("drivers_json") else []
        except (TypeError, ValueError):
            drivers = []
        out.append(
            MirrorMatch(
                match_player_id=int(r["match_player_id"]),
                match_player_name=name,
                match_team_name=team,
                match_season=int(r["match_season_year"]),
                similarity_pct=int(r["similarity_pct"]),
                coverage_pct=int(r["feature_coverage_pct"]),
                drivers=drivers,
            )
        )
    return out
