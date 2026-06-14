# Curated player blurbs (manual-in-chat spike)

Source-of-truth, version-controlled, human-authored prospective player blurbs.
One JSON per player. Authored in-session by Claude applying the framework in
`docs/design-system/66-prospective-blurb-engine-plan.md` + live web research as of
the file's `as_of_date`. Renderer-agnostic; the render/deploy wire-up maps these to
the player-page story-card slot (`new_story_card_html`) with precedence
**curated > pipeline > legacy**, scoped to an allowlist + kill-switch.

## Schema

```jsonc
{
  "slug": "cj-carr-<PLAYER_ID>",   // canonical site slug (name-PLAYER_ID). Resolve/verify vs DB at wire-up.
  "slug_verified": false,           // set true once matched to a real player_id
  "player_name": "CJ Carr",
  "team": "Notre Dame",
  "position": "QB",
  "as_of_date": "2026-06-12",       // present-day anchor; drives the freshness/regeneration model
  "tier": "tentpole",               // tentpole | feature | standard | minimal
  "story_shape": "free-text label of the blended shape",
  "plan": {                          // the editorial plan the prose was written to
    "spine": "...",
    "blend": ["...", "..."],
    "payoff": "...",
    "forward_stake": "...",
    "register": "projection|imminent|reporting|stakes-peak|transition|reset",
    "horizon": "e.g. 2026 season | 2027-28"
  },
  "hook": "visible ~25-40w grab",
  "expand": "full prose (markdown) -- the NARRATIVE blurb (why he matters, forward); length per tier band, ceiling not target",
  "style_register": "cinematic | descriptive | plain",   // prose ambition by tier (doc 67/68 register ladder)
  "style": "the PLAY-STYLE blurb (how he plays) -- position-native, grounded in real PBP percentiles + attributed scouting; single paragraph",
  "style_layers_pending": "free-text: which deeper layers remain (PBP depth woven in? fan-vs-rival discourse split still pending?)",
  "sources": [ { "label": "...", "url": "..." } ],
  "author": "claude-in-chat (Opus 4.8, framework v1)",
  "status": "draft"                 // draft | approved | live
}
```

## Rules
- `expand` length obeys the tier band (tentpole ~220-260w · feature ~110-160w · standard ~50-90w · minimal ~25-45w); the hook is ~25-40w and always present.
- Attribute bold takes ("fans...", "the market prices..."); never assert house opinion. No NIL hero number.
- Negative/sensitive facts only if verified/official (suspension, charge of record, portal entry, injury) — proportionate; never rumor.
- Forward-looking, framed toward the upcoming season(s) from `as_of_date`. Re-author when a `player_signal_event` (injury, depth-chart, portal, schedule) would change the lead.
- `status: approved` requires owner sign-off before it can deploy.

## Validation (pre-deploy)
`python manage.py validate-curated-blurbs` (to be built, G3): schema, length-band, sources present, as-of freshness, slug resolves to a real player.
