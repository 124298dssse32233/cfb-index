"""Recruit Watch Board renderer — S4 surface.

Ranks programs by weighted recruiting class strength. Star weights match
the historical convention used in player_recruiting_profiles aggregation:
  5★ = 10 pts, 4★ = 4 pts, 3★ = 1 pt, ≤2★ = 0 pts.

Output: /recruit-board/<class_year>/index.html with top-25 program cards.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date
from html import escape
from pathlib import Path

from cfb_rankings.common.cfb_calendar import cfb_week_label, days_to_kickoff

log = logging.getLogger(__name__)


_STAR_WEIGHTS: dict[int, int] = {5: 10, 4: 4, 3: 1, 2: 0, 1: 0, 0: 0}


def _default_class_year(today: date) -> int:
    """The 'next' recruiting class for an anchor date.

    Recruiting classes are named by the year players enroll. In May 2026,
    high-school juniors committing today are class of 2027. The default
    class is therefore current_year + 1 unless today is after early signing
    day (early December), in which case current_year+2 is the active class.
    """
    if today.month == 12 and today.day >= 18:
        return today.year + 2
    return today.year + 1


def _fetch_program_class_data(
    db: sqlite3.Connection, *, class_year: int, top_n: int = 25,
) -> list[dict]:
    """Aggregate player_recruiting_profiles by committed_team for the
    given class year.

    Returns a list of dicts ordered by weighted_score descending. Each
    dict has: program, commits, weighted_score, top_movers (up to 3).
    Empty list if the table is missing or has no rows for the class.
    """
    try:
        rows = db.execute(
            """
            SELECT
              committed_team,
              COUNT(*) AS commits,
              SUM(CASE stars
                    WHEN 5 THEN 10
                    WHEN 4 THEN 4
                    WHEN 3 THEN 1
                    ELSE 0
                  END) AS weighted_score,
              AVG(rating) AS avg_rating
            FROM player_recruiting_profiles
            WHERE season_year = ?
              AND committed_team IS NOT NULL
              AND committed_team != ''
            GROUP BY committed_team
            ORDER BY weighted_score DESC, commits DESC
            LIMIT ?
            """,
            (class_year, top_n),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        log.warning("recruit_board: query failed (%s); returning empty list", exc)
        return []

    out: list[dict] = []
    for row in rows:
        cols = [c[0] for c in db.execute(
            "SELECT 1 FROM player_recruiting_profiles LIMIT 0"
        ).description]
        d = dict(zip(cols, row)) if cols else {}
        # Fall through to positional access for portability
        team = row[0]
        commits = int(row[1] or 0)
        weighted = int(row[2] or 0)
        avg_rating = float(row[3] or 0.0)
        try:
            movers_rows = db.execute(
                """
                SELECT
                  CASE
                    WHEN notes LIKE '%first_name%' THEN substr(notes, 1, 40)
                    ELSE COALESCE(school_name, '')
                  END AS label,
                  stars, position
                FROM player_recruiting_profiles
                WHERE season_year = ?
                  AND committed_team = ?
                ORDER BY stars DESC, rating DESC
                LIMIT 3
                """,
                (class_year, team),
            ).fetchall()
        except sqlite3.OperationalError:
            movers_rows = []
        movers = [
            {
                "label": str(m[0] or ""),
                "stars": int(m[1] or 0),
                "position": str(m[2] or ""),
            }
            for m in movers_rows
        ]
        out.append({
            "program": team,
            "commits": commits,
            "weighted_score": weighted,
            "avg_rating": round(avg_rating, 2) if avg_rating else 0.0,
            "top_movers": movers,
        })
    return out


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
{head_chrome}
<link rel="stylesheet" href="/assets/css/site.css">
<style>
  .recruit-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                    gap: 20px; margin-top: 24px; }}
  .recruit-card {{ background: var(--card, #fff); border: 1px solid var(--border, #d8d8d8);
                    border-radius: 12px; padding: 20px; }}
  .recruit-card__rank {{ font-size: 11px; letter-spacing: 2px; font-weight: 700;
                          color: var(--muted-foreground, #666); }}
  .recruit-card__team {{ font-size: 22px; font-weight: 800; margin: 4px 0 8px; }}
  .recruit-card__stats {{ display: flex; gap: 24px; margin-bottom: 12px; }}
  .recruit-card__stat strong {{ font-size: 22px; font-variant-numeric: tabular-nums;
                                  font-weight: 800; display: block; }}
  .recruit-card__stat small {{ font-size: 11px; letter-spacing: 1px;
                                color: var(--muted-foreground, #777); }}
  .recruit-card__movers {{ font-size: 13px; color: var(--muted-foreground, #555); }}
  .recruit-card__movers li {{ list-style: none; padding: 2px 0; }}
  .recruit-empty {{ padding: 32px; border: 2px dashed var(--border, #d8d8d8);
                     border-radius: 12px; text-align: center;
                     color: var(--muted-foreground, #666); }}
</style>
</head>
<body class="recruit-board-page">
<main class="site-shell" id="main-content">
  <section class="hero">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{title_heading}</h1>
    <p class="lede">{lede}</p>
  </section>
  <section class="section">
    {body}
  </section>
  {meta_footer}
</main>
</body>
</html>
"""


def _format_card(rank: int, prog: dict) -> str:
    movers_html = "".join(
        f"<li>{escape(str(m.get('label') or ''))[:40]} "
        f"({m.get('stars',0)}★ {escape(str(m.get('position') or ''))})</li>"
        for m in prog.get("top_movers", []) or []
    ) or "<li><em>no detail rows</em></li>"
    return (
        f'<article class="recruit-card">'
        f'<div class="recruit-card__rank">#{rank}</div>'
        f'<div class="recruit-card__team">{escape(prog["program"])}</div>'
        f'<div class="recruit-card__stats">'
        f'<div class="recruit-card__stat"><strong>{prog["commits"]}</strong>'
        f'<small>COMMITS</small></div>'
        f'<div class="recruit-card__stat"><strong>{prog["weighted_score"]}</strong>'
        f'<small>WEIGHTED</small></div>'
        f'<div class="recruit-card__stat"><strong>{prog["avg_rating"]:.2f}</strong>'
        f'<small>AVG RATING</small></div>'
        f'</div>'
        f'<ul class="recruit-card__movers">{movers_html}</ul>'
        f'</article>'
    )


def render_recruit_board(
    db: sqlite3.Connection,
    *,
    class_year: int | None = None,
    today: date | None = None,
    output_dir: str = "output/site",
    top_n: int = 25,
) -> dict[str, int | str]:
    """Render /recruit-board/<class_year>/index.html.

    Args:
        db: SQLite connection.
        class_year: Target recruiting class. Defaults to next class
            (e.g. 2027 in May 2026; 2028 after Dec 18 of the prior year).
        today: For tests / pinned runs.
        output_dir: Site output root.
        top_n: How many programs to surface (default 25).

    Returns:
        Dict: {'class_year', 'program_count', 'output_path', 'days_to_kickoff'}.
    """
    today = today or date.today()
    class_year = class_year or _default_class_year(today)

    programs = _fetch_program_class_data(db, class_year=class_year, top_n=top_n)
    week_label = cfb_week_label(today, db)
    dtk = days_to_kickoff(today, db=db)

    title = f"Recruit Watch — Class of {class_year}"
    eyebrow = f"{week_label}"
    title_heading = f"Class of {class_year}: Top {top_n} Programs"
    lede = (
        f"Weighted by star rating (5★=10 pts, 4★=4, 3★=1). "
        f"Updated daily from CFBD recruiting profiles. "
        f"{dtk} days until kickoff."
    )

    if not programs:
        body = (
            '<div class="recruit-empty">'
            f"<strong>No recruiting commitments yet for the {class_year} class.</strong>"
            "<br><br>"
            "Player commitments will surface here as the CFBD recruiting feed "
            "populates. Check back after the next official-visits window."
            "</div>"
        )
    else:
        cards = "".join(
            _format_card(rank, prog) for rank, prog in enumerate(programs, start=1)
        )
        body = f'<div class="recruit-grid">{cards}</div>'

    from cfb_rankings.common.head_chrome import render_head_chrome
    head_chrome = render_head_chrome(
        page_path=f"/recruit-board/{class_year}/",
        title=title,
        description=f"Top {top_n} recruiting classes for {class_year}.",
        og_type="article",
    )
    # Database-archetype meta-footer (Session 6 Track 6 adopter #6).
    from cfb_rankings.database_archetype import (
        render_database_meta_footer as _db_archetype_footer,
    )
    meta_footer = _db_archetype_footer(
        label=(
            "program tracked" if len(programs) == 1
            else "programs tracked"
        ),
        total_rows=len(programs),
        methodology_label="How the recruit board is weighted",
        methodology_href="/methodology/",
        updated_text=f"Updated {today.isoformat()}",
    )
    html = _HTML_TEMPLATE.format(
        title=escape(title),
        description=escape(f"Top {top_n} recruiting classes for {class_year}."),
        eyebrow=escape(eyebrow),
        title_heading=escape(title_heading),
        lede=escape(lede),
        body=body,
        head_chrome=head_chrome,
        meta_footer=meta_footer,
    )

    out_root = Path(output_dir)
    page_dir = out_root / "recruit-board" / str(class_year)
    page_dir.mkdir(parents=True, exist_ok=True)
    page_path = page_dir / "index.html"
    page_path.write_text(html, encoding="utf-8")

    log.info(
        "render_recruit_board: class=%d programs=%d -> %s",
        class_year, len(programs), str(page_path),
    )
    return {
        "class_year": class_year,
        "program_count": len(programs),
        "output_path": str(page_path),
        "days_to_kickoff": dtk,
    }
