"""Rituals strip — Sprint v5-8.5 deliverable.

Renders the rituals strip on a profile-archetype team page. Reads
``profile.frontmatter['rituals']`` and emits the horizontal-scroll-on-
mobile / 5-column-grid-on-desktop strip per the mockup_02 locked design.

Public API:
    from cfb_rankings.team_pages.rituals_module import (
        render_rituals_strip,
        render_cultural_anchors,
        render_visual_identity_chip,
    )
    html = render_rituals_strip(profile)
    if not html:
        # Profile has no rituals — caller renders empty-state placeholder
        # OR omits the section entirely. Tier-B teams currently fall here
        # since they ship rituals later in v5-8.5 editorial curation.

The module is renderer-only: it takes a Profile dataclass and emits
HTML. The data source is ``profiles/<slug>.md`` which Window A's commit
95e7d5dd52 populated for all 16 remaining teams (alabama landed earlier).

Mockup reference: ``docs/mockups/mockup_02_team_alabama_v2.html``
Spec reference: IMPLEMENTATION_PLAN_v2_addendum.md §"Sprint v5-8.5"
Integration: see docs/design-system/34-integration-playbook.md Pattern 6
            (the team-page renderer imports + calls this module just
             below the program-hero block and just above the chronicle
             section)
"""

from __future__ import annotations

import html as _html
import logging as _log
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .profile_loader import Profile


log = _log.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier-aware caption text — short editorial intro per tier
# ---------------------------------------------------------------------------

_TIER_INTRO: dict[int, str] = {
    1: "Things this fanbase does every Saturday — none of them invented in the last decade.",
    2: "The rituals that anchor a Saturday in this program's world.",
    5: "Three gameday rituals — the ones outsiders never quite catch.",
    9: "Three small things — but they're the program.",
}


# ---------------------------------------------------------------------------
# Rituals strip
# ---------------------------------------------------------------------------

def render_rituals_strip(profile: "Profile") -> str:
    """Return the rituals strip HTML for a profile, or empty string.

    Empty string means:
      - The profile has no ``rituals`` key, OR
      - The ``rituals`` list is empty, OR
      - Every entry is missing the required ``name`` field

    The caller decides whether to render an empty-state placeholder or
    omit the section entirely; this module never fabricates.

    Output structure matches ``docs/mockups/mockup_02_team_alabama_v2.html``
    so the existing _mockup_shared.css selectors apply unchanged.
    """
    rituals = (profile.frontmatter.get("rituals") or [])
    rituals = [r for r in rituals if isinstance(r, dict) and r.get("name")]
    if not rituals:
        return ""

    tier = int(profile.frontmatter.get("program_tier", 5) or 5)
    intro = _TIER_INTRO.get(tier, _TIER_INTRO[5])
    cards_html = "\n".join(_render_ritual_card(r) for r in rituals[:5])
    return f"""\
<section class="rituals program-section" aria-label="{_html.escape(profile.frontmatter.get('display_name', profile.slug))} rituals">
  <div class="program-section__head">
    <h2 class="section-title">Rituals<span class="section-title__rule"></span></h2>
    <p class="caption" style="max-width: 36ch;">{_html.escape(intro)}</p>
  </div>
  <div class="rituals-track" role="list">
{cards_html}
  </div>
</section>"""


def _render_ritual_card(ritual: dict[str, Any]) -> str:
    """Render one ritual card. Defensive against missing fields."""
    name = _html.escape(str(ritual.get("name", "")))
    when = _html.escape(str(ritual.get("when", "") or "gameday"))
    when_short = when.split(";", 1)[0].split(",", 1)[0].strip().lower()
    # Compact when_short for the small caption under the monogram
    when_caption = _html.escape(_shorten_when(when_short))
    # The cards use a 2-letter monogram derived from the name
    monogram = _make_monogram(str(ritual.get("name", "")))
    started_year = ritual.get("started_year")
    since_text = (
        f"since {_html.escape(str(started_year))}"
        if started_year is not None else ""
    )
    description = _html.escape(str(ritual.get("description", "") or ""))
    return f"""    <article class="ritual-card" role="listitem" data-significance="{_html.escape(str(ritual.get('cultural_significance', 'medium')))}">
      <div class="ritual-card__glyph" aria-hidden="true">{monogram}<small>{when_caption}</small></div>
      <h3 class="ritual-card__name">{name}</h3>
      <p class="ritual-card__since">{since_text}</p>
      <p class="ritual-card__description visually-hidden">{description}</p>
    </article>"""


def _make_monogram(name: str) -> str:
    """Make a 2-letter monogram from a ritual name.

    Examples:
        "Rammer Jammer"            → RJ
        "Yea Alabama (Fight Song)" → YA
        "Elephant Walk"            → EW
        "Pregame Flyover"          → PF
        "Million Dollar Band Halftime" → MD
        "The Walk of Champions"    → WC (drops "The")
        "VolNavy"                  → VN
    """
    # Strip parenthetical content + everything after a colon/dash
    stripped = name.split("(", 1)[0].split(":", 1)[0].split(" — ", 1)[0].strip()
    words = [w for w in stripped.split() if w.lower() not in {"the", "of", "a", "and"}]
    if not words:
        return name[:2].upper()
    if len(words) == 1:
        # Single word — take first 2 chars
        return words[0][:2].upper()
    # Multi-word — take first letter of first two words
    return (words[0][:1] + words[1][:1]).upper()


def _shorten_when(when: str) -> str:
    """Compress the `when` field to a single short caption."""
    # Heuristic mappings for common patterns
    when = when.lower()
    if "kickoff" in when:
        return "kickoff"
    if "after victory" in when or "post-win" in when:
        return "victory"
    if "entrance" in when or "team entrance" in when:
        return "entrance"
    if "halftime" in when:
        return "halftime"
    if "pregame" in when or "flyover" in when:
        return "pregame"
    if "score" in when:
        return "scoring"
    if "anthem" in when:
        return "anthem"
    return when[:18]


# ---------------------------------------------------------------------------
# Cultural anchors — optional editorial sidebar
# ---------------------------------------------------------------------------

def render_cultural_anchors(profile: "Profile") -> str:
    """Render the cultural-anchors block, or empty string when absent.

    Spec data shape (per v5-8.5 alabama profile):
        cultural_anchors:
          one_sentence: "..."
          if_team_didnt_exist_cfb_would_lose: "..."
          fan_archetype_dominant: "..."
          outsider_archetype_dominant: "..."
    """
    ca = profile.frontmatter.get("cultural_anchors")
    if not ca or not isinstance(ca, dict):
        return ""
    one_sentence = ca.get("one_sentence")
    if not one_sentence:
        return ""
    fan_arch = ca.get("fan_archetype_dominant")
    outsider_arch = ca.get("outsider_archetype_dominant")
    if_lost = ca.get("if_team_didnt_exist_cfb_would_lose")
    arch_row = ""
    if fan_arch or outsider_arch:
        arch_row = (
            '<dl class="cultural-anchors__archetypes">'
            + (f'<dt>From inside</dt><dd>{_html.escape(str(fan_arch))}</dd>' if fan_arch else "")
            + (f'<dt>From outside</dt><dd>{_html.escape(str(outsider_arch))}</dd>' if outsider_arch else "")
            + '</dl>'
        )
    if_lost_row = ""
    if if_lost:
        if_lost_row = (
            '<p class="cultural-anchors__if-lost">'
            f'<strong>If the program didn\'t exist, CFB would lose</strong> '
            f'<span>{_html.escape(str(if_lost))}</span>'
            '</p>'
        )
    return f"""\
<aside class="cultural-anchors" aria-label="Cultural identity">
  <p class="cultural-anchors__one-sentence">{_html.escape(str(one_sentence))}</p>
  {arch_row}
  {if_lost_row}
</aside>"""


# ---------------------------------------------------------------------------
# Visual identity chip — eyebrow-line hint at the helmet/colors register
# ---------------------------------------------------------------------------

def render_visual_identity_chip(profile: "Profile") -> str:
    """Tiny chip showing helmet stripe pattern + signature color combo."""
    vi = profile.frontmatter.get("visual_identity_anchors")
    if not vi or not isinstance(vi, dict):
        return ""
    helmet = vi.get("helmet_stripe_pattern")
    colors = vi.get("signature_color_combination")
    if not helmet and not colors:
        return ""
    parts = []
    if helmet:
        parts.append(f'<span class="vi-chip__helmet">{_html.escape(str(helmet))}</span>')
    if colors:
        parts.append(f'<span class="vi-chip__colors">{_html.escape(str(colors))}</span>')
    return (
        '<div class="vi-chip" aria-label="Visual identity">'
        + ' · '.join(parts)
        + '</div>'
    )


__all__ = [
    "render_rituals_strip",
    "render_cultural_anchors",
    "render_visual_identity_chip",
]
