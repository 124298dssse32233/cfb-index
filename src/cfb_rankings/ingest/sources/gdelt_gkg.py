"""GDELT GKG v2 bulk news-volume adapter — credential-free HTTP path.

Downloads raw GKG ZIP files from the public GDELT masterfilelist over plain
HTTP (no API key, no GCP account). Counts daily article mentions per CFB team
by substring-matching team aliases against the V2Organizations column.

This is the middle tier in the auto-routing chain:
  Tier 1 (best)   — BigQuery (gdelt_volume_bq.py, needs GOOGLE_APPLICATION_CREDENTIALS)
  Tier 2 (this)   — HTTP GKG bulk files (this module, zero credentials required)
  Tier 3 (legacy) — Per-team DOC 2.0 rotation (gdelt_volume.py, slow, rate-limited)

run_adapter.py routes ``gdelt_volume`` here when BQ credentials are absent.

GKG 2.0 column layout (0-indexed, tab-delimited, 27 fields total):
  0   GKGRECORDID
  1   DATE (15-min window timestamp, YYYYMMDDHHMMSS)
  2   SourceCollectionIdentifier
  3   SourceCommonName
  4   DocumentIdentifier
  5   Counts
  6   V2Counts
  7   Themes
  8   V2Themes
  9   Locations
  10  V2Locations
  11  Persons
  12  V2Persons
  13  Organizations
  14  V2Organizations  ← team matching column (NOT col 10 or 11 as in GKG 1.0)
  15  V2Tone
  ...  (27 total)

V2Organizations format: semicolon-separated "NAME,COUNT" pairs, where NAME is
the org name (already lowercased in many records but we lowercase again) and
COUNT is the number of mentions in the article.

Alias matching reuses the team_aliases table (seeded by seed-team-aliases),
same data surface used by the BQ adapter. Each alias is tested as a substring
of the lowercased org name for precision — exact substring, not tokenised.

Memory budget: each GKG ZIP is 30-80 MB text unzipped. We wrap the ZipFile
member in io.TextIOWrapper and process line-by-line, discarding as we go.
Peak memory per file ~5-10 MB (matched team dict only).

Time budget: ~96 files/day × ~2 s download+parse = ~3-4 min per daily run.
Set GDELT_BULK_MAX_FILES env var to cap (default 96 = full 24 h window).
Set GDELT_BULK_LOOKBACK_HOURS env var to override lookback (default 26 h).
"""
from __future__ import annotations

import csv
import io
import logging
import time
import zipfile
from datetime import datetime, timezone
from typing import Any

import requests

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

MASTERFILE_URL = "https://data.gdeltproject.org/gdeltv2/masterfilelist.txt"

# GKG 2.0 column index for V2Organizations (0-based, tab-delimited).
# IMPORTANT: GKG 1.0 used col 10 (Organizations) and col 11. GKG 2.0 has
# additional V2* columns that shift everything right. V2Organizations = col 14.
GKG_COL_ORGS = 14

# Minimum number of tab-delimited fields a valid GKG 2.0 row must have.
_GKG_MIN_COLS = 15  # need at least index 14

# Courtesy sleep between file downloads (seconds).
_INTER_FILE_SLEEP = 0.5

_USER_AGENT = "cfb-index-research/1.0 (academic, non-commercial)"


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def fetch_masterfile_lines(lookback_hours: int = 26) -> list[str]:
    """Download masterfilelist.txt and return GKG file URLs from the past ``lookback_hours``.

    masterfilelist.txt format (space-separated):
        <unix_timestamp> <file_size_bytes> <url>

    Entries are newest-first. We stop as soon as the timestamp falls outside
    the lookback window so we never have to read the full 10 MB+ file.
    Returns a list of URLs, oldest-first (reversed) so the caller processes
    them in chronological order.
    """
    cutoff = time.time() - lookback_hours * 3600
    max_files = _max_files_env()

    resp = requests.get(
        MASTERFILE_URL,
        headers={"User-Agent": _USER_AGENT},
        timeout=30,
        stream=True,
    )
    resp.raise_for_status()

    urls: list[str] = []
    for raw_line in resp.iter_lines(decode_unicode=True):
        line = (raw_line or "").strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        # masterfilelist.txt uses Unix epoch as the first field.
        try:
            ts = float(parts[0])
        except ValueError:
            continue
        if ts < cutoff:
            # Entries are newest-first; once we pass the cutoff we're done.
            break
        url = parts[2]
        if "gkg" not in url or not url.endswith(".zip"):
            continue
        urls.append(url)
        if max_files and len(urls) >= max_files:
            break

    # Reverse so caller processes oldest-first (chronological order).
    urls.reverse()
    logger.info(
        "gdelt_gkg: masterfilelist returned %d GKG file URLs (lookback=%dh, cap=%s)",
        len(urls), lookback_hours, max_files or "none",
    )
    return urls


def _max_files_env() -> int:
    """Read GDELT_BULK_MAX_FILES env var; default 96 (= 24 h of 15-min windows)."""
    import os
    raw = os.environ.get("GDELT_BULK_MAX_FILES", "").strip()
    if raw.isdigit():
        return int(raw)
    return 96


# ---------------------------------------------------------------------------
# Per-file streaming parse
# ---------------------------------------------------------------------------

def parse_gkg_stream(url: str, alias_map: dict[str, int]) -> dict[int, int]:
    """Download and parse one GKG .csv.zip, returning {team_id: mention_count_sum}.

    alias_map: {alias_lower: team_id} — all aliases from the team_aliases table.
    For each GKG record we check V2Organizations (col 14). The org name portion
    (before the comma in each semicolon-delimited pair) is tested against every
    alias as a substring match (case-insensitive). When a match is found we add
    the COUNT portion to the team's running total for this file.

    Encoding errors in foreign org names are replaced silently. Never logs raw
    GKG text (encoding safety).
    """
    counts: dict[int, int] = {}

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=60,
            stream=True,
        )
        if resp.status_code == 404:
            logger.debug("gdelt_gkg: 404 for %s (file still in progress?)", url)
            return counts
        resp.raise_for_status()

        raw_bytes = resp.content  # GKG ZIPs are small enough to buffer
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            members = zf.namelist()
            if not members:
                return counts
            with zf.open(members[0]) as zfp:
                text_stream = io.TextIOWrapper(zfp, encoding="utf-8", errors="replace")
                reader = csv.reader(text_stream, delimiter="\t")
                for row in reader:
                    if len(row) < _GKG_MIN_COLS:
                        continue
                    orgs_field = row[GKG_COL_ORGS]
                    if not orgs_field:
                        continue
                    _accumulate_org_mentions(orgs_field, alias_map, counts)
    except zipfile.BadZipFile:
        logger.warning("gdelt_gkg: bad ZIP from %s (truncated?)", url)
    except requests.RequestException as exc:
        logger.warning("gdelt_gkg: network error fetching %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("gdelt_gkg: unexpected error parsing %s: %s", url, type(exc).__name__)

    return counts


def _accumulate_org_mentions(
    orgs_field: str,
    alias_map: dict[str, int],
    counts: dict[int, int],
) -> None:
    """Parse the V2Organizations field and accumulate mention counts.

    V2Organizations format: "NAME,COUNT;NAME,COUNT;..."
    - Split on ";" to get each org entry.
    - Split each entry on "," — last token is the integer count; the rest is the name.
    - Lowercase the name and check if any alias is a substring of it.
    - Multiple aliases may match the same org (e.g. "ohio state buckeyes" matches
      both "ohio state" and "ohio state buckeyes"); we credit the first match only
      to avoid double-counting a single article.
    """
    already_credited: set[int] = set()
    for entry in orgs_field.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        comma_idx = entry.rfind(",")
        if comma_idx < 1:
            org_name = entry.lower()
            mention_n = 1
        else:
            org_name = entry[:comma_idx].lower()
            try:
                mention_n = int(entry[comma_idx + 1:])
            except ValueError:
                mention_n = 1

        for alias, team_id in alias_map.items():
            if team_id in already_credited:
                continue
            if alias in org_name:
                counts[team_id] = counts.get(team_id, 0) + mention_n
                already_credited.add(team_id)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def ingest_gdelt_news_volume(
    db: Database,
    *,
    date_str: str | None = None,
    lookback_hours: int = 26,
    commit: bool = False,
) -> dict[str, Any]:
    """Download today's GKG bulk files and count CFB team article mentions.

    Parameters
    ----------
    db:
        Open Database instance.
    date_str:
        ISO date string "YYYY-MM-DD" to tag rows with. Defaults to today UTC.
    lookback_hours:
        How far back in the masterfilelist to look (default 26 h covers full
        rolling-24-h window even with slight server lag).
    commit:
        If True, write results to ``team_news_volume`` and ``source_observations``.
        If False (dry-run), count and return stats without touching the DB.

    Returns
    -------
    dict with keys: teams_with_mentions, total_mentions, files_processed, date.
    """
    import os
    import hashlib

    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lookback_hours = int(
        os.environ.get("GDELT_BULK_LOOKBACK_HOURS", str(lookback_hours))
    )

    # --- 1. Build alias map from DB ----------------------------------------
    alias_rows = db.query_all(
        "SELECT ta.alias, t.team_id "
        "FROM team_aliases ta "
        "JOIN teams t ON t.team_id = ta.team_id "
        "WHERE ta.alias IS NOT NULL AND ta.alias != ''"
    )
    alias_map: dict[str, int] = {
        str(r["alias"]).lower(): int(r["team_id"])
        for r in alias_rows
        if r.get("alias") and r.get("team_id")
    }
    if not alias_map:
        logger.warning(
            "gdelt_gkg: team_aliases table is empty — no teams to match. "
            "Run: python manage.py seed-team-aliases --season <year>"
        )
        return {"teams_with_mentions": 0, "total_mentions": 0, "files_processed": 0, "date": date_str}

    logger.info("gdelt_gkg: loaded %d team aliases for %d unique teams",
                len(alias_map), len(set(alias_map.values())))

    # --- 2. Discover GKG file URLs ------------------------------------------
    try:
        urls = fetch_masterfile_lines(lookback_hours)
    except Exception as exc:  # noqa: BLE001
        logger.error("gdelt_gkg: failed to fetch masterfile: %s", exc)
        return {"teams_with_mentions": 0, "total_mentions": 0, "files_processed": 0, "date": date_str}

    if not urls:
        logger.info("gdelt_gkg: no GKG files found for lookback=%dh", lookback_hours)
        return {"teams_with_mentions": 0, "total_mentions": 0, "files_processed": 0, "date": date_str}

    # --- 3. Stream-parse each file, accumulating counts --------------------
    aggregate: dict[int, int] = {}  # {team_id: total_mention_count}
    files_processed = 0

    for i, url in enumerate(urls):
        try:
            file_counts = parse_gkg_stream(url, alias_map)
            for tid, cnt in file_counts.items():
                aggregate[tid] = aggregate.get(tid, 0) + cnt
            files_processed += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("gdelt_gkg: skipping %s due to error: %s", url, type(exc).__name__)
            continue

        # Courtesy sleep between files; skip after the last one.
        if i < len(urls) - 1:
            time.sleep(_INTER_FILE_SLEEP)

    teams_with_mentions = len(aggregate)
    total_mentions = sum(aggregate.values())
    logger.info(
        "gdelt_gkg: %d files processed; %d teams with mentions; %d total mentions (date=%s)",
        files_processed, teams_with_mentions, total_mentions, date_str,
    )

    if not commit:
        return {
            "teams_with_mentions": teams_with_mentions,
            "total_mentions": total_mentions,
            "files_processed": files_processed,
            "date": date_str,
        }

    # --- 4. Write to team_news_volume + source_observations ----------------
    computed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    obs_inserted = 0
    vol_inserted = 0

    for team_id, mention_count in aggregate.items():
        if mention_count <= 0:
            continue

        # team_news_volume upsert
        db.execute(
            """
            INSERT OR REPLACE INTO team_news_volume
                (team_id, date, mention_count, source, computed_at_utc)
            VALUES (?, ?, ?, 'gdelt_gkg', ?)
            """,
            (team_id, date_str, mention_count, computed_at),
        )
        vol_inserted += 1

        # source_observations insert (dedup by day)
        iso_ts = f"{date_str}T00:00:00Z"
        dedup_basis = f"gdelt_volume|{team_id}|article_count|{date_str}"
        dedup_key = _sha1(dedup_basis)
        existing = db.query_one(
            "SELECT source_observation_id FROM source_observations WHERE dedup_key = ?",
            (dedup_key,),
        )
        if not existing:
            db.execute(
                """
                INSERT INTO source_observations (
                    source_id, entity_type, entity_id, entity_label,
                    observed_at_utc, metric, value_numeric,
                    sample_window, source_tier, ingestion_adapter_version,
                    capture_url, dedup_key
                ) VALUES (
                    'gdelt_volume', 'team_query', ?, ?,
                    ?, 'article_count', ?,
                    '1d', 'A', 'gkg-bulk-1.0.0',
                    ?, ?
                )
                """,
                (
                    str(team_id),
                    f"team:{team_id}",
                    iso_ts,
                    float(mention_count),
                    MASTERFILE_URL,
                    dedup_key,
                ),
            )
            obs_inserted += 1

    logger.info(
        "gdelt_gkg: wrote %d team_news_volume rows, %d source_observations rows (date=%s)",
        vol_inserted, obs_inserted, date_str,
    )

    return {
        "teams_with_mentions": teams_with_mentions,
        "total_mentions": total_mentions,
        "files_processed": files_processed,
        "date": date_str,
    }


def _sha1(text: str) -> str:
    import hashlib
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# SourceAdapter wrapper (used by tools/run_adapter.py lifecycle)
# ---------------------------------------------------------------------------

class GdeltGkgBulkAdapter:
    """Minimal adapter shim so run_adapter.py can manage this source via the
    standard fetch/parse/write_rows/run lifecycle.

    Delegates all work to ``ingest_gdelt_news_volume`` so the logic stays in
    one testable function rather than being split across three methods.
    """

    source_id = "gdelt_volume"
    adapter_version = "gkg-bulk-1.0.0"

    def __init__(self, db: Database) -> None:
        self.db = db

    def run(self):
        """Execute ingest and return an AdapterRunResult-compatible object."""
        import dataclasses
        from cfb_rankings.ingest.sources.base import AdapterRunResult

        started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            result = ingest_gdelt_news_volume(self.db, commit=True)
            rows = result.get("teams_with_mentions", 0)
            status = "ok" if rows > 0 else "empty"
            ar = AdapterRunResult(
                source_id=self.source_id,
                status=status,
                rows_inserted=rows,
                adapter_version=self.adapter_version,
                run_started_at_utc=started,
                run_finished_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("gdelt_gkg adapter run failed")
            ar = AdapterRunResult(
                source_id=self.source_id,
                status="error",
                rows_inserted=0,
                error_message=f"{type(exc).__name__}: {exc}",
                adapter_version=self.adapter_version,
                run_started_at_utc=started,
                run_finished_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        # Write health beacon (mirrors SourceAdapter.health_check behaviour).
        run_date = (ar.run_started_at_utc or "")[:10]
        try:
            self.db.execute(
                """
                INSERT INTO scrape_health (
                    source_id, run_date, rows_inserted, status, error_message,
                    run_started_at_utc, run_finished_at_utc, adapter_version
                ) VALUES (
                    :source_id, :run_date, :rows_inserted, :status, :error_message,
                    :run_started_at_utc, :run_finished_at_utc, :adapter_version
                )
                ON CONFLICT (source_id, run_date) DO UPDATE SET
                    rows_inserted = excluded.rows_inserted,
                    status = excluded.status,
                    error_message = excluded.error_message,
                    run_started_at_utc = excluded.run_started_at_utc,
                    run_finished_at_utc = excluded.run_finished_at_utc,
                    adapter_version = excluded.adapter_version
                """,
                {
                    "source_id": ar.source_id,
                    "run_date": run_date,
                    "rows_inserted": ar.rows_inserted,
                    "status": ar.status,
                    "error_message": ar.error_message,
                    "run_started_at_utc": ar.run_started_at_utc,
                    "run_finished_at_utc": ar.run_finished_at_utc,
                    "adapter_version": ar.adapter_version,
                },
            )
        except Exception:  # noqa: BLE001
            pass  # health beacon failure never masks the actual result
        return ar


__all__ = [
    "MASTERFILE_URL",
    "GKG_COL_ORGS",
    "fetch_masterfile_lines",
    "parse_gkg_stream",
    "ingest_gdelt_news_volume",
    "GdeltGkgBulkAdapter",
]
