"""Sprint 6 Chronicle game-edition LLM pass.

Generates 3 game-edition cards (anomaly + echo + retroactive) for both
teams in a fixture, using the Stage 3 LLM writer in 'auto' mode (Opus on
blue-bloods' top card, Sonnet otherwise). Writes a Markdown report to
research/sprint6_chronicle_pass_<UTC>.md.

Usage:
  python tools/run_sprint6_chronicle_pass.py
  python tools/run_sprint6_chronicle_pass.py --fixture tests/fixtures/mock_games/mock-loss-blowout.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cfb_rankings.config import AppConfig  # noqa: E402
from cfb_rankings.db import Database  # noqa: E402
from cfb_rankings.team_pages.chronicle_game_edition import (  # noqa: E402
    generate_game_edition_cards,
)
from cfb_rankings.team_pages.data import fetch_team_snapshot  # noqa: E402
from cfb_rankings.team_pages.profile_loader import load_profile  # noqa: E402


DEFAULT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "mock_games" / "mock-loss-close.json"


def _run_for_team(db, slug: str, fixture: dict, mode: str) -> dict:
    started = time.time()
    try:
        profile = load_profile(slug)
    except FileNotFoundError as exc:
        return {"slug": slug, "ok": False, "error": str(exc), "duration_s": 0.0}
    snap = fetch_team_snapshot(db, slug)
    final_dt = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    final_meta = {
        "home_team_slug": fixture["home_team_slug"],
        "away_team_slug": fixture["away_team_slug"],
        "home_score": fixture["final_home"],
        "away_score": fixture["final_away"],
        "pre_game_spread_home": fixture.get("pre_game_spread_home"),
        "final_at_utc": final_dt,
        "status": "final",
        "game_edition_seeds": fixture.get("game_edition_seeds") or {},
    }
    try:
        cards = generate_game_edition_cards(
            db, profile, snap,
            final_meta=final_meta,
            week=fixture.get("week"),
            mode=mode,
            include_divergence_card=False,
            log=lambda _msg: None,
        )
    except Exception as exc:
        return {"slug": slug, "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "duration_s": round(time.time() - started, 1)}
    return {
        "slug": slug,
        "voice_register": profile.voice_register,
        "ok": True,
        "duration_s": round(time.time() - started, 1),
        "cards": [{
            "card_type": c.card_type,
            "headline": c.headline,
            "body_md": c.body_md,
            "source_attribution": c.source_attribution,
            "model_id": c.model_id,
            "validation_notes": c.validation_notes,
            "word_count": len(c.body_md.split()),
        } for c in cards],
    }


def write_markdown_report(fixture_path: Path, results: list[dict],
                          mode: str, total_s: float, out_path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# Sprint 6 Chronicle game-edition pass — mode={mode}")
    lines.append("")
    lines.append(f"_Generated {datetime.now(timezone.utc).isoformat()} · "
                 f"fixture {fixture_path.name} · total {total_s:.1f}s_")
    lines.append("")
    for r in results:
        lines.append(f"## {r['slug']}")
        lines.append("")
        if not r["ok"]:
            lines.append(f"**FAILED** — {r.get('error')}")
            lines.append("")
            continue
        lines.append(f"- Voice register: `{r['voice_register']}`")
        lines.append(f"- Duration: {r['duration_s']:.1f}s")
        lines.append(f"- Cards: {len(r['cards'])}")
        lines.append("")
        for c in r["cards"]:
            lines.append(f"### {c['card_type']}: {c['headline']}")
            lines.append("")
            lines.append(f"- Model: `{c['model_id']}`")
            lines.append(f"- Words: {c['word_count']}")
            lines.append(f"- Attribution: `{c['source_attribution']}`")
            if c.get("validation_notes"):
                lines.append(f"- Validation notes: {c['validation_notes']}")
            lines.append("")
            lines.append("> " + c["body_md"].strip().replace("\n", "\n> "))
            lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", default=str(DEFAULT_FIXTURE),
                   help="Path to fixture JSON")
    p.add_argument("--mode", default="auto",
                   choices=("template", "sonnet", "opus", "auto"),
                   help="Chronicle writer mode")
    p.add_argument("--out", default=None,
                   help="Markdown report path (default: research/sprint6_chronicle_pass_<UTC>.md)")
    args = p.parse_args()

    fixture_path = Path(args.fixture)
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    db = Database(AppConfig.from_env().database_url)

    print(f"chronicle pass: fixture={fixture_path.name} mode={args.mode}",
          flush=True)
    started = time.time()
    results: list[dict] = []
    # Run home + away serially — Stage 3 pipeline already parallelizes
    # internally across the 3 cards.
    for slug in (fixture["home_team_slug"], fixture["away_team_slug"]):
        print(f"  starting {slug}...", flush=True)
        r = _run_for_team(db, slug, fixture, mode=args.mode)
        results.append(r)
        if r["ok"]:
            print(f"  OK  {slug:14} {r['duration_s']:5.1f}s  "
                  f"{len(r['cards'])} card(s)", flush=True)
        else:
            print(f"  ERR {slug:14}  {r.get('error')}", flush=True)

    total_s = time.time() - started
    out_path = Path(args.out) if args.out else (
        REPO_ROOT / "research" /
        f"sprint6_chronicle_pass_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.md"
    )
    write_markdown_report(fixture_path, results, args.mode, total_s, out_path)
    print(f"\nReport: {out_path}")
    print(f"Total wall: {total_s:.1f}s")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
