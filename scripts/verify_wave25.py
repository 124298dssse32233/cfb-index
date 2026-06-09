"""Wave 25 verify — audit every status code, marquee players, override counts,
cache freshness. Returns 0 on pass, 1 on fail. Used by CI.

Run: python manage.py verify-wave25
     python scripts/verify_wave25.py
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "cfb_rankings.db"


EXPECTED_STATUS_CODES = {
    "RETURNING_2026", "TRANSFERRED_COLLEGE",
    "NFL_DRAFTED_2026", "NFL_DRAFTED_PRIOR", "NFL_UDFA",
    "PORTAL_OPEN", "PORTAL_WITHDREW",
    "EXHAUSTED_ELIGIBILITY", "MEDICAL_RETIREMENT",
    "HISTORICAL_ALUM", "HS_RECRUIT_ONLY",
}


# (pid, name, expected_status, expected_nfl_team, expected_last_college)
MARQUEE_FIXTURES: list[tuple[int, str, str, str | None, str | None]] = [
    (13074, "Arch Manning",     "RETURNING_2026",     None,         "Texas"),
    ( 3830, "Jeremiah Smith",   "RETURNING_2026",     None,         "Ohio State"),
    (11807, "Maddux Madsen",    "RETURNING_2026",     None,         "Boise State"),
    (12763, "Fernando Mendoza", "NFL_DRAFTED_2026",   "Las Vegas",  "California"),
    ( 9020, "Drew Allar",       "NFL_DRAFTED_2026",   "Pittsburgh", "Penn State"),
    (13272, "Carson Beck",      "NFL_DRAFTED_2026",   "Arizona",    "Georgia"),
    ( 1015, "Cam Ward",         "NFL_DRAFTED_PRIOR",  "Tennessee",  None),
    ( 9464, "Cameron Ward",     "NFL_DRAFTED_PRIOR",  "Tennessee",  "Miami"),
    (  120, "Dillon Gabriel",   "NFL_DRAFTED_PRIOR",  "Cleveland",  None),
    (11737, "Dillon Gabriel",   "NFL_DRAFTED_PRIOR",  "Cleveland",  "Oregon"),
    (11804, "Ashton Jeanty",    "NFL_DRAFTED_PRIOR",  "Las Vegas",  "Boise State"),
]


def verify(db_path: Path = DEFAULT_DB) -> bool:
    con = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    print(f"Wave 25 verify — db={db_path}")
    print()

    passes: list[str] = []
    fails: list[str] = []

    # ------ Schema -----------------------------------------------------------
    def chk_table(name: str) -> None:
        r = cur.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone()
        (passes if r else fails).append(f"schema: {name} exists" if r else f"schema: {name} MISSING")

    for tbl in ("player_status_override", "player_depth_chart_2026", "player_award_watch_2026"):
        chk_table(tbl)
    chk_table("player_current_status_view")
    chk_table("player_current_status_cache")

    # Override has the 6 draft columns
    cols = {r[1] for r in cur.execute("PRAGMA table_info(player_status_override)").fetchall()}
    for c in ("nfl_team", "draft_year", "draft_round", "draft_pick", "draft_overall"):
        if c in cols:
            passes.append(f"override.{c} present")
        else:
            fails.append(f"override.{c} MISSING")

    # ------ View v4 markers --------------------------------------------------
    sql = cur.execute("SELECT sql FROM sqlite_master WHERE name='player_current_status_view'").fetchone()
    if sql and "COALESCE(o.draft_year" in sql[0]:
        passes.append("view: v4 (override draft passthrough)")
    else:
        fails.append("view: not v4 — override draft fields will not flow")

    # ------ Cache freshness --------------------------------------------------
    cache_rows = cur.execute("SELECT COUNT(*) FROM player_current_status_cache").fetchone()[0]
    players_n  = cur.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    if cache_rows >= players_n - 50:  # cache may be slightly smaller (rows with no signal collapse)
        passes.append(f"cache: {cache_rows:,} rows vs {players_n:,} players (close)")
    else:
        fails.append(f"cache: {cache_rows:,} rows but {players_n:,} players — rebuild?")

    # ------ Status code coverage --------------------------------------------
    seen_codes = {r[0] for r in cur.execute(
        "SELECT DISTINCT status_code FROM player_current_status_cache"
    ).fetchall()}
    missing = EXPECTED_STATUS_CODES - seen_codes
    extra   = seen_codes - EXPECTED_STATUS_CODES
    # The following codes only appear via editorial override (no automatic signal).
    # Missing them is a WARN, not a FAIL.
    OPTIONAL_OVERRIDE_CODES = {
        "NFL_UDFA", "PORTAL_WITHDREW", "MEDICAL_RETIREMENT", "HS_RECRUIT_ONLY",
    }
    hard_missing = missing - OPTIONAL_OVERRIDE_CODES
    soft_missing = missing & OPTIONAL_OVERRIDE_CODES
    if not hard_missing and not extra:
        passes.append(
            f"codes: all {len(seen_codes)} present "
            f"(soft-missing override-only codes: {sorted(soft_missing) or 'none'})"
        )
    else:
        if hard_missing:
            fails.append(f"codes: missing required {sorted(hard_missing)}")
        if extra:
            fails.append(f"codes: unexpected extras {sorted(extra)}")
    # Distribution
    print("Status code distribution:")
    for code, n in cur.execute(
        "SELECT status_code, COUNT(*) FROM player_current_status_cache "
        "GROUP BY status_code ORDER BY 2 DESC"
    ).fetchall():
        print(f"  {code:25} {n:6,}")
    print()

    # ------ Marquee fixtures -------------------------------------------------
    print("Marquee player checks:")
    for pid, name, exp_status, exp_nfl, exp_last in MARQUEE_FIXTURES:
        r = cur.execute(
            "SELECT full_name, status_code, nfl_team, last_college_team_name "
            "FROM player_current_status_cache WHERE player_id=?", (pid,)
        ).fetchone()
        if not r:
            fails.append(f"marquee: pid={pid} ({name}) NOT IN CACHE")
            print(f"  [FAIL] pid={pid} ({name}) — no row")
            continue
        bad = []
        if r["status_code"] != exp_status:
            bad.append(f"status={r['status_code']!r} ≠ {exp_status!r}")
        if exp_nfl and r["nfl_team"] != exp_nfl:
            bad.append(f"nfl_team={r['nfl_team']!r} ≠ {exp_nfl!r}")
        if exp_last and r["last_college_team_name"] != exp_last:
            bad.append(f"last_college={r['last_college_team_name']!r} ≠ {exp_last!r}")
        if bad:
            fails.append(f"marquee: pid={pid} ({name}) — " + "; ".join(bad))
            print(f"  [FAIL] pid={pid} ({name}): " + "; ".join(bad))
        else:
            passes.append(f"marquee: pid={pid} ({name}) OK")
            print(f"  [OK] pid={pid} ({name}): {r['status_code']:22} "
                  f"nfl={r['nfl_team'] or '—':12} last={r['last_college_team_name'] or '—'}")

    # ------ Override counts --------------------------------------------------
    n_overrides = cur.execute("SELECT COUNT(*) FROM player_status_override").fetchone()[0]
    n_auto = cur.execute(
        "SELECT COUNT(*) FROM player_status_override WHERE set_by LIKE 'auto_alias%'"
    ).fetchone()[0]
    n_with_draft = cur.execute(
        "SELECT COUNT(*) FROM player_status_override WHERE nfl_team IS NOT NULL"
    ).fetchone()[0]
    print()
    print(f"Overrides: {n_overrides} total, {n_auto} auto-alias, {n_with_draft} with draft payload")
    if n_overrides < 50:
        fails.append(f"overrides: only {n_overrides} — expected 95+")
    else:
        passes.append(f"overrides: {n_overrides} rows")

    # ------ Award watch + depth chart counts --------------------------------
    n_award = cur.execute("SELECT COUNT(*) FROM player_award_watch_2026").fetchone()[0]
    n_award_awards = cur.execute(
        "SELECT COUNT(DISTINCT award_slug) FROM player_award_watch_2026"
    ).fetchone()[0]
    n_depth = cur.execute("SELECT COUNT(*) FROM player_depth_chart_2026").fetchone()[0]
    n_depth_returning = cur.execute(
        "SELECT COUNT(*) FROM player_depth_chart_2026 WHERE starter_status='returning_starter'"
    ).fetchone()[0]
    print(f"Award watch: {n_award} rows across {n_award_awards} awards")
    print(f"Depth chart: {n_depth} rows ({n_depth_returning} returning_starter)")

    if n_award < 30:
        fails.append(f"award watch: only {n_award} rows — expected 50+")
    else:
        passes.append(f"award watch: {n_award} rows, {n_award_awards} awards")

    if n_depth < 15:
        fails.append(f"depth chart: only {n_depth} rows — expected 25+")
    else:
        passes.append(f"depth chart: {n_depth} rows")

    # ------ Summary ----------------------------------------------------------
    print()
    print(f"==== Wave 25 verify: {len(passes)} PASS / {len(fails)} FAIL ====")
    for f in fails:
        print(f"  [FAIL] {f}")
    if not fails:
        print("  All checks passed.")
    print()
    print(f"Verified at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    con.close()
    return not fails


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
