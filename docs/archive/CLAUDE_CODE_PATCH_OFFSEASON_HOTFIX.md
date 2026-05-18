# Claude Code Patch — Offseason Hotfix (P.0)

**Use this in your current Claude Code session** after the frontend-resume patch has been applied (dark-mode revert complete, S.2 starting). This hotfix is small and independent — it can run in parallel with or before Stage S.2.

**Purpose:** the production player page currently labels completed 2025 stats as "Current Season Production" and treats the Hero's accolade chip in present tense, which reads as if the season is still active. Today's date is April 23, 2026 — mid-offseason. This patch fixes the labeling so readers don't misread the calendar, and promotes Bio / Recruiting / Transfer / Roster up the page to the position offseason readers actually want.

Full strategic context lives in `PLAYER_PAGE_SEASON_PHASE_DESIGN.md`. This hotfix is Stage P.0 of that plan only — the smallest possible reader-visible win. P.1+ (real phase detection, new modules, Figma offseason variants) is separate future work.

---

```
Shipping the offseason hotfix per PLAYER_PAGE_SEASON_PHASE_DESIGN.md §7
Stage P.0. Narrow scope. Mechanical label changes + one small reshuffle +
a hard-coded phase banner. No phase-detection logic, no new modules — those
are P.1 and later.

## Read first
1. PLAYER_PAGE_SEASON_PHASE_DESIGN.md §§ 1, 5, 7, 9 (the parts that matter
   for P.0; skip the detailed module specs in §3 and §4)
2. CLAUDE.md (repo rules)

## Model: Sonnet (pure mechanical edits)

## What to change in reporting.py

Grep to find each render function or heading string before editing.
Use offset+limit reads — do NOT read reporting.py whole.

### Change 1: Phase banner above Hero (new, hard-coded for now)
At the top of the player-page body, above the Hero, emit a single-line
banner:

  <div class="phase-banner" role="note">
    <span class="phase-banner__label">OFFSEASON · SPRING 2026 · DRAFT WEEK</span>
  </div>

Styled via cfb-index.css @layer components:
  - Uses accolade-gold-base for the label color
  - --fs-meta typography, uppercase, 0.08em letter-spacing
  - Subtle divider below (1px border in --muted)
  - Full width, centered text, --space-3 vertical padding

Find the player-page top-of-body render. Grep for Hero's render function
or for "cj-carr" or "player-anchor-section".

### Change 2: Relabel retrospective modules
Grep for these exact strings (case-sensitive) and replace per the table.
If the string appears more than twice across reporting.py (once for the
heading, once for an aria-label), replace all of them.

  "Current Season Production"      → "2025 Season · Final"
  "Current Season"                 → "2025 Season · Final"
  "CURRENT SEASON PRODUCTION"      → "2025 SEASON · FINAL"
  "CURRENT SEASON"                 → "2025 SEASON · FINAL"
  "Signature Story"                → "2025 Signature"  (heading only;
                                      component class name stays as-is)
  "Advanced Savant"                → "2025 Advanced · Final"
  "ADVANCED · WK {N} UPDATE"       → "2025 ADVANCED · FINAL"
  "SPLITS · 2025"                  → "2025 SPLITS · FINAL"
  "Splits"                         → "2025 Splits · Final"  (heading only;
                                      css class + slug stay as-is)

Do NOT rename "The Room on [Player]" — fans are always talking, that
module stays present-tense.

Do NOT rename Peer Comparator, Supporting Cast, Player Standing, or Hero.

### Change 3: Hero accolade chip → retrospective voice
Grep for the accolade-chip render in reporting.py (likely near the Hero
block — look for "HEISMAN" or "FINALIST" in uppercase strings).

Current: emits chip text like "HEISMAN FINALIST" or "ALL-AMERICAN".
New: prefix with "2025 " so it reads "2025 HEISMAN FINALIST",
"2025 ALL-AMERICAN", etc.

ONLY change the uppercase display text. Do not change any underlying
flag or data field.

Edge case: for players without an accolade chip today, no change needed.
The empty branch stays empty.

### Change 4: Promote Bio / Recruiting / Transfer / Roster up the page
Grep for the section ordering in the player-page body render. The 10
modules are currently in order (per FIGMA / Stage 3 design):

  1 hero · 2 standing · 3 room · 4 signature · 5 production ·
  6 savant · 7 splits · 8 peers · 9 cast · 10 bio

For P.0, move bio from position 10 to position 5. New order:

  1 hero · 2 standing · 3 room · 4 signature · 5 bio ·
  6 production · 7 savant · 8 splits · 9 peers · 10 cast

The subnav anchor list in the sticky subnav (once the subnav ports in
S.5) will pick up the new order automatically. For today, if the current
HTML has a section nav list, update its order to match.

## What NOT to do
- Do NOT add phase-detection logic. Banner text is hard-coded as
  "OFFSEASON · SPRING 2026 · DRAFT WEEK" for now. P.1 will make it
  dynamic.
- Do NOT add 2026 Outlook or Development Trajectory modules. Those are
  P.3 and P.5, separate stages.
- Do NOT change The Room, Peer Comparator, Supporting Cast, Player
  Standing, or Hero content. Labels only.
- Do NOT change any database field, SQL, or data-layer code. Pure
  template/rendering edits.
- Do NOT rename any CSS class, data-module attribute, or id. Slugs +
  selectors remain current-season-named to avoid breaking JS/CSS. This
  is a COPY fix, not a structural fix.

## Acceptance
- `python manage.py build-site` runs clean.
- CJ Carr's page shows:
  - Phase banner "OFFSEASON · SPRING 2026 · DRAFT WEEK" above Hero.
  - Hero accolade chip now reads "2025 HEISMAN FINALIST".
  - Module order: Hero → Standing → Room → Signature → Bio → Production
    → Savant → Splits → Peers → Cast.
  - Each retrospective module (Production, Savant, Splits, Signature)
    heading clearly states "2025" + "Final" where appropriate.
- A player with no accolades (walk-on Luke Watkins, id 13584) still
  renders without any chip — empty state preserved.
- No JS/CSS/DB changes.

## Verification (Haiku subagent)
- Open Carr's page: confirm all 4 changes visible (banner, chip
  retrospective, module order, relabels).
- Open Watkins's page: confirm empty accolade chip state, banner
  present, module order updated.
- Grep reporting.py for any remaining "CURRENT SEASON" string — must
  be 0 unless it's inside a comment.

## Commit
  frontend: P.0 — offseason hotfix (banner + retrospective labels + bio promoted)

## Log line for SESSION_LOG.md
  YYYY-MM-DD | P.0 | Offseason hotfix: phase banner hard-coded, retrospective
  labels on Production/Savant/Splits/Signature, Hero chip prefixed "2025",
  Bio moved from #10 to #5. No data-layer changes. | P.1 (phase detection)
  is next when ready.
```

---

## Operator notes

**Why hardcoded banner copy is OK for now:** the banner text needs to evolve with the calendar (draft week → post-draft → summer → preseason) but phase-detection is Stage P.1 work. Hardcoding for ~1 week while P.1 ships is fine. Update the string manually if draft week ends before P.1 lands.

**Why keep module IDs / CSS classes unchanged:** Alpine directives, CSS selectors, and in-progress JS helpers reference `.signature-story`, `.current-season-production`, `.algorithmic-signature`, etc. Changing class names in P.0 would break them. Display copy is what readers see; slug names are infrastructure.

**Timing relative to Stage S.2 (frontend migration):** P.0 and S.2 don't collide. P.0 touches heading strings + banner + section ordering. S.2 touches the Signature Story render function internals. If Claude Code lands P.0 first, S.2 inherits the "2025 Signature" heading string and carries it forward — which is correct.

**Estimated time:** 45 minutes including verification.
