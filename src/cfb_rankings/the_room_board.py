"""Players in The Room — discovery page for live player-scope mood cards.

The core player-page modules live inside 17k HTML files; without a
leaderboard surface, nobody finds the 2–3 players whose mood cards
actually cleared the floor. This builder writes a small standalone page
that lists every player whose ``The Room`` card renders ``data-state="ready"``
today, with belief score, bucket, confidence, and the representative
quote.

Output: ``output/site/players/the-room.html``. The page is idempotent —
re-running overwrites it cleanly.

CLI: ``python manage.py build-the-room-board [--season YYYY] [--week N]``.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.fan_intelligence import compute_player_mood_index


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def clean_truncate(text: str, max_chars: int = 240) -> str:
    text = _strip_reddit_escapes(text)
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.6:
        truncated = truncated[:last_space]
    return truncated.rstrip(".,;:") + "…"


# Reddit-flavored markdown escapes the characters # > * _ ~ ` to prevent
# autolinks / formatting. When we display the raw text those literal
# backslashes look like a rendering bug ("\#18 Michigan" instead of
# "#18 Michigan"). Strip them; we're not doing reddit-side formatting
# either way.
_REDDIT_ESCAPE_RE = __import__("re").compile(r"\\([#>*_~`\[\](){}.!|+\\-])")


def _strip_reddit_escapes(text: str) -> str:
    if not text or "\\" not in text:
        return text
    return _REDDIT_ESCAPE_RE.sub(r"\1", text)


def _clean_attribution(author_pseudonym: str) -> str:
    """Strip email prefix from author display string.

    'email@host.com (Display Name)' → 'Display Name'

    Some podcast feeds store the iTunes RSS owner field which already
    arrived truncated (paren never closed by upstream pipeline) — e.g.
    'lockedonpodcasts@gmail.com (LJ Martin, Jake Hatch, Deion Sanders'.
    Handle that case by extracting whatever follows '(' even when the
    closing paren is missing, and trimming any dangling comma.

    Other formats are returned as-is.
    """
    s = author_pseudonym.strip()
    # Closed-paren form: "email (Name)"
    m = re.match(r"^[^\s@]+@[^\s@]+\s+\((.+)\)\s*$", s)
    if m:
        return m.group(1)
    # Open-paren form (upstream truncated): "email (Name1, Name2"
    m = re.match(r"^[^\s@]+@[^\s@]+\s+\((.+)$", s)
    if m:
        return m.group(1).rstrip(",;: ").rstrip("…") + "…"
    return author_pseudonym


# ---------------------------------------------------------------------------
# Asset helpers
# ---------------------------------------------------------------------------

def _find_css_filename(site_root: Path) -> str:
    """Resolve the live cfb-index.<hash>.css filename from the assets dir."""
    assets = site_root / "assets"
    if assets.exists():
        css_files = sorted(
            assets.glob("cfb-index.*.css"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if css_files:
            return css_files[0].name
    return "cfb-index.css"


# ---------------------------------------------------------------------------
# Page chrome (nav + head)
# ---------------------------------------------------------------------------

_ROOM_STYLES = """\
/* The Room board — page-scoped styles */
.the-room-page { max-width: 1160px; margin: 0 auto; padding: 40px 20px 96px; }
.the-room-hero { margin-bottom: 40px; }
.the-room-hero__eyebrow {
  font-family: 'IBM Plex Mono', 'SFMono-Regular', monospace;
  font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted-foreground, #8a90a1); margin-bottom: 8px;
}
.the-room-hero__title {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: clamp(28px, 5vw, 44px); font-weight: 700;
  line-height: 1.1; letter-spacing: -0.02em;
  color: var(--foreground, #f5f6fa); margin: 0 0 12px;
}
.the-room-hero__dek {
  color: var(--muted-foreground, #8a90a1); font-size: 15px;
  line-height: 1.6; max-width: 60ch; margin: 0;
}
.the-room-board__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
@media (max-width: 860px) {
  .the-room-board__grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 540px) {
  .the-room-board__grid { grid-template-columns: 1fr; }
  .the-room-page { padding: 24px 16px 64px; }
}

.the-room-board__card {
  background: var(--card, #171b24);
  border: 1px solid var(--border, rgba(255,255,255,0.08));
  border-radius: 12px;
  padding: 20px 20px 16px;
  display: flex; flex-direction: column; gap: 12px;
  transition: border-color 0.15s;
}
.the-room-board__card:hover {
  border-color: rgba(255,255,255,0.18);
}

.the-room-board__header { display: flex; flex-direction: column; gap: 4px; }
.the-room-board__header h2 {
  font-size: 18px; font-weight: 700; margin: 0;
  font-family: 'Source Serif 4', Georgia, serif;
  color: var(--foreground, #f5f6fa);
  line-height: 1.2;
}
.the-room-board__header h2 a {
  color: inherit; text-decoration: none;
}
.the-room-board__header h2 a:hover { text-decoration: underline; }
.the-room-board__meta {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--muted-foreground, #8a90a1);
}

.the-room-board__figures {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 6px 12px;
  padding: 12px 0; border-top: 1px solid var(--border, rgba(255,255,255,0.08));
  border-bottom: 1px solid var(--border, rgba(255,255,255,0.08));
}
.the-room-board__figures > div {
  display: flex; flex-direction: column; gap: 1px;
}
.the-room-board__figures span {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--muted-foreground, #8a90a1);
}
.the-room-board__figures strong {
  font-size: 15px; font-weight: 700; font-variant-numeric: tabular-nums;
  color: var(--foreground, #f5f6fa);
}
.the-room-board__figures > div:first-child strong {
  font-size: 22px; color: var(--accent, #3ea073);
}

.the-room-board__quote {
  margin: 0; padding: 0; flex: 1;
}
.the-room-board__quote p {
  font-style: italic; font-size: 14px; line-height: 1.55;
  color: var(--muted-foreground, #8a90a1); margin: 0 0 8px;
  font-family: 'Source Serif 4', Georgia, serif;
}
.the-room-board__quote cite {
  font-size: 11px; font-style: normal;
  color: var(--muted-foreground, #8a90a1); opacity: 0.7;
}
.the-room-board__quote cite a {
  color: inherit; text-decoration: none; border-bottom: 1px dotted currentColor;
}
.the-room-board__quote cite a:hover { opacity: 1; }
"""


def _nav_html(prefix: str = "../", current: str = "players") -> str:
    """Site nav matching the standard topbar used by player/conference pages."""
    active_key = {
        "players": "players",
        "player": "players",
    }.get(current, current)
    links = [
        ("rankings", "Power Rankings", f"{prefix}rankings/index.html"),
        ("teams", "Teams", f"{prefix}teams/index.html"),
        ("players", "Players", f"{prefix}players/spotlight.html"),
        ("heisman", "Heisman", f"{prefix}heisman/index.html"),
        ("programs", "Programs", f"{prefix}programs/index.html"),
        ("history", "History", f"{prefix}history/index.html"),
        ("model", "The Model", f"{prefix}about-model/index.html"),
        ("analysis", "Analysis", f"{prefix}conferences/index.html"),
        ("archive", "Weekly Archive", f"{prefix}archive/index.html"),
        ("methodology", "Methodology", f"{prefix}methodology/fan-intelligence.html"),
    ]
    rendered = "".join(
        f'<a class="nav-link{" is-current" if key == active_key else ""}" href="{href}">{label}</a>'
        for key, label, href in links
    )
    return (
        f'<a class="skip-link" href="#main-content">Skip to main content</a>'
        f'<header class="topbar">'
        f'<a class="brand" href="{prefix}index.html">THE CFB INDEX</a>'
        f'<button class="nav-toggle" type="button" aria-expanded="false"'
        f' aria-controls="site-nav-links" aria-label="Toggle navigation menu">Menu</button>'
        f'<div class="topbar-panels">'
        f'<nav class="nav" id="site-nav-links">{rendered}</nav>'
        f'<div class="nav-actions">'
        f'<a class="nav-action" href="{prefix}matchups/index.html">Matchup Simulator</a>'
        f'<a class="nav-action" href="{prefix}compare/index.html">Compare Teams</a>'
        f"</div></div></header>"
        """
        <script>
          (() => {
            const topbars = Array.from(document.querySelectorAll('.topbar'));
            topbars.forEach((topbar) => {
              const toggle = topbar.querySelector('.nav-toggle');
              if (!toggle || toggle.dataset.bound === 'true') return;
              toggle.dataset.bound = 'true';
              const close = () => {
                topbar.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
              };
              toggle.addEventListener('click', () => {
                const isOpen = topbar.classList.toggle('is-open');
                toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
              });
              topbar.querySelectorAll('a').forEach((link) => {
                link.addEventListener('click', close);
              });
              document.addEventListener('click', (event) => {
                if (!topbar.contains(event.target)) { close(); }
              });
              window.addEventListener('resize', () => {
                if (window.innerWidth > 860) { close(); }
              });
            });
          })();
        </script>"""
    )


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _fetch_rows(db: Database, season_year: int, week: int) -> list[dict[str, Any]]:
    """Return one row per live Room card, ordered by mention_count desc."""
    index = compute_player_mood_index(db, season_year, week)
    if not index:
        return []
    rows: list[dict[str, Any]] = []
    for pid, story in index.items():
        player = db.query_one(
            "select full_name, position from players where player_id = :pid",
            {"pid": pid},
        )
        name = (player or {}).get("full_name") or f"Player {pid}"
        position = (player or {}).get("position") or ""
        slug = _reconstruct_slug(name, pid)
        rows.append({
            "player_id": pid,
            "player_name": name,
            "position": position,
            "slug": slug,
            "belief": (story.get("belief") or {}).get("score"),
            "belief_label": (story.get("belief") or {}).get("label") or "",
            "archetype": story.get("archetype") or "",
            "confidence": (story.get("confidence") or {}).get("label") or "",
            "scope": story.get("scope") or "",
            "primary_bucket": story.get("primary_bucket") or "",
            "mentions": (story.get("sample") or {}).get("mentions") or 0,
            "authors": (story.get("sample") or {}).get("authors") or 0,
            "top_quote_text": (story.get("top_quote") or {}).get("text"),
            "top_quote_author": (story.get("top_quote") or {}).get("author_pseudonym"),
            "top_quote_source": (story.get("top_quote") or {}).get("source_url"),
        })
    rows.sort(key=lambda r: int(r["mentions"]), reverse=True)
    return rows


def _reconstruct_slug(full_name: str, player_id: int) -> str:
    parts = (full_name or "").lower().replace(".", "").split()
    base = "-".join(p for p in parts if p)
    return f"{base}-{player_id}" if base else f"player-{player_id}"


def _floor_copy() -> str:
    from cfb_rankings.fan_intelligence import (
        MIN_AUTHORS_FOR_SIGNAL,
        MIN_MENTIONS_FOR_SIGNAL,
    )
    return f"≥{MIN_MENTIONS_FOR_SIGNAL} mentions and ≥{MIN_AUTHORS_FOR_SIGNAL} unique authors"


# ---------------------------------------------------------------------------
# Card renderer
# ---------------------------------------------------------------------------

def _render_card(row: dict[str, Any]) -> str:
    belief_txt = "--"
    belief_score = row.get("belief")
    if belief_score is not None:
        try:
            belief_txt = f"{float(belief_score):+.1f}"
        except (TypeError, ValueError):
            belief_txt = "--"

    quote_block = ""
    if row.get("top_quote_text"):
        raw_text = str(row["top_quote_text"])
        quote_text = clean_truncate(raw_text, max_chars=240)
        src_url = row.get("top_quote_source") or ""
        raw_author = str(row.get("top_quote_author") or "fan")
        attrib = escape(_clean_attribution(raw_author))
        attrib_html = f'<a href="{escape(src_url)}">{attrib}</a>' if src_url else attrib
        quote_block = (
            f'<blockquote class="the-room-board__quote">'
            f"<p>{escape(quote_text)}</p>"
            f"<cite>— {attrib_html}</cite>"
            f"</blockquote>"
        )

    scope_label = "season rollup" if row.get("scope") == "season" else "this week"
    bucket = row.get("primary_bucket") or "fan"
    position = str(row.get("position") or "")

    return (
        f'<article class="the-room-board__card"'
        f' data-module="the-room-board-card"'
        f' data-primary-bucket="{escape(bucket)}">'
        f'<header class="the-room-board__header">'
        f'<h2><a href="{escape(row["slug"])}.html">{escape(row["player_name"])}</a></h2>'
        f'<span class="the-room-board__meta">{escape(position)} · {escape(scope_label)}</span>'
        f"</header>"
        f'<div class="the-room-board__figures">'
        f"<div><span>Belief</span><strong>{escape(belief_txt)}</strong></div>"
        f"<div><span>Archetype</span><strong>{escape(str(row.get('archetype') or '--'))}</strong></div>"
        f"<div><span>Mentions</span><strong>{int(row['mentions'])}</strong></div>"
        f"<div><span>Authors</span><strong>{int(row['authors'])}</strong></div>"
        f"<div><span>Primary</span><strong>{escape(bucket)}</strong></div>"
        f"<div><span>Confidence</span><strong>{escape(str(row.get('confidence') or '--'))}</strong></div>"
        f"</div>"
        f"{quote_block}"
        f"</article>"
    )


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------

def render_the_room_board_html(
    rows: list[dict[str, Any]],
    season_year: int,
    week: int,
    css_filename: str = "cfb-index.css",
) -> str:
    if not rows:
        body = (
            '<section class="panel the-room-board the-room-board--empty">'
            "<p>No player in this season has cleared the mention floor yet. "
            "We’ll publish cards as soon as corpus density picks up — for "
            "in-season data, that usually means Monday mornings after Week 1.</p>"
            "</section>"
        )
    else:
        scope_word = "week" if any(r["scope"] == "weekly" for r in rows) else "season"
        count = len(rows)
        noun = "player" if count == 1 else "players"
        cards = "".join(_render_card(r) for r in rows)
        body = (
            f'<div class="the-room-hero">'
            f'<p class="the-room-hero__eyebrow">The Room · {season_year}</p>'
            f'<h1 class="the-room-hero__title">Players in The Room — {season_year}</h1>'
            f'<p class="the-room-hero__dek">'
            f"Who fans are actually talking about. Each card shows the player's "
            f"<strong>Belief score</strong> (where the conversation falls on a "
            f"−100 → +100 cold/hot scale, derived from a weighted sentiment read "
            f"across own fans, rivals, national press, and media), the dominant "
            f"<strong>cohort</strong>, mention volume, and a representative quote "
            f"from the surrounding coverage."
            f"</p>"
            f'<p class="the-room-hero__dek">'
            f"{count} {noun} cleared the publish floor this {scope_word}. "
            f"Gated at {_floor_copy()}."
            f"</p>"
            f"</div>"
            f'<section class="the-room-board__grid">{cards}</section>'
        )

    nav = _nav_html(prefix="../", current="players")
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>Players in The Room — {season_year} | CFB Index</title>\n'
        f'<link rel="stylesheet" href="/assets/{css_filename}">\n'
        f"<style>\n{_ROOM_STYLES}</style>\n"
        "</head>\n"
        "<body>\n"
        '<main class="site-shell" id="main-content">\n'
        f"{nav}\n"
        f'<div class="the-room-page">\n{body}\n</div>\n'
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )


# ---------------------------------------------------------------------------
# Build entry point
# ---------------------------------------------------------------------------

def build_the_room_board(
    db: Database,
    *,
    output_dir: str | Path = "output/site",
    season_year: int,
    week: int = 1,
) -> Path:
    site_root = Path(output_dir)
    css_filename = _find_css_filename(site_root)
    rows = _fetch_rows(db, season_year, week)
    html = render_the_room_board_html(rows, season_year, week, css_filename=css_filename)
    out_dir = site_root / "players"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "the-room.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


__all__ = ["build_the_room_board", "render_the_room_board_html", "clean_truncate"]
