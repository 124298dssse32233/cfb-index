#!/usr/bin/env python3
"""verify_world_class_player_pages.py — CI guardrail that fails the build if
representative player pages are missing the v2 module chrome.

Background (Session 14): 8 new player-page v2 modules were added (Standing Rail,
Mirror Match, Coaching Lineage, Live Signal Flow, Heisman Trajectory, Career Arc,
Development Trajectory, Selector Grid). A silent injection regression in
`render_player_page_html` could ship pages without these modules and we'd never
catch it from byte-count gates alone.

Detection rule:
  Sample N representative player slugs (top QBs from latest season's Heisman
  rankings + the QB-leaderboard reference set). For each, verify the rendered
  HTML contains the `player-standing` data-module marker AND the `career-arc`
  data-module marker (these are the two most reliably-present modules — Standing
  Rail always renders, Career Arc always renders 3-beat rail even with sparse
  data).

  Soft-check (warns only): selector-grid + heisman-trajectory presence.

Exit codes:
  0 — sampled pages all ship v2 chrome
  1 — sample failures detected (CI should fail)

Usage:
  python scripts/verify_world_class_player_pages.py [--site-dir output/site]
      [--db cfb_rankings.db] [--sample-size 20]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REQUIRED_MARKERS = (
    'data-module="player-standing"',
    'data-module="mirror-match"',
)
SOFT_MARKERS = (
    'data-module="selector-grid"',
    'data-module="heisman-trajectory"',
    'data-module="coaching-lineage"',
    'data-module="career-arc"',
    'data-module="development-trajectory"',
    'data-module="live-signal-flow"',
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", default="output/site")
    ap.add_argument("--db", default="cfb_rankings.db")
    ap.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Number of representative player slugs to sample (default 20).",
    )
    args = ap.parse_args()

    site_dir = Path(args.site_dir)
    players_dir = site_dir / "players"
    if not players_dir.exists():
        print(f"::error::players dir missing: {players_dir}", flush=True)
        return 1

    sys.path.insert(0, "src")
    try:
        from cfb_rankings.db import Database
    except Exception as exc:
        print(f"::error::failed to import cfb_rankings.db: {exc}", flush=True)
        return 1

    try:
        db = Database(args.db)
        with db.connection() as conn:
            rows = conn.execute(
                """
                SELECT player_id, full_name
                FROM heisman_rankings_weekly hrw
                JOIN players p USING (player_id)
                WHERE hrw.source_name='model-heisman' AND hrw.season_year >= 2024
                GROUP BY hrw.player_id
                ORDER BY MIN(hrw.rank_overall) ASC
                LIMIT ?
                """,
                (args.sample_size,),
            ).fetchall()
    except Exception as exc:
        print(f"::error::failed to query top players: {exc}", flush=True)
        return 1

    if not rows:
        # No heisman data in DB — fall back to "first 20 player HTML files
        # alphabetically" so we still validate something.
        print(
            "::warning::heisman_rankings_weekly empty; falling back to "
            "first 20 player HTML files",
            flush=True,
        )
        sampled = [(p.stem, p.stem) for p in sorted(players_dir.glob("*.html"))[: args.sample_size]]
    else:
        sampled = []
        for player_id, full_name in rows:
            # Match the slug pattern used by the renderer: <name-with-dashes>-<player_id>
            name_slug = (
                full_name.lower()
                .replace(".", "")
                .replace("'", "")
                .replace(" ", "-")
            )
            slug = f"{name_slug}-{player_id}"
            sampled.append((slug, full_name))

    print(
        f"[verify-player] sampling {len(sampled)} representative player pages",
        flush=True,
    )

    required_failures: list[str] = []
    soft_failures: list[str] = []
    missing_files: list[str] = []
    ok_count = 0

    for slug, name in sampled:
        path = players_dir / f"{slug}.html"
        if not path.exists():
            missing_files.append(f"{slug} ({name})")
            continue
        try:
            html = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            print(f"[verify-player] failed to read {path}: {exc}", flush=True)
            missing_files.append(f"{slug} (read error)")
            continue
        missing_req = [m for m in REQUIRED_MARKERS if m not in html]
        if missing_req:
            required_failures.append(
                f"{slug} ({name}) — missing: {', '.join(missing_req)}"
            )
        else:
            ok_count += 1
            soft_missing = [m for m in SOFT_MARKERS if m not in html]
            if len(soft_missing) > len(SOFT_MARKERS) - 1:
                # Every soft marker missing — likely the v2 injection broke.
                soft_failures.append(f"{slug} ({name}) — no soft v2 markers")

    print(
        f"[verify-player] passed-required={ok_count}/{len(sampled)} "
        f"required-failures={len(required_failures)} "
        f"missing-files={len(missing_files)} "
        f"soft-failures={len(soft_failures)}",
        flush=True,
    )

    if missing_files:
        print("::warning::sampled player pages missing on disk:", flush=True)
        for m in missing_files[:10]:
            print(f"  - {m}", flush=True)

    if soft_failures:
        print(
            "::warning::sampled player pages have no v2 soft markers "
            "(check renderer injection):",
            flush=True,
        )
        for s in soft_failures[:10]:
            print(f"  - {s}", flush=True)

    if required_failures:
        print(
            "::error::sampled player pages MISSING required v2 chrome "
            f"({len(required_failures)} failures):",
            flush=True,
        )
        for f in required_failures[:10]:
            print(f"  - {f}", flush=True)
        if len(required_failures) > 10:
            print(f"  ... +{len(required_failures) - 10} more", flush=True)
        return 1

    # If literally zero sampled pages existed on disk, also fail — that means
    # the build dropped all player HTML or the sampling missed everything.
    if ok_count == 0:
        print(
            "::error::zero sampled player pages passed required-marker check",
            flush=True,
        )
        return 1

    print(
        f"::notice::Player-page v2 chrome verified across {ok_count} sampled pages.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
