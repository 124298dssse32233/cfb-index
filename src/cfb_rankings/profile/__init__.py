"""Profile archetype shared primitives.

Per ``docs/design-system/30-page-archetypes.md``, the Profile archetype
covers ``/programs/<slug>.html``, ``/players/<slug>.html``,
``/coaches/<slug>.html``, and ``/conferences/<slug>.html``. The spec
lists the renderer as **partially** existing — the 17 profiled team
slugs flow through :mod:`cfb_rankings.team_pages.renderer`; the
remaining ~17,836 player pages, 665 program pages, ~662 unprofiled team
pages, and conference pages all flow through legacy ``reporting.py``.

The two paths produce visibly different aesthetics, which is the single
most "feels broken when clicking around" issue Session 4 surfaced. The
profiled path has a tighter identity strip, structured metric tiles,
graceful "Awaiting" empty states, and a consistent module-grid rhythm;
the legacy path has its own ``.team-shell`` + ``.team-stat-ribbon``
flavor.

This module is the **starter scaffold** for the Profile-consolidation
work the v2 audit calls out as Tier 2 (multi-week). The strategy is to
extract a small set of HTML emitters that legacy renderers can adopt
incrementally — same approach the ``cfb_rankings.dashboards`` module
took for ``/heisman/`` and ``/rankings/``.

What lives here today (working primitives, callable from any renderer):

  - :func:`render_awaiting_module` — empty-state shell for missing data
  - :func:`render_profile_identity_strip` — eyebrow + name + chips header
  - :func:`render_module_grid_open` / :func:`render_module_grid_close` —
    consistent module-grid wrappers
  - :func:`render_profile_meta_footer` — methodology footer styled to
    match team_pages aesthetic

What's still TO BUILD (sized for focused future sessions):

  - The full identity-bar component matching team_pages/renderer.py's
    ``_render_hero`` (logo + record + AP/Coaches/CFP chips). The version
    here is a thinner header.
  - Profile-specific page wrapper (analogous to
    :func:`team_pages.renderer._render_page`) that legacy callers can
    invoke instead of building their own ``<html>`` document.

CSS support lives in :func:`cfb_rankings.reporting._PROFILE_PRIMITIVES_CSS_BLOCK`
(see ``reporting.py``), which contributes ``.profile-awaiting``,
``.profile-identity-strip``, ``.profile-module-grid``, and
``.profile-meta-footer`` rules to the global stylesheet.
"""
from __future__ import annotations

from html import escape as _escape


def render_awaiting_module(
    *,
    title: str,
    body: str,
    action_label: str | None = None,
    action_href: str | None = None,
    aria_label: str | None = None,
) -> str:
    """Graceful empty-state shell for missing-data scenarios.

    Use anywhere a legacy renderer would otherwise stack tiles of
    ``"Awaiting Signal"`` or render an inscrutable blank. Mirrors the
    pattern :func:`cfb_rankings.reporting._render_team_mood_card`
    arrived at after the empty-state audit — eyebrow + headline + body
    + optional "How we set the bar" link — but exposes it as a single
    callable so player pages, program pages, conference pages, and
    unprofiled team pages can all hit the same visual.

    Args
    ----
    title
        Headline text (rendered as ``<h3>``).
    body
        One- or two-sentence explanation of why the module is empty.
        Plain text (escaped); use HTML entity references like
        ``&ge;`` if you need them — they pass through unchanged.
    action_label
        Optional CTA text. If supplied with ``action_href``, renders a
        trailing "label →" link.
    action_href
        Target for the CTA. Required iff ``action_label`` is supplied.
    aria_label
        Section-level aria-label. Defaults to ``title``.

    Returns
    -------
    HTML string for a ``<section class="profile-awaiting">`` block.
    """
    aria = aria_label or title
    if action_label and action_href:
        cta = (
            f' <a class="profile-awaiting__cta" href="{_escape(action_href)}">'
            f"{_escape(action_label)} &rsaquo;</a>"
        )
    else:
        cta = ""
    return (
        f'<section class="profile-awaiting" aria-label="{_escape(aria)}">'
        f'<h3 class="profile-awaiting__title">{_escape(title)}</h3>'
        f'<p class="profile-awaiting__body">{body}{cta}</p>'
        f"</section>"
    )


def render_profile_identity_strip(
    *,
    eyebrow: str,
    name: str,
    key_meta: str = "",
    chips: list[str] | None = None,
) -> str:
    """Profile-archetype identity strip.

    Thin version of ``team_pages.renderer._render_hero``'s identity-bar.
    Renders eyebrow + ``<h1>`` + key meta string + optional chips.
    Suitable as a hero replacement on legacy renderers (program /
    conference / unprofiled-team pages) that don't have the full
    ``Profile`` dataclass + logo asset wiring.

    Args
    ----
    eyebrow
        Short uppercase eyebrow line (e.g. ``"SEC · FBS"`` for a
        conference page, ``"PROGRAM HISTORY · 1869–PRESENT"`` for a
        program page).
    name
        Display name (rendered as ``<h1>``).
    key_meta
        Optional sub-line under the wordmark. Plain string. E.g.
        ``"14 conference titles · 18 Heisman winners"``.
    chips
        Optional list of short chip labels. Renders as inline pills.

    Returns
    -------
    HTML string for a ``<section class="profile-identity-strip">``
    block.
    """
    chips_html = ""
    if chips:
        chips_html = "".join(
            f'<span class="profile-identity-strip__chip">{_escape(c)}</span>'
            for c in chips
        )
    meta_html = (
        f'<p class="profile-identity-strip__meta">{_escape(key_meta)}</p>'
        if key_meta else ""
    )
    return f"""<section class="profile-identity-strip" aria-label="Identity">
  <p class="profile-identity-strip__eyebrow">{_escape(eyebrow)}</p>
  <h1 class="profile-identity-strip__name">{_escape(name)}</h1>
  {meta_html}
  <div class="profile-identity-strip__chips">{chips_html}</div>
</section>"""


def render_module_grid_open(*, columns: int = 2) -> str:
    """Open a module-grid wrapper for Profile-archetype pages.

    Pair with :func:`render_module_grid_close`. Uses CSS grid; collapses
    to single-column on mobile via the global stylesheet's
    ``.profile-module-grid`` media query.

    Args
    ----
    columns
        Number of columns at desktop width. 1, 2, or 3 (clamped). The
        legacy ``premium-team-grid`` defaults to 2 — match that for
        cross-renderer visual consistency.
    """
    cols = max(1, min(3, columns))
    return f'<div class="profile-module-grid profile-module-grid--{cols}col">'


def render_module_grid_close() -> str:
    """Close tag for :func:`render_module_grid_open`."""
    return "</div>"


def render_profile_meta_footer(
    *,
    methodology_label: str = "How we measure this",
    methodology_href: str = "/methodology/",
    updated_text: str = "",
    sample_text: str = "",
) -> str:
    """Methodology footer matching the team_pages aesthetic.

    Drop-in for legacy renderers that have their own footer ribbon and
    want to align with the profiled-page convention. NOT a replacement
    for the global site footer (``nav.render_global_footer``) — this is
    the in-content "data depth + methodology + last-updated" block per
    archetype spec.

    Args
    ----
    methodology_label
        Link text. Defaults to "How we measure this".
    methodology_href
        Link target. Defaults to ``/methodology/``.
    updated_text
        Free text for the "Updated …" pill. Empty hides it.
    sample_text
        Free text for the sample-size pill. Empty hides it.
    """
    updated_html = (
        f'<span class="profile-meta-footer__pill">{_escape(updated_text)}</span>'
        if updated_text else ""
    )
    sample_html = (
        f'<span class="profile-meta-footer__pill">{_escape(sample_text)}</span>'
        if sample_text else ""
    )
    return f"""<footer class="profile-meta-footer" aria-label="Methodology + freshness">
  <a class="profile-meta-footer__link" href="{_escape(methodology_href)}">
    {_escape(methodology_label)} &rsaquo;
  </a>
  {updated_html}
  {sample_html}
</footer>"""


__all__ = [
    "render_awaiting_module",
    "render_profile_identity_strip",
    "render_module_grid_open",
    "render_module_grid_close",
    "render_profile_meta_footer",
]
