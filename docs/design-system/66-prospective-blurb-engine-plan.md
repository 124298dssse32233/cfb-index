# 66 — Prospective Player-Blurb Engine — Implementation Plan

_Status: PLAN + PARTIALLY BUILT (updated 2026-06-13). Derived from the 2026-06-13 design session. Memory: `prospective-player-blurb-engine-2026-06-13`. Extends 41 (story-card), 42 (narrative-engine), 49 (pragmatic-v1-critique), 59 (evidence-packet-contract), 60 (player-page-master), 61 (player-noir-migration-plan)._

## Status & related docs (updated 2026-06-13)

**This doc is the NARRATIVE blurb plan.** The player is a **matched pair** — narrative + a **play-style ("how he plays") companion**. The play-style method (register ladder, the 9 world-class pillars, the qualitative-descriptor anti-hallucination law) and the per-position vocabulary live in **[[67-position-style-ontology]]**; the subject-agnostic methodology + the **cross-subject paradigm** (reuse for team / coach / game pages) is **[[68-blurb-method-cross-subject-paradigm]]**. Read 66→67→68 in order.

**As-built (Track A manual spike — done this session):** curated store at `data/curated_player_blurbs/*.json` (all 10 players: narrative hook+expand + grounded play-style + canonical slug). Render hook `src/cfb_rankings/player_pages/curated_blurb.py` (slug-matched first, then name; fail-closed) is preferred in the `reporting.py` story-card build (~L9369) when env `CURATED_BLURBS` is on (persisted via `setx`); **one edit covers BOTH renderers** (Noir reuses `new_story_card_html`). Deploy = full `scripts/build_publish.ps1` (no-clobber, renders every section) → `scripts/publish_to_vercel.ps1` (gated snapshot + alias). Go-points: G1 (top-10) ✅ · G2 (authored, owner-approved live-now) ✅ · G3 (render wire) ✅ · G4 (commit) PENDING (files staged, uncommitted) · G5 (deploy) IN PROGRESS.

**Verified data (this session):** all 10 canonical player_ids confirmed via PBP; WEPA/usage refreshed + PBP ingested/computed for 2025; the play-style half is grounded in **real PBP percentiles** for 9/10 (EDGE has no offensive PBP). The data *corrected* drafts (Carr throws deep; Leavitt's legs > arm; Manning's 9th-pctl success rate).

**Two data workstreams (do NOT block the spike — match by stable key in the meantime):**
- **(A) player_id LINKROT** — ~42,954 orphan `players` rows (~48%, no roster + no source-id) cause wrong-id lookups. Curated content matches by **stable slug/name**, not id, to sidestep it. Fix = a `cli` `audit-orphan-players` + canonical-id resolver + harden the team-blind PBP name matcher (`player_pbp_metrics.py`). The destructive merge needs owner sign-off.
- **(B) discourse-descriptor cleanup** — `player_discourse_terms` currently surfaces names/teams/transactional words, not style adjectives (offseason timing + no proper-noun/news filtering + thin coverage). Cleanup (filter + descriptor-type classify + coverage) unlocks the **fan-vs-rival descriptor layer** and fixes the live `in_their_words` module (currently rendering garbage chips).

## 0. What this is

Evolve the player **Story Card** (`new_story_card_html`, top of both legacy + Noir pages) into a forward-looking, web-grounded blurb that fits a player into the nested narratives of his career / team / team-legacy / CFB-at-large. Primarily PROSPECTIVE (previews the upcoming season+). Written at Sonnet-tier quality, source-agnostic, present-day-accurate, fungible across all players.

**Two tracks, run in parallel:**
- **Track A — Manual-in-chat spike (NOW):** Claude generates blurbs in-session for the ~10 most popular/interesting players, stores them as version-controlled JSON, renders + deploys behind an allowlist + kill-switch. Expand 10 → 100 → beyond. These double as the gold-standard reference set that de-risks Track B.
- **Track B — Automated pipeline (productionize):** the full normalize → detect → plan → write → gate → cache → deploy pipeline, replacing manual generation once proven, scaling to thousands.

## 1. Binding owner rulings (do not violate)

1. **Best product is the only objective.** Do NOT overweight proprietary data — it competes on merit (it tends to win a *different* beat: the fan-perception axis). Never privileged for being "ours."
2. **Spine, not sibling.** The blurb is the page's cold-open that sets up the modules below as its receipts (conceptual handoff, not hyperlinks).
3. **Hook visible → expand for full** (progressive disclosure). Casual reads the hook; diehard expands.
4. **Length follows STORY SIZE**, not data density and not raw interest. "The story is the story." Fame is *evidence* a story exists → find why. Don't pad a hollow story. Effort scales with interest (thin output on a high-interest player = search harder, not ship short).
5. **Anti-formula = fix function, free form.** Story-shapes are an open-ended **combinatorial grammar**, never a fixed enum/mold.
6. **Ethics gate keys on EVIDENTIARY STATUS, not topic.** Verified/official consequences (suspension, charge of public record, portal entry, announced injury) ARE reportable — often required for an accurate forward look — treated factually/proportionately. Rumors/allegations are suppressed regardless of volume. Implement via `source_trust.py` tiers.
7. **No NIL hero number** (per `nil-valuation-not-a-hero-number`). NIL story from discourse is allowed; "worth $X" as a hero/BAN claim is not.
8. **Preserve modules / parallel + kill-switch** (per `preserve-modules-no-delete-without-signoff`). New writer is a parallel path; legacy/local stays the default fallback.

## 2. The pipeline (conceptual — validated this session on CJ Carr + Dylan Raiola)

```
assemble_evidence (+ vetted, dated, provenance-tagged web facts)
   → normalize        (cohort × altitude(local+national) × trend × confidence)
   → detect           (per-element liveness vector {present,live,forward,strength,
                        durability,confidence}; calendar-phase-gated)
   → plan             (merit-blind angle-selection: spine·blend·payoff·forward-stake·
                        register·horizon·length-band·drop-list·evidence-bindings)
   → write            (Sonnet, TO the plan; hook + expand; length = ceiling not target)
   → gate             (HARD: attribution · ethics(evidentiary) · grounding/factscore ·
                        freshness/staleness.  SOFT: padding · contract-floor ·
                        plan-conformance · lead-diversity.  Conflict → RE-TIER.  Floor → LKG)
   → cache + regenerate on signal-events
```

### 2.1 The sizing dial — divergence-and-durability story score
`story_score` inputs: production, attention, and especially their MISMATCH (overlooked = prod≫attn; overrated = attn≫prod), scaled by DURABILITY (sustained vs spike), amplified by situation/stakes, framed by CALENDAR PHASE, capped by the ethics gate. Length bands are CEILINGS (padding gate enforces): tentpole ~220-260w · feature ~110-160w · standard ~50-90w · minimal ~25-45w. Hook ~25-40w fixed.

### 2.2 The planner scoring (operationalizes best-product-not-moat)
`reader_value = (live × forward × strength × durability × confidence) + surprise_bonus − staleness_penalty`. **Source is not a term.** Proprietary wins via `surprise_bonus` when genuinely surprising; loses to a better web story otherwise.

### 2.3 Bedrock layers (build these first — see §5 build order)
- **Cohort-normalization:** cohort = position × role-tier × program-tier × (maybe class) × time-window; DUAL-FRAMED local+national (frame-gap is a story); delta-vs-own-baseline (trend beats level); de-seasonalized; robust/rank-based + log-transform power-law attention; same-scale prod & attention so divergence is computable; thin cohort → hierarchical backoff + shrinkage + lower confidence (never break — **confidence == the restraint dial**).
- **Calendar-phase model:** `date → {phase, live element-families(weighted), register, horizon, expected-attention baseline}`. Shares one calendar service with de-seasonalization. June 13 2026 = deep offseason/projection. Gates whole element FAMILIES on/off; sets prose register + forward horizon; sets regeneration cadence (faster in Aug camp / Dec portal).

### 2.4 Calendar register tokens
`projection · imminent · reporting · stakes-peak · transition · reset` — passed to the writer to condition tense/voice/horizon. The existing season-clock handles the YEAR (2026 vs 2025); this handles within-year voice.

### 2.5 Eligibility hard-gate (non-negotiable — added 2026-06-13 after a real miss)
A forward/returning-season blurb may only be generated for a player whose status is **Active** for the upcoming season. Respect the existing `eligibility.py` gate (Active / Departed / Uncertain): a **Departed** player (drafted, graduated, transferred out) NEVER gets a returning-season forward blurb — give a retrospective "where he is now" or omit. Manual track: verify each player's current status via live research as of the processing day before authoring (training-data knowledge is stale on the April draft + spring portal). This is the failure mode the whole engine exists to prevent (e.g. Carson Beck = drafted April 2026, an NFL rookie in June 2026 — not a CFB player).

## 3. Track A — Manual-in-chat generation & deploy system (IMMEDIATE)

### 3.1 Authoring store (source of truth)
`data/curated_player_blurbs/<slug>.json`, one file per player. Version-controlled, human-readable, renderer-agnostic. Schema in `data/curated_player_blurbs/README.md`. Claude (Opus 4.8 in-chat, applying the §2 framework + live web research as of processing day) authors these; each carries an `as_of_date`, a `plan` block, `sources`, and a `status` (draft|approved|live).

### 3.2 Render precedence (manual track — avoids DB hand-editing)
At build time, the player-page renderer (legacy `reporting.py` + `player_pages_noir`) resolves the story-card slot with precedence **curated > pipeline(Track B) > legacy**, scoped to an allowlist (mirror the Noir spike: an env var `CURATED_BLURB_SLUGS` or read the directory). Kill-switch: env off → curated layer skipped entirely. This keeps the rule "don't hand-edit the DB" — the JSON is the source, read at render.
- A small `manage.py validate-curated-blurbs` lint (schema, length-band conformance, sources present, as-of freshness, slug resolves to a real player) runs in CI before deploy.

### 3.3 Deploy path (full snapshot — respects the clobber rule)
1. Author/commit the JSON files (branch; see §3.4 go-points).
2. `python manage.py build-site` (or the curated-render entry) — renders the allowlisted player pages from the curated source.
3. `scripts/build_publish.ps1` → renders EVERY section (full snapshot — partial renders clobber prod) → `scripts/publish_to_vercel.ps1` deploys + sets the short alias.
4. Verify the per-deploy URL FIRST (alias-rotation gotcha), then the short alias.

### 3.4 Go-points (require explicit owner OK — outward-facing)
- **G1 — lock the top-10 list** (owner editorial call).
- **G2 — author + owner-approve each blurb** (`status: draft → approved`).
- **G3 — wire render precedence + lint** (code change in reporting.py / player_pages_noir / cli.py).
- **G4 — commit** (branch vs master per owner; CLAUDE.md says work lands on master).
- **G5 — build + deploy** to the live site (Claude will not deploy without an explicit "go").

### 3.5 Seeded already
`carr.json` (status: approved — owner said "looks great") and `raiola.json` (status: draft) are written and in the store as the first two records + the working schema example.

## 4. Track B — Automated pipeline (productionize)

Additive evolution of the existing Story-Card pipeline (`story_card.py` det → `story_card_narrator.py` LLM → eval → `player_story_card_cache`), NOT greenfield. Add:
1. **Web-grounding source** in `assemble_evidence()` (bounded retrieval pass — time-scoped queries, recency discipline, dated `[web]` provenance tags) — NOT a live tool in the writer.
2. **Angle-selection / planner** (widen the narrow archetype/BAN selection into the §2.2 merit-blind planner; two-step planner→writer for marquee, one-step for long tail).
3. **Sonnet 4.6 writer** behind a model-routing dial keyed to `story_score` — parallel to `story_card_narrator.py`, kill-switch + slug allowlist (Noir pattern). Wire to existing `data/sonnet_writer_budget.json`.
4. **story_score → rung → {writer, web on/off, length band}** router.
5. **Gates:** reuse factscore/attribution/banlist/do-not-amplify; ADD freshness/staleness + padding; compose HARD vs SOFT with re-tier conflict resolution + LKG floor.
6. **Freshness:** wire `player_signal_events` (currently empty) as regeneration triggers + an as-of stamp.
Same slot (`new_story_card_html`), same season clock, same cache table.

## 5. Build order (gap-map → phases)

1. **Phase 0 — reconcile** with existing specs 41/42/49/59/60/61; confirm the evidence-packet contract (59) covers the new web/normalized signals.
2. **Phase 1 — cohort-normalization layer** (uniform service; today it's piecemeal). Bedrock.
3. **Phase 2 — calendar-phase model** (one service, also feeds de-seasonalization).
4. **Phase 3 — element-detector bank** (liveness vectors; seeded, extensible).
5. **Phase 4 — web-liveness fusion** (the bounded retrieval pass + provenance/recency).
6. **Phase 5 — schedule/collision (relational) detector.**
7. **Phase 6 — planner + Sonnet writer + gate stack** (the §2 brain + output).
8. **Phase 7 — `player_signal_events` wiring** (regeneration / living artifact).
Empty tables to fill: `player_signal_events`, `player_draft_projection`. Ready-now data: depth chart, class, recruiting, succession, production pctls, trajectory, discourse vol/sentiment/vocab, aura gap, Heisman odds.

## 6. Cost & rollout staging

`claude-sonnet-4-6` = $3 / $15 per MTok. Per-player: data-only ~$0.008; +web search ~$0.05 (web is the cost+latency+hallucination driver → tier web to marquee). Batches API −50% (confirm web-tool support on Batches; confirm exact web-search per-search rate before scaling).

| Stage | N players | Web? | Writer | Track | Est. cost/run |
|---|---|---|---|---|---|
| Spike | ~10 | yes (all) | Opus-in-chat → Sonnet | A (manual) | < $1 (negligible) |
| Wave 1 | ~100 | marquee only | Sonnet + planner | A→B | ~$3–6 |
| Wave 2 | ~1,000 | top story_score only | Sonnet/local split | B | ~$20–60 |
| Full | thousands | tiered by story_score | tiered (Sonnet marquee, local/template tail) | B | tens of $ / weekly |

Rollout mirrors the Noir spike: allowlist → widen by `story_score`, kill-switch throughout, LKG floor so a bad run never reaches fans.

## 7. Open decisions (owner)

- **D1:** the top-10 list (proposed in chat; Carr ✅ + Raiola ✅ done).
- **D2:** render precedence via directory-scan vs an explicit `CURATED_BLURB_SLUGS` env allowlist (recommend env, matching Noir).
- **D3:** commit target — feature branch vs straight to master (repo convention = master).
- **D4:** when to flip from Opus-in-chat authoring (Track A) to the automated Sonnet planner+writer (Track B) — recommend after Wave 1 (~100) proves quality.
