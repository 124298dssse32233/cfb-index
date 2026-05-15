"""Offseason wire fallback — REAL retro content, never fabricated.

When the live wire stream is thin (typical May-July dead window when no
games are happening and the portal is quiet), this module surfaces REAL
historical wire rows from prior years on the same calendar window, plus
real recent recruiting commits, plus real archive Reddit threads. It NEVER
fabricates player names or transactions.

Historical context: an earlier version of this file shipped 14 hardcoded
fake transactions with real player names attached to invented destinations
(Quinn Ewers to Ohio State, Glenn Schumann leaving Georgia, etc.) labeled
``source_kind='unverified'``. The label was invisible to the reader; the
wire panel rendered the headline verbatim. That was effectively publishing
fan-fiction transactions as news during the dead months — fixed
2026-05-15 per IMPLEMENTATION_PLAN.md Part 4 Sprint v5-1 Day 1 Patch 5.

Priority order for real-data fallback (each row carries its own real source):

  1. Same MM-DD ±2 days wire rows from prior years (2020-2024). Tag each
     with ``retro_year`` so the renderer can prefix "5 years ago today:".

  2. Top recruiting commits from current year (player_recruiting_profiles,
     star_rating >= 4, committed in last 14d). Real names, real schools.

  3. Top high-engagement archive_threads from the same calendar week N
     years back (Arctic Shift 2014-2025 backfill). Real Reddit threads
     with real titles + scores.

If all three sources are empty, returns ``[]``. The wire panel renders
empty rather than showing fabricated content. This is the correct
graceful-degradation path — an empty panel signals "no signal", which
is honest; a fabricated panel signals "real news", which is fraud.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

log = logging.getLogger(__name__)


def get_offseason_fallback_entries(
    db: sqlite3.Connection | None = None,
    *,
    today: date | None = None,
    target_count: int = 14,
) -> list[dict[str, Any]]:
    """Return REAL retro wire entries for offseason display.

    Args:
        db: Optional SQLite connection. If None or DB is empty/missing
            the relevant tables, returns [] rather than fabricating.
        today: Defaults to ``date.today()``. Used for same-MM-DD lookups.
        target_count: Maximum rows to return.

    Returns:
        A list of wire entry dictionaries, each carrying real source
        attribution. Never fabricates; empty list when no real signal
        is available.
    """
    if db is None:
        log.info("offseason_fallback: no DB provided — returning empty (correct graceful-degrade path)")
        return []

    today = today or date.today()
    target_md = today.strftime("%m-%d")
    rows: list[dict[str, Any]] = []

    # ────────────────────────────────────────────────────────────────────
    # Priority 1: Real same-MM-DD wire rows from prior 1-5 years
    # ────────────────────────────────────────────────────────────────────
    try:
        for year_offset in range(1, 6):
            if len(rows) >= target_count:
                break
            retro_year = today.year - year_offset
            cur = db.execute(
                """
                SELECT
                    occurred_at, program_slug, program_display, action,
                    actor_kind, source_kind, source_url, source_name,
                    fan_intel_velocity_spike, related_thread_slug,
                    why_it_matters, impact_label, impact_color,
                    ? AS retro_year
                FROM wire_entries
                WHERE strftime('%m-%d', occurred_at) BETWEEN ? AND ?
                  AND strftime('%Y', occurred_at) = ?
                  AND source_kind NOT IN ('retro', 'unverified', 'fallback')
                  AND program_slug IS NOT NULL
                ORDER BY COALESCE(fan_intel_velocity_spike, 0) DESC,
                         occurred_at DESC
                LIMIT ?
                """,
                (
                    retro_year,
                    (today - timedelta(days=2)).strftime("%m-%d"),
                    (today + timedelta(days=2)).strftime("%m-%d"),
                    str(retro_year),
                    target_count - len(rows),
                ),
            )
            for r in cur.fetchall():
                d = dict(r) if hasattr(r, "keys") else _row_to_dict(cur, r)
                # Mark this as retro and rewrite action to prefix the year
                d["source_kind"] = "retro"
                d["source_name"] = (d.get("source_name") or "Historical") + f" · {year_offset}y ago"
                d["action"] = f"{year_offset} {'year' if year_offset == 1 else 'years'} ago today: {d['action']}"
                rows.append(d)
    except sqlite3.Error as exc:
        log.warning("offseason_fallback: wire_entries retro query failed (%s); skipping", exc)

    # ────────────────────────────────────────────────────────────────────
    # Priority 2: Real recent 4★+ commits from player_recruiting_profiles
    # ────────────────────────────────────────────────────────────────────
    if len(rows) < target_count:
        try:
            cur = db.execute(
                """
                SELECT
                    committed_at AS occurred_at,
                    committed_team AS program_slug,
                    committed_team_display AS program_display,
                    first_name, last_name, position, star_rating,
                    classification_year, recruit_type, source_url
                FROM player_recruiting_profiles
                WHERE committed_team IS NOT NULL
                  AND star_rating >= 4
                  AND date(committed_at) >= date(?, '-14 days')
                ORDER BY star_rating DESC, committed_at DESC
                LIMIT ?
                """,
                (today.isoformat(), target_count - len(rows)),
            )
            for r in cur.fetchall():
                d = dict(r) if hasattr(r, "keys") else _row_to_dict(cur, r)
                name = f"{d.get('first_name','')} {d.get('last_name','')}".strip() or "Recruit"
                pos = d.get("position") or "Player"
                stars = d.get("star_rating", 0)
                year = d.get("classification_year") or ""
                kind = (d.get("recruit_type") or "commit").lower()
                stars_str = "★" * int(stars) if isinstance(stars, (int, float)) else ""
                rows.append({
                    "occurred_at": d.get("occurred_at") or today.isoformat(),
                    "program_slug": d.get("program_slug"),
                    "program_display": d.get("program_display"),
                    "action": (
                        f"{stars_str} {pos} {name} {kind}s {year}".strip()
                        if kind in ("commit", "flip")
                        else f"{stars_str} {pos} {name} {kind}".strip()
                    ),
                    "actor_kind": "player",
                    "source_kind": "cfbd-recruit",
                    "source_url": d.get("source_url"),
                    "source_name": "CFBD recruiting feed",
                    "fan_intel_velocity_spike": int(stars * 15) if stars else 50,
                    "related_thread_slug": None,
                    "why_it_matters": None,  # editorial fills this in later
                    "impact_label": "BLUE CHIP" if stars >= 5 else "COMMIT",
                    "impact_color": "green" if stars >= 5 else "muted",
                })
        except sqlite3.Error as exc:
            log.warning(
                "offseason_fallback: player_recruiting_profiles retro query failed (%s); skipping",
                exc,
            )

    # ────────────────────────────────────────────────────────────────────
    # Priority 3: Real archive_threads from same calendar week N years ago
    # ────────────────────────────────────────────────────────────────────
    if len(rows) < target_count:
        try:
            cur = db.execute(
                """
                SELECT
                    created_at AS occurred_at,
                    title, subreddit, score, url
                FROM archive_threads
                WHERE strftime('%m-%d', created_at) BETWEEN ? AND ?
                  AND score >= 50
                ORDER BY score DESC, created_at DESC
                LIMIT ?
                """,
                (
                    (today - timedelta(days=3)).strftime("%m-%d"),
                    (today + timedelta(days=3)).strftime("%m-%d"),
                    target_count - len(rows),
                ),
            )
            for r in cur.fetchall():
                d = dict(r) if hasattr(r, "keys") else _row_to_dict(cur, r)
                created = d.get("occurred_at") or ""
                year = created[:4] if isinstance(created, str) and len(created) >= 4 else "earlier"
                title = d.get("title") or "(untitled thread)"
                sub = d.get("subreddit") or "r/CFB"
                rows.append({
                    "occurred_at": d.get("occurred_at"),
                    "program_slug": None,
                    "program_display": "On this date",
                    "action": f"{year}: r/{sub} thread '{title[:120]}'",
                    "actor_kind": "archive",
                    "source_kind": "archive-thread",
                    "source_url": d.get("url"),
                    "source_name": f"Arctic Shift archive · r/{sub}",
                    "fan_intel_velocity_spike": min(95, 50 + int(d.get("score", 0) // 50)),
                    "related_thread_slug": None,
                    "why_it_matters": None,
                    "impact_label": "ARCHIVE",
                    "impact_color": "muted",
                })
        except sqlite3.Error as exc:
            log.warning("offseason_fallback: archive_threads retro query failed (%s); skipping", exc)

    log.info(
        "offseason_fallback: returning %d real retro rows (target=%d, today=%s)",
        len(rows), target_count, today.isoformat(),
    )
    return rows[:target_count]


def _row_to_dict(cur: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    """Fallback for cursors that don't return Row objects."""
    if cur.description is None:
        return {}
    return {col[0]: val for col, val in zip(cur.description, row)}


# ───────────────────────────────────────────────────────────────────────────
# Backwards compatibility shim
# ───────────────────────────────────────────────────────────────────────────
# The original signature took no arguments. Callers that haven't yet been
# updated to pass `db` get [] back (graceful degradation; surfaces empty
# panel rather than fabricated content). New callers should pass `db`.
#
# `OFFSEASON_FALLBACK_ENTRIES` is intentionally NOT exported anymore. Any
# code importing the constant directly will now ImportError, which is the
# correct breakage signal — "you were relying on fake transactions; you
# need to refactor to use the real-data path."
