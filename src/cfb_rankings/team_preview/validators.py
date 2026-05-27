"""Validation gates for team-preview claim candidates.

LLM output is never a source of truth. This module validates candidate prose
against the deterministic evidence packet built from team-preview tables.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from cfb_rankings.team_pages.voice_validator import validate_fan_voice


_NUMBER_RE = re.compile(r"(?<![A-Za-z])#?\b\d+(?:\.\d+)?\b")
_FAN_INTEL_RE = re.compile(
    r"\b(fans?|fanbase|boards?|reddit|conversation|mood|belief|expect|expecting)\b",
    re.IGNORECASE,
)
_BAD_ENDING_RE = re.compile(
    r"\b(and|but|or|despite|although|while|with|without|because|for|from|to|of|in|on|at|by)\s*$",
    re.IGNORECASE,
)
_APPROX_RANK_RE = re.compile(r"\btop[- ]\d+\b", re.IGNORECASE)


@dataclass
class ClaimValidation:
    passed: bool
    errors: list[str] = field(default_factory=list)
    voice_score: float = 0.0
    fact_score: float = 0.0
    slop_score: float = 0.0


def validate_preview_claim(candidate: dict[str, Any], evidence: dict[str, Any]) -> ClaimValidation:
    """Validate a structured preview claim against deterministic evidence.

    Required candidate shape:
      headline: str
      body: str
      supporting_claims: [{evidence_key, text, numeric_values}]
      confidence_band: high|medium|low|unset
    """
    errors: list[str] = []
    headline = _text(candidate.get("headline"))
    body = _text(candidate.get("body"))
    supporting = candidate.get("supporting_claims")
    if not headline:
        errors.append("headline_missing")
    if not body:
        errors.append("body_missing")
    if headline and _BAD_ENDING_RE.search(headline):
        errors.append("headline_fragment")
    if body and body[0].islower():
        errors.append("body_fragment")
    if not isinstance(supporting, list) or not supporting:
        errors.append("supporting_claims_missing")

    combined_parts = [headline, body]
    known_keys = _evidence_keys(evidence)
    allowed_numbers = _allowed_numbers(evidence)
    cited_numbers: set[str] = set()

    for idx, item in enumerate(supporting if isinstance(supporting, list) else []):
        if not isinstance(item, dict):
            errors.append(f"supporting_claim_{idx}_not_object")
            continue
        key = _normalise_key(_text(item.get("evidence_key")))
        if not key:
            errors.append(f"supporting_claim_{idx}_missing_evidence_key")
        elif key not in known_keys:
            # Try inserting a list index — models often omit the index in paths
            # like "transfer_positions.net_count" vs "transfer_positions.0.net_count"
            fuzzy_key = _fuzzy_list_key(key, known_keys)
            if fuzzy_key is None:
                errors.append(f"unsupported_evidence_key:{key}")
        text = _text(item.get("text"))
        if text:
            combined_parts.append(text)
        nums = item.get("numeric_values") or []
        if not isinstance(nums, list):
            errors.append(f"supporting_claim_{idx}_numeric_values_not_list")
            nums = []
        for n in nums:
            if not _number_supported(n, allowed_numbers):
                errors.append(f"unsupported_numeric_value:{n}")
            else:
                cited_numbers.update(_number_candidates(n))
        for token in _numbers_in_text(text):
            if not _number_supported(token, allowed_numbers):
                errors.append(f"unsupported_numeric_text:{token}")
            if not _is_year_token(token) and not _number_supported(token, set(cited_numbers)):
                errors.append(f"numeric_text_missing_receipt:{token}")

    combined = " ".join(combined_parts)
    if not _is_ascii(combined):
        errors.append("non_ascii_text")
    if _APPROX_RANK_RE.search(combined):
        errors.append("approximate_rank_phrase")
    for token in _numbers_in_text(combined):
        if _is_internal_decimal_score(token):
            errors.append(f"internal_decimal_score:{token}")
        if not _number_supported(token, allowed_numbers):
            errors.append(f"unsupported_numeric_text:{token}")
        if not _is_year_token(token) and not _number_supported(token, cited_numbers):
            errors.append(f"numeric_text_missing_receipt:{token}")

    fan_ready = bool((evidence.get("fan_intel") or {}).get("ready"))
    if not fan_ready and _FAN_INTEL_RE.search(combined):
        errors.append("fan_intel_not_ready")

    voice_ok, voice_violations = validate_fan_voice(combined, source="team-preview")
    if not voice_ok:
        errors.extend(f"voice:{v}" for v in voice_violations)

    confidence = _text(candidate.get("confidence_band")) or "unset"
    if confidence not in {"high", "medium", "low", "unset"}:
        errors.append(f"invalid_confidence_band:{confidence}")

    fact_score = 1.0 if not any(
        e.startswith(("unsupported_", "numeric_", "approximate_", "internal_", "fan_intel_not_ready"))
        for e in errors
    ) else 0.0
    voice_score = 1.0 if voice_ok else 0.0
    slop_score = 1.0 if not any(e.startswith("voice:") for e in errors) else 0.0
    return ClaimValidation(
        passed=not errors,
        errors=errors,
        voice_score=voice_score,
        fact_score=fact_score,
        slop_score=slop_score,
    )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalise_key(value: str) -> str:
    return re.sub(r"\[(\d+)\]", r".\1", value)


def _is_ascii(value: str) -> bool:
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _numbers_in_text(text: str) -> list[str]:
    return [m.group(0).lstrip("#") for m in _NUMBER_RE.finditer(text or "")]


def _number_supported(value: Any, allowed: set[str]) -> bool:
    try:
        fval = float(str(value).lstrip("#"))
    except (TypeError, ValueError):
        return False
    return bool(_number_candidates(fval) & allowed)


def _number_candidates(value: Any) -> set[str]:
    fval = float(str(value).lstrip("#"))
    return {
        str(int(round(fval))),
        f"{fval:.1f}".rstrip("0").rstrip("."),
        f"{fval:.2f}".rstrip("0").rstrip("."),
    }


def _is_year_token(value: Any) -> bool:
    try:
        ival = int(float(str(value).lstrip("#")))
    except (TypeError, ValueError):
        return False
    return 1900 <= ival <= 2100


def _is_internal_decimal_score(value: Any) -> bool:
    text = str(value).lstrip("#")
    if "." not in text:
        return False
    try:
        fval = abs(float(text))
    except (TypeError, ValueError):
        return False
    return 0 < fval < 1


def _evidence_keys(evidence: dict[str, Any]) -> set[str]:
    keys: set[str] = set()

    def walk(node: Any, prefix: str = "") -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                next_prefix = f"{prefix}.{key}" if prefix else str(key)
                keys.add(next_prefix)
                walk(val, next_prefix)
        elif isinstance(node, list):
            for idx, val in enumerate(node):
                walk(val, f"{prefix}.{idx}" if prefix else str(idx))

    walk(evidence)
    return keys


def _allowed_numbers(evidence: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()

    def add_number(value: Any) -> None:
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            fval = float(value)
            allowed.add(str(int(round(fval))))
            allowed.add(f"{fval:.1f}".rstrip("0").rstrip("."))
            allowed.add(f"{fval:.2f}".rstrip("0").rstrip("."))
            return
        if isinstance(value, str):
            for token in _numbers_in_text(value):
                allowed.add(token)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for val in node.values():
                walk(val)
        elif isinstance(node, list):
            for val in node:
                walk(val)
        else:
            add_number(node)

    walk(evidence)
    return allowed


def _fuzzy_list_key(key: str, known_keys: set[str]) -> str | None:
    """Try inserting a numeric list index into a key that skipped it.

    Models often write 'transfer_positions.net_count' when the evidence
    structure requires 'transfer_positions.0.net_count'.  We try inserting
    indices 0-5 at each segment boundary and return the first match.
    """
    parts = key.split(".")
    for insert_at in range(1, len(parts)):
        for idx in range(6):
            candidate = ".".join(parts[:insert_at] + [str(idx)] + parts[insert_at:])
            if candidate in known_keys:
                return candidate
    return None
