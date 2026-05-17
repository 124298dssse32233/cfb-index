"""Heading-outline audit.
Verify every mockup has exactly one h1, no skipped heading levels.
"""

import re
from pathlib import Path

MOCKUPS = [
    "docs/mockups/mockup_01_hub_v2.html",
    "docs/mockups/mockup_02_team_alabama_v2.html",
    "docs/mockups/mockup_03_team_vanderbilt_v2.html",
    "docs/mockups/mockup_04_daily_v2.html",
    "docs/mockups/mockup_05_heisman_v2.html",
    "docs/mockups/mockup_06_saturday_strip.html",
    "docs/mockups/mockup_07b_mood_map_svg.html",
    "docs/mockups/mockup_08_dark_share_cards.html",
    "docs/mockups/mockup_09_tokens_specimen.html",
    "docs/mockups/index.html",
]


def audit(path):
    text = Path(path).read_text(encoding="utf-8")
    findings = []

    # Strip <style> blocks so we don't pick up CSS selectors like "h1.foo"
    text_no_style = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)

    # Find every h1..h6 element in document order
    headings = re.findall(r"<h([1-6])\b[^>]*>(.*?)</h\1>", text_no_style, re.DOTALL)
    levels = [int(h[0]) for h in headings]

    if not levels:
        findings.append("No headings at all")
        return findings, levels

    # Exactly one h1
    h1s = levels.count(1)
    if h1s != 1:
        findings.append(f"{h1s} h1 tags (need exactly 1)")

    # No skipped levels (h1 -> h3 without h2 in between)
    prev = 0
    for lvl in levels:
        if prev and lvl > prev + 1:
            findings.append(f"Skipped level: h{prev} -> h{lvl}")
        prev = lvl

    return findings, levels


print(f"{'STATUS':<6} {'FILE':<46} {'OUTLINE'}")
print("-" * 92)
total_issues = 0
for m in MOCKUPS:
    findings, levels = audit(m)
    status = "OK   " if not findings else "ISSUE"
    total_issues += len(findings)
    outline = " > ".join(f"h{l}" for l in levels[:12])
    if len(levels) > 12:
        outline += f" + {len(levels) - 12} more"
    print(f"{status} {m:<46} {outline}")
    for fi in findings:
        print(f"       - {fi}")
print("-" * 92)
print(f"Total: {len(MOCKUPS)} files · {total_issues} findings")
