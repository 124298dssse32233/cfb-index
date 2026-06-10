"""Per-source silent-degradation detector for the daily collect job.

THE BUG THIS PREVENTS (source-expansion risk register, 2026-06):
The Reddit `.json` provider silently dropped to 0 rows for ~10 days in
May 2026 and nobody noticed. The healthchecks.io dead-man's-switch only
fires on whole-JOB failure (collect.ps1 exits non-zero); it is blind to a
single source quietly going to zero while every other source keeps the
job green. `scrape_health` recorded `status=empty, rows_inserted=0` for
the dead Reddit sources — which is *legitimate* for a genuinely quiet feed
— so a naive "rows < N" floor would either miss this or false-alarm
constantly on offseason markets and dedup-zeros.

THE FIX — baseline-aware, NOT a flat floor:
For each source we look at its own trailing history in `scrape_health`
and only alert when an ESTABLISHED source (one that was producing rows on
several recent days) goes dark:
  * SILENT  — the last K runs are all 0 rows, but the source was active
              (>0 rows) on >= MIN_ACTIVE_DAYS days earlier in the window.
  * STALE   — the source has not run at all for longer than its own normal
              cadence allows, despite running regularly before.
Sources that are legitimately intermittent (offseason betting markets,
Spotify/SeatGeek, the Wikimedia rolling-window re-fetch that dedups to 0)
are declared in seeds/source_health_floors.yaml and skipped. Brand-new or
genuinely-quiet sources (too few active days to have a baseline) are not
judged — we only flag a source that *used to* work and stopped.

On degradation the script can open (or reuse) a single GitHub issue via
`gh` (authed on the box) so it reaches Kevin without a human watching logs.

Usage (wired into scripts/collect.ps1 before Complete-Pipeline):
    python scripts/verify_source_health_floors.py --open-issue

Exit codes (mirrors verify_db_artifact_healthy.py):
    0 = all established sources healthy (or only intermittent ones quiet)
    1 = one or more established sources degraded (silent or stale)
    2 = scrape_health unreadable / DB missing (a real failure to surface)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────
# Defaults. Overridable per-source in seeds/source_health_floors.yaml and via
# CLI flags. Chosen for the daily (05:00) collect cadence.
# ─────────────────────────────────────────────────────────────────────────
DEFAULT_WINDOW_DAYS = 21      # trailing history to judge against
DEFAULT_MIN_ACTIVE_DAYS = 5   # >= this many >0-row days => "established"
DEFAULT_CONSECUTIVE_ZERO = 3  # last K runs all 0 => silent
DEFAULT_STALE_DAYS = 3        # floor on the cadence-aware staleness threshold

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = str(_REPO_ROOT / "cfb_rankings.db")
_DEFAULT_YAML = _REPO_ROOT / "seeds" / "source_health_floors.yaml"
_ISSUE_LABEL = "data-health"


def _load_overrides(yaml_path: Path) -> dict:
    """Load per-source overrides. Returns {} if the file or PyYAML is absent."""
    if not yaml_path.exists():
        return {}
    try:
        import yaml  # PyYAML is a project dep
    except Exception:  # noqa: BLE001 — never let a missing optional dep break the gate
        print(f"::warning::PyYAML unavailable; ignoring {yaml_path.name}")
        return {}
    try:
        with open(yaml_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::could not parse {yaml_path.name}: {exc}")
        return {}


def _parse_date(s: str) -> _dt.date | None:
    """scrape_health.run_date is 'YYYY-MM-DD' (UTC-derived)."""
    if not s:
        return None
    try:
        return _dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def _classify_source(
    runs: list[tuple[_dt.date, int, str]],
    today: _dt.date,
    *,
    min_active_days: int,
    consecutive_zero: int,
    stale_days: int,
) -> dict | None:
    """Judge one source from its run history (newest-first).

    `runs` is [(run_date, rows_inserted, status), ...] already filtered to the
    window and to non-'skipped' rows. Returns a finding dict if degraded, else
    None. Returns None when there is too little baseline to judge.
    """
    if not runs:
        return None
    active = [(d, n) for (d, n, _st) in runs if n > 0]
    active_days = len(active)
    if active_days < min_active_days:
        return None  # not established enough to have a trustworthy baseline

    typical = int(statistics.median(n for _d, n in active))
    last_date = runs[0][0]
    days_since_last = (today - last_date).days

    # Cadence-aware staleness: allow the source's own normal gap + slack.
    dates = [d for d, _n, _st in runs]
    gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
    max_gap = max(gaps) if gaps else 1
    stale_threshold = max(stale_days, max_gap + 1)
    if days_since_last > stale_threshold:
        return {
            "kind": "stale",
            "typical_rows": typical,
            "active_days": active_days,
            "days_since_last": days_since_last,
            "last_date": last_date.isoformat(),
            "detail": (
                f"no run in {days_since_last}d (normal gap <= {max_gap}d); "
                f"was active {active_days}/{len(runs)} runs (~{typical} rows/run)"
            ),
        }

    # Silent: the most recent K runs are all zero, but the source was active
    # earlier in the window. (Needs >= K runs to make the call.)
    if len(runs) >= consecutive_zero:
        last_k = runs[:consecutive_zero]
        if all(n == 0 for _d, n, _st in last_k):
            return {
                "kind": "silent",
                "typical_rows": typical,
                "active_days": active_days,
                "zero_runs": consecutive_zero,
                "last_date": last_date.isoformat(),
                "detail": (
                    f"last {consecutive_zero} runs all 0 rows; was active "
                    f"{active_days}/{len(runs)} runs (~{typical} rows/run) — "
                    f"likely a broken source, not a quiet one"
                ),
            }
    return None


def _family(source_id: str) -> str:
    """Collapse per-entity ids to a family for readable grouped alerts.

    reddit_team_alabama -> reddit_team ; google_news_alabama -> google_news.
    Falls back to the whole id when there's nothing to strip.
    """
    import re
    fam = re.sub(r"_[a-z0-9][a-z0-9-]*$", "", source_id)
    return fam or source_id


def verify(
    db_path: str,
    overrides: dict,
    *,
    window_days: int,
    min_active_days: int,
    consecutive_zero: int,
    stale_days: int,
    today: _dt.date,
) -> tuple[bool, list[dict], dict]:
    """Return (healthy, findings, stats). healthy=False iff any finding."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    src_over = (overrides.get("sources") or {}) if isinstance(overrides, dict) else {}
    ignore = set(overrides.get("ignore") or []) if isinstance(overrides, dict) else set()
    defaults = overrides.get("defaults") or {} if isinstance(overrides, dict) else {}
    win = int(defaults.get("window_days", window_days))

    # Read-only connect so we never contend with a writer.
    uri = f"file:{Path(db_path).as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.execute("PRAGMA busy_timeout=8000")
    cutoff = (today - _dt.timedelta(days=win)).isoformat()
    rows = conn.execute(
        """
        select source_id, run_date, coalesce(rows_inserted, 0), status
          from scrape_health
         where run_date >= ?
         order by source_id asc, run_date desc
        """,
        (cutoff,),
    ).fetchall()
    conn.close()

    by_source: dict[str, list[tuple[_dt.date, int, str]]] = {}
    for sid, rdate, n, status in rows:
        if (status or "") == "skipped":
            continue  # intentionally off, not silently broken
        d = _parse_date(rdate)
        if d is None:
            continue
        by_source.setdefault(sid, []).append((d, int(n), status or ""))

    findings: list[dict] = []
    judged = 0
    skipped_intermittent = 0
    for sid, runs in by_source.items():
        if sid in ignore:
            continue
        ov = src_over.get(sid, {}) if isinstance(src_over, dict) else {}
        if ov.get("intermittent") or ov.get("ignore"):
            skipped_intermittent += 1
            continue
        judged += 1
        finding = _classify_source(
            runs,
            today,
            min_active_days=int(ov.get("min_active_days", defaults.get("min_active_days", min_active_days))),
            consecutive_zero=int(ov.get("consecutive_zero", defaults.get("consecutive_zero", consecutive_zero))),
            stale_days=int(ov.get("stale_days", defaults.get("stale_days", stale_days))),
        )
        if finding:
            finding["source_id"] = sid
            findings.append(finding)

    findings.sort(key=lambda f: (f["kind"], -f["typical_rows"], f["source_id"]))
    stats = {
        "sources_in_window": len(by_source),
        "judged": judged,
        "skipped_intermittent": skipped_intermittent,
        "degraded": len(findings),
        "window_days": win,
    }
    return (len(findings) == 0), findings, stats


def _render_report(findings: list[dict]) -> str:
    """Human/issue-body rendering, grouped by family so a 118-source Reddit
    outage is one readable block, not 118 lines."""
    by_fam: dict[str, list[dict]] = {}
    for f in findings:
        by_fam.setdefault(_family(f["source_id"]), []).append(f)
    lines: list[str] = []
    for fam, fs in sorted(by_fam.items(), key=lambda kv: -len(kv[1])):
        kinds = {f["kind"] for f in fs}
        lines.append(f"### {fam} — {len(fs)} source(s) degraded [{', '.join(sorted(kinds))}]")
        for f in fs[:8]:
            lines.append(f"- `{f['source_id']}`: {f['detail']}")
        if len(fs) > 8:
            lines.append(f"- …and {len(fs) - 8} more in this family")
        lines.append("")
    return "\n".join(lines).strip()


def _open_or_reuse_issue(title_date: str, body: str) -> None:
    """Open one data-health issue/day via gh. No-op (logged) if gh is missing
    or unauthed — the printed report still surfaces the problem in the log."""
    gh = shutil.which("gh")
    if not gh:
        print("::warning::gh not on PATH; skipping issue creation (see log report above)")
        return
    title = f"data-health: source degradation detected ({title_date})"
    try:
        # Idempotency: skip if an open data-health issue already names today.
        existing = subprocess.run(
            [gh, "issue", "list", "--label", _ISSUE_LABEL, "--state", "open",
             "--search", title_date, "--json", "number", "--limit", "20"],
            capture_output=True, text=True, timeout=60,
        )
        if existing.returncode == 0 and existing.stdout.strip() not in ("", "[]"):
            print(f"   (open {_ISSUE_LABEL} issue for {title_date} already exists; not duplicating)")
            return
        # Ensure the label exists (ignore 'already exists').
        subprocess.run([gh, "label", "create", _ISSUE_LABEL, "--color", "B60205",
                        "--description", "A data source silently stopped producing rows"],
                       capture_output=True, text=True, timeout=60)
        created = subprocess.run(
            [gh, "issue", "create", "--label", _ISSUE_LABEL, "--title", title, "--body", body],
            capture_output=True, text=True, timeout=60,
        )
        if created.returncode == 0:
            print(f"   opened {_ISSUE_LABEL} issue: {created.stdout.strip()}")
        else:
            print(f"::warning::gh issue create failed: {created.stderr.strip()}")
    except Exception as exc:  # noqa: BLE001 — alerting must never crash the gate
        print(f"::warning::issue creation errored: {exc}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Baseline-aware per-source health gate.")
    p.add_argument("db_path", nargs="?", default=_DEFAULT_DB)
    p.add_argument("--yaml", default=str(_DEFAULT_YAML), help="per-source overrides")
    p.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS)
    p.add_argument("--min-active-days", type=int, default=DEFAULT_MIN_ACTIVE_DAYS)
    p.add_argument("--consecutive", type=int, default=DEFAULT_CONSECUTIVE_ZERO)
    p.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    p.add_argument("--open-issue", action="store_true",
                   help="open a gh issue on degradation (default: report only)")
    p.add_argument("--today", default=None, help="override 'today' (YYYY-MM-DD), for testing")
    p.add_argument("--json", action="store_true", help="emit machine-readable findings")
    args = p.parse_args(argv)

    today = _parse_date(args.today) or _dt.date.today()
    overrides = _load_overrides(Path(args.yaml))

    try:
        healthy, findings, stats = verify(
            args.db_path, overrides,
            window_days=args.window_days, min_active_days=args.min_active_days,
            consecutive_zero=args.consecutive, stale_days=args.stale_days, today=today,
        )
    except FileNotFoundError as exc:
        print(f"::error::DB not found: {exc}")
        return 2
    except sqlite3.OperationalError as exc:
        # scrape_health missing/locked beyond timeout — a real failure to surface.
        print(f"::error::scrape_health unreadable: {exc}")
        return 2

    if args.json:
        print(json.dumps({"healthy": healthy, "stats": stats, "findings": findings}, indent=2))

    if healthy:
        print(f"source health OK: judged {stats['judged']} established source(s), "
              f"{stats['skipped_intermittent']} intermittent skipped, 0 degraded "
              f"({stats['window_days']}d window)")
        return 0

    report = _render_report(findings)
    print(f"::warning::{stats['degraded']} source(s) degraded "
          f"(of {stats['judged']} judged, {stats['window_days']}d window):")
    print(report)
    if args.open_issue:
        body = (
            f"Automated detection from `scripts/verify_source_health_floors.py` "
            f"on {today.isoformat()}.\n\n"
            f"{stats['degraded']} established source(s) went silent or stale. "
            f"These were producing rows recently and stopped — likely a broken "
            f"endpoint/credential, not an offseason lull.\n\n"
            f"{report}\n\n"
            f"**What to check:** run `python manage.py scrape-health --since-days 14` "
            f"for the full table, then probe the affected adapter "
            f"(`python tools/run_adapter.py <source_id>`). If a source is "
            f"legitimately intermittent now, add it to "
            f"`seeds/source_health_floors.yaml` to silence this."
        )
        _open_or_reuse_issue(today.isoformat(), body)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
