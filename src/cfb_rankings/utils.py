from __future__ import annotations

import math
import re
from typing import Iterable


LEVEL_ORDER = {"FBS": 1, "FCS": 2, "DII": 3, "DIII": 4}
DEFAULT_LEVEL_PRIORS = {"FBS": 0.0, "FCS": -11.5, "DII": -22.5, "DIII": -32.5}
DEFAULT_LEVEL_SIGMA = {"FBS": 4.5, "FCS": 5.5, "DII": 7.0, "DIII": 7.5}
PROGRAM_COUNT_REFERENCE_DATE = "April 20, 2026"
SUBDIVISION_PROGRAM_COUNTS = {
    "FBS": {
        "active_full_members": 134,
        "with_transitioning": 136,
        "label": "FBS",
    },
    "FCS": {
        "active_full_members": 128,
        "broad_sponsoring_count": 129,
        "label": "FCS",
    },
    "DII": {
        "football_programs": 161,
        "label": "Division II",
    },
    "DIII": {
        "football_programs": 239,
        "label": "Division III",
    },
}
OFFICIAL_SUBDIVISION_CONFERENCES = {
    "FBS": {
        "ACC",
        "American Athletic",
        "Big 12",
        "Big Ten",
        "Conference USA",
        "FBS Independents",
        "Mid-American",
        "Mountain West",
        "Pac-12",
        "SEC",
        "Sun Belt",
    },
    "FCS": {
        "Big Sky",
        "Big South-OVC",
        "CAA",
        "FCS Independents",
        "Ivy",
        "MEAC",
        "MVFC",
        "NEC",
        "Patriot",
        "Pioneer",
        "Southern",
        "Southland",
        "SWAC",
        "UAC",
    },
    "DII": {
        "CIAA",
        "Carolinas",
        "GLIAC",
        "Great American",
        "Great Lakes",
        "Great Midwest Athletic",
        "Gulf South",
        "Independent DII",
        "Lone Star",
        "Mid America",
        "Mountain East",
        "Northeast 10",
        "Northern Sun",
        "Pennsylvania State Athletic",
        "Rocky Mountain",
        "SIAC",
        "South Atlantic",
    },
    "DIII": {
        "American Rivers",
        "American Southwest",
        "CCIW",
        "Centennial",
        "Commonwealth Coast",
        "Empire 8",
        "Heartland",
        "Independent DIII",
        "Landmark Conference",
        "Liberty League",
        "MSCAC",
        "Michigan",
        "Mid Atlantic",
        "Midwest",
        "Minnesota",
        "NACC",
        "NESCAC",
        "NEWMAC",
        "New Jersey",
        "North Coast",
        "Northwest",
        "Ohio",
        "Old Dominion",
        "Presidents'",
        "So. Cal.",
        "Southern Athletic",
        "Southern Collegiate Athletic",
        "USA South",
        "Upper Midwest",
        "Wisconsin",
    },
}


def slugify(value: str) -> str:
    normalized = normalize_name(value)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug or "team"


def normalize_name(value: str) -> str:
    value = value.lower().strip()
    # Plain string replacements (no word-boundary risk).
    value = value.replace("&", "and")
    value = value.replace("university", "")
    value = value.replace("college", "")
    # "St." / "St" -> "state" requires WORD-BOUNDARY regex. The previous
    # implementation did `value.replace("st ", "state ")` which mangled
    # any token containing the literal substring "st ": "east tennessee
    # state" became "eastate tennessee state", "west georgia" became
    # "westate georgia", "southeast missouri" became "southeastate
    # missouri", and so on — hundreds of team slugs went out wrong.
    # Using \bst\b ensures only the actual "St."/"St" abbreviation
    # (as a standalone word) gets expanded.
    value = re.sub(r"\bst\.\s*", "state ", value)
    value = re.sub(r"\bst\b(?!\.)", "state", value)
    return re.sub(r"\s+", " ", value).strip()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def standardize(values: Iterable[float]) -> list[float]:
    numbers = list(values)
    if not numbers:
        return []
    mean = sum(numbers) / len(numbers)
    variance = sum((number - mean) ** 2 for number in numbers) / len(numbers)
    std_dev = math.sqrt(variance) or 1.0
    return [(number - mean) / std_dev for number in numbers]


def adjusted_scores(home_points: int, away_points: int, margin_cap: int = 28) -> tuple[float, float]:
    total_points = float(home_points + away_points)
    raw_margin = float(home_points - away_points)
    capped_margin = clamp(raw_margin, -margin_cap, margin_cap)
    adjusted_home = (total_points + capped_margin) / 2.0
    adjusted_away = total_points - adjusted_home
    return adjusted_home, adjusted_away


def poisson_binomial_tail(probabilities: list[float], min_successes: int) -> float:
    if not probabilities:
        return 1.0 if min_successes <= 0 else 0.0

    distribution = [1.0] + [0.0] * len(probabilities)
    for probability in probabilities:
        next_distribution = distribution[:]
        next_distribution[0] = distribution[0] * (1.0 - probability)
        for successes in range(1, len(distribution)):
            next_distribution[successes] = (
                distribution[successes] * (1.0 - probability)
                + distribution[successes - 1] * probability
            )
        distribution = next_distribution
    return sum(distribution[min_successes:])


def season_label(season_year: int) -> str:
    return f"{season_year} Season"


def season_span_label(season_year: int) -> str:
    next_short_year = str((season_year + 1) % 100).zfill(2)
    return f"{season_year}-{next_short_year}"


def is_site_eligible_team(level_code: str | None, conference_name: str | None) -> bool:
    if not level_code:
        return False
    normalized_level = level_code.strip().upper()
    allowed = OFFICIAL_SUBDIVISION_CONFERENCES.get(normalized_level)
    if not allowed:
        return False
    normalized_conference = (conference_name or "").strip()
    return normalized_conference in allowed
