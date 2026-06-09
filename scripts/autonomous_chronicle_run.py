"""Autonomous Chronicle mass-generation driver.

Designed to run for hours unattended on the Alienware:
  - Enumerates FBS team slugs from `teams` table (level_code='fbs').
  - For each team × card_type, generates a card via the Chronicle pipeline.
  - Persists everything via the normal cache layer.
  - Promotes shipped (high-confidence) cards to LKG immediately.
  - Writes a JSONL progress log so user can tail it: logs/chronicle/autonomous_<ts>.jsonl
  - Handles failures per-card without aborting the whole run.
  - Periodically prints a stats summary.

Usage:
    python scripts/autonomous_chronicle_run.py \
        --tier T3 \
        --max-teams 30 \
        --card-types flashpoint,echo,devil_card,player_arc \
        --season 2024 --week 12

Tier policy:
    T3  fastest (Writer-only, no critics) — 15s/card
    T2  Planner + Writer + FactCritic     — 25s/card
    T1  full 5-agent single-pass          — 30s/card
    S   5-agent + Best-of-3               — 60-90s/card

To run in background (PowerShell):
    Start-Job -ScriptBlock { python scripts/autonomous_chronicle_run.py --tier T3 --max-teams 30 }
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdout on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--tier", choices=["S", "T1", "T2", "T3"], default="T3")
    p.add_argument("--max-teams", type=int, default=30, help="Number of teams to process (0 = all FBS)")
    p.add_argument("--card-types", default="flashpoint,echo,devil_card,player_arc")
    p.add_argument("--season", type=int, default=2024)
    p.add_argument("--week", type=int, default=12)
    p.add_argument("--n-slots", type=int, default=4)
    p.add_argument("--log-dir", default="logs/chronicle")
    p.add_argument("--start-from", default=None, help="Resume from this team slug (sorted alpha)")
    p.add_argument("--max-runtime-min", type=int, default=180, help="Hard wall-clock cap (minutes)")
    p.add_argument("--skip-cached", action="store_true", default=True, help="Skip teams that already have generated cards in cache")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    log_path = Path(args.log_dir) / f"autonomous_{args.tier}_{ts}.jsonl"
    summary_path = Path(args.log_dir) / f"autonomous_{args.tier}_{ts}_summary.txt"

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Lazy imports so dependency errors surface late
    from cfb_rankings.db import Database
    from cfb_rankings.chronicle.runtime import build_default_router, CardTier
    from cfb_rankings.chronicle.pipeline import generate_page_cards, PipelineConfig, PageTarget

    print(f"=== Chronicle autonomous run starting ===")
    print(f"  tier:        {args.tier}")
    print(f"  max-teams:   {args.max_teams}")
    print(f"  card-types:  {args.card_types}")
    print(f"  season/week: {args.season} / {args.week}")
    print(f"  log:         {log_path}")
    print(f"  max-runtime: {args.max_runtime_min} min")
    print()

    db = Database("cfb_rankings.db")
    router = build_default_router(allow_cloud=False)

    for r in router.routes:
        tiers = ",".join(t.value for t in r.tier_eligible)
        print(f"  route role={r.role:8s} tiers=[{tiers:8s}] backend={r.backend.name}")
    print()

    tier_enum = CardTier[args.tier]
    config = PipelineConfig.for_tier(tier_enum)
    # For autonomous run, be tolerant of voice/quality flags — ship the card
    config.voice_critic_blocking = False
    print(f"  config: best_of_n={config.best_of_n_writer}, retries={config.max_refiner_retries}, threshold={config.factscore_threshold}")
    print()

    card_types = [c.strip() for c in args.card_types.split(",") if c.strip()]

    # Get FBS team slugs (level_code is stored uppercase as 'FBS')
    teams_rows = db.query_all(
        "SELECT slug, school_name, canonical_name FROM teams WHERE level_code='FBS' AND is_active=1 ORDER BY slug",
        {},
    )
    teams = [(r["slug"], r["school_name"] or r["canonical_name"]) for r in teams_rows]
    print(f"  found {len(teams)} active FBS teams")

    if args.start_from:
        teams = [t for t in teams if t[0] >= args.start_from]
        print(f"  resuming from '{args.start_from}': {len(teams)} teams remaining")

    if args.max_teams > 0:
        teams = teams[: args.max_teams]
    print(f"  will process {len(teams)} teams × {len(card_types)} card types = up to {len(teams) * len(card_types)} cards")
    print()

    # Skip teams whose cards we've already generated (cache check at team-level)
    if args.skip_cached:
        try:
            cached_rows = db.query_all(
                """
                SELECT DISTINCT slug FROM chronicle_card_cache
                WHERE word_count > 0 AND entity_kind = 'team'
                  AND season_year = :season_year AND week_number = :week_number
                """,
                {"season_year": args.season, "week_number": args.week},
            )
            cached_slugs = {r["slug"] for r in cached_rows}
            if cached_slugs:
                print(f"  skipping {len(cached_slugs)} teams already with cached cards: {sorted(cached_slugs)[:5]}...")
                teams = [t for t in teams if t[0] not in cached_slugs]
                print(f"  filtered to {len(teams)} teams")
        except Exception as exc:
            print(f"  skip-cached check failed (continuing without skip): {exc}")

    if not teams:
        print("  no teams to process — exiting")
        return 0

    # Stats
    stats = {
        "started_at": ts,
        "teams_attempted": 0,
        "teams_succeeded": 0,
        "teams_failed": 0,
        "cards_generated": 0,
        "cards_shipped": 0,
        "cards_shipped_with_flag": 0,
        "cards_failed": 0,
        "cards_suppressed": 0,
        "cards_cache_hit": 0,
        "total_wall_ms": 0,
        "by_card_type": {},
        "first_card_sample": None,
        "errors": [],
    }

    run_start = time.monotonic()
    max_runtime_s = args.max_runtime_min * 60

    def write_log(record: dict) -> None:
        record["_ts"] = datetime.now(timezone.utc).isoformat()
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def write_summary() -> None:
        elapsed = time.monotonic() - run_start
        lines = [
            f"Chronicle autonomous run — {args.tier}",
            f"Started:  {ts}",
            f"Elapsed:  {elapsed/60:.1f} min",
            f"",
            f"Teams attempted:   {stats['teams_attempted']}",
            f"Teams succeeded:   {stats['teams_succeeded']}",
            f"Teams failed:      {stats['teams_failed']}",
            f"",
            f"Cards generated:   {stats['cards_generated']}",
            f"  shipped:         {stats['cards_shipped']}",
            f"  shipped w/flag:  {stats['cards_shipped_with_flag']}",
            f"  cache hits:      {stats['cards_cache_hit']}",
            f"  suppressed:      {stats['cards_suppressed']}",
            f"  failed:          {stats['cards_failed']}",
            f"",
            f"By card type:",
        ]
        for ct, n in sorted(stats["by_card_type"].items()):
            lines.append(f"  {ct:15s} {n}")
        lines.append(f"")
        if stats["first_card_sample"]:
            lines.append(f"First successful card sample:")
            lines.append(f"  {stats['first_card_sample']['team']}/{stats['first_card_sample']['card_type']}:")
            lines.append(f"  {stats['first_card_sample']['body'][:300]}")
        summary_path.write_text("\n".join(lines), encoding="utf-8")

    # Main loop
    for idx, (slug, name) in enumerate(teams):
        elapsed = time.monotonic() - run_start
        if elapsed > max_runtime_s:
            print(f"\n!! Wall-clock budget exhausted ({elapsed/60:.1f}/{args.max_runtime_min} min) — stopping")
            stats["wall_clock_exhausted"] = True
            break

        team_start = time.monotonic()
        print(f"[{idx+1:3d}/{len(teams)}] {slug:30s}  ({name})", end="", flush=True)

        target = PageTarget(
            entity_kind="team",
            slug=slug,
            season_year=args.season,
            week_number=args.week,
            n_slots=args.n_slots,
            tier=tier_enum,
            card_types=card_types,
        )
        stats["teams_attempted"] += 1

        try:
            result = generate_page_cards(db, target, router, config)
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            print(f"  FAILED — {err_msg}")
            stats["teams_failed"] += 1
            stats["errors"].append({"team": slug, "error": err_msg, "trace": traceback.format_exc()[-500:]})
            write_log({"kind": "team_failed", "team": slug, "error": err_msg})
            continue

        team_elapsed_ms = int((time.monotonic() - team_start) * 1000)
        stats["teams_succeeded"] += 1
        stats["total_wall_ms"] += team_elapsed_ms
        stats["cards_generated"] += len(result.cards)
        stats["cards_shipped"] += sum(1 for c in result.cards if c.action == "shipped")
        stats["cards_shipped_with_flag"] += sum(1 for c in result.cards if c.action == "shipped_with_flag")
        stats["cards_cache_hit"] += sum(1 for c in result.cards if c.action == "cache_hit")
        stats["cards_suppressed"] += sum(1 for c in result.cards if c.action == "suppressed")
        stats["cards_failed"] += sum(1 for c in result.cards if c.action == "failed_after_retry")

        ship_n = sum(1 for c in result.cards if c.action in ("shipped", "shipped_with_flag"))
        fail_n = sum(1 for c in result.cards if c.action == "failed_after_retry")
        supp_n = sum(1 for c in result.cards if c.action == "suppressed")
        cache_n = sum(1 for c in result.cards if c.action == "cache_hit")
        # ASCII-only output for Windows cp1252 compatibility
        print(f"  [ev={result.evidence_count:3d}] {ship_n}ship/{fail_n}fail/{supp_n}supp/{cache_n}cache in {team_elapsed_ms/1000:5.1f}s")

        for c in result.cards:
            ct = c.card_type
            stats["by_card_type"][ct] = stats["by_card_type"].get(ct, 0) + 1
            if stats["first_card_sample"] is None and c.draft and c.draft.body_text and c.action in ("shipped", "shipped_with_flag"):
                stats["first_card_sample"] = {
                    "team": slug,
                    "card_type": ct,
                    "body": c.draft.body_text,
                }
            write_log({
                "kind": "card",
                "team": slug,
                "card_type": ct,
                "slot": c.slot_index,
                "action": c.action,
                "attempts": c.attempts_used,
                "word_count": c.draft.word_count if c.draft else 0,
                "body_preview": (c.draft.body_text[:200] if c.draft and c.draft.body_text else None),
                "failure_reason": c.failure_reason,
                "wall_ms": c.wall_clock_ms,
            })

        # Promote shipped cards to LKG
        try:
            import sqlite3
            conn = sqlite3.connect("cfb_rankings.db")
            promo = conn.execute(
                "UPDATE chronicle_card_cache SET is_lkg=1, lkg_promoted_at_utc=datetime('now') WHERE slug=? AND season_year=? AND week_number=? AND word_count>0 AND is_lkg=0",
                (slug, args.season, args.week),
            )
            conn.commit()
            conn.close()
            if promo.rowcount > 0:
                write_log({"kind": "lkg_promote", "team": slug, "count": promo.rowcount})
        except Exception as exc:
            write_log({"kind": "lkg_promote_failed", "team": slug, "error": str(exc)})

        # Periodic summary every 5 teams
        if (idx + 1) % 5 == 0:
            write_summary()

    write_summary()
    elapsed = time.monotonic() - run_start
    print()
    print(f"=== DONE ===")
    print(f"  elapsed:  {elapsed/60:.1f} min")
    print(f"  shipped:  {stats['cards_shipped']}")
    print(f"  flagged:  {stats['cards_shipped_with_flag']}")
    print(f"  failed:   {stats['cards_failed']}")
    print(f"  summary:  {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
