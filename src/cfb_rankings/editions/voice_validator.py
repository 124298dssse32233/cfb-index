"""Editions validator shim.

Sprint 9 once shipped a local 95-line BANNED_PHRASES list here. During
wave-1-2 integration the canonical fan-voice validator at
``cfb_rankings.team_pages.voice_validator`` absorbed the 20 phrases that
were unique to the editions register (methodology meta-language,
AI/system-tells, generic-magazine clichés). This module now defers to the
single source of truth.

Surface compatibility:
- ``BANNED_PHRASES``: re-exported from canonical
- ``ValidationResult(ok, violations)``: matches the original Sprint-9 dataclass shape
- ``validate(text)``: returns ``ValidationResult`` (Sprint-9 callers)
- ``assert_valid(text, label)``: raises ``ValueError`` on violations (Sprint-9 callers)
"""
from __future__ import annotations

from dataclasses import dataclass

from cfb_rankings.team_pages.voice_validator import (
    BANNED_PHRASES,
    validate_fan_voice,
)


@dataclass
class ValidationResult:
    ok: bool
    violations: list[str]

    def __bool__(self) -> bool:
        return self.ok


def validate(text: str) -> ValidationResult:
    """Sprint-9-compatible wrapper around the canonical validator."""
    if not text:
        return ValidationResult(ok=True, violations=[])
    ok, violations = validate_fan_voice(text, source="editions")
    return ValidationResult(ok=ok, violations=sorted(set(violations)))


def assert_valid(text: str, label: str = "text") -> None:
    """Raise ``ValueError`` if ``text`` contains banned phrases."""
    result = validate(text)
    if not result.ok:
        raise ValueError(
            f"voice_validator: {label} contains banned phrases: "
            f"{', '.join(result.violations)}"
        )
