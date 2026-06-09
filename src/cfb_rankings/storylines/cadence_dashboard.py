"""WS-12: editorial cadence dashboard — surfaces "what's overdue".

The editorial rhythm (Wire, Daily, Mailbag, storyline chapters, Editions) is the
product's moat; cadence is the discipline. This module reads the last-published
timestamp for each surface, compares it against a per-surface staleness
threshold, and flags anything overdue. It is the spec-12 running-gate item
("cadence dashboard surfaces what's overdue — chapters >14 days stale, Wires
missed, Mailbag overdue").

Like the storyline candidate digest, this is an editor-facing ops artifact
(Markdown + JSON sidecar in ``output/``), not a published public page. It reads
only live timestamps; it never publishes or mutates anything.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..db import Database

# Days a surface may go between publications before it's flagged overdue.
# Offseason-tuned (2026-05): Wire is M/W/F, Mailbag weekly, Daily roughly
# weekday, storyline chapters bi-weekly minimum (the spec-explicit >14-day
# staleness rule), Editions monthly-ish. In-season cadence is tighter, but a
# fixed threshold that never false-flags in the slower offseason is the safer
# default — tighten per phase later if the dashboard proves too lax.
SURFACE_THRESHOLDS_DAYS: dict[str, int] = {
    "wire": 3,
    "daily": 4,
    "mailbag": 8,
    "storyline_chapters": 14,
    "editions": 35,
}

_SURFACE_LABELS: dict[str, str] = {
    "wire": "The Wire",
    "daily": "The Daily",
    "mailbag": "Mailbag",
    "storyline_chapters": "Storyline chapters",
    "editions": "Editions",
}

# One SQL per surface returning a single column ``v`` = newest publish timestamp.
# Wrapped in try/except at call time so a DB missing a table (e.g. a minimal
# test fixture) degrades to "never published" rather than raising.
_SURFACE_QUERIES: dict[str, str] = {
    "wire": "select max(occurred_at) as v from wire_entries",
    "daily": "select max(generated_at_utc) as v from daily_editions",
    "mailbag": "select max(generated_at_utc) as v from mailbag_editions",
    "storyline_chapters": (
        "select max(last_chapter_at) as v from storyline_threads "
        "where status = 'active'"
    ),
    "editions": "select max(published_at_utc) as v from editions",
}

_STATUS_OK = "ok"
_STATUS_OVERDUE = "overdue"
_STATUS_NEVER = "never"


def _parse_ts(raw: Any) -> datetime | None:
    """Best-effort parse of the heterogeneous timestamp strings in the DB.

    Handles ``YYYY-MM-DD HH:MM:SS`` / ``...T...`` / trailing ``Z`` / fractional
    seconds / date-only. Returns a UTC-aware datetime or None.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.replace("T", " ")
    if s.endswith("Z"):
        s = s[:-1]
    for candidate in (s, s[:19], s[:16], s[:10]):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(candidate, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _max_ts(db: Database, sql: str) -> datetime | None:
    try:
        row = db.query_one(sql, {})
    except Exception:
        return None
    if not row:
        return None
    return _parse_ts(row.get("v"))


def _age_days(then: datetime | None, now: datetime) -> float | None:
    if then is None:
        return None
    return round((now - then).total_seconds() / 86400.0, 1)


def _surface_states(db: Database, now: datetime) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for key, sql in _SURFACE_QUERIES.items():
        last = _max_ts(db, sql)
        threshold = SURFACE_THRESHOLDS_DAYS[key]
        age = _age_days(last, now)
        if last is None:
            status = _STATUS_NEVER
        elif age is not None and age > threshold:
            status = _STATUS_OVERDUE
        else:
            status = _STATUS_OK
        states.append(
            {
                "surface": key,
                "label": _SURFACE_LABELS[key],
                "last_published_utc": last.strftime("%Y-%m-%d %H:%M UTC") if last else None,
                "age_days": age,
                "threshold_days": threshold,
                "status": status,
            }
        )
    return states


def _stale_threads(db: Database, now: datetime) -> list[dict[str, Any]]:
    """Per-active-thread chapter staleness (the documented cadence slip)."""
    try:
        rows = db.query_all(
            "select thread_slug, title, chapter_count, last_chapter_at "
            "from storyline_threads where status = 'active' "
            "order by last_chapter_at asc",
            {},
        )
    except Exception:
        return []
    threshold = SURFACE_THRESHOLDS_DAYS["storyline_chapters"]
    out: list[dict[str, Any]] = []
    for r in rows:
        last = _parse_ts(r.get("last_chapter_at"))
        age = _age_days(last, now)
        out.append(
            {
                "thread_slug": r.get("thread_slug"),
                "title": r.get("title"),
                "chapter_count": r.get("chapter_count"),
                "last_chapter_utc": last.strftime("%Y-%m-%d") if last else None,
                "age_days": age,
                "stale": bool(age is not None and age > threshold) or last is None,
            }
        )
    return out


def compute_cadence(db: Database, *, now: datetime | None = None) -> dict[str, Any]:
    """Return the cadence summary dict without writing anything."""
    now = now or datetime.now(timezone.utc)
    surfaces = _surface_states(db, now)
    threads = _stale_threads(db, now)
    overdue = [s for s in surfaces if s["status"] in (_STATUS_OVERDUE, _STATUS_NEVER)]
    return {
        "generated_utc": now.strftime("%Y-%m-%d %H:%M UTC"),
        "surfaces": surfaces,
        "stale_threads": threads,
        "overdue_count": len(overdue),
        "stale_thread_count": sum(1 for t in threads if t["stale"]),
    }


def _age_str(age: float | None) -> str:
    if age is None:
        return "—"
    if age < 1:
        return "today"
    return f"{age:.0f}d ago"


def render_cadence_dashboard(
    db: Database,
    output_path: str | Path = "output/editorial-cadence.md",
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Write the editor-facing cadence dashboard (Markdown + JSON sidecar)."""
    summary = compute_cadence(db, now=now)

    icon = {_STATUS_OK: "✅", _STATUS_OVERDUE: "🔴", _STATUS_NEVER: "⚪"}
    lines: list[str] = [
        "# Editorial cadence dashboard",
        "",
        f"_Generated {summary['generated_utc']}_",
        "",
        "Last-published timestamp per editorial surface vs its staleness "
        "threshold. 🔴 = overdue, ⚪ = never published, ✅ = fresh. Thresholds "
        "are offseason-tuned; see `SURFACE_THRESHOLDS_DAYS`.",
        "",
        f"**{summary['overdue_count']} surface(s) overdue · "
        f"{summary['stale_thread_count']} stale storyline thread(s)**",
        "",
        "| | Surface | Last published | Age | Threshold | Status |",
        "|--|---------|----------------|----:|----------:|--------|",
    ]
    for s in summary["surfaces"]:
        lines.append(
            f"| {icon.get(s['status'], '')} | {s['label']} | "
            f"{s['last_published_utc'] or '_never_'} | {_age_str(s['age_days'])} | "
            f"{s['threshold_days']}d | {s['status']} |"
        )
    lines.append("")

    lines.append("## Active storyline threads")
    lines.append("")
    if not summary["stale_threads"]:
        lines.append("_No active threads._")
    else:
        lines.append("| | Thread | Chapters | Last chapter | Age |")
        lines.append("|--|--------|---------:|--------------|----:|")
        for t in summary["stale_threads"]:
            mark = "🔴" if t["stale"] else "✅"
            lines.append(
                f"| {mark} | {t['title']} | {t['chapter_count']} | "
                f"{t['last_chapter_utc'] or '_never_'} | {_age_str(t['age_days'])} |"
            )
    lines.append("")

    md_path = Path(output_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")

    json_path = md_path.with_suffix(".json")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "md_path": str(md_path),
        "json_path": str(json_path),
        "overdue_count": summary["overdue_count"],
        "stale_thread_count": summary["stale_thread_count"],
        "generated_utc": summary["generated_utc"],
    }
