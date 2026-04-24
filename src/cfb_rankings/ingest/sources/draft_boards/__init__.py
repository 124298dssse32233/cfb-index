"""Mock draft board adapters — Autopilot v1 TASK 4.6.

One subclass per analyst (Kiper/Jeremiah/Walter/CBS). Each parses the
public mock-draft page and writes rows to player_draft_projection.

Aggregator reads all subclasses' rows + a freshness cutoff to produce
a consensus band for the player page's "2026 Outlook · Draft Grade"
cell (TASK 7.2).
"""

from cfb_rankings.ingest.sources.draft_boards.base import DraftBoardAdapter

__all__ = ["DraftBoardAdapter"]
