from __future__ import annotations

from dataclasses import dataclass
import math
import random
import time
from typing import Any

from cfb_rankings.clients.cfbd import CfbdClient
from cfb_rankings.db import Database
from cfb_rankings.utils import clamp, normalize_name, sigmoid


HEISMAN_STATS_CATEGORIES = (
    "passing",
    "rushing",
    "receiving",
    "defensive",
    "interceptions",
    "fumbles",
    "kickReturns",
    "puntReturns",
    "kicking",
    "punting",
)

G5_CONFERENCES = {
    "American Athletic",
    "Conference USA",
    "Mid-American",
    "Mountain West",
    "Sun Belt",
}

POLL_SYSTEM_WEIGHTS = {
    "AP Top 25": 0.40,
    "Coaches Poll": 0.25,
    "Playoff Committee Rankings": 0.35,
}

DEFENSIVE_POSITIONS = {
    "CB",
    "DB",
    "DE",
    "DL",
    "DT",
    "EDGE",
    "FS",
    "ILB",
    "LB",
    "NT",
    "OLB",
    "S",
    "SAF",
    "SS",
}

RUSHING_POSITIONS = {"APB", "ATH", "B", "FB", "HB", "RB", "TB"}
RECEIVING_POSITIONS = {"ATH", "FL", "SE", "SLOT", "TE", "WR"}
SPECIAL_TEAMS_POSITIONS = {"K", "P", "PK"}

FRONT_SEVEN_POSITIONS = {"DE", "DL", "DT", "EDGE", "ILB", "LB", "NT", "OLB"}
SECONDARY_POSITIONS = {"CB", "DB", "FS", "S", "SAF", "SS"}


@dataclass
class CandidateRow:
    player_id: int
    source_player_id: str
    full_name: str
    team_id: int | None
    team_name: str | None
    conference_name: str | None
    position: str | None
    class_year: str | None


class HeismanModelRunner:
    def __init__(self, db: Database, model_version: str) -> None:
        self.db = db
        self.model_version = model_version

    def backfill_player_context(
        self,
        season: int,
        through_week: int,
        cfbd_client: CfbdClient,
        include_rankings: bool = True,
        include_usage: bool = True,
        include_value_metrics: bool = True,
        skip_if_present: bool = True,
    ) -> dict[str, int]:
        start_time = time.time()
        summary = {
            "season": season,
            "through_week": through_week,
            "rankings": 0,
            "season_stats": 0,
            "usage": 0,
            "value_metrics": 0,
        }
        print(
            f"[player-context] season {season}: refreshing historical player inputs through week {through_week}",
            flush=True,
        )

        if include_rankings:
            should_refresh_rankings = True
            if skip_if_present:
                loaded = self.db.query_one(
                    """
                    select count(*) as row_count
                    from official_rankings
                    where season_year = %(season)s
                      and week = %(week)s
                    """,
                    {"season": season, "week": through_week},
                ) or {}
                should_refresh_rankings = int(loaded.get("row_count") or 0) <= 0
            if should_refresh_rankings:
                before_count = self._table_row_count("official_rankings", season=season, through_week=through_week)
                self._ensure_official_rankings(
                    season=season,
                    through_week=through_week,
                    cfbd_client=cfbd_client,
                )
                after_count = self._table_row_count("official_rankings", season=season, through_week=through_week)
                summary["rankings"] = max(0, after_count - before_count)
            else:
                print(
                    f"[player-context] season {season}: official rankings already loaded for week {through_week}; skipping",
                    flush=True,
                )

        if skip_if_present and self._table_count("player_season_stats", season=season, through_week=through_week) > 0:
            print(
                f"[player-context] season {season}: player season stats already loaded for week {through_week}; skipping",
                flush=True,
            )
        else:
            summary["season_stats"] = self._refresh_player_season_stats(
                cfbd_client=cfbd_client,
                season=season,
                through_week=through_week,
            )

        if include_usage:
            if skip_if_present and self._table_count("player_usage_season", season=season, through_week=through_week) > 0:
                print(
                    f"[player-context] season {season}: player usage already loaded for week {through_week}; skipping",
                    flush=True,
                )
            else:
                summary["usage"] = self._refresh_player_usage(
                    cfbd_client=cfbd_client,
                    season=season,
                    through_week=through_week,
                )

        if include_value_metrics:
            if skip_if_present and self._table_count("player_value_metrics", season=season, through_week=through_week) > 0:
                print(
                    f"[player-context] season {season}: player value metrics already loaded for week {through_week}; skipping",
                    flush=True,
                )
            else:
                summary["value_metrics"] = self._refresh_value_metrics(
                    cfbd_client=cfbd_client,
                    season=season,
                    through_week=through_week,
                )

        print(
            (
                f"[player-context] season {season}: finished in {time.time() - start_time:.1f}s "
                f"(rankings +{summary['rankings']}, "
                f"season stats +{summary['season_stats']}, "
                f"usage +{summary['usage']}, "
                f"value metrics +{summary['value_metrics']})"
            ),
            flush=True,
        )
        return summary

    def run(
        self,
        model_run_id: int,
        season: int,
        through_week: int,
        cfbd_client: CfbdClient | None = None,
    ) -> int:
        start_time = time.time()
        evaluation_week = _heisman_feature_week(through_week)
        latest_loaded_week = self._latest_loaded_week(season)
        self._ensure_player_inputs(
            season=season,
            through_week=evaluation_week,
            latest_loaded_week=latest_loaded_week,
            cfbd_client=cfbd_client,
        )
        if cfbd_client is not None:
            self._ensure_official_rankings(
                season=season,
                through_week=evaluation_week,
                cfbd_client=cfbd_client,
            )
        candidates = self._candidate_rows(season)
        if not candidates:
            print(f"[heisman] no FBS player candidates found for season {season}", flush=True)
            return 0

        team_context = self._team_context(model_run_id=model_run_id, season=season, through_week=evaluation_week)
        poll_visibility_map = self._poll_visibility_map(season=season, through_week=evaluation_week)
        team_defense_map = self._team_defense_map(
            season=season,
            through_week=evaluation_week,
            cfbd_client=cfbd_client,
        )
        stat_map = self._season_stat_map(season=season, through_week=evaluation_week)
        usage_map = self._usage_map(season=season, through_week=evaluation_week)
        value_metric_map = self._value_metric_map(season=season, through_week=evaluation_week)
        market_map = self._market_prior_map(season=season, through_week=evaluation_week)

        scored_candidates = self._score_candidates(
            candidates=candidates,
            team_context=team_context,
            poll_visibility_map=poll_visibility_map,
            team_defense_map=team_defense_map,
            stat_map=stat_map,
            usage_map=usage_map,
            value_metric_map=value_metric_map,
            market_map=market_map,
            through_week=evaluation_week,
        )
        self._persist_rankings(
            model_run_id=model_run_id,
            season=season,
            through_week=through_week,
            scored_candidates=scored_candidates,
        )
        print(
            f"[heisman] season {season} board week {through_week} using inputs through week {evaluation_week} wrote {len(scored_candidates)} rows in {time.time() - start_time:.1f}s",
            flush=True,
        )
        return len(scored_candidates)

    def _latest_loaded_week(self, season: int) -> int:
        row = self.db.query_one(
            """
            select max(week) as week
            from games
            where season_year = %(season)s
              and home_points is not null
              and away_points is not null
            """,
            {"season": season},
        ) or {}
        return int(row.get("week") or 0)

    def _ensure_player_inputs(
        self,
        season: int,
        through_week: int,
        latest_loaded_week: int,
        cfbd_client: CfbdClient | None,
    ) -> None:
        stat_count = self._table_count(
            "player_season_stats",
            season=season,
            through_week=through_week,
        )
        if stat_count <= 0 and cfbd_client is not None:
            self._refresh_player_season_stats(cfbd_client=cfbd_client, season=season, through_week=through_week)

        allow_live_snapshot_features = through_week >= latest_loaded_week
        usage_count = self._table_count("player_usage_season", season=season, through_week=through_week)
        value_metric_count = self._table_count("player_value_metrics", season=season, through_week=through_week)
        if allow_live_snapshot_features and cfbd_client is not None and usage_count <= 0:
            self._refresh_player_usage(cfbd_client=cfbd_client, season=season, through_week=through_week)
        if allow_live_snapshot_features and cfbd_client is not None and value_metric_count <= 0:
            self._refresh_value_metrics(cfbd_client=cfbd_client, season=season, through_week=through_week)

    def _table_count(self, table: str, season: int, through_week: int) -> int:
        row = self.db.query_one(
            f"""
            select count(*) as row_count
            from {table}
            where season_year = %(season)s
              and week = %(week)s
            """,
            {"season": season, "week": through_week},
        ) or {}
        return int(row.get("row_count") or 0)

    def _table_row_count(self, table: str, season: int, through_week: int) -> int:
        if table == "official_rankings":
            row = self.db.query_one(
                """
                select count(*) as row_count
                from official_rankings
                where season_year = %(season)s
                  and week = %(week)s
                """,
                {"season": season, "week": through_week},
            ) or {}
            return int(row.get("row_count") or 0)
        return self._table_count(table, season=season, through_week=through_week)

    def _current_fbs_team_index(self, season: int) -> dict[str, Any]:
        rows = self.db.query_all(
            """
            select
              t.team_id,
              t.canonical_name as team_name,
              tsi.source_team_id,
              tsi.source_team_name,
              coalesce(ts.level_code, t.level_code) as level_code
            from teams t
            left join team_seasons ts
              on ts.team_id = t.team_id
             and ts.season_year = %(season)s
            left join team_source_ids tsi
              on tsi.team_id = t.team_id
             and tsi.source_name = 'cfbd'
            where coalesce(ts.level_code, t.level_code) = 'FBS'
            """,
            {"season": season},
        )
        source_to_team_id: dict[str, int] = {}
        name_to_team_id: dict[str, int] = {}
        fbs_team_ids: set[int] = set()
        for row in rows:
            team_id = int(row["team_id"])
            fbs_team_ids.add(team_id)
            team_name = str(row.get("team_name") or "")
            if team_name:
                name_to_team_id.setdefault(normalize_name(team_name), team_id)
            source_team_name = str(row.get("source_team_name") or "")
            if source_team_name:
                name_to_team_id.setdefault(normalize_name(source_team_name), team_id)
            source_team_id = str(row.get("source_team_id") or "").strip()
            if source_team_id:
                source_to_team_id[source_team_id] = team_id
        return {
            "source_to_team_id": source_to_team_id,
            "name_to_team_id": name_to_team_id,
            "fbs_team_ids": fbs_team_ids,
        }

    def _ensure_official_rankings(
        self,
        season: int,
        through_week: int,
        cfbd_client: CfbdClient,
    ) -> None:
        if through_week <= 0:
            return
        loaded = self.db.query_one(
            """
            select count(*) as row_count
            from official_rankings
            where season_year = %(season)s
              and week = %(week)s
              and ranking_system in ('AP Top 25', 'Coaches Poll', 'Playoff Committee Rankings')
            """,
            {"season": season, "week": through_week},
        ) or {}
        if int(loaded.get("row_count") or 0) > 0:
            return

        team_index = self._current_fbs_team_index(season)
        insert_query = """
            insert into official_rankings (
              team_id,
              season_year,
              week,
              ranking_system,
              region,
              rank_value,
              rating_value
            )
            values (
              :team_id,
              :season_year,
              :week,
              :ranking_system,
              :region,
              :rank_value,
              :rating_value
            )
        """
        for week in range(1, through_week + 1):
            try:
                ranking_weeks = cfbd_client.get_rankings(year=season, week=week, season_type="regular")
            except Exception as exc:
                print(f"[heisman] skipping official rankings week {week}: {exc}", flush=True)
                if _is_restricted_network_error(exc):
                    print(
                        "[heisman] official rankings refresh stopped early because the current environment cannot reach CFBD.",
                        flush=True,
                    )
                    break
                continue
            rows_to_store: list[dict[str, Any]] = []
            for ranking_week in ranking_weeks:
                for poll in ranking_week.get("polls") or []:
                    ranking_system = str(poll.get("poll") or "")
                    if ranking_system not in POLL_SYSTEM_WEIGHTS:
                        continue
                    for rank_row in poll.get("ranks") or []:
                        team_id = None
                        source_team_id = str(rank_row.get("teamId") or "").strip()
                        if source_team_id:
                            team_id = team_index["source_to_team_id"].get(source_team_id)
                        if team_id is None:
                            school = str(rank_row.get("school") or "")
                            team_id = team_index["name_to_team_id"].get(normalize_name(school))
                        if team_id is None or team_id not in team_index["fbs_team_ids"]:
                            continue
                        rows_to_store.append(
                            {
                                "team_id": team_id,
                                "season_year": season,
                                "week": week,
                                "ranking_system": ranking_system,
                                "region": "",
                                "rank_value": _safe_int(rank_row.get("rank")),
                                "rating_value": _safe_float(rank_row.get("points")),
                            }
                        )
            self.db.execute(
                """
                delete from official_rankings
                where season_year = %(season)s
                  and week = %(week)s
                """,
                {"season": season, "week": week},
            )
            if rows_to_store:
                self.db.execute_many(insert_query, rows_to_store)

    def _current_fbs_roster_index(self, season: int) -> dict[str, Any]:
        rows = self.db.query_all(
            """
            with latest_roster as (
              select re.*
              from roster_entries re
              join (
                select player_id, max(roster_entry_id) as roster_entry_id
                from roster_entries
                where season_year = %(season)s
                group by player_id
              ) latest on latest.roster_entry_id = re.roster_entry_id
            )
            select
              re.player_id,
              re.team_id,
              t.canonical_name as team_name,
              coalesce(ts.level_code, t.level_code) as level_code,
              p.full_name,
              psi.source_player_id
            from latest_roster re
            join players p on p.player_id = re.player_id
            join teams t on t.team_id = re.team_id
            left join team_seasons ts
              on ts.team_id = re.team_id
             and ts.season_year = re.season_year
            left join player_source_ids psi
              on psi.player_id = re.player_id
             and psi.source_name = 'cfbd'
            where coalesce(ts.level_code, t.level_code) = 'FBS'
            """,
            {"season": season},
        )
        source_to_player: dict[str, int] = {}
        source_to_team: dict[str, int] = {}
        team_name_to_id: dict[str, int] = {}
        name_team_to_player: dict[tuple[str, str], int] = {}
        fbs_team_ids: set[int] = set()
        for row in rows:
            player_id = int(row["player_id"])
            team_id = int(row["team_id"])
            team_name = str(row.get("team_name") or "")
            fbs_team_ids.add(team_id)
            team_name_to_id.setdefault(normalize_name(team_name), team_id)
            source_player_id = str(row.get("source_player_id") or "").strip()
            if source_player_id:
                source_to_player[source_player_id] = player_id
                source_to_team[source_player_id] = team_id
            name_key = (
                normalize_name(str(row.get("full_name") or "")),
                normalize_name(team_name),
            )
            if all(name_key):
                name_team_to_player[name_key] = player_id
        return {
            "source_to_player": source_to_player,
            "source_to_team": source_to_team,
            "team_name_to_id": team_name_to_id,
            "name_team_to_player": name_team_to_player,
            "fbs_team_ids": fbs_team_ids,
        }

    def _refresh_player_season_stats(self, cfbd_client: CfbdClient, season: int, through_week: int) -> int:
        roster_index = self._current_fbs_roster_index(season)
        total_written = 0
        for category in HEISMAN_STATS_CATEGORIES:
            try:
                fetched = cfbd_client.get_player_season_stats(
                    year=season,
                    end_week=through_week,
                    season_type="both",
                    category=category,
                )
                print(f"[heisman] fetched {len(fetched)} player season stat rows for {category}", flush=True)
            except Exception as exc:
                print(f"[heisman] skipping {category} season stats: {exc}", flush=True)
                continue
            rows_to_store: list[dict[str, Any]] = []
            for row in fetched:
                normalized = self._normalize_player_stat_row(
                    row=row,
                    season=season,
                    through_week=through_week,
                    roster_index=roster_index,
                )
                if normalized is not None:
                    rows_to_store.append(normalized)
            deduped = self._dedupe_rows(
                rows_to_store,
                key_fields=["season_year", "week", "season_type", "source_name", "source_player_id", "team_name", "category", "stat_type"],
            )
            if not deduped:
                print(f"[heisman] no FBS-normalized rows for {category}", flush=True)
                continue
            self.db.execute(
                """
                delete from player_season_stats
                where season_year = %(season)s
                  and week = %(week)s
                  and source_name = 'cfbd'
                  and category = %(category)s
                """,
                {"season": season, "week": through_week, "category": category},
            )
            self.db.upsert_many(
                "player_season_stats",
                deduped,
                conflict_columns=["season_year", "week", "season_type", "source_name", "source_player_id", "team_name", "category", "stat_type"],
            )
            total_written += len(deduped)
            print(f"[heisman] wrote {len(deduped)} normalized {category} rows", flush=True)
        if total_written <= 0:
            print(f"[heisman] no FBS season stat rows fetched for season {season} week {through_week}", flush=True)
            return 0
        print(f"[heisman] wrote {total_written} total season stat rows", flush=True)
        return total_written

    def _refresh_player_usage(self, cfbd_client: CfbdClient, season: int, through_week: int) -> int:
        roster_index = self._current_fbs_roster_index(season)
        try:
            fetched = cfbd_client.get_player_usage(year=season)
            print(f"[heisman] fetched {len(fetched)} player usage rows", flush=True)
        except Exception as exc:
            print(f"[heisman] skipping player usage refresh: {exc}", flush=True)
            return 0
        rows_to_store: list[dict[str, Any]] = []
        for row in fetched:
            normalized = self._normalize_usage_row(
                row=row,
                season=season,
                through_week=through_week,
                roster_index=roster_index,
            )
            if normalized is not None:
                rows_to_store.append(normalized)
        deduped = self._dedupe_rows(
            rows_to_store,
            key_fields=["season_year", "week", "source_name", "source_player_id", "team_name"],
        )
        if not deduped:
            return 0
        self.db.execute(
            """
            delete from player_usage_season
            where season_year = %(season)s
              and week = %(week)s
              and source_name = 'cfbd'
            """,
            {"season": season, "week": through_week},
        )
        self.db.upsert_many(
            "player_usage_season",
            deduped,
            conflict_columns=["season_year", "week", "source_name", "source_player_id", "team_name"],
        )
        print(f"[heisman] wrote {len(deduped)} normalized player usage rows", flush=True)
        return len(deduped)

    def _refresh_value_metrics(self, cfbd_client: CfbdClient, season: int, through_week: int) -> int:
        roster_index = self._current_fbs_roster_index(season)
        metric_sources = [
            ("wepa_passing", cfbd_client.get_player_passing_wepa),
            ("wepa_rushing", cfbd_client.get_player_rushing_wepa),
        ]
        total_written = 0
        for metric_name, fetcher in metric_sources:
            try:
                fetched = fetcher(year=season)
                print(f"[heisman] fetched {len(fetched)} {metric_name} rows", flush=True)
            except Exception as exc:
                print(f"[heisman] skipping {metric_name}: {exc}", flush=True)
                continue
            rows_to_store: list[dict[str, Any]] = []
            for row in fetched:
                normalized = self._normalize_value_metric_row(
                    row=row,
                    season=season,
                    through_week=through_week,
                    roster_index=roster_index,
                    metric_name=metric_name,
                )
                if normalized is not None:
                    rows_to_store.append(normalized)
            deduped = self._dedupe_rows(
                rows_to_store,
                key_fields=["season_year", "week", "source_name", "metric_name", "source_player_id", "team_name"],
            )
            if not deduped:
                continue
            self.db.execute(
                """
                delete from player_value_metrics
                where season_year = %(season)s
                  and week = %(week)s
                  and source_name = 'cfbd'
                  and metric_name = %(metric_name)s
                """,
                {"season": season, "week": through_week, "metric_name": metric_name},
            )
            self.db.upsert_many(
                "player_value_metrics",
                deduped,
                conflict_columns=["season_year", "week", "source_name", "metric_name", "source_player_id", "team_name"],
            )
            total_written += len(deduped)
            print(f"[heisman] wrote {len(deduped)} normalized {metric_name} rows", flush=True)
        return total_written

    def _normalize_player_stat_row(
        self,
        row: dict[str, Any],
        season: int,
        through_week: int,
        roster_index: dict[str, Any],
    ) -> dict[str, Any] | None:
        source_player_id = str(row.get("playerId") or "").strip()
        team_name = str(row.get("team") or "").strip()
        player_name = str(row.get("player") or "").strip()
        team_key = normalize_name(team_name)
        player_id = roster_index["source_to_player"].get(source_player_id)
        if player_id is None and player_name and team_key:
            player_id = roster_index["name_team_to_player"].get((normalize_name(player_name), team_key))
        if player_id is None:
            return None
        team_id = roster_index["source_to_team"].get(source_player_id) or roster_index["team_name_to_id"].get(team_key)
        if team_id is None or team_id not in roster_index["fbs_team_ids"]:
            return None
        stat_text = str(row.get("stat") or "")
        return {
            "season_year": season,
            "week": through_week,
            "season_type": "both",
            "player_id": player_id,
            "team_id": team_id,
            "source_name": "cfbd",
            "source_player_id": source_player_id,
            "team_name": team_name,
            "player_name": player_name,
            "conference_name": str(row.get("conference") or ""),
            "position": str(row.get("position") or ""),
            "category": str(row.get("category") or ""),
            "stat_type": str(row.get("statType") or ""),
            "stat_value_text": stat_text,
            "stat_value_num": _safe_float(stat_text),
        }

    def _normalize_usage_row(
        self,
        row: dict[str, Any],
        season: int,
        through_week: int,
        roster_index: dict[str, Any],
    ) -> dict[str, Any] | None:
        source_player_id = str(row.get("id") or "").strip()
        team_name = str(row.get("team") or "").strip()
        player_id = roster_index["source_to_player"].get(source_player_id)
        team_id = roster_index["source_to_team"].get(source_player_id) or roster_index["team_name_to_id"].get(normalize_name(team_name))
        if player_id is None or team_id is None or team_id not in roster_index["fbs_team_ids"]:
            return None
        usage = row.get("usage") or {}
        return {
            "season_year": season,
            "week": through_week,
            "player_id": player_id,
            "team_id": team_id,
            "source_name": "cfbd",
            "source_player_id": source_player_id,
            "team_name": team_name,
            "player_name": str(row.get("name") or ""),
            "conference_name": str(row.get("conference") or ""),
            "position": str(row.get("position") or ""),
            "usage_overall": _safe_float(usage.get("overall")),
            "usage_pass": _safe_float(usage.get("pass")),
            "usage_rush": _safe_float(usage.get("rush")),
            "usage_first_down": _safe_float(usage.get("firstDown")),
            "usage_second_down": _safe_float(usage.get("secondDown")),
            "usage_third_down": _safe_float(usage.get("thirdDown")),
            "usage_standard_downs": _safe_float(usage.get("standardDowns")),
            "usage_passing_downs": _safe_float(usage.get("passingDowns")),
        }

    def _normalize_value_metric_row(
        self,
        row: dict[str, Any],
        season: int,
        through_week: int,
        roster_index: dict[str, Any],
        metric_name: str,
    ) -> dict[str, Any] | None:
        source_player_id = str(row.get("athleteId") or "").strip()
        team_name = str(row.get("team") or "").strip()
        player_id = roster_index["source_to_player"].get(source_player_id)
        if player_id is None:
            return None
        team_id = roster_index["source_to_team"].get(source_player_id) or roster_index["team_name_to_id"].get(normalize_name(team_name))
        if team_id is None or team_id not in roster_index["fbs_team_ids"]:
            return None
        return {
            "season_year": season,
            "week": through_week,
            "player_id": player_id,
            "team_id": team_id,
            "source_name": "cfbd",
            "source_player_id": source_player_id,
            "team_name": team_name,
            "player_name": str(row.get("athleteName") or ""),
            "conference_name": str(row.get("conference") or ""),
            "position": str(row.get("position") or ""),
            "metric_name": metric_name,
            "metric_value": _safe_float(row.get("wepa")),
            "plays": _safe_int(row.get("plays")),
        }

    def _candidate_rows(self, season: int) -> list[CandidateRow]:
        rows = self.db.query_all(
            """
            with current_roster as (
              select re.*
              from roster_entries re
              join (
                select player_id, max(roster_entry_id) as roster_entry_id
                from roster_entries
                where season_year = %(season)s
                group by player_id
              ) latest on latest.roster_entry_id = re.roster_entry_id
            )
            select
              p.player_id,
              p.full_name,
              psi.source_player_id,
              re.team_id,
              t.canonical_name as team_name,
              c.conference_name,
              coalesce(re.position, p.position) as position,
              re.class_year
            from current_roster re
            join players p on p.player_id = re.player_id
            join teams t on t.team_id = re.team_id
            left join team_seasons ts
              on ts.team_id = re.team_id
             and ts.season_year = re.season_year
            left join conferences c on c.conference_id = ts.conference_id
            left join player_source_ids psi
              on psi.player_id = p.player_id
             and psi.source_name = 'cfbd'
            where coalesce(ts.level_code, t.level_code) = 'FBS'
            order by lower(t.canonical_name), lower(p.full_name)
            """,
            {"season": season},
        )
        return [
            CandidateRow(
                player_id=int(row["player_id"]),
                source_player_id=str(row.get("source_player_id") or ""),
                full_name=str(row.get("full_name") or "Player"),
                team_id=None if row.get("team_id") is None else int(row["team_id"]),
                team_name=None if row.get("team_name") is None else str(row["team_name"]),
                conference_name=None if row.get("conference_name") is None else str(row["conference_name"]),
                position=None if row.get("position") is None else str(row["position"]),
                class_year=None if row.get("class_year") is None else str(row["class_year"]),
            )
            for row in rows
        ]

    def _team_context(self, model_run_id: int, season: int, through_week: int) -> dict[int, dict[str, float | int | str | None]]:
        rows = self.db.query_all(
            """
            with team_results as (
              select
                g.home_team_id as team_id,
                case when g.home_points > g.away_points then 1 else 0 end as win_flag
              from games g
              where g.season_year = %(season)s
                and g.week <= %(week)s
                and g.home_points is not null
                and g.away_points is not null
              union all
              select
                g.away_team_id as team_id,
                case when g.away_points > g.home_points then 1 else 0 end as win_flag
              from games g
              where g.season_year = %(season)s
                and g.week <= %(week)s
                and g.home_points is not null
                and g.away_points is not null
            )
            select
              p.team_id,
              p.power_rating,
              r.resume_score,
              t.canonical_name as team_name,
              c.conference_name,
              sum(coalesce(tr.win_flag, 0)) as wins,
              count(tr.team_id) as games
            from power_ratings_weekly p
            join teams t on t.team_id = p.team_id
            left join resume_ratings_weekly r
              on r.model_run_id = p.model_run_id
             and r.team_id = p.team_id
             and r.week = p.week
            left join team_seasons ts
              on ts.team_id = p.team_id
             and ts.season_year = p.season_year
            left join conferences c on c.conference_id = ts.conference_id
            left join team_results tr on tr.team_id = p.team_id
            where p.model_run_id = %(model_run_id)s
              and p.season_year = %(season)s
              and p.week = %(week)s
              and coalesce(ts.level_code, t.level_code) = 'FBS'
            group by
              p.team_id,
              p.power_rating,
              r.resume_score,
              t.canonical_name,
              c.conference_name
            """,
            {"model_run_id": model_run_id, "season": season, "week": through_week},
        )
        power_map = {int(row["team_id"]): float(row.get("power_rating") or 0.0) for row in rows}
        resume_map = {
            int(row["team_id"]): 0.0 if row.get("resume_score") is None else float(row["resume_score"])
            for row in rows
        }
        win_pct_map = {
            int(row["team_id"]): (
                float(row.get("wins") or 0) / max(1, int(row.get("games") or 0))
            )
            for row in rows
        }
        power_pct = _all_value_percentiles(power_map)
        resume_pct = _all_value_percentiles(resume_map)
        win_pct_percentiles = _all_value_percentiles(win_pct_map)
        context: dict[int, dict[str, float | int | str | None]] = {}
        for row in rows:
            team_id = int(row["team_id"])
            context[team_id] = {
                "team_name": str(row.get("team_name") or ""),
                "conference_name": None if row.get("conference_name") is None else str(row["conference_name"]),
                "power_rating": power_map[team_id],
                "resume_score": resume_map[team_id],
                "power_percentile": power_pct.get(team_id, 0.5),
                "resume_percentile": resume_pct.get(team_id, 0.5),
                "win_percentile": win_pct_percentiles.get(team_id, 0.5),
                "wins": int(row.get("wins") or 0),
                "games": int(row.get("games") or 0),
            }
        return context

    def _poll_visibility_map(self, season: int, through_week: int) -> dict[int, float]:
        rows = self.db.query_all(
            """
            select
              team_id,
              week,
              ranking_system,
              rank_value
            from official_rankings
            where season_year = %(season)s
              and week <= %(week)s
              and ranking_system in ('AP Top 25', 'Coaches Poll', 'Playoff Committee Rankings')
            """,
            {"season": season, "week": through_week},
        )
        if not rows:
            return {}

        weeks_by_system: dict[str, set[int]] = {}
        for row in rows:
            ranking_system = str(row.get("ranking_system") or "")
            week = int(row.get("week") or 0)
            if ranking_system in POLL_SYSTEM_WEIGHTS and week > 0:
                weeks_by_system.setdefault(ranking_system, set()).add(week)

        if not weeks_by_system:
            return {}

        team_scores: dict[int, dict[str, dict[int, float]]] = {}
        for row in rows:
            ranking_system = str(row.get("ranking_system") or "")
            if ranking_system not in POLL_SYSTEM_WEIGHTS or row.get("team_id") is None:
                continue
            team_id = int(row["team_id"])
            week = int(row.get("week") or 0)
            rank_value = _safe_int(row.get("rank_value"))
            score = _poll_rank_score(rank_value)
            team_scores.setdefault(team_id, {}).setdefault(ranking_system, {})[week] = score

        denominator = sum(weight for system, weight in POLL_SYSTEM_WEIGHTS.items() if weeks_by_system.get(system)) or 1.0
        visibility_map: dict[int, float] = {}
        for team_id, system_scores in team_scores.items():
            latest_score = 0.0
            sustained_score = 0.0
            top_ten_share = 0.0
            top_five_share = 0.0
            for system, weight in POLL_SYSTEM_WEIGHTS.items():
                available_weeks = sorted(weeks_by_system.get(system) or [])
                if not available_weeks:
                    continue
                scores = [system_scores.get(system, {}).get(week, 0.0) for week in available_weeks]
                sustained_score += weight * (sum(scores) / len(scores))
                latest_score += weight * scores[-1]
                top_ten_share += weight * (
                    sum(1.0 for score in scores if score >= _poll_rank_score(10)) / len(scores)
                )
                top_five_share += weight * (
                    sum(1.0 for score in scores if score >= _poll_rank_score(5)) / len(scores)
                )
            visibility_map[team_id] = clamp(
                (
                    0.42 * latest_score
                    + 0.33 * sustained_score
                    + 0.17 * top_ten_share
                    + 0.08 * top_five_share
                )
                / denominator,
                0.0,
                1.0,
            )
        return visibility_map

    def _team_defense_map(
        self,
        season: int,
        through_week: int,
        cfbd_client: CfbdClient | None = None,
    ) -> dict[int, dict[str, float]]:
        raw_metrics: dict[int, dict[str, float]] = {}
        if cfbd_client is not None:
            raw_metrics = self._cfbd_team_defense_metrics(
                season=season,
                through_week=through_week,
                cfbd_client=cfbd_client,
            )
        if not raw_metrics:
            raw_metrics = self._local_team_defense_metrics(
                season=season,
                through_week=through_week,
            )
        if not raw_metrics:
            return {}

        overall_ppa_pct = _all_value_percentiles({team_id: -values.get("ppa", 0.0) for team_id, values in raw_metrics.items()})
        overall_success_pct = _all_value_percentiles(
            {team_id: -values.get("success_rate", 0.0) for team_id, values in raw_metrics.items()}
        )
        overall_explosive_pct = _all_value_percentiles(
            {team_id: -values.get("explosiveness", 0.0) for team_id, values in raw_metrics.items()}
        )
        havoc_pct = _all_value_percentiles({team_id: values.get("havoc_total", 0.0) for team_id, values in raw_metrics.items()})
        rush_ppa_pct = _all_value_percentiles({team_id: -values.get("rush_ppa", 0.0) for team_id, values in raw_metrics.items()})
        rush_success_pct = _all_value_percentiles(
            {team_id: -values.get("rush_success_rate", 0.0) for team_id, values in raw_metrics.items()}
        )
        pass_ppa_pct = _all_value_percentiles({team_id: -values.get("pass_ppa", 0.0) for team_id, values in raw_metrics.items()})
        pass_success_pct = _all_value_percentiles(
            {team_id: -values.get("pass_success_rate", 0.0) for team_id, values in raw_metrics.items()}
        )
        front_havoc_pct = _all_value_percentiles(
            {team_id: values.get("havoc_front", 0.0) for team_id, values in raw_metrics.items()}
        )
        db_havoc_pct = _all_value_percentiles({team_id: values.get("havoc_db", 0.0) for team_id, values in raw_metrics.items()})
        stuff_rate_pct = _all_value_percentiles(
            {team_id: values.get("stuff_rate", 0.0) for team_id, values in raw_metrics.items()}
        )

        defense_map: dict[int, dict[str, float]] = {}
        for team_id in raw_metrics:
            overall = (
                0.31 * overall_ppa_pct.get(team_id, 0.5)
                + 0.23 * overall_success_pct.get(team_id, 0.5)
                + 0.18 * overall_explosive_pct.get(team_id, 0.5)
                + 0.16 * havoc_pct.get(team_id, 0.5)
                + 0.12 * pass_ppa_pct.get(team_id, 0.5)
            )
            front = (
                0.30 * front_havoc_pct.get(team_id, 0.5)
                + 0.24 * rush_ppa_pct.get(team_id, 0.5)
                + 0.16 * rush_success_pct.get(team_id, 0.5)
                + 0.12 * stuff_rate_pct.get(team_id, 0.5)
                + 0.18 * overall
            )
            secondary = (
                0.30 * db_havoc_pct.get(team_id, 0.5)
                + 0.25 * pass_ppa_pct.get(team_id, 0.5)
                + 0.17 * pass_success_pct.get(team_id, 0.5)
                + 0.10 * overall_explosive_pct.get(team_id, 0.5)
                + 0.18 * overall
            )
            defense_map[team_id] = {
                "overall": clamp(overall, 0.0, 1.0),
                "front": clamp(front, 0.0, 1.0),
                "secondary": clamp(secondary, 0.0, 1.0),
            }
        return defense_map

    def _cfbd_team_defense_metrics(
        self,
        season: int,
        through_week: int,
        cfbd_client: CfbdClient,
    ) -> dict[int, dict[str, float]]:
        team_index = self._current_fbs_team_index(season)
        try:
            rows = cfbd_client.get_advanced_season_stats(
                year=season,
                start_week=1,
                end_week=through_week,
                exclude_garbage_time=True,
            )
        except Exception as exc:
            print(f"[heisman] skipping CFBD team defense context: {exc}", flush=True)
            return {}

        metrics: dict[int, dict[str, float]] = {}
        for row in rows:
            team_name = str(row.get("team") or "")
            team_id = team_index["name_to_team_id"].get(normalize_name(team_name))
            if team_id is None:
                continue
            defense = row.get("defense") or {}
            havoc = defense.get("havoc") or {}
            rushing = defense.get("rushingPlays") or {}
            passing = defense.get("passingPlays") or {}
            metrics[team_id] = {
                "ppa": float(defense.get("ppa") or 0.0),
                "success_rate": float(defense.get("successRate") or 0.0),
                "explosiveness": float(defense.get("explosiveness") or 0.0),
                "havoc_total": float(havoc.get("total") or 0.0),
                "havoc_front": float(havoc.get("frontSeven") or 0.0),
                "havoc_db": float(havoc.get("db") or 0.0),
                "rush_ppa": float(rushing.get("ppa") or 0.0),
                "rush_success_rate": float(rushing.get("successRate") or 0.0),
                "pass_ppa": float(passing.get("ppa") or 0.0),
                "pass_success_rate": float(passing.get("successRate") or 0.0),
                "stuff_rate": float(defense.get("stuffRate") or 0.0),
            }
        return metrics

    def _local_team_defense_metrics(self, season: int, through_week: int) -> dict[int, dict[str, float]]:
        rows = self.db.query_all(
            """
            select
              tgas.team_id,
              avg(tgas.defense_ppa) as ppa,
              avg(tgas.success_rate_def) as success_rate,
              avg(tgas.explosiveness_def) as explosiveness,
              avg(tgas.havoc_def) as havoc_total,
              avg(tgas.rushing_ppa_def) as rush_ppa,
              avg(tgas.passing_ppa_def) as pass_ppa
            from team_game_advanced_stats tgas
            join games g on g.game_id = tgas.game_id
            join teams t on t.team_id = tgas.team_id
            left join team_seasons ts
              on ts.team_id = tgas.team_id
             and ts.season_year = g.season_year
            where g.season_year = %(season)s
              and g.week <= %(week)s
              and coalesce(ts.level_code, t.level_code) = 'FBS'
            group by tgas.team_id
            """,
            {"season": season, "week": through_week},
        )
        metrics: dict[int, dict[str, float]] = {}
        for row in rows:
            team_id = int(row["team_id"])
            success_rate = float(row.get("success_rate") or 0.0)
            havoc_total = float(row.get("havoc_total") or 0.0)
            metrics[team_id] = {
                "ppa": float(row.get("ppa") or 0.0),
                "success_rate": success_rate,
                "explosiveness": float(row.get("explosiveness") or 0.0),
                "havoc_total": havoc_total,
                "havoc_front": havoc_total,
                "havoc_db": havoc_total,
                "rush_ppa": float(row.get("rush_ppa") or 0.0),
                "rush_success_rate": success_rate,
                "pass_ppa": float(row.get("pass_ppa") or 0.0),
                "pass_success_rate": success_rate,
                "stuff_rate": 0.0,
            }
        return metrics

    def _season_stat_map(self, season: int, through_week: int) -> dict[int, dict[str, float]]:
        rows = self.db.query_all(
            """
            select
              player_id,
              category,
              stat_type,
              stat_value_num
            from player_season_stats
            where season_year = %(season)s
              and week = %(week)s
            """,
            {"season": season, "week": through_week},
        )
        stats_by_player: dict[int, dict[str, float]] = {}
        for row in rows:
            if row.get("player_id") is None:
                continue
            player_id = int(row["player_id"])
            category = str(row.get("category") or "")
            stat_type = str(row.get("stat_type") or "")
            key = _stat_key(category, stat_type)
            if key is None:
                continue
            stats_by_player.setdefault(player_id, {})[key] = float(row.get("stat_value_num") or 0.0)
        return stats_by_player

    def _usage_map(self, season: int, through_week: int) -> dict[int, dict[str, float]]:
        rows = self.db.query_all(
            """
            select
              player_id,
              usage_overall,
              usage_pass,
              usage_rush,
              usage_first_down,
              usage_second_down,
              usage_third_down,
              usage_standard_downs,
              usage_passing_downs
            from player_usage_season
            where season_year = %(season)s
              and week = %(week)s
            """,
            {"season": season, "week": through_week},
        )
        usage_by_player: dict[int, dict[str, float]] = {}
        for row in rows:
            if row.get("player_id") is None:
                continue
            player_id = int(row["player_id"])
            usage_by_player[player_id] = {
                "usage_overall": float(row.get("usage_overall") or 0.0),
                "usage_pass": float(row.get("usage_pass") or 0.0),
                "usage_rush": float(row.get("usage_rush") or 0.0),
                "usage_first_down": float(row.get("usage_first_down") or 0.0),
                "usage_second_down": float(row.get("usage_second_down") or 0.0),
                "usage_third_down": float(row.get("usage_third_down") or 0.0),
                "usage_standard_downs": float(row.get("usage_standard_downs") or 0.0),
                "usage_passing_downs": float(row.get("usage_passing_downs") or 0.0),
            }
        return usage_by_player

    def _value_metric_map(self, season: int, through_week: int) -> dict[int, dict[str, float]]:
        rows = self.db.query_all(
            """
            select
              player_id,
              metric_name,
              metric_value,
              plays
            from player_value_metrics
            where season_year = %(season)s
              and week = %(week)s
            """,
            {"season": season, "week": through_week},
        )
        metrics_by_player: dict[int, dict[str, float]] = {}
        for row in rows:
            if row.get("player_id") is None:
                continue
            player_id = int(row["player_id"])
            metric_name = str(row.get("metric_name") or "")
            player_metrics = metrics_by_player.setdefault(player_id, {})
            player_metrics[metric_name] = float(row.get("metric_value") or 0.0)
            player_metrics[f"{metric_name}_plays"] = float(row.get("plays") or 0.0)
        return metrics_by_player

    def _market_prior_map(self, season: int, through_week: int) -> dict[int, dict[str, Any]]:
        rows = self.db.query_all(
            """
            select
              player_id,
              avg(implied_probability) as implied_probability,
              min(american_odds) as best_american_odds,
              min(provider) as provider
            from heisman_market_odds_weekly
            where season_year = %(season)s
              and week = %(week)s
              and player_id is not null
            group by player_id
            """,
            {"season": season, "week": through_week},
        )
        return {
            int(row["player_id"]): {
                "implied_probability": None
                if row.get("implied_probability") is None
                else float(row["implied_probability"]),
                "american_odds": None
                if row.get("best_american_odds") is None
                else int(row["best_american_odds"]),
                "provider": None if row.get("provider") is None else str(row["provider"]),
            }
            for row in rows
        }

    def _score_candidates(
        self,
        candidates: list[CandidateRow],
        team_context: dict[int, dict[str, float | int | str | None]],
        poll_visibility_map: dict[int, float],
        team_defense_map: dict[int, dict[str, float]],
        stat_map: dict[int, dict[str, float]],
        usage_map: dict[int, dict[str, float]],
        value_metric_map: dict[int, dict[str, float]],
        market_map: dict[int, dict[str, Any]],
        through_week: int,
    ) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []
        for candidate in candidates:
            stats = stat_map.get(candidate.player_id, {})
            usage = usage_map.get(candidate.player_id, {})
            metrics = value_metric_map.get(candidate.player_id, {})
            market = market_map.get(candidate.player_id, {})
            team = team_context.get(candidate.team_id or -1, {})
            position_bucket = _position_bucket(candidate.position)
            prepared.append(
                {
                    "candidate": candidate,
                    "bucket": position_bucket,
                    "defensive_role": _defensive_role(candidate.position),
                    "team_power_percentile": float(team.get("power_percentile") or 0.0),
                    "team_resume_percentile": float(team.get("resume_percentile") or 0.0),
                    "team_win_percentile": float(team.get("win_percentile") or 0.0),
                    "poll_visibility": float(poll_visibility_map.get(candidate.team_id or -1, 0.0)),
                    "team_defense": float(team_defense_map.get(candidate.team_id or -1, {}).get("overall", 0.0)),
                    "team_defense_role": float(
                        team_defense_map.get(candidate.team_id or -1, {}).get(
                            _defensive_context_key(candidate.position),
                            team_defense_map.get(candidate.team_id or -1, {}).get("overall", 0.0),
                        )
                    ),
                    "market_implied_probability": None
                    if market.get("implied_probability") is None
                    else float(market["implied_probability"]),
                    "market_american_odds": market.get("american_odds"),
                    "market_provider": market.get("provider"),
                    "metrics": self._candidate_metric_payload(candidate, stats, usage, metrics),
                }
            )

        percentile_maps = self._metric_percentiles(prepared)
        scored_rows: list[dict[str, Any]] = []
        market_weight = _market_weight(through_week)
        for item in prepared:
            candidate = item["candidate"]
            bucket = str(item["bucket"])
            defensive_role = str(item["defensive_role"])
            metrics = item["metrics"]
            team_power = float(item["team_power_percentile"])
            team_resume = float(item["team_resume_percentile"])
            team_win = float(item["team_win_percentile"])
            poll_visibility = float(item["poll_visibility"])
            team_defense = float(item["team_defense"])
            team_defense_role = float(item["team_defense_role"])
            context_signal = 0.34 * team_power + 0.27 * team_resume + 0.19 * team_win + 0.20 * poll_visibility
            performance_signal = self._performance_signal(bucket, candidate.player_id, percentile_maps, defensive_role)
            turnover_penalty = self._turnover_penalty(bucket, candidate.player_id, percentile_maps)
            market_implied = item["market_implied_probability"]
            market_signal = 0.0 if market_implied is None else clamp(float(market_implied), 0.0, 1.0)
            position_bias = _position_bias(bucket)
            conference_penalty = _conference_penalty(candidate.conference_name, team_power)
            class_bonus = _class_year_bonus(candidate.class_year)
            marquee_bonus = 0.08 if bucket == "QB" and team_power >= 0.90 else 0.0
            if bucket == "DEF":
                defensive_gate = clamp(
                    0.46 * poll_visibility
                    + 0.34 * team_defense
                    + 0.20 * max(team_power, team_resume),
                    0.0,
                    1.0,
                )
                context_signal = (
                    0.18 * team_power
                    + 0.14 * team_resume
                    + 0.12 * team_win
                    + 0.28 * poll_visibility
                    + 0.28 * team_defense
                )
                performance_signal = (
                    0.76 * performance_signal
                    + 0.16 * team_defense_role
                    + 0.08 * poll_visibility
                )
                position_bias = -0.90 + 0.52 * defensive_gate
            nowcast_score = (
                0.72 * performance_signal
                + 0.28 * context_signal
                + position_bias
                + class_bonus
                + conference_penalty
                + marquee_bonus
                - turnover_penalty
                + 0.45 * market_weight * market_signal
            )
            forecast_score = (
                0.60 * performance_signal
                + 0.40 * context_signal
                + position_bias
                + class_bonus
                + conference_penalty
                + marquee_bonus
                - turnover_penalty
                + 1.10 * market_weight * market_signal
            )
            blended_score = 0.68 * nowcast_score + 0.32 * forecast_score
            scored_rows.append(
                {
                    "player_id": candidate.player_id,
                    "team_id": candidate.team_id,
                    "full_name": candidate.full_name,
                    "position": candidate.position,
                    "conference_name": candidate.conference_name,
                    "class_year": candidate.class_year,
                    "nowcast_score": nowcast_score,
                    "forecast_score": forecast_score,
                    "blended_score": blended_score,
                    "latent_score": blended_score * 4.0,
                    "market_implied_probability": market_implied,
                    "market_american_odds": item["market_american_odds"],
                    "market_provider": item["market_provider"],
                }
            )

        overall_order = sorted(
            scored_rows,
            key=lambda row: (-row["blended_score"], -row["forecast_score"], lower_or_empty(row["full_name"])),
        )
        nowcast_order = sorted(
            scored_rows,
            key=lambda row: (-row["nowcast_score"], -row["forecast_score"], lower_or_empty(row["full_name"])),
        )
        forecast_order = sorted(
            scored_rows,
            key=lambda row: (-row["forecast_score"], -row["nowcast_score"], lower_or_empty(row["full_name"])),
        )

        overall_ranks = {row["player_id"]: index for index, row in enumerate(overall_order, start=1)}
        nowcast_ranks = {row["player_id"]: index for index, row in enumerate(nowcast_order, start=1)}
        forecast_ranks = {row["player_id"]: index for index, row in enumerate(forecast_order, start=1)}

        forecast_scores = [float(row["forecast_score"]) for row in forecast_order]
        top_forecast_score = forecast_scores[0] if forecast_scores else 0.0
        contender_rows = [
            row
            for row in forecast_order
            if float(row["forecast_score"]) >= top_forecast_score - _win_probability_score_window(through_week)
        ][: _win_probability_pool_cap(through_week)]
        win_probabilities = _softmax_probabilities(
            contender_rows,
            "forecast_score",
            temperature=_win_probability_temperature(through_week),
        )
        finalist_probabilities = _simulated_top_k_probabilities(
            forecast_order,
            "forecast_score",
            top_k=4,
            score_window=_finalist_score_window(through_week),
            pool_cap=_finalist_pool_cap(through_week),
            noise_scale=_finalist_noise_scale(through_week),
            simulations=_probability_simulation_count(through_week),
            seed=(through_week * 10007) + 41,
        )
        ballot_probabilities = _simulated_top_k_probabilities(
            forecast_order,
            "forecast_score",
            top_k=_ballot_cutoff_rank(through_week),
            score_window=_ballot_score_window(through_week),
            pool_cap=_ballot_pool_cap(through_week),
            noise_scale=_ballot_noise_scale(through_week),
            simulations=_probability_simulation_count(through_week),
            seed=(through_week * 10007) + 79,
        )

        for row in scored_rows:
            player_id = int(row["player_id"])
            row["rank_overall"] = overall_ranks[player_id]
            row["nowcast_rank"] = nowcast_ranks[player_id]
            row["forecast_rank"] = forecast_ranks[player_id]
            row["win_probability"] = win_probabilities.get(player_id, 0.0)
            row["finalist_probability"] = finalist_probabilities.get(player_id, 0.0)
            row["any_ballot_probability"] = ballot_probabilities.get(player_id, 0.0)
            row["expected_ballot_share"] = clamp(
                0.60 * float(row["any_ballot_probability"])
                + 0.25 * float(row["finalist_probability"])
                + 0.15 * float(row["win_probability"]),
                0.0,
                1.0,
            )

        return sorted(scored_rows, key=lambda row: int(row["rank_overall"]))

    def _candidate_metric_payload(
        self,
        candidate: CandidateRow,
        stats: dict[str, float],
        usage: dict[str, float],
        value_metrics: dict[str, float],
    ) -> dict[str, float]:
        return {
            "pass_att": stats.get("passing_att", 0.0),
            "pass_comp": stats.get("passing_completions", 0.0),
            "pass_int": stats.get("passing_int", 0.0),
            "pass_pct": stats.get("passing_pct", 0.0),
            "pass_td": stats.get("passing_td", 0.0),
            "pass_yds": stats.get("passing_yds", 0.0),
            "pass_ypa": stats.get("passing_ypa", 0.0),
            "rush_car": stats.get("rushing_car", 0.0),
            "rush_td": stats.get("rushing_td", 0.0),
            "rush_yds": stats.get("rushing_yds", 0.0),
            "rush_ypc": stats.get("rushing_ypc", 0.0),
            "rec": stats.get("receiving_rec", 0.0),
            "rec_td": stats.get("receiving_td", 0.0),
            "rec_yds": stats.get("receiving_yds", 0.0),
            "rec_ypr": stats.get("receiving_ypr", 0.0),
            "def_pd": stats.get("defensive_pd", 0.0),
            "def_qb_hur": stats.get("defensive_qb_hur", 0.0),
            "def_sacks": stats.get("defensive_sacks", 0.0),
            "def_solo": stats.get("defensive_solo", 0.0),
            "def_td": stats.get("defensive_td", 0.0),
            "def_tfl": stats.get("defensive_tfl", 0.0),
            "def_tot": stats.get("defensive_tot", 0.0),
            "int_avg": stats.get("interceptions_avg", 0.0),
            "int_int": stats.get("interceptions_int", 0.0),
            "int_td": stats.get("interceptions_td", 0.0),
            "int_yds": stats.get("interceptions_yds", 0.0),
            "fum_lost": stats.get("fumbles_lost", 0.0),
            "kick_return_td": stats.get("kickreturns_td", 0.0),
            "kick_return_yds": stats.get("kickreturns_yds", 0.0),
            "punt_return_td": stats.get("puntreturns_td", 0.0),
            "punt_return_yds": stats.get("puntreturns_yds", 0.0),
            "kick_points": stats.get("kicking_pts", 0.0),
            "fgm": stats.get("kicking_fgm", 0.0),
            "fg_pct": stats.get("kicking_pct", 0.0),
            "usage_overall": usage.get("usage_overall", 0.0),
            "usage_pass": usage.get("usage_pass", 0.0),
            "usage_rush": usage.get("usage_rush", 0.0),
            "wepa_passing": value_metrics.get("wepa_passing", 0.0),
            "wepa_rushing": value_metrics.get("wepa_rushing", 0.0),
            "wepa_passing_plays": value_metrics.get("wepa_passing_plays", 0.0),
            "wepa_rushing_plays": value_metrics.get("wepa_rushing_plays", 0.0),
        }

    def _metric_percentiles(self, prepared: list[dict[str, Any]]) -> dict[str, dict[int, float]]:
        metrics_by_name: dict[str, dict[int, float]] = {
            "team_power": {},
            "team_resume": {},
            "team_win": {},
            "turnovers": {},
            "kick_return_td": {},
            "punt_return_td": {},
        }
        bucket_metric_values: dict[str, dict[str, dict[int, float]]] = {
            "QB": {
                "pass_td": {},
                "pass_yds": {},
                "pass_ypa": {},
                "pass_pct": {},
                "rush_td": {},
                "rush_yds": {},
                "usage_overall": {},
                "usage_pass": {},
                "wepa_passing": {},
            },
            "RB": {
                "rush_td": {},
                "rush_yds": {},
                "rush_ypc": {},
                "rec_td": {},
                "rec_yds": {},
                "usage_overall": {},
                "usage_rush": {},
                "wepa_rushing": {},
            },
            "WR": {
                "rec_td": {},
                "rec_yds": {},
                "rec_ypr": {},
                "rush_td": {},
                "rush_yds": {},
                "kick_return_td": {},
                "punt_return_td": {},
                "usage_overall": {},
            },
            "DEF": {
                "def_sacks": {},
                "def_tfl": {},
                "int_int": {},
                "int_td": {},
                "def_td": {},
                "def_pd": {},
                "def_qb_hur": {},
                "def_tot": {},
                "kick_return_td": {},
                "punt_return_td": {},
                "rec_td": {},
                "rec_yds": {},
                "rush_td": {},
            },
            "ST": {
                "kick_points": {},
                "fgm": {},
                "fg_pct": {},
                "kick_return_td": {},
                "punt_return_td": {},
                "kick_return_yds": {},
                "punt_return_yds": {},
            },
            "OTHER": {
                "rush_td": {},
                "rush_yds": {},
                "rec_td": {},
                "rec_yds": {},
            },
        }

        for item in prepared:
            candidate: CandidateRow = item["candidate"]
            player_id = candidate.player_id
            metrics = item["metrics"]
            metrics_by_name["team_power"][player_id] = float(item["team_power_percentile"])
            metrics_by_name["team_resume"][player_id] = float(item["team_resume_percentile"])
            metrics_by_name["team_win"][player_id] = float(item["team_win_percentile"])
            metrics_by_name["turnovers"][player_id] = float(metrics.get("pass_int", 0.0)) + float(metrics.get("fum_lost", 0.0))
            metrics_by_name["kick_return_td"][player_id] = float(metrics.get("kick_return_td", 0.0))
            metrics_by_name["punt_return_td"][player_id] = float(metrics.get("punt_return_td", 0.0))

            bucket = str(item["bucket"])
            target = bucket_metric_values.get(bucket, bucket_metric_values["OTHER"])
            for metric_name in target:
                target[metric_name][player_id] = float(metrics.get(metric_name, 0.0))

        percentile_maps: dict[str, dict[int, float]] = {}
        for bucket, bucket_values in bucket_metric_values.items():
            for metric_name, values in bucket_values.items():
                percentile_maps[f"{bucket}:{metric_name}"] = _positive_value_percentiles(values)
        percentile_maps["turnovers"] = _positive_value_percentiles(metrics_by_name["turnovers"])
        return percentile_maps

    def _performance_signal(
        self,
        bucket: str,
        player_id: int,
        percentile_maps: dict[str, dict[int, float]],
        defensive_role: str = "front",
    ) -> float:
        if bucket == "QB":
            return (
                0.30 * percentile_maps["QB:pass_td"].get(player_id, 0.0)
                + 0.18 * percentile_maps["QB:pass_yds"].get(player_id, 0.0)
                + 0.10 * percentile_maps["QB:pass_ypa"].get(player_id, 0.0)
                + 0.08 * percentile_maps["QB:pass_pct"].get(player_id, 0.0)
                + 0.12 * percentile_maps["QB:rush_td"].get(player_id, 0.0)
                + 0.10 * percentile_maps["QB:rush_yds"].get(player_id, 0.0)
                + 0.07 * percentile_maps["QB:usage_overall"].get(player_id, 0.0)
                + 0.05 * percentile_maps["QB:usage_pass"].get(player_id, 0.0)
                + 0.08 * percentile_maps["QB:wepa_passing"].get(player_id, 0.0)
            )
        if bucket == "RB":
            return (
                0.26 * percentile_maps["RB:rush_td"].get(player_id, 0.0)
                + 0.22 * percentile_maps["RB:rush_yds"].get(player_id, 0.0)
                + 0.10 * percentile_maps["RB:rush_ypc"].get(player_id, 0.0)
                + 0.10 * percentile_maps["RB:rec_yds"].get(player_id, 0.0)
                + 0.08 * percentile_maps["RB:rec_td"].get(player_id, 0.0)
                + 0.08 * percentile_maps["RB:usage_overall"].get(player_id, 0.0)
                + 0.08 * percentile_maps["RB:usage_rush"].get(player_id, 0.0)
                + 0.08 * percentile_maps["RB:wepa_rushing"].get(player_id, 0.0)
            )
        if bucket == "WR":
            return (
                0.30 * percentile_maps["WR:rec_yds"].get(player_id, 0.0)
                + 0.24 * percentile_maps["WR:rec_td"].get(player_id, 0.0)
                + 0.10 * percentile_maps["WR:rec_ypr"].get(player_id, 0.0)
                + 0.07 * percentile_maps["WR:rush_td"].get(player_id, 0.0)
                + 0.05 * percentile_maps["WR:rush_yds"].get(player_id, 0.0)
                + 0.08 * percentile_maps["WR:usage_overall"].get(player_id, 0.0)
                + 0.08 * percentile_maps["WR:kick_return_td"].get(player_id, 0.0)
                + 0.08 * percentile_maps["WR:punt_return_td"].get(player_id, 0.0)
            )
        if bucket == "DEF":
            if defensive_role == "secondary":
                return (
                    0.24 * percentile_maps["DEF:int_int"].get(player_id, 0.0)
                    + 0.15 * percentile_maps["DEF:int_td"].get(player_id, 0.0)
                    + 0.15 * percentile_maps["DEF:def_pd"].get(player_id, 0.0)
                    + 0.10 * percentile_maps["DEF:def_td"].get(player_id, 0.0)
                    + 0.08 * percentile_maps["DEF:def_tot"].get(player_id, 0.0)
                    + 0.08 * percentile_maps["DEF:kick_return_td"].get(player_id, 0.0)
                    + 0.06 * percentile_maps["DEF:punt_return_td"].get(player_id, 0.0)
                    + 0.07 * percentile_maps["DEF:def_qb_hur"].get(player_id, 0.0)
                    + 0.04 * percentile_maps["DEF:rec_td"].get(player_id, 0.0)
                    + 0.03 * percentile_maps["DEF:rec_yds"].get(player_id, 0.0)
                )
            return (
                0.24 * percentile_maps["DEF:def_sacks"].get(player_id, 0.0)
                + 0.21 * percentile_maps["DEF:def_tfl"].get(player_id, 0.0)
                + 0.12 * percentile_maps["DEF:def_qb_hur"].get(player_id, 0.0)
                + 0.11 * percentile_maps["DEF:def_td"].get(player_id, 0.0)
                + 0.10 * percentile_maps["DEF:def_tot"].get(player_id, 0.0)
                + 0.08 * percentile_maps["DEF:int_int"].get(player_id, 0.0)
                + 0.05 * percentile_maps["DEF:int_td"].get(player_id, 0.0)
                + 0.04 * percentile_maps["DEF:kick_return_td"].get(player_id, 0.0)
                + 0.03 * percentile_maps["DEF:punt_return_td"].get(player_id, 0.0)
                + 0.02 * percentile_maps["DEF:rush_td"].get(player_id, 0.0)
            )
        if bucket == "ST":
            return (
                0.22 * percentile_maps["ST:kick_points"].get(player_id, 0.0)
                + 0.18 * percentile_maps["ST:fgm"].get(player_id, 0.0)
                + 0.10 * percentile_maps["ST:fg_pct"].get(player_id, 0.0)
                + 0.18 * percentile_maps["ST:kick_return_td"].get(player_id, 0.0)
                + 0.18 * percentile_maps["ST:punt_return_td"].get(player_id, 0.0)
                + 0.07 * percentile_maps["ST:kick_return_yds"].get(player_id, 0.0)
                + 0.07 * percentile_maps["ST:punt_return_yds"].get(player_id, 0.0)
            )
        return (
            0.35 * percentile_maps["OTHER:rush_td"].get(player_id, 0.0)
            + 0.25 * percentile_maps["OTHER:rush_yds"].get(player_id, 0.0)
            + 0.20 * percentile_maps["OTHER:rec_td"].get(player_id, 0.0)
            + 0.20 * percentile_maps["OTHER:rec_yds"].get(player_id, 0.0)
        )

    def _turnover_penalty(self, bucket: str, player_id: int, percentile_maps: dict[str, dict[int, float]]) -> float:
        turnover_pct = percentile_maps["turnovers"].get(player_id, 0.0)
        if bucket == "QB":
            return 0.12 * turnover_pct
        if bucket in {"RB", "WR", "OTHER"}:
            return 0.06 * turnover_pct
        return 0.0

    def _persist_rankings(
        self,
        model_run_id: int,
        season: int,
        through_week: int,
        scored_candidates: list[dict[str, Any]],
    ) -> None:
        self.db.execute(
            """
            delete from heisman_rankings_weekly
            where season_year = %(season)s
              and week = %(week)s
              and model_run_id = %(model_run_id)s
              and source_name = 'model-heisman'
            """,
            {"season": season, "week": through_week, "model_run_id": model_run_id},
        )
        rows = [
            {
                "season_year": season,
                "week": through_week,
                "player_id": int(row["player_id"]),
                "team_id": row["team_id"],
                "model_run_id": model_run_id,
                "source_name": "model-heisman",
                "rank_overall": int(row["rank_overall"]),
                "nowcast_rank": int(row["nowcast_rank"]),
                "forecast_rank": int(row["forecast_rank"]),
                "latent_score": float(row["latent_score"]),
                "win_probability": float(row["win_probability"]),
                "finalist_probability": float(row["finalist_probability"]),
                "any_ballot_probability": float(row["any_ballot_probability"]),
                "expected_ballot_share": float(row["expected_ballot_share"]),
                "market_implied_probability": row["market_implied_probability"],
                "market_american_odds": row["market_american_odds"],
                "market_provider": row["market_provider"],
                "notes": self.model_version,
            }
            for row in scored_candidates
        ]
        self.db.upsert_many(
            "heisman_rankings_weekly",
            rows,
            conflict_columns=["season_year", "week", "player_id", "model_run_id", "source_name"],
        )

    def _dedupe_rows(self, rows: list[dict[str, Any]], key_fields: list[str]) -> list[dict[str, Any]]:
        deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
        for row in rows:
            deduped[tuple(row.get(field) for field in key_fields)] = row
        return list(deduped.values())


def _position_bucket(position: str | None) -> str:
    normalized = (position or "").strip().upper()
    if normalized == "QB":
        return "QB"
    if normalized in DEFENSIVE_POSITIONS:
        return "DEF"
    if normalized in SPECIAL_TEAMS_POSITIONS:
        return "ST"
    if normalized in RECEIVING_POSITIONS:
        return "WR"
    if normalized in RUSHING_POSITIONS:
        return "RB"
    return "OTHER"


def _defensive_role(position: str | None) -> str:
    normalized = (position or "").strip().upper()
    if normalized in SECONDARY_POSITIONS:
        return "secondary"
    if normalized in FRONT_SEVEN_POSITIONS:
        return "front"
    return "front"


def _defensive_context_key(position: str | None) -> str:
    return "secondary" if _defensive_role(position) == "secondary" else "front"


def _position_bias(bucket: str) -> float:
    return {
        "QB": 0.16,
        "RB": 0.00,
        "WR": -0.08,
        "DEF": -0.68,
        "ST": -1.05,
        "OTHER": -0.35,
    }.get(bucket, -0.35)


def _conference_penalty(conference_name: str | None, team_power: float) -> float:
    if conference_name in G5_CONFERENCES and team_power < 0.82:
        return -0.08
    return 0.0


def _class_year_bonus(class_year: str | None) -> float:
    year = _safe_int(class_year)
    if year is None:
        return 0.0
    if year >= 4:
        return 0.03
    if year == 3:
        return 0.02
    if year <= 1:
        return -0.03
    return 0.0


def _market_weight(through_week: int) -> float:
    if through_week <= 0:
        return 0.60
    if through_week <= 4:
        return 0.45
    if through_week <= 8:
        return 0.28
    return 0.12


def _win_probability_temperature(through_week: int) -> float:
    if through_week <= 4:
        return 0.14
    if through_week <= 8:
        return 0.12
    if through_week <= 12:
        return 0.10
    if through_week <= 16:
        return 0.09
    return 0.08


def _win_probability_score_window(through_week: int) -> float:
    if through_week <= 4:
        return 1.60
    if through_week <= 8:
        return 1.25
    if through_week <= 12:
        return 1.00
    if through_week <= 16:
        return 0.80
    return 0.60


def _win_probability_pool_cap(through_week: int) -> int:
    if through_week <= 4:
        return 120
    if through_week <= 8:
        return 80
    if through_week <= 12:
        return 50
    if through_week <= 16:
        return 30
    return 18


def _heisman_feature_week(through_week: int) -> int:
    # Heisman ballots are cast before bowl season, so late snapshots should freeze
    # at the conference championship / voting window rather than using bowl data.
    return min(through_week, 16)


def _finalist_score_window(through_week: int) -> float:
    if through_week <= 4:
        return 1.80
    if through_week <= 8:
        return 1.40
    if through_week <= 12:
        return 0.90
    if through_week <= 16:
        return 0.62
    return 0.55


def _finalist_pool_cap(through_week: int) -> int:
    if through_week <= 4:
        return 64
    if through_week <= 8:
        return 44
    if through_week <= 12:
        return 18
    if through_week <= 16:
        return 12
    return 10


def _finalist_noise_scale(through_week: int) -> float:
    if through_week <= 4:
        return 0.22
    if through_week <= 8:
        return 0.18
    if through_week <= 12:
        return 0.11
    if through_week <= 16:
        return 0.07
    return 0.06


def _ballot_cutoff_rank(through_week: int) -> int:
    if through_week <= 4:
        return 56
    if through_week <= 8:
        return 42
    if through_week <= 12:
        return 30
    if through_week <= 16:
        return 22
    return 20


def _ballot_score_window(through_week: int) -> float:
    if through_week <= 4:
        return 1.70
    if through_week <= 8:
        return 1.35
    if through_week <= 12:
        return 1.00
    if through_week <= 16:
        return 0.80
    return 0.72


def _ballot_pool_cap(through_week: int) -> int:
    if through_week <= 4:
        return 100
    if through_week <= 8:
        return 72
    if through_week <= 12:
        return 48
    if through_week <= 16:
        return 38
    return 32


def _ballot_noise_scale(through_week: int) -> float:
    if through_week <= 4:
        return 0.18
    if through_week <= 8:
        return 0.14
    if through_week <= 12:
        return 0.11
    if through_week <= 16:
        return 0.08
    return 0.07


def _probability_simulation_count(through_week: int) -> int:
    if through_week <= 4:
        return 2600
    if through_week <= 8:
        return 3200
    if through_week <= 12:
        return 4200
    return 5200


def _poll_rank_score(rank_value: int | None) -> float:
    if rank_value is None or rank_value <= 0:
        return 0.0
    return clamp((26.0 - rank_value) / 25.0, 0.0, 1.0)


def _stat_key(category: str, stat_type: str) -> str | None:
    category_key = category.strip().lower()
    stat_key = stat_type.strip().lower()
    mapping = {
        ("passing", "att"): "passing_att",
        ("passing", "completions"): "passing_completions",
        ("passing", "int"): "passing_int",
        ("passing", "pct"): "passing_pct",
        ("passing", "td"): "passing_td",
        ("passing", "yds"): "passing_yds",
        ("passing", "ypa"): "passing_ypa",
        ("rushing", "car"): "rushing_car",
        ("rushing", "td"): "rushing_td",
        ("rushing", "yds"): "rushing_yds",
        ("rushing", "ypc"): "rushing_ypc",
        ("receiving", "rec"): "receiving_rec",
        ("receiving", "td"): "receiving_td",
        ("receiving", "yds"): "receiving_yds",
        ("receiving", "ypr"): "receiving_ypr",
        ("defensive", "pd"): "defensive_pd",
        ("defensive", "qb hur"): "defensive_qb_hur",
        ("defensive", "sacks"): "defensive_sacks",
        ("defensive", "solo"): "defensive_solo",
        ("defensive", "td"): "defensive_td",
        ("defensive", "tfl"): "defensive_tfl",
        ("defensive", "tot"): "defensive_tot",
        ("interceptions", "avg"): "interceptions_avg",
        ("interceptions", "int"): "interceptions_int",
        ("interceptions", "td"): "interceptions_td",
        ("interceptions", "yds"): "interceptions_yds",
        ("fumbles", "lost"): "fumbles_lost",
        ("kicking", "pts"): "kicking_pts",
        ("kicking", "fgm"): "kicking_fgm",
        ("kicking", "pct"): "kicking_pct",
        ("kickreturns", "td"): "kickreturns_td",
        ("kickreturns", "yds"): "kickreturns_yds",
        ("puntreturns", "td"): "puntreturns_td",
        ("puntreturns", "yds"): "puntreturns_yds",
    }
    return mapping.get((category_key, stat_key))


def _positive_value_percentiles(values_by_player: dict[int, float]) -> dict[int, float]:
    percentile_map = {player_id: 0.0 for player_id in values_by_player}
    positive = [(player_id, value) for player_id, value in values_by_player.items() if value > 0]
    if not positive:
        return percentile_map
    positive.sort(key=lambda item: (item[1], item[0]))
    if len(positive) == 1:
        percentile_map[positive[0][0]] = 1.0
        return percentile_map
    for index, (player_id, _value) in enumerate(positive):
        percentile_map[player_id] = (index + 1) / len(positive)
    return percentile_map


def _all_value_percentiles(values_by_id: dict[int, float]) -> dict[int, float]:
    if not values_by_id:
        return {}
    ordered = sorted(values_by_id.items(), key=lambda item: (item[1], item[0]))
    if len(ordered) == 1:
        return {ordered[0][0]: 1.0}
    percentile_map: dict[int, float] = {}
    for index, (item_id, _value) in enumerate(ordered):
        percentile_map[item_id] = index / (len(ordered) - 1)
    return percentile_map


def _softmax_probabilities(rows: list[dict[str, Any]], score_field: str, temperature: float) -> dict[int, float]:
    if not rows:
        return {}
    scaled_scores = [float(row.get(score_field) or 0.0) for row in rows]
    max_score = max(scaled_scores)
    numerators = [math.exp((score - max_score) / max(temperature, 1e-6)) for score in scaled_scores]
    total = sum(numerators) or 1.0
    return {
        int(row["player_id"]): numerator / total
        for row, numerator in zip(rows, numerators)
    }


def _simulated_top_k_probabilities(
    rows: list[dict[str, Any]],
    score_field: str,
    top_k: int,
    score_window: float,
    pool_cap: int,
    noise_scale: float,
    simulations: int,
    seed: int,
) -> dict[int, float]:
    if not rows or top_k <= 0:
        return {}
    ordered = sorted(
        rows,
        key=lambda row: (-float(row.get(score_field) or 0.0), lower_or_empty(row.get("full_name"))),
    )
    top_score = float(ordered[0].get(score_field) or 0.0)
    pool = [
        row
        for row in ordered
        if float(row.get(score_field) or 0.0) >= top_score - score_window
    ][: max(top_k, pool_cap)]
    if len(pool) <= top_k:
        return {int(row["player_id"]): 1.0 for row in pool}

    counts = {int(row["player_id"]): 0 for row in pool}
    rng = random.Random(seed)
    for _ in range(max(1, simulations)):
        sampled = sorted(
            pool,
            key=lambda row: (
                -(
                    float(row.get(score_field) or 0.0)
                    + noise_scale * _gumbel_noise(rng)
                ),
                lower_or_empty(row.get("full_name")),
            ),
        )[:top_k]
        for row in sampled:
            counts[int(row["player_id"])] += 1
    return {player_id: count / max(1, simulations) for player_id, count in counts.items()}


def _gumbel_noise(rng: random.Random) -> float:
    draw = min(max(rng.random(), 1e-12), 1.0 - 1e-12)
    return -math.log(-math.log(draw))


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def lower_or_empty(value: Any) -> str:
    return str(value or "").lower()


def _is_restricted_network_error(exc: Exception) -> bool:
    text = str(exc)
    return "WinError 10013" in text or "forbidden by its access permissions" in text or "Network access is blocked" in text
