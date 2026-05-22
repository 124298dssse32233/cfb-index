"""Auto-generate /methodology/freshness.html — Autopilot v1 TASK 8.7.

Reads scrape_health and source_registry, renders a "last successful run
per source, per tier" table. Re-built every weekly cron. Linked from
the fan-intelligence methodology page + global nav.
"""
from __future__ import annotations

import datetime as _dt
import html
import logging
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path("output/site/methodology")
_OUTPUT_FILE = _OUTPUT_DIR / "freshness.html"


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _fetch_freshness_rows(db: Database) -> list[dict[str, Any]]:
    """For every source_registry row that has a source_id, join the most-
    recent scrape_health row (if any) and return a list sorted by tier
    then by last-run-age (oldest first — those are the stale sources
    that need attention)."""
    rows = db.query_all(
        """
        SELECT
            sr.source_id,
            sr.source_name AS name,
            sr.tier,
            sr.ingest_method,
            sr.is_active,
            sh.run_date        AS last_run_date,
            sh.status          AS last_status,
            sh.rows_inserted   AS last_rows_inserted,
            sh.error_message   AS last_error_message
        FROM source_registry sr
        LEFT JOIN (
            SELECT h.source_id, h.run_date, h.status, h.rows_inserted, h.error_message
            FROM scrape_health h
            JOIN (
                SELECT source_id, MAX(run_date) AS max_run
                FROM scrape_health GROUP BY source_id
            ) last_run
              ON last_run.source_id = h.source_id
             AND last_run.max_run   = h.run_date
        ) sh ON sh.source_id = sr.source_id
        WHERE sr.source_id IS NOT NULL
        ORDER BY
            CASE sr.tier WHEN 'A' THEN 1 WHEN 'B' THEN 2 WHEN 'C' THEN 3 WHEN 'D' THEN 4 ELSE 5 END,
            COALESCE(sh.run_date, '0000-00-00') ASC,
            sr.source_id
        """
    )
    return rows


def _format_row(row: dict[str, Any], today: _dt.date) -> str:
    source_id = html.escape(str(row.get("source_id") or ""))
    name = html.escape(str(row.get("name") or source_id))
    tier = html.escape(str(row.get("tier") or "?"))
    method = html.escape(str(row.get("ingest_method") or "?"))
    is_active = int(row.get("is_active") or 0)
    last_run = row.get("last_run_date")
    last_status = row.get("last_status") or ""
    rows_inserted = row.get("last_rows_inserted")

    if last_run:
        try:
            last_date = _dt.date.fromisoformat(str(last_run)[:10])
            age_days = (today - last_date).days
            age_text = "today" if age_days == 0 else f"{age_days}d ago"
        except Exception:
            age_text = str(last_run)
        run_cell = f"<td>{html.escape(str(last_run))}<br><small>({age_text})</small></td>"
    else:
        run_cell = '<td class="never">never</td>'

    status_class = {
        "ok": "status-ok",
        "empty": "status-empty",
        "error": "status-error",
        "skipped": "status-skipped",
    }.get(str(last_status).lower(), "status-unknown")
    status_cell = f'<td class="{status_class}">{html.escape(last_status or "—")}</td>'

    rows_cell = (
        f"<td>{rows_inserted:,}</td>" if isinstance(rows_inserted, (int, float))
        else "<td>—</td>"
    )

    active_cell = "<td>" + ("✓" if is_active else "inactive") + "</td>"

    return (
        "<tr>"
        f"<td>{name}</td>"
        f"<td><code>{source_id}</code></td>"
        f"<td>{tier}</td>"
        f"<td>{method}</td>"
        f"{active_cell}"
        f"{run_cell}"
        f"{status_cell}"
        f"{rows_cell}"
        "</tr>"
    )


def render_freshness_html(db: Database) -> str:
    rows = _fetch_freshness_rows(db)
    today = _dt.date.today()
    total = len(rows)
    ok = sum(1 for r in rows if (r.get("last_status") or "") == "ok")
    err = sum(1 for r in rows if (r.get("last_status") or "") == "error")
    never = sum(1 for r in rows if not r.get("last_run_date"))

    table_body = "\n".join(_format_row(r, today) for r in rows)

    from cfb_rankings.common.head_chrome import render_head_chrome

    generated_at = _utcnow_iso()
    _head_chrome = render_head_chrome(
        page_path="/methodology/freshness.html",
        title="Data Source Freshness | CFB Index",
        description=(
            f"Per-source freshness dashboard for the CFB Index "
            f"fan-intelligence pipeline. {total} registered sources, "
            "regenerated weekly."
        ),
        og_type="article",
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CFB Index — Data Source Freshness</title>
  {_head_chrome}
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; color: #111; }}
    h1 {{ font-size: 2rem; margin-bottom: 0.25rem; }}
    .sub {{ color: #555; margin-bottom: 1.5rem; }}
    .metrics {{ display: flex; gap: 2rem; margin-bottom: 1.5rem; }}
    .metric {{ background: #f7f7f7; padding: 0.75rem 1rem; border-radius: 8px; }}
    .metric b {{ display: block; font-size: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
    th, td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }}
    th {{ background: #fafafa; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; }}
    code {{ font-family: ui-monospace, monospace; background: #f2f2f2; padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.85em; }}
    .status-ok {{ color: #1a7f37; font-weight: 600; }}
    .status-error {{ color: #cf222e; font-weight: 600; }}
    .status-empty {{ color: #b08800; font-weight: 600; }}
    .status-skipped {{ color: #555; }}
    .status-unknown, .never {{ color: #999; font-style: italic; }}
    nav a {{ margin-right: 1rem; color: #0969da; }}
    small {{ color: #666; }}
  </style>
</head>
<body>
  <nav><a href="fan-intelligence.html">← Fan Intelligence methodology</a></nav>
  <h1>Data Source Freshness</h1>
  <p class="sub">Last successful run per source, per tier. Refreshed
     automatically each week. Updated {generated_at}.</p>

  <div class="metrics">
    <div class="metric"><b>{total}</b>registered sources</div>
    <div class="metric"><b>{ok}</b>ok on last run</div>
    <div class="metric"><b>{err}</b>error on last run</div>
    <div class="metric"><b>{never}</b>never pulled</div>
  </div>

  <table>
    <thead>
      <tr>
        <th scope="col">Source</th><th scope="col">ID</th><th scope="col">Tier</th><th scope="col">Method</th><th scope="col">Active</th>
        <th scope="col">Last run</th><th scope="col">Status</th><th scope="col">Items captured</th>
      </tr>
    </thead>
    <tbody>
{table_body}
    </tbody>
  </table>
</body>
</html>
"""


def write_freshness_page(db: Database, output_path: Path | None = None) -> Path:
    target = output_path or _OUTPUT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_freshness_html(db), encoding="utf-8")
    logger.info("wrote freshness page to %s", target)
    return target
