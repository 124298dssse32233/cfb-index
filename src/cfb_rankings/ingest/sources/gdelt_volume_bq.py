"""GDELT volume via BigQuery — the bulk replacement for the per-team DOC 2.0 API.

The DOC 2.0 adapter (``gdelt_volume.py``) makes ONE rate-limited HTTP call per
team (~1 req / 5 s), so an all-138 sweep is an ~11-min floor and trips HTTP 429.
This adapter instead runs ONE BigQuery query against the public GDELT GKG table
``gdelt-bq.gdeltv2.gkg_partitioned`` and gets per-team daily article counts for
*all* teams at once — no rotation, no rate limit, no grind.

Cost & safety (built for a solo dev on the free BigQuery sandbox, 1 TB/month):
  * The query references only the ``_PARTITIONTIME`` pseudo-column + two GKG
    columns (``GKGRECORDID``, ``V2Organizations``) over a short rolling window
    (default 3 days), so bytes-scanned is small and bounded.
  * ``maximum_bytes_billed`` is set HARD (default 2 GB). If a query would scan
    more, BigQuery ERRORS instead of billing — you can never get a surprise bill.
  * ``GDELT_BQ_DRY_RUN=1`` runs a $0 dry-run that only logs the byte estimate
    and writes nothing — use it to validate cost before going live.
  * Missing creds / missing ``google-cloud-bigquery`` → graceful ``skipped``
    (AdapterConfigError), never an error. Until you set GOOGLE_APPLICATION_
    CREDENTIALS this adapter is a clean no-op and the rest of collect.ps1 runs.

Matching: each team has one or more LOWERCASE substring aliases matched against
the GKG ``V2Organizations`` field. Curated aliases live in
``data/seeds/gdelt_team_aliases.json`` (precise nickname/"university of X" forms,
with homonym guards for Miami/Washington/Oregon/Buffalo/Georgia/etc.). Teams not
in the seed fall back to a conservative DB-derived alias (canonical name), with
bare single-token ambiguous names skipped so we don't count the *city/state/pro*
team. GDELT remains a best-effort cross-check; per-team Google News (collected
for all 138) is the primary news-volume signal.

Setup (one time, see docs/gdelt_bigquery_setup_2026-06.md):
  1. Create a free GCP project (BigQuery sandbox — no credit card, no billing).
  2. Create a service account, grant "BigQuery Job User" + "BigQuery Data Viewer".
  3. Download its JSON key to a gitignored path (e.g. secrets/gdelt-bq-key.json).
  4. In .env:  GOOGLE_APPLICATION_CREDENTIALS=secrets/gdelt-bq-key.json
               GDELT_BQ_PROJECT=<your-gcp-project-id>
  5. In .venv:  pip install google-cloud-bigquery
  6. Validate:  GDELT_BQ_DRY_RUN=1 python tools/run_adapter.py gdelt_volume_bq
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.base import AdapterConfigError
from cfb_rankings.ingest.sources.numeric_base import NumericSourceAdapter

logger = logging.getLogger(__name__)

_GKG_TABLE = "gdelt-bq.gdeltv2.gkg_partitioned"
_ALIAS_SEED = Path(__file__).resolve().parents[4] / "data" / "seeds" / "gdelt_team_aliases.json"

# Bare single-token program names that collide with a city / state / pro team /
# country in GDELT org strings. A team whose lowercased canonical name is in
# this set is SKIPPED unless it has a curated alias in the seed file.
_AMBIGUOUS_BARE = {
    "miami", "washington", "oregon", "buffalo", "georgia", "houston",
    "cincinnati", "memphis", "charlotte", "tulsa", "rice", "army", "navy",
    "florida", "indiana", "kansas", "stanford", "auburn", "boston", "san",
    "colorado", "california", "hawaii", "ohio", "utah", "arizona", "nevada",
    "iowa", "minnesota", "michigan", "tennessee", "kentucky", "missouri",
    "oklahoma", "oregon", "syracuse", "temple", "akron", "toledo", "kent",
}


class GdeltVolumeBigQueryAdapter(NumericSourceAdapter):
    """One-query bulk GDELT GKG volume for all priority teams via BigQuery."""

    source_id = "gdelt_volume"  # shares the source_observations bucket with the DOC adapter
    adapter_version = "bq-0.1.0"
    source_tier = "A"

    default_window_days = 3
    default_max_gb_billed = 2.0

    # ------------------------------------------------------------------ aliases
    def _load_curated_aliases(self) -> dict[str, list[str]]:
        if not _ALIAS_SEED.exists():
            return {}
        try:
            raw = json.loads(_ALIAS_SEED.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("gdelt_bq: could not read alias seed %s: %s", _ALIAS_SEED, exc)
            return {}
        out: dict[str, list[str]] = {}
        for slug, aliases in raw.items():
            if slug.startswith("_") or not isinstance(aliases, list):
                continue
            cleaned = [str(a).strip().lower() for a in aliases if str(a).strip()]
            if cleaned:
                out[slug.lower()] = cleaned
        return out

    def _build_alias_rows(self) -> list[dict[str, Any]]:
        """Return [{team_id, alias_lc}] for every team we can match precisely.

        Curated seed wins; otherwise a conservative DB default (canonical name),
        skipping bare-ambiguous single tokens.
        """
        curated = self._load_curated_aliases()
        teams = self.db.query_all(
            "select pt.team_id, t.slug, t.canonical_name "
            "from priority_teams pt join teams t on t.team_id = pt.team_id"
        )
        rows: list[dict[str, Any]] = []
        skipped_ambiguous: list[str] = []
        for t in teams:
            slug = (t.get("slug") or "").lower()
            tid = int(t["team_id"])
            aliases = curated.get(slug)
            if not aliases:
                name = (t.get("canonical_name") or "").strip().lower()
                if not name:
                    continue
                # Skip bare ambiguous single-token names (no curated alias).
                if " " not in name and name in _AMBIGUOUS_BARE:
                    skipped_ambiguous.append(slug or name)
                    continue
                aliases = [name]
            for a in aliases:
                rows.append({"team_id": tid, "alias_lc": a})
        if skipped_ambiguous:
            logger.info(
                "gdelt_bq: %d ambiguous teams skipped for lack of a curated alias "
                "(add them to %s): %s",
                len(skipped_ambiguous), _ALIAS_SEED.name,
                ", ".join(sorted(skipped_ambiguous)[:20]),
            )
        return rows

    # ------------------------------------------------------------------ fetch
    def fetch(self) -> list[dict[str, Any]]:
        try:
            from google.cloud import bigquery  # type: ignore
        except ImportError as exc:  # graceful skip — pip install google-cloud-bigquery
            raise AdapterConfigError(
                "google-cloud-bigquery not installed (pip install google-cloud-bigquery)"
            ) from exc

        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        project = os.environ.get("GDELT_BQ_PROJECT", "").strip() or None
        if not creds_path and not os.environ.get("GOOGLE_CLOUD_PROJECT"):
            raise AdapterConfigError(
                "GOOGLE_APPLICATION_CREDENTIALS not set (point it at your service-account JSON)"
            )
        if creds_path and not Path(creds_path).exists():
            raise AdapterConfigError(
                f"GOOGLE_APPLICATION_CREDENTIALS points at a missing file: {creds_path}"
            )

        alias_rows = self._build_alias_rows()
        if not alias_rows:
            logger.warning("gdelt_bq: no team aliases resolved; nothing to query")
            return []

        window_days = int(os.environ.get("GDELT_BQ_WINDOW_DAYS", str(self.default_window_days)))
        max_gb = float(os.environ.get("GDELT_BQ_MAX_GB", str(self.default_max_gb_billed)))
        dry_run = os.environ.get("GDELT_BQ_DRY_RUN", "").strip() in ("1", "true", "yes")

        now = _dt.datetime.now(_dt.timezone.utc)
        end_ts = (now + _dt.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        start_ts = (now - _dt.timedelta(days=window_days)).strftime("%Y-%m-%d 00:00:00")

        try:
            client = bigquery.Client(project=project)
        except Exception as exc:  # noqa: BLE001 — DefaultCredentialsError etc. → graceful skip
            raise AdapterConfigError(f"BigQuery client init failed: {exc}") from exc

        query = f"""
        WITH gkg AS (
          SELECT GKGRECORDID AS rid,
                 DATE(_PARTITIONTIME) AS d,
                 LOWER(V2Organizations) AS orgs
          FROM `{_GKG_TABLE}`
          WHERE _PARTITIONTIME >= TIMESTAMP(@start_ts)
            AND _PARTITIONTIME <  TIMESTAMP(@end_ts)
            AND V2Organizations IS NOT NULL AND V2Organizations != ''
        )
        SELECT a.team_id AS team_id,
               g.d AS observed_date,
               COUNT(DISTINCT g.rid) AS article_count
        FROM gkg g, UNNEST(@aliases) AS a
        WHERE STRPOS(g.orgs, a.alias_lc) > 0
        GROUP BY team_id, observed_date
        """

        alias_structs = [
            bigquery.StructQueryParameter(
                "",
                bigquery.ScalarQueryParameter("team_id", "INT64", r["team_id"]),
                bigquery.ScalarQueryParameter("alias_lc", "STRING", r["alias_lc"]),
            )
            for r in alias_rows
        ]
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_ts", "STRING", start_ts),
                bigquery.ScalarQueryParameter("end_ts", "STRING", end_ts),
                bigquery.ArrayQueryParameter("aliases", "STRUCT", alias_structs),
            ],
            maximum_bytes_billed=int(max_gb * 1024 ** 3),
            use_query_cache=True,
            dry_run=dry_run,
        )

        job = client.query(query, job_config=job_config)
        if dry_run:
            gb = (job.total_bytes_processed or 0) / 1024 ** 3
            logger.info(
                "gdelt_bq DRY RUN: would scan %.3f GB (cap %.1f GB), window=%dd, %d aliases. "
                "No rows written.", gb, max_gb, window_days, len(alias_rows),
            )
            return []

        out: list[dict[str, Any]] = []
        for row in job.result():
            out.append({
                "team_id": int(row["team_id"]),
                "observed_date": str(row["observed_date"]),
                "article_count": int(row["article_count"] or 0),
            })
        gb = (getattr(job, "total_bytes_billed", None) or 0) / 1024 ** 3
        logger.info(
            "gdelt_bq: %d (team,day) rows over %dd window; billed %.3f GB.",
            len(out), window_days, gb,
        )
        return out

    # ------------------------------------------------------------------ parse
    def parse(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for r in raw:
            d = r.get("observed_date") or ""
            if len(d) < 10:
                continue
            iso = f"{d[:10]}T00:00:00Z"
            tid = str(r["team_id"])
            rows.append({
                "entity_type": "team_query",
                "entity_id": tid,
                "entity_label": f"team:{tid}",
                "observed_at_utc": iso,
                "metric": "article_count",
                "value_numeric": float(r.get("article_count") or 0),
                "sample_window": "1d",
                "capture_url": f"bigquery://{_GKG_TABLE}",
                "raw_payload_json": r,
                # Day granularity so a 3-day rolling window upserts the same
                # (team, day) cell cleanly across daily runs.
                "dedup_key": self.make_dedup_key(self.source_id, tid, "article_count", iso, "day"),
            })
        return rows


__all__ = ["GdeltVolumeBigQueryAdapter"]
