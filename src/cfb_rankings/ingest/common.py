from __future__ import annotations

from datetime import datetime, timezone


FCS_CONFERENCES = {
    "Big Sky",
    "CAA Football",
    "Coastal Athletic Association",
    "Ivy",
    "MEAC",
    "Missouri Valley Football Conference",
    "MVFC",
    "Northeast",
    "NEC",
    "Ohio Valley",
    "OVC",
    "Patriot",
    "Pioneer",
    "SoCon",
    "Southern",
    "Southland",
    "SWAC",
    "United Athletic Conference",
    "UAC",
}


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(tz=timezone.utc)
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


def maybe_int(value: object) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def maybe_float(value: object) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_status(completed: bool | None, home_points: int | None, away_points: int | None) -> str:
    if completed or (home_points is not None and away_points is not None):
        return "Final"
    return "Scheduled"


def infer_cfbd_level(home_conference: str | None, away_conference: str | None) -> str:
    conferences = {home_conference or "", away_conference or ""}
    if any(conference in FCS_CONFERENCES for conference in conferences):
        return "FCS"
    return "FBS"


def normalize_cfbd_classification(value: str | None, fallback_conference: str | None = None) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "fbs":
        return "FBS"
    if normalized == "fcs":
        return "FCS"
    if normalized in {"ii", "d2", "division ii", "division 2"}:
        return "DII"
    if normalized in {"iii", "d3", "division iii", "division 3"}:
        return "DIII"
    if fallback_conference in FCS_CONFERENCES:
        return "FCS"
    return "FBS"


def normalize_season_phase(season_type: str | None, notes: str | None = None) -> str:
    normalized_type = (season_type or "").strip().lower()
    note_text = (notes or "").strip().lower()

    if normalized_type == "preseason":
        return "preseason"
    if normalized_type == "regular":
        return "regular season"

    if "conference championship" in note_text or "championship game" in note_text:
        return "conference championship"
    if "national championship" in note_text or "title game" in note_text:
        return "final"
    if "bowl" in note_text:
        return "bowl"
    if any(keyword in note_text for keyword in {"playoff", "semifinal", "quarterfinal", "first round", "second round"}):
        return "playoff"
    if normalized_type == "postseason":
        return "playoff"
    return "regular season"


def normalize_competition_week(
    season_year: int,
    season_type: str | None,
    week: int | None,
    start_time_utc: datetime | None = None,
) -> int:
    raw_week = week or 0
    normalized_type = (season_type or "").strip().lower()
    if normalized_type != "postseason":
        return raw_week

    # CFBD postseason week numbers are not monotonic across all divisions.
    # We keep the season on one continuous timeline by anchoring postseason
    # weeks to actual game dates relative to the end of the regular season.
    if start_time_utc is None:
        if raw_week >= 10:
            return raw_week
        return 16 + raw_week

    anchor_date = datetime(season_year, 12, 13, tzinfo=timezone.utc).date()
    delta_days = (start_time_utc.date() - anchor_date).days
    return 16 + (delta_days // 7)
