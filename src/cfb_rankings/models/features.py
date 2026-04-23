from __future__ import annotations

from dataclasses import dataclass
import math

from cfb_rankings.db import Database
from cfb_rankings.models.ridge import fit_sparse_ridge_with_prior
from cfb_rankings.utils import clamp


METRIC_SPECS = [
    ("offense_ppa", "defense_ppa", "ppa_off_adj", "ppa_def_adj"),
    ("success_rate_off", "success_rate_def", "success_off_adj", "success_def_adj"),
    ("explosiveness_off", "explosiveness_def", "explosive_off_adj", "explosive_def_adj"),
    ("rushing_ppa_off", "rushing_ppa_def", "rush_ppa_off_adj", "rush_ppa_def_adj"),
    ("passing_ppa_off", "passing_ppa_def", "pass_ppa_off_adj", "pass_ppa_def_adj"),
    ("finishing_drives_off", "finishing_drives_def", "finish_off_adj", "finish_def_adj"),
    ("field_position_off", "field_position_def", "field_pos_off_adj", "field_pos_def_adj"),
]


@dataclass
class FeatureObservation:
    week: int
    team_id: int
    opponent_team_id: int
    home_flag: float
    offense_value: float
    defense_value: float


class OpponentAdjustedFeatureBuilder:
    def __init__(self, db: Database, model_version: str) -> None:
        self.db = db
        self.model_version = model_version
        self._source_rows_cache: dict[int, list[dict[str, object]]] = {}

    def compute_week(self, season: int, week: int) -> dict[int, dict[str, float]]:
        existing_rows = self.db.query_all(
            """
            select team_id, metric_name, adjusted_value
            from opponent_adjusted_team_week
            where season_year = %(season)s
              and week = %(week)s
              and model_version = %(model_version)s
            """,
            {"season": season, "week": week, "model_version": self.model_version},
        )
        if existing_rows:
            print(
                f"[features] season {season} week {week}: reusing cached opponent-adjusted features.",
                flush=True,
            )
            feature_map: dict[int, dict[str, float]] = {}
            for row in existing_rows:
                team_id = int(row["team_id"])
                feature_map.setdefault(team_id, {})[str(row["metric_name"])] = float(row["adjusted_value"] or 0.0)
            return feature_map

        season_rows = self._source_rows_cache.get(season)
        if season_rows is None:
            print(
                f"[features] season {season}: loading advanced-stat source rows for opponent adjustments...",
                flush=True,
            )
            season_rows = self.db.query_all(
                """
                select
                  g.week,
                  g.neutral_site,
                  g.home_team_id,
                  g.away_team_id,
                  tgas.team_id,
                  tgas.opponent_team_id,
                  tgas.offense_ppa,
                  tgas.defense_ppa,
                  tgas.success_rate_off,
                  tgas.success_rate_def,
                  tgas.explosiveness_off,
                  tgas.explosiveness_def,
                  tgas.rushing_ppa_off,
                  tgas.rushing_ppa_def,
                  tgas.passing_ppa_off,
                  tgas.passing_ppa_def,
                  tgas.finishing_drives_off,
                  tgas.finishing_drives_def,
                  tgas.field_position_off,
                  tgas.field_position_def
                from team_game_advanced_stats tgas
                join games g on g.game_id = tgas.game_id
                where g.season_year = %(season)s
                  and g.home_points is not null
                  and g.away_points is not null
                order by g.week, g.game_id, tgas.team_id
                """,
                {"season": season},
            )
            self._source_rows_cache[season] = season_rows
            print(
                f"[features] season {season}: loaded {len(season_rows)} advanced-stat team-game rows.",
                flush=True,
            )

        rows = [row for row in season_rows if int(row["week"]) <= week]
        if not rows:
            print(
                f"[features] season {season} week {week}: no advanced-stat rows available yet.",
                flush=True,
            )
            return {}

        team_ids = sorted({int(row["team_id"]) for row in rows})
        print(
            f"[features] season {season} week {week}: computing opponent-adjusted metrics for "
            f"{len(team_ids)} teams from {len(rows)} rows.",
            flush=True,
        )
        team_index = {team_id: index for index, team_id in enumerate(team_ids)}
        stored_rows: list[dict[str, object]] = []
        feature_map: dict[int, dict[str, float]] = {team_id: {} for team_id in team_ids}

        observations = [_row_to_observation(row) for row in rows]

        for offense_column, defense_column, offense_metric_name, defense_metric_name in METRIC_SPECS:
            metric_rows = [
                (
                    observation,
                    row.get(offense_column),
                    row.get(defense_column),
                )
                for observation, row in zip(observations, rows, strict=True)
                if row.get(offense_column) is not None and row.get(defense_column) is not None
            ]
            if not metric_rows:
                continue

            print(
                f"[features] season {season} week {week}: fitting {offense_metric_name}/{defense_metric_name} "
                f"from {len(metric_rows)} samples.",
                flush=True,
            )

            num_features = 2 * len(team_ids) + 1
            hfa_index = num_features - 1
            sparse_rows: list[tuple[tuple[int, ...], tuple[float, ...]]] = []
            target = [0.0 for _ in range(len(metric_rows))]
            weights = [0.0 for _ in range(len(metric_rows))]
            offense_raw: dict[int, list[float]] = {team_id: [] for team_id in team_ids}
            defense_raw: dict[int, list[float]] = {team_id: [] for team_id in team_ids}
            sample_size: dict[int, int] = {team_id: 0 for team_id in team_ids}

            for row_index, (observation, offense_value_raw, defense_value_raw) in enumerate(metric_rows):
                offense_value = float(offense_value_raw)
                defense_value = float(defense_value_raw)
                team_pos = team_index[observation.team_id]
                opponent_pos = team_index[observation.opponent_team_id]
                sparse_rows.append(_sparse_feature_row(team_pos, len(team_ids) + opponent_pos, hfa_index, observation.home_flag))
                target[row_index] = offense_value
                weights[row_index] = math.exp(-0.1 * max(0, week - observation.week))

                offense_raw[observation.team_id].append(offense_value)
                defense_raw[observation.team_id].append(defense_value)
                sample_size[observation.team_id] += 1

            coefficients = fit_sparse_ridge_with_prior(
                num_features=num_features,
                rows=sparse_rows,
                target=target,
                weights=weights,
                alpha_prior=6.0,
                prior_mean=[0.0 for _ in range(num_features)],
                alpha_ridge=1.0,
            )
            offense_coefficients = coefficients[: len(team_ids)]
            defense_coefficients = coefficients[len(team_ids) : 2 * len(team_ids)]

            offense_percentiles = _percentiles(list(offense_coefficients))
            defense_percentiles = _percentiles(list(defense_coefficients))

            for team_id in team_ids:
                idx = team_index[team_id]
                offense_value = float(offense_coefficients[idx])
                defense_value = float(defense_coefficients[idx])
                feature_map[team_id][offense_metric_name] = offense_value
                feature_map[team_id][defense_metric_name] = defense_value
                stored_rows.extend(
                    [
                        {
                            "season_year": season,
                            "week": week,
                            "team_id": team_id,
                            "metric_name": offense_metric_name,
                            "raw_value": _mean(offense_raw[team_id]),
                            "adjusted_value": offense_value,
                            "percentile": offense_percentiles[idx],
                            "sample_size": sample_size[team_id],
                            "model_version": self.model_version,
                        },
                        {
                            "season_year": season,
                            "week": week,
                            "team_id": team_id,
                            "metric_name": defense_metric_name,
                            "raw_value": _mean(defense_raw[team_id]),
                            "adjusted_value": defense_value,
                            "percentile": defense_percentiles[idx],
                            "sample_size": sample_size[team_id],
                            "model_version": self.model_version,
                        },
                    ]
                )

        self.db.upsert_many(
            "opponent_adjusted_team_week",
            stored_rows,
            conflict_columns=["season_year", "week", "team_id", "metric_name", "model_version"],
        )
        print(
            f"[features] season {season} week {week}: stored {len(stored_rows)} opponent-adjusted metric rows.",
            flush=True,
        )
        return feature_map


def _row_to_observation(row: dict[str, object]) -> FeatureObservation:
    team_id = int(row["team_id"])
    home_team_id = int(row["home_team_id"])
    away_team_id = int(row["away_team_id"])
    neutral_site = bool(row["neutral_site"])
    if neutral_site:
        home_flag = 0.0
    elif team_id == home_team_id:
        home_flag = 1.0
    else:
        home_flag = -1.0

    return FeatureObservation(
        week=int(row["week"]),
        team_id=team_id,
        opponent_team_id=int(row["opponent_team_id"]),
        home_flag=home_flag,
        offense_value=0.0,
        defense_value=0.0,
    )


def _percentiles(values: list[float]) -> list[float]:
    if not values:
        return []
    sorted_pairs = sorted(enumerate(values), key=lambda pair: pair[1])
    percentiles = [0.0] * len(values)
    denominator = max(1, len(values) - 1)
    for rank, (index, _) in enumerate(sorted_pairs):
        percentiles[index] = clamp(rank / denominator, 0.0, 1.0)
    return percentiles


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _sparse_feature_row(
    offense_index: int,
    defense_index: int,
    hfa_index: int,
    home_flag: float,
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    if home_flag:
        return (offense_index, defense_index, hfa_index), (1.0, -1.0, home_flag)
    return (offense_index, defense_index), (1.0, -1.0)
