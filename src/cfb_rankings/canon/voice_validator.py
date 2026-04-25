"""Voice validator for canon editorial copy.

Per CLAUDE_CODE_THE_CANON.md, this module imports the canonical
BANNED_PHRASES list from ``team_pages/voice_validator.py`` if it exists,
and otherwise falls back to a local copy lifted verbatim from
``team_pages/chronicle_generator.py:_BANNED_PHRASES`` (Sprint 8's home of
the same list — we deliberately re-use, not redefine).

If/when team_pages exposes a unified validator, replace ``_load_banned``
with a direct import. See SESSION_LOG (Sprint 11) for the dedup note.
"""
from __future__ import annotations

import re
from typing import Iterable, NamedTuple


# --------------------------------------------------------------------------
# Banned-phrase source (verbatim from chronicle_generator._BANNED_PHRASES,
# Sprint 8). When team_pages.voice_validator is created downstream, switch
# this to ``from cfb_rankings.team_pages.voice_validator import BANNED_PHRASES``.
# --------------------------------------------------------------------------

_BANNED_PHRASES_FALLBACK: tuple[str, ...] = (
    " sample",
    "sample ",
    "stat engine",
    "pipeline",
    "our algorithm",
    "the algorithm",
    "methodology",
    "tier 1",
    "tier 2",
    "the pattern is",
    "summary stat",
    "compression of outcome",
    "flattening of",
    "every season produces",
    "this table",
    "this card",
    "this module",
    "the engine",
    "cfb index",
)


def _load_banned() -> tuple[str, ...]:
    """Prefer team_pages.voice_validator if it exists; else local fallback."""
    try:
        from cfb_rankings.team_pages.voice_validator import (  # type: ignore
            BANNED_PHRASES,
        )
        return tuple(BANNED_PHRASES)
    except ImportError:
        # Fall back to chronicle_generator's list (also exported as a tuple).
        try:
            from cfb_rankings.team_pages.chronicle_generator import (  # type: ignore
                _BANNED_PHRASES,
            )
            return tuple(_BANNED_PHRASES)
        except ImportError:
            return _BANNED_PHRASES_FALLBACK


BANNED_PHRASES: tuple[str, ...] = _load_banned()


# --------------------------------------------------------------------------
# Validation result
# --------------------------------------------------------------------------

class ValidationResult(NamedTuple):
    passed: bool
    text: str
    matches: tuple[str, ...]   # banned phrases that hit (lower-cased)


_MIN_WORDS_PARAGRAPH = 60          # editorial paragraphs ought to be substantive
_MAX_WORDS_PARAGRAPH = 320         # but not bloated
_MIN_WORDS_ONELINER = 8
_MAX_WORDS_ONELINER = 60


def validate(text: str | None, *, kind: str) -> ValidationResult:
    """Run the validator against a single piece of editorial copy.

    ``kind`` is one of ``'paragraph'`` (≥60 words) or ``'oneliner'``
    (≤60 words). Returns ``passed=True`` only when the text:

      1. contains no BANNED_PHRASES (case-insensitive substring),
      2. is within the appropriate word-count band,
      3. is non-empty.
    """
    if text is None or not text.strip():
        return ValidationResult(False, text or "", ("__empty__",))

    lo = text.lower()
    hits = tuple(p for p in BANNED_PHRASES if p in lo)
    if hits:
        return ValidationResult(False, text, hits)

    word_count = len(text.split())
    if kind == "paragraph":
        if word_count < _MIN_WORDS_PARAGRAPH:
            return ValidationResult(False, text, ("__too_short__",))
        if word_count > _MAX_WORDS_PARAGRAPH:
            return ValidationResult(False, text, ("__too_long__",))
    elif kind == "oneliner":
        if word_count < _MIN_WORDS_ONELINER:
            return ValidationResult(False, text, ("__too_short__",))
        if word_count > _MAX_WORDS_ONELINER:
            return ValidationResult(False, text, ("__too_long__",))
    else:  # pragma: no cover — caller-side bug
        raise ValueError(f"unknown kind: {kind!r}")

    return ValidationResult(True, text, ())


def batch_validate(
    items: Iterable[tuple[str, str | None, str]],
) -> dict[str, list[ValidationResult]]:
    """Validate a batch.

    Each input tuple is ``(label, text, kind)``. Returns a dict with
    ``'passed'`` and ``'failed'`` lists, plus a ``'rate'`` float.
    """
    passed: list[ValidationResult] = []
    failed: list[ValidationResult] = []
    failed_labels: list[str] = []
    for label, text, kind in items:
        r = validate(text, kind=kind)
        if r.passed:
            passed.append(r)
        else:
            failed.append(r)
            failed_labels.append(label)
    total = len(passed) + len(failed)
    rate = (len(passed) / total) if total else 1.0
    return {
        "passed": passed,
        "failed": failed,
        "failed_labels": failed_labels,
        "rate": rate,
        "total": total,
    }
