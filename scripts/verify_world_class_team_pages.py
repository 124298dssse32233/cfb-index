#!/usr/bin/env python3
"""verify_world_class_team_pages.py — CI guardrail that fails the build if
any real FBS team page is shipping with the legacy `premium-team-hero`
chrome instead of the world-class `team-page` chrome.

Background (2026-05-23): publish-site silently dropped 5 of 55 hand-authored
profile YAMLs in render_all_profiled_pages. The drops weren't caught by
file-count gates because the legacy file from prior-site stayed in place.
Visible effect: /teams/cincinnati.html shipped as legacy chrome for users.

Detection rule:
  For every real FBS slug (per list_real_fbs_slugs(db)), verify that
  output/site/teams/<slug>.html contains the `team-page` class and does
  NOT contain `premium-team-hero`. Any mismatch is a failure.

Exit codes:
  0 — all 119 real FBS teams ship world-class chrome
  1 — one or more teams ship legacy chrome (CI should fail)

Usage:
  python scripts/verify_world_class_team_pages.py [--site-dir output/site] [--db cfb_rankings.db]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", default="output/site")
    ap.add_argument("--db", default="cfb_rankings.db")
    ap.add_argument(
        "--max-failures-to-print",
        type=int,
        default=20,
        help="Cap on per-slug failure printout (default 20).",
    )
    args = ap.parse_args()

    site_dir = Path(args.site_dir)
    teams_dir = site_dir / "teams"
    if not teams_dir.exists():
        print(f"::error::teams dir missing: {teams_dir}", flush=True)
        return 1

    # Use repo source for list_real_fbs_slugs — guard against editable-install
    # path quirks by inserting src/ first.
    sys.path.insert(0, "src")
    try:
        from cfb_rankings.db import Database
        from cfb_rankings.team_pages.profile_loader import (
            list_real_fbs_slugs, PROFILED_SLUGS, PROFILES_DIR,
        )
    except Exception as exc:
        print(f"::error::failed to import cfb_rankings: {exc}", flush=True)
        return 1

    print(
        f"[verify] PROFILES_DIR={PROFILES_DIR} "
        f"PROFILED_SLUGS={len(PROFILED_SLUGS)} slugs",
        flush=True,
    )

    try:
        db = Database(args.db)
        fbs_slugs = sorted(list_real_fbs_slugs(db))
    except Exception as exc:
        print(f"::error::failed to read FBS slugs from db: {exc}", flush=True)
        return 1

    print(f"[verify] checking {len(fbs_slugs)} real FBS team pages...", flush=True)

    legacy_slugs: list[str] = []
    missing_slugs: list[str] = []
    world_class_count = 0

    for slug in fbs_slugs:
        path = teams_dir / f"{slug}.html"
        if not path.exists():
            missing_slugs.append(slug)
            continue
        try:
            html = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            print(f"[verify] failed to read {path}: {exc}", flush=True)
            missing_slugs.append(slug)
            continue
        # The world-class renderer always emits class="team-page" on <main>.
        # The legacy reporting.py renderer always emits "premium-team-hero".
        # Either presence of "premium-team-hero" OR absence of "team-page"
        # signals legacy.
        is_legacy = "premium-team-hero" in html
        is_world_class = "team-page" in html and not is_legacy
        if is_world_class:
            world_class_count += 1
        elif is_legacy:
            legacy_slugs.append(slug)
        else:
            # Neither marker — treat as suspect.
            legacy_slugs.append(f"{slug} (no chrome marker)")

    print(
        f"[verify] world-class={world_class_count}/{len(fbs_slugs)} "
        f"  legacy={len(legacy_slugs)}  missing={len(missing_slugs)}",
        flush=True,
    )

    if missing_slugs:
        print("::warning::missing team pages:", flush=True)
        for slug in missing_slugs[: args.max_failures_to_print]:
            print(f"  - {slug}", flush=True)
        if len(missing_slugs) > args.max_failures_to_print:
            print(
                f"  ... +{len(missing_slugs) - args.max_failures_to_print} more",
                flush=True,
            )

    if legacy_slugs:
        print(
            "::error::Real FBS team pages still shipping LEGACY chrome:",
            flush=True,
        )
        for slug in legacy_slugs[: args.max_failures_to_print]:
            print(f"  - {slug}", flush=True)
        if len(legacy_slugs) > args.max_failures_to_print:
            print(
                f"  ... +{len(legacy_slugs) - args.max_failures_to_print} more",
                flush=True,
            )
        return 1

    if missing_slugs:
        # Missing pages should also fail, but separately from legacy.
        print(
            "::error::Real FBS team pages MISSING from build output",
            flush=True,
        )
        return 1

    print(
        f"::notice::All {len(fbs_slugs)} real FBS team pages ship world-class chrome.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
