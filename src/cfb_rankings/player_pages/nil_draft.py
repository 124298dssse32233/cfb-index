"""NIL + Draft card — Brief §4.12 / Wave 19.

Shows recruiting pedigree (when applicable), NFL draft outcome (when
applicable), and live NIL valuation from On3 (when available in
player_nil_valuations).

For a current undergrad: shows On3 NIL value + rank + whisper market rate.
For a recruit profile: shows star rating + composite + national rank.
For a drafted alumnus: shows draft year + round + pick + NFL team.

Public API:
    render_nil_draft(db, player_id) -> str
    NIL_DRAFT_CSS                   -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


NIL_DRAFT_CSS = """
/* NIL + Draft card */
.nil-draft {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(12px, 1.6vw, 18px) clamp(14px, 1.8vw, 22px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.nil-draft__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 8px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 6px;
}
.nil-draft__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.nil-draft__title {
  font-size: 1.0rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.nil-draft__body {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.nil-draft__tile {
  background: rgba(255,255,255,0.018);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 9px 12px;
}
.nil-draft__tile-label {
  font-size: 0.66rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0 0 2px 0;
}
.nil-draft__tile-value {
  font-size: 1.05rem; font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
  margin: 0;
}
.nil-draft__tile-sub {
  font-size: 0.72rem; color: var(--text-quiet, rgba(255,255,255,0.55));
}
.nil-draft__tile--gold {
  border-color: var(--accolade-gold-base, #d1a23a);
  background: rgba(209, 162, 58, 0.06);
}
.nil-draft__tile--gold .nil-draft__tile-value {
  color: var(--accolade-gold-base, #d1a23a);
}
.nil-draft__stars {
  display: inline-flex; gap: 2px; color: var(--accolade-gold-base, #d1a23a);
  font-size: 0.90rem; letter-spacing: 1px;
}
.nil-draft__note {
  margin-top: 8px;
  font-size: 0.66rem; color: var(--text-quiet, rgba(255,255,255,0.50));
  font-style: italic;
}
"""


def _star_chars(n: int) -> str:
    n = max(0, min(5, int(n or 0)))
    return "★" * n + "☆" * (5 - n)


def _fetch_nil_valuation(db, player_id: int) -> dict[str, Any] | None:
    """Return most recent On3 NIL snapshot for this player."""
    rows = db.query_all(
        """
        select rank, valuation_usd, whisper_usd, as_of_date, source_name
          from player_nil_valuations
         where player_id = :pid
         order by as_of_date desc
         limit 1
        """,
        {"pid": player_id},
    )
    if not rows:
        return None
    return dict(rows[0])


def _fmt_nil(usd: int | None) -> str:
    """$5,440,974 → '$5.44M', 450000 → '$450K'."""
    if not usd:
        return "—"
    if usd >= 1_000_000:
        return f"${usd / 1_000_000:.2f}M"
    if usd >= 1_000:
        return f"${usd // 1_000:,}K"
    return f"${usd:,}"


def _fmt_date(iso: str | None) -> str:
    """'2026-06-10' → 'Jun 2026'."""
    if not iso:
        return ""
    try:
        parts = iso[:7].split("-")
        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        return f"{months[int(parts[1]) - 1]} {parts[0]}"
    except (IndexError, ValueError):
        return iso[:7]


def _fetch_recruit(db, player_id: int) -> dict[str, Any] | None:
    rows = db.query_all(
        """
        select stars, rating, national_rank, season_year, committed_team, position
          from player_recruiting_profiles
         where player_id = :pid
         order by season_year desc
         limit 1
        """,
        {"pid": player_id},
    )
    if not rows:
        return None
    return dict(rows[0])


def _fetch_draft(db, player_id: int) -> dict[str, Any] | None:
    rows = db.query_all(
        """
        select draft_year, round, pick, overall, nfl_team, position
          from player_nfl_draft
         where player_id = :pid
         order by draft_year desc
         limit 1
        """,
        {"pid": player_id},
    )
    if not rows:
        return None
    return dict(rows[0])


def render_nil_draft(db, player_id: int | None) -> str:
    if db is None or player_id is None:
        return ""
    pid = int(player_id)
    nil_val = _fetch_nil_valuation(db, pid)
    recruit  = _fetch_recruit(db, pid)
    draft    = _fetch_draft(db, pid)
    if not nil_val and not recruit and not draft:
        return ""

    tiles: list[str] = []

    # ── NIL valuation (On3) ─────────────────────────────────────────────────
    if nil_val:
        val_str    = _fmt_nil(nil_val.get("valuation_usd"))
        whisper    = nil_val.get("whisper_usd")
        rank       = nil_val.get("rank")
        as_of      = _fmt_date(nil_val.get("as_of_date"))
        rank_str   = f"#{rank} nationally" if rank else "On3 ranking"
        whisper_str = f"market rate {_fmt_nil(whisper)}" if whisper else ""
        sub_parts  = [p for p in [rank_str, as_of] if p]
        tiles.append(
            '<div class="nil-draft__tile nil-draft__tile--gold">'
            '<p class="nil-draft__tile-label">NIL Valuation · On3</p>'
            f'<p class="nil-draft__tile-value">{escape(val_str)}</p>'
            f'<p class="nil-draft__tile-sub">{escape(" · ".join(sub_parts))}</p>'
            '</div>'
        )
        if whisper:
            tiles.append(
                '<div class="nil-draft__tile">'
                '<p class="nil-draft__tile-label">Whisper Rate</p>'
                f'<p class="nil-draft__tile-value">{escape(_fmt_nil(whisper))}</p>'
                '<p class="nil-draft__tile-sub">per-deal market estimate</p>'
                '</div>'
            )

    # ── Recruiting profile ───────────────────────────────────────────────────
    if recruit:
        stars     = recruit.get("stars") or 0
        rating    = recruit.get("rating")
        natl      = recruit.get("national_rank")
        committed = recruit.get("committed_team") or "—"
        tiles.append(
            '<div class="nil-draft__tile nil-draft__tile--gold">'
            '<p class="nil-draft__tile-label">Recruit stars</p>'
            f'<p class="nil-draft__tile-value">'
            f'<span class="nil-draft__stars">{escape(_star_chars(stars))}</span>'
            '</p>'
            f'<p class="nil-draft__tile-sub">to {escape(str(committed))}</p>'
            '</div>'
        )
        if rating is not None:
            tiles.append(
                '<div class="nil-draft__tile">'
                '<p class="nil-draft__tile-label">Composite</p>'
                f'<p class="nil-draft__tile-value">{float(rating):.4f}</p>'
                f'<p class="nil-draft__tile-sub">'
                + (f"#{int(natl)} national" if natl else "")
                + '</p>'
                '</div>'
            )

    # ── NFL Draft ────────────────────────────────────────────────────────────
    if draft:
        rd   = draft.get("round")
        pk   = draft.get("pick")
        ov   = draft.get("overall")
        team = draft.get("nfl_team") or "—"
        year = draft.get("draft_year")
        tiles.append(
            '<div class="nil-draft__tile nil-draft__tile--gold">'
            '<p class="nil-draft__tile-label">NFL Draft</p>'
            f'<p class="nil-draft__tile-value">{year} &middot; Rd {rd}, Pick {pk}</p>'
            f'<p class="nil-draft__tile-sub">#{ov} overall &middot; {escape(str(team))}</p>'
            '</div>'
        )

    if not tiles:
        return ""

    has_nil  = nil_val is not None
    eyebrow  = "NIL · Recruiting · NFL Draft" if (recruit or draft) else "NIL Valuation"
    title    = "Market value, pedigree &amp; pro outcome" if (recruit or draft) else "Market value"

    return (
        '<section class="nil-draft" data-module="nil-draft" data-state="ready">'
        '<header class="nil-draft__head">'
        '<div>'
        f'<p class="nil-draft__eyebrow">{eyebrow}</p>'
        f'<p class="nil-draft__title">{title}</p>'
        '</div>'
        '</header>'
        f'<div class="nil-draft__body">{"".join(tiles)}</div>'
        '</section>'
    )
