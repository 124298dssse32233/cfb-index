"""Render a one-page specimen showing every hero-finding archetype.

End-to-end smoke that exercises:
  - The v5-7.5 generator bodies (daily / heisman / team)
  - The confidence chip helper
  - The render_hero_finding_html primitive

Useful for verifying the integration path before Window A wires the
real renderers. Writes to docs/mockups/hero_findings_specimen.html
so the file lives alongside the existing mockup set.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from cfb_rankings.db import Database
from cfb_rankings.hero_findings import (
    HeroFinding, FindingKind,
    generate_daily_finding,
    generate_heisman_finding,
    generate_team_finding,
    render_hero_finding_html,
)


def _seed_db() -> Database:
    """Build an in-memory DB with realistic test data."""
    fd, path = tempfile.mkstemp(suffix=".db")
    import os
    os.close(fd)
    d = Database(f"sqlite:///{path}")
    d.execute("""
        CREATE TABLE daily_takes (
            edition_date TEXT, rank_position INTEGER, headline TEXT,
            body TEXT, source_count INTEGER, primary_entity_slug TEXT,
            cited_sources_json TEXT)""")
    d.execute("""
        CREATE TABLE heisman_market_odds_weekly (
            season_year INTEGER, week INTEGER, player_id INTEGER, team_id INTEGER,
            provider TEXT, source_name TEXT, source_player_key TEXT,
            player_name TEXT, team_name TEXT, market_name TEXT,
            american_odds INTEGER, decimal_odds REAL, implied_probability REAL,
            notes TEXT, created_at TEXT)""")
    d.execute("""
        CREATE TABLE fanbase_mood_weekly (
            mood_weekly_id INTEGER PRIMARY KEY, team_id INTEGER,
            week_start_date TEXT, mood_score INTEGER, delta_from_prev_week INTEGER,
            top_cause_token TEXT, top_cause_label TEXT, sample_size INTEGER,
            ingested_at TEXT, source TEXT, sample_authors INTEGER, confidence REAL,
            sample_n INTEGER, sample_window TEXT, confidence_floor TEXT,
            model_version TEXT)""")

    # Daily — real take from 2026-05-13
    d.execute(
        "INSERT INTO daily_takes VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("2026-05-13", 1, "Dead Air at the Top",
         "Here's the thing about a slow news Tuesday in May — it's never actually "
         "slow. Movement is happening in DMs.",
         3, "", '["The Athletic","Solid Verbal","Ty Hildenbrandt"]'),
    )
    # Heisman — Drew Allar's +18 spring move (from the mockup)
    for prov in ("BookA", "BookB", "BookC", "BookD"):
        d.execute(
            "INSERT INTO heisman_market_odds_weekly "
            "(season_year, week, player_id, player_name, team_name, provider, implied_probability) "
            "VALUES (2026, 1, 100, 'Drew Allar', 'Penn State', ?, 0.054)",
            (prov,),
        )
        d.execute(
            "INSERT INTO heisman_market_odds_weekly "
            "(season_year, week, player_id, player_name, team_name, provider, implied_probability) "
            "VALUES (2026, 2, 100, 'Drew Allar', 'Penn State', ?, 0.234)",
            (prov,),
        )
    # Team finding — Michigan -15 from W047
    d.execute(
        "INSERT INTO fanbase_mood_weekly "
        "(team_id, week_start_date, mood_score, delta_from_prev_week, "
        "top_cause_label, sample_size) "
        "VALUES (130, '2026-04-22', 58, -15, 'Moore presser', 3200)",
    )
    return d


HTML_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hero Findings Specimen — v5-7.5 generator output</title>
<link rel="stylesheet" href="_mockup_shared.css">
<style>
  body {{ max-width: 900px; margin: 0 auto; padding: 32px; }}
  .case {{ margin: 48px 0; padding-top: 24px; border-top: 0.5px solid var(--color-line); }}
  .case h2 {{ font-family: var(--font-ui); font-size: 13px;
              letter-spacing: 0.11em; text-transform: uppercase;
              color: var(--color-text-muted); margin: 0 0 16px; }}
  .empty {{ font-family: var(--font-serif); font-style: italic;
            color: var(--color-text-muted); padding: 24px; background: var(--color-surface-card);
            border: 0.5px solid var(--color-line); border-radius: 6px; }}
</style>
</head>
<body>
  <h1 style="font-family: var(--font-display); font-size: 56px; letter-spacing: 0.02em;">
    Hero Findings Specimen
  </h1>
  <p style="font-family: var(--font-serif); font-size: 17px; color: var(--color-text-muted);
            max-width: 60ch; margin: 0;">
    End-to-end output from the three wired v5-7.5 generators
    (<code>generate_daily_finding</code>,
    <code>generate_heisman_finding</code>,
    <code>generate_team_finding</code>) against realistic test data.
    Each is rendered via <code>render_hero_finding_html</code>.
    Window A's renderer integration follows the patterns in
    <a href="../design-system/34-integration-playbook.md">34-integration-playbook.md</a>.
  </p>

  <div class="case">
    <h2>Daily — Lead Claim, 3 sources cited</h2>
    {daily}
  </div>

  <div class="case">
    <h2>Heisman — Race Shift, +18 points across 4 sportsbooks</h2>
    {heisman}
  </div>

  <div class="case">
    <h2>Team Profile — Michigan, mood −15 ("Moore presser")</h2>
    {team}
  </div>

  <div class="case">
    <h2>Empty-state demonstration — generators return None when data absent</h2>
    {empty}
  </div>
</body>
</html>"""


def main() -> None:
    db = _seed_db()
    daily = generate_daily_finding(db, edition_date="2026-05-13")
    heisman = generate_heisman_finding(db, season_year=2026)
    team = generate_team_finding(db, team_id=130, season_year=2026)
    # Demonstrate empty-state — querying a non-existent team_id
    empty = generate_team_finding(db, team_id=99999, season_year=2026)

    out = ROOT / "docs" / "mockups" / "hero_findings_specimen.html"
    html = HTML_SHELL.format(
        daily=render_hero_finding_html(daily, eyebrow_text="TODAY'S LEAD") if daily else "<p class='empty'>None — no take for date</p>",
        heisman=render_hero_finding_html(heisman, eyebrow_text="THE RACE SHIFT") if heisman else "<p class='empty'>None — &lt;2 weeks of market data</p>",
        team=render_hero_finding_html(team, eyebrow_text="THIS WEEK") if team else "<p class='empty'>None — no mood data</p>",
        empty=f"<p class='empty'>generate_team_finding(team_id=99999) returned: {empty!r}</p>",
    )
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}")
    print(f"  daily:   {daily.kind.value if daily else 'None'}, number={daily.number if daily else 'n/a'}")
    print(f"  heisman: {heisman.kind.value if heisman else 'None'}, number={heisman.number if heisman else 'n/a'}")
    print(f"  team:    {team.kind.value if team else 'None'}, number={team.number if team else 'n/a'}")
    print(f"  empty:   {empty}")


if __name__ == "__main__":
    main()
