"""Curated TEAM blurbs (manual-in-chat spike) — the team analog of
``player_pages/curated_blurb.py`` (doc 68, cross-subject paradigm).

Renders a top-of-page narrative "crown" (forward-looking program narrative +
an optional identity / "how they play" companion) from
``data/curated_team_blurbs/*.json`` into the team-page body, just under the
hero. The team Story Card spec is docs/design-system/50-58.

Matching is by **team slug** (the team-page slug, e.g. ``alabama``,
``ohio-state``) — teams have no numeric-id suffix, the slug IS the key.

Design notes (mirrors the player module, which is proven in production):
  * Fail-closed: returns "" whenever no curated record matches or anything
    throws, so a bad/missing file can never blank a team page.
  * Default ON: the curated file's existence is the gate. Set
    ``CURATED_TEAM_BLURBS=off`` (or 0/false/no) to hard-disable. We do NOT
    rely on an env var being *present* — the renderer has no module-level
    ``os`` import, so the env read happens behind a local import here.
  * Forgiving schema: only ``hook``/``expand`` are required to render. Extra
    fields are ignored, so the team Story Card schema can evolve over in the
    design docs without breaking this loader.
  * Files whose name starts with ``_`` (e.g. ``_EXAMPLE.json``) are skipped,
    so templates/examples never ship to prod.
"""
from __future__ import annotations

import html
import json
import re
from functools import lru_cache
from pathlib import Path


def _norm_slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def _data_dir() -> Path | None:
    for c in (
        # repo_root/data/curated_team_blurbs  (…/src/cfb_rankings/team_pages/this.py)
        Path(__file__).resolve().parents[3] / "data" / "curated_team_blurbs",
        Path.cwd() / "data" / "curated_team_blurbs",
    ):
        if c.is_dir():
            return c
    return None


@lru_cache(maxsize=1)
def _index() -> dict[str, dict]:
    by_slug: dict[str, dict] = {}
    d = _data_dir()
    if not d:
        return by_slug
    for fp in sorted(d.glob("*.json")):
        if fp.stem.startswith("_"):  # _EXAMPLE.json, _templates, etc.
            continue
        try:
            rec = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rec, dict) or not (rec.get("hook") or rec.get("expand")):
            continue
        slug = _norm_slug(str(rec.get("slug") or rec.get("team_slug") or ""))
        if slug:
            by_slug[slug] = rec
    return by_slug


def _fmt(s: str) -> str:
    return html.escape((s or "").strip()).replace("--", "—")


def _paras(text: str) -> str:
    return "".join(
        f"<p>{_fmt(p)}</p>" for p in (text or "").split("\n\n") if p.strip()
    )


_CSS = (
    "<style>"
    ".curated-team-blurb{margin:0 0 1.5rem;padding:1.25rem 1.4rem;border-left:3px solid currentColor;"
    "border-radius:.4rem;background:rgba(127,127,127,.06);}"
    ".curated-team-blurb .ctb-hook{font-size:1.18rem;line-height:1.45;font-weight:600;margin:0 0 .8rem;}"
    ".curated-team-blurb .ctb-body p{margin:0 0 .7rem;line-height:1.6;}"
    ".curated-team-blurb .ctb-identity{margin-top:1rem;padding-top:.9rem;border-top:1px solid rgba(127,127,127,.25);}"
    ".curated-team-blurb .ctb-identity h4{margin:0 0 .4rem;font-size:.78rem;letter-spacing:.08em;"
    "text-transform:uppercase;opacity:.7;}"
    ".curated-team-blurb .ctb-identity p{margin:0;line-height:1.6;}"
    ".curated-team-blurb .ctb-meta{margin-top:.9rem;font-size:.72rem;letter-spacing:.05em;"
    "text-transform:uppercase;opacity:.5;}"
    "</style>"
)


def render_curated_team_blurb(slug: str) -> str:
    """Return crown HTML for a curated team blurb, or "" if none matches.

    ``slug`` is the team-page slug (e.g. ``ohio-state``). Fail-closed.
    """
    try:
        import os as _os  # team_pages.renderer has no module-level os import
        if _os.environ.get("CURATED_TEAM_BLURBS", "").lower() in ("0", "off", "false", "no"):
            return ""
        by_slug = _index()
        if not by_slug:
            return ""
        rec = by_slug.get(_norm_slug(slug))
        if rec is None:
            return ""
        hook = _fmt(rec.get("hook", ""))
        body = _paras(rec.get("expand", ""))
        # The team analog of the player "how he plays" companion: program
        # identity / "how they play". Accept either key.
        identity = _fmt(rec.get("identity", "") or rec.get("style", ""))
        identity_label = str(rec.get("identity_label") or "How they play")
        as_of = html.escape(str(rec.get("as_of_date") or "").strip())
        parts = ['<section class="curated-team-blurb" aria-label="program outlook">']
        if hook:
            parts.append(f'<p class="ctb-hook">{hook}</p>')
        if body:
            parts.append(f'<div class="ctb-body">{body}</div>')
        if identity:
            parts.append(
                f'<div class="ctb-identity"><h4>{html.escape(identity_label)}</h4>'
                f'<p>{identity}</p></div>'
            )
        if as_of:
            parts.append(f'<div class="ctb-meta">program outlook &middot; as of {as_of}</div>')
        parts.append("</section>")
        return _CSS + "".join(parts)
    except Exception:
        return ""
