# Claude Code — The Mailbag (Sprint 16)

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session. Concurrency-safe with Sprint 14 (Daily) and Sprint 15 (Reaction) — disjoint module trees.

**Recommended model: Sonnet 4.6.**

**Target budget: ~50k tokens. Runtime: 1.5–2 hours.**

**Branch:** `sprint/16-mailbag` (branch from current `master`).

**File ownership:**
- Create: `src/cfb_rankings/mailbag/` (new module: `__init__.py`, `submissions.py`, `curator.py`, `synthesizer.py`, `renderer.py`, `data.py`, `templates/mailbag.html.j2`, `templates/submit.html.j2`)
- Create: `migrations/20260426_16_mailbag.sql` — schema for `mailbag_submissions` + `mailbag_editions` + `mailbag_answers`
- Extend: `src/cfb_rankings/cli.py` at the documented merge zone (sprint 16 marker block) — register `mailbag-curate-submissions`, `mailbag-generate-answers`, `render-mailbag`, `mailbag-history`, `mailbag-seed-submissions`
- Read-only: every other sprint's module

---

## What this sprint ships

The Mailbag — a Friday 09:00 ET publication that answers 3–5 curated fan submissions per week. Each answer is **corpus synthesis**, not opinion: the answer pulls cited evidence from Wire, Threads, Pulse, Receipts, and named sources to build a fan-voice response.

The editorial product is **the synthesis** — not "what The Mailbag thinks" but "here's what the totality of CFB conversation says about your question, with sources."

Lives at `/mailbag/index.html` (current) + `/mailbag/YYYY-w{NN}/index.html` (archive). Submission form at `/mailbag/submit/index.html`.

---

## Phase 1 — Schema (~3k tokens)

`migrations/20260426_16_mailbag.sql`:

```sql
-- Sprint 16: The Mailbag — fan submission editorial

CREATE TABLE IF NOT EXISTS mailbag_submissions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  submitted_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
  submitter_email TEXT,                              -- nullable; we store if provided
  submitter_handle TEXT,                              -- "Andrew from Knoxville" — what we publish
  question_text   TEXT NOT NULL,
  topic_tags_json TEXT,                              -- ["realignment","sec","alabama"]
  status          TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','curated','answered','rejected','archived')),
  curator_notes   TEXT,
  rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS mailbag_editions (
  edition_slug    TEXT NOT NULL PRIMARY KEY,         -- '2026-w17' (Friday-anchored)
  publish_date    TEXT NOT NULL,                     -- 'YYYY-MM-DD'
  status          TEXT NOT NULL CHECK(status IN ('draft','published','retired')),
  generated_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
  notes           TEXT
);

CREATE TABLE IF NOT EXISTS mailbag_answers (
  edition_slug    TEXT NOT NULL,
  rank_position   INTEGER NOT NULL,                  -- 1..5
  submission_id   INTEGER NOT NULL,
  answer_body     TEXT NOT NULL,
  cited_sources_json TEXT NOT NULL,
  source_count    INTEGER NOT NULL,
  primary_topic   TEXT,
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model TEXT,
  PRIMARY KEY (edition_slug, rank_position),
  FOREIGN KEY (edition_slug) REFERENCES mailbag_editions(edition_slug),
  FOREIGN KEY (submission_id) REFERENCES mailbag_submissions(id)
);

CREATE INDEX IF NOT EXISTS idx_submissions_status
  ON mailbag_submissions(status, submitted_at_utc);
```

---

## Phase 2 — Submission intake (~3k tokens)

`submissions.py` exposes:
- `submit_question(handle, email, question_text)` — server-side function for a future submit form
- `seed_representative_submissions(n)` — for pipeline bootstrapping; flags seeded rows with `submitter_email='editorial-seed@cfbindex.local'` so they're filterable
- `list_queued(limit=50)`

A static submission form at `/mailbag/submit/index.html` is rendered. It's **non-functional this sprint** — the form action is `mailto:mailbag@cfbindex.local` for now. Document this; future sprint wires Resend/Postmark.

---

## Phase 3 — Curator (Haiku, ~3k tokens)

`curator.py` exposes `curate_for_edition(edition_slug, max=5)`:

Selects 3–5 submissions from the queue ranked by:
- Topic freshness (recent Wire/Thread activity on the topic)
- Cohort breadth (does the answer have material for stat folks AND casual fans AND die-hards?)
- Question quality (Haiku scores: specific > vague, original > duplicate-of-recent, narrative > yes-no)
- Variety (no two questions on the same primary entity)

For each picked submission, sets `status='curated'`. Rejected questions get `status='rejected'` with a curator note.

**Bootstrap path**: if fewer than 3 real submissions exist, `seed_representative_submissions` plants 3–5 representative questions covering current calendar moments (transfer portal late activity, spring practice notes, NFL draft fallout, summer-camp speculation). Document seed rows clearly so future cycles replace them with real submissions.

---

## Phase 4 — Answer synthesis (Sonnet, ~30k tokens)

`synthesizer.py` calls `llm_runtime.run_with_voice_validator()` per submission:

```
You are answering a fan question for The Mailbag (Friday 09:00 ET edition {edition_slug}).

The question is from {submitter_handle}: "{question_text}"

Your job is SYNTHESIS, not opinion. Pull cited evidence from:
- Wire entries on related entities ({wire_excerpts})
- Storyline thread chapters ({thread_chapter_excerpts})
- Pulse data on related entities ({pulse_data})
- Aged-well receipts ({related_receipts})
- Named sources from the corpus ({source_quotes})

Voice: warm-fan-positioned. Never aloof-magazine. Acknowledges CFB's absurdity. Treats the questioner like a friend who reads closely and wants the synthesis.

Required:
- 250–400 words
- Cite ≥3 named sources verbatim with attribution
- End with: "Short answer:" — a one-line distilled take after the full synthesis
- Don't pretend to know unknowables — flag uncertainty where warranted
- No banned phrases
- Open with the question hook, not the setup
```

**Model routing**: Sonnet by default. Opus ONLY on questions tagged with `civic_significance` (existential sport-shape questions like "what does the 12-team CFP do to regional identity?", "is realignment killing the rivalry?"). Cap Opus < 15% of total spend.

**Voice validator gate**: same retry-once pattern as Daily/Reaction.

---

## Phase 5 — Renderer (~8k tokens)

Writes:
- `output/site/mailbag/index.html` — current edition (most recent published Friday)
- `output/site/mailbag/{edition_slug}/index.html` — archive
- `output/site/mailbag/submit/index.html` — submission form (mailto-based for now)
- `output/site/mailbag/archive.html` — last 30 editions list

Layout (edition page):
- Masthead: "The Mailbag — {edition_slug} — published Friday {date}"
- Each answer: question quote (display serif italic, attributed to handle) → answer body → "Short answer:" pill → source pills
- Footer: "Have a question? → /mailbag/submit/"
- Sidebar (desktop): "Recent editions" → links to last 5

Submission form: simple input fields — handle, email (optional), question. `<form action="mailto:mailbag@cfbindex.local">` for now.

Uses existing Edition typographic system. No new design tokens.

---

## Phase 6 — CLI subcommands (~2k tokens)

Register at sprint 16 merge zone:
- `mailbag-seed-submissions [--n N]` — bootstrap-only seeder
- `mailbag-curate-submissions [--max N] [--edition SLUG]` — runs Phase 3
- `mailbag-generate-answers [--edition SLUG]` — runs Phase 4 against curated submissions
- `render-mailbag [--edition SLUG]` — renders edition or all
- `mailbag-history [--limit N]` — prints recent editions

---

## Phase 7 — GitHub Actions workflow (~2k tokens)

Create `.github/workflows/mailbag-friday-09am-et.yml`:

```yaml
name: Mailbag — Friday 09:00 ET

on:
  schedule:
    - cron: '0 13 * * 5'  # 09:00 ET Friday = 13:00 UTC
  workflow_dispatch: {}

jobs:
  publish:
    if: false  # GUARD — disabled until first-live-cycle verification flips this
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e .
      - run: |
          EDITION=$(python -c "from datetime import date; d=date.today(); w=d.isocalendar().week; print(f'{d.year}-w{w:02d}')")
          python manage.py mailbag-curate-submissions --edition $EDITION
          python manage.py mailbag-generate-answers --edition $EDITION
          python manage.py render-mailbag --edition $EDITION
          python manage.py build-site
        env: { ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }} }
      - run: |
          git config user.name "mailbag-cron"
          git config user.email "mailbag-cron@cfbindex.local"
          git add output/site/mailbag/
          git diff --cached --quiet || git commit -m "mailbag: $(date -u +%Y-w%V)"
          git push origin master
```

Same `if: false` guard — dormant until first-live-cycle flips it.

---

## Phase 8 — Backfill 1 representative edition (~3k tokens)

Seed 5 representative submissions, curate 3, generate answers, render. Confirms the full pipeline.

```
python manage.py mailbag-seed-submissions --n 5
python manage.py mailbag-curate-submissions --edition 2026-w17 --max 3
python manage.py mailbag-generate-answers --edition 2026-w17
python manage.py render-mailbag --edition 2026-w17
```

---

## Phase 9 — Self-verification

- Edition `2026-w17` renders cleanly
- All 3 answers pass voice validator
- Each answer cites ≥3 named sources
- Submission form page renders (even though non-functional)
- Archive index lists the edition

---

## Phase 10 — Sprint report (~1k tokens)

`output/sprint_reports/sprint-16-mailbag.md`:
1. Phases completed
2. Token usage by model (Opus < 15%)
3. Backfilled edition with question + answer headlines
4. Workflow YAML path + guard status
5. Files touched
6. Open follow-up: real submission form needs email infra (Resend/Postmark) — track as future sprint
7. Quality concerns
8. Natural next: first-live-cycle verification flips the cron guard; future sprint wires real submission ingestion

Commit + push to `sprint/16-mailbag`. Open PR.

---

## Decision authority

Autonomous on: curator scoring weights, seed submission topics, edition slug format ('YYYY-wNN' Friday-anchored ISO week), archive limit, retry semantics, GitHub Actions cron timezone, "Short answer:" formatting.

Stop and flag only on the four canonical hard-blocker conditions.

---

## Report back with

1. Phase 1–10 completion status
2. Backfilled edition with question/answer summaries
3. Voice validator pass rate
4. Token usage by model
5. Files touched
6. PR URL
7. Email-infra follow-up flag
8. Quality concerns

Session complete after PR opens.
