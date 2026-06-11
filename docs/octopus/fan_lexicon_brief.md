# The Language Layer — Fan Discourse Storytelling Brief

_Drafted 2026-06-10. Ideation brief — design-system chart restrictions intentionally set aside per Kevin; the best format wins. Statistical + product research synthesized from a June-2026 state-of-the-art sweep._

## Thesis

CFB fans experience their team as an unfolding story — each day, week, season, and decade a chapter. We hold 189k fan-conversation documents (176.7k team-tagged, 5.4k player-tagged, Reddit backfill to 2014) with per-document sentiment, six-emotion shares, sarcasm, and toxicity already computed. **Nobody in sports media has shipped fan-language visualization.** The formats are proven elsewhere (Baseball Savant percentile sliders, The Pudding's hip-hop vocabulary ratio bars, Spotify Wrapped's Listening Age / era-naming, Reddit Answers' cited synthesis) — the application to fandom is unclaimed territory. We have the corpus, the local LLM ($0 marginal cost), and the eval machinery (Chronicle FActScore gates) to claim it.

## Statistical foundation (settled — do not relitigate)

- **Keyness measure: weighted log-odds with informative Dirichlet prior** (Monroe/Colaresi/Quinn "Fightin' Words"). NOT PMI (variance-blind, inflates rare words — fatal with our volume skew), NOT TF-IDF (not a comparison statistic). Prior from the full CFB corpus shrinks rare-word noise; yields z-scores to threshold (≥1.96 + min raw count floor).
- **Fan-facing effect size: LogRatio** ("fans say 'dawg' 8.2× more than the rest of CFB") — each point = a doubling; explainable in one sentence.
- **LLM concept layer: LLooM/D5-style concept induction** via the box Ollama models — merge surface variants ("cooked"/"we're cooked"/"szn over") into named concepts with explicit inclusion criteria; write the comparative sentence for rivalry mirrors. Post-hoc attribution check (more reliable than generation-time citing), evidence floors, suppress-below-floor — same pattern Chronicle already implements.
- **Citations everywhere**: every aggregate claim links to real posts (we have `source_url`) + a prevalence count ("214 of 1,377 comments this week"). Reddit Answers proved this UX; ESPN's AI-recap backlash proved its absence kills trust.

## Data reality (design around this)

| Fact | Implication |
|---|---|
| Volume skew: Michigan 37.7k docs, Oregon 31.7k, FSU 24.9k, PSU 22.5k, OSU 21.6k → cliff → median team ~650 | Flagship features launch for top-~25 volume teams; confidence-floor fallbacks elsewhere (existing chip pattern) |
| Reddit backfill to 2014-09 | Decade-scale features are REAL for Reddit-heavy programs |
| Live collection only since 2026-05-13 (~4 wks) | Offseason baseline now; in-season volume will be several× higher — build for that |
| 1,051 players tagged; top players 150-330 docs each | Descriptor features viable for ~top 100 players now, grows weekly |
| Emotion shares + sarcasm + toxicity per target already computed | Fanbase-personality features need ZERO new NLP — just aggregation |
| `narrative_phrase_tokens` + `phrase_mentions_weekly` tables exist, empty | Schema already anticipated this layer — populate, don't invent |
| Lexicon tracker (Wave 0) = 22 fixed curated terms, daily counts | New layer is emergent/per-entity keyness — orthogonal, complementary |

---

## The Portfolio

### Tier 1 — Flagship (the moat)

#### 1. The Lexicon — team vocabulary fingerprint
**What:** Per-team signature words/phrases by weighted log-odds vs the full corpus, LLM-clustered into named concepts. Rendered Pudding-style: ranked ratio bars ("**'dawg'** — 8.2× the rest of CFB"), one superlative headline ("The most Georgia word in college football: ___"), tap-through to receipts (real posts).
**Why world-class:** The single most shareable artifact per fanbase. Identity-affirming, screenshot-native, factually bulletproof (it's counting).
**Time dimension:** Per-season signatures → "the words of 2019 vs 2026" strip on team pages; the decade story told in vocabulary.
**Surface:** Team page Act II ("Who We Are") + standalone `/lexicon/` tentpole with all teams.

#### 2. Eras — auto-named season chapters
**What:** Detect shift points in a team's weekly vocabulary + emotion mix (week-bucketed log-odds vs season baseline, change-point on the emotion shares), then the Chronicle pipeline NAMES each chapter — "The Fire-the-DC Weeks," "The Arch Ascendancy" — each era carrying its signature words, dominant emotion, defining game, and a receipt quote.
**Why world-class:** This IS the product thesis — the season literally rendered as a story with named chapters. Spotify's Music Evolution / era-naming mechanic, grounded in real linguistic shift, with citations. Nobody has this.
**The viz:** Horizontal era timeline — colored chapter bands over the season axis, era name set in display type, signature words underneath, game-result ticks annotated. Decade view: same mechanic, one band per season ("The Harbaugh Wars," "The Rebuild," "The Revenge Tour").
**Surface:** Team page hero-adjacent (this deserves prime placement) + season-recap tentpole.

#### 3. In Their Words — player descriptor constellation
**What:** Descriptors and phrases co-occurring with a player's name, LLM-clustered into named concepts, each with prevalence + verbatim quotes. The temporal cut is the story: descriptor drift week-over-week — `"project" → "starter" → "HIM"`.
**Why world-class:** Highest effort-to-impact in the portfolio — player tagging + sentiment already exist. The drift rail turns a tag cloud into a career narrative.
**The viz:** Concept chips sized by prevalence, colored by sentiment, each expandable to quotes; below it a drift rail — the dominant descriptor per week as a connected sequence.
**Bias guard (required):** The sports-linguistics literature shows descriptor bias by race (Black QBs "athletic," white QBs "smart"). Run a descriptor-distribution audit before launch; suppress or contextualize flagged dimensions.
**Surface:** Player page, alongside the existing Aura module (Aura = how much/how positive; this = the actual words).

#### 4. The Rivalry Mirror
**What:** For each rival pair, the language each fanbase uses about the OTHER, D5-style ("how does corpus A's description of X differ from corpus B's?"), split-panel mirror with receipts. Plus obsession asymmetry — who mentions whom more (extends Rent Free with the actual words).
**Why world-class:** Peak shareability — both fanbases screenshot it for opposite reasons. "Michigan fans on Ohio State: 'refs', 'lucky', 'paranoid'. Ohio State fans on Michigan: 'little brother', 'cheaters', 'rent free'."
**Surface:** Team page Act II next to Rent Free; rivalry-week tentpole pages.

### Tier 2 — Recurring beats (the habit loop)

#### 5. Word of the Week
**What:** Per-team + national: the term with the highest keyness this week vs the season baseline. One word, one ratio, one receipt quote, every week.
**Why:** A recurring beat creates the return visit. The archive becomes the season's spine — "2026 in 15 words" writes itself, and feeds Eras detection directly.
**Surface:** Team page chip + site-wide "This Week in Words" strip on the rankings board.

#### 6. Fanbase Personality
**What:** Savant-style percentile slider rows — each trait scored vs all 136 fanbases: Optimism, Doom, Coach-blame rate, Portal fixation, Rival obsession, Slang density, Analytics talk, Sarcasm rate. Top it with an assigned named persona ("The True Believers," "The Doom Scrollers," "The Spreadsheet Fans") à la Duolingo/Reddit Recap.
**Why:** Emotion shares + sarcasm are ALREADY computed per doc — this is pure aggregation + the lexical dims from the keyness engine. Persona naming gives fans an identity badge; percentile sliders give the receipts.
**Surface:** Team page Act II — natural sibling of Fanbase Health (Health = vitality gauge; Personality = character).

#### 7. What the Room Is Saying — cited synthesis
**What:** Upgrade The Room's LLM ledes to citation-grounded claims: embed → cluster → label → quantify → claim backed by verbatim quotes → post-hoc attribution check → evidence floor. "What 1,400 Michigan fans talked about this week," every claim with a count and links.
**Why:** Reddit Answers proved the UX at scale. Chronicle's eval machinery (FActScore gate, LKG cards) already implements the safety pattern — extend, don't rebuild.
**Surface:** The Room (team pages) + player Room cards.

### Tier 3 — Tentpoles (the calendar moments)

#### 8. Fanbase Wrapped — language edition
**What:** New cards in the existing `wrapped_stack`: Your Word of the Year · Your Loudest Week · The Player You Couldn't Stop Talking About · Your Most Delusional Moment (peak belief vs market gap — Delusion module crossover) · Your Vocabulary, As Eras.
**Surface:** Existing Wrapped module (post-bowl window) — extends, not new chrome.

#### 9. The Discourse Atlas
**What:** Which fanbases talk alike — embedding similarity over fanbase language signatures, clustered and mapped (The Pudding's rapper-cluster mechanic). "Iowa fans sound more like Wisconsin fans than like Iowa State fans."
**Surface:** National tentpole page; offseason content moment.

#### 10. Fanbase Age (hold for in-season data)
**What:** Spotify Listening Age analog — one provocative number per fanbase from slang-era markers (2014-corpus terms vs 2026 terms). Highest gimmick risk; needs a season of fresh data to calibrate honestly. Park it.

### Killed / replaced from the original list
- **Radar personality chart** → Savant percentile sliders (better comparison, better mobile, no radar distortion — right call even unconstrained).
- **Raw PMI signature words** → weighted log-odds w/ prior (PMI breaks on our volume skew).
- **Standalone "Vocabulary Drift" line chart** → folded into Eras (drift is the mechanism; eras are the story — ship the story).
- **Word clouds** → still dead even without design-system rules. Ratio bars beat them on every axis.

---

## Shared engine (one build powers everything)

**`discourse_keyness` weekly job** (new module, `src/cfb_rankings/discourse/`):
1. Tokenize + n-gram (1-3) team-tagged docs with body_text, per (team, week) and (team, season).
2. Weighted log-odds w/ Dirichlet prior vs full corpus (and vs season-baseline for weekly cuts). Z-score ≥1.96 + min-count floor.
3. Persist to the existing empty tables: `phrase_mentions_weekly` (weekly rollups + sample quotes) and `narrative_phrase_tokens` (phrase lifetimes: first_used_week / last_used_week / use_count — this IS the era-detection input).
4. LLM concept pass (box Ollama, Chronicle runtime): cluster variants → named concepts + inclusion criteria; descriptor extraction for player-tagged docs.
5. Post-hoc attribution: every stored concept keeps doc_ids → quotes render with links.

Features 1-9 are all views over this one engine + existing emotion aggregates. Internal QA: Scattertext plots per team before shipping a lexicon (analyst-only, never fan-facing).

## Rollout order

1. **Engine + The Lexicon** (top-25 volume teams, confidence floors elsewhere) — proves the stats layer, ships the most shareable artifact.
2. **In Their Words** (top ~100 players) — fastest win on existing tagging.
3. **Word of the Week** — starts the recurring beat + begins accumulating era-detection history.
4. **Fanbase Personality** — pure aggregation, no new NLP.
5. **Rivalry Mirror → Eras** — Eras lands best once weekly keyness history exists (a few in-season weeks deepen it; backfilled Reddit history seeds the decade view immediately).
6. **Cited Room synthesis / Wrapped cards / Atlas** — in-season and post-season moments.

## Risks
- **Toxicity/slur leakage** into surfaced terms: reuse Chronicle banlist + toxicity scores as a render filter; human-reviewable suppression list.
- **Descriptor bias** (player features): audit gate before launch, documented in the module.
- **Small-fanbase embarrassment** (thin lexicons look broken): hard confidence floors; "Growing signal" fallback per existing pattern.
- **Offseason vocabulary ≠ season vocabulary**: label offseason signatures as such; recompute season cuts once games begin.
