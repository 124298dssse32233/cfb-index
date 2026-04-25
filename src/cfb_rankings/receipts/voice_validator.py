"""Receipts validator shim.

Sprint 13 once had its own banned-phrase list here. Per the Sprint-13
review (no-drift rule from the user), the canonical fan-voice validator
lives in `cfb_rankings.team_pages.voice_validator`. The receipts-specific
tone-violation phrases ("hot take", "L take", "cope", etc.) were ported
into the canonical's `BANNED_PHRASES` tuple, and this module now defers
to that single source of truth.

What stays here: receipts-specific *required-token* checks (the
`Surprise Index` mention rule on Best-Calls editorial), which are an
editorial completeness gate, not a phrasing-leakage gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    # Preferred path once team_pages package imports cleanly (post-merge).
    from cfb_rankings.team_pages.voice_validator import (
        BANNED_PHRASES,
        FAN_VOICE_REPLACEMENTS,
        ValidationResult as CanonicalValidationResult,
        first_violation,
        has_banned_phrase,
        validate as _canonical_validate,
        validate_fan_voice,
    )
except ImportError:
    # Worktree fallback: team_pages/__init__.py eagerly imports the renderer,
    # which depends on uncommitted Sprint-8 WIP (FLOOR_AWAITING, etc.) that
    # may not be present in this branch's base. Load the canonical module
    # directly from its path so receipts validation still uses ONE source of
    # truth without dragging in the rest of team_pages.
    import importlib.util as _ilu
    import sys as _sys
    from pathlib import Path as _P
    _src = _P(__file__).resolve().parents[1] / "team_pages" / "voice_validator.py"
    _mod_name = "cfb_rankings._receipts_canonical_voice"
    _spec = _ilu.spec_from_file_location(_mod_name, str(_src))
    _mod = _ilu.module_from_spec(_spec)
    # Register before exec so @dataclass / TYPE introspection resolves cleanly
    # under Python 3.14's stricter module-namespace lookup.
    _sys.modules[_mod_name] = _mod
    _spec.loader.exec_module(_mod)
    BANNED_PHRASES = _mod.BANNED_PHRASES
    FAN_VOICE_REPLACEMENTS = _mod.FAN_VOICE_REPLACEMENTS
    CanonicalValidationResult = _mod.ValidationResult
    first_violation = _mod.first_violation
    has_banned_phrase = _mod.has_banned_phrase
    _canonical_validate = _mod.validate
    validate_fan_voice = _mod.validate_fan_voice


# Tokens that MUST appear in receipts editorial copy (currently only the
# "Surprise Index" callout rule from EDITORIAL_POSITIONING_AND_CONTENT_TYPES.md
# §"The Long-Shot That Hit"). Kept as a receipts-local constant because the
# requirement is editorial-completeness-specific to the Receipts surface.
REQUIRED_TOKENS_BEST_CALLS: tuple[str, ...] = (
    "Surprise Index",
)


@dataclass
class ValidationResult:
    """Receipts-flavored result that adds `missing` (required tokens not present)
    on top of the canonical validator's `passed` / `violations`.
    """

    passed: bool
    violations: list[str]
    missing: list[str]
    notes: str


def validate(text: str, *, require_tokens: Iterable[str] = ()) -> ValidationResult:
    """Run the canonical banned-phrase check + receipts-specific required-token check."""
    canonical = _canonical_validate(text)
    missing = [t for t in require_tokens if t.lower() not in (text or "").lower()]
    passed = canonical.passed and not missing
    notes = (
        "ok" if passed
        else f"{len(canonical.violations)} violations, {len(missing)} missing tokens"
    )
    return ValidationResult(
        passed=passed,
        violations=list(canonical.violations),
        missing=missing,
        notes=notes,
    )


def validate_corpus(
    texts: Iterable[str], *, require_tokens: Iterable[str] = (),
) -> dict[str, int | float]:
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


__all__ = [
    "BANNED_PHRASES",
    "FAN_VOICE_REPLACEMENTS",
    "REQUIRED_TOKENS_BEST_CALLS",
    "ValidationResult",
    "first_violation",
    "has_banned_phrase",
    "validate",
    "validate_corpus",
    "validate_fan_voice",
]
