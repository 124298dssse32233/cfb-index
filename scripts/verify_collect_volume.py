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
# Window of trailing days to look back over (wider than the original 8d so a real
# baseline accrues despite an irregular offseason cadence).
WINDOW_DAYS = 14
# Need at least this many non-empty days before attempting any judgement.
MIN_BASELINE_DAYS = 3
# After removing outliers, need at least this many "normal-range" days, else the
# baseline is too noisy to trust -> SKIP (don't cry wolf).
MIN_NORMAL_DAYS = 3
# Outlier bounds, as multiples of the rough median of active days:
#   > BACKFILL_MULT x  -> a one-time backfill (e.g. a 150k-doc archive import),
#                         which must NOT inflate "normal daily volume".
#   < DEAD_FRAC x      -> a partial-failure day (pipeline barely ran), which must
#                         NOT drag the baseline down either.
BACKFILL_MULT = 3.0
DEAD_FRAC = 0.20


def _median(xs: "list[float]") -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def assess(today: int, daily_counts: "list[int]") -> "tuple[str, str]":
    """Pure decision logic (no DB) so it is unit-testable.

    Returns (verdict, message) where verdict is 'OK', 'FAIL', or 'SKIP'.
    A FAIL means today is a >75% collapse vs the robust typical day. SKIP means
    there isn't yet a stable enough baseline to judge (the honest answer during a
    ramp-up where one-time backfills and partial days dominate the history).
    """
    positives = sorted(n for n in daily_counts if n > 0)
    if len(positives) < MIN_BASELINE_DAYS:
        return "SKIP", f"only {len(positives)} active baseline day(s); need {MIN_BASELINE_DAYS}"

    rough = _median(positives)
    lo, hi = DEAD_FRAC * rough, BACKFILL_MULT * rough
    normal = [n for n in positives if lo <= n <= hi]
    dropped = len(positives) - len(normal)
    if len(normal) < MIN_NORMAL_DAYS:
        return "SKIP", (
            f"baseline too noisy to judge -- {len(positives)} active day(s), but only "
            f"{len(normal)} in the normal range after dropping {dropped} backfill/partial "
            f"outlier(s). A stable baseline will form as the pipeline runs cleanly daily.")

    typical = _median(normal)
    floor = DROP_FLOOR * typical
    if today < floor:
        return "FAIL", (
            f"today={today:,} docs vs typical={typical:,.0f}/day (below {DROP_FLOOR:.0%} floor "
            f"of {floor:,.0f}). A collector likely died silently -- check today's collect log "
            f"for tracebacks before trusting the build.")
    pct = (today / typical * 100) if typical else 0.0
    return "OK", f"today={today:,} docs vs typical={typical:,.0f}/day ({pct:.0f}% of typical)."


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
            "WHERE collected_at_utc >= datetime('now', ?) "
            "  AND collected_at_utc <  datetime('now','-1 day') "
            "GROUP BY d",
            (f"-{WINDOW_DAYS} day",),
        ).fetchall()
    finally:
        con.close()

    verdict, msg = assess(int(today), [int(n) for _d, n in per_day])
    print(f"verify-collect-volume: {verdict} -- {msg}")
    return 1 if verdict == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(check(_resolve_db_path()))
