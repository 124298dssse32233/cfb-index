# Curated team blurbs (manual-in-chat spike)

The **team analog** of `data/curated_player_blurbs/`. One JSON file per program
renders a top-of-page narrative **crown** (forward-looking program narrative +
an optional "how they play" identity companion) just under the team-page hero.

Spec: the team Story Card lives in `docs/design-system/50-58`; the shared
method/paradigm is `docs/design-system/68-blurb-method-cross-subject-paradigm.md`
(Part C — cross-subject adaptation). This store is the manual spike that lets a
chat-authored team blurb go **live** without a build of the automated engine.

## How it renders
- Loader: `src/cfb_rankings/team_pages/curated_blurb.py` → `render_curated_team_blurb(slug)`.
- Hook: `team_pages/renderer.py::_render_page` injects `{curated_team_blurb_html}`
  right under the hero / page-tone strip.
- **Match key = team slug** (e.g. `alabama`, `ohio-state`). Teams have no
  numeric id — the slug IS the key. Use the same slug as the team page filename
  (`output/site/teams/<slug>.html`).
- **Default ON**: the file's existence is the gate. A team with no file keeps
  its normal world-class chrome unchanged. Kill globally with
  `CURATED_TEAM_BLURBS=off`.
- **Fail-closed**: a malformed/throwing file renders nothing (never blanks a page).
- Files whose name starts with `_` (like `_EXAMPLE.json`) are **skipped** — use
  that prefix for templates/drafts you don't want live.

## Schema (forgiving — only `hook`/`expand` are required)
```json
{
  "slug": "<team-page-slug>",        // REQUIRED match key, e.g. "ohio-state"
  "team_name": "Ohio State",
  "as_of_date": "2026-06-13",
  "tier": "tentpole | feature | plain",   // sizing hint (free-form, not enforced)
  "hook": "1-2 sentence visible lede — the spine, not a sibling.",
  "expand": "The body narrative. Blank-line-separated paragraphs become <p>s.",
  "identity": "Optional 'how they play / who they are' companion paragraph.",
  "identity_label": "How they play",  // optional; defaults to 'How they play'
  "sources": [ { "label": "...", "url": "https://..." } ],
  "author": "...",
  "status": "approved"
}
```
Extra fields are ignored, so the schema can grow in the design docs (frames,
ledgers, characters, etc.) without breaking this loader. When the automated
team engine lands, it can write the same files.

## Authoring discipline (same as player blurbs)
- **Verify current status** at authoring time (coaching changes, conference,
  roster churn) — the player gate already caught a fired coach + two departures.
- **No hallucinated claims**: every factual assertion should trace to a real
  source (cite in `sources`) or to our proprietary data, framed honestly.
- Length follows the story — don't pad a quiet program to match a blue-blood.
