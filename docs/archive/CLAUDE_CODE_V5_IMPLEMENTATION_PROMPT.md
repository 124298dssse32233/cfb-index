# Claude Code — Fan Intelligence Hub V5 Implementation Brief

> Paste this entire file into Claude Code as the opening message.
> Read `CLAUDE.md` and `FAN_INTEL_HUB_V4_A_PLUS_REVIEW.md` before touching code. `CLAUDE_CODE_FIX_PROMPT.md` is the prior surgical-fix brief — P0-P2 items from that brief that overlap with this work (P1.4 `Awaiting Signal`, P1.3 `model_version`, P1.2 internal labels, P1.5 conference depth) are folded into the phase plan below. Don't duplicate work.

---

## 0) Mission

Implement **Version 5 of the Fan Intelligence Hub** in the live Python generator (`src/cfb_rankings/reporting.py` + `src/cfb_rankings/fan_intelligence.py`). Your job is to turn the Figma v5.1 design (shipped; details below) into rendered HTML at `output/site/hub/index.html` (or the existing hub route — verify first), and to push the archetype + mood classification down to every team page so the fan-intel layer stops rendering "Awaiting Signal."

Do NOT redesign any flagship chart from v4 — polish, don't rebuild. Do NOT expand scope beyond the eight sections specified. Do NOT hand-edit `cfb_rankings.db`.

The deliverable is a weekly-publishable Fan Intelligence Hub issue with (a) the three new flagship modules, (b) the 18-primary + 8-modifier taxonomy shipping both on the hub page and on team pages, (c) every chart polish fix from the A+ review, and (d) the hub-page "Awaiting Signal" dead-end replaced with real offseason content.

### Canonical design reference — Figma v5.1 (shipped)

The design source of truth is the Figma export at **`Fan Intelligence Hub Design (3).zip`** in the repo root. Unzip it to a scratch directory before reading. It is a React + TypeScript + Tailwind codebase; you are **not** porting the React code — you are reading it as a spec for HTML structure, copy, and CSS tokens, then rendering through the existing Python generator.

All previously-open design questions are closed in v5.1:

- **18 primary archetypes** are fully specced in `src/app/components/publication/FanbaseArchetypesTaxonomy.tsx` — each card has `name`, `description`, `teams[]` with match %, `signature_phrase`, 6-week `migration[]` sparkline array, and optional `migrationNote`.
- **8 modifiers** (Emerging, Entrenched, Upstart, Fading, Rebuilding, Reloading, In Crisis, Ascendant) are in a dedicated strip at the bottom of that same file, each with the amber `#E0A300` dot.
- **Typographer quotes** are live throughout via `dangerouslySetInnerHTML` with `&rsquo;` entities (see `RivalryMatrix.tsx` and the taxonomy file for the pattern). Mirror this in Python by emitting the HTML entities directly.
- **Section order** is authoritative in `src/app/App.tsx` — do NOT read `src/app/AppV5.tsx`, it is dead code and should be ignored (the Vite entry at `src/main.tsx` imports `App.tsx`, not `AppV5.tsx`).
- **Typography spine, palette, section-number ritual, methodology row, team-chip component** are all expressed in the publication components — read them once at the start of Phase 2 and treat them as the design tokens.

Because the Figma spec is this concrete, **you should not need Opus to design anything that already exists in the Figma** — the schema, the copy voice, the card shape, and the layout are decided. Opus is reserved for the three decisions in §0.5 that the Figma cannot answer (classifier weights, migration-history shape, lexicon phrase-mining heuristic).

`FIGMA_MAKE_V5_PROMPT.md` remains useful as a prose narrative of the design intent, but the Figma export is authoritative when they conflict.

---

## 0.5) Model & token economy — READ THIS FIRST

Goal: ship a world-class v5 build while keeping the total session cost rational. The rules below are not suggestions — they are the budget.

**Core discipline:**

- Default **Sonnet**. Escalate to **Opus** only for the three decisions listed below. Push mechanical work to **Haiku subagents**, aggressively.
- **Do not read the whole of `reporting.py`.** It's 17.5k lines. Use `Read` with `offset` and `limit` anchored to the line numbers in §2. If you need context around a fix, read ±80 lines, not the whole section.
- **Do not read the generated `output/site/**/*.html`** to verify — they're 5MB+. Use targeted `Grep`.
- **Do not read the Figma React codebase more than once per phase.** Phase 2 opens the publication components; Phase 3/4 can re-grep for specific tokens but should not re-open the files.
- Prefer `Grep` over `Read`. Prefer `Edit` over `Write`.
- `/compact` after Phase 2, Phase 4, and Phase 6. `CLAUDE.md` is your persistent memory; the live context isn't.
- Every Haiku subagent call should be a **bundled** bash or grep — never spawn a subagent for a single one-line check.

### Per-phase token budget caps (hard)

If a phase crosses its cap, stop and `/compact` before continuing. Overrun is a signal you're reading too much or letting Opus run too long.

| Phase | Cap | Primary model |
|---|---|---|
| Orientation (§2 grep map + skim briefs) | 8k | Sonnet |
| Phase 1 — schema + migrations + ingest CLIs | 12k | Opus (one plan) → Sonnet |
| Phase 2 — hub-page IA + shared partials + copy dict | 18k | Sonnet |
| Phase 3 — archetype classifier + hub grid + team module | 22k | Opus (weights only) → Sonnet |
| Phase 4 — Mood Ticker + Rivalry Matrix + Lexicon Feature | 18k | Sonnet (Opus one-shot for phrase-mining rule) |
| Phase 5 — chart polish | 10k | Sonnet |
| Phase 6 — voice consistency + renames + quotes sweep | 6k | Haiku subagent |
| Phase 7 — team-page fan-intel resurrection | 5k | Sonnet |
| Verification + final summary | 4k | Haiku subagent → Sonnet |
| **Total target** | **≤110k** | |

### Routing table (this brief) — sharpened

Three columns, no ambiguity: the model, the trigger, and a token ceiling for that unit of work. If the unit crosses its ceiling, stop and re-plan.

| Unit of work | Model | When to use | Ceiling |
|---|---|---|---|
| Orientation pass (this brief + CLAUDE.md + §2 grep map) | Sonnet | Start of session | 8k |
| First-move grep map (§2) | **Haiku subagent** | Right after orientation; one bash call, bundled | 1k |
| Phase 1 schema design (data-model shape + migration pattern decision) | **Opus** | Once, in plan mode, then drop back | 6k |
| Phase 1 migration SQL + CLI subcommands + seed data + classifier stubs | Sonnet | After Opus plan | 8k |
| Phase 1 seed verification (sqlite counts) | **Haiku subagent** | Bundled SQL counts | 0.5k |
| Phase 2 hub-page IA (section order, partial list, copy-dict shape) | Sonnet | Read directly from `App.tsx` in Figma export — the IA is already decided | 4k |
| Phase 2 section renderers + shared partials + copy dict | Sonnet | Most of Phase 2 | 14k |
| Phase 3 classifier weights (tone vs phrase vs record vs recency) | **Opus** | One prompt, one reply, drop back. Do NOT let Opus write the classifier code | 4k |
| Phase 3 classifier implementation (rules engine) | Sonnet | After Opus weights | 10k |
| Phase 3 hub taxonomy grid + team-page archetype module | Sonnet | Template work; copy comes from Figma `FanbaseArchetypesTaxonomy.tsx` | 8k |
| Phase 4 Mood Ticker + Rivalry Matrix renderers | Sonnet | Copy comes from Figma `MoodTicker.tsx` and `RivalryMatrix.tsx` | 8k |
| Phase 4 Lexicon phrase-mining heuristic design | **Opus** | One prompt, one reply. Criterion + weights, no code | 3k |
| Phase 4 Lexicon renderer implementation | Sonnet | After Opus heuristic | 7k |
| Phase 5 chart polish (Michigan blue, two-reds, semantic deltas, tabular-nums, Moore presser annotation) | Sonnet | Targeted `Edit` calls against located line numbers | 10k |
| Phase 6 — `73 conferences` fix, internal label renames, typographer quotes sweep, methodology row consistency | **Haiku subagent** | One bundled bash + grep + sed + verification in a single subagent turn | 6k |
| Phase 7 `Awaiting Signal` replacement | Sonnet | Falls out of Phase 3; two `Edit` calls | 5k |
| Full verification (§4 bash block) | **Haiku subagent** | One bash call at the end | 2k |
| `design:design-critique` + `design:accessibility-review` | Skill invocations | End only, not during | 2k |
| Final summary (§5) | Sonnet | Short + structured | 2k |

### When to escalate to Opus (this brief)

Only **three** decisions earn Opus, and each is capped at one prompt / one reply:

1. **Phase 1 — data-model shape.** The 18-primary + 8-modifier + weekly cadence + 6-week migration history crossing four tables. Ask Opus for the schema + migration pattern, nothing else. ≤6k tokens.
2. **Phase 3 — classifier weight vector.** What fraction of archetype confidence comes from tone vs phrase frequency vs record vs recency vs program identity. Ask Opus for the weight vector + tie-breakers, not the code. ≤4k tokens.
3. **Phase 4 — Lexicon phrase-mining heuristic.** The selection rule for the `featured=true` phrase (spike threshold + novelty score + sample-quote floor). Ask Opus for the criterion, not the code. ≤3k tokens.

Everything else — including editorial voice, hub-page IA, copy polishing, schema implementation, classifier code, chart polish, renderer work — is **Sonnet**. The Figma v5.1 export already encodes the editorial voice and IA, so do not spend Opus on copy judgment calls that the design already resolved.

### What Haiku does (aggressively)

Haiku subagents take every unit of work that is mechanical, bounded, and verifiable. In this brief that is:

- The first-move grep map in §2 (one bundled bash call).
- All `wc -l`, `grep -c`, `sqlite3 COUNT(*)` verification — bundled.
- The §6 voice sweep: `73 conferences` → `10 FBS conferences`, internal label renames (`Stress Point` → `Pressure Point`, `Reminiscence` → `Comp`, drop `Player Card Blueprint`), `model_version` → `CFB Index v1` in visible copy, and the typographer-quote sweep over rendered-text string literals. All in one subagent turn that diffs its own changes before committing.
- The §4 final verification block.
- Any post-Phase rename sweep (e.g., if a CSS class or partial name changes mid-build).

Rule: if a task is purely "find X and replace with Y" or "count Z", it belongs in Haiku. Sonnet never runs a `grep -c` in this build.

---

## 1) Ground rules

- **Never edit files under `output/site/**`.** Generated. Change the Python generator and rebuild.
- **Build command:** `python -u manage.py build-site` between fixes (fast, template-only). `./publish_site.ps1` once at the end (full publish, includes data refresh).
- **Data changes via CLI subcommand in `cli.py`.** Idempotent. No hand-edits of `cfb_rankings.db`.
- **Visible body content is Python-rendered before write.** Never use JS `${…}` template literals in anything that must render statically. Keep JS inside `<script>` blocks only.
- **Tool discipline:** `Grep` > `Read`. `Edit` > `Write`. Never `Read` a file whose line count you don't know — `wc -l` via `Bash` first.
- **Don't fight the v4 structure.** The 8 archetype cards, the Mood Index chart, Hype vs Reality matrix, Index Cards, and the commiseration block already render in v4 (or their v2/v3 precursors are in `fan_intelligence.py`). Upgrade in place — don't rewrite.
- **The Figma v5.1 export (`Fan Intelligence Hub Design (3).zip`) is source of truth for visual spec, copy, and section IA.** If there is a conflict between this brief and the Figma, the Figma wins for visuals and copy; this brief wins for code structure, data model, and build sequencing. `FIGMA_MAKE_V5_PROMPT.md` is a narrative description of the design intent and is superseded by the Figma export wherever they disagree.
- **Ignore `src/app/AppV5.tsx` in the Figma export.** It is dead code. `src/main.tsx` imports `src/app/App.tsx`, and that is the authoritative section order.

---

## 2) Codebase orientation

Same as `CLAUDE.md` + `CLAUDE_CODE_FIX_PROMPT.md §2`. Key paths and line numbers relevant to this brief:

```
src/cfb_rankings/
  reporting.py          ← HTML monolith. Hub page renderer lives here — grep for "fan_intelligence_hub" or "Fan Intelligence Hub" to find the entrypoint.
  fan_intelligence.py   ← Mood Card, Respect Gap, Rival Heat, Cohesion, Swing Meter. Default dict at lines 833-838.
  config.py             ← model_version string at line 43.
  cli.py                ← manage.py subcommands.
  ingest/
    honors.py           ← Heisman winner flag source.
    (add) archetypes.py ← NEW: archetype classifier (Phase 3).
    (add) lexicon.py    ← NEW: weekly phrase mining (Phase 4).
    (add) rivalry.py    ← NEW: rivalry obsession ratios (Phase 4).
  pipeline.py, operations.py, audit.py, integrity.py
manage.py               ← entrypoint
publish_site.ps1        ← python manage.py build-published
refresh_site.ps1        ← incremental sync
output/site/hub/        ← Fan Intelligence Hub page(s)
output/site/teams/      ← 667 team pages (archetype module lands here)

Fan Intelligence Hub Design (3).zip  ← Figma v5.1 export; unzip to /tmp or a scratch dir
  src/app/App.tsx                               ← authoritative section order (IGNORE AppV5.tsx)
  src/app/components/publication/               ← 13 components = design spec
    Masthead.tsx            ← top strip
    Navigation.tsx          ← primary nav with chevrons + Subscribe
    CoverHero.tsx           ← asymmetric hero
    EditorNote.tsx          ← drop-cap note
    MoodIndexFlagship.tsx   ← N° 01
    MoodTicker.tsx          ← N° 02
    HypeVsRealityMatrix.tsx ← N° 03
    FanbaseArchetypesTaxonomy.tsx ← N° 04 (18 archetypes + 8 modifiers — authoritative copy)
    RivalryMatrix.tsx       ← N° 05
    LexiconWeek.tsx         ← N° 06
    IndexCards.tsx          ← N° 07
    CommiserationBlock.tsx  ← N° 08
    TeamChip.tsx, TeamColors.ts ← shared primitives
```

### Known line numbers (from CLAUDE.md, verified)

| Concern | File | Line(s) |
|---|---|---|
| `fetch_site_pulse` / counter bug | `reporting.py` | ~4087; 4123-4124 |
| "72 NCAA-eligible team records" user-facing copy | `reporting.py` | 5784, 10769 |
| Heisman winner render | `reporting.py` | 3935-3957 |
| Primary nav tuples | `reporting.py` | 11717-11723 |
| Fan intel fallback "Awaiting Signal" | `reporting.py` | ~14830 |
| Internal labels (Stress Point / Reminiscence / Blueprint) | `reporting.py` | 13116, 13465, 13483, 9821 |
| Mood Card default dict | `fan_intelligence.py` | 833-838 |
| `model_version` source | `config.py` | 43 |

### First-move grep map (run all in one Bash call)

Before writing a plan, have a Haiku subagent run these and report back:

```bash
cd "<repo root>"
echo "== hub page entrypoint ==" ; grep -n "Fan Intelligence Hub\|fan_intelligence_hub\|build_fan_intel" src/cfb_rankings/reporting.py | head -20
echo "== archetype code paths ==" ; grep -n "archetype\|Anxious Dynasty\|Perpetual Believer" src/cfb_rankings/fan_intelligence.py src/cfb_rankings/reporting.py | head -20
echo "== mood index chart ==" ; grep -n "Mood Index\|MoodIndex\|mood_index" src/cfb_rankings/reporting.py | head -10
echo "== hype vs reality ==" ; grep -n "Hype\|HYPE\|reality" src/cfb_rankings/reporting.py | head -10
echo "== rivalry logic ==" ; grep -n "rival\|Rival" src/cfb_rankings/fan_intelligence.py src/cfb_rankings/reporting.py | head -20
echo "== hub output path ==" ; ls -la output/site/hub 2>/dev/null ; grep -n "/hub/\|hub/index" src/cfb_rankings/reporting.py | head -5
echo "== team-page fan-intel render ==" ; grep -n "Awaiting Signal" src/cfb_rankings/reporting.py
echo "== db schema source ==" ; find src/cfb_rankings -name "*.sql" -o -name "schema*.py" | head -10
```

This map tells you which function owns each current section and whether we're augmenting existing code or adding new renderers.

---

## 3) Phase plan (execute in order)

### Phase 1 — Data model  **[Opus to design; Sonnet to implement]**

Four new database concerns. Use Opus **once**, in plan mode, to design all four together. Then Sonnet implements.

**1.1 — `archetype_taxonomy` (reference data)**
Seed table with the 18 primary archetypes and 8 modifiers from `FIGMA_MAKE_V5_PROMPT.md §N° 04`. Columns per archetype: `id`, `slug`, `name`, `description`, `signature_phrase`, `half_life_seasons` (long/medium/short/cyclical/indefinite), `display_order`. Columns per modifier: `id`, `slug`, `name`, `description`.

Ship as a seed script invoked by a new CLI: `python manage.py seed-archetypes`. Idempotent.

**1.2 — `fanbase_classification` (per-team, current-season)**
Columns: `team_id`, `season`, `primary_archetype_id`, `primary_confidence` (0.0-1.0), `modifier_ids` (JSON array of up to 3), `classified_at` (timestamp), `classifier_version`. Unique key on `(team_id, season)`.

Also ship `fanbase_classification_history` with the same columns minus `classified_at` + plus `week_of_classification` — this is what the 5-season migration sparkline reads from.

**1.3 — `fanbase_mood_weekly`**
Columns: `team_id`, `week_start_date`, `mood_score` (0-100 int), `delta_from_prev_week` (signed int), `top_cause_token` (short string, e.g., `moore_presser`, `portal_win`, `spring_game`), `sample_size` (int), `ingested_at`.

The Mood Index flagship chart reads from this. The Mood Ticker reads top 10 biggest `delta_from_prev_week` values.

**1.4 — `rivalry_obsession_weekly`**
Columns: `team_a_id`, `team_b_id`, `week_start_date`, `a_mentions_b_count`, `b_mentions_a_count`, `ratio_a_over_b` (float). Unique on `(team_a_id, team_b_id, week_start_date)` with canonical ordering (`team_a_id < team_b_id`).

**1.5 — `lexicon_weekly`**
Columns: `phrase`, `week_start_date`, `mention_count`, `spike_pct_wow` (percent change week-over-week), `origin_community` (e.g., `r/OhioStateFootball`), `related_team_id` (nullable), `sample_quotes` (JSON array of {text, source, date} up to 5), `featured` (bool — the one we elevate into the Lexicon of the Week feature).

**Schema migration rule:** one file, `src/cfb_rankings/migrations/0005_fan_intel_v5.sql` (or whatever the migration pattern is in this repo — grep for existing migrations first). Wire it through `cli.py` as `python manage.py migrate`.

**CLI subcommands to add** (in `cli.py`):
- `seed-archetypes` — populates `archetype_taxonomy` from a hardcoded seed.
- `classify-fanbases --season 2025` — runs the classifier and writes `fanbase_classification`.
- `compute-mood-week --week YYYY-MM-DD` — computes per-team mood from conversation ingest.
- `compute-rivalry-ratios --week YYYY-MM-DD` — computes the 12 flagship rivalries.
- `mine-lexicon --week YYYY-MM-DD` — extracts phrase spikes and picks a `featured=true` phrase.

All CLIs are **idempotent**. Running twice with the same args should produce identical rows.

**Acceptance:**
- `python manage.py migrate` succeeds on a fresh clone.
- `python manage.py seed-archetypes` writes 18 primary rows and 8 modifier rows.
- `python manage.py classify-fanbases --season 2025` writes 133 rows to `fanbase_classification` (one per FBS team) and 133 × 5 = 665 rows to `fanbase_classification_history` (5 seasons back).
- `python manage.py compute-mood-week --week 2026-04-15` and `--week 2026-04-22` both succeed and produce reasonable deltas between the two.

### Phase 2 — Hub page structure  **[Sonnet — IA already decided by Figma v5.1]**

The section order, component vocabulary, and page skeleton are decided in the Figma export (`src/app/App.tsx`). Do not re-derive them. Open `App.tsx`, mirror the section order in Python, and move on. No Opus pass here.

Find the current hub-page entrypoint in `reporting.py` (from the grep map in §2). Refactor it into a set of section renderers that emit HTML fragments, assembled by a top-level `build_fan_intelligence_hub()` function.

Section list (contiguous numbering, matches Figma prompt):
1. Masthead strip
2. Primary nav (shared partial — may already exist)
3. Cover hero (asymmetric 60/40: headline + chart)
4. Byline + pull quote
5. Editor's Note (with drop cap)
6. `N° 01` — The Fanbase Mood Index
7. `N° 02` — The Ticker (new)
8. `N° 03` — Hype vs Reality
9. `N° 04` — The Taxonomy (upgraded to 18)
10. `N° 05` — The Rivalry Obsession Matrix (new)
11. `N° 06` — The Lexicon of the Week (new)
12. `N° 07` — This Week's Cards (renumbered from N° 09)
13. `N° 08` — Commiseration block
14. Footer

**Shared partials** (centralize — these render in multiple places):
- `render_masthead_strip(issue_num, model_week, updated_at)` — top dark bar.
- `render_byline(model_version, edited_by, date)` — used on cover and repeatable for other weekly features.
- `render_methodology_row(n, scope, freshness, link=True)` — canonical format for every chart's metadata line. Every chart in this issue uses this exact partial. Kills the format inconsistency the A+ review flagged.
- `render_team_chip(team_id, size="sm"|"md"|"lg", show_score=None, show_delta=None)` — the universal team-chip component with helmet circle + abbrev.
- `render_section_eyebrow(section_num, section_name)` — the `N° 0X · SECTION NAME` mono-caps row.
- `render_editorial_caption(text)` — serif italic chart caption.

**Copy content lives in a Python `HUB_ISSUE_047 = {...}` dict** at the top of the hub renderer file — not inline in the rendering function. This makes next week's issue a dict swap, not a code change. Include: cover headline, dek, editor's note body, pull quote, each chart's italic caption, Index Card headlines + bodies + signoff lines, commiseration letter body.

**Section eyebrow numbering is deep-linkable.** Every `N° 0X` anchor has an `id` attribute so `#sec-01`, `#sec-02`, etc. work as URL fragments.

**Acceptance:**
- `python -u manage.py build-site` emits `output/site/hub/index.html` with exactly 8 `N°` section anchors contiguously numbered `01` through `08`.
- `grep -c 'id="sec-0' output/site/hub/index.html` returns 8.
- Every chart-bearing section contains exactly one `<div class="methodology">` (or equivalent CSS class) — no custom inline metadata rows.

### Phase 3 — Archetype taxonomy upgrade on the hub page + team pages  **[Opus one-shot for classifier weights; Sonnet implements]**

**3.1 Classifier** (`src/cfb_rankings/ingest/archetypes.py`, new file)

Before writing code, use Opus **once** (≤4k tokens, single prompt) to decide the weight vector: what fraction of archetype confidence comes from tone vs phrase frequency vs record trajectory vs recency vs program identity, plus the tie-breaker order. Do not let Opus write the rules engine — Sonnet writes the engine against Opus's weight table.

Input: a team's fan conversations over the last N weeks + their current record + their program history signature. Output: a row in `fanbase_classification`.

Ship the v1 classifier as a rules engine (not ML). Rules priority order:
1. Structural archetypes first (Service Academy, HBCU Standard) — deterministic from school identity.
2. Coach-centric archetypes (Coach Cult, Celebrity Appointment, Mercenary) — require a named head coach entity + recency < 3 seasons.
3. Competitive-state archetypes (Newly Crowned, Anxious Dynasty, Wounded Giant, Identity-Crisis Blueblood, Quiet Professional, Content Mid-Major, Hopeful Uprising, Generational Hope, Perpetual Believer, Sleeper, Stockholm Syndrome, Petulant Blueblood, Regional Identity) — from recency signals + conversation sentiment + record trajectory.

Confidence score: weighted sum across rule hits, normalized 0-1. Minimum confidence 0.60 to emit; below that, assign a fallback `Quiet Professional` (safest prior) with confidence 0.60 and log the team for manual review.

Modifiers: 0-3 per fanbase. Deterministic rules (grep for known program properties — e.g., Notre Dame → `Independent` + `Faith-Based` + `Pedigree-Entitled`).

Historical classification (for the migration sparkline): run the classifier against each of the last 5 completed seasons using season-end context, writing to `fanbase_classification_history`. This runs **once per season**, not weekly.

**3.2 Hub-page taxonomy section**

The copy, card shape, and 6-week migration sparkline pattern are all specified in the Figma `FanbaseArchetypesTaxonomy.tsx` file. Open that component once, mirror its structure in Python, and stop. Do not re-design cards. The 18 primary names, descriptions, team assignments with match %, signature phrases, 6-week migration arrays, and modifier strip are authoritative as shipped — copy them into a Python constant (`ARCHETYPE_CARDS_047 = [...]`) verbatim.

Per-card render:
- Condensed display name (`THE IDENTITY-CRISIS BLUEBLOOD`).
- Serif description.
- 2-4 team chips with confidence percentages (`MICH 96%`, `FSU 92%`).
- `SIGNATURE PHRASE` mono-caps label → phrase in mono italic with typographer quotes (emit `&rsquo;` as HTML entity, mirroring the Figma pattern).
- `MODIFIERS` mono-caps label → 0-3 modifier chips (grey pill, mono caps, subtle border) with the amber `#E0A300` dot indicator where modifiers are strip-wide.
- 6-week migration sparkline (SVG) + optional italic migration note (e.g., "Washington joined; LSU fading.").
- The shared 8-modifier strip renders once below the grid — copy its text verbatim from the Figma file.

**3.3 Team-page archetype module**

On every team page, replace the "Awaiting Signal" fallback (currently at `reporting.py:~14830`) with an archetype block:
- Primary archetype name + confidence in mono.
- Signature phrase in mono italic.
- Active modifiers as chips.
- 5-season migration sparkline for this specific team.
- Link back to `/hub/#sec-04` for the full taxonomy.

**Offseason mode** (from `CLAUDE_CODE_FIX_PROMPT.md P1.4`): when no current mood signal is available, the team page shows the archetype block + a compact "Mood: offseason floor. Next reading after fall camp." line. Never render "Awaiting Signal" repeated six times.

**Acceptance:**
- `grep -l "Awaiting Signal" output/site/teams/*.html | wc -l` → 0.
- `grep -l "SIGNATURE PHRASE" output/site/teams/*.html | wc -l` → 133 (every FBS team page has one).
- `grep -c "Primary:" output/site/hub/index.html` → 18.
- `grep -oE 'MODIFIERS' output/site/hub/index.html | wc -l` → 18.

### Phase 4 — Three new flagship modules  **[Sonnet, with Opus for Lexicon phrase-mining rule]**

**4.1 Mood Ticker (N° 02)** — `render_mood_ticker(week)` reads top 10 biggest `delta_from_prev_week` values from `fanbase_mood_weekly`, splits 5 gainers (top) / 5 losers (bottom). Each pill = team chip + score + delta chip (amber if positive, alert red if negative) + one-line serif italic cause.

**4.2 Rivalry Obsession Matrix (N° 05)** — `render_rivalry_matrix(week)` reads the 12 canonical rivalries from `rivalry_obsession_weekly`. Hard-code the rivalry set in a Python constant `FLAGSHIP_RIVALRIES = [(team_a_slug, team_b_slug, display_name), ...]` — there are only 12 and they don't change week-to-week. Each cell: two team chips + proportional color bar + ratio in mono + one-line italic serif take.

**4.3 Lexicon of the Week (N° 06)** — `render_lexicon_feature(week)` reads the `featured=true` row from `lexicon_weekly`. Asymmetric 60/40 layout: 3-paragraph serif explainer on the left, 4-week sparkline + 3 sample quotes on the right.

For the phrase-mining rule (the `--featured` pick), use Opus once to design the selection heuristic. Candidate rule: among all phrases in `lexicon_weekly` for that week with `spike_pct_wow >= 100` and `mention_count >= 500`, pick the one with the highest *novelty score* (inverse frequency over prior 12 weeks). Cap: only pick a phrase if we have ≥3 quotable samples.

**Acceptance:**
- `grep -c 'id="sec-02"' output/site/hub/index.html` → 1.
- `grep -oE 'THE TICKER\|THE RIVALRY\|THE LEXICON' output/site/hub/index.html` → 3 hits.
- Mood Ticker: `grep -oE '<article class="ticker-pill"' output/site/hub/index.html | wc -l` → 10.
- Rivalry Matrix: `grep -oE '<article class="rivalry-cell"' output/site/hub/index.html | wc -l` → 12.
- Lexicon: exactly one featured-phrase feature renders; the sparkline has 28 data points (daily over 4 weeks) or 4 (weekly), whichever matches the ingest.

### Phase 5 — Chart polish  **[Sonnet]**

Apply every fix from `FAN_INTEL_HUB_V4_A_PLUS_REVIEW.md §3`. Concretely:

**Cover chart:**
- Render Michigan line in `#00274C` (Michigan blue) with maize `#FFCB05` endpoint dot.
- Add endpoint label `MICH 58` in mono at the right edge of the line.
- Add vertical tick at Mar 14 annotated `Moore presser` (mono italic).
- Anchor the `10-year average` label to the right endpoint of the dashed line inside the chart.
- Straighten x-axis date labels (horizontal, not rotated).
- Add `Chart by The Index Desk · Model: power-resume-v1.3.2` byline in mono micro below the italic serif caption.
- Add the "ALSO READING" rail below the chart (3 teasers).

**Mood Index (N° 01):**
- Two-reds fix: render Alabama in houndstooth grey `#828A8F` on the Mood Index chart only. Document the override in a comment.
- Move `playoff confidence` reference line label to chart-left whitespace.
- Color delta chips semantically: positive in amber `#E0A300`, negative in alert red `#B7281D`.
- Downsize right-rail team chips from 28px to 20px.
- Axis labels: mono + `font-variant-numeric: tabular-nums`.

**Hype vs Reality (N° 03):**
- Truncate annotations to short form: `Nebraska — peak delusion.` and `Michigan — underrated by its own.`
- Scale the ghosted quadrant words (`DELUSIONAL / JUSTIFIED / REALISTIC / SLEEPING GIANT`) to ~85% of current size so they stay inside chart bounds.
- Rotate the `Fan Hype Level` axis title to vertical (or replace with corner caption `Y: Fan Hype · X: Model Reality`).

**Acceptance:**
- Open `/hub/index.html` in a local server (`python -m http.server --directory output/site 8000`) and eyeball each chart against `FIGMA_MAKE_V5_PROMPT.md`.
- `grep -c "Moore presser" output/site/hub/index.html` → ≥1.
- `grep -c "Michigan blue\|#00274C" output/site/hub/index.html` → ≥1 (in style or data).
- No delta chip in the Mood Index right rail has a `-` prefix rendered in amber — all negatives are alert red.

### Phase 6 — Editorial voice consistency + cross-cutting polish  **[Haiku subagent, bundled]**

These are mechanical, cheap, and visible. **Batch them into a single Haiku subagent turn.** The subagent reads this whole section, produces one diff across all six items, runs the verification greps at the bottom of §4 for the Phase 6 items, and reports back. No Sonnet time spent on finds-and-replaces.

**6.1 Footer `73 conferences` fix.** `grep -n "73 conferences\|73 FBS conferences" src/cfb_rankings/reporting.py` → change to `10 FBS conferences`, OR delete the conference count from the footer data-scope line. Decision: keep `10 FBS conferences` — scope discipline is a credibility signal.

**6.2 Methodology row consistency.** Use the `render_methodology_row()` partial from Phase 2 on every chart. Grep for any inline `"n ="` strings in `reporting.py` under the hub renderer and replace with the partial call. Acceptance: `grep -c 'class="methodology"' output/site/hub/index.html` equals the number of chart-bearing sections.

**6.3 Typographer quotes sweep.** Run a scoped `sed` (via a Haiku subagent) over Python string literals in the hub renderer path: convert ASCII `"..."` inside user-visible copy to curly `"..."`, and ASCII `'` to `'`. **Do NOT touch Python string delimiters or dict keys.** The subagent must only edit rendered-text string values. Review the diff before committing.

**6.4 Editor's Note drop cap + measure.** CSS: `.editors-note-body { max-width: 64ch; }` and add a `::first-letter` rule that renders at 4rem condensed display, float left, with `margin-right: 0.35em` and tight `line-height: 0.9`. Verify visually.

**6.5 `— the staff` signoff consistency.** Editor's Note should append ` · 22 Apr 2026` to match the commiseration block. Fix in the copy dict.

**6.6 Internal label renames + `model_version` leak** (from `CLAUDE_CODE_FIX_PROMPT.md P1.2 + P1.3`, not yet shipped at time of writing). If those haven't landed yet, bundle them here:
- `Stress Point` → `Pressure Point` (`reporting.py:13116`).
- `Offensive Reminiscence` → `Offensive Comp` (`reporting.py:13465`).
- `Defensive Reminiscence` → `Defensive Comp` (`reporting.py:13483`).
- Remove `Player Card Blueprint` block (`reporting.py:9821`).
- `model_version` (`config.py:43`) stays as internal semver; add a `FRIENDLY_MODEL_LABEL = "CFB Index v1"` and use that in user-visible copy.

**6.7 Prev/next issue chevrons + Subscribe link in nav.** Nav tuples at `reporting.py:11717-11723` — add the `← N° 046` / `N° 048 preview →` chevrons (hide N° 048 if the future issue doesn't exist yet) and a `Subscribe` text-link to the far right.

**Acceptance:**
- `grep -R "Reminiscence\|Player Card Blueprint\|Stress Point\|73 conferences" output/site | wc -l` → 0.
- `grep -R "power-resume-v" output/site --include='*.html' -l` → 0 in visible body (scripts OK).
- Visual: drop cap renders at 3 lines tall on the Editor's Note.

### Phase 7 — Team-page fan-intel resurrection  **[Sonnet]**

This is the final piece. With Phase 3's classifier live, the team page archetype module already ships on every FBS team. Now replace the remaining "Awaiting Signal" fallback paths entirely:

- `reporting.py:~14830` — rewrite the Mood Card fallback branch: if `fanbase_mood_weekly` has no row for this team this week, fall through to the archetype module (Phase 3) + a single line `Mood: offseason floor. Next reading after fall camp.` No six-metric stacked "Awaiting Signal" grid.
- `fan_intelligence.py:833-838` — change the default dict so the generator never returns a row of `"Awaiting Signal"` values. Default to `None` + let the renderer decide the fallback.

**Acceptance (from `CLAUDE_CODE_FIX_PROMPT.md P1.4`):**
`grep -c "Awaiting Signal" output/site/teams/*.html | awk -F: '$2>0{c++} END{print c}'` → 0.

---

## 4) Verification protocol

Run inside a Haiku subagent. One bash call.

```bash
set -e
cd "<repo root>"

echo "== Phase 1 schema seeded =="
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM archetype_taxonomy WHERE kind='primary';"   # expect 18
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM archetype_taxonomy WHERE kind='modifier';"  # expect 8
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM fanbase_classification WHERE season=2025;"  # expect 133

echo "== Phase 2 hub page sections =="
grep -oE 'id="sec-0[1-8]"' output/site/hub/index.html | sort -u | wc -l   # expect 8
grep -oE 'N° 0[1-8]' output/site/hub/index.html | sort -u | wc -l        # expect 8

echo "== Phase 3 archetype on hub =="
grep -oE 'class="archetype-card"' output/site/hub/index.html | wc -l      # expect 18
grep -oE 'class="modifier-chip"'  output/site/hub/index.html | wc -l      # expect >=18 (1+ per card)

echo "== Phase 3 archetype on team pages =="
grep -lr "SIGNATURE PHRASE" output/site/teams/*.html | wc -l              # expect 133
grep -l "Awaiting Signal" output/site/teams/*.html | wc -l                # expect 0

echo "== Phase 4 new modules present =="
grep -oE 'class="ticker-pill"' output/site/hub/index.html | wc -l         # expect 10
grep -oE 'class="rivalry-cell"' output/site/hub/index.html | wc -l        # expect 12
grep -c 'class="lexicon-feature"' output/site/hub/index.html              # expect 1

echo "== Phase 5 chart polish =="
grep -c "Moore presser" output/site/hub/index.html                        # expect >=1
grep -c "Chart by The Index Desk" output/site/hub/index.html              # expect >=1

echo "== Phase 6 voice consistency =="
grep -c '73 conferences' output/site/hub/index.html                       # expect 0
grep -c '10 FBS conferences' output/site/hub/index.html                   # expect 1
grep -c 'class="methodology"' output/site/hub/index.html                  # expect >=6 (per chart-bearing section)
grep -R "Reminiscence\|Player Card Blueprint" output/site | wc -l         # expect 0
grep -R "power-resume-v" output/site --include='*.html' -l | wc -l        # expect 0 in visible body

echo "== overall =="
wc -c output/site/hub/index.html                                          # sanity: should be >100KB and <2MB
```

**Spot-check in a browser:**
- `/hub/index.html` — scroll top to bottom, confirm all 8 sections + correct numbering + drop-cap on Editor's Note + semantic delta colors on Mood Index + 12 rivalry cells in matrix.
- `/teams/michigan.html` — archetype block renders "Identity-Crisis Blueblood" with modifiers.
- `/teams/georgia.html` — archetype block renders something in the Quiet Professional / Anxious Dynasty family with modifiers.
- `/teams/jackson-state.html` — archetype block renders "The HBCU Standard" (new).
- `/teams/army.html` — archetype block renders "The Service Academy".

**Design review at the end (not during):**
- Invoke `design:design-critique` on `/hub/index.html`.
- Invoke `design:accessibility-review` on `/hub/index.html` and `/teams/alabama.html` — contrast, focus, tabular-nums, skip-link.

---

## 5) Deliverable

When done, commit changes, then post a summary:

1. **What changed** — one line per phase.
2. **What's verified** — the verification-protocol output table.
3. **What you deferred** — anything from `FAN_INTEL_HUB_V4_A_PLUS_REVIEW.md §The 10-item punch list` or `FIGMA_MAKE_V5_PROMPT.md` you didn't ship, with reason.
4. **Diff stats** — `git diff --stat main..HEAD`.
5. **Build artifact location** — `/hub/index.html`, `/teams/michigan.html`, `/teams/jackson-state.html`, `/teams/army.html` (reviewers should open these in order).

Do not write a retrospective. If you introduce a new CLI subcommand, add exactly one line to `README.md` pointing at it.

---

## 6) Execution order (optimized for cost)

The cadence is: **one Opus call per phase that needs judgment, Sonnet for everything else, Haiku in parallel for all verification and mechanical sweeps.** No Opus session lasts more than one round-trip.

0. **Pre-flight** (Sonnet, <2 min). Unzip `Fan Intelligence Hub Design (3).zip` to a scratch dir. Confirm the 13 publication components are present. Ignore `src/app/AppV5.tsx` entirely — it is dead code, do not read it.
1. **Sonnet — orientation** (one turn, ≤8k tokens). Read `CLAUDE.md`, skim this brief, skim `FAN_INTEL_HUB_V4_A_PLUS_REVIEW.md` §3. Spawn a Haiku subagent to run the "First-move grep map" from §2 and report back in ≤1k tokens. Produce a one-paragraph plan of attack. **Stop. Do not start fixing yet.**
2. **Opus one-shot — Phase 1 schema + migration pattern** (≤6k tokens). One prompt in, one plan out. No code. Drop to Sonnet.
3. **Sonnet — Phase 1 implementation** (≤8k tokens). Migrations + CLI subcommands + seed data. Run `python manage.py migrate && python manage.py seed-archetypes && python manage.py classify-fanbases --season 2025`. Haiku subagent verifies with §4 SQL counts.
4. **Sonnet — Phase 2 implementation** (≤18k tokens). Read `App.tsx` + the 13 publication components *once*. Build hub-page section wrappers + shared partials + copy dict from that reference. Build once (`python -u manage.py build-site`). Haiku subagent confirms 8 sections render with `N°` numbering. **`/compact` here.**
5. **Opus one-shot — Phase 3 classifier weights** (≤4k tokens). Weight vector + tie-breakers only. Drop to Sonnet.
6. **Sonnet — Phase 3 implementation** (≤18k tokens). Classifier rules engine + hub taxonomy grid (copy verbatim from Figma `FanbaseArchetypesTaxonomy.tsx`) + team-page archetype module. Build. Haiku subagent verifies `grep -l "Awaiting Signal" output/site/teams/*.html` returns 0.
7. **Opus one-shot — Phase 4 Lexicon phrase-mining heuristic** (≤3k tokens). Criterion + thresholds, no code.
8. **Sonnet — Phase 4 implementation** (≤15k tokens). Mood Ticker, Rivalry Matrix, Lexicon Feature renderers, sourcing copy from `MoodTicker.tsx`, `RivalryMatrix.tsx`, `LexiconWeek.tsx`. Build. **`/compact` here.**
9. **Sonnet — Phase 5 chart polish** (≤10k tokens). All fixes from the A+ review.
10. **Haiku subagent — Phase 6 mechanical sweeps** (≤6k tokens, one bundled turn). `73 conferences`, typographer quotes, internal label renames (`Stress Point` → `Pressure Point`, `Reminiscence` → `Comp`, drop `Player Card Blueprint`), `model_version` → `CFB Index v1`, methodology row consistency. Subagent diffs its own changes before committing. **`/compact` here.**
11. **Sonnet — Phase 7** (≤5k tokens). Team-page `Awaiting Signal` replacement. Two `Edit` calls.
12. **Haiku subagent — full verification** (≤2k tokens). §4 one-bash-call.
13. **Skills — `design:design-critique` + `design:accessibility-review`** at the end, one invocation each. Not during the build.
14. **Sonnet — final summary** (§5, ≤2k tokens). Then `./publish_site.ps1` and ship.

**Budget guardrails:**

- **Total target ≤110k tokens** across the full build. If you cross 80k before Phase 5, stop and `/compact`; you are reading too much.
- **No Opus session >1 round-trip.** Each of the three Opus calls is exactly one prompt and one reply. If Opus needs follow-up, it is because you under-specified the prompt — rewrite and retry, don't let it run long.
- **No Sonnet turn >6k tokens of output code.** If the diff is bigger than that, split into two phases.

**Checkpoint discipline:** `/compact` after Phase 2, Phase 4, and Phase 6 (three checkpoints). Update `CLAUDE.md` with any new line numbers discovered, in one-line entries per finding.

**Fail-fast rule:** if any `build-site` call after Phase 2 onward fails, stop and fix before advancing — never let build failures compound across phases.

Go.
