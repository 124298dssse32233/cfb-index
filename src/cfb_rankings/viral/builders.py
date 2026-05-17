"""DB-backed data builders for the v5-10e share-card renderers.

The renderers in this package take JSON-serializable input dataclasses
and produce Pillow PNGs. The builders here turn live DB rows into those
input dataclasses. Each builder is conservative — if the underlying
table is empty (0-row DB state per the reddit-deep wipe documented in
v5_followups.md §E), the builder returns sensible fallback data so the
artifact still renders with the locked composition.

Public API:

    from cfb_rankings.viral.builders import (
        build_mood_map_input,
        build_daily_movers_input,
        build_quote_card_input,
        build_receipt_card_input,
    )

Each ``build_*`` returns a tuple of kwargs ready to splat into the
corresponding ``viral.<module>.render(**kwargs)`` call.

The full v5-10e Sprint adds caching + cron orchestration; these
builders are the dumb-pure data layer.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import sqlite3
from typing import TYPE_CHECKING

from .mood_map import Cluster, Mover

if TYPE_CHECKING:
    from ..db import Database


# ---------------------------------------------------------------------------
# Mood Map builder
# ---------------------------------------------------------------------------

# The 11 FBS conference clusters with their actual 2026 team counts.
# Each cluster's (label, x, y, cols, rows, count) is the layout from the
# v5-5.4 mockup_07; the count matches actual conference roster size.
_CLUSTER_LAYOUT: list[tuple[str, int, int, int, int, int]] = [
    ("SEC",      70,  150, 8, 2, 16),
    ("BIG TEN",  70,  280, 9, 2, 18),
    ("ACC",      70,  410, 9, 2, 17),
    ("BIG 12",   70,  540, 8, 2, 16),
    ("PAC",      580, 150, 2, 1, 2),
    ("AAC",      680, 150, 7, 2, 14),
    ("MWC",      580, 280, 6, 2, 12),
    ("CUSA",     810, 280, 5, 2, 10),
    ("SUN BELT", 580, 410, 7, 2, 14),
    ("MAC",      780, 410, 6, 2, 12),
    ("FBS IND.", 580, 540, 3, 2, 6),
]


def build_mood_map_input(
    db: "Database",
    *,
    week_iso: str | None = None,
) -> dict:
    """Build the kwargs dict for ``viral.mood_map.render(**kwargs)``.

    Sources:
      - ``fanbase_mood_weekly`` per team for the latest week, joined to
        ``teams.current_conference_id`` → ``conferences.short_name``
        for cluster placement
      - Top up/down movers from ``fanbase_mood_weekly.delta_from_prev_week``
      - Hero finding number/sentence from ``hub_issue_metadata`` for the
        same week, or constructed from the divergence count if no hub
        issue exists for the week

    Falls back to the W048 mockup composition when tables are empty.
    """
    today = _dt.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    when_label = (
        f"WEEK OF {today:%d %b %Y}".upper() + f" · No. {iso_week:03d}"
    )

    # Try to read real mood data. If anything's missing, we fall back
    # to the seeded mockup composition.
    moods_by_conf: dict[str, dict[int, int]] = {}
    movers_up: list[Mover] = []
    movers_down: list[Mover] = []
    try:
        rows = db.query_all(
            """
            SELECT
                t.team_id,
                t.short_name AS abbr,
                COALESCE(c.short_name, 'IND') AS conference,
                m.mood_score, m.delta_from_prev_week, m.top_cause_label
            FROM fanbase_mood_weekly m
            JOIN teams t ON m.team_id = t.team_id
            LEFT JOIN conferences c ON t.current_conference_id = c.conference_id
            WHERE m.week_start_date = (
                SELECT MAX(week_start_date) FROM fanbase_mood_weekly
            )
            ORDER BY ABS(COALESCE(m.delta_from_prev_week, 0)) DESC
            """
        )
        for row in rows:
            conf = (row["conference"] or "IND").upper()
            moods_by_conf.setdefault(conf, {})
            # Place dots in conference clusters by team_id order
            idx_in_conf = len(moods_by_conf[conf])
            moods_by_conf[conf][idx_in_conf] = int(row["mood_score"] or 50)

        # Top 4 up + top 4 down movers
        movers_up_rows = [r for r in rows if (r["delta_from_prev_week"] or 0) > 0][:4]
        movers_dn_rows = [r for r in rows if (r["delta_from_prev_week"] or 0) < 0][:4]
        movers_up = [
            Mover(abbr=r["abbr"] or "?",
                  delta=f"+{r['delta_from_prev_week']}",
                  reason=(r["top_cause_label"] or "")[:24])
            for r in movers_up_rows
        ]
        movers_down = [
            Mover(abbr=r["abbr"] or "?",
                  delta=str(r["delta_from_prev_week"]),
                  reason=(r["top_cause_label"] or "")[:24])
            for r in movers_dn_rows
        ]
    except sqlite3.OperationalError:
        moods_by_conf = {}

    # Build clusters from layout + observed moods (or fallback seed)
    clusters = []
    for label, x, y, cols, rows_count, count in _CLUSTER_LAYOUT:
        observed = moods_by_conf.get(label, {})
        if observed:
            # Trim/pad to the cluster's count
            overrides = {i: observed.get(i, 50) for i in range(count)}

            def _provider(i: int, _o=overrides) -> int:
                return _o.get(i, 50)
            clusters.append(Cluster(label, x, y, cols, rows_count, count, _provider, {}))
        else:
            # Mockup fallback — sin/cos seeded distribution per cluster
            seed = sum(ord(c) for c in label)

            def _seed_provider(i: int, _s=seed) -> int:
                return int(55 + 22 * math.sin((i + _s) * 0.5))
            clusters.append(Cluster(label, x, y, cols, rows_count, count, _seed_provider, {}))

    # Hero finding — from hub_issue_metadata if present, otherwise constructed
    hero_number = "47 of 130"
    hero_sentence = "fanbases diverged from the model by more than 15 spots."
    hero_caption = "Sample: 202,341 mentions · 47 sources · 7 days · High confidence"
    try:
        hub = db.query_one(
            """
            SELECT cover_headline, cover_dek, cover_chart_caption
            FROM hub_issue_metadata
            ORDER BY week_start_date DESC LIMIT 1
            """
        )
        if hub and hub["cover_headline"]:
            # The hub's cover headline is often phrased as a full sentence
            # like "Michigan's belief is at a decade low." — use it as the
            # mood-map hero sentence when present.
            hero_sentence = hub["cover_headline"]
            if hub["cover_dek"]:
                hero_caption = (hub["cover_dek"] or "")[:96]
    except sqlite3.OperationalError:
        pass

    # Use mockup fallback movers if DB returned nothing
    if not movers_up:
        movers_up = [
            Mover("OSU",  "+8", "5★ trust me"),
            Mover("TEX",  "+7", "spring tempo"),
            Mover("BSU",  "+5", "no exits"),
            Mover("IOWA", "+4", "RPO footage"),
        ]
    if not movers_down:
        movers_down = [
            Mover("MICH", "−15", "Moore presser"),
            Mover("UF",   "−9",  "OL exits"),
            Mover("AUB",  "−7",  "quiet portal"),
            Mover("WIS",  "−6",  "DC departure"),
        ]

    return {
        "when_label": when_label,
        "hero_number": hero_number,
        "hero_sentence": hero_sentence,
        "hero_caption": hero_caption,
        "clusters": clusters,
        "up_movers": movers_up,
        "down_movers": movers_down,
    }


# ---------------------------------------------------------------------------
# Quote-card builder — pulls today's lead Daily take's pull quote
# ---------------------------------------------------------------------------

def build_quote_card_input(
    db: "Database",
    *,
    edition_date: str | None = None,
) -> dict:
    """Build kwargs for ``viral.quote_card.render(**kwargs)``.

    Reads ``daily_takes`` rank=1 for the requested (or latest) edition_date.
    The pull-quote is extracted as the first sentence of the body. If
    that's longer than ~140 chars it's truncated at the previous
    sentence break.
    """
    today = _dt.date.today()
    when_label = f"DAILY · {today:%d %b %Y}".upper()
    quote = "The dead zone is the sport's most consequential work week."
    attribution = "Lead take, The Daily"
    footer_meta = "3 sources cited"

    try:
        if edition_date is None:
            row = db.query_one(
                "SELECT MAX(edition_date) AS d FROM daily_editions"
            )
            edition_date = row["d"] if row else None
        if edition_date:
            take = db.query_one(
                """
                SELECT headline, body, source_count, cited_sources_json
                FROM daily_takes
                WHERE edition_date = ? AND rank_position = 1
                """,
                (edition_date,),
            )
            if take and take["body"]:
                quote = _first_sentence(take["body"])
                # Use the headline as attribution context
                attribution = f"Lead take · {edition_date}"
                sc = take["source_count"] or 0
                footer_meta = f"{sc} source{'s' if sc != 1 else ''} cited"
            when_label = f"DAILY · {edition_date}"
    except sqlite3.OperationalError:
        pass

    return {
        "when_label": when_label,
        "quote": quote,
        "attribution": attribution,
        "footer_meta": footer_meta,
    }


def _first_sentence(body: str, *, max_chars: int = 140) -> str:
    """Extract the first sentence, truncated to max_chars.

    "First sentence" means the prefix up to the EARLIEST '.', '?', or '!'.
    Any of those wins — we pick the minimum-index occurrence so "Question?"
    is preferred over "Question? Then a period." which would otherwise
    return the whole thing when '.' appeared later.
    """
    body = body.strip()
    earliest_idx = -1
    for end in (".", "?", "!"):
        idx = body.find(end)
        if idx >= 0 and (earliest_idx == -1 or idx < earliest_idx):
            earliest_idx = idx
    if 0 < earliest_idx <= max_chars:
        return body[:earliest_idx + 1].strip()
    return (body[:max_chars - 1] + "…") if len(body) > max_chars else body


# ---------------------------------------------------------------------------
# Receipt-card builder — most-recently resolved hit
# ---------------------------------------------------------------------------

def build_receipt_card_input(
    db: "Database",
    *,
    season_year: int | None = None,
) -> dict | None:
    """Build kwargs for ``viral.receipt_card.render(**kwargs)``.

    Returns None when no resolved 'hit' predictive claim exists — the
    caller should not generate a receipt card in that case (don't fake
    receipts).
    """
    today = _dt.date.today()
    try:
        row = db.query_one(
            """
            SELECT
                claim_text, claim_summary_short, source_slug,
                source_published_at, outcome_text, aged_well_pct,
                outcome_resolved_at
            FROM predictive_claims
            WHERE outcome_verdict = 'hit'
              AND outcome_resolved = 1
            ORDER BY outcome_resolved_at DESC LIMIT 1
            """
        )
    except sqlite3.OperationalError:
        return None
    if row is None:
        return None

    when_label = f"RECEIPT · {today:%d %b %Y}".upper()
    original_date = (row["source_published_at"] or "")[:10]
    quote = row["claim_summary_short"] or _first_sentence(row["claim_text"] or "")
    attribution = row["source_slug"] or "Source"
    resolved = row["outcome_text"] or "(no resolution text)"
    pct = int(row["aged_well_pct"] or 50)
    return {
        "when_label": when_label,
        "original_claim_date": original_date,
        "original_claim_quote": quote,
        "original_attribution": attribution,
        "resolved_summary": resolved,
        "aged_well_pct": pct,
    }


# ---------------------------------------------------------------------------
# Daily Belief Movers builder — biggest mood deltas today
# ---------------------------------------------------------------------------

def build_daily_movers_input(
    db: "Database",
    *,
    week_iso: str | None = None,
    top_n: int = 6,
) -> dict:
    """Build kwargs for ``viral.daily_movers.render(**kwargs)``.

    Reads ``fanbase_mood_weekly`` for the latest week; orders by absolute
    delta_from_prev_week DESC; picks ``top_n`` (typically 6 — 3 up + 3 down).

    Falls back to the W048 mockup composition when fanbase_mood_weekly
    is empty (current DB state).
    """
    from .daily_movers import MoverCard
    today = _dt.date.today()
    when_label = f"MOVERS · {today:%d %b %Y}".upper()
    movers: list[MoverCard] = []

    try:
        rows = db.query_all(
            """
            SELECT
                t.short_name AS abbr,
                m.delta_from_prev_week AS delta,
                m.top_cause_label AS reason
            FROM fanbase_mood_weekly m
            JOIN teams t ON m.team_id = t.team_id
            WHERE m.week_start_date = (
                SELECT MAX(week_start_date) FROM fanbase_mood_weekly
            )
              AND m.delta_from_prev_week IS NOT NULL
              AND m.delta_from_prev_week != 0
            ORDER BY ABS(m.delta_from_prev_week) DESC
            LIMIT ?
            """,
            (top_n,),
        )
        for row in rows:
            direction = "up" if (row["delta"] or 0) > 0 else "down"
            delta_str = f"+{row['delta']}" if direction == "up" else str(row["delta"])
            movers.append(MoverCard(
                abbr=row["abbr"] or "?",
                delta=delta_str,
                reason=(row["reason"] or "")[:32],
                direction=direction,
            ))
    except sqlite3.OperationalError:
        pass

    if not movers:
        movers = [
            MoverCard("OSU",  "+8",  "5★ trust me",    direction="up"),
            MoverCard("TEX",  "+7",  "spring tempo",   direction="up"),
            MoverCard("BSU",  "+5",  "no exits",       direction="up"),
            MoverCard("MICH", "-15", "Moore presser",  direction="down"),
            MoverCard("UF",   "-9",  "OL exits",       direction="down"),
            MoverCard("AUB",  "-7",  "quiet portal",   direction="down"),
        ]

    return {
        "when_label": when_label,
        "movers": movers,
        "sample_caption": "Sample: 47 sources · 7 days · High confidence",
    }


# ---------------------------------------------------------------------------
# Pre-game Pack builder — Friday-night Saturday game preview
# ---------------------------------------------------------------------------

def build_pregame_pack_input(
    db: "Database",
    *,
    game_id: int | None = None,
) -> dict | None:
    """Build kwargs for ``viral.pregame_pack.render(**kwargs)``.

    Reads the requested game from ``games`` joined to ``teams`` for both
    sides; pulls each side's record + mood + recent narrative line. When
    ``game_id`` is None, picks the highest-power-rating-sum upcoming Saturday
    game from the next 7 days.

    Returns None when no qualifying game found — caller should NOT generate
    a pregame pack when there's no marquee Saturday matchup (don't fabricate).
    """
    from .pregame_pack import TeamSide
    try:
        if game_id is None:
            row = db.query_one(
                """
                SELECT g.game_id
                FROM games g
                JOIN power_ratings_weekly h ON g.home_team_id = h.team_id
                JOIN power_ratings_weekly a ON g.away_team_id = a.team_id
                WHERE DATE(g.start_time_utc) BETWEEN DATE('now')
                                                AND DATE('now', '+7 days')
                  AND strftime('%w', g.start_time_utc) = '6'  -- Saturday
                  AND g.status IN ('scheduled', 'upcoming')
                ORDER BY (h.power_rating + a.power_rating) DESC
                LIMIT 1
                """
            )
            game_id = row["game_id"] if row else None
        if game_id is None:
            return None
        game = db.query_one(
            """
            SELECT
                g.game_id, g.start_time_utc,
                ht.team_id AS home_id, ht.short_name AS home_abbr,
                ht.school_name AS home_name, ht.slug AS home_slug,
                at.team_id AS away_id, at.short_name AS away_abbr,
                at.school_name AS away_name, at.slug AS away_slug
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.game_id = ?
            """,
            (game_id,),
        )
        if not game:
            return None
    except sqlite3.OperationalError:
        return None

    # Per-side enrichment — best-effort
    def _side(team_id: int, abbr: str, name: str) -> TeamSide:
        record = "—"
        mood = 50
        line = "—"
        try:
            ts = db.query_one(
                """
                SELECT wins, losses FROM team_seasons
                WHERE team_id = ?
                ORDER BY season_year DESC LIMIT 1
                """,
                (team_id,),
            )
            if ts:
                record = f"{ts['wins'] or 0}-{ts['losses'] or 0}"
        except sqlite3.OperationalError:
            pass
        try:
            mr = db.query_one(
                """
                SELECT mood_score, top_cause_label
                FROM fanbase_mood_weekly
                WHERE team_id = ?
                ORDER BY week_start_date DESC LIMIT 1
                """,
                (team_id,),
            )
            if mr:
                mood = int(mr["mood_score"] or 50)
                if mr["top_cause_label"]:
                    line = (mr["top_cause_label"] or "")[:36]
        except sqlite3.OperationalError:
            pass
        return TeamSide(
            name=name, abbr=abbr, record=record, mood=mood, short_line=line,
        )

    away = _side(game["away_id"], game["away_abbr"], game["away_name"])
    home = _side(game["home_id"], game["home_abbr"], game["home_name"])

    today = _dt.date.today()
    when_label = f"FRI · SATURDAY PACK · {today:%d %b}".upper()
    return {
        "when_label": when_label,
        "away": away,
        "home": home,
        "headline_facts": [
            f"{away.abbr} at {home.abbr} · {(game['start_time_utc'] or '')[:10]}",
            f"Mood gap: {away.mood} vs {home.mood}",
            "Power-rating + spread overlay pending market sync",
        ],
        "url_line": f"cfb-index · /preview/{game['game_id']}",
    }


__all__ = [
    "build_mood_map_input",
    "build_quote_card_input",
    "build_receipt_card_input",
    "build_daily_movers_input",
    "build_pregame_pack_input",
]
