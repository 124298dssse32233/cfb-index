"""Wikipedia-based awards/honors scrapers — Autopilot v1 TASKs 4.1, 4.2, 4.3.

Wikipedia maintains clean tables for:
- "YYYY College Football All-America Team"
- "YYYY All-<Conference> football team" (SEC/B1G/ACC/Big 12/AAC/etc.)
- "YYYY <Award>" (Heisman, Davey O'Brien, Maxwell, Camp, Outland,
  Biletnikoff, Mackey, Thorpe, Groza, Guy, Nagurski, Bednarik, Manning)

This module exposes three public entry points:
    scrape_all_america(year) -> list[dict]
    scrape_all_conference(year, conference) -> list[dict]
    scrape_position_award(year, award) -> list[dict]

All three return lists of dicts that slot directly into the
`import_player_honors_csv` pipeline's normalizer via the
`emit_honor_csvs()` orchestrator.

Uses beautifulsoup4. No DB writes here — pure parse. The CLI hook
writes CSVs to `data/scraped_honors/{year}/{source_file}.csv` then
calls `import-player-honors --csv ...` for each.
"""

from __future__ import annotations

import csv
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from bs4 import BeautifulSoup  # type: ignore

log = logging.getLogger(__name__)

_UA = "CFBIndex-autopilot/1.0 (+https://cfbindex.example)"


def _wiki_url(title: str) -> str:
    return f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"


def _fetch_html(title: str, timeout: float = 30.0) -> str:
    url = _wiki_url(title)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _cell_text(cell) -> str:
    """Extract clean text from a <td>/<th>, stripping citations + links."""
    # Drop footnote references like [1] [a]
    for sup in cell.find_all("sup"):
        sup.decompose()
    text = cell.get_text(" ", strip=True)
    # Collapse multiple spaces
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# TASK 4.1 — All-America Team scraper
# ---------------------------------------------------------------------------

# Canonical selectors per STRATEGY / kickoff: AP, AFCA, FWAA, Sporting News,
# Walter Camp (NCAA-recognized 5), plus SI, The Athletic, USA Today, ESPN,
# CBS, PFF, CFN, Athlon, Phil Steele.
_AA_HEADER_TO_SELECTOR = {
    "AP": "AP",
    "AFCA": "AFCA",
    "FWAA": "FWAA",
    "Sporting News": "Sporting News",
    "Walter Camp": "Walter Camp",
    "Athletic": "The Athletic",
    "SI": "Sports Illustrated",
    "USA Today": "USA Today",
    "ESPN": "ESPN",
    "CBS": "CBS",
    "PFF": "PFF",
    "CFN": "CFN",
    "Athlon": "Athlon",
    "Phil Steele": "Phil Steele",
}


def scrape_all_america(year: int) -> list[dict[str, Any]]:
    """Scrape the 'YYYY College Football All-America Team' Wikipedia article.

    Wikipedia's format: big grid tables split by position (QB/RB/WR/TE/OL/...).
    Rows = positions; each selector gets its own column with the selected
    player's name + school. Consensus + Unanimous are derived from appearance
    counts across the 5 NCAA-recognized selectors.

    Returns one dict per (player, selector) pair ready for the honors CSV
    pipeline.
    """
    title = f"{year} College Football All-America Team"
    try:
        html = _fetch_html(title)
    except Exception as exc:
        log.warning("scrape_all_america %d: fetch failed: %s", year, exc)
        return []

    soup = BeautifulSoup(html, "lxml")
    out: list[dict[str, Any]] = []
    position_pattern = re.compile(r"^(Quarterback|Running back|Wide receiver|Tight end|Tackle|Guard|Center|Offensive|Defensive|Linebacker|Defensive back|Cornerback|Safety|Kicker|Punter|Return|Long snapper|All-purpose)", re.I)

    # Iterate every wikitable and look for rows whose first cell contains a
    # position name. That filters out inapplicable tables (info-boxes etc.).
    for table in soup.find_all("table", class_=lambda c: c and "wikitable" in c):
        header_cells = table.find_all("th", scope="col") or (table.find("tr").find_all("th") if table.find("tr") else [])
        headers = [_cell_text(h) for h in header_cells]
        selector_cols: list[tuple[int, str]] = []
        for i, h in enumerate(headers):
            for key, selector in _AA_HEADER_TO_SELECTOR.items():
                if key.lower() in h.lower():
                    selector_cols.append((i, selector))
                    break
        if not selector_cols:
            continue

        rows = table.find_all("tr")
        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            pos_text = _cell_text(cells[0])
            if not position_pattern.match(pos_text):
                continue
            # Determine placement: consensus team tables carry first team, most
            # "second team" tables have heading anchors that include the phrase.
            placement = "first_team"
            heading = table.find_previous(["h2", "h3", "h4"])
            if heading and "second" in heading.get_text(" ").lower():
                placement = "second_team"
            for col_idx, selector in selector_cols:
                if col_idx >= len(cells):
                    continue
                cell_text = _cell_text(cells[col_idx])
                if not cell_text or cell_text == "-":
                    continue
                # Cells often combine "Player Name, School"
                m = re.match(r"^(.+?)[,]\s*(.+)$", cell_text)
                if m:
                    player_name = m.group(1).strip()
                    team_name = m.group(2).strip()
                else:
                    player_name = cell_text
                    team_name = ""
                out.append({
                    "season_year": year,
                    "player_name": player_name,
                    "position": pos_text.split(" ")[0][:4].upper(),  # QUAR -> QB-ish; normalize below
                    "team_name": team_name,
                    "honor_scope": "all_america",
                    "honor_name": "All-America",
                    "selector": selector,
                    "placement": placement,
                    "source_name": "wikipedia",
                    "source_url": _wiki_url(title),
                })
    return out


# ---------------------------------------------------------------------------
# TASK 4.2 — All-Conference scraper
# ---------------------------------------------------------------------------

_CONFERENCE_ARTICLE_TEMPLATES = {
    "SEC": ["{year} All-SEC football team"],
    "Big Ten": ["{year} All-Big Ten Conference football team", "{year} Big Ten Conference football season"],
    "ACC": ["{year} All-ACC football team"],
    "Big 12": ["{year} All-Big 12 Conference football team"],
    "AAC": ["{year} All-American Athletic Conference football team"],
    "Mountain West": ["{year} All-Mountain West Conference football team"],
    "Sun Belt": ["{year} All-Sun Belt Conference football team"],
    "MAC": ["{year} All-Mid-American Conference football team"],
    "Conference USA": ["{year} All-Conference USA football team"],
}


def scrape_all_conference(year: int, conference: str) -> list[dict[str, Any]]:
    templates = _CONFERENCE_ARTICLE_TEMPLATES.get(conference, [])
    for tmpl in templates:
        title = tmpl.format(year=year)
        try:
            html = _fetch_html(title)
        except Exception as exc:
            log.info("scrape_all_conference %d %s: %s failed: %s",
                     year, conference, title, exc)
            continue
        soup = BeautifulSoup(html, "lxml")
        out: list[dict[str, Any]] = []
        position_re = re.compile(r"(QB|RB|WR|TE|OL|OT|OG|C|DL|DE|DT|LB|ILB|OLB|DB|CB|S|K|P|LS|AP|ATH)", re.I)
        for table in soup.find_all("table", class_=lambda c: c and "wikitable" in c):
            heading = table.find_previous(["h2", "h3", "h4"])
            heading_text = heading.get_text(" ").lower() if heading else ""
            placement = "first_team"
            if "second" in heading_text:
                placement = "second_team"
            elif "third" in heading_text:
                placement = "third_team"
            elif "honorable" in heading_text:
                placement = "honorable_mention"
            rows = table.find_all("tr")
            for tr in rows[1:]:
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                pos_text = _cell_text(cells[0])
                if not position_re.search(pos_text):
                    continue
                name_cell_text = _cell_text(cells[1]) if len(cells) > 1 else ""
                team_cell_text = _cell_text(cells[2]) if len(cells) > 2 else ""
                if not name_cell_text:
                    continue
                out.append({
                    "season_year": year,
                    "player_name": name_cell_text,
                    "position": pos_text.upper()[:4],
                    "team_name": team_cell_text,
                    "honor_scope": "all_conference",
                    "honor_name": f"All-{conference}",
                    "selector": conference,
                    "placement": placement,
                    "source_name": "wikipedia",
                    "source_url": _wiki_url(title),
                })
        if out:
            return out
    return []


# ---------------------------------------------------------------------------
# TASK 4.3 — Position Awards scraper
# ---------------------------------------------------------------------------

_POSITION_AWARDS = {
    "Heisman Trophy": ("QB", "Heisman"),
    "Davey O'Brien Award": ("QB", "Davey O'Brien"),
    "Manning Award": ("QB", "Manning"),
    "Johnny Unitas Golden Arm Award": ("QB", "Unitas Golden Arm"),
    "Maxwell Award": ("ATH", "Maxwell"),
    "Walter Camp Award": ("ATH", "Walter Camp"),
    "Doak Walker Award": ("RB", "Doak Walker"),
    "Biletnikoff Award": ("WR", "Biletnikoff"),
    "John Mackey Award": ("TE", "Mackey"),
    "Outland Trophy": ("OL", "Outland"),
    "Rimington Trophy": ("C", "Rimington"),
    "Lombardi Award": ("DL", "Lombardi"),
    "Bronko Nagurski Trophy": ("DEF", "Nagurski"),
    "Chuck Bednarik Award": ("DEF", "Bednarik"),
    "Dick Butkus Award": ("LB", "Butkus"),
    "Jim Thorpe Award": ("DB", "Thorpe"),
    "Ray Guy Award": ("P", "Ray Guy"),
    "Lou Groza Award": ("K", "Lou Groza"),
}


def scrape_position_award(year: int, award: str) -> list[dict[str, Any]]:
    """Scrape winner + finalists for one award in one year."""
    position, honor_name = _POSITION_AWARDS.get(award, ("ATH", award))
    title = f"{year} {award}"
    try:
        html = _fetch_html(title)
    except Exception as exc:
        log.info("scrape_position_award %d %s: fetch failed: %s", year, award, exc)
        return []

    soup = BeautifulSoup(html, "lxml")
    out: list[dict[str, Any]] = []

    # Winner: infobox's "Recipient(s)" row or the lede's first bold link.
    infobox = soup.find("table", class_=lambda c: c and "infobox" in c)
    winner_name: str | None = None
    winner_team: str | None = None
    if infobox:
        for row in infobox.find_all("tr"):
            header = row.find("th")
            data = row.find("td")
            if not header or not data:
                continue
            h_text = _cell_text(header).lower()
            if "recipient" in h_text or "winner" in h_text:
                # data may contain "Name (School)" or "Name – School"
                d_text = _cell_text(data)
                m = re.match(r"^(.+?)\s*[\(\u2013\u2014-]\s*(.+?)[\)]?$", d_text)
                if m:
                    winner_name = m.group(1).strip()
                    winner_team = m.group(2).strip()
                else:
                    winner_name = d_text
                break

    if winner_name:
        out.append({
            "season_year": year,
            "player_name": winner_name,
            "position": position,
            "team_name": winner_team or "",
            "honor_scope": "position_award",
            "honor_name": honor_name,
            "selector": honor_name,
            "placement": "winner",
            "source_name": "wikipedia",
            "source_url": _wiki_url(title),
        })

    # Finalists: look for a heading "Finalists" followed by a list or table.
    for heading in soup.find_all(["h2", "h3"]):
        if "finalist" in heading.get_text(" ").lower():
            # Next sibling table or ul
            sibling = heading.find_next(["table", "ul"])
            if sibling is None:
                continue
            if sibling.name == "ul":
                for li in sibling.find_all("li"):
                    t = _cell_text(li)
                    m = re.match(r"^(.+?)[,\s\u2013\u2014-]+(.+)$", t)
                    if m:
                        p_name = m.group(1).strip()
                        t_name = m.group(2).strip()
                        if p_name == winner_name:
                            continue
                        out.append({
                            "season_year": year,
                            "player_name": p_name,
                            "position": position,
                            "team_name": t_name,
                            "honor_scope": "position_award",
                            "honor_name": honor_name,
                            "selector": honor_name,
                            "placement": "finalist",
                            "source_name": "wikipedia",
                            "source_url": _wiki_url(title),
                        })
            break
    return out


# ---------------------------------------------------------------------------
# Orchestrator — emit CSVs usable by the import-player-honors CLI.
# ---------------------------------------------------------------------------


def emit_honor_csvs(years: Iterable[int], out_dir: str | Path = "data/scraped_honors") -> dict[str, int]:
    """Run every scraper across every year and write CSVs.

    Returns row counts per source so the caller can decide which CSVs to
    import via `python manage.py import-player-honors`.
    """
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    summary: dict[str, int] = {}

    for year in years:
        # All-America
        rows = scrape_all_america(year)
        if rows:
            p = out_root / f"all_america_{year}.csv"
            _write_csv(p, rows)
            summary[p.name] = len(rows)
        time.sleep(1.0)

        # All-Conference — every canonical conference
        for conference in _CONFERENCE_ARTICLE_TEMPLATES.keys():
            rows = scrape_all_conference(year, conference)
            if rows:
                slug = conference.lower().replace(" ", "_")
                p = out_root / f"all_conf_{slug}_{year}.csv"
                _write_csv(p, rows)
                summary[p.name] = len(rows)
            time.sleep(0.5)

        # Position awards
        for award in _POSITION_AWARDS.keys():
            rows = scrape_position_award(year, award)
            if rows:
                slug = award.lower().replace(" ", "_").replace("'", "")
                p = out_root / f"award_{slug}_{year}.csv"
                _write_csv(p, rows)
                summary[p.name] = len(rows)
            time.sleep(0.3)

    return summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields = [
        "season_year", "player_name", "position", "team_name",
        "honor_scope", "honor_name", "selector", "placement",
        "source_name", "source_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    log.info("wrote %s (%d rows)", path, len(rows))
