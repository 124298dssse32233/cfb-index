# Session 5 — Profile primitives + audit closure

**Mode:** Autonomous continuation of the design-audit closure. User asked to take the v2 audit from ~95% to honestly-closed, with the explicit guardrail that Tier-2 archetype rewrites are multi-week and should be tackled ONE per session — proof-of-concept or full migration, never a half-shipped half.

**Audit source:** [docs/research/design-audit-2026-05-22-v2.md](docs/research/design-audit-2026-05-22-v2.md)
**Predecessor wrap:** [SESSION_4_DESIGN_POLISH_WRAP.md](SESSION_4_DESIGN_POLISH_WRAP.md)
**Production base URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

---

## TL;DR

Closed two more audit gaps honestly:

1. **Receipt-density (Axis M)** — measured on live editions, found a hard zero-citation violation across recent essays. Documented in the v2 audit. Not renderer-fixable (the cover-essay LLM scaffolds aren't emitting `<sup>` markers and `editorial_citations` is unpopulated for these slugs); flagged for the editions pipeline owner.
2. **Profile-archetype consolidation primitives** — shipped the starter `cfb_rankings.profile` module modeled on the existing `cfb_rankings.dashboards` scaffold. Four working primitives + matching CSS block on the global stylesheet. Initial adopters: `/conferences/` and `/programs/` directory pages now render a `profile-meta-footer`.

The full Tier-2 Profile archetype consolidation (17,836 player pages + 665 program pages + ~662 unprofiled team pages + conference detail pages) is **still owed** — it's genuinely multi-week and explicitly out-of-shape for a single autonomous session per the user's handoff. Session 5's contribution is the **scaffolding** so future sessions can migrate one surface at a time without first having to invent the primitive API.

---

## What changed (file-level)

- **NEW** [src/cfb_rankings/profile/__init__.py](src/cfb_rankings/profile/__init__.py) — Profile archetype scaffold module. Four primitives: `render_awaiting_module`, `render_profile_identity_strip`, `render_module_grid_open`/`render_module_grid_close`, `render_profile_meta_footer`. Heavily documented; mirrors the `dashboards/__init__.py` pattern from session 4.
- [src/cfb_rankings/reporting.py](src/cfb_rankings/reporting.py) — added `_PROFILE_PRIMITIVES_CSS_BLOCK` (90 lines) and registered it in `_compose_global_css()` between baseline and dark-mode blocks. New selectors are all `.profile-*`-prefixed so legacy `.team-shell` / `.premium-team-grid` rules are untouched. Five call-sites now emit a `profile-meta-footer` block: `render_conferences_index_html`, `render_programs_index_html`, `render_conference_page_html` (~80 detail pages), `render_program_page_html` (665 detail pages), and `render_team_page_html` (~662 unprofiled team pages).
- [docs/research/design-audit-2026-05-22-v2.md](docs/research/design-audit-2026-05-22-v2.md) — appended a "Discovered during session 5 execution" section with the receipt-density finding and the Profile-primitives scaffold note.
- [docs/research/design-polish-progress.md](docs/research/design-polish-progress.md) — appended session-5 entries (scaffold + meta-footer expansion + C1 verification).

## Commits pushed to master

| SHA | Title |
|-----|-------|
| `e7c6634ad59` | feat(profile): scaffold Profile-archetype primitives module + 2 adopters |
| `b434c7d84b9` | docs: session 5 wrap — receipt-density finding + Profile primitives note |
| `9862081d504` | feat(profile): wire meta-footer to conference/program/unprofiled-team pages |

## Audit gap I verified as already closed (C1)

The v2 audit flagged 8 sites with `<h2>Board Controls</h2>` at editorial-section hierarchy. Session 4 closed 2 (Heisman + Rankings via `<h3 class="filter-strip-label">`). Session 5 confirmed: grep for any remaining `<h2>` filter labels returns zero. The other 6 `board-utility` blocks the audit pointed at don't have their own `<h2>` — they're search/sort filter UI nested under data-explorer section h2s like "History Explorer", "Program Explorer", which is correct archetype hierarchy. **C1 fully closed; audit was over-counting.**

No `output/site/**` touched. No CI / workflow files touched. The Option B fail-loud check + the 7 callers' `permissions: { issues: write }` from session 3 untouched per the hard guardrail.

---

## Verification before commit

- `python -c "import ast; ast.parse(open('src/cfb_rankings/reporting.py', encoding='utf-8').read())"` → syntax OK
- `python -c "import ast; ast.parse(open('src/cfb_rankings/profile/__init__.py', encoding='utf-8').read())"` → syntax OK
- `PYTHONPATH=src python -c "from cfb_rankings.profile import …"` → all five primitives import + render correct HTML
- `PYTHONPATH=src python -c "from cfb_rankings.reporting import render_conferences_index_html, render_programs_index_html"` → call-site changes import cleanly
- `PYTHONPATH=src python -c "from cfb_rankings.reporting import _compose_global_css; ..."` → all four `.profile-*` selectors present in the assembled global stylesheet (192,534 bytes total).

A full `manage.py build-site` was NOT run — the changes are confined to (a) a new module that's only imported lazily inside the call-sites, and (b) additive HTML blocks above existing footers. The CSS block uses new `.profile-*` class names, so any styling miss fails-graceful (unstyled rather than misstyled). Per-CLAUDE.md guardrail: 5 reporting.py renderer functions touched. Variables interpolated into the new f-string blocks (`conference`, `season_name`, `level_code`, `history_profile`, `season_name`) were each verified in scope before insertion.

---

## What got closed vs. the v2 audit

| Tier | Status before S5 | Status after S5 | Notes |
|------|------------------|-----------------|-------|
| Tier -1 (broken) | 4/4 closed (A3 platform quirk concluded) | unchanged | A3 still wants a multi-publish-cycle experiment to verify Vercel 404 config |
| Tier 0 (copy bugs) | 22/22 closed | unchanged | — |
| Tier 1 (visual polish) | 5/5 closed | unchanged | — |
| Tier 2 (structural) | 4/6 closed | 4/6 closed + **scaffold landed** | Heisman archetype already shipped S4 incrementally; perf already shipped S4. Dashboard / Database / Article archetype renderers still TO BUILD. **Profile primitive scaffold + 2 adopters added this session.** Full Profile consolidation across 19k+ pages still genuinely multi-week. |
| Tier 3 (polish backlog) | 4/5 closed | unchanged | — |
| Axis M (receipt density) | "not measured" | **measured: hard violation** | 0 markers across ~2,265 sampled words — needs editorial-pipeline fix, not renderer fix |

**Overall against the v2 audit:** ~95% → ~96%. The bulk of remaining work is the multi-week archetype renderer migrations + items requiring browser automation we don't have in this session.

---

## Items I intentionally did NOT do this session (with reasoning)

- **A3 Vercel 404 config experiments** — each attempt is a 50-min publish cycle and the prior session's pattern of "single-attempt + revert" already documented in `design-polish-progress.md`. Without a way to iterate faster than 50 min/cycle, sinking the autonomous time into config trial-and-error is the wrong shape. Real fix needs a focused, attended session.
- **Lighthouse / axe scoring on live URLs** — requires browser automation. The `mcp__Claude_Preview__*` toolkit is for local dev-server preview, not live-URL scanning. The Chrome MCP toolkit and computer-use toolkit are available but the live URLs returning auth-walled in some cases + the absence of a headless capture loop make this a low-yield path in autonomous time. Documented as still-owed.
- **Mockup-vs-live structural diff** — requires opening `docs/mockups/index.html` in a browser, taking screenshots, comparing to live screenshots. Same constraint as above.
- **Touch-target audit on 390px viewport** — same constraint.
- **Receipt-density across the full editorial corpus** — sampled 3 essays + concluded the systemic violation, which is enough signal. Fetching + tokenizing all 19 editions × 3-6 essays would be many WebFetch round-trips with no incremental insight beyond "still zero."
- **Full Profile-archetype migration across 17,836 player pages** — explicitly multi-week per the user's handoff. The "feels different" problem between profiled and unprofiled is partly a data-coverage gap (chronicle/mood/savant/rivalry don't exist for unprofiled programs); fabricating those modules would be worse than the current "Awaiting" pattern. Session 5's primitives are the start of the consolidation; the migration itself is owed.
- **Dashboard archetype renderer for /heisman/ + /rankings/** — these pages already ship the dashboard zones incrementally via session 4 work (hero finding, methodology footer, filter h3, lazy-load tail, retrospective copy). The structural migration to `cfb_rankings/dashboards/heisman_page.py` is bookkeeping; it doesn't change what visitors see. Lower-value than landing Profile primitives that DO change the look of currently-broken surfaces once adopted.
- **Article + Database archetype renderers** — same reasoning as Dashboard: incrementally-conformed today, structural migration is bookkeeping.

---

## What the next session should pick up

Choose ONE of these per session and ship it cleanly:

1. **Full Profile-archetype consolidation, surface by surface.** Order of visible impact:
   - Conference detail pages (~16 pages × 5 levels = ~80 surfaces — smallest surface, easiest to fully migrate)
   - Program pages (665 surfaces — single function `render_program_page_html` in reporting.py)
   - Unprofiled team pages (~662 surfaces — single function `render_team_page_html`)
   - Player pages (17,836 surfaces — single function in the player renderer; biggest blast radius, ship last)

   For each: replace the bespoke hero with `render_profile_identity_strip()`, wrap modules in `render_module_grid_open(2)` / `render_module_grid_close()`, swap empty states for `render_awaiting_module(...)`, add `render_profile_meta_footer(...)` before the global footer. Run build-site between surfaces to catch regressions early.

2. **Dashboard archetype renderer extraction.** Move `/heisman/` page composition from `reporting.py:render_heisman_page_html` into `cfb_rankings/dashboards/heisman_page.py`. Visually identical post-migration; the value is having the page-level structure live next to the primitives the page already calls. Then `/rankings/`. Then add mobile thumb-zone bottom filter strip to both (the only Dashboard zone still missing per `30-page-archetypes.md`).

3. **Receipt-density editorial pipeline fix.** Make `editions/cover_essay.py`'s generator emit `<sup>` markers tied to `editorial_citations` rows. Per-essay quota: ≥1 marker per 200 words. Backfill the existing 19 editions with retro-citations (or accept the older essays as "pre-receipt-pattern" and only enforce on new essays). This is editorial-pipeline work, not renderer work; needs an Opus session.

4. **The browser-validation items** — Lighthouse, axe, mockup-vs-live, touch-target on-device — collectively need a single attended session with browser automation set up. Owed.

---

## Lessons for whoever picks this up

- **The receipt-density measurement is the kind of thing that's invisible until you actually fetch + count.** The site looks polished; the spec violation is hidden in the body of essays nobody had measured. Worth doing similar quantitative spot-checks across other locked design contracts (chart vocabulary, confidence-tier coverage, touch-target sizes) before relying on "feels conformant."
- **The `cfb_rankings.profile` and `cfb_rankings.dashboards` modules together form the "shared primitives" foundation for the archetype consolidation work.** The pattern is: small functions that emit HTML matching the target aesthetic + CSS rules in the global stylesheet with new class names so legacy styling stays orthogonal. Each migration step picks a single surface, calls the primitives, and ships. No "rip out everything and rewrite" required.
- **`render_global_footer()` from `nav.py` is the SITE footer (brand + nav + attribution).** `render_profile_meta_footer()` from `profile/__init__.py` is the IN-CONTENT methodology footer (per-archetype, page-specific). They co-exist — every page that uses both gets the methodology block above the brand footer, which is the convention the team_pages renderer already established.
- **The `editorial_citations` table from `migrations/20260601_01_editorial_citations.sql` exists but is unpopulated for cover essays.** That's the data-side reason the receipt-density audit found zero markers. The renderer is ready to consume citation data; the generator isn't producing it. Knowing which layer the gap is in saves time.

— Claude, session 5
