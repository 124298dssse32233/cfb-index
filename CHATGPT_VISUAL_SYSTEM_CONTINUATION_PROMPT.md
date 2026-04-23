# Claude Prompt — Continue the CFB Index Visual System (Step-by-Step ChatGPT Production)

**Paste everything below the horizontal rule into a new Claude / Claude Code task window.**

---

## Context for Claude

I'm Kevin. I run The CFB Index — a weekly editorial-style college football rankings + fan-intelligence product. Static site, Python generator → SQLite → ~17k HTML pages. Workspace: `C:\Users\kevin\Downloads\Sports Website\`.

You're picking up an in-flight visual-system design project. Four docs in the workspace are the full context — read them in this order before doing anything else:

1. **`CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md`** — the strategic concept. Three illustration families (risograph covers + ligne-claire totems + halftone portraits), 4-tier asset taxonomy, 18 archetype totems with specific object proposals, 12 rivalry coins, the 90-day plan.
2. **`CFB_INDEX_IDENTITY_PRODUCTION_PLAYBOOK.md`** — the how-to. 10 editorial-identity rules distilled from The New Yorker, Businessweek, The Economist, WSJ, Monocle. 7 ready-to-paste ChatGPT/Midjourney prompt templates. Direct-API strategy for team assets (CFBD + ESPN CDN). Cost model, failure modes, 6 decisions I still owe.
3. **`FAN_INTEL_HUB_V4_A_PLUS_REVIEW.md`** — the design context the visual system is feeding into.
4. **`CLAUDE.md`** in the workspace root — codebase ground rules.

Don't read `reporting.py` whole — it's 17.5k lines. Use offset+limit or grep when you need to look at it.

## What I want from this task

I want to *actually start producing assets*. The concept and playbook are complete; now I need the executable, day-by-day ChatGPT workflow that gets the first tier of the visual system shipped. Your output is a **step-by-step ChatGPT production runbook** that I can follow over the next 7-14 days to produce, at minimum:

- The three master style plates (one ligne-claire totem, one halftone portrait, one risograph cover sample).
- All 18 archetype totems.
- The 8 modifier glyphs.
- The section rubric icon set (24 icons).

Do not write code, generate images, or send anything to external APIs. This task is pure planning + runbook authoring. I'll execute in ChatGPT myself and come back with the results.

## Deliverables

Create **one file** in the workspace root: `CHATGPT_VISUAL_SYSTEM_RUNBOOK.md`. It must contain, in order:

### Section 1 — Pre-flight checklist
What I need to have set up before I start. Specifically:
- ChatGPT Plus/Pro subscription confirmation (do I need it? which tier?).
- The Custom GPT to create ("CFB Index Art Director") with the exact system prompt I should paste into its configuration — literal paste-ready text, not a description.
- The reference files I need to upload into that Custom GPT's knowledge base.
- Folder structure to create locally for organizing outputs (`assets/masters/`, `assets/totems/`, `assets/rejected/totems/`, etc.).
- Naming convention for final files and the `.prompt.md` sidecar format.

### Section 2 — Day-by-day runbook, 14 days
Literal day-numbered schedule with a clear objective per day, expected time commitment (30 min / 2 hrs / half day), and a concrete pass/fail definition for "this day is done."

Days 1-3: lock the three master plates.
Days 4-8: ship 18 archetype totems (~4/day).
Days 9-10: ship the 8 modifier glyphs.
Days 11-13: ship 24 section rubric icons.
Day 14: full-grid review and rejection pass; update the style bible based on what I learned.

For each day, give me:
- The exact goal.
- The specific brief(s) to work on.
- The literal prompt(s) to paste into ChatGPT (not templates — the full prompt I paste, with placeholders filled in for *this* specific asset).
- What success looks like (visual criteria; what to reject).
- Where to save the winner and what to write in the sidecar.
- What to do if ChatGPT is being stubborn (specific re-prompt tactics).

### Section 3 — The 18 totem briefs, each as a paste-ready ChatGPT prompt
One sub-section per archetype with the exact prompt filled in. Examples (finalize all 18):
- Anxious Dynasty → crumbling stone crown
- Perpetual Believer → weathered NEXT YEAR pennant
- Wounded Giant → toppled statue with ivy
- ...and 15 more from the concept doc.

Each is a paste-ready prompt, not a template. I should be able to open ChatGPT, paste the prompt, receive 4 candidates, pick one, and move on.

### Section 4 — The re-prompting playbook
ChatGPT will sometimes return things that are wrong in specific ways. Give me a table of failure modes → the exact follow-up prompt that fixes each. Examples: "rendering is too smooth/glossy" → "Regenerate with heavier paper texture, visible fiber grain, no digital shine, hand-inked quality." etc. Cover at minimum: glossy/rendered look; centered/symmetric composition; missing amber accent; wrong line weight; text showing up where it shouldn't; "sports mascot cartoon" default; real-person likenesses appearing.

### Section 5 — Curation & rejection protocol
Step-by-step for reviewing 4 candidates and picking one. What to compare them against. When to regenerate vs. accept. What to write in a `.reject.md` note for the rejected candidates. How to batch-review at end of day.

### Section 6 — Batching and efficiency tips for ChatGPT specifically
How to speed-run this in ChatGPT without losing quality. Tab management, conversation management (when to start a fresh conversation vs. continue), gen_id references, the "generate variations of #2" workflow, uploading multiple references at once, when to switch to API batch mode.

### Section 7 — Hand-off to the weekly issue workflow
After the 14 days, what does the recurring per-issue production look like for covers + commiseration cartoons? Short — a 1-page operating rhythm.

## Constraints

- Do not invent archetype content. Use the 18 primary archetypes already specified in `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md` § asset taxonomy Tier 1 and in `CFB_INDEX_IDENTITY_PRODUCTION_PLAYBOOK.md` Part 3 Template B.
- Do not rewrite the style bible or the concept — reference them, don't duplicate them. The runbook should *execute* the plan, not repeat it.
- Every prompt in Section 3 must open with the locked style prefix block from the playbook. Consistency matters.
- Never suggest generating team logos, helmets, conference marks, or real-person faces via AI. That rule is absolute — use CFBD + ESPN CDN per Part 4 of the playbook.
- Target length: concrete runbook, no filler. Probably 2500-4500 words depending on how tight you can write.

## Model + approach

Use whatever combination of direct work and sub-agents makes sense. For the 18 totem prompts in Section 3, consider delegating to a subagent with the concept doc's archetype list and the playbook's prompt template to bang them out in parallel — then you integrate. For the day-by-day scheduling, do it yourself.

Ask me clarifying questions before writing the runbook *only* if something in the two source docs is ambiguous or contradictory. Otherwise proceed.

When you're done, drop me a computer:// link and a 3-sentence summary. I'll execute in ChatGPT and come back with the first batch of candidates for review.

---

*(end of prompt to paste)*
