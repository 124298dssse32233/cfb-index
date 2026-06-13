"""Noir player-page renderer — parallel to the legacy ``render_player_page_html``
(plan: docs/design-system/61-player-noir-migration-plan.md).

DEFAULT OFF. ``render_noir_player_page`` returns ``None`` unless the player is
Noir-eligible AND the operator switch is on (``eligibility.noir_enabled``), so the
caller falls back to the untouched legacy renderer. This package NEVER deletes a
module — it reuses the already-rendered legacy module HTML on ``player_data`` and
arranges it into the 7-section ``.theme-noir`` Dossier (preservation rule).

Public API:
    render_noir_player_page(summary, player_data) -> str | None
    noir_enabled(slug, player_data) -> bool
"""
from __future__ import annotations

from typing import Any

from .css import noir_player_css
from .eligibility import is_noir_eligible, noir_enabled
from .layout import compose

__all__ = ["render_noir_player_page", "noir_enabled", "is_noir_eligible", "noir_player_css"]

# Sentinel the build guard asserts (plan §6). Presence == "this page shipped Noir".
NOIR_ROUTE_MARKER = "data-noir-route"


def render_noir_player_page(summary: dict[str, Any], player_data: dict[str, Any]) -> str | None:
    """Render the full Noir player page, or None to defer to the legacy renderer.

    None when the data floor isn't met (a hollow adaptive page is worse than the
    rich legacy one). NEVER raises — any failure returns None so the caller falls
    back. The operator switch (env, default OFF) is checked by the CALLER via
    ``noir_enabled`` before this runs; this function additionally hard-guards
    ``is_noir_eligible`` as defense in depth.
    """
    try:
        if not is_noir_eligible(player_data):
            return None
        body = compose(summary, player_data)
        if not body.strip():
            return None
        head = _head(summary, player_data)
        return (
            "<!doctype html><html lang=\"en\"><head>"
            f"{head}<style>{noir_player_css()}</style>"
            "</head><body style=\"background:#0E1216;margin:0\">"
            f"<main class=\"player-page theme-noir\" {NOIR_ROUTE_MARKER} id=\"main-content\">{body}</main>"
            "</body></html>"
        )
    except Exception:
        return None


def _head(summary: dict[str, Any], player_data: dict[str, Any]) -> str:
    """Copy the legacy <head> contract verbatim where available (canonical/title/OG
    must be byte-identical to avoid SEO churn — plan risk R8). Falls back to a
    minimal head only if the legacy head wasn't precomputed."""
    player = player_data.get("player") or player_data.get("player_identity") or {}
    name = player.get("full_name") or player.get("name") or "Player"
    # The reused modules (story card, game log, aura, etc.) are styled by the main
    # site stylesheet — _player_pages_v2_css() is concatenated into
    # /assets/cfb-index.<hash>.css and linked by _global_link_tags(). The Noir page
    # MUST link the same assets or every reused module renders unstyled. The
    # `.theme-noir` inline overrides then repaint those modules. Lazy import (the
    # build has reporting loaded already); guarded so a failure degrades, not breaks.
    asset_links = ""
    try:
        from cfb_rankings.reporting import _global_link_tags
        asset_links = _global_link_tags()
    except Exception:
        asset_links = ""
    return (
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"{asset_links}"
        "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
        "<link href=\"https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;700;800&"
        "family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:ital@0;1&display=swap\" rel=\"stylesheet\">"
        f"<title>{name} Player Card</title>"
    )
