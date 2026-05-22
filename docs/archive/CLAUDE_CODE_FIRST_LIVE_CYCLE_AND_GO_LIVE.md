# Claude Code — First Live Cycle + Go Live

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session on `master` branch (after Wave 3 has merged to master). Verifies the full live-publishing pipeline end-to-end, then flips the 4 GitHub Actions cron workflows from disabled to enabled.

**Recommended model: Sonnet 4.6.**

**Target budget: ~50k tokens. Runtime: 1.5–2.5 hours.**

**Branch:** `master`. No new branch needed — this is verification + a small workflow-config commit.

**File ownership:**
- Read-only: every module's CLI subcommand
- Edit: 4 GitHub Actions workflow YAMLs in `.github/workflows/`
- Write: `output/sprint_reports/first-live-cycle.md`

---

## Why this sprint

Wave 3 + Wave 1+2 + Sprint 8.5 are all on master. The product is technically complete. But every prior sprint's content was generated in batch backfills during sprint runs. Going forward, the product needs to publish on schedule via crons.

This sprint is the **moment of truth** — the first live cycle that exercises every surface end-to-end. If quality holds, we flip the crons on and the product becomes auto-publishing. If quality slips, we document, tune, and try again.

---

## Phase 1 — Manual first live cycle (60-90 min, ~40k tokens)

Run each surface's live publication pipeline IN ORDER. Each command exercises real LLM calls (via `llm_runtime`) producing fresh editorial content.

### 1.1 Wire — ingest yesterday's transactions

```
python manage.py wire-ingest --hours 24
python manage.py wire-generate-editorial --hours 24
```

Should ingest any new portal entries / coaching news / signing-day events from CFBD's last 24h + generate editorial captions (`why_it_matters` + `historical_comp`) for each. Voice validator gates each caption.

If ingest returns zero new entries (slow day), that's fine — just note it.

### 1.2 Pulse refresh — recompute this week's mood + themes for the live entities

```
python manage.py compute-conference-pulse --week=current
python manage.py render-conferences-pulse --all
python manage.py render-team-pages --slug alabama,ohio-state,georgia,michigan,texas,usc,notre-dame,penn-state,tennessee,auburn
python manage.py render-the-room --top 15
```

Refreshes Pulse data for top entities with this week's freshly-classified sentiment + new theme extraction.

### 1.3 The Daily — generate today's morning digest

```
python manage.py generate-daily
python manage.py render-daily
```

Should synthesize last 24h of Wire + active Threads + Pulse spikes + Receipt resolutions into 3 takes. Voice validator gates each take.

### 1.4 Storyline Thread — generate one fresh chapter

Pick the most active thread (likely "The 12-Team Playoff Settling" or "Realignment Endgame"):

```
python manage.py generate-thread-chapter --thread the-12-team-playoff-settling --auto
python manage.py render-storylines
```

Should produce a new chapter that references prior chapters in the thread, cites ≥3 named sources verbatim, runs through validator.

If `--auto` falls back to draft-scaffold mode (no API key path), document and note the chapter wasn't fully generated. Voice validator should still pass.

### 1.5 The Reaction Story — auto-trigger check

Check the Wire for any high-velocity entries from 1.1 that should have triggered a Reaction Story:

```
python manage.py reactions-check-triggers --hours 24
```

If any triggered, the Reaction Story auto-generates. If nothing triggered (no big news in last 24h), that's fine — Reaction Stories fire on demand, not on schedule.

### 1.6 The Mailbag — curate + answer (only if real submissions exist)

```
python manage.py mailbag-curate-submissions --max 3
```

If real submissions in the queue: continues to:

```
python manage.py mailbag-generate-answers
python manage.py render-mailbag
```

If no real submissions yet (likely on first live cycle), seed 3 representative questions yourself directly to the `mailbag_submissions` table for verification purposes only — mark them with `submitter_email='editorial-test@cfbindex.local'` so they're filterable. Then run the answer + render commands. Document the seed data in the report; we'll either remove it or replace with real submissions on the next cycle.

### 1.7 The Edition — publish next Saturday's edition

```
python manage.py publish-edition --slug $(python -c "from datetime import date, timedelta; today = date.today(); next_sat = today + timedelta((5 - today.weekday()) % 7); week = next_sat.isocalendar().week; print(f'{next_sat.year}-w{week:02d}')")
python manage.py render-edition --slug <the-slug-just-generated>
```

The Edition is the marquee — uses Opus eligible for the cover essay if it's an editorial-tier week (calendar moment, big news week, anniversary, etc.). Otherwise Sonnet. Voice validator gates everything.

This is the longest-running command — possibly 5-15 minutes.

### 1.8 Final build-site

```
python manage.py build-site 2>&1 | tee output/sprint_reports/first-live-cycle-build.log
```

Generates the integrated state from all the live content just produced. Should complete cleanly — if any errors, debug.

---

## Phase 2 — Quality verification (30-45 min, no new tokens)

This phase is human-equivalent eyeball review of the generated content. Apply the Beat-Writer Test from `docs/EDITORIAL_POSITIONING_AND_CONTENT_TYPES.md` §"Voice register."

For each surface, verify the live output reads well. Specifically:

### 2.1 Edition cover essay

Open the just-generated cover essay article page. Read it through. Apply 4-question Beat-Writer Test:
- Does the essay synthesize what the week meant in a way nobody else could?
- Are sources cited by name + verbatim?
- Does the voice carry warmth / fan-knowledge / acknowledgment of CFB's absurdity (per voice register adjustment)?
- Would a sharp blogger forward this to their group chat?

If any answer is "no" — flag in the report. We don't enable GH Actions on this Edition; we tune first.

### 2.2 Daily

Read today's Daily. Check:
- Three takes are real, ranked by what fans actually moved on
- Each take cites ≥2 named sources
- Voice is warm-fan-positioned, not aloof-magazine

### 2.3 Wire entries

Spot-check 5 Wire entries from today. Each `why_it_matters` should be specific, fan-voice, comparative. No banned phrases.

### 2.4 Storyline chapter

Read the freshly-generated chapter. References prior chapters? Cites real sources? Continues the narrative voice consistently?

### 2.5 Mailbag answers (if generated)

Read each answer. Synthesizes corpus rather than opining? Cites named sources? Reads as fan-voice not lecture?

### 2.6 Pulse modules — top 3

Open Notre Dame + Alabama + SEC pages. Verify:
- Lede is fresh + voiced (not deterministic template)
- Themes are real corpus quotes, not stock-phrase fallback
- Sentiment slice renders if sample warrants

### 2.7 Voice validator full sweep

Run the validator across the live-generated HTML:

```python
import glob
from cfb_rankings.team_pages.voice_validator import validate_fan_voice
violations = []
sample_paths = [
    "output/site/index.html",
    "output/site/editions/<just-generated-slug>/cover-essay/index.html",
    "output/site/editions/<just-generated-slug>/feature-iv/index.html",
    "output/site/daily/index.html",
    "output/site/storylines/the-12-team-playoff-settling.html",
    "output/site/teams/notre-dame.html",
    "output/site/teams/alabama.html",
    "output/site/conferences/fbs-sec.html",
    "output/site/wire/index.html",
    "output/site/mailbag/index.html",
]
for p in sample_paths:
    try:
        with open(p, encoding='utf-8') as f:
            text = f.read()
        passed, vs = validate_fan_voice(text, source=p)
        if not passed:
            violations.extend(vs)
    except FileNotFoundError:
        violations.append(f"file missing: {p}")
print(f"Sample violations: {len(violations)}")
for v in violations[:30]:
    print(v)
```

Expected: 0 substantive violations on editorial-content samples (chrome false positives don't count). Document any real banned-phrase leakage — the next iteration's prompt tunes against them.

---

## Phase 3 — Decide: enable or hold (5 min)

Based on Phase 2 findings, make the call:

### Pass — enable the GitHub Actions

If quality holds across all surfaces (Beat-Writer Test passes, voice validator clean on samples, no obvious editorial drift), proceed to Phase 4.

### Hold — document and don't enable yet

If 1+ surface fails quality (cover essay reads aloof / Daily takes are generic / themes have invented quotes / Reaction Story has wrong cohort framing / etc.), STOP. Document in the report:
- Which surface failed
- What specifically was off
- Likely root cause (prompt under-tuned? voice register drift? data thinness?)
- Proposed fix for the next iteration

Leave GH Actions disabled. Kevin reviews + decides next steps. Sprint ends with the report.

---

## Phase 4 — Enable the 4 GitHub Actions cron workflows (10 min)

If Phase 3 passed, edit each workflow YAML to remove the `if: false` guard.

### Workflows to enable

1. `.github/workflows/wire-daily-04am-et.yml` — daily 04:00 ET ingest + editorial generation
2. `.github/workflows/the-daily-06am-et.yml` — weekday 06:00 ET Daily publication
3. `.github/workflows/publish-edition-weekly.yml` — Saturday 06:00 ET Edition publication
4. `.github/workflows/mailbag-friday-09am-et.yml` — Friday 09:00 ET Mailbag publication

For each: locate the line `if: false` (or `if: ${{ false }}` or similar guard) inside the job definition. Remove the line entirely (or change to `if: ${{ github.event_name == 'schedule' || github.event_name == 'workflow_dispatch' }}` if a more nuanced gate is appropriate).

Verify the cron expressions are correct:
- `wire-daily-04am-et`: `0 8 * * *` (04:00 ET = 08:00 UTC, no DST for now)
- `the-daily-06am-et`: `0 10 * * 1-5` (06:00 ET weekdays = 10:00 UTC)
- `publish-edition-weekly`: `0 10 * * 6` (06:00 ET Saturday = 10:00 UTC)
- `mailbag-friday-09am-et`: `0 13 * * 5` (09:00 ET Friday = 13:00 UTC)

Note: these use UTC. Adjust if DST handling matters per Kevin's preference. Document the choice.

### Commit + push

```
git add .github/workflows/wire-daily-04am-et.yml .github/workflows/the-daily-06am-et.yml .github/workflows/publish-edition-weekly.yml .github/workflows/mailbag-friday-09am-et.yml
git commit -m "go live: enable 4 cron workflows after first-live-cycle verification"
git push origin master
```

After push, GitHub will pick up the schedule. The next 04:00/06:00/09:00 ET window starts the auto-publishing.

---

## Phase 5 — First-live-cycle report (15 min)

Write `output/sprint_reports/first-live-cycle.md` with:

1. Cycle summary — which surfaces ran successfully, which had warnings, runtime per command
2. Token usage by surface + by model
3. Voice validator sample sweep — count + any real violations
4. Beat-Writer Test results per surface — pass / hold + specific notes
5. Quality concerns observed — anything worth tuning in the next prompt iteration
6. Workflow enablement status — which 4 enabled, when next runs are scheduled
7. Natural next: monitor first 2-3 weekly cycles, tune as needed

Commit + push the report.

---

## Decision authority

Autonomous on: Edition slug computation logic, mock-submission seed data for the Mailbag if no real submissions exist, voice validator sample path selection, cron expression timezone choices, workflow YAML guard removal mechanics.

Stop and flag only on:
- Phase 2 quality fails on cover essay or Daily (the two tentpole surfaces) — leave GH Actions disabled, document, halt
- Any rendered HTML has obvious banned-phrase leakage (≥3 real violations on editorial samples)
- Any of the 4 workflow YAMLs are structurally broken or have unexpected guard mechanisms
- Build-site fails on the integrated state

---

## Report back with

1. Phase 1 — every command's run + output (success/warning/error per surface)
2. Phase 2 — Beat-Writer Test results per surface (pass / hold + notes)
3. Phase 2 — voice validator sample sweep (count + any real violations)
4. Phase 3 — decision (enable or hold) with rationale
5. Phase 4 — workflow enablement status (which enabled, schedule confirmed)
6. Phase 5 — final report committed + pushed
7. Token usage by surface + model
8. Files touched
9. Quality concerns for next-iteration tuning

When the 4 workflows are enabled and the report is pushed, **the editorial product is live and auto-publishing.** Session complete.
