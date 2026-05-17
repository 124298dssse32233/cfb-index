"""Render a citation-pattern specimen page.

Output: docs/mockups/citations_specimen.html

Builds a synthetic Pattern C/D article with inline citation markers,
the Wikipedia-style footer list, and the legacy-notice block. Used as
visual proof for reviewer verification of the v5-6a.5 receipt-pattern
foundation.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfb_rankings.citations import (  # noqa: E402
    Citation,
    annotate_body_markdown,
    render_citation_footer,
    render_legacy_notice,
)


SAMPLE_BODY = """\
Alabama's offseason narrative tightened around two threads this week.
The first is Kalen DeBoer's quiet QB-room re-stack[1] — three transfer
arrivals in 72 hours after a Bryce Underwood comp tape leaked to
247Sports. The second is something quieter, picked up first on
r/CFB[2] and corroborated by Andy Staples on the Locked On Tide pod[3]:
the offensive line's spring drill cadence is faster than any year
under Saban. Whether that translates to in-game pace is the open
question — and the betting market hasn't moved yet, which Stewart
Mandel called out as "the cleanest unbet edge of the spring"[4].

Underneath all of it, the recruiting picture is steadier than the
public-facing churn suggests. CFBD's class composite[5] still has
Alabama at #3 in the country, only a tenth of a point behind Georgia.
Bear in mind: the Tide finished 2025 at 13-1 with the SEC title and a
CFP semifinal loss — a season that, by their standards, gets called a
"rebuilding year." Nobody else's program operates with that calibration.
"""

CITATIONS = [
    Citation(
        marker_id=1,
        source_kind="beat_writer",
        source_label="Brett McMurphy · Action Network · May 14, 2026",
        source_url="https://example.com/action-network/alabama-qb-room",
        source_date="2026-05-14",
        confidence="primary",
    ),
    Citation(
        marker_id=2,
        source_kind="reddit",
        source_label='r/CFB · "Alabama OL pace under DeBoer — film thread" · 247 replies',
        source_url="https://www.reddit.com/r/CFB/comments/example",
        source_date="2026-05-12",
        confidence="supporting",
    ),
    Citation(
        marker_id=3,
        source_kind="podcast",
        source_label="Andy Staples · Locked On Crimson Tide · Ep. 1342 (May 13, 2026)",
        source_url="https://example.com/locked-on-tide/ep-1342",
        source_date="2026-05-13",
        confidence="supporting",
    ),
    Citation(
        marker_id=4,
        source_kind="beat_writer",
        source_label="Stewart Mandel · The Athletic · May 12, 2026",
        source_url="https://example.com/the-athletic/mandel-mailbag",
        source_date="2026-05-12",
        confidence="primary",
    ),
    Citation(
        marker_id=5,
        source_kind="cfbd",
        source_label="CollegeFootballData — 2026 recruiting class composite",
        source_url="https://collegefootballdata.com/recruiting",
        source_date="2026-05-15",
        confidence="background",
    ),
]


def main() -> None:
    annotated_body = annotate_body_markdown(SAMPLE_BODY, CITATIONS)
    footer_html = render_citation_footer(CITATIONS)
    legacy_html = render_legacy_notice("2026-05-17")

    css = (ROOT / "src" / "cfb_rankings" / "citations" / "assets"
           / "citations.css").read_text(encoding="utf-8")
    js = (ROOT / "src" / "cfb_rankings" / "citations" / "assets"
          / "citations.js").read_text(encoding="utf-8")
    tokens_css = (ROOT / "src" / "cfb_rankings" / "team_pages" / "assets"
                  / "tokens.css").read_text(encoding="utf-8")

    body_html = "<p>" + annotated_body.strip().replace(
        "\n\n", "</p>\n<p>"
    ).replace("\n", " ") + "</p>"

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Receipt Pattern Specimen — Sprint v5-6a.5</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{tokens_css}

body {{
  background: var(--bg-0);
  color: var(--fg-primary);
  font-family: var(--font-serif);
  font-size: var(--fs-serif-body);
  line-height: 1.65;
  max-width: 720px;
  margin: 0 auto;
  padding: 64px 24px;
}}

h1 {{ font-family: var(--font-display); font-size: 36px; margin: 0 0 16px; }}
h2 {{ font-family: var(--font-display); font-size: 14px; letter-spacing: 0.16em;
      text-transform: uppercase; color: var(--fg-muted); margin: 32px 0 12px; }}
p {{ margin: 0 0 16px; }}

{css}
</style>
</head>
<body>
<h1>Alabama's quiet spring: three signals</h1>
<h2>v5-6a.5 receipt-pattern specimen</h2>

{body_html}

{footer_html}

<h2 style="margin-top:80px;">Legacy notice (for pre-cutover content)</h2>
{legacy_html}

<script>{js}</script>
</body>
</html>"""

    out_path = ROOT / "docs" / "mockups" / "citations_specimen.html"
    out_path.write_text(html_out, encoding="utf-8")
    print(f"wrote {out_path.relative_to(ROOT)} ({len(html_out):,} chars)")
    print(f"  citation markers in body: {annotated_body.count('class=\"citation\"')}")
    print(f"  footer entries: {len(CITATIONS)}")


if __name__ == "__main__":
    main()
