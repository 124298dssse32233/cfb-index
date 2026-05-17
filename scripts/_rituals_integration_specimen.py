"""Render a single team page with synthetic data + write to a specimen
file. Demonstrates the v5-8.5 rituals strip + cultural anchors
integration without requiring a populated DB.

Output: docs/mockups/team_page_rituals_specimen.html

Used as visual proof for PR #118 (Sprint v5-8.5 wire-up).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfb_rankings.team_pages.profile_loader import load_profile  # noqa: E402
from cfb_rankings.team_pages.data import TeamSnapshot  # noqa: E402
from cfb_rankings.team_pages.state_resolver import PageState  # noqa: E402
from cfb_rankings.team_pages.renderer import _render_page  # noqa: E402


def main() -> None:
    profile = load_profile("alabama")

    snapshot = TeamSnapshot(
        team_id=profile.team_id or 333,
        slug="alabama",
        canonical_name="Alabama",
        school_name="University of Alabama",
        level_code="FBS",
        conference_id=1,
        conference_name="SEC",
        season_year=2025,
        wins=13,
        losses=1,
        ties=0,
        ap_rank=4,
        coaches_rank=4,
        cfp_rank=4,
    )
    state = PageState(
        today=date(2026, 5, 17),
        season_year=2025,
        season_phase="OFFSEASON",
        day_of_week_label="Sunday",
        is_in_season=False,
        anchor_variant="dead-period-summer",
        hero_priority="heritage",
        copy_tone="basking",
        accent_key="amber",
        program_tier=1,
        voice_register=profile.voice_register or "Process-Believer",
        tonal_template=profile.tonal_template or "basking",
    )

    html_out = _render_page(
        profile=profile,
        snapshot=snapshot,
        state=state,
        mood={},
        divergence=None,
        sp_rating=None,
        state_of_team=None,
        chronicle_cards=[],
        savant_rows=[],
        savant_narrative=None,
        savant_echo=None,
        savant_season=None,
        rivalry_bundle=None,
        arc_rows=[],
        arc_thesis=None,
        arc_closing=None,
    )

    out_path = ROOT / "docs" / "mockups" / "team_page_rituals_specimen.html"
    out_path.write_text(html_out, encoding="utf-8")
    print(f"wrote {out_path.relative_to(ROOT)} ({len(html_out):,} chars)")
    print(f"ritual cards in output: {html_out.count('ritual-card')}")
    print(f"cultural anchors block: {'cultural-anchors' in html_out}")


if __name__ == "__main__":
    main()
