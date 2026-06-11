#!/usr/bin/env python3
"""Verify the generated site against the canonical build manifest (WP-0.2).

Asserts every global-nav target (and committed section page) declared in
``scripts/build_manifest.py`` exists in ``output/site`` and is not an empty
stub. This is the build-/deploy-time guard that prevents a recurrence of the
``/offseason/`` + ``/film-room/`` clobber (globally linked but never generated
→ 404 in a full-snapshot deploy).

Exit codes:
  0  all required nav routes present (section/stub issues are warnings).
  1  one or more REQUIRED_NAV_ROUTES missing  (only when --strict; default is
     warn-only so it can be wired into build_publish.ps1 before being promoted
     to a hard gate).
  2  bad invocation.

Usage:
  python scripts/verify_build_manifest.py [--site-dir output/site] [--strict] [--emit]
Stdlib only — safe to run in any environment.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Import the canonical manifest (same dir).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_manifest as M  # noqa: E402


def _redirect_target(f: Path, site: Path) -> "Path | None":
    """If f is an intentional meta-refresh redirect (e.g. a hub landing that
    forwards to its latest dated ledger), return the resolved target Path so the
    caller can confirm the target actually exists. Returns None if not a redirect."""
    try:
        head = f.read_text(encoding="utf-8", errors="ignore")[:800]
    except OSError:
        return None
    m = re.search(r'http-equiv=["\']?refresh["\']?[^>]*url=([^"\'>\s]+)', head, re.I)
    if not m:
        return None
    target = m.group(1).strip().lstrip("/").split("#", 1)[0].split("?", 1)[0]
    if not target or target.endswith("/") or not Path(target).suffix:
        target = target.rstrip("/") + "/index.html"
    return site / target


def _check(site: Path, routes: list[tuple[str, str]]) -> tuple[list, list, list]:
    missing, stub, ok = [], [], []
    for key, rel in routes:
        f = site / rel
        if not f.exists():
            missing.append((key, rel))
            continue
        tgt = _redirect_target(f, site)
        if tgt is not None:
            # A redirect is valid ONLY if its target exists (else it 404s the user).
            if tgt.exists():
                ok.append((key, rel))
            else:
                stub.append((key, rel, f"redirect→missing /{tgt.relative_to(site).as_posix()}"))
            continue
        if f.stat().st_size < M.STUB_BYTE_THRESHOLD:
            stub.append((key, rel, f.stat().st_size))
        else:
            ok.append((key, rel))  # full page
    return missing, stub, ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", default="output/site")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 if any REQUIRED_NAV_ROUTE is missing (default: warn-only).")
    ap.add_argument("--emit", action="store_true",
                    help="Write output/site/_build_manifest_routes.json with per-route status.")
    args = ap.parse_args()

    site = Path(args.site_dir)
    if not site.is_dir():
        print(f"ERROR: site dir not found: {site}", file=sys.stderr)
        return 2

    nav_missing, nav_stub, nav_ok = _check(site, M.REQUIRED_NAV_ROUTES)
    sec_missing, sec_stub, sec_ok = _check(site, M.EXPECTED_SECTION_ROUTES)

    print("== build-manifest verification ==")
    print(f"  nav routes:     {len(nav_ok)} ok / {len(nav_stub)} stub / {len(nav_missing)} MISSING "
          f"(of {len(M.REQUIRED_NAV_ROUTES)})")
    print(f"  section routes: {len(sec_ok)} ok / {len(sec_stub)} stub / {len(sec_missing)} missing "
          f"(of {len(M.EXPECTED_SECTION_ROUTES)})")
    for key, rel in nav_missing:
        print(f"  [FAIL] nav route MISSING: /{rel}  ({key}) — globally linked, will 404 in prod")
    for key, rel, sz in nav_stub:
        _d = f"{sz} B" if isinstance(sz, int) else str(sz)
        print(f"  [{'FAIL' if args.strict else 'warn'}] nav route empty/stub: /{rel}  ({_d}) — would ship a clobbered page")
    for key, rel in sec_missing:
        print(f"  [warn] section route missing: /{rel}  ({key})")
    for key, rel, sz in sec_stub:
        _d = f"{sz} B" if isinstance(sz, int) else str(sz)
        print(f"  [warn] section route empty/stub: /{rel}  ({_d})")

    render_gaps = M.gaps("GAP-render")
    if render_gaps:
        print(f"  [info] {len(render_gaps)} documented box-omitted RENDER command(s) "
              f"(see build_manifest.COMMAND_PARITY): "
              + ", ".join(c["cmd"] for c in render_gaps))

    if args.emit:
        out = {
            "nav_ok": [r for _, r in nav_ok],
            "nav_missing": [r for _, r in nav_missing],
            "nav_stub": [r for _, r, _ in nav_stub],
            "section_missing": [r for _, r in sec_missing],
            "render_gaps": [c["cmd"] for c in render_gaps],
        }
        (site / "_build_manifest_routes.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("  emitted output/site/_build_manifest_routes.json")

    if nav_missing or nav_stub:
        if args.strict:
            print("RESULT: FAIL (nav routes missing or empty/stub; --strict)")
            return 1
        print("RESULT: WARN (nav routes missing/stub; not strict — promote to --strict once green)")
        return 0
    print("RESULT: OK (all required nav routes present and non-stub)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
