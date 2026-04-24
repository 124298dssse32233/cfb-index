"""Reddit historical backfill runner — Autopilot v1 TASK 2.2.

Reads seeds/reddit_historical_plan.yaml, partitions each source's
date range into N-day windows, and invokes
`python manage.py collect-reddit-plan` once per window.

Provider policy:
    1. Try arctic-shift first.
    2. On failure (non-zero exit or 429s), retry once with pullpush.
    3. On repeated failure, log a scrape_health row with
       status='error' and move on (per kickoff autonomy).

State:
    data/reddit_backfill_state.json — JSON checkpoint of every
    completed (source_key, window_start) pair with status. Re-runs
    skip already-completed pairs so the script is restart-safe.

Usage:
    python scripts/backfill_reddit_history.py --dry-run
    python scripts/backfill_reddit_history.py --commit
    python scripts/backfill_reddit_history.py --commit --only alabama_team
    python scripts/backfill_reddit_history.py --commit --limit-windows 50
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "seeds" / "reddit_historical_plan.yaml"
STATE_PATH = ROOT / "data" / "reddit_backfill_state.json"
DB_PATH = ROOT / "cfb_rankings.db"


# ---------------------------------------------------------------------------
# Plan expansion
# ---------------------------------------------------------------------------


def _load_plan() -> dict:
    with PLAN_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_date(raw: str | date) -> date:
    if isinstance(raw, date):
        return raw
    if raw == "today":
        return date.today()
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _resolve_season_week(d: date) -> tuple[int, int]:
    """Map a calendar date to (season_year, week).

    Season = the academic-year fall kickoff (Aug-onward gets that year).
    Week = (d - Aug 20 of season) // 7 + 1, clamped 1..25.
    Offseason dates map to weeks 18-25 (spring / summer).
    """
    season = d.year if d.month >= 8 else d.year - 1
    anchor = date(season, 8, 20)
    weeks = (d - anchor).days // 7 + 1
    week = max(1, min(25, weeks))
    return season, week


def expand_windows(plan: dict) -> list[dict]:
    """Return a list of {source_key, subreddit, audience_bucket,
    team_name, after_iso, before_iso, season, week} windows.
    """
    defaults = plan.get("defaults", {})
    start = _parse_date(defaults.get("windows_start", "2022-09-01"))
    end = _parse_date(defaults.get("windows_end", "today"))
    window_days = int(defaults.get("window_days", 7))
    windows: list[dict] = []
    for source in plan["sources"]:
        key = source["key"]
        subreddit = source["subreddit"]
        bucket = source["audience_bucket"]
        team_name = source.get("team_name")
        cursor = start
        while cursor < end:
            window_end = min(cursor + timedelta(days=window_days), end)
            season, week = _resolve_season_week(cursor)
            windows.append(
                {
                    "source_key": key,
                    "subreddit": subreddit,
                    "audience_bucket": bucket,
                    "team_name": team_name,
                    "after_iso": cursor.isoformat(),
                    "before_iso": window_end.isoformat(),
                    "season": season,
                    "week": week,
                    "mode": source.get("mode", defaults.get("mode", "subreddit_listing")),
                }
            )
            cursor = window_end
    return windows


# ---------------------------------------------------------------------------
# Checkpoint state
# ---------------------------------------------------------------------------


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"completed": {}, "errors": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"completed": {}, "errors": {}}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _window_key(window: dict) -> str:
    return f"{window['source_key']}|{window['after_iso']}"


# ---------------------------------------------------------------------------
# Invocation
# ---------------------------------------------------------------------------


def _build_plan_json(window: dict) -> dict | None:
    entry = {
        "mode": window["mode"],
        "subreddit": window["subreddit"],
        "audience_bucket": window["audience_bucket"],
        "after": window["after_iso"],
        "before": window["before_iso"],
        "limit": 100,
        "replace_existing": False,
    }
    if window["mode"] == "subreddit_listing":
        # collect-reddit-plan's subreddit_listing mode requires a real team
        # name to attribute rows. The r/CFB sitewide row (team_name is None)
        # doesn't map cleanly onto this API — skip at runtime by returning
        # a sentinel; caller filters out these windows.
        if not window["team_name"]:
            return None  # caller will skip
        entry["team"] = window["team_name"]
        entry["listing"] = "new"
        entry["require_cfb_context"] = window["subreddit"].upper() == "CFB"
    else:
        entry["teams"] = [window["team_name"]] if window["team_name"] else []
    return {"sources": [entry]}


def _run_manage_py(plan_path: Path, window: dict, provider: str, timeout: int) -> tuple[int, str]:
    cmd = [
        sys.executable,
        "-u",
        str(ROOT / "manage.py"),
        "collect-reddit-plan",
        "--season",
        str(window["season"]),
        "--week",
        str(window["week"]),
        "--plan",
        str(plan_path),
        "--provider",
        provider,
        "--after",
        window["after_iso"],
        "--before",
        window["before_iso"],
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
        )
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode, out
    except subprocess.TimeoutExpired as exc:
        return 124, f"TIMEOUT after {timeout}s: {exc}"


def _record_scrape_health(
    source_key: str, window: dict, status: str, error_message: str | None
) -> None:
    """Write one scrape_health row per window."""
    import sqlite3

    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    try:
        conn.execute(
            "insert or replace into scrape_health "
            "(source_id, run_date, rows_inserted, status, error_message) "
            "values (?, ?, ?, ?, ?)",
            (
                f"reddit_backfill_{source_key}",
                window["after_iso"],
                None,
                status,
                (error_message or "")[:1000],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def backfill_one(
    window: dict,
    state: dict,
    primary: str,
    fallback: str,
    timeout: int,
    commit: bool,
) -> str:
    """Backfill a single window. Returns status string."""
    key = _window_key(window)
    if key in state["completed"] and state["completed"][key] == "ok":
        return "skipped-completed"

    plan_json = _build_plan_json(window)
    if plan_json is None:
        state["completed"][key] = "skipped-unsupported"
        return "skipped-completed"

    if not commit:
        print(f"[DRY-RUN] {key} -> mode={window['mode']} "
              f"sub={window['subreddit']} bucket={window['audience_bucket']} "
              f"season={window['season']} week={window['week']}")
        return "dry-run"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(plan_json, tmp)
        tmp_path = Path(tmp.name)

    try:
        for attempt, provider in enumerate([primary, fallback], start=1):
            exit_code, stdout = _run_manage_py(tmp_path, window, provider, timeout)
            if exit_code == 0:
                state["completed"][key] = "ok"
                _record_scrape_health(window["source_key"], window, "ok", None)
                print(f"[OK provider={provider}] {key}")
                return "ok"
            # Exponential backoff on HTTP 429
            if "429" in stdout or "rate" in stdout.lower():
                sleep_s = min(60, 2 ** attempt * 5)
                print(f"[RATE-LIMIT provider={provider}] {key} — sleeping {sleep_s}s")
                time.sleep(sleep_s)
                continue
        # Both providers failed.
        state["errors"][key] = stdout[-500:] if stdout else "unknown error"
        _record_scrape_health(window["source_key"], window, "error", stdout[:500])
        print(f"[FAIL] {key}\n    {stdout[-1200:]}")
        return "error"
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
        help="List the windows that would be processed. No DB writes, no subprocesses.")
    parser.add_argument("--commit", action="store_true",
        help="Actually run. Mutually exclusive with --dry-run.")
    parser.add_argument("--only", default=None,
        help="Limit to one source_key (e.g. alabama_team).")
    parser.add_argument("--limit-windows", type=int, default=None,
        help="Optional cap on total windows to process this run.")
    parser.add_argument("--timeout", type=int, default=300,
        help="Per-window subprocess timeout (seconds). Default 300.")
    args = parser.parse_args()

    if not args.dry_run and not args.commit:
        print("Refusing to run without --dry-run or --commit. Exiting.")
        return 2

    plan = _load_plan()
    defaults = plan.get("defaults", {})
    primary = defaults.get("provider_primary", "arctic-shift")
    fallback = defaults.get("provider_fallback", "pullpush")

    windows = expand_windows(plan)
    if args.only:
        windows = [w for w in windows if w["source_key"] == args.only]
    if args.limit_windows:
        windows = windows[: args.limit_windows]

    print(f"[plan] {len(windows)} windows queued. primary={primary} fallback={fallback}")

    state = _load_state()
    print(f"[state] {len(state.get('completed', {}))} already completed")

    t0 = time.time()
    per_status = {"ok": 0, "error": 0, "skipped-completed": 0, "dry-run": 0}
    for i, window in enumerate(windows, start=1):
        status = backfill_one(window, state, primary, fallback, args.timeout, args.commit)
        per_status[status] = per_status.get(status, 0) + 1
        if args.commit and (i % 20 == 0 or i == len(windows)):
            _save_state(state)
            elapsed = time.time() - t0
            print(f"[checkpoint] {i}/{len(windows)} "
                  f"ok={per_status['ok']} err={per_status['error']} "
                  f"skip={per_status['skipped-completed']} "
                  f"elapsed={elapsed:.0f}s")
    if args.commit:
        _save_state(state)

    print(f"[done] {per_status}")
    return 0 if per_status.get("error", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
