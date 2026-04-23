# The CFB Index — Visual System & Image Library Concept

**Ambition:** build a bespoke illustration library — 500+ images over the season — that makes the CFB Index look and feel like nothing else in sports media. Warm, considered, editorial, weird in the right ways. Not clip art. Not corporate vector flat. Not AI-slop hero images. A visual identity that a smart CFB fan recognizes before they read a word.

**Tool:** ChatGPT (and similar) for generation. The edge isn't the tool — it's the style bible, the taxonomy, and the curation discipline.

---

## 1) The one rule that makes everything else work

**Every image on this site looks like it was pulled from the same magazine.**

Three directions are usable for a sports-editorial publication. Many other directions would be fine individually but would break the system when you put them on the same page:

- **Ligne claire editorial (small, iconic, monochrome).** Thin single-weight line drawing, flat fills, 2–3 colors max, lots of white/bone space. Hergé energy, but modernized. Works at favicon size and at poster size. This is the voice for icons, archetype marks, modifier glyphs, section rubrics.
- **Risograph/screenprint (bold, poster, full color).** Two-color overprint, slight misregistration, visible paper texture, punchy saturated team-color accents. Works for Index Cards, issue covers, rivalry marks. The energy is "dorm-room poster that somehow ended up in the Whitney gift shop."
- **Halftone engraving (portrait, historical, moody).** Cross-hatched pen-and-ink on bone paper, or old-newspaper halftone dot pattern, black ink only + one accent. Works for editorial portraits, the commiseration block, season-arc "field notes," lexicon feature illustrations. Think The New Yorker op-ed page, or a 1972 Sports Illustrated feature.

Three families, one system — because they share **palette, paper texture, and print-era DNA**. All three live on bone paper with warm ink. All three use team color as accent only, never as background. All three feel like something you'd find in a printed publication, not a dashboard.

Proposed primary direction: **lead with risograph for covers and cards, ligne claire for icons, halftone for portraits.** Lock this before generating anything.

---

## 2) The style bible (the document that makes 500 images look like one library)

Before you generate a single image, write one file — `STYLE_BIBLE.md` — that every image prompt starts from. This is what keeps ChatGPT from drifting into slop.

Components:

**Palette (hard-coded, never "similar to"):**
- Warm ink `#0B0F14`
- Bone paper `#F3EEE4`
- Amber accent `#E0A300` (sparingly, freshness/motion signals only)
- Alert red `#B7281D` (alarm states only)
- Team colors (pulled from a canonical team-color JSON map) — accent only, never background

**Paper & texture:**
- All illustrations read as if printed on warm cream paper stock
- Subtle paper grain (risograph and halftone only)
- Slight edge imperfection on ligne-claire strokes (not laser-straight vector)

**Line weight:**
- Ligne claire: 1.5–2.5px at 1000px render, uniform weight, no tapering
- Engraving: 0.5–1px cross-hatching, organic weight variation allowed
- Risograph: no line work (shape-based only)

**Composition:**
- No drop shadows, no gradients (except the paper grain), no 3D extrusions, no glossy highlights
- No "AI-isms" — no floating particles, no lens flares, no generic sunburst rays, no smooth metallic gradients
- Negative space is part of the composition, not empty filler

**Typography in images:**
- Zero text inside most illustrations (signs, scoreboards, uniform numbers excepted)
- Where text is unavoidable (a pennant, a tombstone, a banner), use condensed sans or serif that matches the site's type system — never use cursive, script, handwriting, or fantasy fonts
- Uniform numbers are always legible and accurate

**Content rules:**
- Never generate real person likenesses (no coaches, no players, no Deion, no Saban, no Prime)
- Figures are anonymous — hoods up, backs turned, silhouettes, helmets down, crowd masses, fan-in-stands-from-behind
- Stadium architecture is suggestive, not identifiable (avoid literal "this is exactly the Big House")
- Sideline/crowd scenes read as editorial, not photojournalism
- No overt NIL logos, brand marks, or licensed IP

**What gets in, what doesn't:**
- IN: weathered objects, old trophies, folded flags, clipboards, pennants, bleachers, marching-band instruments, tailgate grills, stadium silhouettes, pocket-schedules, ticket stubs, scoreboards, helmets, marching band formations
- OUT: swooshes, motion blurs, power lines, screaming athletes mid-action, fire effects, explosion effects, "realistic photography" styling, stock-photo energy

Save this as one page. Reference it as the **first paragraph** of every image prompt. No negotiation.

---

## 3) The asset taxonomy (what to build, ordered by leverage)

### Tier 1 — ship these first, they define the brand

**1.1 Archetype totems (18 images)**

One symbolic object per primary archetype, rendered in **ligne claire on bone paper, single ink + one accent team-neutral amber**. Each totem is a specific noun, not a scene. Dense with editorial meaning.

| Archetype | Totem proposal |
|---|---|
| The Anxious Dynasty | A crumbling stone crown on a pedestal, one jewel missing |
| The Perpetual Believer | A weathered "NEXT YEAR" pennant on a splintered pole |
| The Wounded Giant | A toppled statue, pedestal still inscribed with a glory year |
| The Hopeful Uprising | A sapling growing through a crack in concrete bleachers |
| The Quiet Professional | A clipboard with a neat play diagram, a clean whistle beside it |
| The Identity-Crisis Blueblood | A mirror on a locker-room wall, reflection fractured |
| The Content Mid-Major | A pocket schedule with every game neatly circled |
| The Generational Hope | A shooting star frozen above a goalpost |
| The Newly Crowned | A brand-new champion belt, still in its box with tags |
| The Stockholm Syndrome | A threadbare scarf tied around a losing-score tombstone |
| The Service Academy | A folded flag, corners sharp, on a wooden bench |
| The Coach Cult | A megaphone with a faint halo |
| The HBCU Standard | A sousaphone mid-note, bell pointed skyward |
| The Mercenary | An open briefcase with a playbook inside |
| The Celebrity Appointment | A red-carpet stanchion with a velvet rope |
| The Petulant Blueblood | A gilded throne knocked onto its side |
| The Regional Identity | A vintage state-shaped pennant |
| The Sleeper | A dusty trophy on a high shelf, slowly being rediscovered |

These render in two sizes: **80×80px chip icon** (for cards and tags) and **600×600px editorial portrait** (for the hub archetype grid + team pages). Same object, two resolutions.

This is the single highest-leverage move in the whole visual system. Nobody else does this. Once it lands, every team page carries a little editorial identity mark.

**1.2 Modifier glyphs (8 images)**

One small iconic mark per modifier, **extreme ligne claire minimum, black-on-bone only, 48×48px**. These sit as chips next to archetype names.

| Modifier | Glyph |
|---|---|
| State Identity | State outline with a single star |
| Rivalry-Defined | Two opposing arrows crossing |
| Faith-Based | A church steeple silhouette |
| Academic Cousin | A laurel wreath with an open book |
| Sibling School | Two gates side-by-side, one slightly taller |
| Scorned Ex | A broken chain link |
| Pedigree-Entitled | A vertical ribbon with a single medal |
| Independent | A lone flagpole, no affiliation |

Simple enough to read at 16px favicon scale if needed. Legible at 200px inside a modifier chip.

**1.3 Section rubrics (8 images)**

One small mark per flagship section of the hub issue. These sit next to the `N° 0X` eyebrow in section headers.

| Section | Rubric |
|---|---|
| N° 01 The Mood Index | Pulsewave inside a circle |
| N° 02 The Ticker | Stacked horizontal tick marks |
| N° 03 Hype vs Reality | Two overlapping axes, one strong one dotted |
| N° 04 The Taxonomy | A branching tree trunk, skeletal |
| N° 05 The Rivalry | Two helmets facing each other, beveled |
| N° 06 The Lexicon | An open dictionary with one entry underlined |
| N° 07 This Week's Cards | Three overlapping index cards |
| N° 08 The Commiseration | A single candle, lit |

Also ligne claire, mono-on-bone, ~40×40px.

**1.4 Issue cover art (weekly, one image per issue)**

The headline illustration that anchors the cover story. **Risograph / screenprint**, two-color over-print, full bleed. 1200×800 editorial aspect.

This is the equivalent of a New Yorker cover or an Economist cover. One image, carefully commissioned. Example covers from your current Michigan story:

- A hooded figure in winged helmet, shoulders slumped, walking away from a goalpost at dusk. Maize endpoint dot on a declining line in the sky. Title type overlaid: "Michigan's Belief Is At A Decade Low."
- Alternative: a single empty maize folding chair in an empty press-conference room, one microphone, one dangling spotlight. Title type: "The Moore Presser."
- Alternative: a weather vane shaped like a wolverine, spinning in a dust devil.

One of these ships per week. The back catalog of 47 covers becomes the archive's greatest asset — a visual history of the season's emotional arc.

### Tier 2 — ship these in the first month, they deepen the system

**2.1 Team helmet silhouettes (133 FBS, optionally 532 more for FCS/DII/DIII)**

Canonical ligne-claire helmet profile per school, in the team's primary color. Silhouette only — no logos, no facemask detail that would require trademark clearance, just the recognizable **shape + color** of each school's helmet.

These become the team-chip helmet icons everywhere on the site. Already referenced throughout the design as 20–28px team chips. Ship them as generated-and-curated assets, not as text abbreviations.

**2.2 Rivalry marks (12 images)**

One custom editorial mark per flagship rivalry. **Ligne claire, two team colors, small coin/seal format** — like a varsity letter patch or a medal.

Examples:
- Michigan / Ohio State ("The Game"): Two helmets nose-to-nose, one maize one scarlet, over a single yard-line.
- Iowa / Iowa State (Cy-Hawk): A pitchfork and a corncob crossed.
- Army / Navy: An anchor and a saber crossed, 14 stars around.
- Alabama / Auburn (Iron Bowl): Two boxer fists in houndstooth and burnt orange, touching gloves.
- Red River Rivalry: A single longhorn skull with a crimson sooner schooner behind it.

These sit in each cell of the Rivalry Obsession Matrix (N° 05) and can be used standalone on team pages.

**2.3 Archetype migration diagrams (5 images)**

Hand-drawn-looking arrow-diagram illustrations showing the common migration pathways between archetypes. **Halftone engraving on bone paper, purely monochromatic**.

- **The Ascension Path:** Hopeful Uprising → Newly Crowned → Anxious Dynasty (with arrows and small illustrative nodes).
- **The Collapse Path:** Anxious Dynasty → Wounded Giant → Identity-Crisis Blueblood.
- **The Rebuild Path:** Wounded Giant → Hopeful Uprising → Newly Crowned.
- **The Fade Path:** Celebrity Appointment → Mercenary → Coach Cult → collapse.
- **The Rare Reclamation:** Identity-Crisis Blueblood → (long pause) → Anxious Dynasty again.

These render as marginal illustrations in the taxonomy section closer — the italic-serif paragraph that reads *"Archetypes are probabilistic, not permanent. Half of the 2024 Hopeful Uprisings are now Wounded Giants."*

**2.4 Commiseration cartoons (weekly, one per issue)**

A single moody halftone-engraving spot illustration for the weekly commiseration block. Small, 400×300, bone paper, one accent color only.

For the Michigan issue: an empty winged helmet on a locker-room bench, single hanging lightbulb, long shadow. For a Nebraska issue: a "WE'RE BACK" banner crumpled in a trash can. For a USC issue: a palm tree silhouette with half its fronds gone.

These are the emotional punchline of every issue. They're the image readers screenshot and share.

### Tier 3 — ship these progressively, they add depth

**3.1 Editorial portrait generics (10–15 reusable "fan types")**

Not specific fans. Archetypal fan silhouettes. Shoulders and backs of heads, in stadium contexts. Useable as library stock for future articles.

- The Dad at the Tailgate (cooler, folding chair, back of head)
- The Student Section (anonymous mass seen from low angle)
- The Alumni Returner (coat, scarf, gray hair seen from behind)
- The Sign Holder (arm raised, sign obscured)
- The First Game (child on shoulders, seen from behind)
- The Superfan (body paint shoulders, no face)
- The Road Tripper (packed car seen from driver's POV)

Halftone engraving. Anonymous. Never faces.

**3.2 Lexicon of the Week illustrations (weekly, one per issue)**

A single ~400×400 editorial spot illustration per featured phrase. Tone matches the phrase's origin community.

For `"5-star trust me"`: a vintage "Trust Me" card being held up from behind a desk, with a recruiting-service logo obscured.
For a deep-cut SEC phrase: corresponding Southern visual context.
For a Big Ten winter phrase: snow, scarf, bleachers visible.

Risograph style, two-color.

**3.3 Stadium silhouettes (40–60 images)**

Anonymous stadium profiles at iconic moments — dusk sky, snow, under-the-lights, end-of-quarter scoreboard view. Used as sectional breaks and as Index Card background art.

Halftone, monochrome on bone paper. Generic enough to not be "this is exactly Michigan Stadium" but evocative enough to feel like college football.

**3.4 Field notes (marginal illustrations)**

Hand-drawn-feel pencil diagrams: X's and O's, field schematics, seating-chart sketches, blackboard-style chalk diagrams. Small (200×150), meant to live in margins of prose sections.

Graphite-on-bone rendering. The "professor's notes on a napkin" feel. Adds handmade warmth to data-heavy sections.

**3.5 Editorial photography substitutes (40–80 images)**

Spot illustrations for: a mascot costume hanging on a hook, a marching band's tuba in a case, a game ball on a muddy sideline, a letterman jacket draped over a chair, a stadium pennant drooping in rain, a playbook open to a key page, a whistle on a lanyard, a coaches-box coffee cup with cold coffee, a sideline headset, a goalpost shadow at sunset.

These fill sidebar slots and header strip backgrounds — replacing the need for photography licensing.

### Tier 4 — opportunistic

- **Tradition illustrations** (Dotting the I, Enter Sandman, Roll Down, The Grove tailgate, The 12th Man sign — one per iconic tradition, ~30–40 total)
- **Historical moment illustrations** (the Flutie Hail Mary, the Bush Push, Kick Six, Music City Miracle — iconic plays rendered as engraving-style memory pieces, used on program history pages)
- **Decade markers** ("the 1970s era," "the 2010s SEC era") — cover-style illustrations for the Archive navigation

---

## 4) The "bespoke & amazing" moves (the differentiators)

Most sports sites could build Tier 1 & 2. Here's what makes this *unique*:

**4.1 The Totem System (already described)** — nobody treats fanbases as having specific symbolic objects. This is editorial illustration treating fan communities like the New Yorker treats literary figures.

**4.2 Weekly original cover art** — 47 issues = 47 custom covers. A year in, the Archive grid becomes a visual history of the season's drama. Readers revisit for the covers, not just the data.

**4.3 Archetype portraits** — every primary archetype gets a full-bleed halftone editorial portrait (600×800) for deep-archetype pages. Not the 80×80 chip totem — a magazine-feature-sized treatment. Example: *The Identity-Crisis Blueblood* is rendered as a hooded figure staring at its own reflection in a locker-room mirror, the reflection fractured. This becomes the wallpaper of the deep page.

**4.4 The Rivalry Coin** — each rivalry gets a seal/coin mark, rendered as if it were a varsity letterman's pin or a military challenge coin. Collectible. Each one tiny, each one carefully commissioned. 12 this year; more next year as new rivalries get canonized.

**4.5 The Commiseration Cartoon** — a weekly spot illustration that becomes the emotional anchor of each issue. Readers share these. They're the unit of virality.

**4.6 The Lexicon Panel** — the featured phrase of the week gets its own small illustrated panel. Like the Far Side's weekly cartoon, but for college football community language.

**4.7 The Field Notes style** — the marginal pencil-diagram illustrations add a handmade, "the staff actually watches football" texture to data-heavy sections. This is the visual equivalent of the italic-serif editorial captions on charts.

**4.8 Paper-texture consistency** — every single image is rendered as if printed on the same warm-cream stock as the rest of the site. This is what makes the system feel like one publication instead of an inventory of assets.

None of these require generative AI to be state-of-the-art — they require editorial discipline. AI is the drafting tool. The style bible and the curation are the product.

---

## 5) The production pipeline

Generating 500 images is easy. Having 500 images that look like one library is the whole game.

**5.1 Prompt template**

Every image prompt starts with the style bible block (copy-paste, not rewritten):

```
Editorial illustration in the style of The New Yorker / mid-century Sports Illustrated.
Medium: [risograph screenprint with visible paper texture] OR [fine line ligne claire]
  OR [cross-hatched engraving / halftone].
Palette: warm ink #0B0F14 on bone paper #F3EEE4. [One team accent color: TEAM_HEX].
No drop shadows. No gradients beyond paper grain. No lens flares or sparkle effects.
No specific real person likenesses. No identifiable licensed logos or trademarks.
Composition: [specific composition].
Subject: [one specific noun or short phrase].
Mood: [one emotional word].
```

Then the specific request. Then one sentence of what NOT to produce (negative prompt).

Save the template as `PROMPT_TEMPLATE.md`. Revise the template as you learn what works — never revise individual prompts. The style bible is shared; the subject-specific copy is the only variable.

**5.2 Naming convention**

`/assets/images/[category]/[subject-slug]-[variant].[format]`

Examples:
- `/assets/images/totems/anxious-dynasty-80.png`
- `/assets/images/totems/anxious-dynasty-600.png`
- `/assets/images/rubrics/n01-mood-index.svg`
- `/assets/images/covers/vol-v-no-047-michigan-belief.png`
- `/assets/images/rivalries/michigan-ohio-state-coin.svg`

Consistent kebab-case. Size suffix for raster variants. Version suffix only if you had to re-cut an asset (`-v2`).

**5.3 Source-prompt record**

For every image committed to the library, save the exact prompt used in a sidecar file: `/assets/images/[category]/[subject-slug].prompt.md`. This is the source of truth. If you need to regenerate at a different size, you start from the saved prompt, not from a fresh description.

**5.4 Curation rules (this is where AI art libraries die without discipline)**

For every subject you commission, generate **4–6 variants**. Reject most of them. Keep **one**.

Rejection triggers (write these down, pin them to the wall):
- Any AI-slop tell (extra fingers, melting geometry, nonsensical shadows, floating artifacts)
- Breaks palette (color that isn't in the bible)
- Breaks medium consistency (e.g., a shadow that implies 3D when it should be flat)
- Recognizable real person likeness
- Recognizable trademark or licensed logo
- Typography in a style that conflicts with the site type system
- "Generic stock illustration" feel — no editorial specificity
- Too literal (a fan screaming = no; a shoulders-slumped figure walking away = yes)

A single gatekeeper (you, initially) makes the keep/kill call. Never commit all six — commit one. The archive stays curated.

**5.5 Review cadence**

- **Weekly:** the three images specific to this week's issue (cover + commiseration cartoon + lexicon panel). Generate Tuesday, commit Tuesday night, publish Wednesday.
- **Monthly:** fill gaps in the library — add 10–15 new reusable assets (editorial generics, stadium silhouettes, field notes, rivalry coins for upcoming games).
- **Seasonally:** regenerate anything that has aged. Style drifts. Refreshed covers for the archive.

**5.6 Where the images live in the code**

Two homes:
- **`/output/site/assets/images/`** — the generated/curated library, committed. Each image has a sidecar `.prompt.md`.
- **Python constants** (new file: `src/cfb_rankings/visual_assets.py`) — the registry mapping archetype/modifier/section/team to image path. The renderer pulls image paths from this registry so renaming an asset is a one-line change.

Never hotlink images from an external service. Every image in the library is a committed file.

---

## 6) First 90 days — the plan

**Days 1–7: Lock the style**

1. Pick the three-family style direction (or counter-propose).
2. Draft `STYLE_BIBLE.md`, `PROMPT_TEMPLATE.md`, the naming convention.
3. Generate *one* totem (The Anxious Dynasty) in all three mediums. Pick the direction that wins.
4. Regenerate the same totem 8 more times, varying one parameter per attempt, to find the canonical rendering spec.
5. Save the winning prompt as the template.

**Days 8–21: Ship Tier 1**

6. Generate all 18 archetype totems (small + large). Curate aggressively — 4–6 attempts per, keep one. Commit the library. 18 × 2 = 36 images.
7. Generate the 8 modifier glyphs. 8 images.
8. Generate the 8 section rubrics. 8 images.
9. Integrate into the hub page — the taxonomy section, the archetype chips on team pages, the section eyebrows.

**Days 22–45: Covers + rivalry + commiseration**

10. Build the weekly cover-art workflow. Ship one cover per week retroactively — backfill Vol V N° 040 through N° 047 to populate the archive visually. 8 images.
11. Generate the 12 rivalry coin marks. Integrate into the Rivalry Obsession Matrix (N° 05) and onto rivalry-match pages. 12 images.
12. Start shipping the weekly commiseration cartoon alongside the commiseration block. 4 new images per month going forward.

**Days 46–75: Depth layer**

13. Commission team helmet silhouettes — 133 FBS first, as a single batch generation run with tight prompt templates and per-team color injection. Aggressive curation — a bad helmet here is worse than no helmet. Backstop with the current text abbreviation for any team whose silhouette isn't convincing. 133 images.
14. Generate the 5 archetype migration diagrams. Place inline in the taxonomy section closer. 5 images.
15. Start the editorial-generics library (fan types, stadium silhouettes, field-notes marginals). 20–30 images.

**Days 76–90: Polish and registry**

16. Build `visual_assets.py` registry so every image is looked up by symbolic name.
17. Add alt-text per image (write once per asset, not per use).
18. Run an accessibility pass — every decorative image has empty alt; every meaningful image has descriptive alt that matches the editorial voice.
19. Audit for palette drift, medium drift, and unauthorized licensed references.

At day 90 the library is ~250–300 curated images. The site no longer looks like a data dashboard. It looks like a publication.

---

## 7) Risks and how to defuse them

**Risk: AI-slop creep.** Generation gets easier week 2, discipline erodes week 6. *Defense:* the rejection triggers in §5.4, a single gatekeeper, the curation discipline of "generate 6, keep 1."

**Risk: Licensed IP contamination.** A helmet looks *exactly* like a real school's trademark. A cover quotes a real coach. *Defense:* the style bible rule against "specific real person likenesses and identifiable licensed logos," and a pre-publish legal-eyeball pass on every cover and every rivalry mark. If in doubt, don't ship — ask first.

**Risk: Style drift across families.** Risograph covers start pulling the ligne-claire icons toward illustrated color; halftone portraits start bleeding into full-color. *Defense:* enforce the three-family rule. Each image is cataloged by medium. No hybrid mediums in a single image except where the style bible explicitly allows.

**Risk: The archetype totems feel too cute / too kitschy / too clever.** "A crumbling stone crown" sounds great in a brainstorm and lands as tacky in execution. *Defense:* prototype all 18 in pencil (literal pencil, or ChatGPT sketch mode) before committing to final. If you can't write a three-sentence caption explaining the totem's meaning that doesn't feel forced, the totem is wrong. Iterate.

**Risk: Time.** Weekly illustration commitments compound. *Defense:* backfill the archive once, then only commit to three new images per issue (cover + commiseration + lexicon). Everything else is library work that happens in batches during quieter weeks.

**Risk: Every generator output needs an original. Even "take that cover but more moody" drifts.** *Defense:* never regenerate a committed asset without rolling the variant counter (`-v2`, `-v3`). The Git history tells you what changed when.

---

## 8) What to decide next (open questions)

1. **Which of the three style families leads?** My recommendation is risograph for covers, ligne claire for icons, halftone for portraits. Counter-proposals welcome.
2. **Is ChatGPT image generation actually the right tool vs. Midjourney / Ideogram / hand-illustration contractor?** ChatGPT is easy; Midjourney is more controllable at quality. A $200/mo contract with a working illustrator might produce the archetype totems at a higher ceiling than any model. Consider at least for Tier 1.
3. **Gatekeeper capacity.** If Kevin is the gatekeeper, this costs him 4–6 hours/week of curation. If an editor hat is hired, that person owns it. Decide.
4. **Do we bother with FCS/DII/DIII helmet silhouettes?** 532 more images. Probably skip — keep those divisions on text abbreviation chips to keep scope contained.
5. **What lives on team pages vs. just on the hub?** Proposal: totem + modifier glyphs + helmet silhouette on every team page. Cover art + commiseration cartoon + lexicon panel *only* on the hub issue page. That keeps team pages clean.

---

## 9) Closing principle

The visual system earns its keep only if a CFB fan looks at a screenshot and immediately knows it's The CFB Index. Not "a sports analytics site." Not "a data dashboard with some illustrations." *The CFB Index.*

Every asset choice should pass this test: **if you covered the logo and the masthead, would this still look like us?** If yes — commit. If no — reject and try again.

Aim for the thing where ten years from now someone pulls an old archive page and the visual voice still reads. That's the bar.
