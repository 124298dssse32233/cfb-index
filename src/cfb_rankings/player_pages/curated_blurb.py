"""Curated player blurbs (manual-in-chat spike).

Renders a top-of-page "2026 Outlook" crown (forward-looking narrative + a
play-style paragraph) from ``data/curated_player_blurbs/*.json`` into the
story-card slot (``new_story_card_html``), which both the legacy and Noir
renderers consume.

Matching is by **player_id** first (the numeric suffix of the canonical
``name-PLAYER_ID`` slug — always in scope at the render call site), then by the
full slug, then by normalized player name. Keying on player_id makes this work
even when ``page_data["player"]`` (the name) isn't populated yet at the
injection point. Gated by the ``CURATED_BLURBS`` env var at the call site; this
module returns "" whenever no curated record matches.
"""
from __future__ import annotations

import html
import json
import re
from functools import lru_cache
from pathlib import Path

try:  # reuse the site's canonical slugify so reconstructed slugs match
    from cfb_rankings.utils import slugify as _slugify
except Exception:  # pragma: no cover
    def _slugify(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def _data_dir() -> Path | None:
    for c in (
        Path(__file__).resolve().parents[3] / "data" / "curated_player_blurbs",
        Path.cwd() / "data" / "curated_player_blurbs",
    ):
        if c.is_dir():
            return c
    return None


@lru_cache(maxsize=1)
def _index() -> tuple[dict, dict, dict]:
    by_slug: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    by_id: dict[int, dict] = {}
    d = _data_dir()
    if not d:
        return by_slug, by_name, by_id
    for fp in sorted(d.glob("*.json")):
        try:
            rec = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rec, dict) or not (rec.get("hook") or rec.get("expand")):
            continue
        slug = str(rec.get("slug") or "").strip().lower()
        if slug:
            by_slug[slug] = rec
            m = re.search(r"-(\d+)$", slug)  # the canonical player_id suffix
            if m:
                by_id[int(m.group(1))] = rec
        nm = _slugify(str(rec.get("player_name") or ""))
        if nm:
            by_name.setdefault(nm, rec)
    return by_slug, by_name, by_id


def _fmt(s: str) -> str:
    return html.escape((s or "").strip()).replace("--", "—")


def _paras(text: str) -> str:
    return "".join(
        f"<p>{_fmt(p)}</p>" for p in (text or "").split("\n\n") if p.strip()
    )


_CSS = (
    "<style>"
    ".curated-blurb{margin:0 0 1.5rem;padding:1.25rem 1.4rem;border-left:3px solid currentColor;"
    "border-radius:.4rem;background:rgba(127,127,127,.06);}"
    ".curated-blurb .cb-hook{font-size:1.18rem;line-height:1.45;font-weight:600;margin:0 0 .8rem;}"
    ".curated-blurb .cb-body p{margin:0 0 .7rem;line-height:1.6;}"
    ".curated-blurb .cb-style{margin-top:1rem;padding-top:.9rem;border-top:1px solid rgba(127,127,127,.25);}"
    ".curated-blurb .cb-style h4{margin:0 0 .4rem;font-size:.78rem;letter-spacing:.08em;"
    "text-transform:uppercase;opacity:.7;}"
    ".curated-blurb .cb-style p{margin:0;line-height:1.6;}"
    ".curated-blurb .cb-meta{margin-top:.9rem;font-size:.72rem;letter-spacing:.05em;"
    "text-transform:uppercase;opacity:.5;}"
    "</style>"
)


def render_curated_blurb(player_id, full_name=None, team_name=None) -> str:
    """Return story-card HTML for a curated blurb, or "" if none matches.

    Matches by player_id (slug numeric suffix) first, then full slug, then name.
    """
    by_slug, by_name, by_id = _index()
    if not by_slug:
        return ""
    rec = None
    if player_id is not None:
        try:
            rec = by_id.get(int(player_id))
        except (TypeError, ValueError):
            rec = None
    if rec is None and player_id and full_name:
        rec = by_slug.get(f"{_slugify(str(full_name))}-{player_id}".lower())
    if rec is None and full_name:
        rec = by_name.get(_slugify(str(full_name)))
    if rec is None:
        return ""
    hook = _fmt(rec.get("hook", ""))
    body = _paras(rec.get("expand", ""))
    style = _fmt(rec.get("style", ""))
    as_of = html.escape(str(rec.get("as_of_date") or "").strip())
    parts = ['<section class="curated-blurb" aria-label="2026 outlook">']
    if hook:
        parts.append(f'<p class="cb-hook">{hook}</p>')
    if body:
        parts.append(f'<div class="cb-body">{body}</div>')
    if style:
        parts.append(f'<div class="cb-style"><h4>How he plays</h4><p>{style}</p></div>')
    if as_of:
        parts.append(f'<div class="cb-meta">2026 outlook &middot; as of {as_of}</div>')
    parts.append("</section>")
    return _CSS + "".join(parts)
