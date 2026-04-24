# Team Page — Iteration Log

**Purpose:** Running log of design decisions, mockups, and concepts developed during the team-page redesign sessions. Insurance against conversation compression. Update after every major iteration.

**Canonical brief:** `TEAM_PAGE_WORLD_CLASS_BRIEF.md` (Part I + Part II addendum).
**Companion:** `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`.

---

## North-star framing (Kevin's direction)

- Goal: "best in class visualization of what it's like to actually follow the team or the sport."
- Audience: second-screen fan — Twitter open, group-texting, half-watching. Also serve casuals, hardcore fans, data nerds in one surface.
- Emotional bullseye: "boots on the ground feel and emotional attachment to theater of the season."
- Metaphor posture: inherit from narrative forms (prestige TV, books, theater, journalism, Bloomberg terminal) without literally costuming the product as any of them. The metaphor is a *standard the product is held to*, not a model it resembles.
- Voice: every team's structure identical, voice never. Per-team voice profiles drive copy, era names, mascot fallbacks, tribal vocabulary.
- Design posture: "A+ make-or-break." Work in Figma. Mobile-amazing is a hard requirement.

## Scope decision

**v1.0 = CFP era (2014–present).** Locked 2026-04-23.

Rationale: data completeness consistent, LLM narrative generation quality high, build cost ~10x cheaper than full 130-year history. Heritage preserved via a compact strip (title count, Heismans, legendary coaches in one sentence) + legendary-season canon cards for the ~5-10 most-important all-time seasons per program.

Architecture must be extensible — adding historical depth later should be additive, not a rebuild.

## Technical constraints

- Solo builder, AI-assisted (ChatGPT Pro + Claude Max).
- Python static-site generator → SQLite → HTML.
- `reporting.py` is 17.5k lines; new work lives in a separate module.
- Build-time LLM generation is fine. Runtime LLM calls are not.
- No backend, no auth, no real-time infrastructure.
- Mobile-first, not mobile-afterthought.
- Community/UGC features cut from committed scope — seeded editorial annotations only.

## Core concepts established

### The frame slot (generalizes Conference Lens)
Three templates chosen by program attribute:
- Conference (for P4 / G5 conference members)
- Division (for divisional conferences)
- Independent Resume (for ND, Army, Navy, UConn, etc.)

### Rivalry tiering is program-local
A program declares 3–7 rivalries with internal tiers. Notre Dame ships with USC/Navy/Michigan at Tier 1, Stanford/BC at Tier 2, Purdue/Michigan State at Tier 3. Alabama ships with Auburn at Tier 1, Tennessee/LSU at Tier 2.

### The Arc viz — two registers
- For historical-depth programs (future/v2): 131-season climate stripe with era ribbon, FT-style annotations, coach/conference regime ribbon.
- For CFP-era v1.0: 13-season "brick strip" — each season a richer info-dense card (year / record / rank / outcome) instead of one thin bar. Each season earns real visual real estate because there are fewer of them.

### The season theater view
The current-season surface. Key design moves:
- 4-metric top row (AP / Record / SP+ / CFP odds) with weekly deltas
- 12-game schedule strip where every game has a *characterization* ("the axis", "revenge", "trap", "sacred", "closer") — the fanbase's emotional map rendered
- Past-vs-future visual distinction (filled vs outlined; current week bold-outlined)
- Mood sparkline beneath that interacts with the schedule above
- Serif story paragraph + "this week" bookmarked callout
- Dual-audience: 5-second read = metric tiles; 30-second read = schedule + characterizations; deep read = mood curve + story

### The Pulse module — proprietary-data moat visible
Bloomberg-terminal aesthetic, updated daily. Contains:
- Mood number + weekly delta + velocity vs. baseline (e.g., "2.3x baseline · busiest Tuesday since 2024 run")
- 72-hour "what moved it" event log with signed mood deltas (Strava activity-feed pattern)
- Top 3–4 conversation topics with sentiment bars
- Reality gap + respect gap + cohort divergence compact cards
- 3 curated representative quotes ("the takes"), sentiment-color-coded, venue-attributed
- Footer linking to conversation venues (r/team, hashtags, boards)

### The rivalry card
Inspired by: boxing tale-of-the-tape, polling aggregators, Polymarket dual-outcome boards, Letterboxd activity panels, Genius dual-annotation.
- Mythic-centered header (rivalry proper noun in serif, e.g., "The Jeweled Shillelagh")
- 4-column meta strip (all-time / streak / trophy / countdown)
- Dual-trajectory chart showing both fanbases' rivalry-heat building toward kickoff, with gap annotated on-chart (FT-style)
- Two posture-labeled panels (e.g., "dismissive · confident" vs "anxious · bargaining"), each with a representative quote
- Recent meetings as editorial list (one sentence of context per meeting, not just scores)
- Dual-perspective "what each side needs" stakes footer

### Tribal voice system
Per-team `team_voice` SQLite table holding accent color, gradient pair, vocab dict, mascot voice templates, era name overrides, tonal template enum. LLM generates per-team copy; human editorial review for top-30 programs; long tail uses tonal defaults. Generic-template voice is *worse* than no voice — don't ship wrong voices.

### Seasonal sentience (in-progress concept)
The page should feel different by time of year and day of week.
- Annual cycle: Jan (bowl + coaching carousel + Wrapped) → Feb (NSD + portal) → Mar–Apr (spring + portal + draft) → May–June (dead period + heritage) → July (media days) → Aug (camp) → Sep (early season) → Oct (stakes rising) → Nov (rivalry peak) → Dec (CFP selection).
- Weekly cycle: Sun (autopsy) → Mon (licking wounds or basking) → Tue (depth chart + injuries) → Wed (matchup sharpens) → Thu (hype peaks) → Fri (anticipation) → Sat (gameday → live → post-game) → Sun (autopsy again).
- Implementation: daily build picks template variant based on calendar. Modules promoted/demoted based on context. Copy templates have day-of-week and month-of-year variants.

### Historical contextualization (in-progress concept)
Each season since 2014 rendered with the same immersive treatment as the current season:
- Title + thesis (serif editorial)
- Retrospective season shape with mood trajectory (including crash if applicable)
- 2–3 defining moments as editorial callouts
- Pull quote from the era
- Legacy framing ("what it meant")
- Nav to adjacent seasons

## Mockups produced this session

1. **131-season climate stripe hero** — ND 1896–2026, era ribbon with "The Wilderness" and named epochs, FT-style annotations at peaks, 1988 season card preview. Demonstrated maximum historical depth.

2. **CFP-era 13-season brick strip** — ND 2014–2026, heritage strip on top (compact preservation), 13 richer season cards, 2-era ribbon (Kelly / Freeman), 2024 featured season expanded. Demonstrated the narrowed-scope hero at a better altitude for 13 seasons.

3. **Current-season theater view** — ND 2026 through Week 2. 4-metric row, 12-game characterized schedule strip, mood curve with preseason-to-projected trajectory, serif story, this-week callout. Demonstrated the "theater of now" register and dual-audience density.

4. **The Pulse module** — ND Week 3 fan intelligence surface. Bloomberg-terminal aesthetic with live indicator, 72-hour event log, topics with sentiment bars, reality/respect/divergence gap cards, 3 curated takes. Demonstrated the proprietary-data moat as a living dashboard.

5. **The rivalry card (ND vs USC, Jeweled Shillelagh)** — mythic header, 4-column meta strip, dual-trajectory heat chart with gap annotated, two posture-labeled panels with representative quotes, editorial last-ten meetings list, dual-perspective stakes footer. Demonstrated what the fan intel data can do when pointed at *two* fanbases at once.

6. **Historical season deep-dive (ND 2018 — "The Proof")** — archive eyebrow + nav, serif title + thesis, 5-column meta strip (record / final / AP / SP+ / era), retrospective shape viz with game-result cards + vertically-crashing mood curve ending at Cotton Bowl, three defining-moments cards color-coded by emotional register (blue switch / amber announcement / red gap), pull quote attributed to contemporaneous publication, legacy paragraph connecting forward to 2024 and backward to Kelly era pattern, bottom nav treating seasons as chapters in a series. Demonstrated the pattern for turning every CFP-era season into an immersive retrospective artifact.

7. **CFP-era multi-metric view (ND 2014–2026)** — era title + thesis, 5-column meta strip (record / CFP appearances / title games / top-10 finishes / titles), two-line trajectory chart (thick coral mood + thin navy AP rank) with CFP bids as vertical gold annotations, era ribbon beneath (Kelly / Freeman), 13-brick index below the chart mapping to season deep-dives, editorial closing paragraph framing the era's arc, three meta-context stats (SP+ avg rank, mood avg, gap-from-#1 closing). Demonstrated elegant multi-metric layering — hero metric + context metric + landmark annotations — following Economist/FT design discipline.

8. **The Chronicle module (ND week 3)** — four-card editorial intelligence module with distinct register per card type: The Anomaly (amber/historical, hero stat + 12-year comparison bar chart), The Moment (coral/social, platform velocity metrics + cultural comparison), The Flashpoint (navy/tactical, strength-on-weakness unit comparison), The Echo (gray/historical, cosine similarity across 20+ years of unit profiles with editorial legacy frame). Every card has source attribution, editorial voice, screenshot-native design. Demonstrated LLM-as-editorial-researcher at full ambition: Claude sweeping play-by-play, FI signals, cross-era vectors to surface observations that would require full-time beat writers to find manually.

9. **Mobile team page — top-of-page (ND 2026 week 3)** — 390pt viewport mockup demonstrating the full system's thumb-native translation. Team identity header, heritage strip, state-of-team serif paragraph, 2×2 metric grid (touch targets 48pt), horizontal-scroll schedule strip with current-week snap center, mood sparkline at full width, editorial story paragraph (narrower measure = better reading), "this week" callout, fade-to-more indicator listing what continues below. Footer codified six mobile design principles applied this pass.

10. **Seasonal sentience — four states (ND, same team, different moments)** — 2×2 grid showing the same page at post-loss Monday (red accent, Pulse promoted, wound-open register), pre-USC Friday (amber accent, Rivalry Card promoted, coiled register), mid-June dead period (gray accent, On-This-Day heritage promoted, patient register), and Selection Sunday (navy accent, CFP Projection promoted, held-breath register). Each state shares team identity skeleton but diverges in hero slot + copy register + accent color.

11. **Game recap mode — loss scenario (ND 17 USC 28, 2h 23m after final)** — the highest-stakes design moment in a fan's week rendered at full fidelity. Header signals the mood (red pulsing dot, rank-drop visible, "final 2h 23m ago"). State-of-team paragraph in post-loss voice ("the version of it you wanted is not"). Game-shape WP chart with 82% halftime peak and Q3 collapse, annotated on three inflection points. 4-stat diagnosis row (rush yds allowed, 3rd down, TO margin, 2nd half pts) selected by LLM from ~30 candidates by divergence from season baselines. Pulse live-loss mode showing real-time mood crash (89 → 38 in 3 hrs, 4.7x velocity, event-timestamped "what moved it" log). Chronicle game edition with 3 observations (anomaly: 223 rushing yds worst in Freeman era; echo: 7th straight road loss after halftime lead; retroactive: Miami concerns returned). CFP math revised (64% → 32%, if-win-out 71%) with calibrated paragraph. Footer tells fan when next update arrives. Demonstrated LLM-at-full-ambition: every module's copy generated 15-31 minutes after final whistle, no beat writer could produce this for 130 teams.

12. **Program-tier sentience (UMass comparison study)** — the macro principle that every module reshapes for the program it's rendering. UMass page at 3-2 rendered at full fidelity: team identity with SP+ instead of AP rank, serif state-of-team in scrappy-proud register ("three wins in five weeks is momentum here"), metric tiles with Bowl odds replacing CFP odds and improvement-vs-last-year replacing gap-from-#1, new aspiration ladder module (6/7/8/9 wins with odds and one-sentence context each — the "9+" rung dimmed as "locked/dreaming"), footer explaining what changed from the default contender template, and a program-profile JSON example showing the ~10 hand-curated fields that drive all adaptation. Key insight: the same design system handles UMass with equal editorial care as Alabama — the defensive brand position nobody else in CFB can match.

13. **Deep program profile — Vanderbilt case study** — the program profile elevated from ~10 fields to ~45-50 fields of hand-curated editorial research per team. Two-column document format showing left-column data paired with right-column "drives →" annotations that connect every profile field to the specific design decision it triggers in the rendered page. Sections covered: identity & heritage, coaching lineage, fans & culture, voice & ethos (the most load-bearing), rivalries by emotional weight, aspiration framework with unlock conditions. Closer showed what a handful of those fields look like when rendered for Notre Dame instead, demonstrating dramatic divergence from same architecture. Scale: ~4 hours Claude-assisted research + ~30 min editorial review × 130 programs = ~2 weeks focused sprint for full CFB library.

14. **Four-program payoff render (Alabama / Vanderbilt / UMass / Army)** — 2×2 grid proving the profile concept visually. Same components, same tokens, same rendering logic; four genuinely different pages produced by four different profiles. Each quadrant shows: program identity + record, one-line context, state-of-team paragraph in program-specific voice, aspiration ladder with 4 rungs (some locked/dimmed), identity phrase + mantra footer. Alabama's ladder runs "CFP → champion." Vandy's tops at "unprecedented." UMass's has 2 dimmed rungs. Army's is Beat-Navy-first then CiC-Trophy then AAC — a program-specific reordering that only human-curated profiles can produce. Footer: identical-vs-varies table making architecture visible.

15. **Savant card (ND 2026 through 2 games)** — the stat-density module for the deep-dive audience, last specified-but-unrendered module from original brief §5. Peer-set toggle (FBS / P4 / independents / ND all-time), LLM-written narrative header that makes the bars an argument not an inventory, 13 metrics grouped offense (6) / defense (5, all inverted with ↓ glyph + clarifier) / special situations (3). Ordering is narrative — best → interesting → concern — within each section. Echo callout in defense section referencing Chronicle's "2012 · 0.94 similarity" finding, tying Savant to Chronicle. Color-ramp legend at bottom. Source attribution.

16. **Full desktop composition (ND, week 3, standard in-season Tuesday)** — the design-concept capstone. Top-to-bottom scroll stitching all modules into one coherent page. Editorial-fidelity gradient: hero zone (team identity → heritage → state-of-team → season theater) at near-full density; below-fold modules progressively compressed but preserving visual DNA (Pulse keeps its live dot, Chronicle keeps its four color-accented card types, Savant keeps its percentile bars, Era view keeps its CFP-gold verticals). Eyebrow labels serve as self-orienting navigation at every section. Archive strip at bottom as 13-season index linking to deep-dive chapters. Whole page reads as one editorial product, not stitched-together features — the payoff of design-system work.

## Where we land

The design concept work is genuinely complete after this composition. Remaining work is production:

- **Editorial production:** write 130 program profiles (Vanderbilt done as case study; ~20 top programs as first-sprint target, then long tail)
- **Figma library:** build ~22-28 auto-layout components with viewport × priority × context variants, using design tokens established across these iterations
- **HTML/CSS implementation:** new `src/cfb_rankings/team_pages/` module reading from SQLite + profile files; separate from reporting.py
- **Content generation:** `manage.py generate-narratives` subcommand via Claude Code headless + Max subscription tokens; overnight batch for initial fill-up, incremental daily during season

Total timeline from concept-complete to shippable top-20 programs: ~4-6 weeks of focused solo work with AI assistance.

## The full module inventory at design-concept-complete

16 mockups produced:
1. 131-season hero Arc (historical-depth mode)
2. CFP-era 13-brick hero Arc (v1.0 scope)
3. Current-season theater view
4. The Pulse (live fan-intel module)
5. The Rivalry Card (ND × USC)
6. The Chronicle module (4 card types at full fidelity)
7. Historical season deep-dive (ND 2018)
8. CFP-era multi-metric view (mood + AP rank + CFP annotations)
9. Mobile team page top-of-page (390pt)
10. Seasonal sentience 4-states
11. Game recap mode (post-loss scenario)
12. Program-tier sentience (UMass adaptation)
13. Deep program profile (Vanderbilt case study, ~45-50 fields)
14. Four-program payoff render (Alabama / Vandy / UMass / Army)
15. Savant card (13-metric percentile module)
16. Full desktop composition (end-to-end scroll)

Plus frameworks documented:
- Seasonal sentience resolver (~10 named anchor variants + parameter overrides)
- Program-tier sentience resolver (10-tier taxonomy + dynamic unlock conditions)
- Tribal voice system (per-team vocab + era naming + mascot voice)
- Claude Code + Max subscription pattern for content generation
- Chronicle card type taxonomy (6 types with distinct visual treatment)
- Component inventory mapped to Figma auto-layout structure
- Editorial-vs-technical separation of concerns
- Screenshot-native design discipline throughout

## Savant card design principles

- **Narrative header > stat dump.** The LLM writes one sentence that tells the fan what the 13 bars say, before they parse any bar. Makes the card a piece of writing backed by data.
- **Narrative ordering within sections.** Best → strongest → most interesting → concerns. Reading top-to-bottom is the team's profile.
- **Inverted defense metrics labeled explicitly.** ↓ glyph + "harder to play against" framing removes the ambiguity that plagues sports analytics sites.
- **Peer toggle includes all-time program.** Unique to team pages — "how does this year's defense compare to ND defenses since 2010?" is a question no other site can answer. Feature, not commodity.
- **Modules reference each other.** Echo callout in defense section references Chronicle's cross-era finding. Savant isn't an island; it's part of the product.
- **Color ramp is legible.** Red-coral-gray-blue-deep-blue for crisis/concerning/middle/strong/elite. Legend at bottom makes encoding explicit.

## Module set now complete

With Savant rendered, every major module specified in original brief Part I (§3-§11) has a design mockup in the new language. Remaining "modules" to design are either variants (more Chronicle card types) or production work (composing assembled pages), not new conceptual ground.

## Where we are now — framework complete

After 14 mockups and ~15 conceptual frameworks documented, the team-page concept work is conceptually complete:

### What's proven
- Hero Arc visualization (131-season climate stripe + CFP-era 13-brick)
- Multi-metric era view
- Current-season theater
- The Pulse (live fan-intelligence module)
- Rivalry Card (dual-trajectory + editorial meetings)
- The Chronicle (LLM editorial observations, 4 of 6 card types)
- Historical season deep-dive (2018 prototype)
- Mobile translation (top-of-page proven)
- Seasonal sentience (4 states — day/week/year rhythm)
- Game recap mode (post-game emotional apex)
- Program-tier sentience (UMass adaptation)
- Deep program profile (Vanderbilt — 45-50 fields per team)
- Four-program payoff (Alabama, Vandy, UMass, Army)

### What's architecturally defined
- ~22-28 Figma components with viewport × priority × context variants
- `program_profiles.json` with ~45-50 hand-curated fields per program
- Seasonal sentience resolver (date signal + outcome signal → anchor variant + parameter overrides)
- Program-tier sentience resolver (tier baseline + current trajectory → module selection + aspiration framing)
- Claude Code + Max subscription for all LLM content generation
- Daily build cadence delivering "alive" feel without real-time infrastructure
- SQLite tables: team_season_narratives, team_eras, team_annotations, team_voice, team_chronicle_observations

### What's editorially defined
- Voice register taxonomy (~10 tones: dynastic, scrappy-proud, defiant-academic, disciplined-proud, etc.)
- Card-type taxonomy for the Chronicle (6 types: anomaly, moment, flashpoint, echo, retroactive, player-arc)
- Rivalry tiering within-program (1-7 rivalries per program)
- Aspiration ladder structure (3-5 rungs per program, locked/unlocked mechanic)
- Guardrails system (never-use + always-surface per program)

### What's remaining (operational, not conceptual)
- Full desktop composition stitching (visual capstone for Figma handoff)
- Savant card redesign (stat-density module for deep-dive audience)
- Remaining 2 Chronicle card types (Retroactive, Player Arc) at full fidelity
- Coaching tree / lineage module (one more distinctive data viz)
- Live gameday mode (deferred — no games for 3 months per Kevin's guidance)
- Write all 130 program profiles (editorial sprint, 2 weeks)
- Figma component library build-out (design production work)
- Translation to HTML/CSS in `reporting.py` templates

## Handoff readiness

The concept work is complete enough to begin Figma production. A reasonable next workflow:

1. **Kevin + Claude build Figma library** — 22-28 auto-layout components with all variant dimensions (viewport, priority, context). Tokens first, then atomic components, then module components, then page templates.
2. **Kevin seeds program profiles** — start with top-20 programs (~4 hours each with Claude research). UMass and Vandy are done via these iterations; ~18 more to build, then long-tail.
3. **HTML/CSS implementation** — new `src/cfb_rankings/team_pages/` module with templates reading from SQLite + profile files. Separate from `reporting.py` (17.5k lines — keep it out of there).
4. **Content generation pipeline** — `manage.py generate-narratives` using Claude Code headless, running overnight. Cached in SQLite.
5. **Iterative rollout** — top-20 programs first, then tier 1-5 (blue blood + P4), then full FBS.

Approximate timeline from concept-complete to shippable top-20-programs: 4-6 weeks of focused work (Kevin solo with AI assistance), conservatively.

## Deep program profile — principles

### The profile IS editorial infrastructure
Not metadata about the program — the document that directly drives every rendered design decision. Edit a field → the rendered output changes everywhere that field reaches. The profile is executable.

### Voice & ethos carries ~70% of the perceived quality
Five fields do most of the work:
- Identity phrase (opens every state-of-team)
- Mantra (signs off every state-of-team)
- Stock phrases (verbatim in specific moments)
- Never-use guardrails (negative-space protection)
- Always-surface positives (positive-space emphasis)

Nail these for every program; the rest can be 80% right and the product still reads as bespoke. Miss these; no amount of good design saves the page.

### Guardrails matter as much as prompts
The "never use" list protects the product from tropes that would alienate the fanbase. Rocky Top inversions on a Vandy page, "cute underdog" on a ND page, "David vs Goliath" on a Kent State page — fans notice wrong vocabulary instantly and close the tab. Guardrails are infrastructure.

### Realistic vs. dream is psychologically load-bearing
Baseline + ceiling + dream-ceiling, each annotated with historical context, lets the fan calibrate their expectations without being condescended to or over-promised. The page sits next to them at the right distance.

### Unlock conditions make the profile dynamic
`8 wins OR SP+ rank ≤ top-half-of-SEC` for Vandy → promotes contender-view modules. Static profiles with dynamic overrides. The program is characterized by its baseline, but the current season can legitimately transcend it.

## Profile sections (full list)

A complete program profile has roughly these sections (~45-50 fields total):

1. **Identity & heritage** — founding, conference history, titles, stadium, uniform traditions, historic ceiling references
2. **Coaching lineage** — cornerstone coach, modern high-water, wounds, current, legendary assistants
3. **Notable players** — Heismans, HOFers, recent standouts, by position group
4. **Fans & culture** — archetype, geography, size, gameday register, tailgate culture
5. **Voice & ethos** — identity phrase, mantra, stock phrases, never-use, always-surface, tonal template
6. **Rivalries** — tiered list with proper-noun names, all-time records, emotional weight
7. **Current context** — coaching staff, AD, NIL collective, facilities, conference positioning
8. **Program narratives** — ongoing storylines, portal/NIL era position, identity crisis flags
9. **Aspiration framework** — baseline / realistic ceiling / dream ceiling / historic ceiling / unlock conditions
10. **Chronicle tuning** — what counts as anomaly for this program, what observations resonate, what retrospective insights are available
11. **In-jokes & copypasta** — the stock phrases fans use, for authenticity in generated copy
12. **Taboos & sensitivities** — raw wounds, topics that cause backlash, competitive insecurities

Stored as structured markdown or JSON per program in `profiles/<program_slug>.md`. Rendered into page as data-source reference. Editable like any content file.

## Program-tier sentience — the macro principle

**Every module has three variant dimensions now:**
- Viewport (desktop / mobile)
- Priority (hero / scroll / hidden)
- **Program-tier** (tier-baseline / tier-unlocked)

**Tier taxonomy (1-10):**
1. Blue bloods (Alabama, Ohio State, Georgia, Texas, Michigan, Notre Dame, Oregon)
2. Established P4 (Oklahoma, LSU, USC, Penn State, Florida, Auburn)
3. Rising P4 (Indiana recently, SMU recently, Kansas recently)
4. Mid P4 (most conference teams)
5. Lower P4 (Vandy, Purdue lately, Rutgers)
6. Top G5 (Boise, Memphis, Liberty, UNLV, Tulane)
7. Solid G5 (JMU, App State, Coastal, Louisiana, Toledo)
8. Middle G5 (most MAC, most Sun Belt mid-tier)
9. Low G5 (UMass, Kent State, New Mexico State)
10. FCS (if ever covered)

**What success means per tier (for aspiration-ladder generation):**
- Tier 1: CFP semifinal / title game / national champion
- Tier 2: CFP appearance / conference title / 10-win season
- Tier 3-4: 9-win season / bowl win / beat rival
- Tier 5: bowl eligibility / beat rival / exceed last year
- Tier 6: conference title / NY6 bid / top-25 finish
- Tier 7: bowl win / conference contention
- Tier 8: bowl eligibility / exceed last year
- Tier 9: any winning season is historic / beat rival
- Tier 10: beat nearest FBS neighbor

**What adapts in each module:**

| Module | Contender (tier 1-2) | Mid (tier 3-5) | Non-contender (tier 6-10) |
|---|---|---|---|
| Metric tiles | AP / SP+ / CFP odds / record | SP+ / record / bowl odds / conf rank | Record / SP+ / bowl odds / mood |
| Aspiration ladder | Semifinal → champion | 8 wins → conf title → CFP buzz | 6 wins → exceed last year → statement year |
| State-of-team register | Dynastic / expectant | Proving / grinding | Scrappy / proud / incremental |
| Chronicle observations | Era-relative peaks | Program-relative progress | Program-historic progress |
| Top-25 opponent framing | Expected weekly | Occasional highlight | Rare, amplified |
| CFP math | Always | Conditional (if realistic) | Hidden unless unlocked |
| Rivalry weight | High | Very high | Highest (season's biggest stakes) |
| Heritage strip | Titles, Heismans, legendary coaches | Conference titles, notable alums | Founding year, FBS-era milestones, FCS titles if applicable |

**Dynamic unlock conditions (override baseline tier):**
- `wins >= 1.5 × baseline OR sp+_rank <= (tier_expected - 20)` → unlock higher-aspiration modules
- `wins <= 0.5 × baseline OR sp+_rank >= (tier_expected + 20)` → hide aspirational modules, promote rebuilding-frame
- Rivalry week always overrides weight regardless of tier
- Heritage anniversary (e.g., "25th anniversary of 2003 FCS title" for UMass) unlocks heritage-promoted layout for a week

**Implementation artifact:** `program_profiles.json` — one entry per program, ~10 hand-curated fields. 130 programs × ~10 fields = ~1,300 data points. One weekend of editorial work for full coverage. Reviewed every 2-3 years when programs fundamentally reposition.

## Brand position unlocked by program-tier sentience

Competitors that fail at this specifically:
- **Sports-Reference**: identical template for every program; UMass page visibly lower-effort than Alabama's
- **ESPN**: UMass basically doesn't exist; their page is a stub
- **The Athletic**: doesn't cover UMass at all
- **247/On3**: recruiting-focused; treats non-P4 as footnote
- **Team official sites**: limited to merchandise and press releases

The position CFB Index can own: **"the only site that takes every team seriously at that team's own level of stakes."** That's a defensible moat that competitors can't match without rebuilding their editorial product from scratch.

## Game-recap mode design principles

- **Honest register, not performative.** "The version of it you wanted is not" is the tone — truth-first, hope qualified, nobody panicking or maintaining.
- **The WP chart is the spine.** A loss page with a big WP swing tells the story better than any paragraph. Peak + pivot + seal — three annotations are enough.
- **Stats selected, not dumped.** LLM picks the 4 stats that diverge most from season baselines. Different games surface different diagnosis stats. Every recap is tailored.
- **Pulse in live mode shows the *during*.** Mood didn't crash in post — it crashed while the page was rendering. Event-timestamped deltas show the emotional arc of the fanbase *as it happened*.
- **Chronicle does three different analytical tasks.** Anomaly detection + pattern-streak detection + retroactive-linking. Running in parallel, all completing in 30 min.
- **CFP math in human language.** "Not closed. Not open either" — calibrated, not spun.
- **Demotions matter as much as promotions.** Rivalry card gone (game happened), schedule reduced to one-line footer, Arc invisible. The page knows this moment isn't about where the program sits.
- **Footer tells fan to come back.** "Next update 6am Sunday · full recap Monday 10am" — the product commits to developing the story with the fan across the 48 hours.

## LLM workload per game recap (fanning out from final whistle)

Triggered by final-score ingest at ~T+5 min:
- **T+15:** state-of-team paragraph (post-loss-sunday-monday template + game facts)
- **T+20:** 4-stat diagnosis row (divergence ranking from ~30 candidates + captions)
- **T+25:** Chronicle anomaly + retroactive cards (stat-anomaly detection + cross-week linkback)
- **T+30:** Chronicle echo card (streak pattern detection across seasons)
- **T+35:** CFP math paragraph (forecast model delta + calibrated language)
- **T+40:** "What moved it" summary paragraph
- Page republishes by T+45

All via Claude Code + Max subscription. Runs in parallel across 65 programs on a given Saturday. Max budget: trivial.

## Seasonal sentience implementation summary (revised after Kevin challenged the 10-variant count)

The honest count is closer to ~28-32 distinct states. But architecturally, most aren't bespoke templates — they're the same template with three parameters overridden. Revised model:

### Three parameters drive every state

1. **Hero-priority rule** — which module claims the top slot. ~8 options:
   - Pulse / Rivalry Card / Heritage / CFP Projection / Chronicle / Schedule-next / On-This-Day / Portal-Tracker
2. **Copy tone** — which voice-template the state-of-team paragraph draws from. ~10 options:
   - wound / coiled / basking / patient / reckoning / euphoric / anxious / held-breath / optimistic / resolute
3. **Accent color** — the emotional key. ~6 options:
   - red / amber / navy / gray / coral / green

That's ~480 theoretical states from three parameters. Reality is much fewer (not all combinations are valid or sensible), but the expressive range is vast.

### Named anchor variants (~10-12, editorially reviewed)

These are the reference designs. Each one gets explicit editorial treatment so the voice lands right:

1. standard-in-season-midweek (Tue–Thu baseline)
2. standard-friday (anticipation building)
3. rivalry-week-friday (amplified anticipation)
4. gameday-pre-kickoff (Saturday morning)
5. post-win-sunday-monday (basking + validating)
6. post-loss-sunday-monday (reckoning + processing)
7. post-upset-win (explosive; Chronicle dominates)
8. post-close-loss (honest, what-if register)
9. selection-sunday (projected / bubble / out — three sub-variants)
10. dead-period-summer (June heritage-forward)
11. camp-open (August optimism-building)
12. portal-window-active (Dec + April)

### Emergent states (~20+ additional)

Formed by combining anchor modes with contextual overrides:
- Post-win + top-10 opponent = amplified basking
- Post-loss + rivalry = wound + identity-reckoning
- Bye week + in-season = schedule-demoted, Chronicle-promoted
- Road trip + top-25 opponent = logistical + matchup hybrid
- Rivalry week + heavy underdog = coiled + grievance register

Unlimited further emergent states as parameter combinations. The system never fails to render something appropriate because the parameters are always defined.

### Implementation artifact

`team_page_state_resolver.py` runs at each daily build:
1. Read today's date → resolve season phase (offseason-sub-state / in-season-day-of-week / postseason-week)
2. Read last game outcome + context (win/loss × blowout/close × top-N opponent × home/away)
3. Resolve to named anchor mode + apply contextual overrides
4. Emit state object: `{hero_module, copy_tone, accent_color, promoted_modules[], demoted_modules[]}`
5. Template renders page with that state object

One JSON config file (`team_page_anchors.json`) defines the 10-12 anchors. Overrides live in Python logic. Adding new anchors is cheap; the system is extensible.

## Figma variant dimensions (updated)

Each module component now has three variant dimensions:
- **Viewport**: desktop / mobile
- **Priority**: hero / scroll
- **Context**: default / post-win / post-loss / rivalry-week / offseason (not all modules have all context variants — most have 1-2)

Total variant count per module: ~2 × 2 × 2 = 8 to 12 variants. Still manageable.

## Mobile findings codified

- **Editorial voice gets better on narrow viewports.** Serif paragraphs read like magazine columns at ~60 char/line. Lean into it.
- **Horizontal scroll for timelines is thumb-native.** Schedule strip on mobile is superior to desktop — snap-center on current week, swipe through season naturally.
- **Touch target discipline:** 44pt minimum, 48pt for frequently-tapped elements (metric tiles), 60pt for schedule cards.
- **Grid-to-stack rules:** 4-col → 2×2, 3-col → 1-col stack, 2-col → 1-col stack. Spacing rhythm preserved.
- **Type scales in steps, not fluidly:** 22→20 identity, 18→18 editorial headlines (no shrink for serif), 16→14 body serif, labels stay 10-11.
- **Every module fits portrait screenshot within one thumb-length of scroll.** Distribution channel is iMessage; every module is built for iMessage.

## Figma component inventory (provisional)

Across the full team page, ~22-28 Figma auto-layout components, each with desktop and mobile variants sharing design tokens. Grouped:

**Atomic:**
- ColorToken, TypeToken, SpacingToken, RadiusToken (design system foundation)

**Small components:**
- Eyebrow (uppercase small-caps label)
- MetricTile (stat + label + delta)
- StatPill (inline stat with context)
- BadgeChip (characterization tag: "the axis" / "revenge" / "trap")
- PullQuote (serif blockquote with attribution)

**Module components:**
- TeamIdentityHeader
- HeritageStrip
- StateOfTeamParagraph
- MetricTileGrid (2/3/4 tile variants)
- ScheduleStrip (horizontal-scroll variant + desktop grid variant)
- MoodSparkline
- ThisWeekCallout
- ArcHeroStripe (131-season variant + 13-season brick variant)
- EraRibbon
- SeasonBrickIndex
- TrajectoryChart (two-line hero + context variant)
- PulseModule (composite of MoodSummary + EventLog + TopicsBar + GapCards + TakesGrid + ConversationFooter)
- RivalryCard (composite of MythicHeader + MetaStrip + DualTrajectoryChart + PosturePanels + MeetingsList + StakesFooter)
- ChronicleCard (6 variants: Anomaly / Moment / Flashpoint / Echo / Retroactive / PlayerArc)
- SeasonDeepDive (composite for historical season full-width treatment)
- CFPEraView (composite for era-level multi-metric view)

**Page-level:**
- TeamPageDesktop (composition of all modules)
- TeamPageMobile (same composition, mobile variants)

Maintenance surface: one set of tokens, one library of components, two page variants per team (desktop + mobile) rendering identically because components handle their own responsive behavior.

## The Chronicle as reusable pattern

Works at three altitudes with the same architecture:
- **Weekly Chronicle** — this week's 5 most interesting observations (in-season module)
- **Seasonal Chronicle** — the 10 discoveries that defined a given season (lives inside historical season deep-dive)
- **Era Chronicle** — the 20 observations that characterize an entire era (lives inside CFP-era view)

Generation pattern: `manage.py generate-chronicle` subcommand pulls week/season/era data, runs stat engine to produce ~1,000-5,000 candidate anomalies with oddity scores, feeds structured prompt to Claude via Claude Code headless, Claude ranks by reader-surprise and writes top-K in editorial voice. The raw ratio (~1% of candidates ship) means the LLM's real work is ranking + voice, not observation generation. This is the job no human beat writer has time to do weekly for every program.

## Card-type taxonomy for observations

Claude classifies each candidate observation into one of ~6 types, each getting its own visual treatment:

1. **Anomaly** — statistical outlier vs. historical distribution (amber accent)
2. **Moment** — cultural/social velocity signal (coral accent)
3. **Flashpoint** — next-opponent matchup intelligence (navy accent)
4. **Echo** — cross-era similarity or parallel (gray accent)
5. **Retroactive** — recontextualization of an earlier game/moment (purple accent, reserved)
6. **Player arc** — individual trajectory within a cohort comparison (teal accent, reserved)

Widget prototype showed 4 of the 6 types. Next iteration could demonstrate the full 6-card range on a single page.

## Design principles codified from the multi-metric work

- **One hero metric per chart.** Others exist as context.
- **Visual hierarchy via line weight.** Thick = hero; thin = supporting; vertical accents = landmarks.
- **Annotations on the chart, not in a legend.** FT discipline.
- **Endpoint labels only.** No label per data point.
- **Sparse gridlines.** Three at most. Dashed and muted.
- **Whitespace is the design.** Let the silhouette breathe.
- **Color for meaning, not decoration.** Same two or three colors used consistently across all modules so the system reads coherent.
- **Extensible in both directions.** Era view (years) and season view (weeks) use the same grammar at different altitudes. Works for cross-program comparisons too.

## Technical architecture update — Claude Code on Max

Pattern confirmed workable:
- New `manage.py generate-narratives` subcommand
- Pulls season data from SQLite → builds prompt → subprocess-invokes Claude Code in headless mode → reads response → writes generated content to `team_season_narratives` table
- Uses Max subscription tokens, not API billing
- Initial bulk generation (~1,700 CFP-era season units) runs overnight
- Incremental updates during season take minutes
- Falls back to direct API only for large prompt-rewrite operations if needed

Caveats:
- Max subscription fair-use — spread initial bulk across several days to be safe
- Claude Code headless is slower per call than API (seconds of setup overhead)
- Model selection constrained to what Max provides (generally Sonnet, Opus for harder tasks)

Net: content generation is effectively free going forward. Design ambition can scale up accordingly — richer annotations, deeper per-season narratives, weekly refreshed copy site-wide.

## Next iterations queued (updated)

- **Seasonal sentience 4-state mockup** — same ND page at 4 contrasting moments (post-loss Monday, pre-USC Friday, mid-June dead period, post-bowl Wrapped Monday). Proves the ebb-and-flow concept.
- **Historical season deep-dive upgraded** — ND 2018 with multi-metric layering (weekly AP rank + weekly SP+ + weekly mood all aligned). Apply the era-view design discipline to the within-season view.
- **Mobile end-to-end pass** — stitch everything to 390-wide phone viewport.
- **Savant card redesign** — complete the module set for data-density audience.
- **Full desktop composition** — stitch all modules into a single top-to-bottom scroll for Figma handoff.

## Kevin quotes added this turn

- "the archive to not just chart fanbase mood, but also like the team's weekly ranking, team quality by week, etc. in an incredibly elegant world-class design way somehow"
- "keep iterating and refining this season idea and also a 2014-present view that applies all our thoughts and considerations"
- "i could process all these anthropic calls directly thru claude code so i can use the tokens from my claude max membership"

## Figma file initiated — 2026-04-23/24

File created: https://www.figma.com/design/eGIVOKDIFSmo1yM1LShLQx (Kevin's team, name "CFB Index — Team Page Design System").

Pages structured: Cover / 01 · Tokens / 02 · Atoms / 03 · Modules / 04 · Pages — Desktop / 05 · Pages — Mobile / 99 · Sandbox.

### Figma MCP persistence finding

Discovered that the Figma MCP (via `use_figma`) has a persistence quirk: mutations to pages OTHER THAN the first (Cover) don't reliably persist between `use_figma` invocations. Writes to Cover page persist cleanly. Writes to Tokens/Atoms/Modules pages get silently rolled back.

Workaround: all design content currently lives as sibling frames on the Cover page. "Cover · v0.1" at x=0 (file-level title + TOC), "Tokens · v0.1" at x=1600 (the tokens canvas). Future sections (Atoms, Modules, Pages Desktop, Pages Mobile) will also be Cover-page siblings, positioned horizontally.

Kevin can manually reorganize frames into proper pages once he opens the file in his own Figma session (user-session mutations likely don't hit the same bug).

### Built so far

**Cover · v0.1 (1440 × 1024, node 1:8)** — file identity, eyebrow, title "CFB Index", subtitle "Team page design system", navy divider, description paragraph citing companion docs, TOC header, 6-row page index, footer. TOC rows persisted as nodes but auto-layout collapsed them visually — needs sizing fix.

**Tokens · v0.1 (1840 × 3500, node 28:2)** — the design tokens canvas with six sections:
- Page header (eyebrow + title + intro)
- Color palette: 6 ramps × 7 stops = 42 swatches with hex + stop labels
- Usage rules (6 bullets on how colors get applied)
- Typography scale: 9 sizes (Display serif, Headline serif, Subhead italic, Headline sans, Body serif, Body sans, Label medium, Caption, Micro)
- Spacing rhythm: 9 tokens (sp-1 through sp-24) with visual bars
- Corner radii: 5 tokens (sm/md/lg/xl/full) with rounded squares
- Stroke weights: 3 tokens (hair/std/heavy)
- Footer note about tokens.css export

Serif resolved to Source Serif Pro (Figma loaded it automatically — Lora/Playfair were attempted but Source Serif Pro was first match).

## Autonomous sprint completed 2026-04-24 overnight

While Kevin slept, executed the following:

### Program profiles (8 new)

Written as markdown files in `profiles/` directory matching the established YAML-frontmatter-plus-narrative format:

- **notre_dame.md** (tier 1, dynastic-with-question-mark) — 11 titles, 7 Heismans, 38-year drought framing
- **ohio-state.md** (tier 1, dynastic-industrial) — 8+ titles, 7 Heismans, 2024 title, Michigan rivalry axis
- **georgia.md** (tier 1, dominant-hungry) — 4 titles, back-to-back 2021-22, Kirby Smart dynasty
- **michigan.md** (tier 1, proud-institutional) — 12 titles, 2023 title, Harbaugh→Moore transition, sign-stealing cloud
- **texas.md** (tier 1, confident-texan) — 4 titles, 2005 Vince Young peak, 2010s collapse, Sarkisian restoration
- **oregon.md** (tier 2, innovative-fashion-forward) — 0 titles, Chip Kelly revolution, Big Ten arrival
- **usc.md** (tier 1, hollywood-dynastic) — 11 titles, Carroll dynasty, post-sanctions wilderness, Riley restoration
- **penn-state.md** (tier 2, blue-collar-dynastic) — 2 titles, Paterno legacy, Franklin era "can he win the big one" question

Existing profiles remain: alabama.md, vanderbilt.md, massachusetts.md.

Total: 11 program profiles complete (10 unique programs; notre-dame.md and notre_dame.md are duplicates — kept both since the delete operation wasn't available, content is nearly identical).

### Brief Part III — major integration update

Appended Part III (§32-§41) to `TEAM_PAGE_WORLD_CLASS_BRIEF.md`. Covers:

- §32 Seasonal sentience — temporal ebb-flow with two nested clocks and ~10 named anchor variants
- §33 Program-tier sentience — 10-tier taxonomy, per-module adaptation matrix, dynamic unlock conditions
- §34 Program profiles — editorial infrastructure, 45-50 field structure, voice & ethos as load-bearing
- §35 Game recap mode — Saturday-night apex, LLM pipeline T+5 through T+45
- §36 Chronicle module — 6 card types, three-altitude architecture (weekly/seasonal/era), Haiku→Sonnet→Opus routing
- §37 Claude Code + Max — model routing rules, subcommand pattern
- §38 Figma component inventory — tokens + ~10 atoms + ~22 modules + 2 page templates
- §39 Brand position — "only site that takes every team seriously at its own level"
- §40 Revised operational roadmap — 6 phases from foundation to community + offseason
- §41 Part III summary — five macro principles that now govern the design

### Design specs written for Claude Code implementation

Created `docs/design-system/` directory with implementation-ready specs:

- **00-tokens.md** — Complete CSS custom properties for colors, typography, spacing, radii, strokes, dark-mode variants, program-variable tokens via data-attr
- **01-atoms.md** — Atomic components: Eyebrow, MetricTile, BadgeChip, PullQuote, AspirationRung, EventLogItem, PercentileBar, LiveDot, DividerRule (with HTML + CSS for each)
- **10-modules-hero.md** — TeamIdentityHeader, HeritageStrip, StateOfTeamParagraph, MetricTileGrid (with program-tier variants)
- **11-modules-season.md** — ScheduleStrip, MoodSparkline, ThisWeekCallout, AspirationLadder
- **12-modules-intel.md** — PulseModule, ChronicleCard (6 variants) + ChronicleModule, RivalryCard, SavantCard
- **13-modules-archive.md** — CFPEraView, HistoricalSeasonDeepDive
- **14-modules-game-recap.md** — GameRecapHero composition, LLM generation pipeline timing, Pulse-live-loss-mode + CFPMathRevised + NextGameFooter, state-resolver activation logic
- **20-page-compositions.md** — Full desktop + mobile compositions, component swaps per state, program-tier swaps, build-time rendering pipeline

Each spec contains: HTML template outline, CSS with token references, data contracts, variant rules, generation logic where LLM-driven.

### Claude Code sprint prompt

Created `CLAUDE_CODE_TEAM_PAGE_SPRINT.md` at the root — a comprehensive autonomous engineering sprint prompt Kevin can paste directly into Claude Code. Covers:

- 12 reference documents to read first
- 15 deliverables across 5 phases (infrastructure → templates/styles → content generation → ND end-to-end → fan out to 10 profiled programs)
- Model routing rules (Opus/Sonnet/Haiku) with explicit decision authority
- Self-verification checklist
- Report-back format with 8 required elements
- Fallback options if sprint completes early

Expected runtime: 6-12 hours autonomous in Claude Code. Token budget: ~500k Max tokens.

## Where the product is now

**Design concept:** complete, documented, committed to Part III of brief.

**Editorial content:** 10 full program profiles written (covering tier-1 through tier-9 representative programs). Remaining ~120 profiles = ~2 weeks of editorial work via Claude Code.

**Design system:** Figma file with tokens page live; atoms + modules + pages pending. Full implementation specs written as markdown.

**Engineering:** Ready for Claude Code sprint. Prompt self-contained. Expected to ship ND + 9 other teams end-to-end after sprint.

## Remaining work for next Cowork session with Kevin

1. **Review Claude Code sprint output** — screenshots of 10 generated team pages; voice assessment; layout verification.
2. **Figma file expansion** — Atoms page, Modules page, Desktop + Mobile page compositions. Requires user-session Figma access or accepting the Cover-page-sibling-frames workaround documented earlier.
3. **Program profile expansion** — remaining 120 profiles. Batched via Claude Code headless + editorial review pass.
4. **Live gameday mode** — deferred per Kevin's note (no games for 3 months).
5. **Community annotation layer** — P3 work, lower priority.

## Figma file state at end of autonomous sprint

`https://www.figma.com/design/eGIVOKDIFSmo1yM1LShLQx`

Three frames on Cover page (all as siblings due to MCP persistence quirk):

1. **Cover · v0.1** (node 1:8, 1440 × 1024) — file identity, title, description, table of contents, footer. Persistent. Some TOC rows collapsed visually — needs sizing fix in user session.

2. **Tokens · v0.1** (node 26:2 or 28:2 depending on rebuild state, 1840 × 3500) — complete design token canvas: 6 color ramps × 7 stops, typography scale (9 sizes, Source Serif Pro resolved as serif), spacing rhythm (9 tokens with visual bars), corner radii (5 tokens with rounded squares), stroke weights (3 tokens). Usage rules bulleted. Footer about tokens.css export.

3. **Notre Dame · Desktop Hero** (node 32:2, 1440 × 920) — real in-context team page hero mockup using the tokens. Contains: TeamIdentityHeader, HeritageStrip, StateOfTeamParagraph, MetricTileGrid (4 tiles), ScheduleStrip (12 games with correct characterization chips), MoodSparkline (24-bar visualization), ThisWeekCallout, scroll-continues footer listing below-fold modules. All text content real for ND 2026. Some module heights needed explicit fixing due to MCP-context auto-layout computation; content persists at correct heights now. Screenshot rendering via MCP is unreliable but Figma editor will show fully in user session.

## Deliverables recap — what Kevin wakes up to

### New files created
- `profiles/notre_dame.md` (my version, also exists as notre-dame.md with opus-authored version)
- `profiles/ohio-state.md`
- `profiles/georgia.md`
- `profiles/michigan.md`
- `profiles/texas.md`
- `profiles/oregon.md`
- `profiles/usc.md`
- `profiles/penn-state.md`
- `docs/design-system/00-tokens.md`
- `docs/design-system/01-atoms.md`
- `docs/design-system/10-modules-hero.md`
- `docs/design-system/11-modules-season.md`
- `docs/design-system/12-modules-intel.md`
- `docs/design-system/13-modules-archive.md`
- `docs/design-system/14-modules-game-recap.md`
- `docs/design-system/20-page-compositions.md`
- `CLAUDE_CODE_TEAM_PAGE_SPRINT.md` (root — the next engineering sprint prompt to paste into Claude Code)

### Updated files
- `TEAM_PAGE_WORLD_CLASS_BRIEF.md` — appended Part III (§32-§41) integrating all post-Part-II refinements
- `TEAM_PAGE_ITERATION_LOG.md` — this document, fully updated

### Figma file
- Cover page with identity + TOC
- Tokens canvas (full)
- Notre Dame hero mockup (real in-context example using the tokens)

### Next move for Kevin
Open `CLAUDE_CODE_TEAM_PAGE_SPRINT.md` and paste into Claude Code to kick off the autonomous engineering sprint. Expected runtime 6-12 hours; expected output: Notre Dame + 9 other programs' team pages rendering end-to-end with real data, real voice, real chronicle content.

### Known visual issues to refine

- Cover TOC rows collapsed to 6px tall — row auto-layout needs fix so children's text sets row height
- Some typography preview rows may be visually thin
- Ramp-row labels (Navy, Coral, etc.) may need width/color adjustments for legibility at file-zoom levels
- Corner radii and stroke weight visuals are small — may want larger visual samples

### Next Figma steps

- Fix Cover TOC rendering
- Atoms page: MetricTile, BadgeChip, Eyebrow, PullQuote, DividerRule
- Modules page: start with TeamIdentityHeader + StateOfTeamParagraph + ScheduleStrip as highest-impact
- Page templates: desktop + mobile for one team (ND)

All subsequent work continues as Cover-page siblings until Kevin verifies the persistence behavior in his own session.

## The link between live + historical + seasonal sentience

The current-season theater view and the historical season deep-dive are the *same skeleton in different tenses*. As a season progresses into the past, the live version transforms into the historical version:
- Projected mood (dashed) becomes determinate mood (solid)
- "This week" callouts get archived as weekly bookmarks within the season
- The legacy paragraph (initially empty or aspirational) gets written after the bowl game
- Defining moments get nominated during the season and locked after it

The weekly rhythm (Mon licking wounds → Fri game focus) lives *above* the season unit as a template-selection layer. Same modules, reshuffled priority by day-of-week and outcome-context. Post-loss Monday promotes the Pulse (what the fanbase is doing with this). Friday-before-big-game promotes the next-opponent hero + rivalry card. Mid-summer promotes heritage + portal + recruiting. The page is one skeleton with ~8–10 template-variant rules choosing which bones are loud.

## Refinements to integrate into the brief

1. **Frame slot flex** (Conference / Division / Independent Resume) replaces §10 Conference Lens.
2. **Program-local rivalry tiering** (3–7 rivalries per program, internal tiers) replaces the "3-4 featured" global rule.
3. **Pre-modern season treatment** (honors-weighted, not SP+) — deferred to future v2 via scope decision.
4. **Seasonal sentience as first-class feature** (new concept, promote to §X in brief).
5. **"View from here" strip** — external CFB context through this program's lens, replacing generic news river.
6. **Heritage compact strip** — one-line program silhouette preserved above the fold.
7. **Legendary-season canon cards** — top ~5–10 all-time seasons per program get distinguished-card treatment even in v1.0.
8. **Share-card engine in `src/cfb_rankings/share_cards/`** — not jammed into `reporting.py`.
9. **Three new SQLite tables**: `team_eras`, `team_annotations`, `team_voice`. Plus new `team_season_narratives` table for the LLM-generated season units.
10. **Anthropic API budget** — ~$300–500 one-time for initial generation, pennies per week for incremental (reduced to ~$30–80 one-time under CFP-era scope).
11. **Daily build cadence** delivers "live" feel without real-time infrastructure.

## Open questions

1. The two model visualizations — does the CFP-era 13-brick Arc *fully* replace the 131-bar climate stripe for v1.0, or does the stripe survive as a compact heritage flourish? (Probably: compact stripe in heritage strip, brick strip as primary.)
2. Era-adjustment composite weights for when historical depth comes back in v2.
3. Should the pulse module's curated quotes be attributed to individual handles, anonymized as "from r/cfb," or attributed to source-tier only? (Current default: venue + signal rank, no individual handles.)
4. Seasonal sentience template — how many discrete "modes" should exist? (Current thinking: 4 seasonal modes × 7 day-of-week modes during fall = 28 potential states, but many are near-identical. Need to categorize into ~8–10 effective template variants.)
5. Historical season deep-dive — how much editorial polish vs. LLM-generation? (Probably: top-20 programs × 10 CFP-era seasons = 200 hand-polished; rest generated + lightly reviewed.)
6. Rivalry card — does the dual-trajectory chart always fit or do we need a compact variant for non-Tier-1 rivalries? (Probably compact variant without trajectory, just meta + last-ten + stakes.)

## Next iterations queued

- **Seasonal sentience mockup** — show the same ND page at 4 different moments: post-loss Monday, pre-USC Friday, mid-June dead period, post-bowl Wrapped day. One widget with 4 mini-states.
- **Historical season deep-dive** — ND 2018 "The Proof" rendered at full fidelity.
- **Mobile end-to-end pass** — stitch everything to 390-wide phone viewport.
- **Savant card redesign** — complete the module set for data-density audience.
- **Full desktop composition** — stitch all modules into a single top-to-bottom scroll for Figma handoff.

## Key Kevin quotes (direction-shaping)

- "best in class visualization of what it's like to actually follow the team or the sport"
- "boots on the ground feel and emotional attachment to theater of the season"
- "it needs to work for casuals, hardcore fans, data viz nerds"
- "I want this to be a site for the new generation of cfb fan who has twitter open and group texting while half watching games"
- "I like it just as an abstract paradigm to view the feel and intent of what we're going for. The structure can easily not be a 1-to-1 replica of any of these other forms"
- "make it amazing on mobile"
- "I want figma to really get pushed to its limits"
- "I want to continue focusing also on our proprietary data / fan intelligence advantage since we'll be getting tons of new data like weekly"
- "the pages to feel alive and like a part of the conversation"
- "the page should also be alive and ebb and flow depending on time of year… during season each week is different"
- "contextualize a team's history (with tons of data from 2014 onwards) in a similar way to what we're doing here"
- "start documenting all your thoughts in case our convo gets compressed"

## Session timestamps

- 2026-04-23 afternoon: initial brainstorm + competitor framing + metaphor discussion (concluded: inherited narrative *standards*, not literal costumes)
- 2026-04-23 late afternoon: ND stress test + 131-season Arc mockup + scope discussion
- 2026-04-23 evening: CFP-era scope locked + 13-brick Arc + current-season theater + Pulse module + ND-USC rivalry card
- 2026-04-23 night: seasonal sentience + historical deep-dive concepts raised; this log initialized
- 2026-04-24 morning: overnight autonomous sprint completed (see §Autonomous sprint completed)
- 2026-04-24 midday: Claude Code sprint 1 + sprint 2 shipped (11 world-class pages, Savant + Rivalry modules, `--llm claude` swap, `build-site` integration)
- 2026-04-24 afternoon: clobber hotfix (`PROFILED_SLUGS` guard in `reporting.py`) + Claude Code sprint 3 kickoff (CFP-era Season Arc + profile coverage expansion)

## Figma work parallel to sprint 3 — 2026-04-24

While Claude Code executes sprint 3 engineering, Figma captures design-of-record so the spec and the code don't drift.

### Notre Dame · Mobile · v0.1 (task #29 — complete)

- Frame: Cover-page sibling at x=7500, 390 × 3191
- 15 modules stacked: status-bar chrome → hero (eyebrow, wordmark, record, identity phrase, rank chips) → heritage strip (horizontal scroll hint) → state-of-team (serif) → metric tiles 2×2 (CFP odds / SP+ / momentum / portal net) → schedule strip (6 cards with swipe hint; current week accent-bordered) → mood sparkline (20-bar gradient) → this-week callout (gold 2px stroke) → pulse (live dot + mood card + 2 takes) → chronicle (flashpoint hero + anomaly mid + echo mid) → rivalry card (USC dual-posture + 10-meeting W/L dots) → savant (5 percentile bars) → aspiration ladder (active rung + locked rung) → CFP-era condensed bar chart → footer
- Proves mobile adaptation rules from `docs/design-system/20-page-compositions.md`: MetricTileGrid 1×4 → 2×2, ScheduleStrip horizontal scroll, ChronicleModule 3-col → single column, Pulse `__mid-grid` 2-col → 1-col
- Resolves the mobile-composition gap flagged in the overnight sprint summary

### Notre Dame · CFP-Era Season Arc · v0.1 (task #33 — complete)

- Frame: Cover-page sibling at x=8200, 1040 × 1067
- Spec source: `docs/design-system/13-modules-archive.md` §CFPEraView
- Structure: eyebrow + serif "The CFP Era" title + serif-italic thesis → 5-column meta strip (record · CFP bids · title games · top-10 · titles) → chart frame (mood coral polyline + AP navy polyline + amber CFP vertical markers with "CFP" labels + coach-regime ribbon at bottom + 3 annotation callouts for 2016 crater / 2018 Cotton Bowl / 2024 title game + NOW marker) → 12-season brick grid (color-coded states: peak, title-era, winning, ok, crisis, current) → "WHAT THE ERA SAID" closing serif paragraph → 3-stat peer footer (era avg SP+, mood avg, gap-from-#1)
- Design intent for Claude Code's sprint-3 implementation: this is what the SVG should evoke. The polyline-via-rotated-rects pattern approximates the real SVG `<polyline>` output Claude Code will generate via `svgwrite`/Pillow

### Figma persistence finding (superseded)

Previous finding: non-Cover pages don't persist across use_figma invocations.
New finding from this session: **throwing at end of `use_figma` script rolls back the entire transaction**. For reads (inspection), throw is fine — no mutations to roll back. For writes, end scripts with `figma.notify(...)` and verify via a separate read-only inspection call.

### Next Figma steps (queued for future Cowork sessions)

- Historical Season Deep-Dive mockup for ND 2024 (title-game chapter) — tapping the 2024 brick in the Arc should open this. Spec in 13-modules-archive.md §HistoricalSeasonDeepDive.
- Game Recap mode mockup (post-loss state) — Spec in 14-modules-game-recap.md. Once sprint 2's Chronicle game-edition cards run, a live post-game page exists to design against.
- Screenshot-diff review of rendered Notre Dame HTML vs Figma mockup — iterative design critique that feeds sprint 4+.
