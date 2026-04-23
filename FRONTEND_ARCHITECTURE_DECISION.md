# Frontend Architecture Decision — Solo Operator, Content Site at Reader Scale

**Author:** Claude, April 2026 · **Status:** Recommendation · **Audience:** Kevin

## The question

CFB Index has a working Python static-site generator producing 17,426 HTML pages from SQLite. Figma Make has produced a beautiful React/Tailwind/Vite prototype of the player page. These are different runtimes. How do we get the design into production without breaking what's working, and what does the system look like at scale (hundreds → thousands of readers)?

## Constraints that actually matter

- **Solo, beginner.** One person maintains everything. Every piece of complexity is a tax on shipping. A stack I can't keep in my head while tired at 9pm is a stack that drifts and breaks.
- **Reader scale is easy.** "Hundreds to thousands of readers" is well within static-HTML territory. A 17k-page static site on Cloudflare Pages / Netlify serves 100K+ reads/day for free. The scaling argument for React-SSR / Next.js / Astro-SSR does not apply at this scale — static HTML wins on every dimension (speed, cost, simplicity, SEO, resilience).
- **The data pipeline works.** The Python generator, SQLite backend, Signature Story engine, and Room-on-Player adapter are live and tested. Rewriting this is pure cost.
- **The Figma prototype is a design spec, not production.** React/Tailwind/Vite was the fastest way to get a visual reference. It was never going to drop into the generator as-is. Treating it as such has caused confusion — including my own when I wrote "Figma will replace the shells" without saying how.
- **Interactivity needs are modest.** Cohort pills, tab bars, drawer open/close, subnav sticky + IntersectionObserver, URL sync, search filter. No complex client state, no real-time, no dashboards. The React prototype's interactivity is an order of magnitude more than production actually needs.

## What I found in the production site

Things you probably already know but worth naming so the plan is grounded:

- Every page inlines a `<style>` block with its own CSS. A single CSS file served from `/assets/` would shave maybe 200KB per page and make design changes instant across the site instead of re-generating 17k pages.
- Production CSS tokens are old-style hex (`#FAFAFA`, `#DC2626`) with Anton/Bebas Neue fonts. The v5 design system uses OKLCH ramps, Inter Display, fluid `clamp()` type. **The visual system itself needs to migrate before any component ports do.**
- `reporting.py` has 126 render functions and 16,412 lines. It's the system of record. Changing it is daily work, but it's orderly — each module renders in a known function.
- Some JavaScript already lives in the HTML (~13 `<script>` / `onclick` references per player page). There's precedent for client-side interactivity; it's not a greenfield JS decision.

## The four paths, honestly

I considered (1) vanilla HTML+CSS+JS, (2) Next.js/React migration, (3) Alpine.js hybrid, (4) Astro.

### Path 1 — Vanilla HTML + CSS + hand-written JS
Keep everything in Python, write interactivity by hand.

- **Pros:** Zero new dependencies. Static HTML ships anywhere. You already know how to write vanilla JS.
- **Cons:** Every interactive pattern is a small hand-written JS module. Cohort pills, tabs, drawers — each becomes bespoke code. State management across modules is manual. URL-sync has to be re-implemented per surface. At 10 modules × 3-5 states each, you're writing ~500 lines of JS.
- **Solo-operator fit:** Workable but tedious. Risk of inconsistency across modules.

### Path 2 — Next.js / React rewrite
Migrate the whole frontend to React + Next.js App Router. Python becomes a data pipeline that writes JSON for Next.js to consume at build time.

- **Pros:** The Figma components drop in almost as-is. Component composition. Hot-reload DX. Standard stack.
- **Cons:** Full frontend rewrite. Steep learning curve (React, Next.js App Router, Server Components, ISR). 15k-page builds can take 10-30 min on Vercel free tier. You now have TWO build systems (Python pipeline + Next.js). Solo maintenance burden roughly doubles.
- **Solo-operator fit:** Poor for a beginner. High probability the project stalls during the migration. The payoff (better DX) is real but doesn't translate to the end-user.

### Path 3 — Alpine.js progressive enhancement on top of the Python generator
Python still generates HTML. Alpine handles the interactive bits via HTML attributes (`x-data`, `x-show`, `x-on:click`). ~14KB runtime, no build step, no ecosystem. CSS migrates to a single external stylesheet using v5 tokens.

- **Pros:** Keeps the Python generator intact. Alpine's syntax is declarative and HTML-native — the learning curve is ~30 minutes. All 10 modules' interactive needs are trivially expressible in Alpine. Static HTML + tiny JS — the site stays free to host at any reader scale. You can port one module at a time; live site never breaks.
- **Cons:** Not as "componenty" as React. You're still writing Jinja-equivalent templates in Python strings. Alpine's ecosystem is smaller than React's — if you ever want a rich datagrid, you build it yourself.
- **Solo-operator fit:** Excellent. Minimum viable complexity for the interactivity needs.

### Path 4 — Astro with Python as data source
Python exports JSON from SQLite; Astro consumes it at build time, can embed React islands where needed.

- **Pros:** Component authoring. Islands architecture ships zero JS by default. Can import the Figma React components directly for interactive modules.
- **Cons:** Full frontend rewrite from Python strings → Astro components. Another build system to learn (Astro-specific patterns, islands, client directives). Your reporting.py work becomes JSON-export-only, which is a downgrade in expressiveness. Pelican or another Python-native SSG would have a smaller learning curve but a bigger migration.
- **Solo-operator fit:** Tempting because of islands, but the migration cost is still real. Not as bad as Next.js, but not as cheap as Alpine.

## Recommendation: Path 3 (Alpine + static HTML + external CSS), executed in stages

This is the right answer for a solo operator at your scale and skill level. It keeps what works, adds minimum new machinery, and gets the v5 design into production without rewriting anything that already ships.

The React prototype stays as the design source of truth. You deploy it to Vercel once as a living spec (useful for anyone who ever helps you, or for you when you're tired and need to see "what should this feel like"). It's not production.

## The staged plan

Each stage is a commit. Live site never breaks — if a stage is half-done, the old version still renders.

### Stage 0 — Pre-flight (1 day)
- **Extract inline `<style>` into one file** at `output/site/assets/cfb-index.css`. Every page `<link>` it. This alone is a cleanup win independent of anything else — turns 17k inline style blocks into one cached file.
- **Add a page-level `<script src="/assets/alpine.min.js" defer></script>`** via `reporting.py`. Pin to Alpine 3.x. ~14KB gzipped.
- **Commit.**

### Stage 1 — Token migration (1-2 days)
- **Introduce v5 OKLCH tokens** alongside the existing hex tokens in `cfb-index.css`. Both systems coexist temporarily.
- **Port the typography tokens first** (`--fs-display/h1/h2/body/meta` via `clamp()`). Apply to one page as a test — say, the methodology page.
- **Port the color tokens** (percentile ramp, belief ramp, accolade gold, neutral scale). Map old hex usages to the new tokens one visual region at a time.
- **Retire the old hex tokens** once no rule references them.
- **Commit per region:** topbar, footer, navs, then per-module.

This is the unglamorous work that unblocks everything. Skip it and every module port fights the old system.

### Stage 2 — First module port (Signature Story) (1 day)
- **Rewrite `_render_algorithmic_signature_card` in `reporting.py`** to emit the v5 component's HTML structure. Signature Story has no interactivity — it's just semantic markup with the tokens you just defined.
- **Compare side-by-side:** old page (with old minimal shell) vs new page (with v5 structure). Ship when visually correct.
- **Commit.**

One module down, nine to go. Stage 3 is the same pattern.

### Stage 3 — Port the non-interactive modules (Current Season Production, Supporting Cast) (1-2 days)
- Same pattern as Stage 2. These are purely data-display, no JS needed.

### Stage 4 — First interactive module (The Room on [Player]) (1-2 days)
This is where Alpine earns its seat.

The Room needs cohort-pill state (`own` / `rival` / `national` / `media`), derived dial/trajectory/quote per cohort. The entire thing is ~40 lines of HTML + Alpine:

```html
<article class="the-room" x-data="{ cohort: 'own', cohorts: {{ cohort_data_json }} }">
  <div class="cohort-pills" role="tablist">
    <template x-for="(data, id) in cohorts" :key="id">
      <button type="button"
              :class="cohort === id ? 'pill--active' : 'pill'"
              :aria-pressed="cohort === id"
              @click="cohort = id">
        <span x-text="data.label"></span>
      </button>
    </template>
  </div>
  <div class="belief-dial">
    <div class="dial-fill" :style="`width: ${cohorts[cohort].score}%`"></div>
  </div>
  <blockquote x-text="cohorts[cohort].topQuote"></blockquote>
</article>
```

Python serializes the per-cohort data as JSON; Alpine reactively renders it. That's the whole pattern. Repeat for every interactive module.

### Stage 5 — Port remaining interactive modules (Standing, Splits, Bio, Peers, Savant, Hero, Subnav) (1 week)
- Each module in its own commit.
- URL sync via a tiny shared Alpine helper that reads/writes `window.location.search` on state change.
- IntersectionObserver for the Subnav is plain JS (~20 lines) wired via Alpine.

### Stage 6 — Retire old code (1 day)
- Remove old render functions that are fully replaced.
- Confirm no references to old hex tokens remain.
- Lock `cfb-index.css` as the canonical system; any future design changes update it, not inline styles.

## Total effort: ~2 weeks of focused solo work

- Stage 0: 1 day
- Stage 1: 1-2 days
- Stages 2-3: 2-3 days
- Stages 4-5: 1-2 weeks
- Stage 6: 1 day

No stage is blocking. You can pause between modules without breaking the site. Each commit is independently shippable.

## What the React prototype is FOR after this

- **Design canon.** When you're porting a module and wondering "is this spacing right?" — open the React prototype.
- **Design review for future modules.** Figma Make keeps producing React; you use it the same way you have been. It's a faster design loop than iterating in Python strings.
- **Contractor handoff reference.** If you ever hire help, the React prototype communicates the design spec in one afternoon. Way better than reading `reporting.py`.
- **Your personal visual QA tool.** Run the React prototype locally, compare live site against it. Any drift is a bug.

Deploy the React prototype to Vercel at something like `design.cfbindex.com` (or just a Vercel preview URL you save). It lives there. Forever. It's not production.

## Why not Alpine + existing Python generator later, once you have users?

You could punt this entire decision. Keep the current hex-token CSS, the inline styles, the minimal HTML shells. Ship like that. Figure out architecture when you have a reader complaint.

Honest counter-argument: the token migration is a prerequisite for ANY future design change. Every month you delay is compounding visual drift. And the inline-style-per-page pattern actively hurts cacheability and time-to-interactive right now, at zero readers, in a way you'll never get credit for fixing later but will get blamed for if you don't.

Fix the CSS migration in Stage 0-1 regardless of whether you do Path 3 the rest of the way. It's the cheapest user-visible win on the table.

## Things I'm less sure about and would flag

- **Font loading.** Inter Display isn't free on your domain today — the v5 prototype uses Inter Display at CDN. You'll need to decide: serve `font-display: swap` from Google Fonts (easy, ~1 HTTP request, works today), or self-host in `/assets/fonts/` (faster, more control, takes an hour to set up the correct subsetted woff2s). I'd self-host. But Google Fonts is fine for v1.

- **Dark mode default.** The v5 system is dark-mode first. Production today is light-mode. Switching the default is a real change to every page's visual identity. I'd do this intentionally: in Stage 1, set dark mode as the `<html>` default with a light-mode override class for whoever prefers it, and respect `prefers-color-scheme`. But don't do it silently — it's a visible moment in the product's identity and you should own it.

- **Analytics / reader counts.** Once you have readers, you'll want to know what they do. Plausible or Umami (both self-hostable, privacy-first, cheap) are good defaults. Skip Google Analytics — it's cumbersome for what you'll actually use. Don't worry about this until you have 50+ daily readers.

- **Deployment.** You haven't named a host yet. Cloudflare Pages is free for static sites of any size with unlimited bandwidth, and has the best edge network of the free options. Netlify and Vercel are good but have stricter free-tier bandwidth caps. For a content site at your scale, Cloudflare Pages is the right answer. Setup is 15 minutes.

## The one sentence

Keep the Python generator, add Alpine for interactivity, migrate CSS to v5 OKLCH tokens in one external stylesheet, port modules one at a time from the React reference — and the React prototype becomes your permanent design spec rather than your production code.
