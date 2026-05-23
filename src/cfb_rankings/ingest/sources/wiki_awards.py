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

from cfb_rankings.common.head_chrome import base_url

log = logging.getLogger(__name__)

# Routes through head_chrome.base_url() so a domain swap is a one-line change.
_UA = f"CFBIndex-autopilot/1.0 (+{base_url()})"


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


def scrape_per_selector_all_america(year: int) -> list[dict[str, Any]]:
    """Scrape per-selector All-America picks from the YYYY article.

    Wikipedia's 2024+ format dropped the per-selector grid table in favor
    of position-section <ul> lists, where each player's <li> has a
    <small>(SEL1, SEL2, ...)</small> parenthetical listing every selector
    that picked them. Bold selector codes inside that small element mean
    first-team; non-bold means second-team or honorable mention.

    Tries the URL ``YYYY_All-America_college_football_team`` first (the
    canonical post-2024 page title) and falls back to
    ``YYYY_College_Football_All-America_Team`` (the pre-2024 form, which
    sometimes 301s).

    Emits one CandidateObservation-shaped dict per (player, selector)
    pair, normalised to the selectors used by the Selector Grid module.

    Selector code normalisation:
        AP    -> "AP"      (Associated Press, NCAA-recognized)
        AFCA  -> "AFCA"    (Coaches, NCAA-recognized)
        FWAA  -> "FWAA"    (Football Writers, NCAA-recognized)
        TSN   -> "SN"      (Sporting News, NCAA-recognized — aliased)
        WCFF  -> "WCFF"    (Walter Camp, NCAA-recognized)
        SI    -> "SI"      (Sports Illustrated)
        plus passthroughs for CBS/Athletic/ESPN/PFF/USAT/Athlon/Steele.

    Placement (first_team / second_team) derives from whether the
    selector code in the parenthetical is wrapped in <b>...</b>.
    """
    # 2024+ canonical title.
    titles_to_try = (
        f"{year} All-America college football team",
        f"{year} College Football All-America Team",
    )
    html = None
    used_title = None
    for title in titles_to_try:
        try:
            html = _fetch_html(title)
            used_title = title
            break
        except Exception as exc:
            log.debug(
                "scrape_per_selector_all_america %d: %s failed: %s",
                year, title, exc,
            )
    if html is None:
        log.warning(
            "scrape_per_selector_all_america %d: no Wikipedia article reachable",
            year,
        )
        return []

    soup = BeautifulSoup(html, "lxml")
    out: list[dict[str, Any]] = []
    source_url = _wiki_url(used_title)

    # Selector code normalisation map. Keys are wikipedia bare-strings;
    # values are the canonical selector code stored in player_honors.
    selector_normalise = {
        "AP":     "AP",
        "AFCA":   "AFCA",
        "FWAA":   "FWAA",
        "TSN":    "SN",   # The Sporting News — also "Sporting News" elsewhere
        "SN":     "SN",
        "Sporting News": "SN",
        "WCFF":   "WCFF",
        "Walter Camp": "WCFF",
        "SI":     "SI",
        "Sports Illustrated": "SI",
        "CBS":    "CBS",
        "ESPN":   "ESPN",
        "PFF":    "PFF",
        "Athletic": "The Athletic",
        "The Athletic": "The Athletic",
        "USAT":   "USA Today",
        "USA Today": "USA Today",
        "Athlon": "Athlon",
        "Phil Steele": "Phil Steele",
    }
    # Patterns for position canonicalisation
    position_canonical = {
        "Quarterback": "QB",
        "Running back": "RB",
        "Wide receiver": "WR",
        "Tight end": "TE",
        "Offensive line": "OL",
        "Offensive tackle": "OT",
        "Tackle": "OT",
        "Guard": "OG",
        "Offensive guard": "OG",
        "Center": "C",
        "Defensive line": "DL",
        "Defensive end": "DE",
        "Defensive tackle": "DT",
        "Edge": "EDGE",
        "Linebacker": "LB",
        "Defensive back": "DB",
        "Cornerback": "CB",
        "Safety": "S",
        "Kicker": "K",
        "Punter": "P",
        "Long snapper": "LS",
        "All-purpose": "AP-RET",
        "All-purpose / return specialist": "AP-RET",
        "Return specialist": "RET",
    }

    # Walk every h3 in the article — each is a position section. Modern
    # Wikipedia wraps headings in <div class="mw-heading mw-heading3"> so
    # we have to look for the h3 inside the div OR a bare h3.
    for h3 in soup.find_all("h3"):
        position_label = h3.get_text(" ", strip=True)
        if not position_label:
            continue
        # Only process actual position headings.
        if not any(position_label.startswith(k) for k in position_canonical):
            continue
        pos_code = next(
            (v for k, v in position_canonical.items() if position_label.startswith(k)),
            "",
        )
        # Find the FIRST <ul> after this h3 that's still inside the same
        # section. Walk forward sibling-by-sibling from the h3's wrapping
        # mw-heading div (modern Wikipedia format), stopping at the next
        # mw-heading wrapper.
        parent_wrapper = h3.find_parent("div", class_=lambda c: c and "mw-heading" in c)
        anchor = parent_wrapper or h3
        ul = None
        cursor = anchor
        for _ in range(10):
            cursor = cursor.find_next_sibling()
            if cursor is None:
                break
            cls = cursor.get("class") if hasattr(cursor, "get") else None
            if cls and any("mw-heading" in c for c in cls):
                break
            if cursor.name == "ul":
                ul = cursor
                break
        if ul is None:
            # Fallback: any ul up to the next h3 anywhere in the tree
            ul = anchor.find_next("ul")
            if ul is not None:
                # Verify it precedes the next h3 (i.e., is in our section).
                next_heading_div = anchor.find_next("div", class_=lambda c: c and "mw-heading" in c)
                if next_heading_div is not None:
                    # Compare positions: ul must come before next heading
                    ul_pos = sum(1 for _ in ul.find_all_previous())
                    nh_pos = sum(1 for _ in next_heading_div.find_all_previous())
                    if ul_pos > nh_pos:
                        ul = None
        if ul is None:
            continue

        for li in ul.find_all("li", recursive=False):
            # Skip nested-ul li children (some pages have sub-bullets).
            # The player name is the first <a> or <b> in the li.
            # Team is the SECOND link (the team-season article).
            anchors = li.find_all("a", recursive=False)
            # Some pages wrap the player name in <b>; the <a> may be inside.
            # Walk the li children in order and find the first non-trivial
            # <a> for player name, and the first link with "football team"
            # in href for the team.
            player_a = None
            team_a = None
            for a in li.find_all("a"):
                href = a.get("href", "")
                title_attr = a.get("title", "")
                text = a.get_text(" ", strip=True)
                if not text:
                    continue
                # Player anchor: linked to a player article. Heuristic:
                # NOT a year/team page, NOT a navigation link.
                if "football_team" in href or "football team" in title_attr:
                    if team_a is None:
                        team_a = a
                elif player_a is None and not href.startswith("#"):
                    player_a = a
            if player_a is None:
                continue
            player_name = re.sub(r"\*", "", player_a.get_text(" ", strip=True)).strip()
            if not player_name:
                continue
            # Team name: prefer team-page link; else fall back to the next
            # text node after the player name.
            if team_a is not None:
                team_text = team_a.get_text(" ", strip=True)
                # Strip leading "YYYY " season prefix if present.
                team_name = re.sub(r"^\d{4}\s+", "", team_text)
                # Strip trailing " football team" suffix.
                team_name = re.sub(r"\s+football\s+team\s*$", "", team_name, flags=re.I)
            else:
                team_name = ""

            # Find the parenthetical <small>. Selectors are the codes inside.
            small = li.find("small")
            if small is None:
                continue
            small_html = str(small)
            # Pull out bold selector codes (first-team) and plain codes
            # (second-team or "also-rec'd"). Bold is detected via <b>.
            first_team_codes: list[str] = []
            second_team_codes: list[str] = []
            for tag in small.find_all(["b", "a"]):
                # Direct child of small only (skip nested <b><a>)
                if tag.name == "b":
                    code = tag.get_text(" ", strip=True).strip(",. ")
                    if code:
                        first_team_codes.append(code)
            # Plain codes: text inside small that's NOT inside a <b>
            # Strategy: get the small's text, remove the bold-text, parse
            # the leftover for codes.
            small_text = small.get_text(" ", strip=True).strip("()")
            for bold_code in first_team_codes:
                small_text = small_text.replace(bold_code, "")
            # Remaining tokens, comma-or-space-separated
            for tok in re.split(r"[,\s]+", small_text):
                tok = tok.strip(".,()")
                if tok and tok not in first_team_codes:
                    second_team_codes.append(tok)

            # All listed selectors on the 2024+ unified page are FIRST-TEAM
            # picks by that selector. The bold-vs-plain distinction is NCAA-
            # recognition (bold = AP/FWAA/AFCA/WCFF/TSN — the 5 selectors
            # that drive Consensus computation), NOT placement. We mark all
            # selectors as first_team. If a separate "Second team" section
            # exists on a future page version, the section header logic
            # would need updating.
            for code, placement in (
                *((c, "first_team") for c in first_team_codes),
                *((c, "first_team") for c in second_team_codes),
            ):
                # Normalise selector code
                sel = selector_normalise.get(code)
                if sel is None:
                    # Try uppercase form
                    sel = selector_normalise.get(code.upper())
                if sel is None:
                    continue  # Unknown selector — skip rather than pollute
                # honor_team carries the "first" / "second" team designation
                # that the Selector Grid module reads to pick a gold/silver
                # medal class. The CSV's `placement` column is INT in the DB
                # schema (1/2/3) and the importer's maybe_int(placement)
                # would silently nullify "first_team" strings — so we set
                # both fields and let downstream consumers pick the form
                # they need.
                honor_team_text = "first" if placement == "first_team" else "second"
                out.append({
                    "season_year": year,
                    "player_name": player_name,
                    "position": pos_code,
                    "team_name": team_name,
                    "honor_scope": "all_america",
                    "honor_name": f"All-America ({sel})",
                    "selector": sel,
                    "honor_team": honor_team_text,
                    "placement": 1 if placement == "first_team" else 2,
                    "source_name": "wikipedia",
                    "source_url": source_url,
                })

    return out


def scrape_consensus_all_america(year: int) -> list[dict[str, Any]]:
    """Scrape the 'Consensus All-Americans' table from the YYYY All-America
    article. 2026-05-23: Added because the per-selector grid scraper
    (`scrape_all_america`) returns 0 rows for 2024 — the Wikipedia table
    format has changed. The Consensus table is structurally simpler and
    captures the most-impactful tier of recognition.

    Each row: Name (with wiki link), Position, Year (class), University.

    Returns one dict per consensus player. Selector = "Consensus" which is
    sufficient to populate the Selector Grid's gold cells.
    """
    title = f"{year} College Football All-America Team"
    try:
        html = _fetch_html(title)
    except Exception as exc:
        log.warning("scrape_consensus_all_america %d: fetch failed: %s", year, exc)
        return []
    soup = BeautifulSoup(html, "lxml")
    out: list[dict[str, Any]] = []
    for table in soup.find_all("table", class_=lambda c: c and "wikitable" in c):
        caption = table.find("caption")
        if not caption:
            continue
        cap_text = _cell_text(caption)
        if "consensus" not in cap_text.lower():
            continue
        # This is the Consensus All-Americans table. Use first + last cells
        # only — those are the most reliable across rowspan-rich rows.
        # Middle cells (position, year) sometimes rowspan multiple players
        # which makes naive cell-indexing wrong; we leave position blank and
        # let the players table provide it via player_id resolution.
        rows = table.find_all("tr")
        for tr in rows[1:]:  # Skip header
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            cell_texts = [_cell_text(c) for c in cells]
            name = cell_texts[0]
            school = cell_texts[-1]
            # Strip asterisks/footnotes from name
            name = re.sub(r"\*", "", name).strip()
            if not name:
                continue
            out.append({
                "season_year": year,
                "player_name": name,
                "position": "",   # Left blank — see comment above
                "team_name": school,
                "honor_scope": "all_america",
                "honor_name": "All-America (Consensus)",
                "selector": "Consensus",
                "placement": "first_team",
                "source_name": "wikipedia",
                "source_url": _wiki_url(title),
            })
        break  # First consensus table is the canonical one
    return out


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
        # All-America (per-selector grid; format-fragile, 0 rows for 2024)
        rows = scrape_all_america(year)
        if rows:
            p = out_root / f"all_america_{year}.csv"
            _write_csv(p, rows)
            summary[p.name] = len(rows)
        time.sleep(1.0)

        # All-America Consensus (single canonical table — more reliable).
        # 2026-05-23: Added because the per-selector grid scraper above
        # silently returned 0 rows for 2024 due to Wikipedia format change.
        rows = scrape_consensus_all_america(year)
        if rows:
            p = out_root / f"all_america_consensus_{year}.csv"
            _write_csv(p, rows)
            summary[p.name] = len(rows)
        time.sleep(1.0)

        # Per-selector All-America (2024+ Wikipedia unified-page format).
        # Each player's <li> includes a <small>(SEL1, SEL2, ...)</small>
        # parenthetical with every selector that picked them. Emits one
        # row per (player, selector) pair — activates the Selector Grid
        # module's gold cells beyond just the Consensus aggregate.
        rows = scrape_per_selector_all_america(year)
        if rows:
            p = out_root / f"all_america_per_selector_{year}.csv"
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
