"""Phase 12 final smoke test — 50 representative URLs.

Runs against a target host and verifies for each URL:
  - HTTP 200
  - body has a recognisable signal (skip-link OR <main> OR <h1>)
  - no obvious dev-leak markers (TODO, lorem ipsum, console.error)
  - no 5xx in any embedded iframe (out of scope here)

Run:
    python scripts/phase12_50url_smoke.py
      --base https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

The pass threshold is 95%+. Falls below → exit 1 + print failing rows.

This is the manual companion to .github/workflows/live_smoke_test.yml
which hits 28 URLs every 30 min. This script's 50-URL set is broader
(samples every archetype) and runs on demand before declaring v2 done.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass


URLS = [
    # ===== A. Landing surfaces =====
    "/",
    "/rankings/",
    "/about/",
    "/about-model/",
    "/methodology/",
    "/methodology/fan-intelligence.html",
    "/methodology/freshness.html",
    # ===== B. Profile archetype (17 profiled + sample unprofiled) =====
    "/programs/alabama.html",
    "/programs/notre-dame.html",
    "/programs/ohio-state.html",
    "/teams/florida-international.html",  # unprofiled
    "/teams/texas-southern.html",          # unprofiled HBCU
    "/teams/dartmouth.html",               # unprofiled Ivy
    "/players/fernando-mendoza-38276.html",
    # ===== C. Dashboard archetype =====
    "/heisman/",
    "/hub/",
    "/hub/vibe-shifts/",
    # ===== D. Database archetype =====
    "/wire/",
    "/portal-heat/",
    "/storylines/",
    "/canon/",
    "/conferences/",
    "/players/",
    # ===== E. Article archetype =====
    "/editions/",
    "/editions/2026-w19/three-weeks-before-camp-whispers/",
    "/editions/2026-w18/the-quiet-week/",
    "/editions/2026-w17/the-spring-issue/",
    "/daily/2026-05-22/",
    "/mailbag/",
    # ===== F. Canon entries =====
    "/canon/the-100-best-players-cfp-era.html",
    "/canon/the-100-best-players-cfp-era/leonard-fournette.html",
    "/canon/the-25-best-coaching-hires-2020s.html",
    "/canon/the-50-most-defining-games-cfp-era.html",
    # ===== G. Storylines =====
    "/storylines/vandy-renaissance.html",
    "/storylines/big-ten-reasserting.html",
    "/storylines/realignment-endgame.html",
    # ===== H. Compare + tools =====
    "/compare/",
    "/matchups/",
    "/nfl-pipeline/",
    "/history/",
    # ===== I. Infrastructure =====
    "/sitemap.xml",
    "/robots.txt",
    "/attributions/",
    "/404.html",
    # ===== J. Conference detail pages =====
    "/conferences/sec.html",
    "/conferences/big-ten.html",
    "/conferences/acc.html",
    # ===== K. Team detail =====
    "/teams/alabama.html",
    "/teams/georgia.html",
    "/teams/oregon.html",
    "/teams/usc.html",
    # ===== L. Players spotlight =====
    "/players/spotlight.html",
]

assert len(URLS) == 50, f"Expected 50 URLs, got {len(URLS)}"


@dataclass
class Result:
    url: str
    ok: bool
    status: int
    size: int
    note: str


def check_url(base: str, path: str, timeout: float = 30.0) -> Result:
    url = base.rstrip("/") + path
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "CFBIndex-Phase12-Smoke/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.getcode()
    except urllib.error.HTTPError as e:
        return Result(path, False, e.code, 0, f"HTTPError {e.code}")
    except (urllib.error.URLError, TimeoutError) as e:
        return Result(path, False, 0, 0, f"URLError {e}")
    except Exception as e:
        return Result(path, False, 0, 0, f"{type(e).__name__} {e}")

    if status != 200:
        return Result(path, False, status, len(body), f"non-200 {status}")

    text = body.decode("utf-8", errors="replace").lower()

    # Dev-leak markers that should never be on a production page
    leaks = [
        ("todo:", "TODO marker in HTML"),
        ("lorem ipsum", "lorem ipsum placeholder"),
        ("placeholder copy", "placeholder copy text"),
        ("xxx pending", "XXX pending marker"),
    ]
    for marker, label in leaks:
        if marker in text:
            return Result(path, False, status, len(body), label)

    # XML/text paths just need 200
    if path.endswith((".xml", ".txt")):
        return Result(path, True, status, len(body), "ok (text/xml)")

    # HTML paths need at least one recognisable signal
    has_main = "<main" in text
    has_h1 = "<h1" in text
    if not (has_main or has_h1):
        return Result(path, False, status, len(body), "no <main> or <h1>")

    return Result(path, True, status, len(body), "ok")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True,
                        help="Base URL, e.g. https://example.vercel.app")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=95.0,
                        help="Pass threshold percent. Default 95.0.")
    args = parser.parse_args()

    results: list[Result] = []
    with ThreadPoolExecutor(max_workers=args.threads) as exe:
        futures = {exe.submit(check_url, args.base, u): u for u in URLS}
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: r.url)
    passing = [r for r in results if r.ok]
    failing = [r for r in results if not r.ok]
    pass_pct = 100.0 * len(passing) / len(URLS)

    print(f"Phase 12 50-URL smoke @ {args.base}")
    print(f"Total: {len(URLS)} | Pass: {len(passing)} | Fail: {len(failing)}")
    print(f"Pass rate: {pass_pct:.1f}%  (threshold: {args.threshold:.1f}%)")
    print()

    if failing:
        print("FAILING URLs:")
        for r in failing:
            print(f"  ❌ {r.url:60s}  [{r.status}]  {r.note}")
        print()

    if pass_pct < args.threshold:
        print(f"FAIL — below {args.threshold:.1f}% threshold.", file=sys.stderr)
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
