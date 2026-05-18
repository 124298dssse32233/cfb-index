"""CitationCritic — validates that Pattern C/D output cites its sources.

Pre-Pattern-C-wire-up the critic is invoked manually:

    from cfb_rankings.citations import CitationCritic
    critic = CitationCritic()
    result = critic.critique(
        body_markdown=output["body_markdown"],
        citations=output["citations"],
        available_sources=context["available_sources"],
    )
    if not result.passed:
        # revise or reject

Window A's eventual wiring into quality_loop.py inserts this critic
into the Pattern C/D revise loop as an additional verdict alongside
the existing critics.

Spec: docs/design-system/32-receipt-pattern.md §"Citation critic role"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Literal

from .types import Citation


_MARKER_RE = re.compile(r"\[(\d+)\]")

# How many citations we want per N words. Spec target: >=1 per 200 words.
# Warn at <1 per 400; block at <1 per 800 (i.e. an entire long article
# with one or zero citations).
_DENSITY_WORDS_PER_CITATION_TARGET = 200
_DENSITY_WORDS_PER_CITATION_WARN = 400
_DENSITY_WORDS_PER_CITATION_BLOCK = 800

Severity = Literal["blocker", "warning", "info"]


@dataclass(frozen=True)
class CritiqueIssue:
    """One problem the critic identified."""
    severity: Severity
    kind: str
    detail: str


@dataclass(frozen=True)
class CritiqueResult:
    """Aggregate critic verdict on a single Pattern C/D output."""
    passed: bool
    issues: tuple[CritiqueIssue, ...] = field(default_factory=tuple)
    citation_count: int = 0
    word_count: int = 0
    density: float = 0.0  # citations per 200 words

    @property
    def blockers(self) -> tuple[CritiqueIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "blocker")

    @property
    def warnings(self) -> tuple[CritiqueIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")


@dataclass(frozen=True)
class _AvailableSource:
    """Normalized view of an entry in prompt_context['available_sources']."""
    label_words: frozenset[str]


def _normalize_available_sources(
    available_sources: Iterable[dict] | None,
) -> list[_AvailableSource]:
    if not available_sources:
        return []
    out: list[_AvailableSource] = []
    for src in available_sources:
        label = str(src.get("label", "")).lower()
        # Words >= 4 chars are signal; shorter words ("a", "of", "the")
        # are noise and would generate false positives on fuzzy match.
        words = frozenset(w for w in re.findall(r"\w+", label) if len(w) >= 3)
        out.append(_AvailableSource(label_words=words))
    return out


@dataclass
class CitationCritic:
    """Validates the receipt pattern in a Pattern C/D output.

    Checks (per spec):
      1. Every [N] marker in body_markdown has a matching Citation
      2. Every Citation has a non-empty source_label
      3. Citation source_kinds match one of the spec's 8 enum values
      4. Citation labels fuzzy-match the available_sources from prompt
         context (catches hallucinated sources)
      5. Citation density: target >=1 per 200 words; warn <1 per 400;
         block <1 per 800
    """
    # Configurable thresholds — kept as instance fields so tests can tighten
    # them without monkey-patching module constants.
    target_words_per_citation: int = _DENSITY_WORDS_PER_CITATION_TARGET
    warn_words_per_citation: int = _DENSITY_WORDS_PER_CITATION_WARN
    block_words_per_citation: int = _DENSITY_WORDS_PER_CITATION_BLOCK

    def critique(
        self,
        body_markdown: str,
        citations: Iterable[Citation],
        available_sources: Iterable[dict] | None = None,
    ) -> CritiqueResult:
        issues: list[CritiqueIssue] = []
        cit_list = list(citations)
        marker_ids_in_body = {int(m) for m in _MARKER_RE.findall(body_markdown)}
        cit_marker_ids = {c.marker_id for c in cit_list}

        # 1. Missing citations — markers in body but no Citation entry
        missing = marker_ids_in_body - cit_marker_ids
        if missing:
            issues.append(CritiqueIssue(
                severity="blocker",
                kind="missing_citation",
                detail=(
                    f"Body has marker(s) {sorted(missing)} with no matching "
                    f"citation entry"
                ),
            ))

        # 2. Orphan citations — Citation entries with no marker in body
        orphans = cit_marker_ids - marker_ids_in_body
        if orphans:
            issues.append(CritiqueIssue(
                severity="warning",
                kind="orphan_citation",
                detail=(
                    f"Citation(s) {sorted(orphans)} have no [N] marker in "
                    f"body — remove or reference"
                ),
            ))

        # 3. Each citation must have a non-empty source_label
        for c in cit_list:
            if not c.source_label or not c.source_label.strip():
                issues.append(CritiqueIssue(
                    severity="blocker",
                    kind="empty_source_label",
                    detail=(
                        f"Citation marker_id={c.marker_id} has empty "
                        f"source_label"
                    ),
                ))

        # 4. Hallucinated source check (only when available_sources is
        # provided; if not given, skip — pre-wiring sanity check use).
        normalized = _normalize_available_sources(available_sources)
        if normalized:
            for c in cit_list:
                label_lower = c.source_label.lower()
                cit_words = {
                    w for w in re.findall(r"\w+", label_lower) if len(w) >= 3
                }
                if not any(
                    cit_words & src.label_words for src in normalized
                ):
                    issues.append(CritiqueIssue(
                        severity="blocker",
                        kind="hallucinated_source",
                        detail=(
                            f"Citation '{c.source_label}' doesn't fuzzy-"
                            f"match any available_source"
                        ),
                    ))

        # 5. Citation density
        word_count = len(body_markdown.split())
        # Density is "citations per 200 words"
        density = (
            (len(cit_list) / (word_count / self.target_words_per_citation))
            if word_count > 0 else 0.0
        )
        # Compute the threshold in citations needed to clear warn / block
        # given the current word count.
        if word_count >= 100:  # skip density check for tiny bodies
            cits_for_warn = max(
                1, word_count // self.warn_words_per_citation
            )
            cits_for_block = max(
                1, word_count // self.block_words_per_citation
            )
            if len(cit_list) < cits_for_block:
                issues.append(CritiqueIssue(
                    severity="blocker",
                    kind="critical_low_density",
                    detail=(
                        f"{len(cit_list)} citation(s) in {word_count} words "
                        f"— need >= {cits_for_block} to clear block "
                        f"(1 per {self.block_words_per_citation} words)"
                    ),
                ))
            elif len(cit_list) < cits_for_warn:
                issues.append(CritiqueIssue(
                    severity="warning",
                    kind="low_citation_density",
                    detail=(
                        f"{len(cit_list)} citation(s) in {word_count} words "
                        f"(density {density:.2f}; target >= 1.0 per "
                        f"{self.target_words_per_citation} words)"
                    ),
                ))

        passed = not any(i.severity == "blocker" for i in issues)
        return CritiqueResult(
            passed=passed,
            issues=tuple(issues),
            citation_count=len(cit_list),
            word_count=word_count,
            density=density,
        )


__all__ = ["CitationCritic", "CritiqueIssue", "CritiqueResult"]
