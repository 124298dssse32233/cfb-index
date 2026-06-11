"""On3 NIL valuation scraper.

On3 renders their NIL rankings in a JS-heavy page.  We try two paths:
  1. Embedded __NEXT_DATA__ JSON (fast, zero parsing)
  2. HTML table/div parsing (fragile but works if SSR is active)

If neither yields results the function returns [] and logs a warning —
callers should fall back to ``import-nil-valuations --csv`` for manual data.

Public entry point:
    scrape_on3_nil(limit=200) -> list[dict]

Each dict has keys:
    rank, player_name, position, team_name, valuation_usd, whisper_usd,
    source_name="on3", source_url
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from typing import Any

log = logging.getLogger(__name__)

_ON3_CFB_URL = "https://www.on3.com/nil/rankings/player/college/football/"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_dollar(text: str) -> int | None:
    """'$3.2M' → 3_200_000, '$450K' → 450_000, '$1,200,000' → 1_200_000."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.KkMm]", "", text.strip())
    if not cleaned:
        return None
    try:
        if cleaned.upper().endswith("M"):
            return int(float(cleaned[:-1]) * 1_000_000)
        if cleaned.upper().endswith("K"):
            return int(float(cleaned[:-1]) * 1_000)
        return int(float(cleaned.replace(",", "")))
    except (ValueError, OverflowError):
        return None


def _extract_next_data(html: str) -> list[dict[str, Any]]:
    """Pull player NIL data from the embedded __NEXT_DATA__ JSON blob.

    On3's CFB NIL page embeds data at:
        props.pageProps.nilRankings.list
    Each entry: { person: { name, positionAbbreviation, status: { committedOrganizationSlug } },
                  valuation: { rank, valuation, whisper } }
    """
    m = re.search(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    props = data.get("props", {}).get("pageProps", {})

    # Primary path: nilRankings.list
    nil_rankings = props.get("nilRankings", {})
    entries = nil_rankings.get("list") if isinstance(nil_rankings, dict) else None

    if not entries:
        # Generic fallback: hunt for any list with valuation + person keys
        def _find_list(obj: Any, depth: int = 0) -> list | None:
            if depth > 5:
                return None
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                if "valuation" in obj[0] and "person" in obj[0]:
                    return obj
            if isinstance(obj, dict):
                for v in obj.values():
                    result = _find_list(v, depth + 1)
                    if result:
                        return result
            return None
        entries = _find_list(props)

    if not entries:
        return []

    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        person = entry.get("person") or {}
        valuation = entry.get("valuation") or {}

        name = str(person.get("name") or "").strip()
        if not name:
            continue

        position = str(person.get("positionAbbreviation") or "").upper().strip()

        # School from committedOrganizationSlug e.g. "texas-longhorns"
        status = person.get("status") or {}
        school_slug = str(status.get("committedOrganizationSlug") or "")
        # Convert slug → readable name: "texas-longhorns" → "Texas Longhorns"
        school = school_slug.replace("-", " ").title() if school_slug else ""

        rank = valuation.get("rank")
        val = valuation.get("valuation")
        whisper = valuation.get("whisper")

        out.append({
            "rank": int(rank) if rank is not None else None,
            "player_name": name,
            "position": position,
            "team_name": school,
            "valuation_usd": int(val) if val is not None else None,
            "whisper_usd": int(whisper) if whisper is not None else None,
            "source_name": "on3",
            "source_url": _ON3_CFB_URL,
        })
    return out


def _extract_html_rows(html: str) -> list[dict[str, Any]]:
    """Fallback: parse visible HTML if __NEXT_DATA__ was empty.

    On3's ranking page uses a mix of divs; we look for any pattern that
    contains a dollar amount next to a name and a school.  Heuristic and
    intentionally lenient.
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        log.warning("on3_nil: beautifulsoup4 not available for HTML fallback")
        return []

    soup = BeautifulSoup(html, "lxml")
    out: list[dict[str, Any]] = []

    # Look for table rows first (some pages render a <table>)
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 5:
            continue
        header = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        rank_col = next((i for i, h in enumerate(header) if h in ("rank", "#", "rk")), None)
        name_col = next((i for i, h in enumerate(header) if "name" in h or "player" in h), None)
        pos_col = next((i for i, h in enumerate(header) if h in ("pos", "position")), None)
        school_col = next((i for i, h in enumerate(header) if "school" in h or "team" in h), None)
        nil_col = next((i for i, h in enumerate(header) if "nil" in h or "value" in h or "valuation" in h), None)

        if name_col is None or nil_col is None:
            continue

        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            name = cells[name_col].get_text(strip=True) if name_col < len(cells) else ""
            if not name:
                continue
            rank = None
            if rank_col is not None and rank_col < len(cells):
                try:
                    rank = int(cells[rank_col].get_text(strip=True))
                except ValueError:
                    pass
            position = cells[pos_col].get_text(strip=True) if pos_col is not None and pos_col < len(cells) else ""
            school = cells[school_col].get_text(strip=True) if school_col is not None and school_col < len(cells) else ""
            nil_text = cells[nil_col].get_text(strip=True)
            val = _parse_dollar(nil_text)
            if val is None:
                continue
            out.append({
                "rank": rank,
                "player_name": name,
                "position": position.upper().strip(),
                "team_name": school,
                "valuation_usd": val,
                "whisper_usd": None,
                "source_name": "on3",
                "source_url": _ON3_CFB_URL,
            })
        if out:
            return out

    # Div-based fallback: find elements containing dollar amounts
    dollar_pattern = re.compile(r"\$[\d,.]+[KkMm]?")
    candidates = soup.find_all(string=dollar_pattern)
    rank_counter = 0
    for node in candidates[:300]:
        parent = node.parent
        if parent is None:
            continue
        # Walk up to find a container with a name
        container = parent
        for _ in range(6):
            if container is None:
                break
            text = container.get_text(" ", strip=True)
            # Heuristic: container must have a realistic name-like prefix
            parts = text.split()
            if len(parts) >= 3 and not parts[0].startswith("$"):
                nil_match = dollar_pattern.search(text)
                if nil_match:
                    rank_counter += 1
                    out.append({
                        "rank": rank_counter,
                        "player_name": " ".join(parts[:2]),
                        "position": "",
                        "team_name": "",
                        "valuation_usd": _parse_dollar(nil_match.group()),
                        "whisper_usd": None,
                        "source_name": "on3",
                        "source_url": _ON3_CFB_URL,
                    })
                    break
            container = container.parent

    return out


def scrape_on3_nil(limit: int = 200) -> list[dict[str, Any]]:
    """Fetch On3's college football NIL rankings.

    Returns a list of dicts (rank, player_name, position, team_name,
    valuation_usd, whisper_usd, source_name, source_url).

    Returns [] if the page is not parseable — caller should fall back to
    CSV import via ``import-nil-valuations --csv``.
    """
    log.info("on3_nil: fetching %s", _ON3_CFB_URL)
    try:
        html = _fetch_html(_ON3_CFB_URL)
    except Exception as exc:
        log.warning("on3_nil: fetch failed: %s", exc)
        return []

    rows = _extract_next_data(html)
    if rows:
        log.info("on3_nil: extracted %d rows via __NEXT_DATA__", len(rows))
    else:
        log.info("on3_nil: __NEXT_DATA__ empty, falling back to HTML parsing")
        rows = _extract_html_rows(html)
        if rows:
            log.info("on3_nil: extracted %d rows via HTML parse", len(rows))
        else:
            log.warning(
                "on3_nil: no data extracted — page is likely fully JS-rendered. "
                "Use: python manage.py import-nil-valuations --csv <file.csv>"
            )
            return []

    rows = [r for r in rows if r.get("player_name") and r.get("valuation_usd")]
    rows.sort(key=lambda r: r.get("rank") or 9999)
    return rows[:limit]


def save_nil_valuations(
    db: Any,
    rows: list[dict[str, Any]],
    as_of_date: str,
    scraped_at: str,
) -> dict[str, int]:
    """Resolve player names and upsert rows into player_nil_valuations.

    Returns {"inserted": N, "skipped": N} where skipped = name not in DB.
    """
    inserted = skipped = 0
    for row in rows:
        name = (row.get("player_name") or "").strip()
        if not name:
            skipped += 1
            continue
        matched = db.query_one(
            "select player_id from players where lower(full_name) = lower(:name) order by player_id asc limit 1",
            {"name": name},
        )
        if matched is None:
            log.debug("on3_nil: no player match for %r", name)
            skipped += 1
            continue
        player_id = int(matched["player_id"])
        db.execute(
            """
            INSERT INTO player_nil_valuations
                (player_id, as_of_date, rank, valuation_usd, whisper_usd,
                 source_name, source_url, scraped_at)
            VALUES
                (:player_id, :as_of_date, :rank, :valuation_usd, :whisper_usd,
                 :source_name, :source_url, :scraped_at)
            ON CONFLICT (player_id, as_of_date, source_name) DO UPDATE SET
                rank          = excluded.rank,
                valuation_usd = excluded.valuation_usd,
                whisper_usd   = excluded.whisper_usd,
                source_url    = excluded.source_url,
                scraped_at    = excluded.scraped_at
            """,
            {
                "player_id": player_id,
                "as_of_date": as_of_date,
                "rank": row.get("rank"),
                "valuation_usd": row.get("valuation_usd"),
                "whisper_usd": row.get("whisper_usd"),
                "source_name": row.get("source_name") or "on3",
                "source_url": row.get("source_url") or _ON3_CFB_URL,
                "scraped_at": scraped_at,
            },
        )
        inserted += 1
    return {"inserted": inserted, "skipped": skipped}
