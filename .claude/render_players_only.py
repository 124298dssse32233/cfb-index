"""One-off — re-render all player HTML pages without doing a full site build.

Uses build_player_page_data_map + render_player_page_html on whatever
players currently sit in player_directory rows for the inferred season.

Usage: python .claude/render_players_only.py [--limit N]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0,
                   help="Render only N player pages (0 = all). Useful for smoke testing.")
    p.add_argument("--slug", type=str, default=None,
                   help="Render only player(s) whose slug contains this substring.")
    args = p.parse_args()

    from cfb_rankings.db import Database
    from cfb_rankings.reporting import (
        build_player_page_data_map,
        render_player_page_html,
    )
    # Use the same directory-rows query that reporting.py uses internally.
    db = Database("sqlite:///cfb_rankings.db")

    # Infer season from most recent heisman row
    season_row = db.query_one(
        "SELECT MAX(season_year) AS s FROM heisman_rankings_weekly"
    )
    season = int((season_row or {}).get("s") or 2024)
    summary = {"season_year": season, "week": 16, "model_version": "render-only"}

    # Use the same directory query that publish_site uses — players with a
    # heisman row OR a season-stats row OR a recruiting profile.
    sql = """
        SELECT DISTINCT p.player_id,
               COALESCE(p.full_name, '') AS player_name,
               COALESCE(p.position, '') AS position,
               lower(replace(replace(replace(replace(replace(replace(
                 COALESCE(p.full_name, 'player'),
                 ' ', '-'), '.', ''), ',', ''), '''', ''), '''', ''), '"', ''))
                 || '-' || p.player_id AS player_slug
          FROM players p
         WHERE EXISTS (
             SELECT 1 FROM heisman_rankings_weekly h
              WHERE h.player_id = p.player_id AND h.season_year = :s
                AND h.rank_overall IS NOT NULL
         )
            OR EXISTS (
             SELECT 1 FROM player_honors h
              WHERE h.player_id = p.player_id AND h.season_year = :s
         )
    """
    rows = db.query_all(sql, {"s": season})
    if args.slug:
        rows = [r for r in rows if args.slug in (r.get("player_slug") or "")]
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    print(f"[render-players] season={season} candidates={len(rows)}")
    if not rows:
        print("[render-players] no candidates — bailing")
        return

    t0 = time.time()
    page_map = build_player_page_data_map(db, summary, list(rows))
    elapsed_build = time.time() - t0
    print(f"[render-players] built {len(page_map)} payloads in {elapsed_build:.1f}s")

    players_dir = ROOT / "output" / "site" / "players"
    players_dir.mkdir(parents=True, exist_ok=True)
    n_written = 0
    n_failed = 0
    t0 = time.time()
    for slug, page_data in page_map.items():
        try:
            html = render_player_page_html(summary, page_data)
            (players_dir / f"{slug}.html").write_text(html, encoding="utf-8")
            n_written += 1
        except Exception as exc:
            n_failed += 1
            if n_failed <= 5:
                print(f"  {slug}: {type(exc).__name__}: {exc}", flush=True)
    print(
        f"[render-players] wrote {n_written} pages "
        f"({n_failed} failed) in {time.time() - t0:.1f}s"
    )


if __name__ == "__main__":
    main()
