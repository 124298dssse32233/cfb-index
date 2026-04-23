from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.models.power import WeeklyPowerState
from cfb_rankings.utils import clamp, poisson_binomial_tail, sigmoid


@dataclass
class ResumeTeamRating:
    team_id: int
    week: int
    resume_score: float
    record_strength_score: float
    performance_over_expectation_score: float
    result_quality_score: float
    best_win_score: float | None
    worst_loss_score: float | None
    schedule_strength_score: float


class ResumeModelRunner:
    def __init__(self, db: Database, model_version: str) -> None:
        self.db = db
        self.model_version = model_version

    def run(self, model_run_id: int, season: int, through_week: int, weekly_states: dict[int, WeeklyPowerState]) -> dict[int, dict[int, ResumeTeamRating]]:
        weekly_resume: dict[int, dict[int, ResumeTeamRating]] = {}
        benchmark_rows_to_store: list[dict[str, Any]] = []

        games = self.db.query_all(
            """
            select
              g.game_id,
              g.week,
              g.neutral_site,
              g.home_team_id,
              g.away_team_id,
              g.home_points,
              g.away_points
            from games g
            where g.season_year = %(season)s
              and g.home_points is not null
              and g.away_points is not null
            order by g.week, g.game_id
            """,
            {"season": season},
        )

        for current_week in range(1, through_week + 1):
            week_start = time.time()
            state = weekly_states[current_week]
            current_games = [game for game in games if int(game["week"]) <= current_week]
            team_ids = sorted(state.team_ratings.keys())
            benchmark_powers = _benchmark_powers(state)
            snapshots: dict[int, ResumeTeamRating] = {}
            raw_record_strength: dict[int, float] = {}
            raw_poe: dict[int, float] = {}
            raw_result_quality: dict[int, float] = {}
            team_best_win: dict[int, float | None] = {}
            team_worst_loss: dict[int, float | None] = {}
            schedule_strength: dict[int, float] = {}
            benchmark_score_rows: list[dict[str, Any]] = []

            games_by_team: dict[int, list[dict[str, Any]]] = {team_id: [] for team_id in team_ids}
            for game in current_games:
                games_by_team[int(game["home_team_id"])].append(_team_perspective(game, int(game["home_team_id"]), int(game["away_team_id"])))
                games_by_team[int(game["away_team_id"])].append(_team_perspective(game, int(game["away_team_id"]), int(game["home_team_id"])))

            for team_id in team_ids:
                team_games = games_by_team[team_id]
                if not team_games:
                    raw_record_strength[team_id] = 0.0
                    raw_poe[team_id] = 0.0
                    raw_result_quality[team_id] = 0.0
                    team_best_win[team_id] = None
                    team_worst_loss[team_id] = None
                    schedule_strength[team_id] = 0.0
                    continue

                actual_wins = sum(1 for game in team_games if game["won"])
                benchmark_scores: dict[str, float] = {}
                average_opp_power = 0.0
                poe_values: list[float] = []
                win_values: list[float] = []
                loss_costs: list[float] = []

                for benchmark_name, benchmark_power in benchmark_powers.items():
                    probabilities = []
                    for game in team_games:
                        site_bonus = 0.0
                        if not game["neutral_site"]:
                            site_bonus = state.home_field_advantage if game["is_home"] else -state.home_field_advantage
                        opponent_power = state.team_ratings[game["opponent_team_id"]].power_rating
                        margin = benchmark_power - opponent_power + site_bonus
                        probabilities.append(_normal_cdf(margin / 14.5))
                    tail_probability = max(poisson_binomial_tail(probabilities, actual_wins), 1e-12)
                    benchmark_scores[benchmark_name] = -math.log10(tail_probability)

                raw_record_strength[team_id] = (
                    0.50 * benchmark_scores["Elite"]
                    + 0.30 * benchmark_scores["Top25"]
                    + 0.20 * benchmark_scores["Top50"]
                )
                if current_week == through_week:
                    benchmark_score_rows.extend(
                        [
                            {
                                "model_run_id": model_run_id,
                                "team_id": team_id,
                                "benchmark_name": benchmark_name,
                                "benchmark_power": benchmark_powers[benchmark_name],
                                "match_or_exceed_prob": 10 ** (-benchmark_score),
                                "score_value": benchmark_score,
                            }
                            for benchmark_name, benchmark_score in benchmark_scores.items()
                        ]
                    )

                for game in team_games:
                    pre_state = weekly_states[max(0, int(game["week"]) - 1)]
                    team_pre_power = pre_state.team_ratings.get(team_id)
                    opponent_pre_power = pre_state.team_ratings.get(game["opponent_team_id"])
                    if team_pre_power is None or opponent_pre_power is None:
                        continue
                    site_bonus = 0.0
                    if not game["neutral_site"]:
                        site_bonus = pre_state.home_field_advantage if game["is_home"] else -pre_state.home_field_advantage
                    expected_margin = team_pre_power.power_rating - opponent_pre_power.power_rating + site_bonus
                    actual_margin = clamp(float(game["margin"]), -28.0, 28.0)
                    residual = clamp(actual_margin - expected_margin, -21.0, 21.0)
                    opp_power = opponent_pre_power.power_rating
                    loc_mult = 1.10 if game["is_away"] else (1.03 if game["neutral_site"] else 0.95)
                    opp_mult = 0.75 + 0.50 * sigmoid(opp_power / 7.0)
                    bad_loss_mult = 1.0
                    if not game["won"] and opp_power < -5.0:
                        bad_loss_mult = 1.50
                    elif not game["won"] and opp_power < 0.0:
                        bad_loss_mult = 1.20
                    poe_values.append(residual * loc_mult * opp_mult * bad_loss_mult)
                    average_opp_power += opp_power

                    if game["won"]:
                        win_value = loc_mult * (
                            0.70 * sigmoid((opp_power - 3.0) / 6.0)
                            + 0.30 * sigmoid((actual_margin - expected_margin) / 7.0)
                        )
                        win_values.append(win_value)
                    else:
                        loss_value = loc_mult * (
                            0.70 * sigmoid((-opp_power - 1.0) / 6.0)
                            + 0.30 * sigmoid((expected_margin - actual_margin) / 7.0)
                        )
                        loss_costs.append(loss_value)

                raw_poe[team_id] = sum(poe_values) / len(poe_values) if poe_values else 0.0
                schedule_strength[team_id] = average_opp_power / len(team_games)
                top_wins = sorted(win_values, reverse=True)[:4]
                top_losses = sorted(loss_costs, reverse=True)[:2]
                team_best_win[team_id] = max(win_values) if win_values else None
                team_worst_loss[team_id] = max(loss_costs) if loss_costs else None
                raw_result_quality[team_id] = 0.60 * _average(top_wins) - 0.90 * _average(top_losses) + 0.30 * _average(win_values + [-value for value in loss_costs])

            rs_z = _z_scores(raw_record_strength)
            poe_z = _z_scores(raw_poe)
            rq_z = _z_scores(raw_result_quality)

            for team_id in team_ids:
                snapshots[team_id] = ResumeTeamRating(
                    team_id=team_id,
                    week=current_week,
                    resume_score=0.50 * rs_z[team_id] + 0.30 * poe_z[team_id] + 0.20 * rq_z[team_id],
                    record_strength_score=raw_record_strength[team_id],
                    performance_over_expectation_score=raw_poe[team_id],
                    result_quality_score=raw_result_quality[team_id],
                    best_win_score=team_best_win[team_id],
                    worst_loss_score=team_worst_loss[team_id],
                    schedule_strength_score=schedule_strength[team_id],
                )
            weekly_resume[current_week] = snapshots
            self._persist_single_week(model_run_id, season, current_week, snapshots)
            print(
                f"[resume] season {season} week {current_week} complete in {time.time() - week_start:.1f}s",
                flush=True,
            )
            if current_week == through_week:
                benchmark_rows_to_store = benchmark_score_rows

        if benchmark_rows_to_store:
            self.db.upsert_many(
                "strength_of_record_benchmarks",
                benchmark_rows_to_store,
                conflict_columns=["model_run_id", "team_id", "benchmark_name"],
            )
        self._update_delta_resume_effect(model_run_id, weekly_resume)
        return weekly_resume

    def _persist_weekly(self, model_run_id: int, season: int, weekly_resume: dict[int, dict[int, ResumeTeamRating]]) -> None:
        rows: list[dict[str, Any]] = []
        for week, snapshots in weekly_resume.items():
            for rating in snapshots.values():
                rows.append(
                    {
                        "model_run_id": model_run_id,
                        "team_id": rating.team_id,
                        "season_year": season,
                        "week": week,
                        "resume_score": rating.resume_score,
                        "record_strength_score": rating.record_strength_score,
                        "performance_over_expectation_score": rating.performance_over_expectation_score,
                        "result_quality_score": rating.result_quality_score,
                        "best_win_score": rating.best_win_score,
                        "worst_loss_score": rating.worst_loss_score,
                        "schedule_strength_score": rating.schedule_strength_score,
                    }
                )
        self.db.upsert_many("resume_ratings_weekly", rows, conflict_columns=["model_run_id", "team_id", "week"])

    def _persist_single_week(
        self,
        model_run_id: int,
        season: int,
        week: int,
        snapshots: dict[int, ResumeTeamRating],
    ) -> None:
        rows = [
            {
                "model_run_id": model_run_id,
                "team_id": rating.team_id,
                "season_year": season,
                "week": week,
                "resume_score": rating.resume_score,
                "record_strength_score": rating.record_strength_score,
                "performance_over_expectation_score": rating.performance_over_expectation_score,
                "result_quality_score": rating.result_quality_score,
                "best_win_score": rating.best_win_score,
                "worst_loss_score": rating.worst_loss_score,
                "schedule_strength_score": rating.schedule_strength_score,
            }
            for rating in snapshots.values()
        ]
        self.db.upsert_many("resume_ratings_weekly", rows, conflict_columns=["model_run_id", "team_id", "week"])

    def _update_delta_resume_effect(self, model_run_id: int, weekly_resume: dict[int, dict[int, ResumeTeamRating]]) -> None:
        rows = self.db.query_all(
            """
            select team_rating_delta_id, team_id, game_id
            from team_rating_deltas
            where model_run_id = %(model_run_id)s
            """,
            {"model_run_id": model_run_id},
        )
        if not rows:
            return
        games = self.db.query_all("select game_id, week from games where game_id in (select game_id from team_rating_deltas where model_run_id = %(model_run_id)s)", {"model_run_id": model_run_id})
        game_week = {int(row["game_id"]): int(row["week"]) for row in games}
        updates: list[dict[str, float | int]] = []
        for row in rows:
            week = game_week.get(int(row["game_id"]))
            if week is None or week <= 0:
                continue
            current_resume = weekly_resume.get(week, {}).get(int(row["team_id"]))
            previous_resume = weekly_resume.get(max(1, week - 1), {}).get(int(row["team_id"]))
            resume_delta = 0.0
            if current_resume is not None and previous_resume is not None:
                resume_delta = current_resume.resume_score - previous_resume.resume_score
            elif current_resume is not None:
                resume_delta = current_resume.resume_score
            updates.append(
                {"resume_delta": resume_delta, "team_rating_delta_id": int(row["team_rating_delta_id"])}
            )
        if updates:
            self.db.execute_many(
                """
                update team_rating_deltas
                set resume_delta = %(resume_delta)s
                where team_rating_delta_id = %(team_rating_delta_id)s
                """,
                updates,
            )


def _benchmark_powers(state: WeeklyPowerState) -> dict[str, float]:
    sorted_powers = sorted((rating.power_rating for rating in state.team_ratings.values()), reverse=True)
    elite_idx = min(4, len(sorted_powers) - 1)
    top25_idx = min(24, len(sorted_powers) - 1)
    top50_idx = min(49, len(sorted_powers) - 1)
    return {
        "Elite": sorted_powers[elite_idx],
        "Top25": sorted_powers[top25_idx],
        "Top50": sorted_powers[top50_idx],
    }


def _team_perspective(game: dict[str, Any], team_id: int, opponent_team_id: int) -> dict[str, Any]:
    is_home = team_id == int(game["home_team_id"])
    team_points = int(game["home_points"]) if is_home else int(game["away_points"])
    opponent_points = int(game["away_points"]) if is_home else int(game["home_points"])
    return {
        "game_id": int(game["game_id"]),
        "week": int(game["week"]),
        "opponent_team_id": opponent_team_id,
        "neutral_site": bool(game["neutral_site"]),
        "is_home": is_home,
        "is_away": not is_home and not bool(game["neutral_site"]),
        "won": team_points > opponent_points,
        "margin": team_points - opponent_points,
    }


def _z_scores(values: dict[int, float]) -> dict[int, float]:
    numbers = list(values.values())
    if not numbers:
        return {}
    mean = sum(numbers) / len(numbers)
    variance = sum((number - mean) ** 2 for number in numbers) / len(numbers)
    std_dev = math.sqrt(variance) or 1.0
    return {team_id: (value - mean) / std_dev for team_id, value in values.items()}


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))
