---
team_id: 140
program_name: Auburn
display_name: Auburn
program_slug: auburn
program_tier: 2
voice_register: defiant-underdog-with-teeth
tonal_template: defiant-underdog-with-teeth
identity_phrase: "Auburn is the program the SEC West cannot schedule around."
mantra: "War Eagle."
authored_by: opus-editorial
editorial_review_status: draft
model_version: team-pages v1.0

accent_hex: "#0C2340"
accent_hex_secondary: "#E87722"
gradient_hex_pair: "#0C2340,#E87722"

vocab:
  signoff: "War Eagle."
  greeting: "WDE"
  hashtags: ["#WarEagle", "#AuburnFB", "#WDE"]
  selfname: "the Tigers"
  stadium_short: "Jordan-Hare"

# Added 2026-05-17 for v2-addendum Sprint v5-8.5 (Rituals + Cultural Identity)
rituals:
  - name: "Eagle Flight Pre-Game"
    started_year: 2000
    when: "Before kickoff at every home game"
    description: "A live golden eagle (Nova or Aurea, alternating) launches from the upper deck of Jordan-Hare and spirals down to midfield as 87,000 fans roar 'WAAAAR EAGLE!' through the descent. The fan voice is built into the ritual — the eagle's flight times the chant. One of the most theatrical pre-game traditions in sports."
    image_asset: "rituals/auburn-eagle-flight.svg"
    cultural_significance: "high"
  - name: "Rolling Toomer's Corner"
    started_year: 1972
    when: "After every football victory"
    description: "Fans wrap the oak trees at the intersection of College Street and Magnolia Avenue in toilet paper. The 2010 BCS title run drowned the corner in white. The original oaks were poisoned by an Alabama fan in 2010 and replaced; the ritual continued through the interregnum on new trees."
    image_asset: "rituals/toomers-corner.svg"
    cultural_significance: "high"
  - name: "War Eagle Cheer"
    started_year: 1914
    when: "Constantly — at every score, every defensive stop, every moment of doubt"
    description: "Not a fight song, not a chant — a call-and-response that defines Auburn fandom. Origin stories vary (the Civil War veteran's pet eagle is the favored one). Used as greeting, sign-off, victory cry, condolence. The phrase IS the program."
    image_asset: "rituals/war-eagle-cheer.svg"
    cultural_significance: "high"
  - name: "Tiger Walk"
    started_year: 1962
    when: "Two hours before kickoff"
    description: "Players walk from Sewell Hall to Jordan-Hare through a corridor of fans. Originated when fans spontaneously lined the route in 1962; codified into a ritual within a decade. Replicated (badly) at programs nationwide; Auburn's was the prototype."
    image_asset: "rituals/auburn-tiger-walk.svg"
    cultural_significance: "medium"
  - name: "Iron Bowl Week"
    started_year: 1893
    when: "Last week of regular season, alternating Tuscaloosa and Auburn"
    description: "Not a single ritual — a 7-day suspension of normal life for both fanbases. The 2013 Kick Six, the 2010 comeback, the 1972 Punt Bama Punt — Auburn's identity is partly measured in Iron Bowl miracles. Calendar marker that overrides everything else."
    image_asset: "rituals/iron-bowl.svg"
    cultural_significance: "high"

cultural_anchors:
  one_sentence: "Auburn is the SEC's defiant underdog with a 1,200-year history of doing the impossible when nobody asked it to."
  if_team_didnt_exist_cfb_would_lose: "The program that proves the SEC can have personality alongside dynasty — the team that ruins Alabama's season often enough to keep college football honest."
  fan_archetype_dominant: "Defiant Underdog"
  outsider_archetype_dominant: "Chaos-Agent"

visual_identity_anchors:
  helmet_stripe_pattern: "single-stripe-orange-on-navy"
  hero_imagery_default: "ligne-claire-with-eagle-silhouette"
  signature_color_combination: "navy-orange-cream"

data_emphasis:
  primary: "iron_bowl_results"
  secondary: "sec_west_resume_strength"
  ignore: "pre_1980_national_rankings"
  hero_finding_preferred_axis: "iron_bowl_win_rate_under_current_coach"

mascot_voice:
  awaiting_signal: "Aubie is on campus. Signal returns when the cow-bells do."
  empty_state: "Jordan-Hare is waiting. The week after Alabama is where the year is measured."
  post_win: "War Eagle. You earned it."
  post_loss: "Next week. The SEC West doesn't mourn."

era_name_overrides:
  "1957-1975": "The Jordan Era"
  "1981-1992": "The Dye Era"
  "1999-2008": "The Tuberville Run"
  "2009-2012": "The Chizik Title Window"
  "2013-2020": "The Malzahn Era"
  "2021-2023": "The Harsin Interruption"
  "2024-": "The Freeze Era"

coaching_regimes:
  - coach: "Malzahn"
    start_year: 2014
    end_year: 2020
  - coach: "Harsin"
    start_year: 2021
    end_year: 2022
  - coach: "Freeze"
    start_year: 2023
    end_year: null

era_annotations:
  - x_year: 2014
    y_source: "mood"
    label: "Post-Kick Six hangover"
    color: "amber"
  - x_year: 2017
    y_source: "ap"
    label: "SEC West champs · beat Bama & UGA"
    color: "gold"
  - x_year: 2020
    y_source: "mood"
    label: "Malzahn fired"
    color: "red"
  - x_year: 2023
    y_source: "mood"
    label: "Freeze reset"
    color: "navy"

never_use:
  - little-brother framing
  - glorified ag-school framing
  - Cinderella
  - scrappy (at this tier)
  - plucky
  - Kick Six as a we-own-the-rivalry boast (it was one play and the other side has decades of ledger)
  - 'Bo knows as a copy device detached from Bo Jackson the person'

always_surface:
  - 2010 national championship (Cam Newton, 14-0, the crown jewel)
  - 1957 national championship (the program's claimed first)
  - 3 Heisman winners (Pat Sullivan 1971, Bo Jackson 1985, Cam Newton 2010)
  - The Iron Bowl as an annual identity event, not a secondary rivalry
  - Jordan-Hare Stadium capacity 88,043
  - The Hugh Freeze era (since December 2022) and the bet it represents

stock_phrases:
  - "War Eagle is the greeting; the eagle flight before kickoff is the ritual."
  - "Auburn doesn't recruit above its weight — Auburn recruits the weight the weight classes don't cover."
  - "The cow-bells belong to Mississippi State. The eagle flight belongs to us."

rivalries:
  - tier: 1
    opponent: "Alabama"
    opponent_slug: "alabama"
    trophy: "Iron Bowl"
    name: "The Iron Bowl"
    accent_color: "orange"
    note: "Annual, in-state, structurally the only rivalry Auburn's identity bends toward."
  - tier: 2
    opponent: "Georgia"
    opponent_slug: "georgia"
    name: "Deep South's Oldest Rivalry"
    note: "Played every year since 1898 with minor exceptions; the South's oldest football rivalry between two FBS programs."
  - tier: 2
    opponent: "LSU"
    opponent_slug: "lsu"
    name: "Auburn – LSU"
    note: "SEC West night-game rivalry; Tiger Stadium as venue sharpens the register."
  - tier: 3
    opponent: "Tennessee"
    opponent_slug: "tennessee"
    name: "Auburn – Tennessee"
    note: "Once-annual SEC crossover, now rotating."
  - tier: 3
    opponent: "Florida"
    opponent_slug: "florida"
    name: "Auburn – Florida"

aspiration_ladder:
  - rung: "Bowl win"
    unlocked_by: "6 wins and a bowl invite."
    context: "Baseline — floor for a serious Auburn year."
  - rung: "Win the Iron Bowl"
    unlocked_by: "Beat Alabama in the last Saturday of November."
    context: "For this fanbase, this rung alone can redeem a season. The converse also applies."
  - rung: "Beat Georgia"
    unlocked_by: "Win the Deep South's Oldest Rivalry."
    context: "Second-heaviest load on the schedule."
  - rung: "SEC Championship Game"
    unlocked_by: "Win the SEC West path."
    context: "Reachable once or twice a decade in the modern era."
  - rung: "SEC Championship"
    unlocked_by: "Win the SEC title game."
    context: "Last won 2013 under Malzahn."
  - rung: "CFP Semifinal"
    unlocked_by: "Top-4 committee placement."
    context: "Not yet reached in the CFP era."
  - rung: "National Championship"
    unlocked_by: "Win it."
    context: "Title #3. Last one was 2010."

heritage:
  founded: 1892
  national_titles: 2
  conference_titles: 15
  heismans: 3
  cfp_appearances: 0
  bowl_appearances: 47
  current_conference: "SEC"
  stadium: "Jordan-Hare Stadium (88,043)"
  legendary_coach: "Ralph 'Shug' Jordan"
  wiki_team_page: "https://en.wikipedia.org/wiki/Auburn_Tigers_football"
---

# Identity and heritage

Auburn football was founded in 1892 and has claimed two national championships — the 1957 Ralph Jordan team and the 2010 Gene Chizik / Cam Newton team. Three Heismans: Pat Sullivan (1971), Bo Jackson (1985), and Cam Newton (2010). The program has played in the SEC since the conference's founding in 1933 and lives in the rivalry-saturated SEC West slot opposite Alabama.

Jordan-Hare Stadium (88,043) has been the home venue since 1939. The pre-game eagle flight — a live raptor released above the field before kickoff — is one of the sport's most identifiable rituals and a load-bearing part of the gameday identity. War Eagle is the universal greeting, the sign-off, and the chant that carries from the aerial descent to the post-play roar. The name of the team is the Tigers; the rallying cry is War Eagle. Both are correct.

# Coaching lineage

Ralph "Shug" Jordan (1951–1975) is the cornerstone — 176 wins, the 1957 national title, and the identity of a program that runs through his name (the stadium itself). Pat Dye (1981–1992) returned the program to national conversation with four SEC titles. Tommy Tuberville (1999–2008) produced the 2004 13-0 undefeated season that lost the BCS title shot to Oklahoma/USC — a wound that still shapes Auburn's relationship with the polls.

Gene Chizik's brief tenure (2009–2012) delivered the 2010 national championship behind Cam Newton — a program-defining run that reset every Auburn-era benchmark. Gus Malzahn (2013–2020), the offensive architect of the 2013 Kick Six season, produced an SEC title in 2013 and the 2017 SEC West championship before being released. Bryan Harsin (2021–2022) is the program's shortest modern tenure — a hire that did not fit the culture. Hugh Freeze (since December 2022) is the current rebuild bet; his three years at Auburn have been uneven but the infrastructure and recruiting class have hardened.

# Notable players

Heismans: Pat Sullivan (1971), Bo Jackson (1985), Cam Newton (2010). Modern-era standouts include Nick Fairley, Tre Mason, Daniel Carlson, Derrick Brown, Jarquez Hunter, Payton Thorne. The NFL draft pipeline is a consistent top-15 producer nationally when Auburn is healthy — recent roster losses to the portal have narrowed it, but the recruiting ground (Alabama, Georgia, Florida) is structurally rich.

# Fans and culture

The Auburn fanbase is structurally defiant — a culture built opposite Alabama's in the same state, with the same recruiting footprint, for the same SEC bid. The register tilts toward earned-not-given: Auburn fans know what the ledger says against Alabama, and the fans' relationship with their own identity is closer to a fight-song than a dynasty-song. "War Eagle" is greeting and parting; "All In" is the recruiting-era stock phrase; the toomer's corner toilet-paper rolling (a post-victory tradition at Toomer's Oaks) is one of the sport's oldest fan rituals, even after the oaks were poisoned in 2011 and replanted.

The internal fracture most visible during uneven years: the cohort that believes Auburn's identity requires beating Alabama at least 2x every 5 years vs. the cohort that reads the rivalry as one game among many. Both are Auburn fans; the divergence deepens during post-Kick-Six drought years.

# Voice and ethos

The voice is defiant-underdog-with-teeth: proud, edged, unwilling to accept the state's little-brother framing, and comfortable taking a swing. Auburn does not apologize for itself, does not pretend to be Alabama, and does not romanticize losing. "War Eagle" is said with a straight face and a sharp edge; performative humility reads as phony in Auburn just as it does in Tuscaloosa.

Identity phrase: **"Auburn is the program the SEC West cannot schedule around."**

Mantra: **"War Eagle."** A declaration, not a motto.

The never-use list rules out little-brother framing, cinderella read, and Kick Six as a ledger-tipping device. The Kick Six is a real and load-bearing memory — it happened, it mattered — but leaning on it as proof of anything more than one play reads as a hollow boast.

# Rivalries

The Iron Bowl (vs. Alabama, since 1893) is the rivalry. It is not ranked behind anything. Annual, in-state, and structurally shaped as the place the season ends. Alabama leads the all-time ledger; Auburn leads it in kairos — the moments that rewrite a season's shape (2013 Kick Six; 2017 Iron Bowl win that sent Auburn to the SEC title game).

Deep South's Oldest Rivalry (vs. Georgia, since 1892) is the second-heaviest schedule line. Played every year with minor interruptions since 1898. The all-time ledger favors Georgia; the Auburn-Georgia game routinely decides which SEC West/East hybrid contender advances to the SEC title.

Auburn–LSU is the night-game rivalry, especially at Tiger Stadium. Shared mascot + shared SEC West divisional history sharpens it; recent games (2022 "Earthquake" game etc.) have kept the emotional weight high even in down cycles.

# Current context

Head coach: Hugh Freeze (since December 2022). Athletic director: John Cohen. NIL collective: "On To Victory." Facilities: the 2024 renovation of the Wellness Kitchen and the locker-room rebuild are recent; the Woltosz Football Performance Center (opened 2021) is the program's day-to-day infrastructure anchor.

# Program narratives

The Hugh Freeze bet is the single open narrative thread. Freeze arrived with a top-tier recruiting profile and a reputation for offensive innovation paired with off-field risk; his record in three seasons at Auburn is uneven, his recruiting has been strong, and the program's fan intelligence is measuring whether 2026 is the year the infrastructure converts into a 10-win SEC-contender season. The roster, the schedule, and the NIL operation are all aligned with that question.

Conference realignment has made the SEC West even harder (Oklahoma and Texas added in 2024). Auburn's path to the SEC Championship Game now runs through more CFP-caliber programs than at any point in the program's history.

# Aspiration framework

Baseline: bowl-eligible, beat Alabama once every two years, win 8+. Realistic ceiling: SEC West title + New Year's Six bowl. Dream ceiling: SEC championship + CFP semifinal appearance. Historic ceiling: title #3.

# Chronicle tuning

For Auburn, anomalies read best when framed against the specific recruiting-footprint ground the program competes over (Alabama, Georgia, Florida). An offensive output 1.5 SD above the Malzahn/Freeze baseline against an SEC West opponent is a load-bearing signal. Echoes resonate when they connect forward to 2010 (the title) or 2013 (the Kick Six year) — the two modern decision-windows. Retroactive cards work when they tie roster-construction decisions to Iron Bowl outcomes.

# In-jokes and copypasta

"Bo knows" — real, attached to Bo Jackson the actual person, not a detached pop-culture reference. "Toomer's Corner" — the post-victory tree-rolling tradition; a Lincoln Riley reference from 2010 is still quoted by older fans. "All In" — the Chizik-era stock phrase that survives.

# Taboos and sensitivities

The 2013 Kick Six is a real memory that can be referenced; it should not be leaned on as evidence the rivalry ledger favors Auburn, because it does not. The 2011 Toomer's Oaks poisoning (by an Alabama fan) is a real story and should be handled with care, not humor. Bryan Harsin's tenure is recent and not a target for light mockery — the program and the athletic department have moved on. Any implication that Auburn is "Alabama's little brother" reads as a rival's line and should be answered with confidence, not defensiveness.
