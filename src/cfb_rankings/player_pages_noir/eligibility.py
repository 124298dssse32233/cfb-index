"""Noir player-page rollout gate (plan doc 61 §4).

Two independent controls, BOTH must pass for a player to render Noir:
  1. operator switch  — env `NOIR_ROLLOUT_TIER` / `NOIR_PLAYER_SLUGS` (DEFAULT OFF)
  2. data eligibility — `is_noir_eligible(player_data)` minimum-viable-section floor
     (so the adaptive layout never ships a hollow page; below the floor we fall
     back to the legacy renderer, never a thin Noir page).

DEFAULT IS OFF. With no env set, `noir_enabled()` returns False for everyone and
the build is 100% legacy — this package is inert until explicitly switched on.
"""
from __future__ import annotations

import os
from typing import Any

# Tiers, lowest→highest coverage. "off" (default) disables Noir entirely.
_TIERS = ("off", "spike", "alpha", "beta", "fbs", "all")


def _tier() -> str:
    t = (os.environ.get("NOIR_ROLLOUT_TIER") or "off").strip().lower()
    return t if t in _TIERS else "off"


def _spike_slugs() -> set[str]:
    raw = os.environ.get("NOIR_PLAYER_SLUGS") or ""
    return {s.strip() for s in raw.split(",") if s.strip()}


def is_noir_eligible(player_data: dict[str, Any]) -> bool:
    """Minimum-viable-section floor: a Story Card (the Dossier spine) plus at least
    one real stat surface. Below this, the adaptive page would look hollow → legacy.
    Never raises."""
    try:
        has_dossier = bool((player_data.get("new_story_card_html") or "").strip())
        has_record = bool(
            (player_data.get("season_stat_tables") or "")
            or (player_data.get("new_game_log_html") or "").strip()
        )
        return has_dossier and has_record
    except Exception:
        return False


def noir_enabled(player_slug: str, player_data: dict[str, Any]) -> bool:
    """Operator switch AND data eligibility. DEFAULT OFF (no env → False)."""
    tier = _tier()
    if tier == "off":
        return False
    if tier == "spike":
        return player_slug in _spike_slugs() and is_noir_eligible(player_data)
    # alpha/beta/fbs/all cohorts are resolved by the caller's data; here we only
    # require data-eligibility. Cohort narrowing (story-card cohort, top-N, FBS)
    # is applied by noir_cohort_slugs() so the build guard and renderer agree.
    return is_noir_eligible(player_data)
