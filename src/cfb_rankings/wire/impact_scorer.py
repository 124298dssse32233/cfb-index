"""Wire impact scoring — deterministic rule-based scorer.

Decides `impact_label` + `impact_color` per Wire entry. Scored, not
generated, so it's both fast (no LLM cost) and stable across re-runs.

Inputs that drive the score:
  * actor_kind          — coaches > players > programs > conferences > committee for routine entries; reverses on big policy moves.
  * action keywords      — "five-star", "QB1", "DC", "DC promotion", "TV deal", "realignment" all bump up.
  * fan_intel_velocity_spike — the cohort-velocity reading. >70 → loud, >85 → "MOVES <conference>"-tier.
  * program_tier (when known) — blue-blood actions read louder; mid-major actions read quieter unless velocity is screaming.

Output palette:
    "MOVES SEC"     amber   — top of the wire, conference-shaping
    "MOVES BIG TEN" amber   — same
    "MAJOR"         amber   — high-impact but not conference-shaping
    "+NARRATIVE"    green   — adds to a Storyline thread (related_thread_slug present)
    "WATCH"         red     — flagged for follow-up (e.g. flips, breaking velocity)
    "MINOR"         muted   — routine, buried in the wire body

Conference inference is best-effort: actions on flagship programs
inherit a conference tag for the label. Falls back to MAJOR / MINOR
when the program isn't profile-tagged.
"""
from __future__ import annotations

import re
from typing import Any


# Conference inference for the MOVES <X> label.
# Maps program slug -> conference shorthand.
_CONFERENCE_MAP: dict[str, str] = {
    # SEC
    "alabama": "SEC", "auburn": "SEC", "florida": "SEC", "georgia": "SEC",
    "tennessee": "SEC", "texas": "SEC", "oklahoma": "SEC", "lsu": "SEC",
    "ole-miss": "SEC", "mississippi": "SEC", "kentucky": "SEC",
    "south-carolina": "SEC", "missouri": "SEC", "vanderbilt": "SEC",
    "arkansas": "SEC", "texas-am": "SEC", "mississippi-state": "SEC",
    # Big Ten
    "ohio-state": "BIG TEN", "michigan": "BIG TEN", "penn-state": "BIG TEN",
    "usc": "BIG TEN", "oregon": "BIG TEN", "washington": "BIG TEN",
    "wisconsin": "BIG TEN", "iowa": "BIG TEN", "minnesota": "BIG TEN",
    "nebraska": "BIG TEN", "michigan-state": "BIG TEN", "indiana": "BIG TEN",
    "illinois": "BIG TEN", "purdue": "BIG TEN", "northwestern": "BIG TEN",
    "rutgers": "BIG TEN", "maryland": "BIG TEN", "ucla": "BIG TEN",
    # ACC
    "clemson": "ACC", "miami": "ACC", "florida-state": "ACC",
    "north-carolina": "ACC", "duke": "ACC", "virginia-tech": "ACC",
    "boston-college": "ACC", "louisville": "ACC", "pittsburgh": "ACC",
    "syracuse": "ACC", "wake-forest": "ACC", "stanford": "ACC",
    "california": "ACC", "smu": "ACC",
    # Big 12
    "kansas": "BIG 12", "kansas-state": "BIG 12", "oklahoma-state": "BIG 12",
    "iowa-state": "BIG 12", "tcu": "BIG 12", "baylor": "BIG 12",
    "texas-tech": "BIG 12", "west-virginia": "BIG 12", "houston": "BIG 12",
    "ucf": "BIG 12", "cincinnati": "BIG 12", "byu": "BIG 12",
    "colorado": "BIG 12", "arizona": "BIG 12", "arizona-state": "BIG 12",
    "utah": "BIG 12",
    # Notable independents / Group of Five flagships
    "notre-dame": "INDEPENDENT",
    "boise-state": "MOUNTAIN WEST",
    "memphis": "AAC", "tulane": "AAC",
}


# Blue-blood programs — actions on these read louder.
_BLUE_BLOODS: frozenset[str] = frozenset({
    "alabama", "ohio-state", "georgia", "michigan", "texas", "usc",
    "notre-dame", "oklahoma", "lsu", "penn-state", "florida-state",
    "miami", "tennessee", "auburn", "clemson",
})


# Action keyword -> base impact bump.
_KEYWORD_BUMPS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"five[- ]star", re.I), 25),
    (re.compile(r"QB1\b", re.I), 22),
    (re.compile(r"\bflip", re.I), 25),
    (re.compile(r"\bDC\b|defensive coord", re.I), 20),
    (re.compile(r"\bOC\b|offensive coord", re.I), 20),
    (re.compile(r"head coach", re.I), 35),
    (re.compile(r"realign|TV deal|tv-deal|tv deal", re.I), 30),
    (re.compile(r"top[- ]?\d{2,3}", re.I), 12),
    (re.compile(r"NIL", re.I), 12),
    (re.compile(r"committee", re.I), 18),
    (re.compile(r"\bAD\b|athletic director", re.I), 14),
    # Position weighting — QB moves read loudest, specialists quietest.
    (re.compile(r"\bQB\b", re.I), 8),
    (re.compile(r"\b(OT|IOL)\b", re.I), 4),
    (re.compile(r"\b(EDGE|DL|DE|DT)\b", re.I), 3),
    (re.compile(r"\b(WR|RB|TE|CB|S|LB|DB)\b", re.I), 1),
    (re.compile(r"\b(K|P|LS)\b", re.I), -8),
    # Donor-program tier — moves from peer-tier programs land louder.
    (re.compile(r"\bfrom\s+(Alabama|Georgia|Ohio State|Michigan|Texas|USC|Oklahoma|LSU|Penn State|Notre Dame|Tennessee|Auburn|Florida State|Miami|Clemson|Oregon)\b", re.I), 8),
    (re.compile(r"\bfrom\s+(Vanderbilt|Kentucky|Mississippi State|Arkansas|Missouri|Ole Miss|South Carolina)\b", re.I), 4),
    # General "transfer commits" base — every portal entry gets a small bump.
    (re.compile(r"transfer commits|portal exit", re.I), 4),
    (re.compile(r"helmet|stadium", re.I), -8),
    (re.compile(r"strength coach|analyst hire", re.I), -10),
    (re.compile(r"spring", re.I), -6),
)


def _keyword_score(action: str) -> int:
    score = 0
    for pattern, bump in _KEYWORD_BUMPS:
        if pattern.search(action):
            score += bump
    return score


def score_impact(row: dict[str, Any]) -> tuple[str, str]:
    """Return (impact_label, impact_color) for a Wire entry candidate.

    `row` is a dict with keys matching wire_entries (or the ingestion
    intermediate shape). Required: actor_kind, action, program_slug,
    fan_intel_velocity_spike. Optional: related_thread_slug.
    """
    actor_kind = row.get("actor_kind", "program")
    action = row.get("action", "") or ""
    program_slug = (row.get("program_slug") or "").lower()
    velocity = int(row.get("fan_intel_velocity_spike") or 0)
    has_thread = bool(row.get("related_thread_slug"))

    # Compose the impact score.
    score = velocity                       # 0..100 from the boards
    score += _keyword_score(action)        # keyword bumps

    # Blue-blood actions read +12 louder.
    if program_slug in _BLUE_BLOODS:
        score += 12

    # Coaching > player for routine entries.
    if actor_kind == "coach":
        score += 6
    elif actor_kind == "committee":
        score += 4

    # Storyline-thread linkage = +NARRATIVE label, regardless of score.
    if has_thread:
        return ("+NARRATIVE", "green")

    # Recalibrated against real CFBD `/player/portal` data — Sprint 12.
    # Real portal moves carry base velocity 70. After the +6 "transfer
    # commits" keyword bump every G5 portal move would land at 76; with
    # the prior MAJOR>=70 threshold every entry tagged MAJOR. Tuned so:
    #   MOVES <conf>: blue-blood incoming + a name-recognition keyword
    #                 (~5% of entries)
    #   MAJOR:       blue-blood incoming, or non-blue-blood with a
    #                 strong action keyword (~12-18%)
    #   WATCH:       flips, departures, blue-blood-to-blue-blood
    #                 defections (~3-5%)
    #   MINOR:       the wire body (~70-80%)

    # Conference-shaping tier — blue-blood + peer-program donor + skill position.
    if score >= 92:
        conf = _CONFERENCE_MAP.get(program_slug)
        if conf and conf != "INDEPENDENT":
            return (f"MOVES {conf}", "amber")
        return ("MAJOR", "amber")

    # Watch tier — flips, departures, peer-program defections to a rival.
    if re.search(r"\bflip|breaking|leak|departure to\b", action, re.I) and score >= 75:
        return ("WATCH", "red")

    # Watch tier (player) — peer-program SEC-internal / B1G-internal portal moves.
    if (
        actor_kind == "player"
        and re.search(r"transfer commits from", action, re.I)
        and re.search(
            r"\bfrom\s+(Alabama|Georgia|Auburn|Tennessee|Texas|LSU|Ohio State|Michigan|"
            r"Oregon|USC|Penn State|Notre Dame|Florida State|Miami|Clemson|Oklahoma|"
            r"Ole Miss|Mississippi)\b",
            action, re.I,
        )
    ):
        # Donor program is a peer — defection-flavored move worth flagging.
        if score >= 80:
            return ("WATCH", "red")

    # Major tier.
    if score >= 80:
        return ("MAJOR", "amber")

    # Everything else is the wire body.
    return ("MINOR", "muted")
