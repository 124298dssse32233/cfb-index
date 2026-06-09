# CFB Index — Chronicle Quality Brainstorm Brief

**For:** ChatGPT Codex
**Date:** May 23, 2026 (offseason — 2025 season just concluded, 2026 season kicks off in late August)
**Output target:** `CHRONICLE_QUALITY_PROPOSAL_v1.md` (single self-contained Markdown document)

---

## TL;DR Mission

CFB Index ships an LLM-generated narrative module called **Chronicle**. Cards appear at `/chronicle/<slug>.html`, on team pages (`/teams/<slug>.html` → "AI Narratives" section), and inline on player pages. The pipeline runs on a local RTX 5070 via Ollama (Mistral Nemo writer + Qwen3-8B planner/critic) on a self-hosted Alienware runner.

**Two acute problems:**
1. **Quality is mid.** Cards feel generic — "Team X had a rollercoaster season with a 5-7 record." That's a stat. It's not an insight.
2. **Same-team cards are near-duplicates.** Generating 3 cards for Auburn yields 3 paraphrases of the same season-record observation.

**Your mission:** Read the codebase, read the live site, scan the competitive landscape, and produce a single deliverable that proposes:
- New card *categories* (specific shapes of insight nobody else publishes)
- Anti-duplication architecture (mechanical guarantees, not just "ask the LLM nicely")
- World-class data visualizations paired with cards
- A pipeline refactor plan that lands on local hardware + selective paid-LLM spend
- A sprint-by-sprint implementation roadmap

**Uniqueness comes from the *treatment*, not the data.** You are free to use *any* data source we have access to or can reasonably acquire — including:
- **CFBD API tier 2** (PPA / advanced box scores / recruits / coaches / talent / returning production / portal / draft / SP+ / Elo / FPI mirror / play-by-play / drives / lines / venues / weather — basically the whole stack). Already wired in `src/cfb_rankings/ingest/sources/cfbd_*.py`.
- Polymarket prediction-market feeds (already wired)
- Reddit /r/CFB JSON (free)
- News scrapes / RSS (whatever's permitted)
- Wikipedia
- Sports Reference (within ToS)
- Any other paid API the user is willing to add ($20/mo tier is fair game; flag bigger spends)

What competitors *also* have (ESPN, Athletic, On3, PFF, 247) is mostly the same raw data. They don't all do the *interesting things* with it. **That's the gap.** Chronicle's edge is in synthesis, comparison, counterfactuals, voice, framing, and pairing-with-viz — not in owning a secret stat. Don't pretend we have a moat we don't.

The user wants Chronicle to be the thing 2026 CFB fans *screenshot and tweet*. Aim for "I've never seen anyone else frame it that way," not "this is a competent ESPN clone."

---

## Phase 1 — Self-brief (read these BEFORE you write anything)

### 1a. Codebase orientation (in this order)

| File | What you learn |
|------|----------------|
| `CLAUDE.md` | Project orientation, conventions, recent gotchas, module inventory |
| `docs/octopus/discover.md` | Current-state audit (latest comprehensive) |
| `docs/octopus/define.md` | Fix charter & triage |
| `WORLD_CLASS_GAP_AUDIT_2026_05_22.md` | Latest gap analysis — read in full |
| `TEAM_PAGE_WORLD_CLASS_BRIEF.md` | Vision for team pages |
| `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` | Vision for player pages |
| `FAN_INTEL_SOURCE_STRATEGY.md` | Reddit/news/betting signal source-of-truth |
| `docs/design-system/00-tokens.md` | Color, type, design tokens (locked) |
| `docs/design-system/30-page-archetypes.md` | 6 archetypes & their module contracts |
| `docs/design-system/31-chart-vocabulary.md` | 6 allowed chart types (your viz proposals should justify extending this) |
| `docs/design-system/32-receipt-pattern.md` | Citation wire format & density rules |
| `docs/design-system/33-confidence-signaling.md` | 3-band confidence model |

### 1b. Chronicle module deep dive

Walk every file in `src/cfb_rankings/chronicle/`:

| File | What to extract |
|------|-----------------|
| `__init__.py` | Public surface |
| `config.py` | Tier policy (S/T1/T2/T3), model routing, thresholds |
| `pipeline.py` | 5-agent cascade orchestration |
| `prompts.py` | Current Planner / Writer / FactCritic / VoiceCritic / Refiner prompts — **quote them verbatim in your diagnosis** |
| `evidence_sources.py` | All 10+ source fetchers + `EVIDENCE_SOURCE_ROUTING` (what cards pull from what sources) |
| `retriever.py` | SQL + FTS5 hybrid retrieval |
| `runtime.py` | Backend abstraction (Ollama / DeepInfra / Null) |
| `cache.py` | `chronicle_card_cache` read/write |
| `lkg.py` | Last-Known-Good fallback |
| `eval.py` | FActScore heuristic, GEval, OVERLAP_THRESHOLD=0.2 |
| `antislop.py` | 56-phrase banlist |
| `source_trust.py` | Per-source trust tier |
| `observability.py` | Logging |
| `lora_corpus.py` | Voice LoRA corpus builder |
| `run.py` | CLI entry-point |

Then trace one card end-to-end: pick `auburn` echo card week 14 2024, follow Planner→Writer→FactCritic→VoiceCritic→cache. Quote the actual prompt strings, the actual evidence pool, the actual generated body. That trace becomes Section 2 of your deliverable.

### 1c. Data inventory (everything we have or can get)

Walk these to build a complete asset inventory. The goal is **not** to find a proprietary moat — it's to know every lever you can pull when synthesizing.

**Local DB tables** (walk `migrations/` for the complete schema):
- `chronicle_card_cache` (existing LLM outputs — sample 30+ to study quality baseline)
- `season_narrative_arc`, `narrative_frame_stack`, `season_narrative_state`
- `editorial_citations`, `confidence_calibration`
- `games`, `team_chronicle_observations`
- `narrative_phrase_tokens`, `chronicle_slop_observations`
- `pipeline_checkpoints`, `calendar_pressure`
- Plus everything CFBD ingests have written to (look for it)

**CFBD API tier 2 (full access; we pay for it)** — `src/cfb_rankings/ingest/sources/cfbd_*.py`. Endpoints to know:
- `/games` + `/games/teams` (schedule, results)
- `/games/players` (per-game player stat lines)
- `/play/types` + `/plays` (play-by-play)
- `/drives` (drive-by-drive)
- `/ppa/games` / `/ppa/players/season` / `/ppa/predicted` (Predicted Points Added — the modern EPA equivalent)
- `/stats/season/advanced` + `/stats/game/advanced` (success rate, explosiveness, finishing-drives, havoc, line yards, stuff rate, second-level / open-field yards)
- `/lines` (Vegas spreads / O-U / moneyline history per game)
- `/venues` + `/games/weather` (yes, weather)
- `/recruiting/players` + `/recruiting/teams` + `/recruiting/groups`
- `/player/portal` (transfer portal in/out, per year)
- `/player/returning` (returning production %)
- `/talent` (composite team talent)
- `/draft/picks` + `/draft/positions` + `/draft/teams` (NFL Draft 2002-present)
- `/coaches` (HC tenure)
- `/ratings/sp` + `/ratings/sp/conferences` + `/ratings/srs` + `/ratings/elo` + `/ratings/fpi` (SP+, SRS, Elo, FPI — yes, all of them)
- `/metrics/wp` + `/metrics/wp/pregame` (win probability per play and pregame)
- `/conferences` + `/teams` + `/teams/matchup` + `/teams/fbs`
- `/calendar` (week boundaries, postseason dates)
- Most of these have multi-decade history.

**Already-wired external feeds:**
- Polymarket prediction-market quotes (already in DB)
- Reddit /r/CFB free JSON endpoints
- News scrapes (whichever feeds `fan_intelligence`)
- Honors / awards scraping (`ingest/honors.py`)

**Editorial assets we authored:**
- `profiles/*.md` — 127 hand-authored fanbase identity YAMLs (mascot voice, ritual, fight song, aspiration ladder, fanbase identity, page tone strip)
- `data/voice_corpus.jsonl` — 329 voice passages with [CFB-INDEX-VOICE] sentinel
- `src/cfb_rankings/fan_intelligence.py` — mood-card + belief computation
- `editorial_citations` table — pre-built receipt pool
- 23 team-page modules, 8 player-page v2 modules — these compute derived metrics Chronicle can ref

**External you should propose adding** (flag spend if any):
- Massey Composite / Sagarin (free; scrape or RSS)
- Bart Torvik's CFB ratings (free; scrape)
- ESPN unofficial JSON endpoints (free; standings, schedule, transactions)
- The Athletic RSS / Substack RSS for editorial pulse (free)
- DraftKings / FanDuel public odds feeds (free or low-tier paid)
- Twitter/X via a low-volume search API or `r/CFB` discussion mining (light)
- Wikipedia REST API for historical anchor facts (free)
- Football Outsiders / FEI archive (paid; flag cost)
- Pro Football Focus team grades (paid; flag cost; valuable for "graded badly but won" cards)

**Data currently sitting in DB but Chronicle ISN'T using:**
- Aspiration ladder (`profiles`)
- Per-team mascot voice & fight song (`profiles`)
- Heisman model probabilities + per-week trajectory
- NFL Draft pipeline (`draft_picks` 2018-2025)
- Recruiting class strength (`sp_plus_recruiting` + CFBD recruits)
- Transfer portal in/out (2018-2025)
- Returning production / talent metrics
- Coaches table (HC tenure, scheme, era)
- Polymarket quotes
- Bowl history (`postseason_games`)
- Conference standings history
- `fan_intelligence` Reddit/news/betting signals
- `confidence_calibration` per-team-week distribution data
- `editorial_citations` receipt pool

**The leverage isn't "we have rare data."** It's "we have *all* the data, *all* in one place, with a voice register + design system + 119-team coverage." Use that.

This inventory matters. Every proposed card type must name which datasets feed it.

### 1d. Live site reconnaissance

Visit these URLs (live alias: `https://wonderful-margulis-8ec96b.vercel.app`):

**Homepage & navigation:**
- `/` — what's featured?
- `/about/`
- `/methodology/index.html`
- `/methodology/fan-intelligence.html`
- `/editions/index.html`

**Team pages (representative range — read in full):**
- `/teams/alabama.html` (blue-blood, has hand-authored profile YAML)
- `/teams/auburn.html` (recently struggling SEC)
- `/teams/wyoming.html` (G5, mid-tier, has YAML)
- `/teams/army.html` (G5, identity-rich)
- `/teams/massachusetts.html` (worst FBS — does the system gracefully handle bad teams?)
- `/teams/notre-dame.html`
- `/teams/oregon.html`

**Chronicle (the actual cards):**
- `/chronicle/index.html`
- `/chronicle/alabama.html` (and 3–4 others — quote real card bodies in your diagnosis)

**Player pages:**
- Pick the top-3 Heisman candidates from the 2025 season and read their pages

**Then take notes on:**
- What's the current visual language? (Bebas Neue, Source Serif Pro, dark theme with per-team accent)
- What modules already exist on team pages that Chronicle could *play off*? (Page Tone Strip, Kickoff Countdown, Offseason Pulse, Top Commits, NFL Draft Pipeline, Recent Form, Season Standing, Program Prestige, Trajectory chip, Peer Comparator, On This Day, Wrapped, Fanbase Health, Conference Standing, Ceiling/Floor, Home-Field Advantage, Moment of the Year, Schedule Strength, Statement Wins, Bowl History — these exist. Use them as anchors.)
- What's the current Chronicle card density per team? Quality? Tone?
- Where does the visual hierarchy let down? Where could a chart-paired card explode the page open?

### 1e. Competitive landscape scan

Survey what competitors offer for the same teams. Do at least these:

| Source | What to look for |
|--------|------------------|
| espn.com/college-football/team/_/id/333/alabama-crimson-tide | Schedule, news, stats — what categorical insights? |
| theathletic.com/team/alabama-crimson-tide/ | Long-form takes, beat-writer voice |
| on3.com/teams/alabama-crimson-tide-football/ | Recruiting, NIL angle |
| 247sports.com/college/alabama | Recruiting, message-board takes |
| cfb.sports-reference.com/schools/alabama/ | Deep historical |
| pff.com/college (Premium tier — find one team's free-tier sample) | Grades, stat angles |
| fanmatch.predict.com / Bart Torvik / Sagarin / Massey | Ratings & projections |
| /r/CFB top posts last 30 days (search `top this month`) | What posts get fan engagement? Why? |
| Substacks: Spencer Hall, Bill Connelly (ESPN), Andy Staples (On3), Brian Fremeau | Editorial voice samples |
| Action Network / Saturday Down South / The Comeback | Betting & emotion angles |
| Podcast topic scans (PFF College Football, Bear Logic, Solid Verbal episodes May 2026) | What angles are CFB fans hearing about right now? |

For each, note:
- 3 things they do well
- 1–2 *gaps* — angles that nobody covers, or that everyone covers but badly — that Chronicle could exploit
- 1 visualization they use (or notably lack)

**Then run the novelty triangulation.** Most CFB sites have access to the *same* underlying data (CFBD, ESPN feeds, Vegas lines). The differentiator is treatment. For each candidate card type you'll later propose in §3A, classify it:

- **A. Nobody does this** — the angle doesn't exist on the public web. Highest value, hardest to defend you didn't miss it.
- **B. One niche outlet does it** (e.g., Bill Connelly's SP+ posts cover identity-style stats; Bart Torvik does pace splits) — but their audience is small and they don't pair with voice / viz / fanbase-specific framing.
- **C. Many do it but poorly** — e.g., "team X had a rollercoaster season" is everywhere; Chronicle's version must do it 10× better via specificity, comparison, and voice.
- **D. Mainstream covers it well** — drop or only include if Chronicle's voice/viz materially elevates it.

Anything you propose that lands in (D) without a clear "here's what we add" should be cut. Anything in (A) needs an explicit "I checked these 5 outlets, none of them publish this angle" footnote.

### 1f. Recent CFB context as of May 23, 2026

- 2025 season completed (NCG was January 2026, recap state in site)
- Spring practice / transfer portal cycle just ended
- 2026 schedule is set, kickoff in ~14 weeks
- Recruiting rankings for 2026 class largely locked
- Coaching carousel for 2026 settled

Cards generated *right now* are offseason-themed. What does an offseason CFB fan actually want? (Hint: nostalgia, "what if" speculation, recruiting hype, schedule reactions, NFL Draft afterglow, depth-chart speculation, transfer-portal winners-and-losers, way-too-early Top 25, narrative previews of fall.)

---

## Phase 2 — Diagnose (be brutal)

In the deliverable's "Current State Diagnosis" section, answer:

1. **What categories of insight are current Chronicle cards limited to?** Survey the existing `chronicle_card_cache` rows (sample 30+ at random; quote 5 verbatim).
2. **What "shapes" of insight are missing?** Use a categorical framework like:
   - *Causation* ("they lost because their O-line allowed 38 sacks, 7th-most in FBS")
   - *Counterfactual* ("if 3 one-score games had flipped, they're 8-4 and bowl-eligible")
   - *Comparison-to-history* ("first 0-3 start since 1956")
   - *Comparison-to-peers* ("only FBS team in 2025 to do X")
   - *Market arbitrage* ("Polymarket says X, Vegas says Y, gap means Z")
   - *Voice / character* ("the fanbase that invented Y is now living through Z")
   - *Counterintuitive* ("their best win came on their worst day statistically")
   - *Trajectory / momentum* ("4 of their last 5 third-down conversions came on a screen")
   - *Receipt-heavy* ("here are 3 specific moments")
   - *Mascot / identity* ("Sparty would never forgive this")
   - *Recruit-to-result* ("the 2022 #4 recruit threw the pick that ended their season")
   - *Coaching-tree* ("their DC played for the OC's father")
3. **Why are multi-card-per-team outputs near-duplicates?** Trace it in the code:
   - Is the planner enforcing angle diversity?
   - Is the writer being given the same evidence pool every time?
   - Is there a per-slot frame assignment, or just "make 3 cards"?
   - Is post-generation similarity scored & rejected?
   Quote the offending code paths.
4. **Where is the quality ceiling capped?** Data? Prompt? Model? Eval gate? Render? Cite specific files.

---

## Phase 3 — Brainstorm (greedy, then triage)

### 3A. Card-type taxonomy

Current types (per `EVIDENCE_SOURCE_ROUTING` in `evidence_sources.py`): echo, flashpoint, retroactive, player_arc, devil_card, heisman_trajectory + others.

**Propose 30+ new card types**, then triage to the top 15. For each top-15 type, deliver:

| Field | Spec |
|-------|------|
| Name | E.g., "Counterfactual Ladder", "Decade Echo", "Market Arbitrage Watch" |
| One-paragraph spec | What kind of claim, what shape, what tone |
| Primary data sources | Concrete table names AND/OR CFBD endpoints AND/OR external feeds |
| 2 example bodies | 60–80 words each, for REAL teams using REAL 2025 data. Voice-correct. |
| Viz pairing | Which proposed viz (from §3C) attaches |
| Tier | S / T1 / T2 / T3 (cost-tier; what model writes it) |
| Anti-duplication slot | What "angle slot" it occupies (so a team's 6 cards span 6 different angles) |
| Novelty class (A/B/C/D per §1e) | A = nobody, B = niche, C = many do it badly, D = mainstream covers well |
| Competitive footnote | 1 line: which competitor(s) (if any) do something similar, and how Chronicle differs |

**Seeds (you should produce 30+ — these are just to calibrate):**

- *"What-If Tree"* — For a 5-7 team: "If they win the 3 one-score losses, they're 8-4 + bowl + coach-extension. They were +2 in turnover margin in two of those three. Here's why each broke." Tier T1, viz = win-prob-flip strip.
- *"Decade Echo"* — "This is Texas's first 0-3 start since 1956. The last three to do it were Fred Akers '78, Mack Brown '10, and Steve Sarkisian '21. All three recovered to win a New Year's Six bowl within 2 years." Tier T1, viz = anniversary spark.
- *"Identity Crisis"* — "Wyoming has the 7th-best run defense by EPA/play allowed and the worst 3rd-down offense in FBS. They play three different styles of football on the same field." Tier T2.
- *"Market Arbitrage Watch"* — "Polymarket has Penn State at 14% to win the Big Ten East. Vegas has them at 18%. The 4-point gap implies betting markets see the OSU/Mich injury thread Polymarket hasn't yet priced." Tier T1, viz = tri-panel probability comparator.
- *"Mascot Voice Card"* — Authored from `profiles/<slug>.md` voice register. First-person fanbase POV. Tier S.
- *"Recruit-to-Result"* — "The 2023 #6 recruit in the country threw the interception that ended their playoff push. He's also the QB who beat them in 2024 — at his new school." Tier T1, viz = recruit→roster timeline arc.
- *"Coaching Tree Twist"* — "Their new OC is the godson of the HC's college roommate. Both played for the same OC in 1998 at Toledo. Toledo is on their 2027 schedule." Tier T2.
- *"NFL Pipeline Audit"* — "11 NFL Draft picks since 2018. 9 of them played for two-different DBs coordinators. The 9 are 38-12 in the NFL through year 2; the 2 are 6-22." Tier T1, viz = pipeline funnel.
- *"Fan Mood Index Backward"* — Pull `fan_intelligence` Reddit+news+betting signals from 6 specific dates this past season; tell the story of the fan rollercoaster. Tier T2, viz = mood timeline.
- *"Anniversary Trap"* — "10 years ago this week, [moment]. Today, [contrast]. The team that played that day went 11-1. This team is 6-6." Tier T2.
- *"The Hinge"* — "Three plays defined their season. Here they are with diagrams." Tier S, viz = play diagrams.
- *"Schedule Lottery"* — "If their non-con had been the conference's softest, they'd be 9-3. If it had been the hardest, they'd be 4-8. They drew average — and went 6-6." Tier T2.
- *"Crystal Ball Recall"* — "Recruiting analysts called this class 'transformative' in 2022. Here's what each top-10 commit actually did. 4 transferred. 2 started Day 1. 1 made All-American." Tier T1.

### 3B. Anti-duplication architecture

The deliverable must include concrete mechanisms:

1. **Frame stack rotation** — When generating N cards for a team, draw N distinct frames from `narrative_frame_stack` (or invent a new table). Each card commits to its frame; subsequent cards cannot reuse.
2. **Angle-slot assignment** — Hard-coded slots ["trajectory", "identity", "market", "counterfactual", "comparison-history", "comparison-peers", "voice"] — when generating 6 cards, planner assigns one frame to each slot.
3. **Evidence-diversity constraint** — Each card must use a *primary* evidence source not used as primary by any other card for that team this season.
4. **Twin detector (post-gen)** — Compute embedding (BGE-M3 already available per `retriever.py`); reject if cosine > 0.85 with any existing card for same team-season.
5. **Banned-phrase rotation** — Beyond the 56-phrase banlist, dynamically ban the top-N nouns/verbs from the previous card when generating the next.
6. **Per-card "thesis sentence"** — Planner emits a thesis; writer expands. Two cards with embedding-similar theses are rejected before writing.

For each mechanism: pseudo-code, where it lands in `pipeline.py`, what migration adds the supporting table, test plan.

### 3C. World-class data viz catalog

Current vocab (per `docs/design-system/31-chart-vocabulary.md`): percentile bar, trajectory spark, bump chart, annotated line, small multiples, heatmap.

**Propose 15+ new viz forms. For each:**

| Field | Spec |
|-------|------|
| Name | E.g., "Win-Prob Flip Strip", "Recruit→Result Arc" |
| Sketch | ASCII diagram OR inline SVG mockup |
| Data sources | Concrete table/column names |
| Render approach | Static SVG at build-time / Vega-Lite / D3 / Plotly / canvas — pick one and justify |
| Card type pairing | Which §3A card types attach |
| Build cost | Where in build pipeline (per-team page render? Background job? CI step?) |
| Risk | Mobile readability, data freshness, accessibility |

**Seeds:**

- **Per-game Momentum Strip** — Horizontal strip of 12 cells, one per game, color-coded by win-prob delta. Hover = score + win-prob curve.
- **Win-Prob Flip Strip** — Same shape, but cells highlight the 3 closest losses where a 1-play swing flips the result.
- **Conference Standings Sankey** — "If these 3 games flip, here's the standings." Animated on hover.
- **Identity Radar (5-axis)** — Tempo / Explosive Play Rate / RZ Eff / 3rd-Down / TFL Rate. Overlaid: team vs. conference median vs. national median.
- **Recruit→Roster Arc** — Per recruiting class: HS rank → CFB depth chart status → NFL draft position. Curve per recruit.
- **Polymarket-Vegas-FPI Tri-Pane** — Three probability bars side-by-side; gap callouts in copy.
- **Heisman Bump Chart** — Weekly Heisman probability for top-12 candidates; player names labeled.
- **Per-Week Mood Timeline** — Reddit/news/betting sentiment as 3-line chart with annotations for key games.
- **Coaching Lineage Tree** — Vertical tree showing HC → OC → QB-coach → recruit-coordinator chain across multiple programs.
- **NFL Pipeline Funnel** — Sankey from recruit star rating → years played → draft round → NFL career length.
- **Decade-Anniversary Spark** — Today vs. 10/20/30 years ago — small multiple sparks.
- **Play-Diagram Tile** — SVG of a single play (the season-defining one) with annotation.
- **Transfer Portal Net** — In vs. out arrows, per position group, with star-rating weights.
- **Schedule-Strength Bracket** — 12 games sorted by opponent quality; each cell = result with EPA delta.

### 3D. Evidence-source-to-card-type map

Map every dataset from §1c — local DB, CFBD tier 2 endpoints, Polymarket, free external feeds, and any new sources you propose adding — to the §3A card types they enable. Output a table:

| Dataset / endpoint | Source file or API path | Already in DB? | Card types it unlocks | Acquisition cost |
|--------------------|-------------------------|----------------|----------------------|------------------|
| `profiles/<slug>.md` aspiration ladder | `team_pages/data.py` Profile dataclass | Yes | Mascot Voice, Identity Crisis, Anniversary Trap | $0 |
| `draft_picks` 2018-2025 | `ingest/sources/cfbd_draft.py` | Yes (CFBD ingest) | NFL Pipeline Audit, Recruit-to-Result | $0 (CFBD tier 2 paid) |
| `fan_intelligence` Reddit+news+betting | `fan_intelligence.py` | Yes | Fan Mood Index Backward, Market Arbitrage | $0 |
| CFBD `/plays` (PBP) | `cfbd_plays.py` (or wire if not) | Probably partial | The Hinge, Counterfactual Ladder, Win-Prob Flip | $0 (CFBD tier 2) |
| CFBD `/ppa/players/season` | wire if needed | TBD | PPA Outlier, Hidden Star, Replacement-Cost | $0 (CFBD tier 2) |
| CFBD `/stats/season/advanced` | wire if needed | TBD | Identity Crisis (havoc/explosiveness/success rate angles) | $0 (CFBD tier 2) |
| CFBD `/lines` | wire if needed | TBD | Market Arbitrage Watch, Cover-Rate Trail, Closing-Line Value | $0 (CFBD tier 2) |
| CFBD `/games/weather` | wire if needed | TBD | Weather Anomaly, "Played in 17 mph wind, threw 47 times" | $0 (CFBD tier 2) |
| Polymarket quotes | `polymarket_*` table | Yes | Market Arbitrage, Crystal Ball Recall | $0 |
| Massey Composite / Sagarin | scrape (propose) | No | Rating Disagreement, "The Models Are Split" | $0 (free scrape) |
| Bart Torvik CFB ratings | scrape (propose) | No | Style-Mismatch Tag, Pace Anomaly | $0 (free) |
| /r/CFB top posts | Reddit JSON | Partial via fan_intel | Fan Sentiment Anomaly, "What Reddit Cared About" | $0 |
| Wikipedia historical | REST API (propose) | No | Decade Echo, Anniversary Trap (historical anchors) | $0 |
| ESPN unofficial JSON | propose | No | Cross-sport callbacks, transaction timeline | $0 |
| ... | ... | ... | ... | ... |

This table is mission-critical. **You are not limited to data we already ingest.** If a CFBD tier 2 endpoint or a free scrape unlocks a great card, propose wiring it. Flag any paid-tier external (PFF, FEI) with explicit cost.

The user's request is "use any data, but do unique things with it." This table is where you show what unique syntheses become possible when you combine 3+ sources nobody else combines (e.g., CFBD PPA × Polymarket × per-team voice register = a "market-vs-PPA-vs-fanbase-mood" card no other site can produce, not because the data is proprietary but because nobody else has stitched those three sources together with a 127-fanbase voice library).

### 3E. Pipeline architecture refactor

Propose concrete changes. Examples:

1. **Two-pass generation**:
   - Pass A: "Narrative Frame Planner" — given team + season + retrieved evidence, emit a JSON list of N frame plans (each with: angle slot, thesis sentence, primary evidence source IDs, target viz, target word count).
   - Pass B: Per-frame card writer — given frame plan, write the card. Critic + refiner per card.
2. **New agent roles**:
   - *Insight Critic* — rejects cards scoring low on novelty + specificity + emotional resonance (rubric below).
   - *Comparison Critic* — rejects cards lacking at least one historical/peer/counterfactual anchor.
   - *Visual Director* — emits viz spec alongside copy (chart type + data query).
3. **Per-team narrative state machine**:
   - `season_narrative_state` table: track frames consumed, themes touched, citations used.
   - Reject cards that repeat consumed frames.
4. **Eval upgrade**:
   - Replace pure FActScore with a composite "Insight Quality Score":
     - Factual correctness (current FActScore, weight 0.4)
     - Specificity (rare-term density, weight 0.2)
     - Novelty vs. existing cards same team-season (embedding distance, weight 0.2)
     - Receipt density (citations per 100 words, weight 0.1)
     - Voice alignment (cosine to voice corpus centroid, weight 0.1)
5. **Caching strategy**:
   - Per-frame hash; rebuild affected frames on data refresh, not all cards.

For each refactor: which file changes, which migration adds the supporting schema, test coverage plan.

### 3F. Hardware + cost plan

User has:
- RTX 5070 (16GB VRAM)
- Ollama: `mistral-nemo:12b-instruct-2407-q4_K_M` (writer, ~7.5GB) + `qwen3:8b` (planner/critic, ~5.2GB)
- DeepInfra fallback ($0.02/$0.04 per M tokens for Mistral Nemo)
- Self-hosted Alienware GitHub Actions runner
- Willing to spend "some" beyond local

Propose tier-by-tier:

| Tier | Cards | Model used | Cost per card | Cost per FBS-week (119 teams × 6 cards = 714) |
|------|-------|------------|---------------|-----------------------------------------------|
| S    | top-25 teams + top-25 players flagship | Claude Sonnet 4 or GPT-5 (paid) for Writer + Insight Critic; Qwen3-8B local for Planner | ~$? | ~$? |
| T1   | top-50 teams | Local Mistral Nemo + paid Insight Critic (Sonnet) | ~$? | ~$? |
| T2   | ranks 51-100 | All local | ~$0 | ~$0 (compute time only) |
| T3   | long-tail | Template-fill + Mistral Nemo local | ~$0 | ~$0 |

Then propose:
- Which tasks **must** stay local (latency / privacy / cost)
- Which are worth paying for (insight-critic on flagship cards; refiner on top-25 only; etc.)
- Estimated total weekly $ for full FBS coverage
- An overnight-cron architecture so the user's desktop runs the heavy work while they sleep

### 3G. Editorial voice fit-test

Reference `data/voice_corpus.jsonl` and pick 3 hand-authored profiles (e.g., `profiles/alabama.md`, `profiles/wyoming.md`, `profiles/army.md`). For each, write one example card in §3A's catalog and demonstrate that it sounds like *that fanbase's voice*, not a generic LLM voice.

The voice register:
- Specific (named players, weeks, scores), not generic ("the team")
- Confident (no hedging, no "perhaps", no "it may be argued")
- Curious, not preachy
- Receipt-cited (at least one `[src:...]` per 60 words)
- Distinct per fanbase

---

## Phase 4 — Deliverable spec

File: `CHRONICLE_QUALITY_PROPOSAL_v1.md` at repo root.

Required sections:

1. **TL;DR** — 250 words max. What changes, why, expected impact.
2. **Current State Diagnosis** — what's broken, with quoted real card bodies as evidence.
3. **Top 15 New Card Types** — full table per §3A spec.
4. **Anti-Duplication Architecture** — mechanisms + pseudo-code + test plan.
5. **New Viz Catalog (15+)** — full table per §3C spec.
6. **Evidence-Source-to-Card-Type Map** — table per §3D.
7. **Pipeline Refactor Plan** — per §3E, step-by-step, file-by-file.
8. **Hardware + Cost Plan** — per §3F.
9. **Implementation Roadmap** — sprint-by-sprint, P0 → P3, with effort estimates in dev-days and explicit dependencies.
10. **Voice Fit-Test** — 3 example cards in 3 voices.
11. **Risks & Open Questions** — what could blow up, what needs user decision.
12. **Appendix A: Competitive Scan Notes** — per §1e, structured.
13. **Appendix B: Codebase Trace** — the one card walked end-to-end with quoted prompts/evidence/output.

### Format rules

- **Tables** for catalogs (markdown table syntax).
- **Code blocks** for prompts, pseudo-code, SQL.
- **Concrete examples** — never "a card about X." Write the actual 60–80 word body.
- **Cite file paths and table names** (`src/cfb_rankings/chronicle/pipeline.py:142`, `chronicle_card_cache.fact_critic_score`).
- **Use real team names and 2025 data**. If you don't have a number, say so explicitly — don't fabricate.
- **No filler.** If a section can't be filled with substance, omit it and say why.

---

## Constraints & ground rules

- **You read the codebase yourself.** Do not ask the user for code paths; explore them.
- **You read the live site yourself.** WebFetch `https://wonderful-margulis-8ec96b.vercel.app/...`
- **Date is May 23, 2026.** All competitive references should be current (PFF College's May 2026 takes, /r/CFB top posts last 30 days, etc.).
- **Data is wide-open.** Use any source — local DB, CFBD tier 2 (we pay for it), Polymarket, Reddit, free scrapes, Wikipedia, ESPN unofficial endpoints, anything ToS-compliant. Flag any paid external (PFF, FEI, Sportradar) with explicit per-month cost. The constraint is "is the *synthesis* unique," not "is the *data* unique."
- **Numbers must be real or marked as TODO.** No hallucinated stats. If you don't yet have a number for an example body, write the body with `[TODO: pull X from CFBD /ppa/players/season]` inline.
- **Voice must match.** If you propose a "Mascot Voice Card," write it in that mascot's actual voice — check `profiles/<slug>.md`.
- **Stay scoped.** This is a brainstorm + architecture proposal. Don't write production code. Pseudo-code only.
- **Be greedy.** 30+ card ideas, 15+ viz ideas, then triage to top 15 + top 15. Show your work — list the cut ideas in an appendix with one-line reasons.
- **Be honest.** Don't pretend we have a moat we don't. Don't pretend a card is novel when ESPN already does it. If a competitor already publishes the angle you're proposing, say so and explain how Chronicle's take is materially different (voice / framing / pairing / depth).

---

## Success criteria

The user reads the proposal and reacts:
1. "I haven't seen these angles anywhere on the CFB web — and Codex showed me the receipts that nobody else does them."
2. "The anti-duplication mechanism actually solves the problem I had."
3. "I can see exactly how to build the top 5 things this sprint."
4. "These viz ideas would make Chronicle the most visually arresting CFB editorial product on the web."
5. "The cost estimate is realistic and the local-vs-paid split makes sense."
6. "The new CFBD endpoints to wire are concrete and the synthesis examples are believable."

If half your top-15 cards are class C/D (mainstream covers it) without a clearly differentiated treatment, the proposal fails. Push hard for class A and B with explicit competitive footnotes.

If your proposal hits all five, it ships and the user spends the next quarter implementing it. If it's a generic "use better prompts" doc, it goes in the trash.

Go.
