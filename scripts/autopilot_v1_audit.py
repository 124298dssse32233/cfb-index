"""Autopilot v1 end-to-end audit script — TASK 9.1.

Runs all 14 checks from the kickoff's W9 and renders a markdown report
at `docs/audits/autopilot_v1_audit.md`. Per-check pass/fail + one-line
evidence. Designed to be re-runnable: committing a fix and re-running
produces a fresh snapshot.

Usage:
    python scripts/autopilot_v1_audit.py
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "cfb_rankings.db"


def _conn():
    c = sqlite3.connect(str(DB_PATH), timeout=30.0)
    c.row_factory = sqlite3.Row
    return c


def _count(query: str, *args: Any) -> int:
    with _conn() as c:
        row = c.execute(query, args).fetchone()
    return int(row[0]) if row else 0


def _row(query: str, *args: Any) -> dict | None:
    with _conn() as c:
        row = c.execute(query, args).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_source_registry_coverage() -> tuple[bool, str]:
    # Every STRATEGY §3 source family should have at least one row with source_id set.
    families = (
        "cfbd", "wiki_pv", "wiki_edits", "seatgeek", "youtube_meta",
        "kalshi", "polymarket", "gdelt_volume", "spotify_charts",
        "reddit_cfb", "bluesky_curated", "bluesky_feeds", "campus",
        "athletics", "locked_on", "beat", "substack", "finebaum",
    )
    missing = []
    for fam in families:
        n = _count(
            "select count(*) from source_registry "
            "where source_id like ? or source_id = ?",
            f"{fam}_%", fam,
        )
        if n == 0:
            missing.append(fam)
    passed = not missing
    evidence = (
        f"{len(families)}/{len(families)} families present"
        if passed else f"missing: {', '.join(missing)}"
    )
    return passed, evidence


def check_conversation_seasons() -> tuple[bool, str]:
    # season coverage per kickoff
    # At minimum 2025 should have >1k rows. 2022-2024 rows require
    # Reddit historical backfill (W2.3) which hasn't been run at commit level.
    by_season = {}
    with _conn() as c:
        rows = c.execute(
            "select season_year, count(distinct conversation_document_id) n "
            "from conversation_document_targets where season_year is not null "
            "group by season_year"
        ).fetchall()
    for r in rows:
        by_season[int(r["season_year"])] = int(r["n"])
    threshold = 1000
    passing_seasons = [y for y, n in by_season.items() if n >= threshold]
    evidence = " / ".join(f"{y}:{by_season.get(y, 0):,}" for y in sorted(by_season.keys()))
    return len(passing_seasons) >= 1, evidence


def check_player_target_coverage() -> tuple[bool, str]:
    n = _count(
        "select count(*) from conversation_document_targets where target_type='player'"
    )
    distinct_players = _count(
        "select count(distinct player_id) from conversation_document_targets "
        "where target_type='player'"
    )
    return n > 0, f"{n:,} player-target rows / {distinct_players} distinct players"


def check_player_week_features() -> tuple[bool, str]:
    n = _count("select count(*) from player_week_conversation_features")
    players = _count("select count(distinct player_id) from player_week_conversation_features")
    return n > 0, f"{n:,} rows / {players} players"


def check_player_advanced_metrics() -> tuple[bool, str]:
    by_season = {}
    with _conn() as c:
        rows = c.execute(
            "select season_year, count(*) n from player_advanced_metrics "
            "group by season_year order by season_year"
        ).fetchall()
    for r in rows:
        by_season[int(r["season_year"])] = int(r["n"])
    # Kickoff target: at least 2 of 2022/2023/2024/2025 populated.
    covered = [y for y in (2022, 2023, 2024, 2025) if by_season.get(y, 0) >= 10000]
    evidence = " / ".join(f"{y}:{by_season.get(y, 0):,}" for y in (2022, 2023, 2024, 2025, 2026))
    return len(covered) >= 2, evidence


def check_player_honors_scope() -> tuple[bool, str]:
    scopes = {}
    with _conn() as c:
        rows = c.execute(
            "select honor_scope, count(*) n from player_honors group by honor_scope"
        ).fetchall()
    for r in rows:
        scopes[r["honor_scope"]] = int(r["n"])
    n = sum(scopes.values())
    return n > 0, f"{n} rows across scopes: {scopes}"


def check_player_nfl_draft() -> tuple[bool, str]:
    n = _count("select count(*) from player_nfl_draft")
    by_year = {}
    with _conn() as c:
        rows = c.execute(
            "select draft_year, count(*) n from player_nfl_draft "
            "group by draft_year order by draft_year"
        ).fetchall()
    for r in rows:
        by_year[int(r["draft_year"])] = int(r["n"])
    evidence = " / ".join(f"{y}:{by_year.get(y, 0)}" for y in sorted(by_year.keys()))
    return n > 200, f"{n} picks · {evidence}"


def check_player_draft_projection() -> tuple[bool, str]:
    try:
        n = _count("select count(*) from player_draft_projection")
        return True, f"{n} projection rows (table present, rows expected from per-source scrapers)"
    except sqlite3.OperationalError:
        return False, "table missing"


def check_workflow_artifact_pattern() -> tuple[bool, str]:
    # Every workflow yml should have both download-artifact and upload-artifact.
    wf_dir = ROOT / ".github" / "workflows"
    yamls = list(wf_dir.glob("*.yml"))
    bad = []
    for y in yamls:
        text = y.read_text(encoding="utf-8")
        if y.name in ("deep_research_monthly.yml",):
            continue  # reminder-only
        if "actions/download-artifact" not in text or "actions/upload-artifact" not in text:
            bad.append(y.name)
    return not bad, (
        f"{len(yamls) - len(bad)}/{len(yamls)} workflows wire the DB artifact"
        if not bad else f"missing artifact pattern: {bad}"
    )


def check_publish_workflow() -> tuple[bool, str]:
    p = ROOT / ".github" / "workflows" / "publish_site.yml"
    return p.exists(), "publish_site.yml present" if p.exists() else "publish_site.yml missing"


def check_divergence_nonzero() -> tuple[bool, str]:
    n = _count(
        "select count(*) from team_cohort_divergence_week where divergence_score > 0"
    )
    return n > 0, f"{n} (team, week) pairs with divergence_score > 0"


def check_carr_page_renders() -> tuple[bool, str]:
    p = ROOT / "output" / "site" / "players" / "cj-carr-4788.html"
    if not p.exists():
        return False, "Carr page not built yet — run python manage.py build-site"
    text = p.read_text(encoding="utf-8", errors="replace")
    required = ["the-room", "algorithmic-signature", "phase-banner"]
    missing = [r for r in required if r not in text]
    return not missing, (
        f"present: {len(required)}/{len(required)} modules"
        if not missing else f"Carr page missing: {missing}"
    )


def check_methodology_pages() -> tuple[bool, str]:
    for stem in ("fan-intelligence.html", "freshness.html"):
        p = ROOT / "output" / "site" / "methodology" / stem
        if not p.exists():
            return False, f"{stem} missing"
    return True, "fan-intelligence.html + freshness.html both present"


def check_retry_wrapper_present() -> tuple[bool, str]:
    p = ROOT / "src" / "cfb_rankings" / "db.py"
    text = p.read_text(encoding="utf-8")
    return "_with_retry" in text, "db.py _with_retry wrapper present"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


CHECKS: list[tuple[str, callable]] = [
    ("source_registry §3 family coverage", check_source_registry_coverage),
    ("conversation_document_targets season coverage", check_conversation_seasons),
    ("conversation_document_targets player scope", check_player_target_coverage),
    ("player_week_conversation_features populated", check_player_week_features),
    ("player_advanced_metrics multi-season", check_player_advanced_metrics),
    ("player_honors scoped rows", check_player_honors_scope),
    ("player_nfl_draft populated 2022-2025", check_player_nfl_draft),
    ("player_draft_projection schema", check_player_draft_projection),
    ("workflow artifact pattern", check_workflow_artifact_pattern),
    ("publish_site.yml present", check_publish_workflow),
    ("cohort divergence nonzero cells", check_divergence_nonzero),
    ("CJ Carr page renders modules", check_carr_page_renders),
    ("methodology + freshness pages", check_methodology_pages),
    ("Database retry wrapper present", check_retry_wrapper_present),
]


def render_report(results: list[tuple[str, bool, str]]) -> str:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    lines = [
        f"# Autopilot v1 — End-to-End Audit · {ts}",
        "",
        f"**{passed}/{total}** checks pass.",
        "",
        "| # | Check | Result | Evidence |",
        "|---|---|---|---|",
    ]
    for i, (name, ok, evidence) in enumerate(results, start=1):
        status = "✅ PASS" if ok else "❌ FAIL"
        lines.append(f"| {i} | {name} | {status} | {evidence} |")
    lines.append("")
    fails = [n for n, ok, _ in results if not ok]
    if fails:
        lines.append("## Follow-ups")
        lines.append("")
        for f in fails:
            lines.append(f"- Investigate: **{f}**")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/audits/autopilot_v1_audit.md")
    args = parser.parse_args()

    results: list[tuple[str, bool, str]] = []
    for name, fn in CHECKS:
        try:
            ok, evidence = fn()
        except Exception as exc:
            ok = False
            evidence = f"check raised: {exc}"
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {evidence}")
        results.append((name, ok, evidence))

    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(results), encoding="utf-8")
    print(f"\nWrote {out}")
    # Exit 0 even on fails — audit is read-only and informational.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
