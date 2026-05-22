"""Live-site smoke test for CFB Index.

Hits a representative spread of URLs across every major site section and
reports 200/404/error counts. Designed to be safe to run anywhere — just
needs Python 3.10+ stdlib (urllib).

Use cases:
- Post-deploy verification: did the latest deploy break anything obvious?
- Daily monitoring: cron this somewhere and alert if pass-rate drops.
- Debugging: which section of the site is currently broken?

Usage:
    python scripts/smoke_test_live.py
    python scripts/smoke_test_live.py --base https://staging.example.com
    python scripts/smoke_test_live.py --fail-under 95   # exit 1 if <95% pass
    python scripts/smoke_test_live.py --json            # machine-readable

Exit codes:
    0 = pass rate meets --fail-under threshold (default 100)
    1 = pass rate below threshold OR networking failure
    2 = invalid arguments

The URL list is curated — not a full crawl. Add new entries here when
new top-level sections ship, and treat persistent regressions as a real
signal worth investigating rather than reflexively widening this list.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE = "https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app"

# Curated representative URL set per section. Adding URLs here is cheap;
# removing them costs coverage. Each entry is (path, category, why-included).
URLS: list[tuple[str, str, str]] = [
    # Roots
    ("/", "root", "Homepage — most-trafficked page"),

    # Section indexes
    ("/heisman/index.html", "section-index", "Heisman board — high-value linkable page"),
    ("/rankings/", "section-index", "Rankings — core product page"),
    ("/teams/", "section-index", "Teams directory"),
    ("/players/", "section-index", "Players directory"),
    ("/programs/", "section-index", "Programs directory"),
    ("/conferences/", "section-index", "Conferences directory"),
    ("/editions/", "section-index", "Editorial editions archive"),
    ("/hub/vibe-shifts/", "section-index", "Hub vibe shifts"),
    ("/wire/", "section-index", "The Wire"),
    ("/about-model/", "section-index", "Methodology — model"),
    ("/methodology/", "section-index", "Methodology landing"),
    ("/compare/", "section-index", "Team comparison tool"),
    ("/storylines/", "section-index", "Storylines"),
    ("/history/", "section-index", "Historical archive"),

    # Sampled detail pages — players (drawn from Heisman board)
    ("/players/fernando-mendoza-38276.html", "player-detail",
     "Mendoza — the canonical 'is the player ID URL stable' check"),
    ("/players/jeremiyah-love-48316.html", "player-detail",
     "Love — top non-QB from Heisman board"),
    ("/players/byrum-brown-38981.html", "player-detail",
     "Brown — Group of Five representative"),

    # Sampled team pages (profiled programs)
    ("/teams/alabama.html", "team-detail", "Alabama — top profiled team"),
    ("/teams/georgia.html", "team-detail", "Georgia — top profiled team"),
    ("/teams/ohio-state.html", "team-detail", "Ohio State — top profiled team"),
    ("/teams/notre-dame.html", "team-detail", "Notre Dame — profiled"),
    ("/teams/oregon.html", "team-detail", "Oregon — profiled"),
    ("/teams/texas.html", "team-detail", "Texas — profiled"),
    ("/teams/uconn.html", "team-detail", "UConn — small profiled team"),
    ("/teams/vanderbilt.html", "team-detail", "Vanderbilt — small profiled team"),

    # Unprofiled team (legacy renderer)
    ("/teams/florida-international.html", "team-detail",
     "FIU — unprofiled team, exercises the legacy reporting.py renderer"),

    # 404 page itself should resolve to a 200 served as the 404 body
    ("/404.html", "static", "Custom 404 page"),
]


@dataclass
class Result:
    path: str
    category: str
    status: int  # HTTP status or -1 on network error
    elapsed_ms: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 400


def fetch_head(url: str, timeout: float = 10.0) -> tuple[int, int, str | None]:
    """Return (status, elapsed_ms, error). HEAD with GET fallback for picky CDNs."""
    start = time.perf_counter()
    for method in ("HEAD", "GET"):
        req = Request(url, method=method, headers={
            "User-Agent": "cfb-index-smoke-test/1.0",
            "Accept": "text/html,*/*",
        })
        try:
            with urlopen(req, timeout=timeout) as resp:
                elapsed = int((time.perf_counter() - start) * 1000)
                return resp.status, elapsed, None
        except HTTPError as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            # Some sites 405 on HEAD — retry as GET. Other 4xx/5xx is final.
            if method == "HEAD" and exc.code == 405:
                continue
            return exc.code, elapsed, None
        except URLError as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            return -1, elapsed, f"network: {exc}"
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.perf_counter() - start) * 1000)
            return -1, elapsed, f"unexpected: {type(exc).__name__}: {exc}"
    elapsed = int((time.perf_counter() - start) * 1000)
    return -1, elapsed, "no method succeeded"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help=f"Base URL (default: {DEFAULT_BASE})")
    parser.add_argument("--fail-under", type=float, default=100.0,
                        help="Exit 1 if pass-rate %% < this (default: 100)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of human-readable table")
    parser.add_argument("--category", default=None,
                        help="Only test URLs in this category")
    args = parser.parse_args(argv)

    base = args.base.rstrip("/")
    targets = [(p, c, w) for (p, c, w) in URLS
               if args.category is None or c == args.category]

    results: list[Result] = []
    for (path, category, _why) in targets:
        url = f"{base}{path}"
        status, elapsed_ms, error = fetch_head(url)
        results.append(Result(path=path, category=category,
                              status=status, elapsed_ms=elapsed_ms,
                              error=error))

    pass_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - pass_count
    pass_rate = (pass_count / len(results) * 100) if results else 0.0

    if args.json:
        payload = {
            "base": base,
            "total": len(results),
            "passed": pass_count,
            "failed": fail_count,
            "pass_rate": round(pass_rate, 2),
            "fail_under": args.fail_under,
            "results": [
                {"path": r.path, "category": r.category,
                 "status": r.status, "elapsed_ms": r.elapsed_ms,
                 "error": r.error, "ok": r.ok}
                for r in results
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Base: {base}")
        print(f"{'STATUS':>6} {'MS':>5}  {'CAT':<14} PATH")
        print("-" * 80)
        for r in sorted(results, key=lambda x: (not x.ok, x.category, x.path)):
            marker = " " if r.ok else "X"
            err_suffix = f"  ! {r.error}" if r.error else ""
            print(f"{marker} {r.status:>4} {r.elapsed_ms:>5}  {r.category:<14} {r.path}{err_suffix}")
        print("-" * 80)
        print(f"Pass: {pass_count}/{len(results)} ({pass_rate:.1f}%) "
              f"-- threshold {args.fail_under:.1f}%")

    return 0 if pass_rate >= args.fail_under else 1


if __name__ == "__main__":
    raise SystemExit(main())
