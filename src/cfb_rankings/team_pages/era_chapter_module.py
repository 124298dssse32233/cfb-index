from __future__ import annotations

import html as _html
from typing import Any


ERA_CHAPTER_CSS: str = """
<style>
/* === Era Chapter Module === */
.era-ch {
  margin: 2rem 0;
  padding: 0;
}

.era-ch__heading {
  font-family: 'Bebas Neue', 'Impact', sans-serif;
  font-size: 1.1rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-secondary, #888);
  margin: 0 0 1rem 0;
}

.era-ch__band {
  border-left: 3px solid var(--accent-primary, #e8a838);
  background: rgba(232, 168, 56, 0.05);
  padding: 0.85rem 1rem 0.85rem 1.1rem;
  margin-bottom: 0.75rem;
  border-radius: 0 4px 4px 0;
}

.era-ch__year {
  font-family: 'Bebas Neue', 'Impact', sans-serif;
  font-size: 1.35rem;
  letter-spacing: 0.08em;
  color: var(--accent-primary, #e8a838);
  display: block;
  margin-bottom: 0.25rem;
}

.era-ch__label {
  font-family: 'Bebas Neue', 'Impact', sans-serif;
  font-size: 1.05rem;
  letter-spacing: 0.06em;
  color: var(--text-primary, #f0f0f0);
  display: block;
  margin-bottom: 0.55rem;
}

.era-ch__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.5rem;
  margin-bottom: 0.6rem;
}

.era-ch__chip {
  font-family: 'Hepta Slab', 'Georgia', serif;
  font-size: 0.82rem;
  color: var(--text-primary, #f0f0f0);
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(232, 168, 56, 0.2);
  border-radius: 3px;
  padding: 0.15rem 0.45rem;
  white-space: nowrap;
  line-height: 1.5;
}

.era-ch__receipt {
  margin: 0.5rem 0 0 0;
  padding: 0.45rem 0.7rem;
  border-left: 2px solid var(--accent-primary, #e8a838);
  background: rgba(0, 0, 0, 0.2);
  font-family: 'Source Serif Pro', 'Georgia', serif;
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--text-secondary, #aaa);
  font-style: italic;
  border-radius: 0 3px 3px 0;
}

.era-ch__hl {
  background: rgba(232, 168, 56, 0.30);
  color: var(--text-primary, #f0f0f0);
  font-style: normal;
  padding: 0 0.15em;
  border-radius: 2px;
}

@media (max-width: 640px) {
  .era-ch__band {
    padding: 0.7rem 0.75rem 0.7rem 0.9rem;
  }

  .era-ch__year {
    font-size: 1.15rem;
  }

  .era-ch__label {
    font-size: 0.95rem;
  }

  .era-ch__chip {
    font-size: 0.78rem;
    padding: 0.12rem 0.38rem;
  }

  .era-ch__receipt {
    font-size: 0.78rem;
  }
}
</style>
"""


def _weight(log2_ratio: float) -> int:
    """Map log2_ratio to CSS font-weight [300, 900].

    Clamps log2_ratio to [-1, 4], then linearly maps to [300, 900].
    """
    clamped = max(-1.0, min(4.0, log2_ratio))
    # linear map: -1 -> 300, 4 -> 900
    # slope = (900 - 300) / (4 - (-1)) = 600 / 5 = 120
    weight = 300 + (clamped - (-1.0)) * 120.0
    # Round to nearest 100 for valid CSS font-weight values
    rounded = int(round(weight / 100.0) * 100)
    return max(300, min(900, rounded))


def render_era_chapters(db: Any, profile: Any, snapshot: Any) -> str:
    """Render NYT-style era chapter bands for a team page.

    Returns an HTML string with season vocabulary bands, or empty string
    when floors are not met.
    """
    if db is None or profile is None:
        return ""

    # Resolve team_id
    team_id = 0
    try:
        team_id = int(getattr(profile, "team_id", None) or 0)
    except (TypeError, ValueError):
        team_id = 0

    if team_id == 0:
        try:
            team_id = int(getattr(snapshot, "team_id", None) or 0)
        except (TypeError, ValueError):
            team_id = 0

    if team_id == 0:
        return ""

    # Query era terms for this team
    try:
        rows = db.execute(
            """
            SELECT season_year, term, term_rank, log2_ratio, sample_quote
            FROM team_discourse_era_terms
            WHERE team_id = :tid
            ORDER BY season_year DESC, term_rank ASC
            """,
            {"tid": team_id},
        ).fetchall()
    except Exception:
        return ""

    if not rows:
        return ""

    # Group by season_year
    seasons: dict[int, list[dict]] = {}
    for row in rows:
        yr = int(row[0])
        if yr not in seasons:
            seasons[yr] = []
        seasons[yr].append({
            "term": row[1],
            "term_rank": row[2],
            "log2_ratio": float(row[3]) if row[3] is not None else 0.0,
            "sample_quote": row[4] if len(row) > 4 else None,
        })

    # Floor checks
    if len(seasons) < 2:
        return ""

    sorted_years = sorted(seasons.keys(), reverse=True)
    most_recent_year = sorted_years[0]
    if len(seasons[most_recent_year]) < 3:
        return ""

    # Build HTML
    parts: list[str] = []
    parts.append('<section class="era-ch">')
    parts.append('<h3 class="era-ch__heading">Season Vocabulary</h3>')

    for yr in sorted_years[:4]:
        terms = seasons[yr]
        top_term = terms[0]

        band_parts: list[str] = []
        band_parts.append('<div class="era-ch__band">')
        band_parts.append(f'<span class="era-ch__year">{yr}</span>')
        band_parts.append(
            f'<span class="era-ch__label">{_html.escape(top_term["term"].upper())}</span>'
        )

        # Chips row
        band_parts.append('<div class="era-ch__chips">')
        for t in terms[:6]:
            fw = _weight(t["log2_ratio"])
            band_parts.append(
                f'<span class="era-ch__chip" style="font-weight: {fw}">'
                f'{_html.escape(t["term"])}'
                f'</span>'
            )
        band_parts.append("</div>")  # .era-ch__chips

        # Receipt block for top term if sample_quote exists
        quote = top_term.get("sample_quote")
        if quote:
            term_text = top_term["term"]
            # HTML-escape the full quote first, then wrap the highlighted term.
            import re
            escaped_quote = _html.escape(str(quote))
            escaped_term  = _html.escape(term_text)
            highlighted_quote = re.sub(
                re.escape(escaped_term),
                f'<mark class="era-ch__hl">{escaped_term}</mark>',
                escaped_quote,
                flags=re.IGNORECASE,
            )
            band_parts.append(
                f'<blockquote class="era-ch__receipt">{highlighted_quote}</blockquote>'
            )

        band_parts.append("</div>")  # .era-ch__band
        parts.append("".join(band_parts))

    parts.append("</section>")

    return ERA_CHAPTER_CSS + "\n".join(parts)
