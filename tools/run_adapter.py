"""Runner used by the GitHub Actions workflows — ``python tools/run_adapter.py <adapter-id>``.

Looks up the adapter class, constructs it against the production DB, calls
``.run()``. Exits 0 on ok/empty/skipped so upstream cron keeps running even
when a single source's API is flaky. Exits 2 on hard config errors (missing
env var for an adapter that can't run without it).

Usage from a workflow step:

    - name: wiki pageviews
      run: python tools/run_adapter.py wiki_pv

Set ``FANINTEL_REQUIRED=1`` to turn missing-env errors into exit-1 instead
of exit-0 (useful for a dedicated secrets-smoke workflow).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from cfb_rankings.config import AppConfig  # noqa: E402
from cfb_rankings.db import Database  # noqa: E402
from cfb_rankings.migrations import apply_runtime_migrations  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_adapter")


def _build_adapter(adapter_id: str, db: Database):
    """Construct and return the adapter instance for a given source_id.

    Adapters that take per-team constructor args (campus_*, beat_*, …) loop
    over priority_teams inside the runner instead of being instantiated here.
    """
    if adapter_id == "wiki_pv":
        from cfb_rankings.ingest.sources.wikipedia import WikipediaPageviewsAdapter
        return WikipediaPageviewsAdapter(db)
    if adapter_id == "wiki_edits":
        from cfb_rankings.ingest.sources.wikipedia import WikipediaEditsAdapter
        return WikipediaEditsAdapter(db)
    if adapter_id == "seatgeek":
        from cfb_rankings.ingest.sources.seatgeek import SeatGeekAdapter
        return SeatGeekAdapter(db)
    if adapter_id == "youtube_meta":
        from cfb_rankings.ingest.sources.youtube_meta import YouTubeMetaAdapter
        return YouTubeMetaAdapter(db)
    if adapter_id == "kalshi":
        from cfb_rankings.ingest.sources.prediction_markets import KalshiAdapter
        return KalshiAdapter(db)
    if adapter_id == "polymarket":
        from cfb_rankings.ingest.sources.prediction_markets import PolymarketAdapter
        return PolymarketAdapter(db)
    if adapter_id == "gdelt_volume":
        from cfb_rankings.ingest.sources.gdelt_volume import GdeltVolumeAdapter
        return GdeltVolumeAdapter(db)
    if adapter_id == "spotify_charts":
        from cfb_rankings.ingest.sources.spotify_charts import SpotifyChartsAdapter
        return SpotifyChartsAdapter(db)
    if adapter_id == "bluesky_curated":
        from cfb_rankings.ingest.sources.bluesky import BlueskyCuratedAdapter
        return BlueskyCuratedAdapter(db)
    if adapter_id == "bluesky_feeds":
        from cfb_rankings.ingest.sources.bluesky import BlueskyFeedsAdapter
        return BlueskyFeedsAdapter(db)
    raise SystemExit(f"run_adapter: unknown adapter_id={adapter_id!r}")


def _per_feed_adapter_runs(adapter_id: str, db: Database) -> int:
    """Bulk-run beat_writers_all or substack_all by iterating over the per-
    feed source_registry rows seeded by seed-feed-instances.

    Each row has source_id like 'beat_<team>_<writer>' or
    'substack_<writer>' and a terms_url that points at the feed RSS.
    """
    from cfb_rankings.ingest.sources.rss_family import (
        BeatWriterAdapter, SubstackAdapter,
    )

    if adapter_id == "beat_writers_all":
        prefix = "beat_"
        AdapterClass = BeatWriterAdapter
        family = "beat"
    elif adapter_id == "substack_all":
        prefix = "substack_"
        AdapterClass = SubstackAdapter
        family = "substack"
    else:
        return -1

    rows = db.query_all(
        "select source_id, source_name, terms_url from source_registry "
        "where source_id like :p and terms_url is not null "
        "and (is_active = 1 or is_active is null) "
        "and source_id not in ('beat_articles', 'substack_cfb')",
        {"p": f"{prefix}%"},
    )
    ok = err = 0
    for r in rows:
        sid = r["source_id"]
        feed_url = r["terms_url"]
        # Derive team_slug / writer_slug from the source_id.
        parts = sid[len(prefix):].split("_", 1)
        team_slug = parts[0] if len(parts) == 2 else ""
        writer_slug = parts[1] if len(parts) == 2 else parts[0]
        try:
            team_id_row = db.query_one(
                "select t.team_id from teams t where lower(t.slug) = lower(:s) limit 1",
                {"s": team_slug},
            ) if team_slug else None
            team_id = int(team_id_row["team_id"]) if team_id_row else None

            if AdapterClass is BeatWriterAdapter:
                if team_id is None:
                    err += 1
                    logger.info("%s %s: no team match for slug=%r", family, sid, team_slug)
                    continue
                adapter = AdapterClass(
                    db, team_id=team_id, team_slug=team_slug,
                    writer_slug=writer_slug, feed_url=feed_url,
                )
            else:  # SubstackAdapter
                adapter = AdapterClass(
                    db, team_id=team_id, writer_slug=(writer_slug if writer_slug else team_slug),
                    feed_url=feed_url,
                )
            result = adapter.run()
            logger.info("%s %s: %s (%d rows)",
                        family, sid, result.status, result.rows_inserted)
            if result.status == "error":
                err += 1
            else:
                ok += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s %s failed: %s", family, sid, exc)
            err += 1
    logger.info("%s totals: ok=%d err=%d", adapter_id, ok, err)
    return 0


def _per_team_adapter_runs(adapter_id: str, db: Database) -> int:
    """Handle adapters that need one instance per priority_teams row."""
    from cfb_rankings.ingest.sources.campus_news import CampusNewsAdapter
    from cfb_rankings.ingest.sources.google_news import GoogleNewsAdapter
    from cfb_rankings.ingest.sources.rss_family import (
        AthleticsSiteAdapter, LockedOnAdapter,
    )

    if adapter_id in ("beat_writers_all", "substack_all"):
        return _per_feed_adapter_runs(adapter_id, db)

    family_map = {
        "campus_news_all": ("campus_newspaper_feed", CampusNewsAdapter, "campus"),
        "google_news_all": ("google_news_query", GoogleNewsAdapter, "google"),
        "athletics_all":   ("athletic_dept_feed", AthleticsSiteAdapter, "athletics"),
        "locked_on_all":   ("locked_on_rss",      LockedOnAdapter,      "locked_on"),
    }
    if adapter_id not in family_map:
        return -1
    col, AdapterClass, family = family_map[adapter_id]
    rows = db.query_all(
        f"select pt.team_id, t.slug, t.canonical_name, pt.{col} as feed_url "
        f"from priority_teams pt join teams t on t.team_id = pt.team_id "
        f"where pt.{col} is not null"
    )
    ok = err = 0
    for r in rows:
        slug = (r.get("slug") or r.get("canonical_name") or "").lower().replace(" ", "-")
        try:
            if family == "google":
                adapter = AdapterClass(
                    db, team_id=r["team_id"], team_slug=slug,
                    query=r["feed_url"],
                )
            else:
                adapter = AdapterClass(
                    db, team_id=r["team_id"], team_slug=slug,
                    feed_url=r["feed_url"],
                )
            result = adapter.run()
            logger.info("%s %s: %s (%d rows)",
                        family, slug, result.status, result.rows_inserted)
            if result.status == "error":
                err += 1
            else:
                ok += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s %s failed: %s", family, slug, exc)
            err += 1
    logger.info("%s totals: ok=%d err=%d", adapter_id, ok, err)
    return 0  # never exit non-zero from a per-team bulk run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter_id",
                        help="source_id of a single adapter, or a bulk family like "
                             "'campus_news_all', 'google_news_all', 'athletics_all', "
                             "'locked_on_all'.")
    args = parser.parse_args()

    config = AppConfig.from_env()
    db = Database(config.database_url)
    apply_runtime_migrations(db)

    bulk_result = _per_team_adapter_runs(args.adapter_id, db)
    if bulk_result != -1:
        return bulk_result

    try:
        adapter = _build_adapter(args.adapter_id, db)
    except SystemExit as exc:
        logger.error(str(exc))
        return 2

    try:
        result = adapter.run()
    except RuntimeError as exc:
        # Typically "missing env var"
        logger.warning("%s could not run: %s", args.adapter_id, exc)
        return 1 if os.environ.get("FANINTEL_REQUIRED") else 0

    logger.info("%s: status=%s rows=%d", args.adapter_id,
                result.status, result.rows_inserted)
    # scrape_health has the row; always exit 0 so cron continues
    return 0


if __name__ == "__main__":
    sys.exit(main())
