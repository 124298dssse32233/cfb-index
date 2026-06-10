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


# NOTE 2026-05-23: Use the user-facing short URL by default. The longer
# scoped URL DOES auto-rotate on every Vercel deploy, but the short alias
# wonderful-margulis-8ec96b.vercel.app didn't rotate for several deploys —
# so smoke-testing the short URL is the only way to catch the alias rotation
# bug class. The DEFAULT_BASE constant below points at the live URL users
# actually hit.
DEFAULT_BASE = "https://wonderful-margulis-8ec96b.vercel.app"
DEFAULT_BASE_SCOPED = "https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app"

# Team pages that MUST ship with world-class chrome (team-page class) and
# never the legacy 'premium-team-hero' class. Anything regressing back to
# legacy is a deploy failure even if the HTTP status is 200.
CHROME_CHECK_TEAMS = [
    "alabama",      # original 17 PROFILED_SLUGS — should always be world-class
    "cincinnati",   # newer profile — canary for the silent-fail bug class
    "indiana",      # newer profile — also a canary
    "ohio-state",
    "notre-dame",
]

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
    ("/hub/backometer/", "section-index", "Backometer fan-belief board"),
    ("/wire/", "section-index", "The Wire"),
    ("/about-model/", "section-index", "Methodology — model"),
    ("/methodology/", "section-index", "Methodology landing"),
    ("/compare/", "section-index", "Team comparison tool"),
    ("/storylines/", "section-index", "Storylines"),
    ("/history/", "section-index", "Historical archive"),
    ("/anniversary/today/", "section-index", "Today-in-CFB-history daily render — render-today-in-history CLI writes here despite workflow comment saying /today-in-history/"),

    # Sampled detail pages — players (drawn from Heisman board).
    # NOTE 2026-06-10: player_id is NOT stable across re-ingest — these IDs
    # changed from 38276/48316/38981 to the 12xxx values below when the player
    # table was rebuilt, which is itself a linkrot signal worth fixing upstream.
    # Until IDs are pinned, refresh these to the current built pages.
    ("/players/fernando-mendoza-12763.html", "player-detail",
     "Mendoza — the canonical 'is the player ID URL stable' check"),
    ("/players/jeremiyah-love-12194.html", "player-detail",
     "Love — top non-QB from Heisman board"),
    ("/players/byrum-brown-12655.html", "player-detail",
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
    parser.add_argument("--check-chrome", action="store_true",
                        help="ALSO fetch CHROME_CHECK_TEAMS team pages and verify "
                             "they ship world-class chrome (team-page class, no "
                             "premium-team-hero). Catches the alias rotation bug.")
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

    # Chrome regression check (post-2026-05-23). Pulls the full body of
    # known-canary team pages and asserts they're world-class, not legacy.
    chrome_failures: list[str] = []
    if args.check_chrome:
        try:
            from urllib.request import Request, urlopen
            for slug in CHROME_CHECK_TEAMS:
                url = f"{base}/teams/{slug}.html"
                try:
                    req = Request(url, headers={"User-Agent": "cfb-smoke-chrome/1.0"})
                    with urlopen(req, timeout=20) as resp:
                        body = resp.read().decode("utf-8", errors="ignore")
                except Exception as exc:
                    chrome_failures.append(f"{slug}: fetch failed — {type(exc).__name__}: {exc}")
                    continue
                has_world_class = "team-page" in body and "premium-team-hero" not in body
                if not has_world_class:
                    has_premium = "premium-team-hero" in body
                    reason = "premium-team-hero present" if has_premium else "team-page missing"
                    chrome_failures.append(f"{slug}: legacy chrome — {reason}")
        except Exception as exc:
            chrome_failures.append(f"chrome check setup failed: {exc}")

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
        if args.check_chrome:
            if chrome_failures:
                print(f"\nCHROME CHECK FAILED ({len(chrome_failures)} regressions):")
                for f in chrome_failures:
                    print(f"  X {f}")
            else:
                print(f"\nChrome check: all {len(CHROME_CHECK_TEAMS)} canary pages world-class")

    http_ok = pass_rate >= args.fail_under
    chrome_ok = not chrome_failures
    return 0 if (http_ok and chrome_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
