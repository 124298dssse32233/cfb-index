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

    # Session 6 (2026-05-22): one-shot recovery for editions whose
    # Pattern C output drifted off-topic (wrong season, wrong scene,
    # invented facts). Direct-UPDATEs body_markdown + dek from the
    # seed payload, bypassing upsert detection. Does not change
    # status — published editions stay published. Use when an
    # already-published edition has demonstrably bad content and you
    # need to restore the seed text immediately, without waiting for
    # the next world_class_enrich pass.
    # Session 6 (2026-05-22): backfill receipt citations for editions
    # whose Pattern C run pre-dated the receipt pipeline. Hand-curated
    # citation lists per slug live in this module's _CURATED_BACKFILL
    # mapping. Idempotent — re-running on an already-backfilled slug
    # replaces its citation rows via persist_citations.
    backfill_cit = subparsers.add_parser(
        "backfill-edition-citations",
        help=(
            "Backfill hand-curated citation receipts to a published "
            "edition's cover essay. Soft-fail: missing seed → exit 1; "
            "missing DB row → exit 2; otherwise persists + exits 0."
        ),
    )
    backfill_cit.add_argument("--slug", required=True,
                              help="Edition slug, e.g. 2026-w18")
    backfill_cit.set_defaults(func=_cmd_backfill_citations)

    force_reseed = subparsers.add_parser(
        "force-reseed-feature",
        help=(
            "One-shot direct-UPDATE of an edition feature's body+dek "
            "from seeds.py, bypassing upsert preservation logic. "
            "Use to recover from off-topic Pattern C drift on an "
            "already-published edition."
        ),
    )
    force_reseed.add_argument("--slug", required=True,
                              help="Edition slug, e.g. 2026-w18")
    force_reseed.add_argument("--feature-order", type=int, default=1,
                              help="Feature order to reset (default: 1, the cover essay)")
    force_reseed.set_defaults(func=_cmd_force_reseed_feature)

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


# =============================================================================
# Receipt-pattern backfill — Session 6 closure for Axis M (design audit v2).
# =============================================================================
#
# These citations are hand-curated to close the receipt-density spec
# violation logged in docs/research/design-audit-2026-05-22-v2.md §M.
# Each list pairs a Citation with a `[N]` marker that's been inserted
# into the corresponding edition feature's body via the seed payload.
# When Pattern C regenerates with the offseason-aware prompt + receipt
# instructions (Session 6 Track 1), it will emit its own citations and
# overwrite this backfill via persist_citations' DELETE-then-INSERT
# idempotency.
#
# Marker placement convention:
#   * Cover essays: ~5 markers per ~1,100 words (≈ one per 220 words)
#   * Secondary features: ~3 markers per ~250 words (≈ one per 80 words —
#     spec allows tighter density on tight features)
#
# The Citation marker_ids start at 1 within each generation_id (i.e.
# within each feature). Marker placement in body markdown is done in
# seeds.py at the appropriate factual claims; this CLI just persists
# the source-side metadata.

def _curated_backfill_citations() -> dict[str, dict[int, list]]:
    """Per-slug, per-feature-order curated citation lists.

    Outer key: edition_slug.
    Inner key: feature_order (1 = cover essay, 2+ = features).
    Value: list of Citation objects with sequential marker_ids.
    """
    from cfb_rankings.citations import Citation

    return {
        # Issue XVII — receipts on the 2025 College Football Playoff
        "2026-w17": {
            1: [  # cover essay "After the bracket — three conversations"
                Citation(marker_id=1, source_kind="cfbd",
                         source_label="CFBD · 2025 CFP bracket data",
                         source_url="https://collegefootballdata.com/games?year=2025&seasonType=postseason",
                         confidence="primary", source_date="2026-01-20"),
                Citation(marker_id=2, source_kind="beat_writer",
                         source_label="The Athletic · Stewart Mandel on the 12-team bracket lessons",
                         source_url="https://theathletic.com/college-football/",
                         confidence="primary", source_date="2026-01-22"),
                Citation(marker_id=3, source_kind="edition",
                         source_label="CFB Index Issue XV · pre-bracket cover essay",
                         source_url="/editions/2026-w15/",
                         confidence="supporting", source_date="2026-04-19"),
                Citation(marker_id=4, source_kind="cfbd",
                         source_label="CFBD · 2025 advanced stats (final)",
                         source_url="https://collegefootballdata.com/stats/season",
                         confidence="primary", source_date="2026-01-25"),
                Citation(marker_id=5, source_kind="podcast",
                         source_label="Solid Verbal · post-CFP wrap (David Ubben + Ty Hildenbrandt)",
                         source_url="https://www.thesolidverbal.com/",
                         confidence="background", source_date="2026-01-23"),
            ],
        },
        # Issue XVIII — "The Quiet Week" · May 4 offseason gap
        "2026-w18": {
            1: [  # cover essay "The Quiet Week"
                Citation(marker_id=1, source_kind="official",
                         source_label="NCAA spring portal window · April 16–30 close",
                         source_url="https://www.ncaa.org/sports/2021/8/31/transfer-portal-windows.aspx",
                         confidence="primary", source_date="2026-04-30"),
                Citation(marker_id=2, source_kind="beat_writer",
                         source_label="247Sports · April-portal final-tally roundup",
                         source_url="https://247sports.com/college/football/portal-tracker/",
                         confidence="supporting", source_date="2026-05-02"),
                Citation(marker_id=3, source_kind="reddit",
                         source_label="r/CFB · weekly discussion · first Monday of May",
                         source_url="https://reddit.com/r/CFB/",
                         confidence="background", source_date="2026-05-04"),
                Citation(marker_id=4, source_kind="edition",
                         source_label="CFB Index Issue XVII · post-bracket lookahead",
                         source_url="/editions/2026-w17/",
                         confidence="supporting", source_date="2026-04-26"),
            ],
            3: [  # connection "Receipts: Two Months Past Pre-Draft Boards"
                Citation(marker_id=1, source_kind="beat_writer",
                         source_label="NFL.com · Daniel Jeremiah late-February consensus board",
                         source_url="https://www.nfl.com/news/2026-mock-draft-board/",
                         confidence="primary", source_date="2026-02-24"),
                Citation(marker_id=2, source_kind="wire",
                         source_label="CFB Index Wire · combine-week pre-draft movement",
                         source_url="/wire/",
                         confidence="primary", source_date="2026-03-01"),
                Citation(marker_id=3, source_kind="official",
                         source_label="NFL · final 2026 draft order (3-day event)",
                         source_url="https://www.nfl.com/draft/",
                         confidence="primary", source_date="2026-04-25"),
            ],
        },
        # Issue XIX — "Three Weeks Before Camp Whispers" · May 11
        "2026-w19": {
            1: [  # cover essay "Three Weeks Before Camp Whispers"
                Citation(marker_id=1, source_kind="official",
                         source_label="NCAA · FBS fall-camp open window (Aug 3, 2026)",
                         source_url="https://www.ncaa.org/sports/football/calendar",
                         confidence="primary", source_date="2026-05-01"),
                Citation(marker_id=2, source_kind="beat_writer",
                         source_label="ESPN · Bill Connelly preseason SP+ preview cycle dates",
                         source_url="https://www.espn.com/college-football/insider/",
                         confidence="supporting", source_date="2026-05-08"),
                Citation(marker_id=3, source_kind="cfbd",
                         source_label="CFBD · ratings as of May 11, 2026",
                         source_url="https://collegefootballdata.com/ratings",
                         confidence="primary", source_date="2026-05-11"),
                Citation(marker_id=4, source_kind="edition",
                         source_label="CFB Index Issue XVIII · the quiet week baseline",
                         source_url="/editions/2026-w18/",
                         confidence="supporting", source_date="2026-05-04"),
                Citation(marker_id=5, source_kind="reddit",
                         source_label="r/CFB · pre-camp speculation thread velocity",
                         source_url="https://reddit.com/r/CFB/",
                         confidence="background", source_date="2026-05-10"),
            ],
            3: [  # connection "Storyline Threads in Mid-Spring"
                Citation(marker_id=1, source_kind="edition",
                         source_label="CFB Index · active storyline threads (storylines/)",
                         source_url="/storylines/",
                         confidence="primary", source_date="2026-05-11"),
                Citation(marker_id=2, source_kind="wire",
                         source_label="CFB Index Wire · 2026 spring portal close roundup",
                         source_url="/wire/",
                         confidence="primary", source_date="2026-05-01"),
                Citation(marker_id=3, source_kind="beat_writer",
                         source_label="On3 · spring evaluation period recap (Pete Nakos)",
                         source_url="https://www.on3.com/news/category/recruiting/",
                         confidence="supporting", source_date="2026-05-06"),
            ],
        },
    }


def _cmd_backfill_citations(args: argparse.Namespace) -> int:
    """Persist hand-curated citation receipts for a published edition.

    Idempotent via persist_citations' DELETE-then-INSERT pattern. Returns:
        0 — at least one citation set persisted
        1 — no curated set exists for this slug
        2 — features table has no rows for this slug (run seed-editions
            first so feature ids exist to attach citations to)
    """
    from cfb_rankings.citations import persist_citations
    from .data import fetch_edition_features

    backfill = _curated_backfill_citations()
    slug_data = backfill.get(args.slug)
    if slug_data is None:
        print(f"no curated backfill for {args.slug}; add to _curated_backfill_citations")
        return 1

    db = _open_db()
    features = fetch_edition_features(db, args.slug)
    if not features:
        print(f"no DB features for {args.slug}; run seed-editions + publish-edition first")
        return 2

    feature_by_order = {f.feature_order: f for f in features}
    total = 0
    for feature_order, cits in slug_data.items():
        feature = feature_by_order.get(feature_order)
        if feature is None or feature.id is None:
            print(f"  skip feature_order={feature_order}: not in DB")
            continue
        n = persist_citations(db, int(feature.id), cits)
        print(f"  persisted {n} citations on feature_order={feature_order} (id={feature.id})")
        total += n
    print(f"backfill-edition-citations {args.slug}: total={total}")
    return 0


def _cmd_force_reseed_feature(args: argparse.Namespace) -> int:
    """Session 6 recovery tool — direct-UPDATE a feature's body+dek
    from the seed payload, bypassing upsert preservation logic.

    Used to recover from off-topic Pattern C drift on an already-
    published edition (e.g. W18 shipped a mid-November scene-setter
    on a May 4 publish date because Pattern C interpreted ISO calendar
    week 18 as football week 18). The new offseason-aware Pattern C
    prompt prevents this from recurring; this command restores the
    seed body so the live site reads correctly while the next
    world_class_enrich run hasn't fired yet.

    Idempotent: if the seed has no payload for this slug+order, exits
    1. If the row doesn't exist in the DB yet, exits 2. Otherwise
    UPDATEs body_markdown + dek from the seed and exits 0.
    """
    from .seeds import _archive_edition_payload, _w17_payload

    # Dispatch to the right seed loader. w17 is the canonical large
    # seed (its own _w17_payload); the rest live under
    # _archive_edition_payload(slug).
    try:
        if args.slug == "2026-w17":
            _, features, _ = _w17_payload()
        else:
            _, features, _ = _archive_edition_payload(args.slug)
    except KeyError:
        print(f"no seed payload for {args.slug}; add a seed loader first")
        return 1
    target = next(
        (f for f in features if f.feature_order == args.feature_order),
        None,
    )
    if target is None:
        print(f"no seed feature with order={args.feature_order} for {args.slug}")
        return 1

    db = _open_db()
    existing = db.query_one(
        "select id from edition_features where edition_slug = :slug "
        "and feature_order = :ord",
        {"slug": args.slug, "ord": args.feature_order},
    )
    if not existing:
        print(f"no DB row for {args.slug} order={args.feature_order}; run seed-editions first")
        return 2

    db.execute(
        """
        update edition_features
           set body_markdown = :body,
               dek = :dek,
               title = :title,
               byline = :byline,
               read_time_minutes = :read_time
         where edition_slug = :slug
           and feature_order = :ord
        """,
        {
            "slug": args.slug,
            "ord": args.feature_order,
            "body": target.body_markdown,
            "dek": target.dek,
            "title": target.title,
            "byline": target.byline,
            "read_time": target.read_time_minutes,
        },
    )
    print(
        f"force-reseeded {args.slug} order={args.feature_order} "
        f"(title={target.title!r}, body_len={len(target.body_markdown)})"
    )
    return 0


def _open_db() -> Database:
    from cfb_rankings.config import AppConfig
    from cfb_rankings.migrations import apply_sql_migrations
    config = AppConfig.from_env()
    db = Database(config.database_url)
    apply_sql_migrations(db)
    return db
