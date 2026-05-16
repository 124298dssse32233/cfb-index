"""Feed URL validator — catches dead RSS / API URLs before the first cron run.

For every source_registry row with a URL (``terms_url``), we issue a HEAD
(falling back to GET on 405) with a short timeout. Result writes a row to
``scrape_health`` keyed on ``source_id``, so ``python manage.py scrape-health``
will surface the dead ones in its normal sort order.

Scope: both global sources (cfbd, wiki_pv, …) and per-team instantiations
(campus_alabama, beat_lsu_advocate_lsu, …). For Wikipedia entities,
the terms_url points at the Foundation ToS — not the article — so we also
validate ``priority_teams.wiki_{team,coach,qb}_page`` in a dedicated pass.
"""
from __future__ import annotations

import datetime as _dt
import logging
import urllib.parse
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from cfb_rankings.common.head_chrome import base_url
from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

# Routes through head_chrome.base_url() so a domain swap is a one-line change.
_UA = f"CFBIndex-FanIntel/0.1 (+{base_url()})"
_TIMEOUT_SECONDS = 10.0


def _check_url(url: str) -> tuple[str, str | None]:
    """Return (status, error_message_or_None). Status is ok|error|skipped."""
    if not url or not url.startswith(("http://", "https://")):
        return "skipped", "no http(s) url"
    # Try HEAD first
    for method in ("HEAD", "GET"):
        try:
            req = Request(url, method=method, headers={"User-Agent": _UA, "Accept": "*/*"})
            with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
                if 200 <= resp.status < 400:
                    return "ok", None
                return "error", f"HTTP {resp.status}"
        except HTTPError as exc:
            if exc.code == 405 and method == "HEAD":
                continue  # fallback to GET
            return "error", f"HTTP {exc.code}"
        except URLError as exc:
            return "error", f"URLError: {exc.reason}"
        except Exception as exc:  # noqa: BLE001
            return "error", f"{type(exc).__name__}: {exc}"
    return "error", "unreachable"


def _today_iso() -> str:
    return _dt.date.today().isoformat()


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_registry_feeds(db: Database, *, only_active: bool = True,
                            include_templates: bool = False) -> dict[str, int]:
    """Validate every source_registry row with a terms_url. Writes scrape_health."""
    filters = ["source_id is not null", "terms_url is not null"]
    if only_active:
        filters.append("is_active = 1")
    if not include_templates:
        # Exclude *_template rows (they point at generic ToS URLs shared by instances)
        filters.append("source_id not like '%\\_template' escape '\\'")
    where = " and ".join(filters)
    rows = db.query_all(
        f"select source_id, terms_url, adapter_version from "
        f"(select source_id, terms_url, null as adapter_version from source_registry where {where})"
    )
    ok = err = skipped = 0
    started = _now_iso()
    for row in rows:
        status, msg = _check_url(row["terms_url"])
        if status == "ok":
            ok += 1
        elif status == "error":
            err += 1
        else:
            skipped += 1
        db.execute(
            """
            insert into scrape_health (
                source_id, run_date, rows_inserted, status, error_message,
                run_started_at_utc, run_finished_at_utc, adapter_version
            ) values (
                :sid, :date, 0, :status, :msg, :start, :end, :ver
            )
            on conflict (source_id, run_date) do update set
                status = excluded.status,
                error_message = excluded.error_message,
                run_started_at_utc = excluded.run_started_at_utc,
                run_finished_at_utc = excluded.run_finished_at_utc,
                adapter_version = excluded.adapter_version
            """,
            {
                "sid": row["source_id"], "date": _today_iso(),
                "status": status, "msg": msg,
                "start": started, "end": _now_iso(),
                "ver": "validator-0.1.0",
            },
        )
    return {"ok": ok, "error": err, "skipped": skipped, "total": ok + err + skipped}


def validate_priority_team_wiki_pages(db: Database) -> dict[str, Any]:
    """Check every priority_teams.wiki_* page is a real Wikipedia article.

    Returns per-team results. Does NOT write to scrape_health (these are
    individual article-page checks, not source-level). Instead, returns
    a structured report that the CLI prints.
    """
    rows = db.query_all(
        """
        select pt.team_id, t.canonical_name,
               pt.wiki_team_page, pt.wiki_coach_page, pt.wiki_qb_page
        from priority_teams pt
        join teams t on t.team_id = pt.team_id
        """
    )
    report: list[dict[str, Any]] = []
    for r in rows:
        team_row: dict[str, Any] = {
            "team_id": r["team_id"], "team_name": r["canonical_name"], "issues": [],
        }
        for col, kind in (
            ("wiki_team_page", "team"),
            ("wiki_coach_page", "coach"),
            ("wiki_qb_page", "qb"),
        ):
            article = r.get(col)
            if not article:
                if kind == "team":
                    team_row["issues"].append(f"{kind}: MISSING")
                continue
            url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(article, safe='')}"
            status, msg = _check_url(url)
            if status != "ok":
                team_row["issues"].append(f"{kind}: {status} ({msg}) — {article}")
        report.append(team_row)
    return {"teams": report}


__all__ = ["validate_registry_feeds", "validate_priority_team_wiki_pages"]
