"""Loaders for Fan Intelligence seed YAML files.

- ``seed_source_registry`` — reads ``seeds/source_registry.yaml`` and upserts
  rows keyed on ``source_id`` (text). Extends the existing source_registry
  rows rather than replacing them.
- ``seed_priority_teams`` — reads ``seeds/priority_teams.yaml`` and upserts
  rows keyed on ``team_id``. Resolves team names → team_id via teams table.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from cfb_rankings.db import Database

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SEEDS_DIR = _REPO_ROOT / "seeds"

_REQUIRED_SOURCE_FIELDS = ("source_id", "tier", "max_publication_form", "cohort_weights")


def _utcnow_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def seed_source_registry(db: Database, path: Path | None = None) -> dict[str, int]:
    path = path or (_SEEDS_DIR / "source_registry.yaml")
    doc = _load_yaml(path)
    sources = doc.get("sources") or []
    if not sources:
        raise ValueError(f"no sources found in {path}")

    inserted = 0
    updated = 0
    for entry in sources:
        missing = [f for f in _REQUIRED_SOURCE_FIELDS if entry.get(f) in (None, "")]
        if missing:
            raise ValueError(f"source {entry.get('source_id')} missing required fields: {missing}")
        source_id = entry["source_id"]
        existing = db.query_one(
            "select source_registry_id from source_registry where source_id = :source_id",
            {"source_id": source_id},
        )
        params = {
            "source_id": source_id,
            "source_name": entry.get("name") or source_id,
            "provider_name": entry.get("platform") or "",
            "source_kind": f"fanintel_tier_{entry['tier'].lower()}",
            "collection_method": entry.get("ingest_method") or "unspecified",
            "terms_profile": entry.get("license") or "unspecified",
            "tier": entry["tier"],
            "ingest_method": entry.get("ingest_method"),
            "terms_url": entry.get("terms_url"),
            "license": entry.get("license"),
            "retention_days": entry.get("retention_days"),
            "cohort_weights": json.dumps(entry["cohort_weights"], sort_keys=True),
            "cohort_weights_rationale": (entry.get("cohort_weights_rationale") or "").strip() or None,
            "cohort_weights_updated_at": _utcnow_iso()[:10],
            "max_publication_form": entry["max_publication_form"],
            "is_active": 1,
            "updated_at": _utcnow_iso(),
        }
        if existing:
            db.execute(
                """
                update source_registry set
                    source_name = :source_name,
                    provider_name = :provider_name,
                    tier = :tier,
                    ingest_method = :ingest_method,
                    terms_url = :terms_url,
                    license = :license,
                    retention_days = :retention_days,
                    cohort_weights = :cohort_weights,
                    cohort_weights_rationale = :cohort_weights_rationale,
                    cohort_weights_updated_at = :cohort_weights_updated_at,
                    max_publication_form = :max_publication_form,
                    is_active = :is_active,
                    updated_at = :updated_at
                where source_id = :source_id
                """,
                params,
            )
            updated += 1
        else:
            params["created_at"] = _utcnow_iso()
            db.execute(
                """
                insert into source_registry (
                    source_id, source_name, provider_name, source_kind,
                    collection_method, terms_profile, tier, ingest_method,
                    terms_url, license, retention_days, cohort_weights,
                    cohort_weights_rationale, cohort_weights_updated_at,
                    max_publication_form, is_active, created_at, updated_at
                ) values (
                    :source_id, :source_name, :provider_name, :source_kind,
                    :collection_method, :terms_profile, :tier, :ingest_method,
                    :terms_url, :license, :retention_days, :cohort_weights,
                    :cohort_weights_rationale, :cohort_weights_updated_at,
                    :max_publication_form, :is_active, :created_at, :updated_at
                )
                """,
                params,
            )
            inserted += 1
    return {"inserted": inserted, "updated": updated, "total": inserted + updated}


def seed_priority_teams(db: Database, path: Path | None = None) -> dict[str, int]:
    path = path or (_SEEDS_DIR / "priority_teams.yaml")
    doc = _load_yaml(path)
    teams = doc.get("teams") or []
    if not teams:
        raise ValueError(f"no teams found in {path}")

    inserted = 0
    updated = 0
    missing_teams: list[str] = []
    for entry in teams:
        name = entry.get("team_name")
        if not name:
            raise ValueError(f"entry missing team_name: {entry}")
        team_row = None
        for col in ("canonical_name", "school_name", "short_name", "slug"):
            team_row = db.query_one(
                f"select team_id from teams where lower({col}) = lower(:name)",
                {"name": name},
            )
            if team_row:
                break
        if not team_row:
            try:
                team_row = db.query_one(
                    "select team_id from team_aliases where lower(alias_name) = lower(:name)",
                    {"name": name},
                )
            except Exception:
                team_row = None
        if not team_row:
            missing_teams.append(name)
            continue

        team_id = team_row["team_id"]
        params: dict[str, Any] = {
            "team_id": team_id,
            "rank_priority": entry.get("rank_priority", 0),
            "reddit_team_sub": entry.get("reddit_team_sub"),
            "reddit_alumni_sub": entry.get("reddit_alumni_sub"),
            "reddit_city_sub": entry.get("reddit_city_sub"),
            "wiki_team_page": entry.get("wiki_team_page"),
            "wiki_coach_page": entry.get("wiki_coach_page"),
            "wiki_qb_page": entry.get("wiki_qb_page"),
            "google_news_query": entry.get("google_news_query"),
            "youtube_team_channel_id": entry.get("youtube_team_channel_id"),
            "youtube_fan_channels": _json_or_none(entry.get("youtube_fan_channels")),
            "bluesky_team_handle": entry.get("bluesky_team_handle"),
            "bluesky_beat_handles": _json_or_none(entry.get("bluesky_beat_handles")),
            "message_board_primary": entry.get("message_board_primary"),
            "message_board_secondary": entry.get("message_board_secondary"),
            "campus_newspaper_feed": entry.get("campus_newspaper_feed"),
            "substack_feeds": _json_or_none(entry.get("substack_feeds")),
            "beat_writer_rss": _json_or_none(entry.get("beat_writer_rss")),
            "athletic_dept_feed": entry.get("athletic_dept_feed"),
            "seatgeek_team_slug": entry.get("seatgeek_team_slug"),
            "twitch_channels": _json_or_none(entry.get("twitch_channels")),
            "sports_radio_shows": _json_or_none(entry.get("sports_radio_shows")),
            "head_coach_bsky": entry.get("head_coach_bsky"),
            "head_coach_ig": entry.get("head_coach_ig"),
            "tiktok_creators": _json_or_none(entry.get("tiktok_creators")),
            "locked_on_rss": entry.get("locked_on_rss"),
            "needs_research": 1 if entry.get("needs_research") else 0,
            "last_config_refresh": entry.get("last_config_refresh") or _utcnow_iso()[:10],
            "updated_at_utc": _utcnow_iso(),
        }

        existing = db.query_one(
            "select team_id from priority_teams where team_id = :team_id",
            {"team_id": team_id},
        )
        if existing:
            db.execute(
                """
                update priority_teams set
                    rank_priority = :rank_priority,
                    reddit_team_sub = :reddit_team_sub,
                    reddit_alumni_sub = :reddit_alumni_sub,
                    reddit_city_sub = :reddit_city_sub,
                    wiki_team_page = :wiki_team_page,
                    wiki_coach_page = :wiki_coach_page,
                    wiki_qb_page = :wiki_qb_page,
                    google_news_query = :google_news_query,
                    youtube_team_channel_id = :youtube_team_channel_id,
                    youtube_fan_channels = :youtube_fan_channels,
                    bluesky_team_handle = :bluesky_team_handle,
                    bluesky_beat_handles = :bluesky_beat_handles,
                    message_board_primary = :message_board_primary,
                    message_board_secondary = :message_board_secondary,
                    campus_newspaper_feed = :campus_newspaper_feed,
                    substack_feeds = :substack_feeds,
                    beat_writer_rss = :beat_writer_rss,
                    athletic_dept_feed = :athletic_dept_feed,
                    seatgeek_team_slug = :seatgeek_team_slug,
                    twitch_channels = :twitch_channels,
                    sports_radio_shows = :sports_radio_shows,
                    head_coach_bsky = :head_coach_bsky,
                    head_coach_ig = :head_coach_ig,
                    tiktok_creators = :tiktok_creators,
                    locked_on_rss = :locked_on_rss,
                    needs_research = :needs_research,
                    last_config_refresh = :last_config_refresh,
                    updated_at_utc = :updated_at_utc
                where team_id = :team_id
                """,
                params,
            )
            updated += 1
        else:
            params["created_at_utc"] = _utcnow_iso()
            db.execute(
                """
                insert into priority_teams (
                    team_id, rank_priority, reddit_team_sub, reddit_alumni_sub,
                    reddit_city_sub, wiki_team_page, wiki_coach_page, wiki_qb_page,
                    google_news_query, youtube_team_channel_id, youtube_fan_channels,
                    bluesky_team_handle, bluesky_beat_handles, message_board_primary,
                    message_board_secondary, campus_newspaper_feed, substack_feeds,
                    beat_writer_rss, athletic_dept_feed, seatgeek_team_slug,
                    twitch_channels, sports_radio_shows, head_coach_bsky,
                    head_coach_ig, tiktok_creators, locked_on_rss, needs_research,
                    last_config_refresh, created_at_utc, updated_at_utc
                ) values (
                    :team_id, :rank_priority, :reddit_team_sub, :reddit_alumni_sub,
                    :reddit_city_sub, :wiki_team_page, :wiki_coach_page, :wiki_qb_page,
                    :google_news_query, :youtube_team_channel_id, :youtube_fan_channels,
                    :bluesky_team_handle, :bluesky_beat_handles, :message_board_primary,
                    :message_board_secondary, :campus_newspaper_feed, :substack_feeds,
                    :beat_writer_rss, :athletic_dept_feed, :seatgeek_team_slug,
                    :twitch_channels, :sports_radio_shows, :head_coach_bsky,
                    :head_coach_ig, :tiktok_creators, :locked_on_rss, :needs_research,
                    :last_config_refresh, :created_at_utc, :updated_at_utc
                )
                """,
                params,
            )
            inserted += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "total": inserted + updated,
        "missing_team_names": missing_teams,
    }


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


__all__ = ["seed_source_registry", "seed_priority_teams"]
