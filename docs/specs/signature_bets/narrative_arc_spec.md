# Narrative Arc Board — spec (S3.4 / §4 Bet #14)

**Purpose.** A 3-act synopsis of the player's season — opinionated,
editorial, short. Tells a story where most sites show only stats.

## 3-act structure

Every arc carries exactly three acts; voice rules per brief §2:

- **Act I — Discovery**  (Weeks 1-4, usually)
- **Act II — Ascent / Adjustment**  (Weeks 5-9)
- **Act III — Coronation / Crisis / Closure**  (Weeks 10+)

Each act has:
- `title`: one of the canonical titles above, or a 1-3 word custom
  headline (e.g. "Crisis of Confidence" for a decline arc).
- `week_range`: "Weeks 1-4" format.
- `inflection`: a single-game inflection moment — "The Texas A&M game
  was the inflection: 3 TDs, 88th pct pressure EPA."
- `synthesis`: 1-2 sentences describing what the act MEANT.

Total arc card is ≤ 12 lines of body copy. Any longer and it reads
like an essay.

## Voice rules (§2 brief)

- Declarative. No hedging ("in some ways"). Own the take.
- No exclamation points, no "generational/insane/special".
- Each act ends on a period, never an ellipsis.
- Never narrates what the player felt or thought. We describe what
  happened + what it meant. Psychology stays off the page.

## Hand-authored top-N + auto-gen gate

**V1 scope**: hand-authored seeds in `seeds/narrative_arcs.yaml` for a
curated set (Carr, Mendoza, a few others). Players outside the seed
render the empty-state card: "Arc lights up when the editorial pass
covers this player, or when the auto-generator clears its confidence
gate."

**V2 scope** (follow-up): auto-generator reads signature_story +
achievements + week-by-week stats, generates a draft arc, applies a
confidence gate (signature_story.has_story + achievements_count >= 2),
and writes to the same seed-shaped cache. A `flag-for-review` column
defaults True — nothing renders auto-gen'd until an editor clears it.

The module is designed so hand-authored and auto-gen paths write to
the same fetch interface — flipping a player from auto to manual is a
YAML edit, not a code change.

## Data model

Seed file (YAML):
```
arcs:
  "4788":                       # player_id
    player_name: CJ Carr
    season: 2025
    acts:
      - title: Discovery
        week_range: Weeks 1-4
        inflection: "The Miami game was the inflection: 221 pass yds in a 24-27 loss that set the season's tone."
        synthesis: "From preseason question mark to verified starter…"
      - ...
```

No database schema today; the YAML-first pattern matches coaching
lineage (S2.9). A future migration adds a `player_narrative_arcs`
cache table for auto-gen.

## Rendering

Three-column card (or stacked vertical on mobile). Each column carries
the title, week range, inflection (styled italic), and synthesis.

```
<article class="narrative-arc" data-module="narrative-arc" data-state="ready">
  <p class="narrative-arc__eyebrow">2025 Season in 3 Acts</p>
  <div class="narrative-arc__acts">
    <section>
      <h3>Act I — Discovery</h3>
      <p class="meta">Weeks 1-4</p>
      <p class="inflection">"…"</p>
      <p class="synthesis">…</p>
    </section>
    …
  </div>
</article>
```

Empty state: muted line beneath the eyebrow — "Arc authoring in
progress for this player."

## Acceptance criteria

- Carr page renders a 3-act arc from the seed file.
- Walkon / unseeded player renders empty state.
- Every act has title + week_range + inflection + synthesis.
- Voice passes the brief §2 rules (spot-check).
