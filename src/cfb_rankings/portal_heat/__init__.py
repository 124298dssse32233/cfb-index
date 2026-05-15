"""Transfer Portal Heat Index (S3 surface).

DESIGN_AUDIT_2026_05_15_v5_4.md Part 4 §S3:
  URL:       /portal-heat/
  Cadence:   3x/day during open windows (Dec, Apr-May); 1x/day otherwise.
  Renderer:  this package.
  Data:      portal_moves (populated by wire/ingestion.py Adapter 1),
             team_brand_assets (program colors), player_recruiting_profiles
             (star ratings if available).

Surface a Top-25 board of programs ranked by net Δ talent (entries -
exits, weighted by star rating when known, fallback to raw count) over
the last `days` window.

When `portal_moves` is empty, the renderer produces a valid
empty-state HTML page rather than crashing — see `renderer.render_index`
and the EMPTY_LEDE branch.

Public surface:
    data.fetch_program_churn(db, days)   -> list[ProgramChurn]
    data.last_entry_age_days(db)         -> int | None
    renderer.render_index(db, output_dir, days, now) -> Path
    renderer.render_all(db, output_dir, days, now)   -> dict
"""
from cfb_rankings.portal_heat.renderer import render_all, render_index  # noqa: F401
from cfb_rankings.portal_heat.data import (  # noqa: F401
    ProgramChurn,
    PortalMover,
    fetch_program_churn,
    last_entry_age_days,
    compute_net_delta,
)

__all__ = [
    "ProgramChurn",
    "PortalMover",
    "compute_net_delta",
    "fetch_program_churn",
    "last_entry_age_days",
    "render_all",
    "render_index",
]
