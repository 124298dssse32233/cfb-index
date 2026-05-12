"""manage.py subcommand registrations for the editions module.

Three commands:
    publish-edition  — seed a slug's content + mark published. Idempotent.
    render-edition   — render the homepage + article pages for a slug.
    render-homepage  — render just the homepage from the active edition.

The seed payload for the four backfilled editions lives in ``seeds.py``.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from cfb_rankings.db import Database


def register_edition_subcommands(subparsers: argparse._SubParsersAction) -> None:
    publish = subparsers.add_parser(
        "publish-edition",
        help="Seed and publish a weekly edition (idempotent).",
    )
    publish.add_argument("--slug", required=True,
                         help="Edition slug, e.g. 2026-w17")
    publish.set_defaults(func=_cmd_publish_edition)

    render = subparsers.add_parser(
        "render-edition",
        help="Render the homepage + feature article pages for an edition.",
    )
    render.add_argument("--slug", required=True)
    render.set_defaults(func=_cmd_render_edition)

    render_home = subparsers.add_parser(
        "render-homepage",
        help="Render only the homepage using the currently-active edition.",
    )
    render_home.set_defaults(func=_cmd_render_homepage)

    seed = subparsers.add_parser(
        "seed-editions",
        help="Seed all four backfilled editions (2026-w14..w17). Idempotent.",
    )
    seed.set_defaults(func=_cmd_seed_editions)

    archive = subparsers.add_parser(
        "build-editions-archive",
        help="Render /editions/index.html — the archive page listing every edition.",
    )
    archive.set_defaults(func=_cmd_build_archive)


# ---------------- Command implementations ----------------

def _cmd_publish_edition(args: argparse.Namespace) -> int:
    from .seeds import seed_edition
    db = _open_db()
    try:
        seed_edition(db, args.slug)
    except KeyError:
        # No seed payload exists for this slug yet. This is the expected
        # offseason path for the Saturday cron — log + exit 0 so the
        # workflow stays green and doesn't email-spam. When a new edition
        # is authored, add the seed to seeds.py and re-run.
        print(f"no seed payload for {args.slug}; skipping (offseason / not yet authored)")
        return 0
    print(f"published {args.slug}")
    return 0


def _cmd_seed_editions(args: argparse.Namespace) -> int:
    from .seeds import seed_all_editions
    db = _open_db()
    seed_all_editions(db)
    print("seeded 2026-w14, 2026-w15, 2026-w16, 2026-w17")
    return 0


def _cmd_render_edition(args: argparse.Namespace) -> int:
    from .homepage_renderer import render_homepage
    from .article_renderer import render_articles_for_edition
    db = _open_db()
    homepage_path = render_homepage(db)
    articles_paths = render_articles_for_edition(db, args.slug)
    print(f"rendered homepage: {homepage_path}")
    print(f"rendered {len(articles_paths)} article pages")
    return 0


def _cmd_render_homepage(args: argparse.Namespace) -> int:
    from .homepage_renderer import render_homepage
    db = _open_db()
    path = render_homepage(db)
    if path is None:
        print("no active edition; nothing rendered")
        return 1
    print(f"rendered: {path}")
    return 0


def _cmd_build_archive(args: argparse.Namespace) -> int:
    from .archive_renderer import write_editions_archive
    db = _open_db()
    path = write_editions_archive(db)
    print(f"editions archive written: {path}")
    return 0


def _open_db() -> Database:
    from cfb_rankings.config import AppConfig
    from cfb_rankings.migrations import apply_sql_migrations
    config = AppConfig.from_env()
    db = Database(config.database_url)
    apply_sql_migrations(db)
    return db
