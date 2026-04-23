from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.models.features import OpponentAdjustedFeatureBuilder
from cfb_rankings.models.ridge import fit_sparse_ridge_with_prior
from cfb_rankings.utils import DEFAULT_LEVEL_PRIORS, DEFAULT_LEVEL_SIGMA, adjusted_scores, clamp


@dataclass
class PowerTeamRating:
    team_id: int
    team_name: str
    level_code: str
    conference_id: int | None
    week: int
    power_rating: float
    offense_rating: float
    defense_rating: float
    special_teams_rating: float
    tempo_rating: float
    prior_mean: float
    posterior_sd: float
    cross_level_confidence: float
    schedule_connectivity: float


@dataclass
class WeeklyPowerState:
    week: int
    base_points: float
    home_field_advantage: float
    team_ratings: dict[int, PowerTeamRating]


class PowerModelRunner:
    def __init__(self, db: Database, model_version: str) -> None:
        self.db = db
        self.model_version = model_version
        self.feature_builder = OpponentAdjustedFeatureBuilder(db, model_version)

    def run(self, model_run_id: int, season: int, through_week: int) -> dict[int, WeeklyPowerState]:
        print(f"[power] season {season}: preparing priors and source data...", flush=True)
        priors = self._ensure_preseason_priors(season)
        metadata_rows = self._season_team_metadata(season)
        completed_games = self._completed_games(season)
        tempo_by_week = self._tempo_components_by_week(season, through_week)
        weekly_states: dict[int, WeeklyPowerState] = {}
        current_games: list[dict[str, Any]] = []
        game_cursor = 0
        last_feature_map: dict[int, dict[str, float]] = {}
        feature_weeks = self._feature_source_weeks(season)
        print(
            f"[power] season {season}: loaded {len(metadata_rows)} teams, {len(completed_games)} completed games, "
            f"and {len(feature_weeks)} feature weeks through target week {through_week}.",
            flush=True,
        )

        for week in range(0, through_week + 1):
            week_start = time.time()
            print(f"[power] season {season} week {week}: fitting ratings...", flush=True)
            while game_cursor < len(completed_games) and int(completed_games[game_cursor]["week"]) <= week:
                current_games.append(completed_games[game_cursor])
                game_cursor += 1
            if week > 0 and week in feature_weeks:
                last_feature_map = self.feature_builder.compute_week(season, week)
            feature_map = last_feature_map if week > 0 else {}
            weekly_states[week] = self._fit_week(
                week=week,
                priors=priors,
                feature_map=feature_map,
                metadata_rows=metadata_rows,
                completed_games=current_games,
                tempo=tempo_by_week.get(week, {}),
            )
            self._persist_single_week_state(model_run_id, season, weekly_states[week])
            print(
                f"[power] season {season} week {week} complete in {time.time() - week_start:.1f}s",
                flush=True,
            )

        self._persist_level_and_conference_strength(model_run_id, weekly_states[through_week])
        self._persist_game_predictions(model_run_id, season, through_week, weekly_states[through_week])
        self._persist_rating_deltas(model_run_id, season, through_week, weekly_states)
        return weekly_states

    def _feature_source_weeks(self, season: int) -> set[int]:
        rows = self.db.query_all(
            """
            select distinct g.week
            from team_game_advanced_stats tgas
            join games g on g.game_id = tgas.game_id
            where g.season_year = %(season)s
              and g.home_points is not null
              and g.away_points is not null
            order by g.week
            """,
            {"season": season},
        )
        return {int(row["week"]) for row in rows}

    def _ensure_preseason_priors(self, season: int) -> dict[int, dict[str, float]]:
        teams = self.db.query_all(
            """
            select distinct
              t.team_id,
              coalesce(ts.level_code, t.level_code) as level_code,
              ts.conference_id as season_conference_id
            from teams t
            join games g on g.home_team_id = t.team_id or g.away_team_id = t.team_id
            left join team_seasons ts
              on ts.team_id = t.team_id
             and ts.season_year = g.season_year
            where g.season_year = %(season)s
            """,
            {"season": season},
        )
        team_metadata = {
            int(team["team_id"]): {
                "level_code": str(team["level_code"]),
                "season_conference_id": (
                    int(team["season_conference_id"]) if team["season_conference_id"] is not None else None
                ),
            }
            for team in teams
        }
        previous_map = _season_end_power_map(self.db, season - 1)
        program_baseline_map = _program_baseline_map(self.db, season)
        conference_anchor_map = _conference_anchor_map(previous_map, team_metadata)
        returning_points = _level_relative_points(
            _single_value_map(
                self.db,
                """
                select team_id, returning_total as value
                from returning_production
                where season_year = %(season)s
                """,
                {"season": season},
            ),
            team_metadata,
            amplitude=2.2,
        )
        qb_continuity_points = _level_relative_points(
            _single_value_map(
                self.db,
                """
                select team_id, returning_qb as value
                from returning_production
                where season_year = %(season)s
                """,
                {"season": season},
            ),
            team_metadata,
            amplitude=0.9,
        )
        talent_points = _blend_point_maps(
            [
                _level_relative_points(
                    _single_value_map(
                        self.db,
                        """
                        select team_id, talent_score as value
                        from team_talent_snapshots
                        where season_year = %(season)s
                        """,
                        {"season": season},
                    ),
                    team_metadata,
                    amplitude=1.4,
                ),
                _level_relative_points(
                    _single_value_map(
                        self.db,
                        """
                        select team_id, rating as value
                        from recruiting_entries
                        where season_year = %(season)s
                          and class_key = 'team'
                        """,
                        {"season": season},
                    ),
                    team_metadata,
                    amplitude=1.0,
                ),
            ]
        )
        transfer_points = _level_relative_points(
            _transfer_balance_map(self.db, season),
            team_metadata,
            amplitude=1.1,
        )
        continuity_proxy_points = _level_relative_points(
            _roster_continuity_map(self.db, season),
            team_metadata,
            amplitude=1.0,
        )

        rows: list[dict[str, Any]] = []
        priors: dict[int, dict[str, float]] = {}
        for team in teams:
            team_id = int(team["team_id"])
            level_code = str(team["level_code"])
            level_points = DEFAULT_LEVEL_PRIORS[level_code]
            previous_power = previous_map.get(team_id)
            program_baseline = program_baseline_map.get(team_id)
            conference_anchor = conference_anchor_map.get(team_id)
            previous_anchor = previous_power
            if previous_anchor is None:
                previous_anchor = program_baseline if program_baseline is not None else conference_anchor
            prev_season_points = 0.0 if previous_anchor is None else 0.52 * (float(previous_anchor) - level_points)
            program_baseline_points = (
                0.18 * (float(program_baseline) - level_points) if program_baseline is not None else 0.0
            )
            conference_points = 0.08 * (float(conference_anchor) - level_points) if conference_anchor is not None else 0.0
            returning_production_points = returning_points.get(team_id, 0.0)
            talent_component = talent_points.get(team_id, 0.0)
            transfer_component = transfer_points.get(team_id, 0.0)
            qb_continuity_component = qb_continuity_points.get(team_id, 0.0)
            continuity_component = continuity_proxy_points.get(team_id, 0.0)
            coach_points = 0.0
            official_rank_points = 0.0
            manual_offseason_points = 0.0
            prior_mean = (
                level_points
                + prev_season_points
                + program_baseline_points
                + conference_points
                + returning_production_points
                + talent_component
                + transfer_component
                + qb_continuity_component
                + continuity_component
                + coach_points
                + official_rank_points
                + manual_offseason_points
            )
            component_hits = sum(
                1
                for available in (
                    previous_power is not None,
                    program_baseline is not None,
                    conference_anchor is not None,
                    team_id in returning_points,
                    team_id in talent_points,
                    team_id in transfer_points,
                    team_id in qb_continuity_points,
                    team_id in continuity_proxy_points,
                )
                if available
            )
            prior_sd = DEFAULT_LEVEL_SIGMA[level_code] * (1.0 - min(0.24, 0.035 * component_hits))
            if previous_power is None:
                prior_sd *= 1.08
            prior_sd = max(2.5, prior_sd)
            rows.append(
                {
                    "season_year": season,
                    "team_id": team_id,
                    "level_points": level_points,
                    "conference_points": conference_points,
                    "prev_season_points": prev_season_points,
                    "program_baseline_points": program_baseline_points,
                    "returning_production_points": returning_production_points,
                    "talent_points": talent_component,
                    "transfer_points": transfer_component,
                    "coach_points": coach_points,
                    "qb_continuity_points": qb_continuity_component,
                    "continuity_proxy_points": continuity_component,
                    "official_rank_points": official_rank_points,
                    "manual_offseason_points": manual_offseason_points,
                    "prior_mean": prior_mean,
                    "prior_sd": prior_sd,
                }
            )
            priors[team_id] = {"prior_mean": prior_mean, "prior_sd": prior_sd}

        if rows:
            self.db.upsert_many("preseason_prior_components", rows, conflict_columns=["season_year", "team_id"])
        return priors

    def _fit_week(
        self,
        week: int,
        priors: dict[int, dict[str, float]],
        feature_map: dict[int, dict[str, float]],
        metadata_rows: list[dict[str, Any]],
        completed_games: list[dict[str, Any]],
        tempo: dict[int, float],
    ) -> WeeklyPowerState:
        team_ids = [int(row["team_id"]) for row in metadata_rows]
        team_index = {team_id: index for index, team_id in enumerate(team_ids)}
        metadata = {int(row["team_id"]): row for row in metadata_rows}

        if not completed_games:
            return self._prior_only_state(week, metadata, priors)

        active_team_ids = sorted(
            {
                int(game["home_team_id"])
                for game in completed_games
            }
            | {
                int(game["away_team_id"])
                for game in completed_games
            }
        )
        team_ids = active_team_ids
        team_index = {team_id: index for index, team_id in enumerate(team_ids)}
        metadata = {team_id: metadata[team_id] for team_id in team_ids if team_id in metadata}

        observations: list[tuple[int, int, float, float, float]] = []
        adjusted_team_scores: list[float] = []
        bridge_counts = {team_id: 0 for team_id in team_ids}
        opponent_bridge_scores = {team_id: 0 for team_id in team_ids}
        games_played = {team_id: 0 for team_id in team_ids}
        opponent_map: dict[int, set[int]] = {team_id: set() for team_id in team_ids}
        opponent_prior_totals = {team_id: 0.0 for team_id in team_ids}
        opponent_prior_counts = {team_id: 0 for team_id in team_ids}

        for game in completed_games:
            home_id = int(game["home_team_id"])
            away_id = int(game["away_team_id"])
            week_gap = max(0, week - int(game["week"]))
            weight = math.exp(-0.12 * week_gap)
            home_adjusted, away_adjusted = adjusted_scores(int(game["home_points"]), int(game["away_points"]))
            adjusted_team_scores.extend([home_adjusted, away_adjusted])
            home_flag = 0.0 if bool(game["neutral_site"]) else 1.0
            away_flag = 0.0 if bool(game["neutral_site"]) else -1.0
            observations.extend(
                [
                    (home_id, away_id, home_adjusted, home_flag, weight),
                    (away_id, home_id, away_adjusted, away_flag, weight),
                ]
            )
            games_played[home_id] += 1
            games_played[away_id] += 1
            opponent_map[home_id].add(away_id)
            opponent_map[away_id].add(home_id)
            opponent_prior_totals[home_id] += float(priors.get(away_id, {"prior_mean": 0.0})["prior_mean"])
            opponent_prior_totals[away_id] += float(priors.get(home_id, {"prior_mean": 0.0})["prior_mean"])
            opponent_prior_counts[home_id] += 1
            opponent_prior_counts[away_id] += 1
            if game["home_level_code"] != game["away_level_code"]:
                bridge_counts[home_id] += 1
                bridge_counts[away_id] += 1

        for team_id, opponents in opponent_map.items():
            opponent_bridge_scores[team_id] = sum(1 for opponent_id in opponents if bridge_counts.get(opponent_id, 0) > 0)

        base_points = float(sum(adjusted_team_scores) / len(adjusted_team_scores)) if adjusted_team_scores else 28.0
        num_features = 2 * len(team_ids) + 1
        hfa_index = num_features - 1
        sparse_rows: list[tuple[tuple[int, ...], tuple[float, ...]]] = []
        target = [0.0 for _ in range(len(observations))]
        weights = [0.0 for _ in range(len(observations))]
        prior_vector = [0.0 for _ in range(num_features)]

        for team_id in team_ids:
            idx = team_index[team_id]
            prior_mean = priors.get(team_id, {"prior_mean": 0.0})["prior_mean"]
            prior_vector[idx] = prior_mean / 2.0
            prior_vector[len(team_ids) + idx] = prior_mean / 2.0
        prior_vector[-1] = 2.3

        for row_index, (offense_team_id, defense_team_id, observed_points, home_flag, weight) in enumerate(observations):
            offense_idx = team_index[offense_team_id]
            defense_idx = team_index[defense_team_id]
            sparse_rows.append(_sparse_rating_row(offense_idx, len(team_ids) + defense_idx, hfa_index, home_flag))
            target[row_index] = observed_points - base_points
            weights[row_index] = weight

        prior_weight = max(0.10, math.exp(-0.35 * max(0, week - 1)))
        coefficients = fit_sparse_ridge_with_prior(
            num_features=num_features,
            rows=sparse_rows,
            target=target,
            weights=weights,
            alpha_prior=16.0 * prior_weight,
            prior_mean=prior_vector,
            alpha_ridge=2.0,
        )
        offense_coefficients = coefficients[: len(team_ids)]
        defense_coefficients = coefficients[len(team_ids) : 2 * len(team_ids)]
        hfa = float(coefficients[-1])

        feature_composite = _feature_composite(feature_map)
        special_teams = _special_teams_component(feature_map)

        team_ratings: dict[int, PowerTeamRating] = {}
        for team_id in team_ids:
            idx = team_index[team_id]
            offense_rating = float(offense_coefficients[idx])
            defense_rating = float(defense_coefficients[idx])
            base_power = offense_rating + defense_rating
            feature_bonus = feature_composite.get(team_id, 0.0)
            special_teams_rating = special_teams.get(team_id, 0.0)
            level_code = str(metadata[team_id]["level_code"])
            prior_mean = float(priors.get(team_id, {"prior_mean": DEFAULT_LEVEL_PRIORS[level_code]})["prior_mean"])
            opponent_anchor = (
                opponent_prior_totals[team_id] / opponent_prior_counts[team_id]
                if opponent_prior_counts[team_id] > 0
                else prior_mean
            )
            anchor_mean = 0.65 * prior_mean + 0.35 * opponent_anchor
            if level_code in {"FBS", "FCS"} and team_id in feature_composite:
                raw_power = 0.72 * base_power + 0.22 * feature_bonus + 0.06 * special_teams_rating
            else:
                raw_power = base_power + special_teams_rating

            connectivity = clamp(
                math.log1p(bridge_counts[team_id] + 0.5 * opponent_bridge_scores[team_id]) / math.log(12),
                0.0,
                1.0,
            )
            games_weight = clamp(games_played[team_id] / 12.0, 0.0, 1.0)
            if level_code == "FBS":
                evidence_weight = clamp(0.24 + 0.30 * games_weight + 0.42 * connectivity, 0.24, 0.97)
            elif level_code == "FCS":
                evidence_weight = clamp(0.15 + 0.25 * games_weight + 0.44 * connectivity, 0.15, 0.88)
            else:
                evidence_weight = clamp(0.06 + 0.18 * games_weight + 0.50 * connectivity, 0.06, 0.64)
            final_power = evidence_weight * raw_power + (1.0 - evidence_weight) * anchor_mean

            prior_sd = priors.get(team_id, {"prior_sd": DEFAULT_LEVEL_SIGMA[level_code]})["prior_sd"]
            posterior_sd = max(2.5, prior_sd / math.sqrt(1.0 + 0.85 * games_played[team_id] + 0.35 * bridge_counts[team_id]))
            cross_level_confidence = 100.0 * connectivity * max(0.0, 1.0 - posterior_sd / 10.0)
            team_ratings[team_id] = PowerTeamRating(
                team_id=team_id,
                team_name=str(metadata[team_id]["canonical_name"]),
                level_code=level_code,
                conference_id=int(metadata[team_id]["season_conference_id"]) if metadata[team_id]["season_conference_id"] is not None else None,
                week=week,
                power_rating=final_power,
                offense_rating=offense_rating,
                defense_rating=defense_rating,
                special_teams_rating=special_teams_rating,
                tempo_rating=tempo.get(team_id, 0.0),
                prior_mean=prior_mean,
                posterior_sd=posterior_sd,
                cross_level_confidence=cross_level_confidence,
                schedule_connectivity=connectivity,
            )

        return WeeklyPowerState(week=week, base_points=base_points, home_field_advantage=hfa, team_ratings=team_ratings)

    def _season_team_metadata(self, season: int) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            select distinct
              t.team_id,
              t.canonical_name,
              coalesce(ts.level_code, t.level_code) as level_code,
              ts.conference_id as season_conference_id
            from teams t
            join games g on g.home_team_id = t.team_id or g.away_team_id = t.team_id
            left join team_seasons ts
              on ts.team_id = t.team_id
             and ts.season_year = g.season_year
            where g.season_year = %(season)s
            order by t.team_id
            """,
            {"season": season},
        )

    def _completed_games(self, season: int) -> list[dict[str, Any]]:
        return self.db.query_all(
            """
            select
              g.game_id,
              g.week,
              g.neutral_site,
              g.home_team_id,
              g.away_team_id,
              g.home_points,
              g.away_points,
              coalesce(home_season.level_code, home.level_code) as home_level_code,
              coalesce(away_season.level_code, away.level_code) as away_level_code
            from games g
            join teams home on home.team_id = g.home_team_id
            join teams away on away.team_id = g.away_team_id
            left join team_seasons home_season
              on home_season.team_id = g.home_team_id
             and home_season.season_year = g.season_year
            left join team_seasons away_season
              on away_season.team_id = g.away_team_id
             and away_season.season_year = g.season_year
            where g.season_year = %(season)s
              and g.home_points is not null
              and g.away_points is not null
            order by g.week, g.game_id
            """,
            {"season": season},
        )

    def _tempo_components_by_week(self, season: int, through_week: int) -> dict[int, dict[int, float]]:
        rows = self.db.query_all(
            """
            select g.week, d.offense_team_id as team_id, count(*) as drives, count(distinct d.game_id) as games
            from drives d
            join games g on g.game_id = d.game_id
            where g.season_year = %(season)s
              and g.week <= %(week)s
            group by g.week, d.offense_team_id
            order by g.week, d.offense_team_id
            """,
            {"season": season, "week": through_week},
        )
        by_week: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            by_week.setdefault(int(row["week"]), []).append(row)

        cumulative_drives: dict[int, int] = {}
        cumulative_games: dict[int, int] = {}
        tempo_by_week: dict[int, dict[int, float]] = {}
        for week in range(0, through_week + 1):
            for row in by_week.get(week, []):
                team_id = int(row["team_id"])
                cumulative_drives[team_id] = cumulative_drives.get(team_id, 0) + int(row["drives"] or 0)
                cumulative_games[team_id] = cumulative_games.get(team_id, 0) + int(row["games"] or 0)

            per_game = {
                team_id: cumulative_drives[team_id] / max(1, cumulative_games[team_id])
                for team_id in cumulative_drives
                if cumulative_games.get(team_id, 0) > 0
            }
            if not per_game:
                tempo_by_week[week] = {}
                continue
            values = list(per_game.values())
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            std_dev = math.sqrt(variance) or 1.0
            tempo_by_week[week] = {team_id: (value - mean) / std_dev for team_id, value in per_game.items()}
        return tempo_by_week

    def _prior_only_state(
        self,
        week: int,
        metadata: dict[int, dict[str, Any]],
        priors: dict[int, dict[str, float]],
    ) -> WeeklyPowerState:
        ratings: dict[int, PowerTeamRating] = {}
        for team_id, row in metadata.items():
            level_code = str(row["level_code"])
            prior_mean = priors.get(team_id, {"prior_mean": DEFAULT_LEVEL_PRIORS[level_code], "prior_sd": DEFAULT_LEVEL_SIGMA[level_code]})
            ratings[team_id] = PowerTeamRating(
                team_id=team_id,
                team_name=str(row["canonical_name"]),
                level_code=level_code,
                conference_id=int(row["season_conference_id"]) if row["season_conference_id"] is not None else None,
                week=week,
                power_rating=float(prior_mean["prior_mean"]),
                offense_rating=float(prior_mean["prior_mean"]) / 2.0,
                defense_rating=float(prior_mean["prior_mean"]) / 2.0,
                special_teams_rating=0.0,
                tempo_rating=0.0,
                prior_mean=float(prior_mean["prior_mean"]),
                posterior_sd=float(prior_mean["prior_sd"]),
                cross_level_confidence=0.0,
                schedule_connectivity=0.0,
            )
        return WeeklyPowerState(week=week, base_points=28.0, home_field_advantage=2.3, team_ratings=ratings)

    def _persist_weekly_states(self, model_run_id: int, season: int, weekly_states: dict[int, WeeklyPowerState]) -> None:
        rows: list[dict[str, Any]] = []
        for week, state in weekly_states.items():
            for rating in state.team_ratings.values():
                rows.append(
                    {
                        "model_run_id": model_run_id,
                        "team_id": rating.team_id,
                        "season_year": season,
                        "week": week,
                        "power_rating": rating.power_rating,
                        "offense_rating": rating.offense_rating,
                        "defense_rating": rating.defense_rating,
                        "special_teams_rating": rating.special_teams_rating,
                        "tempo_rating": rating.tempo_rating,
                        "prior_mean": rating.prior_mean,
                        "posterior_sd": rating.posterior_sd,
                        "cross_level_confidence": rating.cross_level_confidence,
                        "schedule_connectivity": rating.schedule_connectivity,
                    }
                )
        self.db.upsert_many("power_ratings_weekly", rows, conflict_columns=["model_run_id", "team_id", "week"])

    def _persist_single_week_state(self, model_run_id: int, season: int, state: WeeklyPowerState) -> None:
        rows = [
            {
                "model_run_id": model_run_id,
                "team_id": rating.team_id,
                "season_year": season,
                "week": state.week,
                "power_rating": rating.power_rating,
                "offense_rating": rating.offense_rating,
                "defense_rating": rating.defense_rating,
                "special_teams_rating": rating.special_teams_rating,
                "tempo_rating": rating.tempo_rating,
                "prior_mean": rating.prior_mean,
                "posterior_sd": rating.posterior_sd,
                "cross_level_confidence": rating.cross_level_confidence,
                "schedule_connectivity": rating.schedule_connectivity,
            }
            for rating in state.team_ratings.values()
        ]
        self.db.upsert_many("power_ratings_weekly", rows, conflict_columns=["model_run_id", "team_id", "week"])

    def _persist_level_and_conference_strength(self, model_run_id: int, state: WeeklyPowerState) -> None:
        level_groups: dict[str, list[float]] = {}
        conference_groups: dict[int, list[float]] = {}
        for rating in state.team_ratings.values():
            level_groups.setdefault(rating.level_code, []).append(rating.power_rating)
            if rating.conference_id is not None:
                conference_groups.setdefault(rating.conference_id, []).append(rating.power_rating)

        self.db.upsert_many(
            "level_strength_weekly",
            [
                {
                    "model_run_id": model_run_id,
                    "level_code": level_code,
                    "level_mean": sum(values) / len(values),
                    "level_sd": _std_dev(values),
                }
                for level_code, values in level_groups.items()
            ],
            conflict_columns=["model_run_id", "level_code"],
        )
        self.db.upsert_many(
            "conference_strength_weekly",
            [
                {
                    "model_run_id": model_run_id,
                    "conference_id": conference_id,
                    "conference_mean": sum(values) / len(values),
                    "conference_sd": _std_dev(values),
                }
                for conference_id, values in conference_groups.items()
            ],
            conflict_columns=["model_run_id", "conference_id"],
        )

    def _persist_game_predictions(self, model_run_id: int, season: int, through_week: int, state: WeeklyPowerState) -> None:
        upcoming_games = self.db.query_all(
            """
            select g.game_id, g.week, g.neutral_site, g.home_team_id, g.away_team_id
            from games g
            where g.season_year = %(season)s
              and g.week >= %(week)s
              and (g.home_points is null or g.away_points is null)
            order by g.week, g.start_time_utc
            """,
            {"season": season, "week": through_week},
        )
        rows: list[dict[str, Any]] = []
        for game in upcoming_games:
            home = state.team_ratings.get(int(game["home_team_id"]))
            away = state.team_ratings.get(int(game["away_team_id"]))
            if home is None or away is None:
                continue
            home_site_bonus = 0.0 if bool(game["neutral_site"]) else state.home_field_advantage
            pace_adjustment = 0.5 * (home.tempo_rating + away.tempo_rating)
            predicted_home_points = state.base_points + home.offense_rating - away.defense_rating + 0.5 * (home.special_teams_rating - away.special_teams_rating) + 0.5 * home_site_bonus + pace_adjustment
            predicted_away_points = state.base_points + away.offense_rating - home.defense_rating + 0.5 * (away.special_teams_rating - home.special_teams_rating) - 0.5 * home_site_bonus + pace_adjustment
            predicted_spread = predicted_home_points - predicted_away_points
            volatility = 14.5
            home_win_probability = _normal_cdf(predicted_spread / volatility)
            rows.append(
                {
                    "model_run_id": model_run_id,
                    "game_id": int(game["game_id"]),
                    "home_power_pre": home.power_rating,
                    "away_power_pre": away.power_rating,
                    "predicted_home_points": predicted_home_points,
                    "predicted_away_points": predicted_away_points,
                    "predicted_spread_home": predicted_spread,
                    "predicted_total": predicted_home_points + predicted_away_points,
                    "home_win_probability": home_win_probability,
                    "upset_probability": min(home_win_probability, 1.0 - home_win_probability),
                    "volatility": volatility,
                }
            )
        if rows:
            self.db.upsert_many("game_predictions", rows, conflict_columns=["model_run_id", "game_id"])

    def _persist_rating_deltas(
        self,
        model_run_id: int,
        season: int,
        through_week: int,
        weekly_states: dict[int, WeeklyPowerState],
    ) -> None:
        games = self.db.query_all(
            """
            select game_id, week, home_team_id, away_team_id
            from games
            where season_year = %(season)s
              and week <= %(week)s
              and home_points is not null
              and away_points is not null
            order by week, game_id
            """,
            {"season": season, "week": through_week},
        )
        rows: list[dict[str, Any]] = []
        for game in games:
            game_week = int(game["week"])
            pre_state = weekly_states[max(0, game_week - 1)]
            post_state = weekly_states[game_week]
            for team_id, opponent_id in (
                (int(game["home_team_id"]), int(game["away_team_id"])),
                (int(game["away_team_id"]), int(game["home_team_id"])),
            ):
                pre = pre_state.team_ratings.get(team_id)
                post = post_state.team_ratings.get(team_id)
                opponent = pre_state.team_ratings.get(opponent_id)
                if pre is None or post is None or opponent is None:
                    continue
                rows.append(
                    {
                        "model_run_id": model_run_id,
                        "game_id": int(game["game_id"]),
                        "team_id": team_id,
                        "pregame_power": pre.power_rating,
                        "postgame_power": post.power_rating,
                        "power_delta": post.power_rating - pre.power_rating,
                        "offense_delta": post.offense_rating - pre.offense_rating,
                        "defense_delta": post.defense_rating - pre.defense_rating,
                        "special_teams_delta": post.special_teams_rating - pre.special_teams_rating,
                        "resume_delta": None,
                        "opponent_quality_effect": opponent.power_rating,
                        "dominance_effect": post.power_rating - pre.power_rating,
                        "garbage_time_discount": 0.0,
                        "location_effect": post.schedule_connectivity - pre.schedule_connectivity,
                        "explanation_json": _json_text(
                            {
                                "pregame_power": round(pre.power_rating, 3),
                                "postgame_power": round(post.power_rating, 3),
                                "opponent_power": round(opponent.power_rating, 3),
                            }
                        ),
                    }
                )
        if rows:
            self.db.upsert_many("team_rating_deltas", rows, conflict_columns=["model_run_id", "game_id", "team_id"])


def _feature_composite(feature_map: dict[int, dict[str, float]]) -> dict[int, float]:
    if not feature_map:
        return {}
    metric_weights = {
        "ppa_off_adj": 2.6,
        "ppa_def_adj": 2.6,
        "success_off_adj": 1.8,
        "success_def_adj": 1.8,
        "explosive_off_adj": 1.2,
        "explosive_def_adj": 1.2,
        "finish_off_adj": 0.9,
        "finish_def_adj": 0.9,
        "field_pos_off_adj": 0.6,
        "field_pos_def_adj": 0.6,
    }
    metric_names = sorted({metric for values in feature_map.values() for metric in values})
    standardized_by_metric: dict[str, dict[int, float]] = {}
    for metric_name in metric_names:
        present = {team_id: values[metric_name] for team_id, values in feature_map.items() if metric_name in values}
        if not present:
            continue
        values = list(present.values())
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        std_dev = math.sqrt(variance) or 1.0
        standardized_by_metric[metric_name] = {team_id: (value - mean) / std_dev for team_id, value in present.items()}

    composite: dict[int, float] = {}
    for team_id in feature_map:
        total = 0.0
        weight_total = 0.0
        for metric_name, weight in metric_weights.items():
            value = standardized_by_metric.get(metric_name, {}).get(team_id)
            if value is None:
                continue
            total += value * weight
            weight_total += abs(weight)
        if weight_total > 0:
            composite[team_id] = total / weight_total * 10.0
    return composite


def _special_teams_component(feature_map: dict[int, dict[str, float]]) -> dict[int, float]:
    if not feature_map:
        return {}
    values = {team_id: features.get("field_pos_off_adj", 0.0) + features.get("field_pos_def_adj", 0.0) for team_id, features in feature_map.items()}
    mean = sum(values.values()) / len(values)
    variance = sum((value - mean) ** 2 for value in values.values()) / len(values)
    std_dev = math.sqrt(variance) or 1.0
    return {team_id: ((value - mean) / std_dev) * 0.75 for team_id, value in values.items()}


def _std_dev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _json_text(payload: dict[str, float]) -> str:
    import json

    return json.dumps(payload)


def _single_value_map(db: Database, sql: str, params: dict[str, Any]) -> dict[int, float]:
    rows = db.query_all(sql, params)
    return {
        int(row["team_id"]): float(row["value"])
        for row in rows
        if row.get("team_id") is not None and row.get("value") is not None
    }


def _season_end_power_map(db: Database, season: int) -> dict[int, float]:
    if season <= 0:
        return {}
    rows = db.query_all(
        """
        select prw.team_id, prw.power_rating
        from power_ratings_weekly prw
        join (
          select team_id, max(week) as max_week
          from power_ratings_weekly
          where season_year = %(season)s
          group by team_id
        ) latest on latest.team_id = prw.team_id and latest.max_week = prw.week
        where prw.season_year = %(season)s
        """,
        {"season": season},
    )
    return {int(row["team_id"]): float(row["power_rating"]) for row in rows}


def _program_baseline_map(db: Database, season: int) -> dict[int, float]:
    rows = db.query_all(
        """
        select prw.season_year, prw.team_id, prw.power_rating
        from power_ratings_weekly prw
        join (
          select season_year, team_id, max(week) as max_week
          from power_ratings_weekly
          where season_year between %(start_season)s and %(end_season)s
          group by season_year, team_id
        ) latest
          on latest.season_year = prw.season_year
         and latest.team_id = prw.team_id
         and latest.max_week = prw.week
        where prw.season_year between %(start_season)s and %(end_season)s
        order by prw.team_id, prw.season_year desc
        """,
        {"start_season": max(1, season - 3), "end_season": season - 1},
    )
    season_weights = {season - 1: 0.65, season - 2: 0.25, season - 3: 0.10}
    weighted_totals: dict[int, float] = {}
    weight_totals: dict[int, float] = {}
    for row in rows:
        team_id = int(row["team_id"])
        season_year = int(row["season_year"])
        weight = float(season_weights.get(season_year, 0.0))
        if weight <= 0:
            continue
        weighted_totals[team_id] = weighted_totals.get(team_id, 0.0) + float(row["power_rating"]) * weight
        weight_totals[team_id] = weight_totals.get(team_id, 0.0) + weight
    return {
        team_id: weighted_totals[team_id] / weight_totals[team_id]
        for team_id in weighted_totals
        if weight_totals.get(team_id, 0.0) > 0.0
    }


def _conference_anchor_map(
    previous_power_map: dict[int, float],
    team_metadata: dict[int, dict[str, Any]],
) -> dict[int, float]:
    conference_values: dict[int, list[float]] = {}
    for team_id, metadata in team_metadata.items():
        conference_id = metadata.get("season_conference_id")
        previous_power = previous_power_map.get(team_id)
        if conference_id is None or previous_power is None:
            continue
        conference_values.setdefault(int(conference_id), []).append(float(previous_power))
    conference_means = {
        conference_id: sum(values) / len(values)
        for conference_id, values in conference_values.items()
        if values
    }
    return {
        team_id: conference_means[int(metadata["season_conference_id"])]
        for team_id, metadata in team_metadata.items()
        if metadata.get("season_conference_id") is not None
        and int(metadata["season_conference_id"]) in conference_means
    }


def _transfer_balance_map(db: Database, season: int) -> dict[int, float]:
    rows = db.query_all(
        """
        select
          team_id,
          sum(balance_points) as value
        from (
          select to_team_id as team_id, coalesce(transfer_points, 1.0) as balance_points
          from transfer_entries
          where season_year = %(season)s
            and to_team_id is not null
          union all
          select from_team_id as team_id, -coalesce(transfer_points, 1.0) as balance_points
          from transfer_entries
          where season_year = %(season)s
            and from_team_id is not null
        ) balances
        group by team_id
        """,
        {"season": season},
    )
    return {
        int(row["team_id"]): float(row["value"])
        for row in rows
        if row.get("team_id") is not None and row.get("value") is not None
    }


def _roster_continuity_map(db: Database, season: int) -> dict[int, float]:
    rows = db.query_all(
        """
        select
          current.team_id,
          cast(sum(case when previous.player_id is not null then 1 else 0 end) as real) / nullif(count(*), 0) as value
        from roster_entries current
        left join roster_entries previous
          on previous.team_id = current.team_id
         and previous.player_id = current.player_id
         and previous.season_year = current.season_year - 1
        where current.season_year = %(season)s
        group by current.team_id
        """,
        {"season": season},
    )
    return {
        int(row["team_id"]): float(row["value"])
        for row in rows
        if row.get("team_id") is not None and row.get("value") is not None
    }


def _level_relative_points(
    raw_values: dict[int, float],
    team_metadata: dict[int, dict[str, Any]],
    amplitude: float,
) -> dict[int, float]:
    if not raw_values:
        return {}
    values_by_level: dict[str, list[float]] = {}
    for team_id, value in raw_values.items():
        level_code = str(team_metadata.get(team_id, {}).get("level_code") or "")
        if not level_code:
            continue
        values_by_level.setdefault(level_code, []).append(float(value))

    means: dict[str, float] = {}
    std_devs: dict[str, float] = {}
    for level_code, values in values_by_level.items():
        if not values:
            continue
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        means[level_code] = mean
        std_devs[level_code] = math.sqrt(variance) or 1.0

    points: dict[int, float] = {}
    for team_id, value in raw_values.items():
        level_code = str(team_metadata.get(team_id, {}).get("level_code") or "")
        if level_code not in means:
            continue
        z_score = (float(value) - means[level_code]) / std_devs[level_code]
        points[team_id] = clamp(z_score, -1.6, 1.6) * amplitude
    return points


def _blend_point_maps(point_maps: list[dict[int, float]]) -> dict[int, float]:
    blended: dict[int, list[float]] = {}
    for point_map in point_maps:
        for team_id, value in point_map.items():
            blended.setdefault(team_id, []).append(float(value))
    return {
        team_id: sum(values) / len(values)
        for team_id, values in blended.items()
        if values
    }


def _priors_match_expected(
    existing: dict[int, dict[str, float]],
    expected: dict[int, dict[str, float]],
) -> bool:
    if existing.keys() != expected.keys():
        return False
    for team_id, expected_values in expected.items():
        existing_values = existing.get(team_id)
        if existing_values is None:
            return False
        if abs(existing_values["prior_mean"] - expected_values["prior_mean"]) > 1e-6:
            return False
        if abs(existing_values["prior_sd"] - expected_values["prior_sd"]) > 1e-6:
            return False
    return True


def _sparse_rating_row(
    offense_index: int,
    defense_index: int,
    hfa_index: int,
    home_flag: float,
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    if home_flag:
        return (offense_index, defense_index, hfa_index), (1.0, -1.0, home_flag)
    return (offense_index, defense_index), (1.0, -1.0)
