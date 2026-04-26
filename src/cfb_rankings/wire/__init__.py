"""The Wire — Sprint 12.

Daily transaction wire with editorial captions per entry.

Surfaces:
  * output/site/wire/index.html        — last 30 days (rolled out by render_wire)
  * output/site/wire/archive/<YYYY-MM>.html — monthly archives
  * Homepage section (THE WIRE) — latest 8 entries patched in by
    homepage_integration.refresh_homepage_wire_block.

Pipeline:
  1. ingestion.collect_recent_actions(db, days=N)
        Pulls candidate transactions from existing CFBD / portal /
        coaching-news adapters when reachable, falls back to a
        deterministic synthesised seed when offline. Inserts into
        wire_entries with action + provenance only — editorial fields
        empty.
  2. editorial.generate_editorial_for_pending(db)
        For every row missing why_it_matters: generates a fan-voice
        sentence, an optional historical_comp, and an impact_label /
        impact_color triplet. Validates with voice_validator before
        committing. One retry on failure; second-failure rows fall back
        to a factual restatement.
  3. renderer.render_wire(db, days=30)
        Writes output/site/wire/index.html and the monthly archive
        pages.
  4. homepage_integration.refresh_homepage_wire_block(db)
        Patches output/site/index.html — replaces the existing stubbed
        Wire <tbody> with live DB rows.

Concurrency: the module owns its own files exclusively; the only shared
write target is output/site/index.html, where it edits *only* the
delimited Wire <tbody> region (search + replace inside a marker pair).
That makes it safe to run while another sprint regenerates the rest of
the homepage.
"""
from __future__ import annotations

__all__ = [
    "ingestion",
    "editorial",
    "renderer",
    "homepage_integration",
    "impact_scorer",
]
