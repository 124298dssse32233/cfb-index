#!/usr/bin/env python3
"""
decorate_rankings_table.py — post-process output/site/rankings/index.html to
add mobile card-view attributes:

  1. Adds data-wcfb-card-mobile to the <table> tag (triggers CSS rule)
  2. Adds data-label="..." to each <td> in each row, positionally

The CSS in wcfb-enhancements.css uses these attributes to transform the
table into stacked cards at viewport ≤720px.

Idempotent: skips if data-wcfb-card-mobile is already present.
"""
import re
import sys
from pathlib import Path

PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/site/rankings/index.html")

# Position-to-label mapping based on the rankings table column order.
# Headers: Rank, Change, Team, Level, Power, Resume
LABELS = ["Rank", "Change", "Team", "Level", "Power", "Resume"]


def add_data_labels_to_row(row_html: str) -> str:
    """Walk <td> tags and add data-label by position. Skips if already present."""
    if 'data-label=' in row_html:
        return row_html

    cells_seen = [0]

    def replace_td(match):
        idx = cells_seen[0]
        cells_seen[0] += 1
        if idx >= len(LABELS):
            return match.group(0)
        label = LABELS[idx]
        tag = match.group(1)  # full <td...> opening tag
        # Insert data-label as the first attribute after `<td`
        if " data-label=" in tag:
            return match.group(0)
        new_tag = re.sub(r'<td\b', f'<td data-label="{label}"', tag, count=1)
        return new_tag

    return re.sub(r'(<td\b[^>]*>)', replace_td, row_html)


def main() -> int:
    if not PATH.exists():
        print(f"[decorate_rankings] {PATH} not found — skipping")
        return 0
    html = PATH.read_text(encoding="utf-8")

    if 'data-wcfb-card-mobile' in html:
        print("[decorate_rankings] already decorated — skipping")
        return 0

    # 1) Add the data-wcfb-card-mobile attribute to the rankings <table>.
    #    There's only one bare <table> in the rankings page (we verified).
    html_new = html.replace(
        '<table>\n            <thead>',
        '<table data-wcfb-card-mobile>\n            <thead>',
        1,
    )
    if html_new == html:
        # Fallback: any <table> tag preceding <thead>
        html_new = re.sub(
            r'<table([^>]*)>(\s*<thead>)',
            r'<table\1 data-wcfb-card-mobile>\2',
            html,
            count=1,
        )

    if html_new == html:
        print("[decorate_rankings] could not find rankings table to decorate")
        return 0

    # 2) Walk every <tr>...</tr> in the <tbody> and add data-label to its <td>s
    rows_decorated = [0]
    def per_row(match):
        rows_decorated[0] += 1
        return "<tr" + match.group(1) + ">" + add_data_labels_to_row(match.group(2)) + "</tr>"

    html_new = re.sub(
        r'<tr([^>]*data-rank[^>]*)>(.*?)</tr>',
        per_row,
        html_new,
        flags=re.DOTALL,
    )

    PATH.write_text(html_new, encoding="utf-8")
    print(f"[decorate_rankings] decorated {rows_decorated[0]} rows with data-label attributes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
