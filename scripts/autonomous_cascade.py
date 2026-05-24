"""Cascade runner — chain multiple Chronicle generation passes overnight.

Strategy:
  1. Tier T3 across all FBS teams, season 2024 week 12         (just ran)
  2. Tier T3 across all FBS teams, season 2024 week 8          (different content)
  3. Tier T3 with alternate card types: retroactive, moment_of_year, rivalry_lens
  4. Tier T1 (full 5-agent) for evidence-rich teams only       (highest quality)

Each pass:
  - Uses evidence-floor gate to skip empty-data teams quickly
  - Persists everything to chronicle_card_cache
  - Promotes shipping cards to LKG
  - Logs to logs/chronicle/cascade_<phase>.jsonl

Usage:
    python scripts/autonomous_cascade.py [--phase N] [--max-runtime-hr 4]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
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
    # Phase 1 — full 5-agent (Planner+Writer+Critics) on marquee teams w/ rich evidence.
    # FactCritic catches topic-drift better than T3's writer-only pipeline.
    # Cards may take 30-60s each but quality is much higher.
    {
        "name": "T1-week12-marquee-full-5agent",
        "args": ["--tier", "T1", "--card-types", "flashpoint,echo,player_arc,devil_card",
                 "--season", "2024", "--week", "12", "--n-slots", "4", "--max-teams", "189",
                 "--max-runtime-min", "60"],
        "expected_min": 60,
    },
    # Phase 2 — Tier S Best-of-3 on same teams w/ different week. Higher-quality
    # variants. Best-of-N forces 3 candidates, picks lowest-slop_fingerprint.
    {
        "name": "T1-week8-marquee",
        "args": ["--tier", "T1", "--card-types", "flashpoint,echo,player_arc,devil_card",
                 "--season", "2024", "--week", "8", "--n-slots", "4", "--max-teams", "189",
                 "--max-runtime-min", "60"],
        "expected_min": 60,
    },
    # Phase 3 — different card types for the same teams. Variety.
    {
        "name": "T1-week12-altcards",
        "args": ["--tier", "T1", "--card-types", "moment_of_year,retroactive,rivalry_lens,matchup_echo",
                 "--season", "2024", "--week", "12", "--n-slots", "4", "--max-teams", "189",
                 "--max-runtime-min", "60"],
        "expected_min": 60,
    },
    # Phase 4 — wider net for T3 fast pass (covers more teams quickly)
    {
        "name": "T3-week14-broader",
        "args": ["--tier", "T3", "--card-types", "echo,player_arc",
                 "--season", "2024", "--week", "14", "--n-slots", "2", "--max-teams", "189",
                 "--max-runtime-min", "45"],
        "expected_min": 30,
    },
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start-phase", type=int, default=1, help="Phase to start from (1-based)")
    p.add_argument("--max-runtime-hr", type=float, default=4.0)
    p.add_argument("--log-dir", default="logs/chronicle")
    args = p.parse_args()

    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    cascade_log = Path(args.log_dir) / f"cascade_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.jsonl"

    start_time = time.monotonic()
    max_runtime_s = args.max_runtime_hr * 3600

    def log_event(rec: dict) -> None:
        rec["_ts"] = datetime.now(timezone.utc).isoformat()
        with cascade_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"=== Cascade runner starting ===")
    print(f"  max runtime: {args.max_runtime_hr} hr")
    print(f"  phases: {len(PHASES)}")
    print(f"  log: {cascade_log}")
    print()

    for idx, phase in enumerate(PHASES):
        if idx + 1 < args.start_phase:
            print(f"  [{idx+1}/{len(PHASES)}] SKIP {phase['name']}")
            continue

        elapsed_hr = (time.monotonic() - start_time) / 3600
        if elapsed_hr > args.max_runtime_hr:
            print(f"\n!! Cascade budget exhausted ({elapsed_hr:.1f}/{args.max_runtime_hr} hr)")
            log_event({"kind": "cascade_exhausted", "elapsed_hr": elapsed_hr})
            break

        phase_t0 = time.monotonic()
        print(f"\n=== [{idx+1}/{len(PHASES)}] PHASE: {phase['name']} ===")
        log_event({"kind": "phase_start", "phase": phase["name"], "args": phase["args"]})

        # Cap each phase to remaining budget
        remaining_min = (max_runtime_s - (time.monotonic() - start_time)) / 60
        phase_min = min(phase.get("expected_min", 60), remaining_min)
        phase_args = list(phase["args"])
        if "--max-runtime-min" not in phase_args:
            phase_args.extend(["--max-runtime-min", str(int(phase_min))])

        cmd = [sys.executable, "scripts/autonomous_chronicle_run.py"] + phase_args
        print(f"  $ {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=False)
            phase_elapsed = time.monotonic() - phase_t0
            log_event({
                "kind": "phase_done",
                "phase": phase["name"],
                "elapsed_s": phase_elapsed,
                "returncode": result.returncode,
            })
            print(f"  ↳ phase done in {phase_elapsed/60:.1f} min, rc={result.returncode}")
        except KeyboardInterrupt:
            print("Interrupted")
            log_event({"kind": "interrupted", "phase": phase["name"]})
            return 130
        except Exception as e:
            print(f"  ↳ FAILED: {e}")
            log_event({"kind": "phase_failed", "phase": phase["name"], "error": str(e)})

    elapsed_hr = (time.monotonic() - start_time) / 3600
    print(f"\n=== Cascade complete in {elapsed_hr:.2f} hr ===")
    log_event({"kind": "cascade_done", "elapsed_hr": elapsed_hr})
    return 0


if __name__ == "__main__":
    sys.exit(main())
