"""Verify player-pages Wave-1..9 against the Brief P0+P1+P2 checklist.

Runs after `python manage.py build-site` to confirm every shipped
module renders in `data-state="ready"` for representative players
across positions.

Targets:
  Dillon Gabriel  (QB, 11737) — Heisman finalist tier
  Tre Stewart     (RB, 6623)  — All-Conference RB
  K.J. Wallace    (CB, 3824)  — All-Conference DB

Usage:
  python scripts/verify_player_pages_wave_complete.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYERS_DIR = ROOT / "output" / "site" / "players"


TARGETS = [
    ("dillon-gabriel-11737.html", "Dillon Gabriel", "QB"),
    ("maddux-madsen-11807.html", "Maddux Madsen", "QB"),
    ("tre-stewart-6623.html", "Tre Stewart", "RB"),
    ("k-j-wallace-3824.html", "K.J. Wallace", "CB"),
]


# (module_id, expect_ready_for_positions, description)
MODULE_CHECKS = [
    # Wave 1-9 modules
    ("player-standing",       {"QB", "RB", "WR", "CB"}, "17-rung Standing rail"),
    ("game-log",              {"QB", "RB", "WR", "CB"}, "Game Log table"),
    ("box-savant",            {"QB", "RB", "WR", "CB"}, "Box-Score Savant card"),
    ("splits-v2",             {"QB", "RB", "WR", "CB"}, "Splits panels"),
    ("peer-comparator-v2",    {"QB", "RB", "WR", "CB"}, "Peer Comparator"),
    ("career-arc",            {"QB", "RB", "WR", "CB"}, "Career Arc rail"),
    ("heisman-trajectory",    {"QB"},                   "Heisman trajectory"),
    ("mirror-match",          {"QB", "RB"},             "Mirror match"),
    # Wave 10+ modules
    ("supporting-cast-v2",    {"QB", "RB", "WR", "CB"}, "Supporting Cast"),
    ("narrative-arc-v2",      {"QB", "RB", "WR", "CB"}, "Narrative Arc (LLM)"),
    ("nil-draft",             {"QB", "RB"},             "NIL + Draft card"),
    ("scenario-explorer-v2",  {"QB", "RB", "WR", "CB"}, "Scenario Explorer"),
    ("trophy-case-v2",        {"QB", "RB", "WR", "CB"}, "Trophy Case streams"),
]


def check_player(path: Path, name: str, position: str) -> list[tuple[str, bool, str]]:
    """Return list of (check_name, pass, details)."""
    if not path.exists():
        return [(f"file:{path.name}", False, "file missing")]

    html = path.read_text(encoding="utf-8", errors="ignore")
    results: list[tuple[str, bool, str]] = []

    # Hero composite score: should NOT be "Awaiting" on cell #1
    hero_match = re.search(
        r'<article class="qb-fingerprint__cell">.*?</article>', html, re.DOTALL,
    )
    if hero_match:
        cell1 = hero_match.group(0)
        is_awaiting = "qb-fingerprint__cell-value--awaiting" in cell1
        score_match = re.search(
            r'cell-value[^"]*"[^>]*>([^<]+)<', cell1,
        )
        score_val = score_match.group(1) if score_match else "?"
        results.append((
            "hero composite score",
            not is_awaiting and score_val.isdigit(),
            f"cell-1 value={score_val!r}{' (Awaiting)' if is_awaiting else ''}",
        ))
    else:
        results.append(("hero composite score", False, "no qb-fingerprint__cell found"))

    # Module checks
    for module_id, expect_pos, _desc in MODULE_CHECKS:
        if position not in expect_pos:
            continue
        ready_pat = rf'data-module="{re.escape(module_id)}"\s+data-state="ready"'
        empty_pat = rf'data-module="{re.escape(module_id)}"\s+data-state="empty"'
        ready = re.search(ready_pat, html) is not None
        empty = re.search(empty_pat, html) is not None
        if ready:
            results.append((f"module {module_id}", True, "ready"))
        elif empty:
            results.append((f"module {module_id}", False, "EMPTY"))
        else:
            results.append((f"module {module_id}", False, "missing"))

    # Signature story prose check: at least one of the cards in #signature-story
    # should have substantive non-template prose.
    sig_section = re.search(
        r'<section[^>]*id="signature-story".*?</section>', html, re.DOTALL,
    )
    if sig_section:
        body = sig_section.group(0)
        # Look for non-placeholder prose
        has_real = bool(re.search(r'[A-Z][a-z]+ [A-Z][a-z]+(?:\'s)? \d+', body))
        results.append((
            "signature story prose",
            has_real,
            "has stat-rich prose" if has_real else "looks like template",
        ))

    return results


def main() -> int:
    overall_pass = True
    summary_rows: list[tuple[str, int, int]] = []
    for slug, name, position in TARGETS:
        path = PLAYERS_DIR / slug
        print(f"\n=== {name} ({position}) — {slug} ===")
        results = check_player(path, name, position)
        passed = sum(1 for _, ok, _ in results if ok)
        total = len(results)
        for cname, ok, detail in results:
            tag = "PASS" if ok else "FAIL"
            print(f"  [{tag}] {cname}: {detail}")
        summary_rows.append((name, passed, total))
        if passed < total:
            overall_pass = False

    print("\n=== SUMMARY ===")
    for name, p, t in summary_rows:
        print(f"  {name}: {p}/{t}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
