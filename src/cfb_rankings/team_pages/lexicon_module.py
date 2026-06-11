"""The Lexicon team-page module — Language Layer Wave 1.

What this fanbase sounds like: the most statistically distinctive words in a
team's fan-voice corpus (weighted log-odds keyness vs the same-season field),
presented the way a type foundry presents a font — a specimen hero for the #1
term, a word wall where type weight is set by the data itself, and a verbatim
receipt quote with the term highlighted.

Reads team_discourse_terms (week=0 season cuts, written by
``manage.py compute-discourse-keyness``). Confidence floor: the module renders
only when the team has >= 8 surviving terms AND >= 200 docs in its corpus —
otherwise it returns "" and silently collapses out of the act (the team-page
graceful-degradation contract).

Public API:
    render_lexicon(db, profile, snapshot) -> str
    LEXICON_CSS                           -> str
"""

from __future__ import annotations

import re
from html import escape
from typing import Any

from .data import TeamSnapshot
from .profile_loader import Profile

_WALL_TERMS = 10
_MIN_TERMS = 8
_MIN_TEAM_DOCS = 200

_BAND_LABELS = {
    "signature": "Signature — ≥10× the rest of college football",
    "characteristic": "Characteristic — 3–10×",
    "mild": "Mild — <3×",
}

_ROW_KEYS = (
    "term", "term_rank", "mention_count", "z_score", "rate_ratio",
    "log2_ratio", "magnitude_band", "team_doc_count",
    "sample_quote", "sample_quote_source",
)


def _field(row: Any, key: str) -> Any:
    """Read a column from a dict-like or tuple row (defensive, chronicle-style)."""
    try:
        return row[key]
    except (TypeError, KeyError, IndexError):
        pass
    try:
        return row[_ROW_KEYS.index(key)]
    except (TypeError, ValueError, IndexError):
        return None


def _highlight_term(quote: str, term: str) -> str:
    """HTML-escape ``quote``, wrapping the first case-insensitive occurrence
    of ``term`` in the highlight span."""
    match = re.search(re.escape(term), quote, re.IGNORECASE)
    if not match:
        return escape(quote)
    return (
        escape(quote[: match.start()])
        + f'<mark class="lexicon-module__hl">{escape(match.group(0))}</mark>'
        + escape(quote[match.end():])
    )


def _wall_rows(rows: list[Any]) -> str:
    """The word wall: top terms, weight 300..900 mapped linearly over the
    team's own log2_ratio range, size ramp capped at ~2x (16px -> 32px)."""
    log2_values = [float(_field(r, "log2_ratio") or 0.0) for r in rows]
    lo, hi = min(log2_values), max(log2_values)
    span = (hi - lo) or 1.0

    parts: list[str] = []
    seen_bands: set[str] = set()
    for row, log2 in zip(rows, log2_values):
        band = str(_field(row, "magnitude_band") or "mild")
        if band not in seen_bands:
            seen_bands.add(band)
            label = _BAND_LABELS.get(band, band)
            band_cls = "lexicon-module__band"
            if band == "signature":
                band_cls += " lexicon-module__band--sig"
            parts.append(f'<div class="{band_cls}">{escape(label)}</div>')
        frac = (log2 - lo) / span
        weight = int(round(300 + frac * 600))
        size = round(16 + frac * 16, 1)  # 16px..32px — capped at 2x
        term = escape(str(_field(row, "term") or ""))
        ratio = float(_field(row, "rate_ratio") or 0.0)
        count = int(_field(row, "mention_count") or 0)
        parts.append(
            f'<div class="lexicon-module__row">'
            f'<span class="lexicon-module__term" '
            f'style="font-weight:{weight};font-size:{size}px">{term}</span>'
            f'<span class="lexicon-module__chip">×{ratio:.1f}</span>'
            f'<span class="lexicon-module__count">n={count:,}</span>'
            f'</div>'
        )
    return "".join(parts)


def render_lexicon(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None or not getattr(snapshot, "team_id", None):
        return ""
    team_id = int(snapshot.team_id)
    try:
        season_row = db.query_one(
            "SELECT MAX(season_year) AS season FROM team_discourse_terms "
            "WHERE team_id = :team_id AND week = 0",
            {"team_id": team_id},
        )
        if season_row is None:
            return ""
        try:
            season = season_row["season"]
        except (TypeError, KeyError, IndexError):
            season = season_row[0]
        if season is None:
            return ""
        season = int(season)
        rows = db.query_all(
            "SELECT term, term_rank, mention_count, z_score, rate_ratio, "
            "log2_ratio, magnitude_band, team_doc_count, "
            "sample_quote, sample_quote_source "
            "FROM team_discourse_terms "
            "WHERE team_id = :team_id AND season_year = :season AND week = 0 "
            "ORDER BY term_rank ASC LIMIT 30",
            {"team_id": team_id, "season": season},
        )
    except Exception:
        # Table may not exist yet (migration owned by another wave) — skip.
        return ""

    if len(rows) < _MIN_TERMS:
        return ""
    team_doc_count = int(_field(rows[0], "team_doc_count") or 0)
    if team_doc_count < _MIN_TEAM_DOCS:
        return ""

    top = rows[0]
    top_term = str(_field(top, "term") or "")
    top_ratio = float(_field(top, "rate_ratio") or 0.0)

    wall_html = _wall_rows(rows[:_WALL_TERMS])

    receipt_html = ""
    quote = _field(top, "sample_quote")
    if quote:
        quote_html = _highlight_term(str(quote), top_term)
        source = str(_field(top, "sample_quote_source") or "fan post")
        receipt_html = (
            f'<div class="lexicon-module__receipt">'
            f'<p class="lexicon-module__quote">&ldquo;{quote_html}&rdquo;</p>'
            f'<div class="lexicon-module__prov">{escape(source)} · fan post, verbatim</div>'
            f'</div>'
        )

    return f"""
<section class="lexicon-module" aria-label="The Lexicon">
  <div class="lexicon-module__head">
    <span class="lexicon-module__eyebrow">The Lexicon</span>
    <span class="lexicon-module__cohort">{team_doc_count:,} fan posts vs the field · {season} season</span>
  </div>
  <div class="lexicon-module__specimen">
    <div class="lexicon-module__specimen-term">{escape(top_term)}</div>
    <div class="lexicon-module__specimen-chip">×{top_ratio:.1f} the field</div>
  </div>
  <div class="lexicon-module__wall">{wall_html}</div>
  {receipt_html}
</section>"""


LEXICON_CSS = """
/* The Lexicon — fan-voice keyness specimen (Language Layer Wave 1) */
.lexicon-module {
  display: grid;
  gap: clamp(10px, 1.2vw, 14px);
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
}
.lexicon-module__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.lexicon-module__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent-primary, #c9a24a);
}
.lexicon-module__cohort {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  font-variant-numeric: tabular-nums;
}
.lexicon-module__specimen {
  text-align: center;
  padding: clamp(10px, 1.6vw, 20px) 0 4px;
}
.lexicon-module__specimen-term {
  font-family: var(--font-display, 'Bebas Neue', Impact, sans-serif);
  font-size: clamp(44px, 9vw, 88px);
  line-height: 0.95;
  letter-spacing: 0.01em;
  text-transform: uppercase;
  color: var(--accent-primary, #c9a24a);
  overflow-wrap: anywhere;
}
.lexicon-module__specimen-chip {
  display: inline-block;
  margin-top: 10px;
  padding: 5px 14px;
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 999px;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-primary);
  font-variant-numeric: tabular-nums;
}
.lexicon-module__wall {
  display: grid;
  gap: 0;
}
.lexicon-module__band {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--fg-muted);
  padding: 14px 0 4px;
}
.lexicon-module__band--sig { color: var(--accent-primary, #c9a24a); }
.lexicon-module__row {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 6px 0;
  border-bottom: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
}
.lexicon-module__row:last-child { border-bottom: none; }
.lexicon-module__term {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  color: var(--fg-primary);
  line-height: 1.1;
  min-width: 0;
  overflow-wrap: anywhere;
}
.lexicon-module__chip {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-primary, #c9a24a);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.lexicon-module__count {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10.5px;
  color: var(--fg-muted);
  margin-left: auto;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.lexicon-module__receipt {
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.08));
  padding-top: 12px;
}
.lexicon-module__quote {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 15px;
  line-height: 1.55;
  color: var(--fg-primary);
  margin: 0;
}
.lexicon-module__hl {
  color: inherit; /* override the UA's <mark> marktext default */
  background: color-mix(in srgb, var(--accent-primary, #c9a24a) 18%, transparent);
  box-shadow: inset 0 -2px 0 var(--accent-primary, #c9a24a);
  padding: 0 2px;
  border-radius: 2px;
}
.lexicon-module__prov {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-top: 8px;
}
"""


__all__ = ["render_lexicon", "LEXICON_CSS"]
