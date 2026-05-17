"""Hero-finding generators per page archetype.

The API surface is locked so Window A's renderer work (v5-7) can call
into these generators with a stable signature. Bodies fill in
incrementally as upstream data arrives:

* generate_hub_finding         — IMPLEMENTED 2026-05-17 (cohort divergence aggregator)
* generate_daily_finding       — IMPLEMENTED (reads daily_takes)
* generate_heisman_finding     — IMPLEMENTED 2026-05-17 (PR #102 wrote 2025 data)
* generate_team_finding        — IMPLEMENTED 2026-05-17

Picker algorithm (when the full implementation lands at the renderer call site):

    candidate findings = [
        cohort_divergence(...),
        race_shift(...),
        anniversary_anchor(...),
        belief_delta(...),     # team finding
        edition_lead(...),     # editorial pulled-forward
        fallback_avg_mood(...) # always-available
    ]
    winner = max(candidates, key=lambda f: (f.confidence_rank, f.sort_priority))
    return winner

Each generator MUST be safe to call with empty/0-row data — it returns
None and the caller falls through to the next candidate.

The fallback_avg_mood is always-available (renders something every day)
so a page archetype that requires a hero finding NEVER has none.
"""

from __future__ import annotations

import logging as _log
import sqlite3
from typing import TYPE_CHECKING

from .types import FindingKind, HeroFinding

if TYPE_CHECKING:
    from ..db import Database

log = _log.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hub generator
# ---------------------------------------------------------------------------

def generate_hub_finding(
    db: "Database",
    *,
    season_year: int | None = None,
    week_iso: str | None = None,
    min_cohorts: int = 3,
) -> HeroFinding | None:
    """Hub archetype hero finding — most-divergent fanbase this week.

    Reads ``team_cohort_divergence_week`` for the latest week (or the
    week passed in ``week_iso`` if specified), finds the team with the
    highest cross-cohort divergence_score, packages as a
    COHORT_DIVERGENCE finding. High divergence = fragmented fanbase =
    story (per cohorts/divergence.py docstring).

    Suppression rules (returns None):
      * db is None (defensive)
      * Table doesn't exist (OperationalError)
      * No rows for the target week
      * Top divergence_score is NULL or zero
      * num_cohorts_qualifying < ``min_cohorts`` (default 3) — we don't
        want a "story" built on 2 cohorts disagreeing

    The picker score is calibrated against other hub candidates:
    confidence_rank=75 when num_cohorts_qualifying >= 4 (strong),
    confidence_rank=55 when 3 (passable).
    """
    if db is None:
        return None
    try:
        if week_iso:
            target_week = week_iso
        else:
            row = db.query_one(
                """
                SELECT week FROM team_cohort_divergence_week
                WHERE divergence_score IS NOT NULL
                ORDER BY week DESC LIMIT 1
                """,
            )
            if not row:
                return None
            target_week = row["week"]

        top = db.query_one(
            """
            SELECT d.team_id, d.divergence_score, d.num_cohorts_qualifying,
                   t.short_name, t.canonical_name, t.slug
            FROM team_cohort_divergence_week d
            JOIN teams t ON t.team_id = d.team_id
            WHERE d.week = ?
              AND d.divergence_score IS NOT NULL
              AND d.num_cohorts_qualifying >= ?
            ORDER BY d.divergence_score DESC, d.num_cohorts_qualifying DESC
            LIMIT 1
            """,
            (target_week, min_cohorts),
        )
    except sqlite3.OperationalError:
        return None
    if not top:
        return None
    score = top["divergence_score"]
    if score is None or float(score) <= 0:
        return None

    num_cohorts = int(top["num_cohorts_qualifying"] or 0)
    team_name = top["short_name"] or top["canonical_name"] or top["slug"] or "A fanbase"
    # The "number" is the count of qualifying cohorts disagreeing —
    # makes the receipt concrete ("5 cohorts" rather than abstract σ=0.83).
    number_str = str(num_cohorts)
    # Tier the editorial framing by sharpness of the disagreement.
    score_pts = float(score)
    if score_pts >= 1.0:
        intensity_word = "fractured"
    elif score_pts >= 0.5:
        intensity_word = "split"
    else:
        intensity_word = "diverged"
    sentence = (
        f"{team_name}'s fanbase {intensity_word} this week — "
        f"<em>{num_cohorts} cohorts</em> disagreed sharply on the program's direction."
    )
    return HeroFinding(
        kind=FindingKind.COHORT_DIVERGENCE,
        number=number_str,
        sentence=sentence,
        sample_caption=(
            f"Sample: {num_cohorts} cohort{'s' if num_cohorts != 1 else ''} · "
            f"week of {target_week[:10]}"
        ),
        sample_size=num_cohorts,
        confidence_domain="fan_intel",
        confidence_rank=75 if num_cohorts >= 4 else 55,
        sort_priority=45,
        extras={
            "team_id": int(top["team_id"]),
            "team_slug": top["slug"] or None,
            "season_year": season_year,
            "week_iso": target_week,
            "divergence_score": score_pts,
        },
    )


# ---------------------------------------------------------------------------
# Daily generator
# ---------------------------------------------------------------------------

def generate_daily_finding(
    db: "Database",
    *,
    edition_date: str,
) -> HeroFinding | None:
    """Daily archetype hero finding.

    The Daily's hero finding is the LEAD CLAIM from the day's #1 take,
    pulled forward into the hero. Reads the rank=1 row from
    ``daily_takes`` for the date, extracts the lead sentence + the source
    count, and packages as a HeroFinding.

    Returns None when:
    * db is None (defensive)
    * The edition_date doesn't exist in daily_takes
    * The lead take has no body
    """
    if db is None:
        return None
    try:
        take = db.query_one(
            """
            SELECT headline, body, source_count, primary_entity_slug
            FROM daily_takes
            WHERE edition_date = ? AND rank_position = 1
            """,
            (edition_date,),
        )
    except sqlite3.OperationalError:
        return None
    if not take or not take["body"]:
        return None

    body = take["body"].strip()
    # First sentence of the body becomes the hero sentence
    for end in (". ", "? ", "! "):
        idx = body.find(end)
        if 0 < idx <= 160:
            sentence = body[:idx + 1].strip()
            break
    else:
        sentence = body[:160].rsplit(" ", 1)[0] + "…" if len(body) > 160 else body

    source_count = take["source_count"] or 0
    # Hero "number" is the count of sources backing the take. The headline
    # carries the editorial framing; the number gives the receipts.
    number_str = str(source_count) if source_count else "0"
    # Confidence-chip label is the SOURCE COUNT, not the fan_intel sample
    # band. Override the chip text accordingly — preserves the
    # editorial-honesty rule (band still color-coded) while reading
    # naturally on the daily archetype.
    if source_count >= 3:
        chip_label = f"{source_count} sources cited"
    elif source_count == 2:
        chip_label = "2 sources cited"
    elif source_count == 1:
        chip_label = "1 source cited"
    else:
        chip_label = "No sources cited"
    return HeroFinding(
        kind=FindingKind.LEAD_CLAIM,
        number=number_str,
        sentence=sentence,
        sample_caption=f"Lead take · {edition_date}",
        sample_size=max(source_count, 4),  # lift above fan_intel UNSET floor;
                                            # the chip label overrides anyway
        confidence_domain="fan_intel",
        confidence_override_label=chip_label,
        confidence_rank=70,
        sort_priority=30,
        extras={
            "edition_date": edition_date,
            "primary_entity_slug": take["primary_entity_slug"] or None,
            "actual_source_count": source_count,
        },
    )


# ---------------------------------------------------------------------------
# Heisman generator
# ---------------------------------------------------------------------------

def generate_heisman_finding(
    db: "Database",
    *,
    season_year: int,
    week: int | None = None,
) -> HeroFinding | None:
    """Heisman Lens hero finding — biggest weekly market mover.

    Reads ``heisman_market_odds_weekly`` for the latest week + prior week,
    computes the largest absolute delta in market_implied_probability,
    packages as a RACE_SHIFT finding. Falls back to None when the table
    is empty, or when there's only one week of data (no prior to delta
    against), or when no candidate clears a 4-week sample threshold.

    Data note (2026-05-17): Window A's PR #102 fixed the Heisman model's
    week-fallback so the world_class_enrich workflow now writes 15,601
    rows to heisman_rankings_weekly for season 2025. Market odds also
    populate when the betting-line ingest runs against Kalshi/PolyMarket.
    """
    if db is None:
        return None
    try:
        # Find the latest and previous week with market data
        weeks = db.query_all(
            """
            SELECT DISTINCT week FROM heisman_market_odds_weekly
            WHERE season_year = ?
            ORDER BY week DESC LIMIT 2
            """,
            (season_year,),
        )
    except sqlite3.OperationalError:
        return None
    if len(weeks) < 2:
        return None
    latest_week = weeks[0]["week"]
    prior_week = weeks[1]["week"]

    # Find the largest absolute weekly delta
    try:
        rows = db.query_all(
            """
            SELECT
                latest.player_id,
                latest.player_name,
                latest.team_name,
                latest.implied_probability AS latest_pct,
                prior.implied_probability AS prior_pct
            FROM heisman_market_odds_weekly AS latest
            JOIN heisman_market_odds_weekly AS prior
              ON latest.player_id = prior.player_id
             AND latest.season_year = prior.season_year
             AND latest.provider = prior.provider
            WHERE latest.season_year = ?
              AND latest.week = ?
              AND prior.week = ?
              AND latest.implied_probability IS NOT NULL
              AND prior.implied_probability IS NOT NULL
            """,
            (season_year, latest_week, prior_week),
        )
    except sqlite3.OperationalError:
        return None
    if not rows:
        return None
    # Aggregate per player (multiple sportsbooks per player) — use median
    by_player: dict[int, list[tuple[str, str, float, float]]] = {}
    for r in rows:
        pid = r["player_id"]
        by_player.setdefault(pid, []).append((
            r["player_name"] or "",
            r["team_name"] or "",
            float(r["latest_pct"] or 0),
            float(r["prior_pct"] or 0),
        ))
    scored = []
    for pid, books in by_player.items():
        if len(books) < 2:
            continue  # need ≥2 books for a confident shift
        # Median latest/prior across books, then delta
        latest_med = sorted(b[2] for b in books)[len(books) // 2]
        prior_med = sorted(b[3] for b in books)[len(books) // 2]
        delta = latest_med - prior_med
        scored.append((abs(delta), delta, books[0][0], books[0][1], len(books)))
    if not scored:
        return None
    scored.sort(reverse=True)
    _abs, delta, name, team, book_count = scored[0]

    # Convert prob delta (e.g. 0.18) to percentage-points (e.g. +18)
    delta_pts = int(round(delta * 100))
    if delta_pts == 0:
        return None
    sign = "+" if delta_pts > 0 else "−"
    number_str = f"{sign}{abs(delta_pts)}"
    direction_word = "tightened" if delta_pts > 0 else "drifted"
    sentence = (
        f"{name}'s market odds {direction_word} <em>{abs(delta_pts)} points</em> "
        f"against the prior week — the biggest preseason shift in the field."
    )
    return HeroFinding(
        kind=FindingKind.RACE_SHIFT,
        number=number_str,
        sentence=sentence,
        sample_caption=f"Sample: {book_count} sportsbook{'s' if book_count != 1 else ''} · 2 weeks",
        sample_size=book_count,
        confidence_domain="market",
        confidence_rank=85 if abs(delta_pts) >= 10 else 60,
        sort_priority=50,
        extras={
            "player_id": int(list(by_player.keys())[
                scored.index(scored[0])
            ]) if scored else 0,
            "team": team,
            "season_year": season_year,
            "week": latest_week,
        },
    )


# ---------------------------------------------------------------------------
# Team profile generator
# ---------------------------------------------------------------------------

def generate_team_finding(
    db: "Database",
    *,
    team_id: int,
    season_year: int,
    week_iso: str | None = None,
) -> HeroFinding | None:
    """Team Profile hero finding — this-week belief delta.

    Reads ``fanbase_mood_weekly`` for the team + most-recent prior week,
    computes the delta, packages as a BELIEF_DELTA finding. Empty data
    → None → renderer suppresses the hero-finding module (Profile
    archetype tolerates absence).

    Suppression rules:
    * Returns None when db is None (defensive)
    * Returns None when fanbase_mood_weekly is empty for this team
    * Returns None when only 1 week of data (no prior to delta against)
    * Returns None when |delta| < 3 — not worth the hero-real-estate
    * Returns None when team_id is unknown
    """
    if db is None:
        return None
    try:
        rows = db.query_all(
            """
            SELECT week_start_date, mood_score, delta_from_prev_week,
                   top_cause_label, sample_size, confidence
            FROM fanbase_mood_weekly
            WHERE team_id = ?
            ORDER BY week_start_date DESC
            LIMIT 2
            """,
            (team_id,),
        )
    except sqlite3.OperationalError:
        return None
    if not rows:
        return None
    latest = rows[0]
    delta = latest["delta_from_prev_week"]
    if delta is None or abs(delta) < 3:
        # Not a story — let other modules carry the page
        return None

    sample_size = latest["sample_size"] or 0
    cause = (latest["top_cause_label"] or "").strip()
    sign = "+" if delta > 0 else "−"
    delta_str = f"{sign}{abs(delta)}"
    if cause:
        # Preserve case — cause_label is editorial content and may
        # contain proper nouns ("Moore presser", "5-star trust me").
        sentence = (
            f"Belief moved <em>{sign}{abs(delta)} points</em> this week — "
            f"{cause}."
        )
    else:
        sentence = (
            f"Belief moved <em>{sign}{abs(delta)} points</em> this week."
        )
    return HeroFinding(
        kind=FindingKind.BELIEF_DELTA,
        number=delta_str,
        sentence=sentence,
        sample_caption=(
            f"Sample: {sample_size} mention{'s' if sample_size != 1 else ''} · "
            f"week of {(latest['week_start_date'] or '')[:10]}"
        ),
        sample_size=sample_size,
        confidence_domain="fan_intel",
        confidence_rank=80 if abs(delta) >= 10 else 60,
        sort_priority=40,
        extras={
            "team_id": team_id,
            "season_year": season_year,
            "week_iso": week_iso,
            "delta": delta,
        },
    )


__all__ = [
    "generate_hub_finding",
    "generate_daily_finding",
    "generate_heisman_finding",
    "generate_team_finding",
]
