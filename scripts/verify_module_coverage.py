"""Baseline-aware coverage gate for COMPUTED module tables.

THE GAP THIS FILLS (2026-06-11):
`verify_source_health_floors.py` watches raw SOURCE ingestion (scrape_health).
But every fan-intel module on the site is fed by a DERIVED table that a compute
step populates AFTER ingestion -- discourse keyness, Atlas clusters, Team Eras,
KWIC quotes, Fanbase Voice, the lexicon tracker, weekly mood, AI-narrative cards.
On 2026-06-11 a cli.py bug killed the Atlas + KWIC compute while every source
stayed green: `team_discourse_clusters` and `team_discourse_term_quotes` went to
0 rows, the Atlas chip + KWIC passages silently vanished from every team page,
and NOTHING alerted -- the source-health floor saw healthy feeds, the build
caught every render exception and shipped blank sections, and the publish gate
only WARNed. This check closes that blind spot: it watches the computed tables
the modules actually read.

DESIGN -- baseline-aware, established-only (mirrors verify_source_health_floors):
A module signal is judged ONLY once it has been populated on >= MIN_ACTIVE_BUILDS
recent builds. Then a >75% drop vs its own trailing median (including a fall to
0) is flagged. Brand-new modules that have never populated (Atlas/KWIC today)
are NOT judged -- they can't regress from a baseline they never had -- so this
never false-alarms on a feature that simply hasn't launched yet. The trailing
history lives in a JSON state file; a regressed build is NOT written back, so a
multi-day outage keeps alerting instead of silently normalising to 0.

Pure stdlib + sqlite3, read-only DB connect. Wired NON-critical into
build_publish.ps1 after build-site: on regression it opens one GitHub issue/day
via `gh` (the alert) and exits 1, but must never block the must-publish deploy.

Usage:
    python scripts/verify_module_coverage.py [db_path] [--open-issue]
Exit codes (mirror verify_source_health_floors.py):
    0 = all established modules healthy (or only un-established ones are empty)
    1 = one or more established modules went dark
    2 = DB missing / unreadable (a real failure to surface)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import sqlite3
import statistics
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = str(_REPO_ROOT / "cfb_rankings.db")
_DEFAULT_HISTORY = _REPO_ROOT / "data" / "module_coverage_history.json"
_ISSUE_LABEL = "module-coverage"

# Tuning (daily build cadence).
MIN_ACTIVE_BUILDS = 5   # >= this many >0 recent builds => "established"
DROP_FLOOR = 0.25       # today must be >= 25% of trailing median (>75% drop fails)
MAX_HISTORY = 40        # entries kept per signal

# Each signal: (key, the module/surface it feeds, SQL returning ONE integer).
# "distinct team_id at the latest season" == how many programs that module can
# render for. Season is resolved as MAX present in the table so it auto-adapts
# to the offseason season-key convention without hard-coding a year.
SIGNALS: list[tuple[str, str, str]] = [
    ("keyness_terms", "rankings discourse chips + Lexicon team module",
     "SELECT COUNT(DISTINCT team_id) FROM team_discourse_terms "
     "WHERE season_year=(SELECT MAX(season_year) FROM team_discourse_terms) AND week=0"),
    ("atlas_clusters", "Discourse Atlas chip (team pages)",
     "SELECT COUNT(DISTINCT team_id) FROM team_discourse_clusters "
     "WHERE season_year=(SELECT MAX(season_year) FROM team_discourse_clusters)"),
    ("era_terms", "Team Eras chapter (team pages)",
     "SELECT COUNT(DISTINCT team_id) FROM team_discourse_era_terms "
     "WHERE season_year=(SELECT MAX(season_year) FROM team_discourse_era_terms)"),
    ("kwic_quotes", "KWIC fan-quote passages (team pages)",
     "SELECT COUNT(DISTINCT team_id) FROM team_discourse_term_quotes "
     "WHERE season_year=(SELECT MAX(season_year) FROM team_discourse_term_quotes)"),
    ("voice_profiles", "Fanbase Voice (team pages + leaderboard)",
     "SELECT COUNT(DISTINCT team_id) FROM fanbase_voice_profile "
     "WHERE season_year=(SELECT MAX(season_year) FROM fanbase_voice_profile)"),
    ("lexicon_daily", "Lexicon tracker board",
     "SELECT COUNT(DISTINCT term_group) FROM lexicon_term_daily "
     "WHERE season_year=(SELECT MAX(season_year) FROM lexicon_term_daily)"),
    ("mood_weekly", "rankings mood chips + Fanbase Health",
     "SELECT COUNT(DISTINCT team_id) FROM fanbase_mood_weekly "
     "WHERE week_start_date=(SELECT MAX(week_start_date) FROM fanbase_mood_weekly) "
     "AND mood_score IS NOT NULL AND mood_score<>0"),
    ("chronicle_cards", "AI Narratives (chronicle cards, team pages)",
     "SELECT COUNT(DISTINCT slug) FROM chronicle_card_cache"),
]


def _query_count(conn: sqlite3.Connection, sql: str) -> "int | None":
    """Run a single-int signal query. Returns None on any SQL error (schema
    drift / missing table) -- surfaced as a warning, never crashes the gate."""
    try:
        row = conn.execute(sql).fetchone()
    except sqlite3.Error as exc:
        print(f"::warning::signal query failed ({exc}): {sql.split('FROM',1)[-1][:60].strip()}")
        return None
    if not row or row[0] is None:
        return 0
    return int(row[0])


def _load_history(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"::warning::could not read history {path.name} ({exc}); starting fresh")
        return {}


def _save_history(path: Path, history: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2, sort_keys=True), encoding="utf-8")


def evaluate(conn: sqlite3.Connection, history: dict, today: str) -> tuple[list[dict], dict]:
    """Judge each signal against its trailing history. Mutates `history` with
    today's healthy counts (regressed signals are intentionally NOT recorded so
    the baseline is not poisoned). Returns (findings, stats)."""
    findings: list[dict] = []
    judged = 0
    unestablished = 0

    for key, powers, sql in SIGNALS:
        today_count = _query_count(conn, sql)
        if today_count is None:
            continue  # query errored -- warned already, not judged
        prior = history.get(key, [])
        active = [int(e["count"]) for e in prior if int(e.get("count", 0)) > 0]

        if len(active) < MIN_ACTIVE_BUILDS:
            # Not established yet -- record and move on (no judgement).
            unestablished += 1
            history.setdefault(key, []).append({"date": today, "count": today_count})
            history[key] = history[key][-MAX_HISTORY:]
            continue

        judged += 1
        typical = int(statistics.median(active))
        floor = DROP_FLOOR * typical
        if today_count < floor:
            findings.append({
                "key": key,
                "powers": powers,
                "today": today_count,
                "typical": typical,
                "floor": int(floor),
            })
            # Do NOT record a regressed value -- keep the good baseline so the
            # alert persists every build until the module is repaired.
            continue

        history.setdefault(key, []).append({"date": today, "count": today_count})
        history[key] = history[key][-MAX_HISTORY:]

    stats = {"judged": judged, "unestablished": unestablished, "degraded": len(findings)}
    return findings, stats


def _render_report(findings: list[dict]) -> str:
    lines = []
    for f in findings:
        lines.append(
            f"- **{f['key']}** ({f['powers']}): today={f['today']} vs "
            f"typical={f['typical']} (floor {f['floor']}). The module is dark or "
            f"near-dark across the site."
        )
    return "\n".join(lines)


def _open_or_reuse_issue(title_date: str, body: str) -> None:
    """Open one module-coverage issue/day via gh. No-op (logged) if gh is
    missing/unauthed -- the printed report still surfaces it in the build log."""
    gh = shutil.which("gh")
    if not gh:
        print("::warning::gh not on PATH; skipping issue creation (see report above)")
        return
    title = f"module-coverage: a module went dark ({title_date})"
    try:
        existing = subprocess.run(
            [gh, "issue", "list", "--label", _ISSUE_LABEL, "--state", "open",
             "--search", title_date, "--json", "number", "--limit", "20"],
            capture_output=True, text=True, timeout=60,
        )
        if existing.returncode == 0 and existing.stdout.strip() not in ("", "[]"):
            print(f"   (open {_ISSUE_LABEL} issue for {title_date} already exists; not duplicating)")
            return
        subprocess.run([gh, "label", "create", _ISSUE_LABEL, "--color", "D93F0B",
                        "--description", "A computed module table went dark vs its baseline"],
                       capture_output=True, text=True, timeout=60)
        created = subprocess.run(
            [gh, "issue", "create", "--label", _ISSUE_LABEL, "--title", title, "--body", body],
            capture_output=True, text=True, timeout=60,
        )
        if created.returncode == 0:
            print(f"   opened {_ISSUE_LABEL} issue: {created.stdout.strip()}")
        else:
            print(f"::warning::gh issue create failed: {created.stderr.strip()}")
    except Exception as exc:  # noqa: BLE001 -- alerting must never crash the gate
        print(f"::warning::issue creation errored: {exc}")


def main(argv: "list[str] | None" = None) -> int:
    p = argparse.ArgumentParser(description="Baseline-aware computed-module coverage gate.")
    p.add_argument("db_path", nargs="?", default=_DEFAULT_DB)
    p.add_argument("--history", default=str(_DEFAULT_HISTORY), help="coverage history JSON")
    p.add_argument("--open-issue", action="store_true", help="open a gh issue on regression")
    p.add_argument("--today", default=None, help="override 'today' (YYYY-MM-DD), for testing")
    p.add_argument("--json", action="store_true", help="emit machine-readable findings")
    args = p.parse_args(argv)

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"::error::DB not found: {db_path}")
        return 2

    today = args.today or _dt.date.today().isoformat()
    history_path = Path(args.history)
    history = _load_history(history_path)

    try:
        uri = f"file:{db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10)
        conn.execute("PRAGMA busy_timeout=8000")
    except sqlite3.Error as exc:
        print(f"::error::cannot open DB read-only: {exc}")
        return 2

    try:
        findings, stats = evaluate(conn, history, today)
    finally:
        conn.close()

    _save_history(history_path, history)

    if args.json:
        print(json.dumps({"stats": stats, "findings": findings}, indent=2))

    if not findings:
        print(f"module coverage OK: judged {stats['judged']} established module(s), "
              f"{stats['unestablished']} not-yet-established skipped, 0 dark.")
        return 0

    report = _render_report(findings)
    print(f"::warning::{stats['degraded']} module(s) went dark "
          f"(of {stats['judged']} judged):")
    print(report)
    if args.open_issue:
        body = (
            f"Automated detection from `scripts/verify_module_coverage.py` on {today}.\n\n"
            f"{stats['degraded']} computed module table(s) that were populated on recent "
            f"builds dropped >75% (or to zero) today. The module(s) are silently blank "
            f"across the site -- a compute step likely failed while sources stayed green.\n\n"
            f"{report}\n\n"
            f"**What to check:** look at today's `logs/fanintel_build_publish_*.log` for a "
            f"traceback in the matching discourse/compute step, re-run that "
            f"`manage.py compute-*` command, then rebuild. If a module was intentionally "
            f"retired, remove its entry from SIGNALS in this script."
        )
        _open_or_reuse_issue(today, body)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
