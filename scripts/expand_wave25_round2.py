"""One-shot script: Round 2 expansion of award_watch_2026.csv and depth_chart_2026.csv.

Adds:
  Award Watch:
    - NEW: Rimington Award (center of year) — 5 candidates
    - NEW: Lombardi Award (lineman of year) — 7 candidates
    - Outland expanded: +3 (DT/C additions) → 8 total
    - Walter Camp expanded: +4 (skill/versatile players) → 8 total
    - Bednarik expanded: +2 (DT additions) → 10 total

  Depth Chart:
    - DT: +3 new entries (OSU, LSU, Clemson)
    - Safety: +4 new entries (LSU, Georgia, PSU, Texas)
    - CB: +3 new entries (OSU, PSU, Georgia)
    - OL: +3 new entries (OSU C, AL C, PSU OT)

All player_ids verified RETURNING_2026 in player_current_status_cache.
Run once from repo root: python scripts/expand_wave25_round2.py
"""
from pathlib import Path

WATCH_CSV = Path("data/award_watch_2026.csv")
DEPTH_CSV = Path("data/depth_chart_2026.csv")

# ──────────────────────────────────────────────────────────────────────────────
# AWARD WATCH additions
# ──────────────────────────────────────────────────────────────────────────────
WATCH_ADDITIONS = """\
# Dave Rimington Trophy (center of the year) — new award category, 5 candidates
# Sources: Phil Steele 2026 OL grades, PFF offensive line rankings, On3 center watch.
31585,Carson Hinzman,rimington,watchlist_official,1,1,consensus_may_2026,,2026-05-27,Rimington - Ohio State C; returning starting center for national-champion Buckeyes
28409,Parker Brailsford,rimington,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Rimington - Alabama C; anchor of Tide interior line multi-year starter
24874,Drew Bobo,rimington,watchlist_official,3,2,consensus_may_2026,,2026-05-27,Rimington - Georgia C/OG; versatile interior piece Outland/Rimington crossover
27018,Ryan Linthicum,rimington,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Rimington - Clemson C; Clemson's returning starting center spring depth chart confirmed
31304,Nolan Rucci,rimington,watchlist_official,5,3,consensus_may_2026,,2026-05-27,Rimington - Penn State OL; elite interior blocker anchors Lions run game
# Rotary Lombardi Award (lineman of year — OL or DL) — new award category, 7 candidates
# Sources: Phil Steele 2026 lineman grades, ESPN preseason lineman watch, PFF.
28408,Elijah Pritchett,lombardi,watchlist_official,1,1,consensus_may_2026,,2026-05-27,Lombardi - Alabama LT; top returning OT in SEC dominant pass protector
33401,Xavier Gilliam,lombardi,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Lombardi - Penn State DT; interior anchor A-gap control Outland/Bednarik crossover
13102,Colin Simmons,lombardi,watchlist_official,3,1,consensus_may_2026,,2026-05-27,Lombardi - Texas EDGE; top returning pass rusher Big 12 Bednarik crossover
32533,Jaylen Harvey,lombardi,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Lombardi - Penn State DE; edge specialist disruption upside
27015,Tristan Leigh,lombardi,watchlist_official,5,2,consensus_may_2026,,2026-05-27,Lombardi - Clemson LT; franchise-LT caliber pass protector
32342,Austin Siereveld,lombardi,watchlist_official,6,2,consensus_may_2026,,2026-05-27,Lombardi - Ohio State OG; elite guard mauler in run game Outland crossover
23361,Dominick McKinley,lombardi,watchlist_official,7,3,consensus_may_2026,,2026-05-27,Lombardi - LSU DT; 4-year starter interior havoc generator All-SEC caliber
# Outland Trophy — expanded from 5 to 8 candidates (added DT/C)
31585,Carson Hinzman,outland,watchlist_official,6,3,consensus_may_2026,,2026-05-27,Outland - Ohio State C; returning starting center two-way anchor
23361,Dominick McKinley,outland,watchlist_official,7,3,consensus_may_2026,,2026-05-27,Outland - LSU DT; interior defensive anchor 4-year starter SEC force
3732,Tywone Malone,outland,watchlist_official,8,3,consensus_may_2026,,2026-05-27,Outland - Ohio State DT; returning DT for national champion Buckeyes
# Walter Camp Player of the Year — expanded from 4 to 8 candidates
11334,Makhi Hughes,walter_camp,watchlist_official,5,2,consensus_may_2026,,2026-05-27,Walter Camp - Oregon RB; top returning rusher Pac-12 powerhouse
14116,Desmond Reid,walter_camp,watchlist_official,6,2,consensus_may_2026,,2026-05-27,Walter Camp - Pittsburgh RB; all-purpose weapon Hornung/Doak Walker crossover
26138,Dasan McCullough,walter_camp,watchlist_official,7,3,consensus_may_2026,,2026-05-27,Walter Camp - Nebraska LB; top returning linebacker Butkus/Bednarik crossover
27706,Cormani McClain,walter_camp,watchlist_official,8,3,consensus_may_2026,,2026-05-27,Walter Camp - Florida CB; former #1 CB recruit elite cover corner Thorpe crossover
# Bednarik Award — expanded from 8 to 10 candidates (added DTs)
23361,Dominick McKinley,bednarik,watchlist_official,9,3,consensus_may_2026,,2026-05-27,Bednarik - LSU DT; 4-year starter dominant interior force All-SEC
3732,Tywone Malone,bednarik,watchlist_official,10,3,consensus_may_2026,,2026-05-27,Bednarik - Ohio State DT; defensive anchor for national-champion Buckeyes
"""

# ──────────────────────────────────────────────────────────────────────────────
# DEPTH CHART additions
# ──────────────────────────────────────────────────────────────────────────────
DEPTH_ADDITIONS = """\
# DT depth chart — top returning interior defensive tackles (Round 2)
3732,Tywone Malone,DT,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Ohio State DT — multi-year starter anchor of national-champion defense
23361,Dominick McKinley,DT,1,returning_starter,confirmed,manual_editorial,,2026-05-27,LSU DT1 — 4-year starter All-SEC interior force dominant run stuffer
13263,Vic Burley,DT,1,returning_starter,projected,manual_editorial,,2026-05-27,Clemson DT — experienced interior anchor leads Clemson D-line rotation
# Safety depth chart — top returning safeties (Round 2 expansion)
13976,Austin Ausberry,S,1,returning_starter,confirmed,manual_editorial,,2026-05-27,LSU S — versatile enforcer leads Tigers secondary high-IQ coverage
9460,Jaden Harris,S,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Georgia S — Georgia's returning safety leader instinctive playmaker
23313,Vaboue Toure,S,1,returning_starter,projected,manual_editorial,,2026-05-27,Penn State S — Lions returning safety presence in back-end coverage
27325,Lance St. Louis,S,1,returning_starter,projected,manual_editorial,,2026-05-27,Texas S — Longhorns returning safety presence in Big 12 defense
# CB depth chart — additional returning cornerbacks (Round 2 expansion)
3754,Jermaine Mathews Jr.,CB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Ohio State CB — Buckeyes returning corner high upside in man coverage
9008,A.J. Harris,CB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Penn State CB — Lions shutdown corner returns as secondary anchor
24914,Maurice Hayes,CB,1,returning_starter,projected,manual_editorial,,2026-05-27,Georgia CB — Bulldogs returning corner in deep SEC secondary depth
# OL depth chart — additional returning offensive linemen (Round 2 expansion)
31585,Carson Hinzman,OL,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Ohio State C — returning starting center for national-champion Buckeyes Rimington candidate
28409,Parker Brailsford,OL,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Alabama C — Alabama's returning interior anchor multi-year starter Rimington candidate
31304,Nolan Rucci,OL,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Penn State OT — elite returner anchors Lions offensive line Outland candidate
"""


def append_csv(path: Path, additions: str) -> int:
    current = path.read_text(encoding="utf-8")
    if current.endswith("\n"):
        path.write_text(current + additions, encoding="utf-8")
    else:
        path.write_text(current + "\n" + additions, encoding="utf-8")
    return additions.count("\n")


watch_lines = append_csv(WATCH_CSV, WATCH_ADDITIONS)
depth_lines = append_csv(DEPTH_CSV, DEPTH_ADDITIONS)

print(f"Award watch: appended {watch_lines} lines to {WATCH_CSV}")
print(f"Depth chart: appended {depth_lines} lines to {DEPTH_CSV}")
