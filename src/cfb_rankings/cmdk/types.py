"""SearchItem dataclass + ItemKind Literal."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ItemKind = Literal[
    "team", "profile", "player", "edition", "mailbag",
    "conference", "methodology",
]

KIND_VALUES: tuple[str, ...] = (
    "team", "profile", "player", "edition", "mailbag",
    "conference", "methodology",
)


@dataclass(frozen=True)
class SearchItem:
    """One indexable item in the Cmd-K search payload.

    Field semantics:
      kind         — category (renders the chip color/group in the overlay)
      title        — primary display string (the searchable text)
      url          — destination on hit
      subtitle     — optional secondary line (e.g. team name for a player,
                     date for an edition, conference for a team)
      tier         — optional sort/relevance signal (lower = higher priority)
                     Profile slugs get tier 1; FBS teams tier 2; FCS tier 3;
                     DII/DIII tier 4. Editions tier by recency.
      aliases      — alternate strings the search should match (e.g.
                     "rolltide" → "Alabama"; "RJ" → "Rammer Jammer")
    """
    kind: ItemKind
    title: str
    url: str
    subtitle: str = ""
    tier: int = 5
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        """JSON-serialization shape — keys match what the overlay JS expects."""
        d = {
            "kind": self.kind,
            "title": self.title,
            "url": self.url,
        }
        if self.subtitle:
            d["subtitle"] = self.subtitle
        if self.tier != 5:
            d["tier"] = self.tier
        if self.aliases:
            d["aliases"] = list(self.aliases)
        return d


__all__ = ["ItemKind", "SearchItem", "KIND_VALUES"]
