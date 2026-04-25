"""Voice validator (Sprint 13 cross-cut).

Lightweight banned-phrase + tone check for receipts editorial copy. Mirrors
the pattern used by chronicle/pulse but tuned for the receipts framing rules:

  * Celebratory not gotcha.
  * Aged-poorly takes are framed gently.
  * No anonymized sources — names are non-negotiable.
  * No editorializing on the source's character (only on the take itself).

Returns (passed, notes).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


# Phrases that violate receipts framing rules.
BANNED_PHRASES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE), reason)
    for phrase, reason in [
        ("hot take",          "use 'take' or 'prediction' — 'hot take' editorializes"),
        ("clown",             "gotcha-tone; banned by framing rules"),
        ("clowned",           "gotcha-tone"),
        ("idiot",             "personal attack"),
        ("stupid",            "personal attack"),
        ("dumb",              "personal attack"),
        ("anonymous source",  "framing rule: no anonymous attribution"),
        ("according to a source", "framing rule: name the predictor"),
        ("we all know",       "lazy editorial filler"),
        ("obviously",         "lazy editorial filler"),
        ("of course",         "lazy editorial filler"),
        ("amirite",            "tone violation"),
        ("L take",            "gotcha-tone"),
        ("ratio",             "platform-native sneering tone"),
        ("cope",              "personal attack"),
        ("seethe",            "personal attack"),
    ]
)

# Phrases REQUIRED somewhere in best-calls / receipts copy.
REQUIRED_TOKENS_BEST_CALLS: tuple[str, ...] = (
    "Surprise Index",
)


@dataclass
class ValidationResult:
    passed: bool
    violations: list[str]
    missing: list[str]
    notes: str


def validate(text: str, *, require_tokens: Iterable[str] = ()) -> ValidationResult:
    violations: list[str] = []
    for pat, reason in BANNED_PHRASES:
        if pat.search(text):
            violations.append(f"{pat.pattern}: {reason}")
    missing: list[str] = []
    for tok in require_tokens:
        if tok.lower() not in text.lower():
            missing.append(tok)
    passed = not violations and not missing
    notes = "ok" if passed else (
        f"{len(violations)} violations, {len(missing)} missing tokens"
    )
    return ValidationResult(passed=passed, violations=violations, missing=missing, notes=notes)


def validate_corpus(texts: Iterable[str], *, require_tokens: Iterable[str] = ()) -> dict[str, int | float]:
    total = 0
    passing = 0
    violation_count = 0
    missing_count = 0
    for t in texts:
        total += 1
        result = validate(t, require_tokens=require_tokens)
        if result.passed:
            passing += 1
        violation_count += len(result.violations)
        missing_count += len(result.missing)
    pass_rate = (passing / total) if total else 1.0
    return {
        "total": total,
        "passing": passing,
        "violations_total": violation_count,
        "missing_total": missing_count,
        "pass_rate": round(pass_rate, 4),
    }
