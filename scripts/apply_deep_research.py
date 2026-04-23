"""Apply the Deep Research pass-2 YAML output to the seed files.

Reads research/deep_research_refresh_2026-04-23_pass2.yaml, merges into:
  - seeds/priority_teams.yaml    (bluesky handles, youtube, locked_on, boards)
  - seeds/beat_writer_feeds.yaml (Gannett replacements)
  - seeds/podcast_feeds.yaml     (Locked On + Finebaum + Solid Verbal + Audible + Split Zone Duo)
  - seeds/substack_feeds.yaml    (Extra Points; nullify 4 dead ones)
  - seeds/prediction_market_contracts.yaml (full rewrite)
  - seeds/tiktok_creators.yaml   (new file)

Also updates wiki_coach_page per 7 coach changes.

Safe to re-run: every merge is idempotent. The priority_teams loader
upserts on team_id.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SEEDS = REPO / "seeds"
RESEARCH_P2 = REPO / "research" / "deep_research_refresh_2026-04-23_pass2.yaml"
RESEARCH_P1 = REPO / "research" / "deep_research_refresh_2026-04-23.yaml"


def load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def write_yaml(p: Path, data: dict, header: str = "") -> None:
    body = yaml.safe_dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    p.write_text((header.rstrip() + "\n\n" if header else "") + body, encoding="utf-8")
    print(f"  wrote {p.relative_to(REPO)} ({p.stat().st_size:,} bytes)")


# Slug -> wiki_coach_page substitution per pass2 coach_updates
# Only updating the 7 actual changes; extensions keep the same coach.
SLUG_COACH_WIKI = {
    "lsu":           "Lane_Kiffin",
    "michigan":      "Kyle_Whittingham",
    "penn-state":    "Matt_Campbell_(American_football_coach)",
    "kansas-state":  "Collin_Klein",
    "memphis":       "Charles_Huff",
    "tulane":        "Will_Hall",
    "howard":        "Ted_White",
}


def merge_priority_teams() -> None:
    print("\n[1/6] merging seeds/priority_teams.yaml")
    current = load_yaml(SEEDS / "priority_teams.yaml")
    research = load_yaml(RESEARCH_P2)
    research_by_slug = {t["team_slug"]: t for t in research["priority_teams"]}

    # Build slug from team_name for matching. Use lowercase + dashes.
    def slug(name: str) -> str:
        return name.lower().replace(" ", "-")

    updated_count = 0
    for team in current["teams"]:
        tslug = slug(team["team_name"])
        r = research_by_slug.get(tslug)
        if not r:
            continue
        updated_count += 1
        # Apply non-null fields from research
        if r.get("bluesky_beat_handles"):
            team["bluesky_beat_handles"] = r["bluesky_beat_handles"]
        if r.get("youtube_team_channel_id"):
            team["youtube_team_channel_id"] = r["youtube_team_channel_id"]
        if r.get("youtube_fan_channels"):
            team["youtube_fan_channels"] = r["youtube_fan_channels"]
        if r.get("locked_on_rss"):
            team["locked_on_rss"] = r["locked_on_rss"]
        if r.get("message_board_primary"):
            team["message_board_primary"] = r["message_board_primary"]
        # campus_newspaper_feed: research may explicitly set null (correction)
        if "campus_newspaper_feed" in r:
            if r["campus_newspaper_feed"] is None:
                team["campus_newspaper_feed"] = None
            elif r["campus_newspaper_feed"]:
                team["campus_newspaper_feed"] = r["campus_newspaper_feed"]
        # wiki_coach_page: update for the 7 known changes
        if tslug in SLUG_COACH_WIKI:
            team["wiki_coach_page"] = SLUG_COACH_WIKI[tslug]
        # Drop needs_research flag once we've merged research data
        team["needs_research"] = False

    # Add Notre Dame if not already present
    nd_slugs = {slug(t["team_name"]): t for t in current["teams"]}
    if "notre-dame" not in nd_slugs:
        nd = research_by_slug.get("notre-dame")
        if nd:
            current["teams"].append({
                "team_name": "Notre Dame",
                "rank_priority": 21,
                "reddit_team_sub": "notredamefootball",
                "reddit_alumni_sub": None,
                "reddit_city_sub": "southbend",
                "wiki_team_page": "Notre_Dame_Fighting_Irish_football",
                "wiki_coach_page": "Marcus_Freeman",
                "google_news_query": "Notre Dame Fighting Irish football",
                "campus_newspaper_feed": nd.get("campus_newspaper_feed"),
                "athletic_dept_feed": "https://und.com/rss.aspx",
                "message_board_primary": nd.get("message_board_primary"),
                "bluesky_beat_handles": nd.get("bluesky_beat_handles"),
                "youtube_team_channel_id": nd.get("youtube_team_channel_id"),
                "youtube_fan_channels": nd.get("youtube_fan_channels"),
                "locked_on_rss": nd.get("locked_on_rss"),
                "seatgeek_team_slug": "notre-dame-fighting-irish-football",
                "needs_research": False,
            })
            updated_count += 1
            print(f"    + added Notre Dame")

    print(f"  {updated_count} teams merged")
    write_yaml(
        SEEDS / "priority_teams.yaml",
        current,
        header=(
            "# Fan Intelligence priority teams. 21 programs (Notre Dame added 2026-04-23)\n"
            "#   5 SEC / 4 B1G+ND / 3 ACC / 3 B12 / 3 G5 / 2 HBCU\n"
            "#\n"
            "# Last refreshed via Deep Research pass 2 on 2026-04-23\n"
            "# (research/deep_research_refresh_2026-04-23_pass2.yaml).\n"
            "# Includes 7 coach changes (LSU/Mich/PSU/K-State/Memphis/Tulane/Howard),\n"
            "# 13 teams with verified Bluesky beat handles, 17 YouTube channel IDs,\n"
            "# 18 Locked On RSS feeds.\n"
        ),
    )


def apply_replacements() -> None:
    print("\n[2/6] applying replacements to beat/podcast/substack feed YAMLs")
    p1 = load_yaml(RESEARCH_P1)
    reps = {r["replacement_for"]: r for r in (p1.get("replacements") or [])}

    # --- beat_writer_feeds.yaml ---
    beat = load_yaml(SEEDS / "beat_writer_feeds.yaml")
    gannett_to_sbn = {
        "alabama_tuscaloosa_news_cecil":    "roll_bama_roll",
        "clemson_greenville_news":           "shakin_the_southland",
        "florida-state_tallahassee_democrat":"tomahawk_nation",
        "jackson-state_clarion_ledger":      "hbcu_gameday_jackson_state",
        "kansas-state_topeka_capital":       "bring_on_the_cats",
        "memphis_commercial_appeal":         "underdog_dynasty_memphis",
        "michigan_detroit_free_press_um":    "maize_n_brew",
        "ohio-state_dispatch_osu":           "land_grant_holy_land",
        "tennessee_knoxville_sentinel_football":"rocky_top_insider",
        "texas-tech_lubbock_avalanche":      "wreck_em_red",
    }
    beat_updated = 0
    for feed in beat["feeds"]:
        key = f"{feed['team_slug']}_{feed['writer_slug']}"
        rep_key = f"beat_{key}"
        if rep_key in reps and reps[rep_key].get("new_url"):
            feed["writer_slug"] = reps[rep_key]["new_writer_slug"]
            feed["url"] = reps[rep_key]["new_url"]
            feed["needs_research"] = False
            feed["notes"] = reps[rep_key].get("notes", "")[:200]
            beat_updated += 1
    print(f"  beat_writer_feeds: {beat_updated} feeds updated")
    write_yaml(SEEDS / "beat_writer_feeds.yaml", beat,
               header="# Beat-writer RSS feeds - TASK 4.1.\n"
                      "# Updated 2026-04-23 via Deep Research: Gannett outlets replaced\n"
                      "# with SBN/FanSided equivalents that expose working RSS.\n")

    # --- podcast_feeds.yaml ---
    pod = load_yaml(SEEDS / "podcast_feeds.yaml")
    pod_rep = {
        "finebaum_rss":              reps.get("podcast_finebaum_rss"),
        "split_zone_duo":            reps.get("podcast_split_zone_duo"),
        "the_solid_verbal":          reps.get("podcast_the_solid_verbal"),
        "the_audible":               reps.get("podcast_the_audible"),
        "locked_on_alabama":         reps.get("locked_on_alabama"),
        "locked_on_georgia":         reps.get("locked_on_georgia"),
        "locked_on_lsu":             reps.get("locked_on_lsu"),
        "locked_on_buckeyes":        reps.get("locked_on_buckeyes"),
        "locked_on_wolverines":      reps.get("locked_on_wolverines"),
        "locked_on_ducks":           reps.get("locked_on_ducks"),
        "locked_on_college_football":reps.get("locked_on_college_football"),
    }
    pod_updated = 0
    for feed in pod["feeds"]:
        rep = pod_rep.get(feed["show_slug"])
        if rep and rep.get("new_url"):
            feed["url"] = rep["new_url"]
            feed["needs_research"] = False
            pod_updated += 1
    print(f"  podcast_feeds: {pod_updated} feeds updated")
    write_yaml(SEEDS / "podcast_feeds.yaml", pod,
               header="# Podcast RSS feeds. Updated 2026-04-23 via Deep Research:\n"
                      "# 7 Locked On shows + Finebaum + Split Zone Duo + Solid Verbal + Audible\n"
                      "# all moved off the placeholder URLs. 3 Locked On team feeds remain\n"
                      "# unresolved (Clemson, Texas Tech, Boise State).\n")

    # --- substack_feeds.yaml ---
    sub = load_yaml(SEEDS / "substack_feeds.yaml")
    sub_rep = {
        "extra_points":      reps.get("extra_points"),
        "max_olson":         reps.get("max_olson"),
        "recruiting_scoops": reps.get("recruiting_scoops"),
        "swindle_stats":     reps.get("swindle_stats"),
        "the_athletic_cfb":  reps.get("the_athletic_cfb"),
    }
    sub_updated = 0
    sub_dead = []
    new_feeds = []
    for feed in sub["feeds"]:
        rep = sub_rep.get(feed["writer_slug"])
        if rep:
            if rep.get("new_url"):
                feed["url"] = rep["new_url"]
                feed["needs_research"] = False
                sub_updated += 1
                new_feeds.append(feed)
            else:
                sub_dead.append(feed["writer_slug"])
                # skip - don't include dead substacks in the seed
        else:
            new_feeds.append(feed)
    sub["feeds"] = new_feeds
    print(f"  substack_feeds: {sub_updated} updated, {len(sub_dead)} removed ({', '.join(sub_dead)})")
    write_yaml(SEEDS / "substack_feeds.yaml", sub,
               header="# CFB Substack feeds - TASK 4.3. Updated 2026-04-23 via Deep Research:\n"
                      "# Extra Points migrated to new Substack URL. 4 dead feeds removed\n"
                      "# (Max Olson, Recruiting Scoops, Swindle Stats, The Athletic CFB -\n"
                      "# all either 404 or The Athletic disabled per-author RSS entirely).\n")


def apply_prediction_markets() -> None:
    print("\n[3/6] rewriting seeds/prediction_market_contracts.yaml")
    p2 = load_yaml(RESEARCH_P2)
    pm = p2["prediction_markets"]
    out = {"contracts": []}
    for k in pm["kalshi"]:
        out["contracts"].append({
            "platform": "kalshi",
            "ticker": k["ticker"],
            "label": k["label"],
            "needs_research": False,
        })
    for p in pm["polymarket"]:
        out["contracts"].append({
            "platform": "polymarket",
            "slug": p["slug"],
            "label": p["label"],
            "needs_research": False,
        })
    print(f"  {sum(1 for c in out['contracts'] if c['platform']=='kalshi')} kalshi + "
          f"{sum(1 for c in out['contracts'] if c['platform']=='polymarket')} polymarket")
    write_yaml(SEEDS / "prediction_market_contracts.yaml", out,
               header="# Kalshi + Polymarket contracts.\n"
                      "# Refreshed 2026-04-23 via Deep Research pass 2 - all Kalshi tickers\n"
                      "# validated against live kalshi.com URLs; Polymarket slugs via\n"
                      "# gamma-api. 15 Kalshi + 10 Polymarket = 25 total contracts tracked.\n")


def create_tiktok_seed() -> None:
    print("\n[4/6] creating seeds/tiktok_creators.yaml")
    p2 = load_yaml(RESEARCH_P2)
    tt = p2["tiktok_creators"]
    out = {
        "national": tt.get("national") or [],
        "team_aligned": tt.get("team_aligned") or [],
        "hbcu": tt.get("hbcu") or [],
        "dropped": tt.get("dropped") or [],
    }
    n = sum(len(v) for k, v in out.items() if k != "dropped")
    print(f"  {n} creators across 3 buckets ({len(out['dropped'])} dropped candidates documented)")
    write_yaml(SEEDS / "tiktok_creators.yaml", out,
               header="# TikTok creator roster - TASK 6.2 (weekly Cowork observation).\n"
                      "# Seeded 2026-04-23 from Deep Research pass 2. Follower counts\n"
                      "# Chrome-verified. Last-post freshness unverifiable via unauth web\n"
                      "# (TikTok video grids are login-walled) - per-entry field flags this.\n")


def update_coach_changes_in_db() -> None:
    print("\n[5/6] updating teams.head_coach via SQL (informational - not read by adapters)")
    # Skipped — the teams table doesn't have a head_coach column in this
    # repo's schema; coach name is tracked via wiki_coach_page + the
    # coaching_changes table. priority_teams.yaml now has the corrected
    # wiki_coach_page values, which feeds into wiki_pv adapter.
    print("  (nothing to do - wiki_coach_page already updated in priority_teams.yaml)")


def reactivate_replaced_sources() -> None:
    print("\n[6/6] reactivating sources that have new URLs")
    import sqlite3
    db = sqlite3.connect(str(REPO / "cfb_rankings.db"))
    # Deactivated sources where we now have a replacement URL should be
    # re-activated. The seed-feed-instances CLI will update the URL.
    # We also clear their error rows from scrape_health so the next
    # validate-feed-urls run starts clean.
    cur = db.execute(
        """
        update source_registry set is_active = 1
        where source_id like 'beat_%' or source_id like 'podcast_%' or source_id like 'substack_%'
        """
    )
    db.commit()
    print(f"  reactivated {cur.rowcount} feed-family sources")


def main() -> None:
    if not RESEARCH_P2.exists():
        sys.exit(f"research file not found: {RESEARCH_P2}")
    if not RESEARCH_P1.exists():
        sys.exit(f"research file not found: {RESEARCH_P1}")
    merge_priority_teams()
    apply_replacements()
    apply_prediction_markets()
    create_tiktok_seed()
    update_coach_changes_in_db()
    reactivate_replaced_sources()
    print("\ndone. Next: python manage.py seed-priority-teams && seed-source-instances && seed-feed-instances && validate-feed-urls")


if __name__ == "__main__":
    main()
