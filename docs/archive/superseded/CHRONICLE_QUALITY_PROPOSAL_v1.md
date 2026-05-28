# Chronicle Quality Proposal v1

Current as requested through May 23, 2026. Note: the local repo and live alias also contain Chronicle activation work timestamped May 24, 2026; this proposal treats that as implementation evidence while keeping the competitive/offseason context anchored to May 23.

## 1. TL;DR

Chronicle's problem is not that it lacks agents. It already has Planner -> Writer -> FactCritic -> VoiceCritic -> CollisionCritic -> Refiner, cache, LKG fallback, source trust, and an antislop banlist. The problem is that the pipeline does not make insight diversity a mechanical invariant. It gives sibling cards the same page-level evidence pool, lets the Planner pick loose card types instead of hard angle slots, passes all evidence to the Writer, does not filter assigned evidence before writing, and runs CollisionCritic after cards are already generated without using it as a rejection gate. The result is visible on Alabama's live Chronicle page: seven cards, most of them paraphrases of the same Polymarket national-title-volume observation.

The fix is to turn Chronicle from "generate N cards" into "fill N distinct editorial jobs." Add angle slots, primary-source exclusivity, per-frame hashes, thesis embeddings, twin detection, and a narrative state table that records consumed frames. Then broaden the taxonomy: counterfactual ladders, recruit-to-result audits, market-vs-model disagreement, fan mood reversals, portal pressure maps, identity crisis cards, schedule lottery cards, and play-level hinge moments. Pair each with static SVG chart modules that are designed as screenshot objects.

Target outcome: six cards per team that never repeat a thesis, each with a different evidence spine, different visual grammar, and a reason a fan would screenshot it.

## 2. Current State Diagnosis

### What shipped

Local DB sample, `cfb_rankings.db`, May 23/24 state:

| Item | Finding |
|---|---|
| `chronicle_card_cache` rows | 301 |
| Active live Chronicle page | 121 cards, 24 teams, per `/chronicle/index.html` |
| Dominant card types | `echo` 173, `player_arc` 55, `devil_card` 34, `flashpoint` 33 |
| Empty support tables | `season_narrative_state` 0, `narrative_frame_stack` 0, `calendar_pressure` 0, `editorial_citations` 0 |
| Evidence-heavy tables Chronicle barely uses | `player_game_stats` 1,304,322; `player_season_stats` 426,725; `player_recruiting_profiles` 17,274; `transfer_entries` 10,379; `player_nfl_draft` 2,059; `returning_production` 525; `team_talent_snapshots` 530 |

The current cards cluster into four weak categories:

1. Season-record recap: "went 5-7", "rollercoaster", "hot streak", "season in review."
2. Market-volume recap: Polymarket volume moved/stayed steady.
3. Off-topic retrieval bleed: Kansas cards about Kansas State, Arizona card about Alabama's Ty Simpson, Indiana card about the Circle City Classic.
4. Generic trend paraphrase: "on a roll", "struggled down the stretch", "odds steady."

Five real card bodies from the cache/live page:

```text
Auburn's 2024 season has been a rollercoaster, with as many losses (7) as wins (7) through Week 14. They've alternated wins and losses in their last six games [src:cfbi_db]. The Tigers started strong with a 73-3 victory over Alabama A&M but stumbled against Power Five opponents, including a 13-31 loss to Georgia and a 28-14 defeat at Alabama. Their lone SEC win came against Kentucky (24-10).
```

```text
Alabama's odds to win the 2027 CFP National Championship have been stable, with betting volumes consistently around $27,160 on Polymarket. The Crimson Tide has been a favorite for next season's title despite no significant changes in their odds since May.
```

```text
Wisconsin finished 2024 with a 5-7 record. They opened strong, winning their first two games but struggled down the stretch, losing seven of their last ten. The Badgers' highest-scoring win was a 52-6 victory over Purdue [src:cfbi_db], while their largest loss was a 42-10 defeat to Iowa [src:cfbi_db]. Their season ended with a 7-24 loss to Minnesota [src:cfbi_db].
```

```text
Kansas State is making waves in recruiting. They've earned the first offer for top 2028 OL target [src:substack_recruits]. Additionally, they've been praised for their basketball transfers [src:substack_recruits]. However, these are Kansas State's achievements, not Kansas'.
```

```text
Arizona's Ty Simpson has been generating buzz, but is he ready for the NFL? Tyler Dunne celebrated Ty Simpson's potential with a quote: 'Congrats, Ty Simpson. You win the 2026 NFL Draft.' [src:substack_long]
```

The Auburn trace requested in the brief lands on a single real cache row:

| Field | Value |
|---|---|
| Query | `slug='auburn'`, `season_year=2024`, `week_number=14` |
| Cache row | 1 |
| DB `card_type` | `echo` |
| JSON `card_type` | `flashpoint` |
| Headline | "Auburn's Streaky Season" |
| Fact critic score | 0.0 |
| Voice critic score | 0.0 |
| Created | `2026-05-24T04:57:18Z` |

That mismatch alone is a signal: the cache row says `echo`, the stored JSON says `flashpoint`, and the body is a generic season recap.

### Why duplicates happen

The code path explains it.

1. `src/cfb_rankings/chronicle/pipeline.py:62` gives tiers a list of allowed card types, not hard angle slots. T3 only gets `flashpoint` and `player_arc`; S gets six loose names.
2. `_collect_evidence()` in `pipeline.py:385` builds one deduped page-level evidence pool for all card types and caps it at 50 rows. The evidence hash is page-level, not card-frame-level.
3. `_run_planner()` in `pipeline.py:446` calls `build_planner_prompt(...)` with `previously_published_cards=None` at `pipeline.py:471`. The Planner is not shown prior sibling output or active cache rows.
4. `build_writer_prompt()` tells the Writer to use `assigned_evidence_ids`, but `pipeline.py:802` passes the full `evidence` list to the Writer. That is an instruction, not a mechanical filter.
5. `CollisionCritic` runs only after shipped drafts exist (`pipeline.py:1142`). The aggregate result is returned, but not used to block or regenerate individual cards.
6. Dense retrieval is still a stub: `retriever.py:13` says BGE-M3 is stubbed by `NullDenseEncoder`, and `retriever.py:256` confirms the zero-vector encoder.

Current prompt strings make the intent good but non-binding. Verbatim key strings:

```python
SYSTEM_VOICE_CFB = """You write for CFB Index, a college-football intelligence product. Your job is to produce short, factual, voiced prose — not blog filler, not engagement bait, not press-release hype.
...
OUTPUT FORMAT

When a JSON schema is supplied via constrained decoding, emit a single valid JSON object matching that schema and nothing else — no prose preamble, no code fences, no trailing commentary."""
```

```python
system = SYSTEM_VOICE_CFB + "\n\nROLE: You are the Planner. Decide what each card on this page should DO. Output a PlannerOutput JSON object with one CardBrief per slot."
```

```python
system = SYSTEM_VOICE_CFB + "\n\nROLE: You are the Writer. Produce ONE card draft as a CardDraft JSON object. Use ONLY the brief's assigned_evidence_ids. Use the assigned opening_type. Never start with a phrase in forbidden_ledes."
```

```python
system = SYSTEM_VOICE_CFB + (
    "\n\nROLE: You are the FactCritic. Score the draft's groundedness. "
    "For each atomic factual claim in body_text, check whether the evidence "
    "supports it. factscore_atomic = supported_claims / total_claims. "
    "verdict='pass' if >=0.85 and no misattributed quotes; 'fix' if 0.6-0.85; "
    "'fail' if <0.6 OR any fabricated quote OR any entity-misattribution "
    "(e.g. 'Arizona's Ty Simpson' when Ty Simpson plays for Alabama)."
)
```

```python
system = SYSTEM_VOICE_CFB + (
    "\n\nROLE: You are the CollisionCritic. Examine all sibling cards on this "
    "page. Flag: (a) two cards with the same opening_type, (b) two cards citing "
    "majority-overlapping evidence_ids, (c) repeated 4-grams across sibling bodies."
)
```

The prompts know the right rules. The pipeline does not enforce enough of them outside the model.

### Where the quality ceiling is capped

| Ceiling | Evidence |
|---|---|
| Data selection | `EVIDENCE_SOURCE_ROUTING` at `evidence_sources.py:1172` mostly routes to market, conversations, editorial citations, game results, and a few player modules. It does not route to recruiting, transfer, returning production, draft, talent, advanced stats, weather, drives, lines, or play-by-play. |
| Slot semantics | Card types are names, not editorial jobs. `echo`, `player_arc`, and `flashpoint` can all write the same Polymarket thesis. |
| Retrieval | Dense retrieval and cross-encoder rerank are stubs. Lexical rows are the only meaningful retrieval layer today. |
| Eval | FActScore overlap (`eval.py:421`) protects against unsupported text but does not score novelty, insight, or fan resonance. Voice scores in sampled rows are often 0.0. |
| Render | Live Chronicle cards are text-first. They do not pair each card with a decisive visual object, despite team pages already having strong modules such as Offseason Pulse, Top Commits, Recruiting Footprint, NFL Draft Pipeline, Fanbase Health, Conference Standing, Ceiling/Floor, Statement Wins, and Bowl History. |

### Live site notes

The live team pages are much stronger than live Chronicle cards. Alabama, Auburn, Wyoming, Army, UMass, Notre Dame, and Oregon pages all present a coherent dark-profile language with Bebas Neue/Source Serif/Inter, team accents, offseason pulse, recruiting, portal, returning production, prestige rails, standing rails, and fanbase health. Chronicle should not sit beside those modules as generic prose. It should play off them.

The live Alabama Chronicle page is the clearest failure case: seven cards, nearly all about 2027 CFP Polymarket movement/volume. It is factual enough to render, but it does not behave like editorial.

## 3. Top 15 New Card Types

Thirty-two candidate ideas were considered: Counterfactual Ladder, Decade Echo, Identity Crisis, Market Arbitrage Watch, Mascot Voice, Recruit-to-Result, Coaching Tree Twist, NFL Pipeline Audit, Fan Mood Backward, Anniversary Trap, The Hinge, Schedule Lottery, Crystal Ball Recall, Portal Pressure Map, Returning Production Trap, Talent-Development Gap, Model Split, Weather Tax, Fourth-Quarter Truth, Red-Zone Lie Detector, Garbage-Time Mirage, Rivalry Thermostat, Depth Chart Debt, Coordinator Fingerprint, Trophy Case Stress, Conference Escape Route, Draft Afterglow, Spring Practice Mismatch, Home-Field Tax, Style-Mismatch Tag, Belief vs Reality, and Program Floor Detector.

The top 15:

| Name | Spec | Primary data sources | Example bodies | Viz | Tier | Slot | Novelty | Competitive footnote |
|---|---|---|---|---|---|---|---|---|
| Counterfactual Ladder | Shows how a season changes if the highest-leverage one-score games flip, then explains why those games did not flip. Tone: analytical, not whiny. | `games`, CFBD `/metrics/wp`, `/plays`, `/drives`, `game_lines` | Auburn: "Auburn does not need fan fiction to see the 2024 hinge. The Tigers were 5-7, and the season's argument lives in the narrow losses: one late possession away from bowl math, but not from proof. The next build should pull win-probability swing plays for every one-score loss, not retell the record [src:game:TODO]."<br><br>Wisconsin: "Wisconsin's 5-7 was not one story. It was two: 2-0 before the schedule hardened, 3-7 after. The Counterfactual Ladder should ask which losses were actually flippable and which were simply the bill coming due. Until CFBD win-probability is wired, this card must mark the hinge plays as TODO [src:games]." | Win-Prob Flip Strip | T1 | counterfactual | B | ESPN has win probability and recaps; it does not package a team's whole offseason identity around the exact flip ladder. |
| Identity Crisis | Finds a team that is elite in one identity metric and broken in another. It argues "this team is two teams." | CFBD `/stats/season/advanced`, `/ppa/games`, `team_savant_weekly`, `power_ratings_weekly` | Wyoming: "Wyoming's page already says the truth out loud: 77% returning production, talent outside the top 100, and a 3-9 finish. That is not a contradiction. It is the identity crisis. The Cowboys have continuity, but the roster still has to win through development, altitude, and game script [src:returning_production_2025] [src:team_talent_snapshots]."<br><br>Oregon: "Oregon is 13-0 on the page and still flagged for 19% returning production. That is the weird offseason sentence: the Ducks can be both the finished product and the rebuild. The card should compare returning production to talent rank and schedule draw before it prints another title-odds paragraph [src:returning_production_2025]." | Identity Split Percentile Pair | T1 | identity | B | PFF and SP+ cover unit strength; Chronicle adds program-specific identity and offseason roster tension. |
| Market-vs-Model Split | Compares Polymarket, Vegas, SP+/FPI/Elo, and CFB Index power/resume. The claim is not "odds moved"; it is "which market disagrees with which model." | `source_observations`, CFBD `/lines`, `/ratings/sp`, `/ratings/elo`, `power_ratings_weekly`, `resume_ratings_weekly` | Notre Dame: "Notre Dame is the market's loudest offseason ticket in our Polymarket feed: $935.61 in observed volume on May 21, far above LSU, Ohio State, Oregon, Miami, and Georgia [src:polymarket_2026-05-21]. The actual Chronicle card should not call that a title case by itself. It should ask whether SP+, FPI, and Vegas agree."<br><br>Alabama: "Alabama's Polymarket volume sat at $27.16 in the latest local observation, the same number that produced seven live Chronicle paraphrases [src:polymarket_2026-05-21]. The better card is a disagreement card: if the market is calm but roster talent is still top-two, say who is underpricing the Tide." | Polymarket-Vegas-Model Tri-Pane | T1 | market | B | Action Network covers odds; ESPN covers FPI; almost nobody stitches market/model/fanbase voice per team. |
| Recruit-to-Result Audit | Follows a class from stars to starts, transfers, honors, draft picks, and wins. Tone: accountability without recruiting-board scolding. | `player_recruiting_profiles`, `recruiting_entries`, `transfer_entries`, `player_game_stats`, `player_honors`, `player_nfl_draft` | Alabama: "Alabama's 2025 class sits No. 3 on the team page with a 298.4 composite rating. The Chronicle job is to hold that number until it becomes snaps: which five-stars are already in the two-deep, which blue-chips left, and which position group still had to buy help through the portal [src:recruiting_entries_2025]."<br><br>UMass: "UMass does not need to be judged on Alabama's ladder. The 2025 recruiting class is listed No. 130, but the portal is +8. That is the card: not a talent flex, a roster triage. The Minutemen are trying to manufacture replacement-level depth in one offseason [src:recruiting_entries_2025] [src:transfer_entries_2025]." | Recruit-to-Roster Arc | T1 | recruiting | B | On3/247 own rankings; Chronicle owns the after-action audit across stars, snaps, portal, and outcome. |
| Portal Pressure Map | Quantifies position-group in/out movement and asks where the roster got younger, older, thinner, or merely noisier. | `transfer_entries`, `roster_source_snapshots`, `returning_production`, CFBD `/player/portal` | Auburn: "Auburn's page says -6 net portal movement: 21 in, 27 out. That is not automatically bad. The pressure map asks where it happened. If the outflow is back-end depth, fine. If it is offensive-line bodies on a 5-7 team, the offseason story changes [src:transfer_entries_2025]."<br><br>Army: "Army's transfer line reads 0 in, 11 out. For a service academy, that is not the same sentence it would be at USC. The Portal Pressure Map has to weight institutional constraints and returning production, not just arrows. Go Army, but count the bodies honestly [src:transfer_entries_2025]." | Transfer Portal Net | T2 | portal | A | Mainstream portal winners/losers lists rarely normalize for program type and position-group pressure. |
| Returning Production Trap | Flags teams whose continuity should help, or whose talent makes continuity less meaningful. | `returning_production`, `team_talent_snapshots`, `power_ratings_weekly`, `profiles/*.md` aspiration ladders | Wyoming: "Wyoming returning 77% should feel comforting. It does not automatically feel dangerous. The Cowboys are outside the talent top 100, so continuity is only valuable if development turns it into efficiency. The card should compare returning production to prior-year EPA, not treat familiar names as progress [src:returning_production_2025]."<br><br>Oregon: "Oregon returning 19% is the kind of number that would scare a normal program. Oregon is not a normal roster. Talent No. 5 changes the continuity math: this is less 'empty cupboard' than 'new starters with five-star receipts' [src:team_talent_snapshots_2025]." | Continuity-vs-Talent Quadrant | T1 | roster | B | Bill Connelly often writes returning-production context; Chronicle can make it team-page-native and visual. |
| The Hinge | Identifies the three plays or drives that changed the season, with a tiny play diagram and receipts. | CFBD `/plays`, `/metrics/wp`, `/drives`, `player_signature_plays`, game video links if available | Notre Dame: "Notre Dame's 11-1 page does not need another top-five sentence. It needs the three snaps that preserved the season. Pull the largest win-probability swings, label down-distance-field-position, and let the card say what every fan remembers but cannot find in a box score [src:plays_TODO]."<br><br>NC State: "The card should not say 'defensive struggles plagued them.' It should show the exact drive where the season tilted: opponent, field position, down, distance, EPA, win probability before and after. If the play data is missing, suppress the card [src:plays_TODO]." | Play-Diagram Tile Stack | S | hinge | B | ESPN has game win-prob charts; it does not produce three-play season autopsies for every team. |
| Fan Mood Reversal | Shows when fan sentiment diverged from the scoreboard: wins that felt bad, losses that stabilized belief, portal moments that changed tone. | `conversation_documents`, `team_week_conversation_features`, `fanbase_mood_weekly`, Reddit JSON, news/RSS, `games` | Alabama: "Alabama went 9-3, but the team page labels the fanbase 'Growing' at low confidence. That is the unresolved offseason card: not whether the Tide were good, but whether the post-Saban fanbase is grading DeBoer against 9 wins or against the standard [src:fan_intel_TODO]."<br><br>Army: "Army at 11-2 and 'Surging' is the clean version of Fan Mood Reversal: the model should find the week where the national conversation stopped treating the option as a curiosity and started treating it as a problem. Then cite the threads, not vibes [src:conversation_documents]." | Mood Timeline with Game Pins | T2 | fan_mood | A | Reddit has raw emotion; CFB Index can bind it to results, markets, and program voice. |
| Decade Echo | Compares the current team-week to exact 10/20/30-year historical anchors. | `games`, `team_historical_seasons`, Wikipedia REST, Sports Reference, `calendar_pressure` | Alabama: "Ten-year echoes work only when they are earned. Alabama's card should not say 'dynasty' because the profile says dynasty. It should compare the current DeBoer-era checkpoint to the exact Saban-era checkpoint: record, rank, opponent quality, and what happened next [src:team_historical_seasons_TODO]."<br><br>Army: "Army's best echo is not cosmetic. The profile says 1944-46 and 2024 belong in the same prestige sentence. A Decade Echo can show how rare an 11-win service-academy season is, then hand the reader the next Army-Navy implication [src:wiki_army_football]." | Decade Anniversary Spark | T2 | history | B | Sports Reference owns history tables; Chronicle adds exact-date framing plus voice. |
| Rivalry Thermostat | Measures rivalry-week heat from both fanbases and connects it to stakes, not just history. | `profiles/*.md` rivalries, `team_week_rival_mentions`, Reddit, `games`, `team_rivalry_meetings`, odds | Auburn: "Auburn's whole page admits the week after Alabama is where the year is measured. The Rivalry Thermostat should not wait for November. In May, it can show the Iron Bowl as the season's emotional ceiling: bowl access, recruiting bragging rights, and the one game that can rescue a 6-6 year [src:profiles/auburn.md]."<br><br>Ohio State: "If Michigan heat is high in May, that is data. The card should compare offseason mention share, betting stakes, and last three rivalry outcomes. Rivalry copy without heat is nostalgia. Heat without receipts is message-board fog [src:team_week_rival_mentions_TODO]." | Rivalry Thermometer Pair | T1 | rivalry | A | Team pages list rivalries; competitors rarely quantify two-sided emotional heat. |
| NFL Pipeline Audit | Tests whether a program's development reputation is still true by position and era. | `player_nfl_draft`, `player_recruiting_profiles`, `player_honors`, `profiles` draft anchors | Alabama: "Alabama's profile says NFL draft production is a sustained talent pipeline. Chronicle should audit it by position, not repeat it. Since 2018, the draft table has the names; the card should ask whether the DeBoer transition protects the pipeline or just inherits the logo [src:player_nfl_draft]."<br><br>Wyoming: "Wyoming's NFL pipeline is not broad; it is mythic because of Josh Allen. That is exactly why the audit matters. Show every drafted Cowboy since 2018, then compare the program's next quarterback development bet to the Allen shadow without pretending the shadow is a system [src:player_nfl_draft]." | NFL Pipeline Funnel | T1 | draft | B | ESPN/NFL Draft pages list picks; Chronicle audits a program claim against position outcomes. |
| Schedule Lottery | Reorders the schedule by opponent strength and shows whether the team drew a fair, cruel, or weird path. | `games`, `power_ratings_weekly`, `resume_ratings_weekly`, CFBD `/ratings/sp`, `/lines` | UMass: "UMass is not chasing the same rung as Oregon. The Schedule Lottery should show which weeks are actual swing chances and which are budgeted pain. That makes a 2-10 program readable without condescension: the goal is the rung above itself [src:profiles/massachusetts.md]."<br><br>Oregon: "Oregon at 13-0 has a different lottery problem: not whether the schedule was survivable, but whether the pressure was distributed. Sort the 12 games by opponent rating, then mark where the Ducks actually built the playoff resume [src:power_ratings_weekly]." | Schedule-Strength Bracket | T2 | schedule | B | Strength-of-schedule is common; rung-aware schedule storytelling is not. |
| Coordinator Fingerprint | Explains a team through the coordinator's measurable tendencies and historical comparables. | CFBD `/plays`, `/stats/season/advanced`, coaches table, `coaching_changes`, staff profiles | Alabama: "The DeBoer card should be about play identity, not biography. Give me early-down pass rate, explosive-play tolerance, red-zone behavior, and how it compares to his Washington teams. If those tables are not wired, the card should say TODO, not 'new era' [src:coaches_TODO]."<br><br>Georgia: "Georgia's coordinator fingerprint is the Smart-era stress test: which part of the defense is still Kirby, and which part belongs to the current staff? A chart can compare havoc, success rate allowed, and explosive plays to the 2021 and 2022 title baselines [src:team_game_advanced_stats_TODO]." | Coordinator Tendency Fingerprint | S | coaching | A | Beat writers cover coordinator hires; few attach schematic metrics to program voice. |
| Belief vs Reality | Puts fan belief, market price, ranking model, and on-field rating in one card. | `fan_intelligence.py`, `source_observations`, `power_ratings_weekly`, `resume_ratings_weekly`, `confidence_calibration` | Notre Dame: "Notre Dame's page says 11-1, CFP #5, and Fanbase Health 80 at low confidence. Belief vs Reality should put those in one line: the fans are loud, the record supports it, but the signal sample is thin. That is transparent, and more useful than another 'title hopes gaining steam' card [src:confidence_calibration]."<br><br>Auburn: "Auburn's 5-7 record, top-10 recruiting class, and middling fan-health score are not three cards. They are one Belief vs Reality card: the future is being priced higher than the present because the class is carrying the argument [src:recruiting_entries_2025]." | Belief-Reality Quad | T1 | belief | A | This is the CFB Index-native moat: fan intel plus model plus market plus roster. |
| Weather Tax | Finds games where weather meaningfully changed play-calling or efficiency. | CFBD `/games/weather`, `/plays`, `/stats/game/advanced`, `games` | Army: "A Weather Tax card for Army should be surgical: wind, temperature, run rate, drive length. If Michie weather turns an opponent's offense into short-field math, that is not vibes; it is the option's home-field tax in numbers [src:game_weather_TODO]."<br><br>Wyoming: "Laramie's altitude is already the voice. The Weather Tax makes it measurable: visiting drives by quarter, pace drop, false starts, and passing efficiency in cold/wind games at 7,220 feet. Cowboy Tough, but with receipts [src:game_weather_TODO]." | Weather Tax Strip | T2 | environment | A | Weather appears in game previews; program-level weather tax is rare. |
| Crystal Ball Recall | Compares preseason/recruiting/media expectations to what actually happened. | recruiting rankings, preseason polls, SP+/FPI preseason, `editorial_citations`, RSS/On3/247 archives | Texas: "Texas is where Crystal Ball Recall can sing. If the 2025/2026 expectation was SEC title or CFP semifinal, the card should preserve the preseason receipts and grade them in May. The goal is not dunking. It is memory with a scoreboard [src:editorial_citations_TODO]."<br><br>USC: "USC's Riley era is made for receipt accounting. Capture the preseason thesis, the portal thesis, and the Big Ten schedule thesis. Then mark which part was right. Fight On does not need amnesia; it needs better receipts [src:rss_TODO]." | Receipt Timeline | T1 | receipts | B | Prediction accountability exists in columns; Chronicle can automate it across 119 teams. |
| Trophy Case Stress | Shows where current expectations sit against program prestige and realistic aspiration ladder. | `profiles/*.md` aspiration_ladder, prestige tiers, `games`, rankings, conference standings | Alabama: "A 9-3 Alabama season lives in a strange place: Top 15 nationally, crisis-adjacent internally. Trophy Case Stress is the chart for that. It should show Alabama's page rung: bowl is baseline, SEC title game is table stakes, national title is the standard [src:profiles/alabama.md]."<br><br>UMass: "UMass should never be graded on Alabama's ladder. A 4-8 season with conference traction can be a legitimate rung climb. Trophy Case Stress makes that visible: local aspiration, not national mockery [src:profiles/massachusetts.md]." | Aspiration Ladder Rail | T2 | aspiration | A | Competitors flatten expectations; CFB Index has authored aspiration ladders. |

## 4. Anti-Duplication Architecture

### Mechanism 1: angle-slot assignment

Add a hard enum. The Planner fills slots, not vague card types.

```python
ANGLE_SLOTS = [
    "trajectory", "identity", "market", "counterfactual", "history",
    "peer_comparison", "fan_voice", "roster", "coaching", "rivalry",
]

def assign_slots(target, n_cards):
    eligible = slot_policy_for_team(target.slug, target.tier, target.phase)
    return eligible[:n_cards]
```

Landing: `src/cfb_rankings/chronicle/pipeline.py` before `_run_planner()`. Migration:

```sql
CREATE TABLE chronicle_angle_slot_policy (
  entity_kind TEXT NOT NULL,
  entity_slug TEXT NOT NULL,
  season_year INTEGER NOT NULL,
  week_number INTEGER NOT NULL DEFAULT -1,
  slot_index INTEGER NOT NULL,
  angle_slot TEXT NOT NULL,
  required_primary_source_kind TEXT,
  min_confidence_band TEXT DEFAULT 'medium',
  created_at_utc TEXT DEFAULT (datetime('now')),
  PRIMARY KEY(entity_kind, entity_slug, season_year, week_number, slot_index)
);
```

Tests: `tests/test_chronicle_angle_slots.py` asserts six generated briefs have six distinct `angle_slot` values and reject unknown slots.

### Mechanism 2: frame stack rotation

Use `season_narrative_state` for teams, not only player-flavored `narrative_frame_stack`.

```python
def reserve_frame(db, target, angle_slot):
    frames = load_open_frames(db, target, angle_slot)
    for frame in frames:
        if not frame.consumed_this_week:
            mark_frame_reserved(frame.frame_id, batch_id)
            return frame
    return synthesize_new_frame(target, angle_slot)
```

Migration:

```sql
CREATE TABLE chronicle_frame_consumption (
  entity_kind TEXT NOT NULL,
  entity_slug TEXT NOT NULL,
  season_year INTEGER NOT NULL,
  week_number INTEGER NOT NULL DEFAULT -1,
  frame_id TEXT NOT NULL,
  angle_slot TEXT NOT NULL,
  card_cache_key TEXT,
  consumed_at_utc TEXT DEFAULT (datetime('now')),
  PRIMARY KEY(entity_kind, entity_slug, season_year, week_number, frame_id)
);
```

Tests: generate six Auburn cards; assert no two rows share `frame_id` or `angle_slot`.

### Mechanism 3: primary evidence exclusivity

Each card declares one primary source family. Sibling cards cannot reuse it unless no alternative exists.

```python
used_primary_sources = set()
for brief in planner.briefs:
    rows = evidence_router.fetch(brief.card_type, brief.angle_slot)
    primary = choose_primary_source(rows, excluded=used_primary_sources)
    brief.primary_evidence_ids = top_k(rows, source=primary, k=4)
    used_primary_sources.add(primary)
```

Landing: replace `pipeline.py:_collect_evidence()` with per-brief collection after planning. The Writer receives only `brief.primary_evidence_ids + brief.support_evidence_ids`.

Tests: Alabama six-card generation must include at most one Polymarket-primary card.

### Mechanism 4: thesis sentence gate

Planner emits `thesis_sentence` for each brief. Reject similar theses before writing.

```python
for a, b in combinations(briefs, 2):
    if cosine(embed(a.thesis_sentence), embed(b.thesis_sentence)) > 0.82:
        raise PlannerCollision(f"{a.slot_index} duplicates {b.slot_index}")
```

Landing: `prompts.CardBrief` schema gets `angle_slot`, `thesis_sentence`, `primary_source_kind`, `viz_type`. Use BGE-M3 once `retriever.py` dense stub is replaced.

Tests: fixture with seven Alabama Polymarket theses should fail before Writer.

### Mechanism 5: twin detector post-generation

Check against existing same-team-season cache plus sibling drafts.

```python
def reject_twins(db, target, draft):
    prior = load_active_bodies(db, target.slug, target.season_year)
    for body in prior:
        if cosine(embed(draft.body_text), embed(body)) > 0.85:
            return Reject("semantic twin")
    return Pass()
```

Landing: inside `generate_card()` before `store_card()`. Store score in new columns.

```sql
ALTER TABLE chronicle_card_cache ADD COLUMN angle_slot TEXT;
ALTER TABLE chronicle_card_cache ADD COLUMN thesis_sentence TEXT;
ALTER TABLE chronicle_card_cache ADD COLUMN primary_source_kind TEXT;
ALTER TABLE chronicle_card_cache ADD COLUMN twin_similarity_max REAL;
ALTER TABLE chronicle_card_cache ADD COLUMN viz_spec_json TEXT;
```

Tests: seed Alabama cache with Polymarket body; generating another market-stability card returns `suppressed` or `regenerate`.

### Mechanism 6: dynamic banned phrase rotation

Beyond `chronicle_banlist`, ban the previous card's top nouns/verbs and repeated openings.

```python
dynamic_bans = extract_salient_terms(previous_card.body_text, top_n=12)
brief.forbidden_ledes.extend(previous_card.opening_ngrams)
writer_config.antislop_banlist += dynamic_bans
```

Landing: `generate_page_cards()` loop. Store terms in `narrative_phrase_tokens`.

Tests: if card 1 uses "odds steady", card 2 cannot use that lede or phrase.

### Mechanism 7: CollisionCritic as a gate, not a report

Move collision before cache writes or add a second-pass invalidation.

```python
drafts = [write_draft(brief) for brief in briefs]
collision = run_collision_critic(drafts)
if collision.verdict != "pass":
    regenerate_flagged_slots(collision.flagged_slot_indices)
for draft in passed_drafts:
    store_card(...)
```

Tests: a fixture with three same-source/same-opening drafts must store zero until regenerated.

## 5. New Viz Catalog

These extend the locked six-chart vocabulary deliberately. Most should render as static SVG at build time, using existing token colors and tabular numerals. Interaction can be progressive enhancement only.

| Name | Sketch | Data sources | Render approach | Pairing | Build cost | Risk |
|---|---|---|---|---|---|---|
| Win-Prob Flip Strip | `Wk3 [-----X----] Wk8 [---X------] Wk11 [------X---]` | CFBD `/metrics/wp`, `/plays`, `games` | Static SVG plus title/desc; optional hover in team page | Counterfactual Ladder, The Hinge | Background job precomputes top flips per team-week | Needs CFBD WP wiring and mobile labels |
| Per-Game Momentum Barcode | `W1 +++ W2 -- W3 + W4 ---` | `games`, `power_ratings_weekly`, `/ppa/games` | Static SVG 12-cell strip | Season Arc, Identity Crisis | Render during team page build | Color scale must be accessible |
| Polymarket-Vegas-Model Tri-Pane | `Market 12% | Vegas 15% | Model 8%` | `source_observations`, `game_lines`, SP+/FPI/Elo | Static SVG bars | Market-vs-Model Split | Weekly cron after odds ingest | Odds semantics can be misread |
| Recruit-to-Roster Arc | `5* -> starter -> portal -> drafted` | `player_recruiting_profiles`, `transfer_entries`, stats, draft | Static SVG Sankey-lite | Recruit-to-Result Audit | Per team, offseason cron | Dense for large classes |
| Portal Position Net | `QB +2/-1, OL +1/-5` arrows | `transfer_entries`, roster snapshots | Static SVG with position rows | Portal Pressure Map | Fast SQL aggregation | Requires position normalization |
| Continuity-vs-Talent Quadrant | `high talent/low return` quadrant | `returning_production`, `team_talent_snapshots` | Static SVG scatter with labels | Returning Production Trap | Build once per offseason refresh | Talent rank missing for long-tail |
| Mood Timeline with Game Pins | `sentiment line + W/L pins` | `fan_intelligence`, Reddit/news/betting, `games` | SVG annotated line | Fan Mood Reversal | Needs fan-intel aggregates populated | Low-confidence teams need fallback |
| Decade Anniversary Spark | `2016 ... 2026` small multiple | `team_historical_seasons`, Wikipedia, SportsRef | Static SVG small multiples | Decade Echo | Low after historical ingest | Historical source consistency |
| Rivalry Thermometer Pair | `Auburn heat || Alabama heat` | rivalry profiles, Reddit mentions, odds | SVG mirrored thermometer | Rivalry Thermostat | Rivalry-week cron plus offseason snapshot | Avoid inflammatory copy |
| NFL Pipeline Funnel | `recruit stars -> starts -> draft round` | `player_nfl_draft`, recruits, stats | Static SVG funnel/Sankey | NFL Pipeline Audit | Medium aggregation | NFL career data needs source |
| Schedule-Strength Bracket | games sorted by opponent strength | `games`, `power_ratings_weekly`, SP+ | SVG bracket/ladder | Schedule Lottery | Per-team build | Sorting may confuse chronology |
| Coordinator Tendency Fingerprint | 5-axis allowed only as fingerprint exception | `/plays`, advanced stats, coaches | Static SVG radar-like fingerprint; justified exception | Coordinator Fingerprint | Needs advanced/play data | Existing chart doc forbids radar except player fingerprint; requires approval |
| Belief-Reality Quad | 2x2: fans/model/market/results | fan intel, market, ratings, standings | Static SVG quad | Belief vs Reality | Medium; depends on signal availability | Confidence chips must be prominent |
| Weather Tax Strip | wind/temp/rush rate by game | `game_weather`, `/plays`, `/stats/game/advanced` | Static SVG strip | Weather Tax | Needs weather ingest | Sparse weather data |
| Aspiration Ladder Rail | rung ladder with locked/unlocked states | profiles, standings, rankings, odds | Static SVG rail | Trophy Case Stress | Already profile-backed | Must not shame low-tier programs |
| Receipt Timeline | preseason -> midseason -> final receipts | `editorial_citations`, RSS, archived predictions | Static SVG timeline | Crystal Ball Recall | Needs citation ingest | Legal/ToS handling for quotes |

## 6. Evidence-Source-to-Card-Type Map

| Dataset / endpoint | Source file or API path | Already in DB? | Card types unlocked | Cost |
|---|---|---|---|---|
| `profiles/*.md` voice, rituals, aspiration ladders | `src/cfb_rankings/team_pages/data.py` profile loader | Yes, 127 files | Mascot Voice, Trophy Case Stress, Rivalry Thermostat, Decade Echo | $0 |
| `games` | Local DB, CFBD `/games` | Yes, 8,594 rows | Counterfactual Ladder, Schedule Lottery, Decade Echo, Hinge | CFBD tier 2 already paid |
| `player_game_stats` | CFBD `/games/players` | Yes, 1.3M rows | Recruit-to-Result, Hinge player attribution, hidden star | CFBD |
| `player_season_stats` | CFBD season stats | Yes, 426k rows | Development arc, NFL Pipeline Audit | CFBD |
| `player_recruiting_profiles` | CFBD `/recruiting/players` | Yes, 17,274 rows | Recruit-to-Result, Crystal Ball Recall | CFBD |
| `recruiting_entries` | CFBD `/recruiting/teams` | Yes, 533 rows | Recruit-to-Result, Trophy Case Stress | CFBD |
| `transfer_entries` | CFBD `/player/portal` | Yes, 10,379 rows | Portal Pressure Map, Returning Production Trap | CFBD |
| `returning_production` | CFBD `/player/returning` | Yes, 525 rows | Returning Production Trap, Belief vs Reality | CFBD |
| `team_talent_snapshots` | CFBD `/talent` | Yes, 530 rows | Identity Crisis, Talent-Development Gap | CFBD |
| `player_nfl_draft` | CFBD `/draft/picks` | Yes, 2,059 rows | NFL Pipeline Audit, Draft Afterglow | CFBD |
| `source_observations` Polymarket | Polymarket adapter | Yes, 160 rows | Market-vs-Model Split, Belief vs Reality | $0 |
| `conversation_documents` | Reddit/news/fan-intel ingest | Partial, 110 rows; target rows empty | Fan Mood Reversal, Rivalry Thermostat | $0 |
| `editorial_citations` | `src/cfb_rankings/citations/persistence.py` | Table yes, 0 rows | Crystal Ball Recall, Receipt Timeline | $0 plus ingestion |
| CFBD `/plays` | Wire via `src/cfb_rankings/clients/cfbd.py`; local `plays` table empty | No useful rows today | The Hinge, Weather Tax, Coordinator Fingerprint | CFBD |
| CFBD `/metrics/wp` | New adapter needed | No | Counterfactual Ladder, Win-Prob Flip Strip | CFBD |
| CFBD `/drives` | `drives` table exists, 0 rows | No useful rows | The Hinge, drive identity | CFBD |
| CFBD `/stats/season/advanced` | `team_game_advanced_stats` exists, 0 rows | No useful rows | Identity Crisis, Coordinator Fingerprint | CFBD |
| CFBD `/lines` | `game_lines`, `game_line_snapshots` exist, 0 rows | No useful rows | Market-vs-Model, Schedule Lottery | CFBD |
| CFBD `/games/weather` | `game_weather` exists, 0 rows | No useful rows | Weather Tax | CFBD |
| SP+/Elo/FPI/SRS | CFBD ratings endpoints | Partial via local power/resume, not external ratings | Market-vs-Model, Schedule Lottery | CFBD |
| ESPN team JSON | Unofficial/free, ToS-sensitive | No | Schedule context, transaction timeline | $0, verify permitted use |
| Sports Reference | Public historical pages | No structured ingest | Decade Echo, Trophy Case Stress | $0, respect ToS/robots |
| Wikipedia REST | Free API | No | Decade Echo, historical anchors | $0 |
| Massey/Sagarin/Torvik-style ratings | Scrape or manual CSV where permitted | No | Model Split, Style Mismatch | $0, verify ToS |
| PFF grades | Paid | No | Coordinator Fingerprint, "graded badly but won" | Paid; likely more than $20/mo, user decision |
| FEI archive | Paid/free mix depending access | No | Drive efficiency identity | Paid/uncertain, flag before build |

## 7. Pipeline Refactor Plan

### Step 1: schema

Add `angle_slot`, `thesis_sentence`, `primary_source_kind`, `viz_spec_json`, `twin_similarity_max`, and `source_diversity_key` to `chronicle_card_cache`. Add `chronicle_angle_slot_policy`, `chronicle_frame_consumption`, and `chronicle_viz_cache`.

### Step 2: Planner schema

Extend `CardBrief` in `prompts.py`:

```python
class CardBrief(BaseModel):
    slot_index: int
    angle_slot: Literal[
      "trajectory","identity","market","counterfactual","history",
      "peer_comparison","fan_voice","roster","coaching","rivalry"
    ]
    card_type: str
    thesis_sentence: str
    primary_source_kind: str
    assigned_evidence_ids: list[str]
    support_evidence_ids: list[str] = []
    viz_type: str | None = None
    forbidden_ledes: list[str] = []
```

### Step 3: per-brief evidence routing

Replace page-level `_collect_evidence(db, target, card_types)` with:

```python
page_pool = collect_candidate_evidence(db, target, all_possible_sources)
plans = planner(target, page_pool, required_angle_slots)
for plan in plans:
    evidence = filter_to_assigned_ids(page_pool, plan.assigned_evidence_ids)
    enforce_primary_source_uniqueness(plan, evidence, state)
    draft = generate_card(..., evidence=evidence)
```

### Step 4: twin detection

Wire real dense embeddings into `retriever.py` behind optional deps. BGE-M3 is appropriate because the architecture already names it. Until installed, use TF-IDF cosine as a deterministic fallback so tests run locally.

### Step 5: visual director

Add `build_visual_director_prompt()` or keep it deterministic at first. For P0, visual specs are generated by card type and SQL:

```json
{
  "viz_type": "continuity_talent_quadrant",
  "data_query_id": "team_returning_talent_2025",
  "primary_metric": "returning_total",
  "comparison_group": "FBS"
}
```

Renderer lands in `src/cfb_rankings/chronicle/viz/` with static SVG functions. Store outputs in `chronicle_viz_cache`.

### Step 6: eval upgrade

Replace binary-ish FActScore gating with Insight Quality Score:

| Component | Weight | Mechanic |
|---|---:|---|
| Factual correctness | 0.40 | Existing FactCritic + heuristic FActScore |
| Specificity | 0.20 | named entities, dates, scores, source IDs per 75 words |
| Novelty | 0.20 | embedding distance from same-team-season cache |
| Receipt density | 0.10 | citation markers and source diversity |
| Voice alignment | 0.10 | corpus/profile similarity plus banlist score |

Block if factual correctness fails. Regenerate if Insight Quality Score < 0.72 for S/T1 or < 0.62 for T2/T3.

### Step 7: render

Team pages: replace generic "AI Narratives" grid with angle-slot modules:

```text
Chronicle
  1. The Hinge          [play-diagram stack]
  2. Belief vs Reality  [quad]
  3. Portal Pressure    [position net]
  4. Decade Echo        [anniversary spark]
```

Standalone `/chronicle/<slug>.html`: group by angle slot, show source family chips, confidence, generated time, and "why this is different from the previous card" metadata.

### Test plan

| Test | Assertion |
|---|---|
| `test_planner_assigns_distinct_angle_slots` | Six-card plan has six distinct slots. |
| `test_writer_receives_only_assigned_evidence` | Prompt evidence block excludes unassigned IDs. |
| `test_primary_source_unique_per_team_week` | Only one Polymarket-primary card per team-week. |
| `test_twin_detector_rejects_semantic_duplicate` | Alabama Polymarket paraphrase fails. |
| `test_collision_critic_blocks_store` | Repeated 4-grams do not reach cache. |
| `test_viz_spec_required_for_visual_card_types` | Top 15 card types emit valid `viz_spec_json`. |
| `test_lkg_preserves_last_good_when_new_card_rejected` | Rejection serves LKG, does not erase prior. |

## 8. Hardware + Cost Plan

Current local stack:

| Component | Role |
|---|---|
| RTX 5070, 16GB VRAM | Overnight generation |
| Ollama `mistral-nemo:12b-instruct-2407-q4_K_M` | Writer |
| Ollama `qwen3:8b` | Planner/Critic |
| DeepInfra Mistral Nemo | cheap fallback at $0.02/M input, $0.04/M output per `runtime.py` |
| Self-hosted Alienware GitHub Actions runner | Scheduled batches |

Assumptions for cost math: a full card pass is roughly 3,500 input tokens and 500 output tokens across planning/writing/critics if local models handle most work. Paid premium critic/refiner calls are estimated at 4,000 input + 800 output. Actual GPT-5/Sonnet pricing must be checked before implementation because API prices are temporally unstable.

| Tier | Cards | Model route | Cost/card | FBS-week cost at 714 cards |
|---|---|---|---:|---:|
| S | Top 10 teams, top 25 players, flagship cards | Paid Writer or paid Insight Critic + local Planner; Best-of-3 local draft first | TODO current GPT-5/Sonnet price; budget cap $0.03-$0.08 | If 60 cards, $1.80-$4.80 |
| T1 | Top 50 teams and high-traffic player pages | Local Mistral Writer, local Qwen Planner/Critic, paid Insight Critic only for failed novelty | ~$0.002-$0.01 average if 10-20% paid review | $1-$5 for 500 T1/T2 mixed cards |
| T2 | Ranks 51-100 | All local, optional DeepInfra fallback | DeepInfra approx $0.00009/card at 3.5k in/500 out | <$0.10 if all 714 fallback |
| T3 | Long tail | Template + local Mistral or Null suppress when evidence thin | $0 | $0 compute only |

What stays local:

- Planner drafts, evidence compression, initial Writer, FactCritic for non-flagship cards, slop checks, embeddings, static SVG rendering.

What is worth paying for:

- S-tier Insight Critic.
- S-tier Refiner for screenshot cards.
- One weekly "top 20 most likely to be shared" polish pass.
- Occasional source/citation critic for receipt-heavy cards.

Overnight cron:

```text
22:00 local: ingest CFBD/reddit/news/market deltas
22:30: compute frame/slot plans for all 119 teams
23:00: generate T3/T2 local cards
01:30: generate T1 cards
03:00: paid critic/refiner only for S/T1 failed or flagship cards
04:00: render SVGs + Chronicle pages
04:30: export LKG + run quality gates
05:00: publish if pass; otherwise serve prior LKG
```

## 9. Implementation Roadmap

| Priority | Sprint | Work | Effort | Dependencies |
|---|---|---|---:|---|
| P0 | Sprint 1 | Add angle slots to `CardBrief`, slot policy, and per-card evidence filtering. Block more than one same-primary-source card per team-week. | 3 dev-days | Migration, prompt schema |
| P0 | Sprint 1 | Make CollisionCritic a gate before cache write. Add twin detector with TF-IDF fallback. | 2 dev-days | Cache metadata |
| P0 | Sprint 1 | Add regression fixtures from Alabama live page and Auburn cache row. | 1 dev-day | Existing cache samples |
| P0 | Sprint 2 | Ship first five card types: Belief vs Reality, Portal Pressure, Returning Production Trap, Market-vs-Model, Trophy Case Stress. | 5 dev-days | Existing DB tables |
| P1 | Sprint 3 | Wire static SVG renderers for five visual forms and attach to `/chronicle/<slug>.html`. | 5 dev-days | Viz cache |
| P1 | Sprint 3 | Replace Chronicle page layout with angle groups, confidence chips, source-family chips. | 2 dev-days | Renderer |
| P1 | Sprint 4 | Wire CFBD `/plays`, `/metrics/wp`, `/drives`, `/stats/season/advanced`, `/lines`, `/games/weather`. | 7 dev-days | CFBD tier 2 token |
| P1 | Sprint 5 | Ship The Hinge, Counterfactual Ladder, Identity Crisis, Weather Tax, Coordinator Fingerprint. | 6 dev-days | New CFBD endpoints |
| P2 | Sprint 6 | Populate `editorial_citations` from RSS/archives and ship Crystal Ball Recall / Receipt Timeline. | 5 dev-days | Citation ingestion |
| P2 | Sprint 7 | Add BGE-M3 embeddings and semantic twin detector. | 3 dev-days | Optional deps, model download |
| P2 | Sprint 8 | Add fan mood/rivalry aggregates and Rivalry Thermostat. | 5 dev-days | Fan-intel target tables populated |
| P3 | Sprint 9 | Share-card PNG pre-render for best Chronicle cards. | 4 dev-days | Stable SVG layout |
| P3 | Sprint 10 | Paid-critic routing, spend caps, per-surface cost dashboard. | 3 dev-days | `llm_usage_log` |

## 10. Voice Fit-Test

### Alabama - dynastic-process

Alabama does not need a hopeful May card. It needs a standard card. The page says 9-3, recruiting class No. 3, talent No. 2, and returning production 43%. That is the DeBoer equation: the roster is still a national-title instrument, but the continuity is not free. The process does not flinch at rankings. It asks which position group has earned them [src:profiles/alabama.md] [src:returning_production_2025].

### Wyoming - Laramie altitude

Wyoming's best offseason number is not the 3-9 record. It is 77% returning production sitting next to a talent profile outside the top 100. That is Laramie football in one cold sentence: familiar bodies, thin margin, development or bust. The altitude can steal a quarter. It cannot recruit for you. Cowboy Tough means counting both [src:profiles/wyoming.md] [src:returning_production_2025].

### Army - West Point service academy

Army's page carries the rare clean signal: 11-2, ranked, Commander-in-Chief context alive, and a transfer ledger that looks nothing like a portal-school ledger. Eleven out, zero in is not panic copy at West Point. It is the institution. The Black Knights win by system, mission, and repetition. Go Army. Beat Navy. Count the constraint before grading the roster [src:profiles/army.md] [src:transfer_entries_2025].

## 11. Risks & Open Questions

| Risk / question | Decision needed |
|---|---|
| Date/state mismatch | The brief says 2025 season completed; local/live site is still publishing many "2024 Season" labels. Decide whether Chronicle should target 2024 final data, 2025 final data, or 2026 offseason preview state before mass regeneration. |
| Chart vocabulary lock | Coordinator fingerprint and rivalry thermometer extend the six-chart vocabulary. Approve explicit exceptions or recast them as small multiples/percentile bars. |
| Low-confidence fan intel | Many fan-intel aggregate tables are empty. Fan Mood Reversal should be gated until cohort rows exist or it will repeat current "low confidence" surface issues. |
| Source ToS | Sports Reference, ESPN unofficial JSON, Sagarin/Massey/Torvik scraping need ToS review before automation. |
| Paid model prices | Current GPT-5/Sonnet costs must be verified at implementation time. Use spend caps, not assumptions. |
| PFF/FEI value | PFF grades would unlock unique "won despite bad grades" cards, but cost likely exceeds the user's casual $20/mo comfort line. |
| Off-topic retrieval | Current topical anchor helps, but evidence targets are still weak. Source rows need canonical entity IDs, not just text. |
| LKG staleness | LKG is good for reliability, but stale LKG cards can preserve bad old theses. Add an editorial stale threshold per angle slot. |

## 12. Appendix A: Competitive Scan Notes

| Source | What they do well | Gaps Chronicle can exploit | Viz notes |
|---|---|---|---|
| ESPN team pages, e.g. Alabama | Schedule, roster, stats, news, FPI adjacency. Fast and familiar. | Little team-specific voice; insight is modular but not synthesized into "why this matters now." | Mostly tables, scoreboards, leader lists. |
| The Athletic team pages | Beat-writer voice, access, columns, depth. | Paywalled, not systematic across all 119 FBS teams; no per-team data-viz grammar. | Article imagery more than bespoke interactive team charts. |
| On3 team pages | Recruiting, NIL, transfer portal, insider framing. | Strong raw recruiting coverage, weaker after-action accountability that ties stars to results. | Recruiting rankings/tables; limited narrative viz. |
| 247Sports team pages | Deep recruiting database, Crystal Ball, boards. | Owns the inputs; does not own "what the 2022 class actually became" as a visual audit. | Rankings, lists, article cards. |
| Sports Reference | Historical tables, yearly results, player stats. | Great reference, not voiced; no fanbase or market layer. | Tables, not screenshot-native editorial cards. |
| PFF College | Grades, advanced player/team evaluation. | Premium and grade-centric; less fanbase identity, market, and historical voice synthesis. | Grade tables and rankings; good but not team-page-native. |
| Bill Connelly/SP+ style analysis | Excellent returning production, SP+, explosiveness, success-rate framing. | Niche audience, mostly article format, not 119-team persistent profile cards. | Some charts in articles; not per-team card system. |
| Reddit /r/CFB | Reveals what fans actually care about: portal rumors, schedule anxiety, realignment jokes, coach trust, rivalry resentment. | Raw and chaotic; needs entity linking, confidence, and citation discipline. | None native beyond post rankings. |
| Action Network / betting sites | Odds, line movement, futures, betting angles. | Betting-first; does not reconcile fan mood, model ratings, and program identity. | Odds tables, movement charts. |
| Saturday Down South / The Comeback | Fast emotion, SEC/topic-specific takes. | Take-driven, inconsistent data depth. | Article cards, not advanced viz. |
| Podcasts (Solid Verbal, PFF College, Bear Logic, Andy Staples) | Agenda-setting topics, offseason narratives, voice. | Hard to search/structure; great as low-trust color and citation candidates. | Audio, no reusable viz. |

Novelty triangulation:

- A: Belief vs Reality, Rivalry Thermostat, Weather Tax, Trophy Case Stress, Portal Pressure normalized by program constraints.
- B: Counterfactual Ladder, Returning Production Trap, Recruit-to-Result, Decade Echo, NFL Pipeline Audit, Market-vs-Model.
- C: Schedule Lottery and Crystal Ball Recall are covered in pieces elsewhere but can be made 10x better with receipts and visuals.
- D: Plain odds movement and plain season recap should be dropped except as raw evidence inside stronger frames.

Useful public reference URLs:

- ESPN Alabama team page: `https://www.espn.com/college-football/team/_/id/333/alabama-crimson-tide`
- On3 Alabama: `https://www.on3.com/teams/alabama-crimson-tide-football/`
- 247 Alabama: `https://247sports.com/college/alabama/`
- Sports Reference Alabama: `https://www.sports-reference.com/cfb/schools/alabama/`
- PFF College football: `https://www.pff.com/college`
- Reddit CFB top month: `https://www.reddit.com/r/CFB/top/?t=month`
- Bill Connelly/SP+ coverage via ESPN: `https://www.espn.com/college-football/`

## 13. Appendix B: Codebase Trace

### Trace target

`auburn`, `season_year=2024`, `week_number=14`, requested `echo` card.

### Retrieval / evidence

`pipeline.py:_collect_evidence()`:

```python
for ct in card_types:
    rows = fetch_evidence_for_card(
        db,
        card_type=ct,
        slug=target.slug,
        entity_kind=target.entity_kind,
        season_year=target.season_year,
        week_number=target.week_number,
    )
...
query = RetrievalQuery(
    entity_slug=target.slug,
    entity_kind=target.entity_kind,
    season_year=target.season_year,
    week_number=target.week_number,
    card_type=primary_ct,
    k=30,
    mode="all",
)
```

For `echo`, `evidence_sources.py:1187` routes:

```python
"echo": [
    "fetch_conversation_evidence",
    "fetch_what_changed_evidence",
    "fetch_editorial_citations",
    "fetch_team_game_evidence",
],
```

The game evidence fetcher produces rows like:

```python
text = (
    f"{slug} {outcome} {team_pts}-{opp_pts} {ha} {opp_name} "
    f"(Week {week} {season_year})"
)
...
text=f"{slug} {season_year} record: {wins}-{losses} through week 14"
```

For Auburn, that is enough to let the model write a record-recap card, but not enough to write a distinctive insight.

### Planner prompt

Verbatim builder core:

```python
system = SYSTEM_VOICE_CFB + "\n\nROLE: You are the Planner. Decide what each card on this page should DO. Output a PlannerOutput JSON object with one CardBrief per slot."

user = (
    f"<task>plan {n_slots} cards for {entity_kind}={entity_slug}, "
    f"season={season_year}, week={week_number}</task>\n\n"
    f"<available_card_types>{json.dumps(available_card_types)}</available_card_types>\n"
    f"<available_evidence_ids>{json.dumps(_evidence_id_list(evidence))}</available_evidence_ids>\n\n"
    + render_evidence_block(evidence) + "\n\n"
    + render_narrative_state(frame_stack, open_arcs, calendar_pressure, phrase_tokens) + "\n\n"
    + prior
    + "\n<instructions>For each of the {n} slots: choose card_type, assign 2-4 evidence_ids, "
    "pick opening_type (no two siblings share an opening), and list forbidden_ledes (phrases the "
    "Writer must avoid). Suppress (action='suppress') if evidence is thin. Set page_thesis to a "
    "single sentence describing what the page argues. Return a PlannerOutput JSON object.</instructions>".format(n=n_slots)
)
```

Issue: this asks for evidence assignment but does not force primary-source diversity, and `previously_published_cards` is not populated.

### Writer prompt

Verbatim builder core:

```python
system = SYSTEM_VOICE_CFB + "\n\nROLE: You are the Writer. Produce ONE card draft as a CardDraft JSON object. Use ONLY the brief's assigned_evidence_ids. Use the assigned opening_type. Never start with a phrase in forbidden_ledes."
...
user = (
    topical_anchor
    + f"<page_thesis>{page_thesis}</page_thesis>\n"
    + f"<brief>{brief.model_dump_json()}</brief>\n\n"
    + render_evidence_block(evidence) + "\n"
    + voice_note + devil_note
    + "\n<instructions>Write the card body now. Target "
    f"{brief.target_word_count} words. Open with opening_type='{brief.opening_type}'. "
    f"Use template_pattern='{brief.template_pattern}' if it fits the evidence; otherwise "
    "use freeform. Cite at least once with [src:source_id]. Return a CardDraft JSON object.</instructions>"
)
```

Issue: the Writer sees the full evidence block, so "Use ONLY assigned_evidence_ids" is advisory.

### FactCritic / eval

FactCritic asks for >=0.85 support, but heuristic eval hard-rejects only below 0.50 (`eval.py:792`) and can be overridden when the LLM critic passes (`pipeline.py:886-913`). This protects against some hallucination but does not penalize low novelty or banal framing.

### Actual cached output

```json
{
  "slot_index": 0,
  "card_type": "flashpoint",
  "headline": "Auburn's Streaky Season",
  "body_text": "Auburn's 2024 season has been a rollercoaster, with as many losses (7) as wins (7) through Week 14. They've alternated wins and losses in their last six games [src:cfbi_db]. The Tigers started strong with a 73-3 victory over Alabama A&M but stumbled against Power Five opponents, including a 13-31 loss to Georgia and a 28-14 defeat at Alabama. Their lone SEC win came against Kentucky (24-10).",
  "word_count": 75
}
```

### Diagnosis from trace

The card is fact-ish, but it is not an insight. It names a record, uses a banned-feeling generic frame ("rollercoaster"), does not explain the cause, does not compare Auburn to history or peers, does not use the Auburn profile voice, does not include a visual, and does not know whether a sibling card already made the same point. That is exactly what the new architecture has to make impossible.

## 14. Appendix C: Cut Ideas

| Idea | Reason parked |
|---|---|
| Garbage-Time Mirage | Useful, but needs play-level garbage-time model first. |
| Red-Zone Lie Detector | Good sub-card inside Identity Crisis; not top-15 standalone. |
| Fourth-Quarter Truth | Overlaps with The Hinge and Counterfactual Ladder. |
| Home-Field Tax | Keep for P2; Weather Tax and Rivalry Thermostat are sharper. |
| Style-Mismatch Tag | Better as matchup-week product than offseason Chronicle. |
| Draft Afterglow | Subset of NFL Pipeline Audit. |
| Spring Practice Mismatch | Needs reliable spring practice sourcing. |
| Conference Escape Route | Useful in-season; less offseason screenshot value. |
| Program Floor Detector | Fold into Trophy Case Stress. |
| Talent-Development Gap | Fold into Recruit-to-Result and Returning Production Trap. |
| Depth Chart Debt | Fold into Portal Pressure Map. |
| Trophy Room Dust | Too close to snark; use Trophy Case Stress with empathy. |
