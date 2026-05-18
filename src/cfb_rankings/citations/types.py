"""Citation types — frozen dataclasses + literal enums.

Mirrors the TypedDict spec in docs/design-system/32-receipt-pattern.md
but as a frozen dataclass so renderer + critic can both treat citations
as immutable records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SourceKind = Literal[
    "reddit", "beat_writer", "podcast", "wikipedia",
    "official", "cfbd", "wire", "edition",
]

ConfidenceTier = Literal["primary", "supporting", "background"]

SOURCE_KIND_VALUES: tuple[str, ...] = (
    "reddit", "beat_writer", "podcast", "wikipedia",
    "official", "cfbd", "wire", "edition",
)


@dataclass(frozen=True)
class Citation:
    """One citation receipt.

    ``marker_id`` is the integer that appears as ``[N]`` in the
    accompanying ``body_markdown``. The pair ``(generation_id, marker_id)``
    is unique in the database.

    ``source_url`` may be None for non-web sources (a CFBD API call, a
    seed CSV, etc.). ``source_label`` is always populated — it's the
    display string shown in the footer.

    ``confidence`` is one of three tiers:
      * primary    — the claim's load-bearing source
      * supporting — corroborates the primary
      * background — provides framing context

    Renderer treatment doesn't visually distinguish the three today but
    the field exists so future surface work (e.g. only-show-primary in
    a compact footer) can adapt without a schema migration.
    """
    marker_id: int
    source_kind: SourceKind
    source_label: str
    source_url: str | None = None
    source_date: str | None = None
    confidence: ConfidenceTier = "supporting"
    generation_id: int | None = None
    citation_id: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "generation_id": self.generation_id,
            "marker_id": self.marker_id,
            "source_kind": self.source_kind,
            "source_url": self.source_url,
            "source_label": self.source_label,
            "source_date": self.source_date,
            "confidence": self.confidence,
        }


def citation_from_row(row: dict[str, Any]) -> Citation:
    """Build a Citation from a DB row (dict or sqlite3.Row coerced).

    Tolerates missing optional keys.
    """
    return Citation(
        marker_id=int(row["marker_id"]),
        source_kind=row["source_kind"],
        source_label=str(row["source_label"]),
        source_url=row.get("source_url"),
        source_date=row.get("source_date"),
        confidence=row.get("confidence", "supporting") or "supporting",
        generation_id=row.get("generation_id"),
        citation_id=row.get("citation_id"),
    )


__all__ = [
    "Citation",
    "ConfidenceTier",
    "SourceKind",
    "SOURCE_KIND_VALUES",
    "citation_from_row",
]
