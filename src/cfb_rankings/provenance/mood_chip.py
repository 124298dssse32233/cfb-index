"""Provenance chip for the Mood Card (M-4).

Sprint v5-7.5 confidence chip showed sample-size; this chip surfaces
*where the sample came from* (count of distinct sources/subreddits) and
links to the methodology page that explains how the signal is computed.

Spec: docs/octopus/define.md §"M-4: Provenance chip on team Mood Cards"
  "based on N posts from M sources, methodology →"

Public API:
    from cfb_rankings.provenance.mood_chip import (
        fetch_source_count,
        render_provenance_chip,
        ProvenanceData,
    )

    n_sources = fetch_source_count(db, team_id=333, season_year=2025,
                                   week=12, bucket="fan")
    chip_html = render_provenance_chip(
        mentions=247,
        sources=n_sources,
        methodology_url="/methodology/fan-intelligence.html",
    )

The chip is renderer-agnostic — drop-in for both the legacy
``reporting.py::_render_team_mood_card`` and ``team_pages/renderer.py
::_render_pulse``. M-4's "two renderers" caveat is the reason this
primitive lives in ``provenance/`` rather than in either renderer's
module — both pull from one source of truth.
"""

from __future__ import annotations

import html as _html
import logging as _log
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..db import Database


log = _log.getLogger(__name__)


_DEFAULT_METHODOLOGY_URL = "/methodology/fan-intelligence.html"


@dataclass(frozen=True)
class ProvenanceData:
    """One Mood Card provenance record — packages the inputs the chip needs.

    `mentions` is the count of conversation documents that fed the
    signal. `sources` is the count of distinct subreddits / feeds /
    podcasts those documents came from. A high `mentions` with a low
    `sources` is a single-source echo chamber risk; a high `mentions`
    spread across many `sources` is the trust signal.
    """
    mentions: int
    sources: int
    methodology_url: str = _DEFAULT_METHODOLOGY_URL


# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------

def fetch_source_count(
    db: "Database",
    *,
    team_id: int,
    season_year: int,
    week: int,
    bucket: str = "fan",
) -> int:
    """Count the distinct sources (subreddits/feeds) that fed this team-week.

    Excludes the synthetic 'all' aggregate row. Returns 0 on missing-table
    OperationalError so the chip degrades gracefully on pre-migration DBs.
    """
    try:
        row = db.query_one(
            """
            SELECT COUNT(DISTINCT source_name) AS n
            FROM team_week_conversation_features
            WHERE team_id = ?
              AND season_year = ?
              AND week = ?
              AND audience_bucket = ?
              AND source_name != 'all'
            """,
            (team_id, season_year, week, bucket),
        )
    except sqlite3.OperationalError as e:
        log.warning("fetch_source_count: %s", e)
        return 0
    return int(row["n"]) if row and row["n"] is not None else 0


def fetch_player_source_count(
    db: "Database",
    *,
    player_id: int,
    season_year: int,
    week: int,
    bucket: str = "fan",
) -> int:
    """Same as fetch_source_count but reads player_week_conversation_features.

    Used by the player-page Room renderer when surfacing per-player chip.
    """
    try:
        row = db.query_one(
            """
            SELECT COUNT(DISTINCT source_name) AS n
            FROM player_week_conversation_features
            WHERE player_id = ?
              AND season_year = ?
              AND week = ?
              AND audience_bucket = ?
              AND source_name != 'all'
            """,
            (player_id, season_year, week, bucket),
        )
    except sqlite3.OperationalError as e:
        log.warning("fetch_player_source_count: %s", e)
        return 0
    return int(row["n"]) if row and row["n"] is not None else 0


# ---------------------------------------------------------------------------
# Render layer
# ---------------------------------------------------------------------------

def render_provenance_chip(
    mentions: int,
    sources: int,
    *,
    methodology_url: str = _DEFAULT_METHODOLOGY_URL,
    compact: bool = False,
) -> str:
    """Emit the locked provenance-chip HTML.

    Output (default):
        <span class="provenance-chip">
          based on <strong>247 posts</strong> from
          <strong>5 sources</strong> &middot;
          <a href="/methodology/fan-intelligence.html">methodology &rarr;</a>
        </span>

    ``compact=True`` drops the prefix copy for tight nav-strip use:
        <span class="provenance-chip provenance-chip--compact">
          <strong>247</strong>&middot;<strong>5</strong>
          <a href="/methodology/fan-intelligence.html">methodology</a>
        </span>

    Returns empty string when both mentions and sources are 0 (no
    provenance to surface — the caller should be rendering the empty-
    state chip instead).
    """
    if mentions <= 0 and sources <= 0:
        return ""
    methodology_safe = _html.escape(methodology_url)
    if compact:
        return (
            f'<span class="provenance-chip provenance-chip--compact" '
            f'aria-label="Provenance: {mentions} posts from {sources} sources">'
            f'<strong>{mentions:,}</strong>&middot;'
            f'<strong>{sources}</strong> '
            f'<a href="{methodology_safe}" class="provenance-chip__link">'
            f'methodology</a>'
            f'</span>'
        )
    posts_label = _pluralize(mentions, "post")
    sources_label = _pluralize(sources, "source")
    return (
        f'<span class="provenance-chip" '
        f'aria-label="Provenance: {mentions} posts from {sources} sources">'
        f'based on <strong>{mentions:,} {posts_label}</strong> from '
        f'<strong>{sources} {sources_label}</strong> &middot; '
        f'<a href="{methodology_safe}" class="provenance-chip__link">'
        f'methodology &rarr;</a>'
        f'</span>'
    )


def _pluralize(n: int, noun: str) -> str:
    return noun if n == 1 else noun + "s"


# Bundled CSS — drop into any host page's <style> block or stylesheet.
# Uses var() fallback chains so the chip looks correct on hosts using
# any of the four production token systems (team_pages dark, mockup
# light, Daily bespoke, reporting.py shadcn).
PROVENANCE_CHIP_CSS = """\
.provenance-chip {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.32em;
  font-family: var(--font-body, var(--sans, "Inter", system-ui, sans-serif));
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--fg-muted, var(--muted-foreground, var(--muted, #6b6b6b)));
  letter-spacing: 0.01em;
  line-height: 1.4;
}
.provenance-chip strong {
  font-weight: 600;
  color: var(--fg-primary, var(--foreground, var(--ink, #1c1c1f)));
}
.provenance-chip__link {
  color: var(--accent-primary, var(--gold, var(--primary, #c5b358)));
  text-decoration: none;
  border-bottom: 1px solid color-mix(in srgb,
    var(--accent-primary, var(--gold, #c5b358)) 35%, transparent);
  padding-bottom: 1px;
}
.provenance-chip__link:hover,
.provenance-chip__link:focus-visible {
  border-bottom-color: var(--accent-primary, var(--gold, #c5b358));
  outline: none;
}
.provenance-chip--compact {
  gap: 0.2em;
  font-size: 11px;
  letter-spacing: 0.02em;
}
"""


__all__ = [
    "ProvenanceData",
    "fetch_source_count",
    "fetch_player_source_count",
    "render_provenance_chip",
    "PROVENANCE_CHIP_CSS",
]
