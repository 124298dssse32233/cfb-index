#!/usr/bin/env python3
"""
inject_rankings_logos.py — post-process output/site/rankings/index.html to add
team logo <img> tags before each team link.

Run after build-site as a standalone step so logos appear even when build-site
has no model runs and just preserves the prior HTML.

Usage:
    python tools/inject_rankings_logos.py [rankings_html_path]

Default path: output/site/rankings/index.html
"""

import re
import sys
from pathlib import Path

RANKINGS_HTML = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/site/rankings/index.html")
TEAM_ART_DIR = Path("output/site/assets/team-art")

LOGO_CSS = """
<style>
.rankings__team-logo {
  width: 24px;
  height: 24px;
  object-fit: contain;
  vertical-align: middle;
  margin-right: 6px;
  flex-shrink: 0;
}
.team-cell { vertical-align: middle; }
.team-cell .team-link { vertical-align: middle; }
.team-cell .submetric {
  display: block;
  font-size: 11px;
  color: var(--muted-foreground, #777);
  margin-top: 2px;
  margin-left: 32px;
}
</style>"""

def main():
    if not RANKINGS_HTML.exists():
        print(f"[inject_logos] {RANKINGS_HTML} not found — skipping")
        sys.exit(0)

    html = RANKINGS_HTML.read_text(encoding="utf-8")

    # Don't double-inject
    if "rankings__team-logo" in html:
        print("[inject_logos] logos already present — skipping")
        sys.exit(0)

    # Inject CSS before </head>
    html = html.replace("</head>", LOGO_CSS + "\n</head>", 1)

    # Add class="team-cell" to the <td> containing a team link, and inject logo img
    # Pattern: <td><a class="team-link" href="../teams/{slug}.html">
    def replace_td(m):
        slug = m.group(1)
        logo_path = TEAM_ART_DIR / slug / "logo_primary.png"
        if not logo_path.exists():
            return m.group(0)  # no logo for this slug, leave unchanged
        img = (
            f'<img class="rankings__team-logo" '
            f'src="../assets/team-art/{slug}/logo_primary.png" '
            f'alt="{slug}" loading="lazy" onerror="this.style.display=\'none\'">'
        )
        return f'<td class="team-cell">{img}<a class="team-link" href="../teams/{slug}.html">'

    pattern = r'<td><a class="team-link" href="\.\./teams/([^"]+)\.html">'
    new_html, count = re.subn(pattern, replace_td, html)

    RANKINGS_HTML.write_text(new_html, encoding="utf-8")
    print(f"[inject_logos] injected logos into {count} team rows in {RANKINGS_HTML}")


if __name__ == "__main__":
    main()
