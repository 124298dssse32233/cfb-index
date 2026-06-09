"""Date- and archetype-aware re-labeling helper — Wave 25 / Module 5.

Replaces hardcoded "Current Season Production" / "2024 Stats" labels with
archetype-appropriate text. Critically takes `current_date` as a parameter
so the same code works in May 2026, November 2026, and May 2027 — no
literal year numbers in this module.

Public API:
    season_context_label(status_code, last_team_name, last_season_year,
                         current_team_name, current_date) -> str
    page_title_suffix(...)                                  -> str
"""
from __future__ import annotations

from datetime import date
from typing import Optional


def _upcoming_season(current_date: date) -> int:
    """Return the season year we're previewing toward."""
    if current_date.month >= 5:
        return current_date.year
    return current_date.year - 1


def _last_completed_season(current_date: date) -> int:
    """The most recent season whose stats are final."""
    if current_date.month >= 1 and current_date.month <= 7:
        return current_date.year - 1
    return current_date.year - 1


def season_context_label(
    status_code: str,
    last_team_name: Optional[str] = None,
    last_season_year: Optional[int] = None,
    current_team_name: Optional[str] = None,
    current_date: Optional[date] = None,
) -> str:
    """Return the section-header prefix for the retrospective stats surface."""
    today = current_date or date.today()
    last_season = last_season_year or _last_completed_season(today)

    if status_code == "RETURNING_2026" or status_code == "PORTAL_WITHDREW":
        return f"{last_season} season · last completed"
    if status_code == "TRANSFERRED_COLLEGE":
        if last_team_name:
            return f"{last_season} at {last_team_name} · final season there"
        return f"{last_season} season · final season at previous program"
    if status_code in ("NFL_DRAFTED_2026", "NFL_DRAFTED_PRIOR",
                       "NFL_UDFA", "EXHAUSTED_ELIGIBILITY",
                       "MEDICAL_RETIREMENT"):
        return f"{last_season} · final college season"
    if status_code == "PORTAL_OPEN":
        if last_team_name:
            return f"{last_season} at {last_team_name} · last season before portal"
        return f"{last_season} season · last season before portal"
    if status_code == "HISTORICAL_ALUM":
        return "College career stats"
    if status_code == "HS_RECRUIT_ONLY":
        return "Recruit profile"
    return f"{last_season} season"


def page_title_suffix(
    status_code: str,
    current_team_name: Optional[str] = None,
    position: Optional[str] = None,
    nfl_team: Optional[str] = None,
    last_team_name: Optional[str] = None,
    current_date: Optional[date] = None,
) -> str:
    """Return the suffix for the <title> tag, archetype-aware."""
    today = current_date or date.today()
    upcoming = _upcoming_season(today)
    pos = (position or "").upper() if position else ""
    team = current_team_name or last_team_name or ""

    if status_code == "RETURNING_2026":
        bits = [team]
        if pos:
            bits.append(pos)
        bits.append(f"{upcoming} Outlook")
        return " ".join(b for b in bits if b)
    if status_code == "TRANSFERRED_COLLEGE":
        bits = [team]
        if pos:
            bits.append(pos)
        bits.append(f"Transfer for {upcoming}")
        return " · ".join(b for b in bits if b)
    if status_code == "NFL_DRAFTED_2026":
        return f"{nfl_team or 'NFL'} · {upcoming} NFL Draft"
    if status_code == "NFL_DRAFTED_PRIOR":
        return f"{nfl_team or 'NFL'} · NFL"
    if status_code == "NFL_UDFA":
        return f"{nfl_team or 'NFL'} · UDFA"
    if status_code == "PORTAL_OPEN":
        return "In transfer portal"
    if status_code == "EXHAUSTED_ELIGIBILITY":
        return f"{last_team_name or 'CFB'} · career complete"
    if status_code == "MEDICAL_RETIREMENT":
        return f"{last_team_name or 'CFB'} · medical"
    if status_code == "HISTORICAL_ALUM":
        return f"{last_team_name or 'CFB'} alum"
    if status_code == "HS_RECRUIT_ONLY":
        return "Recruit"
    return "CFB"
