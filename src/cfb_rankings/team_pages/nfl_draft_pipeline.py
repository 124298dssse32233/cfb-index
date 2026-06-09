"""NFL Draft Pipeline chip — surfaces a team's recent NFL Draft pipeline.

Sources from `player_nfl_draft` (CFBD-ingested, 2018+). For each team we
compute:
  - Total picks across the recent window (default 5 years)
  - Highest pick (lowest overall number)
  - Marquee picks (top-3 by overall) with name + position
  - First-round count + percentile-band classification

Brief mapping:
  - Audit T20 (NFL pipeline) — directly resolves
  - Brief §16.5 ("NFL development pipeline") — matches the chip spec

Renders even with one pick. Empty (skips) when zero picks in the window.

Public API:
    render_nfl_draft_pipeline(db, profile, snapshot) -> str
    NFL_DRAFT_PIPELINE_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


NFL_DRAFT_PIPELINE_CSS = """
/* NFL Draft Pipeline chip */
.nfl-draft-pipeline {
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-secondary, var(--accent-primary, #c9a24a));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
  display: grid;
  gap: 10px;
}
.nfl-draft-pipeline__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.nfl-draft-pipeline__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.nfl-draft-pipeline__window {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
}
.nfl-draft-pipeline__verdict {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 16px;
  align-items: baseline;
}
.nfl-draft-pipeline__band {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.6vw + 8px, 32px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--fg-primary);
  margin: 0;
}
.nfl-draft-pipeline__band--elite      { color: #4f9d6b; }
.nfl-draft-pipeline__band--strong     { color: var(--accent-primary, #c9a24a); }
.nfl-draft-pipeline__band--steady     { color: var(--fg-primary); }
.nfl-draft-pipeline__band--developing { color: var(--fg-secondary); }
.nfl-draft-pipeline__band--thin       { color: var(--fg-secondary); }

.nfl-draft-pipeline__count {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(28px, 2vw + 10px, 40px);
  font-weight: 400;
  line-height: 1;
  color: var(--accent-primary, #c9a24a);
}
.nfl-draft-pipeline__count-label {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--fg-muted);
  text-transform: uppercase;
  text-align: right;
  display: block;
}

.nfl-draft-pipeline__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 56ch;
}
.nfl-draft-pipeline__marquee {
  display: grid;
  gap: 6px;
  margin-top: 4px;
}
.nfl-draft-pipeline__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: baseline;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 6px;
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
}
.nfl-draft-pipeline__pick {
  color: var(--accent-primary, #c9a24a);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.nfl-draft-pipeline__name {
  color: var(--fg-primary);
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-weight: 600;
}
.nfl-draft-pipeline__pos {
  color: var(--fg-muted);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
"""


def _fetch_recent_picks(db, team_id: int, window_years: int = 5) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select draft_year, round, overall, player_name, position, nfl_team
          from player_nfl_draft
         where college_team_id = :tid
           and draft_year >= (select max(draft_year) from player_nfl_draft) - :win + 1
         order by overall asc
        """,
        {"tid": team_id, "win": window_years},
    )
    return rows


def _band(total: int, first_round: int) -> tuple[str, str, str]:
    """Return (label, css_suffix, story)."""
    if total >= 25 or first_round >= 5:
        return (
            "Elite",
            "elite",
            f"{total} picks last 5 cycles, including {first_round} in round 1. "
            "Top recruit destination + development pipeline.",
        )
    if total >= 15:
        return (
            "Strong",
            "strong",
            f"{total} picks last 5 cycles. {first_round} first-round picks. "
            "Recruits with NFL ambitions notice.",
        )
    if total >= 8:
        return (
            "Steady",
            "steady",
            f"{total} picks last 5 cycles. Reliable mid-tier pipeline.",
        )
    if total >= 3:
        return (
            "Developing",
            "developing",
            f"{total} picks last 5 cycles. Pipeline emerging.",
        )
    return (
        "Thin",
        "thin",
        f"{total} picks last 5 cycles. Roster development still maturing.",
    )


def render_nfl_draft_pipeline(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    rows = _fetch_recent_picks(db, int(snapshot.team_id), window_years=5)
    if not rows:
        return ""

    total = len(rows)
    first_round = sum(1 for r in rows if int(r.get("round") or 99) == 1)
    label, suffix, story = _band(total, first_round)

    # Top 3 marquee picks by overall (lowest overall number)
    marquee = rows[:3]
    marquee_html: list[str] = []
    for r in marquee:
        overall = r.get("overall")
        rnd = r.get("round") or 0
        name = r.get("player_name") or "Unknown"
        pos = r.get("position") or ""
        nfl = r.get("nfl_team") or ""
        year = r.get("draft_year") or ""

        if overall:
            pick_chunk = f"#{int(overall)}"
        else:
            pick_chunk = f"R{int(rnd)}"

        meta_chunk = f"{year} · {nfl}" if year and nfl else (str(year) or nfl)

        marquee_html.append(
            f"""<div class="nfl-draft-pipeline__row">
  <span class="nfl-draft-pipeline__pick">{escape(pick_chunk)}</span>
  <span class="nfl-draft-pipeline__name">{escape(name)}</span>
  <span class="nfl-draft-pipeline__pos">{escape(pos)} · {escape(meta_chunk)}</span>
</div>"""
        )

    # Compute the actual window range from data
    years = sorted({int(r.get("draft_year")) for r in rows if r.get("draft_year")})
    if years:
        window_label = f"{years[0]}–{years[-1]}"
    else:
        window_label = "Recent"

    return f"""
<section class="nfl-draft-pipeline" aria-labelledby="nfl-draft-pipeline-h"
         data-module="nfl-draft-pipeline" data-state="ready" data-band="{suffix}">
  <div class="nfl-draft-pipeline__head">
    <p class="nfl-draft-pipeline__eyebrow" id="nfl-draft-pipeline-h">NFL Draft Pipeline</p>
    <span class="nfl-draft-pipeline__window">{escape(window_label)}</span>
  </div>
  <div class="nfl-draft-pipeline__verdict">
    <div>
      <h2 class="nfl-draft-pipeline__band nfl-draft-pipeline__band--{suffix}">{escape(label)}</h2>
      <p class="nfl-draft-pipeline__story">{escape(story)}</p>
    </div>
    <div>
      <span class="nfl-draft-pipeline__count">{total}</span>
      <span class="nfl-draft-pipeline__count-label">picks · {first_round} R1</span>
    </div>
  </div>
  <div class="nfl-draft-pipeline__marquee">
    {''.join(marquee_html)}
  </div>
</section>"""


__all__ = ["render_nfl_draft_pipeline", "NFL_DRAFT_PIPELINE_CSS"]
