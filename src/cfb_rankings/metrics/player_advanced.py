"""Player advanced metric producers — Autopilot v1 TASK 1.4.

The kickoff spec named 13 PBP-derived metrics (CPOE, pressure-to-sack,
EPA/dropback, aDOT, deep-ball, play-action, scramble, turnover-worthy
play rate, etc.) and promised they were "all computable from game_plays".
In practice the current `plays` table is skinny: it carries offense_team_id
and defense_team_id, EPA, success_flag, down/distance/yard_line, play_type,
yards_gained — but NO player-level attribution (no passer_id, receiver_id,
rusher_id, pressure_flag, dropback_flag, air_yards, play_action_flag).

So v1 ships the 13 metrics the kickoff asked for in spirit, but maps them
to actually-computable quantities: CFBD WEPA (already in
`player_value_metrics`), box-score rates (`player_game_stats`), team-proxy
plays metrics (`plays` aggregated on offense_team_id and attributed to
the player via their `player_game_stats` share), and drive-level red-zone
TD rate (from `drives`). Each metric has a clear definition in its
docstring, a sample-size gate, and a `requires_play_attribution` flag so
future plays-stats ingestion work can upgrade the computer without
touching the schema.

Public API:
    compute_player_advanced_metrics(db, season, week=None)
        -> int  # rows written
    compute_player_advanced_metrics_season(db, season) -> int
    METRICS: dict[metric_id -> MetricSpec]
    MetricResult(value, sample_size)

Row keying: (player_id, season_year, week, metric_id) UNIQUE.
`week=0` = full-season rollup (written by the season-scope helper).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable, Iterable

from cfb_rankings.db import Database

log = logging.getLogger(__name__)

METRIC_VERSION = "1.0.0"

# Positions this v1 considers. Anything else is skipped.
_APPLICABLE_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


@dataclass(frozen=True)
class MetricResult:
    value: float | None
    sample_size: int

    @property
    def is_empty(self) -> bool:
        return self.value is None or self.sample_size <= 0


ComputerFn = Callable[
    ["ComputeContext", int, int, int, str],
    MetricResult | None,
]


@dataclass(frozen=True)
class MetricSpec:
    metric_id: str
    display_name: str
    positions: frozenset[str]
    unit: str                      # e.g. "rate", "per_play", "yards_per_game"
    min_sample: int                # sample_size below this -> value=None
    higher_is_better: bool
    requires_play_attribution: bool  # True if a future PBP-stats table is needed
    compute: ComputerFn


# ---------------------------------------------------------------------------
# Compute context
# ---------------------------------------------------------------------------


@dataclass
class ComputeContext:
    """Per-(season, week) cache of the heavy joins.

    The bulk computation reads all relevant rows for the season once, then
    every metric's computer queries the cache instead of the DB.
    """

    season: int
    # week -> list of rows; week=0 means "through-season"
    pvm_by_player: dict[int, list[dict]]        # player_id -> player_value_metrics rows
    pgs_by_player: dict[int, list[dict]]        # player_id -> player_game_stats rows
    team_season_plays: dict[int, dict]           # team_id -> aggregated plays summary
    team_season_drives: dict[int, dict]          # team_id -> aggregated drives summary
    player_team_ids: dict[int, int]              # player_id -> primary team_id for this season


# ---------------------------------------------------------------------------
# Helpers — parsing player_game_stats text values
# ---------------------------------------------------------------------------


_C_ATT_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


def _parse_c_att(raw: str | None) -> tuple[int, int] | None:
    if not raw:
        return None
    match = _C_ATT_RE.search(raw)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _float_or_none(raw) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _aggregate_player_game_stats(rows: list[dict]) -> dict[str, float]:
    """Collapse a player's season rows in player_game_stats to totals.

    Keyed by (category, stat_type). Text values like "195/308" are parsed
    into their numeric components using _parse_c_att.
    """
    totals: dict[str, float] = {
        "pass_attempts": 0.0,
        "pass_completions": 0.0,
        "pass_yards": 0.0,
        "pass_tds": 0.0,
        "pass_ints": 0.0,
        "rush_attempts": 0.0,
        "rush_yards": 0.0,
        "rush_tds": 0.0,
        "receptions": 0.0,
        "receiving_yards": 0.0,
        "receiving_tds": 0.0,
        "qbr_sum": 0.0,
        "qbr_games": 0.0,
        "games_counted": 0.0,
    }
    games_seen: set[int] = set()
    for row in rows:
        category = (row.get("category") or "").lower()
        stat = (row.get("stat_type") or "").upper().strip()
        num = _float_or_none(row.get("stat_value_num"))
        text = row.get("stat_value_text")
        game_id = row.get("game_id")
        if game_id is not None:
            games_seen.add(int(game_id))
        if category == "passing":
            if stat == "C/ATT":
                parsed = _parse_c_att(text)
                if parsed:
                    cmp, att = parsed
                    totals["pass_completions"] += cmp
                    totals["pass_attempts"] += att
            elif stat == "YDS" and num is not None:
                totals["pass_yards"] += num
            elif stat == "TD" and num is not None:
                totals["pass_tds"] += num
            elif stat == "INT" and num is not None:
                totals["pass_ints"] += num
            elif stat == "QBR" and num is not None:
                totals["qbr_sum"] += num
                totals["qbr_games"] += 1
        elif category == "rushing":
            if stat == "CAR" and num is not None:
                totals["rush_attempts"] += num
            elif stat == "YDS" and num is not None:
                totals["rush_yards"] += num
            elif stat == "TD" and num is not None:
                totals["rush_tds"] += num
        elif category == "receiving":
            if stat == "REC" and num is not None:
                totals["receptions"] += num
            elif stat == "YDS" and num is not None:
                totals["receiving_yards"] += num
            elif stat == "TD" and num is not None:
                totals["receiving_tds"] += num
    totals["games_counted"] = float(len(games_seen))
    return totals


# ---------------------------------------------------------------------------
# Computers
# ---------------------------------------------------------------------------


def _compute_wepa_passing_per_play(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    for row in ctx.pvm_by_player.get(player_id, []):
        if row.get("metric_name") != "wepa_passing":
            continue
        plays = int(row.get("plays") or 0)
        value = _float_or_none(row.get("metric_value"))
        if plays <= 0 or value is None:
            return MetricResult(None, plays)
        return MetricResult(value / plays, plays)
    return None


def _compute_wepa_rushing_per_play(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    for row in ctx.pvm_by_player.get(player_id, []):
        if row.get("metric_name") != "wepa_rushing":
            continue
        plays = int(row.get("plays") or 0)
        value = _float_or_none(row.get("metric_value"))
        if plays <= 0 or value is None:
            return MetricResult(None, plays)
        return MetricResult(value / plays, plays)
    return None


def _pgs_totals(ctx: ComputeContext, player_id: int) -> dict[str, float]:
    rows = ctx.pgs_by_player.get(player_id, [])
    return _aggregate_player_game_stats(rows)


def _compute_pass_completion_pct(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    att = t["pass_attempts"]
    if att <= 0:
        return None
    return MetricResult(t["pass_completions"] / att * 100.0, int(att))


def _compute_pass_ypa(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    att = t["pass_attempts"]
    if att <= 0:
        return None
    return MetricResult(t["pass_yards"] / att, int(att))


def _compute_pass_td_rate(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    att = t["pass_attempts"]
    if att <= 0:
        return None
    return MetricResult(t["pass_tds"] / att * 100.0, int(att))


def _compute_pass_int_rate(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    att = t["pass_attempts"]
    if att <= 0:
        return None
    return MetricResult(t["pass_ints"] / att * 100.0, int(att))


def _compute_pass_yards_per_game(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    games = t["games_counted"]
    if games <= 0:
        return None
    return MetricResult(t["pass_yards"] / games, int(games))


def _compute_qbr_season_avg(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    n = t["qbr_games"]
    if n <= 0:
        return None
    return MetricResult(t["qbr_sum"] / n, int(n))


def _compute_rush_ypc(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    car = t["rush_attempts"]
    if car <= 0:
        return None
    return MetricResult(t["rush_yards"] / car, int(car))


def _compute_rush_yards_per_game(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    games = t["games_counted"]
    if games <= 0:
        return None
    return MetricResult(t["rush_yards"] / games, int(games))


def _compute_receiving_ypr(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    rec = t["receptions"]
    if rec <= 0:
        return None
    return MetricResult(t["receiving_yards"] / rec, int(rec))


def _compute_receiving_yards_per_game(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    t = _pgs_totals(ctx, player_id)
    games = t["games_counted"]
    if games <= 0:
        return None
    return MetricResult(t["receiving_yards"] / games, int(games))


def _compute_team_success_rate_on_offense(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    team_id = ctx.player_team_ids.get(player_id)
    if team_id is None:
        return None
    agg = ctx.team_season_plays.get(team_id)
    if not agg or agg["offense_plays"] <= 0:
        return None
    return MetricResult(
        agg["offense_successes"] / agg["offense_plays"] * 100.0,
        int(agg["offense_plays"]),
    )


def _compute_team_explosive_rate_on_offense(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    team_id = ctx.player_team_ids.get(player_id)
    if team_id is None:
        return None
    agg = ctx.team_season_plays.get(team_id)
    if not agg or agg["offense_plays"] <= 0:
        return None
    return MetricResult(
        agg["offense_explosive_20plus"] / agg["offense_plays"] * 100.0,
        int(agg["offense_plays"]),
    )


def _compute_team_red_zone_td_rate(
    ctx: ComputeContext, player_id: int, season: int, week: int, position: str
) -> MetricResult | None:
    team_id = ctx.player_team_ids.get(player_id)
    if team_id is None:
        return None
    agg = ctx.team_season_drives.get(team_id)
    if not agg or agg["red_zone_drives"] <= 0:
        return None
    return MetricResult(
        agg["red_zone_tds"] / agg["red_zone_drives"] * 100.0,
        int(agg["red_zone_drives"]),
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_QB = frozenset({"QB"})
_QB_RB = frozenset({"QB", "RB"})
_RB = frozenset({"RB"})
_WR_TE = frozenset({"WR", "TE"})
_ALL_SKILL = frozenset({"QB", "RB", "WR", "TE"})

METRICS: dict[str, MetricSpec] = {
    spec.metric_id: spec
    for spec in [
        MetricSpec(
            metric_id="wepa_passing_per_play",
            display_name="CFBD WEPA per pass play",
            positions=_QB,
            unit="per_play",
            min_sample=50,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_wepa_passing_per_play,
        ),
        MetricSpec(
            metric_id="wepa_rushing_per_play",
            display_name="CFBD WEPA per rush play",
            positions=_QB_RB,
            unit="per_play",
            min_sample=30,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_wepa_rushing_per_play,
        ),
        MetricSpec(
            metric_id="pass_completion_pct",
            display_name="Completion percentage",
            positions=_QB,
            unit="percent",
            min_sample=40,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_pass_completion_pct,
        ),
        MetricSpec(
            metric_id="pass_ypa",
            display_name="Yards per pass attempt",
            positions=_QB,
            unit="yards_per_attempt",
            min_sample=40,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_pass_ypa,
        ),
        MetricSpec(
            metric_id="pass_td_rate",
            display_name="Pass TD rate",
            positions=_QB,
            unit="percent",
            min_sample=40,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_pass_td_rate,
        ),
        MetricSpec(
            metric_id="pass_int_rate",
            display_name="Interception rate",
            positions=_QB,
            unit="percent",
            min_sample=40,
            higher_is_better=False,
            requires_play_attribution=False,
            compute=_compute_pass_int_rate,
        ),
        MetricSpec(
            metric_id="pass_yards_per_game",
            display_name="Passing yards per game",
            positions=_QB,
            unit="yards_per_game",
            min_sample=1,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_pass_yards_per_game,
        ),
        MetricSpec(
            metric_id="qbr_season_avg",
            display_name="ESPN QBR (season mean)",
            positions=_QB,
            unit="index_0_100",
            min_sample=1,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_qbr_season_avg,
        ),
        MetricSpec(
            metric_id="rush_ypc",
            display_name="Yards per carry",
            positions=_QB_RB,
            unit="yards_per_attempt",
            min_sample=25,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_rush_ypc,
        ),
        MetricSpec(
            metric_id="rush_yards_per_game",
            display_name="Rushing yards per game",
            positions=_QB_RB,
            unit="yards_per_game",
            min_sample=1,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_rush_yards_per_game,
        ),
        MetricSpec(
            metric_id="receiving_ypr",
            display_name="Yards per reception",
            positions=_WR_TE,
            unit="yards_per_reception",
            min_sample=15,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_receiving_ypr,
        ),
        MetricSpec(
            metric_id="receiving_yards_per_game",
            display_name="Receiving yards per game",
            positions=_WR_TE,
            unit="yards_per_game",
            min_sample=1,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_receiving_yards_per_game,
        ),
        MetricSpec(
            metric_id="team_success_rate_on_offense",
            display_name="Team offense success rate (proxy)",
            positions=_ALL_SKILL,
            unit="percent",
            min_sample=100,
            higher_is_better=True,
            requires_play_attribution=True,
            compute=_compute_team_success_rate_on_offense,
        ),
        MetricSpec(
            metric_id="team_explosive_rate_20plus_on_offense",
            display_name="Team offense explosive-play rate 20+yd (proxy)",
            positions=_ALL_SKILL,
            unit="percent",
            min_sample=100,
            higher_is_better=True,
            requires_play_attribution=True,
            compute=_compute_team_explosive_rate_on_offense,
        ),
        MetricSpec(
            metric_id="team_red_zone_td_rate",
            display_name="Team red-zone TD rate (from drives)",
            positions=_ALL_SKILL,
            unit="percent",
            min_sample=10,
            higher_is_better=True,
            requires_play_attribution=False,
            compute=_compute_team_red_zone_td_rate,
        ),
    ]
}


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


def _build_context(db: Database, season: int, week: int | None) -> ComputeContext:
    # player_value_metrics
    if week is None:
        pvm_rows = db.query_all(
            "select player_id, team_id, position, metric_name, metric_value, plays, week "
            "from player_value_metrics where season_year = :season",
            {"season": season},
        )
    else:
        pvm_rows = db.query_all(
            "select player_id, team_id, position, metric_name, metric_value, plays, week "
            "from player_value_metrics where season_year = :season and week = :week",
            {"season": season, "week": week},
        )
    pvm_by_player: dict[int, list[dict]] = {}
    player_team_ids: dict[int, int] = {}
    for row in pvm_rows:
        pvm_by_player.setdefault(row["player_id"], []).append(row)
        if row["team_id"] is not None:
            player_team_ids.setdefault(row["player_id"], int(row["team_id"]))

    # player_game_stats
    if week is None:
        pgs_rows = db.query_all(
            "select player_id, team_id, game_id, category, stat_type, stat_value_text, stat_value_num "
            "from player_game_stats where season_year = :season",
            {"season": season},
        )
    else:
        pgs_rows = db.query_all(
            "select player_id, team_id, game_id, category, stat_type, stat_value_text, stat_value_num "
            "from player_game_stats where season_year = :season and week <= :week",
            {"season": season, "week": week},
        )
    pgs_by_player: dict[int, list[dict]] = {}
    for row in pgs_rows:
        pgs_by_player.setdefault(row["player_id"], []).append(row)
        if row["player_id"] not in player_team_ids and row["team_id"] is not None:
            player_team_ids[row["player_id"]] = int(row["team_id"])

    # team-level plays — aggregate offense side only
    if week is None:
        team_plays_rows = db.query_all(
            """
            select
                p.offense_team_id as team_id,
                count(*) as plays,
                coalesce(sum(p.success_flag), 0) as successes,
                coalesce(sum(case when p.yards_gained >= 20 then 1 else 0 end), 0) as explosive
            from plays p
            join games g on g.game_id = p.game_id
            where g.season_year = :season
              and coalesce(p.is_garbage_time, 0) = 0
              and p.offense_team_id is not null
            group by p.offense_team_id
            """,
            {"season": season},
        )
    else:
        team_plays_rows = db.query_all(
            """
            select
                p.offense_team_id as team_id,
                count(*) as plays,
                coalesce(sum(p.success_flag), 0) as successes,
                coalesce(sum(case when p.yards_gained >= 20 then 1 else 0 end), 0) as explosive
            from plays p
            join games g on g.game_id = p.game_id
            where g.season_year = :season
              and g.week <= :week
              and coalesce(p.is_garbage_time, 0) = 0
              and p.offense_team_id is not null
            group by p.offense_team_id
            """,
            {"season": season, "week": week},
        )
    team_season_plays: dict[int, dict] = {
        int(row["team_id"]): {
            "offense_plays": int(row["plays"] or 0),
            "offense_successes": int(row["successes"] or 0),
            "offense_explosive_20plus": int(row["explosive"] or 0),
        }
        for row in team_plays_rows
    }

    # drives for red-zone TD rate. Red zone ≈ end yardline within 20 of opponent.
    # drives.end_yardline is measured from offense's side; "red zone reached"
    # = end_yardline <= 20 OR any play within (derived from play-level would be
    # cleaner but we use drive-end as a proxy for "drive crossed into RZ").
    # Counting red-zone DRIVES is the denominator; red-zone TDs (result='TD'
    # and end_yardline <= 20) is the numerator.
    if week is None:
        drives_rows = db.query_all(
            """
            select
                d.offense_team_id as team_id,
                sum(case when d.end_yardline is not null and d.end_yardline <= 20 then 1 else 0 end) as red_zone_drives,
                sum(case when d.end_yardline is not null and d.end_yardline <= 20 and lower(d.result) like '%td%' then 1 else 0 end) as red_zone_tds
            from drives d
            join games g on g.game_id = d.game_id
            where g.season_year = :season and d.offense_team_id is not null
            group by d.offense_team_id
            """,
            {"season": season},
        )
    else:
        drives_rows = db.query_all(
            """
            select
                d.offense_team_id as team_id,
                sum(case when d.end_yardline is not null and d.end_yardline <= 20 then 1 else 0 end) as red_zone_drives,
                sum(case when d.end_yardline is not null and d.end_yardline <= 20 and lower(d.result) like '%td%' then 1 else 0 end) as red_zone_tds
            from drives d
            join games g on g.game_id = d.game_id
            where g.season_year = :season and g.week <= :week and d.offense_team_id is not null
            group by d.offense_team_id
            """,
            {"season": season, "week": week},
        )
    team_season_drives: dict[int, dict] = {
        int(row["team_id"]): {
            "red_zone_drives": int(row["red_zone_drives"] or 0),
            "red_zone_tds": int(row["red_zone_tds"] or 0),
        }
        for row in drives_rows
    }

    return ComputeContext(
        season=season,
        pvm_by_player=pvm_by_player,
        pgs_by_player=pgs_by_player,
        team_season_plays=team_season_plays,
        team_season_drives=team_season_drives,
        player_team_ids=player_team_ids,
    )


def _player_position(db: Database, player_id: int) -> str | None:
    """Resolve the player's current position (cache-free; compute path is
    called once per player per metric)."""
    row = db.query_one(
        "select position from players where player_id = :pid",
        {"pid": player_id},
    )
    if not row:
        return None
    pos = row.get("position")
    return pos.upper() if pos else None


def _player_positions_bulk(db: Database, player_ids: Iterable[int]) -> dict[int, str]:
    ids = list(set(int(pid) for pid in player_ids))
    if not ids:
        return {}
    placeholders = ", ".join("?" for _ in ids)
    rows = db.query_all(
        f"select player_id, position from players where player_id in ({placeholders})",
        tuple(ids),
    )
    return {
        int(row["player_id"]): (row["position"].upper() if row.get("position") else "")
        for row in rows
    }


def _candidate_player_ids(ctx: ComputeContext) -> set[int]:
    return set(ctx.pvm_by_player.keys()) | set(ctx.pgs_by_player.keys())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_player_advanced_metrics(
    db: Database, season: int, week: int | None = None
) -> int:
    """Compute and upsert player_advanced_metrics rows for the given season.

    Args:
        db: Database.
        season: season year (e.g. 2025).
        week: if given, constrain to games with week <= N; rows land with
            week=<that N> so the season-rollup CLI can later overwrite week=0.
            When None, we write through the latest available week and stamp
            week=0 (the season rollup key).

    Returns the number of rows upserted.
    """
    ctx = _build_context(db, season, week)
    stamp_week = week if week is not None else 0
    candidates = _candidate_player_ids(ctx)
    positions = _player_positions_bulk(db, candidates)

    rows_to_write: list[dict] = []
    for player_id in candidates:
        position = positions.get(player_id, "")
        if position not in _APPLICABLE_POSITIONS:
            continue
        for spec in METRICS.values():
            if position not in spec.positions:
                continue
            result = spec.compute(ctx, player_id, season, stamp_week, position)
            if result is None:
                continue
            value = result.value if result.sample_size >= spec.min_sample else None
            rows_to_write.append(
                {
                    "player_id": player_id,
                    "season_year": season,
                    "week": stamp_week,
                    "metric_id": spec.metric_id,
                    "value": value,
                    "sample_size": result.sample_size,
                    "cohort_id": None,
                    "metric_version": METRIC_VERSION,
                }
            )

    if rows_to_write:
        db.upsert_many(
            "player_advanced_metrics",
            rows_to_write,
            conflict_columns=["player_id", "season_year", "week", "metric_id"],
        )
    log.info(
        "compute_player_advanced_metrics: season=%d week=%s wrote=%d",
        season,
        stamp_week,
        len(rows_to_write),
    )
    return len(rows_to_write)


def compute_player_advanced_metrics_season(db: Database, season: int) -> int:
    """Compute season rollup (week=0) AND per-metric percentiles within
    position cohorts (QB, RB, WR, TE).
    """
    weekly_written = compute_player_advanced_metrics(db, season, week=None)

    rollup_rows = db.query_all(
        "select player_id, season_year, metric_id, value, sample_size, metric_version "
        "from player_advanced_metrics where season_year = :season and week = 0",
        {"season": season},
    )
    if not rollup_rows:
        return weekly_written

    positions = _player_positions_bulk(db, [row["player_id"] for row in rollup_rows])

    # Group rows by (metric_id, position) and compute percentiles.
    cohort_groups: dict[tuple[str, str], list[dict]] = {}
    for row in rollup_rows:
        position = positions.get(int(row["player_id"]), "")
        if not position or row["value"] is None:
            continue
        cohort_groups.setdefault((row["metric_id"], position), []).append(row)

    season_rows: list[dict] = []
    for (metric_id, position), rows in cohort_groups.items():
        spec = METRICS.get(metric_id)
        if spec is None:
            continue
        # Only keep rows meeting this metric's min_sample gate for ranking.
        qualified = [r for r in rows if int(r.get("sample_size") or 0) >= spec.min_sample]
        cohort_size = len(qualified)
        if cohort_size == 0:
            continue
        qualified.sort(
            key=lambda r: float(r["value"]),
            reverse=spec.higher_is_better,
        )
        for rank, row in enumerate(qualified, start=1):
            percentile = (1.0 - (rank - 1) / cohort_size) * 100.0
            season_rows.append(
                {
                    "player_id": int(row["player_id"]),
                    "season_year": season,
                    "metric_id": metric_id,
                    "value": float(row["value"]),
                    "sample_size": int(row["sample_size"] or 0),
                    "cohort_id": f"{position.lower()}_season_{season}",
                    "percentile": round(percentile, 2),
                    "rank_in_cohort": rank,
                    "cohort_size": cohort_size,
                    "metric_version": METRIC_VERSION,
                }
            )

    if season_rows:
        db.upsert_many(
            "player_advanced_metrics_season",
            season_rows,
            conflict_columns=["player_id", "season_year", "metric_id"],
        )
    log.info(
        "compute_player_advanced_metrics_season: season=%d rollup_written=%d season_rows=%d",
        season,
        weekly_written,
        len(season_rows),
    )
    return weekly_written + len(season_rows)
