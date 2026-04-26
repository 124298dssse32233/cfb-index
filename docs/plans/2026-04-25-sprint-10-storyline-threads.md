# Sprint 10 — Storyline Threads v1 Implementation Plan

> **For Claude:** This plan is the execution log for Sprint 10. It runs autonomously per `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`. Token budget (~220k) is a target, not a stop condition.

**Goal:** Ship 8 active Storyline Threads with 3-5 historical chapters each + 1 fresh chapter, a per-thread reader page, an index page, and a contract file the homepage (Sprint 9) reads.

**Architecture:** New disjoint module `src/cfb_rankings/storylines/`. SQLite tables hold metadata + chapters. Seeded chapter content lives in `seeds/<thread-slug>.py` (auditable Python data). Renderer reads DB → emits standalone HTML to `output/site/storylines/`. CLI subcommands wire build into `manage.py`.

**Tech Stack:** Python 3, SQLite (via existing `Database` helper), Python `string.Template` substitution into HTML skeletons (no Jinja dep — matches team_pages convention while honoring brief's `templates/*.html` paths).

---

## Documented judgment calls (per autonomy contract)

| Decision | Alternatives | Why |
|---|---|---|
| Use `string.Template` substitution into `templates/thread.html` + `thread_index.html`, no Jinja2 | (a) Jinja2 dep, (b) Pure f-strings in renderer.py | Honors brief's filesystem layout AND the team_pages "no Jinja" convention. Reversible — can swap to Jinja later. |
| Author chapter bodies as Python data in `seeds/<thread-slug>.py`, not via runtime LLM calls | (a) Live Anthropic SDK calls, (b) JSON files | Auditable, version-controllable, deterministic. The brief says "Sonnet writes" — I (Sonnet) write directly via parallel subagents into seed files. Live LLM-call infra is its own future sprint. |
| `generate-thread-chapter --auto` is a stub that writes to a draft seed file pending human review | Live LLM call producing DB row | Reversibility — first pass goes through human review before publish. Future sprint can wire live writes once voice quality is validated. |
| Render from brief's component spec; defer Figma node `62:2` fidelity audit | Block on Figma fetch | Brief lacks Figma file key. Component list is explicit. Style inherits from team_pages. Deferred audit is logged as known follow-up. |
| Emit `stub_data/threads.json` from this sprint as a Sprint 9 contract | Wait for Sprint 9 to write the file | Sprint 9 is concurrent; Sprint 10 owns canonical thread data. Emitting the file unblocks Sprint 9's homepage integration. |
| National threads (no program anchor) inherit "Editor's Desk" voice; program-anchored threads inherit profile voice; conference-level threads use a synthetic Big Ten/SEC register | Block on conference-profile sprint | Per autonomy contract: when briefs are silent, default to the editorially-congruent choice. |
| Migration uses `executescript` via existing `db.apply_sql_file()` — no schema diff tool | Roll a schema diff utility | Reuses existing helper. Idempotent on re-run. |

---

## Phase 1 — Schema + scaffold + thread metadata

**Files:**
- Create: `migrations/20260425_10_storylines_schema.sql`
- Create: `src/cfb_rankings/storylines/__init__.py`
- Create: `src/cfb_rankings/storylines/seed_loader.py` — reads seed modules → DB
- Create: `src/cfb_rankings/storylines/seeds/__init__.py` — registry of thread seeds
- Create: `src/cfb_rankings/storylines/seeds/_metadata.py` — 8 thread metadata records (no chapters yet)

**Step 1.1 — Migration.** Write the 3-table schema (storyline_threads, storyline_chapters, storyline_followers_stub) with header comment per existing migration pattern.

**Step 1.2 — Apply migration.** `python -c "from cfb_rankings.config import load_config; from cfb_rankings.db import Database; Database(load_config().database_url).apply_sql_file('migrations/20260425_10_storylines_schema.sql')"`. Expected: silent success.

**Step 1.3 — Module scaffold.** `__init__.py`, `seed_loader.py`, `seeds/__init__.py`. Seed loader exposes `load_all_seeds(db)` which iterates registered thread modules and upserts threads + chapters.

**Step 1.4 — Thread metadata seeds.** 8 records with title, dek, accent_hex, status='active', started_at, primary_program_slugs (JSON), primary_conference_slug.

**Step 1.5 — Verify.** Run `select count(*) from storyline_threads` after seeding metadata-only — expect 8.

## Phase 2 — Chapter generation (parallel subagents)

**Files:**
- Create: `src/cfb_rankings/storylines/seeds/<8 slugs>.py` — one per thread, each with full chapter list

**Strategy.** Dispatch 8 Sonnet subagents in parallel via Agent tool. Each subagent gets:
- Voice contract excerpt (Chronicle brief Rules 1-10 + banned phrases)
- Thread metadata (title, dek, accent, anchor program/conference, started_at)
- Voice register source (program profile excerpt or Editor's Desk synthetic)
- Brief excerpts: Stratechery compounding-canon rule, source-citation requirements, byline format
- Strict output contract: Python literal `CHAPTERS = [{...}, ...]` with all required fields
- Each chapter: 800-1500 words, ≥1 prior-chapter reference, ≥3 verbatim source citations, banned-phrase clean

**Step 2.1 — Dispatch 8 subagents in parallel** (one Agent tool batch).

**Step 2.2 — Collect & validate.** For each returned seed file: write to disk, run voice_validator on every chapter body, log pass/fail. Single retry per failed chapter via narrower subagent prompt. Chapters that fail twice → flagged in report, kept in seed for human review.

**Step 2.3 — Re-run seed_loader to insert chapters.** Confirm row counts.

## Phase 3 — Renderer + templates

**Files:**
- Create: `src/cfb_rankings/storylines/templates/thread.html` — reader page skeleton (`${var}` slots)
- Create: `src/cfb_rankings/storylines/templates/thread_index.html` — index page skeleton
- Create: `src/cfb_rankings/storylines/templates/_styles.css` — inlined into both templates
- Create: `src/cfb_rankings/storylines/renderer.py` — `render_thread(db, slug, output_dir)`, `render_index(db, output_dir)`, `render_all(db, output_dir)`
- Create: `src/cfb_rankings/storylines/render_helpers.py` — markdown-to-HTML, drop cap, pull quote, sources panel, breadcrumb

**Component checklist (per brief §Phase 3):**
- Thread page: breadcrumb + title + dek + meta strip (chapter count, follower count placeholder, status, accent bar) + Follow CTA (form-stub) + chapter index (newest first, chapter # badges, dek per chapter) + current chapter (drop cap on first ¶, body, pull-quote, sources panel) + related threads (3 cards) + Receipts placeholder + footer
- Index page: header + 8 thread cards (title, dek, accent bar, last-chapter date, chapter count) + footer

**Step 3.1 — Templates.** HTML files with `${slot}` placeholders. CSS inlined into a `<style>` tag in each template.

**Step 3.2 — render_helpers.** Pure-Python markdown-light (paragraphs, blockquotes, links, em/strong, "smart quotes"), drop-cap wrapper, citation formatter.

**Step 3.3 — renderer.py.** `render_thread(db, slug, output_dir)` queries the thread + all chapters + 3 related threads + Receipts placeholder list, applies template substitution, writes to `output_dir/<slug>.html`. Same for index.

**Step 3.4 — Render all 8 + index.**

**Step 3.5 — Verify.** `ls output/site/storylines/` should show 9 files. Open `12-team-playoff-settling.html` and confirm structure renders.

## Phase 4 — Homepage contract emission

**Files:**
- Create: `stub_data/threads.json` — 8 thread teasers Sprint 9 reads

**Step 4.1.** `renderer.py` has `emit_homepage_threads_json(db, output_path)` that writes `[{slug, title, dek, accent_hex, latest_chapter_title, latest_chapter_dek, last_chapter_at, chapter_count, href}, …]`. Marker key `_emitted_by_sprint_10` so Sprint 9 knows the contract.

**Step 4.2.** Render-pipeline calls this after rendering. CLI also exposes it.

## Phase 5 — CLI subcommands

**Files:**
- Modify: `src/cfb_rankings/cli.py` — insert two subparsers in alphabetical merge zone (between `generate-chronicle` and `render-team`, and after `render-team` before `refresh-savant`) + dispatch in handler

**Subcommands:**
- `generate-thread-chapter --thread <slug> --auto` — writes a draft chapter dict to `seeds/_drafts/<slug>_<timestamp>.py` (stub for live LLM in a future sprint)
- `render-storylines [--all]` — runs `seed_loader.load_all_seeds(db)` then `renderer.render_all()` then emits `stub_data/threads.json`

**Step 5.1.** Add subparsers + handlers, importing from the storylines module.

**Step 5.2.** End-to-end: `python -u manage.py render-storylines --all` should re-seed, render 8+1 pages, and emit the JSON contract.

## Phase 6 — Self-verification

**Step 6.1.** Voice-validator sweep on every chapter body. Compute pass-rate. Target ≥80% per brief.

**Step 6.2.** Source-citation count per chapter. Target ≥3.

**Step 6.3.** Cross-chapter reference count: every chapter beyond #1 must reference ≥1 prior chapter id. Compute compliance rate.

**Step 6.4.** Render-output integrity: grep rendered HTML for banned phrases (should be 0). Grep for required structural classes.

**Step 6.5.** File counts: 9 HTML files, 1 JSON contract, 8 seed modules, 1 migration, 2 templates, 1 CSS, ≥3 module Python files.

## Phase 7 — Sprint report

**Files:**
- Create: `output/sprint_reports/sprint-10-storyline-threads.md`

Per the reporting contract: phases completed, judgment calls (this doc), token usage by model, validation results, files touched, concurrency notes, quality concerns, natural next.

---

## File ownership recap (concurrency safety)

**Created (sole owner):** all of `src/cfb_rankings/storylines/`, `migrations/20260425_10_storylines_schema.sql`, `output/site/storylines/`, `stub_data/threads.json`, `docs/plans/2026-04-25-sprint-10-storyline-threads.md`, `output/sprint_reports/sprint-10-storyline-threads.md`

**Modified (merge zone):** `src/cfb_rankings/cli.py` — two subparsers + handler dispatch in alphabetical positions ~line 794 and ~line 816. Other concurrent sprints (11/12/13) inserting in the same file should land in their own alphabetical positions; manual merge is trivial.

**Untouched:** `editions/*`, `team_pages/*`, `wire/*` (Sprint 12), `canon/*`, `receipts/*`, `reporting.py`.
