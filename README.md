# College Football Rankings Backend

This project turns the research in [`research/`](./research) into executable code.

Link integrity: run `python manage.py audit-links --strict` to fail the build on any broken internal href (invoked automatically by `publish_site.ps1`).

If we ever lose thread context, start with:

- [`docs/internal-project-context.md`](./docs/internal-project-context.md)
- [`docs/operations-runbook.md`](./docs/operations-runbook.md)
- [`docs/cfbd-tier2-and-safe-operations.md`](./docs/cfbd-tier2-and-safe-operations.md)
- [`docs/anthropic-second-brain-workflow.md`](./docs/anthropic-second-brain-workflow.md)
- [`research/feature-gap-memo-2026-04-21.md`](./research/feature-gap-memo-2026-04-21.md)
- [`research/conference-ranking-research-2026-04-21.md`](./research/conference-ranking-research-2026-04-21.md)
- [`research/sentiment-market-study-design-2026-04-21.md`](./research/sentiment-market-study-design-2026-04-21.md)
- [`research/cfb-fan-delight-viz-brief-2026-04-21.md`](./research/cfb-fan-delight-viz-brief-2026-04-21.md)
- [`research/anthropic-second-brain-synthesis-2026-04-21.md`](./research/anthropic-second-brain-synthesis-2026-04-21.md)
- [`research/conversation-intelligence-v1-data-plan-2026-04-21.md`](./research/conversation-intelligence-v1-data-plan-2026-04-21.md)
- [`research/conversation-intelligence-runtime-validation-2026-04-21.md`](./research/conversation-intelligence-runtime-validation-2026-04-21.md)
- [`research/anthropic-validated-conversation-v1-synthesis-2026-04-21.md`](./research/anthropic-validated-conversation-v1-synthesis-2026-04-21.md)
- [`research/offseason-modules-calendar-2026-04-21.md`](./research/offseason-modules-calendar-2026-04-21.md)
- [`research/offseason-modules-recommendation-2026-04-21.md`](./research/offseason-modules-recommendation-2026-04-21.md)
- [`research/proprietary-fan-intelligence-ideation-2026-04-21.md`](./research/proprietary-fan-intelligence-ideation-2026-04-21.md)
- [`research/fan-intelligence-flagship-roadmap-2026-04-21.md`](./research/fan-intelligence-flagship-roadmap-2026-04-21.md)
- [`research/fanbase-mood-system-design-2026-04-21.md`](./research/fanbase-mood-system-design-2026-04-21.md)
- [`research/affection-hostility-leaderboards-2026-04-21.md`](./research/affection-hostility-leaderboards-2026-04-21.md)
- [`research/frontend-design-benchmark-2026-04-21.md`](./research/frontend-design-benchmark-2026-04-21.md)
- [`research/cfb-language-understanding-2026-04-21.md`](./research/cfb-language-understanding-2026-04-21.md)
- [`research/unique-concepts-hardening-2026-04-22.md`](./research/unique-concepts-hardening-2026-04-22.md)
- [`research/unique-concepts-market-honesty-2026-04-22.md`](./research/unique-concepts-market-honesty-2026-04-22.md)
- [`research/offseason-homepage-execution-2026-04-22.md`](./research/offseason-homepage-execution-2026-04-22.md)
- [`research/offseason-fan-delight-deep-research-2026-04-22.md`](./research/offseason-fan-delight-deep-research-2026-04-22.md)
- [`research/offseason-publishing-queue-and-build-order-2026-04-22.md`](./research/offseason-publishing-queue-and-build-order-2026-04-22.md)
- [`src/cfb_rankings/fan_intelligence.py`](./src/cfb_rankings/fan_intelligence.py) (Team Mood Card + home board computation)
- [`output/anthropic-proprietary-fan-lab-review.md`](./output/anthropic-proprietary-fan-lab-review.md)
- [`output/anthropic-fanbase-mood-system-review.md`](./output/anthropic-fanbase-mood-system-review.md)
- [`output/anthropic-love-hate-leaderboards-review.md`](./output/anthropic-love-hate-leaderboards-review.md)
- [`output/anthropic-frontend-design-strategy-review.md`](./output/anthropic-frontend-design-strategy-review.md)
- [`output/anthropic-homepage-visual-review.md`](./output/anthropic-homepage-visual-review.md)
- [`output/anthropic-teampage-visual-review.md`](./output/anthropic-teampage-visual-review.md)
- [`output/anthropic-cfb-language-sarcasm-review.md`](./output/anthropic-cfb-language-sarcasm-review.md)
- [`output/anthropic-unique-concepts-hardening-review.md`](./output/anthropic-unique-concepts-hardening-review.md)
- [`output/anthropic-offseason-fan-delight-review.md`](./output/anthropic-offseason-fan-delight-review.md)
- [`output/anthropic-offseason-viz-review.md`](./output/anthropic-offseason-viz-review.md)
- [`output/anthropic-offseason-build-order-review.md`](./output/anthropic-offseason-build-order-review.md)

It is a greenfield analytics backend built for:

- `CollegeFootballData Tier 2` as the primary football data and analytics source
- `TheSportsDB` as an optional metadata and enrichment source
- an all-level `Power` model
- a separate `Resume` model

## Database

This project uses `SQLite` for local development.

That means:

- no PostgreSQL server
- no pgAdmin
- no database password
- one local file in the repo: `cfb_rankings.db`

## What is here

- database helpers and schema application
- source clients for SportsDB and CFBD
- canonical team/game mapping helpers
- ingestion pipelines
- a weekly model runner for `Power` and `Resume`

## Quick start

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and fill in the API keys.
3. Initialize the database.
4. Run CFBD ingestion first.
5. Run the models.
6. Build the full static site.
7. Add SportsDB later only if you want extra metadata or artwork.

Example commands:

```bash
python -m pip install -e .
python manage.py init-db
python manage.py ingest-cfbd-preseason --season 2025 --classification fbs
python manage.py ingest-cfbd-week --season 2025 --week 1
python manage.py run-models --season 2025 --through-week 1
python manage.py run-heisman-model --season 2025 --through-week 1
python manage.py build-site
```

The editable install matters for the newer conversation-intelligence path because it pulls in `vaderSentiment`, which is used for the first-pass local sentiment scoring layer.

The preseason ingest command now supports a classification-wide roster pull, which is the cleanest way to load the full FBS player universe in one CFBD roster call. That path also stores raw roster payload snapshots plus richer home-location metadata and current CFBD v2 returning-production fields for later player-card and model work.

The Heisman model now caches player season stats, player usage, and player-level WEPA inputs in local tables so the board can be rebuilt without repeatedly hammering the largest CFBD endpoints. The dedicated `run-heisman-model` command is useful when the team models are already loaded and you only want to refresh the award board.

CFBD currently exposes game betting lines, but not Heisman futures. The site is wired to display an external market prior if you load rows into `heisman_market_odds_weekly`, but it does not require award odds to render the board.

## One-command refresh

If you want the project to handle the ingest, model run, and HTML rebuild for you automatically, use:

```bash
python manage.py sync-site
```

That command will:

- initialize the SQLite schema if needed
- choose the most sensible season automatically
- detect the latest completed week when possible
- ingest every week from `1` through that week
- run the `Power` and `Resume` models
- rebuild the standalone report in `output/rankings.html`
- rebuild the full static site in `output/site`

Windows shortcuts:

- double-click [refresh_site.bat](C:\Users\kevin\Downloads\Sports Website\refresh_site.bat)
- or run [refresh_site.ps1](C:\Users\kevin\Downloads\Sports Website\refresh_site.ps1)

The PowerShell shortcut now uses the incremental sync path by default so everyday refreshes are less brute-force.

If you want the safest everyday refresh for a non-technical workflow, use:

- double-click [safe_refresh_site.bat](C:\Users\kevin\Downloads\Sports Website\safe_refresh_site.bat)
- or run [safe_refresh_site.ps1](C:\Users\kevin\Downloads\Sports Website\safe_refresh_site.ps1)

That helper writes a timestamped log to `output/logs` and defaults to a lighter incremental sync by skipping the heaviest play-level ingest and Heisman pass unless you opt back in.

`sync-site-incremental` can now skip an unnecessary model rerun when:

- the local season data is already current
- the latest saved model snapshot already covers the needed week
- the saved snapshot uses the current `MODEL_VERSION`

If you want to force a fresh model run anyway, use:

```bash
python manage.py sync-site-incremental --season 2025 --through-week 21 --force-models
```

If you want to force a specific cutoff, you can still do:

```bash
python manage.py sync-site --season 2025 --through-week 4
```

The combined commands now support safer lightweight flags when needed:

```bash
python manage.py sync-site-incremental --season 2025 --through-week 8 --skip-play-level --skip-heisman
python manage.py run-models --season 2025 --through-week 8 --skip-heisman
python manage.py ingest-cfbd-week --season 2025 --week 8 --skip-play-level
```

## Fan intelligence layer

The site now ships a first-class fan-intelligence layer on top of the conversation-intelligence pipeline.

Key surfaces:

- Team pages lead with a flagship `Team Mood Card` rendering `Fan Pulse`, `Reality Check`, `Swing Meter`, `Cohesion`, `Respect Gap`, `Rival Heat`, and `Top Storylines`, plus a confidence band. When the conversation sample has not cleared the publish gate, the card renders an intentional `Awaiting Signal` state rather than printing fake precision.
- The homepage now leads with a `Mood Board` block with `Biggest Vibe Shifts`, `Respect Gap Leaders`, `Country Higher Than The Fans`, `Rival Heat Leaders`, `Main Character Of The Week`, and `Most Panicked Fanbases`. If no team clears the publish gate, the block degrades to a visible "warming up" state.
- The matchup page now has an `Argument Theater` block with `Which Fanbase Is Calmer`, `What Fans Are Afraid Of`, and `Rival Timelines On Fire`.

Implementation notes:

- All derived axes live in `src/cfb_rankings/fan_intelligence.py`. The module reads directly from `team_week_conversation_features` and `conversation_storylines` and intentionally never collapses fan / rival / national audience buckets together.
- `Reality Gap` is derived by comparing fan belief to the structural power percentile. It is never inferred from text alone.
- The sarcasm / meme layer lives in `src/cfb_rankings/conversation_utils.py`. It carries a hand-built `CFB_MEME_PHRASES` lexicon (victory-lap, doompost, explicit-irony, rival-bait, and sarcastic-praise tags) and downgrades confidence when positive sentiment collides with rivalry or sarcastic-praise patterns.
- All public outputs prefer labeled confidence bands over precise numeric scores, per `research/fanbase-mood-system-design-2026-04-21.md` and `research/cfb-language-understanding-2026-04-21.md`.

## Conversation intelligence v1

The repo now has an early conversation-intelligence pipeline aimed at comparing fan discussion with model and market context.

Current operator commands:

```bash
python manage.py seed-team-aliases --season 2025
python manage.py collect-reddit-watchlist --season 2025 --week 8 --limit-teams 15 --search-limit 10
python manage.py collect-reddit-plan --season 2025 --week 21 --plan research/reddit-community-plan-v1.json
python manage.py collect-reddit-plan --season 2025 --week 21 --plan research/reddit-community-plan-cfb-safe-v2.json
python manage.py build-conversation-features --season 2025 --week 8
```

What this currently does:

- seeds season-aware team aliases
- builds a watchlist from explicit teams or the local schedule/model context
- collects Reddit posts for that watchlist
- stores raw conversation documents plus team-target sentiment rows
- aggregates daily and weekly features
- generates simple storyline keywords and representative links

Current source reality:

- Reddit JSON works from this environment with browser-like headers
- Reddit RSS / Atom feeds were also verified and are used as a fallback path
- The repo now supports config-driven subreddit collection via `collect-reddit-plan`, including direct team-subreddit listing pulls for `fan` buckets plus targeted in-community search for `rival` buckets
- Bluesky public search still looks unreliable from this environment
- YouTube and Apify remain the best next source expansions

Useful research / strategy references:

- `research/community-language-and-source-taxonomy-2026-04-22.md`
- `research/cfb-only-reddit-filtering-2026-04-22.md`
- `research/reddit-community-plan-cfb-safe-v2.json`
- `research/offseason-publishing-queue-and-build-order-2026-04-22.md`
- `output/anthropic-community-source-taxonomy-review.md`
- `output/anthropic-cfb-only-filtering-review.md`

Important caution:

- game-window conversation features only make sense when collection happens near the real game dates for the target week
- if you run a live test against an old historical week, the weekly aggregates can still validate, but the pregame/postgame game windows may correctly come back empty

## Full site output

The main generated site lives in:

- `output/site/index.html`
- `output/site/heisman/index.html`
- `output/site/players/index.html`
- `output/site/rankings/index.html`
- `output/site/archive/index.html`
- `output/site/conferences/index.html`
- `output/site/matchups/index.html`
- `output/site/teams/<team>.html`
- `output/site/players/<player>.html`

If you only want to rebuild the already-loaded site without re-ingesting data:

```bash
python manage.py build-site
```

If you want the cleanest publish step from already-loaded data, rebuild both deliverables together:

```bash
python manage.py build-published
```

That refreshes:

- `output/rankings.html`
- `output/site`

Windows shortcut:

- double-click [publish_site.bat](C:\Users\kevin\Downloads\Sports Website\publish_site.bat)
- or run [publish_site.ps1](C:\Users\kevin\Downloads\Sports Website\publish_site.ps1)

## Historical backfill

If you want the archive and year-by-year pages to get much richer, backfill more CFBD seasons.

Example:

```bash
python manage.py backfill-cfbd-history --start-season 2019 --end-season 2025 --include-postseason --run-models --build-site
```

That command will:

- initialize the schema if needed
- ingest each detected CFBD week for each requested season
- optionally ingest postseason checkpoints too
- optionally rerun models after each season load
- optionally rebuild the static site when the backfill is done

If you want to load data first and run models later, you can skip the last two flags:

```bash
python manage.py backfill-cfbd-history --start-season 2019 --end-season 2025 --include-postseason
```

If you want a logged Windows helper for a large backfill, use:

- [scripts/backfill_cfbd_logged.ps1](C:\Users\kevin\Downloads\Sports Website\scripts\backfill_cfbd_logged.ps1)

## Recommended source strategy

Use `CFBD` first.

That is the best source for:

- game results
- schedules
- advanced stats
- rosters
- recruiting
- returning production
- betting lines
- weather

Use `SportsDB` only as optional enrichment.

That is best for:

- extra metadata
- team identity fields
- venue fields
- badges, fanart, and other presentation assets

Current recommendation for this project:

- build the ratings engine on `CFBD`
- treat `SportsDB` as optional
- only ingest SportsDB when we specifically need better presentation or broader non-CFBD coverage

## Season identity

This project defines a football season by the year in which that competitive cycle begins.

Examples:

- the `2025 season` includes preseason coverage in summer 2025
- regular-season games in fall 2025 stay in `season_year = 2025`
- bowls, playoffs, and title games played in January or February 2026 still stay in `season_year = 2025`
- offseason movement in early 2026 belongs to the buildup for the `2026 season`, not the final 2025 rankings

In practice:

- `season_year` is the canonical season key
- the real game timestamp still lives on the game record
- `season_phase` is used to distinguish `preseason`, `regular season`, `conference championship`, `playoff`, `bowl`, and `final`
- front-end labels should prefer `2025 Season` and can optionally show `2025-26` as a helper label

## NCAA reference counts

Reference subdivision counts currently used for product framing as of `April 20, 2026`:

- `FBS`: `134` active/full-member programs, or `136` including transitioners
- `FCS`: `128` active/full-member programs, or `129` on the broader NCAA championship sponsorship listing
- `Division II`: `161` football programs
- `Division III`: `239` football programs

## Conference ranking model

Conference pages are no longer supposed to rank leagues by simple average team power alone.

Current product direction:

- primary conference rank uses a KenPom-style `RR50` benchmark
- `RR50` means the neutral-field rating a hypothetical team would need to go `.500` against a full round robin of that conference
- this is intentionally more robust than a plain average because one awful bottom team should not be able to hijack a whole league's rank
- conference pages also surface `Upper Strength`, a top-weighted quality measure that gives more emphasis to the best teams in the league
- very small affiliation groups are lightly regressed toward their subdivision baseline so one-team or two-team groups do not break the conference board
- together those measures help separate:
  - the hardest league to survive week to week
  - the league with the best national-title ceiling
  - the league with the strongest middle tier

## SportsDB workflow

Use SportsDB mainly for metadata enrichment:

- league and team discovery
- team identity fields
- venue fields
- schedule coverage in places where CFBD is thinner

Recommended sequence:

```bash
python manage.py list-sportsdb-leagues
python manage.py ingest-sportsdb --league-id <league_id> --season 2025 --level-code FBS --conference "Conference Name"
```

You can repeat `ingest-sportsdb` for each league or conference you want to bring in.

## Notes

- `manage.py` is the simplest way to run the project from the repo, especially on machines where user-site installs are not added to `sys.path`.
- `DATABASE_URL` defaults to `sqlite:///./cfb_rankings.db`, so you do not need to set up PostgreSQL for local work.
- The ingestion clients are built to be practical and editable. Sports APIs change, especially on long-lived hobby and indie plans.
- `Power` is predictive.
- `Resume` is backward-looking.
- Cross-level comparisons are published with uncertainty and connectivity instead of fake certainty.
