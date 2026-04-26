# Claude Code — Autonomy + Token Discipline Contract

> Every Claude Code prompt in this product inherits these rules. Each prompt links to this contract at top. The contract is the baseline; prompt-specific rules layer on top.

> **Two superseding rules** (override anything below or in any individual sprint prompt that contradicts these):
>
> 1. **A sprint never stops because token usage hit a budget number.** Token budgets are *targets for efficiency*, not stop conditions. If a sprint runs over budget, it continues to completion and flags the overage in the final report. Kevin trusts the sprint to run; running out of budget is a planning issue to learn from, not an execution issue to halt for.
> 2. **The only hard stop conditions are the four below in §"The 'stop and flag' cases" — none of them are token-related.**

## Autonomy contract

Kevin runs Claude Code sessions while away from the computer for 6–10 hours at a time. The expectation is **complete autonomous execution** of the assigned sprint, no approval-seeking, no waiting.

### Hard rules

1. **Never stop to ask for approval on judgment calls.** Make the call, document it in the report, proceed.
2. **Never wait for user input.** If a sub-task requires a decision, make the decision based on the design briefs + this contract + prior sprint reports, document it, proceed.
3. **The only acceptable stop conditions are four (token budget is NOT one):**
   - File conflict with a concurrent sprint (see concurrency-safety section)
   - Schema/contract mismatch where wrong choice has irreversible downstream cost
   - Security issue (e.g., would expose API keys, allow injection)
   - Hard data unavailability with no graceful fallback (truly nothing to work with)

   Validation gate dropout >50% is a quality alarm — flag in report, continue with what passes (NOT a stop condition). Token usage is never a stop condition.
4. **Document every judgment call in the final report.** Include: what decision, what alternatives considered, why this one. The report is the audit trail.
5. **If unclear between two acceptable approaches, pick the one with less downstream change risk.** Reversibility beats elegance.
6. **Never block on "should I bother Kevin about this?"** — the answer is always no during autonomous runs. Document and proceed.

### What "autonomous" means in practice

- The prompt names what to ship. Claude Code ships it.
- The design briefs (Chronicle Editorial Brief, Pulse Redesign Brief, Editorial Positioning, etc.) are the spec. Read them; follow them.
- When briefs conflict with each other (rare but possible), the more recent doc wins. Document the conflict resolution choice.
- When briefs are silent on a detail, default to: (a) what the existing rendered output does, (b) what feels editorially congruent with the rest of the product, (c) Sonnet's best judgment.
- Run end-to-end. Render. Verify. Re-render if needed. Report. Done.

## Token discipline contract

Token efficiency is non-negotiable. Kevin pays for tokens through the Claude Max subscription; minimizing usage means more sprints fit in a budget cycle.

### Model routing — what each model does

**Use Haiku for:**
- File system searches (grep, glob, find)
- Bulk regex matching
- Simple text validation (banned-phrase checks, format checks)
- Candidate scoring (mention counts, oddity scores, percentile lookups)
- Theme extraction first-pass (TF-IDF clustering, topic naming)
- Sentiment classification at scale
- Validation gates (4-check Stage-4 verification from Chronicle Brief)
- Bulk renames, refactors, simple find-and-replace
- Simple data transformations (CSV parsing, JSON shaping)
- Subagent verification passes after Sonnet/Opus generation
- Fan-voice copy validator (the BANNED_PHRASES check)

**Use Sonnet (default) for:**
- All code-writing
- Standard editorial copy generation (most Chronicle cards, most Pulse themes, most Daily takes)
- Ranking + selection logic (picking top N from candidates)
- Integration glue (wiring data providers to templates)
- Migration writing
- CLI subcommand implementation
- Test writing
- Refactoring within a single module
- API integration code
- Schema migration logic
- Most theme writing in Pulse

**Use Opus ONLY for:**
- Voice-register-defining editorial copy
  - Blue-blood program profile authoring (Alabama, Ohio State, Georgia, Michigan, Texas, USC, Notre Dame)
  - Conference voice profile authoring (SEC, Big Ten — top-volume conferences only; smaller conferences get Sonnet)
  - Cover essay writing (the longform Edition piece — when it's the kind that demands editorial-tier voice)
  - The Lede generation for blue-blood programs / SEC + Big Ten conferences
  - Anchor-state narrative templates (post-loss-blowout, post-upset-win, selection-sunday)
  - Hand-authored historical season chapters for marquee programs (the 19 + 40 flagship seasons pattern from sprint 5)
  - "The Long-Shot That Hit" annual canonical list write-ups (highest-stakes editorial, low volume)
- Schema design where wrong choices cascade
  - Database table designs that will hold years of data
  - Voice register specifications that affect every downstream prompt
- Strategic architectural decisions where reversibility cost is high

### The 15% Opus target (efficiency aspiration, not a halt rule)

In any sprint, **aim for** Opus token usage under 15% of total spend. Track it. If approaching 15%, escalate fewer items to Opus.

If Opus ends up >15%, the sprint completes anyway — the report flags the overage as a sprint-architecture learning ("this sprint mis-scoped Opus reservation; next iteration of this prompt should route X to Sonnet"). The rule is about **efficiency discipline**, not about stopping execution.

The same applies to total token budget. Targets are targets. Sprints run to completion regardless.

### When in doubt, default down

- Unclear between Haiku and Sonnet? → Haiku
- Unclear between Sonnet and Opus? → Sonnet
- Quality concerns at Sonnet level? → expand the Sonnet prompt with more context before escalating to Opus

### Other token discipline tactics

- Read large files with offset+limit, not whole-file reads. `reporting.py` is 17.5k lines — never read whole.
- Use `grep` to find call sites before reading.
- Cache LLM calls where deterministic. Never re-call for the same input within a sprint.
- Batch similar calls (e.g., classify 50 sentiments in one Haiku call, not 50 calls).
- Use subagents (the Agent tool) for read-heavy operations that don't need to ship code — the subagent's context isolation keeps the main agent's context clean.

## Concurrency-safety contract

Kevin will run multiple Claude Code sessions concurrently. Sprints must not collide on file edits.

### File ownership per sprint

Each sprint owns a clearly-defined set of files. The prompt for each sprint lists:
- Files this sprint creates (new modules)
- Files this sprint extends (existing modules)
- Files this sprint touches superficially (e.g., one line in `cli.py`)
- Files this sprint absolutely must not touch (everything else)

If a concurrent sprint needs to touch a shared file (cli.py, migrations/, etc.), it does so at a documented "merge zone" — a stable insertion point with comment markers — so manual merge is trivial.

### Coordination via DB schema, not in-memory state

Sprints communicate through the database, not through global Python state. If sprint A needs sprint B's data, it reads from a table sprint B writes to. No shared in-memory caches that require both sprints to know about each other.

### Branch strategy

Each concurrent sprint runs in its own git branch:
- `sprint/8-pulse`
- `sprint/9-edition`
- `sprint/10-threads`
- etc.

When a sprint completes:
1. Rebase against master
2. Resolve any documented merge zones (cli.py insertion, migration ordering)
3. Open PR
4. Merge

Manual merge resolution is acceptable for documented merge zones. Don't auto-merge on conflicts.

### What never gets touched concurrently

- `reporting.py` outside the documented `PROFILED_SLUGS` guard hook and the homepage rendering hook (per CLAUDE.md). Surgical edits only; coordinate sequentially.
- Migrations in the same numerical range. Each sprint adds migrations with sprint-prefixed numbers (e.g., `20260425_08_pulse_*.sql`, `20260425_09_editions_*.sql`).
- The `profiles/` directory is read-only during execution; profile authoring sprints should be sequential, not concurrent.

## Self-verification contract

Every sprint includes self-verification phases. The verification:

1. Renders to disk (not just generates in memory)
2. Greps the rendered output for banned phrases (the voice validator's job)
3. Greps the rendered output for the new patterns (positive verification)
4. Spot-checks 3+ entities (e.g., 3 programs of different tiers, 3 conferences of different sizes)
5. Captures a representative screenshot if visual changes shipped
6. Reports validation pass rate, dropout rate, banned-phrase frequency

If self-verification fails, the sprint reports the failure and proposes the fix; it doesn't try to keep generating until it passes (that's the wrong loop).

## The reporting contract

Every sprint reports back with:

1. **Phases completed** — one paragraph per phase with status
2. **Judgment calls made** — every non-trivial decision documented
3. **Token usage** by model (Haiku/Sonnet/Opus). Validate Opus < 15% of total.
4. **Verification results** — pass rates, dropout rates, validation report
5. **Files touched** — every file modified, with one-line description per
6. **Concurrency notes** — if a merge zone was used or a conflict was avoided
7. **Visual diff** when applicable (screenshot before/after)
8. **Quality concerns observed** — anything noted while running that wasn't part of the sprint scope but might matter later
9. **Natural next** — what sprint would naturally follow

Reports go to disk in `output/sprint_reports/<sprint_id>.md`. Kevin reviews when convenient.

## The "stop and flag" cases — listed once, never elaborated

The only cases where a sprint pauses and waits for Kevin:

1. File conflict with a concurrent sprint (manual merge needed)
2. Schema mismatch where wrong choice has unrecoverable downstream cost
3. Security issue (API key exposure, injection vulnerability)
4. Hard data unavailability with no graceful fallback

**Token usage is never a stop condition.** Budget targets are efficiency aspirations; sprints run to completion regardless.

Anything else: decide, document, proceed.
