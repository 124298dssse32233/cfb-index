"""State resolver: date + last-game outcome + tier + profile → PageState.

This is the seasonal-sentience layer from the Iteration Log:

    Three parameters drive every state
      1. hero_priority — which module claims the top slot
      2. copy_tone — which voice-template draws the state-of-team paragraph
      3. accent_color — the emotional key

Plus program-tier sentience:

    Every module has variant axes. Among them, program_tier reshapes
    which modules render at all (Alabama gets CFP math; UMass gets
    bowl-eligibility math).

Resolution order:
    1. Base on season phase (in-season vs offseason, day-of-week).
    2. Apply outcome override (post-win / post-loss / post-upset).
    3. Apply rivalry-week override.
    4. Apply profile-driven overrides (dynasty vs scrappy-proud shift copy
       tone priors).

The PageState is passed to the renderer; it is the single object that
encodes everything needed to render a coherent moment-in-time page.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .data import TeamSnapshot, GameResult
from .profile_loader import Profile


# ----- Anchor + tone tables --------------------------------------------------

# Seasonal month → phase enum. Matches Iteration Log annual cycle.
_MONTH_TO_PHASE = {
    1: "bowl-and-carousel",
    2: "nsd-and-portal",
    3: "spring-and-portal",
    4: "spring-and-portal",
    5: "dead-period-heritage",
    6: "dead-period-heritage",
    7: "media-days",
    8: "camp",
    9: "early-season",
    10: "stakes-rising",
    11: "rivalry-peak",
    12: "cfp-selection-and-bowl",
}

# Day-of-week rhythm (used only in-season).
_DOW_LABEL = {
    0: "licking-wounds-or-basking",    # Mon
    1: "depth-chart-injuries",         # Tue
    2: "matchup-sharpens",             # Wed
    3: "hype-peaks",                   # Thu
    4: "anticipation",                 # Fri
    5: "gameday",                      # Sat
    6: "autopsy",                      # Sun
}


@dataclass
class PageState:
    today: date
    season_year: int
    season_phase: str
    day_of_week_label: str
    is_in_season: bool
    anchor_variant: str              # e.g. 'dead-period-summer', 'standard-friday'
    hero_priority: str               # e.g. 'season-theater', 'rivalry-card', 'heritage', 'on-this-day'
    copy_tone: str                   # e.g. 'basking', 'reckoning', 'patient', 'coiled', 'resolute'
    accent_key: str                  # 'red' | 'amber' | 'navy' | 'gray' | 'coral' | 'green'
    program_tier: int
    voice_register: str
    tonal_template: str
    demoted_modules: list[str] = field(default_factory=list)
    promoted_modules: list[str] = field(default_factory=list)
    rivalry_this_week: dict[str, Any] | None = None
    last_outcome: str | None = None   # 'W' | 'L' | None
    last_margin: int | None = None
    narrative_context_lines: list[str] = field(default_factory=list)
    # Sprint 6 — Live Gameday extensions
    outcome_category: str | None = None     # 'win-clear' | 'win-upset' | 'loss-close' | 'loss-blowout' | 'loss-upset' | None
    pre_game_spread: float | None = None    # negative = team favored; positive = team underdog (points)
    hours_since_final: float | None = None  # only set when last game was within last 72h
    game_recap_active: bool = False         # True iff we should swap in GameRecapHero
    game_id: int | None = None              # the just-ended game row in games_live or games

    def as_dict(self) -> dict[str, Any]:
        """Flat dict for storing as state_signature JSON."""
        return {
            "today": self.today.isoformat(),
            "season_year": self.season_year,
            "season_phase": self.season_phase,
            "day_of_week": self.day_of_week_label,
            "is_in_season": self.is_in_season,
            "anchor_variant": self.anchor_variant,
            "hero_priority": self.hero_priority,
            "copy_tone": self.copy_tone,
            "accent_key": self.accent_key,
            "program_tier": self.program_tier,
            "voice_register": self.voice_register,
            "tonal_template": self.tonal_template,
            "last_outcome": self.last_outcome,
            "last_margin": self.last_margin,
            "outcome_category": self.outcome_category,
            "pre_game_spread": self.pre_game_spread,
            "hours_since_final": self.hours_since_final,
            "game_recap_active": self.game_recap_active,
            "game_id": self.game_id,
        }


def resolve_state(
    profile: Profile,
    snapshot: TeamSnapshot,
    today: date | None = None,
    *,
    live_game_meta: dict[str, Any] | None = None,
) -> PageState:
    """Resolve the page-state for a (profile, snapshot) at a given date.

    ``live_game_meta`` is an optional dict carrying live-gameday state from
    ``games_live`` (or simulate-game). When present and ``status='final'`` with
    ``final_at`` within the last 24h, the resolver flips into a
    ``game-recap-<outcome_category>`` anchor and sets ``game_recap_active=True``.

    Expected keys (all optional):
        game_id, status, final_at (ISO8601), home_team_slug, away_team_slug,
        home_score, away_score, pre_game_spread (float; negative = home favored
        by abs(spread)), simulated (bool).
    """
    today = today or date.today()
    phase = _MONTH_TO_PHASE.get(today.month, "early-season")
    dow_label = _DOW_LABEL[today.weekday()]
    is_in_season = today.month in (8, 9, 10, 11, 12) or (
        today.month == 1 and today.day <= 15
    )

    # Sprint 6 — outcome category & live-game derivation.
    outcome_category, pre_game_spread, hours_since_final, game_id, game_recap_active = (
        _derive_live_game_state(profile, snapshot, today, live_game_meta)
    )

    anchor, hero, tone, accent = _resolve_anchor(
        phase=phase,
        dow=today.weekday(),
        snapshot=snapshot,
        profile=profile,
        today=today,
        outcome_category=outcome_category,
        hours_since_final=hours_since_final,
        game_recap_active=game_recap_active,
    )

    # Program-tier-driven promotions / demotions.
    promoted, demoted = _tier_module_rules(profile.program_tier, snapshot)

    # Rivalry-week override: if the next game is listed in profile.rivalries
    # and kickoff is within 10 days, promote the rivalry card. Skipped when
    # game-recap is active — that hero claims the page for 24h regardless.
    rivalry = _detect_rivalry_this_week(profile, snapshot, today)
    if rivalry is not None and is_in_season and not game_recap_active:
        hero = "rivalry-card"
        accent = rivalry.get("accent_color", accent)
        promoted = ["rivalry-card"] + [m for m in promoted if m != "rivalry-card"]

    context_lines = _build_context_lines(snapshot, profile, today)
    last_out = snapshot.last_game.outcome if snapshot.last_game else None
    last_margin = snapshot.last_game.margin if snapshot.last_game else None

    return PageState(
        today=today,
        season_year=snapshot.season_year,
        season_phase=phase,
        day_of_week_label=dow_label,
        is_in_season=is_in_season,
        anchor_variant=anchor,
        hero_priority=hero,
        copy_tone=tone,
        accent_key=accent,
        program_tier=profile.program_tier,
        voice_register=profile.voice_register,
        tonal_template=profile.tonal_template,
        promoted_modules=promoted,
        demoted_modules=demoted,
        rivalry_this_week=rivalry,
        last_outcome=last_out,
        last_margin=last_margin,
        narrative_context_lines=context_lines,
        outcome_category=outcome_category,
        pre_game_spread=pre_game_spread,
        hours_since_final=hours_since_final,
        game_recap_active=game_recap_active,
        game_id=game_id,
    )


def _resolve_anchor(
    *,
    phase: str,
    dow: int,
    snapshot: TeamSnapshot,
    profile: Profile,
    today: date,
    outcome_category: str | None = None,
    hours_since_final: float | None = None,
    game_recap_active: bool = False,
) -> tuple[str, str, str, str]:
    """Return (anchor_variant, hero_priority, copy_tone, accent_key).

    The 10-12 named anchors from the iteration log, with outcome overrides
    plus Sprint 6 game-recap variants when ``game_recap_active`` is set.
    """
    # Sprint 6 — game-recap mode trumps season phase for the first 24h.
    if game_recap_active and outcome_category is not None:
        return _resolve_game_recap_anchor(outcome_category)

    # Sprint 6 — soft post-game window (24-72h): keep state-of-team but
    # signal that game-edition Chronicle cards remain pinned.
    if outcome_category is not None and hours_since_final is not None and 24 <= hours_since_final <= 72:
        tone, accent = _post_game_24_72h_register(outcome_category)
        return ("post-game-monday-tuesday", "pulse", tone, accent)

    if phase == "dead-period-heritage":
        return ("dead-period-summer", "heritage", "patient", "gray")
    if phase == "media-days":
        return ("media-days", "on-this-day", "optimistic", "navy")
    if phase == "camp":
        return ("camp-open", "season-theater", "optimistic", "green")
    if phase in ("spring-and-portal", "nsd-and-portal"):
        return (
            "portal-window-active",
            "portal-tracker",
            _spring_tone_by_register(profile.voice_register),
            "navy",
        )
    if phase == "bowl-and-carousel":
        return ("bowl-and-carousel", "heritage", "basking", "navy")

    # In-season branches
    last = snapshot.last_game
    if last is None:
        return ("camp-open", "season-theater", "optimistic", "green")

    # Post-loss vs post-win override (Sun/Mon)
    if dow in (6, 0) and last.outcome in ("W", "L"):
        if last.outcome == "L":
            tone = "reckoning" if (last.margin or 0) > -14 else "wound"
            return ("post-loss-sunday-monday", "pulse", tone, "red")
        else:
            return ("post-win-sunday-monday", "season-theater", "basking", "green")

    if phase == "rivalry-peak" and dow >= 3:
        return ("rivalry-week-friday", "rivalry-card", "coiled", "amber")
    if dow == 4:
        return ("standard-friday", "season-theater", "anticipatory", "amber")
    if dow == 5:
        return ("gameday-pre-kickoff", "season-theater", "coiled", "amber")

    tone = _midweek_tone(profile, snapshot)
    return ("standard-in-season-midweek", "season-theater", tone, "navy")


# ----- Sprint 6 — game-recap anchor map -------------------------------------

# (anchor_variant, copy_tone, accent_key) per outcome category. The accent
# values feed the GameRecapHero modulator via _outcome_accent_hex().
_GAME_RECAP_ANCHORS: dict[str, tuple[str, str, str]] = {
    "win-clear":   ("game-recap-win-clear",   "confident",   "green"),
    "win-upset":   ("game-recap-win-upset",   "vindicated",  "amber"),
    "loss-close":  ("game-recap-loss-close",  "reckoning",   "coral"),
    "loss-blowout":("game-recap-loss-blowout","wound",       "red"),
    "loss-upset":  ("game-recap-loss-upset",  "crisis",      "red"),
}


def _resolve_game_recap_anchor(outcome_category: str) -> tuple[str, str, str, str]:
    """Map outcome_category to (anchor, hero, tone, accent) for game-recap mode."""
    anchor, tone, accent = _GAME_RECAP_ANCHORS.get(
        outcome_category,
        ("game-recap-loss-close", "reckoning", "coral"),
    )
    # hero_priority is always 'game-recap' so the renderer knows to swap in
    # the GameRecapHero module instead of the standard hero.
    return (anchor, "game-recap", tone, accent)


def _post_game_24_72h_register(outcome_category: str) -> tuple[str, str]:
    """Tone + accent for the 24-72h post-game window (state-of-team returns,
    game-edition Chronicle cards remain pinned but no longer dominate)."""
    return {
        "win-clear":    ("basking",     "green"),
        "win-upset":    ("vindicated",  "amber"),
        "loss-close":   ("reckoning",   "coral"),
        "loss-blowout": ("wound",       "red"),
        "loss-upset":   ("crisis",      "red"),
    }.get(outcome_category, ("reckoning", "red"))


# ----- Sprint 6 — outcome derivation ----------------------------------------

def _derive_live_game_state(
    profile: Profile,
    snapshot: TeamSnapshot,
    today: date,
    live_game_meta: dict[str, Any] | None,
) -> tuple[str | None, float | None, float | None, int | None, bool]:
    """Compute (outcome_category, pre_game_spread, hours_since_final, game_id, game_recap_active).

    Resolution order:
      1. ``live_game_meta`` (passed by the renderer or simulate-game CLI)
         takes precedence — it carries the just-finalized game's score and
         freshness directly from games_live.
      2. Otherwise, derive from snapshot.last_game using its margin and best-
         available pre-game spread (from game_line_snapshots if any). The
         freshness window assumes the snapshot is from the previous Saturday.

    All five outcome categories require a non-zero margin and (for upset
    detection) a pre-game spread. If the spread is unknown, win-upset and
    loss-upset are NOT inferred — we degrade to win-clear / loss-close as a
    conservative default.
    """
    if live_game_meta and (live_game_meta.get("status") or "").lower() == "final":
        team_slug = profile.slug.lower()
        home_slug = (live_game_meta.get("home_team_slug") or "").lower()
        away_slug = (live_game_meta.get("away_team_slug") or "").lower()
        home_score = live_game_meta.get("home_score")
        away_score = live_game_meta.get("away_score")
        # The live row stores spread_home in 'pre_game_spread_home' (preferred)
        # or, when constructed by simulate-game, sometimes 'pre_game_spread'.
        spread_home = live_game_meta.get("pre_game_spread_home")
        if spread_home is None:
            spread_home = live_game_meta.get("pre_game_spread")

        if home_slug == team_slug:
            team_pts, opp_pts = home_score, away_score
            spread_for_team = float(spread_home) if spread_home is not None else None
        elif away_slug == team_slug:
            team_pts, opp_pts = away_score, home_score
            # spread_home convention flips for the away team.
            spread_for_team = (-1.0 * float(spread_home)) if spread_home is not None else None
        else:
            return (None, None, None, None, False)

        if team_pts is None or opp_pts is None:
            return (None, None, None, None, False)
        margin = int(team_pts) - int(opp_pts)
        # Accept either 'final_at_utc' (DB column) or 'final_at' (legacy alias).
        final_iso = live_game_meta.get("final_at_utc") or live_game_meta.get("final_at")
        hours = _hours_since(final_iso, today)
        category = _classify_outcome(margin, spread_for_team)
        active = (hours is not None and hours <= 24)
        return (category, spread_for_team, hours, live_game_meta.get("game_id"), active)

    # Fallback to last_game on the snapshot.
    last = snapshot.last_game
    if last is None or last.outcome not in ("W", "L"):
        return (None, None, None, None, False)
    margin = last.margin or 0
    spread = None  # spread lookup deferred to the renderer when it has db
    hours = None  # without a final_at timestamp on the snapshot, can't say
    category = _classify_outcome(margin, spread)
    return (category, spread, hours, None, False)


def _classify_outcome(margin: int, pre_game_spread: float | None) -> str:
    """Return one of the 5 outcome categories given a final margin + spread.

    margin > 0 → team won; margin < 0 → team lost. ``pre_game_spread`` is
    expressed from the team's perspective: negative means the team was the
    favorite (e.g. -7.5 = laid 7.5). When the spread is unknown, only the
    margin-driven categories fire (win-clear / win-close→loss-close → blowout).
    """
    if margin > 0:
        # Team won. Was the team an underdog by ≥ 7? → win-upset.
        if pre_game_spread is not None and pre_game_spread >= 7.0:
            return "win-upset"
        if margin >= 10:
            return "win-clear"
        # Close win — register-wise 'win-clear' is the closest match; we
        # don't carry a 'win-close' variant in the 5-mode taxonomy.
        return "win-clear"

    # Team lost (margin < 0). Loss magnitude.
    abs_margin = abs(margin)
    # Loss-upset: opponent was favored by ≤ 3 points OR team was favored.
    # i.e. team's pre_game_spread <= 3.0 means the team was favored or
    # close to a pick'em.
    if pre_game_spread is not None and pre_game_spread <= 3.0:
        return "loss-upset"
    if abs_margin >= 14:
        return "loss-blowout"
    if abs_margin <= 7:
        return "loss-close"
    # 8-13 point loss with unknown / favorable spread defaults to close.
    return "loss-close"


def _hours_since(iso_ts: str | None, today: date) -> float | None:
    """Hours between an ISO timestamp and 'now'.

    ``today`` is accepted for signature compatibility but not used as the
    reference point — we compare against ``datetime.now(UTC)`` since
    freshness windows in this codebase are measured by wall-clock, not
    calendar-day boundaries. The renderer caller passes the production
    date for state-phase logic; for live-game freshness we want the
    real elapsed time.
    """
    if not iso_ts:
        return None
    from datetime import datetime, timezone
    try:
        # Permissive parser: accept naive or 'Z' suffixed strings.
        ts = iso_ts.replace("Z", "+00:00") if iso_ts.endswith("Z") else iso_ts
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    now_utc = datetime.now(timezone.utc)
    delta = now_utc - dt
    hours = delta.total_seconds() / 3600.0
    return max(0.0, hours)


def _spring_tone_by_register(register: str) -> str:
    return {
        "dynastic": "basking",
        "dynastic-with-question-mark": "patient",
        "defiant-academic": "resolute",
        "scrappy-proud": "optimistic",
    }.get(register, "patient")


def _midweek_tone(profile: Profile, snapshot: TeamSnapshot) -> str:
    """In-season midweek tone is calibrated to record × program tier."""
    total = snapshot.wins + snapshot.losses
    if total == 0:
        return "optimistic"
    win_pct = snapshot.wins / total
    tier = profile.program_tier
    if tier <= 2:  # blue blood / established P4
        if win_pct >= 0.75:
            return "expectant"
        if win_pct < 0.5:
            return "reckoning"
        return "resolute"
    if tier <= 5:
        if win_pct >= 0.7:
            return "optimistic"
        return "grinding"
    # G5 / bottom
    if win_pct >= 0.5:
        return "resolute"
    return "grinding"


def _tier_module_rules(tier: int, snapshot: TeamSnapshot) -> tuple[list[str], list[str]]:
    """Per-tier module promotion/demotion (Iteration Log §Program-tier sentience)."""
    promoted: list[str] = []
    demoted: list[str] = []
    if tier <= 2:
        promoted = ["cfp-math", "savant-card", "rivalry-card"]
        demoted = ["aspiration-ladder"]
    elif tier <= 5:
        promoted = ["aspiration-ladder", "season-theater", "savant-card"]
        demoted = ["cfp-math"]
    else:
        promoted = ["aspiration-ladder", "heritage", "rivalry-card"]
        demoted = ["cfp-math", "cfp-projection"]
    return promoted, demoted


def _detect_rivalry_this_week(
    profile: Profile,
    snapshot: TeamSnapshot,
    today: date,
) -> dict[str, Any] | None:
    if snapshot.next_game is None or not profile.rivalries:
        return None
    opp_slug = snapshot.next_game.opponent_slug
    opp_name = (snapshot.next_game.opponent_name or "").lower()
    for riv in profile.rivalries:
        riv_slug = str(riv.get("opponent_slug", "")).lower()
        riv_name = str(riv.get("opponent", "")).lower()
        if opp_slug and riv_slug and opp_slug == riv_slug:
            return dict(riv)
        if opp_name and riv_name and riv_name in opp_name:
            return dict(riv)
    return None


def _build_context_lines(
    snapshot: TeamSnapshot,
    profile: Profile,
    today: date,
) -> list[str]:
    """Plain-English bullet context used by narrative generator as prompt facts."""
    lines = []
    record = f"{snapshot.wins}-{snapshot.losses}" + (f"-{snapshot.ties}" if snapshot.ties else "")
    lines.append(f"{snapshot.season_year} record: {record}")
    if snapshot.ap_rank:
        lines.append(f"Latest AP rank: #{snapshot.ap_rank}")
    if snapshot.coaches_rank:
        lines.append(f"Coaches poll: #{snapshot.coaches_rank}")
    if snapshot.cfp_rank:
        lines.append(f"CFP committee rank: #{snapshot.cfp_rank}")
    if snapshot.last_game:
        g = snapshot.last_game
        lines.append(
            f"Last game: {g.outcome} {g.team_points}-{g.opp_points} "
            f"{'vs' if g.is_home else 'at'} {g.opponent_name} (Wk {g.week})"
        )
    if snapshot.next_game:
        n = snapshot.next_game
        lines.append(
            f"Next game: {'vs' if n.is_home else 'at'} {n.opponent_name} (Wk {n.week})"
        )
    if snapshot.season_complete:
        lines.append(
            f"Season complete. As of {today.isoformat()} the program is in "
            "the off-season: spring practice, portal window, NFL draft context."
        )
    lines.append(f"Program tier: {profile.program_tier}")
    lines.append(f"Voice register: {profile.voice_register}")
    lines.append(f"Tonal template: {profile.tonal_template}")
    if profile.identity_phrase:
        lines.append(f"Identity phrase: '{profile.identity_phrase}'")
    if profile.always_surface:
        lines.append("Always surface: " + "; ".join(_stringify_entries(profile.always_surface)))
    if profile.never_use:
        lines.append("Never use: " + "; ".join(_stringify_entries(profile.never_use)))
    return lines


def _stringify_entries(items: list) -> list[str]:
    """Coerce any non-string entries (dicts from YAML 'key: value' lines) to strings."""
    out: list[str] = []
    for it in items:
        if isinstance(it, str):
            out.append(it)
        elif isinstance(it, dict):
            out.extend(f"{k}: {v}" for k, v in it.items())
        else:
            out.append(str(it))
    return out
