"""Read-only data accessors for team-page rendering.

All SQL lives here. The renderer + narrative generator consume typed
dataclasses, never raw rows. Every function is deliberately small and
pure — no side effects, no caching layer beyond the caller's.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# Poll + prediction ranking system names, as they live in official_rankings.
AP_SYSTEM = "AP Top 25"
COACHES_SYSTEM = "Coaches Poll"
CFP_SYSTEM = "Playoff Committee Rankings"


# Floor thresholds for the fan-intelligence floor rule. Single source of
# truth for the data-layer reader AND the renderer — DO NOT duplicate.
# <FLOOR_AWAITING is rendered as "Awaiting Signal" (no sparkline, no
# velocity number, takes fall back to profile stock phrases).
# FLOOR_AWAITING ≤ effective_n < FLOOR_GROWING shows a sample-growing
# badge with the live data we have. ≥ FLOOR_GROWING gets the full render
# with no caveat.
FLOOR_AWAITING = 20.0
FLOOR_GROWING = 100.0


@dataclass
class GameResult:
    season_year: int
    week: int
    opponent_id: int
    opponent_name: str
    opponent_slug: str | None
    is_home: bool
    team_points: int | None
    opp_points: int | None
    status: str
    margin: int | None = None
    outcome: str | None = None  # 'W' / 'L' / 'T' / 'upcoming'
    start_time_utc: str | None = None  # ISO 8601, when known

    def label(self) -> str:
        if self.outcome in (None, "upcoming"):
            loc = "vs" if self.is_home else "at"
            return f"{loc} {self.opponent_name}"
        return f"{self.outcome} {self.team_points}-{self.opp_points} {('vs' if self.is_home else 'at')} {self.opponent_name}"


@dataclass
class TeamSnapshot:
    team_id: int
    slug: str
    canonical_name: str
    school_name: str | None
    level_code: str
    conference_id: int | None
    conference_name: str | None
    season_year: int
    wins: int
    losses: int
    ties: int
    ap_rank: int | None
    coaches_rank: int | None
    cfp_rank: int | None
    recent_games: list[GameResult] = field(default_factory=list)
    next_game: GameResult | None = None
    last_game: GameResult | None = None
    season_complete: bool = False


def fetch_team_row(db, slug: str) -> dict[str, Any]:
    row = db.query_one(
        """
        select t.team_id, t.slug, t.canonical_name, t.school_name, t.level_code,
               t.current_conference_id, c.conference_name as conf_name
        from teams t
        left join conferences c on c.conference_id = t.current_conference_id
        where t.slug = :slug
        """,
        {"slug": slug},
    )
    if not row:
        raise LookupError(f"team slug not found: {slug}")
    return dict(row)


def _latest_season_with_games(db, team_id: int) -> int:
    row = db.query_one(
        """
        select max(season_year) as y
        from games
        where (home_team_id = :tid or away_team_id = :tid)
          and status in ('Final','final','FINAL')
        """,
        {"tid": team_id},
    )
    # Fall back to the current calendar year rather than a hardcoded
    # literal. Previously this returned 2025 unconditionally on missing-
    # game teams, which silently froze a team's "current snapshot" at
    # 2025 once the calendar rolled into 2026.
    from datetime import datetime as _dt
    return int(row["y"]) if row and row["y"] else _dt.utcnow().year


def fetch_team_snapshot(db, slug: str, season_year: int | None = None) -> TeamSnapshot:
    """Build a season-level snapshot for the team.

    If season_year is None, uses the most recent season for which the team
    has games. Rankings come from the max-week official_rankings row.
    """
    team = fetch_team_row(db, slug)
    tid = int(team["team_id"])
    if season_year is None:
        season_year = _latest_season_with_games(db, tid)

    games = _fetch_games(db, tid, season_year)
    wins = sum(1 for g in games if g.outcome == "W")
    losses = sum(1 for g in games if g.outcome == "L")
    ties = sum(1 for g in games if g.outcome == "T")

    last_game = next((g for g in reversed(games) if g.outcome in ("W", "L", "T")), None)
    next_game = next((g for g in games if g.outcome == "upcoming"), None)

    ap_rank = _latest_rank(db, tid, season_year, AP_SYSTEM)
    coaches_rank = _latest_rank(db, tid, season_year, COACHES_SYSTEM)
    cfp_rank = _latest_rank(db, tid, season_year, CFP_SYSTEM)

    # "Complete" heuristic: last game played + we're past the natural regular
    # season (week >= 14 or past Dec 15 of that season).
    season_complete = bool(
        last_game
        and (last_game.week or 0) >= 14
        and next_game is None
    )

    return TeamSnapshot(
        team_id=tid,
        slug=team["slug"],
        canonical_name=team["canonical_name"],
        school_name=team.get("school_name"),
        level_code=team["level_code"],
        conference_id=team.get("current_conference_id"),
        conference_name=team.get("conf_name"),
        season_year=season_year,
        wins=wins,
        losses=losses,
        ties=ties,
        ap_rank=ap_rank,
        coaches_rank=coaches_rank,
        cfp_rank=cfp_rank,
        recent_games=games[-8:],
        next_game=next_game,
        last_game=last_game,
        season_complete=season_complete,
    )


def _fetch_games(db, team_id: int, season_year: int) -> list[GameResult]:
    rows = db.query_all(
        """
        select g.season_year, g.week, g.status,
               g.start_time_utc,
               g.home_team_id, g.away_team_id,
               g.home_points, g.away_points,
               ht.canonical_name as home_name, ht.slug as home_slug,
               at.canonical_name as away_name, at.slug as away_slug
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where g.season_year = :season
          and (g.home_team_id = :tid or g.away_team_id = :tid)
        order by coalesce(g.week, 0), coalesce(g.start_time_utc, '')
        """,
        {"season": season_year, "tid": team_id},
    )
    out: list[GameResult] = []
    for r in rows:
        is_home = int(r["home_team_id"]) == team_id
        opp_id = int(r["away_team_id"] if is_home else r["home_team_id"])
        opp_name = r["away_name"] if is_home else r["home_name"]
        opp_slug = r["away_slug"] if is_home else r["home_slug"]
        t_pts = r["home_points"] if is_home else r["away_points"]
        o_pts = r["away_points"] if is_home else r["home_points"]
        status = (r["status"] or "").lower()
        margin = None
        outcome = "upcoming"
        if status in ("final", "completed") and t_pts is not None and o_pts is not None:
            margin = int(t_pts) - int(o_pts)
            outcome = "W" if margin > 0 else ("L" if margin < 0 else "T")
        out.append(
            GameResult(
                season_year=int(r["season_year"]),
                week=int(r["week"] or 0),
                opponent_id=opp_id,
                opponent_name=opp_name,
                opponent_slug=opp_slug,
                is_home=is_home,
                team_points=int(t_pts) if t_pts is not None else None,
                opp_points=int(o_pts) if o_pts is not None else None,
                status=r["status"] or "",
                margin=margin,
                outcome=outcome,
                start_time_utc=r["start_time_utc"] if "start_time_utc" in r.keys() else None,
            )
        )
    return out


def _latest_rank(db, team_id: int, season_year: int, system: str) -> int | None:
    row = db.query_one(
        """
        select rank_value
        from official_rankings
        where team_id = :tid and season_year = :season
          and ranking_system = :sys
        order by week desc, rank_value asc
        limit 1
        """,
        {"tid": team_id, "season": season_year, "sys": system},
    )
    if not row or row["rank_value"] is None:
        return None
    return int(row["rank_value"])


def _mood_from_cohort_week(db, team_id: int) -> dict[str, Any] | None:
    """Build a Pulse mood payload from team_cohort_week.

    Aggregates the latest 8 weeks. For each week, computes weighted
    mean sentiment across cohorts (weight = effective_n). Returns None
    when the latest week is below the awaiting-signal floor or has no
    sentiment values, signaling the caller should fall back to the
    legacy team_week_conversation_features path.
    """
    rows = db.query_all(
        """
        with recent as (
            select distinct week
            from team_cohort_week
            where team_id = :tid
            order by week desc
            limit 8
        )
        select tcw.week,
               sum(tcw.effective_n) as eff_n_total,
               sum(case when tcw.sentiment_score is not null
                        then tcw.sentiment_score * tcw.effective_n end) as wsent,
               sum(case when tcw.sentiment_score is not null
                        then tcw.effective_n end) as eff_n_with_sent,
               sum(tcw.volume) as vol_total,
               max(tcw.confidence_tier) as conf
        from team_cohort_week tcw
        join recent r on r.week = tcw.week
        where tcw.team_id = :tid
        group by tcw.week
        order by tcw.week desc
        """,
        {"tid": team_id},
    )
    if not rows:
        return None

    # Headline reading = the most recent week within the last 8 that BOTH
    # has sentiment AND clears the awaiting-signal floor at the team level.
    # Looking back through the window (not strictly the latest week)
    # smooths over offseason gaps where one calendar week may have only a
    # handful of docs while a prior week is more representative.
    headline_idx = next(
        (
            i for i, r in enumerate(rows)
            if (r["wsent"] is not None
                and float(r["eff_n_with_sent"] or 0.0) > 0
                and float(r["eff_n_total"] or 0.0) >= FLOOR_AWAITING)
        ),
        None,
    )
    if headline_idx is None:
        return None
    latest = rows[headline_idx]
    eff_n = float(latest["eff_n_total"] or 0.0)
    eff_n_with_sent = float(latest["eff_n_with_sent"] or 0.0)
    latest_sent = float(latest["wsent"]) / eff_n_with_sent

    # Trajectory in chronological order, oldest → newest.
    trajectory: list[dict[str, Any]] = []
    for r in reversed(rows):
        n_with_sent = float(r["eff_n_with_sent"] or 0.0)
        wsent_total = r["wsent"]
        sent = (float(wsent_total) / n_with_sent) if (wsent_total is not None and n_with_sent > 0) else 0.0
        trajectory.append({
            "week": r["week"],
            "net_sentiment": sent,
            "volume": int(r["vol_total"] or 0),
        })

    mood_delta: float | None = None
    if len(rows) > 1:
        prev = rows[1]
        prev_n_sent = float(prev["eff_n_with_sent"] or 0.0)
        if prev_n_sent > 0 and prev["wsent"] is not None:
            prev_sent = float(prev["wsent"]) / prev_n_sent
            mood_delta = latest_sent - prev_sent

    confidence = (latest["conf"] or "B").lower()
    confidence_tier = {
        "a": "high", "b": "medium", "c": "low",
    }.get(confidence, "medium")

    return {
        "has_data": True,
        "mood_value": _mood_display(latest_sent),
        "raw_sentiment": latest_sent,
        "mood_delta": mood_delta,
        "trajectory": trajectory,
        "top_storyline": None,  # cohort path has no storyline join yet
        "confidence_tier": confidence_tier,
        "latest_week": latest["week"],
        "volume": int(latest["vol_total"] or 0),
        "effective_n": eff_n,
    }


def fetch_mood_snapshot(db, team_id: int, season_year: int) -> dict[str, Any]:
    """Pulse module: latest team mood / sentiment + recent weeks' trajectory.

    Layered source resolution:
      1. ``team_cohort_week`` — the new fan-intel pipeline (preferred when
         the team crosses the awaiting-signal floor). Aggregates sentiment
         across cohorts weighted by effective_n.
      2. ``team_week_conversation_features`` — legacy reddit-only mood
         scores. Used when the cohort pipeline has no usable signal yet.

    Returns {}-equivalent fallback if neither source has a usable signal
    for this team-season. Renderer treats missing fields as "no signal"
    and shows the profile's mascot voice 'awaiting_signal' string.
    """
    cohort_payload = _mood_from_cohort_week(db, team_id)
    if cohort_payload is not None:
        return cohort_payload

    rows = db.query_all(
        """
        select week, net_sentiment_score, mean_sentiment_score,
               mention_count, joy_share, anger_share, fear_share,
               top_storyline_json, sample_n, confidence_floor
        from team_week_conversation_features
        where team_id = :tid
          and season_year = :season
          and source_name = 'all'
          and audience_bucket = 'all'
        order by week desc
        limit 8
        """,
        {"tid": team_id, "season": season_year},
    )
    if not rows:
        return {
            "has_data": False,
            "mood_value": None,
            "mood_delta": None,
            "trajectory": [],
            "top_storyline": None,
            "confidence_tier": None,
            "effective_n": fetch_team_effective_n(db, team_id),
        }
    trajectory = []
    for r in reversed(rows):
        trajectory.append({
            "week": int(r["week"]),
            "net_sentiment": float(r["net_sentiment_score"] or 0.0),
            "volume": int(r["mention_count"] or 0),
        })
    latest = rows[0]
    prev = rows[1] if len(rows) > 1 else None
    storyline = None
    try:
        if latest["top_storyline_json"]:
            parsed = json.loads(latest["top_storyline_json"])
            if isinstance(parsed, list) and parsed:
                storyline = parsed[0]
            elif isinstance(parsed, dict):
                storyline = parsed
    except (json.JSONDecodeError, TypeError):
        pass
    mood_delta = None
    if prev is not None and latest["net_sentiment_score"] is not None \
       and prev["net_sentiment_score"] is not None:
        mood_delta = float(latest["net_sentiment_score"]) - float(prev["net_sentiment_score"])
    return {
        "has_data": True,
        "mood_value": _mood_display(latest["net_sentiment_score"]),
        "raw_sentiment": float(latest["net_sentiment_score"] or 0.0),
        "mood_delta": mood_delta,
        "trajectory": trajectory,
        "top_storyline": storyline,
        "confidence_tier": latest["confidence_floor"],
        "latest_week": int(latest["week"]),
        "volume": int(latest["mention_count"] or 0),
        "effective_n": fetch_team_effective_n(db, team_id),
    }


def fetch_team_effective_n(db, team_id: int) -> float:
    """Sum effective_n across cohorts for the team's most-recent week.

    Reads ``team_cohort_week`` (the new fan-intel pipeline output). Used by
    the Pulse module's floor rule: <30 → "Awaiting Signal", 30–100 →
    sample-growing badge, ≥100 → full render. Returns 0.0 when the team
    has no cohort rows.
    """
    row = db.query_one(
        """
        select sum(effective_n) as total_n
        from team_cohort_week
        where team_id = :tid
          and week = (
            select max(week) from team_cohort_week where team_id = :tid
          )
        """,
        {"tid": team_id},
    )
    if not row or row["total_n"] is None:
        return 0.0
    return float(row["total_n"])


def _mood_display(net_sentiment: float | None) -> int | None:
    """Map net_sentiment in [-1, 1] to a 0-100 'belief dial' integer."""
    if net_sentiment is None:
        return None
    return int(round((float(net_sentiment) + 1.0) * 50.0))


def fetch_divergence(db, team_id: int, season_year: int) -> float | None:
    row = db.query_one(
        """
        select divergence_score
        from team_cohort_divergence_week
        where team_id = :tid
        order by week desc
        limit 1
        """,
        {"tid": team_id},
    )
    if not row or row["divergence_score"] is None:
        return None
    return float(row["divergence_score"])


def fetch_last_sp_rating(db, team_id: int, season_year: int) -> dict[str, Any] | None:
    """Return the most recent power_ratings_weekly row for the team-season.

    Used by Pulse + hero metric tiles. Falls back to None if no power
    rating was ever computed for this team-season (e.g., off-season teams
    before ratings are generated).
    """
    row = db.query_one(
        """
        select p.week, p.power_rating, p.offense_rating, p.defense_rating
        from power_ratings_weekly p
        where p.team_id = :tid
          and p.season_year = :season
        order by p.week desc, p.power_rating_weekly_id desc
        limit 1
        """,
        {"tid": team_id, "season": season_year},
    )
    if not row:
        return None
    return {
        "week": int(row["week"]),
        "power_rating": float(row["power_rating"]),
        "offense": float(row["offense_rating"]),
        "defense": float(row["defense_rating"]),
    }


def fetch_chronicle_cards(
    db,
    team_id: int,
    season_year: int,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Read back the top-ranked, published Chronicle observations.

    Scoped to the six editorial stream types (anomaly / moment / flashpoint /
    echo / retroactive / player_arc). Other card_types live in
    team_chronicle_observations alongside these — e.g. rivalry_posture /
    rivalry_stakes / savant_echo emitted by separate sprint scripts — but
    those render in their own modules, not in The Chronicle feed.
    """
    rows = db.query_all(
        """
        select card_type, headline, body_md, source_attribution,
               stat_json, comparison_json, week
        from team_chronicle_observations
        where team_id = :tid
          and season_year = :season
          and is_published = 1
          and card_type in ('anomaly','moment','flashpoint','echo',
                            'retroactive','player_arc')
        order by coalesce(surfaced_rank, 999) asc, generated_at_utc desc
        limit :lim
        """,
        {"tid": team_id, "season": season_year, "lim": limit},
    )
    out = []
    for r in rows:
        out.append({
            "card_type": r["card_type"],
            "headline": r["headline"],
            "body_md": r["body_md"],
            "source": r["source_attribution"],
            "week": r["week"],
        })
    return out


def fetch_team_season_path(db, team_id: int) -> dict[str, dict[str, Any]] | None:
    """Read the latest floor/base/ceiling season-path projection set.

    Sourced from the deterministic team-preview truth layer
    (team_season_path_projection, Milestone A). Returns a dict keyed by scenario
    ('floor'/'base'/'ceiling') for the most recent (season_year, as_of_date)
    projection on file for this team, or None when none exist — in which case
    the renderer falls back to its heuristic band.

    The final_wins/final_losses here are *final-season-aware*: they include a
    conference title game and CFP rounds, so a ceiling can legitimately exceed
    the 12-game regular season.
    """
    if db is None:
        return None
    try:
        latest = db.query_one(
            "select season_year, as_of_date from team_season_path_projection "
            "where team_id = :tid order by season_year desc, as_of_date desc limit 1",
            {"tid": team_id},
        )
    except Exception:
        # Table absent (migrations not applied) — degrade gracefully.
        return None
    if not latest:
        return None
    rows = db.query_all(
        """
        select scenario, regular_season_wins, regular_season_losses,
               conference_title_game, conference_title_result, bowl_or_cfp_path,
               postseason_wins, postseason_losses, final_wins, final_losses,
               final_ties, path_label, rationale, confidence_band,
               season_year, as_of_date
        from team_season_path_projection
        where team_id = :tid and season_year = :sy and as_of_date = :ad
        """,
        {"tid": team_id, "sy": latest["season_year"], "ad": latest["as_of_date"]},
    )
    by_scenario = {r["scenario"]: dict(r) for r in rows}
    return by_scenario or None


def fetch_bowl_ledger_row(db, slug: str) -> dict[str, Any] | None:
    """Read the most-trustworthy all-time bowl-record ledger row for a slug.

    Sourced from team_bowl_record_ledger (Milestone A). A slug can have several
    source rows; prefer verified > single_source > conflict > missing. Returns
    None when the table is absent or no row exists — the renderer then falls
    back to an honestly-scoped recent-era record.
    """
    if db is None:
        return None
    try:
        rows = db.query_all(
            "select slug, wins, losses, ties, appearances, last_bowl_year, "
            "last_bowl_name, last_bowl_result, source_name, verification_status "
            "from team_bowl_record_ledger where slug = :slug",
            {"slug": slug},
        )
    except Exception:
        return None
    if not rows:
        return None
    trust = {"verified": 0, "single_source": 1, "conflict": 2, "missing": 3}
    return min(rows, key=lambda r: trust.get(r["verification_status"], 9))


def fetch_llm_chronicle_cards(
    db,
    slug: str,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Read LLM-generated Chronicle cards from chronicle_card_cache.

    These are the Mistral Nemo / Qwen3 generated narrative cards from the
    autonomous pipeline — flashpoint, echo, devil_card, player_arc, etc.
    Prefers is_lkg=1 cards first (fact-critic approved), then by
    season_year + week desc so the freshest content surfaces.

    Uses raw sqlite3 since db.query_all may not be available in all call sites.
    """
    import sqlite3 as _sqlite3
    import json as _json

    # The db object wraps sqlite3.Connection; reach through to it.
    # Supports both: raw sqlite3.Connection and the project's DB wrapper.
    try:
        # Project DB wrapper exposes .query_all(sql, params)
        rows = db.query_all(
            """
            SELECT card_type, card_content_json, word_count,
                   fact_critic_score, voice_critic_score,
                   season_year, week_number, is_lkg,
                   confidence_band, prompt_template_id
            FROM chronicle_card_cache
            WHERE slug = :slug
              AND word_count > 0
            ORDER BY is_lkg DESC, season_year DESC, week_number DESC
            LIMIT :lim
            """,
            {"slug": slug, "lim": limit},
        )
    except Exception:
        return []

    out = []
    seen_keys: set[str] = set()
    for r in rows:
        try:
            content = _json.loads(r["card_content_json"] or "{}")
        except Exception:
            content = {}
        body = content.get("body_text") or content.get("body_md") or ""
        headline = content.get("headline") or ""
        if not body:
            continue
        # Dedup: the same headline (or near-identical body opening) can appear
        # across regenerations / card types and rendered twice on the page.
        dedup_key = (headline.strip().lower() or body.strip()[:80].lower())
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        out.append({
            "card_type": r["card_type"] or "echo",
            "headline": headline,
            "body": body,
            "word_count": r["word_count"],
            "fact_critic_score": r["fact_critic_score"],
            "season_year": r["season_year"],
            "week_number": r["week_number"],
            "is_lkg": bool(r["is_lkg"]),
            "confidence_band": r["confidence_band"] or "medium",
            "prompt_template_id": r["prompt_template_id"] or "",
        })
    return out


def fetch_savant_rows(
    db,
    team_id: int,
    season_year: int,
    week: int = 0,
) -> list[dict[str, Any]]:
    """Savant card — pre-computed percentiles from team_savant_weekly.

    Rows are ordered offense → defense → special (per the Savant registry
    order); the renderer just iterates straight through. Returns [] if the
    loader hasn't run yet for this team-season.
    """
    rows = db.query_all(
        """
        select metric_key, metric_group, metric_label, is_inverted, raw_value,
               pct_vs_fbs, pct_vs_p4, pct_vs_conf, pct_vs_alltime,
               sample_size,
               peer_set_size_fbs, peer_set_size_p4,
               peer_set_size_conf, peer_set_size_alltime,
               generated_at_utc
        from team_savant_weekly
        where team_id = :tid and season_year = :s and week = :w
        """,
        {"tid": team_id, "s": season_year, "w": week},
    )
    from .savant_data_loader import SAVANT_METRICS
    order = {m.key: i for i, m in enumerate(SAVANT_METRICS)}
    rows.sort(key=lambda r: order.get(r["metric_key"], 999))
    return rows


def fetch_savant_narrative(
    db,
    team_id: int,
    season_year: int,
) -> str | None:
    """Narrative header sentence for the Savant card, generated Sonnet.

    Stored in team_season_narratives with variant='savant_narrative'.
    """
    row = db.query_one(
        """
        select body_md
        from team_season_narratives
        where team_id = :tid and season_year = :s
          and variant = 'savant_narrative'
          and is_published = 1
        order by generated_at_utc desc
        limit 1
        """,
        {"tid": team_id, "s": season_year},
    )
    return row["body_md"] if row else None


def fetch_season_arc(db, team_id: int) -> list[dict[str, Any]]:
    """Season Arc rows 2014+ for the CFPEraView card."""
    return db.query_all(
        """
        select season_year, wins, losses, ties, win_pct,
               ap_rank_final, sp_plus_final,
               cfp_flag, title_game_flag, title_won_flag,
               is_crisis, is_current,
               mood_score_avg, quality_score, brick_state,
               notes_json
        from team_season_arc
        where team_id = :tid
        order by season_year asc
        """,
        {"tid": team_id},
    )


def fetch_arc_narrative(db, team_id: int, variant: str) -> str | None:
    """Era thesis ('arc_thesis') or closing paragraph ('arc_closing')."""
    row = db.query_one(
        """
        select body_md
        from team_season_narratives
        where team_id = :tid and variant = :v and is_published = 1
        order by generated_at_utc desc
        limit 1
        """,
        {"tid": team_id, "v": variant},
    )
    return row["body_md"] if row else None


def fetch_rivalry_posture(
    db,
    team_id: int,
    season_year: int,
    opponent_slug: str,
) -> dict[str, Any] | None:
    """Posture label + representative quote for this team's rivalry vs opponent."""
    row = db.query_one(
        """
        select headline, body_md, comparison_json
        from team_chronicle_observations
        where team_id = :tid and season_year = :s
          and card_type = 'rivalry_posture'
          and headline like '%' || :opp || '%'
          and is_published = 1
        order by generated_at_utc desc
        limit 1
        """,
        {"tid": team_id, "s": season_year, "opp": opponent_slug.replace("-", " ")},
    )
    return dict(row) if row else None


def fetch_rivalry_stakes(
    db,
    team_id: int,
    season_year: int,
    opponent_slug: str,
) -> str | None:
    row = db.query_one(
        """
        select body_md
        from team_chronicle_observations
        where team_id = :tid and season_year = :s
          and card_type = 'rivalry_stakes'
          and headline like '%' || :opp || '%'
          and is_published = 1
        order by generated_at_utc desc
        limit 1
        """,
        {"tid": team_id, "s": season_year, "opp": opponent_slug.replace("-", " ")},
    )
    return row["body_md"] if row else None


def fetch_rivalry_quote(
    db,
    team_id: int,
    season_year: int,
    opponent_slug: str,
) -> dict[str, Any] | None:
    row = db.query_one(
        """
        select body_md, attribution
        from team_season_narratives
        where team_id = :tid and season_year = :s
          and variant = :variant
          and is_published = 1
        order by generated_at_utc desc
        limit 1
        """,
        {"tid": team_id, "s": season_year, "variant": f"rivalry_quote_{opponent_slug}"},
    )
    return dict(row) if row else None


def fetch_savant_echo(
    db,
    team_id: int,
    season_year: int,
) -> dict[str, Any] | None:
    """Echo callout — nearest-neighbor defensive profile across program history."""
    row = db.query_one(
        """
        select headline, body_md, stat_json, comparison_json, source_attribution
        from team_chronicle_observations
        where team_id = :tid and season_year = :s
          and card_type = 'savant_echo'
          and is_published = 1
        order by generated_at_utc desc
        limit 1
        """,
        {"tid": team_id, "s": season_year},
    )
    if not row:
        return None
    return dict(row)


def fetch_state_of_team(
    db,
    team_id: int,
    season_year: int,
    variant: str = "state_of_team",
) -> dict[str, Any] | None:
    row = db.query_one(
        """
        select title, body_md, attribution, week_context, model_id,
               generated_at_utc
        from team_season_narratives
        where team_id = :tid
          and season_year = :season
          and variant = :variant
          and is_published = 1
        order by generated_at_utc desc
        limit 1
        """,
        {"tid": team_id, "season": season_year, "variant": variant},
    )
    if not row:
        return None
    return {
        "title": row["title"],
        "body_md": row["body_md"],
        "attribution": row["attribution"],
        "week_context": row["week_context"],
        "model_id": row["model_id"],
        "generated_at_utc": row["generated_at_utc"],
    }
