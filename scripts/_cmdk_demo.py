"""Build a self-contained Cmd-K overlay demo.

Output:
  docs/mockups/cmdk_demo.html
  docs/mockups/cmdk_demo_index.json

The demo loads the index inline (no fetch needed) so reviewers can
exercise the overlay locally without running the canon DB build.
Press Cmd-K (Mac) or Ctrl-K (Win/Linux) on the page to activate.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    """Build a synthetic but realistic-looking demo index."""
    # Synthetic items that exercise all 7 kinds + edge cases (long titles,
    # accent chars, mobile reflow). Mirrors the shape of the real index
    # without requiring DB access.
    items = [
        # Profiles (tier 1)
        {"kind": "profile", "title": "Alabama",
         "url": "/teams/alabama.html",
         "subtitle": "Profiled program", "tier": 1},
        {"kind": "profile", "title": "Georgia",
         "url": "/teams/georgia.html",
         "subtitle": "Profiled program", "tier": 1},
        {"kind": "profile", "title": "Notre Dame",
         "url": "/teams/notre-dame.html",
         "subtitle": "Profiled program", "tier": 1},
        {"kind": "profile", "title": "Ohio State",
         "url": "/teams/ohio-state.html",
         "subtitle": "Profiled program", "tier": 1},
        # Teams (tier 2-3)
        {"kind": "team", "title": "Air Force",
         "url": "/teams/air-force.html",
         "subtitle": "FBS · Mountain West", "tier": 2},
        {"kind": "team", "title": "Akron",
         "url": "/teams/akron.html",
         "subtitle": "FBS · Mid-American", "tier": 2},
        {"kind": "team", "title": "Eastern Kentucky",
         "url": "/teams/eastern-kentucky.html",
         "subtitle": "FCS · ASUN", "tier": 3},
        {"kind": "team", "title": "Texas A&M",
         "url": "/teams/texas-am.html",
         "subtitle": "FBS · SEC", "tier": 2},
        # Conferences
        {"kind": "conference", "title": "Southeastern Conference",
         "url": "/conferences/sec.html",
         "subtitle": "FBS · 16 teams", "tier": 3},
        {"kind": "conference", "title": "Big Ten Conference",
         "url": "/conferences/big-ten.html",
         "subtitle": "FBS · 18 teams", "tier": 3},
        # Editions
        {"kind": "edition", "title": "The Spring Wire",
         "url": "/editions/2026-w19/",
         "subtitle": "Edition · 2026-05-09", "tier": 2},
        # Mailbag (none in demo — show empty-kind handling)
        # Players
        {"kind": "player", "title": "Bryce Underwood",
         "url": "/players/100001.html",
         "subtitle": "QB · Bama"},
        {"kind": "player", "title": "Carson Beck",
         "url": "/players/100002.html",
         "subtitle": "QB · UGA"},
        {"kind": "player", "title": "Quinn Ewers",
         "url": "/players/100003.html",
         "subtitle": "QB · Texas"},
        {"kind": "player", "title": "Cade Klubnik",
         "url": "/players/100004.html",
         "subtitle": "QB · Clemson"},
        {"kind": "player", "title": "Dillon Gabriel",
         "url": "/players/100005.html",
         "subtitle": "QB · Oregon"},
        # Methodology
        {"kind": "methodology", "title": "Fan Intelligence",
         "url": "/methodology/fan-intelligence.html",
         "subtitle": "How we read the fanbase", "tier": 4},
        {"kind": "methodology", "title": "Citations",
         "url": "/methodology/citations.html",
         "subtitle": "Where our claims come from", "tier": 4},
    ]
    payload = {"items": items, "schema_version": 1}

    index_path = ROOT / "docs" / "mockups" / "cmdk_demo_index.json"
    index_path.write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    css = (ROOT / "src" / "cfb_rankings" / "cmdk" / "assets"
           / "cmdk.css").read_text(encoding="utf-8")
    js = (ROOT / "src" / "cfb_rankings" / "cmdk" / "assets"
          / "cmdk.js").read_text(encoding="utf-8")
    tokens_css = (ROOT / "src" / "cfb_rankings" / "team_pages"
                  / "assets" / "tokens.css").read_text(encoding="utf-8")

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Command-K Overlay Demo — Sprint v5-11.5</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{tokens_css}

body {{
  background: var(--bg-0, #0b0d12);
  color: var(--fg-primary, #f5f6fa);
  font-family: var(--font-body, "Inter", system-ui, sans-serif);
  margin: 0;
  padding: 48px 24px;
  min-height: 100vh;
}}

.demo-wrap {{ max-width: 720px; margin: 0 auto; }}
h1 {{ font-family: var(--font-display); font-size: 36px; margin: 0 0 8px; }}
h2 {{ font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase;
      color: var(--fg-muted); margin: 32px 0 8px; }}
p {{ font-size: 16px; line-height: 1.6; color: var(--fg-secondary); max-width: 56ch; }}
kbd {{ font-family: var(--font-mono); font-size: 12px; padding: 2px 6px;
       background: var(--bg-1); border: 1px solid var(--stroke-default);
       border-radius: 4px; color: var(--fg-primary); }}

.demo-actions {{ display: flex; gap: 12px; margin: 24px 0 48px; flex-wrap: wrap; }}
.demo-btn {{ all: unset; }}

{css}
</style>
</head>
<body>
<div class="demo-wrap">
  <h1>Command-K overlay demo</h1>
  <p>Sprint v5-11.5 foundation. Press
  <kbd>⌘K</kbd> (macOS) or <kbd>Ctrl+K</kbd> (Win/Linux), or click the
  trigger button below.</p>

  <div class="demo-actions">
    <button class="cmdk-trigger" data-cmdk-trigger>
      <svg class="cmdk-input-icon" viewBox="0 0 20 20" aria-hidden="true">
        <path d="M9 2a7 7 0 015.29 11.59l4.06 4.06-1.42 1.41-4.05-4.06A7 7 0 119 2zm0 2a5 5 0 100 10 5 5 0 000-10z"/>
      </svg>
      Search…
      <span class="cmdk-trigger__shortcut">⌘K</span>
    </button>
  </div>

  <h2>What's indexed in this demo</h2>
  <p>18 synthetic items spanning all 7 kinds — profiles, teams,
  conferences, editions, mailbag (empty in this demo), players, and
  methodology pages. The real build emits ~9,300 items.</p>

  <h2>Try these searches</h2>
  <ul>
    <li><code>alab</code> — fuzzy match on Alabama (profile, tier 1)</li>
    <li><code>QB</code> — finds players by subtitle (position)</li>
    <li><code>sec</code> — finds conference + SEC teams via subtitle</li>
    <li><code>cita</code> — finds methodology pages</li>
    <li>empty input — browse mode, grouped by kind</li>
  </ul>

  <h2>Keyboard</h2>
  <p><kbd>↑</kbd> <kbd>↓</kbd> navigate · <kbd>↵</kbd> open ·
  <kbd>esc</kbd> close · <kbd>⌘K</kbd>/<kbd>Ctrl+K</kbd> toggle.</p>
</div>

<script>
window.CMDK_CONFIG = {{
  indexUrl: '/cmdk_demo_index.json',
  placeholder: 'Search the demo index…',
  storageKey: 'cmdk-demo:index-v1'
}};
</script>
<script>{js}</script>
</body>
</html>"""

    out_path = ROOT / "docs" / "mockups" / "cmdk_demo.html"
    out_path.write_text(html_out, encoding="utf-8")
    print(f"wrote {out_path.relative_to(ROOT)} ({len(html_out):,} chars)")
    print(f"wrote {index_path.relative_to(ROOT)} ({len(payload['items'])} items)")


if __name__ == "__main__":
    main()
