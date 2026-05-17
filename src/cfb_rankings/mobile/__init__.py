"""Mobile-first UI primitives.

Sprint v5-7.6 — the Saturday Strip + bottom-nav + auto-summary deliverables.
Mockup reference: ``docs/mockups/mockup_06_saturday_strip.html``.
"""

from .saturday_strip import (
    StripState,
    StripGame,
    StripChip,
    build_strip_state,
    render_strip_html,
)

__all__ = [
    "StripState",
    "StripGame",
    "StripChip",
    "build_strip_state",
    "render_strip_html",
]
