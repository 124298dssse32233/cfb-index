"""Data Health Spine orchestrator (Wave 0 scaffold).

Opens the canonical ``cfb_rankings.db`` READ-ONLY, runs the registered health
pillars, computes the overall gate, and renders JSON or a console report.

Stdlib + raw sqlite3 only; never mutates the DB. Mirrors the open/flag style of
``scripts/verify_data_floors.py`` (read-only URI, busy_timeout) and is also
importable so ``manage.py data-health`` can call ``run(...)`` directly.

Usage:
    python scripts/verify_data_health.py [db_path] [--json] [--strict] [--season N]
                                         [--snapshot] [--open-issue] [--dry-run]
Exit codes:
    0 = gate GREEN / YELLOW (or any non-RED, unless --strict raises on UNKNOWN too)
    1 = gate RED (with --strict)
    2 = DB missing / unreadable

Active-guard flags (computed AFTER the gate; the DATA read stays ?mode=ro):
    --snapshot     persist this run to the additive data_health_* tables (a
                   SEPARATE read-write connection writes only those tables).
    --open-issue   open one deduped GitHub issue per regression CLASS via `gh`.
    --dry-run      with --open-issue, PRINT what would be opened; create nothing.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# Allow running both as a script (python scripts/verify_data_health.py) and as an
# import target (manage.py data-health) without a package install: ensure ``src``
# is importable.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_DEFAULT_DB = str(_REPO_ROOT / "cfb_rankings.db")

from cfb_rankings.data_health import checks as health_checks      # noqa: E402
from cfb_rankings.data_health import gate as health_gate          # noqa: E402
from cfb_rankings.data_health import report as health_report      # noqa: E402
from cfb_rankings.data_health import report_html as health_report_html  # noqa: E402
from cfb_rankings.data_health import snapshots as health_snapshots  # noqa: E402
from cfb_rankings.data_health import alerting as health_alerting    # noqa: E402

# Default internal dashboard path (gitignored; an OPERATOR view, never deployed —
# must not land under output/site).
_DEFAULT_HTML = str(_REPO_ROOT / "data_health_report.html")


def _open_ro(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(
        f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=10
    )
    conn.execute("PRAGMA busy_timeout=8000")
    return conn


def run(db_path: str | Path = _DEFAULT_DB, season: int | None = None) -> dict:
    """Run the health checks against ``db_path`` and return the JSON report dict.

    Raises FileNotFoundError if the DB is absent; sqlite3.Error on open failure.
    ``season`` is accepted for forward-compat scoping; with zero pillars it has no
    effect yet (the scaffold returns an empty/UNKNOWN report).
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    conn = _open_ro(db_path)
    try:
        results = health_checks.run_all(conn)
    finally:
        conn.close()

    if season is not None:
        results = [r for r in results if r.season in (None, season)]

    gate = health_gate.compute_gate(results)
    return health_report.to_json(gate, results), gate, results


def main(argv: "list[str] | None" = None) -> int:
    p = argparse.ArgumentParser(
        description="Data Health Spine: gate the factual + offseason data layer."
    )
    p.add_argument("db_path", nargs="?", default=_DEFAULT_DB)
    p.add_argument("--json", action="store_true", help="emit the JSON report")
    p.add_argument(
        "--strict", action="store_true",
        help="exit 1 when the overall gate is RED (publish-blocking mode).",
    )
    p.add_argument(
        "--season", type=int, default=None,
        help="scope the report to a single season (forward-compat).",
    )
    p.add_argument(
        "--html", nargs="?", const=_DEFAULT_HTML, default=None, metavar="PATH",
        help="write a self-contained INTERNAL HTML dashboard to PATH "
             f"(default {Path(_DEFAULT_HTML).name}, gitignored). "
             "Read-only side effect: never writes under output/site, never the DB.",
    )
    p.add_argument(
        "--snapshot", action="store_true",
        help="persist this run to the additive data_health_* tables "
             "(separate read-write connection; writes only those tables).",
    )
    p.add_argument(
        "--open-issue", action="store_true",
        help="open one deduped GitHub issue per regression class via gh.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="with --open-issue, print what would be opened; create nothing.",
    )
    args = p.parse_args(argv)

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"::error::DB not found: {db_path}")
        return 2
    try:
        report_json, gate, results = run(db_path, season=args.season)
    except sqlite3.Error as exc:
        print(f"::error::cannot open DB read-only: {exc}")
        return 2

    if args.json:
        print(json.dumps(report_json, indent=2, default=str))
    else:
        print(health_report.render_console(gate, results))

    # --- internal HTML dashboard (read-only side effect; never under output/site) ---
    if args.html is not None:
        html_path = Path(args.html)
        if "output/site" in html_path.resolve().as_posix():
            # Guard: this is an operator view, NOT a deployed site page.
            print(f"::error::refusing to write data-health HTML under a site path: {html_path}")
            return 2
        try:
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(
                health_report_html.render_html(gate, results), encoding="utf-8"
            )
            print(f"   data-health HTML dashboard written: {html_path}")
        except OSError as exc:
            print(f"::warning::could not write data-health HTML dashboard: {exc}")

    # --- active-guard layer: persist + alert AFTER the gate (read stayed ?mode=ro) ---
    if args.snapshot:
        try:
            snapshot_id = health_snapshots.persist(db_path, gate, results)
            print(f"   data-health snapshot persisted: snapshot_id={snapshot_id}")
        except sqlite3.Error as exc:
            # A missing data_health_* table means the migration hasn't run — surface
            # it loudly, but never let persistence failure mask the gate result.
            print(f"::warning::could not persist data-health snapshot: {exc}")

    if args.open_issue:
        try:
            payloads = health_alerting.build_issue_payloads(gate, results)
            health_alerting.open_issues(payloads, dry_run=args.dry_run)
        except Exception as exc:  # noqa: BLE001 — alerting must never crash the checker
            print(f"::warning::data-health alerting errored: {exc}")

    if args.strict and gate.get("overall") == "RED":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
