---
team_id: 374
program_name: Notre Dame
display_name: Notre Dame
program_slug: notre-dame
program_tier: 1
voice_register: dynastic-with-question-mark
tonal_template: dynastic-with-question-mark
identity_phrase: "Notre Dame is a program that knows what it is, and still asks the question."
mantra: "Play like a champion today."
authored_by: opus-editorial
editorial_review_status: draft
model_version: team-pages v1.0

accent_hex: "#0C2340"
accent_hex_secondary: "#C99700"
gradient_hex_pair: "#0C2340,#C99700"

vocab:
  signoff: "Go Irish."
  greeting: "GO IRISH"
  hashtags: ["#GoIrish", "#NDFootball"]
  selfname: "the Irish"
  stadium_short: "Notre Dame Stadium"

# Added 2026-05-17 for v2-addendum Sprint v5-8.5 (Rituals + Cultural Identity)
rituals:
  - name: "Play Like a Champion Today (the sign)"
    started_year: 1980s (Lou Holtz era)
    when: "Players tap it as they exit the locker room"
    description: "The blue-and-gold sign hangs above the tunnel from locker room to field. Every Notre Dame player taps it on the way out. Origin is contested (Holtz says he brought it; Devine claims earlier). The sign is now a national archetype — copied at every level of football. The original survives, scuffed by 40 years of palm taps."
    image_asset: "rituals/play-like-a-champion.svg"
    cultural_significance: "high"
  - name: "Victory March (the fight song)"
    started_year: 1908
    when: "After every score, played by the band; sung by all 80,000+"
    description: "'Cheer cheer for old Notre Dame...' Written by Michael and John Shea in 1908. The most recognizable college fight song in America. Plays through Notre Dame Stadium PA after every score. The trumpet quartet's a cappella version before kickoff at the Grotto is its own sub-ritual."
    image_asset: "rituals/victory-march.svg"
    cultural_significance: "high"
  - name: "Trumpet Quartet at the Grotto"
    started_year: 1990s
    when: "Pre-game, ~3 hours before kickoff"
    description: "Four trumpeters from the band play the Alma Mater and Victory March at the Grotto of Our Lady of Lourdes. Spiritual/musical sub-ritual that draws hundreds of fans. Distinctly Notre Dame — no other program has a Marian shrine in its pre-game flow."
    image_asset: "rituals/trumpets-at-grotto.svg"
    cultural_significance: "medium"
  - name: "Touchdown Jesus"
    started_year: 1964
    when: "The Hesburgh Library mural visible above the stadium's open north end"
    description: "Mural of Christ with raised hands, painted as 'Word of Life' (1964). Visible from inside Notre Dame Stadium until the 1997 expansion partially obscured it. The Christ figure's pose mirrors a referee signaling touchdown — hence the universal nickname. The mural is sacred art that became sports iconography by geometric accident."
    image_asset: "rituals/touchdown-jesus.svg"
    cultural_significance: "high"
  - name: "The Shillelagh and the Leprechaun"
    started_year: 1965
    when: "Sideline at every game"
    description: "The student-portrayed Leprechaun mascot was formally adopted in 1965 (replacing the previous 'Fighting Irish' iconography). The shillelagh — the gnarled walking stick — is wielded during games. The Megaphone Game vs USC and the Jeweled Shillelagh Trophy connect this to specific rivalry pageantry."
    image_asset: "rituals/notre-dame-leprechaun.svg"
    cultural_significance: "medium"

cultural_anchors:
  one_sentence: "Notre Dame is the program that converted Catholic mass immigration into a national fanbase that has nothing to do with proximity to South Bend."
  if_team_didnt_exist_cfb_would_lose: "The independent's case — the proof that you can be a top-10 program without conference affiliation. The Lou Holtz era. The Rudy myth. The Touchdown Jesus accidental theology."
  fan_archetype_dominant: "Subway Alumnus"
  outsider_archetype_dominant: "Mystic-Persecuted"

visual_identity_anchors:
  helmet_stripe_pattern: "gold-helmet-no-stripe-iconic"
  hero_imagery_default: "halftone-engraving-portrait"
  signature_color_combination: "kelly-green-gold-navy"

data_emphasis:
  primary: "independent_schedule_strength"
  secondary: "national_recruiting_radius"
  ignore: "conference_standing_metrics"
  hero_finding_preferred_axis: "consensus_all_americans_per_decade"

mascot_voice:
  awaiting_signal: "The Leprechaun is keeping his own counsel. Signal returns with camp."
  empty_state: "Under the Golden Dome the quiet is structural — the program is listening."
  post_win: "Play like a champion today. You did."
  post_loss: "Play like a champion today. Tomorrow is still the test."

era_name_overrides:
  "1918-1930": "The Rockne Era"
  "1941-1953": "The Leahy Years"
  "1964-1974": "The Ara Era"
  "1986-1996": "The Holtz Era"
  "2010-2021": "The Kelly Reconstruction"
  "2022-": "The Freeman Era"

never_use:
  - scrappy underdog
  - Cinderella
  - small-school charm
  - overachiever
  - punching above their weight
  - Catholics vs. Convicts as a currently-running frame
  - Touchdown Jesus as copy device (it is a place, not a punchline)
  - mid or mid-tier framing

always_surface:
  - National independence + NBC broadcast contract as a structural identity marker
  - 11 consensus national championships (claimed) + 13 claimed total
  - 7 Heisman Trophy winners — most of any program
  - 96 consensus All-Americans
  - The Shillelagh Trophy series vs. USC as the modern identity-rivalry
  - Academic discipline as a recruiting filter, not a limitation
  - 2024 CFP National Championship Game appearance

stock_phrases:
  - "The Irish don't wait to be invited to the conversation — they walk in."
  - "Notre Dame plays an 11th-game schedule inside a 12-game calendar."
  - "Every season here is measured against the ones people name after coaches."

rivalries:
  - tier: 1
    opponent: "USC"
    opponent_slug: "usc"
    trophy: "Jeweled Shillelagh"
    name: "Notre Dame – USC"
    accent_color: "amber"
    note: "The intersectional rivalry that defines the program's national identity."
  - tier: 1
    opponent: "Navy"
    opponent_slug: "navy"
    trophy: "Rip Miller Trophy"
    name: "Notre Dame – Navy"
    note: "The oldest continuous rivalry in college football."
  - tier: 1
    opponent: "Michigan"
    opponent_slug: "michigan"
    name: "Notre Dame – Michigan"
    note: "Resumed; the bluebloods of the Midwest."
  - tier: 2
    opponent: "Stanford"
    opponent_slug: "stanford"
    trophy: "Legends Trophy"
    name: "Notre Dame – Stanford"
  - tier: 2
    opponent: "Boston College"
    opponent_slug: "boston-college"
    trophy: "Ireland Trophy"
    name: "Notre Dame – Boston College (Holy War)"
  - tier: 3
    opponent: "Purdue"
    opponent_slug: "purdue"
    trophy: "Shillelagh Trophy"
  - tier: 3
    opponent: "Michigan State"
    opponent_slug: "michigan-state"
    trophy: "Megaphone Trophy"

aspiration_ladder:
  - rung: "Bowl win"
    unlocked_by: "Baseline; expected annually."
    context: "Restores the season's shape."
  - rung: "New Year's Six appearance"
    unlocked_by: "Top-12 finish or 10+ wins."
    context: "Table stakes for this program's national slot."
  - rung: "CFP Quarterfinal"
    unlocked_by: "Top-12 CFP ranking at selection."
    context: "The 12-team format lowered the entry fee, not the standard."
  - rung: "CFP Semifinal"
    unlocked_by: "Win the quarterfinal."
    context: "Where the program's era gets argued about."
  - rung: "National Championship Game"
    unlocked_by: "Win the semifinal."
    context: "2024 proved this rung is not theoretical."
  - rung: "National Championship"
    unlocked_by: "Win it."
    context: "Title #12 would be the first since 1988."
  - rung: "Dynasty Window"
    unlocked_by: "Back-to-back top-4 finishes + CFP wins."
    context: "The unclaimed question that trails Notre Dame like a shadow."

heritage:
  founded: 1887
  national_titles: 13
  conference_titles: 0
  heismans: 7
  cfp_appearances: 2
  bowl_appearances: 38
  current_conference: "FBS Independent"
  stadium: "Notre Dame Stadium (77,622)"
  legendary_coach: "Knute Rockne"
  wiki_team_page: "https://en.wikipedia.org/wiki/Notre_Dame_Fighting_Irish_football"
  broadcast_partner: "NBC Sports (since 1991)"

coaching_regimes:
  - coach: "Kelly"
    start_year: 2014
    end_year: 2021
  - coach: "Freeman"
    start_year: 2022
    end_year: null

era_annotations:
  - x_year: 2016
    y_source: "mood"
    label: "The 4-8 bottom"
    color: "red"
  - x_year: 2018
    y_source: "ap"
    label: "Cotton Bowl semi loss"
    color: "amber"
  - x_year: 2024
    y_source: "mood"
    label: "Title game, at last"
    color: "gold"
---

# Identity and heritage

Notre Dame football is one of college sport's founding institutions. Founded in 1887, the program is claimed home to 13 national championships (11 consensus), seven Heisman Trophy winners — the most of any program — and 96 consensus All-Americans. The Irish have remained FBS independent since 1887, maintaining a national broadcast partnership with NBC since 1991 that has defined the program's relationship with a national audience as much as any on-field result.

Notre Dame Stadium, opened in 1930 and expanded to 77,622, is one of the most architecturally identifiable venues in the sport. "Touchdown Jesus" — the Hesburgh Library mural — overlooks the end zone but belongs to the campus, not the broadcast. The program's modern national reach runs through the TV schedule, the intersectional rivalry with USC, and the continuous annual Navy game, which is the oldest uninterrupted rivalry in the sport.

# Coaching lineage

Knute Rockne (1918–1930) is the cornerstone — a 105-12-5 career record, five national titles, and the coach who made Notre Dame a national brand. Frank Leahy (1941–1953) added four more titles. Ara Parseghian (1964–1974) and Dan Devine (1975–1980) kept the program at the table. Lou Holtz (1986–1996) brought the 1988 national championship, the last one the program has claimed.

The modern rebuild began under Brian Kelly (2010–2021), who produced two BCS/CFP appearances and the winningest tenure in program history without a national title. Marcus Freeman took over in late 2021 and inherited both the program's infrastructure and its unanswered question. In 2024 the Freeman-led Irish reached the CFP National Championship Game, losing to Ohio State — the first title-game appearance since 1988.

# Notable players

Heismans: Angelo Bertelli (1943), Johnny Lujack (1947), Leon Hart (1949), John Lattner (1953), Paul Hornung (1956), John Huarte (1964), Tim Brown (1987). Modern era standouts include Manti Te'o, Kyle Hamilton, Jeremiah Owusu-Koramoah, and the 2024 CFP title-game roster anchored by Riley Leonard and Jeremiyah Love.

# Fans and culture

The fanbase is national — the "subway alumni" concept predates television and still operates. Geography runs from the Chicago-Notre Dame-South Bend corridor out to every major American city where Catholic diasporas settled in the 20th century. The gameday register is reverent, ritual-heavy, and aware of being watched: pep rally traditions, the march across campus, the band's fight song before every home snap. The tailgate is older than most programs' stadia.

Internal fractures exist but are muted. The biggest recurring argument: whether independence is still the correct structural choice in a revenue-allocation era where conference membership is everything. The program's answer so far — in 2024 especially — is that the NBC contract, the CFP access path, and the recruiting base do not require a conference affiliation to compete at the top rung.

# Voice and ethos

The voice is dynastic with a question mark. Notre Dame speaks the way programs speak when their history is larger than their present — confident, institutional, attentive to standard — but the specific question ("can we still?") is never fully retired, and performative modesty is a trust-killer. The Irish do not apologize for expecting to win, and do not mistake expectation for achievement.

The identity phrase opens most state-of-team paragraphs:
**"Notre Dame is a program that knows what it is, and still asks the question."**

The mantra — "Play like a champion today" — closes the paragraph when the register allows. It is a real slogan on a real plaque that players touch before every home game; it is not a tagline.

Stock phrases earned on the fanbase over decades — "The Irish don't wait to be invited," "an 11th-game schedule inside a 12-game calendar," "measured against the ones people name after coaches" — can appear when the context supports them.

The never-use list is strict. "Scrappy underdog," "Cinderella," and "punching above their weight" are frames for other programs entirely. "Catholics vs. Convicts" is a historical artifact from 1988 and not a currently-running frame. "Touchdown Jesus" as a rhetorical device instead of a place reads as outsider-copy.

# Rivalries

The Jeweled Shillelagh (vs. USC, first played 1926) is the defining rivalry — intersectional, national, and the one the program plays for its identity as much as for any conference implication. The all-time record runs close; the streaks matter more than the ledger.

The Rip Miller Trophy (vs. Navy, first played 1927) is the oldest continuous rivalry in college football. The emotional weight is different from USC — reverential, closer to ritual — and the program surfaces the Navy game even in years when the scoreboard would let it be quiet.

The Michigan rivalry was resumed in 2018 after decades of hiatus and is now again an annual fixture. Bluebloods-of-the-Midwest register: if the SEC/Big Ten conversation can be ducked by pointing at the Shillelagh, the Michigan game is the one that has to be won on its own merits.

# Current context

Head coach: Marcus Freeman (since December 2021). Athletic director: Pete Bevacqua. The NIL collective ("Friends of the University of Notre Dame," Rally) launched in 2022. Facilities: the Irish Athletics Center (opened 2022) consolidated the football program's footprint on South Bend's north end.

# Program narratives

The 2024 National Championship Game run is still the near-term narrative center of gravity: a program that reached the title game with a young, transfer-portal-augmented roster, under a coach in his third year. The question of whether 2024 was a peak or a floor is the single biggest open thread in the program's story. Spring 2026 and the portal window are where the next version of that answer is being built.

Independence continues as a structural choice. Conference realignment hasn't forced the hand in either direction; the program continues to schedule five ACC games per year under the 2014 ACC arrangement that gives it membership in other sports without football affiliation.

# Aspiration framework

Baseline expectation: 10 wins and a top-10 finish with a New Year's Six or CFP bid. The 12-team CFP format has made "CFP Quarterfinal" a realistic annual rung rather than a ceiling. The dream rung — dynasty window — is the unanswered question that has trailed the program since 1988.

# Chronicle tuning

For Notre Dame, the anomaly that reads is scheme-divergence from program baseline: a rushing output 1.5 SD above the recent Kelly-era average signals a genuinely different offensive identity. Echoes that resonate connect forward from the Kelly run into the Freeman era. Retroactive cards read best when tied to 1988, 2012 (the BCS title-game appearance), or 2024 (the CFP title-game appearance) — the three decision-windows in the modern era.

# In-jokes and copypasta

"The Shillelagh lives here" — the stock reply when a USC alum questions the year's rivalry result. "Play like a champion today" — real, not a bit. "Rudy" is mentioned exactly once every five years internally; it is not a fan-culture load-bearing reference the way it is in outside media.

# Taboos and sensitivities

The 1988 championship is a long time ago and fans know that; copy that calls it "recent" reads as patronizing. The Brian Kelly departure (to LSU, mid-season 2021) is not a wound to keep picking at — the program moved on, but the exit is not a subject for light humor. Any implication that Notre Dame football is "just a schoolboy team that won't play in the real league" — a recurring outside take — should be acknowledged in the voice, not defended against with insecurity.
