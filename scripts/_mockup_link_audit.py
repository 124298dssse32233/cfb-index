"""Cross-mockup link audit.
Every internal link in docs/mockups/*.html must resolve to a file that
exists in docs/mockups/. External links (href starts with http) are
not validated.
"""

import re
from pathlib import Path

DIR = Path("docs/mockups")
files = sorted(p.name for p in DIR.glob("*.html"))
assets = sorted(p.name for p in DIR.glob("*.png"))
css = sorted(p.name for p in DIR.glob("*.css"))
all_local = set(files) | set(assets) | set(css) | {"index.html"}

print(f"Available files in {DIR}: {len(all_local)}")
print(f"  HTML: {len(files)}")
print(f"  PNG:  {len(assets)}")
print()

broken = []
for html_path in DIR.glob("*.html"):
    text = html_path.read_text(encoding="utf-8")
    # Find every href that doesn't start with http, #, or javascript
    hrefs = re.findall(r'href="([^"]+)"', text)
    for href in hrefs:
        # Skip externals, anchors, and javascript
        if href.startswith(("http", "#", "javascript:", "mailto:")):
            continue
        # Strip any query string / fragment for the file check
        path_only = href.split("?")[0].split("#")[0]
        if not path_only:
            continue
        if path_only not in all_local:
            broken.append((html_path.name, href))

print(f"Checked {len(files)} HTML files")
print(f"Broken internal links: {len(broken)}")
for src, href in broken:
    print(f"  {src} -> {href}")
