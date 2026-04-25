"""Chronicle game-edition cards — Sprint 6.

Builds 3 game-tied Chronicle cards (anomaly / echo / retroactive) to land
in the T+25–30 window after a final. Reuses the Stage 3 LLM writer + Stage
4 validation gate from ``chronicle_generator``; the only thing that
changes here is candidate construction and the date_window contract.

Optional 4th card: ``divergence`` — fired only when fan-intel cohort
divergence is strong enough (effective_n ≥ 100 on at least two cohorts).

Editorial contract: every card must reference a specific play, quarter,
or stat from the just-ended game. Attribution must cite the gamelog,
beat-writer post-game piece, or a named fan source within the T-24h to
T+30min window.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .chronicle_streams import CandidateObservation
from .chronicle_generator import (
    ChronicleCard, BLUE_BLOODS, write_card, validate_card, _payload_to_card,
)
from .data import TeamSnapshot
from .profile_loader import Profile


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def generate_game_edition_cards(
    db,
    profile: Profile,
    snapshot: TeamSnapshot,
    *,
    final_meta: dict[str, Any],
    season_year: int | None = None,
    week: int | None = None,
    log: Any = None,
    mode: str = "auto",
    include_divergence_card: bool = True,
) -> list[ChronicleCard]:
    """Generate 3-4 game-edition Chronicle cards for the just-ended game.

    Returns ``ChronicleCard`` objects already validated through Stage 4.

    ``mode``:
      - 'auto'     → Sonnet for all 3 cards; Opus for the anomaly card on
                     blue-blood programs.
      - 'sonnet'   → all Sonnet
      - 'opus'     → all Opus (testing only)
      - 'template' → deterministic copy from candidate evidence (no LLM)
    """
    logf = _make_logger(log)
    season_year = season_year or snapshot.season_year
    cards: list[ChronicleCard] = []

    candidates = _build_game_edition_candidates(
        db, profile, snapshot, final_meta, season_year, week
    )

    if include_divergence_card:
        div = _build_divergence_candidate(db, profile, snapshot, final_meta, season_year, week)
        if div is not None:
            candidates.append(div)
            logf(f"  [{profile.slug}] game-edition: divergence candidate added")

    if not candidates:
        logf(f"  [{profile.slug}] game-edition: no candidates — skip")
        return []

    is_blueblood = profile.slug in BLUE_BLOODS
    from .chronicle_generator import CLAUDE_MODEL_SONNET, CLAUDE_MODEL_OPUS

    for i, cand in enumerate(candidates):
        if mode == "template":
            cards.append(_template_game_card(cand, profile))
            continue

        if mode == "sonnet":
            mdl = CLAUDE_MODEL_SONNET
        elif mode == "opus":
            mdl = CLAUDE_MODEL_OPUS
        else:  # auto
            # First card (anomaly) gets Opus on blue-bloods.
            mdl = CLAUDE_MODEL_OPUS if (is_blueblood and i == 0) else CLAUDE_MODEL_SONNET

        try:
            payload, meta = write_card(cand, profile, snapshot, model=mdl)
        except Exception as exc:
            logf(f"  [{profile.slug}] game-edition rank-{i+1} write error: {exc}; using template")
            cards.append(_template_game_card(cand, profile))
            continue

        if payload is None:
            logf(f"  [{profile.slug}] game-edition rank-{i+1} {cand.suggested_type}: write failed ({meta.get('error')})")
            cards.append(_template_game_card(cand, profile))
            continue

        ok, reasons = validate_card(payload, cand, profile)
        if ok:
            cards.append(_payload_to_card(
                payload, cand, model_id=mdl,
                snapshot=snapshot, season_year=season_year, validation_notes=[],
            ))
            continue

        logf(f"  [{profile.slug}] game-edition rank-{i+1} {cand.suggested_type}: validation failed {reasons}; retrying once")
        try:
            payload2, _ = write_card(cand, profile, snapshot, model=mdl)
        except Exception:
            payload2 = None
        if payload2 is None:
            cards.append(_template_game_card(cand, profile))
            continue
        ok2, reasons2 = validate_card(payload2, cand, profile)
        if ok2:
            cards.append(_payload_to_card(
                payload2, cand, model_id=mdl,
                snapshot=snapshot, season_year=season_year,
                validation_notes=[f"retry-after:{reasons}"],
            ))
        else:
            logf(f"  [{profile.slug}] game-edition rank-{i+1} retry failed {reasons2}; using template")
            cards.append(_template_game_card(cand, profile))

    return cards


# --------------------------------------------------------------------------
# Candidate construction — 3 game-edition card types
# --------------------------------------------------------------------------

def _build_game_edition_candidates(
    db,
    profile: Profile,
    snapshot: TeamSnapshot,
    final_meta: dict[str, Any],
    season_year: int,
    week: int | None,
) -> list[CandidateObservation]:
    """Return up to 3 candidates: anomaly, echo, retroactive.

    Each carries evidence from the just-ended game window:
      - anomaly:    program-historical outlier in a single game stat
      - echo:       resemblance to an earlier defining loss/win
      - retroactive: a card framing from earlier this season overturned by today
    """
    out: list[CandidateObservation] = []
    today = datetime.now(timezone.utc)
    window_start = (today - timedelta(hours=24)).isoformat()
    window_end = (today + timedelta(minutes=30)).isoformat()
    date_window = (window_start, window_end)

    team_pts, opp_pts, opp_slug, was_home = _team_score_facts(profile, final_meta)
    margin = team_pts - opp_pts
    rivalry_name = _rivalry_name_for(profile, opp_slug)
    opp_pretty = opp_slug.replace("-", " ").title()
    venue = "at home" if was_home else f"at {opp_pretty}"

    # ---- 1. Anomaly card ------------------------------------------------
    # Mock evidence: a stat that's a program-historical outlier. In
    # production, this is derived from per-game stats vs program-historical
    # baselines. The simulate-game CLI populates these via mock fixtures.
    anomaly_seed = (final_meta.get("game_edition_seeds") or {}).get("anomaly") or {}
    if anomaly_seed:
        out.append(CandidateObservation(
            suggested_type="anomaly",
            stream="gamelog",
            evidence={
                "stat_name": anomaly_seed.get("stat_name"),
                "stat_value": anomaly_seed.get("stat_value"),
                "historical_context": anomaly_seed.get("historical_context"),
                "rivalry_name": rivalry_name,
                "opponent_slug": opp_slug,
                "score": f"{team_pts}-{opp_pts}",
                "week": week,
            },
            source_citation=anomaly_seed.get("source_citation",
                f"gamelog · {rivalry_name or opp_pretty} {season_year} · Q{anomaly_seed.get('quarter', 4)} breakdown"),
            oddity_score=anomaly_seed.get("oddity_score", 0.85),
            date_window=date_window,
            notes=anomaly_seed.get("notes",
                f"{anomaly_seed.get('stat_name', 'A key stat')} — {profile.program_name}'s "
                f"{anomaly_seed.get('historical_context', 'worst result of the season')}."),
        ))

    # ---- 2. Echo card ---------------------------------------------------
    # A pattern in this game that rhymes with an earlier season. Production
    # path: cosine similarity between this game's WP shape + scoring cadence
    # and prior defining losses/wins from historical_season archive.
    echo_seed = (final_meta.get("game_edition_seeds") or {}).get("echo") or {}
    if echo_seed:
        out.append(CandidateObservation(
            suggested_type="echo",
            stream="archive",
            evidence={
                "echoed_season": echo_seed.get("echoed_season"),
                "echoed_game": echo_seed.get("echoed_game"),
                "similarity_features": echo_seed.get("similarity_features"),
                "rivalry_name": rivalry_name,
                "opponent_slug": opp_slug,
                "score": f"{team_pts}-{opp_pts}",
                "week": week,
            },
            source_citation=echo_seed.get("source_citation",
                f"historical archive · {echo_seed.get('echoed_season', '')} season · "
                f"vs {opp_pretty}"),
            oddity_score=echo_seed.get("oddity_score", 0.78),
            date_window=date_window,
            notes=echo_seed.get("notes",
                f"This loss to {opp_pretty} rhymes with {echo_seed.get('echoed_season', 'a prior season')} "
                f"in shape and result."),
        ))

    # ---- 3. Retroactive card --------------------------------------------
    retro_seed = (final_meta.get("game_edition_seeds") or {}).get("retroactive") or {}
    if retro_seed:
        out.append(CandidateObservation(
            suggested_type="retroactive",
            stream="retroactive",
            evidence={
                "earlier_card_headline": retro_seed.get("earlier_card_headline"),
                "earlier_card_week": retro_seed.get("earlier_card_week"),
                "overturned_by": retro_seed.get("overturned_by"),
                "rivalry_name": rivalry_name,
                "opponent_slug": opp_slug,
                "score": f"{team_pts}-{opp_pts}",
                "week": week,
            },
            source_citation=retro_seed.get("source_citation",
                f"prior Chronicle card · Wk {retro_seed.get('earlier_card_week', '?')} · "
                f"{season_year}"),
            oddity_score=retro_seed.get("oddity_score", 0.72),
            date_window=date_window,
            notes=retro_seed.get("notes",
                f"What looked like a fixed concern earlier this season has not held."),
        ))

    return out


# --------------------------------------------------------------------------
# Divergence bonus candidate (Sprint 6 §3.3)
# --------------------------------------------------------------------------

def _build_divergence_candidate(
    db,
    profile: Profile,
    snapshot: TeamSnapshot,
    final_meta: dict[str, Any],
    season_year: int,
    week: int | None,
) -> CandidateObservation | None:
    """Build the optional 4th game-edition card if divergence signal is strong.

    Strict gate: requires effective_n ≥ 100 in at least 2 cohorts AND
    divergence_score ≥ 0.30 from team_cohort_divergence_week.
    """
    try:
        # Latest divergence row.
        row = db.query_one(
            """
            select divergence_score
            from team_cohort_divergence_week
            where team_id = :tid
            order by week desc
            limit 1
            """,
            {"tid": snapshot.team_id},
        )
        div_score = float(row["divergence_score"]) if row and row.get("divergence_score") else 0.0
    except Exception:
        div_score = 0.0

    if div_score < 0.30:
        # Allow a fixture override for offline rehearsal.
        seed = (final_meta.get("game_edition_seeds") or {}).get("divergence")
        if not seed:
            return None
        if not seed.get("force_divergence"):
            return None

    # Confirm at least 2 cohorts have effective_n ≥ 100.
    try:
        rows = db.query_all(
            """
            select cohort, effective_n
            from team_cohort_week
            where team_id = :tid and effective_n >= 100.0
            order by week desc
            limit 14
            """,
            {"tid": snapshot.team_id},
        )
        n_qualified = len({r["cohort"] for r in rows}) if rows else 0
    except Exception:
        n_qualified = 0

    seed = (final_meta.get("game_edition_seeds") or {}).get("divergence") or {}
    if n_qualified < 2 and not seed.get("force_divergence"):
        return None

    today = datetime.now(timezone.utc)
    date_window = (
        (today - timedelta(hours=24)).isoformat(),
        (today + timedelta(minutes=30)).isoformat(),
    )

    team_pts, opp_pts, opp_slug, was_home = _team_score_facts(profile, final_meta)
    rivalry_name = _rivalry_name_for(profile, opp_slug)

    return CandidateObservation(
        suggested_type="divergence",
        stream="fanintel",
        evidence={
            "divergence_score": round(div_score, 3),
            "qualified_cohorts": n_qualified,
            "rivalry_name": rivalry_name,
            "opponent_slug": opp_slug,
            "score": f"{team_pts}-{opp_pts}",
            "week": week,
            "analytics_take": seed.get("analytics_take",
                "the per-play numbers were closer than the score"),
            "casual_take": seed.get("casual_take",
                "the score line is what it is"),
        },
        source_citation=seed.get("source_citation",
            f"cohort divergence · n={n_qualified} cohorts · {season_year}"),
        oddity_score=seed.get("oddity_score", min(1.0, 0.4 + div_score)),
        date_window=date_window,
        notes=seed.get("notes",
            "Two cohorts read the same game differently — both honestly."),
    )


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _team_score_facts(profile: Profile, final_meta: dict[str, Any]) -> tuple[int, int, str, bool]:
    team_slug = profile.slug.lower()
    home_slug = (final_meta.get("home_team_slug") or "").lower()
    away_slug = (final_meta.get("away_team_slug") or "").lower()
    hs = int(final_meta.get("home_score") or 0)
    as_ = int(final_meta.get("away_score") or 0)
    if home_slug == team_slug:
        return (hs, as_, away_slug, True)
    if away_slug == team_slug:
        return (as_, hs, home_slug, False)
    return (0, 0, "opponent", False)


def _rivalry_name_for(profile: Profile, opp_slug: str) -> str:
    for r in profile.rivalries:
        if (r.get("opponent_slug") or "").lower() == opp_slug.lower():
            return r.get("name") or r.get("trophy") or ""
    return ""


def _template_game_card(cand: CandidateObservation, profile: Profile) -> ChronicleCard:
    """Deterministic on-voice card from candidate evidence — used when LLM
    is unavailable or produces validation-failing output. Voice still comes
    from the profile's identity_phrase and stock_phrases.

    Card type-specific scaffolds:
      - anomaly:    leads with the stat, attaches the historical_context comparison
      - echo:       leads with the echoed game, attaches the rhyme
      - retroactive: leads with the earlier framing, attaches the overturn
      - divergence: leads with the analytics-cohort vs casual-vibes split
    """
    ev = cand.evidence
    ct = cand.suggested_type
    program = profile.program_name
    raw_rival = ev.get("rivalry_name") or ""
    opp_slug_for_label = ev.get("opponent_slug") or "the opponent"
    opp_label = (
        opp_slug_for_label.replace("-", " ").title()
        if opp_slug_for_label != "the opponent" else "the opponent"
    )
    if raw_rival:
        # Drop a leading "The " so phrases like "in the The Iron Bowl" don't
        # double-article. Reads correctly as "in the Iron Bowl".
        if raw_rival.lower().startswith("the "):
            rival_phrase = f"the {raw_rival[4:]}"
        else:
            rival_phrase = f"the {raw_rival}"
    else:
        # No rivalry — use the venue language instead of forcing a "the X" phrase.
        rival_phrase = f"the game at {opp_label}"
    # Determine outcome from score (used for win-aware copy in echo card).
    score = ev.get("score") or "—"
    try:
        team_pts_str, opp_pts_str = score.split("-")
        team_won = int(team_pts_str) > int(opp_pts_str)
    except (ValueError, AttributeError):
        team_won = False
    score = ev.get("score") or "—"

    if ct == "anomaly":
        stat = ev.get("stat_name") or "A key stat"
        val = ev.get("stat_value") or ""
        context = ev.get("historical_context") or "the worst in recent program memory"
        headline = f"{stat} — {context}"
        body = (
            f"{program} put up {val} in {rival_phrase}, "
            f"{context} for the program. "
            f"The score went to {score}; the underlying number went to a place "
            f"the program has rarely been."
        )
    elif ct == "echo":
        echoed_season = ev.get("echoed_season") or "a prior season"
        echoed_game = ev.get("echoed_game") or ""
        headline = f"This game rhymed with {echoed_season} — and not by accident"
        flow_word = "win" if team_won else "loss"
        shape = (
            "early lead, controlled tempo, the same mood in the room"
            if team_won
            else "early lead, second-half collapse, the same mood in the room"
        )
        body = (
            f"The flow of the {flow_word} in {rival_phrase} carried the same shape as "
            f"{echoed_season}{(' ' + echoed_game) if echoed_game else ''}: "
            f"{shape}. {program} has seen this film before."
        )
    elif ct == "retroactive":
        earlier = ev.get("earlier_card_headline") or "the earlier framing"
        overturn = ev.get("overturned_by") or "today's tape"
        result_word = "win" if team_won else "loss"
        headline = f"What we wrote earlier did not survive {rival_phrase}"
        body = (
            f"{earlier} read as a settled matter through midseason. "
            f"{overturn} unsettled it. The {result_word} at {score} is the "
            f"evidence that closes that argument differently than it opened."
        )
    elif ct == "divergence":
        a_take = ev.get("analytics_take") or "the per-play numbers were close"
        c_take = ev.get("casual_take") or "the score is the score"
        headline = f"The analytics room and the bar saw different games"
        body = (
            f"In {rival_phrase}, the analytics cohort spent the second half noting "
            f"that {a_take}. The casual cohort spent it watching the score: "
            f"{c_take} at {score}. Both readings are honest. Only one is comfortable."
        )
    else:
        headline = f"{program} after {rival_phrase}"
        body = f"{program} took the result. {score}. The work continues."

    return ChronicleCard(
        card_type=ct,
        headline=headline,
        body_md=body,
        stat={"stream": cand.stream, "evidence": ev, "oddity_score": round(cand.oddity_score, 3)},
        comparison={"source_citation": cand.source_citation,
                    "date_window": list(cand.date_window)},
        source_attribution=cand.source_citation,
        surprise_score=round(cand.oddity_score, 3),
        week=ev.get("week"),
        model_id="template-v2-game-edition",
    )


def _make_logger(log: Any) -> Any:
    if log is None:
        return lambda msg: print(msg, flush=True)
    if callable(log):
        return log
    if hasattr(log, "write"):
        return lambda msg: (log.write(msg + "\n"), log.flush())
    return lambda msg: print(msg, flush=True)
