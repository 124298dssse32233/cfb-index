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
            # Preserve operator-set is_active flag on update (so manual
            # deactivations via SQL / CLI survive a re-seed). Only inserts
            # default is_active=1.
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


_FAMILY_TO_TEMPLATE: dict[str, str] = {
    "board": "board_template",
    "campus": "campus_template",
    "substack": "substack_template",
    "beat": "beat_template",
    "athletics": "athletics_template",
    "locked_on": "locked_on_template",
    "radio": "radio_template",
    "google_news": "beat_template",  # Google News aggregates inherit beat cohort weights
}


def seed_source_instances(db: Database) -> dict[str, int]:
    """Expand template rows into per-team source_registry rows.

    For each priority_teams row and each supported family where a corresponding
    seed/handle exists (e.g. priority_teams.campus_newspaper_feed), insert a
    per-team source_registry row whose cohort_weights inherit from the
    ``{family}_template`` row. Idempotent (upsert on the generated source_id).
    """
    teams = db.query_all("""
        select pt.team_id, pt.rank_priority, t.canonical_name, t.slug,
               pt.message_board_primary, pt.campus_newspaper_feed,
               pt.beat_writer_rss, pt.substack_feeds, pt.athletic_dept_feed,
               pt.locked_on_rss, pt.sports_radio_shows, pt.google_news_query
        from priority_teams pt
        join teams t on t.team_id = pt.team_id
    """)
    templates: dict[str, dict[str, Any]] = {}
    for tmpl in db.query_all(
        "select source_id, tier, cohort_weights, cohort_weights_rationale, "
        "max_publication_form, ingest_method, license, retention_days "
        "from source_registry where source_id like '%\\_template' escape '\\'"
    ):
        templates[tmpl["source_id"]] = tmpl

    inserted = 0
    updated = 0
    skipped_no_template = 0

    for team in teams:
        team_slug = (team.get("slug") or team.get("canonical_name") or "").lower().replace(" ", "-")
        if not team_slug:
            continue
        # Check each family signal and, if present, instantiate a per-team source row.
        instances: list[tuple[str, str]] = []  # (family, concrete_source_id)
        if team.get("message_board_primary"):
            instances.append(("board", f"board_{team_slug}"))
        if team.get("campus_newspaper_feed"):
            instances.append(("campus", f"campus_{team_slug}"))
        if team.get("athletic_dept_feed"):
            instances.append(("athletics", f"athletics_{team_slug}"))
        if team.get("locked_on_rss"):
            instances.append(("locked_on", f"locked_on_{team_slug}"))
        if team.get("google_news_query"):
            instances.append(("google_news", f"google_news_{team_slug}"))
        # Substack + beat are many-per-team; skipped here, handled by dedicated
        # per-feed seed file loaders (seed_beat_writer_feeds, seed_substack_feeds)
        # once those CLIs land. The template row itself still exists for cohort
        # weight lookup.

        for family, concrete_source_id in instances:
            template_id = _FAMILY_TO_TEMPLATE.get(family)
            if not template_id or template_id not in templates:
                skipped_no_template += 1
                continue
            tmpl = templates[template_id]
            existing = db.query_one(
                "select source_registry_id from source_registry where source_id = :sid",
                {"sid": concrete_source_id},
            )
            params = {
                "source_id": concrete_source_id,
                "source_name": f"{family} — {team['canonical_name']}",
                "provider_name": family,
                "source_kind": f"fanintel_tier_{tmpl['tier'].lower()}",
                "collection_method": tmpl.get("ingest_method") or "unspecified",
                "terms_profile": tmpl.get("license") or "inherited",
                "tier": tmpl["tier"],
                "ingest_method": tmpl.get("ingest_method"),
                "terms_url": None,
                "license": tmpl.get("license"),
                "retention_days": tmpl.get("retention_days"),
                "cohort_weights": tmpl["cohort_weights"],
                "cohort_weights_rationale":
                    f"Inherits from {template_id}. Per-team instance for "
                    f"team_id={team['team_id']} ({team['canonical_name']}).",
                "cohort_weights_updated_at": _utcnow_iso()[:10],
                "max_publication_form": tmpl["max_publication_form"],
                "is_active": 1,
                "updated_at": _utcnow_iso(),
            }
            if existing:
                db.execute(
                    """
                    update source_registry set
                        source_name = :source_name,
                        tier = :tier,
                        cohort_weights = :cohort_weights,
                        cohort_weights_rationale = :cohort_weights_rationale,
                        cohort_weights_updated_at = :cohort_weights_updated_at,
                        max_publication_form = :max_publication_form,
                        ingest_method = :ingest_method,
                        license = :license,
                        retention_days = :retention_days,
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

    return {
        "inserted": inserted, "updated": updated,
        "total": inserted + updated,
        "skipped_no_template": skipped_no_template,
    }


def _seed_per_feed_instances(db: Database, yaml_path: Path, family: str,
                              slug_key: str, template_id: str,
                              team_slug_key: str | None) -> dict[str, int]:
    """Shared loader for beat_writer_feeds.yaml / substack_feeds.yaml / etc.

    Each YAML entry becomes one concrete source_registry row whose
    cohort_weights inherit from ``template_id``. source_id is
    ``{family}_{team_slug}_{writer_slug}`` (beat) or ``{family}_{writer_slug}``
    (substack, when team_slug_key is None or value is null).
    """
    if not yaml_path.exists():
        return {"inserted": 0, "updated": 0, "total": 0, "skipped": 0}
    doc = _load_yaml(yaml_path)
    feeds = doc.get("feeds") or []
    tmpl = db.query_one(
        "select * from source_registry where source_id = :sid", {"sid": template_id}
    )
    if not tmpl:
        raise RuntimeError(f"{template_id} not found — run seed-source-registry first")

    inserted = updated = skipped = 0
    for feed in feeds:
        writer_slug = feed.get(slug_key)
        if not writer_slug:
            skipped += 1
            continue
        team_slug = feed.get(team_slug_key) if team_slug_key else None
        if team_slug:
            source_id = f"{family}_{team_slug.lower()}_{writer_slug.lower()}"
            label = f"{family} — {team_slug} / {writer_slug}"
        else:
            source_id = f"{family}_{writer_slug.lower()}"
            label = f"{family} — {writer_slug}"
        existing = db.query_one(
            "select source_registry_id from source_registry where source_id = :sid",
            {"sid": source_id},
        )
        params = {
            "source_id": source_id,
            "source_name": label,
            "provider_name": family,
            "source_kind": f"fanintel_tier_{tmpl['tier'].lower()}",
            "collection_method": tmpl.get("ingest_method") or "unspecified",
            "terms_profile": tmpl.get("license") or "inherited",
            "tier": tmpl["tier"],
            "ingest_method": tmpl.get("ingest_method"),
            "terms_url": feed.get("url"),
            "license": tmpl.get("license"),
            "retention_days": tmpl.get("retention_days"),
            "cohort_weights": tmpl["cohort_weights"],
            "cohort_weights_rationale":
                f"Inherits from {template_id}. Feed URL: {feed.get('url')}",
            "cohort_weights_updated_at": _utcnow_iso()[:10],
            "max_publication_form": tmpl["max_publication_form"],
            "is_active": 1,
            "updated_at": _utcnow_iso(),
        }
        if existing:
            db.execute(
                """
                update source_registry set
                    source_name = :source_name,
                    tier = :tier,
                    cohort_weights = :cohort_weights,
                    cohort_weights_rationale = :cohort_weights_rationale,
                    cohort_weights_updated_at = :cohort_weights_updated_at,
                    max_publication_form = :max_publication_form,
                    terms_url = :terms_url,
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
    return {"inserted": inserted, "updated": updated,
            "total": inserted + updated, "skipped": skipped}


def seed_beat_writer_feeds(db: Database,
                            path: Path | None = None) -> dict[str, int]:
    return _seed_per_feed_instances(
        db,
        path or (_SEEDS_DIR / "beat_writer_feeds.yaml"),
        family="beat",
        slug_key="writer_slug",
        template_id="beat_template",
        team_slug_key="team_slug",
    )


def seed_substack_feeds(db: Database,
                         path: Path | None = None) -> dict[str, int]:
    return _seed_per_feed_instances(
        db,
        path or (_SEEDS_DIR / "substack_feeds.yaml"),
        family="substack",
        slug_key="writer_slug",
        template_id="substack_template",
        team_slug_key="team_slug",
    )


def seed_podcast_feeds(db: Database,
                        path: Path | None = None) -> dict[str, int]:
    return _seed_per_feed_instances(
        db,
        path or (_SEEDS_DIR / "podcast_feeds.yaml"),
        family="podcast",
        slug_key="show_slug",
        template_id="locked_on_template",
        team_slug_key=None,
    )


def seed_radio_feeds(db: Database,
                      path: Path | None = None) -> dict[str, int]:
    return _seed_per_feed_instances(
        db,
        path or (_SEEDS_DIR / "radio_feeds.yaml"),
        family="radio",
        slug_key="show_slug",
        template_id="radio_template",
        team_slug_key=None,
    )


__all__ = [
    "seed_source_registry", "seed_priority_teams", "seed_source_instances",
    "seed_beat_writer_feeds", "seed_substack_feeds",
    "seed_podcast_feeds", "seed_radio_feeds",
]
