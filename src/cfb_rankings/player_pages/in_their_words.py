"""In Their Words — fan-voice player descriptor module (Language Layer Wave 3).

Reads player_discourse_terms to surface how fans describe a player in their own
vocabulary. Presents top descriptor chips (Hepta Slab variable weight, mapped to
rate_ratio) with a verbatim receipt quote below.

This is the player-page companion to The Lexicon on team pages. It answers:
"what words do fans disproportionately use when specifically describing this player?"

Confidence floor: >= 3 terms AND total_windows >= 30.
Below floor -> returns "" (graceful degradation).

Public API:
    render_in_their_words(db, player_id) -> str
    IN_THEIR_WORDS_CSS                   -> str
"""

from __future__ import annotations
import re
from html import escape
from typing import Any

_MIN_TERMS = 3
_MIN_WINDOWS = 30
_MAX_CHIPS = 8

_ROW_KEYS = ("term", "term_rank", "window_count", "z_score", "rate_ratio",
             "log2_ratio", "total_windows", "sample_quote", "sample_quote_source")


def _field(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (TypeError, KeyError, IndexError):
        pass
    try:
        return row[_ROW_KEYS.index(key)]
    except (TypeError, ValueError, IndexError):
        return None


def _highlight_term(quote: str, term: str) -> str:
    match = re.search(re.escape(term), quote, re.IGNORECASE)
    if not match:
        return escape(quote)
    return (
        escape(quote[:match.start()])
        + f'<mark class="itw__hl">{escape(match.group(0))}</mark>'
        + escape(quote[match.end():])
    )


def render_in_their_words(db, player_id: int) -> str:
    if db is None or not player_id:
        return ""
    try:
        season_row = db.query_one(
            "SELECT MAX(season_year) AS season FROM player_discourse_terms "
            "WHERE player_id = :player_id",
            {"player_id": player_id},
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
            "SELECT term, term_rank, window_count, z_score, rate_ratio, log2_ratio, "
            "total_windows, sample_quote, sample_quote_source "
            "FROM player_discourse_terms "
            "WHERE player_id = :player_id AND season_year = :season "
            "ORDER BY term_rank ASC LIMIT 15",
            {"player_id": player_id, "season": season},
        )
    except Exception:
        return ""

    if len(rows) < _MIN_TERMS:
        return ""
    total_windows = int(_field(rows[0], "total_windows") or 0)
    if total_windows < _MIN_WINDOWS:
        return ""

    chips_rows = rows[:_MAX_CHIPS]
    ratios = [float(_field(r, "log2_ratio") or 0.0) for r in chips_rows]
    lo, hi = min(ratios), max(ratios)
    span = (hi - lo) or 1.0

    chips_html = ""
    for row, l2 in zip(chips_rows, ratios):
        frac = (l2 - lo) / span
        weight = int(round(300 + frac * 600))
        term = escape(str(_field(row, "term") or ""))
        ratio = float(_field(row, "rate_ratio") or 0.0)
        chips_html += (
            f'<span class="itw__chip" style="font-weight:{weight}">'
            f'{term}<span class="itw__chip-ratio">×{ratio:.1f}</span>'
            f'</span>'
        )

    receipt_html = ""
    # Use first row with a quote
    for row in rows:
        quote = _field(row, "sample_quote")
        if quote:
            term = str(_field(row, "term") or "")
            quote_html = _highlight_term(str(quote), term)
            source = str(_field(row, "sample_quote_source") or "fan post")
            receipt_html = (
                f'<div class="itw__receipt">'
                f'<p class="itw__quote">&ldquo;{quote_html}&rdquo;</p>'
                f'<div class="itw__prov">{escape(source)} · fan post, verbatim</div>'
                f'</div>'
            )
            break

    return f"""<style>{IN_THEIR_WORDS_CSS}</style>
<section class="itw" aria-label="In Their Words">
  <div class="itw__head">
    <span class="itw__eyebrow">In Their Words</span>
    <span class="itw__subhead">{total_windows:,} windows · {season} fan posts</span>
  </div>
  <div class="itw__chips">{chips_html}</div>
  {receipt_html}
</section>"""


IN_THEIR_WORDS_CSS = """
/* In Their Words — player descriptor chips (Language Layer Wave 3) */
.itw {
  display: grid;
  gap: clamp(8px, 1.2vw, 12px);
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2vw, 24px);
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(16px, 2.5vw, 24px);
}
.itw__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.itw__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent-primary, #c9a24a);
}
.itw__subhead {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  font-variant-numeric: tabular-nums;
}
.itw__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.itw__chip {
  font-family: 'Hepta Slab', var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: clamp(13px, 2vw, 17px);
  line-height: 1.1;
  color: var(--fg-primary);
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  overflow-wrap: anywhere;
}
.itw__chip-ratio {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10px;
  font-weight: 500;
  color: var(--accent-primary, #c9a24a);
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.itw__receipt {
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.08));
  padding-top: 12px;
}
.itw__quote {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 14px;
  line-height: 1.55;
  color: var(--fg-primary);
  margin: 0;
}
.itw__hl {
  color: inherit;
  background: color-mix(in srgb, var(--accent-primary, #c9a24a) 18%, transparent);
  box-shadow: inset 0 -2px 0 var(--accent-primary, #c9a24a);
  padding: 0 2px;
  border-radius: 2px;
}
.itw__prov {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-top: 8px;
}
"""

__all__ = ["render_in_their_words", "IN_THEIR_WORDS_CSS"]
