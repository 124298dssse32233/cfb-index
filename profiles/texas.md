---
team_id: 170
program_name: Texas
display_name: Texas
program_slug: texas
program_tier: 1
voice_register: confident-texan
tonal_template: confident-texan
identity_phrase: "Texas is the program that spent fifteen years explaining what it used to be, and is now remembering how to speak in present tense."
mantra: "Hook 'em."
authored_by: opus-editorial
editorial_review_status: draft
model_version: team-pages v1.0

accent_hex: "#BF5700"
accent_hex_secondary: "#FFFFFF"
gradient_hex_pair: "#BF5700,#8c3f00"

vocab:
  signoff: "Hook 'em."
  greeting: "HOOK 'EM"
  hashtags: ["#HookEm", "#TexasFight", "#ThisIsTexas"]
  selfname: "the Longhorns"
  stadium_short: "DKR"

# Added 2026-05-17 for v2-addendum Sprint v5-8.5 (Rituals + Cultural Identity)
rituals:
  - name: "Hook 'em Horns (the hand sign)"
    started_year: 1955
    when: "Constantly — at every score, every greeting, in every photograph involving a Texas fan"
    description: "Index and pinky extended, middle and ring folded — invented by head cheerleader Harley Clark in 1955 at a pep rally before the TCU game. Within a decade, every Texas fan greeted with it. Visible at presidential photos, Hollywood premieres, and graduation ceremonies. The most-recognized college fan hand sign in America."
    image_asset: "rituals/hook-em-horns.svg"
    cultural_significance: "high"
  - name: "Bevo (the longhorn steer)"
    started_year: 1916
    when: "Sideline every home game (when behaviorally appropriate)"
    description: "Live longhorn steer (Bevo XV is current). Each Bevo is a working steer with handlers from the Silver Spurs honorary service organization. The 2019 Bevo-vs-Uga (Sugar Bowl) charging incident is part of the lore. Bevo's horns are usually 70+ inches tip-to-tip. The bull is the largest live mascot in any major American sport."
    image_asset: "rituals/bevo-mascot.svg"
    cultural_significance: "high"
  - name: "The Eyes of Texas"
    started_year: 1903
    when: "End of every game, win or loss; pre-game"
    description: "The alma mater, set to 'I've Been Working on the Railroad.' Written 1903 by John Lang Sinclair. Sung by team, band, and fans with Hook 'em signs raised. Controversy around its minstrel-era origins surfaced in 2020; the program kept the song but added historical context. Still central to Texas game-day."
    image_asset: "rituals/eyes-of-texas.svg"
    cultural_significance: "high"
  - name: "Smokey the Cannon"
    started_year: 1953
    when: "Fired after every Texas score and after victories"
    description: "10-pound black-powder cannon fired by Texas Cowboys honorary service organization. Stationed in the south end zone. Each Texas score = one boom, audible across campus. Visiting fans often jump on the first one (it's louder than they expect). Smokey is technically illegal in some states; Austin grants a permit."
    image_asset: "rituals/smokey-cannon.svg"
    cultural_significance: "medium"
  - name: "Texas Fight (fight song)"
    started_year: 1923
    when: "After every score and during momentum shifts"
    description: "Composed by Walter Hunnicutt in 1923. The 'Texas Fight, Texas Fight, And it's goodbye to A&M' lyric was originally pointed at the rival; after A&M left the Big 12 (2012), the lyric became geographically odd. Now that A&M is back on the schedule (SEC 2024+), the lyric is timely again. The song's call-and-response structure is its signature."
    image_asset: "rituals/texas-fight.svg"
    cultural_significance: "medium"

cultural_anchors:
  one_sentence: "Texas is the program that spent 15 years convinced it deserved more — and the SEC move is the test of whether the conviction was correct."
  if_team_didnt_exist_cfb_would_lose: "Hook 'em Horns as the canonical college hand sign. Bevo as the largest live mascot in American sports. The Red River as a top-3 American sports rivalry. The 2005 Vince Young national title as the canonical 'one-man team beats dynasty' arc."
  fan_archetype_dominant: "Birthright-Believer"
  outsider_archetype_dominant: "Always-Should-Be-Better"

visual_identity_anchors:
  helmet_stripe_pattern: "single-burnt-orange-stripe-on-white-helmet"
  hero_imagery_default: "halftone-engraving-portrait-with-longhorn-silhouette"
  signature_color_combination: "burnt-orange-cream"

data_emphasis:
  primary: "sec_resume_first_year_and_beyond"
  secondary: "red_river_results"
  ignore: "big_12_only_metrics_now_obsolete"
  hero_finding_preferred_axis: "sec_road_record_first_two_seasons"

mascot_voice:
  awaiting_signal: "Bevo is chewing. Signal returns on its own time."
  empty_state: "DKR doesn't sleep in the off-season. It waits."
  post_win: "Hook 'em. That's more like it."
  post_loss: "Hook 'em. The burnt orange doesn't fade."

era_name_overrides:
  "1893-1956": "The Pre-Royal Decades"
  "1957-1976": "The Royal Era"
  "1977-1997": "The Wilderness (post-Royal)"
  "1998-2013": "The Mack Brown Era"
  "2014-2020": "The Collapse"
  "2021-": "The Sarkisian Restoration"

never_use:
  - plucky
  - Cinderella
  - scrappy
  - underdog
  - Texas is back without context (the phrase is its own meme)
  - college-football-royalty-now-slumbering-sleeping-giant register
  - mocking the burnt orange

always_surface:
  - 4 national championships (1963, 1969, 1970, 2005)
  - 2 Heisman winners (Earl Campbell 1977, Ricky Williams 1998)
  - 33 claimed conference championships across SWC + Big 12
  - SEC member since 2024 (conference realignment)
  - Darrell K Royal-Texas Memorial Stadium — ~100,119 capacity
  - Bevo — the live Texas longhorn steer mascot, continuous since 1916
  - The 2005 Rose Bowl (Vince Young vs. USC) — canonical national title game
  - Red River Showdown vs. Oklahoma — annual neutral-site in Dallas

stock_phrases:
  - Texas Fight.
  - The Eyes of Texas are upon you.
  - Hook 'em.
  - Born on third base and trying to hit a double. (fanbase self-aware line)
  - This is Texas.

rivalries:
  - tier: 1
    opponent: "Oklahoma"
    opponent_slug: "oklahoma"
    trophy: "Golden Hat"
    name: "Red River Showdown"
    accent_color: "amber"
    note: "Annual neutral-site at the Cotton Bowl in Dallas during the State Fair. The defining rivalry. Both programs now in the SEC; the series continues."
  - tier: 1
    opponent: "Texas A&M"
    opponent_slug: "texas-am"
    name: "Texas – Texas A&M"
    accent_color: "maroon"
    note: "Lone Star Showdown. Dormant 2011-2023 after A&M's SEC move; resumed in 2024. The in-state identity rivalry."
  - tier: 2
    opponent: "Arkansas"
    opponent_slug: "arkansas"
    name: "Texas – Arkansas"
    note: "Former SWC rivals; now both SEC. Annual resumption."
  - tier: 2
    opponent: "LSU"
    opponent_slug: "lsu"
    name: "Texas – LSU"
    note: "Emerging SEC crossover; recent Sugar Bowl history and 2023 non-conference game."
  - tier: 3
    opponent: "Baylor"
    opponent_slug: "baylor"
    name: "Texas – Baylor"
    note: "Former SWC / Big 12 rival; dormant post-realignment."

aspiration_ladder:
  - rung: "Bowl appearance"
    unlocked_by: "Baseline — assumed."
    context: "Below this rung is program-crisis territory."
  - rung: "Beat Oklahoma"
    unlocked_by: "Win the Red River Showdown."
    context: "For this fanbase, the season's truth-teller regardless of record."
  - rung: "SEC Championship Game"
    unlocked_by: "Win the SEC schedule path."
    context: "Where the 2024 Sarkisian team landed."
  - rung: "SEC Championship"
    unlocked_by: "Win the conference title game."
    context: "First SEC title would be program-historic."
  - rung: "CFP First-Round Bye"
    unlocked_by: "Top-4 seed in the 12-team CFP."
    context: "Where post-collapse Texas is expected to land."
  - rung: "CFP Semifinal"
    unlocked_by: "Win the quarterfinal."
    context: "The 2023 and 2024 Texas teams both reached this rung."
  - rung: "National Championship Game"
    unlocked_by: "Win the semifinal."
    context: "The 2023 team lost to Washington here; the 2025 team's open question."
  - rung: "National Championship"
    unlocked_by: "Win it."
    context: "Title #5 — the first since 2005, which is the program's 20-year loop."

heritage:
  founded: 1893
  national_titles: 4
  conference_titles: 33
  heismans: 2
  cfp_appearances: 2
  bowl_appearances: 59
  current_conference: "SEC"
  stadium: "Darrell K Royal-Texas Memorial Stadium / 'DKR' (100,119)"
  legendary_coach: "Darrell K. Royal"
  wiki_team_page: "https://en.wikipedia.org/wiki/Texas_Longhorns_football"

coaching_regimes:
  - coach: "Strong"
    start_year: 2014
    end_year: 2016
  - coach: "Herman"
    start_year: 2017
    end_year: 2020
  - coach: "Sarkisian"
    start_year: 2021
    end_year: null

era_annotations:
  - x_year: 2016
    y_source: "mood"
    label: "5-7 · Strong fired"
    color: "red"
  - x_year: 2023
    y_source: "mood"
    label: "CFP semi · last Big 12 year"
    color: "amber"
  - x_year: 2024
    y_source: "mood"
    label: "CFP semi as SEC member"
    color: "gold"
---

# Identity and heritage

Texas football was founded in 1893 and has operated since as one of American college football's flagship state-university programs. Four national championships: 1963, 1969, 1970, and 2005. Two Heismans: Earl Campbell (1977) and Ricky Williams (1998). Thirty-three conference championships across Southwest Conference (1915–1995) and Big 12 (1996–2023) play. In 2024 Texas joined the SEC, alongside Oklahoma, as part of the conference realignment that reshaped American college football's power structure.

Darrell K Royal-Texas Memorial Stadium — "DKR" — opened 1924 and now holds 100,119 after multiple expansions. Named for the program's most important coach; his statue stands outside the stadium. Bevo — the live Texas longhorn steer mascot — has been a continuous line since 1916, with the current Bevo being the fifteenth. The program's colors, burnt orange and white, are one of the most recognizable identity palettes in American college sport.

The 2005 national championship — Vince Young's 8-yard fourth-down run vs. USC in the Rose Bowl with 19 seconds left — is the modern spine of the program's identity. It's also the line that divides recent Texas history: everything before is context for the title; everything after is measured against the decade-and-a-half of not being able to get back.

# Coaching lineage

Dana X. Bible (1937–1946) stabilized the pre-war program. Darrell K. Royal (1957–1976) is the program's cornerstone — 167-47-5 record, three national titles (1963, 1969, 1970), 11 SWC championships. Royal's "wishbone" offense, designed with Emory Bellard, revolutionized college football. Royal's statue, DKR stadium, and the program's cultural memory all anchor to him. He died in 2012; his legacy endures.

The post-Royal wilderness (Fred Akers, David McWilliams, John Mackovic — 1977–1997) produced three SWC titles and a Heisman (Campbell 1977) but no national championships and only one Cotton Bowl win in the final SWC decade. Mack Brown (1998–2013) restored the program: 158-48 record, two BCS title-game appearances, the 2005 national championship, Ricky Williams' Heisman (1998), and a decade (1998–2009) of sustained top-10 presence.

The collapse era (Charlie Strong 2014–2016, Tom Herman 2017–2020) is the program's defining recent wound. Seven years of losing seasons in a span where Oklahoma dominated the Big 12 and the SEC pulled away as the national power conference. The "Texas is back" meme — born in this era from each false restart — still hangs over the program.

Steve Sarkisian (2021–present) inherited a damaged program, produced three losing-to-competitive years (2021 5-7, 2022 8-5, 2023 12-2), and delivered a 2024 SEC-first-season 13-3 run that reached the CFP semifinal. 2026 is Sarkisian's sixth year and the question of whether Texas has fully restored or is still recovering.

# Notable players

Heismans: Earl Campbell (1977) — possibly the most physically dominant college running back who ever played. Ricky Williams (1998) — the all-time career rushing yards leader at the time of his graduation. National champion rosters: 1963 James Saxton-era team, 1969 Steve Worster wishbone team, 2005 Vince Young / Jamaal Charles team, plus Cedric Benson, Colt McCoy, Brian Orakpo.

Modern era: Colt McCoy (2009 title game), Jamaal Charles, Brian Orakpo, Malcolm Brown, Sam Ehlinger, Bijan Robinson (2022 first-round pick), Quinn Ewers, Arch Manning (2026 starter — the Manning family continuation).

# Fans and culture

The fanbase is the SEC's newest megabase and one of the largest in college football by any measure. Geography is Texas-dominated (Austin + Dallas–Fort Worth + Houston + San Antonio saturation), with a strong national alumni network concentrated in coastal cities. Gameday register is confident-Texan: the fanbase carries itself with the institutional confidence of a program that has four titles and expects more, and the specific swagger of Texas itself.

"The Eyes of Texas" — the alma mater — is sung after every home game, win or lose. "Hook 'em" is a greeting, a sign-off, a hand gesture (index and pinky extended), and a declaration of affiliation. "Texas Fight" is the fight song. Bevo is led onto the field pre-game. The burnt orange color is recognizable statewide.

The internal fracture most visible: the older fans who remember Royal-era dominance and the 2005 title, and the middle-aged fans who lived the 2010s collapse and are still not sure if the 2024 run was sustainable. The register "Texas is back" is treated with fanbase irony (from years of false starts) and must be handled carefully in generated copy.

# Voice and ethos

The voice is confident-Texan: institutional, swagger-forward, aware of the 2010s collapse and moving through it without self-pity or defensiveness. Texas doesn't apologize for expecting to be in the conversation, but the program's fanbase has had enough self-awareness injected by the collapse years that the voice carries more maturity than the "born on third base" stereotype would suggest. The register is "we know where we've been."

Identity phrase: **"Texas is the program that spent fifteen years explaining what it used to be, and is now remembering how to speak in present tense."**

Mantra: **"Hook 'em."** Universal. Greeting, sign-off, punctuation. The hand gesture is the visual equivalent.

Stock phrases — "Texas Fight," "The Eyes of Texas are upon you," "Hook 'em," "This is Texas" — carry real weight. "Born on third base" is a fanbase-internal line of self-awareness; it appears rarely but earns affection when it does.

The never-use list excludes "plucky," "Cinderella," "scrappy" (all wrong for Texas). "Texas is back" without context is a meme — the phrase itself is its own joke at this point. The 2010s collapse is real institutional memory; dismissing or ignoring it reads as generic copy. "College-football-royalty-now-slumbering-sleeping-giant" is a frame that was true 2015–2020 but is not the current frame.

# Rivalries

**Red River Showdown** (vs. Oklahoma) is the program's signature rivalry. Annual, neutral-site at the Cotton Bowl in Dallas during the Texas State Fair. The Golden Hat trophy has alternated since 1941. Both programs joined the SEC in 2024; the rivalry continues as an SEC conference game (with the neutral-site tradition preserved). The 2023 Texas win (34-30) was an emotional capstone to the "Texas is back" conversation.

**Texas–Texas A&M** (Lone Star Showdown) was dormant 2011–2023 after A&M's SEC move and resumed in 2024 with both in the SEC. The rivalry is the in-state identity game; its resumption in 2024 was one of the SEC's biggest storylines of the conference-realignment era.

**Texas–Arkansas** is a former SWC rivalry that resumed under SEC realignment.

**Texas–LSU** is an emerging SEC rivalry; the 2023 non-conference game (LSU won 45-24 at LSU) and recent Sugar Bowl meetings have built weight.

# Current context

Head coach: Steve Sarkisian (6th year, 2026). Offensive coordinator: Sarkisian retains play-calling. Defensive coordinator: Pete Kwiatkowski. Athletic director: Chris Del Conte. NIL collective: Texas One Fund (merged from prior collectives). Facilities: Moncrief-Neuhaus Athletic Center, the Moody Center (2022), Red McCombs Red Zone.

Conference: SEC (since 2024). Previous: Big 12 (1996–2023), Southwest Conference (1915–1995).

# Program narratives

The 2024 SEC-first-season run (13-3, CFP semifinal) answered the "can Texas play at SEC speed" question. The 2025 and 2026 seasons are about whether the program can close the gap to Georgia, Alabama, and LSU in the SEC title race, and whether Arch Manning (Peyton and Eli's nephew, starter since 2025) can be the program's Vince Young-caliber quarterback.

The portal and NIL era have favored Texas — the Texas One Fund has been among the SEC's best-resourced collectives, and the program has successfully recruited both high-end high school talent and key portal additions. The specific open question: at what point is Sarkisian's program the SEC favorite, or does it plateau as a top-10 perennial without the national-title cut?

# Aspiration framework

Baseline: SEC Championship Game appearance and CFP bid. Realistic ceiling: CFP semifinal and national title game. Dream ceiling: first SEC championship and national title #5 (first since 2005). Historic ceiling: the 2005 perfect season or the 1969 wishbone-era dominance. Historic floor: 2016 (5-7) under Strong. Unlock: contender view is on by default; remained on even in the collapse years because of program stature.

# Chronicle tuning

For Texas, the anomaly that reads is Sarkisian-era-improving-relative-to-Royal or 2005 benchmark. Echoes resonate when connected to 2005 (the canonical title), 1969 (wishbone dominance), 1998 (Ricky Williams Heisman). Retroactive patterns: "Texas in Red River games," "Fourth-quarter defense under Sarkisian," "Arch Manning progression." The 2010s collapse years are available as dark echoes when relevant.

# In-jokes and copypasta

"Hook 'em" — universal; real hand gesture. "The Eyes of Texas" — alma mater; sung reverently. "Texas Fight" — fight song. "Come early, be loud, stay late, wear orange" — DKR home game instruction to fans. "Texas is back" — meme; used with irony. "Arch" — Arch Manning shorthand; affectionate. "Burnt orange" — color identity, specifically burnt (not pumpkin, not regular orange). "DKR" — the stadium shorthand.

# Taboos and sensitivities

The 2005 national title is sacred; references should be earned, not casual. The 2010s collapse is a real wound; acknowledge, don't litigate. "The Eyes of Texas" has had an ongoing racial-history conversation that the university has addressed; copy should not flatten that history or treat it glibly. The 2023 Alabama loss (34-24) in Austin is recent wound; the 2024 CFP loss to Washington is also recent. The "Texas is back" meme is used by fans in self-deprecation; outside-media use of it without that context reads as mockery.
