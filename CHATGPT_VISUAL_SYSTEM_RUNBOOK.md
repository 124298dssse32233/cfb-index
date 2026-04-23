# The CFB Index — 14-Day ChatGPT Production Runbook

*Companion to `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md` and `CFB_INDEX_IDENTITY_PRODUCTION_PLAYBOOK.md`. This is the literal "do-these-things-each-day" execution manual. Not strategy — operations. Read the two source docs once; reference them, don't re-read them.*

**Day 14 deliverable:** 3 locked master plates + 18 archetype totems + 8 modifier glyphs + 24 section rubric icons, each with a `.prompt.md` sidecar, winners committed to `assets/`, rejects logged with `.reject.md` notes.

---

## Section 1 — Pre-flight checklist

### 1.1 ChatGPT subscription tier

**Required: ChatGPT Plus ($20/mo) minimum.** Plus unlocks `gpt-image-1.5` in the web app, the Custom GPT builder, knowledge-file uploads, and the reference-image / edits workflow. Pro ($200/mo) buys faster generations and more parallel threads — useful if you want to run 6-candidate batches back-to-back, not required. Free tier will not do this work.

**Also recommended (optional for this sprint):** an OpenAI API key at platform.openai.com with $25 funded. Enables Section 6's batch workflow if you decide to stop fighting the chat UI on Day 11+. The full 14-day run at 6 candidates per asset ≈ $12–15 in API spend.

### 1.2 Custom GPT to create — "CFB Index Art Director"

In ChatGPT's side nav: Explore GPTs → Create → Configure.

- **Name:** CFB Index Art Director
- **Description:** Editorial illustration director for The CFB Index. Generates ligne-claire totems, halftone hedcut portraits, and risograph covers against a locked style bible.

Paste the block below — literally, verbatim — into the **Instructions** field:

```
You are the art director of The CFB Index, a weekly editorial-style
college football publication. Your only job is to produce illustrations
that look like they came out of the same magazine. You follow the locked
style bible below on every generation without exception.

THE THREE-TIED-ELEMENTS RULE. Every image must share all three:
1. Bone-cream paper substrate #F3EEE4 — never white, never a gradient,
   never a photograph backdrop that isn't paper-textured.
2. Amber #E0A300 appears somewhere — an accent, a stripe, a glint. If
   an image doesn't contain amber, it is rejected.
3. One of three compositional templates: centered object, off-center
   subject with negative space right, or full-bleed scene. Nothing else.

PALETTE (hard-coded, never "similar to"):
- Warm ink #0B0F14
- Bone paper #F3EEE4
- Amber accent #E0A300 (freshness / motion only)
- Alert red #B7281D (alarm states only)
- Team colors — accent only, never background.

THREE VISUAL FAMILIES — pick one per asset, never hybrid:
A. Ligne claire — 2px uniform contour line, flat fills, no hatching,
   no shadow, Hergé / Chris Ware discipline. For totems, modifier
   glyphs, rubric icons.
B. Risograph screenprint — 2-color overprint, visible 45° halftone
   dot pattern, 1–2mm registration offset, grainy ink, warm paper.
   For weekly covers.
C. Halftone hedcut — WSJ-style stipple + short directional hatching,
   ink only + amber accent, 1,500–3,000 individual marks.
   For anonymous editorial portraits.

HARD CONTENT RULES:
- Never generate real person likenesses. No coaches, no players,
  no real faces. Figures are anonymous: hoods up, backs turned,
  silhouettes, helmets down, crowd masses.
- Never generate team logos, conference marks, helmets of real
  schools, or any licensed IP.
- Stadium architecture is suggestive, not identifiable.
- No text inside illustrations except: pennants, tombstones,
  banners, scoreboards, uniform numbers — and only in condensed
  sans or serif matching the site's display type. Never cursive,
  never script, never handwriting, never fantasy fonts.

STYLE PREFIX BLOCK — prepend this to every internal generation plan:

EDITORIAL STYLE: warm bone-cream paper background #F3EEE4 with visible
paper-fiber texture. Muted limited palette: warm ink #0B0F14, amber
accent #E0A300, deep alert red #B7281D. Hand-made print-era feel. No
digital shine, no gradients, no drop shadows, no chrome, no
photorealism, no glow. Composition off-center with negative space.
Think: New Yorker spot illustration, Field Notes Quarterly cover,
mid-century editorial print, letterpress imperfection.

NEGATIVE (avoid): glossy, shiny, hyperreal, 3D render, trending on
artstation, symmetric, centered, sports-mascot cartoon, generic team
logo, real player faces, corporate vector illustration, AI-smooth skin.

REJECTION TRIGGERS — if any output shows these, regenerate instead of
presenting it:
- Glossy / rendered / chrome / 3D-ish shading
- Symmetric centered composition when the brief asked for off-center
- Missing amber
- Real-person likeness
- Recognizable licensed logo or trademark
- Generic "AI illustration" smoothness with no paper grain
- Line weight that varies or tapers when ligne claire was requested
- Any text inside the illustration in a cursive / script / fantasy font

WORKFLOW: When the user requests an asset, produce 4 candidate images
per generation call by default. After delivery, ask if they want
variations of a specific candidate or a fresh set.

REFERENCE FILES: You have three master plates in knowledge —
totem_master.png, hedcut_master.png, riso_cover_master.png. Use the
relevant plate as a style anchor on every generation.
```

**Knowledge files to upload** (on Day 3, once they exist):
- `totem_master.png` — the locked Anxious Dynasty totem
- `hedcut_master.png` — the locked anonymous-fan hedcut
- `riso_cover_master.png` — the locked Michigan-belief cover
- `VISUAL_STYLE_BIBLE.md` — the canonical bible
- `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md` — concept doc

On Day 1 you build the GPT *without* masters in knowledge — you're producing them. After Day 3, upload all three and re-save the GPT.

### 1.3 Local folder structure

Create inside `C:\Users\kevin\Downloads\Sports Website\`:

```
assets/
  masters/                 # 3 locked style plates + sidecars
  totems/                  # 18 final archetype totems + sidecars
  modifiers/               # 8 final modifier glyphs + sidecars
  rubrics/                 # 24 final rubric/utility icons + sidecars
  rejected/
    masters/
    totems/
    modifiers/
    rubrics/
docs/
  VISUAL_STYLE_BIBLE.md    # already scoped in playbook Part 2
  PROMPT_TEMPLATE.md       # prefix block + template variants
```

### 1.4 Naming + sidecar convention

- **Final:** `assets/totems/anxious-dynasty.png` (kebab-case; add size suffix only if you render a second variant, e.g. `anxious-dynasty-80.png`).
- **Sidecar:** `assets/totems/anxious-dynasty.prompt.md` using the 7-field template from playbook Part 5 (one-line brief / visual family / full prompt / reference images / model+settings / selection rationale / rejection notes).
- **Rejected:** `assets/rejected/totems/anxious-dynasty_candidate_3.png` + `anxious-dynasty_candidate_3.reject.md` (one sentence on *why* rejected).
- **Versioning:** only roll `-v2` if you re-commission after the library is live. During this 14-day sprint, overwrite in place.

---

## Section 2 — Day-by-day runbook (14 days)

Time commitments assume one gatekeeper (Kevin) working solo. "Half day" ≈ 4 hrs. "2 hrs" is 2 hrs.

### Day 1 — Ligne-claire master plate (3–4 hrs)

**Goal:** produce the Anxious Dynasty totem at a quality bar you'd commit as the canonical style reference for *every* subsequent ligne-claire asset. This one file sets the line-weight, fill-density, and amber-discipline standard for all 26 ligne-claire assets that follow.

**Prompt to paste** into the CFB Index Art Director GPT:

```
Generate 4 candidate images for the ligne-claire master plate.

SUBJECT: a single symbolic object that represents The Anxious Dynasty.
The object is a crumbling stone crown resting on a short pedestal, one
front jewel socket empty, hairline cracks running down one side, a
sprig of ivy creeping up the pedestal base. No humans. No faces. No
team logos. Just the object on bone paper #F3EEE4.

MEDIUM: ligne claire illustration. Uniform 2px warm-ink #0B0F14 contour
line. No hatching. No cross-hatching. Flat local-color fills only —
stone in a muted neutral, ivy in a muted green. Every element rendered
with equal line precision, foreground and background. Hergé / Chris
Ware discipline. Clean silhouette legible at 40px.

AMBER: the empty jewel socket's rim, or a small tag tied to the
pedestal, is amber #E0A300. Exactly one amber detail.

COMPOSITION: object off-center to the right, negative space at left.
~20% paper margin on all sides. 3/4 front view. Square 1:1 aspect.

Return 4 variants. All four must obey the prefix block and the
three-tied-elements rule.
```

**Success criteria (pass/fail for "Day 1 done"):**
- One candidate reads editorial at 600px AND stays legible when downscaled to 80px.
- Amber is present and reads correctly at thumbnail.
- Line weight is uniform — no tapering, no feathering.
- No shadow, no gradient, no chrome.
- The piece would feel at home printed on warm cream cardstock.

If none of the 4 pass, re-prompt with Section 4 tactics. Allow up to 3 re-prompt rounds. If still failing at round 4, stop — re-check the GPT's Instructions field for truncation (ChatGPT sometimes silently truncates very long paste-ins). Reload and continue.

**When a winner is picked:**
1. Download as `assets/masters/totem_master.png`.
2. Also save a copy to `assets/totems/anxious-dynasty.png` — this file does double duty as master + first finished totem.
3. Write `assets/masters/totem_master.prompt.md` (7-field template).
4. Move the other 3 to `assets/rejected/masters/` with `.reject.md` notes.

**If ChatGPT is stubborn:** "Regenerate with heavier paper texture, visible fiber grain, no digital shine or smooth rendering. Line weight exactly 2px with no tapering or ink pooling. Treat this as ligne-claire editorial illustration, not a sports mascot."

### Day 2 — Halftone portrait master plate (3 hrs)

**Goal:** the anonymous archetypal-fan hedcut that sets the style for every future halftone portrait.

**Prompt to paste:**

```
Generate 4 candidate hedcut portraits for the halftone master plate.

SUBJECT: anonymous archetypal portrait — an adult figure in a
threadbare wool scarf, hands in coat pockets, viewed from three-quarter
rear so the face is not visible. Empty stadium bleachers softly
suggested behind the figure at low angle, not identifiable. NO VISIBLE
FACE. The subject is a type, not a person.

MEDIUM: Wall Street Journal hedcut style. Stipple dots and short
directional hatching only. No continuous contour lines for shadow.
Target 2,000–3,000 individual marks. High contrast. Warm ink #0B0F14
on bone paper #F3EEE4.

AMBER: one small amber #E0A300 accent — a scarf stripe, a lapel pin,
or a program tucked under the arm. Exactly one amber detail.

COMPOSITION: bust crop, 3/4 rear view, figure off-center right, negative
space at left for editorial caption overprint. 3:4 portrait aspect.

Return 4 variants. The face must remain obscured through angle, posture,
or crop — never rendered and blurred.
```

**Success criteria:** face actually obscured (not blurred), stipple reads as stipple not a noise filter, amber present, figure feels like a *type*.

**Save winner:** `assets/masters/hedcut_master.png` + sidecar. Reject rest.

### Day 3 — Risograph cover master plate (3–4 hrs)

**Goal:** the Michigan "belief at a decade low" cover that locks the riso cover voice for the season. The playbook flags riso as Midjourney's aesthetic strength — if you have Midjourney v7 spun up, use it for this one. Otherwise gpt-image-1.5 is acceptable.

**Prompt to paste (gpt-image-1.5 in ChatGPT):**

```
Generate 4 candidate risograph covers.

SUBJECT: a lone hooded figure in a winged helmet, shoulders slumped,
walking away from a goalpost at dusk. Figure small in the frame. A
single maize-amber endpoint dot sits at the end of a declining line
traced across the dusk sky above. No identifiable school likeness —
the winged helmet shape is suggestive, not literal.

MEDIUM: 2-color risograph screenprint on warm uncoated paper. Visible
45° halftone dot pattern throughout. 1–2mm registration offset between
the two ink layers. Grainy, imperfect ink coverage. Ink colors: deep
navy #0B0F14 + amber #E0A300, on bone paper #F3EEE4.

COMPOSITION: figure off-center to the lower left, goalpost silhouette
at right, negative space at top for a masthead overprint (we add type
later). 4:5 portrait.

AMBER: the endpoint dot on the declining line is pure amber #E0A300.
A single amber stripe appears on the horizon.

Return 4 variants. No text on the image itself.
```

**Success criteria:** riso grain visible and feels printed, registration offset present but subtle, no gloss, composition leaves room for the masthead, the amber dot is the focal resolution.

**Save winner:** `assets/masters/riso_cover_master.png` + sidecar.

**End-of-Day-3 checklist:** three masters sitting in `assets/masters/`. Open them side-by-side in a single preview window. If they read as *one magazine*, proceed. If one feels off, regenerate before continuing — everything downstream compounds off these three files.

Then upload all three masters + `VISUAL_STYLE_BIBLE.md` + `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md` to the CFB Index Art Director GPT's knowledge files. Re-save. Verify the knowledge is live by asking the GPT to describe the masters back — it should reference the files by name.

### Day 4 — Totems 1–4 (3 hrs)

Anxious Dynasty is already finalized from Day 1. Today you ship: **Perpetual Believer, Wounded Giant, Hopeful Uprising** (three more). Prompts are in Section 3.

For each: paste the archetype-specific prompt into the Art Director GPT → get 4 candidates → curate per Section 5 → save winner + sidecar → move rejects.

**Pace target:** 45 minutes per totem including rejection notes. If you're slower than that by noon, you're over-iterating — commit the best available, flag for Day 14 rework, and move on.

**Success criteria (per totem):** reads editorial at 600px, legible at 80px, amber present, same line weight and fill density as `totem_master.png` when laid beside it.

### Day 5 — Totems 5–8 (3 hrs)

**Quiet Professional, Identity-Crisis Blueblood, Content Mid-Major, Generational Hope.** Same cadence.

**Watch for drift:** Day 5 is where prompts start to feel boring and you're tempted to get clever. Don't. The system *is* the product. If a totem isn't working, re-read its prompt in Section 3 instead of improvising.

### Day 6 — Totems 9–12 (3 hrs)

**Newly Crowned, Stockholm Syndrome, Service Academy, Coach Cult.**

**Mid-run review:** at end of Day 6 you have 12 totems. Open them as a 4×3 grid. Do they read as one set? Flag 2–3 outliers on a punch list for Day 14 rework — don't fix now.

### Day 7 — Totems 13–16 (3 hrs)

**HBCU Standard, Mercenary, Celebrity Appointment, Petulant Blueblood.**

### Day 8 — Totems 17–18 + rework buffer (half day, ~4 hrs)

**Regional Identity, Sleeper.** That leaves ~2 hrs buffer — use it to rework any of the 16 totems flagged on the Day 6 mid-run review. Resist adding new assets; use the buffer for quality.

**End-of-Day-8 gate:** 18 totems committed, 18 sidecars written. Open the full 18-tile grid. If any one breaks the family feel, regenerate now. This is the last quiet day before glyphs and icons.

### Day 9 — Modifier glyphs 1–4 (2.5 hrs)

**State Identity, Rivalry-Defined, Faith-Based, Academic Cousin.**

**Glyph prompt template** (paste once per glyph, swap the two bracketed fill-ins):

```
Generate 4 candidate modifier glyphs.

SUBJECT: an extreme-minimalist ligne-claire glyph representing
[MODIFIER NAME]. The glyph is [SPECIFIC OBJECT]. No humans. No faces.
No team logos. No text. One object, pure silhouette.

MEDIUM: ligne claire on bone paper #F3EEE4. 2px uniform warm-ink
#0B0F14 contour only. NO fill. NO hatching. NO shadow. Pure line
drawing. Target render size 48×48px. IBM Carbon icon discipline —
strokes snap to a pixel grid, butt caps, 2px corner radius.

AMBER: one amber #E0A300 dot or stripe, ≤10% of visual weight.

COMPOSITION: glyph centered 1:1. Legible at 16px favicon size.

Return 4 variants.
```

Fill-ins from the concept doc:
- **State Identity** → "a generic US-state outline with a single five-pointed star inside it"
- **Rivalry-Defined** → "two opposing arrows crossing at their centers to form an X"
- **Faith-Based** → "a church steeple silhouette with a simple cross at the peak"
- **Academic Cousin** → "a laurel wreath encircling an open book"

### Day 10 — Modifier glyphs 5–8 (2.5 hrs)

- **Sibling School** → "two simple gate silhouettes side-by-side, one slightly taller than the other"
- **Scorned Ex** → "a single chain link, broken cleanly at one end"
- **Pedigree-Entitled** → "a vertical hanging ribbon with a single circular medal at its base"
- **Independent** → "a lone flagpole standing freely, no flag"

**End-of-Day-10:** 18 totems + 8 glyphs = 26 assets. Grid-review the 8 glyphs together — they drift most easily because they're smallest and simplest. If one feels heavier than its neighbors, re-render.

### Day 11–13 — Section rubric icons (2.5 hrs/day × 3 = 7.5 hrs)

**Scope note + a reconciliation:** the concept doc specifies 8 named section rubrics (N° 01 through N° 08); the playbook Part 6 sets the budget at 24 icons. This runbook resolves that by keeping the 8 named rubrics and adding 16 editorial-utility icons the hub and team pages will need. **Before Day 11, review and approve the 16 utility candidates below — swap any that don't fit.**

**Day 11 — 8 named section rubrics:**
1. N° 01 Mood Index → pulsewave inside a circle
2. N° 02 The Ticker → stacked horizontal tick marks
3. N° 03 Hype vs Reality → two overlapping axes, one solid one dotted
4. N° 04 The Taxonomy → a skeletal branching tree trunk
5. N° 05 The Rivalry → two profile helmets facing each other
6. N° 06 The Lexicon → an open dictionary with one entry underlined
7. N° 07 This Week's Cards → three overlapping index cards
8. N° 08 The Commiseration → a single lit candle

**Day 12 — 8 editorial-utility icons (batch A):**
9. Pull-quote mark (oversized quotation mark)
10. Footnote dagger
11. Field-notes pencil stub, horizontal
12. Section-divider fleuron (three-dot ornament)
13. Archive back-arrow (left-chevron in circle)
14. Next-issue forward-arrow (right-chevron in circle)
15. Chart-legend dot row (three ascending dots)
16. Table-row indicator (rightward small triangle)

**Day 13 — 8 editorial-utility icons (batch B):**
17. Rivalry crossbar (horizontal thick bar)
18. Season compass (four-point compass rose, minimal)
19. Snow-week cloud (stylized snowcloud)
20. Tailgate flame (single-point flame)
21. Coach's pea whistle, profile
22. Referee flag on short staff
23. Yardline chalk mark (dashed horizontal line)
24. Stopwatch (circular with crown)

**Icon prompt template** (paste per icon, swap the fill-in):

```
Generate 4 candidate rubric icons.

SUBJECT: a ligne-claire icon representing [LABEL]. The icon is
[SPECIFIC NOUN FROM LIST]. No humans. No text.

MEDIUM: ligne claire on bone paper #F3EEE4. 2px uniform warm-ink
#0B0F14 contour only. NO fill. NO hatching. Pure line drawing.
32×32px target render. Strokes snap to pixel grid, butt caps, 2px
corner radius. IBM Carbon / Phosphor discipline.

AMBER: one amber #E0A300 dot or stripe, ≤10% of visual weight.

COMPOSITION: centered 1:1. Legible at 16px.

Return 4 variants.
```

**Strategic alternative:** the playbook notes that hand-drawing these 24 in Illustrator (or Nucleo / IcoMoon) will be faster and higher-quality than fighting the AI at icon scale. **If by mid-Day 11 you have fewer than 6 keepers, switch mediums.** Don't burn three days forcing ChatGPT to do what a vector tool does natively.

### Day 14 — Full-grid review + bible update (half day, ~4 hrs)

**Morning (2 hrs) — Grid review.** Build `docs/day14_grid.html` — a single static page showing all 50 assets on a `#F3EEE4` background at true intended sizes (80px for totems, 48px for glyphs, 32px for rubrics, plus a second 600px row for the totems). Scroll it. Test: if you covered the labels, do they all feel like they came from the same magazine? Score each asset:

- **Pass** — leave as-is.
- **Soft-fail** — candidate for month-2 re-render, keep for now.
- **Hard-fail** — regenerate today before shipping.

**Afternoon (2 hrs) — Bible update.** Re-read every `.reject.md` from the 14 days. Count reasons. Any reason that appears ≥3 times earns an explicit new rule in `VISUAL_STYLE_BIBLE.md`. Example: if "too glossy" hit 7 times, add to the Out list: *"any shading that reads as rendered 3D — flat fills only, no exceptions."* Then re-paste the updated bible into the Custom GPT's Instructions field and re-upload the bible to knowledge.

**Pass/fail for Day 14:** (a) 50 committed assets, (b) full rejection corpus saved, (c) updated bible reflecting what you learned, (d) Custom GPT re-trained. All four, or Day 14 isn't done.

---

## Section 3 — The 18 totem briefs, paste-ready

Every prompt below is the full paste — not a template — for the Art Director GPT. Same frame, only the SUBJECT line varies.

### 3.1 The Anxious Dynasty

See Day 1. This is the master plate; re-use the same file.

### 3.2 The Perpetual Believer

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Perpetual Believer.
The object is a weathered cloth pennant reading NEXT YEAR in condensed
serif caps, thumbtacked at one corner to a splintered wooden plank,
edges frayed, one corner drooping, sun-bleached stripes visible in the
fabric. No humans. No faces. No team logos. Bone paper #F3EEE4.

MEDIUM: ligne claire. 2px uniform warm-ink #0B0F14 contour. No
hatching. Flat local-color fills — cloth in a muted faded primary,
wood in a warm neutral. Same line precision as totem_master.png.

AMBER: the thumbtack is amber #E0A300. Exactly one amber detail.

COMPOSITION: pennant off-center to the right, plank and drooping
corner creating diagonal motion downward-left. ~20% margin. 1:1 square.

Text in the illustration: the words NEXT YEAR on the pennant, in
condensed serif caps matching the site's display type.

Return 4 variants against the master plate.
```

### 3.3 The Wounded Giant

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Wounded Giant. A
toppled stone statue on its side, pedestal still standing upright
behind it, the pedestal inscribed with a glory year (use "1971"). A
crack runs along the statue's shoulder. The statue reads as an
anonymous heroic figure, not a real person. No faces. No team logos.
Bone paper #F3EEE4.

MEDIUM: ligne claire. 2px contour. Flat fills — weathered stone in a
muted neutral. Match totem_master.png.

AMBER: the year inscription "1971" on the pedestal is amber #E0A300.
Exactly one amber detail.

COMPOSITION: toppled statue diagonal across the lower frame, pedestal
upright mid-right, negative space upper-left. 1:1 square.

Return 4 variants against the master plate.
```

### 3.4 The Hopeful Uprising

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Hopeful Uprising.
A young sapling with three leaves pushing up through a jagged crack in
a weathered concrete bleacher riser. Roots faintly visible through the
concrete lines. No humans. No faces. No team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — concrete neutral,
sapling in a muted green. Match totem_master.png.

AMBER: a single amber #E0A300 glint on one leaf tip.

COMPOSITION: bleacher riser horizontal across the lower third, sapling
rising vertically off-center to the right, negative space upper-left.
1:1 square.

Return 4 variants against the master plate.
```

### 3.5 The Quiet Professional

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Quiet Professional.
A clipboard lying flat on a wooden sideline bench, a hand-drawn play
diagram on the top sheet (x's and o's, arrows, no legible team
indicator), a clean silver coach's whistle resting beside it. No
humans. No faces. No team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — clipboard tan, bench
warm wood, whistle a flat muted metallic (not glossy). Match
totem_master.png.

AMBER: the whistle lanyard cord, or a small tag on the clipboard, is
amber #E0A300.

COMPOSITION: clipboard and whistle off-center to the right, viewed
from above at 3/4 angle, negative space upper-left. 1:1 square.

Return 4 variants against the master plate.
```

### 3.6 The Identity-Crisis Blueblood

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Identity-Crisis
Blueblood. A rectangular locker-room mirror mounted on a warm wooden
wall, glass fractured in a spiderweb pattern from a single impact
point. No reflection rendered in detail — the fracture obscures any
reflected content; no face is implied. No humans. No team logos.
Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — wood warm brown,
mirror glass a flat neutral with line-only fracture detail. Match
totem_master.png.

AMBER: a single amber #E0A300 highlight at the fracture impact point.

COMPOSITION: mirror off-center right, hanging vertically, wood wall as
background, negative space at left. 1:1 square.

Return 4 variants against the master plate.
```

### 3.7 The Content Mid-Major

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Content Mid-Major.
A folded pocket schedule card laid flat, every game row neatly circled
in handwritten pen, the card slightly worn at the folds. Team
abbreviations in the rows are illegible (suggestive, not readable).
No humans. No faces. No team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — card cream, pen ink
dark. Match totem_master.png.

AMBER: the hand-drawn circles are amber #E0A300 — the only accent
color, used only for the circles.

COMPOSITION: schedule card centered at a slight 8° rotation, ~70% of
frame. 1:1 square.

Return 4 variants against the master plate.
```

### 3.8 The Generational Hope

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Generational Hope.
A shooting star frozen mid-arc over a simple goalpost silhouette at
dusk. Goalpost is generic, no field markings beneath. The star has a
long thin trailing tail. No humans. No faces. No team logos. Bone
paper.

MEDIUM: ligne claire. 2px contour. Flat fills — goalpost deep navy,
sky a flat muted dusk tone. Match totem_master.png.

AMBER: the shooting star and its trailing tail are amber #E0A300.
Nothing else is amber.

COMPOSITION: goalpost lower-right, star arcing diagonally from
upper-left, negative space upper-right. 1:1 square.

Return 4 variants against the master plate.
```

### 3.9 The Newly Crowned

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Newly Crowned. A
brand-new championship belt seated in an open display case, cardboard
retail tags hanging from one strap, protective tissue paper visible
inside. The belt is generic — no team names, no year, no logos. No
humans. No faces. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — belt leather rich
warm brown (flat, not glossy), case neutral, tissue paper off-white.
Match totem_master.png.

AMBER: the belt's central plate is amber #E0A300. Tags stay neutral.

COMPOSITION: open case off-center left, belt inside, one tag dangling
down-right, negative space upper-right. 1:1 square.

Return 4 variants against the master plate.
```

### 3.10 The Stockholm Syndrome

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Stockholm Syndrome.
A threadbare knit scarf tied in a loose knot around the top of a small
gravestone-style tombstone. The tombstone reads "38 - 3" in condensed
serif caps — a lopsided score, nothing else. No humans. No faces. No
team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — scarf a muted faded
knit pattern, stone neutral grey. Match totem_master.png.

AMBER: one stripe in the scarf pattern is amber #E0A300.

COMPOSITION: tombstone upright mid-frame, scarf tied at top and
draping down one side, negative space at left. 1:1 square.

Text in illustration: "38 - 3" on the tombstone, condensed serif caps.

Return 4 variants against the master plate.
```

### 3.11 The Service Academy

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Service Academy. A
crisply folded triangular flag on a wooden bench, corners sharp, folds
precise, bench viewed from a low angle. Flag detail is not
nation-specific — stars and stripes are suggested but not identifiable
to any country. No humans. No faces. No team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — flag in muted deep
navy + muted neutral, bench warm wood. Match totem_master.png.

AMBER: a small amber #E0A300 brass tack or plaque on the bench.

COMPOSITION: flag off-center right on the bench, bench horizontal
across the lower third, negative space upper-left. 1:1 square.

Return 4 variants against the master plate.
```

### 3.12 The Coach Cult

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Coach Cult. A
cheerleader-style megaphone lying on its side, a thin halo of light
hovering above it. The megaphone is plain — no logos, no team name.
No humans. No faces. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — megaphone a muted
primary, halo rendered as a flat uniform thin line ring (not a glow,
not a gradient — a line only). Match totem_master.png.

AMBER: the halo line is amber #E0A300.

COMPOSITION: megaphone horizontal mid-frame, halo ring above it,
negative space at left and upper-right. 1:1 square.

IMPORTANT: the halo is a flat line ring. No glow, no gradient, no
bloom lighting.

Return 4 variants against the master plate.
```

### 3.13 The HBCU Standard

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The HBCU Standard. A
single brass sousaphone held upright, bell pointed up and slightly
forward as if mid-note during a stand tune. No humans — the
instrument stands alone. No faces. No team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — brass in a muted warm
tone (NOT metallic shine, NOT a gradient — a flat fill only). Match
totem_master.png.

AMBER: the bell's interior and the mouthpiece are amber #E0A300.

COMPOSITION: sousaphone vertical mid-frame, bell mouth pointed
upper-right at a 30° angle, negative space at left. 1:1 square.

IMPORTANT: no metallic shine, no chrome gradient. Brass is a flat
ligne-claire fill.

Return 4 variants against the master plate.
```

### 3.14 The Mercenary

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Mercenary. An open
leather briefcase lying flat, a bound playbook visible inside on top
of a folded sweatshirt, a pen clipped into the playbook's binding. No
legible names on the playbook. No humans. No faces. No team logos.
Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — briefcase leather
warm brown, playbook cover neutral black, sweatshirt a muted color.
Match totem_master.png.

AMBER: the briefcase's two latches are amber #E0A300.

COMPOSITION: briefcase horizontal mid-frame viewed slightly from
above, ~75% of frame, negative space upper-right. 1:1 square.

Return 4 variants against the master plate.
```

### 3.15 The Celebrity Appointment

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Celebrity
Appointment. Two red-carpet stanchion poles with a velvet rope strung
between them. No people. A single visible strip of carpet underneath.
Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — stanchion poles a
brushed-metal flat neutral (no shine), rope a muted deep red, carpet
strip a muted dark red. Match totem_master.png.

AMBER: the bases of both stanchions are amber #E0A300.

COMPOSITION: two stanchions at subtly asymmetric angles (left slightly
forward, right slightly back), rope sagging slightly between, carpet
strip across the lower edge, negative space above. 1:1 square.

Return 4 variants against the master plate.
```

### 3.16 The Petulant Blueblood

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Petulant Blueblood.
An ornate gilded throne chair tipped onto its side on a floor, one
leg pointed in the air, cushion slipped to the ground beside it. No
humans. No faces. No team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — throne frame rendered
as a flat muted amber-tinged neutral (no metallic shine, no gradient),
cushion deep muted red, floor neutral. Match totem_master.png.

AMBER: the throne's frame accents are amber #E0A300 (kept to ≤15% of
visual weight).

COMPOSITION: throne diagonal across the lower two-thirds, tipping
left, cushion on the floor at right, negative space upper-left.
1:1 square.

Return 4 variants against the master plate.
```

### 3.17 The Regional Identity

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Regional Identity.
A vintage pennant cut in the silhouette of a generic US state (a
simple lozenge-like state shape — not identifiable as any specific
state), hanging from a short wooden dowel by two cords. No legible
text on the pennant. No humans. No faces. No team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — pennant in two muted
primaries as horizontal stripes, dowel warm wood. Match
totem_master.png.

AMBER: one pennant stripe is amber #E0A300.

COMPOSITION: pennant off-center right hanging vertically from dowel,
dowel horizontal near top, negative space at left. 1:1 square.

Return 4 variants against the master plate.
```

### 3.18 The Sleeper

```
Generate 4 candidate archetype totems.

SUBJECT: a single symbolic object representing The Sleeper. A dusty
two-handled trophy resting on a high wooden shelf, a layer of dust
visible on its rim and base, a single fingertip trail swiped across
the dust as if someone just rediscovered it. No team name on the
trophy. No humans visible — the fingertip trail is the only trace.
No faces. No team logos. Bone paper.

MEDIUM: ligne claire. 2px contour. Flat fills — trophy warm muted
gold (flat, not shiny), shelf warm wood, dust rendered as a soft flat
grey layer. Match totem_master.png.

AMBER: the fingertip trail through the dust reveals amber #E0A300
underneath — the only warm accent.

COMPOSITION: trophy centered on the shelf, shelf horizontal in the
lower third, negative space above and at left. 1:1 square.

Return 4 variants against the master plate.
```

---

## Section 4 — The re-prompting playbook

When first-pass output is wrong in a specific way, don't start over — paste the matching fix below as a follow-up in the same conversation. Keep the conversation open so the GPT retains context.

| Failure mode | Paste-ready fix prompt |
|---|---|
| Too glossy / rendered / 3D / chrome | "Regenerate with visible paper-fiber grain throughout. No digital shine, no metallic gradients, no chrome — treat every fill as flat printed ink on warm uncoated paper. Letterpress imperfection, not rendered CGI." |
| Centered / symmetric composition | "Regenerate with the subject off-center to the right, ~60% negative space at left. No symmetric axial composition. New Yorker spot illustration, not Instagram-center." |
| Missing amber accent | "Add exactly one amber #E0A300 detail — a tag, a stripe, a glint, a label. Everything else stays. Amber is non-negotiable." |
| Line weight tapers / varies | "Regenerate with strict 2px uniform contour. Every line — foreground and background — same weight. No tapering, no brush feather, no ink pooling. Ligne-claire discipline: single-weight ink outline only." |
| Random text appears where it shouldn't | "Regenerate with NO text anywhere in the image. Strip all lettering. The only exceptions in this library are explicitly specified pennants, tombstones, or banners." |
| Default "sports mascot cartoon" look | "This is editorial illustration, not a mascot cartoon. No cartoon face, no exaggerated expressions, no Nickelodeon geometry. Think New Yorker, Field Notes, Hergé — not ESPN or team mascot design." |
| Real-person likeness appearing | "Regenerate with the figure viewed from behind, or the face completely obscured by helmet / hood / crop. No recognizable facial features under any circumstances. The figure is a type, not a person." |
| Team logo appearing | "Regenerate with all team indicators removed. No logos, no team names, no school-specific colors, no mascot likenesses. The subject is generic and archetypal — it cannot point to any real school." |
| Output looks like a 3D UI icon | "This is a hand-drawn editorial illustration on warm cream paper, not a UI icon. Flat printed ink only. No beveled edges, no drop shadow, no faux-3D." |
| Halftone reads as digital noise filter | "Regenerate with real stipple-and-hatch hedcut marks — 2,000–3,000 individual dots and short directional strokes, WSJ hedcut style. Not a halftone filter applied to a photo." |
| Riso grain too uniform / fake | "Increase registration offset between ink layers to 1–2mm visible misregistration. Add ink bleed at layer boundaries. Make paper-fiber grain visible through the ink — letterpressed, not filtered." |
| Candidate feels generic | "Add one editorial-specific detail — a worn corner, a frayed edge, a small weathered mark — that makes this object feel owned and used, not stock. The argument is 'this belongs to someone's history,' not 'this is clip-art.'" |

If the same failure persists after 2 re-prompts, stop and reload the Custom GPT in a fresh conversation — its system-prompt attention sometimes decays in long sessions. A new conversation with the same GPT resets the drift.

---

## Section 5 — Curation & rejection protocol

**Per-asset review (5–7 minutes):**

1. Open the 4 candidates side-by-side at *true intended size*. For totems that means both 80×80 and 600×600; for glyphs 48×48 + 200×200; for rubrics 32×32 + 128×128. An illustration that works at one scale and not the other is a fail.
2. Eliminate any candidate that fails the three-tied-elements rule — bone paper? amber? one of the three compositional templates? Hard-fail; no rescue.
3. Eliminate any candidate with an AI-slop tell — extra fingers, melted geometry, chrome shine, phantom shadows, impossible anatomy.
4. Of the remaining, which matches the master plate's line weight and fill density closest? That one wins.
5. Overthinking past 2 minutes means you're between two good options — take the one with more editorial specificity (worn edges, owned feel).
6. Save winner to its final path. Move the 3 rejects to `assets/rejected/[category]/`.
7. Write the sidecar (7-field template from playbook Part 5).
8. Write a one-line `.reject.md` for each reject: *why* it lost. Example: "candidate_3: line weight tapered at the crown tines, broke ligne-claire discipline."

**When to regenerate instead of accepting:**
- All 4 candidates fail the three-tied-elements rule.
- All 4 feel like outliers when placed beside the master plate.
- You'd be embarrassed to see this asset in the year-end archive grid.

**When to accept best-available and move on:**
- One candidate passes all hard rules but feels ~80% of the quality you want.
- You've re-prompted twice and improvement is asymptotic.
- Day pace is at risk (Day 4's 45-min budget, etc.).
- Flag it on the Day 14 rework list and ship.

**End-of-day batch review (10 min):** Open all the day's winners in a grid. Any asset that jumps out as not-belonging → mark for Day 14 rework. Don't iterate at end-of-day — iterate on Day 14 with fresh eyes.

---

## Section 6 — Batching and ChatGPT efficiency

**Conversation management.** One conversation per asset family per day. Fresh chat on Day 4 morning for "totems 1–4," another on Day 5 for "totems 5–8." Focus keeps short-term context tight and prevents drift. Don't run a whole week in one mega-thread — quality degrades after ~15 generations in a single chat.

**"Variations of #2."** After 4 candidates arrive, say: "Generate 4 more variants based on candidate #2 but with [specific adjustment]." ChatGPT carries candidate references inside a conversation. Faster than re-prompting from scratch. Use it when a candidate is 70% right and needs a specific nudge.

**gen_id references.** Every generated image has a `gen_id` visible on hover. When you want a different subject in *exactly the same style*, prompt: "Use the same style as gen_id [id], new subject: [X]." This is your cross-session consistency lever when the master-plate upload isn't tightening style enough.

**Uploading references.** The Art Director GPT already has the masters in knowledge, so most days you don't need to upload. Exception: on Day 14 rework, upload the approved-totems grid as one wide image with "here are the 18 approved totems, use this as the reference feel for the re-render of [slug]."

**When to switch to API batch mode.** If you're doing more than 40 generations in a day, stop fighting the chat UI — script it via `openai.images.edit()` with the master plate as the reference, loop over a list of subject briefs, save candidates to disk, review in a local grid viewer. Playbook Part 5 Option 2 has the pseudocode. One evening of API batching produces what takes 3 days of chat clicking.

**Tab management.** Four browser tabs during a run: (1) the Art Director GPT conversation, (2) a file-explorer on `assets/`, (3) a preview tool open on the growing grid, (4) the concept doc + playbook for reference. Don't add a fifth — context-switching past four destroys throughput.

**Stop when the eye is tired.** If you're consistently picking candidate #1 without real deliberation, the eye has fatigued. Stop for the day. A tired gatekeeper approves slop they'd reject on Monday. This is the single most common failure mode in AI illustration production — more damaging than any prompt mistake.

---

## Section 7 — Hand-off to the weekly issue workflow

After Day 14, library production mostly stops; per-issue production starts. For each weekly issue going forward:

**Monday (1 hr).** Write the cover brief — one sentence of visual argument. *"Michigan's belief at a decade low, a hooded figure walking away from a goalpost at dusk."* Commission ONE cover (playbook Template A — Midjourney or Art Director GPT) and ONE commiseration cartoon (Template F). That's the whole weekly art commitment.

**Tuesday (2 hrs).** Generate 6 cover candidates + 6 cartoon candidates. Pick one each. Save to `assets/covers/vol-v-no-[NNN]-[slug].png` and `assets/cartoons/vol-v-no-[NNN]-[slug].png` with sidecars.

**Wednesday (30 min, optional).** One Lexicon panel illustration if the week's featured phrase warrants it.

**Friday.** Publish. The new cover drops into the archive's visual history page. Archive value compounds issue over issue — by issue 100, the archive *is* the moat.

**Monthly (2 hrs).** Fill library gaps — one or two editorial-generic portraits, a stadium silhouette, a field-notes marginal. Cap 8/month.

**Quarterly (half day).** Moat-ledger review — are we drifting? Rebuild the Day-14 grid with the new quarter's assets added. If ≥3 assets now feel like outliers, re-render them. Update the bible with what was learned.

That's the operating rhythm. ~4 hrs/week per issue, 2 hrs/month of library work, half a day/quarter of audit. 47 issues a year, compounding.

---

*End of runbook. Execute Day 1 tomorrow. Bring back the first 4 Anxious Dynasty candidates and we'll curate together.*
