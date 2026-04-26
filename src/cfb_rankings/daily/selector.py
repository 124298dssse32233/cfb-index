"""Phase 2 — Input selector for The Daily.

Reads the last 24h of wire_entries, storyline_chapters/threads,
team_pulse_cache, predictive_claims, and (optionally) conference_pulse_state.
Returns a DailyInputBundle ranked by fan-resonance score.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from .data import (
    DailyInputBundle,
    PulseSpike,
    ResolvedReceipt,
    ThreadCandidate,
    WireCandidate,
)

log = logging.getLogger(__name__)

_TOP_WIRE = 20
_TOP_THREADS = 8
_TOP_PULSE = 5
_TOP_RECEIPTS = 5
_FINAL_CANDIDATES = 12

# mood delta threshold for pulse spike inclusion
_PULSE_DELTA_MIN = 15.0
# minimum surprise_index for resolved receipts
_RECEIPT_SURPRISE_MIN = 60.0


def _window_start(edition_date: str) -> str:
    """ISO datetime for 24h before midnight on edition_date."""
    d = datetime.strptime(edition_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (d - timedelta(hours=24)).isoformat()


def _window_end(edition_date: str) -> str:
    """ISO datetime for end of edition_date (06:00 ET ≈ 11:00 UTC)."""
    d = datetime.strptime(edition_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (d + timedelta(hours=11)).isoformat()


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _fetch_wire(conn, window_start: str, edition_date: str) -> list[WireCandidate]:
    if not _table_exists(conn, "wire_entries"):
        log.debug("wire_entries table absent — skipping wire candidates")
        return []
    rows = conn.execute(
        """
        SELECT id, program_slug, program_display, action, why_it_matters,
               COALESCE(source_name, 'Unknown Source') AS source_name,
               occurred_at,
               COALESCE(fan_intel_velocity_spike, 50) AS velocity_score,
               impact_label
        FROM wire_entries
        WHERE occurred_at >= ?
        ORDER BY velocity_score DESC
        LIMIT ?
        """,
        (window_start, _TOP_WIRE),
    ).fetchall()
    candidates = []
    for r in rows:
        candidates.append(WireCandidate(
            wire_id=r[0],
            program_slug=r[1] or "",
            program_display=r[2],
            action=r[3],
            why_it_matters=r[4],
            source_name=r[5],
            occurred_at=r[6],
            velocity_score=float(r[7]),
            impact_label=r[8] or "Notable",
        ))
    return candidates


def _fetch_threads(conn, window_start: str) -> list[ThreadCandidate]:
    if not _table_exists(conn, "storyline_threads") or not _table_exists(conn, "storyline_chapters"):
        log.debug("storyline tables absent — skipping thread candidates")
        return []

    # Recently updated threads (chapter in last 24h)
    recent_rows = conn.execute(
        """
        SELECT DISTINCT t.thread_slug, t.title, t.dek,
               t.primary_program_slugs,
               t.last_chapter_at,
               COALESCE(t.chapter_count, 1) * COALESCE(t.follower_count, 10) AS engagement,
               c.dek AS chapter_excerpt
        FROM storyline_threads t
        JOIN storyline_chapters c ON c.thread_slug = t.thread_slug
        WHERE c.published_at >= ?
          AND t.status = 'active'
        ORDER BY engagement DESC
        LIMIT ?
        """,
        (window_start, _TOP_THREADS),
    ).fetchall()

    # Also grab high-engagement threads even if no recent chapter (within 7d)
    older_window = (
        datetime.now(timezone.utc) - timedelta(days=7)
    ).isoformat()
    high_eng_rows = conn.execute(
        """
        SELECT DISTINCT t.thread_slug, t.title, t.dek,
               t.primary_program_slugs,
               t.last_chapter_at,
               COALESCE(t.chapter_count, 1) * COALESCE(t.follower_count, 10) AS engagement,
               '' AS chapter_excerpt
        FROM storyline_threads t
        WHERE t.last_chapter_at >= ?
          AND t.status = 'active'
          AND COALESCE(t.chapter_count, 1) * COALESCE(t.follower_count, 10) > 50
        ORDER BY engagement DESC
        LIMIT ?
        """,
        (older_window, _TOP_THREADS),
    ).fetchall()

    seen: set[str] = set()
    candidates: list[ThreadCandidate] = []
    for r in list(recent_rows) + list(high_eng_rows):
        slug = r[0]
        if slug in seen:
            continue
        seen.add(slug)
        try:
            prog_slugs = json.loads(r[3] or "[]")
        except Exception:
            prog_slugs = []
        candidates.append(ThreadCandidate(
            thread_slug=slug,
            title=r[1],
            dek=r[2],
            chapter_excerpt=r[6] or r[2],
            primary_program_slugs=prog_slugs,
            last_chapter_at=r[4] or "",
            engagement_proxy=float(r[5] or 0),
        ))
    return candidates[:_TOP_THREADS]


def _fetch_pulse_spikes(conn) -> list[PulseSpike]:
    if not _table_exists(conn, "team_pulse_cache"):
        log.debug("team_pulse_cache absent — skipping pulse spikes")
        return []
    rows = conn.execute(
        """
        SELECT entity_slug, entity_type,
               COALESCE(lede, '') AS lede,
               COALESCE(themes_json, '[]') AS themes_json
        FROM team_pulse_cache
        WHERE lede IS NOT NULL
        ORDER BY generated_at_utc DESC
        LIMIT ?
        """,
        (_TOP_PULSE * 4,),
    ).fetchall()
    spikes = []
    for r in rows:
        spikes.append(PulseSpike(
            entity_slug=r[0],
            entity_type=r[1],
            lede=r[2],
            themes_json=r[3],
            mood_delta=_PULSE_DELTA_MIN + 5.0,  # treat all cached as above threshold
        ))
    return spikes[:_TOP_PULSE]


def _fetch_resolved_receipts(conn, window_start: str) -> list[ResolvedReceipt]:
    if not _table_exists(conn, "predictive_claims"):
        log.debug("predictive_claims absent — skipping receipts")
        return []
    rows = conn.execute(
        """
        SELECT pc.id,
               COALESCE(sp.display_name, pc.source_slug) AS source_display,
               pc.source_slug,
               pc.claim_summary_short,
               pc.outcome_verdict,
               COALESCE(pc.surprise_index, 50) AS surprise_index,
               pc.claim_text
        FROM predictive_claims pc
        LEFT JOIN source_profiles sp ON sp.source_slug = pc.source_slug
        WHERE pc.outcome_resolved = 1
          AND pc.outcome_resolved_at >= ?
          AND pc.outcome_verdict = 'hit'
          AND COALESCE(pc.surprise_index, 0) >= ?
        ORDER BY pc.surprise_index DESC
        LIMIT ?
        """,
        (window_start, _RECEIPT_SURPRISE_MIN, _TOP_RECEIPTS),
    ).fetchall()
    receipts = []
    for r in rows:
        receipts.append(ResolvedReceipt(
            claim_id=r[0],
            source_display=r[1],
            source_slug=r[2],
            claim_summary_short=r[3],
            outcome_verdict=r[4],
            surprise_index=float(r[5]),
            claim_text=r[6],
        ))
    return receipts


def _fetch_conference_pulse(conn) -> list[str]:
    """Optional: return theme summaries if conference_pulse_state exists."""
    if not _table_exists(conn, "conference_pulse_state"):
        return []
    try:
        rows = conn.execute(
            "SELECT conference_slug, theme_summary FROM conference_pulse_state LIMIT 5"
        ).fetchall()
        return [f"{r[0]}: {r[1]}" for r in rows if r[1]]
    except Exception as exc:
        log.debug("conference_pulse_state query failed: %s", exc)
        return []


def select_inputs(conn, edition_date: str) -> DailyInputBundle:
    """Return a DailyInputBundle with top candidates for the given edition_date."""
    window_start = _window_start(edition_date)
    now_iso = datetime.now(timezone.utc).isoformat()

    wire = _fetch_wire(conn, window_start, edition_date)
    threads = _fetch_threads(conn, window_start)
    pulses = _fetch_pulse_spikes(conn)
    receipts = _fetch_resolved_receipts(conn, window_start)

    # Sort wire by fan-resonance score
    wire.sort(key=lambda w: w.fan_resonance(now_iso), reverse=True)
    wire = wire[:_TOP_WIRE]

    log.info(
        "select_inputs(%s): wire=%d threads=%d pulses=%d receipts=%d",
        edition_date, len(wire), len(threads), len(pulses), len(receipts),
    )

    return DailyInputBundle(
        edition_date=edition_date,
        wire_candidates=wire,
        thread_candidates=threads,
        pulse_spikes=pulses,
        resolved_receipts=receipts,
    )
