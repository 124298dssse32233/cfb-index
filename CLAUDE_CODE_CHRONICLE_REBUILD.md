# Claude Code — The Chronicle Rebuild

Paste this entire document into a fresh Claude Code session. Autonomous. Sonnet default; Haiku for candidate scanning + validation gate; Opus for the weekly top-1 card per blue-blood. Target budget: ~200k tokens.

**Do not run this in parallel to the sprint currently editing `chronicle_generator.py`.** Coordinate — if another sprint is touching the Chronicle generator, wait for it to land, then run this.

---

## Context

Current Chronicle output reads like a stats engine describing itself. Example observed on ND:

> **ANOMALY — 8 straight wins closing the season's sample**
> Running the last eight games end-to-end produces a run of 8 consecutive wins — a compression of outcome that a season's summary stat flattens. The pattern is often a better read of where the program is than any single number this table will print.
> *CFB Index game-log stat engine*

Problems: writes about statistics instead of about football; explains its own methodology; "stat engine" attribution leaks the pipeline; zero proper nouns beyond "Notre Dame"; generic ("every season produces one of these"); could swap team names and still read.

Target: Chronicle cards that read like what a sharp OneFootDown / BGG contributor would write. Real names, real archive connections, real source attribution, real program voice.

Full design: `docs/CHRONICLE_EDITORIAL_BRIEF.md` (read this FIRST — it's the voice manifesto, not optional context).

---

## Context documents — read these first in this order

1. `docs/CHRONICLE_EDITORIAL_BRIEF.md` — **required**. Contains the ten voice rules, the banned-phrase list, the pipeline, before/after examples.
2. `docs/design-system/12-modules-intel.md` §Chronicle — updated spec with data-stream table + validation gate.
3. `src/cfb_rankings/team_pages/chronicle_generator.py` — current generator, will be rebuilt
4. `profiles/notre-dame.md` — reference profile for voice fields (voice_register, identity_phrase, mantra, stock_phrases, mascot_voice, era_name_overrides, never_use). All 17 profiles follow the same structure.
5. `src/cfb_rankings/fan_intelligence.py` — fan-intel reads for Stage 1 stream 2
6. `src/cfb_rankings/cohorts/aggregate.py` — cohort + conversation velocity
7. `src/cfb_rankings/team_pages/season_arc_loader.py` — historical archive access for Stage 1 stream 3
8. `SESSION_LOG.md` — fan-intel commit baseline; check what's flowing

---

## Phase 1 — Build the six-stream candidate scanner

New module `src/cfb_rankings/team_pages/chronicle_streams.py` with one public function per stream. Each returns a list of `CandidateObservation` dataclasses:

```python
@dataclass
class CandidateObservation:
    suggested_type: str  # 'anomaly' | 'moment' | 'flashpoint' | 'echo' | 'retroactive' | 'player_arc'
    evidence: dict       # structured data supporting the card
    source_citation: str # fan-readable attribution (see brief §7)
    oddity_score: float  # 0-1, how unusual is this
    date_window: tuple   # (start_date, end_date) for the evidence
    stream: str          # which scanner found this
```

### 1.1 savant_stream(team_slug, week)

Reads from Savant card percentiles + gamelog. Emits anomaly candidates when:
- Any of 13 Savant metrics is ≥95th or ≤5th percentile this week
- Any 4+ game streak (W/L, cover/no-cover, over/under) exists
- Home/away splits diverge by >20% on any efficiency metric
- Situational split shows something the baseline hides (3rd-and-long, red-zone TD%, etc.)

Source citation format: `gamelog · <season_year> through wk <N>` or `Savant card · CFBD data`.

### 1.2 fanintel_stream(team_slug, week)

Reads from fan-intel pipeline. Emits moment candidates when:
- Cohort conversation velocity ≥ 2× the 4-week baseline
- A single Bluesky post crosses a re-share / like threshold
- A board thread title is being quoted back across venues (use title cosine similarity)
- Beat-writer headlines in the last 7d cluster around a specific theme

Source citation format: `OneFootDown · <relative_date>` / `BlueGrayGold thread · <relative_date>` / `from <N> beat-writer pieces this week` / `conversation velocity · Bluesky firehose`.

### 1.3 archive_stream(team_slug, week)

Reads from historical season archive (2014–now via `season_arc_loader`). Emits echo candidates by computing cosine similarity between:
- Current season's week-by-week shape features (W/L pattern, margin distribution, mood trajectory)
- Every prior CFP-era season for this program

For matches ≥0.75 similarity where the prior season has a defined "how it resolved" (in `team_historical_seasons` from sprint 4), emit an echo candidate.

Source citation format: `from the <year> season archive · <era_name> year <N>` where era_name is from profile.era_name_overrides.

### 1.4 rivalry_stream(team_slug, week)

Reads from rivalry archive + opponent profile. Emits flashpoint candidates when:
- An upcoming game (within 14 days) is vs. a profiled rival
- Both programs have an `opposing_posture` on each other in their profiles

Source citation format: `from the <trophy_name> archive · last meeting <year>` or `both sides · profile voice`.

### 1.5 retroactive_stream(team_slug, week)

Reads from `team_chronicle_observations` (historical Chronicle cards for this team this season). Emits retroactive candidates when:
- A prior-week card's framing has been overturned by later events (e.g., shipped a "this QB is the problem" card in week 4; team has won 6 straight since)

Source citation format: `earlier this season · wk <N> Chronicle · reframe`.

### 1.6 player_arc_stream(team_slug, week)

Reads from player stat trajectories + fan-intel name-velocity. Emits player-arc candidates when:
- A player's name-velocity in the last 14 days is ≥ 3× their 8-week baseline
- Their stat trajectory shows a >30% trend across 4+ consecutive games
- A historical program player has a comp pattern (search `historical_season.defining_moments` for player mentions)

Source citation format: `gamelog + roster archive` / `<player_name> trajectory via fan-intel name-velocity`.

### Self-verification for Phase 1

- Running the scanner for Notre Dame current week produces ~30 candidates across all 6 streams.
- No candidate cites "CFB Index" or "stat engine" as source — all citations are one of the approved formats.
- If any stream produces 0 candidates for current week, that is acceptable (a program may have no echo candidates if its current season is unprecedented) but log the stream and week.

---

## Phase 2 — Rewrite ranking + writing

Rewrite `chronicle_generator.py`:

### 2.1 rank_candidates(candidates, profile, max_cards=6) — Sonnet

Input: ~30 candidates. Output: top 4–6 with justification.

Sonnet prompt asks the model to rank candidates on the five criteria from the brief (surprise, voice-fit, evidence, recency × durability, diversity). Diversity constraint: max 2 of any one card type per week; aim for 3–4 different types.

### 2.2 write_card(candidate, profile, model) — Sonnet for standard; Opus for top-3 weekly card of blue-bloods

Load profile fields: `voice_register`, `identity_phrase`, `mantra`, `stock_phrases`, `mascot_voice`, `era_name_overrides`, `never_use`.

Prompt structure:

```
ROLE: You are writing a Chronicle card for <program display_name>. The Chronicle is an editorial observation feed; each card reads like what a sharp beat writer for this program would notice and post. NOT a stats engine describing itself.

PROGRAM VOICE (use these fields; do not paraphrase them):
- voice_register: <verbatim from profile>
- identity_phrase: <verbatim>
- mantra: <verbatim>
- stock_phrases: <list, verbatim>
- mascot_voice: <verbatim>
- era_name_overrides: <verbatim>

NEVER USE (reject outputs containing these):
- sample (as a stat word)
- stat engine / pipeline / our algorithm
- tier 1 / tier 2 (as program taxonomy)
- "the pattern is ..." (as sentence subject)
- summary stat / compression of outcome / flattening
- "Every season produces ..."
- "this table" / "this card" / "this module"
- methodology / the engine
- anything the profile's `never_use` field forbids

CANDIDATE:
- Card type: <suggested_type>
- Evidence: <structured evidence>
- Source citation: <source_citation from Phase 1>

STRUCTURAL CONSTRAINTS:
- Headline: must contain a specific noun beyond the program name (player, date, opponent, stadium, play)
- Body: 2–3 sentences, maximum 80 words
- Attribution field: use the source_citation verbatim
- At least one comparative marker ("since", "like", "only", "longest", "first time", "the last time"...)

SELF-CHECK BEFORE RETURNING:
Read your output back as if you were a sharp independent blogger for <program>. Would you post this? If no, rewrite. If yes, return.
```

Blue-bloods (Alabama, Ohio State, Georgia, Michigan, Texas, USC, Notre Dame): pick the top-1 ranked card per week and upgrade model to Opus. Standard cards stay Sonnet.

### 2.3 validate_card(card) — Haiku

Four checks (see brief §Stage 4):
1. Headline or body contains a proper noun beyond the program name — regex or NER check.
2. No banned phrase from the list above — substring check (case-insensitive).
3. Comparative marker present — regex for "since|like|only|longest|first time|last time|hasn't X since|the shortest|the first".
4. Attribution field matches one of the approved formats (regex patterns).

Failure routes back to write_card with `retry=True`. Second failure drops the card.

### Self-verification for Phase 2

- Generate one full week of Chronicle for Notre Dame. Validation dropout rate ≤ 20%.
- Human-readable test: paste the 4 cards into chat. Each should (a) name a real person / date / opponent, (b) carry ND voice (Leprechaun, Kelly/Freeman-era references, gold/blue palette in language), (c) make a comparison to program memory, (d) attribute to a real source.
- Repeat for Alabama. Voice should differ (crimson, dynasty-quiet, Saban-era references, tide/state cultural markers).
- Repeat for UMass. Voice should differ (scrappy-proud, just-found-itself register, basketball-school energy).

---

## Phase 3 — Re-generate for all 17 profiled programs

```
python manage.py generate-chronicle --team <slug> --model auto
```

`--model auto` routes blue-bloods' top-1 weekly card to Opus and everything else to Sonnet. Run for all 17 programs.

Report: dropout rate per program. Any program with >30% dropout needs its profile's voice fields reviewed (flag to Kevin, don't retry blindly).

Re-render pages:
```
python manage.py render-team-pages
```

---

## Phase 4 — Apply the same voice rules to spillover editorial copy

Same anti-scaffolding rules apply to these surfaces (see brief §spillover):

1. **Pulse takes fallback** — when conversation signal is below floor, pick from `profile.stock_phrases` with a deterministic rotation (hash on team_slug + week_number). Do NOT generate new copy here; the stock phrases already exist and are profile-voice-correct.
2. **Rivalry card per-meeting one-liners** — audit each profiled rivalry's `meetings` list; any one-liner that reads generic ("a close game" / "a high-scoring affair") must be regenerated using the Beat-Writer Test. Estimate ~50 one-liners across 17 programs × avg 3 Tier-1 rivalries × 10 meetings.
3. **Historical season `defining_moments` cards** — audit the 19 flagship seasons from sprint 4; run the validation gate. Some template-fallback seasons from sprint 4 may also fail; re-queue them for Opus graduation (sprint 5 is already doing this for prioritized seasons — coordinate to avoid double work).

---

## Decision authority

Autonomous on: exact candidate-stream heuristics, ranking criteria weights, prompt wording nuances, which specific source URLs to format, which seasons to re-audit for spillover (within the scopes above).

Stop and flag only if:
- Fan-intel data is empty for most teams (check SESSION_LOG first; if the cron hasn't caught up, run with whatever signal exists and flag which programs are below-floor)
- A profile's voice fields are so thin that Opus/Sonnet cannot produce on-voice output — report profile + suggested fields
- `team_chronicle_observations` schema doesn't support a new column you need (e.g., to store source_citation properly) — propose migration, stop
- >50% of generated cards fail validation — voice prompt isn't biting; stop and report

---

## Report back with

1. **Phase 1** — per-stream candidate counts for ND, Alabama, UMass current week. Sample 3 candidates from each stream and paste for review.
2. **Phase 2** — before/after: paste the 4 previous ND Chronicle cards and the 4 newly-generated ND Chronicle cards side by side. Kevin will do the Beat-Writer Test.
3. **Phase 3** — dropout rate per program. Any >30% flagged. Pick 3 programs with distinct voices (ND, Auburn, UMass) and paste one card from each back-to-back — tonal distinctness check.
4. **Phase 4** — spillover audit count + sample fixes.
5. Token usage by phase + model. Validate that blue-blood Opus cost is <15% of total.
6. Natural next — typically: deeper fan-intel ingestion (more adapters live) unlocks more moment candidates; OR profile voice-field sharpening for programs with high dropout.

Report at end, not between phases. Good luck.
