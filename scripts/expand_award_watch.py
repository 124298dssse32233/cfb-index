"""One-shot script: appends comprehensive defensive/special-teams award watch
entries to data/award_watch_2026.csv.

All player_ids are verified RETURNING_2026 in player_current_status_cache.
Run once from repo root: python scripts/expand_award_watch.py
"""
from pathlib import Path

CSV = Path("data/award_watch_2026.csv")

ADDITIONS = """\
# Butkus Award (linebacker of the year) — preseason 2026 top candidates
# Expanded from 1 to 9 candidates. Sources: Phil Steele 2026, On3 LB watch, 247Sports.
26138,Dasan McCullough,butkus,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Butkus - Oklahoma LB; top returning rush linebacker in Big 12
32566,Payton Pierce,butkus,watchlist_official,3,1,consensus_may_2026,,2026-05-27,Butkus - Ohio State LB; 2025 Big Ten Defensive Player candidate
31773,Kahanu Kia,butkus,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Butkus - Notre Dame LB; high-motor edge/off-ball hybrid
28406,Jeremiah Alexander,butkus,watchlist_official,5,2,consensus_may_2026,,2026-05-27,Butkus - Alabama LB; top edge-setting linebacker in SEC
29043,Jack MacKinnon,butkus,watchlist_official,6,2,consensus_may_2026,,2026-05-27,Butkus - Michigan LB; key returning piece of Wolverines defense
29604,Xavier Atkins,butkus,watchlist_official,7,3,consensus_may_2026,,2026-05-27,Butkus - LSU LB; fast-flowing inside linebacker
29608,Davhon Keys,butkus,watchlist_official,8,3,consensus_may_2026,,2026-05-27,Butkus - LSU LB; playmaking sideline-to-sideline
26139,Emeka Megwa,butkus,watchlist_official,9,3,consensus_may_2026,,2026-05-27,Butkus - Oklahoma LB; blitz package specialist
# Jim Thorpe Award (defensive back of the year) — preseason 2026 top candidates
# 0 to 10 candidates. Sources: Phil Steele 2026, On3 DB Watch, ESPN preseason.
3720,Gabe Powers,thorpe,watchlist_official,1,1,consensus_may_2026,,2026-05-27,Thorpe - Ohio State DB; top returning safety/LB hybrid in B1G
27706,Cormani McClain,thorpe,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Thorpe - Florida CB; former No. 1 CB recruit elite cover corner
29639,Craig Walton Jr.,thorpe,watchlist_official,3,1,consensus_may_2026,,2026-05-27,Thorpe - LSU CB; shutdown corner SEC All-Defensive candidate
29628,Michael Turner Jr.,thorpe,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Thorpe - LSU CB; press-man specialist high NFL upside
27039,Kylen Webb,thorpe,watchlist_official,5,2,consensus_may_2026,,2026-05-27,Thorpe - Clemson S; ball-hawk safety leads Tigers secondary
29007,Mason Curtis,thorpe,watchlist_official,6,2,consensus_may_2026,,2026-05-27,Thorpe - Michigan DB; versatile safety/nickel hybrid
28412,Jahlil Hurley,thorpe,watchlist_official,7,2,consensus_may_2026,,2026-05-27,Thorpe - Alabama DB; lockdown corner returning to Tide
28445,Dre Kirkpatrick Jr.,thorpe,watchlist_official,8,3,consensus_may_2026,,2026-05-27,Thorpe - Alabama DB; legacy name emerging cornerback
26150,Makari Vickers,thorpe,watchlist_official,9,3,consensus_may_2026,,2026-05-27,Thorpe - Oklahoma CB; splash-play cornerback in Sooners scheme
28912,Aaron Flowers,thorpe,watchlist_official,10,3,consensus_may_2026,,2026-05-27,Thorpe - Oregon DB; versatile safety in Oregon defense
# Bednarik Award (defensive player of the year) — expanded
# 1 to 8 candidates. Colin Simmons (Texas) already entered.
32533,Jaylen Harvey,bednarik,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Bednarik - Penn State DE; off-ball pressure specialist
32383,Jordan Mayer,bednarik,watchlist_official,3,1,consensus_may_2026,,2026-05-27,Bednarik - Penn State DE; versatile edge player with disruption upside
33391,Dominic Kirks,bednarik,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Bednarik - Ohio State DE; elite motor penetrating 3-tech
33401,Xavier Gilliam,bednarik,watchlist_official,5,2,consensus_may_2026,,2026-05-27,Bednarik - Penn State DT; interior anchor with pass-rush ability
27059,Darien Mayo,bednarik,watchlist_official,6,2,consensus_may_2026,,2026-05-27,Bednarik - Clemson DE; active edge 2025 postseason performer
4521,Lebbeus Overton,bednarik,watchlist_official,7,3,consensus_may_2026,,2026-05-27,Bednarik - Alabama DL; versatile rusher off the edge
26138,Dasan McCullough,bednarik,watchlist_official,8,3,consensus_may_2026,,2026-05-27,Bednarik - Oklahoma LB; all-conference rush linebacker
# Nagurski Award (defensive player of the year) — expanded
# 1 to 6 candidates. Colin Simmons already entered.
32533,Jaylen Harvey,nagurski,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Nagurski - Penn State DE
32383,Jordan Mayer,nagurski,watchlist_official,3,2,consensus_may_2026,,2026-05-27,Nagurski - Penn State DE
33401,Xavier Gilliam,nagurski,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Nagurski - Penn State DT interior havoc player
4521,Lebbeus Overton,nagurski,watchlist_official,5,3,consensus_may_2026,,2026-05-27,Nagurski - Alabama DL
26138,Dasan McCullough,nagurski,watchlist_official,6,3,consensus_may_2026,,2026-05-27,Nagurski - Oklahoma LB
# Mackey Award (tight end of the year) — new award category 0 to 5 candidates
# Sources: 247Sports TE watch May 2026 On3 TE rankings.
27768,Jackson Carver,mackey,watchlist_official,1,1,consensus_may_2026,,2026-05-27,Mackey - Miami TE; top returning TE in ACC seam threat
24925,Henry Delp,mackey,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Mackey - Georgia TE; featured receiving TE returning to Bulldogs
26639,Johnny Pascuzzi,mackey,watchlist_official,3,2,consensus_may_2026,,2026-05-27,Mackey - Iowa TE; classic Iowa TE mold tight-window catcher
29033,Zack Marshall,mackey,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Mackey - Michigan TE; pro-style blocker with receiving upside
28448,Jay Lindsey,mackey,watchlist_official,5,3,consensus_may_2026,,2026-05-27,Mackey - Alabama TE; versatile move-TE in Alabama RPO scheme
# Ray Guy Award (punter of the year) — new award category 0 to 4 candidates
# Sources: Kohl Kicking preseason P rankings Phil Steele punter grades.
13305,Brett Thorson,ray_guy,watchlist_official,1,1,consensus_may_2026,,2026-05-27,Ray Guy - Georgia P; elite directional punter field-position weapon
12199,James Rendell,ray_guy,watchlist_official,2,2,consensus_may_2026,,2026-05-27,Ray Guy - Notre Dame P; high-hang-time punter top 5 nationally
3840,Joe McGuire,ray_guy,watchlist_official,3,2,consensus_may_2026,,2026-05-27,Ray Guy - Ohio State P; pin-deep specialist high gross average
11808,James Ferguson-Reynolds,ray_guy,watchlist_official,4,3,consensus_may_2026,,2026-05-27,Ray Guy - Boise State P; Mountain West top punter 2024
# Lou Groza Award (placekicker) — expanded from 1 to 5 candidates
# Note: Will Stone (15903) is TRANSFERRED will be pruned by clean_watch_csvs.py
13306,Peyton Woodring,lou_groza,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Groza - Georgia K; elite accuracy 50-plus yard range
4663,Conor Talty,lou_groza,watchlist_official,3,2,consensus_may_2026,,2026-05-27,Groza - Alabama K; returning starter clutch-game track record
12365,Drew Stevens,lou_groza,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Groza - Iowa K; Hawkeyes workhorse kicker
23315,Ryan Barker,lou_groza,watchlist_official,5,3,consensus_may_2026,,2026-05-27,Groza - Penn State K; accurate medium-range specialist
# Outland Trophy (interior lineman of year) — new award category 0 to 5 candidates
# Covers OL (OT/OG/C) and interior DL (DT). Sources: Phil Steele PFF.
28408,Elijah Pritchett,outland,watchlist_official,1,1,consensus_may_2026,,2026-05-27,Outland - Alabama OL; dominant LT top returning tackle in SEC
33401,Xavier Gilliam,outland,watchlist_official,2,1,consensus_may_2026,,2026-05-27,Outland - Penn State DT; interior anchor with A-gap control
32342,Austin Siereveld,outland,watchlist_official,3,2,consensus_may_2026,,2026-05-27,Outland - Ohio State OL; elite guard prospect mauler in run game
27015,Tristan Leigh,outland,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Outland - Clemson OL; franchise-LT caliber returning starter
24874,Drew Bobo,outland,watchlist_official,5,3,consensus_may_2026,,2026-05-27,Outland - Georgia OL; versatile interior lineman
# Walter Camp Player of the Year — expanded from 2 to 6 candidates
8280,Lanorris Sellers,walter_camp,watchlist_official,3,2,consensus_may_2026,,2026-05-27,Walter Camp - South Carolina QB; dual threat with Heisman upside
3830,Jeremiah Smith,walter_camp,watchlist_official,4,2,consensus_may_2026,,2026-05-27,Walter Camp - Ohio State WR; non-QB on preseason list
13102,Colin Simmons,walter_camp,watchlist_official,5,3,consensus_may_2026,,2026-05-27,Walter Camp - Texas EDGE; top returning pass rusher in Big 12
# Hornung Award (versatility) — expanded from 2 to 4 candidates
3830,Jeremiah Smith,hornung,watchlist_official,3,2,consensus_may_2026,,2026-05-27,Hornung - Ohio State WR; reverses screens short-yardage impact
3720,Gabe Powers,hornung,watchlist_official,4,3,consensus_may_2026,,2026-05-27,Hornung - Ohio State DB; box safety/LB hybrid rare versatility
"""

current = CSV.read_text(encoding="utf-8")
if current.endswith("\n"):
    CSV.write_text(current + ADDITIONS, encoding="utf-8")
else:
    CSV.write_text(current + "\n" + ADDITIONS, encoding="utf-8")

print(f"Appended {ADDITIONS.count(chr(10))} lines to {CSV}")
