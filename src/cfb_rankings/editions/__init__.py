"""Edition framework — Sprint 9.

The Edition is the weekly magazine-cover surface that ties the homepage to
a coherent editorial theme, a cover viz, a cover essay, and 5 secondary
features. Schema lives in ``migrations/20260425_09_editions_schema.sql``.

Disjoint from ``reporting.py`` and ``team_pages``. The single integration
point is ``reporting.py``'s homepage write path (the documented exception
in CLAUDE.md), which delegates to ``editions.homepage_renderer.render_homepage``
when an active edition exists.

Module layout:
    data.py             — DAO + dataclasses for editions / features / voices
    voice_validator.py  — banned-phrase + register check
    theme_resolver.py   — picks theme + dek + viz_kind for a publish date
    viz_templates/      — 7 SVG viz template renderers
    homepage_renderer.py— renders output/site/index.html per Figma 73:2
    article_renderer.py — renders article pages for cover essay + features
    seeds.py            — seed content for the 4 backfilled editions
    cli.py              — manage.py subcommand registrations
    stub_data/          — Wave 2 placeholder JSON (threads, canon, wire, daily)
"""
from __future__ import annotations

from .data import (
    Edition,
    EditionFeature,
    EditionVoice,
    fetch_active_edition,
    fetch_edition,
    fetch_edition_features,
    fetch_edition_voices,
    list_editions,
    upsert_edition,
    upsert_feature,
    upsert_voice,
)
from .homepage_renderer import render_homepage

__all__ = [
    "Edition",
    "EditionFeature",
    "EditionVoice",
    "fetch_active_edition",
    "fetch_edition",
    "fetch_edition_features",
    "fetch_edition_voices",
    "list_editions",
    "upsert_edition",
    "upsert_feature",
    "upsert_voice",
    "render_homepage",
]
