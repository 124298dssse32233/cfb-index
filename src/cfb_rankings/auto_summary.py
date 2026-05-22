"""30-second auto-summary primitive.

Sprint v5-7.6 deliverable. Generates 2-3 sentence summaries for the top
of every Article-archetype page (Daily / Mailbag / Reactions / Edition
features). Pattern A (single-shot Sonnet + regex voice validation —
the cheapest of the loop tiers).

Public API:
    from cfb_rankings.auto_summary import (
        generate_article_summary,
        AutoSummary,
    )

    summary = generate_article_summary(
        body_markdown=feature.body_markdown,
        headline=feature.title,
        dek=feature.dek,
        cache_key=f"daily:{edition_date}",
    )
    if summary:
        html += render_auto_summary_html(summary)

The cache layer is a thin SQLite table (``auto_summary_cache``) keyed on
(cache_key, body_hash). Same body produces the same summary; changing
the body invalidates the cache.

Cost: ~$0.006 per call (Sonnet, 4k tokens). At 1 daily edition per day +
1 mailbag/week + ad-hoc reactions, monthly spend is ~$0.50.

Locked spec:
    docs/mockups/mockup_04_daily_v2.html — the .auto-summary block
    docs/design-system/30-page-archetypes.md §"Article archetype"
"""

from __future__ import annotations

import hashlib
import html as _html
import logging as _log
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .db import Database


log = _log.getLogger(__name__)


_SYSTEM_PROMPT = """\
You write 30-second summaries for college football editorial articles.
Your output is 2-3 short bullets. Each bullet is one sentence, 12-20
words. No exclamation marks. No throat-clearing ("this article is
about..."). Cite the same kind of claim the body makes.

Output format — markdown unordered list, exactly:

- Bullet one (one sentence).
- Bullet two (one sentence).
- Bullet three (one sentence, optional).

Never invent claims. If the body doesn't support a bullet, output fewer
bullets rather than fabricating.
"""


@dataclass(frozen=True)
class AutoSummary:
    """One auto-summary record."""
    bullets: tuple[str, ...]
    body_hash: str
    model_version: str = "auto-summary.v1"


# ---------------------------------------------------------------------------
# Cache layer
# ---------------------------------------------------------------------------

CACHE_DDL = """
CREATE TABLE IF NOT EXISTS auto_summary_cache (
    cache_key      TEXT NOT NULL,
    body_hash      TEXT NOT NULL,
    bullets_json   TEXT NOT NULL,
    model_version  TEXT NOT NULL,
    created_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (cache_key, body_hash)
)
"""


def _body_hash(body: str) -> str:
    """Stable hash for cache invalidation."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _read_cache(
    db: "Database",
    cache_key: str,
    body_hash: str,
) -> AutoSummary | None:
    """Read a cached summary or None."""
    try:
        row = db.query_one(
            """
            SELECT bullets_json, model_version
            FROM auto_summary_cache
            WHERE cache_key = ? AND body_hash = ?
            """,
            (cache_key, body_hash),
        )
    except sqlite3.OperationalError:
        return None
    if not row:
        return None
    import json
    try:
        bullets = tuple(json.loads(row["bullets_json"]))
    except (json.JSONDecodeError, TypeError):
        return None
    return AutoSummary(
        bullets=bullets, body_hash=body_hash,
        model_version=row["model_version"] or "unknown",
    )


def _write_cache(
    db: "Database",
    cache_key: str,
    summary: AutoSummary,
) -> None:
    """Upsert a summary into the cache."""
    import json
    try:
        db.execute(
            """
            INSERT INTO auto_summary_cache
              (cache_key, body_hash, bullets_json, model_version)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key, body_hash) DO UPDATE SET
              bullets_json = excluded.bullets_json,
              model_version = excluded.model_version,
              created_at_utc = datetime('now')
            """,
            (cache_key, summary.body_hash,
             json.dumps(list(summary.bullets)), summary.model_version),
        )
    except sqlite3.OperationalError as e:
        log.warning("auto_summary cache write failed: %s", e)


# ---------------------------------------------------------------------------
# Bullets parser — extract markdown list from LLM output
# ---------------------------------------------------------------------------

def _parse_bullets(raw: str, *, max_bullets: int = 3) -> tuple[str, ...]:
    """Pull markdown list items out of the LLM output.

    Tolerant: accepts ``-``, ``*``, or ``•`` prefixes. Caps at max_bullets.
    Strips trailing whitespace + empty lines. Skips lines that don't look
    like bullets.
    """
    bullets: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        for prefix in ("- ", "* ", "• ", "– "):
            if s.startswith(prefix):
                bullet = s[len(prefix):].strip()
                if bullet and len(bullet) >= 10:  # reject too-short
                    bullets.append(bullet)
                break
        if len(bullets) >= max_bullets:
            break
    return tuple(bullets)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_article_summary(
    body_markdown: str,
    *,
    headline: str = "",
    dek: str = "",
    cache_key: str,
    db: "Database | None" = None,
    force_regenerate: bool = False,
    model: str | None = None,
) -> AutoSummary | None:
    """Generate (or read from cache) an auto-summary for an article.

    Returns None when:
      - body_markdown is empty or trivially short (<200 chars)
      - The LLM call fails or returns no parseable bullets
      - The LLM call is blocked by Rung-3 weekly ceiling on auto_summary
        surface (unlikely at $0.006/call)

    Caching:
      - Reads from auto_summary_cache on (cache_key, body_hash)
      - body_hash invalidates when body_markdown changes byte-for-byte
      - ``force_regenerate=True`` bypasses the read path

    The function is safe to call without a Database — it just won't
    cache and will always call the LLM.
    """
    if not body_markdown or len(body_markdown.strip()) < 200:
        return None
    bh = _body_hash(body_markdown)

    # Cache read
    if db is not None and not force_regenerate:
        cached = _read_cache(db, cache_key, bh)
        if cached is not None:
            log.info("auto_summary cache hit: %s/%s", cache_key, bh)
            return cached

    # Build the prompt — include headline + dek + first ~3000 chars of body
    # to keep tokens bounded.
    body_excerpt = body_markdown.strip()
    if len(body_excerpt) > 3000:
        # Keep the start + a chunk of the tail (the conclusion often carries
        # the most-summarizable claim)
        body_excerpt = body_excerpt[:2200] + "\n\n[...middle truncated...]\n\n" + body_excerpt[-700:]

    prompt = (
        f"HEADLINE: {headline.strip()}\n"
        f"DEK: {dek.strip()}\n"
        f"\nBODY:\n{body_excerpt}\n"
        f"\nWrite the 2-3 bullet summary now."
    )

    # Pattern A — single-shot via quality_loop. Import lazily to avoid a
    # cycle when this module is imported during cli.py setup.
    try:
        from .quality_loop import loop_a_single_shot
        result = loop_a_single_shot(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            model=model,
            max_tokens=400,
            surface="tier3.auto_summary",
            subcommand="auto_summary.A",
        )
    except Exception as e:
        log.warning("auto_summary loop_a failed: %s", e)
        return None
    if result is None or not getattr(result, "text", None):
        return None
    bullets = _parse_bullets(result.text)
    if not bullets:
        log.warning(
            "auto_summary: %s parsed 0 bullets from output: %r",
            cache_key, (result.text or "")[:200],
        )
        return None
    summary = AutoSummary(
        bullets=bullets, body_hash=bh, model_version="auto-summary.v1",
    )
    if db is not None:
        _write_cache(db, cache_key, summary)
    return summary


def render_auto_summary_html(summary: AutoSummary) -> str:
    """Emit the .auto-summary block from mockup_04 daily mockup."""
    if not summary or not summary.bullets:
        return ""
    items = "\n".join(
        f"        <li>{_html.escape(b)}</li>"
        for b in summary.bullets
    )
    return f"""\
<aside class="auto-summary" aria-label="30-second summary">
  <p class="auto-summary__title">30-second summary</p>
  <ul class="auto-summary__list">
{items}
  </ul>
  <p class="auto-summary__meta">AI-summarized · refreshed every 4 hours</p>
</aside>"""


__all__ = [
    "AutoSummary",
    "CACHE_DDL",
    "generate_article_summary",
    "render_auto_summary_html",
]
