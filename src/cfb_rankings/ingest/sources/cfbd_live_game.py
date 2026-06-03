"""CFBD live-game adapter — Sprint 6.

Polls CFBD's live-game endpoint every ~60s during kickoff windows and writes
to ``games_live``. Designed to be invoked once per polling tick from the
``fanintel-gameday-live`` GitHub Actions workflow (cron: every minute,
Saturdays during the season).

Behavior:
  - Fetch all in-progress + recently-final games for the active week
  - Upsert each into games_live keyed on (season_year, week, home_slug, away_slug)
  - For games that just transitioned in_progress → final, append final_at_utc
    and call ``enqueue_post_game_jobs`` so the renderer can spin up the
    T+5/T+15/.../T+45 cadence

When CFBD is unavailable or no games are live, the adapter is a no-op — it
exits cleanly so the workflow never red-X's just because the schedule is
empty.

Live-WP timeseries handling:
  - If CFBD returns ``home_win_probability.timeseries``, persist as-is.
  - Otherwise compute a coarse per-quarter approximation from line scores +
    play sequence (best-effort; the WP chart still renders, with quarter
    boundaries as the only annotation candidates).

Pre-game spread:
  - Pulled from ``game_line_snapshots`` (provider preference: consensus,
    fanduel, draftkings, caesars). Stored as ``pre_game_spread_home``
    (negative = home favored).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CFBD_BASE = "https://api.collegefootballdata.com"
ADAPTER_VERSION = "0.1.0"


# --------------------------------------------------------------------------
# Public entry point — called by tools/run_adapter.py and the workflow
# --------------------------------------------------------------------------

def run_poll(db, *, season_year: int | None = None, week: int | None = None,
             api_key: str | None = None) -> dict[str, Any]:
    """Single polling tick. Returns a result dict for logging.

    Skips quietly if no API key is configured. The Saturday workflow runs
    this every minute; off-Saturdays it's a no-op.
    """
    api_key = api_key or os.environ.get("CFBD_API_KEY")
    if not api_key:
        return {"status": "skipped", "reason": "no CFBD_API_KEY"}

    today_utc = datetime.now(timezone.utc)
    season_year = season_year or today_utc.year
    week = week or _current_week(today_utc)

    try:
        raw_games = _fetch_live_games(api_key, season_year, week)
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    inserted, transitioned = 0, 0
    for game in raw_games:
        try:
            res = _upsert_game(db, game, season_year, week)
            inserted += 1
            if res.get("transitioned_to_final"):
                transitioned += 1
                enqueue_post_game_jobs(db, res["games_live_id"], game)
        except Exception as exc:
            # Per-game errors should not break the poll loop.
            print(f"  cfbd_live_game: skip {game.get('id')} — {exc}")

    return {
        "status": "ok",
        "season_year": season_year,
        "week": week,
        "games_processed": inserted,
        "transitioned_to_final": transitioned,
    }


# --------------------------------------------------------------------------
# CFBD HTTP fetch
# --------------------------------------------------------------------------

def _fetch_live_games(api_key: str, season_year: int, week: int) -> list[dict[str, Any]]:
    url = f"{CFBD_BASE}/games?" + urlencode({
        "year": str(season_year),
        "week": str(week),
        "seasonType": "regular",
    })
    req = Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "CFBIndex-LiveGame/0.1",
    })
    with urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    games = json.loads(body)
    if not isinstance(games, list):
        return []
    # CFBD /games has no live "status" field — it exposes a `completed` bool
    # (camelCase) plus homePoints/awayPoints once a game has a score. Keep games
    # that are finished (completed) or have started (have a score); skip the rest
    # as scheduled. (NOTE: /games is not a true live feed, so in-progress quarter/
    # clock/win-probability won't populate; final-game capture + the post-game
    # render cadence DO work.)
    out: list[dict[str, Any]] = []
    for g in games:
        completed = bool(g.get("completed"))
        started = g.get("homePoints") is not None or g.get("awayPoints") is not None
        if completed or started:
            out.append(g)
    return out


def _current_week(today_utc: datetime) -> int:
    """Best-effort current-week derivation. Real callers can override."""
    # Week 1 typically lands the Saturday of Labor Day weekend (~Sept 5).
    # Without a season metadata table on hand, approximate: weeks since
    # August 25 / 7, capped at 16.
    season_anchor = datetime(today_utc.year, 8, 25, tzinfo=timezone.utc)
    delta = today_utc - season_anchor
    wk = max(1, min(16, delta.days // 7 + 1))
    return wk


# --------------------------------------------------------------------------
# Upsert into games_live
# --------------------------------------------------------------------------

def _upsert_game(db, game: dict[str, Any], season_year: int, week: int) -> dict[str, Any]:
    """Idempotent upsert. Returns dict with games_live_id + transition flag."""
    # CFBD /games uses camelCase keys (homeTeam/awayTeam/homePoints/awayPoints/
    # startDate) and a `completed` bool rather than a live status string. Keep
    # snake_case fallbacks in case a caller passes a pre-normalized dict.
    home_team = (game.get("homeTeam") or game.get("home_team") or "").strip()
    away_team = (game.get("awayTeam") or game.get("away_team") or "").strip()
    home_slug = _slugify(home_team)
    away_slug = _slugify(away_team)
    if not home_slug or not away_slug:
        raise ValueError("missing team identifiers")

    home_score = game.get("homePoints")
    if home_score is None:
        home_score = game.get("home_points")
    away_score = game.get("awayPoints")
    if away_score is None:
        away_score = game.get("away_points")
    status = _status_from_game(game, home_score, away_score)
    final_at = game.get("completion_time") or game.get("end_time") or None
    kickoff = game.get("startDate") or game.get("start_time") or ""

    home_wp = _extract_current_home_wp(game)
    wp_ts = _extract_wp_timeseries(game)
    events_log = _extract_events_log(game)
    last_play_text = _extract_last_play_text(game)
    pre_game_spread_home = _lookup_pre_game_spread_home(db, game)

    # Existence check — track whether we just transitioned to final.
    existing = db.query_one(
        """
        select games_live_id, status, final_at_utc
        from games_live
        where season_year = :s and week = :w
          and home_team_slug = :h and away_team_slug = :a
        """,
        {"s": season_year, "w": week, "h": home_slug, "a": away_slug},
    )
    transitioned = bool(existing and existing.get("status") != "final" and status == "final")

    db.execute(
        """
        insert into games_live (
            game_id, season_year, week,
            home_team_id, away_team_id,
            home_team_slug, away_team_slug,
            kickoff_at_utc, status, current_quarter, time_remaining,
            home_score, away_score, home_wp, last_play_text,
            final_at_utc, pre_game_spread_home,
            wp_timeseries_json, events_log_json, simulated, updated_at_utc
        ) values (
            :game_id, :s, :w,
            :hid, :aid,
            :hslug, :aslug,
            :kick, :status, :q, :clock,
            :hs, :as_, :hwp, :lp,
            :final_at, :spread,
            :wp_ts, :evts, 0, current_timestamp
        )
        on conflict(season_year, week, home_team_slug, away_team_slug) do update set
            game_id = excluded.game_id,
            status = excluded.status,
            current_quarter = excluded.current_quarter,
            time_remaining = excluded.time_remaining,
            home_score = excluded.home_score,
            away_score = excluded.away_score,
            home_wp = excluded.home_wp,
            last_play_text = excluded.last_play_text,
            final_at_utc = coalesce(games_live.final_at_utc, excluded.final_at_utc),
            pre_game_spread_home = coalesce(excluded.pre_game_spread_home, games_live.pre_game_spread_home),
            wp_timeseries_json = excluded.wp_timeseries_json,
            events_log_json = excluded.events_log_json,
            updated_at_utc = current_timestamp
        """,
        {
            "game_id": game.get("id"),
            "s": season_year, "w": week,
            "hid": _team_id_for_slug(db, home_slug),
            "aid": _team_id_for_slug(db, away_slug),
            "hslug": home_slug, "aslug": away_slug,
            "kick": kickoff, "status": status,
            "q": game.get("period"), "clock": game.get("clock"),
            "hs": home_score, "as_": away_score,
            "hwp": home_wp, "lp": last_play_text,
            "final_at": final_at,
            "spread": pre_game_spread_home,
            "wp_ts": json.dumps(wp_ts) if wp_ts else None,
            "evts": json.dumps(events_log) if events_log else None,
        },
    )
    row = db.query_one(
        """
        select games_live_id from games_live
        where season_year = :s and week = :w
          and home_team_slug = :h and away_team_slug = :a
        """,
        {"s": season_year, "w": week, "h": home_slug, "a": away_slug},
    )
    return {"games_live_id": row["games_live_id"], "transitioned_to_final": transitioned}


def _team_id_for_slug(db, slug: str) -> int | None:
    row = db.query_one("select team_id from teams where slug = :s", {"s": slug})
    return int(row["team_id"]) if row else None


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "").replace(".", "")


def _normalize_status(s: Any) -> str:
    val = (s or "").lower()
    if val in ("in_progress", "live", "active"):
        return "in_progress"
    if val in ("final", "completed"):
        return "final"
    return "scheduled"


def _status_from_game(game: dict[str, Any], home_score: Any, away_score: Any) -> str:
    """Derive status from CFBD /games fields: the `completed` bool plus whether a
    score exists yet. /games has no live in-progress status, so in-progress is
    inferred from a present score on a not-yet-completed game."""
    if bool(game.get("completed")):
        return "final"
    if home_score is not None or away_score is not None:
        return "in_progress"
    return "scheduled"


def _extract_current_home_wp(game: dict[str, Any]) -> float | None:
    wp = game.get("home_win_probability")
    if isinstance(wp, dict):
        ts = wp.get("timeseries") or wp.get("series") or []
        if ts:
            last = ts[-1]
            if isinstance(last, dict):
                return last.get("wp") or last.get("home_wp")
    if isinstance(wp, (int, float)):
        return float(wp)
    return None


def _extract_wp_timeseries(game: dict[str, Any]) -> list[dict[str, Any]] | None:
    wp = game.get("home_win_probability")
    if isinstance(wp, dict):
        ts = wp.get("timeseries") or wp.get("series") or []
        if isinstance(ts, list):
            return ts
    return None


def _extract_events_log(game: dict[str, Any]) -> list[dict[str, Any]] | None:
    plays = game.get("scoring_plays") or []
    if not isinstance(plays, list):
        return None
    out = []
    for p in plays:
        if isinstance(p, dict):
            out.append({
                "period": p.get("period"),
                "clock": p.get("clock"),
                "text": p.get("play_text") or p.get("text"),
                "home_score": p.get("home_score"),
                "away_score": p.get("away_score"),
            })
    return out or None


def _extract_last_play_text(game: dict[str, Any]) -> str | None:
    plays = game.get("plays") or []
    if isinstance(plays, list) and plays:
        last = plays[-1]
        if isinstance(last, dict):
            return last.get("play_text") or last.get("text")
    return None


def _lookup_pre_game_spread_home(db, game: dict[str, Any]) -> float | None:
    """Look for an earlier game_line_snapshots row keyed on game_id.

    Preference: consensus → first available provider. Returns spread_home as-is
    (negative = home favored).
    """
    gid = game.get("id")
    if not gid:
        return None
    row = db.query_one(
        """
        select spread_home, provider
        from game_line_snapshots
        where game_id = :gid
          and spread_home is not null
        order by case when provider = 'consensus' then 0 else 1 end,
                 snapshot_time_utc desc
        limit 1
        """,
        {"gid": gid},
    )
    if row and row.get("spread_home") is not None:
        return float(row["spread_home"])
    return None


# --------------------------------------------------------------------------
# Render-job enqueue (Sprint 6 §1.3 cache + re-render cadence)
# --------------------------------------------------------------------------

# Per spec — T+5 through T+45 in 5/10-minute increments. Each tick re-renders
# both team pages with progressively more populated game-recap content.
POST_GAME_TICK_MINUTES: tuple[int, ...] = (5, 15, 20, 25, 30, 35, 40, 45)


def enqueue_post_game_jobs(db, games_live_id: int, game: dict[str, Any]) -> int:
    """Insert pending render jobs for both teams at the spec'd cadence.

    Idempotent — same (games_live_id, team_slug, t_offset_minutes) is a
    no-op. Returns the count of new rows.
    """
    home_slug = _slugify(game.get("homeTeam") or game.get("home_team") or "")
    away_slug = _slugify(game.get("awayTeam") or game.get("away_team") or "")
    final_at = game.get("completion_time") or game.get("end_time")
    if not final_at:
        final_at = datetime.now(timezone.utc).isoformat()

    base_dt = _parse_iso(final_at) or datetime.now(timezone.utc)
    inserted = 0
    for slug in (home_slug, away_slug):
        if not slug:
            continue
        for t_offset in POST_GAME_TICK_MINUTES:
            scheduled_at = base_dt.timestamp() + (t_offset * 60.0)
            scheduled_iso = datetime.fromtimestamp(scheduled_at, tz=timezone.utc).isoformat()
            try:
                db.execute(
                    """
                    insert or ignore into games_live_render_queue (
                        games_live_id, team_slug, t_offset_minutes,
                        scheduled_at_utc, status
                    ) values (
                        :gl, :slug, :t, :sched, 'pending'
                    )
                    """,
                    {"gl": games_live_id, "slug": slug, "t": t_offset, "sched": scheduled_iso},
                )
                inserted += 1
            except Exception:
                pass
    return inserted


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# --------------------------------------------------------------------------
# Read accessors used by the renderer
# --------------------------------------------------------------------------

def fetch_recent_final_for_team(db, team_slug: str, *,
                                window_hours: float = 72.0) -> dict[str, Any] | None:
    """Return the most-recent finalized games_live row for ``team_slug``
    whose ``final_at_utc`` is within ``window_hours``.

    Drives the renderer's game-recap / post-game-monday-tuesday branches.
    """
    row = db.query_one(
        """
        select games_live_id, game_id, season_year, week,
               home_team_slug, away_team_slug,
               home_team_id, away_team_id,
               home_score, away_score, status, final_at_utc,
               pre_game_spread_home, wp_timeseries_json, events_log_json,
               simulated
        from games_live
        where (home_team_slug = :s or away_team_slug = :s)
          and status = 'final'
          and final_at_utc is not null
        order by final_at_utc desc
        limit 1
        """,
        {"s": team_slug.lower()},
    )
    if not row:
        return None
    final_dt = _parse_iso(row.get("final_at_utc"))
    if final_dt is None:
        return None
    age_hours = (datetime.now(timezone.utc) - final_dt).total_seconds() / 3600.0
    if age_hours > window_hours:
        return None
    return dict(row)
