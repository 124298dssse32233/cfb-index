"""Tier-1 bespoke illustration URLs.

The CFB Index has 36 bespoke illustrations produced from the locked
style bible (CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md / IDENTITY_PRODUCTION_
PLAYBOOK.md / CHATGPT_VISUAL_SYSTEM_RUNBOOK.md):

  - 18 archetype totems (e.g. "anxious-dynasty" = crumbling stone crown)
  -  8 modifier glyphs (e.g. "state-identity" = state outline w/ star)
  -  8 section rubrics (e.g. "the-mood-index" = pulsewave in circle)
  -  2 master plates (author_portrait, totem_master) — internal style
     reference, can also serve as byline avatar.

Each is published in two sizes per the visual concept:
  - totems: 80px (chip) + 600px (editorial portrait)
  - modifiers: 48px (chip) + 200px (larger)
  - rubrics: 40px (section header) + 128px (large)
  - masters: 400px

This module is the canonical URL emitter. Renderers should call these
helpers rather than hardcoding paths.
"""
from __future__ import annotations

from typing import Iterable

_ILLUSTRATIONS_ROOT = "/assets/illustrations"

# Cross-check at import time: any archetype slug in the existing code that
# matches a known totem produces a valid totem URL. Adding a new totem to
# the static_assets/illustrations/totems/ directory is the only step
# needed to extend coverage.
_TOTEM_SLUGS: frozenset[str] = frozenset({
    "anxious-dynasty",
    "celebrity-appointment",
    "coach-cult",
    "content-mid-major",
    "generational-hope",
    "hbcu-standard",
    "hopeful-uprising",
    "identity-crisis-blueblood",
    "mercenary",
    "newly-crowned",
    "perpetual-believer",
    "petulant-blueblood",
    "quiet-professional",
    "regional-identity",
    "service-academy",
    "sleeper",
    "stockholm-syndrome",
    "wounded-giant",
})

_MODIFIER_SLUGS: frozenset[str] = frozenset({
    "academic-cousin",
    "faith-based",
    "independent",
    "pedigree-entitled",
    "rivalry-defined",
    "scorned-ex",
    "sibling-school",
    "state-identity",
})

# Maps section title (case-insensitive, normalized) → rubric filename stem.
_RUBRIC_SLUGS: frozenset[str] = frozenset({
    "hype-vs-reality",
    "the-commiseration",
    "the-lexicon",
    "the-mood-index",
    "the-rivalry",
    "the-taxonomy",
    "the-ticker",
    "this-weeks-cards",
})

_VALID_TOTEM_SIZES: frozenset[int] = frozenset({80, 600})
_VALID_MODIFIER_SIZES: frozenset[int] = frozenset({48, 200})
_VALID_RUBRIC_SIZES: frozenset[int] = frozenset({40, 128})


def totem_url(slug: str, size: int = 80) -> str | None:
    """Return the URL for an archetype totem at the requested size.

    Returns None when the slug isn't a known totem. Callers should treat
    None as "fall back to text-only rendering" rather than erroring.
    """
    if slug not in _TOTEM_SLUGS:
        return None
    if size not in _VALID_TOTEM_SIZES:
        size = 80  # default to chip size
    return f"{_ILLUSTRATIONS_ROOT}/totems/{slug}-{size}.png"


def modifier_url(slug: str, size: int = 48) -> str | None:
    """Return the URL for a modifier glyph at the requested size."""
    if slug not in _MODIFIER_SLUGS:
        return None
    if size not in _VALID_MODIFIER_SIZES:
        size = 48
    return f"{_ILLUSTRATIONS_ROOT}/modifiers/{slug}-{size}.png"


def rubric_url(slug: str, size: int = 40) -> str | None:
    """Return the URL for a section rubric icon at the requested size."""
    if slug not in _RUBRIC_SLUGS:
        return None
    if size not in _VALID_RUBRIC_SIZES:
        size = 40
    return f"{_ILLUSTRATIONS_ROOT}/rubrics/{slug}-{size}.png"


def author_portrait_url(size: int = 400) -> str:
    """Return the URL for the byline author portrait.

    The CFB Index's fictional editor-in-chief — a leprechaun-as-Gilded-Age
    sporting editor halftone hedcut. Used as byline avatar on editorial
    surfaces (Daily, Mailbag, Reactions, Storylines).
    """
    return f"{_ILLUSTRATIONS_ROOT}/masters/author_portrait-{size}.png"


def all_totem_slugs() -> Iterable[str]:
    """Iterate over all known totem slugs (alphabetical)."""
    return sorted(_TOTEM_SLUGS)


def all_modifier_slugs() -> Iterable[str]:
    return sorted(_MODIFIER_SLUGS)


def all_rubric_slugs() -> Iterable[str]:
    return sorted(_RUBRIC_SLUGS)
