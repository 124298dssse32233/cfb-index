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


def render_profile_identity_strip_v2(
    *,
    eyebrow: str,
    name: str,
    sub_meta: str = "",
    team_mark_html: str = "",
    stat_tiles: list[dict] | None = None,
    action_buttons: list[dict] | None = None,
    chips: list[str] | None = None,
    accent_color: str = "",
    accent_color_soft: str = "",
    aria_label: str = "Identity",
) -> str:
    """Profile-archetype identity strip — RICHER VARIANT (v2).

    Where :func:`render_profile_identity_strip` is the thin "eyebrow +
    name + chips" header suitable for conference pages, this v2 also
    carries the visual chrome needed for player / program / team
    profile pages:

      * ``team_mark_html`` — pre-rendered SVG / unicode glyph that
        appears as the identity badge (left of the name on desktop,
        above the name on mobile)
      * ``stat_tiles`` — list of ``{"label": ..., "value": ..., "sub": ...}``
        dicts; renders as a tile-grid below the wordmark
      * ``action_buttons`` — list of ``{"label": ..., "href": ...,
        "variant": "primary"|"secondary"}`` dicts; renders as a CTA
        row below the stat tiles
      * ``accent_color`` / ``accent_color_soft`` — team-specific color
        for the strip's accent rail and stat-tile borders; injected via
        CSS custom properties so callers don't have to ship per-team
        stylesheets

    This is the unblocking primitive for the Phase 3 architectural
    migration described in ``ROADMAP_TO_COMPLETE.md``. After this lands,
    ``render_program_page_html``, ``render_team_page_html`` (unprofiled),
    and ``render_player_page_html`` can each replace their bespoke
    ``<section class="hero team-hero premium-team-hero">`` blocks with
    a single primitive call.

    CSS support lives in
    :data:`cfb_rankings.reporting._PROFILE_IDENTITY_V2_CSS_BLOCK`
    (see ``reporting.py``).

    Args
    ----
    eyebrow
        Short uppercase context line. E.g. ``"FBS · BIG TEN · 2025 SEASON"``
        for a team page, ``"PROGRAM EXPLORER · 1869–PRESENT"`` for a
        program page, ``"QUARTERBACK · #16 INDIANA · CLASS OF 2026"`` for
        a player page.
    name
        Display name (rendered as ``<h1>``).
    sub_meta
        Optional sub-line under the wordmark. E.g. ``"latest conference
        era: Big Ten"`` for a program page.
    team_mark_html
        Pre-rendered HTML for the identity badge. SVG, unicode glyph,
        or empty. Caller is responsible for escaping.
    stat_tiles
        Optional list of ``{"label": str, "value": str, "sub": str}``
        dicts. Each tile renders as a stacked ``label / value / sub``
        block. Empty list omits the tile row.
    action_buttons
        Optional list of ``{"label": str, "href": str, "variant":
        "primary" | "secondary"}`` dicts. Each button renders with the
        v2 button styles. Empty list omits the action row.
    chips
        Optional list of short chip labels. Renders as inline pills
        below the action row.
    accent_color
        Optional CSS color (hex or var()) for the strip's left rail +
        stat-tile borders. Defaults to the global ``--accent-primary``.
    accent_color_soft
        Optional CSS color for stat-tile backgrounds (typically a
        ~10%-alpha tint of ``accent_color``).
    aria_label
        Section's aria-label for screen readers.

    Returns
    -------
    HTML string for a ``<section class="profile-identity-v2">`` block.
    """
    chips = chips or []
    stat_tiles = stat_tiles or []
    action_buttons = action_buttons or []

    style_parts: list[str] = []
    if accent_color:
        style_parts.append(f"--profile-v2-accent:{accent_color}")
    if accent_color_soft:
        style_parts.append(f"--profile-v2-accent-soft:{accent_color_soft}")
    style_attr = f' style="{";".join(style_parts)}"' if style_parts else ""

    sub_meta_html = (
        f'<p class="profile-identity-v2__sub-meta">{_escape(sub_meta)}</p>'
        if sub_meta else ""
    )
    team_mark_block = (
        f'<div class="profile-identity-v2__team-mark">{team_mark_html}</div>'
        if team_mark_html else ""
    )

    # Stat tiles. Sub copy uses _escape; label and value escape too,
    # but callers can pass pre-formatted numerics (e.g. "+12.4") which
    # remain readable.
    tiles_html = ""
    if stat_tiles:
        tile_items = []
        for tile in stat_tiles:
            label = _escape(str(tile.get("label", "")))
            value = _escape(str(tile.get("value", "")))
            sub = _escape(str(tile.get("sub", "")))
            sub_block = (
                f'<span class="profile-identity-v2__stat-tile-sub">{sub}</span>'
                if sub else ""
            )
            tile_items.append(
                f'<article class="profile-identity-v2__stat-tile">'
                f'<span class="profile-identity-v2__stat-tile-label">{label}</span>'
                f'<strong class="profile-identity-v2__stat-tile-value">{value}</strong>'
                f'{sub_block}'
                f'</article>'
            )
        tiles_html = (
            f'<div class="profile-identity-v2__stat-grid">{"".join(tile_items)}</div>'
        )

    # Action buttons row.
    actions_html = ""
    if action_buttons:
        action_items = []
        for action in action_buttons:
            variant = action.get("variant", "primary")
            cls = f"profile-identity-v2__action profile-identity-v2__action--{_escape(variant)}"
            action_items.append(
                f'<a class="{cls}" href="{_escape(str(action.get("href", "")))}">'
                f'{_escape(str(action.get("label", "")))}'
                f'</a>'
            )
        actions_html = (
            f'<div class="profile-identity-v2__action-row">{"".join(action_items)}</div>'
        )

    chips_html = ""
    if chips:
        chips_html = '<div class="profile-identity-v2__chips">' + "".join(
            f'<span class="profile-identity-v2__chip">{_escape(c)}</span>'
            for c in chips
        ) + "</div>"

    return f"""<section class="profile-identity-v2" aria-label="{_escape(aria_label)}"{style_attr}>
  <div class="profile-identity-v2__header">
    {team_mark_block}
    <div class="profile-identity-v2__wordmark">
      <p class="profile-identity-v2__eyebrow">{_escape(eyebrow)}</p>
      <h1 class="profile-identity-v2__name">{_escape(name)}</h1>
      {sub_meta_html}
    </div>
  </div>
  {tiles_html}
  {actions_html}
  {chips_html}
</section>"""


__all__ = [
    "render_awaiting_module",
    "render_profile_identity_strip",
    "render_profile_identity_strip_v2",
    "render_module_grid_open",
    "render_module_grid_close",
    "render_profile_meta_footer",
]
