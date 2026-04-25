"""Render-queue worker — Sprint 6 §1.3 cache + re-render cadence.

Consumes ``games_live_render_queue``. For each pending row whose
``scheduled_at_utc`` is in the past, re-renders the team page (which now
reads from games_live and resolves into ``game-recap-<outcome>``), marks
the queue row 'done', and moves on.

Designed to be invoked once per minute by the same workflow that polls
``cfbd_live_game`` (or via ``manage.py process-render-queue`` from a CLI).

T+5 / T+15 / T+20 / T+25 / T+30 / T+35 / T+40 / T+45 cadence per the
spec — each tick gives the GameRecapHero progressively more populated
content as the post-game pipelines (Opus narrative, diagnosis stats,
Chronicle game-edition cards) finish.

The worker is intentionally idempotent at the page level — re-rendering
the same team's page on tick T+30 simply overwrites the HTML that was
written at T+15. State accumulates in ``games_live`` and downstream
caches; the renderer reads the latest snapshot every time.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "output/site/teams"


def process_queue(
    db,
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    max_jobs: int = 50,
    log: Any = None,
) -> dict[str, Any]:
    """Process all due render jobs in one tick.

    Returns a dict with counts: ``processed``, ``ok``, ``failed``, ``skipped``.

    A job is "due" when ``status='pending'`` AND ``scheduled_at_utc`` is
    in the past. We claim each job by flipping it to ``running`` before
    starting the render, then to ``done`` (or ``failed`` with last_error).
    SQLite has no native row locking, so this worker assumes a single
    consumer per polling tick (the gameday workflow runs serially anyway).
    """
    logf = _logger(log)
    now_iso = datetime.now(timezone.utc).isoformat()

    rows = db.query_all(
        """
        select queue_id, games_live_id, team_slug, t_offset_minutes,
               scheduled_at_utc
        from games_live_render_queue
        where status = 'pending'
          and scheduled_at_utc <= :now
        order by scheduled_at_utc asc
        limit :lim
        """,
        {"now": now_iso, "lim": max_jobs},
    ) or []

    if not rows:
        logf("render-queue: no pending jobs due")
        return {"processed": 0, "ok": 0, "failed": 0, "skipped": 0}

    counts = {"processed": 0, "ok": 0, "failed": 0, "skipped": 0}
    output_path = Path(output_dir)

    for row in rows:
        qid = row["queue_id"]
        slug = row["team_slug"]
        t_offset = row["t_offset_minutes"]

        # Claim
        try:
            db.execute(
                "update games_live_render_queue set status='running' where queue_id=:q",
                {"q": qid},
            )
        except Exception as exc:
            logf(f"render-queue: claim failed for {qid} — {exc}")
            counts["skipped"] += 1
            continue
        counts["processed"] += 1

        # Render
        try:
            from .renderer import render_team_page
            html_path = render_team_page(db, slug, output_path)
            db.execute(
                """
                update games_live_render_queue
                set status='done', completed_at_utc=:c, last_error=null
                where queue_id=:q
                """,
                {"q": qid, "c": datetime.now(timezone.utc).isoformat()},
            )
            logf(f"render-queue: T+{t_offset:>2}m {slug} → {html_path}")
            counts["ok"] += 1
        except FileNotFoundError as exc:
            # Profile missing — mark done (not failed) so we don't retry.
            db.execute(
                """
                update games_live_render_queue
                set status='done', completed_at_utc=:c,
                    last_error='profile-missing'
                where queue_id=:q
                """,
                {"q": qid, "c": datetime.now(timezone.utc).isoformat()},
            )
            logf(f"render-queue: T+{t_offset:>2}m {slug} skip (no profile)")
            counts["skipped"] += 1
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            db.execute(
                """
                update games_live_render_queue
                set status='failed', completed_at_utc=:c, last_error=:e
                where queue_id=:q
                """,
                {"q": qid, "c": datetime.now(timezone.utc).isoformat(), "e": err[:400]},
            )
            logf(f"render-queue: T+{t_offset:>2}m {slug} FAILED — {err}")
            counts["failed"] += 1

    logf(
        f"render-queue tick: processed={counts['processed']} "
        f"ok={counts['ok']} failed={counts['failed']} skipped={counts['skipped']}"
    )
    return counts


def queue_summary(db) -> dict[str, int]:
    """Return per-status counts for the render queue. Used by the CLI."""
    rows = db.query_all(
        """
        select status, count(*) as n
        from games_live_render_queue
        group by status
        """
    ) or []
    out = {"pending": 0, "running": 0, "done": 0, "failed": 0}
    for r in rows:
        out[r["status"]] = int(r["n"])
    return out


def _logger(log: Any):
    if log is None:
        return lambda msg: print(msg, flush=True)
    if callable(log):
        return log
    if hasattr(log, "write"):
        return lambda msg: (log.write(msg + "\n"), log.flush())
    return lambda msg: print(msg, flush=True)
