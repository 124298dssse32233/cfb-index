"""Local-LLM candidate synthesis for team-preview claims."""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from cfb_rankings.chronicle.runtime import (
    CardTier,
    GenerationConfig,
    GenerationError,
    Router,
    build_default_router,
)
from cfb_rankings.team_preview.evidence import canonical_fbs_slugs_for_db
from cfb_rankings.team_preview.persistence import write_preview_claim_cache
from cfb_rankings.team_preview.prompts import (
    PROMPT_TEMPLATE_ID,
    PreviewClaimCandidate,
    build_preview_claim_prompt,
    build_preview_evidence,
)
from cfb_rankings.team_preview.validators import (
    _allowed_numbers,
    _is_internal_decimal_score,
    _is_year_token,
    _number_candidates,
    _number_supported,
    _numbers_in_text,
    validate_preview_claim,
)


SURFACE_PREVIEW_THESIS = "preview_thesis"
CLAIM_TYPE_THESIS = "team_preview_thesis"
MAX_VALIDATION_ATTEMPTS = 2


@dataclass
class ClaimGenerationReport:
    targets: int = 0
    approved: int = 0
    rejected: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


def generate_team_preview_claims(
    db: Any,
    *,
    season_year: int,
    as_of_date: str,
    slugs: list[str] | None = None,
    allow_cloud: bool = False,
    router: Router | None = None,
) -> ClaimGenerationReport:
    targets = list(slugs) if slugs else canonical_fbs_slugs_for_db(db)
    report = ClaimGenerationReport(targets=len(targets))
    router = router or build_default_router(allow_cloud=allow_cloud)
    backend = router.select(CardTier.T3, "writer")

    for slug in targets:
        evidence = build_preview_evidence(db, slug, season_year, as_of_date)
        if not evidence:
            report.skipped += 1
            report.errors.append({"slug": slug, "error": "missing_evidence"})
            continue
        prompt = build_preview_claim_prompt(evidence)
        candidate = None
        generation = None
        validation = None
        last_errors: list[str] = []
        for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
            started = time.perf_counter()
            try:
                candidate_model, generation = backend.generate_structured(
                    prompt,
                    PreviewClaimCandidate,
                    GenerationConfig(
                        max_tokens=520,
                        temperature=0.2 if attempt > 1 else 0.25,
                        top_p=0.75 if attempt > 1 else 0.8,
                        wall_clock_budget_s=45.0,
                    ),
                )
                duration_s = max(0.0, time.perf_counter() - started)
            except Exception as exc:
                _log_usage(
                    model_id=getattr(backend, "model_id", "unknown"),
                    backend_name=getattr(backend, "name", "unknown"),
                    prompt_tokens=max(1, len(prompt) // 4),
                    completion_tokens=0,
                    duration_s=max(0.0, time.perf_counter() - started),
                    success=False,
                    error_kind=type(exc).__name__,
                    evidence_hash=str(evidence.get("evidence_hash") or ""),
                )
                last_errors = [f"generation:{type(exc).__name__}"]
                if attempt < MAX_VALIDATION_ATTEMPTS:
                    prompt = _repair_prompt(prompt, last_errors)
                continue

            candidate = _normalise_candidate_text(_candidate_to_dict(candidate_model))
            candidate = _fix_comma_evidence_keys(candidate, evidence)
            candidate = _autofill_numeric_receipts(candidate, evidence)
            candidate = _fix_approximate_ranks(candidate, evidence)
            candidate = _strip_internal_decimal_scores(candidate, evidence)
            validation = validate_preview_claim(candidate, evidence)
            _log_usage(
                model_id=generation.model_id,
                backend_name=generation.backend,
                prompt_tokens=generation.tokens_in,
                completion_tokens=generation.tokens_out,
                duration_s=duration_s,
                success=validation.passed,
                error_kind=None if validation.passed else "validator_reject",
                evidence_hash=str(evidence.get("evidence_hash") or ""),
                validator_scores={
                    "voice": validation.voice_score,
                    "fact": validation.fact_score,
                    "slop": validation.slop_score,
                },
            )
            if validation.passed:
                break
            last_errors = validation.errors
            if attempt < MAX_VALIDATION_ATTEMPTS:
                prompt = _repair_prompt(prompt, last_errors)

        if not candidate or not generation or not validation or not validation.passed:
            report.rejected += 1
            report.errors.append({
                "slug": slug,
                "error": "validator_reject",
                "violations": last_errors,
            })
            continue

        team = evidence["team"]
        key = write_preview_claim_cache(
            db,
            team_id=int(team["team_id"]),
            slug=slug,
            season_year=season_year,
            as_of_date=str(team["as_of_date"]),
            surface=SURFACE_PREVIEW_THESIS,
            claim_type=CLAIM_TYPE_THESIS,
            claim_payload=candidate,
            evidence=evidence,
            evidence_hash=str(evidence["evidence_hash"]),
            prompt_template_id=PROMPT_TEMPLATE_ID,
            model_id=generation.model_id,
            model_backend=generation.backend,
            voice_score=validation.voice_score,
            fact_score=validation.fact_score,
            slop_score=validation.slop_score,
            confidence_band=str(candidate.get("confidence_band") or "unset"),
        )
        report.approved += 1
        report.errors.append({"slug": slug, "claim_key": key, "status": "approved"})

    return report


def preview_llm_status(*, allow_cloud: bool = False) -> list[dict[str, Any]]:
    """Return Chronicle-router backend health for preview synthesis."""
    router = build_default_router(allow_cloud=allow_cloud)
    rows: list[dict[str, Any]] = []
    for route in router.routes:
        backend = route.backend
        try:
            healthy = bool(backend.health_check())
        except GenerationError:
            healthy = False
        except Exception:
            healthy = False
        rows.append({
            "role": route.role,
            "tiers": ",".join(t.value for t in route.tier_eligible),
            "backend": getattr(backend, "name", "unknown"),
            "model_id": getattr(backend, "model_id", "unknown"),
            "healthy": healthy,
        })
    return rows


def _candidate_to_dict(candidate: Any) -> dict[str, Any]:
    if hasattr(candidate, "model_dump"):
        try:
            return candidate.model_dump()
        except Exception:
            return {}
    if isinstance(candidate, dict):
        return candidate
    return {}


def _normalise_candidate_text(candidate: dict[str, Any]) -> dict[str, Any]:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }

    def norm(value: Any) -> Any:
        if isinstance(value, str):
            for old, new in replacements.items():
                value = value.replace(old, new)
            # Final pass: decompose accented chars to ASCII equivalents
            # (e.g. é→e) then strip any remaining non-ASCII bytes.
            # This prevents non_ascii_text validator failures from model
            # output that slips past the explicit replacement map above.
            value = (
                unicodedata.normalize("NFKD", value)
                .encode("ascii", "ignore")
                .decode("ascii")
            )
            return value
        if isinstance(value, list):
            return [norm(v) for v in value]
        if isinstance(value, dict):
            return {k: norm(v) for k, v in value.items()}
        return value

    return norm(candidate)


def _fix_comma_evidence_keys(candidate: dict, evidence: dict) -> dict:
    """Split comma-joined evidence_key fields into the first valid single key.

    The model sometimes writes 'evidence_key: "a.b,c.d"' (two paths joined by
    a comma) which fails the validator's key-existence check.  We split on
    comma, strip whitespace, and keep the first part that exists in the
    evidence key set (falling back to the first part unconditionally so the
    claim doesn't lose its key entirely).
    """
    from cfb_rankings.team_preview.validators import _evidence_keys, _fuzzy_list_key

    known = _evidence_keys(evidence)
    supporting = candidate.get("supporting_claims")
    if not isinstance(supporting, list):
        return candidate
    for claim in supporting:
        if not isinstance(claim, dict):
            continue
        raw_key = claim.get("evidence_key") or ""
        if "," not in raw_key:
            continue
        parts = [p.strip() for p in raw_key.split(",") if p.strip()]
        chosen = None
        for part in parts:
            if part in known:
                chosen = part
                break
            fuzzy = _fuzzy_list_key(part, known)
            if fuzzy:
                chosen = fuzzy
                break
        if chosen is None and parts:
            chosen = parts[0]  # fallback: take first segment even if unknown
        if chosen is not None:
            claim["evidence_key"] = chosen
    return candidate


def _autofill_numeric_receipts(candidate: dict, evidence: dict) -> dict:
    """Auto-populate supporting_claims.numeric_values with evidenced numbers.

    qwen3 reliably uses correct numbers from evidence but forgets to list them
    in numeric_values. We scan each supporting_claim.text (plus headline/body)
    for non-year, non-decimal-score numerals that ARE present in the evidence
    packet and add them to the appropriate numeric_values list.  This turns
    formatting failures into passes without changing any factual content.
    """
    allowed = _allowed_numbers(evidence)
    supporting = candidate.get("supporting_claims")
    if not isinstance(supporting, list) or not supporting:
        return candidate

    def _coerce_numeric_list(nums: object) -> list[float]:
        if not isinstance(nums, list):
            return []
        out: list[float] = []
        for n in nums:
            try:
                out.append(float(n))
            except (TypeError, ValueError):
                pass
        return out

    def _add_evidenced_numbers(text: str, nums: list[float]) -> list[float]:
        existing_candidates: set[str] = set()
        for n in nums:
            existing_candidates.update(_number_candidates(n))
        for token in _numbers_in_text(text):
            if _is_year_token(token):
                continue
            if _is_internal_decimal_score(token):
                continue
            if not _number_supported(token, allowed):
                continue
            # Already covered by an existing numeric_value?
            if _number_supported(token, existing_candidates):
                continue
            try:
                fval = float(token)
            except (TypeError, ValueError):
                continue
            nums.append(fval)
            existing_candidates.update(_number_candidates(fval))
        return nums

    # Collect all numbers from headline + body and attach to first claim
    headline = str(candidate.get("headline") or "")
    body = str(candidate.get("body") or "")
    first_claim = supporting[0]
    if isinstance(first_claim, dict):
        first_claim["numeric_values"] = _add_evidenced_numbers(
            headline + " " + body,
            _coerce_numeric_list(first_claim.get("numeric_values")),
        )

    # Per-claim: add numbers from its own text
    for claim in supporting:
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("text") or "")
        claim["numeric_values"] = _add_evidenced_numbers(
            text,
            _coerce_numeric_list(claim.get("numeric_values")),
        )

    return candidate


_APPROX_RANK_RE = re.compile(r"\btop[- ](\d+)\b", re.IGNORECASE)


def _fix_approximate_ranks(candidate: dict, evidence: dict) -> dict:
    """Replace 'top-N' / 'top N' phrases with '#N' when N is evidence-backed.

    The validator rejects approximate_rank_phrase but the model often writes
    'top-10' or 'top 25' instead of '#10' or '#25'. We repair in-place:
    only substitute when the integer N appears in allowed_numbers from evidence.
    """
    allowed = _allowed_numbers(evidence)

    def _repair_text(text: str) -> str:
        def _replace(m: "re.Match[str]") -> str:
            n = m.group(1)
            if _number_supported(n, allowed):
                return f"#{n}"
            return m.group(0)  # leave unchanged if N not in evidence
        return _APPROX_RANK_RE.sub(_replace, text)

    def _walk(node: object) -> object:
        if isinstance(node, str):
            return _repair_text(node)
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        return node

    return _walk(candidate)  # type: ignore[return-value]


def _strip_internal_decimal_scores(candidate: dict, evidence: dict) -> dict:
    """Replace raw internal decimal scores (0.xxx) with evidence labels.

    The model sometimes outputs 'reload_score of 0.662' instead of a human
    label. We look for the score value in the evidence's label-adjacent keys
    and substitute when possible, otherwise replace with 'N/A'.
    """
    _DECIMAL_RE = re.compile(r"(?<!\d)(0\.\d+)(?!\d)")

    # Build a map: float → nearest label string from evidence text fields
    def _label_map_from_evidence(ev: dict) -> dict[str, str]:
        """Walk evidence for paired (score, label) neighbours."""
        label_map: dict[str, str] = {}
        # Roster reload summary has convenient pairs like reload_score + label fields
        reload = ev.get("roster_reload") or {}
        label_fields = {
            "reload_score": reload.get("reload_profile_label") or reload.get("returning_profile_label"),
            "continuity_score": reload.get("continuity_score"),  # no label
            "volatility_score": reload.get("volatility_score"),  # no label
            "portal_addition_score": reload.get("portal_addition_score"),
            "portal_loss_score": reload.get("portal_loss_score"),
        }
        for field, label in label_fields.items():
            score = reload.get(field)
            if score is not None and label and isinstance(label, str):
                try:
                    key = f"{float(score):.3f}"
                    label_map[key] = label
                except (TypeError, ValueError):
                    pass
        return label_map

    label_map = _label_map_from_evidence(evidence)

    def _repair_text(text: str) -> str:
        def _replace(m: "re.Match[str]") -> str:
            raw = m.group(1)
            try:
                fval = float(raw)
            except (TypeError, ValueError):
                return m.group(0)
            if not (0 < fval < 1):
                return m.group(0)
            # Try to find a label from the evidence
            key = f"{fval:.3f}"
            label = label_map.get(key)
            if label:
                return f'"{label}"'
            # No label available — use a qualitative descriptor so we
            # don't introduce a bare integer that isn't in allowed_numbers
            # (e.g. "66%" contains "66" which triggers unsupported_numeric_text)
            if fval < 0.25:
                return '"low"'
            elif fval < 0.45:
                return '"below-average"'
            elif fval < 0.60:
                return '"moderate"'
            elif fval < 0.75:
                return '"above-average"'
            else:
                return '"high"'

        return _DECIMAL_RE.sub(_replace, text)

    def _walk(node: object) -> object:
        if isinstance(node, str):
            return _repair_text(node)
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        return node

    return _walk(candidate)  # type: ignore[return-value]


def _repair_prompt(original_prompt: str, violations: list[str]) -> str:
    violation_text = "\n".join(f"- {v}" for v in violations[:12])
    return f"""{original_prompt}

The previous JSON candidate failed validation:
{violation_text}

Return a corrected JSON object only.
Rules for the repair:
- Remove unsupported claims instead of explaining them.
- Use only ASCII text.
- Use only numeric values present in the evidence.
- Put every number used in headline/body/supporting text into supporting_claims.numeric_values.
- Use one evidence_key path exactly as it appears in the evidence packet; do not comma-join paths.
- Headline must not end with a dangling word like despite, while, with, and, or but.
- Body must start with an uppercase letter and stand alone as complete prose.
- Use exact ranks like #3; do not write approximate phrases like top-10.
- Do not write raw internal decimal scores like 0.294; use the evidence labels instead.
"""


def _log_usage(
    *,
    model_id: str,
    backend_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_s: float,
    success: bool,
    error_kind: str | None,
    evidence_hash: str,
    validator_scores: dict[str, float] | None = None,
) -> None:
    try:
        from cfb_rankings.team_pages.llm_usage_log import append_llm_usage

        append_llm_usage(
            subcommand="team_preview.generate_claim",
            model=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_s=duration_s,
            extra={
                "surface": SURFACE_PREVIEW_THESIS,
                "prompt_version": PROMPT_TEMPLATE_ID,
                "model_backend": backend_name,
                "fell_back": not success,
                "fallback_reason": error_kind,
                "error_kind": error_kind,
                "evidence_hash": evidence_hash,
                "validator_scores": validator_scores or {},
            },
            cost_usd=0.0,
        )
    except Exception:
        return
