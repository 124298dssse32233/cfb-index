"""Fan intelligence / fanbase mood computation.

This module bridges the conversation-intelligence data (team_week_conversation_features,
team_conversation_daily, conversation_storylines) into the reporting layer as a
single team mood profile plus editorial leaderboards for the homepage.

Design rules this module holds the line on:

- Public outputs should never print raw classifier scores as precise truths.
- Every profile carries a confidence band and a graceful "no signal yet" state
  so we can ship the UI before the collection pipeline is fully filled in.
- Reality Gap is derived by comparing fan belief against the structural power
  percentile. It is never inferred from text alone.
- Fan vs rival vs national audience buckets stay separate. We never let rival
  mockery drift into a team's own fan pulse.
- Sarcasm-risky samples get their confidence downgraded and the worst readers
  get suppressed out of headline surfaces entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import math
from typing import Any, Iterable

from cfb_rankings.common.cfb_calendar import cfb_week_label_for_window
from cfb_rankings.db import Database


# Minimum gates before we treat a team as "publishable" on a surface.
MIN_MENTIONS_FOR_SIGNAL = 12
MIN_AUTHORS_FOR_SIGNAL = 4
MIN_MENTIONS_FOR_HIGH_CONFIDENCE = 40
MIN_AUTHORS_FOR_HIGH_CONFIDENCE = 12


@dataclass
class MoodContext:
    """Per-team context used to derive Reality Gap and Respect Gap."""

    team_id: int
    power_percentile: float | None
    resume_percentile: float | None


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def fetch_team_mood_profile(
    db: Database,
    team_id: int,
    season_year: int,
    week: int,
    context: MoodContext,
) -> dict[str, Any]:
    """Build a single team's mood profile for display on the team page.

    Returns a dict with a stable shape. If no conversation signal exists for the
    team, returns a profile with ``has_data=False`` and readable placeholder
    copy so the UI can still render a premium "awaiting signal" state.
    """

    fan_row = _fetch_weekly_bucket(db, team_id, season_year, week, "fan")
    national_row = _fetch_weekly_bucket(db, team_id, season_year, week, "national")
    rival_row = _fetch_rival_bucket(db, team_id, season_year, week)
    history = _fetch_belief_history(db, team_id, season_year, week, window=5)
    storylines = _fetch_storylines(db, team_id, season_year, week)

    mention_count = int((fan_row or {}).get("mention_count") or 0)
    author_count = int((fan_row or {}).get("unique_author_count") or 0)

    if not fan_row or mention_count < MIN_MENTIONS_FOR_SIGNAL:
        return _empty_profile(
            team_id=team_id,
            season_year=season_year,
            week=week,
            mention_count=mention_count,
            author_count=author_count,
        )

    belief = _belief_from_row(fan_row)
    national_belief = _belief_from_row(national_row) if national_row else None
    rival_belief = _belief_from_row(rival_row) if rival_row else None

    reality_gap = _reality_gap(belief, context)
    respect_gap = _respect_gap(belief, national_belief)
    cohesion = _cohesion_from_row(fan_row)
    swing = _swing_from_history(history, current_belief=belief["score"])
    rival_heat = _rival_heat(rival_row)
    sarcasm_risk = _sarcasm_risk_from_row(fan_row, rival_row)
    confidence = _confidence(
        mentions=mention_count,
        authors=author_count,
        sarcasm_risk=sarcasm_risk,
    )

    archetype = _archetype(belief, reality_gap, swing, cohesion)

    return {
        "has_data": True,
        "team_id": team_id,
        "season_year": season_year,
        "week": week,
        "confidence": confidence,
        "sample": {
            "mentions": mention_count,
            "authors": author_count,
            "sarcasm_risk": sarcasm_risk,
            "national_mentions": int((national_row or {}).get("mention_count") or 0),
            "rival_mentions": int((rival_row or {}).get("mention_count") or 0),
        },
        "belief": belief,
        "reality_gap": reality_gap,
        "respect_gap": respect_gap,
        "swing": swing,
        "cohesion": cohesion,
        "rival_heat": rival_heat,
        "archetype": archetype,
        "storylines": storylines,
        "updated_label": f"{cfb_week_label_for_window(date.today(), week, db=None)} conversation window",
    }


def fetch_player_mood_profile(
    db: Database,
    player_id: int,
    season_year: int,
    week: int,
    context: "MoodContext | None" = None,
) -> dict[str, Any]:
    """Build The Room on [Player] — player-scoped mirror of fetch_team_mood_profile.

    Reads `player_week_conversation_features`. Returns the same shape as the
    team-scope profile plus a ``top_quote`` field. When the player has no
    conversation signal yet, returns a ``has_data=False`` envelope identical
    in shape to the team-scope empty profile so the template never branches.

    Reality Gap and Rival Heat are held at ``available=False`` on purpose —
    both rely on team-level structural inputs (power percentile, rival
    fanbase mockery) that don't map cleanly to a single player; the template
    can still render those panels with honest "context lives on the team
    page" copy.
    """
    fan_row = _fetch_weekly_bucket_scoped(
        db, scope="player", entity_id=player_id,
        season_year=season_year, week=week, bucket="fan",
    )
    national_row = _fetch_weekly_bucket_scoped(
        db, scope="player", entity_id=player_id,
        season_year=season_year, week=week, bucket="national",
    )
    rival_row = _fetch_weekly_bucket_scoped(
        db, scope="player", entity_id=player_id,
        season_year=season_year, week=week, bucket="rival",
    )
    media_row = _fetch_weekly_bucket_scoped(
        db, scope="player", entity_id=player_id,
        season_year=season_year, week=week, bucket="media",
    )
    history = _fetch_belief_history_scoped(
        db, scope="player", entity_id=player_id,
        season_year=season_year, week=week, window=5,
    )

    mention_count = int((fan_row or {}).get("mention_count") or 0)
    author_count = int((fan_row or {}).get("unique_author_count") or 0)

    if not fan_row or mention_count < MIN_MENTIONS_FOR_SIGNAL or author_count < MIN_AUTHORS_FOR_SIGNAL:
        return _empty_player_profile(
            player_id=player_id,
            season_year=season_year,
            week=week,
            mention_count=mention_count,
            author_count=author_count,
        )

    belief = _belief_from_row(fan_row)
    national_belief = _belief_from_row(national_row) if national_row else None
    rival_belief = _belief_from_row(rival_row) if rival_row else None  # noqa: F841

    respect_gap = _respect_gap(belief, national_belief)
    cohesion = _cohesion_from_row(fan_row)
    swing = _swing_from_history(history, current_belief=belief["score"])
    sarcasm_risk = _sarcasm_risk_from_row(fan_row, rival_row)
    confidence = _confidence(
        mentions=mention_count,
        authors=author_count,
        sarcasm_risk=sarcasm_risk,
    )

    # Derive the top_quote from JSON stored on the fan row (preferred) or the
    # media row. Templates render the pseudonym + backlink per Tier B rule.
    # Entity-match guard: only surface quotes that actually name the player.
    # Prevents cohort-level chatter ("Indiana's recruiting under Cignetti")
    # from being attributed to a specific player ("Fernando Mendoza") who
    # is not named in the quote text.
    name_tokens = _player_name_tokens(db, player_id)
    top_quote = _player_top_quote(fan_row, media_row, player_name_tokens=name_tokens)

    return {
        "has_data": True,
        "player_id": player_id,
        "season_year": season_year,
        "week": week,
        "confidence": confidence,
        "sample": {
            "mentions": mention_count,
            "authors": author_count,
            "sarcasm_risk": sarcasm_risk,
            "national_mentions": int((national_row or {}).get("mention_count") or 0),
            "rival_mentions": int((rival_row or {}).get("mention_count") or 0),
            "media_mentions": int((media_row or {}).get("mention_count") or 0),
        },
        "belief": belief,
        "reality_gap": {
            "available": False,
            "label": None,
            "score": None,
            "narrative": "Reality Gap is a team-level check; see the program page for structural context.",
        },
        "respect_gap": respect_gap,
        "swing": swing,
        "cohesion": cohesion,
        "rival_heat": {
            "available": False,
            "label": None,
            "score": None,
            "narrative": "Rival Heat aggregates across a fanbase and sits on the team page.",
        },
        "archetype": _archetype(belief, {"label": None}, swing, cohesion),
        "storylines": [],   # player-scope storylines require conversation_storylines(entity_type='player'); wiring pending
        "top_quote": top_quote,
        "updated_label": f"{cfb_week_label_for_window(date.today(), week, db=None)} conversation window",
    }


def compute_player_mood_index(
    db: Database,
    season_year: int,
    week: int,
    *,
    fallback_to_season_rollup: bool = True,
) -> dict[int, dict[str, Any]]:
    """Batch-precompute per-player mood profiles for a site build.

    One query pulls all qualifying player rows for (season, week); rows are
    grouped by player_id and handed to `fetch_player_mood_profile`-equivalent
    logic without re-querying.

    When ``fallback_to_season_rollup`` is True (default), players whose
    weekly row does NOT clear the gates are evaluated against the
    season-rollup row (week=0) written by
    ``compute_player_season_mood``. Lets offseason pages surface real
    Room cards for players whose mentions cross the floor *across* the
    season even when no single week clears it on its own.
    """
    all_rows = db.query_all(
        """
        select *
        from player_week_conversation_features
        where season_year = %(season_year)s
          and week = %(week)s
        """,
        {"season_year": season_year, "week": week},
    )
    season_rollup_rows: list[dict[str, Any]] = []
    if fallback_to_season_rollup and week != 0:
        season_rollup_rows = db.query_all(
            """
            select *
            from player_week_conversation_features
            where season_year = %(season_year)s
              and week = 0
            """,
            {"season_year": season_year},
        )
    if not all_rows and not season_rollup_rows:
        return {}
    # Group by player_id → {bucket: row}. Prefer source_name='all' then
    # highest mention_count, matching the non-batch helper's ordering.
    def _group(rows: list[dict[str, Any]]) -> dict[int, dict[str, dict[str, Any]]]:
        out: dict[int, dict[str, dict[str, Any]]] = {}
        for row in rows:
            pid = int(row["player_id"])
            bucket = str(row.get("audience_bucket") or "all")
            existing = out.setdefault(pid, {}).get(bucket)
            if existing is None or _better_bucket_row(row, existing):
                out.setdefault(pid, {})[bucket] = row
        return out

    weekly_groups = _group(all_rows)
    rollup_groups = _group(season_rollup_rows)
    # Consider every player who appears in either dataset.
    all_player_ids = set(weekly_groups) | set(rollup_groups)

    def _primary_bucket(buckets: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
        """Pick the bucket that drives belief.

        Preference order: fan (own-fan chatter is the highest-fidelity signal
        when available), then national, then media, then rival. Within the
        chosen preference, the bucket must clear MIN_MENTIONS_FOR_SIGNAL and
        MIN_AUTHORS_FOR_SIGNAL. Returns (bucket_name, row) or None if no
        bucket clears.

        Honoring this order avoids rival mockery driving the belief score
        (an existing design rule: rival never bleeds into fan belief).
        """
        for name in ("fan", "national", "media", "rival"):
            row = buckets.get(name)
            if not row:
                continue
            m = int(row.get("mention_count") or 0)
            a = int(row.get("unique_author_count") or 0)
            if m >= MIN_MENTIONS_FOR_SIGNAL and a >= MIN_AUTHORS_FOR_SIGNAL:
                return name, row
        return None

    # History is still per-player; query once per qualifying player. Given
    # player-scope row counts are small at v1, this is not a hot path.
    index: dict[int, dict[str, Any]] = {}
    for pid in all_player_ids:
        # Try weekly first; fall back to season rollup if weekly is below gates.
        chosen_scope = "weekly"
        chosen_bucket = "fan"
        buckets = weekly_groups.get(pid) or {}
        primary = _primary_bucket(buckets)
        if primary is None and fallback_to_season_rollup and pid in rollup_groups:
            buckets = rollup_groups[pid]
            primary = _primary_bucket(buckets)
            chosen_scope = "season"
        if primary is None:
            continue
        chosen_bucket, primary_row = primary
        mention_count = int(primary_row.get("mention_count") or 0)
        author_count = int(primary_row.get("unique_author_count") or 0)
        # Keep the actual fan-bucket row available separately so the top_quote
        # preference stays "fan voice first, then media", regardless of which
        # bucket drove the belief gate.
        fan_row_for_quote = buckets.get("fan")
        national_row = buckets.get("national")
        rival_row = buckets.get("rival")
        media_row = buckets.get("media")
        history = _fetch_belief_history_scoped(
            db, scope="player", entity_id=pid,
            season_year=season_year, week=week, window=5,
        )
        # Belief, cohesion, and sarcasm are computed from the row that
        # drove the gate — fan preferred, then national, etc.
        belief = _belief_from_row(primary_row)
        national_belief = _belief_from_row(national_row) if national_row else None
        cohesion = _cohesion_from_row(primary_row)
        swing = _swing_from_history(history, current_belief=belief["score"])
        sarcasm_risk = _sarcasm_risk_from_row(primary_row, rival_row)
        confidence = _confidence(mentions=mention_count, authors=author_count, sarcasm_risk=sarcasm_risk)
        # Quote ordering is independent of gate: fan voice first (even if
        # the fan bucket was below the gate), then media, then the
        # primary bucket as a last resort so the Room never renders
        # quote-less when a quote exists anywhere in the player's data.
        # Entity-match guard: only surface quotes that name the player —
        # see _player_top_quote docstring for the cohort-leak motivation.
        name_tokens = _player_name_tokens(db, pid)
        top_quote = (
            _player_top_quote(fan_row_for_quote, media_row, player_name_tokens=name_tokens)
            or _player_top_quote(primary_row, None, player_name_tokens=name_tokens)
        )
        index[pid] = {
            "has_data": True,
            "player_id": pid,
            "season_year": season_year,
            "week": week if chosen_scope == "weekly" else 0,
            "scope": chosen_scope,
            "primary_bucket": chosen_bucket,
            "confidence": confidence,
            "sample": {
                "mentions": mention_count,
                "authors": author_count,
                "sarcasm_risk": sarcasm_risk,
                "national_mentions": int((national_row or {}).get("mention_count") or 0),
                "rival_mentions": int((rival_row or {}).get("mention_count") or 0),
                "media_mentions": int((media_row or {}).get("mention_count") or 0),
            },
            "belief": belief,
            "reality_gap": {
                "available": False, "label": None, "score": None,
                "narrative": "Reality Gap is a team-level check; see the program page for structural context.",
            },
            "respect_gap": _respect_gap(belief, national_belief),
            "swing": swing,
            "cohesion": cohesion,
            "rival_heat": {
                "available": False, "label": None, "score": None,
                "narrative": "Rival Heat aggregates across a fanbase and sits on the team page.",
            },
            "archetype": _archetype(belief, {"label": None}, swing, cohesion),
            "storylines": [],
            "top_quote": top_quote,
            "updated_label": (
                f"Season {season_year} conversation window"
                if chosen_scope == "season"
                else f"{cfb_week_label_for_window(date.today(), week, db=None)} conversation window"
            ),
        }
    return index


def _better_bucket_row(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    """Prefer source_name='all'; tie-break by mention_count; then source_name."""
    c_all = (candidate.get("source_name") == "all")
    x_all = (current.get("source_name") == "all")
    if c_all != x_all:
        return c_all  # True if candidate is 'all' and current isn't
    c_n = int(candidate.get("mention_count") or 0)
    x_n = int(current.get("mention_count") or 0)
    if c_n != x_n:
        return c_n > x_n
    return str(candidate.get("source_name") or "") < str(current.get("source_name") or "")


def _player_top_quote(
    primary_row: dict[str, Any] | None,
    fallback_row: dict[str, Any] | None,
    *,
    player_name_tokens: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    """Pull one representative quote from the row's top_quote_json, if present.

    Defensive entity-match guard: when ``player_name_tokens`` is supplied,
    the quote text must contain at least one token (case-insensitive
    substring match) before we attribute it to the player. This stops
    cohort-level quotes (e.g. a Locked-On podcast about Mississippi NIL
    law that happens to be in Indiana's bucket) from being surfaced on a
    specific player's page as if they were said about him. Empty tuple =
    legacy behavior, no filter.
    """
    for row in (primary_row, fallback_row):
        if not row:
            continue
        raw = row.get("top_quote_json")
        if not raw:
            continue
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        text = str(data.get("text") or "").strip()
        if not text:
            continue
        if player_name_tokens:
            haystack = text.lower()
            if not any(tok and tok in haystack for tok in player_name_tokens):
                # Quote does not name the player — skip rather than risk
                # surfacing a team-level take as the player's top quote.
                continue
        return {
            "text": text,
            "author_pseudonym": str(data.get("author_pseudonym") or "fan"),
            "source_url": data.get("source_url"),
            "sentiment_score": data.get("sentiment_score"),
            "bucket": row.get("audience_bucket"),
        }
    return None


def _player_name_tokens(db: Database, player_id: int) -> tuple[str, ...]:
    """Fetch a small set of name tokens to entity-match a player against quote
    text. Best-effort: returns lowercased first/last name + any short alias
    we have on file. Empty tuple means "no filter" (legacy behavior).
    """
    try:
        row = db.query_one(
            "select first_name, last_name from players where player_id = %(pid)s",
            params={"pid": int(player_id)},
        )
    except Exception:
        return ()
    if not row:
        return ()
    tokens: list[str] = []
    for key in ("first_name", "last_name"):
        v = str(row.get(key) or "").strip().lower()
        # First names like "A.J." or "T.J." would match too aggressively
        # against random text; require >= 3 chars for inclusion.
        if len(v) >= 3:
            tokens.append(v)
    return tuple(tokens)


def _empty_player_profile(
    *,
    player_id: int,
    season_year: int,
    week: int,
    mention_count: int,
    author_count: int,
) -> dict[str, Any]:
    return {
        "has_data": False,
        "player_id": player_id,
        "season_year": season_year,
        "week": week,
        "confidence": {"label": "No signal", "score": 0.0, "sarcasm_risk": "low"},
        "sample": {
            "mentions": mention_count,
            "authors": author_count,
            "sarcasm_risk": "low",
            "national_mentions": 0,
            "rival_mentions": 0,
            "media_mentions": 0,
        },
        "belief": {"score": None, "label": None, "narrative": "Not enough player-specific chatter yet."},
        "reality_gap": {"available": False, "label": None, "score": None, "narrative": "Reality Gap lives on the team page until player mentions clear gates."},
        "respect_gap": {"available": False, "label": None, "score": None, "narrative": "Respect Gap compares fans vs. outsiders — needs enough of each."},
        "swing": {"available": False, "label": None, "score": None, "narrative": "Swing needs a few weeks of history before it's honest."},
        "cohesion": {"score": 0.0, "label": None, "narrative": "Internal polarization shows up once the sample is big enough."},
        "rival_heat": {"available": False, "label": None, "score": None, "narrative": "Rival Heat aggregates across a fanbase and sits on the team page."},
        "archetype": None,
        "storylines": [],
        "top_quote": None,
        "updated_label": f"{cfb_week_label_for_window(date.today(), week, db=None)} conversation window",
    }


def fetch_fan_intel_board(
    db: Database,
    season_year: int,
    week: int,
    team_index: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Build homepage fan-intelligence leaderboards for a given week.

    ``team_index`` maps team_id -> {"slug", "team_name", "level_code", "power_percentile"}
    so we can tag each board row with presentation-safe metadata.
    """

    weekly = _fetch_all_weekly_features(db, season_year, week)
    if not weekly:
        return _empty_board(season_year=season_year, week=week)

    prior_weekly = _fetch_all_weekly_features(db, season_year, max(1, week - 1))
    prior_fan = {
        (row["team_id"], row["audience_bucket"]): row for row in prior_weekly
    }

    per_team: dict[int, dict[str, Any]] = {}
    for row in weekly:
        bucket = str(row.get("audience_bucket") or "all")
        team_id = int(row["team_id"])
        entry = per_team.setdefault(team_id, {})
        entry[bucket] = row

    vibe_shifts: list[dict[str, Any]] = []
    respect_gap_leaders: list[dict[str, Any]] = []
    respect_gap_doubters: list[dict[str, Any]] = []
    rival_heat_leaders: list[dict[str, Any]] = []
    main_characters: list[dict[str, Any]] = []
    panicked_fanbases: list[dict[str, Any]] = []
    polarized: list[dict[str, Any]] = []

    for team_id, buckets in per_team.items():
        team_meta = team_index.get(team_id)
        if not team_meta:
            continue
        fan_row = buckets.get("fan") or buckets.get("all")
        if not fan_row:
            continue
        if int(fan_row.get("mention_count") or 0) < MIN_MENTIONS_FOR_SIGNAL:
            continue

        belief = _belief_from_row(fan_row)
        cohesion = _cohesion_from_row(fan_row)
        sarcasm_risk = _sarcasm_risk_from_row(fan_row, buckets.get("rival"))
        confidence = _confidence(
            mentions=int(fan_row.get("mention_count") or 0),
            authors=int(fan_row.get("unique_author_count") or 0),
            sarcasm_risk=sarcasm_risk,
        )

        prior = prior_fan.get((team_id, "fan")) or prior_fan.get((team_id, "all"))
        delta = None
        if prior and prior.get("mean_sentiment_score") is not None:
            prior_belief = _belief_from_row(prior)
            delta = belief["score"] - prior_belief["score"]

        if delta is not None:
            vibe_shifts.append(
                _board_row(
                    team_meta,
                    headline=_delta_headline(delta),
                    subtext=f"{belief['label']} • {confidence['label']} confidence",
                    sort_value=abs(delta),
                    signed_value=delta,
                )
            )

        national_row = buckets.get("national")
        if national_row and int(national_row.get("mention_count") or 0) >= MIN_MENTIONS_FOR_SIGNAL:
            national_belief = _belief_from_row(national_row)
            gap_value = belief["score"] - national_belief["score"]
            if gap_value >= 10:
                respect_gap_leaders.append(
                    _board_row(
                        team_meta,
                        headline=f"+{int(round(gap_value))} fan vs national",
                        subtext=f"Fans say {belief['label'].lower()}; outsiders say {national_belief['label'].lower()}.",
                        sort_value=gap_value,
                        signed_value=gap_value,
                    )
                )
            elif gap_value <= -10:
                respect_gap_doubters.append(
                    _board_row(
                        team_meta,
                        headline=f"{int(round(gap_value))} fan vs national",
                        subtext=f"National chatter is hotter on them than their own fans.",
                        sort_value=abs(gap_value),
                        signed_value=gap_value,
                    )
                )

        rival_row = buckets.get("rival")
        if rival_row:
            rh = _rival_heat(rival_row)
            if rh and rh.get("score") is not None and float(rh["score"]) >= 0.35:
                rival_heat_leaders.append(
                    _board_row(
                        team_meta,
                        headline=rh["label"],
                        subtext=f"{int(rival_row.get('mention_count') or 0)} rival mentions this week.",
                        sort_value=float(rh["score"]),
                        signed_value=float(rh["score"]),
                    )
                )

        attention = float(fan_row.get("attention_score") or 0.0)
        if national_row:
            attention += float(national_row.get("attention_score") or 0.0) * 1.25
        if rival_row:
            attention += float(rival_row.get("attention_score") or 0.0) * 0.75
        main_characters.append(
            _board_row(
                team_meta,
                headline=f"{attention:.1f} attention",
                subtext=f"Fan, national, and rival chatter combined.",
                sort_value=attention,
                signed_value=attention,
            )
        )

        # Panic = combined fear+anger ("unease"). Both are negative-arousal
        # emotions; treating them as one signal matches how readers perceive
        # an anxious fanbase. Threshold 0.06 reflects the actual distribution
        # of the emotion classifier's output (fear alone p90 ≈ 0.03; combined
        # fear+anger p90 ≈ 0.10). The trajectory condition (mood flat or down)
        # keeps celebratory anger out — a fanbase angrily celebrating a win
        # has a positive delta and is filtered out here.
        fear_share = float(fan_row.get("fear_share") or 0.0)
        anger_share = float(fan_row.get("anger_share") or 0.0)
        unease_share = fear_share + anger_share
        if unease_share >= 0.06 and (delta is None or delta <= 0):
            dominant = "Fear" if fear_share >= anger_share else "Anger"
            panicked_fanbases.append(
                _board_row(
                    team_meta,
                    headline=f"{int(round(unease_share * 100))}% fear/anger share",
                    subtext=f"Dominant negative emotion: {dominant} ({int(round(max(fear_share, anger_share) * 100))}%)",
                    sort_value=unease_share,
                    signed_value=unease_share,
                )
            )

        if cohesion["score"] >= 0.40:
            polarized.append(
                _board_row(
                    team_meta,
                    headline=cohesion["label"],
                    subtext=f"Belief: {belief['label']} • {confidence['label']} confidence",
                    sort_value=cohesion["score"],
                    signed_value=cohesion["score"],
                )
            )

    vibe_shifts.sort(key=lambda r: r["sort_value"], reverse=True)
    respect_gap_leaders.sort(key=lambda r: r["sort_value"], reverse=True)
    respect_gap_doubters.sort(key=lambda r: r["sort_value"], reverse=True)
    rival_heat_leaders.sort(key=lambda r: r["sort_value"], reverse=True)
    main_characters.sort(key=lambda r: r["sort_value"], reverse=True)
    panicked_fanbases.sort(key=lambda r: r["sort_value"], reverse=True)
    polarized.sort(key=lambda r: r["sort_value"], reverse=True)

    has_data = bool(
        vibe_shifts
        or respect_gap_leaders
        or respect_gap_doubters
        or rival_heat_leaders
        or main_characters
        or panicked_fanbases
    )

    return {
        "has_data": has_data,
        "season_year": season_year,
        "week": week,
        "vibe_shifts": vibe_shifts[:6],
        "respect_gap_leaders": respect_gap_leaders[:6],
        "respect_gap_doubters": respect_gap_doubters[:6],
        "rival_heat_leaders": rival_heat_leaders[:6],
        "main_characters": main_characters[:6],
        "panicked_fanbases": panicked_fanbases[:6],
        "polarized": polarized[:6],
    }


# ---------------------------------------------------------------------------
# Axis computations
# ---------------------------------------------------------------------------


def _belief_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """Compose a -100..+100 belief band from a weekly conversation row."""

    net = float(row.get("net_sentiment_score") or 0.0)
    mean = float(row.get("mean_sentiment_score") or 0.0)
    trust = float(row.get("trust_share") or 0.0)
    fear = float(row.get("fear_share") or 0.0)
    joy = float(row.get("joy_share") or 0.0)
    anger = float(row.get("anger_share") or 0.0)

    mentions = max(1, int(row.get("mention_count") or 0))
    pos = int(row.get("positive_doc_count") or 0)
    neg = int(row.get("negative_doc_count") or 0)
    sentiment_balance = (pos - neg) / mentions

    composite = 0.55 * net + 0.20 * (trust - fear) + 0.10 * (joy - anger) + 0.15 * sentiment_balance
    score = max(-100.0, min(100.0, composite * 100.0))

    label = _belief_label(score)
    return {
        "score": round(score, 1),
        "label": label,
        "narrative": _belief_narrative(label, score),
    }


def _belief_label(score: float) -> str:
    if score >= 45:
        return "Very Bullish"
    if score >= 20:
        return "Bullish"
    if score >= 5:
        return "Cautiously Hopeful"
    if score > -5:
        return "Mixed"
    if score > -20:
        return "Uneasy"
    if score > -45:
        return "Bearish"
    return "Doomposting"


def _belief_narrative(label: str, score: float) -> str:
    if label == "Very Bullish":
        return "Fans are publicly calling their shot."
    if label == "Bullish":
        return "The room is leaning hopeful, not delirious."
    if label == "Cautiously Hopeful":
        return "Believers are there, but they are quiet about it."
    if label == "Mixed":
        return "Every take has a counter-take right under it."
    if label == "Uneasy":
        return "The mood is jittery more than angry."
    if label == "Bearish":
        return "Fans are writing their own obituaries."
    return "The fanbase is in the doom spiral."


def _reality_gap(belief: dict[str, Any], context: MoodContext) -> dict[str, Any]:
    if context.power_percentile is None:
        return {
            "available": False,
            "label": "Not enough structure signal",
            "score": None,
            "narrative": "We need a locked power percentile to compare against.",
        }

    belief_percentile = (belief["score"] + 100.0) / 2.0  # map -100..100 → 0..100
    # power_percentile is ALREADY a 0..100 percentile (reporting._rank_percentile
    # returns 0..100); do NOT multiply by 100 again, or the gap is ~always huge-
    # negative and every team reads "Doomer Ball".
    structural = float(context.power_percentile)
    gap = belief_percentile - structural

    if gap >= 22:
        label = "Hype Train"
        narrative = "Fans are out in front of what the model sees on the field."
    elif gap >= 8:
        label = "A Little Ahead Of The Evidence"
        narrative = "Belief is slightly warmer than the structure suggests."
    elif gap > -8:
        label = "Grounded"
        narrative = "Belief lines up with how good this team actually looks."
    elif gap > -22:
        label = "A Little Too Low"
        narrative = "Fans are underselling a team the model still likes."
    else:
        label = "Doomer Ball"
        narrative = "Fans are way below where the structure has this team."

    return {
        "available": True,
        "label": label,
        "score": round(gap, 1),
        "belief_percentile": round(belief_percentile, 1),
        "structural_percentile": round(structural, 1),
        "narrative": narrative,
    }


def _respect_gap(belief: dict[str, Any], national_belief: dict[str, Any] | None) -> dict[str, Any]:
    if not national_belief:
        return {
            "available": False,
            "label": "National sample still thin",
            "score": None,
            "narrative": "We do not have enough outsider chatter this week to compare.",
        }

    gap = belief["score"] - national_belief["score"]
    if gap >= 15:
        label = "Fans hotter than the country"
        narrative = "The home fanbase is out ahead of the national mood."
    elif gap <= -15:
        label = "Country hotter than the fans"
        narrative = "Outsiders are hyping this team more than its own fans."
    elif abs(gap) <= 5:
        label = "Room is aligned"
        narrative = "Fans and outsiders are reading this team the same way."
    else:
        label = "Slight disagreement"
        narrative = "A small gap between how fans and outsiders are talking."

    return {
        "available": True,
        "label": label,
        "score": round(gap, 1),
        "fan_score": belief["score"],
        "national_score": national_belief["score"],
        "narrative": narrative,
    }


def _cohesion_from_row(row: dict[str, Any]) -> dict[str, Any]:
    mentions = max(1, int(row.get("mention_count") or 0))
    pos = int(row.get("positive_doc_count") or 0) / mentions
    neg = int(row.get("negative_doc_count") or 0) / mentions
    neu = max(0.0, 1.0 - pos - neg)
    polarization = 4.0 * pos * neg
    entropy = 0.0
    for share in (pos, neu, neg):
        if share > 0:
            entropy -= share * math.log(share, 3)  # base 3 → 0..1

    disagreement = 0.7 * polarization + 0.3 * entropy
    if disagreement >= 0.65:
        label = "Civil War"
        narrative = "The fanbase is fighting itself in public."
    elif disagreement >= 0.45:
        label = "Split"
        narrative = "There is no consensus in the room."
    elif disagreement >= 0.25:
        label = "Tense"
        narrative = "Low-grade disagreement bubbling under the surface."
    else:
        label = "United"
        narrative = "The fanbase is reading this moment the same way."

    return {
        "score": round(disagreement, 3),
        "label": label,
        "narrative": narrative,
        "positive_share": round(pos, 3),
        "neutral_share": round(neu, 3),
        "negative_share": round(neg, 3),
    }


def _swing_from_history(history: list[dict[str, Any]], current_belief: float) -> dict[str, Any]:
    scores: list[float] = []
    if history:
        # history arrives newest→oldest (order by week desc); reverse to
        # chronological so adjacent deltas are true consecutive weeks and the
        # week-over-week delta compares against the immediately prior week (not
        # the oldest week in the window).
        scores = [_belief_from_row(row)["score"] for row in reversed(history)]
    scores.append(current_belief)

    if len(scores) < 2:
        return {
            "available": False,
            "score": None,
            "label": "Warming up",
            "narrative": "We need a few more weekly snapshots before the swing meter is trustworthy.",
        }

    deltas = [abs(b - a) for a, b in zip(scores[:-1], scores[1:])]
    volatility = sum(deltas) / len(deltas)

    if volatility >= 25:
        label = "Full Roller Coaster"
        narrative = "The fanbase mood whips back and forth every week."
    elif volatility >= 15:
        label = "Swingy"
        narrative = "Results move the mood more than most fanbases."
    elif volatility >= 7:
        label = "Reactive"
        narrative = "Small week-over-week moves, nothing wild."
    else:
        label = "Steady"
        narrative = "The mood barely moves, win or lose."

    most_recent_delta = scores[-1] - scores[-2] if len(scores) >= 2 else 0.0

    return {
        "available": True,
        "score": round(volatility, 1),
        "label": label,
        "narrative": narrative,
        "week_over_week_delta": round(most_recent_delta, 1),
    }


def _rival_heat(rival_row: dict[str, Any] | None) -> dict[str, Any]:
    if not rival_row:
        return {
            "available": False,
            "score": None,
            "label": "Rivals are quiet",
            "narrative": "We have not seen rival fanbases post about this team this week.",
        }

    mentions = int(rival_row.get("mention_count") or 0)
    if mentions < MIN_MENTIONS_FOR_SIGNAL:
        return {
            "available": False,
            "score": None,
            "label": "Low rival signal",
            "narrative": "Too few rival posts to publish a confident read yet.",
        }

    attention = float(rival_row.get("attention_score") or 0.0)
    negativity = float(rival_row.get("negative_doc_count") or 0.0) / max(1, mentions)
    anger = float(rival_row.get("anger_share") or 0.0)
    fear = float(rival_row.get("fear_share") or 0.0)
    # Weight attention and hostility together, but do not collapse fear into mockery.
    heat = min(1.0, 0.45 * min(1.0, attention / 5.0) + 0.35 * negativity + 0.20 * max(anger, fear))

    if heat >= 0.7:
        label = "Rent Free"
    elif heat >= 0.5:
        label = "High"
    elif heat >= 0.3:
        label = "Moderate"
    else:
        label = "Low"

    return {
        "available": True,
        "score": round(heat, 3),
        "label": label,
        "mentions": mentions,
        "narrative": "Rivals are generating real heat about this team." if heat >= 0.5 else "Some rival noise, nothing dominant.",
    }


def _archetype(belief: dict[str, Any], reality_gap: dict[str, Any], swing: dict[str, Any], cohesion: dict[str, Any]) -> str:
    if cohesion["score"] >= 0.55:
        return "Civil War"
    if swing.get("available") and (swing.get("score") or 0) >= 22:
        return "Roller Coaster"
    if reality_gap.get("available"):
        gap = reality_gap["score"] or 0
        if belief["score"] >= 15 and gap >= 18:
            return "Hype Train"
        if belief["score"] <= -15 and gap <= -18:
            return "Too Low On Ourselves"
        if belief["score"] >= 15 and abs(gap) <= 10:
            return "Grounded Believers"
        if belief["score"] <= -15 and abs(gap) <= 10:
            return "Scarred But Sane"
        if belief["score"] <= -25 and gap <= -5:
            return "Doomer Ball"
    if belief["score"] >= 10:
        return "Quietly Bullish"
    if belief["score"] <= -10:
        return "Jittery"
    return "Reading The Room"


# ---------------------------------------------------------------------------
# Confidence and sarcasm risk
# ---------------------------------------------------------------------------


def _sarcasm_risk_from_row(fan_row: dict[str, Any] | None, rival_row: dict[str, Any] | None) -> str:
    """Tier-3 confidence gate. If rival share is comparable to fan share AND
    fan sentiment is strongly positive, something weird is going on."""

    if not fan_row:
        return "low"
    fan_mentions = int(fan_row.get("mention_count") or 0)
    if fan_mentions <= 0:
        return "low"
    rival_mentions = int((rival_row or {}).get("mention_count") or 0)
    net = float(fan_row.get("net_sentiment_score") or 0.0)
    joy = float(fan_row.get("joy_share") or 0.0)
    surprise = float(fan_row.get("surprise_share") or 0.0)

    # Top-line sarcasm heuristics: strong positive while rivals are swarming is
    # suspicious, and abnormally high surprise share often reads as "we are so
    # back" energy.
    risk = 0.0
    if net >= 0.45 and rival_mentions >= fan_mentions * 0.6:
        risk += 0.35
    if joy >= 0.35 and surprise >= 0.15:
        risk += 0.20
    if net <= -0.45 and joy >= 0.2:
        risk += 0.20  # "great, just great" energy

    if risk >= 0.4:
        return "high"
    if risk >= 0.2:
        return "medium"
    return "low"


def _confidence(mentions: int, authors: int, sarcasm_risk: str) -> dict[str, Any]:
    base = min(1.0, mentions / MIN_MENTIONS_FOR_HIGH_CONFIDENCE)
    author_factor = min(1.0, authors / MIN_AUTHORS_FOR_HIGH_CONFIDENCE)
    composite = 0.7 * base + 0.3 * author_factor

    if sarcasm_risk == "high":
        composite *= 0.55
    elif sarcasm_risk == "medium":
        composite *= 0.80

    if composite >= 0.75 and sarcasm_risk != "high":
        label = "High"
    elif composite >= 0.45:
        label = "Medium"
    elif composite >= 0.20:
        label = "Low"
    else:
        label = "Very Low"

    return {
        "label": label,
        "score": round(composite, 3),
        "sarcasm_risk": sarcasm_risk,
    }


# ---------------------------------------------------------------------------
# Storylines
# ---------------------------------------------------------------------------


def _fetch_storylines(db: Database, team_id: int, season_year: int, week: int) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select
          storyline_rank,
          storyline_label,
          storyline_summary,
          keywords_json,
          representative_source_urls_json,
          sample_document_count,
          audience_bucket,
          window_label
        from conversation_storylines
        where team_id = %(team_id)s
          and season_year = %(season_year)s
          and week = %(week)s
        order by storyline_rank asc
        limit 6
        """,
        {"team_id": team_id, "season_year": season_year, "week": week},
    )
    results: list[dict[str, Any]] = []
    for row in rows:
        keywords: list[str] = []
        try:
            parsed = json.loads(row.get("keywords_json") or "[]")
            if isinstance(parsed, list):
                keywords = [str(k) for k in parsed if k]
        except (TypeError, ValueError):
            keywords = []
        urls: list[str] = []
        try:
            parsed_urls = json.loads(row.get("representative_source_urls_json") or "[]")
            if isinstance(parsed_urls, list):
                urls = [str(u) for u in parsed_urls if u]
        except (TypeError, ValueError):
            urls = []
        results.append(
            {
                "rank": int(row.get("storyline_rank") or 0),
                "label": str(row.get("storyline_label") or "Unlabeled storyline"),
                "summary": row.get("storyline_summary") or "",
                "keywords": keywords[:6],
                "urls": urls[:3],
                "sample_count": int(row.get("sample_document_count") or 0),
                "bucket": str(row.get("audience_bucket") or "all"),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def _fetch_weekly_bucket(
    db: Database,
    team_id: int,
    season_year: int,
    week: int,
    bucket: str,
) -> dict[str, Any] | None:
    # Thin wrapper around the scope-aware fetch for backward compatibility
    # with callers that think in team-only terms.
    return _fetch_weekly_bucket_scoped(
        db, scope="team", entity_id=team_id,
        season_year=season_year, week=week, bucket=bucket,
    )


_SCOPE_TABLES = {
    "team": ("team_week_conversation_features", "team_id"),
    "player": ("player_week_conversation_features", "player_id"),
}


def _fetch_weekly_bucket_scoped(
    db: Database,
    *,
    scope: str,
    entity_id: int,
    season_year: int,
    week: int,
    bucket: str,
) -> dict[str, Any] | None:
    """Look up one weekly-bucket row for either a team or a player.

    `scope='team'` reads `team_week_conversation_features`; `scope='player'`
    reads `player_week_conversation_features`. Both tables carry the same
    sentiment/emotion columns (plus `sarcasm_risk` and `top_quote_json` on
    the player side), so downstream row-shape consumers work unchanged.
    """
    table, id_col = _SCOPE_TABLES[scope]
    return db.query_one(
        f"""
        select *
        from {table}
        where {id_col} = %(entity_id)s
          and season_year = %(season_year)s
          and week = %(week)s
          and audience_bucket = %(bucket)s
        order by
          case when source_name = 'all' then 0 else 1 end,
          mention_count desc,
          source_name
        limit 1
        """,
        {
            "entity_id": entity_id,
            "season_year": season_year,
            "week": week,
            "bucket": bucket,
        },
    )


def _fetch_rival_bucket(
    db: Database,
    team_id: int,
    season_year: int,
    week: int,
) -> dict[str, Any] | None:
    # "rival" is the dominant incoming bucket from rival audiences; some rows
    # are stored under explicit rival keys, others under "opponent_fan" or
    # similar. We just take the best non-fan, non-national bucket if one
    # exists at the weekly granularity.
    return db.query_one(
        """
        select *
        from team_week_conversation_features
        where team_id = %(team_id)s
          and season_year = %(season_year)s
          and week = %(week)s
          and audience_bucket in ('rival', 'opponent_fan')
        order by
          case when source_name = 'all' then 0 else 1 end,
          mention_count desc,
          source_name
        limit 1
        """,
        {"team_id": team_id, "season_year": season_year, "week": week},
    )


def _fetch_belief_history(
    db: Database,
    team_id: int,
    season_year: int,
    week: int,
    window: int = 5,
) -> list[dict[str, Any]]:
    return _fetch_belief_history_scoped(
        db, scope="team", entity_id=team_id,
        season_year=season_year, week=week, window=window,
    )


def _fetch_belief_history_scoped(
    db: Database,
    *,
    scope: str,
    entity_id: int,
    season_year: int,
    week: int,
    window: int = 5,
) -> list[dict[str, Any]]:
    table, id_col = _SCOPE_TABLES[scope]
    return db.query_all(
        f"""
        select *
        from (
          select
            f.*,
            row_number() over (
              partition by f.week
              order by
                case when f.source_name = 'all' then 0 else 1 end,
                f.mention_count desc,
                f.source_name
            ) as row_priority
          from {table} f
          where f.{id_col} = %(entity_id)s
            and f.season_year = %(season_year)s
            and f.week < %(week)s
            and f.audience_bucket = 'fan'
        ) ranked
        where row_priority = 1
        order by week desc
        limit %(window)s
        """,
        {
            "entity_id": entity_id,
            "season_year": season_year,
            "week": week,
            "window": int(window),
        },
    )


def _fetch_all_weekly_features(
    db: Database,
    season_year: int,
    week: int,
) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select *
        from (
          select
            twcf.*,
            row_number() over (
              partition by twcf.team_id, twcf.audience_bucket
              order by
                case when twcf.source_name = 'all' then 0 else 1 end,
                twcf.mention_count desc,
                twcf.source_name
            ) as row_priority
          from team_week_conversation_features twcf
          where twcf.season_year = %(season_year)s
            and twcf.week = %(week)s
        ) ranked
        where row_priority = 1
        """,
        {"season_year": season_year, "week": week},
    )


# ---------------------------------------------------------------------------
# Empty / fallback states
# ---------------------------------------------------------------------------


def _empty_profile(
    *,
    team_id: int,
    season_year: int,
    week: int,
    mention_count: int,
    author_count: int,
) -> dict[str, Any]:
    return {
        "has_data": False,
        "team_id": team_id,
        "season_year": season_year,
        "week": week,
        "confidence": {"label": "No signal", "score": 0.0, "sarcasm_risk": "low"},
        "sample": {
            "mentions": mention_count,
            "authors": author_count,
            "sarcasm_risk": "low",
            "national_mentions": 0,
            "rival_mentions": 0,
        },
        "belief": {"score": None, "label": None, "narrative": "We have not collected enough fan conversation to publish a pulse yet."},
        "reality_gap": {"available": False, "label": None, "score": None, "narrative": "Reality check lights up once fan sample clears publication gates."},
        "respect_gap": {"available": False, "label": None, "score": None, "narrative": "Respect Gap compares fan mood to outsider chatter."},
        "swing": {"available": False, "label": None, "score": None, "narrative": "The swing meter tracks how violently the mood moves week to week."},
        "cohesion": {"score": 0.0, "label": None, "narrative": "We flag internal civil wars once the sample is big enough to trust."},
        "rival_heat": {"available": False, "label": None, "score": None, "narrative": "Rival Heat tracks mockery, fear, and obsession from rival fanbases."},
        "archetype": None,
        "storylines": [],
        "updated_label": f"{cfb_week_label_for_window(date.today(), week, db=None)} conversation window",
    }


def _empty_board(*, season_year: int, week: int) -> dict[str, Any]:
    return {
        "has_data": False,
        "season_year": season_year,
        "week": week,
        "vibe_shifts": [],
        "respect_gap_leaders": [],
        "respect_gap_doubters": [],
        "rival_heat_leaders": [],
        "main_characters": [],
        "panicked_fanbases": [],
        "polarized": [],
    }


def _board_row(
    team_meta: dict[str, Any],
    *,
    headline: str,
    subtext: str,
    sort_value: float,
    signed_value: float,
) -> dict[str, Any]:
    return {
        "team_id": int(team_meta["team_id"]),
        "slug": team_meta.get("slug"),
        "team_name": team_meta.get("team_name"),
        "level_code": team_meta.get("level_code"),
        "conference": team_meta.get("conference_name"),
        "headline": headline,
        "subtext": subtext,
        "sort_value": float(sort_value),
        "signed_value": float(signed_value),
    }


def _delta_headline(delta: float) -> str:
    sign = "+" if delta >= 0 else ""
    return f"{sign}{int(round(delta))} belief shift"


def build_team_index(
    rankings: Iterable[Any],
    team_pages: Iterable[dict[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    """Produce a ``team_id -> meta`` lookup that the board builder needs.

    Accepts both a sequence of RankingRow objects and (optionally) a sequence of
    team_page dicts so we can prefer conference/level labels from the richer
    team_page payload when available.
    """

    index: dict[int, dict[str, Any]] = {}
    for row in rankings:
        team_id = int(getattr(row, "team_id"))
        conference = getattr(row, "conference_name", None)
        index[team_id] = {
            "team_id": team_id,
            "slug": getattr(row, "slug", None),
            "team_name": getattr(row, "team_name", None),
            "level_code": getattr(row, "level_code", None),
            "conference_name": conference,
            "power_percentile": getattr(row, "power_percentile", None),
            "resume_percentile": getattr(row, "resume_percentile", None),
        }
    for page in team_pages or []:
        ranking = page.get("ranking")
        if not ranking:
            continue
        team_id = int(getattr(ranking, "team_id"))
        meta = index.setdefault(team_id, {"team_id": team_id})
        team_row = page.get("team") or {}
        meta.setdefault("slug", getattr(ranking, "slug", None))
        meta.setdefault("team_name", getattr(ranking, "team_name", None))
        meta.setdefault("level_code", getattr(ranking, "level_code", None))
        conf = team_row.get("conference_name") or getattr(ranking, "conference_name", None)
        meta["conference_name"] = conf
        meta.setdefault("power_percentile", getattr(ranking, "power_percentile", None))
        meta.setdefault("resume_percentile", getattr(ranking, "resume_percentile", None))
    return index
