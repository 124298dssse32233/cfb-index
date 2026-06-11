"""Critical post-collect volume sanity check.

Compares ``conversation_documents`` inserted in the last 24h against the trailing
7-day median. Exits 1 (CRITICAL) when today is a >75% collapse vs that median --
the signal that a collector died wholesale (e.g. on 2026-06-11 an import-shadowing
bug in cli.py killed every Reddit/board/lexicon subcommand at once, dropping the
day from ~31,900 docs to ~2,800).

Why this exists, given the per-source health floor already runs:
  * The per-source floor (verify_source_health_floors.py) judges on a 21-DAY
    window, so a single catastrophic day never dents the baseline -- it reported
    "0 degraded" on the day everything broke.
  * collect.ps1 steps are non-Critical by design ("a quiet source must not fail
    the whole collect"), so 7 dead subcommands still left FailedSteps empty and
    the pipeline pinged SUCCESS.
  * The publish gate flags the same drop but only as a WARN, and deploys anyway.
This check is the one place a single-day wholesale collapse becomes a hard fail
(fail-ping + non-zero exit) so the nightly actually alerts.

Pure stdlib + sqlite3 ON PURPOSE: it must keep working even if cli.py's main()
entrypoint is broken, since "main() is broken" is exactly the failure mode it
exists to catch. Do NOT route this through manage.py.

Usage:
    python scripts/verify_collect_volume.py [path-to-db]
Exit codes:
    0  OK (today within tolerance) or SKIP (no db / thin baseline)
    1  FAIL (today is a >75% drop vs 7d median)
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Today must be at least this fraction of the trailing 7-day median.
# 0.25 == "a >75% drop is a hard fail" -- matches the publish gate's WARN
# boundary (cli.py verify-publish-readiness, section C) so the two agree.
DROP_FLOOR = 0.25
# Need at least this many non-empty baseline days, else SKIP (fresh-DB starts /
# brand-new boxes must not false-fail before a baseline exists).
MIN_BASELINE_DAYS = 3


def _resolve_db_path() -> Path:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return Path(sys.argv[1]).expanduser()
    return Path(__file__).resolve().parents[1] / "cfb_rankings.db"


def check(db_path: Path) -> int:
    if not db_path.exists():
        print(f"verify-collect-volume: SKIP (no db at {db_path})")
        return 0

    con = sqlite3.connect(str(db_path))
    try:
        today = con.execute(
            "SELECT COUNT(*) FROM conversation_documents "
            "WHERE collected_at_utc >= datetime('now','-1 day')"
        ).fetchone()[0]
        per_day = con.execute(
            "SELECT substr(collected_at_utc,1,10) AS d, COUNT(*) AS n "
            "FROM conversation_documents "
            "WHERE collected_at_utc >= datetime('now','-8 day') "
            "  AND collected_at_utc <  datetime('now','-1 day') "
            "GROUP BY d"
        ).fetchall()
    finally:
        con.close()

    baseline = sorted(int(n) for _d, n in per_day if int(n or 0) > 0)
    if len(baseline) < MIN_BASELINE_DAYS:
        print(f"verify-collect-volume: SKIP (only {len(baseline)} baseline day(s); "
              f"need {MIN_BASELINE_DAYS})")
        return 0

    mid = len(baseline) // 2
    median = (baseline[mid] if len(baseline) % 2
              else (baseline[mid - 1] + baseline[mid]) / 2)
    floor = DROP_FLOOR * median

    if median > 0 and today < floor:
        print(f"verify-collect-volume: FAIL -- today={today:,} docs vs "
              f"7d-median={median:,.0f} (below {DROP_FLOOR:.0%} floor of {floor:,.0f}). "
              f"A collector likely died silently -- check today's collect log for "
              f"tracebacks before trusting the build.")
        return 1

    pct = (today / median * 100) if median else 0.0
    print(f"verify-collect-volume: OK -- today={today:,} docs vs "
          f"7d-median={median:,.0f} ({pct:.0f}% of median).")
    return 0


if __name__ == "__main__":
    sys.exit(check(_resolve_db_path()))
