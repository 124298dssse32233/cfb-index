# The CFB Index — Identity & Production Playbook

*Deep research + executable system for building a world-class editorial identity using ChatGPT image generation + direct-API assets.*

Companion to `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md` (the strategic concept). This document is the **how we actually ship it** half.

---

## Part 1 — What makes editorial identity legendary

Six publications' practices distilled into rules we're stealing. Sources and long-form notes live in §10; this is the operative list.

### The rules we're locking in

**Rule 1 — One gatekeeper, final cover approval, never delegated.** The New Yorker works because Françoise Mouly has been art editor since 1993. Bloomberg Businessweek's 2010-2014 breakthrough was Richard Turley's willingness to fight editors on every cover. The Economist has had one visual voice for four decades under the Hillman redesign. Failure modes — Newsweek post-Tina Brown, Wired post-Dadich, BuzzFeed News as it shrank — all share a lost art director and no succession. **For us: you (Kevin) own final approval on every cover, every archetype totem, every rivalry coin. No delegating to "looks fine, ship it."**

**Rule 2 — Commission to a brief, not to a style.** Mouly's method: one-sentence editorial brief → illustrator returns ten thumbnails → pick one and iterate on composition, not style. The magazine's coherence comes from her gatekeeping of *what the image argues*, not how it's drawn. **For us: every image starts with a one-line editorial brief ("the crumbling stone crown of Florida State's anxious dynasty"), then the prompt + 6-10 generations, then we pick one.**

**Rule 3 — Visual argument, not visual headline.** The Economist's briefing language to illustrators. A "visual headline" is literal (quarterback throwing ball); a "visual argument" is metaphor (empty throne room for a post-dynasty program). The former is stock photography; the latter is editorial identity. **For us: every hero image must make an argument. If it only describes, it's wrong.**

**Rule 4 — Three-mode cover rotation.** Businessweek uses three cover modes: (a) all-typographic, (b) single absurd object on seamless, (c) commissioned illustration. The *system* is the oscillation — readers never know which they'll get but they always know they're reading Businessweek. **For us: Mode A = typographic hero (just big condensed type on bone paper), Mode B = single totem object (riso, limited palette), Mode C = editorial scene illustration (ligne claire, multi-figure). Rotate weekly so no mode ever runs twice in a row.**

**Rule 5 — Typography is the spine.** Monocle runs 15+ illustrators per issue but reads as one magazine because all the type is locked. The illustration lives *inside* a typographic frame that never varies. **For us: our three-voice type system (condensed display + editorial serif + tabular mono) is the coherence engine. Never let an illustration break out of it.**

**Rule 6 — One non-negotiable accent.** The Economist's red rectangle. The FT's salmon pink. Le Monde Diplomatique's single blue. One color appears on every piece without fail. **For us: amber #E0A300 is the non-negotiable. If an image doesn't contain amber somewhere — even as a single accent — reject it or composite it in.**

**Rule 7 — Rituals are uncopyable.** The New Yorker's Thanksgiving cover. The Sports Illustrated Swimsuit Issue. Field Notes Quarterly. A recurring format readers anticipate becomes a moat nothing else can touch. **For us: the Rivalry Week Special Edition (different cover treatment, coin art, section order), the Preseason Almanac, the Postseason Autopsy. Three rituals across the 47-issue year.**

**Rule 8 — Moat ledger, actively maintained.** Copycats can match your look within six months. What they can't match: a licensed custom display face (The New Yorker's Irvin, The Economist's Ecotype, The Guardian's Guardian Egyptian), long-term illustrator relationships (Barry Blitt for 30+ years), proprietary chart language (FT, Upshot, 538), and consistency across years. **For us: quarterly review of the moat ledger, at least one investment per quarter.**

**Rule 9 — Maintain a rejected-images folder.** Equally important to the approved folder. Trains your eye and trains your prompts. Fast Company's mid-2010s collapse was commissioning without a rejection discipline — everything was "good enough" and the result was noise. **For us: `/assets/rejected/[category]/` with a short `.reject.md` next to each file explaining why (off-palette, AI-slop shine, wrong line weight, generic default). Read the folder monthly.**

**Rule 10 — Identity requires a budget line.** SI, BuzzFeed News, Deadspin pre-Defector all lost identity when the illustration budget was the first thing cut. Identity is an operating cost, not a capex. **For us: hard commit to weekly cover art + at least one original commissioned human illustration per quarter (see §6). Budget it like hosting.**

### The failure modes we're specifically avoiding

- **AI-slop creep** — the chrome-orb, gradient, hyperreal, symmetrical, centered default that DALL-E and Midjourney output when you don't fight them. Antidote: deliberate imperfection (riso grain, ink bleed, paper texture), limited palette, off-center composition, §3 prompt discipline.
- **Variety becoming noise** — Fast Company, over-commissioned publications. Antidote: the three-tied-elements rule in §2.
- **Scale without system** — adding assets faster than the style bible can absorb them. Antidote: generate ≤15 new assets per week in month 1-2, review batch against bible before expanding.
- **Losing the art director** — no succession. Antidote: write the bible down so even without you, the next person has rails.

### What stays consistent — the three-tied-elements rule

Every image we publish must share all three:

1. **Same bone paper substrate.** `#F3EEE4` background or inferred background. Never a white background, never a gradient, never a photograph backdrop that isn't paper-textured.
2. **Amber somewhere.** `#E0A300` appears in every image. Usually as an accent (a pennant stripe, a highlight, a single shape). Reject images that don't have it.
3. **One of three compositional templates.** Centered portrait/object, off-center subject with negative space at right, or full-bleed scene. Nothing else.

Diverse illustration styles (ligne claire + risograph + halftone) inside this frame will read as one magazine.

---

## Part 2 — The ChatGPT production system

### The model landscape, honestly

As of April 2026, the operative tradeoffs:

**OpenAI gpt-image-1.5** — the current OpenAI flagship. ~$0.04 per standard image direct. Accepts up to 16 reference images per edit call. Good at text-in-image (relatively). Supports masked in-place edits. Conversational mode in the ChatGPT web app maintains context across a session (say "keep the same style, now do X" and it holds). The honest weakness: editorial *aesthetic* quality lags Midjourney — outputs tend toward literal rather than argumentative, and the default look still skews rendered-glossy unless you fight the prompt hard.

**gpt-image-1-mini** — $0.005 per image. Use for drafts, thumbnails, quick iteration. Don't ship final assets from it; use it to explore composition cheaply before rolling the expensive model.

**Midjourney v7 (V8 in late 2026)** — the quality leader for editorial aesthetics. The `--sref <url>` style reference + `--sv 6` default, plus the V7/V8 Style Creator that generates persistent style handles. This is the cheat code for risograph consistency — create one style reference, use it on every risograph cover for the season, and they lock together. Not on an official API; Discord bot + third-party wrappers.

**Google Imagen** — a strong third option. Not the winner for editorial illustration in current comparisons.

### Honest tool assignment per asset type

| Asset class | Best tool | Why |
|---|---|---|
| Weekly risograph covers | **Midjourney v7** with one locked `--sref` per season | Riso aesthetic consistency is still Midjourney's moat |
| 18 archetype totems (ligne claire) | **gpt-image-1.5** with reference-image workflow | Needs strict line-weight discipline; easier to iterate via API |
| 12 rivalry coins (medallion marks) | **Hire a human illustrator, once** | 12 evergreen assets, $1.5-3k one-time. AI struggles with the precision this asks for; humans crush it |
| Halftone/hedcut editorial portraits | **gpt-image-1.5** with ref images | API workflow; accept 20:1 keep ratio |
| Commiseration cartoons (New Yorker panel style) | **Midjourney v7** with locked sref | Aesthetic quality matters most here; low volume (47/yr) |
| Section rubric icons | **Hand-drawn in Illustrator** OR gpt-image-1.5 with strict grid prompts | Icons are where AI is weakest; consider skipping AI entirely |
| Field-notes marginalia | **Custom handwriting font**, not AI images | Use Calligraphr to turn handwriting into a font; no per-image generation needed |
| 133 FBS team treatments | **Use CFBD + ESPN CDN real logos** (see Part 4) — do not generate | Legal, accurate, free |
| Helmet silhouette treatments | **Real helmet photos from ESPN CDN, stylized via SVG filter** | Same — real assets beat synthetic |

Executive summary: **Midjourney for covers and cartoons, gpt-image-1.5 for totems and portraits, Illustrator/humans for icons and coins, real APIs for team assets.** Don't try to use ChatGPT for everything; use it where it genuinely wins.

### Consistency techniques that actually work

1. **Reference images are the biggest lever, and gpt-image-1.5 finally supports them well.** Create one "master style plate" per visual family (one for ligne-claire totems, one for halftone portraits, one for riso covers). Every new generation uses the plate as a reference via the edits endpoint. This is the single biggest consistency gain available in 2026.

2. **Locked reusable style prefixes.** Every prompt begins with the same 2-3 lines of style specification, then diverges on subject. This is what serious production shops have been doing since DALL-E 3. See the templates in Part 3.

3. **gen_id / ChatGPT seed passthrough.** In the ChatGPT web app, each generated image has a `gen_id` you can reference in the next prompt ("same style as gen_id abc123, new subject: ..."). This maintains style within a conversation. Less useful for cross-session batch production; use reference images instead.

4. **Custom GPT with locked system prompt.** In ChatGPT, create a custom GPT with the entire CFB Index style bible in its instructions. Every chat in that GPT starts with the bible already applied. Pair with uploaded reference images in the knowledge files. This is the cleanest consumer-mode workflow.

5. **API + prompt template + seed.** If building at scale, use the Python OpenAI SDK, load a prompt template, interpolate subject-specific variables, pass a consistent style-reference image, and log every generation with its prompt and image ID. This is the industrial workflow.

6. **"Generate 6, keep 1" curation.** Non-negotiable. Every asset concept gets 6 generations; you pick one. Budget cost and time accordingly — see §7.

### The style bible document (what we write once, reference forever)

Create `C:\Users\kevin\Downloads\Sports Website\docs\VISUAL_STYLE_BIBLE.md` with exactly these sections:

1. **Palette** — hex codes for every color, including which are "ink" colors (can be used for shapes) vs "paper" (background only) vs "data ink" (team colors, restricted use). `#0B0F14 / #F3EEE4 / #E0A300 / #B7281D / team colors as data ink only.`
2. **Paper & texture** — `#F3EEE4` bone, subtle fiber texture (approximate Mohawk Loop Antique Vellum), 45° halftone at 71 LPI when we simulate riso, tiny registration offset 1-2mm on multi-color riso pieces.
3. **Line discipline** — 2px uniform stroke for ligne claire, no hatching, flat fills, butt caps, 1px corner radius max.
4. **Typography in images** — when text appears inside an illustration, it must be our licensed display face only; no generic AI sans-serif.
5. **In / out list** — explicit allow/deny. Example: *In: warm muted palette, visible paper fiber, small registration offset, 45° halftone, hand-drawn quality. Out: gradients, metallic/chrome, photorealism, gradients, drop shadows, glow/bloom, "trending on artstation" lighting, hyperreal skin texture, real-person likenesses, team logos as trademarks.*
6. **Content rules** — no real player or coach faces, ever. Obscured features, from behind, silhouettes, or archetypal composites only.
7. **Prompt template** — the reusable prefix block (Part 3).
8. **Rejection triggers** — specific visual cues that auto-fail a generation (AI-slop smoothness, symmetric composition, centered default, etc.).

This bible is a living doc. You update it when you reject 3+ consecutive images for the same reason.

---

## Part 3 — Ready-to-use prompt templates

These are the exact phrasings to start with. Expect to refine over the first 20 generations per family; the shapes below are tested starting points distilled from the OpenAI cookbook and working illustrator templates.

### Style prefix block (every prompt starts with this)

```
EDITORIAL STYLE: warm bone-cream paper background #F3EEE4 with visible
paper-fiber texture. Muted limited palette: warm ink #0B0F14, amber accent
#E0A300, deep alert red #B7281D. Hand-made print-era feel. No digital
shine, no gradients, no drop shadows, no chrome, no photorealism, no glow.
Composition off-center with negative space. Think: New Yorker spot
illustration, Field Notes Quarterly cover, mid-century editorial print,
letterpress imperfection.

NEGATIVE (avoid): glossy, shiny, hyperreal, 3D render, trending on
artstation, symmetric, centered, sports-mascot cartoon, generic team logo,
real player faces, corporate vector illustration, AI-smooth skin.
```

### Template A — Risograph cover art (use with Midjourney v7)

```
[prefix block]

SUBJECT: [one-line editorial argument — e.g. "Florida State's anxious
dynasty, a stone crown crumbling on an empty bleacher"]

MEDIUM: 2-color risograph screenprint on warm uncoated paper. Visible 45°
halftone dot pattern. Slight 1-2mm registration offset between ink layers.
Grainy ink texture. Pantone Federal Blue + Fluorescent Pink color layers,
or Black + Sunflower, or Teal + Bright Red (pick one pair per piece).
Amber accent detail.

COMPOSITION: single strong silhouetted subject, off-center, large negative
space for masthead overprint at top. 4:5 portrait aspect.

--sref [locked season style URL] --sv 6 --ar 4:5
```

### Template B — Archetype totem (ligne claire, use with gpt-image-1.5)

```
[prefix block]

SUBJECT: a single symbolic object that represents [archetype name]. The
object is [specific noun: a crumbling stone crown / a weathered pennant /
a toppled statue / a sapling growing through a bleacher crack / etc.].
No humans. No faces. No team logos. Just the object on bone paper.

MEDIUM: ligne claire illustration. Uniform 2px black ink contour line.
No hatching, no cross-hatching. Flat local-color fills only. Every
element rendered with equal line precision, foreground and background.
Hergé / Chris Ware discipline. Clean silhouette legible at 40px.

AMBER: one small amber #E0A300 detail somewhere (a tag, a stripe, a glint).

COMPOSITION: object centered on paper with ~20% margin. Front or 3/4
view. Square 1:1 aspect for icon use.
```

Reference image: upload `totem_master_plate.png` (your first successful totem, used as style anchor on every subsequent generation).

### Template C — Halftone editorial portrait (anonymous fan archetype)

```
[prefix block]

SUBJECT: anonymous archetypal portrait — [e.g. "a middle-aged man in a
threadbare college football scarf, viewed from behind, facing away from
camera, shoulders slumped"]. NO VISIBLE FACE. The subject is a type, not
a person. Possible approaches: viewed from behind, profile shadow with
hat brim obscuring face, hands on clipboard instead of face, silhouette
against stadium lights, figure in fog.

MEDIUM: Wall Street Journal-style hedcut. Stipple dots and short
directional hatching only. No continuous contour lines for shadow.
1,500-3,000 individual marks. High contrast. Plain bone-paper background.
Reads correctly at 120px thumbnail.

AMBER: one subtle amber accent (scarf stripe, hat piping, program in hand).

COMPOSITION: bust crop, 3/4 rear view, off-center right with negative
space at left for editorial caption overprint. 3:4 aspect.
```

Reference image: upload `hedcut_master_plate.png`.

### Template D — Ligne-claire section rubric icon (for N° 01, N° 02 section headers)

```
[prefix block]

SUBJECT: a single small icon representing [section theme — e.g. "mood",
"hype", "rivalry", "lexicon", "commiseration"]. One object, zero humans.

MEDIUM: ligne claire, 2px uniform black ink contour only. NO fill. Pure
line drawing on bone paper. 32×32px target render size. IBM Carbon icon
discipline — 2px stroke, 2px corner radius, strokes snap to pixel grid.
Silhouette legible at 16px.

AMBER: one amber #E0A300 dot or line accent — never more than 10% of the
icon's visual weight.

COMPOSITION: centered on square paper. 1:1 aspect. Clear edges, no
bleed.
```

Consider: for icons specifically, hand-drawing in Illustrator will likely be faster and higher quality than fighting the AI. Budget one afternoon, draw 24 icons, done.

### Template E — Rivalry coin (recommended: human illustrator)

If you still want to try AI:

```
[prefix block]

SUBJECT: a two-sided circular medallion mark for [rivalry name — e.g.
"The Iron Bowl"]. Obverse shows [symbolic detail — e.g. "houndstooth
pattern cap above crossed burnt-orange boxing gloves"]. Reverse shows
[team mascot symbols, not logos]. Designed like a vintage sports
championship coin or a Field Notes enamel pin.

MEDIUM: flat vector-style illustration on bone paper. Two-color
screenprint aesthetic. Beveled circular edge, no realistic 3D rendering.

COMPOSITION: single circular coin centered, 1:1 aspect. Obverse and
reverse side-by-side in separate circular frames. Tiny typographic
labels above each in condensed caps.
```

Honestly: skip this and pay Malika Favre, Andrew Kolb, or a similar illustrator $150/coin. 12 coins = $1800, evergreen, nothing beats it.

### Template F — Commiseration cartoon (New Yorker panel style, Midjourney v7)

```
[prefix block]

SUBJECT: single-panel editorial cartoon. Scene: [specific micro-scenario —
e.g. "a devastated fan in the stands reading a statistics printout,
other fans streaming past him toward the exits"]. The joke is in the
situation, not in exaggerated expressions. Specific, pointed, never mean.
Human figures but no recognizable faces — use distance, angle, or crop
to obscure.

MEDIUM: single-panel New Yorker-style cartoon. Loose ink brush line.
Light grey wash for shadow. Small caption space at bottom (we'll add
type separately). Avoid contemporary digital-illustration feel.

COMPOSITION: wide landscape 16:9, single scene, clear narrative read
left-to-right, space at bottom for caption.

--sref [locked cartoon style URL] --sv 6 --ar 16:9
```

### Template G — Field-notes marginalia (recommendation: not AI)

Build one real handwriting face via Calligraphr ($5/mo, writes-your-own-handwriting workflow) using either your actual handwriting or a commissioned hand. Use it as a webfont in margins. Every "handwritten note" becomes a span of HTML styled in that face. Zero per-image generation, infinite consistency, feels more human.

---

## Part 4 — Use direct-API assets wherever possible

This is the part most AI-first thinking misses. **We already pay for CollegeFootballData (CFBD) and we already work with ESPN's CDN. They have real, licensed, canonical team assets. Use them.**

### What CFBD's API provides

The CFBD REST `/teams` endpoint and their GraphQL schema expose:

- `color` and `altColor` (team primary + secondary hex codes — already in our data model)
- `logos[]` (array of logo image URLs — multiple variants)
- `images` (GraphQL schema — includes helmet images in some cases)
- `mascot` (name string, useful for prompt interpolation)
- `conference`, `division`, `classification`

Our existing `clients/cfbd.py` doesn't currently have a `get_teams` method but the endpoint exists. **Action: add `get_teams()` to `clients/cfbd.py` and an ingest pass to `ingest/` that pulls logos and helmets into a local cache.** That gives us canonical team assets without generating anything.

### ESPN CDN — free team logo URL pattern

ESPN's undocumented CDN uses predictable URLs:

```
https://a.espncdn.com/i/teamlogos/ncaa/500/{team_id}.png
https://a.espncdn.com/i/teamlogos/ncaa/500-dark/{team_id}.png
https://a.espncdn.com/i/teamlogos/ncaa/scoreboard/{abbrev}.png
```

And the team endpoint:

```
http://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{team}
```

Returns team metadata including logos, colors, and sometimes helmet imagery. No auth required. Unofficial so treat as best-effort, but it's been stable for a decade. Good fallback when CFBD is missing a logo variant.

### Assets we should NEVER generate with AI

Hard rule. These always come from APIs or licensing, never from gpt-image-1 / Midjourney:

- **Team logos.** They're trademarks. AI versions would be wrong *and* legally problematic. Use CFBD `logos[]` + ESPN CDN.
- **Conference logos.** Same.
- **Helmet graphics for real teams.** Use real helmet photography (ESPN CDN, team media sites) rendered behind a halftone SVG filter to match our visual language — *or* commission a photographer for a one-day shoot of 133 helmet macros if you want true ownership.
- **Real player faces or coach faces.** Ever. No exceptions. Use archetypal composites (Template C) for editorial portraits.
- **Stadium photography.** Use wire-service photography under appropriate licensing (AP, Getty, etc.) or commission.
- **Scoreboards, statlines, any factual data viz.** These are our typographic tables, not images.

### The hybrid stack

```
Real assets (CFBD / ESPN / licensed)      AI-generated (ChatGPT / Midjourney)      Human-commissioned
─────────────────────────────────          ───────────────────────────────          ──────────────────
Team logos                                  Archetype totems (18)                    Rivalry coins (12)
Helmet images                               Weekly cover art (47/yr)                 Custom display face
Team colors                                 Editorial portraits (anonymous types)    Handwriting face
Conference marks                            Commiseration cartoons (47/yr)           One premium cover / season
Stadium photography (licensed)              Section rubric icons (optional)
Player photos (don't use)                   Decorative marginalia graphics
```

This split is what actually produces world-class. Pure AI output lacks legal and aesthetic ground; pure commissioning bankrupts the project; the mix wins.

### Proposal: add an `assets.py` layer

Create `src/cfb_rankings/visual_assets.py` with:

```python
# Pseudocode outline
class AssetRegistry:
    def team_logo(self, team_slug: str, variant: str = "primary") -> str:
        # 1. Look up cached CFBD logo
        # 2. Fall back to ESPN CDN
        # 3. Fall back to a generic helmet glyph
        ...

    def team_helmet(self, team_slug: str) -> str:
        # ESPN CDN helmet URL
        ...

    def archetype_totem(self, archetype_key: str) -> str:
        # Local path to curated AI-generated PNG
        # e.g. /assets/images/totems/anxious-dynasty.png
        ...

    def rivalry_coin(self, rivalry_key: str) -> str:
        # Local path to commissioned SVG
        ...

    def cover_art(self, issue_number: int) -> str:
        # Local path to that week's cover
        ...
```

Every template in `reporting.py` calls this registry instead of hardcoding paths. Swap a totem by replacing the file, regenerate site, done.

---

## Part 5 — Systematic ChatGPT production workflow

Concrete step-by-step for producing assets at scale.

### Option 1 — Custom GPT workflow (best for low-volume / manual curation)

1. In ChatGPT, create a new Custom GPT called "CFB Index Art Director."
2. System prompt: paste the entire `VISUAL_STYLE_BIBLE.md` (palette, paper, line discipline, in/out list, prompt prefix block, rejection triggers).
3. Knowledge files: upload `totem_master_plate.png`, `hedcut_master_plate.png`, `riso_master_plate.png`, and any previously-approved examples.
4. Workflow per asset:
   - "Generate the archetype totem for [Anxious Dynasty]. Reference the master plate for style."
   - It returns 4 images. Pick one.
   - "Generate 4 more like #2 but with [specific adjustment]."
   - Save the winner to `/assets/images/totems/anxious-dynasty.png`.
   - Add a `.prompt.md` sidecar with the exact prompt used and why you picked it.

This is how you'll do 80% of the work. It's slow but produces the best editorial quality because you're in the loop.

### Option 2 — OpenAI API batch workflow (for scale + reproducibility)

When you have a batch of 20+ assets to generate (e.g. seeding all 18 totems in one sitting):

```python
# pseudocode
from openai import OpenAI
from pathlib import Path
import json, time

client = OpenAI()
STYLE_PREFIX = Path("docs/style_prefix.txt").read_text()
REFERENCE = Path("assets/masters/totem_master.png")

def generate(subject_brief: str, out_path: Path, ref: Path = REFERENCE, n: int = 6):
    prompt = f"{STYLE_PREFIX}\n\nSUBJECT: {subject_brief}"
    result = client.images.edit(
        model="gpt-image-1.5",
        image=ref.open("rb"),
        prompt=prompt,
        n=n,
        size="1024x1024",
        quality="high",
    )
    for i, img in enumerate(result.data):
        (out_path.parent / f"{out_path.stem}_candidate_{i}.png").write_bytes(img.b64)
    # write sidecar with prompt
    (out_path.parent / f"{out_path.stem}.prompt.md").write_text(
        f"Prompt:\n\n{prompt}\n\nReference: {ref}\n\nModel: gpt-image-1.5\nGenerated: {time.ctime()}"
    )

BATCH = [
    ("anxious-dynasty", "a crumbling stone crown sitting on weathered bleachers, ivy creeping up the base"),
    ("perpetual-believer", "a faded NEXT YEAR pennant thumbtacked to a splintered bleacher plank"),
    # ... 16 more
]
for key, brief in BATCH:
    generate(brief, Path(f"assets/totems/{key}.png"))
```

Use OpenAI's Batch API (50% discount, 24hr async) for cost savings on large runs. Review all candidates in a grid, promote the winner to the final filename.

### The 7-field prompt template (paste into every sidecar)

Every final image gets a `.prompt.md` next to it:

```
# {filename}

## One-line brief
{e.g. "The crumbling stone crown of an anxious dynasty"}

## Visual family
{ligne-claire-totem | riso-cover | hedcut-portrait | cartoon-panel | ...}

## Full prompt
{the exact prompt used}

## Reference images
- {master plate used}
- {any additional references}

## Model + settings
{gpt-image-1.5, 1024×1024, quality=high, seed=N}

## Selection rationale
{why this variant won — e.g. "registration offset felt most print-era,
amber detail read correctly at thumbnail size"}

## Rejection notes
{what I rejected from the other 5 candidates — e.g. "candidate 3 had
AI-smooth rendering on the crown ivy; candidate 5 was too centered"}
```

This is your institutional memory. In 6 months when you want to regenerate a variant or pass the work to someone else, it's all here.

### Curation discipline — the "generate 6, keep 1" rule

Non-negotiable. Budget numbers for planning (at $0.04/image for gpt-image-1.5):

- 18 archetype totems × 6 candidates = 108 generations × $0.04 = **$4.32**
- 47 weekly covers × 6 = 282 × $0.04 = **$11.28** (or free-ish on Midjourney $30/mo)
- 47 commiseration cartoons × 6 = 282 × $0.04 = **$11.28** (or on Midjourney)
- 60 editorial portraits (archetypal fans across the year) × 6 = 360 × $0.04 = **$14.40**
- 24 section rubric icons × 6 = 144 × $0.04 = **$5.76**

**Annual OpenAI image budget ≈ $50-100** if we use it for everything, less if we split with Midjourney ($30/mo = $360/yr). Rounding error on the project.

Throughput: a disciplined session with the Custom GPT workflow produces 4-6 final approved assets per hour. Scaling the 90-day plan in Part 6:

- Days 1-7: lock the style (10 hours)
- Days 8-21: ship 18 totems + 12 rivalry coins + icon set (~25 hours)
- Days 22-45: ship covers + cartoons at the weekly cadence while the season opens (~3 hrs/wk)
- Day 46+: recurring operating cost ~4 hours per weekly issue for art

### Failure modes the pipeline catches

- **Drift** — monthly, render a 4×4 grid of all approved totems. If they don't feel like one set, something drifted. Regenerate the outliers against the master plate.
- **Slop creep** — quarterly, re-read the rejection folder. If the rejections are looking like the approvals, the eye has drifted. Reset by pulling fresh reference from your inspiration folder (New Yorker covers, Field Notes quarterlies, Businessweek archive).
- **Scope ratchet** — when you feel the urge to add a new visual family (say, "we need isometric diagrams now"), resist for one full issue cycle. Most scope creep is vibes, not need.

---

## Part 6 — The first 90 days, tactically

### Days 1-7: Lock the style

- Day 1-2: write `VISUAL_STYLE_BIBLE.md` (Part 2's 8-section spec).
- Day 3: build the Custom GPT "CFB Index Art Director" with bible + references.
- Day 4: generate 6 candidates for Anxious Dynasty totem. Pick one. This is your **master plate for ligne-claire totems.** Save to `assets/masters/totem_master.png`.
- Day 5: repeat for halftone portraits (one anonymous-fan portrait) → `hedcut_master.png`.
- Day 6: spin up Midjourney v7, generate 6 riso cover candidates. Pick one. Get its style ID via Style Creator. This is your **season `--sref` URL**. Save.
- Day 7: review all three masters side-by-side with the amber accent present. If they read as one magazine, ship. If not, iterate.

### Days 8-21: Ship Tier 1 (archetype totems + rivalry coins + icons)

- Days 8-11: 18 archetype totems using the ligne-claire master. Budget ~3 hours/day, 6 totems/day. One `.prompt.md` per winner.
- Days 12-14: commission the 12 rivalry coins from a human illustrator. Contract, brief, pay.
- Days 15-18: 8 modifier glyphs using the totem master.
- Days 19-21: section rubric icons. Consider hand-drawing these in Illustrator instead. 24 icons, one afternoon.

### Days 22-45: Weekly operating rhythm starts

- Each Monday: sketch the week's editorial brief. What's the cover argument?
- Monday/Tuesday: generate 6 cover candidates on Midjourney, pick one.
- Wednesday: generate 6 commiseration cartoon candidates, pick one.
- Thursday: any new archetypal portraits needed for the week's stories.
- Friday: publish.

Total weekly art time: ~4 hours once the rhythm is locked.

### Days 46-75: Depth layer

- Build the ESPN CDN + CFBD ingest for team logos/helmets into `visual_assets.py`.
- Commission the custom display face (long lead time — start now). Lucas Sharp, James Edmondson, or David Jonathan Ross. $5-15k.
- Build the Calligraphr handwriting face for marginalia.
- Hire a photographer for one day of helmet macros if budget allows (~$2-3k for 133 helmets of your flagship teams + conferences).

### Days 76-90: Polish and registry

- Finalize `visual_assets.py` and wire it through `reporting.py`.
- Quarterly moat ledger review.
- Rejected-folder review.
- Write the first annual Preseason Almanac ritual treatment for the next August issue.

---

## Part 7 — Six decisions I need from you

Listed in order of urgency. Each one blocks something downstream.

**1. Which visual family leads?** Recommendation: **risograph covers + ligne-claire totems + halftone portraits** (the three-family split in the concept doc). If you want single-family: **ligne claire** (safest at all sizes, cheapest to produce, most ownable). If you want maximalist: keep all three. *My bet: all three, split by asset class.*

**2. Midjourney or gpt-image-1.5 as primary?** Recommendation: **both — Midjourney for covers + cartoons, gpt-image-1.5 for totems + portraits + icons.** ~$30/mo Midjourney + ~$50-100/yr OpenAI. Total art stack cost: ~$500/yr.

**3. Commission a human illustrator for rivalry coins?** Recommendation: **yes, $1500-3000 one-time for 12 evergreen assets that AI can't do this well.** The ROI is overwhelming.

**4. Commission a custom display face?** Recommendation: **yes, eventually.** This is the most durable moat in editorial publishing. $5-15k, long lead time (3-6 months). Start conversations now; ship in year 2.

**5. Who is the gatekeeper?** This is non-optional. Someone must say yes/no on every published image against the bible. *If it's you, commit time. If you want to delegate it, I can draft a reviewer rubric so a second person could run it against clear criteria.* But one human is final, not a team.

**6. FCS / D-II / D-III scope?** Recommendation: **skip.** 133 FBS is already a huge scope. Non-FBS teams get a generic "unaffiliated" treatment or a text-only card. Revisit in year 2 if there's demand.

---

## Part 8 — Risk register

Per the CLAUDE.md pattern — risks we're running, with specific defenses.

| Risk | Probability | Defense |
|---|---|---|
| AI-slop creep across the year | High | Monthly 4×4 grid review; rejected folder discipline |
| Style drift when a new asset class is added | Medium | Require a master plate before generating any new family |
| Over-commissioning / scope explosion | Medium | Hard cap: ≤15 new assets/week in months 1-2, ≤8/week after |
| Trademark issues from AI-generated logos | Low (if we follow the rule in Part 4) | Never generate team logos with AI. Period. |
| Licensing shift in OpenAI's content policy | Medium | Keep all reference images and prompts local; migrate to Midjourney/open models if needed |
| Losing the gatekeeper (you, unavailable) | Certain at some point | Document the bible well enough that a backup reviewer can run it |
| Illustrator unavailability for coin commissions | Medium | Have a list of 3 acceptable illustrators, not 1 |
| AI "catches up" and generates world-class art at scale | Certain | Good — it makes our moat the editorial voice, not the production technique. We're hedged because our moat is the *argument* behind each image, not the image itself |

---

## Part 9 — The synthesis sentence

One paragraph, try to remember this more than the 12,000 words above:

*The CFB Index visual identity is a single gatekeeper applying a written bible to a mix of human-commissioned foundations (custom display face, 12 rivalry coins, handwriting), AI-generated editorial production (totems via gpt-image-1.5 with reference images, covers via Midjourney with locked sref, cartoons via Midjourney), and canonical real-asset APIs (CFBD + ESPN CDN for team logos, colors, helmets), all unified by bone paper #F3EEE4, amber #E0A300, three compositional templates, and the three-voice typographic spine. We never generate team logos, real faces, or anything factual. Every image makes an argument, not a headline. Every image sits in the same frame. The moat is the editorial voice we've built over 47 issues a year for three years; everything else is production technique anyone could copy.*

---

## Part 10 — Sources and long-form notes

Primary research for this playbook:

- The New Yorker's commissioning process — Françoise Mouly's *Blown Covers* (2012), Tom Bachtell's Talk of the Town tenure (1995-2017), João Fazenda's successor era. Mouly's "ten roughs, no finish" methodology is the operative lesson.
- Bloomberg Businessweek — Richard Turley (2010-2014) and Rob Vargas (2014-present) interviews at Brand New Conference and elsewhere. Three cover modes (typographic / conceptual object / commissioned illustration).
- The Economist — the Monday meeting / Thursday illustration / Friday print cadence. KAL, Noma Bar, Jon Berkeley as the rotating short list. The "visual argument, not visual headline" brief.
- Wall Street Journal hedcut tradition — Noli Novak and the dedicated hedcut team, 1979-present. Stipple-and-hatching discipline, 1,500-4,000 marks per portrait.
- Monocle — the 15+ illustrators-per-issue model, typography-as-spine coherence.
- Field Notes Quarterly — the format-as-ritual lesson; consistency through same-dimension / varying-paper editions.
- Defector and The Ringer — proof that punk-zine aesthetics and clean portrait illustration can both work if applied consistently.
- Identity collapses — Sports Illustrated post-2019, Newsweek post-Tina Brown, Wired post-Dadich, Fast Company mid-2010s, BuzzFeed News, Deadspin pre-Defector. All lessons in what not to do.
- Ligne claire rules — Benoît Peeters' *Hergé, Son of Tintin* (2012) and the Hergé Foundation's public style documentation.
- Icon system discipline — IBM Carbon icons documentation, Google Material Symbols, Phosphor Icons, Streamline Icons rule sets.
- Prompt engineering for consistency — OpenAI's [GPT Image Generation Models Prompting Guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), OpenAI community forum threads on DALL-E 3 series consistency, Midjourney Style Reference documentation.
- Pricing as of April 2026 — [OpenAI API Pricing](https://openai.com/api/pricing/), [costgoat OpenAI images calculator](https://costgoat.com/pricing/openai-images). gpt-image-1.5 ≈ $0.04/image standard; gpt-image-1-mini ≈ $0.005/image; Batch API 50% discount.
- Model capability claims — [MindStudio model comparison 2026](https://www.mindstudio.ai/blog/imagen-2-vs-gpt-image-1-5-vs-midjourney-2026); Midjourney remains aesthetic quality leader, gpt-image-1.5 has reference-image strength and conversational context.
- Reference-image support — [OpenAI API image generation guide](https://developers.openai.com/api/docs/guides/image-generation) confirms up to 16 input images per edit call.
- CFBD team data — [CollegeFootballData.com API](https://api.collegefootballdata.com/) and [GraphQL schema](https://graphqldocs.collegefootballdata.com/) expose `color`, `altColor`, `logos[]`, `images`, `mascot`.
- ESPN CDN team logos — [pseudo-r/Public-ESPN-API](https://github.com/pseudo-r/Public-ESPN-API) and [akeaswaran hidden API docs](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b) for URL patterns.

Research agent long-form synthesis (editorial identity systems deep dive) is available on request — the condensed rules in Part 1 are the operational distillation.

---

*Last updated: 2026-04-22. This is a living document. Update the bible when you reject three images in a row for the same reason.*
