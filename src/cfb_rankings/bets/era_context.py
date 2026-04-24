"""Era Context — "Best by a ND QB since …" hooks (Signature Bets S1.3).

Spec: ``docs/specs/signature_bets/era_context_spec.md``. This module
resolves one-line historical comparables for a (player, metric, season,
value) tuple against ``player_season_stats``.

Today's DB carries only 2024–2025 passing + 2025 rushing for most
programs, so the coverage gate (≥ 4 seasons) silently returns
``applicable=False`` for almost every call. The infrastructure is live
and the moment a historical backfill lands the Signature Story surfaces
start picking up era hooks with zero additional wiring.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from cfb_rankings.db import Database


# Minimum number of distinct prior seasons the cohort must carry at this
# stat_type before any "best since" claim can ship. Four seasons is the
# smallest window where a "since" phrasing reads honestly.
MIN_COHORT_SEASON_SPAN = 4

# Percentage gap-to-leader threshold for "Tied for best" phrasing. Values
# within 0.5% round to a tie; 10% keeps us from claiming rank-2 / rank-3
# territory when the leader is far ahead.
TIE_THRESHOLD_PCT = 0.005
TOP_BAND_GAP_PCT = 0.10

# Metric → (category, stat_type) mapping used to resolve the cohort
# query. Extended as new metric_ids are added; unmapped metrics return
# applicable=False.
_METRIC_STAT_MAP: dict[str, tuple[str, str, bool]] = {
    # metric_id : (category, stat_type, higher_is_better)
    # Canonical keys (spec form).
    "passing_yards": ("passing", "YDS", True),
    "passing_tds": ("passing", "TD", True),
    "passing_pct": ("passing", "PCT", True),
    "passing_ypa": ("passing", "YPA", True),
    "rushing_yards": ("rushing", "YDS", True),
    "rushing_tds": ("rushing", "TD", True),
    "rushing_ypc": ("rushing", "YPC", True),
    # Signature Story metric_ids (seeds/signature_story_metrics.yaml).
    "passing_yards_total": ("passing", "YDS", True),
    "completion_pct":      ("passing", "PCT", True),
    "ypa":                 ("passing", "YPA", True),
    "rushing_yards_total": ("rushing", "YDS", True),
    "ypc":                 ("rushing", "YPC", True),
    "receiving_yards_total": ("receiving", "YDS", True),
    "ypr":                   ("receiving", "YPR", True),
}


def _era_label(season: int) -> str:
    if season >= 2020:
        return "modern"
    if season >= 2010:
        return "analytics"
    if season >= 2006:
        return "BCS-era"
    return "pre-BCS"


@lru_cache(maxsize=None)
def _cohort_span(
    db_id: int,
    category: str,
    stat_type: str,
    position: str,
    team_id: int | None,
    conference_id: int | None,
    level_code: str | None,
) -> tuple[int, int] | None:
    """Return (min_season, max_season) available for the cohort, or None."""
    db = _Database_Registry.get(db_id)
    if db is None:
        return None
    clauses = [
        "category = :category",
        "stat_type = :stat_type",
        "position = :position",
        "stat_value_num IS NOT NULL",
    ]
    params: dict[str, Any] = {
        "category": category,
        "stat_type": stat_type,
        "position": position,
    }
    if team_id is not None:
        clauses.append("team_id = :team_id")
        params["team_id"] = team_id
    elif conference_id is not None:
        clauses.append(
            "team_id IN (SELECT team_id FROM teams WHERE current_conference_id = :conference_id)"
        )
        params["conference_id"] = conference_id
    elif level_code is not None:
        clauses.append(
            "team_id IN (SELECT team_id FROM teams WHERE level_code = :level_code)"
        )
        params["level_code"] = level_code
    sql = (
        "SELECT MIN(season_year) AS min_y, MAX(season_year) AS max_y, "
        "COUNT(DISTINCT season_year) AS spans "
        f"FROM player_season_stats WHERE {' AND '.join(clauses)}"
    )
    row = db.query_one(sql, params)
    if not row or row.get("spans") is None:
        return None
    if int(row["spans"]) < MIN_COHORT_SEASON_SPAN:
        return None
    return int(row["min_y"]), int(row["max_y"])


class _Database_Registry:
    """Tiny registry so the lru_cache key can stay hashable.

    We can't hash a Database object directly; we hash ``id(db)`` instead
    and look the instance back up here. Safe because build-site uses a
    single Database across the whole process.
    """
    _by_id: dict[int, Database] = {}

    @classmethod
    def register(cls, db: Database) -> int:
        cls._by_id[id(db)] = db
        return id(db)

    @classmethod
    def get(cls, db_id: int) -> Database | None:
        return cls._by_id.get(db_id)


def _query_prior_best(
    db: Database,
    *,
    category: str,
    stat_type: str,
    position: str,
    team_id: int | None,
    conference_id: int | None,
    level_code: str | None,
    exclude_player_id: int,
    current_value: float,
    higher_is_better: bool,
    current_season: int,
) -> dict[str, Any] | None:
    """Return the top prior holder row — distinct from current player."""
    clauses = [
        "pss.category = :category",
        "pss.stat_type = :stat_type",
        "pss.position = :position",
        "pss.stat_value_num IS NOT NULL",
        "pss.player_id != :exclude_id",
        "pss.season_year <= :current_season",
    ]
    params: dict[str, Any] = {
        "category": category,
        "stat_type": stat_type,
        "position": position,
        "exclude_id": exclude_player_id,
        "current_season": current_season,
    }
    if team_id is not None:
        clauses.append("pss.team_id = :team_id")
        params["team_id"] = team_id
    elif conference_id is not None:
        clauses.append(
            "pss.team_id IN (SELECT team_id FROM teams WHERE current_conference_id = :conference_id)"
        )
        params["conference_id"] = conference_id
    elif level_code is not None:
        clauses.append(
            "pss.team_id IN (SELECT team_id FROM teams WHERE level_code = :level_code)"
        )
        params["level_code"] = level_code
    order = "DESC" if higher_is_better else "ASC"
    sql = (
        "SELECT pss.player_id, pss.season_year, pss.team_id, pss.stat_value_num, "
        "       p.full_name AS predecessor_name "
        "FROM player_season_stats pss "
        "LEFT JOIN players p ON p.player_id = pss.player_id "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY pss.stat_value_num {order}, pss.season_year DESC "
        "LIMIT 1"
    )
    row = db.query_one(sql, params)
    if not row or row.get("predecessor_name") is None:
        return None
    return dict(row)


def _format_text(
    *,
    cohort_level: str,
    program_short: str | None,
    conference_short: str | None,
    level_label: str | None,
    position: str,
    predecessor_name: str,
    predecessor_season: int,
    rank: int,
    is_tie: bool,
    era_label: str,
    era_start_season: int,
) -> str:
    if cohort_level == "program":
        if is_tie:
            return (
                f"Tied for best by a {program_short} {position} with "
                f"{predecessor_name} {predecessor_season}."
            )
        return (
            f"Best by a {program_short} {position} since "
            f"{predecessor_name} {predecessor_season}."
        )
    if cohort_level == "conference":
        label = conference_short or "conference"
        return (
            f"Top-{rank} among {label} {position}s since {era_start_season}."
        )
    label = level_label or "FBS"
    return (
        f"Top-{rank} among {label} {position}s in the {era_label} era "
        f"({era_start_season}–present)."
    )


def compute_era_context(
    db: Database,
    *,
    player_id: int,
    metric_id: str,
    season: int,
    value: float | None,
    position: str,
    team_id: int | None = None,
) -> dict[str, Any]:
    """Return era-context metadata for a (player, metric, season) cell.

    Always returns a dict — callers read ``applicable`` and render the
    ``text`` only when True. See the spec doc for shape and templates.
    """
    inapplicable = {"applicable": False, "text": "", "target_ref": None}

    if value is None:
        return inapplicable
    meta = _METRIC_STAT_MAP.get(metric_id)
    if meta is None:
        return inapplicable
    category, stat_type, higher_is_better = meta

    if team_id is None:
        # Fall back to the team the player most recently carried in
        # player_season_stats — the call site often doesn't know team_id
        # up-front (Signature Story pipeline).
        row = db.query_one(
            "SELECT team_id FROM player_season_stats WHERE player_id = :pid "
            "ORDER BY season_year DESC LIMIT 1",
            {"pid": player_id},
        )
        if row:
            team_id = row["team_id"]
    team_row: dict[str, Any] | None = None
    if team_id is not None:
        team_row = db.query_one(
            "SELECT team_id, school_name, short_name, current_conference_id, level_code "
            "FROM teams WHERE team_id = :team_id",
            {"team_id": team_id},
        )
    conference_id = (team_row or {}).get("current_conference_id")
    level_code = (team_row or {}).get("level_code")
    program_short = (team_row or {}).get("short_name") or (team_row or {}).get("school_name")

    db_id = _Database_Registry.register(db)

    # Cohort chain: program → conference → level.
    cohort_chain: list[tuple[str, dict[str, Any]]] = []
    if team_id is not None:
        span = _cohort_span(db_id, category, stat_type, position, team_id, None, None)
        if span is not None:
            cohort_chain.append(("program", {"team_id": team_id, "span": span}))
    if conference_id is not None:
        span = _cohort_span(db_id, category, stat_type, position, None, conference_id, None)
        if span is not None:
            cohort_chain.append(("conference", {"conference_id": conference_id, "span": span}))
    if level_code is not None:
        span = _cohort_span(db_id, category, stat_type, position, None, None, level_code)
        if span is not None:
            cohort_chain.append(("level", {"level_code": level_code, "span": span}))

    if not cohort_chain:
        return inapplicable

    for cohort_level, data in cohort_chain:
        kwargs: dict[str, Any] = {
            "category": category,
            "stat_type": stat_type,
            "position": position,
            "team_id": None,
            "conference_id": None,
            "level_code": None,
            "exclude_player_id": player_id,
            "current_value": float(value),
            "higher_is_better": higher_is_better,
            "current_season": season,
        }
        if cohort_level == "program":
            kwargs["team_id"] = data["team_id"]
        elif cohort_level == "conference":
            kwargs["conference_id"] = data["conference_id"]
        else:
            kwargs["level_code"] = data["level_code"]

        prior = _query_prior_best(db, **kwargs)
        if not prior:
            continue

        prior_value = float(prior["stat_value_num"])
        # Rank gate — we only ship rank 1 (player beats prior best) or a
        # near-tie. For lower-is-better metrics the comparison flips.
        if higher_is_better:
            beats_prior = float(value) >= prior_value
            gap = abs(float(value) - prior_value) / max(abs(prior_value), 1e-9)
        else:
            beats_prior = float(value) <= prior_value
            gap = abs(prior_value - float(value)) / max(abs(prior_value), 1e-9)
        is_tie = gap <= TIE_THRESHOLD_PCT
        if not beats_prior and not is_tie:
            # Player didn't beat the prior best — claim must be scoped
            # to "top-N" phrasing for fallback cohorts only.
            if cohort_level == "program":
                continue
            if gap > TOP_BAND_GAP_PCT:
                continue
            rank_display = 2 if gap <= 0.05 else 3
        else:
            rank_display = 1

        conference_short = None
        level_label = None
        if cohort_level == "conference":
            conf_row = db.query_one(
                "SELECT short_name FROM conferences WHERE conference_id = :cid",
                {"cid": data["conference_id"]},
            )
            conference_short = (conf_row or {}).get("short_name") if conf_row else None
        elif cohort_level == "level":
            lvl = data["level_code"]
            level_label = "FBS" if lvl in ("fbs",) else "FCS" if lvl in ("fcs",) else str(lvl or "FBS").upper()

        era_start = data["span"][0]

        text = _format_text(
            cohort_level=cohort_level,
            program_short=program_short,
            conference_short=conference_short,
            level_label=level_label,
            position=position,
            predecessor_name=str(prior["predecessor_name"]),
            predecessor_season=int(prior["season_year"]),
            rank=rank_display,
            is_tie=is_tie,
            era_label=_era_label(era_start),
            era_start_season=era_start,
        )
        return {
            "applicable": True,
            "text": text,
            "target_ref": {
                "player_id": int(prior["player_id"]),
                "season": int(prior["season_year"]),
                "metric_id": metric_id,
                "cohort": f"{cohort_level}-{position.lower()}",
                "rank_in_cohort": rank_display,
                "era_start_season": era_start,
            },
        }

    return inapplicable
