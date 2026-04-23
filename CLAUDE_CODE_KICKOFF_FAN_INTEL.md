# Claude Code Kickoff — Fan Intelligence System

**How to use this file**: open a fresh Claude Code session in this repo and paste the block below as your first message. Claude Code will read the docs, pick the starting task, and begin shipping.

---

```
You are shipping the CFB Fan Intelligence multi-platform collection system for
the CFB Index product. This is a multi-week build. You will work through tasks
one at a time, commit per task, and log progress so context can reset cleanly
between tasks.

## Read first, in this order
1. CLAUDE.md
2. FAN_INTEL_SOURCE_STRATEGY.md   (canonical reference — sources, cohorts, schema, provenance)
3. FAN_INTEL_BUILD_PLAN.md        (8-week task list with model routing)

Do NOT read src/cfb_rankings/reporting.py whole. It's 17.5k lines. Use
offset+limit reads, or Grep. Same for any other file over ~2k lines.

## Model routing — enforce this every task
- Opus:   schema design, cohort-weight decisions, architectural choices,
          cross-cutting copy (methodology page, public-facing labels),
          auditing Sonnet output.
- Sonnet: default. Implementing a specified feature, one adapter, tests,
          editorial drafts. The workhorse.
- Haiku (via subagent): grep sweeps, file listings, renames, format checks,
          diff reviews, scrape_health canaries, single-field validation.

If a task spans both design and implementation, split it: Opus for design in
one commit, Sonnet for implementation in the next. Do not let Opus ship what
Sonnet can ship well, and do not let Sonnet verify what a Haiku subagent can
verify.

When you need a verification step, launch a Haiku subagent via the Task tool
with a tight prompt — do not do verification work in your own context.

## Token discipline
- Large files (reporting.py, fan_intelligence.py): Grep first, Read by range.
- Multi-file audits: Task subagent, not in-context reading.
- At ~60% context full: stop at the next natural boundary, commit, summarize
  for Kevin, and hand back so he can /clear.
- Each task ends with a fresh commit and a 3-line log entry in SESSION_LOG.md
  so a /clear between tasks is safe.

## Repo conventions
- New source adapters:  src/cfb_rankings/ingest/sources/{source_id}.py
- Board adapters:       src/cfb_rankings/ingest/sources/boards/{name}.py
- Cohort logic:         src/cfb_rankings/cohorts/
- Provenance helpers:   src/cfb_rankings/provenance/
- Cowork playbooks:     docs/cowork_playbooks/{name}.md
- Schema migrations:    migrations/YYYYMMDD_NN_description.sql
- Seed files:           seeds/{name}.yaml
- Tests colocated with code: test_{module}.py
- CLI subcommands:      added to src/cfb_rankings/cli.py
- Secrets: env vars only. .env is gitignored. GitHub Secrets for Actions.

Never edit output/site/**. Never hand-edit cfb_rankings.db — write a CLI
subcommand in cli.py and invoke it.

## Per-task protocol (every task follows this)
1. Announce: "Starting TASK N.M — {name}. Model: {Opus|Sonnet}."
2. Read only what Token Tips in the build plan allow.
3. Implement the task.
4. If the task's Verification line calls for it, spawn a Haiku subagent to
   verify (diff review, test run, grep check, row-count query).
5. git commit -m "fanintel: TASK N.M — {short summary}"
6. Append one line to SESSION_LOG.md:
   YYYY-MM-DD | TASK N.M | {one-line outcome} | {any follow-ups}
7. Check the box next to that task in FAN_INTEL_BUILD_PLAN.md.
8. Look up the next task. Continue, or stop at the stop conditions below.

## When to stop and hand back to Kevin
- End of each week (Week 1 boundary, Week 2 boundary, …).
- Any change that would affect published numbers or the methodology page.
- Three failures in a row on the same adapter — hand back with diagnosis.
- Context above 60% full.
- You hit a decision not covered by the strategy doc (see "When to ask me").

## When to ask Kevin (one AskUserQuestion call, not a narrative)
- Any schema change not already specified in STRATEGY §5.
- Adding, removing, or adjusting a cohort weight.
- Adding a source that isn't in STRATEGY §3.
- Any edit to reporting.py beyond a surgical change at a known line.
- Anything that could break ./publish_site.ps1.

For routine ambiguity (naming, test structure, log format): pick the obvious
convention and proceed; flag it in SESSION_LOG.md so it can be revisited.

## Verification is non-optional
Every task ends with verification evidence — a test run, a schema check, a
row-count query, or a Haiku subagent diff review. No "I'm done" without
evidence attached.

## Begin
Start with TASK 1.1 in FAN_INTEL_BUILD_PLAN.md (schema additions, Opus).
Produce the migration SQL, apply it locally, confirm the existing
`python manage.py build-site` still runs. Commit. Log. Move to TASK 1.2.

If SESSION_LOG.md doesn't exist yet, create it with a one-line header
"# Fan Intelligence Build — Session Log" and start appending.
```

---

## Operator notes (not part of the paste-in)

**When to paste this prompt**: at the start of a build session, whether Week 1 Day 1 or Week 5 Day 3. Claude Code reads the plan, finds the next unchecked task, and resumes.

**Between sessions**: `/clear` is safe as long as `SESSION_LOG.md` has been updated and the current task was committed. The prompt is designed so resuming from a cleared context is identical to starting fresh — everything Claude Code needs to know is in the docs.

**If a task goes wrong**: the 3-line log entries make it easy to bisect which commit broke what. Ask Claude Code to revert or fix by citing the `TASK N.M` ID; it'll know where to look.

**Weekly rhythm Kevin runs**:
- Monday: ship 2–3 tasks (2–4 hrs).
- Midweek: a quick session if context is fresh.
- Friday: end-of-week checkpoint — confirm week's tasks boxed, `scrape-health` clean, push.

**When a source adapter breaks** (eventually every adapter does): open a fresh session, paste the prompt, say "TASK: diagnose and fix adapter `{source_id}`. Check `scrape_health` for the failure pattern. Use a Haiku subagent to diff against the last working commit." The prompt's model-routing and conventions apply to maintenance work too.

**Cost control**: Opus tasks are gated to ~15 across 8 weeks (schema, cohort weights, firehose architecture, graph sampler, aggregator, divergence, methodology page, audit). Sonnet does the ~60 adapter/test/playbook tasks. Haiku subagents do the ~80+ verifications. This routing keeps the Claude Max spend efficient without sacrificing quality on the decisions that matter.
