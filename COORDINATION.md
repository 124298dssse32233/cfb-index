# Multi-Window Coordination Log

Both autonomous task windows write here when they're about to touch
files in the other window's scope, or when they encounter merge conflicts.

This file is the single source of truth for "who is doing what right now"
across the parallel-execution model.

---

## Window Ownership

### Window A (original) — owns:
- All sprints in `IMPLEMENTATION_PLAN.md` (v5-2 through v5-12)
- Tech-debt cleanup carried forward from earlier sessions:
  - Pattern C critic tuning for short-form/JSON surfaces (pulse_lede, pulse_themes_writer)
  - `llm_usage_log` dedup via call_id
  - Canon generator LLM rewrite (canon_top10, canon_tail flags currently inert)
  - `today_in_cfb_history` workflow startup_failure
- Existing-plan sprints: v5-6a, v5-6b, v5-7, v5-8, v5-9, v5-10a/b/c/d, v5-11, v5-12

### Window B (new) — owns:
- All sprints in `IMPLEMENTATION_PLAN_v2_addendum.md`
- Specifically:
  - Sprint v5-5.4 (mockup sprint — 7 HTML mockups)
  - Sprint v5-5.5 (foundational decisions documentation)
  - Sprint v5-6a.5 (receipt pattern foundation)
  - Sprint v5-7.5 (hero findings + sample-size system)
  - Sprint v5-7.6 (mobile Saturday Strip + bottom nav + auto-summary)
  - Sprint v5-8.5 (rituals + cultural identity surfacing on team pages)
  - Sprint v5-10e (viral content engine — Monday Mood Map, Daily Belief Movers, etc.)
  - Sprint v5-11.5 (dark mode + Command-K navigation)

---

## Shared files requiring coordination

These files are touched by BOTH windows. Edits MUST be flagged here BEFORE editing.

| File | Window A use | Window B use |
|---|---|---|
| `src/cfb_rankings/quality_loop.py` | extends for Pattern D adversarial in v5-8 | extends for citation_critic role in v5-6a.5 |
| `src/cfb_rankings/llm_runtime.py` | tech-debt cleanup (CostMeter telemetry dedup) | adds citation persistence in v5-6a.5 |
| `profiles/*.md` | reads existing fields | adds `rituals`, `cultural_anchors`, `visual_identity_anchors`, `data_emphasis` frontmatter in v5-8.5 |
| `docs/design-system/00-tokens.md` | reads existing typography | adds display font + tabular numerals + new tokens in v5-5.5 |
| `docs/design-system/*.md` (numbered 30+) | none | creates 30-page-archetypes, 31-chart-vocabulary, 32-receipt-pattern, 33-confidence-signaling in v5-5.5 |
| `.github/workflows/world_class_enrich.yml` | adds new steps for compute pipelines | may add daily hero-finding generator step in v5-7.5 |
| `src/cfb_rankings/cli.py` | adds CLI handlers for existing-plan commands | adds CLI for hero-finding generator, mood-map generator |
| `cfb_rankings.db` migrations | adds migrations for existing-plan needs | adds `editorial_citations` migration in v5-6a.5 |

---

## Conflict resolution protocol

### When a window is about to touch a shared file
1. **Append a coordination entry below** with: ISO date | window | will-touch | file | brief reason
2. **Wait 5 minutes** for the other window to flag a conflict (in practice, the other window is also writing here)
3. **If no conflict, proceed.** Update the entry with `| done` when finished.

### When a conflict is detected (other window's coordination entry overlaps yours)
1. **STOP your edit immediately**
2. **Write a conflict-flag entry** with what you wanted to do
3. **Wait for human resolution.** Do not proceed.

### When you encounter a merge conflict at PR time
1. **Don't try to auto-resolve** — your context may not have the other window's intent
2. **Write a merge-conflict entry** with the file and the conflicting blocks
3. **Wait for human resolution**

---

## Discipline rules (apply to both windows)

These are non-negotiable. They are the reason the previous session work succeeded.

1. **No debugger-agent dispatches at any debugging task.** Manual investigation only. Three failed debugger-agent attempts in the previous session proved this. Use grep + read + run-locally instead.
2. **Live-site verification after every deploy.** Use `curl + grep` against `wonderful-margulis-8ec96b.vercel.app`, or `git show origin/published:<path>` to inspect the deployed HTML. Don't trust "the PR merged" as evidence the site changed correctly.
3. **One task at a time, no parallel agent fan-out.** Each window runs serially; the parallelism is between Window A and Window B, not within either.
4. **Honest SESSION_LOG retrospectives.** Document what landed, what surprised you, what you couldn't fix. "Worked on stuff" is forbidden.
5. **Hard stop at each sprint's acceptance criteria gate.** Don't auto-advance to the next sprint without verifying acceptance criteria met.
6. **No fake-fixes.** "Couldn't complete in window — root cause hypothesis: X, next-step proposal: Y" is the correct shape when blocked.

---

## Active coordination entries

(format: ISO timestamp | window | action | file | reason | status)

2026-05-16T22:30:00Z | meta | initial-setup | this file | establishing coordination model | done

<!-- Append new entries below. Most-recent at bottom. -->
