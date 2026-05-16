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

    # Sprint v5-2: LLM-driven Edition cover essay synthesis.
    # Routes through quality_loop.loop_c_critic_revise when the feature
    # flag is set in config.QUALITY_LOOP_FLAGS, otherwise falls back to
    # the seed-authored body. See editions/cover_essay.py for the full
    # dispatch contract.
    gen_cover = subparsers.add_parser(
        "generate-edition-cover",
        help=(
            "Synthesize the Edition cover essay body via quality_loop "
            "(Pattern C). Falls back to seed payload when the flag is "
            "unset or the loop falls back."
        ),
    )
    gen_cover.add_argument("--season", required=True, type=int,
                           help="Season year, e.g. 2026")
    gen_cover.add_argument("--week", required=True, type=int,
                           help="Week number, e.g. 17")
    gen_cover.add_argument("--slug", required=True,
                           help="Edition slug, e.g. 2026-w17")
    gen_cover.add_argument(
        "--persist", action="store_true",
        help=(
            "Persist the generated body to edition_features (feature_order=1, "
            "feature_kind='cover_essay'). Without this flag the command "
            "prints the result to stdout and writes nothing."
        ),
    )
    gen_cover.set_defaults(func=_cmd_generate_cover)

    # Sprint v5-2 follow-up: batch wrapper around generate-edition-cover.
    # Iterates over editions matching a status filter, generates each
    # cover via Pattern C (or seed fall-back), persists the body to
    # edition_features, and (default) promotes status draft → published.
    # Used by the world_class_enrich workflow to auto-fill draft stubs
    # like W18/W19 — without this, the homepage stays on the last
    # status='published' edition (XVII) and never rotates.
    gen_covers = subparsers.add_parser(
        "generate-edition-covers",
        help=(
            "Batch-generate cover essays for editions matching a status "
            "filter (default: 'draft'). Persists each body to "
            "edition_features and promotes status to 'published'. "
            "Idempotent — re-running on an already-published edition is "
            "a no-op unless --include-published is set."
        ),
    )
    gen_covers.add_argument(
        "--status", default="draft",
        help="Filter editions by status. Default: 'draft'.",
    )
    gen_covers.add_argument(
        "--no-promote", action="store_true",
        help=(
            "Persist the generated body but do NOT update editions.status. "
            "Default behavior: promote draft → published once a body is "
            "successfully generated and persisted."
        ),
    )
    gen_covers.add_argument(
        "--require-llm", action="store_true",
        help=(
            "Only persist/promote when the generator's source == 'llm'. "
            "Seed-fall-back bodies are left in place but the edition is "
            "NOT promoted. Use this in workflows where Pattern C must "
            "have actually fired (e.g. quality-gated production runs)."
        ),
    )
    gen_covers.set_defaults(func=_cmd_generate_edition_covers)


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


def _cmd_generate_cover(args: argparse.Namespace) -> int:
    """Sprint v5-2 — first quality_loop flag flip.

    With ``config.QUALITY_LOOP_FLAGS["tier1.edition_cover"]`` set to
    ``LoopPattern.C_CRITIC_REVISE`` (the v5-2 default), this routes the
    cover essay through the 3-critic loop. Without the flag, it returns
    the seed body. Either way the command exits 0 with the body on
    stdout — workflows decide whether to ``--persist`` it.
    """
    from .cover_essay import synthesize_cover_essay

    db = _open_db()
    result = synthesize_cover_essay(
        season=int(args.season),
        week=int(args.week),
        edition_slug=args.slug,
        db=db,
    )

    if result.text is None:
        print(
            f"no cover essay body produced for {args.slug} "
            f"(source={result.source}, reason={result.fallback_reason})"
        )
        return 1

    if args.persist:
        _persist_cover_body(db, args.slug, result.text)
        print(
            f"persisted cover essay for {args.slug} "
            f"(source={result.source}, len={len(result.text)})"
        )
    else:
        print(f"source={result.source} len={len(result.text)}")
        print("--- BODY ---")
        print(result.text)
    return 0


def _persist_cover_body(db, slug: str, body: str) -> None:
    """Update an existing cover_essay feature in-place. Does not create a
    new row — the edition seed (or an authoring step) is expected to
    have already inserted the feature_order=1 placeholder.

    Hotfix-11: ALSO update the feature's `dek` field. The homepage and
    archive cards render `dek` (not `body_markdown`) as the tease text
    under the issue title. Prior to this fix the seed-authored "Cover
    essay scaffold — auto-filled by the Pattern C generator on the next
    world_class_enrich run" placeholder dek persisted forever, even
    after Pattern C wrote a real body. Derive the new dek from the
    first paragraph of body (cap ~220 chars at sentence boundary) so
    the tease accurately summarizes the live essay.
    """
    new_dek = _dek_from_body(body)
    db.execute(
        """
        update edition_features
           set body_markdown = :body,
               dek = :dek
         where edition_slug = :slug
           and feature_order = 1
           and feature_kind = 'cover_essay'
        """,
        {"body": body, "dek": new_dek, "slug": slug},
    )


def _dek_from_body(body: str, *, max_chars: int = 220) -> str:
    """Derive a tease-dek from the first paragraph of a cover essay body.

    Strategy:
      1. Take the first non-empty paragraph (split on \\n\\n).
      2. If it fits in max_chars, return it verbatim.
      3. Otherwise truncate at the last sentence-ending punctuation
         (`.`, `?`, `!`) before max_chars, preserving the punctuation.
         If no sentence break exists, truncate at the last word boundary
         and append `…`.

    Returns the original body capped at max_chars when no paragraph
    break is present (e.g. seed-fall-back single-line placeholders).
    Never returns an empty string when body is non-empty — falls back
    to a hard char cap if all else fails.
    """
    if not body:
        return ""
    text = body.strip()
    # First paragraph: split on blank line; if none, treat the whole
    # text as one paragraph.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    first = paragraphs[0] if paragraphs else text
    # Collapse internal whitespace to single spaces (avoids
    # \n-mid-paragraph artifacts in the rendered HTML).
    first = " ".join(first.split())
    if len(first) <= max_chars:
        return first
    # Find the last sentence-ending punctuation at or before max_chars.
    head = first[:max_chars]
    for punct in (". ", "? ", "! "):
        idx = head.rfind(punct)
        if idx >= max_chars // 2:  # prefer a sentence break in the back half
            return head[: idx + 1].rstrip()
    # Fall back to last word boundary + ellipsis.
    space_idx = head.rfind(" ")
    if space_idx > 0:
        return head[:space_idx].rstrip() + "…"
    return head + "…"


def _cmd_generate_edition_covers(args: argparse.Namespace) -> int:
    """Batch: generate cover essays for editions matching --status,
    persist each body, and (default) promote draft → published.

    Workflow entry point. The world_class_enrich pipeline calls this
    after `seed-editions` ensures W18/W19 stubs exist; this then
    materializes their cover essays via Pattern C and promotes them
    so the homepage's `fetch_active_edition` rotation picks them up.

    Exit codes:
        0 — at least one edition processed (success or graceful skip)
        2 — no editions matched the --status filter

    Counters are printed at the end for workflow log visibility.
    """
    from .cover_essay import synthesize_cover_essay

    db = _open_db()
    rows = db.query_all(
        "select edition_slug, edition_number, status, "
        "       publish_date "
        "from editions "
        "where status = :status "
        "order by publish_date asc, edition_number asc",
        {"status": args.status},
    )
    if not rows:
        print(f"no editions with status='{args.status}' — nothing to do")
        return 2

    promoted = 0
    persisted_no_promote = 0
    skipped_no_text = 0
    skipped_seed_only = 0
    print(f"found {len(rows)} edition(s) with status='{args.status}'")
    for row in rows:
        slug = str(row["edition_slug"])
        # The edition_slug carries the calendar year + ISO week as
        # `YYYY-w{WW}`. Parse rather than relying on edition_number
        # in case the two ever drift. publish_date is the authoritative
        # date for context-builder lookups; derive the season from its
        # year prefix so the cohort/storyline queries pull the right
        # offseason window.
        publish_date = str(row["publish_date"] or "")
        season = int(publish_date[:4]) if publish_date else int(row["edition_number"])
        week = int(row["edition_number"])
        print(f"\n  → {slug} (season={season}, week={week})")
        result = synthesize_cover_essay(
            season=season, week=week, edition_slug=slug, db=db,
        )
        if result.text is None:
            print(
                f"    no text produced (source={result.source}, "
                f"reason={result.fallback_reason}) — skipped"
            )
            skipped_no_text += 1
            continue

        if args.require_llm and result.source != "llm":
            print(
                f"    source={result.source!r} but --require-llm set — "
                f"body left untouched, edition NOT promoted"
            )
            skipped_seed_only += 1
            continue

        _persist_cover_body(db, slug, result.text)

        if args.no_promote:
            print(
                f"    persisted body (source={result.source}, "
                f"len={len(result.text)}) — --no-promote set, status stays "
                f"'{row['status']}'"
            )
            persisted_no_promote += 1
        else:
            db.execute(
                "update editions "
                "   set status = 'published', "
                "       published_at_utc = coalesce(published_at_utc, "
                "                                   datetime('now')), "
                "       last_updated_utc = current_timestamp "
                " where edition_slug = :slug",
                {"slug": slug},
            )
            print(
                f"    persisted body (source={result.source}, "
                f"len={len(result.text)}) + promoted "
                f"{row['status']} → published"
            )
            promoted += 1

    print(
        f"\nsummary: promoted={promoted} "
        f"persisted_no_promote={persisted_no_promote} "
        f"skipped_no_text={skipped_no_text} "
        f"skipped_seed_only={skipped_seed_only}"
    )
    return 0


def _open_db() -> Database:
    from cfb_rankings.config import AppConfig
    from cfb_rankings.migrations import apply_sql_migrations
    config = AppConfig.from_env()
    db = Database(config.database_url)
    apply_sql_migrations(db)
    return db
