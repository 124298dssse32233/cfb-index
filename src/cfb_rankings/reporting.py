from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
from html import escape
import json
import math
from pathlib import Path
import re
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.fan_intelligence import (
    MoodContext,
    build_team_index,
    fetch_fan_intel_board,
    fetch_team_mood_profile,
)
from cfb_rankings.visual_assets import resolve_team_brand
from cfb_rankings.utils import (
    PROGRAM_COUNT_REFERENCE_DATE,
    SUBDIVISION_PROGRAM_COUNTS,
    is_site_eligible_team,
    season_label,
    season_span_label,
    slugify,
)


@dataclass
class RankingRow:
    rank: int
    team_id: int
    slug: str
    team_name: str
    level_code: str
    conference_name: str | None
    power_rating: float
    resume_score: float
    cross_level_confidence: float | None
    schedule_connectivity: float | None
    previous_rank: int | None = None
    rank_change: int = 0
    power_display: float | None = None
    resume_display: float | None = None
    power_percentile: float | None = None
    resume_percentile: float | None = None
    resume_rank: int | None = None


@dataclass
class HeismanRankingRow:
    overall_rank: int
    player_id: int
    player_slug: str
    full_name: str
    team_id: int | None
    team_slug: str | None
    team_name: str | None
    conference_name: str | None
    position: str | None
    class_year: str | None
    season_year: int
    week: int
    nowcast_rank: int | None
    forecast_rank: int | None
    win_probability: float | None
    finalist_probability: float | None
    any_ballot_probability: float | None
    expected_ballot_share: float | None
    latent_score: float | None
    market_implied_probability: float | None = None
    market_american_odds: int | None = None
    market_provider: str | None = None


G5_CONFERENCES = {
    "American Athletic",
    "Conference USA",
    "Mid-American",
    "Mountain West",
    "Sun Belt",
}

DEFENSIVE_POSITIONS = {
    "CB",
    "DB",
    "DE",
    "DL",
    "DT",
    "EDGE",
    "FS",
    "ILB",
    "LB",
    "NT",
    "OLB",
    "S",
    "SAF",
    "SS",
}


_SIMILARITY_PROFILE_CACHE: dict[str, dict[str, Any]] = {}
_OG_LOGO_B64_CACHE: dict[str, str | None] = {}


def _og_logo_data_url(slug: str, site_root: Path | None = None) -> str | None:
    """Return a base64 data-URL for a team's primary logo, or None.

    Results are cached per slug for the lifetime of the process.
    """
    if slug in _OG_LOGO_B64_CACHE:
        return _OG_LOGO_B64_CACHE[slug]
    try:
        brand = resolve_team_brand(slug)
        local_path: str | None = brand.logo_local_path
        if not local_path:
            _OG_LOGO_B64_CACHE[slug] = None
            return None
        root = site_root if site_root is not None else Path("output/site")
        full_path = root / local_path.lstrip("/")
        if not full_path.is_file():
            _OG_LOGO_B64_CACHE[slug] = None
            return None
        data = full_path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        _OG_LOGO_B64_CACHE[slug] = data_url
        return data_url
    except Exception as exc:  # noqa: BLE001
        print(f"[OG logo] Warning: could not load logo for {slug!r}: {exc}", flush=True)
        _OG_LOGO_B64_CACHE[slug] = None
        return None


def fetch_latest_run_summary(db: Database) -> dict[str, Any] | None:
    return db.query_one(
        """
        select mr.model_run_id, mr.season_year, mr.week, mr.model_version, mr.data_cutoff_utc, s.season_label
        from model_runs mr
        left join seasons s on s.season_year = mr.season_year
        where exists (
          select 1
          from power_ratings_weekly p
          where p.model_run_id = mr.model_run_id
        )
        order by mr.season_year desc, mr.week desc, mr.model_run_id desc
        limit 1
        """
    )


def fetch_snapshot_summaries(db: Database) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        with snapshot_runs as (
          select mr.season_year, mr.week, max(mr.model_run_id) as model_run_id
          from model_runs mr
          where exists (
            select 1
            from power_ratings_weekly p
            where p.model_run_id = mr.model_run_id
              and p.season_year = mr.season_year
              and p.week = mr.week
          )
          group by mr.season_year, mr.week
        )
        select
          sr.model_run_id,
          sr.season_year,
          sr.week,
          mr.model_version,
          mr.data_cutoff_utc,
          s.season_label
        from snapshot_runs sr
        join model_runs mr on mr.model_run_id = sr.model_run_id
        left join seasons s on s.season_year = sr.season_year
        order by sr.season_year desc, sr.week desc, sr.model_run_id desc
        """
    )
    snapshots: list[dict[str, Any]] = []
    for row in rows:
        season_year = int(row["season_year"])
        week = int(row["week"])
        snapshots.append(
            {
                **row,
                "season_year": season_year,
                "week": week,
                "slug": f"{season_year}-week-{week:02d}",
                "season_name": season_label(season_year),
            }
        )
    return snapshots


def _fetch_rankings_for_summary(
    db: Database,
    summary: dict[str, Any],
    limit: int = 1000,
) -> list[RankingRow]:
    rows = db.query_all(
        """
        select
          t.team_id,
          t.slug,
          t.canonical_name as team_name,
          coalesce(ts.level_code, t.level_code) as level_code,
          c.conference_name,
          p.power_rating,
          r.resume_score,
          p.cross_level_confidence,
          p.schedule_connectivity
        from power_ratings_weekly p
        join teams t on t.team_id = p.team_id
        left join team_seasons ts
          on ts.team_id = t.team_id
         and ts.season_year = p.season_year
        left join conferences c on c.conference_id = ts.conference_id
        left join resume_ratings_weekly r
          on r.model_run_id = p.model_run_id
         and r.team_id = p.team_id
         and r.week = p.week
        where p.model_run_id = %(model_run_id)s
          and p.week = %(week)s
        order by p.power_rating desc, r.resume_score desc, t.canonical_name asc
        """,
        {"model_run_id": summary["model_run_id"], "week": summary["week"]},
    )

    ranking_rows: list[RankingRow] = []
    for row in rows:
        level_code = str(row["level_code"] or "")
        conference_name = row.get("conference_name")
        if not is_site_eligible_team(level_code, None if conference_name is None else str(conference_name)):
            continue
        ranking_rows.append(
            RankingRow(
                rank=len(ranking_rows) + 1,
                team_id=int(row["team_id"]),
                slug=str(row["slug"]),
                team_name=str(row["team_name"]),
                level_code=level_code,
                conference_name=None if conference_name is None else str(conference_name),
                power_rating=float(row["power_rating"] or 0.0),
                resume_score=float(row["resume_score"] or 0.0),
                cross_level_confidence=float(row["cross_level_confidence"] or 0.0),
                schedule_connectivity=float(row["schedule_connectivity"] or 0.0),
            )
        )
    _attach_public_metric_context(ranking_rows)
    return ranking_rows[:limit]


def _attach_rank_changes(current_rankings: list[RankingRow], previous_rankings: list[RankingRow]) -> None:
    previous_rank_map = {row.team_id: row.rank for row in previous_rankings}
    for row in current_rankings:
        previous_rank = previous_rank_map.get(row.team_id)
        row.previous_rank = previous_rank
        row.rank_change = int(previous_rank - row.rank) if previous_rank is not None else 0


def _rank_percentile(rank_value: int, total: int) -> float:
    if total <= 1:
        return 100.0
    return 100.0 * (total - rank_value) / max(1, total - 1)


def _attach_public_metric_context(rankings: list[RankingRow]) -> None:
    if not rankings:
        return

    mean_power = sum(float(row.power_rating) for row in rankings) / len(rankings)
    power_order = sorted(rankings, key=lambda row: (-row.power_rating, -row.resume_score, row.team_name.lower()))
    resume_order = sorted(rankings, key=lambda row: (-row.resume_score, -row.power_rating, row.team_name.lower()))
    power_rank_map = {row.slug: index + 1 for index, row in enumerate(power_order)}
    resume_rank_map = {row.slug: index + 1 for index, row in enumerate(resume_order)}

    for row in rankings:
        power_rank = power_rank_map[row.slug]
        resume_rank = resume_rank_map[row.slug]
        row.power_display = float(row.power_rating) - mean_power
        row.resume_display = _rank_percentile(resume_rank, len(rankings))
        row.power_percentile = _rank_percentile(power_rank, len(rankings))
        row.resume_percentile = _rank_percentile(resume_rank, len(rankings))
        row.resume_rank = resume_rank


def _attach_historical_public_metric_context(ledger: list[dict[str, Any]]) -> None:
    if not ledger:
        return

    rows_by_season: dict[int, list[dict[str, Any]]] = {}
    for row in ledger:
        rows_by_season.setdefault(int(row.get("season_year") or 0), []).append(row)

    for rows in rows_by_season.values():
        power_rows = [row for row in rows if row.get("end_power") is not None]
        if power_rows:
            mean_power = sum(float(row.get("end_power") or 0.0) for row in power_rows) / len(power_rows)
            ordered_power = sorted(
                power_rows,
                key=lambda row: (
                    -float(row.get("end_power") or 0.0),
                    -float(row.get("end_resume") or 0.0),
                    str(row.get("team_name") or "").lower(),
                ),
            )
            power_rank_map = {
                (int(row.get("team_id") or 0), int(row.get("season_year") or 0)): index + 1
                for index, row in enumerate(ordered_power)
            }
            for row in power_rows:
                key = (int(row.get("team_id") or 0), int(row.get("season_year") or 0))
                row["end_power_display"] = float(row.get("end_power") or 0.0) - mean_power
                row["end_power_percentile"] = _rank_percentile(power_rank_map[key], len(power_rows))
        resume_rows = [row for row in rows if row.get("end_resume") is not None]
        if resume_rows:
            ordered_resume = sorted(
                resume_rows,
                key=lambda row: (
                    -float(row.get("end_resume") or 0.0),
                    -float(row.get("end_power") or 0.0),
                    str(row.get("team_name") or "").lower(),
                ),
            )
            resume_rank_map = {
                (int(row.get("team_id") or 0), int(row.get("season_year") or 0)): index + 1
                for index, row in enumerate(ordered_resume)
            }
            for row in resume_rows:
                key = (int(row.get("team_id") or 0), int(row.get("season_year") or 0))
                row["end_resume_display"] = _rank_percentile(resume_rank_map[key], len(resume_rows))
                row["end_resume_percentile"] = _rank_percentile(resume_rank_map[key], len(resume_rows))


def _ordinal(value: int) -> str:
    remainder = value % 100
    if 10 <= remainder <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _public_power_value(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _public_resume_value(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _public_power_text(value: Any, decimals: int = 1) -> str:
    public_value = _public_power_value(value)
    if public_value is None:
        return "--"
    return f"{public_value:+.{decimals}f}"


def _public_resume_text(value: Any, decimals: int = 0) -> str:
    public_value = _public_resume_value(value)
    if public_value is None:
        return "--"
    if decimals <= 0:
        return f"{round(public_value):.0f}"
    return f"{public_value:.{decimals}f}"


def _public_resume_percentile_label(value: Any) -> str:
    public_value = _public_resume_value(value)
    if public_value is None:
        return "--"
    return f"{_percentile_label(public_value)} season"


def _percentile_label(value: Any) -> str:
    if value is None:
        return "--"
    return f"{_ordinal(int(round(float(value))))} percentile"


def _power_resume_gap_note(power_value: Any, resume_value: Any) -> str:
    if power_value is None or resume_value is None:
        return "Power and resume will sharpen as more results land."
    gap = float(power_value) - float(resume_value)
    rounded_gap = int(round(abs(gap)))
    if rounded_gap < 2:
        return "Power and resume are essentially aligned right now."
    point_label = "point" if rounded_gap == 1 else "points"
    if gap > 0:
        return f"Power is running {rounded_gap} percentile {point_label} ahead of resume right now."
    return f"Resume is running {rounded_gap} percentile {point_label} ahead of power right now."


def _signed_integer_text(value: Any) -> str:
    if value is None:
        return "--"
    return f"{float(value):+.0f}"


def _first_present_float(*values: Any) -> float | None:
    for value in values:
        if value not in (None, ""):
            return float(value)
    return None


def fetch_latest_rankings(db: Database, limit: int = 1000) -> tuple[dict[str, Any] | None, list[RankingRow]]:
    snapshots = fetch_snapshot_summaries(db)
    if not snapshots:
        return None, []
    latest = snapshots[0]
    previous = next(
        (
            snapshot
            for snapshot in snapshots[1:]
            if int(snapshot["season_year"]) == int(latest["season_year"])
        ),
        None,
    )
    ranking_rows = _fetch_rankings_for_summary(db, latest, limit=limit)
    if previous is not None:
        previous_rankings = _fetch_rankings_for_summary(db, previous, limit=2000)
        _attach_rank_changes(ranking_rows, previous_rankings)
    return latest, ranking_rows


def write_latest_rankings_report(db: Database, output_path: str | Path, limit: int = 100) -> Path:
    _report_progress(f"Building standalone rankings report at {output_path}...")
    summary, rankings = fetch_latest_rankings(db, limit=limit)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if summary is None:
        output.write_text("<html><body><h1>No model runs found.</h1></body></html>", encoding="utf-8")
        _report_progress("No model runs found for standalone rankings report.")
        return output
    html = render_legacy_entry_html(summary, rankings)
    output.write_text(html, encoding="utf-8")
    _report_progress(f"Standalone rankings report wrote {len(rankings)} rows to {output}.")
    return output


# ---------------------------------------------------------------------------
# Frontend Migration S.0 — global asset emission
# ---------------------------------------------------------------------------
# Single external stylesheet served from /assets/cfb-index.<hash>.css; one
# vendored Alpine.js 3.14 from /assets/alpine.min.js. Every page emits one
# <link> + one <script defer> via _global_link_tags(). _ensure_global_assets
# writes the CSS file with a content-hashed filename at build start.
# ---------------------------------------------------------------------------

_ALPINE_ASSET_NAME = "alpine.min.js"

# Moved out of inline <style> blocks in S.0:
#   - _TEAM_ARCHETYPE_CSS_BLOCK was at reporting.py:9019-9035 (team page render)
#   - _ATTRIBUTIONS_CSS_BLOCK was at reporting.py:467-481 (attributions page)
# Attributions rules are scoped under .attributions-page; the page now sets
# `class="attributions-page"` on its <body>.

_TEAM_ARCHETYPE_CSS_BLOCK = """
.team-archetype-section { padding: 2rem 0; }
.team-archetype-module { background: #FFFFFF; border: 1px solid #B5AFA3; padding: 2rem; font-family: 'Source Serif 4', Georgia, serif; color: #0B0F14; }
.team-archetype-eyebrow { font-family: 'IBM Plex Mono', 'SFMono-Regular', monospace; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; color: #5A5954; margin-bottom: .75rem; }
.team-archetype-name { font-family: 'Bebas Neue', Impact, sans-serif; font-size: 2rem; line-height: 1; letter-spacing: -.005em; margin: 0 0 .25rem 0; }
.team-archetype-confidence { font-family: 'IBM Plex Mono', monospace; font-size: .875rem; color: #5A5954; font-variant-numeric: tabular-nums; margin-bottom: 1rem; }
.team-archetype-desc { font-size: 1rem; line-height: 1.55; margin: 0 0 1.25rem 0; }
.team-archetype-phrase, .team-archetype-modifier-block, .team-archetype-migration { border-top: 1px solid #E8E1D2; padding-top: 1rem; margin-bottom: 1rem; }
.team-archetype-phrase-label { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #5A5954; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: .5rem; }
.team-archetype-phrase-body { font-family: 'IBM Plex Mono', monospace; font-style: italic; font-size: .95rem; }
.team-archetype-modifier-row { display: flex; flex-wrap: wrap; gap: .75rem; }
.modifier-chip { display: inline-flex; align-items: center; gap: .25rem; font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: #0B0F14; background: #F3EEE4; border: 1px solid #B5AFA3; padding: .25rem .6rem; border-radius: 999px; }
.hub-gold-dot { color: #E0A300; }
.team-archetype-link { font-family: 'IBM Plex Mono', monospace; font-size: .82rem; border-bottom: 1px dotted currentColor; text-decoration: none; color: inherit; }
.team-archetype-spark { width: 100%; max-width: 360px; height: auto; }
.team-archetype-empty .team-archetype-blurb { font-size: 1rem; color: #5A5954; }
"""

_ATTRIBUTIONS_CSS_BLOCK = """
.attributions-page { background: #F3EEE4; color: #0B0F14; font-family: 'Source Serif 4', Georgia, serif; margin: 0; padding: 0 24px 96px; }
.attributions-page .rule { height: 4px; background: #E0A300; margin: 0 -24px 48px; }
.attributions-page main { max-width: 720px; margin: 0 auto; }
.attributions-page h1 { font-family: 'Bebas Neue', 'Impact', sans-serif; font-size: 56px; letter-spacing: 0.02em; margin: 48px 0 8px; }
.attributions-page h2 { font-family: 'Bebas Neue', 'Impact', sans-serif; font-size: 22px; letter-spacing: 0.12em; text-transform: uppercase; color: #6b6a63; margin: 40px 0 12px; }
.attributions-page .eyebrow { font-family: 'Bebas Neue', 'Impact', sans-serif; font-size: 14px; letter-spacing: 0.18em; text-transform: uppercase; color: #6b6a63; margin: 0; }
.attributions-page p { line-height: 1.65; font-size: 17px; }
.attributions-page a { color: #0B0F14; }
.attributions-page .back { margin-top: 64px; font-size: 14px; color: #6b6a63; }
"""

# Dark-mode override (S.1). OKLCH values from design-ref/Premium College
# Football Website UI/src/styles/theme.css. Every rendered <html> gets
# class="dark" so dark is the default; OS `prefers-color-scheme: light`
# reverts to the :root light palette via the media query block.
_DARK_MODE_CSS_BLOCK = """
html.dark {
  color-scheme: dark;
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.165 0 0);
  --card-foreground: oklch(0.985 0 0);
  --popover: oklch(0.165 0 0);
  --popover-foreground: oklch(0.985 0 0);
  --primary: oklch(0.985 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --secondary: oklch(0.269 0 0);
  --secondary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.269 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --accent-surface: oklch(0.269 0 0);
  --accent-foreground: oklch(0.985 0 0);
  --destructive: oklch(0.55 0.19 25.7);
  --destructive-foreground: oklch(0.985 0 0);
  --border: oklch(0.3 0 0);
  --border-strong: oklch(0.4 0 0);
  --input-background: oklch(0.269 0 0);
}

@media (prefers-color-scheme: light) {
  html.dark {
    color-scheme: light;
    --background: #FAFAFA;
    --foreground: #0A0A0A;
    --card: #FFFFFF;
    --card-foreground: #0A0A0A;
    --popover: #FFFFFF;
    --popover-foreground: #0A0A0A;
    --primary: #0A0A0A;
    --primary-foreground: #FFFFFF;
    --secondary: #F5F5F5;
    --secondary-foreground: #0A0A0A;
    --muted: #E8E8E8;
    --muted-foreground: #6B6B6B;
    --accent-surface: #1a1a1a;
    --accent-foreground: #FFFFFF;
    --destructive: #DC2626;
    --destructive-foreground: #FFFFFF;
    --border: rgba(10, 10, 10, 0.08);
    --border-strong: rgba(10, 10, 10, 0.14);
    --input-background: #F5F5F5;
  }
}
"""


# Cohort panel CSS — moved from inline block inside _render_cohort_panel (reporting.py:~16163).
_COHORT_PANEL_CSS_BLOCK = """
.cohort-panel { padding: 1.5rem 0; }
.cohort-list { list-style: none; padding: 0; margin: 1rem 0 0; font-family: "IBM Plex Mono", monospace; font-size: .85rem; }
.cohort-row { display: grid; grid-template-columns: 140px 1fr 60px 60px; gap: .75rem; align-items: center; padding: .25rem 0; }
.cohort-label { text-transform: uppercase; letter-spacing: .05em; color: #5A5954; }
.cohort-bar-track { background: #F3EEE4; height: 10px; position: relative; }
.cohort-bar { display: block; height: 100%; }
.cohort-bar--pos { background: #2f7d32; }
.cohort-bar--neg { background: #b23a3a; }
.cohort-bar--mute { background: #d7d1c2; }
.cohort-score--mute { color: #a09b8d; }
.cohort-row--volume-only .cohort-label { color: #5A5954; }
.cohort-score { text-align: right; font-variant-numeric: tabular-nums; }
.cohort-n { text-align: right; color: #5A5954; font-size: .75rem; }
.cohort-n--thin { color: #b07a00; }
.cohort-panel-empty-body { padding: 1rem 0; color: #5A5954; font-family: "Source Serif 4", Georgia, serif; }
"""

# Self-hosted fonts (vendored 2026-04-23). Declarations are additive in S.0;
# legacy @import in _site_css() still loads Anton / Bebas Neue / Inter from
# Google Fonts. S.1 typography migration removes the @import.
_FONT_FACE_BLOCK = """
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 100 900;
  font-display: swap;
  src: url('/assets/fonts/Inter-Variable.woff2') format('woff2-variations'),
       url('/assets/fonts/Inter-Variable.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter Display';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('/assets/fonts/InterDisplay-SemiBold.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter Display';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/assets/fonts/InterDisplay-Bold.woff2') format('woff2');
}
"""

_CSS_LAYER_HEADER = """@layer reset, tokens, base, typography, components, utilities, overrides;
"""


def _compose_global_css() -> str:
    """Assemble the contents of cfb-index.css.

    S.0 is mechanical: header + @layer declaration + @font-face block +
    verbatim _site_css() output + extracted inline blocks. S.1+ refactor.
    """
    header = (
        "@charset \"utf-8\";\n"
        "/*!\n"
        " * CFB Index — global stylesheet (Stage S.0, 2026-04-23)\n"
        " * Generated from src/cfb_rankings/reporting.py at build time.\n"
        " * Mechanical migration of inline <style> blocks; refactor lands in S.1+.\n"
        " */\n"
    )
    return (
        header
        + _CSS_LAYER_HEADER
        + _FONT_FACE_BLOCK
        + "\n/* === Legacy site CSS (verbatim from _site_css()) === */\n"
        + _site_css()
        + "\n/* === Team-archetype module — moved from reporting.py:~9019 === */\n"
        + _TEAM_ARCHETYPE_CSS_BLOCK
        + "\n/* === Attributions page — moved from reporting.py:~467, scoped to .attributions-page === */\n"
        + _ATTRIBUTIONS_CSS_BLOCK
        + "\n/* === Cohort panel — moved from reporting.py:~16163 === */\n"
        + _COHORT_PANEL_CSS_BLOCK
        + "\n/* === Dark-mode override (S.1) === */\n"
        + _DARK_MODE_CSS_BLOCK
    )


_global_css_filename: str | None = None


def _ensure_global_assets(site_root: Path) -> str:
    """Write cfb-index.<hash>.css and confirm alpine.min.js exists.

    Returns the content-hashed CSS filename (cached after first call).
    Alpine is vendored manually (not auto-fetched) — file must be present.
    """
    global _global_css_filename
    assets_dir = site_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    if _global_css_filename is None:
        css_text = _compose_global_css()
        digest = hashlib.sha256(css_text.encode("utf-8")).hexdigest()[:12]
        _global_css_filename = f"cfb-index.{digest}.css"
        out_path = assets_dir / _global_css_filename
        if not out_path.exists() or out_path.read_text(encoding="utf-8") != css_text:
            out_path.write_text(css_text, encoding="utf-8")
    return _global_css_filename


def _global_link_tags() -> str:
    """Per-page <link> + <script> tags for the vendored stylesheet + Alpine."""
    filename = _global_css_filename or "cfb-index.css"
    return (
        f'<link rel="stylesheet" href="/assets/{filename}">\n'
        f'    <script src="/assets/{_ALPINE_ASSET_NAME}" defer></script>'
    )


def _write_attributions_page(site_root: Path, db: "Database | None" = None) -> None:
    attributions_dir = site_root / "attributions"
    attributions_dir.mkdir(parents=True, exist_ok=True)
    espn_cdn_active = False
    if db is not None:
        try:
            row = db.query_one(
                "SELECT 1 AS found FROM team_brand_assets WHERE source_name = 'espn_cdn' LIMIT 1"
            )
            espn_cdn_active = row is not None and bool(row.get("found"))
        except Exception:
            pass
    html = """<!doctype html>
<html lang=\"en\" class=\"dark\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>Attributions | CFB Index</title>
__GLOBAL_TAGS__
</head>
<body class=\"attributions-page\">
<div class=\"rule\" aria-hidden=\"true\"></div>
<main>
  <p class=\"eyebrow\">Colophon</p>
  <h1>Attributions</h1>
  <p>A short accounting of where the data comes from, and whose marks appear on these pages.</p>

  <h2>Data sources</h2>
  <p>The CFB Index is built on <strong>CollegeFootballData.com</strong>. CFBD supplies the upstream scaffolding for every team page on this site &mdash; canonical names, mascots, conference and division assignments, FBS and FCS classification, primary and alternate color values, and the logo references that give each program its visual signature. CFBD is also the backbone of the ranking inputs: schedules, results, and the play-level records that feed the model.</p>
  <p>Where CFBD is missing a logo variant &mdash; most often a dark-mode mark or a secondary wordmark &mdash; the <strong>ESPN content delivery network</strong> serves as a backstop. The selection is deterministic and documented in the build.{espn_cdn_note}</p>
  <p><strong>TheSportsDB</strong> is not in active use for NCAA football on this site. Their college-football coverage remains incomplete enough that relying on it would introduce inconsistency the editorial product cannot accept.</p>

  <h2>Marks and names</h2>
  <p>Team marks, logos, wordmarks, uniforms, and institutional names are the property of their respective universities, athletic departments, and conferences. The CFB Index reproduces them in the ordinary editorial and analytical manner &mdash; to identify the team a paragraph, table, or chart is discussing. No endorsement is claimed and none should be inferred.</p>

  <h2>See also</h2>
  <p>The methodology behind the numbers lives at <a href=\"../about-model/\">/about-model/</a>. The full index of pages lives at <a href=\"../\">the hub</a>.</p>

  <p class=\"back\"><a href=\"../\">&larr; back to hub</a></p>
</main>
</body>
</html>
"""
    espn_cdn_note = (
        " As of this build, one or more primary logos are sourced directly from the ESPN CDN."
        if espn_cdn_active
        else ""
    )
    html = html.replace("{espn_cdn_note}", espn_cdn_note)
    html = html.replace("__GLOBAL_TAGS__", _global_link_tags())
    (attributions_dir / "index.html").write_text(html, encoding="utf-8")


def build_static_site(db: Database, output_dir: str | Path = "output/site") -> Path:
    _report_progress(f"Building static site at {output_dir}...")
    summary, rankings = fetch_latest_rankings(db, limit=1000)
    site_root = Path(output_dir)
    site_root.mkdir(parents=True, exist_ok=True)
    _ensure_global_assets(site_root)
    _write_attributions_page(site_root, db=db)

    if summary is None or not rankings:
        (site_root / "index.html").write_text("<html><body><h1>No model runs found.</h1></body></html>", encoding="utf-8")
        _report_progress("No model runs found for static site.")
        return site_root

    latest_local_week = _latest_local_week(db, int(summary["season_year"]))
    _report_progress(
        f"Loaded snapshot season {summary['season_year']} week {summary['week']} with {len(rankings)} ranking rows."
    )
    historical_season_ledger = fetch_historical_season_ledger(db)
    _report_progress(f"Loaded {len(historical_season_ledger)} historical season rows.")
    historical_rows_by_team: dict[int, list[dict[str, Any]]] = {}
    for row in historical_season_ledger:
        historical_rows_by_team.setdefault(int(row["team_id"]), []).append(row)
    history_hub = build_history_hub(historical_season_ledger)
    current_rankings_by_team = {row.team_id: row for row in rankings}
    _report_progress("Building team pages...")
    team_pages = {
        row.slug: fetch_team_page_data(db, summary, row, historical_rows_by_team.get(row.team_id, []))
        for row in rankings
    }
    global _VALID_TEAM_SLUGS
    _VALID_TEAM_SLUGS = {str(slug) for slug in team_pages.keys()}
    _report_progress(f"Built {len(team_pages)} team pages.")
    _report_progress("Building program pages...")
    program_pages = {
        program_data["team"]["slug"]: program_data
        for team_id, rows in historical_rows_by_team.items()
        if rows
        for program_data in [fetch_program_page_data(db, summary, team_id, rows, current_rankings_by_team.get(team_id))]
    }
    program_explorer_rows = build_program_explorer_rows(list(program_pages.values()))
    _report_progress(f"Built {len(program_pages)} program pages.")
    _report_progress("Building player and Heisman pages...")
    heisman_snapshot = fetch_current_heisman_snapshot(db, summary)
    player_directory_rows = fetch_player_directory_rows(db, summary, heisman_snapshot["week"])
    player_pages = build_player_page_data_map(db, summary, player_directory_rows)
    featured_team_pages = [team_pages[row.slug] for row in rankings if row.slug in team_pages]
    _attach_team_page_context(featured_team_pages)
    _report_progress(
        f"Built {len(player_pages)} player pages and prepared {len(featured_team_pages)} featured team snapshots."
    )
    _report_progress("Building archive and conference context...")
    archive_snapshots = fetch_snapshot_summaries(db)
    archive_rankings: dict[str, list[RankingRow]] = {}
    previous_by_season: dict[int, str] = {}
    for snapshot in reversed(archive_snapshots):
        snapshot_rankings = _fetch_rankings_for_summary(db, snapshot, limit=1000)
        previous_slug = previous_by_season.get(int(snapshot["season_year"]))
        if previous_slug:
            _attach_rank_changes(snapshot_rankings, archive_rankings[previous_slug])
        archive_rankings[str(snapshot["slug"])] = snapshot_rankings
        previous_by_season[int(snapshot["season_year"])] = str(snapshot["slug"])
    site_pulse = fetch_site_pulse(db, summary, rankings=rankings)
    conference_pages = build_conference_pages(featured_team_pages)
    _report_progress(
        f"Prepared {len(archive_snapshots)} archive snapshots and {len(conference_pages)} conference pages."
    )

    team_index = build_team_index(rankings, featured_team_pages)
    fan_intel_board = fetch_fan_intel_board(
        db,
        season_year=int(summary["season_year"]),
        week=int(summary["week"]),
        team_index=team_index,
    )
    _report_progress(
        "Fan intelligence board built with "
        f"{sum(len(fan_intel_board.get(k) or []) for k in ('vibe_shifts','respect_gap_leaders','rival_heat_leaders','main_characters','panicked_fanbases','polarized'))} rows."
    )

    _report_progress("Writing home, rankings, and history pages...")
    (site_root / "index.html").write_text(
        render_home_html(
            summary,
            rankings,
            featured_team_pages,
            latest_local_week,
            site_pulse,
            history_hub,
            conference_pages,
            archive_snapshots[:6],
            archive_rankings,
            fan_intel_board,
        ),
        encoding="utf-8",
    )

    rankings_dir = site_root / "rankings"
    rankings_dir.mkdir(parents=True, exist_ok=True)
    (rankings_dir / "index.html").write_text(
        render_rankings_page_html(summary, rankings, latest_local_week, featured_team_pages, history_hub),
        encoding="utf-8",
    )

    history_dir = site_root / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    (history_dir / "index.html").write_text(
        render_history_index_html(summary, history_hub, site_pulse),
        encoding="utf-8",
    )

    about_dir = site_root / "about-model"
    about_dir.mkdir(parents=True, exist_ok=True)
    (about_dir / "index.html").write_text(render_about_model_html(summary, site_pulse), encoding="utf-8")

    _report_progress("Writing matchup and compare pages...")
    matchups_dir = site_root / "matchups"
    matchups_dir.mkdir(parents=True, exist_ok=True)
    (matchups_dir / "index.html").write_text(
        render_matchups_page_html(summary, featured_team_pages, site_pulse, fan_intel_board),
        encoding="utf-8",
    )

    compare_dir = site_root / "compare"
    compare_dir.mkdir(parents=True, exist_ok=True)
    for existing_file in compare_dir.glob("*.html"):
        _safe_unlink_generated_file(existing_file)
    (compare_dir / "index.html").write_text(
        render_compare_page_html(summary, featured_team_pages, site_pulse),
        encoding="utf-8",
    )

    archive_dir = site_root / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for existing_file in archive_dir.glob("*.html"):
        _safe_unlink_generated_file(existing_file)
    _report_progress("Writing archive pages...")
    (archive_dir / "index.html").write_text(
        render_archive_index_html(summary, archive_snapshots, archive_rankings),
        encoding="utf-8",
    )
    for index, snapshot in enumerate(archive_snapshots):
        newer_snapshot = archive_snapshots[index - 1] if index > 0 else None
        older_snapshot = archive_snapshots[index + 1] if index + 1 < len(archive_snapshots) else None
        (archive_dir / f"{snapshot['slug']}.html").write_text(
            render_archive_snapshot_html(
                snapshot,
                archive_rankings.get(str(snapshot["slug"]), []),
                newer_snapshot,
                older_snapshot,
                current_season_year=int(summary["season_year"]),
            ),
            encoding="utf-8",
        )

    conferences_dir = site_root / "conferences"
    conferences_dir.mkdir(parents=True, exist_ok=True)
    for existing_file in conferences_dir.glob("*.html"):
        _safe_unlink_generated_file(existing_file)
    _report_progress("Writing conference pages...")
    (conferences_dir / "index.html").write_text(
        render_conferences_index_html(summary, conference_pages, site_pulse),
        encoding="utf-8",
    )
    for conference_page in conference_pages:
        (conferences_dir / f"{conference_page['slug']}.html").write_text(
            render_conference_page_html(summary, conference_page),
            encoding="utf-8",
        )

    programs_dir = site_root / "programs"
    programs_dir.mkdir(parents=True, exist_ok=True)
    for existing_file in programs_dir.glob("*.html"):
        _safe_unlink_generated_file(existing_file)
    _report_progress("Writing program pages...")
    (programs_dir / "index.html").write_text(
        render_programs_index_html(summary, program_explorer_rows, history_hub, site_pulse),
        encoding="utf-8",
    )
    for slug, program_data in program_pages.items():
        (programs_dir / f"{slug}.html").write_text(render_program_page_html(summary, program_data), encoding="utf-8")

    heisman_dir = site_root / "heisman"
    heisman_dir.mkdir(parents=True, exist_ok=True)
    for existing_file in heisman_dir.glob("*.html"):
        _safe_unlink_generated_file(existing_file)
    _report_progress("Writing Heisman pages...")
    heisman_team_conference_map: dict[str, str] = {}
    for row in db.query_all(
        """
        select
          t.slug,
          t.canonical_name as team_name,
          c.conference_name
        from teams t
        left join conferences c on c.conference_id = t.current_conference_id
        where t.level_code = 'FBS'
          and t.is_active = 1
        """
    ):
        conference_name = str(row.get("conference_name") or "").strip()
        if not conference_name:
            continue
        heisman_team_conference_map[f"slug:{row['slug']}"] = conference_name
        heisman_team_conference_map[f"name:{str(row['team_name']).lower()}"] = conference_name
    (heisman_dir / "index.html").write_text(
        render_heisman_page_html(summary, heisman_snapshot, player_directory_rows, heisman_team_conference_map),
        encoding="utf-8",
    )

    players_dir = site_root / "players"
    players_dir.mkdir(parents=True, exist_ok=True)
    for existing_file in players_dir.glob("*.html"):
        _safe_unlink_generated_file(existing_file)
    _report_progress("Writing player pages...")
    (players_dir / "index.html").write_text(
        render_players_index_html(summary, player_directory_rows, heisman_snapshot),
        encoding="utf-8",
    )
    for player_slug, player_data in player_pages.items():
        (players_dir / f"{player_slug}.html").write_text(
            render_player_page_html(summary, player_data),
            encoding="utf-8",
        )

    teams_dir = site_root / "teams"
    teams_dir.mkdir(parents=True, exist_ok=True)
    for existing_file in teams_dir.glob("*.html"):
        _safe_unlink_generated_file(existing_file)
    (teams_dir / "index.html").write_text(
        render_teams_index_html(summary, rankings),
        encoding="utf-8",
    )

    # Fan Intelligence Hub v5 — attach each team's archetype classification so
    # the team-page render can drop in the archetype module in place of the
    # "Awaiting Signal" fallback when no mood signal is available.
    try:
        from cfb_rankings.hub_page import (
            fetch_team_classification,
            fetch_modifier_lookup,
            render_team_archetype_module,
        )
        from cfb_rankings.ingest.archetypes import fetch_migration_sparkline

        modifier_lookup = fetch_modifier_lookup(db)
        for slug, team_data in team_pages.items():
            ranking = team_data.get("ranking")
            if ranking is None:
                continue
            classification = fetch_team_classification(
                db,
                team_id=int(ranking.team_id),
                season_year=int(summary["season_year"]),
            )
            migration = fetch_migration_sparkline(db, team_id=int(ranking.team_id), seasons=5)
            team_data["archetype_module_html"] = render_team_archetype_module(
                classification, migration, modifier_lookup,
            )
    except Exception as exc:
        _report_progress(f"Could not attach archetype modules to team pages: {exc}")

    _report_progress("Writing team season pages...")
    for slug, team_data in team_pages.items():
        (teams_dir / f"{slug}.html").write_text(render_team_page_html(summary, team_data), encoding="utf-8")
        ranking = team_data.get("ranking")
        season_summary = team_data.get("season_summary") or {}
        if ranking is not None:
            wins = int(season_summary.get("wins") or 0)
            losses = int(season_summary.get("losses") or 0)
            (teams_dir / f"{slug}-og.svg").write_text(
                _render_og_image_svg(
                    eyebrow=f"{ranking.level_code} · {ranking.conference_name or 'Independent'}",
                    headline=str(ranking.team_name),
                    subline=f"#{ranking.rank} · {wins}-{losses} · Power {_public_power_text(ranking.power_display)}",
                    slug=slug,
                    site_root=site_root,
                ),
                encoding="utf-8",
            )

    season_year_value = int(summary["season_year"])
    (site_root / "og-image.svg").write_text(
        _render_og_image_svg(
            eyebrow=f"{season_year_value} Season",
            headline="THE CFB INDEX",
            subline="Power · Resume · Mood · Model",
        ),
        encoding="utf-8",
    )

    # Fan Intelligence Hub v5 — magazine-style weekly issue page.
    _report_progress("Writing Fan Intelligence Hub page...")
    try:
        from cfb_rankings.hub_page import build_hub_page

        hub_path = build_hub_page(
            db,
            output_dir=site_root,
            issue_number="N\u00b0 047",
            week_start="2026-04-22",
            season_year=season_year_value,
        )
        _report_progress(f"Hub page written to {hub_path}.")
    except Exception as exc:
        _report_progress(f"Hub page build skipped: {exc}")

    # Player-scope discovery boards — small, cheap to regenerate, and the
    # only way readers find the players with live Room or Signature Story
    # cards under a 17k-page index.
    try:
        from cfb_rankings.the_room_board import build_the_room_board
        the_room_path = build_the_room_board(
            db, output_dir=site_root, season_year=season_year_value,
        )
        _report_progress(f"The Room board written to {the_room_path}.")
    except Exception as exc:
        _report_progress(f"The Room board build skipped: {exc}")
    try:
        from cfb_rankings.signature_story_board import build_signature_story_board
        ss_path = build_signature_story_board(
            db, output_dir=site_root, season_year=season_year_value,
        )
        _report_progress(f"Signature Stories board written to {ss_path}.")
    except Exception as exc:
        _report_progress(f"Signature Stories board build skipped: {exc}")
    try:
        from cfb_rankings.players_landing import build_players_landing
        landing_path = build_players_landing(
            db, output_dir=site_root, season_year=season_year_value,
        )
        _report_progress(f"Players spotlight landing written to {landing_path}.")
    except Exception as exc:
        _report_progress(f"Players landing build skipped: {exc}")

    _report_progress(f"Static site build finished at {site_root}.")
    return site_root


_VALID_TEAM_SLUGS: set[str] = set()


def _team_link(prefix: str, slug: str | None, label: str, css_class: str = "team-link", extra: str = "") -> str:
    slug_str = str(slug or "").strip()
    escaped_label = escape(label)
    extra_html = f" {extra}" if extra else ""
    if slug_str and (not _VALID_TEAM_SLUGS or slug_str in _VALID_TEAM_SLUGS):
        return f'<a class="{css_class}" href="{prefix}{escape(slug_str)}.html">{escaped_label}</a>{extra_html}'
    return f'<span class="{css_class} is-unlinked">{escaped_label}</span>{extra_html}'


def audit_site_links(site_dir: str | Path = "output/site") -> list[dict[str, str]]:
    """Walk the built site and return a list of broken internal href targets.

    Strips <script> and <style> blocks before extracting hrefs so client-side
    template literals (e.g. ${varName}) do not register as real links. External
    links (http/https/mailto/tel), anchors, and data URIs are skipped; only
    internal .html paths are resolved against the file's location and checked.
    """
    root = Path(site_dir).resolve()
    if not root.exists():
        return [{"file": str(root), "href": "", "reason": "site directory does not exist"}]
    html_files = list(root.rglob("*.html"))
    broken: list[dict[str, str]] = []
    script_style_re = re.compile(r"<(?:script|style)\b[\s\S]*?</(?:script|style)>", re.IGNORECASE)
    href_re = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
    skip_prefixes = ("http://", "https://", "mailto:", "tel:", "javascript:", "data:", "#")
    for path in html_files:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            broken.append({"file": str(path), "href": "", "reason": f"read error: {exc}"})
            continue
        clean = script_style_re.sub(" ", raw)
        for match in href_re.finditer(clean):
            raw_href = match.group(1).strip()
            if not raw_href:
                broken.append({"file": str(path.relative_to(root)), "href": raw_href, "reason": "empty href"})
                continue
            if raw_href.startswith(skip_prefixes):
                continue
            href, _, _ = raw_href.partition("#")
            href, _, _ = href.partition("?")
            if not href:
                continue
            if re.search(r"/\.html$", href) or href.endswith("/.html"):
                broken.append({"file": str(path.relative_to(root)), "href": raw_href, "reason": "empty-slug .html"})
                continue
            if not href.endswith(".html"):
                continue
            target = (path.parent / href).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                broken.append({"file": str(path.relative_to(root)), "href": raw_href, "reason": "escapes site root"})
                continue
            if not target.exists():
                broken.append({"file": str(path.relative_to(root)), "href": raw_href, "reason": "target missing"})
    return broken


def _safe_unlink_generated_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except PermissionError:
        # On Windows the in-app browser or another preview process can briefly lock
        # a generated file. We still overwrite all active generated pages below, so
        # skipping deletion is better than aborting the entire publish step.
        return


def _report_progress(message: str) -> None:
    print(f"[publish][{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def fetch_team_page_data(
    db: Database,
    summary: dict[str, Any],
    ranking: RankingRow,
    historical_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    season_year = int(summary["season_year"])
    model_run_id = int(summary["model_run_id"])
    team_row = db.query_one(
        """
        select
          t.team_id,
          t.slug,
          t.canonical_name,
          t.school_name,
          t.short_name,
          coalesce(ts.level_code, t.level_code) as level_code,
          c.conference_name
        from teams t
        left join team_seasons ts
          on ts.team_id = t.team_id
         and ts.season_year = %(season_year)s
        left join conferences c on c.conference_id = ts.conference_id
        where t.team_id = %(team_id)s
        """,
        {"team_id": ranking.team_id, "season_year": season_year},
    ) or {}

    season_summary = db.query_one(
        """
        select
          sum(case
                when g.home_team_id = %(team_id)s and coalesce(g.home_points, -999) > coalesce(g.away_points, -999) then 1
                when g.away_team_id = %(team_id)s and coalesce(g.away_points, -999) > coalesce(g.home_points, -999) then 1
                else 0
              end) as wins,
          sum(case
                when g.home_team_id = %(team_id)s and coalesce(g.home_points, -999) < coalesce(g.away_points, -999) then 1
                when g.away_team_id = %(team_id)s and coalesce(g.away_points, -999) < coalesce(g.home_points, -999) then 1
                else 0
              end) as losses,
          sum(case
                when g.home_team_id = %(team_id)s then coalesce(g.home_points, 0)
                when g.away_team_id = %(team_id)s then coalesce(g.away_points, 0)
                else 0
              end) as points_for,
          sum(case
                when g.home_team_id = %(team_id)s then coalesce(g.away_points, 0)
                when g.away_team_id = %(team_id)s then coalesce(g.home_points, 0)
                else 0
              end) as points_against
        from games g
        where g.season_year = %(season_year)s
          and (%(team_id)s in (g.home_team_id, g.away_team_id))
        """,
        {"team_id": ranking.team_id, "season_year": season_year},
    ) or {}

    schedule_rows = db.query_all(
        """
        select
          g.game_id,
          g.week,
          g.season_phase,
          g.start_time_utc,
          g.status,
          home.team_id as home_team_id,
          home.slug as home_slug,
          home.canonical_name as home_team_name,
          away.team_id as away_team_id,
          away.slug as away_slug,
          away.canonical_name as away_team_name,
          g.home_points,
          g.away_points,
          coalesce(opp_season.level_code, opp.level_code) as opponent_level_code,
          opp_conf.conference_name as opponent_conference_name,
          gl.provider as line_provider,
          gl.spread_home_close,
          gl.total_close,
          gl.moneyline_home_close,
          gl.moneyline_away_close,
          td.power_delta,
          td.pregame_power,
          td.postgame_power,
          td.resume_delta
        from games g
        join teams home on home.team_id = g.home_team_id
        join teams away on away.team_id = g.away_team_id
        join teams opp on opp.team_id = case when g.home_team_id = %(team_id)s then g.away_team_id else g.home_team_id end
        left join team_seasons opp_season
          on opp_season.team_id = opp.team_id
         and opp_season.season_year = g.season_year
        left join conferences opp_conf on opp_conf.conference_id = opp_season.conference_id
        left join team_rating_deltas td
          on td.game_id = g.game_id
         and td.team_id = %(team_id)s
         and td.model_run_id = %(model_run_id)s
        left join game_lines gl on gl.game_id = g.game_id
        where g.season_year = %(season_year)s
          and %(team_id)s in (g.home_team_id, g.away_team_id)
        order by g.week asc, g.start_time_utc asc, g.game_id asc
        """,
        {"team_id": ranking.team_id, "season_year": season_year, "model_run_id": model_run_id},
    )

    history_rows = sorted(
        list(historical_rows or []),
        key=lambda row: int(row.get("season_year") or 0),
        reverse=True,
    )

    phase_rows = db.query_all(
        """
        select
          coalesce(g.season_phase, 'regular season') as season_phase,
          count(*) as games_played,
          sum(case
                when g.home_team_id = %(team_id)s and coalesce(g.home_points, -999) > coalesce(g.away_points, -999) then 1
                when g.away_team_id = %(team_id)s and coalesce(g.away_points, -999) > coalesce(g.home_points, -999) then 1
                else 0
              end) as wins,
          sum(case
                when g.home_team_id = %(team_id)s and coalesce(g.home_points, -999) < coalesce(g.away_points, -999) then 1
                when g.away_team_id = %(team_id)s and coalesce(g.away_points, -999) < coalesce(g.home_points, -999) then 1
                else 0
              end) as losses
        from games g
        where g.season_year = %(season_year)s
          and %(team_id)s in (g.home_team_id, g.away_team_id)
        group by coalesce(g.season_phase, 'regular season')
        order by games_played desc, season_phase asc
        """,
        {"team_id": ranking.team_id, "season_year": season_year},
    )

    efficiency_rows = db.query_all(
        """
        select metric_name, adjusted_value, percentile, sample_size
        from opponent_adjusted_team_week
        where season_year = %(season_year)s
          and week = %(week)s
          and team_id = %(team_id)s
          and model_version = %(model_version)s
        """,
        {
            "season_year": season_year,
            "week": int(summary["week"]),
            "team_id": ranking.team_id,
            "model_version": str(summary["model_version"]),
        },
    )

    rating_snapshot = db.query_one(
        """
        select
          p.offense_rating,
          p.defense_rating,
          p.special_teams_rating,
          p.tempo_rating,
          p.posterior_sd,
          p.cross_level_confidence,
          p.schedule_connectivity,
          r.record_strength_score,
          r.performance_over_expectation_score,
          r.result_quality_score,
          r.best_win_score,
          r.worst_loss_score,
          r.schedule_strength_score
        from power_ratings_weekly p
        left join resume_ratings_weekly r
          on r.model_run_id = p.model_run_id
         and r.team_id = p.team_id
         and r.week = p.week
        where p.model_run_id = %(model_run_id)s
          and p.week = %(week)s
          and p.team_id = %(team_id)s
        """,
        {
            "model_run_id": model_run_id,
            "week": int(summary["week"]),
            "team_id": ranking.team_id,
        },
    ) or {}

    journey_points = _build_team_journey_points(ranking.team_id, schedule_rows)
    trend_points = []
    rating_path = []
    for row in schedule_rows:
        pre = row.get("pregame_power")
        post = row.get("postgame_power")
        delta = row.get("power_delta")
        if pre is not None:
            rating_path.append(float(pre))
        if post is not None:
            rating_path.append(float(post))
        trend_points.append(
            {
                "week": int(row["week"] or 0),
                "delta": None if delta is None else float(delta),
                "post": None if post is None else float(post),
            }
        )

    efficiency_metric_map = _efficiency_metric_map(efficiency_rows)
    efficiency_snapshot = _efficiency_snapshot(efficiency_rows)
    history_insights = build_team_history_insights(history_rows, season_year)
    history_profile = build_team_history_profile(history_rows, season_year)
    similarity_cards = _build_similarity_cards(
        db=db,
        summary=summary,
        ranking=ranking,
        season_summary=season_summary,
        rating_snapshot=rating_snapshot,
        efficiency_metric_map=efficiency_metric_map,
    )
    betting_summary = _summarize_team_betting(ranking.team_id, schedule_rows)

    mood_profile = fetch_team_mood_profile(
        db,
        team_id=ranking.team_id,
        season_year=season_year,
        week=int(summary["week"]),
        context=MoodContext(
            team_id=ranking.team_id,
            power_percentile=ranking.power_percentile,
            resume_percentile=ranking.resume_percentile,
        ),
    )
    cohort_rows = _fetch_cohort_rows_for_team(db, ranking.team_id)

    return {
        "ranking": ranking,
        "team": team_row,
        "season_summary": season_summary,
        "schedule": schedule_rows,
        "history": history_rows,
        "history_insights": history_insights,
        "history_profile": history_profile,
        "phase_summary": phase_rows,
        "efficiency_snapshot": efficiency_snapshot,
        "journey_points": journey_points,
        "trend_points": trend_points,
        "rating_path": rating_path,
        "rating_snapshot": rating_snapshot,
        "similarity_cards": similarity_cards,
        "betting_summary": betting_summary,
        "mood_profile": mood_profile,
        "cohort_rows": cohort_rows,
    }


def fetch_program_page_data(
    db: Database,
    summary: dict[str, Any],
    team_id: int,
    historical_rows: list[dict[str, Any]],
    current_ranking: RankingRow | None = None,
) -> dict[str, Any]:
    season_year = int(summary["season_year"])
    ordered_history = sorted(
        list(historical_rows or []),
        key=lambda row: int(row.get("season_year") or 0),
        reverse=True,
    )
    team_row = db.query_one(
        """
        select
          t.team_id,
          t.slug,
          t.canonical_name,
          t.school_name,
          t.short_name,
          coalesce(ts.level_code, t.level_code) as level_code,
          c.conference_name
        from teams t
        left join team_seasons ts
          on ts.team_id = t.team_id
         and ts.season_year = %(season_year)s
        left join conferences c on c.conference_id = ts.conference_id
        where t.team_id = %(team_id)s
        """,
        {"team_id": team_id, "season_year": season_year},
    ) or {}
    if ordered_history:
        latest_history_row = ordered_history[0]
        if not team_row.get("conference_name"):
            team_row["conference_name"] = latest_history_row.get("conference_name")
        if not team_row.get("level_code"):
            team_row["level_code"] = latest_history_row.get("level_code")

    history_insights = build_team_history_insights(ordered_history, season_year)
    history_profile = build_team_history_profile(ordered_history, season_year)
    conference_timeline = build_program_conference_timeline(ordered_history)

    latest_row = history_profile.get("current_row") or (ordered_history[0] if ordered_history else {})
    latest_season_year = int(latest_row.get("season_year") or 0)
    latest_record = f"{int(latest_row.get('wins') or 0)}-{int(latest_row.get('losses') or 0)}" if latest_row else "--"
    current_season_url = None if current_ranking is None else f"../teams/{escape(current_ranking.slug)}.html"
    return {
        "team": team_row,
        "history": ordered_history,
        "history_insights": history_insights,
        "history_profile": history_profile,
        "conference_timeline": conference_timeline,
        "current_ranking": current_ranking,
        "current_season_url": current_season_url,
        "latest_season_year": latest_season_year,
        "latest_record": latest_record,
    }


def build_program_conference_timeline(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not history_rows:
        return {
            "segments": [],
            "realignment_count": 0,
            "latest_conference": None,
        }
    ordered = sorted(history_rows, key=lambda row: int(row.get("season_year") or 0))
    segments: list[dict[str, Any]] = []
    current_segment: dict[str, Any] | None = None
    for row in ordered:
        season_year = int(row.get("season_year") or 0)
        level_code = str(row.get("level_code") or "")
        conference_name = _clean_conference_name(
            str(row.get("conference_name") or f"{level_code} Independents")
        )
        if (
            current_segment
            and current_segment["conference_name"] == conference_name
            and current_segment["level_code"] == level_code
            and season_year == int(current_segment["end_season"]) + 1
        ):
            current_segment["end_season"] = season_year
            current_segment["season_count"] = int(current_segment["season_count"]) + 1
            continue
        if current_segment is not None:
            segments.append(current_segment)
        current_segment = {
            "conference_name": conference_name,
            "level_code": level_code,
            "start_season": season_year,
            "end_season": season_year,
            "season_count": 1,
        }
    if current_segment is not None:
        segments.append(current_segment)
    return {
        "segments": list(reversed(segments)),
        "realignment_count": max(0, len(segments) - 1),
        "latest_conference": segments[-1]["conference_name"] if segments else None,
    }


def build_program_explorer_rows(program_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    explorer_rows: list[dict[str, Any]] = []
    for program_data in program_pages:
        team = program_data.get("team") or {}
        history = program_data.get("history") or []
        history_profile = program_data.get("history_profile") or {}
        if not history:
            continue

        latest_row = history_profile.get("current_row") or history[0]
        peak_power_row = history_profile.get("peak_power_row") or {}
        best_resume_row = history_profile.get("best_resume_row") or {}
        best_finish_row = history_profile.get("best_finish_row") or {}
        power_rows = [row for row in history if row.get("end_power") is not None]
        average_end_power = (
            sum(float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0) for row in power_rows) / len(power_rows)
            if power_rows
            else None
        )
        power_range = (
            max(float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0) for row in power_rows)
            - min(float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0) for row in power_rows)
            if len(power_rows) >= 2
            else 0.0
        )
        current_ranking: RankingRow | None = program_data.get("current_ranking")
        level_code = str(latest_row.get("level_code") or team.get("level_code") or "")
        conference_name = _clean_conference_name(
            str(latest_row.get("conference_name") or team.get("conference_name") or f"{level_code} Independents")
        )
        explorer_rows.append(
            {
                "team_id": int(team.get("team_id") or latest_row.get("team_id") or 0),
                "slug": str(team.get("slug") or latest_row.get("slug") or ""),
                "team_name": str(team.get("canonical_name") or latest_row.get("team_name") or ""),
                "level_code": level_code,
                "conference_name": conference_name,
                "loaded_seasons": int(history_profile.get("loaded_seasons") or len(history)),
                "latest_season_year": int(latest_row.get("season_year") or 0),
                "latest_record": f"{int(latest_row.get('wins') or 0)}-{int(latest_row.get('losses') or 0)}",
                "latest_end_power": None if latest_row.get("end_power") is None else float(latest_row.get("end_power") or 0.0),
                "latest_end_resume": None if latest_row.get("end_resume") is None else float(latest_row.get("end_resume") or 0.0),
                "latest_end_power_display": None if latest_row.get("end_power_display") is None else float(latest_row.get("end_power_display") or 0.0),
                "latest_end_resume_display": None if latest_row.get("end_resume_display") is None else float(latest_row.get("end_resume_display") or 0.0),
                "latest_final_rank": None if latest_row.get("final_rank") is None else int(latest_row.get("final_rank") or 0),
                "peak_power": None if not peak_power_row else float(peak_power_row.get("end_power") or 0.0),
                "peak_power_display": None if not peak_power_row or peak_power_row.get("end_power_display") is None else float(peak_power_row.get("end_power_display") or 0.0),
                "peak_power_year": None if not peak_power_row else int(peak_power_row.get("season_year") or 0),
                "best_resume": None if not best_resume_row else float(best_resume_row.get("end_resume") or 0.0),
                "best_resume_display": None if not best_resume_row or best_resume_row.get("end_resume_display") is None else float(best_resume_row.get("end_resume_display") or 0.0),
                "best_resume_year": None if not best_resume_row else int(best_resume_row.get("season_year") or 0),
                "best_finish": None if not best_finish_row else int(best_finish_row.get("final_rank") or 0),
                "best_finish_year": None if not best_finish_row else int(best_finish_row.get("season_year") or 0),
                "average_end_power": average_end_power,
                "current_vs_baseline": history_profile.get("current_vs_baseline"),
                "gap_to_peak_power": history_profile.get("gap_to_peak_power"),
                "power_range": power_range,
                "current_rank": None if current_ranking is None else int(current_ranking.rank),
                "current_season_url": program_data.get("current_season_url"),
            }
        )
    explorer_rows.sort(
        key=lambda row: (
            row.get("current_rank") is None,
            row.get("current_rank") or 9999,
            -(float(row.get("latest_end_power") or -999.0)),
            str(row.get("team_name") or ""),
        )
    )
    return explorer_rows


def build_history_explorer_rows(
    historical_season_ledger: list[dict[str, Any]],
    current_season_year: int,
) -> list[dict[str, Any]]:
    if not historical_season_ledger:
        return []

    rows_by_team: dict[int, list[dict[str, Any]]] = {}
    for row in historical_season_ledger:
        rows_by_team.setdefault(int(row.get("team_id") or 0), []).append(row)

    history_profiles = {
        team_id: build_team_history_profile(rows, current_season_year)
        for team_id, rows in rows_by_team.items()
    }

    explorer_rows: list[dict[str, Any]] = []
    for row in historical_season_ledger:
        team_id = int(row.get("team_id") or 0)
        history_profile = history_profiles.get(team_id) or {}
        lens_label, lens_body = _render_history_row_context(row, history_profile)
        conference_name = _clean_conference_name(
            str(row.get("conference_name") or f"{row.get('level_code') or ''} Independents")
        )
        season_year = int(row.get("season_year") or 0)
        slug = str(row.get("slug") or "")
        explorer_rows.append(
            {
                "team_id": team_id,
                "team_name": str(row.get("team_name") or ""),
                "slug": slug,
                "season_year": season_year,
                "level_code": str(row.get("level_code") or ""),
                "conference_name": conference_name,
                "record": f"{int(row.get('wins') or 0)}-{int(row.get('losses') or 0)}",
                "wins": int(row.get("wins") or 0),
                "losses": int(row.get("losses") or 0),
                "games_played": int(row.get("games_played") or 0),
                "margin": int(row.get("margin") or 0),
                "win_pct": float(row.get("win_pct") or 0.0),
                "end_power": _first_present_float(row.get("end_power_display"), row.get("end_power")),
                "end_resume": _first_present_float(row.get("end_resume_display"), row.get("end_resume")),
                "final_rank": None if row.get("final_rank") is None else int(row.get("final_rank") or 0),
                "lens_label": lens_label,
                "lens_body": lens_body,
                "program_url": f"../programs/{slug}.html" if slug else None,
                "season_url": f"../teams/{slug}.html" if slug and season_year == current_season_year else None,
            }
        )

    explorer_rows.sort(
        key=lambda row: (
            -int(row.get("season_year") or 0),
            row.get("final_rank") is None,
            row.get("final_rank") or 9999,
            -(float(row.get("end_power") or -999.0)),
            str(row.get("team_name") or "").lower(),
        )
    )
    return explorer_rows


def fetch_current_heisman_snapshot(db: Database, summary: dict[str, Any]) -> dict[str, Any]:
    season_year = int(summary["season_year"])
    week_row = db.query_one(
        """
        select max(week) as week
        from heisman_rankings_weekly
        where season_year = %(season_year)s
        """,
        {"season_year": season_year},
    ) or {}
    week = None if week_row.get("week") is None else int(week_row["week"])
    rows = db.query_all(
        """
        with latest_rows as (
          select player_id, max(heisman_ranking_id) as heisman_ranking_id
          from heisman_rankings_weekly
          where season_year = %(season_year)s
            and week = %(week)s
          group by player_id
        )
        select
          h.player_id,
          h.team_id,
          h.season_year,
          h.week,
          h.rank_overall,
          h.nowcast_rank,
          h.forecast_rank,
          h.win_probability,
          h.finalist_probability,
          h.any_ballot_probability,
          h.expected_ballot_share,
          h.latent_score,
          h.market_implied_probability,
          h.market_american_odds,
          h.market_provider,
          p.full_name,
          coalesce(re.position, p.position) as position,
          re.class_year,
          t.slug as team_slug,
          t.canonical_name as team_name,
          c.conference_name
        from latest_rows latest
        join heisman_rankings_weekly h on h.heisman_ranking_id = latest.heisman_ranking_id
        join players p on p.player_id = h.player_id
        left join teams t on t.team_id = h.team_id
        left join team_seasons ts
          on ts.team_id = h.team_id
         and ts.season_year = h.season_year
        left join conferences c on c.conference_id = ts.conference_id
        left join roster_entries re
          on re.player_id = h.player_id
         and re.team_id = h.team_id
         and re.season_year = h.season_year
        order by
          coalesce(h.rank_overall, h.nowcast_rank, h.forecast_rank, 999999) asc,
          h.win_probability desc,
          lower(p.full_name) asc
        """,
        {"season_year": season_year, "week": -1 if week is None else week},
    )
    board_rows: list[HeismanRankingRow] = []
    for index, row in enumerate(rows, start=1):
        full_name = str(row.get("full_name") or "Player")
        board_rows.append(
            HeismanRankingRow(
                overall_rank=int(row.get("rank_overall") or row.get("nowcast_rank") or row.get("forecast_rank") or index),
                player_id=int(row["player_id"]),
                player_slug=_player_slug(int(row["player_id"]), full_name),
                full_name=full_name,
                team_id=None if row.get("team_id") is None else int(row["team_id"]),
                team_slug=None if row.get("team_slug") is None else str(row["team_slug"]),
                team_name=None if row.get("team_name") is None else str(row["team_name"]),
                conference_name=None
                if row.get("conference_name") is None
                else _clean_conference_name(str(row["conference_name"])),
                position=None if row.get("position") is None else str(row["position"]),
                class_year=None if row.get("class_year") is None else str(row["class_year"]),
                season_year=int(row.get("season_year") or season_year),
                week=int(row.get("week") or week or 0),
                nowcast_rank=None if row.get("nowcast_rank") is None else int(row["nowcast_rank"]),
                forecast_rank=None if row.get("forecast_rank") is None else int(row["forecast_rank"]),
                win_probability=None
                if row.get("win_probability") is None
                else float(row["win_probability"]),
                finalist_probability=None
                if row.get("finalist_probability") is None
                else float(row["finalist_probability"]),
                any_ballot_probability=None
                if row.get("any_ballot_probability") is None
                else float(row["any_ballot_probability"]),
                expected_ballot_share=None
                if row.get("expected_ballot_share") is None
                else float(row["expected_ballot_share"]),
                latent_score=None if row.get("latent_score") is None else float(row["latent_score"]),
                market_implied_probability=None
                if row.get("market_implied_probability") is None
                else float(row["market_implied_probability"]),
                market_american_odds=None
                if row.get("market_american_odds") is None
                else int(row["market_american_odds"]),
                market_provider=None if row.get("market_provider") is None else str(row["market_provider"]),
            )
        )
    return {
        "season_year": season_year,
        "week": week,
        "rows": board_rows,
        "has_market_data": any(
            row.market_implied_probability is not None
            or row.market_american_odds is not None
            or bool(row.market_provider)
            for row in board_rows
        ),
    }


def fetch_player_directory_rows(
    db: Database,
    summary: dict[str, Any],
    heisman_week: int | None = None,
) -> list[dict[str, Any]]:
    season_year = int(summary["season_year"])
    rows = db.query_all(
        """
        with current_roster as (
          select re.*
          from roster_entries re
          join (
            select player_id, max(roster_entry_id) as roster_entry_id
            from roster_entries
            where season_year = %(season_year)s
            group by player_id
          ) latest on latest.roster_entry_id = re.roster_entry_id
        ),
        fbs_roster as (
          select
            re.player_id,
            re.team_id,
            re.season_year,
            re.position,
            re.class_year,
            re.jersey,
            re.height_inches,
            re.weight_lbs,
            coalesce(re.hometown, p.hometown) as hometown,
            coalesce(re.home_state, p.home_state) as home_state,
            coalesce(ts.level_code, t.level_code) as level_code,
            c.conference_name
          from current_roster re
          join players p on p.player_id = re.player_id
          join teams t on t.team_id = re.team_id
          left join team_seasons ts
            on ts.team_id = re.team_id
           and ts.season_year = re.season_year
          left join conferences c on c.conference_id = ts.conference_id
          where coalesce(ts.level_code, t.level_code) = 'FBS'
        ),
        current_heisman as (
          select h.*
          from heisman_rankings_weekly h
          join (
            select player_id, max(heisman_ranking_id) as heisman_ranking_id
            from heisman_rankings_weekly
            where season_year = %(season_year)s
              and week = %(heisman_week)s
            group by player_id
          ) latest on latest.heisman_ranking_id = h.heisman_ranking_id
        )
        select
          p.player_id,
          p.full_name,
          p.first_name,
          p.last_name,
          coalesce(fr.position, p.position) as current_position,
          fr.class_year,
          fr.team_id,
          t.slug as team_slug,
          t.canonical_name as team_name,
          fr.conference_name,
          fr.jersey,
          fr.height_inches,
          fr.weight_lbs,
          fr.hometown,
          fr.home_state,
          coalesce(ch.rank_overall, ch.nowcast_rank, ch.forecast_rank) as current_heisman_rank,
          ch.nowcast_rank,
          ch.forecast_rank,
          ch.win_probability,
          ch.finalist_probability,
          ch.any_ballot_probability,
          ch.expected_ballot_share
        from players p
        left join fbs_roster fr on fr.player_id = p.player_id
        left join teams t on t.team_id = fr.team_id
        left join current_heisman ch on ch.player_id = p.player_id
        where fr.player_id is not null
           or exists (select 1 from heisman_rankings_weekly hw where hw.player_id = p.player_id)
           or exists (select 1 from heisman_vote_results hv where hv.player_id = p.player_id)
        order by
          case when coalesce(ch.rank_overall, ch.nowcast_rank, ch.forecast_rank) is null then 1 else 0 end,
          coalesce(ch.rank_overall, ch.nowcast_rank, ch.forecast_rank, 999999),
          lower(coalesce(t.canonical_name, '')),
          lower(p.full_name)
        """,
        {"season_year": season_year, "heisman_week": -1 if heisman_week is None else heisman_week},
    )
    player_rows: list[dict[str, Any]] = []
    for row in rows:
        player_id = int(row["player_id"])
        full_name = str(row.get("full_name") or "Player")
        player_rows.append(
            {
                **row,
                "player_id": player_id,
                "player_slug": _player_slug(player_id, full_name),
                "full_name": full_name,
                "conference_name": None
                if row.get("conference_name") is None
                else _clean_conference_name(str(row["conference_name"])),
                "current_heisman_rank": None
                if row.get("current_heisman_rank") is None
                else int(row["current_heisman_rank"]),
                "nowcast_rank": None if row.get("nowcast_rank") is None else int(row["nowcast_rank"]),
                "forecast_rank": None if row.get("forecast_rank") is None else int(row["forecast_rank"]),
                "win_probability": None
                if row.get("win_probability") is None
                else float(row["win_probability"]),
                "finalist_probability": None
                if row.get("finalist_probability") is None
                else float(row["finalist_probability"]),
                "any_ballot_probability": None
                if row.get("any_ballot_probability") is None
                else float(row["any_ballot_probability"]),
                "expected_ballot_share": None
                if row.get("expected_ballot_share") is None
                else float(row["expected_ballot_share"]),
            }
        )
    return player_rows


def build_player_page_data_map(
    db: Database,
    summary: dict[str, Any],
    player_directory_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    player_ids = [int(row["player_id"]) for row in player_directory_rows]
    if not player_ids:
        return {}
    current_season = int(summary["season_year"])

    # Precompute algorithmic Signature Stories (one cohort SQL per metric,
    # cached; cheap player-sql lookup per candidate). Only players with a
    # player_value_metrics row or WRs with >= 20 receptions get an entry.
    from cfb_rankings.signature_story import compute_signature_story_index
    try:
        algorithmic_signature_index = compute_signature_story_index(db, current_season)
    except Exception as exc:  # pragma: no cover — keep site build resilient
        print(f"[signature_story] precompute failed: {exc}; rendering skeletons.")
        algorithmic_signature_index = {}

    # Precompute "The Room on [Player]" mood profiles. Today this returns
    # an empty index because `player_week_conversation_features` has no rows;
    # every player page renders the Awaiting Signal shell until player-scope
    # extraction starts populating the aggregate.
    from cfb_rankings.fan_intelligence import compute_player_mood_index
    the_room_week = int(summary.get("week") or 0) or 1
    try:
        player_mood_index = compute_player_mood_index(db, current_season, the_room_week)
    except Exception as exc:  # pragma: no cover
        print(f"[the_room] precompute failed: {exc}; rendering skeletons.")
        player_mood_index = {}

    roster_history_rows = _query_rows_for_player_ids(
        db,
        """
        select
          re.player_id,
          re.season_year,
          re.team_id,
          t.slug as team_slug,
          t.canonical_name as team_name,
          c.conference_name,
          coalesce(ts.level_code, t.level_code) as level_code,
          coalesce(re.position, p.position) as position,
          re.class_year,
          re.jersey,
          re.height_inches,
          re.weight_lbs,
          coalesce(re.hometown, p.hometown) as hometown,
          coalesce(re.home_state, p.home_state) as home_state
        from roster_entries re
        join players p on p.player_id = re.player_id
        join teams t on t.team_id = re.team_id
        left join team_seasons ts
          on ts.team_id = re.team_id
         and ts.season_year = re.season_year
        left join conferences c on c.conference_id = ts.conference_id
        where re.player_id in ({placeholders})
        order by re.player_id asc, re.season_year desc, re.roster_entry_id desc
        """,
        player_ids,
    )
    heisman_history_rows = _query_rows_for_player_ids(
        db,
        """
        select
          h.player_id,
          h.season_year,
          h.week,
          h.team_id,
          t.slug as team_slug,
          t.canonical_name as team_name,
          c.conference_name,
          coalesce(re.position, p.position) as position,
          re.class_year,
          h.rank_overall,
          h.nowcast_rank,
          h.forecast_rank,
          h.win_probability,
          h.finalist_probability,
          h.any_ballot_probability,
          h.expected_ballot_share,
          h.latent_score,
          h.market_implied_probability,
          h.market_american_odds,
          h.market_provider
        from heisman_rankings_weekly h
        join players p on p.player_id = h.player_id
        left join teams t on t.team_id = h.team_id
        left join team_seasons ts
          on ts.team_id = h.team_id
         and ts.season_year = h.season_year
        left join conferences c on c.conference_id = ts.conference_id
        left join roster_entries re
          on re.player_id = h.player_id
         and re.team_id = h.team_id
         and re.season_year = h.season_year
        where h.player_id in ({placeholders})
        order by
          h.player_id asc,
          h.season_year desc,
          h.week desc,
          coalesce(h.rank_overall, h.nowcast_rank, h.forecast_rank, 999999) asc,
          h.heisman_ranking_id desc
        """,
        player_ids,
    )
    vote_history_rows = _query_rows_for_player_ids(
        db,
        """
        select
          hv.player_id,
          hv.season_year,
          hv.team_id,
          t.slug as team_slug,
          t.canonical_name as team_name,
          c.conference_name,
          coalesce(re.position, p.position) as position,
          hv.place,
          hv.winner_flag,
          hv.finalist_flag,
          hv.first_place_votes,
          hv.second_place_votes,
          hv.third_place_votes,
          hv.total_points,
          hv.ballot_count,
          hv.source_name
        from heisman_vote_results hv
        join players p on p.player_id = hv.player_id
        left join teams t on t.team_id = hv.team_id
        left join team_seasons ts
          on ts.team_id = hv.team_id
         and ts.season_year = hv.season_year
        left join conferences c on c.conference_id = ts.conference_id
        left join roster_entries re
          on re.player_id = hv.player_id
         and re.team_id = hv.team_id
         and re.season_year = hv.season_year
        where hv.player_id in ({placeholders})
        order by
          hv.player_id asc,
          hv.season_year desc,
          coalesce(hv.place, 999) asc,
          coalesce(hv.total_points, -1) desc,
          hv.heisman_vote_result_id desc
        """,
        player_ids,
    )
    current_stat_rows = _query_rows_for_player_ids(
        db,
        """
        select
          player_id,
          season_year,
          week,
          category,
          stat_type,
          stat_value_num
        from player_season_stats
        where player_id in ({placeholders})
          and season_year = ?
          and week = (
            select max(pss.week)
            from player_season_stats pss
            where pss.season_year = ?
          )
        order by player_id asc, category asc, stat_type asc
        """,
        player_ids,
        extra_params=(current_season, current_season),
    )
    current_usage_rows = _query_rows_for_player_ids(
        db,
        """
        select
          player_id,
          season_year,
          week,
          usage_overall,
          usage_pass,
          usage_rush,
          usage_first_down,
          usage_second_down,
          usage_third_down,
          usage_standard_downs,
          usage_passing_downs
        from player_usage_season
        where player_id in ({placeholders})
          and season_year = ?
          and week = (
            select max(pus.week)
            from player_usage_season pus
            where pus.season_year = ?
          )
        order by player_id asc
        """,
        player_ids,
        extra_params=(current_season, current_season),
    )
    current_value_rows = _query_rows_for_player_ids(
        db,
        """
        select
          player_id,
          season_year,
          week,
          metric_name,
          metric_value,
          plays
        from player_value_metrics
        where player_id in ({placeholders})
          and season_year = ?
          and week = (
            select max(pvm.week)
            from player_value_metrics pvm
            where pvm.season_year = ?
          )
        order by player_id asc, metric_name asc
        """,
        player_ids,
        extra_params=(current_season, current_season),
    )
    season_stat_history_rows = _query_player_season_stat_history_rows(db, player_ids)
    peer_stat_rows = db.query_all(
        """
        select
          pss.player_id,
          pss.category,
          pss.stat_type,
          pss.stat_value_num,
          coalesce(pss.position, re.position, p.position) as position,
          coalesce(ts.level_code, t.level_code) as level_code
        from player_season_stats pss
        join players p on p.player_id = pss.player_id
        left join teams t on t.team_id = pss.team_id
        left join team_seasons ts
          on ts.team_id = pss.team_id
         and ts.season_year = pss.season_year
        left join roster_entries re
          on re.player_id = pss.player_id
         and re.team_id = pss.team_id
         and re.season_year = pss.season_year
        where pss.season_year = %(season_year)s
          and pss.week = (
            select max(pss2.week)
            from player_season_stats pss2
            where pss2.season_year = %(season_year)s
          )
        """,
        {"season_year": current_season},
    )
    peer_usage_rows = db.query_all(
        """
        select
          pus.player_id,
          coalesce(pus.position, re.position, p.position) as position,
          coalesce(ts.level_code, t.level_code) as level_code,
          pus.usage_overall,
          pus.usage_pass,
          pus.usage_rush,
          pus.usage_first_down,
          pus.usage_second_down,
          pus.usage_third_down,
          pus.usage_standard_downs,
          pus.usage_passing_downs
        from player_usage_season pus
        join players p on p.player_id = pus.player_id
        left join teams t on t.team_id = pus.team_id
        left join team_seasons ts
          on ts.team_id = pus.team_id
         and ts.season_year = pus.season_year
        left join roster_entries re
          on re.player_id = pus.player_id
         and re.team_id = pus.team_id
         and re.season_year = pus.season_year
        where pus.season_year = %(season_year)s
          and pus.week = (
            select max(pus2.week)
            from player_usage_season pus2
            where pus2.season_year = %(season_year)s
          )
        """,
        {"season_year": current_season},
    )
    peer_value_rows = db.query_all(
        """
        select
          pvm.player_id,
          pvm.metric_name,
          pvm.metric_value,
          coalesce(pvm.position, re.position, p.position) as position,
          coalesce(ts.level_code, t.level_code) as level_code
        from player_value_metrics pvm
        join players p on p.player_id = pvm.player_id
        left join teams t on t.team_id = pvm.team_id
        left join team_seasons ts
          on ts.team_id = pvm.team_id
         and ts.season_year = pvm.season_year
        left join roster_entries re
          on re.player_id = pvm.player_id
         and re.team_id = pvm.team_id
         and re.season_year = pvm.season_year
        where pvm.season_year = %(season_year)s
          and pvm.week = (
            select max(pvm2.week)
            from player_value_metrics pvm2
            where pvm2.season_year = %(season_year)s
          )
        """,
        {"season_year": current_season},
    )
    recruiting_rows = _query_rows_for_player_ids(
        db,
        """
        select
          pr.player_id,
          pr.season_year,
          pr.recruit_type,
          pr.source_name,
          pr.source_recruit_id,
          pr.source_athlete_id,
          pr.team_id,
          t.slug as team_slug,
          t.canonical_name as team_name,
          pr.school_name,
          pr.committed_team,
          pr.position,
          pr.stars,
          pr.rating,
          pr.national_rank,
          pr.height_inches,
          pr.weight_lbs,
          pr.city,
          pr.state_province,
          pr.country
        from player_recruiting_profiles pr
        left join teams t on t.team_id = pr.team_id
        where pr.player_id in ({placeholders})
        order by pr.player_id asc, pr.season_year desc, pr.rating desc, pr.player_recruiting_profile_id desc
        """,
        player_ids,
    )
    transfer_history_rows = _query_rows_for_player_ids(
        db,
        """
        select
          te.player_id,
          te.season_year,
          te.from_team_id,
          ft.slug as from_team_slug,
          ft.canonical_name as from_team_name_resolved,
          te.to_team_id,
          tt.slug as to_team_slug,
          tt.canonical_name as to_team_name_resolved,
          te.from_level_code,
          te.to_level_code,
          te.position,
          te.rating,
          te.transfer_points,
          te.transfer_stars,
          te.transfer_date,
          te.eligibility,
          te.from_team_name,
          te.to_team_name
        from transfer_entries te
        left join teams ft on ft.team_id = te.from_team_id
        left join teams tt on tt.team_id = te.to_team_id
        where te.player_id in ({placeholders})
        order by te.player_id asc, te.season_year desc, te.transfer_entry_id desc
        """,
        player_ids,
    )
    honor_rows = _query_rows_for_player_ids(
        db,
        """
        select
          ph.player_id,
          ph.season_year,
          ph.week,
          ph.team_id,
          t.slug as team_slug,
          t.canonical_name as team_name,
          ph.conference_name,
          ph.honor_scope,
          ph.honor_name,
          ph.selector,
          ph.honor_team,
          ph.position,
          ph.placement,
          ph.consensus_flag,
          ph.unanimous_flag,
          ph.source_name,
          ph.source_url,
          ph.notes
        from player_honors ph
        left join teams t on t.team_id = ph.team_id
        where ph.player_id in ({placeholders})
        order by
          ph.player_id asc,
          ph.season_year desc,
          case when ph.week is null then 999 else ph.week end desc,
          ph.player_honor_id desc
        """,
        player_ids,
    )

    roster_by_player: dict[int, list[dict[str, Any]]] = {}
    for row in roster_history_rows:
        player_id = int(row["player_id"])
        normalized = {
            **row,
            "player_id": player_id,
            "season_year": int(row.get("season_year") or 0),
            "conference_name": None
            if row.get("conference_name") is None
            else _clean_conference_name(str(row["conference_name"])),
        }
        roster_by_player.setdefault(player_id, []).append(normalized)

    heisman_by_player: dict[int, dict[int, dict[str, Any]]] = {}
    for row in heisman_history_rows:
        player_id = int(row["player_id"])
        season_year = int(row.get("season_year") or 0)
        player_history = heisman_by_player.setdefault(player_id, {})
        if season_year in player_history:
            continue
        player_history[season_year] = {
            **row,
            "player_id": player_id,
            "season_year": season_year,
            "week": int(row.get("week") or 0),
            "conference_name": None
            if row.get("conference_name") is None
            else _clean_conference_name(str(row["conference_name"])),
            "rank_overall": None if row.get("rank_overall") is None else int(row["rank_overall"]),
            "nowcast_rank": None if row.get("nowcast_rank") is None else int(row["nowcast_rank"]),
            "forecast_rank": None if row.get("forecast_rank") is None else int(row["forecast_rank"]),
            "win_probability": None
            if row.get("win_probability") is None
            else float(row["win_probability"]),
            "finalist_probability": None
            if row.get("finalist_probability") is None
            else float(row["finalist_probability"]),
            "any_ballot_probability": None
            if row.get("any_ballot_probability") is None
            else float(row["any_ballot_probability"]),
            "expected_ballot_share": None
            if row.get("expected_ballot_share") is None
            else float(row["expected_ballot_share"]),
            "latent_score": None if row.get("latent_score") is None else float(row["latent_score"]),
            "market_implied_probability": None
            if row.get("market_implied_probability") is None
            else float(row["market_implied_probability"]),
            "market_american_odds": None
            if row.get("market_american_odds") is None
            else int(row["market_american_odds"]),
            "market_provider": None if row.get("market_provider") is None else str(row["market_provider"]),
        }

    votes_by_player: dict[int, dict[int, dict[str, Any]]] = {}
    for row in vote_history_rows:
        player_id = int(row["player_id"])
        season_year = int(row.get("season_year") or 0)
        player_votes = votes_by_player.setdefault(player_id, {})
        if season_year in player_votes:
            continue
        player_votes[season_year] = {
            **row,
            "player_id": player_id,
            "season_year": season_year,
            "conference_name": None
            if row.get("conference_name") is None
            else _clean_conference_name(str(row["conference_name"])),
            "place": None if row.get("place") is None else int(row["place"]),
            "winner_flag": bool(int(row.get("winner_flag") or 0)),
            "finalist_flag": bool(int(row.get("finalist_flag") or 0)),
            "first_place_votes": None
            if row.get("first_place_votes") is None
            else int(row["first_place_votes"]),
            "second_place_votes": None
            if row.get("second_place_votes") is None
            else int(row["second_place_votes"]),
            "third_place_votes": None
            if row.get("third_place_votes") is None
            else int(row["third_place_votes"]),
            "total_points": None if row.get("total_points") is None else int(row["total_points"]),
            "ballot_count": None if row.get("ballot_count") is None else int(row["ballot_count"]),
        }

    current_stats_by_player: dict[int, dict[str, Any]] = {}
    for row in current_stat_rows:
        player_id = int(row["player_id"])
        stat_map = current_stats_by_player.setdefault(
            player_id,
            {
                "season_year": int(row.get("season_year") or 0),
                "week": int(row.get("week") or 0),
                "stats": {},
                "raw_rows": [],
            },
        )
        stat_key = _player_stat_key(row.get("category"), row.get("stat_type"))
        if stat_key:
            stat_map["stats"][stat_key] = float(row.get("stat_value_num") or 0.0)
        stat_map["raw_rows"].append(
            {
                "category": str(row.get("category") or ""),
                "stat_type": str(row.get("stat_type") or ""),
                "value": None if row.get("stat_value_num") is None else float(row.get("stat_value_num") or 0.0),
            }
        )

    current_usage_by_player: dict[int, dict[str, Any]] = {}
    for row in current_usage_rows:
        player_id = int(row["player_id"])
        current_usage_by_player[player_id] = {
            "season_year": int(row.get("season_year") or 0),
            "week": int(row.get("week") or 0),
            "usage_overall": float(row.get("usage_overall") or 0.0),
            "usage_pass": float(row.get("usage_pass") or 0.0),
            "usage_rush": float(row.get("usage_rush") or 0.0),
            "usage_first_down": float(row.get("usage_first_down") or 0.0),
            "usage_second_down": float(row.get("usage_second_down") or 0.0),
            "usage_third_down": float(row.get("usage_third_down") or 0.0),
            "usage_standard_downs": float(row.get("usage_standard_downs") or 0.0),
            "usage_passing_downs": float(row.get("usage_passing_downs") or 0.0),
            "raw_rows": [
                {"metric_name": "usage_overall", "value": None if row.get("usage_overall") is None else float(row.get("usage_overall") or 0.0)},
                {"metric_name": "usage_pass", "value": None if row.get("usage_pass") is None else float(row.get("usage_pass") or 0.0)},
                {"metric_name": "usage_rush", "value": None if row.get("usage_rush") is None else float(row.get("usage_rush") or 0.0)},
                {"metric_name": "usage_first_down", "value": None if row.get("usage_first_down") is None else float(row.get("usage_first_down") or 0.0)},
                {"metric_name": "usage_second_down", "value": None if row.get("usage_second_down") is None else float(row.get("usage_second_down") or 0.0)},
                {"metric_name": "usage_third_down", "value": None if row.get("usage_third_down") is None else float(row.get("usage_third_down") or 0.0)},
                {"metric_name": "usage_standard_downs", "value": None if row.get("usage_standard_downs") is None else float(row.get("usage_standard_downs") or 0.0)},
                {"metric_name": "usage_passing_downs", "value": None if row.get("usage_passing_downs") is None else float(row.get("usage_passing_downs") or 0.0)},
            ],
        }

    current_value_by_player: dict[int, dict[str, Any]] = {}
    for row in current_value_rows:
        player_id = int(row["player_id"])
        payload = current_value_by_player.setdefault(
            player_id,
            {
                "season_year": int(row.get("season_year") or 0),
                "week": int(row.get("week") or 0),
                "metrics": {},
                "raw_rows": [],
            },
        )
        metric_name = str(row.get("metric_name") or "")
        if metric_name:
            payload["metrics"][metric_name] = {
                "value": float(row.get("metric_value") or 0.0),
                "plays": int(row.get("plays") or 0),
            }
            payload["raw_rows"].append(
                {
                    "metric_name": metric_name,
                    "value": None if row.get("metric_value") is None else float(row.get("metric_value") or 0.0),
                    "plays": int(row.get("plays") or 0),
                }
            )

    season_stats_by_player: dict[int, dict[int, dict[str, Any]]] = {}
    for row in season_stat_history_rows:
        player_id = int(row["player_id"])
        season_year = int(row.get("season_year") or 0)
        payload = season_stats_by_player.setdefault(player_id, {}).setdefault(
            season_year,
            {
                "season_year": season_year,
                "week": int(row.get("week") or 0),
                "team_name": row.get("team_name"),
                "team_slug": row.get("team_slug"),
                "stats": {},
                "raw_rows": [],
            },
        )
        stat_key = _player_stat_key(row.get("category"), row.get("stat_type"))
        if stat_key:
            payload["stats"][stat_key] = float(row.get("stat_value_num") or 0.0)
        payload["raw_rows"].append(
            {
                "category": str(row.get("category") or ""),
                "stat_type": str(row.get("stat_type") or ""),
                "value": None if row.get("stat_value_num") is None else float(row.get("stat_value_num") or 0.0),
            }
        )

    recruiting_by_player: dict[int, list[dict[str, Any]]] = {}
    for row in recruiting_rows:
        player_id = int(row["player_id"])
        recruiting_by_player.setdefault(player_id, []).append(
            {
                **row,
                "player_id": player_id,
                "season_year": int(row.get("season_year") or 0),
                "stars": None if row.get("stars") is None else int(row["stars"]),
                "national_rank": None if row.get("national_rank") is None else int(row["national_rank"]),
                "rating": None if row.get("rating") is None else float(row["rating"]),
                "height_inches": None if row.get("height_inches") is None else float(row["height_inches"]),
                "weight_lbs": None if row.get("weight_lbs") is None else float(row["weight_lbs"]),
            }
        )

    transfers_by_player: dict[int, list[dict[str, Any]]] = {}
    for row in transfer_history_rows:
        player_id = int(row["player_id"])
        transfers_by_player.setdefault(player_id, []).append(
            {
                **row,
                "player_id": player_id,
                "season_year": int(row.get("season_year") or 0),
                "rating": None if row.get("rating") is None else float(row["rating"]),
                "transfer_points": None if row.get("transfer_points") is None else float(row["transfer_points"]),
                "transfer_stars": None if row.get("transfer_stars") is None else int(row["transfer_stars"]),
                "from_team_name": row.get("from_team_name_resolved") or row.get("from_team_name"),
                "to_team_name": row.get("to_team_name_resolved") or row.get("to_team_name"),
            }
        )

    honors_by_player: dict[int, list[dict[str, Any]]] = {}
    for row in honor_rows:
        player_id = int(row["player_id"])
        honors_by_player.setdefault(player_id, []).append(
            {
                **row,
                "player_id": player_id,
                "season_year": int(row.get("season_year") or 0),
                "week": None if row.get("week") is None else int(row["week"]),
                "placement": None if row.get("placement") is None else int(row["placement"]),
                "consensus_flag": bool(int(row.get("consensus_flag") or 0)),
                "unanimous_flag": bool(int(row.get("unanimous_flag") or 0)),
            }
        )
    stat_peer_context = _build_player_stat_peer_context(peer_stat_rows, peer_usage_rows, peer_value_rows)

    player_pages: dict[str, dict[str, Any]] = {}
    for row in player_directory_rows:
        player_id = int(row["player_id"])
        page_data = _assemble_player_page_data(
            summary,
            row,
            roster_by_player.get(player_id, []),
            heisman_by_player.get(player_id, {}),
            votes_by_player.get(player_id, {}),
            current_stats_by_player.get(player_id, {}),
            current_usage_by_player.get(player_id, {}),
            current_value_by_player.get(player_id, {}),
            season_stats_by_player.get(player_id, {}),
            stat_peer_context,
            recruiting_by_player.get(player_id, []),
            transfers_by_player.get(player_id, []),
            honors_by_player.get(player_id, []),
            algorithmic_signature_index.get(player_id),
            player_mood_index.get(player_id),
        )
        row["tracked_heisman_seasons"] = len(page_data["heisman_years"])
        row["best_heisman_rank"] = page_data["best_heisman_rank"]
        row["latest_heisman_season"] = page_data["latest_heisman_season"]
        row["official_best_finish"] = page_data["official_best_finish"]
        row["primary_team_name"] = page_data["primary_team"].get("team_name")
        row["primary_team_slug"] = page_data["primary_team"].get("team_slug")
        row["primary_conference_name"] = page_data["primary_team"].get("conference_name")
        if not row.get("team_name") and page_data["primary_team"].get("team_name"):
            row["team_name"] = page_data["primary_team"]["team_name"]
            row["team_slug"] = page_data["primary_team"].get("team_slug")
        if not row.get("conference_name") and page_data["primary_team"].get("conference_name"):
            row["conference_name"] = page_data["primary_team"]["conference_name"]
        player_pages[str(row["player_slug"])] = page_data
    return player_pages


def _assemble_player_page_data(
    summary: dict[str, Any],
    player_row: dict[str, Any],
    roster_history: list[dict[str, Any]],
    heisman_by_year: dict[int, dict[str, Any]],
    vote_by_year: dict[int, dict[str, Any]],
    current_stat_snapshot: dict[str, Any],
    current_usage_snapshot: dict[str, Any],
    current_value_snapshot: dict[str, Any],
    season_stat_history: dict[int, dict[str, Any]],
    stat_peer_context: dict[tuple[str, str, str], list[float]],
    recruiting_history: list[dict[str, Any]],
    transfer_history: list[dict[str, Any]],
    honors_history: list[dict[str, Any]],
    algorithmic_signature: dict[str, Any] | None = None,
    the_room: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_season = int(summary["season_year"])
    current_roster = next((row for row in roster_history if int(row.get("season_year") or 0) == current_season), None)
    seasons = sorted(set(heisman_by_year) | set(vote_by_year), reverse=True)
    heisman_years: list[dict[str, Any]] = []
    for season_year in seasons:
        weekly = heisman_by_year.get(season_year) or {}
        vote = vote_by_year.get(season_year) or {}
        team_name = (
            weekly.get("team_name")
            or vote.get("team_name")
            or next(
                (row.get("team_name") for row in roster_history if int(row.get("season_year") or 0) == season_year),
                None,
            )
        )
        team_slug = (
            weekly.get("team_slug")
            or vote.get("team_slug")
            or next(
                (row.get("team_slug") for row in roster_history if int(row.get("season_year") or 0) == season_year),
                None,
            )
        )
        conference_name = (
            weekly.get("conference_name")
            or vote.get("conference_name")
            or next(
                (row.get("conference_name") for row in roster_history if int(row.get("season_year") or 0) == season_year),
                None,
            )
        )
        heisman_years.append(
            {
                "season_year": season_year,
                "team_name": team_name,
                "team_slug": team_slug,
                "conference_name": conference_name,
                "position": weekly.get("position")
                or vote.get("position")
                or next(
                    (row.get("position") for row in roster_history if int(row.get("season_year") or 0) == season_year),
                    None,
                ),
                "class_year": weekly.get("class_year")
                or next(
                    (row.get("class_year") for row in roster_history if int(row.get("season_year") or 0) == season_year),
                    None,
                ),
                "latest_week": None if not weekly else int(weekly.get("week") or 0),
                "overall_rank": weekly.get("rank_overall"),
                "nowcast_rank": weekly.get("nowcast_rank"),
                "forecast_rank": weekly.get("forecast_rank"),
                "win_probability": weekly.get("win_probability"),
                "finalist_probability": weekly.get("finalist_probability"),
                "any_ballot_probability": weekly.get("any_ballot_probability"),
                "expected_ballot_share": weekly.get("expected_ballot_share"),
                "latent_score": weekly.get("latent_score"),
                "market_implied_probability": weekly.get("market_implied_probability"),
                "market_american_odds": weekly.get("market_american_odds"),
                "market_provider": weekly.get("market_provider"),
                "official_place": vote.get("place"),
                "winner_flag": bool(vote.get("winner_flag")),
                "finalist_flag": bool(vote.get("finalist_flag")),
                "first_place_votes": vote.get("first_place_votes"),
                "second_place_votes": vote.get("second_place_votes"),
                "third_place_votes": vote.get("third_place_votes"),
                "total_points": vote.get("total_points"),
                "ballot_count": vote.get("ballot_count"),
                "official_result_text": _official_heisman_result_text(vote),
            }
        )

    current_snapshot = next(
        (row for row in heisman_years if int(row.get("season_year") or 0) == current_season),
        heisman_years[0] if heisman_years else {},
    )
    primary_team = current_roster or (roster_history[0] if roster_history else None)
    if primary_team is None and current_snapshot:
        primary_team = {
            "team_name": current_snapshot.get("team_name"),
            "team_slug": current_snapshot.get("team_slug"),
            "conference_name": current_snapshot.get("conference_name"),
            "position": current_snapshot.get("position"),
            "class_year": current_snapshot.get("class_year"),
        }
    primary_team = primary_team or {}
    level_code = str(primary_team.get("level_code") or "FBS")
    best_heisman_rank = min(
        [
            int(rank)
            for rank in [
                row.get("official_place") if row.get("official_place") is not None else row.get("nowcast_rank")
                for row in heisman_years
            ]
            if rank is not None
        ],
        default=None,
    )
    official_best_finish = min(
        [int(row.get("official_place")) for row in heisman_years if row.get("official_place") is not None],
        default=None,
    )
    player_identity = {
        "full_name": str(player_row.get("full_name") or "Player"),
        "position": player_row.get("current_position") or primary_team.get("position"),
        "class_year": player_row.get("class_year") or primary_team.get("class_year"),
        "jersey": player_row.get("jersey")
        or next((row.get("jersey") for row in roster_history if row.get("jersey")), None),
        "height_inches": player_row.get("height_inches")
        or next((row.get("height_inches") for row in roster_history if row.get("height_inches") is not None), None),
        "weight_lbs": player_row.get("weight_lbs")
        or next((row.get("weight_lbs") for row in roster_history if row.get("weight_lbs") is not None), None),
        "hometown": player_row.get("hometown")
        or next((row.get("hometown") for row in roster_history if row.get("hometown")), None),
        "home_state": player_row.get("home_state")
        or next((row.get("home_state") for row in roster_history if row.get("home_state")), None),
    }
    stat_profile = _build_player_stat_profile(
        position=player_identity.get("position"),
        stats=(current_stat_snapshot or {}).get("stats") or {},
        usage=current_usage_snapshot or {},
        value_metrics=(current_value_snapshot or {}).get("metrics") or {},
        raw_stats=(current_stat_snapshot or {}).get("raw_rows") or [],
        raw_usage_rows=(current_usage_snapshot or {}).get("raw_rows") or [],
        raw_value_rows=(current_value_snapshot or {}).get("raw_rows") or [],
        season_year=(current_stat_snapshot or {}).get("season_year") or current_season,
        week=(current_stat_snapshot or {}).get("week"),
        level_code=level_code,
        peer_context=stat_peer_context,
    )
    season_stat_tables = _build_player_season_stat_tables(
        bucket=str(stat_profile.get("bucket") or _position_filter_bucket(player_identity.get("position"))),
        season_stat_history=season_stat_history,
        roster_history=roster_history,
    )
    recruiting_profile = _build_player_recruiting_profile(recruiting_history)
    transfer_profile = _build_player_transfer_profile(transfer_history)
    signature_story = _build_player_signature_story(
        player_identity=player_identity,
        primary_team=primary_team,
        current_snapshot=current_snapshot,
        roster_history=roster_history,
        stat_profile=stat_profile,
        heisman_years=heisman_years,
        recruiting_profile=recruiting_profile,
        transfer_profile=transfer_profile,
        honors_history=honors_history,
    )
    honors_history = _filter_projected_heisman_honors(honors_history, current_season)
    trophy_case = _build_player_trophy_case(heisman_years, honors_history)
    return {
        "player": {
            "player_id": int(player_row["player_id"]),
            "player_slug": str(player_row["player_slug"]),
            **player_identity,
        },
        "primary_team": primary_team,
        "current_snapshot": current_snapshot,
        "heisman_years": heisman_years,
        "roster_history": roster_history,
        "recruiting_history": recruiting_history,
        "recruiting_profile": recruiting_profile,
        "transfer_history": transfer_history,
        "transfer_profile": transfer_profile,
        "honors_history": honors_history,
        "best_heisman_rank": best_heisman_rank,
        "official_best_finish": official_best_finish,
        "latest_heisman_season": heisman_years[0]["season_year"] if heisman_years else None,
        "signature_story": signature_story,
        "algorithmic_signature": algorithmic_signature,
        "the_room": the_room,
        "stat_profile": stat_profile,
        "season_stat_tables": season_stat_tables,
        "trophy_case": trophy_case,
        "modules": _player_module_cards(),
    }


def _player_stat_key(category: Any, stat_type: Any) -> str | None:
    category_key = re.sub(r"[^a-z0-9]+", "", str(category or "").lower())
    stat_key = re.sub(r"[^a-z0-9]+", "", str(stat_type or "").lower())
    mapping = {
        ("passing", "att"): "passing_att",
        ("passing", "completions"): "passing_completions",
        ("passing", "int"): "passing_int",
        ("passing", "pct"): "passing_pct",
        ("passing", "td"): "passing_td",
        ("passing", "yds"): "passing_yds",
        ("passing", "ypa"): "passing_ypa",
        ("rushing", "car"): "rushing_car",
        ("rushing", "td"): "rushing_td",
        ("rushing", "yds"): "rushing_yds",
        ("rushing", "ypc"): "rushing_ypc",
        ("receiving", "rec"): "receiving_rec",
        ("receiving", "td"): "receiving_td",
        ("receiving", "yds"): "receiving_yds",
        ("receiving", "ypr"): "receiving_ypr",
        ("defensive", "pd"): "defensive_pd",
        ("defensive", "qbhur"): "defensive_qb_hur",
        ("defensive", "sacks"): "defensive_sacks",
        ("defensive", "solo"): "defensive_solo",
        ("defensive", "td"): "defensive_td",
        ("defensive", "tfl"): "defensive_tfl",
        ("defensive", "tot"): "defensive_tot",
        ("interceptions", "avg"): "interceptions_avg",
        ("interceptions", "int"): "interceptions_int",
        ("interceptions", "td"): "interceptions_td",
        ("interceptions", "yds"): "interceptions_yds",
        ("fumbles", "fum"): "fumbles_forced",
        ("fumbles", "lost"): "fumbles_lost",
        ("fumbles", "rec"): "fumbles_recovered",
        ("kicking", "pts"): "kicking_pts",
        ("kicking", "fgm"): "kicking_fgm",
        ("kicking", "pct"): "kicking_pct",
        ("kickreturns", "td"): "kick_returns_td",
        ("kickreturns", "yds"): "kick_returns_yds",
        ("kickreturns", "avg"): "kick_returns_avg",
        ("kickreturns", "no"): "kick_returns_no",
        ("puntreturns", "td"): "punt_returns_td",
        ("puntreturns", "yds"): "punt_returns_yds",
        ("puntreturns", "avg"): "punt_returns_avg",
        ("puntreturns", "no"): "punt_returns_no",
    }
    return mapping.get((category_key, stat_key))


def _build_player_stat_profile(
    position: Any,
    stats: dict[str, float],
    usage: dict[str, Any],
    value_metrics: dict[str, Any],
    raw_stats: list[dict[str, Any]] | None = None,
    raw_usage_rows: list[dict[str, Any]] | None = None,
    raw_value_rows: list[dict[str, Any]] | None = None,
    season_year: int | None = None,
    week: int | None = None,
    level_code: str = "FBS",
    peer_context: dict[tuple[str, str, str], list[float]] | None = None,
) -> dict[str, Any]:
    bucket = _position_filter_bucket(position)
    scrimmage_yards = float(stats.get("rushing_yds", 0.0)) + float(stats.get("receiving_yds", 0.0))
    total_return_yards = float(stats.get("kick_returns_yds", 0.0)) + float(stats.get("punt_returns_yds", 0.0))
    total_return_tds = float(stats.get("kick_returns_td", 0.0)) + float(stats.get("punt_returns_td", 0.0))
    passing_wepa = (
        None
        if (value_metrics.get("wepa_passing") or {}).get("value") is None
        else float((value_metrics.get("wepa_passing") or {}).get("value") or 0.0)
    )
    rushing_wepa = (
        None
        if (value_metrics.get("wepa_rushing") or {}).get("value") is None
        else float((value_metrics.get("wepa_rushing") or {}).get("value") or 0.0)
    )
    usage_overall = None if usage.get("usage_overall") is None else float(usage.get("usage_overall") or 0.0)
    usage_pass = None if usage.get("usage_pass") is None else float(usage.get("usage_pass") or 0.0)
    usage_rush = None if usage.get("usage_rush") is None else float(usage.get("usage_rush") or 0.0)

    cards: list[dict[str, str]] = []
    rows: list[dict[str, str]] = []

    def add_card(label: str, value: str, submetric: str) -> None:
        cards.append({"label": label, "value": value, "submetric": submetric})

    def add_row(label: str, value: str, context: str) -> None:
        rows.append({"label": label, "value": value, "context": context})

    if bucket == "QB":
        add_card("Pass yards", _fmt_whole(stats.get("passing_yds")), f"{_fmt_whole(stats.get('passing_td'))} TD | {_fmt_whole(stats.get('passing_int'))} INT")
        add_card("Completion rate", _fmt_pct_fraction(stats.get("passing_pct")), f"{_fmt_whole(stats.get('passing_completions'))}/{_fmt_whole(stats.get('passing_att'))} completions")
        add_card("Yards/attempt", _fmt_decimal(stats.get("passing_ypa"), 1), "Explosiveness through the air")
        add_card("Rush impact", _fmt_whole(stats.get("rushing_yds")), f"{_fmt_whole(stats.get('rushing_td'))} rush TD")
        add_card(
            "Usage",
            _fmt_pct_fraction(usage_overall),
            (
                f"{_fmt_pct_fraction(usage_pass)} pass share | {_fmt_pct_fraction(usage_rush)} rush share"
                if usage_overall is not None
                else "Role share still loading"
            ),
        )
        add_card(
            "Passing WEPA",
            _fmt_signed_decimal(passing_wepa, 2),
            "Opponent-adjusted passing value" if passing_wepa is not None else "Adjusted value feed still loading",
        )
        add_row("Passing line", f"{_fmt_whole(stats.get('passing_yds'))} yds | {_fmt_whole(stats.get('passing_td'))} TD", f"{_fmt_pct_fraction(stats.get('passing_pct'))} comp | {_fmt_decimal(stats.get('passing_ypa'), 1)} YPA")
        add_row("Rushing line", f"{_fmt_whole(stats.get('rushing_yds'))} yds | {_fmt_whole(stats.get('rushing_td'))} TD", f"{_fmt_whole(stats.get('rushing_car'))} carries")
        add_row("Ball security", f"{_fmt_whole(stats.get('passing_int'))} INT | {_fmt_whole(stats.get('fumbles_lost'))} lost fumbles", "Turnover pressure is part of the profile")
        add_row(
            "Adjusted value",
            _fmt_signed_decimal(passing_wepa, 2),
            (
                f"{_fmt_whole((value_metrics.get('wepa_passing') or {}).get('plays'))} weighted plays"
                if passing_wepa is not None
                else "Adjusted value feed still loading"
            ),
        )
    elif bucket == "RB":
        add_card("Scrimmage yards", _fmt_whole(scrimmage_yards), f"{_fmt_whole(stats.get('rushing_yds'))} rush | {_fmt_whole(stats.get('receiving_yds'))} rec")
        add_card("Rush TD", _fmt_whole(stats.get("rushing_td")), f"{_fmt_whole(stats.get('rushing_car'))} carries")
        add_card("Yards/carry", _fmt_decimal(stats.get("rushing_ypc"), 1), "Per-rush efficiency")
        add_card("Receiving work", _fmt_whole(stats.get("receiving_rec")), f"{_fmt_whole(stats.get('receiving_yds'))} rec yds")
        add_card(
            "Usage",
            _fmt_pct_fraction(usage_overall),
            f"{_fmt_pct_fraction(usage_rush)} rush share" if usage_overall is not None else "Role share still loading",
        )
        add_card(
            "Rushing WEPA",
            _fmt_signed_decimal(rushing_wepa, 2),
            "Opponent-adjusted rush value" if rushing_wepa is not None else "Adjusted value feed still loading",
        )
        add_row("Rushing line", f"{_fmt_whole(stats.get('rushing_yds'))} yds | {_fmt_whole(stats.get('rushing_td'))} TD", f"{_fmt_decimal(stats.get('rushing_ypc'), 1)} YPC")
        add_row("Receiving line", f"{_fmt_whole(stats.get('receiving_rec'))} catches | {_fmt_whole(stats.get('receiving_yds'))} yds", f"{_fmt_whole(stats.get('receiving_td'))} receiving TD")
        add_row(
            "Usage split",
            _fmt_pct_fraction(usage_overall),
            (
                f"{_fmt_pct_fraction(usage_rush)} rush share | {_fmt_pct_fraction(usage_pass)} pass-game share"
                if usage_overall is not None
                else "Role share still loading"
            ),
        )
        if total_return_yards > 0 or total_return_tds > 0:
            add_row("Return game", f"{_fmt_whole(total_return_yards)} return yds", f"{_fmt_whole(total_return_tds)} return TD")
    elif bucket in {"WR", "TE"}:
        add_card("Receptions", _fmt_whole(stats.get("receiving_rec")), f"{_fmt_whole(stats.get('receiving_td'))} rec TD")
        add_card("Receiving yards", _fmt_whole(stats.get("receiving_yds")), f"{_fmt_decimal(stats.get('receiving_ypr'), 1)} per catch")
        add_card("Scrimmage yards", _fmt_whole(scrimmage_yards), "Total offensive yardage")
        add_card(
            "Usage",
            _fmt_pct_fraction(usage_overall),
            f"{_fmt_pct_fraction(usage_pass)} pass-game share" if usage_overall is not None else "Role share still loading",
        )
        add_card("Return yards", _fmt_whole(total_return_yards), f"{_fmt_whole(total_return_tds)} return TD")
        add_card("Touchdowns", _fmt_whole(float(stats.get("receiving_td", 0.0)) + float(stats.get("rushing_td", 0.0)) + total_return_tds), "Across offense and returns")
        add_row("Receiving line", f"{_fmt_whole(stats.get('receiving_rec'))} catches | {_fmt_whole(stats.get('receiving_yds'))} yds", f"{_fmt_whole(stats.get('receiving_td'))} TD | {_fmt_decimal(stats.get('receiving_ypr'), 1)} YPR")
        add_row("Designed touches", f"{_fmt_whole(stats.get('rushing_yds'))} rush yds | {_fmt_whole(stats.get('rushing_td'))} rush TD", "Hand-offs, reverses, and other touches")
        add_row("Return game", f"{_fmt_whole(total_return_yards)} return yds", f"{_fmt_whole(total_return_tds)} return TD")
        add_row(
            "Usage split",
            _fmt_pct_fraction(usage_overall),
            f"{_fmt_pct_fraction(usage_pass)} pass share" if usage_overall is not None else "Role share still loading",
        )
    elif bucket == "DEF":
        add_card("Total tackles", _fmt_whole(stats.get("defensive_tot")), f"{_fmt_whole(stats.get('defensive_solo'))} solo")
        add_card("TFL", _fmt_decimal(stats.get("defensive_tfl"), 1), "Backfield disruption")
        add_card("Sacks", _fmt_decimal(stats.get("defensive_sacks"), 1), "Pass-rush finish")
        add_card("INT", _fmt_whole(stats.get("interceptions_int")), f"{_fmt_whole(stats.get('interceptions_td'))} pick-six TD")
        add_card("Pass breakups", _fmt_whole(stats.get("defensive_pd")), "Coverage disruption")
        add_card("QB pressures", _fmt_whole(stats.get("defensive_qb_hur")), "Quarterback hurries")
        add_row("Disruption line", f"{_fmt_decimal(stats.get('defensive_tfl'), 1)} TFL | {_fmt_decimal(stats.get('defensive_sacks'), 1)} sacks", f"{_fmt_whole(stats.get('defensive_qb_hur'))} QB hurries")
        add_row("Tackle load", f"{_fmt_whole(stats.get('defensive_tot'))} tackles", f"{_fmt_whole(stats.get('defensive_solo'))} solo")
        add_row("Coverage splash", f"{_fmt_whole(stats.get('interceptions_int'))} INT | {_fmt_whole(stats.get('defensive_pd'))} PBUs", f"{_fmt_whole(stats.get('interceptions_td'))} defensive return TD")
        if total_return_yards > 0 or total_return_tds > 0:
            add_row("Return game", f"{_fmt_whole(total_return_yards)} return yds", f"{_fmt_whole(total_return_tds)} return TD")
    else:
        add_card("Scrimmage yards", _fmt_whole(scrimmage_yards), "Combined rushing and receiving")
        add_card("Touchdowns", _fmt_whole(float(stats.get("rushing_td", 0.0)) + float(stats.get("receiving_td", 0.0)) + total_return_tds), "Across offense and returns")
        add_card(
            "Usage",
            _fmt_pct_fraction(usage_overall),
            "Share of team offense" if usage_overall is not None else "Role share still loading",
        )
        add_row("Rushing", f"{_fmt_whole(stats.get('rushing_yds'))} yds | {_fmt_whole(stats.get('rushing_td'))} TD", f"{_fmt_decimal(stats.get('rushing_ypc'), 1)} YPC")
        add_row("Receiving", f"{_fmt_whole(stats.get('receiving_rec'))} catches | {_fmt_whole(stats.get('receiving_yds'))} yds", f"{_fmt_whole(stats.get('receiving_td'))} TD")
        add_row("Returns", f"{_fmt_whole(total_return_yards)} return yds", f"{_fmt_whole(total_return_tds)} return TD")

    explorer_rows = _build_player_stat_explorer_rows(
        bucket=bucket,
        raw_stats=raw_stats or [],
        raw_usage_rows=raw_usage_rows or [],
        raw_value_rows=raw_value_rows or [],
    )
    explorer_rows = [row for row in explorer_rows if _player_stat_group_allowed(bucket, str(row.get("group") or ""))]
    explorer_rows = _attach_player_stat_peer_context(
        explorer_rows=explorer_rows,
        bucket=bucket,
        level_code=level_code,
        peer_context=peer_context or {},
    )
    headline_cards = _enrich_player_stat_cards_with_peer_context(cards[:3], explorer_rows, bucket)
    support_cards = _enrich_player_stat_cards_with_peer_context(cards[3:], explorer_rows, bucket)
    traditional_sections = _build_player_traditional_sections(bucket, explorer_rows, season_year)
    advanced_rows = _build_player_advanced_rows(bucket, explorer_rows)
    archetype = _build_player_archetype(bucket, explorer_rows, level_code)
    return {
        "bucket": bucket,
        "cards": cards,
        "rows": rows,
        "stats": stats,
        "usage": usage,
        "value_metrics": value_metrics,
        "headline_cards": headline_cards,
        "support_cards": support_cards,
        "summary_rows": rows,
        "explorer_rows": explorer_rows,
        "traditional_sections": traditional_sections,
        "advanced_rows": advanced_rows,
        "archetype": archetype,
        "default_filter": _default_player_stat_filter(bucket),
        "available_groups": _player_stat_available_groups(explorer_rows),
        "snapshot_note": _player_stat_snapshot_note(season_year, week),
        "metric_guide": _player_stat_metric_guide(bucket),
    }


def _build_player_stat_explorer_rows(
    bucket: str,
    raw_stats: list[dict[str, Any]],
    raw_usage_rows: list[dict[str, Any]],
    raw_value_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    explorer_rows: list[dict[str, Any]] = []

    for row in raw_stats:
        category = str(row.get("category") or "")
        stat_type = str(row.get("stat_type") or "")
        value = row.get("value")
        if value in (None, ""):
            continue
        label, group_name, family, format_kind = _player_stat_meta(category, stat_type)
        if not _include_player_stat_row(category, stat_type, value):
            continue
        explorer_rows.append(
            {
                "group": group_name,
                "group_key": _board_filter_value(group_name),
                "family": family,
                "metric": label,
                "value": _format_player_stat_value(format_kind, value),
                "sort_value": float(value),
                "context": family,
                "priority": _player_stat_priority(bucket, group_name, label),
            }
        )

    usage_labels = {
        "usage_overall": ("Role share", "Usage", "Share of team offense"),
        "usage_pass": ("Pass share", "Usage", "Air-game usage"),
        "usage_rush": ("Rush share", "Usage", "Ground-game usage"),
        "usage_first_down": ("1st-down usage", "Usage", "Early-down load"),
        "usage_second_down": ("2nd-down usage", "Usage", "Middle-down load"),
        "usage_third_down": ("3rd-down usage", "Usage", "Money-down load"),
        "usage_standard_downs": ("Standard-down usage", "Usage", "Base-situation share"),
        "usage_passing_downs": ("Passing-down usage", "Usage", "Known-passing share"),
    }
    for row in raw_usage_rows:
        metric_name = str(row.get("metric_name") or "")
        value = row.get("value")
        if metric_name not in usage_labels or value in (None, ""):
            continue
        label, group_name, context = usage_labels[metric_name]
        explorer_rows.append(
            {
                "group": group_name,
                "group_key": _board_filter_value(group_name),
                "family": "Usage",
                "metric": label,
                "value": _fmt_pct_fraction(value),
                "sort_value": float(value),
                "context": context,
                "priority": _player_stat_priority(bucket, group_name, label),
            }
        )

    value_labels = {
        "wepa_passing": ("Passing WEPA", "Value", "Opponent-adjusted passing value"),
        "wepa_rushing": ("Rushing WEPA", "Value", "Opponent-adjusted rushing value"),
    }
    for row in raw_value_rows:
        metric_name = str(row.get("metric_name") or "")
        value = row.get("value")
        if metric_name not in value_labels or value in (None, ""):
            continue
        label, group_name, context = value_labels[metric_name]
        plays = int(row.get("plays") or 0)
        explorer_rows.append(
            {
                "group": group_name,
                "group_key": _board_filter_value(group_name),
                "family": "Adjusted",
                "metric": label,
                "value": _fmt_signed_decimal(value, 2),
                "sort_value": float(value),
                "context": f"{context} | {_fmt_whole(plays)} weighted plays" if plays else context,
                "priority": _player_stat_priority(bucket, group_name, label),
            }
        )

    explorer_rows.sort(key=lambda item: (int(item.get("priority") or 999), -float(item.get("sort_value") or 0.0), str(item.get("metric") or "")))
    return explorer_rows


def _build_player_stat_peer_context(
    peer_stat_rows: list[dict[str, Any]],
    peer_usage_rows: list[dict[str, Any]],
    peer_value_rows: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[float]]:
    distributions: dict[tuple[str, str, str], list[float]] = {}

    def add_value(level_code: Any, bucket: str, metric_key: str, value: Any) -> None:
        if value in (None, ""):
            return
        distributions.setdefault((str(level_code or "FBS"), bucket, metric_key), []).append(float(value))

    for row in peer_stat_rows:
        category = str(row.get("category") or "")
        stat_type = str(row.get("stat_type") or "")
        value = row.get("stat_value_num")
        if value in (None, ""):
            continue
        label, group_name, _family, _format_kind = _player_stat_meta(category, stat_type)
        if not _include_player_stat_row(category, stat_type, value):
            continue
        bucket = _position_filter_bucket(row.get("position"))
        metric_key = _player_stat_metric_key(group_name, label)
        add_value(row.get("level_code"), bucket, metric_key, value)

    for row in peer_usage_rows:
        bucket = _position_filter_bucket(row.get("position"))
        usage_labels = {
            "usage_overall": "Role share",
            "usage_pass": "Pass share",
            "usage_rush": "Rush share",
            "usage_first_down": "1st-down usage",
            "usage_second_down": "2nd-down usage",
            "usage_third_down": "3rd-down usage",
            "usage_standard_downs": "Standard-down usage",
            "usage_passing_downs": "Passing-down usage",
        }
        for metric_name, label in usage_labels.items():
            add_value(row.get("level_code"), bucket, _player_stat_metric_key("Usage", label), row.get(metric_name))

    for row in peer_value_rows:
        bucket = _position_filter_bucket(row.get("position"))
        metric_name = str(row.get("metric_name") or "")
        value_labels = {
            "wepa_passing": "Passing WEPA",
            "wepa_rushing": "Rushing WEPA",
        }
        label = value_labels.get(metric_name, metric_name)
        add_value(row.get("level_code"), bucket, _player_stat_metric_key("Value", label), row.get("metric_value"))

    for key in list(distributions.keys()):
        _level_code, _bucket, metric_key = key
        distributions[key].sort(reverse=not _player_stat_lower_is_better(metric_key))
    return distributions


def _attach_player_stat_peer_context(
    explorer_rows: list[dict[str, Any]],
    bucket: str,
    level_code: str,
    peer_context: dict[tuple[str, str, str], list[float]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in explorer_rows:
        metric_key = _player_stat_metric_key(row.get("group"), row.get("metric"))
        peer_values = peer_context.get((level_code, bucket, metric_key), [])
        sort_value = float(row.get("sort_value") or 0.0)
        rank_text, percentile_text = _player_stat_rank_percentile_text(
            peer_values,
            sort_value,
            lower_is_better=_player_stat_lower_is_better(metric_key),
        )
        enriched.append(
            {
                **row,
                "rank_text": rank_text,
                "percentile_text": percentile_text,
                "peer_basis": f"vs {level_code} {bucket}" if bucket != "OTHER" else f"vs {level_code} peers",
            }
        )
    return enriched


def _enrich_player_stat_cards_with_peer_context(
    cards: list[dict[str, str]],
    explorer_rows: list[dict[str, Any]],
    bucket: str,
) -> list[dict[str, str]]:
    row_lookup = {
        _player_stat_metric_key(row.get("group"), row.get("metric")): row
        for row in explorer_rows
    }
    enriched_cards: list[dict[str, str]] = []
    for card in cards:
        metric_key = _player_card_metric_key(bucket, str(card.get("label") or ""))
        peer_row = row_lookup.get(metric_key)
        if peer_row and peer_row.get("percentile_text") not in (None, "", "--"):
            value = str(card.get("value") or "--")
            if not _player_stat_has_display_value(value) and _player_stat_has_display_value(peer_row.get("value")):
                value = str(peer_row.get("value") or "--")
            submetric = str(card.get("submetric") or "")
            peer_note = _compact_player_peer_note(peer_row.get("rank_text"), peer_row.get("percentile_text"))
            submetric = f"{submetric} | {peer_note}" if submetric else peer_note
            enriched_cards.append({**card, "value": value, "submetric": submetric})
        else:
            enriched_cards.append(card)
    return enriched_cards


def _player_card_metric_key(bucket: str, card_label: str) -> str:
    mapping = {
        "QB": {
            "Pass yards": ("Passing", "Passing yards"),
            "Completion rate": ("Passing", "Completion %"),
            "Yards/attempt": ("Passing", "Yards / attempt"),
            "Rush impact": ("Rushing", "Rushing yards"),
            "Usage": ("Usage", "Role share"),
            "Passing WEPA": ("Value", "Passing WEPA"),
        },
        "RB": {
            "Scrimmage yards": ("Rushing", "Rushing yards"),
            "Rush TD": ("Rushing", "Rush TD"),
            "Yards/carry": ("Rushing", "Yards / carry"),
            "Receiving work": ("Receiving", "Receptions"),
            "Usage": ("Usage", "Role share"),
            "Rushing WEPA": ("Value", "Rushing WEPA"),
        },
        "WR": {
            "Receptions": ("Receiving", "Receptions"),
            "Receiving yards": ("Receiving", "Receiving yards"),
            "Scrimmage yards": ("Receiving", "Receiving yards"),
            "Usage": ("Usage", "Pass share"),
            "Return yards": ("Returns", "Kick return yards"),
            "Touchdowns": ("Receiving", "Receiving TD"),
        },
        "TE": {
            "Receptions": ("Receiving", "Receptions"),
            "Receiving yards": ("Receiving", "Receiving yards"),
            "Scrimmage yards": ("Receiving", "Receiving yards"),
            "Usage": ("Usage", "Pass share"),
            "Return yards": ("Returns", "Kick return yards"),
            "Touchdowns": ("Receiving", "Receiving TD"),
        },
        "DEF": {
            "Total tackles": ("Defense", "Total tackles"),
            "TFL": ("Defense", "TFL"),
            "Sacks": ("Defense", "Sacks"),
            "INT": ("Defense", "Interceptions"),
            "Pass breakups": ("Defense", "Pass breakups"),
            "QB pressures": ("Defense", "QB hurries"),
        },
    }
    group_metric = mapping.get(bucket, {}).get(card_label)
    if not group_metric:
        return ""
    return _player_stat_metric_key(group_metric[0], group_metric[1])


def _player_stat_rank_percentile_text(peer_values: list[float], target_value: float, lower_is_better: bool = False) -> tuple[str, str]:
    if not peer_values:
        return "--", "--"
    total = len(peer_values)
    if lower_is_better:
        better_or_equal = sum(1 for value in peer_values if value <= target_value)
        percentile = sum(1 for value in peer_values if target_value <= value) / total
    else:
        better_or_equal = sum(1 for value in peer_values if value >= target_value)
        percentile = sum(1 for value in peer_values if target_value >= value) / total
    percentile_value = int(round(percentile * 100))
    return f"#{better_or_equal}/{total}", f"{_ordinal_text(percentile_value)} pct"


def _player_stat_metric_key(group_name: Any, metric_name: Any) -> str:
    return f"{_board_filter_value(group_name)}::{_board_filter_value(metric_name)}"


def _compact_player_peer_note(rank_text: Any, percentile_text: Any) -> str:
    rank = str(rank_text or "").strip()
    percentile = str(percentile_text or "").strip()
    if rank and rank != "--" and percentile and percentile != "--":
        return f"{rank} ({percentile})"
    if rank and rank != "--":
        return rank
    if percentile and percentile != "--":
        return percentile
    return "--"


def _ordinal_text(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _player_stat_group_allowed(bucket: str, group_name: str) -> bool:
    allowed = {
        "QB": {"Passing", "Rushing", "Usage", "Value", "Ball Security"},
        "RB": {"Rushing", "Receiving", "Returns", "Usage", "Value", "Ball Security"},
        "WR": {"Receiving", "Rushing", "Returns", "Usage", "Value", "Ball Security"},
        "TE": {"Receiving", "Rushing", "Usage", "Value", "Ball Security"},
        "DEF": {"Defense", "Usage", "Value", "Ball Security"},
    }
    return group_name in allowed.get(bucket, {group_name})


def _player_stat_has_display_value(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text != "--"


def _player_stat_percentile_value(percentile_text: Any) -> int | None:
    match = re.search(r"(\d+)", str(percentile_text or ""))
    return int(match.group(1)) if match else None


def _player_stat_percentile_tone(percentile_text: Any) -> str:
    percentile_value = _player_stat_percentile_value(percentile_text)
    if percentile_value is None:
        return "tone-neutral"
    if percentile_value >= 90:
        return "tone-elite"
    if percentile_value >= 75:
        return "tone-strong"
    if percentile_value >= 50:
        return "tone-solid"
    return "tone-warning"


def _build_player_traditional_section(
    title: str,
    subtitle: str,
    columns: list[tuple[str, str, str]],
    row_lookup: dict[str, dict[str, Any]],
    season_year: int | None,
) -> dict[str, Any] | None:
    cells: list[dict[str, str]] = []
    peer_basis = ""
    for group_name, metric_name, short_label in columns:
        row = row_lookup.get(_player_stat_metric_key(group_name, metric_name), {})
        value = str(row.get("value") or "--")
        if not _player_stat_has_display_value(value):
            continue
        percentile_text = str(row.get("percentile_text") or "")
        peer = " | ".join(
            item for item in [str(row.get("rank_text") or ""), percentile_text] if item and item != "--"
        ) or "--"
        if not peer_basis:
            peer_basis = str(row.get("peer_basis") or "").strip()
        cells.append(
            {
                "label": short_label,
                "value": value,
                "peer": peer,
                "tone": _player_stat_percentile_tone(percentile_text),
            }
        )
    if not cells:
        return None
    return {
        "title": title,
        "subtitle": subtitle,
        "season_label": str(int(season_year or 0)) if season_year not in (None, 0) else "Current season",
        "peer_basis": peer_basis,
        "cells": cells,
    }


def _build_player_traditional_sections(bucket: str, explorer_rows: list[dict[str, Any]], season_year: int | None) -> list[dict[str, Any]]:
    row_lookup = {
        _player_stat_metric_key(row.get("group"), row.get("metric")): row
        for row in explorer_rows
    }
    section_catalog = {
        "QB": [
            {
                "title": "Passing Efficiency",
                "subtitle": "Start with accuracy and per-throw efficiency before the raw totals.",
                "columns": [
                    ("Passing", "Completions", "CMP"),
                    ("Passing", "Attempts", "ATT"),
                    ("Passing", "Completion %", "CMP%"),
                    ("Passing", "Yards / attempt", "YPA"),
                    ("Passing", "Passer rating", "RTG"),
                ],
            },
            {
                "title": "Passing Production",
                "subtitle": "Volume, scoring, explosiveness, and the pressure cost of the passing load.",
                "columns": [
                    ("Passing", "Passing yards", "YDS"),
                    ("Passing", "Pass TD", "TD"),
                    ("Passing", "Interceptions", "INT"),
                    ("Passing", "Longest pass", "LNG"),
                    ("Passing", "Sacks taken", "SACK"),
                ],
            },
            {
                "title": "Rushing",
                "subtitle": "What the quarterback adds on the ground.",
                "columns": [
                    ("Rushing", "Carries", "CAR"),
                    ("Rushing", "Rushing yards", "YDS"),
                    ("Rushing", "Yards / carry", "YPC"),
                    ("Rushing", "Rush TD", "TD"),
                    ("Rushing", "Longest rush", "LNG"),
                ],
            },
        ],
        "RB": [
            {
                "title": "Rushing",
                "subtitle": "Core backfield box-score production.",
                "columns": [
                    ("Rushing", "Carries", "CAR"),
                    ("Rushing", "Rushing yards", "YDS"),
                    ("Rushing", "Yards / carry", "YPC"),
                    ("Rushing", "Rush TD", "TD"),
                    ("Rushing", "Longest rush", "LNG"),
                ],
            },
            {
                "title": "Receiving",
                "subtitle": "Passing-game value that rounds out the rushing profile.",
                "columns": [
                    ("Receiving", "Receptions", "REC"),
                    ("Receiving", "Receiving yards", "YDS"),
                    ("Receiving", "Yards / catch", "YPR"),
                    ("Receiving", "Receiving TD", "TD"),
                    ("Receiving", "Longest catch", "LNG"),
                ],
            },
        ],
        "WR": [
            {
                "title": "Receiving",
                "subtitle": "The base receiving line most fans look for first.",
                "columns": [
                    ("Receiving", "Receptions", "REC"),
                    ("Receiving", "Receiving yards", "YDS"),
                    ("Receiving", "Yards / catch", "YPR"),
                    ("Receiving", "Receiving TD", "TD"),
                    ("Receiving", "Longest catch", "LNG"),
                ],
            },
            {
                "title": "Rushing",
                "subtitle": "Designed touches outside the normal receiving workload.",
                "columns": [
                    ("Rushing", "Carries", "CAR"),
                    ("Rushing", "Rushing yards", "YDS"),
                    ("Rushing", "Yards / carry", "YPC"),
                    ("Rushing", "Rush TD", "TD"),
                    ("Rushing", "Longest rush", "LNG"),
                ],
            },
            {
                "title": "Returns",
                "subtitle": "Special-teams production for all-purpose profiles.",
                "columns": [
                    ("Returns", "Kick return yards", "KR YDS"),
                    ("Returns", "Kick return avg", "KR AVG"),
                    ("Returns", "Punt return yards", "PR YDS"),
                    ("Returns", "Punt return avg", "PR AVG"),
                    ("Returns", "Punt return TD", "RET TD"),
                ],
            },
        ],
        "TE": [
            {
                "title": "Receiving",
                "subtitle": "Traditional receiving production for the position.",
                "columns": [
                    ("Receiving", "Receptions", "REC"),
                    ("Receiving", "Receiving yards", "YDS"),
                    ("Receiving", "Yards / catch", "YPR"),
                    ("Receiving", "Receiving TD", "TD"),
                    ("Receiving", "Longest catch", "LNG"),
                ],
            },
            {
                "title": "Rushing",
                "subtitle": "Any gadget or short-yardage rushing usage.",
                "columns": [
                    ("Rushing", "Carries", "CAR"),
                    ("Rushing", "Rushing yards", "YDS"),
                    ("Rushing", "Yards / carry", "YPC"),
                    ("Rushing", "Rush TD", "TD"),
                    ("Rushing", "Longest rush", "LNG"),
                ],
            },
        ],
        "DEF": [
            {
                "title": "Tackling & Disruption",
                "subtitle": "How often the defender creates negative or high-leverage plays.",
                "columns": [
                    ("Defense", "Total tackles", "TOT"),
                    ("Defense", "Solo tackles", "SOLO"),
                    ("Defense", "TFL", "TFL"),
                    ("Defense", "Sacks", "SACK"),
                    ("Defense", "QB hurries", "QBH"),
                ],
            },
            {
                "title": "Coverage & Takeaways",
                "subtitle": "Ball production and play-finishing metrics that make defensive cases visible nationally.",
                "columns": [
                    ("Defense", "Pass breakups", "PD"),
                    ("Defense", "Interceptions", "INT"),
                    ("Defense", "Forced fumbles", "FF"),
                ],
            },
        ],
    }
    sections: list[dict[str, Any]] = []
    for section in section_catalog.get(bucket, []):
        built_section = _build_player_traditional_section(
            str(section.get("title") or "Stats"),
            str(section.get("subtitle") or ""),
            list(section.get("columns") or []),
            row_lookup,
            season_year,
        )
        if built_section:
            sections.append(built_section)
    return sections


def _player_stat_metric_guide(bucket: str) -> list[dict[str, str]]:
    shared = [
        {
            "label": "Peer percentile",
            "body": "Every percentile is compared against players at the same position and level, so an FBS quarterback is judged against FBS quarterbacks, not the whole sport.",
        },
        {
            "label": "Traditional first",
            "body": "The top tables stick to the stats fans already know from broadcasts and box scores. Advanced context is pushed underneath instead of replacing the basics.",
        },
    ]
    bucket_specific = {
        "QB": [
            {
                "label": "Passing WEPA",
                "body": "Opponent-adjusted passing value. Positive numbers mean the quarterback is adding more value through the air than a neutral peer would in the same environment.",
            },
            {
                "label": "Role share",
                "body": "How much of the offense runs through the quarterback once passing and rushing responsibility are blended together.",
            },
        ],
        "RB": [
            {
                "label": "Rushing WEPA",
                "body": "Opponent-adjusted rushing value. It helps separate empty volume from carries that actually move the scoreboard.",
            },
            {
                "label": "Role share",
                "body": "How much of the team's offense flows through this back once rushing work and receiving work are combined.",
            },
        ],
        "WR": [
            {
                "label": "Pass share",
                "body": "The player's share of a team's passing-game involvement. It is the fastest way to see whether the receiver is a true focal point or more of a complementary piece.",
            },
            {
                "label": "Role share",
                "body": "A blended workload view that accounts for catches, designed touches, and any return-game involvement that shapes the overall profile.",
            },
        ],
        "TE": [
            {
                "label": "Pass share",
                "body": "The tight end's share of the passing offense, which helps distinguish a featured receiving tight end from a secondary option.",
            },
            {
                "label": "Role share",
                "body": "A blended usage view that shows how often the offense flows through the tight end compared with other same-level peers.",
            },
        ],
        "DEF": [
            {
                "label": "Disruption stats",
                "body": "TFL, sacks, and QB hurries are grouped together because defensive Heisman cases are usually built on visible havoc, not on tackle counts alone.",
            },
            {
                "label": "Coverage splash",
                "body": "Pass breakups, interceptions, and forced fumbles matter because national awards voters respond to plays that change possessions and highlight reels.",
            },
        ],
    }
    return (bucket_specific.get(bucket) or []) + shared


def _player_season_table_catalog(bucket: str) -> list[dict[str, Any]]:
    return {
        "QB": [
            {
                "title": "Passing",
                "subtitle": "Season-by-season quarterback passing line in a familiar scoreboard layout.",
                "columns": [
                    {"label": "CMP", "group": "Passing", "metric": "Completions", "format": "whole", "aggregate": "sum"},
                    {"label": "ATT", "group": "Passing", "metric": "Attempts", "format": "whole", "aggregate": "sum"},
                    {
                        "label": "CMP%",
                        "format": "pct",
                        "aggregate": "ratio",
                        "numerator": ("Passing", "Completions"),
                        "denominator": ("Passing", "Attempts"),
                    },
                    {"label": "YDS", "group": "Passing", "metric": "Passing yards", "format": "whole", "aggregate": "sum"},
                    {
                        "label": "YPA",
                        "format": "decimal",
                        "aggregate": "ratio",
                        "numerator": ("Passing", "Passing yards"),
                        "denominator": ("Passing", "Attempts"),
                    },
                    {"label": "TD", "group": "Passing", "metric": "Pass TD", "format": "whole", "aggregate": "sum"},
                    {"label": "INT", "group": "Passing", "metric": "Interceptions", "format": "whole", "aggregate": "sum"},
                    {"label": "RTG", "format": "decimal", "aggregate": "passer_rating"},
                    {"label": "LNG", "group": "Passing", "metric": "Longest pass", "format": "whole", "aggregate": "max"},
                    {"label": "SACK", "group": "Passing", "metric": "Sacks taken", "format": "whole", "aggregate": "sum"},
                ],
            },
            {
                "title": "Rushing",
                "subtitle": "Ground contribution that rounds out the quarterback profile.",
                "columns": [
                    {"label": "CAR", "group": "Rushing", "metric": "Carries", "format": "whole", "aggregate": "sum"},
                    {"label": "YDS", "group": "Rushing", "metric": "Rushing yards", "format": "whole", "aggregate": "sum"},
                    {
                        "label": "AVG",
                        "format": "decimal",
                        "aggregate": "ratio",
                        "numerator": ("Rushing", "Rushing yards"),
                        "denominator": ("Rushing", "Carries"),
                    },
                    {"label": "TD", "group": "Rushing", "metric": "Rush TD", "format": "whole", "aggregate": "sum"},
                    {"label": "LNG", "group": "Rushing", "metric": "Longest rush", "format": "whole", "aggregate": "max"},
                ],
            },
        ],
        "RB": [
            {
                "title": "Rushing",
                "subtitle": "Classic running back rushing table with season and career context.",
                "columns": [
                    {"label": "CAR", "group": "Rushing", "metric": "Carries", "format": "whole", "aggregate": "sum"},
                    {"label": "YDS", "group": "Rushing", "metric": "Rushing yards", "format": "whole", "aggregate": "sum"},
                    {
                        "label": "AVG",
                        "format": "decimal",
                        "aggregate": "ratio",
                        "numerator": ("Rushing", "Rushing yards"),
                        "denominator": ("Rushing", "Carries"),
                    },
                    {"label": "TD", "group": "Rushing", "metric": "Rush TD", "format": "whole", "aggregate": "sum"},
                    {"label": "LNG", "group": "Rushing", "metric": "Longest rush", "format": "whole", "aggregate": "max"},
                ],
            },
            {
                "title": "Receiving",
                "subtitle": "Passing-game production that separates pure runners from all-purpose backs.",
                "columns": [
                    {"label": "REC", "group": "Receiving", "metric": "Receptions", "format": "whole", "aggregate": "sum"},
                    {"label": "YDS", "group": "Receiving", "metric": "Receiving yards", "format": "whole", "aggregate": "sum"},
                    {
                        "label": "AVG",
                        "format": "decimal",
                        "aggregate": "ratio",
                        "numerator": ("Receiving", "Receiving yards"),
                        "denominator": ("Receiving", "Receptions"),
                    },
                    {"label": "TD", "group": "Receiving", "metric": "Receiving TD", "format": "whole", "aggregate": "sum"},
                    {"label": "LNG", "group": "Receiving", "metric": "Longest catch", "format": "whole", "aggregate": "max"},
                ],
            },
        ],
        "WR": [
            {
                "title": "Receiving",
                "subtitle": "Traditional receiver line with season-by-season growth baked in.",
                "columns": [
                    {"label": "REC", "group": "Receiving", "metric": "Receptions", "format": "whole", "aggregate": "sum"},
                    {"label": "YDS", "group": "Receiving", "metric": "Receiving yards", "format": "whole", "aggregate": "sum"},
                    {
                        "label": "AVG",
                        "format": "decimal",
                        "aggregate": "ratio",
                        "numerator": ("Receiving", "Receiving yards"),
                        "denominator": ("Receiving", "Receptions"),
                    },
                    {"label": "TD", "group": "Receiving", "metric": "Receiving TD", "format": "whole", "aggregate": "sum"},
                    {"label": "LNG", "group": "Receiving", "metric": "Longest catch", "format": "whole", "aggregate": "max"},
                ],
            },
            {
                "title": "Rushing & Returns",
                "subtitle": "Extra-touch value for all-purpose profiles.",
                "columns": [
                    {"label": "CAR", "group": "Rushing", "metric": "Carries", "format": "whole", "aggregate": "sum"},
                    {"label": "RUSH YDS", "group": "Rushing", "metric": "Rushing yards", "format": "whole", "aggregate": "sum"},
                    {"label": "KR YDS", "group": "Returns", "metric": "Kick return yards", "format": "whole", "aggregate": "sum"},
                    {"label": "PR YDS", "group": "Returns", "metric": "Punt return yards", "format": "whole", "aggregate": "sum"},
                    {"label": "RET TD", "group": "Returns", "metric": "Punt return TD", "format": "whole", "aggregate": "sum"},
                ],
            },
        ],
        "TE": [
            {
                "title": "Receiving",
                "subtitle": "Traditional tight end receiving production with season progression.",
                "columns": [
                    {"label": "REC", "group": "Receiving", "metric": "Receptions", "format": "whole", "aggregate": "sum"},
                    {"label": "YDS", "group": "Receiving", "metric": "Receiving yards", "format": "whole", "aggregate": "sum"},
                    {
                        "label": "AVG",
                        "format": "decimal",
                        "aggregate": "ratio",
                        "numerator": ("Receiving", "Receiving yards"),
                        "denominator": ("Receiving", "Receptions"),
                    },
                    {"label": "TD", "group": "Receiving", "metric": "Receiving TD", "format": "whole", "aggregate": "sum"},
                    {"label": "LNG", "group": "Receiving", "metric": "Longest catch", "format": "whole", "aggregate": "max"},
                ],
            },
        ],
        "DEF": [
            {
                "title": "Defense",
                "subtitle": "Season-by-season defensive box score for disruption and splash plays.",
                "columns": [
                    {"label": "TOT", "group": "Defense", "metric": "Total tackles", "format": "whole", "aggregate": "sum"},
                    {"label": "SOLO", "group": "Defense", "metric": "Solo tackles", "format": "whole", "aggregate": "sum"},
                    {"label": "TFL", "group": "Defense", "metric": "TFL", "format": "decimal", "aggregate": "sum"},
                    {"label": "SACK", "group": "Defense", "metric": "Sacks", "format": "decimal", "aggregate": "sum"},
                    {"label": "PD", "group": "Defense", "metric": "Pass breakups", "format": "whole", "aggregate": "sum"},
                    {"label": "INT", "group": "Defense", "metric": "Interceptions", "format": "whole", "aggregate": "sum"},
                    {"label": "FF", "group": "Defense", "metric": "Forced fumbles", "format": "whole", "aggregate": "sum"},
                ],
            },
        ],
    }.get(bucket, [])


def _build_player_season_metric_lookup(raw_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in raw_rows:
        category = str(row.get("category") or "")
        stat_type = str(row.get("stat_type") or "")
        value = row.get("value")
        if value in (None, "") or not _include_player_stat_row(category, stat_type, value):
            continue
        label, group_name, _family, format_kind = _player_stat_meta(category, stat_type)
        metric_key = _player_stat_metric_key(group_name, label)
        lookup[metric_key] = {
            "value": float(value),
            "display": _format_player_stat_value(format_kind, value),
            "format": format_kind,
        }
    return lookup


def _player_season_metric_value(metric_lookup: dict[str, dict[str, Any]], group_name: str, metric_name: str) -> float | None:
    row = metric_lookup.get(_player_stat_metric_key(group_name, metric_name), {})
    value = row.get("value")
    return None if value in (None, "") else float(value)


def _aggregate_player_season_metric(
    season_lookups: list[dict[str, dict[str, Any]]],
    column: dict[str, Any],
) -> float | None:
    aggregate = str(column.get("aggregate") or "sum")
    if aggregate == "ratio":
        numerator_group, numerator_metric = tuple(column.get("numerator") or ("", ""))
        denominator_group, denominator_metric = tuple(column.get("denominator") or ("", ""))
        numerator = sum(
            _player_season_metric_value(metric_lookup, str(numerator_group), str(numerator_metric)) or 0.0
            for metric_lookup in season_lookups
        )
        denominator = sum(
            _player_season_metric_value(metric_lookup, str(denominator_group), str(denominator_metric)) or 0.0
            for metric_lookup in season_lookups
        )
        return None if denominator <= 0 else numerator / denominator
    if aggregate == "passer_rating":
        attempts = sum(
            _player_season_metric_value(metric_lookup, "Passing", "Attempts") or 0.0
            for metric_lookup in season_lookups
        )
        if attempts <= 0:
            return None
        completions = sum(
            _player_season_metric_value(metric_lookup, "Passing", "Completions") or 0.0
            for metric_lookup in season_lookups
        )
        passing_yards = sum(
            _player_season_metric_value(metric_lookup, "Passing", "Passing yards") or 0.0
            for metric_lookup in season_lookups
        )
        passing_tds = sum(
            _player_season_metric_value(metric_lookup, "Passing", "Pass TD") or 0.0
            for metric_lookup in season_lookups
        )
        interceptions = sum(
            _player_season_metric_value(metric_lookup, "Passing", "Interceptions") or 0.0
            for metric_lookup in season_lookups
        )
        return ((8.4 * passing_yards) + (330.0 * passing_tds) + (100.0 * completions) - (200.0 * interceptions)) / attempts

    group_name = str(column.get("group") or "")
    metric_name = str(column.get("metric") or "")
    values = [
        value
        for value in (
            _player_season_metric_value(metric_lookup, group_name, metric_name)
            for metric_lookup in season_lookups
        )
        if value is not None
    ]
    if not values:
        return None
    if aggregate == "max":
        return max(values)
    return sum(values)


def _format_player_season_table_value(format_kind: str, value: Any) -> str:
    if value in (None, ""):
        return "--"
    return _format_player_stat_value(format_kind, value)


def _build_player_season_stat_tables(
    bucket: str,
    season_stat_history: dict[int, dict[str, Any]],
    roster_history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not season_stat_history:
        return []

    roster_by_season = {
        int(row.get("season_year") or 0): row
        for row in roster_history
        if row.get("season_year") is not None
    }
    ordered_seasons = sorted(
        (payload for payload in season_stat_history.values() if payload),
        key=lambda payload: int(payload.get("season_year") or 0),
        reverse=True,
    )
    season_rows: list[dict[str, Any]] = []
    for payload in ordered_seasons:
        season_year = int(payload.get("season_year") or 0)
        roster_row = roster_by_season.get(season_year, {})
        season_rows.append(
            {
                "season_year": season_year,
                "team_name": payload.get("team_name") or roster_row.get("team_name"),
                "team_slug": payload.get("team_slug") or roster_row.get("team_slug"),
                "week": int(payload.get("week") or 0),
                "metric_lookup": _build_player_season_metric_lookup(list(payload.get("raw_rows") or [])),
            }
        )

    if not season_rows:
        return []

    season_lookups = [row["metric_lookup"] for row in season_rows]
    tables: list[dict[str, Any]] = []
    for section in _player_season_table_catalog(bucket):
        columns = list(section.get("columns") or [])
        rendered_rows: list[dict[str, Any]] = []
        has_values = False
        for row in season_rows:
            cells: list[dict[str, str]] = []
            for column in columns:
                numeric_value = _aggregate_player_season_metric([row["metric_lookup"]], column)
                display_value = _format_player_season_table_value(str(column.get("format") or "whole"), numeric_value)
                if display_value != "--":
                    has_values = True
                cells.append({"label": str(column.get("label") or ""), "value": display_value})
            rendered_rows.append(
                {
                    "season_label": str(row.get("season_year") or ""),
                    "team_name": str(row.get("team_name") or "--"),
                    "team_slug": row.get("team_slug"),
                    "context": f"Week {int(row.get('week') or 0)} snapshot" if row.get("week") else "",
                    "cells": cells,
                    "row_kind": "season",
                }
            )

        if not has_values:
            continue

        career_cells: list[dict[str, str]] = []
        for column in columns:
            career_value = _aggregate_player_season_metric(season_lookups, column)
            career_cells.append(
                {
                    "label": str(column.get("label") or ""),
                    "value": _format_player_season_table_value(str(column.get("format") or "whole"), career_value),
                }
            )
        rendered_rows.append(
            {
                "season_label": "Career",
                "team_name": f"{len(season_rows)} loaded season{'s' if len(season_rows) != 1 else ''}",
                "team_slug": None,
                "context": "Career row reflects the stat seasons currently loaded in this database.",
                "cells": career_cells,
                "row_kind": "career",
            }
        )
        tables.append(
            {
                "title": str(section.get("title") or "Season stats"),
                "subtitle": str(section.get("subtitle") or ""),
                "columns": [str(column.get("label") or "") for column in columns],
                "rows": rendered_rows,
            }
        )
    return tables


def _build_player_advanced_rows(bucket: str, explorer_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred = {
        "QB": [("Value", "Passing WEPA"), ("Usage", "Role share"), ("Usage", "Pass share"), ("Usage", "Rush share"), ("Passing", "Yards / attempt"), ("Passing", "Passer rating")],
        "RB": [("Value", "Rushing WEPA"), ("Usage", "Role share"), ("Usage", "Rush share"), ("Usage", "Pass share"), ("Rushing", "Yards / carry"), ("Receiving", "Yards / catch")],
        "WR": [("Usage", "Pass share"), ("Usage", "Role share"), ("Receiving", "Yards / catch"), ("Returns", "Kick return avg"), ("Returns", "Punt return avg")],
        "TE": [("Usage", "Pass share"), ("Usage", "Role share"), ("Receiving", "Yards / catch")],
        "DEF": [("Defense", "TFL"), ("Defense", "Sacks"), ("Defense", "QB hurries"), ("Defense", "Pass breakups"), ("Defense", "Interceptions")],
    }
    row_lookup = {
        _player_stat_metric_key(row.get("group"), row.get("metric")): row
        for row in explorer_rows
    }
    rows: list[dict[str, Any]] = []
    for group_name, metric_name in preferred.get(bucket, []):
        row = row_lookup.get(_player_stat_metric_key(group_name, metric_name))
        if row is None:
            continue
        rows.append(
            {
                "metric": metric_name,
                "value": row.get("value"),
                "peer": _compact_player_peer_note(row.get("rank_text"), row.get("percentile_text")),
                "context": row.get("context"),
            }
        )
    return rows[:6]


def _build_player_archetype(bucket: str, explorer_rows: list[dict[str, Any]], level_code: str) -> dict[str, Any]:
    row_lookup = {
        _player_stat_metric_key(row.get("group"), row.get("metric")): row
        for row in explorer_rows
    }
    def pct(group_name: str, metric_name: str) -> int:
        row = row_lookup.get(_player_stat_metric_key(group_name, metric_name), {})
        text = str(row.get("percentile_text") or "")
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else 0

    tags: list[str] = []
    summary = "This player profile will sharpen as more advanced context is loaded."

    if bucket == "QB":
        volume = max(pct("Passing", "Passing yards"), pct("Passing", "Attempts"))
        efficiency = max(pct("Passing", "Completion %"), pct("Passing", "Passer rating"))
        explosive = pct("Passing", "Yards / attempt")
        rushing = pct("Rushing", "Rushing yards")
        if volume >= 85:
            tags.append("High-volume passer")
        elif volume >= 65:
            tags.append("Steady volume")
        if efficiency >= 85:
            tags.append("Highly efficient")
        elif efficiency >= 65:
            tags.append("Efficient")
        if explosive >= 85:
            tags.append("Vertical threat")
        if rushing >= 75:
            tags.append("Dual-threat")
        elif rushing <= 40:
            tags.append("Pocket-leaning")
        summary = (
            f"{' | '.join(tags[:3]) if tags else 'Balanced quarterback'} against {level_code} QB peers. "
            f"The quickest read is whether the profile wins on volume, efficiency, explosiveness, or rushing value."
        )
    elif bucket == "RB":
        rush = pct("Rushing", "Rushing yards")
        efficiency = pct("Rushing", "Yards / carry")
        receiving = pct("Receiving", "Receptions")
        if rush >= 85:
            tags.append("Workhorse")
        if efficiency >= 80:
            tags.append("Efficient runner")
        if receiving >= 70:
            tags.append("Passing-game back")
        summary = f"{' | '.join(tags[:3]) if tags else 'Backfield contributor'} against {level_code} RB peers."
    elif bucket in {"WR", "TE"}:
        target = pct("Receiving", "Receptions")
        explosive = pct("Receiving", "Yards / catch")
        return_game = max(pct("Returns", "Kick return yards"), pct("Returns", "Punt return yards"))
        if target >= 85:
            tags.append("Target magnet")
        if explosive >= 80:
            tags.append("Big-play receiver")
        if return_game >= 70:
            tags.append("All-purpose weapon")
        summary = f"{' | '.join(tags[:3]) if tags else 'Receiving weapon'} against {level_code} receiving peers."
    elif bucket == "DEF":
        disruption = max(pct("Defense", "TFL"), pct("Defense", "Sacks"), pct("Defense", "QB hurries"))
        coverage = max(pct("Defense", "Pass breakups"), pct("Defense", "Interceptions"))
        tackles = pct("Defense", "Total tackles")
        if disruption >= 85:
            tags.append("High-disruption defender")
        if coverage >= 80:
            tags.append("Coverage splash")
        if tackles >= 80:
            tags.append("High-volume tackler")
        summary = f"{' | '.join(tags[:3]) if tags else 'Defensive contributor'} against {level_code} defenders."

    if not tags:
        tags.append("Balanced profile")
    return {"tags": tags[:4], "summary": summary}


def _player_stat_lower_is_better(metric_key: str) -> bool:
    return metric_key in {
        "passing::interceptions",
        "passing::sacks-taken",
        "ball-security::fumbles-lost",
    }


def _player_stat_meta(category: str, stat_type: str) -> tuple[str, str, str, str]:
    key = (re.sub(r"[^a-z0-9]+", "", category.lower()), re.sub(r"[^a-z0-9]+", "", stat_type.lower()))
    catalog = {
        ("passing", "att"): ("Attempts", "Passing", "Volume", "whole"),
        ("passing", "completions"): ("Completions", "Passing", "Volume", "whole"),
        ("passing", "yds"): ("Passing yards", "Passing", "Volume", "whole"),
        ("passing", "pct"): ("Completion %", "Passing", "Efficiency", "pct"),
        ("passing", "avg"): ("Yards / completion", "Passing", "Efficiency", "decimal"),
        ("passing", "ypa"): ("Yards / attempt", "Passing", "Efficiency", "decimal"),
        ("passing", "lng"): ("Longest pass", "Passing", "Explosive", "whole"),
        ("passing", "td"): ("Pass TD", "Passing", "Scoring", "whole"),
        ("passing", "int"): ("Interceptions", "Passing", "Turnovers", "whole"),
        ("passing", "sack"): ("Sacks taken", "Passing", "Pressure", "whole"),
        ("passing", "syl"): ("Sack yards lost", "Passing", "Pressure", "whole"),
        ("passing", "rtg"): ("Passer rating", "Passing", "Efficiency", "decimal"),
        ("rushing", "car"): ("Carries", "Rushing", "Volume", "whole"),
        ("rushing", "yds"): ("Rushing yards", "Rushing", "Volume", "whole"),
        ("rushing", "avg"): ("Yards / carry", "Rushing", "Efficiency", "decimal"),
        ("rushing", "ypc"): ("Yards / carry", "Rushing", "Efficiency", "decimal"),
        ("rushing", "lng"): ("Longest rush", "Rushing", "Explosive", "whole"),
        ("rushing", "td"): ("Rush TD", "Rushing", "Scoring", "whole"),
        ("receiving", "rec"): ("Receptions", "Receiving", "Volume", "whole"),
        ("receiving", "yds"): ("Receiving yards", "Receiving", "Volume", "whole"),
        ("receiving", "avg"): ("Yards / catch", "Receiving", "Efficiency", "decimal"),
        ("receiving", "ypr"): ("Yards / catch", "Receiving", "Efficiency", "decimal"),
        ("receiving", "lng"): ("Longest catch", "Receiving", "Explosive", "whole"),
        ("receiving", "td"): ("Receiving TD", "Receiving", "Scoring", "whole"),
        ("defensive", "tot"): ("Total tackles", "Defense", "Volume", "whole"),
        ("defensive", "solo"): ("Solo tackles", "Defense", "Volume", "whole"),
        ("defensive", "tfl"): ("TFL", "Defense", "Disruption", "decimal"),
        ("defensive", "sacks"): ("Sacks", "Defense", "Disruption", "decimal"),
        ("defensive", "pd"): ("Pass breakups", "Defense", "Coverage", "whole"),
        ("defensive", "qbhur"): ("QB hurries", "Defense", "Disruption", "whole"),
        ("defensive", "td"): ("Defensive TD", "Defense", "Scoring", "whole"),
        ("interceptions", "int"): ("Interceptions", "Defense", "Takeaways", "whole"),
        ("interceptions", "yds"): ("INT return yards", "Defense", "Takeaways", "whole"),
        ("interceptions", "avg"): ("INT return avg", "Defense", "Takeaways", "decimal"),
        ("interceptions", "td"): ("Pick-six TD", "Defense", "Scoring", "whole"),
        ("fumbles", "fum"): ("Forced fumbles", "Defense", "Takeaways", "whole"),
        ("fumbles", "rec"): ("Fumbles recovered", "Defense", "Takeaways", "whole"),
        ("fumbles", "lost"): ("Fumbles lost", "Ball Security", "Turnovers", "whole"),
        ("kicking", "fgm"): ("FG made", "Kicking", "Scoring", "whole"),
        ("kicking", "pct"): ("FG %", "Kicking", "Efficiency", "pct"),
        ("kicking", "pts"): ("Kicking points", "Kicking", "Scoring", "whole"),
        ("kickreturns", "no"): ("Kick returns", "Returns", "Volume", "whole"),
        ("kickreturns", "yds"): ("Kick return yards", "Returns", "Volume", "whole"),
        ("kickreturns", "avg"): ("Kick return avg", "Returns", "Efficiency", "decimal"),
        ("kickreturns", "td"): ("Kick return TD", "Returns", "Scoring", "whole"),
        ("puntreturns", "no"): ("Punt returns", "Returns", "Volume", "whole"),
        ("puntreturns", "yds"): ("Punt return yards", "Returns", "Volume", "whole"),
        ("puntreturns", "avg"): ("Punt return avg", "Returns", "Efficiency", "decimal"),
        ("puntreturns", "td"): ("Punt return TD", "Returns", "Scoring", "whole"),
    }
    return catalog.get(key, (f"{category.title()} {stat_type.upper()}".strip(), category.title() or "Other", "Metric", "whole"))


def _include_player_stat_row(category: str, stat_type: str, value: Any) -> bool:
    numeric = float(value or 0.0)
    if abs(numeric) > 0.0:
        return True
    keep_zeroes = {
        ("passing", "int"),
        ("fumbles", "lost"),
        ("interceptions", "int"),
        ("defensive", "sacks"),
        ("defensive", "tfl"),
        ("passing", "td"),
        ("rushing", "td"),
        ("receiving", "td"),
    }
    key = (re.sub(r"[^a-z0-9]+", "", category.lower()), re.sub(r"[^a-z0-9]+", "", stat_type.lower()))
    return key in keep_zeroes


def _format_player_stat_value(format_kind: str, value: Any) -> str:
    if format_kind == "pct":
        return _fmt_pct_fraction(value)
    if format_kind == "decimal":
        return _fmt_decimal(value, 1)
    return _fmt_whole(value)


def _player_stat_priority(bucket: str, group_name: str, label: str) -> int:
    group_key = _board_filter_value(group_name)
    label_key = _board_filter_value(label)
    priorities = {
        "QB": {
            ("passing", "passing-yards"): 1,
            ("passing", "pass-td"): 2,
            ("passing", "completion"): 3,
            ("passing", "yards-attempt"): 4,
            ("rushing", "rushing-yards"): 5,
            ("value", "passing-wepa"): 6,
            ("usage", "role-share"): 7,
        },
        "RB": {
            ("rushing", "rushing-yards"): 1,
            ("rushing", "rush-td"): 2,
            ("rushing", "yards-carry"): 3,
            ("receiving", "receptions"): 4,
            ("receiving", "receiving-yards"): 5,
            ("value", "rushing-wepa"): 6,
            ("usage", "role-share"): 7,
        },
        "WR": {
            ("receiving", "receptions"): 1,
            ("receiving", "receiving-yards"): 2,
            ("receiving", "receiving-td"): 3,
            ("receiving", "yards-catch"): 4,
            ("returns", "kick-return-yards"): 5,
            ("returns", "punt-return-yards"): 6,
            ("usage", "pass-share"): 7,
        },
        "TE": {
            ("receiving", "receptions"): 1,
            ("receiving", "receiving-yards"): 2,
            ("receiving", "receiving-td"): 3,
            ("receiving", "yards-catch"): 4,
            ("usage", "pass-share"): 5,
        },
        "DEF": {
            ("defense", "total-tackles"): 1,
            ("defense", "tfl"): 2,
            ("defense", "sacks"): 3,
            ("defense", "interceptions"): 4,
            ("defense", "pass-breakups"): 5,
            ("defense", "qb-hurries"): 6,
        },
    }
    bucket_priorities = priorities.get(bucket, {})
    for (target_group, target_metric), rank in bucket_priorities.items():
        if group_key == target_group and target_metric in label_key:
            return rank
    fallback_groups = {
        "passing": 20,
        "rushing": 30,
        "receiving": 40,
        "defense": 50,
        "returns": 60,
        "usage": 70,
        "value": 80,
        "ball-security": 90,
        "kicking": 95,
    }
    return fallback_groups.get(group_key, 99)


def _default_player_stat_filter(bucket: str) -> str:
    return {
        "QB": "passing",
        "RB": "rushing",
        "WR": "receiving",
        "TE": "receiving",
        "DEF": "defense",
    }.get(bucket, "all")


def _player_stat_available_groups(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    ordered: list[dict[str, str]] = [{"key": "all", "label": "All Metrics"}]
    seen = {"all"}
    for row in rows:
        key = str(row.get("group_key") or "")
        label = str(row.get("group") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append({"key": key, "label": label})
    return ordered


def _player_stat_snapshot_note(season_year: int | None, week: int | None) -> str:
    season_text = "--" if season_year in (None, 0) else str(int(season_year or 0))
    week_text = "--" if week in (None, 0) else str(int(week or 0))
    return f"{season_text} season snapshot | through week {week_text}"


def _build_player_signature_story(
    player_identity: dict[str, Any],
    primary_team: dict[str, Any],
    current_snapshot: dict[str, Any],
    roster_history: list[dict[str, Any]],
    stat_profile: dict[str, Any],
    heisman_years: list[dict[str, Any]],
    recruiting_profile: dict[str, Any],
    transfer_profile: dict[str, Any],
    honors_history: list[dict[str, Any]],
) -> dict[str, Any]:
    player_name = str(player_identity.get("full_name") or "This player")
    position = _normalize_position(player_identity.get("position"))
    bucket = _position_filter_bucket(position)
    stats = stat_profile.get("stats") or {}
    usage = stat_profile.get("usage") or {}
    current_rank = current_snapshot.get("nowcast_rank")
    current_rank_text = _display_rank_text(current_rank)
    team_name = str(primary_team.get("team_name") or "his current team")
    conference_name = str(primary_team.get("conference_name") or "")
    team_count = len({str(row.get("team_name") or "") for row in roster_history if row.get("team_name")})
    transferred = team_count > 1
    usage_overall = None if usage.get("usage_overall") is None else float(usage.get("usage_overall") or 0.0)
    total_return_tds = float(stats.get("kick_returns_td", 0.0)) + float(stats.get("punt_returns_td", 0.0))
    total_return_yards = float(stats.get("kick_returns_yds", 0.0)) + float(stats.get("punt_returns_yds", 0.0))
    heisman_live = current_rank is not None and int(current_rank) <= 25
    blue_chip = bool(recruiting_profile.get("blue_chip"))
    transfer_count = int(transfer_profile.get("transfer_count") or 0)
    honor_count = len(honors_history)

    title = "What makes this player interesting right now"
    if bucket == "DEF":
        title = "Why this is a rare defensive case"
        body = (
            f"{player_name} is trying to climb the steepest award hill in college football: a defensive candidacy. "
            f"The hook is the disruption profile on {team_name}'s defense, with {_fmt_decimal(stats.get('defensive_sacks'), 1)} sacks, "
            f"{_fmt_decimal(stats.get('defensive_tfl'), 1)} tackles for loss, and {_fmt_whole(stats.get('interceptions_int'))} interceptions "
            f"through the current loaded season. For a defender, the question is never just production; it is whether elite disruption and team context can become nationally undeniable."
        )
    elif bucket == "QB" and (float(stats.get("rushing_td", 0.0)) >= 5 or float(stats.get("rushing_yds", 0.0)) >= 250):
        title = "Why this is a two-channel quarterback case"
        body = (
            f"The unusual part of {player_name}'s case is that the production comes in two channels, not one. "
            f"For {team_name}, he has {_fmt_whole(stats.get('passing_yds'))} passing yards and {_fmt_whole(stats.get('passing_td'))} touchdown passes, "
            f"but he also adds {_fmt_whole(stats.get('rushing_yds'))} rushing yards and {_fmt_whole(stats.get('rushing_td'))} rushing scores. "
            f"That kind of dual-threat load tends to create a more resilient Heisman case because the offense can tilt the game in multiple ways."
        )
    elif bucket == "RB" and (float(stats.get("receiving_rec", 0.0)) >= 25 or total_return_tds > 0 or total_return_yards >= 150):
        title = "Why this is more than a rushing profile"
        body = (
            f"{player_name} is not a one-lane back. The profile is interesting because the workload spills beyond pure rushing volume: "
            f"{_fmt_whole(stats.get('rushing_yds'))} rushing yards, {_fmt_whole(stats.get('receiving_rec'))} catches, and "
            f"{_fmt_whole(total_return_yards)} return yards for {team_name}. That kind of all-purpose footprint gives the card a much richer story than a basic carry total."
        )
    elif blue_chip and heisman_live:
        title = "Why the pedigree actually matters here"
        body = (
            f"{player_name} was a real recruiting acquisition, not an out-of-nowhere name, and that matters when a Heisman case starts to form. "
            f"The card shows a {_recruit_stars_text(recruiting_profile.get('top_entry', {}).get('stars'))} profile with a "
            f"{_display_recruit_rank(recruiting_profile.get('top_entry', {}).get('national_rank'))} national ranking lane, which helps explain why voters and media were ready to notice fast once the production showed up."
        )
    elif transfer_count > 0 and heisman_live:
        title = "Why the transfer arc matters"
        body = (
            f"{player_name}'s path is unusually interesting because the candidacy survived movement. "
            f"The page has {transfer_count} portal move{'s' if transfer_count != 1 else ''} on file, and national relevance after a change in program usually signals that role, fit, and surrounding ecosystem all amplified the player instead of merely carrying him."
        )
    elif honor_count > 0 and not heisman_live:
        title = "Why the honors trail matters"
        body = (
            f"The useful clue on this card is not just the Heisman rank, but the broader honors spine. "
            f"{player_name} already has {honor_count} loaded recognition item{'s' if honor_count != 1 else ''}, which helps distinguish a player who is merely productive from one who is already earning selector-level validation."
        )
    elif bucket in {"WR", "TE"} and (total_return_tds > 0 or float(stats.get("rushing_td", 0.0)) > 0):
        title = "Why the profile pops beyond receiving"
        body = (
            f"The most interesting thing about {player_name} is that he shows up in multiple game states. "
            f"He is a receiver first, but the profile also includes designed touches and return-game juice, which means his value is not limited to a conventional route tree."
        )
    elif conference_name in G5_CONFERENCES and heisman_live:
        title = "Why this is a national-outlier candidacy"
        body = (
            f"The real intrigue here is that {player_name} is trying to force a national award conversation from outside the power-conference spotlight. "
            f"A {conference_name} player sitting at {current_rank_text} has to be overwhelming enough that the production becomes impossible for voters to ignore."
        )
    elif transferred and heisman_live:
        title = "Why the transfer arc matters"
        body = (
            f"{player_name}'s card is compelling because the national relevance arrived fast after a change in surroundings. "
            f"The transfer path matters: when a player changes programs and still rises into the {current_rank_text} tier, it usually means the role, production, and team fit all clicked immediately."
        )
    else:
        body = (
            f"{player_name}'s story is about how role and output meet each other. "
            f"For {team_name}, the card already shows enough current-season production to explain why he is on the serious-player board, "
            f"and the next layer is determining whether the profile is just very good or actually distinctive."
        )

    support_cards = [
        {
            "label": "Current place",
            "value": current_rank_text,
            "submetric": f"{_probability_text(current_snapshot.get('win_probability'))} win | {_probability_text(current_snapshot.get('finalist_probability'))} finalist",
        },
        {
            "label": "Role load",
            "value": _fmt_pct_fraction(usage_overall),
            "submetric": "Overall usage share" if usage_overall is not None else "Role share still loading",
        },
        {
            "label": "Profile quirk",
            "value": (
                "Blue-chip pedigree"
                if blue_chip
                else "Transfer path"
                if transferred
                else "Honors spine"
                if honor_count > 0
                else "Defensive rarity"
                if bucket == "DEF"
                else "All-purpose load"
                if total_return_tds > 0 or float(stats.get("receiving_rec", 0.0)) >= 25
                else "National contender"
                if heisman_live
                else "Development arc"
            ),
            "submetric": (
                _display_recruit_rank(recruiting_profile.get("top_entry", {}).get("national_rank"))
                if blue_chip
                else f"{transfer_count} portal move{'s' if transfer_count != 1 else ''}"
                if transferred
                else f"{honor_count} honors loaded"
                if honor_count > 0
                else f"{_fmt_whole(total_return_yards)} return yds"
                if total_return_yards > 0
                else f"{_fmt_decimal(stats.get('defensive_sacks'), 1)} sacks | {_fmt_decimal(stats.get('defensive_tfl'), 1)} TFL"
                if bucket == "DEF"
                else "The card should explain why this profile stands out"
            ),
        },
    ]
    return {
        "title": title,
        "body": body,
        "cards": support_cards,
    }


def _build_player_recruiting_profile(recruiting_history: list[dict[str, Any]]) -> dict[str, Any]:
    if not recruiting_history:
        return {
            "top_entry": {},
            "blue_chip": False,
            "recruit_types": [],
            "cards": [
                {"label": "Top pedigree", "value": "No recruit row", "submetric": "CFBD has no matched recruiting profile on file"},
                {"label": "Composite rating", "value": "--", "submetric": "Recruit feed not matched"},
                {"label": "Signed with", "value": "--", "submetric": "Commitment history unavailable"},
                {"label": "Origin", "value": "--", "submetric": "School and hometown unavailable"},
            ],
            "rows": [],
        }
    top_entry = next(
        (
            row
            for row in recruiting_history
            if row.get("rating") is not None or row.get("stars") is not None or row.get("national_rank") is not None
        ),
        recruiting_history[0] if recruiting_history else {},
    )
    blue_chip = bool((top_entry.get("stars") or 0) >= 4)
    recruit_types = sorted({str(row.get("recruit_type") or "").strip() for row in recruiting_history if row.get("recruit_type")})
    cards = [
        {
            "label": "Top pedigree",
            "value": _recruit_stars_text(top_entry.get("stars")),
            "submetric": _display_recruit_rank(top_entry.get("national_rank")),
        },
        {
            "label": "Composite rating",
            "value": _fmt_decimal(top_entry.get("rating"), 4),
            "submetric": str(top_entry.get("recruit_type") or "Recruit type TBD"),
        },
        {
            "label": "Signed with",
            "value": str(top_entry.get("team_name") or top_entry.get("committed_team") or "--"),
            "submetric": str(top_entry.get("season_year") or "--"),
        },
        {
            "label": "Origin",
            "value": str(top_entry.get("school_name") or "--"),
            "submetric": _location_text(top_entry.get("city"), top_entry.get("state_province"), top_entry.get("country")),
        },
    ]
    rows = [
        {
            "label": str(row.get("season_year") or "--"),
            "value": f"{_recruit_stars_text(row.get('stars'))} | {_fmt_decimal(row.get('rating'), 4)}",
            "context": " | ".join(
                part
                for part in [
                    _display_recruit_rank(row.get("national_rank")),
                    str(row.get("recruit_type") or "").strip(),
                    str(row.get("team_name") or row.get("committed_team") or "").strip(),
                ]
                if part
            )
            or "Recruiting profile",
        }
        for row in recruiting_history[:5]
    ]
    return {
        "top_entry": top_entry,
        "blue_chip": blue_chip,
        "recruit_types": recruit_types,
        "cards": cards,
        "rows": rows,
    }


def _build_player_transfer_profile(transfer_history: list[dict[str, Any]]) -> dict[str, Any]:
    latest = transfer_history[0] if transfer_history else {}
    transfer_count = len(transfer_history)
    cards = [
        {
            "label": "Portal moves",
            "value": str(transfer_count),
            "submetric": "Programs changed on file" if transfer_count else "No portal entry on file",
        },
        {
            "label": "Latest destination",
            "value": str(latest.get("to_team_name") or "--"),
            "submetric": str(latest.get("season_year") or "--"),
        },
        {
            "label": "Transfer stars",
            "value": _recruit_stars_text(latest.get("transfer_stars")),
            "submetric": "CFBD transfer rating context",
        },
        {
            "label": "Eligibility",
            "value": str(latest.get("eligibility") or "--"),
            "submetric": str(latest.get("transfer_date") or "Transfer date TBD"),
        },
    ]
    rows = [
        {
            "label": str(row.get("season_year") or "--"),
            "value": f"{str(row.get('from_team_name') or '--')} -> {str(row.get('to_team_name') or '--')}",
            "context": " | ".join(
                part
                for part in [
                    _recruit_stars_text(row.get("transfer_stars")),
                    _fmt_decimal(row.get("rating"), 4),
                    str(row.get("eligibility") or "").strip(),
                ]
                if part and part != "--"
            )
            or "Transfer context",
        }
        for row in transfer_history[:6]
    ]
    return {
        "latest_entry": latest,
        "transfer_count": transfer_count,
        "cards": cards,
        "rows": rows,
    }


def _filter_projected_heisman_honors(
    honors_history: list[dict[str, Any]],
    current_season: int,
) -> list[dict[str, Any]]:
    """Drop 'Heisman Trophy Winner' honor rows for the current modeled season
    (or later), since the projection pipeline writes speculative winner rows
    into player_honors before the award is canonically recorded. Historical
    seasons retain their canonical winner rows.
    """
    cleaned: list[dict[str, Any]] = []
    for row in honors_history:
        honor_name = str(row.get("honor_name") or "").strip().lower()
        honor_team = str(row.get("honor_team") or "").strip().lower()
        claims_win = "heisman" in honor_name and ("winner" in honor_name or honor_team == "winner")
        if claims_win:
            season_year = int(row.get("season_year") or 0)
            if season_year >= int(current_season):
                continue
        cleaned.append(row)
    return cleaned


def _build_player_trophy_case(heisman_years: list[dict[str, Any]], honors_history: list[dict[str, Any]]) -> list[dict[str, str]]:
    winner_years = [int(row.get("season_year") or 0) for row in heisman_years if row.get("winner_flag")]
    finalist_years = [int(row.get("season_year") or 0) for row in heisman_years if row.get("finalist_flag")]
    vote_years = [
        int(row.get("season_year") or 0)
        for row in heisman_years
        if row.get("official_place") is not None or (row.get("total_points") not in (None, 0))
    ]
    best_finish = min(
        [int(row.get("official_place")) for row in heisman_years if row.get("official_place") is not None],
        default=None,
    )
    all_america = [row for row in honors_history if str(row.get("honor_scope") or "").lower() == "all_america"]
    all_conference = [row for row in honors_history if str(row.get("honor_scope") or "").lower() == "all_conference"]
    weekly = [row for row in honors_history if "week" in str(row.get("honor_scope") or "").lower() or str(row.get("honor_scope") or "").lower() == "weekly_honor"]
    consensus_count = sum(1 for row in honors_history if row.get("consensus_flag"))
    unanimous_count = sum(1 for row in honors_history if row.get("unanimous_flag"))
    items: list[dict[str, str]] = []
    if winner_years:
        years_text = ", ".join(str(year) for year in winner_years)
        items.append(
            {
                "kicker": "Heisman",
                "title": "Heisman Trophy winner",
                "body": f"Won the award in {years_text}. This should always live at the front of the card's trophy case.",
            }
        )
    elif best_finish is not None:
        items.append(
            {
                "kicker": "Heisman",
                "title": f"Best official finish: #{best_finish}",
                "body": "Finished in the top end of the Heisman vote on a completed ballot, which is a cleaner historical signal than model-only attention.",
            }
        )
    if finalist_years:
        years_text = ", ".join(str(year) for year in finalist_years)
        items.append(
            {
                "kicker": "Finalist",
                "title": f"{len(finalist_years)} finalist season{'s' if len(finalist_years) != 1 else ''}",
                "body": f"Invited into the official finalist tier in {years_text}. That belongs in the trophy case, not buried in a table.",
            }
        )
    if all_america:
        items.append(
            {
                "kicker": "All-America",
                "title": f"{len(all_america)} All-America selection{'s' if len(all_america) != 1 else ''}",
                "body": "National selector recognition is one of the strongest non-Heisman signals on a player card and should sit near the top of the showcase.",
            }
        )
    if all_conference:
        items.append(
            {
                "kicker": "All-Conference",
                "title": f"{len(all_conference)} all-conference honor{'s' if len(all_conference) != 1 else ''}",
                "body": "Conference-level recognition helps anchor whether a player is merely statistically loud or actually viewed as elite within his competitive lane.",
            }
        )
    if consensus_count or unanimous_count:
        items.append(
            {
                "kicker": "Selectors",
                "title": "Consensus-grade recognition",
                "body": f"{consensus_count} consensus tag{'s' if consensus_count != 1 else ''} and {unanimous_count} unanimous tag{'s' if unanimous_count != 1 else ''} are on file.",
            }
        )
    if weekly:
        items.append(
            {
                "kicker": "Weekly",
                "title": f"{len(weekly)} weekly honor{'s' if len(weekly) != 1 else ''}",
                "body": "Weekly awards are smaller than season-end honors, but they help tell the week-by-week story of when a candidacy or breakout started to gather force.",
            }
        )
    if vote_years:
        items.append(
            {
                "kicker": "Votes",
                "title": f"Heisman votes in {len(set(vote_years))} season{'s' if len(set(vote_years)) != 1 else ''}",
                "body": "Even lower-volume award recognition is worth preserving because it marks seasons where a player entered the national conversation.",
            }
        )
    if not honors_history:
        items.append(
            {
                "kicker": "Honors",
                "title": "Honors pipeline is ready",
                "body": "This card is now structured to absorb All-America, all-conference, player-of-the-week, watch-list, and postseason award rows as soon as those sources are imported.",
            }
        )
    return items


def _query_rows_for_player_ids(
    db: Database,
    query_template: str,
    player_ids: list[int],
    extra_params: tuple[Any, ...] = (),
    chunk_size: int = 350,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in _chunked(player_ids, chunk_size):
        placeholders = ", ".join("?" for _ in chunk)
        rows.extend(db.query_all(query_template.format(placeholders=placeholders), tuple(chunk) + extra_params))
    return rows


def _query_player_season_stat_history_rows(
    db: Database,
    player_ids: list[int],
    chunk_size: int = 350,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    query_template = """
        with latest as (
          select
            player_id,
            season_year,
            max(week) as max_week
          from player_season_stats
          where player_id in ({placeholders})
          group by player_id, season_year
        )
        select
          pss.player_id,
          pss.season_year,
          pss.week,
          pss.team_id,
          t.slug as team_slug,
          t.canonical_name as team_name,
          pss.category,
          pss.stat_type,
          pss.stat_value_num
        from player_season_stats pss
        join latest
          on latest.player_id = pss.player_id
         and latest.season_year = pss.season_year
         and latest.max_week = pss.week
        left join teams t on t.team_id = pss.team_id
        order by pss.player_id asc, pss.season_year desc, pss.category asc, pss.stat_type asc
    """
    for chunk in _chunked(player_ids, chunk_size):
        placeholders = ", ".join("?" for _ in chunk)
        rows.extend(db.query_all(query_template.format(placeholders=placeholders), tuple(chunk)))
    return rows


def _chunked(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def fetch_site_pulse(
    db: Database,
    summary: dict[str, Any],
    rankings: list[RankingRow] | None = None,
) -> dict[str, Any]:
    season_year = int(summary["season_year"])
    model_run_id = int(summary["model_run_id"])
    week = int(summary["week"])
    archive_row = db.query_one(
        """
        select
          min(season_year) as first_season,
          max(season_year) as last_season,
          count(distinct season_year) as loaded_seasons,
          count(*) as total_games,
          sum(case when home_points is not null and away_points is not null then 1 else 0 end) as completed_games
        from games
        """
    ) or {}
    current_row = db.query_one(
        """
        select
          count(*) as current_season_games,
          sum(case when home_points is not null and away_points is not null then 1 else 0 end) as current_season_completed_games,
          avg((home_points + away_points) / 2.0) as base_points
        from games
        where season_year = %(season_year)s
        """,
        {"season_year": season_year},
    ) or {}
    team_rows = db.query_all(
        """
        select distinct coalesce(ts.level_code, t.level_code) as level_code, c.conference_name
        from team_seasons ts
        join teams t on t.team_id = ts.team_id
        left join conferences c on c.conference_id = ts.conference_id
        where ts.season_year = %(season_year)s
        """,
        {"season_year": season_year},
    )
    if rankings is not None:
        tracked_teams = len(rankings)
        tracked_conferences_set: set[tuple[str, str]] = set()
        for ranking in rankings:
            level = str(ranking.level_code or "")
            conference = None if ranking.conference_name is None else str(ranking.conference_name)
            if conference:
                tracked_conferences_set.add((level, conference))
        tracked_conferences_count = len(tracked_conferences_set)
    else:
        tracked_teams = 0
        tracked_conferences_set = set()
        for row in team_rows:
            level_code = str(row["level_code"] or "")
            conference_name = None if row.get("conference_name") is None else str(row["conference_name"])
            if not is_site_eligible_team(level_code, conference_name):
                continue
            tracked_teams += 1
            if conference_name:
                tracked_conferences_set.add((level_code, conference_name))
        tracked_conferences_count = len(tracked_conferences_set)

    ranked_rows = db.query_all(
        """
        select coalesce(ts.level_code, t.level_code) as level_code, c.conference_name
        from power_ratings_weekly p
        join teams t on t.team_id = p.team_id
        left join team_seasons ts
          on ts.team_id = t.team_id
         and ts.season_year = p.season_year
        left join conferences c on c.conference_id = ts.conference_id
        where p.model_run_id = %(model_run_id)s
          and p.week = %(week)s
        """,
        {"model_run_id": model_run_id, "week": week},
    )
    ranked_teams = 0
    level_breakout: dict[str, int] = {}
    for row in ranked_rows:
        level_code = str(row["level_code"] or "")
        conference_name = None if row.get("conference_name") is None else str(row["conference_name"])
        if not is_site_eligible_team(level_code, conference_name):
            continue
        ranked_teams += 1
        level_breakout[level_code] = level_breakout.get(level_code, 0) + 1
    data_cutoff = str(summary.get("data_cutoff_utc") or "")
    data_cutoff_display = data_cutoff.replace("T", " ").replace("Z", " UTC") if data_cutoff else "Unavailable"
    return {
        "season_year": season_year,
        "model_week": week,
        "model_version": str(summary.get("model_version") or ""),
        "data_cutoff_display": data_cutoff_display,
        "first_season": archive_row.get("first_season"),
        "last_season": archive_row.get("last_season"),
        "loaded_seasons": int(archive_row.get("loaded_seasons") or 0),
        "total_games": int(archive_row.get("total_games") or 0),
        "completed_games": int(archive_row.get("completed_games") or 0),
        "current_season_games": int(current_row.get("current_season_games") or 0),
        "current_season_completed_games": int(current_row.get("current_season_completed_games") or 0),
        "tracked_teams": tracked_teams,
        "tracked_conferences": tracked_conferences_count,
        "ranked_teams": ranked_teams,
        "base_points": float(current_row.get("base_points") or 28.0),
        "home_field_advantage": 2.3,
        "level_breakout": level_breakout,
    }


def fetch_historical_season_ledger(db: Database) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        with team_results as (
          select
            season_year,
            team_id,
            sum(win_flag) as wins,
            sum(loss_flag) as losses,
            count(*) as games_played,
            sum(points_for) as points_for,
            sum(points_against) as points_against
          from (
            select
              g.season_year,
              g.home_team_id as team_id,
              case when coalesce(g.home_points, -999) > coalesce(g.away_points, -999) then 1 else 0 end as win_flag,
              case when coalesce(g.home_points, -999) < coalesce(g.away_points, -999) then 1 else 0 end as loss_flag,
              coalesce(g.home_points, 0) as points_for,
              coalesce(g.away_points, 0) as points_against
            from games g
            where g.home_points is not null and g.away_points is not null
            union all
            select
              g.season_year,
              g.away_team_id as team_id,
              case when coalesce(g.away_points, -999) > coalesce(g.home_points, -999) then 1 else 0 end as win_flag,
              case when coalesce(g.away_points, -999) < coalesce(g.home_points, -999) then 1 else 0 end as loss_flag,
              coalesce(g.away_points, 0) as points_for,
              coalesce(g.home_points, 0) as points_against
            from games g
            where g.home_points is not null and g.away_points is not null
          ) results
          group by season_year, team_id
        ),
        final_runs as (
          select mr.season_year, max(mr.model_run_id) as model_run_id
          from model_runs mr
          where exists (
            select 1
            from power_ratings_weekly p
            where p.model_run_id = mr.model_run_id
          )
          group by mr.season_year
        ),
        final_power as (
          select
            p.season_year,
            p.team_id,
            p.power_rating,
            coalesce(r.resume_score, 0) as resume_score,
            dense_rank() over (
              partition by p.season_year
              order by p.power_rating desc, coalesce(r.resume_score, 0) desc, t.canonical_name asc
            ) as final_rank
          from power_ratings_weekly p
          join final_runs fr on fr.model_run_id = p.model_run_id
          join model_runs mr on mr.model_run_id = fr.model_run_id and p.week = mr.week
          join teams t on t.team_id = p.team_id
          left join resume_ratings_weekly r
            on r.model_run_id = p.model_run_id
           and r.team_id = p.team_id
           and r.week = p.week
        )
        select
          tr.season_year,
          tr.team_id,
          t.slug,
          t.canonical_name as team_name,
          coalesce(ts.level_code, t.level_code) as level_code,
          c.conference_name,
          tr.wins,
          tr.losses,
          tr.games_played,
          tr.points_for,
          tr.points_against,
          fp.power_rating as end_power,
          fp.resume_score as end_resume,
          fp.final_rank
        from team_results tr
        join teams t on t.team_id = tr.team_id
        left join team_seasons ts
          on ts.team_id = tr.team_id
         and ts.season_year = tr.season_year
        left join conferences c on c.conference_id = ts.conference_id
        left join final_power fp
          on fp.season_year = tr.season_year
         and fp.team_id = tr.team_id
        order by tr.season_year desc, fp.final_rank asc, fp.power_rating desc, t.canonical_name asc
        """
    )
    ledger: list[dict[str, Any]] = []
    for row in rows:
        level_code = str(row.get("level_code") or "")
        conference_name = None if row.get("conference_name") is None else str(row.get("conference_name"))
        if not is_site_eligible_team(level_code, conference_name):
            continue
        points_for = int(row.get("points_for") or 0)
        points_against = int(row.get("points_against") or 0)
        games_played = max(1, int(row.get("games_played") or 0))
        ledger.append(
            {
                "season_year": int(row["season_year"]),
                "team_id": int(row["team_id"]),
                "slug": str(row.get("slug") or ""),
                "team_name": str(row.get("team_name") or ""),
                "level_code": level_code,
                "conference_name": conference_name,
                "wins": int(row.get("wins") or 0),
                "losses": int(row.get("losses") or 0),
                "games_played": games_played,
                "points_for": points_for,
                "points_against": points_against,
                "margin": points_for - points_against,
                "win_pct": float(int(row.get("wins") or 0) / games_played),
                "end_power": None if row.get("end_power") is None else float(row.get("end_power")),
                "end_resume": None if row.get("end_resume") is None else float(row.get("end_resume")),
                "final_rank": None if row.get("final_rank") is None else int(row.get("final_rank")),
            }
        )
    _attach_historical_public_metric_context(ledger)
    return ledger


def build_history_hub(historical_season_ledger: list[dict[str, Any]]) -> dict[str, Any]:
    if not historical_season_ledger:
        return {
            "cards": [],
            "loaded_seasons": 0,
            "team_seasons": 0,
            "greatest_seasons": [],
            "strongest_seasons": [],
            "roughest_seasons": [],
            "turnarounds": [],
            "collapses": [],
            "sustained_programs": [],
            "volatile_programs": [],
            "closest_to_peak": [],
            "best_two_year_runs": [],
            "level_cards": [],
            "season_summaries": [],
            "explorer_rows": [],
        }

    ordered_by_resume = [row for row in historical_season_ledger if _first_present_float(row.get("end_resume_display"), row.get("end_resume")) is not None]
    ordered_by_power = [row for row in historical_season_ledger if _first_present_float(row.get("end_power_display"), row.get("end_power")) is not None]
    ordered_by_resume.sort(
        key=lambda row: (
            -float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0),
            -float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0),
            -float(row.get("win_pct") or 0.0),
        )
    )
    ordered_by_power.sort(
        key=lambda row: (
            -float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0),
            -float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0),
            -float(row.get("win_pct") or 0.0),
        )
    )
    roughest_seasons = sorted(
        historical_season_ledger,
        key=lambda row: (
            float(row.get("win_pct") or 0.0),
            float(row.get("end_power") if row.get("end_power") is not None else 999.0),
            float(row.get("end_resume") if row.get("end_resume") is not None else 999.0),
            float(row.get("margin") or 0.0),
        ),
    )

    seasons_loaded = sorted({int(row["season_year"]) for row in historical_season_ledger})
    season_groups: dict[int, list[dict[str, Any]]] = {}
    program_groups: dict[int, list[dict[str, Any]]] = {}
    for row in historical_season_ledger:
        season_groups.setdefault(int(row["season_year"]), []).append(row)
        program_groups.setdefault(int(row["team_id"]), []).append(row)
    for rows in program_groups.values():
        rows.sort(key=lambda row: int(row["season_year"]))

    rises: list[dict[str, Any]] = []
    falls: list[dict[str, Any]] = []
    sustained_candidates: list[dict[str, Any]] = []
    volatile_candidates: list[dict[str, Any]] = []
    closest_to_peak_candidates: list[dict[str, Any]] = []
    best_two_year_runs: list[dict[str, Any]] = []

    for rows in program_groups.values():
        power_rows = [row for row in rows if _first_present_float(row.get("end_power_display"), row.get("end_power")) is not None]
        if len(power_rows) >= 2:
            values = [float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0) for row in power_rows]
            average_power = sum(values) / len(values)
            latest_row = power_rows[-1]
            historical_baseline_rows = power_rows[:-1]
            baseline_sample = historical_baseline_rows[-3:] if historical_baseline_rows else power_rows[-3:]
            baseline_power = (
                sum(float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0) for row in baseline_sample) / len(baseline_sample)
                if baseline_sample
                else float(_first_present_float(latest_row.get("end_power_display"), latest_row.get("end_power")) or 0.0)
            )
            latest_power = float(_first_present_float(latest_row.get("end_power_display"), latest_row.get("end_power")) or 0.0)
            peak_row = max(
                power_rows,
                key=lambda row: float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0),
            )
            peak_power = float(_first_present_float(peak_row.get("end_power_display"), peak_row.get("end_power")) or 0.0)
            closest_to_peak_candidates.append(
                {
                    **latest_row,
                    "season_count": len(power_rows),
                    "peak_power": peak_power,
                    "peak_season_year": int(peak_row.get("season_year") or 0),
                    "gap_to_peak": peak_power - latest_power,
                    "baseline_power": baseline_power,
                    "vs_baseline": latest_power - float(baseline_power),
                }
            )
            sustained_candidates.append(
                {
                    **latest_row,
                    "season_count": len(power_rows),
                    "average_end_power": average_power,
                }
            )
            power_range = max(values) - min(values)
            volatile_candidates.append(
                {
                    **latest_row,
                    "season_count": len(power_rows),
                    "power_range": power_range,
                }
            )
            for previous_row, current_row in zip(power_rows, power_rows[1:], strict=False):
                if int(current_row.get("season_year") or 0) - int(previous_row.get("season_year") or 0) != 1:
                    continue
                best_two_year_runs.append(
                    {
                        **current_row,
                        "window_start": int(previous_row.get("season_year") or 0),
                        "window_end": int(current_row.get("season_year") or 0),
                        "combined_wins": int(previous_row.get("wins") or 0) + int(current_row.get("wins") or 0),
                        "combined_losses": int(previous_row.get("losses") or 0) + int(current_row.get("losses") or 0),
                        "average_end_power": (
                            float(_first_present_float(previous_row.get("end_power_display"), previous_row.get("end_power")) or 0.0)
                            + float(_first_present_float(current_row.get("end_power_display"), current_row.get("end_power")) or 0.0)
                        )
                        / 2.0,
                        "average_end_resume": (
                            float(_first_present_float(previous_row.get("end_resume_display"), previous_row.get("end_resume")) or 0.0)
                            + float(_first_present_float(current_row.get("end_resume_display"), current_row.get("end_resume")) or 0.0)
                        )
                        / 2.0,
                    }
                )
            for previous_row, current_row in zip(power_rows, power_rows[1:], strict=False):
                delta = float(_first_present_float(current_row.get("end_power_display"), current_row.get("end_power")) or 0.0) - float(
                    _first_present_float(previous_row.get("end_power_display"), previous_row.get("end_power")) or 0.0
                )
                candidate = {
                    **current_row,
                    "previous_season_year": int(previous_row["season_year"]),
                    "power_delta": delta,
                    "previous_power": float(_first_present_float(previous_row.get("end_power_display"), previous_row.get("end_power")) or 0.0),
                }
                if delta >= 0:
                    rises.append(candidate)
                else:
                    falls.append(candidate)

    rises.sort(key=lambda row: (-float(row["power_delta"]), -float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0)))
    falls.sort(key=lambda row: (float(row["power_delta"]), float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0)))
    sustained_candidates.sort(
        key=lambda row: (-float(row["average_end_power"]), -float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0))
    )
    volatile_candidates.sort(
        key=lambda row: (
            -float(row["power_range"]),
            -float(row.get("average_end_power") or _first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0),
        )
    )
    closest_to_peak_candidates.sort(
        key=lambda row: (
            float(row.get("gap_to_peak") or 999.0),
            -float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0),
            -float(row.get("vs_baseline") or 0.0),
        )
    )
    best_two_year_runs.sort(
        key=lambda row: (
            -float(row.get("average_end_power") or 0.0),
            -float(row.get("average_end_resume") or 0.0),
            -(int(row.get("combined_wins") or 0) - int(row.get("combined_losses") or 0)),
        )
    )

    cards: list[dict[str, Any]] = []
    if ordered_by_resume:
        cards.append(
            {
                "label": "Greatest Loaded Season",
                "title": f"{ordered_by_resume[0]['season_year']} {ordered_by_resume[0]['team_name']}",
                "slug": ordered_by_resume[0]["slug"],
                "detail": _history_record_line(ordered_by_resume[0]),
                "body": (
                    f"Resume {_public_resume_text(ordered_by_resume[0].get('end_resume_display'))} / 100 with power {_public_power_text(ordered_by_resume[0].get('end_power_display'))}. "
                    f"{ordered_by_resume[0]['level_code']} season that finished #{_display_rank_value(ordered_by_resume[0].get('final_rank'))} on the loaded board."
                ),
            }
        )
    if ordered_by_power:
        cards.append(
            {
                "label": "Strongest Loaded Team",
                "title": f"{ordered_by_power[0]['season_year']} {ordered_by_power[0]['team_name']}",
                "slug": ordered_by_power[0]["slug"],
                "detail": _history_record_line(ordered_by_power[0]),
                "body": (
                    f"Power {_public_power_text(ordered_by_power[0].get('end_power_display'))} at season close. "
                    f"Resume {_public_resume_text(ordered_by_power[0].get('end_resume_display'))} / 100, final board slot #{_display_rank_value(ordered_by_power[0].get('final_rank'))}."
                ),
            }
        )
    if rises:
        cards.append(
            {
                "label": "Biggest Year-Over-Year Rise",
                "title": f"{rises[0]['team_name']} in {rises[0]['season_year']}",
                "slug": rises[0]["slug"],
                "detail": _history_record_line(rises[0]),
                "body": (
                    f"Up {_public_power_text(rises[0].get('power_delta'))} power points from {int(rises[0]['previous_season_year'])} "
                    f"to {int(rises[0]['season_year'])}, with the loaded finish climbing to #{_display_rank_value(rises[0].get('final_rank'))}."
                ),
            }
        )
    if closest_to_peak_candidates:
        cards.append(
            {
                "label": "Closest To Peak Right Now",
                "title": f"{closest_to_peak_candidates[0]['team_name']} {closest_to_peak_candidates[0]['season_year']}",
                "slug": closest_to_peak_candidates[0]["slug"],
                "detail": f"{float(closest_to_peak_candidates[0]['gap_to_peak'] or 0.0):.1f} off peak",
                "body": (
                    f"The current loaded season closed only {float(closest_to_peak_candidates[0]['gap_to_peak'] or 0.0):.1f} power points below "
                    f"this program's peak, and {_public_power_text(closest_to_peak_candidates[0].get('vs_baseline'))} versus its recent standard."
                ),
            }
        )
    if sustained_candidates:
        cards.append(
            {
                "label": "Best Sustained Program",
                "title": str(sustained_candidates[0]["team_name"]),
                "slug": sustained_candidates[0]["slug"],
                "detail": f"{int(sustained_candidates[0]['season_count'])} loaded seasons",
                "body": (
                    f"Average end-of-season power {_public_power_text(sustained_candidates[0].get('average_end_power'))} across the loaded span, "
                    f"which is exactly the kind of historical anchor that should shape preseason starting points."
                ),
            }
        )
    if best_two_year_runs:
        cards.append(
            {
                "label": "Best Loaded Two-Year Run",
                "title": f"{best_two_year_runs[0]['team_name']} {best_two_year_runs[0]['window_start']}-{best_two_year_runs[0]['window_end']}",
                "slug": best_two_year_runs[0]["slug"],
                "detail": f"{int(best_two_year_runs[0]['combined_wins'])}-{int(best_two_year_runs[0]['combined_losses'])} combined",
                "body": (
                    f"Average power {_public_power_text(best_two_year_runs[0].get('average_end_power'))} and average resume "
                    f"{_public_resume_text(best_two_year_runs[0].get('average_end_resume'))} / 100 across back-to-back loaded seasons."
                ),
            }
        )
    if falls and len(cards) < 6:
        cards.append(
            {
                "label": "Steepest Loaded Drop",
                "title": f"{falls[0]['team_name']} in {falls[0]['season_year']}",
                "slug": falls[0]["slug"],
                "detail": _history_record_line(falls[0]),
                "body": (
                    f"Down {abs(float(falls[0]['power_delta'] or 0.0)):.1f} power points from {int(falls[0]['previous_season_year'])} "
                    f"to {int(falls[0]['season_year'])}, a reminder that program arcs matter as much as single snapshots."
                ),
            }
        )
    if volatile_candidates and len(cards) < 6:
        cards.append(
            {
                "label": "Most Volatile Program",
                "title": str(volatile_candidates[0]["team_name"]),
                "slug": volatile_candidates[0]["slug"],
                "detail": f"{int(volatile_candidates[0]['season_count'])} loaded seasons",
                "body": (
                    f"Power range {float(volatile_candidates[0]['power_range'] or 0.0):.1f} across loaded seasons, "
                    f"which is why prior success should influence preseason power without fully hard-coding destiny."
                ),
            }
        )

    level_cards: list[dict[str, Any]] = []
    for level_code in ("FBS", "FCS", "DII", "DIII"):
        level_rows = [row for row in historical_season_ledger if str(row.get("level_code") or "") == level_code]
        if not level_rows:
            continue
        level_resume_rows = [row for row in level_rows if row.get("end_resume") is not None]
        level_power_rows = [row for row in level_rows if row.get("end_power") is not None]
        if not level_resume_rows and not level_power_rows:
            continue
        resume_leader = (
            max(
                level_resume_rows,
                key=lambda row: (
                    float(row.get("end_resume") or 0.0),
                    float(row.get("end_power") or 0.0),
                    float(row.get("win_pct") or 0.0),
                ),
            )
            if level_resume_rows
            else None
        )
        power_leader = (
            max(
                level_power_rows,
                key=lambda row: (
                    float(row.get("end_power") or 0.0),
                    float(row.get("end_resume") or 0.0),
                    float(row.get("win_pct") or 0.0),
                ),
            )
            if level_power_rows
            else None
        )
        anchor_row = resume_leader or power_leader
        if anchor_row is None:
            continue
        level_cards.append(
            {
                "level_code": level_code,
                "slug": str(anchor_row.get("slug") or ""),
                "title": f"{level_code} Historical Peak",
                "body": _level_history_card_body(level_code, resume_leader, power_leader),
                "detail": _history_record_line(anchor_row),
            }
        )

    season_summaries: list[dict[str, Any]] = []
    for season_year in sorted(season_groups.keys(), reverse=True):
        rows = season_groups[season_year]
        resume_rows = [row for row in rows if row.get("end_resume") is not None]
        power_rows = [row for row in rows if row.get("end_power") is not None]
        top_resume = (
            max(
                resume_rows,
                key=lambda row: (
                    float(row.get("end_resume") or 0.0),
                    float(row.get("end_power") or 0.0),
                    float(row.get("win_pct") or 0.0),
                ),
            )
            if resume_rows
            else None
        )
        top_power = (
            max(
                power_rows,
                key=lambda row: (
                    float(row.get("end_power") or 0.0),
                    float(row.get("end_resume") or 0.0),
                    float(row.get("win_pct") or 0.0),
                ),
            )
            if power_rows
            else None
        )
        best_record = max(
            rows,
            key=lambda row: (
                float(row.get("win_pct") or 0.0),
                int(row.get("wins") or 0),
                float(row.get("end_resume") or 0.0),
            ),
        )
        season_summaries.append(
            {
                "season_year": season_year,
                "team_count": len(rows),
                "top_resume": top_resume,
                "top_power": top_power,
                "best_record": best_record,
            }
        )

    explorer_rows = build_history_explorer_rows(historical_season_ledger, seasons_loaded[-1])

    return {
        "cards": cards,
        "loaded_seasons": len(seasons_loaded),
        "team_seasons": len(historical_season_ledger),
        "first_season": seasons_loaded[0],
        "last_season": seasons_loaded[-1],
        "greatest_seasons": ordered_by_resume[:24],
        "strongest_seasons": ordered_by_power[:24],
        "roughest_seasons": roughest_seasons[:24],
        "turnarounds": rises[:18],
        "collapses": falls[:18],
        "sustained_programs": sustained_candidates[:18],
        "volatile_programs": volatile_candidates[:18],
        "closest_to_peak": closest_to_peak_candidates[:18],
        "best_two_year_runs": best_two_year_runs[:18],
        "level_cards": level_cards,
        "season_summaries": season_summaries,
        "explorer_rows": explorer_rows,
    }


def build_team_history_insights(history_rows: list[dict[str, Any]], current_season_year: int) -> list[dict[str, str]]:
    if not history_rows:
        return []

    ordered = sorted(history_rows, key=lambda row: int(row.get("season_year") or 0))
    rows_with_power = [row for row in ordered if row.get("end_power") is not None]
    rows_with_resume = [row for row in ordered if row.get("end_resume") is not None]
    current_row = next((row for row in ordered if int(row.get("season_year") or 0) == current_season_year), ordered[-1])
    previous_row = next((row for row in reversed(ordered[:-1]) if row.get("end_power") is not None), None)
    strongest_row = (
        max(rows_with_power, key=lambda row: float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0))
        if rows_with_power
        else ordered[-1]
    )
    best_resume_row = (
        max(rows_with_resume, key=lambda row: float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0))
        if rows_with_resume
        else ordered[-1]
    )
    roughest_row = min(
        ordered,
        key=lambda row: (
            float(row.get("win_pct") or 0.0),
            float(row.get("end_power") if row.get("end_power") is not None else 999.0),
        ),
    )
    best_record_row = max(
        ordered,
        key=lambda row: (
            float(row.get("win_pct") or 0.0),
            int(row.get("wins") or 0),
            float(row.get("end_resume") or 0.0),
        ),
    )

    cards = [
        {
            "kicker": "Strongest Loaded Team",
            "title": f"{int(strongest_row['season_year'])} Season",
            "body": (
                f"Ended at power {_public_power_text(strongest_row.get('end_power_display'))}, "
                f"record {int(strongest_row.get('wins') or 0)}-{int(strongest_row.get('losses') or 0)}, "
                f"and final loaded-board rank #{_display_rank_value(strongest_row.get('final_rank'))}."
            ),
        },
        {
            "kicker": "Best Loaded Resume",
            "title": f"{int(best_resume_row['season_year'])} Season",
            "body": (
                f"Resume {_public_resume_text(best_resume_row.get('end_resume_display'))} / 100 with "
                f"{int(best_resume_row.get('wins') or 0)} wins and a {float(best_resume_row.get('win_pct') or 0.0):.0%} win rate."
            ),
        },
        {
            "kicker": "Best Record",
            "title": f"{int(best_record_row['wins'])}-{int(best_record_row['losses'])}",
            "body": (
                f"The cleanest loaded season by results came in {int(best_record_row['season_year'])}, "
                f"with a margin of {int(best_record_row.get('margin') or 0):+d}."
            ),
        },
        {
            "kicker": "Roughest Loaded Season",
            "title": f"{int(roughest_row['season_year'])} Season",
            "body": (
                f"{int(roughest_row.get('wins') or 0)}-{int(roughest_row.get('losses') or 0)} with "
                f"power {_public_power_text(roughest_row.get('end_power_display'))} and margin {int(roughest_row.get('margin') or 0):+d}."
            ),
        },
    ]

    if previous_row and current_row.get("end_power") is not None and previous_row.get("end_power") is not None:
        previous_power = float(_first_present_float(previous_row.get("end_power_display"), previous_row.get("end_power")) or 0.0)
        current_power = float(_first_present_float(current_row.get("end_power_display"), current_row.get("end_power")) or 0.0)
        power_delta = current_power - previous_power
        cards.insert(
            2,
            {
                "kicker": "Year-Over-Year Swing",
                "title": f"{_public_power_text(power_delta)} power",
                "body": (
                    f"From {int(previous_row['season_year'])} to {int(current_row['season_year'])}, the program moved "
                    f"from {_public_power_text(previous_power)} to {_public_power_text(current_power)}."
                ),
            },
        )
    return cards[:4]


def build_team_history_profile(history_rows: list[dict[str, Any]], current_season_year: int) -> dict[str, Any]:
    if not history_rows:
        return {
            "loaded_seasons": 0,
            "current_row": None,
            "baseline_power": None,
            "current_vs_baseline": None,
            "current_power_rank": None,
            "current_resume_rank": None,
            "power_percentile": None,
            "resume_percentile": None,
            "peak_power_row": None,
            "best_resume_row": None,
            "best_finish_row": None,
            "best_record_row": None,
            "gap_to_peak_power": None,
            "best_power_since": None,
            "best_resume_since": None,
        }

    ordered = sorted(history_rows, key=lambda row: int(row.get("season_year") or 0))
    rows_with_power = [row for row in ordered if row.get("end_power") is not None]
    rows_with_resume = [row for row in ordered if row.get("end_resume") is not None]
    current_row = next((row for row in ordered if int(row.get("season_year") or 0) == current_season_year), ordered[-1])
    historical_baseline_rows = [
        row for row in rows_with_power if int(row.get("season_year") or 0) != current_season_year
    ]
    baseline_sample = historical_baseline_rows[-3:] if historical_baseline_rows else rows_with_power[-3:]
    baseline_power = (
        sum(float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0) for row in baseline_sample) / len(baseline_sample)
        if baseline_sample
        else None
    )
    current_power = _first_present_float(current_row.get("end_power_display"), current_row.get("end_power"))
    current_resume = _first_present_float(current_row.get("end_resume_display"), current_row.get("end_resume"))
    peak_power_row = (
        max(rows_with_power, key=lambda row: float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0))
        if rows_with_power
        else None
    )
    best_resume_row = (
        max(rows_with_resume, key=lambda row: float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0))
        if rows_with_resume
        else None
    )
    best_finish_rows = [row for row in ordered if row.get("final_rank") is not None]
    best_finish_row = min(best_finish_rows, key=lambda row: int(row.get("final_rank") or 999999)) if best_finish_rows else None
    best_record_row = max(
        ordered,
        key=lambda row: (
            float(row.get("win_pct") or 0.0),
            int(row.get("wins") or 0),
            float(row.get("end_resume") or 0.0),
        ),
    )
    current_power_rank = None
    if current_power is not None and rows_with_power:
        current_power_rank = 1 + sum(
            1
            for row in rows_with_power
            if float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0) > current_power
        )
    current_resume_rank = None
    if current_resume is not None and rows_with_resume:
        current_resume_rank = 1 + sum(
            1
            for row in rows_with_resume
            if float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0) > current_resume
        )
    power_percentile = None
    if current_power_rank is not None and rows_with_power:
        power_percentile = 100.0 * (len(rows_with_power) - current_power_rank + 1) / len(rows_with_power)
    resume_percentile = None
    if current_resume_rank is not None and rows_with_resume:
        resume_percentile = 100.0 * (len(rows_with_resume) - current_resume_rank + 1) / len(rows_with_resume)
    prior_better_power_rows = [
        row
        for row in rows_with_power
        if int(row.get("season_year") or 0) < int(current_row.get("season_year") or 0)
        and float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0) >= float(current_power or 0.0)
    ]
    prior_better_resume_rows = [
        row
        for row in rows_with_resume
        if int(row.get("season_year") or 0) < int(current_row.get("season_year") or 0)
        and float(_first_present_float(row.get("end_resume_display"), row.get("end_resume")) or 0.0) >= float(current_resume or 0.0)
    ]
    return {
        "loaded_seasons": len(ordered),
        "current_row": current_row,
        "baseline_power": baseline_power,
        "current_vs_baseline": (
            None if baseline_power is None or current_power is None else current_power - float(baseline_power)
        ),
        "current_power_rank": current_power_rank,
        "current_resume_rank": current_resume_rank,
        "power_percentile": power_percentile,
        "resume_percentile": resume_percentile,
        "peak_power_row": peak_power_row,
        "best_resume_row": best_resume_row,
        "best_finish_row": best_finish_row,
        "best_record_row": best_record_row,
        "gap_to_peak_power": (
            None
            if peak_power_row is None or current_power is None
            else float(_first_present_float(peak_power_row.get("end_power_display"), peak_power_row.get("end_power")) or 0.0)
            - float(current_power)
        ),
        "best_power_since": (
            None
            if current_power is None
            else max((int(row.get("season_year") or 0) for row in prior_better_power_rows), default=None)
        ),
        "best_resume_since": (
            None
            if current_resume is None
            else max((int(row.get("season_year") or 0) for row in prior_better_resume_rows), default=None)
        ),
    }


def _level_history_card_body(
    level_code: str,
    resume_leader: dict[str, Any] | None,
    power_leader: dict[str, Any] | None,
) -> str:
    if resume_leader and power_leader and resume_leader.get("slug") == power_leader.get("slug") and int(
        resume_leader.get("season_year") or 0
    ) == int(power_leader.get("season_year") or 0):
        return (
            f"{resume_leader['season_year']} {resume_leader['team_name']} owns both the best loaded resume "
            f"({_public_resume_text(resume_leader.get('end_resume_display'))} / 100) and the strongest closing power "
            f"({_public_power_text(power_leader.get('end_power_display'))}) in {level_code}."
        )
    parts: list[str] = []
    if resume_leader:
        parts.append(
            f"Best resume: {resume_leader['season_year']} {resume_leader['team_name']} "
            f"({_public_resume_text(resume_leader.get('end_resume_display'))} / 100)."
        )
    if power_leader:
        parts.append(
            f"Strongest team: {power_leader['season_year']} {power_leader['team_name']} "
            f"({_public_power_text(power_leader.get('end_power_display'))} power)."
        )
    return " ".join(parts)


def _history_record_line(row: dict[str, Any]) -> str:
    rank_text = f" | #{_display_rank_value(row.get('final_rank'))}" if row.get("final_rank") is not None else ""
    return f"{int(row.get('wins') or 0)}-{int(row.get('losses') or 0)}{rank_text}"


def _display_rank_value(value: Any) -> str:
    if value in (None, ""):
        return "--"
    return str(int(value))


def build_conference_pages(team_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    level_power_groups: dict[str, list[float]] = {}
    level_resume_groups: dict[str, list[float]] = {}
    level_resume_display_groups: dict[str, list[float]] = {}
    global_power_values = [float(team_data["ranking"].power_rating) for team_data in team_pages if team_data.get("ranking")]
    overall_power_mean = sum(global_power_values) / len(global_power_values) if global_power_values else 0.0
    for team_data in team_pages:
        ranking: RankingRow = team_data["ranking"]
        conference_name = _clean_conference_name(str(team_data["team"].get("conference_name") or f"{ranking.level_code} Independents"))
        grouped.setdefault((conference_name, ranking.level_code), []).append(team_data)
        level_power_groups.setdefault(ranking.level_code, []).append(float(ranking.power_rating))
        level_resume_groups.setdefault(ranking.level_code, []).append(float(ranking.resume_score))
        level_resume_display_groups.setdefault(ranking.level_code, []).append(float(ranking.resume_display or 0.0))

    level_baselines = {
        level_code: {
            "round_robin_power": _conference_round_robin_rating(power_values, target_win_pct=0.50),
            "upper_strength": _conference_upper_strength(power_values),
            "average_power": sum(power_values) / len(power_values),
            "median_power": _median(power_values),
            "average_resume": sum(level_resume_groups.get(level_code, [0.0])) / max(1, len(level_resume_groups.get(level_code, []))),
            "average_resume_display": sum(level_resume_display_groups.get(level_code, [0.0])) / max(1, len(level_resume_display_groups.get(level_code, []))),
        }
        for level_code, power_values in level_power_groups.items()
        if power_values
    }

    conference_pages: list[dict[str, Any]] = []
    for (conference_name, level_code), items in grouped.items():
        ordered_items = sorted(items, key=lambda item: item["ranking"].rank)
        top_team = ordered_items[0]
        best_resume_team = max(ordered_items, key=lambda item: item["ranking"].resume_score)
        level_baseline = level_baselines.get(level_code, {})
        sample_weight = _conference_sample_weight(len(ordered_items))
        power_values = [float(item["ranking"].power_rating) for item in ordered_items]
        resume_values = [float(item["ranking"].resume_score) for item in ordered_items]
        resume_display_values = [float(item["ranking"].resume_display or 0.0) for item in ordered_items]
        average_power_raw = sum(power_values) / len(power_values)
        average_resume = sum(resume_values) / len(resume_values)
        average_resume_display = sum(resume_display_values) / len(resume_display_values)
        median_power_raw = _median(power_values)
        median_resume = _median(resume_values)
        depth_cut = ordered_items[: min(5, len(ordered_items))]
        depth_index = sum(item["ranking"].power_rating for item in depth_cut) / max(1, len(depth_cut))
        betting_rows = [item.get("betting_summary") or {} for item in ordered_items if (item.get("betting_summary") or {}).get("games_with_lines")]
        conference_cover_rates = [float(row["cover_rate"]) for row in betting_rows if row.get("cover_rate") is not None]
        conference_wins_above = [float(row.get("wins_above_market") or 0.0) for row in betting_rows]
        conference_over_rates = [float(row["over_rate"]) for row in betting_rows if row.get("over_rate") is not None]
        best_ats_team = max(
            (item for item in ordered_items if (item.get("betting_summary") or {}).get("cover_rate") is not None),
            key=lambda item: (
                float((item.get("betting_summary") or {}).get("cover_rate") or 0.0),
                int((item.get("betting_summary") or {}).get("games_with_lines") or 0),
            ),
            default=None,
        )
        market_surprise_team = max(
            (item for item in ordered_items if (item.get("betting_summary") or {}).get("games_with_lines")),
            key=lambda item: float((item.get("betting_summary") or {}).get("wins_above_market") or -999.0),
            default=None,
        )
        round_robin_power = _shrink_metric(
            _conference_round_robin_rating(power_values, target_win_pct=0.50),
            float(level_baseline.get("round_robin_power", average_power_raw)),
            sample_weight,
        )
        upper_strength = _shrink_metric(
            _conference_upper_strength(power_values),
            float(level_baseline.get("upper_strength", average_power_raw)),
            sample_weight,
        )
        average_power = _shrink_metric(
            average_power_raw,
            float(level_baseline.get("average_power", average_power_raw)),
            sample_weight,
        )
        median_power = _shrink_metric(
            median_power_raw,
            float(level_baseline.get("median_power", median_power_raw)),
            sample_weight,
        )
        parity_gap = float(top_team["ranking"].power_rating) - median_power_raw
        power_sd = _std_dev(power_values)
        top_25_count = sum(1 for item in ordered_items if item["ranking"].rank <= 25)
        top_100_count = sum(1 for item in ordered_items if item["ranking"].rank <= 100)
        total_wins = sum(int(item["season_summary"].get("wins") or 0) for item in ordered_items)
        total_losses = sum(int(item["season_summary"].get("losses") or 0) for item in ordered_items)
        conference_pages.append(
            {
                "conference_name": conference_name,
                "level_code": level_code,
                "slug": _conference_slug(conference_name, level_code),
                "team_count": len(ordered_items),
                "sample_weight": sample_weight,
                "round_robin_power": round_robin_power,
                "round_robin_power_display": round_robin_power - overall_power_mean,
                "upper_strength": upper_strength,
                "upper_strength_display": upper_strength - overall_power_mean,
                "average_power": average_power,
                "average_power_display": average_power - overall_power_mean,
                "average_resume": average_resume,
                "average_resume_display": average_resume_display,
                "median_power": median_power,
                "median_power_display": median_power - overall_power_mean,
                "median_resume": median_resume,
                "depth_index": depth_index,
                "depth_index_display": depth_index - overall_power_mean,
                "average_cover_rate": None if not conference_cover_rates else sum(conference_cover_rates) / len(conference_cover_rates),
                "average_wins_above_market": None if not conference_wins_above else sum(conference_wins_above) / len(conference_wins_above),
                "average_over_rate": None if not conference_over_rates else sum(conference_over_rates) / len(conference_over_rates),
                "parity_gap": parity_gap,
                "power_sd": power_sd,
                "top_25_count": top_25_count,
                "top_100_count": top_100_count,
                "wins": total_wins,
                "losses": total_losses,
                "top_team": top_team,
                "best_resume_team": best_resume_team,
                "best_ats_team": best_ats_team,
                "market_surprise_team": market_surprise_team,
                "teams": ordered_items,
                "profile_note": _conference_profile_note(
                    conference_name,
                    round_robin_power,
                    upper_strength,
                    average_power,
                    average_resume,
                    median_power,
                    parity_gap,
                    top_25_count,
                    ordered_items,
                ),
            }
        )
    conference_pages.sort(
        key=lambda item: (
            -item["round_robin_power"],
            -item["median_power"],
            -item["upper_strength"],
            -item["average_resume"],
            item["conference_name"],
        )
    )
    overall_rank = 0
    level_rankings: dict[str, int] = {}
    for conference in conference_pages:
        overall_rank += 1
        level_code = str(conference["level_code"])
        level_rankings[level_code] = level_rankings.get(level_code, 0) + 1
        conference["overall_rank"] = overall_rank
        conference["level_rank"] = level_rankings[level_code]
    return conference_pages


def _conference_round_robin_rating(values: list[float], target_win_pct: float = 0.50, volatility: float = 14.5) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    low = ordered[0] - 5.0 * volatility
    high = ordered[-1] + 5.0 * volatility
    for _ in range(48):
        midpoint = (low + high) / 2.0
        win_pct = sum(_normal_cdf((midpoint - value) / volatility) for value in ordered) / len(ordered)
        if win_pct < target_win_pct:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def _conference_upper_strength(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted((float(value) for value in values), reverse=True)
    if len(ordered) == 1:
        return ordered[0]
    weights = [(1.0 - (index / (len(ordered) - 1))) ** 2 for index in range(len(ordered))]
    weight_total = sum(weights) or 1.0
    return sum(value * weight for value, weight in zip(ordered, weights, strict=False)) / weight_total


def _conference_sample_weight(team_count: int) -> float:
    return float(team_count) / float(team_count + 4)


def _shrink_metric(raw_value: float, baseline_value: float, sample_weight: float) -> float:
    return sample_weight * raw_value + (1.0 - sample_weight) * baseline_value


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0


def _std_dev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _american_odds_to_implied_prob(odds: Any) -> float | None:
    if odds in (None, "", 0):
        return None
    try:
        american = int(odds)
    except (TypeError, ValueError):
        return None
    if american > 0:
        return 100.0 / (american + 100.0)
    if american < 0:
        return (-american) / ((-american) + 100.0)
    return None


def _team_line_context(team_id: int, row: dict[str, Any]) -> dict[str, Any]:
    is_home = int(row["home_team_id"]) == team_id
    spread_home_close = row.get("spread_home_close")
    total_close = row.get("total_close")
    moneyline_home_close = row.get("moneyline_home_close")
    moneyline_away_close = row.get("moneyline_away_close")
    team_points = row.get("home_points") if is_home else row.get("away_points")
    opp_points = row.get("away_points") if is_home else row.get("home_points")

    team_spread_close = None
    if spread_home_close is not None:
        team_spread_close = float(spread_home_close if is_home else -float(spread_home_close))

    expected_margin = None if team_spread_close is None else -float(team_spread_close)
    team_moneyline = moneyline_home_close if is_home else moneyline_away_close
    implied_win_prob = _american_odds_to_implied_prob(team_moneyline)
    if implied_win_prob is None and expected_margin is not None:
        implied_win_prob = _normal_cdf(expected_margin / 14.5)

    ats_margin = None
    total_margin = None
    ats_result = None
    total_result = None
    if team_points is not None and opp_points is not None:
        team_margin = int(team_points) - int(opp_points)
        if team_spread_close is not None:
            ats_margin = float(team_margin) + float(team_spread_close)
            if math.isclose(ats_margin, 0.0, abs_tol=1e-9):
                ats_result = "Push"
            elif ats_margin > 0:
                ats_result = "Cover"
            else:
                ats_result = "No cover"
        if total_close is not None:
            total_margin = float(int(team_points) + int(opp_points)) - float(total_close)
            if math.isclose(total_margin, 0.0, abs_tol=1e-9):
                total_result = "Push"
            elif total_margin > 0:
                total_result = "Over"
            else:
                total_result = "Under"

    return {
        "team_spread_close": team_spread_close,
        "expected_margin": expected_margin,
        "team_moneyline_close": team_moneyline,
        "implied_win_prob": implied_win_prob,
        "ats_margin": ats_margin,
        "ats_result": ats_result,
        "total_close": None if total_close is None else float(total_close),
        "total_margin": total_margin,
        "total_result": total_result,
    }


def _format_spread_text(team_spread: Any) -> str:
    if team_spread is None:
        return "--"
    value = float(team_spread)
    if math.isclose(value, 0.0, abs_tol=1e-9):
        return "PK"
    return f"{value:+.1f}"


def _format_moneyline_text(american_odds: Any) -> str:
    if american_odds in (None, ""):
        return "--"
    try:
        value = int(american_odds)
    except (TypeError, ValueError):
        return "--"
    return f"+{value}" if value > 0 else str(value)


def _format_total_text(total_value: Any) -> str:
    if total_value is None:
        return "--"
    return f"{float(total_value):.1f}"


def _cover_rate(summary: dict[str, Any]) -> float | None:
    decisions = int(summary.get("ats_wins") or 0) + int(summary.get("ats_losses") or 0)
    if decisions <= 0:
        return None
    return float(summary.get("ats_wins") or 0) / float(decisions)


def _total_rate(summary: dict[str, Any], direction: str) -> float | None:
    decisions = int(summary.get("overs") or 0) + int(summary.get("unders") or 0)
    if decisions <= 0:
        return None
    numerator = int(summary.get("overs") or 0) if direction == "over" else int(summary.get("unders") or 0)
    return numerator / float(decisions)


def _summarize_team_betting(team_id: int, schedule: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "games_with_lines": 0,
        "ats_wins": 0,
        "ats_losses": 0,
        "ats_pushes": 0,
        "overs": 0,
        "unders": 0,
        "total_pushes": 0,
        "favorite_games": 0,
        "favorite_ats_wins": 0,
        "favorite_ats_losses": 0,
        "favorite_ats_pushes": 0,
        "underdog_games": 0,
        "underdog_ats_wins": 0,
        "underdog_ats_losses": 0,
        "underdog_ats_pushes": 0,
        "actual_wins_lined": 0,
        "expected_wins": 0.0,
        "providers": set(),
        "best_cover": None,
        "worst_burn": None,
        "biggest_total_miss": None,
    }

    for row in schedule:
        context = _team_line_context(team_id, row)
        row.update(context)
        if row.get("line_provider"):
            summary["providers"].add(str(row["line_provider"]))

        has_line = (
            context["team_spread_close"] is not None
            or context["total_close"] is not None
            or context["team_moneyline_close"] is not None
        )
        if not has_line:
            continue
        summary["games_with_lines"] += 1

        is_completed = row.get("home_points") is not None and row.get("away_points") is not None
        if context["implied_win_prob"] is not None and is_completed:
            summary["expected_wins"] += float(context["implied_win_prob"])
        if is_completed:
            is_home = int(row["home_team_id"]) == team_id
            team_points = int(row["home_points"] if is_home else row["away_points"])
            opp_points = int(row["away_points"] if is_home else row["home_points"])
            if team_points > opp_points:
                summary["actual_wins_lined"] += 1

        if context["team_spread_close"] is not None:
            if float(context["team_spread_close"]) < 0:
                summary["favorite_games"] += 1
            elif float(context["team_spread_close"]) > 0:
                summary["underdog_games"] += 1

        ats_result = context["ats_result"]
        if ats_result == "Cover":
            summary["ats_wins"] += 1
            if context["team_spread_close"] is not None and float(context["team_spread_close"]) < 0:
                summary["favorite_ats_wins"] += 1
            elif context["team_spread_close"] is not None and float(context["team_spread_close"]) > 0:
                summary["underdog_ats_wins"] += 1
        elif ats_result == "No cover":
            summary["ats_losses"] += 1
            if context["team_spread_close"] is not None and float(context["team_spread_close"]) < 0:
                summary["favorite_ats_losses"] += 1
            elif context["team_spread_close"] is not None and float(context["team_spread_close"]) > 0:
                summary["underdog_ats_losses"] += 1
        elif ats_result == "Push":
            summary["ats_pushes"] += 1
            if context["team_spread_close"] is not None and float(context["team_spread_close"]) < 0:
                summary["favorite_ats_pushes"] += 1
            elif context["team_spread_close"] is not None and float(context["team_spread_close"]) > 0:
                summary["underdog_ats_pushes"] += 1

        total_result = context["total_result"]
        if total_result == "Over":
            summary["overs"] += 1
        elif total_result == "Under":
            summary["unders"] += 1
        elif total_result == "Push":
            summary["total_pushes"] += 1

        opponent_name = str(row["away_team_name"] if int(row["home_team_id"]) == team_id else row["home_team_name"])
        game_stub = {
            "week": int(row.get("week") or 0),
            "opponent_name": opponent_name,
            "opponent_slug": str(row["away_slug"] if int(row["home_team_id"]) == team_id else row["home_slug"]),
            "season_phase": row.get("season_phase"),
            "ats_margin": context["ats_margin"],
            "total_margin": context["total_margin"],
            "ats_result": context["ats_result"],
            "total_result": context["total_result"],
            "line_provider": row.get("line_provider"),
            "team_spread_close": context["team_spread_close"],
            "total_close": context["total_close"],
        }
        if context["ats_margin"] is not None:
            best_cover = summary.get("best_cover")
            worst_burn = summary.get("worst_burn")
            if best_cover is None or float(context["ats_margin"]) > float(best_cover.get("ats_margin") or -999.0):
                summary["best_cover"] = game_stub
            if worst_burn is None or float(context["ats_margin"]) < float(worst_burn.get("ats_margin") or 999.0):
                summary["worst_burn"] = game_stub
        if context["total_margin"] is not None:
            biggest_total_miss = summary.get("biggest_total_miss")
            if biggest_total_miss is None or abs(float(context["total_margin"])) > abs(float(biggest_total_miss.get("total_margin") or 0.0)):
                summary["biggest_total_miss"] = game_stub

    summary["cover_rate"] = _cover_rate(summary)
    summary["over_rate"] = _total_rate(summary, "over")
    summary["under_rate"] = _total_rate(summary, "under")
    summary["wins_above_market"] = float(summary["actual_wins_lined"]) - float(summary["expected_wins"])
    providers = sorted(summary["providers"])
    summary["provider_text"] = ", ".join(providers[:3]) if providers else "CFBD lines"
    summary["providers"] = providers
    return summary


def _attach_team_page_context(team_pages: list[dict[str, Any]]) -> None:
    if not team_pages:
        return

    ordered = list(team_pages)
    level_groups: dict[str, list[dict[str, Any]]] = {}
    conference_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for team_data in ordered:
        level_code = _team_display_level_code(team_data)
        conference_name = _team_display_conference_name(team_data)
        level_groups.setdefault(level_code, []).append(team_data)
        conference_groups.setdefault((level_code, conference_name), []).append(team_data)

    level_positions: dict[str, dict[str, Any]] = {}
    conference_positions: dict[str, dict[str, Any]] = {}

    for group in level_groups.values():
        total = len(group)
        for index, team_data in enumerate(group):
            slug = str(team_data["ranking"].slug)
            level_positions[slug] = {
                "rank": index + 1,
                "total": total,
                "ahead": _peer_reference(group[index - 1], team_data["ranking"]) if index > 0 else None,
                "behind": _peer_reference(group[index + 1], team_data["ranking"]) if index + 1 < total else None,
            }

    for group in conference_groups.values():
        total = len(group)
        for index, team_data in enumerate(group):
            slug = str(team_data["ranking"].slug)
            conference_positions[slug] = {
                "rank": index + 1,
                "total": total,
                "ahead": _peer_reference(group[index - 1], team_data["ranking"]) if index > 0 else None,
                "behind": _peer_reference(group[index + 1], team_data["ranking"]) if index + 1 < total else None,
            }

    for index, team_data in enumerate(ordered):
        ranking: RankingRow = team_data["ranking"]
        current_slug = str(ranking.slug)
        current_power = float(ranking.power_rating)
        current_resume = float(ranking.resume_score)
        current_level = _team_display_level_code(team_data)
        bridge_candidate = min(
            (
                candidate
                for candidate in ordered
                if candidate["ranking"].slug != current_slug and _team_display_level_code(candidate) != current_level
            ),
            key=lambda candidate: (
                abs(float(candidate["ranking"].power_rating) - current_power),
                abs(float(candidate["ranking"].resume_score) - current_resume),
                abs(int(candidate["ranking"].rank) - int(ranking.rank)),
            ),
            default=None,
        )
        team_data["peer_context"] = {
            "overall_ahead": _peer_reference(ordered[index - 1], ranking) if index > 0 else None,
            "overall_behind": _peer_reference(ordered[index + 1], ranking) if index + 1 < len(ordered) else None,
            "level": level_positions.get(current_slug, {"rank": 1, "total": 1, "ahead": None, "behind": None}),
            "conference": conference_positions.get(current_slug, {"rank": 1, "total": 1, "ahead": None, "behind": None}),
            "cross_level_peer": None if bridge_candidate is None else _peer_reference(bridge_candidate, ranking),
        }


def _peer_reference(team_data: dict[str, Any], current_ranking: RankingRow) -> dict[str, Any]:
    ranking: RankingRow = team_data["ranking"]
    level_code = _team_display_level_code(team_data)
    conference = _team_display_conference_name(team_data)
    return {
        "team_name": ranking.team_name,
        "slug": ranking.slug,
        "rank": ranking.rank,
        "level_code": level_code,
        "conference": conference,
        "power_gap": float(ranking.power_display or 0.0) - float(current_ranking.power_display or 0.0),
        "resume_gap": float(ranking.resume_display or 0.0) - float(current_ranking.resume_display or 0.0),
    }


def _team_display_level_code(team_data: dict[str, Any]) -> str:
    ranking: RankingRow = team_data["ranking"]
    team = team_data.get("team") or {}
    return str(team.get("level_code") or ranking.level_code)


def _team_display_conference_name(team_data: dict[str, Any]) -> str:
    level_code = _team_display_level_code(team_data)
    team = team_data.get("team") or {}
    return _clean_conference_name(str(team.get("conference_name") or f"{level_code} Independents"))


def _conference_slug(conference_name: str, level_code: str) -> str:
    raw = f"{level_code} {conference_name}".lower().strip()
    raw = raw.replace("&", " and ")
    raw = raw.replace("'", "")
    raw = raw.replace(".", "")
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-") or f"{level_code.lower()}-conference"


def _clean_conference_name(value: str) -> str:
    cleaned = value.strip()
    replacements = {
        "Great Midwestate Athletic": "Great Midwest Athletic",
        "Northeastate 10": "Northeast 10",
        "Independent Dii": "Independent DII",
        "Independent Diii": "Independent DIII",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    standalones = {
        "FBS": "FBS Independents",
        "FCS": "FCS Independents",
        "DII": "Independent DII",
        "DIII": "Independent DIII",
    }
    return standalones.get(cleaned, cleaned)


def _team_theme(slug: str | None) -> dict[str, str]:
    from cfb_rankings.visual_assets import resolve_team_brand
    brand = resolve_team_brand(slug)
    # Generic registry fallback is "#5A5954"; preserve the old editorial fallback
    # pair (#19423f / #b98343) for truly unknown slugs so conferences render
    # with the paper-tone accent they had in Phase 1.
    accent = brand.primary_color if brand.primary_color != "#5A5954" else "#19423f"
    accent_soft = brand.secondary_color or "#b98343"
    return {"accent": accent, "accent_soft": accent_soft}


def _team_mark(team_name: str, slug: str | None = None) -> str:
    if slug:
        from cfb_rankings.visual_assets import resolve_team_brand
        brand = resolve_team_brand(slug)
        if brand.abbreviation and brand.abbreviation != "TEAM":
            return brand.abbreviation
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", team_name) if part]
    if not parts:
        return "CFB"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def _conference_profile_note(
    conference_name: str,
    round_robin_power: float,
    upper_strength: float,
    average_power: float,
    average_resume: float,
    median_power: float,
    parity_gap: float,
    top_25_count: int,
    ordered_items: list[dict[str, Any]],
) -> str:
    top_team_name = ordered_items[0]["ranking"].team_name if ordered_items else conference_name
    if len(ordered_items) <= 2:
        return f"{conference_name} is a very small affiliation group this season, so its strength is shown with extra regression instead of being treated like a full league ecosystem."
    if top_25_count >= 4:
        return f"{conference_name} carries real selection-room weight with {top_25_count} teams inside the top 25 and {top_team_name} driving a legitimate national ceiling."
    if parity_gap <= 3.5 and round_robin_power >= median_power - 0.8:
        return f"{conference_name} reads like a weekly gauntlet. The middle of the league is strong enough that contenders do not get many breathers."
    if upper_strength - median_power >= 4.5 and parity_gap >= 5.5:
        return f"{conference_name} is more top-heavy than deep. {top_team_name} gives the league punch, but the middle tier falls away faster than the top leagues."
    if average_resume - average_power >= 0.45:
        return f"{conference_name} is outperforming its raw power profile. The league body of work is stronger than the market would expect."
    if average_power - average_resume >= 0.45:
        return f"{conference_name} looks stronger on team quality than on season resume, which makes it a dangerous future-facing league."
    if upper_strength >= round_robin_power + 1.8:
        return f"{conference_name} has real upper-tier density. The top of the board raises the conference ceiling without the rest of the league completely falling away."
    return f"{conference_name} reads like a balanced league right now, with {top_team_name} setting the pace and the rest of the board staying reasonably connected behind it."


def _matchup_team_snapshot(team_data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    ranking: RankingRow = team_data["ranking"]
    season_summary = team_data["season_summary"]
    rating_snapshot = team_data.get("rating_snapshot") or {}
    conference = _clean_conference_name(str(team_data["team"].get("conference_name") or f"{ranking.level_code} Independents"))
    return {
        "slug": ranking.slug,
        "team_name": ranking.team_name,
        "rank": ranking.rank,
        "level_code": ranking.level_code,
        "conference": conference,
        "record": f"{int(season_summary.get('wins') or 0)}-{int(season_summary.get('losses') or 0)}",
        "power_rating": float(ranking.power_rating),
        "resume_score": float(ranking.resume_score),
        "power_display": float(ranking.power_display or 0.0),
        "resume_display": float(ranking.resume_display or 0.0),
        "power_percentile": float(ranking.power_percentile or 0.0),
        "resume_percentile": float(ranking.resume_percentile or 0.0),
        "offense_rating": float(rating_snapshot.get("offense_rating") or 0.0),
        "defense_rating": float(rating_snapshot.get("defense_rating") or 0.0),
        "special_teams_rating": float(rating_snapshot.get("special_teams_rating") or 0.0),
        "tempo_rating": float(rating_snapshot.get("tempo_rating") or 0.0),
        "recent_form": _compact_recent_form(ranking.team_id, team_data["schedule"]),
        "best_result": _best_result_text(ranking.team_id, team_data["schedule"]),
        "worst_result": _worst_result_text(ranking.team_id, team_data["schedule"]),
        "team_url": f"{prefix}teams/{ranking.slug}.html",
    }


def _project_matchup(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    site_pulse: dict[str, Any],
    location: str = "neutral",
) -> dict[str, Any]:
    base_points = float(site_pulse.get("base_points") or 28.0)
    home_field_advantage = float(site_pulse.get("home_field_advantage") or 2.3)
    if location == "team-a-home":
        home_team = team_a
        away_team = team_b
        home_bonus = home_field_advantage
        team_a_is_home = True
    elif location == "team-b-home":
        home_team = team_b
        away_team = team_a
        home_bonus = home_field_advantage
        team_a_is_home = False
    else:
        home_team = team_a
        away_team = team_b
        home_bonus = 0.0
        team_a_is_home = True

    pace_adjustment = 0.5 * (float(team_a["tempo_rating"]) + float(team_b["tempo_rating"]))
    predicted_home_points = (
        base_points
        + float(home_team["offense_rating"])
        - float(away_team["defense_rating"])
        + 0.5 * (float(home_team["special_teams_rating"]) - float(away_team["special_teams_rating"]))
        + 0.5 * home_bonus
        + pace_adjustment
    )
    predicted_away_points = (
        base_points
        + float(away_team["offense_rating"])
        - float(home_team["defense_rating"])
        + 0.5 * (float(away_team["special_teams_rating"]) - float(home_team["special_teams_rating"]))
        - 0.5 * home_bonus
        + pace_adjustment
    )
    if team_a_is_home:
        team_a_points = predicted_home_points
        team_b_points = predicted_away_points
    else:
        team_a_points = predicted_away_points
        team_b_points = predicted_home_points
    spread_for_a = team_a_points - team_b_points
    win_probability_a = 0.5 * (1.0 + math.erf((spread_for_a / 14.5) / math.sqrt(2.0)))
    favorite = team_a if spread_for_a >= 0 else team_b
    favorite_spread = abs(spread_for_a)
    return {
        "team_a_points": team_a_points,
        "team_b_points": team_b_points,
        "spread_for_a": spread_for_a,
        "win_probability_a": win_probability_a,
        "predicted_total": team_a_points + team_b_points,
        "favorite_name": favorite["team_name"],
        "favorite_spread": favorite_spread,
        "resume_gap": float(team_a.get("resume_display") or 0.0) - float(team_b.get("resume_display") or 0.0),
        "power_gap": float(team_a.get("power_display") or 0.0) - float(team_b.get("power_display") or 0.0),
    }


def _default_matchup_pair(team_pages: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(team_pages) < 2:
        raise ValueError("Need at least two teams to build matchup data.")
    first = team_pages[0]
    for candidate in team_pages[1:12]:
        if _clean_conference_name(str(candidate["team"].get("conference_name") or "")) != _clean_conference_name(str(first["team"].get("conference_name") or "")):
            return first, candidate
    return team_pages[0], team_pages[1]


def _matchup_payload(team_pages: list[dict[str, Any]], site_pulse: dict[str, Any], prefix: str = "") -> str:
    if len(team_pages) < 2:
        return "{}"
    default_team_a, default_team_b = _default_matchup_pair(team_pages)
    payload = {
        "basePoints": round(float(site_pulse.get("base_points") or 28.0), 4),
        "homeFieldAdvantage": round(float(site_pulse.get("home_field_advantage") or 2.3), 4),
        "defaultTeamA": default_team_a["ranking"].slug,
        "defaultTeamB": default_team_b["ranking"].slug,
        "teams": [_matchup_team_snapshot(team_data, prefix=prefix) for team_data in team_pages],
    }
    return json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")


def _render_matchup_tool(
    team_pages: list[dict[str, Any]],
    site_pulse: dict[str, Any],
    prefix: str = "",
    compact: bool = False,
) -> str:
    if len(team_pages) < 2:
        return '<p class="footer-note">Matchup Studio unlocks after at least two teams have been rated.</p>'

    default_a_page, default_b_page = _default_matchup_pair(team_pages)
    default_a = _matchup_team_snapshot(default_a_page, prefix=prefix)
    default_b = _matchup_team_snapshot(default_b_page, prefix=prefix)
    projection = _project_matchup(default_a, default_b, site_pulse, location="neutral")
    options = "".join(
        f'<option value="{escape(team_data["ranking"].slug)}">{escape(team_data["ranking"].team_name)} ({escape(team_data["ranking"].level_code)})</option>'
        for team_data in team_pages
    )
    studio_class = "matchup-tool compact-matchup-tool" if compact else "matchup-tool"
    summary_text = (
        f"{projection['favorite_name']} would be favored by {projection['favorite_spread']:.1f} points on a neutral field. "
        f"The current projected score is {default_a['team_name']} {projection['team_a_points']:.1f}, {default_b['team_name']} {projection['team_b_points']:.1f}."
    )
    return f"""
    <div class="{studio_class}">
      <div class="matchup-controls">
        <label class="board-control">
          <span>Team A</span>
          <select id="matchupTeamA">{options}</select>
        </label>
        <label class="board-control">
          <span>Team B</span>
          <select id="matchupTeamB">{options}</select>
        </label>
        <label class="board-control">
          <span>Location</span>
          <select id="matchupLocation">
            <option value="neutral">Neutral field</option>
            <option value="team-a-home">Team A home</option>
            <option value="team-b-home">Team B home</option>
          </select>
        </label>
      </div>
      <div class="projection-shell">
        <div class="projection-band">
          <p class="panel-kicker">Current Projection</p>
          <h3 id="matchupHeadline">{escape(default_a['team_name'])} vs. {escape(default_b['team_name'])}</h3>
          <p class="projection-copy" id="matchupSummary">{escape(summary_text)}</p>
          <div class="projection-stat-grid">
            <div class="impact-stat">
              <span>Projected Spread</span>
              <strong id="matchupSpread">{escape(projection['favorite_name'])} -{projection['favorite_spread']:.1f}</strong>
            </div>
            <div class="impact-stat">
              <span>Win Probability</span>
              <strong id="matchupWinProb">{projection['win_probability_a'] * 100:.1f}% Team A</strong>
            </div>
            <div class="impact-stat">
              <span>Projected Total</span>
              <strong id="matchupTotal">{projection['predicted_total']:.1f}</strong>
            </div>
            <div class="impact-stat">
              <span>Resume Edge</span>
              <strong id="matchupResumeGap">{_signed_integer_text(projection['resume_gap'])}</strong>
            </div>
          </div>
        </div>
        <div class="matchup-team-grid">
          <article class="team-mini-card">
            <p class="panel-kicker">Team A</p>
            <h3><a id="teamALink" href="{escape(default_a['team_url'])}">{escape(default_a['team_name'])}</a></h3>
            <p class="team-mini-meta" id="teamAMeta">#{default_a['rank']} | {escape(default_a['level_code'])} | {escape(default_a['conference'])}</p>
            <div class="mini-team-stat-grid">
              <div class="impact-stat"><span>Record</span><strong id="teamARecord">{escape(default_a['record'])}</strong></div>
              <div class="impact-stat"><span>Power</span><strong id="teamAPower">{_public_power_text(default_a['power_display'])}</strong><span class="submetric">pts vs avg team</span></div>
              <div class="impact-stat"><span>Resume</span><strong id="teamAResume">{_public_resume_text(default_a['resume_display'])}</strong><span class="submetric">0-100 season score</span></div>
              <div class="impact-stat"><span>Recent Form</span><strong id="teamARecent">{escape(default_a['recent_form'])}</strong></div>
            </div>
            <p class="team-mini-note" id="teamABest">Best signal: {escape(default_a['best_result'])}</p>
            <p class="team-mini-note muted-note" id="teamAWorst">Stress point: {escape(default_a['worst_result'])}</p>
          </article>
          <article class="team-mini-card">
            <p class="panel-kicker">Team B</p>
            <h3><a id="teamBLink" href="{escape(default_b['team_url'])}">{escape(default_b['team_name'])}</a></h3>
            <p class="team-mini-meta" id="teamBMeta">#{default_b['rank']} | {escape(default_b['level_code'])} | {escape(default_b['conference'])}</p>
            <div class="mini-team-stat-grid">
              <div class="impact-stat"><span>Record</span><strong id="teamBRecord">{escape(default_b['record'])}</strong></div>
              <div class="impact-stat"><span>Power</span><strong id="teamBPower">{_public_power_text(default_b['power_display'])}</strong><span class="submetric">pts vs avg team</span></div>
              <div class="impact-stat"><span>Resume</span><strong id="teamBResume">{_public_resume_text(default_b['resume_display'])}</strong><span class="submetric">0-100 season score</span></div>
              <div class="impact-stat"><span>Recent Form</span><strong id="teamBRecent">{escape(default_b['recent_form'])}</strong></div>
            </div>
            <p class="team-mini-note" id="teamBBest">Best signal: {escape(default_b['best_result'])}</p>
            <p class="team-mini-note muted-note" id="teamBWorst">Stress point: {escape(default_b['worst_result'])}</p>
          </article>
        </div>
      </div>
    </div>
    """


def _render_site_pulse_cards(site_pulse: dict[str, Any]) -> str:
    archive_label = (
        f"{site_pulse['first_season']}-{site_pulse['last_season']}"
        if site_pulse.get("first_season") and site_pulse.get("last_season")
        else "Current local load"
    )
    cards = [
        (
            "Local Archive",
            f"{site_pulse['current_season_completed_games']:,} completed games",
            f"{site_pulse['tracked_teams']:,} teams across FBS, FCS, Division II, and Division III. {site_pulse['tracked_conferences']:,} conferences currently surfaced on the site.",
            archive_label,
        ),
        (
            "Published Run",
            f"Week {site_pulse['model_week']} board",
            f"CFB Index v1 was last cut at {site_pulse['data_cutoff_display']}.",
            "CFB Index publish",
        ),
        (
            "Projection Engine",
            f"{site_pulse['base_points']:.1f} base points / team",
            f"Matchup projections use current offense, defense, special teams, and tempo components with a {site_pulse['home_field_advantage']:.1f}-point home edge.",
            "Predictive layer",
        ),
        (
            "Data Stack",
            "CFBD primary, SportsDB enrichment",
            "CFBD powers games, advanced stats, drive and play detail, rosters, recruiting, and preseason signals. SportsDB stays in the stack for identity, artwork, and metadata enrichment.",
            "Source design",
        ),
    ]
    rendered = []
    for kicker, title, copy, tag in cards:
        rendered.append(
            f"""
            <article class="feature-card pulse-card">
              <span class="feature-rank">{escape(kicker)}</span>
              <h3>{escape(title)}</h3>
              <p>{escape(copy)}</p>
              <p class="story-tail">{escape(tag)}</p>
            </article>
            """
        )
    return "".join(rendered)


def _render_conference_spotlight(conference_pages: list[dict[str, Any]], prefix: str = "") -> str:
    cards = []
    for conference in conference_pages:
        top_team = conference["top_team"]["ranking"]
        best_resume_team = conference["best_resume_team"]["ranking"]
        cards.append(
            f"""
            <a class="conference-card" href="{escape(prefix)}{escape(conference['slug'])}.html">
              <span class="conference-level pill level-{escape(conference['level_code'])}">{escape(conference['level_code'])}</span>
              <h3>{escape(conference['conference_name'])}</h3>
              <p class="conference-note">{escape(conference['profile_note'])}</p>
              <div class="conference-stat-line">
                <span>RR50 <strong>{_public_power_text(conference.get('round_robin_power_display'))}</strong></span>
                <span>Upper Strength <strong>{_public_power_text(conference.get('upper_strength_display'))}</strong></span>
              </div>
              <div class="conference-stat-line">
                <span>Top Team <strong>{escape(top_team.team_name)}</strong></span>
                <span>Best Resume <strong>{escape(best_resume_team.team_name)}</strong></span>
              </div>
            </a>
            """
        )
    return "".join(cards)


def render_matchups_page_html(
    summary: dict[str, Any],
    team_pages: list[dict[str, Any]],
    site_pulse: dict[str, Any],
    fan_intel_board: dict[str, Any] | None = None,
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    matchup_tool = _render_matchup_tool(team_pages, site_pulse, prefix="../", compact=False)
    matchup_payload = _matchup_payload(team_pages, site_pulse, prefix="../")
    scenarios = _render_matchup_scenario_cards(team_pages, site_pulse)
    argument_theater = _render_matchup_argument_theater(fan_intel_board or {}, prefix="../teams/")
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} Matchups</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="matchups")}
      <section class="hero">
        <p class="eyebrow">Argument Theater</p>
        <h1>Model, market, mood &mdash; who actually wins the fight?</h1>
        <p class="lede">
          Matchup pages here aren't just a betting matrix. They are the place where the model, the market, and the two fanbases all line up side by side.
          Pick any two teams and start the argument.
        </p>
      </section>

      <section class="section">
        <article class="panel tool-panel">
          <div class="section-head">
            <div>
              <h2>Neutral-Field Matchup Studio</h2>
              <p class="section-note">The spread and score projection come from the latest power components, not from the resume side.</p>
            </div>
          </div>
          {_metric_guide_strip()}
          {matchup_tool}
        </article>
      </section>

      {argument_theater}

      <section class="section">
        <div class="section-head">
          <div>
            <h2>Quick-Load Scenarios</h2>
            <p class="section-note">Use these to jump straight into the kinds of debates fans actually care about.</p>
          </div>
        </div>
        <div class="feature-grid scenario-grid">
          {scenarios}
        </div>
      </section>

      <script id="matchupPayload" type="application/json">{matchup_payload}</script>
      <script>{_matchup_tool_script()}</script>
    </main>
  </body>
</html>
"""


def _compare_result_payload(team_id: int, schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in _preferred_schedule_rows(schedule):
        is_home = int(row["home_team_id"]) == team_id
        opponent_name = str(row["away_team_name"] if is_home else row["home_team_name"])
        opponent_slug = str(row["away_slug"] if is_home else row["home_slug"])
        team_points = row["home_points"] if is_home else row["away_points"]
        opp_points = row["away_points"] if is_home else row["home_points"]
        if team_points is None or opp_points is None:
            continue
        team_score = int(team_points)
        opp_score = int(opp_points)
        margin = team_score - opp_score
        result_prefix = "W" if margin > 0 else "L" if margin < 0 else "T"
        results.append(
            {
                "opponent_slug": opponent_slug,
                "opponent_name": opponent_name,
                "week": int(row.get("week") or 0),
                "phase": _phase_display_label(row.get("season_phase")),
                "location": "vs" if is_home else "@",
                "result": f"{result_prefix} {team_score}-{opp_score}",
                "margin": margin,
                "power_delta": None if row.get("power_delta") is None else float(row.get("power_delta") or 0.0),
                "resume_delta": None if row.get("resume_delta") is None else float(row.get("resume_delta") or 0.0),
            }
        )
    return results


def _compare_phase_payload(phase_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(phase_summary, key=lambda row: _phase_sort_key(row.get("season_phase")))
    return [
        {
            "phase": _phase_display_label(row.get("season_phase")),
            "wins": int(row.get("wins") or 0),
            "losses": int(row.get("losses") or 0),
            "games": int(row.get("games_played") or 0),
        }
        for row in ordered
    ]


def _compare_metric_payload(team_data: dict[str, Any]) -> dict[str, float]:
    ranking: RankingRow = team_data["ranking"]
    rating_snapshot = team_data.get("rating_snapshot") or {}
    efficiency_snapshot = team_data.get("efficiency_snapshot") or {}
    offensive_eff = efficiency_snapshot.get("Offensive Efficiency", {})
    defensive_eff = efficiency_snapshot.get("Defensive Efficiency", {})
    explosiveness = efficiency_snapshot.get("Explosiveness", {})
    finishing = efficiency_snapshot.get("Finishing Drives", {})
    return {
        "power": float(ranking.power_display or 0.0),
        "resume": float(ranking.resume_display or 0.0),
        "powerRaw": float(ranking.power_rating),
        "resumeRaw": float(ranking.resume_score),
        "powerPercentile": float(ranking.power_percentile or 0.0),
        "resumePercentile": float(ranking.resume_percentile or 0.0),
        "offense": float(rating_snapshot.get("offense_rating") or 0.0),
        "defense": float(rating_snapshot.get("defense_rating") or 0.0),
        "specialTeams": float(rating_snapshot.get("special_teams_rating") or 0.0),
        "tempo": float(rating_snapshot.get("tempo_rating") or 0.0),
        "recordStrength": float(rating_snapshot.get("record_strength_score") or 0.0),
        "performanceOverExpectation": float(rating_snapshot.get("performance_over_expectation_score") or 0.0),
        "resultQuality": float(rating_snapshot.get("result_quality_score") or 0.0),
        "bestWin": float(rating_snapshot.get("best_win_score") or 0.0),
        "scheduleStrength": float(rating_snapshot.get("schedule_strength_score") or 0.0),
        "offensiveEfficiencyPct": float(offensive_eff.get("offense_percentile") or 0.0) * 100.0,
        "defensiveEfficiencyPct": float(defensive_eff.get("defense_percentile") or 0.0) * 100.0,
        "explosivenessPct": max(
            float(explosiveness.get("offense_percentile") or 0.0),
            float(explosiveness.get("defense_percentile") or 0.0),
        )
        * 100.0,
        "finishingDrivesPct": max(
            float(finishing.get("offense_percentile") or 0.0),
            float(finishing.get("defense_percentile") or 0.0),
        )
        * 100.0,
    }


def _compare_team_snapshot(team_data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    ranking: RankingRow = team_data["ranking"]
    season_summary = team_data["season_summary"]
    points_for = int(season_summary.get("points_for") or 0)
    points_against = int(season_summary.get("points_against") or 0)
    games_played = max(1, int(season_summary.get("wins") or 0) + int(season_summary.get("losses") or 0))
    conference = _clean_conference_name(str(team_data["team"].get("conference_name") or f"{ranking.level_code} Independents"))
    return {
        "slug": ranking.slug,
        "team_name": ranking.team_name,
        "rank": ranking.rank,
        "rank_change": ranking.rank_change,
        "level_code": ranking.level_code,
        "conference": conference,
        "record": f"{int(season_summary.get('wins') or 0)}-{int(season_summary.get('losses') or 0)}",
        "recent_form": _compact_recent_form(ranking.team_id, team_data["schedule"]),
        "best_result": _best_result_text(ranking.team_id, team_data["schedule"]),
        "worst_result": _worst_result_text(ranking.team_id, team_data["schedule"]),
        "efficiency_note": _best_efficiency_signal(team_data.get("efficiency_snapshot") or {}),
        "team_url": f"{prefix}teams/{ranking.slug}.html",
        "points_for": points_for,
        "points_against": points_against,
        "average_margin": (points_for - points_against) / games_played,
        "power_display": float(ranking.power_display or 0.0),
        "resume_display": float(ranking.resume_display or 0.0),
        "power_percentile": float(ranking.power_percentile or 0.0),
        "resume_percentile": float(ranking.resume_percentile or 0.0),
        "phase_summary": _compare_phase_payload(team_data["phase_summary"]),
        "results": _compare_result_payload(ranking.team_id, team_data["schedule"]),
        "metrics": _compare_metric_payload(team_data),
    }


def _default_compare_pair(team_pages: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(team_pages) < 2:
        return team_pages[0], team_pages[0]
    top_power = team_pages[0]
    best_resume = max(team_pages[:30], key=lambda item: item["ranking"].resume_score)
    if top_power["ranking"].slug != best_resume["ranking"].slug:
        return top_power, best_resume
    return team_pages[0], team_pages[1]


def _build_compare_scenarios(team_pages: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any], dict[str, Any], str]]:
    scenarios: list[tuple[str, dict[str, Any], dict[str, Any], str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    if len(team_pages) < 2:
        return scenarios

    def add_scenario(label: str, team_a_page: dict[str, Any], team_b_page: dict[str, Any], blurb: str) -> None:
        slug_a = str(team_a_page["ranking"].slug)
        slug_b = str(team_b_page["ranking"].slug)
        if slug_a == slug_b:
            return
        pair = tuple(sorted((slug_a, slug_b)))
        if pair in seen_pairs:
            return
        seen_pairs.add(pair)
        scenarios.append((label, team_a_page, team_b_page, blurb))

    top_power, best_resume = _default_compare_pair(team_pages)
    add_scenario(
        "Best team vs. best resume",
        top_power,
        best_resume,
        "The most classic committee argument on the board.",
    )
    fbs = [item for item in team_pages if item["ranking"].level_code == "FBS"]
    fcs = [item for item in team_pages if item["ranking"].level_code == "FCS"]
    dii = [item for item in team_pages if item["ranking"].level_code == "DII"]
    if fbs and fcs:
        bridge_fbs = min(fbs[:50], key=lambda item: abs(item["ranking"].power_rating - fcs[0]["ranking"].power_rating))
        add_scenario(
            "Top FCS bridge test",
            bridge_fbs,
            fcs[0],
            "How the best FCS team stacks up against a quality FBS profile with a similar rating.",
        )
    if fcs and dii:
        bridge_fcs = min(fcs[:60], key=lambda item: abs(item["ranking"].power_rating - dii[0]["ranking"].power_rating))
        add_scenario(
            "Division bridge",
            bridge_fcs,
            dii[0],
            "A cleaner look at the gap between the top of Division II and the lower edge of strong FCS territory.",
        )
    if len(fbs) >= 2:
        close_pair = sorted(fbs[:25], key=lambda item: item["ranking"].power_rating)[:]
        if len(close_pair) >= 2:
            add_scenario(
                "Crowded playoff lane",
                close_pair[-1],
                close_pair[-2],
                "Two strong FBS profiles whose difference comes down to resume texture and unit edges.",
            )
    return scenarios[:4]


def _compare_href(prefix: str, team_a_slug: str, team_b_slug: str) -> str:
    return f"{prefix}compare/index.html?teamA={team_a_slug}&teamB={team_b_slug}"


def _compare_payload(team_pages: list[dict[str, Any]], prefix: str = "") -> str:
    default_a_page, default_b_page = _default_compare_pair(team_pages)
    payload = {
        "teams": [_compare_team_snapshot(team_data, prefix=prefix) for team_data in team_pages],
        "defaultTeamA": default_a_page["ranking"].slug,
        "defaultTeamB": default_b_page["ranking"].slug,
    }
    return json.dumps(payload, separators=(",", ":"))


def _render_compare_scenario_cards(team_pages: list[dict[str, Any]]) -> str:
    cards = []
    for label, team_a_page, team_b_page, blurb in _build_compare_scenarios(team_pages):
        cards.append(
            f"""
            <button type="button" class="feature-card scenario-card" data-team-a="{escape(team_a_page['ranking'].slug)}" data-team-b="{escape(team_b_page['ranking'].slug)}">
              <span class="feature-rank">{escape(label)}</span>
              <h3>{escape(team_a_page['ranking'].team_name)} vs. {escape(team_b_page['ranking'].team_name)}</h3>
              <p>{escape(blurb)}</p>
              <p class="story-tail">Open the comparison board</p>
            </button>
            """
        )
    return "".join(cards)


def _render_compare_feature_cards(team_pages: list[dict[str, Any]], prefix: str = "") -> str:
    cards = []
    for label, team_a_page, team_b_page, blurb in _build_compare_scenarios(team_pages):
        cards.append(
            f"""
            <a class="feature-card" href="{escape(_compare_href(prefix, team_a_page['ranking'].slug, team_b_page['ranking'].slug))}">
              <span class="feature-rank">{escape(label)}</span>
              <h3>{escape(team_a_page['ranking'].team_name)} vs. {escape(team_b_page['ranking'].team_name)}</h3>
              <p>{escape(blurb)}</p>
              <p class="story-tail">Open the comparison board</p>
            </a>
            """
        )
    return "".join(cards)


def _render_market_feature_cards(team_pages: list[dict[str, Any]], prefix: str = "teams/") -> str:
    candidates = [team_data for team_data in team_pages if (team_data.get("betting_summary") or {}).get("games_with_lines")]
    if not candidates:
        return '<p class="footer-note">Market cards will populate after more CFBD line data is loaded into the current season.</p>'

    cards: list[str] = []

    best_ats = max(
        (item for item in candidates if (item.get("betting_summary") or {}).get("cover_rate") is not None),
        key=lambda item: (
            float((item.get("betting_summary") or {}).get("cover_rate") or 0.0),
            int((item.get("betting_summary") or {}).get("games_with_lines") or 0),
        ),
        default=None,
    )
    if best_ats:
        betting = best_ats["betting_summary"]
        cards.append(
            f"""
            <a class="feature-card story-card" href="{prefix}{escape(best_ats['ranking'].slug)}.html">
              <span class="feature-rank">Best ATS</span>
              <h3>{escape(best_ats['ranking'].team_name)}</h3>
              <p>{int(betting.get('ats_wins') or 0)}-{int(betting.get('ats_losses') or 0)} ATS with {int(betting.get('ats_pushes') or 0)} pushes.</p>
              <p class="story-tail">Cover rate {escape(_probability_text(betting.get('cover_rate')))} across {int(betting.get('games_with_lines') or 0)} lined games.</p>
            </a>
            """
        )

    most_respected = max(
        candidates,
        key=lambda item: float((item.get("betting_summary") or {}).get("wins_above_market") or -999.0),
    )
    respected_betting = most_respected["betting_summary"]
    cards.append(
        f"""
        <a class="feature-card story-card" href="{prefix}{escape(most_respected['ranking'].slug)}.html">
          <span class="feature-rank">Beat The Market</span>
          <h3>{escape(most_respected['ranking'].team_name)}</h3>
          <p>{float(respected_betting.get('wins_above_market') or 0.0):+.2f} wins versus market expectation.</p>
          <p class="story-tail">Actual lined record {int(respected_betting.get('actual_wins_lined') or 0)} wins against {float(respected_betting.get('expected_wins') or 0.0):.2f} expected.</p>
        </a>
        """
    )

    best_under = max(
        (item for item in candidates if (item.get("betting_summary") or {}).get("under_rate") is not None),
        key=lambda item: (
            float((item.get("betting_summary") or {}).get("under_rate") or 0.0),
            int((item.get("betting_summary") or {}).get("unders") or 0),
        ),
        default=None,
    )
    if best_under:
        betting = best_under["betting_summary"]
        cards.append(
            f"""
            <a class="feature-card story-card" href="{prefix}{escape(best_under['ranking'].slug)}.html">
              <span class="feature-rank">Under Team</span>
              <h3>{escape(best_under['ranking'].team_name)}</h3>
              <p>{int(betting.get('unders') or 0)} unders and {int(betting.get('overs') or 0)} overs so far.</p>
              <p class="story-tail">Market total leaned under {escape(_probability_text(betting.get('under_rate')))} of decided totals.</p>
            </a>
            """
        )

    taken_slugs = {str(item["ranking"].slug) for item in [best_ats, most_respected, best_under] if item}
    toughest_fade = min(
        (
            item
            for item in candidates
            if (item.get("betting_summary") or {}).get("cover_rate") is not None
            and str(item["ranking"].slug) not in taken_slugs
        ),
        key=lambda item: (
            float((item.get("betting_summary") or {}).get("cover_rate") or 1.0),
            -int((item.get("betting_summary") or {}).get("games_with_lines") or 0),
        ),
        default=None,
    )
    if toughest_fade:
        betting = toughest_fade["betting_summary"]
        cards.append(
            f"""
            <a class="feature-card story-card" href="{prefix}{escape(toughest_fade['ranking'].slug)}.html">
              <span class="feature-rank">Toughest Fade</span>
              <h3>{escape(toughest_fade['ranking'].team_name)}</h3>
              <p>{int(betting.get('ats_wins') or 0)}-{int(betting.get('ats_losses') or 0)} ATS with too many missed covers for backers.</p>
              <p class="story-tail">Worst cover rate among the visible market profiles.</p>
            </a>
            """
        )

    return "".join(cards[:4])


def render_compare_page_html(summary: dict[str, Any], team_pages: list[dict[str, Any]], site_pulse: dict[str, Any]) -> str:
    season_name = season_label(int(summary["season_year"]))
    default_a_page, default_b_page = _default_compare_pair(team_pages)
    default_a = _compare_team_snapshot(default_a_page, prefix="../")
    default_b = _compare_team_snapshot(default_b_page, prefix="../")
    compare_payload = _compare_payload(team_pages, prefix="../")
    scenarios = _render_compare_scenario_cards(team_pages)
    team_options = "\n".join(
        f'<option value="{escape(team.slug)}">{escape(team.team_name)} ({escape(team.level_code)})</option>'
        for team in sorted((item["ranking"] for item in team_pages), key=lambda row: (row.team_name.lower(), row.level_code, row.rank))
    )
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} Compare Teams</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="compare")}
      <section class="hero">
        <p class="eyebrow">Compare Teams</p>
        <h1>Settle the argument without opening ten tabs.</h1>
        <p class="lede">
          Fans do not just want a ranking. They want to know who is stronger now, who has earned more, where the disagreement comes from,
          and how two teams stack up against the same sport around them. This page is built for that.
        </p>
        <div class="cta-row">
          <a class="button button-primary" href="../matchups/index.html">Open Matchup Studio</a>
          <a class="button button-secondary" href="../rankings/index.html">Back To Rankings</a>
        </div>
      </section>

      <section class="section">
        <article class="panel tool-panel">
          <div class="section-head">
            <div>
              <h2>Comparison Board</h2>
              <p class="section-note">Use any two teams from the current NCAA-eligible site universe. The matchup page projects a score; this page explains the argument.</p>
            </div>
          </div>
          {_metric_guide_strip()}
          <div class="compare-controls">
            <label class="board-control">
              <span>Team A</span>
              <select id="compareTeamA">{team_options}</select>
            </label>
            <label class="board-control">
              <span>Team B</span>
              <select id="compareTeamB">{team_options}</select>
            </label>
          </div>

          <div class="compare-headline">
            <div>
              <span class="feature-rank">Selection Room Verdict</span>
              <h3 id="compareHeadline">{escape(default_a['team_name'])} vs. {escape(default_b['team_name'])}</h3>
              <p class="section-note" id="compareSummary">The site will explain who looks stronger, who has the better resume, and where the disagreement actually lives.</p>
            </div>
            <a class="text-link" href="../matchups/index.html">Need a projected score instead?</a>
          </div>

          <div class="compare-team-grid">
            <article class="panel compare-team-card">
              <span class="feature-rank">Team A</span>
              <h3><a id="compareALink" href="{escape(default_a['team_url'])}">{escape(default_a['team_name'])}</a></h3>
              <p class="team-mini-meta" id="compareAMeta">#{default_a['rank']} | {escape(default_a['level_code'])} | {escape(default_a['conference'])}</p>
              <div class="stat-grid compare-stat-grid">
                <div class="stat-card"><span>Record</span><strong id="compareARecord">{escape(default_a['record'])}</strong></div>
                <div class="stat-card"><span>Power</span><strong id="compareAPower">{_public_power_text(default_a['metrics']['power'])}</strong><span class="submetric">pts vs avg team</span></div>
                <div class="stat-card"><span>Resume</span><strong id="compareAResume">{_public_resume_text(default_a['metrics']['resume'])}</strong><span class="submetric">0-100 season score</span></div>
                <div class="stat-card"><span>Avg Margin</span><strong id="compareAMargin">{default_a['average_margin']:+.1f}</strong></div>
              </div>
              <p class="team-mini-note" id="compareABest">Best signal: {escape(default_a['best_result'])}</p>
              <p class="team-mini-note muted-note" id="compareAWorst">Stress point: {escape(default_a['worst_result'])}</p>
              <p class="team-mini-note muted-note" id="compareAEfficiency">{escape(default_a['efficiency_note'])}</p>
            </article>

            <article class="panel compare-team-card">
              <span class="feature-rank">Team B</span>
              <h3><a id="compareBLink" href="{escape(default_b['team_url'])}">{escape(default_b['team_name'])}</a></h3>
              <p class="team-mini-meta" id="compareBMeta">#{default_b['rank']} | {escape(default_b['level_code'])} | {escape(default_b['conference'])}</p>
              <div class="stat-grid compare-stat-grid">
                <div class="stat-card"><span>Record</span><strong id="compareBRecord">{escape(default_b['record'])}</strong></div>
                <div class="stat-card"><span>Power</span><strong id="compareBPower">{_public_power_text(default_b['metrics']['power'])}</strong><span class="submetric">pts vs avg team</span></div>
                <div class="stat-card"><span>Resume</span><strong id="compareBResume">{_public_resume_text(default_b['metrics']['resume'])}</strong><span class="submetric">0-100 season score</span></div>
                <div class="stat-card"><span>Avg Margin</span><strong id="compareBMargin">{default_b['average_margin']:+.1f}</strong></div>
              </div>
              <p class="team-mini-note" id="compareBBest">Best signal: {escape(default_b['best_result'])}</p>
              <p class="team-mini-note muted-note" id="compareBWorst">Stress point: {escape(default_b['worst_result'])}</p>
              <p class="team-mini-note muted-note" id="compareBEfficiency">{escape(default_b['efficiency_note'])}</p>
            </article>
          </div>
        </article>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Why Team A or Team B</h2>
              <p class="section-note">The fast read, without pretending one metric answers everything.</p>
            </div>
          </div>
          <div class="stat-grid compare-verdict-grid" id="compareVerdicts"></div>
        </article>
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Season Phase Split</h2>
              <p class="section-note">How each team's season is distributed across the same year-defined cycle.</p>
            </div>
          </div>
          <div id="comparePhaseTable"></div>
        </article>
      </section>

      <section class="section" id="current-season-production">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Component Battle</h2>
              <p class="section-note">This is where the model disagreement becomes visible instead of hand-wavy.</p>
            </div>
          </div>
          <div class="compare-factor-grid" id="compareFactors"></div>
        </article>
      </section>

      <section class="section" id="current-season-production">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Shared Opponents</h2>
              <p class="section-note">When two teams have touched the same part of the schedule graph, fans want to see it immediately.</p>
            </div>
          </div>
          <div id="compareCommonOpponents"></div>
        </article>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>Quick-Load Arguments</h2>
            <p class="section-note">These presets are based on the same kinds of debates fans keep returning to.</p>
          </div>
        </div>
        <div class="feature-grid scenario-grid">
          {scenarios}
        </div>
      </section>

      <script id="comparePayload" type="application/json">{compare_payload}</script>
      <script>{_compare_tool_script()}</script>
    </main>
  </body>
</html>
"""


def _compare_tool_script() -> str:
    return """
      (() => {
        const payloadNode = document.getElementById('comparePayload');
        const teamASelect = document.getElementById('compareTeamA');
        const teamBSelect = document.getElementById('compareTeamB');
        if (!payloadNode || !teamASelect || !teamBSelect) return;

        const payload = JSON.parse(payloadNode.textContent || '{}');
        const teams = Array.isArray(payload.teams) ? payload.teams : [];
        const teamMap = new Map(teams.map((team) => [team.slug, team]));
        if (!teams.length) return;

        const params = new URLSearchParams(window.location.search);
        const requestedA = params.get('teamA');
        const requestedB = params.get('teamB');

        if (requestedA && teamMap.has(requestedA)) {
          teamASelect.value = requestedA;
        } else if (payload.defaultTeamA && teamMap.has(payload.defaultTeamA)) {
          teamASelect.value = payload.defaultTeamA;
        }

        if (requestedB && teamMap.has(requestedB)) {
          teamBSelect.value = requestedB;
        } else if (payload.defaultTeamB && teamMap.has(payload.defaultTeamB)) {
          teamBSelect.value = payload.defaultTeamB;
        }

        const factorSpecs = [
          ['Power', 'power'],
          ['Resume', 'resume'],
          ['Offense', 'offense'],
          ['Defense', 'defense'],
          ['Special Teams', 'specialTeams'],
          ['Tempo', 'tempo'],
          ['Record Strength', 'recordStrength'],
          ['Result Quality', 'resultQuality'],
          ['Best Win', 'bestWin'],
          ['Schedule Strength', 'scheduleStrength'],
          ['Off. Efficiency %', 'offensiveEfficiencyPct'],
          ['Def. Efficiency %', 'defensiveEfficiencyPct'],
          ['Explosiveness %', 'explosivenessPct'],
          ['Finishing Drives %', 'finishingDrivesPct'],
        ];

        function formatSigned(value, digits = 2) {
          const number = Number(value || 0);
          return `${number >= 0 ? '+' : ''}${number.toFixed(digits)}`;
        }

        function formatPower(value) {
          return formatSigned(value, 1);
        }

        function formatResume(value) {
          return `${Math.round(Number(value || 0))}`;
        }

        function formatMetricValue(metricKey, value) {
          if (metricKey === 'power') return formatPower(value);
          if (metricKey === 'resume') return formatResume(value);
          return Number(value || 0).toFixed(2);
        }

        function ensureDistinctTeams() {
          if (teamASelect.value !== teamBSelect.value) return;
          const fallback = teams.find((team) => team.slug !== teamASelect.value);
          if (fallback) teamBSelect.value = fallback.slug;
        }

        function verdictWinner(teamA, teamB, metricKey) {
          const a = Number(teamA.metrics?.[metricKey] || 0);
          const b = Number(teamB.metrics?.[metricKey] || 0);
          if (Math.abs(a - b) < 0.01) return 'Dead even';
          return a > b ? teamA.team_name : teamB.team_name;
        }

        function renderTeam(slot, team) {
          const map = {
            A: {
              link: 'compareALink',
              meta: 'compareAMeta',
              record: 'compareARecord',
              power: 'compareAPower',
              resume: 'compareAResume',
              margin: 'compareAMargin',
              best: 'compareABest',
              worst: 'compareAWorst',
              efficiency: 'compareAEfficiency',
            },
            B: {
              link: 'compareBLink',
              meta: 'compareBMeta',
              record: 'compareBRecord',
              power: 'compareBPower',
              resume: 'compareBResume',
              margin: 'compareBMargin',
              best: 'compareBBest',
              worst: 'compareBWorst',
              efficiency: 'compareBEfficiency',
            },
          }[slot];
          const link = document.getElementById(map.link);
          const meta = document.getElementById(map.meta);
          const record = document.getElementById(map.record);
          const power = document.getElementById(map.power);
          const resume = document.getElementById(map.resume);
          const margin = document.getElementById(map.margin);
          const best = document.getElementById(map.best);
          const worst = document.getElementById(map.worst);
          const efficiency = document.getElementById(map.efficiency);
          if (link) {
            link.textContent = team.team_name;
            link.setAttribute('href', team.team_url);
          }
          if (meta) meta.textContent = `#${team.rank} | ${team.level_code} | ${team.conference}`;
          if (record) record.textContent = team.record;
          if (power) power.textContent = formatPower(team.metrics?.power || 0);
          if (resume) resume.textContent = formatResume(team.metrics?.resume || 0);
          if (margin) margin.textContent = formatSigned(team.average_margin, 1);
          if (best) best.textContent = `Best signal: ${team.best_result || '--'}`;
          if (worst) worst.textContent = `Stress point: ${team.worst_result || '--'}`;
          if (efficiency) efficiency.textContent = team.efficiency_note || '--';
        }

        function renderHeadline(teamA, teamB) {
          const headline = document.getElementById('compareHeadline');
          const summary = document.getElementById('compareSummary');
          const stronger = verdictWinner(teamA, teamB, 'power');
          const betterResume = verdictWinner(teamA, teamB, 'resume');
          const moreExplosive = verdictWinner(teamA, teamB, 'explosivenessPct');
          if (headline) headline.textContent = `${teamA.team_name} vs. ${teamB.team_name}`;
          if (summary) {
            summary.textContent =
              `${stronger} looks stronger right now on the predictive board. ` +
              `${betterResume} owns the better body of work. ` +
              `${moreExplosive} currently carries the more volatile big-play profile.`;
          }
        }

        function renderVerdicts(teamA, teamB) {
          const node = document.getElementById('compareVerdicts');
          if (!node) return;
          const cards = [
            ['Stronger now', verdictWinner(teamA, teamB, 'power'), `${teamA.team_name} ${formatPower(teamA.metrics?.power || 0)} vs ${teamB.team_name} ${formatPower(teamB.metrics?.power || 0)}`],
            ['More deserving', verdictWinner(teamA, teamB, 'resume'), `${teamA.team_name} ${formatResume(teamA.metrics?.resume || 0)} vs ${teamB.team_name} ${formatResume(teamB.metrics?.resume || 0)}`],
            ['Better offense', verdictWinner(teamA, teamB, 'offense'), `${teamA.team_name} ${Number(teamA.metrics?.offense || 0).toFixed(2)} vs ${teamB.team_name} ${Number(teamB.metrics?.offense || 0).toFixed(2)}`],
            ['Better defense', verdictWinner(teamA, teamB, 'defense'), `${teamA.team_name} ${Number(teamA.metrics?.defense || 0).toFixed(2)} vs ${teamB.team_name} ${Number(teamB.metrics?.defense || 0).toFixed(2)}`],
          ];
          node.innerHTML = cards.map(([label, winner, detail]) => `
            <div class="stat-card">
              <span>${label}</span>
              <strong>${winner}</strong>
              <span class="submetric">${detail}</span>
            </div>
          `).join('');
        }

        function renderFactors(teamA, teamB) {
          const node = document.getElementById('compareFactors');
          if (!node) return;
          node.innerHTML = factorSpecs.map(([label, key]) => {
            const a = Number(teamA.metrics?.[key] || 0);
            const b = Number(teamB.metrics?.[key] || 0);
            const max = Math.max(Math.abs(a), Math.abs(b), 1);
            const aWidth = Math.max(10, (Math.abs(a) / max) * 100);
            const bWidth = Math.max(10, (Math.abs(b) / max) * 100);
            const winner = a === b ? 'Dead even' : a > b ? teamA.team_name : teamB.team_name;
            return `
              <article class="compare-factor-card">
                <div class="compare-factor-top">
                  <span class="feature-rank">${label}</span>
                  <strong>${winner}</strong>
                </div>
                <div class="compare-factor-bars">
                  <div class="compare-bar-row">
                    <span class="compare-bar-team">${teamA.team_name}</span>
                    <div class="compare-bar-track"><span class="compare-bar compare-bar-a" style="width:${aWidth}%"></span></div>
                    <span class="compare-bar-value">${formatMetricValue(key, a)}</span>
                  </div>
                  <div class="compare-bar-row">
                    <span class="compare-bar-team">${teamB.team_name}</span>
                    <div class="compare-bar-track"><span class="compare-bar compare-bar-b" style="width:${bWidth}%"></span></div>
                    <span class="compare-bar-value">${formatMetricValue(key, b)}</span>
                  </div>
                </div>
              </article>
            `;
          }).join('');
        }

        function renderPhases(teamA, teamB) {
          const node = document.getElementById('comparePhaseTable');
          if (!node) return;
          const phaseMapA = new Map((teamA.phase_summary || []).map((row) => [row.phase, row]));
          const phaseMapB = new Map((teamB.phase_summary || []).map((row) => [row.phase, row]));
          const phases = Array.from(new Set([...(teamA.phase_summary || []).map((row) => row.phase), ...(teamB.phase_summary || []).map((row) => row.phase)]));
          if (!phases.length) {
            node.innerHTML = '<p class="section-note">Phase splits will populate as the season structure fills out.</p>';
            return;
          }
          node.innerHTML = `
            <div class="table-wrap compact-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Phase</th>
                    <th>${teamA.team_name}</th>
                    <th>${teamB.team_name}</th>
                  </tr>
                </thead>
                <tbody>
                  ${phases.map((phase) => {
                    const a = phaseMapA.get(phase) || { wins: 0, losses: 0, games: 0 };
                    const b = phaseMapB.get(phase) || { wins: 0, losses: 0, games: 0 };
                    return `<tr>
                      <td>${phase}</td>
                      <td>${a.wins}-${a.losses}<span class="submetric">${a.games} games</span></td>
                      <td>${b.wins}-${b.losses}<span class="submetric">${b.games} games</span></td>
                    </tr>`;
                  }).join('')}
                </tbody>
              </table>
            </div>
          `;
        }

        function renderCommonOpponents(teamA, teamB) {
          const node = document.getElementById('compareCommonOpponents');
          if (!node) return;
          const mapA = new Map((teamA.results || []).map((row) => [row.opponent_slug, row]));
          const shared = (teamB.results || [])
            .filter((row) => mapA.has(row.opponent_slug))
            .map((row) => ({ opponent: row.opponent_name, a: mapA.get(row.opponent_slug), b: row }))
            .sort((left, right) => left.opponent.localeCompare(right.opponent));
          if (!shared.length) {
            node.innerHTML = '<p class="section-note">These teams have not crossed the same opponent path in the current loaded season.</p>';
            return;
          }
          node.innerHTML = `
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Opponent</th>
                    <th>${teamA.team_name}</th>
                    <th>${teamB.team_name}</th>
                  </tr>
                </thead>
                <tbody>
                  ${shared.map((row) => `
                    <tr>
                      <td>${row.opponent}<span class="submetric">${row.a.phase}</span></td>
                      <td>${row.a.location} ${row.a.result}<span class="submetric">Power ${row.a.power_delta === null ? '--' : formatSigned(row.a.power_delta)}</span></td>
                      <td>${row.b.location} ${row.b.result}<span class="submetric">Power ${row.b.power_delta === null ? '--' : formatSigned(row.b.power_delta)}</span></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `;
        }

        function render() {
          ensureDistinctTeams();
          const teamA = teamMap.get(teamASelect.value) || teamMap.get(payload.defaultTeamA) || teams[0];
          const teamB = teamMap.get(teamBSelect.value) || teamMap.get(payload.defaultTeamB) || teams[1];
          renderTeam('A', teamA);
          renderTeam('B', teamB);
          renderHeadline(teamA, teamB);
          renderVerdicts(teamA, teamB);
          renderFactors(teamA, teamB);
          renderPhases(teamA, teamB);
          renderCommonOpponents(teamA, teamB);
        }

        [teamASelect, teamBSelect].forEach((node) => {
          node.addEventListener('change', render);
          node.addEventListener('input', render);
        });

        document.querySelectorAll('.scenario-card').forEach((button) => {
          button.addEventListener('click', () => {
            if (button.dataset.teamA) teamASelect.value = button.dataset.teamA;
            if (button.dataset.teamB) teamBSelect.value = button.dataset.teamB;
            render();
            const panel = document.querySelector('.tool-panel');
            if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
          });
        });

        render();
      })();
    """


def render_conferences_index_html(
    summary: dict[str, Any],
    conference_pages: list[dict[str, Any]],
    site_pulse: dict[str, Any],
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    top_cards = _render_conference_spotlight([conference for conference in conference_pages if int(conference["team_count"]) >= 4][:12], prefix="")
    table_rows = "\n".join(_render_conference_table_row(conference) for conference in conference_pages)
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} Conferences</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="conferences")}
      <section class="hero">
        <p class="eyebrow">Conferences</p>
        <h1>The sport gets more interesting when leagues have identity.</h1>
        <p class="lede">
          Conference pages turn the board from a list of teams into a map of ecosystems: top-end strength, week-to-week density, and who actually drives each league.
          The current local load covers {site_pulse['tracked_conferences']} active conferences.
        </p>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>Conference Spotlight</h2>
            <p class="section-note">The main sort is now round-robin strength: the neutral-field rating a hypothetical team would need to go .500 through that league.</p>
          </div>
        </div>
        <div class="conference-card-grid">
          {top_cards}
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>All Conferences</h2>
            <p class="section-note">Sorted by KenPom-style `RR50` strength first, then by middle-class power and upper-tier quality. Very small affiliations are lightly regressed toward their subdivision baseline so one-team groups do not break the board.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Conference</th>
                <th>Level</th>
                <th>Teams</th>
                <th>RR50</th>
                <th>Upper Strength</th>
                <th>Median Power</th>
                <th>Resume Pulse</th>
                <th>Top Team</th>
              </tr>
            </thead>
            <tbody>
              {table_rows}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </body>
</html>
"""


def _render_conference_movers_section(conference: dict[str, Any]) -> str:
    teams = conference.get("teams") or []
    def _delta(item: dict[str, Any]) -> int:
        return int(getattr(item.get("ranking"), "rank_change", 0) or 0)
    risers = sorted((t for t in teams if _delta(t) > 0), key=_delta, reverse=True)[:3]
    faders = sorted((t for t in teams if _delta(t) < 0), key=_delta)[:3]

    def _card(item: dict[str, Any], direction: str) -> str:
        ranking = item["ranking"]
        delta = _delta(item)
        sign = "+" if delta > 0 else ""
        arrow = "&#9650;" if direction == "up" else "&#9660;"
        return (
            f'<a class="feature-card scenario-card" href="../teams/{escape(ranking.slug)}.html">'
            f'<span class="feature-rank">{arrow} {sign}{delta}</span>'
            f'<h3>{escape(ranking.team_name)}</h3>'
            f'<p>Now #{ranking.rank} &middot; Power {_public_power_text(ranking.power_display)}</p>'
            f'<p class="story-tail">Resume {_public_resume_text(ranking.resume_display)} / 100</p>'
            f'</a>'
        )

    risers_html = "".join(_card(t, "up") for t in risers) or '<p class="footer-note">No meaningful risers this week.</p>'
    faders_html = "".join(_card(t, "down") for t in faders) or '<p class="footer-note">No meaningful faders this week.</p>'
    return f"""
      <section class="section two-up">
        <article class="panel">
          <div class="section-head"><h2>Biggest Risers</h2><p class="section-note">Week-over-week rank change inside the board.</p></div>
          <div class="feature-grid scenario-grid">{risers_html}</div>
        </article>
        <article class="panel">
          <div class="section-head"><h2>Biggest Faders</h2><p class="section-note">Teams whose stock dropped most against the board this week.</p></div>
          <div class="feature-grid scenario-grid">{faders_html}</div>
        </article>
      </section>
    """


def _render_conference_market_section(conference: dict[str, Any]) -> str:
    teams = conference.get("teams") or []
    scored = [
        t for t in teams
        if (t.get("betting_summary") or {}).get("games_with_lines")
    ]
    if not scored:
        return ""

    def _wins_above(item: dict[str, Any]) -> float:
        return float((item.get("betting_summary") or {}).get("wins_above_market") or 0.0)

    def _cover(item: dict[str, Any]) -> float:
        return float((item.get("betting_summary") or {}).get("cover_rate") or 0.0)

    top_cover = sorted(scored, key=_cover, reverse=True)[:5]
    top_wins = sorted(scored, key=_wins_above, reverse=True)[:5]

    def _row(item: dict[str, Any], metric: str) -> str:
        ranking = item["ranking"]
        bs = item.get("betting_summary") or {}
        if metric == "cover":
            cell = _probability_text(bs.get("cover_rate"))
            trailer = f"{int(bs.get('ats_wins') or 0)}-{int(bs.get('ats_losses') or 0)} ATS"
        else:
            cell = f"{_wins_above(item):+.2f}"
            trailer = f"{int(bs.get('games_with_lines') or 0)} lined games"
        return (
            f'<tr>'
            f'<td><a class="team-link" href="../teams/{escape(ranking.slug)}.html">{escape(ranking.team_name)}</a></td>'
            f'<td class="metric-cell">{escape(cell)}</td>'
            f'<td><span class="submetric">{escape(trailer)}</span></td>'
            f'</tr>'
        )

    cover_rows = "".join(_row(t, "cover") for t in top_cover)
    wins_rows = "".join(_row(t, "wins") for t in top_wins)
    return f"""
      <section class="section two-up">
        <article class="panel">
          <div class="section-head"><h2>ATS Leaders</h2><p class="section-note">Who beat the number most often this season.</p></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Team</th><th>Cover Rate</th><th>Record</th></tr></thead>
              <tbody>{cover_rows}</tbody>
            </table>
          </div>
        </article>
        <article class="panel">
          <div class="section-head"><h2>Wins vs Market</h2><p class="section-note">Win total minus the market's implied expectation, by team.</p></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Team</th><th>Wins vs Market</th><th>Sample</th></tr></thead>
              <tbody>{wins_rows}</tbody>
            </table>
          </div>
        </article>
      </section>
    """


def _render_conference_parity_section(conference: dict[str, Any]) -> str:
    teams = conference.get("teams") or []
    if not teams:
        return ""
    ranks = [int(t["ranking"].rank) for t in teams if t.get("ranking") and t["ranking"].rank]
    if not ranks:
        return ""
    top_rank = min(ranks)
    bottom_rank = max(ranks)
    top_name = next(t["ranking"].team_name for t in teams if int(t["ranking"].rank) == top_rank)
    bottom_name = next(t["ranking"].team_name for t in teams if int(t["ranking"].rank) == bottom_rank)
    parity_gap = float(conference.get("parity_gap") or 0.0)
    power_sd = float(conference.get("power_sd") or 0.0)
    top_25 = int(conference.get("top_25_count") or 0)
    top_100 = int(conference.get("top_100_count") or 0)
    if power_sd >= 6.0:
        parity_narrative = "Spread out — the league has a clear elite tier and a clear bottom."
    elif power_sd >= 3.0:
        parity_narrative = "Moderately layered — the league has real tiers but no runaway gap between them."
    else:
        parity_narrative = "Bunched — the power gap between the top and bottom of the league is unusually small."
    return f"""
      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Depth &amp; Parity</h2>
              <p class="section-note">How wide the league's power spread runs from top to bottom.</p>
            </div>
          </div>
          <div class="stat-grid">
            <div class="stat-card"><span>Top Rank</span><strong>#{top_rank} {escape(top_name)}</strong></div>
            <div class="stat-card"><span>Bottom Rank</span><strong>#{bottom_rank} {escape(bottom_name)}</strong></div>
            <div class="stat-card"><span>Top-to-Middle Gap</span><strong>{parity_gap:.1f}</strong></div>
            <div class="stat-card"><span>Power Spread</span><strong>{power_sd:.1f}</strong></div>
            <div class="stat-card"><span>Top 25 Teams</span><strong>{top_25}</strong></div>
            <div class="stat-card"><span>Top 100 Teams</span><strong>{top_100}</strong></div>
          </div>
          <p class="footer-note">{escape(parity_narrative)} Power Spread is the standard deviation of neutral-field power across league members.</p>
        </article>
      </section>
    """


def render_conference_page_html(summary: dict[str, Any], conference: dict[str, Any]) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    top_team = conference["top_team"]
    best_resume_team = conference["best_resume_team"]
    best_ats_team = conference.get("best_ats_team")
    market_surprise_team = conference.get("market_surprise_team")
    team_rows = "\n".join(_render_conference_team_row(team_data, conference) for team_data in conference["teams"])
    is_fbs = str(conference.get("level_code") or "").upper() == "FBS"
    extra_sections = ""
    if is_fbs:
        extra_sections = (
            _render_conference_movers_section(conference)
            + _render_conference_market_section(conference)
            + _render_conference_parity_section(conference)
        )
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(conference['conference_name'])} | {escape(season_name)}</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="conferences")}
      <section class="hero">
        <p class="eyebrow">{escape(conference['level_code'])} Conference</p>
        <h1>{escape(conference['conference_name'])}</h1>
        <p class="lede">{escape(conference['profile_note'])}</p>
        <div class="chip-row season-chip-row">
          <span class="mini-chip">#{int(conference['overall_rank'])} overall</span>
          <span class="mini-chip">#{int(conference['level_rank'])} in {escape(conference['level_code'])}</span>
          <span class="mini-chip">RR50 {_public_power_text(conference.get('round_robin_power_display'))}</span>
          <span class="mini-chip">Upper strength {_public_power_text(conference.get('upper_strength_display'))}</span>
          <span class="mini-chip">{conference['team_count']} teams</span>
          <span class="mini-chip">Top 25 teams {conference['top_25_count']}</span>
        </div>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <h2>Conference Snapshot</h2>
          </div>
          <div class="stat-grid">
            <div class="stat-card"><span>RR50</span><strong>{_public_power_text(conference.get('round_robin_power_display'))}</strong></div>
            <div class="stat-card"><span>Upper Strength</span><strong>{_public_power_text(conference.get('upper_strength_display'))}</strong></div>
            <div class="stat-card"><span>Median Power</span><strong>{_public_power_text(conference.get('median_power_display'))}</strong></div>
            <div class="stat-card"><span>Resume Pulse</span><strong>{_public_resume_text(conference.get('average_resume_display'), decimals=1)}</strong></div>
            <div class="stat-card"><span>Avg ATS</span><strong>{escape(_probability_text(conference.get('average_cover_rate')))}</strong></div>
            <div class="stat-card"><span>Wins vs Market</span><strong>{float(conference.get('average_wins_above_market') or 0.0):+.2f}</strong></div>
            <div class="stat-card"><span>Top-to-Middle Gap</span><strong>{conference['parity_gap']:.1f}</strong></div>
            <div class="stat-card"><span>Combined Record</span><strong>{conference['wins']}-{conference['losses']}</strong></div>
          </div>
          <p class="footer-note">`RR50`, `Upper Strength`, and `Median Power` are shown on the same public power scale as the rest of the site: points on a neutral field versus the average all-level NCAA team. Very small affiliations are gently regressed toward their subdivision baseline so a one-team outlier does not hijack the entire conference board.</p>
        </article>
        <article class="panel">
          <div class="section-head">
            <h2>League Drivers</h2>
          </div>
          <div class="conference-driver-list">
            <a class="conference-driver" href="../teams/{escape(top_team['ranking'].slug)}.html">
              <span class="feature-rank">Power leader</span>
              <strong>{escape(top_team['ranking'].team_name)}</strong>
              <span class="submetric">#{top_team['ranking'].rank} overall | {_public_power_text(top_team['ranking'].power_display)} pts vs avg</span>
            </a>
            <a class="conference-driver" href="../teams/{escape(best_resume_team['ranking'].slug)}.html">
              <span class="feature-rank">Resume leader</span>
              <strong>{escape(best_resume_team['ranking'].team_name)}</strong>
              <span class="submetric">#{best_resume_team['ranking'].rank} overall | {_public_resume_text(best_resume_team['ranking'].resume_display)} / 100 resume</span>
            </a>
            {f'''
            <a class="conference-driver" href="../teams/{escape(best_ats_team["ranking"].slug)}.html">
              <span class="feature-rank">ATS leader</span>
              <strong>{escape(best_ats_team["ranking"].team_name)}</strong>
              <span class="submetric">{escape(_probability_text((best_ats_team.get("betting_summary") or {}).get("cover_rate")))} cover rate</span>
            </a>
            ''' if best_ats_team else ''}
            {f'''
            <a class="conference-driver" href="../teams/{escape(market_surprise_team["ranking"].slug)}.html">
              <span class="feature-rank">Beat expectation</span>
              <strong>{escape(market_surprise_team["ranking"].team_name)}</strong>
              <span class="submetric">{float((market_surprise_team.get("betting_summary") or {}).get("wins_above_market") or 0.0):+.2f} wins vs market</span>
            </a>
            ''' if market_surprise_team else ''}
          </div>
        </article>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>{escape(conference['conference_name'])} Team Board</h2>
            <p class="section-note">The league stack, sorted by predictive strength. Power is shown as neutral-field points versus the all-level average team, while resume is shown on a 0-100 season score.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>Record</th>
                <th>Power</th>
                <th>Resume</th>
                <th>ATS</th>
                <th>Wins vs Market</th>
                <th>Recent Form</th>
              </tr>
            </thead>
            <tbody>
              {team_rows}
            </tbody>
          </table>
        </div>
      </section>
      {extra_sections}
    </main>
  </body>
</html>
"""


def _render_conference_table_row(conference: dict[str, Any]) -> str:
    top_team = conference["top_team"]["ranking"]
    return f"""
    <tr>
      <td><a class="team-link" href="{escape(conference['slug'])}.html">{escape(conference['conference_name'])}</a></td>
      <td><span class="pill level-{escape(conference['level_code'])}">{escape(conference['level_code'])}</span></td>
      <td class="metric-cell">{conference['team_count']}</td>
      <td class="metric-cell">{conference['round_robin_power']:.2f}</td>
      <td class="metric-cell">{conference['upper_strength']:.2f}</td>
      <td class="metric-cell">{conference['median_power']:.2f}</td>
      <td class="metric-cell">{_public_resume_text(conference.get('average_resume_display'), decimals=1)}</td>
      <td><a class="text-link" href="../teams/{escape(top_team.slug)}.html">{escape(top_team.team_name)}</a></td>
    </tr>
    """


def _render_conference_team_row(team_data: dict[str, Any], conference: dict[str, Any]) -> str:
    ranking: RankingRow = team_data["ranking"]
    season_summary = team_data["season_summary"]
    betting_summary = team_data.get("betting_summary") or {}
    ats_text = (
        f"{int(betting_summary.get('ats_wins') or 0)}-{int(betting_summary.get('ats_losses') or 0)}"
        if betting_summary.get("games_with_lines")
        else "--"
    )
    wins_vs_market = betting_summary.get("wins_above_market")
    return f"""
    <tr>
      <td class="rank-cell">#{ranking.rank}</td>
      <td><a class="team-link" href="../teams/{escape(ranking.slug)}.html">{escape(ranking.team_name)}</a></td>
      <td class="metric-cell">{int(season_summary.get('wins') or 0)}-{int(season_summary.get('losses') or 0)}</td>
      <td class="metric-cell">{_public_power_text(ranking.power_display)}</td>
      <td class="metric-cell">{_public_resume_text(ranking.resume_display)}</td>
      <td class="metric-cell">{escape(ats_text)}</td>
      <td class="metric-cell">{escape('--' if wins_vs_market is None else f'{float(wins_vs_market):+.2f}')}</td>
      <td>{escape(_compact_recent_form(ranking.team_id, team_data['schedule']))}</td>
    </tr>
    """


def _snapshot_leaders(rankings: list[RankingRow]) -> tuple[RankingRow | None, RankingRow | None, RankingRow | None]:
    if not rankings:
        return None, None, None
    window = rankings[:40]
    top_power = window[0]
    top_resume = max(window, key=lambda row: row.resume_score)
    biggest_riser = max(window, key=lambda row: row.rank_change)
    return top_power, top_resume, biggest_riser


def _archive_week_label(week: int | None) -> str:
    if week is None:
        return "Final"
    week_int = int(week)
    if week_int <= 0:
        return "Preseason"
    if week_int <= 17:
        return f"Week {week_int}"
    return "Final"


def _archive_snapshot_blurb(snapshot_season: int, current_season: int) -> str:
    if snapshot_season == current_season:
        return (
            "This page freezes the board exactly at this model checkpoint, so postseason games that "
            "spill into the next calendar year still remain attached to the season they decide."
        )
    return (
        f"This is the model's snapshot of the {snapshot_season} season. Records, rankings, and movement "
        "reflect the state of the board at this checkpoint only."
    )


def _program_link_or_text(prefix: str, slug: str | None, body: str, css_class: str = "team-link") -> str:
    slug_str = str(slug or "").strip()
    if not slug_str:
        return body
    return f'<a class="{css_class}" href="{prefix}{escape(slug_str)}.html">{body}</a>'


def _render_archive_snapshot_card(snapshot: dict[str, Any], rankings: list[RankingRow], prefix: str = "") -> str:
    top_power, top_resume, biggest_riser = _snapshot_leaders(rankings)
    top_label = top_power.team_name if top_power is not None else "Awaiting model run"
    mover_label = (
        f"{biggest_riser.team_name} {_rank_change_text(biggest_riser.rank_change)}"
        if biggest_riser is not None and biggest_riser.rank_change
        else "No prior snapshot loaded"
    )
    return f"""
    <a class="feature-card archive-card" href="{prefix}{escape(snapshot['slug'])}.html">
      <span class="feature-rank">{escape(snapshot['season_name'])}</span>
      <h3>{escape(_archive_week_label(snapshot.get('week')))}</h3>
      <p>#1 power: {escape(top_label)} ({_public_power_text(None if top_power is None else top_power.power_display)})</p>
      <p>Best resume: {escape(top_resume.team_name if top_resume is not None else '--')} ({_public_resume_text(None if top_resume is None else top_resume.resume_display)})</p>
      <p class="story-tail">Mover: {escape(mover_label)}</p>
    </a>
    """


def render_archive_index_html(
    summary: dict[str, Any],
    archive_snapshots: list[dict[str, Any]],
    archive_rankings: dict[str, list[RankingRow]],
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    by_season: dict[int, list[dict[str, Any]]] = {}
    for snapshot in archive_snapshots:
        by_season.setdefault(int(snapshot["season_year"]), []).append(snapshot)
    sections = []
    for season_year in sorted(by_season.keys(), reverse=True):
        cards = "".join(
            _render_archive_snapshot_card(snapshot, archive_rankings.get(str(snapshot["slug"]), []), prefix="")
            for snapshot in by_season[season_year]
        )
        sections.append(
            f"""
            <section class="section">
              <div class="section-head">
                <div>
                  <h2>{escape(season_label(season_year))}</h2>
                  <p class="section-note">Each snapshot preserves the board as it looked after that published model checkpoint.</p>
                </div>
              </div>
              <div class="feature-grid archive-card-grid">
                {cards}
              </div>
            </section>
            """
        )
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} Archive</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="archive")}
      <section class="hero">
        <p class="eyebrow">Weekly Archive</p>
        <h1>Replay the board the way fans actually remember a season.</h1>
        <p class="lede">
          The archive keeps each football season attached to the year it began, even when championship and bowl results land in the next calendar year.
          Each week page preserves the power board, resume board, and movement that followed the next major checkpoint.
        </p>
      </section>
      {''.join(sections)}
    </main>
  </body>
</html>
"""


def _render_archive_movers(rankings: list[RankingRow], direction: str, prefix: str = "../teams/") -> str:
    if direction == "up":
        candidates = sorted((row for row in rankings if row.rank_change > 0), key=lambda row: (-row.rank_change, row.rank))[:8]
        heading = "Biggest Risers"
        empty = "No earlier snapshot is loaded yet, so there are no week-over-week risers to show."
    else:
        candidates = sorted((row for row in rankings if row.rank_change < 0), key=lambda row: (row.rank_change, row.rank))[:8]
        heading = "Biggest Drops"
        empty = "No meaningful drops yet."
    if not candidates:
        return f"""
        <article class="panel">
          <div class="section-head"><h2>{heading}</h2></div>
          <p class="section-note">{empty}</p>
        </article>
        """
    rows = []
    for row in candidates:
        conference = _clean_conference_name(str(row.conference_name or f"{row.level_code} Independents"))
        slug_str = str(row.slug or "").strip()
        inner = (
            f'<span class="rank-delta {_rank_change_class(row.rank_change)}">{escape(_rank_change_text(row.rank_change))}</span>'
            f'<span><strong>{escape(row.team_name)}</strong>'
            f'<span class="submetric">#{row.rank} | {escape(row.level_code)} | {escape(conference)}</span>'
            f'</span>'
        )
        if slug_str and (not _VALID_TEAM_SLUGS or slug_str in _VALID_TEAM_SLUGS):
            rows.append(f'<a class="mover-item" href="{prefix}{escape(slug_str)}.html">{inner}</a>')
        else:
            rows.append(f'<div class="mover-item is-unlinked">{inner}</div>')
    return f"""
    <article class="panel">
      <div class="section-head"><h2>{heading}</h2></div>
      <div class="mover-list">
        {''.join(rows)}
      </div>
    </article>
    """


def _render_archive_rankings_row(row: RankingRow) -> str:
    conference = _clean_conference_name(str(row.conference_name or f"{row.level_code} Independents"))
    return f"""
    <tr>
      <td class="rank-cell">#{row.rank}</td>
      <td class="metric-cell"><span class="rank-delta {_rank_change_class(row.rank_change)}">{escape(_rank_change_text(row.rank_change))}</span></td>
      <td>{_team_link("../teams/", row.slug, row.team_name)}<span class="submetric">{escape(conference)}</span></td>
      <td><span class="pill level-{escape(row.level_code)}">{escape(row.level_code)}</span></td>
      <td class="metric-cell">{_public_power_text(row.power_display)}</td>
      <td class="metric-cell">{_public_resume_text(row.resume_display)}</td>
    </tr>
    """


def render_archive_snapshot_html(
    snapshot: dict[str, Any],
    rankings: list[RankingRow],
    newer_snapshot: dict[str, Any] | None,
    older_snapshot: dict[str, Any] | None,
    current_season_year: int | None = None,
) -> str:
    season_name = str(snapshot["season_name"])
    week_label = _archive_week_label(snapshot.get("week"))
    snapshot_season = int(snapshot.get("season_year") or 0)
    blurb = _archive_snapshot_blurb(snapshot_season, int(current_season_year or snapshot_season))
    table_rows = "\n".join(_render_archive_rankings_row(row) for row in rankings[:100])
    top_power, top_resume, biggest_riser = _snapshot_leaders(rankings)
    nav_links = []
    if newer_snapshot is not None:
        nav_links.append(f'<a class="button button-secondary" href="{escape(newer_snapshot["slug"])}.html">Newer Snapshot</a>')
    if older_snapshot is not None:
        nav_links.append(f'<a class="button button-secondary" href="{escape(older_snapshot["slug"])}.html">Older Snapshot</a>')
    mover_text = (
        f'{biggest_riser.team_name} {_rank_change_text(biggest_riser.rank_change)}'
        if biggest_riser is not None and biggest_riser.rank_change
        else "No prior snapshot loaded"
    )
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} {escape(week_label)}</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="archive")}
      <section class="hero">
        <p class="eyebrow">Weekly Snapshot</p>
        <h1>{escape(season_name)} | {escape(week_label)}</h1>
        <p class="lede">
          {escape(blurb)}
        </p>
        <div class="cta-row">
          <a class="button button-primary" href="index.html">Archive Home</a>
          {''.join(nav_links)}
        </div>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head"><h2>Snapshot Leaders</h2></div>
          <div class="stat-grid">
            <div class="stat-card"><span>#1 Power</span><strong>{escape(top_power.team_name if top_power is not None else '--')}</strong></div>
            <div class="stat-card"><span>Best Resume</span><strong>{escape(top_resume.team_name if top_resume is not None else '--')}</strong></div>
            <div class="stat-card"><span>Biggest Riser</span><strong>{escape(mover_text)}</strong></div>
            <div class="stat-card"><span>Teams Ranked</span><strong>{len(rankings)}</strong></div>
          </div>
        </article>
        <article class="panel prose-panel">
          <h2>Why this page matters</h2>
          <p>Fans don’t experience a season as one static final table. They live it week to week, with arguments changing after rivalry games, championship week, and playoff rounds.</p>
          <p>Keeping these snapshots visible makes the site more useful for debates, content, and historical storytelling than a single “latest” board ever could.</p>
        </article>
      </section>

      {"" if not any(row.rank_change for row in rankings) else f'''<section class="section two-up">
        {_render_archive_movers(rankings, "up")}
        {_render_archive_movers(rankings, "down")}
      </section>'''}

      <section class="section">
        <div class="section-head">
          <div>
            <h2>Top 100 Board</h2>
            <p class="section-note">{"This is the only loaded snapshot for this season, so there is no earlier board to diff against." if not any(row.rank_change for row in rankings) else "Week-over-week change is measured against the previous published snapshot in the same season."}</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Change</th>
                <th>Team</th>
                <th>Level</th>
                <th>Power</th>
                <th>Resume</th>
              </tr>
            </thead>
            <tbody>
              {table_rows}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </body>
</html>
"""


def _render_matchup_scenario_cards(team_pages: list[dict[str, Any]], site_pulse: dict[str, Any]) -> str:
    scenarios = _build_matchup_scenarios(team_pages)
    cards = []
    for label, team_a_page, team_b_page, blurb in scenarios:
        team_a = _matchup_team_snapshot(team_a_page)
        team_b = _matchup_team_snapshot(team_b_page)
        projection = _project_matchup(team_a, team_b, site_pulse, location="neutral")
        cards.append(
            f"""
            <button type="button" class="feature-card scenario-card" data-team-a="{escape(team_a['slug'])}" data-team-b="{escape(team_b['slug'])}" data-location="neutral">
              <span class="feature-rank">{escape(label)}</span>
              <h3>{escape(team_a['team_name'])} vs. {escape(team_b['team_name'])}</h3>
              <p>{escape(blurb)}</p>
              <p class="story-tail">{escape(projection['favorite_name'])} -{projection['favorite_spread']:.1f} on a neutral field</p>
            </button>
            """
        )
    return "".join(cards)


def _metric_guide_strip() -> str:
    return """
    <div class="metric-guide-strip" role="note" aria-label="How to read power and resume">
      <article class="metric-guide-pill">
        <span>Power</span>
        <strong>Predictive strength</strong>
        <p>Shown as points versus the average all-level NCAA team.</p>
      </article>
      <article class="metric-guide-pill">
        <span>Resume</span>
        <strong>Season body of work</strong>
        <p>Shown as a 0-100 score based on what the team has actually earned.</p>
      </article>
    </div>
    """


def _build_matchup_scenarios(team_pages: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any], dict[str, Any], str]]:
    top_overall = team_pages[:30]
    top_fbs = [team for team in team_pages if team["ranking"].level_code == "FBS"]
    top_fcs = [team for team in team_pages if team["ranking"].level_code == "FCS"]
    top_dii = [team for team in team_pages if team["ranking"].level_code == "DII"]
    top_diii = [team for team in team_pages if team["ranking"].level_code == "DIII"]
    scenarios: list[tuple[str, dict[str, Any], dict[str, Any], str]] = []

    if len(top_overall) >= 2:
        team_a, team_b = _default_matchup_pair(top_overall)
        scenarios.append(("Championship collision", team_a, team_b, "The cleanest high-end matchup on the board right now."))

    if top_overall:
        power_leader = top_overall[0]
        resume_leader = max(top_overall[:12], key=lambda item: item["ranking"].resume_score)
        if power_leader["ranking"].slug != resume_leader["ranking"].slug:
            scenarios.append(
                (
                    "Power vs. resume",
                    power_leader,
                    resume_leader,
                    "The classic argument: who looks strongest right now versus who has earned the season's best body of work.",
                )
            )

    if top_fcs and top_fbs:
        candidate_fbs = min(top_fbs[:40], key=lambda item: abs(item["ranking"].power_rating - top_fcs[0]["ranking"].power_rating))
        scenarios.append(
            (
                "Cross-level proving ground",
                candidate_fbs,
                top_fcs[0],
                "A test of how the best FCS profile stacks up against a strong FBS opponent with a comparable power number.",
            )
        )

    if top_dii and top_fcs:
        candidate_fcs = min(top_fcs[:50], key=lambda item: abs(item["ranking"].power_rating - top_dii[0]["ranking"].power_rating))
        scenarios.append(
            (
                "Division bridge",
                candidate_fcs,
                top_dii[0],
                "This is the kind of game that tells you how connected the lower-half of the map really is.",
            )
        )

    if top_diii and top_dii:
        candidate_dii = min(top_dii[:40], key=lambda item: abs(item["ranking"].power_rating - top_diii[0]["ranking"].power_rating))
        scenarios.append(
            (
                "Lower-division benchmark",
                candidate_dii,
                top_diii[0],
                "A benchmark matchup for the best DIII team against a DII peer in the same rough power neighborhood.",
            )
        )

    unique: list[tuple[str, dict[str, Any], dict[str, Any], str]] = []
    seen: set[tuple[str, str]] = set()
    for scenario in scenarios:
        key = tuple(sorted((scenario[1]["ranking"].slug, scenario[2]["ranking"].slug)))
        if key in seen:
            continue
        seen.add(key)
        unique.append(scenario)
    return unique[:4]


def render_rankings_html(
    summary: dict[str, Any],
    rankings: list[RankingRow],
    featured_team_pages: list[dict[str, Any]] | None = None,
) -> str:
    latest_local_week = int(summary["week"])
    return render_rankings_page_html(summary, rankings, latest_local_week, featured_team_pages)


def render_legacy_entry_html(summary: dict[str, Any], rankings: list[RankingRow]) -> str:
    season_name = season_label(int(summary["season_year"]))
    top_row = rankings[0]
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=site/rankings/index.html">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} Rankings Redirect</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: linear-gradient(180deg, #faf6ee 0%, #f4efe5 100%);
        color: #111;
        font-family: Georgia, "Times New Roman", serif;
      }}
      .card {{
        width: min(680px, calc(100vw - 28px));
        padding: 28px;
        border-radius: 28px;
        border: 1px solid rgba(17,17,17,0.10);
        background: rgba(255,255,255,0.82);
        box-shadow: 0 22px 60px rgba(0,0,0,0.08);
      }}
      h1 {{ margin: 0 0 12px; font-size: clamp(34px, 6vw, 56px); line-height: 0.96; }}
      p {{ margin: 0 0 14px; color: #625b52; font: 400 18px/1.7 Arial, sans-serif; }}
      a {{
        display: inline-block;
        margin-top: 10px;
        padding: 14px 18px;
        border-radius: 999px;
        background: #111;
        color: white;
        text-decoration: none;
        font: 700 13px/1 Arial, sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.10em;
      }}
    </style>
  </head>
  <body>
    <article class="card">
      <h1>The real site is ready.</h1>
      <p>The old single-file rankings output now points to the new static site experience. Latest published run: {escape(season_name)} through week {escape(str(summary["week"]))}.</p>
      <p>Current top team: #{top_row.rank} {escape(top_row.team_name)}.</p>
      <a href="site/rankings/index.html">Open rankings</a>
    </article>
  </body>
</html>
"""


def _format_calendar_date(value: datetime) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def _meta_tags(description: str, title: str = "", image_path: str = "og-image.svg") -> str:
    safe_desc = escape(description)
    safe_title = escape(title) if title else ""
    safe_image = escape(image_path)
    og_title_line = f'<meta property="og:title" content="{safe_title}">' if safe_title else ""
    twitter_title_line = f'<meta name="twitter:title" content="{safe_title}">' if safe_title else ""
    return (
        f'<meta name="description" content="{safe_desc}">'
        f'<meta property="og:site_name" content="THE CFB INDEX">'
        f'<meta property="og:type" content="website">'
        f'{og_title_line}'
        f'<meta property="og:description" content="{safe_desc}">'
        f'<meta property="og:image" content="{safe_image}">'
        f'<meta property="og:image:width" content="1200">'
        f'<meta property="og:image:height" content="630">'
        f'<meta name="twitter:card" content="summary_large_image">'
        f'{twitter_title_line}'
        f'<meta name="twitter:description" content="{safe_desc}">'
        f'<meta name="twitter:image" content="{safe_image}">'
    )


def _render_og_image_svg(
    *,
    eyebrow: str,
    headline: str,
    subline: str = "",
    accent: str = "#DC2626",
    slug: str | None = None,
    site_root: Path | None = None,
) -> str:
    safe_eyebrow = escape(eyebrow)
    safe_headline = escape(headline)
    safe_subline = escape(subline)
    logo_data_url = _og_logo_data_url(slug, site_root) if slug else None
    if logo_data_url is not None:
        headline_x = "192"
        logo_block = f'<image href="{logo_data_url}" x="72" y="180" width="96" height="96" preserveAspectRatio="xMidYMid meet"/>'
    else:
        headline_x = "72"
        logo_block = ""
    subline_block = (
        f'<text x="{headline_x}" y="498" fill="#A3A3A3" font-family="Inter, system-ui, sans-serif" font-size="28" font-weight="500">{safe_subline}</text>'
        if safe_subline else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">'
        '<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#0A0A0A"/>'
        '<stop offset="1" stop-color="#262626"/>'
        '</linearGradient>'
        '</defs>'
        '<rect width="1200" height="630" fill="url(#bg)"/>'
        f'<rect x="72" y="72" width="8" height="64" fill="{escape(accent)}"/>'
        f'<text x="100" y="120" fill="{escape(accent)}" font-family="Inter, system-ui, sans-serif" font-size="28" font-weight="700" letter-spacing="6">{safe_eyebrow.upper()}</text>'
        f'{logo_block}'
        f'<text x="{headline_x}" y="300" fill="#FFFFFF" font-family="Bebas Neue, Anton, Inter, sans-serif" font-size="96" font-weight="700" letter-spacing="-1">{safe_headline[:36]}</text>'
        f'<text x="{headline_x}" y="400" fill="#FFFFFF" font-family="Bebas Neue, Anton, Inter, sans-serif" font-size="72" font-weight="700" letter-spacing="-1">{safe_headline[36:72] if len(safe_headline) > 36 else ""}</text>'
        f'{subline_block}'
        '<text x="72" y="570" fill="#E5E5E5" font-family="Inter, system-ui, sans-serif" font-size="22" font-weight="700" letter-spacing="8">THE CFB INDEX</text>'
        '</svg>'
    )


def _home_editorial_context(now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now()
    phases = [
        {
            "month": 4,
            "label": "April",
            "theme": "Post-Spring Emotional Reset",
            "summary": "Treat spring like a belief reset: who came out steadier, who came out shakier, and which fanbases already sound divided.",
            "modules": [
                "Spring Exit Survey",
                "Who Gained Belief After Spring",
                "QB Panic Meter",
                "Hope Inventory",
            ],
            "hero_title": "What fanbases are talking themselves into after spring.",
            "hero_lede": "April should read like a post-spring reset, not fake portal chaos: quarterback nerves, new hope, and which programs left spring practice sounding steadier or shakier than before.",
            "board_note": "Read this board like a post-spring belief check: who gained belief, who got more nervous, and where fanbases are already splitting internally.",
            "panic_label": "Spring Panic Meter",
        },
        {
            "month": 5,
            "label": "May",
            "theme": "Identity Formation",
            "summary": "This is when fanbases start deciding what kind of team they think they are before the national conversation fully hardens.",
            "modules": [
                "Respect Gap Census",
                "Most Fragile Contenders",
                "Fanbase Civil War Watch",
                "Programs Outsiders Keep Getting Wrong",
            ],
            "hero_title": "Which fanbases know who they are, and which ones are still bluffing.",
            "hero_lede": "May is identity-formation season. The best content now is about respect gaps, fragile contenders, fanbase fracture, and which programs outsiders still misunderstand.",
            "board_note": "In May, the board should read like an identity census: how fans see themselves, how outsiders see them, and where those versions still do not match.",
            "panic_label": "Panic Meter",
        },
        {
            "month": 6,
            "label": "June",
            "theme": "Summer Discourse Drift",
            "summary": "June is for storyline gravity, recruiting euphoria and paranoia, and the little narratives fans repeat all month until they sound like truth.",
            "modules": [
                "Storyline Gravity",
                "Summer Vibe Stalls",
                "Recruiting Euphoria / Paranoia",
                "Rival Heat Map",
            ],
            "hero_title": "The month when summer narratives start hardening into pseudo-facts.",
            "hero_lede": "June should feel like discourse drift season: the stories fans keep repeating, the recruiting weekends they over-interpret, and the rival heat that keeps simmering without games.",
            "board_note": "In June, mood tracking matters most when it explains which narratives are sticking, which teams have stalled, and which rivalries are quietly heating up.",
            "panic_label": "Panic Meter",
        },
        {
            "month": 7,
            "label": "July",
            "theme": "Media Days And Conference Mood Season",
            "summary": "July is the biggest offseason tentpole: quote energy, conference optimism, awards buzz, and who is selling hope better than the evidence.",
            "modules": [
                "Media Days Reality Check",
                "Conference Respect Gap Boards",
                "Quote Energy vs Fan Mood",
                "Who Is Selling Hope Best",
            ],
            "hero_title": "The month when every conference starts selling a version of reality.",
            "hero_lede": "July is the tentpole month. Media days, awards buzz, conference optimism, and preseason quote season all make fan-intelligence products sharper, funnier, and more arguable.",
            "board_note": "In July, use the board to separate quote energy from real belief, conference confidence from conference delusion, and national fascination from actual substance.",
            "panic_label": "Panic Meter",
        },
        {
            "month": 8,
            "label": "August",
            "theme": "Certainty Theater Meets Real Uncertainty",
            "summary": "By August, everybody talks like they know the truth. The best content is about where that confidence is real, fake, fragile, or already cracking.",
            "modules": [
                "Delusion Meter",
                "Camp Panic Meter",
                "AP Poll vs Fan Pulse",
                "Week 0 Vibe Board",
            ],
            "hero_title": "The last honest mood check before the sport starts proving people wrong.",
            "hero_lede": "August should feel like certainty theater meeting real uncertainty: camp panic, depth-chart volatility, preseason truth detection, and the final optimism rush before kickoff.",
            "board_note": "In August, the board should feel like a preseason truth detector: who sounds grounded, who sounds terrified, and who is sprinting onto the hype train too early.",
            "panic_label": "Camp Panic Meter",
        },
    ]
    active_phase = next((phase for phase in phases if phase["month"] == current.month), None)

    if not active_phase:
        return {
            "is_offseason": False,
            "today_label": _format_calendar_date(current),
            "hero_eyebrow": "Fan Intelligence / Power / Resume",
            "hero_title": "How college football is actually feeling this week.",
            "hero_lede": "A single football universe for FBS through Division III, paired with a proprietary fan-intelligence layer that reads the belief, respect, and rivalry heat around every team. Built for argument, not dashboards.",
        }

    return {
        "is_offseason": True,
        "today_label": _format_calendar_date(current),
        "hero_eyebrow": "Offseason Fan Intelligence / Power / Resume",
        "hero_title": active_phase["hero_title"],
        "hero_lede": active_phase["hero_lede"],
        "phases": phases,
        "active_phase": active_phase,
    }


def _render_home_meta_row(summary: dict[str, Any], latest_local_week: int, editorial_context: dict[str, Any]) -> str:
    season_name = season_label(int(summary["season_year"]))
    if editorial_context.get("is_offseason"):
        active_phase = editorial_context.get("active_phase") or {}
        return f"""
        <div class="home-meta-row premium-meta-row">
          <div class="meta-pill"><span>Today</span><strong>{escape(str(editorial_context.get("today_label") or ""))}</strong></div>
          <div class="meta-pill"><span>Window</span><strong>{escape(str(active_phase.get("label") or ""))}: {escape(str(active_phase.get("theme") or ""))}</strong></div>
          <div class="meta-pill"><span>Latest Model</span><strong>{escape(season_name)} wk {escape(str(summary["week"]))}</strong></div>
          <div class="meta-pill"><span>Games Loaded</span><strong>Through wk {latest_local_week}</strong></div>
          <div class="meta-pill"><span>Methodology</span><strong><a href="about-model/index.html" style="color:inherit;border-bottom:1px dotted currentColor;">How we build this</a> &middot; <a href="methodology/fan-intelligence.html" style="color:inherit;border-bottom:1px dotted currentColor;">Fan Intel</a></strong></div>
          <div class="meta-pill"><span>Players</span><strong><a href="players/spotlight.html" style="color:inherit;border-bottom:1px dotted currentColor;">Spotlight</a> &middot; <a href="players/signature-stories.html" style="color:inherit;border-bottom:1px dotted currentColor;">Signature Stories</a> &middot; <a href="players/the-room.html" style="color:inherit;border-bottom:1px dotted currentColor;">The Room</a></strong></div>
        </div>
        """
    return f"""
    <div class="home-meta-row premium-meta-row">
      <div class="meta-pill"><span>Season</span><strong>{escape(season_name)}</strong></div>
      <div class="meta-pill"><span>Model Week</span><strong>{escape(str(summary["week"]))}</strong></div>
      <div class="meta-pill"><span>Games Loaded</span><strong>Through wk {latest_local_week}</strong></div>
      <div class="meta-pill"><span>Methodology</span><strong><a href="about-model/index.html" style="color:inherit;border-bottom:1px dotted currentColor;">How we build this</a> &middot; <a href="methodology/fan-intelligence.html" style="color:inherit;border-bottom:1px dotted currentColor;">Fan Intel</a></strong></div>
      <div class="meta-pill"><span>Players</span><strong><a href="players/spotlight.html" style="color:inherit;border-bottom:1px dotted currentColor;">Spotlight</a> &middot; <a href="players/signature-stories.html" style="color:inherit;border-bottom:1px dotted currentColor;">Signature Stories</a> &middot; <a href="players/the-room.html" style="color:inherit;border-bottom:1px dotted currentColor;">The Room</a></strong></div>
    </div>
    """


def _render_offseason_radar_section(editorial_context: dict[str, Any]) -> str:
    if not editorial_context.get("is_offseason"):
        return ""

    active_phase = editorial_context.get("active_phase") or {}
    phases = editorial_context.get("phases") or []
    cards: list[str] = []
    active_month = int(active_phase.get("month") or 0)
    for phase in phases:
        module_items = "".join(f"<li>{escape(str(module))}</li>" for module in phase.get("modules") or [])
        is_active = int(phase.get("month") or 0) == active_month
        status_chip = '<span class="offseason-card-status">Now</span>' if is_active else ""
        cards.append(
            f"""
            <article class="panel offseason-card{' offseason-card-current' if is_active else ''}">
              <div class="offseason-card-head">
                <span class="offseason-card-month">{escape(str(phase.get('label') or ''))}</span>
                {status_chip}
              </div>
              <h3>{escape(str(phase.get('theme') or ''))}</h3>
              <p>{escape(str(phase.get('summary') or ''))}</p>
              <ul class="offseason-module-list">
                {module_items}
              </ul>
            </article>
            """
        )

    return f"""
    <section class="section offseason-radar">
      <div class="section-head">
        <div>
          <p class="eyebrow">Road To Kickoff</p>
          <h2>April Through August, On Purpose</h2>
          <p class="section-note">
            As of {escape(str(editorial_context.get("today_label") or ""))}, the site should change its voice with the offseason calendar.
            Each month gets its own fan-intelligence frame instead of recycling generic preview-season sludge.
          </p>
        </div>
      </div>
      <article class="panel offseason-now-card">
        <div class="offseason-now-copy">
          <span class="offseason-now-kicker">Right Now</span>
          <h3>{escape(str(active_phase.get('label') or ''))}: {escape(str(active_phase.get('theme') or ''))}</h3>
          <p>{escape(str(active_phase.get('summary') or ''))}</p>
        </div>
        <div class="offseason-now-note">
          <strong>Current lens</strong>
          <span>{escape(str(active_phase.get('hero_lede') or ''))}</span>
        </div>
      </article>
      <div class="feature-grid offseason-grid">
        {"".join(cards)}
      </div>
    </section>
    """


def render_home_html(
    summary: dict[str, Any],
    rankings: list[RankingRow],
    featured_team_pages: list[dict[str, Any]],
    latest_local_week: int,
    site_pulse: dict[str, Any],
    history_hub: dict[str, Any],
    conference_pages: list[dict[str, Any]],
    archive_snapshots: list[dict[str, Any]],
    archive_rankings: dict[str, list[RankingRow]],
    fan_intel_board: dict[str, Any] | None = None,
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    editorial_context = _home_editorial_context()
    summary_cards = _render_summary_cards(featured_team_pages)
    board = _render_home_team_board(featured_team_pages)
    power_resume_plot = _render_power_resume_plot(featured_team_pages, prefix="")
    level_ladder = _render_strength_ladder(rankings)
    conference_spotlight = _render_conference_spotlight([conference for conference in conference_pages if int(conference["team_count"]) >= 4][:6], prefix="conferences/")
    matchup_studio = _render_matchup_tool(featured_team_pages, site_pulse, prefix="", compact=True)
    compare_cards = _render_compare_feature_cards(featured_team_pages, prefix="")
    market_cards = _render_market_feature_cards(featured_team_pages, prefix="teams/")
    history_cards = _render_history_feature_cards(history_hub, prefix="programs/")
    history_level_cards = _render_history_level_cards(history_hub, prefix="programs/")
    site_pulse_cards = _render_site_pulse_cards(site_pulse)
    archive_cards = "".join(
        _render_archive_snapshot_card(snapshot, archive_rankings.get(str(snapshot["slug"]), []), prefix="archive/")
        for snapshot in archive_snapshots
    )
    matchup_payload = _matchup_payload(featured_team_pages, site_pulse, prefix="")
    offseason_section = _render_offseason_radar_section(editorial_context)
    fan_intel_section = _render_fan_intel_home_section(
        fan_intel_board or {},
        prefix="teams/",
        editorial_context=editorial_context,
    )
    hero_meta_row = _render_home_meta_row(summary, latest_local_week, editorial_context)

    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} | College Football Power Index</title>
    {_meta_tags(f"THE CFB INDEX — Power and Resume rankings for every NCAA football team, with a fan-intelligence layer reading belief, respect, and rivalry heat. One universe from FBS through Division III.", title=f"THE CFB INDEX | {season_name}")}
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("", current="home")}
      <section class="home-shell">
        <div class="hero-mast premium-home-hero">
          <p class="eyebrow">{escape(str(editorial_context.get("hero_eyebrow") or "Fan Intelligence / Power / Resume"))}</p>
          <h1>{escape(str(editorial_context.get("hero_title") or "How college football is actually feeling this week."))}</h1>
          <p class="lede mast-copy">
            {escape(str(editorial_context.get("hero_lede") or "A single football universe for FBS through Division III, paired with a proprietary fan-intelligence layer that reads the belief, respect, and rivalry heat around every team. Built for argument, not dashboards."))}
          </p>
          {hero_meta_row}
        </div>

        {offseason_section}

        {fan_intel_section}

        <section class="dashboard-grid premium-dashboard-grid">
          <section class="main-column">
            {board}
          </section>

          <aside class="side-column premium-side-column">
            <article class="panel viz-panel">
              <div class="section-head compact-head">
                <h2>Power vs. Resume Analysis</h2>
              </div>
              {power_resume_plot}
            </article>

            <article class="panel highlight-panel">
              <div class="section-head compact-head">
                <h2>Highlight Cards</h2>
              </div>
              <div class="summary-strip summary-strip-rail">
                {summary_cards}
              </div>
            </article>

            <article class="panel viz-panel">
              <div class="section-head compact-head">
                <h2>Strength Ladder</h2>
              </div>
              {level_ladder}
            </article>
          </aside>
        </section>

        <section class="section two-up">
          <article class="panel tool-panel">
            <div class="section-head">
              <div>
                <h2>Matchup Studio</h2>
                <p class="section-note">Pick any two teams and get a current neutral-field or home-field projection from the predictive model.</p>
              </div>
              <a class="text-link" href="matchups/index.html">Open Matchups</a>
            </div>
            {matchup_studio}
          </article>

          <article class="panel">
            <div class="section-head">
              <div>
                <h2>Conference Power Map</h2>
                <p class="section-note">Depth matters. These cards surface leagues that carry real top-end strength and week-to-week density.</p>
              </div>
              <a class="text-link" href="conferences/index.html">All Conferences</a>
            </div>
            <div class="conference-card-grid conference-card-grid-compact">
              {conference_spotlight}
            </div>
          </article>
        </section>

        <section class="section">
          <div class="section-head">
            <div>
              <h2>Debate Desk</h2>
              <p class="section-note">These are the kinds of arguments college football fans actually have: best team versus best resume, cross-level showdowns, and crowded playoff lanes.</p>
            </div>
            <a class="text-link" href="compare/index.html">Open Compare</a>
          </div>
          <div class="feature-grid scenario-grid">
            {compare_cards}
          </div>
        </section>

        <section class="section">
          <div class="section-head">
            <div>
              <h2>Weekly Replay</h2>
              <p class="section-note">The best college-football products let people relive how the argument changed week by week. So do we.</p>
            </div>
            <a class="text-link" href="archive/index.html">Open Archive</a>
          </div>
          <div class="feature-grid archive-card-grid">
            {archive_cards}
          </div>
        </section>

        <section class="section">
          <div class="section-head">
            <div>
              <h2>Market Reality Check</h2>
              <p class="section-note">Where the betting market kept being too low, too high, or simply late to what the season was becoming.</p>
            </div>
          </div>
          <div class="feature-grid scenario-grid">
            {market_cards}
          </div>
        </section>

        <section class="section">
          <div class="section-head">
            <div>
              <h2>History Lab</h2>
              <p class="section-note">Previous seasons matter twice: they shape where teams start in August, and they give the board memory once the season is over.</p>
            </div>
            <a class="text-link" href="history/index.html">Open History</a>
          </div>
          <div class="feature-grid scenario-grid">
            {history_cards}
          </div>
          <div class="feature-grid history-level-grid">
            {history_level_cards}
          </div>
        </section>

        <section class="section">
          <div class="section-head">
            <div>
              <h2>Data Pulse</h2>
              <p class="section-note">What is loaded locally right now, what powers the numbers, and why the site can keep growing.</p>
            </div>
          </div>
          <div class="feature-grid pulse-grid">
            {site_pulse_cards}
          </div>
        </section>

        <section class="section">
          <div class="section-head">
            <h2>Subdivision Footprint</h2>
          </div>
          <div class="feature-grid counts-grid">
            {_render_count_cards()}
          </div>
          <p class="footer-note">Reference counts reflect the latest NCAA-published figures we are using as of {escape(PROGRAM_COUNT_REFERENCE_DATE)}.</p>
        </section>
      </section>
      <script id="matchupPayload" type="application/json">{matchup_payload}</script>
      <script>{_power_resume_plot_script()}</script>
      <script>{_home_board_script()}</script>
      <script>{_matchup_tool_script()}</script>
    </main>
  </body>
</html>
"""


def render_rankings_page_html(
    summary: dict[str, Any],
    rankings: list[RankingRow],
    latest_local_week: int,
    featured_team_pages: list[dict[str, Any]] | None = None,
    history_hub: dict[str, Any] | None = None,
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    featured_team_pages = featured_team_pages or []
    conferences = sorted({_clean_conference_name(str(row.conference_name or f"{row.level_code} Independents")) for row in rankings})
    table_rows = "\n".join(_render_rankings_row(row) for row in rankings)
    summary_cards = _render_summary_cards(featured_team_pages, prefix="../teams/") if featured_team_pages else ""
    compare_cards = _render_compare_feature_cards(featured_team_pages, prefix="../") if featured_team_pages else ""
    power_resume_plot = _render_power_resume_plot(featured_team_pages, prefix="../") if featured_team_pages else ""
    level_ladder = _render_strength_ladder(rankings)
    history_cards = _render_history_feature_cards(history_hub or {}, prefix="../programs/")
    history_level_cards = _render_history_level_cards(history_hub or {}, prefix="../programs/")

    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} Rankings</title>
    {_meta_tags(f"Power and Resume rankings for all NCAA football teams in {season_name}. FBS, FCS, Division II, and Division III on one board with filterable sort and conference views.", title=f"{season_name} Rankings | THE CFB INDEX", image_path="../og-image.svg")}
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="rankings")}
        <section class="hero">
          <p class="eyebrow">Power Rankings</p>
          <h1>{escape(season_name)} across every level.</h1>
          <p class="lede">
            Predictive power and season resume are shown side by side. The current published run is through week {escape(str(summary["week"]))},
            while your local game database is currently populated through week {latest_local_week}.
          </p>
          <p class="section-note">
            The list is meant to read like a clean selection-room board: how strong teams look right now, and what they have actually earned.
          </p>
          <div class="cta-row">
            <a class="button button-primary" href="../matchups/index.html">Open Matchups</a>
            <a class="button button-secondary" href="../compare/index.html">Compare Teams</a>
            <a class="button button-secondary" href="../conferences/index.html">Browse Conferences</a>
          </div>
        </section>

        <section class="section">
          <div class="home-meta-row panel">
            <div class="meta-pill"><span>Season</span><strong>{escape(season_name)}</strong></div>
            <div class="meta-pill"><span>Span</span><strong>{escape(season_span_label(season_year_value))}</strong></div>
            <div class="meta-pill"><span>Published Run</span><strong>Week {escape(str(summary["week"]))}</strong></div>
            <div class="meta-pill"><span>Site Universe</span><strong>{len(rankings)} ranked teams</strong></div>
          </div>
        </section>

        <section class="section two-up">
          <article class="panel">
            <div class="section-head">
              <div>
                <h2>Selection Room Readout</h2>
                <p class="section-note">Start with the top-line answers: who is surging, who owns the strongest body of work, and who looks most complete when power and resume agree.</p>
              </div>
              <a class="text-link" href="../teams/{escape(rankings[0].slug)}.html">Top Team File</a>
            </div>
            <div class="summary-strip">
              {summary_cards}
            </div>
          </article>

          <article class="panel">
            <div class="section-head">
              <div>
                <h2>Debate Starters</h2>
                <p class="section-note">The fastest way to make this rankings board feel alive is to surface the arguments fans actually want to have, not just the ordered list.</p>
              </div>
              <a class="text-link" href="../compare/index.html">Open Compare</a>
            </div>
            <div class="feature-grid scenario-grid">
              {compare_cards}
            </div>
          </article>
        </section>

        <section class="section two-up">
          <article class="panel viz-panel">
            <div class="section-head compact-head">
              <h2>Power vs. Resume Analysis</h2>
            </div>
            {power_resume_plot}
          </article>

          <article class="panel viz-panel">
            <div class="section-head compact-head">
              <h2>Strength Ladder</h2>
            </div>
            {level_ladder}
          </article>
        </section>

        <section class="section">
          <article class="panel">
            <div class="section-head">
              <div>
                <h2>Historical Context</h2>
                <p class="section-note">A serious rankings board needs memory. These cards surface the strongest loaded seasons, the biggest year-over-year jumps, and the programs with real staying power.</p>
              </div>
              <a class="text-link" href="../history/index.html">Open History</a>
            </div>
            <div class="feature-grid scenario-grid">
              {history_cards}
            </div>
            <div class="feature-grid history-level-grid">
              {history_level_cards}
            </div>
          </article>
        </section>

        <section class="section">
          <article class="panel">
            <div class="section-head">
              <div>
                <h2>Rankings Board Controls</h2>
                <p class="section-note">Keep the official board visible, but slice it the way fans actually browse: by level, league, rank range, or argument style.</p>
              </div>
              <a class="text-link" href="../compare/index.html">Open Compare</a>
            </div>
            {_metric_guide_strip()}
            <div class="board-utility">
              <div class="board-controls">
                <label class="board-control board-search">
                  <span>Search Teams</span>
                  <input id="rankingsSearch" type="search" placeholder="Search team, conference, or level">
                </label>
                <label class="board-control">
                  <span>Level</span>
                  <select id="rankingsLevelFilter">
                    <option value="ALL">All levels</option>
                    <option value="FBS">FBS</option>
                    <option value="FCS">FCS</option>
                    <option value="DII">Division II</option>
                    <option value="DIII">Division III</option>
                  </select>
                </label>
                <label class="board-control">
                  <span>Conference</span>
                  <select id="rankingsConferenceFilter">
                    <option value="ALL">All conferences</option>
                    {"".join(f'<option value="{escape(conf)}">{escape(conf)}</option>' for conf in conferences)}
                  </select>
                </label>
                <label class="board-control">
                  <span>Sort</span>
                  <select id="rankingsSortMode">
                    <option value="rank">Published rank</option>
                    <option value="power">Power</option>
                    <option value="resume">Resume</option>
                    <option value="team">Team A-Z</option>
                  </select>
                </label>
              </div>
              <div class="board-toolbar">
                <div class="jump-group" role="group" aria-label="Quick ranking range">
                  <button type="button" class="jump-chip" data-rankings-limit="25">Top 25</button>
                  <button type="button" class="jump-chip" data-rankings-limit="100">Top 100</button>
                  <button type="button" class="jump-chip is-active" data-rankings-limit="all">All teams</button>
                </div>
                <div class="board-status">
                  <strong id="rankingsCount">{len(rankings)}</strong>
                  <span>teams visible</span>
                </div>
                <button type="button" class="clear-filters" id="clearRankingsFilters">Clear filters</button>
              </div>
              <div class="active-filter-row" id="rankingsActiveFilterRow" hidden></div>
            </div>
          </article>
        </section>

        <section class="section">
          <div class="table-wrap">
            <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Change</th>
                <th>Team</th>
                <th>Level</th>
                <th>Power</th>
                <th>Resume</th>
              </tr>
            </thead>
            <tbody id="rankingsTableBody">
              {table_rows}
            </tbody>
          </table>
        </div>
      </section>
    </main>
    <script>{_power_resume_plot_script()}</script>
    <script>{_rankings_board_script()}</script>
  </body>
</html>
"""


def render_history_index_html(summary: dict[str, Any], history_hub: dict[str, Any], site_pulse: dict[str, Any]) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    level_cards = _render_history_level_cards(history_hub, prefix="../programs/")
    greatest_rows = _render_history_team_season_rows(history_hub.get("greatest_seasons") or [], prefix="../programs/")
    strongest_rows = _render_history_team_season_rows(history_hub.get("strongest_seasons") or [], prefix="../programs/")
    roughest_rows = _render_history_team_season_rows(history_hub.get("roughest_seasons") or [], prefix="../programs/")
    turnaround_rows = _render_history_program_rows(history_hub.get("turnarounds") or [], prefix="../programs/", mode="turnaround")
    collapse_rows = _render_history_program_rows(history_hub.get("collapses") or [], prefix="../programs/", mode="collapse")
    sustained_rows = _render_history_program_rows(history_hub.get("sustained_programs") or [], prefix="../programs/", mode="sustained")
    closest_rows = _render_history_program_rows(history_hub.get("closest_to_peak") or [], prefix="../programs/", mode="closest")
    run_rows = _render_history_program_rows(history_hub.get("best_two_year_runs") or [], prefix="../programs/", mode="run")
    season_cards = _render_history_season_summary_cards(history_hub, prefix="../programs/")
    preseason_playbook = _render_preseason_playbook_cards()
    explorer_rows = history_hub.get("explorer_rows") or []
    explorer_table_rows = _render_history_explorer_rows(explorer_rows)
    explorer_conferences = sorted({str(row.get("conference_name") or "") for row in explorer_rows if row.get("conference_name")})
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(season_name)} History</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="history")}
      <section class="hero">
        <p class="eyebrow">History</p>
        <h1>The archive should argue back.</h1>
        <p class="lede">
          World-class college-football products do not treat prior seasons like a dusty appendix. They turn history into context for today's rankings,
          tomorrow's preseason priors, and the long arc of every program across every level.
        </p>
      </section>

      <section class="section">
        <div class="home-meta-row panel">
          <div class="meta-pill"><span>Loaded seasons</span><strong>{int(history_hub.get("loaded_seasons") or 0)}</strong></div>
          <div class="meta-pill"><span>Archive span</span><strong>{escape(str(history_hub.get("first_season") or "--"))} to {escape(str(history_hub.get("last_season") or "--"))}</strong></div>
          <div class="meta-pill"><span>Modeled team-seasons</span><strong>{int(history_hub.get("team_seasons") or 0):,}</strong></div>
          <div class="meta-pill"><span>Completed games</span><strong>{int(site_pulse.get("completed_games") or 0):,}</strong></div>
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>Best By Level</h2>
            <p class="section-note">The all-level universe only becomes real when FBS, FCS, DII, and DIII each get their own historical peaks instead of being flattened into one pile.</p>
          </div>
        </div>
        <div class="feature-grid history-level-grid">
          {level_cards}
        </div>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Greatest Loaded Seasons</h2>
              <p class="section-note">Sorted by the body-of-work side first, because greatness should not just mean the prettiest predictive number.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Team</th>
                  <th>Record</th>
                  <th>Final Rank</th>
                  <th>Power</th>
                  <th>Resume</th>
                </tr>
              </thead>
              <tbody>
                {greatest_rows}
              </tbody>
            </table>
          </div>
        </article>

        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Strongest Loaded Teams</h2>
              <p class="section-note">This is the predictive side: the most powerful closing teams currently modeled in the archive.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Team</th>
                  <th>Record</th>
                  <th>Final Rank</th>
                  <th>Power</th>
                  <th>Resume</th>
                </tr>
              </thead>
              <tbody>
                {strongest_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Closest To Program Peak</h2>
              <p class="section-note">The most addictive historical question is usually not “who was great once?” It is “how close is this team to the best version of itself?”</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Program</th>
                  <th>Latest Season</th>
                  <th>Peak Gap</th>
                  <th>Context</th>
                </tr>
              </thead>
              <tbody>
                {closest_rows}
              </tbody>
            </table>
          </div>
        </article>

        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Best Two-Year Runs</h2>
              <p class="section-note">Single years make headlines. Back-to-back years are where programs start to look like eras.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Program</th>
                  <th>Window</th>
                  <th>Average Power</th>
                  <th>Context</th>
                </tr>
              </thead>
              <tbody>
                {run_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Turnarounds</h2>
              <p class="section-note">Programs do not just drift. These are the biggest year-over-year power jumps in the loaded archive.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Program</th>
                  <th>Jump Season</th>
                  <th>Change</th>
                  <th>Latest Finish</th>
                </tr>
              </thead>
              <tbody>
                {turnaround_rows}
              </tbody>
            </table>
          </div>
        </article>

        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Dynasty Track</h2>
              <p class="section-note">KenPom-style products win because they remember ecosystems over time. These are the programs with the strongest average closing power across the loaded span.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Program</th>
                  <th>Loaded Seasons</th>
                  <th>Average Power</th>
                  <th>Latest Season</th>
                </tr>
              </thead>
              <tbody>
                {sustained_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Roughest Loaded Seasons</h2>
              <p class="section-note">History is more honest when it remembers the bad years too, not just the highlight reel.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Team</th>
                  <th>Record</th>
                  <th>Final Rank</th>
                  <th>Power</th>
                  <th>Resume</th>
                </tr>
              </thead>
              <tbody>
                {roughest_rows}
              </tbody>
            </table>
          </div>
        </article>

        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Hard Landings</h2>
              <p class="section-note">When a program falls off, the drop should be visible instead of being hand-waved away as a reset.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Program</th>
                  <th>Drop Season</th>
                  <th>Change</th>
                  <th>Latest Finish</th>
                </tr>
              </thead>
              <tbody>
                {collapse_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>Season Almanac</h2>
            <p class="section-note">Each season should read like its own editorial package: who looked strongest, who owned the best resume, and who stacked the cleanest record.</p>
          </div>
          <a class="text-link" href="../archive/index.html">Weekly archive</a>
        </div>
        <div class="feature-grid archive-card-grid">
          {season_cards}
        </div>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>History Explorer</h2>
              <p class="section-note">This is the query layer serious fans expect: every loaded team-season in one searchable table, with level, conference-era, and season-context filters built in.</p>
            </div>
            <a class="text-link" href="../programs/index.html">Programs Explorer</a>
          </div>
          <div class="board-utility">
            <div class="board-controls">
              <label class="board-control board-search">
                <span>Search Seasons</span>
                <input id="historyExplorerSearch" type="search" placeholder="Search program, conference, level, or season">
              </label>
              <label class="board-control">
                <span>Level</span>
                <select id="historyExplorerLevelFilter">
                  <option value="ALL">All levels</option>
                  <option value="FBS">FBS</option>
                  <option value="FCS">FCS</option>
                  <option value="DII">Division II</option>
                  <option value="DIII">Division III</option>
                </select>
              </label>
              <label class="board-control">
                <span>Conference</span>
                <select id="historyExplorerConferenceFilter">
                  <option value="ALL">All conferences</option>
                  {"".join(f'<option value="{escape(conf)}">{escape(conf)}</option>' for conf in explorer_conferences)}
                </select>
              </label>
              <label class="board-control">
                <span>Sort</span>
                <select id="historyExplorerSort">
                  <option value="season-desc">Newest seasons</option>
                  <option value="power-desc">Strongest power</option>
                  <option value="resume-desc">Best resume</option>
                  <option value="rank-asc">Best finish</option>
                  <option value="winpct-desc">Best win rate</option>
                  <option value="margin-desc">Best scoring margin</option>
                  <option value="team">Program A-Z</option>
                </select>
              </label>
            </div>
            <div class="board-toolbar">
              <div class="board-status">
                <strong id="historyExplorerCount">{len(explorer_rows)}</strong>
                <span>seasons visible</span>
              </div>
              <button type="button" class="clear-filters" id="clearHistoryExplorerFilters">Clear filters</button>
            </div>
            <div class="active-filter-row" id="historyExplorerActiveFilterRow" hidden></div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Program</th>
                  <th>Lens</th>
                  <th>Record</th>
                  <th>Final Rank</th>
                  <th>Power</th>
                  <th>Resume</th>
                  <th>Margin</th>
                  <th>Open</th>
                </tr>
              </thead>
              <tbody id="historyExplorerBody">
                {explorer_table_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>How Teams Start The Next Season</h2>
            <p class="section-note">The preseason board should have memory, but not destiny. This is the fan-facing version of how previous years affect the next cycle.</p>
          </div>
        </div>
        <div class="feature-grid scenario-grid">
          {preseason_playbook}
        </div>
      </section>
    </main>
    <script>{_history_explorer_script()}</script>
  </body>
</html>
"""


def render_team_page_html(summary: dict[str, Any], team_data: dict[str, Any]) -> str:
    ranking: RankingRow = team_data["ranking"]
    team = team_data["team"]
    season_summary = team_data["season_summary"]
    schedule = team_data["schedule"]
    history = team_data["history"]
    history_insights = team_data["history_insights"]
    history_profile = team_data["history_profile"]
    phase_summary = sorted(team_data["phase_summary"], key=lambda row: _phase_sort_key(row.get("season_phase")))
    efficiency_snapshot = team_data["efficiency_snapshot"]
    journey_points = team_data.get("journey_points") or []
    trend_points = team_data["trend_points"]
    rating_path = team_data["rating_path"]
    peer_context = team_data.get("peer_context") or {}

    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    team_name = str(team.get("canonical_name") or ranking.team_name)
    conference = _clean_conference_name(str(team.get("conference_name") or f"{ranking.level_code} Independents"))
    conference_slug = _conference_slug(conference, ranking.level_code)
    wins = int(season_summary.get("wins") or 0)
    losses = int(season_summary.get("losses") or 0)
    pf = int(season_summary.get("points_for") or 0)
    pa = int(season_summary.get("points_against") or 0)
    best_result = _best_result_text(ranking.team_id, schedule)
    worst_result = _worst_result_text(ranking.team_id, schedule)
    recent_form = _compact_recent_form(ranking.team_id, schedule)
    efficiency_note = _best_efficiency_signal(efficiency_snapshot)
    schedule_rows = "\n".join(_render_schedule_row(ranking.team_id, row) for row in schedule)
    history_rows = "\n".join(_render_history_row(row, history_profile) for row in history)
    phase_rows = "\n".join(_render_phase_row(row) for row in phase_summary)
    history_signal_cards = _render_team_history_cards(history_insights)
    history_snapshot = _render_team_history_snapshot(history_profile)
    story_cards = _render_team_story_cards(
        ranking,
        best_result,
        worst_result,
        recent_form,
        efficiency_note,
        phase_summary,
        season_year_value,
    )
    impact_cards = _render_game_impact_cards(ranking.team_id, schedule)
    impact_table = _render_game_impact_table(ranking.team_id, schedule)
    phase_pills = _render_phase_pills(phase_summary)
    history_chart = _render_history_chart(history)
    similarity_cards = team_data.get("similarity_cards") or []
    historical_dna = _render_historical_dna(team_name, similarity_cards)
    betting_summary = team_data.get("betting_summary") or {}
    betting_overview = _render_team_betting_overview(team_data)
    betting_table = _render_team_betting_table(ranking.team_id, schedule)
    team_theme = _team_theme(ranking.slug)
    team_mark = _team_mark(team_name, slug=ranking.slug)
    from cfb_rankings.visual_assets import team_logo_src
    hero_logo_path = team_logo_src(ranking.slug)
    hero_logo_html = (
        f'<img src="../{hero_logo_path.lstrip("/")}" alt="{escape(team_name)} logo" '
        f'width="120" height="120" class="team-hero-logo" loading="lazy">'
        if hero_logo_path else ""
    )
    net_points = pf - pa
    mood_profile = team_data.get("mood_profile") or {}
    mood_card = _render_team_mood_card(mood_profile, team_name=team_name)
    cohort_rows = team_data.get("cohort_rows") or []
    cohort_panel = _render_cohort_panel(cohort_rows, team_name=team_name)
    archetype_module = team_data.get("archetype_module_html") or ""
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(team_name)} | {escape(season_name)}</title>
    {_meta_tags(f"{team_name} {season_name}: record {int(season_summary.get('wins') or 0)}-{int(season_summary.get('losses') or 0)}, Power {_public_power_text(ranking.power_display)}, Resume {_public_resume_text(ranking.resume_display)}. Mood, matchups, and the model's read on the season.", title=f"{team_name} | {season_name}", image_path=f"{ranking.slug}-og.svg")}
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="team")}
      <section class="team-shell" style="--team-accent:{team_theme['accent']}; --team-accent-soft:{team_theme['accent_soft']};">
        <div class="team-breadcrumbs">
          <a href="../programs/index.html">Programs</a>
          <span>/</span>
          <a href="../programs/{escape(ranking.slug)}.html">{escape(team_name)}</a>
          <span>/</span>
          <a href="../conferences/{escape(conference_slug)}.html">{escape(conference)}</a>
          <span>/</span>
          <strong>{escape(season_name)}</strong>
        </div>
        <section class="hero team-hero premium-team-hero">
          <div class="team-hero-top">
            <div class="team-hero-heading">
              {hero_logo_html}
              <div>
                <h1>{escape(team_name)}</h1>
                <p class="team-hero-sub">{escape(conference)} Conference</p>
              </div>
            </div>
            <div class="team-rank-chip">Rank #{ranking.rank}</div>
          </div>
          <div class="team-stat-ribbon">
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Record</span>
                <strong>{wins}-{losses}</strong>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Power</span>
                <strong>{_public_power_text(ranking.power_display)}</strong>
                <span class="submetric">pts vs avg NCAA team</span>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Resume</span>
                <strong>{_public_resume_text(ranking.resume_display)}</strong>
                <span class="submetric">{_public_resume_percentile_label(ranking.resume_display)}</span>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Net Points</span>
                <strong>{net_points:+d}</strong>
              </div>
            </article>
          </div>
          <div class="team-hero-actions">
            <a class="button button-primary" href="../programs/{escape(ranking.slug)}.html">Program History</a>
            <a class="button button-primary" href="../matchups/index.html">Matchup Simulator</a>
            <a class="button button-secondary" href="../compare/index.html">Compare Teams</a>
            <a class="button button-secondary" href="../rankings/index.html">Back To Rankings</a>
          </div>
        </section>
      </section>

      {mood_card}

      {cohort_panel}

      <section class="section team-archetype-section">
        <div class="section-head">
          <h2>Fanbase Archetype</h2>
          <p class="section-sub">How this fanbase sorts in the Fan Intelligence taxonomy (N\u00b0 04 on the Hub).</p>
        </div>
        {archetype_module}
        <link rel="stylesheet" href="../hub/archetype-module.css" onerror="this.remove()">
      </section>

      <section class="section premium-team-grid">
        <article class="panel narrative-panel">
          <div class="section-head">
            <h2>Performance Narrative</h2>
          </div>
          {_render_team_journey_chart(journey_points)}
        </article>

        <aside class="panel game-impact-panel">
          <div class="section-head">
            <h2>Game Impact Board</h2>
          </div>
          {impact_table}
          <p class="footer-note">Best signal: {escape(best_result)}. Stress point: {escape(worst_result)}</p>
        </aside>
      </section>

      <section class="section premium-team-grid">
        <article class="panel">
          <div class="section-head">
            <h2>Betting Lens</h2>
            <p class="section-note">Market context is a second read on the season: how often this team rewarded believers, disappointed them, or played into totals differently than expected.</p>
          </div>
          {betting_overview}
        </article>

        <aside class="panel">
          <div class="section-head">
            <h2>Market Game Log</h2>
            <p class="section-note">Closing lines from {escape(str(betting_summary.get("provider_text") or "CFBD providers"))} when available.</p>
          </div>
          {betting_table}
        </aside>
      </section>

      <section class="section premium-team-grid">
        <article class="panel">
          <div class="section-head">
            <h2>Efficiency Dashboard</h2>
            <p class="section-note">Opponent-adjusted efficiency cards organized as a premium team dashboard.</p>
          </div>
          <div class="feature-grid efficiency-dashboard-grid">
            {_render_efficiency_cards(efficiency_snapshot)}
          </div>
        </article>

        <aside class="panel">
          {historical_dna}
        </aside>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Why The Model Has Them Here</h2>
          <p class="section-note">A team page should explain the ranking, not just print it.</p>
        </div>
        <div class="feature-grid team-story-grid">
          {story_cards}
        </div>
      </section>

      {_render_team_peer_section(team_data, peer_context)}

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Historical Snapshot</h2>
              <p class="section-note">Fans should be able to see the short version immediately: how big the loaded sample is, what this program's standard looks like, and where the current season sits inside that arc.</p>
            </div>
          </div>
          {history_snapshot}
        </article>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <h2>Program Arc</h2>
            <p class="section-note">Bars track win rate. The line tracks end-of-season power, so users can see whether the program is actually getting stronger or just stacking wins.</p>
          </div>
          {history_chart}
        </article>

        <article class="panel">
          <div class="section-head">
            <h2>Season Phase Split</h2>
            <p class="section-note">How this season breaks apart inside the same year-defined competitive cycle.</p>
          </div>
          <div class="phase-pill-row">
            {phase_pills}
          </div>
          <div class="table-wrap compact-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Phase</th>
                  <th>Record</th>
                  <th>Games</th>
                </tr>
              </thead>
              <tbody>
                {phase_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Loaded History Signals</h2>
          <p class="section-note">This is the fastest way to explain what the last few seasons say about the program, and why prior success should matter in the next preseason cycle.</p>
        </div>
        <div class="feature-grid team-story-grid">
          {history_signal_cards}
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Impact Cards</h2>
          <p class="section-note">A card-based alternate view of the same rating swings for fans who want the season game by game.</p>
        </div>
        <div class="impact-card-grid">
          {impact_cards}
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>{escape(season_name)} Schedule And Rating Movement</h2>
          <p class="section-note">Every result, every phase, and how the rating changed because of it.</p>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Week</th>
                <th>Date</th>
                <th>Game</th>
                <th>Phase</th>
                <th>Result</th>
                <th>Close</th>
                <th>ATS</th>
                <th>Total</th>
                <th>Pregame</th>
                <th>Power Change</th>
                <th>Resume Change</th>
                <th>Postgame</th>
              </tr>
            </thead>
            <tbody>
              {schedule_rows}
            </tbody>
          </table>
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Year-By-Year Results</h2>
          <p class="section-note">The competitive story by season, kept cleanly tied to the year each season began.</p>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Season</th>
                <th>Lens</th>
                <th>Record</th>
                <th>Final Rank</th>
                <th>End Power</th>
                <th>End Resume</th>
                <th>Games</th>
                <th>Points For</th>
                <th>Points Against</th>
                <th>Margin</th>
              </tr>
            </thead>
            <tbody>
              {history_rows}
            </tbody>
          </table>
        </div>
      </section>
    </main>
    <script>{_team_journey_script()}</script>
  </body>
</html>
"""


def render_programs_index_html(
    summary: dict[str, Any],
    explorer_rows: list[dict[str, Any]],
    history_hub: dict[str, Any],
    site_pulse: dict[str, Any],
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    cards = _render_program_explorer_cards(explorer_rows)
    table_rows = "".join(_render_program_explorer_row(row) for row in explorer_rows)
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Programs | {escape(season_name)}</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="programs")}
      <section class="hero">
        <p class="eyebrow">Programs</p>
        <h1>Program history should be explorable, not buried.</h1>
        <p class="lede">
          This explorer turns every loaded team into a long-arc program page: peak teams, best resumes, conference-era changes,
          and the question fans actually ask first, which is how the current season stacks up against what that program normally is.
        </p>
      </section>

      <section class="section">
        <div class="home-meta-row panel">
          <div class="meta-pill"><span>Programs</span><strong>{len(explorer_rows):,}</strong></div>
          <div class="meta-pill"><span>Archive span</span><strong>{escape(str(history_hub.get("first_season") or "--"))} to {escape(str(history_hub.get("last_season") or "--"))}</strong></div>
          <div class="meta-pill"><span>Modeled team-seasons</span><strong>{int(history_hub.get("team_seasons") or 0):,}</strong></div>
          <div class="meta-pill"><span>Current season</span><strong>{escape(season_name)}</strong></div>
        </div>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Program Signals</h2>
              <p class="section-note">A premium history explorer needs instant starting points, not just one giant table.</p>
            </div>
            <a class="text-link" href="../history/index.html">Open History Hub</a>
          </div>
          <div class="feature-grid scenario-grid">
            {cards}
          </div>
        </article>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Program Explorer</h2>
              <p class="section-note">Season-aware conference memberships power the era view here, so historical rows follow the conference a team actually belonged to that season.</p>
            </div>
          </div>
          <div class="board-utility">
            <div class="board-controls">
              <label class="board-control board-search">
                <span>Search Programs</span>
                <input id="programSearch" type="search" placeholder="Search program, conference, or level">
              </label>
              <label class="board-control">
                <span>Level</span>
                <select id="programLevelFilter">
                  <option value="ALL">All levels</option>
                  <option value="FBS">FBS</option>
                  <option value="FCS">FCS</option>
                  <option value="DII">Division II</option>
                  <option value="DIII">Division III</option>
                </select>
              </label>
              <label class="board-control">
                <span>Sort</span>
                <select id="programSort">
                  <option value="current-rank">Current board</option>
                  <option value="latest-power">Latest power</option>
                  <option value="peak-power">Peak loaded power</option>
                  <option value="best-resume">Best loaded resume</option>
                  <option value="loaded-seasons">Loaded seasons</option>
                  <option value="current-vs-baseline">Current vs baseline</option>
                  <option value="volatility">Volatility</option>
                </select>
              </label>
            </div>
            <div class="board-status">
              <span class="status-pill"><strong id="programVisibleCount">{len(explorer_rows)}</strong> programs visible</span>
              <a class="button button-secondary" href="../rankings/index.html">Open Current Board</a>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Program</th>
                  <th>Current Board</th>
                  <th>Latest Season</th>
                  <th>Loaded Seasons</th>
                  <th>Peak Power</th>
                  <th>Best Resume</th>
                  <th>Best Finish</th>
                  <th>Vs. Baseline</th>
                  <th>Volatility</th>
                  <th>Season Page</th>
                </tr>
              </thead>
              <tbody id="programExplorerBody">
                {table_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>
      <script>{_programs_explorer_script()}</script>
    </main>
  </body>
</html>
"""


def render_teams_index_html(
    summary: dict[str, Any],
    rankings: list[RankingRow],
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    level_counts: dict[str, int] = {}
    conference_set: set[tuple[str, str]] = set()
    rendered_rows: list[str] = []
    for row in rankings:
        level = str(row.level_code or "")
        conference = _clean_conference_name(str(row.conference_name or f"{level} Independents"))
        level_counts[level] = level_counts.get(level, 0) + 1
        if row.conference_name:
            conference_set.add((level, conference))
        rank_text = str(row.rank) if row.rank else "--"
        power_text = _public_power_text(row.power_display)
        resume_text = _public_resume_text(row.resume_display)
        search_blob = f"{row.team_name} {conference} {level}".lower()
        rendered_rows.append(
            f"""
            <tr
              class="teams-index-row"
              data-search="{escape(search_blob)}"
              data-level="{escape(level)}"
              data-conference="{escape(conference)}"
              data-team="{escape(str(row.team_name).lower())}"
            >
              <td class="metric-cell">#{escape(rank_text)}</td>
              <td><a class="team-link" href="{escape(row.slug)}.html">{escape(row.team_name)}</a><span class="submetric">{escape(conference)}</span></td>
              <td><span class="pill level-{escape(level)}">{escape(level)}</span></td>
              <td class="metric-cell">{power_text}</td>
              <td class="metric-cell">{resume_text}</td>
            </tr>
            """
        )
    table_rows = "".join(rendered_rows)
    conference_options = "".join(
        f'<option value="{escape(conf)}">{escape(conf)} ({escape(level)})</option>'
        for level, conf in sorted(conference_set, key=lambda pair: (pair[0], pair[1]))
    )
    level_summary = " | ".join(
        f"{level_counts.get(level, 0):,} {level}"
        for level in ("FBS", "FCS", "DII", "DIII")
        if level_counts.get(level)
    )
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Teams | {escape(season_name)}</title>
    {_meta_tags(f"Every NCAA football team for {season_name} — FBS, FCS, Division II, and Division III. Filter by level, browse by conference, search by name.", title=f"Teams | {season_name}", image_path="../og-image.svg")}
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="teams")}
      <section class="hero">
        <p class="eyebrow">Teams</p>
        <h1>Every team, every level, one index.</h1>
        <p class="lede">
          All {len(rankings):,} current-season teams across FBS, FCS, Division II, and Division III.
          Filter by level or conference, search by name, then click through to the team's season page.
        </p>
      </section>

      <section class="section">
        <div class="home-meta-row panel">
          <div class="meta-pill"><span>Teams</span><strong>{len(rankings):,}</strong></div>
          <div class="meta-pill"><span>Conferences</span><strong>{len(conference_set)}</strong></div>
          <div class="meta-pill"><span>Coverage</span><strong>{escape(level_summary or '--')}</strong></div>
          <div class="meta-pill"><span>Current season</span><strong>{escape(season_name)}</strong></div>
        </div>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Team Browser</h2>
              <p class="section-note">Current-season snapshot. Rank and metrics reflect the latest model checkpoint; click a team to open the full season page.</p>
            </div>
            <a class="text-link" href="../programs/index.html">Long-arc Programs Explorer</a>
          </div>
          <div class="board-utility">
            <div class="board-controls">
              <label class="board-control board-search">
                <span>Search</span>
                <input id="teamsSearch" type="search" placeholder="Team, conference, or level">
              </label>
              <label class="board-control">
                <span>Level</span>
                <select id="teamsLevelFilter">
                  <option value="ALL">All levels</option>
                  <option value="FBS">FBS</option>
                  <option value="FCS">FCS</option>
                  <option value="DII">Division II</option>
                  <option value="DIII">Division III</option>
                </select>
              </label>
              <label class="board-control">
                <span>Conference</span>
                <select id="teamsConferenceFilter">
                  <option value="ALL">All conferences</option>
                  {conference_options}
                </select>
              </label>
            </div>
            <div class="board-status">
              <span class="status-pill"><strong id="teamsVisibleCount">{len(rankings)}</strong> teams visible</span>
              <a class="button button-secondary" href="../rankings/index.html">Open Power Rankings</a>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Team</th>
                  <th>Level</th>
                  <th>Power</th>
                  <th>Resume</th>
                </tr>
              </thead>
              <tbody id="teamsIndexBody">
                {table_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>
      <script>{_teams_index_script()}</script>
    </main>
  </body>
</html>
"""


def _teams_index_script() -> str:
    return """
      (() => {
        const body = document.getElementById('teamsIndexBody');
        const search = document.getElementById('teamsSearch');
        const levelFilter = document.getElementById('teamsLevelFilter');
        const conferenceFilter = document.getElementById('teamsConferenceFilter');
        const visibleCount = document.getElementById('teamsVisibleCount');
        if (!body) return;
        const rows = Array.from(body.querySelectorAll('.teams-index-row'));

        function apply() {
          const q = (search?.value || '').trim().toLowerCase();
          const level = levelFilter?.value || 'ALL';
          const conf = conferenceFilter?.value || 'ALL';
          let shown = 0;
          rows.forEach((row) => {
            const matchesLevel = level === 'ALL' || row.dataset.level === level;
            const matchesConf = conf === 'ALL' || row.dataset.conference === conf;
            const matchesSearch = !q || (row.dataset.search || '').includes(q);
            const show = matchesLevel && matchesConf && matchesSearch;
            row.style.display = show ? '' : 'none';
            if (show) shown += 1;
          });
          if (visibleCount) visibleCount.textContent = shown;
        }

        [search, levelFilter, conferenceFilter].forEach((el) => {
          if (!el) return;
          const evt = el.tagName === 'SELECT' ? 'change' : 'input';
          el.addEventListener(evt, apply);
        });
        apply();
      })();
    """


def render_program_page_html(summary: dict[str, Any], program_data: dict[str, Any]) -> str:
    team = program_data.get("team") or {}
    history = program_data.get("history") or []
    history_profile = program_data.get("history_profile") or {}
    history_insights = program_data.get("history_insights") or []
    conference_timeline = program_data.get("conference_timeline") or {}
    current_ranking: RankingRow | None = program_data.get("current_ranking")

    team_name = str(team.get("canonical_name") or "Program")
    team_slug = str(team.get("slug") or "")
    level_code = str(team.get("level_code") or (history[0].get("level_code") if history else ""))
    conference_name = _clean_conference_name(
        str(
            conference_timeline.get("latest_conference")
            or team.get("conference_name")
            or (history[0].get("conference_name") if history else f"{level_code} Independents")
        )
    )
    history_chart = _render_history_chart(history)
    history_snapshot = _render_team_history_snapshot(history_profile)
    history_cards = _render_team_history_cards(history_insights)
    season_rows = "\n".join(
        _render_program_season_explorer_row(row, history_profile, program_data.get("current_season_url"))
        for row in history
    )
    season_filter_conferences = sorted(
        {
            _clean_conference_name(str(row.get("conference_name") or f"{row.get('level_code') or ''} Independents"))
            for row in history
        }
    )
    program_subnav = _render_player_page_subnav(
        [
            ("program-arc", "Arc"),
            ("historical-snapshot", "Snapshot"),
            ("current-context", "Context"),
            ("program-signals", "Signals"),
            ("season-explorer", "Seasons"),
        ]
    )

    peak_power_row = history_profile.get("peak_power_row") or {}
    best_resume_row = history_profile.get("best_resume_row") or {}
    best_finish_row = history_profile.get("best_finish_row") or {}
    baseline_power = history_profile.get("baseline_power")
    current_vs_baseline = history_profile.get("current_vs_baseline")
    gap_to_peak_power = history_profile.get("gap_to_peak_power")
    latest_row = history_profile.get("current_row") or (history[0] if history else {})

    team_theme = _team_theme(team_slug)
    team_mark = _team_mark(team_name, slug=team_slug)
    current_rank_text = "--" if current_ranking is None else f"#{current_ranking.rank}"
    latest_record = "--" if not latest_row else f"{int(latest_row.get('wins') or 0)}-{int(latest_row.get('losses') or 0)}"
    latest_season_year = int(latest_row.get("season_year") or 0)

    best_finish_text = (
        "--"
        if not best_finish_row or best_finish_row.get("final_rank") is None
        else f"#{int(best_finish_row.get('final_rank') or 0)} in {int(best_finish_row.get('season_year') or 0)}"
    )
    peak_power_text = (
        "--"
        if not peak_power_row or peak_power_row.get("end_power") is None
        else f"{int(peak_power_row.get('season_year') or 0)} | {_public_power_text(peak_power_row.get('end_power_display'))}"
    )
    best_resume_text = (
        "--"
        if not best_resume_row or best_resume_row.get("end_resume") is None
        else f"{int(best_resume_row.get('season_year') or 0)} | {_public_resume_text(best_resume_row.get('end_resume_display'))} / 100"
    )
    current_context = f"""
    <div class="feature-grid history-snapshot-grid">
      <article class="stat-card">
        <span>Current board</span>
        <strong>{escape(current_rank_text)}</strong>
        <span class="submetric">Where the latest loaded season sits on today's all-level board.</span>
      </article>
      <article class="stat-card">
        <span>Latest season</span>
        <strong>{escape(str(latest_season_year or '--'))}</strong>
        <span class="submetric">{escape(latest_record)}</span>
      </article>
      <article class="stat-card">
        <span>Program baseline</span>
        <strong>{escape(_public_power_text(baseline_power))}</strong>
        <span class="submetric">Recent multi-year closing-power standard.</span>
      </article>
      <article class="stat-card">
        <span>Gap to peak</span>
        <strong>{"--" if gap_to_peak_power is None else f"{float(gap_to_peak_power):.1f}"}</strong>
        <span class="submetric">How far the latest season sits below the program's strongest loaded team.</span>
      </article>
    </div>
    """
    season_name = season_label(int(summary["season_year"]))
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(team_name)} Program History</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="programs")}
      <section class="team-shell" style="--team-accent:{team_theme['accent']}; --team-accent-soft:{team_theme['accent_soft']};">
        <div class="team-breadcrumbs">
          <a href="../programs/index.html">Programs</a>
          <span>/</span>
          <a href="../history/index.html">History</a>
          <span>/</span>
          <strong>{escape(team_name)}</strong>
        </div>
        <section class="hero team-hero premium-team-hero">
          <div class="team-hero-top">
            <div>
              <h1>{escape(team_name)}</h1>
              <p class="team-hero-sub">{escape(level_code)} program | latest conference era: {escape(conference_name)}</p>
            </div>
            <div class="team-rank-chip">Program Explorer</div>
          </div>
          <div class="team-stat-ribbon">
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Loaded Seasons</span>
                <strong>{int(history_profile.get("loaded_seasons") or 0)}</strong>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Latest Season</span>
                <strong>{escape(str(latest_season_year or '--'))}</strong>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Peak Loaded Season</span>
                <strong>{escape(peak_power_text)}</strong>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Best Finish</span>
                <strong>{escape(best_finish_text)}</strong>
              </div>
            </article>
          </div>
          <div class="team-hero-actions">
            {f'<a class="button button-primary" href="{program_data.get("current_season_url")}">{escape(season_name)} Season Page</a>' if program_data.get("current_season_url") else ''}
            <a class="button button-secondary" href="../rankings/index.html">Current Rankings</a>
            <a class="button button-secondary" href="../history/index.html">History Hub</a>
          </div>
          {program_subnav}
        </section>
      </section>

      <section class="section premium-team-grid player-anchor-section" id="program-arc">
        <article class="panel narrative-panel">
          <div class="section-head">
            <h2>Program Arc</h2>
            <p class="section-note">Win rate shows the results layer. End-of-season power shows the strength layer. A serious history page needs both.</p>
          </div>
          {history_chart}
        </article>

        <aside class="panel">
          <div class="section-head">
            <h2>Conference Journey</h2>
            <p class="section-note">These eras follow the actual season-specific conference membership stored for each loaded year, not today's alignment.</p>
          </div>
          {_render_program_conference_timeline(conference_timeline)}
        </aside>
      </section>

      <section class="section player-anchor-section" id="historical-snapshot">
        <article class="panel">
          <div class="section-head">
            <h2>Historical Snapshot</h2>
            <p class="section-note">A fast read on what this program usually is, what its peak looks like, and how the latest season compares.</p>
          </div>
          {history_snapshot}
        </article>
      </section>

      <section class="section player-anchor-section" id="current-context">
        <article class="panel">
          <div class="section-head">
            <h2>Current Context</h2>
            <p class="section-note">The premium fan question is not only "how good is this team?" It is "how good is this season relative to the program I know?"</p>
          </div>
          {current_context}
        </article>
      </section>

      <section class="section player-anchor-section" id="program-signals">
        <div class="section-head">
          <h2>Program Signals</h2>
          <p class="section-note">The clearest historical takeaways, written for scan speed.</p>
        </div>
        <div class="feature-grid team-story-grid">
          {history_cards}
        </div>
      </section>

      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <h2>Best Resume Season</h2>
          </div>
          <p class="lede" style="margin:0;">{escape(best_resume_text)}</p>
          <p class="footer-note">The strongest body-of-work season in the loaded archive for this program.</p>
        </article>

        <article class="panel">
          <div class="section-head">
            <h2>Latest Vs. Standard</h2>
          </div>
          <p class="lede" style="margin:0;">{escape(_public_power_text(current_vs_baseline))}</p>
          <p class="footer-note">Positive means the latest season closed above the program's recent baseline. Negative means it finished below the standard.</p>
        </article>
      </section>

      <section class="section player-anchor-section" id="season-explorer">
        <div class="section-head">
          <h2>Season Explorer</h2>
          <p class="section-note">Every loaded season, with conference era attached to the correct year and filters built for the questions fans actually ask.</p>
        </div>
        <div class="board-utility">
          <div class="board-controls">
            <label class="board-control board-search">
              <span>Search Seasons</span>
              <input id="programSeasonSearch" type="search" placeholder="Search season, lens, conference, or level">
            </label>
            <label class="board-control">
              <span>Conference</span>
              <select id="programSeasonConferenceFilter">
                <option value="ALL">All conferences</option>
                {"".join(f'<option value="{escape(conf)}">{escape(conf)}</option>' for conf in season_filter_conferences)}
              </select>
            </label>
            <label class="board-control">
              <span>Lens</span>
              <select id="programSeasonLensFilter">
                <option value="ALL">All lenses</option>
                <option value="Current">Current</option>
                <option value="Peak power">Peak power</option>
                <option value="Best resume">Best resume</option>
                <option value="Best finish">Best finish</option>
                <option value="Best record">Best record</option>
                <option value="Above standard">Above standard</option>
                <option value="Down year">Down year</option>
                <option value="In range">In range</option>
              </select>
            </label>
            <label class="board-control">
              <span>Sort</span>
              <select id="programSeasonSort">
                <option value="season-desc">Newest seasons</option>
                <option value="power-desc">Strongest power</option>
                <option value="resume-desc">Best resume</option>
                <option value="rank-asc">Best finish</option>
                <option value="margin-desc">Best margin</option>
                <option value="wins-desc">Most wins</option>
              </select>
            </label>
          </div>
          <div class="board-toolbar">
            <div class="board-status">
              <strong id="programSeasonVisibleCount">{len(history)}</strong>
              <span>seasons visible</span>
            </div>
            <button type="button" class="clear-filters" id="clearProgramSeasonFilters">Clear filters</button>
          </div>
          <div class="active-filter-row" id="programSeasonActiveFilterRow" hidden></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Season</th>
                <th>Conference</th>
                <th>Lens</th>
                <th>Record</th>
                <th>Final Rank</th>
                <th>End Power</th>
                <th>End Resume</th>
                <th>Margin</th>
                <th>Season Page</th>
              </tr>
            </thead>
            <tbody id="programSeasonExplorerBody">
              {season_rows}
            </tbody>
          </table>
        </div>
      </section>
    </main>
    <script>{_program_page_script()}</script>
  </body>
</html>
"""


def render_heisman_page_html(
    summary: dict[str, Any],
    heisman_snapshot: dict[str, Any],
    player_directory_rows: list[dict[str, Any]],
    team_conference_map: dict[str, str] | None = None,
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    board_rows: list[HeismanRankingRow] = heisman_snapshot.get("rows") or []
    conference_fallback_by_player = {
        int(row["player_id"]): str(row.get("conference_name") or row.get("primary_conference_name") or "").strip()
        for row in player_directory_rows
        if row.get("player_id") is not None and (row.get("conference_name") or row.get("primary_conference_name"))
    }
    board_rows = [
        replace(
            row,
            conference_name=(
                str(row.conference_name or "").strip()
                or conference_fallback_by_player.get(int(row.player_id))
                or (team_conference_map or {}).get(f"slug:{row.team_slug}")
                or (team_conference_map or {}).get(f"name:{str(row.team_name or '').lower()}")
                or None
            ),
        )
        for row in board_rows
    ]
    has_market_data = bool(heisman_snapshot.get("has_market_data"))
    conference_options = sorted(
        {str(row.conference_name).strip() for row in board_rows if row.conference_name},
        key=lambda value: value.lower(),
    )
    team_options = sorted(
        {str(row.team_name).strip() for row in board_rows if row.team_name},
        key=lambda value: value.lower(),
    )
    market_header = "<th>Market</th>" if has_market_data else ""
    table_rows = (
        "".join(_render_heisman_board_row(row, include_market=has_market_data) for row in board_rows)
        if board_rows
        else f'<tr><td colspan="{10 if has_market_data else 9}">Heisman model rows have not been loaded yet for this season.</td></tr>'
    )
    featured_cards = _render_heisman_feature_cards(board_rows)
    tracked_profiles = len(player_directory_rows)
    ranked_profiles = len(board_rows)
    tracked_on_board = sum(1 for row in player_directory_rows if row.get("current_heisman_rank") is not None)
    latest_week = heisman_snapshot.get("week")
    vote_eligible_week = None if latest_week is None else min(int(latest_week), 16)
    market_note = (
        "An external award-market prior is loaded for this snapshot and blended into the forecast with a decaying in-season weight."
        if has_market_data
        else "No external Heisman futures prior is loaded for this snapshot. CFBD currently exposes game betting lines, not award futures."
    )
    vote_note = (
        "Postseason snapshots freeze the Heisman inputs at conference championship week so bowl and playoff games do not rewrite a vote that was already cast."
        if latest_week is not None and int(latest_week) > 16
        else "The probabilities reflect the live vote-eligible data horizon for this week."
    )
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Heisman Tracker | {escape(season_name)}</title>
    {_meta_tags(f"A full-board Heisman model for {season_name}. Nowcast, Forecast, Win, Finalist, and Ballot probabilities for every real contender — including the best non-QB, best G5, and best defensive case.", title=f"Heisman Tracker | {season_name}", image_path="../og-image.svg")}
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="heisman")}
      <section class="hero">
        <p class="eyebrow">Heisman Tracker</p>
        <h1>A full-board Heisman model, not just a top-three list.</h1>
        <p class="lede">
          This page is built to support the stronger interpretation of the award: if every voter had to rank the full FBS universe,
          where would every player land right now, and how much actual win equity does each candidacy have?
        </p>
        <p class="section-note">
          The structure is ready for a world-class nowcast and forecast system: position priors, team-success constraints,
          ballot salience, and official result history all live on the same player record.
        </p>
        <div class="cta-row">
          <a class="button button-primary" href="../players/index.html">Open Player Cards</a>
          <a class="button button-secondary" href="../rankings/index.html">Team Rankings</a>
          <a class="button button-secondary" href="../about-model/index.html">Model Notes</a>
        </div>
      </section>

      <section class="section">
        <div class="home-meta-row panel">
          <div class="meta-pill"><span>Season</span><strong>{escape(season_name)}</strong></div>
          <div class="meta-pill"><span>Latest Heisman week</span><strong>{escape("--" if latest_week is None else f"Week {int(latest_week)}")}</strong></div>
          <div class="meta-pill"><span>Vote-eligible inputs</span><strong>{escape("--" if vote_eligible_week is None else f"Week {vote_eligible_week}")}</strong></div>
          <div class="meta-pill"><span>Ranked players</span><strong>{ranked_profiles:,}</strong></div>
          <div class="meta-pill"><span>Player cards</span><strong>{tracked_profiles:,}</strong></div>
          <div class="meta-pill"><span>Current candidates with pages</span><strong>{tracked_on_board:,}</strong></div>
          <div class="meta-pill"><span>Market prior</span><strong>{escape("Loaded" if has_market_data else "Not loaded")}</strong></div>
        </div>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Fast Read</h2>
              <p class="section-note">A premium awards board should surface the real shape of the race immediately: the favorite, the best non-quarterback, the strongest Group of Five case, and whether any defender is even threatening the historical bias.</p>
            </div>
            <a class="text-link" href="../players/index.html">Browse every player card</a>
          </div>
          <div class="feature-grid scenario-grid">
            {featured_cards}
          </div>
        </article>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Board Controls</h2>
              <p class="section-note">Search the full board by player, team, conference, or position, then flip between raw order and probability views.</p>
            </div>
          </div>
          <p class="section-note">{escape(market_note)}</p>
          <p class="section-note">{escape(vote_note)}</p>
          <div class="board-utility">
            <div class="board-controls">
              <label class="board-control board-control-wide board-search">
                <span>Search Players</span>
                <input id="heismanSearch" type="search" placeholder="Search player, team, conference, or position">
              </label>
              <label class="board-control">
                <span>Team</span>
                <select id="heismanTeamFilter">
                  <option value="ALL">All teams</option>
                  {"".join(f'<option value="{escape(_board_filter_value(team))}">{escape(team)}</option>' for team in team_options)}
                </select>
              </label>
              <label class="board-control">
                <span>Conference</span>
                <select id="heismanConferenceFilter">
                  <option value="ALL">All conferences</option>
                  {"".join(f'<option value="{escape(_board_filter_value(conf))}">{escape(conf)}</option>' for conf in conference_options)}
                </select>
              </label>
              <label class="board-control">
                <span>Position</span>
                <select id="heismanPositionFilter">
                  <option value="ALL">All positions</option>
                  <option value="QB">QB</option>
                  <option value="RB">RB</option>
                  <option value="WR">WR</option>
                  <option value="TE">TE</option>
                  <option value="DEF">Defense</option>
                  <option value="OTHER">Other</option>
                </select>
              </label>
              <label class="board-control">
                <span>Sort</span>
                <select id="heismanSortMode">
                  <option value="rank">Current rank</option>
                  <option value="win">Win probability</option>
                  <option value="finalist">Finalist probability</option>
                  <option value="ballot">Ballot share</option>
                  <option value="player">Player A-Z</option>
                </select>
              </label>
            </div>
              <div class="board-toolbar">
                <div class="jump-group" role="group" aria-label="Quick Heisman range">
                  <button type="button" class="jump-chip" data-heisman-limit="10">Top 10</button>
                  <button type="button" class="jump-chip" data-heisman-limit="25">Top 25</button>
                  <button type="button" class="jump-chip" data-heisman-limit="100">Top 100</button>
                <button type="button" class="jump-chip is-active" data-heisman-limit="all">All players</button>
              </div>
              <div class="board-status">
                <strong id="heismanVisibleCount">{len(board_rows)}</strong>
                <span>players visible</span>
                </div>
                <button type="button" class="clear-filters" id="clearHeismanFilters">Clear filters</button>
              </div>
              <div class="active-filter-row" id="heismanActiveFilterRow" hidden></div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Player</th>
                  <th>Team</th>
                  <th>Pos</th>
                  <th>Nowcast</th>
                  <th>Forecast</th>
                  {market_header}
                  <th>Win</th>
                  <th>Finalist</th>
                  <th>Ballot</th>
                </tr>
              </thead>
              <tbody id="heismanBoardBody">
                {table_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </main>
    <script>{_heisman_board_script()}</script>
  </body>
</html>
"""


def render_players_index_html(
    summary: dict[str, Any],
    player_directory_rows: list[dict[str, Any]],
    heisman_snapshot: dict[str, Any],
) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    current_ranked = sum(1 for row in player_directory_rows if row.get("current_heisman_rank") is not None)
    table_rows = (
        "".join(_render_player_directory_row(row) for row in player_directory_rows)
        if player_directory_rows
        else '<tr><td colspan="8">Player cards will populate after roster or Heisman data is loaded.</td></tr>'
    )
    latest_week = heisman_snapshot.get("week")
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Player Cards | {escape(season_name)}</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="players")}
      <section class="hero">
        <p class="eyebrow">Players</p>
        <h1>Every serious award model needs durable player pages.</h1>
        <p class="lede">
          These player cards are the foundation for a much deeper product: Heisman history by season, team context, role identity,
          and room for future production, efficiency, recruiting, transfer, draft, and awards modules.
        </p>
      </section>

      <section class="section">
        <div class="home-meta-row panel">
          <div class="meta-pill"><span>Player cards</span><strong>{len(player_directory_rows):,}</strong></div>
          <div class="meta-pill"><span>Current Heisman ranks</span><strong>{current_ranked:,}</strong></div>
          <div class="meta-pill"><span>Latest Heisman week</span><strong>{escape("--" if latest_week is None else f"Week {int(latest_week)}")}</strong></div>
          <div class="meta-pill"><span>Season</span><strong>{escape(season_name)}</strong></div>
        </div>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Player Directory</h2>
              <p class="section-note">Searchable, sortable player cards let the Heisman page stay focused on the race while each athlete gets a durable home that can grow over time.</p>
            </div>
            <a class="text-link" href="../heisman/index.html">Open Heisman board</a>
          </div>
          <div class="board-utility">
            <div class="board-controls">
              <label class="board-control board-search">
                <span>Search Players</span>
                <input id="playerDirectorySearch" type="search" placeholder="Search player, team, conference, or position">
              </label>
              <label class="board-control">
                <span>Position</span>
                <select id="playerDirectoryPositionFilter">
                  <option value="ALL">All positions</option>
                  <option value="QB">QB</option>
                  <option value="RB">RB</option>
                  <option value="WR">WR</option>
                  <option value="TE">TE</option>
                  <option value="DEF">Defense</option>
                  <option value="OTHER">Other</option>
                </select>
              </label>
              <label class="board-control">
                <span>Sort</span>
                <select id="playerDirectorySort">
                  <option value="current-rank">Current Heisman rank</option>
                  <option value="best-finish">Best official finish</option>
                  <option value="tracked-seasons">Tracked seasons</option>
                  <option value="forecast">Current forecast</option>
                  <option value="player">Player A-Z</option>
                </select>
              </label>
            </div>
            <div class="board-status">
              <span class="status-pill"><strong id="playerDirectoryVisibleCount">{len(player_directory_rows)}</strong> players visible</span>
              <a class="button button-secondary" href="../heisman/index.html">Heisman board</a>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Team</th>
                  <th>Pos</th>
                  <th>Current Heisman</th>
                  <th>Best Finish</th>
                  <th>Tracked Seasons</th>
                  <th>Forecast</th>
                  <th>Card</th>
                </tr>
              </thead>
              <tbody id="playerDirectoryBody">
                {table_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </main>
    <script>{_player_directory_script()}</script>
  </body>
</html>
"""


def _render_algorithmic_signature_card(story: dict[str, Any] | None) -> str:
    """Minimal HTML shell for the algorithmic Signature Story module.

    Figma replaces this in Stage 2 of the player-page redesign. The shell
    here carries the data payload verbatim plus readable fallback copy so
    the page is scannable while the design is in flight.
    """
    if not story or not story.get("has_story"):
        # Shape-accurate skeleton: narrative + confidence label are always present.
        narrative = (
            (story or {}).get("narrative")
            or "He hasn't written his page yet — we'll start filling it in "
               "when there are enough snaps to rank against his peers."
        )
        label = ((story or {}).get("confidence") or {}).get("label") or "No signal"
        return f"""
          <article class="panel algorithmic-signature algorithmic-signature--empty"
                   data-module="algorithmic-signature" data-state="empty">
            <div class="section-head">
              <h3>Signature Story</h3>
              <p class="section-note">An auditable, cohort-ranked read on the one stat that defines this season.</p>
            </div>
            <p class="prose-panel">{escape(narrative)}</p>
            <p class="section-note">Confidence: {escape(label)}.</p>
          </article>
        """

    hs = story.get("headline_stat") or {}
    narrative = str(story.get("narrative") or "")
    confidence = story.get("confidence") or {}
    runners = story.get("runners_up") or []

    def _fmt_val(val: Any, unit: str) -> str:
        try:
            fv = float(val)
        except (TypeError, ValueError):
            return str(val)
        if unit == "pct":
            return f"{fv:.1f}%"
        if unit == "EPA":
            return f"{fv:+.3f}"
        if unit == "QBR":
            return f"{fv:.1f}"
        if unit == "ratio":
            return f"{fv:.1f}"
        if unit == "yds":
            if fv >= 100:
                return f"{fv:,.0f}"
            return f"{fv:.1f}"
        if unit == "rate":
            return f"{fv:.0%}"
        return f"{fv:g}"

    rank = hs.get("rank")
    cohort_size = hs.get("cohort_size")
    rank_line = f"#{rank} of {cohort_size}" if rank and cohort_size else "--"

    runners_html = ""
    if runners:
        items = "".join(
            f"<li><span>{escape(r.get('label') or '')}</span>"
            f"<span>#{r.get('rank')} / {r.get('cohort_size')}</span></li>"
            for r in runners[:3]
        )
        runners_html = f'<ul class="algorithmic-signature__runners">{items}</ul>'

    return f"""
      <article class="panel algorithmic-signature"
               data-module="algorithmic-signature" data-state="ready"
               data-metric-id="{escape(str(hs.get('metric_id') or ''))}"
               data-cohort-id="{escape(str(hs.get('cohort_id') or ''))}">
        <div class="section-head">
          <h3>Signature Story</h3>
          <p class="section-note">{escape(str(story.get('updated_label') or ''))}</p>
        </div>
        <div class="algorithmic-signature__headline">
          <span class="algorithmic-signature__label">{escape(str(hs.get('label') or ''))}</span>
          <strong class="algorithmic-signature__value">{escape(_fmt_val(hs.get('value'), str(hs.get('unit') or '')))}</strong>
          <span class="algorithmic-signature__unit">{escape(str(hs.get('unit') or ''))}</span>
        </div>
        <div class="algorithmic-signature__rank">
          <span>{escape(rank_line)}</span>
          <span class="section-note">{escape(str(hs.get('rank_cohort') or ''))}</span>
        </div>
        <p class="prose-panel algorithmic-signature__narrative">{escape(narrative)}</p>
        <p class="section-note">Confidence: {escape(str(confidence.get('label') or ''))} (sample {int(hs.get('sample_size') or 0)}, cohort {cohort_size or 0}).</p>
        {runners_html}
      </article>
    """


def _render_the_room_card(story: dict[str, Any] | None, player_name: str) -> str:
    """Minimal HTML shell for "The Room on [Player]" — Feature B template slot.

    Same contract as the algorithmic Signature Story card: Figma replaces
    the innards in Stage 2. Empty state matches the team-scope "Awaiting
    Signal" voice so the template is consistent across scopes.
    """
    if not story or not story.get("has_data"):
        return f"""
          <article class="panel the-room the-room--empty"
                   data-module="the-room" data-state="empty">
            <div class="section-head">
              <h3>The Room on {escape(player_name)}</h3>
              <p class="section-note">Fan conversation pulse for this player — across own fans, rivals, national, and media.</p>
            </div>
            <p class="prose-panel">Not enough player-specific chatter yet. We start publishing a pulse once mentions clear sample and author gates.</p>
            <p class="mood-waiting-banner">Awaiting Signal</p>
          </article>
        """

    belief = story.get("belief") or {}
    sample = story.get("sample") or {}
    confidence = story.get("confidence") or {}
    respect_gap = story.get("respect_gap") or {}
    cohesion = story.get("cohesion") or {}
    swing = story.get("swing") or {}
    top_quote = story.get("top_quote") or {}
    archetype = story.get("archetype") or "--"

    quote_block = ""
    if top_quote and top_quote.get("text"):
        url = top_quote.get("source_url") or ""
        attrib = escape(str(top_quote.get("author_pseudonym") or "fan"))
        src = f'<a href="{escape(url)}">{attrib}</a>' if url else attrib
        quote_block = f"""
          <blockquote class="the-room__quote">
            <p>{escape(str(top_quote.get('text') or ''))}</p>
            <cite>— {src}</cite>
          </blockquote>
        """

    def _belief_pct(score: Any) -> str:
        try:
            return f"{float(score):+.2f}"
        except (TypeError, ValueError):
            return "--"

    return f"""
      <article class="panel the-room"
               data-module="the-room" data-state="ready">
        <div class="section-head">
          <h3>The Room on {escape(player_name)}</h3>
          <p class="section-note">{escape(str(story.get('updated_label') or ''))}</p>
        </div>
        <div class="the-room__header">
          <span class="the-room__archetype">{escape(str(archetype))}</span>
          <span class="the-room__belief">Belief {_belief_pct(belief.get('score'))}</span>
          <span class="the-room__confidence">{escape(str(confidence.get('label') or ''))} ({int(sample.get('mentions') or 0)} mentions · {int(sample.get('authors') or 0)} authors)</span>
        </div>
        <p class="prose-panel">{escape(str(belief.get('narrative') or ''))}</p>
        <ul class="the-room__axes">
          <li><span>Respect Gap</span><span>{escape(str(respect_gap.get('label') or '--'))}</span></li>
          <li><span>Swing</span><span>{escape(str(swing.get('label') or '--'))}</span></li>
          <li><span>Cohesion</span><span>{escape(str(cohesion.get('label') or '--'))}</span></li>
        </ul>
        <ul class="the-room__pills">
          <li>Own fans · {int(sample.get('mentions') or 0)}</li>
          <li>Rivals · {int(sample.get('rival_mentions') or 0)}</li>
          <li>National · {int(sample.get('national_mentions') or 0)}</li>
          <li>Media · {int(sample.get('media_mentions') or 0)}</li>
        </ul>
        {quote_block}
      </article>
    """


def render_player_page_html(summary: dict[str, Any], player_data: dict[str, Any]) -> str:
    player = player_data.get("player") or {}
    primary_team = player_data.get("primary_team") or {}
    current_snapshot = player_data.get("current_snapshot") or {}
    heisman_years = player_data.get("heisman_years") or []
    roster_history = player_data.get("roster_history") or []
    recruiting_profile = player_data.get("recruiting_profile") or {}
    transfer_profile = player_data.get("transfer_profile") or {}
    honors_history = player_data.get("honors_history") or []
    signature_story = player_data.get("signature_story") or {}
    stat_profile = player_data.get("stat_profile") or {}
    season_stat_tables = player_data.get("season_stat_tables") or []
    trophy_case = player_data.get("trophy_case") or []
    modules = player_data.get("modules") or []

    player_name = str(player.get("full_name") or "Player")
    position = str(player.get("position") or primary_team.get("position") or "--")
    class_year = str(player.get("class_year") or primary_team.get("class_year") or "--")
    team_name = str(primary_team.get("team_name") or "Independent file")
    team_slug = primary_team.get("team_slug")
    conference_name = str(primary_team.get("conference_name") or "Team context TBD")
    team_theme = _team_theme(str(team_slug or player.get("player_slug") or "player"))
    team_mark = _team_mark(player_name, slug=team_slug)
    current_rank_text = _display_rank_text(current_snapshot.get("nowcast_rank"))
    forecast_text = _display_rank_text(current_snapshot.get("forecast_rank"))
    best_finish_text = (
        "--"
        if player_data.get("official_best_finish") is None
        else f"#{int(player_data.get('official_best_finish') or 0)}"
    )
    hero_fact_items = [
        class_year if class_year and class_year != "--" else "",
        f"#{player.get('jersey')}" if player.get("jersey") not in (None, "", "--") else "",
        _player_measurement_text(player.get("height_inches"), player.get("weight_lbs")),
        _player_hometown_text(player.get("hometown"), player.get("home_state")),
    ]
    hero_facts = "".join(
        f'<span class="player-hero-fact">{escape(str(item))}</span>'
        for item in hero_fact_items
        if str(item or "").strip() and str(item or "").strip() != "--"
    )
    identity_cards = f"""
      <div class="feature-grid history-snapshot-grid">
        <article class="stat-card"><span>Position</span><strong>{escape(position)}</strong></article>
        <article class="stat-card"><span>Class</span><strong>{escape(class_year)}</strong></article>
        <article class="stat-card"><span>Jersey</span><strong>{escape(str(player.get("jersey") or "--"))}</strong></article>
        <article class="stat-card"><span>Measurements</span><strong>{escape(_player_measurement_text(player.get("height_inches"), player.get("weight_lbs")))}</strong></article>
        <article class="stat-card"><span>Hometown</span><strong>{escape(_player_hometown_text(player.get("hometown"), player.get("home_state")))}</strong></article>
        <article class="stat-card"><span>Primary team</span><strong>{escape(team_name)}</strong></article>
      </div>
    """
    heisman_year_rows = (
        "".join(_render_player_heisman_year_row(row) for row in heisman_years)
        if heisman_years
        else '<tr><td colspan="10">This player does not have Heisman tracking or official result rows loaded yet.</td></tr>'
    )
    roster_rows = (
        "".join(_render_player_roster_history_row(row) for row in roster_history)
        if roster_history
        else '<tr><td colspan="6">Roster history will appear after player-season records are loaded.</td></tr>'
    )
    roadmap_cards = "".join(
        f"""
        <article class="feature-card story-card">
          <span class="feature-rank">{escape(str(card.get("kicker") or ""))}</span>
          <h3>{escape(str(card.get("title") or ""))}</h3>
          <p>{escape(str(card.get("body") or ""))}</p>
        </article>
        """
        for card in modules
    )
    story_support_cards = "".join(
        f"""
        <article class="stat-card">
          <span>{escape(str(card.get("label") or ""))}</span>
          <strong>{escape(str(card.get("value") or "--"))}</strong>
          <span class="submetric">{escape(str(card.get("submetric") or ""))}</span>
        </article>
        """
        for card in (signature_story.get("cards") or [])
    )
    stat_summary_ribbon = "".join(
        f"""
        <article class="player-stat-summary-tile">
          <span>{escape(str(card.get("label") or ""))}</span>
          <strong>{escape(str(card.get("value") or "--"))}</strong>
          <span class="submetric">{escape(str(card.get("submetric") or ""))}</span>
        </article>
        """
        for card in (stat_profile.get("headline_cards") or [])
    )
    stat_advanced_cards = "".join(
        f"""
        <article class="stat-card player-stat-support-card">
          <span>{escape(str(card.get("label") or ""))}</span>
          <strong>{escape(str(card.get("value") or "--"))}</strong>
          <span class="submetric">{escape(str(card.get("submetric") or ""))}</span>
        </article>
        """
        for card in (stat_profile.get("support_cards") or [])
    )
    stat_guide_cards = "".join(
        f"""
        <article class="player-stat-guide-card">
          <span>{escape(str(card.get("label") or ""))}</span>
          <p>{escape(str(card.get("body") or ""))}</p>
        </article>
        """
        for card in (stat_profile.get("metric_guide") or [])
    )
    stat_trust_badges = "".join(
        f'<span class="player-stats-trust-badge">{escape(text)}</span>'
        for text in [
            str(stat_profile.get("snapshot_note") or "Current season snapshot"),
            "Data: CFBD player stats + local Heisman model",
            "Peer context: same position + same level",
        ]
        if str(text or "").strip()
    )
    traditional_sections_html = "".join(
        _render_player_traditional_stat_section(section)
        for section in (stat_profile.get("traditional_sections") or [])
    ) or '<p class="footer-note">Traditional season stats will appear here as soon as the player-season feed has the needed categories.</p>'
    season_stat_tables_html = "".join(
        _render_player_season_stat_table(section)
        for section in season_stat_tables
    ) or '<p class="footer-note">Season-by-season stat tables will appear here as soon as older player stat seasons are loaded into the local database.</p>'
    advanced_rows_html = (
        "".join(
            f"""
            <tr>
              <td>{_render_player_metric_label(str(row.get("metric") or "--"))}</td>
              <td class="metric-cell">{escape(str(row.get("value") or "--"))}</td>
              <td class="metric-cell">{escape(str(row.get("peer") or "--"))}</td>
              <td>{escape(str(row.get("context") or "--"))}</td>
            </tr>
            """
            for row in (stat_profile.get("advanced_rows") or [])
        )
        or '<tr><td colspan="4">Advanced metrics will appear here as soon as the player-season feed has usable context for this role.</td></tr>'
    )
    archetype_tags = "".join(
        f'<span class="player-stat-archetype-tag">{escape(str(tag or ""))}</span>'
        for tag in (stat_profile.get("archetype", {}).get("tags") or [])
    )
    stat_filter_chips = "".join(
        f'<button class="player-stat-filter{" is-active" if str(chip.get("key") or "") == str(stat_profile.get("default_filter") or "all") else ""}" type="button" data-player-stat-filter="{escape(str(chip.get("key") or ""))}">{escape(str(chip.get("label") or ""))}</button>'
        for chip in (stat_profile.get("available_groups") or [])
    )
    stat_explorer_rows = (
        "".join(_render_player_stat_explorer_row(row) for row in (stat_profile.get("explorer_rows") or []))
        or '<tr><td colspan="6">The stat explorer will populate once player-season metrics are loaded for this player.</td></tr>'
    )
    trophy_case_cards = "".join(
        f"""
        <article class="feature-card story-card">
          <span class="feature-rank">{escape(str(card.get("kicker") or ""))}</span>
          <h3>{escape(str(card.get("title") or ""))}</h3>
          <p>{escape(str(card.get("body") or ""))}</p>
        </article>
        """
        for card in trophy_case
    )
    recruiting_cards = "".join(
        f"""
        <article class="stat-card">
          <span>{escape(str(card.get("label") or ""))}</span>
          <strong>{escape(str(card.get("value") or "--"))}</strong>
          <span class="submetric">{escape(str(card.get("submetric") or ""))}</span>
        </article>
        """
        for card in (recruiting_profile.get("cards") or [])
    )
    recruiting_rows = (
        "".join(
            f"""
            <tr>
              <td>{escape(str(row.get("label") or ""))}</td>
              <td class="metric-cell">{escape(str(row.get("value") or "--"))}</td>
              <td>{escape(str(row.get("context") or ""))}</td>
            </tr>
            """
            for row in (recruiting_profile.get("rows") or [])
        )
        or '<tr><td colspan="3">No recruiting profile has been loaded for this player yet.</td></tr>'
    )
    transfer_cards = "".join(
        f"""
        <article class="stat-card">
          <span>{escape(str(card.get("label") or ""))}</span>
          <strong>{escape(str(card.get("value") or "--"))}</strong>
          <span class="submetric">{escape(str(card.get("submetric") or ""))}</span>
        </article>
        """
        for card in (transfer_profile.get("cards") or [])
    )
    transfer_rows = (
        "".join(
            f"""
            <tr>
              <td>{escape(str(row.get("label") or ""))}</td>
              <td class="metric-cell">{escape(str(row.get("value") or "--"))}</td>
              <td>{escape(str(row.get("context") or ""))}</td>
            </tr>
            """
            for row in (transfer_profile.get("rows") or [])
        )
        or '<tr><td colspan="3">No transfer portal movement is loaded for this player.</td></tr>'
    )
    honors_rows = (
        "".join(_render_player_honor_row(row) for row in honors_history)
        if honors_history
        else '<tr><td colspan="5">No honors rows are loaded yet. The card is ready for All-America, all-conference, weekly awards, watch lists, and postseason trophies.</td></tr>'
    )
    current_context = f"""
      <div class="feature-grid history-snapshot-grid">
        <article class="stat-card"><span>Current nowcast</span><strong>{escape(current_rank_text)}</strong><span class="submetric">Latest modeled ballot order</span></article>
        <article class="stat-card"><span>Season forecast</span><strong>{escape(forecast_text)}</strong><span class="submetric">Where the full season sim points</span></article>
        <article class="stat-card"><span>Win probability</span><strong>{escape(_probability_text(current_snapshot.get("win_probability")))}</strong><span class="submetric">Chance to actually win the trophy</span></article>
        <article class="stat-card"><span>Finalist probability</span><strong>{escape(_probability_text(current_snapshot.get("finalist_probability")))}</strong><span class="submetric">Chance to make the finalist tier</span></article>
        <article class="stat-card"><span>Ballot probability</span><strong>{escape(_probability_text(current_snapshot.get("any_ballot_probability")))}</strong><span class="submetric">Chance to appear anywhere on a ballot</span></article>
        <article class="stat-card"><span>Best official finish</span><strong>{escape(best_finish_text)}</strong><span class="submetric">Best completed Heisman placement on file</span></article>
      </div>
    """
    player_subnav = _render_player_page_subnav(
        [
            ("current-heisman-lens", "Overview"),
            ("signature-story", "Story"),
            ("current-season-production", "Stats"),
            ("identity-role", "Bio"),
            ("trophy-case", "Awards"),
            ("heisman-by-year", "History"),
        ]
    )
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(player_name)} Player Card</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="player")}
      <section class="team-shell" style="--team-accent:{team_theme['accent']}; --team-accent-soft:{team_theme['accent_soft']};">
        <div class="team-breadcrumbs">
          <a href="../heisman/index.html">Heisman</a>
          <span>/</span>
          <a href="../players/index.html">Players</a>
          <span>/</span>
          <strong>{escape(player_name)}</strong>
        </div>
        <section class="hero team-hero premium-team-hero">
          <div class="team-hero-top">
            <div>
              <h1>{escape(player_name)}</h1>
              <p class="team-hero-sub">{escape(position)} | {escape(team_name)} | {escape(conference_name)}</p>
              {f'<div class="player-hero-facts">{hero_facts}</div>' if hero_facts else ''}
            </div>
            <div class="team-rank-chip">Player Card</div>
          </div>
          <div class="team-stat-ribbon">
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Current nowcast</span>
                <strong>{escape(current_rank_text)}</strong>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Season forecast</span>
                <strong>{escape(forecast_text)}</strong>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Win probability</span>
                <strong>{escape(_probability_text(current_snapshot.get("win_probability")))}</strong>
              </div>
            </article>
            <article class="team-stat-tile">
              <div class="team-mark">{escape(team_mark)}</div>
              <div>
                <span>Best official finish</span>
                <strong>{escape(best_finish_text)}</strong>
              </div>
            </article>
          </div>
          <div class="team-hero-actions">
            <a class="button button-primary" href="../heisman/index.html">Heisman Board</a>
            <a class="button button-secondary" href="../players/index.html">All Player Cards</a>
            {f'<a class="button button-secondary" href="../teams/{escape(str(team_slug))}.html">{escape(team_name)} team page</a>' if team_slug else ''}
          </div>
        </section>
      </section>

      <section class="section">
        {player_subnav}
      </section>

      <section class="section player-anchor-section" id="current-heisman-lens">
        <article class="panel">
          <div class="section-head">
            <h2>Current Heisman Lens</h2>
            <p class="section-note">Where he sits right now, where the season forecast points, and whether the candidacy is actually trophy-live.</p>
          </div>
          {current_context}
        </article>
      </section>

      <section class="section player-anchor-section" id="the-room">
        {_render_the_room_card(player_data.get("the_room"), player_name)}
      </section>

      <section class="section player-anchor-section" id="signature-story">
        {_render_algorithmic_signature_card(player_data.get("algorithmic_signature"))}
        <article class="panel">
          <div class="section-head">
            <h2>{escape(str(signature_story.get("title") or "What makes this player interesting right now"))}</h2>
            <p class="section-note">The fast read on the thing that makes this player more than a generic stat line.</p>
          </div>
          <div class="prose-panel">
            <p>{escape(str(signature_story.get("body") or "The page will add a signature narrative as more player-level context comes online."))}</p>
          </div>
          <div class="feature-grid history-snapshot-grid">
            {story_support_cards}
          </div>
        </article>
      </section>

      <section class="section player-anchor-section" id="current-season-production">
        <article class="panel">
          <div class="section-head">
            <h2>Current Season Production</h2>
            <p class="section-note">Traditional stats first. Advanced context underneath.</p>
          </div>
          <div class="player-stats-shell">
            <div class="player-stats-topline">
              <div class="player-stats-copy">
                <p class="player-stats-eyebrow">Current stats</p>
                <h3>{escape(_position_filter_bucket(position))} season snapshot</h3>
                <p>{escape(str(stat_profile.get("snapshot_note") or "Current season snapshot"))}</p>
              </div>
            </div>
            <div class="player-stats-trust-strip">
              {stat_trust_badges}
            </div>
            <div class="player-stat-summary-ribbon">
              {stat_summary_ribbon}
            </div>
            <details class="player-stats-drawer player-stats-drawer-open" open>
              <summary>
                <span>Player identity</span>
                <strong>What kind of player is this?</strong>
              </summary>
              <div class="player-stat-archetype-panel">
                <div class="player-stat-archetype-copy">
                  <p class="player-stats-eyebrow">30-second read</p>
                  <h3>What kind of player is this?</h3>
                  <p>{escape(str(stat_profile.get("archetype", {}).get("summary") or ""))}</p>
                </div>
                <div class="player-stat-archetype-tags">
                  {archetype_tags}
                </div>
              </div>
            </details>
          </div>
          <details class="player-stats-drawer player-stats-drawer-open" open>
            <summary>
              <span>Traditional stats</span>
              <strong>Season box score</strong>
            </summary>
            <div class="player-stats-season-ledger">
              <div class="player-stat-module-head">
                <div>
                  <p class="player-stats-eyebrow">Traditional history</p>
                  <h3>Traditional Stats</h3>
                  <p class="section-note">Season rows up top, career context at the bottom.</p>
                </div>
                <div class="player-stat-module-meta">
                  <span class="player-stat-module-chip">Season rows</span>
                  <span class="player-stat-module-chip">Career row</span>
                </div>
              </div>
              {season_stat_tables_html}
            </div>
          </details>
          <details class="player-stats-drawer">
            <summary>
              <span>Advanced layer</span>
              <strong>Usage, value, and context</strong>
            </summary>
            <div class="player-stats-advanced-block">
              <div class="player-stat-module-head">
                <div>
                  <p class="player-stats-eyebrow">Advanced metrics second</p>
                  <h3>Advanced Metrics</h3>
                  <p class="section-note">Usage, value, and opponent-adjusted context.</p>
                </div>
                <div class="player-stat-module-meta">
                  <span class="player-stat-module-chip">Usage</span>
                  <span class="player-stat-module-chip">Value</span>
                  <span class="player-stat-module-chip">Context</span>
                </div>
              </div>
              <div class="player-stat-guide-strip">
                {stat_guide_cards}
              </div>
              <div class="feature-grid history-snapshot-grid player-stat-support-grid">
                {stat_advanced_cards}
              </div>
              <div class="table-wrap compact-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th class="metric-cell">Value</th>
                      <th class="metric-cell">Peer context</th>
                      <th>Why it matters</th>
                    </tr>
                  </thead>
                  <tbody>
                    {advanced_rows_html}
                  </tbody>
                </table>
              </div>
            </div>
          </details>
          <details class="player-stats-explorer">
            <summary>Open full stat explorer</summary>
            <div class="player-stats-toolbar">
              <div class="player-stats-filter-row">
                {stat_filter_chips}
              </div>
              <div class="player-stats-sort-row">
                <label for="playerStatsSearch">Find metric</label>
                <input id="playerStatsSearch" type="search" placeholder="Search yards, TD, usage, sacks..." />
                <label for="playerStatsSort">Sort</label>
                <select id="playerStatsSort">
                  <option value="priority">Role relevance</option>
                  <option value="value-desc">Highest value</option>
                  <option value="value-asc">Lowest value</option>
                  <option value="metric">Metric A-Z</option>
                  <option value="group">Group</option>
                </select>
                <span class="player-stats-visible"><strong id="playerStatsVisibleCount">0</strong> metrics visible</span>
                <span class="player-stats-visible" id="playerStatsStateText">Showing all metrics</span>
              </div>
            </div>
            <div class="table-wrap compact-table-wrap">
              <table id="playerStatsExplorerTable">
                <thead>
                  <tr>
                    <th data-player-stat-sort-trigger="group">Group</th>
                    <th data-player-stat-sort-trigger="metric">Metric</th>
                    <th class="metric-cell" data-player-stat-sort-trigger="value-desc">Value</th>
                    <th class="metric-cell">Rank</th>
                    <th class="metric-cell">Pct</th>
                    <th>Why it matters</th>
                  </tr>
                </thead>
                <tbody id="playerStatsExplorerBody">
                  {stat_explorer_rows}
                </tbody>
              </table>
            </div>
          </details>
          {_player_stats_script()}
          {_player_page_nav_script()}
        </article>
      </section>

      <section class="section player-anchor-section" id="identity-role">
        <article class="panel">
          <div class="section-head">
            <h2>Identity & Role</h2>
            <p class="section-note">The durable bio layer: position, size, hometown, and roster role.</p>
          </div>
          {identity_cards}
        </article>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <h2>Recruiting Pedigree</h2>
            <p class="section-note">How big the prospect was before college, and whether the later career arc beat that expectation.</p>
          </div>
          <div class="feature-grid history-snapshot-grid">
            {recruiting_cards}
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Profile</th>
                  <th>Context</th>
                </tr>
              </thead>
              <tbody>
                {recruiting_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <h2>Transfer Arc</h2>
            <p class="section-note">Portal movement changes role, context, and perception. This keeps that path in one place.</p>
          </div>
          <div class="feature-grid history-snapshot-grid">
            {transfer_cards}
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Move</th>
                  <th>Context</th>
                </tr>
              </thead>
              <tbody>
                {transfer_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section player-anchor-section" id="trophy-case">
        <article class="panel">
          <div class="section-head">
            <h2>Trophy Case</h2>
            <p class="section-note">Major honors at a glance, with Heisman results and selector-grade awards in the same place.</p>
          </div>
          <div class="feature-grid team-story-grid">
            {trophy_case_cards}
          </div>
        </article>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <h2>Honors Timeline</h2>
            <p class="section-note">Season-end distinction and week-by-week recognition on one timeline.</p>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Honor</th>
                  <th>Scope</th>
                  <th>Team / Selector</th>
                  <th>Context</th>
                </tr>
              </thead>
              <tbody>
                {honors_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section player-anchor-section" id="heisman-by-year">
        <article class="panel">
          <div class="section-head">
            <h2>Heisman By Year</h2>
            <p class="section-note">Modeled rank and official finish by season.</p>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Team</th>
                  <th>Role</th>
                  <th>Latest Model</th>
                  <th>Forecast</th>
                  <th>Win</th>
                  <th>Finalist</th>
                  <th>Official Finish</th>
                  <th>Points</th>
                  <th>Context</th>
                </tr>
              </thead>
              <tbody>
                {heisman_year_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="section">
        <article class="panel">
          <div class="section-head">
            <h2>Roster Timeline</h2>
            <p class="section-note">Team, conference, and class by season.</p>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Team</th>
                  <th>Conference</th>
                  <th>Pos</th>
                  <th>Class</th>
                  <th>Bio</th>
                </tr>
              </thead>
              <tbody>
                {roster_rows}
              </tbody>
            </table>
          </div>
        </article>
      </section>

    </main>
  </body>
</html>
"""


def _render_history_level_cards(history_hub: dict[str, Any], prefix: str = "teams/") -> str:
    cards = history_hub.get("level_cards") or []
    if not cards:
        return '<p class="footer-note">Level-specific historical peaks will appear after more seasons are modeled.</p>'
    rendered: list[str] = []
    for card in cards:
        slug_str = str(card.get("slug") or "").strip()
        title_html = escape(str(card.get("title") or ""))
        if slug_str:
            body_open = f'<a class="feature-card story-card" href="{prefix}{escape(slug_str)}.html">'
            body_close = "</a>"
        else:
            body_open = '<div class="feature-card story-card">'
            body_close = "</div>"
        rendered.append(
            f"""
            {body_open}
              <span class="feature-rank">{escape(str(card.get("level_code") or ""))}</span>
              <h3>{title_html}</h3>
              <p>{escape(str(card.get("body") or ""))}</p>
              <p class="story-tail">{escape(str(card.get("detail") or ""))}</p>
            {body_close}
            """
        )
    return "".join(rendered)


def _render_history_team_season_rows(rows: list[dict[str, Any]], prefix: str = "../teams/") -> str:
    if not rows:
        return '<tr><td colspan="6">Historical season rows will populate after more seasons are modeled.</td></tr>'
    rendered: list[str] = []
    for row in rows[:12]:
        conference = _clean_conference_name(str(row.get("conference_name") or f"{row.get('level_code') or ''} Independents"))
        team_link = _program_link_or_text(prefix, row.get("slug"), escape(str(row.get("team_name") or "")))
        rendered.append(
            f"""
            <tr>
              <td>{int(row.get("season_year") or 0)}</td>
              <td>{team_link}<span class="submetric">{escape(str(row.get("level_code") or ""))} | {escape(conference)}</span></td>
              <td class="metric-cell">{int(row.get("wins") or 0)}-{int(row.get("losses") or 0)}</td>
              <td class="metric-cell">#{escape(_display_rank_value(row.get("final_rank")))}</td>
              <td class="metric-cell">{escape(_public_power_text(row.get("end_power_display")))}</td>
              <td class="metric-cell">{escape(_public_resume_text(row.get("end_resume_display")))}</td>
            </tr>
            """
        )
    return "".join(rendered)


def _render_history_explorer_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<tr><td colspan="9">Historical explorer rows will populate after more seasons are modeled.</td></tr>'
    rendered: list[str] = []
    for row in rows:
        search_blob = " ".join(
            [
                str(row.get("team_name") or ""),
                str(row.get("conference_name") or ""),
                str(row.get("level_code") or ""),
                str(row.get("season_year") or ""),
                str(row.get("lens_label") or ""),
            ]
        ).lower()
        team_name = escape(str(row.get("team_name") or ""))
        program_url = row.get("program_url")
        season_url = row.get("season_url")
        power_value = row.get("end_power")
        resume_value = row.get("end_resume")
        rank_value = row.get("final_rank")
        power_attr = "" if power_value is None else f"{float(power_value):.4f}"
        resume_attr = "" if resume_value is None else f"{float(resume_value):.4f}"
        rank_attr = "" if rank_value is None else str(int(rank_value))
        team_cell = (
            f'<a class="team-link" href="{escape(str(program_url))}">{team_name}</a>'
            if program_url
            else team_name
        )
        open_cell = (
            f'<a class="text-link" href="{escape(str(season_url))}">Season page</a>'
            if season_url
            else (
                f'<a class="text-link" href="{escape(str(program_url))}">Program page</a>'
                if program_url
                else '<span class="submetric">No page</span>'
            )
        )
        final_rank = row.get("final_rank")
        rendered.append(
            f"""
            <tr
              class="history-explorer-row"
              data-search="{escape(search_blob)}"
              data-team="{escape(str(row.get('team_name') or '').lower())}"
              data-level="{escape(str(row.get('level_code') or ''))}"
              data-conference="{escape(str(row.get('conference_name') or ''))}"
              data-season="{int(row.get('season_year') or 0)}"
              data-power="{power_attr}"
              data-resume="{resume_attr}"
              data-rank="{rank_attr}"
              data-winpct="{float(row.get('win_pct') or 0.0):.6f}"
              data-margin="{int(row.get('margin') or 0)}"
            >
              <td>{int(row.get("season_year") or 0)}</td>
              <td>{team_cell}<span class="submetric">{escape(str(row.get("level_code") or ""))} | {escape(str(row.get("conference_name") or ""))}</span></td>
              <td>{escape(str(row.get("lens_label") or ""))}<span class="submetric">{escape(str(row.get("lens_body") or ""))}</span></td>
              <td class="metric-cell">{escape(str(row.get("record") or "--"))}</td>
              <td class="metric-cell">#{escape(_display_rank_value(final_rank))}</td>
              <td class="metric-cell">{escape(_public_power_text(row.get("end_power")))}</td>
              <td class="metric-cell">{escape(_public_resume_text(row.get("end_resume")))}</td>
              <td class="metric-cell">{int(row.get("margin") or 0):+d}</td>
              <td>{open_cell}</td>
            </tr>
            """
        )
    return "".join(rendered)


def _render_history_program_rows(rows: list[dict[str, Any]], prefix: str = "../teams/", mode: str = "turnaround") -> str:
    if not rows:
        return '<tr><td colspan="4">Program trend rows will populate after more seasons are modeled.</td></tr>'
    rendered: list[str] = []
    for row in rows[:10]:
        team_link = _program_link_or_text(prefix, row.get("slug"), escape(str(row.get("team_name") or "")))
        if mode == "turnaround":
            detail = f"{int(row.get('season_year') or 0)}"
            value = _public_power_text(row.get("power_delta"))
            tail = _history_record_line(row)
        elif mode == "collapse":
            detail = f"{int(row.get('season_year') or 0)}"
            value = _public_power_text(row.get("power_delta"))
            tail = _history_record_line(row)
        elif mode == "sustained":
            detail = f"{int(row.get('season_count') or 0)} seasons"
            value = _public_power_text(row.get("average_end_power"))
            tail = f"{int(row.get('season_year') or 0)} latest | {_history_record_line(row)}"
        elif mode == "closest":
            detail = f"{int(row.get('season_year') or 0)}"
            value = "--" if row.get("gap_to_peak") is None else f"{float(row.get('gap_to_peak') or 0.0):.1f}"
            tail = (
                f"Peak {int(row.get('peak_season_year') or 0)} | "
                f"{_public_power_text(row.get('vs_baseline'))} vs baseline"
            )
        elif mode == "run":
            detail = f"{int(row.get('window_start') or 0)}-{int(row.get('window_end') or 0)}"
            value = _public_power_text(row.get("average_end_power"))
            tail = (
                f"{int(row.get('combined_wins') or 0)}-{int(row.get('combined_losses') or 0)} combined | "
                f"Resume {_public_resume_text(row.get('average_end_resume'))} / 100"
            )
        else:
            detail = f"{int(row.get('season_count') or 0)} seasons"
            value = "--" if row.get("power_range") is None else f"{float(row.get('power_range') or 0.0):.1f}"
            tail = f"{int(row.get('season_year') or 0)} latest | {_history_record_line(row)}"
        rendered.append(
            f"""
            <tr>
              <td>{team_link}<span class="submetric">{escape(str(row.get("level_code") or ""))}</span></td>
              <td class="metric-cell">{escape(detail)}</td>
              <td class="metric-cell">{escape(value)}</td>
              <td>{escape(tail)}</td>
            </tr>
            """
        )
    return "".join(rendered)


def _render_history_season_summary_cards(history_hub: dict[str, Any], prefix: str = "../teams/") -> str:
    season_summaries = history_hub.get("season_summaries") or []
    if not season_summaries:
        return '<p class="footer-note">Season digest cards will appear after more years are loaded.</p>'
    rendered: list[str] = []
    for summary in season_summaries[:8]:
        top_resume = summary.get("top_resume")
        top_power = summary.get("top_power")
        best_record = summary.get("best_record")
        top_resume_text = (
            f"Best resume: {top_resume['team_name']} ({_public_resume_text(top_resume.get('end_resume_display'))} / 100)"
            if top_resume
            else "Best resume still loading"
        )
        top_power_text = (
            f"Strongest team: {top_power['team_name']} ({_public_power_text(top_power.get('end_power_display'))})"
            if top_power
            else "Power leader still loading"
        )
        best_record_text = (
            f"Best record: {best_record['team_name']} {int(best_record.get('wins') or 0)}-{int(best_record.get('losses') or 0)}"
            if best_record
            else "Best record still loading"
        )
        anchor_slug = ""
        if top_resume:
            anchor_slug = str(top_resume.get("slug") or "")
        elif top_power:
            anchor_slug = str(top_power.get("slug") or "")
        anchor_slug = anchor_slug.strip()
        if anchor_slug:
            card_open = f'<a class="feature-card archive-card" href="{prefix}{escape(anchor_slug)}.html">'
            card_close = "</a>"
        else:
            card_open = '<div class="feature-card archive-card">'
            card_close = "</div>"
        rendered.append(
            f"""
            {card_open}
              <span class="feature-rank">{escape(season_label(int(summary.get("season_year") or 0)))}</span>
              <h3>{int(summary.get("team_count") or 0)} modeled teams</h3>
              <p>{escape(top_resume_text)}</p>
              <p>{escape(top_power_text)}</p>
              <p class="story-tail">{escape(best_record_text)}</p>
            {card_close}
            """
        )
    return "".join(rendered)


def _render_preseason_playbook_cards() -> str:
    cards = [
        (
            "Previous Close",
            "The last version of a team matters",
            "Best public systems do not reset everyone to zero. The previous season's closing power is still the single most important starting clue.",
        ),
        (
            "Program Baseline",
            "One season should not erase the whole arc",
            "Recent multi-year strength helps separate a real rise from a one-year spike and keeps preseason boards from overreacting to noise.",
        ),
        (
            "Returning Production",
            "Continuity keeps ratings sticky",
            "Returning snaps, quarterback continuity, and experienced units help explain why some teams deserve to hold more of last year's strength into August.",
        ),
        (
            "Talent And Recruiting",
            "Roster ceiling matters before the games do",
            "Recruiting and talent data keep the model from treating a roster reload like a total rebuild when the underlying player quality is still elite.",
        ),
        (
            "Roster Carryover",
            "Portal-era change should be visible",
            "Where roster continuity data exists, the prior should move with it. Teams that kept real structure deserve more inertia than teams starting over.",
        ),
    ]
    rendered: list[str] = []
    for kicker, title, body in cards:
        rendered.append(
            f"""
            <article class="feature-card story-card">
              <span class="feature-rank">{escape(kicker)}</span>
              <h3>{escape(title)}</h3>
              <p>{escape(body)}</p>
            </article>
            """
        )
    return "".join(rendered)


def _render_team_peer_section(team_data: dict[str, Any], peer_context: dict[str, Any]) -> str:
    ranking: RankingRow = team_data["ranking"]
    level_code = _team_display_level_code(team_data)
    conference_name = _team_display_conference_name(team_data)
    level_info = peer_context.get("level") or {}
    conference_info = peer_context.get("conference") or {}
    cross_level_peer = peer_context.get("cross_level_peer")
    neighbor_cards = "".join(
        card
        for card in [
            _render_peer_item("Overall Ahead", peer_context.get("overall_ahead")),
            _render_peer_item("Overall Behind", peer_context.get("overall_behind")),
            _render_peer_item(f"{level_code} Ahead", level_info.get("ahead")),
            _render_peer_item(f"{conference_name} Ahead", conference_info.get("ahead")),
            _render_peer_item("Cross-Level Neighbor", cross_level_peer),
        ]
        if card
    )
    if not neighbor_cards:
        neighbor_cards = '<p class="peer-context-note">Peer cards will populate as more ranked teams and connected schedule data are available.</p>'
    compare_shortcuts = _render_team_compare_shortcuts(
        ranking.slug,
        [
            ("Overall Neighbor", peer_context.get("overall_behind") or peer_context.get("overall_ahead")),
            (f"{level_code} Peer", level_info.get("ahead") or level_info.get("behind")),
            ("Conference Peer", conference_info.get("ahead") or conference_info.get("behind")),
            ("Cross-Level Compare", cross_level_peer),
        ],
    )
    cross_level_peer_name = str(cross_level_peer.get("team_name")) if cross_level_peer else "None yet"
    return f"""
      <section class="section two-up">
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Placement Context</h2>
              <p class="section-note">This is where the team sits inside the all-level board, its own subdivision, and its own conference ecosystem.</p>
            </div>
          </div>
          <div class="stat-grid">
            <div class="stat-card"><span>Overall Board</span><strong>#{ranking.rank}</strong></div>
            <div class="stat-card"><span>Inside {escape(level_code)}</span><strong>#{int(level_info.get("rank") or 1)} of {int(level_info.get("total") or 1)}</strong></div>
            <div class="stat-card"><span>Inside {escape(conference_name)}</span><strong>#{int(conference_info.get("rank") or 1)} of {int(conference_info.get("total") or 1)}</strong></div>
            <div class="stat-card"><span>Power</span><strong>{_public_power_text(ranking.power_display)}</strong><span class="submetric">pts vs avg NCAA team</span></div>
            <div class="stat-card"><span>Resume</span><strong>{_public_resume_text(ranking.resume_display)}</strong><span class="submetric">{_public_resume_percentile_label(ranking.resume_display)}</span></div>
            <div class="stat-card"><span>Cross-Level Neighbor</span><strong>{escape(cross_level_peer_name)}</strong></div>
          </div>
          <p class="peer-context-note">Use these shortcuts to jump from this team to the neighbors that best explain its place on the board, including the closest cross-level comparison.</p>
          {compare_shortcuts}
        </article>
        <article class="panel">
          <div class="section-head">
            <div>
              <h2>Closest Neighbors</h2>
              <p class="section-note">The quickest way to explain a ranking is often to show the teams immediately around it.</p>
            </div>
          </div>
          <div class="peer-list">
            {neighbor_cards}
          </div>
        </article>
      </section>
    """


def _render_team_compare_shortcuts(current_slug: str, peers: list[tuple[str, dict[str, Any] | None]], prefix: str = "../") -> str:
    seen: set[str] = set()
    links: list[str] = []
    for label, peer in peers:
        if not peer:
            continue
        peer_slug = str(peer.get("slug") or "")
        if not peer_slug or peer_slug == current_slug or peer_slug in seen:
            continue
        seen.add(peer_slug)
        links.append(
            f'<a class="compare-shortcut" href="{escape(_compare_href(prefix, current_slug, peer_slug))}">{escape(label)}: {escape(str(peer.get("team_name") or peer_slug))}</a>'
        )
    if not links:
        return ""
    return f'<div class="compare-shortcuts">{"".join(links)}</div>'


def _render_peer_item(label: str, peer: dict[str, Any] | None) -> str:
    if not peer:
        return ""
    return f"""
      <a class="peer-item" href="../teams/{escape(str(peer['slug']))}.html">
        <div class="peer-item-top">
          <span class="peer-kicker">{escape(label)}</span>
          <span class="peer-gap-line">Power {escape(_public_power_text(peer.get('power_gap')))} | Resume {escape(_signed_integer_text(peer.get('resume_gap')))}</span>
        </div>
        <strong>#{int(peer['rank'])} {escape(str(peer['team_name']))}</strong>
        <span class="submetric">{escape(str(peer['level_code']))} | {escape(str(peer['conference']))}</span>
      </a>
    """


def _render_team_story_cards(
    ranking: RankingRow,
    best_result: str,
    worst_result: str,
    recent_form: str,
    efficiency_note: str,
    phase_summary: list[dict[str, Any]],
    season_year_value: int,
) -> str:
    alignment_gap = float(ranking.power_percentile or 0.0) - float(ranking.resume_percentile or 0.0)
    phase_note = _phase_summary_note(phase_summary)
    cards = [
        (
            "Predictive Case",
            f"Power {_public_power_text(ranking.power_display)}",
            f"Currently {_public_power_text(ranking.power_display)} versus the all-level average team on a neutral field. {efficiency_note}",
        ),
        (
            "Resume Case",
            f"Resume {_public_resume_text(ranking.resume_display)}",
            f"Body of work: best signal {best_result}. Stress point {worst_result}. {_public_resume_percentile_label(ranking.resume_display)}.",
        ),
        (
            "Recent Form",
            recent_form,
            f"The latest four checkpoints read {recent_form}. {_power_resume_gap_note(ranking.power_percentile, ranking.resume_percentile)}",
        ),
        (
            "Season Identity",
            f"{season_year_value} Season",
            f"{phase_note} Even if a bowl or playoff game lands in early {season_year_value + 1}, it still belongs to this season page.",
        ),
    ]
    rendered = []
    for kicker, title, body in cards:
        rendered.append(
            f"""
            <article class="feature-card story-card">
              <span class="feature-rank">{escape(kicker)}</span>
              <h3>{escape(title)}</h3>
              <p>{escape(body)}</p>
              <p class="story-tail">Open the compare board or matchup studio to pressure-test this profile against the teams around it.</p>
            </article>
            """
        )
    return "".join(rendered)


def _render_phase_pills(phase_summary: list[dict[str, Any]]) -> str:
    if not phase_summary:
        return '<span class="mini-chip">Regular season data pending</span>'
    pills = []
    for row in phase_summary:
        phase = _phase_display_label(row.get("season_phase"))
        wins = int(row.get("wins") or 0)
        losses = int(row.get("losses") or 0)
        games = int(row.get("games_played") or 0)
        pills.append(
            f'<span class="mini-chip phase-summary-chip">{escape(phase)} {wins}-{losses} in {games} game{"s" if games != 1 else ""}</span>'
        )
    return "".join(pills)


def _render_game_impact_cards(team_id: int, schedule: list[dict[str, Any]]) -> str:
    if not schedule:
        return '<p class="footer-note">Schedule detail will populate after the next game sync.</p>'
    return "".join(_render_game_impact_card(team_id, row) for row in reversed(schedule))


def _render_game_impact_table(team_id: int, schedule: list[dict[str, Any]], limit: int = 8) -> str:
    completed = [row for row in schedule if row.get("home_points") is not None and row.get("away_points") is not None]
    if not completed:
        return '<p class="footer-note">Completed game impact rows will appear after the next results sync.</p>'
    rows = "".join(_render_game_impact_table_row(team_id, row) for row in list(reversed(completed))[:limit])
    return f"""
    <div class="table-wrap compact-table-wrap game-impact-table-wrap">
      <table class="game-impact-table">
        <thead>
          <tr>
            <th>Key Result</th>
            <th>Pregame</th>
            <th>Actual</th>
            <th>Delta</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
    """


def _render_game_impact_table_row(team_id: int, row: dict[str, Any]) -> str:
    is_home = int(row["home_team_id"]) == team_id
    opponent_name = str(row["away_team_name"] if is_home else row["home_team_name"])
    opponent_slug = str(row["away_slug"] if is_home else row["home_slug"])
    location = "vs" if is_home else "@"
    team_points = int(row["home_points"] if is_home else row["away_points"])
    opp_points = int(row["away_points"] if is_home else row["home_points"])
    power_delta_value = float(row.get("power_delta") or 0.0)
    delta_class = "up" if power_delta_value > 0 else "down" if power_delta_value < 0 else "flat"
    return f"""
    <tr>
      <td><span class="game-prefix">{location}</span> {_team_link("../teams/", opponent_slug, opponent_name)}</td>
      <td class="metric-cell">{escape(_metric_text(row.get("pregame_power")))}</td>
      <td class="metric-cell">{team_points}-{opp_points}</td>
      <td class="metric-cell"><span class="rank-delta {delta_class}">{escape(_signed_metric_text(power_delta_value))}</span></td>
    </tr>
    """


def _render_game_impact_card(team_id: int, row: dict[str, Any]) -> str:
    is_home = int(row["home_team_id"]) == team_id
    opponent_name = str(row["away_team_name"] if is_home else row["home_team_name"])
    opponent_slug = str(row["away_slug"] if is_home else row["home_slug"])
    location = "vs" if is_home else "@"
    team_points = row["home_points"] if is_home else row["away_points"]
    opp_points = row["away_points"] if is_home else row["home_points"]
    if team_points is None or opp_points is None:
        result_label = "Scheduled"
        result_detail = f"{location} {opponent_name}"
        tone = "impact-pending"
    else:
        if int(team_points) > int(opp_points):
            result_label = "Win"
            tone = "impact-up"
        elif int(team_points) < int(opp_points):
            result_label = "Loss"
            tone = "impact-down"
        else:
            result_label = "Tie"
            tone = "impact-flat"
        result_detail = f"{location} {opponent_name} {team_points}-{opp_points}"
    phase = _phase_display_label(row.get("season_phase"))
    game_date = _format_game_date(row.get("start_time_utc"))
    week_label = f"Week {int(row.get('week') or 0)}"
    power_delta = _signed_metric_text(row.get("power_delta"))
    resume_delta = _signed_metric_text(row.get("resume_delta"))
    pregame = _metric_text(row.get("pregame_power"))
    postgame = _metric_text(row.get("postgame_power"))
    return f"""
    <article class="impact-card {tone}">
      <div class="impact-card-top">
        <span class="impact-week">{escape(week_label)}</span>
        <span class="mini-chip phase-summary-chip">{escape(phase)}</span>
      </div>
      <h3><span class="game-prefix">{location}</span> {_team_link("", opponent_slug, opponent_name)}</h3>
      <p class="impact-meta">{escape(game_date)} | {escape(str(row.get("opponent_level_code") or "Opponent"))} opponent | {escape(result_detail)}</p>
      <div class="impact-stat-grid">
        <div class="impact-stat">
          <span>Result</span>
          <strong>{escape(result_label)}</strong>
        </div>
        <div class="impact-stat">
          <span>Pregame</span>
          <strong>{escape(pregame)}</strong>
        </div>
        <div class="impact-stat">
          <span>Power</span>
          <strong>{escape(power_delta)}</strong>
        </div>
        <div class="impact-stat">
          <span>Resume</span>
          <strong>{escape(resume_delta)}</strong>
        </div>
        <div class="impact-stat impact-stat-wide">
          <span>Postgame</span>
          <strong>{escape(postgame)}</strong>
        </div>
      </div>
    </article>
    """


def _render_historical_dna(team_name: str, similarity_cards: list[dict[str, Any]]) -> str:
    return f"""
    <div class="historical-dna">
      <div class="historical-dna-summary">
        <span class="feature-rank">Historical DNA</span>
        <h3>{escape(team_name)}</h3>
        <p class="section-note">The closest historical echoes across offense, defense, and overall profile.</p>
      </div>
      <div class="historical-dna-grid">
        {_render_reminiscence_cards(similarity_cards)}
      </div>
    </div>
    """


def _render_history_chart(history: list[dict[str, Any]]) -> str:
    if not history:
        return '<p class="footer-note">Program history will appear after more seasons are loaded.</p>'
    rows = sorted(history, key=lambda row: int(row.get("season_year") or 0))[-10:]
    width = max(560, len(rows) * 88)
    height = 260
    padding_left = 36
    padding_right = 32
    top_padding = 26
    baseline = height - 38
    chart_height = baseline - top_padding
    slot_width = (width - padding_left - padding_right) / max(1, len(rows))
    bars = []
    labels = []
    power_values = [
        float(_first_present_float(row.get("end_power_display"), row.get("end_power")) or 0.0)
        for row in rows
        if _first_present_float(row.get("end_power_display"), row.get("end_power")) is not None
    ]
    power_path: list[str] = []
    power_dots: list[str] = []
    power_min = min(power_values) if power_values else 0.0
    power_max = max(power_values) if power_values else 1.0
    if math.isclose(power_min, power_max):
        power_min -= 1.0
        power_max += 1.0
    for index, row in enumerate(rows):
        wins = int(row.get("wins") or 0)
        losses = int(row.get("losses") or 0)
        games = max(1, int(row.get("games_played") or 0))
        win_pct = wins / games
        bar_height = max(10.0, win_pct * chart_height)
        x = padding_left + index * slot_width + slot_width * 0.18
        y = baseline - bar_height
        bar_width = slot_width * 0.64
        center_x = x + bar_width / 2
        season = str(row.get("season_year") or "")
        tooltip = (
            f"{season}: {wins}-{losses}, margin {int(row.get('margin') or 0):+d}, "
            f"power {_public_power_text(row.get('end_power_display'))}, "
            f"resume {_public_resume_text(row.get('end_resume_display'))} / 100, "
            f"final rank #{_display_rank_value(row.get('final_rank'))}"
        )
        labels.append(f'<text x="{center_x:.1f}" y="{baseline + 18:.1f}" text-anchor="middle" font-size="11" font-family="Arial" fill="#625b52">{escape(season)}</text>')
        labels.append(f'<text x="{center_x:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="11" font-family="Arial" fill="#111111">{wins}-{losses}</text>')
        bars.append(
            f'<g><title>{escape(tooltip)}</title><rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="10" fill="url(#historyGradient)"></rect></g>'
        )
        power_value = _first_present_float(row.get("end_power_display"), row.get("end_power"))
        if power_value is not None:
            power_y = baseline - ((power_value - power_min) / max(0.001, power_max - power_min)) * chart_height
            power_path.append(f"{center_x:.1f},{power_y:.1f}")
            power_dots.append(
                f'<g><title>{escape(tooltip)}</title><circle cx="{center_x:.1f}" cy="{power_y:.1f}" r="4.5" fill="#0f2742" stroke="white" stroke-width="2"></circle></g>'
            )
            power_dots.append(
                f'<text x="{center_x:.1f}" y="{power_y - 10:.1f}" text-anchor="middle" font-size="10" font-family="Arial" fill="#0f2742">{escape(_public_power_text(power_value))}</text>'
            )
    power_polyline = (
        f'<polyline fill="none" stroke="#0f2742" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(power_path)}"></polyline>'
        if len(power_path) >= 2
        else ""
    )
    return f"""
    <div class="history-chart-wrap">
      <div class="phase-pill-row">
        <span class="mini-chip">Bars: win rate</span>
        <span class="mini-chip">Line: public power vs average team</span>
      </div>
      <svg class="history-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Program history chart">
        <defs>
          <linearGradient id="historyGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="#8f2330"></stop>
            <stop offset="100%" stop-color="#d48678"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="{width}" height="{height}" rx="24" fill="rgba(255,255,255,0.45)"></rect>
        <line x1="{padding_left}" y1="{baseline}" x2="{width - padding_right}" y2="{baseline}" stroke="rgba(17,17,17,0.18)"></line>
        <line x1="{padding_left}" y1="{baseline - chart_height / 2:.1f}" x2="{width - padding_right}" y2="{baseline - chart_height / 2:.1f}" stroke="rgba(17,17,17,0.10)" stroke-dasharray="3 4"></line>
        <line x1="{padding_left}" y1="{top_padding:.1f}" x2="{width - padding_right}" y2="{top_padding:.1f}" stroke="rgba(17,17,17,0.07)" stroke-dasharray="3 4"></line>
        <text x="8" y="{top_padding + 4:.1f}" font-size="11" font-family="Arial" fill="#625b52">100%</text>
        <text x="10" y="{baseline - chart_height / 2 + 4:.1f}" font-size="11" font-family="Arial" fill="#625b52">50%</text>
        <text x="16" y="{baseline + 4:.1f}" font-size="11" font-family="Arial" fill="#625b52">0%</text>
        <text x="{width - 24}" y="{top_padding + 4:.1f}" text-anchor="end" font-size="11" font-family="Arial" fill="#0f2742">PWR {escape(_public_power_text(power_max))}</text>
        <text x="{width - 24}" y="{baseline + 4:.1f}" text-anchor="end" font-size="11" font-family="Arial" fill="#0f2742">PWR {escape(_public_power_text(power_min))}</text>
        {''.join(bars)}
        {power_polyline}
        {''.join(power_dots)}
        {''.join(labels)}
      </svg>
    </div>
    """


def _render_team_history_cards(cards: list[dict[str, str]]) -> str:
    if not cards:
        return '<p class="footer-note">Loaded history cards will appear after more seasons are processed.</p>'
    rendered: list[str] = []
    for card in cards:
        rendered.append(
            f"""
            <article class="feature-card story-card">
              <span class="feature-rank">{escape(str(card.get("kicker") or ""))}</span>
              <h3>{escape(str(card.get("title") or ""))}</h3>
              <p>{escape(str(card.get("body") or ""))}</p>
            </article>
            """
        )
    return "".join(rendered)


def _render_history_mini_panel(history_profile: dict[str, Any]) -> str:
    if not history_profile or int(history_profile.get("loaded_seasons") or 0) <= 0:
        return """
        <article class="mini-panel detail-history">
          <h3>Historical Context</h3>
          <p>Program history will sharpen as more seasons are processed.</p>
        </article>
        """
    loaded_seasons = int(history_profile.get("loaded_seasons") or 0)
    baseline_power = history_profile.get("baseline_power")
    current_vs_baseline = history_profile.get("current_vs_baseline")
    gap_to_peak_power = history_profile.get("gap_to_peak_power")
    best_power_since = history_profile.get("best_power_since")
    best_resume_since = history_profile.get("best_resume_since")
    best_since_power_text = "best loaded power season" if best_power_since is None else f"best power since {int(best_power_since)}"
    best_since_resume_text = "best loaded resume season" if best_resume_since is None else f"best resume since {int(best_resume_since)}"
    return f"""
    <article class="mini-panel detail-history">
      <h3>Historical Context</h3>
      <p><strong>Loaded seasons:</strong> {loaded_seasons}</p>
      <p><strong>Program baseline:</strong> {_public_power_text(baseline_power)} | <strong>Current vs. standard:</strong> {_public_power_text(current_vs_baseline)}</p>
      <p><strong>Peak gap:</strong> {"--" if gap_to_peak_power is None else f"{float(gap_to_peak_power):.1f}"} | <strong>Best-since read:</strong> {escape(best_since_power_text)}</p>
      <p><strong>Resume read:</strong> {escape(best_since_resume_text)}</p>
    </article>
    """


def _render_team_history_snapshot(history_profile: dict[str, Any]) -> str:
    if not history_profile or int(history_profile.get("loaded_seasons") or 0) <= 0:
        return '<p class="footer-note">Historical snapshot cards will appear after more seasons are processed for this program.</p>'
    current_row = history_profile.get("current_row") or {}
    peak_power_row = history_profile.get("peak_power_row")
    best_resume_row = history_profile.get("best_resume_row")
    best_finish_row = history_profile.get("best_finish_row")
    best_record_row = history_profile.get("best_record_row")
    baseline_power = history_profile.get("baseline_power")
    current_vs_baseline = history_profile.get("current_vs_baseline")
    power_rank = history_profile.get("current_power_rank")
    resume_rank = history_profile.get("current_resume_rank")
    power_percentile = history_profile.get("power_percentile")
    resume_percentile = history_profile.get("resume_percentile")
    gap_to_peak_power = history_profile.get("gap_to_peak_power")
    best_power_since = history_profile.get("best_power_since")
    best_resume_since = history_profile.get("best_resume_since")
    current_season_year = int(current_row.get("season_year") or 0)
    stat_cards = [
        (
            "Loaded Seasons",
            str(int(history_profile.get("loaded_seasons") or 0)),
            "The number of fully modeled seasons currently attached to this program.",
        ),
        (
            "Program Baseline",
            _public_power_text(baseline_power),
            "A recent multi-year closing-power average. This is the kind of anchor that should matter in preseason priors.",
        ),
        (
            "Current Vs. Baseline",
            _public_power_text(current_vs_baseline),
            "How the current season's closing power stacks up against the program's recent standard.",
        ),
        (
            "Gap To Peak",
            "--" if gap_to_peak_power is None else f"{float(gap_to_peak_power):.1f}",
            "How far the current season finished below the strongest loaded team in program history.",
        ),
        (
            "Peak Loaded Season",
            (
                "--"
                if peak_power_row is None
                else f"{int(peak_power_row.get('season_year') or 0)} | {_public_power_text(peak_power_row.get('end_power_display'))}"
            ),
            "The strongest closing power this program has posted in the loaded archive.",
        ),
        (
            "Best Power Since",
            (
                "--"
                if current_season_year <= 0
                else ("Best loaded season" if best_power_since is None else f"Since {int(best_power_since)}")
            ),
            (
                "No earlier loaded season beat the current closing power."
                if current_season_year > 0 and best_power_since is None
                else (
                    f"This is the program's best power season since {int(best_power_since)}."
                    if best_power_since is not None
                    else "Best-since read will sharpen as more seasons load."
                )
            ),
        ),
        (
            "Best Resume Since",
            (
                "--"
                if current_season_year <= 0
                else ("Best loaded season" if best_resume_since is None else f"Since {int(best_resume_since)}")
            ),
            (
                "No earlier loaded season beat the current resume."
                if current_season_year > 0 and best_resume_since is None
                else (
                    f"This is the program's best resume season since {int(best_resume_since)}."
                    if best_resume_since is not None
                    else "Resume context will sharpen as more seasons load."
                )
            ),
        ),
        (
            "Best Finish",
            (
                "--"
                if best_finish_row is None
                else f"{int(best_finish_row.get('season_year') or 0)} | #{_display_rank_value(best_finish_row.get('final_rank'))}"
            ),
            "The highest loaded all-level board finish currently attached to this program.",
        ),
        (
            "Best Resume Season",
            (
                "--"
                if best_resume_row is None
                else f"{int(best_resume_row.get('season_year') or 0)} | {_public_resume_text(best_resume_row.get('end_resume_display'))} / 100"
            ),
            "The strongest body-of-work season currently attached to this program in the loaded archive.",
        ),
        (
            "Current Season Standing",
            (
                "Resume -- | Power --"
                if power_rank is None and resume_rank is None
                else f"Resume #{resume_rank or '--'} | Power #{power_rank or '--'}"
            ),
            "Where the current season sits inside this program's loaded history on the two main scales.",
        ),
        (
            "Program Percentile",
            (
                "Resume -- | Power --"
                if power_percentile is None and resume_percentile is None
                else f"Resume {0 if resume_percentile is None else round(float(resume_percentile))}th | Power {0 if power_percentile is None else round(float(power_percentile))}th"
            ),
            "A cleaner fan-facing answer to the question: is this near the top of the program's arc or just another solid year?",
        ),
    ]
    if best_record_row is not None:
        stat_cards.append(
            (
                "Best Record",
                f"{int(best_record_row.get('season_year') or 0)} | {int(best_record_row.get('wins') or 0)}-{int(best_record_row.get('losses') or 0)}",
                "The cleanest results season in the loaded archive, regardless of whether it was also the strongest by power.",
            )
        )
    rendered = []
    for label, value, body in stat_cards:
        rendered.append(
            f"""
            <article class="stat-card history-snapshot-card">
              <span>{escape(label)}</span>
              <strong>{escape(value)}</strong>
              <p class="submetric">{escape(body)}</p>
            </article>
            """
        )
    return f'<div class="stat-grid history-snapshot-grid">{"".join(rendered)}</div>'


def _phase_summary_note(phase_summary: list[dict[str, Any]]) -> str:
    if not phase_summary:
        return "Season phases are still loading."
    top = max(phase_summary, key=lambda row: int(row.get("games_played") or 0))
    phase = _phase_display_label(top.get("season_phase"))
    wins = int(top.get("wins") or 0)
    losses = int(top.get("losses") or 0)
    return f"Biggest slice of the season so far: {phase} at {wins}-{losses}."


def _phase_sort_key(phase_name: Any) -> tuple[int, str]:
    normalized = str(phase_name or "regular season").strip().replace("_", " ").lower()
    order = {
        "preseason": 0,
        "regular season": 1,
        "conference championship": 2,
        "playoff": 3,
        "bowl": 4,
        "final": 5,
    }
    return order.get(normalized, 99), normalized


def _phase_display_label(phase_name: Any) -> str:
    normalized = str(phase_name or "regular season").strip().replace("_", " ").lower()
    labels = {
        "preseason": "Preseason",
        "regular season": "Regular Season",
        "conference championship": "Conference Championship",
        "playoff": "Playoff",
        "bowl": "Bowl",
        "final": "Final",
    }
    return labels.get(normalized, " ".join(word.capitalize() for word in normalized.split()))


def _format_game_date(value: Any) -> str:
    if value in (None, ""):
        return "Date TBD"
    raw = str(value).strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"
    except ValueError:
        return raw[:10]


def _metric_text(value: Any) -> str:
    return "--" if value is None else f"{float(value):.2f}"


def _signed_metric_text(value: Any) -> str:
    return "--" if value is None else f"{float(value):+.2f}"


def render_about_model_html(summary: dict[str, Any], site_pulse: dict[str, Any]) -> str:
    season_year_value = int(summary["season_year"])
    season_name = season_label(season_year_value)
    return f"""<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>About The Model</title>
    {_global_link_tags()}
  </head>
  <body>
    <main class="site-shell" id="main-content">
      {_site_nav("../", current="about")}
      <section class="hero">
        <p class="eyebrow">Methodology</p>
        <h1>Two models, one football universe.</h1>
        <p class="lede">
          The predictive power model asks how strong a team is right now. The resume model asks what that team has earned so far.
          Both are anchored to the same {escape(season_name)} identity, even when postseason games are played in the next calendar year.
        </p>
      </section>

      <section class="section two-up">
        <article class="panel prose-panel">
          <h2>Power Model</h2>
          <p>Power is forward-looking. It is meant to estimate team quality and inform expected margins in the next game.</p>
          <p>The long-term target is the same broad direction used by the best public college-football systems: opponent-adjusted efficiency, possession quality, time decay, and diminishing returns on blowouts.</p>
          <p>The current local build now blends score results, schedule structure, preseason priors, and opponent-adjusted advanced game stats plus play and drive data where CFBD coverage is available.</p>
        </article>

        <article class="panel prose-panel">
          <h2>Resume Model</h2>
          <p>Resume is backward-looking. It cares about who you played, what happened, and how your results compare to expectation.</p>
          <p>This is the side that makes a season feel fairer for fans, because it separates “best team right now” from “best body of work so far.”</p>
          <p>The project intentionally keeps power and resume separate because that mirrors one of the most useful distinctions in serious college-football analytics.</p>
        </article>
      </section>

      <section class="section">
        <article class="panel prose-panel">
          <h2>How Teams Start A New Season</h2>
          <p>The site does not reset every team to zero in August. Preseason priors blend the previous season's closing power, recent program history, returning production, quarterback continuity, talent/recruiting signals, and roster carryover where that context exists.</p>
          <p>The goal is not to hard-code destiny. It is to start with memory, then let fresh results steadily overpower that memory as the real season unfolds.</p>
          <p>That is the same broad logic used by the best public football systems: strong priors early, much more humility once enough new-game evidence arrives.</p>
        </article>
      </section>

      <section class="section">
        <article class="panel prose-panel">
          <h2>Season Identity Rules</h2>
          <p>The site defines a season by the year the competition begins. So if a playoff or bowl tied to the 2025 competitive cycle is played in January 2026, it still belongs to the 2025 season.</p>
          <p>That keeps archives clean, keeps final rankings attached to the season they decide, and prevents offseason transfers or coaching changes in early 2026 from rewriting the 2025 final story.</p>
        </article>
      </section>

      <section class="section">
        <article class="panel prose-panel">
          <h2>Research Principles</h2>
          <p>The predictive side of the project is being shaped by established college-football ideas from systems like SP+, FEI, and Massey: tempo and possession efficiency, opponent adjustment, time weighting, and capped value for extreme blowouts.</p>
          <p>The resume side also borrows a useful lesson from systems like Colley and the merit-oriented parts of Massey: a credible body-of-work ranking should not simply be a second copy of the predictive model.</p>
          <p>Because this site combines FBS, FCS, Division II, and Division III into one universe, the model has to calibrate carefully across uneven schedules, bridge games, and different levels of data richness without pretending every comparison is equally easy.</p>
        </article>
      </section>

      <section class="section two-up">
        <article class="panel prose-panel">
          <h2>Data Stack</h2>
          <p>CFBD is the football spine of the project: schedules, scores, advanced stats, drive and play detail, rosters, recruiting, returning production, betting context, and weather.</p>
          <p>SportsDB stays in the architecture for the parts CFBD is not trying to optimize for, like identity metadata, presentation enrichment, venue details, and artwork-friendly fields.</p>
          <p>The current local build is surfacing {site_pulse['tracked_teams']:,} team records, {site_pulse['tracked_conferences']} conferences across FBS/FCS/D-II/D-III, and {site_pulse['current_season_completed_games']:,} completed games in the working season archive.</p>
        </article>

        <article class="panel prose-panel">
          <h2>Projection Defaults</h2>
          <p>The matchup surfaces are powered by the predictive layer only, so projected scores stay tied to team quality instead of drifting toward resume sentiment.</p>
          <p>Today the live projection defaults use roughly {site_pulse['base_points']:.1f} base points per team and a {site_pulse['home_field_advantage']:.1f}-point home edge when a sideline advantage is applied.</p>
          <p>That makes the site's matchup studio useful for both playoff-style debates and lower-division bridge questions without turning the resume board into a fake point spread model.</p>
        </article>
      </section>

      <section class="section">
        <article class="panel prose-panel">
          <h2>Program Count Reference</h2>
          <p>As of {escape(PROGRAM_COUNT_REFERENCE_DATE)}, our current reference numbers are:
          FBS {SUBDIVISION_PROGRAM_COUNTS['FBS']['active_full_members']} active/full members, {SUBDIVISION_PROGRAM_COUNTS['FBS']['with_transitioning']} including transitioners;
          FCS {SUBDIVISION_PROGRAM_COUNTS['FCS']['active_full_members']} active/full members, {SUBDIVISION_PROGRAM_COUNTS['FCS']['broad_sponsoring_count']} on the broader NCAA sponsorship listing;
          Division II {SUBDIVISION_PROGRAM_COUNTS['DII']['football_programs']};
          Division III {SUBDIVISION_PROGRAM_COUNTS['DIII']['football_programs']}.</p>
        </article>
      </section>
    </main>
  </body>
</html>
"""


def _render_heisman_feature_cards(rows: list[HeismanRankingRow]) -> str:
    if not rows:
        return '<p class="footer-note">Once Heisman rows are loaded, this section will spotlight the favorite, the best non-quarterback, the strongest Group of Five candidacy, and any credible defensive outlier.</p>'

    favorite = rows[0]
    top_non_qb = next((row for row in rows if _normalize_position(row.position) and _normalize_position(row.position) != "QB"), None)
    top_g5 = next((row for row in rows if (row.conference_name or "") in G5_CONFERENCES), None)
    top_defender = next((row for row in rows if _is_defensive_position(row.position)), None)
    cards: list[str] = []
    for label, row, detail in [
        ("Favorite", favorite, f"Win equity {_probability_text(favorite.win_probability)}"),
        (
            "Best non-QB",
            top_non_qb,
            "--" if top_non_qb is None else f"{_normalize_position(top_non_qb.position) or 'ATH'} | {_probability_text(top_non_qb.win_probability)} to win",
        ),
        (
            "Best Group of Five case",
            top_g5,
            "--"
            if top_g5 is None
            else f"{top_g5.conference_name or 'G5'} | Rank #{top_g5.overall_rank}",
        ),
        (
            "Best defensive case",
            top_defender,
            "--"
            if top_defender is None
            else f"{_normalize_position(top_defender.position)} | Rank #{top_defender.overall_rank}",
        ),
    ]:
        if row is None:
            continue
        cards.append(
            f"""
            <a class="feature-card story-card" href="../players/{escape(row.player_slug)}.html">
              <span class="feature-rank">{escape(label)}</span>
              <h3>{escape(row.full_name)}</h3>
              <p>{escape(str(row.team_name or 'Team context pending'))}</p>
              <p class="story-tail">{escape(detail)}</p>
            </a>
            """
        )
    return "".join(cards)


def _render_heisman_board_row(row: HeismanRankingRow, include_market: bool = False) -> str:
    position = _normalize_position(row.position)
    position_group = _position_filter_bucket(position)
    team_name = str(row.team_name or "")
    conference_name = str(row.conference_name or "")
    search_blob = " ".join(
        [
            row.full_name,
            team_name,
            conference_name,
            position,
            row.class_year or "",
        ]
    ).lower()
    team_cell = (
        f'<a class="team-link" href="../teams/{escape(str(row.team_slug))}.html">{escape(str(row.team_name or ""))}</a>'
        if row.team_slug
        else escape(str(row.team_name or "--"))
    )
    market_cell = (
        f'<td class="metric-cell">{escape(_market_board_text(row.market_american_odds, row.market_implied_probability, row.market_provider))}</td>'
        if include_market
        else ""
    )
    return f"""
    <tr
      class="heisman-row"
      data-rank="{int(row.overall_rank)}"
      data-win="{'' if row.win_probability is None else float(row.win_probability):.6f}"
      data-finalist="{'' if row.finalist_probability is None else float(row.finalist_probability):.6f}"
      data-ballot="{'' if row.expected_ballot_share is None else float(row.expected_ballot_share):.6f}"
      data-search="{escape(search_blob)}"
      data-position-group="{escape(position_group)}"
      data-team-filter="{escape(_board_filter_value(team_name))}"
      data-team-label="{escape(team_name)}"
      data-conference-filter="{escape(_board_filter_value(conference_name))}"
      data-conference-label="{escape(conference_name)}"
    >
      <td class="metric-cell">#{int(row.overall_rank)}</td>
      <td><a class="team-link" href="../players/{escape(row.player_slug)}.html">{escape(row.full_name)}</a><span class="submetric">{escape(position or '--')} | {escape(str(row.class_year or '--'))}</span></td>
      <td>{team_cell}<span class="submetric">{escape(str(row.conference_name or ''))}</span></td>
      <td class="metric-cell">{escape(position or '--')}</td>
      <td class="metric-cell">{escape(_display_rank_text(row.nowcast_rank))}</td>
      <td class="metric-cell">{escape(_display_rank_text(row.forecast_rank))}</td>
      {market_cell}
      <td class="metric-cell">{escape(_probability_text(row.win_probability))}</td>
      <td class="metric-cell">{escape(_probability_text(row.finalist_probability))}</td>
      <td class="metric-cell">{escape(_probability_text(row.expected_ballot_share))}</td>
    </tr>
    """


def _render_player_directory_row(row: dict[str, Any]) -> str:
    position = _normalize_position(row.get("current_position"))
    search_blob = " ".join(
        [
            str(row.get("full_name") or ""),
            str(row.get("team_name") or row.get("primary_team_name") or ""),
            str(row.get("conference_name") or row.get("primary_conference_name") or ""),
            position,
        ]
    ).lower()
    team_name = str(row.get("team_name") or row.get("primary_team_name") or "--")
    team_slug = row.get("team_slug") or row.get("primary_team_slug")
    team_cell = (
        f'<a class="team-link" href="../teams/{escape(str(team_slug))}.html">{escape(team_name)}</a>'
        if team_slug
        else escape(team_name)
    )
    return f"""
    <tr
      class="player-directory-row"
      data-search="{escape(search_blob)}"
      data-position-group="{escape(_position_filter_bucket(position))}"
      data-current-rank="{'' if row.get('current_heisman_rank') is None else int(row.get('current_heisman_rank') or 0)}"
      data-best-finish="{'' if row.get('official_best_finish') is None else int(row.get('official_best_finish') or 0)}"
      data-tracked-seasons="{int(row.get('tracked_heisman_seasons') or 0)}"
      data-forecast="{'' if row.get('forecast_rank') is None else int(row.get('forecast_rank') or 0)}"
    >
      <td><a class="team-link" href="{escape(str(row.get('player_slug') or ''))}.html">{escape(str(row.get("full_name") or ""))}</a><span class="submetric">{escape(str(row.get("class_year") or "--"))}</span></td>
      <td>{team_cell}<span class="submetric">{escape(str(row.get("conference_name") or row.get("primary_conference_name") or ""))}</span></td>
      <td class="metric-cell">{escape(position or '--')}</td>
      <td class="metric-cell">{escape(_display_rank_text(row.get("current_heisman_rank")))}</td>
      <td class="metric-cell">{escape(_display_rank_text(row.get("official_best_finish")))}</td>
      <td class="metric-cell">{int(row.get("tracked_heisman_seasons") or 0)}</td>
      <td class="metric-cell">{escape(_display_rank_text(row.get("forecast_rank")))}</td>
      <td><a class="text-link" href="{escape(str(row.get('player_slug') or ''))}.html">Open card</a></td>
    </tr>
    """


def _render_player_heisman_year_row(row: dict[str, Any]) -> str:
    team_cell = (
        f'<a class="team-link" href="../teams/{escape(str(row.get("team_slug") or ""))}.html">{escape(str(row.get("team_name") or ""))}</a>'
        if row.get("team_slug")
        else escape(str(row.get("team_name") or "--"))
    )
    latest_model_rank = (
        row.get("nowcast_rank")
        if row.get("nowcast_rank") is not None
        else row.get("overall_rank")
    )
    context_bits = []
    if row.get("latest_week") is not None:
        context_bits.append(f"W{int(row.get('latest_week') or 0)} snapshot")
    if row.get("conference_name"):
        context_bits.append(str(row.get("conference_name")))
    market_text = _market_board_text(
        row.get("market_american_odds"),
        row.get("market_implied_probability"),
        row.get("market_provider"),
    )
    if market_text != "--":
        context_bits.append(f"Market {market_text}")
    if row.get("winner_flag"):
        context_bits.append("Won the trophy")
    elif row.get("finalist_flag"):
        context_bits.append("Official finalist")
    context_text = " | ".join(context_bits) if context_bits else "--"
    return f"""
    <tr>
      <td>{int(row.get("season_year") or 0)}</td>
      <td>{team_cell}</td>
      <td>{escape(str(row.get("position") or "--"))}<span class="submetric">{escape(str(row.get("class_year") or "--"))}</span></td>
      <td class="metric-cell">{escape(_display_rank_text(latest_model_rank))}</td>
      <td class="metric-cell">{escape(_display_rank_text(row.get("forecast_rank")))}</td>
      <td class="metric-cell">{escape(_probability_text(row.get("win_probability")))}</td>
      <td class="metric-cell">{escape(_probability_text(row.get("finalist_probability")))}</td>
      <td class="metric-cell">{escape(str(row.get("official_result_text") or "--"))}</td>
      <td class="metric-cell">{escape("--" if row.get("total_points") is None else str(int(row.get("total_points") or 0)))}</td>
      <td>{escape(context_text)}</td>
    </tr>
    """


def _render_player_roster_history_row(row: dict[str, Any]) -> str:
    team_cell = (
        f'<a class="team-link" href="../teams/{escape(str(row.get("team_slug") or ""))}.html">{escape(str(row.get("team_name") or ""))}</a>'
        if row.get("team_slug")
        else escape(str(row.get("team_name") or "--"))
    )
    bio_parts = []
    if row.get("jersey"):
        bio_parts.append(f"No. {row['jersey']}")
    measurement = _player_measurement_text(row.get("height_inches"), row.get("weight_lbs"))
    if measurement != "--":
        bio_parts.append(measurement)
    hometown = _player_hometown_text(row.get("hometown"), row.get("home_state"))
    if hometown != "--":
        bio_parts.append(hometown)
    return f"""
    <tr>
      <td>{int(row.get("season_year") or 0)}</td>
      <td>{team_cell}</td>
      <td>{escape(str(row.get("conference_name") or row.get("level_code") or "--"))}</td>
      <td class="metric-cell">{escape(str(row.get("position") or "--"))}</td>
      <td class="metric-cell">{escape(str(row.get("class_year") or "--"))}</td>
      <td>{escape(" | ".join(bio_parts) if bio_parts else "--")}</td>
    </tr>
    """


def _render_player_honor_row(row: dict[str, Any]) -> str:
    team_or_selector = " | ".join(
        part
        for part in [
            str(row.get("team_name") or "").strip(),
            str(row.get("selector") or "").strip(),
        ]
        if part
    ) or "--"
    context_bits = []
    if row.get("honor_team"):
        context_bits.append(str(row.get("honor_team")))
    if row.get("position"):
        context_bits.append(str(row.get("position")))
    if row.get("conference_name"):
        context_bits.append(str(row.get("conference_name")))
    if row.get("week") not in (None, 0):
        context_bits.append(f"Week {int(row.get('week') or 0)}")
    if row.get("consensus_flag"):
        context_bits.append("Consensus")
    if row.get("unanimous_flag"):
        context_bits.append("Unanimous")
    return f"""
    <tr>
      <td>{int(row.get("season_year") or 0)}</td>
      <td>{escape(str(row.get("honor_name") or "--"))}</td>
      <td>{escape(str(row.get("honor_scope") or "--"))}</td>
      <td>{escape(team_or_selector)}</td>
      <td>{escape(" | ".join(context_bits) if context_bits else "--")}</td>
    </tr>
    """


def _render_player_traditional_stat_section(section: dict[str, Any]) -> str:
    cells = "".join(
        f"""
        <td class="metric-cell player-stat-table-cell" data-label="{escape(str(cell.get("label") or "--"))}">
          <div class="player-stat-table-line">
            <span class="player-stat-table-value">{escape(str(cell.get("value") or "--"))}</span>
            <span class="player-stat-table-peer {escape(str(cell.get("tone") or "tone-neutral"))}">{escape(str(cell.get("peer") or "--"))}</span>
          </div>
        </td>
        """
        for cell in (section.get("cells") or [])
    )
    headers = "".join(f"<th>{escape(str(cell.get('label') or '--'))}</th>" for cell in (section.get("cells") or []))
    subtitle = str(section.get("subtitle") or "").strip()
    peer_basis = str(section.get("peer_basis") or "").strip()
    section_meta = "".join(
        part
        for part in [
            f'<span class="player-stat-section-chip">{escape(str(section.get("season_label") or "Current season"))}</span>',
            f'<span class="player-stat-section-chip">{escape(peer_basis)}</span>' if peer_basis else "",
        ]
    )
    return f"""
    <div class="player-stat-traditional-section">
      <div class="player-stat-section-head">
        <div>
          <h4>{escape(str(section.get("title") or "Stats"))}</h4>
          {f'<p>{escape(subtitle)}</p>' if subtitle else ''}
        </div>
        <div class="player-stat-section-meta">
          {section_meta}
        </div>
      </div>
      <div class="table-wrap compact-table-wrap player-stat-traditional-table">
        <table>
          <thead>
            <tr>
              {headers}
            </tr>
          </thead>
          <tbody>
            <tr>
              {cells}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    """


def _player_metric_help_text(metric_name: Any) -> str | None:
    metric_key = _board_filter_value(metric_name)
    catalog = {
        "passing-wepa": "Opponent-adjusted passing value. Positive means the player is creating more through the air than a neutral same-role peer would against that schedule.",
        "rushing-wepa": "Opponent-adjusted rushing value. It rewards carries and runs that create actual offensive value, not just raw volume.",
        "role-share": "Estimated share of the team's offense owned by this player after combining the ways the ball flows through them.",
        "pass-share": "Share of the team's passing-game involvement. Useful for separating featured targets or pass-heavy quarterbacks from lower-volume roles.",
        "rush-share": "Share of the team's rushing-game involvement. Useful for spotting true workload backs and designed-run quarterbacks.",
        "yards-attempt": "Yards per attempt. This is a quick read on downfield efficiency and explosive passing without needing a full stat sheet.",
        "yards-carry": "Yards per carry. It is not perfect on its own, but it quickly signals whether the rushing profile is efficient or grinding for volume.",
        "yards-catch": "Yards per catch. A fast indicator of how much vertical or chunk-play value a receiver creates.",
        "passer-rating": "Passing efficiency formula built from completion rate, yards, touchdowns, and interceptions. It is a familiar summary stat for quarterbacks.",
        "peer-percentile": "Percentile vs same-position players at the same competition level. An FBS quarterback is compared only with other FBS quarterbacks.",
    }
    return catalog.get(metric_key)


def _render_player_metric_label(metric_name: Any) -> str:
    label = escape(str(metric_name or "--"))
    help_text = _player_metric_help_text(metric_name)
    if not help_text:
        return label
    return f"""
      <span class="metric-label-wrap">
        <span>{label}</span>
        <span class="metric-help" tabindex="0" aria-label="Explain {label}">
          <span class="metric-help-dot">?</span>
          <span class="metric-help-bubble">{escape(help_text)}</span>
        </span>
      </span>
    """


def _render_player_season_stat_table(section: dict[str, Any]) -> str:
    headers = "".join(f"<th>{escape(str(label or '--'))}</th>" for label in (section.get("columns") or []))
    rows_html: list[str] = []
    for row in (section.get("rows") or []):
        team_name = str(row.get("team_name") or "--")
        team_slug = row.get("team_slug")
        team_cell = (
            f'<a class="team-link" href="../teams/{escape(str(team_slug))}.html">{escape(team_name)}</a>'
            if team_slug
            else f"<strong>{escape(team_name)}</strong>"
        )
        cells = "".join(
            f'<td class="metric-cell" data-label="{escape(str(cell.get("label") or "--"))}">{escape(str(cell.get("value") or "--"))}</td>'
            for cell in (row.get("cells") or [])
        )
        row_class = "player-stat-season-summary-row" if str(row.get("row_kind") or "") == "career" else ""
        context = str(row.get("context") or "").strip()
        rows_html.append(
            f"""
            <tr class="{row_class}">
              <td data-label="Season">{escape(str(row.get("season_label") or "--"))}</td>
              <td data-label="Team">{team_cell}{f'<span class="submetric">{escape(context)}</span>' if context else ''}</td>
              {cells}
            </tr>
            """
        )
    subtitle = str(section.get("subtitle") or "").strip()
    return f"""
    <div class="player-stat-season-table">
      <div class="player-stat-section-head">
        <div>
          <h4>{escape(str(section.get("title") or "Season stats"))}</h4>
          {f'<p>{escape(subtitle)}</p>' if subtitle else ''}
        </div>
      </div>
      <div class="table-wrap compact-table-wrap player-stat-season-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Season</th>
              <th>Team</th>
              {headers}
            </tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
      </div>
    </div>
    """


def _render_player_page_subnav(items: list[tuple[str, str]]) -> str:
    links = "".join(
        f'<a class="player-page-subnav-link{" is-active" if index == 0 else ""}" href="#{escape(anchor)}" data-player-nav-target="{escape(anchor)}">{escape(label)}</a>'
        for index, (anchor, label) in enumerate(items)
    )
    return f"""
    <div class="player-page-subnav-shell">
      <nav class="player-page-subnav" aria-label="Player page sections">
        {links}
      </nav>
    </div>
    """


def _render_player_stat_explorer_row(row: dict[str, Any]) -> str:
    return f"""
    <tr
      data-stat-group="{escape(str(row.get('group_key') or ''))}"
      data-stat-metric="{escape(str(row.get('metric') or '').lower())}"
      data-stat-value="{float(row.get('sort_value') or 0.0):.6f}"
      data-stat-priority="{int(row.get('priority') or 999)}"
    >
      <td><span class="player-stat-group-pill">{escape(str(row.get("group") or "--"))}</span></td>
      <td>{escape(str(row.get("metric") or "--"))}</td>
      <td class="metric-cell">{escape(str(row.get("value") or "--"))}</td>
      <td class="metric-cell">{escape(str(row.get("rank_text") or "--"))}</td>
      <td class="metric-cell">{escape(str(row.get("percentile_text") or "--"))}</td>
      <td>{escape(str(row.get("context") or "--"))}<span class="submetric">{escape(str(row.get("peer_basis") or ""))}</span></td>
    </tr>
    """


def _player_page_nav_script() -> str:
    return """
      <script>
        (() => {
          const links = Array.from(document.querySelectorAll('[data-player-nav-target]'));
          if (!links.length || !('IntersectionObserver' in window)) return;
          const sectionMap = new Map(
            links
              .map((link) => [link.dataset.playerNavTarget || '', document.getElementById(link.dataset.playerNavTarget || '')])
              .filter((entry) => entry[0] && entry[1])
          );
          if (!sectionMap.size) return;

          const setActive = (id) => {
            links.forEach((link) => {
              link.classList.toggle('is-active', (link.dataset.playerNavTarget || '') === id);
            });
          };

          const observer = new IntersectionObserver((entries) => {
            const visible = entries
              .filter((entry) => entry.isIntersecting)
              .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
            if (!visible) return;
            if (visible.target && visible.target.id) {
              setActive(visible.target.id);
            }
          }, {
            rootMargin: '-20% 0px -60% 0px',
            threshold: [0.1, 0.25, 0.45, 0.65],
          });

          Array.from(sectionMap.values()).forEach((section) => observer.observe(section));
        })();
      </script>
    """


def _player_stats_script() -> str:
    return """
      <script>
        (() => {
          const tableBody = document.getElementById('playerStatsExplorerBody');
          if (!tableBody) return;
          const rows = Array.from(tableBody.querySelectorAll('tr'));
          if (!rows.length) return;

          const filterButtons = Array.from(document.querySelectorAll('[data-player-stat-filter]'));
          const sortSelect = document.getElementById('playerStatsSort');
          const searchInput = document.getElementById('playerStatsSearch');
          const visibleCount = document.getElementById('playerStatsVisibleCount');
          const stateText = document.getElementById('playerStatsStateText');
          const sortTriggers = Array.from(document.querySelectorAll('[data-player-stat-sort-trigger]'));
          let activeFilter = (filterButtons.find((button) => button.classList.contains('is-active'))?.dataset.playerStatFilter) || 'all';

          const sorters = {
            priority: (a, b) => Number(a.dataset.statPriority || 999) - Number(b.dataset.statPriority || 999),
            'value-desc': (a, b) => Number(b.dataset.statValue || 0) - Number(a.dataset.statValue || 0),
            'value-asc': (a, b) => Number(a.dataset.statValue || 0) - Number(b.dataset.statValue || 0),
            metric: (a, b) => (a.dataset.statMetric || '').localeCompare(b.dataset.statMetric || ''),
            group: (a, b) => (a.dataset.statGroup || '').localeCompare(b.dataset.statGroup || '') || (a.dataset.statMetric || '').localeCompare(b.dataset.statMetric || ''),
          };

          const applyState = () => {
            const sorter = sorters[sortSelect?.value || 'priority'] || sorters.priority;
            const query = (searchInput?.value || '').trim().toLowerCase();
            const filtered = rows
              .filter((row) => {
                const matchesFilter = activeFilter === 'all' || row.dataset.statGroup === activeFilter;
                const haystack = `${row.dataset.statMetric || ''} ${row.dataset.statGroup || ''} ${row.textContent || ''}`.toLowerCase();
                const matchesQuery = !query || haystack.includes(query);
                return matchesFilter && matchesQuery;
              })
              .sort(sorter);

            filtered.forEach((row) => tableBody.appendChild(row));
            rows.forEach((row) => {
              row.hidden = !filtered.includes(row);
            });
            if (visibleCount) visibleCount.textContent = String(filtered.length);
            if (stateText) {
              const activeButton = filterButtons.find((button) => button.dataset.playerStatFilter === activeFilter);
              const filterLabel = (activeButton?.textContent || 'All metrics').trim().toLowerCase();
              const queryText = query ? ` matching "${query}"` : '';
              stateText.textContent = `Showing ${filterLabel}${queryText}`;
            }
          };

          filterButtons.forEach((button) => {
            button.addEventListener('click', () => {
              activeFilter = button.dataset.playerStatFilter || 'all';
              filterButtons.forEach((candidate) => candidate.classList.toggle('is-active', candidate === button));
              applyState();
            });
          });

          if (sortSelect) {
            sortSelect.addEventListener('input', applyState);
            sortSelect.addEventListener('change', applyState);
          }

          sortTriggers.forEach((trigger) => {
            trigger.addEventListener('click', () => {
              const nextSort = trigger.dataset.playerStatSortTrigger || 'priority';
              if (sortSelect) {
                sortSelect.value = nextSort;
              }
              applyState();
            });
          });

          if (searchInput) {
            searchInput.addEventListener('input', applyState);
            searchInput.addEventListener('search', applyState);
          }

          applyState();
        })();
      </script>
    """


def _player_directory_script() -> str:
    return """
      (() => {
        const rows = Array.from(document.querySelectorAll('#playerDirectoryBody tr.player-directory-row'));
        if (!rows.length) return;

        const searchInput = document.getElementById('playerDirectorySearch');
        const positionFilter = document.getElementById('playerDirectoryPositionFilter');
        const sortMode = document.getElementById('playerDirectorySort');
        const countNode = document.getElementById('playerDirectoryVisibleCount');
        const tableBody = document.getElementById('playerDirectoryBody');

        const normalized = (value) => (value || '').toString().trim().toLowerCase();
        const numericValue = (row, key, fallback = Number.POSITIVE_INFINITY) => {
          const raw = row.dataset[key];
          if (raw === undefined || raw === null || raw === '') return fallback;
          const parsed = Number(raw);
          return Number.isFinite(parsed) ? parsed : fallback;
        };
        const playerName = (row) => {
          const anchor = row.querySelector('.team-link');
          return anchor ? anchor.textContent.trim() : '';
        };

        const sorters = {
          'current-rank': (a, b) => numericValue(a, 'currentRank') - numericValue(b, 'currentRank') || playerName(a).localeCompare(playerName(b)),
          'best-finish': (a, b) => numericValue(a, 'bestFinish') - numericValue(b, 'bestFinish') || playerName(a).localeCompare(playerName(b)),
          'tracked-seasons': (a, b) => numericValue(b, 'trackedSeasons', 0) - numericValue(a, 'trackedSeasons', 0) || playerName(a).localeCompare(playerName(b)),
          forecast: (a, b) => numericValue(a, 'forecast') - numericValue(b, 'forecast') || playerName(a).localeCompare(playerName(b)),
          player: (a, b) => playerName(a).localeCompare(playerName(b)),
        };

        function applyState() {
          const query = normalized(searchInput?.value);
          const position = positionFilter?.value || 'ALL';
          const sorter = sorters[sortMode?.value] || sorters['current-rank'];

          const filtered = rows.filter((row) => {
            const matchesQuery = !query || (row.dataset.search || '').includes(query);
            const matchesPosition = position === 'ALL' || row.dataset.positionGroup === position;
            return matchesQuery && matchesPosition;
          }).sort(sorter);

          filtered.forEach((row) => tableBody.appendChild(row));
          const visible = new Set(filtered);
          rows.forEach((row) => {
            row.hidden = !visible.has(row);
          });
          if (countNode) countNode.textContent = String(filtered.length);
        }

        [searchInput, positionFilter, sortMode].forEach((node) => {
          if (!node) return;
          node.addEventListener('input', applyState);
          node.addEventListener('change', applyState);
        });

        applyState();
      })();
    """


def _heisman_board_script() -> str:
    return """
      (() => {
        const rows = Array.from(document.querySelectorAll('#heismanBoardBody tr.heisman-row'));
        if (!rows.length) return;

        const searchInput = document.getElementById('heismanSearch');
        const teamFilter = document.getElementById('heismanTeamFilter');
        const conferenceFilter = document.getElementById('heismanConferenceFilter');
        const positionFilter = document.getElementById('heismanPositionFilter');
        const sortMode = document.getElementById('heismanSortMode');
        const clearButton = document.getElementById('clearHeismanFilters');
        const countNode = document.getElementById('heismanVisibleCount');
        const chipRow = document.getElementById('heismanActiveFilterRow');
        const tableBody = document.getElementById('heismanBoardBody');
        const jumpButtons = Array.from(document.querySelectorAll('[data-heisman-limit]'));
        let limit = 'all';

        const normalized = (value) => (value || '').toString().trim().toLowerCase();
        const numericValue = (row, key, fallback = Number.NEGATIVE_INFINITY) => {
          const raw = row.dataset[key];
          if (raw === undefined || raw === null || raw === '') return fallback;
          const parsed = Number(raw);
          return Number.isFinite(parsed) ? parsed : fallback;
        };
        const playerName = (row) => {
          const anchor = row.querySelector('.team-link');
          return anchor ? anchor.textContent.trim() : '';
        };
        const sortedUniquePairs = (pairs) => Array.from(
          new Map(
            pairs.filter(([value, label]) => value && label).map(([value, label]) => [value, label])
          ).entries()
        ).sort((a, b) => a[1].localeCompare(b[1]));
        const sorters = {
          rank: (a, b) => numericValue(a, 'rank', Number.POSITIVE_INFINITY) - numericValue(b, 'rank', Number.POSITIVE_INFINITY) || playerName(a).localeCompare(playerName(b)),
          win: (a, b) => numericValue(b, 'win') - numericValue(a, 'win') || numericValue(a, 'rank', Number.POSITIVE_INFINITY) - numericValue(b, 'rank', Number.POSITIVE_INFINITY),
          finalist: (a, b) => numericValue(b, 'finalist') - numericValue(a, 'finalist') || numericValue(a, 'rank', Number.POSITIVE_INFINITY) - numericValue(b, 'rank', Number.POSITIVE_INFINITY),
          ballot: (a, b) => numericValue(b, 'ballot') - numericValue(a, 'ballot') || numericValue(a, 'rank', Number.POSITIVE_INFINITY) - numericValue(b, 'rank', Number.POSITIVE_INFINITY),
          player: (a, b) => playerName(a).localeCompare(playerName(b)),
        };

        function renderChips(tokens) {
          if (!chipRow) return;
          chipRow.innerHTML = '';
          if (!tokens.length) {
            chipRow.hidden = true;
            return;
          }
          chipRow.hidden = false;
          tokens.forEach((token) => {
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            chip.textContent = token;
            chipRow.appendChild(chip);
          });
        }

        function rebuildTeamOptions() {
          if (!teamFilter) return;
          const selectedConference = conferenceFilter?.value || 'ALL';
          const previousTeam = teamFilter.value || 'ALL';
          const options = sortedUniquePairs(
            rows
              .filter((row) => selectedConference === 'ALL' || row.dataset.conferenceFilter === selectedConference)
              .map((row) => [row.dataset.teamFilter || '', row.dataset.teamLabel || ''])
          );

          teamFilter.innerHTML = '';
          teamFilter.add(new Option('All teams', 'ALL'));
          options.forEach(([value, label]) => {
            teamFilter.add(new Option(label, value));
          });
          teamFilter.value = options.some(([value]) => value === previousTeam) ? previousTeam : 'ALL';
        }

        function applyState() {
          const query = normalized(searchInput?.value);
          const team = teamFilter?.value || 'ALL';
          const conference = conferenceFilter?.value || 'ALL';
          const position = positionFilter?.value || 'ALL';
          const sorter = sorters[sortMode?.value] || sorters.rank;

          const filtered = rows.filter((row) => {
            const matchesQuery = !query || (row.dataset.search || '').includes(query);
            const matchesTeam = team === 'ALL' || row.dataset.teamFilter === team;
            const matchesConference = conference === 'ALL' || row.dataset.conferenceFilter === conference;
            const matchesPosition = position === 'ALL' || row.dataset.positionGroup === position;
            return matchesQuery && matchesTeam && matchesConference && matchesPosition;
          }).sort(sorter);

          filtered.forEach((row) => tableBody.appendChild(row));
          const visibleRows = limit === 'all' ? filtered : filtered.slice(0, limit);
          const visibleSet = new Set(visibleRows);
          rows.forEach((row) => {
            row.hidden = !visibleSet.has(row);
          });
          if (countNode) countNode.textContent = String(visibleRows.length);

          const chipTokens = [];
          if (query) chipTokens.push(`Search: ${searchInput.value.trim()}`);
          if (team !== 'ALL' && teamFilter) chipTokens.push(`Team: ${teamFilter.options[teamFilter.selectedIndex].text}`);
          if (conference !== 'ALL' && conferenceFilter) chipTokens.push(`Conference: ${conferenceFilter.options[conferenceFilter.selectedIndex].text}`);
          if (position !== 'ALL' && positionFilter) chipTokens.push(`Position: ${positionFilter.options[positionFilter.selectedIndex].text}`);
          if (sortMode) chipTokens.push(`Sort: ${sortMode.options[sortMode.selectedIndex].text}`);
          chipTokens.push(limit === 'all' ? 'Range: All players' : `Range: Top ${limit}`);
          renderChips(chipTokens);
        }

        [searchInput, teamFilter, positionFilter, sortMode].forEach((node) => {
          if (!node) return;
          node.addEventListener('input', applyState);
          node.addEventListener('change', applyState);
        });
        if (conferenceFilter) {
          conferenceFilter.addEventListener('input', () => {
            rebuildTeamOptions();
            applyState();
          });
          conferenceFilter.addEventListener('change', () => {
            rebuildTeamOptions();
            applyState();
          });
        }

        if (clearButton) {
          clearButton.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (conferenceFilter) conferenceFilter.value = 'ALL';
            rebuildTeamOptions();
            if (teamFilter) teamFilter.value = 'ALL';
            if (positionFilter) positionFilter.value = 'ALL';
            if (sortMode) sortMode.value = 'rank';
            limit = 'all';
            jumpButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.heismanLimit === 'all'));
            applyState();
          });
        }

        jumpButtons.forEach((button) => {
          button.addEventListener('click', () => {
            jumpButtons.forEach((candidate) => candidate.classList.remove('is-active'));
            button.classList.add('is-active');
            limit = button.dataset.heismanLimit === 'all' ? 'all' : parseInt(button.dataset.heismanLimit, 10);
            applyState();
          });
        });

        rebuildTeamOptions();
        applyState();
      })();
    """


def _player_slug(player_id: int, full_name: str) -> str:
    return f"{slugify(full_name)}-{player_id}"


def _normalize_position(value: Any) -> str:
    return str(value or "").strip().upper()


def _position_filter_bucket(value: Any) -> str:
    normalized = _normalize_position(value)
    if normalized in {"QB", "RB", "WR", "TE"}:
        return normalized
    if _is_defensive_position(normalized):
        return "DEF"
    return "OTHER"


def _is_defensive_position(value: Any) -> bool:
    normalized = _normalize_position(value)
    return normalized in DEFENSIVE_POSITIONS or normalized.startswith("DB")


def _display_rank_text(value: Any) -> str:
    return "--" if value in (None, "") else f"#{int(value)}"


def _board_filter_value(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


def _recruit_stars_text(value: Any) -> str:
    if value in (None, "", 0):
        return "--"
    return f"{int(value)}-star"


def _display_recruit_rank(value: Any) -> str:
    if value in (None, "", 0):
        return "National rank TBD"
    return f"No. {int(value)} recruit"


def _location_text(city: Any, state_province: Any, country: Any) -> str:
    parts = [str(part).strip() for part in (city, state_province, country) if str(part or "").strip()]
    return ", ".join(parts) if parts else "--"


def _fmt_whole(value: Any) -> str:
    if value in (None, ""):
        return "--"
    return f"{int(round(float(value))):,}"


def _fmt_decimal(value: Any, digits: int = 1) -> str:
    if value in (None, ""):
        return "--"
    return f"{float(value):,.{digits}f}"


def _fmt_signed_decimal(value: Any, digits: int = 2) -> str:
    if value in (None, ""):
        return "--"
    return f"{float(value):+,.{digits}f}"


def _fmt_pct_fraction(value: Any) -> str:
    if value in (None, ""):
        return "--"
    numeric = float(value)
    scaled = numeric * 100.0 if abs(numeric) <= 1.0 else numeric
    return f"{scaled:.1f}%"


def _probability_text(value: Any) -> str:
    if value in (None, ""):
        return "--"
    numeric = float(value)
    scaled = numeric if numeric > 1.0 else numeric * 100.0
    return f"{scaled:.1f}%"


def _market_board_text(american_odds: Any, implied_probability: Any, provider: Any) -> str:
    pieces: list[str] = []
    if american_odds not in (None, ""):
        odds_value = int(float(american_odds))
        pieces.append(f"{odds_value:+d}")
    probability_text = _probability_text(implied_probability)
    if probability_text != "--":
        pieces.append(probability_text)
    if provider not in (None, ""):
        pieces.append(str(provider))
    return " | ".join(pieces) if pieces else "--"


def _player_measurement_text(height_inches: Any, weight_lbs: Any) -> str:
    if height_inches in (None, "") and weight_lbs in (None, ""):
        return "--"
    parts: list[str] = []
    if height_inches not in (None, ""):
        total_inches = int(round(float(height_inches)))
        feet = total_inches // 12
        inches = total_inches % 12
        parts.append(f"{feet}-{inches}")
    if weight_lbs not in (None, ""):
        parts.append(f"{int(round(float(weight_lbs)))} lb")
    return " | ".join(parts) if parts else "--"


def _player_hometown_text(hometown: Any, home_state: Any) -> str:
    parts = [str(part).strip() for part in [hometown, home_state] if part not in (None, "")]
    return ", ".join(parts) if parts else "--"


def _official_heisman_result_text(vote_row: dict[str, Any]) -> str:
    if not vote_row:
        return "--"
    if vote_row.get("winner_flag"):
        return "Winner"
    place = vote_row.get("place")
    if place is not None:
        return f"#{int(place)} finish"
    if vote_row.get("total_points") not in (None, 0):
        return "Received points"
    return "Tracked"


def _player_module_cards() -> list[dict[str, str]]:
    return [
        {
            "kicker": "Splits",
            "title": "Leverage and situation dashboard",
            "body": "Top-tier cards should break production into red zone, early downs, passing downs, garbage-time filters, ranked-opponent games, and one-score moments so the profile can separate accumulation from leverage.",
        },
        {
            "kicker": "Moments",
            "title": "Signature-game ledger",
            "body": "The page should remember the actual performances voters and fans cite: biggest game grades, ranked-opponent explosions, rivalry games, conference title week, and the moments that changed the player's national case.",
        },
        {
            "kicker": "Honors",
            "title": "Selector-grade awards archive",
            "body": "All-America teams by selector, consensus and unanimous status, all-conference teams, player-of-the-year awards, watch lists, and weekly honors should all live on one structured timeline.",
        },
        {
            "kicker": "Context",
            "title": "Team environment and supporting cast",
            "body": "Serious player evaluation needs team quality, offensive or defensive ecosystem, line play, schedule strength, poll visibility, and teammate competition so the production is interpreted in the right setting.",
        },
        {
            "kicker": "Career",
            "title": "Recruiting, transfers, and pro arc",
            "body": "Recruit pedigree, transfer path, age, breakout timing, draft trajectory, and year-over-year development are what turn a season page into a durable career dossier.",
        },
    ]


def _site_nav(prefix: str, current: str) -> str:
    active_key = {
        "home": "rankings",
        "rankings": "rankings",
        "heisman": "heisman",
        "players": "players",
        "player": "players",
        "programs": "programs",
        "history": "history",
        "about": "model",
        "team": "teams",
        "compare": "analysis",
        "conferences": "analysis",
        "archive": "archive",
        "matchups": "matchups",
    }.get(current, current)
    links = [
        ("rankings", "Power Rankings", f"{prefix}rankings/index.html"),
        ("teams", "Teams", f"{prefix}teams/index.html"),
        ("players", "Players", f"{prefix}players/spotlight.html"),
        ("heisman", "Heisman", f"{prefix}heisman/index.html"),
        ("programs", "Programs", f"{prefix}programs/index.html"),
        ("history", "History", f"{prefix}history/index.html"),
        ("model", "The Model", f"{prefix}about-model/index.html"),
        ("analysis", "Analysis", f"{prefix}conferences/index.html"),
        ("archive", "Weekly Archive", f"{prefix}archive/index.html"),
    ]
    rendered = "".join(
        f'<a class="nav-link{" is-current" if key == active_key else ""}" href="{href}">{label}</a>'
        for key, label, href in links
    )
    return (
        f'<a class="skip-link" href="#main-content">Skip to main content</a>'
        f'<header class="topbar">'
        f'<a class="brand" href="{prefix}index.html">THE CFB INDEX</a>'
        f'<button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav-links" aria-label="Toggle navigation menu">Menu</button>'
        f'<div class="topbar-panels">'
        f'<nav class="nav" id="site-nav-links">{rendered}</nav>'
        f'<div class="nav-actions">'
        f'<a class="nav-action{" is-current" if active_key == "matchups" else ""}" href="{prefix}matchups/index.html">Matchup Simulator</a>'
        f'<a class="nav-action{" is-current" if active_key == "compare" else ""}" href="{prefix}compare/index.html">Compare Teams</a>'
        f"</div>"
        f"</div>"
        f"</header>"
        """
        <script>
          (() => {
            const topbars = Array.from(document.querySelectorAll('.topbar'));
            topbars.forEach((topbar) => {
              const toggle = topbar.querySelector('.nav-toggle');
              if (!toggle || toggle.dataset.bound === 'true') return;
              toggle.dataset.bound = 'true';
              const close = () => {
                topbar.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
              };
              toggle.addEventListener('click', () => {
                const isOpen = topbar.classList.toggle('is-open');
                toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
              });
              topbar.querySelectorAll('a').forEach((link) => {
                link.addEventListener('click', close);
              });
              document.addEventListener('click', (event) => {
                if (!topbar.contains(event.target)) {
                  close();
                }
              });
              window.addEventListener('resize', () => {
                if (window.innerWidth > 860) {
                  close();
                }
              });
            });
          })();
        </script>
        """
    )


def _render_rankings_row(row: RankingRow) -> str:
    conference = _clean_conference_name(str(row.conference_name or f"{row.level_code} Independents"))
    delta_class = _rank_change_class(row.rank_change)
    delta_text = _rank_change_text(row.rank_change)
    search_blob = escape(f"{row.team_name} {conference} {row.level_code}".lower())
    return f"""
    <tr data-rank="{row.rank}" data-power="{float(row.power_display or 0.0):.4f}" data-resume="{float(row.resume_display or 0.0):.4f}" data-team="{escape(row.team_name.lower())}" data-level="{escape(row.level_code)}" data-conference="{escape(conference)}" data-search="{search_blob}">
      <td class="rank-cell">#{row.rank}</td>
      <td class="metric-cell"><span class="rank-delta {delta_class}">{escape(delta_text)}</span></td>
      <td><a class="team-link" href="../teams/{escape(row.slug)}.html">{escape(row.team_name)}</a><span class="submetric">{escape(conference)}</span></td>
      <td><span class="pill level-{escape(row.level_code)}">{escape(row.level_code)}</span></td>
      <td class="metric-cell">{_public_power_text(row.power_display)}</td>
      <td class="metric-cell">{_public_resume_text(row.resume_display)}</td>
    </tr>
    """


def _render_schedule_row(team_id: int, row: dict[str, Any]) -> str:
    is_home = int(row["home_team_id"]) == team_id
    opponent_name = str(row["away_team_name"] if is_home else row["home_team_name"])
    opponent_slug = str(row["away_slug"] if is_home else row["home_slug"])
    team_points = row["home_points"] if is_home else row["away_points"]
    opp_points = row["away_points"] if is_home else row["home_points"]
    location = "vs" if is_home else "@"
    result = "Scheduled"
    if team_points is not None and opp_points is not None:
        result_prefix = "W" if int(team_points) > int(opp_points) else "L" if int(team_points) < int(opp_points) else "T"
        result = f"{result_prefix} {team_points}-{opp_points}"

    power_cell = _signed_metric_text(row.get("power_delta"))
    resume_cell = _signed_metric_text(row.get("resume_delta"))
    pre_cell = _metric_text(row.get("pregame_power"))
    post_cell = _metric_text(row.get("postgame_power"))
    line_cell = _format_spread_text(row.get("team_spread_close"))
    ats_cell = str(row.get("ats_result") or "--")
    total_cell = "--"
    if row.get("total_close") is not None:
        total_cell = f"{_format_total_text(row.get('total_close'))} | {str(row.get('total_result') or '--')}"
    phase = _phase_display_label(row.get("season_phase"))
    game_date = _format_game_date(row.get("start_time_utc"))
    return f"""
    <tr>
      <td>{escape(str(row.get("week") or "--"))}</td>
      <td>{escape(game_date)}</td>
      <td><span class="game-prefix">{location}</span> {_team_link("", opponent_slug, opponent_name)} <span class="submetric">{escape(str(row.get('opponent_level_code') or ''))}</span></td>
      <td>{escape(phase)}</td>
      <td>{escape(result)}</td>
      <td class="metric-cell">{escape(line_cell)}</td>
      <td class="metric-cell">{escape(ats_cell)}</td>
      <td class="metric-cell">{escape(total_cell)}</td>
      <td class="metric-cell">{escape(pre_cell)}</td>
      <td class="metric-cell">{escape(power_cell)}</td>
      <td class="metric-cell">{escape(resume_cell)}</td>
      <td class="metric-cell">{escape(post_cell)}</td>
    </tr>
    """


def _history_explorer_script() -> str:
    return """
      (() => {
        const rows = Array.from(document.querySelectorAll('#historyExplorerBody tr.history-explorer-row'));
        if (!rows.length) return;

        const searchInput = document.getElementById('historyExplorerSearch');
        const levelFilter = document.getElementById('historyExplorerLevelFilter');
        const conferenceFilter = document.getElementById('historyExplorerConferenceFilter');
        const sortMode = document.getElementById('historyExplorerSort');
        const clearButton = document.getElementById('clearHistoryExplorerFilters');
        const countNode = document.getElementById('historyExplorerCount');
        const chipRow = document.getElementById('historyExplorerActiveFilterRow');
        const tableBody = document.getElementById('historyExplorerBody');

        const normalized = (value) => (value || '').toString().trim().toLowerCase();
        const numericValue = (row, key, fallback) => {
          const raw = row.dataset[key];
          if (raw === undefined || raw === null || raw === '') return fallback;
          const parsed = Number(raw);
          return Number.isFinite(parsed) ? parsed : fallback;
        };
        const teamName = (row) => normalized(row.dataset.team || '');

        const sorters = {
          'season-desc': (a, b) => numericValue(b, 'season', 0) - numericValue(a, 'season', 0) || teamName(a).localeCompare(teamName(b)),
          'power-desc': (a, b) => numericValue(b, 'power', Number.NEGATIVE_INFINITY) - numericValue(a, 'power', Number.NEGATIVE_INFINITY) || teamName(a).localeCompare(teamName(b)),
          'resume-desc': (a, b) => numericValue(b, 'resume', Number.NEGATIVE_INFINITY) - numericValue(a, 'resume', Number.NEGATIVE_INFINITY) || teamName(a).localeCompare(teamName(b)),
          'rank-asc': (a, b) => numericValue(a, 'rank', Number.POSITIVE_INFINITY) - numericValue(b, 'rank', Number.POSITIVE_INFINITY) || teamName(a).localeCompare(teamName(b)),
          'winpct-desc': (a, b) => numericValue(b, 'winpct', Number.NEGATIVE_INFINITY) - numericValue(a, 'winpct', Number.NEGATIVE_INFINITY) || teamName(a).localeCompare(teamName(b)),
          'margin-desc': (a, b) => numericValue(b, 'margin', Number.NEGATIVE_INFINITY) - numericValue(a, 'margin', Number.NEGATIVE_INFINITY) || teamName(a).localeCompare(teamName(b)),
          team: (a, b) => teamName(a).localeCompare(teamName(b)) || numericValue(b, 'season', 0) - numericValue(a, 'season', 0),
        };

        function renderChips(tokens) {
          if (!chipRow) return;
          chipRow.innerHTML = '';
          chipRow.hidden = !tokens.length;
          tokens.forEach((token) => {
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            chip.textContent = token;
            chipRow.appendChild(chip);
          });
        }

        function applyState() {
          const query = normalized(searchInput?.value);
          const level = levelFilter?.value || 'ALL';
          const conference = conferenceFilter?.value || 'ALL';
          const sorter = sorters[sortMode?.value] || sorters['season-desc'];

          const filtered = rows.filter((row) => {
            const matchesQuery = !query || (row.dataset.search || '').includes(query);
            const matchesLevel = level === 'ALL' || row.dataset.level === level;
            const matchesConference = conference === 'ALL' || row.dataset.conference === conference;
            return matchesQuery && matchesLevel && matchesConference;
          }).sort(sorter);

          filtered.forEach((row) => tableBody.appendChild(row));
          const visible = new Set(filtered);
          rows.forEach((row) => {
            row.hidden = !visible.has(row);
          });
          if (countNode) countNode.textContent = String(filtered.length);

          const chips = [];
          if (query) chips.push(`Search: ${searchInput.value.trim()}`);
          if (level !== 'ALL') chips.push(`Level: ${level}`);
          if (conference !== 'ALL') chips.push(`Conference: ${conference}`);
          if (sortMode?.value && sortMode.value !== 'season-desc') {
            const option = sortMode.options[sortMode.selectedIndex];
            if (option?.textContent) chips.push(`Sort: ${option.textContent}`);
          }
          renderChips(chips);
        }

        [searchInput, levelFilter, conferenceFilter, sortMode].forEach((node) => {
          if (!node) return;
          node.addEventListener('input', applyState);
          node.addEventListener('change', applyState);
        });

        if (clearButton) {
          clearButton.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (levelFilter) levelFilter.value = 'ALL';
            if (conferenceFilter) conferenceFilter.value = 'ALL';
            if (sortMode) sortMode.value = 'season-desc';
            applyState();
          });
        }

        applyState();
      })();
    """


def _program_page_script() -> str:
    return """
      (() => {
        const navLinks = Array.from(document.querySelectorAll('[data-player-nav-target]'));
        const sections = Array.from(document.querySelectorAll('.player-anchor-section[id]'));
        if (navLinks.length && sections.length) {
          const setActive = (id) => {
            navLinks.forEach((link) => {
              link.classList.toggle('is-active', link.dataset.playerNavTarget === id);
            });
          };
          const observer = new IntersectionObserver((entries) => {
            const visible = entries
              .filter((entry) => entry.isIntersecting)
              .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
            if (visible?.target?.id) setActive(visible.target.id);
          }, { rootMargin: '-20% 0px -55% 0px', threshold: [0.15, 0.35, 0.6] });
          sections.forEach((section) => observer.observe(section));
          navLinks.forEach((link) => {
            link.addEventListener('click', () => setActive(link.dataset.playerNavTarget || ''));
          });
        }

        const rows = Array.from(document.querySelectorAll('#programSeasonExplorerBody tr.program-season-row'));
        if (!rows.length) return;

        const searchInput = document.getElementById('programSeasonSearch');
        const conferenceFilter = document.getElementById('programSeasonConferenceFilter');
        const lensFilter = document.getElementById('programSeasonLensFilter');
        const sortMode = document.getElementById('programSeasonSort');
        const clearButton = document.getElementById('clearProgramSeasonFilters');
        const countNode = document.getElementById('programSeasonVisibleCount');
        const chipRow = document.getElementById('programSeasonActiveFilterRow');
        const tableBody = document.getElementById('programSeasonExplorerBody');

        const normalized = (value) => (value || '').toString().trim().toLowerCase();
        const numericValue = (row, key, fallback) => {
          const raw = row.dataset[key];
          if (raw === undefined || raw === null || raw === '') return fallback;
          const parsed = Number(raw);
          return Number.isFinite(parsed) ? parsed : fallback;
        };
        const sorters = {
          'season-desc': (a, b) => numericValue(b, 'season', 0) - numericValue(a, 'season', 0),
          'power-desc': (a, b) => numericValue(b, 'power', Number.NEGATIVE_INFINITY) - numericValue(a, 'power', Number.NEGATIVE_INFINITY) || numericValue(b, 'season', 0) - numericValue(a, 'season', 0),
          'resume-desc': (a, b) => numericValue(b, 'resume', Number.NEGATIVE_INFINITY) - numericValue(a, 'resume', Number.NEGATIVE_INFINITY) || numericValue(b, 'season', 0) - numericValue(a, 'season', 0),
          'rank-asc': (a, b) => numericValue(a, 'rank', Number.POSITIVE_INFINITY) - numericValue(b, 'rank', Number.POSITIVE_INFINITY) || numericValue(b, 'season', 0) - numericValue(a, 'season', 0),
          'margin-desc': (a, b) => numericValue(b, 'margin', Number.NEGATIVE_INFINITY) - numericValue(a, 'margin', Number.NEGATIVE_INFINITY) || numericValue(b, 'season', 0) - numericValue(a, 'season', 0),
          'wins-desc': (a, b) => numericValue(b, 'wins', Number.NEGATIVE_INFINITY) - numericValue(a, 'wins', Number.NEGATIVE_INFINITY) || numericValue(b, 'season', 0) - numericValue(a, 'season', 0),
        };

        function renderChips(tokens) {
          if (!chipRow) return;
          chipRow.innerHTML = '';
          chipRow.hidden = !tokens.length;
          tokens.forEach((token) => {
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            chip.textContent = token;
            chipRow.appendChild(chip);
          });
        }

        function applyState() {
          const query = normalized(searchInput?.value);
          const conference = conferenceFilter?.value || 'ALL';
          const lens = lensFilter?.value || 'ALL';
          const sorter = sorters[sortMode?.value] || sorters['season-desc'];

          const filtered = rows.filter((row) => {
            const matchesQuery = !query || (row.dataset.search || '').includes(query);
            const matchesConference = conference === 'ALL' || row.dataset.conference === conference;
            const matchesLens = lens === 'ALL' || row.dataset.lens === lens;
            return matchesQuery && matchesConference && matchesLens;
          }).sort(sorter);

          filtered.forEach((row) => tableBody.appendChild(row));
          const visible = new Set(filtered);
          rows.forEach((row) => {
            row.hidden = !visible.has(row);
          });
          if (countNode) countNode.textContent = String(filtered.length);

          const chips = [];
          if (query) chips.push(`Search: ${searchInput.value.trim()}`);
          if (conference !== 'ALL') chips.push(`Conference: ${conference}`);
          if (lens !== 'ALL') chips.push(`Lens: ${lens}`);
          if (sortMode?.value && sortMode.value !== 'season-desc') {
            const option = sortMode.options[sortMode.selectedIndex];
            if (option?.textContent) chips.push(`Sort: ${option.textContent}`);
          }
          renderChips(chips);
        }

        [searchInput, conferenceFilter, lensFilter, sortMode].forEach((node) => {
          if (!node) return;
          node.addEventListener('input', applyState);
          node.addEventListener('change', applyState);
        });

        if (clearButton) {
          clearButton.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (conferenceFilter) conferenceFilter.value = 'ALL';
            if (lensFilter) lensFilter.value = 'ALL';
            if (sortMode) sortMode.value = 'season-desc';
            applyState();
          });
        }

        applyState();
      })();
    """


def _render_history_row_context(row: dict[str, Any], history_profile: dict[str, Any]) -> tuple[str, str]:
    season_year = int(row.get("season_year") or 0)
    current_row = history_profile.get("current_row") or {}
    peak_power_row = history_profile.get("peak_power_row") or {}
    best_resume_row = history_profile.get("best_resume_row") or {}
    best_finish_row = history_profile.get("best_finish_row") or {}
    best_record_row = history_profile.get("best_record_row") or {}
    baseline_power = history_profile.get("baseline_power")
    end_power = _first_present_float(row.get("end_power_display"), row.get("end_power"))

    if season_year and int(current_row.get("season_year") or 0) == season_year:
        return "Current", "This season anchors the current board."
    if season_year and int(peak_power_row.get("season_year") or 0) == season_year:
        return "Peak power", "Strongest loaded closing power for the program."
    if season_year and int(best_resume_row.get("season_year") or 0) == season_year:
        return "Best resume", "Best body-of-work season in the loaded archive."
    if season_year and int(best_finish_row.get("season_year") or 0) == season_year:
        return "Best finish", "Highest loaded final board finish."
    if season_year and int(best_record_row.get("season_year") or 0) == season_year:
        return "Best record", "Cleanest win-loss season in the loaded archive."
    if end_power is not None and baseline_power is not None:
        if end_power >= float(baseline_power) + 1.5:
            return "Above standard", "Closed comfortably above the program's recent baseline."
        if end_power <= float(baseline_power) - 1.5:
            return "Down year", "Finished meaningfully below the program's recent standard."
    return "In range", "A season that landed inside the normal historical band."


def _render_team_betting_overview(team_data: dict[str, Any]) -> str:
    ranking: RankingRow = team_data["ranking"]
    betting = team_data.get("betting_summary") or {}
    if not betting.get("games_with_lines"):
        return '<p class="footer-note">Market summaries will appear after more CFBD line data is loaded for this team.</p>'
    best_cover = betting.get("best_cover") or {}
    worst_burn = betting.get("worst_burn") or {}
    total_surprise = betting.get("biggest_total_miss") or {}
    return f"""
      <div class="stat-grid">
        <article class="stat-card"><span>ATS</span><strong>{int(betting.get('ats_wins') or 0)}-{int(betting.get('ats_losses') or 0)}-{int(betting.get('ats_pushes') or 0)}</strong><span class="submetric">{escape(_probability_text(betting.get('cover_rate')))} cover rate</span></article>
        <article class="stat-card"><span>Totals</span><strong>{int(betting.get('overs') or 0)} over / {int(betting.get('unders') or 0)} under</strong><span class="submetric">{int(betting.get('total_pushes') or 0)} pushes</span></article>
        <article class="stat-card"><span>Wins vs Market</span><strong>{float(betting.get('wins_above_market') or 0.0):+.2f}</strong><span class="submetric">{int(betting.get('actual_wins_lined') or 0)} actual wins vs {float(betting.get('expected_wins') or 0.0):.2f} expected</span></article>
        <article class="stat-card"><span>As Favorite</span><strong>{int(betting.get('favorite_ats_wins') or 0)}-{int(betting.get('favorite_ats_losses') or 0)}-{int(betting.get('favorite_ats_pushes') or 0)}</strong><span class="submetric">{int(betting.get('favorite_games') or 0)} favorite spots</span></article>
        <article class="stat-card"><span>As Underdog</span><strong>{int(betting.get('underdog_ats_wins') or 0)}-{int(betting.get('underdog_ats_losses') or 0)}-{int(betting.get('underdog_ats_pushes') or 0)}</strong><span class="submetric">{int(betting.get('underdog_games') or 0)} underdog spots</span></article>
        <article class="stat-card"><span>Provider Mix</span><strong>{escape(str(betting.get('provider_text') or 'CFBD lines'))}</strong><span class="submetric">{int(betting.get('games_with_lines') or 0)} lined games for {escape(ranking.team_name)}</span></article>
      </div>
      <div class="feature-grid team-story-grid">
        <article class="feature-card story-card">
          <span class="feature-rank">Best Cover</span>
          <h3>Week {int(best_cover.get('week') or 0)} vs {escape(str(best_cover.get('opponent_name') or '--'))}</h3>
          <p>{escape(str(best_cover.get('ats_result') or '--'))} by {escape(_signed_metric_text(best_cover.get('ats_margin')))} against a closing line of {escape(_format_spread_text(best_cover.get('team_spread_close')))}.</p>
        </article>
        <article class="feature-card story-card">
          <span class="feature-rank">Worst Burn</span>
          <h3>Week {int(worst_burn.get('week') or 0)} vs {escape(str(worst_burn.get('opponent_name') or '--'))}</h3>
          <p>{escape(str(worst_burn.get('ats_result') or '--'))} by {escape(_signed_metric_text(worst_burn.get('ats_margin')))}. These are the losses bettors remember.</p>
        </article>
        <article class="feature-card story-card">
          <span class="feature-rank">Biggest Total Miss</span>
          <h3>Week {int(total_surprise.get('week') or 0)} vs {escape(str(total_surprise.get('opponent_name') or '--'))}</h3>
          <p>{escape(str(total_surprise.get('total_result') or '--'))} versus {escape(_format_total_text(total_surprise.get('total_close')))} by {escape(_signed_metric_text(total_surprise.get('total_margin')))} points.</p>
        </article>
      </div>
    """


def _render_team_betting_table(team_id: int, schedule: list[dict[str, Any]], limit: int = 8) -> str:
    lined_rows = [
        row
        for row in schedule
        if row.get("team_spread_close") is not None or row.get("total_close") is not None or row.get("team_moneyline_close") is not None
    ]
    if not lined_rows:
        return '<p class="footer-note">No lined games are attached to this team yet.</p>'
    rows: list[str] = []
    for row in list(reversed(lined_rows))[:limit]:
        is_home = int(row["home_team_id"]) == team_id
        opponent_name = str(row["away_team_name"] if is_home else row["home_team_name"])
        opponent_slug = str(row["away_slug"] if is_home else row["home_slug"])
        location = "vs" if is_home else "@"
        result = "Scheduled"
        if row.get("home_points") is not None and row.get("away_points") is not None:
            team_points = int(row["home_points"] if is_home else row["away_points"])
            opp_points = int(row["away_points"] if is_home else row["home_points"])
            prefix = "W" if team_points > opp_points else "L" if team_points < opp_points else "T"
            result = f"{prefix} {team_points}-{opp_points}"
        total_result = str(row.get("total_result") or "--")
        total_cell = "--" if row.get("total_close") is None else f"{_format_total_text(row.get('total_close'))} | {total_result}"
        rows.append(
            f"""
            <tr>
              <td>{escape(str(row.get('week') or '--'))}</td>
              <td><span class="game-prefix">{location}</span> {_team_link("../teams/", opponent_slug, opponent_name)}</td>
              <td class="metric-cell">{escape(result)}</td>
              <td class="metric-cell">{escape(_format_spread_text(row.get('team_spread_close')))}</td>
              <td class="metric-cell">{escape(str(row.get('ats_result') or '--'))}</td>
              <td class="metric-cell">{escape(total_cell)}</td>
              <td class="metric-cell">{escape(_format_moneyline_text(row.get('team_moneyline_close')))}</td>
            </tr>
            """
        )
    return f"""
      <div class="table-wrap compact-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Week</th>
              <th>Game</th>
              <th>Result</th>
              <th>Close</th>
              <th>ATS</th>
              <th>Total</th>
              <th>ML</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>
    """


def _render_history_row(row: dict[str, Any], history_profile: dict[str, Any]) -> str:
    points_for = int(row.get("points_for") or 0)
    points_against = int(row.get("points_against") or 0)
    margin = points_for - points_against
    end_power = row.get("end_power_display")
    end_resume = row.get("end_resume_display")
    lens_label, lens_body = _render_history_row_context(row, history_profile)
    return f"""
    <tr>
      <td>{escape(str(row.get("season_year") or ""))}</td>
      <td>{escape(lens_label)}<span class="submetric">{escape(lens_body)}</span></td>
      <td>{int(row.get("wins") or 0)}-{int(row.get("losses") or 0)}</td>
      <td>#{escape(_display_rank_value(row.get("final_rank")))}</td>
      <td>{escape(_public_power_text(end_power))}</td>
      <td>{escape(_public_resume_text(end_resume))}</td>
      <td>{int(row.get("games_played") or 0)}</td>
      <td>{points_for}</td>
      <td>{points_against}</td>
      <td>{margin:+d}</td>
    </tr>
    """


def _render_phase_row(row: dict[str, Any]) -> str:
    return f"""
    <tr>
      <td>{escape(_phase_display_label(row.get("season_phase")))}</td>
      <td>{int(row.get("wins") or 0)}-{int(row.get("losses") or 0)}</td>
      <td>{int(row.get("games_played") or 0)}</td>
    </tr>
    """


def _journey_axis_label(week_value: int, phase_label: str) -> str:
    normalized_phase = phase_label.strip().lower()
    if week_value <= 0:
        return "Start"
    if "conference championship" in normalized_phase:
        return "CCG"
    if "playoff" in normalized_phase:
        return "CFP"
    if "bowl" in normalized_phase:
        return "Bowl"
    if "final" in normalized_phase:
        return "Final"
    return f"W{week_value}"


def _build_team_journey_points(team_id: int, schedule_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    journey_points: list[dict[str, Any]] = []
    preseason_added = False
    for row in schedule_rows:
        pre = _optional_float(row.get("pregame_power"))
        post = _optional_float(row.get("postgame_power"))
        delta = _optional_float(row.get("power_delta"))
        if not preseason_added and pre is not None:
            preseason_added = True
            journey_points.append(
                {
                    "kind": "start",
                    "week": 0,
                    "week_label": "Preseason",
                    "axis_label": "Start",
                    "phase": "Preseason",
                    "date": "Preseason",
                    "location": "",
                    "opponent_name": "Opening baseline",
                    "opponent_slug": "",
                    "opponent_level_code": "",
                    "game_label": "Preseason baseline",
                    "result": "Baseline",
                    "score": "No game played",
                    "delta": None,
                    "pre": pre,
                    "post": pre,
                    "rating": pre,
                    "tone": "start",
                }
            )
        if post is None:
            continue

        is_home = int(row["home_team_id"]) == team_id
        opponent_name = str(row["away_team_name"] if is_home else row["home_team_name"])
        opponent_slug = str(row["away_slug"] if is_home else row["home_slug"])
        location = "vs" if is_home else "@"
        team_points = row["home_points"] if is_home else row["away_points"]
        opp_points = row["away_points"] if is_home else row["home_points"]
        if team_points is None or opp_points is None:
            result_label = "Scheduled"
            score_text = "No final yet"
        elif int(team_points) > int(opp_points):
            result_label = "Win"
            score_text = f"{int(team_points)}-{int(opp_points)}"
        elif int(team_points) < int(opp_points):
            result_label = "Loss"
            score_text = f"{int(team_points)}-{int(opp_points)}"
        else:
            result_label = "Tie"
            score_text = f"{int(team_points)}-{int(opp_points)}"
        phase_label = _phase_display_label(row.get("season_phase"))
        if delta is None:
            tone = "flat"
        elif delta > 0:
            tone = "up"
        elif delta < 0:
            tone = "down"
        else:
            tone = "flat"
        week_value = int(row.get("week") or 0)
        journey_points.append(
            {
                "kind": "game",
                "week": week_value,
                "week_label": f"Week {week_value}",
                "axis_label": _journey_axis_label(week_value, phase_label),
                "phase": phase_label,
                "date": _format_game_date(row.get("start_time_utc")),
                "location": location,
                "opponent_name": opponent_name,
                "opponent_slug": opponent_slug,
                "opponent_level_code": str(row.get("opponent_level_code") or ""),
                "game_label": f"{location} {opponent_name}",
                "result": result_label,
                "score": score_text,
                "delta": delta,
                "pre": pre,
                "post": post,
                "rating": post,
                "tone": tone,
            }
        )
    return journey_points


def _team_journey_payload(journey_points: list[dict[str, Any]]) -> str:
    checkpoints = []
    for point in journey_points:
        rating = point.get("rating")
        if rating is None:
            continue
        checkpoints.append(
            {
                "kind": point.get("kind") or "game",
                "week": int(point.get("week") or 0),
                "week_label": str(point.get("week_label") or ""),
                "axis_label": str(point.get("axis_label") or ""),
                "phase": str(point.get("phase") or ""),
                "date": str(point.get("date") or ""),
                "location": str(point.get("location") or ""),
                "opponent_name": str(point.get("opponent_name") or ""),
                "opponent_slug": str(point.get("opponent_slug") or ""),
                "opponent_level_code": str(point.get("opponent_level_code") or ""),
                "game_label": str(point.get("game_label") or ""),
                "result": str(point.get("result") or ""),
                "score": str(point.get("score") or ""),
                "delta": None if point.get("delta") is None else float(point.get("delta") or 0.0),
                "pre": None if point.get("pre") is None else float(point.get("pre") or 0.0),
                "post": None if point.get("post") is None else float(point.get("post") or 0.0),
                "rating": float(rating or 0.0),
                "tone": str(point.get("tone") or "flat"),
            }
        )
    payload = {"checkpoints": checkpoints, "defaultIndex": max(0, len(checkpoints) - 1)}
    return json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")


def _render_team_journey_highlights(journey_points: list[dict[str, Any]]) -> str:
    game_points = [point for point in journey_points if point.get("kind") == "game" and point.get("delta") is not None]
    if not game_points:
        return ""
    ranked = sorted(
        game_points,
        key=lambda point: (
            -abs(float(point.get("delta") or 0.0)),
            -float(point.get("post") or point.get("rating") or 0.0),
            int(point.get("week") or 0),
        ),
    )
    cards = []
    for index, point in enumerate(ranked[:3], start=1):
        delta_value = float(point.get("delta") or 0.0)
        opponent_name = str(point.get("opponent_name") or "Opponent")
        location = str(point.get("location") or "")
        week_label = str(point.get("week_label") or "")
        label = "Biggest rise" if delta_value > 0 and index == 1 else "Biggest hit" if delta_value < 0 and index == 1 else f"Swing #{index}"
        score = str(point.get("score") or "")
        cards.append(
            f"""
            <article class="journey-highlight-card">
              <span class="journey-highlight-kicker">{escape(label)}</span>
              <strong>{escape(_signed_metric_text(delta_value))}</strong>
              <p>{escape(week_label)} · {escape(location)} {escape(opponent_name)}</p>
              <span class="journey-highlight-meta">{escape(point.get("result") or "")}{escape(f' {score}' if score else '')}{escape(f' · {point.get("opponent_level_code")}' if point.get("opponent_level_code") else '')}</span>
            </article>
            """
        )
    return f'<div class="journey-highlight-row">{"".join(cards)}</div>'


def _render_team_journey_chart(journey_points: list[dict[str, Any]]) -> str:
    visible_points = [point for point in journey_points if point.get("rating") is not None]
    if len(visible_points) < 2:
        return '<p class="footer-note">Not enough completed game checkpoints yet to draw the season journey.</p>'

    payload = _team_journey_payload(visible_points)
    highlights = _render_team_journey_highlights(visible_points)
    return f"""
    <div class="team-journey" data-team-journey>
      <div class="journey-topline">
        <div>
          <h3>Season Rating Journey</h3>
          <p class="section-note">One line tells the story. Hover or tap any marker to see the exact game and how many power points it moved the rating. Larger markers mean bigger swings.</p>
        </div>
        <div class="journey-legend" aria-label="Season journey legend">
          <span class="journey-legend-item"><span class="journey-swatch up"></span> Rating rose</span>
          <span class="journey-legend-item"><span class="journey-swatch down"></span> Rating fell</span>
          <span class="journey-legend-item"><span class="journey-swatch flat"></span> Little movement</span>
          <span class="journey-legend-item"><span class="journey-swatch ring"></span> Ring shows opponent level</span>
        </div>
      </div>
      <div class="journey-frame">
        <svg id="teamJourneySvg" class="journey-svg" viewBox="0 0 860 360" role="img" aria-labelledby="teamJourneyTitle teamJourneyDesc">
          <title id="teamJourneyTitle">Season rating journey</title>
          <desc id="teamJourneyDesc">A single line chart of the team's rating path by game, with hoverable markers showing the swing from each result.</desc>
        </svg>
        <div id="teamJourneyMarkers" class="journey-marker-layer"></div>
        <div id="teamJourneyTooltip" class="journey-tooltip" hidden data-place="above">
          <span id="teamJourneyTooltipKicker" class="journey-tooltip-kicker"></span>
          <h4 id="teamJourneyTooltipTitle"></h4>
          <p id="teamJourneyTooltipMeta" class="journey-tooltip-meta"></p>
          <div class="journey-tooltip-grid">
            <div class="journey-tooltip-stat">
              <span>Result</span>
              <strong id="teamJourneyTooltipResult">--</strong>
            </div>
            <div class="journey-tooltip-stat">
              <span>Power Swing</span>
              <strong id="teamJourneyTooltipDelta">--</strong>
            </div>
            <div class="journey-tooltip-stat journey-tooltip-stat-wide">
              <span>Rating Path</span>
              <strong id="teamJourneyTooltipRating">--</strong>
            </div>
          </div>
        </div>
      </div>
      <div id="teamJourneyAxis" class="journey-axis-strip"></div>
      {highlights}
      <script id="teamJourneyPayload" type="application/json">{payload}</script>
    </div>
    """


def _render_weekly_delta_blocks(points: list[dict[str, Any]]) -> str:
    if not points:
        return '<p class="footer-note">No team delta history is available yet.</p>'

    bars = []
    for point in points:
        delta = point.get("delta")
        if delta is None:
            height = 18
            class_name = "delta-bar missing"
            label = "No model delta yet"
        else:
            height = int(min(100, max(18, abs(float(delta)) * 28)))
            class_name = "delta-bar positive" if float(delta) >= 0 else "delta-bar negative"
            label = f"{float(delta):+.2f}"
        bars.append(
            f"""
            <div class="delta-col">
              <div class="{class_name}" style="height:{height}px"></div>
              <span class="delta-week">W{int(point.get('week') or 0)}</span>
              <span class="delta-label">{escape(label)}</span>
            </div>
            """
        )
    return f'<div class="delta-grid">{"".join(bars)}</div>'


def _render_rating_path(values: list[float]) -> str:
    if len(values) < 2:
        return '<p class="footer-note">Not enough rating checkpoints yet to draw a path.</p>'

    width = 640
    height = 220
    padding = 18
    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 1.0)
    points = []
    for index, value in enumerate(values):
        x = padding + (index * (width - 2 * padding) / max(1, len(values) - 1))
        y = height - padding - ((value - min_value) / span) * (height - 2 * padding)
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    return f"""
    <svg class="rating-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Team rating path">
      <rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="rgba(255,255,255,0.45)"></rect>
      <polyline fill="none" stroke="#bf3b1f" stroke-width="4" points="{polyline}"></polyline>
    </svg>
    """


def _team_journey_script() -> str:
    return """
      (() => {
        const payloadNode = document.getElementById('teamJourneyPayload');
        const chart = document.querySelector('[data-team-journey]');
        if (!payloadNode || !chart) return;

        let payload = null;
        try {
          payload = JSON.parse(payloadNode.textContent || '{}');
        } catch (error) {
          console.error('Could not parse team journey payload', error);
          return;
        }

        const points = Array.isArray(payload.checkpoints) ? payload.checkpoints : [];
        if (points.length < 2) return;

        const svg = document.getElementById('teamJourneySvg');
        const markerLayer = document.getElementById('teamJourneyMarkers');
        const axis = document.getElementById('teamJourneyAxis');
        const tooltip = document.getElementById('teamJourneyTooltip');
        const kickerNode = document.getElementById('teamJourneyTooltipKicker');
        const titleNode = document.getElementById('teamJourneyTooltipTitle');
        const metaNode = document.getElementById('teamJourneyTooltipMeta');
        const resultNode = document.getElementById('teamJourneyTooltipResult');
        const deltaNode = document.getElementById('teamJourneyTooltipDelta');
        const ratingNode = document.getElementById('teamJourneyTooltipRating');
        if (!svg || !markerLayer || !axis || !tooltip || !kickerNode || !titleNode || !metaNode || !resultNode || !deltaNode || !ratingNode) return;

        const width = 860;
        const height = 360;
        const padding = { top: 28, right: 24, bottom: 54, left: 68 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;

        const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
        const formatPower = (value) => {
          const number = Number(value || 0);
          return `${number >= 0 ? '+' : ''}${number.toFixed(1)}`;
        };
        const escapeHtml = (value) => String(value || '')
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('\"', '&quot;')
          .replaceAll(\"'\", '&#39;');

        const ratings = points.map((point) => Number(point.rating || 0));
        let minValue = Math.min(...ratings);
        let maxValue = Math.max(...ratings);
        const rawSpan = Math.max(maxValue - minValue, 1.0);
        minValue -= rawSpan * 0.18;
        maxValue += rawSpan * 0.12;
        const span = Math.max(maxValue - minValue, 1.0);

        const xAt = (index) => padding.left + (points.length <= 1 ? plotWidth / 2 : (index * plotWidth) / (points.length - 1));
        const yAt = (value) => padding.top + ((maxValue - Number(value || 0)) / span) * plotHeight;

        const gridTicks = Array.from({ length: 5 }, (_, index) => minValue + (span * index) / 4);
        const pathPoints = points.map((point, index) => `${xAt(index).toFixed(1)},${yAt(point.rating).toFixed(1)}`);
        const linePath = pathPoints.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point}`).join(' ');
        const areaPath = `${linePath} L ${xAt(points.length - 1).toFixed(1)},${(height - padding.bottom).toFixed(1)} L ${xAt(0).toFixed(1)},${(height - padding.bottom).toFixed(1)} Z`;

        svg.innerHTML = `
          <defs>
            <linearGradient id="teamJourneyFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stop-color="var(--team-accent, #bf3b1f)" stop-opacity="0.24"></stop>
              <stop offset="100%" stop-color="var(--team-accent, #bf3b1f)" stop-opacity="0.02"></stop>
            </linearGradient>
          </defs>
          <rect x="0" y="0" width="${width}" height="${height}" rx="26" fill="rgba(255,255,255,0.52)"></rect>
          ${gridTicks.map((tick) => `
            <g>
              <line x1="${padding.left}" x2="${width - padding.right}" y1="${yAt(tick).toFixed(1)}" y2="${yAt(tick).toFixed(1)}" stroke="rgba(95,110,126,0.18)" stroke-dasharray="4 8"></line>
              <text x="${padding.left - 12}" y="${(yAt(tick) + 4).toFixed(1)}" text-anchor="end" fill="#667484" font-size="11" font-family="Arial, sans-serif">${escapeHtml(formatPower(tick))}</text>
            </g>
          `).join('')}
          <path d="${areaPath}" fill="url(#teamJourneyFill)"></path>
          <path d="${linePath}" fill="none" stroke="var(--team-accent, #bf3b1f)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"></path>
        `;

        const labelIndexes = new Set([0, points.length - 1]);
        [0.25, 0.5, 0.75].forEach((step) => {
          labelIndexes.add(Math.round((points.length - 1) * step));
        });
        axis.innerHTML = points
          .map((point, index) => {
            if (!labelIndexes.has(index)) return '';
            const left = ((xAt(index) / width) * 100).toFixed(2);
            return `<span class="journey-axis-label" style="left:${left}%">${escapeHtml(point.axis_label || '')}</span>`;
          })
          .join('');

        let pinnedIndex = clamp(Number(payload.defaultIndex || points.length - 1), 0, points.length - 1);

        function setTooltip(index) {
          const point = points[index];
          const marker = markerLayer.querySelector(`[data-journey-index="${index}"]`);
          if (!point || !marker) return;

          markerLayer.querySelectorAll('.journey-point').forEach((node) => {
            node.classList.toggle('is-selected', Number(node.dataset.journeyIndex || -1) === index);
          });

          const kicker = point.kind === 'start'
            ? 'Preseason baseline'
            : `${point.week_label || ''} · ${point.phase || ''}`.replace(/^ · | · $/g, '');
          kickerNode.textContent = kicker;
          titleNode.innerHTML = point.kind === 'start'
            ? 'Opening baseline'
            : `${escapeHtml(point.location || '')} <span>${escapeHtml(point.opponent_name || '')}</span>`;
          metaNode.textContent = point.kind === 'start'
            ? 'The rating before the first result of the season.'
            : `${point.date || ''} · ${point.result || ''}${point.score ? ` ${point.score}` : ''}${point.opponent_level_code ? ` · ${point.opponent_level_code}` : ''}`;
          resultNode.textContent = point.result || 'Baseline';
          deltaNode.textContent = point.delta === null || point.delta === undefined ? '--' : formatPower(point.delta);
          if (point.pre === null || point.pre === undefined || point.post === null || point.post === undefined) {
            ratingNode.textContent = formatPower(point.rating);
          } else {
            ratingNode.textContent = `${formatPower(point.pre)} → ${formatPower(point.post)}`;
          }

          const markerX = Number(marker.dataset.left || 50);
          const markerY = Number(marker.dataset.top || 50);
          const placeBelow = markerY < 28;
          tooltip.hidden = false;
          tooltip.dataset.place = placeBelow ? 'below' : 'above';
          tooltip.style.left = `${clamp(markerX, 14, 86)}%`;
          tooltip.style.top = `${placeBelow ? clamp(markerY + 14, 20, 78) : clamp(markerY - 14, 18, 82)}%`;
        }

        markerLayer.innerHTML = '';
        points.forEach((point, index) => {
          const x = xAt(index);
          const y = yAt(point.rating);
          const left = ((x / width) * 100).toFixed(2);
          const top = ((y / height) * 100).toFixed(2);
          const deltaMagnitude = Math.abs(Number(point.delta || 0));
          const size = point.kind === 'start' ? 12 : clamp(12 + deltaMagnitude * 5.2, 12, 24);
          const tone = point.kind === 'start' ? 'start' : (point.tone || 'flat');
          const opponentLevel = (point.opponent_level_code || 'NA').replace(/[^A-Z0-9]/g, '');
          const button = document.createElement('button');
          button.type = 'button';
          button.className = `journey-point ${tone} opp-${opponentLevel}`;
          button.style.left = `${left}%`;
          button.style.top = `${top}%`;
          button.style.setProperty('--point-size', `${size}px`);
          button.dataset.journeyIndex = String(index);
          button.dataset.left = left;
          button.dataset.top = top;
          button.setAttribute(
            'aria-label',
            point.kind === 'start'
              ? `Preseason baseline, ${formatPower(point.rating)}`
              : `${point.week_label || ''}, ${point.location || ''} ${point.opponent_name || ''}, ${point.result || ''}, swing ${point.delta === null || point.delta === undefined ? '--' : formatPower(point.delta)}`
          );
          button.title = point.kind === 'start' ? 'Preseason baseline' : `${point.week_label || ''} | ${point.location || ''} ${point.opponent_name || ''}`;
          button.addEventListener('mouseenter', () => setTooltip(index));
          button.addEventListener('focus', () => setTooltip(index));
          button.addEventListener('click', () => {
            pinnedIndex = index;
            setTooltip(index);
          });
          markerLayer.appendChild(button);
        });

        chart.addEventListener('mouseleave', () => setTooltip(pinnedIndex));
        setTooltip(pinnedIndex);
      })();
    """


def _render_count_cards() -> str:
    cards = []
    for key in ("FBS", "FCS", "DII", "DIII"):
        record = SUBDIVISION_PROGRAM_COUNTS[key]
        if key == "FBS":
            body = f"{record['active_full_members']} active/full-member programs, {record['with_transitioning']} including transitioners."
        elif key == "FCS":
            body = f"{record['active_full_members']} active/full-member programs, {record['broad_sponsoring_count']} on the broader NCAA sponsorship listing."
        else:
            body = f"{record['football_programs']} football programs."
        cards.append(
            f"""
            <article class="feature-card count-card">
              <span class="count-kicker">{escape(record['label'])}</span>
              <h3>{escape(body)}</h3>
            </article>
            """
        )
    return "".join(cards)


def _render_summary_cards(team_pages: list[dict[str, Any]], prefix: str = "teams/") -> str:
    top_window = team_pages[:40]
    if not top_window:
        return ""
    biggest_riser = max(top_window, key=lambda item: item["ranking"].rank_change)
    best_resume = max(top_window, key=lambda item: item["ranking"].resume_score)
    strongest_team = max(top_window, key=lambda item: item["ranking"].power_rating)
    leaderboard = [
        ("Biggest Riser", biggest_riser, _rank_change_text(biggest_riser["ranking"].rank_change)),
        ("Best Resume", best_resume, f'{_public_resume_text(best_resume["ranking"].resume_display)} / 100'),
        ("Strongest Team", strongest_team, _public_power_text(strongest_team["ranking"].power_display)),
    ]
    cards = []
    for label, team_data, value in leaderboard:
        row: RankingRow = team_data["ranking"]
        cards.append(
            f"""
            <a class="summary-card" href="{prefix}{escape(row.slug)}.html">
              <span class="summary-label">{escape(label)}</span>
              <strong>{escape(row.team_name)}</strong>
              <span class="summary-value">{escape(value)}</span>
              <span class="summary-detail">{escape(row.level_code)} team profile</span>
              <span class="summary-spark">{_sparkline(_trend_path_values(team_data))}</span>
            </a>
            """
        )
    return "".join(cards)


def _render_program_explorer_cards(explorer_rows: list[dict[str, Any]]) -> str:
    if not explorer_rows:
        return '<p class="footer-note">Program explorer cards will populate after more seasons are modeled.</p>'

    most_loaded = max(explorer_rows, key=lambda row: int(row.get("loaded_seasons") or 0))
    strongest_peak = max(
        [row for row in explorer_rows if row.get("peak_power") is not None],
        key=lambda row: float(row.get("peak_power") or 0.0),
        default=None,
    )
    hottest_now = max(
        [row for row in explorer_rows if row.get("current_vs_baseline") is not None],
        key=lambda row: float(row.get("current_vs_baseline") or 0.0),
        default=None,
    )
    closest_to_peak = min(
        [row for row in explorer_rows if row.get("gap_to_peak_power") is not None],
        key=lambda row: float(row.get("gap_to_peak_power") or 999.0),
        default=None,
    )

    cards: list[tuple[str, dict[str, Any] | None, str]] = [
        ("Deepest archive", most_loaded, f"{int(most_loaded.get('loaded_seasons') or 0)} loaded seasons"),
        (
            "Strongest peak",
            strongest_peak,
            "--"
            if strongest_peak is None
            else f"{_public_power_text(strongest_peak.get('peak_power_display'))} in {int(strongest_peak.get('peak_power_year') or 0)}",
        ),
        (
            "Best current over baseline",
            hottest_now,
            "--"
            if hottest_now is None
            else f"{_public_power_text(hottest_now.get('current_vs_baseline'))} vs standard",
        ),
        (
            "Closest to peak",
            closest_to_peak,
            "--"
            if closest_to_peak is None
            else f"{float(closest_to_peak.get('gap_to_peak_power') or 0.0):.1f} below peak",
        ),
    ]
    rendered: list[str] = []
    for label, row, detail in cards:
        if row is None:
            continue
        rendered.append(
            f"""
            <a class="feature-card story-card" href="{escape(str(row.get('slug') or ''))}.html">
              <span class="feature-rank">{escape(label)}</span>
              <h3>{escape(str(row.get("team_name") or ""))}</h3>
              <p>{escape(str(row.get("level_code") or ""))} | {escape(str(row.get("conference_name") or ""))}</p>
              <p class="story-tail">{escape(detail)}</p>
            </a>
            """
        )
    return "".join(rendered)


def _render_program_explorer_row(row: dict[str, Any]) -> str:
    search_blob = " ".join(
        [
            str(row.get("team_name") or ""),
            str(row.get("conference_name") or ""),
            str(row.get("level_code") or ""),
        ]
    ).lower()
    current_rank = row.get("current_rank")
    latest_power = _optional_float(row.get("latest_end_power_display"))
    peak_power = _optional_float(row.get("peak_power_display"))
    best_resume = _optional_float(row.get("best_resume_display"))
    current_vs_baseline = _optional_float(row.get("current_vs_baseline"))
    power_range = _optional_float(row.get("power_range")) or 0.0
    latest_power_attr = "" if latest_power is None else f"{latest_power:.4f}"
    peak_power_attr = "" if peak_power is None else f"{peak_power:.4f}"
    best_resume_attr = "" if best_resume is None else f"{best_resume:.4f}"
    current_vs_baseline_attr = "" if current_vs_baseline is None else f"{current_vs_baseline:.4f}"
    season_link = (
        f'<a class="text-link" href="{escape(str(row.get("current_season_url") or ""))}">Open {int(row.get("latest_season_year") or 0)}</a>'
        if row.get("current_season_url")
        else '<span class="submetric">Archive only</span>'
    )
    return f"""
    <tr
      class="program-explorer-row"
      data-search="{escape(search_blob)}"
      data-level="{escape(str(row.get('level_code') or ''))}"
      data-current-rank="{'' if current_rank is None else int(current_rank)}"
      data-latest-power="{latest_power_attr}"
      data-peak-power="{peak_power_attr}"
      data-best-resume="{best_resume_attr}"
      data-loaded-seasons="{int(row.get('loaded_seasons') or 0)}"
      data-current-vs-baseline="{current_vs_baseline_attr}"
      data-volatility="{power_range:.4f}"
    >
      <td><a class="team-link" href="{escape(str(row.get('slug') or ''))}.html">{escape(str(row.get("team_name") or ""))}</a><span class="submetric">{escape(str(row.get("level_code") or ""))} | {escape(str(row.get("conference_name") or ""))}</span></td>
      <td class="metric-cell">{escape("--" if current_rank is None else f"#{int(current_rank)}")}</td>
      <td>{int(row.get("latest_season_year") or 0)}<span class="submetric">{escape(str(row.get("latest_record") or "--"))}</span></td>
      <td class="metric-cell">{int(row.get("loaded_seasons") or 0)}</td>
      <td class="metric-cell">{escape(_public_power_text(peak_power))}<span class="submetric">{escape("--" if row.get("peak_power_year") is None else str(int(row.get("peak_power_year") or 0)))}</span></td>
      <td class="metric-cell">{escape(_public_resume_text(best_resume))}<span class="submetric">{escape("--" if row.get("best_resume_year") is None else str(int(row.get("best_resume_year") or 0)))}</span></td>
      <td class="metric-cell">{escape("--" if row.get("best_finish") is None else f"#{int(row.get('best_finish') or 0)}")}<span class="submetric">{escape("--" if row.get("best_finish_year") is None else str(int(row.get("best_finish_year") or 0)))}</span></td>
      <td class="metric-cell">{escape(_public_power_text(current_vs_baseline))}</td>
      <td class="metric-cell">{power_range:.2f}</td>
      <td>{season_link}</td>
    </tr>
    """


def _render_program_conference_timeline(timeline: dict[str, Any]) -> str:
    segments = timeline.get("segments") or []
    if not segments:
        return '<p class="footer-note">Conference-era cards will appear after season-specific memberships are loaded.</p>'
    cards = []
    for segment in segments:
        start_season = int(segment.get("start_season") or 0)
        end_season = int(segment.get("end_season") or 0)
        season_span = str(start_season) if start_season == end_season else f"{start_season}-{end_season}"
        cards.append(
            f"""
            <article class="feature-card story-card conference-era-card">
              <span class="feature-rank">{escape(str(segment.get("level_code") or ""))}</span>
              <h3>{escape(str(segment.get("conference_name") or ""))}</h3>
              <p>{escape(season_span)}</p>
              <p class="story-tail">{int(segment.get("season_count") or 0)} seasons</p>
            </article>
            """
        )
    return f"""
    <div class="phase-pill-row">
      <span class="mini-chip">Conference eras {len(segments)}</span>
      <span class="mini-chip">Realignments {int(timeline.get("realignment_count") or 0)}</span>
    </div>
    <div class="feature-grid conference-timeline-grid">
      {''.join(cards)}
    </div>
    """


def _render_program_history_row(
    row: dict[str, Any],
    history_profile: dict[str, Any],
    current_season_url: str | None = None,
) -> str:
    conference = _clean_conference_name(str(row.get("conference_name") or f"{row.get('level_code') or ''} Independents"))
    lens_label, lens_body = _render_history_row_context(row, history_profile)
    current_row = history_profile.get("current_row") or {}
    is_current = int(current_row.get("season_year") or 0) == int(row.get("season_year") or 0)
    season_link = (
        f'<a class="text-link" href="{escape(current_season_url)}">Open season page</a>'
        if is_current and current_season_url
        else '<span class="submetric">Program view</span>'
    )
    return f"""
    <tr>
      <td>{int(row.get("season_year") or 0)}</td>
      <td>{escape(conference)}<span class="submetric">{escape(str(row.get("level_code") or ""))}</span></td>
      <td>{escape(lens_label)}<span class="submetric">{escape(lens_body)}</span></td>
      <td>{int(row.get("wins") or 0)}-{int(row.get("losses") or 0)}</td>
      <td>#{escape(_display_rank_value(row.get("final_rank")))}</td>
      <td>{escape(_public_power_text(row.get("end_power_display")))}</td>
      <td>{escape(_public_resume_text(row.get("end_resume_display")))}</td>
      <td>{int(row.get("margin") or 0):+d}</td>
      <td>{season_link}</td>
    </tr>
    """


def _render_program_season_explorer_row(
    row: dict[str, Any],
    history_profile: dict[str, Any],
    current_season_url: str | None = None,
) -> str:
    conference = _clean_conference_name(str(row.get("conference_name") or f"{row.get('level_code') or ''} Independents"))
    lens_label, lens_body = _render_history_row_context(row, history_profile)
    current_row = history_profile.get("current_row") or {}
    is_current = int(current_row.get("season_year") or 0) == int(row.get("season_year") or 0)
    season_link = (
        f'<a class="text-link" href="{escape(current_season_url)}">Open season page</a>'
        if is_current and current_season_url
        else '<span class="submetric">Program view</span>'
    )
    end_power = _first_present_float(row.get("end_power_display"), row.get("end_power"))
    end_resume = _first_present_float(row.get("end_resume_display"), row.get("end_resume"))
    final_rank = row.get("final_rank")
    search_blob = " ".join(
        [
            str(row.get("season_year") or ""),
            conference,
            str(row.get("level_code") or ""),
            lens_label,
            lens_body,
        ]
    ).lower()
    return f"""
    <tr
      class="program-season-row"
      data-search="{escape(search_blob)}"
      data-season="{int(row.get('season_year') or 0)}"
      data-conference="{escape(conference)}"
      data-lens="{escape(lens_label)}"
      data-power="{'' if end_power is None else f'{float(end_power):.4f}'}"
      data-resume="{'' if end_resume is None else f'{float(end_resume):.4f}'}"
      data-rank="{'' if final_rank is None else int(final_rank)}"
      data-margin="{int(row.get('margin') or 0)}"
      data-wins="{int(row.get('wins') or 0)}"
    >
      <td>{int(row.get("season_year") or 0)}</td>
      <td>{escape(conference)}<span class="submetric">{escape(str(row.get("level_code") or ""))}</span></td>
      <td>{escape(lens_label)}<span class="submetric">{escape(lens_body)}</span></td>
      <td>{int(row.get("wins") or 0)}-{int(row.get("losses") or 0)}</td>
      <td>#{escape(_display_rank_value(final_rank))}</td>
      <td>{escape(_public_power_text(row.get("end_power_display")))}</td>
      <td>{escape(_public_resume_text(row.get("end_resume_display")))}</td>
      <td>{int(row.get("margin") or 0):+d}</td>
      <td>{season_link}</td>
    </tr>
    """


def _render_history_feature_cards(history_hub: dict[str, Any], prefix: str = "teams/") -> str:
    cards = history_hub.get("cards") or []
    if not cards:
        return '<p class="footer-note">Historical features will populate after more season-ending snapshots are loaded.</p>'
    rendered: list[str] = []
    for card in cards:
        slug_str = str(card.get("slug") or "").strip()
        if slug_str:
            card_open = f'<a class="feature-card story-card" href="{prefix}{escape(slug_str)}.html">'
            card_close = "</a>"
        else:
            card_open = '<div class="feature-card story-card">'
            card_close = "</div>"
        rendered.append(
            f"""
            {card_open}
              <span class="feature-rank">{escape(str(card.get("label") or ""))}</span>
              <h3>{escape(str(card.get("title") or ""))}</h3>
              <p>{escape(str(card.get("body") or ""))}</p>
              <p class="story-tail">{escape(str(card.get("detail") or ""))}</p>
            {card_close}
            """
        )
    return "".join(rendered)


def _render_home_ranking_rail(rankings: list[RankingRow]) -> str:
    items = []
    for row in rankings:
        delta_class = _rank_change_class(row.rank_change)
        delta_text = _rank_change_text(row.rank_change)
        items.append(
            f"""
            <a class="rank-row" href="teams/{escape(row.slug)}.html">
              <span class="rank-no">{row.rank}</span>
                <span class="rank-delta {delta_class}">{escape(delta_text)}</span>
              <span class="rank-team-wrap">
                <span class="rank-team">{escape(row.team_name)}</span>
                <span class="rank-team-meta">{escape(row.level_code)} | Power {_public_power_text(row.power_display)}</span>
              </span>
            </a>
            """
        )
    return f"""
    <div class="rank-rail">
      <div class="rank-rail-head">
        <span>Rank</span>
        <span>Delta</span>
        <span>Team</span>
      </div>
      {''.join(items)}
    </div>
    """


def _render_home_team_board(team_pages: list[dict[str, Any]]) -> str:
    if not team_pages:
        return '<section class="team-board panel"><p class="footer-note">Team board will populate after the next successful model run.</p></section>'

    open_index = next(
        (
            index
            for index, team_data in enumerate(team_pages)
            if "utah" in str(team_data["ranking"].team_name).lower()
        ),
        0,
    )
    rows = "".join(
        _render_home_board_row(team_data, index == open_index)
        for index, team_data in enumerate(team_pages)
    )
    conferences = sorted(
        {
            _clean_conference_name(str(team_data["team"].get("conference_name") or f"{team_data['ranking'].level_code} Independents"))
            for team_data in team_pages
        }
    )
    return f"""
    <section class="team-board panel">
      <div class="section-head board-heading">
        <div>
          <h2>Smart Board</h2>
          <p class="section-note">High-density rankings built for scan speed. Each row opens into a richer team snapshot one click deeper.</p>
        </div>
        <a class="text-link" href="rankings/index.html">All Teams</a>
      </div>
      {_metric_guide_strip()}
      <div class="board-utility">
        <div class="board-controls">
          <label class="board-control board-search">
            <span>Search Teams</span>
            <input id="teamSearch" type="search" placeholder="Search team, conference, or level">
          </label>
          <label class="board-control">
            <span>Level</span>
            <select id="levelFilter">
              <option value="ALL">All levels</option>
              <option value="FBS">FBS</option>
              <option value="FCS">FCS</option>
              <option value="DII">Division II</option>
              <option value="DIII">Division III</option>
            </select>
          </label>
          <label class="board-control">
            <span>Conference</span>
            <select id="conferenceFilter">
              <option value="ALL">All conferences</option>
              {"".join(f'<option value="{escape(conf)}">{escape(conf)}</option>' for conf in conferences)}
            </select>
          </label>
          <label class="board-control">
            <span>Sort</span>
            <select id="sortMode">
              <option value="power">Power</option>
              <option value="resume">Resume</option>
              <option value="rank">Published rank</option>
              <option value="team">Team A-Z</option>
            </select>
          </label>
        </div>
        <div class="board-toolbar">
          <div class="jump-group" role="group" aria-label="Quick jump range">
            <button type="button" class="jump-chip is-active" data-limit="25">Top 25</button>
            <button type="button" class="jump-chip" data-limit="100">Top 100</button>
            <button type="button" class="jump-chip" data-limit="all">All teams</button>
          </div>
          <div class="board-status">
            <strong id="boardCount">{len(team_pages)}</strong>
            <span>teams visible</span>
          </div>
          <button type="button" class="clear-filters" id="clearBoardFilters">Clear filters</button>
        </div>
        <div class="active-filter-row" id="activeFilterRow" hidden></div>
      </div>
      <div class="board-topline">
        <div class="board-column-head">
          <span>Rank</span>
          <span>Delta</span>
          <span>Team</span>
          <span>Record</span>
          <span>Power</span>
          <span>Resume</span>
          <span>Trend</span>
        </div>
      </div>
      <div class="team-board-list">
        {rows}
      </div>
    </section>
    """


def _render_home_board_row(team_data: dict[str, Any], is_open: bool) -> str:
    ranking: RankingRow = team_data["ranking"]
    team = team_data["team"]
    season_summary = team_data["season_summary"]
    efficiency_snapshot = team_data["efficiency_snapshot"]
    history_profile = team_data.get("history_profile") or {}
    schedule = team_data["schedule"]
    conference = _clean_conference_name(str(team.get("conference_name") or f"{ranking.level_code} Independents"))
    wins = int(season_summary.get("wins") or 0)
    losses = int(season_summary.get("losses") or 0)
    best_result = _best_result_text(ranking.team_id, schedule)
    worst_result = _worst_result_text(ranking.team_id, schedule)
    recent_form = _compact_recent_form(ranking.team_id, schedule)
    efficiency_note = _best_efficiency_signal(efficiency_snapshot)
    open_attr = " open" if is_open else ""
    delta_class = _rank_change_class(ranking.rank_change)
    delta_text = _rank_change_text(ranking.rank_change)
    reminiscence_cards = _render_reminiscence_cards(team_data.get("similarity_cards") or [])
    level = escape(ranking.level_code)
    conference_attr = escape(conference)
    search_blob = escape(f"{ranking.team_name} {conference} {ranking.level_code}".lower())
    trend_values = _trend_path_values(team_data)
    return f"""
    <details class="board-row"{open_attr} data-rank="{ranking.rank}" data-power="{float(ranking.power_display or 0.0):.4f}" data-resume="{float(ranking.resume_display or 0.0):.4f}" data-team="{escape(ranking.team_name.lower())}" data-level="{level}" data-conference="{conference_attr}" data-search="{search_blob}">
      <summary>
        <span class="board-cell rank-cell-home">#{ranking.rank}</span>
        <span class="board-cell board-delta {delta_class}">{escape(delta_text)}</span>
        <span class="board-cell board-team-cell">
          <span class="board-team-name">{escape(ranking.team_name)}</span>
          <span class="board-team-meta">{escape(ranking.level_code)} | {escape(conference)}</span>
        </span>
        <span class="board-cell board-record">{wins}-{losses}</span>
        <span class="board-cell board-power">{_public_power_text(ranking.power_display)}</span>
        <span class="board-cell board-resume">{_public_resume_text(ranking.resume_display)}</span>
        <span class="board-cell board-trend">{_sparkline(trend_values)}</span>
      </summary>
      <div class="board-row-body">
        <div class="board-detail-grid">
          <article class="mini-panel detail-identity">
            <h3>Team Identity</h3>
            {_render_identity_plot(ranking)}
          </article>
          <article class="mini-panel detail-bestwins">
            <h3>Best Wins / Bad Losses</h3>
            <div class="result-pair-grid">
              <div class="result-slab">
                <span class="result-kicker">Best Signal</span>
                <p>{escape(best_result)}</p>
              </div>
              <div class="result-slab">
                <span class="result-kicker">Pressure Point</span>
                <p>{escape(worst_result)}</p>
              </div>
              <div class="result-slab result-slab-wide">
                <span class="result-kicker">Overall Team Profile</span>
                <p><strong>Recent form:</strong> {escape(recent_form)}</p>
                <p><strong>Efficiency pulse:</strong> {escape(efficiency_note)}</p>
                <p><strong>Power / Resume:</strong> {_public_power_text(ranking.power_display)} / {_public_resume_text(ranking.resume_display)}</p>
              </div>
            </div>
          </article>
          <article class="mini-panel detail-watch">
            <h3>Fraud Watch</h3>
            <p><strong>Watchlist:</strong> {"No" if ranking.resume_score >= -0.2 else "Yes"}</p>
            <p><strong>Reasoning:</strong> {_fraud_watch_reason(ranking, recent_form, efficiency_note)}</p>
          </article>
          {_render_history_mini_panel(history_profile)}
          {reminiscence_cards}
        </div>
        <div class="board-row-footer">
          <a class="text-link" href="teams/{escape(ranking.slug)}.html">Open full team page</a>
        </div>
      </div>
    </details>
    """


def _render_home_team_accordion(team_pages: list[dict[str, Any]]) -> str:
    blocks = []
    for index, team_data in enumerate(team_pages):
        ranking: RankingRow = team_data["ranking"]
        team = team_data["team"]
        season_summary = team_data["season_summary"]
        efficiency_snapshot = team_data["efficiency_snapshot"]
        history_profile = team_data.get("history_profile") or {}
        trend_points = team_data["trend_points"]
        schedule = team_data["schedule"][:4]
        conference = _clean_conference_name(str(team.get("conference_name") or f"{ranking.level_code} Independents"))
        wins = int(season_summary.get("wins") or 0)
        losses = int(season_summary.get("losses") or 0)
        best_result = _best_result_text(ranking.team_id, schedule)
        worst_result = _worst_result_text(ranking.team_id, schedule)
        recent_form = _compact_recent_form(ranking.team_id, schedule)
        efficiency_note = _best_efficiency_signal(efficiency_snapshot)
        open_attr = " open" if index == 0 else ""
        blocks.append(
            f"""
            <details class="team-dropdown"{open_attr}>
              <summary>
                <span class="dropdown-rank">#{ranking.rank}</span>
                <span class="dropdown-team">{escape(ranking.team_name)}</span>
                <span class="dropdown-meta">{escape(ranking.level_code)} | {escape(conference)} | {wins}-{losses}</span>
                <span class="dropdown-power">{_public_power_text(ranking.power_display)}</span>
              </summary>
              <div class="dropdown-body">
                <div class="dropdown-topline">
                  <div class="chip-row">
                    <span class="mini-chip">Record {wins}-{losses}</span>
                    <span class="mini-chip">Resume {_public_resume_text(ranking.resume_display)}</span>
                    <span class="mini-chip">Overall #{ranking.rank}</span>
                    <span class="mini-chip">{escape(ranking.level_code)} profile</span>
                  </div>
                  <a class="text-link" href="teams/{escape(ranking.slug)}.html">Open team page</a>
                </div>
                <div class="dropdown-grid">
                  <article class="mini-panel">
                    <h3>Team Identity</h3>
                    {_render_identity_plot(ranking)}
                  </article>
                  <article class="mini-panel">
                    <h3>Best Wins / Bad Losses</h3>
                    <p><strong>Best signal:</strong> {escape(best_result)}</p>
                    <p><strong>Stress point:</strong> {escape(worst_result)}</p>
                  </article>
                  <article class="mini-panel">
                    <h3>Rating Arc</h3>
                    {_render_micro_rating_path(team_data["rating_path"])}
                  </article>
                  <article class="mini-panel">
                    <h3>Overall Team Profile</h3>
                    <p><strong>Recent form:</strong> {escape(recent_form)}</p>
                    <p><strong>Efficiency pulse:</strong> {escape(efficiency_note)}</p>
                    <p><strong>Power / Resume:</strong> {_public_power_text(ranking.power_display)} / {_public_resume_text(ranking.resume_display)}</p>
                  </article>
                  {_render_history_mini_panel(history_profile)}
                </div>
              </div>
            </details>
            """
        )
    return "".join(blocks)


def _power_resume_plot_payload(team_pages: list[dict[str, Any]], prefix: str = "") -> str:
    eligible_pages = [team_page for team_page in team_pages if team_page.get("ranking")]
    if not eligible_pages:
        return json.dumps({"teams": []})

    rankings = [team_page["ranking"] for team_page in eligible_pages]
    power_order = sorted(rankings, key=lambda row: (-row.power_rating, -row.resume_score, row.team_name.lower()))
    resume_order = sorted(rankings, key=lambda row: (-row.resume_score, -row.power_rating, row.team_name.lower()))
    power_rank = {row.slug: index + 1 for index, row in enumerate(power_order)}
    resume_rank = {row.slug: index + 1 for index, row in enumerate(resume_order)}
    denominator = max(1, len(rankings) - 1)

    def percentile(rank_value: int) -> float:
        if len(rankings) <= 1:
            return 50.0
        return 100.0 * (len(rankings) - rank_value) / denominator

    payload_rows: list[dict[str, Any]] = []
    for team_page in eligible_pages:
        ranking: RankingRow = team_page["ranking"]
        season_summary = team_page.get("season_summary") or {}
        team_row = team_page.get("team") or {}
        conference_name = _clean_conference_name(
            str(team_row.get("conference_name") or ranking.conference_name or f"{ranking.level_code} Independents")
        )
        wins = int(season_summary.get("wins") or 0)
        losses = int(season_summary.get("losses") or 0)
        payload_rows.append(
            {
                "slug": ranking.slug,
                "team_name": ranking.team_name,
                "level_code": ranking.level_code,
                "conference": conference_name,
                "rank": ranking.rank,
                "record": f"{wins}-{losses}",
                "power_display": round(float(ranking.power_display or 0.0), 1),
                "resume_display": round(float(ranking.resume_display or 0.0), 0),
                "power_rating": round(ranking.power_rating, 2),
                "resume_score": round(ranking.resume_score, 2),
                "power_rank": power_rank[ranking.slug],
                "resume_rank": resume_rank[ranking.slug],
                "power_percentile": round(percentile(power_rank[ranking.slug]), 2),
                "resume_percentile": round(percentile(resume_rank[ranking.slug]), 2),
                "team_url": f"{prefix}teams/{ranking.slug}.html",
                "search": f"{ranking.team_name} {ranking.level_code} {conference_name}".lower(),
            }
        )
    return json.dumps({"teams": payload_rows})


def _render_power_resume_plot(team_pages: list[dict[str, Any]], prefix: str = "") -> str:
    eligible_pages = [team_page for team_page in team_pages if team_page.get("ranking")]
    if not eligible_pages:
        return '<p class="footer-note">Power and resume map will populate after the next successful model run.</p>'

    counts = {"ALL": 0, "FBS": 0, "FCS": 0, "DII": 0, "DIII": 0}
    for team_page in eligible_pages:
        level_code = str(team_page["ranking"].level_code)
        counts["ALL"] += 1
        counts[level_code] = counts.get(level_code, 0) + 1

    payload = _power_resume_plot_payload(eligible_pages, prefix=prefix)
    return f"""
    <section class="power-resume-module">
      <div class="power-resume-topline">
        <p class="section-note">Hover a point, search a team, or isolate a level. The x-axis is public power, shown as points versus the average all-level team. The y-axis is the 0-100 public resume score.</p>
        <label class="board-control power-resume-search">
          <span>Find Team</span>
          <input id="powerResumeSearch" type="search" placeholder="Search any team">
        </label>
      </div>

      <div class="power-resume-levels" role="toolbar" aria-label="Filter power versus resume chart by level">
        <button type="button" class="power-resume-level is-active" data-power-resume-level="ALL">All teams <span>{counts['ALL']}</span></button>
        <button type="button" class="power-resume-level" data-power-resume-level="FBS">FBS <span>{counts['FBS']}</span></button>
        <button type="button" class="power-resume-level" data-power-resume-level="FCS">FCS <span>{counts['FCS']}</span></button>
        <button type="button" class="power-resume-level" data-power-resume-level="DII">DII <span>{counts['DII']}</span></button>
        <button type="button" class="power-resume-level" data-power-resume-level="DIII">DIII <span>{counts['DIII']}</span></button>
      </div>
      <div class="power-resume-legend" aria-label="Level legend">
        <span class="power-resume-legend-item"><span class="power-resume-legend-point level-FBS"></span>FBS</span>
        <span class="power-resume-legend-item"><span class="power-resume-legend-point level-FCS"></span>FCS</span>
        <span class="power-resume-legend-item"><span class="power-resume-legend-point level-DII"></span>DII</span>
        <span class="power-resume-legend-item"><span class="power-resume-legend-point level-DIII"></span>DIII</span>
      </div>

      <div class="power-resume-layout">
        <div class="power-resume-stage">
          <div class="power-resume-plot-shell">
            <div class="power-resume-axis-y">More season resume</div>
            <div class="power-resume-plot" id="powerResumePlot" role="img" aria-label="Interactive power versus resume chart">
              <div class="power-resume-field" id="powerResumeField">
                <div class="power-resume-midline power-resume-midline-x"></div>
                <div class="power-resume-midline power-resume-midline-y"></div>
                <div class="power-resume-quadrant power-resume-quadrant-nw">Resume ahead of power</div>
                <div class="power-resume-quadrant power-resume-quadrant-ne">Elite in both</div>
                <div class="power-resume-quadrant power-resume-quadrant-sw">Still building the case</div>
                <div class="power-resume-quadrant power-resume-quadrant-se">Dangerous, resume lagging</div>
                <div class="power-resume-points" id="powerResumePoints"></div>
                <div class="power-resume-tag" id="powerResumeTag" hidden></div>
              </div>
            </div>
            <div class="power-resume-axis-footer">
              <span>Lower predictive strength</span>
              <strong>Predictive power</strong>
              <span>Higher predictive strength</span>
            </div>
            <div class="power-resume-scale">
              <span>0</span>
              <span>50</span>
              <span>100</span>
            </div>
          </div>
          <p class="footer-note">Color and shape mark the level. Click a point to lock the team card, then jump straight into that team page.</p>
        </div>

        <aside class="power-resume-focus" id="powerResumeFocus">
          <span class="feature-rank">Chart Focus</span>
          <h3>Loading team context...</h3>
          <p class="section-note">The chart will load the currently selected team here.</p>
        </aside>
      </div>

      <div class="power-resume-footer">
        <span class="mini-chip"><strong id="powerResumeVisibleCount">{counts['ALL']}</strong> teams visible</span>
        <span class="mini-chip">Percentile axes for fast reading</span>
      </div>

      <script id="powerResumePayload" type="application/json">{payload}</script>
    </section>
    """


def _render_strength_ladder(rankings: list[RankingRow]) -> str:
    groups: dict[str, list[float]] = {"FBS": [], "FCS": [], "DII": [], "DIII": []}
    for row in rankings:
        groups.setdefault(row.level_code, []).append(row.power_rating)
    means = {level: (sum(values[:40]) / max(1, min(len(values), 40))) for level, values in groups.items()}
    max_mean = max(means.values()) if means else 1.0
    bands = []
    order = ["FBS", "FCS", "DII", "DIII"]
    for index, level in enumerate(order):
        width_pct = 100 - index * 16
        color = _level_color(level)
        bands.append(
            f"""
            <div class="ladder-band" style="width:{width_pct}%;">
              <span class="ladder-label">{level}</span>
              <span class="ladder-value">{means.get(level, 0.0):.2f}</span>
              <div class="ladder-fill" style="width:{(means.get(level, 0.0)/max_mean)*100:.1f}%; background:{color};"></div>
            </div>
            """
        )
    return f'<div class="ladder-wrap">{"".join(bands)}</div>'


def _render_identity_plot(ranking: RankingRow) -> str:
    offense = min(100, max(8, 45 + ranking.power_rating * 3.6))
    defense = min(100, max(8, 44 + ranking.resume_score * 11.5))
    color = _level_color(ranking.level_code)
    return f"""
    <svg class="identity-svg" viewBox="0 0 220 170" role="img" aria-label="Team identity plot">
      <rect x="0" y="0" width="220" height="170" rx="18" fill="rgba(255,255,255,0.45)"></rect>
      <line x1="26" y1="85" x2="194" y2="85" stroke="rgba(17,17,17,0.20)"></line>
      <line x1="110" y1="22" x2="110" y2="148" stroke="rgba(17,17,17,0.20)"></line>
      <text x="8" y="20" font-size="11" font-family="Arial" fill="#625b52">Offense</text>
      <text x="152" y="162" font-size="11" font-family="Arial" fill="#625b52">Defense</text>
      <circle cx="{defense*1.6+18:.1f}" cy="{162-offense*1.2:.1f}" r="8" fill="{color}"></circle>
    </svg>
    """


def _render_micro_rating_path(values: list[float]) -> str:
    if len(values) < 2:
        return '<p class="footer-note">Timeline will grow as more model checkpoints land.</p>'
    width = 260
    height = 110
    padding = 10
    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 1.0)
    points = []
    for index, value in enumerate(values):
        x = padding + (index * (width - 2 * padding) / max(1, len(values) - 1))
        y = height - padding - ((value - min_value) / span) * (height - 2 * padding)
        points.append(f"{x:.1f},{y:.1f}")
    return f"""
    <svg class="micro-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Mini rating path">
      <rect x="0" y="0" width="{width}" height="{height}" rx="16" fill="rgba(255,255,255,0.48)"></rect>
      <polyline fill="none" stroke="#bf3b1f" stroke-width="3.5" points="{' '.join(points)}"></polyline>
    </svg>
    """


def _render_reminiscence_cards(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return """
        <article class="mini-panel reminiscence-card">
          <h3>Historical comps pending</h3>
          <p class="reminiscence-title">Load more prior seasons</p>
          <p class="reminiscence-sub">There are not enough earlier modeled seasons in the archive yet to create a real similarity match.</p>
        </article>
        """

    rendered = []
    for card in cards:
        subtitle = f"Similarity Score: {int(card.get('similarity') or 0)}%"
        context = str(card.get("context") or "").strip()
        if context:
            subtitle = f"{subtitle} | {context}"
        rendered.append(
            f"""
            <article class="mini-panel reminiscence-card">
              <h3>{escape(str(card.get("title") or "Historical Comp"))}</h3>
              <p class="reminiscence-title">{escape(str(card.get("comp_team") or "Archive comp"))}</p>
              <p class="reminiscence-sub">{escape(subtitle)}</p>
              {_render_profile_bars(card.get("values") or [])}
            </article>
            """
        )
    return "".join(rendered)


def _efficiency_metric_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["metric_name"]): row for row in rows}


def _build_similarity_cards(
    db: Database,
    summary: dict[str, Any],
    ranking: RankingRow,
    season_summary: dict[str, Any],
    rating_snapshot: dict[str, Any],
    efficiency_metric_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    catalog_bundle = _load_similarity_profile_catalog(db)
    catalog = list(catalog_bundle.get("rows") or [])
    stats = dict(catalog_bundle.get("stats") or {})
    current_season_year = int(summary["season_year"])
    subject = _build_similarity_subject_profile(
        summary=summary,
        ranking=ranking,
        season_summary=season_summary,
        rating_snapshot=rating_snapshot,
        efficiency_metric_map=efficiency_metric_map,
    )
    candidates = [
        row
        for row in catalog
        if int(row.get("season_year") or 0) < current_season_year and int(row.get("team_id") or 0) != ranking.team_id
    ]
    if not candidates:
        return []

    card_specs = [
        {
            "title": "Offensive Comp",
            "features": [
                ("offense_rating", 3.0),
                ("success_off_pct", 1.8),
                ("ppa_off_pct", 2.4),
                ("explosive_off_pct", 1.8),
                ("finish_off_pct", 1.0),
                ("pass_ppa_off_pct", 0.8),
                ("rush_ppa_off_pct", 0.8),
                ("tempo_rating", 0.4),
            ],
            "display": [
                ("Success Rate", "success_off_pct", "percentile"),
                ("EPA / Play", "ppa_off_pct", "percentile"),
                ("Explosiveness", "explosive_off_pct", "percentile"),
            ],
        },
        {
            "title": "Defensive Comp",
            "features": [
                ("defense_rating", 3.0),
                ("success_def_pct", 1.8),
                ("ppa_def_pct", 2.4),
                ("explosive_def_pct", 1.8),
                ("finish_def_pct", 1.0),
                ("pass_ppa_def_pct", 0.8),
                ("rush_ppa_def_pct", 0.8),
            ],
            "display": [
                ("Success Prevention", "success_def_pct", "defense_percentile"),
                ("EPA Prevention", "ppa_def_pct", "defense_percentile"),
                ("Big-Play Prevention", "explosive_def_pct", "defense_percentile"),
            ],
        },
        {
            "title": "Overall Team Profile",
            "features": [
                ("power_rating", 3.0),
                ("resume_score", 2.4),
                ("offense_rating", 1.3),
                ("defense_rating", 1.3),
                ("special_teams_rating", 0.6),
                ("tempo_rating", 0.4),
                ("record_strength_score", 1.0),
                ("performance_over_expectation_score", 1.0),
                ("result_quality_score", 1.1),
                ("schedule_strength_score", 0.9),
                ("win_pct", 1.4),
                ("margin_per_game", 1.0),
                ("success_off_pct", 0.6),
                ("ppa_off_pct", 0.7),
                ("success_def_pct", 0.6),
                ("ppa_def_pct", 0.7),
            ],
            "display": [
                ("Power", "power_rating", "range"),
                ("Resume", "resume_score", "range"),
                ("Win Rate", "win_pct", "win_pct"),
            ],
        },
    ]

    built_cards: list[dict[str, Any]] = []
    for spec in card_specs:
        match = _nearest_similarity_match(
            subject=subject,
            candidates=candidates,
            features=spec["features"],
            stats=stats,
        )
        if match is None:
            continue
        values = _similarity_display_values(
            subject=subject,
            candidate=match["candidate"],
            display_specs=spec["display"],
            stats=stats,
        )
        if not values:
            continue
        candidate = match["candidate"]
        wins = int(candidate.get("wins") or 0)
        losses = int(candidate.get("losses") or 0)
        built_cards.append(
            {
                "title": spec["title"],
                "comp_team": f"{int(candidate.get('season_year') or 0)} {candidate.get('team_name') or 'Historical team'}",
                "similarity": match["similarity"],
                "context": f"{candidate.get('level_code') or '--'} | {wins}-{losses}",
                "values": values,
            }
        )
    return built_cards


def _load_similarity_profile_catalog(db: Database) -> dict[str, Any]:
    cache_key = "season-profile-catalog-v1"
    cached = _SIMILARITY_PROFILE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    rows = db.query_all(
        """
        with latest_run_ids as (
          select mr.season_year, max(mr.model_run_id) as model_run_id
          from model_runs mr
          where exists (
            select 1
            from power_ratings_weekly p
            where p.model_run_id = mr.model_run_id
          )
          group by mr.season_year
        ),
        latest_runs as (
          select mr.season_year, mr.model_run_id, mr.week, mr.model_version
          from model_runs mr
          join latest_run_ids lr on lr.model_run_id = mr.model_run_id
        ),
        game_results as (
          select
            g.season_year,
            g.home_team_id as team_id,
            g.home_points as points_for,
            g.away_points as points_against,
            case
              when g.home_points is not null and g.away_points is not null and g.home_points > g.away_points then 1
              else 0
            end as win,
            case
              when g.home_points is not null and g.away_points is not null and g.home_points < g.away_points then 1
              else 0
            end as loss
          from games g
          union all
          select
            g.season_year,
            g.away_team_id as team_id,
            g.away_points as points_for,
            g.home_points as points_against,
            case
              when g.home_points is not null and g.away_points is not null and g.away_points > g.home_points then 1
              else 0
            end as win,
            case
              when g.home_points is not null and g.away_points is not null and g.away_points < g.home_points then 1
              else 0
            end as loss
          from games g
        ),
        season_results as (
          select
            season_year,
            team_id,
            sum(win) as wins,
            sum(loss) as losses,
            sum(coalesce(points_for, 0)) as points_for,
            sum(coalesce(points_against, 0)) as points_against,
            sum(coalesce(points_for, 0) - coalesce(points_against, 0)) as margin
          from game_results
          group by season_year, team_id
        ),
        metric_pivot as (
          select
            oa.season_year,
            oa.team_id,
            max(case when oa.metric_name = 'success_off_adj' then oa.percentile end) as success_off_pct,
            max(case when oa.metric_name = 'ppa_off_adj' then oa.percentile end) as ppa_off_pct,
            max(case when oa.metric_name = 'explosive_off_adj' then oa.percentile end) as explosive_off_pct,
            max(case when oa.metric_name = 'finish_off_adj' then oa.percentile end) as finish_off_pct,
            max(case when oa.metric_name = 'pass_ppa_off_adj' then oa.percentile end) as pass_ppa_off_pct,
            max(case when oa.metric_name = 'rush_ppa_off_adj' then oa.percentile end) as rush_ppa_off_pct,
            max(case when oa.metric_name = 'success_def_adj' then oa.percentile end) as success_def_pct,
            max(case when oa.metric_name = 'ppa_def_adj' then oa.percentile end) as ppa_def_pct,
            max(case when oa.metric_name = 'explosive_def_adj' then oa.percentile end) as explosive_def_pct,
            max(case when oa.metric_name = 'finish_def_adj' then oa.percentile end) as finish_def_pct,
            max(case when oa.metric_name = 'pass_ppa_def_adj' then oa.percentile end) as pass_ppa_def_pct,
            max(case when oa.metric_name = 'rush_ppa_def_adj' then oa.percentile end) as rush_ppa_def_pct
          from opponent_adjusted_team_week oa
          join latest_runs lr
            on lr.season_year = oa.season_year
           and lr.week = oa.week
           and lr.model_version = oa.model_version
          group by oa.season_year, oa.team_id
        )
        select
          lr.season_year,
          lr.week,
          p.team_id,
          t.slug,
          t.canonical_name as team_name,
          coalesce(ts.level_code, t.level_code) as level_code,
          c.conference_name,
          p.power_rating,
          p.offense_rating,
          p.defense_rating,
          p.special_teams_rating,
          p.tempo_rating,
          r.resume_score,
          r.record_strength_score,
          r.performance_over_expectation_score,
          r.result_quality_score,
          r.best_win_score,
          r.worst_loss_score,
          r.schedule_strength_score,
          sr.wins,
          sr.losses,
          sr.points_for,
          sr.points_against,
          sr.margin,
          mp.success_off_pct,
          mp.ppa_off_pct,
          mp.explosive_off_pct,
          mp.finish_off_pct,
          mp.pass_ppa_off_pct,
          mp.rush_ppa_off_pct,
          mp.success_def_pct,
          mp.ppa_def_pct,
          mp.explosive_def_pct,
          mp.finish_def_pct,
          mp.pass_ppa_def_pct,
          mp.rush_ppa_def_pct
        from latest_runs lr
        join power_ratings_weekly p
          on p.model_run_id = lr.model_run_id
         and p.week = lr.week
        join teams t on t.team_id = p.team_id
        left join team_seasons ts
          on ts.team_id = p.team_id
         and ts.season_year = p.season_year
        left join conferences c on c.conference_id = ts.conference_id
        left join resume_ratings_weekly r
          on r.model_run_id = p.model_run_id
         and r.team_id = p.team_id
         and r.week = p.week
        left join season_results sr
          on sr.season_year = p.season_year
         and sr.team_id = p.team_id
        left join metric_pivot mp
          on mp.season_year = p.season_year
         and mp.team_id = p.team_id
        """
    )

    catalog_rows: list[dict[str, Any]] = []
    for row in rows:
        level_code = str(row.get("level_code") or "")
        conference_name = None if row.get("conference_name") is None else str(row.get("conference_name"))
        if not is_site_eligible_team(level_code, conference_name):
            continue
        wins = int(row.get("wins") or 0)
        losses = int(row.get("losses") or 0)
        games_played = wins + losses
        row["win_pct"] = None if games_played <= 0 else wins / games_played
        row["margin_per_game"] = None if games_played <= 0 else float(row.get("margin") or 0.0) / games_played
        catalog_rows.append(row)

    fields = [
        "power_rating",
        "resume_score",
        "offense_rating",
        "defense_rating",
        "special_teams_rating",
        "tempo_rating",
        "record_strength_score",
        "performance_over_expectation_score",
        "result_quality_score",
        "best_win_score",
        "schedule_strength_score",
        "win_pct",
        "margin_per_game",
        "success_off_pct",
        "ppa_off_pct",
        "explosive_off_pct",
        "finish_off_pct",
        "pass_ppa_off_pct",
        "rush_ppa_off_pct",
        "success_def_pct",
        "ppa_def_pct",
        "explosive_def_pct",
        "finish_def_pct",
        "pass_ppa_def_pct",
        "rush_ppa_def_pct",
    ]
    stats = _similarity_field_stats(catalog_rows, fields)
    bundle = {"rows": catalog_rows, "stats": stats}
    _SIMILARITY_PROFILE_CACHE[cache_key] = bundle
    return bundle


def _build_similarity_subject_profile(
    summary: dict[str, Any],
    ranking: RankingRow,
    season_summary: dict[str, Any],
    rating_snapshot: dict[str, Any],
    efficiency_metric_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    wins = int(season_summary.get("wins") or 0)
    losses = int(season_summary.get("losses") or 0)
    points_for = int(season_summary.get("points_for") or 0)
    points_against = int(season_summary.get("points_against") or 0)
    games_played = wins + losses
    profile = {
        "season_year": int(summary["season_year"]),
        "team_id": ranking.team_id,
        "slug": ranking.slug,
        "team_name": ranking.team_name,
        "level_code": ranking.level_code,
        "power_rating": float(ranking.power_rating),
        "resume_score": float(ranking.resume_score),
        "offense_rating": _optional_float(rating_snapshot.get("offense_rating")),
        "defense_rating": _optional_float(rating_snapshot.get("defense_rating")),
        "special_teams_rating": _optional_float(rating_snapshot.get("special_teams_rating")),
        "tempo_rating": _optional_float(rating_snapshot.get("tempo_rating")),
        "record_strength_score": _optional_float(rating_snapshot.get("record_strength_score")),
        "performance_over_expectation_score": _optional_float(rating_snapshot.get("performance_over_expectation_score")),
        "result_quality_score": _optional_float(rating_snapshot.get("result_quality_score")),
        "best_win_score": _optional_float(rating_snapshot.get("best_win_score")),
        "schedule_strength_score": _optional_float(rating_snapshot.get("schedule_strength_score")),
        "wins": wins,
        "losses": losses,
        "win_pct": None if games_played <= 0 else wins / games_played,
        "margin_per_game": None if games_played <= 0 else (points_for - points_against) / games_played,
    }
    metric_aliases = {
        "success_off_pct": "success_off_adj",
        "ppa_off_pct": "ppa_off_adj",
        "explosive_off_pct": "explosive_off_adj",
        "finish_off_pct": "finish_off_adj",
        "pass_ppa_off_pct": "pass_ppa_off_adj",
        "rush_ppa_off_pct": "rush_ppa_off_adj",
        "success_def_pct": "success_def_adj",
        "ppa_def_pct": "ppa_def_adj",
        "explosive_def_pct": "explosive_def_adj",
        "finish_def_pct": "finish_def_adj",
        "pass_ppa_def_pct": "pass_ppa_def_adj",
        "rush_ppa_def_pct": "rush_ppa_def_adj",
    }
    for field_name, metric_name in metric_aliases.items():
        profile[field_name] = _optional_float((efficiency_metric_map.get(metric_name) or {}).get("percentile"))
    return profile


def _similarity_field_stats(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for field in fields:
        values = [float(row[field]) for row in rows if row.get(field) is not None]
        if not values:
            continue
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        stats[field] = {
            "mean": mean_value,
            "std": max(math.sqrt(variance), 0.001),
            "min": min(values),
            "max": max(values),
        }
    return stats


def _nearest_similarity_match(
    subject: dict[str, Any],
    candidates: list[dict[str, Any]],
    features: list[tuple[str, float]],
    stats: dict[str, dict[str, float]],
) -> dict[str, Any] | None:
    best_match: dict[str, Any] | None = None
    best_distance: float | None = None
    for candidate in candidates:
        distance = _weighted_profile_distance(subject, candidate, features, stats)
        if distance is None:
            continue
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_match = candidate
    if best_match is None or best_distance is None:
        return None
    return {"candidate": best_match, "similarity": _distance_to_similarity(best_distance), "distance": best_distance}


def _weighted_profile_distance(
    subject: dict[str, Any],
    candidate: dict[str, Any],
    features: list[tuple[str, float]],
    stats: dict[str, dict[str, float]],
) -> float | None:
    weighted_error = 0.0
    total_weight = 0.0
    matched_fields = 0
    for field_name, weight in features:
        subject_value = subject.get(field_name)
        candidate_value = candidate.get(field_name)
        field_stats = stats.get(field_name)
        if subject_value is None or candidate_value is None or field_stats is None:
            continue
        delta = (float(subject_value) - float(candidate_value)) / max(float(field_stats.get("std") or 1.0), 0.001)
        weighted_error += weight * delta * delta
        total_weight += weight
        matched_fields += 1
    required_fields = max(3, math.ceil(len(features) / 2))
    if total_weight <= 0 or matched_fields < required_fields:
        return None
    return math.sqrt(weighted_error / total_weight)


def _distance_to_similarity(distance: float) -> int:
    return int(round(max(55.0, min(99.0, 100.0 - (distance * 16.0)))))


def _similarity_display_values(
    subject: dict[str, Any],
    candidate: dict[str, Any],
    display_specs: list[tuple[str, str, str]],
    stats: dict[str, dict[str, float]],
) -> list[tuple[str, int, int]]:
    values: list[tuple[str, int, int]] = []
    for label, field_name, mode in display_specs:
        subject_display = _profile_display_metric(subject, field_name, mode, stats)
        candidate_display = _profile_display_metric(candidate, field_name, mode, stats)
        if subject_display is None or candidate_display is None:
            continue
        values.append((label, int(round(subject_display)), int(round(candidate_display))))
    return values


def _profile_display_metric(
    profile: dict[str, Any],
    field_name: str,
    mode: str,
    stats: dict[str, dict[str, float]],
) -> float | None:
    raw_value = profile.get(field_name)
    if raw_value is None:
        return None
    if mode == "percentile":
        return max(0.0, min(100.0, float(raw_value) * 100.0))
    if mode == "defense_percentile":
        return max(0.0, min(100.0, (1.0 - float(raw_value)) * 100.0))
    if mode == "win_pct":
        return max(0.0, min(100.0, float(raw_value) * 100.0))
    if mode == "range":
        field_stats = stats.get(field_name)
        if field_stats is None:
            return None
        min_value = float(field_stats.get("min") or 0.0)
        max_value = float(field_stats.get("max") or 0.0)
        if math.isclose(min_value, max_value):
            return 50.0
        return max(0.0, min(100.0, ((float(raw_value) - min_value) / (max_value - min_value)) * 100.0))
    return None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _render_profile_bars(values: list[tuple[str, int, int]]) -> str:
    legend = '<div class="profile-legend"><span class="profile-self"></span><strong>This team</strong><span class="profile-comp"></span><strong>Comp</strong></div>'
    bars = []
    for label, current_value, comp_value in values:
        bars.append(
            f"""
            <div class="profile-row">
              <div class="profile-label">{escape(label)}</div>
              <div class="profile-bars">
                <span class="bar-self" style="width:{max(0, min(100, int(current_value)))}%;"></span>
                <span class="bar-comp" style="width:{max(0, min(100, int(comp_value)))}%;"></span>
              </div>
            </div>
            """
        )
    return f'{legend}<div class="profile-bar-grid">{"".join(bars)}</div>'


def _efficiency_snapshot(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    metrics = {str(row["metric_name"]): row for row in rows}
    card_specs = [
        ("Offensive Efficiency", "ppa_off_adj", "success_off_adj"),
        ("Defensive Efficiency", "ppa_def_adj", "success_def_adj"),
        ("Explosiveness", "explosive_off_adj", "explosive_def_adj"),
        ("Field Position", "field_pos_off_adj", "field_pos_def_adj"),
        ("Finishing Drives", "finish_off_adj", "finish_def_adj"),
        ("Passing Edge", "pass_ppa_off_adj", "pass_ppa_def_adj"),
    ]
    snapshot: dict[str, dict[str, float]] = {}
    for label, offense_metric, defense_metric in card_specs:
        offense = metrics.get(offense_metric, {})
        defense = metrics.get(defense_metric, {})
        snapshot[label] = {
            "offense_value": float(offense.get("adjusted_value") or 0.0),
            "offense_percentile": float(offense.get("percentile") or 0.0),
            "offense_sample": int(offense.get("sample_size") or 0),
            "defense_value": float(defense.get("adjusted_value") or 0.0),
            "defense_percentile": float(defense.get("percentile") or 0.0),
            "defense_sample": int(defense.get("sample_size") or 0),
        }
    return snapshot


def _render_efficiency_cards(snapshot: dict[str, dict[str, float]]) -> str:
    cards = []
    for label, values in snapshot.items():
        offense_pct = values.get("offense_percentile", 0.0) * 100.0
        defense_pct = values.get("defense_percentile", 0.0) * 100.0
        sample_size = max(int(values.get("offense_sample", 0)), int(values.get("defense_sample", 0)))
        cards.append(
            f"""
            <article class="feature-card efficiency-card">
              <span class="feature-rank">{escape(label)}</span>
              <div class="efficiency-line">
                <span>Offense</span>
                <strong>{_ordinal(int(round(offense_pct)))} pct</strong>
              </div>
              <div class="efficiency-track"><span class="efficiency-fill offense" style="width:{offense_pct:.1f}%"></span></div>
              <div class="efficiency-line">
                <span>Defense</span>
                <strong>{_ordinal(int(round(defense_pct)))} pct</strong>
              </div>
              <div class="efficiency-track"><span class="efficiency-fill defense" style="width:{defense_pct:.1f}%"></span></div>
              <p><strong>Adjusted values:</strong> {values.get("offense_value", 0.0):+.2f} offense, {values.get("defense_value", 0.0):+.2f} defense</p>
              <p><strong>Sample:</strong> {sample_size} opponent-adjusted games in the current build.</p>
            </article>
            """
        )
    return "".join(cards)


def _best_efficiency_signal(snapshot: dict[str, dict[str, float]]) -> str:
    if not snapshot:
        return "Opponent-adjusted profile will sharpen as more play-level data lands."

    best_label = "Offensive Efficiency"
    best_value = -1.0
    for label, values in snapshot.items():
        offense_pct = float(values.get("offense_percentile", 0.0))
        defense_pct = float(values.get("defense_percentile", 0.0))
        candidate = max(offense_pct, defense_pct)
        if candidate > best_value:
            best_value = candidate
            best_label = _efficiency_signal_display_label(label, offense_pct, defense_pct)
    return f"{best_label} currently grades around the {_percentile_label(best_value * 100.0)}."


def _efficiency_signal_display_label(label: str, offense_pct: float, defense_pct: float) -> str:
    if offense_pct >= defense_pct:
        return label
    defensive_aliases = {
        "Offensive Efficiency": "Defensive Efficiency",
        "Defensive Efficiency": "Defensive Efficiency",
        "Explosiveness": "Big-Play Prevention",
        "Field Position": "Field Position Defense",
        "Finishing Drives": "Finishing Drives Defense",
        "Passing Edge": "Pass Defense",
    }
    return defensive_aliases.get(label, f"{label} defense")


def _opponent_is_site_eligible(row: dict[str, Any]) -> bool:
    return is_site_eligible_team(
        None if row.get("opponent_level_code") is None else str(row.get("opponent_level_code")),
        None if row.get("opponent_conference_name") is None else str(row.get("opponent_conference_name")),
    )


def _preferred_schedule_rows(schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible_rows = [row for row in schedule if _opponent_is_site_eligible(row)]
    return eligible_rows if eligible_rows else schedule


def _best_result_text(team_id: int, schedule: list[dict[str, Any]]) -> str:
    best = None
    for row in _preferred_schedule_rows(schedule):
        delta = row.get("power_delta")
        if delta is None:
            continue
        if best is None or float(delta) > float(best.get("power_delta") or -999):
            best = row
    if best is None:
        return "Awaiting richer model delta history."
    return _game_blurb(team_id, best)


def _worst_result_text(team_id: int, schedule: list[dict[str, Any]]) -> str:
    worst = None
    for row in _preferred_schedule_rows(schedule):
        delta = row.get("power_delta")
        if delta is None:
            continue
        if worst is None or float(delta) < float(worst.get("power_delta") or 999):
            worst = row
    if worst is None:
        return "No negative swing on file yet."
    return _game_blurb(team_id, worst)


def _compact_recent_form(team_id: int, schedule: list[dict[str, Any]]) -> str:
    tokens = []
    for row in _preferred_schedule_rows(schedule)[-4:]:
        result = _result_token(team_id, row)
        if result:
            tokens.append(result)
    return " ".join(tokens) if tokens else "Upcoming schedule still settling."


def _fraud_watch_reason(ranking: RankingRow, recent_form: str, efficiency_note: str) -> str:
    if ranking.resume_score > ranking.power_rating + 1.2:
        return f"Results are running a bit hotter than the underlying strength profile. Recent form: {recent_form}."
    if ranking.power_rating > ranking.resume_score + 1.8:
        return f"Underlying strength still looks better than the season body of work. {efficiency_note}"
    return f"Results and underlying strength are mostly aligned so far. {efficiency_note}"


def _power_resume_plot_script() -> str:
    return """
      (() => {
        const payloadNode = document.getElementById('powerResumePayload');
        const plotField = document.getElementById('powerResumeField');
        const pointsNode = document.getElementById('powerResumePoints');
        const searchInput = document.getElementById('powerResumeSearch');
        const focusNode = document.getElementById('powerResumeFocus');
        const tagNode = document.getElementById('powerResumeTag');
        const countNode = document.getElementById('powerResumeVisibleCount');
        const levelButtons = Array.from(document.querySelectorAll('[data-power-resume-level]'));
        if (!payloadNode || !plotField || !pointsNode || !searchInput || !focusNode || !tagNode || !countNode || !levelButtons.length) return;

        let payload = null;
        try {
          payload = JSON.parse(payloadNode.textContent || '{}');
        } catch (error) {
          console.error('Could not parse power/resume payload', error);
          return;
        }

        const teams = Array.isArray(payload.teams) ? payload.teams : [];
        if (!teams.length) return;

        const normalized = (value) => (value || '').toString().trim().toLowerCase();
        const formatPower = (value) => {
          const number = Number(value || 0);
          return `${number >= 0 ? '+' : ''}${number.toFixed(1)}`;
        };
        const formatResume = (value) => `${Math.round(Number(value || 0))}`;
        let activeLevel = 'ALL';
        let query = '';
        let selectedSlug = teams[0].slug;

        function insightLine(team) {
          const gap = Number(team.power_percentile || 0) - Number(team.resume_display || 0);
          const magnitude = Math.round(Math.abs(gap));
          if (magnitude < 8) return 'Power and resume are telling a mostly aligned story right now.';
          if (gap > 0) return `Power is running about ${magnitude} percentile points ahead of resume right now.`;
          return `Resume is running about ${magnitude} percentile points ahead of power right now.`;
        }

        function escapeHtml(value) {
          return String(value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll(\"'\", '&#39;');
        }

        function filteredTeams() {
          return teams.filter((team) => {
            const matchesLevel = activeLevel === 'ALL' || team.level_code === activeLevel;
            const matchesQuery = !query || team.search.includes(query);
            return matchesLevel && matchesQuery;
          });
        }

        function setTag(team) {
          tagNode.hidden = false;
          tagNode.textContent = `${team.team_name} | ${team.level_code} | #${team.rank}`;
          tagNode.style.left = `${team.power_percentile.toFixed(2)}%`;
          tagNode.style.bottom = `${team.resume_percentile.toFixed(2)}%`;
          tagNode.classList.toggle('is-left', team.power_percentile >= 68);
          tagNode.classList.toggle('is-low', team.resume_percentile >= 84);
        }

        function renderFocus(team, visibleCount) {
          focusNode.innerHTML = `
            <span class="feature-rank">${escapeHtml(team.level_code)} profile</span>
            <h3>${escapeHtml(team.team_name)}</h3>
            <p class="power-resume-focus-sub">${escapeHtml(team.conference)} | ${escapeHtml(team.record)} | #${team.rank} overall</p>
            <div class="power-resume-focus-grid">
              <div class="stat-card"><span>Power</span><strong>${formatPower(team.power_display)}</strong></div>
              <div class="stat-card"><span>Resume</span><strong>${formatResume(team.resume_display)}</strong></div>
              <div class="stat-card"><span>Power Slot</span><strong>#${team.power_rank}</strong></div>
              <div class="stat-card"><span>Resume Slot</span><strong>#${team.resume_rank}</strong></div>
            </div>
            <p class="section-note">${insightLine(team)}</p>
            <p class="footer-note">${visibleCount} teams currently match this chart view.</p>
            <a class="button button-secondary power-resume-link" href="${team.team_url}">Open Team Page</a>
          `;
        }

        function renderPoints() {
          const visible = filteredTeams();
          countNode.textContent = String(visible.length);

          if (!visible.length) {
            selectedSlug = teams[0].slug;
            pointsNode.innerHTML = '<p class="power-resume-empty">No teams match that search yet.</p>';
            tagNode.hidden = true;
            focusNode.innerHTML = `
              <span class="feature-rank">Chart Focus</span>
              <h3>No teams found</h3>
              <p class="section-note">Try a shorter search term or switch back to all levels.</p>
            `;
            return;
          }

          const visibleSlugs = new Set(visible.map((team) => team.slug));
          if (!visibleSlugs.has(selectedSlug)) {
            selectedSlug = visible[0].slug;
          }

          pointsNode.innerHTML = '';
          visible.forEach((team) => {
            const point = document.createElement('button');
            point.type = 'button';
            point.className = `power-resume-point level-${team.level_code}${team.slug === selectedSlug ? ' is-selected' : ''}`;
            point.style.left = `${team.power_percentile.toFixed(2)}%`;
            point.style.bottom = `${team.resume_percentile.toFixed(2)}%`;
            point.setAttribute('aria-label', `${team.team_name}, ${team.level_code}, rank ${team.rank}, power ${formatPower(team.power_display)}, resume ${formatResume(team.resume_display)}`);
            point.title = `${team.team_name} (${team.level_code})`;

            const matchesQuery = !query || team.search.includes(query);
            point.classList.toggle('is-muted', !!query && !matchesQuery);
            point.addEventListener('mouseenter', () => {
              selectedSlug = team.slug;
              renderPoints();
            });
            point.addEventListener('focus', () => {
              selectedSlug = team.slug;
              renderPoints();
            });
            point.addEventListener('click', () => {
              selectedSlug = team.slug;
              renderPoints();
            });
            pointsNode.appendChild(point);
          });

          const selected = visible.find((team) => team.slug === selectedSlug) || visible[0];
          setTag(selected);
          renderFocus(selected, visible.length);
        }

        levelButtons.forEach((button) => {
          button.addEventListener('click', () => {
            activeLevel = button.dataset.powerResumeLevel || 'ALL';
            levelButtons.forEach((item) => item.classList.toggle('is-active', item === button));
            renderPoints();
          });
        });

        searchInput.addEventListener('input', () => {
          query = normalized(searchInput.value);
          const firstMatch = filteredTeams()[0];
          if (firstMatch) {
            selectedSlug = firstMatch.slug;
          }
          renderPoints();
        });

        renderPoints();
      })();
    """


def _home_board_script() -> str:
    return """
      (() => {
        const rows = Array.from(document.querySelectorAll('.board-row'));
        if (!rows.length) return;

        const searchInput = document.getElementById('teamSearch');
        const levelFilter = document.getElementById('levelFilter');
        const conferenceFilter = document.getElementById('conferenceFilter');
        const sortMode = document.getElementById('sortMode');
        const clearButton = document.getElementById('clearBoardFilters');
        const countNode = document.getElementById('boardCount');
        const chipRow = document.getElementById('activeFilterRow');
        const boardList = document.querySelector('.team-board-list');
        const jumpButtons = Array.from(document.querySelectorAll('.jump-chip'));

        let limit = 25;

        const normalized = (value) => (value || '').toString().trim().toLowerCase();
        const sorters = {
          power: (a, b) => parseFloat(b.dataset.power) - parseFloat(a.dataset.power),
          resume: (a, b) => parseFloat(b.dataset.resume) - parseFloat(a.dataset.resume),
          rank: (a, b) => parseInt(a.dataset.rank, 10) - parseInt(b.dataset.rank, 10),
          team: (a, b) => a.dataset.team.localeCompare(b.dataset.team),
        };

        function renderChips(tokens) {
          chipRow.innerHTML = '';
          if (!tokens.length) {
            chipRow.hidden = true;
            return;
          }
          chipRow.hidden = false;
          tokens.forEach((token) => {
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            chip.textContent = token;
            chipRow.appendChild(chip);
          });
        }

        function applyBoardState() {
          const query = normalized(searchInput.value);
          const level = levelFilter.value;
          const conference = conferenceFilter.value;
          const sorter = sorters[sortMode.value] || sorters.power;

          const filtered = rows.filter((row) => {
            const matchesQuery = !query || row.dataset.search.includes(query);
            const matchesLevel = level === 'ALL' || row.dataset.level === level;
            const matchesConference = conference === 'ALL' || row.dataset.conference === conference;
            return matchesQuery && matchesLevel && matchesConference;
          });

          const sorted = [...filtered].sort(sorter);
          rows.forEach((row) => {
            row.style.display = 'none';
            row.open = false;
          });

          const limited = limit === 'all' ? sorted : sorted.slice(0, limit);
          limited.forEach((row, index) => {
            row.style.display = '';
            boardList.appendChild(row);
            if (index === 0 && !query && level === 'ALL' && conference === 'ALL') {
              row.open = row.dataset.team.includes('utah') || row.dataset.rank === '1';
            }
          });

          countNode.textContent = String(limited.length);

          const chipTokens = [];
          if (query) chipTokens.push(`Search: ${searchInput.value.trim()}`);
          if (level !== 'ALL') chipTokens.push(`Level: ${level}`);
          if (conference !== 'ALL') chipTokens.push(`Conference: ${conference}`);
          chipTokens.push(`Sort: ${sortMode.options[sortMode.selectedIndex].text}`);
          chipTokens.push(limit === 'all' ? 'Range: All teams' : `Range: Top ${limit}`);
          renderChips(chipTokens);
        }

        [searchInput, levelFilter, conferenceFilter, sortMode].forEach((node) => {
          node.addEventListener('input', applyBoardState);
          node.addEventListener('change', applyBoardState);
        });

        jumpButtons.forEach((button) => {
          button.addEventListener('click', () => {
            jumpButtons.forEach((item) => item.classList.remove('is-active'));
            button.classList.add('is-active');
            limit = button.dataset.limit === 'all' ? 'all' : parseInt(button.dataset.limit, 10);
            applyBoardState();
          });
        });

        clearButton.addEventListener('click', () => {
          searchInput.value = '';
          levelFilter.value = 'ALL';
          conferenceFilter.value = 'ALL';
          sortMode.value = 'power';
          limit = 25;
          jumpButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.limit === '25'));
          applyBoardState();
        });

        applyBoardState();
      })();
    """


def _rankings_board_script() -> str:
    return """
      (() => {
        const rows = Array.from(document.querySelectorAll('#rankingsTableBody tr'));
        if (!rows.length) return;

        const searchInput = document.getElementById('rankingsSearch');
        const levelFilter = document.getElementById('rankingsLevelFilter');
        const conferenceFilter = document.getElementById('rankingsConferenceFilter');
        const sortMode = document.getElementById('rankingsSortMode');
        const clearButton = document.getElementById('clearRankingsFilters');
        const countNode = document.getElementById('rankingsCount');
        const chipRow = document.getElementById('rankingsActiveFilterRow');
        const tableBody = document.getElementById('rankingsTableBody');
        const jumpButtons = Array.from(document.querySelectorAll('[data-rankings-limit]'));

        let limit = 'all';

        const normalized = (value) => (value || '').toString().trim().toLowerCase();
        const sorters = {
          power: (a, b) => parseFloat(b.dataset.power) - parseFloat(a.dataset.power),
          resume: (a, b) => parseFloat(b.dataset.resume) - parseFloat(a.dataset.resume),
          rank: (a, b) => parseInt(a.dataset.rank, 10) - parseInt(b.dataset.rank, 10),
          team: (a, b) => a.dataset.team.localeCompare(b.dataset.team),
        };

        function renderChips(tokens) {
          chipRow.innerHTML = '';
          if (!tokens.length) {
            chipRow.hidden = true;
            return;
          }
          chipRow.hidden = false;
          tokens.forEach((token) => {
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            chip.textContent = token;
            chipRow.appendChild(chip);
          });
        }

        function applyBoardState() {
          const query = normalized(searchInput.value);
          const level = levelFilter.value;
          const conference = conferenceFilter.value;
          const sorter = sorters[sortMode.value] || sorters.rank;

          const filtered = rows.filter((row) => {
            const matchesQuery = !query || row.dataset.search.includes(query);
            const matchesLevel = level === 'ALL' || row.dataset.level === level;
            const matchesConference = conference === 'ALL' || row.dataset.conference === conference;
            return matchesQuery && matchesLevel && matchesConference;
          });

          const sorted = [...filtered].sort(sorter);
          rows.forEach((row) => {
            row.style.display = 'none';
          });

          const limited = limit === 'all' ? sorted : sorted.slice(0, limit);
          limited.forEach((row) => {
            row.style.display = '';
            tableBody.appendChild(row);
          });

          countNode.textContent = String(limited.length);

          const chipTokens = [];
          if (query) chipTokens.push(`Search: ${searchInput.value.trim()}`);
          if (level !== 'ALL') chipTokens.push(`Level: ${level}`);
          if (conference !== 'ALL') chipTokens.push(`Conference: ${conference}`);
          chipTokens.push(`Sort: ${sortMode.options[sortMode.selectedIndex].text}`);
          chipTokens.push(limit === 'all' ? 'Range: All teams' : `Range: Top ${limit}`);
          renderChips(chipTokens);
        }

        [searchInput, levelFilter, conferenceFilter, sortMode].forEach((node) => {
          node.addEventListener('input', applyBoardState);
          node.addEventListener('change', applyBoardState);
        });

        jumpButtons.forEach((button) => {
          button.addEventListener('click', () => {
            jumpButtons.forEach((item) => item.classList.remove('is-active'));
            button.classList.add('is-active');
            limit = button.dataset.rankingsLimit === 'all' ? 'all' : parseInt(button.dataset.rankingsLimit, 10);
            applyBoardState();
          });
        });

        clearButton.addEventListener('click', () => {
          searchInput.value = '';
          levelFilter.value = 'ALL';
          conferenceFilter.value = 'ALL';
          sortMode.value = 'rank';
          limit = 'all';
          jumpButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.rankingsLimit === 'all'));
          applyBoardState();
        });

        applyBoardState();
      })();
    """


def _programs_explorer_script() -> str:
    return """
      (() => {
        const rows = Array.from(document.querySelectorAll('#programExplorerBody tr.program-explorer-row'));
        if (!rows.length) return;

        const searchInput = document.getElementById('programSearch');
        const levelFilter = document.getElementById('programLevelFilter');
        const sortMode = document.getElementById('programSort');
        const countNode = document.getElementById('programVisibleCount');
        const tableBody = document.getElementById('programExplorerBody');

        const normalized = (value) => (value || '').toString().trim().toLowerCase();
        const numericValue = (row, key, fallback = Number.NEGATIVE_INFINITY) => {
          const raw = row.dataset[key];
          if (raw === undefined || raw === null || raw === '') return fallback;
          const parsed = Number(raw);
          return Number.isFinite(parsed) ? parsed : fallback;
        };
        const teamName = (row) => {
          const anchor = row.querySelector('.team-link');
          return anchor ? anchor.textContent.trim() : '';
        };
        const sorters = {
          'current-rank': (a, b) => {
            const aRank = numericValue(a, 'currentRank', 9999);
            const bRank = numericValue(b, 'currentRank', 9999);
            if (aRank !== bRank) return aRank - bRank;
            return teamName(a).localeCompare(teamName(b));
          },
          'latest-power': (a, b) => numericValue(b, 'latestPower') - numericValue(a, 'latestPower') || teamName(a).localeCompare(teamName(b)),
          'peak-power': (a, b) => numericValue(b, 'peakPower') - numericValue(a, 'peakPower') || teamName(a).localeCompare(teamName(b)),
          'best-resume': (a, b) => numericValue(b, 'bestResume') - numericValue(a, 'bestResume') || teamName(a).localeCompare(teamName(b)),
          'loaded-seasons': (a, b) => numericValue(b, 'loadedSeasons', 0) - numericValue(a, 'loadedSeasons', 0) || teamName(a).localeCompare(teamName(b)),
          'current-vs-baseline': (a, b) => numericValue(b, 'currentVsBaseline') - numericValue(a, 'currentVsBaseline') || teamName(a).localeCompare(teamName(b)),
          volatility: (a, b) => numericValue(b, 'volatility', 0) - numericValue(a, 'volatility', 0) || teamName(a).localeCompare(teamName(b)),
        };

        function applyExplorerState() {
          const query = normalized(searchInput?.value);
          const level = levelFilter?.value || 'ALL';
          const sorter = sorters[sortMode?.value] || sorters['current-rank'];

          const filtered = rows.filter((row) => {
            const matchesQuery = !query || (row.dataset.search || '').includes(query);
            const matchesLevel = level === 'ALL' || row.dataset.level === level;
            return matchesQuery && matchesLevel;
          });

          const sorted = [...filtered].sort(sorter);
          sorted.forEach((row) => tableBody.appendChild(row));
          if (countNode) countNode.textContent = String(sorted.length);
        }

        [searchInput, levelFilter, sortMode].forEach((node) => {
          if (!node) return;
          node.addEventListener('input', applyExplorerState);
          node.addEventListener('change', applyExplorerState);
        });

        applyExplorerState();
      })();
    """


def _matchup_tool_script() -> str:
    return """
      (() => {
        const payloadNode = document.getElementById('matchupPayload');
        const teamASelect = document.getElementById('matchupTeamA');
        const teamBSelect = document.getElementById('matchupTeamB');
        const locationSelect = document.getElementById('matchupLocation');
        if (!payloadNode || !teamASelect || !teamBSelect || !locationSelect) return;

        let payload = null;
        try {
          payload = JSON.parse(payloadNode.textContent || '{}');
        } catch (error) {
          console.error('Could not parse matchup payload', error);
          return;
        }

        const teams = Array.isArray(payload.teams) ? payload.teams : [];
        if (teams.length < 2) return;
        const teamMap = new Map(teams.map((team) => [team.slug, team]));

        const erf = (x) => {
          const sign = x < 0 ? -1 : 1;
          const absX = Math.abs(x);
          const a1 = 0.254829592;
          const a2 = -0.284496736;
          const a3 = 1.421413741;
          const a4 = -1.453152027;
          const a5 = 1.061405429;
          const p = 0.3275911;
          const t = 1 / (1 + p * absX);
          const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX);
          return sign * y;
        };

        const normalCdf = (value) => 0.5 * (1 + erf(value / Math.sqrt(2)));

        const formatSigned = (value, digits = 2) => `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`;
        const formatPower = (value) => formatSigned(Number(value || 0), 1);
        const formatResume = (value) => `${Math.round(Number(value || 0))}`;
        const formatResumeGap = (value) => formatSigned(Number(value || 0), 0);
        const resolveLocationLabel = (teamA, teamB, location) => {
          if (location === 'team-a-home') return `${teamA.team_name} home field`;
          if (location === 'team-b-home') return `${teamB.team_name} home field`;
          return 'neutral field';
        };

        function project(teamA, teamB, location) {
          const basePoints = Number(payload.basePoints || 28.0);
          const homeFieldAdvantage = Number(payload.homeFieldAdvantage || 2.3);
          let home = teamA;
          let away = teamB;
          let teamAIsHome = true;
          let homeBonus = 0;

          if (location === 'team-a-home') {
            home = teamA;
            away = teamB;
            teamAIsHome = true;
            homeBonus = homeFieldAdvantage;
          } else if (location === 'team-b-home') {
            home = teamB;
            away = teamA;
            teamAIsHome = false;
            homeBonus = homeFieldAdvantage;
          }

          const paceAdjustment = 0.5 * (Number(teamA.tempo_rating || 0) + Number(teamB.tempo_rating || 0));
          const predictedHomePoints =
            basePoints +
            Number(home.offense_rating || 0) -
            Number(away.defense_rating || 0) +
            0.5 * (Number(home.special_teams_rating || 0) - Number(away.special_teams_rating || 0)) +
            0.5 * homeBonus +
            paceAdjustment;
          const predictedAwayPoints =
            basePoints +
            Number(away.offense_rating || 0) -
            Number(home.defense_rating || 0) +
            0.5 * (Number(away.special_teams_rating || 0) - Number(home.special_teams_rating || 0)) -
            0.5 * homeBonus +
            paceAdjustment;

          const teamAPoints = teamAIsHome ? predictedHomePoints : predictedAwayPoints;
          const teamBPoints = teamAIsHome ? predictedAwayPoints : predictedHomePoints;
          const spreadForA = teamAPoints - teamBPoints;
          const winProbabilityA = normalCdf((spreadForA / 14.5));

          return {
            teamAPoints,
            teamBPoints,
            spreadForA,
            predictedTotal: teamAPoints + teamBPoints,
            winProbabilityA,
            resumeGap: Number(teamA.resume_display || 0) - Number(teamB.resume_display || 0),
            powerGap: Number(teamA.power_display || 0) - Number(teamB.power_display || 0),
            locationLabel: resolveLocationLabel(teamA, teamB, location),
          };
        }

        function updateTeam(slot, team) {
          const link = document.getElementById(`${slot}Link`);
          const meta = document.getElementById(`${slot}Meta`);
          const record = document.getElementById(`${slot}Record`);
          const power = document.getElementById(`${slot}Power`);
          const resume = document.getElementById(`${slot}Resume`);
          const recent = document.getElementById(`${slot}Recent`);
          const best = document.getElementById(`${slot}Best`);
          const worst = document.getElementById(`${slot}Worst`);
          if (link) {
            link.textContent = team.team_name;
            link.setAttribute('href', team.team_url);
          }
          if (meta) meta.textContent = `#${team.rank} | ${team.level_code} | ${team.conference}`;
          if (record) record.textContent = team.record;
          if (power) power.textContent = formatPower(team.power_display || 0);
          if (resume) resume.textContent = formatResume(team.resume_display || 0);
          if (recent) recent.textContent = team.recent_form || '--';
          if (best) best.textContent = `Best signal: ${team.best_result || '--'}`;
          if (worst) worst.textContent = `Stress point: ${team.worst_result || '--'}`;
        }

        function ensureDistinctTeams() {
          if (teamASelect.value !== teamBSelect.value) return;
          const fallback = teams.find((team) => team.slug !== teamASelect.value);
          if (fallback) {
            teamBSelect.value = fallback.slug;
          }
        }

        function render() {
          ensureDistinctTeams();
          const teamA = teamMap.get(teamASelect.value) || teamMap.get(payload.defaultTeamA) || teams[0];
          const teamB = teamMap.get(teamBSelect.value) || teamMap.get(payload.defaultTeamB) || teams[1];
          const location = locationSelect.value || 'neutral';
          const projection = project(teamA, teamB, location);

          const favoriteName = projection.spreadForA >= 0 ? teamA.team_name : teamB.team_name;
          const favoriteSpread = Math.abs(projection.spreadForA).toFixed(1);
          const headline = document.getElementById('matchupHeadline');
          const summary = document.getElementById('matchupSummary');
          const spread = document.getElementById('matchupSpread');
          const winProb = document.getElementById('matchupWinProb');
          const total = document.getElementById('matchupTotal');
          const resumeGap = document.getElementById('matchupResumeGap');

          if (headline) headline.textContent = `${teamA.team_name} vs. ${teamB.team_name}`;
          if (summary) {
            summary.textContent =
              `${favoriteName} would be favored by ${favoriteSpread} points on ${projection.locationLabel}. ` +
              `Projected score: ${teamA.team_name} ${projection.teamAPoints.toFixed(1)}, ${teamB.team_name} ${projection.teamBPoints.toFixed(1)}.`;
          }
          if (spread) spread.textContent = `${favoriteName} -${favoriteSpread}`;
          if (winProb) {
            const favoredTeam = projection.winProbabilityA >= 0.5 ? teamA.team_name : teamB.team_name;
            const favoredProb = Math.max(projection.winProbabilityA, 1 - projection.winProbabilityA) * 100;
            winProb.textContent = `${favoredProb.toFixed(1)}% ${favoredTeam}`;
          }
          if (total) total.textContent = projection.predictedTotal.toFixed(1);
          if (resumeGap) resumeGap.textContent = formatResumeGap(projection.resumeGap);

          updateTeam('teamA', teamA);
          updateTeam('teamB', teamB);
        }

        [teamASelect, teamBSelect, locationSelect].forEach((node) => {
          node.addEventListener('change', render);
          node.addEventListener('input', render);
        });

        document.querySelectorAll('.scenario-card').forEach((button) => {
          button.addEventListener('click', () => {
            if (button.dataset.teamA) teamASelect.value = button.dataset.teamA;
            if (button.dataset.teamB) teamBSelect.value = button.dataset.teamB;
            if (button.dataset.location) locationSelect.value = button.dataset.location;
            render();
            const panel = document.querySelector('.tool-panel');
            if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
          });
        });

        if (!teamASelect.value) teamASelect.value = payload.defaultTeamA || teams[0].slug;
        if (!teamBSelect.value) teamBSelect.value = payload.defaultTeamB || teams[1].slug;
        render();
      })();
    """


def _game_blurb(team_id: int, row: dict[str, Any]) -> str:
    is_home = int(row["home_team_id"]) == team_id
    opponent = str(row["away_team_name"] if is_home else row["home_team_name"])
    team_points = row["home_points"] if is_home else row["away_points"]
    opp_points = row["away_points"] if is_home else row["home_points"]
    if team_points is None or opp_points is None:
        return f"vs {opponent}"
    result = "beat" if int(team_points) > int(opp_points) else "lost to" if int(team_points) < int(opp_points) else "drew with"
    return f"{result} {opponent} {team_points}-{opp_points}"


def _result_token(team_id: int, row: dict[str, Any]) -> str:
    is_home = int(row["home_team_id"]) == team_id
    team_points = row["home_points"] if is_home else row["away_points"]
    opp_points = row["away_points"] if is_home else row["home_points"]
    if team_points is None or opp_points is None:
        return f"W{row.get('week')}"
    prefix = "W" if int(team_points) > int(opp_points) else "L" if int(team_points) < int(opp_points) else "T"
    return f"{prefix}{row.get('week')}"


def _rank_change_class(value: int) -> str:
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def _rank_change_text(value: int) -> str:
    return f"{value:+d}" if value else "0"


def _trend_path_values(team_data: dict[str, Any]) -> list[float]:
    values = [float(value) for value in team_data.get("rating_path") or [] if value is not None]
    if len(values) >= 2:
        return values[-6:]
    ranking: RankingRow = team_data["ranking"]
    baseline = ranking.power_rating
    delta = ranking.rank_change * 0.18
    return [baseline - 0.45 - delta, baseline - 0.18, baseline - 0.08, baseline + delta, baseline]


def _sparkline(values: list[float]) -> str:
    width = 80
    height = 24
    padding = 2
    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 1.0)
    points = []
    for index, value in enumerate(values):
        x = padding + (index * (width - 2 * padding) / max(1, len(values) - 1))
        y = height - padding - ((value - min_value) / span) * (height - 2 * padding)
        points.append(f"{x:.1f},{y:.1f}")
    return f'<svg viewBox="0 0 {width} {height}" class="spark-svg"><polyline fill="none" stroke="#5a708c" stroke-width="2.2" points="{" ".join(points)}"></polyline></svg>'


def _level_color(level_code: str) -> str:
    return {
        "FBS": "#111111",
        "FCS": "#3657ff",
        "DII": "#c96a10",
        "DIII": "#7c4dff",
    }.get(level_code, "#6c655d")


def _confidence_label(value: float) -> str:
    if value >= 55:
        return "High"
    if value >= 30:
        return "Medium"
    return "Fragile"


def _confidence_tone_class(value: float) -> str:
    if value >= 55:
        return "confidence-high"
    if value >= 30:
        return "confidence-medium"
    return "confidence-fragile"


def _latest_local_week(db: Database, season_year: int) -> int:
    row = db.query_one(
        """
        select max(week) as week
        from games
        where season_year = %(season_year)s
        """,
        {"season_year": season_year},
    )
    return int(row["week"]) if row and row.get("week") is not None else 0


# =============================================================================
# Fan intelligence renderers
# =============================================================================


def _is_offseason_now(now: datetime | None = None) -> bool:
    current = now or datetime.now()
    if current.month in (2, 3, 4, 5, 6, 7):
        return True
    if current.month == 8 and current.day < 15:
        return True
    if current.month == 1:
        return True
    return False


def _render_cohort_panel(cohort_rows: list[dict[str, Any]], team_name: str) -> str:
    """Cohort panel — STRATEGY §4 small-multiples bars per (team, cohort) cell.

    Reads rows from `team_cohort_week` pre-filtered to the team's most recent
    week. Respects the effective-N floor rule: cells with sentiment_score IS
    NULL render as "below floor" badges, never as numbers. Empty input ->
    compact "Awaiting Signal" fallback per STRATEGY §1 principle #1.

    TASK 8.3 (2026-04-23). Does NOT hook into JS; pure inline SVG + CSS.
    """
    FLOOR_MIN = 30.0  # STRATEGY §4
    # A cell counts as "shown" when effective_n clears the floor, regardless
    # of whether sentiment itself is populated. Cells below the floor are
    # suppressed (never a fake number).
    shown = [r for r in cohort_rows if (r.get("effective_n") or 0) >= FLOOR_MIN]
    if not shown:
        return (
            '<section class="section cohort-panel cohort-panel--empty" aria-label="Cohort sentiment">'
            '<div class="section-head">'
            '<h2>Cohort Signal</h2>'
            '<p class="section-sub">How the fan conversation splits across age, lens, and geography cohorts.</p>'
            '</div>'
            '<div class="cohort-panel-empty-body">'
            '<p><strong>Awaiting Signal.</strong> '
            'No cohort cell for this team-week cleared the effective-N floor '
            '(&ge;30 weighted docs). '
            'See <a href="../methodology/fan-intelligence.html">methodology &raquo; effective sample size</a>.</p>'
            '</div>'
            '</section>'
        )
    week_label = shown[0].get("week") or ""
    confidence = shown[0].get("confidence_tier") or "?"
    bars = []
    # Sort with highest effective_n first for visual anchor
    for row in sorted(shown, key=lambda r: -(r.get("effective_n") or 0)):
        cohort = str(row.get("cohort") or "?")
        sentiment_raw = row.get("sentiment_score")
        eff_n = float(row.get("effective_n") or 0)
        n_cls = "cohort-n--thin" if eff_n < 100 else "cohort-n--full"
        if sentiment_raw is None:
            # Volume-only cell — honest "n= shown, no sentiment number yet"
            bars.append(
                f'<li class="cohort-row cohort-row--volume-only">'
                f'<span class="cohort-label">{escape(cohort)}</span>'
                f'<span class="cohort-bar-track">'
                f'<span class="cohort-bar cohort-bar--mute" style="width:100%"></span>'
                f'</span>'
                f'<span class="cohort-score cohort-score--mute" title="Volume above floor; no sentiment data yet">&mdash;</span>'
                f'<span class="cohort-n {n_cls}">n={eff_n:.0f}</span>'
                f'</li>'
            )
            continue
        sentiment = float(sentiment_raw)
        pct = max(-100.0, min(100.0, sentiment * 100))
        bar_cls = "cohort-bar--pos" if sentiment >= 0 else "cohort-bar--neg"
        width = abs(pct)
        bars.append(
            f'<li class="cohort-row">'
            f'<span class="cohort-label">{escape(cohort)}</span>'
            f'<span class="cohort-bar-track">'
            f'<span class="cohort-bar {bar_cls}" style="width:{width:.1f}%"></span>'
            f'</span>'
            f'<span class="cohort-score">{sentiment:+.2f}</span>'
            f'<span class="cohort-n {n_cls}">n={eff_n:.0f}</span>'
            f'</li>'
        )
    return (
        '<section class="section cohort-panel" aria-label="Cohort sentiment">'
        '<div class="section-head">'
        f'<h2>Cohort Signal</h2>'
        '<p class="section-sub">Per-cohort sentiment for '
        f'{escape(team_name)}, week {escape(week_label)}. Confidence tier: '
        f'<strong>{escape(confidence)}</strong>. '
        '<a href="../methodology/fan-intelligence.html">How we weight cohorts &raquo;</a></p>'
        '</div>'
        f'<ul class="cohort-list">{"".join(bars)}</ul>'
        '</section>'
    )


def _fetch_cohort_rows_for_team(db: Any, team_id: int) -> list[dict[str, Any]]:
    """Return the most-recent-week cohort_week rows for a team. Best-effort:
    returns [] on any error so the cohort panel renders Awaiting Signal.
    """
    try:
        latest = db.query_one(
            "select max(week) as w from team_cohort_week where team_id = :t",
            {"t": team_id},
        )
        if not latest or not latest.get("w"):
            return []
        return db.query_all(
            "select cohort, week, effective_n, sentiment_score, volume, "
            "confidence_tier from team_cohort_week "
            "where team_id = :t and week = :w",
            {"t": team_id, "w": latest["w"]},
        )
    except Exception:
        return []


def _render_team_mood_card(mood: dict[str, Any], team_name: str) -> str:
    """Team Mood Card — flagship fan-intelligence surface on team pages.

    When the conversation pipeline has collected enough data, renders a
    premium editorial card with Fan Pulse, Reality Check, Swing, Cohesion,
    Respect Gap, Rival Heat and Top Storylines. When the signal hasn't
    cleared the publish gate, renders a compact offseason-aware empty
    state instead of seven stacked "Awaiting Signal" tiles.
    """

    if not mood:
        return ""

    has_data = bool(mood.get("has_data"))

    if not has_data:
        sample = mood.get("sample") or {}
        sample_mentions = int(sample.get("mentions") or 0)
        sample_authors = int(sample.get("authors") or 0)
        offseason = _is_offseason_now()
        if offseason:
            eyebrow = "Team Mood Card &mdash; Offseason Mode"
            headline = f"{team_name} fan conversation is quiet right now."
            body = (
                "The Mood Card lights up during the season, when live fan, national, and rival chatter "
                "clears the publish gate. In the offseason we hold the frame open rather than print "
                "fake precision. Live signal returns once weekly conversation volume rebuilds."
            )
            footer_copy = "Re-opens with the 2026 season. Follow Power, Resume, and Program History year-round."
        else:
            eyebrow = "Team Mood Card"
            headline = f"No conversation signal yet this week for {team_name}."
            threshold = (
                f"We publish once {sample_mentions or 12}+ clean mentions from "
                f"{sample_authors or 'several'} distinct authors clear the gate."
            )
            body = (
                "Fan Pulse, Respect Gap, Swing, Cohesion, Rival Heat, and Top Storylines all light up "
                f"together when the weekly sample clears that bar. {threshold}"
            )
            footer_copy = "Source: public conversation collected from Reddit & supplemental feeds."
        return f"""
    <section class="section mood-card-section">
      <article class="panel mood-card is-waiting mood-card-empty">
        <div class="mood-card-head">
          <div class="mood-card-title">
            <p class="eyebrow mood-eyebrow">{eyebrow}</p>
            <h2>{escape(headline)}</h2>
            <p class="mood-card-subtitle">{escape(body)}</p>
          </div>
        </div>
        <footer class="mood-card-footer">
          <span>{escape(footer_copy)}</span>
        </footer>
      </article>
    </section>
    """

    confidence = mood.get("confidence") or {}
    sample = mood.get("sample") or {}
    belief = mood.get("belief") or {}
    reality_gap = mood.get("reality_gap") or {}
    respect_gap = mood.get("respect_gap") or {}
    swing = mood.get("swing") or {}
    cohesion = mood.get("cohesion") or {}
    rival_heat = mood.get("rival_heat") or {}
    storylines = mood.get("storylines") or []
    archetype = mood.get("archetype")

    confidence_label = escape(str(confidence.get("label") or "Reading the room"))
    sample_mentions = int(sample.get("mentions") or 0)
    sample_authors = int(sample.get("authors") or 0)
    sarcasm_risk = escape(str(sample.get("sarcasm_risk") or "low").title())
    updated_label = escape(str(mood.get("updated_label") or ""))
    status_class = "is-live" if has_data else "is-waiting"

    # Belief band (top of card)
    belief_label = escape(str(belief.get("label") or "Reading the room"))
    belief_narrative = escape(str(belief.get("narrative") or ""))
    belief_score_raw = belief.get("score")
    belief_pct = 50.0
    belief_score_text = "—"
    if isinstance(belief_score_raw, (int, float)):
        belief_pct = max(0.0, min(100.0, (float(belief_score_raw) + 100.0) / 2.0))
        belief_score_text = f"{belief_score_raw:+.0f}"

    # Reality gap
    reality_label = escape(str(reality_gap.get("label") or "Reading the room"))
    reality_narrative = escape(str(reality_gap.get("narrative") or ""))
    reality_available = bool(reality_gap.get("available"))
    reality_score_text = ""
    if reality_available and reality_gap.get("score") is not None:
        reality_score_text = f"{float(reality_gap['score']):+.0f} belief vs structure"

    # Respect gap
    respect_label = escape(str(respect_gap.get("label") or "Reading the room"))
    respect_narrative = escape(str(respect_gap.get("narrative") or ""))
    respect_available = bool(respect_gap.get("available"))
    respect_detail = ""
    if respect_available:
        fan_score = respect_gap.get("fan_score")
        nat_score = respect_gap.get("national_score")
        if isinstance(fan_score, (int, float)) and isinstance(nat_score, (int, float)):
            respect_detail = f"Fan {fan_score:+.0f} &middot; National {nat_score:+.0f}"

    # Swing
    swing_label = escape(str(swing.get("label") or "Reading the room"))
    swing_narrative = escape(str(swing.get("narrative") or ""))
    swing_available = bool(swing.get("available"))
    swing_detail = ""
    if swing_available and swing.get("week_over_week_delta") is not None:
        swing_detail = f"This week: {float(swing['week_over_week_delta']):+.0f}"

    # Cohesion
    cohesion_label = escape(str(cohesion.get("label") or "Reading the room"))
    cohesion_narrative = escape(str(cohesion.get("narrative") or ""))
    cohesion_pos = float(cohesion.get("positive_share") or 0.0) * 100
    cohesion_neg = float(cohesion.get("negative_share") or 0.0) * 100
    cohesion_neu = max(0.0, 100 - cohesion_pos - cohesion_neg)

    # Rival heat
    rival_label = escape(str(rival_heat.get("label") or "Reading the room"))
    rival_narrative = escape(str(rival_heat.get("narrative") or ""))
    rival_available = bool(rival_heat.get("available"))
    rival_detail = ""
    if rival_available and rival_heat.get("mentions"):
        rival_detail = f"{int(rival_heat['mentions'])} rival posts this week"

    archetype_chip = ""
    if archetype:
        archetype_chip = f'<span class="mood-archetype-chip">{escape(str(archetype))}</span>'

    if storylines:
        storyline_items = "".join(
            f"""
            <li class="mood-storyline-item">
              <span class="mood-storyline-rank">#{escape(str(item.get('rank') or '•'))}</span>
              <div class="mood-storyline-body">
                <strong>{escape(str(item.get('label') or 'Unlabeled storyline'))}</strong>
                <p>{escape(str(item.get('summary') or ''))}</p>
              </div>
            </li>
            """
            for item in storylines[:4]
        )
        storyline_block = f"""
        <div class="mood-storylines">
          <h3>Top Storylines</h3>
          <ol class="mood-storyline-list">{storyline_items}</ol>
        </div>
        """
    elif has_data:
        storyline_block = """
        <div class="mood-storylines mood-storylines-empty">
          <h3>Top Storylines</h3>
          <p>No extracted storylines have cleared the publish bar this week.</p>
        </div>
        """
    else:
        storyline_block = """
        <div class="mood-storylines mood-storylines-empty">
          <h3>Top Storylines</h3>
          <p>Storylines light up automatically once the weekly conversation sample clears the publish gate.</p>
        </div>
        """

    waiting_banner = ""
    if not has_data:
        waiting_banner = f"""
        <p class="mood-waiting-banner">
          <span class="mood-waiting-dot"></span>
          Awaiting fan sample &mdash; we only publish with at least {escape(str(sample_mentions)) if sample_mentions else '12'} clean mentions from {escape(str(sample_authors)) if sample_authors else 'several'} distinct authors. Until then, this card shows the frame, not the number.
        </p>
        """

    sample_detail = f"{sample_mentions} fan mentions" if has_data else "Fan sample not yet published"
    sarcasm_row = ""
    if has_data:
        sarcasm_row = f'<span class="mood-meta-chip">Sarcasm risk: {sarcasm_risk}</span>'

    return f"""
    <section class="section mood-card-section">
      <article class="panel mood-card {status_class}" data-mood-card>
        <div class="mood-card-head">
          <div class="mood-card-title">
            <p class="eyebrow mood-eyebrow">Team Mood Card</p>
            <h2>{escape(team_name)} Fanbase, {escape(updated_label)}</h2>
            <p class="mood-card-subtitle">
              How this fanbase is feeling, how outsiders are talking, and what swung in the last seven days.
            </p>
          </div>
          <div class="mood-card-meta">
            {archetype_chip}
            <span class="mood-meta-chip">Confidence: {confidence_label}</span>
            {sarcasm_row}
            <span class="mood-meta-chip mood-meta-chip-muted">{escape(sample_detail)}</span>
          </div>
        </div>

        {waiting_banner}

        <div class="mood-hero">
          <div class="mood-hero-score">
            <span class="mood-hero-score-label">Fan Pulse</span>
            <strong class="mood-hero-score-value">{belief_label}</strong>
            <span class="mood-hero-score-number">{belief_score_text}</span>
          </div>
          <div class="mood-hero-meter" role="presentation">
            <div class="mood-meter-track">
              <div class="mood-meter-fill" style="width:{belief_pct:.1f}%"></div>
              <div class="mood-meter-markers">
                <span>Bearish</span>
                <span>Mixed</span>
                <span>Bullish</span>
              </div>
            </div>
            <p class="mood-hero-narrative">{belief_narrative}</p>
          </div>
        </div>

        <div class="mood-axis-grid">
          <article class="mood-axis">
            <header><span>Reality Check</span><strong>{reality_label}</strong></header>
            <p>{reality_narrative}</p>
            {f'<span class="mood-axis-detail">{escape(reality_score_text)}</span>' if reality_score_text else ''}
          </article>
          <article class="mood-axis">
            <header><span>Respect Gap</span><strong>{respect_label}</strong></header>
            <p>{respect_narrative}</p>
            {f'<span class="mood-axis-detail">{respect_detail}</span>' if respect_detail else ''}
          </article>
          <article class="mood-axis">
            <header><span>Swing Meter</span><strong>{swing_label}</strong></header>
            <p>{swing_narrative}</p>
            {f'<span class="mood-axis-detail">{escape(swing_detail)}</span>' if swing_detail else ''}
          </article>
          <article class="mood-axis mood-axis-cohesion">
            <header><span>Cohesion</span><strong>{cohesion_label}</strong></header>
            <p>{cohesion_narrative}</p>
            <div class="mood-cohesion-stack" role="presentation">
              <span class="mood-cohesion-seg mood-cohesion-pos" style="width:{cohesion_pos:.1f}%"></span>
              <span class="mood-cohesion-seg mood-cohesion-neu" style="width:{cohesion_neu:.1f}%"></span>
              <span class="mood-cohesion-seg mood-cohesion-neg" style="width:{cohesion_neg:.1f}%"></span>
            </div>
          </article>
          <article class="mood-axis">
            <header><span>Rival Heat</span><strong>{rival_label}</strong></header>
            <p>{rival_narrative}</p>
            {f'<span class="mood-axis-detail">{escape(rival_detail)}</span>' if rival_detail else ''}
          </article>
        </div>

        {storyline_block}

        <footer class="mood-card-footer">
          <span>Source: public conversation collected from Reddit &amp; supplemental feeds.</span>
          <span>We split fan, national, and rival audiences before scoring.</span>
        </footer>
      </article>
    </section>
    """


def _render_fan_intel_home_section(
    board: dict[str, Any],
    prefix: str = "teams/",
    editorial_context: dict[str, Any] | None = None,
) -> str:
    """Editorial fan-intelligence block for the homepage."""

    editorial_context = editorial_context or {}
    has_data = bool(board.get("has_data"))
    active_phase = editorial_context.get("active_phase") or {}
    is_offseason = bool(editorial_context.get("is_offseason"))
    board_title = "The Offseason Mood Board" if is_offseason else "The Mood Board"
    panic_title = str(active_phase.get("panic_label") or "Panic Meter") if is_offseason else "Most Panicked Fanbases"
    board_note = (
        str(active_phase.get("board_note") or "")
        if is_offseason
        else "Belief, respect, rivalry heat. Pulled fresh from this week's fan, national, and rival chatter. Confidence labels travel with every row; we would rather show a band than print a fake number."
    )

    def render_list(items: list[dict[str, Any]], empty_hint: str) -> str:
        if not items:
            return f'<p class="intel-empty">{escape(empty_hint)}</p>'
        rows = []
        for index, item in enumerate(items, start=1):
            slug = str(item.get("slug") or "")
            team_name = escape(str(item.get("team_name") or ""))
            level = escape(str(item.get("level_code") or ""))
            headline = escape(str(item.get("headline") or ""))
            subtext = escape(str(item.get("subtext") or ""))
            href = f"{prefix}{slug}.html" if slug else "#"
            rows.append(
                f"""
                <li class="intel-card-row">
                  <a href="{href}" class="intel-row-inner">
                    <span class="intel-row-rank">{index}</span>
                    <div class="intel-row-body">
                      <strong>{team_name}</strong>
                      <span class="intel-row-level">{level}</span>
                      <span class="intel-row-headline">{headline}</span>
                      <span class="intel-row-sub">{subtext}</span>
                    </div>
                  </a>
                </li>
                """
            )
        return f'<ol class="intel-card-list">{"".join(rows)}</ol>'

    if not has_data:
        if is_offseason:
            module_cards = "".join(
                f"""
                <article class="panel intel-empty-card">
                  <h3>{escape(str(module))}</h3>
                  <p>{escape(str(active_phase.get("theme") or "Offseason fan-intelligence"))} module. This slot becomes a live card once conversation collection clears the publish bar.</p>
                </article>
                """
                for module in (active_phase.get("modules") or [])
            )
            return f"""
            <section class="section fan-intel-home fan-intel-home-empty">
              <div class="section-head">
                <div>
                  <p class="eyebrow">Fan Intelligence</p>
                  <h2>{escape(board_title)}, Warming Up</h2>
                  <p class="section-note">
                    {escape(str(active_phase.get("label") or "This month"))} should lean into {escape(str(active_phase.get("theme") or "the current offseason frame")).lower()}.
                    Once the conversation sample clears the publish bar, these roadmap cards turn into live belief, panic, respect-gap, and rivalry modules.
                  </p>
                </div>
              </div>
              <div class="intel-empty-grid">
                {module_cards}
              </div>
            </section>
            """
        return """
        <section class="section fan-intel-home fan-intel-home-empty">
          <div class="section-head">
            <div>
              <p class="eyebrow">Fan Intelligence</p>
              <h2>The Mood Board, Warming Up</h2>
              <p class="section-note">
                Fan Pulse, Respect Gap, and Rival Heat leaderboards publish automatically once the weekly conversation collection clears the publish bar.
                Until then, these modules stay intentionally empty rather than printing fake precision.
              </p>
            </div>
          </div>
          <div class="intel-empty-grid">
            <article class="panel intel-empty-card">
              <h3>Biggest Vibe Shifts</h3>
              <p>We flag the sharpest week-over-week belief moves once enough fans are posting.</p>
            </article>
            <article class="panel intel-empty-card">
              <h3>Respect Gap Leaders</h3>
              <p>Teams whose own fans are much higher &mdash; or much lower &mdash; than the national conversation.</p>
            </article>
            <article class="panel intel-empty-card">
              <h3>Rival Heat Leaders</h3>
              <p>Teams living rent-free in rival fanbases this week.</p>
            </article>
            <article class="panel intel-empty-card">
              <h3>Main Character Of The Week</h3>
              <p>Whichever team the broader sport cannot stop talking about.</p>
            </article>
          </div>
        </section>
        """

    return f"""
    <section class="section fan-intel-home">
      <div class="section-head">
        <div>
          <p class="eyebrow">Fan Intelligence</p>
          <h2>{escape(board_title)}</h2>
          <p class="section-note">
            {escape(board_note)}
          </p>
        </div>
      </div>

      <div class="intel-grid">
        <article class="panel intel-card intel-card-shift">
          <div class="intel-card-head">
            <h3>Biggest Vibe Shifts</h3>
            <p class="section-note">Largest week-over-week change in fan belief during the current window.</p>
          </div>
          {render_list(board.get('vibe_shifts') or [], 'Not enough fan sample this week to publish vibe shifts yet.')}
        </article>

        <article class="panel intel-card intel-card-respect">
          <div class="intel-card-head">
            <h3>Respect Gap Leaders</h3>
            <p class="section-note">Fans way higher than the national conversation.</p>
          </div>
          {render_list(board.get('respect_gap_leaders') or [], 'Awaiting a national sample to compare against.')}
        </article>

        <article class="panel intel-card intel-card-doubt">
          <div class="intel-card-head">
            <h3>Country Higher Than The Fans</h3>
            <p class="section-note">Fanbases that are lower on themselves than outsiders are.</p>
          </div>
          {render_list(board.get('respect_gap_doubters') or [], 'No inverse-respect cases cleared this week.')}
        </article>

        <article class="panel intel-card intel-card-rival">
          <div class="intel-card-head">
            <h3>Rival Heat Leaders</h3>
            <p class="section-note">Teams living in rival timelines.</p>
          </div>
          {render_list(board.get('rival_heat_leaders') or [], 'Rival sample is still thin. Coming online as collection scales.')}
        </article>

        <article class="panel intel-card intel-card-main">
          <div class="intel-card-head">
            <h3>{"Main Character Right Now" if is_offseason else "Main Character Of The Week"}</h3>
            <p class="section-note">Whoever the sport cannot stop discussing in this window.</p>
          </div>
          {render_list(board.get('main_characters') or [], 'No team hit main-character volume this week.')}
        </article>

        <article class="panel intel-card intel-card-panic">
          <div class="intel-card-head">
            <h3>{escape(panic_title)}</h3>
            <p class="section-note">Fear-heavy fanbases, especially when the mood is already drifting down.</p>
          </div>
          {render_list(board.get('panicked_fanbases') or [], 'No fanbase has crossed the panic gate this week.')}
        </article>

        <article class="panel intel-card intel-card-civil">
          <div class="intel-card-head">
            <h3>Fanbase Civil War Watch</h3>
            <p class="section-note">Internal disagreement, not just negativity.</p>
          </div>
          {render_list(board.get('polarized') or [], 'No fanbase has crossed the internal-disagreement gate this week.')}
        </article>
      </div>
    </section>
    """


def _render_matchup_argument_theater(board: dict[str, Any], prefix: str = "../teams/") -> str:
    """Matchup-page 'argument theater' — Market vs Mood, Which Fanbase Is Calmer."""

    calmer = sorted(
        board.get("vibe_shifts") or [],
        key=lambda row: row.get("signed_value") or 0,
    )
    panic_source = board.get("panicked_fanbases") or []
    rival_source = board.get("rival_heat_leaders") or []

    def intel_row_block(rows: list[dict[str, Any]], empty_hint: str) -> str:
        if not rows:
            return f'<p class="intel-empty">{escape(empty_hint)}</p>'
        items = []
        for item in rows[:3]:
            slug = str(item.get("slug") or "")
            href = f"{prefix}{slug}.html" if slug else "#"
            team_name = escape(str(item.get("team_name") or ""))
            headline = escape(str(item.get("headline") or ""))
            subtext = escape(str(item.get("subtext") or ""))
            items.append(
                f"""
                <li class="intel-card-row">
                  <a class="intel-row-inner" href="{href}">
                    <div class="intel-row-body">
                      <strong>{team_name}</strong>
                      <span class="intel-row-headline">{headline}</span>
                      <span class="intel-row-sub">{subtext}</span>
                    </div>
                  </a>
                </li>
                """
            )
        return f'<ol class="intel-card-list">{"".join(items)}</ol>'

    return f"""
    <section class="section argument-theater">
      <div class="section-head">
        <div>
          <p class="eyebrow">Argument Theater</p>
          <h2>Market vs Model vs Mood</h2>
          <p class="section-note">
            Two teams walk into a matchup. The model has an opinion. The market has an opinion. The fanbases have two more opinions of their own.
            These are the places they disagree the most.
          </p>
        </div>
      </div>
      <div class="intel-grid argument-grid">
        <article class="panel intel-card intel-card-rival">
          <div class="intel-card-head">
            <h3>Which Fanbase Is Calmer</h3>
            <p class="section-note">Steadiest week-over-week Fan Pulse, lowest swing.</p>
          </div>
          {intel_row_block(calmer, 'Awaiting enough consecutive-week samples to rank calm fanbases.')}
        </article>
        <article class="panel intel-card intel-card-panic">
          <div class="intel-card-head">
            <h3>What Fans Are Afraid Of</h3>
            <p class="section-note">Highest fear share across the board.</p>
          </div>
          {intel_row_block(panic_source, 'No fanbase has crossed the panic gate this week.')}
        </article>
        <article class="panel intel-card intel-card-main">
          <div class="intel-card-head">
            <h3>Rival Timelines On Fire</h3>
            <p class="section-note">Where rival chatter is loudest right now.</p>
          </div>
          {intel_row_block(rival_source, 'Rival sample still thin &mdash; lighting up as collection scales.')}
        </article>
      </div>
    </section>
    """


def _site_css() -> str:
    return """
      /* =======================================================
         FAN INTEL — Premium Editorial Sports UI
         Figma theme tokens
         ======================================================= */
      .skip-link {
        position: absolute;
        top: -40px;
        left: 8px;
        background: #0A0A0A;
        color: #FFFFFF;
        padding: 8px 14px;
        text-decoration: none;
        font-weight: 600;
        border-radius: 4px;
        z-index: 1000;
      }
      .skip-link:focus {
        top: 8px;
        outline: 2px solid #FFB800;
        outline-offset: 2px;
      }
      @media print {
        .topbar, .skip-link, script { display: none !important; }
        body { background: #fff !important; color: #000 !important; }
      }
      /* Keyboard focus — visible ring on all interactive elements */
      a:focus-visible, button:focus-visible, input:focus-visible,
      select:focus-visible, textarea:focus-visible, [tabindex]:focus-visible {
        outline: 2px solid #FFB800;
        outline-offset: 2px;
        border-radius: 2px;
      }
      .team-link.is-unlinked {
        color: var(--muted-foreground, #4a4a4a);
        text-decoration: none;
        cursor: default;
      }
      @import url('https://fonts.googleapis.com/css2?family=Anton&family=Bebas+Neue&family=Inter:wght@400;500;600;700;800&display=swap');

      :root {
        /* Core surface palette (Figma) */
        --background: #FAFAFA;
        --foreground: #0A0A0A;
        --card: #FFFFFF;
        --card-foreground: #0A0A0A;
        --popover: #FFFFFF;
        --popover-foreground: #0A0A0A;

        --primary: #0A0A0A;
        --primary-foreground: #FFFFFF;
        --secondary: #F5F5F5;
        --secondary-foreground: #0A0A0A;

        --muted: #E8E8E8;
        --muted-foreground: #6B6B6B;
        --accent-surface: #1a1a1a;
        --accent-foreground: #FFFFFF;

        --destructive: #DC2626;
        --destructive-foreground: #FFFFFF;
        --success: #16A34A;
        --success-foreground: #FFFFFF;
        --warning: #EA580C;
        --warning-foreground: #FFFFFF;

        --gradient-start: #0A0A0A;
        --gradient-end: #262626;
        --gradient-accent: #DC2626;

        --team-red: #DC2626;
        --team-blue: #2563EB;
        --team-green: #16A34A;
        --team-orange: #EA580C;
        --team-purple: #9333EA;
        --team-gold: #D97706;

        --border: rgba(10, 10, 10, 0.08);
        --border-strong: rgba(10, 10, 10, 0.14);
        --input-background: #F5F5F5;

        --font-display: 'Bebas Neue', 'Anton', 'Inter', sans-serif;
        --font-sans: 'Inter', -apple-system, system-ui, Segoe UI, Roboto, sans-serif;

        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 12px;
        --radius-xl: 16px;

        /* Back-compat tokens referenced by inline styles in HTML */
        --bg: var(--background);
        --ink: var(--foreground);
        --panel: var(--card);
        --line: var(--border);
        --accent: var(--foreground);
        --accent-2: #3f3f3f;
        --gold: var(--team-gold);
        --positive: var(--success);
        --negative: var(--destructive);
        --missing: var(--muted-foreground);

        --board-columns: 72px 72px minmax(240px, 1.6fr) 92px 100px 100px 88px;
      }

      * { box-sizing: border-box; }

      html { scroll-behavior: smooth; }

      body {
        margin: 0;
        background: var(--background);
        color: var(--foreground);
        font-family: var(--font-sans);
        font-size: 16px;
        line-height: 1.55;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        overflow-x: hidden;
      }

      a { color: inherit; text-decoration: none; }
      button { font-family: inherit; cursor: pointer; }

      img, svg { max-width: 100%; display: block; }

      /* Editorial display-font utility */
      .display-head,
      .hero h1, .hero-mast h1,
      .section-head h2, .board-heading h2,
      .team-hero h1,
      .feature-card h3, .scenario-card h3, .story-card h3, .archive-card h3,
      .compare-team-card h2,
      .summary-value,
      .team-rank-chip,
      .team-mark {
        font-family: var(--font-display);
        letter-spacing: 0.01em;
      }

      ::selection { background: var(--foreground); color: #fff; }

      .team-hero-heading {
        display: flex;
        align-items: center;
        gap: 18px;
      }
      .team-hero-logo {
        width: 96px;
        height: 96px;
        object-fit: contain;
        flex: 0 0 auto;
        border-radius: 6px;
        background: transparent;
      }
      @media (min-width: 768px) {
        .team-hero-logo { width: 120px; height: 120px; }
      }

      /* =======================================================
         Layout shell
         ======================================================= */
      .site-shell {
        width: 100%;
        max-width: 1400px;
        margin: 0 auto;
        padding: 0 16px 80px;
      }
      @media (min-width: 768px) {
        .site-shell { padding: 0 24px 96px; }
      }
      @media (min-width: 1024px) {
        .site-shell { padding: 0 32px 120px; }
      }

      .home-shell,
      .team-shell {
        display: flex;
        flex-direction: column;
        gap: 32px;
      }
      @media (min-width: 768px) {
        .home-shell, .team-shell { gap: 48px; }
      }

      /* Full-bleed helper for hero sections */
      .hero-mast,
      .premium-home-hero,
      .hero.team-hero,
      .hero.premium-team-hero {
        position: relative;
        margin-left: calc(50% - 50vw);
        margin-right: calc(50% - 50vw);
        padding-left: max(16px, calc(50vw - 700px));
        padding-right: max(16px, calc(50vw - 700px));
      }

      /* =======================================================
         Navigation / topbar
         ======================================================= */
      .topbar {
        position: sticky;
        top: 0;
        z-index: 50;
        margin-left: calc(50% - 50vw);
        margin-right: calc(50% - 50vw);
        padding: 0 max(16px, calc(50vw - 700px));
        background: rgba(255,255,255,0.95);
        backdrop-filter: saturate(1.4) blur(12px);
        -webkit-backdrop-filter: saturate(1.4) blur(12px);
        border-bottom: 1px solid var(--border-strong);
        display: grid;
        grid-template-columns: auto 1fr auto;
        align-items: center;
        gap: 16px;
        min-height: 64px;
        margin-bottom: 0;
      }
      @media (min-width: 768px) {
        .topbar { min-height: 80px; gap: 24px; }
      }

      .brand {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        color: var(--foreground);
        letter-spacing: 0.02em;
      }
      .brand::before {
        content: 'FI';
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        background: var(--primary);
        color: var(--primary-foreground);
        border-radius: var(--radius-md);
        font-family: var(--font-display);
        font-size: 22px;
        line-height: 1;
      }
      @media (min-width: 768px) {
        .brand::before { width: 48px; height: 48px; font-size: 26px; }
      }
      .brand { font: 600 14px/1.1 var(--font-sans); text-transform: none; }
      .brand::after {
        content: attr(data-tagline);
      }

      .topbar-panels {
        display: contents;
      }

      .nav {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
        min-width: 0;
        justify-content: flex-start;
      }

      .nav-link {
        display: inline-flex;
        align-items: center;
        padding: 8px 14px;
        border-radius: var(--radius-md);
        font: 500 14px/1 var(--font-sans);
        color: var(--foreground);
        border: 1px solid transparent;
        transition: background .15s ease, color .15s ease, border-color .15s ease;
        white-space: nowrap;
      }
      .nav-link:hover { background: var(--secondary); }
      .nav-link.is-current {
        background: var(--accent-surface);
        color: var(--accent-foreground);
      }

      .nav-actions {
        display: flex;
        gap: 8px;
        align-items: center;
        justify-content: flex-end;
      }

      .nav-action {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 10px 16px;
        border-radius: var(--radius-md);
        font: 600 13px/1 var(--font-sans);
        background: transparent;
        color: var(--foreground);
        border: 1px solid transparent;
        transition: background .15s ease, color .15s ease, border-color .15s ease;
        white-space: nowrap;
      }
      .nav-action + .nav-action,
      .nav-action:last-child {
        background: var(--primary);
        color: var(--primary-foreground);
      }
      .nav-action + .nav-action:hover,
      .nav-action:last-child:hover { opacity: 0.9; }
      .nav-action:first-of-type { background: transparent; color: var(--foreground); border-color: transparent; }
      .nav-action:first-of-type:hover { background: var(--secondary); }
      .nav-action.is-current { background: var(--accent-surface); color: var(--accent-foreground); }

      .nav-toggle {
        display: none;
        align-items: center;
        justify-content: center;
        gap: 4px;
        padding: 8px 12px;
        border-radius: var(--radius-md);
        border: 1px solid var(--border-strong);
        background: var(--card);
        color: var(--foreground);
        font: 600 12px/1 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      @media (max-width: 900px) {
        .topbar { grid-template-columns: auto 1fr auto; }
        .topbar-panels {
          display: none;
          grid-column: 1 / -1;
          flex-direction: column;
          padding: 12px 0 20px;
          gap: 10px;
          border-top: 1px solid var(--border);
          margin-top: 8px;
        }
        .topbar.is-open .topbar-panels { display: flex; }
        .topbar.is-open { background: #fff; }
        .nav { flex-direction: column; gap: 2px; }
        .nav-link { width: 100%; padding: 12px 14px; }
        .nav-actions { flex-direction: column; gap: 6px; align-items: stretch; }
        .nav-action { justify-content: center; width: 100%; }
        .nav-toggle { display: inline-flex; }
      }

      /* =======================================================
         Typography primitives
         ======================================================= */
      h1, h2, h3, h4 { margin: 0; font-weight: 600; color: var(--foreground); }

      .eyebrow {
        display: inline-block;
        margin: 0 0 14px;
        padding: 4px 12px;
        background: rgba(255,255,255,0.12);
        backdrop-filter: blur(6px);
        border-radius: 999px;
        font: 500 12px/1.4 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: inherit;
      }

      .hero-mast .eyebrow,
      .premium-home-hero .eyebrow,
      .team-hero .eyebrow {
        background: rgba(255,255,255,0.12);
        color: rgba(255,255,255,0.9);
      }

      .lede {
        margin: 18px 0 0;
        max-width: 760px;
        color: inherit;
        font: 400 17px/1.6 var(--font-sans);
      }
      .mast-copy { margin-left: auto; margin-right: auto; }

      /* Section scaffolding */
      .section {
        margin: 0;
      }
      .section-head {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 20px;
      }
      .section-head h2 {
        font-family: var(--font-display);
        font-size: clamp(28px, 4.2vw, 42px);
        line-height: 1;
        letter-spacing: 0.01em;
        text-transform: uppercase;
      }
      .section-head .section-note {
        margin: 8px 0 0;
        max-width: 680px;
        color: var(--muted-foreground);
        font-size: 15px;
      }
      .compact-head h2 { font-size: clamp(22px, 2.5vw, 28px); }

      .footer-note,
      .muted-note,
      .section-note {
        color: var(--muted-foreground);
        font-size: 14px;
        line-height: 1.55;
      }
      .footer-note { margin-top: 16px; }

      .text-link {
        color: var(--foreground);
        font-weight: 600;
        font-size: 14px;
        border-bottom: 1px solid currentColor;
        padding-bottom: 1px;
      }
      .text-link:hover { opacity: 0.7; }

      /* =======================================================
         Hero: home (premium-home-hero / hero-mast)
         ======================================================= */
      .hero-mast,
      .premium-home-hero {
        padding-top: 56px;
        padding-bottom: 64px;
        background: linear-gradient(135deg, var(--gradient-start) 0%, var(--gradient-end) 50%, var(--gradient-start) 100%);
        color: #fff;
        overflow: hidden;
        text-align: left;
      }
      @media (min-width: 768px) {
        .hero-mast,
        .premium-home-hero { padding-top: 80px; padding-bottom: 104px; }
      }
      .hero-mast::before,
      .premium-home-hero::before {
        content: '';
        position: absolute;
        top: 0; left: 20%;
        width: 420px; height: 420px;
        background: var(--gradient-accent);
        opacity: 0.18;
        border-radius: 50%;
        filter: blur(120px);
        pointer-events: none;
      }
      .hero-mast::after,
      .premium-home-hero::after {
        content: '';
        position: absolute;
        bottom: 0; right: 20%;
        width: 420px; height: 420px;
        background: var(--team-blue);
        opacity: 0.18;
        border-radius: 50%;
        filter: blur(120px);
        pointer-events: none;
      }
      .hero-mast > *,
      .premium-home-hero > * { position: relative; z-index: 1; }

      .hero-mast h1,
      .premium-home-hero h1 {
        font-family: var(--font-display);
        font-size: clamp(32px, 7vw, 76px);
        line-height: 1.02;
        letter-spacing: 0.01em;
        max-width: 14ch;
        color: #fff;
        margin: 0 0 8px;
        text-transform: none;
        overflow-wrap: break-word;
      }
      .premium-home-hero .lede,
      .hero-mast .lede { color: rgba(255,255,255,0.82); font-size: 18px; max-width: 680px; }

      .home-meta-row,
      .premium-meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 28px;
      }
      .meta-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(6px);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 999px;
        color: #fff;
        font-size: 13px;
      }
      .meta-pill span {
        color: rgba(255,255,255,0.7);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 11px;
      }
      .meta-pill strong { font-weight: 600; }
      .panel .meta-pill,
      .section .panel .meta-pill {
        background: var(--secondary);
        border-color: var(--border);
        color: var(--foreground);
        backdrop-filter: none;
      }
      .panel .meta-pill span,
      .section .panel .meta-pill span {
        color: var(--muted-foreground);
      }

      /* =======================================================
         Hero: team / program / player pages
         ======================================================= */
      .hero {
        position: relative;
        padding: 40px 24px;
        border-radius: 0;
        background: var(--card);
        border: none;
        box-shadow: none;
      }

      .hero.team-hero,
      .hero.premium-team-hero {
        padding: 48px max(16px, calc(50vw - 700px));
        margin-top: 0;
        background: linear-gradient(135deg, var(--gradient-start) 0%, var(--gradient-end) 60%, #000 100%);
        color: #fff;
        border-radius: 0;
        overflow: hidden;
      }
      @media (min-width: 768px) {
        .hero.team-hero,
        .hero.premium-team-hero { padding-top: 72px; padding-bottom: 72px; }
      }
      .hero.team-hero::before,
      .hero.premium-team-hero::before {
        content: '';
        position: absolute;
        top: 10%; right: 10%;
        width: 360px; height: 360px;
        background: var(--gradient-accent);
        opacity: 0.18;
        border-radius: 50%;
        filter: blur(120px);
        pointer-events: none;
      }
      .hero.team-hero > *,
      .hero.premium-team-hero > * { position: relative; z-index: 1; }

      .team-breadcrumbs {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 16px;
        font-size: 13px;
        color: var(--muted-foreground);
      }
      .team-breadcrumbs a { color: var(--muted-foreground); }
      .team-breadcrumbs a:hover { color: var(--foreground); }
      .team-breadcrumbs strong { color: var(--foreground); font-weight: 600; }
      .team-shell .team-breadcrumbs { padding: 24px 0 0; }

      .team-hero-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 24px;
      }
      .team-hero h1 {
        font-family: var(--font-display);
        font-size: clamp(42px, 8vw, 72px);
        line-height: 1;
        color: #fff;
        text-transform: uppercase;
      }
      .team-hero-sub {
        margin: 8px 0 0;
        color: rgba(255,255,255,0.8);
        font-size: 15px;
      }
      .team-rank-chip {
        padding: 10px 16px;
        background: rgba(255,255,255,0.14);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 999px;
        color: #fff;
        font-family: var(--font-display);
        font-size: 18px;
        letter-spacing: 0.04em;
      }

      .team-stat-ribbon {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin: 0 0 24px;
      }
      @media (min-width: 680px) {
        .team-stat-ribbon { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      }
      .team-stat-tile {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 16px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: var(--radius-lg);
      }
      .team-stat-tile .team-mark {
        flex: 0 0 auto;
        width: 36px; height: 36px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: var(--radius-md);
        font-family: var(--font-display);
        font-size: 15px;
        color: #fff;
      }
      .team-stat-tile > div { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
      .team-stat-tile span { color: rgba(255,255,255,0.7); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
      .team-stat-tile strong { color: #fff; font: 600 22px/1.1 var(--font-sans); }
      .team-stat-tile .submetric { text-transform: none; letter-spacing: 0; font-size: 11px; font-weight: 400; }

      .team-hero-actions,
      .cta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      /* =======================================================
         Buttons & pills
         ======================================================= */
      .button,
      .button-primary,
      .button-secondary {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 12px 20px;
        border-radius: var(--radius-md);
        font: 600 14px/1 var(--font-sans);
        border: 1px solid transparent;
        transition: all .15s ease;
        white-space: nowrap;
      }
      .button-primary { background: #fff; color: var(--foreground); border-color: transparent; }
      .button-primary:hover { background: rgba(255,255,255,0.9); }
      .button-secondary { background: rgba(255,255,255,0.1); color: #fff; border-color: rgba(255,255,255,0.18); backdrop-filter: blur(6px); }
      .button-secondary:hover { background: rgba(255,255,255,0.2); }

      /* When buttons appear on light backgrounds (non-hero), flip palette */
      .site-shell > .home-shell .button-primary,
      .site-shell > .home-shell .button-secondary,
      .panel .button-primary, .panel .button-secondary,
      .section .button-primary, .section .button-secondary {
        /* default white-on-dark */
      }
      .panel .button-primary,
      .section .button-primary,
      .mini-panel .button-primary {
        background: var(--primary);
        color: var(--primary-foreground);
      }
      .panel .button-primary:hover,
      .section .button-primary:hover { opacity: 0.9; }
      .panel .button-secondary,
      .section .button-secondary,
      .mini-panel .button-secondary {
        background: transparent;
        color: var(--foreground);
        border-color: var(--border-strong);
      }
      .panel .button-secondary:hover,
      .section .button-secondary:hover { background: var(--secondary); }

      .pill,
      .phase-summary-chip,
      .metric-guide-pill,
      .mini-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        background: var(--secondary);
        color: var(--foreground);
        font-size: 12px;
        font-weight: 500;
      }
      .metric-guide-strip { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 16px; }
      .phase-pill-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }

      /* State colors */
      .up, .impact-up, .is-positive { color: var(--success); }
      .down, .impact-down, .is-negative { color: var(--destructive); }
      .flat { color: var(--muted-foreground); }

      /* =======================================================
         Panels / cards (generic)
         ======================================================= */
      .panel,
      .mini-panel {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        padding: 24px;
        transition: box-shadow .18s ease, transform .18s ease;
      }
      @media (max-width: 600px) {
        .panel, .mini-panel { padding: 20px; border-radius: var(--radius-lg); }
      }
      .mini-panel { padding: 18px; border-radius: var(--radius-lg); }

      .prose-panel { padding: 28px; }
      .prose-panel p { color: var(--muted-foreground); line-height: 1.7; font-size: 15px; }

      .panel-kicker {
        font: 600 11px/1.2 var(--font-sans);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted-foreground);
        margin: 0 0 6px;
      }

      /* Dashboard grids */
      .dashboard-grid,
      .premium-dashboard-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 20px;
      }
      @media (min-width: 1024px) {
        .dashboard-grid,
        .premium-dashboard-grid {
          grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
          gap: 28px;
        }
      }
      .main-column,
      .side-column,
      .premium-side-column {
        display: flex;
        flex-direction: column;
        gap: 20px;
      }
      .two-up {
        display: grid;
        grid-template-columns: 1fr;
        gap: 20px;
      }
      @media (min-width: 880px) {
        .two-up { grid-template-columns: 1fr 1fr; }
      }

      .feature-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
      }
      @media (min-width: 640px) {
        .feature-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }
      @media (min-width: 1024px) {
        .feature-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
      }
      .scenario-grid,
      .archive-card-grid,
      .pulse-grid,
      .history-level-grid,
      .counts-grid,
      .historical-dna-grid,
      .story-card-grid,
      .impact-card-grid,
      .efficiency-dashboard-grid,
      .history-snapshot-grid,
      .compare-verdict-grid,
      .compare-shortcuts,
      .compare-factor-grid,
      .compare-team-grid,
      .compare-stat-grid,
      .matchup-team-grid,
      .projection-stat-grid,
      .result-pair-grid,
      .team-story-grid,
      .impact-stat-grid,
      .profile-bar-grid,
      .mini-team-stat-grid,
      .journey-tooltip-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
      }
      @media (min-width: 720px) {
        .scenario-grid,
        .archive-card-grid,
        .pulse-grid,
        .counts-grid,
        .history-level-grid,
        .historical-dna-grid,
        .story-card-grid,
        .impact-card-grid,
        .efficiency-dashboard-grid,
        .history-snapshot-grid,
        .compare-verdict-grid,
        .compare-shortcuts,
        .compare-factor-grid,
        .compare-stat-grid,
        .matchup-team-grid,
        .team-story-grid,
        .impact-stat-grid,
        .profile-bar-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .compare-team-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .result-pair-grid { grid-template-columns: 1fr 1fr; }
      }
      @media (min-width: 1024px) {
        .scenario-grid,
        .pulse-grid,
        .history-level-grid,
        .story-card-grid,
        .impact-card-grid,
        .compare-factor-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .counts-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      }

      .premium-team-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 20px;
      }
      @media (min-width: 960px) {
        .premium-team-grid { grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 28px; }
      }
      .premium-team-grid .panel.prose-panel,
      .premium-team-grid .panel.narrative-panel { grid-column: 1 / -1; }

      /* =======================================================
         Summary strip (home side rail)
         ======================================================= */
      .summary-strip,
      .summary-strip-rail {
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
      }
      .summary-card {
        display: grid;
        grid-template-columns: auto 1fr auto;
        grid-template-rows: auto auto;
        column-gap: 16px;
        padding: 18px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        color: var(--foreground);
        transition: box-shadow .18s ease, transform .18s ease;
        position: relative;
      }
      .summary-card:hover { box-shadow: 0 12px 24px rgba(0,0,0,0.06); }
      .summary-label {
        grid-column: 1 / 2;
        grid-row: 1 / 2;
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .summary-detail {
        grid-column: 2 / 3;
        grid-row: 1 / 2;
        font-size: 12px;
        color: var(--muted-foreground);
        text-align: right;
      }
      .summary-value {
        grid-column: 1 / 3;
        grid-row: 2 / 3;
        font-family: var(--font-display);
        font-size: 28px;
        line-height: 1;
        color: var(--foreground);
      }
      .summary-spark {
        grid-column: 3 / 4;
        grid-row: 1 / 3;
        align-self: center;
        color: var(--muted-foreground);
      }

      /* Count cards (subdivision footprint) */
      .count-card {
        display: flex;
        flex-direction: column;
        gap: 6px;
        padding: 20px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
      }
      .count-kicker {
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .count-card strong { font-family: var(--font-display); font-size: 32px; line-height: 1; }
      .count-card small { color: var(--muted-foreground); font-size: 12px; }

      /* =======================================================
         Team board / smart board
         ======================================================= */
      .team-board { padding: 24px; }
      .board-heading { align-items: flex-start; }
      .board-utility {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin: 16px 0 12px;
        padding: 16px;
        background: var(--secondary);
        border-radius: var(--radius-lg);
        border: 1px solid var(--border);
      }
      .board-controls {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
      }
      @media (min-width: 720px) {
        .board-controls { grid-template-columns: 1.4fr 1fr 1fr 1fr; }
      }
      .board-control {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .board-control > span {
        font: 500 11px/1 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .board-control input,
      .board-control select {
        appearance: none;
        background: var(--card);
        border: 1px solid var(--border-strong);
        border-radius: var(--radius-md);
        padding: 10px 12px;
        font: 500 14px/1.2 var(--font-sans);
        color: var(--foreground);
        outline: none;
        transition: border-color .15s;
        min-width: 0;
        width: 100%;
      }
      .board-control input:focus,
      .board-control select:focus { border-color: var(--foreground); }
      .board-toolbar {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
      }
      .jump-group {
        display: inline-flex;
        gap: 4px;
        padding: 3px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 999px;
      }
      .jump-chip {
        border: 0;
        background: transparent;
        color: var(--foreground);
        padding: 6px 14px;
        border-radius: 999px;
        font: 500 13px/1 var(--font-sans);
      }
      .jump-chip.is-active { background: var(--accent-surface); color: var(--accent-foreground); }
      .board-status {
        font-size: 13px;
        color: var(--muted-foreground);
        margin-left: auto;
        display: inline-flex;
        align-items: baseline;
        gap: 6px;
      }
      .board-status strong { color: var(--foreground); font-family: var(--font-display); font-size: 18px; }
      .clear-filters {
        border: 1px solid var(--border-strong);
        background: transparent;
        color: var(--foreground);
        padding: 8px 14px;
        border-radius: var(--radius-md);
        font: 500 13px/1 var(--font-sans);
      }
      .clear-filters:hover { background: var(--secondary); }
      .active-filter-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }
      .active-filter-row .filter-chip {
        display: inline-flex;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        background: var(--card);
        border: 1px solid var(--border-strong);
        font-size: 12px;
      }

      .board-topline {
        padding: 0 12px;
      }
      .board-column-head {
        display: grid;
        grid-template-columns: var(--board-columns);
        gap: 8px;
        padding: 12px 16px;
        border-bottom: 1px solid var(--border);
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .board-column-head span:nth-child(3) { text-align: left; }
      .board-column-head span { text-align: right; }
      .board-column-head span:first-child,
      .board-column-head span:nth-child(2),
      .board-column-head span:nth-child(3) { text-align: left; }

      .team-board-list {
        display: flex;
        flex-direction: column;
      }

      .board-row {
        border-bottom: 1px solid var(--border);
      }
      .board-row[open] { background: rgba(0,0,0,0.015); }
      .board-row > summary {
        display: grid;
        grid-template-columns: var(--board-columns);
        gap: 8px;
        padding: 14px 16px;
        align-items: center;
        cursor: pointer;
        list-style: none;
        transition: background .12s ease;
      }
      .board-row > summary::-webkit-details-marker { display: none; }
      .board-row > summary:hover { background: var(--secondary); }

      .board-cell {
        font-size: 14px;
        color: var(--foreground);
        text-align: right;
      }
      .board-cell.rank-cell-home {
        font-family: var(--font-display);
        font-size: 20px;
        color: var(--foreground);
        text-align: left;
      }
      .board-cell.board-delta { text-align: left; font-weight: 600; }
      .board-cell.board-delta.up { color: var(--success); }
      .board-cell.board-delta.down { color: var(--destructive); }
      .board-cell.board-delta.flat { color: var(--muted-foreground); }
      .board-cell.board-team-cell {
        display: flex;
        flex-direction: column;
        text-align: left;
        min-width: 0;
      }
      .board-team-name {
        font: 600 15px/1.2 var(--font-sans);
        color: var(--foreground);
      }
      .board-team-meta {
        font-size: 12px;
        color: var(--muted-foreground);
      }
      .board-cell.board-trend { display: flex; justify-content: flex-end; color: var(--muted-foreground); }

      .board-row-body {
        padding: 16px;
        background: var(--secondary);
        border-top: 1px solid var(--border);
      }
      .board-detail-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
      }
      @media (min-width: 840px) {
        .board-detail-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .detail-bestwins { grid-column: span 2; }
      }
      .board-detail-grid h3 {
        font-family: var(--font-display);
        font-size: 18px;
        letter-spacing: 0.01em;
        text-transform: uppercase;
        margin-bottom: 10px;
      }
      .detail-watch p { font-size: 14px; color: var(--muted-foreground); margin: 4px 0; }
      .detail-watch p strong { color: var(--foreground); font-weight: 600; }
      .result-slab { padding: 12px; background: var(--card); border-radius: var(--radius-md); border: 1px solid var(--border); }
      .result-slab-wide { grid-column: 1 / -1; }
      .result-kicker { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted-foreground); }
      .result-slab p { margin: 4px 0; font-size: 14px; color: var(--foreground); }

      .board-row-footer {
        padding: 12px 4px 0;
        border-top: 1px solid var(--border);
        margin-top: 14px;
      }

      @media (max-width: 820px) {
        .board-column-head { display: none; }
        .board-row > summary {
          grid-template-columns: 64px 60px 1fr;
          grid-template-rows: auto auto;
          row-gap: 6px;
        }
        .board-row > summary .rank-cell-home { grid-column: 1 / 2; grid-row: 1 / 2; }
        .board-row > summary .board-delta { grid-column: 2 / 3; grid-row: 1 / 2; }
        .board-row > summary .board-team-cell { grid-column: 3 / 4; grid-row: 1 / 2; }
        .board-row > summary .board-record { grid-column: 1 / 2; grid-row: 2 / 3; }
        .board-row > summary .board-power { grid-column: 2 / 3; grid-row: 2 / 3; text-align: left; }
        .board-row > summary .board-resume { grid-column: 3 / 4; grid-row: 2 / 3; text-align: left; }
        .board-row > summary .board-trend { display: none; }
      }

      /* Rankings page full board */
      .team-board + .team-board-list { /* noop */ }

      /* =======================================================
         Feature cards (home: scenarios, archives, etc)
         ======================================================= */
      .feature-card,
      .scenario-card,
      .archive-card,
      .conference-card,
      .pulse-card,
      .history-snapshot-card,
      .stat-card,
      .impact-card,
      .efficiency-card,
      .reminiscence-card,
      .peer-item,
      .compare-team-card,
      .compare-factor-card,
      .story-card,
      .team-mini-card {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 20px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        color: var(--foreground);
        transition: box-shadow .18s ease, transform .18s ease;
        text-decoration: none;
      }
      .feature-card:hover,
      .scenario-card:hover,
      .archive-card:hover,
      .conference-card:hover,
      .story-card:hover,
      .compare-team-card:hover,
      .team-mini-card:hover,
      .peer-item:hover {
        box-shadow: 0 14px 30px rgba(10,10,10,0.06);
      }

      .feature-rank,
      .panel-kicker,
      .reminiscence-sub {
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }

      .feature-card h3,
      .scenario-card h3,
      .archive-card h3,
      .story-card h3,
      .conference-card h3,
      .stat-card h3,
      .impact-card h3,
      .reminiscence-title,
      .compare-team-card h2,
      .compare-factor-top h3 {
        font-family: var(--font-display);
        font-size: 22px;
        line-height: 1.1;
        letter-spacing: 0.01em;
        text-transform: uppercase;
      }

      .feature-card p,
      .scenario-card p,
      .archive-card p,
      .story-card p,
      .conference-card p,
      .pulse-card p,
      .impact-card p,
      .stat-card p,
      .reminiscence-card p,
      .team-mini-card p {
        margin: 0;
        color: var(--muted-foreground);
        font-size: 14px;
        line-height: 1.55;
      }

      .story-card { border-left: 4px solid var(--border); }
      .story-card.is-positive { border-left-color: var(--success); }
      .story-card.is-negative { border-left-color: var(--destructive); }
      .story-card.is-neutral { border-left-color: var(--muted-foreground); }
      .story-tail {
        margin-top: 8px;
        font-size: 12px;
        color: var(--muted-foreground);
      }

      /* Conference card accents by level */
      .conference-card .conference-level,
      .conference-card .conference-note {
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .conference-stat-line {
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        color: var(--muted-foreground);
        padding-top: 8px;
        border-top: 1px solid var(--border);
      }
      .conference-stat-line strong { color: var(--foreground); font-weight: 600; }

      /* Level tags */
      .level-FBS { color: var(--team-blue); }
      .level-FCS { color: var(--team-green); }
      .level-DII { color: var(--team-orange); }
      .level-DIII { color: var(--team-purple); }

      /* Pulse cards */
      .pulse-card h3 { font-family: var(--font-display); font-size: 22px; letter-spacing: 0.01em; }
      .pulse-card strong { font-family: var(--font-display); font-size: 28px; line-height: 1; }

      /* =======================================================
         Impact cards / stats
         ======================================================= */
      .impact-card {
        gap: 12px;
      }
      .impact-card-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
      }
      .impact-card-top h3 { font-family: var(--font-display); font-size: 18px; }
      .impact-week {
        font: 600 11px/1 var(--font-sans);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--muted-foreground);
      }
      .impact-stat-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }
      .impact-stat {
        padding: 10px 12px;
        background: var(--secondary);
        border-radius: var(--radius-md);
      }
      .impact-stat-wide { grid-column: 1 / -1; }
      .impact-stat span {
        display: block;
        font-size: 11px;
        color: var(--muted-foreground);
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .impact-stat strong {
        display: block;
        margin-top: 4px;
        font: 600 16px/1.1 var(--font-sans);
      }
      .impact-meta { font-size: 12px; color: var(--muted-foreground); }
      .impact-up { color: var(--success); }
      .impact-down { color: var(--destructive); }

      /* =======================================================
         Efficiency bars
         ======================================================= */
      .efficiency-card { gap: 8px; }
      .efficiency-line { display: flex; align-items: baseline; justify-content: space-between; font-size: 13px; color: var(--muted-foreground); }
      .efficiency-line strong { color: var(--foreground); font-family: var(--font-display); font-size: 20px; }
      .efficiency-track {
        height: 8px;
        background: var(--muted);
        border-radius: 999px;
        overflow: hidden;
      }
      .efficiency-fill {
        height: 100%;
        background: var(--primary);
        border-radius: 999px;
      }
      .offense .efficiency-fill { background: var(--team-blue); }
      .defense .efficiency-fill { background: var(--team-red); }

      /* Profile bars (compare) */
      .profile-bars { display: flex; flex-direction: column; gap: 12px; }
      .profile-row { display: grid; grid-template-columns: 110px 1fr 60px; gap: 10px; align-items: center; font-size: 13px; }
      .profile-label { color: var(--muted-foreground); text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em; }
      .profile-self, .profile-comp {
        display: block;
        height: 8px;
        border-radius: 999px;
        background: var(--primary);
      }
      .profile-comp { background: var(--team-blue); }
      .profile-legend { display: flex; gap: 16px; font-size: 12px; color: var(--muted-foreground); }
      .profile-legend span::before {
        content: '';
        display: inline-block;
        width: 8px; height: 8px;
        background: currentColor;
        margin-right: 6px;
        border-radius: 50%;
      }

      /* Compare bar (compare factors) */
      .compare-factor-card { display: flex; flex-direction: column; gap: 10px; }
      .compare-factor-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 8px;
      }
      .compare-factor-bars {
        display: grid;
        grid-template-columns: 1fr;
        gap: 8px;
      }
      .compare-bar-row {
        display: grid;
        grid-template-columns: 100px 1fr 50px;
        gap: 10px;
        align-items: center;
        font-size: 13px;
      }
      .compare-bar-team { color: var(--muted-foreground); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
      .compare-bar-track { height: 8px; background: var(--muted); border-radius: 999px; overflow: hidden; }
      .compare-bar,
      .compare-bar-a,
      .compare-bar-b {
        display: block;
        height: 100%;
        background: var(--primary);
        border-radius: 999px;
      }
      .compare-bar-b { background: var(--team-blue); }
      .compare-bar-value { font-family: var(--font-display); font-size: 18px; text-align: right; }

      /* =======================================================
         Matchup tool / compact
         ======================================================= */
      .matchup-tool,
      .compact-matchup-tool {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .matchup-controls {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
      }
      @media (min-width: 720px) {
        .matchup-controls { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      }
      .matchup-controls label {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font: 500 11px/1 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .matchup-controls select,
      .matchup-controls input {
        appearance: none;
        padding: 10px 12px;
        background: var(--card);
        border: 1px solid var(--border-strong);
        border-radius: var(--radius-md);
        font: 500 14px/1.1 var(--font-sans);
        color: var(--foreground);
      }
      .matchup-team-grid {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        gap: 14px;
        align-items: center;
      }
      @media (max-width: 680px) {
        .matchup-team-grid { grid-template-columns: 1fr; }
      }
      .compare-team-card {
        background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
        color: #fff;
        border: 0;
        padding: 22px;
      }
      .compare-team-card h2, .compare-team-card h3 { color: #fff; }
      .compare-team-card .stat-card,
      .compare-team-card .compare-stat-grid { color: #fff; }
      .compare-team-card .stat-card { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.12); color: #fff; }
      .compare-team-card .stat-card span { color: rgba(255,255,255,0.7); }

      .projection-shell {
        padding: 20px;
        background: var(--secondary);
        border-radius: var(--radius-lg);
        border: 1px solid var(--border);
      }
      .projection-band { display: flex; flex-wrap: wrap; gap: 12px; align-items: baseline; }
      .projection-copy { margin: 6px 0 0; color: var(--muted-foreground); font-size: 14px; }

      /* =======================================================
         Historical DNA / reminiscence
         ======================================================= */
      .historical-dna { margin-top: 14px; }
      .historical-dna-summary { color: var(--muted-foreground); font-size: 13px; margin-bottom: 10px; }
      .reminiscence-card {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .reminiscence-title { font-size: 18px; }
      .reminiscence-sub { color: var(--muted-foreground); }

      /* =======================================================
         History mini panel / Journey chart
         ======================================================= */
      .history-chart-wrap { padding-top: 8px; }
      .history-svg,
      .journey-svg,
      .identity-svg,
      .spark-svg { max-width: 100%; height: auto; display: block; }

      .journey-frame {
        position: relative;
        padding: 8px 0 6px;
      }
      .journey-topline { margin-bottom: 8px; color: var(--muted-foreground); font-size: 13px; }
      .journey-axis-strip { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted-foreground); }
      .journey-axis-label { padding: 0 2px; }
      .journey-legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 8px; font-size: 12px; color: var(--muted-foreground); }
      .journey-legend-item { display: inline-flex; align-items: center; gap: 6px; }
      .journey-swatch {
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        background: currentColor;
      }
      .journey-marker-layer { pointer-events: none; }
      .journey-tooltip {
        position: absolute;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 10px 12px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        font-size: 12px;
        pointer-events: none;
      }
      .journey-tooltip-kicker { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted-foreground); }
      .journey-tooltip-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px 14px;
        margin-top: 6px;
      }
      .journey-tooltip-stat-wide { grid-column: 1 / -1; }
      .journey-tooltip-meta { color: var(--muted-foreground); font-size: 11px; }

      .journey-highlight-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
      .journey-highlight-card {
        flex: 1 1 180px;
        min-width: 180px;
        padding: 12px;
        background: var(--secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
      }
      .journey-highlight-kicker {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted-foreground);
      }
      .journey-highlight-meta { font-size: 12px; color: var(--muted-foreground); margin-top: 4px; }

      /* Power vs Resume plot */
      .power-resume-module {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .power-resume-topline {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .power-resume-topline .section-note { margin: 0; font-size: 13px; }
      .power-resume-search {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .power-resume-search span {
        font: 500 11px/1 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .power-resume-search input {
        appearance: none;
        padding: 10px 12px;
        background: var(--card);
        border: 1px solid var(--border-strong);
        border-radius: var(--radius-md);
        font: 500 14px/1.2 var(--font-sans);
        color: var(--foreground);
        width: 100%;
      }
      .power-resume-levels {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        padding: 3px;
        background: var(--secondary);
        border: 1px solid var(--border);
        border-radius: 999px;
        align-self: flex-start;
      }
      .power-resume-level {
        border: 0;
        background: transparent;
        color: var(--foreground);
        padding: 6px 12px;
        border-radius: 999px;
        font: 500 12px/1 var(--font-sans);
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }
      .power-resume-level.is-active { background: var(--accent-surface); color: var(--accent-foreground); }
      .power-resume-level span {
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 999px;
        background: rgba(0,0,0,0.06);
        color: inherit;
      }
      .power-resume-level.is-active span { background: rgba(255,255,255,0.2); }

      .power-resume-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 12px;
        color: var(--muted-foreground);
      }
      .power-resume-legend-item { display: inline-flex; align-items: center; gap: 6px; }
      .power-resume-legend-point { width: 10px; height: 10px; border-radius: 50%; background: currentColor; }
      .power-resume-legend-point.level-FBS { background: var(--team-blue); }
      .power-resume-legend-point.level-FCS { background: var(--team-green); }
      .power-resume-legend-point.level-DII { background: var(--team-orange); }
      .power-resume-legend-point.level-DIII { background: var(--team-purple); }

      .power-resume-layout {
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
      }
      @media (min-width: 960px) {
        .power-resume-layout { grid-template-columns: minmax(0, 1fr) 240px; }
      }
      .power-resume-stage {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .power-resume-plot-shell {
        position: relative;
        background: var(--secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 16px 18px 8px 38px;
      }
      .power-resume-plot {
        position: relative;
        width: 100%;
        aspect-ratio: 1.4 / 1;
        min-height: 260px;
      }
      .power-resume-field {
        position: absolute;
        inset: 0;
      }
      .power-resume-axis-y {
        position: absolute;
        top: 50%;
        left: 10px;
        transform: translateY(-50%) rotate(-90deg);
        transform-origin: left center;
        font-size: 10px;
        color: var(--muted-foreground);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        white-space: nowrap;
      }
      .power-resume-quadrant {
        position: absolute;
        width: 50%; height: 50%;
        opacity: 0.55;
        pointer-events: none;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted-foreground);
        padding: 8px 10px;
        display: flex;
      }
      .power-resume-quadrant-nw { top: 0; left: 0; align-items: flex-start; justify-content: flex-start; }
      .power-resume-quadrant-ne { top: 0; right: 0; align-items: flex-start; justify-content: flex-end; text-align: right; }
      .power-resume-quadrant-sw { bottom: 0; left: 0; align-items: flex-end; justify-content: flex-start; }
      .power-resume-quadrant-se { bottom: 0; right: 0; align-items: flex-end; justify-content: flex-end; text-align: right; }
      .power-resume-midline { position: absolute; background: var(--border-strong); z-index: 1; }
      .power-resume-midline-x { left: 0; right: 0; top: 50%; height: 1px; }
      .power-resume-midline-y { top: 0; bottom: 0; left: 50%; width: 1px; }
      .power-resume-points { position: absolute; inset: 0; z-index: 2; }
      .power-resume-tag {
        position: absolute;
        z-index: 3;
        padding: 4px 8px;
        background: var(--card);
        border: 1px solid var(--border-strong);
        border-radius: var(--radius-sm);
        font-size: 11px;
        pointer-events: none;
        white-space: nowrap;
      }
      .power-resume-axis-footer {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        font-size: 11px;
        color: var(--muted-foreground);
        padding: 4px 0 0;
      }
      .power-resume-axis-footer strong { color: var(--foreground); text-transform: uppercase; letter-spacing: 0.08em; font-size: 10px; font-weight: 600; }
      .power-resume-scale {
        display: flex;
        justify-content: space-between;
        font-size: 10px;
        color: var(--muted-foreground);
        padding-top: 2px;
      }

      .power-resume-focus {
        padding: 16px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        min-height: 180px;
      }
      .power-resume-focus .feature-rank { font-size: 10px; }
      .power-resume-focus h3 {
        font-family: var(--font-display);
        font-size: 22px;
        letter-spacing: 0.01em;
        margin: 6px 0 8px;
      }
      .power-resume-focus-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0; }
      .power-resume-focus-sub { font-size: 12px; color: var(--muted-foreground); }
      .power-resume-tag { font-size: 11px; color: var(--muted-foreground); }
      .power-resume-empty { padding: 16px; color: var(--muted-foreground); font-size: 13px; }
      .power-resume-link { color: var(--foreground); font-weight: 600; }
      .power-resume-footer {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 4px;
      }

      /* Strength ladder */
      .ladder-wrap { display: flex; flex-direction: column; gap: 10px; }
      .ladder-band {
        display: grid;
        grid-template-columns: 56px 1fr 72px;
        grid-template-areas: "label bar value";
        align-items: center;
        gap: 12px;
        padding: 6px 0;
      }
      .ladder-label {
        grid-area: label;
        font: 600 12px/1 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--foreground);
      }
      .ladder-fill {
        grid-area: bar;
        height: 10px;
        min-width: 4px;
        border-radius: 999px;
        background: var(--primary);
      }
      .ladder-value {
        grid-area: value;
        text-align: right;
        color: var(--muted-foreground);
        font-family: var(--font-display);
        font-size: 18px;
        letter-spacing: 0.02em;
      }

      /* =======================================================
         Tables (rankings, history, schedules)
         ======================================================= */
      .table-wrap,
      .compact-table-wrap,
      .game-impact-table-wrap { width: 100%; overflow-x: auto; }

      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }
      th {
        text-align: left;
        padding: 10px 12px;
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted-foreground);
        border-bottom: 1px solid var(--border);
        background: var(--secondary);
      }
      td {
        padding: 12px;
        border-bottom: 1px solid var(--border);
        vertical-align: middle;
      }
      tbody tr:hover td { background: var(--secondary); }

      .heisman-row td {
        font-weight: 500;
      }

      .game-impact-table th,
      .game-impact-table td { padding: 10px; font-size: 13px; }
      .game-impact-table .game-prefix { color: var(--muted-foreground); }

      /* =======================================================
         Team story grid / mini cards
         ======================================================= */
      .team-mini-card { padding: 16px; }
      .team-mini-meta, .team-mini-note {
        font-size: 12px;
        color: var(--muted-foreground);
      }
      .team-link { color: var(--foreground); font-weight: 600; border-bottom: 1px solid currentColor; }

      /* Peer list */
      .peer-list { display: flex; flex-direction: column; gap: 10px; }
      .peer-item { padding: 14px 16px; }
      .peer-item-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
      .peer-kicker { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted-foreground); }
      .peer-gap-line { font-size: 13px; color: var(--muted-foreground); }
      .peer-context-note { font-size: 13px; color: var(--muted-foreground); margin-top: 8px; }
      .compare-shortcut {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        background: var(--secondary);
        border-radius: 999px;
        font-size: 12px;
        color: var(--foreground);
      }
      .compare-shortcut:hover { background: var(--muted); }

      /* =======================================================
         Section & card layout helpers
         ======================================================= */
      .feature-card,
      .stat-card,
      .scenario-card,
      .archive-card,
      .conference-card,
      .history-snapshot-card,
      .compare-team-card,
      .compare-factor-card,
      .story-card,
      .pulse-card,
      .impact-card,
      .efficiency-card,
      .reminiscence-card,
      .count-card,
      .peer-item,
      .team-mini-card,
      .summary-card {
        min-width: 0;
      }

      /* =======================================================
         Player / Heisman / players index specifics (light)
         ======================================================= */
      .heisman-row .board-team-name { font-weight: 600; }
      .compact-head h2 { font-size: 24px; }

      /* =======================================================
         Footer / small
         ======================================================= */
      .page-footer,
      .site-footer {
        margin-top: 64px;
        padding: 32px 0;
        border-top: 1px solid var(--border);
        color: var(--muted-foreground);
        font-size: 13px;
      }

      /* =======================================================
         Misc
         ======================================================= */
      .highlight-panel h2 { font-size: 20px; }

      /* SVG path color hook for sparklines on summary */
      .summary-spark .spark-svg polyline { stroke: var(--muted-foreground); }
      .summary-card:hover .spark-svg polyline { stroke: var(--foreground); }

      /* Generic first-of-type color for navigation shortcut (matchups stays ghost) */
      .nav-actions .nav-action:first-of-type:last-of-type {
        background: var(--primary);
        color: var(--primary-foreground);
      }

      /* Compact rails */
      .conference-card-grid-compact { gap: 12px; }
      .conference-card-grid-compact .conference-card { padding: 14px 16px; }
      .conference-card-grid-compact .conference-card h3 { font-size: 18px; }

      /* Narrow shell for prose-only pages */
      .narrative-panel h2 { font-size: clamp(24px, 3vw, 32px); }

      /* =======================================================
         Responsive fallbacks
         ======================================================= */
      @media (max-width: 520px) {
        .team-hero-top { flex-direction: column; }
        .team-rank-chip { align-self: flex-start; }
        .section-head { flex-direction: column; align-items: flex-start; }
        .meta-pill { font-size: 12px; }
        .summary-card { grid-template-columns: 1fr auto; }
        .summary-value { grid-column: 1 / 2; }
        .summary-spark { grid-column: 2 / 3; grid-row: 1 / 3; }
      }

      /* Print-ish reset */
      @media print {
        .topbar, .nav-toggle, .button, .button-primary, .button-secondary, .nav-action { display: none; }
      }

      /* =======================================================
         Fan Intelligence — Team Mood Card & editorial modules
         ======================================================= */

      .mood-card-section { margin-top: 8px; }

      .mood-card {
        position: relative;
        overflow: hidden;
        padding: 28px;
        border-radius: var(--radius-xl);
        background:
          radial-gradient(120% 140% at 0% 0%, rgba(220, 38, 38, 0.10) 0%, rgba(220, 38, 38, 0.00) 55%),
          radial-gradient(120% 140% at 100% 0%, rgba(37, 99, 235, 0.10) 0%, rgba(37, 99, 235, 0.00) 55%),
          linear-gradient(180deg, #0A0A0A 0%, #1a1a1a 100%);
        color: #fff;
        border: 1px solid rgba(255,255,255,0.08);
      }
      @media (min-width: 768px) { .mood-card { padding: 36px; } }
      .mood-card::after {
        content: '';
        position: absolute;
        inset: 0;
        background-image: repeating-linear-gradient(
          135deg,
          rgba(255,255,255,0.015) 0 2px,
          transparent 2px 6px
        );
        pointer-events: none;
      }
      .mood-card > * { position: relative; z-index: 1; }

      .mood-card-head {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 22px;
      }
      .mood-card-title { max-width: 620px; }
      .mood-eyebrow {
        background: rgba(255,255,255,0.10);
        color: rgba(255,255,255,0.85);
      }
      .mood-card h2 {
        font-family: var(--font-display);
        font-size: clamp(26px, 3.4vw, 38px);
        line-height: 1.05;
        color: #fff;
        text-transform: uppercase;
        letter-spacing: 0.015em;
        margin-top: 6px;
      }
      .mood-card-subtitle {
        margin: 10px 0 0;
        color: rgba(255,255,255,0.72);
        font-size: 14px;
        max-width: 56ch;
      }
      .mood-card-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: flex-start;
        justify-content: flex-end;
      }
      .mood-meta-chip {
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #fff;
        background: rgba(255,255,255,0.10);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 999px;
      }
      .mood-meta-chip-muted {
        background: transparent;
        color: rgba(255,255,255,0.65);
        border-color: rgba(255,255,255,0.12);
      }
      .mood-archetype-chip {
        display: inline-flex;
        align-items: center;
        padding: 6px 14px;
        font-family: var(--font-display);
        font-size: 14px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        background: var(--gradient-accent);
        color: #fff;
        border-radius: 999px;
        box-shadow: 0 1px 0 rgba(255,255,255,0.12) inset;
      }

      .mood-waiting-banner {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0 0 18px;
        padding: 12px 16px;
        background: rgba(234, 88, 12, 0.10);
        border: 1px dashed rgba(234, 88, 12, 0.45);
        border-radius: var(--radius-md);
        color: rgba(255,255,255,0.82);
        font-size: 13.5px;
        line-height: 1.5;
      }
      .mood-waiting-dot {
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #EA580C;
        box-shadow: 0 0 0 4px rgba(234, 88, 12, 0.20);
        flex: 0 0 auto;
      }

      .mood-hero {
        display: grid;
        grid-template-columns: 1fr;
        gap: 18px;
        padding: 20px;
        margin-bottom: 22px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: var(--radius-lg);
      }
      @media (min-width: 720px) {
        .mood-hero { grid-template-columns: minmax(180px, 260px) 1fr; gap: 28px; align-items: center; }
      }
      .mood-hero-score { display: flex; flex-direction: column; gap: 4px; }
      .mood-hero-score-label {
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.65);
      }
      .mood-hero-score-value {
        font-family: var(--font-display);
        font-size: clamp(32px, 5vw, 48px);
        line-height: 1;
        text-transform: uppercase;
        color: #fff;
      }
      .mood-hero-score-number {
        font: 600 15px/1 var(--font-sans);
        color: rgba(255,255,255,0.7);
        letter-spacing: 0.02em;
      }
      .mood-hero-meter { display: flex; flex-direction: column; gap: 10px; }
      .mood-meter-track {
        position: relative;
        height: 10px;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(220, 38, 38, 0.45) 0%, rgba(255,255,255,0.10) 50%, rgba(22, 163, 74, 0.55) 100%);
        overflow: visible;
      }
      .mood-meter-fill {
        position: absolute;
        top: -4px;
        width: 18px;
        height: 18px;
        background: #fff;
        border-radius: 50%;
        transform: translateX(-9px);
        box-shadow: 0 2px 12px rgba(255,255,255,0.35);
      }
      .mood-meter-markers {
        display: flex;
        justify-content: space-between;
        font: 500 10px/1 var(--font-sans);
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.55);
        padding: 0 2px;
      }
      .mood-hero-narrative {
        margin: 0;
        color: rgba(255,255,255,0.84);
        font-size: 15px;
        line-height: 1.55;
      }

      .mood-axis-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
        margin-bottom: 22px;
      }
      @media (min-width: 640px) { .mood-axis-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } }
      @media (min-width: 960px) { .mood-axis-grid { grid-template-columns: repeat(5, minmax(0,1fr)); } }
      .mood-axis {
        padding: 16px;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: var(--radius-md);
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .mood-axis header { display: flex; flex-direction: column; gap: 4px; }
      .mood-axis header span {
        font: 600 11px/1 var(--font-sans);
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.55);
      }
      .mood-axis header strong {
        font-family: var(--font-display);
        font-size: 22px;
        line-height: 1.05;
        color: #fff;
        text-transform: uppercase;
        letter-spacing: 0.015em;
      }
      .mood-axis p {
        margin: 0;
        color: rgba(255,255,255,0.72);
        font-size: 13.5px;
        line-height: 1.5;
      }
      .mood-axis-detail {
        font: 600 11px/1 var(--font-sans);
        color: rgba(255,255,255,0.55);
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .mood-cohesion-stack {
        display: flex;
        width: 100%;
        height: 8px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(255,255,255,0.08);
        margin-top: 4px;
      }
      .mood-cohesion-seg { display: block; height: 100%; }
      .mood-cohesion-pos { background: #16A34A; }
      .mood-cohesion-neu { background: rgba(255,255,255,0.25); }
      .mood-cohesion-neg { background: #DC2626; }

      .mood-storylines {
        padding: 20px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: var(--radius-lg);
        margin-bottom: 18px;
      }
      .mood-storylines h3 {
        margin: 0 0 12px;
        font-family: var(--font-display);
        font-size: 22px;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        color: #fff;
      }
      .mood-storylines-empty p {
        margin: 0;
        color: rgba(255,255,255,0.65);
        font-size: 14px;
      }
      .mood-storyline-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
      .mood-storyline-item { display: flex; gap: 12px; padding: 10px 0; border-top: 1px dashed rgba(255,255,255,0.08); }
      .mood-storyline-item:first-child { border-top: none; padding-top: 0; }
      .mood-storyline-rank {
        flex: 0 0 auto;
        display: inline-flex; align-items: center; justify-content: center;
        width: 34px; height: 34px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: var(--radius-sm);
        font-family: var(--font-display);
        font-size: 14px;
        color: #fff;
      }
      .mood-storyline-body { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
      .mood-storyline-body strong { color: #fff; font-size: 15px; }
      .mood-storyline-body p { margin: 0; color: rgba(255,255,255,0.65); font-size: 13px; line-height: 1.5; }

      .mood-card-footer {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        justify-content: space-between;
        padding-top: 14px;
        border-top: 1px solid rgba(255,255,255,0.08);
        font: 500 11px/1.5 var(--font-sans);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.50);
      }

      .offseason-radar .section-head .eyebrow {
        background: rgba(249, 115, 22, 0.10);
        color: #C2410C;
        border: 1px solid rgba(249, 115, 22, 0.22);
      }
      .offseason-now-card {
        display: grid;
        grid-template-columns: 1fr;
        gap: 18px;
        padding: 22px;
        margin-bottom: 18px;
        border-radius: var(--radius-xl);
        border: 1px solid rgba(194, 65, 12, 0.18);
        background:
          radial-gradient(circle at top right, rgba(59, 130, 246, 0.10), transparent 38%),
          linear-gradient(135deg, rgba(249, 115, 22, 0.08), rgba(250, 204, 21, 0.10));
      }
      @media (min-width: 900px) {
        .offseason-now-card { grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr); align-items: start; }
      }
      .offseason-now-kicker,
      .offseason-card-month {
        display: inline-flex;
        align-items: center;
        font: 700 11px/1 var(--font-sans);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #C2410C;
      }
      .offseason-now-card h3,
      .offseason-card h3 {
        margin: 8px 0 0;
        font-family: var(--font-display);
        font-size: clamp(22px, 3vw, 30px);
        line-height: 1.05;
        text-transform: uppercase;
        letter-spacing: 0.02em;
      }
      .offseason-now-card p,
      .offseason-card p {
        margin: 10px 0 0;
        color: var(--muted-foreground);
        font-size: 14px;
        line-height: 1.6;
      }
      .offseason-now-note {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 16px 18px;
        border-radius: var(--radius-lg);
        border: 1px solid rgba(15, 23, 42, 0.10);
        background: rgba(255,255,255,0.58);
      }
      .offseason-now-note strong {
        font: 700 11px/1 var(--font-sans);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #0F172A;
      }
      .offseason-now-note span {
        color: var(--foreground);
        font-size: 13px;
        line-height: 1.55;
      }
      .offseason-grid {
        grid-template-columns: 1fr;
        gap: 14px;
      }
      @media (min-width: 720px) { .offseason-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } }
      @media (min-width: 1080px) { .offseason-grid { grid-template-columns: repeat(3, minmax(0,1fr)); } }
      .offseason-card {
        position: relative;
        overflow: hidden;
        padding: 20px;
        border-radius: var(--radius-xl);
        border: 1px solid var(--border);
        background: var(--card);
      }
      .offseason-card::after {
        content: '';
        position: absolute;
        inset: auto -40px -40px auto;
        width: 120px;
        height: 120px;
        background: radial-gradient(circle, rgba(59,130,246,0.10), transparent 68%);
        pointer-events: none;
      }
      .offseason-card-current {
        border-color: rgba(194, 65, 12, 0.26);
        box-shadow: 0 12px 34px rgba(194, 65, 12, 0.10);
        background:
          linear-gradient(180deg, rgba(249, 115, 22, 0.04), rgba(255,255,255,0.95)),
          var(--card);
      }
      .offseason-card-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }
      .offseason-card-status {
        display: inline-flex;
        align-items: center;
        padding: 5px 10px;
        border-radius: 999px;
        background: #C2410C;
        color: #fff;
        font: 700 10px/1 var(--font-sans);
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }
      .offseason-module-list {
        list-style: none;
        margin: 14px 0 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .offseason-module-list li {
        position: relative;
        padding-left: 14px;
        color: var(--foreground);
        font-size: 13.5px;
        line-height: 1.45;
      }
      .offseason-module-list li::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0.55em;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: linear-gradient(135deg, #C2410C, #2563EB);
        transform: translateY(-50%);
      }

      /* Home-page fan intelligence grid */
      .fan-intel-home { margin-top: 4px; }
      .fan-intel-home .section-head .eyebrow {
        background: rgba(220, 38, 38, 0.10);
        color: #DC2626;
        border: 1px solid rgba(220, 38, 38, 0.18);
      }
      .intel-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 14px;
      }
      @media (min-width: 720px) { .intel-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } }
      @media (min-width: 1080px) { .intel-grid { grid-template-columns: repeat(3, minmax(0,1fr)); } }
      .intel-card {
        padding: 20px;
        border-radius: var(--radius-xl);
        border: 1px solid var(--border);
        background: var(--card);
        display: flex;
        flex-direction: column;
        gap: 14px;
        transition: box-shadow .15s ease, transform .15s ease;
      }
      .intel-card:hover { box-shadow: 0 8px 30px rgba(10,10,10,0.06); }
      .intel-card-head h3 {
        font-family: var(--font-display);
        font-size: 22px;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        color: var(--foreground);
      }
      .intel-card-head .section-note { margin-top: 4px; font-size: 13px; }
      .intel-card-shift { border-top: 3px solid #DC2626; }
      .intel-card-respect { border-top: 3px solid #2563EB; }
      .intel-card-doubt { border-top: 3px solid #EA580C; }
      .intel-card-rival { border-top: 3px solid #9333EA; }
      .intel-card-main { border-top: 3px solid #16A34A; }
      .intel-card-panic { border-top: 3px solid #0A0A0A; }
      .intel-card-civil { border-top: 3px solid #0F766E; }

      .intel-card-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
      .intel-card-row + .intel-card-row { border-top: 1px solid var(--border); }
      .intel-row-inner {
        display: grid;
        grid-template-columns: 28px 1fr;
        gap: 12px;
        padding: 12px 2px;
        color: var(--foreground);
      }
      .intel-row-inner:hover { background: var(--secondary); border-radius: var(--radius-sm); }
      .intel-row-rank {
        font-family: var(--font-display);
        font-size: 16px;
        line-height: 1;
        color: var(--muted-foreground);
        align-self: center;
        text-align: right;
      }
      .intel-row-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
      .intel-row-body strong {
        font: 600 15px/1.2 var(--font-sans);
        color: var(--foreground);
      }
      .intel-row-level {
        font: 600 10px/1 var(--font-sans);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .intel-row-headline {
        font-family: var(--font-display);
        font-size: 16px;
        color: #DC2626;
        letter-spacing: 0.01em;
      }
      .intel-card-respect .intel-row-headline { color: #2563EB; }
      .intel-card-rival .intel-row-headline { color: #9333EA; }
      .intel-card-main .intel-row-headline { color: #16A34A; }
      .intel-card-doubt .intel-row-headline { color: #EA580C; }
      .intel-card-panic .intel-row-headline { color: #0A0A0A; }
      .intel-card-civil .intel-row-headline { color: #0F766E; }
      .intel-row-sub {
        color: var(--muted-foreground);
        font-size: 12.5px;
        line-height: 1.45;
      }
      .intel-empty {
        margin: 0;
        padding: 18px;
        color: var(--muted-foreground);
        font-size: 13.5px;
        background: var(--secondary);
        border-radius: var(--radius-md);
        border: 1px dashed var(--border-strong);
      }

      .fan-intel-home-empty .section-head .eyebrow {
        background: rgba(234, 88, 12, 0.10);
        color: #EA580C;
        border: 1px solid rgba(234, 88, 12, 0.30);
      }
      .intel-empty-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
      }
      @media (min-width: 720px) { .intel-empty-grid { grid-template-columns: repeat(2, 1fr); } }
      @media (min-width: 1080px) { .intel-empty-grid { grid-template-columns: repeat(4, 1fr); } }
      .intel-empty-card {
        padding: 18px;
        border-radius: var(--radius-lg);
        border: 1px dashed var(--border-strong);
        background: var(--card);
      }
      .intel-empty-card h3 {
        font-family: var(--font-display);
        font-size: 18px;
        letter-spacing: 0.02em;
        text-transform: uppercase;
      }
      .intel-empty-card p {
        margin: 6px 0 0;
        color: var(--muted-foreground);
        font-size: 13px;
      }

      .argument-theater .section-head .eyebrow {
        background: rgba(37, 99, 235, 0.10);
        color: #2563EB;
        border: 1px solid rgba(37, 99, 235, 0.20);
      }
      .argument-grid { grid-template-columns: 1fr; }
      @media (min-width: 720px) { .argument-grid { grid-template-columns: repeat(3, minmax(0,1fr)); } }
    """
