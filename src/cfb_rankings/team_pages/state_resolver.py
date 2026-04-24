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
        }


def resolve_state(
    profile: Profile,
    snapshot: TeamSnapshot,
    today: date | None = None,
) -> PageState:
    today = today or date.today()
    phase = _MONTH_TO_PHASE.get(today.month, "early-season")
    dow_label = _DOW_LABEL[today.weekday()]
    is_in_season = today.month in (8, 9, 10, 11, 12) or (
        today.month == 1 and today.day <= 15
    )

    anchor, hero, tone, accent = _resolve_anchor(
        phase=phase,
        dow=today.weekday(),
        snapshot=snapshot,
        profile=profile,
        today=today,
    )

    # Program-tier-driven promotions / demotions.
    promoted, demoted = _tier_module_rules(profile.program_tier, snapshot)

    # Rivalry-week override: if the next game is listed in profile.rivalries
    # and kickoff is within 10 days, promote the rivalry card.
    rivalry = _detect_rivalry_this_week(profile, snapshot, today)
    if rivalry is not None and is_in_season:
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
    )


def _resolve_anchor(
    *,
    phase: str,
    dow: int,
    snapshot: TeamSnapshot,
    profile: Profile,
    today: date,
) -> tuple[str, str, str, str]:
    """Return (anchor_variant, hero_priority, copy_tone, accent_key).

    The 10-12 named anchors from the iteration log, with outcome overrides.
    """
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
