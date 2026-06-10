"""Build the priority_teams seed by matching the 138-team Reddit census to DB team_ids.

Report-only by default (prints match table + unmatched). Pass --write to emit
data/seeds/team_sources_seed.csv. Never touches the DB.

Match strategy: normalize(census team name) against normalize(canonical_name) and
slug for every team, preferring FBS-flagged teams; a hand alias map fixes the
known mismatches. Auto-generates google_news_query; derives reddit_mode +
reddit_flair_filter from the census activity notes.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from cfb_rankings.config import AppConfig
from cfb_rankings.db import Database

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "data" / "seeds" / "reddit_team_subs_census_2026-06.json"
OUT = ROOT / "data" / "seeds" / "team_sources_seed.csv"

# census name -> DB slug, only where normalized matching fails
ALIASES = {
    "miami": "miami",            # Miami FL (not miami-oh)
    "miami (fl)": "miami",
    "miami fl": "miami",
    "ole miss": "ole-miss",
    "usc": "usc",
    "ucf": "ucf",
    "byu": "byu",
    "tcu": "tcu",
    "smu": "smu",
    "lsu": "lsu",
    "nc state": "nc-state",
    "north carolina state": "nc-state",
    "san jose state": "san-jos-state",
    "san jose st": "san-jos-state",
    "hawaii": "hawai-i",
    "hawai'i": "hawai-i",
    "texas a&m": "texas-a-m",
    "texas a&m": "texas-a-m",
    "app state": "app-state",
    "appalachian state": "app-state",
    "louisiana": "louisiana",
    "ul monroe": "ul-monroe",
    "louisiana monroe": "ul-monroe",
    "massachusetts": "massachusetts",
    "umass": "massachusetts",
    "connecticut": "uconn",
    "uconn": "uconn",
    "florida international": "florida-international",
    "fiu": "florida-international",
    "florida atlantic": "florida-atlantic",
    "fau": "florida-atlantic",
    "middle tennessee": "middle-tennessee",
    "western kentucky": "western-kentucky",
    "western michigan": "western-michigan",
    "central michigan": "central-michigan",
    "eastern michigan": "eastern-michigan",
    "northern illinois": "northern-illinois",
    "miami (oh)": "miami-oh",
    "miami oh": "miami-oh",
    "miami ohio": "miami-oh",
    "sam houston": "sam-houston",
    "sam houston state": "sam-houston",
    "jacksonville state": "jacksonville-state",
    "kennesaw state": "kennesaw-state",
    "james madison": "james-madison",
    "coastal carolina": "coastal-carolina",
    "georgia southern": "georgia-southern",
    "georgia state": "georgia-state",
    "south alabama": "south-alabama",
    "south florida": "south-florida",
    "southern miss": "southern-miss",
    "southern mississippi": "southern-miss",
    "new mexico state": "new-mexico-state",
    "new mexico": "new-mexico",
    "old dominion": "old-dominion",
    "east carolina": "east-carolina",
    "north texas": "north-texas",
    "texas state": "texas-state",
    "boise state": "boise-state",
    "fresno state": "fresno-state",
    "san diego state": "san-diego-state",
    "colorado state": "colorado-state",
    "utah state": "utah-state",
    "washington state": "washington-state",
    "oregon state": "oregon-state",
    "arizona state": "arizona-state",
    "iowa state": "iowa-state",
    "kansas state": "kansas-state",
    "oklahoma state": "oklahoma-state",
    "mississippi state": "mississippi-state",
    "michigan state": "michigan-state",
    "penn state": "penn-state",
    "ohio state": "ohio-state",
    "florida state": "florida-state",
    "arkansas state": "arkansas-state",
    "ball state": "ball-state",
    "kent state": "kent-state",
    "boston college": "boston-college",
    "georgia tech": "georgia-tech",
    "virginia tech": "virginia-tech",
    "texas tech": "texas-tech",
    "louisiana tech": "louisiana-tech",
    "wake forest": "wake-forest",
    "notre dame": "notre-dame",
    "west virginia": "west-virginia",
    "air force": "air-force",
    "north dakota state": "north-dakota-state",
    "ndsu": "north-dakota-state",
    "sacramento state": "sacramento-state",
    "sac state": "sacramento-state",
    "delaware": "delaware",
    "missouri state": "missouri-state",
}


# Tier 1 = the ~22 narrative leaders that drive ~90% of June argument surface
# (master plan §3). Tier 2 = rest of P4 + Notre Dame + big G6. Tier 3 = long tail.
TIER1_SLUGS = {
    "miami", "indiana", "georgia", "notre-dame", "texas", "oregon", "ohio-state",
    "lsu", "michigan", "penn-state", "alabama", "usc", "ole-miss", "auburn",
    "texas-tech", "florida-state", "nebraska", "north-carolina", "tennessee",
    "texas-a-m", "wisconsin", "duke",
}
P4_CONFERENCES = {"SEC", "Big Ten", "Big 12", "ACC"}
BIG_G6_SLUGS = {  # high-conversation Group of 6 / independents worth Tier 2
    "boise-state", "memphis", "tulane", "smu", "south-florida", "byu",
    "app-state", "james-madison", "liberty", "unlv",
}


def norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("&", " and ").replace("'", "").replace(".", "")
    s = re.sub(r"\bst\b", "state", s)         # "san jose st" -> "san jose state"
    s = re.sub(r"\buniv(ersity)?\b", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def derive_reddit(sub: str, activity: str) -> tuple[str | None, str, str | None]:
    """Return (clean_sub, reddit_mode, reddit_flair_filter)."""
    sub = (sub or "").strip()
    sub = re.sub(r"^/?r/", "", sub)  # strip r/ prefix
    act = (activity or "").lower()
    if not sub or "no football sub" in act and "school" not in act:
        # fall through; school-sub note still gives us a sub to use
        pass
    mode = "dedicated"
    flair = None
    if "school sub" in act or "school+sports" in act or "school sub;" in act or "school+sports hybrid" in act:
        mode = "school_flair"
        flair = "Sports,Athletics,Football,Recruiting"
    if act.startswith("dead") or "dead/restricted" in act or "doesn't exist" in act:
        # keep the sub but flag low priority; not a hard skip unless empty
        mode = "school_flair" if ("school" in act) else mode
    # Any school_flair sub MUST carry a flair filter, or we re-import the general
    # university chatter (the exact noise this expansion removes).
    if mode == "school_flair" and not flair:
        flair = "Sports,Athletics,Football,Recruiting"
    return (sub or None), mode, flair


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="emit the CSV (default: report only)")
    args = ap.parse_args()

    db = Database(AppConfig.from_env().database_url)
    census = json.loads(CENSUS.read_text(encoding="utf-8"))

    teams = db.query_all(
        """
        select t.team_id, t.slug, t.canonical_name,
               (case when t.level_code='FBS' or lower(coalesce(t.cfbd_classification,''))='fbs'
                     then 1 else 0 end) as fbs,
               c.conference_name as conference
        from teams t
        left join team_seasons ts on ts.team_id = t.team_id and ts.season_year = 2025
        left join conferences c on c.conference_id = ts.conference_id
        """
    )

    def tier_for(slug: str, conference: str | None) -> int:
        if slug in TIER1_SLUGS:
            return 1
        if (conference or "") in P4_CONFERENCES or slug == "notre-dame" or slug in BIG_G6_SLUGS:
            return 2
        return 3
    # Build lookup: normalized name/slug -> list of (fbs, team_id, slug, name)
    by_norm: dict[str, list[dict]] = {}
    by_slug: dict[str, dict] = {}
    for t in teams:
        by_slug[t["slug"]] = t
        for key in {norm(t["canonical_name"]), norm(t["slug"].replace("-", " "))}:
            by_norm.setdefault(key, []).append(t)

    def resolve(name: str):
        n = norm(name)
        if n in ALIASES and ALIASES[n] in by_slug:
            return by_slug[ALIASES[n]]
        # alias by slug value
        cands = by_norm.get(n, [])
        fbs = [c for c in cands if c["fbs"]]
        if len(fbs) == 1:
            return fbs[0]
        if len(cands) == 1:
            return cands[0]
        if fbs:
            return fbs[0]  # prefer FBS on ambiguity
        return None

    rows = []
    unmatched = []
    for i, entry in enumerate(census):
        name = entry.get("team", "")
        t = resolve(name)
        if not t:
            unmatched.append(name)
            continue
        sub, mode, flair = derive_reddit(entry.get("subreddit", ""), entry.get("activity", ""))
        rows.append({
            "team_id": t["team_id"],
            "slug": t["slug"],
            "canonical_name": t["canonical_name"],
            "conference_2025": t.get("conference") or "",
            "collection_tier": tier_for(t["slug"], t.get("conference")),
            "reddit_team_sub": sub or "",
            "reddit_mode": mode,
            "reddit_flair_filter": flair or "",
            "google_news_query": f'{t["canonical_name"]} football',
            "census_name": name,
            "census_activity": entry.get("activity", ""),
        })

    print(f"census teams: {len(census)}  matched: {len(rows)}  unmatched: {len(unmatched)}")
    if unmatched:
        print("UNMATCHED (need alias):")
        for u in unmatched:
            print(f"   - {u!r}  (norm={norm(u)!r})")
    # duplicate team_id check
    seen = {}
    for r in rows:
        seen.setdefault(r["team_id"], []).append(r["census_name"])
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    if dupes:
        print("DUPLICATE team_id mappings (collision!):")
        for k, v in dupes.items():
            print(f"   team_id={k}: {v}")

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        cols = ["team_id", "slug", "canonical_name", "conference_2025", "collection_tier",
                "reddit_team_sub", "reddit_mode", "reddit_flair_filter",
                "google_news_query", "census_name", "census_activity"]
        with OUT.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
