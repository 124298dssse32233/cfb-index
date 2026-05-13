"""Retro offseason Hub page rendering.

This module keeps the retro magazine path thin: it reuses the Hub v5 renderer and
only adds retro navigation, SEO, provenance framing, and cache-manifest output.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json
import subprocess
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.hub_page import fetch_hub_data, render_hub_page_html
from cfb_rankings.ingest.hub_data_retro import RETRO_BANNER, RETRO_ISSUES, seed_offseason_week_map, seed_retro_issue


def _issue_key(issue_number: str) -> str:
    return issue_number.replace("N°", "").replace("No.", "").replace("No", "").strip().zfill(3)


def _page_filename(issue_key: str, slug: str) -> str:
    return f"issue-{issue_key}-{slug}.html"


def _fingerprint() -> dict[str, str]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        git_sha = "nogit"
    return {"run_id": run_id, "git_sha": git_sha, "fingerprint": f"{git_sha}-{run_id}"}


def _retro_banner_html() -> str:
    return f'<div class="hub-retro-banner">{escape(RETRO_BANNER)}</div>'


def _head_extra(cache_token: str | None = None, *, indexable: bool = False) -> str:
    cache_meta = f'\n    <meta name="cfb-retro-cache" content="{escape(cache_token)}">' if cache_token else ""
    robots = "index,follow" if indexable else "noindex,follow"
    return (
        f'<meta name="robots" content="{robots}">\n'
        '    <link rel="canonical" href="/hub/retro/">'
        f"{cache_meta}"
    )


def _all_visible_stats_computed(data: dict[str, Any]) -> bool:
    ticker = data.get("mood_ticker") or {}
    rows: list[dict[str, Any]] = []
    rows.extend(ticker.get("gainers") or [])
    rows.extend(ticker.get("losers") or [])
    rows.extend(data.get("rivalries") or [])
    if data.get("lexicon"):
        rows.append(data["lexicon"])
    if not rows:
        return False
    return all(str(row.get("source") or "").lower() == "computed" for row in rows)


def _prepare_retro_data(db: Database, issue_key: str, *, cache_token: str | None = None) -> dict[str, Any]:
    meta = RETRO_ISSUES[issue_key]
    data = fetch_hub_data(
        db,
        issue_number=meta["issue_number"],
        week_start=meta["week_start_date"],
        season_year=2025,
    )
    issue = data["issue"]
    issue.update(
        {
            "is_retro": True,
            "source": "editorial",
            "retro_slug": meta["retro_slug"],
            "retro_title": meta["retro_title"],
            "mood_index_dek": meta["mood_index_dek"],
            "retro_banner_html": _retro_banner_html(),
            "prev_issue": _previous_issue_label(issue_key),
            "next_issue": _next_issue_label(issue_key),
        }
    )
    data.update(
        {
            "is_retro": True,
            "site_prefix": "../../",
            "head_extra": _head_extra(cache_token, indexable=_all_visible_stats_computed(data)),
        }
    )
    return data


def _previous_issue_label(issue_key: str) -> str | None:
    keys = sorted(RETRO_ISSUES)
    idx = keys.index(issue_key)
    return RETRO_ISSUES[keys[idx - 1]]["issue_number"] if idx > 0 else None


def _next_issue_label(issue_key: str) -> str | None:
    keys = sorted(RETRO_ISSUES)
    idx = keys.index(issue_key)
    return RETRO_ISSUES[keys[idx + 1]]["issue_number"] if idx < len(keys) - 1 else None


def render_offseason_week(
    db: Database,
    issue: str | int,
    output_dir: str | Path = "output/site",
    *,
    cache_token: str | None = None,
) -> Path:
    issue_key = _issue_key(str(issue))
    if issue_key not in RETRO_ISSUES:
        raise ValueError(f"Unknown retro issue: {issue}")
    retro_dir = Path(output_dir) / "hub" / "retro"
    retro_dir.mkdir(parents=True, exist_ok=True)
    data = _prepare_retro_data(db, issue_key, cache_token=cache_token)
    html = render_hub_page_html(data)
    filename = _page_filename(issue_key, RETRO_ISSUES[issue_key]["retro_slug"])
    out_path = retro_dir / filename
    out_path.write_text(html, encoding="utf-8")
    return out_path


def _archive_card(issue_key: str) -> str:
    issue = RETRO_ISSUES[issue_key]
    href = _page_filename(issue_key, issue["retro_slug"])
    return f"""
    <article class="retro-archive-card">
      <a href="{escape(href)}">
        <div class="retro-archive-issue">{escape(issue["issue_number"])}</div>
        <h2>{escape(issue["retro_title"])}</h2>
        <p>{escape(issue["cover_dek"])}</p>
      </a>
    </article>
    """


def _archive_html(cache_token: str | None = None) -> str:
    cards = "".join(_archive_card(key) for key in sorted(RETRO_ISSUES))
    cache_meta = f'<meta name="cfb-retro-cache" content="{escape(cache_token)}">' if cache_token else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,follow">
    <title>Retro Offseason Magazine · The CFB Index</title>
    <meta name="description" content="Retroactive college football offseason magazine issues from Jan. 19 through Apr. 22, 2026.">
    {cache_meta}
    <style>
      body {{ margin:0; background:#F3EEE4; color:#0B0F14; font-family: Georgia, serif; }}
      .retro-archive {{ max-width:1180px; margin:0 auto; padding:48px 20px 72px; }}
      .retro-archive-banner {{ background:#FFF4CF; border-bottom:1px solid rgba(224,163,0,.45); padding:14px 20px; text-align:center; font:700 12px/1.4 monospace; letter-spacing:.08em; text-transform:uppercase; }}
      .retro-archive h1 {{ font-size:clamp(42px,8vw,92px); line-height:.92; margin:0 0 16px; text-transform:uppercase; }}
      .retro-archive-dek {{ max-width:780px; font-size:20px; line-height:1.45; color:#5A5954; margin:0 0 36px; }}
      .retro-archive-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:18px; }}
      .retro-archive-card {{ background:#fff; border:1px solid #B5AFA3; min-height:220px; }}
      .retro-archive-card a {{ display:block; color:inherit; text-decoration:none; padding:22px; height:100%; }}
      .retro-archive-issue {{ font:700 12px/1 monospace; color:#6f4d00; letter-spacing:.12em; text-transform:uppercase; }}
      .retro-archive-card h2 {{ font-size:30px; line-height:1; margin:16px 0 12px; text-transform:uppercase; }}
      .retro-archive-card p {{ color:#5A5954; line-height:1.5; }}
    </style>
  </head>
  <body>
    <div class="retro-archive-banner">{escape(RETRO_BANNER)}</div>
    <main class="retro-archive">
      <h1>The Road From The Title Game</h1>
      <p class="retro-archive-dek">Ten retroactive weekly issues covering the Jan. 19 national championship through the Apr. 22 live handoff. Phase A pages are visibly editorial until computed rows pass calibration.</p>
      <section class="retro-archive-grid">{cards}</section>
    </main>
  </body>
</html>
"""


def build_retro_pages(
    db: Database,
    output_dir: str | Path = "output/site",
    *,
    bust_cache: bool = False,
) -> list[Path]:
    _ensure_retro_seeded(db)
    fp = _fingerprint() if bust_cache else {"run_id": "", "git_sha": "", "fingerprint": ""}
    cache_token = fp["fingerprint"] if bust_cache else None
    # Render each retro page defensively: if one page's data is missing
    # (empty DB / partial seed) we'd rather skip that page than blow up
    # the whole build pipeline. The publish-site workflow's "seed from
    # prior artifact" step preserves the last good version of each page.
    paths: list[Path] = []
    for issue_key in sorted(RETRO_ISSUES):
        try:
            paths.append(render_offseason_week(db, issue_key, output_dir, cache_token=cache_token))
        except Exception as exc:
            print(f"[retro] {issue_key} render skipped ({type(exc).__name__}): {exc}")
    retro_dir = Path(output_dir) / "hub" / "retro"
    archive_path = retro_dir / "index.html"
    archive_path.write_text(_archive_html(cache_token), encoding="utf-8")
    paths.append(archive_path)
    if bust_cache:
        manifest = {
            **fp,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pages": [str(path.relative_to(Path(output_dir))) for path in paths],
        }
        manifest_path = Path(output_dir) / "retro-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        paths.append(manifest_path)
    return paths


def _ensure_retro_seeded(db: Database) -> None:
    """Seed the retro tables required by the offseason-week pages.

    Tolerant of partial-DB state: when the source DB is missing upstream
    rows (e.g. CI runs against a downloaded artifact that doesn't have
    the model_runs / seasons / weeks scaffolding yet), the upserts here
    can raise ``sqlite3.IntegrityError: FOREIGN KEY constraint failed``.
    In that case we log a warning and return — the retro pages just
    won't be generated this run, which is preferable to crashing the
    whole ``build-site`` pipeline. The deploy then falls back to the
    prior site artifact for retro content via the publish-site
    workflow's seed-from-prior step.
    """
    import sqlite3
    try:
        seed_offseason_week_map(db)
        for issue_key, issue in RETRO_ISSUES.items():
            row = db.query_one(
                "select hub_issue_id, methodology_row_json from hub_issue_metadata where issue_number = %(issue)s limit 1",
                {"issue": issue["issue_number"]},
            )
            methodology = str((row or {}).get("methodology_row_json") or "").strip()
            if not row or methodology in {"", "{}"}:
                seed_retro_issue(db, issue_key)
    except sqlite3.IntegrityError as exc:
        # FK constraint failure usually means the DB artifact this build
        # is running against doesn't have the upstream rows the retro
        # tables reference. Log + continue; downstream renderers will
        # either reuse prior artifact or skip retro cleanly.
        print(f"[retro] retro seeding skipped (FK constraint failure): {exc}")
    except Exception as exc:
        # Catch-all defensive: don't let retro seeding crash the site
        # build. Retro is a section, not the spine.
        print(f"[retro] retro seeding skipped ({type(exc).__name__}): {exc}")
