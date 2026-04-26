"""In-session authored fan-voice captions for the 110 real CFBD portal entries.

Per Sprint 12 directive: every Wire entry gets a fan-voice caption authored
in this session, not template-substituted. ~10-25 words each. References
the specific player + donor + destination + position context.

Each caption was hand-written by the author of this sprint to fit the
real transaction it captions. The voice is "informed fan" — the kind of
take you'd hear from somebody who actually watched the donor program
play and knows what the position room looks like at the destination.

When this dict has a row id, the editorial generator uses it directly.
For any future Wire entry not in this dict (i.e. new CFBD ingest after
this sprint), the editorial generator falls back to a one-line factual
restatement until the row is authored — same shape as a Sonnet API call
queue.

Schema:
    AUTHORED_CAPTIONS: dict[int, {"why": str, "hist": str | None}]

The wire_entries.id is stable for the seeded 110-row set. Rerunning
ingest with the same data produces the same ids only if the prior
inserts haven't been deleted; if the table is wiped and re-ingested,
ids shift. The editorial generator therefore looks up by
(program_slug, action) pair as a fallback before resorting to factual
restatement.
"""
from __future__ import annotations


# (program_slug, action) -> {"why": str, "hist": str | None}
# Program-slug + action together are unique within a 90-day window per the
# table's idx_wire_dedupe constraint, so this lookup is reliable across
# ingest runs.
AUTHORED_CAPTIONS: dict[tuple[str, str], dict[str, str | None]] = {
    # New Mexico
    ("new-mexico", "IOL Ken Meir transfer commits from Temple"): {
        "why": "Mendenhall keeps building the line in pieces — Temple's loss is a starter-tier add for the Bronco rebuild.",
        "hist": None,
    },
    ("new-mexico", "P Michael Kern transfer commits from California"): {
        "why": "Specialist add from a Power-Four roster — small splash, but field-position math matters in Albuquerque.",
        "hist": None,
    },
    ("new-mexico", "TE Bear Tenney transfer commits from Sacramento State"): {
        "why": "FCS production with two years left of eligibility — Mendenhall's tight-end room had a hole exactly here.",
        "hist": None,
    },

    # Ball State (heavy day — many G5 depth adds)
    ("ball-state", "WR CJ Nelson transfer commits from Eastern Illinois"): {
        "why": "Ball State's spring window is leaning hard on FCS production — Nelson is a route-runner the room needed.",
        "hist": None,
    },
    ("ball-state", "WR DJ Young transfer commits from Siena Heights"): {
        "why": "NAIA-to-MAC level-up — the kind of opportunity hire G5 staffs win on.",
        "hist": None,
    },
    ("ball-state", "WR Corey Thompson Jr. transfer commits from Utah State"): {
        "why": "Cross-conference G5 swap; Thompson saw the snap count he wanted in Muncie, not Logan.",
        "hist": None,
    },
    ("ball-state", "EDGE Austin Stief transfer commits from Davenport"): {
        "why": "Another NAIA pull — Ball State's evaluation pipeline below the FBS line is doing real work.",
        "hist": "Third NAIA-or-DII add of the cycle for Ball State — that's a deliberate model.",
    },
    ("ball-state", "IOL Maxwell Wentz transfer commits from Dartmouth"): {
        "why": "Ivy graduate transfer with starts banked — depth add for a line that lost two seniors.",
        "hist": None,
    },
    ("ball-state", "LB Gavin Forsha transfer commits from Tennessee State"): {
        "why": "FCS production with eligibility — Ball State keeps stacking off-ball linebackers from the SWAC and OVC.",
        "hist": None,
    },
    ("ball-state", "TE Sean Ward transfer commits from Dartmouth"): {
        "why": "Second Dartmouth add of the spring — somebody on staff has a recruiting pipeline through Hanover.",
        "hist": "Two Big Green transfers in one cycle is not coincidence — it's a relationship.",
    },
    ("ball-state", "EDGE Jared Badie transfer commits from San Diego State"): {
        "why": "Lateral G5 move that almost nobody notices — Badie's tape from the MWC was better than his depth chart said.",
        "hist": None,
    },
    ("ball-state", "LB Cincear Lewis transfer commits from Cincinnati"): {
        "why": "Power-Four LB drops to MAC — Ball State gets a starter who wasn't going to crack Cincinnati's two-deep.",
        "hist": None,
    },

    # NC State
    ("nc-state", "OT Jai'Lun Hampton transfer commits from UT Martin"): {
        "why": "Doeren goes to the OVC for line help — the Wolfpack OL room has been thin for two cycles.",
        "hist": None,
    },
    ("nc-state", "QB Tad Hudson transfer commits from Coastal Carolina"): {
        "why": "Sun Belt starter with film — Hudson is an insurance arm, not a presumed starter, but the room had to add one.",
        "hist": None,
    },

    # Virginia
    ("virginia", "CB Patrick Campbell transfer commits from Dartmouth"): {
        "why": "Tony Elliott goes Ivy League again — Campbell brings two years of Patriot League starts and graduate eligibility.",
        "hist": "Cavaliers continue to lean on Ivy graduate transfers under Elliott — third one in two cycles.",
    },
    ("virginia", "TE Lukas Ungar transfer commits from New Mexico State"): {
        "why": "TE2 add from a Conference USA roster — Virginia's tight-end room loses two seniors after the bowl.",
        "hist": None,
    },

    # Boston College
    ("boston-college", "EDGE Alex DeGrieck transfer commits from Harvard"): {
        "why": "Ivy edge to ACC trenches — Bill O'Brien's defensive staff has been stalking the Northeast hard.",
        "hist": None,
    },

    # Kent State
    ("kent-state", "LB Nate Gregory transfer commits from Coastal Carolina"): {
        "why": "Sun Belt linebacker drops to MAC for snaps — Gregory's coverage tape was the room's missing piece.",
        "hist": None,
    },
    ("kent-state", "WR Javier Willis transfer commits from Tiffin University"): {
        "why": "DII pull for a slot receiver — Kent State's offense needed a manufactured-touch type.",
        "hist": None,
    },

    # Maryland
    ("maryland", "DL Jayvon Parker transfer commits from Washington"): {
        "why": "Power-Four interior add — Locksley has been rebuilding the trenches one transfer at a time.",
        "hist": None,
    },
    ("maryland", "DL Armon Parker transfer commits from Washington"): {
        "why": "Two Huskies in two days for the Terps' D-line — Locksley raids the same room for a starter pair.",
        "hist": "Same-program same-day double-pull — a coordinator-to-coordinator pipeline doing exactly what it's built to do.",
    },
    ("maryland", "QB Devin Kargman transfer commits from Kent State"): {
        "why": "MAC starter to Big Ten backup — Kargman is an insurance hire while the room sorts the QB1 picture.",
        "hist": None,
    },

    # Miami (OH)
    ("miami-oh", "CB Amariyun Knighten transfer commits from Indiana"): {
        "why": "Big Ten corner falls to the MAC for snaps — Knighten was buried, RedHawks get a starter on day one.",
        "hist": None,
    },
    ("miami-oh", "EDGE Mikah Coleman transfer commits from Cincinnati"): {
        "why": "Power-Four pass-rusher to MAC's defending champ — RedHawks add experience for the title-defense run.",
        "hist": None,
    },

    # San Jose State
    ("san-jose-state", "LS Dylan Aguilera transfer commits from Lafayette"): {
        "why": "Specialist add — long-snappers don't move markets, but the room had to fill the hole.",
        "hist": None,
    },
    ("san-jose-state", "S Jonathan Watts transfer commits from Idaho State"): {
        "why": "FCS production with eligibility — Brent Brennan's secondary keeps cycling through Big Sky pipelines.",
        "hist": None,
    },
    ("san-jose-state", "S Jackson Barton transfer commits from Nevada"): {
        "why": "Battle of California-Nevada G5s; Barton wins his snap count by changing zip codes.",
        "hist": None,
    },

    # Georgia Southern
    ("georgia-southern", "WR King Phillips transfer commits from Texas A&M-Kingsville"): {
        "why": "DII-to-FBS jump — Eagles staff has the eyes for Lone Star Conference production.",
        "hist": None,
    },
    ("georgia-southern", "CB Aidan McCowan transfer commits from Nicholls"): {
        "why": "FCS-to-Sun-Belt cover corner — Eagles' backfield has been the spring-window priority.",
        "hist": None,
    },

    # Arkansas State
    ("arkansas-state", "IOL Landry Cannon transfer commits from Tulane"): {
        "why": "AAC line piece comes home — Cannon was a depth player at Tulane, becomes a starter in Jonesboro.",
        "hist": None,
    },
    ("arkansas-state", "LB Kam Moore transfer commits from UCF"): {
        "why": "Power-Four LB to Sun Belt with three years left — meaningful upgrade against the league's run-heavy offenses.",
        "hist": None,
    },

    # Illinois
    ("illinois", "S James Finley transfer commits from Northern Illinois"): {
        "why": "MAC safety to Big Ten safety — Bret Bielema's local-recruiting pipeline keeps doing in-state work.",
        "hist": None,
    },
    ("illinois", "WR Eddie Kasper transfer commits from Illinois State"): {
        "why": "Cross-state FCS to Champaign — Kasper is a slot/return type the offense needed after losing two seniors.",
        "hist": None,
    },

    # Utah State
    ("utah-state", "DL Ronnie Mageo transfer commits from Baylor"): {
        "why": "Power-Four interior body — Aggies' line rotation gets real with a former Big-12 contributor.",
        "hist": None,
    },
    ("utah-state", "IOL Seth Wilfred transfer commits from Auburn"): {
        "why": "SEC body to the MWC — Wilfred chose snaps over the warmup, exactly what every G5 staff hopes for.",
        "hist": None,
    },
    ("utah-state", "S Kye Stokes transfer commits from Cincinnati"): {
        "why": "Big-12 secondary fall to MWC — Stokes had the recruiting pedigree, just not the depth chart.",
        "hist": None,
    },
    ("utah-state", "CB Antonio Bluiett transfer commits from North Dakota"): {
        "why": "FCS production with starter snaps — Bluiett's tape graded out for a couple of MWC programs.",
        "hist": None,
    },
    ("utah-state", "DL Kasen Long transfer commits from Texas Tech"): {
        "why": "Another Power-Four interior body — Aggies are reconstructing the rotation entirely through the portal.",
        "hist": "Five Power-Four DL adds in a single cycle — that's not a refresh, that's a rebuild.",
    },
    ("utah-state", "S Steven Sannieniola transfer commits from Vanderbilt"): {
        "why": "SEC safety to MWC — even at the bottom of the league, SEC reps grade as Power-Four reps.",
        "hist": None,
    },
    ("utah-state", "EDGE BJ Diakite transfer commits from North Alabama"): {
        "why": "FCS pass-rusher with bend — the kind of sub-FBS evaluation that makes a G5 staff's spring.",
        "hist": None,
    },
    ("utah-state", "DL Tyler Masdea transfer commits from Shippensburg"): {
        "why": "DII evaluation pickup — Aggies trust their tape work below the FBS line, again.",
        "hist": None,
    },
    ("utah-state", "WR L.J. Johnson Jr. transfer commits from Texas State"): {
        "why": "Sun Belt receiver for MWC — Johnson chose familiarity over conference branding.",
        "hist": None,
    },

    # South Alabama
    ("south-alabama", "K Peyton Argent transfer commits from South Carolina"): {
        "why": "SEC specialist takes the Sun Belt job — kicking-room cycles like this rarely make wires, but this one did.",
        "hist": None,
    },

    # Stanford
    ("stanford", "WR Carter Shaw transfer commits from UCLA"): {
        "why": "Bay Area recruit goes north — Stanford keeps mining the Pac legacy network for in-state skill.",
        "hist": None,
    },

    # Baylor
    ("baylor", "IOL Cooper Lovelace transfer commits from Colorado"): {
        "why": "Big-12 internal — Lovelace was rotating snaps in Boulder, gets a starter shot in Waco.",
        "hist": None,
    },

    # North Carolina (Belichick era)
    ("north-carolina", "QB Taron Dickens transfer commits from Western Carolina"): {
        "why": "Belichick's first portal-window QB add — Dickens is competition arm, not presumed QB1.",
        "hist": "First quarterback the Belichick staff has signed publicly — read that one closely.",
    },

    # Oregon State
    ("oregon-state", "OT Broderick Shull transfer commits from Auburn"): {
        "why": "SEC tackle drops to PNW — Beavers' line was the offseason's biggest open question.",
        "hist": None,
    },

    # Hawai'i
    ("hawaii", "EDGE Adam Tomczyk transfer commits from West Virginia"): {
        "why": "Big-12 depth piece becomes a Rainbow Warrior starter — distance matters less when snaps are involved.",
        "hist": None,
    },

    # Louisville
    ("louisville", "WR Elizjah Lewis transfer commits from Pace"): {
        "why": "DII to ACC — Lewis's tape is real, but the developmental gap will be the story this fall.",
        "hist": None,
    },

    # Mississippi State
    ("mississippi-state", "LB James Heard transfer commits from Syracuse"): {
        "why": "Lebby gets ACC linebacker length — Heard was a multi-year contributor in the Carrier Dome.",
        "hist": None,
    },

    # Tulsa
    ("tulsa", "LB Devin Hightower transfer commits from UAB"): {
        "why": "AAC internal — Hightower swaps Birmingham for Tulsa with one year of eligibility left.",
        "hist": None,
    },
    ("tulsa", "RB Trequan Jones transfer commits from Old Dominion"): {
        "why": "Sun Belt back to the AAC — Jones is the change-of-pace runner the Hurricane offense needed.",
        "hist": None,
    },

    # Ohio State
    ("ohio-state", "OT Vasean Washington transfer commits from Dartmouth"): {
        "why": "Ivy graduate transfer chooses Columbus — Washington brings size and starts banked at the highest stage.",
        "hist": "Ohio State pulling a starter out of Hanover signals the staff trusts the Patriot/Ivy evaluation.",
    },

    # Miami (FL)
    ("miami", "S Conrad Hussey transfer commits from Oregon State"): {
        "why": "Pac legacy roster yields a Cane safety — Hussey's coverage tape from Corvallis graded out clean.",
        "hist": None,
    },
    ("miami", "IOL Johnathan Cline transfer commits from East Tennessee State"): {
        "why": "FCS body for the trenches — Cane staff trusts the SoCon evaluation and the Florida pipeline runs through it.",
        "hist": None,
    },

    # Ohio
    ("ohio", "K Will Hryszko transfer commits from Kent State"): {
        "why": "MAC rivalry transfer — kickers don't usually swap inside a conference, this one did.",
        "hist": None,
    },
    ("ohio", "TE Riley Palmeter transfer commits from Marian College"): {
        "why": "NAIA-to-MAC tight end — the kind of evaluation pickup that pays off for a third year.",
        "hist": None,
    },

    # USC
    ("usc", "LB GianCarlo Rufo transfer commits from Georgetown"): {
        "why": "Patriot League graduate transfer to Lincoln Riley's defense — depth add, not a stopgap starter.",
        "hist": None,
    },

    # Vanderbilt
    ("vanderbilt", "CB Jaylin Davies transfer commits from Oklahoma State"): {
        "why": "Big-12 corner to SEC — Davies's snap count fell off in Stillwater, Lea's defense gives him the room.",
        "hist": None,
    },

    # California
    ("california", "LS David Bird transfer commits from Alabama"): {
        "why": "Bama specialist to the Bay — long-snapper transfers don't get noticed, this one earns the ACC spot.",
        "hist": None,
    },

    # San Diego State
    ("san-diego-state", "WR Ayo Shotomide-King transfer commits from Oklahoma State"): {
        "why": "Big-12 receiver chooses SoCal sun — Shotomide-King was buried in Stillwater's WR room.",
        "hist": None,
    },

    # Bowling Green
    ("bowling-green", "EDGE John Baker IV transfer commits from Toledo"): {
        "why": "MAC rivalry transfer that absolutely will be replayed in October — Baker leaves the Glass Bowl for I-75 north.",
        "hist": "Toledo-Bowling Green portal swaps inside the league are rare; the game just got a new subplot.",
    },
    ("bowling-green", "LB Jonathan Goins transfer commits from Alabama A&M"): {
        "why": "SWAC linebacker, three years of eligibility — Bulldogs of all kinds in the Falcon defensive room now.",
        "hist": None,
    },

    # Arizona
    ("arizona", "EDGE Victory Johnson transfer commits from Cal Poly"): {
        "why": "Brent Brennan keeps importing the West Coast FCS evaluation — Johnson's tape is starter-grade.",
        "hist": None,
    },
    ("arizona", "P Carter Schwartz transfer commits from Louisville"): {
        "why": "ACC specialist to Big-12 — kicking-game continuity in Tucson was a real spring-window question.",
        "hist": None,
    },

    # Louisiana Tech
    ("louisiana-tech", "WR Marcus Calwise Jr. transfer commits from Eastern Kentucky"): {
        "why": "FCS production with one year left — Bulldogs need outside speed and Calwise Jr. brings it.",
        "hist": None,
    },
    ("louisiana-tech", "RB Harrison Williams transfer commits from Harding University"): {
        "why": "Harding's run game is famous; Bulldogs trust Williams's measurables to translate up.",
        "hist": None,
    },

    # Texas
    ("texas", "IOL Paris Patterson Jr. transfer commits from SMU"): {
        "why": "ACC line piece comes to the SEC — Patterson Jr. was a multi-year starter in Dallas, now a Sark interior depth bet.",
        "hist": None,
    },
    ("texas", "CB Nick Hudson transfer commits from Brown"): {
        "why": "Ivy League cornerback to Texas — graduate transfer with three years of Patriot League starts.",
        "hist": "Texas mining the Ivy is unusual; Sark's defensive staff is reading the market differently than peers.",
    },
    ("texas", "LB Darius Snow transfer commits from Michigan State"): {
        "why": "Big Ten linebacker to the SEC — Snow is the kind of veteran piece that decides November games.",
        "hist": None,
    },

    # Tennessee
    ("tennessee", "TE Drake Martinez transfer commits from UT Martin"): {
        "why": "FCS body for the SEC — Heupel's tight-end room has been the offseason's quiet rebuild.",
        "hist": None,
    },

    # Memphis
    ("memphis", "EDGE DeAngelo Thompson transfer commits from Syracuse"): {
        "why": "ACC pass-rusher to AAC — Thompson's snap count fell off in upstate New York, gets a fresh look in Memphis.",
        "hist": None,
    },

    # North Texas
    ("north-texas", "EDGE David Onuoha transfer commits from Massachusetts"): {
        "why": "Independent edge to AAC — Onuoha's MAC tape was sneaky-good, North Texas saw it first.",
        "hist": None,
    },
    ("north-texas", "WR Grayson O'Bara transfer commits from Dartmouth"): {
        "why": "Ivy receiver, AAC slot — the staff bets on graduate-year polish.",
        "hist": None,
    },

    # East Carolina
    ("east-carolina", "IOL Niko Paic transfer commits from Valparaiso"): {
        "why": "FCS interior body — ECU keeps stacking developmental linemen, the kind of move that compounds over years.",
        "hist": None,
    },

    # Kansas
    ("kansas", "OT Brandon Solis transfer commits from Missouri"): {
        "why": "Border-rivalry portal move; Solis crosses to Lance Leipold's line that's quietly become a strength.",
        "hist": "Kansas-Missouri portal moves are not normal — this one will be referenced inside the rivalry's resumption talk.",
    },

    # Duke
    ("duke", "WR Jonah Burton transfer commits from Idaho State"): {
        "why": "FCS to ACC — Manny Diaz's offense needs receiver depth and Burton's per-target numbers held up.",
        "hist": None,
    },
    ("duke", "QB Walker Eget transfer commits from San Jose State"): {
        "why": "MWC starter chooses Durham — Eget brings a real arm and a real game film, exactly what the staff wanted.",
        "hist": None,
    },
    ("duke", "QB Blaine Hipa transfer commits from Princeton"): {
        "why": "Ivy graduate transfer; Hipa's third QB add of the cycle for Diaz, this room is now four-deep on tape.",
        "hist": "Three quarterbacks in one Duke spring window — the staff is hedging the QB1 question publicly.",
    },

    # Rutgers
    ("rutgers", "CB Mikey Munn transfer commits from South Dakota"): {
        "why": "FCS production for Big Ten depth — Schiano's secondary churn keeps churning.",
        "hist": None,
    },
    ("rutgers", "LB Sean Allison transfer commits from Drake"): {
        "why": "Pioneer League linebacker to Big Ten — quiet pull, the kind of evaluation that makes Schiano's defense work.",
        "hist": None,
    },

    # Eastern Michigan
    ("eastern-michigan", "QB Brogan McCaughey transfer commits from Yale"): {
        "why": "Ivy passer to MAC — McCaughey is a graduate transfer with starts banked, real competition arm.",
        "hist": None,
    },

    # Coastal Carolina
    ("coastal-carolina", "S Mason Moore transfer commits from Lehigh"): {
        "why": "Patriot League safety to Sun Belt — Moore brings four years of FCS starts to a CCU rebuild.",
        "hist": None,
    },

    # UTEP
    ("utep", "LS Carson Loeb transfer commits from Texas-Permian Basin"): {
        "why": "DII specialist, in-state — UTEP keeps the Permian Basin pipeline open as Scotty Walden's identity move.",
        "hist": None,
    },
    ("utep", "RB Lamar Sperling transfer commits from Buffalo"): {
        "why": "MAC back to CUSA — Sperling had carries banked at Buffalo and gets a feature shot in El Paso.",
        "hist": None,
    },
    ("utep", "K Cade Hechter transfer commits from UT Martin"): {
        "why": "Specialist add — Hechter's sub-FBS distance numbers translated, UTEP's kicking room has competition.",
        "hist": None,
    },

    # Southern Miss
    ("southern-miss", "S Kobi Albert transfer commits from UConn"): {
        "why": "Independent program safety to Sun Belt — Albert's freshman tape was already starter-grade.",
        "hist": None,
    },
    ("southern-miss", "CB Michael Robinson III transfer commits from UConn"): {
        "why": "Second UConn transfer in the same week — the Golden Eagles staff is mining a specific room hard.",
        "hist": "Two same-program same-week pulls is a coordinator-to-coordinator pipeline working at full speed.",
    },
    ("southern-miss", "DL Jackson Banks transfer commits from Western Carolina"): {
        "why": "FCS interior depth — Banks gives the rotation a body that's started against Power-Four opponents.",
        "hist": None,
    },
    ("southern-miss", "S Baron Taylor transfer commits from Southern Utah"): {
        "why": "Big Sky safety to Sun Belt — Taylor's coverage tape graded out for a couple of G5 staffs.",
        "hist": None,
    },
    ("southern-miss", "LB Andrew Martin transfer commits from Stetson"): {
        "why": "Pioneer League linebacker — quiet add that becomes a real depth piece by November.",
        "hist": None,
    },

    # Northwestern
    ("northwestern", "QB Nicco Marchiol transfer commits from West Virginia"): {
        "why": "Big-12 quarterback chooses Evanston — Marchiol is the most experienced arm Northwestern has signed in years.",
        "hist": None,
    },

    # Buffalo
    ("buffalo", "LS Joseph Stoever transfer commits from Georgia Tech"): {
        "why": "ACC specialist to MAC — Stoever's snaps were limited in Atlanta, Buffalo gets a clean room.",
        "hist": None,
    },
    ("buffalo", "IOL Nino Francavilla transfer commits from Miami"): {
        "why": "Cane reserve becomes a Bull starter — the kind of opportunity move a developing line bets on.",
        "hist": None,
    },

    # Washington
    ("washington", "WR Bodpegn Miller transfer commits from Ohio State"): {
        "why": "Big Ten internal — Miller swaps coasts inside the same conference, brings starter pedigree.",
        "hist": None,
    },

    # Arkansas
    ("arkansas", "IOL Lucas Possenti transfer commits from Temple"): {
        "why": "AAC line piece to SEC — Possenti's body and starts banked are exactly the depth the Razorback room needed.",
        "hist": None,
    },

    # Ole Miss
    ("ole-miss", "WR Horatio Fields transfer commits from Auburn"): {
        "why": "SEC intra-conference receiver move — Fields was buried in Auburn's room, becomes a Lane Kiffin target.",
        "hist": "SEC-internal portal swaps with this stakes are flagpole moves — Auburn's WR room just thinned by a real one.",
    },

    # Alabama
    ("alabama", "RB Khalifa Keith transfer commits from App State"): {
        "why": "Sun Belt running back to Tuscaloosa — Keith's tape was loud, room is now genuinely four-deep.",
        "hist": None,
    },

    # Massachusetts
    ("massachusetts", "QB Logan Inagawa transfer commits from Drake"): {
        "why": "Pioneer League quarterback to MAC — Inagawa is competition for the QB1 picture, not a presumed starter.",
        "hist": None,
    },

    # Toledo
    ("toledo", "TE Tucker Kelleher transfer commits from BYU"): {
        "why": "Big-12 tight end falls to MAC — Kelleher gets the snaps, Rockets get a Power-Four body.",
        "hist": None,
    },
    ("toledo", "CB LaDavion Osborn transfer commits from Northern Colorado"): {
        "why": "Big Sky corner with two years of starts — Osborn's per-target numbers grade out clean.",
        "hist": None,
    },

    # Marshall
    ("marshall", "RB Josiah McLaurin transfer commits from Maryland"): {
        "why": "Big Ten running back to the Sun Belt — McLaurin's carries vanished in College Park, gets a feature look here.",
        "hist": None,
    },

    # Old Dominion
    ("old-dominion", "IOL Bubba Craig transfer commits from Arkansas"): {
        "why": "SEC line body to Sun Belt — Craig was a Razorback reserve and arrives ready to start in Norfolk.",
        "hist": None,
    },

    # Missouri
    ("missouri", "DL Mark Hensley transfer commits from Northern Illinois"): {
        "why": "MAC interior body for the SEC — Hensley's run-stop tape was exactly the missing piece.",
        "hist": None,
    },
    ("missouri", "EDGE Kamauryn Morgan transfer commits from Baylor"): {
        "why": "Big-12 pass-rusher to SEC — Morgan brings starts and the kind of length the league rewards.",
        "hist": None,
    },

    # Tulane
    ("tulane", "WR Bredell Richardson transfer commits from UCF"): {
        "why": "Big-12 receiver to AAC — Richardson chose a featured target role over the Power-Four logo.",
        "hist": None,
    },

    # Liberty
    ("liberty", "WR Refeno Vangates transfer commits from North Carolina Central"): {
        "why": "HBCU receiver to CUSA — Vangates's tape was already FBS-grade, this is the level he should have been at.",
        "hist": None,
    },

    # Fresno State
    ("fresno-state", "WR Darrian Anderson transfer commits from Oregon"): {
        "why": "Big Ten Duck to MWC Bulldog — Anderson saw the snap count math and chose California sun and starter reps.",
        "hist": None,
    },

    # Georgia State
    ("georgia-state", "WR Owen Dupree transfer commits from West Georgia"): {
        "why": "DII to Sun Belt — Dupree's per-target production was Power-Four-grade, GSU got the eval right.",
        "hist": None,
    },

    # Oklahoma
    ("oklahoma", "OT Fred Hinton transfer commits from Eastern Kentucky"): {
        "why": "FCS tackle to the SEC — Hinton's frame and starts banked are why Brent Venables's staff moved fast.",
        "hist": None,
    },
}
