"""Tiered adapter orchestrator — Autopilot v1 TASK 8.3.

Replaces per-adapter steps in GitHub Actions workflows with a single
invocation:

    python scripts/run_all_adapters.py --tier hourly
    python scripts/run_all_adapters.py --tier daily
    python scripts/run_all_adapters.py --tier weekly

Each tier runs a fixed list of subprocess commands. Every individual
adapter is allowed to fail; its own `scrape_health` row records the
status. The orchestrator always exits 0 so the cron doesn't give up.

Secret-gating: auth-required adapters short-circuit if their env var
is missing. YouTube/SeatGeek/Spotify adapters already do this at the
Python level; the orchestrator's extra gate is belt-and-suspenders.

At end of tier: prints a summary of (adapter, duration, exit_code)
lines so the Actions log is legible.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _python() -> str:
    return sys.executable


def _manage(subcommand: str, *args: str) -> list[str]:
    return [_python(), "-u", str(ROOT / "manage.py"), subcommand, *args]


def _run_adapter(name: str) -> list[str]:
    return [_python(), "-u", str(ROOT / "tools" / "run_adapter.py"), name]


def _requires_secret(env_var: str) -> bool:
    val = os.environ.get(env_var, "").strip()
    return bool(val)


def _in_cfb_season(today: date | None = None) -> bool:
    today = today or date.today()
    return (today.month >= 8) or (today.month == 1)


def _current_cfb_week(today: date | None = None) -> int:
    from datetime import date as _d
    today = today or _d.today()
    if not _in_cfb_season(today):
        return 0
    anchor_year = today.year if today.month >= 8 else today.year - 1
    anchor = _d(anchor_year, 8, 20)
    return max(1, min(16, (today - anchor).days // 7 + 1))


def _hourly_steps() -> list[tuple[str, list[str]]]:
    steps: list[tuple[str, list[str]]] = [
        ("kalshi", _run_adapter("kalshi")),
        ("polymarket", _run_adapter("polymarket")),
        ("gdelt_volume", _run_adapter("gdelt_volume")),
        ("bluesky_curated", _run_adapter("bluesky_curated")),
        ("bluesky_feeds", _run_adapter("bluesky_feeds")),
        ("google_news_all", _run_adapter("google_news_all")),
    ]
    if _requires_secret("YOUTUBE_API_KEY"):
        steps.append(("youtube_meta", _run_adapter("youtube_meta")))
    if _requires_secret("SEATGEEK_CLIENT_ID"):
        steps.append(("seatgeek", _run_adapter("seatgeek")))
    if _in_cfb_season():
        season = os.environ.get("CURRENT_CFB_SEASON", str(date.today().year))
        week = _current_cfb_week()
        steps.append((
            "cfbd_sync_incremental",
            _manage(
                "sync-site-incremental",
                "--season", season,
                "--through-week", str(week),
                "--skip-play-level",
                "--skip-heisman",
                "--skip-connectivity-check",
            ),
        ))
    return steps


def _daily_steps() -> list[tuple[str, list[str]]]:
    return [
        ("wiki_pv", _run_adapter("wiki_pv")),
        ("wiki_edits", _run_adapter("wiki_edits")),
        ("campus_news_all", _run_adapter("campus_news_all")),
        ("athletics_all", _run_adapter("athletics_all")),
        ("locked_on_all", _run_adapter("locked_on_all")),
        ("beat_writers_all", _run_adapter("beat_writers_all")),
        ("substack_all", _run_adapter("substack_all")),
    ]


def _weekly_steps() -> list[tuple[str, list[str]]]:
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    week_label = f"{iso_year}-{iso_week:02d}"
    steps: list[tuple[str, list[str]]] = [
        ("spotify_charts", _run_adapter("spotify_charts")),
        ("compute_cohort_week", _manage("compute-cohort-week", "--week", week_label)),
        ("compute_divergence", _manage("compute-divergence", "--week", week_label)),
        ("build_methodology", _manage("build-methodology")),
        ("build_freshness", _manage("build-freshness")),
        ("build_site", _manage("build-site")),
    ]
    # NFL-draft scraper: run during draft week (late April) or once monthly.
    if today.month == 4 and 20 <= today.day <= 30:
        steps.insert(
            1,
            ("ingest_nfl_draft", _manage("ingest-nfl-draft", "--year", str(today.year))),
        )
    return steps


TIERS = {
    "hourly": _hourly_steps,
    "daily": _daily_steps,
    "weekly": _weekly_steps,
}


def _three_fail_sources() -> list[str]:
    """Return source_ids whose last 3 scrape_health runs are all 'error'.

    Defensive against missing table — returns [] if scrape_health is
    not yet populated.
    """
    import sqlite3
    db_path = ROOT / "cfb_rankings.db"
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT source_id, COUNT(*) AS fails
            FROM (
                SELECT source_id, status,
                    ROW_NUMBER() OVER (PARTITION BY source_id ORDER BY run_date DESC) rn
                FROM scrape_health
            )
            WHERE rn <= 3 AND status = 'error'
            GROUP BY source_id HAVING COUNT(*) = 3
            ORDER BY source_id
            """
        ).fetchall()
        return [r["source_id"] for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _deactivate_source(source_id: str) -> None:
    """Set source_registry.is_active=0 for a source that crossed the threshold."""
    import sqlite3
    db_path = ROOT / "cfb_rankings.db"
    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute(
            "UPDATE source_registry SET is_active = 0 WHERE source_id = ?",
            (source_id,),
        )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as exc:
        print(f"  [warn] deactivate {source_id} failed: {exc}")


def _emit_followup(source_ids: list[str], tier: str) -> None:
    """Write a dated heading + bullet list to docs/audits/autopilot_followups.md.

    Also tries `gh issue create`; falls back silently if gh is not on PATH.
    """
    if not source_ids:
        return
    from datetime import datetime
    followup = ROOT / "docs" / "audits" / "autopilot_followups.md"
    followup.parent.mkdir(parents=True, exist_ok=True)
    heading = f"\n## {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} — 3-fail sources auto-deactivated (tier={tier})\n\n"
    bullets = "\n".join(
        f"- `{sid}` — set `source_registry.is_active=0` after 3 consecutive errors."
        for sid in source_ids
    )
    entry = heading + bullets + "\n\n---\n"
    existing = followup.read_text(encoding="utf-8") if followup.exists() else ""
    followup.write_text(entry + existing, encoding="utf-8")
    print(f"  [followup] wrote {len(source_ids)} entry/entries to {followup}")

    # Best-effort: try to file a GitHub issue.
    try:
        subprocess.run(
            [
                "gh", "issue", "create",
                "--title", f"Autopilot: {len(source_ids)} source(s) at 3-fail threshold ({tier})",
                "--body", "Auto-deactivated:\n\n" + bullets,
                "--label", "autopilot,data-health",
            ],
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # gh not installed or slow — followup file is the durable record


def run_tier(tier: str, dry_run: bool = False) -> int:
    steps_fn = TIERS.get(tier)
    if steps_fn is None:
        print(f"unknown tier: {tier}", file=sys.stderr)
        return 2
    steps = steps_fn()
    print(f"[orchestrator] tier={tier} steps={len(steps)}")
    results: list[tuple[str, float, int]] = []
    for name, argv in steps:
        t0 = time.time()
        if dry_run:
            print(f"  [DRY-RUN] {name}: {' '.join(argv)}")
            results.append((name, 0.0, 0))
            continue
        try:
            proc = subprocess.run(argv, cwd=str(ROOT))
            exit_code = proc.returncode
        except Exception as exc:  # pragma: no cover — defensive
            print(f"  [EXC] {name}: {exc}")
            exit_code = 99
        dur = time.time() - t0
        status = "OK" if exit_code == 0 else f"FAIL({exit_code})"
        print(f"  [{status}] {name} — {dur:.1f}s")
        results.append((name, dur, exit_code))
    print()
    print("[orchestrator] summary")
    for name, dur, exit_code in results:
        status = "OK" if exit_code == 0 else f"FAIL({exit_code})"
        print(f"  {status:<9} {dur:>6.1f}s  {name}")

    # TASK 8.4: 3-consecutive-fail alerting. After the tier's runs have
    # written fresh scrape_health rows, look for sources stuck in error
    # and deactivate them + emit a follow-up entry.
    if not dry_run:
        stuck = _three_fail_sources()
        if stuck:
            print(f"\n[orchestrator] {len(stuck)} source(s) at 3-fail threshold:")
            for sid in stuck:
                print(f"  - {sid} (deactivating)")
                _deactivate_source(sid)
            _emit_followup(stuck, tier)

    # Always exit 0: per kickoff autonomy, cron continues even when one
    # adapter errors. Row-level failure lives in scrape_health.
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier", required=True,
        choices=sorted(TIERS.keys()),
        help="Which tier of adapters to run.",
    )
    parser.add_argument("--dry-run", action="store_true",
        help="Print the argv for each step without invoking.")
    args = parser.parse_args()
    return run_tier(args.tier, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
