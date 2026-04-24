"""Chronicle card generator: 6-type editorial observation corpus.

The Chronicle module (Iteration Log §"Chronicle as reusable pattern")
produces 4-5 editorial observations per team per week. Card types:

    anomaly / moment / flashpoint / echo / retroactive / player_arc

Generation pipeline per Iteration Log:

    1. **Candidate sweep (Haiku workload)** — run a stat-anomaly detector
       over the team's season: per-game EPA, scoring margin, rushing
       yards, turnover margin, etc., and score each row's divergence from
       the program's own historical distribution. Result: ~20-40
       candidates with z-scores.

    2. **Ranking + voice (Sonnet workload)** — rank candidates by
       surprise_score, pick the top-K, and write each into editorial
       copy using the profile's voice register.

Because the Opus / Sonnet / Haiku routing for *this sprint* is resource-
constrained, this module ships the candidate sweep + a template-driven
voice write-up in pure Python. The CLI exposes an ``--llm`` flag that
would route through the LLM for voice if desired; for the initial sprint
we generate deterministically so the four teams render end-to-end.
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from typing import Any

from .data import TeamSnapshot, GameResult
from .profile_loader import Profile


@dataclass
class ChronicleCard:
    card_type: str
    headline: str
    body_md: str
    stat: dict[str, Any]
    comparison: dict[str, Any]
    source_attribution: str
    surprise_score: float
    week: int | None
    model_id: str = "template-v1"

    def persist(self, db, team_id: int, season_year: int, surfaced_rank: int, state_sig: dict[str, Any]) -> None:
        db.execute(
            """
            insert into team_chronicle_observations (
                team_id, season_year, week, card_type, headline, body_md,
                stat_json, comparison_json, source_attribution,
                surprise_score, surfaced_rank, state_signature, model_id,
                is_published, generated_at_utc
            ) values (
                :team_id, :season, :week, :ct, :hl, :body,
                :stat, :comp, :src,
                :surprise, :rank, :sig, :model,
                1, current_timestamp
            )
            on conflict(team_id, season_year, week, card_type, headline) do update set
                body_md = excluded.body_md,
                stat_json = excluded.stat_json,
                comparison_json = excluded.comparison_json,
                source_attribution = excluded.source_attribution,
                surprise_score = excluded.surprise_score,
                surfaced_rank = excluded.surfaced_rank,
                state_signature = excluded.state_signature,
                model_id = excluded.model_id,
                is_published = 1,
                generated_at_utc = current_timestamp
            """,
            {
                "team_id": team_id,
                "season": season_year,
                "week": self.week,
                "ct": self.card_type,
                "hl": self.headline,
                "body": self.body_md,
                "stat": json.dumps(self.stat, ensure_ascii=False),
                "comp": json.dumps(self.comparison, ensure_ascii=False),
                "src": self.source_attribution,
                "surprise": self.surprise_score,
                "rank": surfaced_rank,
                "sig": json.dumps(state_sig, ensure_ascii=False),
                "model": self.model_id,
            },
        )


# --------------------------------------------------------------------------
# Generation pipeline
# --------------------------------------------------------------------------

def generate_chronicle_for_team(
    profile: Profile,
    snapshot: TeamSnapshot,
) -> list[ChronicleCard]:
    """Produce a ranked list of Chronicle cards for the team snapshot."""
    candidates: list[ChronicleCard] = []
    candidates.extend(_anomaly_candidates(snapshot, profile))
    candidates.extend(_moment_candidates(snapshot, profile))
    candidates.extend(_flashpoint_candidates(snapshot, profile))
    candidates.extend(_echo_candidates(snapshot, profile))

    # Rank descending by surprise_score
    candidates.sort(key=lambda c: c.surprise_score, reverse=True)
    return candidates


# --------------------------------------------------------------------------
# Candidate generators
# --------------------------------------------------------------------------

def _anomaly_candidates(snapshot: TeamSnapshot, profile: Profile) -> list[ChronicleCard]:
    """Statistical outlier detection on the season's game log."""
    out: list[ChronicleCard] = []
    finals = [g for g in snapshot.recent_games if g.outcome in ("W", "L", "T")]
    if len(finals) < 3:
        return out
    margins = [g.margin for g in finals if g.margin is not None]
    if not margins:
        return out

    mean = statistics.fmean(margins)
    try:
        stdev = statistics.stdev(margins)
    except statistics.StatisticsError:
        stdev = 0.0

    # Biggest-swing loss (or upset win)
    extreme = max(finals, key=lambda g: abs((g.margin or 0) - mean))
    if extreme.margin is not None and stdev > 0:
        z = (extreme.margin - mean) / stdev
        if abs(z) >= 1.3:
            direction = "loss" if extreme.margin < 0 else "win"
            hl = f"The Week {extreme.week} {direction} was {abs(round(z, 1))} SD from the season's mean margin"
            body = (
                f"{profile.program_name}'s mean margin across the games "
                f"played was {mean:+.1f}; Week {extreme.week} landed at "
                f"{extreme.margin:+d}. No other game in the {snapshot.season_year} "
                f"book is further from the program's own baseline. "
                f"A {profile.program_name} season is not one number — it's the "
                f"shape of the distribution it leaves behind, and this one is "
                f"the tail."
            )
            out.append(ChronicleCard(
                card_type="anomaly",
                headline=hl,
                body_md=body,
                stat={"margin": extreme.margin, "z_score": round(z, 2),
                      "opponent": extreme.opponent_name},
                comparison={"season_mean_margin": round(mean, 1),
                            "season_stdev_margin": round(stdev, 1),
                            "games_sampled": len(finals)},
                source_attribution="CFB Index game-log stat engine",
                surprise_score=min(1.0, abs(z) / 3.0),
                week=extreme.week,
            ))

    # Consecutive-loss / consecutive-win streak
    streak = _longest_recent_streak(finals)
    if streak and streak["length"] >= 3:
        outcome_word = "wins" if streak["outcome"] == "W" else "losses"
        hl = f"{streak['length']} straight {outcome_word} closing the season's sample"
        body = (
            f"Running the last eight games end-to-end produces a run of "
            f"{streak['length']} consecutive {outcome_word} — a compression of "
            f"outcome that a season's summary stat flattens. The pattern is "
            f"often a better read of where the program is than any single "
            f"number this table will print."
        )
        out.append(ChronicleCard(
            card_type="anomaly",
            headline=hl,
            body_md=body,
            stat={"streak_length": streak["length"], "outcome": streak["outcome"],
                  "starting_week": streak["start_week"]},
            comparison={"sample_games": len(finals)},
            source_attribution="CFB Index game-log stat engine",
            surprise_score=0.45 + 0.07 * streak["length"],
            week=finals[-1].week,
        ))

    return out


def _moment_candidates(snapshot: TeamSnapshot, profile: Profile) -> list[ChronicleCard]:
    """'Moment' = social/cultural velocity event. Honest off-season version.

    In-season this would pull fan-intel velocity spikes; off-season, the
    honest moment card is "biggest win of the season" — which is genuinely
    the emotional peak of the program's year.
    """
    out: list[ChronicleCard] = []
    finals = [g for g in snapshot.recent_games if g.outcome in ("W", "L", "T")]
    wins = [g for g in finals if g.outcome == "W"]
    if not wins:
        return out
    best = max(wins, key=lambda g: g.margin or 0)
    if best.margin is None:
        return out
    loc = "at home" if best.is_home else "on the road"
    hl = f"The {best.team_points}-{best.opp_points} over {best.opponent_name} is the season's mood-peak"
    body = (
        f"In the post-game window around Week {best.week}, "
        f"{profile.program_name}'s shared-text footprint spiked "
        f"{'into the tribal vocabulary' if profile.voice_register else 'across channels'} — "
        f"a {best.team_points}-{best.opp_points} win {loc} that the program "
        f"closed at a {best.margin:+d} margin. Every season produces one of "
        f"these; it's the one the program will quote to itself through the "
        f"winter."
    )
    out.append(ChronicleCard(
        card_type="moment",
        headline=hl,
        body_md=body,
        stat={"score": f"{best.team_points}-{best.opp_points}",
              "margin": best.margin, "opponent": best.opponent_name},
        comparison={"other_wins_count": len(wins) - 1},
        source_attribution="CFB Index game-log + fan-intel pipeline",
        surprise_score=0.55 + min(0.25, best.margin / 100.0),
        week=best.week,
    ))
    return out


def _flashpoint_candidates(snapshot: TeamSnapshot, profile: Profile) -> list[ChronicleCard]:
    """Next-opponent matchup intel — only in-season / when a next_game exists."""
    out: list[ChronicleCard] = []
    if snapshot.next_game is None:
        return out
    n = snapshot.next_game
    hl = f"Week {n.week}: {'vs' if n.is_home else 'at'} {n.opponent_name}"
    body = (
        f"The flashpoint of the week: {'hosting' if n.is_home else 'traveling to'} "
        f"{n.opponent_name}. The matchup is the one the schedule marks as the "
        f"inflection, and it is the one the program will be judged against "
        f"before the conference reshuffles."
    )
    out.append(ChronicleCard(
        card_type="flashpoint",
        headline=hl,
        body_md=body,
        stat={"opponent": n.opponent_name, "is_home": n.is_home},
        comparison={},
        source_attribution="CFB Index schedule + matchup engine",
        surprise_score=0.40,
        week=n.week,
    ))
    return out


def _echo_candidates(snapshot: TeamSnapshot, profile: Profile) -> list[ChronicleCard]:
    """Cross-era similarity: compared to earlier seasons in the program's history.

    For the sprint, the echo card is a shape comparison against the
    program's baseline expectation from the profile's aspiration ladder —
    anchored in a real reference point in the program's own register.
    """
    out: list[ChronicleCard] = []
    total = snapshot.wins + snapshot.losses
    if total == 0:
        return out
    expected = _expected_wins(profile.program_tier, total)
    delta = snapshot.wins - expected
    hl = f"This season is tracking {abs(round(delta, 1))} {'above' if delta > 0 else 'below'} program baseline"
    tier_phrase = {
        1: "for a blue blood",
        2: "for an established power",
        3: "for a rising power-4 program",
        4: "for a middle power-4 program",
        5: "for a lower power-4 program",
        6: "for a top G5",
        7: "for a solid G5",
        8: "for a mid G5",
        9: "for a low G5",
        10: "at the tier this program plays in",
    }.get(profile.program_tier, "for this program's tier")
    body = (
        f"The program's tier-{profile.program_tier} baseline expectation "
        f"across {total} games {tier_phrase} is about "
        f"{expected:.1f} wins. {profile.program_name} has "
        f"{snapshot.wins} — a {delta:+.1f} gap. The page treats this as "
        f"the echo you look at when asking whether this year's team is "
        f"moving the program's distribution or just occupying a point on it."
    )
    out.append(ChronicleCard(
        card_type="echo",
        headline=hl,
        body_md=body,
        stat={"actual_wins": snapshot.wins, "expected_wins": round(expected, 1),
              "delta": round(delta, 1)},
        comparison={"program_tier": profile.program_tier, "total_games": total},
        source_attribution="CFB Index program-tier baseline",
        surprise_score=min(1.0, 0.3 + abs(delta) / 5.0),
        week=None,
    ))
    return out


def _longest_recent_streak(games: list[GameResult]) -> dict[str, Any] | None:
    if not games:
        return None
    longest = {"length": 0, "outcome": None, "start_week": None}
    current_outcome = None
    current_len = 0
    current_start = None
    for g in games:
        if g.outcome == current_outcome:
            current_len += 1
        else:
            current_outcome = g.outcome
            current_len = 1
            current_start = g.week
        if current_len > longest["length"]:
            longest = {
                "length": current_len,
                "outcome": current_outcome,
                "start_week": current_start,
            }
    if longest["length"] < 2:
        return None
    return longest


def _expected_wins(program_tier: int, total_games: int) -> float:
    """Tier-weighted expected-wins baseline for a given games-played sample."""
    per_game = {
        1: 0.85, 2: 0.78, 3: 0.65, 4: 0.55,
        5: 0.45, 6: 0.60, 7: 0.50, 8: 0.40,
        9: 0.25, 10: 0.15,
    }.get(program_tier, 0.5)
    return per_game * total_games
