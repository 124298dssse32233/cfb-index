"""What-Changed diff — page-state blob builder (Signature Bets S1.4).

Every player page embeds a small JSON state snapshot so the client-side
``what-changed.js`` component can diff the current load against the
reader's last visit (stored in ``localStorage``). First visits show
nothing; return visits render a compact card above the hero with up to
five natural-language bullets describing what moved.

The server-side contract is deliberately small:

- ``heisman_heat``     – integer rank (1..N) or None.
- ``standing_rung``    – integer rung id (1..17) or None.
- ``room_mentions``    – integer mention count for the primary cohort.
- ``outlook_updates``  – list of short labels, e.g. ["Davey O'Brien watch"].
- ``achievements``     – list of achievement slugs.
- ``generated_at``     – ISO8601 UTC timestamp of the current build.
- ``version``          – SHA-12 of the deterministic payload. Enables
                         "page has changed since your last visit" checks
                         without diffing every field on the client.

Backend data today carries only a subset of these fields for most
players; missing fields ship as ``None`` / ``[]`` and the diff component
quietly omits bullets it can't generate.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Any


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def build_player_state_blob(player_data: dict[str, Any]) -> dict[str, Any]:
    """Build the state snapshot embedded per-page for diff.

    The shape is append-safe: new fields land as ``None`` for older
    snapshots so returning visitors who haven't visited since the new
    field shipped don't see a spurious "changed" bullet.
    """
    room = (player_data.get("the_room") or {}) if player_data else {}
    room_sample = (room.get("sample") or {}) if isinstance(room, dict) else {}
    outlook = (player_data.get("outlook") or {}) if player_data else {}
    heisman = (player_data.get("heisman") or {}) if player_data else {}
    standing = (player_data.get("standing") or {}) if player_data else {}
    achievements = player_data.get("achievements") or []

    outlook_updates: list[str] = []
    if isinstance(outlook, dict):
        for key in ("watch_lists", "updates", "notes"):
            val = outlook.get(key)
            if isinstance(val, list):
                outlook_updates.extend(str(x) for x in val if x)

    # Achievements: emit a stable list of achievement_id strings, not the
    # full dict. Previously this used `str(a)` which produced Python repr
    # like "{'achievement_id': '...', 'display_name': '...', ...}" — those
    # repr strings leaked into the embedded JSON, broke diff stability
    # (every cosmetic change to display_name flipped the hash), and made
    # the blob ~4× larger than necessary.
    achievement_ids: list[str] = []
    for a in achievements:
        if not a:
            continue
        if isinstance(a, dict):
            aid = a.get("achievement_id")
            if aid:
                achievement_ids.append(str(aid))
        elif isinstance(a, str):
            achievement_ids.append(a)
        else:
            aid = getattr(a, "achievement_id", None)
            if aid:
                achievement_ids.append(str(aid))

    payload: dict[str, Any] = {
        "heisman_heat": _safe_int((heisman or {}).get("rank") if isinstance(heisman, dict) else None),
        "standing_rung": _safe_int((standing or {}).get("current_rung_id") if isinstance(standing, dict) else None),
        "room_mentions": _safe_int(room_sample.get("mentions")) if isinstance(room_sample, dict) else None,
        "outlook_updates": outlook_updates,
        "achievements": achievement_ids,
    }
    # Deterministic version hash — order-sensitive for lists but stable
    # across builds that produce the same values.
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["version"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    payload["generated_at"] = _dt.datetime.now(_dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return payload


def state_blob_script_tag(
    player_slug: str, state: dict[str, Any]
) -> str:
    """Emit the ``<script type="application/json">`` block the Alpine
    component reads."""
    body = json.dumps(state, separators=(",", ":"), ensure_ascii=False)
    # HTML-safe escaping for </script> sequences inside JSON strings is
    # unnecessary here because our fields are all numeric/list-of-slug;
    # we still replace a defensive </script> just in case.
    body = body.replace("</", "<\\/")
    return (
        f'<script type="application/json" id="page-state" '
        f'data-player-slug="{player_slug}">{body}</script>'
    )
