"""Chronicle Visuals — deterministic, visual-first Chronicle layer.

See CHRONICLE_QUALITY_PROPOSAL_v3.md for the design rationale.

Architecture:
    trusted data query
      -> deterministic frame and metric computation
      -> Visual Director (Python rule engine in v1)
      -> deterministic SVG/PNG renderer
      -> visual QA gates
      -> chronicle_visual_cache
      -> team-page render slot

Public API:
    generate_visuals_for_team(db, slug, season_year, week_number) -> list[VisualResult]
    fetch_visual_cards(db, slug, ...) -> list[dict]    # consumer hook for team_pages
    apply_migration(db) -> None                         # idempotent schema bootstrap
"""
from __future__ import annotations

__version__ = "1.0.0"

SCHEMA_VERSION = "v3.0"


def _compute_renderer_version() -> str:
    """Derive renderer version from a short hash of the renderer modules.

    Bumps automatically when any chart family or the dispatch pipeline
    changes — no manual version bump required. Falls back to a static
    string if the package is read-only or files can't be hashed.
    """
    import hashlib
    from pathlib import Path

    here = Path(__file__).parent
    # Files whose content determines visual output
    targets = [
        here / "pipeline.py",
        here / "scorer.py",
        here / "queries.py",
        here / "share_renderer.py",
        here / "families" / "ladder.py",
        here / "families" / "waterfall.py",
        here / "families" / "braid.py",
        here / "families" / "tilemosaic.py",
    ]
    h = hashlib.sha256()
    try:
        for p in targets:
            if p.exists():
                h.update(p.read_bytes())
        return f"v1.{h.hexdigest()[:8]}"
    except Exception:
        return "v1.0.0"


# Renderer version derived from module bytes — changing any renderer file
# automatically invalidates the visual cache for affected entries.
RENDERER_VERSION = _compute_renderer_version()

from .models import (
    VisualSpec,
    VisualReceipt,
    VisualResult,
    VisualQualityScore,
    ChartFamily,
    VisualId,
)
from .scorer import score_visual, VISUAL_SUPPRESS_THRESHOLD
from .registry import (
    list_registered_visuals,
    get_query_function,
    get_renderer_function,
)
from .pipeline import (
    generate_visuals_for_team,
    generate_visuals_for_player,
    generate_all_visuals,
)
from .cache import (
    fetch_visual_cards,
    store_visual,
    get_cached_visual,
    promote_visual_lkg,
)

__all__ = [
    "RENDERER_VERSION",
    "SCHEMA_VERSION",
    "VisualSpec",
    "VisualReceipt",
    "VisualResult",
    "VisualQualityScore",
    "ChartFamily",
    "VisualId",
    "score_visual",
    "VISUAL_SUPPRESS_THRESHOLD",
    "list_registered_visuals",
    "get_query_function",
    "get_renderer_function",
    "generate_visuals_for_team",
    "generate_visuals_for_player",
    "generate_all_visuals",
    "fetch_visual_cards",
    "store_visual",
    "get_cached_visual",
    "promote_visual_lkg",
]
