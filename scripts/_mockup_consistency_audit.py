"""Cross-archetype consistency audit.

Verifies every mockup uses the same design primitives in the same way:
  - .eyebrow class for uppercase labels (not raw inline styles)
  - .hero-finding pattern present on every page that should have one
  - .section-title pattern with __rule suffix
  - .caption class for muted metadata
  - .confidence chips use the standard classes
  - .cite tags use the standard component
  - data-program attribute on team Profile archetypes only
"""

import re
from pathlib import Path

MOCKUPS = [
    ("docs/mockups/mockup_01_hub_v2.html",            "dashboard",  True),
    ("docs/mockups/mockup_02_team_alabama_v2.html",   "profile",    True),
    ("docs/mockups/mockup_03_team_vanderbilt_v2.html","profile",    True),
    ("docs/mockups/mockup_04_daily_v2.html",          "article",    True),
    ("docs/mockups/mockup_05_heisman_v2.html",        "dashboard",  True),
    ("docs/mockups/mockup_06_saturday_strip.html",    "mobile",     False),
    ("docs/mockups/mockup_07b_mood_map_svg.html",     "specimen",   False),
    ("docs/mockups/mockup_08_dark_share_cards.html",  "share-card", False),
    ("docs/mockups/mockup_09_tokens_specimen.html",   "specimen",   False),
    ("docs/mockups/index.html",                       "index",      False),
]


def audit(path, archetype, expects_hero):
    text = Path(path).read_text(encoding="utf-8")
    findings = []

    # Every primary archetype must have a hero-finding
    if expects_hero and 'class="hero-finding"' not in text and "hero-finding__number" not in text:
        findings.append("MISS .hero-finding (expected on this archetype)")

    # Profile archetypes must have data-program on <html>
    if archetype == "profile" and not re.search(r'<html[^>]*\bdata-program=', text):
        findings.append("MISS data-program on <html> (profile archetype)")

    # Profile archetypes must NOT use data-program for non-profile pages
    if archetype != "profile" and re.search(r'<html[^>]*\bdata-program=', text):
        findings.append("UNEXPECTED data-program on non-profile")

    # Eyebrow labels should use the .eyebrow class, not raw inline uppercase
    inline_uppercase = re.findall(
        r'style="[^"]*text-transform:\s*uppercase[^"]*"',
        text
    )
    if len(inline_uppercase) > 4:
        findings.append(
            f"{len(inline_uppercase)} inline uppercase styles (use .eyebrow / .caption / .pill instead)"
        )

    # Section titles should use .section-title with __rule
    titles = text.count('class="section-title"')
    rules = text.count('class="section-title__rule"')
    if titles and titles != rules:
        findings.append(
            f"section-title:{titles} vs section-title__rule:{rules} (every title should have a rule)"
        )

    # Confidence chips should never be inline-coloured; use the modifier class
    bad_conf = re.findall(r'class="confidence[^"]*"[^>]*style="', text)
    if bad_conf:
        findings.append(
            f"{len(bad_conf)} .confidence with inline style (use modifier classes)"
        )

    # cite markers should use the .cite class (not inline <sup>)
    if "receipt" in text.lower() or "/daily/" in text.lower():
        raw_sup = re.findall(r"<sup\b(?![^>]*class=)[^>]*>", text)
        if raw_sup:
            findings.append(
                f"{len(raw_sup)} raw <sup> tags (use .cite class)"
            )

    # Every page should have a single <h1>
    h1s = len(re.findall(r"<h1\b", text))
    if h1s != 1:
        findings.append(f"{h1s} <h1> tags (expected exactly 1)")

    # Mockup chrome present
    if 'class="mockup-stamp"' not in text and archetype != "index":
        findings.append("MISS .mockup-stamp (clearly mark these as mockups)")

    return findings


print(f"{'STATUS':<6}  {'ARCHETYPE':<10}  FILE")
print("-" * 92)
total = 0
for path, archetype, expects_hero in MOCKUPS:
    f = audit(path, archetype, expects_hero)
    status = "OK   " if not f else "ISSUE"
    total += len(f)
    print(f"{status}  {archetype:<10}  {path}  ({len(f)} finding(s))")
    for fi in f:
        print(f"          - {fi}")
print("-" * 92)
print(f"Total: {len(MOCKUPS)} files · {total} findings")
