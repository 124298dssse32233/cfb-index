"""Canonical URL composition + head chrome helpers.

The site has no custom domain — it runs on
``wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app``. Every renderer that emits an
absolute URL (canonical link, ``og:url``, ``og:image``, ``twitter:url``,
sitemap entries, JSON-LD ``@id``) MUST route through this module so a
future domain swap is a one-line code change (the ``DEFAULT_BASE_URL``
constant).

Env-var override
----------------
``CFB_INDEX_BASE_URL`` — set in CI workflows or local dev to override the
default. If unset, falls back to :data:`DEFAULT_BASE_URL`.

Public API
----------
``base_url()``                — current ``BASE_URL`` (mostly for tests).
``absolute_url(path)``        — join a site-relative path to ``BASE_URL``.
``render_head_chrome(...)``   — canonical + ``og:*`` + ``twitter:*`` meta.

Design notes
------------
The module lives in ``common/`` and intentionally has zero downstream
imports — every renderer (``reporting.py``, ``team_pages/``,
``editions/``, ``daily/``, ``retro_render.py``, …) can import from it
without risking a circular dep.

``_BASE_URL`` is captured at *import time* into a module-level
constant so call sites do not pay an ``os.environ`` lookup on every
URL composition. Tests that want to flip the value mid-process should
patch :func:`base_url` and :func:`absolute_url` directly, or call
:func:`_reload_base_url` (used by the test suite only).
"""
from __future__ import annotations

import os
from html import escape
from urllib.parse import urljoin

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The default canonical host. Change this single string when registering a
#: custom domain — every renderer picks the new value up on next build.
DEFAULT_BASE_URL = "https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app"

#: The default OG image path when a renderer doesn't pass an explicit card.
DEFAULT_OG_IMAGE = "/og/default.png"

_ENV_VAR_NAME = "CFB_INDEX_BASE_URL"


def _resolve_base_url() -> str:
    """Read the active BASE_URL from the environment (or fall back)."""
    raw = os.environ.get(_ENV_VAR_NAME) or DEFAULT_BASE_URL
    return raw.rstrip("/")


# Captured at import time. Tests can call _reload_base_url() to refresh
# after a monkeypatch on the env var.
_BASE_URL = _resolve_base_url()


def _reload_base_url() -> str:
    """Refresh the cached ``_BASE_URL`` from the environment.

    Returns the new value. Intended for the test suite — production code
    should set the env var before process start and never call this.
    """
    global _BASE_URL
    _BASE_URL = _resolve_base_url()
    return _BASE_URL


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def base_url() -> str:
    """Return the current canonical base URL (no trailing slash).

    Always reads from the live environment so tests using
    ``monkeypatch.setenv`` see the override without an explicit
    :func:`_reload_base_url` call. The slight per-call cost (one
    ``os.environ`` lookup + one ``rstrip``) is trivial against the
    cost of rendering a page.
    """
    return _resolve_base_url()


def absolute_url(path: str | None) -> str:
    """Join a site-relative path to :func:`base_url`.

    >>> absolute_url("/teams/alabama.html")
    'https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/teams/alabama.html'
    >>> absolute_url("teams/alabama.html")        # leading slash optional
    'https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/teams/alabama.html'
    >>> absolute_url("https://other.example/x")   # passthrough
    'https://other.example/x'
    >>> absolute_url("")                           # empty → base url itself
    'https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app'

    Notes
    -----
    * Already-absolute URLs (``http://`` / ``https://``) pass through
      unchanged — the helper is safe to call defensively.
    * Empty / ``None`` returns the bare base URL (callers that want
      ``"/"`` should pass it explicitly).
    * Uses :func:`urllib.parse.urljoin` under the hood so query
      strings and fragments are preserved.
    """
    base = base_url()
    if not path:
        return base
    if path.startswith(("http://", "https://")):
        return path
    return urljoin(base + "/", path.lstrip("/"))


def render_head_chrome(
    *,
    page_path: str,
    title: str | None = None,
    description: str | None = None,
    og_image_path: str | None = None,
    og_type: str = "article",
    twitter_card: str = "summary_large_image",
    site_name: str = "THE CFB INDEX",
) -> str:
    """Emit the standard head chrome block.

    Produces a multi-line HTML fragment containing:

    * ``<link rel="canonical" href="{absolute page url}">``
    * ``<meta property="og:url" content="{absolute page url}">``
    * ``<meta property="og:type" content="{og_type}">``
    * ``<meta property="og:site_name" content="{site_name}">``
    * ``<meta property="og:title" content="{title}">`` (if title given)
    * ``<meta property="og:description" content="{description}">``
      (if description given)
    * ``<meta property="og:image" content="{absolute og image url}">``
    * ``<meta name="twitter:card" content="{twitter_card}">``
    * ``<meta name="twitter:url" content="{absolute page url}">``
    * ``<meta name="twitter:title" content="{title}">`` (if title given)
    * ``<meta name="twitter:description" content="{description}">``
      (if description given)
    * ``<meta name="twitter:image" content="{absolute og image url}">``

    All user-supplied strings are HTML-escaped.

    Parameters
    ----------
    page_path
        Site-relative path of this page (e.g. ``"/teams/alabama.html"``).
        Joined to :func:`base_url` to form the canonical URL.
    title, description
        Optional meta tags. Falls through if ``None``.
    og_image_path
        Site-relative path or absolute URL to the OG image (typically a
        Pillow-rendered share card). Defaults to :data:`DEFAULT_OG_IMAGE`.
        Absolute URLs pass through unchanged.
    og_type
        ``"article"`` for editorial pages, ``"website"`` for landing
        pages.
    twitter_card
        Twitter card type. ``"summary_large_image"`` is the right answer
        for 1200×630 OG cards.
    site_name
        ``og:site_name``. Override only if a sub-property wants its own.

    Returns
    -------
    str
        Multi-line HTML fragment. Caller drops it inside ``<head>``.
        Already HTML-escaped — safe to f-string into surrounding markup.
    """
    canonical = absolute_url(page_path or "/")
    og_image = absolute_url(og_image_path or DEFAULT_OG_IMAGE)

    safe_canonical = escape(canonical, quote=True)
    safe_og_image = escape(og_image, quote=True)
    safe_site_name = escape(site_name, quote=True)
    safe_og_type = escape(og_type, quote=True)
    safe_twitter_card = escape(twitter_card, quote=True)

    lines: list[str] = [
        f'<link rel="canonical" href="{safe_canonical}">',
        f'<meta property="og:url" content="{safe_canonical}">',
        f'<meta property="og:type" content="{safe_og_type}">',
        f'<meta property="og:site_name" content="{safe_site_name}">',
    ]

    if title:
        safe_title = escape(title, quote=True)
        lines.append(f'<meta property="og:title" content="{safe_title}">')
    if description:
        safe_desc = escape(description, quote=True)
        lines.append(f'<meta property="og:description" content="{safe_desc}">')

    lines.append(f'<meta property="og:image" content="{safe_og_image}">')
    lines.append('<meta property="og:image:width" content="1200">')
    lines.append('<meta property="og:image:height" content="630">')

    lines.append(f'<meta name="twitter:card" content="{safe_twitter_card}">')
    lines.append(f'<meta name="twitter:url" content="{safe_canonical}">')
    if title:
        safe_title = escape(title, quote=True)
        lines.append(f'<meta name="twitter:title" content="{safe_title}">')
    if description:
        safe_desc = escape(description, quote=True)
        lines.append(f'<meta name="twitter:description" content="{safe_desc}">')
    lines.append(f'<meta name="twitter:image" content="{safe_og_image}">')

    return "\n".join(lines)


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_OG_IMAGE",
    "absolute_url",
    "base_url",
    "render_head_chrome",
]
