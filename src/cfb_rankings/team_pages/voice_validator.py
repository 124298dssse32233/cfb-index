"""Fan-voice copy validator.

The banned-phrase enforcement gate from the Pulse Redesign Brief +
HOMEPAGE_AND_WEEKLY_EDITION_STRATEGY §v4. Every string a fan reads on
disk passes through this validator. Failures route back to the LLM for
one rewrite attempt; second-pass failures are dropped and logged.

The list is intentionally explicit. Internal taxonomy ("analytics-cohort",
"n=", "discourse velocity", etc.) is fine in code and methodology pages but
must never reach a fan-facing surface — the validator is what enforces
the boundary at write-time.

**Word-boundary matching (Sprint 10 audit fix).** Each banned phrase is
matched with regex word boundaries on its outer word-character edges,
not as a free substring. This prevents historic false positives like:
- "the engine" matching "the engineering team" (real bug)
- "this table" matching "this tablecloth"
- "cohorts" matching "freshman cohorts" (legitimate non-taxonomy use of
  the standard English word "cohort" — bare "cohort" was removed from
  the list because the actual policy concern is the taxonomy compounds
  ("analytics-cohort", "analytics cohort", "casual-cohort", etc.) which
  are listed explicitly).

Usage:

    from cfb_rankings.team_pages.voice_validator import validate_fan_voice

    ok, violations = validate_fan_voice(generated_lede, source="ND lede")
    if not ok:
        # log violations, retry once, drop on second failure
        ...
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Banned phrases — every entry must NOT appear in user-facing copy.
#
# Maintained as a single flat list (case-insensitive). Matching uses
# word-boundary regex (see _build_pattern below) — substring-within-words
# does NOT count, so "cohort" appearing in "freshman cohort" is allowed
# while "the analytics cohort" is caught by the explicit "analytics
# cohort" entry. This keeps the validator strict on taxonomy leakage
# without over-blocking legitimate uses of common English words.
# ---------------------------------------------------------------------------

BANNED_PHRASES: tuple[str, ...] = (
    # Cohort taxonomy — every taxonomic form, both hyphenated and
    # space-separated. Bare "cohort" (the standard English word) is
    # NOT banned; the taxonomy variants below cover every real
    # leakage path.
    "analytics-cohort",
    "analytics cohort",
    "casual-cohort",
    "casual cohort",
    "casual-vibes-cohort",
    "casual vibes cohort",
    "die-hard-cohort",
    "die-hard cohort",
    "diehard-cohort",
    "diehard cohort",
    "national-narrative-cohort",
    "national narrative cohort",
    "local-market-cohort",
    "local market cohort",
    "alumni-diaspora-cohort",
    "alumni diaspora cohort",
    "boomer-gen-x-cohort",
    "boomer gen-x cohort",
    "gen-z-cohort",
    "gen z cohort",
    "cohort divergence",
    "cohort split",
    # Statistical notation — replace with "the sample" or "how many fans"
    "n=",
    "effective n",
    "effective_n",
    # Pipeline / engine leakage
    "fan-intel",
    "fan-intel pipeline",
    "discourse velocity",
    "discourse-velocity",
    "stat engine",
    "our algorithm",
    "the engine",
    # Tier taxonomy in copy (fine in profile YAML, banned in copy)
    "tier-1 program",
    "tier 1 program",
    "tier-2",
    # Dashboard / methodology meta-talk
    "summary stat",
    "compression of outcome",
    "the pattern is ",
    "every season produces",
    "this table",
    "this card",
    "this module",
    # "methodology" + morphological variants are banned in fan-facing
    # copy; the methodology page itself should not run through this
    # validator.
    "methodology",
    "methodologies",
    "methodological",
    # Pulse-specific dashboard scaffolding
    "sample growing",
    # "sample" alone is borderline — used as standalone in places like
    # "early sample". The narrower "sample growing" / "sample is still
    # building" is what we ban; bare "sample" is allowed (and the
    # confidence-band labels we ship use it).
    # ----------------------------------------------------------------------
    # Sprint 13 (Receipts) tone-violation additions. Receipts editorial has
    # a stricter framing rule than the rest of the surface: celebratory
    # not gotcha, named sources only, no platform-native sneering. These
    # phrases are not internal-taxonomy leakage but they violate the
    # Receipts framing contract and were ported here so we maintain a
    # single banned-phrase list.
    # ----------------------------------------------------------------------
    "hot take",
    "clown",
    "clowned",
    "idiot",
    "stupid",
    "amirite",
    "L take",
    "cope",
    "seethe",
    "anonymous source",
    "according to a source",
    "we all know",
    "obviously",
    "of course",
)


def _build_pattern(phrase: str) -> re.Pattern[str]:
    """Compile a word-boundary-aware regex for a banned phrase.

    Adds ``\\b`` before the phrase if it starts with a word character
    (letters, digits, underscore); adds ``\\b`` after if it ends with
    one. Phrases that begin or end with non-word characters (``n=``,
    ``"the pattern is "`` with trailing space, hyphenated tokens that
    begin or end with a hyphen) get only the boundary that makes
    sense for them, which lets ``n=`` match in ``n=48`` cleanly while
    ``the engine`` does NOT match inside ``the engineering team``.
    """
    escaped = re.escape(phrase.lower())
    if phrase[:1].isalnum() or phrase[:1] == "_":
        escaped = r"\b" + escaped
    if phrase[-1:].isalnum() or phrase[-1:] == "_":
        escaped = escaped + r"\b"
    return re.compile(escaped, re.IGNORECASE)


# Pre-compile patterns at module-import time so per-validation calls are
# allocation-free. Tuple of (lowercased_phrase, compiled_pattern).
_BANNED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (p.lower(), _build_pattern(p)) for p in BANNED_PHRASES
)

# Kept for backward compat with any caller that imports the lowered list.
_BANNED_LOWER: tuple[str, ...] = tuple(p for p, _ in _BANNED_PATTERNS)


# ---------------------------------------------------------------------------
# Approved fan-voice replacements — the lookup table the LLM prompts seed
# from. Not used by the validator itself (the validator is a gate, not a
# rewriter), but ships in this module so generators import a single source
# of truth for "instead of X, say Y".
# ---------------------------------------------------------------------------

FAN_VOICE_REPLACEMENTS: dict[str, tuple[str, ...]] = {
    "analytics-cohort": (
        "the stat crowd",
        "the analytics folks",
        "the spreadsheet types",
        "the EPA people",
        "the chart guys",
    ),
    "casual-cohort": (
        "the casual fans",
        "regular fans",
        "the vibes crowd",
        "your average fan",
        "the average viewer",
    ),
    "casual-vibes-cohort": (
        "the casual fans",
        "regular fans",
    ),
    "die-hard-cohort": (
        "the diehards",
        "the lifers",
        "the every-snap people",
    ),
    "national-narrative-cohort": (
        "the talking heads",
        "ESPN's narrative",
        "the national media",
    ),
    "local-market-cohort": (
        "the locals",
        "home fans",
        "in-state fans",
    ),
    "alumni-diaspora-cohort": (
        "the diaspora",
        "alumni out of state",
        "season-ticket exiles",
    ),
    "boomer-gen-x-cohort": (
        "older fans",
        "longtime fans",
        "the fans who remember Bo and Woody",
    ),
    "gen-z-cohort": (
        "younger fans",
        "college-age fans",
        "students",
    ),
    "cohort divergence": (
        "the gap",
        "the disagreement",
        "the split",
        "where they don't agree",
    ),
    "effective n": (
        "the sample",
        "how many fans we counted",
        "how many fans we heard from",
    ),
    "fan-intel pipeline": (
        "what fans are saying",
        "the conversation",
        "the boards and Bluesky and beat-writers",
        "the corpus",
    ),
    "discourse velocity": (
        "how loud the conversation got",
        "how much fans were talking",
        "the buzz",
    ),
    "sample growing": (
        "more fans, every week",
        "the conversation is building",
    ),
}


@dataclass
class ValidationResult:
    """Structured result so call sites can attribute failures and route retries.

    `passed` is the boolean check; `violations` is the human-readable list
    of banned phrases found. `source` is the call-site label (e.g. "ND lede",
    "SEC theme #2 quote") so logs are scannable when validator dropouts spike.
    """

    passed: bool
    violations: list[str]
    source: str = ""

    def __bool__(self) -> bool:  # allows `if result:` shorthand
        return self.passed


def validate_fan_voice(text: str, source: str = "") -> tuple[bool, list[str]]:
    """Return (passed, violations) for a candidate fan-facing string.

    Word-boundary regex match (case-insensitive). A failure means the
    LLM output leaked internal taxonomy — caller should request one
    rewrite, then drop the copy on second failure.

    Empty / whitespace-only input is treated as passing (caller decides
    whether empty content is acceptable separately — the validator's job
    is to gate phrasing, not presence).
    """
    if not text or not text.strip():
        return (True, [])
    violations: list[str] = []
    for banned, pattern in _BANNED_PATTERNS:
        if pattern.search(text):
            violations.append(banned)
    return (len(violations) == 0, violations)


def validate(text: str, source: str = "") -> ValidationResult:
    """Structured-result variant of `validate_fan_voice`."""
    passed, violations = validate_fan_voice(text, source=source)
    return ValidationResult(passed=passed, violations=violations, source=source)


def has_banned_phrase(text: str) -> bool:
    """Boolean shortcut. Used by render-time grep sweeps over already-rendered HTML."""
    if not text:
        return False
    return any(pattern.search(text) for _, pattern in _BANNED_PATTERNS)


def first_violation(text: str) -> str | None:
    """Return the first banned phrase found, or None. Useful for logging."""
    if not text:
        return None
    for banned, pattern in _BANNED_PATTERNS:
        if pattern.search(text):
            return banned
    return None
