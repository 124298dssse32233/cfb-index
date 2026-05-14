#!/usr/bin/env python3
"""
tools/wcfb_enhancements/install.py — install the World-Class CFB Index
enhancement layer into output/site/.

What this does, idempotently:
  1. Copies wcfb-enhancements.css + wcfb-enhancements.js into output/site/assets/
  2. Walks every output/site/**/*.html and injects the <link> + <script>
     tags before </head> (only if not already present).
  3. Skips: 404.html, any file already bearing the WCFB_MARKER comment.

Run after build-site as a publish-step. Safe to run multiple times.

Usage:
    python tools/wcfb_enhancements/install.py [site_dir]
Default site_dir: output/site
"""
import re
import shutil
import sys
import time
from pathlib import Path

WCFB_MARKER = "<!-- wcfb-enhancements -->"
ASSETS_TO_COPY = ["wcfb-enhancements.css", "wcfb-enhancements.js"]

# Tag block to insert before </head>. The marker line lets us detect+skip
# already-injected pages.
INJECT_BLOCK = (
    '\n'
    f'{WCFB_MARKER}\n'
    '<link rel="stylesheet" href="/assets/wcfb-enhancements.css">\n'
    '<script src="/assets/wcfb-enhancements.js" defer></script>\n'
)

HEAD_CLOSE_RE = re.compile(r'</head>', re.IGNORECASE)


def copy_assets(site_dir: Path, src_dir: Path) -> None:
    assets_dir = site_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for name in ASSETS_TO_COPY:
        src = src_dir / name
        dst = assets_dir / name
        if not src.exists():
            print(f"[wcfb-install] WARNING: source missing {src}")
            continue
        shutil.copyfile(src, dst)
        print(f"[wcfb-install] wrote {dst} ({dst.stat().st_size} bytes)")


def inject_into_html(path: Path) -> bool:
    """Return True if the file was modified."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[wcfb-install] SKIP unreadable: {path} ({e})")
        return False
    if WCFB_MARKER in content:
        return False  # already injected
    if "</head>" not in content.lower():
        return False  # no head close — skip
    new_content, n = HEAD_CLOSE_RE.subn(INJECT_BLOCK + "</head>", content, count=1)
    if n != 1:
        return False
    path.write_text(new_content, encoding="utf-8")
    return True


def main() -> int:
    site_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/site")
    src_dir = Path(__file__).resolve().parent

    if not site_dir.exists():
        print(f"[wcfb-install] ERROR: site dir does not exist: {site_dir}")
        return 1

    print(f"[wcfb-install] site_dir={site_dir.resolve()}")
    print(f"[wcfb-install] src_dir={src_dir.resolve()}")

    copy_assets(site_dir, src_dir)

    t0 = time.time()
    htmls = list(site_dir.rglob("*.html"))
    modified = 0
    skipped = 0
    for p in htmls:
        if inject_into_html(p):
            modified += 1
        else:
            skipped += 1
    elapsed = time.time() - t0
    print(f"[wcfb-install] scanned {len(htmls)} HTML files in {elapsed:.1f}s — "
          f"modified={modified} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
