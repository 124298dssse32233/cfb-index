# Anti-Take Engine — design spec (S2.3)

**Purpose.** The Hot-Take is a confident one-liner; the Anti-Take is the
honest counter. It names the caveat — sample size, cohort tier,
efficiency-vs-volume asymmetry, rank-band noise — that makes the hot
take shakier than it looks. Paired card, quiet divider, ≤ 3 sentences.

Per SIGNATURE_BETS §4 Bet #3 and brief §3 "Voice in practice":

> HOT TAKE: Carr's 3rd-down EPA is higher than every Heisman
>           winner since Burrow 2019.
> ANTI-TAKE: 3 of his 12 big 3rd-down conversions came in the
>            4th quarter against Ball State (53% garbage-time
>            context per our in-play model). Strip those: he ranks
>            4th in the cohort, not 1st. Still elite. Not record.

## Pairing rule

Every Hot-Take must have an Anti-Take. If no defensible Anti-Take can
be generated for a candidate, the **Hot-Take doesn't ship**. The pairing
is load-bearing on trust — a page that publishes only Hot-Takes reads
like marketing.

Concretely: `fetch_or_generate_take()` must return `None` when the
selected Hot-Take can't be paired. The renderer treats `None` as
"no Hot-Take section today," and the page quietly omits the module.

## Caveat library

Seed file: `seeds/anti_take_templates.yaml`. Each caveat has:

```
- id            stable slug
  condition     expression against the hot-take meta:
                  - "efficiency_metric"   — metric unit is efficiency
                  - "volume_metric"       — metric unit is volume
                  - "cohort_tiered"       — cohort label mentions "P4"
                  - "sample_thin_for_band"— sample is in 40..80 window
                  - "rank_band_compressed"— percentile < 95 (top-band noise)
                  - "near_tie"            — cohort_size > rank + 2 and percentile < 97
                  - "always"              — always applicable
  priority      int (1..5) — lower = preferred; picker takes the
                lowest-priority matching caveat
  text          Python .format()-ready with placeholders
```

Placeholders available to every template (from the Hot-Take's meta):

```
{rank}            int
{percentile}      int
{cohort}          str
{cohort_size}     int
{sample}          int
{metric_label}    str
{runner_up}       int         # rank + 1 — "drops to #{runner_up}"
{stripped_rank}   int         # one band lower estimate
{era_label}       str
```

## Selection algorithm

1. Sort caveats by `priority` ASC.
2. For each caveat, evaluate its condition against the take's meta.
3. First match that produces a non-empty rendered string wins.
4. `"always"` catch-all guarantees at least one caveat — the cohort-
   tier boilerplate always applies and reads like honest framing.

Repeatability: because conditions are deterministic on the take's
meta, the same Hot-Take always generates the same Anti-Take. No extra
stateful caching needed — the Anti-Take piggybacks on
`player_daily_hot_take`.

## Voice rules (§2 brief)

- Acknowledge, don't flinch. "Still elite. Not record." reads better
  than "we should note that…".
- Exactly 1–3 sentences. The caveat + an optional "here's the
  adjusted framing" + an optional "but still respect the signal".
- Never boilerplate. If the caveat can only be boilerplate for a given
  take, the pairing fails and the take holds.

## Data flow

```
HotTake (meta quadruple)
   │
   ▼
generate_anti_take(take)  ──► AntiTake { template_id, rendered_text,
   │                                      caveat_tag, meta }
   ▼
render_anti_take_card(ant) ──► <article class="anti-take"> sibling
                               directly below the Hot-Take card
```

`AntiTake.rendered_text` is plain text (escaped at render time). The
`caveat_tag` is a short label ("SAMPLE", "COHORT", "BAND", "TIE",
"EFFICIENCY", "VOLUME") surfaced in the UI as a small chip.

## What this spec deliberately does NOT include

- **Garbage-time stripping**. The example in the brief references an
  in-play model that doesn't exist in current data; that caveat waits
  for PBP-scoped situational tables.
- **Strength-of-schedule rerank**. Requires opponent-adjusted metrics
  at the player level — those land with the S2 savant data plumb.
- **Auto-evolving templates**. Caveats are hand-authored; the library
  grows by manual PR, not by a heuristic.

## Acceptance criteria

- Every Hot-Take on a rendered page ships paired with an Anti-Take
  directly below.
- A Hot-Take whose `generate_anti_take()` returns None is NOT rendered.
- The Anti-Take's caveat always references the specific Hot-Take's
  meta — no boilerplate ("there are always limitations…") ships.
- Voice: 1–3 sentences. Spot-check 10 Hot-Take / Anti-Take pairs and
  confirm each Anti-Take is specific + defensible.
