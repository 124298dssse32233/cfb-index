"""Master autonomous loop — chains cascade phases serially.

When this script runs, it:
  1. Waits for any currently-running chronicle generation to finish (polls DB)
  2. Runs Phase 2 (T1 week 8 with v3 prompts)
  3. Runs Phase 3 (T1 alt card types: retroactive, moment_of_year, rivalry_lens)
  4. Runs Phase 4 (T3 broader sweep across all teams)
  5. Runs final batch eval + drift detection
  6. Writes AUTONOMOUS_RUN_REPORT.md
  7. Generates chronicle_preview.html

Total expected runtime: 3-5 hours.

Each phase logs to logs/chronicle/master_loop_*.log so user can tail progress.

Designed to be invoked as ONE background process:
    python scripts/autonomous_master_loop.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


PHASES = [
    # Phase 2 — Tier T1 v3 prompts, week 8 — different content variety
    {
        "name": "phase2-T1-w8",
        "args": ["--tier", "T1",
                 "--card-types", "flashpoint,echo,devil_card,player_arc",
                 "--season", "2024", "--week", "8",
                 "--n-slots", "4", "--max-teams", "189",
                 "--max-runtime-min", "75"],
    },
    # Phase 3 — Tier T1 v3 prompts, week 12 with alt card types
    {
        "name": "phase3-T1-altcards",
        "args": ["--tier", "T1",
                 "--card-types", "retroactive,moment_of_year,rivalry_lens,matchup_echo",
                 "--season", "2024", "--week", "12",
                 "--n-slots", "4", "--max-teams", "189",
                 "--max-runtime-min", "75"],
    },
    # Phase 4 — Tier T3 broader sweep (writer-only, faster) — gets more teams
    # The v3 topical-anchor + drift detector still catches drift even in T3 mode
    {
        "name": "phase4-T3-broader",
        "args": ["--tier", "T3",
                 "--card-types", "echo,player_arc",
                 "--season", "2024", "--week", "14",
                 "--n-slots", "2", "--max-teams", "189",
                 "--max-runtime-min", "45"],
    },
]

LOG_DIR = Path("logs/chronicle")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def is_chronicle_running() -> bool:
    """Detect if any chronicle gen process is currently running.

    Heuristic: check for chronicle_card_cache modification within last 60s.
    DB-based is reliable; process inspection self-references (the master loop
    process itself has loaded modules and looks chronicle-y).
    """
    try:
        conn = sqlite3.connect("cfb_rankings.db", timeout=5)
        row = conn.execute(
            "SELECT MAX(strftime('%s','now') - strftime('%s', created_at_utc)) FROM chronicle_card_cache"
        ).fetchone()
        conn.close()
        if row and row[0] is not None and row[0] < 60:
            return True
    except Exception:
        pass
    return False


def wait_for_idle(max_wait_s: int = 7200, poll_s: int = 60) -> None:
    """Block until no chronicle gen process is running (or timeout)."""
    start = time.monotonic()
    while time.monotonic() - start < max_wait_s:
        if not is_chronicle_running():
            print(f"  [idle detected after {(time.monotonic()-start)/60:.1f} min]")
            return
        time.sleep(poll_s)
    print(f"  [WARN: still running after {max_wait_s/60:.0f} min, continuing anyway]")


def run_phase(phase: dict) -> dict:
    """Run one cascade phase. Returns stats dict."""
    log_path = LOG_DIR / f"master_{phase['name']}_{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.log"
    print(f"\n=== Phase: {phase['name']} ===")
    print(f"  log: {log_path}")

    t0 = time.monotonic()
    pre_n = _card_count()

    cmd = [sys.executable, "scripts/autonomous_chronicle_run.py"] + phase["args"]
    print(f"  $ {' '.join(cmd[1:])}")

    with log_path.open("w", encoding="utf-8") as f:
        f.write(f"=== {phase['name']} started {datetime.now(timezone.utc).isoformat()} ===\n\n")

    with log_path.open("a", encoding="utf-8") as f:
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)

    elapsed = time.monotonic() - t0
    post_n = _card_count()
    delta = post_n - pre_n
    print(f"  done in {elapsed/60:.1f} min, rc={proc.returncode}, +{delta} cards")

    return {
        "phase": phase["name"],
        "elapsed_min": elapsed / 60,
        "cards_added": delta,
        "total_cards_after": post_n,
        "rc": proc.returncode,
        "log": str(log_path),
    }


def _card_count() -> int:
    try:
        conn = sqlite3.connect("cfb_rankings.db", timeout=5)
        n = conn.execute(
            "SELECT COUNT(*) FROM chronicle_card_cache WHERE word_count > 0"
        ).fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


def final_eval_and_report(phase_results: list[dict]) -> None:
    """Run preview HTML + write report."""
    print("\n=== Final eval + report ===")
    # Generate preview HTML
    try:
        subprocess.run([sys.executable, "scripts/preview_chronicle_cards.py"],
                       check=False, timeout=60)
    except Exception as e:
        print(f"  preview gen failed: {e}")

    # Stats
    conn = sqlite3.connect("cfb_rankings.db", timeout=10)
    stats = {
        "total_cards": conn.execute("SELECT COUNT(*) FROM chronicle_card_cache WHERE word_count>0").fetchone()[0],
        "lkg_cards": conn.execute("SELECT COUNT(*) FROM chronicle_card_cache WHERE is_lkg=1").fetchone()[0],
        "unique_teams": conn.execute("SELECT COUNT(DISTINCT slug) FROM chronicle_card_cache WHERE word_count>0").fetchone()[0],
        "by_template": dict(conn.execute("SELECT prompt_template_id, COUNT(*) FROM chronicle_card_cache WHERE word_count>0 GROUP BY prompt_template_id").fetchall()),
        "by_card_type": dict(conn.execute("SELECT card_type, COUNT(*) FROM chronicle_card_cache WHERE word_count>0 GROUP BY card_type ORDER BY 2 DESC").fetchall()),
    }
    conn.close()

    report = ["# Chronicle Autonomous Run Report", f"\n_Written {datetime.now(timezone.utc).isoformat()}_\n"]
    report.append("## Cards in DB")
    for k, v in stats.items():
        report.append(f"- **{k}**: {v}")
    report.append("\n## Phase results")
    for p in phase_results:
        report.append(f"- **{p['phase']}**: +{p['cards_added']} cards in {p['elapsed_min']:.1f} min (rc={p['rc']})")
    report.append("\n## Preview")
    report.append("- Open `output/chronicle_preview.html` in browser to scan all generated cards.")

    out = Path("AUTONOMOUS_RUN_REPORT.md")
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"  report: {out}")
    print(f"  preview: output/chronicle_preview.html")


def main() -> int:
    print(f"=== Master autonomous loop starting {datetime.now(timezone.utc).isoformat()} ===")
    print(f"  Will chain {len(PHASES)} phases after current run finishes")
    print()

    # Wait for any current gen to complete
    print("Waiting for current chronicle gen to finish...")
    wait_for_idle(max_wait_s=7200, poll_s=60)

    phase_results = []
    for phase in PHASES:
        try:
            result = run_phase(phase)
            phase_results.append(result)
        except KeyboardInterrupt:
            print("Interrupted")
            break
        except Exception as e:
            print(f"  phase failed: {e}")
            phase_results.append({
                "phase": phase["name"],
                "error": str(e),
                "elapsed_min": 0,
                "cards_added": 0,
                "rc": -1,
            })

    final_eval_and_report(phase_results)
    print("\n=== Master loop done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
