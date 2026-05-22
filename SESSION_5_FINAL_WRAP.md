# Session 5 — Profile primitives + Dashboard zone closure + live-audit copy scrub

**Mode:** Autonomous, extended (user said "10+ hours, ok if you screw up, make the site perfect to show people"). Continuation of the design-audit closure that had been at ~95% after session 4.

**Audit source:** [docs/research/design-audit-2026-05-22-v2.md](docs/research/design-audit-2026-05-22-v2.md)
**Predecessor wrap:** [SESSION_4_DESIGN_POLISH_WRAP.md](SESSION_4_DESIGN_POLISH_WRAP.md)
**Production base URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

---

## TL;DR

Closed five categories of audit work — three structural (Profile primitives, Dashboard zone, Player surface adoption) and two visible-polish (placeholder-copy purge, dev-vocab purge). Triggered a publish-site deploy to land everything. Authentic live verification (WebFetch on multiple URLs) drove the polish pass — that's how the homepage placeholder and the methodology dev-vocab leaks both surfaced.

**Best single fix in this session:** the homepage was rendering literal dev text ("Issue XIX placeholder. Pattern C cover essay generation fills this in on next world_class_enrich") as the most-recent edition's cover caption. Live-verified before the fix, replaced with brand-voice editorial copy. Also fixed the upsert logic so the DB-resident placeholder gets replaced on re-seed (a quiet Hotfix-13 gap: the original protected against overwriting Pattern C output, but didn't protect against overwriting placeholders → upgraded seeds).

---

## Commits pushed to master (chronological)

| SHA | Title |
|-----|-------|
| `e7c6634ad59` | feat(profile): scaffold Profile-archetype primitives module + 2 adopters |
| `b434c7d84b9` | docs: session 5 wrap — receipt-density finding + Profile primitives note |
| `9862081d504` | feat(profile): wire meta-footer to conference/program/unprofiled-team pages |
| `3cd7929ab0b` | docs(session5): wrap update — 5 Profile adopters live + C1 verified closed |
| `e8827d844a9` | feat(profile,dashboards): player-page meta-footer + Dashboard mobile filter strip |
| `0ee77130e19` | fix(credibility): replace dev-commentary placeholder copy in editions XVIII/XIX |
| `1f1e5a88cf4` | fix(editions): upsert overwrites known dev-placeholder dek+body |
| `32d50d14f20` | fix(copy): scrub dev-vocab from methodology page + rankings chart placeholder |
| `14b1ce2860f` | fix(copy): scrub dev-vocab + technical jargon from player + rivalry empty states |
| `eda166524be` | fix(copy): scrub team_rating_deltas table-name leak from vibe-shifts page |
| `b71af686f73` | docs(session5): comprehensive wrap reflecting all 10 commits + live-audit findings |
| `6b11a9f022c` | fix(copy): scrub remaining dev-vocab from fan-intel methodology + daily auto-summary |
| `3efb483481c` | feat(profile): wire meta-footer to /history/ and /teams/ index pages |
| `1823767ae4c` | fix(portal-heat): scrub "S3. PORTAL HEAT" sprint label + dedupe kickoff countdown |
| `3ace15f1c91` | fix(copy): replace "Generated YYYY-MM-DDTHH:MM:SSZ" footer with "Updated" |
| `e1e06b6dc1a` | fix(copy): footer tagline "BUILT FOR THE OFFSEASON" → "WHERE EVERY TEAM STANDS" |
| `d75b1123c4e` | fix(copy): missing "that" on /attributions/ — TheSportsDB explanatory sentence |
| `c07894eca39` | fix(copy): scrub Sprint-13 references from storyline-thread receipt stubs |
| `be3598744d2` | fix(footer): omit "NO. —" placeholder on pages without an edition number |
| `d63b108c895` | chore(docs): archive 7 more historical CLAUDE_CODE_*.md planning docs |
| `044fb67e45b` | docs(session5): wrap reflects all 20 commits + 8 Profile renderer adopters |
| `e7998d2340e` | fix(copy): scrub remaining table-name leaks on NFL pipeline + Dynasty Heatmap |

22 commits this session. Last-touch: `e7998d2340e`.

---

## What changed (by axis)

### Structural — Profile archetype consolidation primitives

- **NEW** [src/cfb_rankings/profile/__init__.py](src/cfb_rankings/profile/__init__.py) — Profile archetype scaffold. Four primitives modeled on the existing `cfb_rankings.dashboards` pattern: `render_awaiting_module`, `render_profile_identity_strip`, `render_module_grid_open` / `render_module_grid_close`, `render_profile_meta_footer`.
- [src/cfb_rankings/reporting.py](src/cfb_rankings/reporting.py) — added `_PROFILE_PRIMITIVES_CSS_BLOCK` (90 lines) to the global stylesheet via `_compose_global_css()`. New `.profile-*` class names — legacy `.team-shell` / `.premium-team-grid` styling stays orthogonal so adoption is non-breaking.

### Structural — Profile primitive adoption (6 renderers, ~19,238 surfaces)

The `profile-meta-footer` block now ships above the global footer on:

| Renderer | Surfaces |
|----------|----------|
| `render_conferences_index_html` | 1 |
| `render_conference_page_html` | ~80 (FBS/FCS/DII/DIII conferences) |
| `render_programs_index_html` | 1 |
| `render_program_page_html` | 665 |
| `render_team_page_html` (unprofiled teams) | ~662 |
| `render_player_page_html` | 17,836 |
| `render_history_index_html` | 1 |
| `render_teams_index_html` | 1 |

This closes the largest visible surface in the v2 audit's Tier-2 Profile-archetype consolidation item. Player pages were the biggest blast radius and are the audit's most-cited "feels different from the profiled aesthetic" surface. Total Profile-archetype adopters: **8 renderer functions covering ~19,240 surfaces.**

### Structural — Dashboard archetype mobile filter strip (closes the last archetype zone)

- [src/cfb_rankings/dashboards/__init__.py](src/cfb_rankings/dashboards/__init__.py) — added `render_mobile_filter_strip`. No-JS implementation; uses fragment anchors to scroll the existing inline filter UI into view.
- [src/cfb_rankings/reporting.py](src/cfb_rankings/reporting.py) — new `_PROFILE_PRIMITIVES_CSS_BLOCK` entry styles `.dashboard-mobile-filter-strip` as a 56px sticky bottom bar with thumb-friendly 44px chips. Visible only at `@media (max-width: 767px)` — desktop unchanged.
- Wired to `/heisman/` and `/rankings/`. Added stable `id` anchors to the existing filter h3s so the strip has stable scroll targets.

Per `docs/design-system/30-page-archetypes.md` §"Dashboard archetype", this was the only zone session 4 hadn't shipped. Now closed.

### Credibility — Homepage placeholder text purge

- [src/cfb_rankings/editions/seeds.py](src/cfb_rankings/editions/seeds.py) — replaced the homepage-rendering placeholder text for editions XVIII and XIX. Was: `"Issue XIX placeholder. Pattern C cover essay generation fills this in on next world_class_enrich"`. Now: brand-voice editorial captions + ~150-word real essay bodies for each.
- [src/cfb_rankings/editions/data.py](src/cfb_rankings/editions/data.py) — extended the Hotfix-13 upsert logic to detect known dev-placeholder text and treat it as upgradeable (the original protected against Pattern-C-output being demoted to placeholder, but didn't protect against placeholder→better-seed upgrades). Verified locally: `python manage.py seed-editions` now replaces the placeholder DB rows.

### Copy — Dev-vocabulary scrub (5 surfaces)

Live WebFetch audits of `/methodology/`, `/rankings/`, `/teams/alabama.html`, `/players/<slug>.html`, and `/hub/vibe-shifts/2025/18/` surfaced five remaining dev-vocab leaks. All five fixed:

1. [/methodology/](src/cfb_rankings/provenance/methodology_index_page.py) — removed "Auto-generated from `source_registry`" and the "source of truth: FAN_INTEL_SOURCE_STRATEGY.md in the repo" footer; reframed as plain reader-language.
2. [/methodology/fan-intelligence.html](src/cfb_rankings/provenance/methodology_page.py) — same "Auto-generated from source_registry" subtitle replaced with "Sourced from the live signal registry".
3. [/rankings/](src/cfb_rankings/reporting.py) — power/resume scatter plot's "Chart Focus" empty state was "Loading team context..." (looked like a stuck JS loader). Replaced with "Click any point on the chart" + the tap-to-lock instructions.
4. [Profiled team rivalry card](src/cfb_rankings/team_pages/rivalry_card.py) — "Win on file — commentary pending." dropped the dev-vocab tail: now just "Win recorded."
5. [/hub/vibe-shifts/<season>/<week>/](src/cfb_rankings/vibe_shifts.py) — "Source: `team_rating_deltas` (per-game power swings) joined to `games`" exposed the DB table names. Reframed in plain English.

Plus four more on player pages (in [reporting.py](src/cfb_rankings/reporting.py)):

6. Player Honors empty state — was "This card is now structured to absorb All-America, all-conference, player-of-the-week..." (dev docs). Now: "No formal honors on the ledger yet. ... The absence is the signal."
7. Signature Moment empty state — was "Lights up once multi-game coverage loads. Today's player_game_stats only carries 2025 Week 1 — we ship when the next weeks land." Replaced with reader-friendly explanation.
8. Scenario Explorer empty state — was "Lights up once the player has a qualifying signature metric." Now lists concrete example metrics and explains what the slider does.
9. The Room empty state — was "Belief tracking publishes once player-mention sample + author counts clear the floor." Now: "The Room reads fan conversation around a player — who's talking, what they believe, and how that shifts."

### Copy — Additional dev-vocab scrubs (extended session)

After the first round of live audits, further WebFetch passes surfaced more leaks; all fixed:

- [/methodology/fan-intelligence.html](src/cfb_rankings/provenance/methodology_page.py) — body listed counts using internal table names (`conversation_documents`, `source_observations`, `team_cohort_week`, "team-week divergence rows", "Live counts from the production DB", footer linking to `FAN_INTEL_SOURCE_STRATEGY.md` + `source_registry`, glossary parenthetical "(source: seeds/fi_glossary.yaml)"). All rewritten as plain English.
- [/daily/<slug>](src/cfb_rankings/auto_summary.py) — auto-summary card footer was `"Auto-generated · model_version auto-summary.v1 · cached 4h"`. Replaced with reader-language: `"AI-summarized · refreshed every 4 hours"`.
- [/portal-heat/](src/cfb_rankings/portal_heat/templates/portal_heat.html) — hero eyebrow read `"S3. PORTAL HEAT"` (Sprint 3 identifier). Reframed as `"Transfer Portal Heat Index"`. Also fixed the duplicated `"(92 days to kickoff) (92 days to kickoff)"` parenthetical — `cfb_week_label()` was already appending the countdown, and the template was duplicating it.
- [/anniversary/today/, /editions/, /methodology/freshness.html](src/cfb_rankings/today_in_history/renderer.py) — footer timestamp was `"Generated 2026-05-22T06:24:08Z"` (ISO-8601 dev format). Reframed as `"Updated <same timestamp>"`. Also dropped `"Regenerated by the weekly cron"` from freshness page.
- [Global footer](src/cfb_rankings/nav.py) — tagline read `"BUILT FOR THE OFFSEASON"` which read season-specific in a way that breaks year-round. Replaced with `"WHERE EVERY TEAM STANDS"` (matches the brand tagline).
- [Global footer NO— placeholder](src/cfb_rankings/nav.py) — rendered `"VOL. I · NO. —"` on every non-edition page, where the em-dash placeholder looked like missing data. Now: pages without an edition number get just `"VOL. I"`.
- [/storylines/<slug>/](src/cfb_rankings/storylines/renderer.py) — receipts panel placeholder was `"— Sprint 13 (Receipts) ships the live ledger."`. Reframed as `"— The Receipts Desk"` with body text explaining the editorial rationale.
- [/attributions/](src/cfb_rankings/reporting.py) — minor grammar polish on the TheSportsDB explanatory sentence (missing "that" before restrictive clause).

### Copy — Hero-title defensive fallback

- [src/cfb_rankings/reporting.py](src/cfb_rankings/reporting.py) — the homepage `editorial_context` default fallback (rarely-fired but legal code path) hardcoded "this week" tense and `is_offseason: False`. Reframed: `is_offseason` now actually derives from `is_offseason(current)`, copy is season-neutral.
- The homepage's offseason hero default `"How college football is actually feeling, week by week."` now matches the brand tagline `"Where every team stands, what every fanbase thinks."`

### Audit gap verified as already closed (C1)

The v2 audit flagged 8 sites of `<h2>Board Controls</h2>` filter-hierarchy bugs. Session 4 closed 2 (Heisman + Rankings). Session 5 grepped for any remaining `<h2>` filter labels — zero hits. The other 6 `board-utility` blocks the audit pointed at don't have their own `<h2>` — they're search/sort UI nested under correct data-section h2s like "History Explorer", "Program Explorer", which is correct archetype hierarchy. **C1 fully closed; audit was over-counting.**

### Receipt-density audit (Axis M) — measured: hard zero-violation

Sampled 3 recent edition essays via live WebFetch:

| Edition | Essay | Body words | Citation markers | Words/marker |
|---------|-------|-----------|------------------|--------------|
| 2026-w19 | `three-weeks-before-camp-whispers` | ~1,100 | 0 | n/a |
| 2026-w18 | `receipts-two-months-past-pre-draft-boards` | ~65 (placeholder, now fixed) | 0 | n/a |
| 2026-w17 | `after-the-bracket-three-conversations` | ~1,100 | 0 | n/a |

Spec floor: ≥1 marker per 200 words. Cover essays should have ~5–6 markers each. **Currently shipping zero.** Documented in the v2 audit's "Discovered during session 5 execution" section. Editorial-pipeline issue, not renderer (the `editorial_citations` table from `migrations/20260601_01_editorial_citations.sql` exists but is unpopulated for cover essays). Owed to a future session that can run the cover-essay LLM scaffolds with citation-emission turned on.

---

## Verification before commit

Each commit was syntax-checked with `python -c "import ast; ast.parse(open(...))"` before push. Import-tested the touched reporting.py functions to confirm scope. Smoke-tested the new primitives by direct-call:

- `render_player_page_html` with mock data → 46,100 bytes, contains `profile-meta-footer` ✓
- `render_conference_page_html` with mock data → 14,525 bytes, contains `profile-meta-footer` ✓
- All 6 new `.profile-*` and `.dashboard-mobile-filter-strip-*` selectors verified present in `_compose_global_css()` (194,479 bytes total) ✓

Ran `python -u manage.py build-site` in the background; the run successfully built 664 team pages + 664 program pages before I killed it (player pages would have taken much longer). That confirms the f-string interpolations on the new code paths are valid.

The seeds.py + data.py upsert change was verified by running `python manage.py seed-editions` and then querying the DB directly — confirmed the placeholder rows in editions 2026-w18 and 2026-w19 got replaced with the new editorial copy.

---

## Deploy state

Triggered publish-site workflow [26272150341](https://github.com/124298dssse32233/cfb-index/actions/runs/26272150341) (queued behind an already-in-flight run that started ~5:24 UTC). Both runs will deploy my session 5 changes; the second run picks up the later commits (placeholder fix, copy scrubs).

**Smoke-test canary:** `live_smoke_test.yml` runs every 30 min and opens an automation-failure issue if pass-rate drops below 95%. If session 5 broke anything visibly on the 28 sample URLs, that's where the alarm fires.

---

## What's still genuinely owed

These remain explicitly multi-week or out-of-shape for autonomous time:

- **Full Profile-archetype consolidation** — hero identity-strip swap + module-grid wrapper + typography token migration across the same 17,836+ surfaces I just added meta-footers to. The primitives are in place; the migration is the multi-week work.
- **Dashboard archetype renderer extraction** — move `/heisman/` and `/rankings/` page composition from `reporting.py` into `cfb_rankings/dashboards/heisman_page.py` / `rankings_page.py`. Visually identical post-migration; structural cleanup.
- **Receipt-density editorial pipeline fix** — needs the cover-essay LLM scaffolds to emit `<sup>` markers + populate `editorial_citations`. The renderer is ready to consume citation data; the generator isn't producing it.
- **A3 Vercel 404 config experiments** — each attempt requires a 50-min publish cycle. Iteration cost too high for autonomous time without faster verification.
- **Lighthouse / axe scoring + touch-target on-device measurement + mockup pixel-diff** — all require browser automation we don't have set up in this session.

---

## Lessons for whoever picks this up

- **The single most valuable autonomous activity was live WebFetch audits.** Three rounds of `mcp__cff3bf0e-34e8-466c-ab32-c6a04f4ba95d__web_fetch_vercel_url`/`WebFetch` of the homepage, methodology, rankings, alabama team page, and a player page surfaced ~9 real dev-vocab leaks that grep-only-on-source couldn't have caught (because the offending strings were in different shapes than I knew to grep for). Whenever the user says "make it perfect to show people," WebFetch a sample of live pages — that's the single fastest way to find what visitors actually see.
- **The Hotfix-13 upsert logic in `editions/data.py` is subtle.** It protects Pattern C–generated content from being demoted by re-seeds — but the symmetric protection (allowing seed UPGRADES of known-bad placeholder rows) was missing until session 5. If you change seed copy in the future and it doesn't appear after a re-seed, that's the place to look.
- **`render_global_footer()` from `nav.py` is the SITE footer (brand + nav + attribution). `render_profile_meta_footer()` from `profile/__init__.py` is the IN-CONTENT methodology footer.** They co-exist — every page that uses both gets the methodology block above the brand footer, which is the convention the team_pages renderer established. Don't conflate them.
- **The CSS for the new `.profile-*` and `.dashboard-mobile-filter-strip` selectors deliberately uses new class names** so legacy `.team-shell` / `.premium-team-grid` styling stays orthogonal. Future Profile-consolidation work can adopt the primitives one surface at a time without first having to coordinate a global CSS rewrite.
- **Workflow runs triggered via `gh workflow run ... --ref master` check out the latest master at run time**, not at queue time. So my queued publish-site picked up commits I added after triggering it, which was important — let me bundle multiple late-session fixes into one deploy.

— Claude, session 5 (extended autonomous)
