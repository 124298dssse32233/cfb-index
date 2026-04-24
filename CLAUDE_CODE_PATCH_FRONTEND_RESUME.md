# Claude Code Patch — Frontend Migration Resume

**Use this as a one-shot message in your current Claude Code session** (the one that completed S.0 + S.1 + polish and surfaced the "Figma is missing" problem).

---

```
Two corrections to the frontend kickoff. Both are fixes on me, not on you.

1. Figma reference is NOW in the repo at `figma-reference/player-page/`.
   The earlier kickoff pointed at a session-only path that doesn't exist
   in this repo — that was a bug in the kickoff doc. The folder now
   contains the locked v5 player-page system: Hero, Standing + Variants,
   Room, Signature Story, Current Season Production, Savant (with cohort
   filter), Splits, Peer Comparator, Supporting Cast, Bio/Recruiting/
   Transfer/Roster, plus PlayerPage.tsx assembly, the Subnav primitive,
   and theme.css as token canon. Read `figma-reference/player-page/
   README.md` first — it explains what the folder is FOR and isn't.

2. Revert dark-mode as default. The old production modules are drawn for
   light surfaces; rendering them in dark looks worse than light. Dark
   mode should NOT ship as the default until all 10 modules are ported
   (end of Stage S.5). The dark palette stays defined under a `.dark`
   class in cfb-index.css so it's ready to flip on; Stage S.6 flips it.

   Fix: in reporting.py, remove `class="dark"` from the <html> tag
   rendering. One-line revert. Commit as:
     "frontend: S.1 followup — revert dark default until modules ported"

Then continue with Stage S.2: port Signature Story using
`figma-reference/player-page/src/app/components/SignatureStory.tsx` as
the visual reference and `figma-reference/player-page/src/styles/theme.css`
as the token canon.

Per-module pattern:
- Grep reporting.py for the current render function slug (e.g.
  _render_algorithmic_signature_card, _render_the_room_card). Read a
  tight range around it.
- Open the matching .tsx reference. Don't read the whole tree — read
  just the target component and any primitives it imports.
- Rewrite the Python render function to emit v5-structured HTML, using
  the tokens you added in S.1. Add component CSS under @layer components
  in cfb-index.css.
- For interactive modules (S.4 onward), author the Alpine directives
  inline in the HTML string AND a small companion JS under
  output/site/assets/js/. Register Alpine components via
  `document.addEventListener('alpine:init', ...)`.
- Haiku-subagent verification at the end of each module.
- Commit per module with `frontend: S.N — port {module-name}`.

Stop conditions unchanged. Stop at end of a stage boundary, commit,
summarize, hand back. Don't batch modules across commits.

Resume at TASK S.2.
```

---

## What I did on your side to make this work

1. Copied `/outputs/figma-delivery-stage3b/` (the locked Stage 3 final delivery — full 10 modules + assembly + subnav + URL state + Savant cohort filter) into `figma-reference/player-page/` in the repo.
2. Added a `README.md` in that folder explaining the purpose, what's in scope, what's not, and how to refresh when future Figma iterations land.
3. Updated `CLAUDE_CODE_KICKOFF_FRONTEND.md` to point at `figma-reference/player-page/` instead of the session-only path.
4. Moved the dark-mode-default decision from Stage S.0 (wrong — would regress the look mid-migration) to Stage S.6 (right — all modules ported, visuals ready for dark).

## If Claude Code already committed S.0 + S.1 with dark as default

The revert is small: one `<html class="dark">` → `<html>` in reporting.py. The `.dark { ... }` CSS block stays — it's just not activated yet. That's what the patch message above tells it to do.
