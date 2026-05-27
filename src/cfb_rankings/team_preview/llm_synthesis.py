"""Local-LLM candidate synthesis for team-preview claims."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from cfb_rankings.chronicle.runtime import (
    CardTier,
    GenerationConfig,
    GenerationError,
    Router,
    build_default_router,
)
from cfb_rankings.team_preview.evidence import canonical_fbs_slugs
from cfb_rankings.team_preview.persistence import write_preview_claim_cache
from cfb_rankings.team_preview.prompts import (
    PROMPT_TEMPLATE_ID,
    PreviewClaimCandidate,
    build_preview_claim_prompt,
    build_preview_evidence,
)
from cfb_rankings.team_preview.validators import validate_preview_claim


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
    targets = list(slugs) if slugs else sorted(canonical_fbs_slugs())
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
            return value
        if isinstance(value, list):
            return [norm(v) for v in value]
        if isinstance(value, dict):
            return {k: norm(v) for k, v in value.items()}
        return value

    return norm(candidate)


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
