"""Sprint 6 voice-quality pass — 5 outcomes × 3 voice-contrast programs.

Runs the post-game narrative generator via Opus through the claude CLI for
all 15 (program, outcome) combinations in parallel (default 4 workers).
Writes a Markdown report to research/sprint6_voice_pass_<UTC>.md and prints
a summary.

Usage:
  python tools/run_sprint6_voice_pass.py
  python tools/run_sprint6_voice_pass.py --workers 6 --model claude-opus-4-7
  python tools/run_sprint6_voice_pass.py --programs alabama notre-dame
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cfb_rankings.config import AppConfig  # noqa: E402
from cfb_rankings.db import Database  # noqa: E402
from cfb_rankings.team_pages.data import fetch_team_snapshot  # noqa: E402
from cfb_rankings.team_pages.narrative_generator import (  # noqa: E402
    generate_state_of_team_post_game,
)
from cfb_rankings.team_pages.profile_loader import load_profile  # noqa: E402
from cfb_rankings.team_pages.state_resolver import resolve_state  # noqa: E402


DEFAULT_PROGRAMS = ("alabama", "notre-dame", "massachusetts")
OUTCOMES = ("win-clear", "win-upset", "loss-close", "loss-blowout", "loss-upset")


def synth_meta(outcome: str, program: str) -> dict:
    """Return a clean live_game_meta payload that lands the desired outcome."""
    final_dt = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    if outcome == "win-clear":
        return {
            "home_team_slug": program, "away_team_slug": "tomato-can",
            "home_score": 45, "away_score": 3,
            "pre_game_spread_home": -28.0,
            "status": "final", "final_at_utc": final_dt,
        }
    if outcome == "win-upset":
        return {
            "home_team_slug": "blueblood-favorite", "away_team_slug": program,
            "home_score": 24, "away_score": 27,
            "pre_game_spread_home": -21.0,
            "status": "final", "final_at_utc": final_dt,
        }
    if outcome == "loss-close":
        return {
            "home_team_slug": "rival-program", "away_team_slug": program,
            "home_score": 31, "away_score": 24,
            "pre_game_spread_home": -10.0,
            "status": "final", "final_at_utc": final_dt,
        }
    if outcome == "loss-blowout":
        return {
            "home_team_slug": "national-power", "away_team_slug": program,
            "home_score": 45, "away_score": 14,
            "pre_game_spread_home": -10.0,
            "status": "final", "final_at_utc": final_dt,
        }
    if outcome == "loss-upset":
        return {
            "home_team_slug": program, "away_team_slug": "underdog-program",
            "home_score": 17, "away_score": 20,
            "pre_game_spread_home": -14.0,
            "status": "final", "final_at_utc": final_dt,
        }
    raise ValueError(outcome)


def run_one(*, db_url: str, program: str, outcome: str, model: str) -> dict:
    """Run one (program, outcome) LLM narrative call. Returns a result dict."""
    started = time.time()
    db = Database(db_url)
    try:
        profile = load_profile(program)
    except FileNotFoundError as exc:
        return {
            "program": program, "outcome": outcome,
            "ok": False, "error": f"profile-missing: {exc}",
            "duration_s": 0.0,
        }
    snap = fetch_team_snapshot(db, program)
    meta = synth_meta(outcome, program)
    state = resolve_state(profile, snap, live_game_meta=meta)
    try:
        res = generate_state_of_team_post_game(
            profile, snap, state, final_meta=meta,
            mode="claude-code", claude_model=model,
        )
        return {
            "program": program, "outcome": outcome,
            "voice_register": profile.voice_register,
            "anchor": state.anchor_variant,
            "tone": state.copy_tone,
            "ok": True,
            "model_id": res.model_id,
            "word_count": len(res.body_md.split()),
            "body_md": res.body_md,
            "duration_s": round(time.time() - started, 1),
        }
    except Exception as exc:
        return {
            "program": program, "outcome": outcome,
            "ok": False, "error": f"{type(exc).__name__}: {exc}",
            "duration_s": round(time.time() - started, 1),
        }


def write_markdown_report(results: list[dict], path: Path, model: str, total_s: float) -> None:
    lines: list[str] = []
    lines.append(f"# Sprint 6 voice-quality pass — {model}")
    lines.append("")
    lines.append(f"_Generated {datetime.now(timezone.utc).isoformat()} · "
                 f"total {total_s:.1f}s · {len(results)} paragraphs_")
    lines.append("")
    ok_count = sum(1 for r in results if r["ok"])
    lines.append(f"**Passing:** {ok_count} / {len(results)}")
    lines.append("")

    by_outcome: dict[str, list[dict]] = {}
    for r in results:
        by_outcome.setdefault(r["outcome"], []).append(r)

    for outcome in OUTCOMES:
        if outcome not in by_outcome:
            continue
        lines.append(f"## {outcome}")
        lines.append("")
        for r in by_outcome[outcome]:
            lines.append(f"### {r['program']}")
            lines.append("")
            if not r["ok"]:
                lines.append(f"**FAILED** — {r.get('error')}")
                lines.append("")
                continue
            lines.append(f"- Voice register: `{r.get('voice_register')}`")
            lines.append(f"- Anchor: `{r.get('anchor')}`")
            lines.append(f"- Tone: `{r.get('tone')}`")
            lines.append(f"- Model: `{r.get('model_id')}` · "
                         f"{r['word_count']} words · {r['duration_s']:.1f}s")
            lines.append("")
            lines.append("> " + r["body_md"].strip().replace("\n", "\n> "))
            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--programs", nargs="+", default=list(DEFAULT_PROGRAMS),
                   help="Programs to include (default: alabama notre-dame massachusetts)")
    p.add_argument("--outcomes", nargs="+", default=list(OUTCOMES),
                   help="Outcome categories to include (default: all 5)")
    p.add_argument("--model", default="claude-opus-4-7",
                   help="Claude model (default: claude-opus-4-7)")
    p.add_argument("--workers", type=int, default=4,
                   help="Parallel CLI workers (default: 4)")
    p.add_argument("--out", default=None,
                   help="Markdown report path (default: research/sprint6_voice_pass_<UTC>.md)")
    args = p.parse_args()

    db_url = AppConfig.from_env().database_url
    pairs: list[tuple[str, str]] = [
        (prog, outcome) for outcome in args.outcomes for prog in args.programs
    ]
    print(f"voice pass: {len(pairs)} paragraphs · model={args.model} · "
          f"workers={args.workers}", flush=True)

    started = time.time()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {
            ex.submit(run_one, db_url=db_url, program=prog,
                      outcome=outcome, model=args.model): (prog, outcome)
            for (prog, outcome) in pairs
        }
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            tag = "OK " if r["ok"] else "ERR"
            note = (
                f"{r['word_count']}w" if r["ok"] else r.get("error", "?")
            )
            print(f"  {tag} [{r['outcome']:14}] {r['program']:14} "
                  f"{r['duration_s']:5.1f}s  {note}", flush=True)

    total_s = time.time() - started

    # Stable order in output
    results.sort(key=lambda r: (OUTCOMES.index(r["outcome"]) if r["outcome"] in OUTCOMES else 99,
                                 r["program"]))

    out_path = Path(args.out) if args.out else (
        REPO_ROOT / "research" /
        f"sprint6_voice_pass_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.md"
    )
    write_markdown_report(results, out_path, args.model, total_s)
    print(f"\nReport: {out_path}")
    print(f"Total wall: {total_s:.1f}s "
          f"({sum(1 for r in results if r['ok'])}/{len(results)} ok)")

    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
