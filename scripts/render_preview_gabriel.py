"""Render a standalone preview HTML page showing the new Wave 1-21 modules
for Dillon Gabriel. Writes to output/site/players/_preview-gabriel-wave2.html
which you can open via file:// to see the new modules rendered.

Run: python scripts/render_preview_gabriel.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from cfb_rankings.db import Database
from cfb_rankings.player_pages import (
    render_game_log, render_box_savant, render_splits,
    render_peer_comparator, render_supporting_cast,
    render_narrative_arc, render_nil_draft, render_scenario_explorer,
    render_career_standing, render_trophy_case, render_pass_profile,
    build_stat_sparklines, fetch_narrative_arc, PLAYER_PAGE_TOKENS_CSS,
    GAME_LOG_CSS, BOX_SAVANT_CSS, SPLITS_CSS, PEER_COMPARATOR_CSS,
    SUPPORTING_CAST_CSS, NARRATIVE_ARC_CSS, NIL_DRAFT_CSS,
    SCENARIO_EXPLORER_CSS, CAREER_STANDING_CSS, TROPHY_CASE_CSS,
    SPARKLINE_CSS, PASS_PROFILE_CSS,
    render_season_context, SEASON_CONTEXT_CSS,
)
from cfb_rankings.player_pages.composite_score import compute_cfb_index_score
from cfb_rankings.player_pages.signature_story_generator import (
    fetch_signature_story,
)


def _render_module_with_label(label: str, body: str) -> str:
    if not body or "data-state=\"empty\"" in body and "<section" in body and len(body) < 400:
        body_block = (
            '<div style="padding:12px;color:#888;font-style:italic;border:1px dashed #555;border-radius:8px;">'
            f'{label} — empty (data not available for this player)</div>'
        )
    elif not body:
        body_block = (
            '<div style="padding:12px;color:#888;font-style:italic;">'
            f'{label} — no render</div>'
        )
    else:
        body_block = body
    return (
        '<section style="margin: 24px 0;">'
        f'<h2 style="font-size:0.74rem;letter-spacing:0.10em;text-transform:uppercase;'
        f'color:#d1a23a;margin:0 0 10px 0;">{label}</h2>'
        f'{body_block}'
        '</section>'
    )


def main():
    db = Database(str(ROOT / "cfb_rankings.db"))
    PID = 11737
    NAME = "Dillon Gabriel"
    POS = "QB"
    TEAM_ID = 291  # Oregon
    SEASON = 2024

    # Compute everything
    score = compute_cfb_index_score(db, PID, SEASON, POS)
    sig = fetch_signature_story(db, PID, SEASON)
    arc = fetch_narrative_arc(db, PID, SEASON)
    sparks = build_stat_sparklines(db, PID, SEASON, POS)

    # Hero block (simplified)
    hero_html = f"""
    <section style="background:linear-gradient(135deg,#007030 0%,#FEE123 100%);padding:24px;
        border-radius:12px;margin-bottom:24px;color:#fff;">
      <p style="font-size:0.66rem;letter-spacing:0.14em;margin:0 0 4px 0;opacity:0.85;">
        QB · OREGON · BIG TEN · 2024 SEASON</p>
      <h1 style="font-family:'Bebas Neue',sans-serif;font-size:3.2rem;letter-spacing:0.03em;
        margin:0;line-height:1;">DILLON GABRIEL</h1>
      <p style="margin:6px 0 0 0;font-size:0.86rem;opacity:0.92;">
        Sr · #8 · 5-11 / 204 lb · Mililani, HI</p>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
        gap:12px;margin-top:18px;">
        <div style="background:rgba(0,0,0,0.20);padding:10px 12px;border-radius:8px;">
          <p style="font-size:0.66rem;letter-spacing:0.10em;margin:0;opacity:0.78;">
            CFB INDEX SCORE</p>
          <p style="font-size:2rem;font-weight:700;margin:2px 0;color:#FEE123;">
            {score['score'] if score else '—'}</p>
          <p style="font-size:0.72rem;margin:0;opacity:0.85;">
            {score['tier_label'] if score else ''}</p>
        </div>
        <div style="background:rgba(0,0,0,0.20);padding:10px 12px;border-radius:8px;">
          <p style="font-size:0.66rem;letter-spacing:0.10em;margin:0;opacity:0.78;">
            HEISMAN HEAT</p>
          <p style="font-size:2rem;font-weight:700;margin:2px 0;color:#FEE123;">#1</p>
          <p style="font-size:0.72rem;margin:0;opacity:0.85;">19.6% win, 84% finalist</p>
        </div>
        <div style="background:rgba(0,0,0,0.20);padding:10px 12px;border-radius:8px;">
          <p style="font-size:0.66rem;letter-spacing:0.10em;margin:0;opacity:0.78;">
            FAN BELIEF</p>
          <p style="font-size:2rem;font-weight:700;margin:2px 0;opacity:0.65;">—</p>
          <p style="font-size:0.72rem;margin:0;opacity:0.6;">No player FI for Gabriel
            (NFL now)</p>
        </div>
      </div>
    </section>
    """

    # New module renders
    modules: list[tuple[str, str]] = [
        ("Pass Profile (PBP-derived)", render_pass_profile(db, PID, SEASON)),
        ("Box-Score Savant Card (8 OKLCH percentile bars)",
         render_box_savant(db, PID, SEASON, POS)),
        ("Peer Comparator (closest fingerprint match)",
         render_peer_comparator(db, PID, SEASON, POS)),
        ("Splits — Home/Road · Win/Loss · Season halves",
         render_splits(db, PID, SEASON, POS, TEAM_ID)),
        ("Scenario Explorer / Season Pace",
         render_scenario_explorer(db, PID, SEASON, POS)),
        ("Game Log (week-by-week box, with column tooltips + auto notes)",
         render_game_log(db, PID, SEASON, POS, TEAM_ID)),
        ("Season Context strip (Wave 23 — Team record / OC / scheme tag)",
         render_season_context(db, PID)),
        ("Narrative Arc (LLM-generated 3-act season story)",
         render_narrative_arc(arc)),
        ("Signature Story (LLM prose)",
         f'<div style="background:rgba(255,255,255,0.025);padding:14px;border-radius:10px;'
         f'border-left:3px solid #d1a23a;font-size:0.95rem;line-height:1.5;color:#dcdcdc;">'
         f'{sig["story_text"] if sig else "(no LLM story cached)"}'
         f'</div>'),
        ("Supporting Cast & Scheme Context",
         render_supporting_cast(db, PID, SEASON, TEAM_ID)),
        ("Trophy Case (honors streams)",
         render_trophy_case(db, PID)),
        ("Career-retrospective Standing",
         render_career_standing(db, PID)),
        ("NIL + Draft card",
         render_nil_draft(db, PID)),
    ]

    # Sparklines preview
    spark_preview = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));'
        'gap:10px;background:rgba(255,255,255,0.025);padding:14px;border-radius:10px;'
        'border-left:3px solid #d1a23a;">'
    )
    for k in ["Pass yards", "Pass TDs", "Yards/attempt", "Completion rate", "QBR"]:
        if k in sparks:
            spark_preview += (
                f'<div style="background:rgba(255,255,255,0.020);padding:10px;border-radius:8px;">'
                f'<p style="font-size:0.66rem;letter-spacing:0.10em;text-transform:uppercase;'
                f'color:#aaa;margin:0;">{k}</p>'
                f'{sparks[k]}'
                f'</div>'
            )
    spark_preview += "</div>"

    css_bundle = (
        PLAYER_PAGE_TOKENS_CSS + GAME_LOG_CSS + BOX_SAVANT_CSS + SPLITS_CSS +
        PEER_COMPARATOR_CSS + SUPPORTING_CAST_CSS + NARRATIVE_ARC_CSS +
        NIL_DRAFT_CSS + SCENARIO_EXPLORER_CSS + CAREER_STANDING_CSS +
        TROPHY_CASE_CSS + SPARKLINE_CSS + PASS_PROFILE_CSS +
        SEASON_CONTEXT_CSS
    )

    body_html = (
        hero_html
        + _render_module_with_label(
            "Stat-ribbon sparklines (Wave 1b/12 — 8-week trajectory inline SVG)",
            spark_preview,
        )
        + "".join(_render_module_with_label(label, body) for label, body in modules)
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Wave 1-21 Preview — Dillon Gabriel</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --bg: #0f1014;
  --fg: #f4f4f5;
  --accent: #d1a23a;
  --stroke-subtle: rgba(255,255,255,0.08);
  --text-bright: rgba(255,255,255,0.94);
  --text-soft: rgba(255,255,255,0.80);
  --text-quiet: rgba(255,255,255,0.55);
  --accolade-gold-base: #d1a23a;
  --accolade-gold-highlight: #e4c76b;
}}
* {{ box-sizing: border-box; }}
body {{
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  padding: 0;
  line-height: 1.5;
}}
.container {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 20px;
}}
.preview-banner {{
  background: linear-gradient(135deg,#1a1d24 0%,#0f1014 100%);
  border: 1px solid #2a2d34;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
}}
.preview-banner h1 {{
  font-size: 1.1rem; margin: 0 0 4px 0;
}}
.preview-banner p {{
  font-size: 0.86rem; color: var(--text-soft); margin: 0;
}}
{css_bundle}
</style>
</head>
<body>
<div class="container">
  <div class="preview-banner">
    <h1>Wave 1-21 Preview · Dillon Gabriel · Oregon QB · 2024</h1>
    <p>Standalone showcase of every new module shipped today.
       Renders use the live DB; pass-profile uses partial PBP (weeks 1-11 of 16).
       The full build will splice these into the production player page template.</p>
  </div>
  {body_html}
</div>
</body>
</html>"""

    out = ROOT / "output" / "site" / "players" / "_preview-gabriel-wave2.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Wrote: {out}")
    print(f"Size:  {out.stat().st_size:,} bytes")
    print(f"Open:  file:///{out.as_posix()}")


if __name__ == "__main__":
    main()
