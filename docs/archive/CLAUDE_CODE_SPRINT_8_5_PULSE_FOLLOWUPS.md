# Claude Code — Sprint 8.5: Pulse Follow-Ups (Token-Disciplined)

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session on `master` branch (after Wave 1+2 integration fast-forwarded). Closes Sprint 8's deferred LLM work — focused on the highest-leverage entities; long-tail deferred to a follow-up sprint.

**Recommended Claude Code session model: Sonnet 4.6.** Sonnet has the editorial judgment for the marquee work; Opus is overkill and expensive. The Claude Code session itself runs on Sonnet 4.6, then routes sub-tasks via `llm_runtime` to Haiku for bulk operations and Opus only for the 5-7 highest-stakes Lede generations.

**Target budget: ~65k tokens. Runtime: 1.5–2.5 hours.**

**Branch:** create `sprint/8.5-pulse-followups` off `master`.

**File ownership:** `team_pages/pulse_*.py`, NEW `team_pages/sentiment_classifier.py`, NEW `team_pages/the_room_renderer.py`, `conferences_pulse/`, NEW `profiles/_conferences/*.md` (8 files), `migrations/20260425_85_*.sql` if needed.

**Files NOT to touch:** `editions/*`, `storylines/*`, `canon/*`, `wire/*`, `receipts/*`, `reporting.py` outside the documented one-line conference-pulse hook.

---

## Why this sprint, scope-reduced

Sprint 8 deferred 5 items. Doing all 5 across all 17 programs + 11 conferences + 5,000+ players = 120k+ tokens with diminishing returns past the top entities. Fans don't notice the difference between stock-phrase fallback on UMass and live themes on UMass — they DO notice the difference on Notre Dame, Alabama, the SEC.

**Scope reduction:**
- Live theme extraction + Lede on **top 10 programs + top 5 conferences** (highest-volume entities). Other 7 programs + 6 conferences keep stock-phrase fallback (already working).
- Sentiment classifier runs on **sample-validate-then-scale** approach — not full 1M-post backfill upfront.
- Conference voice profiles for the 8 missing leagues — **all Sonnet, no Opus**. Conference voice is not Lede-tier editorial.
- Player Pulse / The Room redesigned for **top 15 high-traffic players** (Heisman Watch + top NFL Draft prospects). Other 5,000+ render with floor-rule degradation (intentional design).
- Re-render **only entities that got new content** — skip the long-tail.

This delivers world-class quality on every surface fans will actually scrutinize while staying under 70k tokens.

---

## Top entities for full treatment

**Top 10 programs (by Wave 2 corpus volume):**
Alabama · Ohio State · Georgia · Michigan · Texas · USC · Notre Dame · Penn State · Tennessee · Auburn

**Top 5 conferences:**
SEC · Big Ten · ACC · Big 12 · AAC

**Top 15 players** (Heisman Watch contenders + top NFL Draft prospects from existing player corpus — query `players` table ordered by name-velocity in last 30 days):
Auto-pick from `players` joined with name-velocity from `source_observations`. Top 15.

---

## Phase 1 — Sentiment classifier (sample-validate-scale) (~12k tokens)

### 1.1 Migration

If `source_observations.sentiment_label` doesn't exist:

```sql
-- migrations/20260425_85_sentiment.sql
ALTER TABLE source_observations ADD COLUMN sentiment_label TEXT
    CHECK(sentiment_label IS NULL OR sentiment_label IN ('positive','neutral','negative'));
ALTER TABLE source_observations ADD COLUMN sentiment_classified_at DATETIME;
```

### 1.2 Haiku batch classifier

`team_pages/sentiment_classifier.py` — single-batch function calling `llm_runtime.generate_with_voice_check()` with `model='claude-haiku-4-5'`, batch size 50.

### 1.3 Sample run + validate

Classify a 5,000-observation sample (last 7 days × top 10 programs). Manual accuracy spot-check on 30 random results. If ≥3 misclassifications, document samples + tune prompt; re-run a 1k batch to verify.

### 1.4 Targeted backfill

After accuracy is solid, classify last 30 days × top 10 programs + top 5 conferences. Skip the long-tail (other 7 programs + 6 conferences). Approximate volume: 200k-500k observations × ~15 tokens per Haiku classification = 3-8k tokens.

A separate cron sprint handles ongoing classification + long-tail backfill — don't try to do it all here.

### 1.5 Wire into PulseState

`compute_sentiment_distribution(team_slug, week)` reads classified labels. Returns `None` when sample_size < 100 (graceful degradation; long-tail entities show no sentiment slice — that's correct behavior).

### Self-verification

- Migration applies
- 5k sample classified; manual accuracy spot-check passes
- Targeted backfill complete for top entities
- Sentiment slice renders for 5+ programs + 3+ conferences (high-volume entities cleared the floor)

---

## Phase 2 — Live theme extraction + Lede generation (top entities only) (~25k tokens)

Combined Phase covers themes + Lede for the 10 programs + 5 conferences (15 total). Keeps the prompt + LLM-routing logic in one place.

### 2.1 Theme extraction pipeline

`team_pages/pulse_themes.py`:

- **Haiku scan** of last 7 days of source_observations for the entity. TF-IDF cluster or Haiku topic-extraction prompt. Returns 5-10 candidates per entity.
- **Sonnet ranks + writes 3 themes** per entity. Picks verbatim representative_quote from candidate evidence_list. Validates fan voice. One retry on banned phrases.

Per-entity cost: ~1k tokens Haiku + ~1.5k tokens Sonnet = 2.5k. × 15 entities = ~38k.

Wait — this is too much for the budget. Reduce further:

- **Top 5 entities** (Alabama, OSU, Georgia, Notre Dame, SEC) get FULL theme treatment (3 themes each)
- **Other 10 entities** get **partial treatment**: Haiku scans + ranks; Sonnet writes ONLY the top theme (1 per entity, not 3)

That's: 5 × 2.5k + 10 × 1k = ~22k. Within budget.

### 2.2 Lede generation

`team_pages/pulse_lede.py`:

- **Top 3 blue-bloods** (Alabama, OSU, ND) — Opus Lede. ~1k tokens × 3 = 3k.
- **Other 7 programs + 5 conferences** — Sonnet Lede. ~0.7k × 12 = 8.5k.

Total Phase 2 Lede: ~11.5k.

Phase 2 grand total: ~33k. Trim: cut top 5 to top 4. Now: 4×2.5k + 11×1k + 11.5k = ~32k. Still tight; let's accept and stay vigilant during execution.

If actual usage runs ahead of budget, reduce to top 3 entities full theme treatment. Document the cut in the report.

### 2.3 Wire into PulseState

`build_pulse_state()` calls theme extraction + Lede generation. Stock-phrase fallback for entities outside the top-15 — they keep Sprint 8's deterministic Lede + stock-phrase themes, which already work and look fine.

### Self-verification

- 4 entities have 3 real themes each = 12 themes
- 11 entities have 1 real theme each = 11 themes
- 15 entities have live Lede (3 Opus + 12 Sonnet)
- 23 themes + 15 ledes pass voice validator
- Other 12 entities (7 programs + 6 conferences) explicitly fall through to stock-phrase fallback — verify the fallback path still works post-changes

---

## Phase 3 — 8 conference voice profiles, all Sonnet (~8k tokens)

Already shipped: SEC, Big Ten, MAC.

Author 8 missing profiles in Sonnet (NOT Opus — conference voice is structural, not editorial-tier):

ACC, Big 12, AAC, MWC, Sun Belt, C-USA, FBS Independents, Pac-12 (or successor)

Each profile per `profiles/_conferences/*.md` template — YAML frontmatter (voice_register, identity_phrase, mantra, accent_hex, stock_phrases) + 4 narrative sections (identity, voice, current context, current calendar moment). ~1k tokens per profile × 8 = 8k.

### Self-verification

- 11 total conference profiles exist
- Tonal distinctness check: paste 8 voice_registers back-to-back, confirm none read identical

---

## Phase 4 — Conference Pulse rendering on conference pages (~6k tokens)

### 4.1 Renderer

`conferences_pulse/renderer.py` — `render_conference_pulse_section(conference_slug)` returns HTML fragment matching Pulse v2 structure aggregated to conference level.

### 4.2 reporting.py hook

ONE-line delegation hook in `reporting.py` (per CLAUDE.md, this is a documented exception). The hook checks if the conference has Conference Pulse data; if yes, injects the HTML fragment into the conference page render.

### 4.3 Render all 11 conference pages

```
python manage.py render-conferences-pulse --all
```

Output: 11 conference pages with live Pulse module appended. Top 5 conferences (SEC/Big Ten/ACC/Big 12/AAC) show full content (themes + Lede + sentiment when sample warrants); other 6 show stock-phrase fallback (designed graceful degradation).

### Self-verification

- All 11 conference pages render without errors
- 5 high-volume conferences show full content; 6 mid-tier show fallback gracefully
- Visual check: 1 high-volume conference + 1 mid-tier shows correct rendering at both ends of the spectrum

---

## Phase 5 — Player Pulse / The Room v2 (top 15 only) (~10k tokens)

### 5.1 The Room v2 renderer

`team_pages/the_room_renderer.py` — Pulse v2 eight-component structure applied to player pages. Same code patterns as team Pulse, just at player aggregation.

### 5.2 Top 15 players: full treatment

Query `players` joined with `source_observations` for top 15 by 30-day name-velocity. For each: theme extraction + Lede via the same pipeline as Phase 2 (Sonnet for all 15, since these are individual players not entities deserving Opus).

15 × ~600 tokens = ~9k.

### 5.3 Other players: graceful floor-rule

For all other 5,000+ players, render with sample_size < 100 floor-rule kicked in. Sparse Pulse + stock-phrase fallback. They render correctly even with thin data — no LLM calls needed for them.

### 5.4 reporting.py hook

Similar pattern: one-line delegation hook to check if a player has Room v2 data; render accordingly.

### Self-verification

- Top 15 players have full Room v2 with non-stub themes + ledes
- A handful of mid-tier players render with floor-rule degradation
- No errors when rendering players with truly empty corpus

---

## Phase 6 — Selective re-render + sample sweep + commit (~4k tokens)

```
python manage.py render-team-pages --slug alabama,ohio-state,georgia,michigan,texas,usc,notre-dame,penn-state,tennessee,auburn
python manage.py render-conferences-pulse --all
python manage.py render-the-room --top 15
```

Voice validator sample sweep on the new content:
- 5 random themes (top entities) → expect 100% pass
- 5 random ledes (mix of Opus + Sonnet) → expect 100% pass
- 3 conference profiles → expect 100% pass
- 5 random Room v2 ledes → expect 100% pass
Total: 18-string sweep. Trivial token cost.

Commit + push to `sprint/8.5-pulse-followups`. Open PR to master.

---

## Token budget summary

| Phase | Estimate | Driver |
|---|---|---|
| 1 — Sentiment | 12k | Haiku batches on 5k sample + targeted backfill on top entities |
| 2 — Themes + Lede | 32k | Haiku scan, Sonnet write/rank, Opus on top-3 ledes only |
| 3 — Conf profiles | 8k | Sonnet on 8 profiles |
| 4 — Conf rendering | 6k | Code + 11 page renders (template, no per-page LLM) |
| 5 — Room v2 | 10k | Sonnet on top 15 players + code |
| 6 — Re-render + sweep | 4k | Code + small validator sweep |
| **Total** | **~72k** | Cap target 65k; allow up to 80k before flagging |

If running ahead of 80k mid-sprint: reduce Phase 2 from 4 entities to 3 entities for full theme treatment, Phase 5 from 15 players to 10. Document the cuts.

**Opus usage check:** Opus called only on top-3 program ledes = ~3k tokens. As fraction of total: ~4%. Well under 15% cap.

---

## Decision authority

Autonomous on: which 4 entities get full Phase 2 treatment vs partial (default: Alabama, OSU, Georgia, Notre Dame); top 15 player selection algorithm specifics; sentiment classifier sample size; budget reduction tactics if running ahead.

Stop and flag only on the four canonical hard-blocker conditions.

---

## Report back with

1. Sentiment classifier accuracy spot-check (30 samples)
2. Top entities chosen for full Phase 2 treatment + reasoning
3. 4 themes from Alabama + 4 from Notre Dame paste-back for Beat-Writer Test
4. 5 ledes (mix of Opus/Sonnet from Phase 2) paste-back for tonal distinctness
5. 8 conference voice profiles (just the voice_register lines) paste-back
6. 5 player ledes from top 15 paste-back
7. Voice validator sample sweep result
8. Token usage by model + total
9. Files touched
10. Final commit SHA pushed to remote

When committed + PR opened, session complete.
