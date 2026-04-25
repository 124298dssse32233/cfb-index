"""Storyline Threads — Sprint 10.

Persistent narrative threads with chapters that compound canon over time.
Strategy: docs/COMMUNAL_ENGAGEMENT_STRATEGY.md §"Storyline Threads".
Voice: docs/CHRONICLE_EDITORIAL_BRIEF.md (Beat-Writer Test, banned
phrases, source-citation rigor).

Module layout:
    seeds/                 — per-thread metadata + chapters (Python data)
    seed_loader.py         — reads seed modules → upserts to SQLite
    renderer.py            — DB → standalone HTML in output/site/storylines/
    render_helpers.py      — markdown-light, drop cap, citation formatter
    templates/             — HTML skeletons with ${slot} placeholders

Public API:
    seed_loader.load_all_seeds(db)       — full re-seed (metadata + chapters)
    renderer.render_all(db, output_dir)  — re-render all 8 threads + index
    renderer.emit_homepage_threads_json  — Sprint 9 contract emission
"""

__all__ = [
    "seed_loader",
    "renderer",
    "render_helpers",
]
