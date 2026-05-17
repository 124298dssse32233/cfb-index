"""A11y static audit on each mockup file.
Doesn't replace axe / pa11y, but catches the high-leverage HTML defects
without needing a headless browser.
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

    # lang on html
    if not re.search(r"<html[^>]*\blang=", text):
        findings.append("MISS lang= on <html>")

    # viewport
    if "name=\"viewport\"" not in text:
        findings.append("MISS viewport meta")

    # main landmark
    if "<main " not in text and "<main>" not in text:
        findings.append("MISS <main>")

    # skip-link with link to main (saturday strip + dark mockup don't need full
    # site chrome since they're device-frame mockups)
    if "skip-link" not in text and path not in (
        "docs/mockups/mockup_06_saturday_strip.html",
        "docs/mockups/mockup_08_dark_share_cards.html",
        "docs/mockups/index.html",
    ):
        findings.append("MISS skip-link")

    # SVGs must have role="img" + aria-label
    svgs_no_role = re.findall(r"<svg(?![^>]*role=)[^>]*>", text)
    for s in svgs_no_role:
        findings.append(f"SVG missing role=img: {s[:80]}...")

    # Images must have alt (very loose check)
    imgs_no_alt = re.findall(r"<img\b(?![^>]*\balt=)[^>]*>", text)
    for i in imgs_no_alt:
        findings.append(f"img missing alt: {i[:80]}...")

    # Tab targets that are aria-hidden
    bad = re.findall(r"<a\s[^>]*aria-hidden", text)
    for b in bad:
        findings.append(f"<a> with aria-hidden: {b[:80]}...")

    # Headings — verify there is at least one h1 or h2 (allow either since
    # device-frame mockups have a frame-level h1)
    if not re.search(r"<h[12]\b", text):
        findings.append("MISS heading <h1>/<h2>")

    # focusable elements that lack href / type — require word boundary on <a
    bad_a = re.findall(r"<a\s(?![^>]*\bhref=)[^>]*>", text)
    if bad_a:
        findings.append(f"{len(bad_a)} <a> without href")

    # title element
    if "<title>" not in text:
        findings.append("MISS <title>")

    return findings


print(f"{'STATUS':<6} {'FILE':<46} FINDINGS")
print("-" * 90)
total_issues = 0
for m in MOCKUPS:
    f = audit(m)
    status = "OK   " if not f else "ISSUE"
    total_issues += len(f)
    print(f"{status} {m:<46} {len(f)} finding(s)")
    for fi in f:
        print(f"       - {fi}")
print("-" * 90)
print(f"Total: {len(MOCKUPS)} files · {total_issues} findings")
