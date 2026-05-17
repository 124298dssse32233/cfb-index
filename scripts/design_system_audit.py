"""design_system_audit.py — unified design-system compliance audit.

Runs all six individual audit scripts and reports a single combined
exit code: 0 if everything's clean, 1 if any audit reports findings.

Wired by punch list §G in docs/octopus/v5_followups.md.

Usage:
    python scripts/design_system_audit.py          # full run
    python scripts/design_system_audit.py --quick  # skip WCAG (slowest)
    python scripts/design_system_audit.py --only wcag,a11y   # subset

Individual scripts can still be invoked directly:
    python scripts/_mockup_wcag_audit.py
    python scripts/_mockup_a11y_audit.py
    python scripts/_mockup_consistency_audit.py
    python scripts/_mockup_heading_audit.py
    python scripts/_mockup_cvd_audit.py
    python scripts/_mockup_link_audit.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AUDITS: list[tuple[str, str, bool]] = [
    # (short_name, script_path, fails_with_nonzero_exit)
    ("wcag",        "scripts/_mockup_wcag_audit.py",        True),
    ("a11y",        "scripts/_mockup_a11y_audit.py",        False),
    ("consistency", "scripts/_mockup_consistency_audit.py", False),
    ("headings",    "scripts/_mockup_heading_audit.py",     False),
    ("cvd",         "scripts/_mockup_cvd_audit.py",         False),
    ("links",       "scripts/_mockup_link_audit.py",        False),
]


def _run_one(short_name: str, script: str) -> tuple[int, str, float]:
    """Run one audit. Returns (exit_code, last_line_of_output, elapsed_s)."""
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.monotonic() - start
    # The "summary" is the last non-empty line of stdout. Strip the
    # replacement char so we don't blow up Windows cp1252 console.
    out = proc.stdout.strip().splitlines()
    summary = (out[-1] if out else "(no output)").replace("�", "-")
    return proc.returncode, summary, elapsed


def main() -> int:
    parser = argparse.ArgumentParser(prog="design_system_audit")
    parser.add_argument(
        "--only",
        type=lambda s: set(p.strip() for p in s.split(",") if p.strip()),
        default=None,
        help="Comma-separated audit names to run (default: all).",
    )
    parser.add_argument("--quick", action="store_true",
                        help="Skip the slowest audits.")
    args = parser.parse_args()

    selected = AUDITS
    if args.only:
        selected = [a for a in AUDITS if a[0] in args.only]
    if args.quick:
        selected = [a for a in selected if a[0] != "wcag"]

    if not selected:
        print("No audits selected.", file=sys.stderr)
        return 2

    print(f"Running {len(selected)} design-system audits...")
    print("-" * 88)

    fails: list[str] = []
    for short_name, script, fails_nonzero in selected:
        if not (ROOT / script).exists():
            print(f"  SKIP  {short_name:<14} {script} (missing)")
            continue
        code, summary, elapsed = _run_one(short_name, script)
        marker = "PASS" if code == 0 else "FAIL"
        if code != 0 and fails_nonzero:
            fails.append(short_name)
        print(f"  {marker:<5} {short_name:<14} {elapsed:>5.2f}s  {summary[:96]}")

    print("-" * 88)
    if fails:
        print(f"FAILED: {len(fails)} audit(s) — {', '.join(fails)}")
        return 1
    print(f"All {len(selected)} audits clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
