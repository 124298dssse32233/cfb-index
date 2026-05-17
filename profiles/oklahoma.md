---
team_id: 280
program_name: Oklahoma
display_name: Oklahoma
program_slug: oklahoma
program_tier: 1
voice_register: crown-program-in-transition
tonal_template: crown-program-in-transition
identity_phrase: "Oklahoma is a crown program crossing leagues and still carrying the crown."
mantra: "Boomer Sooner."
authored_by: opus-editorial
editorial_review_status: draft
model_version: team-pages v1.0

accent_hex: "#841617"
accent_hex_secondary: "#FDF9D8"
gradient_hex_pair: "#841617,#fdf9d8"

vocab:
  signoff: "Boomer Sooner."
  greeting: "BOOMER"
  hashtags: ["#BoomerSooner", "#OUDNA", "#GoSooners"]
  selfname: "the Sooners"
  stadium_short: "Owen Field"

# Added 2026-05-17 for v2-addendum Sprint v5-8.5 (Rituals + Cultural Identity)
rituals:
  - name: "Sooner Schooner"
    started_year: 1964
    when: "After every Oklahoma score"
    description: "The covered wagon, pulled by two white ponies named Boomer and Sooner, races across the field after every score. The schooner is a Conestoga wagon — a direct reference to the 1889 Land Rush 'Sooners' who entered Oklahoma Territory before the legal start. The 1985 Orange Bowl tipping incident is part of the lore."
    image_asset: "rituals/sooner-schooner.svg"
    cultural_significance: "high"
  - name: "Boomer Sooner (fight song)"
    started_year: 1905
    when: "After every score, before every kickoff, constantly"
    description: "Written by Arthur Alden in 1905 — set to the tune of Yale's 'Boola Boola' (which OU borrowed and arguably improved). The most-played college fight song per minute of game time. The 'Oklahoma! Oklahoma! Oklahoma! Sooners!' breakdown is the signature; visiting fans learn it by osmosis."
    image_asset: "rituals/boomer-sooner.svg"
    cultural_significance: "high"
  - name: "The Crimson Walk (Sooner Walk)"
    started_year: 1990s
    when: "Two hours before kickoff"
    description: "Players walk from Switzer Center through fans into Owen Field. Less codified than Auburn's or Michigan's equivalents but central to the gameday rhythm. Bob Stoops formalized it; Lincoln Riley and Brent Venables continued. The walk passes the Heisman statues — every Oklahoma Heisman winner cast in bronze along the route."
    image_asset: "rituals/sooner-walk.svg"
    cultural_significance: "medium"
  - name: "Pride of Oklahoma (band)"
    started_year: 1904
    when: "Halftime, every home game"
    description: "The marching band's halftime performance — distinguished by the 'Boomer Sooner' fan-tradition culminating in the script 'OKLAHOMA' formation. Less photogenic than Script Ohio but more athletic — the band's fast tempo through OU formations is its signature. Drumline solos are a fixture."
    image_asset: "rituals/pride-of-oklahoma.svg"
    cultural_significance: "medium"
  - name: "Red River Rivalry Week"
    started_year: 1900
    when: "Second Saturday in October, at the Cotton Bowl in Dallas"
    description: "The neutral-site game vs Texas during the State Fair of Texas. The stadium is split exactly in half — crimson on one sideline, burnt orange on the other. The Golden Hat trophy goes to the winner. Calendar-marker rivalry that organizes the OU season the way The Game organizes Ohio State's."
    image_asset: "rituals/red-river-rivalry.svg"
    cultural_significance: "high"

cultural_anchors:
  one_sentence: "Oklahoma is the program built on Land Rush mythology and the only American college team where the mascot is two white ponies pulling a Conestoga wagon at 25mph."
  if_team_didnt_exist_cfb_would_lose: "The Sooner Schooner. The Red River. The Big Eight / Big 12 / SEC migration history as a case study in conference realignment. The Switzer-era wishbone offense as a tactical fossil."
  fan_archetype_dominant: "Manifest-Destiny-Believer"
  outsider_archetype_dominant: "Late-to-the-SEC"

visual_identity_anchors:
  helmet_stripe_pattern: "interlocking-OU-on-crimson-no-stripe"
  hero_imagery_default: "halftone-engraving-portrait-with-schooner"
  signature_color_combination: "crimson-cream"

data_emphasis:
  primary: "red_river_rivalry_results"
  secondary: "all_time_conference_titles_count"
  ignore: "early_sec_transition_anomalies"
  hero_finding_preferred_axis: "national_championships_count_seven"

mascot_voice:
  awaiting_signal: "The Sooner Schooner is in the stable. Signal returns when the horses hear it."
  empty_state: "Owen Field is quiet. Seven titles do not insulate a program from the present."
  post_win: "Boomer Sooner. The crown is still the crown."
  post_loss: "Boomer Sooner. The process adjusts; the crown does not."

era_name_overrides:
  "1895-1907": "The Territory Era"
  "1947-1963": "The Bud Wilkinson Dynasty"
  "1973-1988": "The Barry Switzer Era"
  "1999-2016": "The Bob Stoops Era"
  "2017-2021": "The Riley Window"
  "2022-": "The Venables Reinvention"

coaching_regimes:
  - coach: "Stoops"
    start_year: 2014
    end_year: 2016
  - coach: "Riley"
    start_year: 2017
    end_year: 2021
  - coach: "Venables"
    start_year: 2022
    end_year: null

era_annotations:
  - x_year: 2015
    y_source: "ap"
    label: "CFP · Baker's first full year"
    color: "amber"
  - x_year: 2017
    y_source: "ap"
    label: "Baker's Heisman"
    color: "gold"
  - x_year: 2021
    y_source: "mood"
    label: "Riley departs for USC"
    color: "red"
  - x_year: 2024
    y_source: "mood"
    label: "First SEC season"
    color: "navy"

never_use:
  - Oklahoma as generic Big-12 framing (they're SEC as of 2024)
  - Bedlam as a still-annual rivalry framing (the series is on hiatus post-realignment)
  - Barry Switzer as a museum artifact (he is active in the program's public life)
  - scrappy
  - Cinderella
  - plucky
  - crown as a boast (it is a structural fact, not a performance)
  - It ain't easy to be from Oklahoma as filler (not the voice)

always_surface:
  - 7 national championships (1950, 1955, 1956, 1974, 1975, 1985, 2000)
  - 7 Heisman winners (most of any program tied with Notre Dame / Ohio State)
  - SEC membership as of July 2024 (move announced 2021)
  - Gaylord Family Oklahoma Memorial Stadium capacity 83,489
  - The Venables era (since December 2021) and the identity-reinvention bet
  - The Sooner Schooner pregame tradition

stock_phrases:
  - "Boomer. Sooner."
  - "OU DNA."
  - "Oklahoma's floor is what other programs call a ceiling."

rivalries:
  - tier: 1
    opponent: "Texas"
    opponent_slug: "texas"
    trophy: "Golden Hat"
    name: "Red River Rivalry"
    accent_color: "red"
    note: "Annual in Dallas at the Cotton Bowl (State Fair of Texas); the rivalry the program's identity is measured against."
  - tier: 2
    opponent: "Oklahoma State"
    opponent_slug: "oklahoma-state"
    trophy: "Bedlam"
    name: "Bedlam Series"
    note: "In-state rivalry; on hiatus after conference-realignment-driven scheduling; will return only when both schools can fit it."
  - tier: 2
    opponent: "Nebraska"
    opponent_slug: "nebraska"
    name: "Oklahoma – Nebraska"
    note: "Historical Big-8 rivalry; now occasional non-conference."
  - tier: 3
    opponent: "Missouri"
    opponent_slug: "missouri"
    name: "Oklahoma – Missouri"
    note: "SEC crossover post-2024."

aspiration_ladder:
  - rung: "Bowl win"
    unlocked_by: "6 wins and a bowl invite."
    context: "Baseline — below this is program-crisis."
  - rung: "Win the Red River Rivalry"
    unlocked_by: "Beat Texas in Dallas."
    context: "Annual identity test regardless of SEC standings."
  - rung: "SEC Championship Game"
    unlocked_by: "Win the SEC schedule path."
    context: "Target rung for the mature Venables years."
  - rung: "SEC Championship"
    unlocked_by: "Win the conference title game."
    context: "First SEC title would be historic; first conference title since 2020 Big-12."
  - rung: "CFP Quarterfinal / Semifinal"
    unlocked_by: "Top-12 placement + bracket wins."
    context: "The specific rung the Riley years touched but did not pass."
  - rung: "National Championship"
    unlocked_by: "Win it."
    context: "Title #8 — first since 2000."

heritage:
  founded: 1895
  national_titles: 7
  conference_titles: 50
  heismans: 7
  cfp_appearances: 4
  bowl_appearances: 57
  current_conference: "SEC (as of 2024)"
  stadium: "Gaylord Family Oklahoma Memorial Stadium (83,489)"
  legendary_coach: "Bud Wilkinson"
  wiki_team_page: "https://en.wikipedia.org/wiki/Oklahoma_Sooners_football"
---

# Identity and heritage

Oklahoma football was founded in 1895 and has claimed seven national championships (1950, 1955, 1956, 1974, 1975, 1985, 2000). Seven Heisman Trophy winners — Billy Vessels (1952), Steve Owens (1969), Billy Sims (1978), Jason White (2003), Sam Bradford (2008), Baker Mayfield (2017), Kyler Murray (2018) — tied with Notre Dame and Ohio State for most of any program. Fifty conference championships claimed across Big-6, Big-7, Big-8, Big-12.

Gaylord Family Oklahoma Memorial Stadium (83,489) — traditionally called "Owen Field" — has been the program's home since 1923. The stadium's south-end zone expansion (2015) and the north-end zone rebuild (2020) have kept the capacity and the premium-seating infrastructure aligned with the program's tier.

As of July 2024, Oklahoma plays in the Southeastern Conference — a move announced in 2021 alongside Texas and executed on the 2024 calendar flip. The institutional shift is structural: Oklahoma is in the SEC now, not a Big-12 program with a plan to move. The 2024 season was the first SEC season; the 2025 season is the first in which the roster was built for SEC competition.

# Coaching lineage

Bennie Owen (1905–1926) built the pre-title foundation. Bud Wilkinson (1947–1963) is the cornerstone: three national titles, a 47-game winning streak (still the longest in FBS history), and the defensive/offensive identity that produced "Boomer Sooner" as a cultural anchor. Barry Switzer (1973–1988) is the second cornerstone: three titles, the wishbone offense that redefined college football in the 1970s, and a program-to-coach identification as complete as any in the sport.

The 1990s were uneven between Switzer and Stoops. Bob Stoops (1999–2016) is the modern cornerstone: 190 wins, one national title (2000), 10 Big-12 championships, and a program that lived inside the top-10 for most of 18 years. Lincoln Riley (2017–2021) took over mid-career from Stoops and produced a Heisman factory (Mayfield 2017, Murray 2018, plus Jalen Hurts and Caleb Williams under his roster) before departing for USC in November 2021.

Brent Venables (since December 2021) is the current reinvention bet. Venables is Stoops's former defensive coordinator, returned to Norman as head coach. His three-year tenure has been uneven — the 2022 6-7 season was the program's first losing year since 1998 — but the 2023 rebound (10-3) and the 2024 SEC debut (6-7) have been uneven signal. The 2026 season is the practical measurement year.

# Notable players

Heismans: Vessels (1952), Owens (1969), Sims (1978), White (2003), Bradford (2008), Mayfield (2017), Murray (2018). Modern-era standouts: Adrian Peterson, DeMarco Murray, Sterling Shepard, Gerald McCoy, Ndamukong Suh (transferred out; not a Sooner), Mark Andrews, Brian Bosworth (historically), Roy Williams (DB era), Lee Roy Selmon. The NFL draft pipeline is a consistent top-10 producer nationally, with a concentration at QB (the Heisman factory years).

# Fans and culture

The fanbase is Oklahoma-wide with a concentration in the Oklahoma City / Norman / Tulsa corridor and significant Dallas-metroplex representation (Red River geography). The gameday culture runs: the Sooner Schooner (a covered wagon pulled by two horses, rolled onto the field after every Oklahoma score since 1964), the Oklahoma drill (a defensive rhythm that shares the program's name), "Boomer Sooner" as both the fight song and the universal greeting, and the Pride of Oklahoma marching band's halftime shows that are load-bearing cultural events.

The rivalry with Texas (Red River, in Dallas) is the schedule's gravitational center — and has been since long before either program joined the SEC. The rivalry with Oklahoma State (Bedlam) is on conference-realignment hiatus and the fanbase feels that loss.

# Voice and ethos

The voice is crown-program-in-transition: confident about the seven titles, practical about the Big-12-to-SEC move, aware of what Venables inherited, and unwilling to speak with the register of a mid-major. Oklahoma does not perform humility about its standing; it also does not pretend the 2022 6-7 season didn't happen. The register is closer to an institutional memo than a pep-rally speech.

Identity phrase: **"Oklahoma is a crown program crossing leagues and still carrying the crown."**

Mantra: **"Boomer Sooner."** Two words, always capitalized as proper-noun phrase. Fight song, chant, greeting, sign-off — it carries all those weights at once.

The never-use list protects against the Big-12 default framing (Oklahoma is SEC now), the Bedlam-annual framing (the series is on hiatus), and the "crown as boast" framing (it is a structural fact).

# Rivalries

Red River Rivalry (vs. Texas, since 1900) is the rivalry. Played in the Cotton Bowl (Fair Park, Dallas) during the State Fair of Texas, second Saturday of October. One of college football's most identifiable annual events — the stadium split in half by color, the burnt-orange and crimson vertical line, the fans entering through a common gate into a shared chaos. Now an SEC conference game as of 2024. The all-time ledger runs close.

Bedlam (vs. Oklahoma State, 1904–2023, then hiatus) is the in-state rivalry. The 2024 SEC move and Oklahoma State's Big-12 membership paused the annual game. The fanbase reads that pause as a cultural cost, not a gain. Return is contingent on scheduling realities.

Oklahoma–Nebraska is the historical Big-8 rivalry that still carries cultural weight even when not annual. 2021–2023 non-conference meetings are the modern touchpoint.

# Current context

Head coach: Brent Venables (since December 2021). Athletic director: Joe Castiglione (long-tenured; structurally institutional). NIL collective: "Crimson & Cream Collective" (established 2022). Facilities: the Everest Training Center (opened 2019) is the program's daily operational anchor; the Barry Switzer Center houses offices and player-support.

# Program narratives

The SEC transition is the single open narrative thread. Four specific questions: (1) does the Venables program's recruiting fit the SEC talent-pool battle; (2) does the 2026 schedule produce a year that validates the move; (3) can the offense reach the Riley-era ceiling under different scheme; (4) when does Bedlam come back. The 2024 SEC debut was a rough first-sentence answer to (1) and (2); (3) and (4) are still being written.

The Lincoln Riley departure (to USC, November 2021) is recent but not a wound — the program pivoted to Venables within weeks and the transition is the story, not the exit.

# Aspiration framework

Baseline: 9+ wins, competitive in every SEC game, beat Texas once every two years. Realistic ceiling: SEC Championship Game + CFP bid. Dream ceiling: SEC title + CFP semifinal. Historic ceiling: title #8.

# Chronicle tuning

For Oklahoma, anomalies read best relative to the Stoops-era altitude — a defensive EPA per play 1.5 SD below the Stoops baseline is a readable signal in a way it isn't for a program without that baseline. Echoes resonate when they connect forward to the Wilkinson dynasty or the Switzer era — the two program-defining epochs. Retroactive cards work when they tie Red River outcomes to season-long decisions.

# In-jokes and copypasta

"Boomer. Sooner." — the chant, the greeting, the sign-off. "OU DNA" — modern stock phrase, especially used during recruiting. "The Big Game" — how fans refer to Red River in conversation; no further context needed. "Horns down" — the gesture; originated as an anti-Texas taunt, now used across rival fanbases.

# Taboos and sensitivities

The 2021–2022 Lincoln Riley exit is recent but not a wound — the program's public voice has treated it as a transition, not a betrayal. Bob Stoops remains an institutional figure; copy should reflect that. The 2022 6-7 season is real fact; framing it as the program's identity is false. Barry Switzer is a living institutional presence on campus; "Switzer" as a punchline does not work. Bedlam's hiatus is a sensitive topic — the fanbase wants the rivalry back.
