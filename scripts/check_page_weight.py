"""Page-weight budget reporter (WS-11, spec item 6).

Walks the built static site and reports per-page transfer weight, grouped by
page archetype (teams / players / programs / editions / ...). The number that
matters for real-world performance is the **gzipped** HTML document, since
Vercel serves every static page compressed — raw byte count overstates the
cost of our deliberately inlined CSS (team pages inline their stylesheet so
``file://`` renders faithfully; that CSS gzips down hard).

Default mode is **report-only** (exit 0): print the distribution and the worst
offenders so we can pick honest budgets before we gate anything. Pass
``--enforce`` to fail (exit 1) when more than ``--max-violations`` pages exceed
the gzip budget — wire that into CI only once the distribution is understood.

Usage:
    python scripts/check_page_weight.py
    python scripts/check_page_weight.py --site-dir output/site
    python scripts/check_page_weight.py --enforce --budget-kb 120 --max-violations 0
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path


# Archetype buckets keyed by first path segment under the site root. Anything
# not matched lands in "other" so nothing is silently dropped from the report.
_ARCHETYPE_DIRS = (
    "teams", "players", "programs", "editions", "wire", "mailbag",
    "reactions", "rankings", "methodology", "canon", "stories",
)


def _archetype_for(rel: Path) -> str:
    parts = rel.parts
    if len(parts) == 1:
        return "root"
    head = parts[0]
    return head if head in _ARCHETYPE_DIRS else "other"


def _kb(n: int) -> str:
    return f"{n / 1024:.0f}KB"


def _pct(sorted_vals: list[int], p: float) -> int:
    if not sorted_vals:
        return 0
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Report/enforce per-page transfer weight.")
    ap.add_argument("--site-dir", default="output/site")
    ap.add_argument("--budget-kb", type=int, default=150,
                    help="Gzip budget per HTML page in KB (default 150).")
    ap.add_argument("--enforce", action="store_true",
                    help="Exit 1 if violations exceed --max-violations.")
    ap.add_argument("--max-violations", type=int, default=0,
                    help="Allowed pages over budget before --enforce fails.")
    ap.add_argument("--top", type=int, default=10,
                    help="How many worst offenders to print.")
    args = ap.parse_args(argv)

    site = Path(args.site_dir)
    if not site.is_dir():
        print(f"::warning::site dir not found: {site} — skipping page-weight report")
        return 0

    files = sorted(site.rglob("*.html"))
    if not files:
        print(f"::warning::no HTML under {site} — skipping page-weight report")
        return 0

    budget = args.budget_kb * 1024
    by_arch: dict[str, list[int]] = {}
    all_gz: list[int] = []
    offenders: list[tuple[int, str]] = []
    violations = 0

    for f in files:
        data = f.read_bytes()
        gz = len(gzip.compress(data, 6))
        rel = f.relative_to(site)
        arch = _archetype_for(rel)
        by_arch.setdefault(arch, []).append(gz)
        all_gz.append(gz)
        offenders.append((gz, str(rel)))
        if gz > budget:
            violations += 1

    all_sorted = sorted(all_gz)
    print(f"Page-weight report — {len(files)} pages under {site} (gzip transfer size)")
    print(f"  overall  p50={_kb(_pct(all_sorted, .5))}  "
          f"p90={_kb(_pct(all_sorted, .9))}  p99={_kb(_pct(all_sorted, .99))}  "
          f"max={_kb(all_sorted[-1])}  budget={_kb(budget)}")
    print("  by archetype (count · p50 · p90 · max):")
    for arch in sorted(by_arch, key=lambda a: -max(by_arch[a])):
        vals = sorted(by_arch[arch])
        over = sum(1 for v in vals if v > budget)
        flag = f"  ⚠ {over} over budget" if over else ""
        print(f"    {arch:<12} {len(vals):>6} · {_kb(_pct(vals, .5)):>6} · "
              f"{_kb(_pct(vals, .9)):>6} · {_kb(vals[-1]):>6}{flag}")

    print(f"  worst {args.top} pages:")
    for gz, rel in sorted(offenders, reverse=True)[: args.top]:
        over = "  OVER" if gz > budget else ""
        print(f"    {_kb(gz):>7}  {rel}{over}")

    print(f"  pages over {_kb(budget)} budget: {violations}")

    if args.enforce and violations > args.max_violations:
        print(f"::error::page-weight: {violations} pages exceed {_kb(budget)} "
              f"(allowed {args.max_violations}).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
