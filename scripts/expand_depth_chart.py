"""One-shot script: appends non-QB depth chart entries to data/depth_chart_2026.csv.

All player_ids verified RETURNING_2026 in player_current_status_cache.
Run from repo root: python scripts/expand_depth_chart.py
"""
from pathlib import Path

CSV = Path("data/depth_chart_2026.csv")

ADDITIONS = """\
# TE depth chart — top returning tight ends at major programs
# Sources: On3 spring depth charts Phil Steele 2026 team chapters.
27768,Jackson Carver,TE,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Miami TE1 — Mackey Award candidate
24925,Henry Delp,TE,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Georgia TE1 — returning pass-catcher for Bulldogs
26639,Johnny Pascuzzi,TE,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Iowa TE1 — classic Iowa TE role tight-window target
29033,Zack Marshall,TE,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Michigan TE1 — lead blocker and seam threat
28448,Jay Lindsey,TE,1,returning_starter,projected,manual_editorial,,2026-05-27,Alabama TE1 — move-TE in Alabama RPO system
32629,Justin Fisher,TE,1,returning_starter,projected,manual_editorial,,2026-05-27,Notre Dame TE1 — primary red-zone target for Irish
# DE/EDGE depth chart — top returning edge rushers at power programs
32533,Jaylen Harvey,DE,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Penn State DE1 — Bednarik/Nagurski candidate
32383,Jordan Mayer,DE,1,returning_starter,projected,manual_editorial,,2026-05-27,Penn State DE2 — versatile edge on Lions rotation
33391,Dominic Kirks,DE,1,returning_starter,projected,manual_editorial,,2026-05-27,Ohio State DE — penetrating 3-tech pass-rusher
27059,Darien Mayo,DE,1,returning_starter,projected,manual_editorial,,2026-05-27,Clemson DE — active edge from Clemson defense
27016,Zaire Patterson,DE,1,returning_starter,projected,manual_editorial,,2026-05-27,Clemson DE — rotational edge with sack potential
4521,Lebbeus Overton,DE,1,returning_starter,projected,manual_editorial,,2026-05-27,Alabama DL — versatile rusher off the edge for Tide
13102,Colin Simmons,DE,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Texas EDGE — top returning pass rusher in Big 12
# DT/DL depth chart — top returning interior defensive linemen
33401,Xavier Gilliam,DT,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Penn State DT — interior anchor Outland/Bednarik candidate
# LB depth chart — top returning linebackers
26138,Dasan McCullough,LB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Oklahoma LB1 — Butkus candidate top returning LB Big 12
32566,Payton Pierce,LB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Ohio State LB — key piece of Buckeyes defense
31773,Kahanu Kia,LB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Notre Dame LB — high-motor hybrid edge/off-ball
28406,Jeremiah Alexander,LB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Alabama LB — top edge-setting linebacker in SEC
29043,Jack MacKinnon,LB,1,returning_starter,projected,manual_editorial,,2026-05-27,Michigan LB — key returning piece of Wolverines defense
29604,Xavier Atkins,LB,1,returning_starter,projected,manual_editorial,,2026-05-27,LSU LB — fast-flowing inside linebacker
13977,Whit Weeks,LB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,LSU LB — Butkus preseason watch
# CB/DB depth chart — top returning cornerbacks and safeties
27706,Cormani McClain,CB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Florida CB1 — elite cover corner Thorpe candidate
3720,Gabe Powers,CB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Ohio State DB — Thorpe/Hornung candidate safety-LB hybrid
29639,Craig Walton Jr.,CB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,LSU CB1 — shutdown corner Thorpe watch
29628,Michael Turner Jr.,CB,1,returning_starter,confirmed,manual_editorial,,2026-05-27,LSU CB2 — press-man specialist high NFL upside
27039,Kylen Webb,S,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Clemson S — ball-hawk safety leads Tigers secondary
28412,Jahlil Hurley,CB,1,returning_starter,projected,manual_editorial,,2026-05-27,Alabama CB — lockdown corner returning to Tide
# OL depth chart — top returning offensive linemen
28408,Elijah Pritchett,OL,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Alabama LT — dominant tackle Outland Trophy candidate
27015,Tristan Leigh,OL,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Clemson LT — franchise-caliber returning starter
32342,Austin Siereveld,OL,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Ohio State OG — elite interior mauler
24874,Drew Bobo,OL,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Georgia C/OG — versatile interior lineman for Bulldogs
# K depth chart — top returning kickers
13306,Peyton Woodring,K,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Georgia K — elite accuracy 50-plus yard range
4663,Conor Talty,K,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Alabama K — returning starter with clutch-game resume
12365,Drew Stevens,K,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Iowa K — Hawkeyes workhorse kicker
# P depth chart — top returning punters
13305,Brett Thorson,P,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Georgia P — elite directional punter Ray Guy candidate
12199,James Rendell,P,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Notre Dame P — high-hang-time punter top 5 nationally
3840,Joe McGuire,P,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Ohio State P — pin-deep specialist high gross average
"""

current = CSV.read_text(encoding="utf-8")
if current.endswith("\n"):
    CSV.write_text(current + ADDITIONS, encoding="utf-8")
else:
    CSV.write_text(current + "\n" + ADDITIONS, encoding="utf-8")

print(f"Appended {ADDITIONS.count(chr(10))} lines to {CSV}")
