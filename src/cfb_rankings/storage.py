from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.utils import LEVEL_ORDER, normalize_name, season_label, slugify


@dataclass
class TeamIdentity:
    canonical_name: str
    level_code: str
    conference_name: str | None = None
    school_name: str | None = None
    short_name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str = "USA"


def _raw_name_key(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _team_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or slugify(value)


class Repository:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._team_name_cache: dict[str, list[dict[str, Any]]] | None = None

    def seed_levels(self) -> None:
        rows = [
            {"level_code": "FBS", "level_name": "Football Bowl Subdivision", "sort_order": LEVEL_ORDER["FBS"]},
            {"level_code": "FCS", "level_name": "Football Championship Subdivision", "sort_order": LEVEL_ORDER["FCS"]},
            {"level_code": "DII", "level_name": "Division II", "sort_order": LEVEL_ORDER["DII"]},
            {"level_code": "DIII", "level_name": "Division III", "sort_order": LEVEL_ORDER["DIII"]},
        ]
        self.db.upsert_many("levels", rows, conflict_columns=["level_code"], update_columns=["level_name", "sort_order"])

    def ensure_season(self, season_year: int) -> None:
        self.db.execute(
            """
            insert into seasons (season_year, season_label)
            values (%(season_year)s, %(season_label)s)
            on conflict (season_year) do update set season_label = excluded.season_label
            """,
            {"season_year": season_year, "season_label": season_label(season_year)},
        )

    def get_or_create_conference(self, conference_name: str, level_code: str) -> int:
        existing = self.db.query_one(
            """
            select conference_id
            from conferences
            where lower(conference_name) = lower(%(conference_name)s)
              and level_code = %(level_code)s
            """,
            {"conference_name": conference_name, "level_code": level_code},
        )
        if existing:
            return int(existing["conference_id"])

        row = self.db.query_one(
            """
            insert into conferences (conference_name, conference_short_name, level_code)
            values (%(conference_name)s, %(conference_short_name)s, %(level_code)s)
            returning conference_id
            """,
            {
                "conference_name": conference_name,
                "conference_short_name": conference_name,
                "level_code": level_code,
            },
        )
        if row is None:
            raise RuntimeError(f"Failed to create conference: {conference_name}")
        return int(row["conference_id"])

    def get_or_create_team(self, source_name: str, source_team_id: str, identity: TeamIdentity) -> int:
        existing = self.db.query_one(
            """
            select tsi.team_id
            from team_source_ids tsi
            where tsi.source_name = %(source_name)s
              and tsi.source_team_id = %(source_team_id)s
            """,
            {"source_name": source_name, "source_team_id": source_team_id},
        )
        conference_id = (
            self.get_or_create_conference(identity.conference_name, identity.level_code)
            if identity.conference_name
            else None
        )
        slug = _team_slug(identity.canonical_name)

        if existing:
            team_id = int(existing["team_id"])
            self.db.execute(
                """
                update teams
                set canonical_name = %(canonical_name)s,
                    school_name = %(school_name)s,
                    short_name = %(short_name)s,
                    level_code = %(level_code)s,
                    current_conference_id = %(conference_id)s,
                    city = %(city)s,
                    state = %(state)s,
                    country = %(country)s,
                    updated_at = CURRENT_TIMESTAMP
                where team_id = %(team_id)s
                """,
                {
                    "team_id": team_id,
                    "canonical_name": identity.canonical_name,
                    "school_name": identity.school_name or identity.canonical_name,
                    "short_name": identity.short_name or identity.canonical_name,
                    "level_code": identity.level_code,
                    "conference_id": conference_id,
                    "city": identity.city,
                    "state": identity.state,
                    "country": identity.country,
                },
            )
            self._team_name_cache = None
            return team_id

        same_slug = self.db.query_one(
            """
            select team_id, canonical_name, school_name, short_name, level_code
            from teams
            where slug = %(slug)s
            """,
            {"slug": slug},
        )
        if same_slug and self._team_identity_compatible(same_slug, identity):
            team_id = int(same_slug["team_id"])
            self.db.execute(
                """
                update teams
                set canonical_name = %(canonical_name)s,
                    school_name = %(school_name)s,
                    short_name = %(short_name)s,
                    level_code = %(level_code)s,
                    current_conference_id = %(conference_id)s,
                    city = %(city)s,
                    state = %(state)s,
                    country = %(country)s,
                    updated_at = CURRENT_TIMESTAMP
                where team_id = %(team_id)s
                """,
                {
                    "team_id": team_id,
                    "canonical_name": identity.canonical_name,
                    "school_name": identity.school_name or identity.canonical_name,
                    "short_name": identity.short_name or identity.canonical_name,
                    "level_code": identity.level_code,
                    "conference_id": conference_id,
                    "city": identity.city,
                    "state": identity.state,
                    "country": identity.country,
                },
            )
        else:
            unique_slug = self._next_available_team_slug(slug)
            row = self.db.query_one(
                """
                insert into teams (
                  canonical_name,
                  school_name,
                  short_name,
                  slug,
                  level_code,
                  current_conference_id,
                  city,
                  state,
                  country
                )
                values (
                  %(canonical_name)s,
                  %(school_name)s,
                  %(short_name)s,
                  %(slug)s,
                  %(level_code)s,
                  %(conference_id)s,
                  %(city)s,
                  %(state)s,
                  %(country)s
                )
                returning team_id
                """,
                {
                    "canonical_name": identity.canonical_name,
                    "school_name": identity.school_name or identity.canonical_name,
                    "short_name": identity.short_name or identity.canonical_name,
                    "slug": unique_slug,
                    "level_code": identity.level_code,
                    "conference_id": conference_id,
                    "city": identity.city,
                    "state": identity.state,
                    "country": identity.country,
                },
            )
            if row is None:
                raise RuntimeError(f"Failed to create team: {identity.canonical_name}")
            team_id = int(row["team_id"])

        self.db.execute(
            """
            insert into team_source_ids (team_id, source_name, source_team_id, source_team_name, is_primary)
            values (%(team_id)s, %(source_name)s, %(source_team_id)s, %(source_team_name)s, %(is_primary)s)
            on conflict (source_name, source_team_id)
            do update set team_id = excluded.team_id,
                          source_team_name = excluded.source_team_name,
                          is_primary = excluded.is_primary
            """,
            {
                "team_id": team_id,
                "source_name": source_name,
                "source_team_id": source_team_id,
                "source_team_name": identity.canonical_name,
                "is_primary": True,
            },
        )
        self._team_name_cache = None
        return team_id

    def upsert_team_season(
        self,
        team_id: int,
        season_year: int,
        level_code: str,
        conference_name: str | None = None,
    ) -> None:
        self.ensure_season(season_year)
        conference_id = (
            self.get_or_create_conference(conference_name, level_code)
            if conference_name
            else None
        )
        self.db.execute(
            """
            insert into team_seasons (
              team_id,
              season_year,
              level_code,
              conference_id
            )
            values (
              %(team_id)s,
              %(season_year)s,
              %(level_code)s,
              %(conference_id)s
            )
            on conflict (team_id, season_year) do update set
              level_code = excluded.level_code,
              conference_id = coalesce(excluded.conference_id, team_seasons.conference_id)
            """,
            {
                "team_id": team_id,
                "season_year": season_year,
                "level_code": level_code,
                "conference_id": conference_id,
            },
        )

    def find_team_id(self, source_name: str, source_team_id: str) -> int | None:
        row = self.db.query_one(
            """
            select team_id
            from team_source_ids
            where source_name = %(source_name)s and source_team_id = %(source_team_id)s
            """,
            {"source_name": source_name, "source_team_id": source_team_id},
        )
        return int(row["team_id"]) if row else None

    def match_team_by_name(self, team_name: str, level_code: str | None = None) -> int | None:
        normalized = normalize_name(team_name)
        if self._team_name_cache is None:
            self._team_name_cache = {}
            rows = self.db.query_all(
                """
                select team_id, canonical_name, school_name, short_name, level_code
                from teams
                """
            )
            for row in rows:
                self._team_name_cache.setdefault(normalize_name(str(row["canonical_name"])), []).append(row)

        candidates = [
            row for row in self._team_name_cache.get(normalized, [])
            if level_code is None or row["level_code"] == level_code
        ]
        if not candidates:
            return None

        raw_key = _raw_name_key(team_name)
        exact_matches = [row for row in candidates if raw_key in self._team_row_name_keys(row)]
        if len(exact_matches) == 1:
            return int(exact_matches[0]["team_id"])
        if len(candidates) == 1:
            return int(candidates[0]["team_id"])
        return None

    def resolve_game_team_id(self, game_id: int, team_name: str) -> int | None:
        raw_key = _raw_name_key(team_name)
        normalized = normalize_name(team_name)
        participants = self.db.query_all(
            """
            select t.team_id, t.canonical_name, t.school_name, t.short_name
            from games g
            join teams t on t.team_id in (g.home_team_id, g.away_team_id)
            where g.game_id = %(game_id)s
            """,
            {"game_id": game_id},
        )
        if not participants:
            return None

        exact_matches = [row for row in participants if raw_key in self._team_row_name_keys(row)]
        if len(exact_matches) == 1:
            return int(exact_matches[0]["team_id"])

        normalized_matches = [
            row
            for row in participants
            if normalized in {normalize_name(str(row.get("canonical_name") or "")), normalize_name(str(row.get("school_name") or "")), normalize_name(str(row.get("short_name") or ""))}
        ]
        if len(normalized_matches) == 1:
            return int(normalized_matches[0]["team_id"])
        return None

    def get_or_create_game(
        self,
        source_name: str,
        source_game_id: str,
        payload: dict[str, Any],
    ) -> int:
        existing = self.db.query_one(
            """
            select game_id
            from game_source_ids
            where source_name = %(source_name)s
              and source_game_id = %(source_game_id)s
            """,
            {"source_name": source_name, "source_game_id": source_game_id},
        )
        if existing:
            game_id = int(existing["game_id"])
            self.db.execute(
                """
                update games
                set season_year = %(season_year)s,
                    season_type = %(season_type)s,
                    season_phase = %(season_phase)s,
                    week = %(week)s,
                    source_week = %(source_week)s,
                    start_time_utc = %(start_time_utc)s,
                    status = %(status)s,
                    neutral_site = %(neutral_site)s,
                    venue_id = %(venue_id)s,
                    home_team_id = %(home_team_id)s,
                    away_team_id = %(away_team_id)s,
                    home_points = %(home_points)s,
                    away_points = %(away_points)s,
                    attendance = %(attendance)s,
                    notes = %(notes)s,
                    updated_at = CURRENT_TIMESTAMP
                where game_id = %(game_id)s
                """,
                payload | {"game_id": game_id},
            )
            return game_id

        candidate = self.db.query_one(
            """
            select game_id
            from games
            where season_year = %(season_year)s
              and home_team_id = %(home_team_id)s
              and away_team_id = %(away_team_id)s
              and start_time_utc between %(window_start)s and %(window_end)s
            """,
            {
                "season_year": payload["season_year"],
                "home_team_id": payload["home_team_id"],
                "away_team_id": payload["away_team_id"],
                "window_start": payload["start_time_utc"] - timedelta(days=1),
                "window_end": payload["start_time_utc"] + timedelta(days=1),
            },
        )
        if candidate:
            game_id = int(candidate["game_id"])
            self.db.execute(
                """
                update games
                set season_type = %(season_type)s,
                    season_phase = %(season_phase)s,
                    week = %(week)s,
                    source_week = %(source_week)s,
                    start_time_utc = %(start_time_utc)s,
                    status = %(status)s,
                    neutral_site = %(neutral_site)s,
                    venue_id = %(venue_id)s,
                    home_points = %(home_points)s,
                    away_points = %(away_points)s,
                    attendance = %(attendance)s,
                    notes = %(notes)s,
                    updated_at = CURRENT_TIMESTAMP
                where game_id = %(game_id)s
                """,
                payload | {"game_id": game_id},
            )
        else:
            row = self.db.query_one(
                """
                insert into games (
                  season_year, season_type, season_phase, week, source_week, start_time_utc, status, neutral_site,
                  venue_id, home_team_id, away_team_id, home_points, away_points,
                  attendance, notes
                )
                values (
                  %(season_year)s, %(season_type)s, %(season_phase)s, %(week)s, %(source_week)s, %(start_time_utc)s, %(status)s, %(neutral_site)s,
                  %(venue_id)s, %(home_team_id)s, %(away_team_id)s, %(home_points)s, %(away_points)s,
                  %(attendance)s, %(notes)s
                )
                returning game_id
                """,
                payload,
            )
            if row is None:
                raise RuntimeError("Failed to create game")
            game_id = int(row["game_id"])

        self.db.execute(
            """
            insert into game_source_ids (game_id, source_name, source_game_id)
            values (%(game_id)s, %(source_name)s, %(source_game_id)s)
            on conflict (source_name, source_game_id)
            do update set game_id = excluded.game_id
            """,
            {"game_id": game_id, "source_name": source_name, "source_game_id": source_game_id},
        )
        return game_id

    def create_model_run(self, model_name: str, model_version: str, season_year: int, week: int | None, notes: str = "") -> int:
        row = self.db.query_one(
            """
            insert into model_runs (model_name, model_version, season_year, week, data_cutoff_utc, notes)
            values (%(model_name)s, %(model_version)s, %(season_year)s, %(week)s, CURRENT_TIMESTAMP, %(notes)s)
            returning model_run_id
            """,
            {
                "model_name": model_name,
                "model_version": model_version,
                "season_year": season_year,
                "week": week,
                "notes": notes,
            },
        )
        if row is None:
            raise RuntimeError("Failed to create model run")
        return int(row["model_run_id"])

    def all_team_ids_for_season(self, season_year: int) -> list[int]:
        rows = self.db.query_all(
            """
            select distinct t.team_id
            from teams t
            join games g on g.home_team_id = t.team_id or g.away_team_id = t.team_id
            where g.season_year = %(season_year)s
            order by t.team_id
            """,
            {"season_year": season_year},
        )
        return [int(row["team_id"]) for row in rows]

    def seed_team_aliases(self, season_year: int) -> int:
        rows = self.db.query_all(
            """
            select t.team_id, t.canonical_name, t.school_name, t.short_name, tsi.source_team_name
            from teams t
            left join team_source_ids tsi on tsi.team_id = t.team_id
            """
        )
        alias_rows: list[dict[str, Any]] = []
        seen: set[tuple[int, str, str, int]] = set()
        for row in rows:
            team_id = int(row["team_id"])
            candidates = [
                ("canonical", str(row.get("canonical_name") or "")),
                ("school", str(row.get("school_name") or "")),
                ("short", str(row.get("short_name") or "")),
                ("source", str(row.get("source_team_name") or "")),
            ]
            for alias_type, alias_text in candidates:
                cleaned = alias_text.strip()
                normalized = _raw_name_key(cleaned)
                if not cleaned or not normalized:
                    continue
                key = (team_id, normalized, alias_type, season_year)
                if key in seen:
                    continue
                seen.add(key)
                alias_rows.append(
                    {
                        "team_id": team_id,
                        "alias_text": cleaned,
                        "alias_normalized": normalized,
                        "alias_type": alias_type,
                        "season_year": season_year,
                        "source_name": "seed",
                        "is_active": 1,
                    }
                )
        if alias_rows:
            self.db.upsert_many(
                "team_aliases",
                alias_rows,
                conflict_columns=["team_id", "alias_normalized", "alias_type", "season_year"],
                update_columns=["alias_text", "source_name", "is_active"],
            )
        return len(alias_rows)

    def team_aliases_for_season(self, season_year: int, team_id: int) -> list[str]:
        rows = self.db.query_all(
            """
            select alias_text
            from team_aliases
            where team_id = %(team_id)s
              and season_year = %(season_year)s
              and is_active = 1
            order by
              case alias_type
                when 'canonical' then 1
                when 'school' then 2
                when 'short' then 3
                else 4
              end,
              length(alias_text) desc,
              alias_text
            """,
            {"team_id": team_id, "season_year": season_year},
        )
        unique_aliases: list[str] = []
        seen: set[str] = set()
        for row in rows:
            alias = str(row.get("alias_text") or "").strip()
            normalized = _raw_name_key(alias)
            if not alias or not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_aliases.append(alias)
        return unique_aliases

    def repair_team_current_identity_from_latest_season(self) -> int:
        rows = self.db.query_all(
            """
            with latest as (
              select team_id, max(season_year) as latest_season_year
              from team_seasons
              group by team_id
            )
            select
              t.team_id,
              t.level_code as current_level_code,
              t.current_conference_id as current_conference_id,
              ts.level_code as latest_level_code,
              ts.conference_id as latest_conference_id
            from teams t
            join latest on latest.team_id = t.team_id
            join team_seasons ts
              on ts.team_id = t.team_id
             and ts.season_year = latest.latest_season_year
            where coalesce(t.level_code, '') <> coalesce(ts.level_code, '')
               or coalesce(t.current_conference_id, -1) <> coalesce(ts.conference_id, -1)
            """
        )
        if not rows:
            return 0

        update_rows = [
            {
                "team_id": int(row["team_id"]),
                "level_code": str(row.get("latest_level_code") or ""),
                "conference_id": row.get("latest_conference_id"),
            }
            for row in rows
        ]
        self.db.execute_many(
            """
            update teams
            set level_code = :level_code,
                current_conference_id = :conference_id,
                updated_at = CURRENT_TIMESTAMP
            where team_id = :team_id
            """,
            update_rows,
        )
        self._team_name_cache = None
        return len(update_rows)

    def _team_row_name_keys(self, row: dict[str, Any]) -> set[str]:
        return {
            key
            for key in (
                _raw_name_key(str(row.get("canonical_name") or "")),
                _raw_name_key(str(row.get("school_name") or "")),
                _raw_name_key(str(row.get("short_name") or "")),
            )
            if key
        }

    def _team_identity_compatible(self, row: dict[str, Any], identity: TeamIdentity) -> bool:
        if str(row.get("level_code") or "") != identity.level_code:
            return False
        incoming_normalized = normalize_name(identity.canonical_name)
        existing_normalized = normalize_name(str(row.get("canonical_name") or ""))
        if incoming_normalized != existing_normalized:
            return False
        incoming_keys = {
            key
            for key in (
                _raw_name_key(identity.canonical_name),
                _raw_name_key(identity.school_name),
                _raw_name_key(identity.short_name),
            )
            if key
        }
        return bool(self._team_row_name_keys(row) & incoming_keys)

    def _next_available_team_slug(self, base_slug: str) -> str:
        slug = base_slug
        suffix = 2
        while self.db.query_one("select team_id from teams where slug = %(slug)s", {"slug": slug}):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug
