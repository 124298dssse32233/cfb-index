"""Chronicle candidate-stream scanner — six proprietary data streams.

See docs/CHRONICLE_EDITORIAL_BRIEF.md and CLAUDE_CODE_CHRONICLE_REBUILD.md.

Each stream is a pure-Python function that reads the DB and emits
``CandidateObservation`` rows. A separate ranker picks the top-K, a writer
(LLM) turns them into editorial cards, and a validator (regex) gates output.

This module contains zero LLM calls. It is cheap, deterministic, and
testable. The LLM spend sits downstream in ``chronicle_generator.write_card``.

Streams (per brief §Stage 1):

    1. savant_stream           — percentile outliers + gamelog streaks/splits
    2. fanintel_stream         — cohort velocity spikes + divergence
    3. archive_stream          — historical-season record similarity
    4. rivalry_stream          — upcoming or most-recent Tier-1 rival meeting
    5. retroactive_stream      — prior-week Chronicle cards overturned by later events
    6. player_arc_stream       — player name-velocity + stat trajectories

Source citations follow brief §7. None of the strings assembled here may
include "CFB Index", "stat engine", "pipeline", "algorithm", or any other
self-referential scaffolding — the writer / validator will reject those.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from cfb_rankings.utils import ordinal_suffix as _ordinal


# --------------------------------------------------------------------------
# Candidate observation — what streams emit
# --------------------------------------------------------------------------

@dataclass
class CandidateObservation:
    suggested_type: str          # anomaly | moment | flashpoint | echo | retroactive | player_arc
    evidence: dict[str, Any]     # structured evidence supporting the card
    source_citation: str         # fan-readable attribution (brief §7)
    oddity_score: float          # 0-1, how unusual/noteworthy
    date_window: tuple[str, str] # (start_date, end_date) ISO strings, best-effort
    stream: str                  # which scanner found this
    notes: str = ""              # short free-text summary for the writer prompt


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

def scan_all_streams(
    conn: sqlite3.Connection,
    team_slug: str,
    season_year: int,
    week: int | None,
) -> list[CandidateObservation]:
    """Run all six streams for (team, season, week). Returns aggregate pool."""
    out: list[CandidateObservation] = []
    out.extend(savant_stream(conn, team_slug, season_year, week))
    out.extend(fanintel_stream(conn, team_slug, season_year, week))
    out.extend(archive_stream(conn, team_slug, season_year, week))
    out.extend(rivalry_stream(conn, team_slug, season_year, week))
    out.extend(retroactive_stream(conn, team_slug, season_year, week))
    out.extend(player_arc_stream(conn, team_slug, season_year, week))
    return out


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

def _team_row(conn: sqlite3.Connection, slug: str) -> dict[str, Any] | None:
    r = conn.execute(
        "select team_id, canonical_name, school_name, slug from teams where slug = ?",
        (slug,),
    ).fetchone()
    if not r:
        return None
    return {"team_id": int(r[0]), "canonical_name": r[1], "school_name": r[2], "slug": r[3]}


def _fetch_final_games(
    conn: sqlite3.Connection, team_id: int, season_year: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select g.season_year, g.week,
               g.home_team_id, g.away_team_id,
               g.home_points, g.away_points,
               substr(g.start_time_utc, 1, 10) as game_date,
               ht.canonical_name as home_name, ht.slug as home_slug,
               at.canonical_name as away_name, at.slug as away_slug,
               g.neutral_site
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where g.season_year = ?
          and (g.home_team_id = ? or g.away_team_id = ?)
          and g.status in ('Final','final','FINAL')
        order by coalesce(g.week, 0), coalesce(g.start_time_utc, '')
        """,
        (season_year, team_id, team_id),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for (sy, wk, hid, aid, hp, ap, gd, hname, hslug, aname, aslug, neutral) in rows:
        if hp is None or ap is None:
            continue
        is_home = int(hid) == team_id
        mine = int(hp) if is_home else int(ap)
        theirs = int(ap) if is_home else int(hp)
        outcome = "W" if mine > theirs else ("L" if mine < theirs else "T")
        out.append({
            "season_year": int(sy),
            "week": int(wk or 0),
            "is_home": is_home,
            "neutral_site": bool(neutral),
            "team_points": mine,
            "opp_points": theirs,
            "margin": mine - theirs,
            "outcome": outcome,
            "game_date": gd,
            "opponent_name": aname if is_home else hname,
            "opponent_slug": aslug if is_home else hslug,
        })
    return out


# --------------------------------------------------------------------------
# Stream 1 — Savant + gamelog anomaly scanner
# --------------------------------------------------------------------------

_SAVANT_ANOMALY_LABEL = {
    "epa_play":        "EPA per play",
    "success_off":     "Success rate",
    "explosive_off":   "Explosive play rate",
    "rushing_epa_off": "Rushing EPA",
    "passing_epa_off": "Passing EPA",
    "finishing_off":   "Red-zone finish",
    "epa_allowed":     "EPA per play allowed",
    "success_def":     "Success rate allowed",
    "explosive_def":   "Explosive plays allowed",
    "passing_epa_def": "Opponent passing EPA",
    "rushing_epa_def": "Opponent rushing EPA",
    "finishing_def":   "Red-zone defense",
    "field_pos_off":   "Average starting field position",
}


def savant_stream(
    conn: sqlite3.Connection, team_slug: str, season_year: int, week: int | None,
) -> list[CandidateObservation]:
    """Savant percentile outliers + gamelog streaks / splits."""
    team = _team_row(conn, team_slug)
    if not team:
        return []
    tid = team["team_id"]
    out: list[CandidateObservation] = []

    # 1a — Savant percentile outliers (≥95 or ≤5 on FBS or P4 peer set).
    # Savant data is keyed to the most recent season we have percentiles for;
    # pull that season's rows (usually 2024 in our DB, that's what renders on
    # the team's Savant card).
    sav_season_row = conn.execute(
        "select max(season_year) from team_savant_weekly where team_id = ?", (tid,),
    ).fetchone()
    sav_season = int(sav_season_row[0]) if sav_season_row and sav_season_row[0] else season_year
    sav_rows = conn.execute(
        """
        select metric_key, metric_label, raw_value,
               pct_vs_fbs, pct_vs_p4, pct_vs_conf, pct_vs_alltime,
               is_inverted, sample_size
        from team_savant_weekly
        where team_id = ? and season_year = ? and week = 0
        """,
        (tid, sav_season),
    ).fetchall()
    for (mk, mlabel, raw, pf, pp, pc, pa, inv, n) in sav_rows:
        # After inversion, high percentile = elite. The DB stores inverted-applied
        # percentiles, so we just test pf/pp directly.
        if pf is None:
            continue
        if pf >= 92 or pf <= 8:
            direction = "elite" if pf >= 92 else "sub-FBS-median"
            out.append(CandidateObservation(
                suggested_type="anomaly",
                evidence={
                    "metric_key": mk,
                    "metric_label": _SAVANT_ANOMALY_LABEL.get(mk, mlabel),
                    "pct_vs_fbs": round(pf, 1),
                    "pct_vs_p4": round(pp, 1) if pp is not None else None,
                    "pct_vs_alltime": round(pa, 1) if pa is not None else None,
                    "raw_value": round(raw, 3) if raw is not None else None,
                    "direction": direction,
                    "season_year": sav_season,
                    "sample_size": int(n) if n else None,
                },
                source_citation=f"Savant card · {sav_season} season through postseason",
                oddity_score=max(pf, 100 - pf) / 100.0,
                date_window=(f"{sav_season}-01-01", f"{sav_season}-12-31"),
                stream="savant",
                notes=(
                    f"{_SAVANT_ANOMALY_LABEL.get(mk, mlabel)} sits at the "
                    f"{int(round(pf))}{_ordinal(int(round(pf)))} percentile of FBS — {direction}."
                ),
            ))

    # 1b — Gamelog streak (W/L) of ≥4, current-season end-of-season view.
    games = _fetch_final_games(conn, tid, season_year)
    if len(games) >= 3:
        # Find longest closing streak (from end of season backward).
        closing_out = games[-1]["outcome"]
        closing_len = 0
        for g in reversed(games):
            if g["outcome"] == closing_out:
                closing_len += 1
            else:
                break
        if closing_len >= 4:
            streak_games = games[-closing_len:]
            word = "wins" if closing_out == "W" else "losses"
            margins = [g["margin"] for g in streak_games]
            out.append(CandidateObservation(
                suggested_type="anomaly",
                evidence={
                    "streak_length": closing_len,
                    "outcome": closing_out,
                    "word": word,
                    "margins": margins,
                    "opponents": [g["opponent_name"] for g in streak_games],
                    "weeks": [g["week"] for g in streak_games],
                    "closing": True,
                    "season_year": season_year,
                },
                source_citation=f"gamelog · {season_year} season through wk {games[-1]['week']}",
                oddity_score=min(1.0, 0.35 + 0.08 * closing_len),
                date_window=(streak_games[0]["game_date"] or "", streak_games[-1]["game_date"] or ""),
                stream="savant",
                notes=(
                    f"{closing_len} straight {word} closing {season_year}. "
                    f"Margins: {margins}. Opponents: {[g['opponent_name'] for g in streak_games]}."
                ),
            ))

        # Biggest swing: single game furthest from season-mean margin.
        if len(games) >= 5:
            mean_margin = sum(g["margin"] for g in games) / len(games)
            extreme = max(games, key=lambda g: abs(g["margin"] - mean_margin))
            dev = abs(extreme["margin"] - mean_margin)
            if dev >= 25:
                out.append(CandidateObservation(
                    suggested_type="moment" if extreme["outcome"] == "W" else "anomaly",
                    evidence={
                        "week": extreme["week"],
                        "opponent": extreme["opponent_name"],
                        "opponent_slug": extreme["opponent_slug"],
                        "margin": extreme["margin"],
                        "team_points": extreme["team_points"],
                        "opp_points": extreme["opp_points"],
                        "is_home": extreme["is_home"],
                        "game_date": extreme["game_date"],
                        "season_mean_margin": round(mean_margin, 1),
                        "deviation_from_mean": round(dev, 1),
                        "season_year": season_year,
                    },
                    source_citation=f"gamelog · {season_year} season · wk {extreme['week']}",
                    oddity_score=min(1.0, 0.5 + dev / 60.0),
                    date_window=(extreme["game_date"] or "", extreme["game_date"] or ""),
                    stream="savant",
                    notes=(
                        f"Wk {extreme['week']} {extreme['outcome']} "
                        f"{extreme['team_points']}-{extreme['opp_points']} vs "
                        f"{extreme['opponent_name']}, margin {extreme['margin']:+d} "
                        f"— {round(dev,1)} pts off the season mean."
                    ),
                ))

        # Baseline moment: biggest W of the season (always at least one moment
        # candidate, even for thin-signal teams like mid-G5 programs).
        wins = [g for g in games if g["outcome"] == "W"]
        if wins:
            biggest = max(wins, key=lambda g: g["margin"])
            # Avoid duplicating the "biggest swing" anomaly if they're the same game.
            already_emitted = any(
                c.stream == "savant" and c.suggested_type == "moment"
                and c.evidence.get("week") == biggest["week"]
                for c in out
            )
            if not already_emitted:
                loc = "at home" if biggest["is_home"] else "on the road"
                out.append(CandidateObservation(
                    suggested_type="moment",
                    evidence={
                        "week": biggest["week"],
                        "opponent": biggest["opponent_name"],
                        "opponent_slug": biggest["opponent_slug"],
                        "margin": biggest["margin"],
                        "team_points": biggest["team_points"],
                        "opp_points": biggest["opp_points"],
                        "is_home": biggest["is_home"],
                        "game_date": biggest["game_date"],
                        "kind": "season_biggest_win",
                        "season_year": season_year,
                    },
                    source_citation=f"gamelog · {season_year} season · wk {biggest['week']}",
                    oddity_score=min(0.80, 0.45 + biggest["margin"] / 100.0),
                    date_window=(biggest["game_date"] or "", biggest["game_date"] or ""),
                    stream="savant",
                    notes=(
                        f"Season-biggest win: wk {biggest['week']} "
                        f"{biggest['team_points']}-{biggest['opp_points']} "
                        f"{loc} vs {biggest['opponent_name']} "
                        f"(margin {biggest['margin']:+d})."
                    ),
                ))

        # Home/away split on margin (offseason view is the full season).
        home_games = [g for g in games if g["is_home"] and not g["neutral_site"]]
        away_games = [g for g in games if not g["is_home"] and not g["neutral_site"]]
        if len(home_games) >= 3 and len(away_games) >= 3:
            home_mean = sum(g["margin"] for g in home_games) / len(home_games)
            away_mean = sum(g["margin"] for g in away_games) / len(away_games)
            diff = home_mean - away_mean
            if abs(diff) >= 20:
                side = "home" if diff > 0 else "road"
                out.append(CandidateObservation(
                    suggested_type="anomaly",
                    evidence={
                        "home_mean_margin": round(home_mean, 1),
                        "away_mean_margin": round(away_mean, 1),
                        "diff": round(diff, 1),
                        "dominant_side": side,
                        "n_home": len(home_games),
                        "n_away": len(away_games),
                        "season_year": season_year,
                    },
                    source_citation=f"gamelog · {season_year} season",
                    oddity_score=min(1.0, 0.4 + abs(diff) / 80.0),
                    date_window=(f"{season_year}-08-01", f"{season_year}-12-31"),
                    stream="savant",
                    notes=(
                        f"Home margin mean {home_mean:+.1f} vs road margin mean "
                        f"{away_mean:+.1f} — a {abs(diff):.0f}-point split favoring {side}."
                    ),
                ))

    return out


# --------------------------------------------------------------------------
# Stream 2 — Fan-intel cohort conversation velocity
# --------------------------------------------------------------------------

def fanintel_stream(
    conn: sqlite3.Connection, team_slug: str, season_year: int, week: int | None,
) -> list[CandidateObservation]:
    """Cohort conversation velocity spikes + divergence events."""
    team = _team_row(conn, team_slug)
    if not team:
        return []
    tid = team["team_id"]
    out: list[CandidateObservation] = []

    # 2a — Look at the most recent 8 weeks of cohort data. Flag any week where
    # TOTAL effective_n across cohorts is ≥ 2× the median of the prior 4 weeks.
    # This approximates "conversation velocity spike".
    rows = conn.execute(
        """
        select week, sum(effective_n) as total_eff_n, sum(volume) as total_vol,
               max(confidence_tier) as conf
        from team_cohort_week
        where team_id = ?
        group by week
        order by week desc
        limit 12
        """,
        (tid,),
    ).fetchall()
    if len(rows) >= 5:
        # rows[0] is newest; compare to median of rows[1..4].
        weeks = [r[0] for r in rows]
        volumes = [float(r[1] or 0.0) for r in rows]
        recent = volumes[0]
        baseline_sample = sorted(volumes[1:5])
        baseline_median = baseline_sample[len(baseline_sample) // 2] if baseline_sample else 0.0
        if baseline_median > 1.0 and recent >= 2.0 * baseline_median:
            out.append(CandidateObservation(
                suggested_type="moment",
                evidence={
                    "week_key": weeks[0],
                    "recent_eff_n": round(recent, 1),
                    "baseline_eff_n_median": round(baseline_median, 1),
                    "velocity_multiple": round(recent / max(baseline_median, 0.01), 2),
                    "sample_cohorts_week": 12,
                    "season_year": season_year,
                },
                source_citation="conversation velocity · cohort aggregate",
                oddity_score=min(1.0, 0.5 + min(0.5, (recent / max(baseline_median, 0.01) - 2.0) / 4.0)),
                date_window=(f"{season_year}-01-01", f"{season_year}-12-31"),
                stream="fanintel",
                notes=(
                    f"Week {weeks[0]} conversation effective-n is {recent:.1f}, "
                    f"{round(recent/max(baseline_median,0.01),1)}× the prior 4-week median "
                    f"({baseline_median:.1f}). Fanbase is talking."
                ),
            ))

    # 2b — Cohort divergence event: max divergence week in the season.
    div_rows = conn.execute(
        """
        select week, divergence_score, num_cohorts_qualifying
        from team_cohort_divergence_week
        where team_id = ? and divergence_score is not null
        order by divergence_score desc
        limit 1
        """,
        (tid,),
    ).fetchall()
    if div_rows:
        wk, score, nq = div_rows[0]
        if score is not None and float(score) >= 0.15 and (nq or 0) >= 3:
            out.append(CandidateObservation(
                suggested_type="moment",
                evidence={
                    "week_key": wk,
                    "divergence_score": round(float(score), 3),
                    "num_cohorts_qualifying": int(nq or 0),
                    "season_year": season_year,
                },
                source_citation="cohort divergence · analytics vs casual",
                oddity_score=min(1.0, 0.4 + float(score)),
                date_window=(f"{season_year}-01-01", f"{season_year}-12-31"),
                stream="fanintel",
                notes=(
                    f"Week {wk} had the season's widest cohort divergence "
                    f"({score:.3f}) across {nq} qualifying cohorts — the fanbase was "
                    f"reading the same result differently."
                ),
            ))

    return out


# --------------------------------------------------------------------------
# Stream 3 — Historical-season archive echoes
# --------------------------------------------------------------------------

def archive_stream(
    conn: sqlite3.Connection, team_slug: str, season_year: int, week: int | None,
) -> list[CandidateObservation]:
    """Record-shape echoes from team_historical_seasons."""
    team = _team_row(conn, team_slug)
    if not team:
        return []
    tid = team["team_id"]
    out: list[CandidateObservation] = []

    # Current season (in-progress view)
    games = _fetch_final_games(conn, tid, season_year)
    cur_w = sum(1 for g in games if g["outcome"] == "W")
    cur_l = sum(1 for g in games if g["outcome"] == "L")

    # Historical rows for this program
    hist = conn.execute(
        """
        select season_year, season_title, season_thesis, legacy_paragraph,
               defining_moments_json, gap_year_flag
        from team_historical_seasons
        where team_slug = ?
        order by season_year
        """,
        (team_slug,),
    ).fetchall()
    if not hist:
        return out

    # For each historical season, compute shape distance to current.
    # Shape = (wins, losses) pair from the games table for that prior season.
    candidates: list[tuple[int, str, str, int, int, int]] = []
    for (hsy, title, thesis, legacy, dmj, gap) in hist:
        if int(hsy) == season_year:
            continue
        if gap:
            continue
        hg = _fetch_final_games(conn, tid, int(hsy))
        hw = sum(1 for g in hg if g["outcome"] == "W")
        hl = sum(1 for g in hg if g["outcome"] == "L")
        distance = abs(hw - cur_w) + abs(hl - cur_l)
        candidates.append((int(hsy), title or "", thesis or "", hw, hl, distance))

    # Sort by closest shape; keep top 2.
    candidates.sort(key=lambda c: (c[5], -c[0]))
    for (hsy, title, thesis, hw, hl, dist) in candidates[:2]:
        if dist > 4:
            continue  # Not a real echo
        out.append(CandidateObservation(
            suggested_type="echo",
            evidence={
                "echo_season_year": hsy,
                "echo_title": title,
                "echo_thesis": thesis[:300] if thesis else "",
                "echo_record": f"{hw}-{hl}",
                "current_record": f"{cur_w}-{cur_l}",
                "record_distance": dist,
                "current_season_year": season_year,
            },
            source_citation=f"from the {hsy} season archive",
            oddity_score=max(0.35, 0.9 - 0.15 * dist),
            date_window=(f"{hsy}-01-01", f"{hsy}-12-31"),
            stream="archive",
            notes=(
                f"{season_year} shape ({cur_w}-{cur_l}) echoes {hsy} "
                f"({hw}-{hl}, '{title}'). Thesis: {thesis[:180] if thesis else ''}"
            ),
        ))

    return out


# --------------------------------------------------------------------------
# Stream 4 — Rivalry flashpoint
# --------------------------------------------------------------------------

def rivalry_stream(
    conn: sqlite3.Connection, team_slug: str, season_year: int, week: int | None,
) -> list[CandidateObservation]:
    """Most-recent Tier-1 rivalry meeting (offseason) or upcoming (in-season)."""
    team = _team_row(conn, team_slug)
    if not team:
        return []
    out: list[CandidateObservation] = []

    # Load this team's profile to get Tier-1 rivalries (authoritative list).
    from .profile_loader import load_profile
    try:
        profile = load_profile(team_slug)
    except FileNotFoundError:
        return out

    tier1 = [r for r in profile.rivalries if int(r.get("tier", 9)) == 1]
    if not tier1:
        tier1 = profile.rivalries[:2]

    # For each Tier-1 rival, pull the most recent meeting.
    for rival in tier1[:3]:
        opp_slug = rival.get("opponent_slug")
        if not opp_slug:
            continue
        row = conn.execute(
            """
            select season_year, week, game_date, winner_slug,
                   program_a_slug, program_b_slug, a_points, b_points, margin, venue
            from team_rivalry_meetings
            where ((program_a_slug = ? and program_b_slug = ?)
                or (program_a_slug = ? and program_b_slug = ?))
              and is_complete = 1
            order by season_year desc, coalesce(week, 0) desc
            limit 1
            """,
            (team_slug, opp_slug, opp_slug, team_slug),
        ).fetchone()
        if not row:
            continue
        (rsy, rwk, rdate, winner_slug, pa, pb, ap, bp, margin, venue) = row
        team_won = (winner_slug == team_slug)
        # Pull last 3 meetings to give the writer a streak context.
        last3 = conn.execute(
            """
            select season_year, winner_slug, a_points, b_points, margin
            from team_rivalry_meetings
            where ((program_a_slug = ? and program_b_slug = ?)
                or (program_a_slug = ? and program_b_slug = ?))
              and is_complete = 1
            order by season_year desc limit 3
            """,
            (team_slug, opp_slug, opp_slug, team_slug),
        ).fetchall()
        streak = 0
        for (_, w, _a, _b, _m) in last3:
            if w == team_slug:
                streak += 1
            else:
                break
        trophy = rival.get("trophy") or rival.get("name") or f"{team_slug} vs {opp_slug}"
        out.append(CandidateObservation(
            suggested_type="flashpoint",
            evidence={
                "opponent_slug": opp_slug,
                "trophy": trophy,
                "most_recent_season": int(rsy) if rsy else None,
                "most_recent_result": (
                    f"W {ap}-{bp}" if (team_won and pa == team_slug)
                    else (f"W {bp}-{ap}" if team_won and pb == team_slug
                          else (f"L {ap}-{bp}" if pa == team_slug
                                else f"L {bp}-{ap}"))
                ),
                "streak_length_team_side": streak,
                "last3_summary": [
                    {"season": s, "winner": w, "margin": m}
                    for (s, w, a, b, m) in last3
                ],
                "season_year": season_year,
                "venue": venue,
            },
            source_citation=f"from the {trophy} archive · last met {rsy}",
            oddity_score=0.55 + min(0.35, 0.07 * streak),
            date_window=(f"{rsy}-01-01" if rsy else f"{season_year}-01-01",
                         f"{rsy}-12-31" if rsy else f"{season_year}-12-31"),
            stream="rivalry",
            notes=(
                f"Last meeting vs {opp_slug}: {rsy}. "
                f"{'Team on a '+str(streak)+'-game win streak in series' if streak>=2 else ''}"
            ),
        ))
    return out


# --------------------------------------------------------------------------
# Stream 5 — Retroactive reframing
# --------------------------------------------------------------------------

def retroactive_stream(
    conn: sqlite3.Connection, team_slug: str, season_year: int, week: int | None,
) -> list[CandidateObservation]:
    """Prior-week Chronicle cards whose framing the final record has overturned."""
    team = _team_row(conn, team_slug)
    if not team:
        return []
    tid = team["team_id"]
    out: list[CandidateObservation] = []

    # Final record — we can only reframe if we have enough games to judge.
    games = _fetch_final_games(conn, tid, season_year)
    if len(games) < 6:
        return out
    final_w = sum(1 for g in games if g["outcome"] == "W")
    final_l = sum(1 for g in games if g["outcome"] == "L")

    # Look for early-season (wk ≤ 6) anomaly/moment cards that read as
    # "disaster" framings, where the season ended up respectable. Or vice
    # versa. We key off surprise_score and card_type for now.
    rows = conn.execute(
        """
        select week, card_type, headline, body_md, source_attribution,
               surprise_score, generated_at_utc
        from team_chronicle_observations
        where team_id = ? and season_year = ? and is_published = 1
          and card_type in ('anomaly', 'moment')
          and week is not null and week between 1 and 6
        order by week asc, surfaced_rank asc
        """,
        (tid, season_year),
    ).fetchall()
    for (wk, ct, hl, body, src, sc, gen_at) in rows:
        # Consider "reframe" if the team ended the season with ≥8 wins and
        # the early card's headline/body used disaster / questioning language;
        # OR if team ended with ≤5 wins and early card was a celebration.
        is_disaster_frame = any(t in (hl + " " + (body or "")).lower()
                                for t in ["loss", "collapse", "concern", "problem",
                                          "worst", "question", "slow start", "trouble"])
        is_celebration_frame = any(t in (hl + " " + (body or "")).lower()
                                   for t in ["breakthrough", "statement", "peak",
                                             "best", "mood-peak", "signature"])
        reframe_dir = None
        if final_w >= 8 and is_disaster_frame:
            reframe_dir = "disaster-to-recovery"
        elif final_l >= 5 and is_celebration_frame:
            reframe_dir = "celebration-to-decline"
        if not reframe_dir:
            continue
        out.append(CandidateObservation(
            suggested_type="retroactive",
            evidence={
                "original_week": int(wk) if wk else None,
                "original_card_type": ct,
                "original_headline": hl,
                "reframe_direction": reframe_dir,
                "final_record": f"{final_w}-{final_l}",
                "season_year": season_year,
            },
            source_citation=f"earlier this season · wk {wk} Chronicle · reframe",
            oddity_score=0.6,
            date_window=(f"{season_year}-08-01", f"{season_year}-12-31"),
            stream="retroactive",
            notes=(
                f"Wk {wk} shipped a '{reframe_dir.split('-')[0]}' framing "
                f"('{hl}'). Season closed {final_w}-{final_l}."
            ),
        ))
    return out


# --------------------------------------------------------------------------
# Stream 6 — Player-arc scanner
# --------------------------------------------------------------------------

def player_arc_stream(
    conn: sqlite3.Connection, team_slug: str, season_year: int, week: int | None,
) -> list[CandidateObservation]:
    """Player name-velocity surges + stat trajectories."""
    team = _team_row(conn, team_slug)
    if not team:
        return []
    tid = team["team_id"]
    out: list[CandidateObservation] = []

    # Aggregate player mentions across this season for the team — pick the
    # player with the single highest weekly attention_score spike AND at least
    # 3 weeks of presence (not a one-week blip).
    rows = conn.execute(
        """
        select pwcf.player_id,
               p.first_name, p.last_name, p.position,
               count(distinct pwcf.week) as weeks_present,
               max(pwcf.attention_score) as peak_attention,
               sum(pwcf.mention_count) as total_mentions,
               max(pwcf.week) as last_week
        from player_week_conversation_features pwcf
        join players p on p.player_id = pwcf.player_id
        where pwcf.team_id = ? and pwcf.season_year = ?
        group by pwcf.player_id, p.first_name, p.last_name, p.position
        having count(distinct pwcf.week) >= 3 and max(pwcf.attention_score) >= 2.0
        order by max(pwcf.attention_score) desc
        limit 2
        """,
        (tid, season_year),
    ).fetchall()
    for (pid, first, last, pos, weeks_n, peak_att, total_m, last_wk) in rows:
        # Stat trajectory (if any): pull player_value_metrics long-form rows.
        vm_rows = conn.execute(
            """
            select metric_name, metric_value, plays
            from player_value_metrics
            where player_id = ? and season_year = ?
            """,
            (pid, season_year),
        ).fetchall()
        vm_dict: dict[str, Any] = {}
        for (mname, mval, plays) in vm_rows:
            if mval is None:
                continue
            vm_dict[mname] = {
                "value": round(float(mval), 4),
                "plays": int(plays) if plays is not None else None,
            }
        display_name = " ".join(filter(None, [first, last])) or f"Player {pid}"
        out.append(CandidateObservation(
            suggested_type="player_arc",
            evidence={
                "player_id": int(pid),
                "player_name": display_name,
                "position": pos,
                "weeks_in_convo": int(weeks_n),
                "peak_attention_score": round(float(peak_att), 2),
                "total_mentions": int(total_m or 0),
                "last_mentioned_week": int(last_wk) if last_wk else None,
                "value_metrics": vm_dict,
                "season_year": season_year,
            },
            source_citation=f"gamelog + roster archive · {display_name} · {season_year}",
            oddity_score=min(1.0, 0.45 + float(peak_att) / 12.0),
            date_window=(f"{season_year}-08-01", f"{season_year}-12-31"),
            stream="player_arc",
            notes=(
                f"{display_name} ({pos}) carried {weeks_n} weeks of conversation "
                f"presence, peak attention {peak_att:.2f}. {total_m} mentions."
            ),
        ))
    return out
